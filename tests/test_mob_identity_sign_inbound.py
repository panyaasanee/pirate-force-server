"""LANE-B / R4 beat 0: an inbound identity means what it meant on the way out.

WHY THIS FILE EXISTS (COO-DECISION 2026-09-08 14:41 +07:00, pf_bridge
notes_to_chief/20260908_1441_COO-DECISION-r4-is-your-first-job-with-a-beat-
zero-and-layer-three-stays-open-LANE-B.md, making pf-adversary finding D4 of
round ``gadxq5`` an order):

    "beat 0 (mandatory, must land before ANY scene is flipped): every
     inbound point reads SIGNED ... there must be a test that sends a
     negative identity in and gets the same actor back"

The outbound half was already right: ``v141.qwordtag`` (line 1131) masks
``v & 0xFFFFFFFFFFFFFFFF``, so a negative identity leaves as its two's
complement, and ``mob_identity_sign.encode_wire_identity`` reproduces those
bytes.  Every INBOUND point read the same field with ``struct.unpack('<Q',
...)`` -- unsigned -- so a monster at ``-2`` came back as
``18446744073709551614``.  ``runtime.py``'s combat dispatch then compared
that to ``mob.actor_identity`` with a plain ``==``, matched nothing, and
returned an empty action list: the player swings at a monster and gets
silence.  No event, no bar, no damage, nothing in a log.

The frozen file is NOT edited (it is client-derived and never touched).  The
normalisation is one function, ``mob_identity_sign.decode_wire_identity``,
called at the server-side edge before anything compares the value.

TWO LAYERS, KEPT APART:

  * ``TheFourInboundPointsTests`` MEASURES the frozen parsers -- it runs
    them on real bytes and shows what they hand back.  It does not prove
    production decodes anything; it proves what production is handed.
  * ``ANegativeBandMonsterIsHitTests`` drives the REAL dispatcher end to
    end with the monster band actually negative, and asserts the swing
    lands.  Delete the decode in ``runtime.py`` and this class fails: the
    target resolves to no roster row and the action list comes back empty.

WHAT IS NOT MEASURED HERE, and no line may be read as it: NOBODY HAS SEEN A
NEGATIVE-BAND MONSTER ON A SCREEN.  Beat 2 of the R4 plan flips one scene at
a time behind a GT ticket, and beat 0 -- this file -- is the precondition
that stops that flip from shipping a correctly-coloured monster that cannot
be hit.  This file also does not claim the band HAS moved: ``field_mobs
.FieldMob.actor_identity`` is still ``0x2000 + placement_index + 1`` on
main, and the negative band below is installed by this test, on purpose, as
the canary for the migration that has not happened yet.
"""
from __future__ import annotations

import dataclasses
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_identity_sign  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The identity the whole file swings at.  Taken from the REAL dispenser
#: rather than written by hand: pf-adversary finding D6 of this round caught
#: the first draft using ``-2``, which this module's own
#: ``scene_and_placement_for`` refuses -- it sits inside
#: ``SWEEP_RESERVED_IDENTITIES``, the head the band does not hand out, and it
#: is the attended sweep's ``M-IDNEG`` row.  A test that names a value the
#: band cannot hold does not measure the band.
BAND_IDENTITY = mob_identity_sign.mob_wire_identity(
    1, field_mobs.CONTROL_PLACEMENT_INDEX)

#: What an unsigned read of that identity's own bytes produces -- the number
#: a reader has to recognise in a log.
UNDECODED = BAND_IDENTITY & mob_identity_sign.WIRE_IDENTITY_MASK


def _legacy():
    return load_legacy(LEGACY_PATH)


