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

import hashlib
import json
import subprocess
import sys
import unittest
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
    f"the read-only client image is not at {CLIENT} with sha256 {CLIENT_SHA[:16]}..., "
    f"so the two static verifiers cannot run here. This is a SKIP, not a pass: "
    f"the Windows release gate (py -3) is where these must be green."
)


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
                    try:
                        text.encode("cp874")
                    except UnicodeEncodeError as exc:
                        offender = text[exc.start:exc.end]
                        line = text[:exc.start].count("\n") + 1
                        self.fail(
                            f"{tool.name} writes {offender!r} "
                            f"(U+{ord(offender[0]):04X}) to {stream_name} at output "
                            f"line {line}, which code page 874 cannot encode, so "
                            f"this tool raises UnicodeEncodeError on the Windows "
                            f"gate while passing here. Use ASCII in anything the "
                            f"tool prints; the words carry the meaning."
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
