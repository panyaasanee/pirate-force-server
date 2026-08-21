"""NAMES-FOLD-003 (round 86) - put BOTH halves under pytest, by running the
tools for real and pinning what they produce.

WHY THIS FILE EXISTS
--------------------
Round 85's own lesson, written down in tests/test_vital_id_resolve_scope.py:
*no test module imported tools/pf_vital_id_resolve_static.py, so pytest stayed
green while the tool went red, and the breakage would have surfaced only when a
human ran the release gate by hand.*  NAMES-FOLD-003 adds a second verifier
(tools/pf_vital_thunk_census_static.py) and a section [5] to the first one.
Neither would have been called by anything.  This file calls both.

WHAT IS PINNED, AND WHY EACH PIN IS INDEPENDENT
-----------------------------------------------
A test that only asserts "the tool exits 0" pins nothing the tool does not
already pin about itself.  So this file re-states the load-bearing numbers HERE,
in a second place, from the artifact and the table rather than from the tool's
own constants:

  * half (ก): the names table publishes exactly 38 id_slot_va values on
    v141-inherited rows and leaves exactly 11 null, and four of the 38 slot VAs
    are spelled out below character-for-character;
  * half (ข): the census artifact holds exactly 209 rows, each with a distinct
    slot and a distinct wire id, and it admits nothing;
  * the blind spot is exactly 3 over-long identifiers, 2 of them class names.

If the tool and this file ever disagree, one of them is wrong and the suite says
so - which is the whole point of writing the number twice.

WHAT NEEDS THE CLIENT IMAGE
---------------------------
``ToolRunTests`` executes both verifiers for real (no mocks) and needs the
read-only client image at ../GameClient/GameClient.local.bin, which lives
OUTSIDE the repo.  When it is absent those tests SKIP loudly with the reason in
the message; every other class here is pure stdlib over in-repo files and always
runs.  Neither tool needs capstone, pefile, or any third-party package.

Run just this file:
    python3 -m pytest tests/test_names_fold003_thunk_census.py -q
"""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import textwrap
import unittest
import warnings
from pathlib import Path

from tools.pf_vital_names import load_names_table, wire_id

ROOT = Path(__file__).resolve().parents[1]
THUNK_TOOL = ROOT / "tools" / "pf_vital_name_thunk_static.py"
CENSUS_TOOL = ROOT / "tools" / "pf_vital_thunk_census_static.py"
ARTIFACT = (
    ROOT / "reports" / "PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json"
)
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

# The skip reason must carry the [precondition:...] token - see tests/pf_preconditions.py.
sys.path.insert(0, str(ROOT / "tests"))
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

# ---- half (ก) -------------------------------------------------------------
# 🔴 ERRATUM against the NAMES-FOLD-003 brief: the population of v141-inherited
# rows without a slot was 49, not 38.  38 is how many CLEARED the rule.
LEGACY_TOTAL = 49
LEGACY_WITH_SLOT = 38
LEGACY_WITHOUT_SLOT = 11
TOTAL_PUBLISHED_SLOTS = 287  # 249 before round 86 + these 38

# Four of the 38, spelled out, so a silent renumber cannot pass by count alone.
# ActorAttr and BackpackAttr matter beyond bookkeeping: they are names v141
# always knew and the 327-name tsv never listed.
LEGACY_SLOT_SPOT_CHECKS = {
    "ActorAttr": "0x10334A0",
    "BackpackAttr": "0x103353C",
    "GetWorldInfoVital": "0x1082068",
    "GSCN_RunTimeProtocolReq": "0x1081C90",
}
# The 11 that did not clear it, with the reason.  10 have exactly one
# well-formed thunk but a second, non-registration push of the same literal
# (rule (4)(b) says "the SINGLE push"); 1 has no standalone literal at all.
LEGACY_REFUSED = {
    "StartGameRes": "AMBIGUOUS",
    "TradeZoomVital": "AMBIGUOUS",
    "UpdateAttrVital": "AMBIGUOUS",
    "StorageOpenVital": "AMBIGUOUS",
    "SelectActorVital": "AMBIGUOUS",
    "ItemOperateVital": "NO_LITERAL",
    "LSCN_LoginVitalReq": "AMBIGUOUS",
    "LSCN_LoginVitalRes": "AMBIGUOUS",
    "ItemOperateVitalRes": "AMBIGUOUS",
    "LSCN_SelectServerReq": "AMBIGUOUS",
    "LSCN_SelectServerRes": "AMBIGUOUS",
}

