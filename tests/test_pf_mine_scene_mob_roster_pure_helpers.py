"""LANE-B: three more no-bridge-required helpers in
``tools/pf_mine_scene_mob_roster.py`` had no test of their own -- not even a
bridge-gated one.

WHY THIS FILE EXISTS.  Round `hor2lh` (reserve item 3) named the shape of the
gap and paid one instance of it (``_digest``, see
``test_pf_mine_scene_mob_roster_digest.py``) without auditing the rest of the
module for siblings.  Round `x5bkvl` carried the audit forward as
unfinished.  This round ran it: every direct caller of ``_int``, ``_key`` and
``_ascii_dict`` in this tool's OWN test coverage turned out to be either
``@BRIDGE_GAMEDATA.skip_unless_present()``-gated (so absent on the Windows
merge gate, per ``NOW.md``'s own note that the gate has no bridge next to it)
or -- for these three specifically -- not present at all: grepping
``tests/*.py`` for ``_int(``, ``_key(`` and ``_ascii_dict(`` only turns up a
same-named helper belonging to a DIFFERENT generator tool
(``tools/pf_scan_field_scene_candidates.py``, its own copy, tested in
``tests/test_pf_scan_field_scene_candidates.py``) -- this module's own three
functions were exercised only indirectly, through a full ``Sources(...)``
build over real gamedata, and never on a bad input.

``_int`` is the sharper of the three: it is the one function standing between
a malformed numeric column (level, HP, rank, drop flags) and a silently wrong
roster row -- it is supposed to ``MineError`` rather than coerce, and nothing
before this file drove that branch at all.

WHAT THIS DOES NOT CLAIM.  It says nothing about whether any scene's shipped
tables are still fresh against the live bridge tables -- that is what the
(bridge-gated) regenerate-and-diff tests are for. It only says these three
functions do what their one-line contracts say, using inputs this file owns.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntGuardTests(unittest.TestCase):
    """No bridge clone required -- must run wherever the gate runs."""

    def test_a_well_formed_column_parses_to_the_same_int(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._int({"n_LEVEL_MIN": "27"}, "n_LEVEL_MIN", "row"), 27)

    def test_surrounding_whitespace_is_stripped_before_parsing(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._int({"n_RANK": "  5  "}, "n_RANK", "row"), 5)

    def test_a_missing_column_refuses_rather_than_defaulting_to_zero(
            self) -> None:
        # A mutant that swallows the KeyError/ValueError and returns 0 would
        # ship every unset numeric field as a real, silently-wrong zero.
        tool = _load_tool()
        with self.assertRaises(tool.MineError) as ctx:
            tool._int({}, "n_LEVEL_MIN", "MOBS row 31")
        message = str(ctx.exception)
        self.assertIn("MOBS row 31", message)
        self.assertIn("n_LEVEL_MIN", message)

    def test_a_non_integer_value_refuses_and_names_the_bad_token(
            self) -> None:
        tool = _load_tool()
        with self.assertRaises(tool.MineError) as ctx:
            tool._int({"n_RANK": "12.5"}, "n_RANK", "MOBS row 99")
        message = str(ctx.exception)
        self.assertIn("MOBS row 99", message)
        self.assertIn("n_RANK", message)
        self.assertIn("12.5", message)

    def test_a_blank_value_refuses_the_same_way_as_a_missing_column(
            self) -> None:
        tool = _load_tool()
        with self.assertRaises(tool.MineError):
            tool._int({"n_RANK": "   "}, "n_RANK", "row")


class KeyGuardTests(unittest.TestCase):
    """No bridge clone required -- must run wherever the gate runs."""

    def test_rows_are_keyed_by_the_named_column(self) -> None:
        tool = _load_tool()
        rows = [{"n_ID": "31", "s_NAME": "Tornado Eagle"},
                {"n_ID": "248", "s_NAME": "Da Vinci"}]
        keyed = tool._key(rows, "n_ID", Path("synthetic.tsv"))
        self.assertEqual(set(keyed), {"31", "248"})
        self.assertEqual(keyed["31"]["s_NAME"], "Tornado Eagle")
        self.assertIs(keyed["248"], rows[1])

    def test_the_stored_key_is_the_stripped_column_value(self) -> None:
        tool = _load_tool()
        rows = [{"n_ID": "  31  "}]
        keyed = tool._key(rows, "n_ID", Path("synthetic.tsv"))
        self.assertEqual(set(keyed), {"31"})

    def test_rows_with_a_blank_key_column_are_skipped_not_collided(
            self) -> None:
        tool = _load_tool()
        rows = [{"n_ID": ""}, {"n_ID": "   "}, {"n_ID": "31", "s_NAME": "x"}]
        keyed = tool._key(rows, "n_ID", Path("synthetic.tsv"))
        self.assertEqual(set(keyed), {"31"})

    def test_a_duplicate_key_refuses_and_names_the_source_path(self) -> None:
        # A mutant that keeps the FIRST row on a collision (last-write-wins
        # silently dropped) would make one row invisibly shadow another's
        # level/HP/outfit -- refusing loudly is the whole point of this guard.
        tool = _load_tool()
        rows = [{"n_ID": "31", "s_NAME": "a"}, {"n_ID": "31", "s_NAME": "b"}]
        path = Path("gamedata/tables/CONSTDATA_TH__MOBS.tsv")
        with self.assertRaises(tool.MineError) as ctx:
            tool._key(rows, "n_ID", path)
        message = str(ctx.exception)
        self.assertIn("31", message)
        self.assertIn(str(path), message)


class AsciiDictGuardTests(unittest.TestCase):
    """No bridge clone required -- must run wherever the gate runs."""

    def test_an_empty_mapping_renders_an_empty_braces_block(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._ascii_dict({}), "{\n}")

    def test_entries_are_sorted_by_key_regardless_of_insertion_order(
            self) -> None:
        tool = _load_tool()
        rendered = tool._ascii_dict({"placements": "b", "cline": "a"})
        self.assertLess(rendered.index("'cline'"), rendered.index("'placements'"))

    def test_each_entry_is_one_indented_comma_terminated_line(self) -> None:
        tool = _load_tool()
        rendered = tool._ascii_dict({"mobs": "deadbeef"})
        self.assertEqual(rendered, "{\n    'mobs': 'deadbeef',\n}")

    def test_non_ascii_values_are_escaped_not_emitted_raw(self) -> None:
        # This module's own header insists every generated file is pure
        # ASCII (CONSTDATA_TH__MOBS.s_NAME is CJK in the live data set); a
        # mutant that swapped ``ascii()`` for ``repr()`` or ``str()`` here
        # would smuggle raw non-ASCII bytes into a file the tool promises is
        # ASCII-only.
        tool = _load_tool()
        rendered = tool._ascii_dict({"name": "雨"})
        self.assertTrue(rendered.isascii())
        self.assertIn("\\u96e8", rendered)


if __name__ == "__main__":
    unittest.main()
