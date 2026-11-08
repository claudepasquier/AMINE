# Operator guide

This guide is for the person who runs and deploys AMINE. It has three parts:

* **A. Test the application locally** (no account needed).
* **B. Deploy the web app on a server** (any host satisfying the technical
  requirements in [`docs/deployment.md`](deployment.md)).
* **C. Publish the code on Koda (CNRS GitLab)** and run the container on a VM.

Everything is driven by the same Docker image, so the three parts are
independent.

---

## A. Test the application locally

### A.1 Prerequisites

* Python **3.10 or newer** (`python3 --version`).
* ~2 GB of free disk space for the human STRING data.
* Git.

### A.2 Install

```bash
git clone <repository-url> amine
cd amine

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -e ".[web,dev]"
```

### A.3 Run the automated tests (no data required)

```bash
pytest tests/ -q
```

Expected result: `32 passed`. This includes the golden tests that check the
unified core reproduces the published `amine_github` results.

### A.4 Download the interaction data

The core reads the networks from local files, so download the species you need
(human only, skipping the archives you do not use):

```bash
python -m amine.download_data --specie human --skip-biogrid --skip-intact
```

The files are written to `src/data/real/ppi/` (override with `AMINE_DATA_DIR`).

### A.5 Test the command line (fast, ~1 minute)

Use the bundled custom sub-network so you do not wait for the full STRING
embedding:

```bash
python -m amine \
  -x examples/example_expression.csv \
  -g 0 -l 1 -p 2 -s human -n examples/example_network.tsv \
  -o examples/example_result.xlsx -k 5 -v
```

This writes `examples/example_result.xlsx` (two sheets: modules and
gene-to-module mapping). See [`examples/README.md`](../examples/README.md).

> Using the full STRING network (`-n string`) also works but the pure-Python
> node2vec embedding takes **15–30 minutes** on ~17 000 nodes.

### A.6 Test the web application

```bash
uvicorn web.api.main:app --reload
```

Open <http://127.0.0.1:8000> and fill the form:

* **Expression values file**: `examples/example_expression.csv`
* **Custom network file**: `examples/example_network.tsv` (for a fast run)
* **Gene column** = `0`, **log2fc column** = `1`, **pvalue column** = `2`
* **Max number of modules** = `5`

Submit; the page polls the job and offers the `.xlsx` for download. To stop the
server, press `Ctrl+C`.

### A.7 (Optional) Test the container

```bash
docker build -t amine-web .
docker run -p 8000:8000 -v amine-data:/app/data -v amine-jobs:/app/jobs amine-web
# open http://localhost:8000
```

---

## B. Deploy the web app on a server

This part is generic on purpose: hosting offers change over time, so compare
the providers available when you deploy against the technical requirements in
[`docs/deployment.md`](deployment.md) (§1 requirements, §4 deployment options)
and pick the best fit. What follows works on any host that runs the Docker
image — a VM you control, a container PaaS, or a cluster.

### B.1 Build or obtain the image

Either build it on the host:

```bash
docker build -t amine-web .
```

…or pull it from your container registry, e.g. the image built by CI (see
part C):

```bash
docker login <registry-host>
docker pull <registry-host>/<group>/amine:latest
```

> The image bakes the human STRING data in at build time
> (`--build-arg AMINE_SPECIES="human"`), so the first start is fast. If you
> build without it, the entry point downloads the data on first start.

### B.2 Run the container

```bash
# persistent directories for data and job state
sudo mkdir -p /srv/amine/data /srv/amine/jobs

docker run -d --restart unless-stopped \
  --name amine-web \
  -p 80:8000 \
  -v /srv/amine/data:/app/data \
  -v /srv/amine/jobs:/app/jobs \
  -e AMINE_SPECIES=human \
  -e AMINE_MAX_WORKERS=1 \
  amine-web
```

