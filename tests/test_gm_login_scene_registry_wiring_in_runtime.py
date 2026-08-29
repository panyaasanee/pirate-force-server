"""The boot snapshot reaches lane GM's login-scene calls THROUGH runtime.py.

``CORE-REQUEST-GM-036`` (lane GM, round ``7hfrt0``): lane GM landed a
``scene_registry=`` keyword on every hop of both login-scene chains, and
asked chief to pass ``runtime.py``'s boot snapshot at the three call sites
in chief's file -- the consume at login, the chat-command factory, and the
restore inside ``_put_back_consumed_override``.

WHY LANE GM'S OWN SUITE CANNOT PROVE THIS.  Their
``TheChatCommandCarriesItAllTheWayDownTests`` calls
``make_gm_chat_command_action`` ITSELF with the keyword -- it proves the
chain below the call site, and it is green on a tree where runtime.py does
not pass the keyword at all (measured on main before this round's wiring:
3 passed, unwired).  So this file drives the REAL dispatcher and grades on
the one fact the wiring changes: with a registry supplied, the registry
FILE is never read again after boot.

THE PROOF SHAPE differs by direction, because the lane's rule does
("gm/login_scene_stage.py: the FILE decides what may be written, the
snapshot may refuse on top of that"):

* READ paths (the consume at login, the restore) -- ``load_scene_registry``
  is patched to RAISE after boot, so a green test is a login that worked
  end to end while the only way to read the registry file was an explosion:
  every judgement came from the snapshot.
* the WRITE path (/warp) -- staging consults the file BY DESIGN, so zero
  file reads is not the fact to pin.  What the wiring adds there is the
  snapshot's power to refuse AT THE KEYBOARD a scene the file admits, so
  that is what the test drives.

On the unwired tree each test is red (the fresh read raises, the override
dies as ``consume_failed``, or the /warp the snapshot should have refused
lands in the file), which is the mutation kill for deleting any one of the
three ``scene_registry=`` arguments.

Not claimed: anything client-observable.  Wire/DB and console only.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
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

# Same destination the registry-authority file uses: pinned, spawned,
# allowed at login in the committed registry, and not the home scene.
STAGED_SCENE_ID = 2
HOME_SCENE_ID = 1


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _registry_refusing(scene_id: int) -> world_scene_travel.SceneRegistry:
    """The real registry with one destination shut against login.

    Same builder as tests/test_gm_login_scene_override_registry_authority.py:
    derived from the committed file so the snapshot differs from the disk in
    exactly the one field under test.
    """
    live = world_scene_travel.load_scene_registry()
    return world_scene_travel.SceneRegistry(
        destinations=tuple(
            replace(destination, login_entry_allowed=False)
            if destination.n_id == scene_id else destination
            for destination in live.destinations
        )
    )


def _chat_payload(message: str, speaker: str = "") -> bytes:
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


def _synthetic_chat_pc(legacy, payload: bytes) -> bytes:
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


def _explode(*_args, **_kwargs):
    raise AssertionError(
        "the scene registry FILE was read after boot -- the wiring under "
        "test exists so every read goes to the process snapshot instead"
    )


class RegistrySnapshotWiringTests(unittest.TestCase):
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

    def _gm_map(self):
        return json.loads(self.overrides_path.read_text(encoding="ascii"))[
            "gm_login_scene"
        ]

    def _boot(self, token, snapshot=None):
        """make_state_class BEFORE any explode patch: the boot-time read.

        ``snapshot`` installed only across ``make_state_class``, the same
        shape as tests/test_gm_login_scene_override_registry_authority.py:
        the file on disk stays untouched, so a disagreement between the two
        readings is manufactured in the PROCESS alone.
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
        return state_type(token)

    def _login_and_start(self, state, token):
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
        return state

    def _no_file_reads(self):
        return mock.patch.object(
            world_scene_travel, "load_scene_registry", side_effect=_explode,
        )

    # ----- call site 1: the consume at login ------------------------------

    def test_a_staged_login_reads_the_registry_file_zero_times(self):
        """The entry is judged, spent and applied on the snapshot alone.

        Red on the unwired tree: the fresh read explodes and the override
        comes back ``consume_failed`` instead of ``consumed``.
        """
        self._write_configs(
            ["wire_tester"], {"wire_tester": STAGED_SCENE_ID}, {},
        )
        state = self._boot("wire_tester")

        with self._no_file_reads():
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    self._login_and_start(state, "wire_tester")

        self.assertIn(
            f"gm_login_scene_override_consumed_{STAGED_SCENE_ID}",
            state.events,
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, STAGED_SCENE_ID,
        )
        # Spent means spent: the entry left the file exactly as before.
        self.assertEqual(self._gm_map(), {})

    def test_one_refused_entry_takes_every_override_down_destroying_nothing(
        self,
    ):
        """The accepted cost of snapshot-judged reads, pinned on purpose.

        Two accounts staged; the boot snapshot bars only the OTHER one's
        destination (the file on disk admits it -- registry widened after
        boot, or the line was hand-written).  The whole-file loader then
        refuses the file on that one line, so THIS account's perfectly
        placeable override dies with it as ``consume_failed`` until the
        file and the running registry agree again.

        On the unwired tree the same fixture gave this account its scene
        (per-account isolation, disk-judged) -- so this test is the honest
        record that the isolation was traded away, and of everything that
        must survive the trade: nothing destroyed, nobody locked out, and
        the console not silent (pf-adversary, this round, defect 2).
        """
        self._write_configs(
            ["wire_tester", "bystander"],
            {"wire_tester": STAGED_SCENE_ID, "bystander": 278},
            {},
        )
        snapshot = _registry_refusing(278)
        state = self._boot("wire_tester", snapshot=snapshot)

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            with contextlib.redirect_stderr(io.StringIO()):
                self._login_and_start(state, "wire_tester")

        self.assertIn(
            "gm_login_scene_override_consume_failed", state.events,
        )
        self.assertNotIn(
            f"gm_login_scene_override_consumed_{STAGED_SCENE_ID}",
            state.events,
        )
        # Nothing destroyed: both entries still on disk, byte for byte.
        self.assertEqual(
            self._gm_map(), {"wire_tester": STAGED_SCENE_ID, "bystander": 278},
        )
        # Nobody locked out, and not silent.
        self.assertEqual(
            state.foundation.selected.position.scene_id, HOME_SCENE_ID,
        )
        self.assertIn(
            "GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED", stdout.getvalue(),
        )

    # ----- call site 2: the chat-command factory --------------------------

    def test_a_warp_the_snapshot_refuses_is_refused_at_the_keyboard(self):
        """The snapshot refuses a write ON TOP of a file that admits it.

        The registry FILE on disk still says scene 2 is enterable (nothing
        here edits it); only the process booted with a reading that bars
        it.  Wired, ``/warp 2`` is refused at the moment it is typed --
        which is the whole point lane GM gave for the parameter: the
        refusal happens where a person is standing, not at a login this
        lane cannot speak to.

        Red on the unwired tree: only the file is asked, the file admits,
        and the entry lands in the map for the next login to refuse.
        """
        self._write_configs(["wire_tester"], {}, {})
        snapshot = _registry_refusing(STAGED_SCENE_ID)
        state = self._boot("wire_tester", snapshot=snapshot)
        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(io.StringIO()):
                self._login_and_start(state, "wire_tester")

        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                state.dispatch(self.legacy.parse_outer(
                    _synthetic_chat_pc(
                        self.legacy,
                        _chat_payload(f"/warp {STAGED_SCENE_ID}"),
                    )
                ))

        self.assertEqual(self._gm_map(), {})
        self.assertNotIn(
            f"gm_chat_action_warp_staged_login_scene_{STAGED_SCENE_ID}",
            state.events,
        )
        # THE ROUTE REALLY RAN.  Without these two, a route that never
        # composes anything (rate-limit leak, gate stand-down, chat-parse
        # regression) leaves the map empty and this test green -- measured
        # by pf-adversary with the factory stubbed to return None
        # (scar #2, green-because-it-never-got-there).
        self.assertIn("gm_chat_action_accepted_warp", state.events)
        self.assertIn(
            "gm_chat_action_warp_stage_refused_scene_has_no_login_entry",
            state.events,
        )

    # ----- call site 3: the restore inside _put_back_consumed_override ----

    def test_a_probe_refusal_gives_the_entry_back_without_reading_the_file(
        self,
    ):
        """The undo is judged by the same registry as the take.

        The probe and lane GM's admission read the same snapshot now, so a
        registry object cannot make the probe refuse what the admission
        passed -- the branch is defence in depth against the two readers
        drifting apart.  To walk it, the probe alone is refused here by a
        targeted patch (only the silenced-emit probe call; the placement
        call underneath runs the real resolver).

        Red on the unwired tree: the restore's fresh read explodes, and
        AssertionError is not in ``_put_back_consumed_override``'s catch.
        """
        self._write_configs(
            ["wire_tester"], {"wire_tester": STAGED_SCENE_ID}, {},
        )
        state = self._boot("wire_tester")
        real_resolve = world_scene_entry.resolve_entry

        def probe_refuses(stored, **kwargs):
            if "emit" in kwargs and stored.scene_id == STAGED_SCENE_ID:
                raise world_scene_entry.SceneEntryRefused(
                    world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
                    "probe refused by this test",
                )
            return real_resolve(stored, **kwargs)

        with self._no_file_reads():
            with mock.patch.object(
                world_scene_entry, "resolve_entry",
                side_effect=probe_refuses,
            ):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self._login_and_start(state, "wire_tester")

        self.assertIn(
            f"gm_login_scene_override_consumed_{STAGED_SCENE_ID}",
            state.events,
        )
        self.assertIn(
            "gm_login_scene_override_restored_after_refusal_"
            f"{STAGED_SCENE_ID}",
            state.events,
        )
        # Back on disk with the value it had, written under the snapshot's
        # judgement -- the whole point of wiring call site 3.
        self.assertEqual(self._gm_map(), {"wire_tester": STAGED_SCENE_ID})
        # And the character is in the game at its own row, not locked out.
        self.assertEqual(
            state.foundation.selected.position.scene_id, HOME_SCENE_ID,
        )
        self.assertIn("GM_LOGIN_SCENE_OVERRIDE_REFUSED", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
