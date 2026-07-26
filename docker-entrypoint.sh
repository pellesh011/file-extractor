#!/bin/sh
set -e

pip install -e ".[dev]" --quiet

if [ "${DEBUGPY_ENABLE}" = "1" ]; then
    exec python -m debugpy --listen 0.0.0.0:"${DEBUGPY_PORT:-5678}" -m "$@"
else
    exec "$@"
fi
