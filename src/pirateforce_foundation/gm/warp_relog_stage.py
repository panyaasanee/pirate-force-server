"""The relog half of a live `/warp` whose durable row was refused by policy.

WHY THIS MODULE EXISTS.  `PANYA 20260905_1329` wants `/warp 126` to move the
ship on screen NOW, and `PANYA 20260904_1430` wants the character to still be
there after closing the client and logging back in.  For every ordinary scene
one write serves both: `warp_scene_persist.persist_warp_scene` moves the
`character_positions` row in the same breath as the TeleportVital goes out.

Scene 126 cannot use that write and must not be made to.  Its login door is
shut by `COO-DECISION 20260829_1444`, so `persist_warp_scene` answers
`login_would_refuse` and REFUSES THE ROW -- correctly.  Opening that door to
buy the relog would trade a measured policy for a convenience, which is the
trade `1444` already refused once.

So the relog half travels the OTHER road, the one that was built for exactly
this and has already been seen to work on a real screen (R313, R318): the
single-use login entry of `CORE-REQUEST-GM-038`.  It is not a durable
position; it is a one-shot instruction that the NEXT login for this one GM
account starts in this one scene, consumed on use.

`COO-DECISION 20260905_1746` item 4 is the order that put this here, and it
named this lane's own file as the place, so there is no CORE-REQUEST to wait
on: everything below is inside `gm/`.

WHAT MAKES 126 THE ONLY SCENE ON THIS ROAD, and why there is no `126` written
anywhere in the code below.  The route opens only for a scene that is BOTH
refused by the login path AND named by a chief letter in
`login_scene_admission.SANCTIONED_BARRED_SCENES`, which today holds exactly
one id.  A scene that is merely refused gets the refusal it always got, with
no entry written and no line printed beyond `persist_warp_scene`'s own.  When
a future letter sanctions a second scene, this route follows the letter
rather than a constant somebody has to remember to edit --
`test_gm_warp_relog_stage.py` pins the "exactly one today" reading so that
widening the map is a decision somebody makes on purpose.

FAIL-CLOSED, AND NOT BY THIS MODULE'S OWN GOOD BEHAVIOUR.  The write itself
is `login_scene_stage.stage_login_scene`, which re-checks `gm_accounts`
membership against the caller's own allowlist file and re-validates the whole
config before and after writing.  A non-GM account reaching this function --
which it cannot, `handle_local_talk_chat` gates the command long before -- is
refused there as well as here.  Nothing in this path consults
`production_allowed`, by `CHARTER` rule 1 for this lane: the tool has to work
without the flag, and the flag is not what keeps a player out.  `gm_accounts`
is.

NON-CLAIM.  A staged entry is not evidence that the relog works.  It is the
instruction; `GT-266`'s second criterion (close the client, log back in, still
in Rising Sun Sea) is the measurement, and only a person at the client can
make it.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from . import login_scene_admission, login_scene_stage
from .warp_scene_persist import OUTCOME_LOGIN_WOULD_REFUSE


@dataclass(frozen=True)
class RelogStageResult:
    """What this module did, and how to take it back.

    `outcome` is the word for the event trail.  `undo` is `None` unless an
    entry was really written, and it exists for the reason `_Verdict.undo`
    exists at all, which pf-adversary measured once already in round `741zlx`
    (finding 1, CRITICAL): `chat_command_action._make_action` WITHHOLDS a
    composed `/warp` when its audit row cannot be appended -- a full disk, a
    read-only capture directory -- and then zero bytes go out.

    Without this handle the durable half of that story is: the row was never
    written (126's door is shut, so there is nothing there to undo), but a
    single-use login entry WAS, and it survives the withheld command.  The
    next login would then put the character into scene 126 having never been
    sent there, off a command that never reached the wire.  That is the same
    character-bricking shape `CHARTER-02` rule 2 forbids, arriving by the one
    door this round opened.
    """

    outcome: str
    undo: object | None = None

#: Printed to stderr once when the entry really was written, so a tester
#: reading the console after `/warp 126` sees BOTH lines the COO letter asks
#: for: `persist_warp_scene`'s `GM_WARP_SCENE_PERSIST_FAILED scene=126
#: reason=login_would_refuse` first, then this one.  Two lines because there
#: are two facts and they are not the same fact -- the row did not move, AND
#: the relog was arranged anyway.  Collapsing them would rebuild exactly the
#: blindness `COO-DECISION 20260904_1646` item 2 opened this vocabulary to
#: close.
CONSOLE_TOKEN = "GM_WARP_RELOG_ENTRY_STAGED"

#: And the line for when the second half did NOT happen after the first half
#: failed.  This is the state a tester must never have to infer from silence:
#: the row is not moved and the relog is not arranged, so the character comes
#: back where it started and nothing said so.
FAIL_CONSOLE_TOKEN = "GM_WARP_RELOG_ENTRY_NOT_STAGED"

#: The entry was written and read back by `stage_login_scene`.
OUTCOME_STAGED = "staged"

#: The persist outcome was not the one this route answers.  Includes
#: `persisted` -- a scene whose row moved needs no relog entry and must not
#: get one, because a single-use entry that fires on a login the durable row
#: already answers is a second source of truth for the same question.
OUTCOME_NOT_A_REFUSED_LOGIN = "not_a_refused_login"

#: The persist was refused by the login path, but no chief letter sanctions
#: this scene.  The ordinary refusal stands.  NO CONSOLE LINE for this one:
#: it is the unremarkable case (every barred scene that is not 126), and a
#: line here would print on warps that behave exactly as they always have.
OUTCOME_SCENE_NOT_SANCTIONED = "scene_not_sanctioned"

#: `stage_login_scene` refused; the suffix is its own reason word, not a
#: second vocabulary.
OUTCOME_STAGE_REFUSED_PREFIX = "stage_refused_"

#: `stage_login_scene` raised.  Type name only, never the message -- the same
#: rule every refusal in `chat_command_action.py` follows, for the same
#: reason: an exception message can carry a path or an account name onto a
#: console line an operator will paste somewhere.
OUTCOME_STAGE_RAISED_PREFIX = "stage_raised_"


def _console(line: str) -> bool:
    """Put one line on stderr.  Never raises.  NEVER falls back to stdout.

    The same guard, for the same measured reason, as
    `warp_scene_persist._console`: `sys.stderr` can be `None` (a detached
    console, `pythonw`, a harness that closed it) and `print` reads
    `file=None` as "use stdout", where a token corrupts the JSON artifact
    `tools/pf_runtimeres_death_headless_replay.py --json` writes there.

    Returns whether the line really went out, so a caller can name a lost
    line instead of assuming one was printed.
    """
    stream = sys.stderr
    if stream is None:
        return False
    try:
        print(line, file=stream)
    except Exception:  # noqa: BLE001 - a closed, replaced or raising stderr
        return False
    return True


def stage_relog_entry_after_refused_persist(
    persist_outcome: object,
    scene_id: object,
    account_name: object,
    *,
    gm_accounts_config_path=None,
    login_scene_config_path=None,
    scene_registry=None,
) -> RelogStageResult:
    """Arrange the relog for a live warp whose durable row was refused.

    Returns a `RelogStageResult`: one outcome word, and an undo that is
    offered ONLY when an entry really was written.  NEVER RAISES: this is called from inside a
    `/warp` that has already put a TeleportVital together, and an exception
    escaping here would take down a command whose frame is real and whose
    screen effect is about to happen.  That is the failure shape
    `_no_coords_live_target`'s own note describes paying for once already --
    an accepted command vanishing with no console line at all.

    The argument types are deliberately `object`: every one of them is
    checked below rather than trusted, because the value that decides whether
    a config file is written must not be a shape this function merely assumed.
    `stage_login_scene` type-guards them again (`type(...) is not int`, which
    rejects `True`), and both checks are kept: this one so the refusal has a
    word, that one so the file is safe from callers that never come through
    here.
    """
    if persist_outcome != OUTCOME_LOGIN_WOULD_REFUSE:
        # Every other outcome, `persisted` included.  Nothing printed, nothing
        # written: this is the path every warp in the game takes.
        return RelogStageResult(OUTCOME_NOT_A_REFUSED_LOGIN)

    if type(scene_id) is not int or not login_scene_admission.is_sanctioned_barred_scene(
        scene_id
    ):
        # `type(...) is not int` first and separately: `is_sanctioned_barred_
        # scene` raises TypeError on a non-int, and this function does not
        # raise.  A bool is an int subclass and is refused here for the reason
        # `stage_login_scene` gives -- `True` would otherwise ask about scene 1.
        return RelogStageResult(OUTCOME_SCENE_NOT_SANCTIONED)

    if type(account_name) is not str or not account_name:
        # A sanctioned scene WITH a broken account handle is the loud case:
        # the row did not move, and the relog cannot be arranged either.
        _console(
            f"{FAIL_CONSOLE_TOKEN} scene={scene_id} reason=no_account_name"
        )
        return RelogStageResult(
            f"{OUTCOME_STAGE_REFUSED_PREFIX}no_account_name"
        )

    try:
        result = login_scene_stage.stage_login_scene(
            account_name,
            scene_id,
            gm_accounts_config_path=gm_accounts_config_path,
            config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
    except Exception as error:  # noqa: BLE001 - type name only, as everywhere
        _console(
            f"{FAIL_CONSOLE_TOKEN} scene={scene_id} "
            f"reason={type(error).__name__}"
        )
        return RelogStageResult(
            f"{OUTCOME_STAGE_RAISED_PREFIX}{type(error).__name__}"
        )

    if not result.staged:
        _console(f"{FAIL_CONSOLE_TOKEN} scene={scene_id} reason={result.reason}")
        return RelogStageResult(
            f"{OUTCOME_STAGE_REFUSED_PREFIX}{result.reason}"
        )

    previous = result.previous_scene_id
    _console(
        f"{CONSOLE_TOKEN} scene={scene_id} "
        f"previous={'none' if previous is None else previous} "
        f"single_use=1"
    )
    def _undo() -> bool:
        # THE SAME READING THE STAGE USED, exactly as `_stage_action`'s own
        # undo explains: `restore_login_scene` re-validates the whole file, so
        # an undo judged against the file while the stage was judged against a
        # snapshot refuses and leaves the entry it was called to remove.
        try:
            return bool(
                login_scene_stage.restore_login_scene(
                    account_name,
                    previous,
                    gm_accounts_config_path=gm_accounts_config_path,
                    config_path=login_scene_config_path,
                    scene_registry=scene_registry,
                )
            )
        except Exception:  # noqa: BLE001 - an undo may not raise either
            return False

    return RelogStageResult(OUTCOME_STAGED, _undo)
