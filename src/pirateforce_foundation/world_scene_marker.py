"""Where a scene's own developer said a character arrives - LANE-A, M2.

WHAT THIS MODULE IS FOR, IN ONE SENTENCE.  Every destination this project has
ever pinned needed an arrival point, and each one was argued from scratch -
scene 1 took the runtime's historical spawn, scene 2 took a point a live
client had been stood on, scene 278 took a monster placement because it was
the only authored coordinate in the file, and scene 17 took an owner decree
because it had nothing at all.  Four scenes, four different rules; this module
is the fifth answer written down once, as a table lookup, so the sixth scene
is not a fresh argument: a ``MARKER`` row per scene, with an XYZ and a facing,
authored by the people who built the map.

    THIS MODULE IS NOT THE PROJECT'S FIRST CONTACT WITH THAT TABLE, AND THE
    FIRST DRAFT OF THIS DOCSTRING CLAIMED IT WAS.  "The client's own tables
    carry a fifth answer that none of those rounds read" was written here and
    refuted by pf-adversary (round vyi2ud, D4) out of artifacts already in
    this repository.  What was already here, before this file existed:
    ``scenarios/scene2_load_only.json`` is named ``scene2_load_only_marker2``
    and carries ``coordinate_provenance: scene2_marker2`` (and declines the
    facing: ``direction8_unmapped_constructor_zero``);
    ``docs/EXPERIMENT_LEDGER.md`` records that run as a runtime pass; and
    ``reports/PF_RE_V137_MARKER1_TeleportVital_Transport_Pass_20260815.md``
    -- two weeks before this round -- transported a VISIBLE CLIENT to
    ``MARKER[1]`` with one TeleportVital, watched its coordinate UI read
    ``X:-10322 Y:-755``, and is the evidence behind
    ``docs/FUNCTIONAL_COVERAGE.json``'s ``teleport_transport`` =
    ``runtime_pass``.  So the honest framing is the opposite of the one this
    file opened with: the table is not unread, it is UNCOLLECTED - three
    rounds used single rows of it and nobody wrote the crosswalk down.  That
    is what this module adds, and it is a smaller claim than the one it
    replaces.

THE CROSSWALK, AND IT IS NOT "THE MARKER ID IS THE SCENE ID".
``SCENE_NAME[n_ID].n_MARKER`` -> ``MARKER[n_ID]`` -> ``(n_SCENE, n_X, n_Y,
n_Z, n_DIRTECTION)``, and the row is only accepted when its ``n_SCENE`` points
back at the scene that named it.  The tempting shortcut - read the scene id as
a marker id - is measured WRONG here: of ``MARKER``'s 390 rows only 19 carry
``n_ID == n_SCENE``, and scene 130 (``Bg4001``) names marker **1000**.  A
future round that skips the table and indexes by scene id would put one map's
arrival point in another map.

HOW MANY SCENES THIS ANSWERS FOR, MEASURED RATHER THAN HOPED.  Of the client's
271 registered scenes, exactly **13** carry a non-zero ``n_MARKER``: scenes
1-11, 14 and 130.  All 13 resolve, and all 13 point back at their own scene -
13/13, no mismatch, no dangling id.  The other 258 scenes, scene 17 among
them, have ``n_MARKER = 0`` and this module returns ``None`` for every one of
them.  That is the answer, not a gap in the reader: ``RE-103`` searched the
sea scenes for an arrival datum and closed bounded-negative, and this is the
same negative arriving from the table that WOULD have carried it.  The owner's
provisional decree for scene 17 stays the only source for that scene.

WHAT THE CLIENT HAS ACTUALLY DONE WITH A MARKER POINT - AND THE CIRCULARITY
THIS PARAGRAPH USED TO BE.  The first draft argued that ``MARKER[2]`` being
byte-for-byte the scene-2 spawn in ``world_scene_registry_001.json`` was an
independent measurement agreeing with the table.  It is not: that spawn CAME
from marker 2 (``scenarios/scene2_load_only.json``'s own
``coordinate_provenance``), so the table was agreeing with itself and the
agreement was being re-presented one layer up as client-observable proof
(pf-adversary, round vyi2ud, D5).  The weaker claim that survives is still the
useful one:

* **The client has ACCEPTED marker points twice.**  V137 teleported a visible
  client to ``MARKER[1]`` and the client's own coordinate UI reported the
  marker's X and Y (``reports/PF_RE_V137_MARKER1_TeleportVital_Transport_
  Pass_20260815.md``, ``FUNCTIONAL_COVERAGE.json`` ``teleport_transport`` =
  ``runtime_pass``), and ``SCENE-001`` stood a client on ``MARKER[2]``.  "The
  client accepts a marker coordinate" is measured.  "A marker is where the
  original game puts an arriving player" is NOT, and nothing here may be
  quoted for it.
* **Home does not match, and the difference is stated rather than smoothed.**
  ``MARKER[1]`` is ``(-10322, -755, 671)``; the spawn this runtime actually
  stands a fresh character on is V135's ``(-9239.96, -2830.05, 223.29)``,
  **2340.22 units away in XY and 2382.66 in three dimensions** (per axis
  1082.04 / 2075.05 / 447.71 - the same gap ``runtime.py:3764`` already
  describes as "about 2340 units away horizontally and 448 vertically"; this
  file first said "about 2200", which matched neither, D10).  Both points are
  real: the marker is the client table's authored point, V135's is this
  server's own historical choice, and NOTHING here proposes changing home.

~~[LANE-A ASSUMPTION - AWAITING COO CONFIRMATION]  That a scene's MARKER row
is the right place to stand an arriving character is this lane's reading, not
a ruling: the letter asking for it is
``pf_bridge/notes_to_chief/20260829_0447_LANE-A-ASK-COO-marker-table-as-
default-spawn.md``, and it names what to revert if the answer is no (one row
out of the scene registry).~~  ANSWERED, and the assumption label is struck
rather than deleted so the reading can still be told from the ruling that
followed it.

THE RULE, AS RULED.  ``COO-DECISION 20260829_0542`` (mailbox
``pf_bridge/notes_to_chief/20260829_0542_COO-DECISION-marker-table-is-the-
default-spawn-source-with-an-evidence-label.md``) accepted option 1 as a
STANDING rule of the project, in three parts, and this module is where two of
them are executable:

1. **A scene whose ``SCENE_NAME[n].n_MARKER != 0`` takes ``MARKER[n_MARKER]``
   as its arrival point, with no per-scene ruling asked for.**  A scene with
   ``n_MARKER == 0`` keeps every older rule exactly as it was - client
   evidence, an owner decree, or refusal - and inventing a coordinate stays
   forbidden.  What this changes is the cost of the sixth scene, not what is
   true about any of them.
2. **The indirect read is mandatory: ``SCENE_NAME[n].n_MARKER`` first, always.
   Reading ``MARKER`` by scene id is a PROHIBITION, not a preference.**
   ``forbidden_direct_index_scenes()`` below is that prohibition written as
   arithmetic, and the reason it needs to be: the shortcut agrees with the
   crosswalk on 12 of the 13 marker scenes, so a round that tries it will most
   likely see it work.
3. **The evidence tier of a marker-sourced point is ``authored`` ~~, never
   ``client-observed``~~ UNLESS an attended or runtime pass has actually stood
   a client on that exact point.**  The struck absolute was false of scene 2
   in this project's own registry on the day it was written (pf-adversary,
   round 8ubiku D6): scene 2's spawn came from ``MARKER[2]`` AND ``SCENE-001``
   stood a live client on it, so it reads ``client-observed`` while still
   being marker-sourced.  It was corrected in the registry JSON in round
   8ubiku and NOT here, which is the same correct-one-of-two-copies mistake
   that round had just written up about itself; round 8ubiku2 is the copy it
   missed.  ``EVIDENCE_TIER`` below carries the default and
   ``console_line`` prints it.  No marker-sourced spawn may be promoted to
   ``confirmed`` until an attended round stands a client on that point and a
   human looks at it (``COO-DECISION 20260828_2250``, unchanged by this one).
   ``GT-134`` is the first such proof; the COO's own words are that if the
   tester surfaces in rock, in lava, or under the floor, **this rule falls
   immediately** and the lane reverts without asking again.

WHAT THE RULING DID NOT DO, WHICH IS THE PART EASIEST TO MISREAD.  It did not
open scene 14's door: ``login_entry_allowed`` stays ``false``, as this lane set
it and chief confirmed in letter ``0520``.  Giving a scene an address is not
wiring a scene.  And the rule may not be applied to a sixth scene until this
text is on ``main`` - the COO set that order explicitly, so the rule and its
first use cannot land in one unreviewed step.

~~NOTHING IN PRODUCTION IMPORTS THIS FILE, AND SAYING SO IS NOT A FORMALITY
(pf-adversary, round vyi2ud, D7).  ``grep -rn world_scene_marker
--include=*.py`` finds this module and its test file, and nothing else ... So
``_self_check`` guards THIS module's own consistency and never runs during a
real login, and the sentence an earlier draft carried - "a raise here is a
boot that stops with a reason" - was false.~~

**THIS FILE IS NOW ON THE BOOT PATH, AND THE ROUND THAT PUT IT THERE LEFT THE
PARAGRAPH ABOVE STANDING.**  Struck, not deleted, because the sequence is the
lesson: round vyi2ud was made to write that paragraph by an adversary pass,
and round 8ubiku then falsified it with its own one-line import while
quoting it as still true (pf-adversary, round 8ubiku2, E6).  At HEAD:
``world_scene_travel.py`` imports this module for the load-time cross-check,
``runtime.py`` imports ``world_scene_liveness`` / ``world_travel_gate`` /
``gm.login_scene_stage`` which all import ``world_scene_travel``, and
``runtime.py``'s ``world_travel_gate.preload()`` calls
``load_scene_registry()``.  So ``_self_check()`` runs at server import and a
bad pinned row IS now a boot that stops with a reason - the sentence an
earlier draft carried, which was false when written and is true now.  A
paragraph asserting what imports a file is a claim with a shelf life; this
one is pinned by a test as of this round rather than left to the next reader.

What this file is, exactly: the crosswalk written down once, with its sources
pinned, so the next scene is a lookup and a test rather than an argument.

WHAT A MARKER IS NOT.  It is not ground: it says a coordinate was authored,
not that the mesh under it can be stood on, and this module makes no claim
about walls, water or height.  It is not a spawn policy either - which scenes
a character may enter, and whether a position there may be persisted, are the
scene registry's ``login_entry_allowed`` / ``persist_position_allowed`` keys
and are decided per scene, not here.  And ``n_DIRTECTION`` is carried through
unread: nothing in this project has ever decoded a facing value, so it is
pinned as data and never turned into a heading on any wire.

THE TABLE IS PINNED, NOT PARSED HERE.  The two source TSVs live in the bridge
repository and are not present in this one, exactly like every other table
this package reads, so the 13 rows are baked below with the source hashes
beside them and ``reverify_on_the_bridge()`` states the command that re-derives
them.  A bridge-side round that runs it and gets different bytes has found
drift, and the pin is what makes that detectable at all.

    AND UNTIL ROUND ``i8timv`` THE MACHINE THAT DECIDES WHETHER A CHANGE
    MERGES COULD RUN NONE OF IT.  (Written new here rather than struck: the
    paragraph above never said this, it simply did not mention the gate at
    all, and a strike would claim a correction that no earlier round made.)
    ``COO-DECISION 20260829_0941`` ordered
    the rows this project uses committed as data, and round ``i8timv`` did it:
    ``world_data/world_marker_crosswalk.json`` holds them, ``world_marker_
    copy.py`` derives from them, and ``tests/test_world_marker_copy.py`` binds
    every literal in this file to that copy WITHOUT a skip decorator.  Read
    ``VERIFICATION_REACH`` below before quoting this: what became gate-checkable
    is agreement with a committed artifact, not agreement with the client.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Convention marker, same as every other always-on module in this package:
# nothing here is behind a scenario flag, and nothing here sends a frame.
production_allowed = True

# Source pins.  Both files are in the bridge repo under gamedata/tables/.
SCENE_NAME_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv"
SCENE_NAME_TSV_SHA256 = (
    "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"
)
MARKER_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__MARKER.tsv"
MARKER_TSV_SHA256 = (
    "723c713aeb604b9b594777517d69f333bbe1509d4931b40294fa720163bd67dc"
)

# Measured totals, kept beside the rows so a shortfall is arithmetic rather
# than a matter of opinion: 271 scene rows, 390 marker rows, 13 scenes with a
# non-zero n_MARKER, 13 of those 13 resolving to a row that points back.
SCENE_ROW_COUNT = 271
MARKER_ROW_COUNT = 390
SCENES_WITH_A_MARKER = 13
MARKER_ROWS_WHOSE_ID_EQUALS_THEIR_SCENE = 19

# (scene n_ID, marker n_ID, THAT MARKER ROW'S OWN n_SCENE, x, y, z, direction).
# The third field is transcribed from the MARKER row rather than derived from
# the first, so ``_self_check`` compares two transcribed columns instead of
# comparing a column with itself - a check built out of one column would pass
# by construction and prove nothing (the failure mode pf-adversary named in
# round uajlve: a test that asserts what the loader already guarantees).
# x/y/z are the table's u32 fields read as two's-complement int32 - see
# _READING below for why that reading is not a guess.  The model id in each
# comment is SCENE_NAME.s_MODLE_ID, for a human checking a row against the map
# in front of them.
_ROWS: tuple[tuple[int, int, int, int, int, int, int], ...] = (
    (1, 1, 1, -10322, -755, 671, 3),        # BG0001 Port Royal
    (2, 2, 2, 26905, 21185, 1680, 8),       # BG0002 Prison Exile Island
    (3, 3, 3, -21215, 16907, -830, 3),      # BG0003
    (4, 4, 4, -19076, 17634, 1440, 6),      # BG0004
    (5, 5, 5, 13025, 23379, -740, 6),       # BG0005
    (6, 6, 6, -9848, 24151, 375, 6),        # Bg0006
    (7, 7, 7, -23266, 7709, 5220, 3),       # Bg0007
    (8, 8, 8, 19440, 23997, 560, 6),        # Bg0008
    (9, 9, 9, 2129, 20907, 240, 6),         # Bg0009
    (10, 10, 10, 15740, 25461, 465, 6),     # Bg0010
    (11, 11, 11, 15179, 22807, 380, 6),     # Bg0011
    (14, 14, 14, -17513, 18989, 1894, 6),   # Bg0015 Hell Volcano Island
    (130, 1000, 130, -24482, 13364, -990, 1),  # Bg4001 - marker id != scene id
)

# WHY THE INT32 READING IS NOT A GUESS.  The raw column is unsigned: scene 1's
# n_X arrives as 4294956974.  Read that way the point is 4.29 billion units
# from anything, and no scene in this game is 4.29 billion units wide.  Read as
# int32 it is -10322, which lands 2340.22 units in XY from the position this
# runtime has stood every new character on since V135 - the same corner of the
# same map.  Two independent scenes agree with the signed reading (scene 2's
# signed-identical row matches a live-client point exactly) and none agrees
# with the unsigned one.
_READING = "u32 columns read as two's-complement int32"

# COO-DECISION 20260829_0542, rule 3, as a value rather than as prose.  Every
# point this module hands out carries this tier and nothing here may be quoted
# for a stronger one.  "authored" means: the people who built the map put this
# coordinate in the shipped table.  It does NOT mean any client has ever stood
# on it, and the two marker points a client HAS accepted (MARKER[1] via V137,
# MARKER[2] via SCENE-001) were accepted as teleport destinations, not as the
# arrival the original game would have chosen.
# HOW FAR THE VERIFICATION IN THIS MODULE ACTUALLY REACHES, ON THE MACHINE
# THAT DECIDES WHETHER A CHANGE MERGES.  Round 8ubiku wired a load-time
# cross-check in world_scene_travel and called the pinned rows below "the
# second opinion ... from the client's table rather than from this file".
# That is true on a workstation with the bridge tree beside this repo.  It is
# FALSE on the gate: MarkerReverificationOnTheBridgeTest is
# @BRIDGE_GAMEDATA.skip_unless_present() and is a DECLARED SKIP in
# docs/PYTEST_SKIP_PINS.json, so on a clone without pf_bridge the only thing
# tying _ROWS to CONSTDATA_TH__MARKER.tsv does not run.
#
# Measured by pf-adversary (round 8ubiku2, E1): on such a clone, forge a
# coordinate in _ROWS, update the by-value pin to match - which a round would
# call "updating the pin" - move the registry spawn to match, and the suite is
# GREEN (4311 passed).  The forged point then carries source
# "client_marker_table" and the loader's cross-check certifies it.  Three
# hand-typed literals in one repo, one commit, one lane, checked against each
# other and reported as corroboration: the round vyi2ud D5 shape, one layer up.
#
# So: what is enforced everywhere is INTERNAL CONSISTENCY - registry spawn,
# registry table_row.n_MARKER and these rows must agree, and a bad edit to any
# ONE of them is refused at boot.  What is enforced only where the bridge tree
# exists is AGREEMENT WITH THE CLIENT.  A round that edits _ROWS is unverified
# until a bridge-side run says otherwise, and this constant is what a reader
# should quote instead of "the tests are green".
#
# ~~The project-level fix is not this lane's to choose - it is either committing
# the marker rows as gate-checkable data or teaching the gate that a diff
# touching _ROWS needs a bridge run - and it is asked in
# pf_bridge/notes_to_chief/20260829_0834_LANE-A-ASK-COO-the-gate-cannot-check-
# client-data.md.~~  ANSWERED AND EXECUTED IN ROUND i8timv.  COO-DECISION
# 20260829_0941 took the first option: the rows this project uses are committed
# as data in world_data/world_marker_crosswalk.json, and
# tests/test_world_marker_copy.py re-derives EVERY literal below from that copy
# with no skip decorator on any machine.  The struck text stays because it names
# the two options and which one was chosen, which a reader a month from now
# cannot recover from the code.
#
# WHAT MOVED, EXACTLY, AND WHAT DID NOT.  What the gate now checks: the 13 rows,
# all six totals, and both worked examples of the prohibition, against a
# committed artifact whose bytes are pinned by world_marker_copy.COPY_SHA256.
# What the gate STILL cannot check: whether that artifact matches the client,
# because the client's tables are not in this repository and no test here can
# reach them.
#
# ~~The E1 forgery is not impossible now, it is four coordinated edits ...
# instead of three ... and each verbatim row carries its source line number so
# one sed on the bridge settles it.~~  STRUCK, MEASURED FALSE IN THE ROUND THAT
# WROTE IT (pf-adversary, round i8timv, D1 and D6), before the PR left draft.
# Executed end to end the forgery costs FIVE edits, four hand-typed - _ROWS,
# the by-value literal in tests/test_world_scene_marker.py, the registry spawn,
# the verbatim row in the copy - plus COPY_SHA256, which is computed rather
# than typed.  The honest delta is +1 hand-typed literal and one sha256sum.
# The sed line settles the 18 verbatim rows; the 661 index pairs carry no line
# numbers, so a wrong TOTAL is still caught by internal literals only.
#
# WHAT IS ACTUALLY TRUE, AND IT IS THE PART WORTH KEEPING: an accident - a
# typo, a bad merge, a half-finished edit - cannot survive at all now, where
# before it could; and a deliberate forgery has to touch one more file and
# leave it in the diff.  Quote this constant, not "the tests are green", and
# do not quote it for agreement with the client.
VERIFICATION_REACH = (
    "internal consistency everywhere; agreement with a committed CURATED "
    "PROJECTION of the client tables (world_data/world_marker_crosswalk.json - "
    "two columns of every row, full rows for 18 of 390) on every machine, the "
    "gate included, via tests/test_world_marker_copy.py, which carries no skip "
    "and pins that it never gains one; agreement between that projection and "
    "the client's own tables only where pf_bridge sits beside this repo, which "
    "is still NOT the merge gate. Every artifact in that chain is written by "
    "this lane in one commit, so what the gate proves is that LANE-A is "
    "internally consistent across four files instead of three"
)
# Where the committed copy lives and what regenerates it.  Named here as text
# rather than imported: build_foundation_release.py collects src/**/*.py and
# nothing else, so a module on the boot path that READ the JSON would work in a
# working tree and die in the release archive.  world_marker_copy is imported
# by tests and bridge tooling only, and a test pins that it stays that way.
COMMITTED_COPY = (
    "src/pirateforce_foundation/world_data/world_marker_crosswalk.json"
)
EVIDENCE_TIER = "authored"


def forbidden_direct_index_scenes() -> dict[int, str]:
    """The scenes where reading ``MARKER`` by scene id gives a WRONG answer.

    Rule 2 of the ruling is a prohibition, and a prohibition nobody can
    measure is a comment.  This is the arithmetic behind it, derived from the
    pinned rows and the pinned totals rather than asserted:

    * **Scene 130 gets another map's point.**  It names marker **1000**, so
      ``MARKER[130]`` is a different row entirely - the one case in the 13
      where the shortcut returns a coordinate belonging to somewhere else.
    * **257 scenes get a point invented for them.**  Of the client's 258
      marker-less scenes - the ones the table says have NO authored arrival
      point - ``257`` have a ``MARKER`` row sitting at their scene-id index.
      The shortcut returns a coordinate for all 257.  Scene 17, the sea, is
      one of them: it hands back ``MARKER[17]``, which carries
      ``n_SCENE = 126`` and the point ``(3050, 232, 90)`` - another scene's
      arrival point, offered for the exact scene ``RE-103`` closed
      bounded-negative on, and for which an owner decree had to be issued
      because nothing in the tables answered.

    * **Three of those 257 even survive a back-pointer check.**  Scenes 126,
      127 and 128 have ``n_MARKER = 0`` and a same-numbered ``MARKER`` row
      whose ``n_SCENE`` points back at them, so the one relation this module
      uses to reject a bad row does not reject theirs.  All three are the
      degenerate ``(0, 0, z)`` origin.

    ~~Seven rows look self-consistent and are nobody's declared arrival
    point ... indexing by scene id returns one of those seven for seven
    scene ids.~~  **STRUCK, MEASURED FALSE BY pf-adversary (round 8ubiku,
    D1), BEFORE IT WAS COMMITTED.**  The subtraction survives - ``19 - 12 =
    7`` rows do carry ``n_ID == n_SCENE`` without being the row their scene
    named - but the sentence built on it did not.  Those seven row ids are
    ``12, 15, 16, 126, 127, 128, 129``, and **four of them (12, 15, 16, 129)
    are not scene ids at all**, so no caller can reach them by indexing with
    a scene id.  Quoting "seven" as the size of rule 2's hazard understated
    it by a factor of 36 while sounding measured, and it handed a bridge
    round a ticket that would have come back "three, not seven" and looked
    like pin drift.  The lesson recorded rather than smoothed: this docstring
    also claimed the full table was unreadable from here and the question
    could not be settled.  It was readable - ``MarkerReverificationOnTheBridge
    Test`` executes against the bridge tree WHERE THAT TREE EXISTS - so the
    hedge was not caution, it was an unmeasured claim wearing caution's
    clothes.  Read ``VERIFICATION_REACH`` below before quoting that test as
    proof of anything: it is a declared skip on the machine that gates the
    merge, which round 8ubiku did not say and should have.

    The count is what makes rule 2 worth enforcing rather than trusting: the
    shortcut is RIGHT for 12 of the 13 scenes anyone is likely to try it on,
    so it will look correct to the round that introduces it and be wrong for
    the round that inherits it.

    Returns scene id -> why the shortcut lies there, for the pinned scenes
    only.  ~~The seven are counted here, not named: identifying WHICH seven
    needs the full 390-row table, which is pinned in the bridge repo and not
    readable from this one.~~  STRUCK (pf-adversary, round 8ubiku2, E7): that
    sentence restated, twenty lines below it, the exact hedge this docstring
    had just struck as an unmeasured claim - and it misdescribed the return,
    which counts no sevens and names no sevens.  The seven row ids ARE named
    above, because the table WAS read.
    """
    lying: dict[int, str] = {}
    for arrival in _BY_SCENE.values():
        if arrival.marker_n_id != arrival.scene_n_id:
            # Only scene 130's foreign row is MEASURED, so only scene 130's
            # message may state one.  The first version interpolated
            # MARKER_ROW_AT_SCENE_130_BELONGS_TO into EVERY entry, so a 14th
            # pinned row - say scene 200 naming marker 1500 - would have told
            # the reader "MARKER[200] carries n_SCENE 2", a number nobody
            # measured (pf-adversary, round 8ubiku2, E8).
            if arrival.scene_n_id == 130:
                detail = (
                    f"and MARKER[130] carries n_SCENE "
                    f"{MARKER_ROW_AT_SCENE_130_BELONGS_TO}, so the shortcut "
                    "hands this scene Prison Exile Island's row"
                )
            else:
                detail = (
                    f"so MARKER[{arrival.scene_n_id}] is not the row this "
                    "scene named; what that row carries is not pinned here "
                    "and must not be guessed"
                )
            lying[arrival.scene_n_id] = (
                f"scene {arrival.scene_n_id} names marker "
                f"{arrival.marker_n_id}, {detail}"
            )
    return lying


# The measured size of rule 2's hazard, re-derived by reverification_script()
# rather than asserted here.  257 of the 258 marker-less scenes have a MARKER
# row at their own scene-id index, so the shortcut answers for almost every
# scene that is supposed to have no answer.  The three below additionally
# survive this module's back-pointer check, which is the only structural
# defence it has; all three are the degenerate (0, 0, z) origin.
SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR = 257
MARKER_LESS_SCENES = 258
SHORTCUT_SURVIVES_THE_BACK_POINTER_CHECK = (126, 127, 128)
# The same three as (marker id, x, y, z), so "all three are the degenerate
# (0, 0, z) origin" stops being prose.  pf-adversary (round i8timv, D9) found
# that sentence was the one claim in this block no machine could check: the
# copy kept no coordinates for 126/127/128.  It keeps them now, and
# world_marker_copy.shortcut_survivor_points() re-derives this tuple.
SHORTCUT_SURVIVOR_POINTS = (
    (126, 0, 0, 90),
    (127, 0, 0, 70),
    (128, 0, 0, 100),
)
# What MARKER[130] actually carries.  Scene 130 names marker 1000, so the
# shortcut does not merely miss - it returns Prison Exile Island's row.
MARKER_ROW_AT_SCENE_130_BELONGS_TO = 2
# What the shortcut returns for the sea, the scene RE-103 closed
# bounded-negative and an owner decree had to answer: MARKER[17] is scene
# 126's row.  Kept as a value because it is the single most persuasive
# example of why rule 2 is a prohibition.
SHORTCUT_AT_SCENE_17 = (126, 3050, 232, 90)


def rows_that_look_self_consistent_and_name_nobody() -> int:
    """The 19 - 12 = 7 subtraction, kept ONLY as row arithmetic.

    Seven ``MARKER`` rows carry ``n_ID == n_SCENE`` without being the row
    their own scene named.  That is true and it is all this returns.  It is
    deliberately NOT the size of rule 2's hazard - four of the seven are not
    scene ids at all, so no caller reaches them.  The hazard is
    ``SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR`` (257), and conflating
    the two is the defect pf-adversary caught in this round (D1).
    """
    scenes_naming_their_own_id = sum(
        1 for a in _BY_SCENE.values() if a.marker_n_id == a.scene_n_id
    )
    return MARKER_ROWS_WHOSE_ID_EQUALS_THEIR_SCENE - scenes_naming_their_own_id


class SceneMarkerError(LookupError):
    """A marker lookup that cannot be answered from the pinned rows.

    LookupError, not ValueError, for the same reason
    ``world_scene_entry.SceneEntryRefused`` is one: a caller that catches
    ValueError around table reads must not silently swallow a scene-level
    refusal into a generic parse failure.
    """


@dataclass(frozen=True)
class MarkerArrival:
    """One authored arrival point, exactly as the client's table carries it."""

    scene_n_id: int
    marker_n_id: int
    marker_row_scene: int
    x: int
    y: int
    z: int
    direction: int

    @property
    def xyz(self) -> tuple[float, float, float]:
        """The point as the float triple every other module in this lane uses."""
        return (float(self.x), float(self.y), float(self.z))


