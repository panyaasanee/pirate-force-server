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

from dataclasses import replace  # noqa: E402

from pirateforce_foundation import world_population  # noqa: E402
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
            # Pinned at a path inside this test's own temp dir that is never
            # written, so "no standalone entry" is a fact of the fixture.
            # Left unpinned it resolved to the repo-relative default
            # (`config/gm_login_scene_standalone.json`), and the no-override
            # control below -- which asserts `ordinary_player` gets no
            # override event at all -- would then have depended on whether
            # the machine running the suite happened to have an operator's
            # file there.  The standalone branch itself is walked by
            # tests/test_gm_login_scene_override_standalone_at_login.py.
            login_scene_override.STANDALONE_ENV_OVERRIDE: str(
                Path(self.tmp.name) / "no_standalone_map.json"
            ),
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
        # Not merely the scene number: the WHOLE resolved arrival, compared
        # against an independently resolved one rather than against a field
        # copied out of the same object.  An earlier version of this test
        # pinned scene_seq alone, which pf-adversary measured as
        # unfalsifiable: world_scene_travel.entry_fields() hardcodes
        # scene_seq=0 for every destination today, so that assertion held
        # for the resolved arrival and for the stale row alike.
        stored = self.store.get_character(state.foundation.selected.id)
        expected = world_scene_entry.resolve_entry(
            replace(stored.position, scene_id=KNOWN_SCENE_ID),
            emit=lambda _line: None,
        ).position
        self.assertEqual(state.foundation.selected.position, expected)
        self.assertNotEqual(
            expected, stored.position,
            "the two candidate positions must actually differ, or this test "
            "cannot tell the resolved arrival from the untouched row",
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

    def test_the_checkpoint_of_an_overridden_login_writes_no_durable_row(
        self,
    ):
        """LANE-A's D2, and the answer to what replaced it.

        ``_checkpoint_exact_target`` labels the coordinate it writes with
        ``selected.position.scene_id``.  Measured before this round: an
        overridden login walking one step wrote its new XY under scene 1 --
        a durable row claiming the player is somewhere they have never been.

        Resyncing the in-memory character alone would have fixed the LABEL
        and broken something worse, which pf-adversary measured on this
        round's own first half: the row would then be stamped with the
        overridden scene, and a SINGLE-USE override (COO-DECISION
        20260829_0441 item 2) would become a permanent relocation -- the
        next login carries no override and starts there anyway.  At scene
        278 (`sent_before=NO, return_ticket=REQUIRED`) that is a character
        who cannot walk home, which CHARTER-02 rule 2 calls damage.

        So an overridden login is a VISIT: the in-memory position tracks the
        player (nothing this session decides is stale), and no durable row
        is written for it at all.  The mislabelled row D2 reported is gone
        because there is no row.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        state, _selector = self._login_and_start("gm_runner")
        character_id = state.foundation.selected.id
        before = self.store.get_character(character_id).position

        moved = (111.0, 222.0, 333.0)
        self._step(state, xyz=moved)

        row = self.store.get_character(character_id).position
        self.assertEqual(row, before, "an override login is a visit")
        self.assertNotEqual(row.scene_id, KNOWN_SCENE_ID)
        self.assertIn(
            "gm_login_scene_override_visit_no_durable_write_scene_"
            f"{KNOWN_SCENE_ID}",
            state.events,
        )
        # In memory the step is tracked, scene and coordinates together --
        # withholding the row must not blind this session to its own player.
        self.assertEqual(
            state.foundation.selected.position.scene_id, KNOWN_SCENE_ID,
        )
        position = state.foundation.selected.position
        self.assertEqual((position.x, position.y, position.z), moved)
        # And the token that means "a durable write survived" stays silent.
        self.assertNotIn("gm_warp_position_confirmed", state.events)

    def test_an_ordinary_login_still_checkpoints_durably(self):
        """The control for the test above: the visit rule is scoped.

        Without this, "no row was written" would pass just as well against a
        checkpoint path that had stopped working for everybody.
        """
        self._write_configs([], {})
        state, _selector = self._login_and_start("ordinary_player")
        character_id = state.foundation.selected.id

        moved = (111.0, 222.0, 333.0)
        self._step(state, xyz=moved)

        row = self.store.get_character(character_id).position
        self.assertEqual((row.x, row.y, row.z), moved)
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_visit_")],
            [],
        )

    def test_an_inadmissible_destination_never_reaches_the_login_at_all(self):
        """Round qq0i9u: scene 17 is now refused when the config is READ.

        ~~The entry is spent before the destination can refuse it.~~  That
        was the shape of this test until this round, and the login it
        described -- config accepted, override applied, `resolve_entry`
        refuses, entry handed back -- is no longer reachable from a config
        file.  `gm/login_scene_admission.py` holds a hand-written entry to
        the same rule `stage_login_scene` has enforced since round 0z3kjx,
        so scene 17 is refused at the moment the map loads.

        WHY THE OLD SHAPE HAD TO GO rather than being kept as well: the
        refusal it pinned sends no reply, deliberately, so the client
        retries -- and the STANDALONE map is never consumed
        (`COO-DECISION 20260829_0542`), so the retry was refused the same
        way, forever.  One typo in a hand-edited file locked an account out
        of the game until somebody with shell access deleted the file.
        Measured through this dispatcher in round 38c4tv and asked in
        pf_bridge's ASK-COO letter of 2026-08-29T09:06+07:00; no answer
        came, and that letter named this as the option the lane would walk.

        What the tester gets instead, and what this test pins: the account
        LOGS IN, at its own stored row, and the console says which entry was
        refused and which scene ids are admissible.
        """
        refused_scene = 17
        self._write_configs(["gm_runner"], {"gm_runner": refused_scene})
        before = self.overrides_path.read_bytes()

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            state, _selector = self._login_and_start("gm_runner")

        # It logs in, and at home -- not into a scene, and not nowhere.
        self.assertNotIn("world_scene_entry_refused_no_reply", state.events)
        self.assertEqual(state.foundation.selected.position.scene_id, 1)
        self.assertEqual(
            [event for event in state.events
             if event.startswith("gm_login_scene_override_applied_")],
            [],
        )
        self.assertIn("gm_login_scene_override_consume_failed", state.events)

        # Loud, by the token a tester can grep, naming the way out.
        console = stderr.getvalue()
        self.assertIn(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN, console
        )
        self.assertIn("scene_id=17", console)
        # 14 joined the stageable set in LANE-A round vvy6q7; 126 joined it
        # (single-use only) in round R249 (chief, gate-red repair of
        # `pirate-force-server#332`, `CORE-REQUEST-GM-038`'s widening); 4
        # joined it in round bq4mst (COO-DECISION 20260830_1441); 10 joined
        # it in round 3t75jw, second door in the same queue; 5 joined it in
        # round l03cgh, third door, built+wired+opened in one round; 6
        # joined it in round fx0007, fourth door, same shape; 8 joined it in
        # round p4wire, fifth door, same shape; 3 joined it in round p7wm17,
        # sixth door, same shape; 7 joined it in round 78zayw, seventh door,
        # same shape; 9 joined it in round ir0lpw, eighth door, same shape;
        # 11 joined it this round (68mm02), ninth door, same shape --
        # elevated-risk row (the_two_interiors, shared only with scene 10).
        # Scene 17, the id this test actually drives, is still barred and
        # still refused either way.
        self.assertIn(
            "stageable=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 126, 278, "
            "997)",
            console)

        # And the operator's file is untouched: refusing to ACT on an entry
        # is not licence to edit it.
        self.assertEqual(self.overrides_path.read_bytes(), before)

    def test_a_refused_destination_still_gives_the_staged_entry_back(self):
        """The restore-after-refusal branch, kept alive on purpose.

        `runtime.py`'s handler puts a consumed entry back when the
        destination refuses (chief, round ngwnnj/R223).  The test above
        closed the CONFIG route into that handler, which would have left
        chief's code with no test walking it at all -- so this one reaches
        it at the seam that is still real: admission asks lane A's registry
        at the moment the map loads, `resolve_entry` asks it again -- and
        a registry that disagrees between those two readings, or any
        refusal reason admission does not model, lands here.  Narrow, and
        that is exactly why it must keep working -- nobody will be watching
        when it fires.

        THAT SEAM IS NOT "A FEW MICROSECONDS", which is what this docstring
        used to say and what `CORE-REQUEST-GM-034` corrected: `runtime.py`
        reads the registry ONCE AT BOOT, so the gap between the two
        readings is the age of the process.  Since that ticket the entry is
        given back by the registry probe, before the override is applied,
        and the login survives; the handler further down no longer restores
        anything, because it can no longer be reached holding a spent
        entry.  See `test_gm_login_scene_override_registry_authority` for
        the unmocked walk of that probe.

        The staged scene is an ADMISSIBLE one, so the entry gets in, gets
        consumed, and is then refused at the seam: the branch is walked with
        its gate open (`COO-DECISION 20260829_0742`), not by disabling the
        gate.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        real_resolve = world_scene_entry.resolve_entry

        def refuse_the_override_destination(stored, *args, **kwargs):
            if stored.scene_id == KNOWN_SCENE_ID:
                raise world_scene_entry.SceneEntryRefused(
                    world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
                    "refused by the test, standing in for a registry that "
                    "changed under this login",
                )
            return real_resolve(stored, *args, **kwargs)

        with mock.patch.object(
            world_scene_entry, "resolve_entry",
            side_effect=refuse_the_override_destination,
        ):
            state, _selector = self._login_and_start("gm_runner")

        # CORE-REQUEST-GM-034 MOVED THIS, AND THE MOVE IS THE POINT.  The
        # registry probe now refuses the override BEFORE it is applied, so
        # the seam this test stands on is caught one step earlier: the
        # entry comes back at the probe, and the login is no longer refused
        # at all -- the character goes to its own row and is in the game.
        # The assertion that mattered is unchanged and kept word for word
        # below: the operator's instruction survives.
        self.assertNotIn("world_scene_entry_refused_no_reply", state.events)
        self.assertIn(
            f"gm_login_scene_override_refused_by_registry_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertIn(
            f"gm_login_scene_override_restored_after_refusal_{KNOWN_SCENE_ID}",
            state.events,
        )
        self.assertEqual(
            json.loads(self.overrides_path.read_text(encoding="utf-8"))[
                "gm_login_scene"
            ],
            {"gm_runner": KNOWN_SCENE_ID},
            "the operator's instruction has to survive a login that never "
            "reached the scene it names",
        )

    # ----- the frame-resync failure branch --------------------------------

    def test_a_refused_frame_recompose_still_leaves_selected_on_the_arrival(
        self,
    ):
        """The deliberate answer to a question this design had left open.

        The override path recomposes the ActorAttr/MovementAttr frame from
        `entry.position`, and that recompose has two named failure exits: it
        can raise (`..._frame_resync_refused_*`) or come back the wrong
        length (`..._length_drift`).  Either way the login falls back to the
        untouched production bytes, which name the character's stored scene
        -- while the TELEPORT in the same reply still carries the resolved
        arrival, because it was built from `entry` before any of this.

        So on that branch the login is already split-brained, with or
        without this round's change; what this test pins is WHICH half the
        in-memory character follows.  It follows the teleport (the packet
        that actually moves the client), not the fallback frame: the
        alternative -- leaving `selected` on the stored row -- would bring
        back exactly the census and checkpoint faults the resync exists to
        remove, on the one login least able to afford them.  Both named
        events fire, so the fallback is never silent.

        Found by pf-adversary, which noted no test drove this combination.
        """
        self._write_configs(["gm_runner"], {"gm_runner": KNOWN_SCENE_ID})
        real_start_game = self.projector.start_game

        def refuse_the_recompose(*args, **kwargs):
            # The first call (select_and_start's own) passes no position and
            # must succeed, or there is no login to speak of.  Every
            # recompose from the resolved arrival is refused.
            if kwargs.get("position") is not None:
                raise ValueError("refused by the test")
            return real_start_game(*args, **kwargs)

        with mock.patch.object(
            self.projector, "start_game", side_effect=refuse_the_recompose,
        ):
            state, _selector = self._login_and_start("gm_runner")

        self.assertIn(
            "gm_login_scene_override_frame_resync_refused_ValueError",
            state.events,
        )
        self.assertIn(
            "gm_login_scene_override_selected_position_resynced_"
            f"{KNOWN_SCENE_ID}",
            state.events,
        )
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
