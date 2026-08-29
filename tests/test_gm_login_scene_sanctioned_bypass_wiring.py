"""CORE-REQUEST-GM-038 (LANE-GM, 2026-08-29T19:25+07:00) -- the sanctioned
via_login=False bypass at runtime.py's two resolve_entry() call sites,
driven through the REAL dispatcher.

WHAT IS WIRED: a login whose scene override was taken off the GM-GATED map
(outcome CONSUMED, the only outcome that sets ``override_consumed_scene``)
and names a scene in ``login_scene_admission.SANCTIONED_BARRED_SCENES``
resolves with ``via_login=False`` -- the same bypass shape
``columbus_quest_dispatch.py:464`` already uses -- at BOTH call sites (the
probe and the real call), so a sanctioned, barred destination admits the
GM instead of refusing at the second gate what the first admitted.

WHAT THIS FILE DOES *NOT* CLAIM, said before the tests so a green run is
not misread: the full /warp 126 route is still incomplete.  Lane GM's own
admission (``login_entry_is_pinned``) still refuses sanctioned scenes at
map load, so a REAL config file naming 126 comes back CONSUME_FAILED
before this bypass is ever consulted -- that half is lane GM's to widen
now that this half exists, and their letter says so.  The gated-map test
here therefore substitutes the consumer's ANSWER (a real ``ConsumeResult``
with outcome CONSUMED) and drives everything downstream of it for real:
the bypass predicate, both resolve_entry() calls, the resync, the wire
frames.  The standalone-map and persisted-row tests run the whole real
path with no substitution at all, because their required outcome -- still
refused -- is reachable today end to end.

The registry is the one lane A has not landed yet, synthesized the same
way ``tests/test_gm_login_scene_sanctioned_barred.py`` does: a copy of a
REAL barred row (scene 17) renamed to 126 with ``login_entry_allowed``
False, appended to the real registry.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import runtime as runtime_module  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_admission  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm.login_scene_consume import (  # noqa: E402
    CONSUMED,
    STANDALONE_NOT_CONSUMED,
    ConsumeResult,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SANCTIONED = 126
BARRED_NOT_SANCTIONED = 17


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _registry_with_sanctioned_row():
    """Lane A's registry with the scene-126 row landed, barred at login."""
    registry = world_scene_travel.load_scene_registry()
    source = registry[BARRED_NOT_SANCTIONED]
    landed = dataclasses.replace(
        source, n_id=SANCTIONED, login_entry_allowed=False,
    )
    return dataclasses.replace(
        registry, destinations=registry.destinations + (landed,)
    )


