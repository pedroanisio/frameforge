"""Local web interface for FrameForge MCP feedback sessions."""
from __future__ import annotations

from frameforge.live.server import LiveSessionStore, serve

__all__ = ["LiveSessionStore", "serve"]
