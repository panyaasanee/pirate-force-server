"""LANE-A: the Atlantis crosswalk, re-derived from the committed TSVs.

WHY THIS FILE EXISTS, AND IT IS A DEFECT REPORT ABOUT ELEVEN MODULES, NOT
ONE.  Every identity crosswalk this lane has shipped carries a
``SOURCE_SHA256`` block naming the six gamedata files its rows came from --
and nothing in this repository has ever hashed anything against it.
pf-adversary measured what that costs on this round's own table (round
``4uztfj``): TEN single-value mutations of ``_RESOLVED_ROWS`` and
``_PLACEMENT_ROWS`` -- a wrong ``MOBS.n_ID`` on the wire, an island
wearing a ship's model, a boss at 1 HP, a placement moved 800 units, and a
``SOURCE_SHA256`` digest replaced with ``000...00ff`` -- all left the whole
lane suite green.  ``bodies=ok`` in the census console line cannot catch
any of them: it compares the composer's own bytes against its own counts.

WHAT CHANGES HERE.  The gamedata tables are not in THIS repository, but
they are committed in the bridge repository next to it, which is where the
mining was done and where the Windows gate runs.  So this file re-derives
the crosswalk from those files when they are reachable and compares it to
the shipped literal FIELD BY FIELD -- and skips, loudly and by name, when
they are not.  A skip is honest; a green suite that never opened the
source is not.

WHERE IT LOOKS: ``tests/pf_preconditions.BRIDGE_GAMEDATA`` -- the house
answer to "what does this clone not have", NOT a bare ``skipUnless`` of
this file's own.  A bare one is what the Windows gate rejected this round
("UNDECLARED SKIP"): Panya's 2026-08-20 ruling is that every skip carries
a ``[precondition:<key>]`` token and a pinned count, so a real test cannot
drift into the skip pile unseen.  This file's six skips are pinned in
``docs/PYTEST_SKIP_PINS.json`` under that key.  ``$PF_BRIDGE_GAMEDATA`` is
still honoured for a checkout that keeps the bridge somewhere else, and
when it points at real tables the guard is a no-op and every assertion
below runs at full strength.  Nothing here writes, and nothing here reads
the canonical DB.
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import world_bg3001_identity as identity  # noqa: E402


def _gamedata_root() -> Path | None:
    """The tables, from the env override or the house precondition's path."""
    named = os.environ.get("PF_BRIDGE_GAMEDATA")
    candidates = [Path(named)] if named else []
    # The precondition names ``<sibling>/pf_bridge/gamedata/tables``; this
    # file wants the directory above it, so the scene folder resolves too.
    candidates.extend(path.parent for path in BRIDGE_GAMEDATA.paths)
    for candidate in candidates:
        if (candidate / "tables" / "CONSTDATA_TH__CLINE.tsv").is_file():
            return candidate
    return None


GAMEDATA = _gamedata_root()


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


