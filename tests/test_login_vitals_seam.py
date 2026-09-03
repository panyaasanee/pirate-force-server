"""The login sends the level and HP the character's own row holds.

`COO-DECISION 20260903_0647` -- the decision that let this lane land the four
seam points measured in `pf_bridge/notes_to_chief/20260903_0520` point 2 --
names ONE thing as the evidence it counts:

    "a fixture whose `hp_max` is not the constant `main` sends today, so the
     bytes are the fixture's"

and that sentence is the whole design of this file.  `migrations/007` and
`009` seed level 1 / hp 100 / 100, and `player_wire`'s own constants ARE
1 / 100 / 100, so on any newborn character "the login read the row" and "the
login sent its own literals" produce a BYTE-IDENTICAL frame.  That is the
same trap `COO-DECISION 20260903_0054` caught the walk speed in one lane
over, where `migrations/009` gave `speed_walk` a `DEFAULT 400.0` equal to
`PLAYER_LOGIN_MOVEMENT_SPEED` and made the seam unfalsifiable on every live
database including the owner's.  So every end-to-end assertion here runs on a
row written to `7 / 37 / 250`: three numbers no constant in this repository
holds, and an `hp_max` of 250 that no default can produce.

WHAT EACH GROUP IS FOR, AND THE PRODUCTION MUTATION THAT REDDENS IT
-------------------------------------------------------------------
Every mutation named below was applied to the production tree and measured
going red before this file was committed (the table is in the round file).

* `ComposerTests`        -- put either `100` literal back into
                            `player_wire._make_actor_attr_with_name_and_class`
                            instead of the parameter.
* `ProjectorSeamTests`   -- delete any of the three `getattr` reads in
                            `legacy_bridge.start_game`, or drop `**vitals`
                            from either branch.
* `AllThreeOrNoneTests`  -- make `start_game` fill a missing member in from a
                            constant instead of sending none of them
                            (`PANYA-DECISION 20260901_1059`).
* `RecomposeInheritsTests` -- the reason the numbers ride the character: the
                            faction recompose must carry the SAME three, or
                            `runtime.py` puts the constants back on every
                            flagless production login.
* `TheRealLoginPathTests` -- delete the resolve/apply block from
                            `session.select_and_start`.  This is the group
                            that cost the sibling seam a whole round to
                            learn: with that block deleted, every group above
                            it stays green (measured, see the round file).
* `ConsoleTests`         -- print the resolution BEFORE the apply, or drop
                            the apply token from the line
                            (`COO-DECISION 20260903_0647` point 2).

WHAT THIS FILE DOES NOT PROVE
-----------------------------
Nothing here is client-observable (`G5`).  This is the wire/DB layer: the
bytes leaving the composer carry the row's numbers.  Whether a character then
appears on a real screen at level 7 with 37/250 hit points is an attended
ticket, and this file makes no claim about it.
"""
import contextlib
import io
import sqlite3
import struct
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_login_vitals as login_vitals
from pirateforce_foundation import persistence_vitals as vitals
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Character, Position
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation import player_wire
from pirateforce_foundation.player_wire import (
    PLAYER_LOGIN_HP_CURRENT,
    PLAYER_LOGIN_HP_MAX,
    PLAYER_LOGIN_LEVEL,
    make_actor_attr_with_name_and_class,
    make_actor_attr_with_name_class_and_faction,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

IDENTITY_LO = 0x10010001
IDENTITY_HI = 0
SCENE_ID = 1
SCENE_SEQ = 0
NAME = "test01"

#: THE FIXTURE THE DECISION ASKED FOR.  Not one of these three is a constant
#: this repository holds, and `ROW_HP_MAX` in particular is a number no
#: migration default can produce -- which is what makes "the bytes are the
#: row's" a falsifiable sentence rather than a coincidence of equal defaults.
ROW_LEVEL = 7
ROW_HP_CURRENT = 37
ROW_HP_MAX = 250


def _character(level=None, hp_current=None, hp_max=None):
    return Character(
        id=1, account_id=1, selector=0, name=NAME,
        actor_wire=b"", avatar_wire=b"",
        identity_lo=IDENTITY_LO, identity_hi=IDENTITY_HI,
        position=Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0),
        level=level, hp_current=hp_current, hp_max=hp_max,
    )


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def _level_tag(self, level):
        return self.legacy.u16tag(0x12, level)

    def _hp_tags(self, hp_current, hp_max):
        return (self.legacy.u32tag(0x14, hp_current)
                + self.legacy.u32tag(0x14, hp_max))


