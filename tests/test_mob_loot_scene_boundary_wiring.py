"""CORE-REQUEST (LANE-B v2, pf_bridge notes_to_chief 20260902_1052): the drop
cell learns about a scene crossing, and the generation it composes there is
HELD until the arrival census has committed -- then released BEFORE any kill's
generation in the same dispatch, and only into the scene it was composed for.

Drives ``runtime.make_state_class`` headless -- no server process, no socket,
no client.  The warp seam is the same one
``tests/test_gm_warp_chain_census_shipped.py`` uses (park a ``WarpTarget``,
then let dispatch's own ``_gm_warp_note_position_pending`` ->
``_gm_warp_resync_selected_scene`` run), rebuilt here rather than imported so
this file has no test-to-test coupling.

THE ORDER PIN IS THE POINT OF THIS FILE (pf-adversary D1, round g7yvo2).  The
first version of this wiring appended the held frames LAST in the dispatch,
which is the one order ``mob_loot.MOB_LOOT_WIRING`` step 6 forbids by name: a
kill's generation carries the whole scene, so a boundary generation behind it
rolls the client's ground back to before the player's newest kill.
``test_the_flush_rides_after_the_census_and_before_the_kill`` is the assertion
that would have caught it, and it fails if the flush moves back to the end of
the sum.

MUTATION-PROOF ON PURPOSE.  Delete the ``_mob_loot_cross_scene_boundary`` call
from ``_gm_warp_resync_selected_scene`` and
``test_a_cross_scene_warp_tells_the_drop_cell_it_crossed`` fails on a missing
event.  Delete the census gate and
``test_the_boundary_generation_is_held_until_the_census_commits`` fails on a
frame that arrives a poll early.  Delete the scene tag and
``test_frames_are_never_released_into_another_scene`` fails on bytes published
into a scene they were not composed for.  Delete the ``except`` and
``test_a_composer_refusal_is_an_event_not_an_exception`` fails with the
exception it asserts cannot escape.

WHAT NONE OF THIS PROVES: that a client draws a ground generation delivered at
a scene boundary.  Nobody has watched one.  ``mob_loot.enter_scene_frames``
labels it an assumption of LANE B and NONCLAIM 12 is open.  Wire/DB only.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_drop_presence              # noqa: E402
from pirateforce_foundation import mob_loot                       # noqa: E402
from pirateforce_foundation import mob_pickup_request             # noqa: E402
from pirateforce_foundation import world_scene_folder             # noqa: E402
from pirateforce_foundation import world_scene_travel             # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (       # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import (             # noqa: E402
    WarpTarget,
)
from pirateforce_foundation.gm.warp_target_record import (        # noqa: E402
    current_character_id, record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (                # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle   # noqa: E402
from pirateforce_foundation.model import Position                 # noqa: E402
from pirateforce_foundation.runtime import make_state_class       # noqa: E402
from pirateforce_foundation.store import SQLiteStore              # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

DESTINATION_SCENE_ID = 2


def _legacy():
    return load_legacy(LEGACY_PATH)


class SceneBoundaryHarness(unittest.TestCase):
    """A real login, a real character, a real warp -- and no test of its own.

    ROUND g1y1yc split this out of ``SceneBoundaryWiringTests`` UNCHANGED so
    the pickup class below can drive the same dispatcher without inheriting
    (and re-running) that class's tests.  Same shape as
    ``test_mob_pickup_request.TheWiringHarness``, and for the same reason.
    """

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
        self.empty_poll_pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 0)
        )

    # ----- harness -------------------------------------------------------

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        return state

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        self.console = out.getvalue()
        return actions

    def _warp(self, state, scene_id):
        """One cross-scene GM warp through the production arming path."""
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        target = WarpTarget(scene_id, spawn[0], spawn[1], spawn[2])
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        actions = self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        return actions

    def _stand_in(self, state, scene_id):
        selected = state.foundation.selected
        state.foundation.selected = replace(
            selected, position=replace(selected.position, scene_id=scene_id),
        )

    def _hold(self, state, frames=((b"pc", b"frame"),)):
        """Put `frames` in the stash tagged with the scene the session is
        actually standing in -- the shape a real crossing leaves behind."""
        folder = world_scene_folder.scene_folder_for_scene_id(
            state.foundation.selected.position.scene_id)
        state.mob_loot_boundary_frames_pending = frames
        state.mob_loot_boundary_frames_scene = mob_loot.scene_key(folder)

    def _action_vital_shaped_pc(self):
        """A frame whose nested id is ACTION_VITAL, so the combat lane is
        consulted at all (the stub in the order test answers it)."""
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, 0x2001)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + b"".join(legacy.f32tag(0.0) for _ in range(4))
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )

    @staticmethod
    def _ground(actions):
        return [a for a in actions if a[0] == mob_drop_presence.ACTION_LABEL]


class SceneBoundaryWiringTests(SceneBoundaryHarness):

    # ----- the crossing --------------------------------------------------

    def test_a_cross_scene_warp_tells_the_drop_cell_it_crossed(self):
        state = self._state("tok-boundary-crossed")
        self._warp(state, DESTINATION_SCENE_ID)
        entered = [
            event for event in state.events
            if event.startswith("mob_loot_boundary_entered_")
        ]
        self.assertEqual(
            len(entered), 1,
            "the warp did not reach _mob_loot_cross_scene_boundary: %r"
            % ([e for e in state.events if "mob_loot_boundary" in e],),
        )
        # The scene is named by FOLDER, never by scene id -- the cell's own
        # contract (mob_loot._require_scene refuses a non-str).
        self.assertTrue(
            entered[0].startswith("mob_loot_boundary_entered_Bg0002_"),
            entered[0],
        )
        self.assertEqual(
            state.mob_loot_boundary_frames_scene, mob_loot.scene_key("Bg0002"),
        )

    def test_an_empty_scene_publishes_nothing_and_says_so(self):
        state = self._state("tok-boundary-empty")
        actions = self._warp(state, DESTINATION_SCENE_ID)
        self.assertEqual(self._ground(actions), [])
        self.assertIn(
            "mob_loot_boundary_entered_Bg0002_frames_0", state.events,
        )
        # Nothing is owed, so no later poll invents one either.
        for _ in range(3):
            self.assertEqual(self._ground(self._dispatch(
                state, self.empty_poll_pc)), [])

    def test_an_unaddressed_scene_id_is_refused_by_name_and_clears_the_stash(self):
        state = self._state("tok-boundary-unaddressed")
        self._hold(state)
        state._mob_loot_cross_scene_boundary(9999)
        unaddressed = [
            event for event in state.events
            if event.startswith("mob_loot_boundary_scene_9999_unaddressed_")
        ]
        self.assertEqual(len(unaddressed), 1, state.events[-5:])
        # The event names the cell's own scene, because the cell did NOT
        # learn it left (there is no folder to declare) -- a later return
        # composes nothing, and this line is the only trail that says why.
        self.assertIn("cell_still_declared_", unaddressed[0])
        # And the stash is cleared rather than carried into a scene it was
        # never composed for (pf-adversary D2).
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        self.assertEqual(state.mob_loot_boundary_frames_scene, None)

    def test_a_composer_refusal_is_an_event_not_an_exception(self):
        """The listener thread has no ``except`` above this call.  A refusal
        the composer is entitled to raise (an unmined item id in a standing
        row, a duplicate key, a serializer handle that is not the frozen one)
        must not travel."""
        state = self._state("tok-boundary-refusal")
        self._hold(state)

        def _boom(_legacy, _scene):
            raise mob_loot.MobLootContractError(
                mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD, "measured refusal",
            )

        state.mob_loot_cell.enter_scene_frames = _boom
        state._mob_loot_cross_scene_boundary(DESTINATION_SCENE_ID)
        self.assertIn(
            "mob_loot_boundary_compose_refused_MobLootContractError",
            state.events,
        )
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        self.assertEqual(state.mob_loot_boundary_frames_scene, None)

    # ----- the flush -----------------------------------------------------

    def test_the_boundary_generation_is_held_until_the_census_commits(self):
        state = self._state("tok-boundary-held")
        self._hold(state)
        state.world_census_sent = False
        state.world_census_refused = False
        self.assertEqual(state._mob_loot_boundary_flush(), [])
        self.assertEqual(
            state.mob_loot_boundary_frames_pending, ((b"pc", b"frame"),),
            "a held generation must still be owed after a refused flush",
        )
        state.world_census_sent = True
        released = state._mob_loot_boundary_flush()
        self.assertEqual(released, [("MOB_LOOT_DROP", b"pc", b"frame", 0.0)])
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        self.assertIn("mob_loot_boundary_flushed_frames_1", state.events)
        # Flushed once, never twice.
        self.assertEqual(state._mob_loot_boundary_flush(), [])

    def test_a_refused_census_also_releases_the_held_generation(self):
        """A census that refused by name is never coming.  Holding the ground
        hostage to it would lose the ground forever on that map."""
        state = self._state("tok-boundary-refused-census")
        self._hold(state)
        state.world_census_sent = False
        state.world_census_refused = True
        self.assertEqual(
            state._mob_loot_boundary_flush(),
            [("MOB_LOOT_DROP", b"pc", b"frame", 0.0)],
        )

    def test_the_label_is_the_modules_own_constant_not_a_literal(self):
        state = self._state("tok-boundary-label")
        self._hold(state)
        state.world_census_sent = True
        released = state._mob_loot_boundary_flush()
        self.assertEqual(released[0][0], mob_drop_presence.ACTION_LABEL)

    def test_frames_are_never_released_into_another_scene(self):
        """pf-adversary D2: a stash with no scene on it is a delay, not a
        guard -- any census sets the flag and the bytes go out wherever the
        session happens to be standing."""
        state = self._state("tok-boundary-scene-moved")
        self._hold(state)
        state.world_census_sent = True
        self._stand_in(state, DESTINATION_SCENE_ID)
        self.assertEqual(state._mob_loot_boundary_flush(), [])
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        self.assertEqual(state.mob_loot_boundary_frames_scene, None)
        self.assertTrue(
            [event for event in state.events
             if event.startswith("mob_loot_boundary_dropped_scene_moved_")],
            state.events[-5:],
        )

    def test_a_scenario_ground_lane_in_the_same_dispatch_stands_this_down(self):
        """Those lanes compose EARLIER in the sum, where this flush cannot get
        in front of them.  Erasing an attended lane's frames to publish the
        boundary's would be the same defect in the other direction."""
        state = self._state("tok-boundary-scenario-lane")
        self._hold(state)
        state.world_census_sent = True
        other = [("GROUND_LOOT_HYP", b"pc", b"frame", 0.0)]
        self.assertEqual(state._mob_loot_boundary_flush(other), [])
        self.assertEqual(
            state.mob_loot_boundary_frames_pending, ((b"pc", b"frame"),),
            "the frames must still be owed, not dropped",
        )

    def test_the_flush_rides_after_the_census_and_before_the_kill(self):
        """pf-adversary D1 -- the rule this wiring got backwards once.

        ``MOB_LOOT_WIRING`` step 6: a kill's generation carries the WHOLE
        scene, so it must be the LAST ground generation in the dispatch.  A
        boundary generation appended after it rolls the client's ground back
        to before the player's newest kill.  The combat lane is stubbed to
        one marker action so this pins ORDER, not killing.
        """
        state = self._state("tok-boundary-order")
        self._hold(state)
        state.world_census_sent = True
        state._dispatch_mob_combat = lambda parsed: [
            (mob_drop_presence.ACTION_LABEL, b"kill-pc", b"kill-frame", 0.0),
        ]
        actions = self._dispatch(state, self._action_vital_shaped_pc())
        pcs = [(a[0], a[1]) for a in actions]
        self.assertIn((mob_drop_presence.ACTION_LABEL, b"pc"), pcs)
        self.assertIn((mob_drop_presence.ACTION_LABEL, b"kill-pc"), pcs)
        self.assertLess(
            pcs.index((mob_drop_presence.ACTION_LABEL, b"pc")),
            pcs.index((mob_drop_presence.ACTION_LABEL, b"kill-pc")),
            "the boundary generation must go out BEFORE the kill's, or the "
            "kill's whole-scene generation is not the last writer and the "
            "drop the player just earned is the one the client erases",
        )

    # ----- the refusal the boundary armed --------------------------------

    def test_a_kill_refused_for_being_in_another_scene_breaks_never_raises(self):
        """SOURCE-LEVEL PIN, parsed rather than grepped, and labelled as one.

        Declaring the cell's scene (which the boundary call now does) arms
        ``mob_loot.REFUSE_KILL_IN_ANOTHER_SCENE`` in ``loot_a_kill``.  The
        dispatch site used to re-raise it into a listener thread with no
        ``except``.  A grep for the constant is not enough -- pf-adversary
        replaced the handler's ``break`` with ``raise`` and the grep version
        of this test stayed green -- so this walks the AST and asserts the
        branch for that constant contains no ``raise``.  It is NOT a driven
        kill: no round has produced the refusal yet.
        """
        import ast

        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        branches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            names = {
                child.attr for child in ast.walk(node.test)
                if isinstance(child, ast.Attribute)
            }
            if "REFUSE_KILL_IN_ANOTHER_SCENE" in names:
                branches.append(node)
        self.assertEqual(
            len(branches), 1,
            "expected exactly one handler branch for "
            "REFUSE_KILL_IN_ANOTHER_SCENE in runtime.py",
        )
        body = branches[0].body
        self.assertFalse(
            [n for n in ast.walk(ast.Module(body=body, type_ignores=[]))
             if isinstance(n, ast.Raise)],
            "the handler must not re-raise: this runs in the listener "
            "thread, whose caller in v141 has no except",
        )
        self.assertTrue(
            [n for n in body if isinstance(n, ast.Break)],
            "the handler must stop the retry loop -- the scene disagreement "
            "is a state fact, not a race",
        )