_BY_SCENE: dict[int, MarkerArrival] = {
    row[0]: MarkerArrival(*row) for row in _ROWS
}


def _self_check() -> None:
    """Refuse to import a table that contradicts what this module claims.

    Import-time rather than call-time so a bad edit fails the first test that
    touches the module rather than the tenth.  It is NOT a boot guard: nothing
    in production imports this file today (see the docstring above), and an
    earlier draft of this comment claimed otherwise.  What it can catch is a
    hand-edited row - the back-pointer column and the duplicate-marker check
    below both go red under mutation, which is why they are written as
    relations between two transcribed columns rather than as restatements of
    one.
    """
    if len(_BY_SCENE) != len(_ROWS):
        raise SceneMarkerError("a scene is pinned twice in the marker table")
    if len(_ROWS) != SCENES_WITH_A_MARKER:
        raise SceneMarkerError(
            "the pinned rows and the measured scene count disagree: "
            f"{len(_ROWS)} rows against {SCENES_WITH_A_MARKER} scenes"
        )
    claimed_by: dict[int, int] = {}
    for arrival in _BY_SCENE.values():
        # The relation that makes this a crosswalk and not an index: the row
        # the scene named has to name that scene back.  All 13 do today; a
        # future row that does not is drift, not a new case to accommodate.
        if arrival.marker_row_scene != arrival.scene_n_id:
            raise SceneMarkerError(
                f"marker {arrival.marker_n_id} carries n_SCENE "
                f"{arrival.marker_row_scene}, but scene {arrival.scene_n_id} "
                "names it"
            )
        # Two scenes pointing at one marker row would mean one arrival point
        # serving two maps.  Nothing in the pinned 13 does; this is the guard
        # for the row a later round adds.
        if arrival.marker_n_id in claimed_by:
            raise SceneMarkerError(
                f"marker {arrival.marker_n_id} is claimed by scenes "
                f"{claimed_by[arrival.marker_n_id]} and {arrival.scene_n_id}"
            )
        claimed_by[arrival.marker_n_id] = arrival.scene_n_id
        for value in (arrival.x, arrival.y, arrival.z):
            if type(value) is not int or not -(2 ** 31) <= value < 2 ** 31:
                raise SceneMarkerError(
                    f"scene {arrival.scene_n_id} marker coordinate is not an "
                    "int32"
                )


