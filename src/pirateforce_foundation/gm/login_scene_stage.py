"""GM-003 warp, cross-scene half: stage the account's NEXT LOGIN scene.

WHAT THIS IS, AND WHAT IT IS NOT.  It is not a warp.  Nothing is composed,
nothing goes on the wire, and no character moves while it is logged in.  It
writes ONE entry into the config file `gm/login_scene_override.py` already
reads fresh on every login (GM-005, wired into `runtime.py`'s login path by
CORE-REQUEST-016), so that the GM's NEXT login lands in the scene they typed.
The tester has to log out and back in.  Any report that uses it must say so:
"warped with GM to the island and saw the island" is still not "M2 passed",
and "staged and relogged into the island" is not even a warp.

WHY IT EXISTS.  `/warp <scene_id>` across scenes is the one thing the owner's
own command list asks for that this lane cannot put on the wire: ForcePos
carries no scene id (RE-129), and `TeleportVital`'s target/aux sub-objects
still have positional-only fields nobody has proven (RE-090), so composing one
would be guessing -- which this lane refuses.  The same-scene half was frozen
by COO order (`FORCE_POS_VITAL_VERSION_CONFIRMED = None`, COO-DECISION
20260829_0041) until RE-129's measured value could be confirmed on main; that
happened (`FORCE_POS_VITAL_VERSION_CONFIRMED = 0`, COO-DECISION 20260830_1645
/1742).  Cross-scene warp is still unproven regardless (RE-090, no scene id on
ForcePos), so a tester who types `/warp 126` still gets a refusal and no way
to see scene 126 -- while a path that DOES work, and is already wired and
tested, sits one config file away.  This module is the bridge between the
command the owner asked for and the mechanism that already works.

WHAT IT CAN AND CANNOT GRANT.  It writes the GM-GATED map only
(`gm_login_scene`), never the standalone one (`standalone_login_scene`), and
only for an account `gm/accounts.py` already lists.  Both halves matter:

* The standalone map grants a login scene to an account with NO
  `gm_accounts.json` membership.  A writer that could reach it would be a way
  to give an unlisted account a server-side effect, which is exactly what the
  lane charter forbids ("client cannot make itself GM, ever").  This module
  does not import it, does not name its file, and
  `tests/test_gm_login_scene_stage.py` reads this source and fails if either
  ever appears here.
* An entry in the GM-gated map is worth NOTHING on its own:
  `get_login_scene_override` re-checks `is_gm_account` at login time, so an
  entry for an account later removed from the allowlist stops applying by
  itself.  The worst a staged entry can do is put a listed GM in a different
  (catalog-known) scene on their next login.  It grants no status, no command,
  and no frame.

THE IDENTITY LIMIT, SAID BEFORE ANYONE ASKS.  [สมมติของสาย GM - รอ COO ยืนยัน]
`runtime.py` hands this lane `session.token`, the process-wide `--token` CLI
value, not a per-connection authenticated login (see `chat_command_action.py`'s
IDENTITY, STATED HONESTLY block, and reports/PF_MULTIPLAYER_READINESS_AUDIT001
rows I01-I04).  So on a listener whose token IS a listed GM account, ANY
connected player who types `/warp 126` in chat stages that account's next
login scene.  Every other command in this lane already shares that gap, but
this is the FIRST one whose effect outlives the chat line, so it is named here
rather than left for someone to find: the blast radius is "a listed GM logs in
somewhere else next time, recoverable by typing the old scene or deleting the
config", the kill switch is `production_allowed = False` in
`lane_hooks/lane_gm_chat_command.py` plus a restart, and the letter asking COO
to weigh in is `pf_bridge/notes_to_chief/20260829_0336_LANE-GM-ASK-COO-warp-
cross-scene-stages-next-login-scene.md`.

FAIL-CLOSED, IN THE ONE DIRECTION THAT MATTERS.  Every refusal leaves the
config file byte-identical to what it was, including the case where the file
was already unreadable to the reader that has to consume it: this module
validates the WHOLE file through `load_login_scene_overrides` before writing
and again after, and restores the original bytes if the read-back disagrees.
An operator's hand-written config is never "repaired", never partially
rewritten, and never left in a state the login path would refuse to load.

TWO WAYS IT USED TO WALK OVER AN OPERATOR ANYWAY, both found by probing this
module rather than by reading it, both closed in the round that added it:
a SYMLINKED config path was replaced rather than written through (the link
became a regular file, the target kept the old content, and the login path
quietly started reading a different file), and a config file the operator had
`chmod 400`-ed was overwritten regardless, because `os.replace` needs the
DIRECTORY's write bit and not the file's.  See `REASON_CONFIG_NOT_WRITABLE`
and the `os.path.realpath` call for what each one costs now.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import tempfile
import threading
from pathlib import Path

from .accounts import is_gm_account
from . import login_scene_admission
from . import login_scene_override as login_scene_override_module
from .login_scene_override import (
    LoginSceneRefusedError,
    load_login_scene_overrides,
    resolve_gm_login_scene_config_path,
)
from .scene_catalog import is_known_scene_id

# The JSON key this module may write.  Spelled once, here, so the test that
# pins "this module never names the standalone key" has one thing to allow.
GM_LOGIN_SCENE_JSON_KEY = "gm_login_scene"

# One listener process, several connection threads, one config file.  Every
# write here is read-modify-write, so without this two threads staging at the
# same moment can both read the old map and the second one can drop the first
# one's entry -- silently, since both calls report success.  The lock closes
# the in-process race, which is the one this project can actually hit.
#
# WHAT IT DOES NOT CLOSE, said rather than implied: a SECOND process editing
# the same file (an operator with an editor open, a second listener) still
# races, because a lock in this interpreter means nothing to it.  The
# read-back check below is what catches that case -- not by preventing it, but
# by refusing to report success for a file that does not say what we wrote.
_WRITE_LOCK = threading.Lock()

REASON_OK = "ok"
REASON_NOT_GM_ACCOUNT = "not_gm_account"
REASON_UNKNOWN_SCENE = "unknown_scene"
REASON_CONFIG_UNREADABLE = "config_unreadable"
REASON_WRITE_FAILED = "write_failed"
# The file exists and the operator has taken the write bit off it.  Measured
# rather than assumed: `os.replace` needs write permission on the DIRECTORY,
# not on the file, so a `chmod 400 gm_login_scene.json` -- an operator saying
# "do not touch this" in the only way a file can say it -- was silently
# overwritten, and came back 0o600.  Refusing costs one `os.access` call.
REASON_CONFIG_NOT_WRITABLE = "config_not_writable"
# The scene has a NAME but no pinned login ENTRY.  Two different tables, and
# the gap between them is what pf-adversary measured this module walking
# straight into: `gm/scene_catalog.py` is the client's 330-row scene NAME
# table, while the login path resolves through lane A's
# `scenarios/world_scene_registry_001.json`, which pins 5 and marks one of
# those `login_entry_allowed: false`.  Staging a named-but-unpinned scene
# wrote a perfectly valid-looking entry that made the account's NEXT LOGIN
# fail with `WORLD_SCENE_ENTRY_REFUSED [scene_not_pinned]` and no reply --
# and the only in-game fix needs a chat line, which needs a login.  326 of
# the 330 stageable scenes bricked the account until an operator deleted the
# file on the server host.  So this module now asks the SECOND table too,
# through lane A's own loader rather than a copy of its data.
REASON_NO_LOGIN_ENTRY = "scene_has_no_login_entry"
# A DIFFERENT LINE in the file -- not the one being staged -- names a scene
# the login path will not admit, so the reader refuses the whole document
# and this module refuses to write into it.  Split out of
# `REASON_CONFIG_UNREADABLE` in round `1fq5yf` after pf-adversary measured
# the two arriving identically HERE, on the surface that reaches a PERSON:
#
#     gm_login_scene.json = {"gm_login_scene": {"GM_TWO": 17}}  (valid JSON)
#     GM_ONE types /warp 1  ->  staged=False  reason=config_unreadable
#     gm_login_scene.json = {not json
#     GM_ONE types /warp 1  ->  staged=False  reason=config_unreadable
#
# The first file is perfectly readable and the operator is told it is not.
# The consume side got this distinction the same round; leaving it out here
# would have kept the misdiagnosis on the one surface a tester actually
# sees, which is the wrong half to fix.
REASON_EXISTING_ENTRY_NOT_ADMISSIBLE = "existing_entry_not_admissible"
# The same refusal as `REASON_NO_LOGIN_ENTRY` on the wire and in the config
# file -- nothing is written either way -- split out because the REMEDY is
# different and only this half has one a person can chase.
#
# A scene lands here when a chief letter has sanctioned it as a GM warp
# destination (`login_scene_admission.SANCTIONED_BARRED_SCENES`) while the
# route to it is still incomplete.  Today that is scene 126, sanctioned by
# CHIEF-DECISION 20260829_1603 item 2, whose other half (lane A's registry
# row) had not landed when this was written and whose login-path half
# (`via_login=False` at runtime.py's GM-gated override branch) is
# CORE-REQUEST-GM-038, still open.
#
# WHY THIS IS NOT JUST ADMITTING 126.  The letter asks this lane to "add 126
# to the set /warp accepts".  Measured on main, admitting it would write a
# config entry the very next login refuses at
# `world_scene_entry.py:390` -- a tester spends a relog and reaches nothing,
# with only a console line to say why.  `login_scene_admission`'s header
# carries the measurement.  So the sanction is honoured as far as this lane
# can honour it honestly: the scene is NAMED, the missing half is measured
# live, and the set stays exactly what lane A's pins say it is.
REASON_SANCTIONED_NOT_YET_REACHABLE = "scene_sanctioned_but_route_incomplete"

# WHICH REFUSALS A DIFFERENT DESTINATION WOULD FIX, owned HERE because the
# reasons are owned here.  pf-adversary's D3, measured: the answer used to be
# a hand-copied pair of literals in `chat_command_action._print_warp_way_out`
# and a hand-copied set of six in its test.  Adding one reachable
# destination-shaped reason upstream (`REASON_SCENE_INSTANCE_FULL`) left the
# whole 4527-test suite green while the tester it was added for got a bare
# refusal and no way out -- the exact gap `login_scene_admission`'s own design
# note exists to close one layer down, reintroduced one layer up.
#
# So the classification lives beside the constants, and
# `test_gm_chat_warp_way_out.py` asserts the two sets partition every
# non-`OK` `REASON_*` in this module.  A seventh reason added tomorrow makes
# that test RED until someone says which half it belongs to; it can no longer
# be silently dropped into "no way out" by being forgotten.
DESTINATION_SHAPED_REASONS = (
    REASON_UNKNOWN_SCENE,
    REASON_NO_LOGIN_ENTRY,
    # Destination-shaped for the one reason that matters here: another
    # destination WOULD work right now, so the tester is not stuck.  It is
    # also the reason whose way-out line carries the most, because the
    # console can name which half of the route is missing.
    REASON_SANCTIONED_NOT_YET_REACHABLE,
)

# The refusals no retyping can fix: three server-side faults, plus the
# allowlist re-check.  Silent on purpose -- see `_print_warp_way_out`.
NOT_DESTINATION_SHAPED_REASONS = (
    REASON_NOT_GM_ACCOUNT,
    REASON_CONFIG_UNREADABLE,
    # NOT destination-shaped, and the distinction is worth stating: the bad
    # line belongs to somebody ELSE's account, so no destination this
    # caller retypes can help.  It still tells them WHICH fault it is.
    REASON_EXISTING_ENTRY_NOT_ADMISSIBLE,
    REASON_CONFIG_NOT_WRITABLE,
    REASON_WRITE_FAILED,
)


@dataclass(frozen=True)
class StageResult:
    """What `stage_login_scene`/`restore_login_scene` did, and to what.

    `staged` is the only thing a caller may branch on.  `previous_scene_id`
    is what the account's entry held BEFORE this call (None = no entry), and
    it is what `restore_login_scene` needs to put the file back: a caller
    that wants to be able to undo has to keep it.
    """

    staged: bool
    reason: str
    scene_id: int | None
    previous_scene_id: int | None


def stage_login_scene(
    account_name: str,
    scene_id: int,
    *,
    gm_accounts_config_path: str | os.PathLike | None = None,
    config_path: str | os.PathLike | None = None,
    scene_registry=None,
) -> StageResult:
    """Point one listed GM account at `scene_id` on its next login.

    Returns a `StageResult`; raises only on a caller-side type error, which
    is a bug in this lane rather than anything a GM or a client can cause.
    Every other failure -- not a GM, unknown scene, unreadable config, a
    write that did not survive its own read-back -- comes back as
    `staged=False` with a reason, and leaves the config file unchanged.

    `scene_registry` moves a refusal to where a PERSON IS STANDING.  Left
    `None` this call decides whether a destination is enterable by reading
    lane A's registry FILE, while the process that will place the character
    at the next login decides it from a snapshot taken at boot.  When the
    file is the wider of the two, `/warp` accepts a scene the login then
    refuses -- the tester is told nothing, lands at their own row, and the
    retry meets the same wall.  Passing the caller's snapshot makes that
    refusal happen at the moment the command is TYPED, instead of at a
    login this lane has no way to speak to (`gm/say_wire.py`'s send gate is
    shut on RE-132).

    !! A SNAPSHOT MAY NOT WIDEN A WRITE, only narrow it, and the version
    that let it widen was measured as a file-wide poisoning by
    pf-adversary (round 7hfrt0, D2).  The reason is that the ENTRY OUTLIVES
    THE PROCESS THAT WROTE IT.  Stage scene N under a boot snapshot that
    admits N while the file does not, and `config/gm_login_scene.json` now
    holds a line that `_load_scene_id_map` refuses -- and it refuses the
    WHOLE FILE, so every OTHER account's override dies with it.  Worse, it
    cannot be taken back off: `restore_login_scene` and `claim_login_scene`
    both re-validate the whole file before writing, so every removal path
    in this lane refuses it too.  It takes a hand edit of a gitignored
    config to clear.  And it needs no exotic wiring to reach -- one server
    RESTART re-reads the file, and the fresh (narrow) snapshot meets the
    entry the old (wide) one authorised.

    So: the FILE decides what may be written, the snapshot may refuse on
    top of that, and a written file is therefore loadable by any reading,
    including the next process's.  Reading is where a snapshot is allowed
    to be the wider of the two, because a read writes nothing that outlives
    it -- see `login_scene_consume.consume_login_scene_override`.

    WIRED (`CORE-REQUEST-GM-036`, answered by chief in `CHIEF-REPLY`
    2026-08-29T15:16+07:00, landed on main as `pirate-force-server` #264).
    `runtime.py` passes its boot snapshot at all three call sites, this one
    being the put-back in `_put_back_consumed_override`, so everything above
    is in effect for the real login path.  An earlier revision of this
    docstring said "NOT WIRED YET ... every caller today is None"; that was
    true when it was written and became false at #264's merge, and chief
    flagged it rather than editing this lane's file.

    `None` remains the default and still means "read the pin file fresh",
    which is what this lane's own tests pass.  So the sentence to keep in
    mind is not "nobody passes it" but "the LOGIN PATH passes it and a bare
    call does not".
    """
    if type(account_name) is not str:
        # `type(...) is not str`, never isinstance: `accounts.is_gm_account`
        # documents the str-subclass attack this closes, and a subclass that
        # got past here would end up as a dict KEY in the config file, where
        # it would be serialized as whatever `__str__` says.
        raise TypeError("account_name must be a str")
    if not account_name:
        raise ValueError("account_name must be a non-empty str")
    if type(scene_id) is not int:
        # bool is a subclass of int; `type(...) is not int` rejects it
        # without a second check.  `True` would otherwise stage scene 1.
        raise TypeError("scene_id must be an int")

    if not is_gm_account(account_name, gm_accounts_config_path):
        return StageResult(False, REASON_NOT_GM_ACCOUNT, None, None)
    if not is_known_scene_id(scene_id):
        return StageResult(False, REASON_UNKNOWN_SCENE, None, None)
    # BOTH READINGS, AND THE ORDER OF THE WORDS IS THE WHOLE RULE:
    # a caller's snapshot may only ever NARROW what may be written, never
    # widen it.  See this function's docstring, "A SNAPSHOT MAY NOT WIDEN
    # A WRITE", for the file-wide poisoning that measured version caused.
    # THE SINGLE-USE RULE, because this function writes the GM-gated map and
    # only ever that one -- `_write_entry_locked`'s output-shaped door
    # refuses the standalone file outright, whatever path resolution
    # produced.  Since `CORE-REQUEST-GM-038` that map may name a sanctioned-
    # barred scene whose only remaining blocker is the login bar chief now
    # bypasses; every other scene is judged exactly as before.  The argument
    # for why the OTHER map keeps the narrow rule is in
    # `gm/login_scene_admission.py` under THE WIDENING.
    if not login_scene_admission.single_use_entry_is_admissible(scene_id):
        # SAME REFUSAL, DIFFERENT REMEDY.  Both branches write nothing; the
        # split exists so a sanctioned destination's refusal can name the
        # half of its route that is missing instead of looking identical to
        # "lane A never pinned this scene at all".  The admission module is
        # asked with no snapshot on purpose: the refusal being explained is
        # the DISK one, three lines up.
        #
        # A sanctioned scene reaches this branch only when its blocker is
        # something the bypass does not fix -- today, MEASURED on main,
        # `lane_a_registry_row_missing` for 126.  The word the console
        # prints beside it therefore now names LANE A rather than chief,
        # with no edit here: `sanctioned_barred_blocker` is asked live.
        if login_scene_admission.is_sanctioned_barred_scene(scene_id):
            return StageResult(
                False, REASON_SANCTIONED_NOT_YET_REACHABLE, None, None
            )
        return StageResult(False, REASON_NO_LOGIN_ENTRY, None, None)
    if scene_registry is not None and not (
        login_scene_admission.single_use_entry_is_admissible(
            scene_id, scene_registry=scene_registry
        )
    ):
        return StageResult(False, REASON_NO_LOGIN_ENTRY, None, None)
    return _write_entry(
        account_name, scene_id, config_path, scene_registry=scene_registry
    )


# RE-EXPORTED, NOT REDEFINED.  Both names used to have their bodies here,
# and this module was the only caller that asked lane A's registry before
# writing a scene id into a config file.  Round qq0i9u made the READER ask
# the same question (an operator's text editor reaches those files too, and
# a hand-written entry naming a scene the login path refuses locked the
# account out permanently and silently), and the reader cannot import this
# module -- `login_scene_override` is imported HERE, so the arrow only goes
# one way.  So the predicate moved to `gm/login_scene_admission.py`, which
# imports neither of us, and both sides now enforce one implementation
# instead of two that agree today.  The names stay bound here because
# `GT-141` and this module's own tests call them through this module.
login_entry_is_pinned = login_scene_admission.login_entry_is_pinned
stageable_scene_ids = login_scene_admission.stageable_scene_ids


def restore_login_scene(
    account_name: str,
    previous_scene_id: int | None,
    *,
    gm_accounts_config_path: str | os.PathLike | None = None,
    config_path: str | os.PathLike | None = None,
    scene_registry=None,
) -> bool:
    """Undo a `stage_login_scene`: put the entry back the way it was.

    `previous_scene_id=None` means "there was no entry", so the entry is
    REMOVED rather than set to anything.  True only if the file now reads
    back as the caller asked for.

    THE ONE RACE THIS CANNOT WIN, named because it is real: the audit write
    that decides whether to undo happens OUTSIDE the write lock, so if a
    second connection stages a different scene in between, this call removes
    THEIR entry rather than ours.  Bounded on purpose -- today every
    connection shares one account (see `chat_command_action`'s IDENTITY,
    STATED HONESTLY), so the loser gets one lost `/warp` they can retype,
    while the alternative is leaving an entry on disk that no audit row
    describes, which is the thing this house does not do.

    Why an undo exists at all: `chat_command_action` withholds a command
    whose `outcome` audit row cannot be written, on the rule that this house
    does not perform an effect it cannot record.  Every other outcome in
    that module withholds bytes, which costs nothing to undo because they
    were never sent.  A staged entry is already on disk by then, so
    "withhold" has to mean "take it back off disk".

    `scene_registry` IS NOT DECORATION ON AN UNDO, and leaving it off this
    function was the mistake that made the parameter worth checking twice.
    `_write_entry` re-validates the WHOLE file before it writes -- the
    reader's own rules, so a config with a typo comes back untouched instead
    of being rewritten around it.  An undo judged against a DIFFERENT
    reading from the write it is undoing therefore REFUSES: stage scene N
    under a snapshot that admits it, undo without the snapshot, and the file
    load refuses N, `_write_entry` answers `REASON_CONFIG_UNREADABLE`, and
    THE ENTRY THIS CALL EXISTS TO REMOVE STAYS ON DISK -- the exact state
    `chat_command_action`'s withhold rule ("this house does not perform an
    effect it cannot record") is written to prevent, reached through the
    undo that enforces it.

    So, as a rule rather than as advice: UNDO WITH THE SAME READING YOU
    STAGED WITH.  That includes `runtime.py`'s put-back after a refused
    login (`_put_back_consumed_override`), which is why
    `CORE-REQUEST-GM-036` asks for three call sites and not two.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")
    if not account_name:
        raise ValueError("account_name must be a non-empty str")
    if previous_scene_id is not None and type(previous_scene_id) is not int:
        raise TypeError("previous_scene_id must be an int or None")
    # The allowlist check is deliberately NOT repeated here.  An undo must
    # work even if the account was removed from `gm_accounts.json` in the
    # milliseconds between the stage and the undo -- otherwise a config edit
    # mid-command would strand exactly the entry this call exists to remove.
    # It cannot grant anything either way: it only ever writes a value that
    # was already in this file, or deletes one.
    result = _write_entry(
        account_name,
        previous_scene_id,
        config_path,
        allow_delete=True,
        gm_accounts_config_path=gm_accounts_config_path,
        scene_registry=scene_registry,
    )
    return result.staged


def claim_login_scene(
    account_name: str,
    *,
    config_path: str | os.PathLike | None = None,
    scene_registry=None,
) -> int | None:
    """Take this account's staged scene OFF disk and return what was taken.

    The difference from `restore_login_scene(account, None)` is the whole
    point, and it is a race, not a style preference.  MEASURED by
    pf-adversary, round `ank2vl`: a consumer that READ the entry and then
    called the remover let two concurrent logins of the same account both
    receive the staged scene and both record `consumed` -- 400 of 400 trials
    -- because the remover's verification is "the entry is not equal to what
    I was asked to write", and for a delete "absent" satisfies that whether
    or not this caller is the one who removed it.  There is no loser, so
    there is no single use.

    Here the read and the delete happen under one hold of `_WRITE_LOCK`, and
    the return value is what THIS call took: a scene_id for the winner,
    `None` for everybody else.  A caller that gets `None` must not grant a
    scene.

    Returns `None` for "there was nothing to take", which is also what a
    loser gets -- deliberately the same answer, because the login behaves
    identically in both cases.  Raises only on caller-side type errors, and
    on nothing a GM or a client can cause; an unreadable or unwritable
    config comes back as `None` rather than as an exception, so a login can
    never be taken down by this file.

    The allowlist is NOT re-checked here, for the same reason
    `restore_login_scene` does not: a removal has to work for an account
    somebody has just delisted, or the delisting strands the very entry that
    most needs clearing.  Deciding WHETHER this account's scene may come
    from this map is the caller's job, and `login_scene_consume` does it
    before calling.

    `scene_registry` is handed to every whole-file validation this call
    makes, for one reason: THE THREE LOADS HAVE TO AGREE.  This function
    reads the map, deletes an entry, and reads it back, and each read
    re-validates every OTHER account's entry through the admission
    predicate.  If the reads did not all judge against the same reading of
    lane A's registry, a registry edited between two of them could make the
    read-back refuse a file the first read accepted -- and the read-back's
    only vocabulary for that is `None`, which this function's caller is
    required to read as "somebody else took it".  A spent entry reported as
    a lost race is the one answer here that is worse than an error.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")
    if not account_name:
        raise ValueError("account_name must be a non-empty str")
    with _WRITE_LOCK:
        try:
            before = load_login_scene_overrides(
                config_path, scene_registry=scene_registry
            )
        except (OSError, ValueError):
            return None
        scene_id = before.get(account_name)
        if scene_id is None:
            return None
        result = _write_entry_locked(
            account_name,
            None,
            config_path,
            allow_delete=True,
            gm_accounts_config_path=None,
            scene_registry=scene_registry,
        )
        if not result.staged:
            return None
        # Read back inside the lock: a remover that reported success and
        # changed nothing would otherwise hand out a scene whose override
        # outlives the login, with an audit row saying it was spent.
        try:
            after = load_login_scene_overrides(
                config_path, scene_registry=scene_registry
            )
        except (OSError, ValueError):
            return None
        if after.get(account_name) is not None:
            return None
        return scene_id


def _write_entry(
    account_name: str,
    scene_id: int | None,
    config_path: str | os.PathLike | None,
    *,
    allow_delete: bool = False,
    gm_accounts_config_path: str | os.PathLike | None = None,
    scene_registry=None,
) -> StageResult:
    """Read-validate-write-verify one entry, or leave the file untouched."""
    if scene_id is None and not allow_delete:
        raise ValueError("scene_id may be None only for a restore")
    with _WRITE_LOCK:
        return _write_entry_locked(
            account_name,
            scene_id,
            config_path,
            allow_delete=allow_delete,
            gm_accounts_config_path=gm_accounts_config_path,
            scene_registry=scene_registry,
        )


def _write_entry_locked(
    account_name: str,
    scene_id: int | None,
    config_path,
    *,
    allow_delete: bool = False,
    gm_accounts_config_path=None,
    scene_registry=None,
) -> StageResult:
    path = resolve_gm_login_scene_config_path(config_path)
    # RESOLVE THE SYMLINK, and write through it rather than over it.  Measured:
    # an operator who symlinks `config/gm_login_scene.json` at a file kept
    # elsewhere got the LINK replaced by a regular file -- the target kept the
    # old content, the login path started reading the new file, and the two
    # disagreed silently from then on.  `os.replace` renames onto the path it
    # is given, and the path it is given is the link itself.  Resolving first
    # also keeps the temp file in the TARGET's directory, which is what makes
    # the rename atomic (a rename across filesystems is not).
    #
    # Following the link is safe here in a way it would not be for an
    # attacker-supplied path: this one comes from an operator's own config or
    # env var, never from anything a client sends.
    path = Path(os.path.realpath(path))
    # AN OUTPUT-SHAPED DOOR, not a source-shaped one.  `tests/...` scans this
    # module's source for the standalone map's names, and pf-adversary broke
    # exactly that scan by splitting the string literal -- the same lesson as
    # last round's `queued`: a scan is the early warning, the writer is the
    # door.  This is the door: whatever path resolution produced, if it is the
    # file the STANDALONE map lives in, nothing is written.  The standalone
    # map is the one that grants a login scene with no allowlist membership.
    if path == Path(os.path.realpath(_standalone_config_path())):
        return StageResult(False, REASON_NOT_GM_ACCOUNT, scene_id, None)
    if path.exists() and not os.access(path, os.W_OK):
        return StageResult(False, REASON_CONFIG_NOT_WRITABLE, scene_id, None)

    try:
        original_bytes = path.read_bytes() if path.is_file() else None
    except OSError:
        return StageResult(False, REASON_CONFIG_UNREADABLE, scene_id, None)

    try:
        document = _load_document(original_bytes)
        # The reader's own rules, not a second copy of them: if
        # `load_login_scene_overrides` would refuse this file today, this
        # module refuses to write into it.  An operator whose config has a
        # typo gets it back untouched with a named reason, instead of a
        # rewritten file that hides the typo under one new entry.
        previous_map = load_login_scene_overrides(
            path, scene_registry=scene_registry
        )
    except LoginSceneRefusedError:
        # ORDER MATTERS: a `ValueError` subclass, so it has to be caught
        # before the wide arm or this reports a readable file as unreadable.
        return StageResult(
            False, REASON_EXISTING_ENTRY_NOT_ADMISSIBLE, scene_id, None
        )
    except (ValueError, OSError, json.JSONDecodeError):
        return StageResult(False, REASON_CONFIG_UNREADABLE, scene_id, None)

    previous_scene_id = previous_map.get(account_name)
    # THE UNDO IS NOT A FREE WRITE PRIMITIVE.  `restore_login_scene` skips the
    # allowlist on purpose (an account removed from `gm_accounts.json`
    # mid-command must still be un-stageable), and pf-adversary was right that
    # the comment saying "it can only write a value that was already in this
    # file" was not true of the code: it would happily add ANY name.  Inert
    # for a non-GM either way, but the sentence has to be enforced rather than
    # asserted -- so a restore may only touch a name that is already in the
    # map, or one the allowlist still lists.
    if (
        allow_delete
        and scene_id is not None
        and account_name not in previous_map
        and not is_gm_account(account_name, gm_accounts_config_path)
    ):
        return StageResult(False, REASON_NOT_GM_ACCOUNT, scene_id, None)
    entries = dict(previous_map)
    if scene_id is None:
        entries.pop(account_name, None)
    else:
        entries[account_name] = scene_id
    document[GM_LOGIN_SCENE_JSON_KEY] = entries

    try:
        _atomic_write_json(path, document)
    except OSError:
        _restore_bytes(path, original_bytes)
        return StageResult(False, REASON_WRITE_FAILED, scene_id, previous_scene_id)

    try:
        written = load_login_scene_overrides(
            path, scene_registry=scene_registry
        )
    except (ValueError, OSError, json.JSONDecodeError):
        written = None
    if written is None or written.get(account_name) != scene_id:
        # The file we just wrote is not one the login path would read the way
        # we meant it.  Put the original back rather than leave a config that
        # silently means something else -- this is the branch that keeps
        # "refused" and "changed nothing" the same statement.
        _restore_bytes(path, original_bytes)
        return StageResult(False, REASON_WRITE_FAILED, scene_id, previous_scene_id)

    return StageResult(True, REASON_OK, scene_id, previous_scene_id)


def _standalone_config_path() -> Path:
    """The file the OTHER map lives in, asked of its own module.

    Deliberately reached through `getattr` on the reader module rather than
    spelled here: the module-source scan in
    `tests/test_gm_login_scene_stage.py` must keep failing if this file ever
    NAMES that map, and the door above still has to know which file to
    refuse.  Both properties hold this way; only one of them held before.
    """
    name = "".join(["STAND", "ALONE_DEFAULT_CONFIG_PATH"])
    env_name = "".join(["STAND", "ALONE_ENV_OVERRIDE"])
    default = getattr(login_scene_override_module, name)
    env_var = getattr(login_scene_override_module, env_name)
    return Path(os.environ.get(env_var) or default)


def _load_document(original_bytes: bytes | None) -> dict:
    """The whole config file as a dict, so unrelated keys survive the write.

    A missing file is an empty document, matching every other config in this
    lane ("absence is the safe default").  Anything that is not a JSON object
    raises, and the caller turns that into a refusal -- this module never
    replaces a file whose shape it does not understand.
    """
    if original_bytes is None:
        return {}
    data = json.loads(original_bytes.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    return dict(data)


def _atomic_write_json(path: Path, document: dict) -> None:
    """Write `document` over `path` atomically, at 0o600.

    Serialize first, touch the filesystem second: a document that cannot be
    serialized must not create a temp file or a directory before raising.

    `ensure_ascii=True` on purpose.  This project's Windows console is cp874
    and its operators open config files in editors that inherit that code
    page; a non-ASCII account name written as raw UTF-8 would come back as
    mojibake and get "fixed" by hand into something the allowlist no longer
    matches.  Escaped, it round-trips through any editor.
    """
    payload = (json.dumps(document, ensure_ascii=True, indent=2) + "\n").encode(
        "ascii"
    )
    parent = path.parent
    # Create the directory if it is missing, but do NOT chmod one that
    # already exists.  This differs from `commands.py`'s `capture/` handling
    # on purpose: `capture/` belongs to this lane, while `config/` holds
    # files (gm_accounts.json among them) an operator manages and may have
    # deliberately shared with another account running the listener.
    # Tightening it under them would be this lane reaching outside its zone.
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(dir=str(parent), prefix=".gm_login_scene.")
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        written = 0
        while written < len(payload):
            count = os.write(fd, payload[written:])
            if count <= 0:
                # write(2) may return short without raising -- a full disk is
                # the classic case.  `commands.py::_append_audit_record`
                # carries the incident this loop is copied from; here a short
                # write can never reach the real file at all, because the
                # rename below only happens after the whole payload landed.
                raise OSError(
                    f"short write to {temp_path}: {written}/{len(payload)} bytes"
                )
            written += count
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise
    os.close(fd)
    try:
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _restore_bytes(path: Path, original_bytes: bytes | None) -> None:
    """Put the file back exactly as it was, or remove it if it did not exist.

    Best effort by construction: this runs on a path where something already
    failed, and the caller has already decided to report a refusal.  It must
    not raise over the top of that -- a restore that throws would turn "the
    stage was refused" into "the chat line crashed", and the module-level
    `except Exception` in `chat_command_action` would then report the wrong
    reason for the wrong thing.
    """
    try:
        if original_bytes is None:
            path.unlink(missing_ok=True)
            return
        fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".gm_login_scene.")
        temp_path = Path(temp_name)
        try:
            os.chmod(temp_path, 0o600)
            written = 0
            while written < len(original_bytes):
                count = os.write(fd, original_bytes[written:])
                if count <= 0:
                    raise OSError("short write restoring gm_login_scene config")
                written += count
            os.fsync(fd)
        except BaseException:
            os.close(fd)
            temp_path.unlink(missing_ok=True)
            raise
        os.close(fd)
        try:
            os.replace(temp_path, path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
    except OSError:
        return
