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
import unittest.mock

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
        # ~~15 since round `vwekfq` (LANE-A): world_bg1001_identity (scene
        # 17) joined the registry.~~  ~~16 since round `yob0a2` (LANE-A):
        # world_bg3007_identity (scene 304, the Dark Fog Sea) joined it in
        # the same commit that gave that scene a census.~~  17 since round
        # `9zj630` (LANE-A): world_bg3008_identity (scene 305, the Pale
        # Silver Sea) joined it the same way, in the commit that gave THAT
        # scene a census.
        self.assertEqual(17, len(census.scene_ids_with_a_census()))

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

    def test_a_family_that_renumbers_makes_measured_offset_raise(self):
        # The first draft of this test never called the function; it built a
        # set by hand and asserted `len == 2`, which tests Python (pf-
        # adversary D5).  This drives the real refusal, so deleting the
        # `families disagree` raise turns it red.
        class Renumbered:
            placement_index = 7
            actor_identity = 7  # offset 0, unlike every real family
            n_id = 1
            display_name = "x"

        scene_id, (source, _loader) = next(
            iter(census._SCENE_CENSUS_SOURCES.items())
        )
        patched = dict(census._SCENE_CENSUS_SOURCES)
        patched[scene_id] = (source, lambda: (Renumbered(),))
        with unittest.mock.patch.object(
            census, "_SCENE_CENSUS_SOURCES", patched
        ):
            with self.assertRaises(census.IdentityCensusError) as caught:
                census.measured_identity_offset(legacy=self.legacy)
        self.assertIn("disagree", str(caught.exception))

    def test_the_offset_is_not_a_constant_in_the_file(self):
        # M8 (`return 0x2001` first thing) survived the first draft because
        # the comparison value was itself 0x2001.  This drives the function
        # over a table whose offset is NOT today's, so a hardcoded return
        # cannot satisfy it.
        class Shifted:
            placement_index = 4
            actor_identity = 4 + 0x3000
            n_id = 1
            display_name = "x"

        patched = {
            scene_id: (source, lambda: (Shifted(),))
            for scene_id, (source, _loader) in census._SCENE_CENSUS_SOURCES.items()
        }
        with unittest.mock.patch.object(
            census, "_SCENE_CENSUS_SOURCES", patched
        ):
            with unittest.mock.patch.object(
                census.field_mobs, "roster_for_scene_id", lambda scene_id: ()
            ):
                # A scene id no family claims, so the legacy-backed branch
                # is simply unavailable and skipped rather than raising.
                with unittest.mock.patch.object(
                    census, "_LEGACY_BACKED_SCENE_ID", 9999
                ):
                    self.assertEqual(
                        0x3000, census.measured_identity_offset(legacy=None)
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

    def test_the_conflicting_bucket_is_a_tripwire_not_a_measurement(self):
        # pf-adversary (D1): `conflicting` cannot fire while identity is a
        # pure function of the placement index, so asserting it is empty
        # measures NOTHING on its own.  What is asserted instead is the
        # REASON, computed here from the claims: one offset for every claim
        # in the scene.  The day that stops holding, this goes red and the
        # emptiness below starts meaning something again.
        for scene_id, verdict in sorted(self.verdicts.items()):
            claims = census.roster_claims(scene_id)
            try:
                claims += census.census_claims(scene_id, legacy=self.legacy)
            except census.IdentityFamilyUnavailable:  # pragma: no cover
                pass
            offsets = {
                claim.identity - claim.placement_index for claim in claims
            }
            with self.subTest(scene=scene_id):
                self.assertEqual(1, len(offsets), offsets)
                self.assertEqual((), verdict.conflicting)
                self.assertTrue(verdict.is_unique_within_the_scene())

    def test_distinct_identity_count_is_recomputed_here_not_read_back(self):
        # M16 (`distinct_identities = len(census)`) survived the first draft
        # because the only assertion compared the field against the other
        # field.  This recomputes it from the claims.
        for scene_id, verdict in sorted(self.verdicts.items()):
            claims = census.roster_claims(scene_id)
            try:
                claims += census.census_claims(scene_id, legacy=self.legacy)
            except census.IdentityFamilyUnavailable:  # pragma: no cover
                pass
            expected = len({claim.identity for claim in claims})
            with self.subTest(scene=scene_id):
                self.assertGreater(expected, 0)
                self.assertEqual(expected, verdict.distinct_identities)
                self.assertEqual(verdict.census_count, verdict.distinct_identities)

    def test_every_roster_identity_is_also_a_census_identity_of_that_scene(self):
        # WHY THIS MATTERS, corrected: `world_population.apply_identity_
        # override` does NOT refuse a key its generation does not carry --
        # `entries.append(override.get(identity, original))`, and its own
        # docstring says so.  A roster identity missing from the census is
        # SILENTLY DROPPED: the monster's bytes never leave and the client
        # draws the census NPC in that slot.  Nothing else enforces the
        # containment, so it is pinned here.
        #
        # Recomputed from the claims rather than read off the field, because
        # `absent = ()` survived the first draft (pf-adversary D4).
        shipped = 0
        checked = 0
        for scene_id, verdict in sorted(self.verdicts.items()):
            roster = census.roster_claims(scene_id)
            if not roster:
                continue
            checked += 1
            census_identities = {
                claim.identity
                for claim in census.census_claims(scene_id, legacy=self.legacy)
            }
            expected = tuple(
                sorted(
                    claim.identity
                    for claim in roster
                    if claim.identity not in census_identities
                )
            )
            with self.subTest(scene=scene_id):
                self.assertEqual(expected, verdict.roster_identities_absent_from_census)
                self.assertEqual((), expected)
            shipped += verdict.roster_count
        self.assertGreater(shipped, 0, "no scene shipped a roster at all")
        # COO-DECISION 20260903_1942 item 2: scene 14 (Bg0015) joined
        # scenes 1 and 2 as a roster-shipping scene this round -- the
        # per-scene subTest loop above already proved its 12 live roster
        # identities are every one a census identity of that same scene
        # (the assertion this test exists for); this count just has to
        # keep up with which scenes were checked.
        # ROUND jqeo2m: ~~3~~ -> 4.  Scene 5 (bg0005) joined on the same
        # terms scene 14 did, and the per-scene subTest above is what
        # actually proved it: all six of its roster identities are census
        # identities of scene 5, so none of them is silently dropped by
        # ``apply_identity_override`` -- which is the containment this test
        # exists for.  This number only tracks how many scenes were checked.
        # ROUND am1fw8: ~~4~~ -> 5.  Scene 3 (Bg0003) joined on the same
        # terms scenes 14 and 5 did, and the per-scene subTest above is
        # again what proved it: all twelve of its roster identities are
        # census identities of scene 3, so none is silently dropped by
        # ``apply_identity_override``.  This number only tracks how many
        # scenes were checked.
        # ROUND r6isy5: ~~5~~ -> 6.  Scene 4 (bg0004) joined on the same
        # terms scenes 14, 5 and 3 did, and the per-scene subTest above is
        # again what proved it: all SEVEN of its roster identities are
        # census identities of scene 4, so none is silently dropped by
        # ``apply_identity_override``.  Worth one extra sentence on this
        # scene: three of its seven identities collide with another live
        # scene's (0x2020, 0x202B, 0x2046), and this containment is a
        # WITHIN-scene question, so those collisions cannot help a roster
        # row pass here on another scene's census.  This number only tracks
        # how many scenes were checked.
        self.assertEqual(
            6, checked, "only scenes 1, 2, 3, 4, 5 and 14 ship rosters today")

    def test_the_tripwire_fires_when_one_identity_names_two_placements(self):
        # The routing itself, driven directly.  Shipped data cannot reach
        # this branch (the identity formula makes it impossible), so a
        # mutant that hardcoded `same_placement=True` -- or filed every
        # dispute as benign -- survived the whole first draft.  This is what
        # would have to work on the day the formula grows a scene term.
        class Row:
            def __init__(self, index, identity, template):
                self.placement_index = index
                self.actor_identity = identity
                self.n_id = template
                self.display_name = "probe"

        scene_id = 3
        source, _loader = census._SCENE_CENSUS_SOURCES[scene_id]
        patched = dict(census._SCENE_CENSUS_SOURCES)
        patched[scene_id] = (
            source,
            lambda: (Row(0, 0x2001, 1), Row(5, 0x2001, 2)),
        )
        with unittest.mock.patch.object(
            census, "_SCENE_CENSUS_SOURCES", patched
        ):
            verdict = census.scene_verdict(scene_id)
        self.assertEqual(1, len(verdict.conflicting))
        self.assertEqual((), verdict.shared)
        self.assertFalse(verdict.conflicting[0].same_placement)
        self.assertFalse(verdict.is_unique_within_the_scene())
        self.assertIn("unique_within_scene=NO", census.describe_verdict(verdict))

    def test_two_rows_on_one_placement_that_agree_are_not_a_conflict(self):
        # The other side of the routing, so the test above is not just
        # "anything with two claims is a conflict".
        class Row:
            def __init__(self, template):
                self.placement_index = 4
                self.actor_identity = 0x2005
                self.n_id = template
                self.display_name = "probe"

        scene_id = 3
        source, _loader = census._SCENE_CENSUS_SOURCES[scene_id]
        patched = dict(census._SCENE_CENSUS_SOURCES)
        patched[scene_id] = (source, lambda: (Row(7), Row(7)))
        with unittest.mock.patch.object(
            census, "_SCENE_CENSUS_SOURCES", patched
        ):
            verdict = census.scene_verdict(scene_id)
        self.assertEqual((), verdict.conflicting)
        self.assertEqual(1, len(verdict.shared))
        self.assertEqual((), verdict.disagreeing)

    def test_a_roster_identity_outside_the_census_is_reported(self):
        # The positive half: the computation really runs.  A roster row the
        # census does not carry is the state that gets silently dropped on
        # the wire, so the census has to be able to say it out loud.
        class Ghost:
            placement_index = 9000
            actor_identity = 0x2000 + 9000 + 1
            template_id = 1
            display_name = "ghost"

        real = field_mobs.roster_for_scene_id(2)
        with unittest.mock.patch.object(
            field_mobs, "roster_for_scene_id",
            lambda scene_id: tuple(real) + (Ghost(),) if scene_id == 2 else (),
        ):
            verdict = census.scene_verdict(2, legacy=self.legacy)
        self.assertEqual(
            (Ghost.actor_identity,), verdict.roster_identities_absent_from_census
        )
        # And the distinct count really counts identities rather than census
        # rows: on shipped data the two numbers are equal, so only a roster
        # identity outside the census can tell them apart (M16).
        self.assertEqual(verdict.census_count + 1, verdict.distinct_identities)

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

    def test_an_identity_is_shared_by_more_than_one_scene(self):
        # ~~asserted that some identity is claimed by EVERY censused scene~~
        # -- pf-adversary (D8) showed that is a false-red generator: one new
        # scene mined with a non-overlapping placement range turns it red
        # with nothing wrong.  The structural claim is the one that matters.
        widest = max(len(item.scenes) for item in self.ambiguities)
        self.assertGreaterEqual(widest, 2)

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
        # The LITERAL token, not `census.CONSOLE_TOKEN` -- comparing the
        # constant against itself let a rename survive while every grep
        # pattern and every document naming it silently stopped matching
        # (pf-adversary D7).
        self.assertTrue(line.startswith("GM_IDENTITY_CENSUS"), line)
        self.assertEqual("GM_IDENTITY_CENSUS", census.CONSOLE_TOKEN)
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

    def test_the_line_really_says_NO_when_the_verdict_does(self):
        # Driven through the PRINTER, not just the predicate: a mutant that
        # printed `yes` unconditionally survived the first draft, because
        # nothing could build a verdict that disagreed (pf-adversary D7).
        disputed = census.DisputedIdentity(
            identity=0x2001,
            scene_id=2,
            claims=(),
            same_placement=False,
            templates_agree=False,
        )
        conflicted = census.SceneIdentityVerdict(
            scene_id=2,
            census_count=1,
            roster_count=1,
            distinct_identities=1,
            conflicting=(disputed,),
            shared=(),
            disagreeing=(),
            roster_identities_absent_from_census=(),
        )
        self.assertFalse(conflicted.is_unique_within_the_scene())
        line = census.describe_verdict(conflicted)
        self.assertIn("unique_within_scene=NO", line)
        self.assertIn("conflicting=1", line)

    def test_the_line_says_families_agree_NO_where_the_data_disagrees(self):
        # Scene 1 is the shipped case, so this one needs no hand-built
        # verdict at all.
        line = census.describe_scene(population.SCENE_ID, legacy=self.legacy)
        self.assertIn("families_agree=NO", line)
        self.assertIn("disagreeing=4", line)
        self.assertIn(
            "families_agree=yes", census.describe_scene(2, legacy=self.legacy)
        )

    def test_the_printer_refuses_something_that_is_not_a_verdict(self):
        with self.assertRaises(census.IdentityCensusError):
            census.describe_verdict("scene=2")


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
        # NORMALISED before the comparison: pf-adversary (D6) got
        # `FONT_STYLE_ID` and `0x80000000` past the first draft's literal
        # list.  Underscores out, case folded, so the spellings collapse.
        normalised = (
            self.executable_source().replace("_", "").lower()
        )
        for banned in ("fontstyleid", "fontstyle", "0x80000000", "-0x2000"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned.replace("_", "").lower(), normalised)

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
        # ~~substring bans on `open(`/`write(`/...~~ -- pf-adversary (D6)
        # walked straight past them with `write_text(`, and proved it by
        # creating a file on disk while the suite stayed green.  A spelling
        # ban cannot express "no side effects"; the import surface can.
        # Nothing in this module may reach a filesystem, a process, or a
        # socket, so nothing it imports may be able to.
        tree = ast.parse(
            (PACKAGE / "gm" / "identity_registry_census.py").read_text(
                encoding="utf-8"
            )
        )
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imported.add(node.module.split(".")[0])
                else:
                    imported.update(alias.name for alias in node.names)
        forbidden = imported & {
            "os", "io", "sys", "pathlib", "shutil", "socket", "subprocess",
            "tempfile", "sqlite3", "json", "csv", "struct", "pickle",
        }
        self.assertEqual(set(), forbidden, sorted(imported))
        # And the calls it makes are its own or the tables'; no builtin that
        # can reach outside the process.
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertEqual(
            set(), called & {"open", "exec", "eval", "compile", "__import__"}
        )


if __name__ == "__main__":
    unittest.main()