class SanctionedBypassWiringTests(unittest.TestCase):
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
        self.accounts_path = Path(self.tmp.name) / "gm_accounts.json"
        self.overrides_path = Path(self.tmp.name) / "gm_login_scene.json"
        self.standalone_path = (
            Path(self.tmp.name) / "gm_login_scene_standalone.json"
        )
        self.registry = _registry_with_sanctioned_row()

    def _write_configs(self, gm_list, gm_map, standalone_map):
        # All three, always -- an unpinned path resolves to a repo-relative
        # default and the test's outcome then depends on the machine, the
        # exact hole pf-adversary drove through the older harness in
        # test_gm_login_scene_override_wiring.py.
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": gm_list}), encoding="utf-8"
        )
        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": gm_map}), encoding="utf-8"
        )
        self.standalone_path.write_text(
            json.dumps(
                {login_scene_override.STANDALONE_JSON_KEY: standalone_map}
            ),
            encoding="utf-8",
        )

    def _env(self):
        return {
            gm_accounts.ENV_OVERRIDE: str(self.accounts_path),
            login_scene_override.ENV_OVERRIDE: str(self.overrides_path),
            login_scene_override.STANDALONE_ENV_OVERRIDE: str(
                self.standalone_path
            ),
        }

    def _login_create_start(self, token, *, persisted_scene=None):
        """One full login through the real dispatcher, console captured.

        The registry the state class snapshots at construction is the
        synthesized landed one, patched exactly where runtime.py reads it
        (the ``load_scene_registry()`` call in ``make_state_class``).
        """
        with mock.patch.object(
            world_scene_travel, "load_scene_registry",
            lambda *a, **k: self.registry,
        ):
            state_type = make_state_class(
                self.legacy, self.lifecycle, self.projector,
            )
        state = state_type(token)
        buf = io.StringIO()
        with mock.patch.dict(gm_accounts.os.environ, self._env()):
            with contextlib.redirect_stdout(buf):
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc(token)
                ))
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._V25_REAL_CREATE_PC
                ))
                character = self.store.list_characters(
                    state.foundation.account_id
                )[-1]
                if persisted_scene is not None:
                    # A real, stored row naming the sanctioned scene --
                    # written the only way a test can synthesize it, to a
                    # throwaway per-test SQLite DB (same shape as
                    # test_bg0002_census_wiring.py's _state_at_scene2).
                    self.store.select_character(
                        state.foundation.session_id, character.selector,
                    )
                    stored = self.store.get_character(character.id).position
                    self.store.save_position(
                        state.foundation.session_id, character.id,
                        dataclasses.replace(
                            stored, scene_id=persisted_scene,
                        ),
                    )
                actions = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(character.selector)
                ))
        return state, buf.getvalue(), actions

    def _world_scene_lines(self, out):
        return [
            l for l in out.splitlines() if l.startswith("WORLD_SCENE ")
        ]

    # ----- the letter's test (a): CONSUMED grant of a sanctioned scene ----

    def test_a_consumed_gated_grant_of_the_sanctioned_scene_logs_in_there(
        self,
    ):
        self.assertTrue(
            login_scene_admission.is_sanctioned_barred_scene(SANCTIONED)
        )
        self._write_configs(["gm_runner"], {}, {})
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            lambda *a, **k: ConsumeResult(SANCTIONED, CONSUMED),
        ):
            state, out, actions = self._login_create_start("gm_runner")
        self.assertIn(
            f"gm_login_scene_override_applied_{SANCTIONED}", state.events,
        )
        self.assertNotIn("GM_LOGIN_SCENE_OVERRIDE_REFUSED", out)
        self.assertNotIn("WORLD_SCENE_ENTRY_REFUSED", out)
        lines = self._world_scene_lines(out)
        self.assertEqual(len(lines), 1, out)
        self.assertIn(f"scene_id={SANCTIONED}", lines[0])
        self.assertTrue(
            any(a[0] == "FOUNDATION_SELECTED_START_GAME" for a in actions),
            actions,
        )

    def test_a_consumed_grant_of_a_barred_unsanctioned_scene_still_refuses(
        self,
    ):
        # The letter's no-go #3 (scene 17 must refuse on every path), pinned
        # against the exact mutation that would widen the bypass: dropping
        # the is_sanctioned_barred_scene() half of the predicate.
        self.assertFalse(
            login_scene_admission.is_sanctioned_barred_scene(
                BARRED_NOT_SANCTIONED
            )
        )
        self._write_configs(["gm_runner"], {}, {})
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            lambda *a, **k: ConsumeResult(BARRED_NOT_SANCTIONED, CONSUMED),
        ):
            state, out, _actions = self._login_create_start("gm_runner")
        self.assertIn(
            "gm_login_scene_override_refused_by_registry_"
            f"{BARRED_NOT_SANCTIONED}",
            state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_applied_{BARRED_NOT_SANCTIONED}",
            state.events,
        )
        lines = self._world_scene_lines(out)
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    # ----- the letter's test (b): standalone map, whole real path ---------

    def test_a_standalone_grant_of_the_sanctioned_scene_is_still_refused(
        self,
    ):
        # No substitution anywhere: the real consumer loads the standalone
        # map, lane GM's own admission refuses 126 at map load
        # (login_entry_is_pinned is False for a barred row), and the login
        # lands at the character's own row -- exactly today's behaviour.
        # The bypass must not change one bit of it, because the account is
        # not a GM and the grant never had CONSUMED provenance.
        self._write_configs([], {}, {"plain_tester": SANCTIONED})
        state, out, _actions = self._login_create_start("plain_tester")
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            ),
            state.events,
        )
        lines = self._world_scene_lines(out)
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_a_standalone_outcome_for_the_sanctioned_scene_gets_no_bypass(
        self,
    ):
        """The letter's no-go #1, pinned where the real path cannot reach
        it YET: today a standalone grant of 126 dies at map load
        (CONSUME_FAILED), so the test above never exercises the provenance
        half of the bypass predicate -- measured this round: dropping
        ``override_consumed_scene is not None`` from it left every
        config-driven test green.  The day lane GM widens their admission
        for sanctioned scenes, a STANDALONE_NOT_CONSUMED answer for 126
        WILL reach the probe, and that mutation then hands a server-side
        result to accounts that are not in gm_accounts.json -- the exact
        charter breach the letter says must refuse the whole request
        rather than ship.  So the consumer's future answer is substituted
        here, and the bypass must not fire.
        """
        self._write_configs([], {}, {})
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            lambda *a, **k: ConsumeResult(
                SANCTIONED, STANDALONE_NOT_CONSUMED
            ),
        ):
            state, out, _actions = self._login_create_start("plain_tester")
        self.assertIn(
            f"gm_login_scene_override_refused_by_registry_{SANCTIONED}",
            state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_applied_{SANCTIONED}", state.events,
        )
        lines = self._world_scene_lines(out)
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_a_latched_bypass_never_leaks_onto_the_characters_own_row(self):
        """pf-adversary (this round, D2, MEASURED): the real call's guard is
        ``gm_sanctioned_bypass AND login_scene_override is not None`` and
        the second conjunct had no test -- dropping it left the whole
        5000-test suite green while a driven exploit landed a login in
        barred scene 17.  The scenario that needs it: the bypass latches
        True for a CONSUMED sanctioned grant, then the PROBE refuses the
        sanctioned destination for a NON-login reason (here: lane A ships
        the 126 row barred but spawnless -- the row-shape drift the GM
        letter itself contemplates).  The refusal handler resets
        login_scene_override to None but deliberately not the bypass flag,
        so only the second conjunct keeps via_login=True on the fallback
        resolve of the character's OWN stored row -- which here names
        barred scene 17 and must stay refused (no-gos #2 and #3 at once).
        """
        registry = world_scene_travel.load_scene_registry()
        source = registry[BARRED_NOT_SANCTIONED]
        spawnless_sanctioned = dataclasses.replace(
            source, n_id=SANCTIONED, login_entry_allowed=False, spawn=None,
        )
        self.registry = dataclasses.replace(
            registry, destinations=registry.destinations + (
                spawnless_sanctioned,
            ),
        )
        self._write_configs(["gm_runner"], {}, {})
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            lambda *a, **k: ConsumeResult(SANCTIONED, CONSUMED),
        ):
            state, out, actions = self._login_create_start(
                "gm_runner", persisted_scene=BARRED_NOT_SANCTIONED,
            )
        # The probe refused the override (not at the login gate -- at the
        # spawn gate), so the grant never applied...
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            ),
            state.events,
        )
        # ...and the character's own barred row must then refuse exactly as
        # it does for everyone else, latched bypass or no latched bypass.
        self.assertIn("WORLD_SCENE_ENTRY_REFUSED", out)
        self.assertIn("world_scene_entry_refused_no_reply", state.events)
        self.assertEqual(actions, [])
        self.assertNotIn(f"scene_id={BARRED_NOT_SANCTIONED}",
                         " ".join(self._world_scene_lines(out)))

    # ----- the letter's test (c): a persisted row, no override ------------

    def test_a_persisted_row_naming_the_sanctioned_scene_is_still_refused(
        self,
    ):
        # No-go #2: the bypass is tied to "this row came from a CONSUMED
        # override", never to the scene number, so a character whose STORED
        # row says 126 still meets via_login=True and the barred-at-login
        # refusal -- the door lane A shut stays shut for everyone else.
        self._write_configs([], {}, {})
        state, out, actions = self._login_create_start(
            "row_says_126", persisted_scene=SANCTIONED,
        )
        self.assertIn("WORLD_SCENE_ENTRY_REFUSED", out)
        self.assertIn("not allowed as a login destination", out)
        self.assertIn("world_scene_entry_refused_no_reply", state.events)
        self.assertEqual(actions, [])
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            ),
            state.events,
        )


if __name__ == "__main__":
    unittest.main()
