"""The level and HP a login sends come from the character's row.

Grades `src/pirateforce_foundation/persistence_login_vitals.py`, the LANE-DB
half of CORE-REQUEST `pf_bridge/notes_to_chief/20260902_1310_LANE-DB-CORE-
REQUEST-login-carries-hp-and-level-from-the-row.md` (`COO-DECISION
20260902_1143` points 1/2/4).

WHAT THIS FILE PROVES, AND THE MUTATION THAT REDDENS EACH GROUP
---------------------------------------------------------------
* `ResolverTests`        -- make any fallback branch return the row's numbers
                            anyway, or delete the `validate()` call.
* `AllThreeOrNoneTests`  -- return a dict carrying one row value next to two
                            literals from `wire_kwargs()`.
* `NoGuessedZeroTests`   -- substitute `0` for a missing or refused number
                            anywhere in the module.
* `ReasonsAreDistinctTests` -- collapse `row_has_no_value` and
                            `row_refused_by_vitals_gate` into one token, which
                            is the loss the request's point 2 is about: an
                            operator can no longer tell an UNSEEDED server
                            from a BROKEN row.
* `AgainstARealDatabaseTests` -- the M4 claim itself: damage a character
                            through `store.apply_hp_damage` and the next
                            resolve carries the damaged number, not 100.
                            Delete the store read and these go red.
* `TheModuleOwnsNoConstantsTests` -- write `100` or import `player_wire` into
                            the module, which is how a second copy of a wire
                            constant is born.

WHAT THIS FILE DOES NOT PROVE -- AND THE HOLE IS DELIBERATE
------------------------------------------------------------
!! NOTHING HERE DRIVES A LOGIN.  At the commit that adds this file the module
is not called from anywhere (`grep -rn persistence_login_vitals src/` finds
the module and nothing else): the two seams the request asks for live in
`legacy_bridge.start_game` and `session.py`, both OUTSIDE this lane's write
zone, and they are chief's to write.  That is exactly the gap R309's defect
D5 warns about -- "every test drove the module and none drove the seam" --
and this file may not pretend otherwise.  It is named here rather than left
for a reader to discover, and the seam-level group belongs in the round that
lands the seam.

Nothing here is client-observable either.  And on a FRESH database no byte
changes at all: `persistence_vitals.new_character_vitals()` seeds a newborn at
`level 1, hp 100/100`, which is what the login literals already say.  The
bytes differ only for a row something moved, which is why
`AgainstARealDatabaseTests` moves one.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_login_vitals as login_vitals  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MODULE_SOURCE = ROOT / "src" / "pirateforce_foundation" / "persistence_login_vitals.py"

# The three numbers a login sends today, read from the production module that
# owns them rather than retyped, so that the day one of them changes this file
# grades the NEW literal instead of quietly grading a stale one.  `level` has
# a name in `player_wire`; the two HP numbers do not yet -- they are bare
# literals in the return expression of `_make_actor_attr_with_name_and_class`
# at `player_wire.py:283-284`, which is the composer the login path really
# uses.  (The identical pair at `:202-203` belongs to the FROZEN
# `_make_actor_attr_with_name` the login no longer calls; CORE-REQUEST
# `20260902_1310` cited that one by mistake.)
from pirateforce_foundation.player_wire import PLAYER_LOGIN_LEVEL  # noqa: E402

FALLBACK_LEVEL = PLAYER_LOGIN_LEVEL
FALLBACK_HP_CURRENT = 100
FALLBACK_HP_MAX = 100

FALLBACKS = dict(
    fallback_level=FALLBACK_LEVEL,
    fallback_hp_current=FALLBACK_HP_CURRENT,
    fallback_hp_max=FALLBACK_HP_MAX,
)

# Numbers that are NOT the literals, so a resolution carrying them cannot be a
# resolution that ignored the row.
ROW_LEVEL = 7
ROW_HP_CURRENT = 37
ROW_HP_MAX = 250


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


def _resolution(level=ROW_LEVEL, hp_current=ROW_HP_CURRENT, hp_max=ROW_HP_MAX):
    """A `VitalsResolution` built the way the store builds one: through
    `persistence_vitals.resolve`, so the gate's own rules decide the gaps
    rather than this file asserting what they should be."""
    stored = {}
    if level is not None:
        stored[vitals.LEVEL_COLUMN] = level
    if hp_current is not None:
        stored[vitals.HP_CURRENT_COLUMN] = hp_current
    if hp_max is not None:
        stored[vitals.HP_MAX_COLUMN] = hp_max
    return vitals.resolve(stored)


class _StoreStub:
    """`read_character_vitals` and nothing else."""

    def __init__(self, resolution=None, raises=None):
        self._resolution = resolution
        self._raises = raises
        self.seen = []

    def read_character_vitals(self, character_id):
        self.seen.append(character_id)
        if self._raises is not None:
            raise self._raises
        return self._resolution


class ResolverTests(unittest.TestCase):
    """One branch per reason, and each one says which value goes out."""

    def test_a_complete_consistent_row_is_what_the_login_sends(self):
        resolved = login_vitals.resolve(_resolution(), **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.FROM_ROW)
        self.assertTrue(resolved.came_from_the_row)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, ROW_HP_CURRENT, ROW_HP_MAX),
        )

    def test_a_row_with_nothing_seeded_sends_the_literals(self):
        resolved = login_vitals.resolve(
            _resolution(level=None, hp_current=None, hp_max=None), **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_HAS_NO_VALUE)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
        )

    def test_one_missing_column_sends_the_literals_and_names_the_column(self):
        resolved = login_vitals.resolve(
            _resolution(hp_max=None), **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)
        self.assertIn(vitals.HP_MAX_COLUMN, resolved.detail)

    def test_an_inconsistent_row_is_refused_and_is_not_the_unseeded_reason(self):
        """`hp_current > hp_max` is a row that HAS values and is broken."""
        resolved = login_vitals.resolve(
            _resolution(hp_current=90, hp_max=10), **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)
        self.assertIn(vitals.REASON_HP_ABOVE_MAX, resolved.detail)

    def test_a_level_zero_row_is_refused_by_the_gate_not_sent(self):
        resolved = login_vitals.resolve(_resolution(level=0), **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)
        self.assertEqual(resolved.level, FALLBACK_LEVEL)

    def test_a_dead_row_sends_the_literals_under_its_own_reason(self):
        """`hp_current = 0` is a VALUE (the character died), not an absence,
        so it gets its own token -- and the module takes the option that
        cannot regress anything while the decision is asked for by letter."""
        resolved = login_vitals.resolve(
            _resolution(hp_current=0), **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_HP_NOT_POSITIVE)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
        )

    def test_a_number_the_encoder_would_refuse_sends_the_literals(self):
        """Defence in depth, and MEASURED as such rather than advertised as
        the front door.

        `persistence_vitals.resolve` RAISES `VitalsError` for a stored number
        outside the column's range -- it never reaches a gap -- so a row like
        this arrives at `resolve_for_character` as an exception, not as a
        resolution (the test below).  This branch therefore guards a
        resolution built by HAND with such a number in it, which is the shape
        a future caller, or a future gate that reports instead of raising,
        would hand over.  Deleting the `validate()` call would let that number
        reach `legacy.u32tag`, where `struct.error` happens INSIDE a login.
        """
        handbuilt = vitals.VitalsResolution(
            present={
                vitals.LEVEL_COLUMN: ROW_LEVEL,
                vitals.HP_CURRENT_COLUMN: 2 ** 40,
                vitals.HP_MAX_COLUMN: 2 ** 40,
            },
            gaps=(),
        )
        resolved = login_vitals.resolve(handbuilt, **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VALIDATOR)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))

    def test_an_unstorable_number_in_the_row_is_a_refusal_not_a_crash(self):
        """The route such a row really takes: the gate raises, and a login
        must survive that too."""
        store = _StoreStub(
            raises=vitals.VitalsError("hp_current: 2**40 is outside u32"))
        resolved = login_vitals.resolve_for_character(store, 5, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_COULD_NOT_BE_READ)
        self.assertEqual(resolved.hp_current, FALLBACK_HP_CURRENT)

    def test_a_resolution_with_no_gaps_and_no_numbers_is_refused_not_crashed(self):
        """`persistence_vitals` documents this hand-built shape and refuses
        it; a login must not turn that refusal into a 500."""
        empty = vitals.VitalsResolution(present={}, gaps=())
        resolved = login_vitals.resolve(empty, **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)
        self.assertEqual(resolved.hp_current, FALLBACK_HP_CURRENT)

    def test_something_that_is_not_a_resolution_is_a_programming_error(self):
        with self.assertRaises(TypeError):
            login_vitals.resolve({"level": 1}, **FALLBACKS)

    def test_a_bool_fallback_is_refused_because_python_would_encode_it(self):
        bad = dict(FALLBACKS, fallback_hp_current=True)
        with self.assertRaises(TypeError):
            login_vitals.resolve(_resolution(), **bad)

    def test_a_float_fallback_is_refused_these_three_are_u32_fields(self):
        bad = dict(FALLBACKS, fallback_level=1.0)
        with self.assertRaises(TypeError):
            login_vitals.resolve(_resolution(), **bad)

    def test_an_unregistered_reason_cannot_be_constructed(self):
        with self.assertRaises(ValueError):
            login_vitals.ResolvedLoginVitals(1, 100, 100, "looks_fine")

    def test_a_read_that_raises_is_not_a_failed_login(self):
        store = _StoreStub(raises=KeyError(4321))
        resolved = login_vitals.resolve_for_character(store, 4321, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_COULD_NOT_BE_READ)
        self.assertIn("KeyError", resolved.detail)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
        )

    def test_the_read_goes_through_the_gap_carrying_door(self):
        """Point 2 of the request: `_or_none` throws the gaps away, so a
        broken row and an unseeded row would read identically."""
        store = _StoreStub(resolution=_resolution())
        login_vitals.resolve_for_character(store, 99, **FALLBACKS)
        self.assertEqual(store.seen, [99])
        self.assertFalse(
            hasattr(store, "read_character_vitals_or_none"),
            "this stub offers only the gap-carrying door on purpose")

    def test_the_console_line_is_ascii_and_names_the_reason(self):
        store = _StoreStub(raises=RuntimeError("ไม่มี"))
        resolved = login_vitals.resolve_for_character(store, 1, **FALLBACKS)
        line = resolved.console_line()
        self.assertTrue(all(32 <= ord(c) < 127 for c in line), line)
        self.assertIn(login_vitals.ROW_COULD_NOT_BE_READ, line)
        self.assertIn("LOGIN_VITALS", line)


class AllThreeOrNoneTests(unittest.TestCase):
    """No login block mixes a row value with a literal.  `PANYA-DECISION
    20260901_1059` bans a block whose unknown fields were guessed; a mixed
    block is that ban arriving one field at a time."""

    CASES = (
        ("nothing seeded", dict(level=None, hp_current=None, hp_max=None)),
        ("level only", dict(hp_current=None, hp_max=None)),
        ("hp pair only", dict(level=None)),
        ("hp_current missing", dict(hp_current=None)),
        ("hp_max missing", dict(hp_max=None)),
        ("level zero", dict(level=0)),
        ("hp above max", dict(hp_current=90, hp_max=10)),
        ("hp_max zero", dict(hp_current=0, hp_max=0)),
        ("dead", dict(hp_current=0)),
        ("complete", {}),
    )

    #: Resolutions no `persistence_vitals.resolve` call can produce today --
    #: it raises on these numbers rather than reporting them -- built by hand
    #: so the module's last line of defence is graded too.
    HANDBUILT = (
        ("unencodable", {
            vitals.LEVEL_COLUMN: ROW_LEVEL,
            vitals.HP_CURRENT_COLUMN: -5,
            vitals.HP_MAX_COLUMN: -5,
        }),
        ("no gaps and no numbers", {}),
    )

    @classmethod
    def every_resolution(cls):
        for label, kwargs in cls.CASES:
            yield label, _resolution(**kwargs)
        for label, present in cls.HANDBUILT:
            yield label, vitals.VitalsResolution(present=present, gaps=())

    def test_every_reason_sends_three_row_numbers_or_three_literals(self):
        literals = (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX)
        for label, resolution in self.every_resolution():
            with self.subTest(label):
                resolved = login_vitals.resolve(resolution, **FALLBACKS)
                sent = (resolved.level, resolved.hp_current, resolved.hp_max)
                if resolved.came_from_the_row:
                    self.assertEqual(
                        resolved.wire_kwargs(),
                        {"level": sent[0], "hp_current": sent[1],
                         "hp_max": sent[2]})
                else:
                    self.assertEqual(
                        sent, literals,
                        f"{label}: a refusal sent something that is neither "
                        "the row nor the caller's three literals")
                    self.assertEqual(
                        resolved.wire_kwargs(), {},
                        f"{label}: a refused resolution still handed the seam "
                        "keyword arguments, so the seam would send them")

    def test_the_keyword_names_are_the_ones_the_request_asked_chief_for(self):
        resolved = login_vitals.resolve(_resolution(), **FALLBACKS)
        self.assertEqual(
            sorted(resolved.wire_kwargs()),
            ["hp_current", "hp_max", "level"])


class NoGuessedZeroTests(unittest.TestCase):
    """The owner's standing rule, `PANYA-DECISION 20260901_1059`: an unknown
    field is never a zero."""

    def test_no_refusal_ever_substitutes_zero(self):
        for label, resolution in AllThreeOrNoneTests.every_resolution():
            with self.subTest(label):
                resolved = login_vitals.resolve(resolution, **FALLBACKS)
                self.assertNotIn(
                    0, (resolved.level, resolved.hp_current, resolved.hp_max),
                    f"{label}: a zero reached the wire numbers")

    def test_a_zero_hp_row_is_reported_as_a_value_not_as_an_absence(self):
        """The distinction the rule turns on: the module must not file a dead
        character under `row_has_no_value`."""
        resolved = login_vitals.resolve(
            _resolution(hp_current=0), **FALLBACKS)
        self.assertNotEqual(resolved.reason, login_vitals.ROW_HAS_NO_VALUE)
        self.assertEqual(resolved.reason, login_vitals.ROW_HP_NOT_POSITIVE)


class ReasonsAreDistinctTests(unittest.TestCase):
    def test_every_branch_this_file_drives_reports_a_registered_reason(self):
        for label, resolution in AllThreeOrNoneTests.every_resolution():
            with self.subTest(label):
                resolved = login_vitals.resolve(resolution, **FALLBACKS)
                self.assertIn(resolved.reason, login_vitals.REASONS)

    def test_an_unseeded_server_and_a_broken_row_do_not_read_alike(self):
        unseeded = login_vitals.resolve(
            _resolution(level=None, hp_current=None, hp_max=None), **FALLBACKS)
        broken = login_vitals.resolve(
            _resolution(hp_current=90, hp_max=10), **FALLBACKS)
        self.assertNotEqual(unseeded.reason, broken.reason)


class AgainstARealDatabaseTests(unittest.TestCase):
    """The M4 claim itself, on a database migrated by the real
    `migrations/` directory -- not a stub."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("login-vitals")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)

    def _born(self, tag="lv1"):
        return self.store.create_character(
            self.account_id, "Vital" + tag, tag, "fingerprint-" + tag,
            _build_wire, self.home)

    def test_a_newborn_resolves_from_the_row_at_the_seeded_numbers(self):
        character = self._born()
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        seeded = vitals.new_character_vitals()
        self.assertEqual(resolved.reason, login_vitals.FROM_ROW)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (seeded[vitals.LEVEL_COLUMN],
             seeded[vitals.HP_CURRENT_COLUMN],
             seeded[vitals.HP_MAX_COLUMN]))

    def test_a_fresh_install_sends_the_same_bytes_it_sends_today(self):
        """!! THE NONCLAIM, MEASURED.  The birth seed equals the login
        literals, so on a fresh database this module changes NOTHING on the
        wire.  A round that reports it as a visible win is reporting
        something nobody measured."""
        character = self._born("lv2")
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
            "the birth seed no longer equals the login literals -- which is "
            "GOOD NEWS, but this file's nonclaim has to be rewritten and the "
            "seam becomes observable")

    def test_damage_survives_and_is_what_the_next_login_would_send(self):
        """The hole M4 exists to close: beaten down, logged out, back at
        full health.  This is the first measurement that says otherwise."""
        character = self._born("lv3")
        before = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        outcome = self.store.apply_hp_damage(character.id, 63)

        after = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(after.reason, login_vitals.FROM_ROW)
        self.assertEqual(after.hp_current, outcome.hp_after)
        self.assertLess(after.hp_current, before.hp_current)
        self.assertNotEqual(
            after.hp_current, FALLBACK_HP_CURRENT,
            "a damaged character still resolves to the login literal, so the "
            "whole change is invisible")
        self.assertEqual(after.hp_max, before.hp_max)

    def test_a_character_beaten_to_zero_does_not_send_a_zero(self):
        character = self._born("lv4")
        self.store.apply_hp_damage(character.id, 10_000)
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_HP_NOT_POSITIVE)
        self.assertEqual(resolved.hp_current, FALLBACK_HP_CURRENT)

    def test_an_unknown_character_is_a_refusal_not_an_exception(self):
        resolved = login_vitals.resolve_for_character(
            self.store, 987654, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_COULD_NOT_BE_READ)

    def test_the_module_never_writes_to_the_database(self):
        """A resolver that writes is a resolver that can corrupt a login."""
        character = self._born("lv5")
        self.store.apply_hp_damage(character.id, 5)
        expected = self.store.read_character_vitals(character.id)
        for _ in range(3):
            login_vitals.resolve_for_character(
                self.store, character.id, **FALLBACKS)
        again = self.store.read_character_vitals(character.id)
        self.assertEqual(dict(again.present), dict(expected.present))


