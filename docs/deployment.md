# Deploying the AMINE web front-end

> For a task-oriented, copy-paste walkthrough (local test → server → Koda), see
> [`docs/operator-guide.md`](operator-guide.md).

The web front-end is a single stateless FastAPI process (see
[`web/README.md`](../web/README.md)). Deployment reduces to three questions:

1. **Where does the STRING/BioGRID/IntAct data live?** It must be available
   before the first job.
2. **Where does job state live?** One JSON file per job under `AMINE_JOBS_DIR`.
3. **How much RAM/CPU does a run need?** node2vec on a full STRING network is
   the expensive step.

This document describes the technical requirements and the generic deployment
options. It deliberately does **not** compare specific providers: hosting
offers change over time, so the operator should compare the providers available
at deployment time against the requirements below and pick the best fit.

## 1. Technical requirements

Any host able to satisfy the following can run AMINE:

* **Container support** (recommended) — the project ships a Docker image, so
  any host that runs OCI containers (a VM with Docker, a container PaaS, a
  Kubernetes cluster) works unchanged. Alternatively, a plain Python 3.10+
  environment works too (`pip install -e ".[web]"`).
* **RAM** — see the sizing table in §3. Plan at least 2–4 GB for realistic
  runs on full interaction networks; more is better.
* **CPU** — 1–2 vCPUs are sufficient; the pipeline is mostly single-threaded
  per job.
* **Disk** — a few GB for the interaction data, plus space for job results.
* **Networking** — one inbound HTTP(S) port; optionally outbound SMTP for the
  e-mail notification feature.
* **Data availability** — the interaction networks must be present in
  `AMINE_DATA_DIR` before the first job (downloaded at start, at build time,
  or on a persistent volume — see below).
* **Optional: TLS termination** — put a reverse proxy in front for HTTPS if
  the host does not provide it.

The application is **stateless apart from two directories** (`AMINE_DATA_DIR`
and `AMINE_JOBS_DIR`), which makes it easy to move between hosts: re-run the
container with the right volumes and environment variables.

## 2. Data placement

The core reads the interaction networks from local files; it does **not**
download them on demand. Download only the species you will serve:

```bash
AMINE_DATA_DIR=/app/data python -m amine.download_data --specie human
```

`AMINE_DATA_DIR` (default: `src/data`) is where the files are written and read.

Two strategies, depending on whether the host has persistent storage:

* **Persistent volume**: download once into the volume; the data survives
  restarts and redeploys.
* **Ephemeral storage**: either bake the data into the image at build time
  (`--build-arg AMINE_SPECIES="human"` — the root [`Dockerfile`](../Dockerfile)
  supports this), or let the container entry point
  ([`web/start.sh`](../web/start.sh)) download it on every start.

> Downloading every species (human, mouse, drosophila, *C. elegans*) plus
> BioGRID and IntAct is several GB. For a web service, download only the
> species you expose and skip the archives you do not use
> (`--skip-biogrid --skip-intact`).

## 3. Resource sizing

| Workload | RAM | Notes |
| -------- | --- | ----- |
| Small custom edge list | < 512 MB | runs on the smallest instances |
| STRING human, few modules | ~1–2 GB | set `AMINE_MAX_WORKERS=1` |
| STRING human, full run | 2–4 GB | needs a host with generous RAM |

Set `AMINE_MAX_WORKERS=1` on small instances so a single job does not exhaust
memory. The upload size limit is controlled by `AMINE_MAX_UPLOAD_BYTES`
(default 10 MB).

## 4. Deployment options (generic)

Choose the *class* of hosting that matches your needs; then compare the
providers in that class for price, quotas, and availability at the time you
deploy.

### 4.1 Your own VM / server (most control)

Run the Docker image directly. This works on any machine you control — a lab
server, an institutional VM, or a cloud VM of any provider.

```bash
docker build -t amine-web .          # or pull the image from your registry
docker run -d --restart unless-stopped -p 80:8000 \
  -v /srv/amine/data:/app/data -v /srv/amine/jobs:/app/jobs \
  -e AMINE_SPECIES=human amine-web
```

