"""Report run status to healthchecks.io. Does nothing if HEALTHCHECK_URL is unset.

Success pings the check URL; failure pings <url>/fail with the error text.
If no ping arrives on schedule (computer off, cron dead), healthchecks.io alerts you.
A failing alert must never break the scrape itself, so errors here are swallowed.
"""
import os
import urllib.request


def ping(ok: bool, message: str = "") -> None:
    base = os.environ.get("HEALTHCHECK_URL", "").strip().rstrip("/")
    if not base:
        return
    url = base if ok else base + "/fail"
    try:
        req = urllib.request.Request(url, data=message[-10000:].encode("utf-8"), method="POST")
        urllib.request.urlopen(req, timeout=10).close()
    except Exception as e:
        print(f"healthcheck ping failed: {e}")
