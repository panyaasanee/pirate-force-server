"""COO-DECISION 20260908_0542 section 4: the read-only class-weapon census.

THE FILE IS NAMED FOR A CHANGE THAT IS NOT IN IT, AND THAT IS DELIBERATE.
Round 21lxm6 wrote the widening COO asked for -- ``store.apply_v111_stack_merge``
accepting "a starting bag PLUS acquired rows" -- and then took it back out in
the same round, before unlocking, because pf-adversary measured what it does
on the real line:

    HEAD:    golden+acquired bag -> ValueError at the door -> runtime.py
             swallows it -> no reply, NOTHING WRITTEN
    widened: golden+acquired bag -> the merge COMMITS -> runtime.py:1945
             compares the committed bag against the single
             MERGED_V111_BACKPACK it imported and raises AFTER the write

and the frozen listener wraps ``state.dispatch`` in a ``try`` with a
``finally`` and NO ``except`` (``current/pf_login_game_server_v141.py`` lines
7440 / 7558 / 7847), so that RuntimeError leaves the accept loop.  The player
loses the identity-3 row with no reply AND every other session on the process
goes down with them.  Refusing the merge is bad; that is worse.  The widening
lands the round CORE-REQUEST 20260908_0206 makes the comparison set-shaped.

WHAT IS LEFT HERE IS THE CENSUS, which is the half of PANYA's item 4 (letter
20260908_0025) that can be answered without the owner's machine: how many
characters exist, in which classes, and how many hold a weapon their class
would not be given.  It writes nothing, and "writes nothing" is measured
below rather than promised.

WHAT THIS FILE DOES NOT PROVE.
* Not client-observable.  No window opens; nobody sees anything on a screen.
* It does not claim to know the numbers in the owner's database.  That is
  what the attended ticket goes and asks.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    persistence_class_weapon as class_weapon,
)
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


class TheCensusCountsAndNeverWritesTests(unittest.TestCase):
    """The read-only half of PANYA's item 4 (letter 20260908_0025).

    The census is what tells the owner how big the attended run under
    LOCK_GAME will be.  It runs on a database this test builds through the
    production ``create``, never on the canonical one, which does not exist
    in this clone.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _create(self, login_name):
        session = FoundationSession(self.lifecycle, self.projector, login_name)
        character, _ = session.create(
            "test01", self.legacy.get_preset_actor_wire())
        return character

    def test_an_empty_database_reports_nothing_to_change(self):
        with self.store.connect() as db:
            self.assertEqual(class_weapon.census_rows(db), ())
            self.assertIn(
                "rows_to_change=0", class_weapon.census_lines(db)[-1])

    def test_the_numbers_move_with_the_rows(self):
        """A spelled zero cannot pass: three shapes, three different counts."""
        right = self._create("right")
        wrong = self._create("wrong")
        gone = self._create("gone")
        weapon_identity = class_weapon.weapon_row(INITIAL_BACKPACK).identity
        other_class = next(
            class_id for class_id in class_weapon.CLASS_ID_TO_WEAPON_TEMPLATE
            if class_weapon.CLASS_ID_TO_WEAPON_TEMPLATE[class_id]
            != class_weapon.weapon_row(INITIAL_BACKPACK).template_id
        )
        with self.store.connect() as db:
            db.execute(
                "UPDATE characters SET class_id=? WHERE id=?",
                (other_class, wrong.id))
            db.execute(
                "DELETE FROM character_backpack_items "
                "WHERE character_id=? AND item_identity=?",
                (gone.id, weapon_identity))
        with self.store.connect() as db:
            by_class = {row[0]: row for row in class_weapon.census_rows(db)}
        with self.store.connect() as db:
            born_class = int(db.execute(
                "SELECT class_id FROM characters WHERE id=?",
                (right.id,),
            ).fetchone()[0])
        self.assertNotEqual(born_class, other_class)
        self.assertEqual(by_class[born_class][1], 2)   # right + gone
        self.assertEqual(by_class[born_class][2], 1)   # only "right" is ok
        self.assertEqual(by_class[born_class][4], 1)   # "gone" has no row
        self.assertEqual(by_class[other_class][3], 1)  # "wrong" is wrong

    def test_the_console_entry_cannot_write(self):
        """``mode=ro`` is the mechanism, and it is measured, not promised."""
        self._create("readonly")
        import sqlite3
        uri = "file:%s?mode=ro" % self.path
        with sqlite3.connect(uri, uri=True) as db:
            self.assertTrue(class_weapon.census_lines(db))
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM characters")

    def test_a_class_the_weapon_table_does_not_know_is_counted_not_raised(self):
        stray = self._create("stray")
        with self.store.connect() as db:
            db.execute(
                "UPDATE characters SET class_id=? WHERE id=?", (99, stray.id))
        with self.store.connect() as db:
            rows = {row[0]: row for row in class_weapon.census_rows(db)}
            self.assertEqual(rows[99][4], 1)
            self.assertIn(
                "class_id=99 name=UNKNOWN", "\n".join(
                    class_weapon.census_lines(db)))


