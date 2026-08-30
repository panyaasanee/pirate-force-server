"""LANE-A's ChooseNPC responder for scene 14, and the gate that keeps it off.

COO-DECISION 20260830_0818 approved a ChooseNPC responder for roster scenes,
registered through ``lane_hooks`` the same way
``lane_hooks/lane_a_scene_census.py`` registers its census composer, with one
required test shape (COO's own words): drive the REAL dispatcher both ways --
"no responder = withhold stands, responder present = the NPC is actually
clickable/answerable".

WHY "RESPONDER PRESENT" IS NOT DRIVEN THROUGH ``state.dispatch()`` FOR THE
CLICK ITSELF, AND WHY THAT IS MEASURED HERE RATHER THAN ASSERTED IN PROSE.
Building this responder does not, on its own, make the frozen dispatcher
consult it: ``runtime.py``'s ``super().dispatch(parsed)`` is the ONLY thing
that answers a real ``ChooseNPC`` click today, unconditionally, before any
lane code runs, and its handler loops over the WHOLE of
``self.population_indices`` doing an unconditional
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``-keyed lookup for every one of them --
16 of scene 14's 81 composed indices have no row there.
``TheCrashThisModuleGuardsAgainstTests`` below arms real scene-14 membership
on the REAL dispatcher (by forcing ``lane_a_choose_npc_scene14``'s gate open
for that one test only) and drives a REAL ChooseNPC frame for an actor that
IS in the frozen table, through ``state.dispatch()`` itself -- and it still
raises ``KeyError``, because the loop touches every index, not just the one
clicked.  That is why ``lane_a_choose_npc_scene14.production_allowed`` is
``False`` by default (see that module's own docstring) and why
``TheResponderAnswersDirectlyTests`` below drives the responder's own
``respond()`` function directly, with the REAL armed ``population_indices``
and the REAL identities ``legacy.extract_choose_npc_identities`` pulls out
of a REAL ChooseNPC wire frame, rather than through ``state.dispatch()``:
the seam that would let ``state.dispatch()`` reach ``respond()`` instead of
the frozen loop is the CORE-REQUEST in this round's PR body, not yet landed.
Every OTHER piece here is real production code, not a double.
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

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_choose_npc_scene14 as responder_mod,
)
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_scene_census as lane_a,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
VOLCANO = 14
ROSTER_COUNT = 81
QUALIFIED_MODULE = (
    "pirateforce_foundation.lane_hooks.lane_a_choose_npc_scene14"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _target_pos_pc(legacy, xyz, heading=0.0, moving=0, derived=0):
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, derived)
    )


def _choose_npc_pc(legacy, *actor_ids):
    body = b"".join(
        legacy.u16tag(0x12, legacy.CHOOSE_NPC)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        for actor_id in actor_ids
    )
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, len(actor_ids))
        + body
    )


class ResponderRegistryTests(unittest.TestCase):
    """The registry point itself (mirrors
    ``test_lane_hooks.py::SceneCensusComposerRegistryTests``)."""

    SCENE = 999_902  # private test scene id, no real scene reaches here
    MODULE_A = "pirateforce_foundation.lane_hooks._test_choose_npc_module_a"

    def setUp(self):
        lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop(self.SCENE, None)
        self.addCleanup(
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop, self.SCENE, None,
        )

    def _register(self, module_name, fn=None):
        responder = fn or (lambda **kwargs: None)
        responder.__module__ = module_name
        return lane_hooks.choose_npc_responder(self.SCENE)(responder)

    def test_an_unclaimed_scene_answers_none(self):
        self.assertIsNone(lane_hooks.scene_choose_npc_responder(self.SCENE))

    def test_registration_is_looked_up_with_module_and_callable(self):
        def respond(**kwargs):
            return None

        self._register(self.MODULE_A, respond)
        entry = lane_hooks.scene_choose_npc_responder(self.SCENE)
        self.assertEqual(entry.module, self.MODULE_A)
        self.assertIs(entry.respond, respond)

    def test_registration_prints_the_registered_token_to_stderr(self):
        import io as _io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = _io.StringIO(), _io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self._register(self.MODULE_A)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("LANE_HOOK_REGISTERED", err.getvalue())
        self.assertIn(f"choose_npc_responder:{self.SCENE}", err.getvalue())

    def test_a_duplicate_registration_is_refused_and_the_first_kept(self):
        import io as _io
        from contextlib import redirect_stderr

        first = lambda **kwargs: None  # noqa: E731
        self._register(self.MODULE_A, first)
        with redirect_stderr(_io.StringIO()) as err:
            self._register(
                "pirateforce_foundation.lane_hooks._test_choose_npc_module_b",
            )
        entry = lane_hooks.scene_choose_npc_responder(self.SCENE)
        self.assertEqual(entry.module, self.MODULE_A)
        self.assertIs(entry.respond, first)
        self.assertIn("LANE_HOOK_DUPLICATE", err.getvalue())
        self.assertIn(f"KEPT {self.MODULE_A}", err.getvalue())

    def test_a_responder_from_outside_the_package_is_rejected_loudly(self):
        import io as _io
        from contextlib import redirect_stderr

        def respond(**kwargs):
            return None

        respond.__module__ = "pirateforce_foundation.gm.choose_npc_helper"
        with redirect_stderr(_io.StringIO()) as err:
            returned = lane_hooks.choose_npc_responder(self.SCENE)(respond)
        self.assertIsNone(lane_hooks.scene_choose_npc_responder(self.SCENE))
        self.assertIn("LANE_HOOK_REJECTED", err.getvalue())
        self.assertIn("NOT_A_LANE_HOOKS_MODULE", err.getvalue())
        self.assertIs(returned, respond)

    def test_withdraw_removes_a_modules_claim_and_frees_the_scene(self):
        self._register(self.MODULE_A)
        lane_hooks._withdraw(self.MODULE_A)
        self.assertIsNone(lane_hooks.scene_choose_npc_responder(self.SCENE))
        other = "pirateforce_foundation.lane_hooks._test_choose_npc_module_b"
        self._register(other)
        self.assertEqual(
            lane_hooks.scene_choose_npc_responder(self.SCENE).module, other,
        )


class TheResponderModuleGateIsClosedTests(unittest.TestCase):
    """``production_allowed = False`` today, and that is this round's own
    safety property, not an oversight -- see the module's docstring and
    ``TheCrashThisModuleGuardsAgainstTests`` below for the measurement that
    justifies it."""

    def test_the_real_module_declares_production_allowed_false(self):
        self.assertIs(responder_mod.production_allowed, False)

    def test_the_registered_responder_is_withdrawn_at_discovery(self):
        # _discover() already ran once for this process; the module's own
        # False flag means its registration was withdrawn immediately after
        # import, same mechanism test_lane_a_scene_census.py pins for a
        # closed census module.
        self.assertIsNone(lane_hooks.scene_choose_npc_responder(VOLCANO))
        self.assertFalse(
            lane_hooks.module_production_allowed(
                "lane_a_choose_npc_scene14",
            )
        )


class TheResponderAnswersDirectlyTests(unittest.TestCase):
    """``respond()`` driven directly, with real ``legacy`` and real bg0015
    data -- the half of "responder present = clickable" that does not
    require the still-missing runtime.py seam (see this file's own
    docstring)."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def test_a_real_click_on_an_actor_missing_from_bg0001_is_answered(self):
        """The exact 16-of-81 case R235 D2 measured as a guaranteed crash
        for the frozen handler: this module answers it cleanly instead."""
        legacy = self.legacy
        by_idx = {row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
        placements = responder_mod._placements_by_index()
        population_indices = tuple(sorted(placements))
        self.assertEqual(len(population_indices), ROSTER_COUNT)
        missing_from_bg0001 = [
            idx for idx in population_indices if idx not in by_idx
        ]
        self.assertTrue(
            missing_from_bg0001,
            "fixture drift: scene 14 no longer has a placement absent from "
            "bg0001, which was the whole reason this responder exists",
        )
        selected_idx = missing_from_bg0001[0]
        actor_identity = 0x2000 + selected_idx + 1
        parsed = legacy.parse_outer(_choose_npc_pc(legacy, actor_identity))
        chosen = legacy.extract_choose_npc_identities(parsed)
        self.assertEqual(chosen, [actor_identity])

        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=tuple(chosen),
            population_indices=population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_P{selected_idx}",
        )
        self.assertTrue(answer.pc)
        self.assertTrue(answer.frame)
        self.assertEqual(answer.delay, 0.0)
        self.assertEqual(len(answer.console_lines), 1)
        self.assertIn(
            f"placement={selected_idx}", answer.console_lines[0],
        )
        self.assertIn("visible=81", answer.console_lines[0])
        self.assertIn("omitted=0", answer.console_lines[0])
        # cp874-encodable, same discipline as every other lane console line.
        answer.console_lines[0].encode("cp874")

    def test_a_click_the_frozen_table_would_have_answered_is_also_answered(self):
        """The other 65 of 81: present in bg0001, but the wrong actor
        entirely if answered from that table (R235 D2's second defect).
        This module answers from scene 14's own table instead."""
        legacy = self.legacy
        by_idx = {row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
        placements = responder_mod._placements_by_index()
        population_indices = tuple(sorted(placements))
        present_in_bg0001 = [
            idx for idx in population_indices if idx in by_idx
        ]
        self.assertTrue(present_in_bg0001)
        selected_idx = present_in_bg0001[0]
        actor_identity = 0x2000 + selected_idx + 1
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)
        placement = placements[selected_idx]
        # The name in the answer must be scene 14's own actor, not Port
        # Royal's row at the same placement index.
        self.assertNotEqual(
            placement.display_name,
            world_port_royal_name := by_idx[selected_idx][-1],
        )

    def test_declines_for_an_identity_outside_population_indices(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + 5 + 1,),
            population_indices=(1, 2, 3),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)

    def test_declines_when_membership_is_not_armed(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + 1 + 1,),
            population_indices=None,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)

    def test_declines_when_the_scene_is_not_open_to_players(self):
        with tempfile.TemporaryDirectory() as work:
            legacy = self.legacy
            raw_registry = _shut_registry(Path(work))
            answer = responder_mod.respond(
                legacy=legacy,
                chosen_identities=(0x2000 + 1 + 1,),
                population_indices=(1,),
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                scene_entry_registry=raw_registry,
            )
            self.assertIsNone(answer)

    def test_declines_for_a_scene_other_than_14(self):
        legacy = self.legacy
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + 1 + 1,),
            population_indices=(1,),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=1,
        )
        self.assertIsNone(answer)

    def test_fails_closed_on_a_placement_this_scenes_own_table_lacks(self):
        """Never invent a row: an index in ``population_indices`` that
        this scene's OWN table (not bg0001) does not carry is skipped."""
        legacy = self.legacy
        bogus_idx = 999_999
        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(0x2000 + bogus_idx + 1,),
            population_indices=(bogus_idx,),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(answer)


