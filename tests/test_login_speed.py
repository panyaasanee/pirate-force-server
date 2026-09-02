"""The login's movement speed comes from the character's row.

CORE-REQUEST `pf_bridge/notes_to_chief/20260902_2010_LANE-DB-CORE-REQUEST-
chief-login-speed-comes-from-the-row-not-a-constant.md`, ordered by
`COO-DECISION 20260902_1846` point 3.

WHAT EACH GROUP IN THIS FILE IS FOR, AND THE MUTATION THAT REDDENS IT
---------------------------------------------------------------------
The R309 round file recorded a defect (D5) worth not repeating: an entire
wiring could be DELETED and the test file stayed green, because every test
drove the module and none drove the seam.  So each group below names the
production mutation it catches, and every one of those mutations was applied
and measured going red before this file was committed:

* `ResolverTests`             -- change any fallback branch to return 0.0, or
                                 drop the validator call.
* `ComposerTests`             -- delete `movement_speed=` from either public
                                 composer, or make `_login_movement_speed`
                                 ignore its argument.
* `FrameLengthIsInvariantTests` -- make the speed emission variable-width.
* `SeamTests`                 -- delete the `speed = getattr(character, ...)`
                                 line in `legacy_bridge.start_game` (this is
                                 the D5 mutation: without this group the
                                 whole seam can vanish and the file stays
                                 green).
* `RecomposeInheritsTests`    -- the reason the value rides the character:
                                 a faction recompose must carry the SAME
                                 speed the login composed, not the constant.
* `TheRealLoginPathTests`     -- delete the read-and-attach block in
                                 `session.select_and_start`.

!! THAT LAST GROUP WAS ADDED AFTER AN ADVERSARY PASS PROVED EVERY GROUP ABOVE
IT INSUFFICIENT, and the measurement is the point: with the whole
read-the-row-and-attach block deleted from `session.py` -- the only code in
the repository that ever puts a row value on a login -- this file still
reported 24 passed.  Every earlier group drives the resolver, the composers,
or the projector; none of them executed the production entry point, and none
of them ever paired `login_speed` with a real `SQLiteStore`.  That is R309's
defect D5 one layer up, in the file whose docstring claims to prevent it.
The lesson generalises past this feature: a mutation table is only as good as
its worst-covered LAYER, and "I mutated four things and they all went red"
says nothing about a fifth layer nobody drives.

WHAT THIS FILE DOES NOT PROVE
-----------------------------
Nothing here is client-observable (`G5`).  This is the wire/DB layer only:
the bytes leaving the composer carry the row's number.  Whether the character
then WALKS at that speed on a real screen is an attended ticket, and the
`GT-193` evidence says that half is not a formality.

And it does not prove anything CHANGES today -- but the REASON is no longer
the one this docstring gave when it was written, and the correction matters
more than the sentence it replaces.  It used to say `speed_walk` is NULL for
every character born after `migrations/008`.  `migrations/009` then landed
with `speed_walk REAL DEFAULT 400.0`, so a newborn's row now HOLDS a value
and the production path takes `FROM_ROW`, not `ROW_HAS_NO_VALUE`.  Nothing on
the wire changes anyway, because that DEFAULT is numerically the same as
`player_wire.PLAYER_LOGIN_MOVEMENT_SPEED` -- which is exactly the hazard:
the two branches are byte-identical on a fresh database, so no assertion
about the NUMBER can tell them apart, and one that tries is unfalsifiable.
Only the ATTACHED VALUE separates them (`session.py` attaches on `FROM_ROW`
alone), and that is what `test_a_row_with_no_value_sends_the_constant` now
pins, after emptying the column itself instead of trusting a migration
another lane owns.  [pf-adversary, round `eww6tv`.]
"""
import ast
import sqlite3
import struct
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import login_speed
from pirateforce_foundation import persistence_typed_attrs as typed_attrs
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Character, Position
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.player_wire import (
    PLAYER_LOGIN_MOVEMENT_SPEED,
    make_actor_attr_with_name_and_class,
    make_actor_attr_with_name_class_and_faction,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

IDENTITY_LO = 0x10010001
IDENTITY_HI = 0
SCENE_ID = 1
SCENE_SEQ = 0
NAME = "test01"

# A speed that is NOT the constant and NOT the column default, so a frame
# carrying it cannot be a frame that ignored the row.  300.0 is the value the
# owner's own `/speed 300` session used (`GT-193`), and it survives
# `persistence_typed_attrs.validate` exactly (a float32 with no rounding).
ROW_SPEED = 300.0


class _StoreStub:
    """What `store.read_typed_attributes` does, and nothing else.

    A stub rather than a real database because this file grades the RESOLVER
    and the SEAM, not SQLite; the round-trip through a real store is
    `tests/test_birth_vitals_plug_is_pinned.py`'s business.  It reproduces the
    one behaviour the resolver depends on: a column with no value is OMITTED
    from the mapping rather than rendered as `0`.
    """

    def __init__(self, attributes=None, raises=None):
        self._attributes = dict(attributes or {})
        self._raises = raises

    def read_typed_attributes(self, character_id):
        if self._raises is not None:
            raise self._raises
        return dict(self._attributes)


def _character(movement_speed=None):
    return Character(
        id=1, account_id=1, selector=0, name=NAME,
        actor_wire=b"", avatar_wire=b"",
        identity_lo=IDENTITY_LO, identity_hi=IDENTITY_HI,
        position=Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0),
        movement_speed=movement_speed,
    )