class TheFixtureIsNotAConstantTests(_LegacyCase):
    """The premise of every other group, asserted rather than assumed.

    A `pf-adversary` pass on the sibling seam measured what happens when this
    is left implicit: `migrations/009` gave `speed_walk` a DEFAULT equal to
    the composer's constant, the end-to-end test began grading a branch it
    did not name, and it stayed green with the seam mutated away.  If a future
    migration ever seeds 7 / 37 / 250, THIS file has to be re-read -- so it
    says so here, once, instead of going quietly unfalsifiable.
    """

    def test_no_fixture_number_is_the_constant_beside_it(self):
        self.assertNotEqual(ROW_LEVEL, PLAYER_LOGIN_LEVEL)
        self.assertNotEqual(ROW_HP_CURRENT, PLAYER_LOGIN_HP_CURRENT)
        self.assertNotEqual(ROW_HP_MAX, PLAYER_LOGIN_HP_MAX)

    def test_the_three_constants_are_what_the_composer_defaults_to(self):
        """The signature defaults and the module constants are two spellings
        of one number, and a drift between them would make the fallbacks
        `session.py` passes differ from what the composer sends on its own --
        two different frames for "the row could not be read"."""
        import inspect

        composer = inspect.signature(
            player_wire._make_actor_attr_with_name_and_class)
        # The private composer takes `level` POSITIONALLY (both wrappers pass
        # it), so only the HP pair has a default to compare here.  The two
        # spellings of `100` -- the literal in this signature and the module
        # constant `session.py` passes as a fallback -- are the pair that
        # must not drift: if they did, "the row could not be read" and "no
        # row was asked for" would put different bytes on the wire.
        self.assertEqual(
            composer.parameters["hp_current"].default, PLAYER_LOGIN_HP_CURRENT)
        self.assertEqual(
            composer.parameters["hp_max"].default, PLAYER_LOGIN_HP_MAX)
        for wrapper in (make_actor_attr_with_name_and_class,
                        make_actor_attr_with_name_class_and_faction):
            with self.subTest(wrapper=wrapper.__name__):
                parameters = inspect.signature(wrapper).parameters
                self.assertEqual(
                    parameters["level"].default, PLAYER_LOGIN_LEVEL)
                self.assertEqual(
                    parameters["hp_current"].default, PLAYER_LOGIN_HP_CURRENT)
                self.assertEqual(
                    parameters["hp_max"].default, PLAYER_LOGIN_HP_MAX)


class ComposerTests(_LegacyCase):
    """`player_wire` emits what it is handed, and its own numbers otherwise."""

    def test_no_arguments_composes_the_constants_byte_for_byte(self):
        frame = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME)
        self.assertIn(
            self._level_tag(PLAYER_LOGIN_LEVEL)
            + self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX),
            frame)

    def test_the_rows_numbers_reach_the_bytes(self):
        frame = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            level=ROW_LEVEL,
            hp_current=ROW_HP_CURRENT, hp_max=ROW_HP_MAX,
        )
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX),
            frame)
        self.assertNotIn(
            self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX),
            frame,
            "the composer emitted its own HP pair as well as the row's -- a "
            "frame with two HP fields is not the frame this seam promises")

    def test_the_faction_composer_carries_them_too(self):
        """`runtime.py` recomposes every flagless production login through
        this one; a pair wired into only the plain composer is a pair the
        recompose puts straight back to the constants."""
        frame = make_actor_attr_with_name_class_and_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            1, level=ROW_LEVEL,
            hp_current=ROW_HP_CURRENT, hp_max=ROW_HP_MAX,
        )
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX),
            frame)

    def test_the_hp_fields_are_fixed_width_so_the_frame_length_is_invariant(self):
        """`runtime.py`'s faction recompose diffs the two frames' lengths and
        refuses on anything but 5 bytes; an HP value that changed the frame
        length would refuse the login rather than mis-draw it."""
        lengths = set()
        for hp in (0, 1, PLAYER_LOGIN_HP_MAX, ROW_HP_MAX, 0xFFFFFFFF):
            lengths.add(len(make_actor_attr_with_name_and_class(
                self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ,
                NAME, hp_current=hp, hp_max=hp)))
        self.assertEqual(len(lengths), 1, lengths)


class ProjectorSeamTests(_LegacyCase):
    """`legacy_bridge.start_game` reads the three numbers OFF the character.

    The group the sibling seam's own file records as the one that catches a
    deleted seam: without it the whole `getattr` block can vanish and every
    composer test above stays green.
    """

    def setUp(self):
        self.projector = LegacyProjector(self.legacy)

    def _pc(self, character, **kwargs):
        """The PC blob alone.  `start_game` returns `(pc, frame)`, and a test
        that forgot the index compares two 2-tuples: every length assertion
        reads 2 and every `assertIn` looks for bytes in a tuple of bytes.
        Measured on the first run of this file, where it turned a passing
        seam red for the wrong reason."""
        pc, _frame = self.projector.start_game(character, **kwargs)
        return pc

    def test_a_character_with_no_vitals_composes_the_constants(self):
        pc = self._pc(_character())
        self.assertIn(
            self._level_tag(PLAYER_LOGIN_LEVEL)
            + self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc)

    def test_a_character_carrying_the_row_composes_the_row(self):
        pc = self._pc(_character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), pc)
        self.assertNotIn(
            self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc)

    def test_the_projector_keeps_no_per_login_state(self):
        """`app.py` builds ONE projector and hands it to every connection, so
        a value parked on `self` would be one player's hit points leaking into
        the next player's frame."""
        carried = self._pc(_character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        plain = self._pc(_character())
        self.assertIn(
            self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), carried)
        self.assertIn(
            self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), plain)
        self.assertNotIn(self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), plain)


