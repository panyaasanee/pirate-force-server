"""GM-005: a staged login scene is spent by the login that uses it.

`COO-DECISION 20260829_0441` approved `/warp <scene_id>` staging the next
login's scene and attached one condition to the approval:

    override เป็น single-use -- อ่านแล้ว ลบ/ทำเครื่องหมายบริโภคทันทีใน
    การล็อกอินนั้น ล็อกอินครั้งถัดไปกลับสู่พฤติกรรมปกติ

The reason it is a condition rather than a nicety, in the COO's own words:
every other command this lane has lands inside one chat line, and this one
lands ON DISK.  Without consumption the blast radius of a staged scene is
"until somebody remembers to delete a file on the bridge"; with it, the
radius is one login.  It also removes `GT-127`'s manual cleanup step, which
was resting on a tester's discipline at the end of a long attended job.

WHY A SEPARATE MODULE, and not a side effect inside
`login_scene_override.get_login_scene_override`:

1. `get_login_scene_override` is a READER and several call sites (tests,
   the writer's own read-back, `login_scene_stage`) rely on it staying one.
   A reader that deletes what it read is the kind of function that is
   correct exactly once and then surprises everybody.
2. `login_scene_stage` already imports from `login_scene_override`, so the
   consuming half cannot live in the reader without a circular import.

FAIL-CLOSED, and this is the part worth arguing about: if the entry cannot
be taken off disk, this returns **None** -- the login gets the DEFAULT
scene, not the staged one.  Granting a scene whose override survives is the
exact state the COO's condition exists to forbid, so a failure to consume
has to cost the warp rather than cost the guarantee.  The entry is left on
disk untouched, where an operator can see it, rather than being half-erased.

[สมมติของสาย GM - รอ COO ยืนยัน] The STANDALONE map
(`gm_login_scene_standalone.json`) is NOT consumed.  The decision answers a
ticket about `/warp`, and only the GM-gated map is reachable from a chat
command; the standalone map is typed by an operator into a file, for a
scene they want to keep entering (`GT-110`).  Silently erasing an
operator's own config line on first use is a different and worse surprise
than the one the condition was written to prevent.  Asked in
`notes_to_chief/20260829_0515_LANE-GM-ASK-COO-standalone-map-single-use-too.md`;
if the answer is "both", this file changes in one place.

NONCLAIM, permanent, per the same decision: the caller's identity is a
process-level `session.token`, not a per-connection identity.  This module
narrows the window a staged scene stays live; it does not make the staging
call itself attributable.  **Closes when there is a per-connection
identity** -- not before, and no test here should be read as evidence of it.
"""
from __future__ import annotations

import os

from .accounts import is_gm_account
from .login_scene_override import (
    get_login_scene_override,
    load_login_scene_overrides,
)

# The outcome words, so a caller (and an audit row) can tell the three
# cases apart instead of reading None three different ways.
CONSUMED = "consumed"
NOTHING_STAGED = "nothing_staged"
STANDALONE_NOT_CONSUMED = "standalone_not_consumed"
CONSUME_FAILED = "consume_failed"


class ConsumeResult:
    """What the login should do, and what happened to the entry on disk."""

    __slots__ = ("scene_id", "outcome")

    def __init__(self, scene_id: int | None, outcome: str) -> None:
        self.scene_id = scene_id
        self.outcome = outcome

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"ConsumeResult(scene_id={self.scene_id!r}, outcome={self.outcome!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConsumeResult):
            return NotImplemented
        return (self.scene_id, self.outcome) == (other.scene_id, other.outcome)


