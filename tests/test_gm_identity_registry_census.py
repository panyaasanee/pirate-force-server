"""The identity census, held to the same standard it holds the tables to.

Nothing here is hand-typed from a run of the module.  Every expected value is
either DERIVED from the source families themselves (so a table edit moves the
expectation and the test still means something) or is a STRUCTURAL claim -- no
identity in one scene names two placements, an identity value is not a key on
its own -- that would have to be defeated on purpose.

The one thing deliberately pinned as a NUMBER is the count of scenes this
repository can census, because a scene family silently disappearing from the
registry is exactly the drift the module exists to notice.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import population  # noqa: E402
from pirateforce_foundation.gm import identity_registry_census as census  # noqa: E402
from pirateforce_foundation.gm import name_color_gate  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PACKAGE = ROOT / "src" / "pirateforce_foundation"


class RegistryCoverageTests(unittest.TestCase):
    """The hand-written registry has to keep up with the package."""

    def test_every_scene_identity_module_in_the_package_is_registered(self):
        # DERIVED from the directory, not from a list in the module: a new
        # `world_bgXXXX_identity.py` that nobody adds here is a scene the
        # census would silently skip, and skipping is the failure mode.
        on_disk = {
            path.stem
            for path in PACKAGE.glob("world_bg*_identity.py")
        }
        self.assertTrue(on_disk, "no scene identity modules found at all")
        registered = set()
        for scene_id in census.scene_ids_with_a_census():
            if scene_id == population.SCENE_ID:
                continue
            source, _loader = census._SCENE_CENSUS_SOURCES[scene_id]
            registered.add(source)
        missing = sorted(on_disk - registered)
        self.assertEqual(
            [], missing,
            "these scene identity modules are not in the census registry: %s"
            % missing,
        )

    def test_scene_one_is_registered_even_though_it_needs_the_serializer(self):
        self.assertIn(population.SCENE_ID, census.scene_ids_with_a_census())

    def test_the_scene_count_is_pinned_so_a_family_cannot_vanish_quietly(self):
        self.assertEqual(14, len(census.scene_ids_with_a_census()))

    def test_the_registry_holds_one_entry_per_source_and_lost_none(self):
        # A duplicate SCENE_N_ID would overwrite a whole family; the module
        # refuses at import, and this is the second belt: entry count must
        # equal source count.
        sources = {
            source for source, _loader in census._SCENE_CENSUS_SOURCES.values()
        }
        self.assertEqual(len(census._SCENE_CENSUS_SOURCES), len(sources))

    def test_registering_a_scene_twice_refuses_rather_than_overwriting(self):
        taken = next(iter(census._SCENE_CENSUS_SOURCES))
        with self.assertRaises(census.IdentityCensusError):
            census._register(taken, "probe", tuple)


class RefusalTests(unittest.TestCase):
    """A census that cannot look must never look like a clean census."""

    def test_scene_one_without_the_serializer_refuses_by_its_own_class(self):
        with self.assertRaises(census.IdentityFamilyUnavailable):
            census.census_claims(population.SCENE_ID)

    def test_an_unaddressed_scene_refuses_rather_than_returning_empty(self):
        unknown = max(census.scene_ids_with_a_census()) + 1
        with self.assertRaises(census.IdentityFamilyUnavailable):
            census.census_claims(unknown)

    def test_unavailable_is_a_census_error_so_one_except_clause_catches_both(self):
        self.assertTrue(
            issubclass(
                census.IdentityFamilyUnavailable, census.IdentityCensusError
            )
        )

    def test_a_bool_is_not_a_scene_id(self):
        # True == 1 would census Port Royal and read like an answer.
        with self.assertRaises(census.IdentityCensusError):
            census.roster_claims(True)

    def test_a_negative_scene_id_refuses(self):
        with self.assertRaises(census.IdentityCensusError):
            census.roster_claims(-1)

    def test_a_row_with_no_template_attribute_refuses_instead_of_defaulting(self):
        class NoTemplate:
            placement_index = 3
            actor_identity = 0x2004
            display_name = "x"

        with self.assertRaises(census.IdentityCensusError):
            census._claim(1, census.FAMILY_SCENE_CENSUS, "probe", NoTemplate())

    def test_a_row_with_no_name_attribute_at_all_refuses(self):
        class NoName:
            placement_index = 3
            actor_identity = 0x2004
            n_id = 42

        with self.assertRaises(census.IdentityCensusError):
            census._claim(1, census.FAMILY_SCENE_CENSUS, "probe", NoName())

    def test_an_empty_name_is_data_and_is_kept(self):
        # `world_bg0004_identity` really ships one; refusing it would report a
        # readable scene as unreadable.
        class EmptyName:
            placement_index = 3
            actor_identity = 0x2004
            n_id = 42
            display_name = ""

        claim = census._claim(1, census.FAMILY_SCENE_CENSUS, "probe", EmptyName())
        self.assertEqual("", claim.display_name)

    def test_a_row_with_a_bool_identity_refuses(self):
        class BoolIdentity:
            placement_index = 3
            actor_identity = True
            n_id = 42
            display_name = "x"

        with self.assertRaises(census.IdentityCensusError):
            census._claim(1, census.FAMILY_SCENE_CENSUS, "probe", BoolIdentity())


class TemplateSpaceTests(unittest.TestCase):
    """The template number has to mean the same thing in every family."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_preferring_n_id_over_template_id_is_load_bearing(self):
        # If these ever became the same number the preference would be
        # cosmetic and this test would be pointless -- so it counts.
        both = 0
        differ = 0
        for scene_id in census.scene_ids_with_a_census():
            try:
                rows = census.census_claims(scene_id, legacy=self.legacy)
            except census.IdentityFamilyUnavailable:  # pragma: no cover
                continue
            source = census._SCENE_CENSUS_SOURCES.get(scene_id)
            if source is None:
                continue
            for row in source[1]():
                if hasattr(row, "n_id") and hasattr(row, "template_id"):
                    both += 1
                    if row.n_id != row.template_id:
                        differ += 1
            self.assertTrue(rows)
        self.assertGreater(both, 0, "no family exposes both spellings at all")
        self.assertEqual(
            both, differ,
            "every row exposing both is expected to disagree; if that stops "
            "being true, re-derive which name carries the MOBS template",
        )

    def test_scene_two_is_the_cross_check_that_both_families_use_MOBS_ids(self):
        # The census reads `n_id`, the roster reads `template_id`, and in
        # scene 2 every shared identity agrees -- which is what says the two
        # accessors land in ONE number space rather than two.
        verdict = census.scene_verdict(2, legacy=self.legacy)
        self.assertTrue(verdict.shared)
        for disputed in verdict.shared:
            with self.subTest(identity=disputed.identity):
                self.assertTrue(disputed.templates_agree)