_self_check()


def arrival_point(scene_n_id: Any) -> MarkerArrival | None:
    """The authored arrival point for a scene, or None if it has no marker.

    None is the table's own answer for 258 of the client's 271 scenes and is
    never "not found": a scene with ``n_MARKER = 0`` has no developer-blessed
    arrival point at all, and a caller that needs one for such a scene has to
    get it from somewhere else and say where (scene 17's owner decree is the
    worked example).
    """
    if type(scene_n_id) is not int:
        raise SceneMarkerError(
            f"scene id must be an int, not {type(scene_n_id).__name__}"
        )
    # The range every sibling in this lane checks, added after pf-adversary
    # noted its absence: without it ``arrival_point(-1)`` answers None, which
    # would report a garbage id as "this scene has no marker" - two different
    # facts sharing one answer.
    if not 1 <= scene_n_id <= 0xFFFF:
        raise SceneMarkerError(
            f"scene id {scene_n_id} is outside the client's scene id range"
        )
    return _BY_SCENE.get(scene_n_id)


def scenes_with_an_arrival_point() -> tuple[int, ...]:
    """Every scene id this module can answer for, ascending."""
    return tuple(sorted(_BY_SCENE))


def console_line(arrival: MarkerArrival) -> str:
    """One ASCII line naming a marker that was used, for the cp874 console.

    Printed by whoever stands a character on this point, never by this module:
    a line here would claim an arrival that may still be refused downstream.
    """
    if type(arrival) is not MarkerArrival:
        raise SceneMarkerError("console line needs a MarkerArrival")
    return (
        f"SCENE_MARKER scene={arrival.scene_n_id} marker={arrival.marker_n_id} "
        f"xyz=({arrival.x},{arrival.y},{arrival.z}) "
        f"dir={arrival.direction} source=CLIENT_MARKER_TABLE "
        f"evidence={EVIDENCE_TIER}"
    )


