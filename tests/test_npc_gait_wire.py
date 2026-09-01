"""Watch the decoded walk-gait seam and the Foundation population's silence about it.

`movement/npc_locomotion_presentation` claims that gait selection is accounted
for by the decoded `MOBS.n_SPEED_WALK` value carried in `BasicAttr` bit
`0x0040` (float field `+0x54`).  The runtime record behind that claim is the
legacy V87/V89/V92 scenario runner, whose accepted rule is stronger than "the
field exists": V85 sent the value only in its bootstrap snapshot and the same
actor visibly changed from a walk to a run, so the proven rule is that the
value must be present in *every* generation.

Nothing watched any of that.  `tests/test_population.py` pins nearest-20
membership and byte-exact frames but never mentions speed, and no test in the
tree referenced `movement_speed` at all.

This module pins three separate things:

1. the serializer seam itself, byte-exactly and by hand (never by calling the
   same helper back through the same path);
2. the frozen provenance constants and the "speed in every generation" rule
   as the legacy scenario runner actually emits it;
3. the **negative** that the Foundation population path never sets the bit, so
   that adding gait to the Foundation server cannot happen silently without
   this test and the coverage matrix row disagreeing.

Nonclaims: this module does not claim that a Foundation client walks, that 150
is correct for any template other than the reported ones, or that the field is
sufficient for locomotion.  It watches wire bytes and source seams only.
"""

import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Overridable so a mutation harness can point the suite at a modified copy
# without relocating this file (relocating it would break ROOT).
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SRC_ROOT = ROOT / "src"

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    build_port_royal_initial_population,
    build_port_royal_membership_transition,
)


# BasicAttr mask emitted by an NPCAttr with a visual preset and no name:
# 0x0004 | 0x0008 (HP pair) | 0x0100 | 0x0200 (scene id / sequence).
PLAIN_BASIC_MASK = 0x030C
# The same wire once the decoded walk-speed float is requested.
GAIT_BASIC_MASK = PLAIN_BASIC_MASK | 0x0040
PROVEN_WALK_SPEED = 150.0
V89_WALKER_IDENTITIES = (0x3101, 0x3102, 0x3103)
MOVEMENT_SPEED_TOKEN = re.compile(r"\bmovement_speed\b")


def npc_attr_prefix(actor_identity: int, basic_mask: int) -> bytes:
    """Hand-built NPCAttr prefix: tag0B count, tag32 identity, tag12 mask.

    Built with `struct` on purpose.  Using the legacy tag helpers here would
    let a mutation in those helpers cancel itself out of every assertion.
    """
    return (
        bytes([0x0B, 0x01])
        + bytes([0x32])
        + struct.pack("<Q", actor_identity)
        + bytes([0x12])
        + struct.pack("<H", basic_mask)
    )


def count_gait_carriers(blob: bytes, identities) -> tuple[int, ...]:
    """How many times each identity appears with the walk-speed bit set."""
    return tuple(blob.count(npc_attr_prefix(aid, GAIT_BASIC_MASK)) for aid in identities)


def count_plain_carriers(blob: bytes, identities) -> tuple[int, ...]:
    return tuple(blob.count(npc_attr_prefix(aid, PLAIN_BASIC_MASK)) for aid in identities)


def modules_requesting_movement_speed(root: Path) -> list[str]:
    hits = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if MOVEMENT_SPEED_TOKEN.search(path.read_text(encoding="utf-8")):
            hits.append(path.name)
    return hits


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)


