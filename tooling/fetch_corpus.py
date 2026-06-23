#!/usr/bin/env python3
"""
fetch_corpus.py — download and archive the public-domain expressiveness corpus.

The corpus is the set of real-world documents FrameGraph aims to be able to
represent and render faithfully (the expressiveness / completeness target). The
sources are listed in fixtures/corpus/manifest.yaml and are ALL public domain
(CC0, expired copyright, or U.S. federal-government works) so the bytes can be
committed to this repository with no licensing strings.

What it does (idempotently):
  * downloads every manifest `url` to fixtures/corpus/<dest> (browser UA, retry
    with exponential backoff, polite per-host throttling)
  * records sha256 + size + content-type + http status + fetch time in
    fixtures/corpus/lockfile.json (the integrity record)
  * regenerates fixtures/corpus/PROVENANCE.md (the human-readable license table)
  * skips a file already on disk whose sha256 matches the lockfile (unless
    --force), so re-runs are cheap and only fetch what is missing or changed

Modes:
  (default)        download missing/changed entries, refresh lockfile + provenance
  --check          OFFLINE: verify on-disk files match the lockfile sha256s
                   (exit 1 on any drift/missing) — the CI-friendly gate
  --list           print the manifest (no network)
  --force          re-download every entry even if present
  --id / --tier / --format   restrict to matching entries

Dependency-light: standard library + PyYAML (already a runtime dep). No new deps.

Usage:
  python tooling/fetch_corpus.py
  python tooling/fetch_corpus.py --tier vector
  python tooling/fetch_corpus.py --id nasa-gao-reporting-2021 --force
  python tooling/fetch_corpus.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
CORPUS = os.path.join(ROOT, "fixtures", "corpus")
MANIFEST = os.path.join(CORPUS, "manifest.yaml")
LOCKFILE = os.path.join(CORPUS, "lockfile.json")
PROVENANCE = os.path.join(CORPUS, "PROVENANCE.md")
NOTICE = os.path.join(CORPUS, "NOTICE")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RETRIES = 4
BACKOFF = 2.0          # seconds; doubles each retry (2, 4, 8, 16)
HOST_INTERVAL = 1.0    # min seconds between requests to the same host (politeness)

_LICENSE_NAMES = {
    "CC0-1.0": "CC0 1.0 (public-domain dedication)",
    "PD-USGov": "U.S. federal government work (public domain)",
    "PD": "Public domain",
    "MIT": "MIT License (attribution required)",
    "BSD-3-Clause": "3-Clause BSD (attribution required)",
    "CC-BY-4.0": "CC BY 4.0 (attribution required)",
}
# Licenses that are NOT public domain and therefore require an `attribution`.
_ATTRIBUTION_REQUIRED = {"MIT", "BSD-3-Clause", "CC-BY-4.0"}


# --------------------------------------------------------------------------- #
def _load_manifest() -> list[dict]:
    with open(MANIFEST, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    entries = data.get("entries") or []
    for e in entries:
        for key in ("id", "dest", "license"):
            if not e.get(key):
                raise SystemExit(f"manifest entry missing '{key}': {e!r}")
        if not e.get("generated") and not e.get("url"):
            raise SystemExit(f"manifest entry {e['id']!r} needs a 'url' "
                             "(or 'generated: true' for a rendered artifact)")
        if e["license"] in _ATTRIBUTION_REQUIRED and not e.get("attribution"):
            raise SystemExit(
                f"manifest entry {e['id']!r} has license {e['license']} which "
                "requires an 'attribution' string (none given)")
    return entries


def _load_lock() -> dict:
    if os.path.exists(LOCKFILE):
        with open(LOCKFILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"files": {}}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _select(entries: list[dict], args) -> list[dict]:
    out = entries
    if args.id:
        out = [e for e in out if e["id"] in args.id]
    if args.tier:
        out = [e for e in out if e.get("tier") in args.tier]
    if args.format:
        out = [e for e in out if e.get("format") in args.format]
    return out


# --------------------------------------------------------------------------- #
def _download(url: str, _last_hit: dict[str, float]) -> tuple[bytes, str, int]:
    """Fetch url with retries/backoff + per-host throttling. Returns (body,
    content_type, status). Raises urllib errors after exhausting retries."""
    host = urlsplit(url).netloc
    err: Exception | None = None
    for attempt in range(RETRIES):
        # be polite: space out requests to the same host
        wait = HOST_INTERVAL - (time.monotonic() - _last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                status = resp.status
            _last_hit[host] = time.monotonic()
            return body, ctype, status
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            err = exc
            _last_hit[host] = time.monotonic()
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF * (2 ** attempt))
    raise err  # type: ignore[misc]


def cmd_fetch(entries: list[dict], force: bool) -> int:
    lock = _load_lock()
    files = lock["files"]
    last_hit: dict[str, float] = {}
    fetched = skipped = failed = warned = 0

    for e in entries:
        dest = os.path.join(CORPUS, e["dest"])
        rec = files.get(e["id"])
        if not force and rec and os.path.exists(dest) and _sha256(dest) == rec.get("sha256"):
            print(f"  skip   {e['id']:<32} (up to date)")
            skipped += 1
            continue
        # Generated artifacts (e.g. rendered UI rasters) are not downloaded; we
        # pin the bytes produced by their generator. Ingest the on-disk file.
        if e.get("generated"):
            if not os.path.exists(dest):
                print(f"  MISSING {e['id']:<32} run generator: {e.get('generator','?')}")
                failed += 1
                continue
            files[e["id"]] = {
                "url": "", "dest": e["dest"], "sha256": _sha256(dest),
                "bytes": os.path.getsize(dest), "content_type": "generated",
                "http_status": 0, "license": e["license"], "source": e.get("source", ""),
                "attribution": e.get("attribution", ""), "generated": True,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            print(f"  gen    {e['id']:<32} {os.path.getsize(dest):>9,} B  (pinned)")
            fetched += 1
            continue
        try:
            body, ctype, status = _download(e["url"], last_hit)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL   {e['id']:<32} {type(exc).__name__}: {exc}")
            failed += 1
            continue

        expect = e.get("expect")
        warn = expect and expect not in ctype.lower()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(body)
        digest = hashlib.sha256(body).hexdigest()
        files[e["id"]] = {
            "url": e["url"],
            "dest": e["dest"],
            "sha256": digest,
            "bytes": len(body),
            "content_type": ctype,
            "http_status": status,
            "license": e["license"],
            "source": e.get("source", ""),
            "attribution": e.get("attribution", ""),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        flag = "  WARN " if warn else "  ok   "
        note = f" [content-type {ctype!r} lacks {expect!r}]" if warn else ""
        print(f"{flag} {e['id']:<32} {len(body):>9,} B  {ctype}{note}")
        fetched += 1
        warned += 1 if warn else 0

    # prune lock entries no longer in the manifest selection-agnostic set
    manifest_ids = {e["id"] for e in _load_manifest()}
    for stale in [k for k in files if k not in manifest_ids]:
        del files[stale]

    lock["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOCKFILE, "w", encoding="utf-8") as fh:
        json.dump(lock, fh, indent=2, sort_keys=True)
        fh.write("\n")
    _write_provenance(_load_manifest(), files)

    print(f"\n{fetched} fetched, {skipped} up-to-date, {failed} failed"
          + (f", {warned} warning(s)" if warned else ""))
    return 1 if failed else 0


def cmd_check(entries: list[dict]) -> int:
    """Offline integrity gate: every selected entry must be on disk and match
    the lockfile sha256."""
    lock = _load_lock()
    files = lock["files"]
    bad = 0
    for e in entries:
        rec = files.get(e["id"])
        dest = os.path.join(CORPUS, e["dest"])
        if not rec:
            print(f"  MISSING-LOCK  {e['id']} (run fetch_corpus.py)")
            bad += 1
        elif not os.path.exists(dest):
            print(f"  MISSING-FILE  {e['id']} -> {e['dest']}")
            bad += 1
        elif _sha256(dest) != rec["sha256"]:
            print(f"  DRIFT         {e['id']} (sha256 mismatch)")
            bad += 1
    if bad:
        print(f"\nFAIL: {bad} corpus file(s) missing or drifted.")
        return 1
    print(f"OK: {len(entries)} corpus file(s) match the lockfile.")
    return 0


def cmd_list(entries: list[dict]) -> int:
    for e in entries:
        print(f"  {e['id']:<32} {e.get('tier',''):<10} {e['license']:<9} {e['url']}")
    print(f"\n{len(entries)} entries.")
    return 0


# --------------------------------------------------------------------------- #
def _write_provenance(entries: list[dict], files: dict) -> None:
    present = [e for e in entries if e["id"] in files]
    total = sum(files[e["id"]]["bytes"] for e in present)
    attributed = [e for e in present if e.get("attribution")]
    lines = [
        "# Corpus provenance (generated)",
        "",
        "<!-- GENERATED by tooling/fetch_corpus.py — do not hand-edit. -->",
        "",
        "Documents archived as FrameGraph's expressiveness / completeness target,"
        " in two freely-vendorable licensing classes:",
        "",
        "- **Public domain** — CC0, expired copyright, or U.S. federal works"
        " (17 U.S.C. §105): no obligations.",
        "- **Permissive** — MIT / BSD / CC-BY: vendored *with attribution*, recorded"
        " below and in `NOTICE`.",
        "",
        f"Integrity is pinned in `lockfile.json`. Total archived: **{total:,} bytes**"
        f" across **{len(present)}** files.",
        "",
        "| File | Tier | License | Source | Attribution | sha256 |",
        "|---|---|---|---|---|---|",
    ]
    for e in present:
        rec = files[e["id"]]
        lic = _LICENSE_NAMES.get(e["license"], e["license"])
        attr = e.get("attribution", "") or "—"
        lines.append(
            f"| `{e['dest']}` | {e.get('tier','')} | "
            f"[{lic}]({e.get('license_url','')}) | {e.get('source','')} | "
            f"{attr} | `{rec['sha256'][:12]}…` |"
        )
    lines += ["", "## Licenses", ""]
    for code, name in _LICENSE_NAMES.items():
        if any(e["license"] == code for e in present):
            lines.append(f"- **{code}** — {name}")
    if attributed:
        lines += ["", "## Required attribution", "",
                  "The permissive (non-public-domain) files above are reproduced"
                  " under licenses that require attribution. See `NOTICE`."]
    lines.append("")
    with open(PROVENANCE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    _write_notice(attributed, files)


def _write_notice(attributed: list[dict], files: dict) -> None:
    """Emit a NOTICE aggregating the attribution obligations of permissive files
    (empty/absent when the corpus is entirely public domain)."""
    if not attributed:
        if os.path.exists(NOTICE):
            os.remove(NOTICE)
        return
    seen: dict[str, list[str]] = {}
    for e in attributed:
        seen.setdefault(e["attribution"], []).append(e["dest"])
    out = ["FrameGraph expressiveness corpus — third-party attribution NOTICE",
           "(generated by tooling/fetch_corpus.py)", ""]
    for attribution, dests in seen.items():
        out.append(attribution)
        out += [f"    fixtures/corpus/{d}" for d in sorted(dests)]
        out.append("")
    with open(NOTICE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="offline: verify on-disk files match the lockfile (CI gate)")
    ap.add_argument("--list", action="store_true", help="list manifest entries (no network)")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    ap.add_argument("--id", action="append", help="restrict to this entry id (repeatable)")
    ap.add_argument("--tier", action="append", help="restrict to this tier (repeatable)")
    ap.add_argument("--format", action="append", help="restrict to this format (repeatable)")
    args = ap.parse_args(argv)

    entries = _select(_load_manifest(), args)
    if not entries:
        print("no manifest entries match the selection.")
        return 0
    if args.list:
        return cmd_list(entries)
    if args.check:
        return cmd_check(entries)
    return cmd_fetch(entries, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
