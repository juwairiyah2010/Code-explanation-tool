#!/usr/bin/env bash
set -e

echo "==> Running Code Lore Container Entrypoint..."

# Ensure data directory exists with write permissions
mkdir -p data

# Run database migrations and bootstrap knowledge chunks if required
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "==> Verifying database and executing migrations..."
    python scripts/init_db.py
fi

echo "==> Starting application process: $@"
exec "$@"
