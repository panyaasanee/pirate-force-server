"""lane_hooks/lane_gm_unknown_vital_counter.py -- CORE-REQUEST-GM-063.

At HEAD nothing in ``runtime.py`` fires this module's point, and that is
the measured state, not a "yet": round R390 landed a call site in
``dispatch()`` and round R391 withdrew it again, because a detector
standing there cannot answer the question the point asks (which branch,
if any, read this id).  The module therefore declares the point in its
own ``registered_but_not_fired``, and
``test_declares_never_fired_exactly_while_nothing_fires_it`` below pins
that declaration against ``runtime.py``'s real ``fire()`` call sites.
Everything else here proves the hook function's own contract in
isolation, the posture ``test_gm_activity_cheat_code_dispatch.py`` took
for ``gm/dispatch.py`` while that seam had no call site either.
"""
from __future__ import annotations

import ast
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


#: The module a call site must reach ``fire`` through, and the name of the
#: function itself, as ``src/pirateforce_foundation/`` spells both.
LANE_HOOKS_MODULE_NAME = "lane_hooks"
FIRE_FUNCTION_NAME = "fire"
#: ``fire()`` takes the point positionally in every call site in the tree,
#: but it is an ordinary keyword too, so both are read here.
POINT_KEYWORD = "point"


def _dotted(node: ast.expr) -> str | None:
    """``a.b.c`` for an attribute chain rooted in a plain name, else None."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _fire_point(node: ast.Call) -> str | None:
    """The point name this call passes, only when it is a string literal."""
    candidate: ast.expr | None = node.args[0] if node.args else None
    if candidate is None:
        for entry in node.keywords:
            if entry.arg == POINT_KEYWORD:
                candidate = entry.value
                break
    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
        return candidate.value
    return None


def _fired_hook_names(source: str) -> set[str]:
    """Hook points ``source`` actually fires, read from its AST.

    Only real ``lane_hooks.fire("<point>")`` CALL SITES count.  This
    replaces the string-grep the relation pin below used to do
    (``"<point>" in runtime_source``), which a COMMENT satisfied: chief
    measured both halves of that defect in round R391 (mutants M10/M11,
    ``pf_bridge/rounds/R391_ammtv3_withdraw_the_gm063_detector_from_main``).
    Writing the point name into a comment reddened the pin with no code
    change at all, and writing it into a comment WHILE deleting the real
    call site turned the pin green -- the exact state the pin exists to
    catch.  ``ast.parse`` drops comments, and this walks calls only, so
    prose about a point is invisible here by construction.

    The dotted name before ``.fire`` must match a binding this same source
    created for the lane_hooks module, WHOLE -- not by its last segment,
    which is what keeps ``cannon.lane_hooks.fire(...)`` and
    ``self.config.lane_hooks.fire(...)`` out (the trap
    ``gm/lane_gate_name_audit.py`` documents at ``_resolves_to``, found by
    pf-adversary).  ``lane_hooks.announce_direct_fire(...)`` is a
    different function and is deliberately not counted.
    """
    tree = ast.parse(source)
    module_bindings: set[str] = set()
    fire_bindings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # `import x.y.lane_hooks` is usable as the whole dotted path.
            for alias in node.names:
                if alias.name.split(".")[-1] == LANE_HOOKS_MODULE_NAME:
                    module_bindings.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            tail = (node.module or "").split(".")[-1]
            for alias in node.names:
                if alias.name == LANE_HOOKS_MODULE_NAME:
                    module_bindings.add(alias.asname or alias.name)
                elif (
                    tail == LANE_HOOKS_MODULE_NAME
                    and alias.name == FIRE_FUNCTION_NAME
                ):
                    fire_bindings.add(alias.asname or alias.name)

    fired: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr != FIRE_FUNCTION_NAME:
                continue
            if _dotted(func.value) not in module_bindings:
                continue
        elif isinstance(func, ast.Name):
            if func.id not in fire_bindings:
                continue
        else:
            continue
        point = _fire_point(node)
        if point is not None:
            fired.add(point)
    return fired


def _runtime_source() -> str:
    return (
        ROOT / "src" / "pirateforce_foundation" / "runtime.py"
    ).read_text(encoding="utf-8")


def _session() -> types.SimpleNamespace:
    return types.SimpleNamespace(events=[])


class LaneGmUnknownVitalCounterTests(unittest.TestCase):
    def test_production_allowed(self):
        self.assertIs(counter.production_allowed, True)

    def test_declares_never_fired_exactly_while_nothing_fires_it(self):
        # PIN MOVED, NOT DELETED, by the commit that landed the call site
        # (CORE-REQUEST-GM-063, chief round R390).  The old form asserted
        # the declaration is present, so landing the fire() the letter asks
        # for turned this file red however chief did it, including when he
        # followed the module's own deletion instruction exactly.
        #
        # This asserts the RELATION instead, the shape
        # tests/test_lane_a_island_trigger_log.py already uses for the same
        # handover: the module declares the point never-fired if and only
        # if nothing fires it.  Both end states are green, both illegal
        # in-between states are red.
        #
        # "Fires it" is read from runtime.py's AST, not from its text.  The
        # first form of this pin asked `"vital_inbound_unknown_id" in
        # runtime_source`, so a COMMENT naming the point answered for the
        # code -- R391's mutants M10 and M11 measured it going red on prose
        # alone and, worse, going GREEN on prose that stood in for the
        # deleted call site.  _fired_hook_names() carries the reasoning.
        fired = _fired_hook_names(_runtime_source())
        self.assertTrue(
            fired,
            "read no lane_hooks.fire() call site at all in runtime.py: the "
            "reader above is broken, and a broken reader would answer "
            "'nothing fires it' for every point and pass this pin by "
            "default",
        )
        fired_by_runtime = "vital_inbound_unknown_id" in fired
        declared = "vital_inbound_unknown_id" in getattr(
            counter, "registered_but_not_fired", ()
        )
        self.assertEqual(
            declared,
            not fired_by_runtime,
            "declare the point never-fired exactly while nothing fires it: "
            f"runtime.py fires it = {fired_by_runtime}, "
            f"declared = {declared}",
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
        # pf-adversary (round `vq07el`) walked the whole 16-bit id space
        # once each against the real event list and measured one event,
        # 15.05 MiB of heap and one flushed console line PER ID -- and at
        # the time it measured that, the call site was in dispatch(),
        # which runs from the first frame of a peer that has not logged
        # in.  R391 withdrew that call site, so today nothing reaches this
        # hook from the wire; the cap stays because it is the hook's own
        # contract and the next call site to land must not have to
        # rediscover it.  Dedup bounded REPEATS and nothing bounded
        # DISTINCT ids.
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
