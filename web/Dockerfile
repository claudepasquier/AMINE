# AMINE web application — container image.
#
# Build from the repository root:
#   docker build -f web/Dockerfile -t amine-web .
# Run (with persistent volumes for data and jobs):
#   docker run -p 8000:8000 \
#     -v amine-data:/app/data -v amine-jobs:/app/jobs amine-web
#
# The image installs the core package plus the optional "web" dependencies and
# serves the FastAPI application with uvicorn. It is compatible with free
# container hosts such as Render, Fly.io and Hugging Face Spaces.

FROM src.koda.cnrs.fr:443/dsi/dependency_proxy/containers/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AMINE_JOBS_DIR=/app/jobs \
    AMINE_DATA_DIR=/app/data

WORKDIR /app

# Install build dependencies required by some scientific wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the project metadata and sources.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY web ./web

# Install the package with the web extra.
RUN pip install ".[web]"

# Pre-download the STRING data for the species that will be served. Set
# AMINE_SPECIES to a space-separated list (default: human). Pass
# --build-arg AMINE_SPECIES="" to skip the download and fetch it at runtime
# (the entry point does this automatically when the data directory is empty).
ARG AMINE_SPECIES="human mouse drosophila"
RUN if [ -n "$AMINE_SPECIES" ]; then \
        python -m amine.download_data \
            $(for s in $AMINE_SPECIES; do echo --specie "$s"; done) \
            --skip-biogrid --skip-intact; \
    fi

# Data and job state are meant to live on persistent volumes when available.
VOLUME ["/app/data", "/app/jobs"]

EXPOSE 8000

# The entry point downloads the data if it is missing (for hosts without
# persistent storage) and then starts uvicorn on $PORT (default 8000).
RUN chmod +x web/start.sh
CMD ["sh", "web/start.sh"]
