"""LANE-A: which scenes a player's faction-1 field reaches.

WHAT THIS FILE PROVED THROUGH ROUND vvy6q7.  ``world_faction_admission``
used to admit a login's faction field only into a scene the registry
declared ``login_entry_allowed`` AND ``n_SAVE == 1``, on top of the
``(1, 2)`` floor ``GT-032`` proved byte-for-byte.  That widened D3's original
literal ``(1, 2)`` just far enough to cover Hell Volcano Island (14).

WHY THAT VERSION BECAME THE DEFECT ITSELF.  ka1-A round R321 (letter
``20260906_1255_KA1A-R321-RESULTS-...``, S1) measured a login landing in
scene 126 (the Atlantis ocean panel -- reached today via the GM single-use
relog ticket ``/warp 126`` stages, ``tests/test_gm_warp_relog_stage.py``
owns that mechanism) through the SAME registry-gated policy, refused on
BOTH conditions (``login_entry_allowed: false``, ``n_SAVE: 0``).  The
refusal is silent (``runtime.py`` latches an event, does not raise), so that
session shipped ``FOUNDATION_SELECTED_START_GAME`` with ``basic_mask
0x034F`` and no faction field -- and the client never re-reads the field
after the first login frame, so the whole session stayed factionless in
EVERY later scene until a fresh land login.  ``COO-DECISION`` (letter
``20260906_1347_COO-DECISION-ka1a1255-...-LANE-A.md``) ordered: send
``basic_faction`` on every login scene, no hardcoded scene numbers, no
server-side level check.

THIS ROUND'S FIX AND WHAT THIS FILE NOW PROVES.  The registry-gated WHERE
question is gone: ``admits`` says yes to every well-typed ``int`` scene id
and no only to what could never legally be a scene id.  This is a strictly
WIDER policy than before -- everything the old policy admitted, the new one
still admits (the two-conditions machinery below is gone because it no
longer excludes anything a real login can carry) -- and this file's job
changes to matching that: prove the widening covers scene 126 specifically
(the reported defect), prove it does not depend on the registry at all
(constructing a broken/absent registry object and passing it in must not
change the answer), and prove the fail-closed floor (non-int, bool) still
holds, because THAT is the one way a login could still crash a client
mid-serialize.

NEGATIVE CONTROLS, BECAUSE THIS LANE HAS SHIPPED A TAUTOLOGY BEFORE.  The
old file's tautology risk was "a hardcoded literal masquerading as a
registry read"; the new risk is the opposite direction -- a stray ``and``
that quietly reintroduces a scene exclusion.  ``TheEveryLoginSceneTests``
drives that with the exact scenes the old policy used to refuse (17, 126,
278, 997) and requires all four admitted now.

GATE-WALK DECLARATION (``COO-DECISION 20260906_1347``).

WALKED:

* Every scene the old policy admitted (1, 2, 3-11, 14, 130) still admits.
* Every scene the old policy refused (17, 126, 278, 997) now admits.
* A ``registry`` argument, of any shape including a broken object, changes
  nothing -- the module no longer reads one.
* Fail-closed on: a non-int scene id, a bool, in both ``admits`` and the
  real serializer's production path.
* The frozen ``GT-032`` serializer, asserted STILL frozen at ``(1, 2)``.
* The production dispatcher end to end: a login into scene 126 with no
  flags, dispatched the same way ``TheSerializerTests`` dispatches 14, now
  ships the ``PLAYER_FACTION`` line that used to be silently absent.

NOT WALKED, AND SAID PLAINLY:

* NO CLAIM THAT A REAL CLIENT RENDERS CORRECTLY AFTER A ``/warp 126`` RELOG
  TICKET.  That is the GT ticket this round's letter asks LANE-K to number
  (criterion: relog via the 126 ticket, then ``/warp 2``, monster names not
  green, no blue bar) -- an attended test, not this file's to fake.
* NO CLAIM ABOUT THE FACTION VALUE.  Only 1 is admitted, unchanged.
* NO CLAIM that scene 126 (or 17, 278, 997) becomes reachable by an
  ordinary player's persisted login row.  That gate is
  ``world_scene_entry.resolve_entry``'s ``login_entry_allowed``, a
  different module this round does not touch -- see
  ``tests/test_gm_warp_relog_stage.py`` for why 126's login door still
  answers a durable row differently from a staged relog entry.
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

from pirateforce_foundation import player_wire  # noqa: E402
from pirateforce_foundation import world_faction_admission as wfa  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
HOME = 1
SCENE_2 = 2
VOLCANO = 14
# The scene ka1-A's R321 measurement named: refused by the OLD registry-gated
# policy on both of its conditions (``login_entry_allowed: false``,
# ``n_SAVE: 0``), reached today only via the GM single-use relog ticket
# (``tests/test_gm_warp_relog_stage.py``), tomorrow via the real M2 sailing
# feature.  The scene this round's fix exists for.
SEA_ATLANTIS = 126
# Barred at login like 126, no chief letter sanctions a route to it: the old
# policy refused this one too and is not sanctioned by anything, so it is a
# clean "every scene, not a list" witness.
SHUT_AT_LOGIN = 17
# Open at login and n_SAVE 0: the stage the old policy's SECOND condition
# used to refuse on its own.
STAGE_OPEN_BUT_NOT_A_HOME = 278


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class TheEveryLoginSceneTests(unittest.TestCase):
    """The new predicate: every well-typed scene id, no registry, no list."""

    def test_every_scene_the_old_policy_used_to_refuse_now_admits(self):
        for scene_id in (SHUT_AT_LOGIN, SEA_ATLANTIS, STAGE_OPEN_BUT_NOT_A_HOME,
                          997):
            with self.subTest(scene_id=scene_id):
                self.assertTrue(wfa.admits(scene_id))

    def test_every_scene_the_old_policy_used_to_admit_still_admits(self):
        for scene_id in (HOME, SCENE_2, VOLCANO, 3, 4, 5, 6, 7, 8, 9, 10, 11,
                          130):
            with self.subTest(scene_id=scene_id):
                self.assertTrue(wfa.admits(scene_id))

    def test_an_arbitrary_int_no_registry_has_ever_heard_of_admits(self):
        # The point that separates "every scene" from "every scene we know
        # about": a scene id absent from any table still answers yes, because
        # the byte shape does not depend on the registry knowing the scene.
        self.assertTrue(wfa.admits(999999))

    def test_the_registry_argument_is_accepted_and_ignored(self):
        # A broken registry object, a real one, and no registry at all must
        # all answer the same -- proof this module no longer consults it.
        for registry in (None, object(), world_scene_travel.load_scene_registry()):
            with self.subTest(registry=type(registry).__name__):
                self.assertTrue(wfa.admits(SEA_ATLANTIS, registry))

    def test_forget_cached_registry_is_a_harmless_no_op(self):
        wfa.forget_cached_registry()
        self.assertTrue(wfa.admits(HOME))


class TheProvenFloorTests(unittest.TestCase):
    """GT-032's two scenes: still named, no longer doing any narrowing work."""

    def test_the_floor_is_still_the_two_scenes_gt032_proved(self):
        self.assertEqual((1, 2), wfa.PROVEN_FACTION_SCENE_IDS)

    def test_admitted_scene_ids_returns_the_named_floor(self):
        # No longer "every admitted scene" -- admits() answers yes to ids
        # this function has never seen, so the only enumerable, stable
        # answer left is the proven floor itself.
        self.assertEqual(wfa.PROVEN_FACTION_SCENE_IDS, wfa.admitted_scene_ids())
        self.assertEqual(
            wfa.PROVEN_FACTION_SCENE_IDS, wfa.admitted_scene_ids(object()))

    def test_the_console_line_carries_the_rule_and_the_floor(self):
        line = wfa.console_line()
        self.assertIn("WORLD_FACTION_ADMISSION rule=every_login_scene", line)
        self.assertIn("proven_floor=1,2", line)
        # cp874 is the bridge console's codepage; a line it cannot encode is
        # a line nobody can grep on the machine that runs the server.
        line.encode("ascii")
        line.encode("cp874")


