"""The control a generated roster module NAMES must be one that READS it.

WHY THIS FILE EXISTS.  pf-adversary, round `r6isy5b`, finding D14: every
module `tools/pf_mine_scene_mob_roster.py` emits carried the sentence

    "The executable control on this data is the roster loader's own
    assert_frozen_controls, which holds these rows against
    world_port_royal_identity's independently mined crosswalk table inside
    this repository."

stamped by the generator onto all six scenes.  It is true for bg0001 and
false for the other five: that function calls `load_roster()` with NO
argument, which reads the bg0001 table module by name -- its `IDENTITY_RULE`,
its `SET_NUMBER_FOR_PLACEMENT`, its per-placement rule split -- and has never
touched a sibling scene's table.

That round recorded the finding as debt rather than paying it, because the
sentence lives in generated code and paying it means regenerating all six
modules.  Round `hor2lh` regenerates them; this file is what stops the claim
coming back, and its four checks are shaped by what pf-adversary got PAST the
first draft of it, which was three mutants in a row:

* an appended sentence in the generator's template, six modules untouched --
  green.  So the drift check is no longer "the phrases are present" but
  BLOCK EQUALITY: the delimited provenance block in every shipped module must
  equal the generator's own, character for character.
* a brand-new false claim appended to ONE module -- green, for the same
  reason.  Same fix.
* a seventh scene, born from a pre-correction copy -- green, because the
  module list was hand-written.  The list is now derived from the loader's
  own scene registry, and a module the registry does not know about is a
  failure rather than a silent skip.

AND THE SHAPE THE BEHAVIOURAL HALF HAD TO CHANGE TO (pf-adversary, D4).  The
first draft asserted that a sibling scene's identity can be wrong and the
control still passes -- which is the defect, pinned as a requirement, so the
day somebody widens the control to every scene the suite goes red in five
places for the GOOD outcome.  `tests/test_world_bg0015_identity.py` already
wrote that rule down: "asserting a disagreement that no longer exists is a
red that means 'the good outcome happened'".  So the test below measures
which scenes the control actually reaches and requires the SHIPPED COMMENT TO
AGREE WITH THE MEASUREMENT.  Widening the control is green the moment the
comment is regenerated to say so; what stays red is a table whose provenance
block claims a control that does not read it, which is the whole subject.
"""

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs                    # noqa: E402
from pirateforce_foundation import field_mob_tables              # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy     # noqa: E402


GENERATOR = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
TABLES_DIR = ROOT / "src" / "pirateforce_foundation"

BLOCK_BEGIN = "# --- PROVENANCE BLOCK BEGIN"
BLOCK_END = "# --- PROVENANCE BLOCK END"

#: The sentence D14 named, kept whole so the tests below can prove it is
#: still present AND struck rather than quietly deleted -- this project
#: strikes history, it does not remove it.
WITHDRAWN_CLAIM = (
    "The executable control on this data is the roster loader's own\n"
    "# assert_frozen_controls, which holds these rows against\n"
    "# world_port_royal_identity's independently mined crosswalk table "
    "inside this\n"
    "# repository."
)

#: The loader module's own name must NOT appear in a generated table.
#:
#: `tests/test_field_mobs.py::test_it_declares_itself_shippable_and_installs_
#: nothing` lists every file under `src/` whose TEXT mentions that module and
#: holds the list against a pinned one, so a new importer cannot appear
#: without the wiring letter being rewritten.  The first cut of this round's
#: correction named the module in the comment and put all six generated data
#: tables -- which import nothing at all -- into that list: six red tests for
#: a comment.  The correction names the FUNCTION instead, which is unique in
#: this repository, and this constant is what stops the module name coming
#: back with the next edit.
LOADER_MODULE_NAME = "field_" + "mobs"

#: What the shipped provenance block says about reach.  Read by the
#: measurement test below, not by a human comparing two paragraphs.
CLAIMS_SIBLINGS_ARE_OUT_OF_REACH = (
    "it is TRUE FOR bg0001 AND FALSE\n# FOR EVERY OTHER SCENE"
)

#: bg0001's shipped rows, digested WITHOUT the comment block.
#:
#: pf-adversary D5: the five sibling test files pin bg0001 by whole-FILE hash,
#: so a round that changes a row and a comment together can re-pin them and
#: say "only the comment moved" -- and on the Windows gate, where the
#: byte-for-byte regenerate tests skip for want of a bridge clone, nothing
#: contradicts it.  This digest covers the DATA only, so that claim now has a
#: control that runs everywhere.  Recompute with:
#:
#:   hashlib.sha256(repr(field_mob_tables.SHIPPED_PLACEMENTS).encode("ascii")
#:                  ).hexdigest()
BG0001_SHIPPED_ROWS_SHA256 = (
    "b583a252dc0923a8d2249f79e55fd64659a69266e7198f4177c1ccb30b068fb3"
)


