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
    def test_the_shut_set_is_pinned_in_both_directions(self):
        # pf-adversary D10: assertIn catches a door OPENING and never a door
        # CLOSING - measured, a fifth shut scene kept the whole file green
        # while the module docstring's "four scenes today" went stale.
        self.assertEqual(_shut_scene_ids(), (17, 126, 304, 305))

    def test_the_brick_set_is_the_two_column_answer_and_excludes_17(self):
        # pf-adversary D3: a shut door only strands a character if a durable
        # row naming that scene can be WRITTEN.  Scene 17 carries
        # persist_position_allowed=false, which is why this lane's own
        # world_m2_return_leg says a relog from 17 already lands on land.
        self.assertEqual(recovery_mod.brick_risk_scene_ids(), (126, 304, 305))
        self.assertNotIn(17, recovery_mod.brick_risk_scene_ids())
        for scene_id in recovery_mod.brick_risk_scene_ids():
            self.assertIn(scene_id, _shut_scene_ids())

    def test_the_ids_come_back_sorted(self):
        # pf-adversary D13: six tests index [0] and [-1] of this tuple, so an
        # unpinned order silently changes what they mean.
        self.assertEqual(list(_shut_scene_ids()), sorted(_shut_scene_ids()))
        self.assertEqual(
            list(recovery_mod.brick_risk_scene_ids()),
            sorted(recovery_mod.brick_risk_scene_ids()),
        )

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

    def test_a_remembered_row_the_door_refuses_falls_back_to_the_home_pin(self):
        # pf-adversary D8.  A remembered row in a shut scene must NOT become
        # an arrival (login never admits it) and must NOT leave the caller
        # worse off than passing nothing at all.
        shut = _shut_scene_ids()
        stored = _row_in(shut[0])
        rec = recovery_mod.recovery_for_refusal(
            stored,
            _refusal_for(stored),
            remembered=_row_in(shut[-1]),
            emit=_silent,
        )
        self.assertIsNotNone(rec)
        self.assertEqual(
            rec.ashore_source, recovery_mod.SOURCE_HOME_PIN_AFTER_REMEMBERED
        )
        self.assertEqual(rec.ashore, world_scene_travel.home_return_position())
        self.assertNotIn(rec.entry.position.scene_id, shut)

    def test_a_remembered_row_with_unusable_fields_is_a_loud_bug(self):
        # pf-adversary D2: Position validates nothing, so type() alone let a
        # string coordinate through to abs(x - spawn_x).
        stored = _row_in(_shut_scene_ids()[0])
        for bad in (
            Position(278, 0, "a", "b", 0.0),
            Position("278", 0, 0.0, 0.0, 0.0),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    recovery_mod.recovery_for_refusal(
                        stored, _refusal_for(stored), remembered=bad,
                        emit=_silent,
                    )

    def test_a_remembered_row_that_is_not_a_position_is_a_loud_bug(self):
        stored = _row_in(_shut_scene_ids()[0])
        with self.assertRaises(ValueError):
            recovery_mod.recovery_for_refusal(
                stored, _refusal_for(stored), remembered=(1, 0, 0, 0, 0, 0),
                emit=_silent,
            )


class DeclinedReasonTests(unittest.TestCase):
    def test_the_recoverable_set_is_pinned_as_a_value(self):
        # Pinned as a value, not as a loop condition.  Without this, the
        # "other reasons are declined" test below passes VACUOUSLY the day
        # somebody widens the set - measured: that mutant survived.
        self.assertEqual(
            recovery_mod.RECOVERABLE_REASONS,
            (
                world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
                world_scene_entry.REFUSED_SCENE_ID_OUT_OF_RANGE,
            ),
        )

    def test_a_zeroed_row_recovers_rather_than_staying_bricked(self):
        # pf-adversary D5: store.save_position accepts scene_id 0 and
        # world_scene_travel.destination requires 1, so a zeroed row is
        # persistable and unresolvable.  The range is two literals, so no
        # registry fault can make this fire for a whole population.
        stored = _row_in(0)
        exc = _refusal_for(stored)
        self.assertEqual(
            exc.reason, world_scene_entry.REFUSED_SCENE_ID_OUT_OF_RANGE
        )
        rec = recovery_mod.recovery_for_refusal(stored, exc, emit=_silent)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.entry.position.scene_id, world_scene_travel.HOME_SCENE_ID)

    def test_an_unpinned_scene_is_declined_rather_than_walked_home(self):
        # The failure this cut exists to prevent: a swapped or truncated
        # registry makes EVERY row unpinned, and recovering that reason walks
        # the whole population to Port Royal, then heals their durable rows
        # to it at the first step.  This asks the real door for the refusal.
        unpinned = 999
        stored = _row_in(unpinned)
        exc = _refusal_for(stored)
        self.assertEqual(exc.reason, world_scene_entry.REFUSED_SCENE_NOT_PINNED)
        captured, emit = _lines()
        self.assertIsNone(
            recovery_mod.recovery_for_refusal(stored, exc, emit=emit)
        )
        self.assertEqual(len(captured), 1)
        self.assertIn(recovery_mod.DECLINED_REASON_NOT_RECOVERABLE, captured[0])

    def test_the_other_refusal_reasons_are_declined_by_name(self):
        stored = _row_in(_shut_scene_ids()[0])
        seen = 0
        for reason in (
            world_scene_entry.REFUSED_SCENE_NOT_PINNED,
            world_scene_entry.REFUSED_NO_PINNED_SPAWN,
        ):
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
        self.assertEqual(
            seen,
            len(world_scene_entry.REFUSAL_REASONS)
            - len(recovery_mod.RECOVERABLE_REASONS),
        )
        self.assertGreaterEqual(seen, 2)

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
            names,
            ["from_scene", "refusal", "to_scene", "source", "arrived", "durable"],
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


