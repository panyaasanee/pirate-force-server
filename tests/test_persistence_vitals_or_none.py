"""LANE-DB / M4: the door a login projection can call without learning to
catch an exception -- ``SQLiteStore.read_character_vitals_or_none``.

WHY A SECOND DOOR EXISTS.  ``read_character_vitals`` answers with a
``VitalsResolution``: either ``complete`` with three numbers behind
``require()``, or a list of named gaps.  That shape is right for a report and
wrong for a caller that must not raise -- and the caller this lane is heading
for (a login block that today hardcodes ``level 1, hp 100/100`` in
``player_wire``) is exactly that.  A caller left to write the try/except
itself is one tired evening away from ``except VitalsError: hp_current = 0``,
and on this wire a zero HP is not "unknown", it is DEAD
(``COO-DECISION 20260901_1059`` bans the guessed zero for that reason).
``None`` cannot be encoded, compared, or added to.

WHAT THIS FILE PROVES.

1. A row that really holds all three gives back exactly those three numbers,
   and they follow a later write rather than a constant.
2. Every reason the database has no usable answer comes back as ``None`` and
   never as a number: no vital written, half-written, ``level = 0``,
   ``hp_current > hp_max``, ``hp_max = 0``.
3. The three things that still RAISE, so that "the door that does not raise"
   is not discovered to be false by a login path in production: ``KeyError``
   for a row that does not exist or was soft-deleted, ``SchemaDriftError``
   when the typed schema and the database disagree, and ``VitalsError`` for a
   resolution claiming a completeness it cannot back.
4. No file reads this door and hands the result to the attribute composer --
   the shape in which the owner's banned guessed zero would reach the HP
   field (``NothingComposesFromThisDoorTests``, which also states what it
   cannot see).

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no frame is
composed and nothing is sent.  It does NOT pin that the method has no caller
-- only that no caller composes a block from it; the count of call sites was
zero when this landed, and that is a measurement in this round's file, not a
pin, for the reason ``NothingComposesFromThisDoorTests`` gives.  Whether a
login block may carry the row's numbers instead of ``player_wire``'s literals
is a SEND question and belongs to COO.  This file is wire/DB evidence for the
store half only, and it has never run against the owner's canonical database.
"""
import ast
import sqlite3
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import pf_birth_state  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _StoreCase(unittest.TestCase):
    """One real database, migrated by the repository's own runner."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("or-none")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)
        self.character = self.store.create_character(
            self.account_id, "OrNoneChar", "ornonechar",
            "fingerprint-or-none", _build_wire, self.home,
        )
        # MEASURED, never assumed: `COO-DECISION 20260902_0444` has chief
        # write the three vitals into `create_character`, and the round
        # before this one removed 33 tests of this lane's own that had taken
        # today's empty birth state for a fact of the world.  This call
        # refuses any birth state outside the two `pf_birth_state` accepts,
        # so a wrong insertion point is still caught here -- it just is not
        # caught by tests that are about something else.
        # A SECOND character, and `measure_every_birth` rather than the
        # singular call this fixture had first: a `pf-adversary` pass drove a
        # plug that seeds the account's FIRST character correctly and gives
        # `level = 0` to every one after it straight through the singular
        # version, all sixteen tests green.  `pf_birth_state`'s own docstring
        # names that exact plug as the reason the plural function exists, and
        # this fixture was citing that file while calling the wrong half of
        # it.
        self.second = self.store.create_character(
            self.account_id, "OrNoneChar2", "ornonechar2",
            "fingerprint-or-none-2", _build_wire, self.home,
        )
        self.birth, self.second_birth = pf_birth_state.measure_every_birth(
            self.store, [self.character.id, self.second.id])

    def pre_seed(self):
        """Put this character's row into the state a pre-007 database held.

        The subject of the `None` tests below IS a row that holds none of the
        three, so the row is CONSTRUCTED rather than inherited from whatever
        `create_character` leaves behind today (`pf_birth_state` case 2).
        Once birth seeding lands this is the only way to reach an unseeded
        row at all, so the fail-closed door stays measured instead of
        becoming unreachable.
        """
        pf_birth_state.clear_vitals_to_pre_seed(
            self.path, [self.character.id])

    def seed(self, **values):
        self.store.write_typed_attributes(self.character.id, values)

    def answer(self):
        return self.store.read_character_vitals_or_none(self.character.id)


class ItAnswersWithTheRowTests(_StoreCase):
    """A complete row comes back as its own three numbers."""

    def test_a_complete_row_answers_with_those_three_numbers(self):
        self.seed(level=7, hp_current=64, hp_max=90)
        answer = self.answer()
        self.assertIsInstance(answer, vitals.Vitals)
        self.assertEqual(
            (answer.level, answer.hp_current, answer.hp_max), (7, 64, 90))

    def test_the_numbers_are_the_rows_and_not_a_constant(self):
        # The failure this excludes is a method that "works" by handing back
        # the same seed every time -- which would look right on a database
        # seeded by 007 and be a lie on every other one.
        self.seed(level=1, hp_current=100, hp_max=100)
        self.assertEqual(self.answer(), vitals.Vitals(1, 100, 100))
        self.seed(level=12, hp_current=33, hp_max=250)
        self.assertEqual(self.answer(), vitals.Vitals(12, 33, 250))

    def test_it_follows_damage_written_by_this_lanes_own_writer(self):
        self.seed(level=4, hp_current=100, hp_max=100)
        self.store.apply_hp_damage(self.character.id, 30)
        self.assertEqual(self.answer(), vitals.Vitals(4, 70, 100))

    def test_a_character_alive_at_one_hp_is_still_an_answer(self):
        # The boundary matters more here than usual: 1 is a value, 0 is a
        # state, and neither is an absence.
        self.seed(level=2, hp_current=1, hp_max=50)
        answer = self.answer()
        self.assertEqual(answer.hp_current, 1)
        self.assertTrue(answer.alive)

    def test_a_character_at_zero_hp_answers_and_is_not_alive(self):
        self.seed(level=2, hp_current=0, hp_max=50)
        answer = self.answer()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.hp_current, 0)
        self.assertFalse(answer.alive)


class ItSaysNoneAndNeverANumberTests(_StoreCase):
    """Every state the database cannot answer for comes back as ``None``."""

    def test_a_row_holding_none_of_the_three_answers_none(self):
        # The state a pre-007 database really held, and the state a caller
        # meets today for every character born after 007 ran.  Constructed,
        # not inherited: see `pre_seed`.
        self.pre_seed()
        self.assertIsNone(self.answer())

    def test_a_half_written_row_answers_none(self):
        self.pre_seed()
        self.seed(level=5)
        self.assertIsNone(self.answer())
        self.seed(hp_current=40)
        self.assertIsNone(self.answer())

    def test_a_stored_zero_level_answers_none(self):
        # `COO-DECISION 20260902_0443` point 4: a zero level can be stored
        # and is refused on the way out.  This door must not be the way
        # around that.
        self.seed(level=0, hp_current=100, hp_max=100)
        self.assertIsNone(self.answer())

    def test_hp_current_above_hp_max_answers_none(self):
        # `006` writes one CHECK per column, so SQLite accepts this pair
        # happily; the cross-column rule lives in `persistence_vitals` and
        # this proves it survives the trip through the new door.
        self.seed(level=3, hp_current=120, hp_max=100)
        self.assertIsNone(self.answer())

    def test_a_zero_hp_max_answers_none(self):
        self.seed(level=3, hp_current=0, hp_max=0)
        self.assertIsNone(self.answer())


class ItDoesNotSwallowAMissingRowTests(_StoreCase):
    """``KeyError`` still means "no such character"."""

    def test_an_unknown_character_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.store.read_character_vitals_or_none(self.character.id + 9999)

    def test_a_soft_deleted_character_raises_key_error(self):
        self.seed(level=1, hp_current=100, hp_max=100)
        self.assertIsNotNone(self.answer())
        # try/finally and not `with sqlite3.connect(...)`: that form commits
        # on exit and does NOT close, and a raising UPDATE would leave the
        # handle open -- which costs nothing here and fails the Windows gate
        # at `TemporaryDirectory` cleanup.  `test_persistence_vitals.py`
        # carries the same scar with the measured WinError 32 in its comment.
        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "UPDATE characters SET deleted_at='2026-09-02T00:00:00Z' "
                "WHERE id=?", (self.character.id,))
            db.commit()
        finally:
            db.close()
        with self.assertRaises(KeyError):
            self.answer()


class SchemaDriftIsLoudAndNotNoneTests(_StoreCase):
    """The third exit, named because "the door that does not raise" would
    otherwise be discovered by a login path in production."""

    def test_a_renamed_column_raises_even_with_the_three_vitals_intact(self):
        # `006`'s header pre-announces exactly this rename as "a later, cheap
        # migration".  `read_character_vitals` verifies the WHOLE typed
        # schema, not the three columns this door needs, so the row can be
        # perfectly answerable and the call still raises.  Loud is right for
        # drift -- but a caller told "it never raises" would meet this at
        # login, for every character at once.
        self.seed(level=3, hp_current=50, hp_max=80)
        self.assertEqual(self.answer(), vitals.Vitals(3, 50, 80))
        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "ALTER TABLE characters RENAME COLUMN speed_walk "
                "TO walk_speed")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(vitals.SchemaDriftError) as caught:
            self.answer()
        self.assertIn("speed_walk", str(caught.exception))

    def test_the_drift_error_is_a_vitals_error_so_no_caller_can_miss_it(self):
        self.assertTrue(issubclass(vitals.SchemaDriftError, vitals.VitalsError))


class ABrokenInvariantRaisesRatherThanAnsweringNoneTests(_StoreCase):
    """The one way this method may say "no" is a gap, not a bug."""

    def test_a_complete_but_empty_resolution_raises(self):
        # `VitalsResolution` is public and can be built by hand with no gaps
        # and no values -- a `pf-adversary` pass did exactly that against
        # `require()`.  If that object ever reaches this method, the honest
        # answer is the raise, because `None` here would tell a caller "the
        # database has no answer" about a database nobody asked.
        empty = vitals.VitalsResolution(present={}, gaps=())
        with mock.patch.object(
            SQLiteStore, "read_character_vitals", return_value=empty
        ):
            with self.assertRaises(vitals.VitalsError):
                self.answer()

    def test_a_resolution_with_gaps_is_the_only_none(self):
        gapped = vitals.VitalsResolution(
            present={"level": 1},
            gaps=(vitals.VitalGap("hp_max", "made_up", "for this test"),),
        )
        with mock.patch.object(
            SQLiteStore, "read_character_vitals", return_value=gapped
        ):
            self.assertIsNone(self.answer())


class ItAgreesWithTheDoorItWrapsTests(_StoreCase):
    """The two reads never disagree about the same row."""

    def test_the_pair_agrees_on_every_state_this_file_exercises(self):
        states = (
            {},
            {"level": 5},
            {"level": 0, "hp_current": 100, "hp_max": 100},
            {"level": 3, "hp_current": 120, "hp_max": 100},
            {"level": 9, "hp_current": 10, "hp_max": 10},
        )
        for index, state in enumerate(states):
            with self.subTest(state=state):
                # One fresh database per state, keyed by INDEX and not by
                # `len(state)`: the first draft keyed on the length, two of
                # these states hold three keys, and the second one silently
                # reopened the first one's database.
                store = SQLiteStore(
                    Path(self.tmp.name) / ("agree-%d.sqlite3" % index),
                    MIGRATIONS,
                )
                store.migrate()
                account = store.ensure_account("agree")
                character = store.create_character(
                    account, "AgreeChar%d" % index,
                    "agreechar%d" % index, "fingerprint-agree",
                    _build_wire, self.home,
                )
                pf_birth_state.measure_birth_typed_state(store, character.id)
                # Constructed, not inherited, for the same reason `pre_seed`
                # exists: `{}` and `{"level": 5}` are only "incomplete" while
                # birth writes nothing, and this test is about the two doors
                # agreeing on a NAMED row state rather than on today's.
                pf_birth_state.clear_vitals_to_pre_seed(
                    store.path, [character.id])
                if state:
                    store.write_typed_attributes(character.id, state)
                resolution = store.read_character_vitals(character.id)
                answer = store.read_character_vitals_or_none(character.id)
                if resolution.complete:
                    self.assertEqual(answer, resolution.require())
                else:
                    self.assertIsNone(answer)


class NothingComposesFromThisDoorTests(unittest.TestCase):
    """No file reads this door and hands the result to the attribute composer.

    WHY THIS EXISTS AND WHAT IT IS NOT.  `NothingIsWiredTests` in
    `tests/test_persistence_vitals.py` scans for the NAME of the three older
    vitals store methods; `read_character_vitals_or_none` is deliberately
    absent from that scan, because the day a login path calls this door, that
    call is the wiring this lane asked COO for -- and a name scan would turn
    another lane's PR red for doing it.  A `pf-adversary` pass showed what
    that costs: it wrote a file that calls this door and, on `None`, composes
    `{2: 0, 3: 0, 4: 0}` -- the owner's banned guessed zero, on the field
    where zero means DEAD -- and the whole suite stayed green.

    So this scan pins the DANGEROUS SHAPE rather than the name: a file that
    names this door AND calls the attribute composer/encoder.  The legitimate
    login plug this lane has asked for does not have that shape (it hands
    three numbers to `player_wire`, which builds its own tags), so it stays
    green; the adversary's file does, and goes red.

    WHAT IT CANNOT SEE, said here rather than discovered later: a caller that
    skips the composer and writes `legacy.u32tag(0x14, 0)` itself.  That path
    is caught by neither scan and only review stands there.  It is a SOURCE
    scan like its two siblings: its zero means nobody has written the obvious
    thing.
    """

    DOOR = "read_character_vitals_or_none"
    #: A call to any of these is "putting a value into an attribute block".
    COMPOSERS = ("encode_block", "encode_field", "compose_full_block",
                 "compose_sparse_block", "build_named_field_update")
    #: The file that DEFINES the door, which necessarily names it, and whose
    #: own composer is pinned as caller-driven by
    #: `test_persistence_speed_walk_seed_008.py`.
    DEFINING_FILE = "src/pirateforce_foundation/store.py"

    @classmethod
    def _names(cls, source):
        try:
            with warnings.catch_warnings():
                # `ast.parse` re-raises other files' invalid-escape warnings;
                # they belong to those files, not to this scan.
                warnings.simplefilter("ignore", DeprecationWarning)
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source)
        except SyntaxError:
            return set()
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                seen.add(node.id)
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                seen.add(node.value)
        return seen

    @classmethod
    def _reads_the_door_and_composes(cls, source):
        seen = cls._names(source)
        return cls.DOOR in seen and bool(seen & set(cls.COMPOSERS))

    def test_the_predicate_fires_on_the_shape_the_adversary_wrote(self):
        # The scan is worth running only if it can go off.  This is the
        # adversary's file, shortened.
        self.assertTrue(self._reads_the_door_and_composes(
            "def login_block(store, cid):\n"
            "    answer = store.read_character_vitals_or_none(cid)\n"
            "    if answer is None:\n"
            "        return compose_sparse_block({2: 0, 3: 0, 4: 0})\n"
            "    return compose_sparse_block({2: answer.level})\n"))
        # split across two functions in one file, the evasion its sibling
        # scan was defeated by
        self.assertTrue(self._reads_the_door_and_composes(
            "def load(store, cid):\n"
            "    return store.read_character_vitals_or_none(cid)\n"
            "def send(store, cid):\n"
            "    return encode_block(load(store, cid))\n"))
        # and through a string, the `getattr` evasion
        self.assertTrue(self._reads_the_door_and_composes(
            "def send(store, cid):\n"
            "    v = getattr(store, 'read_character_vitals_or_none')(cid)\n"
            "    return encode_field(2, v.level)\n"))

    def test_the_predicate_leaves_the_plug_this_lane_asked_for_alone(self):
        # The shape of the CORE-REQUEST in this round's letter: read the
        # door, fall back to today's literals, hand three numbers to
        # `player_wire`.  It must not go red -- that is the whole reason the
        # name is not in the sibling scan.
        self.assertFalse(self._reads_the_door_and_composes(
            "def start_game(store, character):\n"
            "    v = store.read_character_vitals_or_none(character.id)\n"
            "    level = PLAYER_LOGIN_LEVEL if v is None else v.level\n"
            "    return make_actor_attr_with_name_and_class(\n"
            "        legacy, lo, hi, scene, seq, name, level=level)\n"))
        # and a file that merely composes, naming no door, is not this
        self.assertFalse(self._reads_the_door_and_composes(
            "def send(values):\n"
            "    return compose_sparse_block(values)\n"))

    def test_no_file_reads_this_door_and_composes_from_it(self):
        offenders = []
        for tree in (ROOT / "src", ROOT / "tools", ROOT / "scenarios",
                     ROOT / "current"):
            if not tree.exists():
                continue
            for path in tree.rglob("*.py"):
                relative = str(path.relative_to(ROOT)).replace("\\", "/")
                if relative == self.DEFINING_FILE:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if self._reads_the_door_and_composes(text):
                    offenders.append(relative)
        self.assertEqual(
            [], sorted(offenders),
            "%r reads `read_character_vitals_or_none` and hands the result "
            "to the attribute composer.  A block composed on the `None` "
            "branch is where the owner's banned guessed zero "
            "(COO-DECISION 20260901_1059) gets onto the HP field, where zero "
            "means DEAD.  If this is a deliberate, adjudicated send, this "
            "test's claim is out of date and must be rewritten with the "
            "decision that authorised it -- not deleted."
            % (sorted(offenders),))

    def test_the_defining_file_is_skipped_for_a_reason_that_still_holds(self):
        """The one skipped path, and the proof it is not a licence: the
        composer in `store.py` composes only the columns its CALLER just
        wrote, which is pinned in
        `tests/test_persistence_speed_walk_seed_008.py::NothingSendsItTests::
        test_the_one_composing_store_method_is_write_first_and_caller_driven`.
        This test fails if that pin ever stops existing."""
        pinned = (ROOT / "tests"
                  / "test_persistence_speed_walk_seed_008.py").read_text(
            encoding="utf-8")
        self.assertIn(
            "def test_the_one_composing_store_method_is_write_first_and_"
            "caller_driven", pinned)
        self.assertTrue((ROOT / self.DEFINING_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