On a managed PaaS the same settings become environment variables and volume
mounts in the platform's configuration UI; bind-mount directories, a named
volume or a platform disk all work — see [`docs/deployment.md`](deployment.md)
§2 for the data-placement trade-offs.

### B.3 Verify

Open `http://<host>/health` (expect `{"status": "ok"}`), then the web UI and
upload `examples/example_expression.csv` with the custom network
`examples/example_network.tsv` for a fast check.

### B.4 Updating

Pull (or rebuild) the image and restart the container:

```bash
docker pull <registry-host>/<group>/amine:latest
docker stop amine-web && docker rm amine-web
# re-run the `docker run` command from B.2
```

---

## C. Publish the code on Koda (CNRS GitLab)

Koda is the CNRS GitLab. It hosts the source and runs CI; the container itself
runs on a VM (lab server or CC-IN2P3). The pipeline is already defined in
[`.gitlab-ci.yml`](../.gitlab-ci.yml).

### C.1 Create the project on Koda

1. Log in to your Koda instance (the URL is provided by your DSI/DR).
2. **New project → Create blank project**.
3. Name it `amine`; keep it **private** or **internal** as appropriate.
4. Copy the repository URL shown (SSH or HTTPS).

### C.2 Push the code

```bash
cd /path/to/amine

git remote add koda <koda-repository-url>
git push -u koda main
```

### C.3 Let the pipeline run

Open **Build → Pipelines** on Koda. The pipeline has two stages:

* **test** — runs `ruff`, `black --check` and `pytest`.
* **build-image** — on the default branch or a tag, builds the image and pushes
  it to the Koda container registry as
  `$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA` and `:latest`.

If the `build-image` job fails with a registry error, ask your DSI to enable the
**Container Registry** for the project (Settings → General → Visibility →
Container Registry).

### C.4 Run the container on a VM

On the VM that will host the service (lab server or CC-IN2P3 VM):

```bash
# 1. Log in to the Koda registry (use a deploy token or your credentials)
docker login <koda-registry-host>

# 2. Pull the image built by CI
docker pull <koda-registry-host>/<group>/amine:latest

# 3. Create the data and job directories
sudo mkdir -p /srv/amine/data /srv/amine/jobs

# 4. Run the service
docker run -d --restart unless-stopped \
  --name amine-web \
  -p 80:8000 \
  -v /srv/amine/data:/app/data \
  -v /srv/amine/jobs:/app/jobs \
  -e AMINE_SPECIES=human \
  -e AMINE_MAX_WORKERS=1 \
  <koda-registry-host>/<group>/amine:latest
```

The image pre-downloads the human STRING data at build time, so the first start
is fast. Put a reverse proxy (Caddy or nginx) in front for HTTPS.

### C.5 Updating

Push to Koda; CI rebuilds and pushes `:latest`. On the VM:

```bash
docker pull <koda-registry-host>/<group>/amine:latest
docker stop amine-web && docker rm amine-web
# re-run the `docker run` command from C.4
```

### C.6 (Optional) Mirror to GitHub

To keep a public mirror and use GitHub Pages for a static description:

```bash
git remote add github git@github.com:<org>/amine.git
git push github main
```

The GitHub Actions workflows in [`.github/workflows/`](../.github/workflows/)
run the same tests and build the image.

---

## Quick reference

| Task | Command |
| ---- | ------- |
| Run tests | `pytest tests/ -q` |
| Download data | `python -m amine.download_data --specie human --skip-biogrid --skip-intact` |
| Run CLI | `python -m amine -x <file> -g 0 -p 2 -s human -n string -o out.xlsx` |
| Run web app | `uvicorn web.api.main:app --reload` |
| Build image | `docker build -t amine-web .` |
| Run image | `docker run -p 8000:8000 -v amine-data:/app/data -v amine-jobs:/app/jobs amine-web` |

See also [`docs/deployment.md`](deployment.md) for the technical requirements
and generic deployment options, and [`web/README.md`](../web/README.md) for
the HTTP API.
