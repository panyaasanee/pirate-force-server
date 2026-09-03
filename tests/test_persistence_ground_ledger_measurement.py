"""LANE-DB: does a ground drop survive a relogin, through the real session
machinery -- and is there anywhere in the schema it COULD survive to?

WHAT THIS ANSWERS.  `pf_bridge/notes_to_chief/20260903_1649_COO-DECISION-
lane-db-0951-accepted-at-the-measured-layer-not-a-milestone-next-queue-is-
the-ground-ledger-after-relogin.md` asked three questions, in order:
(a) where does the ground ledger row live -- a table, or memory only?
(b) if there is a table, does `select_and_start` read it back?
(c) if there is no table, propose ONE door shape in a letter -- do not build
    it.

This file measures (a), through the same class of real production entry
point `0951`'s own round used (`tests/test_persistence_backpack_relogin.py`,
`pirate-force-server#660`): a live `PersistentGameSessionState`, built with
`runtime.make_state_class`, dispatching real wire bytes through `dispatch`
-- not `mob_loot` functions called directly and not raw SQL. The harness
below (`_state`, `_warp`, `_kill`, `_clock`) is reproduced, not imported,
from `tests/test_choose_npc_call_site_loot_cell.py`, for the reason that
file itself gives for reproducing lane A's: importing another test class
makes a production guarantee die quietly the day that file is reorganised.

WHAT IS NOT DONE HERE.  No `migrations/` file, no `persistence_*.py`
module, no `store.py` method. `COO 1649` is explicit: "ประตูใหม่สร้างได้
ต่อเมื่อผมตอบใบนั้น" (a new door may only be built once COO answers that
letter). This round only measures and proposes; the proposal is the letter,
not this file.

WHAT THE TWO STRUCTURAL TESTS PROVE, AND WHAT THEY DO NOT.  `pf-adversary`
(round `ld70iq`) demonstrated, in a disposable worktree, that the migration
scan can be dodged by splitting `CREATE TABLE` from the table name across a
line break, and that BOTH structural tests are dodged outright by a table
named something that shares no substring with "ground"/"drop"/"loot" (e.g.
`floor_items`) -- neither escape hatch is exploited anywhere in this repo's
real `migrations/*.sql` today (checked: every table name at HEAD is
`schema_migrations`/`accounts`/`characters`/`character_positions`/
`sessions`/`character_backpacks`/`character_backpack_items`/the `009`
rebuild's own scratch tables), but a name-substring scan can only ever prove
"no table under this naming convention", never "no table under any name".
That is why this file does not rest on the scan alone: `test_the_ground_
drop_does_not_persist_flag_agrees` below cross-checks against a SEPARATE,
independently-maintained piece of evidence (`mob_loot.GROUND_DROP_DOES_NOT_
PERSIST` and `docs/FUNCTIONAL_COVERAGE.json`'s own long history of this
exact gap) rather than adding a second scan of the same shape.
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import io
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs                      # noqa: E402
from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_combat_membership           # noqa: E402
from pirateforce_foundation import mob_loot                        # noqa: E402
from pirateforce_foundation import world_scene_travel               # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (        # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget     # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (         # noqa: E402
    current_character_id,
    record_warp_target,
)
from pirateforce_foundation.legacy_bridge import (                 # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle    # noqa: E402
from pirateforce_foundation.model import Position                  # noqa: E402
from pirateforce_foundation.runtime import make_state_class        # noqa: E402
from pirateforce_foundation.store import SQLiteStore               # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PRISON_EXILE = 2
DESTINATION_FOLDER = "Bg0002"
SCENE_KEY = "Bg0002"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class GroundLedgerDoesNotSurviveARelogin(unittest.TestCase):
    """Question (a): a table, or memory only?  Measured, not read off a
    docstring -- `mob_loot.py`'s own HYPOTHESES text already says "the
    ledger lives in the caller's process" (`mob_loot.py:928-930`); this
    class drives two real, independent logins through `dispatch` and shows
    the second one never sees the first one's drop."""

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
        self.roster = field_mobs.load_roster(DESTINATION_FOLDER)
        self.clock_ms = 0

    # ---- harness, reproduced from test_choose_npc_call_site_loot_cell.py --

    def _clock(self):
        return self.clock_ms / 1000.0

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            actions = state.dispatch(self.legacy.parse_outer(pc))
        return actions, out.getvalue() + err.getvalue()

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            monotonic_clock=self._clock,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.mob_loot_rng = random.Random(1)
        return state

    def _warp(self, state, scene_id):
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        target = WarpTarget(scene_id, spawn[0], spawn[1], spawn[2])
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        self.clock_ms += 1000
        return spawn

    def _target_pos_pc(self, xyz):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(value) for value in (*xyz, 0.0))
            + legacy.u8tag(0x0B, 0)
            + legacy.u8tag(0x0B, 0)
        )

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

    def _kill(self, state, target_identity):
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(target_identity, row.max_hp, 1)
        )
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        self._dispatch(state, self._action_vital_pc(target_identity))
        self.clock_ms += 1000

    def _row_count(self, state):
        return mob_loot.ground_rows_live_here(state.mob_loot_cell, SCENE_KEY)

    # ---- the measurement --------------------------------------------

    def test_a_kill_in_one_login_leaves_the_ground_empty_for_the_next_login(
        self,
    ) -> None:
        """Login A kills a monster in scene 2 and leaves one row on the
        ground. Login B -- a SECOND, independent session against the
        SAME store file -- warps into the same scene and finds nothing.

        `state.token` is the authenticated login name (`runtime.py`
        ~7008/~8235), so two DIFFERENT tokens are, strictly, two different
        accounts, not one account relogging under the same name. That does
        not weaken this measurement: `self.mob_loot_cell =
        mob_loot.DropLedgerCell()` (`runtime.py:1328`) runs unconditionally
        in `PersistentGameSessionState.__init__` with no token-keyed cache
        or registry anywhere in `runtime.py` for this attribute (pf-adversary
        round `ld70iq` grepped for one and found none) -- so a same-token
        relogin would take the identical code path and produce the
        identical result: a fresh, empty cell.

        `COO 1048`/`1649`: dropped items are meant to belong to "the
        world", per scene, not to the session. This is the measurement
        that names the gap: the world does not currently remember it.
        """
        state_a = self._state("tok_ground_ledger_login_a")
        self._warp(state_a, PRISON_EXILE)
        target = self.roster[0].actor_identity
        self._kill(state_a, target)
        self.assertEqual(
            self._row_count(state_a), 1,
            "the harness did not leave a row on the ground; this test "
            "would pass for the wrong reason",
        )

        state_b = self._state("tok_ground_ledger_login_b")
        self._warp(state_b, PRISON_EXILE)
        self.assertEqual(
            self._row_count(state_b), 0,
            "a second login saw the first login's ground row -- if this "
            "ever goes red, something now DOES carry ground state across "
            "a relogin and questions (a)/(b) below must be re-measured",
        )
        self.assertIsNot(
            state_a.mob_loot_cell, state_b.mob_loot_cell,
            "the two logins are sharing one DropLedgerCell object; that "
            "would be in-process cross-session leakage, not persistence",
        )

    def test_the_cell_constructor_takes_no_store_and_no_character(
        self,
    ) -> None:
        """Structural half of (a): `DropLedgerCell.__init__` has no
        parameter that could reach a database -- so there is no code
        path by which it COULD read or write a row, independent of
        whatever any one call site happens to do today.

        Uses `inspect.signature` and checks for `*args`/`**kwargs`
        explicitly, not a plain `co_varnames[:co_argcount]` slice: that
        slice is blind to a catch-all parameter (`pf-adversary` round
        `ld70iq` demonstrated live, in a disposable worktree, that a
        `**_smuggled_kwargs` added to the constructor -- letting a caller
        pass `store=...` and have it silently kept on `self` -- leaves a
        `co_varnames[:co_argcount]` check green, because a catch-all never
        enters that slice).
        """
        signature = inspect.signature(mob_loot.DropLedgerCell.__init__)
        names = tuple(signature.parameters)
        self.assertEqual(
            names, ("self", "ledger", "lifetime_seconds", "clock", "scene"),
            "DropLedgerCell's constructor changed shape; re-measure "
            "whether it now takes anything that could reach a database",
        )
        catch_alls = [
            name for name, param in signature.parameters.items()
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ]
        self.assertEqual(
            catch_alls, [],
            "DropLedgerCell.__init__ gained a *args/**kwargs catch-all "
            f"({catch_alls}) -- a caller could now smuggle a store or "
            "anything else through it without the named-parameter check "
            "above ever seeing it",
        )


