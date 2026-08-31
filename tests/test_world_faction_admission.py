"""LANE-A: defect D3 -- which scenes a player's faction-1 field reaches.

WHAT THIS FILE PROVES.  ``player_wire``'s faction-1 serializer used to hold a
literal ``scene_id not in (1, 2)``, so a login into any other scene shipped
the plain ``ActorAttr`` and ``runtime.py`` latched ``player_faction1_compose_
refused_production_start_game``.  ``HYP-PF-027`` measured that hostility
renders from a faction PAIR, so on the one scene with a composed cast the
symptom was 81 monsters that could not read as hostile.  Round vvy6q7 replaced
that literal with ``world_faction_admission``, under the blast radius
``COO-DECISION 20260829_2342`` wrote out: scenes the registry declares open at
login AND ``n_SAVE`` 1.

THE TWO THINGS THAT WOULD MAKE THIS ROUND A REGRESSION, DRIVEN FIRST.  A
policy that WIDENS a wire is only as good as the two ways it can be wrong, and
both are asserted here rather than argued in a docstring:

* IT MUST NEVER SUBTRACT.  If this policy ever refuses scene 1, every flagless
  production login loses its faction frame and NOTHING GOES RED -- the runtime
  catches the refusal and latches an event.  ``TheProvenFloorTests`` drives
  that with a registry that will not load at all.
* IT MUST NOT ADMIT A SCENE ON ONE CONDITION.  ``login_entry_allowed`` alone
  would have admitted scenes 278 and 997, two stages that are open at login
  and carry ``n_SAVE`` 0.  ``TheTwoConditionsTests`` drives each condition
  failing on its own.

NEGATIVE CONTROLS, BECAUSE THIS LANE HAS SHIPPED A TAUTOLOGY BEFORE.
pf-adversary caught this lane (round drrnpu, D4) writing tests that passed
against two fake modules, one of which held its own copy of the answer.  So
the serializer tests here do not merely check that scene 14 works today: they
build a registry in a temp file with scene 14's door SHUT, and require the
serializer to refuse again.  A ``world_faction_admission`` that had quietly
grown a literal ``14`` would pass every other test in this file and fail that
one.

GATE-WALK DECLARATION (``COO-DECISION 20260829_0742``).

WALKED:

* The predicate, on the real registry file this repository ships.
* Both conditions, each failed on its own, on registries built in temp files.
* Fail-closed on: an unloadable registry, a registry object of the wrong
  type, a scene id absent from the registry, a non-int scene id, a bool.
* The real serializer ``runtime.py``'s production path calls, admitted and
  refused, with the refusal driven by a SHUT temp registry rather than by a
  scene nobody wants.
* The frozen ``GT-032`` serializer, asserted STILL frozen at ``(1, 2)``.
* The production dispatcher end to end: a login into scene 14 with no flags,
  and the ``PLAYER_FACTION`` line that used to be absent.

NOT WALKED, AND SAID PLAINLY:

* NO CLAIM THAT THE FACTION PAIR RENDERS AS HOSTILE IN SCENE 14.  Nobody has
  stood in scene 14.  The wire carrying a field is not the client drawing
  anything, and ``GT-134`` is the attended ticket that looks.  ACCEPTED IS
  NOT REACHED.
* No claim about the faction VALUE.  Only 1 is admitted, unchanged.
* The ten other marker scenes are not exercised beyond being refused; they
  have no composed cast for the field to matter to.
"""
from __future__ import annotations

