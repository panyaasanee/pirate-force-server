"""GM-004: scene id -> GM scene name catalog, pinned to the committed client table."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import scene_catalog


class GmSceneCatalogTests(unittest.TestCase):
    def test_known_scene_ids_from_the_owner_order_letter(self):
        # notes_to_chief 20260826_1630: Port Royal=1, Prison Exile Island=2, Spice Paradise Island=3
        self.assertEqual(scene_catalog.gm_scene_name(1), "Port Royal")
        self.assertEqual(scene_catalog.gm_scene_name(2), "Prison Exile Island")
        self.assertEqual(scene_catalog.gm_scene_name(3), "Spice Paradise Island")

    def test_scene_count_matches_the_committed_table(self):
        self.assertEqual(scene_catalog.SCENE_COUNT, 330)

    def test_unknown_scene_id_raises(self):
        with self.assertRaises(KeyError):
            scene_catalog.gm_scene_name(123456)

    def test_is_known_scene_id(self):
        self.assertTrue(scene_catalog.is_known_scene_id(1))
        self.assertFalse(scene_catalog.is_known_scene_id(123456))

    def test_ship_in_the_sea_scene_ids_share_the_client_scene_name_but_not_the_gm_name(self):
        # s_SCENE_NAME repeats "Ship in the Sea" for many ids; s_GM_SCENE_NAME
        # disambiguates each with a Thai label + numbered suffix, e.g. id 17
        # -> "เรือในทะเล 1(17)" -- the two columns answer different questions.
        ship_ids = [
            n_id
            for n_id, name in scene_catalog.SCENE_ID_TO_NAME.items()
            if name == "Ship in the Sea"
        ]
        self.assertIn(17, ship_ids)
        self.assertIn(18, ship_ids)
        self.assertGreaterEqual(len(ship_ids), 7)
        self.assertEqual(scene_catalog.gm_scene_name(17), "เรือในทะเล 1(17)")
        gm_names_for_ship_ids = {scene_catalog.gm_scene_name(n_id) for n_id in ship_ids}
        self.assertGreater(len(gm_names_for_ship_ids), 1)

    def test_scene_ids_named_finds_repeated_gm_names(self):
        # ids 308-327 all carry the literal GM name "Hidden Island"
        ids = scene_catalog.scene_ids_named("Hidden Island")
        self.assertIn(308, ids)
        self.assertIn(327, ids)
        self.assertGreaterEqual(len(ids), 20)

    def test_blank_rows_in_the_clients_own_table_are_known_but_empty_named(self):
        # scene_name_tip.tsv itself carries four rows (13, 137, 138, 141)
        # where BOTH s_SCENE_NAME and s_GM_SCENE_NAME are blank in the
        # client's own committed table -- not a parsing gap this module
        # introduced. Pinned here because `is_known_scene_id` returning True
        # for a blank-named row is easy to misread as a bug the first time
        # someone reads `gm_scene_name(13) == ""` rather than a fact of the
        # source data: the id has a row (so `warp <its id>` gets no "unknown
        # scene" flag from `commands.describe_warp_target`), it is simply a
        # row the client itself left nameless. Distinct from
        # `test_unknown_scene_id_raises`, which is an id with NO row at all.
        for blank_id in (13, 137, 138, 141):
            with self.subTest(scene_id=blank_id):
                self.assertTrue(scene_catalog.is_known_scene_id(blank_id))
                self.assertEqual(scene_catalog.gm_scene_name(blank_id), "")
                self.assertEqual(scene_catalog.SCENE_ID_TO_NAME[blank_id], "")

    def test_non_sequential_high_ids_present(self):
        # the table's n_ID column is not contiguous 1..330; 997/999 exist too
        self.assertTrue(scene_catalog.is_known_scene_id(997))
        self.assertTrue(scene_catalog.is_known_scene_id(999))


class ResolveGmSceneNameTests(unittest.TestCase):
    """The name -> id direction `warp <scene name>` is built on.

    Every number in this class is a MEASUREMENT of the committed, sha-pinned
    table, not a preference. If the table is ever re-derived and a row moves,
    these die -- which is the point: the resolver's whole safety argument is
    "the table says so".
    """

    def test_the_three_scenes_the_owner_order_letter_names(self):
        # The M2 ladder is worded "island 2 and island 3" and these are the
        # rows those words land on. An operator at the client types the name.
        self.assertEqual(scene_catalog.resolve_gm_scene_name("Port Royal"), (1,))
        self.assertEqual(
            scene_catalog.resolve_gm_scene_name("Prison Exile Island"), (2,)
        )
        self.assertEqual(
            scene_catalog.resolve_gm_scene_name("Spice Paradise Island"), (3,)
        )

    def test_folding_is_case_and_whitespace_insensitive(self):
        # The shipped table pads every cell with spaces, and an operator
        # typing at 1 a.m. does not reproduce a shipped string exactly.
        for typed in (
            "spice paradise island",
            "SPICE PARADISE ISLAND",
            "  Spice   Paradise  Island  ",
        ):
            with self.subTest(typed=typed):
                self.assertEqual(scene_catalog.resolve_gm_scene_name(typed), (3,))

    def test_a_duplicated_name_returns_every_id_and_never_picks_one(self):
        # `Hidden Island` is on twenty scenes in the client's own table. A
        # resolver that returned one of them would send a GM somewhere they
        # did not ask for, and nothing downstream could tell.
        ids = scene_catalog.resolve_gm_scene_name("Hidden Island")
        self.assertEqual(len(ids), 20)
        self.assertEqual(list(ids), sorted(ids))
        self.assertIn(308, ids)
        poseidon = scene_catalog.resolve_gm_scene_name("Poseidon Island")
        self.assertEqual(len(poseidon), 10)

    def test_an_empty_or_blank_query_matches_nothing(self):
        # Four rows (13, 137, 138, 141) carry an empty name in the shipped
        # table. A resolver keyed on the raw string would hand all four back
        # for the empty query -- i.e. `warp ` would be a legal warp to a
        # scene picked at random from four.
        for query in ("", " ", "\t", "   \n  "):
            with self.subTest(query=repr(query)):
                self.assertEqual(scene_catalog.resolve_gm_scene_name(query), ())
        for blank_id in (13, 137, 138, 141):
            with self.subTest(scene_id=blank_id):
                self.assertNotIn(
                    blank_id,
                    [i for ids in scene_catalog._GM_NAME_TO_SCENE_IDS.values() for i in ids],
                )

    def test_the_empty_query_guard_holds_even_if_the_index_ever_carries_one(self):
        # Measured, not assumed: with the index built as it is today, DELETING
        # the `if not key: return ()` line changes no test -- `_build_name_index`
        # already drops empty keys, so the guard has two defences and only one
        # witness. This is that witness. It aims at the guard itself by handing
        # the resolver an index that DOES carry an empty key, which is exactly
        # the state a future edit to `_build_name_index` would create.
        poisoned = dict(scene_catalog._GM_NAME_TO_SCENE_IDS)
        poisoned[""] = (13, 137, 138, 141)
        with mock.patch.object(scene_catalog, "_GM_NAME_TO_SCENE_IDS", poisoned):
            self.assertEqual(scene_catalog.resolve_gm_scene_name(""), ())
            self.assertEqual(scene_catalog.resolve_gm_scene_name("   "), ())
            # and the same index still answers a real name, so the test is not
            # passing because the patch broke the resolver outright
            self.assertEqual(scene_catalog.resolve_gm_scene_name("Port Royal"), (1,))

    def test_an_unknown_name_is_an_empty_tuple_not_an_exception(self):
        self.assertEqual(scene_catalog.resolve_gm_scene_name("Atlantis"), ())

    def test_a_non_str_query_raises_rather_than_matching(self):
        for bad in (2, None, ["Port Royal"], b"Port Royal"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    scene_catalog.resolve_gm_scene_name(bad)

    def test_the_fold_invents_no_ambiguity_the_table_does_not_already_have(self):
        # The safety argument for folding case is that it merges no two
        # DISTINCT shipped names. Measured here rather than asserted: for
        # every folded key, the set of ids it returns must equal the union of
        # the ids of the shipped names that fold to it -- and each such key
        # must come from exactly one distinct shipped spelling.
        spellings: dict[str, set[str]] = {}
        for n_id, _name, gm_name in scene_catalog._ROWS:
            key = scene_catalog._fold_gm_scene_name(gm_name)
            if not key:
                continue
            spellings.setdefault(key, set()).add(gm_name.strip())
        merged = {k: v for k, v in spellings.items() if len(v) > 1}
        self.assertEqual(merged, {}, f"case/space folding merged distinct names: {merged}")

    def test_every_shipped_name_resolves_back_to_the_row_it_came_from(self):
        # Round trip over the WHOLE table, not a sample: no row may be
        # unreachable by its own name (except the four nameless ones).
        unreachable = [
            n_id
            for n_id, _name, gm_name in scene_catalog._ROWS
            if gm_name.strip() and n_id not in scene_catalog.resolve_gm_scene_name(gm_name)
        ]
        self.assertEqual(unreachable, [])

    def test_the_counts_this_lane_prints_to_an_operator_are_the_tables_own(self):
        self.assertEqual(scene_catalog.SCENE_COUNT, 330)
        self.assertEqual(scene_catalog.GM_NAME_COUNT, 293)
        self.assertEqual(
            scene_catalog.GM_NAME_COUNT, len(scene_catalog._GM_NAME_TO_SCENE_IDS)
        )

    def test_every_name_in_the_table_survives_the_console_encoding(self):
        # 209 of the 330 names carry Thai. The bridge console is cp874 (the
        # Thai code page), so today every name encodes -- measured, not
        # assumed. This test is the tripwire for a re-derived table that
        # introduces a name outside cp874: at that moment any code path that
        # echoes a scene name to the console becomes a way to kill it, and
        # whoever re-derives the table must see that here rather than at 1
        # a.m. on the bridge.
        for n_id, _name, gm_name in scene_catalog._ROWS:
            with self.subTest(scene_id=n_id):
                gm_name.encode("cp874")


if __name__ == "__main__":
    unittest.main()