# ---- half (ข) -------------------------------------------------------------
THUNKS_IN_IMAGE = 519
COVERED_BY_TSV = 310
CENSUS_ROWS = 209
CENSUS_ALREADY_NAMED = 17
CENSUS_ADMITTED = 0
LONG_IDENTIFIERS = 3
LONG_CLASS_NAMES = 2


def is_v141_sourced(entry) -> bool:
    return str(entry.get("source", "")).startswith("v141")


def run_tool(path: Path, *args):
    """Run a verifier for real, from the repo root, and hand back the result."""
    return subprocess.run(
        [sys.executable, str(path), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )


def client_available() -> bool:
    if not CLIENT.exists():
        return False
    digest = hashlib.sha256(CLIENT.read_bytes()).hexdigest().upper()
    return digest == CLIENT_SHA


SKIP_REASON = (
    CLIENT_IMAGE.reason
    + f" (expected at {CLIENT} with sha256 {CLIENT_SHA[:16]}...), "
    f"so the two static verifiers cannot run here. This is a SKIP, not a pass: "
    f"the Windows release gate (py -3) is where these must be green."
)


# ==========================================================================
# THE cp874 CONSOLE GATE - one matcher, two callers (round 86, widened in 92)
# ==========================================================================
# Round 86 learned this the hard way: the gate machine's console is code page
# 874.  A character with no mapping there does not degrade into '?', it raises
# UnicodeEncodeError *inside print()* and kills the tool where it stands, having
# reported nothing.  The sandbox writes UTF-8 and stays green, so the sandbox
# cannot see the bug at all.
#
# Round 86 checked this by RUNNING the two NAMES-FOLD-003 verifiers and encoding
# their captured stdout.  That is the strongest form of the check and it stays,
# but it has two holes: it covers only the tools it can run (most tools in this
# repo need the client image, a capture, or a DB copy), and it can only see the
# branches a single run happens to take.  Round 92 found a live trap that both
# holes hid: tools/pf_move_cadence001_headless_replay.py printed U+00D7 and
# U+00B1 on four lines, was never run by any test, and would have died on the
# gate the first time anyone reproduced MOVE-CADENCE-001.
#
# So the runtime check keeps its two tools and a STATIC scan below covers every
# tool in the tree.  The static scan deliberately looks ONLY at string literals
# that can reach a console (print / sys.stdout.write / sys.stderr.write), never
# at the whole file: this project's comments and docstrings are full of Thai,
# that Thai is harmless because it never reaches an encoder, and it is staying.
UNPRINTABLE_HINT = (
    "Use ASCII in anything a tool prints; the words carry the meaning "
    "(x for the multiplication sign, +/- for plus-minus)."
)

CONSOLE_CALLS = ("print",)
CONSOLE_WRITE_TARGETS = ("sys.stdout", "sys.stderr", "stdout", "stderr")


def unencodable_in_cp874(text: str):
    """Return the first character code page 874 cannot encode, or None.

    This is the ONE matcher.  The runtime check feeds it a tool's captured
    stdout; the static check feeds it a string literal out of a print() call.
    Both callers must agree on what "the gate console can show" means, so
    neither gets its own copy of the encode.
    """
    try:
        text.encode("cp874")
    except UnicodeEncodeError as exc:
        return text[exc.start:exc.end], exc.start
    return None


def _is_console_sink(func: ast.AST) -> bool:
    if isinstance(func, ast.Name) and func.id in CONSOLE_CALLS:
        return True
    if isinstance(func, ast.Attribute) and func.attr == "write":
        try:
            target = ast.unparse(func.value)
        except Exception:  # pragma: no cover - ast.unparse is 3.9+
            return False
        return target in CONSOLE_WRITE_TARGETS
    return False


def console_literals(source: str):
    """Yield (lineno, text) for every string a console could receive.

    Covered: string literals anywhere inside a print(...) / sys.stdout.write(...)
    / sys.stderr.write(...) call - which includes f-string pieces, ``%``
    templates and .format() templates, because they are all Constant nodes in
    the call's subtree - plus module-level ``NAME = "..."`` constants handed
    straight to such a call by name (the banner-constant shape).

    NOT covered, and not claimed: text a tool composes at run time out of data
    it reads.  That is what the runtime check on captured stdout is for.
    """
    # Parsing someone else's source re-raises THEIR warnings (two tools carry an
    # invalid '\-' escape).  Those are real but they are not this gate's finding,
    # and a gate that spams unrelated warnings gets ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(source)
    module_strings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_strings[target.id] = (node.value.lineno, node.value.value)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_console_sink(node.func):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                yield sub.lineno, sub.value
            elif isinstance(sub, ast.Name) and sub.id in module_strings:
                lineno, value = module_strings[sub.id]
                yield lineno, value


def scan_tree_for_unprintable(directory: Path):
    """Report every (path, lineno, char, line) a cp874 console would die on."""
    offenders = []
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            literals = list(console_literals(source))
        except SyntaxError:
            continue  # not this check's job to police syntax
        if not literals:
            continue
        lines = source.splitlines()
        for lineno, text in literals:
            hit = unencodable_in_cp874(text)
            if hit is None:
                continue
            char, _offset = hit
            try:
                shown = str(path.relative_to(ROOT))
            except ValueError:  # a trap file staged outside the repo
                shown = str(path)
            offenders.append((
                shown,
                lineno,
                char,
                lines[lineno - 1].strip() if lineno - 1 < len(lines) else "",
            ))
    return offenders


# ==========================================================================
class LegacySlotTableTests(unittest.TestCase):
    """Half (ก), asserted against docs/PF_VITAL_NAMES.json itself."""

    def setUp(self) -> None:
        self.table = load_names_table()
        self.legacy = [e for e in self.table.entries if is_v141_sourced(e)]

    def test_legacy_population_is_49_not_38(self) -> None:
        self.assertEqual(
            len(self.legacy),
            LEGACY_TOTAL,
            f"{LEGACY_TOTAL} entries are inherited from the frozen v141 snapshot. "
            f"The NAMES-FOLD-003 brief said 38; 38 is how many of them CLEARED the "
            f"admission rule, not how many there were.",
        )

    def test_exactly_38_legacy_entries_publish_a_slot(self) -> None:
        with_slot = [e for e in self.legacy if e.get("id_slot_va")]
        without = [e for e in self.legacy if not e.get("id_slot_va")]
        self.assertEqual(
            len(with_slot),
            LEGACY_WITH_SLOT,
            f"round 86 gave an id_slot_va to the {LEGACY_WITH_SLOT} v141-inherited "
            f"names that clear BOTH conditions of rule (4). Re-derive with "
            f"python3 tools/pf_vital_name_thunk_static.py --list LEGACY.",
        )
        self.assertEqual(len(without), LEGACY_WITHOUT_SLOT)

    def test_the_11_refused_names_are_still_null(self) -> None:
        by_name = {e["name"]: e for e in self.legacy}
        for name, tier in LEGACY_REFUSED.items():
            with self.subTest(name=name):
                self.assertIn(name, by_name, f"{name} left the table")
                self.assertIsNone(
                    by_name[name].get("id_slot_va"),
                    f"{name} is {tier} under rule (4)(b) and must NOT carry a slot. "
                    f"If a later round admits it, that round has to amend rule (4)(b) "
                    f"in the JSON header on purpose - not slip a value in here.",
                )

    def test_spot_checked_slot_vas(self) -> None:
        by_name = {e["name"]: e for e in self.table.entries}
        for name, slot in LEGACY_SLOT_SPOT_CHECKS.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["id_slot_va"].upper(), slot.upper())

    def test_every_legacy_name_still_hashes_to_its_id(self) -> None:
        """Condition (a) is untouched by round 86 - prove it, do not assume it."""
        for entry in self.legacy:
            with self.subTest(name=entry["name"]):
                self.assertEqual(wire_id(entry["name"]), entry["id_dec"])

    def test_total_published_slots(self) -> None:
        published = [e for e in self.table.entries if e.get("id_slot_va")]
        self.assertEqual(
            len(published),
            TOTAL_PUBLISHED_SLOTS,
            f"the table should publish {TOTAL_PUBLISHED_SLOTS} id_slot_va values "
            f"(249 after round 85 + 38 from round 86).",
        )
        for entry in published:
            with self.subTest(name=entry["name"]):
                self.assertRegex(entry["id_slot_va"], r"^0x[0-9A-F]+$")

    def test_round86_did_not_change_the_entry_count(self) -> None:
        """Half (ก) was additive on ONE field. It admitted no new name."""
        self.assertEqual(len(self.table), 298)
        self.assertEqual(self.table.raw["entry_count"], 298)


