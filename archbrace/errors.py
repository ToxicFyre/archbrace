"""
Purpose:
    Define Archbrace's exception hierarchy so the CLI can map failures onto the
    documented exit codes (spec Section 4.5 / 9.4).

Why is this in this project:
    Centralizes the exception hierarchy so every layer signals failure the same
    way and the CLI can map it onto a stable exit code.

Inputs:
    None.

Outputs:
    Exception classes raised by configuration, analysis, and execution code.

Side effects:
    None.

Failure behavior:
    These types are the failure signals; they carry human-readable messages.
"""

from __future__ import annotations


class ArchbraceError(Exception):
    """Base class for all Archbrace errors that should map to exit code 2."""


class ConfigError(ArchbraceError):
    """Raised for missing, malformed, or invalid configuration."""


class AnalysisError(ArchbraceError):
    """Raised when a file cannot be read or parsed during analysis."""


class RuleExecutionError(ArchbraceError):
    """Raised when a rule raises during execution (never silently swallowed)."""