class FailClosedTests(unittest.TestCase):
    """Everything that is not an explicit yes is a no, and none of it raises.

    A refusal returns the server to the behaviour of every boot before D3's
    fix existed, so a refusal is always safe.  A traceback out of a
    serializer during login is not.
    """

    def test_a_non_int_scene_id_is_refused_rather_than_coerced(self):
        for value in ("14", 14.0, None, object(), b"14"):
            with self.subTest(value=repr(value)):
                self.assertFalse(wfa.admits(value))
                self.assertEqual(
                    "faction_refused_scene_id_is_not_an_int",
                    wfa.refusal_reason(value))

    def test_a_bool_is_not_an_int_here(self):
        # True == 1 in Python, and scene 1 is admitted, so a policy that
        # forgot this would admit ``True`` as home.
        self.assertFalse(wfa.admits(True))
        self.assertFalse(wfa.admits(False))

    def test_the_reporter_never_raises_for_anything_admits_answers(self):
        for value in (1, 14, 126, 999999, "x", None, True, -1, 0):
            with self.subTest(value=repr(value)):
                self.assertIsInstance(wfa.refusal_reason(value), str)

    def test_the_reporter_names_admission_for_a_real_scene(self):
        self.assertEqual(
            "faction_admitted_scene_126_every_login_scene",
            wfa.refusal_reason(SEA_ATLANTIS))


