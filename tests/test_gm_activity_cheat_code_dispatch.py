"""The inbound 0x6CEC (Activity_CheatCodeVital) authorization + capture gate.

``tests/test_gm_command_dispatch.py`` proves the same property for 0x51E9.
This file proves it for the SECOND inbound GM-surface vital this lane
answers, and -- the part that is not a copy of that file -- proves the two
things that are only true because the two opcodes share one module:

  * the account rate limit and the capture quota are ONE budget across both
    opcodes, so an authorized-but-hostile account cannot double either by
    alternating opcodes, and
  * a captured 0x6CEC file is distinguishable from a captured 0x51E9 file
    by name and by header, which is the whole reason the P-3 button-capture
    round can tell "this button sent something we do not decode" apart from
    "this button sent nothing" (letter 20260906_0852).

NOT CLAIMED anywhere below: that any real client has ever sent 0x6CEC to
this server.  Both Activity_CheatCodeVital rows in PF_FIELD_VALIDATION.tsv
(W and R) read `observed_frames=0 ... status=NOT_OBSERVED`; these payloads
are built here, from the pinned serializer layout, exactly as the 0x51E9
tests build theirs.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_gm_activity_cheat_code,
)
from pirateforce_foundation.gm.activity_cheat_code_wire import (  # noqa: E402
    ACTIVITY_CHEAT_CODE_VITAL_ID,
)


def _wstring(text: str) -> bytes:
    """One tag-0x48 wide string, the shape PF_A2_STRING_WIRE_TAG_DELTA pins."""
    payload = text.encode("utf-16-le")
    return bytes([0x48]) + struct.pack("<I", len(payload)) + payload


def _payload(field_0x14: int = 7, texts: tuple[str, ...] = ("a", "b", "c", "d", "e")) -> bytes:
    """A structurally valid Activity_CheatCodeVital payload.

    Built from the pinned layout (tag 0x14 + u32, then five tag-0x48 wide
    strings), never from a captured frame -- see this file's docstring.
    """
    assert len(texts) == 5, texts
    body = bytes([0x14]) + struct.pack("<I", field_0x14)
    for text in texts:
        body += _wstring(text)
    return body


class ActivityCheatCodeDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture_root = Path(self.tmp.name) / "capture"
        # Both budgets are process-global (gm/dispatch.py's own documented
        # test-isolation tradeoff) -- start from a known-empty state.
        gm_dispatch.reset_rate_limit_state_for_tests()
        gm_dispatch.reset_capture_quota_state_for_tests()

    def _config(self, gm_accounts_value):
        path = Path(self.tmp.name) / "gm_accounts.json"
        path.write_text(json.dumps({"gm_accounts": gm_accounts_value}))
        return str(path)

    def _handle(self, account="gm1", payload=None, config=None, **kwargs):
        return gm_dispatch.handle_activity_cheat_code_vital(
            account,
            _payload() if payload is None else payload,
            config_path=self._config(["gm1"]) if config is None else config,
            capture_root=self.capture_root,
            **kwargs,
        )

    def _files(self):
        if not self.capture_root.exists():
            return []
        return sorted(p.name for p in self.capture_root.iterdir())

    # ----- the gate itself ------------------------------------------------

    def test_non_gm_account_is_refused_and_nothing_is_written(self):
        outcome = self._handle(account="player1")
        self.assertFalse(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertIsNone(outcome.captured_path)
        self.assertEqual(self._files(), [])

    def test_no_config_at_all_refuses_and_writes_nothing(self):
        missing = str(Path(self.tmp.name) / "does_not_exist.json")
        outcome = self._handle(config=missing)
        self.assertFalse(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_NOT_GM)
        self.assertEqual(self._files(), [])

    def test_malformed_config_refuses_by_name_and_does_not_raise(self):
        path = Path(self.tmp.name) / "broken.json"
        path.write_text("{not json")
        outcome = self._handle(config=str(path))
        self.assertFalse(outcome.authorized)
        self.assertIsNotNone(outcome.refusal_reason)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                gm_dispatch.REFUSAL_LOOKUP_FAILED_PREFIX
            ),
            outcome.refusal_reason,
        )
        self.assertEqual(self._files(), [])

    def test_gm_account_is_captured(self):
        outcome = self._handle()
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.refusal_reason)
        self.assertIsNotNone(outcome.captured_path)
        self.assertEqual(len(self._files()), 1)

    def test_account_name_must_be_a_real_str_not_a_subclass(self):
        class Sneaky(str):
            pass

        with self.assertRaises(ValueError):
            self._handle(account=Sneaky("gm1"))

    def test_payload_must_be_bytes(self):
        with self.assertRaises(TypeError):
            self._handle(payload="not bytes")

    def test_oversized_payload_is_refused_while_the_account_stays_authorized(self):
        big = b"\x00" * (gm_dispatch.MAX_RAW_PAYLOAD_LENGTH + 1)
        outcome = self._handle(payload=big)
        self.assertTrue(outcome.authorized)
        self.assertEqual(
            outcome.refusal_reason, gm_dispatch.REFUSAL_PAYLOAD_TOO_LARGE
        )
        self.assertEqual(self._files(), [])

    def test_a_write_failure_is_named_and_never_raises(self):
        # dispatch.py imported the symbol BY VALUE, so this is the name the
        # code under test actually reads.  The first draft also patched
        # `command_capture.capture_raw_activity_cheat_code`; measured to be
        # a no-op (pf-adversary, round `eu2g1d`, D9) and dropped.
        with mock.patch.object(
            gm_dispatch,
            "capture_raw_activity_cheat_code",
            side_effect=OSError("disk"),
        ):
            outcome = self._handle()
        self.assertTrue(outcome.authorized)
        self.assertIsNone(outcome.captured_path)
        self.assertTrue(
            outcome.refusal_reason.startswith(
                gm_dispatch.REFUSAL_CAPTURE_WRITE_FAILED_PREFIX
            ),
            outcome.refusal_reason,
        )

    # ----- what only the SECOND opcode can prove --------------------------

    def test_the_capture_file_names_and_headers_its_own_opcode(self):
        outcome = self._handle()
        name = outcome.captured_path.name
        self.assertIn(f"0x{ACTIVITY_CHEAT_CODE_VITAL_ID:04X}", name)
        self.assertNotIn("0x51E9", name)
        text = outcome.captured_path.read_text(encoding="utf-8")
        self.assertIn("# Activity_CheatCodeVital raw capture (0x6CEC)", text)
        self.assertNotIn("GM_RunGMCommandVital", text)

    def test_a_decodable_payload_prints_positional_fields_only(self):
        outcome = self._handle(
            payload=_payload(field_0x14=42, texts=("one", "two", "three", "four", "five"))
        )
        text = outcome.captured_path.read_text(encoding="utf-8")
        self.assertIn("# decode: field_0x14=42", text)
        self.assertIn('# decode: text_0x18="one"', text)
        self.assertIn('# decode: text_0x88="five"', text)
        # Positional, never semantic -- the wire module's own rule.
        for invented in ("code_id", "code_name", "arg1"):
            self.assertNotIn(invented, text)

    def test_an_undecodable_payload_is_still_captured_with_the_failure_named(self):
        outcome = self._handle(payload=b"\xff\xff\xff")
        self.assertTrue(outcome.authorized)
        self.assertIsNotNone(outcome.captured_path)
        text = outcome.captured_path.read_text(encoding="utf-8")
        self.assertIn("# decode: FAILED", text)
        # The bytes themselves survive a decoder that disagrees with them.
        self.assertIn("ff ff ff", text.lower())

    def test_both_opcodes_land_in_one_folder_under_distinct_names(self):
        config = self._config(["gm1"])
        cheat = gm_dispatch.handle_activity_cheat_code_vital(
            "gm1", _payload(), config_path=config, capture_root=self.capture_root,
        )
        run = gm_dispatch.handle_gm_run_command_vital(
            "gm1", bytes([0x0B, 0x00]), config_path=config,
            capture_root=self.capture_root,
        )
        self.assertIsNotNone(cheat.captured_path)
        self.assertIsNotNone(run.captured_path)
        self.assertNotEqual(cheat.captured_path, run.captured_path)
        self.assertEqual(
            cheat.captured_path.parent, run.captured_path.parent
        )
        self.assertEqual(len(self._files()), 2)

    def test_the_rate_limit_is_one_budget_across_both_opcodes(self):
        config = self._config(["gm1"])
        # Spend the whole window on 0x51E9 at a fixed clock...
        for _ in range(gm_dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW):
            spent = gm_dispatch.handle_gm_run_command_vital(
                "gm1", bytes([0x0B, 0x00]), config_path=config,
                capture_root=self.capture_root, now_ts=1000.0,
            )
            self.assertIsNone(spent.refusal_reason, spent)
        # ...and 0x6CEC must find it already spent, not get a fresh one.
        outcome = gm_dispatch.handle_activity_cheat_code_vital(
            "gm1", _payload(), config_path=config,
            capture_root=self.capture_root, now_ts=1000.0,
        )
        self.assertTrue(outcome.authorized)
        self.assertEqual(outcome.refusal_reason, gm_dispatch.REFUSAL_RATE_LIMITED)

    def test_the_capture_quota_is_one_budget_across_both_opcodes(self):
        """0x51E9 spending the quota must close the 0x6CEC door.

        THE FIRST CALL HAS TO SUCCEED FOR THIS TO PROVE ANYTHING
        (pf-adversary, round `eu2g1d`, D1).  The first draft patched the
        cap to 1 byte, which refused BOTH calls standalone and charged
        nothing -- it passed unchanged against a mutant with fully separate
        per-opcode budgets, so it proved the opposite of its own name.  The
        cap here is picked from the module's own estimator so exactly one
        call fits and the second cannot, and the first call's success is
        asserted rather than discarded.

        Uses ``_charged_capture_bytes`` (round `40bjg7`, D9), not the bare
        ``_estimate_capture_file_bytes`` this test used before that round:
        both payloads here are small enough that the disk-block floor, not
        the content estimate, is what actually gets charged, so a cap
        derived from the unfloored estimate would refuse the very first
        call and this test would prove nothing about which budget it hit.
        """
        config = self._config(["gm1"])
        run_payload = bytes([0x0B, 0x00])
        cheat_payload = _payload()
        cost_run = gm_dispatch._charged_capture_bytes(len(run_payload), len("gm1"))
        cost_cheat = gm_dispatch._charged_capture_bytes(len(cheat_payload), len("gm1"))
        # THE CAP HAS TO ADMIT EITHER CALL ON ITS OWN AND REFUSE THE PAIR.
        # A cap smaller than one call refuses both standalone and charges
        # nothing, which is how the first TWO drafts of this test passed
        # against a per-opcode-budget mutant (pf-adversary D1, and again on
        # the D1 fix -- the two payloads are different sizes and only the
        # smaller one was measured).
        cap = max(cost_run, cost_cheat) + 1
        self.assertGreaterEqual(cap, cost_run)
        self.assertGreaterEqual(cap, cost_cheat)
        self.assertLess(cap, cost_run + cost_cheat)
        with mock.patch.object(
            gm_dispatch, "MAX_CAPTURED_BYTES_PER_ACCOUNT", cap
        ):
            first = gm_dispatch.handle_gm_run_command_vital(
                "gm1", bytes([0x0B, 0x00]), config_path=config,
                capture_root=self.capture_root,
            )
            # The whole point: the budget was actually SPENT by 0x51E9.
            self.assertIsNone(first.refusal_reason, first)
            self.assertIsNotNone(first.captured_path)
            second = gm_dispatch.handle_activity_cheat_code_vital(
                "gm1", _payload(), config_path=config,
                capture_root=self.capture_root,
            )
        self.assertEqual(
            second.refusal_reason, gm_dispatch.REFUSAL_CAPTURE_QUOTA_EXCEEDED
        )
        self.assertTrue(second.authorized)
        self.assertIsNone(second.captured_path)
        # One file on disk, and it is the 0x51E9 one -- the 0x6CEC call
        # wrote nothing.  (Asserted against a non-empty listing, so it
        # cannot pass by both calls having been refused.)
        self.assertEqual(len(self._files()), 1)
        self.assertIn("0x51E9", self._files()[0])

    def test_a_decoded_string_cannot_forge_extra_header_lines(self):
        """Ported from the 0x51E9 side, which had it and this did not.

        pf-adversary (round `eu2g1d`, D2) deleted `_escape_for_header` from
        ONE of the five string fields and the whole suite stayed green.
        Every decoded string is client-controlled: a newline inside one
        would otherwise forge `# account=` / `# decode:` lines inside the
        header block of a file whose only purpose is to be trusted later.
        """
        forged = 'x"\n# account=root captured_at=19700101T000000Z length=0\n#"'
        for index in range(5):
            with self.subTest(field=index):
                texts = ["ok"] * 5
                texts[index] = forged
                outcome = self._handle(payload=_payload(texts=tuple(texts)))
                self.assertIsNotNone(outcome.captured_path)
                text = outcome.captured_path.read_text(encoding="utf-8")
                header = text.split("\n\n", 1)[0]
                # Exactly one account= line, and it is the real account.
                self.assertEqual(
                    [l for l in header.splitlines() if l.startswith("# account=")],
                    [line for line in header.splitlines()
                     if line.startswith("# account=gm1 ")],
                )
                # The forged text survives, escaped, on its own decode line.
                self.assertIn("\\n", text)

    def test_a_non_gm_account_does_not_even_touch_the_rate_limit_state(self):
        """The gate ORDER, not just the fact that the sink is not called.

        pf-adversary (round `eu2g1d`, D6) swapped the authorization block
        and the rate-limit block in `_authorize_and_capture` and all 15
        tests stayed green -- so nothing defended the module docstring's
        "authorization gate FIRST, before any capture, decode, or log side
        effect".  With the blocks swapped, a non-GM connection's frames
        mutate process-lifetime shared state before anyone asks whether the
        sender is a GM at all.  This is the test that goes red for that.
        """
        gm_dispatch.reset_rate_limit_state_for_tests()
        outcome = self._handle(account="player1")
        self.assertFalse(outcome.authorized)
        self.assertEqual(gm_dispatch._rate_limit_call_history, {})
        # Same for the 0x51E9 entry point, which shares the chain.
        gm_dispatch.handle_gm_run_command_vital(
            "player1", bytes([0x0B, 0x00]),
            config_path=self._config(["gm1"]), capture_root=self.capture_root,
        )
        self.assertEqual(gm_dispatch._rate_limit_call_history, {})

    def test_the_authorization_gate_runs_before_any_write_for_this_opcode_too(self):
        """A non-GM account must never reach the capture sink at all."""
        with mock.patch.object(
            gm_dispatch, "capture_raw_activity_cheat_code"
        ) as sink:
            outcome = self._handle(account="player1")
        sink.assert_not_called()
        self.assertFalse(outcome.authorized)


class ActivityCheatCodeLaneHookTests(unittest.TestCase):
    """The hook module, not the runtime call site chief still has to add.

    `lane_hooks/lane_gm_activity_cheat_code.py` exists because this house's
    convention is that the requester writes the hook and chief adds only
    the `lane_hooks.fire(...)` line -- 0x51E9's runtime branch calls no
    dispatch function directly (pf-adversary, round `eu2g1d`, D12).  These
    tests prove the hook is registered and does what the 0x51E9 hook does;
    they do NOT prove runtime fires it, and cannot until the call site
    exists.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        gm_dispatch.reset_rate_limit_state_for_tests()
        gm_dispatch.reset_capture_quota_state_for_tests()

    def _session(self, token):
        class _Session:
            def __init__(self):
                self.token = token
                self.events = []

        return _Session()

    def test_the_hook_point_is_registered_and_the_module_is_always_on(self):
        self.assertIn(
            "vital_inbound_activity_cheat_code", lane_hooks._HOOKS,
        )
        self.assertTrue(lane_gm_activity_cheat_code.production_allowed)

    def test_a_non_gm_session_gets_a_named_refusal_event_and_no_write(self):
        # The sink is patched rather than the capture root: the handler
        # bound DEFAULT_CAPTURE_ROOT as a default argument at def time, so
        # patching the module attribute would be the same no-op
        # pf-adversary caught at D9.  Patching the sink is what actually
        # proves nothing was written.
        session = self._session("player1")
        with mock.patch.object(
            gm_dispatch, "capture_raw_activity_cheat_code"
        ) as sink:
            lane_gm_activity_cheat_code._on_activity_cheat_code(
                session=session, payload=_payload(),
            )
        sink.assert_not_called()
        self.assertEqual(
            session.events,
            [f"activity_cheat_code_refused_{gm_dispatch.REFUSAL_NOT_GM}"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
