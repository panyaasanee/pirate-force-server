"""The island/destination trigger rows, and the claims they are allowed to make.

LANE-A, round `xv20xj`, for COO-DECISION 20260904_0343 item 2.  Everything
here is grade A static evidence (committed client tables); nothing here is
allowed to become a claim about the wire, and the last class in this file is
the guard on exactly that.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_island_dock_table as islands  # noqa: E402


class TheShippedTableMatchesItsPinnedSourceTests(unittest.TestCase):
    def test_the_copied_trigger_table_still_hashes_to_the_pin(self):
        raw = islands._DATA_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), islands.SOURCE_SHA256)

    def test_every_shipped_row_name_is_the_clients_own_name_for_that_id(self):
        # The rows below are not a list this lane wrote down: each name is
        # read back out of the client's table by id.  A transcription slip
        # in DESTINATION_ROWS is red here, not discovered on the wire.
        for row in islands.DESTINATION_ROWS:
            with self.subTest(trigger_id=row.trigger_id):
                self.assertEqual(islands.trigger_name(row.trigger_id), row.name)

    def test_the_table_covers_the_whole_client_trigger_range(self):
        self.assertEqual(islands.TRIGGER_NAME_COUNT, 312)
        self.assertEqual(min(islands.TRIGGER_NAMES), 1)
        self.assertEqual(max(islands.TRIGGER_NAMES), 312)


class TheDestinationBlockIsIdentifiedByTheTableNotByThisLaneTests(unittest.TestCase):
    def test_the_two_m2_targets_are_the_two_islands_the_milestone_names(self):
        prison = islands.destination_for_trigger_id(153)
        spice = islands.destination_for_trigger_id(154)
        self.assertIsNotNone(prison)
        self.assertIsNotNone(spice)
        self.assertEqual(prison.name, "Prison Exile Island")
        self.assertEqual(spice.name, "Spice Paradise Island")
        self.assertEqual((prison.scene_name_tip_id, spice.scene_name_tip_id), (2, 3))
        self.assertEqual(islands.M2_TARGET_TRIGGER_IDS, (153, 154))

    def test_the_block_is_contiguous_and_ordered_by_scene(self):
        ids = [row.trigger_id for row in islands.DESTINATION_ROWS]
        self.assertEqual(ids, list(range(152, 165)))
        self.assertEqual(ids, sorted(ids))
        scenes = [row.scene_name_tip_id for row in islands.DESTINATION_ROWS]
        # Scene order for the first ten, then the client's own gap (12/15/16
        # are later-version scenes with no CONSTDATA row) -- recorded, not
        # smoothed over.
        self.assertEqual(scenes[:10], [1, 2, 3, 4, 5, 6, 7, 8, 9, 14])
        self.assertEqual(scenes[10:], [12, 15, 16])

    def test_eleven_rows_have_two_tables_agreeing_on_the_level_gate(self):
        agreeing = [row for row in islands.DESTINATION_ROWS if row.levels_agree]
        self.assertEqual([row.trigger_id for row in agreeing], list(range(152, 162)))
        # The gates themselves, in order: this is the sequence that made the
        # block identifiable in the first place.
        self.assertEqual(
            [row.min_level for row in agreeing],
            [0, 0, 25, 45, 60, 70, 81, 86, 92, 100],
        )

    def test_a_destination_row_has_no_double_click_verb_and_its_neighbours_do(self):
        # Property 3 of the module docstring, asserted against the client
        # table rather than restated: 148-151 and 169-175 are props with a
        # usage verb; 152-167 have none.  This is the property that makes
        # "the client fires it on contact" a live hypothesis at all, so it
        # is the one that must go red if a future re-copy changes the table.
        verb = "ดับเบิ้ลคลิก"
        tips = _tips_by_id()
        for trigger_id in list(range(148, 152)) + list(range(169, 176)):
            with self.subTest(prop=trigger_id):
                self.assertIn(verb, tips[trigger_id])
        for trigger_id in range(152, 168):
            with self.subTest(destination=trigger_id):
                self.assertNotIn(verb, tips[trigger_id])


class TheClassifierSaysWhatItKnowsAndNoMoreTests(unittest.TestCase):
    def test_the_five_ids_r307_actually_captured_are_props_not_islands(self):
        # notes_to_chief/20260903_1901 (R307): five 0x1FB2 frames, ids
        # 40/51/3/57/36.  Round `ufcemz` refuted the reading that these were
        # islands; this test is that refutation held in place.
        for trigger_id, name in (
            (40, "Black Braid Landmine"),
            (51, "Magic Egg"),
            (3, "Seafood Cargo"),
            (57, "Black Charm Demon Flower"),
            (36, "Offer Altar"),
        ):
            with self.subTest(trigger_id=trigger_id):
                self.assertEqual(islands.classify_trigger_id(trigger_id), islands.CLASS_PROP)
                self.assertEqual(islands.trigger_name(trigger_id), name)
                self.assertIsNone(islands.destination_for_trigger_id(trigger_id))

    def test_islands_oceans_props_and_nothing_at_all_each_get_their_own_answer(self):
        self.assertEqual(islands.classify_trigger_id(153), islands.CLASS_ISLAND)
        self.assertEqual(islands.classify_trigger_id(165), islands.CLASS_OCEAN)
        self.assertEqual(islands.classify_trigger_id(169), islands.CLASS_PROP)
        self.assertEqual(islands.classify_trigger_id(9999), islands.CLASS_UNKNOWN)
        self.assertEqual(islands.classify_trigger_id(-1), islands.CLASS_UNKNOWN)

    def test_an_ocean_travel_row_is_named_but_asserts_no_scene(self):
        for trigger_id in islands.OCEAN_TRAVEL_TRIGGER_IDS:
            with self.subTest(trigger_id=trigger_id):
                self.assertIsNotNone(islands.trigger_name(trigger_id))
                self.assertIsNone(islands.destination_for_trigger_id(trigger_id))
                self.assertIn("scene=unknown", islands.describe_trigger_id(trigger_id))

    def test_describe_is_ascii_for_every_id_the_client_table_has(self):
        # The bridge console is cp874 and one name in this table (id 310) is
        # Chinese, which cp874 cannot encode at all.  Every line this module
        # can produce must survive print() there.
        for trigger_id in list(islands.TRIGGER_NAMES) + [9999]:
            line = islands.describe_trigger_id(trigger_id)
            with self.subTest(trigger_id=trigger_id):
                line.encode("ascii")
                line.encode("cp874")

    def test_scene_lookup_goes_both_ways(self):
        self.assertEqual(islands.destination_for_scene_id(2).trigger_id, 153)
        self.assertEqual(islands.destination_for_scene_id(3).trigger_id, 154)
        self.assertIsNone(islands.destination_for_scene_id(126))


class ThisTableIsNotAllowedToClaimTheWireTests(unittest.TestCase):
    def test_only_the_two_rows_the_re_queue_proved_are_marked_proven(self):
        # CLIENT_RE_QUEUE.md: the n_ID -> wire scene_id link is "CANDIDATE,
        # NOT ESTABLISHED", proven for rows 1 and 2 only.  A later round that
        # upgrades a row must cite the ticket that proved it, and this test
        # is what makes that a deliberate act instead of a quiet edit.
        proven = [
            row.trigger_id
            for row in islands.DESTINATION_ROWS
            if row.wire_scene_id_status == "PROVEN"
        ]
        self.assertEqual(proven, [152, 153])
        for row in islands.DESTINATION_ROWS:
            with self.subTest(trigger_id=row.trigger_id):
                self.assertIn(row.wire_scene_id_status, ("PROVEN", "CANDIDATE"))

    def test_bg3001_placements_hold_no_island_row_and_the_module_says_so(self):
        # COO-DECISION 0343 item 2 asked for island rows to be separated from
        # floating objects inside Bg3001.placements.tsv, and required "report
        # that there is no column, do not guess" if they could not be. There
        # is no island row there at all: 38 placements, every one a Mob_Set.
        self.assertEqual(islands.BG3001_PLACEMENT_COUNT, 38)
        self.assertEqual(islands.BG3001_ISLAND_PLACEMENT_COUNT, 0)

    def test_the_module_states_the_nonclaim_coo_0343_item_1_required(self):
        # Guard against the reading COO-DECISION 0343 item 1 withdrew: this
        # module names travel destinations, and its docstring has to keep
        # saying, in words, that it does not assert 0x1FB2 is the docking
        # frame.  A later round that deletes the nonclaim goes red here.
        doc = islands.__doc__ or ""
        self.assertIn("NOT that 0x1FB2 is the docking frame", doc)
        self.assertIn("CANDIDATE", doc)


def _tips_by_id() -> dict[int, str]:
    import csv

    tips: dict[int, str] = {}
    with islands._DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader)
        for row in reader:
            if row and row[0].strip().isdigit():
                tips[int(row[0])] = row[2] if len(row) > 2 else ""
    return tips


if __name__ == "__main__":
    unittest.main()
