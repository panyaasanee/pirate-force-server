"""CHIEF-DECISION 20260829_0520 option A, driven through the REAL dispatcher.

An overridden login used to leave ``foundation.selected.position`` on the
character's STORED row while the teleport, the ActorAttr and the MovementAttr
all named the overridden scene.  Nothing in that handler read the stale value,
so it looked harmless -- but every LATER frame of the same session reads
``self.foundation.selected.position`` and never ``entry``:

* the census dispatch decides bg0001 / bg0002 / away-from-home from it
  (LANE-A's D1), and
* ``_checkpoint_exact_target`` stamps the row it writes with its ``scene_id``
  and ``scene_seq`` (LANE-A's D2) -- a checkpoint that mislabels WHERE a
  coordinate is, which is worse than no checkpoint at all.

This file proves the fix end to end, one test per consequence, plus the two
properties the fix must NOT break: a login with no override comes out with
every field of ``selected`` untouched, and the GM-gated entry is spent by
exactly one login (COO-DECISION 20260829_0441 item 2), which is why the call
site now calls ``consume_login_scene_override`` INSTEAD OF -- never beside --
``get_login_scene_override``.

The standalone map is deliberately not exercised for consumption here: it is
never consumed (COO-DECISION 20260829_0542), and
``tests/test_gm_login_scene_consume.py`` owns that half offline.
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

from pirateforce_foundation import world_population  # noqa: E402
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

# Prison Exile Island: a real destination with a pinned spawn and no ground
# extent, the same scene tests/test_gm_login_scene_override_wiring.py drives.
# It is NOT home, which is what makes the census consequence visible.
KNOWN_SCENE_ID = 2


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GmLoginSceneOverridePositionResyncTests(unittest.TestCase):
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
        self.overrides_path = Path(self.tmp.name) / "gm_login_scene.json"
        self.accounts_path = Path(self.tmp.name) / "gm_accounts.json"

    # ----- harness ---------------------------------------------------------

    def _write_configs(self, gm_accounts_value, overrides_value):
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": gm_accounts_value}), encoding="utf-8"
        )
        self.overrides_path.write_text(
            json.dumps({"gm_login_scene": overrides_value}), encoding="utf-8"
        )

    def _env(self):
        return {
            gm_accounts.ENV_OVERRIDE: str(self.accounts_path),
            login_scene_override.ENV_OVERRIDE: str(self.overrides_path),
        }

    def _login_and_start(self, token, *, selector=None, ready=True):
        """One full login through the real dispatcher, stdout swallowed."""
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
                state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(selector)
                ))
        state.runtime_ack_sent = ready
        state.welcome_message_sent = ready
        state.current_scene_music_sent = ready
        return state, selector

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

    # ----- the fix itself --------------------------------------------------

    def test_an_overridden_login_leaves_selected_naming_the_scene_it_reached(
        self,
    ):
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        state, _selector = self._login_and_start("gm_runner")

        self.assertIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", state.events,
        )
        self.assertIn(
            "gm_login_scene_override_selected_position_resynced_"
            f"{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )
        # Not merely the scene number: the whole resolved arrival, scene_seq
        # included.  resolve_entry() is the one authority on where this login
        # landed, and the teleport was built from the same object.
        self.assertEqual(
            state.foundation.selected.position.scene_seq,
            self.store.get_character(
                state.foundation.selected.id
            ).position.scene_seq,
            "the stored row's scene_seq is what resolve_entry passes through "
            "for a scene with a pinned spawn; a different value here would "
            "mean this test stopped comparing the resolved arrival",
        )

    def test_a_login_with_no_override_changes_no_field_of_selected(self):
        """The guard, not a formality: this path runs on every real login."""
        self._write_configs([], {})
        state, _selector = self._login_and_start("ordinary_player")

        stored = self.store.get_character(state.foundation.selected.id)
        self.assertEqual(state.foundation.selected.position, stored.position)
        self.assertEqual(state.foundation.selected, stored)
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_")],
            [],
        )

    # ----- D1: the census reads it ----------------------------------------

    def test_the_census_dispatch_sees_the_overridden_scene(self):
        """LANE-A's D1.

        The census dispatch picks its population from
        ``selected.position.scene_id``: home gets bg0001, scene 2 gets
        bg0002, anything else gets nothing at all by name.  Every actor in
        the bg0001 census is ENCODED with scene 1, so presenting as home
        while standing in scene 2 does not merely send a useless census --
        it delivers the dock NPCs into a map they do not belong to.

        Scene 2 is deliberately the destination here rather than a
        census-less scene: it makes the branch that fires observable
        (bg0002's own population, not silence), which a "nothing was sent"
        assertion could not tell apart from a census that simply failed.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        state, _selector = self._login_and_start("gm_runner")

        self.assertNotEqual(KNOWN_SCENE_ID, world_population.SCENE_ID)
        labels = [action[0] for action in self._step(state)
                  if action[0].startswith("WORLD_CENSUS_")]

        self.assertTrue(
            labels and all(
                label.startswith("WORLD_CENSUS_BG0002_") for label in labels
            ),
            f"expected only scene 2's own census, got {labels}",
        )
        # The home census would come back under the unprefixed labels, which
        # is exactly the bug: dock NPCs encoded with scene 1, delivered to a
        # client standing in scene 2.
        self.assertEqual(
            [label for label in labels
             if label.startswith("WORLD_CENSUS_INITIAL_")
             or label.startswith("WORLD_CENSUS_REAPPLY_")],
            [],
        )

    # ----- D2: the checkpoint stamps it -----------------------------------

    def test_the_checkpoint_stamps_the_scene_the_player_is_actually_in(self):
        """LANE-A's D2.

        ``_checkpoint_exact_target`` labels the coordinate it writes with
        ``selected.position.scene_id``.  Measured before this fix: an
        overridden login walking one step wrote its new XY under scene 1 --
        a durable row claiming the player is somewhere they have never been.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        state, _selector = self._login_and_start("gm_runner")
        character_id = state.foundation.selected.id

        moved = (111.0, 222.0, 333.0)
        self._step(state, xyz=moved)

        row = self.store.get_character(character_id).position
        self.assertEqual(row.scene_id, KNOWN_SCENE_ID)
        self.assertEqual((row.x, row.y, row.z), moved)
        self.assertEqual(
            state.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )

    # ----- single use ------------------------------------------------------

    def test_the_entry_is_spent_by_the_first_login_and_the_second_is_ordinary(
        self,
    ):
        """COO-DECISION 20260829_0441 item 2, proven at the call site.

        The reader was REPLACED by the consumer, so this also proves the
        thing a reader-plus-consumer pair could not give: the login that
        spends the entry is the same login that receives the scene.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        first, selector = self._login_and_start("gm_runner")
        self.assertIn(
            f"gm_login_scene_override_consumed_{KNOWN_SCENE_ID}", first.events,
        )
        self.assertEqual(
            first.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )
        self.assertEqual(
            json.loads(self.overrides_path.read_text(encoding="utf-8"))[
                "gm_login_scene"
            ],
            {},
            "the staged entry has to be off disk, not merely unread",
        )

        second, _selector = self._login_and_start(
            "gm_runner", selector=selector
        )
        self.assertNotIn(
            f"gm_login_scene_override_applied_{KNOWN_SCENE_ID}", second.events,
        )
        self.assertEqual(
            [event for event in second.events
             if event.startswith("gm_login_scene_override_selected_")],
            [],
        )
        # Where the first login LEFT the character is where the second one
        # starts: the second login is ordinary, which means it reads the row
        # rather than an override, not that it goes home.
        self.assertEqual(
            second.foundation.selected.position,
            self.store.get_character(
                first.foundation.selected.id
            ).position,
        )


if __name__ == "__main__":
    unittest.main()