import contextlib
import io
import json
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
# ADDED round bq4mst (LANE-A): opened the same round this constant was added.
SLAVE_MARKET = 4
# ADDED round 3t75jw (LANE-A): opened the same round this constant was added,
# second of the ten doors -- carries an elevated landing-geometry flag
# (registry's own the_two_interiors) this file does not track; see GT-166.
DEEP_SEA_TEMPLE = 10
# Open at login and n_SAVE 0: the stage that proves the second condition is
# doing work rather than decorating the sentence.
STAGE_OPEN_BUT_NOT_A_HOME = 278
# Pinned, shut at login: one of the ten marker scenes round ga91m5 addressed.
SHUT_AT_LOGIN = 3


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _registry_with_door(work: Path, scene_id: int, allowed: bool):
    """A loaded registry whose ``scene_id`` row is open/shut.  Temp file only.

    Never the repository's file.  This is how every negative control here is
    built: the point is to move the registry and watch the policy follow it,
    which is the one thing a policy holding a private literal cannot do.
    """
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] == scene_id:
            row["login_entry_allowed"] = bool(allowed)
    path = work / f"registry_{scene_id}_{'open' if allowed else 'shut'}.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path), path


def _registry_with_save_flag(work: Path, scene_id: int, n_save: int):
    """A loaded registry whose ``scene_id`` row carries ``n_save``."""
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] == scene_id:
            row["table_row"]["n_SAVE"] = n_save
    path = work / f"registry_{scene_id}_nsave_{n_save}.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path), path


class ThePredicateOnTheRealRegistryTests(unittest.TestCase):
    """What the file on main answers today."""

    def test_the_admitted_set_is_exactly_the_two_proven_scenes_and_the_volcano(
            self):
        # ADDED round bq4mst: scene 4 (SLAVE_MARKET) opened this round
        # (COO-DECISION 20260830_1441) and carries n_SAVE 1, so the DERIVED
        # set now includes it -- this is the file's own point, that the set
        # follows the registry rather than a list somebody wrote once.
        # UPDATED round 3t75jw: scene 10 (DEEP_SEA_TEMPLE) opened second,
        # same basis, and also carries n_SAVE 1.
        self.assertEqual(
            (HOME, SCENE_2, SLAVE_MARKET, DEEP_SEA_TEMPLE, VOLCANO),
            wfa.admitted_scene_ids())

    def test_each_admitted_scene_says_yes_one_at_a_time(self):
        for scene_id in (HOME, SCENE_2, SLAVE_MARKET, DEEP_SEA_TEMPLE,
                          VOLCANO):
            with self.subTest(scene_id=scene_id):
                self.assertTrue(wfa.admits(scene_id))

    def test_a_scene_shut_at_login_is_refused_and_says_which_condition(self):
        self.assertFalse(wfa.admits(SHUT_AT_LOGIN))
        self.assertIn("not_open_at_login", wfa.refusal_reason(SHUT_AT_LOGIN))

    def test_the_console_line_carries_the_whole_set_and_the_rule(self):
        """THE ONLY MUTANT THAT SURVIVED THIS ROUND'S BATTERY LIVED HERE.

        pf-adversary (D3) replaced this function's body with a hardcoded
        ``ids = (1, 2, 14)`` and the ENTIRE SUITE STAYED GREEN, because this
        test asserted the literal string "scenes=1,2,14" -- which a hardcoded
        answer satisfies perfectly.  A stale pin, inside the one function
        whose whole purpose is to not be one.

        Fixed by asserting against the DERIVED set instead of a literal, and
        by driving a registry the derivation must follow.  A hardcoded
        ``console_line`` now fails both halves.
        """
        line = wfa.console_line()
        expected = ",".join(str(i) for i in wfa.admitted_scene_ids())
        self.assertIn(f"WORLD_FACTION_ADMISSION scenes={expected}", line)
        self.assertIn("n_save_1", line)
        # cp874 is the bridge console's codepage; a line it cannot encode is
        # a line nobody can grep on the machine that runs the server.
        line.encode("ascii")
        line.encode("cp874")

    def test_the_console_line_follows_a_registry_that_moves(self):
        # The half a literal cannot fake: hand it a registry with another
        # door open and the printed set has to change.
        # UPDATED round 3t75jw: the base registry this opens ON TOP OF now
        # already admits scene 10 (DEEP_SEA_TEMPLE), so the expected string
        # grew a digit that is not the one this test opens.
        with tempfile.TemporaryDirectory() as work:
            opened, _ = _registry_with_door(
                Path(work), SHUT_AT_LOGIN, allowed=True)
            line = wfa.console_line(opened)
            self.assertIn(
                f"WORLD_FACTION_ADMISSION scenes=1,2,{SHUT_AT_LOGIN},4,"
                f"{DEEP_SEA_TEMPLE},14",
                line)
            self.assertNotIn(f"scenes=1,2,4,{DEEP_SEA_TEMPLE},14 ", line)


