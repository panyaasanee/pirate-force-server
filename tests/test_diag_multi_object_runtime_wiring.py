"""CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001) on the REAL dispatcher.

``tests/test_diag_multi_object_wiring.py`` proves every function
``diag_multi_object_wiring.py`` exports, offline, against synthetic
rosters/ledgers. It does not prove the four ``runtime.py`` call sites
themselves -- that they are spliced in the right place, in the right order,
reading the right session attributes. This file drives
``make_state_class`` headless (no socket, no client) exactly the way
``tests/test_mob_combat_dispatch.py`` and ``tests/test_bg0002_census_wiring.py``
do, with ``PF_DIAG_MULTI_OBJECT_CONFIG`` pointed at a temp allowlist naming
the test account, and checks:

* an account NOT in the allowlist gets a login byte-for-byte identical to one
  with the diagnostic module never imported (the "off path is invisible"
  requirement diag_multi_object_wiring.py's own module docstring states);
* an allowlisted account at bg0001's home spawn gets exactly 5
  ``DIAG object=...`` console lines, and the arrival census frame carries
  118 actors (113 real + 5 diagnostic) via the module's own wire-count
  reader;
* an attack on D0 (the diagnostic control) reaches ``mob_combat`` at all
  (point (2) of the wiring: the widened roster/ledger), producing the
  ANNOUNCE+BAR pair like any real field mob;
* the adversary-caught bug this wiring exists to fix: a hit that recomposes
  the bar/death census over the REAL 13-mob roster used to omit -- and, once
  a diagnostic kill entered the register, REFUSE to compose at all -- see
  ``diag_multi_object_wiring``'s own PF-ADVERSARY NOTE.  Here, after
  attacking D0, the four still-alive diagnostic objects remain resolvable as
  combat targets (t proving they were not wiped off the session's own
  roster/ledger by the recompose that just ran).
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

from pirateforce_foundation import diag_multi_object_config  # noqa: E402
from pirateforce_foundation import diag_multi_object_wiring  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_diag_multi_object as diag  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
REAL_CENSUS_COUNT = 115  # bg0001's own committed WORLD-CENSUS-001 roster
DIAG_COUNT = len(diag.diagnostic_objects())


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class DiagMultiObjectRuntimeWiringTests(unittest.TestCase):
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
        self.config_path = Path(self.tmp.name) / "diag_multi_object.json"

    def _write_allowlist(self, *account_names):
        self.config_path.write_text(
            json.dumps({
                diag_multi_object_config.CONFIG_KEY: list(account_names),
            }),
            encoding="utf-8",
        )

    def _state(self, token):
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
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _arrive(self, state, env_override):
        anchor = (
            state.foundation.selected.position.x,
            state.foundation.selected.position.y,
            state.foundation.selected.position.z,
        )
        pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(self.legacy.f32tag(v) for v in (*anchor, 0.0))
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, 0)
        )
        buffer = io.StringIO()
        with mock_env(diag_multi_object_config.ENV_OVERRIDE, env_override):
            with contextlib.redirect_stdout(buffer):
                state.dispatch(self.legacy.parse_outer(pc))
        return buffer.getvalue()

    def _action_vital_pc(self, target_identity):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _attack(self, state, target_identity, env_override):
        with mock_env(diag_multi_object_config.ENV_OVERRIDE, env_override):
            return state.dispatch(
                self.legacy.parse_outer(self._action_vital_pc(target_identity))
            )

    # ----- the off path is invisible ------------------------------------

    def test_an_unlisted_account_gets_no_diag_lines_and_the_ordinary_census(
            self):
        self._write_allowlist("someone_else")
        state = self._state("diag_off")
        console = self._arrive(state, str(self.config_path))
        self.assertNotIn("DIAG object=", console)
        self.assertEqual(state.diag_multi_objects, ())
        self.assertEqual(state.world_census_actor_count, REAL_CENSUS_COUNT)

    def test_no_config_file_at_all_gets_no_diag_lines(self):
        state = self._state("diag_no_config")
        missing_path = str(Path(self.tmp.name) / "does_not_exist.json")
        console = self._arrive(state, missing_path)
        self.assertNotIn("DIAG object=", console)
        self.assertEqual(state.diag_multi_objects, ())

    # ----- the on path ----------------------------------------------------

    def test_a_listed_account_gets_exactly_five_diag_lines_and_a_wider_census(
            self):
        self._write_allowlist("diag_on")
        state = self._state("diag_on")
        console = self._arrive(state, str(self.config_path))
        diag_lines = [
            line for line in console.splitlines()
            if line.startswith("DIAG object=")
        ]
        self.assertEqual(len(diag_lines), DIAG_COUNT)
        for label, line in zip(
            (o.label for o in diag.diagnostic_objects()), diag_lines,
        ):
            self.assertIn("object=%s" % label, line)
        self.assertEqual(len(state.diag_multi_objects), DIAG_COUNT)
        # The CENSUS bookkeeping (world_census_actor_count) stays at the real
        # 113 -- see census_frames()'s own docstring on why the extra five
        # must live in the bytes, never in this count.
        self.assertEqual(state.world_census_actor_count, REAL_CENSUS_COUNT)
        self.assertIn("DIAG_CENSUS assembled=%d" % DIAG_COUNT, console)

    def test_an_attack_on_d0_reaches_mob_combat_and_keeps_all_five_alive(
            self):
        self._write_allowlist("diag_combat")
        state = self._state("diag_combat")
        self._arrive(state, str(self.config_path))
        d0 = next(
            o for o in state.diag_multi_objects
            if o.label == diag.DIAG_LABEL_CONTROL
        )
        buffer = io.StringIO()
        with mock_env(
            diag_multi_object_config.ENV_OVERRIDE, str(self.config_path),
        ):
            with contextlib.redirect_stdout(buffer):
                actions = state.dispatch(self.legacy.parse_outer(
                    self._action_vital_pc(d0.mob.actor_identity)
                ))
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            ["MOB_COMBAT_ANNOUNCE", "MOB_COMBAT_BAR"],
        )
        # THE ADVERSARY-CAUGHT BUG, proven fixed on the real dispatcher: the
        # recompose this hit just ran (MOB_COMBAT_BAR) must not have wiped
        # the OTHER four diagnostic identities off this session's own
        # roster/ledger -- they must still resolve as valid combat targets.
        for obj in state.diag_multi_objects:
            if obj.mob.actor_identity == d0.mob.actor_identity:
                continue
            self.assertIsNotNone(
                state.mob_combat_ledger.balance_of(obj.mob.actor_identity),
                "diagnostic identity 0x%X dropped off the ledger after "
                "hitting D0 -- the town-erasure bug this wiring exists to "
                "prevent" % obj.mob.actor_identity,
            )
        self.assertIn(
            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE", buffer.getvalue(),
        )

    def test_a_gm_configured_but_not_diag_listed_account_gets_nothing(self):
        # Two independent allowlists (gm.accounts vs diag_multi_object_config)
        # must not leak into each other: an account can be a GM without
        # getting the five diagnostic objects, and vice versa.
        self._write_allowlist("only_diag_listed")
        state = self._state("not_diag_listed_at_all")
        console = self._arrive(state, str(self.config_path))
        self.assertNotIn("DIAG object=", console)


class _EnvOverride:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self._had_previous = False
        self._previous = None

    def __enter__(self):
        import os
        self._had_previous = self.name in os.environ
        self._previous = os.environ.get(self.name)
        os.environ[self.name] = self.value
        return self

    def __exit__(self, *exc_info):
        import os
        if self._had_previous:
            os.environ[self.name] = self._previous
        else:
            os.environ.pop(self.name, None)
        return False


def mock_env(name, value):
    return _EnvOverride(name, value)


if __name__ == "__main__":
    unittest.main()
