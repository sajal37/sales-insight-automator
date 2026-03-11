#!/usr/bin/env python3
"""Smoke test — verifies core v2 endpoints against a running backend.

Usage:
    python scripts/smoke_test.py [BASE_URL] [API_KEY]

Defaults:
    BASE_URL = http://localhost:8000
    API_KEY  = $API_KEY env var
"""

import os
import sys
import time
import urllib.error
import urllib.request
import json

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = sys.argv[2] if len(sys.argv) > 2 else os.getenv("API_KEY", "")

PASS = 0
FAIL = 0


def _req(method: str, path: str, *, headers: dict | None = None, body: bytes | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    hdrs = headers or {}
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()) if e.readable() else {}


def check(name: str, ok: bool) -> None:
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if ok:
        PASS += 1
    else:
        FAIL += 1


def main() -> None:
    print(f"\n=== Smoke Test — {BASE_URL} ===\n")

    # 1. Health
    code, data = _req("GET", "/api/v1/health")
    check("Health returns 200", code == 200)
    check("Health status healthy|degraded", data.get("status") in ("healthy", "degraded"))
    check("Health has version 2.0.0", data.get("version") == "2.0.0")
    check("Health has redis field", "redis" in data)
    check("Health has database field", "database" in data)

    # 2. Root
    code, data = _req("GET", "/")
    check("Root returns 200", code == 200)

    # 3. Swagger
    code, _ = _req("GET", "/docs")
    check("Swagger docs accessible", code == 200)

    # 4. Auth required
    code, _ = _req("POST", "/api/v1/upload")
    check("Upload without key → 401", code == 401)

    if not API_KEY:
        print("\n  [SKIP] Skipping authenticated tests (no API_KEY set)\n")
    else:
        auth = {"X-API-Key": API_KEY}

        # 5. Upload with a tiny CSV — creates a job
        boundary = "----SmokeTestBoundary"
        csv_content = (
            "Date,Product_Category,Region,Units_Sold,Unit_Price,Revenue,Status\r\n"
            "2026-01-05,Electronics,North,150,1200,180000,Shipped\r\n"
        )
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="smoke.csv"\r\n'
            f"Content-Type: text/csv\r\n\r\n"
            f"{csv_content}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="to_email"\r\n\r\n'
            f"smoke@example.com\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        upload_headers = {
            **auth,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        code, data = _req("POST", "/api/v1/upload", headers=upload_headers, body=body)
        check("Upload returns 200", code == 200)
        job_id = data.get("job_id", "")
        check("Upload returns job_id", bool(job_id))
        check("Upload returns status_url", "/api/v1/jobs/" in data.get("status_url", ""))

        # 6. Poll job status
        if job_id:
            code, data = _req("GET", f"/api/v1/jobs/{job_id}", headers=auth)
            check("Job status returns 200", code == 200)
            check("Job status has status field", "status" in data)

        # 7. Non-existent job → 404
        code, _ = _req("GET", "/api/v1/jobs/nonexistent999", headers=auth)
        check("Nonexistent job → 404", code == 404)

    # Summary
    total = PASS + FAIL
    print(f"\n=== Results: {PASS}/{total} passed ===\n")
    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
