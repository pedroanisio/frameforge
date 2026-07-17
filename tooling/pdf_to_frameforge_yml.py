#!/usr/bin/env python3
"""
pdf_to_frameforge_yml.py
========================

Transpile a PDF into a FrameForge v2 YAML document.

Goal
----
This is a deterministic, layout-preserving extractor, not a perfect PDF-to-UI
reverse compiler. It maps a PDF page into fixed-layout FrameForge pages:

- page size -> Page.canvas.size
- text spans -> text objects with tokenized text styles
- raster images -> image objects + extracted asset files
- simple vector drawings -> rect / line / path objects
- detected tables -> native ``type: table`` objects (PyMuPDF table finder)
- semantic graph -> page/object/image/text/vector/table nodes and containment edges

Codebase reuse
--------------
The output is built to validate against ``models/frameforge.py`` (the project's
source of truth). The document ``version`` is ``frameforge.HEAD_VERSION`` and the
generated tokens are HEAD-canonical ``Style`` projections — text styles use the
CSS-named keys (``font_family``/``font_size``/``font_weight``/``font_style``/
``text_align``) and stroke styles use the P3 single form (paint in ``stroke``,
geometry in ``stroke_width``), so the same resolvers that drive
``tooling/render_fixtures.py`` render the result with no migration. By default
the result is structurally self-checked with ``frameforge.Document`` before exit
(disable with ``--no-validate``).

Coordinate system
-----------------
FrameForge v2 uses top-left origin and +y down. PyMuPDF page coordinates are
also exposed in a top-left coordinate system for page text/drawings, so most
boxes can be copied directly.

Requirements
------------
    pip install pymupdf pyyaml

Usage
-----
    python pdf_to_frameforge_yml.py input.pdf output.frameforge.yml
    python pdf_to_frameforge_yml.py input.pdf output.yml --asset-dir assets
    python pdf_to_frameforge_yml.py input.pdf output.yml --max-pages 3
    python pdf_to_frameforge_yml.py input.pdf output.yml --no-images
    python pdf_to_frameforge_yml.py input.pdf output.yml --no-vectors
    python pdf_to_frameforge_yml.py input.pdf output.yml --text-mode lines
    python pdf_to_frameforge_yml.py input.pdf output.yml --table-mode off

Notes
-----
- Text is extracted from the PDF text layer. This script does not OCR scanned
  PDFs.
- Tables are detected with PyMuPDF's table finder and emitted as native
  ``type: table`` objects; the per-line text inside a detected table region is
  dropped so the table's own cells are the single source of that text. Detection
  works best on ruled/regularly-aligned tables and can miss or over-report on
  free-form layouts — pass ``--table-mode off`` to fall back to plain text.
- PDF fonts rarely map 1:1 to local renderer fonts. Each generated text style is
  mapped to a sans/serif/mono role; the originating PDF font names are recorded
  under the document ``meta.pdf_fonts`` provenance map.
- Complex paths, transparency groups, blend modes, masks, clipping paths, and
  shadings are approximated.
- Images are extracted as external files by default and referenced by relative
  path from the YAML location.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Reuse the model layer (the project's source of truth) for the HEAD version and
# the structural self-check. Same docs/models/ sys.path shim as tooling/validate.py.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "docs" / "models"))

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: PyYAML. Install with: pip install pyyaml"
    ) from exc

import frameforge as fg  # noqa: E402  (resolved via the models/ path inserted above)


def _import_fitz() -> Any:
    """Import PyMuPDF lazily so the module (and its pure helpers) load without it."""
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependency: PyMuPDF. Install with: pip install pymupdf"
        ) from exc
    return fitz


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def slug(value: str, fallback: str = "item") -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value).strip()).strip("_").lower()
    return s or fallback


def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def r2(n: float) -> float:
    """Round coordinates enough to keep YAML stable while preserving layout."""
    n = float(n)
    if abs(n - round(n)) < 0.01:
        return int(round(n))
    return round(n, 2)


def rect_to_box(rect: Any) -> list[float]:
    return [r2(rect.x0), r2(rect.y0), r2(rect.width), r2(rect.height)]


def point_to_xy(p: Any) -> list[float]:
    return [r2(p.x), r2(p.y)]


def _rgb_hex(r: int, g: int, b: int) -> str:
    return f"#{r & 255:02X}{g & 255:02X}{b & 255:02X}"


def int_rgb_to_hex(value: int | None, default: str = "#000000") -> str:
    if value is None:
        return default
    value = int(value)
    return _rgb_hex((value >> 16) & 255, (value >> 8) & 255, value & 255)


def float_rgb_to_hex(value: Any, default: str = "#000000") -> str:
    """PyMuPDF drawing colors are usually tuples of 0..1 floats."""
    if value is None:
        return default
    if isinstance(value, int):
        return int_rgb_to_hex(value, default)
    try:
        vals = list(value)
        if len(vals) < 3:
            return default
        r, g, b = (int(clamp(float(v), 0, 1) * 255) for v in vals[:3])
        return _rgb_hex(r, g, b)
    except Exception:
        return default


def safe_text(value: str) -> str:
    return value.replace("\u0000", "").strip("\n")


def stable_hash(data: bytes | str, n: int = 10) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    return hashlib.sha1(data).hexdigest()[:n]


def relpath_from(path: Path, base_file: Path) -> str:
    try:
        return os.path.relpath(path, start=base_file.parent).replace(os.sep, "/")
    except Exception:
        return str(path)


def intersection_area(a: Any, b: Any) -> float:
    """Overlap area of two fitz.Rect-like boxes (0 when disjoint)."""
    x0, y0 = max(a.x0, b.x0), max(a.y0, b.y0)
    x1, y1 = min(a.x1, b.x1), min(a.y1, b.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def overlap_ratio(inner: Any, outer: Any) -> float:
    """Fraction of ``inner``'s area covered by ``outer`` (0..1)."""
    area = max(inner.width * inner.height, 1e-6)
    return intersection_area(inner, outer) / area