def _shut_registry(work: Path):
    """A loaded registry with scene 14's door shut, temp file only (same
    technique as ``tests/test_lane_a_scene_census.py``'s own helper)."""
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] == VOLCANO:
            row["login_entry_allowed"] = False
    path = work / "registry_scene_14_shut.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path)


class OnTheRealDispatcherBothWaysTests(unittest.TestCase):
    """COO's own required shape: "ไม่มีตัวตอบ = withhold ยืน, มีตัวตอบ =
    คลิกได้จริง", driven on the REAL dispatcher for both halves of the
    census/membership side.  See this file's module docstring for why the
    CLICK itself is driven against ``respond()`` directly rather than
    ``state.dispatch()`` in the "responder present" case.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()

    def _armed_state(self, token):
        legacy = self.legacy
        lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(legacy, lifecycle, LegacyProjector(legacy))
        state = state_type(token)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc(token)))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(VOLCANO))
        self.store.select_character(
            state.foundation.session_id, character.selector)
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0))
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        with contextlib.redirect_stdout(io.StringIO()):
            actions = state.dispatch(legacy.parse_outer(
                _target_pos_pc(legacy, spawn)))
        return state, actions, spawn

    def test_no_responder_membership_withheld_stands(self):
        """TODAY'S SHIPPED STATE.  No responder is registered (the module's
        own ``production_allowed`` is False), so the composer's membership
        stays ``None`` and the three server-side fields are never armed --
        81 actors ship, none of them clickable, no crash."""
        state, actions, _spawn = self._armed_state("choose-npc-none")
        census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
        self.assertEqual(
            [a[0] for a in census],
            [f"WORLD_CENSUS_LANE_SCENE{VOLCANO}_INITIAL_{ROSTER_COUNT}",
             f"WORLD_CENSUS_LANE_SCENE{VOLCANO}_REAPPLY_{ROSTER_COUNT}"])
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.population_refresh_anchor)
        self.assertIsNone(state.world_census_indices)

    def test_responder_registered_and_allowed_membership_is_armed(self):
        """ONCE THE RESPONDER IS BOTH REGISTERED AND ALLOWED (forced here,
        test-only, to stand in for the day CORE-REQUEST's runtime.py guard
        lands and this lane flips the one line to True): the composer's own
        ``_membership_if_answerable`` gate opens and the REAL dispatcher
        arms all three fields from the seam's own membership, exactly as
        COO-DECISION 20260830_0818 asked."""
        lane_hooks.choose_npc_responder(VOLCANO)(responder_mod.respond)
        lane_hooks._PRODUCTION_ALLOWED[QUALIFIED_MODULE] = True
        self.addCleanup(
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop, VOLCANO, None,
        )
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__,
            QUALIFIED_MODULE, False,
        )

        state, actions, spawn = self._armed_state("choose-npc-armed")
        census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
        self.assertEqual(len(census), 2)
        self.assertIsNotNone(state.population_indices)
        self.assertEqual(len(state.population_indices), ROSTER_COUNT)
        self.assertEqual(
            state.world_census_indices, state.population_indices,
        )
        self.assertEqual(
            state.population_refresh_anchor,
            tuple(float(v) for v in spawn),
        )
        self.assertIn(
            f"world_census_lane_membership_set_{ROSTER_COUNT}",
            state.events,
        )

        # THE CLICK HALF: real armed population_indices, a real ChooseNPC
        # frame, real extraction -- fed straight to respond() rather than
        # through state.dispatch() (see this file's module docstring).
        legacy = self.legacy
        by_idx = {
            row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }
        missing_from_bg0001 = [
            idx for idx in state.population_indices if idx not in by_idx
        ]
        self.assertTrue(missing_from_bg0001)
        selected_idx = missing_from_bg0001[0]
        actor_identity = 0x2000 + selected_idx + 1
        parsed = legacy.parse_outer(_choose_npc_pc(legacy, actor_identity))
        chosen = legacy.extract_choose_npc_identities(parsed)

        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=tuple(chosen),
            population_indices=state.population_indices,
            last_target_pos=state.last_target_pos,
        )
        self.assertIsNotNone(
            answer, "an armed, present actor must be answerable",
        )
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_P{selected_idx}",
        )
        self.assertTrue(answer.pc)
        self.assertTrue(answer.frame)


class TheCrashThisModuleGuardsAgainstTests(unittest.TestCase):
    """MEASURED, NOT ASSERTED: what happens on the REAL dispatcher if
    membership is armed for scene 14 with no runtime.py guard in front of
    the frozen ChooseNPC handler -- the exact reason
    ``lane_a_choose_npc_scene14.production_allowed`` is ``False`` and the
    exact reason ``_membership_if_answerable`` reads that flag before
    arming anything.  Forces the gate open for this ONE test, restores it
    on cleanup, and proves the CORE-REQUEST in this round's PR body is not
    a hypothetical.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        lane_hooks.choose_npc_responder(VOLCANO)(responder_mod.respond)
        lane_hooks._PRODUCTION_ALLOWED[QUALIFIED_MODULE] = True
        self.addCleanup(
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop, VOLCANO, None,
        )
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__,
            QUALIFIED_MODULE, False,
        )

    def test_a_real_click_still_crashes_the_real_dispatcher_today(self):
        legacy = self.legacy
        lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        state_type = make_state_class(legacy, lifecycle, LegacyProjector(legacy))
        state = state_type("choose-npc-crash-proof")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("choose-npc-crash-proof")))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(VOLCANO))
        self.store.select_character(
            state.foundation.session_id, character.selector)
        self.store.save_position(
            state.foundation.session_id, character.id,
            Position(VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0))
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(character.selector)))
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(legacy.parse_outer(_target_pos_pc(legacy, spawn)))
        self.assertIsNotNone(state.population_indices)

        by_idx = {
            row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }
        # Even a placement PRESENT in bg0001 crashes: v141's
        # make_v98_conversation_face_state loops over the WHOLE of
        # population_indices, not only the clicked one.
        present_idx = next(
            idx for idx in state.population_indices if idx in by_idx
        )
        actor_identity = 0x2000 + present_idx + 1
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyError):
                state.dispatch(legacy.parse_outer(
                    _choose_npc_pc(legacy, actor_identity)))


if __name__ == "__main__":
    unittest.main()
