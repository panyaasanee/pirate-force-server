"""LANE-DB rounds `o5zblc` + `cgnzsd`: the HP pair the client displays.

ROUND `cgnzsd` REWROTE THE GUARD after `pf-adversary` found the first draft
INVERTED.  Three findings drove it and each has its own test class below:
D1 the guard passed `0/0`, the value this repository has attended-measured
as the symptom (`ZeroIsTheSymptomNotAnHonestValueTests`); D2 the trigger was
x=9's PRESENCE, which would refuse every login this server sends
(`TheTriggerIsTheArmedValueNotThePresenceTests`); D3 `-1/1` was attributed
to the frame layer when it is a constructor fact
(`TheTwoLayersAreNamedSeparatelyTests`).  D4 asked what this module adds
over the fence that already ships, and the answer is measured rather than
argued in `TheIncumbentFenceIsOnePredicateShortTests`.

The owner's attended observation this lane was pointed at (`GT-218`'s
family, recorded in the bridge repository which a clone of THIS repository
cannot open, so it is cited by ticket id and not by path): the self panel
showed HP **-1/1** at sea and STILL showed HP -1 after landing.  Everything
this file asserts about the mechanism is quoted from `gm/attr_wire.py` and
`persistence_attr_compose.py`, both of which ship here.

WHAT THIS FILE PROVES (wire/DB layer only -- nothing here is on a screen):

1. The three field indices this module reasons about are DERIVED from
   `gm/attr_wire.FIELDS` by name, not typed.  A rename or a removal in that
   table (LANE-GM's zone, not ours) makes the import raise rather than let
   this module pin a stale number.
2. The alternate pair's client construction default really is the corpus
   copy in `persistence_attr_compose`, and it really prints as -1/1.
3. The refusal has teeth: a block carrying the selector row with no honest
   alternate pair is refused, and deleting either half of the guard makes a
   test here go red.
4. A block that does not carry the selector is NOT this module's business
   and passes -- the guard is narrow on purpose.
5. `live_hp_pair_report` reads a real migrated store through LANE-DB's own
   `read_typed_attributes`, writes nothing, and reports an unseeded HP as
   `None` rather than 0.
6. Neither file names a scene id in a sentence about the selector, and
   neither claims any scene takes the alternate pair.
   `SELECTOR_NOTE_R301` says the mapping is not decoded; a sentence-scoped
   detector, pinned against the five sentences that defeated its previous
   version, scans both files for the overclaim.

WHAT THIS FILE DOES NOT PROVE.  It does not evaluate `0x430E10` -- nothing
in this repository can.  It does not claim the alternate branch is what the
owner hit; it claims only that IF that branch is taken and the server has
set nothing, the HUD shows -1/1.  It has not run against the canonical
database.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402,E501
from pirateforce_foundation import persistence_hp_pair_selector as sel  # noqa: E402,E501
from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.gm import login_mask  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
SRC = ROOT / "src" / "pirateforce_foundation"
MODULE_FILE = SRC / "persistence_hp_pair_selector.py"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class TheIndicesComeFromTheWireTableTests(unittest.TestCase):
    def test_primary_pair_is_the_rows_named_hp_current_and_hp_max(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(
            sel.PRIMARY_PAIR, (by_name["hp_current"], by_name["hp_max"])
        )

    def test_alternate_pair_is_the_rows_named_alt_hp(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(
            sel.ALTERNATE_PAIR,
            (by_name["alt_hp_current"], by_name["alt_hp_max"]),
        )

    def test_selector_is_the_row_named_category_5C(self):
        by_name = {row[6]: row[0] for row in attr_wire.FIELDS}
        self.assertEqual(sel.SELECTOR_FIELD, by_name["category_5C"])

    def test_the_three_groups_are_disjoint(self):
        seen = set(sel.PRIMARY_PAIR) | set(sel.ALTERNATE_PAIR)
        self.assertEqual(len(seen), 4)
        self.assertNotIn(sel.SELECTOR_FIELD, seen)

    def test_a_missing_name_raises_rather_than_defaulting(self):
        with self.assertRaises(sel.HpPairError):
            sel._x_named("a_row_gm_never_shipped")

    def test_the_wire_table_note_still_ties_x52_to_the_selector(self):
        """Derived from the shipped note, not from memory: if LANE-GM ever
        detaches x=52 from `0x430E10(x9)`, this module's whole premise is
        stale and this test says so."""
        note = {row[0]: row[8] for row in attr_wire.FIELDS}
        self.assertIn("0x430E10", note[sel.ALTERNATE_PAIR[0]])
        self.assertIn("0x430E10", note[sel.SELECTOR_FIELD])


class TheMinusOneIsTheCorpusValueTests(unittest.TestCase):
    def test_defaults_are_the_compose_corpus_copy(self):
        self.assertEqual(
            sel.ALTERNATE_CONSTRUCTION_DEFAULTS,
            (
                compose.CLIENT_CONSTRUCTION_DEFAULTS[sel.ALTERNATE_PAIR[0]].value,
                compose.CLIENT_CONSTRUCTION_DEFAULTS[sel.ALTERNATE_PAIR[1]].value,
            ),
        )

    def test_the_current_default_prints_as_minus_one(self):
        self.assertEqual(
            sel.as_signed_u32(sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0]), -1
        )

    def test_the_max_default_prints_as_one(self):
        self.assertEqual(
            sel.as_signed_u32(sel.ALTERNATE_CONSTRUCTION_DEFAULTS[1]), 1
        )

    def test_signed_conversion_is_a_conversion_not_a_clamp(self):
        self.assertEqual(sel.as_signed_u32(0), 0)
        self.assertEqual(sel.as_signed_u32(100), 100)
        self.assertEqual(sel.as_signed_u32(0x7FFFFFFF), 0x7FFFFFFF)
        self.assertEqual(sel.as_signed_u32(0x80000000), -(1 << 31))

    def test_non_u32_values_raise(self):
        for bad in (None, "100", 1.5, True, -1, 1 << 32):
            with self.subTest(bad=bad):
                with self.assertRaises(sel.HpPairError):
                    sel.as_signed_u32(bad)


class TheGapsNameEveryDishonestRowTests(unittest.TestCase):
    def test_an_empty_block_gaps_both_rows_as_absent(self):
        gaps = sel.alternate_pair_gaps({})
        self.assertEqual([g.x for g in gaps], list(sel.ALTERNATE_PAIR))
        self.assertEqual(
            {g.reason for g in gaps}, {sel.REASON_ABSENT_READS_ZERO}
        )

    def test_the_construction_default_is_a_gap_not_a_value(self):
        values = {
            sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
            sel.ALTERNATE_PAIR[1]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[1],
        }
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual(
            {g.reason for g in gaps}, {sel.REASON_CONSTRUCTION_DEFAULT}
        )

    def test_a_negative_printing_value_is_a_gap(self):
        values = {
            sel.ALTERNATE_PAIR[0]: 0xFFFFFFFE,
            sel.ALTERNATE_PAIR[1]: 100,
        }
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual([g.x for g in gaps], [sel.ALTERNATE_PAIR[0]])
        self.assertEqual(gaps[0].reason, sel.REASON_NEGATIVE)

    def test_a_non_integer_is_a_gap_not_a_crash(self):
        values = {sel.ALTERNATE_PAIR[0]: "100", sel.ALTERNATE_PAIR[1]: 100}
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual([g.reason for g in gaps], [sel.REASON_NOT_A_U32])

    def test_an_honest_pair_has_no_gaps(self):
        values = {sel.ALTERNATE_PAIR[0]: 87, sel.ALTERNATE_PAIR[1]: 100}
        self.assertEqual(sel.alternate_pair_gaps(values), ())

    def test_every_gap_carries_the_wire_table_name(self):
        for gap in sel.alternate_pair_gaps({}):
            with self.subTest(x=gap.x):
                self.assertEqual(gap.field_name, sel._field_name(gap.x))


class TheGuardHasTeethTests(unittest.TestCase):
    def test_armed_selector_without_any_pair_is_refused(self):
        with self.assertRaises(sel.HpPairError) as caught:
            sel.guard_alternate_pair({sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE})
        message = str(caught.exception)
        self.assertIn(f"x={sel.SELECTOR_FIELD}", message)
        self.assertIn(sel.HP_PAIR_REFUSED_CONSOLE_TOKEN, message)

    def test_armed_selector_with_the_construction_default_is_refused(self):
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
            sel.ALTERNATE_PAIR[1]: 100,
        }
        with self.assertRaises(sel.HpPairError):
            sel.guard_alternate_pair(values)

    def test_armed_selector_with_an_honest_pair_passes(self):
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 87,
            sel.ALTERNATE_PAIR[1]: 100,
        }
        self.assertIsNone(sel.guard_alternate_pair(values))

    def test_current_above_max_is_refused_even_though_both_rows_are_present(self):
        """Two individually honest numbers can still be an impossible bar."""
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 200,
            sel.ALTERNATE_PAIR[1]: 100,
        }
        with self.assertRaises(sel.HpPairError) as caught:
            sel.guard_alternate_pair(values)
        self.assertIn(sel.REASON_CURRENT_ABOVE_MAX, str(caught.exception))

    def test_a_block_without_the_selector_is_not_this_guards_business(self):
        """The narrowness is the property: this module must not become a
        second, quieter permission gate over blocks that never touch x=9."""
        self.assertIsNone(
            sel.guard_alternate_pair(
                {sel.PRIMARY_PAIR[0]: 100, sel.PRIMARY_PAIR[1]: 100}
            )
        )
        self.assertIsNone(sel.guard_alternate_pair({}))

    def test_every_reason_string_is_reachable_from_a_hand_built_block(self):
        """Each block below must produce the reason it is named for.

        THE NAME IS DELIBERATELY NARROW (pf-adversary `cgnzsd`, D3).  Only
        `REASON_ABSENT_READS_ZERO` is reachable from a block
        `make_update_attr_frame` can admit -- the other five need a block
        carrying x=52/x=53, which no login shape does.  This proves the
        branches work, not that production can take them."""
        armed = sel.SELECTOR_ARMED_VALUE
        cases = {
            sel.REASON_ABSENT_READS_ZERO: {sel.SELECTOR_FIELD: armed},
            sel.REASON_ZERO: {
                sel.SELECTOR_FIELD: armed,
                sel.ALTERNATE_PAIR[0]: 0,
                sel.ALTERNATE_PAIR[1]: 100,
            },
            sel.REASON_CONSTRUCTION_DEFAULT: {
                sel.SELECTOR_FIELD: armed,
                sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
                sel.ALTERNATE_PAIR[1]: 100,
            },
            sel.REASON_NEGATIVE: {
                sel.SELECTOR_FIELD: armed,
                sel.ALTERNATE_PAIR[0]: 0xFFFFFF00,
                sel.ALTERNATE_PAIR[1]: 100,
            },
            sel.REASON_NOT_A_U32: {
                sel.SELECTOR_FIELD: armed,
                sel.ALTERNATE_PAIR[0]: "87",
                sel.ALTERNATE_PAIR[1]: 100,
            },
            sel.REASON_CURRENT_ABOVE_MAX: {
                sel.SELECTOR_FIELD: armed,
                sel.ALTERNATE_PAIR[0]: 200,
                sel.ALTERNATE_PAIR[1]: 100,
            },
        }
        self.assertEqual(set(cases), set(sel.ALL_REASONS))
        for reason, values in cases.items():
            with self.subTest(reason=reason):
                reasons = [g.reason for g in sel.alternate_pair_gaps(values)]
                self.assertIn(reason, reasons)

    def test_a_bool_is_not_accepted_as_the_number_one(self):
        """`True == 1` and 1 is x=53's construction default, so a bool must
        be reported as a type gap, never quietly as the default."""
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 87,
            sel.ALTERNATE_PAIR[1]: True,
        }
        reasons = [g.reason for g in sel.alternate_pair_gaps(values)]
        self.assertEqual(reasons, [sel.REASON_NOT_A_U32])

    def test_a_float_row_is_a_type_gap_not_a_silent_pass(self):
        """pf-adversary D10: floats walked through the first draft."""
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 87.0,
            sel.ALTERNATE_PAIR[1]: 100.0,
        }
        with self.assertRaises(sel.HpPairError):
            sel.guard_alternate_pair(values)

    def test_a_float_selector_key_still_arms_the_guard(self):
        """`{9.0: 8}` resolves by numeric equality in a dict, so the guard
        must not be escapable by handing it float keys.  Pinned rather than
        assumed."""
        values = {float(sel.SELECTOR_FIELD): sel.SELECTOR_ARMED_VALUE}
        self.assertTrue(sel.selector_is_armed(values))
        with self.assertRaises(sel.HpPairError):
            sel.guard_alternate_pair(values)


class TheMutantsPfAdversaryFoundAliveTests(unittest.TestCase):
    """Round `cgnzsd`'s second pf-adversary pass (D6) applied 29 mutants and
    four survived the whole suite.  One test each, named for its mutant."""

    def test_full_hp_is_honest(self):
        """Mutant: `current > maximum` -> `>=`.  It survived because nothing
        exercised `current == max`, the commonest honest HP state there is."""
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 87,
            sel.ALTERNATE_PAIR[1]: 87,
        }
        self.assertEqual(sel.alternate_pair_gaps(values), ())
        self.assertIsNone(sel.guard_alternate_pair(values))

    def test_the_supplied_flag_follows_the_server_owned_set(self):
        """Mutant: `alternate_pair_supplied=bool(...)` -> `=False`.  The
        docstring claims the flag is DERIVED; this holds it to that."""

        class _Store:
            def read_typed_attributes(self, character_id):
                return {"hp_current": 10, "hp_max": 20}

        original = compose.SERVER_OWNED_FIELDS
        try:
            self.assertFalse(sel.live_hp_pair_report(_Store(), 1).alternate_pair_supplied)
            compose.SERVER_OWNED_FIELDS = frozenset(
                set(original) | set(sel.ALTERNATE_PAIR)
            )
            self.assertTrue(sel.live_hp_pair_report(_Store(), 1).alternate_pair_supplied)
        finally:
            compose.SERVER_OWNED_FIELDS = original
        self.assertFalse(sel.live_hp_pair_report(_Store(), 1).alternate_pair_supplied)

    def test_the_console_token_literal_is_pinned(self):
        """Mutant: rename the token.  A log-grepper watching for this exact
        string breaks silently when it changes, so the string is the
        contract, not merely 'different from LANE-GM's'."""
        self.assertEqual(sel.HP_PAIR_REFUSED_CONSOLE_TOKEN, "DB_HP_PAIR_DISHONEST")

    def test_an_unknown_row_raises_instead_of_inventing_a_name(self):
        """Mutant: `_field_name`'s raise -> `return f"x{x}"`.  It survived
        because the only test comparing names compared the function with
        itself.  `attr_wire.FIELDS` is 0-based and dense, so a row index one
        past the end is unknown by construction."""
        unknown = max(row[0] for row in attr_wire.FIELDS) + 1
        with self.assertRaises(sel.HpPairError):
            sel._field_name(unknown)

    def test_the_field_names_match_the_wire_table_not_this_module(self):
        """The tautology the mutant hid behind: compare against
        `attr_wire.FIELDS` directly, never against `_field_name` itself."""
        by_x = {row[0]: row[6] for row in attr_wire.FIELDS}
        gaps = sel.alternate_pair_gaps(
            {sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE}
        )
        self.assertEqual(
            [g.field_name for g in gaps], [by_x[x] for x in sel.ALTERNATE_PAIR]
        )


