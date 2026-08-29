"""Which scene registry is authoritative -- the disk, or the one this process holds.

``CORE-REQUEST-GM-034`` (lane GM, round ``qq0i9u``) reports two readers of the
same table that can disagree for the whole life of a process:

* ``runtime.py`` loads the registry ONCE at boot (``CORE-REQUEST-003``, so a
  malformed pin stops the boot in front of an operator rather than surfacing
  as a per-login refusal) and passes that snapshot to ``resolve_entry``.
* ``gm/login_scene_admission.login_entry_is_pinned`` re-reads the FILE on
  every login.

Lane GM's own test called the gap between those two readings "a few
microseconds".  It is the age of the process.

ONLY ONE DIRECTION IS DANGEROUS, and this file walks it.  A registry edited
NARROWER after boot (``login_entry_allowed`` true->false) leaves the snapshot
stricter than the disk, so the destination is refused -- fail-closed, and
nobody is hurt.  A registry edited WIDER after boot produces an override the
disk-side admission APPROVES and the snapshot then REFUSES, and before the
guard this file pins, that refusal returned no frames at all.  A standalone
grant is never consumed (``COO-DECISION 20260829_0542``), so the client's
automatic retry met the same wall every time: a permanent lockout, with the
GM console token never printed because the disk-side check had passed.

WHY THE SIBLING FILE DOES NOT ALREADY COVER THIS.
``test_gm_login_scene_override_standalone_at_login`` drives its refusals with
scene 17, which is pinned ``login_entry_allowed=False`` IN THE COMMITTED
FILE.  Both readers therefore agree, lane GM's disk-side admission refuses
first, and the login never reaches the snapshot at all.  That file pins the
disk-refuses case; nothing pinned the disagreement, which is the only case
``CORE-REQUEST-GM-034`` is about.  The two files must stay distinct for that
reason.

GATE-WALK (``COO-DECISION 20260829_0742``), branches walked here:

* the registry probe REFUSING an override the disk-side admission passed --
  walked, with the process snapshot patched at ``make_state_class`` time so
  the disagreement is REAL (the file on disk is untouched and still allows
  the destination, which the control below measures rather than assumes).
* the same probe ACCEPTING -- walked as the falsifier.  Without it a guard
  that refused every override would pass every other test in this file.
* the restore of a CONSUMED entry refused by the probe -- walked.
* a STANDALONE grant refused by the probe -- walked, and asserted to write
  nothing back, because there was nothing taken off disk to put back.

Not walked here: ``CONSUME_FAILED`` and ``NOTHING_STAGED`` (the sibling files
own those), and any client-observable claim -- this is wire/DB only.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
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

# Prison Exile Island: a real pinned destination with a spawn, allowed at
# login in the committed registry.  The disagreement in this file is
# manufactured in the PROCESS, never in the file, which is what makes it the
# CORE-REQUEST-GM-034 case rather than the sibling file's.
CONTESTED_SCENE_ID = 2
HOME_SCENE_ID = 1


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _registry_refusing(scene_id: int) -> world_scene_travel.SceneRegistry:
    """The real registry, with one destination shut against login.

    Built from the committed file rather than from a hand-made row so the
    snapshot differs from the disk in EXACTLY the one field under test.
    """
    live = world_scene_travel.load_scene_registry()
    return world_scene_travel.SceneRegistry(
        destinations=tuple(
            replace(destination, login_entry_allowed=False)
            if destination.n_id == scene_id else destination
            for destination in live.destinations
        )
    )


class LoginSceneRegistryAuthorityTests(unittest.TestCase):
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

    def _write_configs(self, gm_accounts_list, gm_map, standalone_map):
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": gm_accounts_list}), encoding="ascii",
        )
        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": gm_map}), encoding="ascii",
        )
        self.standalone_path.write_text(
            json.dumps(
                {login_scene_override.STANDALONE_JSON_KEY: standalone_map}
            ),
            encoding="ascii",
        )

    def _env(self):
        return {
            gm_accounts.ENV_OVERRIDE: str(self.accounts_path),
            login_scene_override.ENV_OVERRIDE: str(self.overrides_path),
            login_scene_override.STANDALONE_ENV_OVERRIDE: str(
                self.standalone_path
            ),
        }

    def _login_and_start(self, token, *, snapshot=None, selector=None):
        """One full login through the real dispatcher.

        ``snapshot`` is installed ONLY across ``make_state_class``, which is
        where ``runtime.py`` reads the registry once.  Every later read --
        lane GM's admission among them -- goes to the real file, which is
        precisely the split under test.
        """
        if snapshot is None:
            state_type = make_state_class(
                self.legacy, self.lifecycle, self.projector,
            )
        else:
            with mock.patch.object(
                world_scene_travel, "load_scene_registry",
                return_value=snapshot,
            ):
                state_type = make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                )
        state = state_type(token)
        with mock.patch.dict(gm_accounts.os.environ, self._env()):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc(token)
                ))
                if selector is None:
                    state.dispatch(self.legacy.parse_outer(
                        self.legacy._V25_REAL_CREATE_PC
                    ))
                    character = self.store.list_characters(
                        state.foundation.account_id
                    )[-1]
                    selector = character.selector
                actions = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(selector)
                ))
        return state, selector, actions, stdout.getvalue()

    def _gm_map(self):
        return json.loads(self.overrides_path.read_text(encoding="ascii"))[
            "gm_login_scene"
        ]

    # ----- the control: the two readers AGREE ------------------------------

    def test_an_override_the_snapshot_allows_is_applied(self):
        """The falsifier.

        A guard that refused every override would satisfy every other test
        in this file.  Here disk and snapshot agree that the destination is
        open, and the override must go through untouched.
        """
        self._write_configs([], {}, {"plain_tester": CONTESTED_SCENE_ID})

        with contextlib.redirect_stderr(io.StringIO()):
            state, _selector, actions, _out = self._login_and_start(
                "plain_tester"
            )

        self.assertIn(
            f"gm_login_scene_override_applied_{CONTESTED_SCENE_ID}",
            state.events,
        )
        self.assertNotIn(
            "gm_login_scene_override_refused_by_registry_"
            f"{CONTESTED_SCENE_ID}",
            state.events,
        )
        self.assertNotEqual(actions, [])
        self.assertEqual(
            state.foundation.selected.position.scene_id, CONTESTED_SCENE_ID,
        )

    def test_the_file_still_allows_the_scene_the_snapshot_refuses(self):
        """The disagreement is real, and it is in the process only.

        Without this the whole file could be passing because the fixture
        quietly edited the registry FILE, which would make it a duplicate of
        the sibling file rather than the CORE-REQUEST-GM-034 case.
        """
        snapshot = _registry_refusing(CONTESTED_SCENE_ID)
        self.assertFalse(snapshot[CONTESTED_SCENE_ID].login_entry_allowed)
        on_disk = world_scene_travel.load_scene_registry()
        self.assertTrue(on_disk[CONTESTED_SCENE_ID].login_entry_allowed)

    # ----- the case the ticket is about ------------------------------------

    def test_a_standalone_grant_the_snapshot_refuses_still_lets_the_player_in(
        self,
    ):
        """The lockout, pinned as absent.

        Yesterday this login returned no actions at all, and because the
        standalone map is not consumed, so did every retry after it.
        """
        self._write_configs([], {}, {"plain_tester": CONTESTED_SCENE_ID})
        snapshot = _registry_refusing(CONTESTED_SCENE_ID)

        with contextlib.redirect_stderr(io.StringIO()):
            state, _selector, actions, stdout = self._login_and_start(
                "plain_tester", snapshot=snapshot,
            )

        # In the game, at its own row -- not at the refused destination.
        self.assertNotEqual(
            actions, [], "a refused override must not refuse the login",
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, HOME_SCENE_ID,
        )
        self.assertNotIn("world_scene_entry_refused_no_reply", state.events)
        self.assertIn(
            "gm_login_scene_override_refused_by_registry_"
            f"{CONTESTED_SCENE_ID}",
            state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_applied_{CONTESTED_SCENE_ID}",
            state.events,
        )
        # The operator is told, by name, on the console -- the complaint in
        # CORE-REQUEST-GM-034 was that this path went silent.
        self.assertIn("GM_LOGIN_SCENE_OVERRIDE_REFUSED", stdout)
        self.assertIn(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN, stdout,
        )

    def test_the_retry_after_a_refused_override_is_the_same_as_the_first(self):
        """The lockout was the RETRY, so both logins are measured."""
        self._write_configs([], {}, {"plain_tester": CONTESTED_SCENE_ID})
        snapshot = _registry_refusing(CONTESTED_SCENE_ID)

        with contextlib.redirect_stderr(io.StringIO()):
            first, selector, first_actions, _o1 = self._login_and_start(
                "plain_tester", snapshot=snapshot,
            )
            second, _sel, second_actions, _o2 = self._login_and_start(
                "plain_tester", snapshot=snapshot, selector=selector,
            )

        for state, actions in (
            (first, first_actions), (second, second_actions),
        ):
            self.assertNotEqual(actions, [])
            self.assertEqual(
                state.foundation.selected.position.scene_id, HOME_SCENE_ID,
            )

    def test_only_one_destination_line_reaches_the_console(self):
        """GT-079 reads the destination off the console.

        The probe calls ``resolve_entry`` a SECOND time, so the ACCEPTED
        path is where the double line lands: the probe resolves the
        destination, the real call resolves it again, and an unsilenced
        probe prints ``WORLD_SCENE`` twice for one arrival.  A human
        grading GT-079 off the console counts arrivals.

        THE REFUSED PATH CANNOT SHOW THIS, and this file does not pretend
        otherwise: a refusal raises before ``resolve_entry`` reaches its
        emit loop, so a probe left unsilenced prints nothing there.  That
        was measured -- the mutation is green against the refused case and
        red here -- which is why the assertion lives on this side.

        ``WORLD_SCENE`` is matched as a whole first field on purpose:
        ``WORLD_SCENE_RELOCATED``, ``_KEPT_ROW`` and ``_LIVENESS`` are
        different lines, and counting them would make this pass for the
        wrong reason.
        """
        self._write_configs([], {}, {"plain_tester": CONTESTED_SCENE_ID})

        with contextlib.redirect_stderr(io.StringIO()):
            _state, _selector, actions, stdout = self._login_and_start(
                "plain_tester"
            )

        self.assertNotEqual(actions, [])
        entry_lines = [
            line for line in stdout.splitlines()
            if line.split(" ", 1)[0] == "WORLD_SCENE"
        ]
        self.assertEqual(
            len(entry_lines), 1,
            f"exactly one destination line, got {entry_lines}",
        )
        self.assertIn(f"scene_id={CONTESTED_SCENE_ID} ", entry_lines[0])

    # ----- what happens to a spent entry -----------------------------------

    def test_a_consumed_entry_refused_by_the_snapshot_is_given_back(self):
        """A GM-gated entry is spent BEFORE the probe can refuse it.

        Without the restore the operator's staged warp is destroyed by a
        login that never reached it, and the audit row says ``consumed`` for
        a scene nobody entered.
        """
        self._write_configs(
            ["gm_tester"], {"gm_tester": CONTESTED_SCENE_ID}, {},
        )
        snapshot = _registry_refusing(CONTESTED_SCENE_ID)

        with contextlib.redirect_stderr(io.StringIO()):
            state, _selector, actions, _out = self._login_and_start(
                "gm_tester", snapshot=snapshot,
            )

        self.assertNotEqual(actions, [])
        self.assertIn(
            "gm_login_scene_override_restored_after_refusal_"
            f"{CONTESTED_SCENE_ID}",
            state.events,
        )
        # Back on disk, with the value it had, so the next login after the
        # registry is fixed still finds it.
        self.assertEqual(self._gm_map(), {"gm_tester": CONTESTED_SCENE_ID})
        # And exactly once: a second restore from the handler further down
        # would be a write of an entry this login already gave back.
        self.assertEqual(
            len([
                event for event in state.events
                if event.startswith("gm_login_scene_override_restored_after_")
                or event.startswith("gm_login_scene_override_lost_to_")
            ]),
            1,
        )

    def test_a_refused_standalone_grant_writes_nothing_to_the_gm_map(self):
        """Nothing was taken off disk, so nothing may be written back.

        The blast radius that matters: ``gm_login_scene.json`` is the
        chat-``/warp``-writable file, and a phantom entry there activates
        the day the account is listed as a GM.
        """
        self._write_configs([], {}, {"plain_tester": CONTESTED_SCENE_ID})
        gm_map_before = self.overrides_path.read_bytes()
        standalone_before = self.standalone_path.read_bytes()
        snapshot = _registry_refusing(CONTESTED_SCENE_ID)

        with contextlib.redirect_stderr(io.StringIO()):
            state, _selector, _actions, _out = self._login_and_start(
                "plain_tester", snapshot=snapshot,
            )

        self.assertEqual(self.overrides_path.read_bytes(), gm_map_before)
        self.assertEqual(self._gm_map(), {})
        self.assertEqual(
            self.standalone_path.read_bytes(), standalone_before,
        )
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_restored_after_")
             or event.startswith("gm_login_scene_override_lost_to_")],
            [],
        )


if __name__ == "__main__":
    unittest.main()
