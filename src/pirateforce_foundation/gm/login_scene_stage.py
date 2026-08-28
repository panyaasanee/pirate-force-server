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
would be guessing -- which this lane refuses.  Meanwhile the same-scene half
is frozen by COO order (`FORCE_POS_VITAL_VERSION_CONFIRMED = None`, COO-DECISION
20260829_0041) until chief's confirmation token compares against the commanded
point.  So today a tester who types `/warp 126` gets a refusal and no way at
all to see scene 126 -- while a path that DOES work, and is already wired and
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
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import tempfile
import threading
from pathlib import Path

from .accounts import is_gm_account
from .login_scene_override import (
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
) -> StageResult:
    """Point one listed GM account at `scene_id` on its next login.

    Returns a `StageResult`; raises only on a caller-side type error, which
    is a bug in this lane rather than anything a GM or a client can cause.
    Every other failure -- not a GM, unknown scene, unreadable config, a
    write that did not survive its own read-back -- comes back as
    `staged=False` with a reason, and leaves the config file unchanged.
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
    return _write_entry(account_name, scene_id, config_path)


def restore_login_scene(
    account_name: str,
    previous_scene_id: int | None,
    *,
    gm_accounts_config_path: str | os.PathLike | None = None,
    config_path: str | os.PathLike | None = None,
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
        account_name, previous_scene_id, config_path, allow_delete=True
    )
    return result.staged


def _write_entry(
    account_name: str,
    scene_id: int | None,
    config_path: str | os.PathLike | None,
    *,
    allow_delete: bool = False,
) -> StageResult:
    """Read-validate-write-verify one entry, or leave the file untouched."""
    if scene_id is None and not allow_delete:
        raise ValueError("scene_id may be None only for a restore")
    with _WRITE_LOCK:
        return _write_entry_locked(account_name, scene_id, config_path)


def _write_entry_locked(
    account_name: str, scene_id: int | None, config_path
) -> StageResult:
    path = resolve_gm_login_scene_config_path(config_path)

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
        previous_map = load_login_scene_overrides(path)
    except (ValueError, OSError, json.JSONDecodeError):
        return StageResult(False, REASON_CONFIG_UNREADABLE, scene_id, None)

    previous_scene_id = previous_map.get(account_name)
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
        written = load_login_scene_overrides(path)
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
