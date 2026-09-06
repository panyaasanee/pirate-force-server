"""LANE-B: scene 5 (bg0005, Evil Port) is a REGISTERED combat scene.

ROUND jqeo2m.  Unlike Bg0015's own file, which spent five rounds asserting
that its table stayed inert, this one asserts the opposite from its first
commit: ``field_mob_tables_bg0005`` is registered in
``field_mobs._SCENE_TABLE_MODULES`` in the same commit that adds it, because
the gate Bg0015 was waiting on does not exist here.  Lane A opened scene 5's
arrival census AND its ``login_entry_allowed`` door in round l03cgh; a player
can stand in this map today.  What they could not do until this commit is
swing at anything in it: ``field_mobs.scene_for_scene_id(5)`` returned
``None``, so ``roster_for_scene_id(5)`` was the empty tuple, so every strike
was refused with ``target_not_in_ledger``.

THE THREE TESTS THAT MATTER MOST, of the ones in this file:

``test_the_ai_register_opens_for_every_shipped_row`` is the one that would
have cost a player the most.  ``mob_ai_control.open_register`` raises
``MobAiControlError: ai_row_missing`` for a roster row whose ``AI_COMBAT`` id
is not in the mined AI table, and ``runtime.py``'s
``_sync_combat_scene_state`` call sits ABOVE every ``except`` in
``_dispatch_mob_combat`` -- so the FIRST swing in a scene whose AI rows were
not mined unwinds the listener thread and empties the player's world.  That
is measured, not theoretical: ``mob_combat_bg0015_gates.py`` measured it end
to end for scene 14, and this round reproduced it for scene 5 (placement 59
-> AI_COMBAT 201) before widening ``tools/pf_mine_mob_ai_rows.py``'s union.

``test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk``
is the control ``scene_identity_rule.py`` says this lane did not have:
"NONE of the three [generator controls] touches type 14, yet the generated
module records the type-2 and bg0001 findings under a heading that reads
'what the crosswalk controls found at mining time'".  Scene 5 is the first
scene where a control measured ON THE SCENE BEING MINED is available without
writing a new one: lane A mined this scene's CLINE type 5 crosswalk
independently, for its own arrival census, into
``world_bg0005_identity.IDENTITIES``.  Two lanes, two tools, two tables, one
answer per row -- or this test says which row disagrees.  It is a control,
not a coincidence: the failure it exists to catch is GT-078's, a map wearing
another map's names, and a single shared bug would have to occur in two
independently written miners to slip past it.

``test_scene_five_is_no_longer_acknowledged_without_a_composer`` holds the
promise ``mob_scene_recompose``'s acknowledgement block makes in its own
words -- "this lane WILL compose it; what it cannot do is compose a map with
no monsters in it" -- to the commit that puts the monsters in the map.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import field_mob_tables_bg0005  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_bg0005_identity  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0005.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "bg0005"
EXPECTED_SCENE_ID = 5
EXPECTED_HOSTILE_COUNT = 6
EXPECTED_TEMPLATE_COUNT = 6
EXPECTED_UNAMBIGUOUS = 49
# Equal to the hostile count for this scene, and that equality is a MEASURED
# property of bg0005 rather than a law -- the generator's own docstring says
# a scene where the four readings disagree must be read before its roster
# ships.  Here all four agree at 6; pinned separately so a future divergence
# is a failure with a name instead of a silently different roster.
EXPECTED_DROPS_NORMAL = 6

# The whole shipped roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_ROWS = (
    (59, 148, 0x203C, "Red Devil"),
    (69, 150, 0x2046, "Ned apes"),
    (70, 144, 0x2047, "Hard Blade Eagle"),
    (74, 146, 0x204B, "Black Jack"),
    (84, 523, 0x2055, "Jet cat thieves No.5"),
    (85, 525, 0x2056, "Jet cat thieves No.6"),
)

# Measured immediately before field_mob_tables_bg0005.py was added, and never
# to be updated to make a future edit of field_mob_tables.py pass silently --
# if bg0001's roster changes for a real reason this constant moves in that
# same commit and says why.  Same discipline, same value, as the pin
# tests/test_field_mob_tables_bg0015.py already carries.
# ROUND hor2lh: re-pinned, and by a change that touched ALL SIX generated
# tables on purpose -- pf-adversary D14 of round r6isy5b found the
# generator stamping every scene with a control sentence that is true only
# for bg0001, so the corrected comment was regenerated into each module.
# Only the comment block moved; every row, digest and census value in
# bg0001 is byte-identical (verified by regenerating and diffing).  The
# previous digest is kept, not deleted:
# ~~574fdca1391eb0aa4bc4a5a2b46b50c090839a86baf94426573312afff2866a5~~
BG0001_UNTOUCHED_SHA256 = (
    "c1a341c9d7721db45b07e2e7df2840719da5fcbcf5521d7f31eabd4a1ce26934"
)
# ROUND hor2lh: ~~9708~~ -> 12316, the comment correction described
# above.  This constant still means "this round did not touch that
# file"; it is re-pinned when a round changes bg0001 on purpose.
BG0001_UNTOUCHED_SIZE = 12316


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0005ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0005
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        # The project's ONE identity rule (COO-DECISION 2026-08-29T03:45).
        # Named here rather than inherited from the tool's default, so a
        # change of default cannot silently change what this scene ships.
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 5)
        self.assertEqual(
            len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in module.HOSTILE_PLACEMENTS}),
            EXPECTED_TEMPLATE_COUNT,
        )
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["drops_normal"], EXPECTED_DROPS_NORMAL)
        # This scene ships nothing under the retired set-number reading and
        # nothing off the town-target allowlist; asserted rather than assumed
        # so a future regeneration that starts shipping either is a failure.
        self.assertEqual(module.TOWN_TARGET_PLACEMENTS, [])
        self.assertEqual(module.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION, [])

    def test_the_scene_is_registered_and_reachable_through_its_scene_id(
            self) -> None:
        self.assertEqual(
            field_mobs.scene_for_scene_id(EXPECTED_SCENE_ID), EXPECTED_SCENE)
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            tuple(
                (mob.placement_index, mob.template_id, mob.actor_identity,
                 mob.display_name)
                for mob in rows
            ),
            EXPECTED_ROWS,
        )
        # Every row is stamped with THIS scene: the one thing
        # ``assert_single_scene_tables`` exists to stop is two scenes' rows
        # merged into one roster, and a roster that reached a strike under
        # another scene's name is the same defect one layer down.
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """The trap that unwinds the listener thread on the FIRST swing.

        Reproduced on scene 5 this round before ``tools/pf_mine_mob_ai_rows
        .py``'s union was widened: ``ai_row_missing: placement 59 points at
        AI_COMBAT 201, which is not in the mined rows``.  A future round that
        adds a roster row citing an unmined AI id, or regenerates the AI
        table from a narrower union, fails here instead of in front of a
        player.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_registering_scene_five_left_the_other_three_scenes_alone(
            self) -> None:
        """A fourth scene must not move the three already on the wire."""
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        # ~~12~~ -> 11 for scene 14, round j5v7mu: COO-DECISION
        # 20260905_0545 withheld placement 87 (Carlos) from what this lane
        # ships.  Asserted as a live count minus the withheld list rather
        # than as a bare 11, so this line keeps meaning "nothing else
        # moved" if the ruling is lifted.
        self.assertEqual(
            len(field_mobs.roster_for_scene_id(14)),
            12 - len(field_mobs.lane_withheld_placements("Bg0015")))
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 11)
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         BG0001_UNTOUCHED_SHA256)
        self.assertEqual(len(raw), BG0001_UNTOUCHED_SIZE)

    def test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk(
            self) -> None:
        """The control measured ON the scene being mined -- see the module
        docstring.  Lane A's ``world_bg0005_identity`` resolved this scene's
        CLINE type 5 block with its own miner for its own arrival census;
        this lane's generator resolved it again for the combat roster.  Every
        shipped row must land on the same ``MOBS.n_ID`` AND the same name in
        both, keyed by the scene file's own Mob-Set number.
        """
        sets = field_mob_tables_bg0005.SET_NUMBER_FOR_PLACEMENT
        disagreements = []
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            set_number = sets[mob.placement_index]
            theirs = world_bg0005_identity.IDENTITIES.get(set_number)
            if theirs is None:
                disagreements.append(
                    "placement %d (Mob-Set %d) resolves to %d here and is "
                    "UNRESOLVED in lane A's table"
                    % (mob.placement_index, set_number, mob.template_id))
                continue
            if (theirs.mobs_n_id, theirs.name) != (
                    mob.template_id, mob.display_name):
                disagreements.append(
                    "placement %d (Mob-Set %d): lane B says %d %r, lane A "
                    "says %d %r" % (
                        mob.placement_index, set_number, mob.template_id,
                        mob.display_name, theirs.mobs_n_id, theirs.name))
        self.assertEqual(
            disagreements, [],
            "the two independently mined readings of CLINE type 5 disagree; "
            "GT-078 is what shipping the wrong one costs, so stop and find "
            "out which miner is wrong before regenerating either table",
        )

    def test_the_six_shipped_templates_now_have_a_death_ruling_a_stray_row_still_refuses(
            self) -> None:
        """WHAT CHANGED THIS ROUND, pinned rather than left implicit.

        COO-DECISION 2026-09-04T11:48+07:00 (notes_to_chief/20260904_1148_
        COO-DECISION-lane-b-widen-death-scope-bg0005-six-templates-approved
        .md) approved exactly the six templates this scene ships, under the
        exact ruling name pinned below.  All six now resolve to that name --
        re-derived from the shipped roster rather than hand-copied, the same
        discipline ``mob_death.py``'s own comments hold every other ruling
        to.

        THE OTHER HALF OF THE OLD TEST'S NAME IS STILL TRUE AND STILL PINNED:
        a row in scene 5 outside these six templates still refuses, loud and
        safe, exactly as ``runtime.py:5239``'s ``try``/``except mob_death
        .MobDeathContractError`` expects.  Nothing in
        ``field_mob_tables_bg0005`` ships such a row today (``TOWN_TARGET_
        PLACEMENTS`` and ``LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION`` are
        both empty), so that half is proven on a hand-built stand-in FieldMob
        -- template 916 (the Training Iron Man dummy, ruled ONLY for
        bg0001), stamped with ``scene="bg0005"``.  That is not a fabricated
        monster the client will ever see; it is the same technique
        ``mob_death.rulings_covering``'s own docstring uses to exercise the
        scene axis no shipped row exercises, so a future ruling that widens
        too far cannot pass this test merely because bg0005's own roster
        happens to fit inside it.
        """
        ruling_name = (
            "COO-DECISION 2026-09-04T11:48+07:00 "
            "widen-death-scope-bg0005-six-templates")
        self.assertIn(ruling_name, mob_death.WIDENING_RULINGS)
        self.assertEqual(
            mob_death.WIDENING_RULINGS[ruling_name],
            frozenset(row[1] for row in field_mob_tables_bg0005.HOSTILE_PLACEMENTS),
        )
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[ruling_name],
            field_mob_tables_bg0005.SCENE,
        )
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        seen_templates = set()
        for mob in rows:
            self.assertEqual(mob_death.ruling_for(mob), ruling_name)
            seen_templates.add(mob.template_id)
        self.assertEqual(
            seen_templates,
            frozenset(row[1] for row in field_mob_tables_bg0005.HOSTILE_PLACEMENTS),
        )

        # The stray row: same scene, a template this ruling never named.
        a_shipped_row = rows[0]
        stray = field_mobs.FieldMob(
            placement_index=a_shipped_row.placement_index,
            template_id=916,
            x=a_shipped_row.x, y=a_shipped_row.y, z=a_shipped_row.z,
            visual_preset=a_shipped_row.visual_preset,
            display_name="stray-not-a-real-shipped-row",
            level=a_shipped_row.level,
            rank=a_shipped_row.rank,
            ai_wander=a_shipped_row.ai_wander,
            ai_combat=a_shipped_row.ai_combat,
            speed_walk=a_shipped_row.speed_walk,
            max_hp=a_shipped_row.max_hp,
            drops_normal=a_shipped_row.drops_normal,
            drops_equipment=a_shipped_row.drops_equipment,
            drops_specially=a_shipped_row.drops_specially,
            scene=EXPECTED_SCENE,
        )
        self.assertNotIn(stray.template_id, mob_death.WIDENING_RULINGS[ruling_name])
        with self.assertRaises(mob_death.MobDeathContractError):
            mob_death.ruling_for(stray)


