"""Failure-only diagnostic output for Cloud Run debugging.

Enabled when ``HRD_DEBUG`` is true (set automatically by ``./deploy.sh --debug``).
Normal success paths stay silent.
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import Any

_ENABLED = os.environ.get('HRD_DEBUG', '').lower() in ('true', '1', 'yes')


def debug_enabled() -> bool:
    return _ENABLED


def debug_error(context: str, message: str, **details: Any) -> None:
    """Print a diagnostic line to stderr when HRD_DEBUG is on."""
    if not _ENABLED:
        return
    lines = [f'[HRD_DEBUG] {context}: {message}']
    for key, value in details.items():
        lines.append(f'  {key}={value!r}')
    print('\n'.join(lines), file=sys.stderr, flush=True)


def debug_exception(context: str, message: str, exc: BaseException, **details: Any) -> None:
    """Like :func:`debug_error` but includes the exception type and traceback."""
    if not _ENABLED:
        return
    debug_error(
        context,
        message,
        exc_type=type(exc).__name__,
        exc=str(exc),
        traceback=traceback.format_exc(),
        **details,
    )