Put a reverse proxy (nginx, Caddy, …) in front for TLS. Persistent storage is
trivial (host directories). This is the recommended option when you have, or
can request, a machine.

### 4.2 Container PaaS (least operations)

Managed platforms that build/run a container from a `Dockerfile`. Typical
shape: you push the repository or image, set environment variables, and get an
HTTPS endpoint.

* Check that the plan offers **enough RAM** (many free tiers offer 512 MB,
  which only fits small custom networks).
* Storage is usually **ephemeral**: bake the data into the image or accept a
  re-download on restart.
* Some platforms offer paid persistent disks if you need them.

### 4.3 Kubernetes / cluster schedulers

If your organisation runs a Kubernetes cluster (or the GitLab/CI system offers
"review apps" or long-lived deployments), the same image deploys there. Mount
`AMINE_DATA_DIR` and `AMINE_JOBS_DIR` on persistent volumes; expose the service
on port 8000; set the environment variables from §5. The application has no
other cluster-specific requirements (no database, no shared filesystem between
replicas beyond the job directory if you scale out — run a single replica
unless you adapt the job storage).

### 4.4 What to check when comparing providers

| Criterion | Why it matters |
| --------- | -------------- |
| RAM per instance | node2vec on a full STRING network needs 2–4 GB |
| Persistent storage | avoids re-downloading the interaction data on each restart |
| Egress/ingress limits | users download `.xlsx` results; data download is a few GB at first start |
| Build time / image size limits | the image with baked-in data is ~2 GB |
| Public vs private visibility | expression data may be sensitive; a public demo must not receive confidential files |
| Cost of always-on vs scale-to-zero | jobs run 15–30 min; cold starts delay the queue |

## 5. Environment variables

| Variable | Default | Meaning |
| -------- | ------- | ------- |
| `AMINE_DATA_DIR` | `src/data` | where interaction networks are stored |
| `AMINE_JOBS_DIR` | `jobs` | where job state and results are stored |
| `AMINE_SPECIES` | `human mouse drosophila` | species fetched by the entry point when data is missing |
| `AMINE_MAX_WORKERS` | `2` | size of the process pool (queue width) |
| `AMINE_MAX_UPLOAD_BYTES` | `10485760` | maximum upload size (10 MB) |
| `AMINE_JOB_TIMEOUT` | `3600` | reserved for future timeout handling |
| `AMINE_SMTP_HOST` | *(unset)* | SMTP server for e-mail notifications |
| `AMINE_SMTP_PORT` | `587` | SMTP port |
| `AMINE_SMTP_USER` / `AMINE_SMTP_PASSWORD` | *(unset)* | SMTP credentials |
| `AMINE_SMTP_FROM` | `AMINE_SMTP_USER` | sender address |
| `AMINE_PUBLIC_URL` | *(unset)* | public base URL used in e-mails |
| `PORT` | `8000` | HTTP port |

### Queue and e-mail notifications

A full STRING run takes 15–30 minutes, so jobs are executed **sequentially** by
a `ProcessPoolExecutor` of size `AMINE_MAX_WORKERS`. When all workers are busy,
new jobs wait in the queue; `GET /api/jobs/{id}` reports `queued_ahead` and the
web page shows the position.

E-mail notification is optional: set `AMINE_SMTP_HOST` (and credentials) and the
user can enter an address in the form. The e-mail is sent when the job finishes
or fails. Without SMTP configuration the field is ignored.

## 6. Health check and monitoring

`GET /health` returns `{"status": "ok"}`; point any liveness/readiness probe
or external monitor at it. Job progress is observable through
`GET /api/jobs/{job_id}`.

## 7. Troubleshooting

* **`FileNotFoundError` on the STRING file** — the data was not downloaded, or
  `AMINE_DATA_DIR` points somewhere else. Run `python -m amine.download_data`.
* **Job stuck in `queued`** — the process pool is saturated; increase
  `AMINE_MAX_WORKERS` or wait.
* **Out-of-memory kill** — reduce `AMINE_MAX_WORKERS` to 1 and/or limit the
  number of modules with `-k/--nb_modules`.
* **Data lost after redeploy** — the host has ephemeral storage; bake the data
  into the image or use a host with a volume.
