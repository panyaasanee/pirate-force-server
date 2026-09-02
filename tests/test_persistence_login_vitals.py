"""The level and HP a login sends come from the character's row.

Grades `src/pirateforce_foundation/persistence_login_vitals.py`, the LANE-DB
half of CORE-REQUEST `pf_bridge/notes_to_chief/20260902_1310_LANE-DB-CORE-
REQUEST-login-carries-hp-and-level-from-the-row.md` (`COO-DECISION
20260902_1143` points 1/2/4).

WHAT THIS FILE PROVES, AND THE MUTATION THAT REDDENS EACH GROUP
---------------------------------------------------------------
!! EVERY MUTANT LISTED HERE WAS APPLIED AND MEASURED GOING RED.  Thirteen of
them are ones a `pf-adversary` pass drove straight through an earlier draft of
this file; each is named at the test that now kills it rather than quietly
patched.

* `ResolverTests`        -- make any fallback branch return the row's numbers
                            anyway; re-gate one column instead of three; move
                            the `resolve()` call back outside
                            `resolve_for_character`'s `try`; report only the
                            exception class instead of its message; take the
                            gap branch only for more than one gap; transpose
                            or hardcode a fallback slot; widen the console
                            filter from ASCII to latin-1.
* `AllThreeOrNoneTests`  -- return a dict carrying one row value next to two
                            literals from `wire_kwargs()`; skip the re-gate so
                            a gapless resolution holding `level = 0` or
                            `hp_max = 0` goes out as `FROM_ROW`.
* `NoGuessedZeroTests`   -- substitute `0` for a missing or refused number
                            anywhere in the module.
* `ReasonsAreDistinctTests` -- collapse `row_has_no_value` and
                            `row_refused_by_vitals_gate` into one token, OR
                            classify by counting gaps without reading their
                            reasons (three gaps is not the same thing as
                            three unseeded columns).  Either way an operator
                            can no longer tell an UNSEEDED server from a
                            BROKEN row, which is the loss the request's
                            point 2 is about.
* `AgainstARealDatabaseTests` -- the M4 claim itself: damage a character
                            through `store.apply_hp_damage` and the next
                            resolve carries the damaged number, not 100.
                            Delete the store read and these go red; so does
                            making the resolver write ANY column (the write
                            check hashes the database files, not three
                            columns of one character).
* `ReviveOnLoginTests`   -- `COO-DECISION 20260903_0250` option (khor).
                            Trust the write outcome instead of reading the
                            row back; call the write door on a branch that is
                            not the dead one; let a failed write fail the
                            login, or file it under the reason a SUCCESSFUL
                            revive uses; drop the shout from the failure's
                            console line.
* `TheModuleOwnsNoConstantsTests` -- write ANY of the three login constants
                            into the module, or import `player_wire` there.
                            The forbidden set is DERIVED from `player_wire`
                            (the level by name, the HP pair by parsing the
                            composer the login actually calls), so it cannot
                            go stale and cannot miss one.

WHAT THIS FILE DOES NOT PROVE -- AND THE HOLE IS DELIBERATE
------------------------------------------------------------
!! NOTHING HERE DRIVES A LOGIN.  At the commit that adds `apply_to_character`
the module is still not called from anywhere (`grep -rn persistence_login_
vitals src/` finds the module and nothing else): the seam lives in
`session.py` and the composer it feeds lives in `player_wire.py`, both OUTSIDE
this lane's write zone, and they are chief's to write.  That is exactly the
gap R309's defect D5 warns about -- "every test drove the module and none
drove the seam" -- and this file may not pretend otherwise.  It is named here
rather than left for a reader to discover, and the seam-level group belongs in
the round that lands the seam.

* `ApplyToCharacterTests` -- the seam's own half of `wire_kwargs()`, added so
                            that landing the seam is one line rather than a
                            block of fail-closed plumbing written at the call
                            site.  Mutate it to carry a refused resolution's
                            literals onto the character, to raise on an object
                            without the three fields (which is `model.
                            Character` TODAY), to apply one field without the
                            other two, or to report a `__post_init__` that
                            dropped a field as if it had carried it.

Nothing here is client-observable either.  And on a FRESH database no byte
changes at all: `persistence_vitals.new_character_vitals()` seeds a newborn at
`level 1, hp 100/100`, which is what the login literals already say.  The
bytes differ only for a row something moved, which is why
`AgainstARealDatabaseTests` moves one.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_login_vitals as login_vitals  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from test_persistence_typed_attr_columns import (  # noqa: E402
    NoHandleOutlivesItsTempDirMixin,
)

MIGRATIONS = ROOT / "migrations"
MODULE_SOURCE = ROOT / "src" / "pirateforce_foundation" / "persistence_login_vitals.py"

#: Directories the seam scan skips, and NOTHING ELSE IS SKIPPED.
#:
#: !! IT WALKS FROM `ROOT`, NOT A LIST OF TREES, AND THE LIST IS WHY.  This
#: file carried seven named trees -- the sibling scan's list -- and a
#: `pf-adversary` pass planted a real caller at `./login_seam.py` and at
#: `rounds/seam_under_rounds.py` and watched "nothing calls this module" stay
#: green.  `tests/test_persistence_vitals_heal.py` had already moved to a
#: full walk for exactly those two dodges, in this same lane, and this scan
#: -- the one defending the module's central nonclaim -- had not.  The
#: skip list matches that file's, third-party trees included, so an untracked
#: virtualenv cannot turn this red for code nobody here wrote.
SEAM_SCAN_SKIPPED = (
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "env", ".env", ".tox", "build", "dist", ".eggs",
    "site-packages", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
)

#: The files that name this module because grading it is their job.  Guarded
#: by `test_the_files_allowed_to_name_it_exist_and_really_name_it` below, so
#: an entry cannot rot into a blind spot the way the basename did.
NAMES_THE_MODULE_BY_CONSTRUCTION = frozenset({
    "tests/test_persistence_login_vitals.py",
    "tests/test_persistence_vitals.py",
    # `tests/test_persistence_vitals_heal.py` names this module because the
    # revive of `COO-DECISION 20260903_0250` made it the ONE authorised
    # caller of `store.restore_hp_to_full`, and that file's `AUTHORISED_
    # CALLS` map pins it by path.  Naming for grading, not wiring -- and
    # `test_no_allowlisted_file_actually_imports_the_module` below is what
    # keeps that distinction from being a licence.
    "tests/test_persistence_vitals_heal.py",
})

from pirateforce_foundation.player_wire import PLAYER_LOGIN_LEVEL  # noqa: E402

#: The composer the LOGIN path really reaches -- named by symbol, never by
#: line.  `persistence_vitals.py` records why: "a `pf-adversary` pass moved
#: those lines with an unrelated edit and every test in this lane stayed
#: green".  The identically-shaped literals in `_make_actor_attr_with_name`
#: belong to the FROZEN composer the login no longer calls, and CORE-REQUEST
#: `20260902_1310` (in `pf_bridge`, unopenable from this repository) cited
#: that one by mistake -- so this file must never grade it.
LOGIN_COMPOSER = "_make_actor_attr_with_name_and_class"

#: The ONE file a login seam for this module may live in, and the only path
#: the scan below lets past.  `COO-DECISION 20260903_0447` names the shape --
#: "one call point at the login path, no second one" -- and `session.py` is
#: where the sibling seam (`login_speed`) already went, for the reason its own
#: comment gives: it is the last layer that still holds BOTH a store and a
#: character id, and it is the object the three `start_game` recomposes in
#: `runtime.py` all re-read.  A caller anywhere else, or a SECOND caller here,
#: is what this file refuses -- not a caller as such.  It is written as a path
#: rather than a basename for the reason the scan below records: `src/
#: pirateforce_foundation/gm/session.py` is a filename another lane could
#: write next round.
THE_ONE_LOGIN_SEAM = "src/pirateforce_foundation/session.py"


def _hp_defaults_of(node, ast):
    """The `hp_current`/`hp_max` defaults a PARAMETERISED composer emits.

    `None` unless BOTH parameters exist with `int` defaults AND the body
    hands each of them to its own `u32tag(0x14, ...)` -- a parameter that
    exists and is never emitted is not the number on the wire, and reading
    its default would be this file inventing a pin.
    """
    defaults = {}
    args = node.args
    for group, group_defaults in (
        (args.args + args.posonlyargs, args.defaults),
        (args.kwonlyargs, args.kw_defaults),
    ):
        # `defaults` aligns with the TAIL of the positional list; `kw_
        # defaults` aligns one-to-one and holds `None` for a required one.
        if group is args.kwonlyargs:
            pairs = zip(group, group_defaults)
        else:
            pairs = zip(group[len(group) - len(group_defaults):], group_defaults)
        for arg, default in pairs:
            if (isinstance(default, ast.Constant)
                    and isinstance(default.value, int)
                    and not isinstance(default.value, bool)):
                defaults[arg.arg] = default.value
    if not {"hp_current", "hp_max"} <= set(defaults):
        return None
    emitted = {
        call.args[1].id
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "u32tag"
        and len(call.args) == 2
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value == 0x14
        and isinstance(call.args[1], ast.Name)
    }
    if not {"hp_current", "hp_max"} <= emitted:
        return None
    return [defaults["hp_current"], defaults["hp_max"]]


def _login_hp_literals():
    """The two `u32tag(0x14, N)` numbers `LOGIN_COMPOSER` emits, PARSED.

    A first draft said it parsed them and then copied `100` twice, which a
    `pf-adversary` pass caught: the day the login block's HP literals change,
    a copied pin keeps asserting a nonclaim about a number that is no longer
    on the wire, and its failure message names the wrong cause.  So they are
    read out of `player_wire`'s own syntax tree.  A parse that finds anything
    other than exactly two is an ERROR here rather than a silent skip: it
    means the composer changed shape and this file's premise needs rereading.
    """
    import ast
    source = (ROOT / "src" / "pirateforce_foundation" / "player_wire.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == LOGIN_COMPOSER:
            found = [
                call.args[1].value
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "u32tag"
                and len(call.args) == 2
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value == 0x14
                and isinstance(call.args[1], ast.Constant)
                and isinstance(call.args[1].value, int)
            ]
            if len(found) == 2:
                return found
            parameterised = _hp_defaults_of(node, ast)
            if parameterised is not None:
                # !! THIS BRANCH EXISTS SO THIS FILE CANNOT TAKE THE SEAM'S
                # OWN ROUND DOWN.  The CORE-REQUEST this lane sent chief asks
                # for exactly this change -- the HP pair becomes two keyword
                # parameters whose DEFAULTS are the numbers the composer used
                # to write inline -- and with only the branch above, the day
                # it lands this file raises at IMPORT time and every test in
                # it disappears from the run (measured: `1 error during
                # collection`, 0 of this file's tests executed).  A lane's
                # own guard erasing that lane's coverage the moment another
                # lane does what it asked for is the shape `COO-DECISION
                # 20260903_0447` was already closing one layer down.  The
                # numbers are still DERIVED, never copied: they are read off
                # the signature that feeds the same two `u32tag(0x14, ...)`
                # calls, so a default that drifts moves this file with it.
                return parameterised
            raise AssertionError(
                f"{LOGIN_COMPOSER} emits neither exactly two constant "
                f"u32tag(0x14, N) numbers (found {found}) nor an "
                "`hp_current`/`hp_max` parameter pair with int defaults that "
                "it passes to them; the HP pair this file pins has moved and "
                "the nonclaim below has to be re-read rather than re-run")
    raise AssertionError(
        f"player_wire no longer defines {LOGIN_COMPOSER}; this file's whole "
        "premise about which composer the login uses needs rereading")


FALLBACK_LEVEL = PLAYER_LOGIN_LEVEL
FALLBACK_HP_CURRENT, FALLBACK_HP_MAX = _login_hp_literals()

#: Every wire constant this module's fallbacks stand for, derived rather than
#: typed -- `TheModuleOwnsNoConstantsTests` forbids all of them in the
#: module's code.  A first draft forbade `100` and `400` and was blind to the
#: level, which is the number the request names first.
WIRE_CONSTANTS = frozenset(
    {FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX, 400, 400.0})

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

#: A fallback triple whose three members are DISTINCT.  The real one is
#: `(1, 100, 100)` and a `pf-adversary` pass measured what that hides:
#: transposing the two HP fallbacks inside the module is invisible when they
#: are equal.  Used only where the identity of each slot is what is on trial.
DISTINCT = dict(
    fallback_level=3, fallback_hp_current=11, fallback_hp_max=22)


def _module_imports_in(source):
    """Every import of this module in `source`, however it is spelled.

    PARSED, NOT GREPPED, and a `pf-adversary` pass is why: the substring
    version missed the plain dotted `import pirateforce_foundation.
    persistence_login_vitals`, `importlib.import_module("pirateforce_"
    "foundation.persistence_login_vitals")` (a split literal, the very dodge
    a sibling scan in this lane had already been fixed for) and
    `__import__(...)`.  Enumerating spellings is how a guard rots; asking the
    parser is not.
    """
    import ast

    name = "persistence_login_vitals"
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [name] if name in source else []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if name in a.name]
        elif isinstance(node, ast.ImportFrom):
            if name in (node.module or ""):
                found.append(node.module)
            found += [a.name for a in node.names if name in a.name]
        elif isinstance(node, ast.Call):
            called = getattr(node.func, "attr", None) or getattr(
                node.func, "id", None)
            if called in ("import_module", "__import__"):
                for argument in node.args:
                    if (isinstance(argument, ast.Constant)
                            and isinstance(argument.value, str)
                            and name in argument.value):
                        found.append(argument.value)
    return found


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


class _RefusingWriteStore:
    """A REAL store for reading; a write door that raises.

    Wrapping rather than faking, so the dead row the failure path meets is
    the one the real schema and the real `apply_hp_damage` produced.  Only
    the two doors this module uses are exposed: a stub that forwarded
    everything would let a future call to some third store method pass
    unnoticed, which is the shape this lane's nonclaims are made of.
    """

    def __init__(self, store, error):
        self._store = store
        self._error = error
        self.write_attempts = []

    def read_character_vitals(self, character_id):
        return self._store.read_character_vitals(character_id)

    def restore_hp_to_full(self, character_id):
        self.write_attempts.append(character_id)
        raise self._error


class _BlindAfterWriteStore:
    """The real store, whose SECOND read raises.

    The exact shape a `pf-adversary` pass used to measure the defect that
    made a third reason necessary: the revive write lands on disk and the
    read-back that was supposed to confirm it meets a locked database.  The
    write is forwarded to the real store, so the row really is healed while
    the module is blind to it.
    """

    def __init__(self, store, error):
        self._store = store
        self._error = error
        self.reads = 0

    def read_character_vitals(self, character_id):
        self.reads += 1
        if self.reads > 1:
            raise self._error
        return self._store.read_character_vitals(character_id)

    def restore_hp_to_full(self, character_id):
        return self._store.restore_hp_to_full(character_id)


class _WritesThenRaisesStore:
    """The real store, whose write door lands the write AND THEN raises.

    `SQLiteStore.connect()` commits when its `with` block exits and can still
    raise from the close that follows; a retrying or tracing store wrapped
    around a seam does the same trivially.  A `pf-adversary` pass used this
    shape to reproduce the round's own high defect after its first fix.
    """

    def __init__(self, store, error):
        self._store = store
        self._error = error

    def read_character_vitals(self, character_id):
        return self._store.read_character_vitals(character_id)

    def restore_hp_to_full(self, character_id):
        self._store.restore_hp_to_full(character_id)
        raise self._error


class _ReviveStoreStub:
    """A store whose read answers differently before and after the write.

    THE POINT OF THE `after` PARAMETER: the module must send what the row
    says AFTERWARDS, so a stub that cannot disagree with itself cannot grade
    it.  `after=None` means "the write changed nothing", which is the mutant
    a module trusting the write's own outcome would sail through.
    """

    def __init__(self, before, after=None, write_raises=None,
                 read_back_raises=None, outcome=None):
        self._before = before
        self._after = after
        self._write_raises = write_raises
        self._read_back_raises = read_back_raises
        self._outcome = outcome
        self.reads = 0
        self.writes = []

    def read_character_vitals(self, character_id):
        self.reads += 1
        if self.reads == 1:
            return self._before
        if self._read_back_raises is not None:
            raise self._read_back_raises
        return self._before if self._after is None else self._after

    def restore_hp_to_full(self, character_id):
        self.writes.append(character_id)
        if self._write_raises is not None:
            raise self._write_raises
        return self._outcome


class _HealOutcomeStub:
    """The three fields of a `persistence_vitals.HealOutcome` the module
    reads, and nothing else -- so a field it starts reading without this
    file's knowledge shows up as `None` in a detail rather than silently
    working."""

    def __init__(self, hp_before=None, hp_after=None, was_already_full=None):
        self.hp_before = hp_before
        self.hp_after = hp_after
        self.was_already_full = was_already_full


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
        """!! THE CHARACTERS HERE ARE THE ONES cp874 CANNOT ENCODE.

        A first draft fed a Thai word, and a `pf-adversary` pass measured that
        `"ไม่มี".encode("cp874")` SUCCEEDS -- cp874 IS the Thai code page.  So
        the one test defending the round-86/142 lesson was driven by a
        character that could never have caused it, and a latin-1 filter
        (`32 <= ord(c) < 256`) passed the whole suite.  `e-acute` and an em
        dash are what actually kill a cp874 console, and the gate runs under
        `PYTHONIOENCODING: cp874:strict`.
        """
        for hostile in ("\u00e9", "\u2014", "\u00b0", "\u0e44\u0e21\u0e48"):
            with self.subTest(repr(hostile)):
                store = _StoreStub(raises=RuntimeError(hostile))
                resolved = login_vitals.resolve_for_character(
                    store, 1, **FALLBACKS)
                line = resolved.console_line()
                self.assertTrue(all(32 <= ord(c) < 127 for c in line), line)
                line.encode("cp874")     # the console this really protects
                self.assertIn(login_vitals.ROW_COULD_NOT_BE_READ, line)
                self.assertIn("LOGIN_VITALS", line)

    def test_the_hostile_characters_are_really_hostile(self):
        """The control for the test above: `e-acute` must be a character
        cp874 refuses, or that test proves nothing."""
        with self.assertRaises(UnicodeEncodeError):
            "\u00e9".encode("cp874")

    def test_the_detail_carries_the_message_not_only_the_class(self):
        """The branch's stated value, graded.  "no such column: hp_current"
        and "database is locked" are both `OperationalError`; a line naming
        only the class cannot tell an operator which server they have."""
        store = _StoreStub(
            raises=RuntimeError("no such column: hp_current"))
        resolved = login_vitals.resolve_for_character(store, 1, **FALLBACKS)
        self.assertIn("no such column: hp_current", resolved.detail)
        self.assertIn("no such column: hp_current", resolved.console_line())

    def test_one_gap_takes_the_gap_branch_and_reads_as_a_gap_list(self):
        """Pins the branch, not just the token.  Narrowing `if gaps:` to
        `if len(gaps) > 1:` fell through to a different branch whose message
        happened to contain the same reason string."""
        resolved = login_vitals.resolve(_resolution(level=None), **FALLBACKS)
        self.assertEqual(
            resolved.detail,
            f"{vitals.LEVEL_COLUMN}[{vitals.REASON_NOT_SEEDED}]",
            "a single-gap resolution no longer reads as a gap list, so the "
            "gap branch and the exception branch cannot be told apart")

    def test_a_missing_hp_max_reports_both_of_its_gaps(self):
        """One missing column can raise TWO gaps, and both belong on the
        line: `hp_max` is unseeded AND the HP pair is incomplete."""
        resolved = login_vitals.resolve(_resolution(hp_max=None), **FALLBACKS)
        self.assertEqual(
            resolved.detail,
            f"{vitals.HP_MAX_COLUMN}[{vitals.REASON_NOT_SEEDED}]; "
            f"{vitals.HP_MAX_COLUMN}[{vitals.REASON_HP_PAIR_INCOMPLETE}]")

    def test_the_detail_names_every_gap_not_only_the_first(self):
        """An operator who fixes only the column the console named comes
        straight back to a line about the next one."""
        resolved = login_vitals.resolve(
            _resolution(level=0, hp_current=90, hp_max=10), **FALLBACKS)
        self.assertIn(vitals.REASON_LEVEL_ZERO, resolved.detail)
        self.assertIn(vitals.REASON_HP_ABOVE_MAX, resolved.detail)

    def test_each_fallback_slot_keeps_its_own_identity(self):
        """Transposing two fallbacks inside the module is invisible while the
        real triple is `(1, 100, 100)`."""
        resolved = login_vitals.resolve(
            _resolution(level=None, hp_current=None, hp_max=None), **DISTINCT)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (DISTINCT["fallback_level"],
             DISTINCT["fallback_hp_current"],
             DISTINCT["fallback_hp_max"]))

    def test_every_fallback_slot_refuses_a_bool_and_a_float(self):
        """One slot tested is one slot proved; the other two were not."""
        for slot in ("fallback_level", "fallback_hp_current", "fallback_hp_max"):
            for bad in (True, 1.0, "1", None):
                with self.subTest(slot=slot, bad=repr(bad)):
                    with self.assertRaises(TypeError):
                        login_vitals.resolve(
                            _resolution(), **dict(FALLBACKS, **{slot: bad}))

    def test_a_bad_fallback_is_refused_before_the_store_is_touched(self):
        """A wiring bug must not read as a database problem."""
        store = _StoreStub(resolution=_resolution())
        with self.assertRaises(TypeError):
            login_vitals.resolve_for_character(
                store, 1, **dict(FALLBACKS, fallback_hp_max=1.0))
        self.assertEqual(store.seen, [])


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
        # !! THE THREE A `pf-adversary` PASS DROVE STRAIGHT THROUGH.  A first
        # draft re-checked each column's RANGE and nothing else, so a gapless
        # resolution holding `level = 0` or `hp_max = 0` -- two states
        # `persistence_vitals` refuses BY NAME -- went out as `FROM_ROW` with
        # the zero on the wire.  These three are why this module re-runs the
        # whole gate instead of one third of it.
        ("gapless level zero", {
            vitals.LEVEL_COLUMN: 0,
            vitals.HP_CURRENT_COLUMN: 50,
            vitals.HP_MAX_COLUMN: 100,
        }),
        ("gapless hp_max zero", {
            vitals.LEVEL_COLUMN: ROW_LEVEL,
            vitals.HP_CURRENT_COLUMN: 5,
            vitals.HP_MAX_COLUMN: 0,
        }),
        ("gapless hp above max", {
            vitals.LEVEL_COLUMN: ROW_LEVEL,
            vitals.HP_CURRENT_COLUMN: 90,
            vitals.HP_MAX_COLUMN: 10,
        }),
        ("gapless float hp", {
            vitals.LEVEL_COLUMN: ROW_LEVEL,
            vitals.HP_CURRENT_COLUMN: 1.5,
            vitals.HP_MAX_COLUMN: 10,
        }),
        ("gapless level out of range", {
            vitals.LEVEL_COLUMN: 2 ** 40,
            vitals.HP_CURRENT_COLUMN: 5,
            vitals.HP_MAX_COLUMN: 10,
        }),
        ("gapless hp_max out of range", {
            vitals.LEVEL_COLUMN: ROW_LEVEL,
            vitals.HP_CURRENT_COLUMN: 5,
            vitals.HP_MAX_COLUMN: 2 ** 40,
        }),
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
                # `wire_matches_the_row`, not `came_from_the_row`: after
                # `COO-DECISION 20260903_0250` the two differ (a revived
                # login sends the row and DID write), and the question this
                # sweep asks is the wire's.
                if resolved.wire_matches_the_row:
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

    def test_a_gapless_resolution_still_meets_every_rule_of_the_gate(self):
        """Each of these is a shape the gate refuses BY NAME and a first draft
        sent anyway, because it re-checked ranges instead of re-running the
        gate.  Named one by one rather than left inside the sweep above: the
        sweep proves "not a mix", this proves "not sent"."""
        cases = {
            "gapless level zero": login_vitals.ROW_REFUSED_BY_VITALS_GATE,
            "gapless hp_max zero": login_vitals.ROW_REFUSED_BY_VITALS_GATE,
            "gapless hp above max": login_vitals.ROW_REFUSED_BY_VITALS_GATE,
            "gapless float hp": login_vitals.ROW_REFUSED_BY_VALIDATOR,
            "gapless level out of range": login_vitals.ROW_REFUSED_BY_VALIDATOR,
            "gapless hp_max out of range":
                login_vitals.ROW_REFUSED_BY_VALIDATOR,
        }
        by_label = dict(self.HANDBUILT)
        for label, expected in cases.items():
            with self.subTest(label):
                resolved = login_vitals.resolve(
                    vitals.VitalsResolution(present=by_label[label], gaps=()),
                    **FALLBACKS)
                self.assertEqual(resolved.reason, expected)
                self.assertEqual(
                    resolved.wire_kwargs(), {},
                    f"{label}: the gate refuses this row and the seam was "
                    "still handed keyword arguments")

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

    def test_three_gaps_are_not_the_same_thing_as_nothing_seeded(self):
        """!! THE MUTANT THIS EXISTS FOR: dropping the `all(reason ==
        NOT_SEEDED)` half of the classification left the suite green.

        A row with `level` NULL, `hp_current` NULL and `hp_max = 0` produces
        exactly THREE gaps -- as many as there are vital columns -- but one of
        them is a consistency failure, not an absence.  Counting alone prints
        "nothing is seeded on this server" about a database that holds a
        stored zero maximum, which is precisely the confusion the gap-carrying
        door was chosen to prevent.
        """
        resolution = _resolution(level=None, hp_current=None, hp_max=0)
        self.assertEqual(
            len(resolution.gaps), len(vitals.VITAL_COLUMNS),
            "this test needs a row whose gap COUNT matches the column count, "
            "or it is not driving the mutant it was written for")
        resolved = login_vitals.resolve(resolution, **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)

    def test_an_unseeded_server_and_a_broken_row_do_not_read_alike(self):
        unseeded = login_vitals.resolve(
            _resolution(level=None, hp_current=None, hp_max=None), **FALLBACKS)
        broken = login_vitals.resolve(
            _resolution(hp_current=90, hp_max=10), **FALLBACKS)
        self.assertNotEqual(unseeded.reason, broken.reason)


class AgainstARealDatabaseTests(
        NoHandleOutlivesItsTempDirMixin, unittest.TestCase):
    """The M4 claim itself, on a database migrated by the real
    `migrations/` directory -- not a stub.

    !! IT CARRIES THE LANE'S RUNTIME HANDLE GUARD, and that is worth more
    here than any AST pin: this class now WRITES to the database (see
    `_write_row`), and the mixin asks the operating system, after every test,
    whether anything still holds a descriptor under the temp directory.  That
    is the question the Windows gate asks by refusing the unlink -- the one
    that closed `#495` and `#610` -- rather than a question about how the
    source is spelled.  Registered after the directory's own cleanup so LIFO
    runs it first, while there is still something to ask about.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard_the_temp_dir(self.tmp)
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

    def _row_vitals(self, character_id):
        """The three columns AS THE DATABASE HOLDS THEM, through the store's
        own gap-carrying door -- so a test that says "the wire equals the
        row" is comparing against the row and not against its own copy."""
        return dict(
            self.store.read_character_vitals(character_id).present)

    def test_a_character_beaten_to_zero_is_revived_and_sent_as_the_row(self):
        """`COO-DECISION 20260903_0250` point 1+2 on a real database.

        The previous version of this test asserted the OPPOSITE -- a dead row
        sends the literals -- and it was right until the decision landed.  It
        is rewritten rather than deleted so a reader can see which behaviour
        moved and on whose authority.
        """
        character = self._born("lv4")
        self.store.apply_hp_damage(character.id, 10_000)
        dead = self._row_vitals(character.id)
        self.assertEqual(
            dead[vitals.HP_CURRENT_COLUMN], 0,
            "this test needs a row that really says the character is dead")

        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)

        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        after = self._row_vitals(character.id)
        self.assertEqual(
            after[vitals.HP_CURRENT_COLUMN], after[vitals.HP_MAX_COLUMN],
            "the login did not heal the row to its own maximum")
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (after[vitals.LEVEL_COLUMN],
             after[vitals.HP_CURRENT_COLUMN],
             after[vitals.HP_MAX_COLUMN]),
            "the wire and the row disagree, which is the whole thing the "
            "decision exists to end")
        self.assertEqual(
            after[vitals.HP_MAX_COLUMN], dead[vitals.HP_MAX_COLUMN],
            "the revive moved hp_max, so 'its own maximum' is not what "
            "happened")
        self.assertIn(
            "hp_before=%d" % dead[vitals.HP_CURRENT_COLUMN], resolved.detail,
            "the detail does not carry what the REAL HealOutcome reported, "
            "so a renamed field would print None on every login unnoticed")

    def test_the_revived_numbers_are_the_rows_and_not_the_literals(self):
        """The measurement the natural path above CANNOT make.

        A newborn's `hp_max` is `100`, which is also the login literal, so a
        revive of a freshly-killed newborn sends bytes that a module ignoring
        the row entirely would also send -- the same trap `COO-DECISION
        20260903_0054` caught the speed seam in.  So this one states a row
        whose three numbers are all different from the literals first.
        """
        character = self._born("lv8")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: ROW_LEVEL,
               vitals.HP_CURRENT_COLUMN: 0,
               vitals.HP_MAX_COLUMN: ROW_HP_MAX})
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX))
        self.assertEqual(
            resolved.wire_kwargs(),
            {"level": ROW_LEVEL, "hp_current": ROW_HP_MAX,
             "hp_max": ROW_HP_MAX},
            "a revived login handed the seam no keywords, so the seam would "
            "send its literals over a row that was just written")
        self.assertFalse(
            resolved.came_from_the_row,
            "a revived login reports itself as an untouched read, so a log "
            "cannot tell which logins wrote")
        self.assertTrue(resolved.wire_matches_the_row)

    def test_the_second_login_after_a_revive_is_an_ordinary_read(self):
        """The revive is not a state this module keeps re-entering: once the
        row is healed the next login is `FROM_ROW` and writes nothing."""
        character = self._born("lv9")
        self.store.apply_hp_damage(character.id, 10_000)
        first = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(
            first.reason, login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        fingerprint = self._database_fingerprint()
        second = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(second.reason, login_vitals.FROM_ROW)
        self.assertEqual(
            (second.level, second.hp_current, second.hp_max),
            (first.level, first.hp_current, first.hp_max))
        self.assertEqual(
            fingerprint, self._database_fingerprint(),
            "the login after a revive wrote to the database as well")

    def test_the_revive_branch_really_writes(self):
        """The positive control for the write check below.

        `test_the_module_never_writes_to_the_database` proves the OTHER
        branches leave the file alone; if nothing here ever wrote, that test
        would be green over a module that had lost the revive entirely.
        """
        character = self._born("lv10")
        self.store.apply_hp_damage(character.id, 10_000)
        before = self._database_fingerprint()
        login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertNotEqual(
            before, self._database_fingerprint(),
            "the revive wrote nothing, so the row is still dead and every "
            "assertion about it is green for the wrong reason")

    def test_a_write_that_raises_is_not_a_failed_login(self):
        """`COO-DECISION 20260903_0250` point 4, on the real schema.

        The store REALLY reads (so the dead row is the real one) and its
        write door raises the shape an operator actually meets -- a locked
        database.  Nothing about the login may change except the reason.
        """
        character = self._born("lv11")
        self.store.apply_hp_damage(character.id, 10_000)
        before = self._database_fingerprint()
        refusing = _RefusingWriteStore(
            self.store, sqlite3.OperationalError("database is locked"))

        resolved = login_vitals.resolve_for_character(
            refusing, character.id, **FALLBACKS)

        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
            "a failed revive sent something other than the three literals "
            "main sends today")
        self.assertEqual(resolved.wire_kwargs(), {})
        self.assertIn("database is locked", resolved.detail)
        self.assertEqual(
            before, self._database_fingerprint(),
            "the refused write reached the database anyway")
        self.assertEqual(
            self._row_vitals(character.id)[vitals.HP_CURRENT_COLUMN], 0,
            "the row was healed by a write that was supposed to have failed")

    # ---- the two branches that were unit-only until this round ----------

    def _write_row(self, character_id, **columns):
        """State a precondition on the real database instead of inheriting it.

        !! THROUGH `store.connect()`, WHICH IS A `@contextmanager` THAT
        CLOSES IN `finally`.  No raw `sqlite3.connect` enters this file, so
        it needs no handle pin of its own and adds no surface to the Windows
        `PermissionError [WinError 32]` trap that closed `#495`, `#610` and
        `#614`'s gate.  A first pass of this round deferred these two tests
        on the belief that reaching the database here MEANT a raw handle; a
        `pf-adversary` pass measured that belief false, and the reason is
        written here so no later round re-inherits it.
        """
        assignments = ", ".join("%s = ?" % name for name in columns)
        with self.store.connect() as db:
            db.execute(
                "UPDATE characters SET %s WHERE id = ?" % assignments,
                (*columns.values(), character_id))

    def test_a_row_with_no_values_sends_the_literals_on_a_real_database(self):
        """`ROW_HAS_NO_VALUE` driven against the real schema.

        Until this round both this branch and the one below were reachable
        only through a fake store.  `migrations/009` seeds every newborn, so
        the branch that used to be THE production branch is now reachable in
        production only on a pre-009 row -- which is exactly the shape that
        rots quietly.  The precondition is stated here, not inherited from a
        migration another lane owns, for the same reason
        `tests/test_login_speed.py::TheRealLoginPathTests` empties its own
        column instead of trusting `008`.
        """
        character = self._born("lv5")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: None,
               vitals.HP_CURRENT_COLUMN: None,
               vitals.HP_MAX_COLUMN: None})
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_HAS_NO_VALUE)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertEqual(
            resolved.wire_kwargs(), {},
            "an empty row must send the caller's literals through the "
            "caller's own path, not three keys of its own")

    def test_a_contradictory_row_is_refused_on_a_real_database(self):
        """`ROW_REFUSED_BY_VITALS_GATE`, driven the same way.

        `hp_current` above `hp_max` is the shape a half-applied write leaves
        behind, and the rule this lane exists for is that a field it cannot
        vouch for is never guessed at -- all three literals or all three from
        the row, never a mix (`PANYA-DECISION 20260901_1059`).
        """
        character = self._born("lv6")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: 7,
               vitals.HP_CURRENT_COLUMN: 90,
               vitals.HP_MAX_COLUMN: 10})
        resolved = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(
            resolved.reason, login_vitals.ROW_REFUSED_BY_VITALS_GATE)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
            "a refused row leaked one of its own numbers into the answer")
        self.assertEqual(resolved.wire_kwargs(), {})

    def test_the_two_fixtures_above_really_change_the_row(self):
        """The positive control for `_write_row`.

        Both tests above would pass just as well if the UPDATE silently wrote
        nothing and the resolver were refusing for some unrelated reason, so
        the fixture is measured rather than trusted.
        """
        character = self._born("lv7")
        before = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertEqual(before.reason, login_vitals.FROM_ROW)
        self._write_row(character.id, **{vitals.LEVEL_COLUMN: None})
        after = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)
        self.assertNotEqual(
            after.reason, login_vitals.FROM_ROW,
            "the fixture wrote nothing, so the two tests above are green for "
            "a reason that has nothing to do with what they claim")

    def test_an_unknown_character_is_a_refusal_not_an_exception(self):
        resolved = login_vitals.resolve_for_character(
            self.store, 987654, **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_COULD_NOT_BE_READ)

    def _database_fingerprint(self):
        """Every byte of the database, journals included.

        A first draft compared the three vital columns of ONE character, and a
        `pf-adversary` pass wrote `speed_walk` on every call straight through
        it -- which, one file over, would make each login rewrite the next
        login's movement speed.  A resolver may not write ANYTHING.
        """
        import hashlib
        digest = hashlib.sha256()
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = Path(str(self.path) + suffix)
            digest.update(suffix.encode("ascii"))
            digest.update(path.read_bytes() if path.exists() else b"<none>")
        return digest.hexdigest()

    def test_a_write_that_lands_while_the_read_back_fails_is_not_called_failed(self):
        """!! THE DEFECT A `pf-adversary` PASS MEASURED ON THIS DATABASE.

        The write reaches disk and the confirmation does not, and the first
        draft of this round answered `REVIVE_WRITE_FAILED` -- "the write did
        not happen" -- about a row that had just been healed from 0 to its
        maximum.  Wire and row disagreed on all three numbers through the
        token whose job was to stop exactly that.
        """
        character = self._born("lv12")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: ROW_LEVEL,
               vitals.HP_CURRENT_COLUMN: 0,
               vitals.HP_MAX_COLUMN: ROW_HP_MAX})
        blind = _BlindAfterWriteStore(
            self.store, sqlite3.OperationalError("database is locked"))

        resolved = login_vitals.resolve_for_character(
            blind, character.id, **FALLBACKS)

        self.assertEqual(
            resolved.reason,
            login_vitals.REVIVE_NOT_CONFIRMED)
        self.assertNotEqual(
            resolved.reason, login_vitals.REVIVE_WRITE_FAILED,
            "the row on disk was healed and the login says the row was read "
            "back and found dead")
        on_disk = self._row_vitals(character.id)
        self.assertEqual(
            on_disk[vitals.HP_CURRENT_COLUMN], ROW_HP_MAX,
            "this test needs the write to have LANDED, or it is measuring "
            "the ordinary failure path")
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX),
            "the module sent numbers it could not read")
        self.assertEqual(resolved.wire_kwargs(), {})
        self.assertTrue(resolved.console_line().startswith("!! LOGIN_VITALS "))

    def test_a_write_that_lands_then_raises_is_read_from_the_row(self):
        """!! THE SECOND PASS'S REPRODUCTION, ON THIS DATABASE.  The write
        reaches disk and the door raises afterwards -- a post-commit failure,
        or any wrapping store a seam is handed.  The first draft answered
        "the row still says hp_current=0" about a row holding 250."""
        character = self._born("lv14")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: ROW_LEVEL,
               vitals.HP_CURRENT_COLUMN: 0,
               vitals.HP_MAX_COLUMN: ROW_HP_MAX})
        store = _WritesThenRaisesStore(
            self.store, sqlite3.OperationalError("database is locked"))

        resolved = login_vitals.resolve_for_character(
            store, character.id, **FALLBACKS)

        on_disk = self._row_vitals(character.id)
        self.assertEqual(
            on_disk[vitals.HP_CURRENT_COLUMN], ROW_HP_MAX,
            "this test needs the write to have LANDED before the raise")
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX),
            "the login sent literals over a row that is alive on disk")
        self.assertNotIn(
            "still says", resolved.detail,
            "the answer asserts something about the database that the "
            "database does not say")

    def test_the_next_login_repairs_the_wire_after_a_blind_write(self):
        """The claim the token's comment makes, measured: the disagreement
        lasts one login.  Without this, "the next login repairs it" is a
        sentence nobody checked."""
        character = self._born("lv13")
        self._write_row(
            character.id,
            **{vitals.LEVEL_COLUMN: ROW_LEVEL,
               vitals.HP_CURRENT_COLUMN: 0,
               vitals.HP_MAX_COLUMN: ROW_HP_MAX})
        blind = _BlindAfterWriteStore(
            self.store, sqlite3.OperationalError("database is locked"))
        first = login_vitals.resolve_for_character(
            blind, character.id, **FALLBACKS)
        self.assertEqual(
            first.reason, login_vitals.REVIVE_NOT_CONFIRMED)

        second = login_vitals.resolve_for_character(
            self.store, character.id, **FALLBACKS)

        self.assertEqual(second.reason, login_vitals.FROM_ROW)
        self.assertEqual(
            (second.level, second.hp_current, second.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX))

    def test_the_module_never_writes_to_the_database(self):
        """A resolver that writes is a resolver that can corrupt a login.

        EVERY BRANCH EXCEPT THE REVIVE, and the exception is stated rather
        than left to be inferred from a fixture that happens to be alive:
        this character is damaged by five points, so it resolves `FROM_ROW`
        and the decision's one write is not in play.  The revive's own write
        is measured by `test_the_revive_branch_really_writes` above.
        """
        character = self._born("lv5")
        self.store.apply_hp_damage(character.id, 5)
        before = self._database_fingerprint()
        for _ in range(3):
            login_vitals.resolve_for_character(
                self.store, character.id, **FALLBACKS)
        self.assertEqual(
            before, self._database_fingerprint(),
            "resolving a login changed the database on disk")

    def test_the_fingerprint_notices_a_write(self):
        """The control: a fingerprint that never changes proves nothing."""
        character = self._born("lv6")
        before = self._database_fingerprint()
        self.store.apply_hp_damage(character.id, 1)
        self.assertNotEqual(before, self._database_fingerprint())