class TheModuleOwnsNoConstantsTests(unittest.TestCase):
    """The fallbacks are PARAMETERS.  The day this module writes one of the
    wire numbers down, there are two places to change and one of them will be
    missed."""

    def setUp(self):
        import ast
        self.tree = ast.parse(
            MODULE_SOURCE.read_text(encoding="utf-8"))
        self.ast = ast

    def _executable_nodes(self):
        """Every node except the docstrings.

        Graded on the PARSE rather than on the text on purpose: this module's
        prose quotes `player_wire.py:202-203` and the number 100 in the very
        sentences that explain why neither is imported, and a grep-based
        version of this test would forbid the explanation instead of the
        drift.  A first draft did exactly that and went red on its own
        docstring.
        """
        ast = self.ast
        docstrings = set()
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0]))
        for node in ast.walk(self.tree):
            if id(node) in docstrings:
                continue
            yield node

    def test_the_module_does_not_import_player_wire(self):
        ast = self.ast
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
                self.assertNotIn("player_wire", names)
                self.assertNotIn("player_wire", node.module or "")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("player_wire", alias.name)

    def test_no_wire_literal_is_written_down_in_the_module_code(self):
        ast = self.ast
        found = [
            node.value for node in self._executable_nodes()
            if isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
            and node.value in (100, 400, 400.0)
        ]
        self.assertEqual(
            found, [],
            "the module's CODE writes a login constant down; the three "
            "fallbacks are parameters so that each number lives in exactly "
            "one place")

    def test_the_module_is_not_wired_in_by_this_lane(self):
        """This lane's write zone stops at `persistence_*.py`; the seams are
        chief's.  If this ever fails it is GOOD NEWS -- the seam landed --
        and the right response is to move the seam's own tests into the round
        that landed it, not to loosen this."""
        seam = ROOT / "src" / "pirateforce_foundation" / "legacy_bridge.py"
        self.assertNotIn("persistence_login_vitals", seam.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