class CensusArtifactTests(unittest.TestCase):
    """Half (ข), asserted against the committed artifact."""

    def setUp(self) -> None:
        self.assertTrue(
            ARTIFACT.exists(),
            f"the 209-class census artifact is missing: {ARTIFACT}. Regenerate with "
            f"python3 tools/pf_vital_thunk_census_static.py --emit {ARTIFACT}",
        )
        self.payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.census = self.payload["census"]

    def test_census_holds_209_rows(self) -> None:
        self.assertEqual(len(self.census), CENSUS_ROWS)
        self.assertEqual(self.payload["counts"]["census_rows"], CENSUS_ROWS)
        self.assertEqual(
            self.payload["counts"]["registration_thunks_in_image"], THUNKS_IN_IMAGE
        )
        self.assertEqual(self.payload["counts"]["covered_by_tsv"], COVERED_BY_TSV)
        self.assertEqual(COVERED_BY_TSV + CENSUS_ROWS, THUNKS_IN_IMAGE)

    def test_every_row_carries_slot_wire_id_and_literal(self) -> None:
        for row in self.census:
            with self.subTest(name=row["name"]):
                self.assertTrue(row["literal_readable"])
                self.assertTrue(row["literal_is_identifier"])
                self.assertRegex(row["id_slot_va"], r"^0x[0-9A-F]{8}$")
                self.assertRegex(row["literal_va"], r"^0x[0-9A-F]{8}$")
                self.assertRegex(row["thunk_va"], r"^0x[0-9A-F]{8}$")
                self.assertEqual(int(row["wire_id"], 16), row["wire_id_dec"])

    def test_wire_ids_are_the_round62_hash_of_the_literal(self) -> None:
        """The census's id column is DERIVED. Derive it again, independently."""
        for row in self.census:
            with self.subTest(name=row["name"]):
                self.assertEqual(wire_id(row["name"]), row["wire_id_dec"])

    def test_slots_and_ids_are_distinct(self) -> None:
        self.assertEqual(len({r["id_slot_va"] for r in self.census}), CENSUS_ROWS)
        self.assertEqual(len({r["wire_id_dec"] for r in self.census}), CENSUS_ROWS)
        self.assertEqual(len({r["name"] for r in self.census}), CENSUS_ROWS)

    def test_census_admitted_nothing_to_the_names_table(self) -> None:
        table = load_names_table()
        self.assertEqual(self.payload["admitted_to_names_table"], CENSUS_ADMITTED)
        named = [r for r in self.census if r["name"] in table.by_name]
        self.assertEqual(
            len(named),
            CENSUS_ALREADY_NAMED,
            f"{CENSUS_ALREADY_NAMED} census classes carry a name the table already "
            f"holds (from v141, independently of their own literal).",
        )
        for row in named:
            with self.subTest(name=row["name"]):
                self.assertEqual(table.by_name[row["name"]]["id_dec"], row["wire_id_dec"])
        for row in self.census:
            if row["name"] in table.by_name:
                continue
            with self.subTest(name=row["name"]):
                self.assertNotIn(
                    row["wire_id_dec"],
                    table.by_id,
                    f"{row['name']} is not in the names table, yet its id is - under a "
                    f"different name. That is a collision the chief must see before "
                    f"anything from this census is admitted.",
                )

    def test_artifact_says_loudly_that_it_is_not_a_name_table(self) -> None:
        doc = "\n".join(self.payload["__doc__"])
        for needle in ("NOT a name table", "docs/PF_VITAL_NAMES.json", "vacuous"):
            with self.subTest(needle=needle):
                self.assertIn(needle.lower(), doc.lower())

    def test_blind_spot_is_measured_not_bounded(self) -> None:
        blind = self.payload["round62_sweep_blind_spot"]
        self.assertEqual(blind["regex"], "[\\x20-\\x7e]{3,48}")
        longs = blind["identifiers_longer_than_48"]
        self.assertEqual(len(longs), LONG_IDENTIFIERS)
        self.assertEqual(
            self.payload["counts"]["identifier_literals_longer_than_48"],
            LONG_IDENTIFIERS,
        )
        for item in longs:
            with self.subTest(name=item["name"][:32]):
                self.assertGreater(item["length"], 48)
                self.assertEqual(len(item["name"]), item["length"])
        table = load_names_table()
        class_names = [i["name"] for i in longs if i["name"] in table.by_name]
        self.assertEqual(
            len(class_names),
            LONG_CLASS_NAMES,
            "2 of the 3 over-long identifiers are class names the table already "
            "holds; the third is linker padding.",
        )


