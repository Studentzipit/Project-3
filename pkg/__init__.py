"""Package for word count and citation count lookups."""
from .lookup import get_word_count, get_citation_count, lookup_work
from .openalex import search_works_by_author, search_works_by_institution, search_works_by_topic
