"""LANE-A: the generation that belongs to the scene you just arrived in.

Every byte-level assertion in this file is made against the real frozen
encoder, ``current/pf_login_game_server_v141.py``, loaded the way the census
tests load it.  Doubles appear in exactly one place - the sabotage class - and
only to make the encoder MISBEHAVE, never to make it succeed.  Round e7q6yy
lost a whole adversary pass to a double that was kinder to this lane than the
real object was.

THE SECOND RULE THIS FILE FOLLOWS, added after the adversary pass of round
k69t3b mutated the module and watched three mutants survive: a refusal test
asserts WHICH refusal fired, by message.  ``assertRaises(Exception)`` around a
sabotage double also passes when the double failed to recognise its own mode,
so it cannot tell "the module refused" from "the test was misspelled".
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.population import (  # noqa: E402
    load_port_royal_placements,
)
from pirateforce_foundation.world_scene_travel import (  # noqa: E402
    CENSUS_SOURCE,
    destination,
    load_scene_registry,
    population_source,
    spawn_position,
)
from pirateforce_foundation.world_population import (  # noqa: E402
    CENSUS_COUNT,
    INITIAL_REAPPLY_MS,
    WIRE_COUNT_TAG_OFFSET,
    WIRE_HEADER_BYTES,
    build_world_population,
)
from pirateforce_foundation import world_density  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    world_population_bg0002,
    world_population_bg0015,
)
from pirateforce_foundation.world_population_handoff import (  # noqa: E402
    STOWAWAY_REPORT_RADIUS,
    stowaway_console_line,
    stowaways_near,
    stowaways_on_crossing,
    KIND_CENSUS,
    KIND_CLEAR,
    KIND_UNAVAILABLE,
    LABEL_CENSUS,
    LABEL_CLEAR,
    LABEL_UNAVAILABLE,
    SLOT_AFTER_TELEPORT,
    SLOT_BEFORE_TELEPORT,
    SLOT_NOT_APPLICABLE,
    MembershipReset,
    SceneHandoff,
    build_clear_generation,
    handoff_console_line,
    handoff_for_arrival,
    handoff_on_crossing,
    handoff_report,
    wire_count_of,
)

LEGACY_PATH = ROOT / "current/pf_login_game_server_v141.py"

# AMENDMENT 2026-08-28 (LANE-A, RE-128 / CLINE identities).  ``CENSUS_COUNT``
# (115) is the size of the frozen placement table and is unchanged.  What a
# home arrival ASSEMBLES is 108: seven of those placements have a Mob-Set
# number whose CLINE leader has no CONSTDATA MOBS row (or is 0, or has no
# avatar template), so they have no identity that can be shipped without
# reviving the numbering GT-078 disproved, and ``census_order`` drops them with
# a reason each.  Every assertion below that meant "the census as built" now
# reads this constant; the ones that mean "the size of the source table" still
# read CENSUS_COUNT.
SHIPPED_CENSUS_COUNT = 108

# ~~Every scene pinned in scenarios/world_scene_registry_001.json except home.
# 2 is the one this project has actually rendered besides Port Royal, 278 is
# the M2 stage, 997 is the pinned candidate COO-DECISION 0550 did not choose.
# None has a population table, and none may receive the dock census.
# NON_HOME_SCENES = (2, 278, 997)~~
#
# ROUND 80x5ba (LANE-A).  The struck comment said "none has a population
# table", and by the round it was written that was already false: scene 2 has
# had ``world_population_bg0002``'s roster since M1-P.  The list was doing two
# jobs at once - "not home" and "gets the empty generation" - and those stopped
# being the same set two rounds ago.  Split, so that a scene gaining a composer
# moves between two named lists instead of quietly changing what a test means.
#
# Scenes that arrive EMPTY, and the reason each one does.  278 is the M2 stage:
# its nine placements are Mob-Sets and resolving those to identities is the
# reading GT-078 rejected, so it stays empty by decision, not by omission.  997
# is the pinned candidate COO-DECISION 0550 did not choose and has no
# placements mined at all.
SCENES_WITHOUT_A_COMPOSER = (278, 997)

# Scenes that arrive POPULATED from this lane's own finished per-scene
# composers.  Both rosters are on main and tested in their own files; what is
# tested here is only that the seam hands each arrival ITS OWN roster.
# ~~COMPOSED_AWAY_SCENES = (2, 14)~~ -- SCENE 2 REMOVED, round ucaybn, by
# COO-DECISION 2026-08-29T22:45+07:00 (pf_bridge/notes_to_chief/20260829_2245_
# COO-DECISION-scene2-login-owns-composer-removed-from-crossing.md), answering
# this lane's ASK-COO 20260829_2110.  The login path owns scene 2: its
# populator carries lane B's faction splice and a combat-ledger sync that a
# crossing frame would silently replace.  Scene 2's new expected behaviour is
# pinned by test_a_login_owned_source_is_refused_by_name_not_by_omission.
COMPOSED_AWAY_SCENES = (14,)

# Home is still its own branch and its own builder, not a registry entry.
NON_HOME_SCENES = SCENES_WITHOUT_A_COMPOSER

# Each mode is a way the frozen encoder could drift or be replaced such that a
# frame this module calls a clear is not one, paired with the fragment of the
# refusal that has to fire for it.  The pairing is the point: it pins WHICH
# check caught it, so a check that stops catching anything shows up as a red
# test rather than as a mode some other check happens to cover.
SABOTAGE = {
    "raises": "encoder is gone",
    "not_a_pair": r"did not return \(pc, frame\)",
    "not_bytes": "not bytes",
    "empty_frame": "carries no frame",
    "foreign_frame": "does not match its own pc",
    "no_header": "expected collection header",
    # A real three-actor collection: its frame IS its own pc's frame, so the
    # pair check passes and the COUNT check is what refuses it.
    "counts_actors": "declares 3 actors",
    "lying_header": "declares 3 actors",
    "body_behind_zero": "bytes of body behind a zero count",
}


class _SabotagedEncoder:
    """A legacy stand-in whose ONLY job is to encode the clear frame wrongly.

    The client reads the count in the header and then reads that many actor
    bodies, so a header that lies is not cosmetic - it is the stream-tail
    misalignment this client answers with ErrorData=28317.

    An unknown mode raises at construction, not at call time: a mode name
    misspelled in a test must fail that test, not be absorbed by the module's
    own refusal path and read as a pass.
    """

    def __init__(self, mode: str, real):
        if mode not in SABOTAGE:
            raise AssertionError(f"unknown sabotage mode {mode!r}")
        self.mode = mode
        self.real = real
        self.calls = 0

    def make_runtime_remote_actors(self, entries):
        self.calls += 1
        if self.mode == "raises":
            raise RuntimeError("encoder is gone")
        if self.mode == "not_a_pair":
            return b"only-one-thing"
        if self.mode == "not_bytes":
            return ("pc", "frame")
        if self.mode == "empty_frame":
            pc, _ = self.real.make_runtime_remote_actors(())
            return (pc, b"")
        if self.mode == "foreign_frame":
            # The defect the pc-side checks cannot see at all: a valid empty
            # header, and the CENSUS on the wire behind it.  Only the frame
            # is sent (v141:7755), so every count read off the pc is a read of
            # a buffer the client never receives.
            pc, _ = self.real.make_runtime_remote_actors(())
            _, census_frame = self.real.make_v112_monster_shop_population_state()[:2]
            return (pc, census_frame)
        if self.mode == "no_header":
            pc = b"\x00" * WIRE_HEADER_BYTES
            return (pc, self.real.frame_pc(pc))
        if self.mode == "counts_actors":
            # The clear that quietly became a census: a real three-actor
            # collection returned for a request for none.
            return self.real.make_v112_monster_shop_population_state()[:2]
        if self.mode == "lying_header":
            # Header-length pc whose count field claims three actors with no
            # bodies behind it.  The ONLY check that can catch this is the
            # count check - the length check sees 17 bytes and is happy.
            pc, _ = self.real.make_runtime_remote_actors(())
            lying = bytearray(pc)
            lying[WIRE_COUNT_TAG_OFFSET + 1:WIRE_COUNT_TAG_OFFSET + 3] = (
                (3).to_bytes(2, "little")
            )
            pc = bytes(lying)
            return (pc, self.real.frame_pc(pc))
        if self.mode == "body_behind_zero":
            pc, _ = self.real.make_runtime_remote_actors(())
            pc = pc + b"\x99\x99\x99"
            return (pc, self.real.frame_pc(pc))
        raise AssertionError(f"unhandled sabotage mode {self.mode}")

    def __getattr__(self, name):
        return getattr(self.real, name)


class HandoffTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.anchor = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.far_anchor = (
            cls.legacy.V112_PLAYER_X,
            cls.legacy.V112_PLAYER_Y,
            cls.legacy.V112_PLAYER_Z,
        )

    # ---- the clear frame, measured on the frozen encoder -----------------

    def test_the_clear_frame_is_a_collection_that_declares_no_actors(self):
        pc, frame = build_clear_generation(self.legacy)
        self.assertEqual(len(pc), WIRE_HEADER_BYTES)
        self.assertEqual(wire_count_of(pc), 0)
        self.assertTrue(frame)

    def test_the_bytes_that_are_sent_are_the_bytes_that_were_checked(self):
        """v141:7755 sends the frame; every other check in the module reads pc.

        Without this the module could validate an empty header and ship a
        census behind it, which is the sabotage mode ``foreign_frame``.
        """
        pc, frame = build_clear_generation(self.legacy)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        census = handoff_for_arrival(self.legacy, 1, self.anchor)
        self.assertEqual(census.frame, self.legacy.frame_pc(census.pc))

    def test_the_clear_frame_does_not_depend_on_where_the_player_stands(self):
        """A clear is the same bytes from anywhere; only a census is anchored."""
        first = handoff_for_arrival(self.legacy, 278, self.anchor)
        second = handoff_for_arrival(self.legacy, 278, self.far_anchor)
        self.assertEqual(first.pc, second.pc)
        self.assertEqual(first.frame, second.frame)

    def test_every_scene_without_a_population_table_gets_the_clear(self):
        for scene in NON_HOME_SCENES:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(handoff.kind, KIND_CLEAR)
                self.assertEqual(handoff.actor_count, 0)
                self.assertEqual(handoff.membership, ())
                self.assertEqual(wire_count_of(handoff.pc), 0)
                self.assertIsNone(handoff.generation)
                self.assertIsNone(handoff.reapply_ms)
                self.assertEqual(handoff.label, LABEL_CLEAR.format(scene))
                self.assertTrue(handoff.sends_a_frame)

    def test_the_dock_census_can_never_be_the_answer_for_another_scene(self):
        """The refusal that matters most, checked at the bytes not the branch.

        A census delivered into scene 278 is 115 Port Royal NPCs standing in a
        football field at bg0001 coordinates.  No non-home scene may come back
        with a frame that declares actors, whatever the caller asked for.
        """
        for scene in SCENES_WITHOUT_A_COMPOSER:
            for requested in (None, 3, CENSUS_COUNT):
                with self.subTest(scene=scene, actor_count=requested):
                    handoff = handoff_for_arrival(
                        self.legacy, scene, self.anchor, actor_count=requested
                    )
                    self.assertEqual(wire_count_of(handoff.pc), 0)

    def test_a_composed_scene_gets_its_own_roster_and_never_the_dock_census(self):
        """ROUND 80x5ba: the same refusal, for the scenes that now DO populate.

        A scene that arrives populated is the case where "some other scene's
        actors" is possible at all - the empty branch cannot get it wrong,
        because it has no bodies to get wrong.  So this is where the check
        belongs now, and it is made at the BYTES: the frame a composed arrival
        carries must be byte-for-byte the frame that scene's OWN builder
        produces, and must differ from the dock census.
        """
        home = handoff_for_arrival(self.legacy, 1, self.anchor)
        # ~~(2, world_population_bg0002.build_bg0002_population),~~ removed
        # round ucaybn with the scene 2 registry entry (COO-DECISION
        # 20260829_2245).  Scene 2's own byte-level pins live in its own
        # file; here it is covered by the login-owned refusal test instead.
        for scene, build in (
            (14, world_population_bg0015.build_bg0015_population),
        ):
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(handoff.kind, KIND_CENSUS)
                self.assertNotEqual(handoff.pc, home.pc)
                self.assertNotEqual(handoff.frame, home.frame)
                direct = build(
                    self.legacy, self.anchor, scene_id=scene,
                    count_source=(
                        world_population_bg0015.COUNT_SOURCE_FULL_ROSTER
                    ),
                )
                self.assertEqual(handoff.pc, direct.pc)
                self.assertEqual(handoff.frame, direct.frame)
                self.assertEqual(
                    handoff.membership, tuple(direct.placement_indices))
                self.assertEqual(
                    wire_count_of(handoff.pc), len(handoff.membership))
                self.assertEqual(handoff.actor_count, len(handoff.membership))
                self.assertGreater(handoff.actor_count, 0)

    def test_every_scene_prints_a_readable_console_line(self):
        """The line a tester greps must survive for EVERY scene, not most.

        THIS TEST EXISTS BECAUSE THE ROUND THAT ADDED THE ROSTER BRANCH SHIPPED
        THIS BUG PAST ITS OWN SUITE.  ``handoff_report`` described the
        generation with ``world_population.dispatch_report``, which reads
        fields only the home census carries, so a roster generation raised
        ValueError inside it - and ``handoff_console_line`` catches
        BaseException by contract, so scene 2 and scene 14 printed exactly
        ``WORLD_POP_HANDOFF unreportable reason=ValueError`` and nothing else.
        Every assertion in this file was on the OBJECT; not one printed the
        line.  A tester on GT-131's successor would have had no number to read
        for the two scenes this change exists to populate.
        """
        for scene in (1,) + COMPOSED_AWAY_SCENES + SCENES_WITHOUT_A_COMPOSER:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                line = handoff_console_line(handoff)
                self.assertNotIn("unreportable", line)
                self.assertIn("scene=%d" % scene, line)
                self.assertIn("wire=%d" % wire_count_of(handoff.pc), line)
                self.assertIn("actors=%d" % handoff.actor_count, line)
                # And the report it is built from carries the composer's own
                # description, not a hole where one failed.
                report = handoff_report(handoff)
                if handoff.kind == KIND_CENSUS:
                    self.assertIsInstance(report["census"], dict)
                    self.assertNotEqual(report["census"], {})

    # ---- the caller-count branch, which had never executed ---------------
    #
    # pf-adversary (round 80x5ba, D5) traced this file against the module and
    # measured lines 577-584 - the whole ``actor_count is not None`` branch of
    # _roster_handoff - as NEVER RUN, with nine mutants surviving inside it.
    # Everything from here to the ownership test below exists to execute it.

    def test_a_rung_above_a_roster_is_capped_not_refused(self):
        """D2: the regression that made a safe CLEAR into a silent stale town.

        ``actor_count`` is documented as a CEILING RUNG.  The obvious caller
        reads it from ``census_count_for_dispatch()`` - 108, the HOME ceiling -
        and hands it to whatever scene the player arrived in.  Handed
        unchanged to a 97-actor roster, the builder refused the whole rung,
        ``handoff_on_crossing`` turned that into KIND_UNAVAILABLE, and
        UNAVAILABLE SENDS NO FRAME: the player keeps the town they just left.
        Before this round the same call returned an empty map, which is
        strictly safer.  A ceiling is a min.
        """
        # ~~((2, 97), (14, 81))~~ -- scene 2 removed with its registry entry,
        # round ucaybn (COO-DECISION 20260829_2245).  The cap rule itself is
        # unchanged and is what this test is about.
        for scene, roster_count in ((14, 81),):
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(
                    self.legacy, scene, self.anchor, actor_count=CENSUS_COUNT)
                self.assertEqual(handoff.kind, KIND_CENSUS)
                self.assertEqual(handoff.actor_count, roster_count)
                self.assertEqual(wire_count_of(handoff.pc), roster_count)
                # The cap is reported, not swallowed.
                self.assertIn("capped_from_%d" % CENSUS_COUNT, handoff.reason)
                # And the frame path agrees with the strict path.
                self.assertEqual(
                    handoff_on_crossing(
                        self.legacy, scene, self.anchor,
                        actor_count=CENSUS_COUNT).kind,
                    KIND_CENSUS,
                )

    def test_a_rung_below_a_roster_is_honoured_exactly(self):
        """Capping is downward only - a smaller rung is still the caller's."""
        for scene in COMPOSED_AWAY_SCENES:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(
                    self.legacy, scene, self.anchor, actor_count=5)
                self.assertEqual(handoff.actor_count, 5)
                self.assertEqual(wire_count_of(handoff.pc), 5)
                self.assertNotIn("capped_from", handoff.reason)

    def test_the_count_source_a_roster_records_matches_what_was_asked_for(self):
        """D5, mutants g and h: the recording was untested in both directions.

        bg0002 has no "full roster implies the full count" guard of its own, so
        a 5-actor slice labelled ``bg0002_full_roster`` would print
        ``assembled=5/97 source=bg0002_full_roster`` with 92 unexplained - the
        defect pf-adversary closed in bg0015 and bg0002 still does not have.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        for scene in COMPOSED_AWAY_SCENES:
            composer = handoff_mod.ROSTER_COMPOSERS[
                population_source(scene)]
            with self.subTest(scene=scene, rung="full"):
                full = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(
                    full.generation.count_source,
                    composer.full_roster_count_source)
            with self.subTest(scene=scene, rung="slice"):
                sliced = handoff_for_arrival(
                    self.legacy, scene, self.anchor, actor_count=5)
                self.assertEqual(
                    sliced.generation.count_source,
                    composer.caller_count_source)
            with self.subTest(scene=scene, rung="capped_to_full"):
                # A capped rung IS the full roster, so it must be recorded as
                # one - the honest label for the bytes that went out.
                capped = handoff_for_arrival(
                    self.legacy, scene, self.anchor, actor_count=CENSUS_COUNT)
                self.assertEqual(
                    capped.generation.count_source,
                    composer.full_roster_count_source)

    def test_a_roster_rejects_a_count_that_is_not_an_integer(self):
        """D5, mutant m: the type check in the caller branch never ran."""
        for bad in (3.0, "3", True, None.__class__):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as caught:
                    handoff_for_arrival(
                        self.legacy, 14, self.anchor, actor_count=bad)
                self.assertIn("actor count must be an int", str(caught.exception))

    def test_a_roster_frame_is_checked_against_its_own_pc(self):
        """D5, mutant k: deleting _require_pair in _roster_handoff was green.

        Sabotaged the way this file sabotages everything else - the encoder is
        made to misbehave, never made to succeed - by handing the composer a
        builder whose frame does not belong to its pc.  ``v141:7755`` sends the
        frame and nothing else, so a pc that was validated while a foreign
        frame goes out is a check that reads a buffer the client never sees.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        from dataclasses import replace
        original = dict(handoff_mod.ROSTER_COMPOSERS)
        honest = original["bg0015_roster"]

        def build_with_a_foreign_frame(*args, **kwargs):
            generation = honest.build(*args, **kwargs)
            return replace(generation, frame=generation.frame + b"\x00")

        try:
            handoff_mod.ROSTER_COMPOSERS["bg0015_roster"] = replace(
                honest, build=build_with_a_foreign_frame)
            with self.assertRaises(ValueError) as caught:
                handoff_for_arrival(self.legacy, 14, self.anchor)
            self.assertIn("does not match its own pc", str(caught.exception))
            self.assertEqual(
                handoff_on_crossing(self.legacy, 14, self.anchor).kind,
                KIND_UNAVAILABLE,
            )
        finally:
            handoff_mod.ROSTER_COMPOSERS.clear()
            handoff_mod.ROSTER_COMPOSERS.update(original)

    def test_the_report_names_which_schema_its_census_block_is_in(self):
        """D4: three schemas, and before this there was no discriminator.

        ``report["census"]`` is the home census's dict for scene 1
        (``census_count``), bg0002's for scene 2 (``roster_count``), bg0015's
        for scene 14 (adds ``placement_count``).  A consumer reading
        ``census_count`` - the only read that existed before this round - gets
        a KeyError on the two new scenes, and every caller is behind a
        catch-all, so it surfaces as the same "unreportable" this round
        already fixed once from another cause.
        """
        # ~~(2, "bg0002_roster", "roster_count"),~~ -- removed round ucaybn
        # with the scene 2 registry entry (COO-DECISION 20260829_2245).  Scene
        # 2 is now asserted on the CLEARED side below, which is the whole
        # point of the ruling: this seam reports no census for it at all.
        expectations = (
            (1, CENSUS_SOURCE, "census_count"),
            (14, "bg0015_roster", "roster_count"),
        )
        for scene, source, key in expectations:
            with self.subTest(scene=scene):
                report = handoff_report(
                    handoff_for_arrival(self.legacy, scene, self.anchor))
                self.assertEqual(report["census_source"], source)
                self.assertIn(key, report["census"])
        for cleared_scene in (2, 278):
            with self.subTest(scene=cleared_scene):
                cleared = handoff_report(
                    handoff_for_arrival(self.legacy, cleared_scene, self.anchor))
                self.assertIsNone(cleared["census_source"])
                self.assertIsNone(cleared["census"])

    def test_a_census_handoff_cannot_disagree_with_its_own_generation(self):
        """D6: the two fields that had to be kept in step by hand.

        The dangerous half is the silent one: a roster generation with the
        membership left at its default reported "this frame put nobody on the
        client" while shipping 97 actors, which is the state where one
        ChooseNPC recomposes the old town inside the new map.
        """
        roster = handoff_for_arrival(self.legacy, 14, self.anchor)
        with self.assertRaises(ValueError) as caught:
            SceneHandoff(
                scene_id=14, kind=KIND_CENSUS, reason="hand_built_for_this_test",
                label=LABEL_CENSUS.format(14), actor_count=81,
                pc=roster.pc, frame=roster.frame, reapply_ms=None,
                dispatch_slot=SLOT_AFTER_TELEPORT,
                generation=roster.generation,
            )
        self.assertIn("does not match its own generation", str(caught.exception))
        # The home census is held to it too, not only the rosters.
        home = handoff_for_arrival(self.legacy, 1, self.anchor)
        with self.assertRaises(ValueError):
            SceneHandoff(
                scene_id=1, kind=KIND_CENSUS, reason="hand_built_for_this_test",
                label=LABEL_CENSUS.format(1), actor_count=SHIPPED_CENSUS_COUNT,
                pc=home.pc, frame=home.frame, reapply_ms=None,
                dispatch_slot=SLOT_AFTER_TELEPORT,
                generation=home.generation,
                membership_indices=(1, 2, 3),
            )

    def test_the_two_tables_that_add_a_scene_must_agree(self):
        """D7: adding one of the two entries is a silent skip.

        A source named in CENSUS_SOURCES with no composer falls to the CLEAR
        branch and prints ``..._has_no_crossing_handoff_yet`` - the exact
        string scene 14 printed at this lane for three rounds about code that
        was already written.  A composer with no source row is dead code.
        Neither is visible without this test.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        from pirateforce_foundation.world_scene_travel import CENSUS_SOURCES
        named = set(CENSUS_SOURCES.values()) - {CENSUS_SOURCE}
        composed = set(handoff_mod.ROSTER_COMPOSERS)
        ruled_out = set(handoff_mod.LOGIN_OWNED_SOURCES)
        # WIDENED round ucaybn.  ~~named - composed == set()~~ became false by
        # RULING, not by drift, when scene 2's entry was removed
        # (COO-DECISION 20260829_2245).  The property that still has to hold
        # is the one D7 was really about: a named source is either BUILT here
        # or RULED OUT here, never merely absent - because "absent" reads the
        # same as "nobody got round to it" and is what would put the scene 2
        # entry straight back.
        self.assertEqual(
            named - composed - ruled_out, set(),
            "a scene names a composer that is neither in ROSTER_COMPOSERS nor "
            "ruled out in LOGIN_OWNED_SOURCES, so it silently arrives empty",
        )
        self.assertEqual(
            composed - named, set(),
            "a composer is registered that no scene routes to, so it is dead",
        )
        self.assertEqual(
            ruled_out - named, set(),
            "a source is ruled out that no scene names, so the ruling guards "
            "nothing",
        )
        self.assertEqual(
            composed & ruled_out, set(),
            "a source is both built and ruled out - the ruling would be "
            "silently overridden by the composer",
        )
        # And every registered composer answers for the scene that names it.
        for scene, source in CENSUS_SOURCES.items():
            if source == CENSUS_SOURCE or source in ruled_out:
                continue
            with self.subTest(scene=scene):
                composer = handoff_mod.ROSTER_COMPOSERS[source]
                self.assertEqual(composer.source, source)
                built = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertIs(
                    type(built.generation), composer.generation_type)

    def test_a_login_owned_source_is_refused_by_name_not_by_omission(self):
        """COO-DECISION 20260829_2245, carried out in round ucaybn.

        Scene 2 arrives CLEAR from this seam again, as it did before round
        80x5ba - but the reason string is the ruling, not the to-do.  That
        difference is the whole test: a reader who greps
        ``has_no_crossing_handoff_yet`` for scene 2 would conclude the entry
        is missing and add it back, and adding it back without lane B's
        ledger+faction half is the regression the ruling exists to prevent.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        from pirateforce_foundation.world_scene_travel import CENSUS_SOURCES
        for source, ruling in handoff_mod.LOGIN_OWNED_SOURCES.items():
            scenes = [s for s, name in CENSUS_SOURCES.items() if name == source]
            self.assertTrue(scenes, "a ruling that names no scene")
            for scene in scenes:
                with self.subTest(scene=scene, source=source):
                    handoff = handoff_for_arrival(
                        self.legacy, scene, self.anchor
                    )
                    self.assertEqual(handoff.kind, KIND_CLEAR)
                    self.assertIsNone(handoff.generation)
                    self.assertEqual(handoff.actor_count, 0)
                    self.assertIn("login_path_owns_this_source", handoff.reason)
                    self.assertIn(ruling, handoff.reason)
                    self.assertNotIn(
                        "has_no_crossing_handoff_yet", handoff.reason
                    )

    def test_a_scene_left_empty_on_purpose_says_so_by_name(self):
        """D8c: "by decision, not by omission" was a claim the code denied.

        278 was simply absent from CENSUS_SOURCES and printed the same
        ``has_no_population_table`` as a scene nobody has ever considered.  A
        decision indistinguishable from an oversight is an oversight.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        for scene in handoff_mod.SCENES_INTENTIONALLY_UNPOPULATED:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(handoff.kind, KIND_CLEAR)
                self.assertIn("left_empty_on_purpose", handoff.reason)
        self.assertIn(
            "re152", handoff_for_arrival(self.legacy, 278, self.anchor).reason)
        # A scene nobody has considered still reads differently.
        unconsidered = handoff_for_arrival(self.legacy, 4242, self.anchor)
        self.assertIn("has_no_population_table", unconsidered.reason)
        self.assertNotIn("on_purpose", unconsidered.reason)

    def test_a_membership_from_another_scene_is_refused_not_renamed(self):
        """D3: Port Royal names printed for a Hell Volcano roster.

        ``stowaways_near`` resolves every index against the bg0001 table.
        Before this round the only non-empty membership was scene 1's, so that
        was sound; the moment this module composes rosters it is not, and
        pf-adversary measured ``nearest=Columbus`` - a Port Royal dock NPC -
        reported for a player on Hell Volcano Island, with no refusal at all.
        At larger counts it refused by ACCIDENT, blaming table drift.
        """
        roster = handoff_for_arrival(
            self.legacy, 14, self.anchor, actor_count=5)
        # The accidental-silence case: five indices bg0001 also happens to have.
        with self.assertRaises(ValueError) as caught:
            stowaways_near(
                self.legacy, roster.membership, self.anchor,
                membership_scene_id=14,
            )
        self.assertIn("cannot be named here", str(caught.exception))
        # The frame path degrades to a named refusal, never to wrong names.
        view = stowaways_on_crossing(
            self.legacy, roster.membership, self.anchor, membership_scene_id=14)
        self.assertIsNotNone(view.reason)
        self.assertEqual(view.within_radius, ())
        self.assertIsNone(view.nearest)
        line = stowaway_console_line(view)
        self.assertNotIn("Columbus", line)
        # Home is unchanged: every caller in this tree passes a scene-1
        # membership and must keep getting names.
        home = handoff_for_arrival(self.legacy, 1, self.anchor)
        named = stowaways_near(self.legacy, home.membership, self.anchor)
        self.assertEqual(named.held, SHIPPED_CENSUS_COUNT)

    def test_a_composed_arrival_is_anchored_where_the_player_lands(self):
        """Unlike a clear, a roster is built at the arrival point.

        The clear is the same bytes from anywhere (the test above pins that).
        A roster must NOT be: actors composed around the departure point put
        the whole scene in the wrong place relative to the player.
        """
        for scene in COMPOSED_AWAY_SCENES:
            with self.subTest(scene=scene):
                near = handoff_for_arrival(self.legacy, scene, self.anchor)
                far = handoff_for_arrival(self.legacy, scene, self.far_anchor)
                self.assertEqual(near.generation.anchor, self.anchor)
                self.assertEqual(far.generation.anchor, self.far_anchor)
                self.assertEqual(
                    near.membership_reset.population_refresh_anchor,
                    self.anchor,
                )

    def test_a_composed_arrival_carries_the_addition_ordering_and_a_reapply(self):
        for scene in COMPOSED_AWAY_SCENES:
            with self.subTest(scene=scene):
                handoff = handoff_for_arrival(self.legacy, scene, self.anchor)
                self.assertEqual(handoff.dispatch_slot, SLOT_AFTER_TELEPORT)
                self.assertEqual(handoff.reapply_ms, INITIAL_REAPPLY_MS)
                self.assertEqual(handoff.label, LABEL_CENSUS.format(scene))
                self.assertIn(str(scene), handoff.reason)
                self.assertTrue(handoff.sends_a_frame)

    def test_the_membership_reset_of_a_composed_arrival_is_not_empty(self):
        """The trap the roster generations set for this module.

        Both rosters call their membership ``placement_indices``; the home
        census calls it ``indices``.  A reset that read ``generation.indices``
        would have raised on every composed arrival, and one that reached for
        the name with a bare ``getattr(..., ())`` would have reported "this
        frame put nobody on the client" while shipping a full roster - which
        is the state that lets one ChooseNPC recompose the old town into the
        new map.
        """
        for scene in COMPOSED_AWAY_SCENES:
            with self.subTest(scene=scene):
                reset = handoff_for_arrival(
                    self.legacy, scene, self.anchor).membership_reset
                self.assertFalse(reset.clears_everything)
                self.assertIsNotNone(reset.population_indices)
                self.assertGreater(len(reset.population_indices), 0)
                self.assertEqual(
                    reset.population_refresh_anchor, self.anchor)

    def test_a_header_that_disagrees_with_the_membership_is_refused(self):
        """The check that survived this round's own first mutation run.

        Deleting ``declared != len(membership)`` left the whole suite green,
        because nothing in it could make the two disagree: the real builders
        always agree with themselves, so the check was untested rather than
        redundant.  It is not a tautology - the header is read back out of the
        composed BYTES and the membership out of the generation's own field,
        which is exactly the pair that comes apart when an encoder or a reader
        drifts, and a header promising more bodies than the payload carries is
        the client error (ErrorData=28317) this project has already paid for.

        Driven the only way it can be: a composer whose membership reader
        under-reports by one, which is what a drifting reader looks like.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        original = dict(handoff_mod.ROSTER_COMPOSERS)
        # ~~honest = original["bg0002_roster"]~~ -- driven on scene 14 since
        # round ucaybn: scene 2's entry was removed by COO-DECISION
        # 20260829_2245.  The property is the composer's, not the scene's.
        honest = original["bg0015_roster"]
        try:
            from dataclasses import replace
            handoff_mod.ROSTER_COMPOSERS["bg0015_roster"] = replace(
                honest,
                membership_of=lambda generation: tuple(
                    generation.placement_indices)[:-1],
            )
            with self.assertRaises(ValueError) as caught:
                handoff_for_arrival(self.legacy, 14, self.anchor)
            self.assertIn("encoder or reader drift", str(caught.exception))
            # And it is the strict path that raises: the frame path still
            # refuses instead of killing the connection.
            refused = handoff_on_crossing(self.legacy, 14, self.anchor)
            self.assertEqual(refused.kind, KIND_UNAVAILABLE)
            self.assertFalse(refused.sends_a_frame)
        finally:
            handoff_mod.ROSTER_COMPOSERS.clear()
            handoff_mod.ROSTER_COMPOSERS.update(original)

    def test_a_composed_scene_refuses_a_roster_built_for_another_scene(self):
        """The second lock: the arrival scene is handed to the builder.

        If ``CENSUS_SOURCES`` ever names the wrong composer for a scene, the
        builder's own scene guard has to fire.  Simulated by pointing the
        registry entry for scene 14 at bg0002's composer - the exact shape of
        a one-character edit in that table - and the arrival must refuse
        rather than deliver Prison Exile's NPCs into the volcano.
        """
        import pirateforce_foundation.world_population_handoff as handoff_mod
        from dataclasses import replace
        original = dict(handoff_mod.ROSTER_COMPOSERS)
        try:
            # ~~= original["bg0002_roster"]~~ -- that entry was removed round
            # ucaybn (COO-DECISION 20260829_2245), so the wrong builder is
            # spliced in directly rather than borrowed from a sibling entry.
            # The simulated edit is the same one: scene 14's row now reaches
            # Prison Exile's builder, and the builder's own scene guard is
            # what has to refuse.
            handoff_mod.ROSTER_COMPOSERS["bg0015_roster"] = replace(
                original["bg0015_roster"],
                build=world_population_bg0002.build_bg0002_population,
            )
            with self.assertRaises(Exception) as caught:
                handoff_for_arrival(self.legacy, 14, self.anchor)
            self.assertIn("scene", str(caught.exception).lower())
            # And the frame path turns that raise into a refusal, not a crash.
            refused = handoff_on_crossing(self.legacy, 14, self.anchor)
            self.assertEqual(refused.kind, KIND_UNAVAILABLE)
            self.assertFalse(refused.sends_a_frame)
        finally:
            handoff_mod.ROSTER_COMPOSERS.clear()
            handoff_mod.ROSTER_COMPOSERS.update(original)

    # ---- ordering --------------------------------------------------------

    def test_the_removal_goes_before_the_teleport_and_the_addition_after(self):
        """The ordering rule lives on the object, not in prose to remember.

        The clear belongs to the scene the client is still in - the only state
        anyone has observed omission behave in.  The census belongs to the
        scene it is going to, or 115 actors tagged scene 1 arrive while the
        client still renders 278.
        """
        for scene in NON_HOME_SCENES:
            with self.subTest(scene=scene):
                self.assertEqual(
                    handoff_for_arrival(self.legacy, scene, self.anchor).dispatch_slot,
                    SLOT_BEFORE_TELEPORT,
                )
        self.assertEqual(
            handoff_for_arrival(self.legacy, 1, self.anchor).dispatch_slot,
            SLOT_AFTER_TELEPORT,
        )
        self.assertEqual(
            handoff_on_crossing(None, 278, self.anchor).dispatch_slot,
            SLOT_NOT_APPLICABLE,
        )

    # ---- the home return -------------------------------------------------

    def test_the_return_generation_is_the_census_module_s_own_frame(self):
        """Deliberately narrow: this proves the module delegates, nothing more.

        It does NOT prove equivalence with the login path - nothing in this
        repository composes that path today (`WORLD_CENSUS_INITIAL_` is in an
        unmerged PR), so an equivalence claim here would be a claim about code
        that is not in the tree.  A regression inside ``build_world_population``
        moves both sides of this assertion equally, and that is what
        ``tests/test_world_population.py`` is for.
        """
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor)
        direct = build_world_population(
            self.legacy, self.anchor, CENSUS_COUNT, scene_id=1,
            count_source="full_census",
        )
        self.assertEqual(handoff.kind, KIND_CENSUS)
        self.assertEqual(handoff.pc, direct.pc)
        self.assertEqual(handoff.frame, direct.frame)
        # Was CENSUS_COUNT on both lines.  SUPERSEDED 2026-08-28 (RE-128): a
        # request for the whole census assembles 108, and the handoff reports
        # what assembled - which is exactly the delegation this test is about.
        self.assertEqual(handoff.actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(wire_count_of(handoff.pc), SHIPPED_CENSUS_COUNT)
        self.assertEqual(handoff.reapply_ms, INITIAL_REAPPLY_MS)
        self.assertEqual(handoff.label, LABEL_CENSUS.format(1))

    def test_the_return_census_stands_the_town_around_where_you_came_back_in(self):
        """Membership is the whole census; ORDER is anchored to the arrival."""
        near = handoff_for_arrival(self.legacy, 1, self.anchor)
        far = handoff_for_arrival(self.legacy, 1, self.far_anchor)
        self.assertEqual(set(near.membership), set(far.membership))
        self.assertNotEqual(near.membership, far.membership)
        self.assertNotEqual(near.pc, far.pc)

    def test_the_membership_the_caller_needs_for_population_indices_is_offered(self):
        """v141:4396-4420 answers ChooseNPC for anything in that set.

        A caller that queues a clear and leaves the set alone can have the
        whole town recomposed into the new scene by one click; the set is
        runtime.py's, but it cannot be corrected without this list.
        """
        census = handoff_for_arrival(self.legacy, 1, self.anchor)
        # Was CENSUS_COUNT; the membership offered is the membership built,
        # which is 108 since RE-128 dropped the seven unshippable placements.
        self.assertEqual(len(census.membership), SHIPPED_CENSUS_COUNT)
        self.assertEqual(handoff_report(census)["membership"], census.membership)
        clear = handoff_for_arrival(self.legacy, 278, self.anchor)
        self.assertEqual(handoff_report(clear)["membership"], ())

    def test_a_caller_chosen_count_is_recorded_as_the_callers(self):
        """CHARTER-02: a short frame arrives with its reason attached."""
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor, actor_count=3)
        report = handoff_report(handoff)
        self.assertEqual(report["actor_count"], 3)
        self.assertEqual(report["wire_actor_count"], 3)
        self.assertEqual(report["census"]["count_source"], "caller_requested")
        self.assertEqual(report["census"]["shortfall_reason"], "caller_requested=3")

    # ---- the frame path must never raise ---------------------------------

    def test_the_crossing_entry_point_does_not_raise_on_anything(self):
        """The contract that the last round of this lane broke by omission."""
        cases = (
            ("legacy_none", None, 278, self.anchor, {}),
            ("scene_is_a_string", self.legacy, "278", self.anchor, {}),
            ("scene_is_a_bool", self.legacy, True, self.anchor, {}),
            ("scene_is_zero", self.legacy, 0, self.anchor, {}),
            ("scene_out_of_range", self.legacy, 0x10000, self.anchor, {}),
            ("scene_is_non_ascii", self.legacy, "日本", self.anchor, {}),
            ("anchor_is_none", self.legacy, 1, None, {}),
            ("anchor_is_short", self.legacy, 1, (1.0, 2.0), {}),
            ("anchor_has_a_string", self.legacy, 1, (1.0, 2.0, "z"), {}),
            ("anchor_is_non_ascii", self.legacy, 1, (1.0, 2.0, "位"), {}),
            ("anchor_is_a_list", self.legacy, 1, [1.0, 2.0, 3.0], {}),
            ("anchor_is_nan_free_but_huge", self.legacy, 1, (1e40, 0.0, 0.0), {}),
            ("count_is_a_string", self.legacy, 1, self.anchor,
             {"actor_count": "three"}),
            ("count_is_a_bool", self.legacy, 1, self.anchor,
             {"actor_count": True}),
            ("count_is_zero", self.legacy, 1, self.anchor, {"actor_count": 0}),
            ("count_is_negative", self.legacy, 1, self.anchor,
             {"actor_count": -5}),
            ("count_is_over_the_census", self.legacy, 1, self.anchor,
             {"actor_count": 10_000}),
        )
        for name, legacy, scene, anchor, kwargs in cases:
            with self.subTest(case=name):
                handoff = handoff_on_crossing(legacy, scene, anchor, **kwargs)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                self.assertEqual(handoff.pc, b"")
                self.assertEqual(handoff.frame, b"")
                self.assertFalse(handoff.sends_a_frame)
                self.assertEqual(handoff.dispatch_slot, SLOT_NOT_APPLICABLE)
                self.assertEqual(handoff.label, LABEL_UNAVAILABLE)
                self.assertTrue(handoff.reason.startswith("handoff_not_composed:"))
                handoff_console_line(handoff).encode("ascii")

    def test_an_exception_whose_message_cannot_be_printed_is_still_printed(self):
        """A refusal a cp874 console cannot encode is a refusal nobody reads.

        Two shapes: a message with characters outside ASCII, and one with a
        bare CR, which on a Windows console rewrites the line it was meant to
        add rather than appearing beneath it.
        """

        class _Rude:
            def __init__(self, text):
                self.text = text

            def make_runtime_remote_actors(self, entries):
                raise RuntimeError(self.text)

        for name, text in (
            ("non_ascii", "เสีย"),
            ("carriage_return", "line one\rline two"),
            ("newline", "line one\nline two"),
        ):
            with self.subTest(case=name):
                handoff = handoff_on_crossing(_Rude(text), 278, self.anchor)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                line = handoff_console_line(handoff)
                line.encode("ascii")
                line.encode("cp874")
                self.assertNotIn("\r", line)
                self.assertNotIn("\n", line)

    def test_an_exception_whose_str_itself_raises_is_still_a_refusal(self):
        class _Unprintable(Exception):
            def __str__(self):
                raise ValueError("even the message is broken")

        class _Worse:
            def make_runtime_remote_actors(self, entries):
                raise _Unprintable()

        handoff = handoff_on_crossing(_Worse(), 278, self.anchor)
        self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
        self.assertIn("unprintable", handoff.reason)
        handoff_console_line(handoff).encode("ascii")

    def test_an_interrupt_is_not_swallowed(self):
        """The one deliberate hole in "never raises", pinned so it stays one.

        A frame handler that eats KeyboardInterrupt is a process the operator
        cannot stop at the moment they are trying to stop it.
        """

        class _Interrupts:
            def make_runtime_remote_actors(self, entries):
                raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            handoff_on_crossing(_Interrupts(), 278, self.anchor)

    def test_the_console_helper_does_not_raise_either(self):
        """It is called from the same block, to print the refusal."""
        for bad in (None, 42, "handoff", object(), b""):
            with self.subTest(value=repr(bad)[:20]):
                line = handoff_console_line(bad)
                self.assertIn("WORLD_POP_HANDOFF", line)
                line.encode("ascii")

    def test_an_encoder_that_misbehaves_refuses_by_the_check_that_owns_it(self):
        """Each sabotage pinned to the refusal that must catch it.

        Not ``assertRaises(Exception)``: that passes when a check has stopped
        firing and some other one happens to cover the mode, which is how the
        first version of this file let a deleted count check survive.
        """
        for mode, expected in SABOTAGE.items():
            with self.subTest(mode=mode):
                sabotaged = _SabotagedEncoder(mode, self.legacy)
                with self.assertRaisesRegex(Exception, expected):
                    build_clear_generation(sabotaged)
                self.assertEqual(sabotaged.calls, 1)
                handoff = handoff_on_crossing(sabotaged, 278, self.anchor)
                self.assertEqual(handoff.kind, KIND_UNAVAILABLE)
                self.assertEqual(handoff.pc, b"")
                self.assertFalse(handoff.sends_a_frame)

    def test_a_header_that_promises_bodies_it_does_not_carry_is_refused(self):
        """The count check's own case, which no length check can see.

        17 bytes, a valid tag, a frame that really is this pc's frame - and a
        count field that says three actors follow.  A client told three bodies
        follow and given none is the stream-tail misalignment answered with
        ErrorData=28317.
        """
        sabotaged = _SabotagedEncoder("lying_header", self.legacy)
        pc, frame = sabotaged.make_runtime_remote_actors(())
        self.assertEqual(len(pc), WIRE_HEADER_BYTES)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(wire_count_of(pc), 3)
        with self.assertRaisesRegex(ValueError, "declares 3 actors"):
            build_clear_generation(sabotaged)

    def test_the_clear_that_quietly_became_a_census_is_the_one_that_matters(self):
        """Queued as a clear it would not despawn the town - it would replace
        the town with three dock NPCs standing in the scene just walked into.
        """
        sabotaged = _SabotagedEncoder("counts_actors", self.legacy)
        raw_pc, _ = sabotaged.make_runtime_remote_actors(())
        self.assertGreater(wire_count_of(raw_pc), 0)
        handoff = handoff_on_crossing(sabotaged, 278, self.anchor)
        self.assertEqual(handoff.kind, KIND_UNAVAILABLE)

    def test_nothing_on_the_crossing_path_reads_the_disk(self):
        """Remove every read this process has, then cross both ways.

        A disk read inside a frame handler is a stall on a serial server.  This
        is a weak test on purpose - it is true today because the placements
        come off the legacy module's attributes and ``population_source`` is an
        integer compare - and it is here so that a future version that reaches
        for a file cannot do it quietly.
        """
        import builtins
        import io

        originals = (Path.read_text, Path.read_bytes, Path.open,
                     builtins.open, io.open)
        reads = []

        def refuse(target, *args, **kwargs):
            reads.append(str(target))
            raise AssertionError(f"the crossing path read {target}")

        Path.read_text = refuse
        Path.read_bytes = refuse
        Path.open = refuse
        builtins.open = refuse
        io.open = refuse
        try:
            out = handoff_for_arrival(self.legacy, 278, self.anchor)
            home = handoff_for_arrival(self.legacy, 1, self.anchor)
        finally:
            (Path.read_text, Path.read_bytes, Path.open,
             builtins.open, io.open) = originals
        self.assertEqual(reads, [])
        self.assertEqual(out.kind, KIND_CLEAR)
        self.assertEqual(home.kind, KIND_CENSUS)

    # ---- the console line ------------------------------------------------

    def test_the_line_reports_the_bytes_and_not_the_intent(self):
        """A handoff whose kind and whose header disagree must print both.

        Nothing in the module can construct this; it is assembled by hand
        precisely because the check exists for the day something else can.
        """
        real = handoff_for_arrival(self.legacy, 1, self.anchor)
        lying = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0,
            pc=real.pc, frame=real.frame, reapply_ms=None,
            dispatch_slot=SLOT_BEFORE_TELEPORT, generation=None,
        )
        line = handoff_console_line(lying)
        self.assertIn("kind=clear", line)
        self.assertIn("actors=0", line)
        # Was CENSUS_COUNT: the real generation whose bytes this lying
        # handoff borrows now declares 108 actors in its header, and the point
        # of the line is that it reports the HEADER, not the claim.
        self.assertIn("wire=%d" % SHIPPED_CENSUS_COUNT, line)

    def test_an_unreadable_header_says_so_rather_than_guessing_a_count(self):
        broken = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0,
            pc=b"\x00" * WIRE_HEADER_BYTES, frame=b"\x00" * 8,
            reapply_ms=None, dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
        self.assertEqual(handoff_report(broken)["wire_actor_count"], "UNREADABLE")
        self.assertIn("wire=UNREADABLE", handoff_console_line(broken))

    def test_every_string_this_module_can_print_is_ascii(self):
        """The bridge console is cp874; a non-ASCII byte there is a crash.

        Covers the labels too - the first version of this test only exercised
        lines, so a non-ASCII label survived a mutation run untouched.
        """
        strings = [
            LABEL_UNAVAILABLE,
            LABEL_CENSUS.format(1),
            LABEL_CLEAR.format(278),
            handoff_console_line(handoff_for_arrival(self.legacy, 1, self.anchor)),
            handoff_console_line(handoff_for_arrival(self.legacy, 278, self.anchor)),
            handoff_console_line(handoff_on_crossing(None, 278, self.anchor)),
            handoff_console_line(handoff_on_crossing(self.legacy, "x", self.anchor)),
        ]
        for text in strings:
            with self.subTest(text=text[:40]):
                text.encode("ascii")
                text.encode("cp874")
                self.assertNotIn("\n", text)
                self.assertNotIn("\r", text)

    def test_the_report_carries_the_census_own_count_not_a_second_one(self):
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor)
        report = handoff_report(handoff)
        self.assertTrue(report["census"]["counts_agree"])
        self.assertTrue(report["census"]["bodies_intact"])
        # Was CENSUS_COUNT on both lines; 108 assembles since RE-128, and the
        # two numbers still have to agree with each other, which is what this
        # test is really about.
        self.assertEqual(
            report["census"]["assembled_count"], SHIPPED_CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], SHIPPED_CENSUS_COUNT)
        clear = handoff_report(handoff_for_arrival(self.legacy, 278, self.anchor))
        self.assertIsNone(clear["census"])

    def test_a_handoff_with_no_bytes_is_not_queueable_whatever_its_kind_says(self):
        """``sends_a_frame`` reads the bytes, so a mislabelled kind cannot send.

        The hand-built case is the mutation that survived the first version of
        this file: ``sends_a_frame`` returning on ``kind`` alone.
        """
        refused = handoff_on_crossing(None, 278, self.anchor)
        self.assertFalse(refused.sends_a_frame)
        empty_but_labelled = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0, pc=b"", frame=b"",
            reapply_ms=None, dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=None,
        )
        self.assertFalse(empty_but_labelled.sends_a_frame)
        for scene in (1,) + NON_HOME_SCENES:
            with self.subTest(scene=scene):
                self.assertTrue(
                    handoff_for_arrival(self.legacy, scene, self.anchor).sends_a_frame
                )


