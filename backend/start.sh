#!/bin/bash
set -e

echo "Python version: $(python --version)"
echo "PORT: ${PORT:-8000}"
if [ -n "$DATABASE_URL" ]; then
  DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:/]*\).*/\1/p')
  echo "DB host extracted: $DB_HOST"
  echo "Full URL scheme+host: $(echo "$DATABASE_URL" | sed 's/[^:@]*@/***@/')"
  python3 -c "
import socket
try:
    addr = socket.getaddrinfo('$DB_HOST', 5432)
    print(f'DNS resolves to: {addr[0][4]}')
except Exception as e:
    print(f'DNS resolution failed: {e}')
"
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips=*