class ZeroIsTheSymptomNotAnHonestValueTests(unittest.TestCase):
    """pf-adversary D1.  `gm/attr_wire.py:105` (`RE-222` Q0) and
    `_refuse_selector_change`'s own docstring both say an unset mask bit is a
    ZERO on this client and that a frame flipping the selector hands the HUD
    `0/0`.  A guard against that symptom that PASSES `0/0` is not a weak
    guard, it is the wrong one."""

    def test_zero_zero_is_refused(self):
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 0,
            sel.ALTERNATE_PAIR[1]: 0,
        }
        with self.assertRaises(sel.HpPairError):
            sel.guard_alternate_pair(values)

    def test_both_rows_are_named_and_both_carry_the_frame_layer_reason(self):
        values = {
            sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
            sel.ALTERNATE_PAIR[0]: 0,
            sel.ALTERNATE_PAIR[1]: 0,
        }
        gaps = sel.alternate_pair_gaps(values)
        self.assertEqual([g.x for g in gaps], list(sel.ALTERNATE_PAIR))
        self.assertEqual(
            {g.reason for g in gaps}, {sel.REASON_ZERO}
        )

    def test_one_zero_row_is_enough_to_refuse(self):
        for index, x in enumerate(sel.ALTERNATE_PAIR):
            with self.subTest(x=x):
                values = {
                    sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
                    sel.ALTERNATE_PAIR[0]: 87,
                    sel.ALTERNATE_PAIR[1]: 100,
                }
                values[x] = 0
                with self.assertRaises(sel.HpPairError):
                    sel.guard_alternate_pair(values)

    def test_the_repository_still_says_an_unset_bit_reads_as_zero(self):
        """If LANE-GM ever retracts that sentence, this guard's premise is
        gone and this test says so instead of the guard living on."""
        wire_text = (SRC / "gm" / "attr_wire.py").read_text(encoding="utf-8")
        # Substrings that fit on ONE source line, so LANE-GM re-wrapping a
        # paragraph does not turn LANE-DB's suite red with a message naming
        # LANE-DB (pf-adversary `cgnzsd`, D9).
        self.assertIn("a ZERO on the client", wire_text)
        self.assertIn("HP `0/0`", wire_text)


