"""LANE-B: the per-(viewer, monster) link the client's name colour reads.

The load-bearing test in this file is the FIRST one: with no viewer passed,
``field_mobs.hostile_npc_attr`` must return the SAME BYTES it returned before
this lane grew the keyword.  Everything else here is about the shape of the
field that gets appended when a viewer IS passed, and every one of those
assertions is against ``legacy``'s own encoders rather than against a
hand-typed byte string, so the day the frozen composer moves, these go red
instead of pinning a stale layout.

WHAT THESE TESTS DO NOT PROVE.  Nothing here proves the client accepts the
widened body; that is an attended capture, and the letter for this round asks
for it.  These tests prove the body this lane composes is the frozen body
plus exactly the field the factpack rows describe, in the position the
ascending-mask-bit rule puts it, and that four wrong inputs are refused by
name instead of encoded.
"""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: F401  (import-time gate)
from pirateforce_foundation import field_mobs, mob_name_colour_link
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import SCENE_ID, SCENE_SEQUENCE


VIEWER = 0x5150
OTHER_VIEWER = 0x5151


class MobNameColourLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = list(field_mobs.load_roster())
        assert cls.roster, "the roster is empty; these tests would prove nothing"
        cls.mob = cls.roster[0]

    def _body(self, mob, **kwargs) -> bytes:
        return field_mobs.hostile_npc_attr(self.legacy, mob, **kwargs)

    # --- the load-bearing one --------------------------------------------

    def test_no_viewer_means_byte_identical_to_the_body_before_this_round(
        self,
    ) -> None:
        """Every caller on main passes no viewer; none of them may move."""
        for mob in self.roster:
            with self.subTest(identity=mob.actor_identity):
                plain = self._body(mob)
                explicit_none = self._body(mob, viewer_identity=None)
                self.assertEqual(plain, explicit_none)
                # And the same claim against the composer's own contract:
                # the frozen baseline plus exactly the two documented splices.
                baseline = self.legacy.make_npc_attr(
                    mob.template_id, mob.actor_identity, SCENE_ID,
                    SCENE_SEQUENCE, mob.visual_preset, mob.max_hp, mob.max_hp,
                    movement_speed=float(mob.speed_walk),
                    basic_name=mob.display_name,
                )
                self.assertEqual(
                    len(plain),
                    len(baseline)
                    + field_mobs.FACTION_SPLICE_BYTES
                    + field_mobs.LEVEL_SPLICE_BYTES,
                )

    # --- the shape of the field that appears when a viewer is passed ------

    def test_a_viewer_adds_exactly_the_tagged_qword_and_nothing_else(self) -> None:
        mob = self.mob
        plain = self._body(mob)
        linked = self._body(mob, viewer_identity=VIEWER)
        expected_tag = bytes(
            self.legacy.qwordtag(mob_name_colour_link.LINKED_IDENTITY_TAG, VIEWER)
        )
        self.assertEqual(len(linked), len(plain) + len(expected_tag))
        self.assertTrue(linked.endswith(expected_tag))

    def test_the_npc_field_mask_gains_bit_0x08_and_keeps_its_other_bits(
        self,
    ) -> None:
        mob = self.mob
        plain = self._body(mob)
        linked = self._body(mob, viewer_identity=VIEWER)
        before = mob_name_colour_link.npc_mask_for(mob.visual_preset)
        after = before | mob_name_colour_link.NPC_MASK_BIT_LINKED_IDENTITY
        old_mask_bytes = bytes(
            self.legacy.u8tag(mob_name_colour_link.NPC_FIELD_MASK_TAG, before)
        )
        new_mask_bytes = bytes(
            self.legacy.u8tag(mob_name_colour_link.NPC_FIELD_MASK_TAG, after)
        )
        self.assertIn(old_mask_bytes, plain)
        self.assertIn(new_mask_bytes, linked)
        # The old mask value must be GONE from the linked body's tail: a body
        # carrying both would mean the splice added a second mask rather than
        # widening the one the frozen composer wrote.
        self.assertEqual(linked.count(new_mask_bytes), 1)

    def test_two_viewers_of_the_same_monster_get_different_bodies(self) -> None:
        """The whole point of the field: one monster, two answers."""
        mob = self.mob
        first = self._body(mob, viewer_identity=VIEWER)
        second = self._body(mob, viewer_identity=OTHER_VIEWER)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), len(second))

    def test_the_linked_field_carries_the_viewer_not_the_monster(self) -> None:
        mob = self.mob
        linked = self._body(mob, viewer_identity=VIEWER)
        monster_tag = bytes(
            self.legacy.qwordtag(
                mob_name_colour_link.LINKED_IDENTITY_TAG, mob.actor_identity
            )
        )
        viewer_tag = bytes(
            self.legacy.qwordtag(mob_name_colour_link.LINKED_IDENTITY_TAG, VIEWER)
        )
        self.assertTrue(linked.endswith(viewer_tag))
        self.assertNotEqual(monster_tag, viewer_tag)

    def test_the_entry_composer_passes_the_viewer_through(self) -> None:
        mob = self.mob
        plain = field_mobs.hostile_actor_entry(self.legacy, mob)
        linked = field_mobs.hostile_actor_entry(
            self.legacy, mob, viewer_identity=VIEWER
        )
        self.assertNotEqual(plain, linked)
        self.assertGreater(len(linked), len(plain))

    # --- the refusals ----------------------------------------------------

    def test_a_monster_may_not_be_linked_to_itself(self) -> None:
        mob = self.mob
        with self.assertRaises(mob_name_colour_link.MobNameColourLinkError) as ctx:
            self._body(mob, viewer_identity=mob.actor_identity)
        self.assertIn(
            mob_name_colour_link.REFUSE_VIEWER_IS_THE_MONSTER, str(ctx.exception)
        )

    def test_a_nonpositive_viewer_is_refused_by_name(self) -> None:
        for bad in (0, -1):
            with self.subTest(viewer=bad):
                with self.assertRaises(
                    mob_name_colour_link.MobNameColourLinkError
                ) as ctx:
                    self._body(self.mob, viewer_identity=bad)
                self.assertIn(
                    mob_name_colour_link.REFUSE_VIEWER_IDENTITY_NOT_POSITIVE,
                    str(ctx.exception),
                )

    def test_a_bool_is_not_an_identity(self) -> None:
        """``True`` is an ``int`` in Python; it is not an actor identity."""
        with self.assertRaises(mob_name_colour_link.MobNameColourLinkError) as ctx:
            self._body(self.mob, viewer_identity=True)
        self.assertIn(
            mob_name_colour_link.REFUSE_VIEWER_IDENTITY_NOT_POSITIVE,
            str(ctx.exception),
        )

    def test_a_viewer_wider_than_the_qword_is_refused_before_struct_sees_it(
        self,
    ) -> None:
        with self.assertRaises(mob_name_colour_link.MobNameColourLinkError) as ctx:
            self._body(
                self.mob,
                viewer_identity=mob_name_colour_link.LINKED_IDENTITY_CEILING + 1,
            )
        self.assertIn(
            mob_name_colour_link.REFUSE_VIEWER_IDENTITY_OUT_OF_RANGE,
            str(ctx.exception),
        )

    def test_a_body_whose_tail_moved_is_refused_instead_of_patched(self) -> None:
        """The guard that makes this splice safe to keep.

        A body that does not end the way the frozen composer ends one is a
        body whose layout moved; patching it by offset would put the field
        somewhere the client does not read.
        """
        mob = self.mob
        body = self._body(mob)
        with self.assertRaises(mob_name_colour_link.MobNameColourLinkError) as ctx:
            mob_name_colour_link.link_viewer_to_npc_attr(
                self.legacy,
                body + b"\x00",
                viewer_identity=VIEWER,
                monster_identity=mob.actor_identity,
                template_id=mob.template_id,
                visual_preset=mob.visual_preset,
            )
        self.assertIn(
            mob_name_colour_link.REFUSE_BODY_TAIL_DRIFT, str(ctx.exception)
        )

    def test_a_body_composed_for_another_monster_row_is_refused(self) -> None:
        """A template id that is not the one in the body is the same drift."""
        mob = self.mob
        body = self._body(mob)
        with self.assertRaises(mob_name_colour_link.MobNameColourLinkError) as ctx:
            mob_name_colour_link.link_viewer_to_npc_attr(
                self.legacy,
                body,
                viewer_identity=VIEWER,
                monster_identity=mob.actor_identity,
                template_id=mob.template_id + 1,
                visual_preset=mob.visual_preset,
            )
        self.assertIn(
            mob_name_colour_link.REFUSE_BODY_TAIL_DRIFT, str(ctx.exception)
        )

    # --- the constants, against the artifact rows they came from ----------

    def test_the_constants_match_the_factpack_row_they_were_read_from(self) -> None:
        """PF_A2_ATTR_FIELD_DELTA.tsv:150/151 -- tag 0x32, 8 bytes, bit 0x08.

        Typed out here so that a later round that "tidies" one of these
        constants has to come and change a test that names its source.
        """
        self.assertEqual(mob_name_colour_link.LINKED_IDENTITY_TAG, 0x32)
        self.assertEqual(mob_name_colour_link.LINKED_IDENTITY_WIRE_LEN, 8)
        self.assertEqual(mob_name_colour_link.NPC_MASK_BIT_LINKED_IDENTITY, 0x08)
        self.assertEqual(mob_name_colour_link.NPC_FIELD_MASK_TAG, 0x0B)

    def test_this_module_does_not_carry_the_other_plus_0x98_shape(self) -> None:
        """ActorAttr+0x98 is a u8 with tag 0x0B; NPCAttr+0x98 is a u64.

        Confusing them is the failure this module's docstring exists to
        prevent, so the difference is asserted rather than only described.
        """
        self.assertNotEqual(
            mob_name_colour_link.LINKED_IDENTITY_TAG,
            mob_name_colour_link.NPC_FIELD_MASK_TAG,
        )
        self.assertIn(
            "ActorAttr+0x98",
            mob_name_colour_link.OTHER_ACTORATTR_LINK_AT_0X98,
        )

    def test_the_wiring_constant_names_a_runtime_call_site_not_this_file(
        self,
    ) -> None:
        wiring = mob_name_colour_link.MOB_NAME_COLOUR_LINK_WIRING
        self.assertIn("runtime.py", wiring)
        self.assertIn("viewer_identity", wiring)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
