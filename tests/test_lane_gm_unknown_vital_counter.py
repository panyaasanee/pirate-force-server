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

    def test_a_string_shaped_id_is_coerced_before_formatting(self):
        # A caller that hands in something int()-able (never str-formats
        # it directly) still gets the fixed hex shape, not a str echoed
        # back verbatim -- guards the format string against whatever the
        # eventual call site's own id extraction hands in.
        session = _session()
        counter._on_unknown_vital(session, "4660")  # 0x1234
        self.assertEqual(session.events, ["unknown_vital_id_0x1234"])

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
