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
artifacts, and a third that ~~is deliberately empty~~ turned out to have a
source this lane had not opened:

  1. `GM_VITALS` -- the GM-surface vitals from the client's own registry,
     each with whether THIS SERVER answers it today.  Grade A (a committed
     client artifact) for the id and the name; the "answers today" column is
     re-derived from this repo, not remembered.
  2. `log_types()` -- the 97 GM operations the client's own `GMTOOL` text
     table names.  This is the closest thing to an enumeration of "what GM
     functions exist" that any committed artifact holds.  It is NOT a button
     list and this module refuses to let a caller treat it as one (see
     `LOG_TYPES_ARE_NOT_BUTTONS`).
  3. `BUTTONS` -- ~~EMPTY, on purpose, until an RE runner with the image
     fills it~~ FILLED, round `y1evqj`, from a source that is not the image:
     the four GT-207/R304 GMUI screenshots this house already committed
     (`ROW_CENSUS_SCREENSHOTS`).  See "WHERE THE ROWS CAME FROM" below --
     what they buy is the COUNT and the SHAPE of each row, not one label
     and not one opcode, and every row here still carries
     `handler_symbol=None`.

WHERE THE ROWS CAME FROM, AND WHAT THEY DO NOT SAY
==================================================
`pf_bridge/evidence_screens/GT207_R304_gmui_*` are four 1656x1000 PNGs of
the real client with the real GMUI open -- one per tab, plus a second shot
of tab 1.  They are CLIENT-OBSERVABLE evidence, which is a different (and
for "what is on the page", a stronger) class than the image work this
module's first draft was waiting on: a screenshot cannot tell you what a
widget SENDS, but nothing is better placed to tell you how many there are.

So the census reads off exactly the two things a photograph can carry:
  * HOW MANY radio-selected function rows each page has -- 7 + 5 + 5 = 17,
    and
  * the SHAPE of each row (how many paired option radios, text inputs and
    numeric inputs sit on it).

It does NOT read the labels.  Every row's `label_status` is `UNREAD` except
two that begin with a latin token (`NPC` on page 1 row 3, `BUFF` on page 3
row 2); the Thai is legible as Thai at this resolution but NOT reliably
legible as specific words, and a guessed label is exactly the row this
module's own guard exists to keep out.  Reading the 17 labels is one
attended pass at the screen, and the letter this round sends asks for it as
one `ATTENDED:` block rather than 17.

THE ONE THING THE SCREENSHOTS AGREE ON AND STILL CANNOT SETTLE
---------------------------------------------------------------
Page 1's rows are evenly spaced ~40 px apart except between row 5 (~y=525)
and row 6 (~y=605), where there is an ~80 px gap -- one row-height of
nothing, in BOTH tab-1 shots.  That is the width of a widget that is
present in the layout and not drawn in this state.  So 17 is a FLOOR that
two independent shots agree on, not a proven ceiling, and
:func:`total_is_confirmed_on_screen` stays False until an attended pass
says otherwise.  `PAGE_1_UNEXPLAINED_GAP` carries this in a constant so a
reader who greps rather than reads still meets it.

THE COUNT P-3 ASKED FOR
=======================
`progress()` returns `(closed, total)` for the rows -- `(0, 17)` today:
seventeen GM functions on three pages, none of which this server answers.
`total_is_unknown()` is now False (there IS a measured count) while
`total_is_confirmed_on_screen()` is still False (the count is
screenshot-bounded, see the gap above).  Both are needed: a round may now
write "0 of 17", and may not write "17 is all of them".
`assert_backed` below still makes it impossible to fill a row with a claim
nothing backs, which is what will matter when rows start claiming handlers.

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
_ROW_CENSUS_PATH = Path(__file__).parent / "data" / "gmui_widget_census.tsv"

#: sha256 of this package's own copy of the client's `TEXTDATA_TH__GMTOOL`
#: table (`pf_bridge/gamedata/tables/TEXTDATA_TH__GMTOOL.tsv`, copied
#: byte-for-byte).  Checked at import time, same as `scene_catalog.py` and
#: `npc_switch_catalog.py`: this package never reads `pf_bridge` at runtime
#: (it is not next to this repo inside the gate), so the copy is the source
#: and a silent edit to it must fail loudly.
SOURCE_SHA256 = "8ede7f80ebb0fee239bed31563ad570225785369cbadd81e5611aa6fc7ed1208"

#: sha256 of this package's row census.  Unlike `SOURCE_SHA256` this file is
#: NOT a copy of a client table -- it is this lane's own reading of the
#: screenshots below, so the pin buys something different: a later round
#: that edits a row (adds one, renames a slug, changes a shape) has to move
#: this constant in the same commit, which is the moment a reviewer gets to
#: ask what it was read off.
ROW_CENSUS_SHA256 = (
    "22c4cc55c69f96655dc711f2e780ab33a9283ed7b8fca7cf4fae905acea3c611"
)

