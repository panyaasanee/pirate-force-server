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
models carrying a `GMUI_BASIC` tab; no `GMUI_BASIC.model` exists).

UPDATED round `nfbat1`, and the update is smaller than it looks: `RE-283`
(run on the owner's machine, where the image IS) named the other two tab
pages -- `GMUI_ADVAN` and `GMUI_ACTIVITY` -- so the "only one page is
named" sentence this docstring used to carry is retired, see `PAGES`.
What `RE-283` did NOT buy is the other half of `0245`'s table: it came
back PARTIAL at the one question that matters to a server, "what does a
button send", so every row below still carries no opcode.

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

~~It does NOT read the labels.  Every row's `label_status` is `UNREAD`
except two that begin with a latin token (`NPC` on page 1 row 3, `BUFF` on
page 3 row 2); the Thai is legible as Thai at this resolution but NOT
reliably legible as specific words, and a guessed label is exactly the row
this module's own guard exists to keep out.  Reading the 17 labels is one
attended pass at the screen, and the letter this round sends asks for it as
one `ATTENDED:` block rather than 17.~~

SUPERSEDED, round `dl1etn`: the labels are TEXT, in a table this house
committed weeks ago -- `pf_bridge/gamedata/tables/TEXTDATA_TH__UI_MESSAGE.tsv`
-- and most of the GMUI panel is a run of consecutive `n_ID` in it (see
:data:`GMUI_LABEL_BLOCK_ROLES`).  `data/gmui_label_block.tsv` is that run,
copied byte for byte the way `gm_tool_log_types.tsv` copies the GMTOOL
table, and every censused row now carries the `n_ID` of its own label.

WHAT THAT JOIN IS WORTH, AND EXACTLY WHERE IT STOPS.  ~~The run's shape and
the panel's shape agree row by row and cannot be made to agree any other
way.~~  FALSE, and `pf-adversary` (round `dl1etn`, D2) broke it by
construction rather than by argument: EIGHT of the seventeen rows carry the
IDENTICAL shape triple `(0 radios, 1 text input, 0 numeric)` -- p1r3, p1r4,
p1r5, p1r6, p1r7, p2r1, p2r2, p2r5 -- so shape cannot order them, and it
produced a rotated assignment among them that passes every test in this
module's suite.  (It counted seven; p1r3 has the same shape and is the one
of the eight anchored by something else -- its caption starts with the
latin token `NPC`.  Seven are left unordered by anything but the premise.)

So the claim has to be stated with its load-bearing half showing:

  * WHAT SHAPE PROVES: that this run, and no other run in the 188 committed
    tables, is THIS WINDOW's.  That part is strong and survived the attack.
    `X:` `Y:` `Z:` occur exactly once each in all 188 tables (1390/1391/1392)
    and sit on the one row of three pages that draws three numeric boxes;
    the parenthesised minutes suffix (1411) occurs exactly once and sits on
    the one row that draws one; every row the run gives two option strings
    to is a row the shots draw two radios on.
  * WHAT SHAPE DOES NOT PROVE: which row inside the run is which.  That
    rests entirely on :data:`ROW_ORDER_PREMISE` -- ascending `n_ID` is draw
    order -- which is an ASSUMPTION, is not measured anywhere, and is
    already known to be imperfect (1404 and 1405 are each consumed by two
    different rows, which a strict draw-order sequence would not do).

Do not read a row's `label_row_id` as a measured fact about that row.  Read
it as: this window's caption set is known, and the assignment inside it is
the ordering premise plus two rows that carry latin tokens (p1r3 `NPC`,
p3r2 `BUFF`) which are independently checkable on the shots.

THE ONE THING THE SCREENSHOTS AGREE ON AND STILL CANNOT SETTLE
---------------------------------------------------------------
Page 1's rows are evenly spaced ~40 px apart except between row 5 (~y=525)
and row 6 (~y=605), where there is an ~80 px gap -- one row-height of
nothing, in BOTH tab-1 shots.  That is the width of a widget that is
present in the layout and not drawn in this state.  ~~So 17 is a FLOOR that
two independent shots agree on, not a proven ceiling, and
:func:`total_is_confirmed_on_screen` stays False until an attended pass
says otherwise.~~  The attended pass ran (`GT-269`, `KA1A` round `R321`,
2026-09-06): a human counted 7/5/5 at the panel and reported the gap as
empty, so 17 is a confirmed count of DRAWN rows and that predicate is True
since round `vq07el`.  The half it did not buy is in
:data:`PAGE_1_GAP_ANSWERED` -- looking cannot rule out a widget that is in
the layout and not painted.  `PAGE_1_UNEXPLAINED_GAP` carries this in a constant so a
reader who greps rather than reads still meets it.  The label block adds a
CANDIDATE for what is not drawn there (`PAGE_1_GAP_CANDIDATE`) and does not
settle it: exactly one string of the page-1 run has no widget, and it falls
between the strings of row 5 and row 6.  That is a coincidence worth
writing down and NOT a measurement.  The first reason this lane gave for
keeping it a candidate (page 2 has an undrawn string and no gap) was
withdrawn in the same round after `pf-adversary` measured the axes -- read
the constant, not this paragraph, for what replaced it.