class ResolverTests(unittest.TestCase):
    """The value goes out, or the constant does, and the reason is named."""

    def test_a_row_value_is_what_the_login_sends(self):
        resolved = login_speed.resolve(
            ROW_SPEED, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, ROW_SPEED)
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)
        self.assertTrue(resolved.came_from_the_row)

    def test_no_value_falls_back_to_the_constant_and_never_to_zero(self):
        resolved = login_speed.resolve(
            None, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.ROW_HAS_NO_VALUE)
        self.assertNotEqual(
            resolved.value, 0.0,
            "COO-DECISION 20260901_1059: an unseeded column is an absence, "
            "and a zero on this wire is a value")

    def test_the_validator_is_the_gate_not_a_range_retyped_here(self):
        """Whatever `validate` refuses, this refuses -- with its message.

        The point of this test is that there is no second range in
        `login_speed`: it is the write path's own validator that decides, so
        the two can never disagree about the same number.
        """
        for bad in (float("nan"), float("inf"), "fast", True, 1e-310):
            with self.subTest(bad=bad):
                with self.assertRaises(typed_attrs.TypedAttrError):
                    typed_attrs.validate(login_speed.COLUMN, bad)
                resolved = login_speed.resolve(
                    bad, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(
                    resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(
                    resolved.reason, login_speed.ROW_REFUSED_BY_VALIDATOR)
                self.assertTrue(
                    resolved.detail,
                    "a refusal that says nothing is a refusal nobody can act "
                    "on (R309 defect D3)")

    def test_a_read_that_raises_never_fails_the_login(self):
        for error in (KeyError(1), RuntimeError("db is gone")):
            with self.subTest(error=type(error).__name__):
                resolved = login_speed.resolve_for_character(
                    _StoreStub(raises=error), 1,
                    fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(
                    resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED,
                    "the worst case of this change is the behaviour that "
                    "preceded it")
                self.assertEqual(
                    resolved.reason, login_speed.ROW_COULD_NOT_BE_READ)

    def test_a_store_that_omits_the_column_reads_as_no_value(self):
        resolved = login_speed.resolve_for_character(
            _StoreStub({"level": 7}), 1,
            fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.ROW_HAS_NO_VALUE)

    def test_a_store_that_holds_the_column_reads_as_the_row(self):
        resolved = login_speed.resolve_for_character(
            _StoreStub({"speed_walk": ROW_SPEED}), 1,
            fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, ROW_SPEED)
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)

    def test_only_speed_walk_is_resolved_here(self):
        """`COO-DECISION 20260902_1846` point 3 bound this to one column."""
        self.assertEqual(login_speed.COLUMN, "speed_walk")

    def test_every_console_line_is_ascii_and_names_a_registered_reason(self):
        """cp874: a character outside the page kills the bridge's tooling."""
        for stored in (None, ROW_SPEED, float("nan"), "fast"):
            with self.subTest(stored=stored):
                resolved = login_speed.resolve(
                    stored, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
                line = resolved.console_line()
                line.encode("ascii")
                self.assertTrue(line.startswith("LOGIN_SPEED "))
                self.assertIn(resolved.reason, login_speed.REASONS)

    def test_an_unregistered_reason_cannot_be_constructed(self):
        with self.assertRaises(ValueError):
            login_speed.ResolvedLoginSpeed(400.0, "made_up")

    def test_a_speed_a_player_cannot_use_falls_back_and_says_so(self):
        """The one floor this module owns, and the reason it owns it.

        `persistence_typed_attrs.validate` ADMITS both of these -- it bounds
        the column to the whole f32 range and refuses only a nonzero value
        that underflows to zero.  That is right for a validator protecting
        SQLite and the encoder and wrong for a value about to be painted
        into the client's BasicAttr `+0x54`: `/speed 0` would commit a row
        whose frame is deferred (so nothing visible happens in that session)
        and then the NEXT login makes the character unable to walk.
        """
        for bad in (0.0, -0.0, -600.0, -1e-30):
            with self.subTest(bad=bad):
                # Compared as "still not positive", not for equality: the
                # validator returns the f32-ROUNDED number, so `-1e-30`
                # comes back as `-1.0000000031710769e-30`.  What matters
                # here is that the write path ADMITS it at all -- if it ever
                # starts refusing these, the floor below is redundant and
                # this test is where that should be noticed.
                self.assertLessEqual(
                    typed_attrs.validate(login_speed.COLUMN, bad), 0.0,
                    "the write path now refuses this, so the floor below "
                    "may be redundant -- re-read both before deleting either")
                resolved = login_speed.resolve(
                    bad, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(
                    resolved.reason, login_speed.ROW_SPEED_NOT_POSITIVE)
                self.assertTrue(resolved.detail)
                resolved.console_line().encode("ascii")

    def test_the_smallest_usable_speed_still_gets_through(self):
        """The floor is `> 0`, not a made-up minimum.

        This module has no evidence for any particular lower bound, so it
        does not invent one; a tiny positive speed is a bad idea and is NOT
        this seam's business to refuse.
        """
        resolved = login_speed.resolve(
            1.0, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, 1.0)
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)


class _LegacyCase(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)


class ComposerTests(_LegacyCase):
    """The composers emit the speed they are handed."""

    def _speed_in(self, actor):
        """Every f32 tag in the frame, so the assertion names bytes."""
        tag = self.legacy.f32tag(ROW_SPEED)
        return tag in actor

    def test_none_keeps_the_constant_byte_for_byte(self):
        explicit = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            movement_speed=PLAYER_LOGIN_MOVEMENT_SPEED,
        )
        default = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        self.assertEqual(
            default, explicit,
            "a caller with no row must compose exactly what main composes")

    def test_a_row_speed_reaches_the_bytes(self):
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            movement_speed=ROW_SPEED,
        )
        self.assertTrue(self._speed_in(actor))
        self.assertNotIn(
            self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), actor,
            "the constant must be GONE from the frame, not merely joined")

    def test_the_faction_composer_carries_it_too(self):
        actor = make_actor_attr_with_name_class_and_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            1, movement_speed=ROW_SPEED,
        )
        self.assertTrue(self._speed_in(actor))

    def test_a_value_the_encoder_cannot_carry_is_refused_not_coerced(self):
        """The rule is the float32 rule, not `math.isfinite`.

        The last two rows are the holes pf-adversary measured in the first
        draft, which checked only finiteness: `3.5e38` is finite and outside
        float32, so it reached `struct.pack` and raised `OverflowError` --
        an `ArithmeticError`, caught by NONE of the four handlers guarding
        these composers, so it unwinds the listener thread.  And `1e-320` is
        finite, packs happily, and lands on the client as an exact `0.0` --
        the guessed zero the persistence validator refuses by name, arriving
        through a composer that never asked.  Both are `ValueError` now,
        which every one of those handlers does catch.
        """
        for bad, error in (
            (float("nan"), ValueError), (float("inf"), ValueError),
            ("fast", TypeError), (True, TypeError),
            (3.5e38, ValueError), (-3.5e38, ValueError),
            (1e-320, ValueError), (-1e-320, ValueError),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(error):
                    make_actor_attr_with_name_and_class(
                        self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID,
                        SCENE_SEQ, NAME, movement_speed=bad,
                    )


class FrameLengthIsInvariantTests(_LegacyCase):
    """The speed cannot change the frame's length, and two guards need that.

    runtime.py's flagless production faction recompose refuses on any length
    delta other than the faction field's 5 bytes, and the scene-override
    resync compares lengths outright.  A variable-width speed would turn both
    into a silent fallback to the unmodified bytes on every login -- which is
    exactly the shape of a bug that hides for days.
    """

    def test_every_speed_composes_the_same_length(self):
        lengths = {
            len(make_actor_attr_with_name_and_class(
                self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ,
                NAME, movement_speed=speed,
            ))
            for speed in (None, 0.5, 1.0, ROW_SPEED,
                          PLAYER_LOGIN_MOVEMENT_SPEED, 65535.0, -1.0)
        }
        self.assertEqual(
            len(lengths), 1,
            f"the speed changed the frame length: {sorted(lengths)}")

    def test_the_faction_delta_is_still_exactly_five_bytes(self):
        plain = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            movement_speed=ROW_SPEED,
        )
        faction = make_actor_attr_with_name_class_and_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            1, movement_speed=ROW_SPEED,
        )
        self.assertEqual(len(faction), len(plain) + 5)

    def test_the_composers_f32_ceiling_is_the_persistence_layers(self):
        """Two copies of one number, pinned to each other rather than to a
        literal.  `player_wire` names it so it can refuse an out-of-range
        speed without importing the persistence layer; if the two ever drift,
        a value the database accepts starts raising inside the encoder.
        """
        from pirateforce_foundation import player_wire
        self.assertEqual(player_wire._F32_MAX, typed_attrs.F32_MAX)

    def test_an_f32_tag_is_fixed_width(self):
        widths = {len(self.legacy.f32tag(v))
                  for v in (0.0, 1.0, ROW_SPEED, 1e30, -1e30)}
        self.assertEqual(widths, {5}, "tag byte plus a packed float32")


