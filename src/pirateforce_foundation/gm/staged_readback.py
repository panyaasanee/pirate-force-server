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

`staged` is that readback as a command.  It WRITES NOTHING -- no file, no
row, no frame but its own sentence -- and it answers for THIS account only,
on the same local-talk notice channel the three sentences above use.  Not
"changes nothing at all": the loader it calls prints
`GM_LOGIN_SCENE_CONFIG_REFUSED` to stderr for every row of the file the
running process would refuse, including rows belonging to OTHER accounts, so
typing `staged` can put lines on the server console.  That is the loader's
own fail-loud rule and this command does not get to switch it off; what this
docstring must not do is call the command silent when it is not (pf-adversary
round `qpauwp`, D7).

IT ASKS THE SAME QUESTION THE LOGIN ASKS, and that is the whole design.  The
first version of this module read `gm_login_scene.json` directly, and
pf-adversary measured the screen giving the wrong answer three ways (round
`qpauwp`, D1/D2/D3): an account staged through
`gm_login_scene_standalone.json` was told `NO STAGE SET` while its next login
really did open scene 2; a registry file edited after boot moved the screen's
answer and not the login's, in both directions; and one inadmissible row
belonging to somebody else turned the whole answer into `STAGE NOREAD` on a
file that reads perfectly.  So this module now calls
`login_scene_override.get_login_scene_override` -- the function the login
path's own `consume_login_scene_override` calls to decide the scene, minus
the claim that spends it -- and passes the caller's `scene_registry`
snapshot straight into it.

WHAT THAT DOES AND DOES NOT CLOSE, stated because the first version of this
paragraph said "the screen and the login now disagree only where the disk
changes between the two moments, which no design can close" -- and two
divergences in this module's own PR refuted it (pf-adversary round
`h7bwnl`, D4).  What is closed is the QUESTION: the same lookup, over the
same maps, judged against the same registry snapshot.  What is not:

