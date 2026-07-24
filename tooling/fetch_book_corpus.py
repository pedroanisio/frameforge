#!/usr/bin/env python3
"""Download a permissively licensed book corpus for EPUB/PDF inspection.

The corpus is intentionally small and format-diverse. It is not a training
dataset; it is a product/API pressure set for book import work:

* Project Gutenberg EPUBs exercise narrative books, chapters, front matter,
  images, poetry/prose rhythm, and public-domain licensing constraints.
* OpenStax PDFs exercise textbook layout: dense headings, figures, captions,
  tables, formulas, sidebars, references, and page-level typography.

Downloads go to ``_tmp/book-corpus`` by default so large third-party binaries do
not become repo changes by accident. The script writes a lockfile, provenance
table, and scope report beside the downloaded files.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_OUT = ROOT / "_tmp" / "book-corpus"
OPENSTAX_BOOKS_API = "https://openstax.org/apps/cms/api/books/?format=json"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
RETRIES = 4
BACKOFF_SECONDS = 2.0
HOST_INTERVAL_SECONDS = 1.0

PERMISSIVE_LICENSES = {
    "PD-US": "Public domain in the United States / unrestricted under U.S. copyright law",
    "CC0-1.0": "Creative Commons CC0 1.0 public-domain dedication",
    "CC-BY-4.0": "Creative Commons Attribution 4.0 International",
    "CC-BY-3.0": "Creative Commons Attribution 3.0 Unported",
}


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    title: str
    source: str
    format: str
    license: str
    license_url: str
    landing_url: str
    dest: str
    scope_tags: tuple[str, ...]
    attribution: str = ""
    url: str = ""
    openstax_slug: str = ""


DEFAULT_ENTRIES: tuple[CorpusEntry, ...] = (
    CorpusEntry(
        id="pg-alice",
        title="Alice's Adventures in Wonderland",
        source="Project Gutenberg",
        format="epub",
        license="PD-US",
        license_url="https://www.gutenberg.org/policy/license.html",
        landing_url="https://www.gutenberg.org/ebooks/11",
        url="https://www.gutenberg.org/ebooks/11.epub3.images",
        dest="files/epub/pg-alice.epub",
        scope_tags=("narrative", "illustrations", "chapters", "public-domain"),
    ),
    CorpusEntry(
        id="pg-frankenstein",
        title="Frankenstein; Or, The Modern Prometheus",
        source="Project Gutenberg",
        format="epub",
        license="PD-US",
        license_url="https://www.gutenberg.org/policy/license.html",
        landing_url="https://www.gutenberg.org/ebooks/84",
        url="https://www.gutenberg.org/ebooks/84.epub3.images",
        dest="files/epub/pg-frankenstein.epub",
        scope_tags=("narrative", "front-matter", "letters", "chapters"),
    ),
    CorpusEntry(
        id="pg-moby-dick",
        title="Moby-Dick; Or, The Whale",
        source="Project Gutenberg",
        format="epub",
        license="PD-US",
        license_url="https://www.gutenberg.org/policy/license.html",
        landing_url="https://www.gutenberg.org/ebooks/2701",
        url="https://www.gutenberg.org/ebooks/2701.epub3.images",
        dest="files/epub/pg-moby-dick.epub",
        scope_tags=("narrative", "long-form", "chapter-density", "epigraphs"),
    ),
    CorpusEntry(
        id="pg-sherlock-holmes",
        title="The Adventures of Sherlock Holmes",
        source="Project Gutenberg",
        format="epub",
        license="PD-US",
        license_url="https://www.gutenberg.org/policy/license.html",
        landing_url="https://www.gutenberg.org/ebooks/1661",
        url="https://www.gutenberg.org/ebooks/1661.epub3.images",
        dest="files/epub/pg-sherlock-holmes.epub",
        scope_tags=("short-stories", "toc", "chapter-boundaries"),
    ),
    CorpusEntry(
        id="openstax-biology-2e",
        title="Biology 2e",
        source="OpenStax",
        format="pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        landing_url="https://openstax.org/details/books/biology-2e",
        openstax_slug="books/biology-2e",
        attribution="Biology 2e, OpenStax, Rice University, CC BY 4.0",
        dest="files/pdf/openstax-biology-2e.pdf",
        scope_tags=("textbook", "figures", "tables", "captions", "science"),
    ),
    CorpusEntry(
        id="openstax-astronomy-2e",
        title="Astronomy 2e",
        source="OpenStax",
        format="pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        landing_url="https://openstax.org/details/books/astronomy-2e",
        openstax_slug="books/astronomy-2e",
        attribution="Astronomy 2e, OpenStax, Rice University, CC BY 4.0",
        dest="files/pdf/openstax-astronomy-2e.pdf",
        scope_tags=("textbook", "figures", "equations", "tables", "science"),
    ),
    CorpusEntry(
        id="openstax-college-physics-2e",
        title="College Physics 2e",
        source="OpenStax",
        format="pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        landing_url="https://openstax.org/details/books/college-physics-2e",
        openstax_slug="books/college-physics-2e",
        attribution="College Physics 2e, OpenStax, Rice University, CC BY 4.0",
        dest="files/pdf/openstax-college-physics-2e.pdf",
        scope_tags=("textbook", "formulas", "figures", "worked-examples"),
    ),
    CorpusEntry(
        id="openstax-writing-guide",
        title="Writing Guide with Handbook",
        source="OpenStax",
        format="pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        landing_url="https://openstax.org/details/books/writing-guide",
        openstax_slug="books/writing-guide",
        attribution="Writing Guide with Handbook, OpenStax, Rice University, CC BY 4.0",
        dest="files/pdf/openstax-writing-guide.pdf",
        scope_tags=("textbook", "prose", "tables", "callouts", "references"),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_entries(path: Path | None = None) -> list[CorpusEntry]:
    if path is None:
        entries = list(DEFAULT_ENTRIES)
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = raw.get("entries", raw if isinstance(raw, list) else [])
        entries = [CorpusEntry(**_normalize_record(record)) for record in records]
    validate_entries(entries)
    return entries


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    data = dict(record)
    tags = data.get("scope_tags", ())
    if isinstance(tags, list):
        data["scope_tags"] = tuple(str(tag) for tag in tags)
    return data


def validate_entries(entries: list[CorpusEntry]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry.id in seen:
            raise ValueError(f"duplicate corpus entry id: {entry.id}")
        seen.add(entry.id)
        if entry.format not in {"epub", "pdf"}:
            raise ValueError(f"{entry.id}: unsupported format {entry.format!r}")
        if entry.license not in PERMISSIVE_LICENSES:
            raise ValueError(f"{entry.id}: non-permissive or unknown license {entry.license!r}")
        if not entry.url and not entry.openstax_slug:
            raise ValueError(f"{entry.id}: needs either url or openstax_slug")
        if entry.license.startswith("CC-BY") and not entry.attribution:
            raise ValueError(f"{entry.id}: {entry.license} requires attribution")


def select_entries(entries: list[CorpusEntry], ids: list[str] | None, formats: list[str] | None) -> list[CorpusEntry]:
    selected = entries
    if ids:
        wanted = set(ids)
        selected = [entry for entry in selected if entry.id in wanted]
    if formats:
        allowed = set(formats)
        selected = [entry for entry in selected if entry.format in allowed]
    return selected


def resolve_entries(entries: list[CorpusEntry], fetcher=None) -> list[CorpusEntry]:
    fetch = fetcher or download_bytes
    needs_openstax = [entry for entry in entries if entry.openstax_slug]
    if not needs_openstax:
        return entries
    body, _ctype, _status = fetch(OPENSTAX_BOOKS_API, {})
    data = json.loads(body.decode("utf-8"))
    by_slug = {book["slug"]: book for book in data.get("books", [])}
    resolved: list[CorpusEntry] = []
    for entry in entries:
        if not entry.openstax_slug:
            resolved.append(entry)
            continue
        book = by_slug.get(entry.openstax_slug)
        if not book:
            raise ValueError(f"{entry.id}: OpenStax slug not found: {entry.openstax_slug}")
        url = book.get("high_resolution_pdf_url") or book.get("low_resolution_pdf_url")
        if not url:
            raise ValueError(f"{entry.id}: OpenStax book has no PDF URL")
        resolved.append(
            CorpusEntry(
                **{
                    **asdict(entry),
                    "title": book.get("title") or entry.title,
                    "url": url,
                    "scope_tags": tuple(entry.scope_tags),
                }
            )
        )
    return resolved


def download_bytes(url: str, last_hit: dict[str, float]) -> tuple[bytes, str, int]:
    host = urlsplit(url).netloc
    err: Exception | None = None
    for attempt in range(RETRIES):
        wait = HOST_INTERVAL_SECONDS - (time.monotonic() - last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                status = resp.status
            last_hit[host] = time.monotonic()
            return body, ctype, status
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            err = exc
            last_hit[host] = time.monotonic()
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF_SECONDS * (2 ** attempt))
    raise err  # type: ignore[misc]


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sniff_format(body: bytes) -> str:
    if body.startswith(b"%PDF"):
        return "pdf"
    if body.startswith(b"PK\x03\x04"):
        return "epub"
    return "unknown"


def load_lock(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "lockfile.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"files": {}}


def save_lock(out_dir: Path, lock: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lockfile.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_entries(entries: list[CorpusEntry], out_dir: Path, *, force: bool, dry_run: bool) -> int:
    lock = load_lock(out_dir)
    files = lock.setdefault("files", {})
    last_hit: dict[str, float] = {}
    failures = 0
    downloaded = skipped = 0

    resolved = resolve_entries(entries)
    if dry_run:
        print_entries(resolved, include_urls=True)
        write_scope(out_dir, resolved, files, dry_run=True)
        return 0

    for entry in resolved:
        dest = out_dir / entry.dest
        previous = files.get(entry.id)
        if not force and previous and dest.exists() and sha256_file(dest) == previous.get("sha256"):
            print(f"  skip  {entry.id:<32} {entry.format:<4} up to date")
            skipped += 1
            continue
        try:
            body, ctype, status = download_bytes(entry.url, last_hit)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {entry.id:<32} {type(exc).__name__}: {exc}")
            failures += 1
            continue
        actual = sniff_format(body)
        if actual != entry.format:
            print(f"  FAIL  {entry.id:<32} expected {entry.format}, got {actual} ({ctype})")
            failures += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        files[entry.id] = {
            **asdict(entry),
            "scope_tags": list(entry.scope_tags),
            "bytes": len(body),
            "sha256": sha256_bytes(body),
            "content_type": ctype,
            "http_status": status,
            "fetched_at": utc_now(),
        }
        print(f"  ok    {entry.id:<32} {entry.format:<4} {len(body):>10,} B  {ctype}")
        downloaded += 1

    lock["generated_at"] = utc_now()
    save_lock(out_dir, lock)
    write_provenance(out_dir, resolved, files)
    write_scope(out_dir, resolved, files, dry_run=False)
    print(f"\n{downloaded} downloaded, {skipped} up-to-date, {failures} failed.")
    return 1 if failures else 0


def check_entries(entries: list[CorpusEntry], out_dir: Path) -> int:
    lock = load_lock(out_dir)
    files = lock.get("files", {})
    bad = 0
    for entry in entries:
        rec = files.get(entry.id)
        dest = out_dir / entry.dest
        if not rec:
            print(f"  MISSING-LOCK  {entry.id}")
            bad += 1
        elif not dest.exists():
            print(f"  MISSING-FILE  {entry.id} -> {entry.dest}")
            bad += 1
        elif sha256_file(dest) != rec.get("sha256"):
            print(f"  DRIFT         {entry.id}")
            bad += 1
        else:
            print(f"  ok            {entry.id}")
    if bad:
        print(f"\nFAIL: {bad} book corpus file(s) missing or drifted.")
        return 1
    print(f"\nOK: {len(entries)} book corpus file(s) match {out_dir / 'lockfile.json'}.")
    return 0


def print_entries(entries: list[CorpusEntry], *, include_urls: bool) -> None:
    for entry in entries:
        suffix = f" {entry.url}" if include_urls else ""
        print(f"  {entry.id:<32} {entry.format:<4} {entry.license:<10} {entry.title}{suffix}")
    print(f"\n{len(entries)} entries.")


def write_provenance(out_dir: Path, entries: list[CorpusEntry], files: dict[str, Any]) -> None:
    rows = []
    for entry in entries:
        rec = files.get(entry.id)
        digest = f"`{rec['sha256'][:12]}...`" if rec else "not downloaded"
        size = f"{rec['bytes']:,}" if rec else "not downloaded"
        attr = entry.attribution or "-"
        rows.append(
            f"| `{entry.dest}` | {entry.format} | [{entry.license}]({entry.license_url}) "
            f"| {entry.source} | {attr} | {size} | {digest} |"
        )
    text = "\n".join(
        [
            "# Book Corpus Provenance",
            "",
            "<!-- GENERATED by tooling/fetch_book_corpus.py; do not hand-edit. -->",
            "",
            "This corpus is intended for EPUB/PDF import inspection, not for redistribution as a product bundle.",
            "",
            "| File | Format | License | Source | Attribution | Bytes | sha256 |",
            "|---|---|---|---|---|---:|---|",
            *rows,
            "",
            "## License Policy",
            "",
            "- Accept only public-domain/CC0 or attribution-only Creative Commons entries.",
            "- Reject NonCommercial, NoDerivatives, and unknown licenses by default.",
            "- Keep Project Gutenberg trademark/license constraints in mind if redistributing unmodified files.",
            "",
        ]
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "PROVENANCE.md").write_text(text, encoding="utf-8")


def write_scope(out_dir: Path, entries: list[CorpusEntry], files: dict[str, Any], *, dry_run: bool) -> None:
    formats = sorted({entry.format for entry in entries})
    sources = sorted({entry.source for entry in entries})
    tags = sorted({tag for entry in entries for tag in entry.scope_tags})
    downloaded = sum(1 for entry in entries if entry.id in files)
    mode = "dry-run preview" if dry_run else "downloaded corpus"
    lines = [
        "# Book Corpus Scope Inspection",
        "",
        "<!-- GENERATED by tooling/fetch_book_corpus.py; do not hand-edit. -->",
        "",
        f"Mode: **{mode}**.",
        "",
        f"- Entries: {len(entries)}",
        f"- Downloaded entries in lockfile: {downloaded}",
        f"- Formats: {', '.join(formats)}",
        f"- Sources: {', '.join(sources)}",
        f"- Scope tags: {', '.join(tags)}",
        "",
        "## Coverage Matrix",
        "",
        "| Entry | Format | Source | Scope pressure |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        lines.append(f"| `{entry.id}` | {entry.format} | {entry.source} | {', '.join(entry.scope_tags)} |")
    lines += [
        "",
        "## Scope Assessment",
        "",
        "This starter set is enough to inspect the first import surface if the goal is to answer:",
        "",
        "- Can FrameForge ingest EPUB spine/chapter structure and preserve semantic text runs?",
        "- Can FrameForge ingest PDF page geometry, text blocks, images, tables, formulas, and captions?",
        "- Can imported books be lowered to live FrameForge pages without raster-only shortcuts?",
        "",
        "It is not enough yet for OCR-only scans, right-to-left scripts, math-heavy EPUB, magazines, or DRM/proprietary formats.",
        "",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SCOPE.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory (default: _tmp/book-corpus)")
    parser.add_argument("--manifest", help="optional JSON manifest replacing the embedded starter set")
    parser.add_argument("--id", action="append", help="download/check one entry id; repeatable")
    parser.add_argument("--format", choices=["epub", "pdf"], action="append", help="restrict by format; repeatable")
    parser.add_argument("--list", action="store_true", help="list selected entries without network")
    parser.add_argument("--dry-run", action="store_true", help="resolve URLs and write scope report, but download nothing")
    parser.add_argument("--check", action="store_true", help="offline check: verify files against lockfile")
    parser.add_argument("--force", action="store_true", help="redownload even when the lockfile matches")
    args = parser.parse_args(argv)

    entries = load_entries(Path(args.manifest) if args.manifest else None)
    selected = select_entries(entries, args.id, args.format)
    if not selected:
        print("no book corpus entries match the selection.")
        return 0
    out_dir = Path(args.out)
    if args.list:
        print_entries(selected, include_urls=False)
        return 0
    if args.check:
        return check_entries(selected, out_dir)
    return fetch_entries(selected, out_dir, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