class TheTriggerIsTheArmedValueNotThePresenceTests(unittest.TestCase):
    """pf-adversary D2.  `LOGIN_SOURCED_ROWS` is `{9, 10, 11}` and x=52/x=53
    are in no login shape this server composes, so a guard that fires on the
    PRESENCE of x=9 refuses every login."""

    def test_x9_is_in_the_login_sourced_rows(self):
        self.assertIn(sel.SELECTOR_FIELD, attr_wire.LOGIN_SOURCED_ROWS)

    def test_neither_alternate_row_is_in_any_login_shape(self):
        for x in sel.ALTERNATE_PAIR:
            with self.subTest(x=x):
                self.assertNotIn(x, attr_wire.LOGIN_SOURCED_ROWS)
                self.assertNotIn(x, attr_wire.CURRENT_SCENE_SOURCED_ROWS)

    def test_a_login_shaped_block_is_not_refused(self):
        """The regression the first draft would have shipped: x=9 present,
        carrying an ordinary scene byte, no alternate pair."""
        for scene_byte in (0, 1, 3, 126, 255):
            if scene_byte == sel.SELECTOR_ARMED_VALUE:
                continue
            with self.subTest(scene_byte=scene_byte):
                self.assertIsNone(
                    sel.guard_alternate_pair({sel.SELECTOR_FIELD: scene_byte})
                )

    def test_only_the_armed_value_arms_the_guard(self):
        self.assertTrue(
            sel.selector_is_armed({sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE})
        )
        self.assertFalse(
            sel.selector_is_armed(
                {sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE + 1}
            )
        )
        self.assertFalse(sel.selector_is_armed({}))

    def test_the_armed_value_is_imported_from_the_wire_module(self):
        """pf-adversary D7: the first draft hardcoded 8 and no test read it.
        Two doors with two copies of one comparand drift apart silently."""
        self.assertEqual(
            sel.SELECTOR_ARMED_VALUE, attr_wire.SELECTOR_COMPARED_VALUE
        )
        module_text = MODULE_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "SELECTOR_ARMED_VALUE: int = attr_wire.SELECTOR_COMPARED_VALUE",
            module_text,
        )

    def test_the_selector_row_agrees_with_the_wire_modules_own_constant(self):
        """Derived by name here, typed by hand there -- if they ever
        disagree, one of the two is stale and this says which."""
        self.assertEqual(sel.SELECTOR_FIELD, attr_wire.SELECTOR_ROW_X)
        self.assertEqual(set(sel.ALTERNATE_PAIR), set(attr_wire.ALT_HP_PAIR_ROWS))


