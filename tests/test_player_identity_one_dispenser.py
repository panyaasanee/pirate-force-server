"""R4, the player half: one dispenser for this session's own identity.

WHY THIS FILE EXISTS (PANYA ``20260908_1420``: "R4, do not flip the sign of
an identity only on the way out -- ONE dispenser for the whole circuit, and
guard the value 0"; owner assigned to chief by COO-DECISION
``20260908_1642``, pf_bridge notes_to_chief/20260908_1642_COO-DECISION-the-
player-half-of-r4-is-yours-after-the-m2-tail-LANE-E.md).

Beat 0 moved the MONSTER half of the circuit onto one reader:
``mob_identity_sign.decode_wire_identity``, called at the server edge before
anything compares an inbound identity.  The PLAYER half was still spelled by
hand at nine call sites in ``runtime.py`` as ``((hi & 0xFFFFFFFF) << 32) |
(lo & 0xFFFFFFFF)`` -- which is the unsigned WIRE value, not the identity a
caller means.  Two readings of one field is the exact defect beat 0 was
booted to remove, and the combat door compares the two halves directly
(``target == performer``).

WHAT THIS FILE MEASURES, AND WHAT IT DOES NOT.  It does NOT claim anything
about production values today: ``lifecycle.py`` mints ``hi = 0`` and ``lo``
in ``[0x10000001, 0xFFFFFFFF]``, so every identity a live server has ever
composed is positive and the decode returns it unchanged -- COO's own
words, "this does not explode today and I know it does not".  What it
measures is the sentence "one dispenser for the whole circuit" as WRITTEN:
give this session an identity whose top bit is set, drive the REAL
dispatcher, and the two halves still agree.  Nothing below calls
``decode_wire_identity`` itself; the bytes go in through the frozen encoder
and the verdict comes back out of production dispatch.
"""
from __future__ import annotations

import ast
import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lifecycle as lifecycle_module  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_identity_sign  # noqa: E402
from pirateforce_foundation import runtime  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: A player identity whose TOP BIT IS SET.  Split across the two 32-bit
#: columns exactly the way the schema stores them, so the wire qword is
#: ``0x8000000000000001`` and the identity a caller means is negative.
#: Chosen rather than measured: no live minter produces it (that is the
#: point -- the day one does, this file is what stops the two halves of the
#: circuit from disagreeing silently).
TOP_BIT_HI = 0x80000000
TOP_BIT_LO = 0x00000001
TOP_BIT_WIRE = (TOP_BIT_HI << 32) | TOP_BIT_LO
TOP_BIT_IDENTITY = TOP_BIT_WIRE - 2**64


class TheDispenserAgreesWithTheMonsterHalfTests(unittest.TestCase):
    """Unit layer: the dispenser is the same reader, not a second one."""

    def test_it_returns_what_the_frozen_encoder_round_trips(self):
        for identity in (
            1, 0x10000001, 0xFFFFFFFF, 2**31, 2**62,
            TOP_BIT_IDENTITY, -1, -2, -(2**62),
        ):
            with self.subTest(identity=identity):
                wire = int.from_bytes(
                    mob_identity_sign.encode_wire_identity(identity),
                    "little",
                )
                selected = _Selected(wire >> 32, wire & 0xFFFFFFFF)
                self.assertEqual(
                    runtime.selected_actor_identity(selected), identity)

    def test_a_top_bit_identity_is_negative_not_a_huge_unsigned(self):
        got = runtime.selected_actor_identity(
            _Selected(TOP_BIT_HI, TOP_BIT_LO))
        self.assertEqual(got, TOP_BIT_IDENTITY)
        self.assertLess(got, 0)
        self.assertNotEqual(got, TOP_BIT_WIRE)

    def test_zero_is_refused_because_the_client_never_draws_it(self):
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            runtime.selected_actor_identity(_Selected(0, 0))

    def test_a_part_that_is_not_an_int_is_refused_not_composed(self):
        for hi, lo in ((None, 5), (5, None), ("5", 5), (5, "5"),
                       (True, 5), (5, True), (1.0, 5)):
            with self.subTest(hi=hi, lo=lo):
                with self.assertRaises(
                    mob_identity_sign.MobIdentitySignError
                ):
                    runtime.selected_actor_identity(_Selected(hi, lo))

    def test_a_half_outside_its_column_is_refused_not_masked(self):
        """pf-adversary R406, D4: the mask was silent data loss both ways.

        Without a range check, ``identity_hi = -1`` composed to a NEGATIVE
        identity -- the monster band -- and came back as if it were a real
        player, and ``identity_hi = 0`` and ``identity_hi = 2 ** 32``
        composed to the SAME identity, so two different rows of the
        characters table became one actor.  The columns are plain
        ``INTEGER NOT NULL`` with no CHECK, so nothing else would notice.
        The three composers that predate this one all range-check each
        half first; the official dispenser must not be the loose one.
        """
        for hi, lo in ((-1, 0x10000001), (2**32, 1), (2**32 + 5, 1),
                       (0, 2**32), (0, -1)):
            with self.subTest(hi=hi, lo=lo):
                with self.assertRaises(
                    mob_identity_sign.MobIdentitySignError
                ) as box:
                    runtime.selected_actor_identity(_Selected(hi, lo))
                # the message must name the fault it FOUND, not the last
                # refusal in the function: a reader sent after
                # "IDENTITY_NOT_DRAWN" goes looking for a zero in the
                # database that is not there
                self.assertIn("outside the unsigned 32-bit column",
                              str(box.exception))

    def test_a_missing_attribute_is_the_same_refusal(self):
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            runtime.selected_actor_identity(object())
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            runtime.selected_actor_identity(None)


