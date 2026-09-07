"""LANE-DB round `5vzis0`: what a scene exit may restate about HP.

The ticket this file serves is `GT-301` (`NOW.md` line 34, owner set by
`COO-DECISION 20260907_1441`): leaving scene 126 must return the CHARACTER's
HP, and `BoatHealth` must not be `-1`.

WHAT THIS FILE PROVES (wire/DB layer only -- nothing here is on a screen):

1. The `-1/1` the owner saw is arithmetic, not a coincidence: x=52 / x=53
   are named `GetBoatHealth_current` / `GetBoatHealth_max` in this
   repository's own construction-default table, and their defaults render as
   -1 and 1.  Both halves are read from `persistence_attr_compose` rather
   than typed here, so a corrected table moves this test with it.
2. An unseeded row is REFUSED, not composed as zeroes, and the refusal names
   the column that was missing.
3. The restate really passes through `persistence_hp_pair_selector.
   guard_block`: a store whose row holds a dishonest pair is refused BY THE
   GUARD, with the guard's own console token in the detail.  That is what
   makes the call load-bearing rather than decorative.
4. The boat rows are never stated, and the fact that they are unstated is
   DERIVED from `SERVER_OWNED_FIELDS`: a test patches that table to pretend
   the columns shipped and the refusal narrows by itself.
5. The console line is one ASCII line and shouts on a refusal.

WHAT THIS FILE DOES NOT PROVE.  Nothing here evaluates `0x430E10`, so
nothing here claims which branch the client actually took at sea.  It does
not claim the module has a production caller -- it has none, and the module
says so.  It has not run against the canonical database.
"""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402,E501
from pirateforce_foundation import persistence_hp_pair_selector as sel  # noqa: E402,E501
from pirateforce_foundation import persistence_scene_exit_vitals as exitv  # noqa: E402,E501
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MODULE_FILE = ROOT / "src" / "pirateforce_foundation" / "persistence_scene_exit_vitals.py"

#: Any scene id.  The module carries it and never compares it; the tests say
#: so by using a value that is NOT 126 wherever 126 is not the point.
OCEAN_SCENE = 126
SOME_OTHER_SCENE = 7


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _FakeStore:
    """A store that answers `read_typed_attributes` and nothing else.

    Deliberately not a `unittest.mock.Mock`: a Mock answers every attribute,
    so a module that started calling a second store method would keep this
    file green.  This one raises `AttributeError` instead.
    """

    def __init__(self, typed):
        self.typed = dict(typed)
        self.asked = []

    def read_typed_attributes(self, character_id):
        self.asked.append(character_id)
        return dict(self.typed)


class TheMinusOneIsTheBoatsDefaultNotABrokenHpTests(unittest.TestCase):
    """`R321` said faction; the arithmetic says BoatHealth."""

    def test_the_alternate_rows_are_the_boat_health_rows(self):
        names = {
            x: compose.CLIENT_CONSTRUCTION_DEFAULTS[x].semantic_name
            for x in sel.ALTERNATE_PAIR
        }
        self.assertEqual(
            tuple(names[x] for x in sel.ALTERNATE_PAIR),
            ("GetBoatHealth_current", "GetBoatHealth_max"),
        )

    def test_their_defaults_render_as_the_panel_the_owner_saw(self):
        rendered = tuple(
            sel.as_signed_row_value(x, compose.CLIENT_CONSTRUCTION_DEFAULTS[x].value)
            for x in sel.ALTERNATE_PAIR
        )
        self.assertEqual(rendered, (-1, 1))

    def test_this_server_owns_no_column_for_either_boat_row(self):
        self.assertEqual(exitv.alternate_rows_owned_by_this_server(), ())