class ReviveOnLoginTests(unittest.TestCase):
    """`COO-DECISION 20260903_0250`: a dead row logs in, the server revives it.

    The decision's four points, each with the mutant it exists to kill:

    1. heal to the ROW's own `hp_max`, never a constant -- the store door
       does that arithmetic inside its own transaction, so the mutant here is
       this module writing a number of its own; graded on a real database in
       `AgainstARealDatabaseTests`.
    2. send WHAT WAS WRITTEN -- the mutant is trusting the write's outcome
       instead of reading the row back, which is invisible until a write
       silently does not land.
    3. its own reason and console line -- the mutant is filing either the
       revive or its failure under one of the five older reasons.
    4. a failed write never fails the login -- the mutant is any escaping
       exception, which `D1` measured parks the client on "connecting".
    """

    DEAD = dict(level=ROW_LEVEL, hp_current=0, hp_max=ROW_HP_MAX)
    HEALED = dict(level=ROW_LEVEL, hp_current=ROW_HP_MAX, hp_max=ROW_HP_MAX)
    CHARACTER = 4242

    def _resolve(self, store):
        return login_vitals.resolve_for_character(
            store, self.CHARACTER, **FALLBACKS)

    def test_a_dead_row_is_revived_and_the_answer_is_the_row_read_back(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED))
        resolved = self._resolve(store)
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX))
        self.assertEqual(store.writes, [self.CHARACTER])
        self.assertEqual(
            store.reads, 2,
            "the answer was not read back from the row after the write")

    def test_the_answer_is_the_read_back_and_not_the_write_outcome(self):
        """!! THE MUTANT THIS GROUP EXISTS FOR.  The write door reports
        success and the row is unchanged -- a lost update, a rolled-back
        transaction, a stub that lies.  A module that answered from the
        outcome object would send `hp_max` over a row still holding zero, and
        that is the wire-versus-row disagreement the decision ended."""
        store = _ReviveStoreStub(_resolution(**self.DEAD), after=None)
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertIn("STILL SAYS THE CHARACTER IS DEAD", resolved.detail)
        self.assertNotIn(
            "until the next login", resolved.detail,
            "a row that was read back and is still dead was promised a "
            "repair at a next login that will do exactly the same thing")
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertEqual(resolved.wire_kwargs(), {})

    def test_a_row_that_reads_back_broken_is_a_failure_not_a_revive(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            _resolution(level=ROW_LEVEL, hp_current=90, hp_max=10))
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_NOT_CONFIRMED)
        self.assertIn(
            login_vitals.ROW_REFUSED_BY_VITALS_GATE, resolved.detail,
            "the failure line does not say what the row read back as, so an "
            "operator cannot tell a lost write from a broken row")

    def test_a_write_that_raises_over_a_row_that_is_still_dead(self):
        """The door raised AND the row confirms nothing changed.  Only both
        halves together are `REVIVE_WRITE_FAILED`."""
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked"))
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertIn("database is locked", resolved.detail)
        self.assertIn(
            "OperationalError", resolved.detail,
            "the class was dropped, so two different faults read alike")
        self.assertIn("READ BACK", resolved.detail)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertEqual(
            store.reads, 2,
            "the module decided what the database holds without reading it")

    def test_a_write_that_raises_after_it_landed_is_not_called_a_failure(self):
        """!! THE DEFECT THE SECOND `pf-adversary` PASS REPRODUCED.

        A store that forwards the write and then raises -- a failure after
        the commit, or any wrapping/retrying store a seam is handed -- left
        the first draft printing "the row still says hp_current=0" about a
        row holding its maximum.  The rule is now that the ROW decides, on
        both paths, so this is a revive: the character is alive on disk.
        """
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED),
            write_raises=sqlite3.OperationalError("database is locked"))
        resolved = self._resolve(store)
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, ROW_HP_MAX, ROW_HP_MAX),
            "the wire does not carry the row the database actually holds")
        self.assertIn(
            "the write raised", resolved.detail,
            "the answer hides that the write door raised, so an operator "
            "never learns their database is throwing")

    def test_a_read_back_that_raises_is_not_a_failed_login(self):
        """!! AND IT IS NOT `REVIVE_WRITE_FAILED` EITHER.  A `pf-adversary`
        pass measured, on a real database, what folding these two together
        costs: the write landed (`hp_current` 0 -> 250 on disk), the
        read-back met a locked database, and the login announced that the
        write had not happened.  A write that returned and a row that cannot
        be confirmed is a third state and it says so."""
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            read_back_raises=sqlite3.OperationalError("no such column: hp_max"))
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_NOT_CONFIRMED)
        self.assertNotEqual(
            resolved.reason, login_vitals.REVIVE_WRITE_FAILED,
            "a row nobody could read is being reported as a row that was "
            "read and found dead, which is a false statement about the "
            "database")
        self.assertIn(
            "DOES NOT KNOW WHETHER THE CHARACTER IS ALIVE", resolved.detail,
            "the shouted warning this token exists for is not in the line an "
            "operator reads")
        self.assertIn("no such column", resolved.detail)
        self.assertEqual(resolved.wire_kwargs(), {})
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertTrue(
            resolved.console_line().startswith("!! LOGIN_VITALS "),
            "the state that most needs an operator is not shouted")

    def test_the_two_failure_tokens_are_not_the_same_event(self):
        """One says the door refused, the other says the door returned.  A
        module that answers both with one token tells an operator to go
        looking for a write that did happen."""
        confirmed_dead = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked")))
        unreadable = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            read_back_raises=sqlite3.OperationalError("database is locked")))
        self.assertEqual(
            confirmed_dead.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(
            unreadable.reason, login_vitals.REVIVE_NOT_CONFIRMED)
        self.assertNotEqual(confirmed_dead.reason, unreadable.reason)
        raised, returned = confirmed_dead, unreadable
        for resolved in (raised, returned):
            self.assertEqual(resolved.wire_kwargs(), {})
            self.assertNotIn(
                resolved.reason, login_vitals.WIRE_TAKES_THE_ROWS_NUMBERS)

    def test_a_write_that_healed_nothing_does_not_claim_it_healed(self):
        """The concurrency case, without the concurrency.  The loser of the
        `BEGIN IMMEDIATE` race gets `was_already_full` and writes nothing;
        the row is alive, so the answer stands -- but the DETAIL may not say
        this login healed it."""
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED),
            outcome=_HealOutcomeStub(
                hp_before=ROW_HP_MAX, hp_after=ROW_HP_MAX,
                was_already_full=True))
        resolved = self._resolve(store)
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertIn("was_already_full=True", resolved.detail)

    def test_a_row_that_reads_back_alive_but_not_full_says_so(self):
        """Damage landing between the write and the read-back.  The wire
        still matches the row -- that is the rule -- but the detail may not
        go on saying "healed to its own hp_max" over a row holding 1."""
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            _resolution(level=ROW_LEVEL, hp_current=1, hp_max=ROW_HP_MAX))
        resolved = self._resolve(store)
        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (ROW_LEVEL, 1, ROW_HP_MAX),
            "the wire stopped matching the row")
        self.assertIn("which is NOT its own", resolved.detail)

    def test_a_store_with_no_write_door_is_not_a_failed_login(self):
        """The seam may be handed a store that predates this method, or a
        test double.  An `AttributeError` here would unwind the listener
        thread exactly as the read path's `TypeError` did."""
        store = _StoreStub(resolution=_resolution(**self.DEAD))
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertIn("AttributeError", resolved.detail)

    def test_no_other_reason_touches_the_write_door(self):
        """One write, on one branch.  Every other resolution the module can
        reach must leave the database alone -- this is the unit half of the
        fingerprint check on the real database."""
        for label, resolution in AllThreeOrNoneTests.every_resolution():
            with self.subTest(label):
                store = _ReviveStoreStub(
                    resolution, _resolution(**self.HEALED))
                resolved = login_vitals.resolve_for_character(
                    store, self.CHARACTER, **FALLBACKS)
                if label == "dead":
                    self.assertEqual(
                        store.writes, [self.CHARACTER],
                        "the one branch the decision authorises did not "
                        "write")
                    self.assertEqual(
                        resolved.reason,
                        login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
                else:
                    self.assertEqual(
                        store.writes, [],
                        f"{label}: a login that is not a dead row wrote to "
                        "the character's row")

    def test_the_pure_resolver_never_revives_and_needs_no_store(self):
        """The boundary: `resolve()` has no store, so it reports the dead row
        and carries the literals.  A caller reaching it directly is told the
        truth and sends what `main` sends."""
        resolved = login_vitals.resolve(
            _resolution(**self.DEAD), **FALLBACKS)
        self.assertEqual(resolved.reason, login_vitals.ROW_HP_NOT_POSITIVE)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertEqual(resolved.wire_kwargs(), {})

    def test_the_failure_line_is_shouted_and_carries_the_decisions_spelling(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked"))
        line = self._resolve(store).console_line()
        self.assertTrue(
            line.startswith("!! LOGIN_VITALS "),
            f"the failure line is not shouted: {line!r}")
        self.assertIn("REVIVE_WRITE_FAILED", line)
        self.assertEqual(
            line, "".join(c if 32 <= ord(c) < 127 else "?" for c in line),
            "the shouted line stopped being ASCII, which kills the cp874 "
            "bridge console mid-report")

    def test_the_revived_line_names_its_own_token_and_is_not_shouted(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED))
        line = self._resolve(store).console_line()
        self.assertFalse(line.startswith("!!"))
        self.assertIn(
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN, line)
        self.assertIn("hp=%d/%d" % (ROW_HP_MAX, ROW_HP_MAX), line)

    def test_the_reported_fields_are_the_ones_HealOutcome_really_has(self):
        """!! THE MUTANT: read `hp_start`/`hp_end`, names the dataclass does
        not have, and every test stayed green while every production revive
        printed `None`.  The fragment is tied to the real class here."""
        for field in ("hp_before", "hp_after", "was_already_full"):
            with self.subTest(field=field):
                self.assertIn(
                    field, vitals.HealOutcome.__annotations__,
                    "%s is not a field of persistence_vitals.HealOutcome, so "
                    "the write report reads None on every login" % field)
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED),
            outcome=_HealOutcomeStub(
                hp_before=0, hp_after=ROW_HP_MAX, was_already_full=False))
        detail = self._resolve(store).detail
        for expected in ("hp_before=0", "hp_after=%d" % ROW_HP_MAX,
                         "was_already_full=False"):
            self.assertIn(
                expected, detail,
                "the write's own account of itself is not in the answer")

    def test_a_hostile_outcome_cannot_kill_the_console_or_the_login(self):
        """The bridge console is cp874 and one byte outside it kills the tool
        mid-report.  `detail` is filtered AT THE SOURCE, not only inside
        `console_line`, because a log line or a debugger reads `detail`
        directly."""
        class _Unprintable:
            def __str__(self):
                raise RuntimeError("this value refuses to be rendered")

        cases = {
            "non ascii": _HealOutcomeStub(hp_before="\u0e44\u0e21\u00e9"),
            "enormous": _HealOutcomeStub(hp_before="x" * 500_000),
            "unrenderable": _HealOutcomeStub(hp_before=_Unprintable()),
        }
        for label, outcome in cases.items():
            with self.subTest(label):
                resolved = self._resolve(_ReviveStoreStub(
                    _resolution(**self.DEAD), _resolution(**self.HEALED),
                    outcome=outcome))
                self.assertEqual(
                    resolved.reason,
                    login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
                for text in (resolved.detail, resolved.console_line(),
                             repr(resolved)):
                    text.encode("cp874")
                    self.assertEqual(
                        text,
                        "".join(
                            c if 32 <= ord(c) < 127 else "?" for c in text),
                        "a byte outside the console's page reached a reader "
                        "of this answer")
                self.assertLess(
                    len(resolved.detail), 2000,
                    "one console event grew past what an operator can read")

    def test_an_exception_that_cannot_be_printed_does_not_escape(self):
        """A `pf-adversary` pass drove an exception whose own `__str__`
        raises straight THROUGH the handler written to stop it."""
        class _Unspeakable(Exception):
            def __str__(self):
                raise RuntimeError("even the message refuses")

        resolved = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD), write_raises=_Unspeakable()))
        self.assertIn(resolved.reason, login_vitals.REASONS)
        self.assertIn("_Unspeakable", resolved.detail)

    def test_every_shouted_answer_says_what_the_operator_must_do_about_it(self):
        """The capitals are the claim this round leads with, so they are
        graded.  Mutants that lowercase the warning or delete it survived
        until this test."""
        unreadable = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            read_back_raises=sqlite3.OperationalError("database is locked")))
        failed = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked")))
        self.assertIn(
            "THE ROW COULD NOT BE READ BACK", unreadable.detail)
        self.assertIn(
            "the wire may disagree with the row", unreadable.detail)
        self.assertIn("STILL SAYS THE CHARACTER IS DEAD", failed.detail)
        for resolved in (unreadable, failed):
            self.assertTrue(
                resolved.console_line().startswith("!! LOGIN_VITALS "))
            self.assertIn(
                resolved.reason.upper(), resolved.console_line(),
                "the shouted line no longer carries the token an operator "
                "greps for")

    def test_neither_new_answer_ever_carries_a_zero(self):
        """`PANYA-DECISION 20260901_1059` still holds over the new branch."""
        for label, store in (
                ("revived", _ReviveStoreStub(
                    _resolution(**self.DEAD), _resolution(**self.HEALED))),
                ("failed", _ReviveStoreStub(
                    _resolution(**self.DEAD),
                    write_raises=RuntimeError("no"))),
        ):
            with self.subTest(label):
                resolved = self._resolve(store)
                self.assertNotIn(
                    0,
                    (resolved.level, resolved.hp_current, resolved.hp_max))

    def test_both_new_reasons_are_registered_and_distinct(self):
        self.assertIn(
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
            login_vitals.REASONS)
        self.assertIn(login_vitals.REVIVE_WRITE_FAILED, login_vitals.REASONS)
        self.assertNotEqual(
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
            login_vitals.ROW_HP_NOT_POSITIVE,
            "a revive and a refusal share one token, so no console reader "
            "can tell whether the server wrote")
        self.assertNotIn(
            login_vitals.REVIVE_WRITE_FAILED,
            login_vitals.WIRE_TAKES_THE_ROWS_NUMBERS,
            "a failed write is listed as an answer that matches the row")

    def test_a_revive_is_never_filed_under_an_absence(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD), _resolution(**self.HEALED))
        resolved = self._resolve(store)
        self.assertNotEqual(resolved.reason, login_vitals.ROW_HAS_NO_VALUE)
        self.assertNotEqual(
            resolved.reason, login_vitals.ROW_COULD_NOT_BE_READ,
            "a write that succeeded is being reported as a read that could "
            "not happen")


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
        skip = set()
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    # BOTH the `Expr` and the `Constant` under it.  A first
                    # draft skipped only the `Expr`, so `ast.walk` still
                    # yielded the docstring itself -- harmless only by
                    # accident, because the numeric filter dropped strings.
                    skip.add(id(body[0]))
                    skip.add(id(body[0].value))
        for node in ast.walk(self.tree):
            if id(node) not in skip:
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
            and node.value in WIRE_CONSTANTS
        ]
        self.assertEqual(
            found, [],
            f"the module's CODE writes one of {sorted(WIRE_CONSTANTS)} down; "
            "the three fallbacks are parameters so that each number lives in "
            "exactly one place.  A first draft forbade 100 and 400 only, and "
            "was blind to the LEVEL -- the number the request names first")

    def test_the_docstring_exclusion_really_excludes_the_docstring(self):
        """The control for `_executable_nodes`.  Without it, a group that
        finds nothing cannot be told from a group that looks at nothing."""
        ast = self.ast
        kept = [
            n.value for n in self._executable_nodes()
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "IT DOES NOT CLAIM" in n.value
        ]
        self.assertEqual(kept, [], "the module docstring was not excluded")
        self.assertTrue(
            any(isinstance(n, ast.FunctionDef) for n in self._executable_nodes()),
            "the walker excluded everything, so it grades nothing")

    def test_the_module_has_at_most_one_seam_and_it_is_the_login_one(self):
        """Zero callers or one, and the one may only be `THE_ONE_LOGIN_SEAM`.

        !! THIS USED TO SAY "NOTHING CALLS IT", AND THAT SPELLING WAS ITSELF A
        TRAP FOR THE ROUND THAT LANDS THE SEAM.  `COO-DECISION 20260903_0447`
        ordered the seam wired and this file, owned by the lane that wrote the
        module, would have turned the seam's own landing RED -- a lane holding
        another lane's work hostage with a test of its own.  So the guard now
        pins what the decision actually asked for ("one call point at the
        login path, no second one") instead of the absence that preceded it:
        a caller at `session.py` passes, a caller anywhere else fails, and two
        callers fail.  The seam's own tests still belong to the round that
        lands it -- this only stops being the thing that blocks it.

        ALL of `src/`, not one file: a first draft checked `legacy_bridge.py`
        alone, and `session.py` is the likelier landing site (it is where
        `login_speed` went), so the nonclaim could have gone stale with the
        suite green.  And not `src/` alone either: the sibling caller scan in
        `tests/test_persistence_vitals.py` reads seven trees, and this one
        read one until a `pf-adversary` pass put a working caller in `tools/`
        and measured this test GREEN -- `tools/` is not a hiding place, the
        gate runs the headless replay scripts that live there.  Same seven
        trees now, same `errors="replace"`, same allowlist-with-a-guard shape.

        !! THE EXCLUSION IS BY RESOLVED PATH AND NOT BY BASENAME, AND THAT
        DISTINCTION WAS ALREADY WRITTEN DOWN IN THIS LANE BEFORE THIS FILE
        SPELLED IT WRONG.  `tests/test_persistence_vitals.py` carries a
        comment saying a `pf-adversary` pass broke the basename spelling of
        its own allowlist twice, and that `src/pirateforce_foundation/gm/` is
        a directory another lane writes in every round -- so a real seam
        landing at `src/pirateforce_foundation/gm/persistence_login_vitals.py`
        is not a hypothetical filename.  MEASURED: with `path.name !=`, a
        decoy at that path holding `from .. import persistence_login_vitals`
        and a `resolve_for_character(...)` call left this test GREEN, and the
        same decoy renamed to `gm/login_vitals_seam.py` turned it RED -- so
        the hole was exactly the basename, not a dead scan.  `errors=
        "replace"` for the same reason its sibling scan uses it: one
        non-UTF-8 byte anywhere under `src/` would turn this into an ERROR
        charged to whichever lane is standing nearest.
        """
        importers = []
        seen = 0
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".pyw", ".pyi"):
                continue
            relative = path.relative_to(ROOT).as_posix()
            if any(part in SEAM_SCAN_SKIPPED for part in relative.split("/")):
                continue
            seen += 1
            if relative in NAMES_THE_MODULE_BY_CONSTRUCTION:
                continue
            if path.resolve() == MODULE_SOURCE.resolve():
                continue
            if "persistence_login_vitals" in path.read_text(
                    encoding="utf-8", errors="replace"):
                importers.append(relative)
        self.assertGreater(
            seen, 100,
            "the walk found almost nothing, so a green result here would "
            "mean the scan is broken rather than that nothing calls it")
        self.assertEqual(
            sorted(set(importers) - {THE_ONE_LOGIN_SEAM}), [],
            "this module may be named from exactly one place under `src/` -- "
            "%s -- and it is named from somewhere else, so the login now has "
            "a second seam or a seam in the wrong layer (`COO-DECISION "
            "20260903_0447`: one call point, no second one)" % THE_ONE_LOGIN_SEAM)

    def test_no_allowlisted_file_actually_imports_the_module(self):
        """The allowlist is the scan's only hole, so nothing in it may be a
        real caller.  This file is the exception BY DEFINITION -- it is the
        one that drives the module -- and every other entry may mention the
        name and nothing more."""
        this_file = Path(__file__).resolve().relative_to(ROOT).as_posix()
        for relative in sorted(NAMES_THE_MODULE_BY_CONSTRUCTION):
            if relative == this_file:
                continue
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(
                    encoding="utf-8", errors="replace")
                self.assertEqual(
                    [], _module_imports_in(text),
                    "%s is allowed to NAME this module and IMPORTS it, so "
                    "the allowlist is hiding a caller" % relative)
                for spelling in (
                    # A `pf-adversary` pass drove the dotted spelling
                    # (`import pirateforce_foundation.persistence_login_
                    # vitals as _lv`) straight through the first three, which
                    # is the natural way to write it; the substring below
                    # covers that one and the plain `import` both.
                    "import persistence_login_vitals",
                    "persistence_login_vitals as ",
                    "from pirateforce_foundation.persistence_login_vitals",
                    "from pirateforce_foundation import "
                    "persistence_login_vitals",
                    "import_module(\"pirateforce_foundation."
                    "persistence_login_vitals\")",
                    "import_module('pirateforce_foundation."
                    "persistence_login_vitals')",
                ):
                    self.assertNotIn(
                        spelling, text,
                        "%s is allowed to NAME this module and is importing "
                        "it, so the allowlist is hiding a caller" % relative)

    def test_the_files_allowed_to_name_it_exist_and_really_name_it(self):
        """The allowlist above is the only way past the scan, so it is the
        only thing that can rot it.  A path that no longer exists, or that no
        longer names the module, is an entry silently widening the scan's
        blind spot -- the same defect as the basename, one indirection out."""
        for relative in sorted(NAMES_THE_MODULE_BY_CONSTRUCTION):
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(
                    path.is_file(),
                    "%s is allowed to name this module and does not exist"
                    % relative)
                self.assertIn(
                    "persistence_login_vitals",
                    path.read_text(encoding="utf-8", errors="replace"),
                    "%s is allowed to name this module and does not name it, "
                    "so the entry is only widening the scan's blind spot"
                    % relative)