class AllThreeOrNoneTests(_LegacyCase):
    """`PANYA-DECISION 20260901_1059` at the projector.

    The owner's letter forbids a frame in which an unknown field is guessed.
    A character carrying two of the three is exactly that situation, and the
    only answer that does not guess is to send NONE of them -- the frame
    `main` sends today, whose numbers are at least all from one source.
    """

    def setUp(self):
        self.projector = LegacyProjector(self.legacy)

    def _constants_frame(self):
        return self.projector.start_game(_character())[0]

    def test_a_missing_level_sends_no_row_number_at_all(self):
        pc = self.projector.start_game(
            _character(None, ROW_HP_CURRENT, ROW_HP_MAX))[0]
        self.assertNotIn(self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), pc)
        self.assertEqual(pc, self._constants_frame())

    def test_a_missing_hp_current_sends_no_row_number_at_all(self):
        pc = self.projector.start_game(
            _character(ROW_LEVEL, None, ROW_HP_MAX))[0]
        self.assertNotIn(self._level_tag(ROW_LEVEL), pc)
        self.assertEqual(pc, self._constants_frame())

    def test_a_missing_hp_max_sends_no_row_number_at_all(self):
        pc = self.projector.start_game(
            _character(ROW_LEVEL, ROW_HP_CURRENT, None))[0]
        self.assertNotIn(self._level_tag(ROW_LEVEL), pc)
        self.assertEqual(pc, self._constants_frame())

    def test_a_character_object_without_the_fields_still_composes(self):
        """Another lane's stub, or a `Character` from before this change:
        `start_game` must compose `main`'s frame rather than raise, because
        `runtime.py`'s START_GAME_REQ handler does not catch `AttributeError`
        and `v141`'s per-connection loop has no `except` at all."""
        class _Old:
            id = 1
            name = NAME
            identity_lo = IDENTITY_LO
            identity_hi = IDENTITY_HI
            position = Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0)
            avatar_wire = b""
            selector = 0

        pc, _frame = self.projector.start_game(_Old())
        self.assertIn(
            self._level_tag(PLAYER_LOGIN_LEVEL)
            + self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc)


class RecomposeInheritsTests(_LegacyCase):
    """Why the numbers ride the character instead of being threaded in.

    `runtime.py` composes `start_game` up to three more times per production
    login from the SAME selected character.  A number threaded into the first
    call only is a number the very next recompose silently replaces with the
    constant: green in a unit test, absent on the wire.
    """

    def setUp(self):
        self.projector = LegacyProjector(self.legacy)

    def test_the_faction_recompose_carries_the_same_three(self):
        character = _character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)
        pc, _frame = self.projector.start_game(character, basic_faction=1)
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), pc)

    def test_the_faction_delta_is_still_exactly_five_bytes(self):
        """`runtime.py`'s own `NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA` check
        refuses anything else, so a widening that moved it would refuse every
        flagless production login."""
        character = _character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)
        plain, _p = self.projector.start_game(character)
        factioned, _f = self.projector.start_game(character, basic_faction=1)
        self.assertEqual(len(factioned) - len(plain), 5)

    def test_a_character_straight_out_of_the_store_carries_none(self):
        """`store._character` does not read the typed columns, so the object
        the store hands back must answer `None` on all three -- which is what
        makes `session.py` the only place that fills them in."""
        with tempfile.TemporaryDirectory() as raw:
            path = str(Path(raw) / "pf.sqlite3")
            store = SQLiteStore(path, ROOT / "migrations")
            store.migrate()
            lifecycle = CharacterLifecycle(
                store, Position(1, 0, 1.0, 2.0, 3.0),
                self.legacy.extract_avatar_attr_wire_from_actor,
            )
            account_id, _s, _c = lifecycle.login("strrow")
            born = lifecycle.create(
                account_id, "strrow", _wire_named(self.legacy, "strrow"))
            stored = store.get_character(born.id)
        self.assertIsNone(stored.level)
        self.assertIsNone(stored.hp_current)
        self.assertIsNone(stored.hp_max)


def _wire_named(legacy, name):
    """The client's own preset actor wire carrying `name`.

    Same idiom as `tests/test_login_speed.py`: the lifecycle validates the
    wire's identity/selector/name, so a hand-rolled blob is refused before
    this file gets to measure anything.
    """
    preset = legacy.get_preset_actor_wire()
    old = legacy.wstr_tag("test01")
    new = legacy.wstr_tag(name)
    assert len(new) == len(old), "test names must be six chars"
    return preset.replace(old, new, 1)


