"""LANE-A's ChooseNPC responder for scene 14, on by default as of round
`n8fq3w`.

COO-DECISION 20260830_0818 approved a ChooseNPC responder for roster scenes,
registered through ``lane_hooks`` the same way
``lane_hooks/lane_a_scene_census.py`` registers its census composer, with one
required test shape (COO's own words): drive the REAL dispatcher both ways --
"no responder = withhold stands, responder present = the NPC is actually
clickable/answerable".

THE runtime.py SEAM HAS LANDED (chief, round `hd6tac`/R237, answering this
lane's `20260830_0909` CORE-REQUEST) -- THE PARAGRAPH BELOW DESCRIBES THE
STATE BEFORE IT, KEPT FOR WHY THE GATE STILL MATTERS.  Before this round,
``runtime.py``'s ``super().dispatch(parsed)`` was the ONLY thing that
answered a real ``ChooseNPC`` click, unconditionally, before any lane code
ran, and its handler loops over the WHOLE of ``self.population_indices``
doing an unconditional ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS``-keyed lookup
for every one of them -- 16 of scene 14's 81 composed indices have no row
there.  ``runtime.py`` now checks, ahead of that inherited call, whether the
session's current scene has a REGISTERED and ALLOWED
``lane_hooks.scene_choose_npc_responder``, and if so answers through it
INSTEAD of ever running the frozen loop for that frame --
``TheGuardAnsweredTheClickInsteadOfCrashingTests`` below proves it, on the
REAL dispatcher (the gate was forced open for that one class only between
round `hd6tac` and round `n8fq3w`; round `n8fq3w` flipped the module's own
default instead, so that class no longer needs to force anything -- see
its own docstring for that history, kept rather than pretending the crash
was never measured under a forced gate).

``lane_a_choose_npc_scene14.production_allowed`` FLIPPED TO ``True`` in
LANE-A round `n8fq3w` -- the seam existing on `main` for one full round
(`e2q8c6`, zero-diff) with this line still unflipped is what that round's
own account calls out as the single highest-leverage unblock nobody had
acted on yet; this round is that action.  See that module's own docstring
for the full reasoning and the two gaps shipped with it, pinned rather than
fixed.  ``TheResponderAnswersDirectlyTests`` below still drives
the responder's own ``respond()`` function directly (real armed
``population_indices``, real identities via
``legacy.extract_choose_npc_identities``) because that is the fastest,
narrowest way to pin the responder's OWN logic without also depending on
``runtime.py``'s guard existing -- both are exercised in this file now, at
different layers, and neither replaces the other.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_hostile_bg0015  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
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


def _target_vital_pc(legacy, actor_id, kind=0):
    """One bare TARGET_VITAL frame (v141's `parse_target_vital` shape) --
    no ChooseNPC record attached, so `extract_choose_npc_identities` finds
    no identity in it and only v141's own arming side effect
    (`action_target_last_identity` et al., v141:3788-3811) is at stake."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_VITAL)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        + legacy.u8tag(0x08, kind)
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


class TheResponderModuleGateIsOpenTests(unittest.TestCase):
    """``production_allowed = True`` as of LANE-A round `n8fq3w`, flipped
    once the runtime.py guard this file's own CORE-REQUEST asked for landed
    on `main` (chief, round `hd6tac`/R237) -- see the module's docstring and
    ``TheGuardAnsweredTheClickInsteadOfCrashingTests`` below for the
    measurement that makes this safe.  RENAMED from
    ``TheResponderModuleGateIsClosedTests``, kept in history rather than
    deleted: this class asserted the opposite of both methods below from
    this module's creation until this round."""

    def test_the_real_module_declares_production_allowed_true(self):
        self.assertIs(responder_mod.production_allowed, True)

    def test_the_registered_responder_is_registered_at_discovery(self):
        # _discover() already ran once for this process; the module's own
        # True flag means its registration stood after import, same
        # mechanism test_lane_a_scene_census.py pins for an open census
        # module.
        entry = lane_hooks.scene_choose_npc_responder(VOLCANO)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.module, QUALIFIED_MODULE)
        self.assertTrue(
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


class AClickPreservesTheHostileSpliceTests(unittest.TestCase):
    """Regression coverage for ``pf_bridge/notes_to_chief/20260831_2318_
    CHIEF-TO-LANE-A-choosenpc-scene14-reverts-hostile-splice-to-civilian.md``
    (CONFIRMED defect, chief's own mutation-tested pf-adversary run, round
    R274): before LANE-A round `yfbqmg`'s fix, clicking ANY actor in scene
    14 rebuilt every ``NPCAttr`` through the civilian encoder alone --
    ``respond()`` always rebuilds all 81 entries around the one clicked, so
    the 12 placements ``world_population_handoff._roster_handoff`` splices
    hostile on arrival silently reverted to plain civilians on the wire on
    the very first click, whether or not the clicked actor was one of the
    12.  This class clicks an UNRELATED (non-hostile) actor on purpose, so
    a regression shows up purely in the other 80 rebuilt entries, not in
    the clicked one's own movement bytes.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def test_a_click_on_an_unrelated_actor_still_carries_the_hostile_bodies(
        self,
    ):
        legacy = self.legacy
        placements = responder_mod._placements_by_index()
        population_indices = tuple(sorted(placements))
        hostile_indices = set(
            field_mob_hostile_bg0015.DEFAULT_HOSTILE_PLACEMENT_INDICES
        )
        self.assertTrue(hostile_indices.issubset(set(population_indices)))

        selected_idx = next(
            idx for idx in population_indices if idx not in hostile_indices
        )
        actor_identity = 0x2000 + selected_idx + 1

        answer = responder_mod.respond(
            legacy=legacy,
            chosen_identities=(actor_identity,),
            population_indices=population_indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
        )
        self.assertIsNotNone(answer)

        hostile_roster = {
            mob.placement_index: mob
            for mob in field_mob_hostile_bg0015.scene14_hostile_roster()
        }
        checked = 0
        # (hostile_roster is the MINED twelve on purpose -- the withheld
        # assertion at the end of this method needs the row it is about.)
        for idx in hostile_indices:
            mob = hostile_roster[idx]
            placement = placements[idx]
            hostile_body = field_mobs.hostile_npc_attr(
                legacy, mob, current_hp=mob.max_hp,
                scene_id=responder_mod.SCENE_N_ID, scene_sequence=0,
            )
            civilian_body = legacy.make_npc_attr(
                placement.n_id, placement.actor_identity,
                responder_mod.SCENE_N_ID, 0, placement.visual_preset,
                current_hp=placement.max_hp, max_hp=placement.max_hp,
                basic_name=placement.display_name,
            )
            self.assertIn(
                hostile_body, answer.pc,
                f"placement {idx}'s hostile NPCAttr body is missing from "
                "the click response -- the hostile splice was reverted",
            )
            if civilian_body != hostile_body:
                self.assertNotIn(
                    civilian_body, answer.pc,
                    f"placement {idx}'s CIVILIAN NPCAttr body is present "
                    "in the click response -- the hostile splice was "
                    "reverted",
                )
            checked += 1
        # ~~12~~ DERIVED, ROUND j5v7mu (edited by LANE-B, whose ruling moved
        # it -- this file is LANE-A's and the loop above is unchanged).
        # COO-DECISION 20260905_0545 withheld Bg0015 placement 87 from what
        # LANE-B ships, so DEFAULT_HOSTILE_PLACEMENT_INDICES is eleven.  The
        # count is read off the same tuple the loop walks so this line can
        # never again disagree with it, and the two numbers below say what
        # the tuple must actually be, so "the tuple went empty" still fails.
        self.assertEqual(checked, len(hostile_indices))
        self.assertEqual(checked, 11)
        # AND THE WITHHELD ROW IS MEASURED ON THE REAL RESPONDER PATH, not
        # merely absent from a count: his hostile body must NOT be in the
        # click answer, while he is still one of scene 14's actors.
        for withheld_idx in field_mobs.lane_withheld_placements("Bg0015"):
            self.assertIn(withheld_idx, population_indices)
            self.assertNotIn(withheld_idx, hostile_indices)
            withheld_mob = hostile_roster[withheld_idx]
            withheld_hostile_body = field_mobs.hostile_npc_attr(
                legacy, withheld_mob, current_hp=withheld_mob.max_hp,
                scene_id=responder_mod.SCENE_N_ID, scene_sequence=0,
            )
            self.assertNotIn(withheld_hostile_body, answer.pc)


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
        """REGRESSION COVERAGE FOR A STATE THIS PROCESS NO LONGER SHIPS BY
        DEFAULT.  Until LANE-A round `n8fq3w`, this was "today's shipped
        state" with no forcing at all; the module's own ``production_allowed``
        is now ``True`` by default (see ``TheResponderModuleGateIsOpenTests``),
        so the withhold path is driven here by forcing the registry back to
        empty for this one test -- the same shape ``test_lane_a_scene_census.
        py`` uses to prove its own admission check, not a new technique.  The
        property this test still pins: IF a scene had no registered/allowed
        responder, the three server-side fields would stay unarmed and 81
        actors would still ship with none of them clickable, no crash --
        the composer's fail-safe default, still exercised even though scene
        14 itself no longer takes this branch."""
        with mock.patch.dict(lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS):
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop(VOLCANO, None)
            with mock.patch.dict(
                lane_hooks._PRODUCTION_ALLOWED, {QUALIFIED_MODULE: False},
            ):
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
        """TODAY'S SHIPPED STATE, LANE-A round `n8fq3w` onward.  No forcing:
        the module's own ``production_allowed`` is ``True`` by default, so
        the composer's own ``_membership_if_answerable`` gate is open and
        the REAL dispatcher arms all three fields from the seam's own
        membership on an ordinary boot, exactly as COO-DECISION 20260830_0818
        asked.  RENAMED IN PLACE, kept forcing out of this test's own setup
        (previously forced ``lane_hooks._PRODUCTION_ALLOWED`` True with an
        ``addCleanup`` back to False, standing in for a flip that had not
        happened yet -- that flip is what this round did)."""
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


class TheGuardAnsweredTheClickInsteadOfCrashingTests(unittest.TestCase):
    """MEASURED, NOT ASSERTED: what happens on the REAL dispatcher, now that
    ``runtime.py`` (chief, round `hd6tac`/R237) checks
    ``lane_hooks.scene_choose_npc_responder`` ahead of the inherited
    ``super().dispatch(parsed)`` call.

    RENAMED FROM ``TheCrashThisModuleGuardsAgainstTests``, kept in this
    file's history rather than deleted: before round `hd6tac`, this exact
    test -- same fixture, same clicked actor -- asserted
    ``self.assertRaises(KeyError)``, and that assertion was true right up
    until the guard landed (see the CHIEF-REPLY-shaped comment in
    ``runtime.py`` at the call site for why the inherited branch's crash was
    never a hypothetical: it looped over the WHOLE of
    ``self.population_indices``, not only the clicked actor, so 16 of scene
    14's 81 composed indices missing from
    ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` doomed the FIRST click on ANY of
    the 81, not just the missing ones).  ``lane_a_choose_npc_scene14.
    production_allowed`` was forced ``True`` here and ONLY here between
    round `hd6tac` and round `n8fq3w`, while the module's own default was
    still ``False``; LANE-A round `n8fq3w` flipped that default itself, so
    the forcing this class used to do in ``setUp`` is gone -- these tests
    now exercise the real shipped default, the same simplification
    ``OnTheRealDispatcherBothWaysTests.
    test_responder_registered_and_allowed_membership_is_armed`` made above.
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
        # No forcing needed as of round `n8fq3w`: the module's own
        # ``production_allowed`` is ``True`` by default, so
        # ``lane_hooks.scene_choose_npc_responder(VOLCANO)`` already names
        # this responder from ``_discover()``'s own import-time pass.

    def _armed_state_on_scene_14(self, token):
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
            state.dispatch(legacy.parse_outer(_target_pos_pc(legacy, spawn)))
        self.assertIsNotNone(state.population_indices)
        return state

    def test_a_real_click_is_answered_instead_of_crashing_the_dispatcher(
        self,
    ):
        legacy = self.legacy
        state = self._armed_state_on_scene_14("choose-npc-crash-proof")

        by_idx = {
            row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }
        # A placement PRESENT in bg0001 -- before the guard, this crashed
        # too, because the inherited loop touched every index, not just the
        # one clicked.  The guard now answers it directly and the inherited
        # branch never runs for this frame at all.
        present_idx = next(
            idx for idx in state.population_indices if idx in by_idx
        )
        actor_identity = 0x2000 + present_idx + 1
        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                actions = state.dispatch(legacy.parse_outer(
                    _choose_npc_pc(legacy, actor_identity)))
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0][0],
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_P{present_idx}",
        )
        self.assertTrue(actions[0][1])
        self.assertTrue(actions[0][2])
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertIn(
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_ANSWERED", err.getvalue(),
        )

        # AND A MISSING PLACEMENT -- the one the inherited branch could
        # never have survived at all -- is answered too, not merely spared.
        missing_idx = next(
            idx for idx in state.population_indices if idx not in by_idx
        )
        missing_identity = 0x2000 + missing_idx + 1
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            missing_actions = state.dispatch(legacy.parse_outer(
                _choose_npc_pc(legacy, missing_identity)))
        self.assertEqual(len(missing_actions), 1)
        self.assertEqual(
            missing_actions[0][0],
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_P{missing_idx}",
        )

    def test_a_multi_select_click_answers_only_the_first_identity(self):
        """MEASURED GAP (pf-adversary, round `hd6tac`), pinned rather than
        fixed: the frozen path answers EVERY distinct identity a multi-select
        ChooseNPC frame names (v141:4408, one frame each), but every
        registered responder returns at most one `ChooseNpcResponse` per
        call -- built to try each named identity until ONE answers, not to
        answer all of them.  A claimed scene therefore degrades a
        multi-select click to a single answer instead of sending several.
        This test exists to catch that gap getting SILENTLY WORSE (e.g.
        zero answers instead of one), not to prove it acceptable -- see the
        runtime.py guard's own comment for why it is not fixed in this
        round.
        """
        state = self._armed_state_on_scene_14("choose-npc-multi-select")
        by_idx = {
            row[0]: row for row in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        }
        # Index 1 is `columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX` --
        # an entirely unrelated, already-wired additive branch
        # (`_dispatch_columbus_quest3021`) answers a click naming Columbus's
        # own actor identity regardless of scene, appending a SECOND action
        # this test is not about.  Excluded here so the count below isolates
        # this guard's own behaviour, not a coincidence of shared index
        # numbering between two unrelated features (measured: without this
        # exclusion the "first two present indices" on this fixture are 0
        # and 1, and 1 IS Columbus's).
        present = [
            idx for idx in state.population_indices
            if idx in by_idx and idx != 1
        ]
        self.assertGreaterEqual(len(present), 2)
        first_identity = 0x2000 + present[0] + 1
        second_identity = 0x2000 + present[1] + 1
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _choose_npc_pc(self.legacy, first_identity, second_identity)
            ))
        # The frozen dispatcher would have answered BOTH (two actions); the
        # claimed-scene guard answers only the first-tried identity.
        face_actions = [
            a for a in actions
            if a[0].startswith(f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_")
        ]
        self.assertEqual(len(face_actions), 1)
        self.assertEqual(
            face_actions[0][0],
            f"LANE_A_CHOOSE_NPC_SCENE{VOLCANO}_FACE_P{present[0]}",
        )

    def test_claiming_a_target_vital_frame_skips_v141s_own_arming(self):
        """MEASURED GAP (pf-adversary, round `hd6tac`), pinned rather than
        fixed: v141:3788-3811 unconditionally arms
        `action_target_last_identity` / `_last_kind` / `p30_action_target_
        armed` on every TARGET_VITAL frame, read later by its own
        ACTION_VITAL handling.  A claimed scene never calls
        `super().dispatch(parsed)` at all for that frame, so this arming
        never happens.  Harmless for scene 14 today only because
        `exact_p30_target`'s strict match wants an arena-harness identity
        this scene's real actors do not have -- INCIDENTAL, not designed
        for.  See the runtime.py guard's own comment for the full warning
        any future scene must read before flipping its own
        `production_allowed`.
        """
        state = self._armed_state_on_scene_14("choose-npc-target-vital-arm")
        self.assertIsNone(state.action_target_last_identity)
        self.assertFalse(state.p30_action_target_armed)
        present_identity = 0x2000 + state.population_indices[0] + 1
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                _target_vital_pc(self.legacy, present_identity)
            ))
        # The frozen path would have set this to `present_identity`
        # (v141:3799); the claimed scene's guard never reaches that code.
        self.assertIsNone(state.action_target_last_identity)
        self.assertFalse(state.p30_action_target_armed)

    def test_a_click_the_responder_declines_sends_no_bytes_and_is_named(
        self,
    ):
        """An identity outside `population_indices` gets no honest answer
        (the responder's own fail-closed rule) -- the guard's job is only to
        route to the responder, not to invent a frame when it declines."""
        state = self._armed_state_on_scene_14("choose-npc-declined")
        outside_identity = 0x2000 + max(state.population_indices) + 1000
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _choose_npc_pc(self.legacy, outside_identity)))
        self.assertEqual(actions, [])
        self.assertIn("scene_choose_npc_responder_declined", state.events)

    def test_a_raising_responder_does_not_break_the_connection(self):
        """fail-closed at the guard's call site, not only inside the
        responder's own try/except -- the same shape
        tests/test_gm_chat_command_dispatch_wiring.py pins for the GM chat
        route."""
        state = self._armed_state_on_scene_14("choose-npc-raises")
        present_identity = 0x2000 + state.population_indices[0] + 1

        def _boom(*_args, **_kwargs):
            raise RuntimeError("responder is broken")

        # The registry stores the FUNCTION OBJECT at registration time
        # (`ChooseNpcResponder(module_name, fn)`), not a live attribute
        # lookup on `responder_mod` -- so the raising double has to replace
        # the registry entry itself, the same way `setUp` installed the
        # real one.
        with mock.patch.dict(
            lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS,
            {VOLCANO: lane_hooks.ChooseNpcResponder(QUALIFIED_MODULE, _boom)},
        ):
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                actions = state.dispatch(self.legacy.parse_outer(
                    _choose_npc_pc(self.legacy, present_identity)))
                # The connection survives and keeps serving later frames.
                later = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc(
                        "choose-npc-raises"
                    )
                ))
        self.assertEqual(actions, [])
        self.assertIn(
            "scene_choose_npc_responder_failed_RuntimeError", state.events,
        )
        self.assertIsInstance(later, list)


class TheLedgerReachesSceneFourteenTooTests(unittest.TestCase):
    """``COO-DECISION 20260902_1945``: both production responders move in
    ONE commit.

    Until round `4uztfj` this responder swallowed ``mob_combat_ledger`` in
    ``**_ignored`` and composed every hostile body at ``max_hp``, while
    scene 2's responder read the same keyword -- so the day the call site
    started passing it, two production scenes would have answered
    differently on the same input (chief's letter ``20260902_1918`` item
    4.2, measured).  These drive the rule, not the wiring: ~~the call site
    still passes nothing today~~ -- CORRECTED ROUND ``qa86im``: the call
    site has passed ``mob_combat_ledger=`` since ``server#619`` (R313), and
    what it still passes nothing for is ``mob_death_register=``, which this
    round's own tests supply by hand for the same reason.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        # ROUND j5v7mu (LANE-B edit): the SHIPPED roster, because that is
        # what respond() now reads -- a fixture built from the mined twelve
        # would make this class assert a ledger the live path never opens.
        cls.hostile = {
            mob.placement_index: mob
            for mob in field_mob_hostile_bg0015.scene14_shipped_hostile_roster()
        }
        cls.placements = responder_mod._placements_by_index()
        cls.population_indices = tuple(sorted(cls.placements))
        cls.dead_index = sorted(cls.hostile)[0]
        cls.civilian_index = next(
            idx for idx in cls.population_indices if idx not in cls.hostile
        )

    def _ledger(self, identity, current_hp):
        """A REAL, scene-tagged ledger -- not a duck type.

        pf-adversary D4 (round `4uztfj`) is why: the responders now admit a
        ledger for their own scene through ``mob_ledger_admission`` before
        reading it, because scenes 2 and 14 share identity ``0x2058`` and a
        stale ledger from the other scene dropped a live click.  A stand-in
        object is refused by that admission, so a test that used one would
        assert the ledger-less path while claiming to test the ledger one.
        """
        # THIS SCENE'S OWN ROSTER SOURCE, measured: ``field_mobs`` names
        # no scene 14 at all, so its roster helper answers an EMPTY tuple
        # and a ledger opened from it holds no row for these identities.
        roster = tuple(
            field_mob_hostile_bg0015.scene14_shipped_hostile_roster())
        ledger = mob_combat.open_ledger(roster)
        self.assertEqual(ledger.scene, responder_mod.SCENE_FOLDER)
        row = ledger.balance_of(identity)
        return ledger.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, current_hp))

    def _register(self, mob):
        """A REAL, scene-keyed ``DeathRegister`` holding this mob's grave.

        Typed for the same reason ``_ledger`` is: ``corpse_body_for``
        refuses anything that is not a ``mob_death.DeathRegister``, so a
        stand-in would silently assert the register-less path.
        """
        return mob_death.DeathRegister((
            mob_death.DeathRecord(
                actor_identity=mob.actor_identity,
                killer_identity=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY,
                max_hp=mob.max_hp,
                scene=mob.scene,
            ),
        ), 1)

    def _click(self, index, ledger, register=None):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            answer = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(0x2000 + index + 1,),
                population_indices=self.population_indices,
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                mob_combat_ledger=ledger,
                mob_death_register=register,
            )
        return answer, err.getvalue()

    def test_no_ledger_still_sends_every_hostile_body_at_its_ceiling(self):
        answer, _err = self._click(self.civilian_index, None)
        self.assertIsNotNone(answer)
        self.assertIn("hp=ceiling", answer.console_lines[0])
        self.assertIn("wounded=0", answer.console_lines[0])
        self.assertIn("dead_at_ceiling=0", answer.console_lines[0])

    def test_a_wounded_monster_keeps_its_wound_and_is_counted(self):
        mob = self.hostile[self.dead_index]
        wounded_hp = max(1, mob.max_hp - 1)
        answer, _err = self._click(
            self.civilian_index,
            self._ledger(mob.actor_identity, wounded_hp))
        self.assertIsNotNone(answer)
        self.assertIn("wounded=1", answer.console_lines[0])
        self.assertIn(
            field_mobs.hostile_npc_attr(
                self.legacy, mob, current_hp=wounded_hp,
                scene_id=14, scene_sequence=0,
            ),
            answer.frame,
        )

    def test_a_kill_elsewhere_does_not_silence_a_click_on_a_civilian(self):
        mob = self.hostile[self.dead_index]
        answer, err = self._click(
            self.civilian_index, self._ledger(mob.actor_identity, 0))
        self.assertIsNotNone(
            answer, "a dead monster silenced a click on someone else")
        self.assertIn("dead_at_ceiling=1", answer.console_lines[0])
        self.assertIn(
            f"_DEAD_BODY_AT_CEILING count=1 placements={self.dead_index} "
            f"identities=0x{mob.actor_identity:04X}",
            err)

    def test_clicking_the_dead_body_is_refused_by_its_own_placement(self):
        mob = self.hostile[self.dead_index]
        answer, err = self._click(
            self.dead_index, self._ledger(mob.actor_identity, 0))
        self.assertIsNone(answer)
        self.assertIn(
            "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_mob_"
            f"death_body placement={self.dead_index} identity=0x", err)

    def test_the_register_answers_the_click_on_a_corpse_with_a_body(self):
        """``COO-DECISION 20260903_0252``, scene 14's half of the commit."""
        mob = self.hostile[self.dead_index]
        answer, err = self._click(
            self.dead_index, self._ledger(mob.actor_identity, 0),
            self._register(mob))
        self.assertIsNotNone(
            answer, "a click on a corpse was still answered with silence")
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE14_CORPSE_P{self.dead_index}")
        self.assertIn("dead_as_corpse=1", answer.console_lines[0])
        self.assertIn("dead_at_ceiling=0", answer.console_lines[0])
        self.assertIn("_CLICKED_BODY_IS_A_CORPSE reason=answered_with_a_"
                      f"corpse_body_not_a_facing placement={self.dead_index}",
                      err)
        self.assertNotIn("_IDENTITY_REFUSED", err)

    def test_the_body_in_that_frame_is_the_death_composers_own_bytes(self):
        mob = self.hostile[self.dead_index]
        answer, _err = self._click(
            self.civilian_index, self._ledger(mob.actor_identity, 0),
            self._register(mob))
        self.assertIn(
            mob_death.corpse_npc_attr(
                self.legacy, mob,
                death_timer=mob_death.DEAD_TIMER_SECONDS,
                scene_id=14, scene_sequence=0),
            answer.frame,
            "the corpse in this frame is not the composer's body",
        )
        self.assertNotIn(
            field_mobs.hostile_npc_attr(
                self.legacy, mob, current_hp=mob.max_hp,
                scene_id=14, scene_sequence=0),
            answer.frame,
            "the dead monster was re-sent standing at its ceiling",
        )
        self.assertIn("dead_as_corpse=1", answer.console_lines[0])

    def test_another_scenes_grave_cannot_bury_this_scenes_body(self):
        """The register is scene-keyed, and this is what that BUYS."""
        mob = self.hostile[self.dead_index]
        foreign = mob_death.DeathRegister((
            mob_death.DeathRecord(
                actor_identity=mob.actor_identity,
                killer_identity=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY,
                max_hp=mob.max_hp,
                scene="Bg0002",
            ),
        ), 1)
        answer, err = self._click(
            self.dead_index, self._ledger(mob.actor_identity, 0), foreign)
        self.assertIsNone(
            answer,
            "a kill in another scene composed a corpse in this one",
        )
        self.assertIn("clicked_body_is_dead_needs_a_mob_death_body", err)

    def test_a_packet_naming_a_corpse_AND_a_civilian_is_still_answered(self):
        """The multi-identity packet, driven here too (pf-adversary D1):
        turning this responder's per-identity ``continue`` into a ``return``
        left the whole lane suite green before this test existed."""
        mob = self.hostile[self.dead_index]
        ledger = self._ledger(mob.actor_identity, 0)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            answer = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(
                    0x2000 + self.dead_index + 1,
                    0x2000 + self.civilian_index + 1,
                ),
                population_indices=self.population_indices,
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                mob_combat_ledger=ledger,
            )
        printed = err.getvalue()
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE14_FACE_P{self.civilian_index}")
        self.assertNotIn("_DECLINED", printed)
        self.assertIn("_IDENTITY_REFUSED", printed)

    def test_a_corpse_is_not_counted_as_a_wound_or_a_ledger_read(self):
        mob = self.hostile[self.dead_index]
        answer, _err = self._click(
            self.civilian_index, self._ledger(mob.actor_identity, 0))
        line = answer.console_lines[0]
        self.assertIn("wounded=0", line)
        self.assertIn("dead_at_ceiling=1", line)
        self.assertIn(f"from_ledger={len(self.hostile) - 1}", line)

    def test_a_ledger_from_the_other_scene_is_refused_by_name(self):
        """The same collision scene 2's suite pins from its own side.

        ROUND j5v7mu (LANE-B edit).  THE COLLISION IS GONE FROM THE LIVE
        SETS and that is a real consequence of COO-DECISION 20260905_0545,
        not a bookkeeping detail: 0x2058 was the ONLY identity Bg0002's and
        Bg0015's live rosters shared, and placement 87 is the withheld row.
        The admission mechanism this test is named for is unchanged and is
        still worth pinning, so the subject is taken from the MINED roster
        (which still carries him) and the new fact is asserted first rather
        than left for a later round to discover as a silent skip.
        """
        from pirateforce_foundation import field_mobs as fm
        scene2_roster = fm.roster_for_scene_id(2)
        scene2_identities = {mob.actor_identity for mob in scene2_roster}
        self.assertEqual(
            scene2_identities & {
                mob.actor_identity for mob in self.hostile.values()},
            set(),
            "scene 2 and scene 14's LIVE rosters share an identity again",
        )
        mined = {
            mob.placement_index: mob
            for mob in field_mob_hostile_bg0015.scene14_hostile_roster()
        }
        shared = scene2_identities & {
            mob.actor_identity for mob in mined.values()}
        self.assertTrue(shared, "the collision this test is about is gone")
        identity = sorted(shared)[0]
        foreign = mob_combat.open_ledger(scene2_roster)
        row = foreign.balance_of(identity)
        foreign = foreign.with_balance(
            mob_combat.MobBalance(identity, row.max_hp, 0))
        clicked = next(
            index for index, mob in mined.items()
            if mob.actor_identity == identity
        )
        answer, err = self._click(clicked, foreign)
        self.assertIsNotNone(answer)
        self.assertIn("hp=ceiling", answer.console_lines[0])
        self.assertIn("_LEDGER_NOT_ADMITTED", err)

    def test_the_two_responders_answer_the_same_way_on_the_same_input(self):
        """The property the ruling is actually about: not that either
        answer is right, but that they cannot diverge again.

        ~~an inspection of ``respond.__code__.co_varnames``~~ REPLACED,
        pf-adversary D8: that version proved the keyword was NAMED, not
        that either scene READ it -- the exact shape of test this file's
        own scar list warns about.  This one drives BOTH responders with
        the same three ledger states and compares the behaviour."""
        from pirateforce_foundation import field_mobs as fm
        from pirateforce_foundation.lane_hooks import (
            lane_a_choose_npc_scene2 as scene2,
        )
        from pirateforce_foundation import (
            scene2_prison_exile_tables as scene2_tables,
        )

        scene2_hostile = scene2._hostile_mobs_by_placement_index()
        scene2_dead_index = sorted(scene2_hostile)[0]
        scene2_mob = scene2_hostile[scene2_dead_index]
        scene2_civilian = next(
            index for index in sorted(
                p.placement_index
                for p in scene2_tables.load_known_placements())
            if index not in scene2_hostile
        )
        scene2_roster = fm.roster_for_scene_id(2)

        def scene2_ledger(current_hp):
            ledger = mob_combat.open_ledger(scene2_roster)
            row = ledger.balance_of(scene2_mob.actor_identity)
            return ledger.with_balance(mob_combat.MobBalance(
                scene2_mob.actor_identity, row.max_hp, current_hp))

        mob14 = self.hostile[self.dead_index]
        cases = {
            "dead": (0, "dead_at_ceiling=1"),
            "wounded": (max(1, mob14.max_hp - 1), "wounded=1"),
        }
        for name, (_hp, marker) in cases.items():
            with self.subTest(case=name):
                hp14 = 0 if name == "dead" else max(1, mob14.max_hp - 1)
                hp2 = 0 if name == "dead" else max(
                    1, scene2_mob.max_hp - 1)
                answer14, err14 = self._click(
                    self.civilian_index,
                    self._ledger(mob14.actor_identity, hp14))
                with contextlib.redirect_stderr(io.StringIO()) as err2:
                    answer2 = scene2.respond(
                        legacy=self.legacy,
                        chosen_identities=(0x2000 + scene2_civilian + 1,),
                        population_indices=None,
                        last_target_pos=(1.0, 2.0, 0.0, 0.0),
                        scene_id=2,
                        mob_combat_ledger=scene2_ledger(hp2),
                    )
                self.assertIsNotNone(answer14)
                self.assertIsNotNone(answer2)
                # Both answer, both carry the same marker, and neither
                # calls an answered click a refusal.
                self.assertIn(marker, answer14.console_lines[0])
                self.assertIn(marker, answer2.console_lines[0])
                self.assertNotIn("_DECLINED", err14)
                self.assertNotIn("_DECLINED", err2.getvalue())

        # And the corpse click itself: both refuse the IDENTITY, not the
        # packet, and both name the placement that was clicked.
        _dead14, err14 = self._click(
            self.dead_index, self._ledger(mob14.actor_identity, 0))
        with contextlib.redirect_stderr(io.StringIO()) as err2:
            dead2 = scene2.respond(
                legacy=self.legacy,
                chosen_identities=(0x2000 + scene2_dead_index + 1,),
                population_indices=None,
                last_target_pos=(1.0, 2.0, 0.0, 0.0),
                scene_id=2,
                mob_combat_ledger=scene2_ledger(0),
            )
        self.assertIsNone(_dead14)
        self.assertIsNone(dead2)
        for printed, index in (
            (err14, self.dead_index), (err2.getvalue(), scene2_dead_index),
        ):
            with self.subTest(printed=printed[:40]):
                self.assertIn(
                    "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_"
                    f"mob_death_body placement={index} identity=0x", printed)


if __name__ == "__main__":
    unittest.main()