class ToolRunTests(unittest.TestCase):
    """Run both verifiers for real. This is the class round 85 wished it had."""

    @unittest.skipUnless(client_available(), SKIP_REASON)
    def test_thunk_verifier_runs_clean_and_reports_half_alpha(self) -> None:
        result = run_tool(THUNK_TOOL)
        self.assertEqual(
            result.returncode,
            0,
            f"tools/pf_vital_name_thunk_static.py exited {result.returncode}.\n"
            f"{result.stdout[-4000:]}\n{result.stderr[-2000:]}",
        )
        self.assertNotIn("  FAIL  ", result.stdout)
        self.assertIn("[5] NAMES-FOLD-003 half", result.stdout)
        for needle in (
            f"legacy PROVEN      =  {LEGACY_WITH_SLOT}",
            "legacy AMBIGUOUS   =  10",
            "legacy NO_THUNK    =   0",
            "legacy NO_LITERAL  =   1",
            f"all {TOTAL_PUBLISHED_SLOTS} published id_slot_va values",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stdout)

    @unittest.skipUnless(client_available(), SKIP_REASON)
    def test_thunk_verifier_still_reproduces_the_three_round62_pins(self) -> None:
        """The acceptance gate is the licence for every other number. Watch it."""
        result = run_tool(THUNK_TOOL)
        self.assertIn("[0] ACCEPTANCE", result.stdout)
        for name, slot in (
            ("LogoutVital", "0x0108207C"),
            ("DeleteActorVital", "0x01081FD0"),
            ("Channel_LocalTalkMessageVital", "0x01084458"),
        ):
            with self.subTest(name=name):
                self.assertIn(f"PASS  {name}: unique literal", result.stdout)
                self.assertIn(slot, result.stdout)

    @unittest.skipUnless(client_available(), SKIP_REASON)
    def test_census_verifier_runs_clean_against_the_committed_artifact(self) -> None:
        result = run_tool(CENSUS_TOOL)
        self.assertEqual(
            result.returncode,
            0,
            f"tools/pf_vital_thunk_census_static.py exited {result.returncode}.\n"
            f"{result.stdout[-4000:]}\n{result.stderr[-2000:]}",
        )
        self.assertNotIn("  FAIL  ", result.stdout)
        self.assertIn("byte-identical to what this run derives", result.stdout)
        for needle in (
            f"{CENSUS_ROWS} thunks are NOT in the tsv at all",
            f"{COVERED_BY_TSV} thunks are covered by the tsv",
            f"{LONG_IDENTIFIERS} standalone identifier literals",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stdout)

    @unittest.skipUnless(client_available(), SKIP_REASON)
    def test_both_tools_print_nothing_the_windows_console_cannot_encode(self) -> None:
        """Console output must survive code page 874, which is the gate machine.

        This project verifies on two machines and their consoles do not agree.
        The sandbox writes UTF-8 and will print anything; the Windows gate runs
        on code page 874, and a character with no mapping there does not degrade
        into a question mark, it raises UnicodeEncodeError inside print() and
        kills the tool where it stands.  That is not hypothetical: the census
        tool shipped with a red-circle emoji in one heading, was green in the
        sandbox, and on the gate it died at that line having reported no finding
        at all, taking the whole job red with it.

        Asserting on the tool's captured stdout rather than on its source text
        is deliberate.  A source scan would also flag the Thai in the comments
        and the docstrings, which is harmless and staying, and it would miss
        anything the tool composes at run time from data it reads out of the
        image.  What matters is only what actually reaches a console.
        """
        for tool in (THUNK_TOOL, CENSUS_TOOL):
            with self.subTest(tool=tool.name):
                result = run_tool(tool)
                self.assertEqual(result.returncode, 0, result.stdout[-2000:])
                for stream_name in ("stdout", "stderr"):
                    text = getattr(result, stream_name)
                    hit = unencodable_in_cp874(text)
                    if hit is not None:
                        offender, offset = hit
                        line = text[:offset].count("\n") + 1
                        self.fail(
                            # ascii(), not repr(): this message is itself printed
                            # to the gate console, and a message that carries the
                            # offending character would die the same death.
                            f"{tool.name} writes {ascii(offender)} "
                            f"(U+{ord(offender[0]):04X}) to {stream_name} at output "
                            f"line {line}, which code page 874 cannot encode, so "
                            f"this tool raises UnicodeEncodeError on the Windows "
                            f"gate while passing here. " + UNPRINTABLE_HINT
                        )

    @unittest.skipUnless(client_available(), SKIP_REASON)
    def test_census_tool_shares_the_thunk_tools_acceptance_gate(self) -> None:
        """One matcher, one gate, two callers - assert it, do not trust the docstring.

        The claim is about the FILE, not about module objects: the census tool
        must not carry its own copy of the byte template, because a second copy
        is a second thing to keep in step and round 85 spent its whole budget on
        exactly one template being right.
        """
        import inspect

        import tools.pf_vital_name_thunk_static as thunk_tool
        import tools.pf_vital_thunk_census_static as census_tool

        for symbol in ("Image", "run_acceptance", "load_candidates"):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    Path(inspect.getfile(getattr(census_tool, symbol))).resolve(),
                    Path(inspect.getfile(getattr(thunk_tool, symbol))).resolve(),
                    f"{symbol} must come from tools/pf_vital_name_thunk_static.py",
                )
        source = CENSUS_TOOL.read_text(encoding="utf-8")
        self.assertIn("from pf_vital_name_thunk_static import", source)
        # opcode byte strings only - the two call targets are named in the
        # census tool's PROSE (explaining what ID_ASSIGN does), which is fine;
        # what must not exist twice is the template itself.
        for fragment in ("\\x8b\\xc8", "\\x66\\xa3", "\\x66\\x89\\x05", "0xC3"):
            with self.subTest(fragment=fragment):
                self.assertNotIn(
                    fragment,
                    source,
                    "the census tool re-implemented part of the byte template; "
                    "there must be exactly one copy, in the sibling verifier.",
                )
        result = run_tool(CENSUS_TOOL)
        self.assertIn("[0] ACCEPTANCE", result.stdout)
        self.assertIn("PASS  LogoutVital: unique literal", result.stdout)


