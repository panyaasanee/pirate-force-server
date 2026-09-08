"""GM-004: scene id -> GM scene name catalog, pinned to the committed client table."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import scene_catalog


class GmSceneCatalogTests(unittest.TestCase):
    def test_known_scene_ids_from_the_owner_order_letter(self):
        # notes_to_chief 20260826_1630: Port Royal=1, Prison Exile Island=2, Spice Paradise Island=3
        self.assertEqual(scene_catalog.gm_scene_name(1), "Port Royal")
        self.assertEqual(scene_catalog.gm_scene_name(2), "Prison Exile Island")
        self.assertEqual(scene_catalog.gm_scene_name(3), "Spice Paradise Island")

    def test_scene_count_matches_the_committed_table(self):
        self.assertEqual(scene_catalog.SCENE_COUNT, 330)

    def test_unknown_scene_id_raises(self):
        with self.assertRaises(KeyError):
            scene_catalog.gm_scene_name(123456)

    def test_is_known_scene_id(self):
        self.assertTrue(scene_catalog.is_known_scene_id(1))
        self.assertFalse(scene_catalog.is_known_scene_id(123456))

    def test_ship_in_the_sea_scene_ids_share_the_client_scene_name_but_not_the_gm_name(self):
        # s_SCENE_NAME repeats "Ship in the Sea" for many ids; s_GM_SCENE_NAME
        # disambiguates each with a Thai label + numbered suffix, e.g. id 17
        # -> "เรือในทะเล 1(17)" -- the two columns answer different questions.
        ship_ids = [
            n_id
            for n_id, name in scene_catalog.SCENE_ID_TO_NAME.items()
            if name == "Ship in the Sea"
        ]
        self.assertIn(17, ship_ids)
        self.assertIn(18, ship_ids)
        self.assertGreaterEqual(len(ship_ids), 7)
        self.assertEqual(scene_catalog.gm_scene_name(17), "เรือในทะเล 1(17)")
        gm_names_for_ship_ids = {scene_catalog.gm_scene_name(n_id) for n_id in ship_ids}
        self.assertGreater(len(gm_names_for_ship_ids), 1)

    def test_scene_ids_named_finds_repeated_gm_names(self):
        # ids 308-327 all carry the literal GM name "Hidden Island"
        ids = scene_catalog.scene_ids_named("Hidden Island")
        self.assertIn(308, ids)
        self.assertIn(327, ids)
        self.assertGreaterEqual(len(ids), 20)

    def test_blank_rows_in_the_clients_own_table_are_known_but_empty_named(self):
        # scene_name_tip.tsv itself carries four rows (13, 137, 138, 141)
        # where BOTH s_SCENE_NAME and s_GM_SCENE_NAME are blank in the
        # client's own committed table -- not a parsing gap this module
        # introduced. Pinned here because `is_known_scene_id` returning True
        # for a blank-named row is easy to misread as a bug the first time
        # someone reads `gm_scene_name(13) == ""` rather than a fact of the
        # source data: the id has a row (so `warp <its id>` gets no "unknown
        # scene" flag from `commands.describe_warp_target`), it is simply a
        # row the client itself left nameless. Distinct from
        # `test_unknown_scene_id_raises`, which is an id with NO row at all.
        for blank_id in (13, 137, 138, 141):
            with self.subTest(scene_id=blank_id):
                self.assertTrue(scene_catalog.is_known_scene_id(blank_id))
                self.assertEqual(scene_catalog.gm_scene_name(blank_id), "")
                self.assertEqual(scene_catalog.SCENE_ID_TO_NAME[blank_id], "")

    def test_non_sequential_high_ids_present(self):
        # the table's n_ID column is not contiguous 1..330; 997/999 exist too
        self.assertTrue(scene_catalog.is_known_scene_id(997))
        self.assertTrue(scene_catalog.is_known_scene_id(999))


class ResolveGmSceneNameTests(unittest.TestCase):
    """The name -> id direction `warp <scene name>` is built on.

    Every number in this class is a MEASUREMENT of the committed, sha-pinned
    table, not a preference. If the table is ever re-derived and a row moves,
    these die -- which is the point: the resolver's whole safety argument is
    "the table says so".
    """

    def test_the_three_scenes_the_owner_order_letter_names(self):
        # The M2 ladder is worded "island 2 and island 3" and these are the
        # rows those words land on. An operator at the client types the name.
        self.assertEqual(scene_catalog.resolve_gm_scene_name("Port Royal"), (1,))
        self.assertEqual(
            scene_catalog.resolve_gm_scene_name("Prison Exile Island"), (2,)
        )
        self.assertEqual(
            scene_catalog.resolve_gm_scene_name("Spice Paradise Island"), (3,)
        )

    def test_folding_is_case_and_whitespace_insensitive(self):
        # The shipped table pads every cell with spaces, and an operator
        # typing at 1 a.m. does not reproduce a shipped string exactly.
        for typed in (
            "spice paradise island",
            "SPICE PARADISE ISLAND",
            "  Spice   Paradise  Island  ",
        ):
            with self.subTest(typed=typed):
                self.assertEqual(scene_catalog.resolve_gm_scene_name(typed), (3,))

    def test_a_duplicated_name_returns_every_id_and_never_picks_one(self):
        # `Hidden Island` is on twenty scenes in the client's own table. A
        # resolver that returned one of them would send a GM somewhere they
        # did not ask for, and nothing downstream could tell.
        ids = scene_catalog.resolve_gm_scene_name("Hidden Island")
        self.assertEqual(len(ids), 20)
        self.assertEqual(list(ids), sorted(ids))
        self.assertIn(308, ids)
        poseidon = scene_catalog.resolve_gm_scene_name("Poseidon Island")
        self.assertEqual(len(poseidon), 10)

    def test_an_empty_or_blank_query_matches_nothing(self):
        # Four rows (13, 137, 138, 141) carry an empty name in the shipped
        # table. A resolver keyed on the raw string would hand all four back
        # for the empty query -- i.e. `warp ` would be a legal warp to a
        # scene picked at random from four.
        for query in ("", " ", "\t", "   \n  "):
            with self.subTest(query=repr(query)):
                self.assertEqual(scene_catalog.resolve_gm_scene_name(query), ())
        for blank_id in (13, 137, 138, 141):
            with self.subTest(scene_id=blank_id):
                self.assertNotIn(
                    blank_id,
                    [i for ids in scene_catalog._GM_NAME_TO_SCENE_IDS.values() for i in ids],
                )

    def test_the_empty_query_guard_holds_even_if_the_index_ever_carries_one(self):
        # Measured, not assumed: with the index built as it is today, DELETING
        # the `if not key: return ()` line changes no test -- `_build_name_index`
        # already drops empty keys, so the guard has two defences and only one
        # witness. This is that witness. It aims at the guard itself by handing
        # the resolver an index that DOES carry an empty key, which is exactly
        # the state a future edit to `_build_name_index` would create.
        poisoned = dict(scene_catalog._GM_NAME_TO_SCENE_IDS)
        poisoned[""] = (13, 137, 138, 141)
        with mock.patch.object(scene_catalog, "_GM_NAME_TO_SCENE_IDS", poisoned):
            self.assertEqual(scene_catalog.resolve_gm_scene_name(""), ())
            self.assertEqual(scene_catalog.resolve_gm_scene_name("   "), ())
            # and the same index still answers a real name, so the test is not
            # passing because the patch broke the resolver outright
            self.assertEqual(scene_catalog.resolve_gm_scene_name("Port Royal"), (1,))

    def test_an_unknown_name_is_an_empty_tuple_not_an_exception(self):
        self.assertEqual(scene_catalog.resolve_gm_scene_name("Atlantis"), ())

    def test_a_non_str_query_raises_rather_than_matching(self):
        for bad in (2, None, ["Port Royal"], b"Port Royal"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    scene_catalog.resolve_gm_scene_name(bad)

    def test_the_fold_invents_no_ambiguity_the_table_does_not_already_have(self):
        # The safety argument for folding case is that it merges no two
        # DISTINCT shipped names. Measured here rather than asserted: for
        # every folded key, the set of ids it returns must equal the union of
        # the ids of the shipped names that fold to it -- and each such key
        # must come from exactly one distinct shipped spelling.
        spellings: dict[str, set[str]] = {}
        for n_id, _name, gm_name in scene_catalog._ROWS:
            key = scene_catalog._fold_gm_scene_name(gm_name)
            if not key:
                continue
            spellings.setdefault(key, set()).add(gm_name.strip())
        merged = {k: v for k, v in spellings.items() if len(v) > 1}
        self.assertEqual(merged, {}, f"case/space folding merged distinct names: {merged}")

    def test_every_shipped_name_resolves_back_to_the_row_it_came_from(self):
        # Round trip over the WHOLE table, not a sample: no row may be
        # unreachable by its own name (except the four nameless ones).
        unreachable = [
            n_id
            for n_id, _name, gm_name in scene_catalog._ROWS
            if gm_name.strip() and n_id not in scene_catalog.resolve_gm_scene_name(gm_name)
        ]
        self.assertEqual(unreachable, [])

    def test_the_counts_this_lane_prints_to_an_operator_are_the_tables_own(self):
        self.assertEqual(scene_catalog.SCENE_COUNT, 330)
        self.assertEqual(scene_catalog.GM_NAME_COUNT, 293)
        self.assertEqual(
            scene_catalog.GM_NAME_COUNT, len(scene_catalog._GM_NAME_TO_SCENE_IDS)
        )

    def test_every_name_in_the_table_survives_the_console_encoding(self):
        # 209 of the 330 names carry Thai. The bridge console is cp874 (the
        # Thai code page), so today every name encodes -- measured, not
        # assumed. This test is the tripwire for a re-derived table that
        # introduces a name outside cp874: at that moment any code path that
        # echoes a scene name to the console becomes a way to kill it, and
        # whoever re-derives the table must see that here rather than at 1
        # a.m. on the bridge.
        for n_id, _name, gm_name in scene_catalog._ROWS:
            with self.subTest(scene_id=n_id):
                gm_name.encode("cp874")


class NearMissSuggestionTests(unittest.TestCase):
    """`suggest_gm_scene_names` -- the search an exact-match resolver denied."""

    def test_one_dropped_letter_still_finds_the_island(self):
        self.assertEqual(
            scene_catalog.suggest_gm_scene_names("Prison Exile Iland"),
            (("Prison Exile Island", 1),),
        )

    def test_nonsense_suggests_nothing_rather_than_the_nearest_island(self):
        # The cutoff earns its value here: a suggestion that is merely the
        # closest row of 293 would send a GM to the wrong island with a
        # confident-looking line.
        self.assertEqual(scene_catalog.suggest_gm_scene_names("qqqqqqqq"), ())

    def test_an_exact_hit_is_not_a_suggestion(self):
        # The caller already had a match; anything printed here would be
        # noise under a successful warp.
        self.assertEqual(scene_catalog.suggest_gm_scene_names("Port Royal"), ())
        self.assertEqual(scene_catalog.suggest_gm_scene_names("  pOrT   roYAL "), ())

    def test_empty_and_whitespace_suggest_nothing(self):
        for query in ("", "   ", "\t\n"):
            with self.subTest(query=query):
                self.assertEqual(scene_catalog.suggest_gm_scene_names(query), ())

    def test_an_ambiguous_name_reports_a_count_not_twenty_numbers(self):
        self.assertEqual(
            scene_catalog.suggest_gm_scene_names("hidden iland"),
            (("Hidden Island", 20),),
        )

    def test_the_limit_is_honoured_and_zero_means_nothing(self):
        many = scene_catalog.suggest_gm_scene_names("Navy Prisn2", limit=3)
        self.assertEqual(len(many), 3)
        self.assertEqual(
            scene_catalog.suggest_gm_scene_names("Navy Prisn2", limit=1), many[:1]
        )
        self.assertEqual(
            scene_catalog.suggest_gm_scene_names("Navy Prisn2", limit=0), ()
        )

    def test_every_suggested_name_is_a_row_of_the_table_verbatim(self):
        # The whole safety argument for printing these lines is that no
        # character of them comes from the query. Assert it against the
        # table rather than trusting the implementation.
        shipped = set(scene_catalog.SCENE_ID_TO_GM_NAME.values())
        for query in ("Prison Exile Iland", "Navy Prisn2", "hidden iland", "Port Royl"):
            with self.subTest(query=query):
                suggestions = scene_catalog.suggest_gm_scene_names(query)
                self.assertTrue(suggestions)
                for name, id_count in suggestions:
                    self.assertIn(name, shipped)
                    self.assertEqual(
                        id_count, len(scene_catalog.resolve_gm_scene_name(name))
                    )

    def test_a_suggested_name_resolves_back_to_that_many_ids(self):
        # A suggestion the operator cannot then type is worse than silence.
        for query in ("Prison Exile Iland", "Port Royl"):
            with self.subTest(query=query):
                for name, id_count in scene_catalog.suggest_gm_scene_names(query):
                    self.assertEqual(
                        len(scene_catalog.resolve_gm_scene_name(name)), id_count
                    )

    def test_the_empty_query_guard_holds_even_when_the_matcher_answers_everything(self):
        # Aimed at the GUARD, not at today's behaviour. `_build_name_index`
        # drops the table's four unnamed rows, so an empty key is absent and
        # deleting `if not key` changes no result today -- the guard has no
        # witness. Put the empty key IN the index (the state a future edit to
        # `_build_name_index` would create) and the guard becomes the only
        # thing standing between a blank line and four scenes.
        # Today the matcher itself returns nothing for an empty key, so
        # deleting `if not key` changes no result and the guard has no
        # witness. Make the matcher answer everything -- the state any
        # future change of matcher or cutoff could create -- and the guard
        # is then the only thing between a blank line and a suggestion.
        always = lambda key, keys, n=3, cutoff=0.0: list(keys)[:n]  # noqa: E731
        with mock.patch.object(scene_catalog.difflib, "get_close_matches", always):
            for query in ("", "   ", "\t\n"):
                with self.subTest(query=query):
                    self.assertEqual(scene_catalog.suggest_gm_scene_names(query), ())
                    self.assertEqual(scene_catalog.resolve_gm_scene_name(query), ())
            # ...and a real near miss still comes back through the very same
            # patched matcher, so this cannot pass by breaking the function.
            self.assertTrue(scene_catalog.suggest_gm_scene_names("Prison Exile Iland"))

    def test_a_non_string_query_is_a_type_error_not_a_silent_empty(self):
        with self.assertRaises(TypeError):
            scene_catalog.suggest_gm_scene_names(2)


class WitnessesPfAdversaryNqgmamAskedFor(unittest.TestCase):
    """Three properties that were true but had no test that could see them."""

    def test_the_table_really_has_rows_before_the_sweeps_above_mean_anything(self):
        # D7. `test_every_name_in_the_table_survives_the_console_encoding`
        # and the whole-table round trip are both loops with no assertion of
        # their own: on an empty `_ROWS` they iterate zero times and pass.
        # This is the assertion that makes those two sweeps mean something.
        self.assertEqual(len(scene_catalog._ROWS), 330)
        self.assertEqual(len(scene_catalog.SCENE_ID_TO_GM_NAME), 330)

    def test_the_comment_s_own_counts_are_the_table_s_counts(self):
        # D5. The design paragraph above `_fold_gm_scene_name` said 294
        # distinct names and seven repeated names; both counted the empty
        # name as a name. Re-derived here so the paragraph cannot drift back.
        named = [gm for _id, _scene, gm in scene_catalog._ROWS if gm.strip()]
        self.assertEqual(len(set(named)), 293)
        self.assertEqual(scene_catalog.GM_NAME_COUNT, 293)
        repeated = [
            key
            for key, ids in scene_catalog._GM_NAME_TO_SCENE_IDS.items()
            if len(ids) > 1
        ]
        self.assertEqual(len(repeated), 6)
        self.assertEqual(len(scene_catalog._ROWS) - len(named), 4)

    def test_casefold_and_lower_agree_on_every_character_the_guard_admits(self):
        # D3/M18, answered rather than papered over. pf-adversary found that
        # swapping `casefold()` for `lower()` in `_fold_gm_scene_name` cannot
        # be seen by any test -- and after `gm/commands.py`'s console-codec
        # guard that is no longer a missing witness but a THEOREM: the two
        # differ only on characters (U+00DF, U+017F, U+1E9E, U+212A,
        # U+FB00-06, the Greek final sigma) that cp874 cannot encode, and the
        # guard refuses those before the fold is reached. cp874 is ASCII plus
        # Thai, and Thai is caseless.
        #
        # So this is the mutant's obituary, not its witness: if the guard's
        # codec is ever widened to one where the two disagree, this test goes
        # red and the choice has to be made deliberately.
        for code_point in range(0x110000):
            character = chr(code_point)
            try:
                character.encode("cp874")
            except (UnicodeEncodeError, UnicodeError):
                continue
            self.assertEqual(character.casefold(), character.lower(), hex(code_point))

    def test_ascending_order_is_the_code_s_doing_and_not_the_file_s(self):
        # D3/M10. `resolve_gm_scene_name` promises ascending ids and
        # `sorted()` is the only thing enforcing it -- but the shipped file
        # happens to be in ascending id order, so a test that reads the real
        # table is satisfied by the fixture and `tuple(sorted(ids))` can be
        # cut to `tuple(ids)` invisibly. Build the index from rows in
        # DESCENDING id order: now only the code can produce ascending.
        descending = list(reversed(scene_catalog._ROWS))
        self.assertGreater(descending[0][0], descending[-1][0])
        with mock.patch.object(scene_catalog, "_ROWS", descending):
            rebuilt = scene_catalog._build_name_index()
        hidden = rebuilt[scene_catalog._fold_gm_scene_name("Hidden Island")]
        self.assertEqual(len(hidden), 20)
        self.assertEqual(list(hidden), sorted(hidden))
        self.assertEqual(
            hidden, scene_catalog._GM_NAME_TO_SCENE_IDS["hidden island"]
        )


class TheTableFactsTheWarpGrammarLeansOnTests(unittest.TestCase):
    """Two properties of the pinned table that `gm/commands.py` relies on.

    Both live here rather than there because both are statements about the
    client's shipped data, and both go silently wrong -- not loudly -- if a
    future re-derive changes the file.
    """

    def test_the_longest_name_length_is_the_measured_value_not_a_recompute(self):
        """A LITERAL, backed by the sha pin -- pf-adversary D3, MEASURED.

        ~~`assertEqual(LONGEST_GM_NAME_LENGTH, max(len(key) for key in
        _GM_NAME_TO_SCENE_IDS))`~~ is STRUCK: that is character for
        character the right-hand side of the constant's own definition, so
        it recomputes the implementation and ANY table passes it.  The class
        docstring claimed this pair goes loudly wrong if a re-derive changes
        the file, and it could not: it was a tautology wearing the name of
        the property.

        The honest shape is the measured number written down here and the
        table pinned by `SOURCE_SHA256` at import.  Re-derive the table and
        this goes red, which is the whole point -- `MAX_WARP_NAME_QUERY_
        LENGTH` is twice this, so an off-by-one here is an off-by-two in
        what an operator may type, and that must be a human decision rather
        than a number that follows a data file silently.
        """
        self.assertEqual(54, scene_catalog.LONGEST_GM_NAME_LENGTH)
        self.assertEqual(
            "f9076cfc3c14433b376811437d68375d5dd1ce1ef2c7a50dbc1d4e4d241bfa3a",
            scene_catalog.SOURCE_SHA256,
            "the literal above is only meaningful while this table is that "
            "table; a new sha means re-measure, not re-type",
        )
        # Characters, not bytes: the table is `TEXTDATA_TH__*` and its
        # longest name today is Thai, which is 3 bytes per character in
        # UTF-8 and 1 in cp874. A byte count would mean two different caps
        # depending on who measured it.
        longest = max(scene_catalog._GM_NAME_TO_SCENE_IDS, key=len)
        self.assertEqual(len(longest), scene_catalog.LONGEST_GM_NAME_LENGTH)
        self.assertGreater(
            len(longest.encode("utf-8")), scene_catalog.LONGEST_GM_NAME_LENGTH
        )

    def test_the_thai_row_count_the_constant_cites_is_the_measured_one(self):
        """pf-adversary D4: the docstring said 37; it is 209 of 330.

        Written down rather than recomputed, for D3's reason.  37 was
        `SCENE_COUNT - GM_NAME_COUNT` from another paragraph of the same
        file, re-labelled -- and it is the sentence that argues why this
        constant counts CHARACTERS and not bytes, so a reader checking that
        argument was being handed a number off by 5.6x.
        """
        thai = sum(
            1
            for name in scene_catalog.SCENE_ID_TO_GM_NAME.values()
            if any("\u0e00" <= ch <= "\u0e7f" for ch in name)
        )
        self.assertEqual(209, thai)
        self.assertEqual(330, len(scene_catalog.SCENE_ID_TO_GM_NAME))

    def test_no_shipped_name_contains_the_scene_selector_character(self):
        # This is the whole reason `warp <scene name> #n` can be told apart
        # from a name, where a trailing bare number could not: 52 names end
        # in a digit, none contains a `#`. Walks all 330, not a sample.
        for scene_id, name in scene_catalog.SCENE_ID_TO_GM_NAME.items():
            with self.subTest(scene_id=scene_id):
                self.assertNotIn("#", name)


class TheFragmentSearchTests(unittest.TestCase):
    """`suggest_gm_scene_names` answers a piece of a name, not only a typo.

    difflib scores over the WHOLE name, so a fragment is mostly missing
    name and scores below the ratio however right it is.  That left the
    commonest way to half-remember a name -- its first word -- at the same
    dead end the suggestion helper was written to remove.
    """

    def test_a_first_word_that_used_to_answer_nothing_now_names_scenes(self):
        # Measured on the pinned table: difflib alone returns () for this
        # query against all 293 keys.
        self.assertEqual(
            (("Atlantic Ocean1", 1), ("Atlantic-Dark Fog Sea", 1)),
            scene_catalog.suggest_gm_scene_names("Atlantic"),
        )

    def test_the_measured_size_of_the_hole_this_closed(self):
        """61 of 86 distinct first words answered nothing; now 6 do.

        Written down rather than recomputed from the implementation (the
        lesson of D2/D3 last round): these two numbers are what makes the
        change worth its lines, and if the table is re-derived they must be
        re-measured by a human, not followed silently.
        """
        first_words = sorted(
            {
                name.split(" ")[0]
                for name in scene_catalog.SCENE_ID_TO_GM_NAME.values()
                if name.split(" ")[0]
            }
        )
        self.assertEqual(86, len(first_words))
        unanswered = [
            word for word in first_words if not scene_catalog.suggest_gm_scene_names(word)
        ]
        self.assertEqual(6, len(unanswered))

    def test_a_close_match_is_never_displaced_by_a_fragment_hit(self):
        # One dropped letter still answers with the name it is one letter
        # away from, and answers with it FIRST.
        suggestions = scene_catalog.suggest_gm_scene_names("Prison Exile Iland")
        self.assertEqual(("Prison Exile Island", 1), suggestions[0])

    def test_the_order_is_where_the_fragment_lands_then_alphabetical(self):
        """Pinned as a literal, because the order IS the promise.

        CORRECTED (pf-adversary round `pdf3gh`, D6): only the THIRD entry
        comes from the new code.  `difflib.get_close_matches('island', ...)`
        already returns `mad island` and `bear island` at this cutoff, and
        difflib hits are placed ahead of containment hits, so this triple
        pins the containment sort at one position, not three.  Sorting by
        name alone would answer `Battle Island` (offset 7, alphabetically
        first), not `Bear Island` as this docstring first said -- the
        mutant does die on this assertion, for that reason rather than the
        stated one.  Iterating the table's own dict order would answer
        whatever the file happens to list first and would not be a promise
        at all.  An operator who reads two different answers to the same
        query stops reading the answer.
        """
        expected = (("Mad Island", 1), ("Bear Island", 1), ("Brave Island", 1))
        self.assertEqual(expected, scene_catalog.suggest_gm_scene_names("island"))
        self.assertEqual(expected, scene_catalog.suggest_gm_scene_names("ISLAND"))

    def test_it_is_capped_at_the_same_three_a_way_out_line_can_carry(self):
        for query in ("island", "a", "sea"):
            with self.subTest(query=query):
                self.assertLessEqual(
                    len(scene_catalog.suggest_gm_scene_names(query)),
                    scene_catalog.MAX_SUGGESTIONS,
                )

    def test_an_exact_hit_is_still_not_a_suggestion(self):
        # Containment would match `Atlantic Ocean1` against itself; the
        # early return for a key already in the table is what stops it.
        self.assertEqual((), scene_catalog.suggest_gm_scene_names("Atlantic Ocean1"))
        self.assertEqual((), scene_catalog.suggest_gm_scene_names("  atlantic   ocean1 "))

    def test_a_query_that_is_neither_close_nor_contained_still_answers_nothing(self):
        # The property the ratio was chosen for survives the fallback: a
        # suggestion that is not in the table is worse than no suggestion.
        for query in ("qqqqqqqq", "zzzz zzzz", "\u0e01\u0e01\u0e01\u0e01\u0e01\u0e01"):
            with self.subTest(query=query):
                self.assertEqual((), scene_catalog.suggest_gm_scene_names(query))

    def test_every_character_it_returns_comes_out_of_the_table(self):
        # The rule the whole helper rests on, re-checked on the path that
        # is new: a fragment hit must not carry the operator's own text
        # into a line bound for a cp874 console.
        shipped = set(scene_catalog.SCENE_ID_TO_GM_NAME.values())
        for query in ("island", "MARKER\u2028", "a", "Atlantic"):
            with self.subTest(query=query):
                for name, _count in scene_catalog.suggest_gm_scene_names(query):
                    self.assertIn(name, shipped)


if __name__ == "__main__":
    unittest.main()
