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
"""

import argparse
import sys
from pkg.lookup import get_word_count, get_citation_count, lookup_work


def main():
    parser = argparse.ArgumentParser(
        description="Look up word count and/or citation count for an academic work."
    )
    id_group = parser.add_mutually_exclusive_group()
    id_group.add_argument("--doi",   metavar="DOI",   help="Paper DOI, e.g. 10.1145/3173574.3174223")
    id_group.add_argument("--arxiv", metavar="ID",    help="ArXiv ID, e.g. 1706.03762")
    id_group.add_argument("--title", metavar="TITLE", help="Paper title (free-text search)")
    parser.add_argument("--file", metavar="PATH", help="Path to a text file to count words in")
    parser.add_argument("--text", metavar="TEXT", help="Inline text to count words in")

    args = parser.parse_args()

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
