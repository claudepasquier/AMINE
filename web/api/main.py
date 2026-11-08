"""FastAPI application exposing AMINE over HTTP.

This replaces the historical Django + Huey + SQLite stack with a single
process that:

* serves a small upload form (``GET /``);
* accepts a job (``POST /api/jobs``) and runs it in a background process;
* exposes the job status (``GET /api/jobs/{job_id}``) for polling;
* serves the resulting ``.xlsx`` file (``GET /api/jobs/{job_id}/result``).

Run locally with::

    uvicorn web.api.main:app --reload

The application is intentionally stateless (job state lives in JSON files) so
that it can be deployed on any free container host.
"""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import jobs

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="AMINE",
    description=(
        "Active Module Identification through Network Embedding — web front-end"
    ),
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_upload(upload: UploadFile, destination: pathlib.Path) -> pathlib.Path:
    """Persist an uploaded file, enforcing the configured size limit."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with destination.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > jobs.MAX_UPLOAD_BYTES:
                out.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Uploaded file exceeds the maximum allowed size of "
                        f"{jobs.MAX_UPLOAD_BYTES} bytes"
                    ),
                )
            out.write(chunk)
    return destination


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serve the upload form."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"max_upload_mb": jobs.MAX_UPLOAD_BYTES // (1024 * 1024)},
    )


@app.get("/health")
async def health() -> dict:
    """Liveness probe used by container hosts."""
    return {"status": "ok"}


@app.post("/api/jobs")
async def create_job(
    expvalue_file: UploadFile = File(..., description="expression values file"),
    specie: str = Form("human"),
    gene_col: int = Form(...),
    log2fc_col: int | None = Form(None),
    pvalue_col: int | None = Form(None),
    aggregation_method: str = Form("pvalue"),
    nb_modules_to_find: int | None = Form(None),
    network: str = Form("string"),
    email: str | None = Form(None),
    focus_genes_file: UploadFile | None = File(None),
    network_file: UploadFile | None = File(None),
) -> JSONResponse:
    """Create and enqueue a module-detection job."""
    if not (log2fc_col or pvalue_col):
        raise HTTPException(
            status_code=422,
            detail=("At least one of log2fc_col or pvalue_col must be specified"),
        )
    if aggregation_method not in ("pvalue", "log2fc"):
        raise HTTPException(
            status_code=422,
            detail=(
                "aggregation_method must be 'pvalue' or 'log2fc' "
                "('pivalue' and 'count' are not implemented)"
            ),
        )
    # Only STRING is served by the web front-end: the image bakes in the STRING
    # networks only, so BioGRID/IntAct requests would fail at run time.
    if network not in ("string",) and not network.startswith("/"):
        raise HTTPException(
            status_code=422,
            detail=(
                "network must be 'string' or an uploaded edge list "
                "(BioGRID and IntAct are not available on the web front-end)"
            ),
        )

    job = jobs.create_job(params={})
    workdir = job.workdir

    # Preserve the original extension so that XLSX uploads are read as Excel.
    expvalue_suffix = pathlib.Path(expvalue_file.filename or "").suffix or ".csv"
    expvalue_path = _save_upload(expvalue_file, workdir / f"expvalue{expvalue_suffix}")
    focus_path = None
    if focus_genes_file is not None and focus_genes_file.filename:
        focus_path = _save_upload(focus_genes_file, workdir / "focus_genes.txt")

    # An uploaded edge list takes precedence over the predefined network.
    if network_file is not None and network_file.filename:
        network_suffix = pathlib.Path(network_file.filename or "").suffix or ".tsv"
        network = str(_save_upload(network_file, workdir / f"network{network_suffix}"))

    job.params = {
        "expvalue_file": str(expvalue_path),
        "focus_genes_file": str(focus_path) if focus_path else None,
        "specie": specie,
        "gene_col": gene_col,
        "log2fc_col": log2fc_col,
        "pvalue_col": pvalue_col,
        "aggregation_method": aggregation_method,
        "nb_modules_to_find": nb_modules_to_find,
        "network": network,
        "email": email or None,
    }
    job.save()
    jobs.submit_job(job)

    return JSONResponse(
        status_code=202,
        content={"job_id": job.job_id, "status": job.status},
    )


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str) -> dict:
    """Return the current status of a job."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error,
        "modules": job.modules,
        "has_result": job.result_file is not None,
        "queued_ahead": jobs.queue_position(job),
        "stage": job.stage,
        "progress": job.progress,
        "mapping": job.mapping,
    }


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    """Cancel a queued or running job."""
    if not jobs.cancel_job(job_id):
        raise HTTPException(
            status_code=409, detail="job cannot be cancelled (unknown or finished)"
        )
    return {"job_id": job_id, "status": "cancelled"}


@app.get("/api/jobs/{job_id}/result")
async def job_result(job_id: str) -> FileResponse:
    """Download the ``.xlsx`` result of a finished job."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="job is not finished")
    path = jobs.result_path(job_id)
    if path is None:
        raise HTTPException(status_code=404, detail="result not available")
    return FileResponse(
        path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        filename=f"amine_{job_id}.xlsx",
    )
