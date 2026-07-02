#!/usr/bin/env python3
"""
fg_css_optimize.py
==================

A multi-pass CSS *consolidation* pass over HTML produced by
``framegraph_to_html.py`` (or any HTML built the same way: per-element inline
``style`` attributes plus a single ``<style>`` head block).

It compounds repeated *computed* inline styles into shared classes and strips
declarations / selectors / variables that do nothing, **without changing how
the page renders**. That guarantee is actively defended, not assumed: pooling
moves a declaration from an inline ``style`` (the highest specificity) into a
single class (lower specificity), so any property a higher-specificity head
rule could set on the same element is *kept inline* (see ``risky_properties``).

Why not a DOM parser? HTML parsers (bs4/lxml/html.parser) lowercase SVG's
camelCase ``viewBox`` to ``viewbox``, which silently breaks scaling. So this
tool rewrites only the *values* of the ``style`` and ``class`` attributes via
targeted regex and copies every other attribute — ``viewBox`` included — plus
every non-tag byte through verbatim. Inner SVG tags (``<svg>``/``<polygon>``/
``<polyline>``/``<path>``) now DO carry a ``style`` attribute (paint +
positioning); they are pooled like any other element, which is safe because
SVG paint applied via a CSS class renders identically to the inline form and
no other rule targets them.

Passes
------
  1. normalize        canonicalize values  (0.00px -> 0, trim zeros, lc hex)
  2. prune-decls      drop no-op declarations (==stylesheet default)
  3. compound         hoist poolable theme-sets used >= threshold into .t*
                      classes (risky properties stay inline)
  4. prune-unused     drop orphaned :root vars and unreferenced rules,
                      looped to a fixed point (a removed class can orphan a var)

At-rules (``@media``, ``@keyframes``, ``@font-face`` ...) are preserved verbatim
via brace-matched parsing; the stylesheet is never flattened.

Usage
-----
    python fg_css_optimize.py in.html -o out.html [--threshold N]
                              [--minify] [--passes N] [-q]

``--threshold 2`` (default) only pools styles seen twice or more; ``1`` hoists
every theme-set. ``--passes`` re-runs the whole pipeline (it is idempotent, so
this mainly demonstrates convergence).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, OrderedDict

# Declarations that are inherently per-instance: keep these inline.
GEOM_PROPS = ("left", "top", "right", "bottom", "width", "height",
              "transform", "transform-origin")
GEOM_ORDER = {p: i for i, p in enumerate(GEOM_PROPS)}

# Start tag whose attributes are all name="value" (the generator's output).
TAG_RE = re.compile(r'<(?P<name>[a-zA-Z][\w:-]*)'
                    r'(?P<attrs>(?:\s+[\w:-]+\s*=\s*"[^"]*")*)'
                    r'\s*(?P<slash>/?)>')
ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
NUM_RE = re.compile(r'-?\d*\.\d+|-?\d+')
HEX_RE = re.compile(r'#[0-9a-fA-F]{3,8}\b')
VAR_USE_RE = re.compile(r'var\(\s*(--[\w-]+)')


# --------------------------------------------------------------------------- #
# value / declaration normalization                                            #
# --------------------------------------------------------------------------- #


def _fmt_num(m: re.Match) -> str:
    f = float(m.group())
    if f == int(f):
        return str(int(f))
    return ("%f" % f).rstrip("0").rstrip(".")


def normalize_value(val: str) -> str:
    val = val.strip()
    # Protect hex colors: never run number normalization inside them
    # (e.g. #007acc must not become #7acc). Split keeps hex tokens at odd
    # indices; lowercase those, normalize numbers only in the rest.
    parts = re.split(r"(#[0-9a-fA-F]{3,8}\b)", val)
    for i, part in enumerate(parts):
        parts[i] = part.lower() if i % 2 == 1 else NUM_RE.sub(_fmt_num, part)
    val = "".join(parts)
    val = re.sub(r"\s+", " ", val)
    return val


def split_decls(style: str) -> "OrderedDict[str, str]":
    out: "OrderedDict[str, str]" = OrderedDict()
    for chunk in style.split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        prop, _, value = chunk.partition(":")
        prop = prop.strip().lower()
        out[prop] = normalize_value(value)
    return out


# pass 2: declarations equal to the stylesheet's effective default -> drop
def is_noop(prop: str, value: str) -> bool:
    if prop == "--fg-text-align" and value == "left":
        return True  # .fg-text>span uses var(--fg-text-align,left)
    if prop == "opacity" and value in ("1", "1.0"):
        return True
    if prop in ("border-radius", "border", "outline") and value in ("0", "none"):
        return True
    if prop in ("transform",) and value in ("rotate(0deg)", "none"):
        return True
    return False


# --------------------------------------------------------------------------- #
# tag attribute helpers (case-preserving; only style/class are mutated)        #
# --------------------------------------------------------------------------- #


def parse_attrs(attr_str: str):
    return [[m.group(1), m.group(2)] for m in ATTR_RE.finditer(attr_str)]


def build_tag(name: str, attrs, slash: str) -> str:
    body = "".join(f' {n}="{v}"' for n, v in attrs if v is not None)
    return f"<{name}{body}{'/' if slash else ''}>"


def classify(style: str, risky: "set[str]" = frozenset()):
    """Split one inline style into ``(inline_decls, poolable_theme_decls)``.

    Geometry props and any ``risky`` property — one a higher-specificity head
    rule could override if it were demoted to a class — stay inline; everything
    else is poolable into a shared class.
    """
    decls = split_decls(style)
    geom, theme = OrderedDict(), OrderedDict()
    for prop, val in decls.items():
        if is_noop(prop, val):
            continue
        if prop in GEOM_ORDER or prop in risky:
            geom[prop] = val
        else:
            theme[prop] = val
    return geom, theme


def theme_key(theme: "OrderedDict[str, str]") -> str:
    return "".join(f"{p}:{theme[p]};" for p in sorted(theme))


# --------------------------------------------------------------------------- #
# the optimizer                                                                #
# --------------------------------------------------------------------------- #


def split_stylesheet(css: str):
    """Split a stylesheet into ordered items, preserving at-rules verbatim.

    Each item is either
      ``("rule", selector, declarations)``  -- a flat ``sel { decls }`` rule, or
      ``("verbatim", text)``                -- an at-rule block/statement or comment.

    Brace matching means nested at-rules (``@media{ .x{} }``) survive intact,
    where a naive ``sel{decls}`` regex would shred them into bogus top-level
    rules (turning e.g. a print-only rule into an always-on one).
    """
    items: list[tuple] = []
    i, n, seg = 0, len(css), 0
    while i < n:
        c = css[i]
        if c == "/" and css[i:i + 2] == "/*":                 # comment
            end = css.find("*/", i + 2)
            end = end + 2 if end != -1 else n
            if css[seg:i].strip():
                items.append(("verbatim", css[seg:i]))
            items.append(("verbatim", css[i:end]))
            i = seg = end
            continue
        if c == "@":                                          # at-rule
            j = i
            while j < n and css[j] not in ";{":
                j += 1
            if j < n and css[j] == "{":                       # block at-rule
                depth, k = 0, j
                while k < n:
                    if css[k] == "{":
                        depth += 1
                    elif css[k] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                items.append(("verbatim", css[i:k + 1]))
                i = seg = k + 1
            else:                                             # @import ...; etc.
                end = j + 1 if j < n else n
                items.append(("verbatim", css[i:end]))
                i = seg = end
            continue
        if c == "{":                                          # flat rule
            sel = css[seg:i].strip()
            depth, k = 1, i + 1
            while k < n and depth:
                if css[k] == "{":
                    depth += 1
                elif css[k] == "}":
                    depth -= 1
                k += 1
            items.append(("rule", sel, css[i + 1:k - 1].strip()))
            i = seg = k
            continue
        i += 1
    if css[seg:].strip():
        items.append(("verbatim", css[seg:]))
    return items


def risky_properties(items) -> "set[str]":
    """Property names a higher-specificity head rule could set on a pooled element.

    Pooling demotes a declaration from inline (specificity 1,0,0,0) to one
    appended class (0,0,1,0). A head rule that out-specifies a single class and
    can match the element by a *class* key selector would then win the cascade,
    changing the render — so those properties must stay inline. For
    framegraph_to_html output this set is empty (its only multi-token selectors
    end in a *type*, e.g. ``.fg-text>span`` / ``code``, never a class).
    """
    risky: set[str] = set()
    for it in items:
        if it[0] != "rule":
            continue
        for sub in (s.strip() for s in it[1].split(",")):
            if not sub or sub == ":root":
                continue
            key = re.split(r"\s*[>+~ ]\s*", sub)[-1]          # rightmost compound
            key_classes = re.findall(r"\.([\w-]+)", key)
            outranks_one_class = (
                "#" in sub                                    # an id anywhere
                or bool(re.search(r"[>+~]| ", sub))           # a combinator
                or len(key_classes) >= 2                      # .a.b
                or bool(re.match(r"[A-Za-z*]", key))          # type+class, e.g. div.x
                or ":" in key                                 # pseudo-class
            )
            if key_classes and outranks_one_class:
                risky.update(d.split(":", 1)[0].strip().lower()
                             for d in it[2].split(";") if ":" in d)
    return risky


def _empty_stats(doc: str) -> dict:
    n = len(re.findall(r'style="', doc))
    return {"styled_before": n, "theme_pooled": 0, "pooled_classes": 0,
            "prune_passes": 0, "bytes_before": len(doc), "bytes_after": len(doc),
            "styled_after": n, "rules_after": 0}


def optimize_once(doc: str, threshold: int) -> tuple[str, dict]:
    # split the single <style> head block from the rest of the document
    m = re.search(r"(<style[^>]*>)(.*?)(</style>)", doc, re.S)
    if not m:
        return doc, _empty_stats(doc)        # nothing to pool against; never crash
    head, css, tail = m.group(1), m.group(2), m.group(3)
    prefix, suffix = doc[: m.start()], doc[m.end():]

    # Parse the stylesheet (at-rules kept whole) and find the properties that
    # must stay inline to keep the cascade identical.
    items = split_stylesheet(css)
    risky = risky_properties(items)

    # ----- collect poolable theme-set frequencies across all styled tags ----- #
    freq: Counter[str] = Counter()

    def scan(match: re.Match):
        attrs = parse_attrs(match.group("attrs"))
        sval = next((v for n, v in attrs if n.lower() == "style"), None)
        if sval is not None:
            _, theme = classify(sval, risky)
            if theme:
                freq[theme_key(theme)] += 1
        return match.group(0)

    TAG_RE.sub(scan, suffix)

    classmap: "OrderedDict[str, str]" = OrderedDict()
    for i, (key, n) in enumerate(freq.most_common()):
        if n >= threshold:
            classmap[key] = f"t{i}"

    stats = {"styled_before": len(re.findall(r'style="', suffix)),
             "theme_pooled": sum(n for k, n in freq.items() if k in classmap),
             "pooled_classes": len(classmap)}

    # ----- rewrite tags: inline geometry/risky props, theme -> class or inline -- #
    def rewrite(match: re.Match):
        name, slash = match.group("name"), match.group("slash")
        attrs = parse_attrs(match.group("attrs"))
        idx = {n.lower(): k for k, (n, _) in enumerate(attrs)}
        if "style" not in idx:
            return match.group(0)
        geom, theme = classify(attrs[idx["style"]][1], risky)
        added_class = classmap.get(theme_key(theme))
        # inline = geometry/risky (geometry-ordered), plus theme when NOT pooled
        decls = OrderedDict(sorted(
            geom.items(), key=lambda kv: GEOM_ORDER.get(kv[0], len(GEOM_ORDER))))
        if theme and added_class is None:
            for p in sorted(theme):
                decls[p] = theme[p]
        new_style = "".join(f"{p}:{v};" for p, v in decls.items())
        attrs[idx["style"]][1] = new_style or None      # None -> drop the attribute
        if added_class:
            if "class" in idx:
                cur = attrs[idx["class"]][1]
                attrs[idx["class"]][1] = f"{cur} {added_class}".strip()
            else:
                attrs.insert(0, ["class", added_class])
        return build_tag(name, attrs, slash)

    new_body = TAG_RE.sub(rewrite, suffix)

    # ----- append pooled rules, then prune to a fixed point ----- #
    items += [("rule", f".{cls}", key) for key, cls in classmap.items()]

    used_classes: set[str] = set()
    for m2 in re.finditer(r'class="([^"]*)"', new_body):
        used_classes.update(m2.group(1).split())

    prune_passes = 0
    while True:
        prune_passes += 1
        # 1) drop flat rules whose selector targets only unused classes
        kept = []
        for it in items:
            if it[0] == "rule":
                sclasses = set(re.findall(r"\.([\w-]+)", it[1]))
                if sclasses and not (sclasses & used_classes):
                    continue
            kept.append(it)
        # 2) collect var() usage from the body and every kept chunk (incl. at-rules)
        used_vars = set(VAR_USE_RE.findall(new_body))
        for it in kept:
            used_vars.update(VAR_USE_RE.findall(it[2] if it[0] == "rule" else it[1]))
        # 3) prune unused custom properties out of :root
        changed = len(kept) != len(items)
        kept2 = []
        for it in kept:
            if it[0] == "rule" and it[1].strip() == ":root":
                pairs = [d for d in it[2].split(";") if d.strip()]
                keep_pairs = [d for d in pairs
                              if not d.split(":")[0].strip().startswith("--")
                              or d.split(":")[0].strip() in used_vars]
                if len(keep_pairs) != len(pairs):
                    changed = True
                if keep_pairs:
                    kept2.append(("rule", ":root",
                                  ";".join(p.strip() for p in keep_pairs) + ";"))
                else:
                    changed = True  # whole :root dropped
            else:
                kept2.append(it)
        items = kept2
        if not changed:
            break

    def _render(it):
        return f"{it[1]}{{{it[2]}}}" if it[0] == "rule" else it[1]

    new_css = "\n".join(_render(it) for it in items)
    new_doc = prefix + head + "\n" + new_css + "\n" + tail + new_body

    stats.update({
        "prune_passes": prune_passes,
        "bytes_before": len(doc),
        "bytes_after": len(new_doc),
        "styled_after": len(re.findall(r'style="', new_doc)),
        "rules_after": sum(1 for it in items if it[0] == "rule"),
    })
    return new_doc, stats


def minify(doc: str) -> str:
    # collapse CSS whitespace inside the <style> block, and inter-tag gaps
    def squash_css(m):
        css = m.group(2)
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        css = re.sub(r"\s+", " ", css)
        css = re.sub(r"\s*([{};:,>])\s*", r"\1", css)
        css = css.replace(";}", "}")
        return m.group(1) + css.strip() + m.group(3)
    doc = re.sub(r"(<style[^>]*>)(.*?)(</style>)", squash_css, doc, flags=re.S)
    doc = re.sub(r">\s+<", "><", doc)
    return doc


def optimize(doc: str, threshold=2, passes=1, do_minify=False, quiet=False):
    all_stats = []
    for p in range(passes):
        doc, stats = optimize_once(doc, threshold)
        all_stats.append(stats)
        if not quiet:
            s = stats
            print(f"  pass {p+1}: {s['styled_before']} styled tags "
                  f"({s['theme_pooled']} theme-decls compounded into "
                  f"{s['pooled_classes']} classes), {s['rules_after']} rules, "
                  f"{s['prune_passes']} prune-iters, "
                  f"{s['bytes_before']}B -> {s['bytes_after']}B", file=sys.stderr)
    if do_minify:
        doc = minify(doc)
        if not quiet:
            print(f"  minified -> {len(doc)}B", file=sys.stderr)
    return doc, all_stats


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="HTML file from framegraph_to_html.py")
    ap.add_argument("-o", "--output", help="output HTML (default: *.opt.html)")
    ap.add_argument("--threshold", type=int, default=2,
                    help="min repeats before a style-set is hoisted (default 2; "
                         "1 = hoist everything)")
    ap.add_argument("--passes", type=int, default=1,
                    help="re-run the whole pipeline N times (idempotent)")
    ap.add_argument("--minify", action="store_true", help="also strip whitespace")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        doc = fh.read()
    out, _ = optimize(doc, args.threshold, args.passes, args.minify, args.quiet)
    out_path = args.output or re.sub(r"\.html?$", "", args.input) + ".opt.html"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    saved = (1 - len(out) / len(doc)) * 100
    print(f"Wrote {out_path}  ({len(doc)}B -> {len(out)}B, -{saved:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
