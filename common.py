"""Shared settings and helpers for the GVWG newsletter search pipeline."""

import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
ISSUES_DIR = DATA_DIR / "issues"

SITE = "https://gvwg.ca"
LISTING_URL = f"{SITE}/content.aspx?page_id=22&club_id=182740&module_id=717502"
DOC_URL = SITE + "/docs.ashx?id={id}"

# Identify ourselves honestly. If ClubExpress bot protection blocks this,
# run the pipeline locally rather than disguising the client.
USER_AGENT = "GVWG-newsletter-search/1.0 (+https://github.com/GVWG/newsletter-search)"

REQUEST_DELAY_SECONDS = 2.0   # pause between downloads, to be polite to CE
TIMEOUT_SECONDS = 60
MAX_RETRIES = 3


class BlockedError(RuntimeError):
    """Raised when the site refuses us (403/429 or an HTML challenge page)."""


def http_get(url: str, session: requests.Session) -> requests.Response:
    """GET with retries and backoff. Raises BlockedError on refusal."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(5 * attempt)
            continue
        if resp.status_code in (403, 429):
            raise BlockedError(
                f"{url} returned HTTP {resp.status_code}. The site may be blocking "
                "automated requests; run the pipeline locally instead."
            )
        if resp.status_code >= 500:
            last_exc = RuntimeError(f"HTTP {resp.status_code} for {url}")
            time.sleep(5 * attempt)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Giving up on {url}: {last_exc}")


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s
