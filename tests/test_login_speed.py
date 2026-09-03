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
* `TheSpeedDeferralHoldsTheLoginFrameTests`
                              -- delete the deferral gate, cache its boolean
                                 instead of asking every login, open it on a
                                 read that fails, or move it into `resolve`.

THE GATE THIS FILE NOW HAS TO STATE OUT LOUD
--------------------------------------------
`COO-DECISION 20260903_0645`: while LANE-GM's `/speed` wire is deferred, a
login sends the CONSTANT no matter what the row holds.  `/speed` still writes
its row -- the deferral holds the frame, not the write -- so `/speed 300`
leaves `300.0` behind, and since `#605` the next login was reading it and
encoding `00 00 96 43`: the bytes `GT-193` was sending when a real client
locked itself for 426 frames, reached by the "log in again" recovery step in
`GT-193` and `GT-218` themselves.

Every group above grades behaviour on the far side of that gate, so each one
opens it explicitly with `_wire_open()` instead of inheriting `main`'s
setting.  That is not ceremony: with the gate shut, `test_a_row_with_no_value_
sends_the_constant` and `test_a_zero_in_the_row_does_not_reach_the_client`
would both pass without ever reaching the branch they name -- the same
unfalsifiable shape this docstring already records being removed from this
file once.

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
import contextlib
import io
import sqlite3
import struct
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import login_speed
from pirateforce_foundation.gm import speed_wire
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


def _wire_open():
    """The `/speed` wire open, so the row may reach a login.

    `COO-DECISION 20260903_0645` gated `resolve_for_character` on LANE-GM's
    `speed_wire.send_deferred()`, and on `main` that gate is SHUT
    (`SPEED_LOGIN_READ_LANDED = False`).  Every test below that grades a
    branch of the resolver -- the row's value, an empty column, a validator
    refusal, the positive floor, a read that raises -- is grading behaviour
    that only happens on the far side of that gate, so it opens it explicitly.

    !! IT PATCHES LANE-GM'S FLAG, NOT `send_deferred` ITSELF, and not a stand-
    in inside `login_speed`.  The flag is the one line a future round edits,
    so a test that drives it is a test that measures what that round will do.
    A patched `send_deferred` would keep passing if the gate were rewired to
    read something else entirely.

    THIS IS A PROCESS-LOCAL PATCH AND NOT A FLIP.  `mock.patch.object` restores
    the flag at the end of the block; the flag on `main` stays `False`, which
    `COO-DECISION 20260903_0649` says nobody -- this file included -- may
    change on the strength of `#605` having landed.
    """
    return mock.patch.object(speed_wire, "SPEED_LOGIN_READ_LANDED", True)


def _wire_held():
    """The `/speed` wire deferred: `main`'s state, stated instead of assumed.

    The tests that grade the gate set it EXPLICITLY in both directions rather
    than leaning on the default, so they keep measuring the gate on the day
    LANE-GM's attended trial flips that default.
    """
    return mock.patch.object(speed_wire, "SPEED_LOGIN_READ_LANDED", False)


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
            with self.subTest(error=type(error).__name__), _wire_open():
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
        with _wire_open():
            resolved = login_speed.resolve_for_character(
                _StoreStub({"level": 7}), 1,
                fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.ROW_HAS_NO_VALUE)

    def test_a_store_that_holds_the_column_reads_as_the_row(self):
        with _wire_open():
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


