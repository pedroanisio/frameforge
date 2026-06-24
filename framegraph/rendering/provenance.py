"""FrameForge provenance metatag for rendered documents.

A deterministic, tamper-evident stamp embedded in a rendered artifact: a sha256
content **fingerprint**, the producing **tool + version**, and an optional UTC
**sign timestamp**. It is a fingerprint, not a keyed cryptographic signature — the
same content always yields the same digest, so a changed render is detectable, but
it is not authenticated (the same model `recipe.sign` uses; swap in an HMAC if a
keyed signature is ever needed).

Opt-in by construction: nothing here runs in the default render path, so the
golden lock / byte-identical output is unaffected unless a caller explicitly signs.
A stamp with **no timestamp is fully deterministic** (reproducible signed output);
a stamp with a timestamp records when it was produced and is therefore not
byte-reproducible across runs — which is why signing is never on by default.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from framegraph.rendering.domain.geometry import esc

PROVENANCE_NS = "https://framegraph.dev/ns/provenance"
METATAG_VERSION = "1"
DEFAULT_TOOL = "framegraph"
DEFAULT_TOOL_VERSION = "2.2.0"


def content_fingerprint(content: str, length: int = 64) -> str:
    """sha256 hex digest of the rendered content — the tamper-evident key."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:length]


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 `Z` string (the sign timestamp)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class FrameForgeStamp:
    """A FrameForge provenance metatag for a rendered document."""
    fingerprint: str                       # 'sha256:<hex>'
    tool: str = DEFAULT_TOOL
    tool_version: str = DEFAULT_TOOL_VERSION
    timestamp: str | None = None           # ISO-8601 UTC, or None (deterministic)
    version: str = METATAG_VERSION

    def fields(self) -> dict[str, str]:
        out = {"version": self.version, "fingerprint": self.fingerprint,
               "tool": self.tool, "tool-version": self.tool_version}
        if self.timestamp:
            out["timestamp"] = self.timestamp
        return out

    def svg_metadata(self) -> str:
        """The stamp as an SVG `<metadata>` element (a `frameforge` child in a
        private provenance namespace)."""
        attrs = " ".join(f'{k}="{esc(str(v))}"' for k, v in self.fields().items())
        return f'<metadata><frameforge xmlns="{esc(PROVENANCE_NS)}" {attrs}/></metadata>'


def stamp(content: str, *, timestamp: str | bool | None = None,
          tool: str = DEFAULT_TOOL, tool_version: str = DEFAULT_TOOL_VERSION) -> FrameForgeStamp:
    """Build a provenance stamp for already-rendered `content`. `timestamp` may be an
    ISO string, `True` (= now, UTC), or `None`/`False` (deterministic, no time)."""
    ts = utc_now_iso() if timestamp is True else (timestamp or None)
    return FrameForgeStamp(fingerprint="sha256:" + content_fingerprint(content),
                           tool=tool, tool_version=tool_version, timestamp=ts)


def sign_svg(svg: str, *, timestamp: str | bool | None = None,
             tool: str = DEFAULT_TOOL, tool_version: str = DEFAULT_TOOL_VERSION) -> str:
    """Inject a FrameForge provenance `<metadata>` just after the opening `<svg …>`
    tag. The fingerprint covers the document **body** (everything between `<svg …>`
    and `</svg>`), so it is stable regardless of the metatag itself. Input that is
    not an `<svg>` document is returned unchanged."""
    if not svg.lstrip().startswith("<svg"):
        return svg
    open_end = svg.index(">") + 1
    head, rest = svg[:open_end], svg[open_end:]
    body = rest[: rest.rindex("</svg>")] if "</svg>" in rest else rest
    meta = stamp(body, timestamp=timestamp, tool=tool, tool_version=tool_version).svg_metadata()
    return head + meta + rest
