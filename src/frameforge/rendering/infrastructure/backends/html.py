"""HTML `DocumentRenderer` — the semantic shell around builder-painted pages.

What this module is now
-----------------------
An *assembler*, not a renderer. It drives the shared `Renderer` builder with
`HtmlPainter`, then wraps the pages it gets back in a real HTML document: head,
one hoisted stylesheet, an accessibility landmark, one labelled `<figure>` per
page, and the authored page-link navigation.

What it used to be
------------------
A 1462-line standalone transform that re-derived group layout, text fitting and
wrapping, tables, UML, connectors and dimensions — everything the builder
already did for SVG. It drew 13 of the model's 34 object types and emitted the
other 21 as "unsupported type" placeholders; a `mode: flow` page became a note
saying the profile was not rendered. Every engine improvement had to be
hand-copied here to reach HTML, and mostly was not.

Deleting that duplication is the point. Object-type parity is now *structural*:
HTML is driven by the same builder as SVG, so it cannot support fewer types than
SVG does. `tests/test_html_backend_parity.py` asserts it by comparing the marks
the two targets emit for every oracle fixture — a future object type is covered
the day the builder learns it, with no change here.

The division of labour
----------------------
* the **builder** decides *what* is on the page (layout, typography, pagination);
* `HtmlPainter` decides *how a mark becomes markup*, inheriting the SVG
  primitives rather than reimplementing them;
* this module decides *what a document is* — the parts that exist once per file
  rather than once per mark.

Behaviour changes from the standalone renderer
----------------------------------------------
* Shapes are inline SVG rather than absolutely-positioned `<div>`s. That is what
  buys parity: every primitive the engine can draw is drawn, including the ones
  the CSS box model has no honest answer for (rotated ellipses, path geometry,
  gradient-on-path, filter effects).
* `mode: flow` documents typeset for real instead of showing a placeholder.
* Preserved: layer and object identity, the `:root` palette, `.fg-ts-*` style
  classes, the accessibility markup, and `Page.links` navigation.

Usage
-----
    python -m frameforge.cli input.fg.yaml --to html      # the front door
    # or, in process:
    from frameforge.rendering.infrastructure.backends import get_backend
    html_text = get_backend("html").render(doc_dict).pages[0]

YAML input needs PyYAML; JSON input needs nothing extra.
"""
from __future__ import annotations

import html
import json
import os
import re

from frameforge.rendering.domain.ports import RenderedArtifact
from frameforge.rendering.domain.services.canvas_resolver import (
    DEFAULT_WH as _HTML_DEFAULT_WH, PRESETS as _CANVAS_PRESETS,
    CanvasResolver as _CanvasResolver)
from frameforge.rendering.infrastructure.painters.html import css_ident as _css_ident


# --------------------------------------------------------------------------- #
# Convenience loaders (kept from the standalone tool; the CLI parses itself)    #
# --------------------------------------------------------------------------- #
def load_document(path: str) -> dict:
    """Load a FrameForge document from a `.json` / `.yaml` / `.yml` path."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith((".yaml", ".yml")):
        import yaml
        return yaml.safe_load(text)
    return json.loads(text)


def maybe_validate(doc: dict, schema_path: str | None) -> None:
    """Validate `doc` against a JSON Schema when one is given and jsonschema is
    installed. Absent either, this is a no-op — rendering never depends on it."""
    if not schema_path or not os.path.exists(schema_path):
        return
    try:
        import jsonschema
    except ImportError:
        return
    with open(schema_path, encoding="utf-8") as fh:
        jsonschema.validate(doc, json.load(fh))


# --------------------------------------------------------------------------- #
# Canvas — the ONE canonical resolver, never a mirror                          #
# --------------------------------------------------------------------------- #
# The builder resolves each page's canvas itself, so `--to html` and `--to svg`
# cannot diverge on preset sizes, `orientation` or physical `units`. This alias
# stays because the caption reports the page's pixel size, and because the
# shared-identity gate (drift-risk-map #4) asserts this module reaches the
# canonical `CanvasResolver` rather than copying its table.
_PAGE_CANVAS = _CanvasResolver({})


def canvas_size(page: dict, default=_HTML_DEFAULT_WH) -> tuple[float, float]:
    """Resolve a page's canvas to (w, h) via the canonical CanvasResolver."""
    if not isinstance(page, dict) or page.get("canvas") is None:
        return default
    return _PAGE_CANVAS.resolve(page)