class TheTwoConditionsTests(unittest.TestCase):
    """Each half of the COO's blast radius, failed on its own.

    Both are driven by MOVING THE REGISTRY, never by picking a scene that
    happens to answer the right way -- a test that only ever asks about
    scene 278 cannot tell a policy from a lookup table.
    """

    def setUp(self) -> None:
        self._work = tempfile.TemporaryDirectory()
        self.addCleanup(self._work.cleanup)
        self.work = Path(self._work.name)

    def test_open_at_login_alone_does_not_admit_a_scene_with_n_save_zero(self):
        # 278 is open at login on the real registry today and still refused.
        self.assertTrue(
            world_scene_travel.destination(
                STAGE_OPEN_BUT_NOT_A_HOME).login_entry_allowed)
        self.assertFalse(wfa.admits(STAGE_OPEN_BUT_NOT_A_HOME))
        self.assertIn(
            "n_save_is_0_not_1",
            wfa.refusal_reason(STAGE_OPEN_BUT_NOT_A_HOME))

    def test_n_save_one_alone_does_not_admit_a_scene_shut_at_login(self):
        # Scene 3 carries n_SAVE 1 already; only the door is shut.
        self.assertEqual(
            1, world_scene_travel.destination(SHUT_AT_LOGIN).save_flag)
        self.assertFalse(wfa.admits(SHUT_AT_LOGIN))

    def test_shutting_the_volcano_door_takes_the_admission_back(self):
        shut, _ = _registry_with_door(self.work, VOLCANO, allowed=False)
        self.assertFalse(wfa.admits(VOLCANO, shut))
        self.assertNotIn(VOLCANO, wfa.admitted_scene_ids(shut))

    def test_opening_a_shut_door_admits_that_scene_without_a_code_change(self):
        """The policy follows the registry, which is the whole design.

        If this fails, ``admits`` has grown a private list of scene ids and
        the registry has stopped being the gate.
        """
        opened, _ = _registry_with_door(self.work, SHUT_AT_LOGIN, allowed=True)
        self.assertTrue(wfa.admits(SHUT_AT_LOGIN, opened))
        self.assertIn(SHUT_AT_LOGIN, wfa.admitted_scene_ids(opened))

    def test_dropping_n_save_takes_the_admission_back_too(self):
        bent, _ = _registry_with_save_flag(self.work, VOLCANO, 0)
        self.assertFalse(wfa.admits(VOLCANO, bent))
        self.assertIn("n_save_is_0_not_1", wfa.refusal_reason(VOLCANO, bent))


class TheProvenFloorTests(unittest.TestCase):
    """GT-032's two scenes, which this policy may never take away.

    THE FAILURE THIS GUARDS IS SILENT.  ``runtime.py`` catches the
    serializer's refusal and latches ``player_faction1_compose_refused_
    production_start_game``; it does not raise, and no test outside this file
    watches that event on the home path.  A policy that broke and refused
    scene 1 would ship a server whose every login quietly lost its faction
    frame, and the suite would stay green.
    """

    def test_home_and_scene_two_survive_a_registry_that_will_not_load(self):
        broken = object()
        for scene_id in wfa.PROVEN_FACTION_SCENE_IDS:
            with self.subTest(scene_id=scene_id):
                self.assertTrue(wfa.admits(scene_id, broken))

    def test_home_survives_a_registry_whose_row_says_shut(self):
        with tempfile.TemporaryDirectory() as work:
            shut, _ = _registry_with_door(Path(work), HOME, allowed=False)
            self.assertTrue(wfa.admits(HOME, shut))

    def test_the_floor_is_still_the_two_scenes_gt032_proved(self):
        self.assertEqual((1, 2), wfa.PROVEN_FACTION_SCENE_IDS)

    def test_an_unloadable_registry_yields_the_floor_and_nothing_more(self):
        self.assertEqual(
            wfa.PROVEN_FACTION_SCENE_IDS, wfa.admitted_scene_ids(object()))