class TheFourInboundPointsTests(unittest.TestCase):
    """What the frozen parsers hand back, measured rather than assumed."""

    def setUp(self):
        self.legacy = _legacy()

    def _outer(self, vital_id, body, *, count=1):
        legacy = self.legacy
        return legacy.parse_outer(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, count)
            + legacy.u16tag(0x12, vital_id)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def test_the_outbound_bytes_are_two_s_complement(self):
        """The half that was already right, pinned so it cannot drift."""
        raw = self.legacy.qwordtag(0x32, BAND_IDENTITY)[-8:]
        self.assertEqual(
            raw, mob_identity_sign.encode_wire_identity(BAND_IDENTITY))
        self.assertEqual(struct.unpack("<Q", raw)[0], UNDECODED)

    def test_target_vital_hands_back_the_unsigned_number(self):
        legacy = self.legacy
        parsed = self._outer(
            legacy.TARGET_VITAL,
            legacy.qwordtag(0x32, BAND_IDENTITY) + legacy.u8tag(0x08, 0),
        )
        identity, _kind = legacy.parse_target_vital(parsed)
        self.assertEqual(identity, UNDECODED)
        self.assertEqual(
            mob_identity_sign.decode_wire_identity(identity), BAND_IDENTITY)

    def test_choose_npc_hands_back_the_unsigned_number(self):
        legacy = self.legacy
        parsed = self._outer(
            legacy.CHOOSE_NPC, legacy.qwordtag(0x32, BAND_IDENTITY))
        self.assertEqual(legacy.parse_choose_npc(parsed), UNDECODED)
        self.assertEqual(
            mob_identity_sign.decode_wire_identity(
                legacy.parse_choose_npc(parsed)),
            BAND_IDENTITY,
        )

    def test_the_choose_npc_walker_hands_back_the_unsigned_number(self):
        legacy = self.legacy
        parsed = self._outer(
            legacy.CHOOSE_NPC, legacy.qwordtag(0x32, BAND_IDENTITY))
        self.assertEqual(
            legacy.extract_choose_npc_identities(parsed), [UNDECODED])

    def test_action_vital_hands_back_the_unsigned_number(self):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, BAND_IDENTITY)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        fields = legacy.parse_action_vital(
            self._outer(legacy.ACTION_VITAL, body))
        self.assertEqual(fields["field_qword_20"], UNDECODED)
        self.assertEqual(
            mob_identity_sign.decode_wire_identity(fields["field_qword_20"]),
            BAND_IDENTITY,
        )

    def test_the_decoder_is_the_exact_inverse_of_the_encoder(self):
        """Over the whole signed field, not over a handful of round numbers."""
        edges = (
            -(2 ** 63), -(2 ** 62), -0x2001, BAND_IDENTITY, -1, 1, 0x2001,
            (1 << 32) | 0x750059, 2 ** 62, 2 ** 63 - 1,
        )
        for value in edges:
            with self.subTest(identity=value):
                raw = mob_identity_sign.encode_wire_identity(value)
                wire = int.from_bytes(raw, "little")
                self.assertEqual(
                    mob_identity_sign.decode_wire_identity(wire), value)
                self.assertEqual(struct.unpack("<Q", raw)[0], wire)

    def test_the_decoder_refuses_what_is_not_a_wire_value(self):
        for bad in (-1, 2 ** 64, "2", True):
            with self.subTest(value=bad):
                with self.assertRaises(
                    mob_identity_sign.MobIdentitySignError
                ):
                    mob_identity_sign.decode_wire_identity(bad)


