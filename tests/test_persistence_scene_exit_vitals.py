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
        self.assertEqual(
            exitv._PRIMARY_COLUMNS,
            tuple(compose.SERVER_OWNED_FIELDS[x].column for x in sel.PRIMARY_PAIR),
        )


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