@BRIDGE_GAMEDATA.skip_unless_present()
class TheShippedTableMatchesTheSource(unittest.TestCase):
    """Field by field, against the files ``SOURCE_SHA256`` names."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = GAMEDATA
        cls.cline = _rows(cls.root / "tables" / "CONSTDATA_TH__CLINE.tsv")
        cls.mobs = {
            row["n_ID"]: row
            for row in _rows(cls.root / "tables" / "CONSTDATA_TH__MOBS.tsv")
        }
        cls.tip = {
            row["n_ID"]: row
            for row in _rows(cls.root / "tables" / "TEXTDATA_TH__MOBS_TIP.tsv")
        }
        cls.standard = {
            row["n_ID"]: row
            for row in _rows(
                cls.root / "tables" / "CONSTDATA_TH__STANDARD_MOB.tsv")
        }
        cls.placements = _rows(
            cls.root / "scene" / "Bg3001" / "Bg3001.placements.tsv")
        cls.keys = {
            int(row["n_CREATURE_TYPE"]): row
            for row in cls.cline
            if row["n_CLINE_TYPE"] == str(identity.SCENE_CLINE_TYPE)
        }

    def test_every_source_digest_is_the_file_that_is_there(self) -> None:
        """The pin, actually hashed.  ``000...00ff`` used to pass."""
        for relative, digest in sorted(identity.SOURCE_SHA256.items()):
            with self.subTest(path=relative):
                path = self.root / relative.split("gamedata/", 1)[1]
                self.assertTrue(path.is_file(), path)
                measured = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(measured, digest)

    def test_every_shipped_row_matches_the_table_chain(self) -> None:
        for row in identity._RESOLVED_ROWS:
            (template_id, cline_row_id, mobs_n_id, outfit, name, title,
             level, rank, max_hp, mob_usage) = row
            with self.subTest(set=template_id):
                cline_row = self.keys.get(template_id)
                self.assertIsNotNone(cline_row, "no CLINE row for this set")
                self.assertEqual(int(cline_row["n_ID"]), cline_row_id)
                leader = cline_row["n_LEADER_BK1"]
                self.assertEqual(int(leader), mobs_n_id)
                mob = self.mobs.get(leader)
                self.assertIsNotNone(mob, "no MOBS row for this leader")
                self.assertEqual(mob["s_OUTFIT"], outfit)
                self.assertEqual(int(mob["n_LEVEL_MIN"]), level)
                self.assertEqual(int(mob["n_RANK"]), rank)
                self.assertEqual(int(mob["n_MOB_USAGE"]), mob_usage)
                tip = self.tip.get(leader, {})
                self.assertEqual(tip.get("s_NAME") or "", name)
                self.assertEqual(tip.get("s_TITLE") or "", title)
                standard = self.standard.get(mob["n_LEVEL_MIN"], {})
                self.assertEqual(int(standard["n_HPMAX"]), max_hp)

    def test_every_placement_row_matches_the_scene_file(self) -> None:
        self.assertEqual(len(self.placements), identity.PLACEMENT_COUNT)
        instances: dict[int, int] = {}
        for source, shipped in zip(self.placements, identity._PLACEMENT_ROWS):
            index, template_id, mm_instance, x, y, z = shipped
            with self.subTest(placement=index):
                self.assertEqual(int(source["index"]), index)
                legs = source["template_ids"].split("|")
                self.assertEqual(int(legs[0]), template_id)
                if len(legs) > 1:
                    self.assertEqual(
                        identity.MULTI_SET_PLACEMENTS[index],
                        source["template_ids"])
                instances[template_id] = instances.get(template_id, 0) + 1
                self.assertEqual(mm_instance, instances[template_id])
                self.assertEqual(float(source["x"]), x)
                self.assertEqual(float(source["y"]), y)
                self.assertEqual(float(source["z"]), z)
                self.assertEqual(
                    int(source["extra_triple_count"]),
                    identity.EXTRA_TRIPLES_NOT_SHIPPED.get(index, 0))

    def test_every_dropped_set_is_dropped_for_the_reason_given(self) -> None:
        for template_id, (cline_row_id, leader, reason) in sorted(
            identity.UNRESOLVED.items()
        ):
            with self.subTest(set=template_id):
                cline_row = self.keys[template_id]
                self.assertEqual(int(cline_row["n_ID"]), cline_row_id)
                self.assertEqual(int(cline_row["n_LEADER_BK1"]), leader)
                if leader == 0:
                    self.assertNotIn(str(leader), self.mobs)
                    self.assertIn("leader 0", reason)
                else:
                    tip = self.tip.get(str(leader), {})
                    self.assertFalse((tip.get("s_NAME") or "").isascii())
                    self.assertIn("Thai", reason)

    def test_the_second_leg_is_real_and_never_shipped(self) -> None:
        for template_id, (cline_row_id, leader) in sorted(
            identity.SECOND_LEG_ONLY.items()
        ):
            with self.subTest(set=template_id):
                cline_row = self.keys[template_id]
                self.assertEqual(int(cline_row["n_ID"]), cline_row_id)
                self.assertEqual(int(cline_row["n_LEADER_BK1"]), leader)
                self.assertNotIn(template_id, identity.IDENTITIES)

    def test_the_docstrings_measured_numbers_are_still_true(self) -> None:
        """The counts the module docstring states, re-derived here so a
        paragraph cannot drift away from the file it describes."""
        type_rows = [
            row for row in self.cline
            if row["n_CLINE_TYPE"] == str(identity.SCENE_CLINE_TYPE)
        ]
        self.assertEqual(len(type_rows), 56)
        self.assertEqual(len(self.keys), 56)
        crew_columns = [
            column for column in type_rows[0] if column.startswith("n_CREW")
        ]
        self.assertTrue(crew_columns)
        for row in type_rows:
            with self.subTest(cline_row=row["n_ID"]):
                for column in crew_columns:
                    self.assertIn((row.get(column) or "0"), ("0", ""))
        self.assertEqual(
            sum(identity.EXTRA_TRIPLES_NOT_SHIPPED.values()), 814)
        self.assertEqual(len(identity.EXTRA_TRIPLES_NOT_SHIPPED), 22)


if __name__ == "__main__":
    unittest.main()
