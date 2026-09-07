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
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pirateforce_foundation import combat_pose, lane_hooks          # noqa: E402
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


class Store:
    def __init__(self, raises=None):
        self.calls, self._raises = [], raises

    def equip_item(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises


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


#: A class whose n_EQUIPTYPE is NOT 8, so a slot written as the wire value
#: and a slot written as the equip type can never be confused here.
CLASS_UNDER_TEST = 1
assert combat_pose.equip_type_for_class(CLASS_UNDER_TEST) != 8
RIGHT_HAND = mod.RIGHT_HAND_TEMPLATE_BY_CLASS_ID[CLASS_UNDER_TEST]
EQUIP_TYPE = combat_pose.equip_type_for_class(CLASS_UNDER_TEST)


def a_session(*, class_id=CLASS_UNDER_TEST, identity=41,
              template_id=RIGHT_HAND, store=None, bag="default"):
    store = Store() if store is None else store
    if bag == "default":
        bag = Bag([Row(identity, template_id)])
    return Session(Foundation(Character(7, class_id), bag, store)), store


def fire(session, value32=8, item_identity=41):
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
            "character_id": 7, "slot_id": EQUIP_TYPE,
            "item_identity": 41, "item_template_id": RIGHT_HAND})
        self.assertIn("%s %s " % (mod.CONSOLE_PREFIX, mod.WROTE), line)

    def test_the_slot_written_is_the_equip_type_and_never_the_wire_value(self):
        for value32 in (8, 0, 255, RIGHT_HAND, None):
            with self.subTest(value32=value32):
                session, store = a_session()
                fire(session, value32=value32)
                self.assertEqual(store.calls[0]["slot_id"], EQUIP_TYPE)
                self.assertNotEqual(store.calls[0]["slot_id"], value32)

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
