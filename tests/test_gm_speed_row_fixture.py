"""The fixture that separates "the server read the row" from "the server
sent a constant" -- COO-DECISION `20260903_1250` point 4.

WHY THIS FILE HAD TO EXIST AT ALL
---------------------------------
`NOW.md` (COO `0054`) records the hole this file fills, and it is a hole in
the EVIDENCE, not in the code: since migration `009` the DEFAULT of
`characters.speed_walk` is `400.0`, and `400.0` is also
`player_wire.PLAYER_LOGIN_MOVEMENT_SPEED` -- the hardcoded constant the login
sent before `#605` landed the row read.  On every live database, the owner's
included, "read the row" and "send the constant" therefore produce THE SAME
BYTES.  `GT-218` runs with `PF_SPEED_TRIAL=400`, which is that same number, so
it proves a safe route and cannot prove a read.  COO named the only two
separators: a fixture holding a value that is not `400`, or a real `/speed` on
a real client.  This file is the first one.  `250.0` is COO's number, not this
lane's choice.

WHAT IS PROVEN HERE, IN THE ORDER THE CLASSES RUN
-------------------------------------------------
1. `TheDefaultIsTheConstantTests` -- the premise itself, measured rather than
   quoted: a character born through the real store carries `speed_walk` equal
   to the login constant, so a live database cannot answer this question.
   This class is why the rest of the file is not redundant.
2. `TheRowReachesTheComposerTests` -- with `250.0` in the row, the bytes
   `gm/speed_wire.compose_sparse_speed_update` produces carry the f32 of
   `250.0` and NOT the f32 of the constant, and the two rows produce
   DIFFERENT frames.  The value is written through raw SQL -- a door neither
   the resolver nor the composer participates in -- so nothing in the chain
   under test also supplied the number.
3. `TheDeferralStillHoldsTests` -- the other half, and the half that keeps
   this round honest: through the LIVE login seam
   (`login_speed.resolve_for_character`) that same `250.0` row still does NOT
   reach the wire.  `send_deferred()` holds it, the constant goes out, and
   the row shows up only in the console line's `withheld_row=` detail.  That
   detail is itself the proof that the read is real while the lock is shut.

MUTANTS APPLIED AND MEASURED GOING RED (this round, `1nm6hh`)
-------------------------------------------------------------
* `login_speed.resolve` returns the fallback on every branch
  -> `TheRowReachesTheComposerTests` red.
* `compose_sparse_speed_update` composes `PLAYER_LOGIN_MOVEMENT_SPEED`
  instead of the value it is handed -> `TheRowReachesTheComposerTests` red.
* `_withheld_row_detail` returns `""` -> `TheDeferralStillHoldsTests` red.
* `speed_wire.SPEED_LOGIN_READ_LANDED = True` (the lock flipped)
  -> `TheDeferralStillHoldsTests` red.  This file therefore GUARDS the lock;
  it does not open it.

NONCLAIM -- READ THIS BEFORE QUOTING ANY RESULT FROM THIS FILE
--------------------------------------------------------------
!! Nothing here is a win on a screen.  No byte in this file ever left a
socket; no client rendered anything; no attended round happened.  What is
measured is a chain of this repository's own functions running headless in a
`TemporaryDirectory`.  `/speed` remains deferred at both of its locks
(`COO 2147`), this file opens neither, and `GT-193` steps 4-7 remain
ungradeable.  The canonical database is not read, written, copied or named
here.
"""
from __future__ import annotations