class TheDoorThatMustStayShutUntilCoreRequest0206Tests(unittest.TestCase):
    """The tripwire round 21lxm6 left behind when it withdrew the widening.

    pf-adversary's finding D3 against this round's first draft: a pin that
    only asserts "a four-row bag is not equal to a three-row constant" is
    true forever, passes before and after the hazard is fixed, and therefore
    warns nobody.  These two do go red -- one when the door is re-widened
    early, one when the comparison behind it is finally fixed.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def test_a_bag_that_acquired_a_row_is_refused_and_nothing_is_written(self):
        """Red the day the door is widened before the caller can take it.

        The refusal costs the player their stack merge, and that cost is
        real.  What it buys is measured in the second half: the rows are
        exactly as they were.  The widened door commits them and then the
        caller raises out through a listener with no ``except``.
        """
        name = "acquired"
        session = FoundationSession(self.lifecycle, self.projector, name)
        character, _ = session.create(
            "test01", self.legacy.get_preset_actor_wire())
        relog = FoundationSession(self.lifecycle, self.projector, name)
        selected, _started = relog.select_and_start(character.selector)

        issued = self.store.backpack_issued_through(
            relog.session_id, selected.id)
        bag = self.store.get_backpack(relog.session_id, selected.id)
        taken = {row.slot for row in bag.items}
        free = next(slot for slot in range(40) if slot not in taken)
        self.store.commit_acquired_backpack_item(
            relog.session_id, selected.id,
            type(bag.items[0])(issued + 1, 3000001, 1, free),
        )
        before = self.store.get_backpack(relog.session_id, selected.id)

        with self.assertRaises(ValueError):
            self.store.apply_v111_stack_merge(relog.session_id, selected.id)

        self.assertEqual(
            self.store.get_backpack(relog.session_id, selected.id), before)

    def test_the_caller_still_compares_against_the_single_constant(self):
        """Red the day CORE-REQUEST 20260908_0206 lands -- which is the point.

        A SOURCE pin, and it says so: this lane may not edit ``runtime.py``,
        so the only honest thing it can assert about that module is what its
        text still says.  When chief makes the committed-merge comparison
        set-shaped, this test fails, and the failure message is the next
        LANE-DB round's instruction to put the widening back.
        """
        runtime = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "if self.foundation.backpack != MERGED_V111_BACKPACK:\n"
            "                raise RuntimeError("
            '"committed V111 Backpack state mismatch")',
            runtime,
            "runtime.py no longer raises after the commit -- CORE-REQUEST "
            "20260908_0206 has landed.  Restore the widened pre-state door "
            "in store.apply_v111_stack_merge (git show ebdad7c) and delete "
            "this test.",
        )


if __name__ == "__main__":
    unittest.main()
