#!/bin/sh
# Container entry point for the AMINE web application.
#
# On hosts without persistent storage (e.g. Hugging Face Spaces, Cloud Run) the
# interaction networks are downloaded on first start. On hosts with a volume
# the download is skipped because the data is already present.
#
# Environment variables:
#   AMINE_DATA_DIR   where the networks are stored (default /app/data)
#   AMINE_SPECIES    space-separated species to fetch (default "human")
#   PORT             HTTP port to bind (default 8000; HF Spaces uses 7860)
set -e

DATA_DIR="${AMINE_DATA_DIR:-/app/data}"
# All three supported species are downloaded by default so that the web form
# can serve human, mouse and drosophila out of the box.
SPECIES="${AMINE_SPECIES:-human mouse drosophila}"

# Hugging Face Spaces sets SPACE_ID and expects the app on port 7860.
if [ -n "$SPACE_ID" ]; then
    PORT="${PORT:-7860}"
else
    PORT="${PORT:-8000}"
fi

PPI_DIR="$DATA_DIR/real/ppi"

if [ ! -d "$PPI_DIR" ] || [ -z "$(ls -A "$PPI_DIR" 2>/dev/null)" ]; then
    echo "No interaction data found in $PPI_DIR; downloading for: $SPECIES"
    # shellcheck disable=SC2086
    python -m amine.download_data \
        $(for s in $SPECIES; do echo --specie "$s"; done) \
        --skip-biogrid --skip-intact
else
    echo "Using existing interaction data in $PPI_DIR"
fi

exec uvicorn web.api.main:app --host 0.0.0.0 --port "$PORT"