# --------------------------------------------------------------------------- #
# Page links — authored navigation, which no vector backend can carry          #
# --------------------------------------------------------------------------- #
def page_link_href(link: dict) -> str:
    """The href for one `PageLink`: an external URL, or a same-document anchor.

    Internal targets point at the page figure's own id (`page-<id>`) rather than
    a second, parallel anchor scheme — one id per page, so the link always has
    something real to jump to.
    """
    to = str(link.get("to", ""))
    if link.get("external") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//|^#", to):
        return to
    return f"#page-{_css_ident(to)}"


def render_page_links(page: dict) -> str:
    """`Page.links` as a real navigation landmark.

    `PageLink` has been in the model since 2.0 but no *vector* backend renders
    it — a link list is document furniture, not a mark — so authored navigation
    vanished on export (GH P1-3). HTML is the one target that can carry it, and
    it is emitted outside the artwork so it never overlays the canvas.
    """
    links = page.get("links") or [] if isinstance(page, dict) else []
    items = []
    for link in links:
        if not isinstance(link, dict) or not link.get("to"):
            continue
        href = page_link_href(link)
        label = html.escape(str(link.get("label") or link.get("to")))
        rel = link.get("relation")
        rel_attr = f' rel="{html.escape(str(rel), quote=True)}"' if rel else ""
        ext = ' target="_blank"' if link.get("external") else ""
        items.append(
            f'<li><a class="fg-link" href="{html.escape(href, quote=True)}"'
            f"{rel_attr}{ext}>{label}</a></li>"
        )
    if not items:
        return ""
    return ('<nav class="fg-pagelinks" aria-label="Page links">\n'
            f"<ul>{''.join(items)}</ul>\n</nav>")


# --------------------------------------------------------------------------- #
# The document shell                                                           #
# --------------------------------------------------------------------------- #
#: Structural CSS only: the page frame, the figure furniture, the landmark.
#: Everything describing the *artwork* — palette, text styles — is hoisted by the
#: painter from the document's own tokens, so this sheet injects no design
#: decision the document did not make (the no-injection rule the design audit
#: enforces).
_BASE_CSS = """*,*::before,*::after{box-sizing:border-box;}
body{margin:0;background:#15161a;color:#e8eaed;
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;padding:32px 16px;}
.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;
  overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;}
.fg-doc{display:flex;flex-direction:column;align-items:center;gap:48px;}
.fg-figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:14px;}
.fg-figure>svg{max-width:100%;height:auto;background:#fff;
  box-shadow:0 12px 40px rgba(0,0,0,.5);border-radius:4px;}
.fg-figcaption{max-width:480px;text-align:center;color:#9aa0a6;font-size:13px;
  line-height:1.5;}
.fg-figtitle{margin:0;font-size:15px;font-weight:600;color:#e8eaed;}
.fg-figmeta{display:block;margin-top:2px;}
.fg-pagelinks ul{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;
  gap:12px;justify-content:center;font-size:13px;}
.fg-link{color:inherit;}
@media (prefers-color-scheme: light){
  body{background:#f5f6f7;color:#1f2023;}
  .fg-figtitle{color:#1f2023;}
  .fg-figcaption{color:#5f6368;}
}
@media print{
  body{background:#fff;padding:0;}
  .fg-doc{gap:0;}
  .fg-figure{break-inside:avoid;page-break-after:always;}
  .fg-figure>svg{box-shadow:none;border-radius:0;}
  .fg-figcaption,.fg-pagelinks{display:none;}
}
"""


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _figure(svg: str, page: dict, index: int) -> str:
    """One page as a labelled figure. Labels are authored, never invented."""
    cap_id = f"fg-figcap-{index}"
    pid = page.get("id") if isinstance(page, dict) else None
    anchor = f"page-{_css_ident(pid)}" if pid else f"page-{index}"
    title = (page.get("title") or page.get("name") or "") if isinstance(page, dict) else ""
    w, h = canvas_size(page)

    if title:
        head = f'<h2 class="fg-figtitle" id="{cap_id}">{_esc(title)}</h2>'
        meta = (f'<span class="fg-figmeta">page <code>{_esc(pid or "")}</code> '
                f"&middot; {w:g}&times;{h:g}px</span>")
    else:
        head = (f'<span class="fg-figtitle" id="{cap_id}">page '
                f"<code>{_esc(pid or index + 1)}</code></span>")
        meta = f'<span class="fg-figmeta">{w:g}&times;{h:g}px</span>'

    nav = render_page_links(page)
    nav_html = f"\n{nav}" if nav else ""
    return (
        f'<figure class="fg-figure" id="{_esc(anchor)}" role="group" '
        f'aria-labelledby="{cap_id}">\n'
        f'<figcaption class="fg-figcaption">{head}{meta}</figcaption>\n'
        f"{svg}{nav_html}\n"
        f"</figure>"
    )


