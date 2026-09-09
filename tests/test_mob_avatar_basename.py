"""LANE-B: what leaves this server as a monster's avatar is ONE basename.

ROUND db4o73, executing COO-DECISION 2026-09-08T17:42+07:00 (LANE-B, "the
first token is correct -- hold #1156 and roll bg0002 back").

WHAT CHANGED ON THE WIRE.  Forty of the fifty-two monsters this lane ships in
Bg0002 -- the scene the owner actually stands in -- were sent to the client
with their MOBS ``s_OUTFIT`` CELL as the avatar name, separators and all
(``M001_000_000_N;M001_000_000_SP1``).  After this round those forty send
``M001_000_000_N``: one basename, the form this project's own tables and
LANE-A's identity tables have always carried.

WHAT THIS IS NOT (corrected under pf-adversary D3, and written here because
the first draft of this card got it wrong).  ``RE-296`` result 2
(2026-09-07T20:53) read the client tokenising ITS OWN ``MOBS.s_OUTFIT`` row
and taking index 0.  That is a measurement about the client reading its own
table, NOT about what the client does with the wstr this server writes at
``NPCAttr+0x7C``; the same result records that 8 of 13 ``.avt`` xrefs were
never walked.  So nothing here says a body now draws where none drew before.
The authority for the change is COO-DECISION 2026-09-08T17:42, which rules
that what goes on the wire is always a single basename; the argument behind
it is that "first token" is the only reading of a cell this project has
measured anywhere, while a list is a form no server-side consumer wants.

WHAT IS PINNED HERE, and why each pin is not the same pin twice:

* ``OneRuleTests`` -- the rule itself, on inputs, including the ones that
  would corrupt a legitimate basename if it were written carelessly.
* ``OneDefinitionTests`` -- the roster GENERATOR mines under the very same
  function object the server runs, loaded by path rather than copied.  A
  second copy of this rule is the failure mode the module exists to prevent,
  so it is measured and not asserted in a comment.
* ``NothingShipsACellTests`` -- every placement this lane ships, in every
  registered scene, carries a basename.  This is the standing rule, not a
  bg0002 fact: a future scene mined the old way fails here.
* ``TheRawCellSurvivesTests`` -- rolling back did not throw the cell away.
  Bg0002 keeps every raw cell in a column, and the column agrees with the
  wire column row by row.
* ``TheGatesRefuseTests`` -- both refusals fire, on the two paths that reach
  the client: a stale table entering through the roster parser, and a
  hand-built monster entering at composition.

NON-CLAIMS.  Nothing here claims the client draws these forty bodies: that is
a screen fact and it needs a boot (the GT letter this round writes).  Nothing
here claims the basenames name files that ship -- no test on this side of the
wire can open the client's ``.avt`` directory.  Nothing here re-opens WHO is
an enemy: that is ``n_RANK`` plus ``n_AI_COMBAT`` and nothing else (PANYA
1313), and this round did not move one row in or out of the roster.
"""

from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_tables_bg0002  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_avatar_basename  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"

#: Bg0002 rows the rollback actually moved.  MEASURED on the regenerated
#: module (it is ``len(OUTFIT_CELL_FOR_PLACEMENT)``), pinned as a literal so
#: that a regeneration which silently drops the correction fails here instead
#: of agreeing with itself.
EXPECTED_BG0002_LIST_CELLS = 40

#: Placements this lane ships across every registered scene, at the time this
#: card was written.  A number, not a bound: if a scene is added the count
#: moves and the reader is sent to look at what was added.
EXPECTED_SHIPPED_PLACEMENTS = 145