def _generated_modules():
    """Every scene table the loader can reach, from ITS registry not a list.

    A hand-written tuple is what let a seventh scene walk in carrying the
    withdrawn sentence unstruck (pf-adversary, D3).  Reading the loader's own
    registry means a scene that exists as far as production is concerned is
    covered here by construction.
    """
    modules = dict(field_mobs._SCENE_TABLE_MODULES)
    if not modules:
        raise AssertionError("the loader registers no scene table modules")
    return modules


def _module_text(module):
    return Path(module.__file__).read_text(encoding="ascii")


def _provenance_block(text, what):
    """The delimited block, or a failure naming what was missing."""
    if text.count(BLOCK_BEGIN) != 1 or text.count(BLOCK_END) != 1:
        raise AssertionError(
            "%s must carry exactly one provenance block (found %d begin, %d "
            "end markers)" % (what, text.count(BLOCK_BEGIN),
                              text.count(BLOCK_END)))
    start = text.index(BLOCK_BEGIN)
    end = text.index(BLOCK_END)
    return text[start:end + len(BLOCK_END)]


def _with_a_wrong_identity(rows):
    """``rows`` with the first row's template id and name replaced.

    ``SHIPPED_PLACEMENTS`` is what ``_parse_hostile_placements`` actually
    reads (it prefers it over ``HOSTILE_PLACEMENTS``), so this is the list a
    drifted regeneration would land in.  Column 1 is the resolved
    ``MOBS.n_ID`` and column 6 the displayed name -- the exact two values the
    bg0001 control holds against LANE-A's crosswalk.  65535 is inside the u16
    the shape validator allows, so a refusal here is a control speaking, not
    a parser.
    """
    mutated = list(rows)
    row = list(mutated[0])
    row[1] = 65535
    row[6] = "NOT A MONSTER IN ANY TABLE"
    mutated[0] = tuple(row)
    return mutated


def _control_reaches(legacy, module):
    """True when ``assert_frozen_controls`` notices a wrong identity here."""
    shipped = module.SHIPPED_PLACEMENTS
    module.SHIPPED_PLACEMENTS = _with_a_wrong_identity(shipped)
    try:
        field_mobs.assert_frozen_controls(legacy)
        return False
    except field_mobs.FieldMobContractError:
        return True
    finally:
        module.SHIPPED_PLACEMENTS = shipped