class ANegativeBandMonsterIsHitTests(unittest.TestCase):
    """The real dispatcher, with the monster band actually negative.

    NOT A TAUTOLOGY, and the difference matters: nothing below calls
    ``decode_wire_identity``.  The test composes the bytes a client would
    send (``qwordtag``, the frozen encoder) and reads the action list the
    production dispatch returns.  The only thing that can turn those bytes
    back into ``BAND_IDENTITY`` is the decode inside ``runtime.py``.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
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
        # The band, installed for the length of one test.  ``actor_identity``
        # is a property computed from ``placement_index``; the patch below
        # gives the control placement the value beat 2 will give it for real
        # and leaves every other row exactly where it was, so nothing else
        # in the roster moves underneath the assertions.
        control = field_mobs.CONTROL_PLACEMENT_INDEX
        original = field_mobs.FieldMob.actor_identity

        def _identity(mob):
            if mob.placement_index == control:
                return BAND_IDENTITY
            return original.fget(mob)

        self._patch = mock.patch.object(
            field_mobs.FieldMob, "actor_identity", property(_identity),
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        # Same reason as tests/test_mob_combat_dispatch.py's own _state:
        # a real class_id composes an extra pose frame ahead of the frames
        # this file reads, and pose is not what beat 0 is about.
        state.foundation.selected = dataclasses.replace(
            state.foundation.selected, class_id=None,
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

    def _swing(self, state, wire_identity, *, announce=BAND_IDENTITY):
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (announce,),
                state.mob_combat_announced_membership_generation,
            )
        )
        return state.dispatch(self.legacy.parse_outer(
            self._action_vital_pc(wire_identity)
        ))

    # -- the measurement --------------------------------------------------

    def test_the_roster_really_carries_the_negative_identity(self):
        """The premise of every assertion below, checked rather than assumed."""
        roster = field_mobs.load_roster()
        identities = [mob.actor_identity for mob in roster]
        self.assertIn(BAND_IDENTITY, identities)
        self.assertEqual(identities.count(BAND_IDENTITY), 1)

    def test_a_swing_at_a_negative_band_monster_lands(self):
        state = self._state("beat0-hit")
        actions = self._swing(state, BAND_IDENTITY)
        labels = [label for label, _pc, _f, _d in actions]
        self.assertIn(
            "MOB_COMBAT_ANNOUNCE", labels,
            "the swing produced %r and the refusal events were %r -- with the "
            "decode removed this list is empty, which is the silence beat 0 "
            "exists to stop" % (labels, state.events[-3:]),
        )
        self.assertNotIn(
            "mob_combat_target_not_positive_or_self_no_reply", state.events)
        # the ledger opened under the identity the client named, not under
        # the number an unsigned read would have produced
        self.assertEqual(
            state.mob_combat_ledger.balance_of(BAND_IDENTITY).actor_identity,
            BAND_IDENTITY,
        )

    def test_the_same_swing_takes_damage_off_that_monster(self):
        state = self._state("beat0-damage")
        before = state.mob_combat_ledger.balance_of(BAND_IDENTITY)
        self._swing(state, BAND_IDENTITY)
        after = state.mob_combat_ledger.balance_of(BAND_IDENTITY)
        self.assertLess(
            after.current_hp, before.max_hp,
            "HP did not move, so nothing was actually hit",
        )

    def test_an_unannounced_negative_band_monster_is_still_refused(self):
        """This is what pins the decode in ``runtime.py`` itself.

        MUTANT, run rather than asserted in prose: take the decode out of
        ``_dispatch_mob_combat`` and the other tests in this class STILL
        pass, because ``mob_combat.attack_from_observed_action`` decodes the
        field a second time on its own.  What breaks is this: with an
        undecoded target, ``target_is_field_mob`` is False, so the
        membership gate (RE-157 job 2 -- a target the client was never told
        about must not mutate combat state) and the cadence gate are both
        SKIPPED, and the swing lands anyway.  A forged frame naming a real
        monster nobody announced would go straight through.
        """
        state = self._state("beat0-unannounced")
        # announce a different actor, so the swing's target is a real roster
        # row that THIS session was never told about
        actions = self._swing(state, BAND_IDENTITY, announce=0x2002)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_announced_no_reply", state.events)

    def test_identity_zero_is_still_refused(self):
        """The one value the client refuses to draw, still refused here.

        Widening the guard from ``target <= 0`` to the signed band must not
        widen it to zero: R324A row 8 measured that the client throws that
        actor away before drawing it, so a frame naming it can only be a
        forgery or a desync.
        """
        state = self._state("beat0-zero")
        actions = self._swing(state, 0, announce=0)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_positive_or_self_no_reply", state.events)

    def test_a_swing_at_the_performer_itself_is_still_refused(self):
        state = self._state("beat0-self")
        selected = state.foundation.selected
        performer = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        actions = self._swing(state, performer, announce=performer)
        self.assertEqual(actions, [])
        self.assertIn(
            "mob_combat_target_not_positive_or_self_no_reply", state.events)


class TheSecondWallBeatTwoWalksIntoTests(unittest.TestCase):
    """A band identity does not merely fail to be written -- it RAISES.

    pf-adversary, round 6okcq4, finding D2.  This round surveyed how far a
    band identity can travel, found ``world_scene_registry`` refusing it
    with a returned ``NoteOutcome``, and called that "the wall".  It is not
    the only one and it is not the worst one.  ``mob_ai_player_damage``
    line ~249 -- THIS LANE'S OWN FILE, on the live AI tick path
    (``lane_hooks/lane_b_mob_ai_tick`` line ~270 calls ``apply_tick_damage``
    which calls ``attack_decisions``) -- refuses any ``actor_identity`` that
    is not strictly positive by RAISING ``identity_not_positive``.

    Failure scenario, which is why this is pinned rather than written down:
    beat 2 flips Bg0002 onto the band, and the first monster that decides to
    attack takes the tick hook down for every player in the scene.

    Not fixed in this round on purpose: widening a refusal on the live tick
    path is a behaviour change that wants its own beat and its own full
    suite, and nothing flips a scene until the COO answers the wall letter.
    This test is the receipt.  It goes RED the day the guard is widened,
    which is the day it should be rewritten to assert the new reach.
    """

    def test_the_tick_damage_path_raises_on_a_band_identity(self):
        from pirateforce_foundation import mob_ai_player_damage as mapd

        from pirateforce_foundation import mob_aggro

        identity = mob_identity_sign.mob_wire_identity(2, 0)
        row = dataclasses.make_dataclass(
            "FakeTickResult", ["actor_identity", "intent_kind"])(
                identity, mob_aggro.INTENT_ATTACK_UNDELIVERABLE)
        with self.assertRaises(mapd.MobAiPlayerDamageError) as box:
            mapd.attack_decisions((row,))
        self.assertEqual(box.exception.reason, mapd.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_the_same_call_accepts_the_legacy_positive_identity(self):
        """The control: it is the sign, not the shape of the record."""
        from pirateforce_foundation import mob_ai_player_damage as mapd

        from pirateforce_foundation import mob_aggro

        row = dataclasses.make_dataclass(
            "FakeTickResult", ["actor_identity", "intent_kind"])(
                0x2001, mob_aggro.INTENT_ATTACK_UNDELIVERABLE)
        self.assertEqual(mapd.attack_decisions((row,)), (0x2001,))


class TheOrderingBlockerBeatOneAnsweredTests(unittest.TestCase):
    """The wall beat 1 walked into, now asserted from the other side.

    This class used to pin a COLLISION.  ``field_mobs.load_roster`` returns
    rows in placement order, the first draft of
    ``mob_identity_sign.mob_wire_identity`` DESCENDED as the placement index
    rose, ``mob_combat.CombatLedger`` refuses a roster that is not in
    ascending identity order (on purpose -- "REFUSED rather than silently
    re-sorted"), and ``runtime.PersistentGameSessionState.__init__`` opens
    that ledger off the boot roster.  So flipping a whole scene onto the
    band did not fail one combat assertion, it failed LOGIN, for every
    player.  The old class asserted the descent and asserted the refusal,
    and its own docstring said it should be rewritten the day somebody
    resolved it.

    COO decision ``20260908_1642_COO-DECISION-roster-order-take-option-
    three-LANE-B`` resolved it by making the DISPENSER ascend (option 3),
    rather than re-sorting ``load_roster`` (option 1, which changes the
    order actors go out on the census wire -- a screen question, and the
    owner's machine is the most expensive queue in this house) or teaching
    ``open_ledger`` to sort (option 2, which deletes another module's
    written reason for refusing).  These tests are the same four readers as
    before, asserted in the direction that now holds.
    """

    def test_a_fully_flipped_roster_is_in_ascending_identity_order(self):
        rows = tuple(
            mob_identity_sign.mob_wire_identity(1, mob.placement_index)
            for mob in field_mobs.load_roster()
        )
        self.assertGreater(len(rows), 1)
        # the dispenser now rises where the legacy 0x2000 formula rose --
        # the ordering contract, in one assertion
        self.assertEqual(list(rows), sorted(rows))
        self.assertEqual(len(set(rows)), len(rows))

    def test_the_ledger_that_used_to_refuse_this_roster_now_opens_on_it(self):

        def _identity(mob):
            return mob_identity_sign.mob_wire_identity(1, mob.placement_index)

        with mock.patch.object(
            field_mobs.FieldMob, "actor_identity", property(_identity)
        ):
            roster = field_mobs.load_roster()
            ledger = mob_combat.open_ledger(roster)
        self.assertEqual(
            list(ledger.identities()), sorted(ledger.identities()))
        self.assertTrue(all(i < 0 for i in ledger.identities()))

    def test_the_ledger_still_refuses_a_roster_that_is_out_of_order(self):
        """The fix is the band's order, NOT the removal of the refusal.

        Without this, "the ledger opens" above would also be satisfied by
        somebody quietly deleting the guard, which is exactly the option
        the COO decision rejected.
        """

        def _identity(mob):
            return -mob_identity_sign.mob_wire_identity(1, mob.placement_index)

        with mock.patch.object(
            field_mobs.FieldMob, "actor_identity", property(_identity)
        ):
            roster = field_mobs.load_roster()
            with self.assertRaises(mob_combat.MobCombatContractError) as box:
                mob_combat.open_ledger(roster)
        self.assertEqual(box.exception.reason, "ledger_not_sorted")

    def test_the_register_row_zero_is_the_mob_the_ledger_calls_first(self):
        """COO condition 3 of the option-3 approval, as a measurement.

        ``mob_ai_control.open_register`` sorts by identity SILENTLY.  Option
        3 makes it agree with the ledger today, but a silent sort that
        agrees by luck is the same time bomb the old descent was, so the
        agreement is asserted rather than assumed: row zero of the register
        and row zero of the ledger have to be the same monster, by identity
        AND by placement index.
        """
        from pirateforce_foundation import mob_ai_control

        def _identity(mob):
            return mob_identity_sign.mob_wire_identity(1, mob.placement_index)

        with mock.patch.object(
            field_mobs.FieldMob, "actor_identity", property(_identity)
        ):
            roster = field_mobs.load_roster()
            ledger = mob_combat.open_ledger(roster)
            register = mob_ai_control.open_register(roster)
            self.assertGreater(len(roster), 1)
            self.assertEqual(
                register.rows[0].actor_identity, ledger.identities()[0])
            self.assertEqual(
                register.rows[0].actor_identity, roster[0].actor_identity)
            # NOT "placement_index == 0": the no-argument roster is
            # bg0001's, whose placement indices start at 103.  What the
            # contract says is that row zero is the SMALLEST placement, and
            # asserting the literal 0 would have passed for the wrong reason
            # on any scene that happens to start there.
            placements = [mob.placement_index for mob in roster]
            self.assertEqual(placements, sorted(placements))
            self.assertEqual(roster[0].placement_index, min(placements))
            # and all the way down, not only at row zero
            self.assertEqual(
                [row.actor_identity for row in register.rows],
                list(ledger.identities()),
            )
            # pf-adversary round 6okcq4, D7: everything above is ALSO
            # satisfied by a register that does not sort at all (deleting
            # the sort left the suite green), which is not what the
            # docstring above claims to be pinning.  Hand it a roster in
            # the wrong order and require ascending rows out, so "it sorts"
            # is measured and not inferred from "it agrees".
            shuffled = tuple(reversed(roster))
            self.assertNotEqual(
                [mob.actor_identity for mob in shuffled],
                sorted(mob.actor_identity for mob in shuffled),
            )
            out = mob_ai_control.open_register(shuffled)
            self.assertEqual(
                [row.actor_identity for row in out.rows],
                sorted(row.actor_identity for row in out.rows),
            )



if __name__ == "__main__":  # pragma: no cover
    unittest.main()
