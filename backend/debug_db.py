import os
import socket

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL: not set")
else:
    host = url.split("@")[-1].split(":")[0]
    print(f"DATABASE_URL host: {host}")
    try:
        ips = socket.getaddrinfo(host, 5432)
        print(f"DNS resolves to: {ips[0][4]}")
    except Exception as e:
        print(f"DNS FAILED: {e}")
        # Try common Render internal domains
        for suffix in [
            ".oregon.postgres.render.com",
            ".ohio.postgres.render.com",
            ".postgres.render.com",
        ]:
            try:
                ips = socket.getaddrinfo(host + suffix, 5432)
                print(f"  with '{suffix}' resolves to: {ips[0][4]}")
                break
            except Exception:
                print(f"  with '{suffix}' failed")
