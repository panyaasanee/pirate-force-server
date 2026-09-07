"""The ALL / ALL-NOID sweep: every candidate the owner listed, in one boot.

PANYA-ORDER 2026-09-07T23:25+07:00 and its addendum 23:50, relayed by
COO-ORDER 23:42 (``pf_bridge/notes_to_chief/20260907_2342_COO-ORDER-
panya2325-sweep-all-26-rows-iron-man-square-first-job-LANE-B.md``).  These
tests hold the parts of that order that a machine can check: which rows the
boot draws, that the rows it does NOT draw are refused by somebody else's
standing guard rather than quietly dropped, that each row differs from its own
control by exactly the bytes its own label names, and where the row stands.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA
from pirateforce_foundation import field_mobs, mob_viewer_link, name_colour_sweep
from pirateforce_foundation.legacy_bridge import load_legacy

ALL_ENV = {"PF_NAME_COLOUR_SWEEP": name_colour_sweep.SET_ALL}
NOID_ENV = {"PF_NAME_COLOUR_SWEEP": name_colour_sweep.SET_ALL_NOID}
#: A viewer identity that is not any sweep row's own identity, so the linked
#: rows compose instead of hitting mob_viewer_link's self-link refusal.
VIEWER = 0x0000000123456789


@BRIDGE_GAMEDATA.skip_unless_present()
class AllSetRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def _labels(self, env: dict, viewer: int | None = None) -> tuple[str, ...]:
        return tuple(
            a.label for a in name_colour_sweep.sweep_actors(
                self.legacy, env, viewer_identity=viewer,
            )
        )

    def test_all_noid_is_all_minus_the_identity_families_and_nothing_else(self) -> None:
        """ALL-NOID is a SUBSET, derived, not a second hand-typed list."""
        for viewer in (None, VIEWER):
            with self.subTest(viewer=viewer):
                every = self._labels(ALL_ENV, viewer)
                noid = self._labels(NOID_ENV, viewer)
                self.assertEqual(noid, tuple(l for l in every if l in set(noid)))
                dropped = set(every) - set(noid)
                # Every dropped label belongs to an identity family: it either
                # carries a non-positive identity of its own or is one of the
                # owner's mixes built on one.
                identities = {
                    a.label: a.actor_identity
                    for a in name_colour_sweep.sweep_actors(
                        self.legacy, ALL_ENV, viewer_identity=viewer)
                }
                for label in dropped:
                    self.assertLessEqual(
                        identities[label], 0,
                        f"{label} was dropped from ALL-NOID but its identity "
                        "is an ordinary positive one",
                    )
                for label in noid:
                    self.assertGreater(identities[label], 0)

    def test_the_rows_that_are_not_drawn_are_refused_by_a_real_guard(self) -> None:
        """Not 'left out': each one RAISES when this test composes it here."""
        drawn = set(self._labels(ALL_ENV, VIEWER))
        for label, reason in name_colour_sweep.all_set_uncomposable_rows():
            self.assertNotIn(label, drawn)
            self.assertTrue(reason.strip(), f"{label} has no written reason")
        mob = name_colour_sweep._mob_prototype()
        with self.assertRaises(field_mobs.FieldMobContractError):
            # M-DEAD / M-IDNEG-DEAD.
            field_mobs.hostile_npc_attr(self.legacy, mob, current_hp=0)
        body = name_colour_sweep._npc_plain_body(self.legacy, 0x99999, "N-LNKS")
        with self.assertRaises(mob_viewer_link.MobViewerLinkError):
            # N-LNKS: the self-link.
            name_colour_sweep._npc_linked_body(
                self.legacy, 0x99999, "N-LNKS", 0x99999, body=body,
            )

    def test_the_viewer_rows_appear_only_when_a_viewer_identity_is_known(self) -> None:
        without = set(self._labels(ALL_ENV))
        with_viewer = set(self._labels(ALL_ENV, VIEWER))
        needed = set(name_colour_sweep.all_set_rows_needing_viewer_identity())
        self.assertEqual(with_viewer - without, needed)
        self.assertFalse(needed & without)

    def test_every_linked_row_carries_that_viewer_and_nothing_else_moved(self) -> None:
        rows = {
            a.label: a for a in name_colour_sweep.sweep_actors(
                self.legacy, ALL_ENV, viewer_identity=VIEWER)
        }
        for label in name_colour_sweep.all_set_rows_needing_viewer_identity():
            with self.subTest(label=label):
                actor = rows[label]
                plain = name_colour_sweep._npc_plain_body(
                    self.legacy, actor.actor_identity, label,
                )
                if label.endswith("-LNKP") and "ENM" not in label:
                    expected = mob_viewer_link.link_viewer_to_npc_attr(
                        self.legacy, plain,
                        viewer_identity=VIEWER,
                        monster_identity=actor.actor_identity,
                        template_id=name_colour_sweep.NPC_BASE_TEMPLATE_ID,
                        visual_preset=name_colour_sweep.NPC_BASE_VISUAL_PRESET,
                    )
                    self.assertEqual(actor.npc_attr, expected)
                self.assertIn(
                    bytes(self.legacy.qwordtag(
                        mob_viewer_link.LINKED_IDENTITY_TAG, VIEWER)),
                    actor.npc_attr,
                )

    def test_every_enemy_row_is_its_control_plus_exactly_the_enemy_field(self) -> None:
        rows = {
            a.label: a for a in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)
        }
        for value in name_colour_sweep.ENEMY_CANDIDATES:
            label = "N-ENM%s" % ("FF" if value == 0xFF else value)
            with self.subTest(label=label):
                actor = rows[label]
                plain = name_colour_sweep._npc_plain_body(
                    self.legacy, actor.actor_identity, label,
                )
                self.assertEqual(
                    len(actor.npc_attr),
                    len(plain) + name_colour_sweep.ENEMY_SPLICE_BYTES,
                )
                mask_at = field_mobs._basic_mask_offset(
                    self.legacy, actor.npc_attr, actor.actor_identity,
                )
                mask = int.from_bytes(actor.npc_attr[mask_at:mask_at + 2], "little")
                plain_mask = int.from_bytes(plain[mask_at:mask_at + 2], "little")
                self.assertEqual(
                    mask ^ plain_mask, name_colour_sweep.BASIC_BIT_ENEMY,
                    "the enemy row moved a mask bit that is not n_ENEMY",
                )
                self.assertIn(
                    bytes(self.legacy.u32tag(name_colour_sweep.ENEMY_TAG, value)),
                    actor.npc_attr,
                )
                # Everything except the mask and the appended field is the
                # control, byte for byte.
                spliced_at = field_mobs._faction_splice_offset(
                    self.legacy, plain,
                    name_colour_sweep.NPC_BASE_TEMPLATE_ID,
                    name_colour_sweep.NPC_BASE_VISUAL_PRESET,
                )
                rebuilt = (
                    actor.npc_attr[:mask_at]
                    + plain_mask.to_bytes(2, "little")
                    + actor.npc_attr[mask_at + 2:spliced_at]
                    + actor.npc_attr[
                        spliced_at + name_colour_sweep.ENEMY_SPLICE_BYTES:]
                )
                self.assertEqual(rebuilt, plain)

    def test_the_monster_enemy_row_is_the_monster_body_plus_the_same_field(self) -> None:
        rows = {a.label: a for a in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)}
        actor = rows["M-ENM1"]
        base = rows["M-BASE"]
        self.assertEqual(
            len(actor.npc_attr),
            len(base.npc_attr) + name_colour_sweep.ENEMY_SPLICE_BYTES,
            "M-ENM1 is not M-BASE plus one field (labels and identities are "
            "the same length by construction)",
        )
        self.assertIn(
            bytes(self.legacy.u32tag(name_colour_sweep.ENEMY_TAG, 1)),
            actor.npc_attr,
        )

    def test_m_t001_is_the_monster_carrying_the_npc_template_and_nothing_else(self) -> None:
        rows = {a.label: a for a in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)}
        mob = name_colour_sweep._mob_prototype()
        from dataclasses import replace
        actor = rows["M-T001"]
        control = field_mobs.hostile_npc_attr(
            self.legacy,
            replace(
                mob,
                placement_index=(actor.actor_identity - 1) - 0x2000,
                display_name="M-T001",
                template_id=name_colour_sweep.NPC_BASE_TEMPLATE_ID,
            ),
            faction=field_mobs.FIELD_MOB_FACTION,
        )
        self.assertEqual(actor.npc_attr, control)
        self.assertIn(
            bytes(self.legacy.u16tag(0x12, name_colour_sweep.NPC_BASE_TEMPLATE_ID)),
            actor.npc_attr,
        )

    def test_the_row_stands_on_the_iron_man_square_the_owner_named(self) -> None:
        z = None
        for row in name_colour_sweep.field_mob_tables.TOWN_TARGET_PLACEMENTS:
            if row[0] == name_colour_sweep.ALL_ROW_Z_SOURCE_PLACEMENT_INDEX:
                z = float(row[4])
        self.assertIsNotNone(z)
        actors = name_colour_sweep.sweep_actors(
            self.legacy, ALL_ENV, viewer_identity=VIEWER)
        for ordinal, actor in enumerate(actors):
            line, column = divmod(ordinal, name_colour_sweep.ALL_ROWS_PER_LINE)
            with self.subTest(label=actor.label):
                self.assertEqual(
                    actor.x,
                    name_colour_sweep.ALL_ROW_X0
                    + name_colour_sweep.ALL_ROW_DX * column,
                )
                self.assertEqual(
                    actor.y,
                    name_colour_sweep.ALL_ROW_Y
                    + name_colour_sweep.ALL_ROW_Y_SPLIT * line,
                )
                self.assertEqual(actor.z, z)
        # The line does not run into the shipped dummies it stands beside.
        for row in name_colour_sweep.field_mob_tables.TOWN_TARGET_PLACEMENTS:
            for actor in actors:
                self.assertGreater(
                    abs(float(row[2]) - actor.x) + abs(float(row[3]) - actor.y),
                    1.0,
                    f"{actor.label} stands on shipped placement {row[0]}",
                )

    def test_the_death_row_really_carries_zero_hp_on_the_wire(self) -> None:
        """The named constant hides nothing: the bytes are checked here."""
        rows = {a.label: a for a in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)}
        actor = rows["N-HP0"]
        self.assertEqual(name_colour_sweep.SWEEP_HP_ZERO, 0)
        self.assertEqual(
            actor.npc_attr,
            name_colour_sweep._npc_plain_body(
                self.legacy, actor.actor_identity, "N-HP0",
                current_hp=name_colour_sweep.SWEEP_HP_ZERO),
        )
        self.assertNotEqual(
            actor.npc_attr,
            name_colour_sweep._npc_plain_body(
                self.legacy, actor.actor_identity, "N-HP0"),
        )

    def test_every_label_is_ascii_short_and_unique(self) -> None:
        for env in (ALL_ENV, NOID_ENV):
            labels = self._labels(env, VIEWER)
            self.assertEqual(len(labels), len(set(labels)))
            for label in labels:
                self.assertTrue(label.isascii(), label)
                self.assertLessEqual(len(label), 12, label)

    def test_a_non_positive_identity_cannot_collide_with_a_real_actor(self) -> None:
        """Why 0 and -1 are safe to send even though they leave the band."""
        lowest_real = 0x2000 + 0 + 1
        for actor in name_colour_sweep.sweep_actors(
                self.legacy, ALL_ENV, viewer_identity=VIEWER):
            if actor.actor_identity > 0:
                continue
            self.assertLess(actor.actor_identity, lowest_real)

    def test_no_two_boards_share_an_actor_identity(self) -> None:
        """pf-adversary round ixdda8 finding D3, pinned by execution.

        Six rows shared two identities.  The client keys an actor by its
        identity, so two boards carrying the same one overwrite each other:
        the board that survives names one question while the body drawn may
        answer another, and that result cannot be told from a wrong one.
        """
        for env in (ALL_ENV, NOID_ENV):
            for viewer in (None, VIEWER):
                rows = name_colour_sweep.sweep_actors(
                    self.legacy, env, viewer_identity=viewer)
                identities = [actor.actor_identity for actor in rows]
                with self.subTest(env=env["PF_NAME_COLOUR_SWEEP"], viewer=viewer):
                    self.assertEqual(len(identities), len(set(identities)))

    def test_a_labels_identity_does_not_move_when_other_rows_come_and_go(self) -> None:
        """The slot table is what makes an identity a property of the LABEL.

        Without it the negative rows are numbered by composition order, so
        supplying a viewer identity silently renumbers every later board and
        the attended sheet from one boot does not describe the next.
        """
        seen: dict[str, int] = {}
        for env in (ALL_ENV, NOID_ENV):
            for viewer in (None, VIEWER):
                for actor in name_colour_sweep.sweep_actors(
                        self.legacy, env, viewer_identity=viewer):
                    if actor.label in seen:
                        self.assertEqual(
                            seen[actor.label], actor.actor_identity,
                            f"{actor.label} changed identity between boots")
                    seen[actor.label] = actor.actor_identity
        # And the ones that carry a declared negative slot carry THAT value.
        for label in name_colour_sweep.NEGATIVE_IDENTITY_SLOTS:
            if label in seen:
                self.assertEqual(
                    seen[label], name_colour_sweep.negative_identity_for(label))

    def test_every_negative_identity_is_its_own_slot_and_stays_negative(self) -> None:
        """The pool is distinct AND on one side of the RE-222 split."""
        values = [
            name_colour_sweep.negative_identity_for(label)
            for label in name_colour_sweep.NEGATIVE_IDENTITY_SLOTS
        ]
        self.assertEqual(len(values), len(set(values)))
        for label, value in zip(name_colour_sweep.NEGATIVE_IDENTITY_SLOTS, values):
            with self.subTest(label=label):
                self.assertLess(value, 0)
                # sign-extended high word is -1 for every slot, so every slot
                # is the same side of "the 64-bit identity is not positive"
                self.assertEqual((value >> 32) & 0xFFFFFFFF, 0xFFFFFFFF)
        with self.assertRaises(name_colour_sweep.NameColourSweepError):
            name_colour_sweep.negative_identity_for("N-NOT-A-ROW")

    def test_a_monster_rows_placement_index_really_carries_its_identity(self) -> None:
        """``placement_index_for_identity`` is the only way a mob row gets one."""
        for label in ("M-IDNEG", "M-IDNEG-T31"):
            wanted = name_colour_sweep.negative_identity_for(label)
            index = name_colour_sweep.placement_index_for_identity(wanted)
            with self.subTest(label=label):
                self.assertEqual(0x2000 + index + 1, wanted)
        rows = {
            actor.label: actor
            for actor in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)
        }
        for label in ("M-IDNEG", "M-IDNEG-T31"):
            self.assertEqual(
                rows[label].actor_identity,
                name_colour_sweep.negative_identity_for(label))

    def test_exactly_one_board_carries_the_zero_identity(self) -> None:
        """The zero class holds one value, so it gets one board, not two."""
        for viewer in (None, VIEWER):
            rows = name_colour_sweep.sweep_actors(
                self.legacy, ALL_ENV, viewer_identity=viewer)
            zeros = [a.label for a in rows if a.actor_identity == 0]
            with self.subTest(viewer=viewer):
                self.assertEqual(zeros, [name_colour_sweep.ALL_ZERO_IDENTITY_LABEL])
        self.assertIn(
            "N-ID0-LNKP",
            [label for label, _ in name_colour_sweep.ALL_SET_UNCOMPOSABLE])
        self.assertNotIn(
            "N-ID0-LNKP", name_colour_sweep.ALL_SET_NEEDS_VIEWER_IDENTITY)

    def test_the_identity_times_template_rows_are_read_from_the_shipped_tables(self) -> None:
        """ka1-A addendum 2: the colour comes from the TEMPLATE once a body is
        on the NPC branch, so identity has to be crossed with template.

        Both templates are read out of a shipped roster.  Nothing here writes
        to bg0002; it is loaded and looked at.
        """
        eagle = name_colour_sweep._identity_template_mob_prototype()
        self.assertEqual(
            eagle.template_id,
            name_colour_sweep.IDENTITY_TEMPLATE_MOB_TEMPLATE_ID)
        self.assertIn(
            eagle,
            field_mobs.load_roster(
                scene=name_colour_sweep.IDENTITY_TEMPLATE_MOB_SCENE))
        rows = {
            actor.label: actor
            for actor in name_colour_sweep.sweep_actors(self.legacy, ALL_ENV)
        }
        self.assertIn("M-IDNEG-T31", rows)
        self.assertIn("N-IDNEG-T916", rows)
        # N-IDNEG-T916 is the NPC control body with the monster's template and
        # preset, and its own identity -- nothing else moved.
        control = rows["N-IDNEG-T916"]
        mob = name_colour_sweep._mob_prototype()
        expected = name_colour_sweep._npc_plain_body(
            self.legacy, control.actor_identity, "N-IDNEG-T916",
            template_id=mob.template_id, visual_preset=mob.visual_preset)
        self.assertEqual(control.npc_attr, expected)

    def test_the_identity_times_template_rows_are_absent_from_all_noid(self) -> None:
        """They are identity rows, so the identity-free boot leaves them out."""
        labels = self._labels(NOID_ENV, VIEWER)
        self.assertNotIn("M-IDNEG-T31", labels)
        self.assertNotIn("N-IDNEG-T916", labels)

    def test_the_declared_row_order_names_every_row_and_no_others(self) -> None:
        """The slot table is the identity oracle, so it has to be complete."""
        drawn: set[str] = set()
        for env in (ALL_ENV, NOID_ENV):
            for viewer in (None, VIEWER):
                drawn.update(self._labels(env, viewer))
        nameable = drawn | {
            label for label, _ in name_colour_sweep.ALL_SET_UNCOMPOSABLE
        } | set(name_colour_sweep.ALL_SET_NEEDS_VIEWER_IDENTITY)
        self.assertEqual(set(name_colour_sweep.ALL_ROW_ORDER), nameable)
        self.assertEqual(
            len(name_colour_sweep.ALL_ROW_ORDER),
            len(set(name_colour_sweep.ALL_ROW_ORDER)))
        with self.assertRaises(name_colour_sweep.NameColourSweepError):
            name_colour_sweep.all_row_placement_index("N-NOT-A-ROW")

    def test_every_board_drawn_carries_a_prediction(self) -> None:
        """ka1-A addendum 2: a board with no prediction records a colour; it
        does not grade a hypothesis.  No test here asserts a prediction is
        RIGHT -- nothing in this repository can read a screen."""
        drawn: set[str] = set()
        for env in (ALL_ENV, NOID_ENV):
            for viewer in (None, VIEWER):
                for actor in name_colour_sweep.sweep_actors(
                        self.legacy, env, viewer_identity=viewer):
                    drawn.add(actor.label)
                    with self.subTest(label=actor.label):
                        self.assertTrue(
                            name_colour_sweep.prediction_for(actor.label).strip())
        # No orphan predictions: every declared prediction names a row that is
        # either drawn, or refused with a written reason.
        named = drawn | {label for label, _ in name_colour_sweep.ALL_SET_UNCOMPOSABLE}
        self.assertEqual(
            set(name_colour_sweep.ALL_ROW_PREDICTIONS) - named, set())
        with self.assertRaises(name_colour_sweep.NameColourSweepError):
            name_colour_sweep.prediction_for("N-NOT-A-ROW")

    def test_the_headless_token_tool_reports_what_the_module_composes(self) -> None:
        """The token an attended ticket cites has to be re-runnable.

        Rule 0159 wants a console token measured on the commit the ticket is
        written against.  The boot-time NAME_COLOUR_SWEEP_ARMED line needs a
        real client; this tool prints the half that does not, so LANE-K and
        ka1-A can re-run one command and compare instead of trusting prose.
        """
        import subprocess

        tool = ROOT / "tools" / "pf_name_colour_sweep_headless.py"
        self.assertTrue(tool.is_file())
        done = subprocess.run(
            [sys.executable, str(tool)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        drawn = len(name_colour_sweep.sweep_actors(self.legacy, ALL_ENV))
        self.assertIn(
            f"NAME_COLOUR_SWEEP_COMPOSED set={name_colour_sweep.SET_ALL} "
            f"actors={drawn} ",
            done.stdout,
        )
        self.assertIn("NAME_COLOUR_SWEEP_UNARMED actors=0", done.stdout)
        self.assertIn("NAME_COLOUR_SWEEP_HEADLESS PASS", done.stdout)

    def test_every_positive_identity_row_stays_in_the_reserved_band(self) -> None:
        """The half of the band pin that still applies to this set."""
        for env in (ALL_ENV, NOID_ENV):
            for actor in name_colour_sweep.sweep_actors(
                    self.legacy, env, viewer_identity=VIEWER):
                if actor.actor_identity <= 0:
                    continue
                with self.subTest(label=actor.label):
                    self.assertGreaterEqual(
                        (actor.actor_identity - 1) - 0x2000,
                        name_colour_sweep.SWEEP_PLACEMENT_BASE,
                    )

    def test_the_owner_row_overlaps_the_live_town_so_all_needs_an_empty_world(self) -> None:
        """MEASURED, and the reason COO-ORDER 2342 item 4 exists.

        The anchored sets keep :data:`ROW_CLEARANCE_FROM_REAL_NPCS` between
        every dummy and every real nameboard, because they ship INTO the live
        Port Royal census.  The ALL row cannot: the owner placed it by
        absolute coordinate on the Iron Man square, and that square is inside
        the town -- the closest real placement is a few tens of units away.
        That is exactly why the order says the ALL boot sends NO census
        (``census_actors=0``), and it is why this lane must not quietly ship
        ALL into a populated town.  This test pins the overlap so the day
        somebody moves the row into open ground, the claim above stops being
        true loudly instead of silently.
        """
        floor = name_colour_sweep.ROW_CLEARANCE_FROM_REAL_NPCS
        real = [
            (float(p[2]), float(p[3]), p[6])
            for p in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        ]
        self.assertTrue(real)
        closest = min(
            (
                (((actor.x - x) ** 2 + (actor.y - y) ** 2) ** 0.5, actor.label, name)
                for actor in name_colour_sweep.sweep_actors(
                    self.legacy, ALL_ENV, viewer_identity=VIEWER)
                for x, y, name in real
            ),
        )
        self.assertLess(
            closest[0], floor,
            "the ALL row now clears every real nameboard -- if that is "
            "deliberate, the empty-world requirement can be re-argued and "
            "this test replaced by the ordinary clearance pin",
        )

    def test_unarmed_and_unknown_values_draw_no_all_rows(self) -> None:
        self.assertEqual(name_colour_sweep.sweep_actors(self.legacy, {}), ())
        self.assertEqual(
            name_colour_sweep.sweep_actors(
                self.legacy, {"PF_NAME_COLOUR_SWEEP": "ALL "}), (),
        )
        self.assertEqual(
            name_colour_sweep.unrecognised_env_value({"PF_NAME_COLOUR_SWEEP": "ALL "}),
            "ALL ",
        )
        for value in (name_colour_sweep.SET_ALL, name_colour_sweep.SET_ALL_NOID):
            self.assertIsNone(
                name_colour_sweep.unrecognised_env_value(
                    {"PF_NAME_COLOUR_SWEEP": value})
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
