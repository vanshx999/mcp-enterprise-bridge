#!/bin/bash
set -e

echo "Python version: $(python --version)"
echo "PORT: ${PORT:-8000}"
if [ -n "$DATABASE_URL" ]; then
  echo "DATABASE_URL: ${DATABASE_URL:0:30}... (truncated)"
  DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:/]*\).*/\1/p')
  echo "DB host: $DB_HOST"
  getent hosts "$DB_HOST" && echo "DB hostname resolves" || echo "DB hostname DOES NOT resolve"
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips=*