class MeasuredOffsetTests(unittest.TestCase):
    """The formula is read back off the families, never typed here."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_every_family_uses_one_offset_and_field_mobs_agrees_with_it(self):
        measured = census.measured_identity_offset(legacy=self.legacy)
        # DERIVED from a shipped roster row rather than written as 0x2001.
        row = field_mobs.load_roster()[0]
        self.assertEqual(row.actor_identity - row.placement_index, measured)

    def test_a_family_that_renumbers_makes_the_offset_refuse(self):
        class Renumbered:
            placement_index = 7
            actor_identity = 7  # offset 0, unlike every real family
            n_id = 1
            display_name = "x"

        real = census.roster_claims(1)
        self.assertTrue(real, "scene 1 ships no roster; this test proves nothing")
        odd = census._claim(1, census.FAMILY_SCENE_CENSUS, "probe", Renumbered())
        offsets = {claim.identity - claim.placement_index for claim in real}
        offsets.add(odd.identity - odd.placement_index)
        self.assertEqual(
            2, len(offsets),
            "the probe row was supposed to disagree with the real ones",
        )


class WithinOneSceneTests(unittest.TestCase):
    """The uniqueness half, measured scene by scene."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.verdicts = {
            scene_id: census.scene_verdict(scene_id, legacy=cls.legacy)
            for scene_id in census.scene_ids_with_a_census()
        }

    def test_no_scene_hands_one_identity_to_two_different_placements(self):
        for scene_id, verdict in sorted(self.verdicts.items()):
            with self.subTest(scene=scene_id):
                self.assertEqual((), verdict.conflicting)
                self.assertTrue(verdict.is_unique_within_the_scene())
                # Not vacuous: the scene really was enumerated.
                self.assertGreater(verdict.census_count, 0)

    def test_distinct_identity_count_equals_the_census_row_count(self):
        # The strongest form of "unique within the scene": every census row
        # got its own number, and the roster added no number of its own.
        for scene_id, verdict in sorted(self.verdicts.items()):
            with self.subTest(scene=scene_id):
                self.assertEqual(verdict.census_count, verdict.distinct_identities)

    def test_every_roster_identity_is_also_a_census_identity_of_that_scene(self):
        # `world_population.apply_identity_override` is keyed by identity and
        # refuses a key its generation does not carry.  This containment is
        # what keeps that door from refusing at boot; nothing else enforces
        # it, so it is pinned here.
        shipped = 0
        for scene_id, verdict in sorted(self.verdicts.items()):
            with self.subTest(scene=scene_id):
                self.assertEqual((), verdict.roster_identities_absent_from_census)
            shipped += verdict.roster_count
        self.assertGreater(shipped, 0, "no scene shipped a roster at all")

    def test_the_two_families_only_ever_share_the_same_placement(self):
        for scene_id, verdict in sorted(self.verdicts.items()):
            for disputed in verdict.shared:
                with self.subTest(scene=scene_id, identity=disputed.identity):
                    self.assertTrue(disputed.same_placement)
                    self.assertEqual(
                        {census.FAMILY_SCENE_CENSUS, census.FAMILY_FIELD_MOB_ROSTER},
                        {claim.family for claim in disputed.claims},
                    )

    def test_scene_one_is_where_the_two_families_disagree_about_the_template(self):
        # NOT a defect report: `apply_identity_override` replaces those census
        # entries with the roster's bytes, so one of the two reaches a client.
        # Pinned because a reader of a server log sees both names for one
        # identity, and because the day the disagreement SPREADS is worth a
        # red test rather than a shrug.
        disagreeing = {
            scene_id: [
                disputed.identity
                for disputed in verdict.shared
                if not disputed.templates_agree
            ]
            for scene_id, verdict in self.verdicts.items()
        }
        scenes_with_disagreement = sorted(
            scene_id for scene_id, ids in disagreeing.items() if ids
        )
        self.assertEqual([population.SCENE_ID], scenes_with_disagreement)
        identities = disagreeing[population.SCENE_ID]
        roster = census.roster_claims(population.SCENE_ID)
        self.assertEqual(
            sorted(claim.identity for claim in roster), sorted(identities),
            "every scene 1 roster row is expected to disagree, not just some",
        )