@dataclasses.dataclass(frozen=True)
class _Selected:
    identity_hi: object
    identity_lo: object


class NoCallSiteSpellsItByHandTests(unittest.TestCase):
    """COO's closing token -- and the FIRST version of it did not hold.

    pf-adversary (R406, finding D1) killed the original shape of this test.
    It counted the string ``0xFFFFFFFF) << 32`` and compared the file's
    count to the dispenser's, which pins ONE SPELLING rather than the
    property.  A tenth composition was sitting at ``runtime.py`` line ~4076
    the whole time, spelled ``(int(hi) << 32) | int(lo)`` -- no mask, no
    decode, no fence -- and the token could not see it.  Measured, not
    argued: adding an eleventh function in that spelling left the old test
    green.

    So the pin asks the AST instead: is there any ``x << 32`` anywhere in
    ``runtime.py``, outside the dispenser, whose operands reach an
    ``identity_hi``?  That is the SHAPE of composing a player identity by
    hand, and it does not care how the caller spells the mask.
    """

    @staticmethod
    def _runtime_tree():
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        return source, ast.parse(source)

    @staticmethod
    def _mentions_identity_hi(node):
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr == "identity_hi":
                return True
            if isinstance(child, ast.Name) and child.id == "identity_hi":
                return True
        return False

    def test_no_shift_by_32_over_an_identity_outside_the_dispenser(self):
        source, tree = self._runtime_tree()
        dispenser = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "selected_actor_identity"
        )
        inside = {id(n) for n in ast.walk(dispenser)}
        offenders = []
        for node in ast.walk(tree):
            if id(node) in inside:
                continue
            if not isinstance(node, ast.BinOp):
                continue
            if not isinstance(node.op, ast.LShift):
                continue
            right = node.right
            if not (isinstance(right, ast.Constant) and right.value == 32):
                continue
            if self._mentions_identity_hi(node):
                offenders.append(node.lineno)
        self.assertEqual(
            offenders, [],
            "runtime.py composes a player identity by hand at line(s) %r; "
            "the whole point of R4's player half is that there is one "
            "dispenser, and pf-adversary D1 showed a string-count token "
            "cannot see a different spelling" % (offenders,),
        )

    def test_the_dispenser_itself_still_does_the_composing(self):
        """The other half: the shape must exist somewhere, or nothing works."""
        _source, tree = self._runtime_tree()
        dispenser = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "selected_actor_identity"
        )
        shifts = [
            node for node in ast.walk(dispenser)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.LShift)
        ]
        self.assertEqual(len(shifts), 1)


