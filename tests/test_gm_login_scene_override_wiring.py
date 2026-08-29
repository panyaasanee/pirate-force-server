"""CORE-REQUEST-017 point 1 (LANE-GM, 2026-08-27T15:24+07:00) -- per-account
login-scene override, driven through the REAL dispatcher.

``gm/login_scene_override.py`` (GM-005) was unit-proven offline in
``tests/test_gm_login_scene.py`` since round R194/R195 but had no call site
in ``runtime.py`` -- the registry table's own row 017 tracked this as
"wireable but deliberately deferred another round" behind the lane_hooks
skeleton (R195). This proves the wiring itself: a listed GM account with a
configured override actually arrives at that scene through
``world_scene_entry.resolve_entry()``, not merely that the override function
computes the right answer in isolation.

Wired directly in ``runtime.py`` rather than through ``lane_hooks`` because
it has to change WHICH position ``resolve_entry()`` resolves -- see the
comment at the call site in ``runtime.py`` for why that is outside
``lane_hooks.fire()``'s deliberately report-only shape.

Only the scene_id read by ``resolve_entry()`` changes; the stored row's
x/y/z/heading pass through untouched, so every one of ``resolve_entry()``'s
own safety rules (ground evidence, home-never-touched, login_entry_allowed)
still applies to the overridden destination exactly as it does to a normal
login. This file proves that inheritance holds for two real destinations
(a scene with a ground-less pinned spawn, and home itself), not just that
the override value gets passed through.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
KNOWN_SCENE_ID = 2  # Prison Exile Island -- pinned spawn, no ground extent


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GmLoginSceneOverrideWiringTests(unittest.TestCase):
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

    def _configs(self, gm_accounts_value, overrides_value):
        accounts_path = Path(self.tmp.name) / "gm_accounts.json"
        accounts_path.write_text(
            json.dumps({"gm_accounts": gm_accounts_value}), encoding="utf-8"
        )
        overrides_path = Path(self.tmp.name) / "gm_login_scene.json"
        overrides_path.write_text(
            json.dumps({"gm_login_scene": overrides_value}), encoding="utf-8"
        )
        return accounts_path, overrides_path

    def _login_and_start(
        self, token, accounts_path, overrides_path, standalone_path=None
    ):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        env = {
            gm_accounts.ENV_OVERRIDE: str(accounts_path),
            login_scene_override.ENV_OVERRIDE: str(overrides_path),
        }
        # Always pinned, never left to fall through.  `standalone_path=None`
        # means "this test has no standalone map", and before this line that
        # was expressed by NOT setting the variable -- which resolved to the
        # repo-relative default `config/gm_login_scene_standalone.json`, a
        # gitignored path.  pf-adversary dropped a map there and turned this
        # file's `test_missing_override_config_means_no_override_for_any_gm`
        # red: "no override for any GM" was a fact about the machine, not
        # about the fixture.  An unwritten path inside this test's own temp
        # dir says the same thing and means it.
        env[login_scene_override.STANDALONE_ENV_OVERRIDE] = str(
            standalone_path if standalone_path is not None
            else Path(self.tmp.name) / "no_standalone_map.json"
        )
        with mock.patch.dict(gm_accounts.os.environ, env):
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc(token)
                ))
                state.dispatch(
                    self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
                )
                character = self.store.list_characters(
                    state.foundation.account_id
                )[-1]
                actions = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(character.selector)
                ))
        return state, buf.getvalue(), actions

    def test_a_gm_account_with_an_override_arrives_at_that_scene(self):
        accounts_path, overrides_path = self._configs(
            ["gm_runner"], {"gm_runner": KNOWN_SCENE_ID}
        )
        state, out, _actions = self._login_and_start(
            "gm_runner", accounts_path, overrides_path
        )
        self.assertIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", state.events
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn(f"scene_id={KNOWN_SCENE_ID}", lines[0])

    def test_the_actor_movement_frame_agrees_with_the_teleport_not_the_stored_row(
        self,
    ):
        """pf-adversary (round 0vjgyy) found the first version of this wiring
        only redirected the teleport packet -- the START_GAME_RES ActorAttr/
        MovementAttr frame was already baked from the character's REAL stored
        row by select_and_start(), before the override was even computed, and
        nothing recomposed it. That is exactly world_scene_entry.py's own
        documented "biggest trap" (its module docstring: the teleport and the
        ActorAttr/MovementAttr "cannot name two different places" -- except
        they could, for exactly this override, because nothing enforced it).
        Byte-repro at the time: ActorAttr encoded scene_id=1 (home) while the
        teleport right after it carried scene_id=2.

        This proves the fix (runtime.py's "resync pc/frame" block) by
        independently resolving the SAME entry world_scene_entry.resolve_entry()
        resolves for this login, recomposing a START_GAME_RES from it via the
        same projector call runtime.py's own flagless-production path uses,
        and asserting the actual wire output equals that -- not the
        character's real, un-overridden home row.
        """
        from pirateforce_foundation import world_scene_entry

        accounts_path, overrides_path = self._configs(
            ["gm_runner"], {"gm_runner": KNOWN_SCENE_ID}
        )
        state, _out, actions = self._login_and_start(
            "gm_runner", accounts_path, overrides_path
        )
        by_label = {action[0]: action for action in actions}
        self.assertIn("FOUNDATION_SELECTED_START_GAME", by_label)
        _, actual_pc, actual_frame, _delay = by_label[
            "FOUNDATION_SELECTED_START_GAME"
        ]

        # READ FROM THE STORE, not from foundation.selected: since
        # CHIEF-DECISION 20260829_0520 option A an overridden login resyncs
        # the in-memory character to the scene it was actually sent to, so
        # `selected.position` is no longer the un-overridden row this test
        # needs as its contrast case.  The DB row still is -- this login
        # never checkpoints -- and it is what "the character's real stored
        # row" meant here all along.
        stored_row = self.store.get_character(
            state.foundation.selected.id
        ).position
        self.assertEqual(stored_row.scene_id, 1, "fresh character starts home")
        overridden_row = Position(
            KNOWN_SCENE_ID, stored_row.scene_seq, stored_row.x, stored_row.y,
            stored_row.z, stored_row.heading,
        )
        entry = world_scene_entry.resolve_entry(overridden_row, emit=lambda _l: None)
        self.assertEqual(entry.position.scene_id, KNOWN_SCENE_ID)

        expected_pc, expected_frame = self.projector.start_game(
            state.foundation.selected,
            position=entry.position,
            basic_faction=1,  # NPC_HOSTILE_PLAYER_PAIR_FACTION: the flagless
            # production path's own basic_faction=1 recompose, which this
            # test's login also goes through (no scenario flags -- active_
            # lanes is empty) and which runtime.py must ALSO thread this
            # override's position into, or it silently undoes the resync.
            backpack=state.foundation.backpack,
        )
        home_pc, home_frame = self.projector.start_game(
            state.foundation.selected,
            position=stored_row,
            basic_faction=1,
            backpack=state.foundation.backpack,
        )
        self.assertNotEqual(
            expected_pc, home_pc,
            "the two candidate frames must actually differ, or this test "
            "cannot tell a correct resync from a silently-undone one",
        )
        self.assertEqual(actual_pc, expected_pc)
        self.assertEqual(actual_frame, expected_frame)
        self.assertNotEqual(
            actual_pc, home_pc,
            "ActorAttr/MovementAttr still encode the character's real "
            "stored scene -- the override's own resync was silently undone "
            "downstream (this is the exact bug pf-adversary found)",
        )

    def test_a_non_gm_account_with_a_stray_override_entry_is_unaffected(self):
        # "not_a_gm" has an entry in gm_login_scene.json but is absent from
        # gm_accounts.json -- must log in at home exactly as if the entry
        # were not there at all (mirrors test_gm_login_scene.py's own
        # non-GM offline test, now proven through the real dispatcher).
        accounts_path, overrides_path = self._configs(
            ["gm_runner"], {"not_a_gm": KNOWN_SCENE_ID}
        )
        state, out, _actions = self._login_and_start(
            "not_a_gm", accounts_path, overrides_path
        )
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            )
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_a_gm_account_without_an_entry_logs_in_at_home_unaffected(self):
        accounts_path, overrides_path = self._configs(
            ["gm_runner", "gm_no_entry"], {"gm_runner": KNOWN_SCENE_ID}
        )
        state, out, _actions = self._login_and_start(
            "gm_no_entry", accounts_path, overrides_path
        )
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            )
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_missing_override_config_means_no_override_for_any_gm(self):
        accounts_path = Path(self.tmp.name) / "gm_accounts.json"
        accounts_path.write_text(
            json.dumps({"gm_accounts": ["gm_runner"]}), encoding="utf-8"
        )
        missing_overrides_path = (
            Path(self.tmp.name) / "does_not_exist_gm_login_scene.json"
        )
        state, out, _actions = self._login_and_start(
            "gm_runner", accounts_path, missing_overrides_path
        )
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            )
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_malformed_override_config_refuses_loud_not_a_crash(self):
        # Same refuse-by-name-not-by-crash shape as CORE-REQUEST-006's own
        # is_gm_account() guard: a malformed gm_login_scene.json must not
        # unwind the listener thread for this or any other login.
        accounts_path = Path(self.tmp.name) / "gm_accounts.json"
        accounts_path.write_text(
            json.dumps({"gm_accounts": ["gm_runner"]}), encoding="utf-8"
        )
        overrides_path = Path(self.tmp.name) / "gm_login_scene.json"
        overrides_path.write_text(
            json.dumps({"gm_login_scene": {"gm_runner": "not-an-int"}}),
            encoding="utf-8",
        )
        state, out, _actions = self._login_and_start(
            "gm_runner", accounts_path, overrides_path
        )
        # The name changed with CORE-REQUEST-GM-033 v2 (the call site now
        # CONSUMES rather than reads): `consume_login_scene_override`
        # swallows its own config faults into the CONSUME_FAILED outcome
        # instead of raising, and grants no scene for it.  What this test
        # actually guards is unchanged and still holds -- a malformed
        # gm_login_scene.json is refused BY NAME, the login proceeds at
        # home, and no listener thread unwinds.
        #
        # KNOWN COARSENING, stated rather than hidden: CONSUME_FAILED is
        # also what an entry that could not be REMOVED reports, so this one
        # event no longer tells a bad config apart from a failed delete.
        # Both are "no override was granted", which is what this call site
        # acts on; anything finer belongs in login_scene_consume.py, not in
        # a second read here.
        self.assertIn(
            "gm_login_scene_override_consume_failed", state.events
        )
        self.assertFalse(
            any(
                e.startswith("gm_login_scene_override_applied_")
                for e in state.events
            )
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("scene_id=1", lines[0])

    def test_gm_gated_account_gets_the_override_and_the_gm_state_frame(self):
        # Contrast case for the standalone tests below: a real gm_accounts.json
        # member still rides the pre-existing path end to end -- override
        # applied AND (since gm/state_wire.py's GM_UPDATE_STATE_VITAL_VERSION_
        # CONFIRMED is pinned, not None) a GM_UPDATE_STATE_AFTER_LOGIN action
        # is appended. This is the exact frame this round's standalone path
        # exists to let GT-110 avoid.
        accounts_path, overrides_path = self._configs(
            ["gm_runner"], {"gm_runner": KNOWN_SCENE_ID}
        )
        state, _out, actions = self._login_and_start(
            "gm_runner", accounts_path, overrides_path
        )
        self.assertIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", state.events
        )
        labels = [action[0] for action in actions]
        self.assertIn("GM_UPDATE_STATE_AFTER_LOGIN", labels)

    def test_standalone_only_account_gets_the_override_with_no_gm_state_frame(
        self,
    ):
        # The core safety claim of the 2026-08-28 GT-110 fix (answering
        # notes_to_chief/20260827_2240_KA1A-NOTE-GT110-unsafe-until-0x5A19-
        # payload-fixed-plus-M1P-jobs-staged.md), proven through the REAL
        # dispatcher rather than by reading gm/login_scene_override.py's
        # code: an account listed ONLY in the standalone config (empty
        # gm_accounts.json, empty gm_login_scene.json) still gets its scene
        # override applied, but never gets GM_UPDATE_STATE_AFTER_LOGIN
        # appended to the dispatch actions -- because is_gm_account() stays
        # False for it the whole way through, and that frame is gated
        # purely on is_gm_account() at the runtime.py call site
        # (CORE-REQUEST-016), never on this module. Contrast with
        # test_gm_gated_account_gets_the_override_and_the_gm_state_frame
        # directly above, which proves the same harness DOES produce that
        # action for a real GM account -- so its absence here is meaningful,
        # not an artifact of the harness never producing it at all.
        accounts_path, overrides_path = self._configs([], {})
        standalone_path = Path(self.tmp.name) / "gm_login_scene_standalone.json"
        standalone_path.write_text(
            json.dumps(
                {"standalone_login_scene": {"gt110_tester": KNOWN_SCENE_ID}}
            ),
            encoding="utf-8",
        )
        state, out, actions = self._login_and_start(
            "gt110_tester", accounts_path, overrides_path, standalone_path
        )
        self.assertIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", state.events
        )
        lines = [l for l in out.splitlines() if l.startswith("WORLD_SCENE ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn(f"scene_id={KNOWN_SCENE_ID}", lines[0])
        labels = [action[0] for action in actions]
        self.assertNotIn("GM_UPDATE_STATE_AFTER_LOGIN", labels)

    def test_standalone_config_alone_never_makes_is_gm_account_true(self):
        # Directly exercises the predicate the whole safety argument rests
        # on: is_gm_account() must stay False for a standalone-only account
        # even with the standalone env var pointed at a config that lists
        # it, because is_gm_account() never reads that file.
        standalone_path = Path(self.tmp.name) / "gm_login_scene_standalone.json"
        standalone_path.write_text(
            json.dumps(
                {"standalone_login_scene": {"gt110_tester": KNOWN_SCENE_ID}}
            ),
            encoding="utf-8",
        )
        missing_accounts_path = Path(self.tmp.name) / "does_not_exist.json"
        with mock.patch.dict(
            gm_accounts.os.environ,
            {
                gm_accounts.ENV_OVERRIDE: str(missing_accounts_path),
                login_scene_override.STANDALONE_ENV_OVERRIDE: str(
                    standalone_path
                ),
            },
        ):
            self.assertFalse(gm_accounts.is_gm_account("gt110_tester"))


if __name__ == "__main__":
    unittest.main()