class TheTwoLayersAreNamedSeparatelyTests(unittest.TestCase):
    """pf-adversary D3.  `-1/1` is what the client CONSTRUCTS when no frame
    ever wrote those rows; `0/0` is what a FRAME produces when it arms the
    selector with the rows unset.  The first draft printed the constructor
    number as if the frame produced it."""

    def test_every_reason_declares_its_layer(self):
        """Every reason names the layer of the EVENT it reports.  All six are
        frame-layer events today: something a frame did or failed to do.  The
        constructor layer appears in `format_report`, which describes a state
        no frame caused, and nowhere else."""
        for reason in sel.ALL_REASONS:
            with self.subTest(reason=reason):
                self.assertTrue(reason.startswith("frame_layer_"), reason)

    def test_the_absent_row_reason_is_a_frame_layer_reason(self):
        self.assertTrue(sel.REASON_ABSENT_READS_ZERO.startswith("frame_layer_"))
        self.assertIn("zero", sel.REASON_ABSENT_READS_ZERO)

    def test_the_construction_default_reason_is_a_frame_layer_event(self):
        """pf-adversary `cgnzsd` D7: a frame that puts 0xFFFFFFFF on the wire
        is a FRAME-layer lie whose VALUE happens to be the constructor
        default.  Labelling the event `constructor_layer_` hid it from an
        operator filtering the console for `frame_layer_`."""
        self.assertTrue(
            sel.REASON_CONSTRUCTION_DEFAULT.startswith("frame_layer_")
        )
        self.assertIn("construction_default", sel.REASON_CONSTRUCTION_DEFAULT)
        gaps = sel.alternate_pair_gaps(
            {
                sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE,
                sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
                sel.ALTERNATE_PAIR[1]: 100,
            }
        )
        self.assertEqual([g.reason for g in gaps], [sel.REASON_CONSTRUCTION_DEFAULT])

    def test_the_refusal_message_names_both_layers_and_confuses_neither(self):
        message = sel.refusal_message(
            sel.alternate_pair_gaps({sel.SELECTOR_FIELD: sel.SELECTOR_ARMED_VALUE})
        )
        self.assertIn("frame layer", message)
        self.assertIn("constructor layer", message)
        self.assertIn("0/0", message)

    def test_the_report_prints_both_branches_with_their_layers(self):
        report = sel.HpPairReport(
            character_id=7,
            primary_current=100,
            primary_max=120,
            alternate_if_unset_current=-1,
            alternate_if_unset_max=1,
            alternate_pair_supplied=False,
        )
        block = sel.format_report(report)
        self.assertIn("constructor layer", block)
        self.assertIn("frame layer", block)
        self.assertIn("100/120", block)


