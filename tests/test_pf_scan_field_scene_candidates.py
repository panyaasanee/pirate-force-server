"""LANE-B: the field-scene census is reproducible, and its two hard facts hold.

This is not a gameplay test - ``tools/pf_scan_field_scene_candidates.py``
sends nothing and installs nothing.  What it pins is the evidence behind the
BUILD-004 blocker this round found: regenerate-and-diff against the committed
``docs/FIELD_SCENE_CANDIDATES.json`` (the same pattern the generated
``field_mob_tables.py`` is held to), plus the two facts a field-scene decision
depends on: bg0001 (Port Royal, the shipped control) still counts 13, and
scene 278 (Bg1177, the confirmed M2 destination) still counts zero.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_scan_field_scene_candidates.py"
REPORT_PATH = ROOT / "docs" / "FIELD_SCENE_CANDIDATES.json"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_scan_field_scene_candidates", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FieldSceneCandidatesToolShapeTest(unittest.TestCase):
    """Checks that hold with no bridge clone present: the tool and the file."""

    def test_tool_file_exists(self) -> None:
        self.assertTrue(TOOL_PATH.is_file())

    def test_committed_report_is_valid_json_with_the_two_pinned_facts(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="ascii"))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["control"]["scene"], "bg0001")
        self.assertEqual(report["control"]["hostile_placements"], 13)

        by_folder = {c["scene_folder"].lower(): c for c in report["candidates"]}
        self.assertIn("bg0001", by_folder)
        self.assertEqual(by_folder["bg0001"]["hostile_placements"], 13)
        self.assertEqual(by_folder["bg0001"]["english_name"], "Port Royal")

        # The blocker this round found: the confirmed M2 destination is not
        # in the candidate list at all, because its hostile count is zero.
        self.assertNotIn("bg1177", by_folder)

        # The stronger evidence pf-adversary asked for: not just an absence,
        # but scene 278's own registry name, reported unconditionally.
        m2 = report["m2_destination"]
        self.assertEqual(m2["scene_folder"], "Bg1177")
        self.assertEqual(m2["scene_n_id"], 278)
        self.assertEqual(m2["hostile_placements"], 0)
        self.assertEqual(m2["english_name"], "Beach Soccer Field")

    def test_committed_report_is_pure_ascii(self) -> None:
        # Read as raw bytes, not text decoded with encoding="ascii" -- that
        # decode would already raise on a non-ASCII byte before this
        # assertion ever ran, which would make the assertion itself vacuous.
        raw = REPORT_PATH.read_bytes()
        non_ascii = [b for b in raw if b >= 0x80]
        self.assertEqual(non_ascii, [])

    def test_key_raises_on_a_genuine_duplicate_instead_of_keeping_one_silently(
        self,
    ) -> None:
        module = _load_tool()
        rows = [{"n_ID": "31", "s_NAME": "first"}, {"n_ID": "31", "s_NAME": "second"}]
        with self.assertRaises(module.ScanError):
            module._key(rows, "n_ID", "synthetic duplicate for this test")

    def test_scene_census_raises_on_two_resolved_rows_sharing_an_index(self) -> None:
        module = _load_tool()
        # A synthetic MOBS row that resolves as hostile -- no bridge clone
        # needed, this is testing the tool's own dedup ordering, not a real
        # scene's data.
        mobs = {"31": {"s_OUTFIT": "M011_000_002_SP3", "n_RANK": "1", "n_AI_COMBAT": "214"}}
        # Both placement rows resolve, and both claim index 0 -- the exact
        # shape a garbage row must NOT be allowed to shadow silently
        # (pf-adversary finding 3).
        placements = [
            {"index": "0", "template_ids": "31", "x": "0", "y": "0", "z": "0"},
            {"index": "0", "template_ids": "31", "x": "1", "y": "1", "z": "1"},
        ]
        with self.assertRaises(module.DuplicateIndexError):
            module._scene_census(placements, mobs)

    def test_scene_census_does_not_let_an_unresolved_row_shadow_a_real_one(
        self,
    ) -> None:
        module = _load_tool()
        mobs = {"31": {"s_OUTFIT": "M011_000_002_SP3", "n_RANK": "1", "n_AI_COMBAT": "214"}}
        # A row whose template does not resolve in MOBS, sharing an index
        # with a row that DOES resolve as hostile.  Ordering the dedup check
        # after resolution (this round's fix) must still count the real row.
        placements = [
            {"index": "0", "template_ids": "999999999", "x": "0", "y": "0", "z": "0"},
            {"index": "0", "template_ids": "31", "x": "1", "y": "1", "z": "1"},
        ]
        census = module._scene_census(placements, mobs)
        self.assertEqual(census["hostile"], 1)
        self.assertEqual(census["unambiguous"], 1)


@BRIDGE_GAMEDATA.skip_unless_present()
class FieldSceneCandidatesRegenerateAndDiffTest(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_regenerating_reproduces_the_committed_report_byte_for_byte(self) -> None:
        module = _load_tool()
        report = module.scan(GAMEDATA)
        regenerated = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        committed = REPORT_PATH.read_text(encoding="ascii")
        self.assertEqual(
            regenerated, committed,
            "docs/FIELD_SCENE_CANDIDATES.json is stale - regenerate it with "
            "tools/pf_scan_field_scene_candidates.py",
        )

    def test_scene_278_scans_as_zero_hostile_under_the_shipped_tables(self) -> None:
        module = _load_tool()
        placements = module._read_tsv(
            GAMEDATA / "scene" / "Bg1177" / "Bg1177.placements.tsv"
        )
        mobs_path = GAMEDATA / "tables" / "CONSTDATA_TH__MOBS.tsv"
        mobs = module._key(module._read_tsv(mobs_path), "n_ID", str(mobs_path))
        census = module._scene_census(placements, mobs)
        self.assertEqual(
            census["hostile"], 0,
            "scene 278 now has hostile placements - the BUILD-004 blocker "
            "this round reported may be resolved; update the round note "
            "and docs/FIELD_SCENE_CANDIDATES.json rather than this test",
        )

    def test_control_scene_refusal_fires_on_a_tampered_mobs_row(self) -> None:
        module = _load_tool()
        placements = module._read_tsv(
            GAMEDATA / "scene" / "bg0001" / "bg0001.placements.tsv"
        )
        mobs_path = GAMEDATA / "tables" / "CONSTDATA_TH__MOBS.tsv"
        mobs = module._key(module._read_tsv(mobs_path), "n_ID", str(mobs_path))
        # Flip the rank of a template this scene's own roster uses (31,
        # Tornado Eagle -- the same control the roster miner itself checks)
        # to 0, and confirm the census actually moves: proof the predicate
        # reads live data for this scene, not a cached count.
        control_template = "31"
        self.assertIn(control_template, mobs)
        tampered = dict(mobs)
        tampered[control_template] = {**mobs[control_template], "n_RANK": "0"}
        original = module._scene_census(placements, mobs)
        after = module._scene_census(placements, tampered)
        self.assertLess(after["hostile"], original["hostile"])


if __name__ == "__main__":
    unittest.main()
