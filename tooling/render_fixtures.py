#!/usr/bin/env python3
"""
render_fixtures.py — a dependency-free SVG proxy renderer for FrameGraph v2 docs.

Renders ALL or ANY document under fixtures/ (or any path you pass) to SVG, one
file per page, plus a browsable index.html contact sheet. Unlike the matplotlib
proxy in render_fg_doc.py, this needs only the standard library + PyYAML, so it
runs in a bare environment, and it tolerates the full fixture variety:

  * canvas from explicit `size`, a `preset`, or inherited from a master
  * `page` layers AND `flow` sections (naive vertical text flow, paginated)
  * the core object set: rect / ellipse / circle / line / polyline / polygon /
    path / curve / bezier / text / bullet_list / icon / image / table / group
  * HEAD stroke single-form (paint in `stroke`, geometry in `stroke_style`)
  * token colour deref, CSS-named *and* legacy shorthand text styles,
    linear/radial gradient fills (conic ≈ first stop)

This is a SANITY-CHECK proxy, not a conformant renderer: no real text shaping or
line-breaking metrics, fonts are the browser's generic families, out-of-profile
objects and missing image assets become labelled placeholders. Geometry,
positions, colours and z-order are honoured.

Usage:
    python3 tooling/render_fixtures.py                       # render every fixture -> out/render/
    python3 tooling/render_fixtures.py --all
    python3 tooling/render_fixtures.py fixtures/b1/mckinsey-7s.fg.json
    python3 tooling/render_fixtures.py 'fixtures/*.fg.yaml'  # globs ok (quote them)
    python3 tooling/render_fixtures.py fixtures/b1 --out /tmp/r --max-pages 3
    python3 tooling/render_fixtures.py --list                # just list discoverable docs

Open out/render/index.html in a browser to see the contact sheet.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FIXTURES = os.path.join(ROOT, "fixtures")
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _load_yaml_file(path):
    with open(path, encoding="utf-8") as fh:
        try:
            return yaml.load(fh, Loader=_YAML_LOADER)
        except yaml.YAMLError:
            if _YAML_LOADER is yaml.SafeLoader:
                raise
            fh.seek(0)
            return yaml.load(fh, Loader=yaml.SafeLoader)

sys.path.insert(0, ROOT)
from framegraph.rendering.application.normalize import normalize_doc  # noqa: E402
from framegraph.rendering.application.renderer import Renderer  # noqa: E402
from framegraph.rendering.domain.geometry import esc  # noqa: E402

# ``normalize_doc`` was relocated into framegraph/rendering/application/normalize.py
# so the package no longer imports up into tooling/. It is re-exported here for the
# CLI and any callers that still import it from this module.
__all__ = ["Renderer", "normalize_doc", "discover", "stem_of", "write_index", "main"]


def discover(paths):
    """Expand args (files / dirs / globs) into a sorted list of FrameGraph docs."""
    exts = (".json", ".yaml", ".yml")
    out = []
    if not paths:
        paths = [FIXTURES]
    for p in paths:
        cand = glob.glob(p, recursive=True) or ([p] if os.path.exists(p) else [])
        for c in cand:
            if os.path.isdir(c):
                for root, _, files in os.walk(c):
                    out += [os.path.join(root, f) for f in files if f.endswith(exts)]
            elif c.endswith(exts):
                out.append(c)
    seen, docs = set(), []
    for f in sorted(set(out)):
        try:
            d = _load_yaml_file(f)
        except Exception:
            continue
        d = normalize_doc(d)
        if isinstance(d, dict) and d.get("dsl") == "FrameGraph" and d.get("pages"):
            rp = os.path.relpath(f, ROOT)
            if rp not in seen:
                seen.add(rp); docs.append((f, d))
    return docs


def stem_of(path):
    # keep the extension so docusign.fg.json and docusign.fg.yaml stay distinct
    rel = os.path.relpath(path, FIXTURES) if path.startswith(FIXTURES) else os.path.basename(path)
    return rel.replace(os.sep, "_")


def write_index(out_dir, entries, title, page_links=False):
    cards = []
    for name, link, thumbs in entries:
        if page_links:
            imgs = "".join(
                f'<a href="{esc(t)}"><img src="{esc(t)}" loading="lazy" '
                f'style="width:200px;border:1px solid #ccc;margin:4px;background:#fff"></a>'
                for t in thumbs)
            cards.append(f'<section><h2>{esc(name)} '
                         f'<small style="color:#888">({len(thumbs)} page(s))</small></h2>{imgs}</section>')
        else:
            first = f'<img src="{esc(thumbs[0])}" loading="lazy" style="width:240px;border:1px solid #ccc;background:#fff">' if thumbs else ""
            cards.append(f'<a href="{esc(link)}" style="text-decoration:none;color:inherit">'
                         f'<figure style="display:inline-block;margin:8px;vertical-align:top">'
                         f'{first}<figcaption style="font:13px sans-serif;max-width:240px">{esc(name)} '
                         f'<span style="color:#888">({len(thumbs)}p)</span></figcaption></figure></a>')
    body = "".join(cards)
    doc = (f'<!doctype html><meta charset="utf-8"><title>{esc(title)}</title>'
           f'<body style="font:14px sans-serif;margin:24px;background:#fafafa">'
           f'<h1>{esc(title)}</h1>{body}</body>')
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "render"), help="output dir")
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages rendered per doc (0 = all)")
    ap.add_argument("--list", action="store_true", help="list discoverable docs and exit")
    ap.add_argument("--check-overflow", action="store_true",
                    help="render, then assert no text visually overflows a containing box (exit 1 on failure)")
    ap.add_argument("--real-metrics", action="store_true",
                    help="wrap/fit text using real font advances (needs fontTools) instead of "
                         "the per-character estimate; off by default so golden output is stable")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    docs = discover([] if args.all else args.paths)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        print(f"\n{len(docs)} document(s).")
        return 0
    if not docs:
        print("No FrameGraph documents found. Try: render_fixtures.py --all", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    index_entries, total_pages = [], 0
    agg = {}
    for f, doc in docs:
        stem = stem_of(f)
        doc_dir = os.path.join(args.out, stem)
        os.makedirs(doc_dir, exist_ok=True)
        r = Renderer(doc, os.path.dirname(os.path.abspath(f)), real_metrics=args.real_metrics)
        svgs, thumbs = [], []
        for page in doc.get("pages", []):
            if not isinstance(page, dict):
                continue
            for s in r.render_page(page):
                svgs.append(s)
                if args.max_pages and len(svgs) >= args.max_pages:
                    break
            if args.max_pages and len(svgs) >= args.max_pages:
                break
        for i, s in enumerate(svgs, 1):
            fn = f"p{i:03d}.svg"
            with open(os.path.join(doc_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(s)
            thumbs.append(f"{stem}/{fn}")
        write_index(doc_dir, [(stem, "", [f"p{i:03d}.svg" for i in range(1, len(svgs) + 1)])],
                    f"FrameGraph proxy — {stem}", page_links=True)
        index_entries.append((stem, f"{stem}/index.html", thumbs))
        total_pages += len(svgs)
        for k, v in r.tstats.items():
            agg[k] = agg.get(k, 0) + v
        if not args.quiet:
            note = f" ({r.skipped} skipped)" if r.skipped else ""
            ov = f"  ⚠ {r.tstats['uncontained']} text overflow" if r.tstats["uncontained"] else ""
            print(f"  {stem}: {len(svgs)} page(s){note}{ov}")

    write_index(args.out, index_entries, "FrameGraph fixtures — SVG proxy contact sheet")
    print(f"\nRendered {len(docs)} document(s), {total_pages} page(s) -> {args.out}")
    print(f"Open {os.path.join(args.out, 'index.html')}")

    if args.check_overflow:
        print("\n=== text-fit overflow check ===")
        print(f"  text objects ............................ {agg.get('total',0)}")
        print(f"  would overflow naively (1-line, no fit) . {agg.get('naive_overflow',0)}   <- the reported bug")
        print(f"  fixed by wrap ........................... {agg.get('wrapped',0)}")
        print(f"  fixed by shrink_to_fit .................. {agg.get('shrunk',0)}")
        print(f"  contained by clip/ellipsis net ......... {agg.get('clipped',0)}")
        print(f"  fit without change ...................... {agg.get('contained',0)}")
        print(f"  overflow:visible (permitted to spill) .. {agg.get('visible_overflow',0)}")
        bad = agg.get("uncontained", 0) - agg.get("visible_overflow", 0)  # contained-policy spill (must be 0)
        print(f"  text spilling a CONTAINING box .......... {bad}   (must be 0)")
        ok = bad == 0
        print(f"\n  RESULT: {'PASS' if ok else 'FAIL'} — "
              f"{'every box-contained text fits or is clipped to its box' if ok else 'some contained text still overflows'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