class AnUnseededRowIsRefusedNotZeroedTests(unittest.TestCase):
    def test_an_empty_row_states_nothing(self):
        store = _FakeStore({})
        resolved = exitv.resolve_for_scene_exit(store, 11, OCEAN_SCENE)
        self.assertFalse(resolved.may_restate)
        self.assertEqual(resolved.rows, {})
        self.assertEqual(resolved.reason, exitv.REASON_ROW_UNSEEDED)
        self.assertEqual(store.asked, [11])

    def test_half_a_pair_is_not_a_pair_and_the_detail_names_the_gap(self):
        for typed, missing in (
            ({"hp_current": 37}, "hp_max"),
            ({"hp_max": 41}, "hp_current"),
        ):
            with self.subTest(typed=typed):
                resolved = exitv.resolve_for_scene_exit(
                    _FakeStore(typed), 12, SOME_OTHER_SCENE
                )
                self.assertFalse(resolved.may_restate)
                self.assertEqual(resolved.reason, exitv.REASON_ROW_UNSEEDED)
                self.assertIn(missing, resolved.detail)

    def test_a_seeded_row_is_restated_with_its_own_numbers(self):
        for current, maximum in ((37, 41), (1, 999), (250, 250)):
            with self.subTest(hp=(current, maximum)):
                store = _FakeStore({"hp_current": current, "hp_max": maximum})
                resolved = exitv.resolve_for_scene_exit(store, 13, OCEAN_SCENE)
                self.assertTrue(resolved.may_restate)
                self.assertEqual(
                    resolved.rows,
                    {sel.PRIMARY_PAIR[0]: current, sel.PRIMARY_PAIR[1]: maximum},
                )
                self.assertIsNone(resolved.reason)

    def test_a_missing_character_raises_rather_than_restating_nothing(self):
        class _NoSuchCharacter:
            def read_typed_attributes(self, character_id):
                raise KeyError(character_id)

        with self.assertRaises(KeyError):
            exitv.resolve_for_scene_exit(_NoSuchCharacter(), 99, OCEAN_SCENE)


class TheGuardIsALoadBearingCallNotADecorationTests(unittest.TestCase):
    """The guard has had no caller outside its own tests since it was built.

    If these go green with the `guard_block` call deleted, the module's claim
    to have given it one is false.
    """

    def test_a_row_holding_a_dishonest_pair_is_refused_by_the_guard(self):
        # max 0 with a current above it: `pair_gaps` calls this dishonest on
        # the primary pair, and the primary pair is checked armed or not.
        store = _FakeStore({"hp_current": 50, "hp_max": 0})
        resolved = exitv.resolve_for_scene_exit(store, 14, OCEAN_SCENE)
        self.assertFalse(resolved.may_restate)
        self.assertEqual(resolved.reason, exitv.REASON_GUARD_REFUSED)
        self.assertIn(sel.HP_PAIR_REFUSED_CONSOLE_TOKEN, resolved.detail)

    def test_the_refused_pair_would_have_been_composed_without_the_guard(self):
        """Control: the same row passes the unseeded check, so the refusal
        above is the guard's doing and not the missing-column branch's."""
        typed = {"hp_current": 50, "hp_max": 0}
        columns = tuple(
            compose.SERVER_OWNED_FIELDS[x].column for x in sel.PRIMARY_PAIR
        )
        self.assertTrue(all(column in typed for column in columns))

    def test_an_honest_pair_walks_through_the_same_call(self):
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 50, "hp_max": 100}), 15, OCEAN_SCENE
        )
        self.assertTrue(resolved.may_restate)
        self.assertIsNone(resolved.reason)


class TheDeadCharacterIsTheWholePointTests(unittest.TestCase):
    """pf-adversary `5vzis0` D4: `max(int(value), 1)` SURVIVED the first
    draft of this file at `19 passed`, because no test here ever passed
    `hp_current = 0`.  A dead character is the one value the module's whole
    premise turns on: 0 is a MEASURED zero and must be restated as 0, while
    an ABSENT column must be refused -- the two are indistinguishable to a
    reader who never tries the first."""

    def test_a_dead_character_is_restated_as_zero_not_bumped_to_one(self):
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 0, "hp_max": 100}), 21, OCEAN_SCENE
        )
        self.assertTrue(resolved.may_restate)
        self.assertEqual(resolved.rows[sel.PRIMARY_PAIR[0]], 0)
        self.assertEqual(resolved.rows[sel.PRIMARY_PAIR[1]], 100)

    def test_a_measured_zero_and_an_absent_column_are_not_the_same_answer(self):
        measured = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 0, "hp_max": 100}), 22, OCEAN_SCENE
        )
        absent = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_max": 100}), 22, OCEAN_SCENE
        )
        self.assertTrue(measured.may_restate)
        self.assertFalse(absent.may_restate)

    def test_the_console_line_prints_the_zero(self):
        line = exitv.console_line(
            exitv.resolve_for_scene_exit(
                _FakeStore({"hp_current": 0, "hp_max": 100}), 23, OCEAN_SCENE
            )
        )
        self.assertIn("x3=0", line)
        self.assertFalse(line.startswith("!! "))


