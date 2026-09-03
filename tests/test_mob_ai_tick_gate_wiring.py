"""The mob-AI tick gate at runtime.py's dispatch(), measured by its ANSWER.

COO-DECISION 2026-09-03T16:48+07:00, on LANE-B's CORE-REQUEST
20260903_1639.  The call site guarded ``lane_b_mob_ai_tick.maybe_tick``
with the hand-typed string ``"lane_hooks.lane_b_mob_ai_tick"``.
``lane_hooks.module_production_allowed()`` qualifies a name that does not
already start with its own ``__name__`` by PREFIXING it, so the argument
resolved to ``pirateforce_foundation.lane_hooks.lane_hooks.
lane_b_mob_ai_tick`` -- a key no module owns -- and the fail-closed lookup
answered ``False`` on every frame.  The tick never ran for a player.

WHY THIS FILE EXISTS AND WHAT IT REFUSES TO BE.  The card that stated the
defect (tests/test_mob_aggro.py::test_the_tick_gate_is_reported_not_
assumed) hardcodes both spellings and asks the RESOLVER; it never reads
the call site, and its own prose says so in a struck-out sentence.  The
card that watched the site
(test_the_gate_answers_what_it_answered_at_every_hand_spelled_site) can
only see call sites that type a STRING LITERAL, so the repair COO ordered
-- read ``MODULE_NAME`` off the module, which is what makes a rename
unable to re-open the hole -- takes that site out of its table by design.

So the site would be unwatched exactly the way it was unwatched for the
two days the tick was dead.  This file watches it the only way that
survives both repairs: it BOOTS THE REAL DISPATCHER, sends a real
TargetPos frame, and reads the console the gate is supposed to produce.
Reverting the argument to the old string, to any other name that does not
resolve, or deleting the branch, goes red here.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import lane_b_mob_ai_tick  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RUNTIME_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
LIVE_TOKEN = "MOB_AI_TICK_LIVE"
STEP_ANCHOR = (11.0, 22.0, 33.0)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobAiTickGateWiringTests(unittest.TestCase):
    """Same boot shape as tests/test_lane_scene_census_wiring.py: the real
    state class, a throwaway SQLite database, and a real TargetPos frame
    parsed by the legacy parser.  Nothing here registers a double."""

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

    # ----- harness ------------------------------------------------------

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

    def _booted(self, token, scene_id=None):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        )
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        if scene_id is not None:
            # Same seeding route as tests/test_lane_scene_census_wiring.py,
            # for the same recorded reason (nothing in this tree seeds a
            # non-default scene on a real boot yet).
            destination = world_scene_travel.destination(scene_id)
            spawn = world_scene_travel.spawn_position(destination)
            self.store.select_character(
                state.foundation.session_id, character.selector,
            )
            self.store.save_position(
                state.foundation.session_id, character.id,
                Position(scene_id, 0, spawn[0], spawn[1], spawn[2], 0.0),
            )
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _step(self, state, xyz=STEP_ANCHOR):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            state.dispatch(
                self.legacy.parse_outer(self._target_pos_pc(xyz))
            )
        return out.getvalue(), err.getvalue()

    @staticmethod
    def _live_lines(out: str) -> list[str]:
        return [
            line for line in out.splitlines()
            if line.startswith(LIVE_TOKEN)
        ]

    # ----- the gate's answer, on the real dispatcher ---------------------

    def test_a_target_pos_frame_reaches_the_tick(self):
        # THE ONE THAT DIES ON THE REVERT.  Not "is the argument spelled
        # right" -- the tick's own FIRED token, printed from inside
        # maybe_tick() by lane_hooks.announce_direct_fire, on a frame the
        # real dispatcher routed.  Put the old string back and this is
        # the assertion that goes red, because the gate answers False and
        # the branch is skipped in silence, which is exactly how the
        # defect stayed invisible for two days.
        state = self._booted("mob_ai_tick_reached")
        _out, err = self._step(state)
        self.assertIn(
            "LANE_HOOK_FIRED %s %s" % (
                lane_b_mob_ai_tick.MODULE_NAME, lane_b_mob_ai_tick.POINT,
            ),
            err,
            "the aggro tick did not fire on a TargetPos frame the real "
            "dispatcher accepted: the gate at the call site is answering "
            "False again (a name it hands module_production_allowed that "
            "no module owns answers False and skips in total silence)",
        )

    def test_the_live_line_names_the_scene_and_the_mob_count(self):
        # COO-DECISION 20260903_1648 item 4: one line, so an attended
        # round reads the gate's answer off the build it is RUNNING.
        # Both numbers are derived from the booted state, never typed:
        # a line that hardcoded either would pass its own check here and
        # tell the operator a number the server did not measure.
        state = self._booted("mob_ai_tick_live_line")
        expected_scene = state.foundation.selected.position.scene_id
        expected_mobs = len(state.mob_ai_register.rows)
        out, _err = self._step(state)
        self.assertEqual(
            self._live_lines(out),
            ["%s scene=%d mobs=%d" % (
                LIVE_TOKEN, expected_scene, expected_mobs,
            )],
            "the MOB_AI_TICK_LIVE line is missing or does not name the "
            "scene and register this session actually ticked",
        )

    def test_the_live_line_reports_a_scene_that_is_not_the_home_scene(self):
        # THE MUTANT THE CARD ABOVE CANNOT CATCH ON ITS OWN, MEASURED:
        # a boot lands the character on the home scene, whose id is 1, so
        # ``scene=1`` typed as a literal passes a check that derives its
        # expectation from that same boot.  This one seeds a character on
        # scene 278 (the beach football field, real in
        # scene_entry_registry) before StartGame, so a constant in the
        # line is a wrong number instead of a lucky one.
        state = self._booted("mob_ai_tick_other_scene", scene_id=278)
        self.assertEqual(state.foundation.selected.position.scene_id, 278)
        out, _err = self._step(state)
        self.assertEqual(
            self._live_lines(out),
            ["%s scene=278 mobs=%d" % (
                LIVE_TOKEN, len(state.mob_ai_register.rows),
            )],
        )

    def test_the_live_line_is_one_per_session_not_one_per_frame(self):
        # A player walking sends TargetPos continuously.  A line per
        # frame is a console flood, and the latch that prevents it is the
        # kind of state a later round breaks without noticing.
        state = self._booted("mob_ai_tick_once")
        first, _err = self._step(state)
        second, _err2 = self._step(state, xyz=(12.0, 23.0, 34.0))
        third, _err3 = self._step(state, xyz=(13.0, 24.0, 35.0))
        self.assertEqual(len(self._live_lines(first)), 1)
        self.assertEqual(self._live_lines(second), [])
        self.assertEqual(self._live_lines(third), [])

    def test_the_line_is_console_safe(self):
        # AGENTS.md section 9: the bridge console is cp874.  Every byte
        # this line can print is derived from two integers and a fixed
        # ASCII prefix, and this pins that -- a later round that adds a
        # scene NAME to it would put an operator-supplied string on a
        # console that cannot render one.
        state = self._booted("mob_ai_tick_ascii")
        out, _err = self._step(state)
        line = self._live_lines(out)[0]
        self.assertEqual(line, line.encode("ascii", "strict").decode("ascii"))

    # ----- what the console tokens above CANNOT see ---------------------
    #
    # ADDED AFTER A pf-adversary PASS ON THE FIRST DRAFT OF THIS FILE
    # (round `gjyxt5`).  That draft had seven cards and the reviewer got
    # FIVE mutants of the call site past all of them AND past the whole
    # 8,808-test suite: discarding the register the tick returns, moving
    # the call inside the once-per-session latch, passing the origin
    # instead of the player's position, passing identity 1, and -- the
    # worst -- ``or True`` after the gate, which reads the owner's kill
    # switch and then ignores it.  Console tokens cannot see any of that:
    # they prove the branch was ENTERED.  These cards watch the call.

    def _spy_on_the_tick(self):
        """Record every ``maybe_tick`` call the dispatcher makes, and let
        the real one run.  Patches the attribute runtime.py reads
        (``lane_b_mob_ai_tick.maybe_tick``), so a call site that stopped
        going through this module would show up as zero calls."""
        calls = []
        real = lane_b_mob_ai_tick.maybe_tick

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return real(*args, **kwargs)

        patch = mock.patch.object(lane_b_mob_ai_tick, "maybe_tick", spy)
        patch.start()
        self.addCleanup(patch.stop)
        return calls

    def test_a_closed_gate_stands_the_tick_down(self):
        # THE KILL SWITCH, MEASURED AS A REFUSAL AND NOT AS A FLAG READ.
        # COO-DECISION 20260829_0041 option (b) is "the call site reads
        # the flag BEFORE it calls" -- the whole point being that an owner
        # who closes a lane stops its code from running on a live server.
        # Nothing in the tree proved this call site obeys the answer it
        # asks for: ``or True`` after the gate passed every other card
        # here while the tick kept firing on every frame.  This is the
        # same shape tests/test_lane_scene_census_wiring.py's
        # test_a_closed_module_stands_down_to_the_not_home_skip already
        # has for the census point, and the file this one borrows its
        # boot from is where the omission showed.
        calls = self._spy_on_the_tick()
        previous = lane_hooks._PRODUCTION_ALLOWED[lane_b_mob_ai_tick.MODULE_NAME]
        lane_hooks._PRODUCTION_ALLOWED[lane_b_mob_ai_tick.MODULE_NAME] = False
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__,
            lane_b_mob_ai_tick.MODULE_NAME, previous,
        )
        state = self._booted("mob_ai_tick_closed")
        out, err = self._step(state)
        self.assertEqual(
            calls, [],
            "the tick ran while its module was NOT production_allowed: the "
            "call site asked the gate and then ignored the answer, so the "
            "owner's switch no longer stops this lane",
        )
        self.assertEqual(self._live_lines(out), [])
        self.assertNotIn(lane_b_mob_ai_tick.MODULE_NAME, err)

    def test_the_tick_runs_on_every_frame_not_once_per_session(self):
        # The console line is latched on purpose; the TICK must not be.
        # Moving the call inside that latch leaves every token check in
        # this file green (the line still prints once, the token still
        # fires once) while the decision loop runs for one frame of the
        # session and never again.
        calls = self._spy_on_the_tick()
        state = self._booted("mob_ai_tick_every_frame")
        self._step(state)
        self._step(state, xyz=(12.0, 23.0, 34.0))
        self._step(state, xyz=(13.0, 24.0, 35.0))
        self.assertEqual(
            len(calls), 3,
            "the tick did not run on every TargetPos frame: a player who "
            "keeps walking must keep being ticked",
        )

    def test_the_register_the_tick_returns_is_the_one_the_session_keeps(self):
        # ``maybe_tick`` is pure: it RETURNS the advanced register instead
        # of mutating one.  A call site that drops the return value ticks
        # for ever and accumulates nothing, and every console token still
        # fires.  The sentinel makes the assignment, not the call, the
        # thing being measured.
        sentinel = object()
        state = self._booted("mob_ai_tick_stored")
        with mock.patch.object(
                lane_b_mob_ai_tick, "maybe_tick",
                lambda *a, **k: (sentinel, ())):
            self._step(state)
        self.assertIs(
            state.mob_ai_register, sentinel,
            "the register the tick returned was discarded: the session "
            "kept the one it had, so nothing the AI decides survives the "
            "frame it decided it in",
        )

    def test_the_tick_is_told_this_players_identity_and_position(self):
        # The arguments, derived from the state and the frame rather than
        # typed here.  Passing the origin, or an identity no player has,
        # leaves the mobs looking at a phantom -- and leaves every
        # console token in this file green, because the branch still ran.
        calls = self._spy_on_the_tick()
        state = self._booted("mob_ai_tick_arguments")
        selected = state.foundation.selected
        expected_identity = (
            (selected.identity_hi & 0xFFFFFFFF) << 32
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        self._step(state, xyz=(101.0, 202.0, 303.0))
        self.assertEqual(len(calls), 1)
        args, _kwargs = calls[0]
        _register, _ledger, performer, position = args[:4]
        self.assertEqual(performer, expected_identity)
        self.assertEqual(position, (101.0, 202.0, 303.0))

    # ----- the call site itself -----------------------------------------

    def test_the_call_site_reads_the_module_constant_not_a_string(self):
        # WHY A SHAPE CHECK SURVIVES NEXT TO THE VALUE CHECKS ABOVE: the
        # value checks pass for ANY spelling that resolves, including the
        # fully qualified string typed by hand.  That spelling works
        # today and silently stops working the day the module is renamed
        # or moved -- the same class of defect, re-armed.  COO ordered
        # MODULE_NAME specifically, so this pins the ORDER, not the
        # behaviour, and says which is which.
        tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
        spellings = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = (
                callee.attr if isinstance(callee, ast.Attribute)
                else callee.id if isinstance(callee, ast.Name)
                else None
            )
            if name != "module_production_allowed":
                continue
            argument = node.args[0] if node.args else None
            for keyword in node.keywords:
                if keyword.arg == "module_name":
                    argument = keyword.value
            if (isinstance(argument, ast.Attribute)
                    and isinstance(argument.value, ast.Name)
                    and argument.value.id == "lane_b_mob_ai_tick"):
                spellings.append(argument.attr)
        self.assertEqual(
            spellings, ["MODULE_NAME"],
            "runtime.py must ask the tick gate with "
            "lane_b_mob_ai_tick.MODULE_NAME exactly once (COO-DECISION "
            "20260903_1648 item 3); a hand-typed string is what broke it",
        )

    def test_the_constant_the_call_site_reads_is_the_key_the_gate_holds(self):
        # The two halves of the repair, stated where a reader sees both:
        # the module's own MODULE_NAME resolves, and the string that was
        # there before it does not.  The second half is why "it looks
        # like a module name" is not a check -- it looked like one for
        # two days while answering False.
        self.assertIs(
            lane_hooks.module_production_allowed(
                lane_b_mob_ai_tick.MODULE_NAME),
            True,
        )
        self.assertIs(
            lane_hooks.module_production_allowed(
                "lane_hooks.lane_b_mob_ai_tick"),
            False,
        )
        # AND THE HALF THE COMMENT AT THE CALL SITE USED TO OVERSTATE
        # (pf-adversary, same round): MODULE_NAME is itself a hand-typed
        # literal in the lane's file.  Reading it off the module makes
        # ONE spelling authoritative instead of two, which is a real
        # improvement, but it is not rename-proof by itself -- a rename
        # that misses that literal moves the same hole one file over.
        # This is what actually closes it, and it is why the card must
        # not be deleted as redundant with the behaviour cards above.
        self.assertEqual(
            lane_b_mob_ai_tick.MODULE_NAME, lane_b_mob_ai_tick.__name__,
            "the lane's MODULE_NAME no longer matches its own module "
            "path: the gate will answer False for a name nobody owns "
            "again, silently, exactly as it did before this round",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
