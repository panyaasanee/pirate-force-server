"""PANYA-ORDER 20260908_1545 item 5 -- ONE test, one monster, four doors.

The owner's condition for letting LANE-B flip ``field_mobs.actor_identity``
off ``0x2000 + placement_index + 1`` onto the negative monster band is not
"grep finds no ``<= 0``".  It is this, in her words: compose a monster with a
NON-POSITIVE identity and then

  * register it in the world,
  * write its health down,
  * bind a ground drop to it,
  * bury it in the death register,

all four in ONE test, and have that test be green BEFORE the allocator moves.

That is what this file is.  It is deliberately end-to-end across four modules
that do not import each other, because the failure the order is guarding
against is exactly the one a per-module test cannot see: every module agreeing
in isolation and the monster still falling through the floor between two of
them.

WHERE IT IS RED TODAY, AND WHY THAT IS THE POINT.  Three of the four doors
take the band already.  The fourth -- ``world_scene_registry`` -- does not:
its ``_require_identity`` reads ``1 <= n <= 0xFFFFFFFF`` and throws on
everything the band hands out.  That module belongs to LANE-A, this lane is
forbidden to edit it (COO-DECISION 20260909_1312: "A changes it to call your
function AFTER M2"), so the leg is asserted HERE AS IT IS, not skipped, not
xfailed, and not quietly dropped from the four.  ``test_leg_1_...`` asserts
the refusal that exists; ``test_the_four_in_one_is_not_green_yet`` states in
one place what is still missing and why the allocator therefore may not move.

THE DAY LANE-A LANDS ITS CHANGE, both of those cases go red and the fix is
mechanical: invert them to the assertions written out in their own bodies.
A test that goes red when a blocker is REMOVED is the shape that makes a
blocker impossible to forget, which is the whole reason it is not a comment.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_combat            # noqa: E402
from pirateforce_foundation import mob_death             # noqa: E402
from pirateforce_foundation import mob_identity_sign     # noqa: E402
from pirateforce_foundation import mob_loot              # noqa: E402
from pirateforce_foundation import world_scene_registry  # noqa: E402


#: One real band identity, taken from the allocator rather than typed, so
#: this file cannot drift away from the band it is testing.  Scene 1,
#: placement 0 -- the first monster of the first scene, the row a boot would
#: hit first.
BAND_IDENTITY = mob_identity_sign.mob_wire_identity(1, 0)

#: A player, on the other side of the sign.  Rule 1 of the sign module.
KILLER_IDENTITY = 0x10000001

#: A mined item id, copied from ``tests/test_mob_loot.py`` -- the loot floor
#: refuses an id that is not in the mined table, so an invented number would
#: fail this test for a reason that has nothing to do with identities.
MINED_ITEM_ID = 2400046

SCENE = "bg0001"


def _always_refuses():
    """A stand-in door, for the case that proves the derivation can move."""
    raise ValueError("this door refuses everything")


def _register_a_mob_in_the_world():
    world_scene_registry.MobVital(BAND_IDENTITY, 100, 100)


def _write_its_health_down():
    mob_combat.CombatLedger(
        (mob_combat.MobBalance(BAND_IDENTITY, 100, 100),), 0, SCENE)


def _bind_a_ground_drop_to_it():
    mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE, MINED_ITEM_ID, 1, 1.0, 2.0, 3.0,
        BAND_IDENTITY, KILLER_IDENTITY, SCENE)


def _bury_it():
    mob_death.DeathRegister().with_death(
        mob_death.DeathRecord(BAND_IDENTITY, KILLER_IDENTITY, 100, SCENE))


#: The four doors of PANYA-ORDER 20260908_1545 item 5, in the order a fight
#: uses them, each paired with the name the report should print.
THE_FOUR_DOORS = (
    ("world_scene_registry._require_identity", _register_a_mob_in_the_world),
    ("mob_combat.MobBalance", _write_its_health_down),
    ("mob_loot.GroundDrop", _bind_a_ground_drop_to_it),
    ("mob_death.DeathRegister.with_death", _bury_it),
)


def _doors_that_refuse_the_band(probes=THE_FOUR_DOORS):
    """Which doors REFUSE a band identity, measured by driving each one.

    Derived, never declared.  This is the whole of pf-adversary's D1: the
    first draft of the gate above compared a hand-typed tuple with itself,
    so landing lane A's change could not turn it red.  Here the tuple comes
    out of what the doors DO, so opening one changes the answer.

    A door "refuses" when it raises anything at all.  Deliberately broad:
    the point is whether a monster with this identity can get through, not
    which exception type the module chose, and a door that starts raising
    something new is still a door that stopped letting the band through.
    """
    refused = []
    for name, drive in probes:
        try:
            drive()
        except Exception:                              # noqa: BLE001
            refused.append(name)
    return refused


class TheBandIsWhatTheOrderSaysItIs(unittest.TestCase):
    """Guard the premise before spending four doors on it."""

    def test_the_allocator_hands_out_a_non_positive_identity(self):
        self.assertLess(BAND_IDENTITY, 0)
        self.assertTrue(mob_identity_sign.is_mob_identity(BAND_IDENTITY))
        self.assertFalse(mob_identity_sign.is_player_identity(BAND_IDENTITY))

    def test_zero_is_not_in_the_band_at_all(self):
        """Rule 4: 0 is forbidden outright, measured on screen (R324A)."""
        self.assertFalse(
            mob_identity_sign.identity_is_drawn(
                mob_identity_sign.IDENTITY_NOT_DRAWN))
        with self.assertRaises(mob_identity_sign.MobIdentitySignError):
            mob_identity_sign.refuse_undrawable_identity(0)

    def test_the_killer_is_on_the_other_side_of_the_sign(self):
        self.assertTrue(mob_identity_sign.is_player_identity(KILLER_IDENTITY))


class TheFourDoorsOneMonsterMustPass(unittest.TestCase):
    """One monster, one identity, four modules, in the order a fight uses."""

    def test_leg_1_registering_it_in_the_world_is_still_refused_by_lane_a(self):
        """LEG 1 OF 4, RED ON PURPOSE -- ``world_scene_registry`` is LANE-A's.

        THE ASSERTION TO INVERT the day lane A points ``_require_identity``
        at ``mob_identity_sign``::

            vital = world_scene_registry.MobVital(BAND_IDENTITY, 100, 100)
            self.assertEqual(vital.actor_identity, BAND_IDENTITY)

        Until then the monster the other three doors accept cannot be put
        into the world at all, which is precisely the breakage PANYA-ORDER
        20260908_1545 predicted from the four disagreeing range rules, and
        it is why the allocator does not move this round.
        """
        with self.assertRaises(ValueError) as caught:
            world_scene_registry.MobVital(BAND_IDENTITY, 100, 100)
        # "actor identity", not the bare "out of range" the first draft
        # asserted: pf-adversary (D9) pointed out that ``_require_hp`` in the
        # same module raises "<what> out of range" too, so the loose match
        # would have passed if this leg started failing for the HP argument
        # instead -- a green leg reporting the wrong blocker.
        self.assertIn("actor identity out of range", str(caught.exception))

    def test_leg_2_its_health_is_written_down(self):
        """LEG 2 OF 4 -- the combat ledger carries the band."""
        balance = mob_combat.MobBalance(BAND_IDENTITY, 100, 100)
        self.assertEqual(balance.actor_identity, BAND_IDENTITY)
        ledger = mob_combat.CombatLedger((balance,), 0, SCENE)
        self.assertEqual(ledger.balances[0].actor_identity, BAND_IDENTITY)

    def test_leg_3_a_ground_drop_binds_to_it(self):
        """LEG 3 OF 4 -- the loot floor keys a row by the same number."""
        drop = mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE, MINED_ITEM_ID, 1, 1.0, 2.0, 3.0,
            BAND_IDENTITY, KILLER_IDENTITY, SCENE)
        self.assertEqual(drop.mob_identity, BAND_IDENTITY)
        self.assertEqual(drop.killer_identity, KILLER_IDENTITY)

    def test_leg_4_the_death_register_buries_it(self):
        """LEG 4 OF 4 -- and it is still dead when asked by that number."""
        register = mob_death.DeathRegister()
        record = mob_death.DeathRecord(
            BAND_IDENTITY, KILLER_IDENTITY, 100, SCENE)
        buried = register.with_death(record)
        self.assertIn(BAND_IDENTITY, buried.identities())
        self.assertTrue(buried.is_dead(BAND_IDENTITY))
        self.assertEqual(
            buried.record_of(BAND_IDENTITY).actor_identity, BAND_IDENTITY)

    def test_the_three_open_doors_agree_on_ONE_number(self):
        """ONE ID FOR THE WHOLE CIRCUIT (order item 3, Codex R4).

        The three doors that are open today must be reachable with the same
        value -- not with three values that each module happens to accept.
        A monster whose ledger row, whose dropped crystal and whose grave
        carry three different numbers is three monsters to the client, which
        keys an actor BY its identity.
        """
        balance = mob_combat.MobBalance(BAND_IDENTITY, 100, 100)
        drop = mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE, MINED_ITEM_ID, 1, 1.0, 2.0, 3.0,
            BAND_IDENTITY, KILLER_IDENTITY, SCENE)
        grave = mob_death.DeathRegister().with_death(
            mob_death.DeathRecord(
                BAND_IDENTITY, KILLER_IDENTITY, 100, SCENE))
        self.assertEqual(
            {balance.actor_identity, drop.mob_identity,
             grave.record_of(BAND_IDENTITY).actor_identity},
            {BAND_IDENTITY})

    def test_the_four_in_one_is_not_green_yet(self):
        """The closing token of PANYA-ORDER 20260908_1545, kept honest.

        THE FIRST DRAFT OF THIS CASE WAS A LITERAL COMPARED TO ITSELF
        (pf-adversary, round ``9xv7rc``, D1): it read
        ``assertEqual(still_shut, ("world_scene_registry._require_identity",))``
        over a tuple hard-typed one line above, and the reviewer measured
        that landing lane A's change turns leg 1 red and leaves THIS case
        green -- the one case the round designated as the gate on the flip
        could not be made to fail by any edit to this repository.  A gate
        satisfied by editing the gate is not a gate.

        So the tuple is now DERIVED: every door is driven with the band
        identity and named here only if it actually refused.  The expected
        set is the literal, and the measurement is what is compared to it,
        which is the direction that can go red.
        """
        still_shut = tuple(sorted(_doors_that_refuse_the_band()))
        self.assertEqual(
            still_shut, ("world_scene_registry._require_identity",),
            "the set of doors that refuse a band identity has changed. If a "
            "door was OPENED, invert leg 1 and update the expected tuple in "
            "the same commit -- and only then may field_mobs.actor_identity "
            "move onto the band. If a door CLOSED, a module that used to "
            "carry the band has stopped, and the flip is further away than "
            "it was.")

    def test_the_gate_itself_can_be_made_to_fail(self):
        """The gate above is only a gate if something can turn it red.

        pf-adversary's D1 was not "the assertion is weak", it was "no edit
        to this repository can fail it".  So this case drives the derivation
        with a door that behaves the OTHER way and asserts the answer moves.
        If :func:`_doors_that_refuse_the_band` is ever rewritten back into
        something that ignores what the doors actually do, this goes red.
        """
        self.assertEqual(
            _doors_that_refuse_the_band(
                probes=(("a_door_that_refuses", _always_refuses),
                        ("a_door_that_accepts", lambda: None))),
            ["a_door_that_refuses"])
        self.assertEqual(
            _doors_that_refuse_the_band(
                probes=(("a_door_that_accepts", lambda: None),)),
            [])


class TheSweepRowsAreNotOverwrittenByTheBand(unittest.TestCase):
    """The one collision the band was widened to avoid, re-checked here.

    ``name_colour_sweep`` allocates -1, -2, -3, ... for attended rows, and
    the client keys an actor by its identity, so a production identity
    landing on a sweep row overwrites the board the tester is reading.
    """

    def test_no_production_identity_lands_on_a_reserved_head(self):
        reserved = set(
            range(-mob_identity_sign.SWEEP_RESERVED_IDENTITIES, 0))
        produced = {
            mob_identity_sign.mob_wire_identity(scene, placement)
            for scene in (0, 1, 2, 14, 4095)
            for placement in (0, 1, 2, mob_identity_sign.SCENE_STRIDE - 1)
        }
        self.assertEqual(produced & reserved, set())


if __name__ == "__main__":
    unittest.main()