import sqlite3
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import login_speed  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402
from pirateforce_foundation.gm import speed_wire  # noqa: E402
from pirateforce_foundation.gm.speed_wire import (  # noqa: E402
    compose_sparse_speed_update,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from test_persistence_typed_attr_columns import (  # noqa: E402
    NoHandleOutlivesItsTempDirMixin,
)

MIGRATIONS = ROOT / "migrations"
LEGACY_SOURCE = ROOT / "current" / "pf_login_game_server_v141.py"

#: COO-DECISION `20260903_1250` point 4 picked this number.  Its whole job is
#: to be a speed that is NOT the column default and NOT the wire constant, so
#: a frame carrying it cannot have been composed from either.
FIXTURE_SPEED = 250.0

#: NOT a literal `400.0`.  The point of the file is that this number and the
#: column default are the same today; writing it twice by hand is how that
#: coincidence would survive somebody fixing one of them.
THE_CONSTANT = player_wire.PLAYER_LOGIN_MOVEMENT_SPEED


def _build_wire(selector):
    """The shape `store.create_character` unpacks, as the persistence tests
    build it (`tests/test_persistence_login_vitals.py:408`)."""
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


def _f32(value: float) -> bytes:
    """The four bytes the client reads for a speed, spelled once."""
    return struct.pack("<f", value)


class _ARealDatabaseOnDisk(NoHandleOutlivesItsTempDirMixin, unittest.TestCase):
    """A run copy in a `TemporaryDirectory`, migrated by the real migrations.

    COO's scope line for this work, quoted: tests only, run copy /
    `TemporaryDirectory` only, the canonical database is not touched and no
    migration is proposed.  Nothing in this file opens a database anywhere
    else, and the mixin above fails the test if a handle outlives the
    directory (that is the defect that killed PR #495 on the Windows gate).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # AFTER the line above: cleanups run LIFO, so this one runs first.
        self.guard_the_temp_dir(self.tmp)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("gm-speed-row-fixture")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)

    def born(self, tag="row"):
        return self.store.create_character(
            self.account_id, "Speed" + tag, "speed" + tag,
            "fingerprint-speed-" + tag, _build_wire, self.home,
        )

    def write_the_row_behind_the_code_under_test(self, character_id, value):
        """Put `value` in the column WITHOUT using any door under test.

        This is the whole method of this file.  `store.write_typed_attributes`
        would work too, but it shares a code path with the composer
        (`write_typed_attributes_and_compose_sparse`), and
        `tests/test_persistence_typed_attr_columns.py` records an adversary
        pass in which replacing that class's read-back with the caller's own
        input dict changed nothing.  Raw SQL cannot be the source of the
        number the resolver later reports, so a match downstream is a read.
        """
        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "UPDATE characters SET speed_walk = ? WHERE id = ?",
                (value, character_id),
            )
            db.commit()
        finally:
            db.close()


class TheDefaultIsTheConstantTests(_ARealDatabaseOnDisk):
    """The premise `NOW.md` states, measured here instead of quoted.

    If this class ever goes red the rest of the file is answering a question
    nobody is asking any more -- a live database would have become able to
    separate a read from a constant on its own.
    """

    def test_a_newborn_row_holds_exactly_the_login_constant(self):
        character = self.born("newborn")
        stored = self.store.read_typed_attributes(character.id)
        self.assertEqual(stored[login_speed.COLUMN], THE_CONSTANT)

    def test_so_a_newborn_composes_the_bytes_a_constant_would(self):
        """Both sides of the question, byte for byte, on a live-shaped row.

        This is the indistinguishability itself: nothing downstream can tell
        these two apart, which is why `GT-218`'s `PF_SPEED_TRIAL=400` proves a
        safe route and not a read.
        """
        character = self.born("newborn-bytes")
        stored = self.store.read_typed_attributes(character.id)
        legacy = load_legacy(LEGACY_SOURCE)
        _pc_row, frame_from_row = compose_sparse_speed_update(
            legacy, 1, 0, stored[login_speed.COLUMN])
        _pc_const, frame_from_constant = compose_sparse_speed_update(
            legacy, 1, 0, THE_CONSTANT)
        self.assertEqual(frame_from_row, frame_from_constant)


class TheRowReachesTheComposerTests(_ARealDatabaseOnDisk):
    """With `250.0` in the row, the frame carries `250.0`.

    The chain exercised end to end: raw SQL write -> `store.
    read_typed_attributes` -> `login_speed.resolve` -> `gm/speed_wire.
    compose_sparse_speed_update` -> bytes.  `resolve` rather than
    `resolve_for_character` on purpose: the live seam answers with the
    deferral before the row is consulted, and that half is graded by
    `TheDeferralStillHoldsTests` below.  Calling the resolver directly opens
    no gate -- it composes bytes in memory that no call site sends.
    """

    def frame_for_a_row_holding(self, value, tag):
        character = self.born(tag)
        self.write_the_row_behind_the_code_under_test(character.id, value)
        stored = self.store.read_typed_attributes(character.id)
        resolved = login_speed.resolve(
            stored.get(login_speed.COLUMN), fallback=THE_CONSTANT)
        legacy = load_legacy(LEGACY_SOURCE)
        _pc, frame = compose_sparse_speed_update(
            legacy, 1, 0, resolved.value)
        return resolved, frame

    def test_the_resolver_reports_the_row_as_the_source(self):
        resolved, _frame = self.frame_for_a_row_holding(FIXTURE_SPEED, "src")
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)
        self.assertEqual(resolved.value, FIXTURE_SPEED)

    def test_the_frame_carries_the_f32_of_the_row_and_not_of_the_constant(self):
        _resolved, frame = self.frame_for_a_row_holding(FIXTURE_SPEED, "f32")
        self.assertIn(_f32(FIXTURE_SPEED), frame)
        self.assertNotIn(_f32(THE_CONSTANT), frame)

    def test_two_different_rows_do_not_compose_the_same_frame(self):
        """The control the whole file rests on.

        A composer fed a constant returns equal frames here whatever the rows
        hold; that is the mutant this test exists to kill, and it is the shape
        an adversary pass has already driven through a neighbouring file.
        """
        _r1, frame_at_the_fixture = self.frame_for_a_row_holding(
            FIXTURE_SPEED, "differ-a")
        _r2, frame_at_the_constant = self.frame_for_a_row_holding(
            THE_CONSTANT, "differ-b")
        self.assertNotEqual(frame_at_the_fixture, frame_at_the_constant)
        self.assertIn(_f32(FIXTURE_SPEED), frame_at_the_fixture)
        self.assertIn(_f32(THE_CONSTANT), frame_at_the_constant)


class TheDeferralStillHoldsTests(_ARealDatabaseOnDisk):
    """The live login seam, and it does NOT send the row -- by design.

    `COO 2147` holds both `/speed` locks until an attended round tries a
    sanctioned value.  A file that proved the row reaches the composer and
    stopped there could be read as "the row reaches the client".  It does not,
    and this class is the pin that keeps anybody from reading it that way.
    """

    def a_character_whose_row_holds_the_fixture_speed(self, tag):
        character = self.born(tag)
        self.write_the_row_behind_the_code_under_test(
            character.id, FIXTURE_SPEED)
        return character

    def test_the_wire_is_still_deferred_at_head(self):
        """Read off the module live, the way the seam itself reads it."""
        self.assertIs(speed_wire.SPEED_LOGIN_READ_LANDED, False)
        self.assertIs(speed_wire.send_deferred(), True)

    def test_the_login_seam_sends_the_constant_not_the_row(self):
        character = self.a_character_whose_row_holds_the_fixture_speed("held")
        resolved = login_speed.resolve_for_character(
            self.store, character.id, fallback=THE_CONSTANT)
        self.assertEqual(resolved.reason, login_speed.WIRE_DEFERRED)
        self.assertEqual(resolved.value, THE_CONSTANT)
        self.assertFalse(resolved.came_from_the_row)

    def test_the_console_line_names_the_row_it_withheld(self):
        """The observable that separates a read from a constant TODAY.

        On a live database this detail reads `withheld_row=400.0` and says
        nothing -- the same number either way.  Against this fixture it must
        read `250.0`, and that is the only place on `main` where the login's
        row read is visible to an operator while the lock is shut.
        """
        character = self.a_character_whose_row_holds_the_fixture_speed("line")
        resolved = login_speed.resolve_for_character(
            self.store, character.id, fallback=THE_CONSTANT)
        line = resolved.console_line()
        self.assertIn("withheld_row=%r" % FIXTURE_SPEED, line)
        self.assertNotIn("withheld_row=%r" % THE_CONSTANT, line)


if __name__ == "__main__":
    unittest.main()