class Bg0005RecomposeRegistrationTests(unittest.TestCase):
    """The promise ``mob_scene_recompose``'s acknowledgement block made."""

    def test_scene_five_is_no_longer_acknowledged_without_a_composer(
            self) -> None:
        self.assertNotIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER)
        self.assertTrue(
            mob_scene_recompose.scene_is_accounted_for(EXPECTED_SCENE_ID))
        self.assertIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.composer_scene_ids())
        composer = mob_scene_recompose.composer_for_scene_id(EXPECTED_SCENE_ID)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.kind, mob_scene_recompose.COMPOSER_BG0005)
        self.assertEqual(composer.scene, EXPECTED_SCENE)

    def test_the_new_composer_kind_is_non_delegated_and_has_a_builder(
            self) -> None:
        """The pair round n4pv7k found out of step when scene 14 was added.

        A kind that is admitted by :func:`_compose`'s guard but absent from
        the builder table reaches a ``KeyError`` in the listener thread; a
        kind in the table that is not admitted is a scene someone believes is
        composable and is not.  Both halves are one tuple now, and the
        assertion that keeps them one runs at import time.
        """
        self.assertIn(
            mob_scene_recompose.COMPOSER_BG0005,
            mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS,
        )
        self.assertEqual(
            frozenset(mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS),
            frozenset(mob_scene_recompose._POPULATION_BUILDERS),
        )
        for composer in mob_scene_recompose._COMPOSERS.values():
            if composer.kind == mob_scene_recompose.COMPOSER_DELEGATED:
                continue
            self.assertIn(
                composer.kind,
                mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS,
                "a registered composer whose kind is neither delegated nor "
                "admitted cannot compose at all",
            )

    def test_the_import_time_assertion_actually_refuses_a_broken_pair(
            self) -> None:
        """Mutation guard: the assertion above is only worth having if it
        fails on the mismatch it exists for.  Handed a broken pair rather
        than breaking the real one."""
        with self.assertRaises(mob_scene_recompose.SceneRecomposeError):
            mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
                kinds=("a_kind_with_no_builder",), builders={},
            )
        with self.assertRaises(mob_scene_recompose.SceneRecomposeError):
            mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
                kinds=(), builders={"a_builder_nothing_admits": None},
            )
        # And passes on a matching pair, so the test above is not green
        # merely because this function raises on everything.
        mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
            kinds=("k",), builders={"k": None},
        )

    def test_a_kind_wired_to_another_scenes_builder_is_refused(self) -> None:
        """THE MUTANT THAT SURVIVED, and the reason the assertion grew a
        second half.

        pf-adversary, this round: changing one entry to
        ``COMPOSER_BG0005: _build_bg0015`` passed the coverage check (the key
        SETS still matched), passed the ENTIRE suite unchanged, and made
        every scene-5 recompose return ``refused_Bg0015CensusError`` -- which
        the call site answers with the one-entry census RE-092 proved erases
        every other actor from the client's registry, silently.  The comment
        shipped beside the dispatch claimed it "cannot pick the wrong builder
        at all"; it could.

        Reproduced here as the mutation itself, against the REAL builders and
        the REAL composer registry, rather than a hand-built pair -- a
        misroute test that cannot see the real table is not a guard on it.
        """
        real = mob_scene_recompose._POPULATION_BUILDERS
        mutant = dict(real)
        mutant[mob_scene_recompose.COMPOSER_BG0005] = real[
            mob_scene_recompose.COMPOSER_BG0015]
        with self.assertRaises(
                mob_scene_recompose.SceneRecomposeError) as caught:
            mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
                builders=mutant)
        message = str(caught.exception)
        self.assertIn("wrong scene", message)
        self.assertIn(mob_scene_recompose.COMPOSER_BG0005, message)
        # Every real builder serves the scene its own composer registered
        # for -- asserted positively too, so this card cannot pass merely
        # because the function raises.
        mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder()
        for composer in mob_scene_recompose._COMPOSERS.values():
            builder = real.get(composer.kind)
            if builder is None:
                continue
            self.assertEqual(builder.serves_scene_id, composer.scene_id)


