#!/usr/bin/env python3
"""Tests for the permissive EPUB/PDF book corpus downloader."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from tooling import fetch_book_corpus as corpus


def test_default_manifest_covers_epub_and_pdf():
    entries = corpus.load_entries()
    formats = {entry.format for entry in entries}
    sources = {entry.source for entry in entries}

    assert formats == {"epub", "pdf"}
    assert {"Project Gutenberg", "OpenStax"} <= sources
    assert all(entry.license in corpus.PERMISSIVE_LICENSES for entry in entries)


def test_manifest_rejects_non_permissive_license():
    bad = corpus.CorpusEntry(
        id="bad",
        title="Bad",
        source="Example",
        format="pdf",
        license="CC-BY-NC-4.0",
        license_url="https://example.test/license",
        landing_url="https://example.test/book",
        url="https://example.test/book.pdf",
        dest="files/pdf/bad.pdf",
        scope_tags=("bad",),
    )

    with pytest.raises(ValueError, match="non-permissive"):
        corpus.validate_entries([bad])


def test_sniff_format_accepts_pdf_and_epub_magic_bytes():
    assert corpus.sniff_format(b"%PDF-1.7\n...") == "pdf"
    assert corpus.sniff_format(b"PK\x03\x04...") == "epub"
    assert corpus.sniff_format(b"not a book") == "unknown"


def test_resolve_openstax_entries_uses_api_pdf_url():
    payload = {
        "books": [
            {
                "slug": "books/test-book",
                "title": "Resolved Title",
                "high_resolution_pdf_url": "https://assets.example.test/book.pdf",
            }
        ]
    }

    def fake_fetch(url, _last_hit):
        assert url == corpus.OPENSTAX_BOOKS_API
        return corpus.json.dumps(payload).encode("utf-8"), "application/json", 200

    entry = corpus.CorpusEntry(
        id="openstax-test",
        title="Unresolved",
        source="OpenStax",
        format="pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        landing_url="https://openstax.org/details/books/test-book",
        openstax_slug="books/test-book",
        attribution="Test Book, OpenStax, CC BY 4.0",
        dest="files/pdf/openstax-test.pdf",
        scope_tags=("textbook",),
    )

    resolved = corpus.resolve_entries([entry], fetcher=fake_fetch)

    assert resolved[0].title == "Resolved Title"
    assert resolved[0].url == "https://assets.example.test/book.pdf"
