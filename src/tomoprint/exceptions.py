"""Exception hierarchy for tomoprint."""

from __future__ import annotations


class TomoprintError(Exception):
    """Base class for all tomoprint errors."""


class ValidationError(TomoprintError, ValueError):
    """Raised when a parameter or input value is invalid."""


class NonManifoldError(TomoprintError):
    """Raised when a mesh fails watertight/manifold verification and cannot be repaired.

    The ``diagnostics`` attribute carries the dict returned by
    :func:`tomoprint.mesh.verify_watertight` so callers (CLI/GUI) can surface it.
    """

    def __init__(self, message: str, diagnostics: dict | None = None) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics or {}