def clean_cell_text(value: Any) -> str:
    """Normalise a detected table cell to single-line, collapsed whitespace."""
    s = "" if value is None else str(value)
    s = re.sub(r"[\u0000\u200b\u200c\ufeff]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def is_bold_font(font_name: str) -> bool:
    f = font_name.lower()
    return any(k in f for k in ("bold", "black", "heavy", "semibold", "demibold"))


def is_italic_font(font_name: str) -> bool:
    f = font_name.lower()
    return any(k in f for k in ("italic", "oblique"))


def family_class(font_name: str) -> str:
    f = font_name.lower()
    if any(k in f for k in ("mono", "courier", "code", "consolas")):
        return "mono"
    if any(k in f for k in ("times", "serif", "garamond", "georgia")):
        return "serif"
    return "sans"


def yaml_dump(data: dict[str, Any], path: Path) -> None:
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    text = yaml.dump(
        data,
        Dumper=NoAliasDumper,
        allow_unicode=True,
        sort_keys=False,
        width=120,
        default_flow_style=False,
    )
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Token store
# --------------------------------------------------------------------------- #

@dataclass
class TokenStore:
    """Deduping token tables. Text/stroke styles are emitted as HEAD-canonical
    ``Style`` projections so the document validates against models/frameforge.py
    and renders through the existing resolvers without a codemod pass."""

    colors: dict[str, str] = field(default_factory=dict)
    fonts: dict[str, Any] = field(default_factory=dict)
    text_styles: dict[str, Any] = field(default_factory=dict)
    stroke_styles: dict[str, Any] = field(default_factory=dict)
    styles: dict[str, Any] = field(default_factory=dict)
    # ts_key -> set of originating PDF font names (provenance, surfaced in meta).
    font_provenance: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.colors.setdefault("transparent", "rgba(0,0,0,0)")
        self.colors.setdefault("black", "#000000")
        self.colors.setdefault("white", "#FFFFFF")
        self.colors.setdefault("page_bg", "#FFFFFF")

        self.fonts.setdefault("sans", {"family": "DejaVu Sans", "fallback": ["Arial", "sans-serif"]})
        self.fonts.setdefault("serif", {"family": "DejaVu Serif", "fallback": ["Georgia", "Times New Roman", "serif"]})
        self.fonts.setdefault("mono", {"family": "DejaVu Sans Mono", "fallback": ["Consolas", "Courier New", "monospace"]})

    def add_color(self, hex_value: str | None, *, prefix: str = "c") -> str:
        if not hex_value:
            return "black"
        h = str(hex_value).upper()
        if not h.startswith("#"):
            return h
        key = f"{prefix}_{h.strip('#').lower()}"
        self.colors.setdefault(key, h)
        return key

    def default_text_style(self) -> str:
        self.text_styles.setdefault(
            "ts_default",
            {"font_family": "sans", "font_size": "10px", "color": "black"},
        )
        return "ts_default"

    def add_text_style(
        self,
        *,
        font: str,
        size: float,
        color: str,
        weight: int | str = 400,
        italic: bool = False,
        align: str = "left",
    ) -> str:
        family = family_class(font)
        color_ref = self.add_color(color, prefix="text")
        w = 700 if is_bold_font(font) else weight
        is_italic = italic or is_italic_font(font)
        style_hash = stable_hash(f"{family}|{size:.2f}|{color_ref}|{w}|{is_italic}|{align}", 8)
        key = f"ts_{style_hash}"
        if key not in self.text_styles:
            self.text_styles[key] = {
                "font_family": family,
                "font_size": f"{r2(size)}px",
                "font_weight": w,
                "font_style": "italic" if is_italic else "normal",
                "color": color_ref,
                "text_align": align,
                "line_height": 1.18,
            }
        self.font_provenance.setdefault(key, set()).add(font)
        return key

    def add_stroke_style(self, *, color: str, width: float, opacity: float | None = None) -> str:
        color_ref = self.add_color(color, prefix="stroke")
        style_hash = stable_hash(f"{color_ref}|{width:.3f}|{opacity}", 8)
        key = f"stroke_{style_hash}"
        if key not in self.stroke_styles:
            style = {"stroke": color_ref, "stroke_width": r2(width)}
            if opacity is not None:
                # `opacity` (not stroke_opacity) is the Style key the StrokeResolver
                # reads from a bundle (bundle.get("opacity")).
                style["opacity"] = round(opacity, 3)
            self.stroke_styles[key] = style
        return key

    def ensure_table_tokens(self) -> dict[str, str]:
        """Seed (once) the tokens a detected table references and return the refs.

        Lazy so documents with no tables carry no unused table tokens. The grid is
        the P3 single form (paint in ``stroke``); header/cell text are canonical
        ``Style`` projections, matching the rest of this generator."""
        self.colors.setdefault("table_grid", "#5A5A5A")
        self.colors.setdefault("table_header_bg", "#E6E6E6")
        self.stroke_styles.setdefault("table_grid", {"stroke": "table_grid", "stroke_width": 0.75})
        self.text_styles.setdefault("table_header", {
            "font_family": "sans", "font_size": "8.5px", "font_weight": 700,
            "color": "black", "text_align": "left", "line_height": 1.15,
        })
        self.text_styles.setdefault("table_cell", {
            "font_family": "sans", "font_size": "8px", "font_weight": 400,
            "color": "black", "text_align": "left", "line_height": 1.12,
        })
        return {"grid": "table_grid", "header_fill": "table_header_bg",
                "header_text": "table_header", "cell_text": "table_cell"}


# --------------------------------------------------------------------------- #
# Extraction core
# --------------------------------------------------------------------------- #

@dataclass
class ExtractionOptions:
    asset_dir: Path
    output_file: Path
    text_mode: str = "lines"  # spans | lines | blocks
    include_images: bool = True
    include_vectors: bool = True
    include_background: bool = True
    embed_images: bool = False
    max_pages: int | None = None
    min_vector_area: float = 0.5
    table_mode: str = "native"  # native | off
    table_min_cells: int = 4
    table_skip_text_overlap: float = 0.45


class PDFToFrameForge:
    def __init__(self, pdf_path: Path, options: ExtractionOptions):
        self.pdf_path = pdf_path
        self.options = options
        self.tokens = TokenStore()
        self.object_ids: set[str] = set()
        self.semantic_nodes: list[dict[str, Any]] = []
        self.semantic_edges: list[dict[str, Any]] = []
        self.image_xref_seen: dict[int, str] = {}
        self.table_stats: dict[str, int] = {"tables": 0, "cells": 0, "skipped_text": 0}
        self.fitz: Any = None  # bound lazily in transpile()

    def unique_id(self, raw: str) -> str:
        base = slug(raw)
        candidate = base
        i = 2
        while candidate in self.object_ids:
            candidate = f"{base}_{i}"
            i += 1
        self.object_ids.add(candidate)
        return candidate

    # ---- object / semantic scaffolding (shared by every extractor) -------- #
    def _new_object(self, oid: str, otype: str, meta: dict[str, Any], **fields: Any) -> dict[str, Any]:
        """Build an object with the common id/bind/meta scaffold."""
        obj: dict[str, Any] = {"type": otype, "id": oid}
        obj.update(fields)
        obj["bind"] = oid
        obj["meta"] = meta
        return obj

    def add_sem_node(self, node_id: str, typ: str, label: str, **meta: Any) -> None:
        node = {"id": node_id, "type": typ, "label": label}
        if meta:
            node["meta"] = meta
        self.semantic_nodes.append(node)

    def add_sem_edge(self, edge_id: str, typ: str, src: str, dst: str, **meta: Any) -> None:
        edge = {"id": edge_id, "type": typ, "from": src, "to": dst}
        if meta:
            edge["meta"] = meta
        self.semantic_edges.append(edge)

    def _register(self, page_id: str, oid: str, sem_type: str, label: str, **sem_meta: Any) -> None:
        """Add the semantic node + ``derived_from`` edge for an extracted object."""
        self.add_sem_node(oid, sem_type, label, **sem_meta)
        self.add_sem_edge(f"{page_id}_{oid}_derived", "derived_from", page_id, oid)

    def _fill_ref(self, fill: str | None) -> str:
        return self.tokens.add_color(fill, prefix="fill") if fill else "none"

    def _apply_paint(self, obj: dict[str, Any], fill: str | None, stroke_style: str | None) -> None:
        obj["fill"] = self._fill_ref(fill)
        if stroke_style:
            obj["stroke_style"] = stroke_style

    def transpile(self) -> dict[str, Any]:
        self.fitz = _import_fitz()
        pdf = self.fitz.open(self.pdf_path)
        self.add_sem_node("doc", "document", self.pdf_path.name, pages=len(pdf))

        page_count = len(pdf)
        if self.options.max_pages is not None:
            page_count = min(page_count, self.options.max_pages)

        self.options.asset_dir.mkdir(parents=True, exist_ok=True)

        pages = [self._page(pdf[i], i) for i in range(page_count)]
        first_size = [r2(pdf[0].rect.width), r2(pdf[0].rect.height)] if len(pdf) else None
        return self._assemble(pages, first_size)

    def _page(self, page: Any, page_index: int) -> dict[str, Any]:
        page_id = f"page_{page_index + 1}"
        self.add_sem_node(page_id, "page", f"Page {page_index + 1}", page_index=page_index)

        page_w, page_h = r2(page.rect.width), r2(page.rect.height)
        layers: list[dict[str, Any]] = []

        if self.options.include_background:
            layers.append({
                "id": "background",
                "z": 0,
                "objects": [{
                    "type": "rect",
                    "id": self.unique_id(f"{page_id}_background"),
                    "box": [0, 0, page_w, page_h],
                    "fill": "page_bg",
                    "decorative": True,
                }],
            })

        # Tables first: their bounding boxes mask out the duplicate per-line text
        # that the text pass would otherwise emit on top of the table.
        table_objects, table_regions = (
            self.extract_tables(page, page_id)
            if self.options.table_mode == "native"
            else ([], [])
        )
        vector_objects = self.extract_vectors(page, page_id) if self.options.include_vectors else []
        image_objects = self.extract_images(page, page_id) if self.options.include_images else []
        text_objects = self.extract_text(page, page_id, table_regions)
        for layer_id, z, objects in (
            ("vectors", 1, vector_objects),
            ("images", 2, image_objects),
            ("tables", 3, table_objects),
            ("text", 4, text_objects),
        ):
            if objects:
                layers.append({"id": layer_id, "z": z, "objects": objects})

        page_dict = {
            "mode": "page",
            "id": page_id,
            "canvas": {"size": [page_w, page_h], "units": "px"},
            "rendering": {
                "coordinate_mode": "absolute",
                "preserve_manual_line_breaks": True,
                # PDF boxes are sized to the source font; a re-rendering font is
                # usually wider, so `clip` would silently drop the tail of every
                # tight line. `shrink_to_fit` scales text down to its box instead,
                # preserving all content (the §9.6 text-fit contract). min_font_size
                # floors the shrink so nothing collapses to nothing.
                "text": {"overflow": "shrink_to_fit", "min_font_size": 3},
            },
            "semantic": {
                "nodes": [n for n in self.semantic_nodes
                          if n["id"] == page_id or n["id"].startswith(page_id + "_")],
                "edges": [e for e in self.semantic_edges if e["id"].startswith(page_id + "_")],
            },
            "layers": layers,
            "meta": {
                "pdf_page_index": page_index,
                "pdf_page_number": page_index + 1,
                "rotation": page.rotation,
                "mediabox": [r2(x) for x in page.mediabox],
                "cropbox": [r2(x) for x in page.cropbox],
                "detected_tables": len(table_objects),
            },
        }
        self.add_sem_edge(f"{page_id}_contained_by_doc", "contains", "doc", page_id)
        return page_dict

    def _assemble(self, pages: list[dict[str, Any]], first_size: list[float] | None) -> dict[str, Any]:
        return {
            "dsl": "FrameForge",
            "version": fg.HEAD_VERSION,
            "profile": "mixed" if len(pages) > 1 else "diagram",
            "title": f"FrameForge extraction — {self.pdf_path.name}",
            "description": "Generated by pdf_to_frameforge_yml.py from a PDF text/layout/vector/image extraction pass.",
            "lang": "und",
            "defs": {
                "tokens": {
                    "colors": self.tokens.colors,
                    "fonts": self.tokens.fonts,
                    "text_styles": self.tokens.text_styles,
                    "stroke_styles": self.tokens.stroke_styles,
                    "styles": self.tokens.styles,
                },
                "ontology": {
                    "node_types": {
                        "document": {"meaning": "Source PDF document"},
                        "page": {"meaning": "PDF page converted to a fixed FrameForge page"},
                        "text": {"meaning": "Extracted text run, line, or block"},
                        "image": {"meaning": "Extracted raster image placement"},
                        "vector": {"meaning": "Extracted vector drawing primitive"},
                        "table": {"meaning": "Detected table emitted as a native table object"},
                    },
                    "edge_types": {
                        "contains": {"meaning": "Containment relation", "directionality": "directed"},
                        "derived_from": {"meaning": "FrameForge object derived from PDF source element", "directionality": "directed"},
                    },
                },
            },
            "targets": [
                {
                    "name": "pdf-native",
                    "canvas": {"size": first_size, "units": "px"},
                }
            ] if first_size else [],
            "pages": pages,
            "meta": self._doc_meta(),
        }

    def _doc_meta(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "source_pdf": str(self.pdf_path),
            "generator": "pdf_to_frameforge_yml.py",
            "generator_scope": {
                "ocr": False,
                "text_layer_required": True,
                "vectors": self.options.include_vectors,
                "images": self.options.include_images,
                "image_embedding": self.options.embed_images,
                "tables": self.options.table_mode,
            },
            "warnings": [
                "This is an approximation. PDF render semantics such as masks, blend modes, shadings, ligatures, complex scripts, and clipping paths may not be preserved exactly.",
                "Text re-rendering depends on available fonts and can differ from the source PDF.",
            ],
        }
        if self.tokens.font_provenance:
            meta["pdf_fonts"] = {k: sorted(v) for k, v in self.tokens.font_provenance.items()}
        if self.options.table_mode == "native":
            meta["table_stats"] = dict(self.table_stats)
        return meta

    # --------------------------------------------------------------------- #
    # Tables (native FrameForge `type: table` objects)
    # --------------------------------------------------------------------- #

    def extract_tables(self, page: Any, page_id: str) -> tuple[list[dict[str, Any]], list[Any]]:
        """Detect tables and emit them as native ``type: table`` objects.

        Returns ``(objects, regions)``; ``regions`` are the table bounding boxes so
        ``extract_text`` can drop the duplicate per-line text inside them — the
        table's own cells become the single source of that content."""
        objects: list[dict[str, Any]] = []
        regions: list[Any] = []
        for ti, tbl in enumerate(self.find_tables(page)):
            obj = self._table_object(tbl, page_id, ti)
            if obj is None:
                continue
            objects.append(obj)
            regions.append(tbl["bbox"])
            self.table_stats["tables"] += 1
        return objects, regions

    def find_tables(self, page: Any) -> list[dict[str, Any]]:
        """Normalise PyMuPDF table detection to ``{bbox, matrix, ncol, col_widths}``."""
        try:
            finder = page.find_tables()
            raw = list(getattr(finder, "tables", []) or [])
        except Exception:
            return []

        out: list[dict[str, Any]] = []
        for tbl in raw:
            try:
                matrix = [[clean_cell_text(c) for c in row] for row in tbl.extract()]
            except Exception:
                continue
            matrix = [row for row in matrix if row]
            if not matrix:
                continue
            ncol = max(len(r) for r in matrix)
            matrix = [r + [""] * (ncol - len(r)) for r in matrix]   # rectangular grid

            total = sum(len(r) for r in matrix)
            non_empty = sum(1 for r in matrix for c in r if c)
            if total < self.options.table_min_cells and non_empty < 2:
                continue

            bbox = self.fitz.Rect(tbl.bbox)
            if bbox.is_empty:
                continue
            out.append({
                "bbox": bbox,
                "matrix": matrix,
                "ncol": ncol,
                "col_widths": self._column_widths(tbl, ncol),
            })
        return out

    def _column_widths(self, tbl: Any, ncol: int) -> list[float] | None:
        """Per-column pixel widths from detected cell geometry (layout-preserving).

        Reads the per-row ``cells`` (row-major, column-ordered) — the flat
        ``tbl.cells`` is column-major, so column index there is not ``idx % ncol``.
        Returns ``None`` when the geometry is incomplete so the renderer falls back
        to an equal split rather than emitting bogus widths."""
        try:
            row_objs = list(getattr(tbl, "rows", []) or [])
        except Exception:
            row_objs = []
        if not row_objs or ncol <= 0:
            return None
        lefts: list[float | None] = [None] * ncol
        rights: list[float | None] = [None] * ncol
        for row in row_objs:
            for ci, cell in enumerate(list(getattr(row, "cells", []) or [])[:ncol]):
                if cell is None:
                    continue
                rect = self.fitz.Rect(cell)
                lefts[ci] = rect.x0 if lefts[ci] is None else min(lefts[ci], rect.x0)
                rights[ci] = rect.x1 if rights[ci] is None else max(rights[ci], rect.x1)
        widths: list[float] = []
        for lo, hi in zip(lefts, rights):
            if lo is None or hi is None or hi <= lo:
                return None
            widths.append(hi - lo)
        return widths

    def _table_object(self, tbl: dict[str, Any], page_id: str, ti: int) -> dict[str, Any] | None:
        matrix: list[list[str]] = tbl["matrix"]
        if not matrix:
            return None
        refs = self.tokens.ensure_table_tokens()

        header: list[str] | None = None
        rows = matrix
        if len(matrix) > 1 and self._looks_like_header(matrix[0]):
            header, rows = matrix[0], matrix[1:]

        oid = self.unique_id(f"{page_id}_table_{ti}")
        fields: dict[str, Any] = {"box": rect_to_box(tbl["bbox"])}
        if header is not None:
            fields["header"] = header
        cols = tbl.get("col_widths")
        if cols:
            fields["columns"] = [{"width": r2(w), "align": "left"} for w in cols]
        fields.update({
            "rows": rows,
            "zebra": True,
            "cell_padding": 2,
            "stroke_style": refs["grid"],
            "style": {
                "header_fill": refs["header_fill"],
                "header_text": refs["header_text"],
                "cell_text": refs["cell_text"],
            },
        })
        obj = self._new_object(
            oid, "table",
            {"pdf_table_index": ti, "detector": "pymupdf.find_tables",
             "rows": len(rows), "cols": tbl["ncol"]},
            **fields,
        )
        self.table_stats["cells"] += sum(1 for r in rows for c in r if c)
        if header:
            self.table_stats["cells"] += sum(1 for c in header if c)
        self._register(page_id, oid, "table", f"Table {ti + 1}",
                       pdf_table_index=ti, rows=len(rows), cols=tbl["ncol"])
        return obj

    @staticmethod
    def _looks_like_header(first_row: list[str]) -> bool:
        """Heuristic: a short, mostly-labels first row reads as a header.

        Crude by design (no font/rule signal here); errs toward *not* promoting a
        row, so a misfire leaves the data in the body rather than losing it."""
        labels = [c for c in first_row if c]
        if len(labels) < 2:
            return False
        avg_len = sum(len(c) for c in labels) / len(labels)
        return avg_len <= 28

    # --------------------------------------------------------------------- #
    # Text
    # --------------------------------------------------------------------- #

    def extract_text(self, page: Any, page_id: str,
                     table_regions: list[Any] | None = None) -> list[dict[str, Any]]:
        raw = page.get_text("dict", flags=self.fitz.TEXTFLAGS_DICT)
        objects: list[dict[str, Any]] = []
        regions = table_regions or []
        for unit in self._text_units(raw):
            if regions and self._box_in_tables(unit["box"], regions):
                self.table_stats["skipped_text"] += 1
                continue
            oid = self.unique_id(f"{page_id}_{unit['id']}")
            objects.append(self._new_object(
                oid, "text", unit["meta"],
                text=unit["text"], box=unit["box"], style=unit["style"],
            ))
            self._register(page_id, oid, "text", unit["text"][:80], **unit["sem"])
        return objects

    def _box_in_tables(self, box: list[float], regions: list[Any]) -> bool:
        """True when a text unit's box lies mostly inside a detected table region."""
        x, y, w, h = box
        rect = self.fitz.Rect(x, y, x + w, y + h)
        thr = self.options.table_skip_text_overlap
        return any(overlap_ratio(rect, tr) >= thr for tr in regions)

    def _text_units(self, raw: dict[str, Any]):
        """Yield mode-specific text units as {id, text, box, style, meta, sem}.

        The three text modes differ only in granularity and the index keys they
        record; the object/semantic emission in extract_text is shared."""
        mode = self.options.text_mode
        for bi, block in enumerate(raw.get("blocks", [])):
            if block.get("type") != 0:
                continue

            if mode == "blocks":
                text = self.block_text(block)
                if not text.strip():
                    continue
                first = self.first_span(block)
                style = self.style_for_span(first) if first else self.tokens.default_text_style()
                yield {
                    "id": f"text_block_{bi}",
                    "text": text,
                    "box": rect_to_box(self.fitz.Rect(block["bbox"])),
                    "style": style,
                    "meta": {"pdf_block_index": bi, "extract_mode": "block"},
                    "sem": {"pdf_block_index": bi},
                }
                continue

            for li, line in enumerate(block.get("lines", [])):
                if mode == "lines":
                    spans = [s for s in line.get("spans", []) if safe_text(s.get("text", ""))]
                    if not spans:
                        continue
                    text = "".join(s.get("text", "") for s in spans).strip()
                    if not text:
                        continue
                    yield {
                        "id": f"text_line_{bi}_{li}",
                        "text": text,
                        "box": rect_to_box(self.fitz.Rect(line["bbox"])),
                        "style": self.style_for_span(spans[0]),
                        "meta": {"pdf_block_index": bi, "pdf_line_index": li, "extract_mode": "line"},
                        "sem": {"pdf_block_index": bi, "pdf_line_index": li},
                    }
                    continue

                for si, span in enumerate(line.get("spans", [])):  # spans mode
                    text = safe_text(span.get("text", ""))
                    if not text:
                        continue
                    yield {
                        "id": f"text_span_{bi}_{li}_{si}",
                        "text": text,
                        "box": rect_to_box(self.fitz.Rect(span["bbox"])),
                        "style": self.style_for_span(span),
                        "meta": {"pdf_block_index": bi, "pdf_line_index": li,
                                 "pdf_span_index": si, "extract_mode": "span"},
                        "sem": {"pdf_block_index": bi, "pdf_line_index": li, "pdf_span_index": si},
                    }

    def first_span(self, block: dict[str, Any]) -> dict[str, Any] | None:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if safe_text(span.get("text", "")):
                    return span
        return None

    def block_text(self, block: dict[str, Any]) -> str:
        lines: list[str] = []
        for line in block.get("lines", []):
            s = "".join(span.get("text", "") for span in line.get("spans", []))
            if s.strip():
                lines.append(s.rstrip())
        return "\n".join(lines)

    def style_for_span(self, span: dict[str, Any]) -> str:
        font = span.get("font", "sans")
        size = float(span.get("size", 10))
        color = int_rgb_to_hex(span.get("color", 0), "#000000")
        flags = int(span.get("flags", 0))
        italic = bool(flags & 2) or is_italic_font(font)
        weight = 700 if is_bold_font(font) else 400
        return self.tokens.add_text_style(
            font=font,
            size=size,
            color=color,
            weight=weight,
            italic=italic,
            align="left",
        )

    # --------------------------------------------------------------------- #
    # Images
    # --------------------------------------------------------------------- #

    def extract_images(self, page: Any, page_id: str) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []

        for ii, info in enumerate(page.get_image_info(xrefs=True)):
            bbox = self.fitz.Rect(info["bbox"])
            if bbox.is_empty:
                continue

            xref = info.get("xref")
            meta: dict[str, Any] = {
                "pdf_image_index": ii,
                "xref": xref,
                "width": info.get("width"),
                "height": info.get("height"),
                "colorspace": info.get("colorspace"),
            }

            oid = self.unique_id(f"{page_id}_image_{ii}")
            objects.append(self._new_object(
                oid, "image", meta,
                src=self._image_src(page.parent, xref, page_id, ii),
                box=rect_to_box(bbox),
                preserve_aspect_ratio=True,
            ))
            self._register(page_id, oid, "image", f"Image {ii + 1}", **meta)

        return objects

    def _image_src(self, pdf: Any, xref: int | None, page_id: str, index: int) -> str:
        if self.options.embed_images:
            src = self._image_data_uri(pdf, xref)
        else:
            path = self._extract_image_asset(pdf, xref, page_id, index)
            src = relpath_from(Path(path), self.options.output_file) if path else None
        return src or f"missing-image-xref-{xref or index}"

    def _load_image(self, pdf: Any, xref: int | None) -> tuple[str, bytes] | None:
        """Decode an image xref to (ext, data); shared by asset + data-uri paths."""
        if not xref:
            return None
        try:
            image = pdf.extract_image(xref)
        except Exception:
            return None
        data = image.get("image")
        if not data:
            return None
        return image.get("ext", "png"), data

    def _extract_image_asset(self, pdf: Any, xref: int | None, page_id: str, index: int) -> str | None:
        if xref in self.image_xref_seen:
            return self.image_xref_seen[xref]
        loaded = self._load_image(pdf, xref)
        if not loaded:
            return None
        ext, data = loaded
        name = f"{page_id}_img_{index + 1}_xref_{xref}.{ext}"
        path = self.options.asset_dir / name
        path.write_bytes(data)
        self.image_xref_seen[xref] = str(path)
        return str(path)

    def _image_data_uri(self, pdf: Any, xref: int | None) -> str | None:
        loaded = self._load_image(pdf, xref)
        if not loaded:
            return None
        ext, data = loaded
        mime = "jpeg" if ext.lower() in ("jpg", "jpeg") else ext.lower()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/{mime};base64,{b64}"

    # --------------------------------------------------------------------- #
    # Vectors
    # --------------------------------------------------------------------- #

    def extract_vectors(self, page: Any, page_id: str) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        try:
            drawings = page.get_drawings()
        except Exception:
            return objects

        for di, drawing in enumerate(drawings):
            rect = self.fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
            if rect.width * rect.height < self.options.min_vector_area and not drawing.get("items"):
                continue

            fill = float_rgb_to_hex(drawing.get("fill"), None)
            stroke = float_rgb_to_hex(drawing.get("color"), None)
            width = float(drawing.get("width") or 1.0)
            stroke_style = self.tokens.add_stroke_style(color=stroke, width=width) if stroke else None

            # If one drawing is a single rect/line item, emit that primitive.
            simple = self._simple_vector(drawing, page_id, di, fill, stroke_style)
            if simple:
                objects.append(simple)
                continue

            # Otherwise emit a path approximation.
            d = self.drawing_to_svg_path(drawing)
            if not d:
                continue

            oid = self.unique_id(f"{page_id}_path_{di}")
            obj = self._new_object(
                oid, "path",
                {"pdf_drawing_index": di, "approximation": "path from PyMuPDF drawing items"},
                d=d,
            )
            self._apply_paint(obj, fill, stroke_style)
            objects.append(obj)
            self._register(page_id, oid, "vector", f"Path {di + 1}", pdf_drawing_index=di)

        return objects

    def _simple_vector(
        self,
        drawing: dict[str, Any],
        page_id: str,
        index: int,
        fill: str | None,
        stroke_style: str | None,
    ) -> dict[str, Any] | None:
        items = drawing.get("items") or []
        if len(items) != 1:
            return None
        item = items[0]
        op = item[0]

        # PyMuPDF rect item: ("re", Rect, orientation)
        if op == "re":
            oid = self.unique_id(f"{page_id}_rect_{index}")
            obj = self._new_object(
                oid, "rect",
                {"pdf_drawing_index": index, "source_operator": "re"},
                box=rect_to_box(self.fitz.Rect(item[1])),
            )
            self._apply_paint(obj, fill, stroke_style)
            self._register(page_id, oid, "vector", f"Rect {index + 1}", pdf_drawing_index=index)
            return obj

        # PyMuPDF line item: ("l", Point, Point)
        if op == "l":
            oid = self.unique_id(f"{page_id}_line_{index}")
            obj = self._new_object(
                oid, "line",
                {"pdf_drawing_index": index, "source_operator": "l"},
                **{"from": point_to_xy(item[1]), "to": point_to_xy(item[2])},
            )
            if stroke_style:
                obj["stroke_style"] = stroke_style
            self._register(page_id, oid, "vector", f"Line {index + 1}", pdf_drawing_index=index)
            return obj

        return None

    def drawing_to_svg_path(self, drawing: dict[str, Any]) -> str:
        parts: list[str] = []
        current: list[float] | None = None
        for item in drawing.get("items") or []:
            op = item[0]
            try:
                if op == "l":
                    p1, p2 = item[1], item[2]
                    if current != [r2(p1.x), r2(p1.y)]:
                        parts.append(f"M {r2(p1.x)} {r2(p1.y)}")
                    parts.append(f"L {r2(p2.x)} {r2(p2.y)}")
                    current = [r2(p2.x), r2(p2.y)]
                elif op == "c":
                    p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                    if current != [r2(p1.x), r2(p1.y)]:
                        parts.append(f"M {r2(p1.x)} {r2(p1.y)}")
                    parts.append(
                        f"C {r2(p2.x)} {r2(p2.y)} {r2(p3.x)} {r2(p3.y)} {r2(p4.x)} {r2(p4.y)}"
                    )
                    current = [r2(p4.x), r2(p4.y)]
                elif op == "qu":
                    quad = item[1]
                    # Quad points: ul, ur, ll, lr. Approximate as polygon.
                    pts = [quad.ul, quad.ur, quad.lr, quad.ll]
                    parts.append(f"M {r2(pts[0].x)} {r2(pts[0].y)}")
                    for p in pts[1:]:
                        parts.append(f"L {r2(p.x)} {r2(p.y)}")
                    parts.append("Z")
                    current = None
                elif op == "re":
                    rect = self.fitz.Rect(item[1])
                    x0, y0, x1, y1 = r2(rect.x0), r2(rect.y0), r2(rect.x1), r2(rect.y1)
                    parts.append(f"M {x0} {y0} L {x1} {y0} L {x1} {y1} L {x0} {y1} Z")
                    current = None
            except Exception:
                continue
        return " ".join(parts)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Transpile PDF pages into a fixed-layout FrameForge v2 YAML document."
    )
    p.add_argument("input_pdf", type=Path, help="Input PDF")
    p.add_argument("output_yml", type=Path, help="Output FrameForge YAML")
    p.add_argument(
        "--asset-dir",
        type=Path,
        default=None,
        help="Directory for extracted image assets. Default: <output>.assets/",
    )
    p.add_argument(
        "--text-mode",
        choices=["spans", "lines", "blocks"],
        default="lines",
        help="Granularity for extracted text objects. Default: lines.",
    )
    p.add_argument("--max-pages", type=int, default=None, help="Limit the number of converted pages.")
    p.add_argument("--no-images", action="store_true", help="Skip raster image extraction.")
    p.add_argument("--no-vectors", action="store_true", help="Skip vector drawing extraction.")
    p.add_argument("--no-background", action="store_true", help="Do not add a white page background rect.")
    p.add_argument(
        "--embed-images",
        action="store_true",
        help="Embed extracted images as data URIs instead of writing asset files. Can make YAML very large.",
    )
    p.add_argument(
        "--min-vector-area",
        type=float,
        default=0.5,
        help="Drop empty/tiny vector drawings below this area. Default: 0.5.",
    )
    p.add_argument(
        "--table-mode",
        choices=["native", "off"],
        default="native",
        help="native = detect tables and emit native `type: table` objects (dropping "
             "the duplicate text inside them); off = no table detection. Default: native.",
    )
    p.add_argument(
        "--table-min-cells",
        type=int,
        default=4,
        help="Minimum detected cells before a region is emitted as a table. Default: 4.",
    )
    p.add_argument(
        "--table-skip-text-overlap",
        type=float,
        default=0.45,
        help="Drop extracted text whose box is at least this fraction inside a detected "
             "table region. Default: 0.45.",
    )
    p.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip the structural self-check against models/frameforge.py.",
    )
    return p.parse_args(argv)


