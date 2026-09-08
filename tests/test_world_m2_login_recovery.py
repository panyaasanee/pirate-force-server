"""LANE-A, M2: the refused login becomes an arrival ashore.

Every case here derives the shut-scene set from the registry rather than
spelling it in, so the day a door opens these tests re-derive the claim
instead of pinning a number that has gone stale.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    world_m2_login_recovery as recovery_mod,
    world_scene_entry,
    world_scene_travel,
)
from pirateforce_foundation.model import Position


def _silent(_line):
    return None


def _lines():
    captured = []
    return captured, captured.append


def _shut_scene_ids():
    return recovery_mod.login_shut_scene_ids()


def _refusal_for(stored):
    """The refusal the real door raises for this row - never constructed."""
    try:
        world_scene_entry.resolve_entry(stored, emit=_silent, via_login=True)
    except world_scene_entry.SceneEntryRefused as exc:
        return exc
    raise AssertionError(f"the door admitted {stored!r}; this test needs a refusal")


def _row_in(scene_id):
    return Position(scene_id, 0, 10.0, 20.0, 30.0, 0.0)


class ShutDoorsAreDerivedTests(unittest.TestCase):
    def test_the_set_is_not_empty_and_contains_the_m2_destinations(self):
        shut = _shut_scene_ids()
        self.assertTrue(shut, "no shut door left = this module has nothing to guard")
        # The three M2 seam destinations chief measured (R399), plus 17.
        for scene_id in (17, 126, 304, 305):
            self.assertIn(scene_id, shut)

    def test_home_is_not_shut(self):
        self.assertNotIn(world_scene_travel.HOME_SCENE_ID, _shut_scene_ids())

    def test_every_shut_scene_really_is_refused_by_the_door(self):
        for scene_id in _shut_scene_ids():
            with self.subTest(scene_id=scene_id):
                exc = _refusal_for(_row_in(scene_id))
                self.assertEqual(
                    exc.reason, world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN
                )


class RecoveryTests(unittest.TestCase):
    def test_every_shut_scene_recovers_to_an_admitted_arrival(self):
        for scene_id in _shut_scene_ids():
            with self.subTest(scene_id=scene_id):
                stored = _row_in(scene_id)
                rec = recovery_mod.recovery_for_refusal(
                    stored, _refusal_for(stored), emit=_silent
                )
                self.assertIsNotNone(rec)
                self.assertEqual(rec.refused_scene_id, scene_id)
                self.assertNotIn(rec.entry.position.scene_id, _shut_scene_ids())
                # The arrival came through the same door, so it is admissible.
                world_scene_entry.resolve_entry(
                    rec.ashore, emit=_silent, via_login=True
                )

    def test_a_recovery_is_a_visit_and_never_authorises_a_write(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertFalse(rec.durable_write_allowed)
        self.assertIn("durable=0", rec.console_line)

    def test_the_stored_row_is_reported_not_replaced(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertEqual(rec.refused_scene_id, stored.scene_id)
        self.assertEqual(rec.entry.stored, rec.ashore)

    def test_a_second_login_without_moving_recovers_again(self):
        # The row is not written, so the brick does not come back but the
        # recovery does.  Both logins must produce the same arrival.
        stored = _row_in(_shut_scene_ids()[0])
        first = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        second = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertEqual(first.console_line, second.console_line)
        self.assertEqual(first.entry.position, second.entry.position)


class RememberedRowTests(unittest.TestCase):
    def test_a_remembered_row_the_door_admits_is_used(self):
        stored = _row_in(_shut_scene_ids()[0])
        remembered = world_scene_travel.home_return_position()
        remembered = Position(
            remembered.scene_id,
            remembered.scene_seq,
            remembered.x + 1.0,
            remembered.y,
            remembered.z,
            remembered.heading,
        )
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), remembered=remembered, emit=_silent
        )
        self.assertEqual(rec.ashore_source, recovery_mod.SOURCE_REMEMBERED)
        self.assertEqual(rec.ashore, remembered)

    def test_no_remembered_row_falls_back_to_the_home_pin(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertEqual(rec.ashore_source, recovery_mod.SOURCE_HOME_PIN)
        self.assertEqual(rec.ashore, world_scene_travel.home_return_position())

    def test_a_remembered_row_the_door_refuses_declines_rather_than_arrives(self):
        # A remembered row that is itself in a shut scene must NOT become an
        # arrival: that would put a character somewhere login never admits.
        shut = _shut_scene_ids()
        stored = _row_in(shut[0])
        rec = recovery_mod.recovery_for_refusal(
            stored,
            _refusal_for(stored),
            remembered=_row_in(shut[-1]),
            emit=_silent,
        )
        self.assertIsNone(rec)

    def test_a_remembered_row_that_is_not_a_position_is_a_loud_bug(self):
        stored = _row_in(_shut_scene_ids()[0])
        with self.assertRaises(ValueError):
            recovery_mod.recovery_for_refusal(
                stored, _refusal_for(stored), remembered=(1, 0, 0, 0, 0, 0),
                emit=_silent,
            )


class DeclinedReasonTests(unittest.TestCase):
    def test_the_recoverable_set_is_exactly_the_shut_door(self):
        # Pinned as a value, not as a loop condition.  Without this, the
        # "other reasons are declined" test below passes VACUOUSLY the day
        # somebody widens the set - measured: that mutant survived.
        self.assertEqual(
            recovery_mod.RECOVERABLE_REASONS,
            (world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,),
        )

    def test_an_unpinned_scene_is_declined_rather_than_walked_home(self):
        # The failure this cut exists to prevent: a swapped or truncated
        # registry makes EVERY row unpinned, and recovering that reason walks
        # the whole population to Port Royal, then heals their durable rows
        # to it at the first step.  This asks the real door for the refusal.
        unpinned = max(_shut_scene_ids()) + 100000
        stored = _row_in(unpinned)
        exc = _refusal_for(stored)
        self.assertNotEqual(
            exc.reason, world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN
        )
        captured, emit = _lines()
        self.assertIsNone(
            recovery_mod.recovery_for_refusal(stored, exc, emit=emit)
        )
        self.assertEqual(len(captured), 1)
        self.assertIn(recovery_mod.DECLINED_REASON_NOT_RECOVERABLE, captured[0])

    def test_the_other_refusal_reasons_are_declined_by_name(self):
        stored = _row_in(_shut_scene_ids()[0])
        seen = 0
        for reason in world_scene_entry.REFUSAL_REASONS:
            if reason == world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN:
                continue
            seen += 1
            with self.subTest(reason=reason):
                captured, emit = _lines()
                refusal = world_scene_entry.SceneEntryRefused(reason, "measured")
                rec = recovery_mod.recovery_for_refusal(
                    stored, refusal, emit=emit
                )
                self.assertIsNone(rec)
                self.assertEqual(len(captured), 1)
                self.assertIn(recovery_mod.DECLINED_CONSOLE_TOKEN, captured[0])
                self.assertIn(
                    recovery_mod.DECLINED_REASON_NOT_RECOVERABLE, captured[0]
                )
                self.assertIn(reason, captured[0])
        self.assertEqual(seen, len(world_scene_entry.REFUSAL_REASONS) - 1)
        self.assertGreaterEqual(seen, 3)

    def test_declining_and_recovering_do_not_share_a_token(self):
        self.assertNotIn(
            recovery_mod.CONSOLE_TOKEN, recovery_mod.DECLINED_CONSOLE_TOKEN
        )
        self.assertNotIn(
            recovery_mod.DECLINED_CONSOLE_TOKEN, recovery_mod.CONSOLE_TOKEN
        )

    def test_an_unknown_refusal_reason_is_refused_not_recovered(self):
        stored = _row_in(_shut_scene_ids()[0])
        real = _refusal_for(stored)
        # A refusal object whose reason was tampered with after construction.
        object.__setattr__(real, "reason", "invented_reason")
        with self.assertRaises(ValueError):
            recovery_mod.recovery_for_refusal(stored, real, emit=_silent)

    def test_something_that_is_not_a_refusal_is_a_loud_bug(self):
        stored = _row_in(_shut_scene_ids()[0])
        for bogus in (None, LookupError("no"), "scene_not_allowed_at_login"):
            with self.subTest(bogus=bogus):
                with self.assertRaises(ValueError):
                    recovery_mod.recovery_for_refusal(stored, bogus, emit=_silent)


class FailSoftDoorTests(unittest.TestCase):
    """`try_recovery_for_refusal` sits inside runtime.py's except handler."""

    def test_bad_arguments_decline_instead_of_raising(self):
        stored = _row_in(_shut_scene_ids()[0])
        for bad_stored, bad_refusal in (
            (None, _refusal_for(stored)),
            ((126, 0, 0.0, 0.0, 0.0, 0.0), _refusal_for(stored)),
            (stored, None),
            (stored, "not a refusal"),
            (None, None),
        ):
            with self.subTest(stored=type(bad_stored), refusal=type(bad_refusal)):
                captured, emit = _lines()
                rec = recovery_mod.try_recovery_for_refusal(
                    bad_stored, bad_refusal, emit=emit
                )
                self.assertIsNone(rec)
                self.assertEqual(len(captured), 1)
                self.assertIn(
                    recovery_mod.DECLINED_BAD_ARGUMENTS, captured[0]
                )

    def test_the_good_path_is_the_same_answer_as_the_strict_one(self):
        stored = _row_in(_shut_scene_ids()[0])
        soft = recovery_mod.try_recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        strict = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertEqual(soft.console_line, strict.console_line)