class PlugSiteContractTests(unittest.TestCase):
    """pf-adversary D1: `entry` alone re-arms the brick at the next TargetPos."""

    def test_the_recovery_names_the_in_memory_row_the_caller_must_adopt(self):
        stored = _row_in(recovery_mod.brick_risk_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        # Not the shut scene: a caller that adopts this row makes the next
        # durable write name a scene the login door admits, which is the
        # whole of "the row heals at the first TargetPos".
        self.assertEqual(rec.selected_resync, rec.entry.position)
        self.assertNotIn(rec.selected_resync.scene_id, _shut_scene_ids())
        self.assertNotEqual(rec.selected_resync.scene_id, stored.scene_id)

    def test_the_resync_is_the_door_s_row_not_the_row_offered_to_it(self):
        # The two are equal whenever the door kept the offer, so equality on
        # the ordinary path let a mutant returning `ashore` survive
        # (measured).  This builds the case where they differ.
        stored = _row_in(recovery_mod.brick_risk_scene_ids()[0])
        real = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        offered_elsewhere = Position(999, 7, 1.0, 2.0, 3.0, 4.0)
        forged = recovery_mod.LoginRecovery(
            refused_scene_id=real.refused_scene_id,
            refused_reason=real.refused_reason,
            ashore=offered_elsewhere,
            ashore_source=real.ashore_source,
            entry=real.entry,
        )
        self.assertEqual(forged.selected_resync, real.entry.position)
        self.assertNotEqual(forged.selected_resync, offered_elsewhere)
        # And the console reports the arrival, not the discarded offer.
        self.assertIn(
            f"to_scene={real.entry.position.scene_id}", forged.console_line
        )
        self.assertNotIn("to_scene=999", forged.console_line)

    def test_a_write_is_never_authorised_by_the_recovery_itself(self):
        stored = _row_in(recovery_mod.brick_risk_scene_ids()[0])
        rec = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), emit=_silent
        )
        self.assertFalse(rec.durable_write_allowed)
        # pf-adversary D6: as a defaulted field this was constructible True.
        with self.assertRaises((TypeError, AttributeError)):
            recovery_mod.LoginRecovery(
                refused_scene_id=stored.scene_id,
                refused_reason=rec.refused_reason,
                ashore=rec.ashore,
                ashore_source=rec.ashore_source,
                entry=rec.entry,
                durable_write_allowed=True,
            )


