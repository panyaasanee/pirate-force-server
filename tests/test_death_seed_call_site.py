"""DEATH_SEED_WIRING -- the chief seam in runtime.py, proven at the call site.

LANE-B's pf-adversary finding D2 (``pf_bridge notes_to_chief/20260906_1712``,
routed to chief by ``COO-DECISION 20260906_1955`` item 3): the WRITE half of
the world's grave book has been live for rounds -- ``mob_death.commit_death``
buries every accepted kill -- but ``grep mob_death_persistence runtime.py``
returned ZERO rows, so nothing ever read it back.  ``mob_death_register`` is
built in ``PersistentGameSessionState.__init__``, i.e. per CONNECTION, and a
relog therefore handed the new session a virgin register: every monster the
player had killed stood up again at full HP, and two players in one scene
never saw each other's kills.  Directly against ``PANYA 20260906_1057/1140``
("scene state is the world's, not the connection's").

``tests/test_mob_death_persistence.py`` already pins what
``seed_the_session_state`` DOES when someone calls it.  This file pins that
runtime.py CALLS it, on the one path that matters and used to be missed.

WHY THE BOOT SCENE IS THE WHOLE POINT.  ``__init__`` seeds
``mob_combat_scene_folder`` from the boot roster's own scene, so for a
character whose stored scene is the boot scene the
``if folder != self.mob_combat_scene_folder:`` branch inside
``_sync_combat_scene_state`` is false on its very first evaluation and NEVER
RUNS.  A seed placed inside it would have worked in scene 2 and never in
bg0001 -- the scene the game boots into.  ``test_the_branch_that_would_have
_carried_this_never_runs_here`` measures that condition directly, so the
other tests in this file cannot be satisfied by a future seed hidden in the
branch.

Mutants this file was written against (each reverted by hand and measured
before the round's push):

  * delete the two-line seed statement from ``_sync_combat_scene_state``
    -> ``test_a_relogin_finds_the_monster_it_killed_still_dead`` and
    ``test_a_second_session_in_the_same_scene_sees_the_first_ones_kill``
    both redden (register clean, ledger at the ceiling);
  * seed the register alone (drop the ledger half of the assignment)
    -> ``test_the_ledger_moves_with_the_register_never_without_it``
    reddens, which is the shape ``mob_death.REFUSE_LEDGER_DISAGREES_WITH
    _REGISTER`` turns into an unwound v141 listener thread in production.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_death_persistence as graves  # noqa: E402
from pirateforce_foundation import world_scene_folder  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
BOOT_SCENE_ID = 1
#: A killer identity is a plain int on the wire (mob_death refuses anything
#: else): the account-derived actor id the previous connection swung with.
KILLER = 0x750059


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class TheDeathSeedCallSiteTests(unittest.TestCase):
    """A kill outlives the connection that made it."""

    def setUp(self) -> None:
        # A book of this test's own, never the process singleton a parallel
        # test could be burying into.  install_world_deaths returns the new
        # book and swaps it in; the cleanup puts a clean one back rather than
        # leaving this test's graves where the next file would seed from them.
        self.world = graves.install_world_deaths(graves.WorldDeaths())
        self.addCleanup(graves.install_world_deaths, graves.WorldDeaths())
        graves.forget_announced_scenes()
        self.addCleanup(graves.forget_announced_scenes)

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
                BOOT_SCENE_ID, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.folder = world_scene_folder.scene_folder_for_scene_id(
            BOOT_SCENE_ID)
        self.assertIsNotNone(
            self.folder, "the boot scene must resolve to a folder")
        self.roster = field_mobs.load_roster(self.folder)
        self.assertTrue(self.roster, "the boot scene must have a mob table")
        self.victim = self.roster[0]

    # ---- harness ----------------------------------------------------

    def _session(self, token):
        """One connection, logged in and in the boot scene."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)))
            state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC))
            character = self.store.list_characters(
                state.foundation.account_id)[-1]
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        return state

    def _kill_the_victim(self, state):
        """An accepted kill, through the same commit_death production uses.

        commit_death's own write seam buries it (world=None resolves to the
        book install_world_deaths just put in place), which is the half that
        was already wired before this round.
        """
        record = mob_death.DeathRecord(
            self.victim.actor_identity, KILLER, self.victim.max_hp,
            self.folder)
        step = mob_death.DeathStep(
            record=record,
            dying_pc=b"\x01", dying_frame=b"\x02",
            dead_pc=b"\x03", dead_frame=b"\x04",
            register=state.mob_death_register.with_death(record),
            base_generation=0,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            mob_death.commit_death(state.mob_death_register, step)
        self.assertTrue(
            self.world.is_buried(self.folder, self.victim.actor_identity),
            "the write half did not reach the world book -- this test is"
            " about the READ seam, so a broken write here is not the finding",
        )

    def _sync(self, state):
        with contextlib.redirect_stdout(io.StringIO()):
            return state._sync_combat_scene_state()

    # ---- the seam ---------------------------------------------------

    def test_a_relogin_finds_the_monster_it_killed_still_dead(self) -> None:
        first = self._session("seed-relog-a")
        self._kill_the_victim(first)

        # The connection dies here.  Everything the player did to the world
        # that is still true is in the world's book, not in this object.
        relogged = self._session("seed-relog-b")
        self.assertFalse(
            relogged.mob_death_register.is_dead(
                self.victim.actor_identity, self.folder),
            "a fresh session must start with a virgin register -- if this"
            " fails the test is measuring leakage, not the seam",
        )

        self._sync(relogged)

        self.assertTrue(
            relogged.mob_death_register.is_dead(
                self.victim.actor_identity, self.folder),
            "the monster the player killed before the relog stood back up",
        )

    def test_the_ledger_moves_with_the_register_never_without_it(
        self,
    ) -> None:
        first = self._session("seed-ledger-a")
        self._kill_the_victim(first)
        relogged = self._session("seed-ledger-b")
        self._sync(relogged)

        balance = relogged.mob_combat_ledger.balance_of(
            self.victim.actor_identity)
        self.assertEqual(
            balance.current_hp, 0,
            "the register says dead and the ledger says alive:"
            " REFUSE_LEDGER_DISAGREES_WITH_REGISTER, which the arrival census"
            " reaches from an else: its own try does not cover",
        )
        self.assertEqual(
            balance.max_hp, self.victim.max_hp,
            "the seed must move the current HP, never the ceiling",
        )
        for other in self.roster[1:]:
            self.assertEqual(
                relogged.mob_combat_ledger.balance_of(
                    other.actor_identity).current_hp,
                other.max_hp,
                "a monster nobody killed lost HP to the seed",
            )

    def test_a_second_session_in_the_same_scene_sees_the_first_ones_kill(
        self,
    ) -> None:
        # PANYA 20260906_1057/1140: the scene's state belongs to the world,
        # so the second player in it inherits what the first one did.
        first = self._session("seed-shared-a")
        second = self._session("seed-shared-b")
        self._kill_the_victim(first)

        self._sync(second)

        self.assertTrue(
            second.mob_death_register.is_dead(
                self.victim.actor_identity, self.folder),
            "two sessions in one scene did not share a kill",
        )

    def test_the_branch_that_would_have_carried_this_never_runs_here(
        self,
    ) -> None:
        # The reason the seed is OUTSIDE `if folder != mob_combat_scene_
        # folder:`.  If this assertion ever fails, the seam may have been
        # moved into that branch and the tests above would pass for the
        # wrong reason.
        state = self._session("seed-branch")
        self.assertEqual(
            state.mob_combat_scene_folder, self.folder,
            "__init__ no longer opens on the boot scene's own folder --"
            " re-derive where DEATH_SEED_WIRING has to sit before trusting"
            " the rest of this file",
        )

    def test_an_empty_book_leaves_every_monster_standing(self) -> None:
        # The seed must not be a way to lose monsters: nobody died here.
        state = self._session("seed-empty")
        self._sync(state)
        for row in self.roster:
            self.assertFalse(
                state.mob_death_register.is_dead(
                    row.actor_identity, self.folder),
                "the seed buried a monster no one killed",
            )
            self.assertEqual(
                state.mob_combat_ledger.balance_of(
                    row.actor_identity).current_hp,
                row.max_hp,
            )

    def test_the_seam_is_idempotent_on_every_dispatch(self) -> None:
        # It runs outside the branch, so it runs on every dispatch: a second
        # call must not double-apply or raise.
        first = self._session("seed-idem-a")
        self._kill_the_victim(first)
        relogged = self._session("seed-idem-b")
        self._sync(relogged)
        before = relogged.mob_combat_ledger.balance_of(
            self.victim.actor_identity)
        self._sync(relogged)
        self._sync(relogged)
        after = relogged.mob_combat_ledger.balance_of(
            self.victim.actor_identity)
        self.assertEqual((before.current_hp, before.max_hp),
                         (after.current_hp, after.max_hp))
        self.assertTrue(
            relogged.mob_death_register.is_dead(
                self.victim.actor_identity, self.folder))


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