THE COUNT P-3 ASKED FOR
=======================
`progress()` returns `(closed, total)` for the rows -- `(0, 17)` today:
seventeen GM functions on three pages, none of which this server answers.
`total_is_unknown()` is now False (there IS a measured count) and
`total_is_confirmed_on_screen()` is now True as well (a human counted the
rows at the panel -- see the gap section above).  What replaced the old
caveat is a THIRD predicate: `labels_are_confirmed_on_screen()`, still
False, because the same attended pass read eight of the seventeen captions
as something other than the table row the census points them at
(`data/gmui_observed_labels.tsv`, `label_disagreements()`).  So a round may
now write "0 of 17" and "17 rows are drawn", and may not write "we know
what the 17 rows say".
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
_LABEL_BLOCK_PATH = Path(__file__).parent / "data" / "gmui_label_block.tsv"
_OBSERVED_LABELS_PATH = (
    Path(__file__).parent / "data" / "gmui_observed_labels.tsv"
)

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
    "5d0382c1aeb962d08fc6ee09baa4846363317f4be2b3f9eb2113f3b4afcd74c2"
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

#: The client text table the GMUI labels are IN, and its sha256 as this
#: house committed it.  This package never reads `pf_bridge` at runtime, so
#: the pin is the record (same posture as `ROW_CENSUS_SCREENSHOTS`): the
#: copy under `data/` is what the code loads, and this constant is how a
#: later round proves the copy still comes from the same source file.
LABEL_SOURCE_TABLE = "gamedata/tables/TEXTDATA_TH__UI_MESSAGE.tsv"
LABEL_SOURCE_TABLE_SHA256 = (
    "2d97ff4836955e72bcebff2fcda4c1e703df880b8490d241624df20c34efa2c1"
)

#: sha256 of this package's copy of the GMUI slice of that table.  Checked
#: at import time, same as `SOURCE_SHA256`.
LABEL_BLOCK_SHA256 = (
    "6e86ea1107ab9408a11d874cc6d80aab3131e81bd1ce27f2cdbe410758c2992f"
)

#: sha256 of what an attended pass read OFF THE SCREEN, pinned the same way
#: and for a sharper reason than the two above: the block and the census are
#: derived from committed artifacts and can be re-derived, while this file
#: is a transcription of somebody's eyes on a photograph and can never be
#: re-derived from anything in this repository.  An edit to it is an edit to
#: the only copy of the evidence.
OBSERVED_LABELS_SHA256 = (
    "5152e1d763274115e8f6ab1c877f969810fc3dd39c54f8222387860d870e797c"
)

#: Where that transcription came from, named so a reader can go back to it.
#: `GT-269` ran in `KA1A` round `R321`; the labels are section 5 of
#: `pf_bridge/notes_to_chief/20260906_1255_KA1A-R321-RESULTS-faction-missing-
#: on-126-login-RE272-lv-GT217-269-queue-stale.md`, read by `ka1-A` off
#: three photographs and confirmed afterwards by the owner.
OBSERVED_LABELS_SOURCE = (
    "GT-269 PASS-CLIENT, KA1A round R321, 2026-09-06 12:4x +07:00; "
    "notes_to_chief/20260906_1255_KA1A-R321-RESULTS-*.md section 5"
)

