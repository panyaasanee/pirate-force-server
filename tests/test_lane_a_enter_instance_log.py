"""The log-only NavigationEx_EnterInstanceVital (0xC723) hook: RE-227's
five-byte fixed shape, decoded without walking tags.

LANE-A, round `09:51`, for COO-DECISION 20260904_0747 item 3(a) and
COO-DECISION 20260904_0850 item 3, correcting the chief (LANE-E) letter of
round `8nh6q5`/R334 at 08:01+07 with its own 09:10+07 follow-up: this frame's
body is `12 <opaque-u16 LE> 0B 06`, and its first byte IS the tag
`lane_a_island_trigger_log`'s walker deliberately cannot step over -- so this
module decodes the fixed shape directly instead of reusing that walker.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_enter_instance_log as hooklog,
)


def _body(opaque: int, trailer: bytes = b"\x0b\x06") -> bytes:
    return b"\x12" + opaque.to_bytes(2, "little") + trailer


class TheProducerOfTheOnlyEventFragment(unittest.TestCase):
    """THE TRIPWIRE `sent_state` NEEDS, AND DID NOT HAVE.

    pf-adversary (round `xf6eoi`, MEASURED) renamed `runtime.py`'s
    ``m2_survey_trial_sent_<n>`` event to `..._DISPATCHED_<n>` and ran the
    WHOLE suite: green, every test, including the nine below.  The console
    would then have printed `provisioned=2 ... sent=0` on a boot that
    composed and queued two records -- `sent=0` being exactly the reading
    an attended grader is told means "this server never sent".  Nothing
    anywhere went red, because the only thing tying reader to producer was
    the same literal typed twice: once in `lane_a_enter_instance_log.py`
    and once in a `_FakeSession(events=[...])` fixture in this file.

    That is a fixture, not a tripwire.  The test this round retired
    (`test_the_state_is_the_repositorys_and_goes_red_when_a_call_site_
    lands`) DID act -- it is why chief had to touch this lane's constant in
    `#763` at all -- so the recovery must not leave the file with less
    coupling than it had.  This class is that coupling, in the direction
    that matters: the reader's prefix must still be what the writer writes.

    `runtime.py` is chief's file and LANE-A may not edit it.  This does not
    edit it; it reads it, and goes red rather than silently disagreeing
    with it.  Read via `ast`, not `grep`: an f-string tokenises differently
    on 3.11 and on the gate's 3.14 (PEP 701), and `ast.JoinedStr` is the
    one reading that is identical on both.
    """

    RUNTIME = ROOT / "src" / "pirateforce_foundation" / "runtime.py"

    def _appended_event_prefixes(self):
        """Every static prefix appended to a `.events` list in `runtime.py`.

        Matches `<anything>.events.append(f"prefix{...}")` and the plain
        string form, and returns the leading literal of each.
        """
        tree = ast.parse(self.RUNTIME.read_text(encoding="utf-8"))
        prefixes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "append":
                continue
            target = func.value
            if not isinstance(target, ast.Attribute) or target.attr != "events":
                continue
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):
                    head = arg.values[0] if arg.values else None
                    if isinstance(head, ast.Constant) and isinstance(head.value, str):
                        prefixes.append(head.value)
                elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    prefixes.append(arg.value)
        return prefixes

    def test_the_prefix_this_hook_counts_is_still_the_one_runtime_appends(self):
        prefixes = self._appended_event_prefixes()
        # `runtime.py` appends ~300 distinct event prefixes; printing all of
        # them on failure buries the answer.  Show only the survey-trial
        # neighbours, which is where a rename will have landed.
        neighbours = sorted({p for p in prefixes if p.startswith("m2_survey")})
        self.assertTrue(
            hooklog._SENT_EVENT_PREFIX in prefixes,
            "runtime.py no longer appends the event this hook counts.  The "
            "`sent=` fragment on LANE_A_ENTER_INSTANCE now reads 0 on a boot "
            "that sent records.  Either restore the event name or move "
            "`_SENT_EVENT_PREFIX` to match it -- do not delete this test.  "
            f"Looking for {hooklog._SENT_EVENT_PREFIX!r}; the survey-trial "
            f"prefixes runtime.py does append are: {neighbours}",
        )

    def test_the_reader_is_not_pinned_to_a_prefix_nothing_writes(self):
        """The mirror: this file's own fixtures must use the real name.

        A fixture string that has drifted from the module constant would
        make every `sent=` test above pass against a prefix the hook does
        not count.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertIn(
            f'"{hooklog._SENT_EVENT_PREFIX}',
            source,
            "this file's fixtures no longer spell the prefix the hook reads",
        )


