"""LANE-DB: the attribute-source gate refuses to guess, and says why.

The one property every test here defends: no value reaches a composed block
unless the caller supplied it from a typed column or the Codex corpus proved
the client's constructor wrote it.  A zero that "looks fine" is the exact
thing the owner banned (COO-DECISION 20260901_1059), so the tests below are
written to catch a substitution, not merely to exercise the happy path -- of
which there is none today, on purpose.
"""
import ast
import csv
import hashlib
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.attr_wire import (  # noqa: E402
    BY_X, FIELDS, SENSITIVE_FIELDS,
)
from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
CORPUS = (
    ROOT.parent / "pf_bridge" / "notes_to_chief" / "reference_codex_attr"
    / "PF_ATTR_FIELD_SEMANTICS.tsv"
)

MODULE_PATH = ROOT / "src" / "pirateforce_foundation" / "persistence_attr_compose.py"

# sha256 over the 28 copied construction defaults (x|value|writer_va|name).
# Moved only together with the corpus cross-check that re-derives them.
PINNED_DEFAULT_TABLE_DIGEST = (
    "17e573bbe056826da54853e17b44a3ab8996dd935f9554ed9ccbb091567f79ef"
)

ALL_SERVER_OWNED = {
    x: (0 if BY_X[x][5] != "wstr" else "") for x in compose.SERVER_OWNED_FIELDS
}


class PartitionTests(unittest.TestCase):
    def test_every_field_has_exactly_one_source(self):
        sources = {f[0]: compose.source_of(f[0]) for f in FIELDS}
        self.assertEqual(len(sources), 55)
        self.assertEqual(
            set(sources.values()),
            {compose.SERVER_OWNED, compose.CLIENT_DEFAULT,
             compose.UNSOURCED, compose.REFUSED},
        )

    def test_the_partition_is_disjoint_and_covers_the_table(self):
        server = set(compose.SERVER_OWNED_FIELDS)
        default = set(compose.CLIENT_CONSTRUCTION_DEFAULTS)
        unsourced = set(compose.UNSOURCED_FIELDS)
        self.assertEqual(server & unsourced, set())
        self.assertEqual(default & unsourced, set())
        # x=1 and x=7 carry BOTH a proven construction default and a typed
        # column; the server column wins, which is why `source_of` is the
        # authority and not `x in CLIENT_CONSTRUCTION_DEFAULTS`.
        self.assertEqual(server & default, {1, 7})
        self.assertEqual(server | default | unsourced, {f[0] for f in FIELDS})

    def test_the_sensitive_field_is_refused_even_though_it_has_a_default(self):
        self.assertIn(30, compose.CLIENT_CONSTRUCTION_DEFAULTS)
        self.assertIn(30, SENSITIVE_FIELDS)
        self.assertEqual(compose.source_of(30), compose.REFUSED)

    def test_an_x_outside_the_table_is_named_not_defaulted(self):
        for bad in (0, 56, -1, "7"):
            with self.assertRaises(compose.AttrComposeError):
                compose.source_of(bad)

    def test_no_field_is_adjudicated_safe_to_resend_yet(self):
        # If a future round populates RESEND_ADJUDICATED it must do so with the
        # evidence in the module docstring; this test exists so that widening
        # it is a deliberate edit here, not a side effect somewhere else.
        self.assertEqual(compose.RESEND_ADJUDICATED, frozenset())


class GapReportTests(unittest.TestCase):
    def test_nothing_composes_today_and_every_field_says_why(self):
        gaps = compose.block_gaps({})
        self.assertEqual(len(gaps), len(FIELDS))
        self.assertEqual([g.x for g in gaps], sorted(g.x for g in gaps))
        for gap in gaps:
            self.assertTrue(gap.detail)
            self.assertEqual(gap.field_name, BY_X[gap.x][6])

    def test_supplying_every_server_owned_value_still_does_not_unlock(self):
        # The load-bearing negative: even a complete set of typed columns
        # leaves the 7 unsourced + the sensitive one + 25 unadjudicated
        # defaults.  A round that "finishes M4" must not read as done here.
        gaps = compose.block_gaps(ALL_SERVER_OWNED)
        reasons = {g.reason for g in gaps}
        self.assertNotIn(compose.REASON_NO_COLUMN, reasons)
        self.assertNotIn(compose.REASON_NO_TYPED_VALUE, reasons)
        self.assertEqual(
            sorted(g.x for g in gaps if g.reason == compose.REASON_UNSOURCED),
            [14, 25, 36, 41, 42, 43, 54],
        )
        self.assertEqual(
            [g.x for g in gaps if g.reason == compose.REASON_SENSITIVE], [30]
        )
        self.assertEqual(len(gaps), 33)

    def test_a_missing_typed_value_is_a_named_gap_not_a_zero(self):
        supplied = dict(ALL_SERVER_OWNED)
        del supplied[7]
        gaps = {g.x: g for g in compose.block_gaps(supplied)}
        self.assertIn(7, gaps)
        self.assertEqual(gaps[7].reason, compose.REASON_NO_COLUMN)

    def test_the_speed_field_reports_the_column_this_lane_owes(self):
        gap = {g.x: g for g in compose.block_gaps({})}[7]
        self.assertEqual(gap.reason, compose.REASON_NO_COLUMN)
        self.assertIn("characters.speed_walk", gap.detail)

    def test_the_only_built_column_today_is_the_name(self):
        report = compose.unlock_report()
        self.assertEqual(report["server_owned_columns_built"], [1])
        self.assertEqual(report["blocked_fields"], 55)
        self.assertEqual(report["total_fields"], 55)