class ApplyToCharacterTests(unittest.TestCase):
    """`apply_to_character` puts the row's numbers on the object, or nothing.

    THE SEAM'S HALF, WRITTEN HERE SO THE SEAM IS ONE LINE.  `COO-DECISION
    20260903_0447` asked for one call point at the login path; everything that
    call point has to get right -- refuse a resolution whose numbers are the
    caller's literals, survive an object without the fields, never raise into
    a listener thread, and never report a carry it did not verify -- lives in
    this function instead of being retyped at a seam in another lane's file.
    """

    def _dataclass_character(self, **overrides):
        """A frozen dataclass shaped like `model.Character` AFTER the seam.

        Deliberately not `model.Character` itself: that class does not have
        the three fields today, and a test that needed it to would be a test
        that cannot run until another lane moves.  The real class is graded
        by `test_todays_real_character_is_returned_untouched` below, from the
        other side.
        """
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class SeamCharacter:
            id: int = 7
            name: str = "rowvit"
            level: int | None = None
            hp_current: int | None = None
            hp_max: int | None = None

        return SeamCharacter(**overrides)

    def _row(self, reason=login_vitals.FROM_ROW):
        """A resolution whose three numbers differ from every login constant.

        `7 / 37 / 250` for the reason `COO-DECISION 20260903_0447` gives in
        its own words: after `migrations/009` a fixture at the constants
        cannot tell "read the row" from "send the literal", because they are
        the same bytes.
        """
        return login_vitals.ResolvedLoginVitals(7, 37, 250, reason)

    def test_a_row_resolution_rides_the_character(self):
        carried = login_vitals.apply_to_character(
            self._dataclass_character(), self._row())
        self.assertEqual(
            (carried.level, carried.hp_current, carried.hp_max),
            (7, 37, 250))

    def test_the_revived_login_rides_too(self):
        """`REVIVED_ON_LOGIN` numbers were read BACK off the row, so they are
        the row's -- `wire_kwargs()` says so and this must agree with it."""
        carried = login_vitals.apply_to_character(
            self._dataclass_character(),
            self._row(login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN))
        self.assertEqual(
            (carried.level, carried.hp_current, carried.hp_max),
            (7, 37, 250))

    def test_every_literal_carrying_reason_leaves_the_object_alone(self):
        """Not "returns equal" -- returns THE SAME OBJECT.

        Identity, because that is what makes the refusal unmistakable: a copy
        that happens to be equal today is a copy some later field could make
        differ, and the promise this function makes about a refusal is that
        the login composes exactly what `main` composes.
        """
        character = self._dataclass_character()
        for reason in sorted(login_vitals.REASONS):
            if reason in login_vitals.WIRE_TAKES_THE_ROWS_NUMBERS:
                continue
            with self.subTest(reason=reason):
                resolved = self._row(reason)
                self.assertEqual(
                    {}, resolved.wire_kwargs(),
                    "the fixture no longer reaches the refusing branch")
                self.assertIs(
                    character,
                    login_vitals.apply_to_character(character, resolved))

    def test_the_real_character_is_safe_in_both_states_of_the_model(self):
        """`model.Character` today has no such fields, and this must not raise.

        !! THE ASSERTION IS PICKED FROM THE MODEL RATHER THAN FROM TODAY, AND
        THAT IS THIS FILE REFUSING TO BE A HOSTAGE AGAIN.  Pinning "the real
        character comes back untouched" would have gone red on the day the
        OTHER lane adds the three fields -- which is the change this lane's
        own CORE-REQUEST asks for -- so the lane that wants the seam would
        have been the lane blocking it (measured on a patched copy: this test
        was one of exactly three real failures the seam patch caused).  What
        must hold in BOTH states is the contract: a model without the fields
        is handed back untouched, a model with them carries the row, and
        neither raises.
        """
        from dataclasses import fields as dataclass_fields
        from pirateforce_foundation.model import Character, Position

        character = Character(
            1, 1, 0, "rowvit", b"", b"", 0, 0, Position(1, 0, 1.0, 2.0, 3.0))
        names = {f.name for f in dataclass_fields(Character)}
        result = login_vitals.apply_to_character(character, self._row())
        if set(login_vitals.CHARACTER_FIELDS) <= names:
            self.assertEqual(
                (result.level, result.hp_current, result.hp_max),
                (7, 37, 250),
                "the model grew the three fields, so a login must now carry "
                "the row's numbers on the real character")
        else:
            self.assertIs(
                character, result,
                "the model has no such fields, so this must be a no-op -- "
                "not a crash in the START_GAME_REQ handler")

    def test_an_object_that_is_not_a_dataclass_is_returned_untouched(self):
        class NotADataclass:
            level = None
            hp_current = None
            hp_max = None

        character = NotADataclass()
        self.assertIs(
            character,
            login_vitals.apply_to_character(character, self._row()))

    def test_a_partial_dict_carries_nothing(self):
        """All three or none, at this layer too (`PANYA-DECISION 20260901_1059`).

        The refusal is measured on a resolution that ANSWERS with two of the
        three, which is the shape a future `wire_kwargs()` bug would have.
        """
        class TwoOfThree:
            def wire_kwargs(self):
                return {"hp_current": 37, "hp_max": 250}

        character = self._dataclass_character()
        self.assertIs(
            character,
            login_vitals.apply_to_character(character, TwoOfThree()))
        self.assertIsNone(character.hp_current)

    def test_a_bool_is_not_an_int_here_either(self):
        """`True` is an `int` in python and would encode as `1` on the wire."""
        class BoolLevel:
            def wire_kwargs(self):
                return {"level": True, "hp_current": 37, "hp_max": 250}

        character = self._dataclass_character()
        self.assertIs(
            character,
            login_vitals.apply_to_character(character, BoolLevel()))

    def test_a_resolution_whose_door_raises_cannot_fail_a_login(self):
        class Hostile:
            def wire_kwargs(self):
                raise RuntimeError("no")

        character = self._dataclass_character()
        self.assertIs(
            character, login_vitals.apply_to_character(character, Hostile()))

    def test_a_character_whose_replace_raises_cannot_fail_a_login(self):
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Refuses:
            level: int | None = None
            hp_current: int | None = None
            hp_max: int | None = None

            def __post_init__(self):
                if self.level is not None:
                    raise ValueError("this object refuses to carry a level")

        character = Refuses()
        self.assertIs(
            character,
            login_vitals.apply_to_character(character, self._row()))

    def test_an_object_that_drops_the_field_is_not_reported_as_carrying_it(self):
        """The read back, one layer up from the one `COO-DECISION 20260903_0447`
        point 2 made a house rule: a `__post_init__` that normalises the value
        away hands back an object that does NOT carry the row, and returning it
        would be the seam claiming a carry nobody verified."""
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Clamps:
            level: int | None = None
            hp_current: int | None = None
            hp_max: int | None = None

            def __post_init__(self):
                object.__setattr__(self, "hp_current", 100)

        character = Clamps()
        self.assertIs(
            character,
            login_vitals.apply_to_character(character, self._row()))

    def test_a_field_whose_read_raises_is_not_reported_as_carrying_it(self):
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class RaisesOnRead:
            level: int | None = None
            _hp_current: int | None = None
            hp_max: int | None = None

            @property
            def hp_current(self):
                raise RuntimeError("this field cannot be read")

        # `replace` needs the init field name, so the property sits beside a
        # private one; what matters is that the READ BACK raises.
        character = RaisesOnRead()
        try:
            result = login_vitals.apply_to_character(character, self._row())
        except Exception as exc:   # noqa: BLE001 -- the whole point
            self.fail(f"a login must not fail here; got {exc!r}")
        self.assertIs(character, result)

    def test_the_read_back_reads_the_three_fields_it_names(self):
        """The read back spells the three attributes out (a computed name is
        forbidden in this module by the sibling call map), so a fourth field
        added to `CHARACTER_FIELDS` without a fourth read would be verified by
        nothing.  This is the test that keeps the two in step."""
        import ast

        source = MODULE_SOURCE.read_text(encoding="utf-8")
        node = next(
            n for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.FunctionDef) and n.name == "apply_to_character")
        read = {
            a.attr for a in ast.walk(node)
            if isinstance(a, ast.Attribute)
            and isinstance(a.value, ast.Name) and a.value.id == "carried"
        }
        self.assertEqual(set(login_vitals.CHARACTER_FIELDS), read)

    def test_the_three_field_names_are_the_three_wire_names(self):
        """One list, not two.  A fourth spelling is how they drift apart."""
        self.assertEqual(
            sorted(login_vitals.CHARACTER_FIELDS),
            sorted(self._row().wire_kwargs()))


