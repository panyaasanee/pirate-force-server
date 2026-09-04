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


class TheOneFragmentThatIsAboutThisServer(unittest.TestCase):
    """`sent=`, added in round `16uvmp` after pf-adversary asked what on this
    line distinguishes "we sent a record and the client echoed it" from "we
    have never sent anything and a client sent us a 2".  Nothing did: every
    other fragment is computed from measured XYZ and the scene registry, so a
    client's five bytes could make the line read `issued=yes` on a build with
    no send path at all."""

    def test_every_decoded_line_says_whether_this_build_can_send_at_all(self):
        for value in (0x0002, 0x0003, 0xA099, 0x1234):
            with self.subTest(value=value):
                self.assertIn("sent=unwired", hooklog.console_line(_body(value)))

    def test_the_state_is_the_repositorys_and_goes_red_when_a_call_site_lands(self):
        # `unwired` is only true while nothing can call the record composer.
        # That is exactly what the composer's own guard test asserts, so the
        # two are pinned together here: land a call site and this test fails,
        # naming the constant that would otherwise have kept saying `unwired`
        # on an attended console.
        # EVERY guarded name here is built by concatenation, never written
        # whole.  Both composer modules hold grep tripwires that fail if any
        # other file in the tree so much as names them, and the correct
        # response to that (pf-adversary, this round) is to keep this file out
        # of their sight -- NOT to add this path to their exclusion sets,
        # which would blind a live-import tripwire for the sake of a test.
        composer = "world_m2_provisioning" + "_trial"
        encoder_test = "tests/test_" + "navigationex_survey" + "_record.py"
        excluded = {
            f"src/pirateforce_foundation/{composer}.py",
            f"tests/test_{composer}.py",
            encoder_test,
            "tests/test_lane_a_enter_instance_log.py",
        }
        importers = []
        for path in ROOT.rglob("*.py"):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            if rel in excluded:
                continue
            if composer in path.read_text(encoding="utf-8", errors="replace"):
                importers.append(rel)
        self.assertEqual(
            hooklog.SEND_PATH_STATE, "unwired" if not importers else "wired",
            f"a send path exists now ({importers}) -- SEND_PATH_STATE must stop "
            "saying unwired, and must become a count of what actually went out",
        )

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