class SeamTests(_LegacyCase):
    """The projector reads the speed OFF THE CHARACTER.

    This is the group R309's defect D5 says has to exist: without it, the
    whole `legacy_bridge` wiring can be deleted and every other test in this
    file stays green, because they all drive the composers directly.
    """

    def setUp(self):
        super().setUp()
        self.projector = LegacyProjector(self.legacy)

    def test_a_character_with_no_speed_composes_the_constant(self):
        pc, _frame = self.projector.start_game(_character())
        self.assertIn(self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)

    def test_a_character_carrying_a_speed_composes_that_speed(self):
        pc, _frame = self.projector.start_game(
            _character(movement_speed=ROW_SPEED))
        self.assertIn(self.legacy.f32tag(ROW_SPEED), pc)

    def test_the_two_frames_are_the_same_length(self):
        plain, _ = self.projector.start_game(_character())
        carried, _ = self.projector.start_game(
            _character(movement_speed=ROW_SPEED))
        self.assertEqual(len(plain), len(carried))

    def test_the_projector_keeps_no_per_login_state(self):
        """app.py builds ONE projector for the whole server.

        So a speed parked on the projector by one connection would be the
        next connection's speed.  Composing a carrying character and then a
        plain one, through the SAME projector, has to give the plain one the
        constant back.
        """
        self.projector.start_game(_character(movement_speed=ROW_SPEED))
        pc, _frame = self.projector.start_game(_character())
        self.assertIn(self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)
        self.assertNotIn(self.legacy.f32tag(ROW_SPEED), pc)