class NoSchemaExistsForGroundDrops(unittest.TestCase):
    """Question (b) is moot without a table; this class proves there is
    none, structurally, so the answer does not rot the day someone adds
    an unrelated column named similarly."""

    NAME_FRAGMENTS = ("ground", "drop", "loot")

    #: Matches across line breaks and arbitrary whitespace between the
    #: keywords and the table name -- `pf-adversary` round `ld70iq`
    #: demonstrated live that a line-by-line, `str.startswith`-based scan
    #: is dodged by writing `CREATE TABLE` and the table name on separate
    #: physical lines (a real, working SQLite statement). This is still a
    #: NAME scan, not a shape scan: see the module docstring for what it
    #: does and does not prove.
    _CREATE_TABLE = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
        re.IGNORECASE,
    )

    def test_no_migration_creates_a_table_naming_ground_drop_or_loot(self):
        hits = []
        for sql_file in sorted((ROOT / "migrations").glob("*.sql")):
            text = sql_file.read_text(encoding="utf-8")
            for match in self._CREATE_TABLE.finditer(text):
                name = match.group(1)
                if any(frag in name.lower() for frag in self.NAME_FRAGMENTS):
                    hits.append(f"{sql_file.name}: table {name!r}")
        self.assertEqual(
            hits, [],
            "a migration now creates a table whose name mentions ground/"
            "drop/loot -- (b) needs answering for real: does "
            f"select_and_start read it back? found: {hits}",
        )

    def test_ground_drop_does_not_persist_flag_agrees(self):
        """Second, independently-maintained evidence for (a), not another
        name scan: `mob_loot.py` itself carries a constant recording this
        exact gap, and `docs/FUNCTIONAL_COVERAGE.json` documents the same
        conclusion across many rounds of LANE-B's own history (mob_loot's
        ground-drop line, not the separately-tracked backpack-pickup
        persistence work `0951`/`#660` already measured). Two sources that
        do not share this file's naming-scan blind spot, agreeing with it,
        is what makes claim (a) more than "grep found nothing"."""
        self.assertIs(
            mob_loot.GROUND_DROP_DOES_NOT_PERSIST, True,
            "mob_loot.py's own flag now says a ground drop DOES persist -- "
            "(a) must be re-measured for real, not read off this constant",
        )
        coverage = (ROOT / "docs" / "FUNCTIONAL_COVERAGE.json").read_text(encoding="utf-8")
        self.assertIn(
            "GROUND_DROP_DOES_NOT_PERSIST", coverage,
            "the coverage doc no longer names this constant; the "
            "corroboration this test relies on may have been edited away",
        )

    def test_sqlitestore_has_no_method_naming_ground_drop_or_loot(self):
        import pirateforce_foundation.store as store_module

        tree = ast.parse(Path(store_module.__file__).read_text(encoding="utf-8"))
        class_node = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "SQLiteStore"
        )
        method_names = [
            node.name for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        hits = [
            name for name in method_names
            if any(frag in name.lower() for frag in self.NAME_FRAGMENTS)
        ]
        self.assertEqual(
            hits, [],
            "SQLiteStore now has a method naming ground/drop/loot -- "
            f"read it before answering (b) again: {hits}",
        )


if __name__ == "__main__":
    unittest.main()
