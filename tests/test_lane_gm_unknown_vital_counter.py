"""lane_hooks/lane_gm_unknown_vital_counter.py -- CORE-REQUEST-GM-063.

Not wired into runtime.py yet (see the module's own
``registered_but_not_fired``); this proves the hook function's own
contract in isolation, the same posture
``test_gm_activity_cheat_code_dispatch.py`` takes for ``gm/dispatch.py``
before its own call site existed.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_gm_unknown_vital_counter as counter,
)


def _session() -> types.SimpleNamespace:
    return types.SimpleNamespace(events=[])


class LaneGmUnknownVitalCounterTests(unittest.TestCase):
    def test_production_allowed(self):
        self.assertIs(counter.production_allowed, True)

    def test_declares_registered_but_not_fired(self):
        # The call site is chief's (CORE-REQUEST-GM-063) -- until it lands,
        # gm/lane_gate_name_audit.py's dead-hook-point scan must see this
        # declaration or it reds on a registered point nothing fires.
        self.assertEqual(
            counter.registered_but_not_fired, ("vital_inbound_unknown_id",)
        )

    def test_discovered_and_registered_under_its_own_point(self):
        points = lane_hooks.registered_points()
        self.assertIn("vital_inbound_unknown_id", points)
        self.assertGreaterEqual(points["vital_inbound_unknown_id"], 1)

    def test_records_one_line_for_a_new_id(self):
        session = _session()
        counter._on_unknown_vital(session, 0x9999)
        self.assertEqual(session.events, ["unknown_vital_id_0x9999"])

    def test_second_call_same_id_same_session_adds_nothing(self):
        # The whole point of the per-session dedup set: a scripted sender
        # replaying one unrecognised id must not grow this session's event
        # log without bound.
        session = _session()
        counter._on_unknown_vital(session, 0x9999)
        counter._on_unknown_vital(session, 0x9999)
        counter._on_unknown_vital(session, 0x9999)
        self.assertEqual(session.events, ["unknown_vital_id_0x9999"])

    def test_a_different_id_on_the_same_session_adds_a_second_line(self):
        session = _session()
        counter._on_unknown_vital(session, 0x9999)
        counter._on_unknown_vital(session, 0xABCD)
        self.assertEqual(
            session.events,
            ["unknown_vital_id_0x9999", "unknown_vital_id_0xABCD"],
        )

    def test_two_sessions_do_not_share_the_dedup_set(self):
        # Per-session state lives on the session object itself, not in a
        # module-level dict keyed by something -- two independent
        # connections must not suppress each other's first sighting.
        session_a = _session()
        session_b = _session()
        counter._on_unknown_vital(session_a, 0x1234)
        counter._on_unknown_vital(session_b, 0x1234)
        self.assertEqual(session_a.events, ["unknown_vital_id_0x1234"])
        self.assertEqual(session_b.events, ["unknown_vital_id_0x1234"])

    def test_an_id_this_hook_cannot_report_truthfully_is_dropped(self):
        # This card replaces `test_a_string_shaped_id_is_coerced_before_
        # formatting`, which pinned `int(vital_id)` and therefore pinned the
        # bug: pf-adversary (round `vq07el`) fed the old code 4660.9 and got
        # `unknown_vital_id_0x1234` -- a DIFFERENT id from the one handed in,
        # written into the one record whose only job is to say which id
        # arrived. 0x12345 produced a five-digit line the old comment called
        # a "fixed hex shape"; -1 produced `0x-001`; True produced `0x0001`.
        #
        # Silence is recoverable and a wrong id in a P-3 capture is not, so
        # every one of these is dropped instead of coerced.
        for bad in ("4660", "0x51E9", 4660.9, -1, 0x10000, True, None):
            with self.subTest(bad=bad):
                session = _session()
                counter._on_unknown_vital(session, bad)
                self.assertEqual(session.events, [])

    def test_the_edges_of_the_id_space_are_still_recorded(self):
        # The refusal above must not have narrowed the hook to a subset of
        # real ids: `nested_id = c.u16(0x12)`, so 0x0000 and 0xFFFF are both
        # frames a client can actually send.
        for good in (0x0000, 0xFFFF):
            with self.subTest(good=good):
                session = _session()
                counter._on_unknown_vital(session, good)
                self.assertEqual(
                    session.events, [f"unknown_vital_id_0x{good:04X}"]
                )

    def test_one_session_cannot_record_the_whole_id_space(self):
        # pf-adversary (round `vq07el`) walked 0x0000..0xFFFF once each
        # against the real event list and measured 65,536 events, 15.05 MiB
        # of heap and 65,536 flushed console lines -- from a peer that has
        # not logged in, because this hook's call site is in dispatch() and
        # dispatch() runs from the first frame. Dedup bounded REPEATS and
        # nothing bounded DISTINCT ids.
        session = _session()
        for vital_id in range(0x0000, 0x0100):
            counter._on_unknown_vital(session, vital_id)
        self.assertEqual(
            len(session.events), counter.MAX_UNKNOWN_IDS_PER_SESSION + 1
        )
        self.assertEqual(session.events[-1], counter.CAP_REACHED_EVENT)

    def test_the_cap_line_is_said_once_and_not_once_per_frame(self):
        # The cap is worth nothing if reaching it is itself per-frame: that
        # is the same flood wearing a different string.
        session = _session()
        for vital_id in range(0x0000, 0x0400):
            counter._on_unknown_vital(session, vital_id)
        self.assertEqual(
            session.events.count(counter.CAP_REACHED_EVENT), 1
        )

    def test_the_truncation_is_visible_to_whoever_reads_the_capture(self):
        # A cap that recorded nothing about itself would leave a truncated
        # list looking like a complete one -- the exact false negative this
        # module exists to close, re-introduced one layer up.
        session = _session()
        for vital_id in range(0x0000, 0x0100):
            counter._on_unknown_vital(session, vital_id)
        self.assertIn(counter.CAP_REACHED_EVENT, session.events)
        self.assertIn(
            str(counter.MAX_UNKNOWN_IDS_PER_SESSION), counter.CAP_REACHED_EVENT
        )

    def test_a_session_that_will_not_carry_the_set_records_nothing(self):
        # Every attribute touch is guarded, because this runs per frame: an
        # AttributeError here would not be one error, it would be one error
        # per frame through fire(). And a hook that cannot dedup must not
        # record -- without the set every frame is a first sighting, which
        # is the per-frame line the contract forbids.
        class _NoAttributes:
            __slots__ = ()
            events: list = []

        session = _NoAttributes()
        counter._on_unknown_vital(session, 0x1234)
        self.assertEqual(_NoAttributes.events, [])

    def test_a_session_with_no_events_list_does_not_raise(self):
        class _NoEvents:
            pass

        session = _NoEvents()
        counter._on_unknown_vital(session, 0x1234)  # must not raise

    def test_no_payload_parameter_exists_to_store_one(self):
        # The contract (COO-DECISION 20260906T11:49+07:00 item 3) is
        # "count/record the id only, no payload stored" -- enforced at the
        # signature level: the hook takes no bytes-shaped argument at all,
        # so there is nothing here a future edit could accidentally start
        # writing to disk or appending to events.
        import inspect

        params = list(inspect.signature(counter._on_unknown_vital).parameters)
        self.assertEqual(params, ["session", "vital_id"])

    def test_fire_reaches_the_hook_and_appends_exactly_one_line(self):
        # End-to-end through the real fire() path, not just a direct call,
        # so a future refactor of the decorator/registration plumbing is
        # covered too.
        session = _session()
        lane_hooks.fire("vital_inbound_unknown_id", session=session, vital_id=0x2222)
        self.assertEqual(session.events, ["unknown_vital_id_0x2222"])


if __name__ == "__main__":
    unittest.main()
