"""Mandol-AML: an Agent Memory Leaderboard (AML) adapter for the Mandol memory system.

This package adds a synchronous ``Add`` / ``Search`` / ``Health`` HTTP layer on
top of Mandol's SemanticMap / SemanticGraph core. It does not modify Mandol
itself; it is designed to be placed under ``src/`` of a fork of
https://github.com/AgentCombo/Mandol and installed together with it.
"""

from __future__ import annotations

from .version import __version__

__all__ = ["__version__"]
