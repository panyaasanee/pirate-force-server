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
        self.assertEqual(self.raw.get("entry_count"), len(self.table))

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