class Bg0005RecomposeActuallyComposesTest(unittest.TestCase):
    """THE GAP THE MUTANT CAME THROUGH: nothing called this scene's composer.

    pf-adversary, this round: the tests above inspect registry dicts, and
    the designated drift pin in ``tests/test_mob_scene_recompose.py`` asserts
    only that scene 5 appears in ``composer_scene_ids()``.  A composer that
    is registered and REFUSES satisfies every one of those and still ships
    the one-entry world-wipe frame at the call site.  So this card runs the
    real thing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from pirateforce_foundation import mob_combat
        from pirateforce_foundation import world_population_bg0005
        from pirateforce_foundation.legacy_bridge import load_legacy

        cls.legacy = load_legacy(ROOT / "current" / "pf_login_game_server_v141.py")
        cls.anchor = mob_scene_recompose.census_anchor(
            EXPECTED_SCENE_ID, (10.0, 20.0, 30.0),
            world_population_bg0005.DEFAULT_ACTOR_COUNT,
        )
        cls.ledger = mob_combat.open_ledger_for_scene_id(EXPECTED_SCENE_ID)

    def test_scene_five_recomposes_a_full_census_rather_than_refusing(
            self) -> None:
        record = mob_scene_recompose.recompose_frames(
            self.legacy, self.anchor, mob_death.DeathRegister(),
            ledger=self.ledger,
        )
        self.assertEqual(
            record.state, mob_scene_recompose.STATE_COMPOSED,
            "a refused recompose is what the caller answers with the "
            "one-entry census RE-092 proved erases every other actor: "
            "state=%r detail=%r" % (record.state, getattr(record, "detail", None)),
        )
        self.assertTrue(record.composed)
        self.assertTrue(record.frame)
        self.assertEqual(record.scene, EXPECTED_SCENE)
        # The ledger this scene's own helper opens covers this scene's own
        # roster, so nothing is healed at ceiling behind a declined ledger.
        self.assertFalse(record.heals)
        self.assertEqual(
            record.ledger_covered, len(field_mobs.roster_for_scene_id(
                EXPECTED_SCENE_ID)))


class LaneComposedScenesAreNotFightableYetTest(unittest.TestCase):
    """THE SEAM THIS ROUND WALKED INTO -- UPDATED, round `9vec2s`, not
    deleted: the seam this card originally pinned is now OPEN, on a
    measurement, not by removing the card that named it shut.

    ORIGINAL FINDING (round jqeo2m, still true about the code as it stood
    then): a player in scene 5 could not damage anything, because scene 5
    arrives through ``runtime.py``'s LANE-COMPOSED census branch, and that
    branch stamped an EMPTY announced membership NO MATTER WHAT THE LANE
    COMPOSED -- ``SceneCensusResult`` carried no per-actor identity list at
    all, so the call site had nothing honest to announce.  The RE-157 gate
    refuses every unannounced target before cadence and before the ledger,
    so an empty announced membership meant no swing in a lane-composed
    scene could ever land, roster or no roster.

    WHAT CLOSED IT (CORE-REQUEST LANE-B 20260904_1134, chief round
    `9vec2s`): ``SceneCensusResult.actor_identities`` already existed
    (COO-DECISION 20260903_2247) and ``lane_a_scene_census.compose`` already
    populated it from ``field_mobs.roster_for_scene_id`` -- the gap was one
    call site in ``runtime.py`` that built the announced membership from a
    literal ``()`` instead of reading the field the composer had been
    filling in all along.  ``test_lane_scene_census_wiring.py``'s
    ``test_actor_identities_populate_the_announced_membership`` (and its
    three siblings: str-coercion, the untouched default, and the malformed-
    value refusal) is the measurement backing this: a lane-composed arrival
    now stamps the REAL roster the composer handed it, on a synthetic
    composer driven through the real dispatcher -- not scene 5 itself, and
    not a live attack.

    NOT CLAIMED HERE, still: that scene 5 (or 14) is fightable end to end.
    RE-157's cadence gate, the AI register, aggro, and every other combat
    precondition are untouched by this round and unmeasured by this file --
    see the OTHER classes in this module for scene 5's own combat-readiness
    tests, and ``pf_bridge/NOW.md``'s standing rule that GT (attended) tests
    against scene 5 wait for P-2 to close regardless of what the code can
    now do.  What changed is narrower and real: the announced-membership
    seam that made every lane-composed scene structurally unfightable, no
    matter how complete its roster, is gone.

    This card stays as the place a future round updates again, the same way
    this one did: with a measurement and a named PR, not a deletion.
    """

    def test_the_lane_composed_arrival_now_announces_a_real_roster(
            self) -> None:
        # Whitespace- and comment-marker-normalised, same reason the
        # original version of this test gave: the sentence this pins is
        # wrapped across several comment lines in the source, and a raw
        # substring search would break on a re-wrap that changed nothing.
        # (NOW.md: a PR that moves a string a test greps for must fix the
        # grep in the same round -- so the grep is made hard to break by
        # re-wrapping in the first place.)
        raw = (SRC / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8")
        runtime_src = " ".join(raw.replace("#", " ").split())
        self.assertIn(
            "SO A LANE-COMPOSED ARRIVAL CAN NOW ANNOUNCE A REAL ROSTER",
            runtime_src,
            "the lane-composed arrival branch's own justification has "
            "changed again.  Read the new wording at the "
            "mob_combat_announced_membership_generation call site (RE-157 "
            "job 2 / MOB-COMBAT-001) and pin the new fact here with a "
            "measurement -- do not delete this card, and do not just widen "
            "the assertion to match whatever text happens to be there.",
        )
        self.assertNotIn(
            "no lane scene a player can stand in and fight in exists yet",
            runtime_src,
            "the OLD justification this test used to pin is still present "
            "-- if the call site reverted to stamping an empty membership "
            "unconditionally, that is a regression of CORE-REQUEST "
            "LANE-B 20260904_1134, not a harmless leftover comment.",
        )

    def test_this_lane_announces_nine_lane_composed_scenes_now(
            self) -> None:
        """Named, so nobody arms a tenth without seeing the count move.

        ~~``test_this_lane_has_armed_two_scenes_behind_that_shut_seam``,
        pinning ``(5, 14)``.~~  MOVED TO THREE AND RENAMED, ROUND am1fw8:
        scene 3's roster and composer land this round, so the round that
        armed the third scene came here and said which, exactly as this card
        was built to force.  The name changed too, because the fact it names
        changed underneath it between round `9vec2s` and this one: the seam
        is OPEN.  These are no longer scenes armed behind a shut seam -- they
        are the scenes a lane-composed arrival now ANNOUNCES a real roster
        for, and scene 3 joined that set the moment ``field_mobs
        .roster_for_scene_id(3)`` stopped returning ``()``.  Measured, not
        inferred, in ``tests/test_field_mob_tables_bg0003.py``'s
        ``test_the_lane_composed_arrival_now_announces_all_twelve``.

        MOVED TO FOUR, ROUND r6isy5: scene 4 (Slave Market Island) joins,
        and this card's own condition -- say what else is shut -- is
        answered by saying that for this scene NOTHING in this lane is:
        ``scene_door_walk.describe_live_scene_doors`` walks it at
        ``target=7 kill=7 drop=7 every_door=yes`` on the same commit that
        registers it, the first scene this lane has armed through all three
        doors in ONE round (scene 3 needed two).  What IS shut, and is not
        this lane's to open, is the attended half: NOW.md forbids an
        on-screen monster-hit GT for scenes 3/4/5/14 until P-2 (monster
        name colour) closes, so no player has yet SEEN any of this.  The
        death ruling these seven rows travel under is the COO's 0546
        letter, whose five template ids are this lane's own answer awaiting
        confirmation -- see ``mob_death.WIDENING_RULINGS``' own entry.

        MOVED TO FIVE, ROUND (this round): scene 8 (Silver Harbour) joins.
        Nine placements mined, over seven distinct templates, but only SIX
        of the nine are what this lane SHIPS as attackable: placement 69
        (MOBS 529, "Nina") is a hostile-predicate row this lane withholds
        (``field_mobs.LANE_WITHHELD_PLACEMENTS['Bg0008']``), the same
        content-unknown reasoning already applied to Bg0015's Carlos.  The
        death ruling the six shipped templates travel under is the COO's
        0548 letter (``COO-DECISION widen-death-scope-bg0008-six-templates
        2026-09-06T05:48+07:00``); Nina's own content question travels
        under a separate letter and is not answered here.  NOW.md still
        forbids an on-screen monster-hit GT for scenes 3/4/5/8/14 until P-2
        closes, so no player has yet SEEN any of this either.

        MOVED TO NINE, ROUND 4tnhzw: scenes 6, 7, 9 and 11 join at once
        (COO-DECISION 2026-09-06T07:48+07:00) -- none of the four ships a
        town target, a legacy-pending row, or a withheld placement (no
        player-model avatar exists in any of their hostile sets), so unlike
        Bg0008's own arrival there is no "what else is shut" beyond the
        standing P-2 gate every scene here already carries.  The death
        ruling each of the four's own templates travels under is its own
        COO letter (see ``mob_death.WIDENING_RULINGS``' four new entries);
        Bg0009 additionally flags two rows (546, 549) as DROPS_UNMINED
        rather than withheld, named in ``field_mobs.DROPS_UNMINED_
        PLACEMENTS`` rather than here, since that flag does not change
        which scenes are in THIS set.

        The set is still written as a tuple and not a count for the same
        reason as before: a scene LEAVING it has to be as visible as one
        joining.
        """
        armed_behind_the_seam = tuple(
            scene_id for scene_id in sorted(mob_scene_recompose.composer_scene_ids())
            if scene_id not in (1, 2)
        )
        self.assertEqual(
            armed_behind_the_seam, (3, 4, 5, 6, 7, 8, 9, 11, 14),
            "a scene joined or left the set of lane-composed scenes this "
            "lane ships a roster for.  Scenes 1 and 2 have their own "
            "dedicated arrival branches in runtime.py; every other scene "
            "arrives lane-composed, and since chief's round `9vec2s` such "
            "an arrival announces the roster the composer hands it -- so a "
            "scene joining this tuple is a scene whose monsters become "
            "TARGETABLE.  Adding one is not wrong; shipping it as 'the "
            "player can now fight here' without saying what else is shut "
            "(a death ruling, a drop table) is.",
        )


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0005RegenerateTests(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_regenerating_reproduces_the_committed_module_byte_for_byte(
            self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        rule = tool.IDENTITY_RULE_CLINE
        controls = tool.check_crosswalk_controls(sources)
        census = tool.predicate_census(sources, rule)
        roster = tool.hostile_roster(sources, rule)
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census,
            rule=rule, cline_type=sources.cline_type,
            town=tool.town_target_roster(sources, rule),
            controls=controls,
            withdrawn=tool.withdrawn_under_rule(sources, rule),
            unresolved=tool.unresolved_placements(sources, rule),
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(sources, rule)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
        )
        self.assertEqual(
            regenerated, MODULE_PATH.read_text(encoding="ascii"),
            "src/pirateforce_foundation/field_mob_tables_bg0005.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene bg0005 --identity-rule cline --out "
            "<this file>",
        )

    def test_verify_frozen_runs_at_all_and_reproduces_bg0001(self) -> None:
        """``--verify-frozen`` is the generator's ONE checkable control, and
        it had been RAISING rather than verifying since
        ``unambiguous_placements`` grew an eighth tuple element: every call
        died on ``ValueError: too many values to unpack (expected 7)``, so
        the two scenes mined between that change and this round were mined
        with the control off.  Nothing caught it because nothing called this
        function -- so this test calls it.
        """
        tool = _load_tool()
        legacy = ROOT / "current" / "pf_login_game_server_v141.py"
        compared, mismatches = tool.verify_frozen(GAMEDATA, legacy)
        self.assertEqual(compared, tool.CONTROL_UNAMBIGUOUS_COUNT)
        self.assertEqual(mismatches, 0)


if __name__ == "__main__":
    unittest.main()
