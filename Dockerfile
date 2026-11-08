# Root Dockerfile for hosts that require the build definition at the repository
# root (e.g. Hugging Face Spaces, Google Cloud Run, generic PaaS).
#
# NOTE: this file is kept in sync with web/Dockerfile, which is the canonical
# definition used by Render and the CI workflow. If you change one, change the
# other.
#
# Build from the repository root:
#   docker build -t amine-web .
# Run:
#   docker run -p 8000:8000 -v amine-data:/app/data -v amine-jobs:/app/jobs amine-web

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AMINE_JOBS_DIR=/app/jobs \
    AMINE_DATA_DIR=/app/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY web ./web

RUN pip install ".[web]"

# Pre-download the STRING data for the species that will be served. Set
# AMINE_SPECIES to a space-separated list (default: human). Pass
# --build-arg AMINE_SPECIES="" to skip the download and fetch it at runtime.
ARG AMINE_SPECIES="human mouse drosophila"
RUN if [ -n "$AMINE_SPECIES" ]; then \
        python -m amine.download_data \
            $(for s in $AMINE_SPECIES; do echo --specie "$s"; done) \
            --skip-biogrid --skip-intact; \
    fi

VOLUME ["/app/data", "/app/jobs"]

EXPOSE 8000

RUN chmod +x web/start.sh
CMD ["sh", "web/start.sh"]