class RecomposeInheritsTests(_LegacyCase):
    """Why the value rides the character instead of being an argument.

    runtime.py recomposes the START_GAME frame with `basic_faction=1` on
    every flagless production login, passing `self.foundation.selected`.  If
    the speed had been threaded into the login call alone, this recompose --
    which REPLACES pc/frame -- would put the constant straight back, and the
    whole change would be green in unit tests and absent on the wire.
    """

    def setUp(self):
        super().setUp()
        self.projector = LegacyProjector(self.legacy)

    def test_the_faction_recompose_carries_the_same_speed(self):
        carrying = _character(movement_speed=ROW_SPEED)
        login_pc, _ = self.projector.start_game(carrying)
        faction_pc, _ = self.projector.start_game(carrying, basic_faction=1)
        self.assertIn(self.legacy.f32tag(ROW_SPEED), login_pc)
        self.assertIn(
            self.legacy.f32tag(ROW_SPEED), faction_pc,
            "the recompose dropped back to the constant, which is the "
            "no-op this design exists to prevent")
        self.assertEqual(len(faction_pc), len(login_pc) + 5)

    def test_a_replaced_character_keeps_carrying_it(self):
        """session.py attaches the speed with `dataclasses.replace`."""
        carrying = replace(_character(), movement_speed=ROW_SPEED)
        pc, _frame = self.projector.start_game(carrying)
        self.assertIn(self.legacy.f32tag(ROW_SPEED), pc)

    def test_a_character_straight_out_of_the_store_carries_none(self):
        """`store._character` is LANE-DB's and was not touched.

        A character built the way the store builds it must therefore arrive
        with `movement_speed=None` and behave exactly as main behaves today.
        """
        positional = Character(
            1, 1, 0, NAME, b"", b"", IDENTITY_LO, IDENTITY_HI,
            Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0),
        )
        self.assertIsNone(positional.movement_speed)
        pc, _frame = self.projector.start_game(positional)
        self.assertIn(self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)


