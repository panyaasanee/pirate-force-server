"""LANE-E: the three CORE-REQUEST 20260906_2318 keywords at the ChooseNPC
call site, and the scene-scoping that keeps them from reaching a scene they
were never written for.

WHY A FAKE RESPONDER, REPRODUCING THE SWAP TECHNIQUE
``tests/test_choose_npc_call_site_ledger.py`` ALREADY USES FOR ITS OWN
``test_a_malformed_extra_actions_does_not_kill_the_dispatch_thread``, RATHER
THAN A REAL CLICK ON A REAL SCENE.  ``runtime.py``'s respond() call now
passes ``runtime_ack_sent``, ``exact_frozen_marker1_ready_pc`` and
``world_census_identity_resolved`` (lane A's letter ``20260906_2318``,
``WORLD_CENSUS_IDENTITY_RESOLVED_WIRING`` and
``FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING`` in
``lane_hooks/lane_a_choose_npc_scene1.py``).  What this file needs to prove
is the CALL SITE's own new logic -- that it passes the three keywords
through, and that a decline explained by one of them reroutes to the frozen
loop under a distinct event -- not scene 1's own already-tested decline
branches (``tests/test_lane_a_choose_npc_scene1.py`` covers those by calling
``respond()`` directly).  A fake, registered under scene 1's REAL module
name so the call site's scene-scoping check treats it as scene 1, removes
every dependency on Port Royal's census/population machinery actually
composing a real answer, which is a fragile multi-frame harness this file
does not need to carry to make its point.

THE DEFECT THIS FILE GUARDS WAS REAL, MEASURED IN THIS ROUND, NOT
HYPOTHESISED: an earlier draft of the call-site patch computed the fallback
flag correctly but nested the FIRST call-site edit's ``if chosen_identities:``
block (the one that calls ``respond()`` at all) one level too deep, inside a
scene-1-only guard.  Every OTHER registered responder (scene 2, scene 14,
the roster scenes) stopped being called entirely -- ``state.dispatch`` fell
through to ``actions = []`` for every ChooseNPC click in the game, silently,
with ``scene_choose_npc_responder_declined`` and nothing else on the
console.  ``tests/test_lane_a_choose_npc_scene14.py`` and
``tests/test_choose_npc_call_site_ledger.py`` caught it (both went red)
before this round's patch reached a commit -- full suite run, not a guess.
This file's second test pins the shape that made it visible directly,
without relying on those two files continuing to exercise scene 1's kwargs
as a side effect of testing scene 2/14's own features.

A THIRD DEFECT, ALSO REAL AND ALSO MEASURED, WAS CAUGHT BY PF-ADVERSARY
(round `lk97bl`, reviewing this exact patch) AFTER THE FIRST TWO TESTS
BELOW WERE ALREADY GREEN: ``frozen_fallback_guard_declined`` was computed
from session-global state BEFORE ``respond()`` ran and never revisited
based on what ``respond()`` actually did, so an UNRELATED bug raising
inside ``respond()`` (never reaching any of the three guards) was
silently relabelled as a guard decline whenever the session happened to
also be pre-ack or census-unresolved -- rerouting a real failure into the
frozen loop this whole call site exists to avoid running for a claimed
scene, instead of the safe zero-byte decline every other exception at
this call site gets.  The third test below reproduces exactly that shape
and would have caught it; it is the reason ``response is not None`` is
tested for explicitly rather than trusted to correlate with "no
exception happened".
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

from pirateforce_foundation import lane_hooks                      # noqa: E402
from pirateforce_foundation.legacy_bridge import (                  # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle     # noqa: E402
from pirateforce_foundation.model import Position                   # noqa: E402
from pirateforce_foundation.runtime import make_state_class         # noqa: E402
from pirateforce_foundation.store import SQLiteStore                # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENE1_MODULE = "pirateforce_foundation.lane_hooks.lane_a_choose_npc_scene1"
OTHER_MODULE = "pirateforce_foundation.lane_hooks.fake_other_scene_responder"
ARBITRARY_ACTOR_IDENTITY = 0x2000 + 1


def _legacy():
    return load_legacy(LEGACY_PATH)


class TheThreeGuardsFallBackWithoutLeakingToAnotherSceneTests(
    unittest.TestCase
):
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

    # ---- harness, reproduced from test_choose_npc_call_site_ledger.py ----

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions, out.getvalue() + err.getvalue()

    def _state(self, token):
        state_type = make_state_class(self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        self.assertEqual(
            state.foundation.selected.position.scene_id, 1,
            "a fresh session must start in scene 1 for this file's swap "
            "to register under the right key",
        )
        return state

    def _choose_npc_pc(self, actor_identity):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.CHOOSE_NPC)
            + legacy.u8tag(0x0B, 0)
            + legacy.qwordtag(0x32, actor_identity)
        )

    def _swap_scene1_responder(self, module_name, fn):
        """Register ``fn`` as scene 1's responder under ``module_name``,
        production-allowed, for the life of one test -- the same
        registry-swap technique
        test_choose_npc_call_site_ledger.py::
        test_a_malformed_extra_actions_does_not_kill_the_dispatch_thread
        already uses, restored via ``addCleanup``."""
        original_entry = lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.get(1)
        original_allowed = lane_hooks._PRODUCTION_ALLOWED.get(module_name)

        def _restore():
            if original_entry is None:
                lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS.pop(1, None)
            else:
                lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS[1] = original_entry
            if original_allowed is None:
                lane_hooks._PRODUCTION_ALLOWED.pop(module_name, None)
            else:
                lane_hooks._PRODUCTION_ALLOWED[module_name] = original_allowed

        self.addCleanup(_restore)
        lane_hooks._SCENE_CHOOSE_NPC_RESPONDERS[1] = lane_hooks.ChooseNpcResponder(
            module_name, fn,
        )
        lane_hooks._PRODUCTION_ALLOWED[module_name] = True

    # ---- the pins ---------------------------------------------------

    def test_the_call_site_passes_the_three_keywords_and_reroutes_on_decline(
        self,
    ) -> None:
        """WORLD_CENSUS_IDENTITY_RESOLVED_WIRING and
        FROZEN_TARGET_VITAL_BEHAVIOUR_WIRING, measured through a real
        dispatch against scene 1's OWN registered module name: a decline
        this call site attributes to one of the three new keywords must
        fall back to the frozen loop, under a distinct event, and the
        keywords it read must be the session's real values -- not a
        fake's guess."""
        captured = {}

        def _declining_respond(**kwargs):
            captured.update(kwargs)
            return None

        self._swap_scene1_responder(SCENE1_MODULE, _declining_respond)
        state = self._state("tok_census_false")
        state.world_census_identity_resolved = False
        actions, _console = self._dispatch(
            state, self._choose_npc_pc(ARBITRARY_ACTOR_IDENTITY),
        )
        self.assertEqual(
            captured.get("world_census_identity_resolved"), False,
            "the call site must read the session's real "
            "world_census_identity_resolved, not omit the keyword",
        )
        self.assertIn("runtime_ack_sent", captured)
        self.assertIn("exact_frozen_marker1_ready_pc", captured)
        # NOT claimed: that `actions` is non-empty here.  This session
        # never walked, so `population_indices` is still `None` and the
        # frozen loop this falls back to has nothing to compose for an
        # arbitrary identity either -- measured, `actions == []` on THIS
        # harness even on the fallback path.  What this test can and does
        # prove is which branch ran: the distinct event below fires only
        # from the `elif frozen_fallback_guard_declined:` branch, never
        # from the ordinary `else` a few lines under it, so its presence
        # (and the plain token's absence) is the call site actually
        # having taken `actions = super().dispatch(parsed)` rather than
        # `actions = []` outright -- the real, letter-mandated fix, on a
        # harness a real Port Royal population would only make more
        # expensive to build, not more true.
        self.assertIn(
            "scene_choose_npc_responder_declined_frozen_fallback",
            state.events,
        )
        self.assertNotIn("scene_choose_npc_responder_declined", state.events)

    def test_the_new_guards_do_not_reach_a_different_scenes_responder(
        self,
    ) -> None:
        """Regression guard for the defect this file's module docstring
        names.  A responder registered under a DIFFERENT module name that
        declines for reasons of its own must get the ORDINARY decline
        (zero bytes, the plain event), never the scene-1 guards' fallback
        token -- even when the two session-global attributes those guards
        read happen to be set exactly the way they would be for a real
        scene-1 decline.  Before this round's fix, the call site computed
        this flag from the session's attributes alone, with no module
        check at all: a coincidental match here would have rerouted an
        UNRELATED scene's decline into the frozen loop instead of
        answering (or truthfully declining) on its own terms."""
        def _declining_respond(**_ignored):
            return None

        self._swap_scene1_responder(OTHER_MODULE, _declining_respond)
        state = self._state("tok_other_module")
        state.world_census_identity_resolved = False
        state.runtime_ack_sent = False
        actions, _console = self._dispatch(
            state, self._choose_npc_pc(ARBITRARY_ACTOR_IDENTITY),
        )
        self.assertEqual(
            actions, [],
            "a decline from a responder that is not scene 1's own module "
            "must stay the ordinary zero-byte decline",
        )
        self.assertIn("scene_choose_npc_responder_declined", state.events)
        self.assertNotIn(
            "scene_choose_npc_responder_declined_frozen_fallback",
            state.events,
            "the scene-1 guards' fallback token must never fire for a "
            "different module's decline, however the session's global "
            "attributes happen to be set",
        )

    def test_an_unrelated_exception_is_never_relabelled_as_a_guard_decline(
        self,
    ) -> None:
        """pf-adversary, round `lk97bl`, on this exact patch: a bug in
        scene 1's own respond() that has nothing to do with any of the
        three guards (it never reaches them -- it raises immediately) must
        not be rerouted into the frozen loop just because the session
        happens to also be in a guard-triggering state.  Before this
        test's fix, `frozen_fallback_guard_declined` was computed once
        from session-global attributes and never revisited after the
        `except Exception` handler set `response = None`, so ANY bug in a
        production scene-1 responder, on a pre-ack or census-unresolved
        boot, would have silently swapped `super().dispatch(parsed)` in
        for the safe zero-byte decline every other exception at this call
        site gets -- reintroducing, only for that one state combination,
        exactly the "crash-prone frozen loop for a claimed scene" exposure
        this call site's own surrounding comment (round `hd6tac`) says it
        exists to avoid."""
        def _buggy_respond(**_ignored):
            raise KeyError("unrelated bug, nothing to do with any guard")

        self._swap_scene1_responder(SCENE1_MODULE, _buggy_respond)
        state = self._state("tok_unrelated_exception")
        state.world_census_identity_resolved = False
        actions, _console = self._dispatch(
            state, self._choose_npc_pc(ARBITRARY_ACTOR_IDENTITY),
        )
        self.assertEqual(
            actions, [],
            "an unrelated exception must stay the ordinary zero-byte "
            "decline, never the frozen-loop fallback",
        )
        self.assertIn(
            "scene_choose_npc_responder_failed_KeyError", state.events,
        )
        self.assertIn("scene_choose_npc_responder_declined", state.events)
        self.assertNotIn(
            "scene_choose_npc_responder_declined_frozen_fallback",
            state.events,
            "an exception is never a guard decline, however the "
            "session's global attributes happen to be set",
        )


if __name__ == "__main__":
    unittest.main()
