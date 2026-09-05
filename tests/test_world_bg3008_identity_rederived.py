"""LANE-A: the Pale Silver Sea crosswalk, re-derived from the committed TSVs.

WHY THIS FILE EXISTS.  ``world_bg3008_identity`` ships 47 hand-checked table
rows and 59 placement rows, and a wrong digit in any of them puts a wrong
actor on a client with every count still agreeing with itself - the defect
``tests/test_world_bg3001_identity_rederived.py`` was written for, on the
sibling scene, after pf-adversary measured ten single-value mutations of
that table leaving the whole lane suite green.  This file is that guard for
scene 305: it re-derives the crosswalk from the bridge's own files and
compares it to the shipped literal FIELD BY FIELD.  It carries one job the
sibling's copy does not: this scene drops NOTHING, so the file that would
notice a drop appearing (or a set silently vanishing from the table while
the counts still agree) is this one.

WHAT IT CANNOT DO, SAID FIRST.  ``.github/workflows/gate-windows.yml``
checks out ONE repository and will never have ``pf_bridge`` beside it, so on
the machine that decides the merge this class SKIPS and grades nothing.  The
gate-runnable half of the claim is ``tests/test_world_bg3008_identity.py``,
which checks the table's internal shape without the sources.  This is the
same split, and the same known hole, the sibling scene's pair carries; it is
recorded here rather than implied.

WHERE IT LOOKS: ``../pf_bridge/gamedata`` beside this repository, asked
through ``tests/pf_preconditions.BRIDGE_GAMEDATA`` - the single authority on
that question for every module that already asks it.
"""
from __future__ import annotations

import csv
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import world_bg3008_identity as identity  # noqa: E402

#: DERIVED, not retyped: the guard and the reader must never be able to
#: point at different trees (pf-adversary D5, round ``l6at2v``, on the
#: sibling scene's own file).
GAMEDATA = BRIDGE_GAMEDATA.paths[0].parent

#: Every file this class opens.  The precondition guards the ``tables/``
#: DIRECTORY and one of these is not under it, so a clone with tables and no
#: ``scene/`` would otherwise die with a raw ``FileNotFoundError`` inside
#: ``setUpClass`` - red, but with nothing named.  House rule
#: (``tests/test_scene_identity_rule.py``): present-but-incomplete is RED
#: with the missing file named, never a skip.
_REQUIRED_SOURCES = (
    Path("tables") / "CONSTDATA_TH__CLINE.tsv",
    Path("tables") / "CONSTDATA_TH__MOBS.tsv",
    Path("tables") / "TEXTDATA_TH__MOBS_TIP.tsv",
    Path("tables") / "CONSTDATA_TH__STANDARD_MOB.tsv",
    Path("scene") / "Bg3008" / "Bg3008.placements.tsv",
)


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