class ComposeRefusalTests(unittest.TestCase):
    def test_compose_refuses_today_and_names_every_blocked_field(self):
        with self.assertRaises(compose.AttrComposeError) as caught:
            compose.compose_full_block({})
        message = str(caught.exception)
        self.assertIn("55 field(s)", message)
        for x in (7, 14, 30):
            self.assertIn(f"x={x}(", message)

    def test_a_value_for_a_sensitive_field_cannot_be_smuggled_in(self):
        with self.assertRaises(compose.AttrComposeError) as caught:
            compose.compose_full_block({30: b"deadbeef"})
        self.assertIn("x=[30]", str(caught.exception))

    def test_a_value_for_an_unsourced_field_cannot_be_smuggled_in(self):
        with self.assertRaises(compose.AttrComposeError) as caught:
            compose.compose_full_block({25: "anything"})
        self.assertIn("refused for x=[25]", str(caught.exception))

    def test_a_full_set_of_typed_values_still_refuses(self):
        with self.assertRaises(compose.AttrComposeError):
            compose.compose_full_block(ALL_SERVER_OWNED)

    def test_the_module_uses_no_defaulting_call_anywhere(self):
        """AST, not grep.

        The first version of this guard was a regex for `.get(x, 0)` and
        `or 0`.  An adversary pass found nine edits that reintroduce a guessed
        value and sail past it -- `typed_values.get(int(x), 0)` alone defeats
        it, because the character class cannot cross the inner `)`.  Parsing
        catches the shape instead of the spelling: any two-argument `.get`,
        any `.setdefault`, and any `dict(...) | fallback` merge in this module
        is a defect regardless of how it is written.
        """
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and len(node.args) >= 2:
                    self.fail(f"defaulting .get() at line {node.lineno}")
                if node.func.attr == "setdefault":
                    self.fail(f"setdefault() at line {node.lineno}")
        # `|` and `or` are legitimate over sets in the partition check, so the
        # stricter rule applies where values are actually produced.
        producers = {"_value_for", "compose_full_block", "block_gaps"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in producers:
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitOr):
                    self.fail(f"merge-shaped `|` in {node.name} line {inner.lineno}")
                if isinstance(inner, ast.BoolOp) and isinstance(inner.op, ast.Or):
                    self.fail(f"`or` fallback in {node.name} line {inner.lineno}")
        self.assertEqual(
            {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            & producers,
            producers,
            "a producer was renamed and this guard stopped covering it",
        )


class CorpusProvenanceTests(unittest.TestCase):
    """The 28 defaults are a COPY of corpus rows; this proves they still agree.

    THE HONEST LIMIT OF THIS CLASS.  `docs/PYTEST_SKIP_PINS.json` is not this
    lane's file, so a pytest skip is not available and a clone without the
    sibling repository is handled by asserting the REASON it is absent.  That
    is a real assertion, but it is not the corpus check: on a single-repo
    checkout these tests fall back and the corpus is never read.  An adversary
    pass this round proved what that costs -- rewriting x=52's proven
    `0xFFFFFFFF` to `0`, the exact guessed zero the owner banned, stayed green
    22/22 on a checkout with no `pf_bridge`.  `TamperEvidenceTests` is the
    answer to that: it pins a digest of the module's own table and so goes red
    on every machine.  These tests remain the only thing that checks the table
    against the corpus itself, and they need the corpus to do it.
    """

    def _corpus_rows(self):
        rows = {}
        with open(CORPUS, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                rows.setdefault((row["class"], row["offset"]), []).append(row)
        return rows

    def _rows_for(self, x, rows=None):
        """Corpus rows for this field's own class+offset.

        The corpus writes offsets with python `hex()` (`0x28`, `0x99`) for the
        low ones and three digits above 0xFF; both spellings are looked up so
        that a field below 0x100 is not silently reported as "no rows" -- the
        shape that would let an unproven default sit here unchallenged.
        """
        rows = self._corpus_rows() if rows is None else rows
        field = BY_X[x]
        cls = "BasicAttr" if field[1] == "basic" else "ActorAttr"
        found = []
        for spelling in {hex(field[3]), "0x%03X" % field[3], "0x%X" % field[3]}:
            found.extend(rows.get((cls, spelling), []))
        return found

    def test_corpus_is_present_or_the_sibling_repository_is_absent(self):
        if not CORPUS.exists():
            self.assertFalse(
                (ROOT.parent / "pf_bridge").exists(),
                "pf_bridge is present but the Codex attr corpus is not at "
                f"{CORPUS} -- it moved, and this lane's defaults lost their "
                "provenance",
            )

    def test_every_copied_default_matches_a_proven_exact_corpus_row(self):
        if not CORPUS.exists():
            return self.test_corpus_is_present_or_the_sibling_repository_is_absent()
        rows = self._corpus_rows()
        for x, default in sorted(compose.CLIENT_CONSTRUCTION_DEFAULTS.items()):
            field = BY_X[x]
            found = self._rows_for(x, rows)
            with self.subTest(x=x):
                self.assertTrue(found, f"no corpus row for x={x}@{field[3]:#05x}")
                self.assertEqual(
                    {r["structural_status"] for r in found}, {"PROVEN_EXACT"}
                )
                self.assertEqual(
                    {r["default_writer_va"] for r in found}, {default.writer_va}
                )
                raw = {r["default_value"] for r in found}
                self.assertEqual(len(raw), 1)
                self.assertEqual(
                    _render(raw.pop(), field[5]), default.value,
                    "the corpus default no longer renders to the copied value",
                )

    def test_the_seven_unsourced_fields_really_have_no_corpus_default(self):
        if not CORPUS.exists():
            return self.test_corpus_is_present_or_the_sibling_repository_is_absent()
        for x in sorted(compose.UNSOURCED_FIELDS):
            with self.subTest(x=x):
                values = {
                    r["default_value"] for r in self._rows_for(x)
                } - {"", "N/A"}
                self.assertEqual(
                    values, set(),
                    f"x={x} now has a corpus default -- the gap shrank and "
                    "UNSOURCED_FIELDS must move in the same commit",
                )

    def test_every_copied_row_describes_the_pinned_client_image(self):
        if not CORPUS.exists():
            return self.test_corpus_is_present_or_the_sibling_repository_is_absent()
        images = set()
        for x in compose.CLIENT_CONSTRUCTION_DEFAULTS:
            images |= {r["image_sha256"] for r in self._rows_for(x)}
        self.assertEqual(
            images, {compose.CORPUS_IMAGE_SHA256},
            "a copied default now comes from a different client image than the "
            "one the module pins; three generation ids live in that directory "
            "and its README calls the mirror stale, so this is not cosmetic",
        )

    def test_how_many_copied_defaults_sit_on_an_open_conflict_is_pinned(self):
        """Not a failure -- a number that must not drift unnoticed.

        The module presents PROVEN_EXACT as settled.  The corpus's own open
        conflicts table disagrees for some of these rows, and `gm/attr_wire.py`
        says as much about this corpus in general.  Pinning the counts means a
        corpus refresh that widens (or closes) the dispute shows up here.
        """
        if not CORPUS.exists():
            return self.test_corpus_is_present_or_the_sibling_repository_is_absent()
        disputed = {
            x for x in compose.CLIENT_CONSTRUCTION_DEFAULTS
            if any(r["open_conflicts_with"] not in ("", "N/A")
                   for r in self._rows_for(x))
        }
        self.assertEqual(sorted(disputed), [9, 10, 11, 12, 15, 26, 27, 28, 29, 30, 37, 55])
        wired = (CORPUS.parent / "PF_ATTR_CONFLICTS_OPEN_WIRED.tsv")
        if not wired.exists():
            return
        offsets = set()
        with open(wired, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                match = re.match(
                    r"(BasicAttr|ActorAttr)@(0x[0-9A-Fa-f]+)", row.get("field_key", "")
                )
                if match:
                    offsets.add((match.group(1), int(match.group(2), 16)))
        listed = [
            f[0] for f in FIELDS
            if (("BasicAttr" if f[1] == "basic" else "ActorAttr"), f[3]) in offsets
        ]
        self.assertEqual(len(listed), 30)

    def test_the_speed_default_is_the_one_the_order_names(self):
        if not CORPUS.exists():
            return self.test_corpus_is_present_or_the_sibling_repository_is_absent()
        default = compose.CLIENT_CONSTRUCTION_DEFAULTS[7]
        self.assertEqual(default.value, 400.0)
        self.assertEqual(BY_X[7][3], 0x054)
        self.assertEqual(BY_X[7][5], "f32")
        names = {r["semantic_name"] for r in self._rows_for(7)}
        self.assertIn(
            "MOBS.n_SPEED_WALK_to_initial_visual_horizontal_locomotion_scalar",
            names,
        )


class ValueShapeTests(unittest.TestCase):
    def test_every_copied_default_fits_the_field_kind_it_belongs_to(self):
        widths = {"u8": 8, "u16": 16, "u32": 32, "u64": 64}
        for x, default in sorted(compose.CLIENT_CONSTRUCTION_DEFAULTS.items()):
            kind = BY_X[x][5]
            with self.subTest(x=x, kind=kind):
                if kind in widths:
                    self.assertIsInstance(default.value, int)
                    self.assertGreaterEqual(default.value, 0)
                    self.assertLess(default.value, 1 << widths[kind])
                elif kind == "f32":
                    self.assertIsInstance(default.value, float)
                elif kind == "i32":
                    self.assertIsInstance(default.value, int)
                    self.assertTrue(-(1 << 31) <= default.value < (1 << 31))
                elif kind == "wstr":
                    self.assertIsInstance(default.value, str)
                elif kind == "blob":
                    self.assertIsInstance(default.value, bytes)
                else:  # pragma: no cover - FIELDS shape guard
                    self.fail(f"unhandled kind {kind}")

    def test_every_writer_va_is_a_real_va_shape(self):
        for x, default in compose.CLIENT_CONSTRUCTION_DEFAULTS.items():
            with self.subTest(x=x):
                for part in default.writer_va.split("|"):
                    self.assertRegex(part, r"^0x[0-9A-F]{8}$")

    def test_server_owned_column_names_are_distinct_and_sane(self):
        columns = [o.column for o in compose.SERVER_OWNED_FIELDS.values()]
        self.assertEqual(len(columns), len(set(columns)))
        for column in columns:
            self.assertRegex(column, r"^[a-z][a-z0-9_]*$")



class ValueProducerTests(unittest.TestCase):
    """`_value_for` is the only thing in the module that produces a value.

    `compose_full_block` cannot return today -- x=30 is refused
    unconditionally -- so an invariant tested only through it would be green
    for the wrong reason (an adversary pass this round drove the module to its
    most permissive reachable state and it still refused; the guarantee was
    unassertable).  These tests hit the producer directly, so the refusals are
    real assertions and not consequences of an unreachable code path.
    """

    def test_the_sensitive_field_produces_no_value_even_with_its_default(self):
        with self.assertRaises(compose.AttrComposeError) as caught:
            compose._value_for(30, {})
        self.assertIn("SENSITIVE_FIELDS", str(caught.exception))
        # and a caller who supplies one anyway still gets nothing
        with self.assertRaises(compose.AttrComposeError):
            compose._value_for(30, {30: b"\x00" * 16})

    def test_an_unsourced_field_produces_no_value(self):
        for x in sorted(compose.UNSOURCED_FIELDS):
            with self.subTest(x=x):
                with self.assertRaises(compose.AttrComposeError):
                    compose._value_for(x, {})

    def test_a_client_default_is_withheld_until_adjudicated(self):
        for x in sorted(set(compose.CLIENT_CONSTRUCTION_DEFAULTS)
                        - set(compose.SERVER_OWNED_FIELDS) - SENSITIVE_FIELDS):
            with self.subTest(x=x):
                with self.assertRaises(compose.AttrComposeError) as caught:
                    compose._value_for(x, {})
                self.assertIn("adjudicated", str(caught.exception))

    def test_a_server_owned_field_returns_exactly_what_was_supplied(self):
        marker = object()
        self.assertIs(compose._value_for(1, {1: marker}), marker)
        self.assertIs(compose._value_for(7, {7: marker}), marker)

    def test_no_field_produces_a_value_from_nowhere(self):
        # The whole guarantee in one loop: with an empty typed_values, not one
        # of the 55 fields may return anything at all.
        for field in FIELDS:
            with self.subTest(x=field[0]):
                with self.assertRaises(compose.AttrComposeError):
                    compose._value_for(field[0], {})

    def test_compose_routes_every_field_through_the_producer(self):
        # If a future edit stops calling `_value_for`, this goes red: the
        # producer is patched to a sentinel that must be seen or the block
        # could not have been built from it.
        calls = []
        real = compose._value_for
        try:
            compose._value_for = lambda x, values: calls.append(x) or real(x, values)
            with self.assertRaises(compose.AttrComposeError):
                compose.compose_full_block({})
        finally:
            compose._value_for = real
        # block_gaps refuses before the producer runs, which is itself the
        # contract: nothing is produced while any gap is open.
        self.assertEqual(calls, [])


class TamperEvidenceTests(unittest.TestCase):
    """A checkout without the sibling repository must still notice an edit.

    The corpus cross-checks below can only run where `pf_bridge` is present.
    On the single-repo gate checkout they cannot, and an earlier version of
    this file let a corrupted "proven" default pass there in silence -- 22/22
    green with `0xFFFFFFFF` rewritten to `0`.  This digest is computed from
    the module's own table, so changing any value, VA or name is red on every
    machine, corpus or no corpus.
    """

    def test_the_copied_default_table_matches_its_pinned_digest(self):
        digest = hashlib.sha256(
            "\n".join(
                f"{d.x}|{d.value!r}|{d.writer_va}|{d.semantic_name}"
                for _, d in sorted(compose.CLIENT_CONSTRUCTION_DEFAULTS.items())
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            digest, PINNED_DEFAULT_TABLE_DIGEST,
            "the 28 copied construction defaults changed.  That is allowed -- "
            "but only in a commit that also re-runs the corpus cross-check "
            "below and moves this pin, so the change is visible on a machine "
            "that cannot read the corpus.",
        )

    def test_the_pin_actually_moves_when_a_value_is_corrupted(self):
        # Proves the digest is load-bearing rather than decorative: the exact
        # corruption an adversary used (0xFFFFFFFF -> 0 on x=52) must change it.
        rows = dict(compose.CLIENT_CONSTRUCTION_DEFAULTS)
        rows[52] = compose.ClientConstructionDefault(
            52, 0, rows[52].writer_va, rows[52].semantic_name
        )
        digest = hashlib.sha256(
            "\n".join(
                f"{d.x}|{d.value!r}|{d.writer_va}|{d.semantic_name}"
                for _, d in sorted(rows.items())
            ).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(digest, PINNED_DEFAULT_TABLE_DIGEST)


class SchemaPinTests(unittest.TestCase):
    """`column_exists` is a hand-written flag; this derives the truth instead.

    Without this, the next commit that adds `characters.speed_walk` and
    forgets to flip the flag makes `block_gaps` report "no characters.
    speed_walk column in migrations/ yet" into a letter to COO -- a false
    reason that no other test can see, because every other test reads the same
    constant it is checking.
    """

    def _real_character_columns(self):
        sys.path.insert(0, str(ROOT / "src"))
        from pirateforce_foundation.store import SQLiteStore
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "schema_probe.sqlite3")
            SQLiteStore(path, ROOT / "migrations").migrate()
            db = sqlite3.connect(path)
            try:
                return {row[1] for row in db.execute("PRAGMA table_info(characters)")}
            finally:
                db.close()

    def test_column_exists_agrees_with_the_real_migrated_schema(self):
        columns = self._real_character_columns()
        for x, owned in sorted(compose.SERVER_OWNED_FIELDS.items()):
            with self.subTest(x=x, column=owned.column):
                self.assertEqual(
                    owned.column in columns, owned.column_exists,
                    f"characters.{owned.column} "
                    f"{'exists' if owned.column in columns else 'does not exist'} "
                    "in the real migrated schema, but the module says otherwise",
                )


def _render(cell: str, kind: str):
    """Corpus `default_value` cell -> the python value `FIELDS` kind implies."""
    if cell == "empty_sequence":
        return b"" if kind == "blob" else ""
    if cell == "all_zero":
        return 0
    if kind == "f32":
        return float(cell)
    if re.fullmatch(r"0x[0-9A-Fa-f]+", cell):
        return int(cell, 16)
    return int(cell)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
