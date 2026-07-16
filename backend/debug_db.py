import os
import socket

url = os.environ.get("DATABASE_URL", "")
ext_url = os.environ.get("DATABASE_URL_EXTERNAL", "")

for label, u in [("DATABASE_URL", url), ("DATABASE_URL_EXTERNAL", ext_url)]:
    if not u:
        print(f"{label}: not set")
        continue
    masked = u.split("@")[0].split(":")[0] + "://***@" + u.split("@")[-1]
    print(f"{label}: {masked}")
    host = u.split("@")[-1].split(":")[0]
    print(f"  host: {host}")
    try:
        ips = socket.getaddrinfo(host, 5432)
        print(f"  DNS resolves to: {ips[0][4]}")
    except Exception as e:
        print(f"  DNS FAILED: {e}")
        for suffix in [
            ".oregon.postgres.render.com",
            ".ohio.postgres.render.com",
            ".frankfurt.postgres.render.com",
            ".postgres.render.com",
        ]:
            try:
                ips = socket.getaddrinfo(host + suffix, 5432)
                print(f"  with '{suffix}' resolves to: {ips[0][4]}")
                break
            except Exception:
                print(f"  with '{suffix}' failed")
