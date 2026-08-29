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

* BOTH returns that produce ``STANDALONE_NOT_CONSUMED`` -- walked.  The
  outcome has two sources and they are different code: the non-GM shortcut
  in ``consume_login_scene_override``, and ``_ask_the_standalone_map`` for a
  LISTED GM whose scene came from the standalone map because the GM-gated
  file has no entry for them.  An earlier version of this file walked only
  the first, so a regression that mislabelled the second would have been
  invisible here -- measured by pf-adversary, which flipped that return to
  ``CONSUMED`` and watched all five tests stay green.
* the refused-destination REFUSAL, reached from a standalone grant -- walked,
  and it is why the restore below is asserted rather than assumed.

Branches this file does NOT walk, and why:

* ``CONSUME_FAILED`` and ``NOTHING_STAGED`` -- reached by the two files named
  above; not repeated here.
* the refused-destination RESTORE -- unreachable from a standalone grant,
  because ``override_consumed_scene`` stays ``None`` when no entry was taken
  off disk.  That reason is prose, and prose is not a guard: pf-adversary
  measured a one-line mutation (setting ``override_consumed_scene`` inside
  the standalone branch) that leaves the whole 645-test GM suite green and
  turns the restore into a write of a NEVER-STAGED entry into the GM-gated
  file, which is the chat-writable one.  So this file no longer states the
  reason -- it asserts the consequence, in
  ``test_a_refused_standalone_destination_writes_nothing_to_the_gm_map``.
