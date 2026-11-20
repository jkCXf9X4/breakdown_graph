"""Exceptions shared by loader, exporters and the CLI."""

from __future__ import annotations


class BreakdownError(Exception):
    """Base class for user-facing failures."""


class ExportError(BreakdownError):
    """An export cannot be written safely."""