def _validate(doc: dict[str, Any]) -> None:
    """Structural self-check against the model layer (non-fatal, advisory)."""
    try:
        fg.Document.model_validate(doc)
        print("Validation: PASS (conforms to models/frameforge.py)")
    except Exception as exc:  # pragma: no cover - depends on PDF content
        print(f"Validation: WARN — output did not fully validate against the model:\n{exc}",
              file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.input_pdf.exists():
        raise SystemExit(f"Input PDF not found: {args.input_pdf}")

    asset_dir = args.asset_dir
    if asset_dir is None:
        asset_dir = args.output_yml.with_suffix("").with_name(args.output_yml.stem + ".assets")

    opts = ExtractionOptions(
        asset_dir=asset_dir,
        output_file=args.output_yml,
        text_mode=args.text_mode,
        include_images=not args.no_images,
        include_vectors=not args.no_vectors,
        include_background=not args.no_background,
        embed_images=args.embed_images,
        max_pages=args.max_pages,
        min_vector_area=args.min_vector_area,
        table_mode=args.table_mode,
        table_min_cells=args.table_min_cells,
        table_skip_text_overlap=args.table_skip_text_overlap,
    )

    converter = PDFToFrameForge(args.input_pdf, opts)
    frameforge = converter.transpile()
    args.output_yml.parent.mkdir(parents=True, exist_ok=True)
    yaml_dump(frameforge, args.output_yml)

    page_count = len(frameforge.get("pages", []))
    obj_count = sum(
        len(layer.get("objects", []))
        for page in frameforge.get("pages", [])
        for layer in page.get("layers", [])
    )

    print(f"Wrote {args.output_yml}")
    print(f"Pages: {page_count}")
    print(f"Top-level layer objects: {obj_count}")
    if opts.table_mode == "native":
        ts = converter.table_stats
        print(f"Tables: {ts['tables']} ({ts['cells']} cells; "
              f"{ts['skipped_text']} duplicate text objects dropped)")
    if opts.include_images and not opts.embed_images:
        print(f"Assets: {asset_dir}")

    if not args.no_validate:
        _validate(frameforge)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
