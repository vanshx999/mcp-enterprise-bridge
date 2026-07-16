#!/bin/bash
set -e

echo "Python version: $(python --version)"
echo "PORT: ${PORT:-8000}"

python3 << 'PYEOF'
import os, socket, re

url = os.environ.get("DATABASE_URL", "")
if url:
    masked = re.sub(r':([^@]+)@', ':***@', url)
    print(f"DATABASE_URL: {masked}")
    m = re.match(r'.*@([^:/]+)(?::(\d+))?[/?]', url)
    if m:
        host = m.group(1)
        port = int(m.group(2)) if m.group(2) else 5432
        print(f"  host: {host}, port: {port}")
        tried = [host]
        for suffix in ['.oregon.postgres.render.com', '.ohio.postgres.render.com', '.postgres.render.com']:
            tried.append(host + suffix)
        for h in tried:
            try:
                ips = socket.getaddrinfo(h, port)
                print(f"  DNS OK: {h} -> {ips[0][4]}")
                break
            except Exception:
                if h == tried[-1]:
                    print(f"  DNS FAILED: all tried")
    else:
        print(f"  Could not parse hostname from URL")
else:
    print("DATABASE_URL: not set")
PYEOF

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips=*