def _vitals_aliases_in(text):
    """Every local name `text` binds this module to, via any import spelling."""
    import ast

    aliases = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "persistence_login_vitals":
                    aliases.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[-1] == "persistence_login_vitals":
                    aliases.add(a.asname or a.name.split(".")[0])
    return aliases


def _called_names_in(text):
    """Every attribute/name a call in `text` uses, as dotted strings."""
    import ast

    names = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        parts = []
        while isinstance(target, ast.Attribute):
            parts.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            parts.append(target.id)
        if parts:
            names.append(".".join(reversed(parts)))
    return names


class TheOneLoginSeamTests(unittest.TestCase):
    """What the seam must look like ON THE DAY it lands, graded from here.

    !! THIS GROUP IS DELIBERATELY QUIET TODAY AND SAYS SO.  The seam is in
    `session.py`, which this lane may not write; until the file names this
    module there is no seam to grade and these tests say that in an assertion
    rather than in a `skip` (a new skip is a thing this project counts, and a
    skip here would be a hole in the very guard `COO-DECISION 20260903_0447`
    asked for).  The moment the seam lands, the same tests start grading it --
    which is the only shape that does not need this lane to be awake at the
    same hour as the lane that lands it.
    """

    def setUp(self):
        self.path = ROOT / THE_ONE_LOGIN_SEAM
        self.text = self.path.read_text(encoding="utf-8", errors="replace")
        self.wired = "persistence_login_vitals" in self.text

    def test_the_seam_file_exists_at_the_path_this_file_allows(self):
        """The allowlisted path is a real file, or the scan's one hole leads
        nowhere and would never be noticed."""
        self.assertTrue(
            self.path.is_file(),
            "%s is the one path allowed to hold the seam and does not exist"
            % THE_ONE_LOGIN_SEAM)

    def test_a_seam_that_names_the_module_goes_through_both_doors(self):
        """Naming is not wiring.  A seam that imports the module and then
        composes its own numbers would pass the scan above and send the
        literals -- the exact "green test, unchanged wire" shape `COO-DECISION
        20260903_0054` caught `/speed` in."""
        called = _called_names_in(self.text)
        if not self.wired:
            # `resolve_for_character` is NOT a usable probe here: the sibling
            # seam `login_speed` exports a function of the same name and
            # `session.py` already calls it.  `apply_to_character` is this
            # module's alone, so it is the one that answers "wired without
            # being named".
            self.assertEqual(
                [], [n for n in called if n.endswith("apply_to_character")],
                "the seam calls this lane's `apply_to_character` without "
                "naming the module, so the caller scan cannot see it")
            return
        aliases = _vitals_aliases_in(self.text)
        self.assertNotEqual(
            set(), aliases,
            "the seam names this module in prose only -- no import binds it, "
            "so nothing here is calling it")
        for door in ("resolve_for_character", "apply_to_character"):
            with self.subTest(door=door):
                self.assertTrue(
                    any(name in {f"{alias}.{door}" for alias in aliases}
                        or name == door
                        for name in called),
                    "the login seam names this module but never calls "
                    "`%s`, so the row's numbers do not reach the character"
                    % door)

    def test_the_seam_does_not_call_the_resolver_twice(self):
        """One call point, no second one (`COO-DECISION 20260903_0447`).  Two
        resolves in one login is also two REVIVE writes, because
        `resolve_for_character` writes on the dead-row branch."""
        if not self.wired:
            return
        called = _called_names_in(self.text)
        aliases = _vitals_aliases_in(self.text)
        # BY ALIAS, NOT BY BARE NAME.  `login_speed.resolve_for_character` is
        # a different module's function of the same name, already called once
        # in this very file, so a bare-name count would read the speed seam as
        # a second vitals resolve and refuse a seam that is correct.
        mine = [n for n in called
                if n in {f"{alias}.resolve_for_character" for alias in aliases}]
        self.assertLessEqual(
            len(mine), 1,
            "the login seam resolves the vitals more than once, and each "
            "resolve of a dead row is another revive WRITE")

    def test_the_call_scan_really_sees_a_call(self):
        """The control.  Without it a seam could delete both doors and this
        group would stay green by looking at nothing."""
        sample = (
            "import x\n"
            "def f(store, c):\n"
            "    r = login_vitals.resolve_for_character(store, c.id)\n"
            "    return login_vitals.apply_to_character(c, r)\n"
        )
        called = _called_names_in(sample)
        self.assertIn("login_vitals.resolve_for_character", called)
        self.assertIn("login_vitals.apply_to_character", called)
        self.assertEqual([], _called_names_in("x = 1\n"))
        self.assertEqual(
            {"login_vitals"},
            _vitals_aliases_in(
                "from . import persistence_login_vitals as login_vitals\n"))
        self.assertEqual(
            {"pirateforce_foundation"},
            _vitals_aliases_in(
                "import pirateforce_foundation.persistence_login_vitals\n"))
        self.assertEqual(set(), _vitals_aliases_in("import sys\n"))


