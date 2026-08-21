"""RESOLVE-SCOPE-001 (round 85) - put tools/pf_vital_id_resolve_static.py under
pytest, and pin the SCOPE of its sections [2]/[3] rather than only its numbers.

WHY THIS FILE EXISTS
--------------------
NAMES-FOLD-002 grew docs/PF_VITAL_NAMES.json from 52 to 298 entries.  Sections
[2]/[3] of the resolver selected their targets as "every id in the table that
v141 never had", a phrasing that happened to name three ids when it was written
and named 249 afterwards - so the tool started asserting, of 246 folded names,
that they "appear UNNAMED in the golden corpus", which was never claimed and is
not true.  The tool went red.

**No test module imported the tool**, so pytest stayed green and the breakage
would have surfaced only when a human ran the release gate by hand.  That is the
failure mode this file closes: from now on the resolver runs under pytest, with
its scope re-derived independently here, so "the tool is red" and "the suite is
red" are the same event.

WHAT IS ASSERTED WITHOUT ANY THIRD-PARTY PACKAGE
------------------------------------------------
``ScopeRuleTests`` and ``ScopeTrapTests`` never touch capstone and never open
the client image.  They lift the pinned constants and the ``resolve_scope()``
function OUT of the tool's own source with ``ast`` (real code from the real
file, executed - not a copy, not a mock, not a re-implementation) and run them
against the real docs/PF_VITAL_NAMES.json plus the real frozen v141 snapshot.
The trap tests then doctor the table in memory and prove the guards would FIRE:
a fourth resolved id breaks the count pin, and a provenance/corpus disagreement
breaks the two-way cross-check.

WHAT NEEDS capstone AND THE CLIENT IMAGE
-----------------------------------------
``ToolRunTests`` executes the whole verifier for real (no mocks, no stubs) and
asserts exit code 0, an empty FAILS list and exactly three section-[2] targets.
It needs ``capstone`` (the tool disassembles the registration thunks) and the
read-only client image at ``../GameClient/GameClient.local.bin``, which lives
outside the repo.  When either is missing these tests SKIP - loudly, with the
reason in the skip message - and the pure-stdlib classes above still run.  A
whole-file silent skip is exactly what let the drift hide, so there is none.

Run just this file:
    python3 -m pytest tests/test_vital_id_resolve_scope.py -q
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "pf_vital_id_resolve_static.py"
TABLE_JSON = ROOT / "docs" / "PF_VITAL_NAMES.json"
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

sys.path.insert(0, str(ROOT))
from tools.pf_vital_names import (  # noqa: E402  (path juggling above)
    VitalNamesTable,
    load_names_table,
    parse_v141_names,
)

# The skip reason must carry the [precondition:...] token - see tests/pf_preconditions.py.
sys.path.insert(0, str(ROOT / "tests"))
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

TOOL_SRC = TOOL.read_text(encoding="utf-8")

#: module-level constants this file lifts out of the tool and pins
PINNED_NAMES = (
    "RESOLVE_SOURCE_PREFIX",
    "RESOLVE_TARGET_COUNT",
    "RESOLVE_TARGET_IDS",
    "FOLD_SOURCE_PREFIX",
    "FOLD_ENTRY_MIN",
    "V141_SOURCE",
    "V141_ENTRY_COUNT",
    "TABLE_ENTRY_MIN",
    "SEM",
)


def load_scope_pieces():
    """Execute ONLY the pins and ``resolve_scope()`` out of the tool's source.

    The tool is a script: importing it runs the whole verifier and needs
    capstone.  Parsing it with ``ast`` and executing just these top-level
    statements gives the genuine code under test on a bare stdlib interpreter.
    """
    tree = ast.parse(TOOL_SRC, filename=str(TOOL))
    namespace: dict = {}
    seen = set()
    for node in tree.body:
        keep = False
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(name in PINNED_NAMES for name in names):
                keep, seen = True, seen | set(names)
        elif isinstance(node, ast.FunctionDef) and node.name == "resolve_scope":
            keep, seen = True, seen | {"resolve_scope"}
        if keep:
            block = ast.Module(body=[node], type_ignores=[])
            exec(compile(block, str(TOOL), "exec"), namespace)  # noqa: S102
    missing = (set(PINNED_NAMES) | {"resolve_scope"}) - seen
    if missing:
        raise AssertionError(
            f"{TOOL.name} no longer defines {sorted(missing)} at module level. "
            "RESOLVE-SCOPE-001 requires the section [2]/[3] scope to be a named, "
            "pinned, testable thing - do not inline it back into the script body."
        )
    return namespace


SCOPE = load_scope_pieces()
V141_PAIRS = parse_v141_names()
V141_IDS = {ident for ident, _name, _const in V141_PAIRS}


def doctored_table(mutate):
    """Return a VitalNamesTable built from a MUTATED copy of the real JSON.

    Nothing is written to disk; docs/PF_VITAL_NAMES.json is opened read-only.
    """
    raw = copy.deepcopy(json.loads(TABLE_JSON.read_text(encoding="utf-8")))
    mutate(raw)
    raw.pop("entry_count", None)
    return VitalNamesTable(raw, TABLE_JSON)


class ScopeRuleTests(unittest.TestCase):
    """Pure stdlib. The scope of sections [2]/[3] is the claim, not the table."""

    def setUp(self):
        self.table = load_names_table()

    def test_pins_are_the_published_numbers(self):
        self.assertEqual(SCOPE["RESOLVE_TARGET_COUNT"], 3,
                         "PF-NAMEID-RESOLVE-001 resolved THREE bare-hex corpus ids")
        self.assertEqual(tuple(sorted(SCOPE["RESOLVE_TARGET_IDS"])),
                         (0x1B40, 0x36DB, 0xAC52))
        self.assertEqual(SCOPE["V141_ENTRY_COUNT"], 49,
                         "v141 is byte-frozen; its NAMES count cannot move")
        self.assertEqual(SCOPE["FOLD_ENTRY_MIN"], 246,
                         "NAMES-FOLD-002 admitted 246 names in round 85")
        self.assertEqual(
            SCOPE["TABLE_ENTRY_MIN"],
            SCOPE["V141_ENTRY_COUNT"] + SCOPE["RESOLVE_TARGET_COUNT"]
            + SCOPE["FOLD_ENTRY_MIN"],
            "the table floor must stay the sum of its three buckets, so it is "
            "impossible to bump one number without saying which bucket grew",
        )

    def test_v141_snapshot_still_parses_to_the_pinned_count(self):
        self.assertEqual(len(V141_IDS), SCOPE["V141_ENTRY_COUNT"])

    def test_scope_selects_exactly_the_three_resolved_ids(self):
        corpus_side, source_side = SCOPE["resolve_scope"](self.table, V141_IDS)
        self.assertEqual(corpus_side, source_side,
                         "corpus membership and the provenance field must agree")
        self.assertEqual(len(corpus_side), SCOPE["RESOLVE_TARGET_COUNT"])
        self.assertEqual(tuple(corpus_side), tuple(sorted(SCOPE["RESOLVE_TARGET_IDS"])))

    def test_sem_tokens_cover_every_target(self):
        corpus_side, _ = SCOPE["resolve_scope"](self.table, V141_IDS)
        self.assertEqual(sorted(SCOPE["SEM"]), corpus_side,
                         "section [3] must have an expected hypothesis token for "
                         "every section [2] target, so none can be skipped")

    def test_folded_names_are_out_of_scope_and_carry_slot_evidence(self):
        corpus_side, _ = SCOPE["resolve_scope"](self.table, V141_IDS)
        fold = [ident for ident, entry in self.table.by_id.items()
                if str(entry.get("source", "")).startswith(SCOPE["FOLD_SOURCE_PREFIX"])]
        self.assertGreaterEqual(len(fold), SCOPE["FOLD_ENTRY_MIN"])
        self.assertFalse(set(fold) & set(corpus_side),
                         "a folded registry name is not a golden-corpus resolution")
        no_slot = [f"0x{i:04X}" for i in fold if not self.table.by_id[i].get("id_slot_va")]
        self.assertEqual(no_slot, [],
                         "every NAMES-FOLD-002 entry is admitted on literal->slot "
                         "evidence, so id_slot_va may never be null")

    def test_the_scope_rule_is_written_down_in_the_tool_header(self):
        head = ast.get_docstring(ast.parse(TOOL_SRC)) or ""
        self.assertIn("SCOPE OF SECTIONS [2] AND [3]", head)
        for phrase in ("golden corpus", "RESOLVE_TARGET_COUNT", "NAMES-FOLD-002"):
            self.assertIn(phrase, head,
                          f"the tool's own docstring must explain the scope ({phrase})")


class ScopeTrapTests(unittest.TestCase):
    """Prove the pins would FIRE. A guard nobody has seen fail is a decoration."""

    def test_a_fourth_resolved_id_breaks_the_count_pin(self):
        def add_one(raw):
            raw["entries"].append({
                "id": "0x1234", "id_dec": 0x1234, "name": "TRAP_NotARealName",
                "source": "PF-NAMEID-RESOLVE-001 (trap)", "v141_const": None,
                "id_slot_va": "0x1000000", "evidence": ["trap"],
                "in_golden_corpus": True, "notes": "in-memory trap, never written",
            })
        table = doctored_table(add_one)
        corpus_side, source_side = SCOPE["resolve_scope"](table, V141_IDS)
        self.assertEqual(corpus_side, source_side)
        self.assertEqual(len(corpus_side), SCOPE["RESOLVE_TARGET_COUNT"] + 1)
        self.assertNotEqual(len(corpus_side), SCOPE["RESOLVE_TARGET_COUNT"],
                            "a newly resolved corpus id MUST turn the tool red")

    def test_provenance_and_corpus_flag_disagreeing_is_detected(self):
        def unflag(raw):
            for entry in raw["entries"]:
                if entry["id_dec"] == 0x36DB:
                    entry["in_golden_corpus"] = False
        table = doctored_table(unflag)
        corpus_side, source_side = SCOPE["resolve_scope"](table, V141_IDS)
        self.assertNotEqual(corpus_side, source_side,
                            "the two-way cross-check must catch a table whose "
                            "provenance and corpus flag disagree")
        self.assertIn(0x36DB, source_side)
        self.assertNotIn(0x36DB, corpus_side)

    def test_a_folded_name_cannot_sneak_into_scope_by_provenance_alone(self):
        def relabel(raw):
            for entry in raw["entries"]:
                if str(entry["source"]).startswith(SCOPE["FOLD_SOURCE_PREFIX"]):
                    entry["source"] = "PF-NAMEID-RESOLVE-001 (trap relabel)"
                    break
        table = doctored_table(relabel)
        corpus_side, source_side = SCOPE["resolve_scope"](table, V141_IDS)
        self.assertNotEqual(corpus_side, source_side)
        self.assertEqual(len(corpus_side), SCOPE["RESOLVE_TARGET_COUNT"],
                         "the corpus side of the rule is what defines the claim")


def _why_skipped():
    """Return None when the real tool can run here, else the loud reason."""
    if importlib.util.find_spec("capstone") is None:
        return ("capstone is not installed in this environment; "
                "tools/pf_vital_id_resolve_static.py disassembles the registration "
                "thunks and cannot run without it. The pure-stdlib scope tests in "
                "this file still ran.")
    if not CLIENT.is_file():
        return (CLIENT_IMAGE.reason + ". The pure-stdlib scope "
                "tests in this file still ran.")
    return None


SKIP_WHY = _why_skipped()

_RUN = {}


def run_tool():
    """Execute the verifier for real, once. Returns (module, stdout, exit_code)."""
    if not _RUN:
        spec = importlib.util.spec_from_file_location(
            "pf_vital_id_resolve_static_under_test", TOOL)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        argv, cwd = sys.argv[:], os.getcwd()
        buffer = io.StringIO()
        code = None
        try:
            os.chdir(ROOT)
            # one argument only: the pinned capture corpus stays authoritative
            sys.argv = [str(TOOL), str(CLIENT)]
            with redirect_stdout(buffer):
                spec.loader.exec_module(module)
        except SystemExit as exc:      # the tool always exits at the end
            code = exc.code
        finally:
            sys.argv = argv
            os.chdir(cwd)
        _RUN["module"], _RUN["out"], _RUN["code"] = module, buffer.getvalue(), code
    return _RUN["module"], _RUN["out"], _RUN["code"]


@unittest.skipIf(SKIP_WHY is not None, SKIP_WHY or "")
class ToolRunTests(unittest.TestCase):
    """The real tool, really executed, against the real image and corpus."""

    def test_the_verifier_exits_clean(self):
        module, out, code = run_tool()
        self.assertEqual(module.FAILS, [], f"guards drifted:\n{out}")
        self.assertEqual(code, 0, f"exit {code}\n{out}")
        self.assertIn("PASS - all guards reproduced", out)

    def test_it_read_the_pinned_client_image(self):
        module, _out, _code = run_tool()
        self.assertEqual(module.EXPECT_SHA, CLIENT_SHA)

    def test_section_two_has_exactly_three_targets(self):
        module, _out, _code = run_tool()
        self.assertEqual(len(module.RESOLVED), SCOPE["RESOLVE_TARGET_COUNT"])
        self.assertEqual(
            tuple(sorted(wid for wid, _n, _s in module.RESOLVED)),
            tuple(sorted(SCOPE["RESOLVE_TARGET_IDS"])))

    def test_it_actually_asserted_something(self):
        _module, out, _code = run_tool()
        self.assertGreater(out.count("  PASS  "), 40,
                           "a green run with almost no guards is not a green run")
        self.assertEqual(out.count("  FAIL  "), 0)

    def test_the_scope_is_printed_where_a_human_will_see_it(self):
        _module, out, _code = run_tool()
        self.assertIn("SCOPE:", out)
        self.assertIn("pf_vital_name_thunk_static.py", out,
                      "the run must say where the folded names' evidence lives, so "
                      "nobody reads the narrowed scope as dropped coverage")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