class FailClosedTests(unittest.TestCase):
    """Everything that is not an explicit yes is a no, and none of it raises.

    A refusal returns the server to the behaviour of every boot before this
    module existed, so a refusal is always safe.  A traceback out of a
    serializer during login is not.
    """

    def test_a_scene_absent_from_the_registry_is_refused(self):
        self.assertFalse(wfa.admits(999999))
        self.assertIn("not_readable_from_registry", wfa.refusal_reason(999999))

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

    def test_a_registry_object_of_the_wrong_type_is_refused_not_raised(self):
        self.assertFalse(wfa.admits(VOLCANO, object()))
        self.assertIn(
            "not_readable_from_registry", wfa.refusal_reason(VOLCANO, object()))

    def test_the_reporter_never_raises_for_anything_admits_answers(self):
        for value in (1, 14, 3, 999999, "x", None, True, -1, 0):
            with self.subTest(value=repr(value)):
                self.assertIsInstance(wfa.refusal_reason(value), str)


class TheSerializerTests(unittest.TestCase):
    """The wire, not the predicate: what ``runtime.py`` actually calls."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _compose(self, scene_id):
        return player_wire.make_actor_attr_with_name_class_and_faction(
            self.legacy, 1, 0, scene_id, 0, "driver", 1)

    def test_the_volcano_now_serializes_a_faction_field(self):
        wire = self._compose(VOLCANO)
        self.assertIsInstance(wire, bytes)
        self.assertGreater(len(wire), 0)

    def test_the_faction_field_costs_the_same_five_bytes_it_always_did(self):
        """The delta ``runtime.py``'s own drift guard checks, at scene 14.

        If this ever differs from 5, ``runtime.py`` refuses the recompose as
        length drift and the frame is dropped -- so a wider faction field
        would present as "no faction line" rather than as a bad one.
        """
        plain = player_wire.make_actor_attr_with_name_and_class(
            self.legacy, 1, 0, VOLCANO, 0, "driver")
        self.assertEqual(len(self._compose(VOLCANO)) - len(plain), 5)

    def test_a_scene_shut_at_login_is_still_refused_by_the_serializer(self):
        with self.assertRaises(ValueError) as caught:
            self._compose(SHUT_AT_LOGIN)
        self.assertIn("not_open_at_login", str(caught.exception))

    def test_a_stage_with_n_save_zero_is_still_refused_by_the_serializer(self):
        with self.assertRaises(ValueError) as caught:
            self._compose(STAGE_OPEN_BUT_NOT_A_HOME)
        self.assertIn("n_save", str(caught.exception))

    def test_the_faction_value_and_scene_seq_are_as_frozen_as_ever(self):
        for kwargs in ({"basic_faction": 6}, {"scene_seq": 1}):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError) as caught:
                    player_wire.make_actor_attr_with_name_class_and_faction(
                        self.legacy, 1, 0, VOLCANO,
                        kwargs.get("scene_seq", 0), "driver",
                        kwargs.get("basic_faction", 1))
                # The message must name the condition that REFUSED.  A
                # mutation run this round produced "faction-1 is refused:
                # faction_admitted_scene_14_..." -- a self-contradicting
                # sentence that sends the reader to the registry to debug a
                # value the registry has no opinion about.
                message = str(caught.exception)
                self.assertNotIn("faction_admitted_scene", message)
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

    def test_the_negative_control_a_shut_volcano_refuses_the_wire_again(self):
        """THE CONTROL THAT KILLS THE TAUTOLOGY.

        Everything above would still pass if ``world_faction_admission`` held
        a literal ``14``.  This points the module's loader at a registry whose
        scene-14 door is shut and requires the serializer to refuse: only a
        policy that really reads the registry can do that.
        """
        with tempfile.TemporaryDirectory() as work:
            _, patched = _registry_with_door(Path(work), VOLCANO, allowed=False)
            real_loader = world_scene_travel.load_scene_registry
            world_scene_travel.load_scene_registry = (
                lambda *a, _f=real_loader, _p=patched, **k: _f(_p))
            self.addCleanup(
                setattr, world_scene_travel, "load_scene_registry",
                real_loader)
            # THE CACHE IS PER PROCESS, SO A LOADER PATCH ALONE NO LONGER
            # REACHES THIS MODULE -- which is the entire point of the cache
            # (D2: this policy must read the same age of the world as every
            # other reader, not re-read the file per login).  Dropping it
            # here is how a test simulates a fresh BOOT against a different
            # registry, and the cleanup drops it again so no later test
            # inherits this one's view.
            wfa.forget_cached_registry()
            self.addCleanup(wfa.forget_cached_registry)
            with self.assertRaises(ValueError) as caught:
                self._compose(VOLCANO)
            self.assertIn("not_open_at_login", str(caught.exception))
            # ...and home is untouched by the same shut registry.
            self.assertIsInstance(self._compose(HOME), bytes)


class OnTheRealDispatcherTests(unittest.TestCase):
    """The end of D3, driven on a boot with no flags at all.

    This is the pair to ``tests/test_lane_a_scene_census.py``'s dispatcher
    test: that one proves 81 actors reach the player, this one proves the
    player carries the faction field those actors are meant to pair against.
    Neither proves anything renders -- ``GT-134`` is the eyes.
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

    # THE REFUSAL EVENT IS A PREFIX, NOT A WHOLE STRING, AND ASSERTING THE
    # WHOLE STRING IS AN ASSERTION THAT CANNOT FAIL.  pf-adversary caught
    # this round writing ``assertNotIn("player_faction1_compose_refused_
    # production_start_game", state.events)`` (D8): runtime.py:6385 latches
    # the event with the exception repr appended --
    # ``..._start_game_ValueError('faction-1 is refused: ...')`` -- so exact
    # list membership NEVER matches and the assertion passed whether or not
    # the faction had been refused.  Both of the tests below were among the
    # round's headline evidence.  Matched by prefix now, and a test asserts
    # the prefix itself still appears on a real refusal, so this cannot rot
    # back into a tautology if the event name changes.
    REFUSED_PREFIX = "player_faction1_compose_refused_production_start_game"

    def _assert_no_faction_refusal(self, state):
        refused = [e for e in state.events if e.startswith(self.REFUSED_PREFIX)]
        self.assertEqual([], refused)

    def test_a_scene_14_login_now_ships_the_player_faction_frame(self):
        with tempfile.TemporaryDirectory() as work:
            state, console = self._login_into(Path(work), VOLCANO)
            self.assertTrue(state.teleport_sent)
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

    def test_the_refusal_prefix_really_is_what_a_refused_login_latches(self):
        """The control that keeps the two tests above from going vacuous.

        If ``runtime.py`` ever renames the event, the two ``_assert_no_
        faction_refusal`` calls would start passing for the wrong reason --
        exactly the defect D8 named.  So drive a REAL refusal and require the
        prefix to show up, on a scene the policy refuses.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            _, patched = _registry_with_door(work, VOLCANO, allowed=False)
            real_loader = world_scene_travel.load_scene_registry
            world_scene_travel.load_scene_registry = (
                lambda *a, _f=real_loader, _p=patched, **k: _f(_p))
            self.addCleanup(
                setattr, world_scene_travel, "load_scene_registry",
                real_loader)
            wfa.forget_cached_registry()
            self.addCleanup(wfa.forget_cached_registry)
            # Scene 278 is pinned, open at login, and refused by n_SAVE - so
            # the login itself succeeds and only the FACTION is refused,
            # which is the exact state the prefix has to be able to name.
            state, _ = self._login_into(work, STAGE_OPEN_BUT_NOT_A_HOME)
            refused = [
                e for e in state.events if e.startswith(self.REFUSED_PREFIX)]
            self.assertEqual(1, len(refused), state.events)
            self.assertIn("n_save", refused[0])


class TheOptInBootHazardTests(unittest.TestCase):
    """CLOSED 2026-08-30 by ``scene_admission_gate`` -- history kept, not deleted.

    THIS CLASS USED TO ASSERT BEHAVIOUR THIS LANE CONSIDERED WRONG.  It was
    added because pf-adversary (round vvy6q7, D1) measured that opening
    scene 14's door made a bad path REACHABLE that the shut door had been
    holding closed, and because the only thing standing in front of it was a
    paragraph in a ticket header in ANOTHER REPOSITORY, which depends on a
    human reading it.

    THE MECHANISM THAT MADE IT WRONG.  ``runtime.py``'s
    ``world_census_enabled`` is
    ``(not active_lanes and second_password_mode == "required")``.  That one
    expression is BOTH the guard on the per-scene lane census AND the
    (former) sole disarm of the inherited ``v141:4292`` dispatcher.  So on
    any opt-in boot -- a ``--*-scenario`` flag, or
    ``--second-password-mode bypass`` -- the lane census never fired and the
    inherited branch stayed armed, composing three bg0001 PORT ROYAL
    placements with NO SCENE TEST AT ALL, wherever travel had actually put
    the session.

    WHY IT SHIPPED ANYWAY AT THE TIME, AND WHO DECIDED.  COO-DECISION
    20260829_2342 opened scene 14's door with the flag ban as its
    condition 1, and that ruling was the authority, not this lane's
    preference.  The code-level guard was named as the chief's job in
    COO-DECISION 20260829_0941 item 2 and reaffirmed in COO-DECISION
    20260830_0817 (deadline 2026-08-30T12:00+07:00).

    THE CLOSE.  ``scene_admission_gate.strip_frozen_legacy_population``,
    wired into ``runtime.py`` right after ``super().dispatch()`` this same
    round, drops every ``V134_P0_P30_P91_ISOLATED_*`` action whenever the
    session's current scene is not ``world_population.SCENE_ID`` (home) --
    regardless of which opt-in lane left the inherited branch armed.  A
    session that never leaves scene 1 is untouched (see
    ``test_scene_admission_gate.py``'s CONTAINMENT-preserving control test);
    a session travelled to the volcano no longer gets Port Royal's actors.
    ``test_the_wrong_islands_actors_are_what_ships_instead`` below is kept,
    inverted, as the regression proof -- the hazard reproduction it used to
    assert is now what it asserts CANNOT happen.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _opt_in_login_into_the_volcano(self, work: Path):
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
            legacy, lifecycle, LegacyProjector(legacy),
            second_password_mode="bypass",
        )
        state = state_type("driver")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("driver")))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[-1]
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(
                VOLCANO, world_scene_travel.load_scene_registry()))
        store.select_character(state.foundation.session_id, character.selector)
        store.save_position(
            state.foundation.session_id, character.id,
            Position(VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)))
        return state, buf.getvalue()

    def test_an_opt_in_boot_reaches_scene_14_now_and_the_census_does_not(self):
        """The door lets the login through; the census is disarmed with it."""
        with tempfile.TemporaryDirectory() as work:
            state, console = self._opt_in_login_into_the_volcano(Path(work))
            self.assertTrue(state.teleport_sent)
            # ...and the scene's own census is NOT what ships.
            self.assertNotIn("WORLD_CENSUS_BG0015", console)
            self.assertNotIn("world_census_armed", state.events)

    def test_the_wrong_islands_actors_are_what_ships_instead(self):
        """CLOSED 2026-08-30 -- was defect D1 (Port Royal on the volcano).

        Three bg0001 placement indices used to compose with no scene test,
        anchored on Hell Volcano Island: a tester on this boot would see
        three bodies and no BG0015 line, exactly the false FAIL GT-134's
        hard precondition exists to prevent.  ``scene_admission_gate`` now
        WITHHOLDS them whenever the row this session carries names a scene
        other than ``world_population.SCENE_ID``.

        Withheld, not stripped, and this test asserts both halves.  An
        earlier version of the fix dropped the two frames but left
        ``population_indices`` latched at ``(0, 30, 91)``, and pf-adversary
        measured what that bought: the ChooseNPC answerer reads that very
        field as its evidence the client has the actor, so a click still
        drew a full position/heading frame for a Port Royal placement at
        volcano coordinates, and the trade window still opened.  The frozen
        branch still RUNS unmodified (v141 is pinned); what changed is that
        the state it latched is rolled back with the frames.
        """
        with tempfile.TemporaryDirectory() as work:
            state, _ = self._opt_in_login_into_the_volcano(Path(work))
            state.runtime_ack_sent = True
            state.welcome_message_sent = True
            state.current_scene_music_sent = True
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(VOLCANO))
            pc = (
                self.legacy.u16tag(
                    0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
                + self.legacy.u32tag(0x14, 0)
                + self.legacy.u8tag(0x08, 0)
                + self.legacy.u8tag(0x0B, 2)
                + self.legacy.u16tag(0x12, 1)
                + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
                + self.legacy.u8tag(0x0B, 0)
                + b"".join(
                    self.legacy.f32tag(v) for v in (*spawn, 0.0))
                + self.legacy.u8tag(0x0B, 0)
                + self.legacy.u8tag(0x0B, 0)
            )
            with contextlib.redirect_stdout(io.StringIO()):
                actions = state.dispatch(self.legacy.parse_outer(pc))
            labels = [a[0] for a in actions]
            self.assertFalse(
                any("V134_P0_P30_P91_ISOLATED" in label for label in labels),
                f"the scene admission gate should have stripped these; "
                f"got {labels}",
            )
            self.assertFalse(
                [lbl for lbl in labels if lbl.startswith("WORLD_CENSUS_LANE")])
            # ...and nothing downstream is left believing the client has
            # them.  This is the assertion that would have caught the
            # half-fix: it read (0, 30, 91) when the frames were merely
            # stripped.
            self.assertIsNone(state.population_indices)
            self.assertIs(state.npc_spawn_sent, False)
            self.assertIn(
                "frozen_legacy_population_withheld_scene_"
                f"{VOLCANO}", state.events,
            )

    def test_the_faction_frame_still_ships_which_is_the_confusing_part(self):
        """The faction policy does NOT depend on the census, and says so.

        A tester on a wrongly-flagged boot sees PLAYER_FACTION and three
        Port Royal NPCs, and could read the faction line as confirmation
        that the scene is working.  It is not.  This is pinned because it is
        the exact misreading GT-134's precondition has to survive, and
        because the PLAYER_FACTION console token carries no scene id
        (pf-adversary D4) so it cannot be told apart from a Port Royal login
        by grep alone.
        """
        with tempfile.TemporaryDirectory() as work:
            state, console = self._opt_in_login_into_the_volcano(Path(work))
            self.assertIn("PLAYER_FACTION basic_faction=", console)
            self.assertIn("player_faction1_start_game_sent", state.events)


if __name__ == "__main__":
    unittest.main()
