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

#: Every tree a seam could land in, matching the sibling caller scan in
#: `tests/test_persistence_vitals.py` rather than inventing a shorter list.
SEAM_SCAN_TREES = (
    ROOT / "src", ROOT / "tools", ROOT / "scenarios", ROOT / "current",
    ROOT / "tests", ROOT / "drafts", ROOT / "reports",
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
            if len(found) != 2:
                raise AssertionError(
                    f"{LOGIN_COMPOSER} no longer emits exactly two constant "
                    f"u32tag(0x14, N) numbers (found {found}); the HP pair "
                    "this file pins has moved or been parameterised, and the "
                    "nonclaim below has to be re-read rather than re-run")
            return found
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
            login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)
        self.assertNotEqual(
            resolved.reason, login_vitals.REVIVE_WRITE_FAILED,
            "the row on disk was healed and the login says the write never "
            "happened")
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
            first.reason, login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)

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
        self.assertEqual(
            resolved.reason,
            login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)
        self.assertIn(login_vitals.ROW_HP_NOT_POSITIVE, resolved.detail)
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))
        self.assertEqual(resolved.wire_kwargs(), {})

    def test_a_row_that_reads_back_broken_is_a_failure_not_a_revive(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            _resolution(level=ROW_LEVEL, hp_current=90, hp_max=10))
        resolved = self._resolve(store)
        self.assertEqual(
            resolved.reason,
            login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)
        self.assertIn(
            login_vitals.ROW_REFUSED_BY_VITALS_GATE, resolved.detail,
            "the failure line does not say what the row read back as, so an "
            "operator cannot tell a lost write from a broken row")

    def test_a_write_that_raises_is_not_a_failed_login(self):
        store = _ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked"))
        resolved = self._resolve(store)
        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertIn("database is locked", resolved.detail)
        self.assertIn(
            "OperationalError", resolved.detail,
            "the class was dropped, so two different faults read alike")
        self.assertEqual(
            (resolved.level, resolved.hp_current, resolved.hp_max),
            (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX))

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
        self.assertEqual(
            resolved.reason,
            login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)
        self.assertNotEqual(
            resolved.reason, login_vitals.REVIVE_WRITE_FAILED,
            "a write that returned is being reported as a write that never "
            "happened, which is a false statement about the database")
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
        raised = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            write_raises=sqlite3.OperationalError("database is locked")))
        returned = self._resolve(_ReviveStoreStub(
            _resolution(**self.DEAD),
            read_back_raises=sqlite3.OperationalError("database is locked")))
        self.assertEqual(raised.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(
            returned.reason,
            login_vitals.REVIVE_WROTE_BUT_ROW_NOT_READ_BACK)
        self.assertNotEqual(raised.reason, returned.reason)
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

    def test_the_module_is_not_wired_in_by_this_lane(self):
        """This lane's write zone stops at `persistence_*.py`; the seams are
        chief's.  If this ever fails it is GOOD NEWS -- the seam landed --
        and the right response is to move the seam's own tests into the round
        that landed it, not to loosen this.

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
        for tree in SEAM_SCAN_TREES:
            if not tree.exists():
                continue
            for path in tree.rglob("*.py"):
                relative = path.relative_to(ROOT).as_posix()
                if relative in NAMES_THE_MODULE_BY_CONSTRUCTION:
                    continue
                if path.resolve() == MODULE_SOURCE.resolve():
                    continue
                if "persistence_login_vitals" in path.read_text(
                        encoding="utf-8", errors="replace"):
                    importers.append(relative)
        self.assertEqual(
            sorted(importers), [],
            "a seam now names this module, so the round file's 'nothing "
            "calls it' nonclaim is stale and the seam needs its own tests")

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


if __name__ == "__main__":
    unittest.main()