* the caller-side ``except (ValueError, OSError, TypeError)`` at the consume
  call, and the frame-resync ``refused`` / ``length_drift`` branches -- not
  reached by anything in this file, and not claimed to be.

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
        passes neither.

        WHAT THESE TWO WITNESSES DO NOT CATCH, stated because an earlier
        version of this docstring claimed the opposite and pf-adversary
        measured it false: a call site that DELETES the line, writes the
        file, then writes it back with identical content passes BOTH.  That
        is a real regression shape -- it makes the standalone file a write
        target, and any reader inside that window sees the entry gone -- and
        nothing in this file would go red for it.  Catching it needs a
        witness these tests do not have (a write watch on the path, or an
        open-for-write count), so it is named here rather than implied away.
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

    # ----- the second source of the same outcome ---------------------------

    def test_a_listed_gm_can_be_answered_by_the_standalone_map_too(self):
        """The OTHER return that produces ``STANDALONE_NOT_CONSUMED``.

        ``get_login_scene_override`` consults the GM-gated map only for a
        listed GM, then falls through to the standalone map for EVERYONE,
        GMs included.  So a listed GM with no GM-gated entry and a standalone
        one is answered by the standalone map -- and that answer comes back
        through ``_ask_the_standalone_map``, a different return statement in
        a different function from the non-GM shortcut every other test in
        this file walks.

        pf-adversary measured the cost of missing it: flipping that return to
        ``CONSUMED`` left all five original tests green, so the file's own
        stated purpose -- "the call site could have labelled a standalone
        grant consumed and every existing test would still be green" -- did
        not hold for half of the outcome it names.

        The GM state frame is asserted present here on purpose: it shows the
        two decisions are independent.  Being a GM is what grants the frame;
        it is not what decided which map answered.
        """
        self._write_configs(["gm_runner"], {}, {"gm_runner": KNOWN_SCENE_ID})
        before = self.standalone_path.read_bytes()

        state, selector, actions = self._login_and_start("gm_runner")

        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_consumed_{KNOWN_SCENE_ID}", state.events,
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )
        self.assertEqual(self.standalone_path.read_bytes(), before)
        self.assertEqual(
            [action[0] for action in actions
             if action[0] == "GM_UPDATE_STATE_AFTER_LOGIN"],
            ["GM_UPDATE_STATE_AFTER_LOGIN"],
        )

        second, _selector, _actions = self._login_and_start(
            "gm_runner", selector=selector,
        )
        self.assertIn(
            f"gm_login_scene_override_standalone_kept_{KNOWN_SCENE_ID}",
            second.events,
        )

    # ----- the branch whose reason used to be the only guard ---------------

    def test_a_refused_standalone_destination_writes_nothing_to_the_gm_map(
        self,
    ):
        """The consequence, asserted, of a branch this file does not walk.

        When a destination is refused, the call site gives the staged entry
        back -- but only when THIS login took one off disk, which a standalone
        grant never does.  That "never" was written as prose in the GATE-WALK
        paragraph above, and pf-adversary showed prose is not a guard: setting
        ``override_consumed_scene`` inside the standalone branch is one line,
        leaves the entire GM suite green, and makes the restore write an entry
        that was NEVER STAGED into ``gm_login_scene.json``.

        Why that file and not any other: it is the GM-gated one, the one a
        chat ``/warp`` writes, and ``restore_login_scene`` deliberately skips
        the allowlist check on the stated ground that it "only ever writes a
        value that was already in this file, or deletes one".  Under that
        mutation the ground is false.  A phantom entry there is invisible to
        this lane's standalone tripwire (wrong file) and activates the day the
        account is added to ``gm_accounts.json``.

        Scene 17 is the destination because it is in the committed catalog --
        so the config used to load -- and pinned ``login_entry_allowed=False``,
        so the refusal is the real one and not a fixture trick.

        ~~NOT A CLAIM THAT THIS LOGIN IS FINE.  It is refused, it sends no
        actions at all, and because the standalone entry is never consumed
        the client's retry is refused again, every time, until someone
        hand-edits the file.~~  **CLOSED IN ROUND qq0i9u.**  That paragraph
        described the outcome this file was pinning, and the ASK-COO letter
        of 2026-08-29T09:06+07:00 it pointed at said the lane would walk
        option (a) if no answer arrived by the next round.  None did, so
        ``gm/login_scene_admission.py`` now refuses such an entry when the
        map is READ: the account logs in at its own row instead of being
        locked out of the game, and the console names the entry.

        The blast-radius assertions this test was written for are kept
        WORD FOR WORD -- refusing an entry still may not touch the GM-gated
        file -- because the mutation they kill (setting
        ``override_consumed_scene`` inside the standalone branch, which
        makes the restore write a phantom entry into the file a chat
        ``/warp`` can act on) is a mutation of the code, not of the config,
        and would survive this change untouched.
        """
        refusal_scene = 17
        self._write_configs([], {}, {"plain_tester": refusal_scene})
        gm_map_before = self.overrides_path.read_bytes()
        standalone_before = self.standalone_path.read_bytes()

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            state, _selector, actions = self._login_and_start("plain_tester")

        # NOT kept, NOT applied, NOT refused at the scene -- refused at the
        # map, before any of that could happen.
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_standalone_kept_")
             or event.startswith("gm_login_scene_override_applied_")],
            [],
        )
        self.assertNotIn("world_scene_entry_refused_no_reply", state.events)
        self.assertIn("gm_login_scene_override_consume_failed", state.events)
        self.assertIn(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN,
            stderr.getvalue(),
        )

        # The account is IN THE GAME, which is the whole point of the
        # change: yesterday this login sent nothing at all, and so did
        # every retry after it.
        self.assertNotEqual(actions, [], "an admissible-config login replies")
        self.assertEqual(state.foundation.selected.position.scene_id, 1)

        # The guard the GATE-WALK paragraph used to only assert in words.
        self.assertEqual(self.overrides_path.read_bytes(), gm_map_before)
        self.assertEqual(self._gm_map(), {})
        self.assertEqual(self.standalone_path.read_bytes(), standalone_before)
        # ...and the silence that goes with it, by name rather than by
        # "no override events at all", which would also hold if the whole
        # override path had been skipped.
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_restored_after_")
             or event.startswith("gm_login_scene_override_lost_to_refusal_")],
            [],
        )

    def test_the_second_login_after_a_refused_entry_is_the_same_as_the_first(
        self,
    ):
        """The lockout, pinned as absent rather than described as fixed.

        The defect was never one bad login -- it was that the standalone map
        is not consumed, so the client's retry met the same wall, forever.
        A fix that only made login #1 survive would leave a tester staring
        at a door that opens once.  Both logins must come out the same, and
        both must come out inside the game.
        """
        self._write_configs([], {}, {"plain_tester": 17})

        with contextlib.redirect_stderr(io.StringIO()):
            first, selector, first_actions = self._login_and_start(
                "plain_tester"
            )
            second, _selector, second_actions = self._login_and_start(
                "plain_tester", selector=selector
            )

        for state, actions in ((first, first_actions), (second, second_actions)):
            self.assertNotEqual(actions, [])
            self.assertEqual(state.foundation.selected.position.scene_id, 1)
            self.assertIn(
                "gm_login_scene_override_consume_failed", state.events
            )


if __name__ == "__main__":
    unittest.main()
