"""Local web interface for FrameGraph MCP feedback sessions."""
from __future__ import annotations

from framegraph.live.server import LiveSessionStore, serve

__all__ = ["LiveSessionStore", "serve"]