class NpcGaitSeamTests(_LegacyCase):
    """The serializer seam: what exactly does asking for a speed change?"""

    def _preset(self):
        return "P_MALE_002_000_SP1"

    def test_walk_speed_sets_exactly_bit_0x0040_in_the_basic_mask(self):
        plain = self.legacy.make_npc_attr(1, 0x2001, 1, 0, self._preset())
        gait = self.legacy.make_npc_attr(
            1, 0x2001, 1, 0, self._preset(), movement_speed=PROVEN_WALK_SPEED,
        )
        plain_mask = struct.unpack_from("<H", plain, 12)[0]
        gait_mask = struct.unpack_from("<H", gait, 12)[0]
        self.assertEqual(plain[11], 0x12)
        self.assertEqual(gait[11], 0x12)
        self.assertEqual(plain_mask, PLAIN_BASIC_MASK)
        self.assertEqual(gait_mask, GAIT_BASIC_MASK)
        self.assertEqual(plain_mask ^ gait_mask, 0x0040)

    def test_speed_float_is_written_immediately_after_the_hp_pair(self):
        preset = self._preset()
        encoded = preset.encode("utf-16le")
        expected = (
            bytes([0x0B, 0x01])
            + bytes([0x32]) + struct.pack("<Q", 0x2001)
            + bytes([0x12]) + struct.pack("<H", GAIT_BASIC_MASK)
            + bytes([0x14]) + struct.pack("<I", 100)
            + bytes([0x14]) + struct.pack("<I", 100)
            + bytes([0x2A]) + struct.pack("<f", PROVEN_WALK_SPEED)
            + bytes([0x12]) + struct.pack("<H", 1)
            + bytes([0x32]) + struct.pack("<Q", 0)
            + bytes([0x0B, 0x05])
            + bytes([0x12]) + struct.pack("<H", 1)
            + b"\x48" + struct.pack("<I", len(encoded)) + encoded
        )
        actual = self.legacy.make_npc_attr(
            1, 0x2001, 1, 0, preset, movement_speed=PROVEN_WALK_SPEED,
        )
        self.assertEqual(actual, expected)

    def test_adding_speed_inserts_exactly_five_bytes_and_changes_nothing_else(self):
        preset = self._preset()
        plain = self.legacy.make_npc_attr(1, 0x2001, 1, 0, preset)
        gait = self.legacy.make_npc_attr(
            1, 0x2001, 1, 0, preset, movement_speed=PROVEN_WALK_SPEED,
        )
        self.assertEqual(len(gait) - len(plain), 5)
        # Everything up to the mask value is identical.
        self.assertEqual(plain[:12], gait[:12])
        # The insertion point is right after the two HP tags (1 + 4 each).
        cut = 14 + 5 + 5
        self.assertEqual(plain[14:cut], gait[14:cut])
        self.assertEqual(
            gait[cut:cut + 5], bytes([0x2A]) + struct.pack("<f", PROVEN_WALK_SPEED),
        )
        self.assertEqual(plain[cut:], gait[cut + 5:])

    def test_speed_is_serialized_as_float32_not_float64(self):
        value = 150.1
        gait = self.legacy.make_npc_attr(
            1, 0x2001, 1, 0, self._preset(), movement_speed=value,
        )
        cut = 14 + 10
        self.assertEqual(gait[cut:cut + 5], bytes([0x2A]) + struct.pack("<f", value))
        self.assertNotIn(struct.pack("<d", value), gait)
        # The wire keeps the float32 rounding, not the Python double.
        self.assertNotEqual(struct.unpack("<f", gait[cut + 1:cut + 5])[0], value)

    def test_zero_speed_is_still_serialized_because_only_none_means_absent(self):
        zero = self.legacy.make_npc_attr(
            1, 0x2001, 1, 0, self._preset(), movement_speed=0.0,
        )
        absent = self.legacy.make_npc_attr(1, 0x2001, 1, 0, self._preset())
        self.assertEqual(struct.unpack_from("<H", zero, 12)[0], GAIT_BASIC_MASK)
        self.assertEqual(struct.unpack_from("<H", absent, 12)[0], PLAIN_BASIC_MASK)
        self.assertEqual(len(zero) - len(absent), 5)


