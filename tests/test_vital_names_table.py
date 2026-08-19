"""NAMES-HOME-001 - enforce docs/PF_VITAL_NAMES.json as the single home for
Vital wire id -> class names.

These tests exist so the rule survives whoever is at the keyboard:

  * the table must COVER the frozen v141 snapshot's NAMES dict completely, and
    agree with it name-for-name on every shared id;
  * every entry's name must hash to its own id under the round-62 algorithm.

Consequences, on purpose:
  - Adding a name to current/pf_login_game_server_v141.py (which is byte-frozen
    and must never be edited) turns this file red, and the failure message says
    to put it in docs/PF_VITAL_NAMES.json instead.
  - Typing a name wrong anywhere in the table turns this file red, because the
    id is a hash of the exact characters of the name.

Run just this file:
    python3 -m pytest tests/test_vital_names_table.py -q
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.pf_vital_names import (
    DEFAULT_TABLE,
    DEFAULT_V141,
    VitalNamesError,
    VitalNamesTable,
    cross_check_v141,
    load_names_table,
    parse_v141_names,
    wire_id,
)

FIX_HINT = (
    "FIX IT IN docs/PF_VITAL_NAMES.json. "
    "current/pf_login_game_server_v141.py is a frozen delivery snapshot "
    "(the comparison reference for the rewrite) and must not be edited."
)

# The three ids NAMES-HOME-001 added on top of v141, with the client-binary
# id-slot VA that PF-NAMEID-RESOLVE-001 proved for each.
RESOLVED_ADDITIONS = {
    0x1B40: ("LogoutVital", "0x108207C"),
    0x36DB: ("DeleteActorVital", "0x1081FD0"),
    0xAC52: ("Channel_LocalTalkMessageVital", "0x1084458"),
}

# NAMES-FOLD-002 (round 85) folded 246 names out of the 327-candidate registry
# in pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv, admitting only
# the PROVEN tier of tools/pf_vital_name_thunk_static.py.
FOLD_SOURCE = "NAMES-FOLD-002 (chief round 85)"
FOLD_ENTRY_COUNT = 246
EXPECTED_TOTAL_ENTRIES = 298


# ---------------------------------------------------------------------------
# Validators.  These live at module level, not inside a test method, so that
# the SAME code proves the real table clean and proves that a deliberately
# broken table is rejected.  A rule nobody has watched reject something is not
# a rule.
# ---------------------------------------------------------------------------
def is_v141_sourced(entry) -> bool:
    """True for the 49 names grandfathered in from the frozen v141 snapshot."""
    return str(entry.get("source", "")).startswith("v141")


def slot_evidence_problems(table) -> list:
    """Entries that were added OUTSIDE v141 but carry no id-slot VA.

    docs/PF_VITAL_NAMES.json rule (4)(b): a name that v141 never had is only
    admissible with LITERAL -> SLOT evidence, and the slot VA is how that
    evidence is recorded.  A null slot on such an entry means the name got in
    on a hash match alone, which is exactly the mistake this table exists to
    prevent (many distinct names hash to the same 16-bit id).
    """
    problems = []
    for entry in table.entries:
        if is_v141_sourced(entry):
            continue
        if not entry.get("id_slot_va"):
            problems.append(
                f"{entry['name']} (0x{entry['id_dec']:04X}, source={entry.get('source')!r}) "
                f"has no id_slot_va; a name added outside v141 needs literal->slot evidence"
            )
    return problems


def ordering_problems(entries) -> list:
    """Entries must be stored in ascending id order, with no id used twice."""
    problems = []
    seen = {}
    previous = None
    for position, entry in enumerate(entries):
        ident = entry["id_dec"]
        if previous is not None and ident < previous:
            problems.append(
                f"entry #{position} ({entry['name']}, 0x{ident:04X}) breaks ascending "
                f"id order after 0x{previous:04X}"
            )
        if ident in seen:
            problems.append(
                f"id 0x{ident:04X} used twice: {seen[ident]} and {entry['name']}"
            )
        seen[ident] = entry["name"]
        previous = ident
    return problems


def _table_from(raw) -> VitalNamesTable:
    """Build a table object straight from a dict, no file involved."""
    return VitalNamesTable(raw, Path("<in-memory>"))


class VitalNamesTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = load_names_table()
        self.raw = json.loads(DEFAULT_TABLE.read_text(encoding="utf-8"))
        self.v141_pairs = parse_v141_names()

    # --- the table loads and is internally consistent --------------------
    def test_table_exists_and_loads(self) -> None:
        self.assertTrue(
            DEFAULT_TABLE.exists(),
            f"docs/PF_VITAL_NAMES.json is missing. It is the single source of "
            f"truth for Vital names; it must exist at {DEFAULT_TABLE}.",
        )
        self.assertGreaterEqual(len(self.table), 52)
        self.assertEqual(
            self.raw.get("entry_count"),
            len(self.table),
            "entry_count must equal len(entries); update it in the same edit "
            "that adds or removes a name.",
        )
        self.assertEqual(
            len(self.table),
            EXPECTED_TOTAL_ENTRIES,
            f"the table should hold {EXPECTED_TOTAL_ENTRIES} names "
            f"(49 v141 + 3 PF-NAMEID-RESOLVE-001 + {FOLD_ENTRY_COUNT} NAMES-FOLD-002). "
            f"If a round deliberately added or removed names, re-derive the count with "
            f"python3 tools/pf_vital_name_thunk_static.py and update this pin in the "
            f"same commit - never the other way round.",
        )

    def test_ids_and_names_are_unique(self) -> None:
        ids = [entry["id_dec"] for entry in self.table.entries]
        names = [entry["name"] for entry in self.table.entries]
        self.assertEqual(len(set(ids)), len(ids), f"duplicate id in table. {FIX_HINT}")
        self.assertEqual(
            len(set(names)), len(names), f"duplicate name in table. {FIX_HINT}"
        )

    def test_every_entry_carries_evidence(self) -> None:
        for entry in self.table.entries:
            with self.subTest(name=entry["name"]):
                self.assertTrue(
                    entry["evidence"],
                    f"{entry['name']} has no evidence pointer. Every name in "
                    f"docs/PF_VITAL_NAMES.json must say where it came from "
                    f"(v141 NAMES entry, finding document, or literal->slot proof).",
                )
                self.assertTrue(entry.get("source"), f"{entry['name']} has no 'source'.")

    # --- the header has to keep telling the whole story ------------------
    def test_doc_header_is_self_contained(self) -> None:
        doc = "\n".join(self.raw.get("__doc__", []))
        self.assertTrue(doc, "docs/PF_VITAL_NAMES.json lost its __doc__ header.")
        for needle in (
            "PF_VITAL_NAMES.json",
            "pf_login_game_server_v141.py",
            "0x1B40",
            "0x36DB",
            "0xAC52",
            "tests/test_vital_names_table.py",
        ):
            with self.subTest(needle=needle):
                self.assertIn(
                    needle,
                    doc,
                    f"__doc__ header no longer mentions {needle}; a reader with "
                    f"no context must be able to understand this file alone.",
                )

    # --- hash: name and id must agree, always ----------------------------
    def test_round62_hash_reference_vectors(self) -> None:
        # Independently anchored ids that appear NAMED in the golden corpus.
        for name, expected in (
            ("StartGameReq", 0x1E87),
            ("CreateActorVital", 0x36CF),
            ("LoginVerifyVital", 0x3784),
            ("GetWorldInfoVital", 0x3D4B),
            ("GSCN_LoginProtocol", 0x453A),
            ("GSCN_RunTimeProtocolReq", 0x6E6F),
        ):
            with self.subTest(name=name):
                self.assertEqual(wire_id(name), expected)

    def test_every_entry_hashes_to_its_own_id(self) -> None:
        bad = self.table.hash_mismatches()
        self.assertEqual(
            bad,
            [],
            "these entries in docs/PF_VITAL_NAMES.json have a name that does not "
            "hash to their id under the round-62 algorithm "
            "(id = sum of (signed char)name[i]*(i+1) mod 2^16): "
            + ", ".join(f"{n} declared 0x{d:04X} but hashes to 0x{g:04X}" for n, d, g in bad)
            + ". Either the name is misspelled or the id is wrong. " + FIX_HINT,
        )

    # --- coverage of the frozen v141 snapshot ----------------------------
    def test_v141_snapshot_still_parses(self) -> None:
        self.assertTrue(DEFAULT_V141.exists(), f"missing frozen snapshot {DEFAULT_V141}")
        self.assertGreaterEqual(
            len(self.v141_pairs),
            49,
            "the v141 NAMES parse returned fewer entries than expected; the "
            "cross-check guard would be silently weakened.",
        )

    def test_table_is_a_superset_of_v141_names(self) -> None:
        problems = cross_check_v141(self.table, self.v141_pairs)
        self.assertEqual(
            problems,
            [],
            "docs/PF_VITAL_NAMES.json no longer covers the v141 NAMES table:\n  "
            + "\n  ".join(problems)
            + "\n"
            + FIX_HINT
            + "\nIf you just resolved a new wire id: add it to "
            "docs/PF_VITAL_NAMES.json, not to v141.",
        )

    def test_overlapping_names_match_character_for_character(self) -> None:
        for ident, name, const in self.v141_pairs:
            entry = self.table.by_id.get(ident)
            with self.subTest(id=f"0x{ident:04X}"):
                self.assertIsNotNone(
                    entry,
                    f"0x{ident:04X} ({name}) exists in v141 NAMES[{const or hex(ident)}] "
                    f"but not in docs/PF_VITAL_NAMES.json. {FIX_HINT}",
                )
                self.assertEqual(
                    entry["name"],
                    name,
                    f"0x{ident:04X} is '{entry['name']}' in docs/PF_VITAL_NAMES.json "
                    f"but '{name}' in v141 NAMES. {FIX_HINT}",
                )

    # --- the three names this table exists to hold -----------------------
    def test_resolved_additions_present_with_slot_evidence(self) -> None:
        for ident, (name, slot) in RESOLVED_ADDITIONS.items():
            with self.subTest(id=f"0x{ident:04X}"):
                entry = self.table.by_id.get(ident)
                self.assertIsNotNone(
                    entry,
                    f"0x{ident:04X} ({name}) was resolved by PF-NAMEID-RESOLVE-001 "
                    f"and must stay in docs/PF_VITAL_NAMES.json.",
                )
                self.assertEqual(entry["name"], name)
                self.assertEqual(wire_id(name), ident)
                self.assertEqual(
                    (entry.get("id_slot_va") or "").upper(),
                    slot.upper(),
                    f"{name} lost its client-binary id-slot VA {slot}; a name added "
                    f"outside v141 must keep its literal->slot evidence pointer.",
                )
                self.assertNotIn(
                    ident,
                    {pair[0] for pair in self.v141_pairs},
                    f"0x{ident:04X} appeared inside v141 NAMES. The frozen snapshot "
                    f"must not have been edited; revert it and keep the name in "
                    f"docs/PF_VITAL_NAMES.json.",
                )

    # --- NAMES-FOLD-002 (round 85) ---------------------------------------
    def test_entries_are_sorted_by_id_with_no_duplicates(self) -> None:
        problems = ordering_problems(self.table.entries)
        self.assertEqual(
            problems,
            [],
            "docs/PF_VITAL_NAMES.json entries must stay sorted by id with no id "
            "used twice, so that a diff of this file is readable:\n  "
            + "\n  ".join(problems),
        )

    def test_every_non_v141_entry_carries_a_slot_va(self) -> None:
        problems = slot_evidence_problems(self.table)
        self.assertEqual(
            problems,
            [],
            "these entries were added outside the frozen v141 snapshot but carry no "
            "id_slot_va, so nothing ties the name to the client binary:\n  "
            + "\n  ".join(problems)
            + "\nRe-derive the slot with python3 tools/pf_vital_name_thunk_static.py "
            "or remove the entry. " + FIX_HINT,
        )

    def test_fold_round85_is_present_and_fully_evidenced(self) -> None:
        folded = [e for e in self.table.entries if e.get("source") == FOLD_SOURCE]
        self.assertEqual(
            len(folded),
            FOLD_ENTRY_COUNT,
            f"expected {FOLD_ENTRY_COUNT} entries with source {FOLD_SOURCE!r}; "
            f"found {len(folded)}. Re-derive with "
            f"python3 tools/pf_vital_name_thunk_static.py.",
        )
        for entry in folded:
            with self.subTest(name=entry["name"]):
                self.assertEqual(wire_id(entry["name"]), entry["id_dec"])
                self.assertTrue(
                    entry.get("id_slot_va"),
                    f"{entry['name']} was folded in without an id_slot_va.",
                )
                self.assertIsNone(
                    entry.get("v141_const"),
                    f"{entry['name']} is not a v141 name and must not claim a v141 const.",
                )
                joined = " ".join(entry["evidence"])
                self.assertIn(
                    "pf_vital_name_thunk_static.py",
                    joined,
                    f"{entry['name']} must cite the tool that proved its thunk.",
                )
                self.assertIn(
                    entry["id_slot_va"].lstrip("0x").lstrip("0X").upper(),
                    joined.upper(),
                    f"{entry['name']}'s evidence must quote the id-slot VA it records.",
                )

    def test_folded_entries_never_overwrote_a_v141_name(self) -> None:
        v141_ids = {pair[0] for pair in self.v141_pairs}
        clashes = [
            e["name"]
            for e in self.table.entries
            if e.get("source") == FOLD_SOURCE and e["id_dec"] in v141_ids
        ]
        self.assertEqual(
            clashes,
            [],
            f"these folded entries sit on an id the frozen v141 snapshot already "
            f"names: {clashes}. The fold must never restate a v141 id under a new "
            f"source.",
        )

    def test_doc_header_explains_the_round85_fold(self) -> None:
        doc = "\n".join(self.raw.get("__doc__", []))
        for needle in (
            "NAMES-FOLD-002",
            "pf_vital_name_thunk_static.py",
            "VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv",
            "PROVEN",
            "AMBIGUOUS",
            "NO_THUNK",
            "NO_LITERAL",
        ):
            with self.subTest(needle=needle):
                self.assertIn(
                    needle,
                    doc,
                    f"__doc__ no longer explains {needle}; the header has to tell the "
                    f"whole story of where these names came from and why the rest were "
                    f"kept out.",
                )

    # --- trap tests: the rules above must actually reject bad tables -----
    def _fake_entry(self, name, ident, **over):
        entry = {
            "id": f"0x{ident:04X}",
            "id_dec": ident,
            "name": name,
            "source": FOLD_SOURCE,
            "v141_const": None,
            "id_slot_va": "0x1080000",
            "evidence": ["fabricated for a trap test"],
            "in_golden_corpus": False,
            "notes": None,
        }
        entry.update(over)
        return entry

    def test_trap_hash_mismatch_is_caught(self) -> None:
        """A name that does not hash to its id must be rejected."""
        good = self._fake_entry("LogoutVital", wire_id("LogoutVital"))
        bad = self._fake_entry("LogoutVita1", wire_id("LogoutVital"))  # digit one
        self.assertEqual(_table_from({"entries": [good]}).hash_mismatches(), [])
        self.assertTrue(
            _table_from({"entries": [bad]}).hash_mismatches(),
            "a fabricated name whose hash does not match its id slipped through; "
            "hash_mismatches() is not doing its job.",
        )

    def test_trap_fold_entry_without_slot_va_is_caught(self) -> None:
        """A non-v141 entry with a null id_slot_va must be rejected."""
        good = self._fake_entry("LogoutVital", wire_id("LogoutVital"))
        bad = self._fake_entry("LogoutVital", wire_id("LogoutVital"), id_slot_va=None)
        grandfathered = self._fake_entry(
            "LogoutVital", wire_id("LogoutVital"), id_slot_va=None, source="v141_NAMES"
        )
        self.assertEqual(slot_evidence_problems(_table_from({"entries": [good]})), [])
        self.assertTrue(
            slot_evidence_problems(_table_from({"entries": [bad]})),
            "an entry sourced from the fold with no literal->slot evidence slipped "
            "through; it would rest on a 16-bit hash alone.",
        )
        self.assertEqual(
            slot_evidence_problems(_table_from({"entries": [grandfathered]})),
            [],
            "v141-inherited names are grandfathered and must NOT be flagged for a "
            "missing slot VA; the trap must be specific, not a blanket.",
        )

    def test_trap_duplicate_id_is_caught(self) -> None:
        """The same id twice must be rejected, by the loader and by ordering."""
        entries = [
            self._fake_entry("LogoutVital", 0x1B40),
            self._fake_entry("SomethingElse", 0x1B40),
        ]
        self.assertTrue(
            ordering_problems(entries),
            "two entries sharing an id went unnoticed by ordering_problems().",
        )
        with self.assertRaises(VitalNamesError):
            _table_from({"entries": entries})

    def test_trap_out_of_order_entries_are_caught(self) -> None:
        entries = [
            self._fake_entry("B", 0x3000),
            self._fake_entry("A", 0x1000),
        ]
        self.assertTrue(
            ordering_problems(entries),
            "entries stored out of id order went unnoticed; the file diff would "
            "become unreadable one careless append at a time.",
        )
        self.assertEqual(ordering_problems(list(reversed(entries))), [])

    def test_trap_wrong_entry_count_is_caught(self) -> None:
        """entry_count that disagrees with len(entries) must be rejected."""
        value = copy.deepcopy(self.raw)
        value["entry_count"] = len(value["entries"]) + 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(VitalNamesError):
                load_names_table(path)

    # --- negative tests: the loader really does reject bad tables --------
    def _reject(self, mutate) -> VitalNamesError:
        value = copy.deepcopy(self.raw)
        mutate(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(VitalNamesError) as caught:
                load_names_table(path)
        return caught.exception

    def test_loader_rejects_id_disagreeing_with_id_dec(self) -> None:
        self._reject(lambda v: v["entries"][0].__setitem__("id_dec", 1))

    def test_loader_rejects_missing_evidence(self) -> None:
        self._reject(lambda v: v["entries"][0].__setitem__("evidence", []))

    def test_loader_rejects_stale_entry_count(self) -> None:
        self._reject(lambda v: v.__setitem__("entry_count", 999))

    def test_loader_rejects_duplicate_id(self) -> None:
        def mutate(value):
            clone = copy.deepcopy(value["entries"][0])
            clone["name"] = clone["name"] + "X"
            value["entries"].append(clone)
            value["entry_count"] = len(value["entries"])

        self._reject(mutate)

    def test_dropping_a_v141_name_is_detected(self) -> None:
        """Deleting a shared entry must be caught by the cross-check."""
        value = copy.deepcopy(self.raw)
        victim = value["entries"].pop(0)
        value["entry_count"] = len(value["entries"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            table = load_names_table(path)
        problems = cross_check_v141(table, self.v141_pairs)
        self.assertTrue(problems, f"removing {victim['name']} went unnoticed")
        self.assertIn("PF_VITAL_NAMES.json", problems[0])

    def test_renaming_an_entry_is_detected_twice(self) -> None:
        """A wrong name must trip BOTH the hash check and the v141 agreement."""
        value = copy.deepcopy(self.raw)
        target = next(e for e in value["entries"] if e["name"] == "TeleportVital")
        target["name"] = "TeleportVita1"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            table = load_names_table(path)
        self.assertTrue(table.hash_mismatches(), "hash check missed a renamed entry")
        self.assertTrue(
            cross_check_v141(table, self.v141_pairs),
            "v141 agreement check missed a renamed entry",
        )


if __name__ == "__main__":
    unittest.main()