class TheGuardRefusesMoreThanOneShapeTests(unittest.TestCase):
    """pf-adversary `5vzis0` D5: guarding only on `current > max` SURVIVED at
    `19 passed`, because the first draft exercised exactly one refusing
    shape.  The shape it missed is the one this ticket exists for: a pair
    that is ordered correctly and still renders NEGATIVE on the client."""

    REFUSED = (
        (101, 100),
        (50, 0),
        (0xFFFFFFFF, 1),
        (0xFFFFFFF0, 0xFFFFFFFF),
        (2 ** 31, 2 ** 32 - 1),
    )

    def test_every_dishonest_shape_is_refused_by_the_guard(self):
        for current, maximum in self.REFUSED:
            with self.subTest(hp=(current, maximum)):
                resolved = exitv.resolve_for_scene_exit(
                    _FakeStore({"hp_current": current, "hp_max": maximum}),
                    24,
                    OCEAN_SCENE,
                )
                self.assertFalse(resolved.may_restate)
                self.assertEqual(resolved.reason, exitv.REASON_GUARD_REFUSED)

    def test_the_negative_rendering_pair_is_ordered_and_still_refused(self):
        """`0xFFFFFFF0 <= 0xFFFFFFFF`, so an ordering-only guard admits it and
        the HUD prints `-16 / -1` -- the very `-1` GT-301 exists to remove,
        leaving the module inside a `may_restate=True` restate."""
        current, maximum = 0xFFFFFFF0, 0xFFFFFFFF
        self.assertLessEqual(current, maximum)
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": current, "hp_max": maximum}), 25, OCEAN_SCENE
        )
        self.assertFalse(resolved.may_restate)
        self.assertEqual(resolved.reason, exitv.REASON_GUARD_REFUSED)

    def test_every_refusing_shape_is_storable_so_none_of_this_is_hypothetical(self):
        """`migrations/006` bounds these columns to `BETWEEN 0 AND 4294967295`,
        so each value above is one a real row can hold."""
        for current, maximum in self.REFUSED:
            with self.subTest(hp=(current, maximum)):
                for value in (current, maximum):
                    self.assertGreaterEqual(value, 0)
                    self.assertLessEqual(value, 4294967295)


class TheVerdictBindsTheObjectItVerifiedTests(unittest.TestCase):
    """pf-adversary `5vzis0` D6: `frozen=True` froze the FIELD, not the dict
    behind it, so a caller could edit the pair after the guard passed it."""

    def test_the_stated_rows_cannot_be_edited_after_the_guard_spoke(self):
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 50, "hp_max": 100}), 26, OCEAN_SCENE
        )
        with self.assertRaises(TypeError):
            resolved.rows[sel.ALTERNATE_PAIR[0]] = 0xFFFFFFFF
        with self.assertRaises(TypeError):
            resolved.rows[sel.PRIMARY_PAIR[0]] = 0

    def test_a_refusal_carries_an_uneditable_empty_mapping_too(self):
        resolved = exitv.resolve_for_scene_exit(_FakeStore({}), 27, OCEAN_SCENE)
        with self.assertRaises(TypeError):
            resolved.rows[sel.PRIMARY_PAIR[0]] = 1

    def test_a_reason_and_a_restate_cannot_both_be_present_or_both_absent(self):
        """The invariant the class docstring states, enforced rather than
        promised: hand-constructing the contradiction raises."""
        with self.assertRaises(ValueError):
            exitv.SceneExitVitals(1, OCEAN_SCENE, {}, None, "")
        with self.assertRaises(ValueError):
            exitv.SceneExitVitals(1, OCEAN_SCENE, {3: 1, 4: 2}, "some_reason", "")