#: The committed client-observable evidence the census was read off, pinned
#: by content so "the screenshots" can never quietly become different
#: screenshots.  Paths are relative to the bridge repo (`pf_bridge/`), which
#: this package never reads at runtime -- the pins are the record, not a
#: lookup.  All four are 1656x1000 PNGs from GT-207 / R304, 2026-09-02.
ROW_CENSUS_SCREENSHOTS = (
    (
        "evidence_screens/GT207_R304_gmui_window_open_tab1_basic_"
        "20260902_185434.png",
        "5c11c6298cf41038ebf94b896e3ad42ad338b281886808dcc41dc281cc6f7203",
    ),
    (
        "evidence_screens/GT207_R304_gmui_window_open_tab1_second_shot_"
        "20260902_185516.png",
        "1c3425433fa385cd7ba06773e51b939e0be74c487e9f44c0420493538beac5ea",
    ),
    (
        "evidence_screens/GT207_R304_gmui_tab2_ban_controls_"
        "20260902_190211.png",
        "034233bd0c5fae10cd16b177300ea786bd3b517c13758b54d982c85a3861133c",
    ),
    (
        "evidence_screens/GT207_R304_gmui_tab3_drop_buff_event_"
        "20260902_190450.png",
        "03cdb85467afb70739e1eed1ed7adba9a3371ee993c2248bd7002873d284bbbb",
    ),
)

#: The one place the two tab-1 shots do not settle the count.  See the
#: module docstring: 17 is a floor two shots agree on, not a ceiling.
PAGE_1_UNEXPLAINED_GAP = (
    "page 1 rows are ~40px apart except between row 5 (~y=525) and row 6 "
    "(~y=605), where ~80px is blank in BOTH tab-1 shots -- one row-height "
    "of layout with nothing drawn in it.  So the census counts what is "
    "DRAWN, and total_is_confirmed_on_screen() stays False until an "
    "attended pass rules out an undrawn widget there"
)

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
        "gm.forbid_to_talk_wire",
        "layout proven in external/PF_SERIALIZER_FIELDS.tsv rows 6283-6288 "
        "(tag 0x0B @+0x14, tag 0x14 @+0x18, tagged wstring @+0x1C, tag "
        "corrected to 0x48 by PF_A2_STRING_WIRE_TAG_DELTA.tsv rows "
        "6287/6288); not wired into runtime.py -- a mute/forbid-to-talk "
        "button still needs a call site before it could report anything",
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
        "gm.activity_cheat_code_wire",
        "layout proven in external/PF_SERIALIZER_FIELDS.tsv rows 4345-4356 "
        "(tag 0x14 @+0x14, five tagged wstrings, tag corrected to 0x48 by "
        "PF_A2_STRING_WIRE_TAG_DELTA.tsv rows 4347-4356); decode-only, no "
        "dispatch.py call site yet",
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


#: ~~EMPTY BY DECISION, NOT BY OVERSIGHT.  See the module docstring: filling
#: a row needs the client image, which no clone this lane runs on has.~~
#: Superseded in round `y1evqj`: the OPCODE half still needs the image, but
#: the ROW half did not -- `ROW_CENSUS_SCREENSHOTS` had been sitting in the
#: bridge since GT-207 (2026-09-02).  Built by `_row_census_buttons()` from
#: `data/gmui_widget_census.tsv`, one row per radio-selected function row,
#: every one of them `client_frame=None, handler_symbol=None`.
BUTTONS: tuple[ButtonRow, ...]

#: ~~Named so a test can pin it and a reader cannot mistake emptiness for
#: "there are no buttons".~~ Kept, with the half that is still true: what
#: the rows below still cannot say.
BUTTONS_ARE_UNFILLED_BECAUSE = (
    "the button->opcode mapping is only in the client image; this clone has "
    "no image, so client_frame is None on every row and no row claims a "
    "handler -- what the GT-207 screenshots bought is how many rows there "
    "are and what shape each one is, never what one sends"
)

#: What a row's `function` string says while its label is unread.  A slug is
#: a POSITION ("page 1, row 3"), not a name, and the two must not be allowed
#: to look alike in a round file.
FUNCTION_LABEL_UNREAD = "label unread on the GT-207 screenshots"

#: The two rows whose label starts with a latin token.  Still not a read
#: label: knowing a row is about NPCs is not knowing what it does to one.
FUNCTION_LABEL_PARTIAL = "label only partly read on the GT-207 screenshots"


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


@dataclass(frozen=True)
class RowCensusEntry:
    """One radio-selected function row, as a photograph can describe it.

    Everything here is a COUNT or a POSITION -- the two things a screenshot
    carries honestly.  `label_status` is `UNREAD` for fifteen of the
    seventeen rows and says so rather than carrying a guess.
    """

    page: int
    row: int
    slug: str
    option_radios: int
    text_inputs: int
    numeric_inputs: int
    anchor_y_approx: int
    label_status: str
    label_note: str

    @property
    def label_is_unread(self) -> bool:
        return self.label_status == "UNREAD"