class AcrossScenesTests(unittest.TestCase):
    """The registry half: an identity is not a key, and that is measured."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.ambiguities = census.cross_scene_ambiguities(legacy=cls.legacy)

    def test_identity_alone_is_ambiguous_across_scenes(self):
        self.assertTrue(
            self.ambiguities,
            "if this ever becomes empty the identity rule changed; that is a "
            "result worth reading, not a green test to keep",
        )

    def test_at_least_one_identity_is_claimed_by_every_censused_scene(self):
        widest = max(len(item.scenes) for item in self.ambiguities)
        self.assertEqual(len(census.scene_ids_with_a_census()), widest)

    def test_each_ambiguity_names_more_than_one_scene_in_ascending_order(self):
        for item in self.ambiguities:
            with self.subTest(identity=item.identity):
                self.assertGreater(len(item.scenes), 1)
                self.assertEqual(tuple(sorted(set(item.scenes))), item.scenes)

    def test_the_ambiguous_set_covers_the_low_end_of_every_scene(self):
        # DERIVED: the lowest identity any family hands out must be ambiguous,
        # because every family starts counting from the same offset.
        offset = census.measured_identity_offset(legacy=self.legacy)
        ambiguous = {item.identity for item in self.ambiguities}
        self.assertIn(offset, ambiguous)


class ConsoleLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def test_the_line_is_one_ascii_line_carrying_the_grep_token(self):
        line = census.describe_scene(2, legacy=self.legacy)
        self.assertTrue(line.startswith(census.CONSOLE_TOKEN))
        self.assertNotIn("\n", line)
        line.encode("ascii")

    def test_the_line_reports_the_verdict_it_was_built_from(self):
        verdict = census.scene_verdict(2, legacy=self.legacy)
        line = census.describe_scene(2, legacy=self.legacy)
        for field, value in (
            ("scene", verdict.scene_id),
            ("census", verdict.census_count),
            ("roster", verdict.roster_count),
            ("distinct", verdict.distinct_identities),
            ("conflicting", len(verdict.conflicting)),
            ("shared", len(verdict.shared)),
        ):
            with self.subTest(field=field):
                self.assertIsNotNone(
                    re.search(r"\b%s=%d\b" % (field, value), line), line
                )

    def test_a_scene_with_a_conflict_would_say_NO(self):
        # The word only means something if the other word is reachable.
        conflicted = census.SceneIdentityVerdict(
            scene_id=2,
            census_count=1,
            roster_count=1,
            distinct_identities=1,
            conflicting=(
                census.DisputedIdentity(
                    identity=0x2001,
                    scene_id=2,
                    claims=(),
                    same_placement=False,
                    templates_agree=False,
                ),
            ),
            shared=(),
            roster_identities_absent_from_census=(),
        )
        self.assertFalse(conflicted.is_unique_within_the_scene())


class ThisModuleUnlocksNothingTests(unittest.TestCase):
    """Closing a precondition is not permission, and the code has to show it."""

    def test_the_p2_colour_verdict_is_untouched_and_still_refuses(self):
        verdict = name_color_gate.p2_color_wiring_verdict()
        self.assertFalse(verdict.allowed)
        self.assertEqual(
            name_color_gate.P2_COLOR_WIRING_BLOCKERS, verdict.blockers
        )

    def test_the_census_names_no_style_and_no_negative_identity_scheme(self):
        # The module may DISCUSS the negative-identity question in prose --
        # its docstring says outright that it does NOT close it -- so prose is
        # stripped and what is left is what the interpreter executes.  Same
        # rule `name_color_gate` is held to, applied to the file that could
        # most easily smuggle a scheme in.
        for banned in ("FontStyleID", "fontstyle", "0x8000_0000", "-0x2000"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.executable_source())

    def executable_source(self) -> str:
        path = PACKAGE / "gm" / "identity_registry_census.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        prose: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef)
            ):
                continue
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                prose.update(range(first.lineno, first.end_lineno + 1))
        return "\n".join(
            line
            for number, line in enumerate(source.splitlines(), start=1)
            if number not in prose and not line.strip().startswith("#")
        )

    def test_the_prose_stripper_really_removes_the_docstrings(self):
        # Otherwise the ban above could be passing because it read nothing.
        stripped = self.executable_source()
        self.assertNotIn("Make the identity-uniqueness claim EXECUTABLE", stripped)
        self.assertIn("def scene_verdict", stripped)

    def test_it_writes_nothing_and_composes_no_frame(self):
        source = (
            PACKAGE / "gm" / "identity_registry_census.py"
        ).read_text(encoding="utf-8")
        for banned in ("open(", "write", "compose", "send", "socket"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned + "(", source)


if __name__ == "__main__":
    unittest.main()
