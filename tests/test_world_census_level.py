"""LANE-A: the census level splice, on the real frozen serializer.

The wire/DB half of the two-layer evidence rule for the field ``GT-192``
showed missing.  What this file proves without a client: the frozen
serializer alone sends no level at all (the defect), the splice adds exactly
one field and exactly one mask bit and reduces back to the frozen body, it
refuses every shape it was not derived on, and the level it writes is read
back byte-identically by the same reader that reads lane B's already-proven
hostile bodies.

What it cannot prove, and does not: that a client draws ``LV 105`` over an
actor's head.  ``GT-192``'s next run is that ticket.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_hostile_bg0015 as hostile15  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import world_bg0006_identity as identity  # noqa: E402
from pirateforce_foundation import world_census_level as level_splice  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_port_royal_identity  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SCENE_ID = 6
SCENE_SEQUENCE = 0

# Every ordinary census composer wired to send a level, named once so the
# cross-scene test below and the source-side check under it read the same
# list.  bg0001/bg0002 are deliberately absent -- see those tests.
WIRED_SCENES = (
    "bg0003", "bg0004", "bg0005", "bg0006", "bg0007", "bg0008",
    "bg0009", "bg0010", "bg0011", "bg0015", "bg1001", "bg3001", "bg4001",
)

# bg0001 and bg0002 are wired too but are not in the loop above: bg0002's
# composer takes its constants from its own scene tables (``SCENE2_N_ID``)
# and its rows carry ``level`` directly rather than through a
# ``SceneIdentity``; bg0001's composer lives in ``world_population`` itself,
# takes its HP from a per-placement rule rather than the roster, and resolves
# identities through ``world_port_royal_identity``.  Each gets its own test
# rather than a special case inside a shared one.
WIRED_COMPOSERS = tuple(sorted(
    ["world_population.py", "world_population_bg0002.py"]
    + ["world_population_%s.py" % scene for scene in WIRED_SCENES]
))

# Every live census source, keyed by the name ``world_scene_travel
# .CENSUS_SOURCES`` gives it, mapped to the module that composes it.  This
# exists because the round's first pin (the glob below) is one-directional:
# pf-adversary dropped a new ``world_population_bg0012.py`` that did not
# import this module and the whole file stayed green, because a composer that
# is simply MISSING looks exactly like one nobody has built yet.  That is the
# failure ``world_population_handoff.SCENES_INTENTIONALLY_UNPOPULATED`` was
# written to prevent for a different table, applied here.
CENSUS_SOURCE_COMPOSERS = {
    "bg0001_census": "world_population",
    "bg0002_roster": "world_population_bg0002",
    "bg0003_roster": "world_population_bg0003",
    "bg0004_roster": "world_population_bg0004",
    "bg0005_roster": "world_population_bg0005",
    "bg0006_roster": "world_population_bg0006",
    "bg0007_roster": "world_population_bg0007",
    "bg0008_roster": "world_population_bg0008",
    "bg0009_roster": "world_population_bg0009",
    "bg0010_roster": "world_population_bg0010",
    "bg0011_roster": "world_population_bg0011",
    "bg0015_roster": "world_population_bg0015",
    # ADDED round 4uztfj (LANE-A): scene 126, the ocean panel.  Its level
    # column is mined the same way every island's is (MOBS.n_LEVEL_MIN ->
    # STANDARD_MOB), so it belongs in the map above rather than in
    # CENSUS_SOURCES_WITHOUT_A_MINED_LEVEL below -- its levels really do
    # vary (1, 5, 60, 110, 120), which the cross-scene loop asserts.
    "bg3001_roster": "world_population_bg3001",
    "bg4001_roster": "world_population_bg4001",
    # ADDED round vwekfq (LANE-A): scene 17, the ship at sea.  Its level
    # column is mined the same way every island's is (MOBS.n_LEVEL_MIN ->
    # STANDARD_MOB), levels really do vary (30, 32, 34, 35) - the
    # cross-scene loop asserts that too.
    "bg1001_roster": "world_population_bg1001",
}

# A live census source that deliberately sends no level, and why.  Empty on
# purpose since round `7ste68` wired the last one (scene 1, Port Royal, whose
# mined level column that round's own first draft wrongly reported as
# missing).  A future source with no mined level belongs HERE, with its
# reason, not merely absent from the map above -- a decision that reads as an
# oversight is an oversight.
CENSUS_SOURCES_WITHOUT_A_MINED_LEVEL: dict[str, str] = {}


class CensusLevelSplice(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.placement = next(
            p for p in identity.shippable_placements() if p.display_name)

    def _frozen(self, *, name: str | None = None) -> bytes:
        placement = self.placement
        return self.legacy.make_npc_attr(
            placement.n_id,
            placement.actor_identity,
            SCENE_ID,
            SCENE_SEQUENCE,
            placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name if name is None else name,
        )

    def _spliced(self, *, level: int = 71, name: str | None = None) -> bytes:
        placement = self.placement
        return level_splice.with_level(
            self.legacy, self._frozen(name=name),
            actor_identity=placement.actor_identity,
            basic_name=placement.display_name if name is None else name,
            level=level,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
        )

    def test_the_frozen_body_carries_no_level_at_all(self) -> None:
        """The defect GT-192 put on the owner's screen, stated as a test.

        Not "the client ignored the level we sent": there is no level in
        these bytes to ignore.  If this ever starts returning a number, the
        frozen serializer grew the field itself and this whole module should
        be deleted rather than kept alongside it.
        """
        body = self._frozen()
        self.assertIsNone(level_splice.read_level(
            self.legacy, body, self.placement.actor_identity))
        mask_at = level_splice.basic_mask_offset(
            self.legacy, body, self.placement.actor_identity)
        mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
        self.assertFalse(mask & level_splice.BASIC_BIT_LEVEL)

    def test_the_splice_adds_exactly_one_field_and_one_mask_bit(self) -> None:
        frozen = self._frozen()
        spliced = self._spliced(level=71)
        self.assertEqual(
            len(spliced), len(frozen) + level_splice.LEVEL_SPLICE_BYTES)
        mask_at = level_splice.basic_mask_offset(
            self.legacy, frozen, self.placement.actor_identity)
        before = int.from_bytes(frozen[mask_at:mask_at + 2], "little")
        after = int.from_bytes(spliced[mask_at:mask_at + 2], "little")
        self.assertEqual(after ^ before, level_splice.BASIC_BIT_LEVEL)
        # Everything before the mask is untouched, and everything after the
        # inserted field is the frozen tail verbatim.
        self.assertEqual(spliced[:mask_at], frozen[:mask_at])
        self.assertTrue(spliced.endswith(
            frozen[mask_at + 2:][len(self.legacy.wstr_tag(
                self.placement.display_name)):]))

    def test_the_level_reads_back_off_the_bytes(self) -> None:
        for value in (1, 35, 71, 105, 255):
            with self.subTest(level=value):
                body = self._spliced(level=value)
                self.assertEqual(
                    level_splice.read_level(
                        self.legacy, body, self.placement.actor_identity),
                    value)

    def test_a_nameless_body_splices_too(self) -> None:
        """Bodies with no name exist in this project's census history
        (bg0001's P0/P91), and the splice position is name-length dependent,
        so the nameless shape is checked rather than assumed."""
        body = self._spliced(level=42, name="")
        self.assertEqual(
            level_splice.read_level(
                self.legacy, body, self.placement.actor_identity),
            42)

    def test_it_refuses_a_body_that_already_carries_a_level(self) -> None:
        """The double-field guard, checked against the real hostile encoder.

        Scene 14 ships a hostile subset through
        ``field_mobs.hostile_actor_entry``, which already splices bit 0x0002.
        Handing such a body to this module must refuse rather than write a
        second level field and a mask that claims one.
        """
        mob = hostile15.scene14_hostile_roster()[0]
        hostile = field_mobs.hostile_npc_attr(self.legacy, mob)
        # Same reader, lane B's bytes: the two modules agree on the field.
        self.assertEqual(
            level_splice.read_level(self.legacy, hostile, mob.actor_identity),
            mob.level)
        with self.assertRaises(level_splice.CensusLevelError):
            level_splice.with_level(
                self.legacy, hostile,
                actor_identity=mob.actor_identity,
                basic_name=mob.display_name,
                level=mob.level,
                current_hp=mob.max_hp,
                max_hp=mob.max_hp,
            )

    def test_it_refuses_a_level_that_is_not_a_plain_in_range_int(self) -> None:
        # 256 and 300 are inside the u16 the wire could carry and OUTSIDE
        # the mined domain (CONSTDATA_TH__MOBS tops out at n_LEVEL_MIN 255):
        # the ceiling is the data's, so a caller handing this an HP value
        # fails closed instead of shipping a four-digit level.
        for value in (0, -1, 256, 300, 0x10000, 7980, True, 3.0, "71", None):
            with self.subTest(level=value):
                with self.assertRaises(level_splice.CensusLevelError):
                    self._spliced(level=value)

    def test_it_refuses_when_the_caller_names_the_wrong_actor(self) -> None:
        """A wrong identity means the head does not match, which means the
        mask offset would be guessed.  Refuse rather than splice into the
        middle of somebody else's field."""
        with self.assertRaises(level_splice.CensusLevelError):
            level_splice.with_level(
                self.legacy, self._frozen(),
                actor_identity=self.placement.actor_identity + 1,
                basic_name=self.placement.display_name,
                level=71,
                current_hp=self.placement.max_hp,
                max_hp=self.placement.max_hp,
            )

    def test_it_refuses_when_the_name_does_not_match_the_body(self) -> None:
        for name in ("", "Not This Actor"):
            with self.subTest(name=name):
                with self.assertRaises(level_splice.CensusLevelError):
                    level_splice.with_level(
                        self.legacy, self._frozen(),
                        actor_identity=self.placement.actor_identity,
                        basic_name=name,
                        level=71,
                        current_hp=self.placement.max_hp,
                        max_hp=self.placement.max_hp,
                    )

    def test_it_refuses_a_body_that_is_not_the_frozen_shape(self) -> None:
        for body in (b"", b"\x0b\x01", self._frozen()[3:],
                     bytearray(self._frozen())):
            with self.subTest(body=repr(body)[:24]):
                with self.assertRaises(level_splice.CensusLevelError):
                    level_splice.with_level(
                        self.legacy, bytes(body) if type(body) is bytes else body,
                        actor_identity=self.placement.actor_identity,
                        basic_name=self.placement.display_name,
                        level=71,
                        current_hp=self.placement.max_hp,
                        max_hp=self.placement.max_hp,
                    )

    def test_the_composing_helper_equals_frozen_plus_splice(self) -> None:
        placement = self.placement
        composed = level_splice.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=SCENE_ID,
            scene_sequence=SCENE_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.identity.level,
        )
        self.assertEqual(
            composed, self._spliced(level=placement.identity.level))
        self.assertEqual(
            level_splice.read_level(
                self.legacy, composed, placement.actor_identity),
            placement.identity.level)

    def test_every_wired_scene_puts_its_mined_level_on_the_wire(self) -> None:
        """One check across every composer this round wired, so a scene
        cannot be wired in source and left unproven on the wire.

        Read OFF each scene's own ``generation.pc``.  ``bg0001`` (Port Royal)
        is deliberately NOT here: ``world_port_royal_identity`` has no mined
        level column at all, and a made-up number on the owner's screen would
        be worse than the ``LV 1`` it replaced -- that scene needs an RE
        answer first, not a default.  ``bg0002`` is not here either: its
        composer has its own call shape and its own level/level_max pair, so
        it is a separate, deliberate decision rather than a copy of this one.
        """
        import importlib

        for scene in WIRED_SCENES:
            module = importlib.import_module(
                "pirateforce_foundation.world_population_%s" % scene)
            scene_identity = importlib.import_module(
                "pirateforce_foundation.world_%s_identity" % scene)
            build = getattr(module, "build_%s_population" % scene)
            placements = list(scene_identity.shippable_placements())
            # Anchored on the scene's own first shippable placement: every
            # builder refuses an anchor it cannot order the roster around,
            # and a real placement is one by construction for every scene.
            first = placements[0]
            generation = build(
                self.legacy, (first.x, first.y, first.z),
                scene_id=module.SCENE_N_ID)
            attr_tag = self.legacy.u16tag(0x12, module.NPC_ATTR_ID)
            by_index = {p.placement_index: p for p in placements}
            with self.subTest(scene=scene):
                seen = set()
                for index in generation.placement_indices:
                    placement = by_index[index]
                    marker = (
                        attr_tag
                        + self.legacy.u8tag(0x0B, 1)
                        + self.legacy.qwordtag(
                            0x32, placement.actor_identity)
                    )
                    # Uniqueness first: reading a level out of the WRONG
                    # actor's body still compares equal wherever a scene's
                    # roster shares a level (79 of bg0015's 81 are 105), so
                    # the match has to be pinned before the value is read.
                    self.assertEqual(generation.pc.count(marker), 1)
                    at = generation.pc.index(marker) + len(attr_tag)
                    level = level_splice.read_level(
                        self.legacy, generation.pc[at:],
                        placement.actor_identity)
                    self.assertEqual(level, placement.identity.level)
                    seen.add(level)
                # Not "no level at all", and not one constant per scene:
                # both are shapes the pre-round census could have had.
                self.assertNotIn(None, seen)
                self.assertGreater(len(seen), 1)

    def test_bg0002_puts_its_own_mined_level_on_the_wire(self) -> None:
        """Scene 2's rows carry ``level``/``level_max`` themselves.

        What goes on the wire is ``level`` -- the mined ``MOBS.n_LEVEL_MIN``
        every sibling scene sends, and the one ``RE-173`` corrected for
        placement 63 -- never ``level_max``: a row with a range is a range
        the original server rolls per spawn, and nothing in this project has
        measured that roll.
        """
        census = world_population_bg0002
        placements = list(census.census_order((0.0, 0.0, 0.0)))
        first = placements[0]
        generation = census.build_bg0002_population(
            self.legacy, (first.x, first.y, first.z),
            scene_id=census.SCENE2_N_ID)
        attr_tag = self.legacy.u16tag(0x12, census.NPC_ATTR_ID)
        by_index = {p.placement_index: p for p in placements}
        ranged = 0
        for index in generation.placement_indices:
            placement = by_index[index]
            marker = (
                attr_tag
                + self.legacy.u8tag(0x0B, 1)
                + self.legacy.qwordtag(0x32, placement.actor_identity)
            )
            with self.subTest(placement=index):
                self.assertEqual(generation.pc.count(marker), 1)
                at = generation.pc.index(marker) + len(attr_tag)
                level = level_splice.read_level(
                    self.legacy, generation.pc[at:], placement.actor_identity)
                self.assertEqual(level, placement.level)
                if placement.level_max != placement.level:
                    ranged += 1
                    self.assertNotEqual(level, placement.level_max)
        # The distinction above is only meaningful if the scene has at
        # least one row whose range is not a point.
        self.assertGreater(ranged, 0)

    def test_bg0001_port_royal_puts_its_own_mined_level_on_the_wire(self) -> None:
        """Scene 1, the scene the owner logs into first.

        The round that added this module skipped scene 1 in its first draft,
        writing that ``world_port_royal_identity`` had "no mined level column
        at all".  pf-adversary did the join and refuted it: all 105 resolved
        templates carry a real ``MOBS.n_ID`` and every one of them has an
        ``n_LEVEL_MIN`` in the shipped table.  This test is what stops that
        claim from being re-made: it fails if scene 1 goes back to sending
        nothing.
        """
        census = world_population
        anchor = (self.legacy.V135_PLAYER_X, self.legacy.V135_PLAYER_Y,
                  self.legacy.V135_PLAYER_Z)
        placements = {p.placement_index: p
                      for p in census.census_order(self.legacy, anchor)}
        generation = census.build_world_population(
            self.legacy, anchor, len(placements), scene_id=census.SCENE_ID)
        attr_tag = self.legacy.u16tag(0x12, census.NPC_ATTR_ID)
        seen = set()
        for index in generation.indices:
            placement = placements[index]
            identity = world_port_royal_identity.resolve(placement.template_id)
            marker = (
                attr_tag
                + self.legacy.u8tag(0x0B, 1)
                + self.legacy.qwordtag(0x32, placement.actor_identity)
            )
            with self.subTest(placement=index):
                self.assertEqual(generation.pc.count(marker), 1)
                at = generation.pc.index(marker) + len(attr_tag)
                level = level_splice.read_level(
                    self.legacy, generation.pc[at:], placement.actor_identity)
                self.assertEqual(level, identity.level)
                seen.add(level)
        self.assertNotIn(None, seen)
        self.assertGreater(len(seen), 1)

    def test_every_live_census_source_either_sends_a_level_or_says_why(
        self,
    ) -> None:
        """The omission catcher (see CENSUS_SOURCE_COMPOSERS' own comment).

        The glob test below cannot see a composer that was never wired,
        because a file that does not mention this module is indistinguishable
        from a file nobody has written.  This one starts from the live
        dispatch table instead, so a NEW census source ships red rather than
        shipping ``LV 1``.
        """
        live = set(world_scene_travel.CENSUS_SOURCES.values())
        self.assertEqual(
            live, set(CENSUS_SOURCE_COMPOSERS),
            "a live census source has no composer named here: add it (and "
            "wire it), or record it in CENSUS_SOURCES_WITHOUT_A_MINED_LEVEL")
        for source, module_name in sorted(CENSUS_SOURCE_COMPOSERS.items()):
            with self.subTest(source=source):
                body = (ROOT / "src/pirateforce_foundation"
                        / ("%s.py" % module_name)).read_text(encoding="utf-8")
                wired = "world_census_level.leveled_npc_attr" in body
                excused = source in CENSUS_SOURCES_WITHOUT_A_MINED_LEVEL
                self.assertTrue(
                    wired or excused,
                    "%s composes a live census and neither sends a level nor "
                    "has a written reason not to" % source)
                self.assertFalse(
                    wired and excused,
                    "%s is both wired and excused; one of the two is stale"
                    % source)

    def test_the_level_tag_is_the_one_re117_pinned(self) -> None:
        """Pinned as a literal, and checked on the wire as a literal.

        pf-adversary mutated ``LEVEL_TAG`` to 0x14 and every ..._ON_THE_WIRE
        test still passed, because ``read_level`` reads the same constant
        that wrote the field.  A literal on both sides is the only thing that
        catches that.  0x12 is the u16 tag RE-117 measured at the level
        writer (0x00465736..0x0046574A), and it is the same tag the frozen
        serializer already uses for its own u16 fields.
        """
        self.assertEqual(level_splice.LEVEL_TAG, 0x12)
        self.assertEqual(level_splice.BASIC_BIT_LEVEL, 0x0002)
        self.assertEqual(level_splice.LEVEL_SPLICE_BYTES, 3)
        body = self._spliced(level=77)
        mask_at = level_splice.basic_mask_offset(
            self.legacy, body, self.placement.actor_identity)
        at = mask_at + 2 + len(self.legacy.wstr_tag(
            self.placement.display_name))
        self.assertEqual(body[at], 0x12)
        self.assertEqual(
            int.from_bytes(body[at + 1:at + 3], "little"), 77)

    def test_it_refuses_when_the_hp_pair_is_not_where_the_mask_says(
        self,
    ) -> None:
        """The independent position check, driven directly.

        The guard this replaced inverted the splice with the same offset the
        splice used, so it reproduced the baseline for any offset and
        accepted a level written into the middle of the HP field.  This one
        is anchored on bytes the caller states separately, so a body whose HP
        pair is not where the ascending mask order puts it is refused.
        """
        placement = self.placement
        for wrong_hp in (placement.max_hp + 1, 0, 1):
            with self.subTest(current_hp=wrong_hp):
                with self.assertRaises(level_splice.CensusLevelError):
                    level_splice.with_level(
                        self.legacy, self._frozen(),
                        actor_identity=placement.actor_identity,
                        basic_name=placement.display_name,
                        level=71,
                        current_hp=wrong_hp,
                        max_hp=placement.max_hp,
                    )
        # And a nameless body, the shape the old guard could not refuse at
        # all: 25 of bg0004's 109 shipped placements are nameless.
        with self.assertRaises(level_splice.CensusLevelError):
            level_splice.with_level(
                self.legacy, self._frozen(name=""),
                actor_identity=placement.actor_identity,
                basic_name="",
                level=71,
                current_hp=placement.max_hp + 1,
                max_hp=placement.max_hp,
            )

    def test_the_wired_composers_are_exactly_the_ones_named(self) -> None:
        """The list above is not decoration: it is what says which scenes a
        player warping across maps still sees ``LV 1`` in.  A composer wired
        without being added here goes red rather than unnoticed."""
        source = (ROOT / "src/pirateforce_foundation").glob(
            "world_population*.py")
        wired = sorted(
            path.name for path in source
            if "world_census_level" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(
            tuple(wired), WIRED_COMPOSERS,
            "a census composer was wired (or unwired) without saying so here")

    def test_this_module_never_invents_a_level(self) -> None:
        """No default anywhere in the public surface: a scene with no mined
        level column (bg0001 today) must fail to call this, not receive a
        made-up number."""
        import inspect

        for func in (level_splice.with_level, level_splice.leveled_npc_attr):
            with self.subTest(func=func.__name__):
                parameter = inspect.signature(func).parameters["level"]
                self.assertIs(parameter.default, inspect.Parameter.empty)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