class RegistryFaultTests(unittest.TestCase):
    """pf-adversary D4/D2: a broken pin is not a bad character row."""

    def test_a_registry_that_will_not_load_is_named_as_itself(self):
        class Broken:
            destinations = ()

        stored = _row_in(_shut_scene_ids()[0])
        captured, emit = _lines()
        rec = recovery_mod.try_recovery_for_refusal(
            stored, _refusal_for(stored), registry=Broken(), emit=emit
        )
        self.assertIsNone(rec)
        self.assertEqual(len(captured), 1)
        self.assertIn(recovery_mod.DECLINED_REGISTRY_FAULT, captured[0])
        self.assertNotIn(recovery_mod.DECLINED_BAD_ARGUMENTS, captured[0])

    def test_a_registry_of_the_wrong_type_never_escapes_the_soft_door(self):
        stored = _row_in(_shut_scene_ids()[0])
        for bogus in (object(), {}, [], 7):
            with self.subTest(bogus=type(bogus)):
                captured, emit = _lines()
                self.assertIsNone(
                    recovery_mod.try_recovery_for_refusal(
                        stored, _refusal_for(stored), registry=bogus, emit=emit
                    )
                )
                self.assertEqual(len(captured), 1)

    def test_an_unreadable_pin_file_does_not_escape_the_soft_door(self):
        # The DEFAULT call shape is registry=None, which reads the pin file on
        # two separate paths.  Measured escape: FileNotFoundError.
        stored = _row_in(_shut_scene_ids()[0])
        refusal = _refusal_for(stored)  # taken BEFORE the pin is broken
        original = world_scene_travel.load_scene_registry

        def explode(*args, **kwargs):
            raise FileNotFoundError("world_scene_registry_001.json")

        world_scene_travel.load_scene_registry = explode
        try:
            captured, emit = _lines()
            rec = recovery_mod.try_recovery_for_refusal(
                stored, refusal, emit=emit
            )
        finally:
            world_scene_travel.load_scene_registry = original
        self.assertIsNone(rec)
        self.assertEqual(len(captured), 1)
        self.assertIn(recovery_mod.DECLINED_REGISTRY_FAULT, captured[0])

    def test_an_emit_that_is_not_callable_does_not_escape_the_soft_door(self):
        # There is no console to decline on, so the only thing left is to
        # leave the listener thread alive.  The strict door still shouts.
        stored = _row_in(_shut_scene_ids()[0])
        for bogus in (None, 7, "print"):
            with self.subTest(bogus=bogus):
                self.assertIsNone(
                    recovery_mod.try_recovery_for_refusal(
                        stored, _refusal_for(stored), emit=bogus
                    )
                )
                with self.assertRaises(ValueError):
                    recovery_mod.recovery_for_refusal(
                        stored, _refusal_for(stored), emit=bogus
                    )


class HostileRowTests(unittest.TestCase):
    """pf-adversary D6: Position validates nothing and scene_id is printed."""

    def test_a_scene_id_that_is_not_an_int_cannot_forge_a_field(self):
        line = recovery_mod._declined_line(
            "126 durable=1 xx",
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
            recovery_mod.DECLINED_BAD_ARGUMENTS,
        )
        self.assertEqual(line.count("="), 3)
        self.assertNotIn("durable=", line)
        line.encode("ascii")

    def test_a_scene_id_outside_cp874_cannot_reach_the_console(self):
        for hostile in ("\u0e01\u2603", 1.5, None, True, b"126"):
            with self.subTest(hostile=hostile):
                field = recovery_mod._scene_field(hostile)
                self.assertEqual(field, "not_a_scene_id")
                field.encode("ascii")

    def test_a_hostile_stored_row_declines_instead_of_raising(self):
        stored = Position("126 durable=1 xx", 0, 0.0, 0.0, 0.0)
        captured, emit = _lines()
        rec = recovery_mod.try_recovery_for_refusal(
            stored,
            world_scene_entry.SceneEntryRefused(
                world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN, "measured"
            ),
            emit=emit,
        )
        self.assertIsNone(rec)
        self.assertEqual(len(captured), 1)
        self.assertNotIn("durable=", captured[0])


class ArrivedFieldTests(unittest.TestCase):
    """pf-adversary D7: `source=` names the offer, not the landing."""

    def test_a_relocated_remembered_row_does_not_print_as_offered(self):
        stored = _row_in(recovery_mod.brick_risk_scene_ids()[0])
        home = world_scene_travel.home_return_position()
        kept = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), remembered=home, emit=_silent
        )
        self.assertIn("arrived=as_offered", kept.console_line)
        self.assertFalse(kept.relocated)
        # A remembered row the door admits but MOVES must not print the same
        # line as one it kept.
        moved = Position(
            home.scene_id, home.scene_seq,
            home.x + 500000.0, home.y + 500000.0, home.z, home.heading,
        )
        landed = recovery_mod.recovery_for_refusal(
            stored, _refusal_for(stored), remembered=moved, emit=_silent
        )
        if landed.relocated:
            self.assertIn("arrived=relocated", landed.console_line)
            self.assertNotEqual(landed.console_line, kept.console_line)
        else:
            self.assertEqual(landed.entry.position, moved)


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
