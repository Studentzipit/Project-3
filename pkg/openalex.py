"""Search OpenAlex for works by a given author."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

# OpenAlex asks for a mailto in the User-Agent for the "polite pool"
_USER_AGENT = "word-citation-lookup/1.0 (mailto:example@example.com)"
_BASE = "https://api.openalex.org"

# Rate-limit: stay well inside the 10 req/s polite-pool limit
_REQUEST_INTERVAL = 0.11   # seconds between requests (~9 req/s)
_last_request_time: float = 0.0


# ── low-level helpers ──────────────────────────────────────────────────────────

def _rate_limited_get(url: str, retries: int = 3) -> dict:
    """
    Fetch *url* as JSON, honouring rate limits and retrying on transient errors.

    Raises:
        urllib.error.HTTPError: on 4xx errors (not retried).
        RuntimeError: if all retries are exhausted on 5xx / network errors.
    """
    global _last_request_time

    # Enforce minimum gap between requests
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _REQUEST_INTERVAL:
        time.sleep(_REQUEST_INTERVAL - elapsed)

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            _last_request_time = time.monotonic()
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                # Respect Retry-After header if present, otherwise back off
                retry_after = float(exc.headers.get("Retry-After", delay))
                if attempt < retries:
                    time.sleep(retry_after)
                    delay *= 2
                    continue
            raise  # 4xx errors other than 429 are not retried
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(
                f"Request failed after {retries} attempts: {exc}"
            ) from exc

    raise RuntimeError(f"Request failed after {retries} attempts")  # pragma: no cover


# ── author resolution ──────────────────────────────────────────────────────────

def _resolve_author_id(author_name: str) -> str:
    """
    Return the OpenAlex author ID for the best match of *author_name*.

    Raises:
        ValueError: if no author is found.
    """
    params = urllib.parse.urlencode({"search": author_name, "per_page": 1})
    url = f"{_BASE}/authors?{params}"
    data = _rate_limited_get(url)
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No OpenAlex author found for: {author_name!r}")
    author = results[0]
    return author["id"]  # e.g. "https://openalex.org/A12345678"


# ── main public function ───────────────────────────────────────────────────────

def search_works_by_author(
    author_name: str,
    max_results: int = 50,
    mailto: Optional[str] = None,
) -> list[dict]:
    """
    Search OpenAlex for works by *author_name*.

    The function first resolves the name to an OpenAlex author ID, then fetches
    that author's works page-by-page.

    Args:
        author_name: Full name of the author, e.g. ``"Jennifer Doudna"``.
        max_results:  Maximum number of works to return (default 50).
                      Set to ``0`` or ``None`` to fetch all available works.
        mailto:       Optional e-mail address appended to the User-Agent so
                      OpenAlex routes requests through the polite pool.

    Returns:
        A list of dicts, each with::

            {
                "title":          str,
                "year":           int | None,
                "citation_count": int,
            }

    Raises:
        ValueError:   if the author cannot be found.
        RuntimeError: if all retry attempts are exhausted.
    """
    global _USER_AGENT
    if mailto:
        _USER_AGENT = f"word-citation-lookup/1.0 (mailto:{mailto})"

    author_id = _resolve_author_id(author_name)

    works: list[dict] = []
    page = 1
    per_page = min(max_results or 200, 200)  # OpenAlex max per_page is 200

    while True:
        params = urllib.parse.urlencode({
            "filter": f"author.id:{author_id}",
            "select": "title,publication_year,cited_by_count",
            "per_page": per_page,
            "page": page,
        })
        url = f"{_BASE}/works?{params}"
        data = _rate_limited_get(url)

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            works.append({
                "title":          item.get("title") or "",
                "year":           item.get("publication_year"),
                "citation_count": item.get("cited_by_count", 0),
            })
            if max_results and len(works) >= max_results:
                return works

        # Stop if we've received the last page
        meta = data.get("meta", {})
        total = meta.get("count", 0)
        if len(works) >= total:
            break

        page += 1

    return works