class TheHpPinSurvivesTheRequestedChangeTests(unittest.TestCase):
    """`_hp_defaults_of`, graded on synthetic composers.

    The real composer is another lane's file and holds ONE of these shapes at
    a time, so the branch that is not live today would otherwise be graded by
    nothing -- which is how a fallback branch rots into a hole before anyone
    reaches it.
    """

    def _composer(self, source):
        import ast

        tree = ast.parse(source)
        node = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef))
        return _hp_defaults_of(node, ast)

    def test_the_parameterised_shape_the_core_request_asks_for_is_read(self):
        self.assertEqual(
            [100, 100],
            self._composer(
                "def c(legacy, *, hp_current: int = 100, hp_max: int = 100):\n"
                "    return legacy.u32tag(0x14, hp_current) + legacy.u32tag(0x14, hp_max)\n"))

    def test_positional_defaults_are_read_too(self):
        self.assertEqual(
            [7, 9],
            self._composer(
                "def c(legacy, hp_current=7, hp_max=9):\n"
                "    return legacy.u32tag(0x14, hp_current) + legacy.u32tag(0x14, hp_max)\n"))

    def test_a_parameter_the_composer_never_emits_is_not_a_pin(self):
        """The hole this guard exists to refuse: a signature that carries the
        names while the wire still carries something else."""
        self.assertIsNone(
            self._composer(
                "def c(legacy, *, hp_current: int = 100, hp_max: int = 100):\n"
                "    return legacy.u32tag(0x14, 100) + legacy.u32tag(0x14, 100)\n"))

    def test_one_of_the_two_is_not_enough(self):
        self.assertIsNone(
            self._composer(
                "def c(legacy, *, hp_current: int = 100):\n"
                "    return legacy.u32tag(0x14, hp_current)\n"))

    def test_a_bool_default_is_refused(self):
        """`True` is an `int` and would pin the HP constant at 1."""
        self.assertIsNone(
            self._composer(
                "def c(legacy, *, hp_current=True, hp_max=True):\n"
                "    return legacy.u32tag(0x14, hp_current) + legacy.u32tag(0x14, hp_max)\n"))

    def test_todays_composer_still_reaches_the_literal_branch(self):
        """The control: on `main` as it stands the numbers come from the two
        inline literals, not from this file's fallback."""
        self.assertEqual(
            [FALLBACK_HP_CURRENT, FALLBACK_HP_MAX], _login_hp_literals())


if __name__ == "__main__":
    unittest.main()