def _doc_meta(doc: dict) -> tuple[str, str, str]:
    """(title, description, lang) accepting both the top-level and `meta:` forms."""
    meta = doc.get("meta") or {}
    title = doc.get("title") or meta.get("title") or "FrameForge render"
    description = doc.get("description") or meta.get("description") or ""
    lang = doc.get("lang") or meta.get("lang") or meta.get("language") or "en"
    return str(title), str(description), str(lang)


def render_document(doc: dict, base_dir: str | None = None,
                    *, real_metrics: bool | None = None) -> str:
    """Render a whole FrameForge document to one HTML page.

    Drives the shared builder with `HtmlPainter`, then assembles the shell. The
    stylesheet is collected across every page and emitted once, so a palette
    token first used on page 9 is still declared exactly once, at the top.

    `real_metrics` threads the builder's glyph-advance text measurement: None
    (the default) consults `FRAMEFORGE_REAL_METRICS`, an explicit bool always
    wins. The golden harness passes False so the HTML lock pins estimate-mode
    measurement and stays reproducible on a machine with different fonts —
    exactly as the SVG lock does.
    """
    from frameforge.rendering.application.normalize import normalize_doc
    from frameforge.rendering.application.renderer import Renderer
    from frameforge.rendering.infrastructure.painters.html import HtmlPainter

    data = normalize_doc(doc if isinstance(doc, dict) else {})
    held: dict = {}

    def factory(color_resolver):
        held["painter"] = HtmlPainter(color_resolver)
        return held["painter"]

    renderer = Renderer(data, base_dir or ".", painter_factory=factory,
                        real_metrics=real_metrics)

    figures: list[str] = []
    index = 0
    for page in data.get("pages", []):
        if not isinstance(page, dict):
            continue
        # One page dict can yield several output pages (a paginated flow
        # section); each becomes its own <figure>.
        for svg in renderer.render_page(page):
            figures.append(_figure(svg, page, index))
            index += 1

    painter = held.get("painter")
    tokens_css = painter.stylesheet() if painter is not None else ""
    sheet = _BASE_CSS + (tokens_css + "\n" if tokens_css else "")

    title, description, lang = _doc_meta(data)
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="generator" content="frameforge (html backend)">',
        f'<meta name="description" content="{_esc(description)}">',
        f"<title>{_esc(title)}</title>",
    ]

    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{_esc(lang)}">\n'
        "<head>\n" + "\n".join(head) + "\n"
        f"<style>\n{sheet}</style>\n"
        "</head>\n"
        "<body>\n"
        '<main class="fg-doc">\n'
        f'<h1 class="sr-only">{_esc(title)}</h1>\n'
        + "\n".join(figures)
        + "\n</main>\n"
        "</body>\n"
        "</html>\n"
    )


# --------------------------------------------------------------------------- #
# DocumentRenderer port adapter                                                #
# --------------------------------------------------------------------------- #
class HtmlDocumentRenderer:
    """HTML/CSS output backend — the `DocumentRenderer` port, in-process.

    A thin adapter over `render_document`. It holds no per-run state: builder and
    painter are constructed per call, so the one shared instance in the backend
    registry is safe.
    """

    target = "html"
    kind = "web"
    blurb = "HTML/CSS (semantic shell + inline SVG; full engine parity)"

    def available(self) -> "str | None":
        return None  # pure Python — no optional dependency, no external binary

    def render(self, document, *, base_dir=None, options=None) -> RenderedArtifact:
        # `options` is unused: HTML takes no per-invocation knobs. It is accepted
        # to satisfy the port.
        return RenderedArtifact(
            pages=[render_document(document, base_dir)],
            media_type="text/html",
            extension="html",
            one_file_per_page=False,
        )
