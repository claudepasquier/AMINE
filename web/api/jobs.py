"""Background job management for the AMINE web application.

The historical web server used Django + Huey + SQLite. This module replaces
that stack with a deliberately simple, dependency-light design:

* each job is described by a JSON file ``<JOBS_DIR>/<job_id>.json``;
* the heavy computation runs in a :class:`concurrent.futures.ProcessPoolExecutor`
  so that the FastAPI event loop is never blocked;
* no database is required, which keeps deployment on free container hosts
  (Render, Fly.io, Hugging Face Spaces, ...) trivial.

The public surface is intentionally small: :func:`create_job`,
:func:`get_job`, :func:`submit_job` and :func:`result_path`.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import pathlib
import queue
import sys
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# Make the ``amine`` package importable when the application is run from a
# source checkout (e.g. ``uvicorn web.api.main:app`` without
# ``pip install -e .``). This module is re-imported in the worker process, so
# the bootstrap also fixes ``ModuleNotFoundError: No module named 'amine'``
# raised inside the process pool.
_SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Configuration (overridable through environment variables)
# ---------------------------------------------------------------------------

JOBS_DIR = pathlib.Path(os.environ.get("AMINE_JOBS_DIR", "jobs")).resolve()
MAX_WORKERS = int(os.environ.get("AMINE_MAX_WORKERS", "2"))
MAX_UPLOAD_BYTES = int(os.environ.get("AMINE_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
JOB_TIMEOUT_SECONDS = int(os.environ.get("AMINE_JOB_TIMEOUT", "3600"))

# Optional e-mail notification (disabled unless SMTP_HOST is set).
SMTP_HOST = os.environ.get("AMINE_SMTP_HOST")
SMTP_PORT = int(os.environ.get("AMINE_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AMINE_SMTP_USER")
SMTP_PASSWORD = os.environ.get("AMINE_SMTP_PASSWORD")
SMTP_FROM = os.environ.get("AMINE_SMTP_FROM", SMTP_USER or "amine@localhost")
SMTP_STARTTLS = os.environ.get("AMINE_SMTP_STARTTLS", "1") not in ("0", "false", "")
PUBLIC_URL = os.environ.get("AMINE_PUBLIC_URL", "")

JOBS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Scheduler
#
# Jobs are executed one per process so that a running job can be terminated on
# demand (the "abort" button). A bounded pool of worker threads pulls job ids
# from a queue, so at most ``MAX_WORKERS`` jobs run concurrently and the rest
# wait in the queue.
# ---------------------------------------------------------------------------

_job_queue: queue.Queue = queue.Queue()
_processes: dict[str, multiprocessing.Process] = {}
_processes_lock = threading.Lock()
_workers_started = False
_workers_lock = threading.Lock()


def _worker_loop() -> None:
    """Pull job ids from the queue and run each in a dedicated process."""
    while True:
        job_id = _job_queue.get()
        if job_id is None:
            break
        try:
            job = get_job(job_id)
            if job is None or job.status == "cancelled":
                continue
            process = multiprocessing.Process(
                target=_run_job, args=(job_id,), daemon=True
            )
            with _processes_lock:
                _processes[job_id] = process
            process.start()
            process.join()
            with _processes_lock:
                _processes.pop(job_id, None)
        finally:
            _job_queue.task_done()


def _ensure_workers() -> None:
    """Start the worker threads on first use."""
    global _workers_started
    with _workers_lock:
        if not _workers_started:
            for _ in range(MAX_WORKERS):
                threading.Thread(target=_worker_loop, daemon=True).start()
            _workers_started = True


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------


@dataclass
class Job:
    """Description of a single module-detection job."""

    job_id: str
    status: str = "queued"  # queued | running | done | error
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    params: dict[str, Any] = field(default_factory=dict)
    result_file: str | None = None
    error: str | None = None
    modules: list[list[Any]] = field(default_factory=list)
    stage: str = ""
    progress: float = 0.0
    mapping: dict[str, Any] = field(default_factory=dict)

    @property
    def json_path(self) -> pathlib.Path:
        return JOBS_DIR / f"{self.job_id}.json"

    @property
    def workdir(self) -> pathlib.Path:
        return JOBS_DIR / self.job_id

    def save(self) -> None:
        """Persist the job state to disk (atomic write)."""
        tmp = self.json_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(self.json_path)


def create_job(params: dict[str, Any]) -> Job:
    """Create a new job, persist it and return it."""
    job = Job(job_id=uuid.uuid4().hex, params=params)
    job.workdir.mkdir(parents=True, exist_ok=True)
    job.save()
    return job


def get_job(job_id: str) -> Job | None:
    """Load a job from disk, or return ``None`` if it does not exist."""
    path = JOBS_DIR / f"{job_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Job(**data)


def result_path(job_id: str) -> pathlib.Path | None:
    """Return the path of the result file for a finished job."""
    job = get_job(job_id)
    if job and job.result_file:
        path = pathlib.Path(job.result_file)
        if path.is_file():
            return path
    return None


def queue_position(job: Job) -> int:
    """Return the number of jobs ahead of ``job`` in the queue.

    Jobs are executed by a :class:`ProcessPoolExecutor`; when all workers are
    busy, new jobs wait in the executor's internal queue. This function makes
    that queue visible by counting the still-queued jobs that were created
    before ``job``. A value of ``0`` means the job is next (or already running).
    """
    if job.status != "queued":
        return 0
    ahead = 0
    for path in JOBS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if (
            data.get("status") == "queued"
            and data.get("created_at", 0) < job.created_at
        ):
            ahead += 1
    return ahead


def send_notification(job: Job) -> None:
    """E-mail the job owner when the job finishes (if configured).

    Notification is best-effort: any failure is logged and never affects the
    job result. It is enabled only when ``AMINE_SMTP_HOST`` is set and the job
    carries an ``email`` parameter.
    """
    recipient = job.params.get("email")
    if not recipient or not SMTP_HOST:
        return

    import smtplib
    from email.message import EmailMessage

    if job.status == "done":
        subject = f"AMINE job {job.job_id} finished"
        body = (
            f"Your AMINE job {job.job_id} has finished.\n\n"
            f"Number of modules found: {len(job.modules)}\n"
        )
        if PUBLIC_URL:
            body += f"Download the result: {PUBLIC_URL}/api/jobs/{job.job_id}/result\n"
    else:
        subject = f"AMINE job {job.job_id} failed"
        body = f"Your AMINE job {job.job_id} failed.\n\n{job.error or ''}\n"

    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            if SMTP_STARTTLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD or "")
            smtp.send_message(message)
    except Exception:  # noqa: BLE001 - notification must never break a job
        print(f"warning: could not send notification for job {job.job_id}")


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


def _run_job(job_id: str) -> None:
    """Execute a job in a worker process.

    This function is the entry point of the :class:`ProcessPoolExecutor`. It
    re-reads the job from disk (the object is not pickled across processes),
    runs the AMINE core and updates the job state.
    """
    job = get_job(job_id)
    if job is None:
        return

    job.status = "running"
    job.started_at = time.time()
    job.save()

    try:
        # Imported here so that the worker process only pays the import cost
        # when it actually runs a job.
        from amine.download_data import ensure_species_data
        from amine.process_real_network import process

        # NOTE: the callbacks update the *same* ``job`` object that the
        # ``finally`` block saves below. Re-reading the job here would be
        # overwritten by that final save, losing the stage/progress/mapping.
        def progress(stage: str, fraction: float) -> None:
            """Persist the current stage so the web page can display it."""
            job.stage = stage
            job.progress = fraction
            job.save()

        def stats(mapping: dict) -> None:
            """Persist the gene-identifier mapping statistics."""
            job.mapping = mapping
            job.save()

        params = job.params

        # Download the species data on demand if it is not already present, so
        # that a job for a species that was not pre-downloaded still succeeds.
        progress("checking species data", 0.02)
        ensure_species_data(params["specie"])

        output_file = job.workdir / "result.xlsx"
        modules = process(
            expvalue_file=params["expvalue_file"],
            network=params.get("network", "string"),
            specie=params["specie"],
            gene_col=params["gene_col"],
            log2fc_col=params.get("log2fc_col"),
            pvalue_col=params.get("pvalue_col"),
            output_file=str(output_file),
            focus_genes_file=params.get("focus_genes_file"),
            aggregation_method=params.get("aggregation_method", "pvalue"),
            precomputed=params.get("precomputed"),
            nb_modules_to_find=params.get("nb_modules_to_find"),
            progress_callback=progress,
            stats_callback=stats,
        )
        job.modules = modules or []
        job.result_file = str(output_file)
        job.status = "done"
    except Exception:  # noqa: BLE001 - we want to surface any failure to the user
        job.status = "error"
        job.error = traceback.format_exc()
    finally:
        job.finished_at = time.time()
        job.save()
        send_notification(job)


def submit_job(job: Job) -> None:
    """Enqueue a job for execution."""
    _ensure_workers()
    _job_queue.put(job.job_id)


def cancel_job(job_id: str) -> bool:
    """Cancel a queued or running job.

    A running job is terminated (its process is killed); a queued job is simply
    marked as cancelled and skipped by the worker. Returns ``True`` if the job
    was cancelled, ``False`` if it was unknown or already finished.
    """
    job = get_job(job_id)
    if job is None or job.status not in ("queued", "running"):
        return False
    with _processes_lock:
        process = _processes.get(job_id)
    if process is not None and process.is_alive():
        process.terminate()
        process.join(timeout=5)
    job.status = "cancelled"
    job.finished_at = time.time()
    job.save()
    return True