class ConsoleLineTests(unittest.TestCase):
    def test_the_line_is_ascii_and_one_line(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        line = rec.console_line
        line.encode("ascii")
        self.assertNotIn("\n", line)
        self.assertTrue(line.startswith(recovery_mod.CONSOLE_TOKEN))

    def test_every_field_is_one_name_equals_one_value(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        fields = rec.console_line.split(" ")[1:]
        names = [field.split("=")[0] for field in fields]
        self.assertEqual(
            names, ["from_scene", "refusal", "to_scene", "source", "durable"]
        )
        for field in fields:
            self.assertEqual(field.count("="), 1, field)

    def test_two_different_shut_scenes_do_not_print_the_same_line(self):
        shut = _shut_scene_ids()
        lines = set()
        for scene_id in shut:
            stored = _row_in(scene_id)
            rec = recovery_mod.recovery_for_refusal(
                stored, _refusal_for(stored), emit=_silent
            )
            lines.add(rec.console_line)
        self.assertEqual(len(lines), len(shut))

    def test_a_reason_carrying_a_separator_is_refused_not_split(self):
        for hostile in ("has space", "has=equals", "has@at", "smörg", "", "a\nb"):
            with self.subTest(hostile=hostile):
                field = recovery_mod._reason_field(hostile)
                self.assertNotIn("=", field)
                self.assertNotIn(" ", field)
                field.encode("ascii")

    def test_the_console_line_needs_a_real_recovery(self):
        with self.assertRaises(ValueError):
            recovery_mod.recovery_console_line("WORLD_LOGIN_RECOVERED scene=1")

    def test_the_recovering_call_emits_exactly_one_recovery_line(self):
        stored = _row_in(_shut_scene_ids()[0])
        captured, emit = _lines()
        recovery_mod.recovery_for_refusal(stored, _refusal_for(stored), emit=emit)
        recovered = [
            line for line in captured
            if line.startswith(recovery_mod.CONSOLE_TOKEN)
        ]
        self.assertEqual(len(recovered), 1)
        self.assertEqual(
            [l for l in captured if recovery_mod.DECLINED_CONSOLE_TOKEN in l], []
        )


class ReportTests(unittest.TestCase):
    def test_the_report_carries_both_rows(self):
        stored = _row_in(_shut_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        report = recovery_mod.recovery_report(rec)
        self.assertEqual(report["refused_scene_id"], stored.scene_id)
        self.assertEqual(
            report["refused_reason"],
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
        )
        self.assertFalse(report["durable_write_allowed"])
        # The wrapped scene-entry columns are still there.
        self.assertIn("stored_scene_id", report)

    def test_the_report_needs_a_real_recovery(self):
        with self.assertRaises(ValueError):
            recovery_mod.recovery_report({"refused_scene_id": 126})


class NoStateTests(unittest.TestCase):
    def test_the_module_holds_no_mutable_module_level_state(self):
        mutable = [
            name for name, value in vars(recovery_mod).items()
            if not name.startswith("__")
            and isinstance(value, (list, dict, set, bytearray))
        ]
        self.assertEqual(mutable, [])

    def test_it_is_not_behind_a_flag(self):
        self.assertTrue(recovery_mod.production_allowed)
        self.assertFalse(recovery_mod.test_only)


if __name__ == "__main__":
    unittest.main()
