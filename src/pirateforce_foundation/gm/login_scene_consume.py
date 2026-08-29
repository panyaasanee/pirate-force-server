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
    LoginSceneRefusedError,
    get_login_scene_override,
    load_login_scene_overrides,
    load_standalone_login_scene_overrides,
)

# The outcome words, so a caller (and an audit row) can tell the three
# cases apart instead of reading None three different ways.
CONSUMED = "consumed"
NOTHING_STAGED = "nothing_staged"
STANDALONE_NOT_CONSUMED = "standalone_not_consumed"
# WIDER THAN ITS NAME, and said here because pf-adversary read the name and
# checked: it covers "an entry was found but could not be removed" AND "a
# config this process could not read, so which map answered is unknown".
# Both mean the same thing to a login -- no scene is returned -- and neither
# may be reported as a scene the caller can use.
#
# `cause` below is what tells those apart WITHOUT widening what a login may
# do about them.  The word stays one word on purpose.
CONSUME_FAILED = "consume_failed"

# ---------------------------------------------------------------------------
# WHY `CONSUME_FAILED` HAPPENED -- a CLOSED vocabulary this lane wrote.
#
# Asked for by chief in `CHIEF-REPLY` 2026-08-29T15:16+07:00 item 5, whose
# own console line had to print `cause=not_carried_by_the_outcome` because
# this class carried no cause: six different faults arrived at the operator
# as one word, and the two remedies they need (edit a config / restart the
# server) are not the same remedy.
#
# THE RULE THAT SHAPES THIS LIST, and it is not a style preference -- chief
# PRINTS this token on the owner's console.  Round `9wy444` D1 established
# that no byte a client sent may reach that console, and a cause built from
# `str(exc)` would carry a config file's bytes (a JSON parse error quotes
# the offending line) straight there, wearing this lane's own token as a
# prefix.  So:
#
#   * every cause is a literal written HERE, before any client connected;
#   * an exception's message NEVER becomes a cause, not even in part;
#   * the set is closed and `ConsumeResult` REFUSES anything outside it, so
#     a future branch cannot invent a cause by passing a string.
#
# That last point is the difference between this and a filter: there is no
# path that sanitises a cause, because there is no path that builds one.
#
# THE AXIS IS THE REMEDY, NOT THE RETURN SITE.  The first version of this
# list split on "which of the three reads saw the bad bytes" and pf-adversary
# measured what that bought an operator: nothing.  Six of its seven tokens
# fired only if a config file changed underneath a login MID-FLIGHT, and the
# seventh -- the only one an ordinary bad config could produce -- answered
# BOTH of the two remedies chief said were not the same remedy:
#
#     malformed JSON            -> cause=override_lookup_unreadable
#     row the snapshot refuses  -> cause=override_lookup_unreadable
#
# and the second of those is the case chief measured as the NEW NORMAL after
# `CORE-REQUEST-GM-036`, on a file that is perfectly readable.  Telling an
# operator a readable file is "unreadable" is worse than saying nothing: they
# grep it, find it well-formed, and stop believing the line.
#
# So the split that ships is the one an operator can ACT on:
#
#   `config_unreadable`      the bytes are bad          -> edit the file
#   `registry_refused_entry` the bytes are fine, this   -> restart the
#                            process will not admit        server, or fix
#                            the row                       lane A's registry
#   `gm_accounts_unreadable` } which FILE, when the loader can say -- these
#   `gm_map_unreadable`      } are reachable only through a mid-flight race
#   `standalone_map_unreadable`
#   `claim_raised`           removal raised, entry's fate UNKNOWN
#   `entry_survived_claim`   removal failed, entry KNOWN to be on disk
#
# WHAT WAS DELIBERATELY DROPPED, so the next reader does not "restore" it:
# `gm_map_unreadable_after_claim`.  It split one file's read on WHICH MOMENT
# it failed at, and pf-adversary pointed out that the standalone read has the
# same two moments and got one token -- so the axis was not even applied
# consistently.  Rather than add a token to match, the axis went: an operator
# does not do anything different about a read that failed before the claim
# than one that failed after it.  `claim_raised` / `entry_survived_claim`
# stay because THEY are a remedy split ("go look at the disk" vs "delete the
# line by hand"), not a chronology.
CAUSE_NONE = "none"
CAUSE_CONFIG_UNREADABLE = "config_unreadable"
CAUSE_REGISTRY_REFUSED_ENTRY = "registry_refused_entry"
CAUSE_GM_ACCOUNTS_UNREADABLE = "gm_accounts_unreadable"
CAUSE_GM_MAP_UNREADABLE = "gm_map_unreadable"
CAUSE_STANDALONE_MAP_UNREADABLE = "standalone_map_unreadable"
CAUSE_CLAIM_RAISED = "claim_raised"
CAUSE_ENTRY_SURVIVED_CLAIM = "entry_survived_claim"