def reverification_script() -> str:
    """A self-contained script that RE-DERIVES these rows and asserts them.

    Returned as the text of a ``.py`` file, deliberately not as a shell
    command: the earlier version of this function returned a POSIX heredoc
    (``python - <<'EOF'``), and the bridge is a Windows host that drives
    everything through ``py -3`` and PowerShell, which has no ``<<`` - so the
    one place it was written for could not run it (pf-adversary, round
    vyi2ud, D9).

    It ASSERTS rather than prints, for the same round's other finding: the old
    version ended in ``# expect exactly 13 lines``, a comment, so a 14th scene
    gaining a marker still exited 0 and the three measured totals below were
    read by nothing at all.  Every number this module states about the source
    tables is checked here: both file hashes, the 271 scene rows, the 390
    marker rows, the 19 rows whose id equals their scene, the 13 scenes with a
    marker, and the exact contents of all 13 pinned rows.

    ``tests/test_world_scene_marker.py`` runs this against the bridge tree
    when it is present beside this repository, and skips when it is not, so
    the assertions are exercised rather than merely offered.
    """
    expected = ",\n    ".join(repr(row) for row in _ROWS)
    return (
        '"""Re-derive world_scene_marker.py from the client tables.  py -3 this file'
        "\n\nRun it from the pf_bridge working tree (the directory holding gamedata/).\n"
        "Exit 0 = every pinned number still matches the sources.  Any assertion\n"
        "failure is drift: report the failing line, do not edit the pin to match.\n"
        '"""\n'
        "import csv\n"
        "import hashlib\n"
        "import sys\n"
        "\n"
        f"SCENE_TSV = {SCENE_NAME_TSV.split('/', 1)[1]!r}\n"
        f"MARKER_TSV = {MARKER_TSV.split('/', 1)[1]!r}\n"
        f"SCENE_SHA = {SCENE_NAME_TSV_SHA256!r}\n"
        f"MARKER_SHA = {MARKER_TSV_SHA256!r}\n"
        f"SCENE_ROWS = {SCENE_ROW_COUNT}\n"
        f"MARKER_ROWS = {MARKER_ROW_COUNT}\n"
        f"ID_EQUALS_SCENE = {MARKER_ROWS_WHOSE_ID_EQUALS_THEIR_SCENE}\n"
        f"MARKER_LESS_SCENES = {MARKER_LESS_SCENES}\n"
        f"SHORTCUT_INVENTS = {SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR}\n"
        f"SHORTCUT_BACK_POINTER_OK = {SHORTCUT_SURVIVES_THE_BACK_POINTER_CHECK!r}\n"
        f"MARKER_130_BELONGS_TO = {MARKER_ROW_AT_SCENE_130_BELONGS_TO}\n"
        f"SHORTCUT_AT_17 = {SHORTCUT_AT_SCENE_17!r}\n"
        f"EXPECTED = (\n    {expected},\n)\n"
        "\n"
        "\n"
        "def s32(value):\n"
        "    value = int(value)\n"
        "    return value - (1 << 32) if value >= (1 << 31) else value\n"
        "\n"
        "\n"
        "def read(path):\n"
        "    with open(path, newline='', encoding='utf-8') as handle:\n"
        "        return list(csv.DictReader(handle, delimiter='\\t'))\n"
        "\n"
        "\n"
        "for path, pinned in ((SCENE_TSV, SCENE_SHA), (MARKER_TSV, MARKER_SHA)):\n"
        "    with open(path, 'rb') as handle:\n"
        "        actual = hashlib.sha256(handle.read()).hexdigest()\n"
        "    assert actual == pinned, 'sha256 drift in %s: %s' % (path, actual)\n"
        "\n"
        "scenes = read(SCENE_TSV)\n"
        "markers = read(MARKER_TSV)\n"
        "assert len(scenes) == SCENE_ROWS, len(scenes)\n"
        "assert len(markers) == MARKER_ROWS, len(markers)\n"
        "by_id = {int(row['n_ID']): row for row in markers}\n"
        "same = sum(1 for row in markers if int(row['n_ID']) == int(row['n_SCENE']))\n"
        "assert same == ID_EQUALS_SCENE, same\n"
        "\n"
        "derived = []\n"
        "for scene in scenes:\n"
        "    marker_id = int(scene['n_MARKER'])\n"
        "    if not marker_id:\n"
        "        continue\n"
        "    row = by_id[marker_id]\n"
        "    derived.append((\n"
        "        int(scene['n_ID']), marker_id, int(row['n_SCENE']),\n"
        "        s32(row['n_X']), s32(row['n_Y']), s32(row['n_Z']),\n"
        "        int(row['n_DIRTECTION']),\n"
        "    ))\n"
        "\n"
        "assert tuple(derived) == EXPECTED, tuple(derived)\n"
        "\n"
        "# Rule 2's hazard, re-derived rather than asserted.  These are the\n"
        "# numbers a docstring got wrong by a factor of 36 before a bridge\n"
        "# round could check them (round 8ubiku, pf-adversary D1).\n"
        "marker_less = [int(r['n_ID']) for r in scenes if not int(r['n_MARKER'])]\n"
        "assert len(marker_less) == MARKER_LESS_SCENES, len(marker_less)\n"
        "invents = [i for i in marker_less if i in by_id]\n"
        "assert len(invents) == SHORTCUT_INVENTS, len(invents)\n"
        "survives = tuple(sorted(\n"
        "    i for i in invents if int(by_id[i]['n_SCENE']) == i))\n"
        "assert survives == SHORTCUT_BACK_POINTER_OK, survives\n"
        "assert int(by_id[130]['n_SCENE']) == MARKER_130_BELONGS_TO\n"
        "row17 = by_id[17]\n"
        "assert (int(row17['n_SCENE']), s32(row17['n_X']), s32(row17['n_Y']),\n"
        "        s32(row17['n_Z'])) == SHORTCUT_AT_17\n"
        "\n"
        "sys.stdout.write('world_scene_marker: %d rows re-derived, all pinned "
        "values match\\n' % len(derived))\n"
    )