class TheBoatRowsAreNeverStatedAndThatIsDerivedTests(unittest.TestCase):
    def test_no_restate_ever_carries_x52_or_x53(self):
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 50, "hp_max": 100}), 16, OCEAN_SCENE
        )
        self.assertEqual(set(resolved.rows) & set(sel.ALTERNATE_PAIR), set())
        self.assertEqual(resolved.alternate_rows_refused, sel.ALTERNATE_PAIR)

    def test_the_refusal_narrows_by_itself_the_day_a_column_ships(self):
        """Not a literal `()`: patch the owned table and watch it move."""
        pretend = dict(compose.SERVER_OWNED_FIELDS)
        pretend[sel.ALTERNATE_PAIR[0]] = compose.ServerOwnedField(
            sel.ALTERNATE_PAIR[0], "boat_health_current", False, False
        )
        with unittest.mock.patch.object(
            compose, "SERVER_OWNED_FIELDS", pretend
        ), unittest.mock.patch.object(exitv, "SERVER_OWNED_FIELDS", pretend):
            self.assertEqual(
                exitv.alternate_rows_owned_by_this_server(),
                (sel.ALTERNATE_PAIR[0],),
            )
            resolved = exitv.resolve_for_scene_exit(
                _FakeStore({"hp_current": 50, "hp_max": 100}), 17, OCEAN_SCENE
            )
            self.assertEqual(
                resolved.alternate_rows_refused, (sel.ALTERNATE_PAIR[1],)
            )

    def test_the_primary_columns_come_from_the_owned_table(self):
        """pf-adversary `5vzis0` D8: this test used to compare the constant
        to the same expression that builds it, which is a tautology -- the
        literal `("hp_current", "hp_max")` SURVIVED it.  The module now reads
        the table per call, so patching it moves the answer, which is the
        only spelling that can tell a read from a copy."""
        self.assertEqual(exitv._primary_columns(), ("hp_current", "hp_max"))
        pretend = dict(compose.SERVER_OWNED_FIELDS)
        for x in sel.PRIMARY_PAIR:
            pretend[x] = compose.ServerOwnedField(
                x, "renamed_column_%d" % x, True, False
            )
        with unittest.mock.patch.object(exitv, "SERVER_OWNED_FIELDS", pretend):
            self.assertEqual(
                exitv._primary_columns(),
                ("renamed_column_3", "renamed_column_4"),
            )
            # And the read is used, not merely available: a row keyed by the
            # real column names is now unseeded as far as this module knows.
            resolved = exitv.resolve_for_scene_exit(
                _FakeStore({"hp_current": 50, "hp_max": 100}), 30, OCEAN_SCENE
            )
            self.assertFalse(resolved.may_restate)
            self.assertEqual(resolved.reason, exitv.REASON_ROW_UNSEEDED)
        self.assertEqual(exitv._primary_columns(), ("hp_current", "hp_max"))


class TheSceneIdIsCarriedNeverComparedTests(unittest.TestCase):
    def test_the_same_row_resolves_identically_in_every_scene(self):
        typed = {"hp_current": 50, "hp_max": 100}
        answers = {
            scene: exitv.resolve_for_scene_exit(_FakeStore(typed), 18, scene).rows
            for scene in (0, 1, OCEAN_SCENE, SOME_OTHER_SCENE, 65535)
        }
        self.assertEqual(len(set(map(str, answers.values()))), 1)

    def test_the_module_hardcodes_no_scene_id_in_its_logic(self):
        text = MODULE_FILE.read_text(encoding="ascii")
        body = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )
        # `126` may appear in prose; it must not appear in a comparison.
        self.assertNotIn("== 126", body)
        self.assertNotIn("scene_id ==", body)