#: What each `n_ID` in the copied block is, on the panel.  THIS DICT IS THE
#: CLAIM -- the tsv beside it is only the client's own text.  A role of
#: `undrawn` means the string is inside the run and no widget on the shot
#: carries it; `.label` means it is the caption of a censused row and is the
#: only role a census row's `label_row_id` is allowed to point at.
GMUI_LABEL_BLOCK_ROLES = {
    1386: "page1.row1.label",
    1387: "page1.row1.option_a",
    1388: "page1.row1.option_b",
    1389: "page1.row2.label",
    1390: "page1.row2.axis_x",
    1391: "page1.row2.axis_y",
    1392: "page1.row2.axis_z",
    1393: "page1.row3.label",
    1394: "page1.row4.label",
    1395: "page1.row5.label",
    1396: "undrawn",
    1397: "page1.row6.label",
    1398: "page1.row7.label",
    1399: "page2.row1.label",
    1400: "page2.row2.label",
    1401: "page2.row3.label",
    1402: "page2.row3.option_a",
    1403: "undrawn",
    1404: "page2.row3.option_b+page2.row4.option_b",
    1405: "page2.row3.duration_caption+page2.row4.duration_caption",
    1406: "page2.row3.duration_unit",
    1407: "page2.row4.label",
    1408: "page2.row4.option_a",
    1409: "page2.row4.name_caption",
    1410: "page2.row4.reason_caption",
    1411: "page2.row4.duration_unit",
    1412: "page2.row5.label",
    1413: "action_button.all_pages",
    1671: "page3.row3.label",
    1439: "page1.tab_title",
    1440: "page2.tab_title",
    1891: "page3.tab_title",
    1892: "page3.row1.label",
    1893: "page3.row1.inline_caption",
    1894: "page3.row2.label",
    1895: "page3.row4.label",
    1896: "page3.row5.label",
}

#: THE ASSUMPTION THE ROW-BY-ROW ASSIGNMENT RESTS ON, named so it can be
#: attacked instead of inherited.  Nothing in this package measures it.
ROW_ORDER_PREMISE = (
    "ascending n_ID inside the run is the order the client draws the rows.  "
    "NOT MEASURED.  It is the only thing separating the seven rows that "
    "share the shape (0 radios, 1 text input, 0 numeric), and it is already "
    "imperfect: 1404 and 1405 are each consumed by two different rows, which "
    "a strict draw-order sequence would not do.  An attended pass that reads "
    "any ONE of p1r4/p1r5/p1r6/p1r7/p2r1/p2r2/p2r5 off the screen settles "
    "far more than another table read can"
)

#: Rows of the run that no widget on any of the four shots carries.
#: 1403 is the weaker of the two: it is a full row-caption-shaped sentence
#: with the same grammar as 1401 and 1407, and page 2 row 3 draws a
#: full-width text input whose caption this run does not otherwise account
#: for -- so "1403 captions that input" is a live competing reading that
#: this lane has NOT excluded.  Recorded here rather than buried, because
#: calling it undrawn is a choice.
UNDRAWN_BLOCK_ROWS = (1396, 1403)

#: The one page-1 row the census cannot see, if the gap is a row at all.
#: [LANE-GM HYPOTHESIS -- awaiting COO or an attended pass]
#:
#: ~~Why it is not more than that: page 2's run ALSO carries an undrawn
#: string (1403) and page 2 has NO gap of any size, so an undrawn string
#: demonstrably does not have to reserve layout space in this client.~~
#: WITHDRAWN as stated -- `pf-adversary` (D8) measured the axes and the
#: sentence crosses them: 1403 is claimed to be a radio OPTION, which would
#: occupy horizontal flow inside a row, while the page-1 gap is a VERTICAL
#: row slot (measured at exactly 2 x 40.0 px against a 40 px pitch, in both
#: tab-1 shots).  Option radios are laid out left-anchored with no reserved
#: horizontal slots, which is a real measurement and says nothing about
#: whether an undrawn ROW reserves a vertical one.
#:
#: The conclusion is unchanged and now rests on the honest reason: nothing
#: in any committed artifact says what an undrawn row does to this client's
#: vertical layout, so 1396 is one story that fits and not the only one.
#: Settling it is an attended question, which is why
#: `total_is_confirmed_on_screen()` does not move.
PAGE_1_GAP_CANDIDATE = 1396

#: The one place the two tab-1 shots do not settle the count.  See the
#: module docstring: 17 is a floor two shots agree on, not a ceiling.
PAGE_1_UNEXPLAINED_GAP = (
    "page 1 rows are ~40px apart except between row 5 (~y=525) and row 6 "
    "(~y=605), where ~80px is blank in BOTH tab-1 shots -- one row-height "
    "of layout with nothing drawn in it.  So the census counts what is "
    "DRAWN, and total_is_confirmed_on_screen() stays False until an "
    "attended pass rules out an undrawn widget there"
)