class TheSpeedDeferralHoldsTheLoginFrameTests(unittest.TestCase):
    """`COO-DECISION 20260903_0645`: one lock has to guard both doors.

    `/speed` sends nothing today, but it still COMMITS the row, and since
    `#605` a login READS that row.  `/speed 300` therefore leaves behind the
    value whose bytes (`00 00 96 43`) locked a real client for 426 frames in
    `GT-193` -- and "log in again" is the RECOVERY STEP in `GT-193` and
    `GT-218` themselves, so the recovery walked into the trap.

    THE MUTATIONS THIS GROUP CATCHES (each applied and measured red before
    this class was committed):

    * delete the `held_by_the_speed_deferral` call from
      `resolve_for_character` -- the gate is gone;
    * cache the boolean at import time instead of asking every call -- the
      gate stops tracking LANE-GM's flag;
    * make the fail-closed branch return `None` (open) instead of the
      constant -- an unaskable gate starts sending rows;
    * move the gate into `resolve` -- LANE-GM's `next_login=` console line
      stops answering the question it is printed to answer.
    """

    def _held(self):
        return login_speed.resolve_for_character(
            _StoreStub({"speed_walk": ROW_SPEED}), 1,
            fallback=PLAYER_LOGIN_MOVEMENT_SPEED)

    def test_a_poison_row_does_not_reach_the_login_while_the_wire_is_held(self):
        with _wire_held():
            resolved = self._held()
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.WIRE_DEFERRED)
        self.assertFalse(
            resolved.came_from_the_row,
            "`session.py` attaches the value only when it came from the row, "
            "so this is the flag that keeps 300.0 off the character")

    def test_the_same_row_goes_out_once_the_wire_is_open(self):
        """The gate is a GATE, not a second refusal of the row.

        Without this half, deleting the whole `#605` read would look like a
        passing gate.
        """
        with _wire_open():
            resolved = self._held()
        self.assertEqual(resolved.value, ROW_SPEED)
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)

    def test_the_flag_is_read_live_and_not_captured_once(self):
        """Flip it twice inside one process and the answer follows.

        A gate that reads a module-level copy of the boolean passes the two
        tests above and fails this one, and that is exactly the shape that
        would leave one door open on the day LANE-GM flips their flag.
        """
        seen = []
        for opener in (_wire_open, _wire_held, _wire_open):
            with opener():
                seen.append(self._held().reason)
        self.assertEqual(
            seen,
            [login_speed.FROM_ROW,
             login_speed.WIRE_DEFERRED,
             login_speed.FROM_ROW])

    def test_a_gate_that_cannot_be_asked_is_a_gate_that_is_shut(self):
        """Fail-closed, and the reason names what stopped the question."""
        with mock.patch.object(
            speed_wire, "send_deferred", side_effect=RuntimeError("boom")
        ):
            resolved = self._held()
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.DEFERRAL_UNREADABLE)
        self.assertIn("RuntimeError", resolved.detail)
        self.assertIn("boom", resolved.detail)
        resolved.console_line().encode("ascii")

    def test_anything_but_a_literal_false_holds_the_frame(self):
        """`send_deferred()` is typed `-> bool`; the gate does not trust that.

        A later round adding an early `return None` to that function would
        make a truthiness test send the row.  The deferral is the default
        answer, so only a literal `False` opens the door.
        """
        for answer in (None, 0, "", []):
            with self.subTest(answer=answer):
                with mock.patch.object(
                    speed_wire, "send_deferred", return_value=answer
                ):
                    resolved = self._held()
                self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
                self.assertEqual(resolved.reason, login_speed.WIRE_DEFERRED)

    def test_the_pure_resolver_is_not_gated(self):
        """`resolve` answers "what would this row do", and must keep doing it.

        LANE-GM's deferred `/speed` console line calls `login_speed.resolve`
        to print `next_login=<reason>` on the same line that announces the
        deferral (`tests/test_gm_speed_deferred.py`).  Gating it there would
        make that line answer `wire_deferred` -- the thing it already says --
        instead of what the row would do at a login, and would take a token
        away from a lane whose file this round may not touch.
        """
        with _wire_held():
            resolved = login_speed.resolve(
                ROW_SPEED, fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.FROM_ROW)
        self.assertEqual(resolved.value, ROW_SPEED)

    def test_a_per_session_trial_does_not_open_the_login_door(self):
        """The defect a first draft shipped, now a test (pf-adversary D1).

        `COO-DECISION 20260903_0646` opens `/speed` for an attended round
        through `PF_SPEED_TRIAL`, which sanctions ONE value.  If that is
        implemented by making `send_deferred()` answer False for the session,
        a login gated on that alone sends WHATEVER the row holds -- and
        `/speed` writes its row even when the frame is withheld.  So: trial
        opens for 400, the tester types `/speed 300` (frame held, ROW
        WRITTEN), `GT-218`'s own recovery step re-logs in, and the GT-193
        bytes go out in the round written to prevent them.

        The durable flag is what releases the row; a trial leaves it shut.
        """
        with _wire_held(), mock.patch.object(
            speed_wire, "send_deferred", return_value=False
        ):
            resolved = self._held()
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.WIRE_TRIAL_ONLY)
        self.assertFalse(resolved.came_from_the_row)
        self.assertIn("SPEED_LOGIN_READ_LANDED", resolved.detail)

    def test_the_console_line_names_the_value_that_was_withheld(self):
        """A held login has to be gradeable, or the gate is invisible.

        Without this, every login prints the identical line whether the row
        held the harmless default or the number that locked a client, so no
        attended round could ever show the gate catching anything
        (pf-adversary D5).  It is also the missing-column warning that would
        otherwise have gone silent (D6).
        """
        with _wire_held():
            resolved = self._held()
        self.assertIn(f"withheld_row={ROW_SPEED!r}", resolved.detail)
        resolved.console_line().encode("ascii")

    def test_a_store_that_raises_still_leaves_a_held_login_intact(self):
        """The detail read may not become the login's exception."""
        with _wire_held():
            resolved = login_speed.resolve_for_character(
                _StoreStub(raises=RuntimeError("db is gone")), 1,
                fallback=PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.value, PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(resolved.reason, login_speed.WIRE_DEFERRED)
        self.assertIn("withheld_row=unreadable(RuntimeError)", resolved.detail)

    def test_a_bad_fallback_still_names_the_caller_not_the_resolver(self):
        """The gate answers first, so it owes the same TypeError `resolve` did.

        Before this, an `int` fallback reached `ResolvedLoginSpeed` and the
        operator was told "a resolved login speed is a float" -- pointing at
        the resolver instead of at the call site that has the constant
        (pf-adversary D8).
        """
        for bad in (400, True):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError) as caught:
                    login_speed.resolve_for_character(
                        _StoreStub({"speed_walk": ROW_SPEED}), 1, fallback=bad)
                self.assertIn(
                    "PLAYER_LOGIN_MOVEMENT_SPEED", str(caught.exception))

    def test_every_new_reason_is_registered_and_prints_ascii_with_its_detail(self):
        """The details, not just the tokens: `console_line` prints both."""
        cases = (
            (login_speed.WIRE_DEFERRED, _wire_held(), None),
            (login_speed.WIRE_TRIAL_ONLY, _wire_held(),
             mock.patch.object(speed_wire, "send_deferred",
                               return_value=False)),
            (login_speed.DEFERRAL_UNREADABLE, mock.patch.object(
                speed_wire, "send_deferred",
                side_effect=RuntimeError("boom")), None),
        )
        for reason, outer, inner in cases:
            with self.subTest(reason=reason):
                self.assertIn(reason, login_speed.REASONS)
                with outer:
                    if inner is None:
                        resolved = self._held()
                    else:
                        with inner:
                            resolved = self._held()
                self.assertEqual(resolved.reason, reason)
                self.assertTrue(
                    resolved.detail,
                    "a refusal that says nothing is a refusal nobody can act "
                    "on (R309 defect D3)")
                line = resolved.console_line()
                line.encode("ascii")
                self.assertIn(reason, line)

    def test_the_gate_asks_lane_gm_rather_than_keeping_its_own_flag(self):
        """No second source for "is the speed wire held".

        `login_speed` may not grow its own copy of LANE-GM's flag: two places
        holding one truth is how a door ends up half open.

        THIS IS A BELT, NOT THE BRACES, and an earlier draft of this docstring
        claimed otherwise ("a copy would be invisible to every other test in
        this class") -- measured false: a second source of truth under another
        name turns nine tests red, three of them in this class.  What this
        test adds is the SHAPE, caught at the source level before anyone has
        to read a failure list to find out why.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "login_speed.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        assigned = [
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        ]
        self.assertNotIn("SPEED_LOGIN_READ_LANDED", assigned)
        # A CALL IN THE TREE, NOT THE STRING ANYWHERE IN THE FILE.  The first
        # draft asserted `"speed_wire.send_deferred()" in source`, and that
        # spelling appears four times in this module's own prose: delete the
        # one real call, read a private copy instead, and the assertion stayed
        # green (pf-adversary, round `4lf2hl`, D4 -- measured).
        called = [
            node.func
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ]
        self.assertIn(
            ("speed_wire", "send_deferred"),
            [(func.value.id, func.attr) for func in called],
            "the gate must CALL LANE-GM's own function, not merely mention it")


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

    def _start_and_read_the_console(self, session, selector):
        """Drive the real login and keep the line it prints about itself.

        !! WITHOUT THIS, TWO TESTS BELOW NAMED A BRANCH THEY DID NOT GRADE,
        and it was measured: `ROW_HAS_NO_VALUE`, `ROW_SPEED_NOT_POSITIVE` and
        `WIRE_DEFERRED` all produce the same two observable facts -- the
        constant in the frame, and `movement_speed is None`, because
        `session.py` attaches only on `FROM_ROW`.  So a test asserting those
        two things passes on any of the three, and neutering `_wire_open()`
        left both of them green (pf-adversary, round `4lf2hl`, D3).
        `session.py` already prints `LOGIN_SPEED <reason>` to stderr for
        exactly this purpose; capturing it is what makes the branch visible.
        """
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            selected, (pc, frame) = session.select_and_start(selector)
        return selected, pc, buffer.getvalue()

    def test_the_login_sends_the_speed_the_row_holds_while_the_wire_is_open(self):
        """The whole claim of this change, end to end, in one test.

        !! THE `while the wire is open` HALF OF THAT NAME IS NEW AND IT IS THE
        POINT.  `COO-DECISION 20260903_0645` gated this seam on LANE-GM's
        `/speed` deferral, and on `main` that gate is SHUT -- so this test now
        states the precondition it used to inherit.  Its sibling below owns
        the other side, and between them the gate cannot be deleted or welded
        shut without one of them going red.
        """
        character = self._born()
        self.store.write_typed_attributes(
            character.id, {login_speed.COLUMN: ROW_SPEED})

        session = self._session()
        with _wire_open():
            selected, pc, console = self._start_and_read_the_console(
                session, character.selector)

        self.assertIn(f"LOGIN_SPEED {login_speed.FROM_ROW}", console)
        self.assertEqual(selected.movement_speed, ROW_SPEED)
        self.assertIn(
            self.legacy.f32tag(ROW_SPEED), pc,
            "the login composed the constant even though the row held "
            "another number -- which is the entire defect this change is for")

    def test_the_poison_row_stays_off_the_wire_while_speed_is_deferred(self):
        """`GT-193`'s own bytes, on `main`'s own gate setting, end to end.

        The row holds `300.0` -- what a `/speed 300` session commits today,
        since the deferral stops the FRAME and not the WRITE -- and the login
        must compose `400.0` anyway.  This is the window `COO-DECISION
        20260903_0645` closed: the door was shut and the next login was
        reading the row through the wall.

        BOTH HALVES ARE GRADED, and neither alone would do.  The attached
        value is the SEAM (`session.py` attaches only on `FROM_ROW`); the byte
        pattern is the COMPOSER'S OUTPUT -- still the wire layer, not
        client-observable, and calling it "the client's half" (as a first
        draft did) is the exact G5 mixing this file's own docstring refuses.
        It is safe to assert here for a reason this fixture can state:
        `300.0` is not the constant, not the
        column default, and not one of this fixture's coordinates
        (`Position(1, 0, 1.0, 2.0, 3.0)`), so its f32 tag cannot appear in the
        frame by accident.  A future fixture that moves a character to x=300
        turns this into the fragile-by-fixture assertion pf-adversary caught
        once already in this file, and this sentence is where that round is
        supposed to notice.
        """
        character = self._born("psn300")
        self.store.write_typed_attributes(
            character.id, {login_speed.COLUMN: ROW_SPEED})

        session = self._session("psn300")
        with _wire_held():
            selected, pc, console = self._start_and_read_the_console(
                session, character.selector)

        self.assertIn(f"LOGIN_SPEED {login_speed.WIRE_DEFERRED}", console)
        self.assertIn(f"withheld_row={ROW_SPEED!r}", console)
        self.assertIsNone(
            selected.movement_speed,
            "the deferred wire still let the row reach the login")
        self.assertIn(self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED), pc)
        self.assertNotIn(
            self.legacy.f32tag(ROW_SPEED), pc,
            "the bytes GT-193 was sending when the client locked itself for "
            "426 frames reached the frame anyway")

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
        # The wire is opened so this test keeps grading ROW_HAS_NO_VALUE.  With
        # `main`'s gate shut, every branch below would answer WIRE_DEFERRED and
        # this test would pass without ever reaching the branch it names --
        # the same unfalsifiable shape its own docstring is about.
        with _wire_open():
            selected, pc, console = self._start_and_read_the_console(
                session, character.selector)

        # THE LINE THAT MAKES THE BRANCH VISIBLE, not merely reached: the
        # constant on the wire and a `None` attachment are what WIRE_DEFERRED
        # produces too, so without this the test passes on the wrong branch
        # (pf-adversary D3, measured on this exact test).
        self.assertIn(f"LOGIN_SPEED {login_speed.ROW_HAS_NO_VALUE}", console)
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
                # Opened for the same reason as the sibling above: the
                # positive floor is only reachable past the `/speed` gate, and
                # a test that never reaches its own branch grades nothing.
                with _wire_open():
                    selected, pc, console = self._start_and_read_the_console(
                        session, character.selector)
                # Same reason as the sibling above: three branches produce the
                # same two facts, so the console line is what says WHICH one
                # this test drove (pf-adversary D3).
                self.assertIn(
                    f"LOGIN_SPEED {login_speed.ROW_SPEED_NOT_POSITIVE}",
                    console)
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
        # Past the `/speed` gate on purpose: this test is about the READ
        # surviving a missing store, which is a question only asked on the
        # far side of that gate.
        with _wire_open():
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