class TheIncumbentFenceIsOnePredicateShortTests(unittest.TestCase):
    """pf-adversary D4 asked what this module adds over the fence that
    already ships at `gm/attr_wire.py:992`.  Measured, not argued.  The
    incumbent's clause is evaluated here from the wire module's own imported
    constants, never retyped, so a change there changes this test."""

    @staticmethod
    def _incumbent_refuses(values):
        return (
            values.get(attr_wire.SELECTOR_ROW_X)
            == attr_wire.SELECTOR_COMPARED_VALUE
            and not attr_wire.ALT_HP_PAIR_ROWS <= set(values)
        )

    @staticmethod
    def _this_module_refuses(values):
        try:
            sel.guard_alternate_pair(values)
        except sel.HpPairError:
            return True
        return False

    def test_the_incumbent_admits_a_frame_that_reads_zero_zero(self):
        values = {
            attr_wire.SELECTOR_ROW_X: attr_wire.SELECTOR_COMPARED_VALUE,
            sel.ALTERNATE_PAIR[0]: 0,
            sel.ALTERNATE_PAIR[1]: 0,
        }
        self.assertFalse(self._incumbent_refuses(values))
        self.assertTrue(self._this_module_refuses(values))

    def test_the_incumbent_admits_a_frame_that_echoes_the_construction_default(self):
        values = {
            attr_wire.SELECTOR_ROW_X: attr_wire.SELECTOR_COMPARED_VALUE,
            sel.ALTERNATE_PAIR[0]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[0],
            sel.ALTERNATE_PAIR[1]: sel.ALTERNATE_CONSTRUCTION_DEFAULTS[1],
        }
        self.assertFalse(self._incumbent_refuses(values))
        self.assertTrue(self._this_module_refuses(values))

    def test_this_module_never_admits_what_the_incumbent_refuses(self):
        """The direction that matters: a strictly stronger door, never a
        second permission gate that opens something the wire wall shut."""
        armed = attr_wire.SELECTOR_COMPARED_VALUE
        blocks = [
            {attr_wire.SELECTOR_ROW_X: armed},
            {attr_wire.SELECTOR_ROW_X: armed, sel.ALTERNATE_PAIR[0]: 5},
            {attr_wire.SELECTOR_ROW_X: armed, sel.ALTERNATE_PAIR[1]: 5},
            {attr_wire.SELECTOR_ROW_X: armed, sel.PRIMARY_PAIR[0]: 5},
        ]
        for values in blocks:
            with self.subTest(values=sorted(values)):
                if self._incumbent_refuses(values):
                    self.assertTrue(self._this_module_refuses(values))

    def test_the_two_doors_print_different_console_tokens(self):
        self.assertNotEqual(
            sel.HP_PAIR_REFUSED_CONSOLE_TOKEN,
            attr_wire.SELECTOR_STANDDOWN_CONSOLE_TOKEN,
        )

    def test_no_block_carrying_the_alternate_pair_can_reach_that_fence(self):
        """pf-adversary `cgnzsd` D1, re-measured by this lane and ACCEPTED.

        `make_update_attr_frame` refuses at `gm/attr_wire.py:955` any block
        whose key set does not EQUAL an admitted login shape, 37 lines before
        the fence at 992.  Neither admitted shape carries x=52/x=53, so the
        membership clause at 992 is always true and the incumbent reduces to
        `values.get(9) == 8` alone -- which `gm/attr_wire.py:989-990` already
        says.  The first draft of this round cited 992 without reading 989
        and claimed a hole that cannot be reached.  This test is that
        correction, pinned to LANE-GM's own function so it cannot rot."""
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        shapes = login_mask.admitted_field_x_sets(legacy)
        self.assertTrue(shapes)
        for shape in shapes:
            with self.subTest(shape=list(shape)):
                self.assertFalse(set(shape) & set(sel.ALTERNATE_PAIR))
                self.assertIn(attr_wire.SELECTOR_ROW_X, shape)

    def test_wiring_this_module_at_that_fence_would_add_nothing(self):
        """The consequence of the test above, measured over the whole domain
        that can reach the fence: both admitted shapes x every byte x=9 can
        carry.  This is why the round's own CORE-REQUEST was withdrawn."""
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        shapes = login_mask.admitted_field_x_sets(legacy)
        disagreements = []
        for shape in shapes:
            for selector_byte in range(256):
                values = {x: 1 for x in shape}
                values[attr_wire.SELECTOR_ROW_X] = selector_byte
                if self._incumbent_refuses(values) != self._this_module_refuses(
                    values
                ):
                    disagreements.append((sorted(shape), selector_byte))
        self.assertEqual(disagreements, [])

    def test_the_module_says_out_loud_that_it_has_no_caller(self):
        """The claim that keeps this module honest while it waits for one."""
        text = MODULE_FILE.read_text(encoding="utf-8")
        self.assertIn("WHO CALLS THIS PREDICATE TODAY: NOBODY", text)
        self.assertIn("WITHDRAWN", text)