class Cp874ConsoleGateTests(unittest.TestCase):
    """Round 92: the cp874 gate, widened from 2 named tools to the whole tools/ tree.

    ``ToolRunTests.test_both_tools_print_nothing_the_windows_console_cannot_encode``
    is the strong version of this check - it encodes what the tool REALLY wrote -
    but it can only run the two verifiers, and only down the branches one run
    takes.  Every other tool in this repo needs the client image, an out-of-repo
    capture, or a DB copy, so no test ever ran them and nothing ever looked at
    what they would print.

    That is not theoretical.  tools/pf_move_cadence001_headless_replay.py sat in
    the tree printing U+00D7 (multiplication sign) on three lines and U+00B1
    (plus-minus) on two more.  Neither character exists in code page 874.  The
    tool was green in the sandbox, uncalled by pytest, and would have raised
    UnicodeEncodeError on the Windows gate the first time anyone reproduced
    MOVE-CADENCE-001 - after the run had already done its work, so the job would
    have gone red with no finding.  Round 92 replaced them with "x" and "+/-".

    These tests need no client image and no subprocess, so unlike ToolRunTests
    they always run, on both machines.
    """

    # a gate that truncates its own finding list makes the next person run it
    # twice to learn what else is broken
    maxDiff = None

    FAILURE_HINT = (
        "the lines listed above hand a code-page-874 console a character it "
        "cannot encode, so print() raises UnicodeEncodeError and the tool dies "
        "mid-run on the Windows gate. " + UNPRINTABLE_HINT
    )

    @staticmethod
    def _ascii_lines(offenders):
        """Render the offenders as ascii()-only strings.

        The assertions below compare THESE strings, never the raw tuples: this
        very failure message gets printed on the gate console, and unittest's
        own diff would paste the offending character straight into it.  A
        report that dies of the bug it is reporting helps nobody.
        """
        return [
            f"{path}:{lineno} U+{ord(char):04X} {ascii(char)} in: {ascii(line)}"
            for path, lineno, char, line in offenders
        ]

    def test_no_tool_can_print_a_character_code_page_874_cannot_encode(self) -> None:
        offenders = scan_tree_for_unprintable(ROOT / "tools")
        self.assertEqual(self._ascii_lines(offenders), [], self.FAILURE_HINT)

    def test_no_test_module_can_print_one_either(self) -> None:
        """Same gate over tests/, which is clean today - lock it in while it is.

        A test that BUILDS a non-ASCII payload is fine and there are several
        (emoji, CJK, lone surrogates) - they are wire data, not console output,
        and this scan does not look at them.  What must not happen is one of
        them reaching print().
        """
        offenders = scan_tree_for_unprintable(ROOT / "tests")
        self.assertEqual(self._ascii_lines(offenders), [], self.FAILURE_HINT)

    # ---- traps: a check nobody has watched go red is not a check ------------
    # Every character below is built with chr(), never written as a literal, so
    # that this file's own failure output stays printable on the gate console.
    MULTIPLICATION_SIGN = chr(0x00D7)
    PLUS_MINUS = chr(0x00B1)
    RED_CIRCLE = chr(0x1F534)

    def test_trap_the_matcher_on_the_three_characters_that_actually_bit_us(self) -> None:
        for name, char in (
            ("MULTIPLICATION SIGN", self.MULTIPLICATION_SIGN),
            ("PLUS-MINUS SIGN", self.PLUS_MINUS),
            ("LARGE RED CIRCLE", self.RED_CIRCLE),
        ):
            with self.subTest(name=name):
                hit = unencodable_in_cp874("total " + char + " ok")
                self.assertIsNotNone(hit, f"{name} must be refused by cp874")
                # compare code points, not characters: an assertion that fails
                # here must still be printable on the console it is about.
                self.assertEqual(ord(hit[0]), ord(char))
        # ...and the matcher must NOT cry wolf: ASCII and Thai both encode fine
        # in cp874, which is exactly why the Thai comments in this repo are safe.
        self.assertIsNone(unencodable_in_cp874("plain ascii 1 x5 (+/-1e-4)"))
        self.assertIsNone(unencodable_in_cp874("การทดสอบ"))

    def test_trap_the_scanner_sees_a_planted_print_and_ignores_planted_prose(self) -> None:
        """One source, four shapes: two must be caught, two must be left alone."""
        planted = textwrap.dedent(
            '''
            """Docstring with %(x)s in it - prose, never printed, must be ignored."""
            # comment with %(x)s in it - must be ignored
            BANNER = "banner %(pm)s tolerance"
            def main():
                print("moving flag: 1 %(x)s5")
                print(BANNER)
                sys.stdout.write(f"gap {1} %(x)s {2}")
                unrelated = "held in a variable %(x)s and never printed"
                return unrelated
            '''
        ) % {"x": self.MULTIPLICATION_SIGN, "pm": self.PLUS_MINUS}

        found = sorted(
            (lineno, ord(char))
            for lineno, text in console_literals(planted)
            for char in [(unencodable_in_cp874(text) or (None,))[0]]
            if char is not None
        )
        # dedent leaves line 1 blank, so: 2 docstring, 3 comment, 4 BANNER,
        # 6 print literal, 7 print(BANNER), 8 sys.stdout.write, 9 dead variable.
        # A name handed to print() is reported at the line the string was
        # DEFINED on (4), which is where someone has to go to fix it.
        self.assertEqual(
            found,
            [(4, 0x00B1), (6, 0x00D7), (8, 0x00D7)],
            "the scanner must catch both print() literals, the sys.stdout.write "
            "literal and the banner constant handed to print() by name - and "
            "must leave the docstring, the comment and the dead variable alone",
        )

    def test_trap_the_whole_tree_scan_goes_red_on_a_planted_file(self) -> None:
        """Drive scan_tree_for_unprintable end to end, not just its parts.

        The tree scan is what the gate test above calls.  Green over the real
        tools/ tree proves nothing on its own - it could be green because it
        walks nothing, parses nothing, or swallows the SyntaxError branch.  So
        point it at a directory with one planted tool in it and watch it fire.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            planted_dir = Path(tmp)
            (planted_dir / "pf_planted_trap_tool.py").write_text(
                "print('DB layer: save_position succeeded "
                + self.MULTIPLICATION_SIGN
                + "19')\n",
                encoding="utf-8",
            )
            (planted_dir / "pf_innocent_tool.py").write_text(
                "# ความเห็นภาษาไทย - encodes fine in cp874 and must be ignored\n"
                "print('DB layer: save_position succeeded x19')\n",
                encoding="utf-8",
            )
            offenders = scan_tree_for_unprintable(planted_dir)

        self.assertEqual(len(offenders), 1, self._ascii_lines(offenders))
        path, lineno, char, line = offenders[0]
        self.assertTrue(path.endswith("pf_planted_trap_tool.py"), path)
        self.assertEqual(lineno, 1)
        self.assertEqual(ord(char), 0x00D7)
        self.assertTrue("save_position succeeded" in line, ascii(line))

    def test_trap_the_offending_tool_of_round_92_would_have_been_caught(self) -> None:
        """Rebuild the four lines round 92 fixed and prove the gate refuses them.

        This is the regression pin: if someone reverts the fix in
        tools/pf_move_cadence001_headless_replay.py, the tree scan above goes
        red - and this test proves the tree scan is what would catch it, rather
        than the tree scan merely being green because it looks at nothing.
        """
        reverted = (
            'print(f"moving flag: 1' + self.MULTIPLICATION_SIGN + '{a}")\n'
            'print(f"matches GT-005 AFTER row (' + self.PLUS_MINUS + '1e-4): {b}")\n'
            'print(f"DB layer: save_position succeeded ' + self.MULTIPLICATION_SIGN + '{c}")\n'
            'print(f"DB final row matches GT-005 AFTER (' + self.PLUS_MINUS + '1e-4): {d}")\n'
        )
        caught = [
            unencodable_in_cp874(text)[0]
            for _lineno, text in console_literals(reverted)
            if unencodable_in_cp874(text) is not None
        ]
        self.assertEqual(len(caught), 4, "all four reverted lines must be caught")
        # ...and the ASCII replacements that shipped must still be there.
        # assertTrue(x in s), never assertIn: assertIn's default message pastes
        # the whole container, and that container is a file this test exists
        # because it might contain unprintable characters.  A failure message
        # that cannot be printed on the gate console is worse than no message.
        tool = ROOT / "tools" / "pf_move_cadence001_headless_replay.py"
        shipped = tool.read_text(encoding="utf-8")
        for replacement in ("moving flag: 1 x{", "(+/-1e-4)",
                            "save_position succeeded x{"):
            with self.subTest(replacement=replacement):
                self.assertTrue(
                    replacement in shipped,
                    f"{tool.name} no longer prints {replacement!r}; round 92 put "
                    f"it there to replace a character cp874 cannot encode.",
                )
        leftovers = [
            f"line {lineno} U+{ord(hit[0]):04X}"
            for lineno, text in console_literals(shipped)
            for hit in [unencodable_in_cp874(text)]
            if hit is not None
        ]
        self.assertEqual(leftovers, [], f"{tool.name}: {leftovers}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
