"""LANE-B: three more no-bridge-required helpers in
``tools/pf_mine_scene_mob_roster.py`` had no test of their own -- not even a
bridge-gated one.

WHY THIS FILE EXISTS.  Round `hor2lh` (reserve item 3) NAMED the shape of the
gap without paying it; round `x5bkvl` paid the one instance it picked
(``_digest``, see ``test_pf_mine_scene_mob_roster_digest.py`` -- that file's
own docstring says so directly) without auditing the rest of the module for
siblings.  Round `qamp70` carried the audit forward as still open.  This
round ran it: every direct caller of ``_int``, ``_key`` and ``_ascii_dict`` in
this tool's OWN test coverage turned out to be either
``@BRIDGE_GAMEDATA.skip_unless_present()``-gated (so absent on the Windows
merge gate, per ``NOW.md``'s own note that the gate has no bridge next to it)
or -- for ``_int`` and ``_ascii_dict`` specifically -- not present anywhere at
all: grepping ``tests/*.py`` for ``_int(`` and ``_ascii_dict(`` turns up
nothing.  ``_key(`` turns up one same-named helper belonging to a DIFFERENT
generator tool (``tools/pf_scan_field_scene_candidates.py``, its own separate
copy, tested in ``tests/test_pf_scan_field_scene_candidates.py``) -- not this
module's ``_key``.  Either way, this module's own three functions were
exercised only indirectly, through a full ``Sources(...)`` build over real
gamedata, and never on a bad input.

``_int`` is the sharper of the three: it is the one function standing between
a malformed numeric column (level, HP, rank, drop flags) and a silently wrong
roster row -- it is supposed to ``MineError`` rather than coerce, and nothing
before this file drove that branch at all.

WHAT THIS DOES NOT CLAIM.  It says nothing about whether any scene's shipped
tables are still fresh against the live bridge tables -- that is what the
(bridge-gated) regenerate-and-diff tests are for. It only says these
functions do what their one-line contracts say, using inputs this file owns.

ROUND p4ts3e added a fourth group, ``UnnumberedTemplateIdTests``, for the
same reason and in the same shape: ``_set_number_or_none`` and
``_reason_token`` decide what happens to a placement whose template id is not
a number at all, and that decision (skip the row, name it, keep the scene)
has to hold where the gate runs, with no bridge clone beside it.
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


class UnnumberedTemplateIdTests(unittest.TestCase):
    """One unreadable placement must not cost a scene its readable ones.

    ``Bg0010``'s placement 50 names ``Mob_Set_99``, a Mob-Set its own scene
    file never defines, so the decoder writes the literal string
    ``UNRESOLVED`` where a number belongs.  ``int()`` used to raise on that
    one cell and the whole scene refused to mine -- 99 readable placements
    lost to one unreadable one.  COO-DECISION 2026-09-06T07:48+07:00 item 3
    allows skipping it and forbids doing so quietly, which is the pair of
    claims these tests hold.  No bridge clone required.
    """

    def test_a_numeric_cell_is_still_read_as_that_number(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._set_number_or_none("99"), 99)
        self.assertEqual(tool._set_number_or_none(" 31 "), 31)

    def test_a_non_numeric_cell_yields_none_instead_of_raising(self) -> None:
        tool = _load_tool()
        self.assertIsNone(tool._set_number_or_none("UNRESOLVED"))

    def test_the_reason_token_stays_ascii_and_keeps_the_raw_word(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._reason_token("UNRESOLVED"), "UNRESOLVED")
        token = tool._reason_token("Mob_Set 雨/9")
        self.assertTrue(token.isascii())
        self.assertEqual(token, "Mob_Set___9")

    def test_an_empty_raw_cell_still_names_something(self) -> None:
        tool = _load_tool()
        self.assertEqual(tool._reason_token(""), "empty")

    def test_the_skipped_row_is_named_in_unresolved_placements(self) -> None:
        tool = _load_tool()
        sources = _StubSources([
            _placement("50", "UNRESOLVED"),
            _placement("51", "31"),
        ])
        rows = tool.unresolved_placements(sources, tool.IDENTITY_RULE_CLINE)
        by_index = {row["placement_index"]: row for row in rows}
        self.assertIn(50, by_index)
        self.assertEqual(
            by_index[50]["reason"], "template_id_is_not_a_number_UNRESOLVED",
        )
        # 51 resolves to a MOBS row with a single-basename avatar, so it is
        # carried, not unresolved: the skip is scoped to the bad cell alone.
        self.assertNotIn(51, by_index)

    def test_the_readable_rows_of_the_same_scene_are_still_carried(
        self,
    ) -> None:
        tool = _load_tool()
        sources = _StubSources([
            _placement("50", "UNRESOLVED"),
            _placement("51", "31"),
        ])
        carried = tool.unambiguous_placements(sources, tool.IDENTITY_RULE_CLINE)
        self.assertEqual([item[0] for item in carried], [51])


def _placement(index: str, template_ids: str) -> dict:
    """One placements.tsv row, only the columns these two functions read."""
    return {
        "index": index, "template_ids": template_ids,
        "x": "1.0", "y": "2.0", "z": "3.0",
    }


class _StubSources:
    """The three attributes the two functions under test actually read.

    Deliberately not a real ``Sources``: this file's whole point is helpers
    that run where no bridge clone exists, and a real one reads gamedata.
    """

    crosswalk = {"stub": True}

    def __init__(self, placements: list[dict]) -> None:
        self.placements = placements
        self.scene = "Bg0010"
        self.mobs = {
            "31": {"s_OUTFIT": "M011_000_000_SP3", "n_RANK": "1",
                   "n_AI_COMBAT": "214"},
        }

    def resolve(self, set_number: int, rule: str) -> int | None:
        return set_number if str(set_number) in self.mobs else None


if __name__ == "__main__":
    unittest.main()