class FrozenGaitProvenanceTests(_LegacyCase):
    """The reported walkers and the 'speed in every generation' rule."""

    def test_frozen_walk_speed_constants_are_the_reported_value(self):
        self.assertEqual(self.legacy.V73_WALK_SPEED, PROVEN_WALK_SPEED)
        self.assertEqual(self.legacy.V89_WALK_SPEED, PROVEN_WALK_SPEED)

    def test_frozen_mover_sets_match_the_reported_experiments(self):
        self.assertEqual(self.legacy.V73_MOVERS, (5, 84, 89, 50, 85, 144))
        self.assertEqual(self.legacy.V89_TEST_INDICES, (5, 144, 50))
        known = {row[0] for row in self.legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
        self.assertTrue(set(self.legacy.V73_MOVERS) <= known)
        self.assertTrue(set(self.legacy.V89_TEST_INDICES) <= known)

    def test_every_v89_movement_generation_carries_speed_for_all_walkers(self):
        sequence = self.legacy.make_v89_ground_sequence(0.0, 0.0, 0.0)
        self.assertGreaterEqual(len(sequence), 2)
        for label, pc, _frame, _delay in sequence:
            with self.subTest(label=label[:32]):
                self.assertEqual(
                    count_gait_carriers(pc, V89_WALKER_IDENTITIES), (1, 1, 1),
                )
                self.assertEqual(
                    count_plain_carriers(pc, V89_WALKER_IDENTITIES), (0, 0, 0),
                )

    def test_the_v89_baseline_generation_carries_speed_too(self):
        pc, _frame = self.legacy.make_v89_ground_state(0.0, 0.0, 0.0)
        self.assertEqual(count_gait_carriers(pc, V89_WALKER_IDENTITIES), (1, 1, 1))
        self.assertEqual(count_plain_carriers(pc, V89_WALKER_IDENTITIES), (0, 0, 0))


class FoundationPopulationEmitsNoGaitTests(_LegacyCase):
    """The negative: the Foundation POPULATION (census) path never asks for a
    speed -- narrowed this round, not weakened, see below.

    This is deliberately an assertion about absence.  The coverage matrix row
    is graded on legacy-scenario-runner runtime evidence, and the Foundation
    server does not reproduce it.  If someone wires gait into the Foundation
    population, these tests fail and the matrix row must be revisited in the
    same change.

    NARROWED 2026-08-28 (COO-DECISION 2026-08-28T01:46+07:00, lane B).
    ``field_mobs.hostile_npc_attr`` now always requests ``movement_speed``
    (the mined MOBS ``n_SPEED_WALK`` for that exact monster, not a guess --
    see that function's own docstring), and ``mob_death.py`` /
    ``mob_diag_multi_object.py`` widen the same field consistently into
    their own hand-written and D3-diagnostic NPCAttr composers so that EVERY
    generation of a field-mob body (live, damaged, dying, dead) carries it --
    which is exactly the "must be present in every generation" rule this
    module's own ``FrozenGaitProvenanceTests`` pins from the V85 walk-to-run
    regression, not a violation of it.  This is a DIFFERENT identity space
    from the Foundation POPULATION (ambient) census this class's two byte
    tests below cover (``population.py`` / ``world_population.py``, neither
    touched this round) -- so the two byte-level tests below are unchanged
    and still pass, and only the blanket whole-``src/``-tree source sweep
    below is narrowed to name its known, now-legitimate exceptions
    rather than silently going green for the wrong reason.

    WIDENED round jqxe6v: ``field_mob_hostile_bg0015.py`` calls
    ``field_mobs.hostile_actor_entry`` for the same reason ``field_mobs.py``
    itself is already named here -- one more scene's hostile composer, same
    mined ``n_SPEED_WALK`` field, not a new gait mechanism.
    """

    KNOWN_GAIT_REQUESTING_MODULES = (
        "field_mob_hostile_bg0015.py", "field_mobs.py", "mob_death.py",
        "mob_diag_multi_object.py",
    )

    def test_initial_population_carries_no_walk_speed_field(self):
        transition = build_port_royal_initial_population(self.legacy, (0.0, 0.0, 0.0))
        identities = transition.current_actor_identities
        self.assertEqual(len(identities), AUTHORITATIVE_COUNT)
        self.assertEqual(count_gait_carriers(transition.pc, identities), (0,) * 20)
        self.assertEqual(count_plain_carriers(transition.pc, identities), (1,) * 20)
        self.assertEqual(count_gait_carriers(transition.frame, identities), (0,) * 20)

    def test_transition_population_carries_no_walk_speed_field(self):
        first = build_port_royal_initial_population(self.legacy, (0.0, 0.0, 0.0))
        transition = build_port_royal_membership_transition(
            self.legacy, first.current_indices, (500.0, 0.0, 0.0),
        )
        identities = transition.current_actor_identities
        self.assertEqual(len(identities), AUTHORITATIVE_COUNT)
        self.assertEqual(count_gait_carriers(transition.pc, identities), (0,) * 20)
        self.assertEqual(count_plain_carriers(transition.pc, identities), (1,) * 20)

    def test_no_foundation_module_requests_a_movement_speed(self):
        # See this class's own docstring, "NARROWED 2026-08-28": the three
        # named exceptions are lane B's own hostile field-mob composers, not
        # the Foundation POPULATION (census) path this test is actually
        # about.  Anything else showing up here is still a real find.
        hits = modules_requesting_movement_speed(SRC_ROOT)
        self.assertEqual(
            sorted(set(hits) - set(self.KNOWN_GAIT_REQUESTING_MODULES)), [],
        )
        self.assertEqual(
            sorted(set(self.KNOWN_GAIT_REQUESTING_MODULES) - set(hits)), [],
            "a named exception no longer requests movement_speed -- narrow "
            "KNOWN_GAIT_REQUESTING_MODULES back down",
        )

    def test_the_frame_detector_would_notice_a_generation_that_did_carry_speed(self):
        """Kept in the suite so the two absence assertions cannot go vacuous."""
        entries = []
        for lane, identity in enumerate(V89_WALKER_IDENTITIES):
            npc_attr = self.legacy.make_npc_attr(
                1, identity, 1, 0, "P_MALE_002_000_SP1",
                movement_speed=PROVEN_WALK_SPEED,
            )
            entries.append(self.legacy.make_remote_actor_entry(
                4, identity, [(self.legacy.NPC_ATTR, npc_attr)],
            ))
        pc, _frame = self.legacy.make_runtime_remote_actors(entries)
        self.assertEqual(count_gait_carriers(pc, V89_WALKER_IDENTITIES), (1, 1, 1))
        self.assertEqual(count_plain_carriers(pc, V89_WALKER_IDENTITIES), (0, 0, 0))

    def test_the_source_scanner_would_notice_a_module_that_requested_speed(self):
        """Same idea for the source guard: prove it bites before trusting it."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "clean.py").write_text("SPEED = 150.0\n", encoding="utf-8")
            self.assertEqual(modules_requesting_movement_speed(root), [])
            (root / "gait.py").write_text(
                "make_npc_attr(1, 2, movement_speed=150.0)\n", encoding="utf-8",
            )
            self.assertEqual(modules_requesting_movement_speed(root), ["gait.py"])
            # A word that merely contains the token must not trip the scanner.
            (root / "clean.py").write_text("no_movement_speeds = 1\n", encoding="utf-8")
            self.assertEqual(modules_requesting_movement_speed(root), ["gait.py"])


if __name__ == "__main__":
    unittest.main()