def consume_login_scene_override(
    account_name: str,
    gm_accounts_config_path: str | os.PathLike | None = None,
    login_scene_config_path: str | os.PathLike | None = None,
    standalone_config_path: str | os.PathLike | None = None,
) -> ConsumeResult:
    """Resolve this account's login scene AND spend the entry that gave it.

    This is what a login path should call.  `get_login_scene_override` stays
    the right call for anything that wants to LOOK without spending.

    The four outcomes, all of them reachable:

    * `CONSUMED` -- a GM-gated entry supplied the scene and is now off disk.
      A second call in the same login returns `NOTHING_STAGED`, which is the
      whole point of the condition.
    * `STANDALONE_NOT_CONSUMED` -- the standalone map supplied the scene; it
      is left alone (see the module docstring, and the open question there).
    * `NOTHING_STAGED` -- no override for this account, the ordinary case.
    * `CONSUME_FAILED` -- an entry was found but could not be removed, so
      **no scene is returned**: the login goes to the default rather than to
      a scene whose override would outlive it.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")

    scene_id = get_login_scene_override(
        account_name,
        gm_accounts_config_path=gm_accounts_config_path,
        login_scene_config_path=login_scene_config_path,
        standalone_config_path=standalone_config_path,
    )
    if scene_id is None:
        return ConsumeResult(None, NOTHING_STAGED)

    # Which map answered?  Ask the GM-gated map directly rather than
    # inferring it from the scene_id: two maps can legitimately name the
    # same scene, and guessing would consume the wrong entry.
    #
    # BOTH halves of the GM path are re-asked here, not just the entry.
    # Presence in `gm_login_scene.json` alone does NOT mean that file is
    # what answered: `get_login_scene_override` consults the GM map only
    # for a listed GM account, so for a NON-GM named in both files the
    # scene came from the standalone map while the GM-gated file still
    # holds a stale hand-written line.  Consuming on the entry alone would
    # then delete that line -- this module editing a config on behalf of an
    # account the allowlist does not list, which is the one thing this lane
    # never does.  (Found by self-review this round; the remover
    # deliberately does not re-check the allowlist itself, so the check has
    # to be here.)
    if not is_gm_account(account_name, gm_accounts_config_path):
        return ConsumeResult(scene_id, STANDALONE_NOT_CONSUMED)
    try:
        gm_gated = load_login_scene_overrides(login_scene_config_path)
    except (OSError, ValueError):
        # A config this process cannot read is a config it must not act on.
        return ConsumeResult(None, CONSUME_FAILED)
    if gm_gated.get(account_name) is None:
        return ConsumeResult(scene_id, STANDALONE_NOT_CONSUMED)

    # Imported here, not at module scope: `login_scene_stage` imports from
    # `login_scene_override`, which this module also imports, and a
    # top-level import would close that loop.
    from . import login_scene_stage

    # `restore_login_scene(account, None)` is the existing remover -- the
    # same one `chat_command_action` uses to take a staged entry back off
    # disk when its audit row cannot be written.  Reusing it rather than
    # writing a second deleter keeps one implementation of "edit this file
    # safely", which is the whole reason that one is as careful as it is.
    # It deliberately does not re-check the allowlist: a removal must work
    # even for an account someone has since delisted, or the delisting
    # would strand exactly the entry that most needs clearing.
    try:
        removed = login_scene_stage.restore_login_scene(
            account_name,
            None,
            gm_accounts_config_path=gm_accounts_config_path,
            config_path=login_scene_config_path,
        )
    except Exception:
        # The writer is fail-closed on its own account and restores the
        # operator's bytes; anything that still escapes it costs the warp,
        # never the guarantee.
        return ConsumeResult(None, CONSUME_FAILED)

    if not removed:
        return ConsumeResult(None, CONSUME_FAILED)

    # Do not take the writer's word for it: read the file back through the
    # reader the login path itself uses.  A removal that reported success
    # and left the entry there is the one failure this whole module exists
    # to prevent, and it is one call to rule out.
    try:
        still_there = load_login_scene_overrides(login_scene_config_path)
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED)
    if still_there.get(account_name) is not None:
        return ConsumeResult(None, CONSUME_FAILED)

    return ConsumeResult(scene_id, CONSUMED)
