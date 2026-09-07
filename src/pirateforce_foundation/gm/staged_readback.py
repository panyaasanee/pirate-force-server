"""Read back WHAT IS STAGED for this GM's next login, in 12 ASCII characters.

WHY THIS MODULE EXISTS, said as the operator experiences it.  A cross-scene
`/warp` does not move anybody: it writes the account's next-login scene into
`config/gm_login_scene.json` (`gm/login_scene_stage.py`) and the scene appears
only after that GM logs out and back in.  Every other GM command that changes
durable state without moving a pixel says so ON SCREEN -- `/lv` answers
`LV SET RELOG`, a refused `/speed` answers `SPEED DENIED`, a mistyped line
answers `TYPO REFUSED`.  The staged warp answered nothing at all: its only
report is a `GM_CHAT_STAGED_NEXT_LOGIN` line on the SERVER console, which is
not where the person typing the command is looking.  An attended tester at
the client had exactly one way to find out which scene their next login would
open in -- open the JSON file next to the game and read it.

`staged` is that readback as a command.  It changes NOTHING: it reads the map
this lane already writes, for THIS account only, and answers on the same
local-talk notice channel the three sentences above use.

THE THREE ANSWERS, and why each is the length it is.  A notice body is
exactly 12 printable ASCII characters (`gm/say_wire.py::
NOTICE_TEXT_EXACT_LENGTH` -- a MEASURED length, GT-006/GT-009, not a style
rule), so these sentences were found inside that length rather than written
freely, the same way `TYPO REFUSED` and `LV SET RELOG` were:

    SCENE 000123   a scene is staged; the digits are the scene_id
    NO STAGE SET   this account has no entry in the map
    STAGE NOREAD   the map could not be read at all

EVERY CHARACTER COMES OUT OF THIS MODULE OR OUT OF AN INTEGER, never out of
anything a client typed.  `staged` takes no arguments at all, so there is no
query to echo; the scene_id is an `int` this lane's own loader already
validated against the committed catalog, rendered with `%06d`.  That is the
same rule the `warp <scene name>` suggestion line follows (LANE-GM round
`osxc85`, pf-adversary D2): text on this channel is this lane's words, and
the console it also reaches is cp874.

THE SCENE NAME IS NOT ON SCREEN, and that is not an oversight.  `Prison Exile
Island` does not fit in twelve characters, and a truncated island name is a
worse answer than an id the operator can type straight back into `warp`.  The
name goes to the SERVER console line instead, where the width is not pinned
and where the catalog's names are already known cp874-encodable.

NONCLAIMS.  A `SCENE 000123` on screen says the config file says 123.  It
does not say the login will grant it (admission is decided at login by
`gm/login_scene_admission.py` against a registry that can change under it),
it does not say any byte moved, and it is not evidence for M2 or for any GT
ticket: this is a tool for reaching a testable state, never proof that the
state is right.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import scene_catalog
from .login_scene_override import load_login_scene_overrides

# The one place these three bodies are spelled.  Their length is asserted by
# `tests/test_gm_staged_readback.py` against `say_wire.NOTICE_TEXT_EXACT_LENGTH`
# itself, so a round that moves the pinned length moves these with it instead
# of shipping a body the wire will refuse.
NOTICE_NOTHING_STAGED = "NO STAGE SET"
NOTICE_UNREADABLE = "STAGE NOREAD"

# `SCENE ` + six digits.  Six, not "as many as the id needs": a fixed width
# keeps the body at the pinned length for every id the loader can return, and
# a variable one would ship an 11-character body for scene 1 -- refused by
# `make_local_talk_notice_frame`, at the client, after the command worked.
NOTICE_SCENE_PREFIX = "SCENE "
NOTICE_SCENE_ID_DIGITS = 6
MAX_NOTICE_SCENE_ID = 10 ** NOTICE_SCENE_ID_DIGITS - 1

STATUS_STAGED = "staged"
STATUS_NOTHING_STAGED = "nothing_staged"
STATUS_UNREADABLE = "config_unreadable"
# A staged id that cannot be rendered in six digits.  Unreachable through the
# loader today (every id it returns is a row of the committed catalog, whose
# largest is three digits) and still a named status rather than a crash: this
# module accepts a config path from its caller, and "the file said 10000000"
# must be an answer, not a `ValueError` on the listener thread.
STATUS_ID_OUT_OF_RANGE = "scene_id_out_of_notice_range"

STATUSES = (
    STATUS_STAGED,
    STATUS_NOTHING_STAGED,
    STATUS_UNREADABLE,
    STATUS_ID_OUT_OF_RANGE,
)

# The name printed on the server console when the staged id has no catalog
# row.  Not `None` and not the empty string: the console line is read by grep
# in attended runs, and a missing value must read as a fact rather than as a
# broken formatter.
CONSOLE_UNNAMED_SCENE = "not_in_catalog"


@dataclass(frozen=True)
class StagedReadback:
    """One answer to `staged`, for one account.

    `notice_text` is always a body `say_wire.make_local_talk_notice_frame`
    accepts -- there is no status whose answer is "print nothing", because a
    command that sometimes answers and sometimes does not is a command an
    operator stops trusting.  `console_detail` is the same answer with the
    scene NAME and the failure TYPE in it, for the server console only.
    """

    status: str
    scene_id: int | None
    notice_text: str
    console_detail: str


def _scene_name_for(scene_id: int) -> str:
    if not scene_catalog.is_known_scene_id(scene_id):
        return CONSOLE_UNNAMED_SCENE
    return scene_catalog.gm_scene_name(scene_id)


def read_staged_scene(
    account_name: object,
    *,
    config_path: str | os.PathLike | None = None,
) -> StagedReadback:
    """What `config/gm_login_scene.json` says THIS account's next login opens.

    READ ONLY, and the distinction is a race rather than a style preference:
    `login_scene_stage.claim_login_scene` TAKES the entry off disk under a
    lock because a login must spend it exactly once.  This function must
    never do that -- an operator asking "what is staged" would otherwise
    consume the staging they were about to use, and the bug would look like
    a warp that silently did not happen.  It calls the loader, reads one key
    and returns.

    `account_name` is the session's authenticated `.token`, the same
    identity `_stage_action` writes under.  It is never read from a payload
    and never compared case-insensitively: the map's keys are whatever
    `stage_login_scene` wrote, so the lookup is exact or it is nothing.

    FAILS TO AN ANSWER, NEVER TO AN EXCEPTION.  A malformed or unreadable
    config makes the loader raise (its own fail-loud rule, which is right
    for a login that would otherwise send an operator's typo to an
    unreviewed scene), and raising HERE would turn a courtesy readback into
    `gm_chat_action_unexpected_*` on the listener thread -- this lane's
    standing rule is that a diagnostic may never alter dispatch.  So every
    exception becomes `STATUS_UNREADABLE`, and the console detail names the
    exception TYPE only: an arbitrary message can carry bytes the cp874
    console cannot print, which is the same reason `_typo_refused_notice`
    records a type name rather than a message.
    """
    if type(account_name) is not str:
        # Exact type, not `isinstance`: a `str` subclass can lie through
        # `__eq__`/`__hash__`, and this value selects WHOSE staging is read.
        return StagedReadback(
            STATUS_UNREADABLE,
            None,
            NOTICE_UNREADABLE,
            "staged_readback account_name_not_a_str",
        )
    try:
        overrides = load_login_scene_overrides(config_path)
        staged = overrides.get(account_name)
    except Exception as error:  # noqa: BLE001 - see the docstring
        return StagedReadback(
            STATUS_UNREADABLE,
            None,
            NOTICE_UNREADABLE,
            f"staged_readback unreadable error={type(error).__name__}",
        )
    if staged is None:
        return StagedReadback(
            STATUS_NOTHING_STAGED,
            None,
            NOTICE_NOTHING_STAGED,
            "staged_readback nothing_staged",
        )
    if type(staged) is not int or isinstance(staged, bool):
        # The loader promises `dict[str, int]`; a caller-supplied loader
        # double or a future widening that breaks the promise must not reach
        # `%06d` with something that formats into a body of the wrong width.
        return StagedReadback(
            STATUS_UNREADABLE,
            None,
            NOTICE_UNREADABLE,
            "staged_readback staged_value_not_an_int",
        )
    if staged < 0 or staged > MAX_NOTICE_SCENE_ID:
        return StagedReadback(
            STATUS_ID_OUT_OF_RANGE,
            staged,
            NOTICE_UNREADABLE,
            f"staged_readback out_of_notice_range scene={staged}",
        )
    return StagedReadback(
        STATUS_STAGED,
        staged,
        f"{NOTICE_SCENE_PREFIX}{staged:0{NOTICE_SCENE_ID_DIGITS}d}",
        f"staged_readback staged scene={staged} name={_scene_name_for(staged)!r}",
    )
