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
disk where an operator can see it.  One exception, named rather than
implied: if the writer's own byte-restore fails (`login_scene_stage`
swallows that `OSError`), the entry can be gone while the outcome still
says `CONSUME_FAILED`.  The guarantee that holds in every case is the one
that matters -- no scene is returned -- not "the file is always unchanged".

CONFIRMED, no longer an assumption: the STANDALONE map
(`gm_login_scene_standalone.json`) is NOT consumed.  This lane asked in
`notes_to_chief/20260829_0515_LANE-GM-ASK-COO-standalone-map-single-use-too.md`
and `COO-DECISION 20260829_0542` upheld it -- item 2 of the 0441 decision
binds `config/gm_login_scene.json` (the file a chat command can reach) to
the letter, and stops there.  The reasoning, which is the COO's and not
this module's: the danger 0441 names is a command whose effect lands ON
DISK instead of ending with the chat line, and the standalone map does not
come from a command at all.  Silently erasing an operator's own config line
on first use is a different and worse surprise than the one the condition
was written to prevent, and `GT-110` has to be able to re-enter the same
scene on every retry.

NONCLAIM, and it is the condition that decision rests on (item 3): the
standalone map is NOT safer in general.  It grants a login scene with no
`gm_accounts.json` membership at all, which is a STRONGER capability than
anything the GM-gated map grants.  Its only protection is that nothing a
client sends and no chat line can write it -- an operator at the machine
types it or it does not exist.  **The day any path lets a client or a chat
command write that file, this decision is void without asking again and the
standalone map becomes single-use.**  `tests/test_gm_standalone_map_is_not
_chat_writable.py` is the tripwire for exactly that (COO-DECISION 0542 item
4): it drives every command name this lane parses, AND the client's inbound
`0x51E9` route, past the file, and asks whether any write-capable call named
a file with that BASENAME -- not whether one particular resolved path was
touched, which is what the first version asked and what a write to the real
cwd-relative default walked straight past.  What it proves is "no route that
RAN", not "no route that exists": a write deferred past the assertions, or
one made through a call it does not wrap, would need the file, the directory
or the reader to show it.

