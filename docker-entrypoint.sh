#!/bin/sh
set -e

pip install -e ".[dev]" --quiet

# Clean up stale Celery beat schedule (from previous crashed runs)
rm -f celerybeat-schedule

if [ "${DEBUGPY_ENABLE}" = "1" ]; then
    exec python -m debugpy --listen 0.0.0.0:"${DEBUGPY_PORT:-5678}" -m "$@"
else
    exec "$@"
fi
