"""Functions to look up word count and citation count for academic works."""

import re
import urllib.request
import urllib.parse
import json


def get_word_count(text: str) -> int:
    """Count the number of words in a text string."""
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def get_citation_count(query: str) -> dict:
    """
    Look up citation count for an academic work via the Semantic Scholar API.

    Args:
        query: A DOI (e.g. '10.1145/...'), ArXiv ID (e.g. 'arXiv:2301.00001'),
               or paper title string.

    Returns:
        dict with keys: title, authors, year, citation_count, url
    """
    # Detect query type and build the appropriate API URL
    if query.startswith("10.") and "/" in query:
        # DOI
        paper_id = f"DOI:{query}"
    elif re.match(r"^(arxiv:)?\d{4}\.\d{4,5}(v\d+)?$", query, re.IGNORECASE):
        # ArXiv ID
        arxiv_id = re.sub(r"^arxiv:", "", query, flags=re.IGNORECASE)
        paper_id = f"ARXIV:{arxiv_id}"
    else:
        # Search by title
        return _search_by_title(query)

    url = f"https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(paper_id)}"
    url += "?fields=title,authors,year,citationCount,externalIds,url"
    return _fetch_paper(url)


def _search_by_title(title: str) -> dict:
    """Search Semantic Scholar by title and return the top result."""
    params = urllib.parse.urlencode({
        "query": title,
        "fields": "title,authors,year,citationCount,externalIds,url",
        "limit": 1,
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "word-citation-lookup/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    papers = data.get("data", [])
    if not papers:
        raise ValueError(f"No results found for title: {title!r}")
    return _format_paper(papers[0])


def _fetch_paper(url: str) -> dict:
    """Fetch a paper by its Semantic Scholar API URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "word-citation-lookup/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    return _format_paper(data)


def _format_paper(data: dict) -> dict:
    """Normalize a Semantic Scholar paper record."""
    authors = [a.get("name", "") for a in data.get("authors", [])]
    return {
        "title": data.get("title", ""),
        "authors": authors,
        "year": data.get("year"),
        "citation_count": data.get("citationCount", 0),
        "url": data.get("url", ""),
    }


def lookup_work(query: str, text: str | None = None) -> dict:
    """
    Combined lookup: citation count for a work plus optional word count.

    Args:
        query: DOI, ArXiv ID, or paper title.
        text:  Optional full text of the paper to count words in.

    Returns:
        dict with citation info and, if text is provided, word_count.
    """
    result = get_citation_count(query)
    if text is not None:
        result["word_count"] = get_word_count(text)
    return result
