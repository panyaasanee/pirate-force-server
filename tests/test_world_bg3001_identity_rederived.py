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

WHERE IT LOOKS: ``../pf_bridge/gamedata`` beside this repository, the one
layout the bridge machine and the cloud clones share -- asked through
``tests/pf_preconditions.BRIDGE_GAMEDATA``, which is the single authority
on that question for the eleven modules that already ask it.

WHAT THIS FILE CANNOT DO, SAID BEFORE ANYTHING ELSE, BECAUSE THE GATE IS
THE ONLY EYE THAT CLOSES PULL REQUESTS.  ``.github/workflows/
gate-windows.yml`` checks out ONE repository and will never have
``pf_bridge`` beside it, so on the machine that decides the merge this
class always skips and grades nothing.  pf-adversary measured the cost
this round rather than leaving it implied: with no sibling, five separate
single-value mutations of ``world_bg3001_identity.py`` -- a
``SOURCE_SHA256`` digest replaced with ``0...0ff``, an HP 106 -> 1, a
placement moved 800 units, a ``MOBS.n_ID`` 8001 -> 8002, an island wearing
a ship's outfit -- leave this lane's suite byte-identical to the clean
control at ``115 passed, 6 skipped`` AND leave the skip census printing
``RESULT: PASS``.  So "the mutants are dead" is true of a machine with the
bridge clone beside it, and of no other.  The gate-runnable half of the
digest claim is ``test_world_bg3001_identity.py::
test_the_source_digests_are_pinned``, which this round widened from
"64 hex characters" (``000...00ff`` passed by construction) to also refuse
a degenerate digest -- a fix for one mutant, not for the hole.  Closing
the hole needs a decision this lane may not make alone (a vendored slice
of the six source files, a digest-of-digests committed here, or a second
gate job that clones the sibling); it is the open question in
``pf_bridge/notes_to_chief/20260902_2240_LANE-A-TO-COO-...``.

WHY THE PRECONDITION AND NOT AN ENV VAR (round ``l6at2v``, and it is why
the round before this one never reached ``main``).  The first draft
resolved the root itself, honouring ``$PF_BRIDGE_GAMEDATA`` first, and
wrote a bare ``unittest.skipIf`` with its own prose reason.  On the
Windows gate that is an UNDECLARED SKIP: ``tools/
pf_pytest_precondition_census.py`` counts every skip and demands each one
carry a ``[precondition:<key>]`` token or a pin, so ``skip_census`` went
RED and the merge workflow closed ``pirate-force-server#601`` with the
whole round on it.  This shape has closed pull requests repeatedly and in
more than one lane -- ``docs/PYTEST_SKIP_PINS.json`` names ``#231``
(round ``vyi2ud``), ``#540`` (round ``h6bl53``) and ``#545`` (round
``qtxdpr``) in its own notes, and records rounds ``ctflxc``, ``2vxlx2``,
``y7koj9``, ``szdkgs`` and ``0n9inw`` shipping or converting the same
defect.  A single total is deliberately NOT quoted here: pf-adversary
showed this round's first draft miscounted it in both directions from
those same notes.  Asking the house precondition
instead also closes the false-SKIP window ``pf_preconditions`` documents
on ``BRIDGE_SERIALIZER_TABLE``: a private env var would let this module
RUN on a machine the census believes has nothing, and skip on one it
believes has everything, with the census green either way because it
never saw the token.  One question, one answer, one place.  Nothing here
writes, and nothing here reads the canonical DB.
"""
from __future__ import annotations

import csv
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402
from pirateforce_foundation import world_bg3001_identity as identity  # noqa: E402

#: DERIVED, not retyped (pf-adversary D5, round ``l6at2v``): the guard and
#: the reader must never be able to point at different trees.  The day
#: ``BRIDGE_GAMEDATA`` is repointed -- and its own comments propose naming
#: a file rather than the directory -- a hand-written copy of this path
#: would keep reading the old place with the census still green.
#: ``tests/test_world_scene_folder_on_the_bridge.py`` already derives it
#: this way, for the same reason.
GAMEDATA = BRIDGE_GAMEDATA.paths[0].parent

#: Every file this class opens.  The precondition guards the ``tables/``
#: DIRECTORY, and one of these is NOT under it (pf-adversary D3, measured:
#: a sibling holding a full ``tables/`` and no ``scene/`` made the
#: precondition answer PRESENT, the class run, and ``setUpClass`` die with
#: a raw ``FileNotFoundError`` -- six errors, and a census that reports
#: this key green because a skip is not what happened).  The house rule
#: for that state is ``tests/test_scene_identity_rule.py`` lines 214-221:
#: a clone that has the directory without the file is BROKEN, so it is red
#: rather than skipped -- but red with the missing file NAMED.
_REQUIRED_SOURCES = (
    Path("tables") / "CONSTDATA_TH__CLINE.tsv",
    Path("tables") / "CONSTDATA_TH__MOBS.tsv",
    Path("tables") / "TEXTDATA_TH__MOBS_TIP.tsv",
    Path("tables") / "CONSTDATA_TH__STANDARD_MOB.tsv",
    Path("scene") / "Bg3001" / "Bg3001.placements.tsv",
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
            # NOT a skip: the precondition already said this clone HAS the
            # bridge tables.  A tree that answers yes and then cannot
            # produce the file is broken, and the census must not be able
            # to read that as "declared and pinned".  See _REQUIRED_SOURCES.
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
                    # ~~a non-ASCII MOBS_TIP name is a drop reason~~
                    # STRUCK, round `gx7xtp`: COO-DECISION 20260902_2146
                    # shape 1 ships a cp874-representable name, so the
                    # only drop shape this scene has left is leader 0.
                    # A future non-zero drop must still name a leader the
                    # table really has, and say why in ASCII.
                    self.assertIn(str(leader), self.mobs)
                    self.assertTrue(reason)
                    self.assertTrue(reason.isascii())

    def test_the_thai_name_is_the_tables_own_bytes(self) -> None:
        """Shape 1 of ``COO-DECISION 20260902_2146``, re-derived.

        The pin in ``NAME_CP874_HEX`` is not trusted: it is rebuilt here
        from ``TEXTDATA_TH__MOBS_TIP`` and compared, so a hand-typed hex
        digit cannot put a name on the wire that the table never had.
        """
        for template_id, pinned in sorted(identity.NAME_CP874_HEX.items()):
            with self.subTest(set=template_id):
                row = identity.IDENTITIES[template_id]
                tip = self.tip[str(row.mobs_n_id)]
                source = tip["s_NAME"]
                self.assertFalse(source.isascii())
                self.assertEqual(source.encode("cp874").hex(), pinned)
                self.assertEqual(row.name, source)
                self.assertEqual(
                    identity.evidence_name(row), "name_cp874_hex=%s" % pinned)

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
        second leg's columns have to be MINED and not copied from the
        first - a leg transcribed from its own partner would make the gate
        agree with itself no matter what the table says."""
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
        row, which is not the same fact as having an empty name.  Re-derive
        the answer for every leg the scene's multi-set placements name."""
        for template_id, has_tip in sorted(
            identity.MULTI_SET_LEG_HAS_TIP_ROW.items()
        ):
            with self.subTest(set=template_id):
                leader = int(self.keys[template_id]["n_LEADER_BK1"])
                self.assertEqual(str(leader) in self.tip, has_tip)

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