class OneRuleTests(unittest.TestCase):
    """The rule, on the inputs that decide whether it is written correctly."""

    def test_a_list_cell_becomes_its_first_token(self) -> None:
        self.assertEqual(
            mob_avatar_basename.avatar_basename(
                "M001_000_000_N;M001_000_000_SP1"),
            "M001_000_000_N",
        )

    def test_a_basename_is_returned_unchanged(self) -> None:
        # The 105 rows this lane already shipped correctly must not move.
        self.assertEqual(
            mob_avatar_basename.avatar_basename("M011_000_000_SP1"),
            "M011_000_000_SP1",
        )

    def test_every_separator_re296_named_is_refused_and_split(self) -> None:
        for cell, expected in (
            ("A;B", "A"),
            ("A\tB", "A"),
            ("A B", "A"),
            ("A;B\tC D", "A"),
        ):
            with self.subTest(cell=cell):
                self.assertEqual(
                    mob_avatar_basename.avatar_basename(cell), expected)
                self.assertTrue(mob_avatar_basename.has_separator(cell))

    def test_an_empty_cell_is_empty_and_not_an_error(self) -> None:
        # Callers upstream already read '' as "this row ships no avatar" and
        # clear the NPCAttr preset bit for it; turning that into an exception
        # here would refuse rows the roster never had a problem with.
        for cell in ("", "   ", "\t"):
            with self.subTest(cell=cell):
                self.assertEqual(mob_avatar_basename.avatar_basename(cell), "")

    def test_a_non_string_cell_is_a_type_error_not_a_silent_pass(self) -> None:
        with self.assertRaises(TypeError):
            mob_avatar_basename.avatar_basename(None)


class OneDefinitionTests(unittest.TestCase):
    """The generator mines under the function the server runs."""

    def test_the_miner_loads_this_module_rather_than_copying_it(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "pf_mine_scene_mob_roster_for_this_test", TOOL_PATH)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        # Not "they agree on these inputs" -- that is what a copy would also
        # do until it drifted.  The miner must be running THIS source file.
        self.assertEqual(
            Path(tool._AVATAR_RULE_PATH).resolve(),
            (SRC / "pirateforce_foundation" / "mob_avatar_basename.py"
             ).resolve(),
        )
        self.assertEqual(
            tool.avatar_basename("M001_000_000_N;M001_000_000_SP1"),
            mob_avatar_basename.avatar_basename(
                "M001_000_000_N;M001_000_000_SP1"),
        )

    # THE OTHER HOLDERS OF THE SAME READING, PINNED BY CENSUS RATHER THAN
    # SKIPPED BY NAME (pf-adversary D9, round db4o73).  The first version of
    # this test excluded LANE-A's identity tables BY NAME and then claimed
    # this module was "the single dispenser of the rule".  That sentence was
    # wider than the measurement: those files hold the same first-token
    # reading in a dozen more places, and a name-shaped skip cannot tell a
    # thirteenth from the twelve.  So they are still not this lane's to
    # refactor -- but they are COUNTED.  A new holder appearing anywhere,
    # including inside LANE-A, turns this test red with the file that grew.
    #
    # Measured on round vavm4h over src/pirateforce_foundation/**/*.py with
    # the idiom set below: 15 files, 26 lines.  Nothing in this lane's own
    # files is in it, which is the claim this lane is actually entitled to
    # make: LANE-B has one dispenser, and the rest of the tree's copies are
    # enumerated instead of waved at.
    OTHER_HOLDERS_OF_THE_READING = {
        "world_bg0003_identity.py": 2,
        "world_bg0004_identity.py": 2,
        "world_bg0005_identity.py": 2,
        "world_bg0006_identity.py": 2,
        "world_bg0007_identity.py": 2,
        "world_bg0008_identity.py": 2,
        "world_bg0009_identity.py": 2,
        "world_bg0010_identity.py": 2,
        "world_bg0011_identity.py": 2,
        "world_bg0015_identity.py": 2,
        "world_bg1001_identity.py": 1,
        "world_bg3001_identity.py": 1,
        "world_bg3007_identity.py": 1,
        "world_bg3008_identity.py": 1,
        "world_bg4001_identity.py": 2,
    }

    # D9's second half: the old grep matched the literal text ``split(';')``
    # and nothing else, so ``partition(';')[0]`` -- the same reading, spelled
    # differently -- walked straight past it.  Every idiom that takes a first
    # token off a ';' is matched now.  ``rsplit`` is in the set although it
    # takes the LAST token: a file that reaches for it on an outfit cell is
    # applying some reading of this rule and this test wants to see it.
    FIRST_TOKEN_IDIOMS = (
        "split(';')", 'split(";")',
        "partition(';')", 'partition(";")',
        "rsplit(';')", 'rsplit(";")',
    )

    def _census_of_the_reading(self) -> dict:
        """Every file outside this module that reads an outfit cell on ';'.

        ``;`` is a separator in more than one of this game's tables -- the AI
        rule strings in ``mob_ai_rules`` split on it too, and those have
        nothing to do with avatars -- so a line counts only when an avatar
        word sits on it, which is what a second copy of THIS rule looks like.
        """
        avatar_words = ("outfit", "preset", "avatar", ".avt")
        census: dict = {}
        for path in sorted((SRC / "pirateforce_foundation").rglob("*.py")):
            if path.name == "mob_avatar_basename.py":
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("*"):
                    continue
                if not any(idiom in line for idiom in self.FIRST_TOKEN_IDIOMS):
                    continue
                if any(word in line.lower() for word in avatar_words):
                    census[path.name] = census.get(path.name, 0) + 1
        return census

    def test_this_lane_holds_one_definition_of_the_rule(self) -> None:
        census = self._census_of_the_reading()
        in_this_lane = {
            name: count for name, count in census.items()
            if name not in self.OTHER_HOLDERS_OF_THE_READING
        }
        self.assertEqual(
            in_this_lane, {},
            "a second copy of the avatar rule appeared outside "
            "mob_avatar_basename.py: %s" % sorted(in_this_lane),
        )

    def test_the_other_holders_of_the_reading_are_counted_not_skipped(
            self) -> None:
        census = self._census_of_the_reading()
        counted = {
            name: count for name, count in census.items()
            if name in self.OTHER_HOLDERS_OF_THE_READING
        }
        self.assertEqual(
            counted, self.OTHER_HOLDERS_OF_THE_READING,
            "the census of files outside this lane that hold the same "
            "first-token reading changed.  This test does not forbid that "
            "-- those are LANE-A's files -- it forbids it happening "
            "silently.  Re-measure, update the census, and say in the round "
            "file which file grew or lost a copy.",
        )

    def test_the_census_would_see_a_partition_spelling(self) -> None:
        # The mutant D9 named: the same reading spelled with ``partition``.
        # Written as a check on the matcher itself rather than on a file, so
        # it stays true when no file in the tree spells it that way.
        line = "        preset = cell.partition(';')[0]"
        self.assertTrue(
            any(idiom in line for idiom in self.FIRST_TOKEN_IDIOMS),
            "partition(';') is the same reading and must be matched",
        )
        old_pattern_only = "split(';')" in line or 'split(";")' in line
        self.assertFalse(
            old_pattern_only,
            "this line is exactly the one the pre-vavm4h grep missed; if it "
            "now matches the old pattern the mutant has stopped being one",
        )