# Every `CONSUME_FAILED` return site in this module carries one of these, and
# `test_gm_login_scene_consume_cause.py` COUNTS THE RETURN SITES IN THIS
# SOURCE and refuses one that carries a cause outside the set -- pinning the
# count of constants alone did not refuse an eighth branch that borrows an
# existing token, which is what pf-adversary added to prove it.
CONSUME_FAILED_CAUSES = frozenset(
    {
        CAUSE_CONFIG_UNREADABLE,
        CAUSE_REGISTRY_REFUSED_ENTRY,
        CAUSE_GM_ACCOUNTS_UNREADABLE,
        CAUSE_GM_MAP_UNREADABLE,
        CAUSE_STANDALONE_MAP_UNREADABLE,
        CAUSE_CLAIM_RAISED,
        CAUSE_ENTRY_SURVIVED_CLAIM,
    }
)


class ConsumeResult:
    """What the login should do, and what happened to the entry on disk."""

    __slots__ = ("scene_id", "outcome", "cause")

    def __init__(
        self, scene_id: int | None, outcome: str, cause: str = CAUSE_NONE
    ) -> None:
        # REFUSED BY NAME, not filtered.  `cause` is not free text and this
        # is the only place that could let it become free text, so the check
        # lives here rather than at seven call sites that would each have to
        # remember it.
        #
        # SAFE TO RAISE, measured rather than assumed: the consume call in
        # `runtime.py` sits inside `except (ValueError, OSError, TypeError)`,
        # which logs `gm_login_scene_override_lookup_failed_ValueError`, so a
        # cause this lane got wrong costs the OVERRIDE and never the login.
        # Fail-closed in the direction that matters: an unprintable cause
        # becomes no scene, not an unchecked string on the owner's console.
        # (No line number here on purpose -- an earlier revision pinned one
        # in chief's 6800-line file, where it goes stale every round and no
        # test can notice it moved.)
        #
        # `type(...) is not str`, never isinstance, for the same reason
        # `account_name` gets it below: a `str` SUBCLASS compares equal to a
        # member of the set, passes `in`, and then renders as whatever its
        # `__str__` says when chief interpolates it -- which is a forged
        # `key=value` field, or a forged second console line, arriving with
        # this lane's token in front of it.
        if type(cause) is not str:
            raise TypeError("cause must be a str, not a str subclass")
        if cause not in CONSUME_FAILED_CAUSES and cause != CAUSE_NONE:
            raise ValueError("cause must be one of CONSUME_FAILED_CAUSES")
        # THE TWO-WAY BINDING, and both directions earn their keep.  Without
        # the first, a success could carry a cause and chief's console line
        # would name a fault on a login that worked.  Without the second, a
        # failure could carry `CAUSE_NONE` and chief would be back to
        # printing "not carried by the outcome" for a branch that simply
        # forgot -- the exact regression this field exists to end.
        if outcome == CONSUME_FAILED:
            if cause == CAUSE_NONE:
                raise ValueError("CONSUME_FAILED must carry a cause")
        elif cause != CAUSE_NONE:
            raise ValueError("only CONSUME_FAILED may carry a cause")
        object.__setattr__(self, "scene_id", scene_id)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "cause", cause)

    # FROZEN AFTER CONSTRUCTION, and this is the half the first version was
    # missing.  pf-adversary measured it: validating only in `__init__` left
    # `result.cause = f"{CAUSE_GM_MAP_UNREADABLE}: {exc}"` a legal one-line
    # change that put a config file's PATH and an ACCOUNT NAME onto the
    # owner's console -- and it survived all 23 tests, because every one of
    # them drove the constructor.  The module comment above claims "there is
    # no path that builds a cause"; assignment was that path.  Now the only
    # way a `ConsumeResult` gets a cause is through the check above.
    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            "ConsumeResult is immutable; construct a new one instead"
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ConsumeResult is immutable")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"ConsumeResult(scene_id={self.scene_id!r}, "
            f"outcome={self.outcome!r}, cause={self.cause!r})"
        )

    def __eq__(self, other: object) -> bool:
        # `cause` IS part of the identity.  Measured before choosing: no
        # test in this repo constructs a `ConsumeResult`, so nothing had to
        # be relaxed to include it -- and leaving it out would have made
        # `== ConsumeResult(None, CONSUME_FAILED, X)` pass for cause `Y`,
        # which is a test that reads like it pins the cause and does not.
        if not isinstance(other, ConsumeResult):
            return NotImplemented
        return (self.scene_id, self.outcome, self.cause) == (
            other.scene_id,
            other.outcome,
            other.cause,
        )


