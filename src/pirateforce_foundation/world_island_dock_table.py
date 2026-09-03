"""LANE-A / M2: which trigger id names which island, and what gates it.

WHY THIS FILE EXISTS
--------------------
M2's pass bar is "sail near an island -> a captain report window -> confirm ->
you are standing on island 2 (Prison Exile) and island 3 (Spice Paradise)".
Round `ufcemz` established two things about that path and neither of them was
an answer: `TriggerVital` (0x1FB2) has no responder anywhere in this server,
and the five trigger ids a real capture showed (40/51/3/57/36) are ordinary
sea props (Seafood Cargo, Offer Altar, Black Braid Landmine, Magic Egg, Black
Charm Demon Flower), not islands.  COO-DECISION 20260904_0343 item 2 then
asked this lane to derive the island rows itself from committed client tables,
and to report "there is no column for it" rather than guess.

The answer is NOT in the file that letter pointed at.  Measured:
`pf_bridge/gamedata/scene/Bg3001/Bg3001.placements.tsv` (sha256
63a61fcfa6f48d548f2dede28a41a79dbdb2f81c6cb824cb5246c5e31fd1c0e1) holds 38
placements and every single one of them is a `Mob_Set_NN` row -- there is no
island row in it to separate from a floating-object row, and no column that
carries a trigger id.  That half of the assignment is reported as absent, not
guessed, exactly as the letter required.

The answer IS in the trigger tables, and it is unambiguous.  Trigger ids
152..167 are one contiguous block of TRAVEL DESTINATIONS, and the block is
identifiable by three independent properties, none of which this lane chose:

1. NAMES.  Each row's `s_Trigger_NAME` is character-for-character a scene
   name in `TEXTDATA_TH__SCENE_NAME_TIP.tsv` (sha256 f9076cfc...bfa3a, the
   same copy `gm/scene_catalog.py` already ships), and the run is in scene
   order: 152 Port Royal, 153 Prison Exile Island, 154 Spice Paradise Island,
   155 Slave Market Island, ... 161 Hell Volcanic Island.
2. LEVEL GATES.  Each row's tip text carries a level requirement, and for
   every one of the eleven rows 152..161 that number equals `n_SCENE_LV` of
   the matching scene row in `CONSTDATA_TH__SCENE_NAME.tsv` (sha256
   e38114a8...5d60b -- already the pinned `scene_name` source of a dozen
   `world_bg*_identity.py` modules in this repo).  Two tables written by
   different teams agreeing on eleven numbers is not a coincidence of naming.
3. NO CLICK VERB.  Every neighbouring prop trigger -- 148/149/150/151 above
   the block, 169..175 below it -- spells out a usage verb in its tip
   ("[vithi chai: double-click left]").  Not one row in 152..167 does.  They
   carry a level requirement and nothing else.

Property 3 is the one that matters for M2, because the owner said what the
real server does (PANYA-INFO 20260904_0409, her words): "sail the ship into
the island and the captain report window pops by itself, you do not click the
island".  A destination trigger with no click verb is exactly the shape of a
trigger the client fires on contact.  That is a CONSISTENCY, not a proof: no
byte of a 0x1FB2 frame carrying id 153 or 154 has ever been observed.  The
capture ticket drafted with this round exists to get those bytes.

WHAT THIS MODULE DOES NOT CLAIM
-------------------------------
* NOT that 0x1FB2 is the docking frame.  COO-DECISION 0343 item 1 withdrew
  that reading and this file does not reinstate it.  What it offers is a
  cheap way to find out: if the client fires 0x1FB2 with id 153 when the ship
  touches Prison Exile Island, the log-only hook in
  `lane_hooks/lane_a_island_trigger_log.py` prints it on the next attended
  boot, and the hypothesis is settled in one round instead of a static-RE
  chain.
* NOT that `scene_name_tip_id` below IS the wire `scene_id`.  The bridge's
  own RE queue pins that link as "CANDIDATE, NOT ESTABLISHED", proven only
  for rows 1 (Port Royal) and 2 (Prison Exile Island).  Every row carries
  `wire_scene_id_status` saying which it is; a caller that needs the wire id
  must read that field rather than the number next to it.
* NOT a level check.  `min_level` is what the CLIENT's own tables say gates
  each destination.  Nothing here enforces it, and it is recorded because a
  test character below level 25 is a plausible reason for a capture round at
  Spice Paradise Island to produce a refusal instead of a captain report --
  the attended ticket says so in its preconditions.

HOW TO RE-DERIVE (both commands run in a `pf_bridge` clone)
-----------------------------------------------------------
    awk -F'\t' 'NR>1 && $1>=148 && $1<=175 {print $1"\t"$2"\t|"$3"|"}' \
        gamedata/tables/TEXTDATA_TH__Trigger_TIP.tsv
    awk -F'\t' 'NR>1 && $1>=1 && $1<=16 {print $1"\t"$2"\t"$3"\t"$19}' \
        gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv

Evidence grade A (committed client artifacts) for "this id has this name and
this level gate", and nothing above grade A for anything about the wire.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple
import csv
import hashlib


_DATA_PATH = Path(__file__).parent / "world_data" / "trigger_tip_th.tsv"

# sha256 of the byte-for-byte copy in world_data/, taken from
# pf_bridge/gamedata/tables/TEXTDATA_TH__Trigger_TIP.tsv.
SOURCE_SHA256 = "bccbb0430a40793611d1bc864a7d81711fa46831c38c2f9769f9ffceaed7503f"

# The two tables the rows below were cross-derived from.  Recorded, not read:
# neither file is in this repository, and the second sha is already the pinned
# `scene_name` source of the world_bg*_identity.py family.
SCENE_NAME_TIP_SHA256 = (
    "f9076cfc3c14433b376811437d68375d5dd1ce1ef2c7a50dbc1d4e4d241bfa3a"
)
CONST_SCENE_NAME_SHA256 = (
    "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"
)
BG3001_PLACEMENTS_SHA256 = (
    "63a61fcfa6f48d548f2dede28a41a79dbdb2f81c6cb824cb5246c5e31fd1c0e1"
)

# Bg3001.placements.tsv: 38 placements, all of them Mob_Set_NN.  Kept as a
# number so a future re-derivation that finds an island row there fails this
# module's test instead of silently agreeing with a stale docstring.
BG3001_PLACEMENT_COUNT = 38
BG3001_ISLAND_PLACEMENT_COUNT = 0


class DestinationRow(NamedTuple):
    """One travel-destination trigger row, as the client's tables describe it.

    ``trigger_id``          the id that appears in a 0x1FB2 frame's 0x0F tag.
    ``name``                ``s_Trigger_NAME``, stripped.  ASCII for every row
                            in this table; the module never assumes that of
                            names outside it (see ``console_safe``).
    ``scene_name_tip_id``   ``n_ID`` of the row in TEXTDATA_TH__SCENE_NAME_TIP
                            whose ``s_SCENE_NAME`` equals ``name`` exactly.
    ``scene_model``         ``s_MODLE_ID`` of that scene in
                            CONSTDATA_TH__SCENE_NAME, or None when that table
                            has no row for the id (true for 12/15/16).
    ``min_level``           the level gate.  Present in BOTH tables and equal
                            in both for every row that has ``levels_agree``.
    ``levels_agree``        True when the tip text and ``n_SCENE_LV`` matched.
                            False means only the tip text had a number.
    ``wire_scene_id_status``  "PROVEN" only where the bridge's RE queue says
                            the n_ID equals the wire scene_id; "CANDIDATE"
                            everywhere else.  Never upgrade a row here from a
                            successful /warp alone -- say which ticket did it.
    """

    trigger_id: int
    name: str
    scene_name_tip_id: int
    scene_model: str | None
    min_level: int
    levels_agree: bool
    wire_scene_id_status: str


# Trigger ids 152..164: a destination each, name-matched to a scene row.
# 152..161 additionally agree on the level gate across two tables.
DESTINATION_ROWS: tuple[DestinationRow, ...] = (
    DestinationRow(152, "Port Royal", 1, "BG0001", 0, True, "PROVEN"),
    DestinationRow(153, "Prison Exile Island", 2, "BG0002", 0, True, "PROVEN"),
    DestinationRow(154, "Spice Paradise Island", 3, "BG0003", 25, True, "CANDIDATE"),
    DestinationRow(155, "Slave Market Island", 4, "BG0004", 45, True, "CANDIDATE"),
    DestinationRow(156, "Evil Port", 5, "BG0005", 60, True, "CANDIDATE"),
    DestinationRow(157, "Ocean Walled City", 6, "Bg0006", 70, True, "CANDIDATE"),
    DestinationRow(158, "Voodoo Island", 7, "Bg0007", 81, True, "CANDIDATE"),
    DestinationRow(159, "Silver Harbour", 8, "Bg0008", 86, True, "CANDIDATE"),
    DestinationRow(160, "Death City Sea", 9, "Bg0009", 92, True, "CANDIDATE"),
    DestinationRow(161, "Hell Volcanic Island", 14, "Bg0015", 100, True, "CANDIDATE"),
    DestinationRow(162, "Drake empty Walled", 12, None, 112, False, "CANDIDATE"),
    DestinationRow(163, "Lost Eden", 15, None, 111, False, "CANDIDATE"),
    DestinationRow(164, "Sunset Deserted", 16, None, 115, False, "CANDIDATE"),
)

# Trigger ids 165..167 sit inside the same no-click-verb block but their names
# are travel phrases ("travel to <ocean>"), not scene names, so no exact
# name match exists and NO scene id is asserted for them.  They are listed so
# the hook can say "this is in the destination block" instead of "unknown",
# and so a future round does not re-discover them as if they were props.
OCEAN_TRAVEL_TRIGGER_IDS: tuple[int, ...] = (165, 166, 167)

# The block, stated once.
DESTINATION_BLOCK_FIRST = 152
DESTINATION_BLOCK_LAST = 167

# M2's two targets, by the pass bar in NOW.md's milestone ladder.
M2_TARGET_TRIGGER_IDS: tuple[int, ...] = (153, 154)

CLASS_ISLAND = "ISLAND"
CLASS_OCEAN = "OCEAN_TRAVEL"
CLASS_PROP = "PROP"
CLASS_UNKNOWN = "UNKNOWN"


def _load_names() -> dict[int, str]:
    raw = _DATA_PATH.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise RuntimeError(
            "world_data/trigger_tip_th.tsv sha256 mismatch: expected "
            f"{SOURCE_SHA256}, got {actual} -- the trigger table drifted from "
            "the pinned client source; re-copy it from pf_bridge/gamedata "
            "before trusting any name this module returns"
        )
    names: dict[int, str] = {}
    with _DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        if header[:2] != ["n_ID", "s_Trigger_NAME"]:
            raise RuntimeError(
                f"world_data/trigger_tip_th.tsv header changed: {header[:2]!r}"
            )
        for row in reader:
            if not row or not row[0].strip().lstrip("-").isdigit():
                continue
            names[int(row[0])] = row[1].strip()
    return names


TRIGGER_NAMES: dict[int, str] = _load_names()
TRIGGER_NAME_COUNT = len(TRIGGER_NAMES)

_BY_TRIGGER_ID: dict[int, DestinationRow] = {
    row.trigger_id: row for row in DESTINATION_ROWS
}


def console_safe(text: str) -> str:
    """ASCII rendering of any client-table string before it reaches print().

    The bridge console is cp874.  One name in this table (id 310) is Chinese
    and has no cp874 mapping at all; two more (165/166) are Thai, which cp874
    does map but which this project still prefers not to push through a
    console line other tools grep.  Same lesson, same fix, as
    ``lane_hooks._console_safe``: escape rather than risk raising inside the
    print that was supposed to be the evidence.
    """
    return text.encode("ascii", "backslashreplace").decode("ascii")


def trigger_name(trigger_id: int) -> str | None:
    """The client's own name for this trigger id, or None if the table has none."""
    return TRIGGER_NAMES.get(trigger_id)