class NothingShipsACellTests(unittest.TestCase):
    """Every shipped placement, every registered scene, one basename."""

    def test_no_registered_scene_ships_a_list_cell_on_the_wire(self) -> None:
        shipped = 0
        offenders = []
        for scene in field_mobs.live_scenes():
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            for row in module.SHIPPED_PLACEMENTS:
                shipped += 1
                preset = row[5]
                if mob_avatar_basename.has_separator(preset):
                    offenders.append((scene, row[0], preset))
        self.assertEqual(
            offenders, [],
            "these placements would send an s_OUTFIT cell to the client: %s"
            % offenders,
        )
        self.assertEqual(
            shipped, EXPECTED_SHIPPED_PLACEMENTS,
            "the number of placements this lane ships moved; re-read what "
            "was added before moving this pin",
        )

    def test_the_roster_loader_returns_basenames_for_every_scene(self) -> None:
        # The table is one thing and what load_roster hands downstream is
        # another; this walks the second one, through the real parser.
        for scene in field_mobs.live_scenes():
            with self.subTest(scene=scene):
                for mob in field_mobs.load_roster(scene=scene):
                    self.assertFalse(
                        mob_avatar_basename.has_separator(mob.visual_preset),
                        "%s placement %d loads a cell, not a basename"
                        % (scene, mob.placement_index),
                    )