class TheRowValueSurvivesTheWireTests(_LegacyCase):
    """The number in the row is the number in the bytes, not a near miss.

    `persistence_typed_attrs.validate` rounds an f32 column to float32 so the
    database and the client cannot quietly disagree.  This reads the float
    back OUT of the composed frame and compares it to what the resolver
    returned, which is the only assertion in this file that grades the whole
    path end to end in one number.
    """

    def test_the_float_read_back_out_of_the_frame_is_the_resolved_one(self):
        for stored in (ROW_SPEED, 123.5, 400.0, 1.0):
            with self.subTest(stored=stored):
                resolved = login_speed.resolve(
                    stored, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
                projector = LegacyProjector(self.legacy)
                pc, _frame = projector.start_game(
                    _character(movement_speed=resolved.value))
                tag = self.legacy.f32tag(resolved.value)
                at = pc.find(tag)
                self.assertNotEqual(at, -1, "the speed tag is not in the frame")
                (read_back,) = struct.unpack("<f", pc[at + 1:at + 5])
                self.assertEqual(read_back, resolved.value)


class TheRealLoginPathTests(_LegacyCase):
    """A real store, a real lifecycle, a real `select_and_start`.

    !! THIS CLASS EXISTS BECAUSE EVERYTHING ABOVE IT WAS NOT ENOUGH, AND THAT
    WAS MEASURED, NOT SUSPECTED.  A pf-adversary pass deleted the ENTIRE
    read-the-row-and-attach block from `session.select_and_start` -- the only
    code in the repository that ever puts a row value on a login -- and this
    file stayed at 24 passed.  Every other test here drives the resolver, the
    composers, or the projector directly; not one of them executed the seam.
    That is R309's defect D5 exactly, moved up one layer, in the very file
    whose docstring says it exists to prevent it.

    So this class pairs `login_speed` with a REAL `SQLiteStore` for the first
    time and drives the production entry point.  Delete the wiring and these
    go red.
    """

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "pf.sqlite3")
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.lifecycle = CharacterLifecycle(
            self.store, Position(1, 0, 1.0, 2.0, 3.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def _wire_named(self, name):
        """The client's own preset actor wire carrying `name`.

        Same idiom as `tests/test_character_identity_binding.py`: the
        lifecycle validates the wire's identity/selector/name, so a
        hand-rolled blob is refused before this file gets to measure
        anything.
        """
        preset = self.legacy.get_preset_actor_wire()
        old = self.legacy.wstr_tag("test01")
        new = self.legacy.wstr_tag(name)
        self.assertEqual(len(new), len(old), "test names must be six chars")
        return preset.replace(old, new, 1)

    def _born(self, login="rowspd"):
        account_id, _session_id, _characters = self.lifecycle.login(login)
        return self.lifecycle.create(
            account_id, login, self._wire_named(login))

    def _session(self, login="rowspd"):
        return FoundationSession(self.lifecycle, self.projector, login)

    def test_the_login_sends_the_speed_the_row_holds(self):
        """The whole claim of this change, end to end, in one test."""
        character = self._born()
        self.store.write_typed_attributes(
            character.id, {login_speed.COLUMN: ROW_SPEED})

        session = self._session()
        selected, (pc, _frame) = session.select_and_start(character.selector)

        self.assertEqual(selected.movement_speed, ROW_SPEED)
        self.assertIn(
            self.legacy.f32tag(ROW_SPEED), pc,
            "the login composed the constant even though the row held "
            "another number -- which is the entire defect this change is for")

    def test_a_row_with_no_value_sends_the_constant(self):
        """The ROW_HAS_NO_VALUE branch, driven end to end.

        !! THIS TEST'S ORIGINAL PREMISE WENT STALE UNDER IT AND IT KEPT
        PASSING, WHICH IS THE WHOLE REASON THE BODY BELOW LOOKS LIKE THIS.
        It used to say: "`migrations/006` adds the column NULLable with no
        DEFAULT and `008` is a one-shot seed of the EXISTING cohort, so a
        character born after `008` has no value here" -- and it asserted only
        that the constant appears on the wire.  `migrations/009` then landed
        with `speed_walk REAL DEFAULT 400.0`, so a newborn's row DOES hold a
        value, this test began walking FROM_ROW instead of ROW_HAS_NO_VALUE,
        and it stayed green ONLY because that DEFAULT is numerically the same
        as `player_wire.PLAYER_LOGIN_MOVEMENT_SPEED`.  Two different branches,
        one byte-identical wire, and nothing said so.  [pf-adversary, round
        `eww6tv`; the same measurement retired the sibling claim in
        `login_speed.py`'s docstring.]

        So the row is emptied explicitly rather than assumed empty -- a
        fixture that STATES its precondition instead of inheriting it from a
        migration another lane owns -- and the branch is pinned by the
        attached value, which is `None` for every reason except FROM_ROW, not
        by a number that both branches produce.
        """
        character = self._born("plain1")
        # Raw SQL on purpose: `write_typed_attributes` is the write door for
        # VALUES, and what this test needs is the ABSENCE of one.  Emptying
        # the column is also the only way to reach this branch now that 009
        # fills it at birth.
        # NOT `with sqlite3.connect(...) as db:`.  That form commits and does
        # NOT close, the surviving handle is invisible on Linux, and on the
        # Windows gate `TemporaryDirectory.cleanup` then raises
        # `PermissionError: [WinError 32]` at teardown.  It is what took this
        # whole change down once already as `#610` (`1 failed / 7148 passed`,
        # the pull request closed by the workflow, the diff lost, and `main`
        # left red for every lane meanwhile) after `#495` before it.
        # This comment is NOT what protects the line -- comments do not fail.
        # `NoUnclosedSqliteHandleInThisFileTests` at the bottom of this file
        # does, and it was measured going red on both spellings of the leak
        # (the bare `with`, and dropping only `close()`).  Deleting that class
        # takes this file back to `32 passed` with the leak in place, which is
        # exactly the state `#610` was written and measured in.
        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "UPDATE characters SET speed_walk = NULL WHERE id = ?",
                (character.id,))
            db.commit()
        finally:
            db.close()
        self.assertIsNone(
            self.store.read_typed_attributes(character.id).get(
                login_speed.COLUMN),
            "the fixture failed to empty the column, so this test would be "
            "measuring FROM_ROW again while claiming ROW_HAS_NO_VALUE")

        session = self._session("plain1")
        selected, (pc, _frame) = session.select_and_start(character.selector)

        self.assertIn(self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)
        # THE LINE THAT MAKES THIS TEST FALSIFIABLE.  `session.py` attaches
        # the resolved value only `if resolved.came_from_the_row`, so `None`
        # here is the branch itself, distinguishable from a row that happened
        # to hold the constant.
        self.assertIsNone(selected.movement_speed)

    def test_a_zero_in_the_row_does_not_reach_the_client(self):
        """`/speed 0` stores and encodes; it must not brick a character.

        `persistence_typed_attrs.validate` admits `0.0` (it refuses only a
        nonzero value that UNDERFLOWS to zero), so before the positive floor
        in `login_speed` this row would have painted `0.0` into the login
        ActorAttr and the character could not walk -- with the deferred
        `/speed` frame meaning nothing visible happened in the session that
        typed it.  `GT-193` is the standing evidence for what a wrong number
        on this field costs.
        """
        for bad in (0.0, -600.0):
            with self.subTest(bad=bad):
                login = "flr%03d" % (abs(int(bad)) % 1000,)
                character = self._born(login)
                self.store.write_typed_attributes(
                    character.id, {login_speed.COLUMN: bad})
                session = self._session(login)
                selected, (pc, _frame) = session.select_and_start(
                    character.selector)
                self.assertIn(
                    self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)
                # Graded on the SEAM, not by hunting the byte pattern in the
                # frame: `f32tag(0.0)` also appears in the MovementAttr's
                # position floats, so an `assertNotIn` here would be green or
                # red depending on the fixture's coordinates rather than on
                # the behaviour (pf-adversary's fragile-by-fixture warning,
                # measured -- the first draft of this assertion failed for
                # exactly that reason).  `movement_speed is None` says the
                # row value was refused and nothing was attached, which is
                # the claim.
                self.assertIsNone(
                    selected.movement_speed,
                    "a speed a player cannot use was attached to the login")

    def test_the_scene_load_session_deliberately_does_not_read_the_row(self):
        """The divergence this change accepts, pinned so it stays a choice.

        `ReadOnlyFoundationSession` holds a store and a character id and
        could resolve the speed -- an adversary pass raised exactly that.
        It must not: `tests/test_action_ack.py` snapshots the database file
        AND its `-wal`/`-shm` sidecars around a StartGame on that path and
        requires them byte-identical, and `read_typed_attributes` opens its
        own connection, so a READ alone creates sidecars that were not there.
        "Read-only" on that milestone means no trace on disk, not merely no
        UPDATE.

        So a `--scene-load` boot composes the constant even when the row
        holds another number.  A future round that closes this needs a read
        that opens no connection; this test is here so that round has to
        notice the reason rather than rediscover it by turning
        `test_action_ack` red.
        """
        import inspect
        from pirateforce_foundation import session as session_module
        source = inspect.getsource(
            session_module.ReadOnlyFoundationSession.select_and_start)
        self.assertNotIn(
            "resolve_for_character", source,
            "the scene-load session started reading the row -- see this "
            "test's docstring for the sidecar guard that forbids it")

    def test_the_seam_survives_a_lifecycle_that_has_no_store(self):
        """The crash pf-adversary measured: `AttributeError` from the two
        lookups, one line above the try that is supposed to absorb them.

        `AttributeError` is caught by none of runtime.py's START_GAME
        handlers and v141's connection loop has no `except` at all, so an
        escape here unwinds the listener thread with the client parked on
        "connecting".  A stub lifecycle stands in for every caller that never
        promised this seam a store.
        """
        resolved = login_speed.resolve_for_character(
            None, None, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.ROW_COULD_NOT_BE_READ)
        self.assertIn(
            "AttributeError", resolved.detail,
            "the reason must name what actually went wrong; two different "
            "database faults printing one identical line is not evidence")


class NoUnclosedSqliteHandleInThisFileTests(unittest.TestCase):
    """The only thing in this round that can actually GO RED.

    !! THIS CLASS IS HERE BECAUSE PROSE HAS NOW FAILED TWICE.  The trap it
    pins -- `with sqlite3.connect(path) as db:`, which commits on exit and
    does NOT close -- has closed two pull requests a month apart: `#495`
    (`1 failed / 5471 passed`) and `#610` (`1 failed / 7148 passed`, gate run
    `33660327427`, on the very test above).  `#610` was itself the repair for
    a red `main`, so the leak took `main` down for every lane, not just this
    one.  After `#495` the resolution was written down; a month later `#610`
    walked into the identical hole four metres outside the fence, because the
    only mechanism that could go red was scoped by `Path(__file__)` to one
    other module.  A comment does not fail.  A round file does not fail.  An
    `AGENTS.md` line does not fail.  This does.

    MEASURED, on the commit this class ships with:
      * the shipped `try/finally: db.close()` form -- GREEN.
      * restore the bare `with` form and change nothing else -- RED here,
        and `32 passed` with this class deleted.  That second number is the
        state `#610` was written and measured in.
      * keep `db.commit()` and drop only `db.close()` -- RED here, `32
        passed` with this class deleted.

    Scoped to THIS FILE on purpose, and the scope is the honest part.
    `COO-DECISION 20260903_0052` point 1 requires a red-`main` recovery to be
    the smallest change possible and forbids adding a new `tests/test_*.py`
    FILE; a class in a file the same ticket already edits is neither a new
    file nor other work.  The repository-wide version -- lifting the runtime
    `/proc/self/fd` guard out of `tests/test_persistence_typed_attr_columns.py`
    into a helper every lane can import, and widening a source pin that today
    reads exactly one module -- is a separate ticket, and this class is what
    holds the line until it lands.

    An AST pin rather than a text search: `grep` cannot tell a real call from
    the same characters inside this docstring, and exempting the docstring
    would put a hole in the pin for the sake of the pin.
    """

    def _connect_calls(self, tree):
        """Every `sqlite3.connect(...)` call node in this file."""
        return [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "connect"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "sqlite3"
        ]

    def _tree(self):
        return ast.parse(Path(__file__).read_text(encoding="utf-8"))

    def test_this_file_never_writes_the_leaking_with_form(self):
        """`with sqlite3.connect(...) as db:` -- the exact line that died."""
        tree = self._tree()
        leaking = sorted(
            item.context_expr.lineno
            for node in ast.walk(tree) if isinstance(node, ast.With)
            for item in node.items
            if item.context_expr in self._connect_calls(tree)
        )
        self.assertEqual(
            leaking, [],
            "`with sqlite3.connect(...)` commits but does NOT close.  On "
            "Linux the surviving handle is silent; on the Windows gate "
            "TemporaryDirectory.cleanup raises PermissionError [WinError 32] "
            "at TEARDOWN, after the test body has printed its correct "
            "result.  Write `db = sqlite3.connect(...)` with "
            "`try: ... db.commit() / finally: db.close()` instead.  "
            f"Offending line(s): {leaking}")

    def test_every_connection_this_file_opens_is_closed(self):
        """The other half: assigned, committed, and then never closed.

        The `with` form is not the only way to leak one.  Dropping just the
        `finally: db.close()` from the fixture above leaves the same three
        descriptors open and is equally invisible on Linux, so pinning only
        the `with` spelling would pin the typo rather than the defect.
        """
        tree = self._tree()
        calls = self._connect_calls(tree)
        unclosed = []
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            owned = [c for c in calls if any(c is n for n in ast.walk(function))]
            if not owned:
                continue
            closes = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "close"
                for node in ast.walk(function))
            if not closes:
                unclosed.append((function.name, owned[0].lineno))
        self.assertEqual(
            unclosed, [],
            "a function opens a sqlite connection and never calls .close() "
            "on anything.  On the Windows gate that handle makes "
            "TemporaryDirectory.cleanup raise PermissionError [WinError 32] "
            f"at teardown.  Offender(s): {unclosed}")


if __name__ == "__main__":
    unittest.main()