#: The two `label_status` values the census uses.  `LATIN_PARTIAL` means a
#: latin token at the START of the label was legible and the Thai after it
#: was not -- it is NOT a read label, and `label_is_unread` deliberately
#: does not treat it as one being read either way in any count that matters.
LABEL_STATUS_UNREAD = "UNREAD"
LABEL_STATUS_LATIN_PARTIAL = "LATIN_PARTIAL"
LABEL_STATUSES = (LABEL_STATUS_UNREAD, LABEL_STATUS_LATIN_PARTIAL)


def _parse_census_line(line: str) -> RowCensusEntry:
    """One tsv line -> one entry, refusing anything it cannot account for.

    Split out from :func:`_load_row_census` so every refusal below is
    reachable from a test WITHOUT writing a bad row into the pinned file
    (which the pin would then reject first, hiding the refusal being
    tested).
    """
    columns = line.split("\t")
    if len(columns) != 9:
        raise GmuiCatalogError(
            f"gmui_widget_census.tsv row has {len(columns)} columns, "
            f"expected 9: {columns[0:3]!r}"
        )
    entry = RowCensusEntry(
        page=int(columns[0]),
        row=int(columns[1]),
        slug=columns[2],
        option_radios=int(columns[3]),
        text_inputs=int(columns[4]),
        numeric_inputs=int(columns[5]),
        anchor_y_approx=int(columns[6]),
        label_status=columns[7],
        label_note=columns[8],
    )
    if entry.label_status not in LABEL_STATUSES:
        raise GmuiCatalogError(
            f"row {entry.slug!r} has label_status {entry.label_status!r}, "
            f"expected one of {LABEL_STATUSES}"
        )
    if not 1 <= entry.page <= len(PAGES):
        raise GmuiCatalogError(
            f"row {entry.slug!r} names page {entry.page}, and there are "
            f"{len(PAGES)} pages"
        )
    return entry


def _load_row_census() -> tuple[RowCensusEntry, ...]:
    raw = _ROW_CENSUS_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != ROW_CENSUS_SHA256:
        raise GmuiCatalogError(
            f"gmui_widget_census.tsv has drifted from its pin: expected "
            f"{ROW_CENSUS_SHA256}, got {digest}"
        )
    return tuple(
        _parse_census_line(line)
        for line in raw.decode("utf-8").splitlines()[1:]
        if line.strip()
    )


ROW_CENSUS = _load_row_census()


def _row_census_buttons() -> tuple[ButtonRow, ...]:
    """One `ButtonRow` per censused row, claiming nothing but its shape.

    `client_frame` and `handler_symbol` are `None` on every row and this
    function has no parameter that could make them anything else -- the
    census is a photograph, and a photograph cannot name an opcode.
    """
    rows = []
    for entry in ROW_CENSUS:
        shape = (
            f"{entry.option_radios} option radios, {entry.text_inputs} text "
            f"inputs, {entry.numeric_inputs} numeric inputs"
        )
        label = (
            FUNCTION_LABEL_UNREAD
            if entry.label_is_unread
            else f"{FUNCTION_LABEL_PARTIAL} ({entry.label_note})"
        )
        rows.append(
            ButtonRow(
                page=PAGES[entry.page - 1],
                button=entry.slug,
                function=f"{label}; {shape}",
                client_frame=None,
                handler_symbol=None,
                owner="LANE-GM",
            )
        )
    return tuple(rows)


BUTTONS = _row_census_buttons()


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
    """True while nobody can say how many GMUI rows there are.

    `COO-DECISION 20260904_0245`: P-3 moves to "รอ Panya ติ๊ก" only when every
    button works, and that is uncountable while this is True.  A round file
    that writes "ปุ่ม x/y" while this is True is writing a number nothing
    backs.

    FALSE since round `y1evqj`.  Read it WITH
    :func:`total_is_confirmed_on_screen`, which is still False: the count
    exists, and it is a floor read off a photograph, not a confirmed
    ceiling.
    """
    return not BUTTONS


def total_is_confirmed_on_screen() -> bool:
    """True once an attended pass has confirmed the count AT the screen.

    Deliberately a hardcoded `False` and not a computation: the thing it
    reports is not a property of any table in this repository, it is whether
    a human has looked.  See :data:`PAGE_1_UNEXPLAINED_GAP` for the specific
    doubt, and the round `y1evqj` letter for the `ATTENDED:` block that
    would settle it.  A later round flips this in the same commit as the
    evidence, or not at all.
    """
    return False


def progress() -> tuple[int, int]:
    """`(rows whose handler exists, rows catalogued)`.

    `(0, 17)` today: seventeen GM functions across the three pages, none of
    which this server answers.  Read it with BOTH predicates above -- 0 of
    17 is a real number, and 17 is a floor.
    """
    return (sum(1 for row in BUTTONS if row.server_answers_today), len(BUTTONS))


for _row in BUTTONS:
    assert_backed(_row)
