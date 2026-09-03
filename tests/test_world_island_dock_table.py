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

    def test_eight_rows_have_two_tables_agreeing_on_a_level_NUMBER(self):
        # Corrected twice by pf-adversary (D7).  The first draft said
        # "eleven rows 152..161" in prose while asserting ten ids here, and
        # counted 152/153 as agreements when their tip text carries no
        # number at all (it says "no level limit").  An absence read as a
        # zero is not two tables agreeing.
        agreeing = [
            row for row in islands.DESTINATION_ROWS if row.numeric_level_agreement
        ]
        self.assertEqual([row.trigger_id for row in agreeing], list(range(154, 162)))
        self.assertEqual(
            [row.min_level for row in agreeing], [25, 45, 60, 70, 81, 86, 92, 100]
        )

    def test_the_two_rows_with_no_number_in_their_tip_are_not_counted_as_agreeing(self):
        tips = _tips_by_id()
        for trigger_id in (152, 153):
            row = islands.destination_for_trigger_id(trigger_id)
            with self.subTest(trigger_id=trigger_id):
                self.assertFalse(row.numeric_level_agreement)
                self.assertEqual(row.min_level, 0)
                self.assertNotIn("Lv", tips[trigger_id])
                self.assertIn("ไม่จำกัดเลเวล", tips[trigger_id])

    def test_the_name_match_is_exclusive_to_this_block_and_nothing_else(self):
        # Property 1, the one that actually identifies the block, checked as
        # an EXCLUSIVITY rather than as thirteen lookups: of all 312 trigger
        # rows, only these carry a scene name.  If a future client table
        # gives a prop a scene name, this goes red and the derivation has to
        # be re-argued instead of quietly widening.
        scene_names = {row.name for row in islands.DESTINATION_ROWS}
        matches = sorted(
            trigger_id
            for trigger_id, name in islands.TRIGGER_NAMES.items()
            if name in scene_names
        )
        self.assertEqual(matches, list(range(152, 165)))

    def test_the_no_click_verb_property_is_recorded_with_its_real_base_rate(self):
        # Property 3, DEMOTED (pf-adversary D6).  The first draft asserted it
        # over two hand-picked neighbour windows (148-151, 169-175) that
        # stepped over 147 `Secret Station` and 168 `Shut The Door`, which
        # have no verb either.  Measured across the whole table the property
        # has a 30.8% base rate, so it discriminates almost nothing and must
        # never classify a row on its own.  The block genuinely has none --
        # that part was true -- and this test says both things at once.
        verb = "ดับเบิ้ลคลิก"
        tips = _tips_by_id()
        for trigger_id in range(152, 168):
            with self.subTest(destination=trigger_id):
                self.assertNotIn(verb, tips[trigger_id])
        without = [tid for tid, tip in tips.items() if verb not in tip]
        self.assertEqual(len(without), 96)
        self.assertGreater(len(without) / len(tips), 0.30)
        # The two immediate neighbours the first draft's windows skipped.
        for neighbour in (147, 168):
            with self.subTest(neighbour=neighbour):
                self.assertNotIn(verb, tips[neighbour])
                self.assertEqual(
                    islands.classify_trigger_id(neighbour), islands.CLASS_PROP
                )


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

    def test_the_bg3001_island_cast_is_derived_from_the_module_that_ships_it(self):
        # pf-adversary D1: the first draft of this module asserted that
        # Bg3001.placements.tsv holds NO island row, while
        # world_bg3001_identity.py -- same repo, same pinned sha256 for the
        # same file, already on main -- resolves four of those placements to
        # MAP_ISLAND_01 actors and ships them into scene 126 every boot.
        # Nothing can be allowed to assert that again, so this derives the
        # count and the names from that module rather than trusting a
        # literal here.
        from pirateforce_foundation import world_bg3001_identity as bg3001

        placements = bg3001.shippable_placements()
        island_names = sorted(
            p.identity.name
            for p in placements
            if p.identity.outfit == islands.BG3001_ISLAND_ACTOR_OUTFIT
        )
        self.assertEqual(bg3001.PLACEMENT_COUNT, islands.BG3001_PLACEMENT_COUNT)
        self.assertEqual(len(island_names), islands.BG3001_ISLAND_ACTOR_COUNT)
        self.assertEqual(tuple(island_names), islands.BG3001_ISLAND_ACTOR_NAMES)
        self.assertGreater(len(island_names), 0)

    def test_neither_m2_target_is_in_bg3001s_cast_which_is_the_real_finding(self):
        # The narrower true answer to COO-DECISION 0343 item 2: the file does
        # hold islands, and neither of the two M2 needs is one of them.  That
        # leaves open whether Prison Exile and Spice Paradise are actors this
        # server has never placed or client-side geometry -- raised to COO,
        # deliberately not answered here.
        from pirateforce_foundation import world_bg3001_identity as bg3001

        cast = {p.identity.name for p in bg3001.shippable_placements()}
        for trigger_id in islands.M2_TARGET_TRIGGER_IDS:
            row = islands.destination_for_trigger_id(trigger_id)
            with self.subTest(trigger_id=trigger_id):
                self.assertNotIn(row.name, cast)
        self.assertIs(islands.M2_TARGETS_ABSENT_FROM_BG3001_CAST, True)

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
