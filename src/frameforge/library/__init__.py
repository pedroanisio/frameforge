"""frameforge.library — themes, symbol packs, generators (issue #32).

A bounded context in the §13 layout: the content library absorbed from the
predecessor project — 7 consulting token packs as v2 ``defs.tokens``
fragments, 4 symbol packs (cover, agenda pane, insight box / KPI card /
2×2 / stencil node, hex cells) instantiable through grammar-level ``use``,
and 2 data-driven page generators (honeycomb capability map, radial module
hub). All content is committed under ``data/``; nothing here touches the
document schema.
"""
from frameforge.library.generators import (
    EXAMPLES_DIR,
    HONEYCOMB_GEOMETRY,
    HONEYCOMB_PALETTE,
    MODULE_GEOMETRY,
    MODULE_PALETTE,
    honeycomb_capability_map,
    load_example,
    module_hub_radial,
)
from frameforge.library.symbols import (
    SYMBOLS_DIR,
    list_symbols,
    load_symbols,
    support_text_styles,
)
from frameforge.library.themes import THEMES_DIR, list_themes, load_theme

__all__ = [
    "EXAMPLES_DIR",
    "HONEYCOMB_GEOMETRY",
    "HONEYCOMB_PALETTE",
    "MODULE_GEOMETRY",
    "MODULE_PALETTE",
    "SYMBOLS_DIR",
    "THEMES_DIR",
    "honeycomb_capability_map",
    "list_symbols",
    "list_themes",
    "load_example",
    "load_symbols",
    "load_theme",
    "module_hub_radial",
    "support_text_styles",
]
