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
  1082.04 / 2075.05 / 447.71 - the same gap ``runtime.py:3717`` already
  describes as "about 2340 units away horizontally and 448 vertically"; this
  file first said "about 2200", which matched neither, D10).  Both points are
  real: the marker is the client table's authored point, V135's is this
  server's own historical choice, and NOTHING here proposes changing home.

[LANE-A ASSUMPTION - AWAITING COO CONFIRMATION]  That a scene's MARKER row is
the right place to stand an arriving character is this lane's reading, not a
ruling: the letter asking for it is
``pf_bridge/notes_to_chief/20260829_0447_LANE-A-ASK-COO-marker-table-as-
default-spawn.md``, and it names what to revert if the answer is no (one row
out of the scene registry).

NOTHING IN PRODUCTION IMPORTS THIS FILE, AND SAYING SO IS NOT A FORMALITY
(pf-adversary, round vyi2ud, D7).  ``grep -rn world_scene_marker --include=*.py``
finds this module and its test file, and nothing else: the scene-14 spawn in
``scenarios/world_scene_registry_001.json`` is a hand-typed JSON literal that
a test cross-checks against the row below, not a value read from here at boot.
So ``_self_check`` guards THIS module's own consistency and never runs during
a real login, and the sentence an earlier draft carried - "a raise here is a
boot that stops with a reason" - was false.  What this file is, exactly: the
crosswalk written down once, with its sources pinned, so the next scene is a
lookup and a test rather than an argument.

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
# int32 it is -10322, which lands about 2200 units from the position this
# runtime has stood every new character on since V135 - the same corner of the
# same map.  Two independent scenes agree with the signed reading (scene 2's
# signed-identical row matches a live-client point exactly) and none agrees
# with the unsigned one.
_READING = "u32 columns read as two's-complement int32"


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
        f"dir={arrival.direction} source=CLIENT_MARKER_TABLE"
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
        "sys.stdout.write('world_scene_marker: %d rows re-derived, all pinned "
        "values match\\n' % len(derived))\n"
    )
