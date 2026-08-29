"""CORE-REQUEST-021 (LANE-A M1-P item 2) -- Bg0002 (Prison Exile Island)
login teleport and census, on the REAL dispatcher.

``world_scene_entry.resolve_entry()`` (BUILD-002) already derives every login
frame from one resolved position for ANY pinned scene_id, so a character row
that names scene 2 already lands on the pinned spawn with no runtime.py
change at all -- this file's first two tests are the confirmation of that,
not a new wiring point.

The part that genuinely was not wired is the census: the runtime.py
WORLD-CENSUS-001 block only knew scene 1 (bg0001) and skipped every other
scene, including 2, with ``world_census_skipped_scene_2_not_home``. This
file proves the new scene_id == 2 branch added alongside it: same trigger
(first TargetPos after the runtime ack), same console-before-frame order,
same initial-plus-reapply schedule, over
``world_population_bg0002.build_bg0002_population`` instead of
``world_population.build_world_population``.

NO SEED PATH EXISTS ON A REAL BOOT for a character whose stored row names
scene 2 (grep for P0_P30_P91/scene2 seeding in src/ comes up empty; this is
recorded, not invented, in the handback). This file synthesizes that row the
only way a test can: writing directly to the character_positions row this
tree's own ``store.save_position`` already exposes, for a character created
in a throwaway per-test SQLite database -- never the canonical DB, never any
committed fixture.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_census_hostility  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _apply_mob_death_census_override,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENE2_N_ID = world_population_bg0002.SCENE2_N_ID
PIN_ANCHOR = (10.0, 20.0, 30.0)

INITIAL_PREFIX = "WORLD_CENSUS_BG0002_INITIAL_"
REAPPLY_PREFIX = "WORLD_CENSUS_BG0002_REAPPLY_"

# Same bytes proven elsewhere (tests/test_second_password_bypass.py) to
# parse as an outer RuntimeProtocolReq frame with vital_count == 0 -- an
# ordinary empty runtime poll, carrying no TargetPosVital at all.
EMPTY_RUNTIME_PC = bytes.fromhex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 00"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class Bg0002CensusWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    # ----- harness -----------------------------------------------------

    def _target_pos_pc(self, xyz, heading=0.0, moving=0, derived=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(
                self.legacy.f32tag(value) for value in (*xyz, heading)
            )
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _step(self, state, xyz=PIN_ANCHOR, **kwargs):
        return state.dispatch(
            self.legacy.parse_outer(self._target_pos_pc(xyz, **kwargs))
        )

    def _login_and_create(self, token):
        """Login and character-create only -- stops BEFORE start_game so a
        caller can rewrite the fresh character's stored row first."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        return state, character

    def _start_game(self, state, character):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return actions, buf.getvalue()

    def _state_at_scene2(self, token):
        """A real, stored character row whose scene_id is 2 -- written the
        only way a test can synthesize what nothing in this tree seeds on a
        real boot: a direct ``store.save_position`` write to a throwaway
        per-test SQLite database, never the canonical DB.
        """
        state, character = self._login_and_create(token)
        destination = world_scene_travel.destination(SCENE2_N_ID)
        spawn = world_scene_travel.spawn_position(destination)
        # save_position requires an open session that already SELECTED this
        # character (store.py's own stale-session detection, CORE-REQUEST-018
        # / GT-106 (4).3) -- select it directly first. select_and_start()
        # (inside the start_game dispatch right after this) re-selects the
        # same character under the same session, which is a harmless no-op.
        self.store.select_character(state.foundation.session_id, character.selector)
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(SCENE2_N_ID, 0, spawn[0], spawn[1], spawn[2], 0.0),
        )
        actions, out = self._start_game(state, character)
        return state, actions, out

    def _census(self, actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]

    def _expected_spliced(self, state, anchor):
        """The census bytes the wired branch now queues: the raw bg0002
        build with LANE-B's hostile-faction override spliced in
        (CORE-REQUEST 20260829_1600), composed through the same public
        functions the call site uses.  Deliberately NO ledger argument,
        same as the call site and for the measured reason in the letter:
        at login the boot ledger still holds bg0001's roster and
        ``full_roster_override`` raises on the mismatched pair.

        Still mutation-proof for the wiring: revert the override
        application in runtime.py's bg0002 branch and every byte
        comparison built from this helper fails, because the splice
        changes entry sizes (0x2033: 183 -> 196 bytes, measured by the
        lane's own headless run).
        """
        independent = world_population_bg0002.build_bg0002_population(
            self.legacy, anchor, scene_id=SCENE2_N_ID,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        override = mob_census_hostility.hostile_override_for_scene_id(
            self.legacy, SCENE2_N_ID, state.mob_death_register,
        )
        return _apply_mob_death_census_override(
            self.legacy, independent, override,
        )

    # ----- point 1: the login teleport needs no runtime.py change ------

    def test_a_scene2_stored_row_teleports_to_the_pinned_spawn(self):
        """Confirms, not builds: ``world_scene_entry.resolve_entry()`` +
        the existing ``entry.teleport_fields`` call site already send this
        with zero runtime.py code change for point 1.
        """
        state, actions, _out = self._state_at_scene2("bg0002_teleport")
        teleport = [
            action for action in actions
            if action[0] == "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE"
        ]
        self.assertEqual(len(teleport), 1, actions)
        destination = world_scene_travel.destination(SCENE2_N_ID)
        expected_fields = world_scene_travel.login_teleport_fields(destination)
        self.assertEqual(expected_fields[0], SCENE2_N_ID)
        expected_pc, expected_frame = self.legacy.make_login_teleport(
            *expected_fields
        )
        self.assertEqual(teleport[0][1], expected_pc)
        self.assertEqual(teleport[0][2], expected_frame)

    def test_the_world_scene_console_line_names_scene2_at_login(self):
        state, _actions, out = self._state_at_scene2("bg0002_scene_line")
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn(f"scene_id={SCENE2_N_ID}", lines[0])
        self.assertIn("model=BG0002", lines[0])

    # ----- point 2: the census branch this CORE-REQUEST actually wires -

    def test_the_scene2_boot_queues_the_whole_bg0002_census_twice(self):
        state, _login_actions, _out = self._state_at_scene2("bg0002_census")
        actions = self._step(state)
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [f"{INITIAL_PREFIX}97", f"{REAPPLY_PREFIX}97"],
        )
        self.assertEqual([action[3] for action in census], [0.0, 3.0])
        expected = self._expected_spliced(state, PIN_ANCHOR)
        for action in census:
            self.assertEqual(action[1], expected.pc)
            self.assertEqual(action[2], expected.frame)
        self.assertEqual(
            census[1][3],
            world_population_bg0002.INITIAL_REAPPLY_MS / 1000.0,
        )
        self.assertIs(state.world_census_sent, True)
        self.assertIs(state.world_census_refused, False)
        self.assertIn(
            "world_census_bg0002_committed_actors_97_pc_"
            f"{expected.pc_bytes}_frame_{expected.frame_bytes}",
            state.events,
        )
        # Deliberately not touched by this branch -- see runtime.py's own
        # comment at the call site for why.
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.world_census_indices)

    def test_the_console_prints_world_scene_and_world_census_before_the_frame(
        self,
    ):
        state, _login_actions, _login_out = self._state_at_scene2(
            "bg0002_console"
        )
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self._step(state)
        lines = captured.getvalue().splitlines()
        scene_lines = [l for l in lines if l.startswith("WORLD_SCENE ")]
        census_lines = [l for l in lines if l.startswith("WORLD_CENSUS ")]
        self.assertEqual(len(scene_lines), 1, lines)
        self.assertIn(f"scene_id={SCENE2_N_ID}", scene_lines[0])
        self.assertEqual(len(census_lines), 1, lines)
        self.assertIn("assembled=97/97", census_lines[0])
        # Order: WORLD_SCENE, then WORLD_CENSUS, then actor lines.
        self.assertLess(
            lines.index(scene_lines[0]), lines.index(census_lines[0]),
        )
        self.assertGreater(len(lines), 2 + 2, "no actor lines printed")

    def test_the_census_is_one_shot_per_scene2_session(self):
        state, _login_actions, _out = self._state_at_scene2("bg0002_once")
        self.assertEqual(len(self._census(self._step(state))), 2)
        self.assertEqual(self._census(self._step(state)), [])

    def test_a_scene2_compose_refusal_sends_no_frame_and_latches(self):
        original = world_population_bg0002.build_bg0002_population

        def explode(*args, **kwargs):
            raise ValueError("synthetic bg0002 refusal")

        state, _login_actions, _out = self._state_at_scene2("bg0002_refused")
        world_population_bg0002.build_bg0002_population = explode
        try:
            actions = self._step(state)
        finally:
            world_population_bg0002.build_bg0002_population = original
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_refused, True)
        self.assertIn(
            "world_census_bg0002_compose_refused_ValueError", state.events,
        )
        # Latched: a later step neither retries nor emits a second refusal.
        self.assertEqual(self._census(self._step(state)), [])
        self.assertEqual(
            state.events.count(
                "world_census_bg0002_compose_refused_ValueError"
            ),
            1,
        )

    def test_the_scene_line_does_not_re_read_the_registry_from_disk(self):
        """pf-adversary, round f9pzed: the WORLD_SCENE console line called
        ``world_scene_travel.destination(scene_id)`` with no registry, which
        re-reads and re-validates the pin file from disk on every login --
        the exact anti-pattern this same file already fixed once nearby (see
        the comment at the login resolve_entry() call site). A registry that
        goes unreadable/malformed AFTER boot (a rotation, a permissions
        change) would then raise OUTSIDE the branch's own try/except and
        unwind out of dispatch() uncaught -- v141's own listener loop has no
        except at that level, only a finally, so the connection dies with no
        reply and no clean close. Fixed by passing the SAME boot-preloaded
        registry the login path already uses. This test breaks the disk read
        specifically and confirms the boot proceeds anyway.
        """
        state, _login_actions, _out = self._state_at_scene2(
            "bg0002_registry_reuse"
        )
        original = world_scene_travel.load_scene_registry

        def explode(*args, **kwargs):
            raise ValueError("synthetic: registry file corrupted after boot")

        world_scene_travel.load_scene_registry = explode
        try:
            actions = self._step(state)
        finally:
            world_scene_travel.load_scene_registry = original
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [f"{INITIAL_PREFIX}97", f"{REAPPLY_PREFIX}97"],
        )
        self.assertIs(state.world_census_sent, True)

    # ----- scene 1 is provably unchanged --------------------------------

    def test_scene1_still_sends_the_bg0001_census_unchanged(self):
        """The control: an ordinary scene-1 boot through the SAME dispatcher
        path this file drives for scene 2 still queues the bg0001 census
        under its own bg0001 labels, at its own count -- the new branch is
        additive, not a replacement of the existing one.
        """
        state, character = self._login_and_create("bg0001_control")
        actions, _out = self._start_game(state, character)
        self.assertEqual(state.foundation.selected.position.scene_id, 1)
        census = self._census(self._step(state))
        # Was _115.  SUPERSEDED 2026-08-28 (LANE-A, RE-128 / CLINE
        # identities): the bg0001 census assembles 108 of its 115 frozen
        # placements, because seven of them have a Mob-Set number whose CLINE
        # leader has no CONSTDATA MOBS row and therefore no shippable
        # identity.  The label carries what assembled, so the control moved
        # with it; what this test proves - scene 1 still takes the bg0001
        # branch, under bg0001 labels, at its own count - is unchanged.
        self.assertEqual(
            [action[0] for action in census],
            ["WORLD_CENSUS_INITIAL_108", "WORLD_CENSUS_REAPPLY_108"],
        )
        independent = world_population.build_world_population(
            self.legacy, PIN_ANCHOR, scene_id=1,
        )
        # mob_death.full_roster_override splices hostile bodies into the
        # bg0001 census (unrelated to this CORE-REQUEST); only membership,
        # count and ordering are checked here, not the exact bytes, which
        # tests/test_world_census_wiring.py already pins byte-for-byte.
        self.assertEqual(len(census[0][1]) > 0, True)
        self.assertEqual(
            state.world_census_actor_count, independent.actor_count,
        )
        self.assertIsNotNone(state.population_indices)

    # ----- CORE-REQUEST-026: arrival trigger, bg0002 only ----------------

    def test_the_scene2_census_arrives_with_no_target_pos_vital_ever_sent(self):
        """The gap CORE-REQUEST-026 closes: M1-P found the scene empty until
        the player pressed a movement key, because the frozen guard this
        branch inherited waits for ``last_target_pos``, which only a
        TargetPosVital sets.  This drives an EMPTY runtime poll -- the same
        constant proven elsewhere in this suite to carry
        ``vital_count == 0`` -- straight after login/start_game, with no
        TargetPosVital dispatched at any point, and expects the census
        anyway, anchored on the scene's own pinned spawn.
        """
        state, _login_actions, _out = self._state_at_scene2(
            "bg0002_arrival_no_wasd"
        )
        actions = state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [f"{INITIAL_PREFIX}97", f"{REAPPLY_PREFIX}97"],
        )
        self.assertIs(state.world_census_sent, True)
        self.assertIsNone(state.last_target_pos)
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(SCENE2_N_ID)
        )
        expected = self._expected_spliced(state, spawn)
        for action in census:
            self.assertEqual(action[1], expected.pc)
            self.assertEqual(action[2], expected.frame)

    def test_a_late_target_pos_vital_still_wins_as_the_anchor(self):
        """If the player DOES move before the next poll, the real position
        is used -- the arrival fallback only fires when nothing better has
        arrived yet, it does not override a real TargetPosVital.
        """
        state, _login_actions, _out = self._state_at_scene2(
            "bg0002_real_target_pos_wins"
        )
        census = self._census(self._step(state))
        expected = self._expected_spliced(state, PIN_ANCHOR)
        for action in census:
            self.assertEqual(action[1], expected.pc)
            self.assertEqual(action[2], expected.frame)

    def test_an_unpinned_arrival_anchor_latches_a_refusal_not_a_retry_loop(
        self,
    ):
        """pf-adversary, round confident-ride-sf9kel: the registry lookup
        used for the fallback anchor raises (a corrupted/unpinned bg0002
        spawn row, same failure mode the existing registry-reuse test
        drills for the WORLD_SCENE line).  Unlike a genuinely transient
        read, ``scene_entry_registry`` is loaded once at boot and never
        reloaded, so this failure is deterministic for the rest of the
        process's life -- it must latch (one event, no frame, no retry)
        exactly like the sibling population-build refusal a few lines
        below it, not silently re-raise and re-log on every later poll.
        """
        state, _login_actions, _out = self._state_at_scene2(
            "bg0002_arrival_anchor_failure"
        )
        original = world_scene_travel.spawn_position

        def explode(*args, **kwargs):
            raise ValueError("synthetic: spawn position unreadable")

        world_scene_travel.spawn_position = explode
        try:
            actions = state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        finally:
            world_scene_travel.spawn_position = original
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, False)
        self.assertIs(state.world_census_refused, True)
        self.assertIn(
            "world_census_bg0002_arrival_anchor_refused_ValueError",
            state.events,
        )
        # A later poll, even with the real function restored, must NOT
        # retry -- the refusal latched, same as the compose-refusal test
        # above.
        actions = state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, False)
        self.assertEqual(
            state.events.count(
                "world_census_bg0002_arrival_anchor_refused_ValueError"
            ),
            1,
        )

    def test_scene1_still_waits_for_a_target_pos_vital_unlike_scene2(self):
        """Control for the disjunct itself: an ordinary scene-1 boot must
        NOT gain the arrival trigger -- an empty poll with no TargetPosVital
        must send nothing, exactly as before this CORE-REQUEST.
        """
        state, character = self._login_and_create("bg0001_arrival_control")
        self._start_game(state, character)
        self.assertEqual(state.foundation.selected.position.scene_id, 1)
        actions = state.dispatch(self.legacy.parse_outer(EMPTY_RUNTIME_PC))
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_sent, False)

    # ----- CORE-REQUEST (LANE-B 20260829_1600): hostile splice ---------

    def test_the_scene2_census_bytes_are_not_the_raw_faction0_build(self):
        """The queued census must DIFFER from the raw bg0002 build: the
        hostile override replaces every roster monster's entry with a
        wider spliced body (0x2033: 183 -> 196 bytes, the lane's own
        headless measurement), so byte-identity with the raw build means
        the splice never ran.  This is the direct kill for a mutation
        that deletes the override application but keeps the console line.
        """
        state, _login_actions, _out = self._state_at_scene2(
            "bg0002_hostile_bytes"
        )
        census = self._census(self._step(state))
        self.assertEqual(len(census), 2)
        raw = world_population_bg0002.build_bg0002_population(
            self.legacy, PIN_ANCHOR, scene_id=SCENE2_N_ID,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        override = mob_census_hostility.hostile_override_for_scene_id(
            self.legacy, SCENE2_N_ID, state.mob_death_register,
        )
        # The scene's roster is non-empty, so the override must be too --
        # an empty override would make this whole test vacuous.
        self.assertTrue(override)
        for identity, body in override.items():
            self.assertIn(identity, raw.actor_identities)
        self.assertNotEqual(census[0][1], raw.pc)
        spliced = _apply_mob_death_census_override(
            self.legacy, raw, override,
        )
        self.assertEqual(census[0][1], spliced.pc)
        self.assertEqual(census[0][2], spliced.frame)
        # Same actors, same order -- the splice widens entries, it never
        # adds, drops or reorders them.
        self.assertEqual(spliced.actor_identities, raw.actor_identities)

    def test_the_hostility_console_line_prints_unconditionally(self):
        """CORE-REQUEST (LANE-B 20260829_1600), point 3: the
        MOB_CENSUS_HOSTILITY line prints on the census step, OUTSIDE the
        override's if -- "no line at all" is the state GT-084 already
        misread once.  Pinned to the full text so a regression to
        "backed=0" or a silent scene mismatch fails by word, not just by
        presence.
        """
        state, _login_actions, _login_out = self._state_at_scene2(
            "bg0002_hostility_line"
        )
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self._step(state)
        lines = [
            l for l in captured.getvalue().splitlines()
            if l.startswith("MOB_CENSUS_HOSTILITY ")
        ]
        self.assertEqual(len(lines), 1, captured.getvalue())
        report = mob_census_hostility.census_backing_report(
            SCENE2_N_ID, ())
        roster_count = report["roster_count"]
        self.assertEqual(
            lines[0],
            "MOB_CENSUS_HOSTILITY scene_id=%d scene=Bg0002 roster=%d "
            "backed=%d unbacked=none" % (
                SCENE2_N_ID, roster_count, roster_count,
            ),
        )

    def test_the_hostility_line_still_prints_when_the_override_is_empty(
        self,
    ):
        """The half the test above cannot see (pf-adversary, round roj9lp,
        D1): with scene 2's real roster the override is never empty, so
        "prints unconditionally" and "prints when the override is
        non-empty" are indistinguishable there -- a later editor could
        move the print inside ``if override:`` and stay green.  This
        forces the empty-override state the way the roster could reach it
        for real (an owner ruling shrinking it to nothing, the mechanism
        that already cut 17 rows to 12) by patching the composer runtime
        actually calls, and demands the line anyway: an empty answer is a
        real answer, silence is the GT-084 misread.
        """
        state, _login_actions, _login_out = self._state_at_scene2(
            "bg0002_hostility_line_empty"
        )
        original = mob_census_hostility.hostile_override_for_scene_id
        mob_census_hostility.hostile_override_for_scene_id = (
            lambda *args, **kwargs: {}
        )
        try:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                actions = self._step(state)
        finally:
            mob_census_hostility.hostile_override_for_scene_id = original
        lines = [
            l for l in captured.getvalue().splitlines()
            if l.startswith("MOB_CENSUS_HOSTILITY ")
        ]
        self.assertEqual(len(lines), 1, captured.getvalue())
        # And the census itself shipped the RAW build -- an empty
        # override overrides nothing, it never falls back to anything
        # else (the one misreading hostile_override_for_scene_id's own
        # docstring forbids).
        census = self._census(actions)
        self.assertEqual(len(census), 2)
        raw = world_population_bg0002.build_bg0002_population(
            self.legacy, PIN_ANCHOR, scene_id=SCENE2_N_ID,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(census[0][1], raw.pc)


if __name__ == "__main__":
    unittest.main()