def destination_for_trigger_id(trigger_id: int) -> DestinationRow | None:
    """The destination row for this trigger id, or None if it is not one."""
    return _BY_TRIGGER_ID.get(trigger_id)


def destination_for_scene_id(scene_name_tip_id: int) -> DestinationRow | None:
    """The destination row that names this scene, or None.

    Takes the SCENE_NAME table's ``n_ID``.  Read the row's
    ``wire_scene_id_status`` before treating that number as a wire scene_id.
    """
    for row in DESTINATION_ROWS:
        if row.scene_name_tip_id == scene_name_tip_id:
            return row
    return None


def classify_trigger_id(trigger_id: int) -> str:
    """One of ISLAND / OCEAN_TRAVEL / PROP / UNKNOWN.

    ISLAND means "the client's tables call this id a named travel
    destination", which includes Port Royal, a port rather than an island.
    It does NOT mean "sailing into it docks you there" -- nothing in this
    repository has evidence for that yet.
    """
    if trigger_id in _BY_TRIGGER_ID:
        return CLASS_ISLAND
    if trigger_id in OCEAN_TRAVEL_TRIGGER_IDS:
        return CLASS_OCEAN
    if trigger_id in TRIGGER_NAMES:
        return CLASS_PROP
    return CLASS_UNKNOWN


def describe_trigger_id(trigger_id: int) -> str:
    """One ASCII console fragment describing a trigger id.  Never raises.

    Shapes, exactly:
        `id=153 name=Prison Exile Island ISLAND scene=2 min_level=0 wire=PROVEN`
        `id=165 name=\\u0e40... OCEAN_TRAVEL scene=unknown`
        `id=40 name=Black Braid Landmine PROP`
        `id=9999 name=? UNKNOWN`
    """
    kind = classify_trigger_id(trigger_id)
    name = trigger_name(trigger_id)
    head = f"id={trigger_id} name={console_safe(name) if name else '?'} {kind}"
    row = destination_for_trigger_id(trigger_id)
    if row is None:
        if kind == CLASS_OCEAN:
            return head + " scene=unknown"
        return head
    return (
        f"{head} scene={row.scene_name_tip_id} min_level={row.min_level}"
        f" wire={row.wire_scene_id_status}"
    )