class TheModuleDoesNotDecodeCategoryEightTests(unittest.TestCase):
    """`SELECTOR_NOTE_R301`: "WHAT CATEGORY 8 IS: not decoded".  An earlier
    draft of that very note had to strike out a sentence telling a tester
    which scene to visit.  This test is that lesson, applied to this lane's
    own files.

    REWRITTEN IN ROUND `cgnzsd` (pf-adversary D4).  The first detector matched
    three verb patterns and excused any hit with the word `not`/`no`/`never`
    anywhere in the preceding 60 characters, whatever that word negated.  Five
    of five realistic evasions walked through it, and its single control was
    the one sentence engineered to match, so the gate read green.

    THE RULE NOW, and its honest limits.  A SENTENCE is forbidden when it
    names a scene number AND one of the selector's subjects (category, the
    alternate pair, x=52/x=53, `0x430E10`), unless that same sentence carries
    an explicit disclaimer phrase.  Proximity is gone; the excuse must be in
    the sentence that makes the claim.  This is still a smoke alarm and not a
    proof -- English can express the claim without a number, and this does
    not read English.  It is pinned against a corpus of the five sentences
    that defeated the previous version, and it scans BOTH files, because the
    previous one scanned only the module."""

    _SCENE_NUMBER = re.compile(r"\bscene\s*\d+\b|\b126\b", re.IGNORECASE)
    _SELECTOR_SUBJECT = re.compile(
        r"category|alternate\s+(hp\s+)?pair|x=5[23]|0x430E10", re.IGNORECASE
    )
    _DISCLAIMER = re.compile(
        r"does\s+not\s+claim|not\s+decoded|is\s+undecoded|"
        r"no\s+function\s+(here|in\s+this\s+module)\s+computes",
        re.IGNORECASE,
    )

    # BEGIN CONTROL CORPUS -- excluded from the scan by `_scannable`, because
    # these sentences are the thing being detected, not claims of this file.
    _EVASIONS_THAT_MUST_BE_CAUGHT = (
        "Scene 126 takes the alternate pair; category 8 covers open water.",
        "There is no doubt about this now: scene 126 is category 8.",
        "The mapping was measured. It is not a guess -- scene 126 is category 8.",
        "Testers should visit scene 126 to hit the alternate HP pair.",
        "0x430E10(126) returns 8, so 126 selects x=52/x=53.",
    )
    # END CONTROL CORPUS

    _SENTENCE = re.compile(r"[^.!?\n]+")

    @classmethod
    def _offending_sentences(cls, text):
        found = []
        for match in cls._SENTENCE.finditer(text):
            sentence = match.group(0)
            if not cls._SCENE_NUMBER.search(sentence):
                continue
            if not cls._SELECTOR_SUBJECT.search(sentence):
                continue
            if cls._DISCLAIMER.search(sentence):
                continue
            found.append(sentence.strip())
        return found

    @staticmethod
    def _scannable(path):
        """A file's own text minus the control corpus delimited above."""
        text = path.read_text(encoding="utf-8")
        begin = text.find("# BEGIN CONTROL CORPUS")
        stop = text.find("# END CONTROL CORPUS")
        if begin == -1 or stop == -1:
            return text
        return text[:begin] + text[stop:]

    def test_neither_file_maps_a_scene_to_the_category(self):
        for path in (MODULE_FILE, Path(__file__).resolve()):
            with self.subTest(path=path.name):
                self.assertEqual(self._offending_sentences(self._scannable(path)), [])

    def test_the_detector_catches_every_sentence_that_defeated_the_last_one(self):
        """Control.  Without this the rule could be widened until it permits
        everything, which is exactly how the previous version died."""
        for sentence in self._EVASIONS_THAT_MUST_BE_CAUGHT:
            with self.subTest(sentence=sentence):
                self.assertNotEqual(self._offending_sentences(sentence), [])

    def test_the_detector_still_lets_an_explicit_disclaimer_through(self):
        """The other direction: a rule that forbids the disclaimer too would
        make the module unable to say what it does not claim."""
        self.assertEqual(
            self._offending_sentences(
                "It does not claim scene 126 is category 8."
            ),
            [],
        )

    def test_the_control_corpus_is_actually_excluded_from_the_scan(self):
        """If the exclusion silently stopped working the suite would go red
        on its own controls; if it silently swallowed the whole file the scan
        would pass on anything.  Both directions pinned here."""
        own = Path(__file__).resolve()
        scanned = self._scannable(own)
        self.assertNotIn(self._EVASIONS_THAT_MUST_BE_CAUGHT[0], scanned)
        self.assertIn("def test_neither_file_maps_a_scene_to_the_category", scanned)

    def test_the_module_says_the_comparison_is_on_the_result(self):
        text = MODULE_FILE.read_text(encoding="utf-8")
        self.assertIn("RESULT that is compared", text)

    def test_the_module_is_ascii_only(self):
        raw = MODULE_FILE.read_bytes()
        self.assertEqual(raw, raw.decode("ascii").encode("ascii"))