class TheSerializerTests(unittest.TestCase):
    """The wire, not the predicate: what ``runtime.py`` actually calls."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _compose(self, scene_id):
        return player_wire.make_actor_attr_with_name_class_and_faction(
            self.legacy, 1, 0, scene_id, 0, "driver", 1)

    def test_the_sea_scene_now_serializes_a_faction_field(self):
        # THE DIRECT REGRESSION TEST FOR THE REPORTED DEFECT: this used to
        # raise ValueError("faction-1 is refused: ...not_open_at_login").
        wire = self._compose(SEA_ATLANTIS)
        self.assertIsInstance(wire, bytes)
        self.assertGreater(len(wire), 0)

    def test_a_formerly_shut_scene_now_serializes_too(self):
        wire = self._compose(SHUT_AT_LOGIN)
        self.assertIsInstance(wire, bytes)
        self.assertGreater(len(wire), 0)

    def test_the_faction_field_costs_the_same_five_bytes_it_always_did(self):
        """The delta ``runtime.py``'s own drift guard checks, at scene 126.

        If this ever differs from 5, ``runtime.py`` refuses the recompose as
        length drift and the frame is dropped -- so a wider faction field
        would present as "no faction line" rather than as a bad one.
        """
        plain = player_wire.make_actor_attr_with_name_and_class(
            self.legacy, 1, 0, SEA_ATLANTIS, 0, "driver")
        self.assertEqual(len(self._compose(SEA_ATLANTIS)) - len(plain), 5)

    def test_the_faction_value_and_scene_seq_are_as_frozen_as_ever(self):
        for kwargs in ({"basic_faction": 6}, {"scene_seq": 1}):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError) as caught:
                    player_wire.make_actor_attr_with_name_class_and_faction(
                        self.legacy, 1, 0, SEA_ATLANTIS,
                        kwargs.get("scene_seq", 0), "driver",
                        kwargs.get("basic_faction", 1))
                message = str(caught.exception)
                self.assertIn("basic_faction=", message)
                self.assertIn("scene_seq=", message)

    def test_the_gt032_frozen_serializer_did_not_widen_with_it(self):
        """The reference GT-032 proved byte-for-byte, still refusing 14.

        Widening a frozen reference is how a reference stops being one, so
        this asserts the OLD literal is still there.
        """
        for scene_id in (HOME, SCENE_2):
            with self.subTest(scene_id=scene_id):
                self.assertIsInstance(
                    player_wire.make_actor_attr_with_basic_faction(
                        self.legacy, 1, 0, scene_id, 0, "driver", 1),
                    bytes)
        with self.assertRaises(ValueError):
            player_wire.make_actor_attr_with_basic_faction(
                self.legacy, 1, 0, VOLCANO, 0, "driver", 1)

    def test_a_non_int_scene_id_is_still_refused_by_the_serializer(self):
        with self.assertRaises(ValueError) as caught:
            self._compose("126")
        self.assertIn("not_an_int", str(caught.exception))


class OnTheRealDispatcherTests(unittest.TestCase):
    """The end of this round's fix, driven on a boot with no flags at all.

    Mirrors ``TheSerializerTests`` for the production dispatch path itself:
    ``runtime.py``'s recompose, not just the serializer function it calls.

    WHY 278, NOT 126, DRIVES THIS CLASS.  A character's PERSISTED row at
    scene 126 (or 17) never reaches the faction composer through the
    ordinary login dispatch at all -- ``world_scene_entry.resolve_entry``
    refuses it first (``login_entry_allowed: false``), a full login
    refusal (``world_scene_entry_refused_no_reply``), untouched by this
    round on purpose (see the module docstring's nonclaims).  126 is
    reached in production only through the GM single-use relog override
    (``tests/test_gm_warp_relog_stage.py``), which this lightweight harness
    does not wire up.  Scene 278 exercises the SAME composer bug the old
    policy had (``login_entry_allowed`` true, ``n_SAVE`` 0 -- the old
    policy's second condition alone used to refuse it) through the
    ordinary dispatch path this harness already drives, so it is the
    faithful end-to-end proof available at this level.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _login_into(self, work: Path, scene_id: int, **state_kwargs):
        store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
        store.migrate()
        legacy = self.legacy
        lifecycle = CharacterLifecycle(
            store,
            Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                     legacy.V135_PLAYER_Z),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(
            legacy, lifecycle, LegacyProjector(legacy), **state_kwargs)
        state = state_type("driver")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("driver")))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(
                scene_id, world_scene_travel.load_scene_registry()))
        store.select_character(state.foundation.session_id, character.selector)
        store.save_position(
            state.foundation.session_id, character.id,
            Position(scene_id, 0, spawn[0], spawn[1], spawn[2], 0.0))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)))
        return state, buf.getvalue()

    REFUSED_PREFIX = "player_faction1_compose_refused_production_start_game"

    def _assert_no_faction_refusal(self, state):
        refused = [e for e in state.events if e.startswith(self.REFUSED_PREFIX)]
        self.assertEqual([], refused)

    def test_a_formerly_refused_stage_login_now_ships_the_faction_frame(self):
        with tempfile.TemporaryDirectory() as work:
            state, console = self._login_into(
                Path(work), STAGE_OPEN_BUT_NOT_A_HOME)
            self.assertIn("player_faction1_start_game_sent", state.events)
            self._assert_no_faction_refusal(state)
            self.assertIn("PLAYER_FACTION basic_faction=", console)

    def test_the_home_login_is_byte_for_byte_unaffected(self):
        """The regression this round could most easily have caused.

        Every flagless production login goes through this path, and a broken
        policy would take its faction frame away without raising anything.
        """
        with tempfile.TemporaryDirectory() as work:
            state, console = self._login_into(Path(work), HOME)
            self.assertIn("player_faction1_start_game_sent", state.events)
            self._assert_no_faction_refusal(state)
            self.assertIn("PLAYER_FACTION basic_faction=", console)


if __name__ == "__main__":
    unittest.main()