@BRIDGE_GAMEDATA.skip_unless_present()
class TheShippedTableMatchesTheSource(unittest.TestCase):
    """Field by field, against the files ``SOURCE_SHA256`` names."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = GAMEDATA
        missing = [
            relative for relative in _REQUIRED_SOURCES
            if not (cls.root / relative).is_file()
        ]
        if missing:
            raise AssertionError(
                "the bridge gamedata tree at %s is present but incomplete - "
                "this class reads %d files and %d are missing: %s"
                % (cls.root, len(_REQUIRED_SOURCES), len(missing),
                   ", ".join(str(relative) for relative in missing))
            )
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
            cls.root / "scene" / "Bg3008" / "Bg3008.placements.tsv")
        cls.keys = {
            int(row["n_CREATURE_TYPE"]): row
            for row in cls.cline
            if row["n_CLINE_TYPE"] == str(identity.SCENE_CLINE_TYPE)
        }

    def test_every_source_digest_is_the_file_that_is_there(self) -> None:
        """The pin, actually hashed."""
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

    def test_nothing_is_dropped_and_the_sources_agree(self) -> None:
        """This scene's whole shortfall claim, re-derived rather than
        trusted: EVERY first-leg set its placements use resolves through
        CLINE type 3008 to a MOBS row with a real outfit and a
        STANDARD_MOB row for its level.  The sibling scene's version of
        this test proves four named drops; this one proves there are none,
        which is the claim that would rot silently if a table row were lost.
        """
        self.assertEqual(identity.UNRESOLVED, {})
        used = {int(row["template_ids"].split("|")[0])
                for row in self.placements}
        for template_id in sorted(used):
            with self.subTest(set=template_id):
                cline_row = self.keys.get(template_id)
                self.assertIsNotNone(cline_row, "no CLINE row for this set")
                leader = cline_row["n_LEADER_BK1"]
                self.assertNotEqual(int(leader), 0)
                mob = self.mobs.get(leader)
                self.assertIsNotNone(mob, "no MOBS row for this leader")
                self.assertTrue(mob["s_OUTFIT"])
                self.assertIn(mob["n_LEVEL_MIN"], self.standard)
                self.assertIn(template_id, identity.IDENTITIES)

    def test_no_shipped_name_needs_a_cp874_pin_on_this_scene(self) -> None:
        """The membership gate, re-derived.  Every ``MOBS_TIP.s_NAME`` this
        table ships is ASCII, so ``NAME_CP874_HEX`` is empty - and if a
        regeneration ever brings a Thai row in, THIS test goes red rather
        than the name reaching the wire unpinned."""
        self.assertEqual(identity.NAME_CP874_HEX, {})
        for row in identity._RESOLVED_ROWS:
            with self.subTest(set=row[0]):
                source = self.tip.get(str(row[2]), {}).get("s_NAME") or ""
                self.assertTrue(source.isascii(), source)

    def test_the_second_leg_is_real_and_never_shipped(self) -> None:
        for template_id, (cline_row_id, leader) in sorted(
            identity.SECOND_LEG_ONLY.items()
        ):
            with self.subTest(set=template_id):
                cline_row = self.keys[template_id]
                self.assertEqual(int(cline_row["n_ID"]), cline_row_id)
                self.assertEqual(int(cline_row["n_LEADER_BK1"]), leader)
                self.assertNotIn(template_id, identity.IDENTITIES)

    def test_every_second_leg_column_is_the_tables_own(self) -> None:
        """``MULTI_SET_GATE`` compares the legs column by column, so the
        second leg's columns have to be MINED and not copied from the first
        - a leg transcribed from its own partner would make the gate agree
        with itself no matter what the table says."""
        for template_id, row in sorted(
            identity.SECOND_LEG_IDENTITIES.items()
        ):
            with self.subTest(set=template_id):
                cline_row = self.keys[template_id]
                self.assertEqual(int(cline_row["n_ID"]), row.cline_row_id)
                leader = int(cline_row["n_LEADER_BK1"])
                self.assertEqual(leader, row.mobs_n_id)
                mob = self.mobs[str(leader)]
                self.assertEqual(mob["s_OUTFIT"], row.outfit)
                self.assertEqual(int(mob["n_LEVEL_MIN"]), row.level)
                self.assertEqual(int(mob["n_RANK"]), row.rank)
                self.assertEqual(int(mob["n_MOB_USAGE"]), row.mob_usage)
                self.assertEqual(
                    int(self.standard[mob["n_LEVEL_MIN"]]["n_HPMAX"]),
                    row.max_hp)

    def test_the_tip_row_answer_each_leg_carries_is_measured(self) -> None:
        """Condition 2 of the gate turns on whether a leg HAS a MOBS_TIP
        row, which is not the same fact as having an empty name."""
        for template_id, has_tip in sorted(
            identity.MULTI_SET_LEG_HAS_TIP_ROW.items()
        ):
            with self.subTest(set=template_id):
                leader = int(self.keys[template_id]["n_LEADER_BK1"])
                self.assertEqual(str(leader) in self.tip, has_tip)

    def test_the_docstrings_measured_numbers_are_still_true(self) -> None:
        """The counts the module docstring states, from the files."""
        self.assertEqual(len(self.placements), 59)
        self.assertEqual(len(self.keys), 58)
        used = {int(row["template_ids"].split("|")[0])
                for row in self.placements}
        self.assertEqual(len(used), 47)
        self.assertEqual(
            used, set(identity.IDENTITIES) | set(identity.UNRESOLVED))
        self.assertEqual(
            sum(int(row["extra_triple_count"]) for row in self.placements),
            780)
        self.assertEqual(
            sum(1 for row in self.placements
                if int(row["extra_triple_count"])),
            19)
        # The scene's own SCENE_NAME row, since three of this module's
        # constants come from it.
        scene = {
            row["n_ID"]: row
            for row in _rows(
                self.root / "tables" / "CONSTDATA_TH__SCENE_NAME.tsv")
        }[str(identity.SCENE_N_ID)]
        self.assertEqual(scene["s_MODLE_ID"], identity.SCENE_MODEL_ID)
        self.assertEqual(
            int(scene["n_CLINE_TYPE"]), identity.SCENE_CLINE_TYPE)
        self.assertEqual(int(scene["n_SAVE"]), identity.SCENE_SAVE_FLAG)
        self.assertEqual(
            int(scene["n_SCENE_LV"]), identity.SCENE_DECLARED_LEVEL)
        # An ocean panel, like scene 126 - the one column the census half's
        # own docstring leans on when it calls this scene's shape familiar.
        self.assertEqual(int(scene["n_SCENE_TYPE"]), 8)

    def test_no_crew_column_is_set_on_this_cline_block(self) -> None:
        """The NO CREW paragraph, re-derived: 0 of 58 rows carry a crew, and
        exactly one carries back-up leaders this crosswalk drops."""
        crew_columns = [name for name in self.cline[0] if name.startswith(
            "n_CREW")]
        self.assertTrue(crew_columns)
        block = [row for row in self.cline
                 if row["n_CLINE_TYPE"] == str(identity.SCENE_CLINE_TYPE)]
        self.assertEqual(len(block), 58)
        for row in block:
            with self.subTest(cline_row=row["n_ID"]):
                for column in crew_columns:
                    self.assertIn(row[column], ("0", ""))
        backups = sorted(
            row["n_ID"] for row in block
            if row["n_LEADER_BK2"] not in ("0", "")
            or row["n_LEADER_BK3"] not in ("0", "")
        )
        self.assertEqual(backups, ["61610"])


if __name__ == "__main__":
    unittest.main()
