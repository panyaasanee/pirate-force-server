"""Pin MP-AUDIT-FOLLOWUP-001's numbers to the client binary they were read from.

MULTIPLAYER-READINESS-AUDIT-001 graded the world-visibility axis D because the
byte `u8tag(0x0B, actor_type)` had no evidence at all.  This milestone enumerates
that byte statically from the read-only client image, so its numbers must not be
hand-typed either.  These tests take the ``DISPATCH_COUNTS`` fenced block out of

``reports/PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.md``

and compare it, key by key, to a live run of
``tools/pf_actor_type_dispatch_static.py``.  If any guard in the verifier drifts,
importing the tool raises ``SystemExit`` and the first test fails; if the guards
hold but a number in the report disagrees with the binary, the comparison tests
fail.  Every number is compared EXACTLY - there is no ">=" rule here, because
none of these numbers is a "how big is the suite today" measurement: they are
all facts about one immutable, hash-pinned binary.

The tests also restate, independently of the report prose, the four load-bearing
conclusions the next round would build on, so that a silent edit to either the
report or the tool cannot quietly change them:

  1. the client knows exactly five actor_type values, 2..6;
  2. actor_type 2 is CNetActor and CMyActor (the local player) derives from it,
     which is what makes 2 the remote-player branch;
  3. ActorAttr binds only to CNetActor and NPCAttr only to CNetNPC, so the Attr
     the server emits today cannot bind to a remote-player actor;
  4. our server has only ever emitted one of the five values.

Re-pinning when a number legitimately moves (a different client build, a server
edit that changes a call-site count): run
``py -3 tools/pf_actor_type_dispatch_static.py --json`` and update the
``DISPATCH_COUNTS`` block in the report in the same change.

These tests import nothing from ``src/``, open no socket, touch no database and
launch no GameClient.  They read one binary and three text files.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

# ../GameClient/GameClient.local.bin is a proprietary binary that is never in
# a fresh clone; every load_tool() test reads it.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

TOOL = ROOT / "tools" / "pf_actor_type_dispatch_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_MPAUDIT_FOLLOWUP001_ACTOR_TYPE_DISPATCH_STATIC_20260818.md"
)
MANIFEST = REPORT.with_suffix(".manifest")
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

DISPATCH_COUNTS_BLOCK = re.compile(r"```json DISPATCH_COUNTS\n(?P<body>.*?)\n```", re.S)

_TOOL_MODULE = None


def load_tool():
    """Execute the verifier once; a drifted guard becomes SystemExit here."""
    global _TOOL_MODULE
    if _TOOL_MODULE is None:
        spec = importlib.util.spec_from_file_location("pf_actor_type_dispatch_static", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _TOOL_MODULE = module
    return _TOOL_MODULE


def report_counts() -> dict:
    match = DISPATCH_COUNTS_BLOCK.search(REPORT.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("the report has no ```json DISPATCH_COUNTS block")
    return json.loads(match.group("body"))


class ArtifactsExistTests(unittest.TestCase):
    """The four files of this milestone must ship together."""

    def test_report_manifest_tool_and_client_all_exist(self):
        for path in (REPORT, MANIFEST, TOOL, CLIENT):
            with self.subTest(path=path.name):
                if path is CLIENT:
                    # Only the client image may be absent on a clone; the three
                    # tracked files must exist everywhere.  See tests/pf_preconditions.py.
                    CLIENT_IMAGE.require(self)
                self.assertTrue(path.is_file(), path)

    def test_the_report_carries_a_machine_readable_counts_block(self):
        counts = report_counts()
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts["measured_at_head"], "f286945")

    def test_the_manifest_pins_the_client_binary_by_hash(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("GameClient.local.bin", text)
        self.assertIn(CLIENT_SHA, text)


# Every test below runs the verifier, and the verifier reads the client image
# at import - nothing here can run without it.  See tests/pf_preconditions.py.
@CLIENT_IMAGE.skip_unless_present()
class VerifierRunsCleanTests(unittest.TestCase):
    """Every guard in the verifier must hold against the pinned binary."""

    def test_the_verifier_imports_without_exiting(self):
        tool = load_tool()
        self.assertEqual(tool.GUARDS_FAILED, [], tool.GUARDS_FAILED)

    def test_the_verifier_read_the_pinned_client_image(self):
        self.assertEqual(load_tool().sha, CLIENT_SHA)

    def test_the_verifier_actually_asserted_something(self):
        tool = load_tool()
        self.assertGreaterEqual(tool.GUARDS_TOTAL, 100)
        self.assertEqual(tool.GUARDS_TOTAL, len(tool.RESULTS))


class ReportMatchesTheBinaryTests(unittest.TestCase):
    """Every number printed in the report is the number the verifier counted."""

    # The two comparisons need the live COUNTS, which come off the client
    # image; the prose test below reads only the report and must keep running.
    # See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_every_reported_key_exists_in_the_live_counts(self):
        reported = report_counts()
        live = load_tool().COUNTS
        self.assertEqual(sorted(reported), sorted(live))

    @CLIENT_IMAGE.skip_unless_present()
    def test_every_reported_value_matches_exactly(self):
        reported = report_counts()
        live = load_tool().COUNTS
        for key in sorted(reported):
            with self.subTest(key=key):
                self.assertEqual(reported[key], live[key])

    def test_the_prose_headline_guard_count_matches_the_counts_block(self):
        text = REPORT.read_text(encoding="utf-8")
        total = report_counts()["guards_total"]
        self.assertIn("%d guards" % total, text)


# The five classes below all read the client image through load_tool(); the
# binary is proprietary and never in a clone.  See tests/pf_preconditions.py.
@CLIENT_IMAGE.skip_unless_present()
class DispatchShapeTests(unittest.TestCase):
    """Conclusion 1: the client knows exactly five actor_type values, 2..6."""

    def test_exactly_five_branches(self):
        tool = load_tool()
        self.assertEqual(len(tool.BRANCHES), 5)
        self.assertEqual(sorted(tool.BRANCHES), [2, 3, 4, 5, 6])

    def test_the_jump_table_holds_exactly_those_five_branch_heads(self):
        tool = load_tool()
        table = [tool.dw(tool.JUMP_TABLE + 4 * i) for i in range(5)]
        self.assertEqual(table, [tool.BRANCH_ENTRY[t] for t in (2, 3, 4, 5, 6)])

    def test_the_range_check_rebases_by_two_and_caps_at_four(self):
        tool = load_tool()
        instructions = tool.dmap(tool.FACTORY, 0x60)
        self.assertEqual(instructions[0x4469C8], ("movzx", "eax, byte ptr [eax + 0x10]"))
        self.assertEqual(instructions[0x4469CC], ("add", "eax, -2"))
        self.assertEqual(instructions[0x4469D1], ("cmp", "eax, 4"))
        self.assertEqual(instructions[0x4469D4], ("ja", hex(tool.FACTORY_DEFAULT)))

    def test_out_of_range_values_build_no_actor(self):
        tool = load_tool()
        instructions = tool.dmap(tool.FACTORY, 0x1C0)
        self.assertEqual(instructions[0x4469CF], ("xor", "esi, esi"))
        self.assertEqual(instructions[tool.FACTORY_DEFAULT], ("mov", "eax, esi"))

    def test_actor_type_is_one_byte_at_record_offset_0x10(self):
        tool = load_tool()
        self.assertEqual(tool.rd(tool.SET_ACTOR_TYPE, 10).hex(), "8a442404884110c20400")


@CLIENT_IMAGE.skip_unless_present()
class RemotePlayerBranchTests(unittest.TestCase):
    """Conclusion 2: actor_type 2 is CNetActor and CMyActor derives from it."""

    def test_branch_two_builds_cnetactor(self):
        tool = load_tool()
        self.assertEqual(tool.BRANCHES[2][0], "CNetActor")
        self.assertEqual(tool.cstr(tool.BRANCHES[2][6]), ".?AVCNetActor@@")

    def test_branch_three_builds_cmyactor_the_local_player(self):
        tool = load_tool()
        self.assertEqual(tool.BRANCHES[3][0], "CMyActor")
        self.assertEqual(tool.cstr(tool.BRANCHES[3][6]), ".?AVCMyActor@@")

    def test_cmyactor_derives_from_cnetactor(self):
        tool = load_tool()
        self.assertEqual(tool.TOKEN_PARENTS[tool.BRANCHES[3][7]], tool.BRANCHES[2][7])

    def test_cnetnpc_is_a_sibling_of_cnetactor_not_an_ancestor(self):
        tool = load_tool()
        self.assertEqual(
            tool.TOKEN_PARENTS[tool.BRANCHES[4][7]], tool.TOKEN_PARENTS[tool.BRANCHES[2][7]]
        )
        self.assertNotEqual(tool.BRANCHES[4][7], tool.BRANCHES[2][7])

    def test_only_one_local_player_may_exist(self):
        tool = load_tool()
        instructions = tool.dmap(tool.FACTORY, 0x1C0)
        self.assertEqual(instructions[0x4469F7], ("cmp", "dword ptr [0x1032ec4], esi"))
        self.assertEqual(instructions[0x4469FD], ("jne", hex(tool.FACTORY_DEFAULT)))


@CLIENT_IMAGE.skip_unless_present()
class AttrClassGateTests(unittest.TestCase):
    """Conclusion 3: the Attr the server emits today cannot bind to actor_type 2."""

    def test_actorattr_gates_on_cnetactor_only(self):
        tool = load_tool()
        self.assertEqual(tool.ATTR_BINDS["ActorAttr"][4], (tool.BRANCHES[2][7],))

    def test_npcattr_gates_on_cnetnpc_only(self):
        tool = load_tool()
        self.assertEqual(tool.ATTR_BINDS["NPCAttr"][4], (tool.BRANCHES[4][7],))

    def test_the_two_gates_are_different_classes(self):
        tool = load_tool()
        self.assertNotEqual(tool.ATTR_BINDS["ActorAttr"][4], tool.ATTR_BINDS["NPCAttr"][4])

    def test_movementattr_gates_on_the_common_ancestor_so_it_binds_everywhere(self):
        tool = load_tool()
        common = tool.TOKEN_PARENTS[tool.BRANCHES[2][7]]
        self.assertEqual(tool.ATTR_BINDS["MovementAttr"][4], (common,))
        self.assertEqual(tool.TOKEN_PARENTS[tool.BRANCHES[4][7]], common)

    def test_basicattr_binds_to_nothing(self):
        tool = load_tool()
        self.assertEqual(tool.rd(tool.ATTR_BINDS["BasicAttr"][3], 3).hex(), "c20400")

    def test_every_attr_id_is_reproduced_from_its_name_literal(self):
        tool = load_tool()
        for name, spec in tool.ATTR_BINDS.items():
            with self.subTest(attr=name):
                self.assertEqual(tool.name_hash(name), spec[0])


@CLIENT_IMAGE.skip_unless_present()
class NameSourceTests(unittest.TestCase):
    """Question 4: the on-screen name comes from the bound Attr, not from login."""

    def test_the_two_actor_families_expose_different_attr_slots(self):
        tool = load_tool()
        self.assertEqual(tool.rd(0x44C630, 7).hex(), "8b8148030000c3")  # [+0x348]
        self.assertEqual(tool.rd(0x45CD20, 7).hex(), "8b8158030000c3")  # [+0x358]
        self.assertEqual(tool.dw(tool.BRANCHES[2][4] + 0x74), 0x44C630)
        self.assertEqual(tool.dw(tool.BRANCHES[4][4] + 0x74), 0x45CD20)

    def test_getname_reads_the_wstring_at_attr_plus_0x28(self):
        tool = load_tool()
        self.assertEqual(
            tool.dmap(0x4549E0, 0x40)[0x4549F4], ("lea", "ecx, [eax + 0x28]")
        )
        self.assertEqual(
            tool.dmap(0x45BB40, 0x40)[0x45BB54], ("lea", "ecx, [eax + 0x28]")
        )

    def test_the_board_update_bails_out_when_no_attr_is_bound(self):
        tool = load_tool()
        update = tool.dmap(tool.NAMEBOARD_UPDATE, 0x80)
        self.assertEqual(update[0x5BD380], ("test", "eax, eax"))
        self.assertEqual(update[0x5BD382], ("je", hex(tool.NAMEBOARD_BAILOUT)))

    def test_label_name_is_fed_attr_plus_0x28(self):
        tool = load_tool()
        update = tool.dmap(tool.NAMEBOARD_UPDATE, 0x600)
        self.assertEqual(update[0x5BD628], ("add", "edi, 0x28"))
        self.assertEqual(update[0x5BD633], ("mov", "ecx, dword ptr [esi + 0x54]"))

    def test_the_widget_literals_are_the_ones_the_report_names(self):
        tool = load_tool()
        for offset, (widget, literal) in tool.WIDGETS.items():
            with self.subTest(widget=widget):
                self.assertEqual(tool.wstr(literal), widget)
        self.assertEqual(tool.wstr(tool.BOARD_TEMPLATE), "board01")


@CLIENT_IMAGE.skip_unless_present()
class ServerCrossCheckTests(unittest.TestCase):
    """Conclusion 4: our server has only ever emitted one of the five values."""

    def test_v141_emits_exactly_one_actor_type(self):
        tool = load_tool()
        self.assertEqual(tool.V141_TYPES, [4])

    def test_the_untried_values_are_the_other_four(self):
        counts = load_tool().COUNTS
        self.assertEqual(counts["actor_types_never_emitted_by_us"], [2, 3, 5, 6])

    def test_the_remote_player_value_is_one_of_the_untried_ones(self):
        counts = load_tool().COUNTS
        self.assertIn(counts["remote_player_actor_type"], counts["actor_types_never_emitted_by_us"])


class ReportDisciplineTests(unittest.TestCase):
    """The report must keep the three evidence levels separate and claim nothing more."""

    def test_the_report_separates_byte_proof_inference_and_guess(self):
        text = REPORT.read_text(encoding="utf-8")
        for marker in ("byte-proof", "structural inference", "guess"):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_the_report_states_the_proposed_grade_and_marks_it_a_proposal(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("D → B", text)
        self.assertIn("proposal", text)

    def test_the_report_makes_no_runtime_or_original_server_claim(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("Nothing was executed", text)
        self.assertIn("No claim about the ORIGINAL server", text)

    def test_the_report_does_not_call_v141_the_original_server(self):
        text = REPORT.read_text(encoding="utf-8").lower()
        self.assertNotIn("v141, the original server", text)
        self.assertNotIn("original server (v141", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
