# AMINE web application

A minimal, modern web front-end for AMINE, replacing the historical
Django + Huey + SQLite server that was accidentally removed.

## Design

| Concern            | Historical stack        | New stack                          |
| ------------------ | ----------------------- | ---------------------------------- |
| HTTP framework     | Django                  | FastAPI + uvicorn                  |
| Background jobs    | Huey + Redis/SQLite     | `ProcessPoolExecutor`              |
| Job persistence    | Django ORM + SQLite     | one JSON file per job (`jobs/`)    |
| Templating         | Django templates        | Jinja2 (via FastAPI)               |
| Deployment         | dedicated server        | any free container host            |

The application is deliberately stateless: all state lives in the `jobs/`
directory, so the container can be restarted or scaled without a database.

## Endpoints

| Method | Path                        | Description                          |
| ------ | --------------------------- | ------------------------------------ |
| GET    | `/`                         | upload form                          |
| GET    | `/health`                   | liveness probe                       |
| POST   | `/api/jobs`                 | create a job (multipart upload)      |
| GET    | `/api/jobs/{job_id}`        | poll job status                      |
| POST   | `/api/jobs/{job_id}/cancel` | abort a queued or running job        |
| GET    | `/api/jobs/{job_id}/result` | download the `.xlsx` result          |

## Running locally

```bash
pip install -e ".[web]"
uvicorn web.api.main:app --reload
# then open http://127.0.0.1:8000
```

## Configuration

All settings are environment variables:

| Variable                 | Default      | Meaning                              |
| ------------------------ | ------------ | ------------------------------------ |
| `AMINE_DATA_DIR`         | `src/data`   | where interaction networks are stored |
| `AMINE_SPECIES`          | `human mouse drosophila` | species fetched when data is missing |
| `AMINE_JOBS_DIR`         | `jobs`       | where job state and results are kept |
| `AMINE_MAX_WORKERS`      | `2`          | size of the process pool (queue width) |
| `AMINE_MAX_UPLOAD_BYTES` | `10485760`   | maximum upload size (10 MB)          |
| `AMINE_JOB_TIMEOUT`      | `3600`       | reserved for future timeout handling |
| `AMINE_SMTP_HOST`        | *(unset)*    | SMTP server for e-mail notifications |
| `AMINE_SMTP_PORT`        | `587`        | SMTP port                            |
| `AMINE_SMTP_USER`        | *(unset)*    | SMTP user                            |
| `AMINE_SMTP_PASSWORD`    | *(unset)*    | SMTP password                        |
| `AMINE_SMTP_FROM`        | `AMINE_SMTP_USER` | sender address                  |
| `AMINE_SMTP_STARTTLS`    | `1`          | use STARTTLS                         |
| `AMINE_PUBLIC_URL`       | *(unset)*    | public base URL used in e-mails      |

## Queue and notifications

Because a full STRING run takes 15–30 minutes, jobs are executed **sequentially**
by a `ProcessPoolExecutor` of size `AMINE_MAX_WORKERS` (default 2). When all
workers are busy, new jobs wait in the executor's queue; the job status endpoint
reports how many jobs are ahead:

```json
{ "status": "queued", "queued_ahead": 3 }
```

The web page displays this position and polls every 2 seconds.

**E-mail notification** is optional. If `AMINE_SMTP_HOST` is set and the user
provides an address in the form, an e-mail is sent when the job finishes (or
fails). If SMTP is not configured, the field is simply ignored.

## Progress and input validation

* **Progress bar.** While a job runs, the worker reports its current stage
  (`mapping gene identifiers`, `computing network embedding`,
  `detecting active modules`, `writing results`) and a fraction; the web page
  shows a progress bar and the stage name.
* **0-based column indices.** The form labels state that the gene / log2fc /
  p-value column indices are 0-based.
* **Mapping report.** After mapping the gene identifiers, the core reports how
  many were mapped, e.g. *"Mapped 7/20 gene identifiers (35.0%) to
  'drosophila'"*. If fewer than 50 % map, a warning is added: *"the selected
  species may be wrong"*. The numbers are shown on the web page (in red when
  low) and printed by the CLI.
* **Abort button.** While a job is queued or running, an **Abort job** button is
  shown. It calls `POST /api/jobs/{id}/cancel`, which terminates the job's
  process and marks the job as `cancelled`.
* **Clear file errors.** If a column index is out of bounds, the error message
  says so and reminds the user that indices are 0-based.
* **On-demand species download.** Before running a job, the worker calls
  `ensure_species_data(specie)`: if the species' STRING files are missing they
  are downloaded automatically (the stage is shown as *"checking species
  data"*). Existing files are left untouched, so this is a no-op once the data
  is present. The image still pre-downloads all three species at build time to
  avoid a slow first job.

## Aggregation methods

Only two aggregation methods are implemented:

| Method | Status | Notes |
| ------ | ------ | ----- |
| `pvalue` | **available** | uses the p-value column directly |
| `log2fc` | **available** | derives a p-value from the log2 fold-changes; must **not** be combined with a p-value column |
| `pivalue` | not implemented | disabled in the form |
| `count` | not implemented | disabled in the form |

The form greys out the unimplemented methods, and the API rejects them with a
`422` error.

> The interaction networks are read from local files and are **not** downloaded
> on demand. Run `python -m amine.download_data --specie human` once, pointing
> `AMINE_DATA_DIR` at a persistent volume.

## Deployment

Build and run the container from the repository root:

```bash
docker build -f web/Dockerfile -t amine-web .
docker run -p 8000:8000 \
  -v amine-data:/app/data -v amine-jobs:/app/jobs amine-web
```

The same image runs on any container host (a VM with Docker, a container PaaS,
a Kubernetes cluster). Ready-made configs are provided in
[`fly.toml`](../fly.toml) and [`render.yaml`](../render.yaml) as examples.

**See [`docs/deployment.md`](../docs/deployment.md) for the full guide**:
technical requirements, data/volume strategy, deployment options and resource
sizing.