class TheRealLoginPathTests(_LegacyCase):
    """A real store, a real lifecycle, a real `select_and_start`.

    !! THIS IS THE GROUP THE DECISION'S EVIDENCE CLAUSE IS ABOUT, and it is
    also the group the sibling seam had to learn the hard way: with the whole
    resolve-and-apply block deleted from `session.py` -- the only code in the
    repository that ever puts a row's vitals on a login -- every group above
    this one stays green.  None of them executes the production entry point.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "pf.sqlite3")
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.lifecycle = CharacterLifecycle(
            self.store, Position(SCENE_ID, SCENE_SEQ, 1.0, 2.0, 3.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def _born(self, login="rowvit"):
        account_id, _session_id, _characters = self.lifecycle.login(login)
        return self.lifecycle.create(
            account_id, login, _wire_named(self.legacy, login))

    def _session(self, login="rowvit"):
        return FoundationSession(self.lifecycle, self.projector, login)

    def _write_row(self, character_id, level, hp_current, hp_max):
        self.store.write_typed_attributes(character_id, {
            vitals.LEVEL_COLUMN: level,
            vitals.HP_CURRENT_COLUMN: hp_current,
            vitals.HP_MAX_COLUMN: hp_max,
        })

    def test_the_login_sends_the_vitals_the_row_holds(self):
        """The whole claim of this change, end to end, in one test.

        `hp_max=250` is the number `COO-DECISION 20260903_0647` point 5 names:
        no constant and no migration default in this repository produces it,
        so a frame carrying it is a frame that read the row.
        """
        character = self._born()
        self._write_row(character.id, ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)

        session = self._session()
        selected, (pc, _frame) = session.select_and_start(character.selector)

        self.assertEqual(
            (selected.level, selected.hp_current, selected.hp_max),
            (ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_CURRENT, ROW_HP_MAX), pc,
            "the login composed the constants even though the row held other "
            "numbers -- which is the entire defect this change is for")
        self.assertNotIn(
            self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc,
            "the constant HP pair is still in the frame beside the row's")

    def test_the_hp_max_on_the_wire_is_the_one_in_the_database(self):
        """The two ends read INDEPENDENTLY, so neither side can move alone.

        The number on the wire is unpacked out of the frame with `struct`
        rather than compared against `ROW_HP_MAX`, and the number in the
        database is read back through the store: a mutation that corrupts one
        of them cannot cancel itself out of this assertion.
        """
        character = self._born("rowvi2")
        self._write_row(character.id, ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)

        session = self._session("rowvi2")
        _selected, (pc, _frame) = session.select_and_start(character.selector)

        in_database = self.store.read_typed_attributes(character.id)
        prefix = self._level_tag(ROW_LEVEL) + bytes([0x14])
        at = pc.index(prefix) + len(prefix)
        on_the_wire_current = struct.unpack_from("<I", pc, at)[0]
        on_the_wire_max = struct.unpack_from("<I", pc, at + 5)[0]
        self.assertEqual(pc[at + 4], 0x14)
        self.assertEqual(
            on_the_wire_current, in_database[vitals.HP_CURRENT_COLUMN])
        self.assertEqual(on_the_wire_max, in_database[vitals.HP_MAX_COLUMN])

    def test_a_newborn_login_sends_exactly_what_main_sends_today(self):
        """The control, and the reason the fixture above is not 1/100/100.

        `migrations/007` and `009` seed a newborn at the composer's own
        constants, so this login's frame is byte-identical to `main`'s -- and
        that is asserted against a frame composed with NO character at all,
        not against the numbers retyped here.
        """
        character = self._born("plain2")

        session = self._session("plain2")
        _selected, (pc, _frame) = session.select_and_start(character.selector)

        self.assertIn(
            self._level_tag(PLAYER_LOGIN_LEVEL)
            + self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc)

    def test_a_row_that_cannot_be_read_sends_the_constants(self):
        """The worst case of this whole change is `main`'s behaviour.

        The column is emptied with raw SQL because what this branch needs is
        the ABSENCE of a value, and `write_typed_attributes` is the write door
        for values.  NOT `with sqlite3.connect(...)`: that form commits and
        does not close, and the surviving handle makes
        `TemporaryDirectory.cleanup` raise `PermissionError [WinError 32]` on
        the Windows gate -- the failure that closed `#610` and took a whole
        round's diff with it.
        """
        character = self._born("plain3")
        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "UPDATE characters SET hp_max = NULL WHERE id = ?",
                (character.id,))
            db.commit()
        finally:
            db.close()
        self.assertIsNone(
            self.store.read_typed_attributes(character.id).get(
                vitals.HP_MAX_COLUMN),
            "the fixture failed to empty the column, so this test would be "
            "measuring a complete row while claiming an incomplete one")

        session = self._session("plain3")
        selected, (pc, _frame) = session.select_and_start(character.selector)

        self.assertIsNone(selected.hp_max)
        self.assertIn(
            self._level_tag(PLAYER_LOGIN_LEVEL)
            + self._hp_tags(PLAYER_LOGIN_HP_CURRENT, PLAYER_LOGIN_HP_MAX), pc)

    def test_the_seam_changes_no_other_field_of_the_selected_character(self):
        """The three fields are named, so anything else moving is a find.

        Same shape as the sibling seam's guard in
        `tests/test_gm_login_scene_override_position_resync.py`: a
        whole-object comparison with the deliberately-written fields named as
        exemptions, rather than a weaker assertion that would let a login
        quietly change something else.
        """
        character = self._born("rowvi4")
        self._write_row(character.id, ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)

        session = self._session("rowvi4")
        selected, _started = session.select_and_start(character.selector)

        stored = self.store.get_character(character.id)
        self.assertEqual(
            replace(
                selected, level=None, hp_current=None, hp_max=None,
                movement_speed=None),
            stored)

    def test_no_row_this_login_can_read_is_unencodable(self):
        """WHY NO REACHABLE ROW CAN RAISE `struct.error` OUT OF THE COMPOSER.

        `level` is packed `<H` and the HP pair `<I`, and neither call is
        guarded at the composer -- so the question "what does a row holding
        70000 do to a login" has to be answered somewhere, and the answer is
        that such a row CANNOT EXIST.  `migrations/006` puts the range and the
        type in the SCHEMA (`CHECK(level IS NULL OR (typeof(level)='integer'
        AND level BETWEEN 0 AND 65535))`, and the u32 pair likewise), so
        SQLite itself refuses the write -- not the store's validator, which
        another lane's raw SQL could go around, but the table.

        Pinned by attempting the write the way a lane going around every
        Python guard would: raw `sqlite3`, no store.  If a future migration
        ever rebuilds `characters` and drops these CHECKs, this test goes red
        and the composer needs a guard of its own before that migration lands.
        """
        character = self._born("rowvi6")
        db = sqlite3.connect(self.path)
        try:
            for column, value in (
                ("level", 70000), ("level", -1), ("level", 1.5),
                ("hp_current", -1), ("hp_max", 2 ** 33), ("hp_max", "abc"),
            ):
                with self.subTest(column=column, value=value):
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute(
                            f"UPDATE characters SET {column} = ? WHERE id = ?",
                            (value, character.id))
            # !! `"250"` IS NOT IN THAT LIST AND THE OMISSION IS MEASURED, NOT
            # AN OVERSIGHT.  The first draft expected the CHECK to refuse a
            # STRING and it did not: the column has INTEGER affinity, so
            # SQLite converts a numeric string to an integer BEFORE the
            # constraint is evaluated, `typeof` then answers `'integer'`, and
            # the row ends up holding a real 250.  That is the right outcome
            # -- the value on the wire is still an int -- but a test that
            # asserted a refusal here would have been asserting a nonclaim
            # about this schema.  A NON-numeric string has no such conversion
            # and is refused above, which is the case that matters.
            db.execute(
                "UPDATE characters SET hp_max = ? WHERE id = ?",
                ("250", character.id))
            stored = db.execute(
                "SELECT typeof(hp_max), hp_max FROM characters WHERE id = ?",
                (character.id,)).fetchone()
            self.assertEqual(stored, ("integer", 250))
            db.rollback()
        finally:
            db.close()

    def test_a_login_that_reads_a_usable_row_does_not_write_it_back(self):
        """A read seam that persists what it read is a different feature.

        !! THE NAME AND THE DOCSTRING OF THIS TEST USED TO SAY "the login does
        not write the vitals back" AND "the row must be exactly as the fixture
        left it", WHICH IS FALSE OF THIS SEAM (`pf-adversary` defect D3).
        `resolve_for_character` WRITES on one branch -- a row that is
        complete, consistent and DEAD is healed on login (`COO-DECISION
        20260903_0250`) -- and this fixture cannot reach that branch, so the
        old wording was a claim broader than its measurement, which is the
        shape that goes stale in silence.  The write branch is driven by
        `test_a_dead_row_is_revived_by_the_login_itself` below.
        """
        character = self._born("rowvi5")
        self._write_row(character.id, ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)
        before = self.store.read_typed_attributes(character.id)

        session = self._session("rowvi5")
        session.select_and_start(character.selector)

        self.assertEqual(self.store.read_typed_attributes(character.id), before)

    def test_a_dead_row_is_revived_by_the_login_itself(self):
        """THE ONE BRANCH ON WHICH A LOGIN WRITES, DRIVEN THROUGH THE SEAM.

        `_revive_on_login` is covered at module level; a `pf-adversary` pass
        measured that NO test in the repository combined a zero `hp_current`
        with `select_and_start`, so the write that a real login performs was
        graded nowhere.  It is graded here: the row changes, the console says
        so in capitals, and the wire carries the revived numbers rather than
        the composer's literals -- because the row was READ BACK after the
        write (`COO-DECISION 20260903_0447`), not assumed.
        """
        character = self._born("rowvi7")
        self._write_row(character.id, ROW_LEVEL, 0, ROW_HP_MAX)

        session = self._session("rowvi7")
        selected, (pc, _frame) = session.select_and_start(character.selector)

        after = self.store.read_typed_attributes(character.id)
        self.assertEqual(after[vitals.HP_CURRENT_COLUMN], ROW_HP_MAX)
        self.assertEqual(
            (selected.level, selected.hp_current, selected.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX))
        self.assertIn(
            self._level_tag(ROW_LEVEL)
            + self._hp_tags(ROW_HP_MAX, ROW_HP_MAX), pc)

    def test_a_second_login_of_a_revived_character_writes_nothing_more(self):
        """One resolve per login, and the second one finds nothing to heal.

        The hazard `session.py`'s comment names is two resolves in ONE login
        being two revive WRITES; this pins the other axis -- two logins -- so
        a revive cannot become a per-login write on an already-full row.
        """
        character = self._born("rowvi8")
        self._write_row(character.id, ROW_LEVEL, 0, ROW_HP_MAX)
        self._session("rowvi8").select_and_start(character.selector)
        after_first = self.store.read_typed_attributes(character.id)

        self._session("rowvi8").select_and_start(character.selector)

        self.assertEqual(
            self.store.read_typed_attributes(character.id), after_first)


class ConsoleTests(_LegacyCase):
    """`COO-DECISION 20260903_0647` point 2: the line reports the APPLY.

    Printing the resolution alone -- which is what the sibling speed seam does
    -- announces `from_row level=7 hp=37/250` on a login whose frame then
    carries the composer's literals, and it is loudest exactly when the seam
    is most broken.  So the token is graded, not the prose.

    !! EVERY TEST HERE USED TO CALL THE HELPER WITH HAND-BUILT ARGUMENTS, AND
    A `pf-adversary` PASS MEASURED WHAT THAT MISSED (defect D1).  The helper
    took a before and an after and compared them by IDENTITY, so
    `apply=carried` meant "two different objects" rather than "the object
    carries the row" -- it said `carried` for `99/1/2` and for `None`.  The
    surviving mutant was the most natural refactor of the seam there is:
    hoisting `selected = carried` above the print makes both arguments one
    object, and the loud REFUSED token then fires on EVERY CORRECT LOGIN with
    140 tests green.  Two things fix that and both are below: the helper now
    asks the character (one argument, no delta), and
    `TheConsoleAtARealLoginTests` captures what a real `select_and_start`
    actually prints instead of pinning line numbers off the syntax tree.
    """

    def _resolved(self, reason=login_vitals.FROM_ROW):
        return login_vitals.ResolvedLoginVitals(
            ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX, reason)

    def test_a_character_carrying_the_row_says_carried(self):
        line = login_vitals.console_line_after_apply(
            self._resolved(),
            _character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        self.assertIn(login_vitals.APPLY_CARRIED, line)
        self.assertNotIn("REFUSED", line)

    def test_a_character_that_did_not_take_the_row_says_refused(self):
        """The one combination an operator has to be able to grep for: the
        reason names the row and the wire will carry the literals."""
        line = login_vitals.console_line_after_apply(
            self._resolved(), _character())
        self.assertIn(login_vitals.APPLY_REFUSED, line)
        self.assertIn("REFUSED", line)

    def test_a_character_carrying_OTHER_numbers_is_not_called_carried(self):
        """The delta-versus-goal case itself, pinned.  `99/1/2` is a different
        object from the one that went in and carries none of the row, and the
        first draft of this helper called that `apply=carried`."""
        line = login_vitals.console_line_after_apply(
            self._resolved(), _character(99, 1, 2))
        self.assertIn(login_vitals.APPLY_REFUSED, line)

    def test_a_partial_carry_is_not_called_carried(self):
        """All three or none holds here too: two of the row's numbers beside
        one constant is exactly the frame `PANYA-DECISION 20260901_1059`
        forbids, so the console may not report it as the row's."""
        for missing in ("level", "hp_current", "hp_max"):
            with self.subTest(missing=missing):
                kwargs = dict(
                    level=ROW_LEVEL, hp_current=ROW_HP_CURRENT,
                    hp_max=ROW_HP_MAX)
                kwargs[missing] = None
                line = login_vitals.console_line_after_apply(
                    self._resolved(), _character(**kwargs))
                self.assertIn(login_vitals.APPLY_REFUSED, line)

    def test_a_resolution_carrying_the_literals_is_not_called_a_refusal(self):
        """Nothing was offered, so nothing was refused -- putting REFUSED on
        that login's console would report the behaviour that preceded this
        seam as a fault."""
        line = login_vitals.console_line_after_apply(
            self._resolved(login_vitals.ROW_COULD_NOT_BE_READ), _character())
        self.assertIn(login_vitals.APPLY_NOT_OFFERED, line)
        self.assertNotIn("REFUSED", line)

    def test_an_unreadable_resolution_still_leaves_a_line(self):
        line = login_vitals.console_line_after_apply(object(), object())
        self.assertIn(login_vitals.APPLY_UNREADABLE, line)
        self.assertTrue(line.strip())

    def test_a_character_that_cannot_be_read_is_unreadable_not_refused(self):
        """"It did not land" and "it could not be measured" are two findings,
        and one console token for both is one finding lost."""
        line = login_vitals.console_line_after_apply(
            self._resolved(), object())
        self.assertIn(login_vitals.APPLY_UNREADABLE, line)

    def test_it_never_raises_even_on_a_str_subclass(self):
        """A `console_line()` returning a `str` SUBCLASS whose `__format__`
        raises passed the first draft's `isinstance` check and then blew up
        inside the f-string, OUTSIDE any handler (`pf-adversary` defect D4).
        `session.py` catches it, so the login survived and printed NOTHING --
        contradicting the docstring's own promise of a line rather than
        silence."""
        class _Exploding(str):
            def __format__(self, spec):
                raise RuntimeError("boom")

        class _Resolved:
            def console_line(self):
                return _Exploding("x")

            def wire_kwargs(self):
                return {"level": ROW_LEVEL, "hp_current": ROW_HP_CURRENT,
                        "hp_max": ROW_HP_MAX}

        # BOTH BRANCHES, because they build their lines separately: grading
        # only the carried one left the loud REFUSED path free to go back to
        # an f-string and stay green (measured this round, mutant M16c) --
        # and the loud path is the one an operator is told to grep for.
        for character, token in (
            (_character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX),
             login_vitals.APPLY_CARRIED),
            (_character(), login_vitals.APPLY_REFUSED),
        ):
            with self.subTest(token=token):
                line = login_vitals.console_line_after_apply(
                    _Resolved(), character)
                self.assertTrue(line.strip())
                self.assertIn(token, line)

        class _NotOffered(_Resolved):
            def wire_kwargs(self):
                return {}

        line = login_vitals.console_line_after_apply(
            _NotOffered(), _character())
        self.assertIn(login_vitals.APPLY_NOT_OFFERED, line)

    def test_every_line_is_ascii_and_names_an_apply_token(self):
        """The bridge console is cp874 and one character outside that page
        kills the tool mid-report (`AGENTS.md`, the round-86 lesson)."""
        carried = _character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)
        for reason in sorted(login_vitals.REASONS):
            for character in (_character(), carried, object()):
                with self.subTest(reason=reason, character=type(character)):
                    line = login_vitals.console_line_after_apply(
                        self._resolved(reason), character)
                    self.assertTrue(line.isascii(), line)
                    self.assertIn("apply=", line)

    def test_a_character_that_already_held_the_numbers_is_not_refused(self):
        """The newborn case on every live database: the object the apply
        hands back is EQUAL to the one that went in, and a helper that
        compared the two would print REFUSED over a correct login."""
        held = _character(ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX)
        applied = login_vitals.apply_to_character(held, self._resolved())
        self.assertEqual(applied, held)
        line = login_vitals.console_line_after_apply(self._resolved(), applied)
        self.assertIn(login_vitals.APPLY_CARRIED, line)