class TheRawCellSurvivesTests(unittest.TestCase):
    """Rolling back kept the cell; it just took it off the wire."""

    def test_bg0002_carries_every_cell_it_normalised(self) -> None:
        cells = field_mob_tables_bg0002.OUTFIT_CELL_FOR_PLACEMENT
        self.assertEqual(len(cells), EXPECTED_BG0002_LIST_CELLS)
        presets = {row[0]: row[5]
                   for row in field_mob_tables_bg0002.SHIPPED_PLACEMENTS}
        for index, cell in cells.items():
            with self.subTest(placement=index):
                self.assertIn(index, presets)
                self.assertTrue(mob_avatar_basename.has_separator(cell))
                self.assertEqual(
                    mob_avatar_basename.avatar_basename(cell),
                    presets[index],
                    "the raw column and the wire column disagree at "
                    "placement %d" % index,
                )

    def test_the_column_covers_exactly_the_rows_that_moved(self) -> None:
        # A row absent from the raw column is a row whose cell WAS already a
        # basename.  Measured, so the column cannot quietly become partial.
        cells = field_mob_tables_bg0002.OUTFIT_CELL_FOR_PLACEMENT
        for row in field_mob_tables_bg0002.SHIPPED_PLACEMENTS:
            if row[0] in cells:
                continue
            with self.subTest(placement=row[0]):
                self.assertFalse(
                    mob_avatar_basename.has_separator(row[5]))

    def test_no_scene_module_without_list_cells_grew_the_column(self) -> None:
        # The emission condition, from the other side: a module carrying the
        # column must have something to put in it.
        for scene in field_mobs.live_scenes():
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            cells = getattr(module, "OUTFIT_CELL_FOR_PLACEMENT", None)
            with self.subTest(scene=scene):
                if cells is None:
                    continue
                self.assertTrue(cells)


class TheGatesRefuseTests(unittest.TestCase):
    """Both paths to the client refuse a cell, and say which row it was."""

    def _bg0002_row_as_list(self) -> list:
        rows = list(field_mob_tables_bg0002.SHIPPED_PLACEMENTS)
        return rows

    def test_the_roster_parser_refuses_a_stale_generated_table(self) -> None:
        rows = self._bg0002_row_as_list()
        index = rows[0][0]
        poisoned = list(rows[0])
        poisoned[5] = "M001_000_000_N;M001_000_000_SP1"
        rows[0] = tuple(poisoned)

        class StaleModule:
            SCENE = field_mob_tables_bg0002.SCENE
            SHIPPED_PLACEMENTS = rows

        with self.assertRaises(field_mobs.FieldMobContractError) as caught:
            field_mobs._parse_hostile_placements(StaleModule)
        self.assertIn(str(index), str(caught.exception))
        self.assertIn("M001_000_000_N;M001_000_000_SP1",
                      str(caught.exception))

    def test_composition_refuses_a_hand_built_monster(self) -> None:
        # A FieldMob built in code never passes the parser, so the parser's
        # gate alone would not cover this path.  This is the reason there are
        # two gates and not one.
        #
        # ROUND db4o73, pf-adversary D2: the first draft of this test called
        # ``refuse_list_cell`` directly, so deleting the call site inside
        # ``hostile_npc_attr`` left the whole suite green while the second
        # gate was gone.  It now composes a real body through the real
        # function, which is the only thing that pins the CALL SITE rather
        # than the predicate.
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        clean = field_mobs.load_roster(scene=field_mob_tables_bg0002.SCENE)[0]
        poisoned = dataclasses.replace(
            clean, visual_preset="M001_000_000_N;M001_000_000_SP1")
        # The control: the same monster with its real basename composes.
        self.assertTrue(field_mobs.hostile_npc_attr(legacy, clean))
        with self.assertRaises(
                mob_avatar_basename.AvatarCellOnTheWireError) as caught:
            field_mobs.hostile_npc_attr(legacy, poisoned)
        self.assertIn(str(clean.placement_index), str(caught.exception))

    def test_the_gate_does_not_normalise_behind_the_callers_back(self) -> None:
        # Deliberate: a silent trim would leave a stale table shipping for
        # another round with nothing to show for it.
        self.assertEqual(
            mob_avatar_basename.refuse_list_cell("M011_000_000_SP1",
                                                 what="a row"),
            "M011_000_000_SP1",
        )


if __name__ == "__main__":
    unittest.main()
