"""P-3 catalogue: the GM surface, row by row, with every unknown named.

`COO-DECISION 20260904_0245` item 1 (from `PANYA-DECISION 20260904_0233`
item 3) redefined P-3: it is no longer "the GMUI window opens" (`GT-207`
PASS bought that), it is "every button and every function on all three GMUI
pages actually works".  Its stated reason for asking for a catalogue FIRST:
"ครบทุกตัว" is only countable once the total is known.  This module is that
count, in code rather than in a report, so it cannot drift the way a table
pasted into a letter does.

WHAT THIS MODULE IS NOT, SAID FIRST
===================================
It is NOT the page/button/opcode table `0245` asked for, and this lane will
not pretend otherwise.  That table has to be read out of the client image --
which page carries which widget, and what each widget sends -- and NO CLONE
THIS LANE RUNS ON HAS THE IMAGE.  `pf_bridge/patches/gm_plugin/
GameMaster.cpp` and `docs/GM_LANE.md` record what the image work found
(`GMUI.project` declares `GMUI_1`; `GMUI_1.model` is the only one of 534
models carrying a `GMUI_BASIC` tab; no `GMUI_BASIC.model` exists), and that
is the whole of the committed page evidence: ONE tab name, on ONE page, and
the other two pages are not named anywhere this house can read.

So this module holds the two halves that CAN be built from committed
artifacts, and a third that is deliberately empty:

  1. `GM_VITALS` -- the GM-surface vitals from the client's own registry,
     each with whether THIS SERVER answers it today.  Grade A (a committed
     client artifact) for the id and the name; the "answers today" column is
     re-derived from this repo, not remembered.
  2. `log_types()` -- the 97 GM operations the client's own `GMTOOL` text
     table names.  This is the closest thing to an enumeration of "what GM
     functions exist" that any committed artifact holds.  It is NOT a button
     list and this module refuses to let a caller treat it as one (see
     `LOG_TYPES_ARE_NOT_BUTTONS`).
  3. `BUTTONS` -- EMPTY, on purpose, until an RE runner with the image fills
     it.  An empty table that says why it is empty is worth more than a
     guessed one: a guessed page/button row would be indistinguishable from
     a measured one three rounds later, and `nonclaim` discipline exists
     because this house has been burned by exactly that.

THE COUNT P-3 ASKED FOR
=======================
`progress()` returns `(closed, total)` for the buttons -- `(0, 0)` today,
and `total_is_unknown()` is True, which is the honest state: nobody can say
"x of y buttons work" yet because y is not known.  A future round that
starts filling `BUTTONS` gets the count for free, and `assert_backed` below
makes it impossible to fill a row with a claim nothing backs.

THE GUARD THAT MAKES THIS MORE THAN A LIST
==========================================
`assert_backed(row)` refuses any row that says the server answers a button
unless it names a handler symbol that EXISTS in this package right now.  It
is checked for every row at import time.  So the day someone writes
"ปุ่ม 3/12 ทำงานแล้ว" in a round file, either the three rows name three real
handlers or this module fails to import.  That is the whole point: P-3 is
graded on buttons that work, and a catalogue that can be edited into
agreement with a claim grades nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib

_DATA_PATH = Path(__file__).parent / "data" / "gm_tool_log_types.tsv"

#: sha256 of this package's own copy of the client's `TEXTDATA_TH__GMTOOL`
#: table (`pf_bridge/gamedata/tables/TEXTDATA_TH__GMTOOL.tsv`, copied
#: byte-for-byte).  Checked at import time, same as `scene_catalog.py` and
#: `npc_switch_catalog.py`: this package never reads `pf_bridge` at runtime
#: (it is not next to this repo inside the gate), so the copy is the source
#: and a silent edit to it must fail loudly.
SOURCE_SHA256 = "8ede7f80ebb0fee239bed31563ad570225785369cbadd81e5611aa6fc7ed1208"

#: Said once, in a constant, so a future reader who greps rather than reads
#: still meets it: the 97 rows below are LOG TYPES -- the operations the
#: client has a log string for -- not buttons, not opcodes, and not a claim
#: that any of them is reachable from a GMUI page.  Some almost certainly
#: are not (a log line can be written by a server-side event).  Turning a
#: log type into a button row requires the image, i.e. the RE ticket this
#: module's docstring names.
LOG_TYPES_ARE_NOT_BUTTONS = (
    "gm_tool_log_types.tsv enumerates GM OPERATIONS THE CLIENT LOGS, not "
    "GMUI buttons: no committed artifact maps a log type to a widget, a "
    "page, or an outbound opcode"
)

#: The one page name any committed artifact carries, and the honest shape of
#: the rest.  `GMUI.project` -> `GMUI_1` -> child tab `GMUI_BASIC`
#: (`pf_bridge/patches/gm_plugin/GameMaster.cpp` GM-DATA-001/002, and
#: `docs/GM_LANE.md` round `gm17278` onward).  `PANYA-DECISION 20260904_0233`
#: item 3 says there are THREE pages -- the owner has seen them on screen --
#: so two rows here are placeholders naming what is missing, not empty
#: strings pretending the pages do not exist.
PAGE_KNOWN = "GMUI_BASIC"
PAGE_UNNAMED_2 = "UNNAMED_PAGE_2"
PAGE_UNNAMED_3 = "UNNAMED_PAGE_3"
PAGES = (PAGE_KNOWN, PAGE_UNNAMED_2, PAGE_UNNAMED_3)

#: Why the two placeholders are placeholders, in the record rather than in a
#: reviewer's memory.
PAGES_NOTE = (
    "three pages per PANYA-DECISION 20260904_0233 item 3 (the owner has seen "
    "them); only GMUI_BASIC is named by a committed artifact (GMUI_1.model's "
    "child tab).  The other two names are an image question, not a guess this "
    "lane gets to make"
)


@dataclass(frozen=True)
class VitalRow:
    """One vital on the GM surface, from the client's own registry."""

    vital_id: int
    name: str
    direction: str
    #: Module in this package that reads/writes the frame, or `None` when
    #: this server has no codec for it at all.  Re-derived by grep, not
    #: remembered -- `test_gm_gmui_catalog.py` re-greps it.
    handler_module: str | None
    #: One line on what a GMUI button would need from it.  No claim that any
    #: button uses it.
    note: str

    @property
    def server_has_a_codec(self) -> bool:
        return self.handler_module is not None