class WhatTheControlReachesTests(unittest.TestCase):
    """The finding, executed -- and executed in a shape that can be closed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_it_passes_on_the_shipped_tables(self) -> None:
        """The control is live, so the measurements below mean something."""
        field_mobs.assert_frozen_controls(self.legacy)

    def test_bg0001_is_reached(self) -> None:
        """The positive control, and it stays true if the reach is widened.

        Measured message:
        ``placement 103 ships n_ID 65535, the crosswalk says 916``.
        """
        self.assertTrue(_control_reaches(self.legacy, field_mob_tables))

    def test_every_module_says_what_the_measurement_says(self) -> None:
        """The comment and the code agree, whichever way the code goes.

        Today every sibling is out of reach and every block says so.  Widen
        the control and this stays green the moment the blocks are
        regenerated -- it never asks for the gap to be preserved.
        """
        reached = {
            scene: _control_reaches(self.legacy, module)
            for scene, module in _generated_modules().items()
        }
        self.assertTrue(
            reached[field_mob_tables.SCENE],
            "bg0001 must be reached; the rest of this test reads against it",
        )
        siblings_out_of_reach = not any(
            hit for scene, hit in reached.items()
            if scene != field_mob_tables.SCENE
        )
        for scene, module in _generated_modules().items():
            with self.subTest(scene=scene):
                block = _provenance_block(_module_text(module), scene)
                self.assertEqual(
                    CLAIMS_SIBLINGS_ARE_OUT_OF_REACH in block,
                    siblings_out_of_reach,
                    "the provenance block and the measured reach of "
                    "assert_frozen_controls disagree: measured "
                    "out-of-reach=%r.  If the control was widened on "
                    "purpose, regenerate the six modules so the comment says "
                    "so." % (siblings_out_of_reach,),
                )


class EveryGeneratedModuleCarriesTheGeneratorsBlockTests(unittest.TestCase):
    """Block equality, because presence checks did not survive review."""

    def test_the_registry_covers_every_generated_table_on_disk(self) -> None:
        """A seventh scene cannot arrive unnoticed.

        `_generated_modules` reads the loader's registry; this reads the
        directory.  A file that exists and is not registered is either a
        table nobody ships (say so in the registry) or a registration
        somebody forgot -- both are worth a red.

        ROUND 4m2kx7: "say so in the registry" now has somewhere to be said.
        ``field_mobs.MINED_NOT_SHIPPED_TABLE_MODULES`` is the first half of
        that sentence, for a table that is mined and correct and must NOT be
        registered yet -- scene 8 has no death ruling, so registering it
        would put nine monsters in a map that cannot die.  A table in NEITHER
        map still fails here, which is what keeps this a declaration rather
        than an escape hatch, and ``mined_not_shipped_scenes()`` refuses a
        scene that is in both or one declared with no reason.
        """
        on_disk = {
            path.name for path in TABLES_DIR.glob("field_mob_tables*.py")
        }
        registered = {
            Path(module.__file__).name
            for module in _generated_modules().values()
        }
        declared_unshipped = {
            Path(field_mobs.MINED_NOT_SHIPPED_TABLE_MODULES[scene].__file__).name
            for scene in field_mobs.mined_not_shipped_scenes()
        }
        self.assertEqual(registered & declared_unshipped, set())
        self.assertEqual(on_disk, registered | declared_unshipped)

    def test_a_declared_unshipped_table_names_the_door_that_is_shut(
            self) -> None:
        """The reason is the whole value of the declaration.

        A scene may sit out of the registry only while somebody can read WHY
        from the registry itself.  An empty or missing reason is the state
        this channel exists to make impossible, so it is asserted rather than
        trusted to review.
        """
        for scene in field_mobs.mined_not_shipped_scenes():
            with self.subTest(scene=scene):
                reason = field_mobs.MINED_NOT_SHIPPED_REASON[scene]
                self.assertIsInstance(reason, str)
                self.assertGreater(len(reason.strip()), 40, reason)
                self.assertNotIn(scene, field_mobs.live_scenes())

    def test_every_module_carries_the_generators_block_verbatim(self) -> None:
        """The check that replaced "the phrases are present".

        Measured: appending four lines to the generator's template while
        leaving the six modules alone passed the phrase check.  It cannot
        pass this one.
        """
        expected = _provenance_block(
            GENERATOR.read_text(encoding="ascii"), "the generator")
        for scene, module in _generated_modules().items():
            with self.subTest(scene=scene):
                self.assertEqual(
                    _provenance_block(_module_text(module), scene), expected)

    def test_the_withdrawn_claim_is_struck_and_still_readable(self) -> None:
        for scene, module in _generated_modules().items():
            with self.subTest(scene=scene):
                text = _module_text(module)
                self.assertIn("~~" + WITHDRAWN_CLAIM + "~~", text)
                self.assertEqual(
                    text.count(WITHDRAWN_CLAIM),
                    text.count("~~" + WITHDRAWN_CLAIM + "~~"),
                    "every occurrence of the withdrawn sentence must be a "
                    "struck one",
                )

    def test_no_generated_table_names_the_loader_module(self) -> None:
        """A comment must not make a data table look like an importer.

        Measured on this round's own first cut: naming the module here put
        all six generated tables into the importer list `tests/
        test_field_mobs.py` pins, and the suite went red in six places for a
        comment that imports nothing.
        """
        for scene, module in _generated_modules().items():
            with self.subTest(scene=scene):
                self.assertNotIn(LOADER_MODULE_NAME, _module_text(module))


class Bg0001RowsAreDigestedWithoutTheCommentTests(unittest.TestCase):
    """pf-adversary D5: give the "only the comment moved" claim a control."""

    def test_the_shipped_rows_are_unchanged(self) -> None:
        digest = hashlib.sha256(
            repr(field_mob_tables.SHIPPED_PLACEMENTS).encode("ascii")
        ).hexdigest()
        self.assertEqual(
            digest, BG0001_SHIPPED_ROWS_SHA256,
            "bg0001's shipped rows moved.  The five sibling test files pin "
            "this module by whole-file hash, so a row change hidden beside a "
            "comment change would re-pin green off-bridge; this digest is "
            "the half that does not skip.",
        )

    def test_the_digest_is_not_vacuous(self) -> None:
        """A changed row really does move it."""
        moved = hashlib.sha256(
            repr(_with_a_wrong_identity(field_mob_tables.SHIPPED_PLACEMENTS))
            .encode("ascii")
        ).hexdigest()
        self.assertNotEqual(moved, BG0001_SHIPPED_ROWS_SHA256)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