* a boot argument.  A listener booted with a non-default
  `login_scene_config_path` or `gm_accounts_config_path` reads back the
  files the chat commands were given, while `runtime.py`'s login leaves all
  three at their defaults.  That is a divergence with nothing on disk
  moving, and it belongs to every staging command in this lane rather than
  to this readback (`gm/chat_command_action.py::_staged_action` carries the
  detail and why it is not this lane's to close).
* what happens AFTER the lookup.  This function answers what the lookup
  would return.  The login then claims the entry and resolves an entry
  point, and either can still fail -- so `SCENE 000123` means the lookup
  says 123, never that a character will stand there.  See NONCLAIMS below.

THE THREE ANSWERS, and why each is the length it is.  A notice body is
exactly 12 printable ASCII characters (`gm/say_wire.py::
NOTICE_TEXT_EXACT_LENGTH` -- a MEASURED length, GT-006/GT-009, not a style
rule), so these sentences were found inside that length rather than written
freely, the same way `TYPO REFUSED` and `LV SET RELOG` were:

    SCENE 000123   a scene is staged; the digits are the scene_id
    NO STAGE SET   this account has no entry in either map
    STAGE BARRED   a map parses, and this process will not admit a row in it
    STAGE NOREAD   a map could not be read at all

`STAGE BARRED` and `STAGE NOREAD` are two sentences because they are two
faults with two different remedies -- restart the server (or fix lane A's
registry) versus edit the config file -- and `LoginSceneRefusedError`
(`gm/login_scene_override.py`) exists precisely so a caller can tell them
apart.  Folding both into "could not be read" is the misdiagnosis that class
was created to end: it sends an operator to grep a file that is correct.

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
from .login_scene_override import (
    LoginSceneRefusedError,
    get_login_scene_override,
)

# The one place these four bodies are spelled.  Their length is asserted by
# `tests/test_gm_chat_command_action.py` against `say_wire.NOTICE_TEXT_EXACT_LENGTH`
# itself, so a round that moves the pinned length moves these with it instead
# of shipping a body the wire will refuse.
NOTICE_NOTHING_STAGED = "NO STAGE SET"
NOTICE_UNREADABLE = "STAGE NOREAD"
NOTICE_REFUSED = "STAGE BARRED"

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
# The file parsed and this process will not admit one of its rows.  A
# SEPARATE status from `STATUS_UNREADABLE` for the reason the module
# docstring gives: two faults, two remedies, and one word for both sends the
# operator to the wrong one.
STATUS_REFUSED = "scene_not_admissible"
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
    STATUS_REFUSED,
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
    gm_accounts_config_path: str | os.PathLike | None = None,
    login_scene_config_path: str | os.PathLike | None = None,
    standalone_config_path: str | os.PathLike | None = None,
    scene_registry=None,
) -> StagedReadback:
    """What THIS account's next login is staged to open, asked the login's way.

    ONE QUESTION, ASKED ONCE.  `get_login_scene_override` is the same call
    `login_scene_consume.consume_login_scene_override` makes to decide the
    scene, so this function inherits every rule that decides a real login:
    the GM-gated map is consulted only for an account `gm/accounts.py`
    actually lists, the standalone map answers for accounts that are not GM
    at all, and both are judged by their own admission rule.  Re-deriving any
    of that here is how the first version of this module ended up telling an
    operator `NO STAGE SET` about a login that opened scene 2.

    READ ONLY, and the distinction is a race rather than a style preference:
    `login_scene_stage.claim_login_scene` TAKES the entry off disk under a
    lock because a login must spend it exactly once.  This function must
    never do that -- an operator asking "what is staged" would otherwise
    consume the staging they were about to use, and the bug would look like
    a warp that silently did not happen.  `get_login_scene_override` is the
    LOOK half of that pair by construction (see its docstring), which is why
    the answer comes from there and not from `consume_login_scene_override`
    with a flag.

    `scene_registry` IS THE CALLER'S, NOT A FRESH READ.  Whoever is going to
    grant the scene judges the config against the registry snapshot it took
    at boot (`CORE-REQUEST-GM-036`); a readback that read the registry file
    fresh would answer a different question and disagree with the login in
    both directions -- narrower on disk gives `STAGE NOREAD` for a login that
    works, wider gives `SCENE 000002` for a login that gets nothing.
    Measured both ways by pf-adversary (round `qpauwp`, D2), which also
    priced the fresh read at one registry parse per row in the map, on the
    listener thread.  `None` keeps a bare caller on the fresh read, the
    behaviour every test in this lane was written against.

    `account_name` is the session's `.token`, the same identity
    `_stage_action` writes under.  It is never read from a payload and never
    compared case-insensitively: the map's keys are whatever
    `stage_login_scene` wrote, so the lookup is exact or it is nothing.
    (`.token` is the process's own `--token` value rather than a per-
    connection identity -- this lane settled that already; the point here is
    only that it is not client-supplied text.)

    FAILS TO AN ANSWER, NEVER TO AN EXCEPTION.  A config the process cannot
    use makes the loader raise (its own fail-loud rule, which is right for a
    login that would otherwise send an operator's typo to an unreviewed
    scene), and raising HERE would turn a courtesy readback into
    `gm_chat_action_unexpected_*` on the listener thread -- this lane's
    standing rule is that a diagnostic may never alter dispatch.  So every
    exception becomes an ANSWER, and the console detail names the exception
    TYPE only: an arbitrary message can carry bytes the cp874 console cannot
    print, which is the same reason `_typo_refused_notice` records a type
    name rather than a message.
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
    if not account_name:
        # The login path refuses an empty name outright
        # (`consume_login_scene_override` raises `ValueError`), so no empty
        # name can ever be granted a scene.  Answering the lookup's own
        # `None` here would print `NO STAGE SET`, which reads as "your file
        # has no line for you" rather than "this session has no name".
        return StagedReadback(
            STATUS_UNREADABLE,
            None,
            NOTICE_UNREADABLE,
            "staged_readback account_name_empty",
        )
    try:
        staged = get_login_scene_override(
            account_name,
            gm_accounts_config_path,
            login_scene_config_path,
            standalone_config_path,
            scene_registry=scene_registry,
        )
    except LoginSceneRefusedError as refused:
        # CAUGHT BEFORE `Exception` BECAUSE IT IS ONE -- a `ValueError`
        # subclass, so the order of these two arms is the whole distinction
        # and not a formality.  `refused.scene_id` is the row's id and may
        # belong to ANOTHER account: the loader holds the whole file to one
        # rule, so somebody else's inadmissible line refuses this read too.
        # That is the login's behaviour as well, which is why the screen
        # reports it instead of hiding it -- but it is reported as "barred",
        # never as "unreadable" (pf-adversary round `qpauwp`, D3).
        return StagedReadback(
            STATUS_REFUSED,
            refused.scene_id,
            NOTICE_REFUSED,
            f"staged_readback scene_not_admissible row_scene={refused.scene_id}",
        )
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
        # The lookup promises `int | None`; a caller-supplied loader double
        # or a future widening that breaks the promise must not reach `%06d`
        # with something that formats into a body of the wrong width.
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