class TheRealDispatcherAgreesWithItselfTests(unittest.TestCase):
    """End to end, through production dispatch, with the top bit set.

    NOT A TAUTOLOGY: the bytes below are composed with the frozen encoder
    (``legacy.qwordtag``) and handed to ``state.dispatch``.  The only thing
    in the process that can make the swing's target and this session's own
    performer the SAME number is the dispenser inside ``runtime.py``.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _state(self, token, *, hi, lo):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        # The identity this session believes is its own.  Replaced AFTER the
        # boot frames, so the login path is untouched and only the readers
        # under test see the top bit -- same technique beat 0's own file uses
        # to install the negative monster band for the length of one test.
        state.foundation.selected = dataclasses.replace(
            state.foundation.selected,
            class_id=None, identity_hi=hi, identity_lo=lo,
        )
        return state

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

    def _swing(self, state, identity, *, announce):
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (announce,),
                state.mob_combat_announced_membership_generation,
            )
        )
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(identity)))

    def test_a_top_bit_player_swinging_at_itself_is_refused_as_itself(self):
        """THE measurement of this round, and it is a discriminator.

        The frame names this session's OWN eight bytes.  The target half of
        the door decodes them to a negative identity (beat 0).  With the
        player half hand-composed, the performer stayed the unsigned
        ``0x8000000000000001``, the two were unequal, and the self-target
        refusal DID NOT FIRE.

        WHICH GATE CATCHES IT INSTEAD, MEASURED RATHER THAN ASSUMED
        (pf-adversary R406, finding D5): the first draft of this docstring
        said "the membership gate", and the mutant says otherwise -- the
        membership gate PASSES, because ``_swing`` announces that very
        target, and the swing falls through to the field-mob gate, which
        answers ``mob_combat_target_not_a_field_mob_no_reply``.  The
        second assertion below names that event, so it is a discriminator;
        naming the membership event made it an assertion that was true in
        both worlds and measured nothing.

        A player cannot attack himself either way today.  What differs is
        WHY he is refused, and two halves of one circuit disagreeing about
        who "himself" is is the defect ``1420`` names.
        """
        state = self._state("r406-self", hi=TOP_BIT_HI, lo=TOP_BIT_LO)
        actions = self._swing(
            state, TOP_BIT_IDENTITY, announce=TOP_BIT_IDENTITY)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_positive_or_self_no_reply", state.events,
            "the refusal that fired instead was %r" % (state.events[-3:],),
        )
        self.assertNotIn(
            "mob_combat_target_not_a_field_mob_no_reply", state.events)

    def test_the_ordinary_positive_player_is_untouched_by_the_move(self):
        """Nothing production mints changes value -- measured, not assumed."""
        state = self._state("r406-plain", hi=0, lo=0x10000001)
        actions = self._swing(state, 0x10000001, announce=0x10000001)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_positive_or_self_no_reply", state.events)


class TheMintRefusesWhatTheCircuitCannotCarryTests(unittest.TestCase):
    """"guard the value 0" at the only place in the tree that mints a pair.

    THE FIRST VERSION OF THIS FENCE WAS DEAD, AND pf-adversary (R406, D3)
    measured it dead: it asked only ``identity_is_drawn`` -- "is the
    composed value 0" -- and ``lo`` starts at ``0x10000001``, so the answer
    is "no" for EVERY ``hi``.  The one minter its comment claimed to fence
    against (``hi != 0``) walked straight through, and the adversary then
    drove that character all the way to a live combat frame, where it
    killed the connection thread on ``REFUSE_VIEWER_IDENTITY_NOT_POSITIVE``.

    So the fence now asks what the circuit actually requires -- a POSITIVE
    identity -- and the rule lives in a module-level function that can be
    measured without patching anything.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.account_id = self.store.ensure_account("r406-mint")

    def _create(self):
        wire = self.legacy.get_preset_actor_wire()
        return self.lifecycle.create(
            self.account_id, lifecycle_module.read_name(wire), wire,
        )

    # -- the rule itself, no mocks, no patching ---------------------------

    def test_the_pair_the_live_minter_produces_is_accepted(self):
        self.assertEqual(
            lifecycle_module.refuse_unmintable_identity(0x10000001, 0),
            0x10000001,
        )

    def test_the_next_minter_the_old_fence_let_through_is_refused(self):
        """The exact pair pf-adversary booted a character with."""
        with self.assertRaises(ValueError) as box:
            lifecycle_module.refuse_unmintable_identity(TOP_BIT_LO, TOP_BIT_HI)
        self.assertIn("positive", str(box.exception))
        # and the message names the real numbers, not a generic refusal
        self.assertIn(str(TOP_BIT_IDENTITY), str(box.exception))

    def test_zero_is_refused_too(self):
        with self.assertRaises(ValueError):
            lifecycle_module.refuse_unmintable_identity(0, 0)

    def test_the_largest_positive_pair_is_still_accepted(self):
        """The fence refuses non-positive, not "large" -- checked, not assumed."""
        self.assertEqual(
            lifecycle_module.refuse_unmintable_identity(0xFFFFFFFF, 0x7FFFFFFF),
            2**63 - 1,
        )

    # -- and it is actually ON the mint path, failing closed --------------

    def test_the_live_minter_still_births_a_character(self):
        character = self._create()
        self.assertEqual(character.identity_hi, 0)
        self.assertGreaterEqual(character.identity_lo, 0x10000001)

    def test_a_refused_identity_writes_no_row(self):
        before = len(self.store.list_characters(self.account_id))
        with mock.patch.object(
            lifecycle_module, "refuse_unmintable_identity",
            side_effect=ValueError("refused for the test"),
        ):
            with self.assertRaises(ValueError):
                self._create()
        self.assertEqual(
            len(self.store.list_characters(self.account_id)), before,
            "the refusal left a half-born character row behind",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