class TheConsoleAtARealLoginTests(_LegacyCase):
    """WHAT A REAL LOGIN ACTUALLY PRINTS, captured off `stderr`.

    !! THIS CLASS EXISTS BECAUSE EVERY OTHER CONSOLE TEST CALLS THE HELPER
    DIRECTLY, and a `pf-adversary` pass measured the hole that leaves: with
    the seam handing the helper the wrong object, the console said the
    opposite of the truth on every correct login and 140 tests stayed green.
    The AST test below pins the ORDER of the two calls; nothing pinned their
    ARGUMENTS.  So this class asserts the console token against the FRAME'S
    OWN BYTES -- the console and the wire have to agree, or the line an
    operator greps is not evidence about the login it is printed for.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "pf.sqlite3")
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.lifecycle = CharacterLifecycle(
            self.store, Position(SCENE_ID, SCENE_SEQ, 1.0, 2.0, 3.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def _login(self, name, row=None):
        account_id, _s, _c = self.lifecycle.login(name)
        character = self.lifecycle.create(
            account_id, name, _wire_named(self.legacy, name))
        if row is not None:
            self.store.write_typed_attributes(character.id, {
                vitals.LEVEL_COLUMN: row[0],
                vitals.HP_CURRENT_COLUMN: row[1],
                vitals.HP_MAX_COLUMN: row[2],
            })
        session = FoundationSession(self.lifecycle, self.projector, name)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            selected, (pc, _frame) = session.select_and_start(
                character.selector)
        lines = [l for l in captured.getvalue().splitlines()
                 if l.startswith(("LOGIN_VITALS", "!! LOGIN_VITALS"))]
        self.assertEqual(len(lines), 1, captured.getvalue())
        return lines[0], selected, pc, character

    def test_the_console_says_carried_exactly_when_the_wire_takes_the_row(self):
        line, _selected, pc, _character = self._login(
            "conrow", (ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        on_the_wire = (
            self.legacy.u16tag(0x12, ROW_LEVEL)
            + self.legacy.u32tag(0x14, ROW_HP_CURRENT)
            + self.legacy.u32tag(0x14, ROW_HP_MAX)) in pc
        self.assertTrue(on_the_wire, line)
        self.assertIn(login_vitals.APPLY_CARRIED, line)
        self.assertNotIn("REFUSED", line)
        self.assertIn(str(ROW_HP_MAX), line)

    def test_a_correct_newborn_login_never_shouts_refused(self):
        """The mutant that fixing defect D1 killed: on a fresh database every
        login is this one, so a helper that reported it as REFUSED would put
        the loud token on the console of every player in the game."""
        line, _selected, _pc, _character = self._login("connew")
        self.assertNotIn("REFUSED", line)
        self.assertIn(login_vitals.APPLY_CARRIED, line)

    def test_an_unusable_row_says_not_offered_and_the_wire_agrees(self):
        line, selected, pc, _character = self._login("congap", (0, 5, 10))
        self.assertIn(login_vitals.APPLY_NOT_OFFERED, line)
        self.assertIsNone(selected.level)
        self.assertIn(
            self.legacy.u16tag(0x12, PLAYER_LOGIN_LEVEL)
            + self.legacy.u32tag(0x14, PLAYER_LOGIN_HP_CURRENT)
            + self.legacy.u32tag(0x14, PLAYER_LOGIN_HP_MAX), pc)

    def test_the_numbers_the_console_prints_are_the_numbers_on_the_wire(self):
        """The whole point of printing after the apply: a console that names
        numbers no login sent is a lie an operator acts on.  Read off the
        printed line by parsing it, not by retyping the fixture."""
        import re

        line, _selected, pc, _character = self._login(
            "conwir", (ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX))
        match = re.search(r"level=(\d+) hp=(\d+)/(\d+)", line)
        self.assertIsNotNone(match, line)
        level, current, maximum = (int(g) for g in match.groups())
        self.assertIn(
            self.legacy.u16tag(0x12, level)
            + self.legacy.u32tag(0x14, current)
            + self.legacy.u32tag(0x14, maximum), pc,
            "the console named three numbers the frame does not carry")

    def test_the_seam_passes_the_composers_own_constants_as_its_fallbacks(self):
        """THE THIRD SPELLING OF `100`, pinned (`pf-adversary` defect D2).

        The signature default and the module constant are pinned against each
        other elsewhere in this file; what `session.py` PASSES was pinned by
        nothing, and it is the spelling that reaches the operator's eyes.
        Drifting all three left 140 tests green while a real login printed
        `level=99 hp=1/7` and sent `1/100/100`.  Read off the syntax tree
        because the value never reaches a frame -- there is no byte to
        measure it by, which is exactly why it needed a guard of its own.
        """
        import ast

        text = (ROOT / "src" / "pirateforce_foundation"
                / "session.py").read_text(encoding="utf-8")
        wanted = {
            "fallback_level": "PLAYER_LOGIN_LEVEL",
            "fallback_hp_current": "PLAYER_LOGIN_HP_CURRENT",
            "fallback_hp_max": "PLAYER_LOGIN_HP_MAX",
        }
        seen = {}
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg in wanted:
                    seen[keyword.arg] = ast.unparse(keyword.value)
        self.assertEqual(set(seen), set(wanted), seen)
        for name, constant in wanted.items():
            with self.subTest(fallback=name):
                self.assertEqual(seen[name], f"player_wire.{constant}")


    def test_the_seam_prints_after_the_apply_not_before(self):
        """The ORDER, read off `session.py`'s syntax tree.

        Kept beside the end-to-end captures above rather than instead of
        them: at runtime the same sentence comes out either way on a login
        whose apply lands, so the order is invisible to a capture and
        visible only here -- and the captures are what pin the ARGUMENTS,
        which is the half this test cannot see (`pf-adversary` defect D1).
        """
        import ast

        text = (ROOT / "src" / "pirateforce_foundation"
                / "session.py").read_text(encoding="utf-8")
        apply_at = print_at = None
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None)
            if name == "apply_to_character":
                apply_at = node.lineno
            elif name == "console_line_after_apply":
                print_at = node.lineno
        self.assertIsNotNone(apply_at, "the seam does not apply")
        self.assertIsNotNone(
            print_at,
            "the seam prints `console_line()` rather than the line that can "
            "report a refused apply (COO-DECISION 20260903_0647 point 2)")
        self.assertLess(apply_at, print_at)


if __name__ == "__main__":
    unittest.main()