#: The GM-surface vitals named in the owner's 1630 order letter, each
#: resolved against this repo.  `direction` is from
#: `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`.
#:
#: `server_has_a_codec` is NOT "the button works".  A codec means this house
#: can read or write the frame; whether any GMUI widget sends it, and
#: whether the server does anything useful in response, are two further
#: questions, and both are open for every row here.
GM_VITALS = (
    VitalRow(
        0x51E9,
        "GM_RunGMCommandVital",
        "client->server",
        "gm.dispatch",
        "the inbound command lane; RE-091 established the real client gates "
        "sending it on a UI widget, which is why P-3 exists at all",
    ),
    VitalRow(
        0x8C77,
        "GM_RunGMCommandResultVital",
        "server->client",
        "gm.command_wire",
        "one-field result reader; the reply half of 0x51E9",
    ),
    VitalRow(
        0x5A19,
        "GM_UpdateGMStateVital",
        "server->client",
        "gm.state_wire",
        "layout proven in external/PF_SERIALIZER_FIELDS.tsv (tag 0x0B @+0x14, "
        "tag 0x0B @+0x15, tag 0x14 @+0x18)",
    ),
    VitalRow(
        0x8D30,
        "GM_ForbidToTalkResultVital",
        "server->client",
        None,
        "no codec in this package; a mute/forbid-to-talk button would need "
        "one built before it could report anything",
    ),
    VitalRow(
        0x9F2C,
        "Channel_GMGlobalMessageVital",
        "server->client",
        "gm.say_wire",
        "global-message codec exists; its send gate is this lane's own and is "
        "closed by default",
    ),
    VitalRow(
        0x162E,
        "CheatVital",
        "client->server",
        "gm.cheat_wire",
        "single string8 len32LE at +0x14 (external/PF_SERIALIZER_FIELDS.tsv)",
    ),
    VitalRow(
        0x6CEC,
        "Activity_CheatCodeVital",
        "client->server",
        None,
        "no codec in this package; layout not in the proven serializer table "
        "either",
    ),
)


@dataclass(frozen=True)
class ButtonRow:
    """One GMUI widget, once an image reader can name one.

    `client_frame` is the opcode the widget sends, `handler_symbol` the name
    in this package that answers it.  `assert_backed` refuses a row that
    claims an answer without a symbol that exists.
    """

    page: str
    button: str
    function: str
    client_frame: int | None
    handler_symbol: str | None
    owner: str

    @property
    def server_answers_today(self) -> bool:
        return self.handler_symbol is not None