class ThePickupGroundGenerationOnTheRealDispatcherTests(
        SceneBoundaryHarness):
    """R304's ``ground_after`` call site, DRIVEN -- not read.

    Every one of these exists because pf-adversary (round g1y1yc) mutated
    the landed call site and ran the whole repository suite on each mutant:

      * transposing the comprehension's names (``for gframe, gpc in ...``)
        stayed GREEN across 261 tests.  ``mob_drop_presence.ACTION_LABEL``
        exists precisely because a pc/frame swap once did that, and v141
        would then ``sendall`` the UNFRAMED pc behind a valid delta and
        desynchronise the client's stream parser on every pickup.
      * ``return out[1:] + out[:1]`` -- ground generation ahead of the
        delta, the one order the wiring note forbids -- stayed GREEN,
        because the only ordering pin was the position of two substrings in
        the SOURCE TEXT.
      * a filesystem sentinel on the first line of the branch was never
        created by the full suite: not one line of it had ever executed.
        The only thing that ran was a snippet exec'd out of a string in
        another file.

    So this class drives the real dispatcher: a real login, a real character,
    the real bag cell the character-select path claims, a real ground ledger,
    and the client's own bytes at the top.  It asserts what came BACK, which
    is the only thing the client will ever see.
    """

    ITEM = 2400046
    MOB = 0x2068
    DROP_AT = (1000.0, 20.0, 3000.0)

    def _pickup_pc(self, drop_key, opaque=0):
        """The client's own seven-byte pickup body in its envelope."""
        legacy = self.legacy
        body = (
            bytes([mob_pickup_request.PICKUP_REQUEST_OBJECT_REF_TAG])
            + int(drop_key).to_bytes(4, "little")
            + bytes([mob_pickup_request.PICKUP_REQUEST_OPAQUE_U8_TAG, opaque])
        )
        return bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, mob_pickup_request.PICKUP_REQUEST_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _identity(self, state):
        selected = state.foundation.selected
        return (((selected.identity_hi & 0xFFFFFFFF) << 32)
                | (selected.identity_lo & 0xFFFFFFFF))

    def _floor(self, state, rows=2):
        """`rows` of this character's own drops, on the scene it stands in."""
        folder = world_scene_folder.scene_folder_for_scene_id(
            state.foundation.selected.position.scene_id)
        identity = self._identity(state)
        drops = tuple(
            mob_loot.GroundDrop(
                mob_loot.DROP_KEY_BASE + index, self.ITEM, 1,
                mob_loot.as_wire_float(self.DROP_AT[0]),
                mob_loot.as_wire_float(self.DROP_AT[1]),
                mob_loot.as_wire_float(self.DROP_AT[2]),
                self.MOB, identity, folder,
            )
            for index in range(rows)
        )
        state.mob_loot_cell = mob_loot.DropLedgerCell(
            mob_loot.DropLedger(
                drops, 1, mob_loot.DROP_KEY_BASE + rows, ()),
            scene=folder,
        )
        # The click is answered against the position the client last
        # REPORTED, so a session that never moved refuses by name.  One
        # reported step, standing on the drop.
        state.last_target_pos = (
            self.DROP_AT[0], self.DROP_AT[1], self.DROP_AT[2], 0.0)

    def _take_one(self, state):
        return self._dispatch(state, self._pickup_pc(mob_loot.DROP_KEY_BASE))

    def test_a_real_click_answers_with_the_delta_and_then_the_ground(self):
        """The branch, executed end to end, and the order asserted on the
        RETURNED LIST rather than on where two words sit in the source."""
        state = self._state("tok-pickup-order")
        self._floor(state)
        actions = self._take_one(state)
        labels = [action[0] for action in actions]
        self.assertEqual(
            labels,
            ["MOB_PICKUP_REQUEST_DELTA", "MOB_PICKUP_GROUND_AFTER"],
            "the click's reply is not `the delta, then the floor`: %r"
            % (labels,),
        )
        # And the label is the one LANE-B publishes, read out of the note
        # rather than retyped: the operator grades GT-204 off `[G>] <label>`
        # and `SENT label=...` in GAME_LIVE.txt.
        self.assertIn(
            'out += [("%s"' % (labels[1],),
            mob_pickup_request.MOB_PICKUP_REQUEST_WIRING,
        )

    def test_every_frame_the_click_sends_is_framed_around_its_own_pc(self):
        """THE pc/frame SWAP, killed.

        v141 sends ``action[2]`` on the wire and ignores ``action[1]``, so a
        transposed pair ships the unframed payload -- valid-looking, 10 bytes
        short of a frame, straight after a good delta.  Re-derive the framing
        through the frozen serializer instead of trusting the tuple.
        """
        state = self._state("tok-pickup-framing")
        self._floor(state)
        actions = self._take_one(state)
        self.assertEqual(len(actions), 2)
        for label, pc, frame, delay in actions:
            with self.subTest(label=label):
                self.assertEqual(
                    frame, self.legacy.frame_pc(pc),
                    "%s carries a frame that is not this pc's frame -- the "
                    "pair is transposed" % (label,),
                )
                self.assertEqual(delay, 0.0)

    def test_nothing_is_sent_for_the_floor_when_the_last_row_is_taken(self):
        """The call site needs no condition of its own -- driven, not said.

        One row on the floor: the take empties it, ``ground_after`` is ``()``
        by RE-208's open hole, and the reply is the delta alone.
        """
        state = self._state("tok-pickup-last-row")
        self._floor(state, rows=1)
        labels = [action[0] for action in self._take_one(state)]
        self.assertEqual(labels, ["MOB_PICKUP_REQUEST_DELTA"])

    def test_a_pickup_releases_a_committed_boundary_before_its_own_reply(self):
        """The other half of D3: once the arrival census HAS committed, the
        held generation is owed to the client and goes out FIRST -- ahead of
        the delta and ahead of this dispatch's own floor.

        MUTATION-PROOF: delete the ``_mob_loot_boundary_flush()`` call at the
        pickup branch and these bytes never leave the process, because this
        branch returns before the final sum that would have flushed them.
        """
        state = self._state("tok-pickup-flush-first")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state)
        held = ((b"owed-pc", b"owed-frame"),)
        self._hold(state, held)
        state.world_census_sent = True
        actions = self._take_one(state)
        labels = [action[0] for action in actions]
        self.assertEqual(
            labels,
            [mob_drop_presence.ACTION_LABEL,
             "MOB_PICKUP_REQUEST_DELTA", "MOB_PICKUP_GROUND_AFTER"],
            "the owed boundary generation is not first, or this dispatch's "
            "own ground generation is not last: %r" % (labels,),
        )
        self.assertEqual(actions[0][1:3], held[0])
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        # RELEASED, NOT DROPPED, and the console must not say otherwise: the
        # flush already handed these frames to the client, so the guard
        # below finds an empty stash and prints nothing at all.
        self.assertNotIn("MOB_LOOT_BOUNDARY_STASH_CLEARED", self.console)

    def test_a_pickup_after_a_warp_flushes_the_held_boundary_first(self):
        """pf-adversary D3, and it is the reason the flush call is there.

        This branch RETURNS -- it never reaches the final sum where
        ``_mob_loot_boundary_flush`` is consulted.  Before R304 a pickup
        taken on the first dispatch after a GM warp left the stale arrival
        generation in the stash, and the NEXT ordinary poll published it:
        a PRE-take generation landing AFTER the POST-take one, which by
        RE-082 puts the row already in the player's bag back on the floor
        while the console says PUBLISHED.

        MUTATION-PROOF: delete the flush call at the pickup branch and the
        stash is still full after the click; the pre-take generation then
        arrives on the next poll and both assertions below fail.
        """
        state = self._state("tok-pickup-after-warp")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state)
        held = ((b"stale-pc", b"stale-frame"),)
        self._hold(state, held)
        actions = self._take_one(state)
        labels = [action[0] for action in actions]
        # The census has not committed on this dispatch, so the flush is
        # still holding: the stale generation must therefore be DROPPED by
        # name rather than published later, and the click's own reply is
        # the delta and the post-take floor.
        self.assertEqual(
            labels,
            ["MOB_PICKUP_REQUEST_DELTA", "MOB_PICKUP_GROUND_AFTER"],
            "this dispatch's own ground generation must be LAST: %r"
            % (labels,),
        )
        self.assertIn(
            "mob_loot_boundary_superseded_by_pickup_%s_frames_%d"
            % (mob_loot.scene_key(world_scene_folder
                                  .scene_folder_for_scene_id(
                                      DESTINATION_SCENE_ID)), len(held)),
            state.events,
        )
        # The stash is empty afterwards, so no later poll can re-publish
        # the pre-take floor behind the removal that just went out.
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        # The OTHER console reason, so one shared token cannot satisfy both
        # cases: here a post-take floor really did replace the stash.
        self.assertIn(
            "MOB_LOOT_BOUNDARY_STASH_CLEARED reason=superseded_by_pickup",
            self.console, self.console,
        )
        for _ in range(3):
            self.assertEqual(
                self._ground(self._dispatch(state, self.empty_poll_pc)), [])

    def test_taking_the_last_row_also_drops_the_stale_boundary(self):
        """THE HOLE R304 LEFT OPEN, and the reason this guard now asks
        ``handled`` instead of ``ground_after`` (COO-DECISION
        2026-09-02T17:46+07:00).

        One row on the floor, taken on the first dispatch after a warp, so
        the flush is still holding.  ``ground_after`` is ``()`` here --
        RE-208's open hole: the scene is empty afterwards and an empty
        generation is a client no-op, so nothing is composed.  With the old
        condition the stash therefore survived the click and the next
        ordinary poll published the PRE-take generation, putting the row
        already in the player's bag back on the floor (RE-082).

        MUTATION-PROOF: restore ``if outcome.ground_after and ...`` and the
        polls below hand back the stale generation, failing on both the
        missing event and the frames that arrive after it.
        """
        state = self._state("tok-pickup-last-row-stash")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state, rows=1)
        held = ((b"stale-pc", b"stale-frame"),)
        self._hold(state, held)
        labels = [action[0] for action in self._take_one(state)]
        # The take succeeded and said nothing about the floor -- that half
        # is R304's behaviour and stays.
        self.assertEqual(labels, ["MOB_PICKUP_REQUEST_DELTA"])
        # AND IT IS NAMED FOR WHAT HAPPENED (COO-DECISION
        # 2026-09-02T17:46+07:00, point 2): nothing replaced the stash in
        # this reply, so the token must not say "superseded" -- an operator
        # grading GT-204 would read that as a redraw the client never got.
        self.assertIn(
            "mob_loot_boundary_last_object_pickup_%s_frames_%d"
            % (mob_loot.scene_key(world_scene_folder
                                  .scene_folder_for_scene_id(
                                      DESTINATION_SCENE_ID)), len(held)),
            state.events,
            "the pre-take generation survived a successful take, or the "
            "drop is misnamed as a supersede: %r"
            % ([e for e in state.events if "mob_loot_boundary" in e],),
        )
        self.assertEqual(state.mob_loot_boundary_frames_pending, ())
        # AND THE OPERATOR CAN READ IT.  Every other mob_loot_boundary_*
        # token is self.events only, which reaches no console without
        # --export-events; GT-204 is graded off what the bridge console
        # shows.  ASCII, so cp874 cannot break the report mid-line.
        self.assertIn(
            "MOB_LOOT_BOUNDARY_STASH_CLEARED reason=last_object_pickup",
            self.console, self.console,
        )
        self.console.encode("cp874")
        # And no later poll resurrects the row the player is carrying.
        for _ in range(3):
            self.assertEqual(
                self._ground(self._dispatch(state, self.empty_poll_pc)), [])

    def test_a_refused_take_leaves_the_boundary_generation_owed(self):
        """A click that takes nothing leaves the arrival generation OWED.

        🔴 WHAT THIS DOES **NOT** PIN, corrected before it shipped
        (pf-adversary D3, measured with a sentinel at the guard): the
        refusal returns at ``if outcome.delta is None: return []``, ABOVE
        the stash guard, so this test never executes that guard at all.
        Its first draft claimed to pin "the other side of the guard, so it
        cannot be widened into drop-the-stash-on-every-click" -- that claim
        was false twice over, because the guard's own condition is
        invariantly true where it is read.  What this test really pins is
        the early return, which is worth keeping: it is what stops a
        stranger's frame from touching an owed generation.
        """
        state = self._state("tok-pickup-refused-keeps-stash")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state)
        held = ((b"owed-pc", b"owed-frame"),)
        self._hold(state, held)
        actions = self._dispatch(
            state, self._pickup_pc(mob_loot.DROP_KEY_BASE + 900))
        self.assertEqual([action[0] for action in actions], [])
        self.assertEqual(state.mob_loot_boundary_frames_pending, held)
        state.world_census_sent = True
        self.assertEqual(
            state._mob_loot_boundary_flush(),
            [("MOB_LOOT_DROP", b"owed-pc", b"owed-frame", 0.0)],
        )

    def test_a_refused_publication_is_not_reported_as_an_empty_scene(self):
        """THE THIRD NAME, and the measured reason it exists.

        ``ground_after`` is ``()`` for two different reasons and only one
        of them is "the scene is empty now".  When
        ``frames_after_a_row_left`` refuses, the take still happened, the
        stash is still stale, and the floor still holds every other row --
        two of them, in pf-adversary's measurement of this exact setup,
        under a console line that said the player had taken the last
        object.  An operator grading GT-204 off that line reports an empty
        floor they are looking straight at.

        MUTATION-PROOF: name this case ``last_object_pickup`` again (i.e.
        select on ``ground_after`` alone) and both assertions below fail on
        the word.
        """
        state = self._state("tok-pickup-publication-refused")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state, rows=3)
        held = ((b"stale-pc", b"stale-frame"),)
        self._hold(state, held)

        def _refuse(_legacy, _key):
            raise mob_loot.MobLootContractError(
                mob_loot.REFUSE_TYPE_NOT_TYPED_RECORD, "measured refusal",
            )

        state.mob_loot_cell.frames_after_a_row_left = _refuse
        labels = [action[0] for action in self._take_one(state)]
        # The take is answered; only the floor publication was lost.
        self.assertEqual(labels, ["MOB_PICKUP_REQUEST_DELTA"])
        scene = mob_loot.scene_key(
            world_scene_folder.scene_folder_for_scene_id(
                DESTINATION_SCENE_ID))
        self.assertIn(
            "mob_loot_boundary_publication_refused_%s_frames_%d"
            % (scene, len(held)), state.events,
            [e for e in state.events if "mob_loot_boundary" in e],
        )
        self.assertIn(
            "MOB_LOOT_BOUNDARY_STASH_CLEARED reason=publication_refused "
            "scene=%s frames=%d rows_left=-1" % (scene, len(held)),
            self.console, self.console,
        )

    def test_a_stash_tagged_for_another_scene_is_never_dropped_here(self):
        """THE SCENE GUARD AT THIS CALL SITE, which no test reached
        (pf-adversary D5: deleting it stayed green across the whole
        repository suite while this file's own header advertises
        MUTATION-PROOF).

        A crossing can leave a stash tagged for scene A while the session
        stands in scene B -- that is the state
        ``_mob_loot_cross_scene_boundary`` exists for.  Destroying scene
        A's frames from a pickup made in scene B loses bytes nobody in
        scene B was owed, and names the wrong scene while doing it.

        MUTATION-PROOF: drop the scene conjunct (``if standing is not
        None:``) and the two assertions below fail on frames that were
        thrown away and an event that named scene B.
        """
        state = self._state("tok-pickup-other-scene-stash")
        self._warp(state, DESTINATION_SCENE_ID)
        self._floor(state)
        other = ((b"scene-a-pc", b"scene-a-frame"),)
        state.mob_loot_boundary_frames_pending = other
        state.mob_loot_boundary_frames_scene = mob_loot.scene_key(
            world_scene_folder.scene_folder_for_scene_id(1))
        self._take_one(state)
        self.assertEqual(state.mob_loot_boundary_frames_pending, other)
        self.assertEqual(
            [e for e in state.events
             if e.startswith("mob_loot_boundary_superseded")
             or e.startswith("mob_loot_boundary_publication_refused")
             or e.startswith("mob_loot_boundary_last_object")], [],
        )
        self.assertNotIn("MOB_LOOT_BOUNDARY_STASH_CLEARED", self.console)


if __name__ == "__main__":
    unittest.main()