#: What that attended pass actually answered (`GT-269`, `KA1A` round `R321`,
#: 2026-09-06).  Kept beside the doubt it answers rather than replacing it,
#: because the doubt is still half-standing and a reader who meets only the
#: answer would not know which half.
#:
#: ANSWERED: nothing is drawn in the gap.  A human looked at the panel and
#: reported the space as empty, so the census counts every row the client
#: paints and 17 is a confirmed count of DRAWN rows, not a floor.
#:
#: NOT ANSWERED, AND NOT ANSWERABLE BY LOOKING: whether a widget exists in
#: the layout and is not painted.  `PAGE_1_GAP_CANDIDATE` (1396) remains one
#: story that fits an empty row-height of layout, and the eight
#: `DISAGREES` rows in `gmui_observed_labels.tsv` -- five of them on page 1,
#: the same run 1396 belongs to -- are a second reason not to bank it.
PAGE_1_GAP_ANSWERED = (
    "GT-269 attended pass (KA1A round R321, 2026-09-06 12:4x +07:00): the "
    "page 1 gap has NO VISIBLE WIDGET, so 17 is a confirmed count of drawn "
    "rows; whether an undrawn row occupies the layout there is a different "
    "question and looking cannot settle it"
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

#: All three page names, each one the client's own `UITabPage` ID.  The two
#: that used to be `UNNAMED_PAGE_2`/`UNNAMED_PAGE_3` placeholders were
#: answered by `RE-283` (result letter
#: `pf_bridge/notes_to_chief/20260906_2328_RE-283-RESULT-PARTIAL-three-pages-53-widgets-and-the-execute-path.md`,
#: consumed round `nfbat1`): the RE runner opened `GMUI_1.model` on the
#: owner's machine and found ONE `UITabControl` holding exactly three
#: `UITabPage` children.  There is no `GMUI_ADVAN.model` or
#: `GMUI_ACTIVITY.model` for the same reason there is no
#: `GMUI_BASIC.model` -- a tab page is not a model of its own, which is
#: what made the older drafts read the absence of those files as "the
#: names are unknown".
PAGE_KNOWN = "GMUI_BASIC"
PAGE_2 = "GMUI_ADVAN"
PAGE_3 = "GMUI_ACTIVITY"
PAGES = (PAGE_KNOWN, PAGE_2, PAGE_3)

#: Where the two new names come from, pinned so a later round can re-check
#: them instead of trusting this module.  The letter carries the sha256 of
#: every input it read; this is the one that carries the tab pages.
PAGE_NAME_PROVENANCE = (
    "GameClient/Data/GUI/Model/GMUI_1.model sha256 "
    "ffd7e5d1c44ffe36b5bacc2857aa049ae6cbea69e11f62541bd0632162bbc69f "
    "(25,434 B), read by the RE runner for RE-283 on the owner's machine; "
    "no clone this lane runs on holds the file"
)

#: The tab-strip caption row each page carries, in page order -- the same
#: three ids `PAGE_TITLE_ROW_IDS` already held as an unordered set, now
#: attached to the page each belongs to.  This is the independent check
#: that the RE result and this module's earlier screenshot census are
#: talking about the same three pages: the ids matched with nothing
#: coordinating them.  A caption is still NOT a model name (page 2's
#: caption disagrees with page 2's content -- see
#: `PAGE_2_TITLE_DOES_NOT_MATCH_ITS_CONTENT`), so the two stay separate
#: fields of the same row rather than one field doing both jobs.
PAGE_CAPTION_ROW_BY_PAGE = {
    PAGE_KNOWN: 1439,
    PAGE_2: 1440,
    PAGE_3: 1891,
}

#: Where each page's `UITabPage` pointer is stashed on the window object,
#: and where the one confirm button outside the tabs is.  `RE-283` read
#: these off the binder at `0x00726DF0..0x00727A56`; they are of no use to
#: this server (it never touches client memory) and are kept only so a
#: later RE round does not have to re-derive them to continue the one
#: question RE-283 left open.
PAGE_MEMBER_OFFSETS = {PAGE_KNOWN: 0x14, PAGE_2: 0x68, PAGE_3: 0xB0}
CONFIRM_BUTTON_MEMBER_OFFSET = 0xE8
CONFIRM_BUTTON_WIDGET_ID = "BUTTON_OK"

#: What is settled about the three pages and what is still open, in the
#: record rather than in a reviewer's memory.  The names are settled.  What
#: a button SENDS is not: RE-283 came back PARTIAL, having proved the
#: dispatcher builds one text command plus a number plus flags into a
#: single object (`[ebx+0x14]`/`[ebx+0x18]`/`[ebx+0x1c]`, the cheat-code
#: branch requiring a literal '/' first character) but NOT having walked
#: that object to the send site -- so no row in this module may carry an
#: opcode yet, `0x51E9` included.
PAGES_NOTE = (
    "three pages per PANYA-DECISION 20260904_0233 item 3 (the owner has seen "
    "them); all three are now named by the client's own GMUI_1.model via "
    "RE-283, one UITabControl with three UITabPage children.  What each "
    "button SENDS is still open: RE-283 is PARTIAL and stops at the object "
    "the dispatcher fills, one step short of the send site"
)

#: The words on the tab strip, by `n_ID` in the copied block -- the caption
#: a human reads, not the model name above.  All three are TABLE_EXACT and
#: all three are corroborated by the tab strip of the tab-1 shot.
PAGE_TITLE_ROW_IDS = (1439, 1440, 1891)

#: Said in a constant because it is the single most misreadable thing the
#: block turned up: page 2's TAB CAPTION and page 2's CONTENT do not agree.
#: The caption is an advancement/levelling word; the widgets under it are
#: mob spawn, mob kill, two chat-ban blocks and a raw command box.  That is
#: the client's own naming and this lane does not get to tidy it -- a round
#: that reads the caption and infers what page 2 does will be wrong.
PAGE_2_TITLE_DOES_NOT_MATCH_ITS_CONTENT = (
    "block row 1440 captions page 2 and its content is unrelated to that "
    "caption; use the row labels (1399..1412), never the tab title, to say "
    "what page 2 does"
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
        "PF_A2_STRING_WIRE_TAG_DELTA.tsv rows 4347-4356); ~~decode-only, no "
        "dispatch.py call site yet~~ round eu2g1d: gm.dispatch."
        "handle_activity_cheat_code_vital authorizes and captures it, the "
        "same gate 0x51E9 gets -- STILL NO runtime.py call site (chief's "
        "edit, CORE-REQUEST-GM-062) and still nothing answered back",
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

#: ~~What a row's `function` string says while its label is unread.~~
#: Retired with `LABEL_STATUS_UNREAD` in round `dl1etn`.  The names are kept
#: so a grep for either still lands on this block and reads why.
FUNCTION_LABEL_UNREAD = "RETIRED round dl1etn -- see FUNCTION_LABEL_FROM_TABLE"
FUNCTION_LABEL_PARTIAL = FUNCTION_LABEL_UNREAD

#: What a row's `function` string says once its caption is a table row.  It
#: names the `n_ID` and NOT the words: the words are Thai, they belong in
#: `data/gmui_label_block.tsv` where the client put them, and a caller that
#: wants them calls :func:`label_text`.  A `function` string that carried
#: the words would let a round file quote a label it never joined to a row.
FUNCTION_LABEL_FROM_TABLE = "label is client text table row"

#: What the one row with no table row says.  Still not a name -- the shot
#: shows Thai there and nothing this house committed spells it.
FUNCTION_LABEL_SCREENSHOT_ONLY = (
    "label visible on the GT-207 screenshots and not found in any committed "
    "table by this lane -- NO ROW IS IN THIS STATE TODAY.  The one that was "
    "(page 3 row 3) had its caption at n_ID 1671, 258 ids outside the run, "
    "and this lane's search had only looked inside the run; `pf-adversary` "
    "found it by rendered glyph width.  Treat this status as 'not found "
    "YET', never as 'absent'"
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
    #: `n_ID` of this row's caption in `data/gmui_label_block.tsv`, or `0`
    #: when no committed table carries the label at all.
    label_row_id: int
    label_note: str

    @property
    def label_has_no_table_row(self) -> bool:
        """True when no committed table spells this row's caption.

        ~~`label_is_unread`~~ -- renamed in round `dl1etn` after
        `pf-adversary` (D9) showed the old name had inverted: the one row
        that was `SCREENSHOT_ONLY` was the only row a human had actually
        READ, and the sixteen it called read were the ones nobody had.
        Zero rows are in this state today; the property and its status stay
        because the next window censused this way will have some.
        """
        return self.label_status != LABEL_STATUS_TABLE_EXACT


#: The two `label_status` values the census uses.  ~~`UNREAD` /
#: `LATIN_PARTIAL`~~ -- both retired in round `dl1etn`, when the labels
#: turned out to be text in a committed table rather than pixels to squint
#: at.  `TABLE_EXACT` means the caption is a row of `gmui_label_block.tsv`
#: AND the row's widget shape agrees with what that run of strings implies.
#: `SCREENSHOT_ONLY` means the shot shows a caption there and NO committed
#: table spells it -- one row on page 3 -- and that row keeps
#: `label_row_id = 0` and stays out of every count of read labels.
LABEL_STATUS_TABLE_EXACT = "TABLE_EXACT"
LABEL_STATUS_SCREENSHOT_ONLY = "SCREENSHOT_ONLY"
LABEL_STATUSES = (LABEL_STATUS_TABLE_EXACT, LABEL_STATUS_SCREENSHOT_ONLY)


def _load_label_block() -> dict[int, str]:
    """`n_ID -> s_UI_WORDS` for the GMUI run, from this package's own copy.

    The copy is byte-pinned exactly like `gm_tool_log_types.tsv`: this
    package never reads `pf_bridge` at runtime, so a silent edit to the copy
    has to fail loudly or the pin buys nothing.
    """
    raw = _LABEL_BLOCK_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != LABEL_BLOCK_SHA256:
        raise GmuiCatalogError(
            f"gmui_label_block.tsv has drifted from its pinned source: "
            f"expected {LABEL_BLOCK_SHA256}, got {digest}"
        )
    block: dict[int, str] = {}
    for line in raw.decode("utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        n_id, _, words = line.partition("\t")
        block[int(n_id)] = words
    missing = sorted(set(GMUI_LABEL_BLOCK_ROLES) - set(block))
    if missing:
        raise GmuiCatalogError(
            f"GMUI_LABEL_BLOCK_ROLES names rows the copied block does not "
            f"carry: {missing} -- the roles are a claim ABOUT the block and "
            "may not outrun it"
        )
    unroled = sorted(set(block) - set(GMUI_LABEL_BLOCK_ROLES))
    if unroled:
        raise GmuiCatalogError(
            f"gmui_label_block.tsv carries rows with no role: {unroled} -- a "
            "string copied into this package without a stated place on the "
            "panel is a guess waiting to be read as evidence"
        )
    return block


LABEL_BLOCK = _load_label_block()


def _assert_label_row_id_is_backed(entry: RowCensusEntry) -> None:
    """Refuse a census row whose `label_row_id` is not a caption.

    Same shape of guard as :func:`assert_backed`, for the same reason: the
    cheap way to look like P-3 moved is to point a row at a plausible
    `n_ID`.  A row may only point at a block row whose role ENDS in
    `.label`, and a `SCREENSHOT_ONLY` row may not point anywhere at all.
    """
    if entry.label_status == LABEL_STATUS_SCREENSHOT_ONLY:
        if entry.label_row_id != 0:
            raise GmuiCatalogError(
                f"row {entry.slug!r} is {LABEL_STATUS_SCREENSHOT_ONLY} and "
                f"still names block row {entry.label_row_id} -- a label no "
                "committed table spells cannot have a table row id"
            )
        return
    role = GMUI_LABEL_BLOCK_ROLES.get(entry.label_row_id)
    if role is None:
        raise GmuiCatalogError(
            f"row {entry.slug!r} names block row {entry.label_row_id}, which "
            "is not in the copied GMUI block"
        )
    if not role.endswith(".label"):
        raise GmuiCatalogError(
            f"row {entry.slug!r} names block row {entry.label_row_id}, whose "
            f"role is {role!r} -- a census row's caption may only be a "
            "`.label` role, never an option text, a unit suffix or a tab "
            "title"
        )
    expected = f"page{entry.page}.row{entry.row}.label"
    if role != expected:
        raise GmuiCatalogError(
            f"row {entry.slug!r} names block row {entry.label_row_id} whose "
            f"role is {role!r}, but the row sits at {expected!r} -- the "
            "census and the roles disagree about where this caption is"
        )


def _parse_census_line(line: str) -> RowCensusEntry:
    """One tsv line -> one entry, refusing anything it cannot account for.

    Split out from :func:`_load_row_census` so every refusal below is
    reachable from a test WITHOUT writing a bad row into the pinned file
    (which the pin would then reject first, hiding the refusal being
    tested).
    """
    columns = line.split("\t")
    if len(columns) != 10:
        raise GmuiCatalogError(
            f"gmui_widget_census.tsv row has {len(columns)} columns, "
            f"expected 10: {columns[0:3]!r}"
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
        label_row_id=int(columns[8]),
        label_note=columns[9],
    )
    if entry.label_status not in LABEL_STATUSES:
        raise GmuiCatalogError(
            f"row {entry.slug!r} has label_status {entry.label_status!r}, "
            f"expected one of {LABEL_STATUSES}"
        )
    _assert_label_row_id_is_backed(entry)
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


#: The three verdicts a transcribed label can carry against the table row
#: the census points the same row at.  There is deliberately no fourth value
#: meaning "close enough": every row here is either the same caption, a
#: different caption, or a reading the observer themself called unclear.
AGREEMENT_AGREES = "AGREES"
AGREEMENT_DISAGREES = "DISAGREES"
AGREEMENT_UNCERTAIN = "UNCERTAIN"
AGREEMENTS = (AGREEMENT_AGREES, AGREEMENT_DISAGREES, AGREEMENT_UNCERTAIN)


@dataclass(frozen=True)
class ObservedLabel:
    """One row's caption AS A HUMAN READ IT ON THE SCREEN.

    This is the second evidence layer for the census, and it is a layer the
    house rules keep separate on purpose: `label_row_id` says which row of
    the client's own text table this house BELIEVES the caption is, and
    `observed_text` says what somebody saw.  Neither is allowed to be read
    as the other, which is exactly why a `DISAGREES` row does not edit the
    census: nothing here outranks a committed table, and nothing in a
    committed table outranks a photograph.  A disagreement is a question,
    and :func:`label_disagreements` is where it stays until an attended pass
    answers it.
    """

    page: int
    row: int
    agreement: str
    observed_text: str
    note: str

    @property
    def contradicts_the_table(self) -> bool:
        return self.agreement == AGREEMENT_DISAGREES


def _parse_observed_line(line: str) -> ObservedLabel:
    """One tsv line -> one entry, refusing anything it cannot account for.

    Split out from :func:`_load_observed_labels` for the same reason
    :func:`_parse_census_line` is: every refusal below stays reachable from
    a test without writing a bad row into the pinned file, which the pin
    would reject first and hide the refusal being tested.

    NOTE ON MESSAGES.  No refusal here prints `observed_text`.  The house
    console is cp874 and these strings are Thai read off a screenshot; a
    tool that dies while reporting a bad row is worse than the bad row.
    Page and row identify a line unambiguously anyway.
    """
    columns = line.split("\t")
    if len(columns) != 5:
        raise GmuiCatalogError(
            f"gmui_observed_labels.tsv row has {len(columns)} columns, "
            f"expected 5: {columns[0:2]!r}"
        )
    entry = ObservedLabel(
        page=int(columns[0]),
        row=int(columns[1]),
        agreement=columns[2],
        observed_text=columns[3],
        note=columns[4],
    )
    if entry.agreement not in AGREEMENTS:
        raise GmuiCatalogError(
            f"observed label at page {entry.page} row {entry.row} has "
            f"agreement {entry.agreement!r}, expected one of {AGREEMENTS}"
        )
    if not entry.observed_text.strip():
        raise GmuiCatalogError(
            f"observed label at page {entry.page} row {entry.row} carries no "
            "text -- a row nobody could read is not an observation, it is an "
            "absence, and belongs outside this file"
        )
    if not entry.note.strip():
        raise GmuiCatalogError(
            f"observed label at page {entry.page} row {entry.row} carries no "
            "note -- the note is where the reading is compared to the table "
            "row the census names, and a verdict with no comparison behind "
            "it is a claim"
        )
    return entry


def _load_observed_labels() -> tuple[ObservedLabel, ...]:
    """Every censused row's on-screen reading, or an import-time failure.

    Pinned and total, both by construction.  TOTAL matters more than it
    looks: a file that may cover a subset would let a later round quietly
    delete the rows that disagree and leave a green suite behind, which is
    the exact failure this whole module is built against.
    """
    raw = _OBSERVED_LABELS_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != OBSERVED_LABELS_SHA256:
        raise GmuiCatalogError(
            f"gmui_observed_labels.tsv has drifted from its pin: expected "
            f"{OBSERVED_LABELS_SHA256}, got {digest}"
        )
    entries = tuple(
        _parse_observed_line(line)
        for line in raw.decode("utf-8").splitlines()[1:]
        if line.strip()
    )
    seen = [(entry.page, entry.row) for entry in entries]
    duplicated = sorted({key for key in seen if seen.count(key) > 1})
    if duplicated:
        raise GmuiCatalogError(
            f"gmui_observed_labels.tsv reads the same row twice: {duplicated}"
        )
    censused = {(entry.page, entry.row) for entry in ROW_CENSUS}
    unknown = sorted(set(seen) - censused)
    if unknown:
        raise GmuiCatalogError(
            f"gmui_observed_labels.tsv reads rows the census does not carry: "
            f"{unknown} -- an observation of a row nobody counted cannot be "
            "compared to anything"
        )
    unread = sorted(censused - set(seen))
    if unread:
        raise GmuiCatalogError(
            f"gmui_observed_labels.tsv is missing censused rows: {unread} -- "
            "this file is total over the census on purpose, so that dropping "
            "an inconvenient reading breaks the import instead of the record"
        )
    return entries


OBSERVED_LABELS = _load_observed_labels()


def observed_label(page: int, row: int) -> ObservedLabel:
    """The on-screen reading of one censused row."""
    for entry in OBSERVED_LABELS:
        if entry.page == page and entry.row == row:
            return entry
    raise GmuiCatalogError(
        f"no observed label for page {page} row {row}"
    )


def label_disagreements() -> tuple[ObservedLabel, ...]:
    """Rows where the screen and the table do not say the same thing.

    Eight of seventeen today, five of them on page 1.  Read the note on
    :func:`labels_are_confirmed_on_screen` before treating that as a finding
    about the table: the far likelier reading is that the transcription is a
    paraphrase, and this house cannot tell the two apart from the cloud.
    """
    return tuple(entry for entry in OBSERVED_LABELS if entry.contradicts_the_table)


def labels_are_confirmed_on_screen() -> bool:
    """True only once every censused row's caption reads the same both ways.

    FALSE today, and the reason is worth stating rather than assuming.  The
    eight `DISAGREES` rows have TWO possible causes and this house cannot
    choose between them without another attended pass:

    * the transcription is a paraphrase.  Most likely.  The readings were
      taken off photographs, and several differ from the table only in one
      token (``ที่นี่`` for ``ที่บิน``, ``ตัวบุคคล`` for ``ตัวละคร``).
    * the census points page 1 at the wrong id run.  Five of the seven page
      1 rows disagree, which is a suspicious place for random transcription
      noise to land -- and `PAGE_1_GAP_CANDIDATE` (1396) is a row of exactly
      that run, so if the run is wrong the gap story is wrong with it.

    A grep of every committed `gamedata/tables/*.tsv` for the observed page 1
    strings (``ฉากที่นี่``, ``ล็อกผู้เล่น``, ``ฆ่าผู้เล่น``) as a UI caption
    returns nothing -- round `vq07el` ran it -- which argues for the first
    cause, since a wrong-run reading would have to be SOME row somewhere.
    It is not proof: absence in the copied tables is not absence in the
    client.  So this stays False and the question goes to the screen.
    """
    return not label_disagreements()


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
            FUNCTION_LABEL_SCREENSHOT_ONLY
            if entry.label_has_no_table_row
            else f"{FUNCTION_LABEL_FROM_TABLE} n_ID {entry.label_row_id}"
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


def label_text(row_id: int) -> str:
    """The client's own words for one block row.

    Raises rather than returning a placeholder for an id the block does not
    carry: a caller that gets `""` back writes a report with a blank where a
    label should be, and nobody notices.
    """
    try:
        return LABEL_BLOCK[row_id]
    except KeyError:
        raise GmuiCatalogError(
            f"n_ID {row_id} is not in the copied GMUI label block"
        ) from None


def page_titles() -> tuple[tuple[int, str], ...]:
    """`(n_ID, words)` for the three tab captions, page order.

    Read it with :data:`PAGE_2_TITLE_DOES_NOT_MATCH_ITS_CONTENT`: page 2's
    caption is about levelling and its widgets are not.
    """
    return tuple((row_id, LABEL_BLOCK[row_id]) for row_id in PAGE_TITLE_ROW_IDS)


def rows_with_a_read_label() -> tuple[RowCensusEntry, ...]:
    """Census rows whose caption is a row of the copied block.

    Sixteen of seventeen today.  This is a LABEL count and says nothing at
    all about whether the server answers any of them -- that is
    :func:`progress`, which is still `(0, 17)` and is the number P-3 is
    graded on.
    """
    return tuple(
        entry
        for entry in ROW_CENSUS
        if entry.label_status == LABEL_STATUS_TABLE_EXACT
    )


def labels_are_read() -> tuple[int, int]:
    """`(rows whose caption is a committed table row, rows catalogued)`."""
    return (len(rows_with_a_read_label()), len(ROW_CENSUS))


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

    TRUE since round `vq07el`, flipped in the same commit as the evidence it
    rests on, which is the condition the previous revision of this docstring
    set: `GT-269` ran attended in `KA1A` round `R321` and a human counted
    7 / 5 / 5 off three photographs -- the census's own numbers, arrived at
    independently -- and answered the page 1 gap: nothing is DRAWN there.
    See :data:`PAGE_1_GAP_ANSWERED`.

    STILL A HARDCODED CONSTANT, not a computation, for the same reason it
    was one while it was False: what it reports is whether a human looked,
    and no table in this repository knows that.

    WHAT IT DOES NOT SAY.  It says the COUNT of drawn rows is confirmed.  It
    says nothing about whether the captions are right --
    :func:`labels_are_confirmed_on_screen` is the predicate for that and is
    still False -- and nothing about an undrawn widget occupying the gap,
    which no amount of looking can rule in or out.
    """
    return True


def progress() -> tuple[int, int]:
    """`(rows whose handler exists, rows catalogued)`.

    `(0, 17)` today: seventeen GM functions across the three pages, none of
    which this server answers.  Read it with BOTH predicates above -- 0 of
    17 is a real number, and 17 is a floor.
    """
    return (sum(1 for row in BUTTONS if row.server_answers_today), len(BUTTONS))


for _row in BUTTONS:
    assert_backed(_row)
