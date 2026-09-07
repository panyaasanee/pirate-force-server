"""LANE-DB: the op=5 equip becomes a durable row, and nothing else.

Covers ``lane_hooks/lane_db_item_operate_op5.py`` at two levels: the hook
function called directly, and the same function reached through
``lane_hooks.fire("vital_inbound_item_operate_op5", ...)`` -- the way
``runtime.py:9910`` reaches it -- so "registered" is measured, not assumed.

THE PIN THIS FILE EXISTS FOR is
``test_the_slot_written_is_the_equip_type_and_never_the_wire_value``: the
wire's ``value32`` is 8 in the only capture this project has (``RE-272``),
and ``n_EQUIPTYPE`` for the class whose weapon it plausibly is happens to be
8 as well.  ``RE-280``'s red warning is that those two 8s must not be
assumed to be the same 8.  A fixture where they are equal cannot tell a
correct implementation from the guess, so every write test here uses a
class whose ``n_EQUIPTYPE`` differs from the ``value32`` handed in.
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pirateforce_foundation import combat_pose, lane_hooks          # noqa: E402
from pirateforce_foundation import store as store_module             # noqa: E402
from pirateforce_foundation.lane_hooks import (                      # noqa: E402
    lane_db_item_operate_op5 as mod,
)
from pirateforce_foundation.persistence_class_id import (            # noqa: E402
    CLASS_PRESETS,
)

ROOT = Path(__file__).resolve().parent.parent


class Row:
    def __init__(self, identity, template_id):
        self.identity, self.template_id = identity, template_id


class Bag:
    def __init__(self, items):
        self.items = tuple(items)


class Character:
    def __init__(self, cid, class_id):
        self.id, self.class_id = cid, class_id


#: What the double's `equip_item_nowait` hands back, standing in for the
#: row id the real door reads back inside its own transaction.
FAKE_ROWID = 91


class Store:
    """The store door the hook calls, and ONLY that door.

    `test_the_double_calls_a_door_the_real_store_actually_has` pins the
    method name against `SQLiteStore` so a green suite here can never mean
    a hook calling a method production does not have.
    """

    def __init__(self, raises=None):
        self.calls, self._raises = [], raises

    def equip_item_nowait(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return FAKE_ROWID


class Lifecycle:
    def __init__(self, store):
        self.store = store


class Foundation:
    def __init__(self, selected, backpack, store, session_id="sid-1"):
        self.selected, self.backpack = selected, backpack
        self.lifecycle, self.session_id = Lifecycle(store), session_id


class Session:
    def __init__(self, foundation):
        self.foundation = foundation


#: THE FIXTURE'S CLASS IS CHOSEN SO THAT NO TWO NUMBERS IN PLAY COINCIDE,
#: and that is the whole reason it is not class 1.  `pf-adversary` finding
#: `D7` on `#1064` killed the earlier fixture for exactly this: at class 1
#: the class id, the `n_EQUIPTYPE`, and `bit_length()` were ALL 1, so three
#: wrong implementations (`slot_id=class_id`, `slot_id=1`,
#: `slot_id=equip_type.bit_length()`) survived every mutant.  The assert
#: below is what stops that from coming back silently: the numbers that
#: must stay distinct are the slot this file expects
#: (`EQUIP_INDEX_RIGHT_HAND_ONE`), the class id, the class's `n_EQUIPTYPE`,
#: the wire's `value32` (8, from `RE-272`), and the `n_EQUIPTYPE`'s bit
#: length.  Class 32 is the only one of the five that satisfies all of it
#: (`n_EQUIPTYPE` 64, bit length 7): at class 1 three numbers are 1, at
#: class 2 the class id and the kind are both 2, at class 4 the class id
#: and `bit_length()-1` are both 4, and at class 16 the kind is the wire's
#: own 8.  Its kind being 64 also makes a second point for free -- 64 is
#: not a legal mask index at all, so `n_EQUIPTYPE` visibly is not one.
CLASS_UNDER_TEST = 32
RIGHT_HAND = mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID[CLASS_UNDER_TEST]
EQUIP_TYPE = combat_pose.equip_type_for_class(CLASS_UNDER_TEST)
WIRE_VALUE32 = 8
EXPECTED_SLOT = mod.EQUIP_INDEX_RIGHT_HAND_ONE
assert EXPECTED_SLOT is not None, (
    "the committed report no longer states the right-hand-one index; the"
    " module refuses to write and this fixture cannot pin what it writes")
_DISTINCT = (EXPECTED_SLOT, CLASS_UNDER_TEST, EQUIP_TYPE, WIRE_VALUE32,
             int(EQUIP_TYPE).bit_length(), int(EQUIP_TYPE).bit_length() - 1)
assert len(set(_DISTINCT)) == len(_DISTINCT), (
    "fixture numbers coincide (%r) -- a wrong implementation would survive"
    % (_DISTINCT,))


def a_session(*, class_id=CLASS_UNDER_TEST, identity=41,
              template_id=RIGHT_HAND, store=None, bag="default"):
    store = Store() if store is None else store
    if bag == "default":
        bag = Bag([Row(identity, template_id)])
    return Session(Foundation(Character(7, class_id), bag, store)), store


def fire(session, value32=WIRE_VALUE32, item_identity=41):
    """Call through ``lane_hooks.fire()`` and return the stderr it wrote."""
    captured, real = io.StringIO(), sys.stderr
    sys.stderr = captured
    try:
        lane_hooks.fire(
            mod.HOOK_POINT, session=session, value32=value32,
            item_identity=item_identity)
    finally:
        sys.stderr = real
    return captured.getvalue()


class TheHookIsReachableTheWayRuntimeReachesItTests(unittest.TestCase):
    def test_the_module_is_registered_on_the_point_runtime_fires(self):
        registered = [
            name for name, _fn in lane_hooks._HOOKS.get(mod.HOOK_POINT, ())]
        self.assertIn(mod.remember_the_equip.__module__, registered)

    def test_the_point_name_is_the_one_runtime_py_actually_fires(self):
        source = (ROOT / "src" / "pirateforce_foundation" / "runtime.py")
        self.assertIn(
            '"%s"' % mod.HOOK_POINT, source.read_text(encoding="utf-8"),
            "the seam runtime.py fires no longer carries this point name")

    def test_the_module_ships_without_a_scenario_flag(self):
        self.assertIs(mod.production_allowed, True)


class TheWriteTests(unittest.TestCase):
    def test_the_class_right_hand_is_persisted(self):
        session, store = a_session()
        line = fire(session)
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0], {
            "character_id": 7, "slot_id": EXPECTED_SLOT,
            "item_identity": 41, "item_template_id": RIGHT_HAND})
        # The LITERAL token, not `mod.CONSOLE_PREFIX`/`mod.WROTE`: `D7`
        # killed both constants as surviving mutants because every
        # assertion went through the module's own spelling, so a rename
        # would have broken every runbook grepping this line and no test
        # would have noticed.
        self.assertIn("LANE_DB_EQUIP wrote ", line)
        self.assertIn("slot_equip_index=%d" % EXPECTED_SLOT, line)
        # "the row is there", not "the call returned" (`D9`).
        self.assertIn("row=%d" % FAKE_ROWID, line)

    def test_the_slot_written_is_the_mask_index_and_nothing_else(self):
        """The four numbers that are NOT the slot, pinned one by one.

        `pf-adversary` `D1`: `n_EQUIPTYPE` cannot be the slot (650 of 974
        `EQUIPMENT_BASE` rows exceed the column's 0..255, and three kinds
        share one `n_EQUIPSLOT`).  `RE-280`: `value32` is not proven to be
        `+0x39`.  `D7`: the class id and the bit length were only ever
        indistinguishable because the old fixture used class 1.
        """
        for value32 in (WIRE_VALUE32, 0, 255, RIGHT_HAND, None):
            with self.subTest(value32=value32):
                session, store = a_session()
                fire(session, value32=value32)
                written = store.calls[0]["slot_id"]
                self.assertEqual(written, EXPECTED_SLOT)
                self.assertNotEqual(written, value32)
                self.assertNotEqual(written, EQUIP_TYPE)
                self.assertNotEqual(written, CLASS_UNDER_TEST)
                self.assertNotEqual(written, int(EQUIP_TYPE).bit_length())

    def test_the_slot_written_is_inside_the_range_a_mask_index_can_have(self):
        # RE-280: the client computes `1 << N` into a 32-bit mask, so a
        # number outside 0..31 is not a slot at all, whatever else it is.
        session, store = a_session()
        fire(session)
        self.assertTrue(0 <= store.calls[0]["slot_id"] <= 31)

    def test_the_wire_value_is_carried_on_the_console_line_for_the_next_re(self):
        session, _store = a_session()
        self.assertIn("value32=8", fire(session, value32=8))

    def test_the_sentinel_that_means_not_worn_is_never_written(self):
        # RE-280: 0xFF is the client's "not equipped" sentinel, and only
        # 0..31 can ever be a real slot bit.  Whatever numbering the column
        # holds, the sentinel must not be a value this server writes.
        for class_id in mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID:
            with self.subTest(class_id=class_id):
                self.assertNotEqual(
                    combat_pose.equip_type_for_class(class_id), 0xFF)


class TheRefusalsWriteNothingTests(unittest.TestCase):
    def refusal(self, session, **kwargs):
        store = session.foundation.lifecycle.store
        line = fire(session, **kwargs)
        self.assertEqual(store.calls, [], "a refusal wrote a row")
        self.assertNotIn(
            "%s %s " % (mod.CONSOLE_PREFIX, mod.WROTE), line)
        return line

    def test_no_selected_character(self):
        session, _store = a_session()
        session.foundation.selected = None
        self.assertIn(mod.REASON_NO_CHARACTER, self.refusal(session))

    def test_no_backpack_loaded(self):
        session, _store = a_session(bag=None)
        self.assertIn(mod.REASON_NO_BAG, self.refusal(session))

    def test_identity_the_bag_does_not_hold(self):
        session, _store = a_session()
        self.assertIn(
            mod.REASON_IDENTITY_NOT_IN_BAG,
            self.refusal(session, item_identity=999))

    def test_a_template_that_is_not_the_class_right_hand(self):
        session, _store = a_session(template_id=RIGHT_HAND + 1)
        self.assertIn(
            mod.REASON_TEMPLATE_IS_NOT_THE_CLASS_RIGHT_HAND,
            self.refusal(session))

    def test_a_class_id_the_creation_table_never_heard_of(self):
        session, _store = a_session(class_id=999)
        self.assertIn(
            mod.REASON_CLASS_NOT_IN_CREATION_GEAR, self.refusal(session))

    def test_an_unresolved_class_id(self):
        session, _store = a_session(class_id=None)
        self.assertIn(mod.REASON_NO_CLASS_ID, self.refusal(session))

    def test_a_bool_class_id_is_refused_not_looked_up_as_one(self):
        # True == 1 and hashes equal, so an unguarded dict lookup would
        # write a real class 1 row for a character that has no class.
        session, _store = a_session(class_id=True)
        self.assertIn(mod.REASON_NO_CLASS_ID, self.refusal(session))

    def test_a_bag_whose_rows_raise_is_unreadable_not_resolved(self):
        class Angry:
            @property
            def identity(self):
                raise RuntimeError("row is not readable")

        session, _store = a_session(bag=Bag([Angry()]))
        self.assertIn(mod.REASON_BAG_UNREADABLE, self.refusal(session))

    def test_two_rows_wearing_one_identity_are_unreadable_not_resolved(self):
        session, _store = a_session(
            bag=Bag([Row(41, RIGHT_HAND), Row(41, RIGHT_HAND)]))
        self.assertIn(mod.REASON_BAG_UNREADABLE, self.refusal(session))

    def test_a_session_with_no_store_writes_nothing(self):
        session, _store = a_session()
        del session.foundation.lifecycle.store
        self.assertIn(mod.REASON_NO_STORE, fire(session))


class NothingEscapesIntoTheListenerTests(unittest.TestCase):
    def test_a_store_that_refuses_is_reported_by_name_not_raised(self):
        for error in (KeyError(7), ValueError("slot_id out of range"),
                      RuntimeError("write lock")):
            with self.subTest(error=type(error).__name__):
                session, store = a_session(store=Store(raises=error))
                line = fire(session)
                self.assertIn(mod.REASON_STORE_REFUSED, line)
                self.assertIn("err=%s" % type(error).__name__, line)

    def test_the_hook_never_raises_for_any_argument_shape(self):
        for kwargs in (
            {"session": None},
            {"session": object()},
            {"session": Session(object())},
            {"item_identity": None},
        ):
            with self.subTest(kwargs=sorted(kwargs)):
                call = {"session": a_session()[0], "value32": 8,
                        "item_identity": 41}
                call.update(kwargs)
                captured, real = io.StringIO(), sys.stderr
                sys.stderr = captured
                try:
                    mod.remember_the_equip(**call)
                finally:
                    sys.stderr = real
                self.assertNotIn("LANE_HOOK_ERR", captured.getvalue())

    def test_a_missing_keyword_is_a_named_refusal_not_a_typeerror(self):
        captured, real = io.StringIO(), sys.stderr
        sys.stderr = captured
        try:
            mod.remember_the_equip()
        finally:
            sys.stderr = real
        self.assertIn(mod.REASON_NO_CHARACTER, captured.getvalue())


class TheTwoTablesStillAgreeTests(unittest.TestCase):
    """Dies on its own if either committed table drifts.

    ``persistence_class_id`` builds ``n_SLOT_RHAND`` off
    ``charcreate_class.tsv``; ``combat_pose`` reads ``n_EQUIPTYPE`` off
    ``creation_gear_by_class.tsv``.  The module under test takes one column
    from each.  Nothing else in this repository checks that the two files
    still name the same right hand for the same class, so this does --
    derived from both sources, with no id typed here by hand.
    """

    def _creation_gear_rows(self):
        path = (ROOT / "src" / "pirateforce_foundation" / "data"
                / "creation_gear_by_class.tsv")
        raw = path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), combat_pose.CREATION_GEAR_SHA256,
            "creation_gear_by_class.tsv drifted from combat_pose's pin")
        with path.open("r", encoding="ascii", newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_both_tables_name_the_same_right_hand_for_every_class(self):
        from_creation_gear = {
            int(row["n_CLASS_ID"]): int(row["n_SLOT_RHAND"])
            for row in self._creation_gear_rows()}
        self.assertEqual(
            mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID, from_creation_gear)

    def test_the_map_comes_from_the_presets_not_from_a_second_file_read(self):
        self.assertEqual(
            mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID,
            {row[0]: row[3] for row in CLASS_PRESETS})

    def test_every_class_the_map_names_has_an_equip_type(self):
        for class_id in mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID:
            with self.subTest(class_id=class_id):
                self.assertIsNotNone(combat_pose.equip_type_for_class(class_id))


class TheAuditCanStillReadThisRegistrationTests(unittest.TestCase):
    """``gm/lane_gate_name_audit.py`` grades hook points from SOURCE.

    A registration whose point name is not a string literal makes that audit
    refuse to grade any hook point in the whole tree, so this file must keep
    a literal in the decorator -- and the constant beside it must keep saying
    the same thing.  Both halves are pinned here rather than trusted.
    """

    def _decorator_literals(self):
        import ast

        tree = ast.parse(Path(mod.__file__).read_text(encoding="ascii"))
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                name = getattr(decorator.func, "id", None)
                if name != "hook":
                    continue
                found.append(
                    [arg.value for arg in decorator.args
                     if isinstance(arg, ast.Constant)])
        return found

    def test_every_registration_names_its_point_as_a_string_literal(self):
        literals = self._decorator_literals()
        self.assertEqual(len(literals), 1)
        self.assertEqual(len(literals[0]), 1)

    def test_the_decorator_literal_and_the_constant_cannot_drift_apart(self):
        self.assertEqual(self._decorator_literals()[0][0], mod.HOOK_POINT)


class TheConsoleStaysReadableOnCp874Tests(unittest.TestCase):
    def test_the_source_file_is_pure_ascii(self):
        raw = Path(mod.__file__).read_bytes()
        self.assertEqual([b for b in raw if b > 127], [])

    def test_every_reason_is_ascii_and_spaceless(self):
        for reason in mod.REASONS:
            with self.subTest(reason=reason):
                reason.encode("ascii")
                self.assertNotIn(" ", reason)

    def test_every_line_this_module_can_print_encodes_on_cp874(self):
        session, _store = a_session()
        lines = [fire(session)]
        session, _store = a_session(class_id=999)
        lines.append(fire(session))
        for line in lines:
            with self.subTest(line=line[:40]):
                line.encode("cp874")


if __name__ == "__main__":
    unittest.main()


class TheOneClientNumberComesFromTheCommittedReportTests(unittest.TestCase):
    """`D1`'s replacement number, and the rule that it is never invented.

    The module writes the client's `ItemAttr+0x39` mask index, and it reads
    that index out of `reports/PF_RE_V130_Equipped_Blade_Negative_Boundary_
    20260815.md` rather than carrying a literal, so the report stays the
    single source for a client fact this lane did not recover itself.
    """

    def test_the_index_is_the_number_the_committed_report_states(self):
        text = mod.EQUIP_INDEX_REPORT.read_text(encoding="utf-8")
        found = mod.EQUIP_INDEX_SENTENCE.findall(text)
        self.assertEqual(len(found), 1, "the provenance sentence moved")
        self.assertEqual(mod.EQUIP_INDEX_RIGHT_HAND_ONE, int(found[0]))

    def test_the_report_is_a_file_in_this_repository(self):
        self.assertTrue(mod.EQUIP_INDEX_REPORT.is_file())
        self.assertEqual(mod.EQUIP_INDEX_REPORT.parent.name, "reports")

    def test_a_report_without_the_sentence_yields_no_number_not_a_default(self):
        for body, why in (
            ("nothing about equipment here\n", "sentence gone"),
            ("statically mapped right-hand-one equipment index 3\n"
             "statically mapped right-hand-one equipment index 5\n",
             "stated twice, and this module must not pick one"),
            ("statically mapped right-hand-one equipment index 47\n",
             "47 cannot be a 32-bit mask index"),
        ):
            with self.subTest(why=why):
                with tempfile.TemporaryDirectory() as tmp:
                    doctored = Path(tmp) / "report.md"
                    doctored.write_text(body, encoding="utf-8")
                    with mock.patch.object(
                            mod, "EQUIP_INDEX_REPORT", doctored):
                        self.assertIsNone(mod._right_hand_equipment_index())

    def test_a_missing_report_is_none_and_never_an_import_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                    mod, "EQUIP_INDEX_REPORT", Path(tmp) / "absent.md"):
                self.assertIsNone(mod._right_hand_equipment_index())

    def test_without_a_proven_index_the_hook_writes_nothing_by_name(self):
        session, store = a_session()
        with mock.patch.object(mod, "EQUIP_INDEX_RIGHT_HAND_ONE", None):
            line = fire(session)
        self.assertEqual(store.calls, [])
        self.assertIn("LANE_DB_EQUIP equip_index_unproven", line)


class TheDoorTheHookCallsTests(unittest.TestCase):
    def test_the_double_calls_a_door_the_real_store_actually_has(self):
        # A green suite against a double that names a method production
        # does not have is the oldest way to ship a hook that raises on the
        # first real frame.
        self.assertTrue(hasattr(store_module.SQLiteStore, "equip_item_nowait"))
        real = inspect.signature(
            store_module.SQLiteStore.equip_item_nowait).parameters
        for name in ("character_id", "slot_id", "item_identity",
                     "item_template_id"):
            self.assertIn(name, real)

    def test_the_canonical_blocking_door_is_not_the_one_called(self):
        session, store = a_session()
        fire(session)
        self.assertEqual(len(store.calls), 1)
        self.assertFalse(hasattr(store, "equip_item"),
                         "the double must not offer the blocking door at all")

    def test_a_busy_lock_is_reported_apart_from_a_refusal(self):
        session, store = a_session(
            store=Store(raises=store_module.WriteLockTimeout("held")))
        line = fire(session)
        self.assertIn("LANE_DB_EQUIP store_busy ", line)
        self.assertNotIn(mod.REASON_STORE_REFUSED, line)
        self.assertNotIn("LANE_DB_EQUIP wrote", line)


class TheReasonCensusIsNotVacuousTests(unittest.TestCase):
    def test_every_reason_is_listed_and_the_census_is_not_empty(self):
        # `D7`: `REASONS = frozenset()` survived as a mutant because the
        # ASCII census iterated an empty set and reported PASS.
        self.assertGreaterEqual(len(mod.REASONS), 12)
        named = {
            value for name, value in vars(mod).items()
            if name.startswith("REASON_") and isinstance(value, str)
        }
        named.add(mod.WROTE)
        self.assertEqual(named, set(mod.REASONS))
        for reason in mod.REASONS:
            self.assertEqual(reason, reason.encode("ascii").decode("ascii"))