def _ask_the_standalone_map(
    account_name: str,
    standalone_config_path: str | os.PathLike | None,
    scene_registry=None,
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

    ONLY THE AMBIGUOUS CALLERS USE THIS.  A non-GM's scene can only have come
    from the standalone map, so that path keeps the id it already has rather
    than paying for a second read it cannot lose.  This function is for the
    two branches where the GM map DID hold an entry a moment ago and no
    longer does -- where "which map answered" is genuinely unknown.
    """
    try:
        standalone = load_standalone_login_scene_overrides(
            standalone_config_path, scene_registry=scene_registry
        )
    except LoginSceneRefusedError:
        # ORDER MATTERS: this is a `ValueError` subclass, so it has to be
        # caught first or the wider arm below swallows it and the console
        # says "unreadable" about a file that reads perfectly.
        return ConsumeResult(
            None, CONSUME_FAILED, CAUSE_REGISTRY_REFUSED_ENTRY
        )
    except (OSError, ValueError):
        # A config this process cannot read is one it must not act on, and
        # no scene is returned.  See `CONSUME_FAILED`'s own note on what the
        # word covers -- it is wider than "a removal failed".
        return ConsumeResult(
            None, CONSUME_FAILED, CAUSE_STANDALONE_MAP_UNREADABLE
        )
    scene_id = standalone.get(account_name)
    if scene_id is None:
        return ConsumeResult(None, NOTHING_STAGED)
    return ConsumeResult(scene_id, STANDALONE_NOT_CONSUMED)


def consume_login_scene_override(
    account_name: str,
    gm_accounts_config_path: str | os.PathLike | None = None,
    login_scene_config_path: str | os.PathLike | None = None,
    standalone_config_path: str | os.PathLike | None = None,
    *,
    scene_registry=None,
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

    `scene_registry` -- CHIEF-REPLY 2026-08-29T12:21+07:00 item 4, the
    parameter chief asked this lane to land first so their call site can
    pass `runtime.py`'s boot snapshot into it.  It reaches every load below
    and decides ONE thing: which reading of lane A's registry the admission
    check judges a config entry against.

    WHAT IT ACTUALLY FIXES, and it is NOT the lockout chief's own gate
    closes.  That gate handles the disk being WIDER than the snapshot (an
    entry the file approves and the process refuses).  This parameter is
    for the other direction, which no gate at the call site can reach: when
    the disk is NARROWER -- lane A's registry file edited to bar or drop a
    scene after boot -- the fresh read refuses that entry, the whole-file
    load raises, and `CONSUME_FAILED` turns off EVERY account's override,
    including accounts naming scenes the running process would still place
    them in perfectly well.  Nobody is locked out and nothing says why; the
    lane just stops working until a restart.  Judged against the snapshot,
    the file is held to what the process can actually do.

    Default `None` = read the file fresh, which is what every test in this
    lane was written against.  It is NO LONGER what the real login does:
    chief wired the boot snapshot in at this call site and two others
    (`CHIEF-REPLY` 2026-08-29T15:16+07:00, main as `pirate-force-server`
    #264), so the sentence this docstring used to carry -- "what every
    caller does today" -- is false and the difference matters, because the
    snapshot reading is the one that decides `CAUSE_OVERRIDE_LOOKUP
    _UNREADABLE` below.
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
            scene_registry=scene_registry,
        )
    except LoginSceneRefusedError:
        # THE CASE THAT ACTUALLY HAPPENS, and the one the first version of
        # this field got wrong.  The file parsed; lane A's registry -- as
        # THIS PROCESS holds it, which since `CORE-REQUEST-GM-036` is the
        # boot snapshot -- will not admit the row.  Editing the config is
        # not the remedy and saying "unreadable" sends the operator to grep
        # a well-formed file.
        return ConsumeResult(
            None, CONSUME_FAILED, CAUSE_REGISTRY_REFUSED_ENTRY
        )
    except (OSError, ValueError):
        # The bytes really are bad.  The lookup reads all three configs and
        # the loader does not say which, so this names the fault and not the
        # file -- an honest "edit one of your config files" beats a guess.
        return ConsumeResult(None, CONSUME_FAILED, CAUSE_CONFIG_UNREADABLE)
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
        return ConsumeResult(
            None, CONSUME_FAILED, CAUSE_GM_ACCOUNTS_UNREADABLE
        )
    if not answered_by_gm_map:
        # NO RE-READ HERE, and that is deliberate rather than an omission.
        # `get_login_scene_override` consults the GM map ONLY for a listed GM
        # account, so for a non-GM the scene it returned can only have come
        # from the standalone map -- there is nothing to disambiguate and the
        # id in hand is already the right one.
        #
        # An earlier version of this round did re-read here, and pf-adversary
        # measured the cost: a non-GM whose standalone file was mid-save
        # inside the new window got `scene=None, consume_failed` where the
        # old code returned their scene, and one whose file was removed got
        # `nothing_staged`.  That is a regression bought for nothing -- the
        # standalone map is not single-use, so there is no race to lose.
        return ConsumeResult(scene_id, STANDALONE_NOT_CONSUMED)

    # WHICH MAP supplied the scene is decided BEFORE the claim, never
    # after: once the entry is gone there is no way to tell "the standalone
    # map answered" from "the GM map answered and another login took it".
    try:
        gm_map = load_login_scene_overrides(
            login_scene_config_path, scene_registry=scene_registry
        )
    except LoginSceneRefusedError:
        return ConsumeResult(
            None, CONSUME_FAILED, CAUSE_REGISTRY_REFUSED_ENTRY
        )
    except (OSError, ValueError):
        return ConsumeResult(None, CONSUME_FAILED, CAUSE_GM_MAP_UNREADABLE)
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
        return _ask_the_standalone_map(
            account_name, standalone_config_path, scene_registry
        )

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
            account_name,
            config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
    except Exception:
        # BEFORE/AFTER MATTERS TO THE OPERATOR: this one says the remover
        # itself raised, so the entry's fate on disk is unknown.  Distinct
        # from `CAUSE_ENTRY_SURVIVED_CLAIM`, where it is known to be there.
        return ConsumeResult(None, CONSUME_FAILED, CAUSE_CLAIM_RAISED)

    if claimed is None:
        # We know the GM map held the entry a moment ago and we did not get
        # it.  Either another login took it -- correct, and this login gets
        # the ordinary scene -- or the removal failed.  One read tells them
        # apart, and only the second is a fault.
        try:
            after = load_login_scene_overrides(
                login_scene_config_path, scene_registry=scene_registry
            )
        except LoginSceneRefusedError:
            return ConsumeResult(
                None, CONSUME_FAILED, CAUSE_REGISTRY_REFUSED_ENTRY
            )
        except (OSError, ValueError):
            # SAME token as the pre-claim read of the same file.  An earlier
            # revision split these on which MOMENT failed; pf-adversary
            # observed the standalone read has the identical two moments and
            # got one token, so the axis was not applied consistently -- and
            # an operator does nothing different about the two.  The axis
            # went rather than the inconsistency being papered over.
            return ConsumeResult(
                None, CONSUME_FAILED, CAUSE_GM_MAP_UNREADABLE
            )
        if after.get(account_name) is not None:
            return ConsumeResult(
                None, CONSUME_FAILED, CAUSE_ENTRY_SURVIVED_CLAIM
            )
        # THE OTHER LOSER BRANCH, and the D3 fix reached only one of them.
        # MEASURED by pf-adversary: this branch returned `NOTHING_STAGED`
        # without ever asking the standalone map, so an operator with a
        # standing `gm_login_scene_standalone.json` entry ("always start me
        # here") lost it on every login that lost the claim -- 420 of 420
        # losers over 60 trials x 8 threads.  It is the MORE likely loser
        # path under contention, not the rarer one, and it falsified this
        # round's own deliverable sentence about `GT-110` being able to
        # re-enter the same scene on every retry.
        return _ask_the_standalone_map(
            account_name, standalone_config_path, scene_registry
        )

    return ConsumeResult(claimed, CONSUMED)
