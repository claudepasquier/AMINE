"""Tests for the FastAPI web front-end.

These tests exercise the HTTP surface without running a real module-detection
job (which would require downloading the STRING network). The background
worker is covered indirectly through :mod:`web.api.jobs`.
"""

import os
import tempfile

# Point the job store at a throw-away directory *before* importing the app.
os.environ.setdefault("AMINE_JOBS_DIR", tempfile.mkdtemp(prefix="amine-jobs-"))

from fastapi.testclient import TestClient

from web.api import jobs
from web.api.main import app

client = TestClient(app)


def test_index_serves_form():
    response = client.get("/")
    assert response.status_code == 200
    assert "AMINE" in response.text


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_job_requires_quantification_column():
    response = client.post(
        "/api/jobs",
        data={"specie": "human", "gene_col": "0"},
        files={"expvalue_file": ("expr.csv", b"gene,log2fc\nA,1\n", "text/csv")},
    )
    assert response.status_code == 422


def test_job_lifecycle_state_machine():
    job = jobs.create_job(params={"specie": "human"})
    assert job.status == "queued"

    loaded = jobs.get_job(job.job_id)
    assert loaded is not None
    assert loaded.job_id == job.job_id
    assert loaded.status == "queued"


def test_unknown_job_returns_404():
    response = client.get("/api/jobs/does-not-exist")
    assert response.status_code == 404


def test_result_before_completion_returns_409():
    job = jobs.create_job(params={"specie": "human"})
    response = client.get(f"/api/jobs/{job.job_id}/result")
    assert response.status_code == 409


def test_queue_position_counts_earlier_queued_jobs():
    first = jobs.create_job(params={"specie": "human"})
    second = jobs.create_job(params={"specie": "human"})
    # ``second`` was created after ``first``, so at least one job is ahead.
    assert jobs.queue_position(second) >= 1
    # A running/done job is never "queued".
    first.status = "running"
    assert jobs.queue_position(first) == 0


def test_status_includes_queue_position():
    job = jobs.create_job(params={"specie": "human"})
    response = client.get(f"/api/jobs/{job.job_id}")
    assert response.status_code == 200
    assert "queued_ahead" in response.json()


def test_cancel_queued_job():
    job = jobs.create_job(params={"specie": "human"})
    assert jobs.cancel_job(job.job_id) is True
    assert jobs.get_job(job.job_id).status == "cancelled"
    # a second cancellation is a no-op
    assert jobs.cancel_job(job.job_id) is False


def test_cancel_unknown_job_returns_409():
    response = client.post("/api/jobs/does-not-exist/cancel")
    assert response.status_code == 409