class DecodeOpaqueTests(unittest.TestCase):
    def test_the_shape_re_227_pinned_decodes_to_its_own_u16(self):
        for opaque in (0x0000, 0x0001, 0x1234, 0xBEEF, 0xFFFF):
            with self.subTest(opaque=hex(opaque)):
                self.assertEqual(hooklog.decode_opaque(_body(opaque)), opaque)

    def test_little_endian_is_load_bearing(self):
        # 0x1234 read big-endian would be 0x3412 -- a byte-order slip a
        # same-value round trip could never catch.
        self.assertEqual(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x06"), 0x1234)
        self.assertNotEqual(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x06"), 0x1234 // 0x100 + (0x1234 % 0x100) * 0x100)

    def test_wrong_length_refuses(self):
        for payload in (b"", b"\x12", b"\x12\x34\x12", b"\x12\x34\x12\x0b", b"\x12\x34\x12\x0b\x06\x00"):
            with self.subTest(payload=payload):
                self.assertIsNone(hooklog.decode_opaque(payload))

    def test_wrong_leading_tag_refuses(self):
        # This is the exact case chief's first (08:01) letter would have
        # gotten wrong by mirroring the trigger-vital walker: that walker's
        # table has no entry for 0x12 at all, so it is not a "wrong tag", it
        # is "no tag" -- here the tag is checked and rejected explicitly.
        self.assertIsNone(hooklog.decode_opaque(b"\x0f\x34\x12\x0b\x06"))

    def test_wrong_trailer_refuses(self):
        self.assertIsNone(hooklog.decode_opaque(b"\x12\x34\x12\x0b\x07"))
        self.assertIsNone(hooklog.decode_opaque(b"\x12\x34\x12\x0c\x06"))

    def test_the_confirm_bodys_own_encoder_round_trips(self):
        # Same construction the dispatch-wiring test's `_confirm_body` uses
        # (`legacy.u16tag(0x12, opaque) + legacy.u8tag(0x0B, 6)`), built here
        # from the frozen tag encoders directly so a change to either side
        # of that pairing is caught without importing the other test module.
        sys.path.insert(0, str(ROOT / "current"))
        import pf_login_game_server_v141 as legacy

        for opaque in (0, 1, 0x1234, 0xFFFF):
            body = legacy.u16tag(0x12, opaque) + legacy.u8tag(0x0B, 6)
            with self.subTest(opaque=hex(opaque)):
                self.assertEqual(body, _body(opaque))
                self.assertEqual(hooklog.decode_opaque(body), opaque)


class ConsoleLineTests(unittest.TestCase):
    def test_a_matching_payload_prints_the_raw_opaque_value(self):
        line = hooklog.console_line(_body(0x1234))
        self.assertIn("opaque=0x1234", line)
        self.assertIn("no_responder bytes_out=0", line)
        self.assertNotIn("UNPARSED", line)

    def test_the_value_is_never_named_island_scene_or_trigger_tip(self):
        # RE-227 nonclaim 3, restated by chief 09:10: the u16 is proven only
        # to be copied unchanged, never what it means.
        line = hooklog.console_line(_body(153))
        self.assertNotIn("island", line.lower())
        self.assertNotIn("scene", line.lower())
        self.assertNotIn("trigger", line.lower())

    def test_a_non_matching_payload_prints_unparsed_with_hex(self):
        line = hooklog.console_line(b"\xff\xee\xdd")
        self.assertIn("UNPARSED", line)
        self.assertIn("hex=ffeedd", line)
        self.assertIn("len=3", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_console_output_is_ascii(self):
        for payload in (_body(0x1234), b"\xff\xee\xdd", b""):
            hooklog.console_line(payload).encode("ascii")

    def test_an_unparsed_payloads_hex_is_capped_not_written_unbounded(self):
        # pf-adversary (this round): the first draft had no cap at all --
        # a 2,000,000-byte payload produced a 4,000,072-character line.
        # Same constant and reasoning as the trigger-vital sibling's own
        # `_MAX_HEX_BYTES`.
        huge = b"\xab" * 2_000_000
        line = hooklog.console_line(huge)
        self.assertLess(len(line), 1_000)
        self.assertIn(f"len={len(huge)}", line)
        self.assertIn("hex=" + ("ab" * hooklog._MAX_HEX_BYTES) + "+", line)

    def test_a_payload_no_longer_than_the_cap_is_not_marked_truncated(self):
        payload = b"\xff" * hooklog._MAX_HEX_BYTES
        line = hooklog.console_line(payload)
        self.assertIn("hex=" + ("ff" * hooklog._MAX_HEX_BYTES), line)
        self.assertNotIn("+", line)


class TheProvisioningAnnotationTests(unittest.TestCase):
    """The `issued=` / `provisioned=` pair the line carries from
    `world_m2_survey_plan` (LANE-A round `npbdgr`).

    It is about THIS SERVER, never about the client's reading of the u16 --
    the guard above (`test_the_value_is_never_named_island_scene_or_trigger_
    tip`) still governs the assembled line, and these tests exist so the
    annotation cannot quietly become decoration that says the same thing
    whatever the plan holds.
    """

    def test_a_decoded_line_says_this_build_can_provision_nothing(self):
        # GT-228 (R308, PASS) has since left both real M2 targets measured
        # by default, so the "provisions nothing" shape is reproduced here
        # by forcing the plan empty rather than assumed for free.
        from pirateforce_foundation import world_m2_survey_plan as plan

        saved = dict(plan.MEASURED_XYZ)
        try:
            plan.MEASURED_XYZ.clear()
            line = hooklog.console_line(_body(0x1234))
            self.assertIn("issued=no", line)
            self.assertIn("provisioned=0", line)
        finally:
            plan.MEASURED_XYZ.clear()
            plan.MEASURED_XYZ.update(saved)

    def test_the_annotation_tracks_the_plan_rather_than_being_a_constant(self):
        from pirateforce_foundation import world_m2_survey_plan as plan

        saved = dict(plan.MEASURED_XYZ)
        try:
            plan.MEASURED_XYZ.clear()
            plan.MEASURED_XYZ[153] = (0.0, 0.0, 0.0)
            mine = plan.handle_for_trigger_id(153)
            line = hooklog.console_line(_body(mine))
            self.assertIn("issued=yes", line)
            self.assertIn("provisioned=1", line)
            self.assertIn(f"opaque=0x{mine:04x}", line)
            # A value we did not issue, on the same non-empty plan.
            self.assertIn("issued=no", hooklog.console_line(_body(0x1234)))
        finally:
            plan.MEASURED_XYZ.clear()
            plan.MEASURED_XYZ.update(saved)
        self.assertIn(
            "provisioned=2", hooklog.console_line(_body(0x1234))
        )

    def test_an_unparsed_line_carries_no_annotation_at_all(self):
        # There is no opaque to annotate, and the UNPARSED shape is what
        # GT-228's own grep and the cap test above read.
        line = hooklog.console_line(b"\xff\xee\xdd")
        self.assertNotIn("issued=", line)
        self.assertNotIn("provisioned=", line)

    def test_a_raising_plan_costs_the_annotation_not_the_line(self):
        import types

        name = "pirateforce_foundation.world_m2_survey_plan"
        broken = types.ModuleType(name)
        broken.console_annotation = lambda _handle: (
            (_ for _ in ()).throw(RuntimeError("boom"))
        )
        import pirateforce_foundation as package

        saved_module = sys.modules[name]
        saved_attr = package.world_m2_survey_plan
        try:
            sys.modules[name] = broken
            package.world_m2_survey_plan = broken
            line = hooklog.console_line(_body(0x1234))
        finally:
            sys.modules[name] = saved_module
            package.world_m2_survey_plan = saved_attr
        self.assertIn("opaque=0x1234", line)
        self.assertIn("issued=err", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_a_plan_that_cannot_even_be_imported_costs_the_annotation_only(self):
        # pf-adversary measured the shape this guards: with the plan imported
        # at module scope, a pinned-source drift underneath it took THIS HOOK
        # out of `lane_hooks._discover()` with IMPORT_FAILED -- no
        # registration, no line, and on an attended console that is
        # indistinguishable from "no confirm frame arrived", which GT-228 is
        # allowed to PASS on.  The import is inside the guard now.
        import pirateforce_foundation as package

        name = "pirateforce_foundation.world_m2_survey_plan"
        saved_module = sys.modules[name]
        saved_attr = package.world_m2_survey_plan
        try:
            # No package attribute and a poisoned sys.modules entry is what an
            # import that raised on its way up leaves behind.
            del package.world_m2_survey_plan
            sys.modules[name] = None
            line = hooklog.console_line(_body(0x1234))
        finally:
            sys.modules[name] = saved_module
            package.world_m2_survey_plan = saved_attr
        self.assertIn("opaque=0x1234", line)
        self.assertIn("issued=err provisioned=err", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_this_hook_still_registers_when_the_plan_cannot_be_imported(self):
        # The registration path itself must not depend on the plan module.
        import importlib

        source = (
            ROOT / "src" / "pirateforce_foundation" / "lane_hooks"
            / "lane_a_enter_instance_log.py"
        ).read_text(encoding="utf-8")
        module_scope_imports = [
            line for line in source.splitlines()
            if line.startswith("from ") or line.startswith("import ")
        ]
        self.assertNotIn(
            "from .. import world_m2_survey_plan as plan", module_scope_imports
        )
        # ...and it really does import cleanly with the plan unavailable.
        import pirateforce_foundation as package

        name = "pirateforce_foundation.world_m2_survey_plan"
        saved_module = sys.modules[name]
        saved_attr = package.world_m2_survey_plan
        try:
            del package.world_m2_survey_plan
            sys.modules[name] = None
            importlib.reload(hooklog)
            self.assertIs(hooklog.production_allowed, True)
        finally:
            sys.modules[name] = saved_module
            package.world_m2_survey_plan = saved_attr
            importlib.reload(hooklog)


class TheHookNeverSendsAndNeverRaisesTests(unittest.TestCase):
    def test_it_is_registered_declares_production_allowed_and_survives_discovery(self):
        points = lane_hooks.registered_points()
        self.assertIn(hooklog.POINT, points)
        self.assertGreaterEqual(points[hooklog.POINT], 1)
        self.assertIs(hooklog.production_allowed, True)
        self.assertIs(lane_hooks.module_production_allowed(hooklog.__name__), True)

    def test_the_hook_returns_none_for_every_payload_shape(self):
        for payload in (
            b"",
            b"\x12",
            b"\x12\x34\x12\x0b\x06",
            b"\xff\xff\xff",
            _body(0) + b"\x00" * 400,
        ):
            with self.subTest(payload=payload[:8]):
                self.assertIsNone(
                    hooklog._on_enter_instance(session=object(), payload=payload)
                )

    def test_a_non_bytes_payload_is_refused_loudly_not_raised(self):
        import contextlib
        import io

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = hooklog._on_enter_instance(session=object(), payload="not bytes")
        self.assertIsNone(result)
        console = stderr.getvalue()
        self.assertIn("UNPARSED", console)
        self.assertIn("bad_payload_type=str", console)

    def test_a_bytearray_and_memoryview_payload_both_decode(self):
        body = _body(0x42)
        self.assertEqual(hooklog.decode_opaque(bytes(bytearray(body))), 0x42)
        self.assertEqual(hooklog.decode_opaque(bytes(memoryview(body))), 0x42)


class _FakeSession:
    """Just enough of `runtime.py`'s session shape for `sent_state` to read:
    an ``events`` list, the same one the M2 survey-trial call site appends
    ``m2_survey_trial_sent_<count>`` to."""

    def __init__(self, events=()):
        self.events = list(events)


class TheOneFragmentThatIsAboutThisServer(unittest.TestCase):
    """`sent=`, added in round `16uvmp` after pf-adversary asked what on this
    line distinguishes "we sent a record and the client echoed it" from "we
    have never sent anything and a client sent us a 2".  Nothing did: every
    other fragment is computed from measured XYZ and the scene registry, so a
    client's five bytes could make the line read `issued=yes` on a build with
    no send path at all.

    ROUND `16uvmp` LEFT THIS ANSWERED WITH A REPOSITORY-WIDE CONSTANT
    (``SEND_PATH_STATE``, "unwired"/"wired"), and flagged it as
    `ADVERSARY_PENDING` item 1: a source-level check answers "could a send
    path be reached at all", not "did a frame leave THIS SESSION" -- the
    question a grader actually needs answered, and one no source check can
    answer (a call site can be wired and a given session still never have
    reached it).  The tripwire fired exactly as designed the round chief's
    call site landed (`test_the_state_is_the_repositorys_and_goes_red_
    when_a_call_site_lands`, which lived here and is retired now that its
    one job -- catching that moment -- is done).  `sent_state()`, closed
    this round (`m1wqqy`), answers the real question instead: a count read
    from `session.events`, the same list the call site itself appends to
    on the send path.
    """

    def test_no_session_reads_as_unknown_not_as_a_guess(self):
        for value in (0x0002, 0x0003, 0xA099, 0x1234):
            with self.subTest(value=value):
                self.assertIn("sent=unknown", hooklog.console_line(_body(value)))

    def test_a_session_with_no_sent_events_reads_as_zero(self):
        session = _FakeSession(events=["some_other_event", "m2_survey_trial_refused_no_records"])
        line = hooklog.console_line(_body(0x1234), session)
        self.assertIn("sent=0", line)

    def test_a_session_that_sent_records_reports_the_real_count(self):
        session = _FakeSession(events=["m2_survey_trial_sent_2"])
        line = hooklog.console_line(_body(0x1234), session)
        self.assertIn("sent=2", line)

    def test_multiple_sends_in_one_session_sum(self):
        # CORRECTED (pf-adversary, round `xf6eoi`).  The earlier comment
        # here named the wrong route and called a reading of source a
        # measurement: it said a scene change is what re-arms the trial.
        # `runtime.py:11596`'s condition is `m2_survey_trial_scene_attempted
        # is None OR m2_survey_reconfirmed`, and the second arm -- the
        # deliberate re-arm when the client confirms a scene that was sent
        # unconfirmed -- needs no scene change at all.  So the sum can pass
        # the per-arrival record count on ONE arrival, and the line can read
        # `provisioned=2 ... sent=4`.  That is the designed meaning of a
        # cumulative counter, and `sent_state`'s docstring now says so; what
        # was wrong was the explanation, not the number.
        session = _FakeSession(events=["m2_survey_trial_sent_2", "m2_survey_trial_sent_2"])
        line = hooklog.console_line(_body(0x1234), session)
        self.assertIn("sent=4", line)

    def test_an_object_with_no_events_attribute_reads_as_unknown(self):
        line = hooklog.console_line(_body(0x1234), object())
        self.assertIn("sent=unknown", line)

    def test_an_events_attribute_that_is_not_a_list_or_tuple_reads_as_unknown(self):
        class _Weird:
            events = "not a list"

        line = hooklog.console_line(_body(0x1234), _Weird())
        self.assertIn("sent=unknown", line)

    def test_a_non_string_or_malformed_event_is_never_a_crash(self):
        session = _FakeSession(events=[123, None, "m2_survey_trial_sent_not_a_number", "m2_survey_trial_sent_1"])
        line = hooklog.console_line(_body(0x1234), session)
        self.assertIn("sent=1", line)

    def test_a_container_whose_own_iteration_raises_still_reads_as_unknown(self):
        # pf-adversary, round `m1wqqy`: malformed ENTRIES were already
        # guarded; a container whose `__iter__` itself raises was not, and
        # would have propagated out of this line entirely -- caught by
        # `lane_hooks.fire()`'s outer handler instead, which prints an ERR
        # line rather than any `LANE_A_ENTER_INSTANCE` line at all.
        class _HostileEvents(list):
            def __iter__(self):
                raise RuntimeError("boom")

        session = _FakeSession()
        session.events = _HostileEvents(["m2_survey_trial_sent_2"])
        line = hooklog.console_line(_body(0x1234), session)
        self.assertIn("sent=unknown", line)

    def test_an_events_property_that_raises_still_reads_as_unknown(self):
        # pf-adversary, round `xf6eoi`, MEASURED: `getattr(session,
        # "events", None)` swallows only `AttributeError`, so a session
        # whose `events` is a property that raises went straight out of
        # `console_line` -- the same "prints nothing" failure the hostile
        # `__iter__` case was written to close, one attribute earlier.
        class _RaisingEvents:
            @property
            def events(self):
                raise RuntimeError("boom")

        line = hooklog.console_line(_body(0x1234), _RaisingEvents())
        self.assertIn("sent=unknown", line)

    def test_a_base_exception_from_iteration_is_caught_too(self):
        # `except Exception` missed `BaseException`; a container raising one
        # took the line down.  KeyboardInterrupt/SystemExit stay re-raised
        # on purpose -- see the next test.
        class _HostileEvents(list):
            def __iter__(self):
                raise BaseException("boom")  # noqa: TRY002 - that is the point

        session = _FakeSession()
        session.events = _HostileEvents(["m2_survey_trial_sent_2"])
        self.assertIn("sent=unknown", hooklog.console_line(_body(0x1234), session))

    def test_the_interpreters_own_shutdown_signals_are_not_swallowed(self):
        # A log line is not worth eating a Ctrl-C or a SystemExit; the same
        # shape `lane_a_choose_npc_scene1` already uses for lane B's
        # registry.  Both the attribute read and the iteration are checked.
        class _InterruptingIter(list):
            def __iter__(self):
                raise KeyboardInterrupt

        session = _FakeSession()
        session.events = _InterruptingIter(["m2_survey_trial_sent_2"])
        with self.assertRaises(KeyboardInterrupt):
            hooklog.sent_state(session)

        class _ExitingProperty:
            @property
            def events(self):
                raise SystemExit(2)

        with self.assertRaises(SystemExit):
            hooklog.sent_state(_ExitingProperty())

    def test_a_suffix_that_is_not_a_plain_run_of_ascii_digits_is_skipped(self):
        # pf-adversary, round `xf6eoi`, MEASURED on the old parser:
        # `_-5` gave sent=-5, `_ 7 ` gave 7, `_1_0` gave 10, and an
        # Arabic-Indic digit gave 2.  None is reachable from the wire today
        # -- every append in the tree has a static prefix and an int -- but
        # the old code's own comment claimed the entries are this repo's
        # own, which is an assumption, not a check.
        for suffix in ("-5", " 7 ", "1_0", "٢", "", "+2", "2.0"):
            with self.subTest(suffix=repr(suffix)):
                session = _FakeSession(events=[f"m2_survey_trial_sent_{suffix}"])
                self.assertIn("sent=0", hooklog.console_line(_body(0x1234), session))

    def test_the_hook_itself_passes_the_real_session_through(self):
        import contextlib
        import io

        session = _FakeSession(events=["m2_survey_trial_sent_2"])
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            hooklog._on_enter_instance(session=session, payload=_body(0x0002))
        self.assertIn("sent=2", stderr.getvalue())

    def test_an_unparsed_line_makes_no_claim_about_sending_either(self):
        line = hooklog.console_line(b"\x99\x99")
        self.assertIn("UNPARSED", line)
        self.assertNotIn("sent=", line)


class TheArrivalFragment(unittest.TestCase):
    """`arrival_plan=` -- the second annotation, and the reason it has its own
    guard rather than sharing the plan's.

    Imported at class scope, not relied on to be in `sys.modules` because an
    earlier test happened to run first: pf-adversary measured this class
    erroring with `KeyError` when run on its own or under a test-order
    randomiser.
    """

    def setUp(self):
        from pirateforce_foundation import world_m2_arrival  # noqa: F401

    def test_a_decoded_line_carries_the_arrival_pair(self):
        line = hooklog.console_line(_body(0x1234))
        self.assertIn("arrival_plan=2/2", line)
        # Beside the plan's pair, not instead of it: the two halves of M2
        # have to be readable apart on one line.  GT-228 (R308, PASS) has
        # since left both real targets measured, so provisioned=2 by
        # default; 0x1234 is still not a handle either one was given.
        self.assertIn("issued=no provisioned=2", line)

    def test_it_tracks_the_arrival_module_rather_than_being_a_constant(self):
        import types

        name = "pirateforce_foundation.world_m2_arrival"
        stub = types.ModuleType(name)
        stub.console_annotation = lambda _registry=None: "arrival_plan=1/2"
        import pirateforce_foundation as package

        saved_module = sys.modules[name]
        saved_attr = package.world_m2_arrival
        try:
            sys.modules[name] = stub
            package.world_m2_arrival = stub
            line = hooklog.console_line(_body(0x1234))
        finally:
            sys.modules[name] = saved_module
            package.world_m2_arrival = saved_attr
        self.assertIn("arrival_plan=1/2", line)

    def test_a_broken_arrival_module_costs_its_own_fragment_only(self):
        # The whole reason the guard is separate: an arrival module that
        # cannot be imported must not take `issued=`/`provisioned=` -- which
        # answers a different question off different data -- down with it.
        import pirateforce_foundation as package

        name = "pirateforce_foundation.world_m2_arrival"
        saved_module = sys.modules[name]
        saved_attr = package.world_m2_arrival
        try:
            del package.world_m2_arrival
            sys.modules[name] = None
            line = hooklog.console_line(_body(0x1234))
        finally:
            sys.modules[name] = saved_module
            package.world_m2_arrival = saved_attr
        self.assertIn("arrival_plan=err", line)
        # GT-228 (R308, PASS) has since left both real targets measured, so
        # provisioned=2 by default (see the fragment test's own note above).
        self.assertIn("issued=no provisioned=2", line)
        self.assertIn("opaque=0x1234", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_the_fragment_names_nothing_the_client_sent(self):
        # Same RE-227 nonclaim 3 guard the raw-value test applies, restated
        # for the fragment added this round.
        line = hooklog.console_line(_body(154))
        self.assertNotIn("island", line.lower())
        self.assertNotIn("scene", line.lower())
        self.assertNotIn("trigger", line.lower())
        line.encode("ascii")

    def test_an_unparsed_line_still_carries_no_annotation_at_all(self):
        line = hooklog.console_line(b"\xff\xee\xdd")
        self.assertNotIn("arrival_plan=", line)

    def test_the_independence_is_conditional_and_both_cases_are_pinned(self):
        # pf-adversary asked the right question and the answer has two
        # halves, so both are measured here rather than asserted in prose.
        # `world_m2_arrival` imports `world_m2_survey_plan` AT MODULE SCOPE:
        #   * once both are loaded, breaking the plan costs only its own
        #     fragment -- the arrival module already holds its reference;
        #   * on a COLD boot, where the arrival module has not been imported
        #     yet, an unimportable plan takes the arrival import down with it
        #     and BOTH fragments read err.  That is the case a real server
        #     meets, and the one the docstring's "learns something a single
        #     err would have hidden" must not be read as excluding.
        # In every case the opaque value and the bytes_out marker survive,
        # which is the property both guards exist for.
        import pirateforce_foundation as package

        plan_name = "pirateforce_foundation.world_m2_survey_plan"
        arrival_name = "pirateforce_foundation.world_m2_arrival"
        saved = {
            name: (sys.modules[name], getattr(package, name.split(".")[-1]))
            for name in (plan_name, arrival_name)
        }
        try:
            sys.modules[plan_name] = None
            del package.world_m2_survey_plan
            warm = hooklog.console_line(_body(0x1234))
            sys.modules[arrival_name] = None
            del package.world_m2_arrival
            cold = hooklog.console_line(_body(0x1234))
        finally:
            for name, (module, attr) in saved.items():
                sys.modules[name] = module
                setattr(package, name.split(".")[-1], attr)
        self.assertIn("issued=err provisioned=err", warm)
        self.assertIn("arrival_plan=2/2", warm)
        self.assertIn("issued=err provisioned=err", cold)
        self.assertIn("arrival_plan=err", cold)
        for line in (warm, cold):
            self.assertIn("opaque=0x1234", line)
            self.assertIn("no_responder bytes_out=0", line)


if __name__ == "__main__":
    unittest.main()
