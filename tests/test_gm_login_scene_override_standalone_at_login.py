"""The standalone half of the login-scene override, walked at the CALL SITE.

``consume_login_scene_override`` has four outcomes and
``tests/test_gm_login_scene_consume.py`` walks all four OFFLINE.  The login
path in ``runtime.py`` has a branch per outcome, and until this file only
three of them had ever been reached through the real dispatcher:

* ``CONSUMED``      -- walked by ``test_gm_login_scene_override_position_resync``
* ``NOTHING_STAGED``-- walked by that file's no-override control
* ``CONSUME_FAILED``-- walked by ``test_gm_login_scene_override_wiring``
* ``STANDALONE_NOT_CONSUMED`` -- **not walked by anything**, which is what
  this file closes.  It was named as still-open in PR #236's own "not proven
  here" list ("no test asserts the ``standalone_kept`` event").

That gap mattered more than one missing event name.  ``COO-DECISION
20260829_0542`` rules that the standalone map is NOT consumed, and item 4 of
it obliges this lane to hold that ruling with a test.  The tripwire this lane
already built (``test_gm_standalone_map_is_not_chat_writable``) guards the
FILE.  Nothing guarded the LOGIN: the call site could have spent the entry,
or labelled a standalone grant ``consumed``, and every existing test would
still have been green -- the two outcomes differ only in an event string and
in whether a file on disk still has a line in it.

GATE-WALK (``COO-DECISION 20260829_0742``), branches this file walks:

* ``STANDALONE_NOT_CONSUMED`` at the login call site -- walked, with the
  standalone config pinned to a temp file so the branch is REACHED and not
  merely accepted.
* the resync, visit and no-GM-status consequences of that branch -- walked.
* ``CONSUMED`` -- walked here too, as the falsifier: without it a test that
  asserts "the entry is still on disk" cannot show it can tell a spent entry
  from a kept one.

Branches this file does NOT walk, and why:

* ``CONSUME_FAILED`` and ``NOTHING_STAGED`` -- reached by the two files named
  above; not repeated here.
* the refused-destination restore -- unreachable from a standalone grant by
  construction, since ``override_consumed_scene`` stays ``None`` when no
  entry was taken off disk.  There is nothing to give back, and this file
  asserts that silence rather than pretending to walk the branch.

Production-call shape: every login here goes through ``state.dispatch`` on
real client packets.  No test in this file calls
``consume_login_scene_override`` itself -- the offline file owns that.
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

from dataclasses import replace  # noqa: E402

from pirateforce_foundation import world_scene_entry  # noqa: E402
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

# Prison Exile Island, the same destination the sibling files drive: a real
# scene with a pinned spawn, not home, so an arrival there is visible.
KNOWN_SCENE_ID = 2


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GmStandaloneLoginSceneAtLoginTests(unittest.TestCase):
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

    # ----- harness ---------------------------------------------------------

    def _write_configs(self, gm_list, gm_map, standalone_map):
        """All THREE configs, always.

        Pinning the standalone file even when it is empty is the point of
        this harness: left unpinned it resolves to the repo-relative default
        path, so the outcome of every test below would depend on whether the
        machine running it happens to have an operator's file there.
        """
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

    def _login_and_start(self, token, *, selector=None):
        """One full login through the real dispatcher.

        Returns the state, the selector, and the actions the START_GAME
        dispatch produced -- the GM state frame is an ACTION, not an event,
        so a test that only reads ``state.events`` cannot see whether GM
        status was handed out.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        with mock.patch.dict(gm_accounts.os.environ, self._env()):
            with contextlib.redirect_stdout(io.StringIO()):
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
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state, selector, actions

    def _target_pos_pc(self, xyz, heading=0.0):
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
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.u8tag(0x0B, 0)
        )

    def _step(self, state, xyz=(10.0, 20.0, 30.0)):
        with contextlib.redirect_stdout(io.StringIO()):
            return state.dispatch(
                self.legacy.parse_outer(self._target_pos_pc(xyz))
            )

    def _standalone_map(self):
        return json.loads(self.standalone_path.read_text(encoding="utf-8"))[
            login_scene_override.STANDALONE_JSON_KEY
        ]

    def _gm_map(self):
        return json.loads(self.overrides_path.read_text(encoding="utf-8"))[
            "gm_login_scene"
        ]

    # ----- the branch nothing had walked -----------------------------------

    def test_a_standalone_grant_reaches_the_scene_and_names_itself_kept(self):
        """The whole branch, end to end, on an account that is NOT a GM."""
        self._write_configs([], {}, {"plain_tester": KNOWN_SCENE_ID})
        state, _selector, _actions = self._login_and_start("plain_tester")

        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", state.events,
        )
        # The event that would mean the entry was SPENT must be absent, and
        # so must the one that means the call site could not spend it.  Both
        # are asserted by name: "kept is present" alone would still hold if
        # the call site emitted two of them.
        self.assertNotIn(
            f"gm_login_scene_override_consumed_{KNOWN_SCENE_ID}", state.events,
        )
        self.assertNotIn(
            "gm_login_scene_override_consume_failed", state.events,
        )
        # Reached, not merely accepted: the character is standing in the
        # arrival an independent resolve produces for that scene.
        stored = self.store.get_character(state.foundation.selected.id)
        expected = world_scene_entry.resolve_entry(
            replace(stored.position, scene_id=KNOWN_SCENE_ID),
            emit=lambda _line: None,
        ).position
        self.assertEqual(state.foundation.selected.position, expected)
        self.assertNotEqual(
            expected, stored.position,
            "the arrival and the untouched row must differ, or this test "
            "cannot tell a granted scene from a login that went home",
        )

    def test_the_standalone_entry_survives_the_login_that_used_it(self):
        """``COO-DECISION 20260829_0542``, held at the call site.

        Two independent witnesses, because either alone is weak: the file on
        disk still carries the line, AND a SECOND login by the same account
        is granted the same scene again.  A call site that spent the entry
        would pass neither; one that rewrote the file with the same content
        would pass the first and fail the second.
        """
        self._write_configs([], {}, {"plain_tester": KNOWN_SCENE_ID})
        before = self.standalone_path.read_bytes()

        first, selector, _actions = self._login_and_start("plain_tester")
        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            first.events,
        )

        self.assertEqual(self.standalone_path.read_bytes(), before)
        self.assertEqual(self._standalone_map(), {"plain_tester": KNOWN_SCENE_ID})

        second, _selector, _actions = self._login_and_start(
            "plain_tester", selector=selector,
        )
        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            second.events,
        )
        self.assertEqual(
            second.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )

    def test_a_gm_gated_entry_is_still_spent_by_its_login(self):
        """The falsifier for the test above, walked through the same harness.

        Same dispatcher, same scene, same two witnesses -- and the opposite
        answer on both.  Without this test, "the entry is still there" would
        be a claim this file has no way to fail.
        """
        self._write_configs(
            ["gm_runner"], {"gm_runner": KNOWN_SCENE_ID}, {},
        )
        state, selector, _actions = self._login_and_start("gm_runner")

        self.assertIn(
            f"gm_login_scene_override_consumed_{KNOWN_SCENE_ID}", state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertEqual(self._gm_map(), {})

        second, _selector, _actions = self._login_and_start(
            "gm_runner", selector=selector,
        )
        self.assertEqual(
            [event for event in second.events
             if event.startswith("gm_login_scene_override_")],
            [],
        )
        self.assertNotEqual(
            second.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )

    def test_a_standalone_login_is_a_visit_like_any_other_override(self):
        """The visit rule is guarded on the override, not on which map gave it.

        This is the branch where getting it wrong would be worst.  A
        standalone entry is re-granted on EVERY login, so a durable write
        here would not merely outlive one login -- the row and the config
        would agree with each other forever, and the day an operator removes
        the line the character stays in a scene it may hold no return ticket
        for (``CHARTER-02`` rule 2).
        """
        self._write_configs([], {}, {"plain_tester": KNOWN_SCENE_ID})
        state, _selector, _actions = self._login_and_start("plain_tester")
        character_id = state.foundation.selected.id
        before = self.store.get_character(character_id).position

        moved = (444.0, 555.0, 666.0)
        self._step(state, xyz=moved)

        row = self.store.get_character(character_id).position
        self.assertEqual(row, before, "a standalone login is a visit too")
        self.assertNotEqual(row.scene_id, KNOWN_SCENE_ID)
        self.assertIn(
            "gm_login_scene_override_visit_no_durable_write_scene_"
            f"{KNOWN_SCENE_ID}",
            state.events,
        )
        # In memory the step is still tracked -- withholding the row must not
        # blind the session to its own player.
        position = state.foundation.selected.position
        self.assertEqual(position.scene_id, KNOWN_SCENE_ID)
        self.assertEqual((position.x, position.y, position.z), moved)

    def test_a_standalone_entry_grants_a_scene_and_no_gm_status(self):
        """The lane's first rule, measured on the path that could break it.

        ``gm_login_scene_standalone.json`` is the one config in this lane
        that grants something to an account NOT listed in ``gm_accounts``.
        If listing an account there also handed out GM status, the standalone
        map would be a way to become a GM without being one -- so the frame
        that carries GM status is checked as an ACTION, which is where it
        actually travels, and the GM-listed control shows the assertion can
        fail.
        """
        self._write_configs([], {}, {"plain_tester": KNOWN_SCENE_ID})
        state, _selector, actions = self._login_and_start("plain_tester")

        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertEqual(
            [action[0] for action in actions
             if action[0] == "GM_UPDATE_STATE_AFTER_LOGIN"],
            [],
        )
        with mock.patch.dict(gm_accounts.os.environ, self._env()):
            self.assertFalse(gm_accounts.is_gm_account("plain_tester"))

        # The control: the same harness DOES hand the frame to a listed GM,
        # so the emptiness above is a measurement rather than a hole in it.
        self._write_configs(["gm_runner"], {}, {})
        gm_state, _selector, gm_actions = self._login_and_start("gm_runner")
        self.assertEqual(
            [event for event in gm_state.events
             if event.startswith("gm_login_scene_override_")],
            [],
            "this control must reach the GM frame without any override",
        )
        self.assertEqual(
            [action[0] for action in gm_actions
             if action[0] == "GM_UPDATE_STATE_AFTER_LOGIN"],
            ["GM_UPDATE_STATE_AFTER_LOGIN"],
        )


if __name__ == "__main__":
    unittest.main()
