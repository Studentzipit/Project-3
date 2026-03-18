"""Search OpenAlex for works by author or institution."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
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


def _set_mailto(mailto: Optional[str]) -> None:
    """Update the User-Agent with a mailto address for the polite pool."""
    global _USER_AGENT
    if mailto:
        _USER_AGENT = f"word-citation-lookup/1.0 (mailto:{mailto})"


# ── author resolution ──────────────────────────────────────────────────────────

def _resolve_author_id(author_name: str) -> str:
    """
    Return the OpenAlex author ID for *author_name*.

    Uses the stricter ``display_name.search`` filter and fetches several
    candidates so an exact case-insensitive name match can be preferred over
    an arbitrary fuzzy top-hit.

    Raises:
        ValueError: if no author is found.
    """
    params = urllib.parse.urlencode({
        "filter": f"display_name.search:{author_name}",
        "per_page": 5,
    })
    url = f"{_BASE}/authors?{params}"
    data = _rate_limited_get(url)
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No OpenAlex author found for: {author_name!r}")

    # Prefer an exact case-insensitive display_name match
    needle = author_name.lower()
    for candidate in results:
        if candidate.get("display_name", "").lower() == needle:
            return candidate["id"]

    # Fall back to the top-ranked result but warn the caller
    best = results[0]
    warnings.warn(
        f"No exact name match for {author_name!r}; "
        f"using closest result {best.get('display_name')!r} (id={best['id']}). "
        f"Results may include works by a different person.",
        stacklevel=3,
    )
    return best["id"]


# ── institution resolution ─────────────────────────────────────────────────────

def _resolve_institution_id(institution_name: str) -> str:
    """
    Return the OpenAlex institution ID for *institution_name*.

    Uses ``display_name.search`` for strict filtering and prefers an exact
    case-insensitive match among the top candidates.

    Raises:
        ValueError: if no institution is found.
    """
    params = urllib.parse.urlencode({
        "filter": f"display_name.search:{institution_name}",
        "per_page": 5,
    })
    url = f"{_BASE}/institutions?{params}"
    data = _rate_limited_get(url)
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No OpenAlex institution found for: {institution_name!r}")

    needle = institution_name.lower()
    for candidate in results:
        if candidate.get("display_name", "").lower() == needle:
            return candidate["id"]

    best = results[0]
    warnings.warn(
        f"No exact name match for {institution_name!r}; "
        f"using closest result {best.get('display_name')!r} (id={best['id']}). "
        f"Results may reflect a different institution.",
        stacklevel=3,
    )
    return best["id"]


# ── public functions ───────────────────────────────────────────────────────────

def search_works_by_author(
    author_name: str,
    max_results: int = 50,
    mailto: Optional[str] = None,
) -> list[dict]:
    """
    Search OpenAlex for works by *author_name*.

    Resolves the name to an OpenAlex author ID (preferring an exact
    ``display_name`` match), then fetches that author's works page-by-page.

    Args:
        author_name: Full name of the author, e.g. ``"Jennifer Doudna"``.
        max_results:  Maximum number of works to return (default 50).
                      Set to ``0`` to fetch all available works.
        mailto:       Optional e-mail for OpenAlex polite-pool routing.

    Returns:
        A list of dicts, each with::

            {"title": str, "year": int | None, "citation_count": int}

    Raises:
        ValueError:   if the author cannot be found.
        RuntimeError: if all retry attempts are exhausted.
    """
    _set_mailto(mailto)
    author_id = _resolve_author_id(author_name)
    return _fetch_works_for_entity("authorships.author.id", author_id, max_results)


def search_works_by_institution(
    institution_name: str,
    top_n: int = 10,
    mailto: Optional[str] = None,
) -> list[dict]:
    """
    Find an institution in OpenAlex and return its *top_n* most-cited works.

    The function resolves the institution name to an OpenAlex institution ID,
    fetches works affiliated with that institution sorted by citation count
    (descending), and returns the top results.

    Args:
        institution_name: Name of the institution, e.g.
                          ``"Carnegie Mellon University"``.
        top_n:            Number of top-cited works to return (default 10).
        mailto:           Optional e-mail for OpenAlex polite-pool routing.

    Returns:
        A list of up to *top_n* dicts, sorted by citation count descending::

            {"title": str, "year": int | None, "citation_count": int}

    Raises:
        ValueError:   if the institution cannot be found.
        RuntimeError: if all retry attempts are exhausted.
    """
    _set_mailto(mailto)
    institution_id = _resolve_institution_id(institution_name)

    # OpenAlex supports sort=cited_by_count:desc, so we can get the top
    # results in a single request (up to per_page=200).
    per_page = min(top_n, 200)
    params = urllib.parse.urlencode({
        "filter": f"authorships.institutions.id:{institution_id}",
        "select": "title,publication_year,cited_by_count",
        "sort": "cited_by_count:desc",
        "per_page": per_page,
        "page": 1,
    })
    url = f"{_BASE}/works?{params}"
    data = _rate_limited_get(url)

    works = []
    for item in data.get("results", [])[:top_n]:
        works.append({
            "title":          item.get("title") or "",
            "year":           item.get("publication_year"),
            "citation_count": item.get("cited_by_count", 0),
        })
    return works


def search_works_by_topic(
    query: str,
    top_n: int = 5,
    mailto: Optional[str] = None,
) -> list[dict]:
    """
    Return the *top_n* most-cited OpenAlex works matching a free-text query.

    Uses the ``/works?search=`` endpoint (full-text relevance search across
    title, abstract, and full text) combined with ``sort=cited_by_count:desc``
    so the API does the ranking server-side in a single request.

    Args:
        query:  Free-text search string, e.g. ``"density functional theory"``.
        top_n:  Number of top-cited works to return (default 5, max 200).
        mailto: Optional e-mail for OpenAlex polite-pool routing.

    Returns:
        A list of up to *top_n* dicts, sorted by citation count descending::

            {"title": str, "year": int | None, "citation_count": int}

    Raises:
        ValueError:   if no works are found for the query.
        RuntimeError: if all retry attempts are exhausted.
    """
    _set_mailto(mailto)
    per_page = min(top_n, 200)
    params = urllib.parse.urlencode({
        "search":   query,
        "select":   "title,publication_year,cited_by_count",
        "sort":     "cited_by_count:desc",
        "per_page": per_page,
        "page":     1,
    })
    url = f"{_BASE}/works?{params}"
    data = _rate_limited_get(url)
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No OpenAlex works found for query: {query!r}")
    return [
        {
            "title":          item.get("title") or "",
            "year":           item.get("publication_year"),
            "citation_count": item.get("cited_by_count", 0),
        }
        for item in results[:top_n]
    ]


# ── shared pagination helper ───────────────────────────────────────────────────

def _fetch_works_for_entity(
    filter_key: str,
    entity_id: str,
    max_results: int,
) -> list[dict]:
    """Paginate through /works filtered by *filter_key*=*entity_id*."""
    works: list[dict] = []
    page = 1
    per_page = min(max_results or 200, 200)

    while True:
        params = urllib.parse.urlencode({
            "filter": f"{filter_key}:{entity_id}",
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

        meta = data.get("meta", {})
        total = meta.get("count", 0)
        if len(works) >= total:
            break

        page += 1

    return works