class TheConsoleLineTests(unittest.TestCase):
    def test_a_restate_prints_one_ascii_line_with_the_token(self):
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 37, "hp_max": 41}), 19, OCEAN_SCENE
        )
        line = exitv.console_line(resolved)
        self.assertEqual(line, line.encode("ascii").decode("ascii"))
        self.assertNotIn("\n", line)
        self.assertTrue(line.startswith(exitv.SCENE_EXIT_VITALS_CONSOLE_TOKEN))
        self.assertIn("x3=37", line)
        self.assertIn("x4=41", line)
        self.assertIn("scene=126", line)

    def test_a_refusal_shouts(self):
        line = exitv.console_line(
            exitv.resolve_for_scene_exit(_FakeStore({}), 20, OCEAN_SCENE)
        )
        self.assertTrue(line.startswith("!! "))
        self.assertIn(exitv.REASON_ROW_UNSEEDED, line)
        self.assertIn("restated=none", line)

    def test_a_guard_refusal_shouts_and_names_the_guard_reason(self):
        """pf-adversary `5vzis0` D9, the false-green shape: shouting only on
        the UNSEEDED reason, and printing `reason=none` on any other, both
        SURVIVED at `19 passed` -- so the round's headline path, a guard
        refusal, could print a line indistinguishable from a success.  The
        first draft only ever tested the unseeded refusal's shout."""
        resolved = exitv.resolve_for_scene_exit(
            _FakeStore({"hp_current": 50, "hp_max": 0}), 28, OCEAN_SCENE
        )
        line = exitv.console_line(resolved)
        self.assertTrue(line.startswith("!! "))
        self.assertIn(exitv.REASON_GUARD_REFUSED, line)
        self.assertNotIn("reason=none", line)
        self.assertIn("restated=none", line)
        self.assertEqual(line, line.encode("ascii").decode("ascii"))
        self.assertNotIn("\n", line)

    def test_the_line_names_the_boat_rows_it_refused_to_state(self):
        """D9: `refused = "none"` SURVIVED -- the boat-row refusal, which is
        the one fact this ticket turns on, was never printed by any test."""
        line = exitv.console_line(
            exitv.resolve_for_scene_exit(
                _FakeStore({"hp_current": 50, "hp_max": 100}), 29, OCEAN_SCENE
            )
        )
        for x in sel.ALTERNATE_PAIR:
            self.assertIn(f"x{x}", line.split("boat_rows_unstated=")[1])
        self.assertNotIn("boat_rows_unstated=none", line)

    def test_the_greppable_token_is_pinned_to_its_spelling(self):
        """D9: renaming the token to `XX` SURVIVED, because every assertion
        compared the token to itself.  An operator is told to grep for this
        exact string, so it is pinned as a literal here once."""
        self.assertEqual(
            exitv.SCENE_EXIT_VITALS_CONSOLE_TOKEN, "DB_SCENE_EXIT_VITALS"
        )
        self.assertEqual(
            exitv.REASON_ROW_UNSEEDED, "primary_pair_not_seeded_in_the_row"
        )
        self.assertEqual(
            exitv.REASON_GUARD_REFUSED, "hp_pair_guard_refused_the_restate"
        )
        self.assertEqual(
            exitv.REASON_ALTERNATE_UNOWNED,
            "boat_health_rows_have_no_column_on_this_server",
        )

    def test_the_line_carries_the_character_and_scene_it_was_asked_about(self):
        """D9: hardcoding `character_id=0` and `scene=0` both SURVIVED."""
        for character_id, scene in ((4242, OCEAN_SCENE), (7, SOME_OTHER_SCENE)):
            with self.subTest(who=(character_id, scene)):
                for typed in ({"hp_current": 5, "hp_max": 9}, {}):
                    line = exitv.console_line(
                        exitv.resolve_for_scene_exit(
                            _FakeStore(typed), character_id, scene
                        )
                    )
                    self.assertIn(f"character_id={character_id}", line)
                    self.assertIn(f"scene={scene}", line)

    def test_the_module_is_ascii_only(self):
        raw = MODULE_FILE.read_bytes()
        self.assertEqual(raw, raw.decode("ascii").encode("ascii"))


class ItReadsARealMigratedStoreTests(unittest.TestCase):
    def _store(self, directory):
        store = SQLiteStore(str(Path(directory) / "pf.db"), MIGRATIONS)
        store.migrate()
        return store

    def test_a_born_character_can_have_its_hp_restated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            account_id = store.ensure_account("exit-a")
            character = store.create_character(
                account_id, "ExitA", "a", "fingerprint-a", _build_wire,
                Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
            )
            resolved = exitv.resolve_for_scene_exit(store, character.id, OCEAN_SCENE)
            self.assertTrue(resolved.may_restate)
            self.assertEqual(set(resolved.rows), set(sel.PRIMARY_PAIR))
            self.assertNotIn(-1, resolved.rows.values())


if __name__ == "__main__":
    unittest.main()