class MembershipResetTests(unittest.TestCase):
    """DANGER 4 OF THE ROUND THAT BUILT THIS MODULE, CLOSED.

    ``membership`` alone is half of a pair.  A caller who set
    ``population_indices`` from it and forgot ``population_refresh_anchor``
    left the frozen state describing two different scenes at once, and no test
    in this file could see it happen.  ``membership_reset`` is the whole pair.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.anchor = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    def test_the_census_reset_carries_the_anchor_it_was_actually_built_at(self):
        handoff = handoff_for_arrival(self.legacy, 1, self.anchor)
        self.assertEqual(handoff.kind, KIND_CENSUS)
        reset = handoff.membership_reset
        self.assertEqual(reset.population_indices, handoff.membership)
        # Was CENSUS_COUNT; the reset carries the membership that was built.
        self.assertEqual(
            len(reset.population_indices), SHIPPED_CENSUS_COUNT)
        self.assertEqual(reset.population_refresh_anchor, self.anchor)
        self.assertFalse(reset.clears_everything)
        # The anchor is the generation's own, not one the caller passed twice.
        self.assertEqual(
            reset.population_refresh_anchor, handoff.generation.anchor)

    def test_every_other_crossing_clears_both_fields(self):
        for scene in NON_HOME_SCENES:
            with self.subTest(scene=scene):
                reset = handoff_for_arrival(
                    self.legacy, scene, self.anchor).membership_reset
                self.assertIsNone(reset.population_indices)
                self.assertIsNone(reset.population_refresh_anchor)
                self.assertTrue(reset.clears_everything)

    def test_an_unavailable_handoff_clears_both_fields_too(self):
        """No frame goes out, so the client keeps the old scene's actors -
        and the frozen state's last_target_pos is already in the new one.
        That is the state where one ChooseNPC recomposes the old town into
        the new map, so the membership goes even though nothing was sent.
        """
        refused = handoff_on_crossing(None, 278, self.anchor)
        self.assertEqual(refused.kind, KIND_UNAVAILABLE)
        self.assertTrue(refused.membership_reset.clears_everything)

    def test_a_hand_built_clear_never_leaks_a_membership(self):
        """THE MUTANT: a reset that branches on ``generation`` alone.

        A SceneHandoff carrying KIND_CLEAR and a census generation is not a
        shape this module builds, but it is one line away, and a reset that
        read the generation without checking the kind would hand back the
        town's membership on the frame that removes the town.
        """
        census = handoff_for_arrival(self.legacy, 1, self.anchor)
        mutant = SceneHandoff(
            scene_id=278, kind=KIND_CLEAR, reason="hand_built_for_this_test",
            label=LABEL_CLEAR.format(278), actor_count=0,
            pc=census.pc, frame=census.frame, reapply_ms=None,
            dispatch_slot=SLOT_BEFORE_TELEPORT,
            generation=census.generation,
        )
        self.assertTrue(mutant.membership_reset.clears_everything)

    def test_the_report_carries_both_halves(self):
        report = handoff_report(handoff_for_arrival(self.legacy, 1, self.anchor))
        self.assertEqual(
            report["membership_reset_indices"], report["membership"])
        self.assertEqual(report["membership_reset_anchor"], self.anchor)
        cleared = handoff_report(
            handoff_for_arrival(self.legacy, 278, self.anchor))
        self.assertIsNone(cleared["membership_reset_indices"])
        self.assertIsNone(cleared["membership_reset_anchor"])

    def test_the_reset_is_frozen(self):
        reset = MembershipReset(None, None)
        with self.assertRaises(Exception):
            reset.population_indices = (1,)


class ArrivalStowawayTests(unittest.TestCase):
    """Who the client is still holding when a crossing lands (round 2pdf6j).

    The numbers here are the round's finding, so they are asserted as
    numbers rather than as "some": a later round that changes the frozen
    table, the sea scene's decreed spawn, or the report band has to come
    back through this file and say so.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        # THE MEMBERSHIP THE CLIENT IS ACTUALLY SENT, not the frozen table.
        # The first draft of this class used the table (115 rows) and pinned
        # ``held=115`` - a number no live dispatch can ever print, because
        # ``build_world_population`` ships 108 of those rows (pf-adversary,
        # round 2pdf6j, D2/D3).  Built here the same way the login path
        # builds it, so the pin below moves the day the census does.
        cls.membership = tuple(
            build_world_population(
                cls.legacy, (0.0, 0.0, 0.0), scene_id=1,
            ).indices
        )
        cls.table = tuple(
            placement.placement_index
            for placement in load_port_royal_placements(cls.legacy)
        )
        # The sea scene's arrival point, and it is READ FROM THE REGISTRY
        # rather than typed as (0, 0, 0): a test that hardcodes the decreed
        # value keeps passing on the day the decree is retired, which is
        # exactly the day this measurement changes.
        registry = load_scene_registry()
        cls.sea_anchor = spawn_position(destination(17, registry))

    def test_the_sea_arrival_point_is_the_one_the_registry_pins(self):
        self.assertEqual(self.sea_anchor, (0.0, 0.0, 0.0))

    def test_four_town_actors_stand_within_the_report_band_of_the_sea(self):
        view = stowaways_near(self.legacy, self.membership, self.sea_anchor)
        self.assertTrue(view.computed)
        self.assertEqual(view.held, SHIPPED_CENSUS_COUNT)
        self.assertEqual(len(self.table), 115)
        self.assertEqual(len(view.within_radius), 4)
        self.assertEqual(
            [member.source_name for member in view.within_radius],
            ["Legend Jack", "Plato", "Qina", "Betula"],
        )
        self.assertAlmostEqual(view.nearest.distance, 1226.6, places=1)
        # The half the console line does not print and a reader would
        # otherwise assume: they are not on the deck, they are ~930 units
        # above the point the player lands on.
        # ...at the DECREED anchor, and only there.  z=0 is the owner's
        # placeholder and the registry records it as outside this scene's
        # own ground band, so this separation is a fact about the decree,
        # not about the sea.  The band test below is the other half.
        for member in view.within_radius:
            self.assertGreater(member.z, 900.0)

    def test_the_headline_number_belongs_to_the_decreed_anchor_not_the_scene(self):
        """Land inside the scene's own ground band and the answer is 5.

        pf-adversary (round 2pdf6j, D1) drove this: the count 4 and the
        ~930-unit separation are properties of ``z=0``, which
        ``world_scene_registry_001.json`` itself records as OUTSIDE the
        ground band ([746.04, 1272.74]) measured from Bg1001's placements.
        Pinned as a number so a later round that retires the decree finds
        the day this measurement changes, instead of reading a refuted 4.
        """
        for z in (746.04, 1009.39, 1272.74):
            view = stowaways_near(self.legacy, self.membership, (0.0, 0.0, z))
            self.assertEqual(len(view.within_radius), 5, z)
            self.assertIn(
                "Kaim", [member.source_name for member in view.within_radius])
            # and the crowd is no longer overhead.  Measured: at a real
            # ground z the largest vertical separation is 341, against ~930
            # for every one of them at the decreed z=0.
            for member in view.within_radius:
                self.assertLess(abs(member.z - z), 400.0)
        decreed = stowaways_near(self.legacy, self.membership, self.sea_anchor)
        self.assertTrue(
            all(member.z > 900.0 for member in decreed.within_radius))

    def test_the_census_and_the_table_disagree_at_five_thousand(self):
        """115 rows exist; 108 are sent.  The gap has a name and a distance.

        pf-adversary (round 2pdf6j, D2): reporting the table's 11 as
        "actors around the player" reads the data-table layer as the wire
        layer.  ``world_density``'s console line does exactly that today.
        """
        census = stowaways_near(
            self.legacy, self.membership, self.sea_anchor, radius=5000.0)
        table = stowaways_near(
            self.legacy, self.table, self.sea_anchor, radius=5000.0)
        self.assertEqual(len(census.within_radius), 10)
        self.assertEqual(len(table.within_radius), 11)
        extra = set(m.source_name for m in table.within_radius) - set(
            m.source_name for m in census.within_radius)
        self.assertEqual(extra, {"Filet"})

    def test_the_band_is_the_one_world_density_already_reports_in(self):
        """The docstring says "not chosen here" - this is what makes it true."""
        self.assertEqual(STOWAWAY_REPORT_RADIUS, world_density.M1_VIEW_RADIUS)
        self.assertEqual(STOWAWAY_REPORT_RADIUS, 2000.0)

    def test_the_band_is_a_report_setting_and_widening_it_finds_more(self):
        wide = stowaways_near(
            self.legacy, self.membership, self.sea_anchor, radius=5000.0)
        self.assertEqual(len(wide.within_radius), 10)
        none_at_all = stowaways_near(
            self.legacy, self.membership, self.sea_anchor, radius=0.0)
        self.assertEqual(len(none_at_all.within_radius), 0)
        # ...and the held count does not move with the band, which is the
        # distinction the console line's two fields exist to keep apart.
        self.assertEqual(none_at_all.held, wide.held)

    def test_moving_the_arrival_point_moves_the_answer(self):
        """The negative control this lane was caught without in round drrnpu.

        Without it, a function that ignored its anchor entirely would pass
        every assertion above.
        """
        view = stowaways_near(
            self.legacy, self.membership, (-507.0, -616.4, 931.4))
        self.assertEqual(view.nearest.source_name, "Legend Jack")
        self.assertLess(view.nearest.distance, 1.0)
        sea = stowaways_near(self.legacy, self.membership, self.sea_anchor)
        self.assertNotEqual(
            [member.source_name for member in view.within_radius],
            [member.source_name for member in sea.within_radius],
        )
        # AND THE NUMBER GOES DOWN, WHICH IS WORTH PINNING BECAUSE IT IS
        # COUNTER-INTUITIVE: standing ON a census member puts THREE inside
        # the band, one fewer than the empty sea point does.  The table is
        # thin everywhere (``world_density``: the densest placement in it
        # has 8 neighbours within 1000u), so "nearer the town" does not mean
        # "more actors around you".
        self.assertEqual(len(view.within_radius), 3)

    def test_the_frame_path_variant_carries_the_radius_it_was_given(self):
        """The passthrough, pinned: a mutant that drops it survived before."""
        narrow = stowaways_on_crossing(
            self.legacy, self.membership, self.sea_anchor, radius=1500.0)
        self.assertTrue(narrow.computed)
        self.assertEqual(narrow.radius, 1500.0)
        self.assertEqual(len(narrow.within_radius), 1)

    def test_a_radius_that_is_not_a_finite_distance_is_refused(self):
        for bad in (-1.0, float("nan"), float("inf"), "2000", None, 10 ** 400):
            with self.assertRaises(ValueError, msg=repr(bad)):
                stowaways_near(
                    self.legacy, self.membership, self.sea_anchor, radius=bad)
            # and the frame-path variant answers the same input with a
            # refusal instead of an exception - including 10**400, which
            # used to overflow inside the handler itself.
            view = stowaways_on_crossing(
                self.legacy, self.membership, self.sea_anchor, radius=bad)
            self.assertFalse(view.computed, repr(bad))
            self.assertEqual(view.radius, 0.0)

    def test_a_membership_that_repeats_an_index_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            stowaways_near(self.legacy, (5, 5, 5), self.sea_anchor)
        self.assertIn("repeats a placement index", str(caught.exception))

    def test_an_unknown_membership_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            stowaways_near(self.legacy, None, self.sea_anchor)
        self.assertIn("no recorded census membership", str(caught.exception))

    def test_a_membership_the_frozen_table_does_not_carry_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            stowaways_near(self.legacy, (2,), self.sea_anchor)
        self.assertIn("frozen table does not carry", str(caught.exception))

    def test_the_frame_path_variant_never_raises_and_names_the_reason(self):
        for bad in (None, (2,), "115", (1.5,)):
            view = stowaways_on_crossing(self.legacy, bad, self.sea_anchor)
            self.assertFalse(view.computed)
            self.assertEqual(view.within_radius, ())
            self.assertIsNone(view.nearest)
            self.assertTrue(view.reason.startswith("stowaways_not_measured:"))
        broken = stowaways_on_crossing(self.legacy, self.membership, "here")
        self.assertFalse(broken.computed)
        self.assertEqual(broken.anchor, (0.0, 0.0, 0.0))

    def test_the_console_line_is_printable_on_the_bridge_console(self):
        for view in (
            stowaways_near(self.legacy, self.membership, self.sea_anchor),
            stowaways_on_crossing(self.legacy, None, self.sea_anchor),
        ):
            line = stowaway_console_line(view)
            line.encode("ascii")
            line.encode("cp874")
        measured = stowaway_console_line(
            stowaways_near(self.legacy, self.membership, self.sea_anchor))
        self.assertIn(f"held={SHIPPED_CENSUS_COUNT}", measured)
        self.assertIn("within=4", measured)
        # the band belongs in the line: without it "within=4" is a number
        # with no unit, and a mutant that dropped the field survived.
        self.assertIn("radius=2000.0", measured)
        self.assertIn("Legend_Jack@1226.6", measured)
        self.assertNotIn("Legend Jack", measured)

    def test_the_console_line_refuses_anything_that_is_not_a_view(self):
        for junk in (None, "a line", 4, object()):
            self.assertIn("unreportable", stowaway_console_line(junk))

    def test_the_view_is_frozen(self):
        view = stowaways_near(self.legacy, self.membership, self.sea_anchor)
        with self.assertRaises(Exception):
            view.held = 0


if __name__ == "__main__":
    unittest.main()
