"""The consume `cause` reaches the operator console THROUGH runtime.py.

``CORE-REQUEST-GM-037`` (lane GM, round ``1fq5yf``): lane GM landed a
``cause`` field on ``ConsumeResult`` -- a closed vocabulary of literals cut
on the remedy axis -- and asked chief to stop printing the placeholder
``cause=not_carried_by_the_outcome`` in ``runtime.py``'s ``CONSUME_FAILED``
arm and print ``override_result.cause`` instead.

WHY LANE GM'S OWN SUITE CANNOT PROVE THIS.  Their 58 tests in
``test_gm_login_scene_consume_cause.py`` drive the consume module itself;
they are green on a tree where runtime.py still prints the placeholder
(measured on main before this round's wiring).  So this file drives the
REAL dispatcher through a full login and grades on the console line, the
one artifact the wiring changes.

THE PROOF SHAPE: two fixtures that fail the consume for two DIFFERENT
causes, asserted against the same print.  A single fixture would stay green
under ``f"cause={CAUSE_CONFIG_REJECTED}"`` hardcoded at the call site; two
distinct tokens on one line can only come from reading the result.  The
mutation kills, measured on this round's tree:

* revert the print to the placeholder literal -- both cause tests red;
* hardcode either token at the call site -- the other cause test red;
* delete the print -- both cause tests red;
* inline the attribute access into the print guard (pf-adversary D2, this
  round) -- the lost-cause test red: the AttributeError must escape
  ``dispatch``, not drown in ``except Exception: pass``.

Round ``npo898`` added the "and then what" half, after chief's 19:24 reply
carried back where that escape LANDS (a dead game listener thread under a
live login port).  Measured kills for the test added there:

* ``ConsumeResultMisuse`` reduced to a plain ``AttributeError`` -- red,
  the error leaves ``dispatch`` again;
* the attribute read inlined into the print guard -- red, the events row
  stops naming the class.

Not claimed: anything client-observable.  Wire/console only -- no byte of
the cause reaches a client, and no test here says otherwise.
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

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_consume  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm.dispatch import (  # noqa: E402
    reset_rate_limit_state_for_tests,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# Same destination the registry-wiring file uses: pinned, spawned, allowed
# at login in the committed registry, and not the home scene.
STAGED_SCENE_ID = 2
HOME_SCENE_ID = 1

CONSOLE_PREFIX = (
    "GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED effect=login_at_own_row cause="
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class ConsumeCauseWiringTests(unittest.TestCase):
    def setUp(self):
        reset_rate_limit_state_for_tests()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.accounts_path = Path(self.tmp.name) / "gm_accounts.json"
        self.overrides_path = Path(self.tmp.name) / "gm_login_scene.json"
        self.standalone_path = (
            Path(self.tmp.name) / "gm_login_scene_standalone.json"
        )
        env_pin = mock.patch.dict(gm_accounts.os.environ, {
            gm_accounts.ENV_OVERRIDE: str(self.accounts_path),
            login_scene_override.ENV_OVERRIDE: str(self.overrides_path),
            login_scene_override.STANDALONE_ENV_OVERRIDE: str(
                self.standalone_path
            ),
        })
        env_pin.start()
        self.addCleanup(env_pin.stop)
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["wire_tester"]}), encoding="ascii",
        )
        self.standalone_path.write_text(
            json.dumps({login_scene_override.STANDALONE_JSON_KEY: {}}),
            encoding="ascii",
        )
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
        field_mobs.load_roster()
        # gm/commands.py's DEFAULT_LOG_PATH resolves against the process
        # CWD (same note as tests/test_gm_chat_command_dispatch_wiring.py).
        import os
        self._owd = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self._owd)

    def _boot(self, token, snapshot=None):
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
        return state_type(token)

    def _login_and_start_capturing_console(self, state, token):
        console = io.StringIO()
        with contextlib.redirect_stdout(console):
            with contextlib.redirect_stderr(io.StringIO()):
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc(token)
                ))
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._V25_REAL_CREATE_PC
                ))
                character = self.store.list_characters(
                    state.foundation.account_id
                )[-1]
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(character.selector)
                ))
        return console.getvalue()

    def _the_consume_failed_lines(self, console_text):
        return [
            line for line in console_text.splitlines()
            if line.startswith("GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED")
        ]

    def _assert_failed_with_cause(self, state, console_text, cause):
        lines = self._the_consume_failed_lines(console_text)
        self.assertEqual(
            1, len(lines),
            f"expected exactly one CONSUME_FAILED line, got {lines!r}",
        )
        self.assertEqual(CONSOLE_PREFIX + cause, lines[0])
        self.assertNotIn("not_carried_by_the_outcome", console_text)
        self.assertIn(
            "gm_login_scene_override_consume_failed", state.events,
        )
        # The failed override costs the override, never the login: the
        # character stands at its own row's scene.
        self.assertEqual(
            HOME_SCENE_ID, state.foundation.selected.position.scene_id,
        )

    # ----- cause 1: the loader refuses the file ---------------------------

    def test_a_malformed_override_file_prints_config_rejected(self):
        """Red on the unwired tree: the line says the placeholder word.

        Fixture measured against the module before writing this test:
        malformed JSON in ``gm_login_scene.json`` comes back
        ``CONSUME_FAILED`` with ``cause=config_rejected``.
        """
        self.overrides_path.write_text("{not json", encoding="ascii")
        state = self._boot("wire_tester")
        console = self._login_and_start_capturing_console(
            state, "wire_tester",
        )
        self._assert_failed_with_cause(
            state, console, login_scene_consume.CAUSE_CONFIG_REJECTED,
        )

    # ----- the loud-failure contract, enforced instead of commented -------

    def test_a_result_that_lost_its_cause_raises_out_of_dispatch(self):
        """A missing ``cause`` is an AttributeError PAST the print guard.

        The GM letter forbids ``getattr(..., "cause", ...)``: a
        ConsumeResult that lost the field must raise, not fall back to a
        placeholder word.  pf-adversary (this round, D2) measured that the
        property lived only in a comment -- inlining the attribute access
        into the ``try: print(...) except Exception: pass`` guard kept
        every test green while turning the contract into silence.  This
        test is that missing mutation kill: the access must happen OUTSIDE
        the guard, so the error propagates out of ``dispatch`` instead of
        being swallowed (and instead of printing anything at all).

        The stub below is only reachable through the patch: at HEAD the
        real ConsumeResult cannot exist without a cause (constructor
        validation, ``__slots__``), so this is the in-repo-regression
        drill, not a live scenario.
        """
        class _ResultThatLostItsCause:
            scene_id = None
            outcome = login_scene_consume.CONSUME_FAILED
            # no `cause` attribute, deliberately

        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": {}}), encoding="ascii",
        )
        state = self._boot("wire_tester")
        from pirateforce_foundation import runtime as runtime_module
        console = io.StringIO()
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            return_value=_ResultThatLostItsCause(),
        ):
            with self.assertRaises(AttributeError):
                with contextlib.redirect_stdout(console):
                    with contextlib.redirect_stderr(io.StringIO()):
                        state.dispatch(self.legacy.parse_outer(
                            self.legacy._synthetic_client_login_pc(
                                "wire_tester",
                            )
                        ))
                        state.dispatch(self.legacy.parse_outer(
                            self.legacy._V25_REAL_CREATE_PC
                        ))
                        character = self.store.list_characters(
                            state.foundation.account_id
                        )[-1]
                        state.dispatch(self.legacy.parse_outer(
                            self.legacy._synthetic_start_game_pc(
                                character.selector,
                            )
                        ))
        # Loud means loud: no placeholder line, no half-printed line.
        self.assertEqual(
            [], self._the_consume_failed_lines(console.getvalue()),
        )

    def test_a_real_result_that_lost_its_cause_costs_the_override_only(self):
        """The SAME contract, on the object chief's call site really gets.

        Round `npo898`, consuming chief's reply of 19:24 item 1.  The stub
        above is a foreign class and answers "does the read happen outside
        the print guard".  It cannot answer "and then what", because at
        that point the process is already unwinding a thread this test
        never sees.

        This one passes a REAL ``ConsumeResult`` whose ``cause`` slot was
        never filled -- the in-repo regression shape a future return path
        could write -- and grades the three things an operator gets:

        * ``dispatch`` RETURNS (the game listener thread is not unwound);
        * nothing is printed for a lost field (no placeholder word, which
          is the contract the stub test above pins);
        * the events row NAMES the fault:
          ``gm_login_scene_override_lookup_failed_ConsumeResultMisuse``.

        Mutation kills measured this round: make ``ConsumeResultMisuse`` a
        plain ``AttributeError`` and this test raises out of ``dispatch``;
        inline the attribute read into the print guard and the events row
        reads ``..._consume_failed`` instead of naming the class.
        """
        lost = login_scene_consume.ConsumeResult.__new__(
            login_scene_consume.ConsumeResult
        )
        object.__setattr__(lost, "scene_id", None)
        object.__setattr__(
            lost, "outcome", login_scene_consume.CONSUME_FAILED,
        )

        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": {}}), encoding="ascii",
        )
        state = self._boot("wire_tester")
        from pirateforce_foundation import runtime as runtime_module
        with mock.patch.object(
            runtime_module, "consume_login_scene_override",
            return_value=lost,
        ):
            console = self._login_and_start_capturing_console(
                state, "wire_tester",
            )
        self.assertEqual([], self._the_consume_failed_lines(console))
        self.assertIn(
            "gm_login_scene_override_lookup_failed_ConsumeResultMisuse",
            state.events,
        )
        # And the person watching the console gets a line of their own --
        # named, not a placeholder cause.  Without this the round would
        # have traded a thread-killing traceback for total silence.
        self.assertIn(
            "GM_CONSUME_RESULT_LOST_FIELD field=cause "
            "effect=override_refused_login_at_own_row",
            console,
        )
        # The override is what was lost, not the login: the character is
        # standing at its own row's scene, same as every other failure.
        self.assertEqual(
            HOME_SCENE_ID, state.foundation.selected.position.scene_id,
        )

    # ----- cause 2: the disk admits, the running snapshot does not --------

    def test_a_snapshot_refused_entry_prints_registry_stale_since_boot(self):
        """A DIFFERENT token through the SAME print: the pass-through proof.

        The entry stages a scene the committed registry file admits, and
        the boot snapshot -- installed only across ``make_state_class``,
        same shape as the GM-036 wiring tests -- bars it.  The disk still
        admitting the row is what makes the honest remedy "restart", so
        the measured cause is ``registry_stale_since_boot``.
        """
        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": {"wire_tester": STAGED_SCENE_ID}}),
            encoding="ascii",
        )
        live = world_scene_travel.load_scene_registry()
        snapshot = world_scene_travel.SceneRegistry(
            destinations=tuple(
                replace(destination, login_entry_allowed=False)
                if destination.n_id == STAGED_SCENE_ID else destination
                for destination in live.destinations
            )
        )
        state = self._boot("wire_tester", snapshot=snapshot)
        console = self._login_and_start_capturing_console(
            state, "wire_tester",
        )
        self._assert_failed_with_cause(
            state, console,
            login_scene_consume.CAUSE_REGISTRY_STALE_SINCE_BOOT,
        )


if __name__ == "__main__":
    unittest.main()
