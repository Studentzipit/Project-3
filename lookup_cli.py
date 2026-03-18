#!/usr/bin/env python3
"""
CLI: look up word count and citation count for an academic work.

Usage examples
--------------
# Citation count by DOI
python lookup_cli.py --doi 10.1145/3173574.3174223

# Citation count by ArXiv ID
python lookup_cli.py --arxiv 1706.03762

# Citation count by title
python lookup_cli.py --title "Attention is all you need"

# Word count of a local file
python lookup_cli.py --file paper.txt

# Both: citation count (by title) + word count (from file)
python lookup_cli.py --title "Attention is all you need" --file paper.txt

# All works by an author (OpenAlex)
python lookup_cli.py --author "Jennifer Doudna"
python lookup_cli.py --author "Jennifer Doudna" --max-results 10

# Top-cited works from an institution (OpenAlex)
python lookup_cli.py --institution "Carnegie Mellon University"
python lookup_cli.py --institution "MIT" --top-n 5
"""

import argparse
import sys
from pkg.lookup import get_word_count, get_citation_count, lookup_work
from pkg.openalex import search_works_by_author, search_works_by_institution


def main():
    parser = argparse.ArgumentParser(
        description="Look up word count and/or citation count for an academic work."
    )
    id_group = parser.add_mutually_exclusive_group()
    id_group.add_argument("--doi",    metavar="DOI",    help="Paper DOI, e.g. 10.1145/3173574.3174223")
    id_group.add_argument("--arxiv",  metavar="ID",     help="ArXiv ID, e.g. 1706.03762")
    id_group.add_argument("--title",  metavar="TITLE",  help="Paper title (free-text search)")
    id_group.add_argument("--author",      metavar="AUTHOR", help="Author name — lists all works via OpenAlex")
    id_group.add_argument("--institution", metavar="NAME",   help="Institution name — lists top-cited works via OpenAlex")
    parser.add_argument("--max-results", metavar="N", type=int, default=50,
                        help="Max works to return for --author (default 50; 0 = all)")
    parser.add_argument("--top-n", metavar="N", type=int, default=10,
                        help="Number of top-cited works for --institution (default 10)")
    parser.add_argument("--mailto", metavar="EMAIL",
                        help="Your e-mail for OpenAlex polite-pool routing")
    parser.add_argument("--file", metavar="PATH", help="Path to a text file to count words in")
    parser.add_argument("--text", metavar="TEXT", help="Inline text to count words in")

    args = parser.parse_args()

    # ── author search via OpenAlex ─────────────────────────────────────────────
    if args.author:
        try:
            works = search_works_by_author(
                args.author,
                max_results=args.max_results,
                mailto=args.mailto,
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        if not works:
            print("No works found.")
            return

        print(f"{'#':<4} {'Year':<6} {'Citations':<10} Title")
        print("-" * 80)
        for i, w in enumerate(works, 1):
            year = w["year"] or "n/a"
            print(f"{i:<4} {str(year):<6} {w['citation_count']:<10} {w['title']}")
        print(f"\n{len(works)} work(s) found for author: {args.author!r}")
        return

    # ── institution search via OpenAlex ───────────────────────────────────────
    if args.institution:
        try:
            works = search_works_by_institution(
                args.institution,
                top_n=args.top_n,
                mailto=args.mailto,
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        if not works:
            print("No works found.")
            return

        print(f"Top {len(works)} most-cited works for: {args.institution!r}")
        print(f"{'#':<4} {'Year':<6} {'Citations':<10} Title")
        print("-" * 80)
        for i, w in enumerate(works, 1):
            year = w["year"] or "n/a"
            print(f"{i:<4} {str(year):<6} {w['citation_count']:<10} {w['title']}")
        return

    # ── word count only ────────────────────────────────────────────────────────
    if not any([args.doi, args.arxiv, args.title]):
        if args.file:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
            print(f"Word count: {get_word_count(text)}")
        elif args.text:
            print(f"Word count: {get_word_count(args.text)}")
        else:
            parser.print_help()
            sys.exit(1)
        return

    # ── build query ────────────────────────────────────────────────────────────
    if args.doi:
        query = args.doi
    elif args.arxiv:
        query = args.arxiv
    else:
        query = args.title

    # ── optional text for word count ───────────────────────────────────────────
    text = None
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    elif args.text:
        text = args.text

    # ── perform lookup ─────────────────────────────────────────────────────────
    try:
        result = lookup_work(query, text)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── print results ──────────────────────────────────────────────────────────
    print(f"Title:          {result['title']}")
    print(f"Authors:        {', '.join(result['authors'])}")
    print(f"Year:           {result['year']}")
    print(f"Citations:      {result['citation_count']}")
    if result.get("url"):
        print(f"URL:            {result['url']}")
    if "word_count" in result:
        print(f"Word count:     {result['word_count']}")


if __name__ == "__main__":
    main()
