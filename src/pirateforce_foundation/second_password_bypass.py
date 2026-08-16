"""Server-selectable proactive Second Password success.

The response bytes are the already accepted V110 result=OK packet.  Sending
that packet after runtime readiness, before a client request, is deliberately
tracked as HYP-PF-009.  The stable server parameter defaults to ``required``;
``bypass`` must be explicitly selected for a local server run.
"""

from __future__ import annotations

import hashlib
from typing import Any


SECOND_PASSWORD_OK_PC_SHA256 = (
    "5C29ED7BCBA475B8B3E71570622E6E0BAD98C7790153BBDA2560289505C99B36"
)
SECOND_PASSWORD_OK_FRAME_SHA256 = (
    "7AEE68CCB80484793EB45471EE13ED197D352AFF6ED3AF03CC9C7A2CB8ACEE05"
)


SECOND_PASSWORD_MODES = ("required", "bypass")


def require_second_password_mode(value: Any) -> str:
    if type(value) is not str or value not in SECOND_PASSWORD_MODES:
        raise ValueError("second-password mode must be exactly required or bypass")
    return value


def make_proactive_second_password_ok(
    legacy: Any, mode: str,
) -> tuple[bytes, bytes]:
    """Build and hash-pin the accepted packet at the hypothesized timing."""
    # PF-HYPOTHESIS-LEDGER: HYP-PF-009 active
    if require_second_password_mode(mode) != "bypass":
        raise ValueError("proactive Second Password OK requires bypass mode")
    pc, frame = legacy.make_check_second_password_success()
    if (
        len(pc) != 34
        or hashlib.sha256(pc).hexdigest().upper()
        != SECOND_PASSWORD_OK_PC_SHA256
    ):
        raise RuntimeError("HYP-PF-009 response PC drift")
    if (
        len(frame) != 44
        or hashlib.sha256(frame).hexdigest().upper()
        != SECOND_PASSWORD_OK_FRAME_SHA256
    ):
        raise RuntimeError("HYP-PF-009 response frame drift")
    return pc, frame