class TheLiveReportReadsARealStoreTests(unittest.TestCase):
    def _store(self, directory):
        store = SQLiteStore(str(Path(directory) / "pf.db"), MIGRATIONS)
        store.migrate()
        return store

    def _character(self, store, key):
        account_id = store.ensure_account("hp-" + key)
        character = store.create_character(
            account_id, "Hp" + key, key, "fingerprint-" + key, _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )
        return character.id

    def test_a_born_character_reports_its_seeded_hp(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "a")
            report = sel.live_hp_pair_report(store, character_id)
            self.assertEqual(report.character_id, character_id)
            self.assertIsNotNone(report.primary_current)
            self.assertIsNotNone(report.primary_max)

    def test_the_primary_pair_carries_the_stores_own_numbers(self):
        """pf-adversary D7: `primary_current`/`primary_max` were replaceable
        by a constant with the whole suite still green, because every test
        only asserted `is not None`.  A fake store with distinct, arbitrary
        numbers kills that mutant."""

        class _FakeStore:
            def __init__(self, values):
                self.values = values
                self.asked = []

            def read_typed_attributes(self, character_id):
                self.asked.append(character_id)
                return dict(self.values)

        for current, maximum in ((37, 41), (1, 999), (0, 0)):
            with self.subTest(hp=(current, maximum)):
                store = _FakeStore({"hp_current": current, "hp_max": maximum})
                report = sel.live_hp_pair_report(store, 4242)
                self.assertEqual(report.primary_current, current)
                self.assertEqual(report.primary_max, maximum)
                self.assertEqual(store.asked, [4242])
                self.assertIn(f"{current}/{maximum}", sel.format_report(report))

    def test_an_unseeded_primary_pair_is_none_not_zero(self):
        class _EmptyStore:
            def read_typed_attributes(self, character_id):
                return {}

        report = sel.live_hp_pair_report(_EmptyStore(), 1)
        self.assertIsNone(report.primary_current)
        self.assertIsNone(report.primary_max)
        self.assertIn("unseeded", sel.format_report(report))

    def test_the_alternate_branch_is_reported_as_unsupplied(self):
        """Not a placeholder: no `characters` column maps to x=52 or x=53,
        so there is nothing this server could read for them."""
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "b")
            report = sel.live_hp_pair_report(store, character_id)
            self.assertFalse(report.alternate_pair_supplied)
            self.assertTrue(report.branch_would_lie())
            self.assertEqual(report.alternate_if_unset_current, -1)
            self.assertEqual(report.alternate_if_unset_max, 1)

    def test_neither_alternate_row_is_a_server_owned_column(self):
        for x in sel.ALTERNATE_PAIR:
            with self.subTest(x=x):
                self.assertNotIn(x, compose.SERVER_OWNED_FIELDS)

    def test_both_primary_rows_are_server_owned_columns(self):
        for x in sel.PRIMARY_PAIR:
            with self.subTest(x=x):
                self.assertIn(x, compose.SERVER_OWNED_FIELDS)

    def test_the_report_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "c")
            before = store.read_typed_attributes(character_id)
            sel.live_hp_pair_report(store, character_id)
            self.assertEqual(store.read_typed_attributes(character_id), before)

    def test_a_missing_character_raises_the_store_s_own_error(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            with self.assertRaises(KeyError):
                sel.live_hp_pair_report(store, 999999)

    def test_the_console_block_is_ascii_and_names_both_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            character_id = self._character(store, "d")
            text = sel.format_report(
                sel.live_hp_pair_report(store, character_id)
            )
            text.encode("ascii")
            self.assertIn("HP_PAIR_SELECTOR_REPORT", text)
            self.assertIn(f"x={sel.PRIMARY_PAIR[0]}", text)
            self.assertIn(f"x={sel.ALTERNATE_PAIR[0]}", text)
            self.assertIn("0x430E10 is not evaluated here", text)


if __name__ == "__main__":
    unittest.main()