#: EMPTY BY DECISION, NOT BY OVERSIGHT.  See the module docstring: filling a
#: row needs the client image, which no clone this lane runs on has.  The RE
#: ticket that fills it is the one this round sends; until it comes back,
#: `total_is_unknown()` is True and no round may write "x of y buttons work".
BUTTONS: tuple[ButtonRow, ...] = ()

#: Named so a test can pin it and a reader cannot mistake emptiness for
#: "there are no buttons".
BUTTONS_ARE_UNFILLED_BECAUSE = (
    "the page/button/opcode mapping is only in the client image; this clone "
    "has no image, no capture corpus and no screen (see the lane brief), so "
    "the rows are an RE question -- guessing them would produce rows "
    "indistinguishable from measured ones a few rounds later"
)


class GmuiCatalogError(Exception):
    """A catalogue row claims something nothing in this package backs."""


def assert_backed(row: ButtonRow) -> None:
    """Refuse a row that says the server answers a button it cannot name.

    THE POINT OF THIS FUNCTION.  P-3 is graded on buttons that WORK, and the
    cheapest way to appear to make progress on it is to add a row saying a
    button works.  This makes that fail at import time unless the named
    symbol actually resolves inside this package -- so a claim in a round
    file and the code that would have to exist for it are the same fact.
    """
    if row.handler_symbol is None:
        return
    module_name, _, attr = row.handler_symbol.rpartition(".")
    if not module_name or not attr:
        raise GmuiCatalogError(
            f"handler_symbol must be 'module.attr', got {row.handler_symbol!r} "
            f"(button {row.button!r} on page {row.page!r})"
        )
    import importlib  # noqa: PLC0415 - only needed when a row makes a claim

    try:
        module = importlib.import_module(f".{module_name}", package=__package__)
    except Exception as error:  # noqa: BLE001 - any import failure is a refusal
        raise GmuiCatalogError(
            f"button {row.button!r} claims handler {row.handler_symbol!r}, but "
            f"{module_name} is unimportable ({type(error).__name__})"
        ) from None
    if not hasattr(module, attr):
        raise GmuiCatalogError(
            f"button {row.button!r} claims handler {row.handler_symbol!r}, but "
            f"{module_name} has no {attr!r} -- a catalogue row may not outrun "
            "the code that would answer it"
        )


def _load_log_types() -> tuple[tuple[int, int, str], ...]:
    raw = _DATA_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise GmuiCatalogError(
            f"gm_tool_log_types.tsv has drifted from its pinned source: "
            f"expected {SOURCE_SHA256}, got {digest}"
        )
    rows = []
    lines = raw.decode("utf-8").splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        n_id, log_type, message = line.split("\t")
        rows.append((int(n_id), int(log_type), message))
    return tuple(rows)


_LOG_TYPES = _load_log_types()


def log_types() -> tuple[tuple[int, int, str], ...]:
    """The 97 `(n_ID, n_LogType, s_MESSAGE)` rows of the client's GMTOOL
    table -- GM OPERATIONS THE CLIENT LOGS.  See
    `LOG_TYPES_ARE_NOT_BUTTONS`."""
    return _LOG_TYPES


def vitals_without_a_codec() -> tuple[VitalRow, ...]:
    """The GM-surface vitals this server cannot read or write at all.

    These are the cheapest real P-3 work available without the image: a
    codec is buildable from the registry and the proven serializer table,
    and a button that sends one of them cannot be answered until it exists.
    """
    return tuple(row for row in GM_VITALS if not row.server_has_a_codec)


def total_is_unknown() -> bool:
    """True while nobody can say how many GMUI buttons there are.

    `COO-DECISION 20260904_0245`: P-3 moves to "รอ Panya ติ๊ก" only when every
    button works, and that is uncountable while this is True.  A round file
    that writes "ปุ่ม x/y" while this is True is writing a number nothing
    backs.
    """
    return not BUTTONS


def progress() -> tuple[int, int]:
    """`(buttons whose handler exists, buttons catalogued)`.

    `(0, 0)` today.  Read it with `total_is_unknown()`: 0 of 0 is not "all
    of them", it is "none of them are known".
    """
    return (sum(1 for row in BUTTONS if row.server_answers_today), len(BUTTONS))


for _row in BUTTONS:
    assert_backed(_row)
