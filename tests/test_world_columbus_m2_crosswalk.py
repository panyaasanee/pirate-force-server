"""LANE-A: pins the corrected Columbus -> quest -> destination-scene crosswalk.

WHY THIS FILE EXISTS.  This project has shipped wrong-NPC bugs from
ordinal/index confusion twice already (RE-093, RE-097), and a third one
reached a chief status letter: ``pf_bridge/notes_to_chief/20260827_1830_
CHIEF-REPLY-PANYA-CHASE-0915-status-faction1-wired-M2-plan-RE100-coverage.md``
lines 28-30 wrote Columbus's quest as ``3023`` and cited placement ``index 1``
as if both facts named the same NPC.  They do not.  Re-derived independently
twice from the committed gamedata tables (see the sha256 pins below):

* ``CONSTDATA_TH__MOBS.tsv`` row ``n_ID=156`` is Port Royal's real Columbus
  (``s_ROLE_GRAPHIC=COLUMBUS_0``, bg0001 placement index 1 - stated by the
  owner in ``pf_bridge/notes_to_chief/20260827_0925_PANYA-DECISION-...`` and
  restated in ``20260827_0950_PANYA-DECISION-index1-Columbus-156-index65-
  Loie-802-and-CORRECTION-...``, one continuous attended session, not two
  independent derivations - and this exact index already moved once that
  same day, RE-097 first argued index 0).  FLAGGED: no committed table
  crosswalks census placement index to MOBS.n_ID (RE-097's own result), so
  this binding is owner testimony, not a table fact - only ``MOBS 156 ->
  quest 3021 -> scene 17`` below is table-measured.  Its ``s_QUEST_BEGIN``
  list contains ``3021``, not ``3023``.
* ``n_ID=36`` is a DIFFERENT real MOBS row (level 35) whose quest list
  contains ``3023``.  ``3023`` is that NPC's quest, not Port Royal
  Columbus's (MOBS 156).  ("Spice Paradise's Columbus" for MOBS 36, used in
  the scenario JSON prose, is a hypothesis/pattern-reading, not a table
  field - n_ID_MAP/s_LOCATION are blank for both rows; it does not matter
  which island 36 belongs to, only that 36 != 156.)
* ``QUESTDATA_TH__QUEST.tsv`` row ``n_ID=3021`` is a ``Q_TELEPORT1`` quest
  whose ``n_VARI_2`` (destination scene_id) is ``17`` - a sea scene
  (``n_SCENE_TYPE=4``), matching the M2 plan (talk to Columbus -> teleport to
  a sea map -> become a ship).  Quest ``3023``'s ``n_VARI_2`` is ``19``,
  which is MOBS 36's destination, not Port Royal's.
* ``CONSTDATA_TH__SCENE_NAME.tsv`` row ``n_ID=17`` is ``Bg1001`` / sea scene.

This file is a pin, not a switch.  It reads the bridge's own committed TSVs
directly (the same pattern ``tools/pf_mine_scene_mob_roster.py`` and
``tests/test_pf_scan_field_scene_candidates.py`` already use) and skips, with
a named reason, on any machine that does not carry the ``pf_bridge`` sibling
checkout (the Windows single-repo gate, most namely) - see
``tests/pf_preconditions.BRIDGE_GAMEDATA``.  It asserts nothing about runtime
wiring: no scene_id 17 has ever been sent to a client by this project, and no
NPCConversation dispatch for MOBS 156 exists in ``src/`` yet.  That wiring is
a ``CORE-REQUEST`` for the chief, handed off separately; this file exists so
the FACTS that request depends on cannot silently drift back to 3023/19
without a red test.

ONE THING THIS FILE DELIBERATELY DOES NOT SETTLE: quest 3021 for MOBS 156 has
only been confirmed at the gamedata/table layer ([STATIC]).  Nobody has
re-run an RE-095-style wire capture for 3021 the way RE-095 did for (the
wrong) 3023.  That gap is not something a static table test can close, and
this file does not pretend to; see the round file / handoff letter for the
open ask to lane C.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"
TABLES = GAMEDATA / "tables"

MOBS_TSV = TABLES / "CONSTDATA_TH__MOBS.tsv"
QUEST_TSV = TABLES / "QUESTDATA_TH__QUEST.tsv"
SCENE_NAME_TSV = TABLES / "CONSTDATA_TH__SCENE_NAME.tsv"
BG1001_PLACEMENTS_TSV = GAMEDATA / "scene" / "Bg1001" / "Bg1001.placements.tsv"

# Provenance: sha256 values supplied by the COO round order (2026-08-27,
# lane-A Columbus M2 crosswalk correction), re-verified by this lane against
# the committed files before this test was written.  A mismatch here means
# the bridge's own tables moved out from under this pin - report it, do not
# silently update this constant to match.
MOBS_TSV_SHA256 = (
    "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b"
)
QUEST_TSV_SHA256 = (
    "cc9927286def2bda166c320a2dddd16f5457eb4579ce5207a3d76758707527bd"
)
SCENE_NAME_TSV_SHA256 = (
    "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"
)
BG1001_PLACEMENTS_TSV_SHA256 = (
    "5e4de48707a87061d9a95471a1c3c25c56f0469fe2ece7ef0709a9c79f40fec7"
)

COLUMBUS_PORT_ROYAL_MOBS_ID = "156"
COLUMBUS_SPICE_PARADISE_MOBS_ID = "36"
CORRECT_QUEST_ID = "3021"
STALE_WRONG_QUEST_ID = "3023"
CORRECT_DESTINATION_SCENE_ID = "17"
STALE_WRONG_DESTINATION_SCENE_ID = "19"
BG1001_MODEL_ID = "Bg1001"
BG1001_SCENE_TYPE_SEA = "4"


def _read_tsv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _row_by_id(rows: list[dict], id_column: str, value: str) -> dict:
    matches = [row for row in rows if row[id_column] == value]
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly one row with %s=%r, found %d"
            % (id_column, value, len(matches))
        )
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@BRIDGE_GAMEDATA.skip_unless_present()
class ColumbusM2CrosswalkTest(unittest.TestCase):
    """Pins MOBS 156 -> quest 3021 -> scene 17/Bg1001, not 3023 -> 19."""

    def test_provenance_hashes_match_the_pinned_tables(self) -> None:
        # If any of these move, everything below is checking stale bytes -
        # fail loud here first rather than mysteriously elsewhere.
        self.assertEqual(_sha256(MOBS_TSV), MOBS_TSV_SHA256)
        self.assertEqual(_sha256(QUEST_TSV), QUEST_TSV_SHA256)
        self.assertEqual(_sha256(SCENE_NAME_TSV), SCENE_NAME_TSV_SHA256)
        self.assertEqual(
            _sha256(BG1001_PLACEMENTS_TSV), BG1001_PLACEMENTS_TSV_SHA256
        )

    def test_port_royal_columbus_mobs_156_quest_begin_contains_3021(self) -> None:
        rows = _read_tsv(MOBS_TSV)
        columbus = _row_by_id(rows, "n_ID", COLUMBUS_PORT_ROYAL_MOBS_ID)
        self.assertEqual(columbus["s_ROLE_GRAPHIC"], "COLUMBUS_0")
        quest_begin = columbus["s_QUEST_BEGIN"].split(";")
        self.assertIn(
            CORRECT_QUEST_ID,
            quest_begin,
            "MOBS 156 (Port Royal Columbus) must offer quest 3021 - if this "
            "goes red, either the table changed or this pin is stale",
        )

    def test_port_royal_columbus_mobs_156_does_not_require_3023(self) -> None:
        # The regression this file exists to prevent: a future round
        # re-copying the stale 1830 status letter's "quest = 3023" claim onto
        # MOBS 156.  3023 belongs to a DIFFERENT NPC (MOBS 36, Spice
        # Paradise's Columbus) - it is not required to be, and in the
        # committed table today is not, part of MOBS 156's quest list.
        rows = _read_tsv(MOBS_TSV)
        columbus_156 = _row_by_id(rows, "n_ID", COLUMBUS_PORT_ROYAL_MOBS_ID)
        quest_begin_156 = columbus_156["s_QUEST_BEGIN"].split(";")
        self.assertNotIn(STALE_WRONG_QUEST_ID, quest_begin_156)

        columbus_36 = _row_by_id(rows, "n_ID", COLUMBUS_SPICE_PARADISE_MOBS_ID)
        quest_begin_36 = columbus_36["s_QUEST_BEGIN"].split(";")
        self.assertIn(
            STALE_WRONG_QUEST_ID,
            quest_begin_36,
            "quest 3023 should still belong to MOBS 36 (a different, real "
            "row) - if this goes red, the mix-up moved rather than resolved",
        )

    def test_quest_3021_destination_scene_is_17(self) -> None:
        rows = _read_tsv(QUEST_TSV)
        quest = _row_by_id(rows, "n_ID", CORRECT_QUEST_ID)
        self.assertEqual(quest["s_LUASCRIPT"], "Q_TELEPORT1")
        self.assertEqual(quest["n_VARI_2"], CORRECT_DESTINATION_SCENE_ID)

    def test_quest_3023_destination_scene_is_19_not_17(self) -> None:
        # Documents WHY 3023/19 must not be reused for Port Royal Columbus:
        # it is a real quest, it just points somewhere else (Spice
        # Paradise's own destination).
        rows = _read_tsv(QUEST_TSV)
        quest = _row_by_id(rows, "n_ID", STALE_WRONG_QUEST_ID)
        self.assertEqual(quest["n_VARI_2"], STALE_WRONG_DESTINATION_SCENE_ID)
        self.assertNotEqual(quest["n_VARI_2"], CORRECT_DESTINATION_SCENE_ID)

    def test_scene_17_is_bg1001_and_is_a_sea_scene(self) -> None:
        rows = _read_tsv(SCENE_NAME_TSV)
        scene = _row_by_id(rows, "n_ID", CORRECT_DESTINATION_SCENE_ID)
        self.assertEqual(scene["s_MODLE_ID"], BG1001_MODEL_ID)
        self.assertEqual(scene["n_SCENE_TYPE"], BG1001_SCENE_TYPE_SEA)

    def test_bg1001_placements_hold_no_player_arrival_spawn(self) -> None:
        # Fail-closed pin: do not let a future round invent a spawn
        # coordinate for Bg1001.  Every row here is a Mob_set_* monster
        # placement (index 0-7); there is no explicit player-arrival point.
        rows = _read_tsv(BG1001_PLACEMENTS_TSV)
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertTrue(
                row["name"].startswith("Mob_set_"),
                "unexpected placement row %r - if a player-arrival row was "
                "added, update the world_scene_registry_001.json spawn "
                "field and this comment together, do not invent one first"
                % (row,),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