If the answer ever flips to "both", it is NOT a one-line change here, and an
earlier draft of this docstring said it was: `login_scene_stage` refuses
that file by design and `restore_login_scene` has no standalone path, so it
needs a new remover, a relaxation of that module's source-scan guard, and a
change to this file's own `test_this_module_cannot_reach_the_standalone
_writer`.  Three places, two modules, two test files.

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
    load_standalone_login_scene_overrides,
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


def _ask_the_standalone_map(
    account_name: str,
    standalone_config_path: str | os.PathLike | None,
) -> ConsumeResult:
    """Did the STANDALONE map really answer, and with which scene?

    The scene id is taken from this read, not carried down from
    `get_login_scene_override`'s earlier one: the two reads can straddle
    another login's claim, and the answer that matters is the one the
    standalone map holds NOW.  If it holds nothing for this account, the
    scene came from the GM-gated map and somebody else has since spent it --
    so this login gets `NOTHING_STAGED` and the ordinary default scene,
    which is what the loser of a single-use race is supposed to get.

    Reading it is also the only way this module can say `STANDALONE_NOT
    _CONSUMED` truthfully; the previous version could say it about a file
    that did not exist.
    """
    try:
        standalone = load_standalone_login_scene_overrides(
            standalone_config_path
        )
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED)
    scene_id = standalone.get(account_name)
    if scene_id is None:
        return ConsumeResult(None, NOTHING_STAGED)
    return ConsumeResult(scene_id, STANDALONE_NOT_CONSUMED)


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
      is left alone, upheld by `COO-DECISION 20260829_0542` (see the module
      docstring for the condition that would reverse it).
    * `NOTHING_STAGED` -- no override for this account, the ordinary case.
    * `CONSUME_FAILED` -- an entry was found but could not be removed, so
      **no scene is returned**: the login goes to the default rather than to
      a scene whose override would outlive it.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")
    if not account_name:
        # Both collaborators refuse an empty name, so accepting it here only
        # buys a permanently unremovable entry reported as a disk fault.
        raise ValueError("account_name must be a non-empty str")

    # Guarded, unlike the first version: a "four outcomes, fail-closed"
    # function that raises on a malformed config is neither.  A config this
    # process cannot read is a config it must not act on -- and a login is
    # never taken down by this file.
    try:
        scene_id = get_login_scene_override(
            account_name,
            gm_accounts_config_path=gm_accounts_config_path,
            login_scene_config_path=login_scene_config_path,
            standalone_config_path=standalone_config_path,
        )
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED)
    if scene_id is None:
        return ConsumeResult(None, NOTHING_STAGED)

    # Which map answered?  BOTH halves of the GM path are asked, not just
    # the entry.  Presence in `gm_login_scene.json` alone does NOT mean that
    # file is what answered: `get_login_scene_override` consults the GM map
    # only for a LISTED GM account, so for a non-GM named in both files the
    # scene came from the standalone map while the GM-gated file still holds
    # a stale hand-written line.  MEASURED by pf-adversary against the first
    # version of this module: it deleted that line, returned the OTHER map's
    # scene, and labelled it `consumed` -- so the override survived every
    # later login while the audit row said it had been spent.  Three
    # failures from one missing half-check.
    try:
        answered_by_gm_map = is_gm_account(
            account_name, gm_accounts_config_path
        )
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED)
    if not answered_by_gm_map:
        return _ask_the_standalone_map(account_name, standalone_config_path)

    # WHICH MAP supplied the scene is decided BEFORE the claim, never
    # after: once the entry is gone there is no way to tell "the standalone
    # map answered" from "the GM map answered and another login took it".
    try:
        gm_map = load_login_scene_overrides(login_scene_config_path)
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED)
    if gm_map.get(account_name) is None:
        # NOT "therefore the standalone map answered".  MEASURED by
        # pf-adversary against the version that concluded exactly that:
        # `scene_id` was read at the top of this function, and if ANOTHER
        # login's atomic claim lands in the window between that read and
        # this one, the GM map no longer holds the entry -- so this branch
        # handed the staged scene to the loser of the race as well, labelled
        # `standalone_not_consumed`, with no standalone file on disk at all.
        # Two logins got the single-use scene (COO-DECISION 0441 item 2 not
        # held) and the audit row named a map that had not answered.
        # Reproduced 4/4 under parallel load, 0/8 alone -- a contention-gated
        # flake, the kind that gets re-run rather than diagnosed.
        #
        # The comment above about deciding WHICH MAP before the claim is true
        # of this call's claim and false of everybody else's.  So ask the
        # standalone map itself rather than inferring it by elimination.
        return _ask_the_standalone_map(account_name, standalone_config_path)

    # Imported here, not at module scope: `login_scene_stage` imports from
    # `login_scene_override`, which this module also imports, and a
    # top-level import would close that loop.
    from . import login_scene_stage

    # ONE atomic take, not read-then-remove.  MEASURED by pf-adversary
    # against the first version of this module: reading the entry and then
    # calling `restore_login_scene(acct, None)` let two concurrent logins of
    # the same account BOTH receive the staged scene and both write
    # `consumed` -- 400 of 400 trials -- because that remover's check is
    # "the entry is not what I was asked to write", which "absent" satisfies
    # for a delete no matter who actually removed it.  There was no loser,
    # so there was no single use.  `claim_login_scene` reads and deletes
    # under one hold of the write lock and returns what THIS call took, so
    # exactly one caller can be handed the scene.
    #
    # Not a contrived race here: this lane shares one `session.token`
    # account across connections (`login_scene_stage`'s IDENTITY, STATED
    # HONESTLY), so two logins of the same account at once is the ordinary
    # case rather than the exotic one.
    try:
        claimed = login_scene_stage.claim_login_scene(
            account_name, config_path=login_scene_config_path
        )
    except Exception:
        return ConsumeResult(None, CONSUME_FAILED)

    if claimed is None:
        # We know the GM map held the entry a moment ago and we did not get
        # it.  Either another login took it -- correct, and this login gets
        # the ordinary scene -- or the removal failed.  One read tells them
        # apart, and only the second is a fault.
        try:
            after = load_login_scene_overrides(login_scene_config_path)
        except (OSError, ValueError):
            return ConsumeResult(None, CONSUME_FAILED)
        if after.get(account_name) is not None:
            return ConsumeResult(None, CONSUME_FAILED)
        return ConsumeResult(None, NOTHING_STAGED)

    return ConsumeResult(claimed, CONSUMED)
