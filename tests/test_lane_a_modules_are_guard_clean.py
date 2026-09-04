"""LANE-A's own half of chief's quest/shop code-name guard.

WHY THIS FILE EXISTS
--------------------
`tests/test_npc_interaction_wire.py`'s `QuestAndShopStateGuardTests` scans
`glob("*.py")` at the TOP LEVEL of `src/pirateforce_foundation/` only -- it
says so itself, and pins the gap with
`test_the_unscanned_subpackages_are_named_and_counted`.  Chief measured the
subpackages out-of-gate in round `t7bsfx`/R342 and wrote to each lane with
its own hits (`pf_bridge/notes_to_chief/20260904_2016_FROM-CHIEF-TO-LANE-A-
quest-shop-guard-recursive-hitlist-two-modules.md`, ADDRESSEE: LANE-A):
two modules, three symbols, deadline 2026-09-05 03:21, at which point chief
flips that glob to recursive and anything left is RED IN THIS LANE'S ZONE,
not chief's.

Two of the three are renamed in the same round as this file
(`vendor_trigger_idx` / `mission_actor_idx` in `lane_a_choose_npc_scene1`).
The third is the imported module name `columbus_quest_dispatch` and cannot
be renamed from here at all -- any import binds that token as code.

WHAT THIS FILE DOES **NOT** SAY, and the round note must not say either
(pf-adversary, round `xf6eoi`, findings A4 and A5):

  1. IT IS NOT "LANE-A's zone is clean".  It scans files whose NAME starts
     with `lane_a_`, recursively under `src/pirateforce_foundation/`.  That
     is a filename rule, not an ownership rule: a LANE-A module named
     something else, or a guard word planted in `lane_hooks/__init__.py`,
     is outside it and was MEASURED to slip through.  Chief's recursive
     guard is the one that decides; this file only keeps this lane's own
     named modules from being the reason it goes red.
  2. `PENDING_CHIEF_GRANT` IS NOT AN EXEMPTION.  Chief's letter says
     per-symbol exemptions are requested and HE decides
     ("ผมตัดสิน"); the request for `columbus_quest_dispatch` is
     `pf_bridge/notes_to_chief/20260904_2229_LANE-A-TO-CHIEF-one-line-
     answer-columbus-quest-dispatch-exemption.md` and was unanswered when
     this file was written.  ~~Until he grants it, chief's recursive guard
     WILL be red on `lane_a_choose_npc_roster_scenes.py`, and that red is
     LANE-A's, owned and expected -- not a surprise and not chief's to
     absorb.~~  ANSWERED: chief granted it in round `zwxuuk`/R345 (server
     `#777`, on `main` as `c055dbc`), so the entry left `PENDING_CHIEF_
     GRANT` in round `qqqtqp` and the allowance is now his table's, checked
     by `test_the_columbus_import_is_covered_by_chiefs_own_table`.
     The machinery below stays for the NEXT request, unused until there is
     one.

WARNING: THE GRANT IS KEYED IN A SHAPE HIS OWN LOOKUP CANNOT FIND (measured this
round, and the reason `test_chiefs_grant_is_reachable_by_the_key_shape_
this_file_resolves` exists).  Chief wrote the new entries with their
subpackage prefix -- `"lane_hooks/lane_a_choose_npc_roster_scenes.py"`,
`"gm/item_catalog.py"` -- but `_offenders_in` reads
`ALLOWED_SYMBOLS.get(path.name, set())`, a BASENAME.  While the gate still
globs the top level only, no prefixed key is ever consulted and nothing
shows.  MEASURED on `c055dbc` by running his own `guard_hits_in_module`
over `**/*.py` with each key shape:

    rglob + key=path.name  -> offenders: lane_a_choose_npc_roster_scenes.py
                              {'quest': ['columbus_quest_dispatch']}
                              item_catalog.py {'quest': [...]}   (LANE-GM)
                              lane_ui_trade_wire_log.py {...}    (LANE-UI)
    rglob + key=relative   -> offenders: lane_ui_trade_wire_log.py only

So the flip alone turns two GRANTED files red.  It is a one-line fix in
chief's file (`path.relative_to(directory).as_posix()`, which leaves every
existing top-level key valid), it is HIS file, and it is asked for in
`pf_bridge/notes_to_chief/20260905_0129_LANE-A-TO-CHIEF-exemption-key-
with-subpackage-prefix-is-never-consulted.md`.  THIS FILE DOES
NOT GO RED FOR IT: this lane resolves his table by both key shapes, so what
is measured here is whether the ALLOWANCE EXISTS, never whether his lookup
finds it.  A red there would be this lane reporting chief's bug as its own.
And because reading only his TABLE is blind to his LOOKUP,
`test_no_lane_a_module_offends_the_lookup_chiefs_gate_actually_uses` CALLS
`_offenders_in` -- his method, his tree, whatever he globs and however he
keys -- and holds the difference in `BLOCKED_ON_CHIEFS_LOOKUP`: a named,
dated list of symbols he granted that his own gate cannot see.  It calls
rather than re-implements because pf-adversary (round `qqqtqp`, finding A)
MEASURED a hand-rolled copy of the lookup staying green in the exact state
it was written to catch: rekey the entry to a basename AND fix the lookup
to a relative path -- two individually sensible chief-side edits -- and a
copy tracks the key while the gate tracks the resolution.

~~THIS FILE READS DIFFERENTLY ON 3.11 AND ON THE GATE'S 3.14 (PEP 701) ...
a planted `f"shop_state_{reason}_refused"` is green on 3.11 and red on
3.13, so do not read a green run here as proof.~~  RETIRED, round
`qqqtqp`, and it was the sentence a real red would have been excused with.
Chief's `module_code_text` now routes every `STRING` token through
`fstring_code_text` (`COO-DECISION 20260904_2153`), whose own docstring
says it exists "so the guard reaches the SAME verdict on every interpreter
it runs on".  MEASURED this round on 3.11, 3.12 and 3.13: that exact plant
gives `{'shop': {'shop_state_'}}` on all three, and this file goes red on
3.11.  (The earlier claim also cited a "19-line warning at
`test_npc_interaction_wire.py:545-563`", which is a different test
entirely -- a line-number pin that outlived what it counted.  The real
material is `fstring_code_text`'s own docstring; grep the name.)  Two
named gaps do survive in it -- PEP 701 nested same-quote fields, and 3.14
t-strings -- and neither shape exists in this package today.

THE RULE THIS ENFORCES.  It borrows chief's helpers rather than
re-implementing them, deliberately: a private copy of the matcher would
drift from the gate's copy and this test would go on passing while the gate
went red.  It says nothing about behaviour: this lane implements no quest
and no shop, and no word list could prove that either way.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

# Imported as a MODULE, never `from ... import QuestAndShopStateGuardTests`:
# binding chief's `TestCase` subclass in this namespace makes pytest collect
# and run his whole guard class a second time under this file's name, which
# both doubles the work and reports his reds as this lane's (MEASURED this
# round).  The matcher is a plain function and is safe to name directly.
import test_npc_interaction_wire as chief_guard  # noqa: E402

guard_hits_in_module = chief_guard.guard_hits_in_module

FOUNDATION = ROOT / "src" / "pirateforce_foundation"

# Computed, never a hardcoded list, and recursive: a hook added next round,
# or moved into a subdirectory, is scanned without anyone remembering to
# edit this.  See limit (1) in this module's docstring for what the
# filename rule does not reach.
LANE_A_GLOB = "**/lane_a_*.py"

# Requested from chief, NOT granted (see limit (2) above).  Empty today,
# and deliberately kept rather than deleted: the next symbol this lane has
# to ask for lands here and the two tests below start checking it again the
# same round.
#
# ~~PENDING_CHIEF_GRANT = {
#     "lane_a_choose_npc_roster_scenes.py": {"columbus_quest_dispatch"},
# }~~  GRANTED, round `zwxuuk`/R345, `c055dbc` on main -- the imported
# module name this lane reads ONE integer out of
# (`COLUMBUS_PLACEMENT_INDEX`, in `_scenes_where_columbus_collides`), on
# the same grounds chief's own table already allows the identical name in
# `world_m2_columbus_trigger_readiness.py` and `runtime.py`.  It is checked
# from here on by `test_the_columbus_import_is_covered_by_chiefs_own_table`,
# which is a stricter check than the pending one it replaces: it reads the
# grant out of HIS table instead of asserting the absence of one.
PENDING_CHIEF_GRANT: dict[str, set[str]] = {}

# The one name this lane holds a granted exemption for, and the file that
# holds it.  Written as the FOUNDATION-relative path because that is the
# shape chief keyed the grant in.
GRANTED_IMPORT_MODULE = "lane_hooks/lane_a_choose_npc_roster_scenes.py"
GRANTED_IMPORT_SYMBOL = "columbus_quest_dispatch"
GRANTED_IMPORT_ATTR = "COLUMBUS_PLACEMENT_INDEX"

# GRANTED BY CHIEF, BUT NOT REACHABLE BY THE LOOKUP HIS GATE USES -- the
# named, dated exception that keeps
# `test_no_lane_a_module_offends_the_lookup_chiefs_gate_actually_uses`
# honest without making it red for his defect.  Everything in here must
# ALSO be a live grant in his table (checked below), so this can never
# quietly become a second, self-service allowance list: an entry here says
# "he read this and said yes, and his own lookup cannot find his yes".
# It empties itself the round he keys the entry, or the lookup, so the two
# agree -- either fix drops the file out of the offender set.
BLOCKED_ON_CHIEFS_LOOKUP: dict[str, set[str]] = {
    "lane_a_choose_npc_roster_scenes.py": {GRANTED_IMPORT_SYMBOL},
}


def _imported_names(source: str) -> set[str]:
    """Every name an `import` statement BINDS in this module.

    Read with `ast`, not with the guard's own token reader, because the
    mirror test below has to answer a different question than the guard
    does: not "does this text appear as a code name" (which an f-string can
    satisfy -- MEASURED, pf-adversary finding A3, round `xf6eoi`) but "is
    this name still an import, which is the whole reason it was allowed".

    KNOWN WEAK, which is why it is no longer the whole check for the
    granted name (pf-adversary finding C, round `qqqtqp`, MEASURED): it is
    satisfied by `import sys as columbus_quest_dispatch` and by an import
    under `if False:` that never runs, and it reports the wrong name for
    `import pirateforce_foundation.columbus_quest_dispatch`.  It stays as
    the check for a PENDING entry, where the question really is only "is
    this word still bound by an import statement at all"; the granted entry
    is checked by `_reads_the_one_integer_off` below.
    """
    bound = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
    return bound


def _reads_the_one_integer_off(source: str, module: str, attr: str) -> bool:
    """The load-bearing half of the exemption's argument, checked.

    The allowance chief granted is not "this file says a word".  It is:
    *this file imports that module and reads ONE integer off it*.  So this
    reads both halves and joins them by the NAME THE IMPORT ACTUALLY BINDS:

      1. a MODULE-LEVEL import (never one nested under `if False:`, a
         function, or a `try:`) of `..<module>` / `pirateforce_foundation.
         <module>`, in any of the spellings that really resolve to it,
         aliased or not; and
      2. an attribute read of `<bound name>.<attr>` somewhere in the file.

    pf-adversary (round `qqqtqp`) MEASURED the shapes this closes and the
    weaker check let through: `import sys as columbus_quest_dispatch` with
    the integer read replaced by a literal `1` -- the module not imported
    at all, the premise of the exemption false, and the old mirror green.
    """
    tree = ast.parse(source)
    # The EXPRESSIONS that denote the module after the import runs, as
    # source text, so that `import pirateforce_foundation.columbus_quest_
    # dispatch` (which binds the PACKAGE, not the module) is read the way
    # Python reads it rather than reported as a missing import.
    denotes: set[str] = set()
    for node in tree.body:  # MODULE LEVEL ONLY -- `if False:` cannot bind.
        if isinstance(node, ast.ImportFrom):
            # `from .. import <module>` (level>0) or
            # `from pirateforce_foundation import <module>`.
            package = node.module or ""
            if node.level > 0 or package == "pirateforce_foundation":
                for alias in node.names:
                    if alias.name == module:
                        denotes.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] == module:
                    denotes.add(alias.asname or alias.name)
    if not denotes:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == attr:
            if ast.unparse(node.value) in denotes:
                return True
    return False


def _the_flip_has_landed() -> bool:
    """Has chief made his gate scan the subpackages yet?

    The ONE place this file reads his source text rather than his
    behaviour, and it is deliberately not used to reach a verdict about
    anything -- only to decide whether a verdict of his EXISTS to compare
    against.  Before the flip, `_offenders_in` never opens a
    `lane_hooks/lane_a_*.py`, so its silence about this lane says nothing
    at all, and an anti-rot check keyed on that silence would be red for
    every round from now until 03:21.
    """
    source = inspect.getsource(
        chief_guard.QuestAndShopStateGuardTests._offenders_in
    )
    return "rglob" in source


class LaneAHookModulesAreGuardClean(unittest.TestCase):
    def _modules(self):
        modules = sorted(FOUNDATION.glob(LANE_A_GLOB))
        self.assertTrue(modules, "no LANE-A modules found to scan")
        return modules

    @staticmethod
    def _keys_for(path: pathlib.Path) -> tuple[str, ...]:
        """The shapes a key for this module can have in chief's table.

        His table carries top-level modules under their bare filename and
        the subpackage ones under a `dir/file.py` path, while his
        `_offenders_in` looks entries up by `path.name` alone -- see the
        warning block in this module's docstring.  This lane reads BOTH so
        that a granted allowance is seen here as granted no matter which
        shape it was written in, and so this file never goes red for the
        lookup bug in his.

        THE BASENAME IS ONLY OFFERED WHEN IT IS UNAMBIGUOUS.  pf-adversary
        (round `qqqtqp`, finding B) MEASURED the hole in the flat union:
        with a granted `lane_a_side_roster.py` at the top level and an
        UNGRANTED `lane_hooks/scene17/lane_a_side_roster.py` carrying
        `def quest_state_for`, the basename key handed the first file's
        allowance to the second and this suite stayed green.  A basename
        shared by two files under `FOUNDATION` names neither of them, so it
        is not consulted for either.
        """
        keys = [path.relative_to(FOUNDATION).as_posix()]
        same_name = [
            p for p in FOUNDATION.rglob(path.name) if p.is_file()
        ]
        if len(same_name) == 1:
            keys.append(path.name)
        return tuple(dict.fromkeys(keys))

    def _allowed_for(self, path: pathlib.Path) -> set[str]:
        """Chief's grant for this file, plus this lane's pending request."""
        allowed = self._granted_for(path)
        for key in self._keys_for(path):
            allowed |= set(PENDING_CHIEF_GRANT.get(key, ()))
        return allowed

    def _granted_for(self, path: pathlib.Path) -> set[str]:
        """CHIEF'S TABLE ONLY -- never this lane's own pending list.

        Kept apart from `_allowed_for` because pf-adversary (round
        `qqqtqp`, finding D) MEASURED the test named "covered by chief's
        own table" passing on an entry this lane had written into
        `PENDING_CHIEF_GRANT` itself, with chief's entry deleted.  A test
        that reads a grant must read it where the grant lives.
        """
        table = chief_guard.QuestAndShopStateGuardTests.ALLOWED_SYMBOLS
        granted: set[str] = set()
        for key in self._keys_for(path):
            granted |= set(table.get(key, ()))
        return granted

    def _this_lanes_rows_in_chiefs_own_offender_set(self):
        """HIS gate's verdict on this lane's modules.  Called, not modelled.

        Every other test here reads chief's exemption TABLE.  His gate
        reaches its verdict through a LOOKUP, and the two disagree today --
        the subject of this round.  A suite that only ever reads the table
        is blind to that, and so is a suite that RE-IMPLEMENTS the lookup:
        pf-adversary (round `qqqtqp`, finding A) MEASURED a hand-rolled
        `get(path.name)` copy of it staying green in the state it was
        written to catch, because a copy tracks the key shape rather than
        chief's actual resolution.

        So this calls `_offenders_in` itself, on the real tree, with the
        real table -- through a stand-in object rather than his `TestCase`,
        because instantiating his class here is what makes pytest report
        his reds under this file's name.  Whatever he globs and however he
        keys, this asks him.  His answer is filtered to this lane's named
        modules: a red here for LANE-GM's or LANE-UI's files would be this
        lane reporting somebody else's work as its own.

        VACUOUS UNTIL HE FLIPS THE GLOB, and that is correct rather than a
        gap: while his gate scans the top level only, it renders NO verdict
        on `lane_hooks/lane_a_*.py`, and a verdict invented here would be
        the modelling mistake again.  The moment the flip lands (due
        2026-09-05 03:21) this goes live with no edit from this lane.
        """
        stand_in = types.SimpleNamespace(
            ALLOWED_SYMBOLS=(
                chief_guard.QuestAndShopStateGuardTests.ALLOWED_SYMBOLS
            )
        )
        offenders = chief_guard.QuestAndShopStateGuardTests._offenders_in(
            stand_in, FOUNDATION
        )
        lane_a = {}
        for key, words in offenders.items():
            # He keys by `path.name` today and may key by a relative path
            # after fixing the defect this round reports; read the last
            # segment either way.
            name = key.replace("\\", "/").rsplit("/", 1)[-1]
            if name.startswith("lane_a_"):
                symbols: set[str] = set()
                for found in words.values():
                    symbols |= set(found)
                lane_a[name] = symbols
        return lane_a

    def test_no_lane_a_module_binds_an_unread_quest_or_shop_code_name(self):
        for path in self._modules():
            with self.subTest(module=path.name):
                found = set()
                for symbols in guard_hits_in_module(
                    path.read_text(encoding="utf-8")
                ).values():
                    found |= symbols
                self.assertEqual(
                    sorted(found - self._allowed_for(path)),
                    [],
                    "a quest/shop code name nobody has read -- rename it "
                    "(chief's rule: an exemption is never granted to make a "
                    "red run green)",
                )

    def test_every_pending_name_is_still_an_import_in_that_module(self):
        """The mirror, so this file cannot rot into a wish list.

        pf-adversary (round `xf6eoi`, A3) broke the first version of this:
        deleting the import and leaving the words inside an f-string kept
        the old check green on 3.13 (= the gate's 3.14), because the guard's
        reader sees f-string text as code there.  The justification for the
        allowance is that the name is an IMPORT read for one integer, so
        that is what gets checked -- an f-string cannot satisfy it.
        """
        for name, expected in PENDING_CHIEF_GRANT.items():
            matches = [
                p for p in self._modules() if name in self._keys_for(p)
            ]
            with self.subTest(module=name):
                self.assertTrue(matches, "pending request names a dead module")
                bound = _imported_names(matches[0].read_text(encoding="utf-8"))
                self.assertEqual(
                    sorted(expected - bound),
                    [],
                    "the pending allowance is no longer an import here -- "
                    "withdraw the request instead of leaving it standing",
                )

    def test_a_pending_request_is_not_quietly_a_grant(self):
        """Red the round chief answers, which is the point.

        A per-symbol exemption is chief's to grant.  While this entry sits
        in `PENDING_CHIEF_GRANT`, chief's recursive guard is red on that
        file and LANE-A owns the red.  The day he adds the symbol to
        `ALLOWED_SYMBOLS`, this goes red and the entry moves out of pending
        -- so the word "pending" can never outlive the fact.
        """
        for name, expected in PENDING_CHIEF_GRANT.items():
            matches = [
                p for p in self._modules() if name in self._keys_for(p)
            ]
            granted: set[str] = set()
            for path in matches:
                granted |= self._granted_for(path)
            with self.subTest(module=name):
                # pf-adversary (round `qqqtqp`, finding G) MEASURED this
                # test passing vacuously on a mistyped key -- a backslash
                # separator, or a `src/...` prefix -- because `matches` was
                # empty and an empty intersection is an empty intersection.
                # Its sibling above already had this guard; the round that
                # made both depend on `matches` did not carry it across.
                self.assertTrue(
                    matches, "pending request names a dead module"
                )
                self.assertEqual(
                    sorted(expected & granted),
                    [],
                    "chief has granted this symbol -- move it out of "
                    "PENDING_CHIEF_GRANT; it is covered by his table now",
                )

    def _granted_module(self) -> pathlib.Path:
        path = FOUNDATION / GRANTED_IMPORT_MODULE
        self.assertTrue(
            path.exists(),
            "the module holding this lane's one granted exemption is gone -- "
            "withdraw the grant from chief's table in the same round",
        )
        return path

    def test_the_columbus_import_is_covered_by_chiefs_own_table(self):
        """The grant is read out of HIS table, not asserted from memory.

        This replaces `test_a_pending_request_is_not_quietly_a_grant` for
        `columbus_quest_dispatch` and is strictly stronger: the pending
        version could only prove chief had NOT answered.  This one goes red
        if the allowance is ever dropped from his table while this lane is
        still binding the name -- which is the shape that would let a
        LANE-A file sit red in his gate with nobody here knowing.
        """
        path = self._granted_module()
        self.assertIn(
            GRANTED_IMPORT_SYMBOL,
            self._granted_for(path),
            "this lane binds a quest/shop code name with no allowance in "
            "chief's table -- rename it or ask him, do not wait for the gate",
        )

    def test_no_lane_a_module_offends_the_lookup_chiefs_gate_actually_uses(
        self,
    ):
        """The gate's verdict on this lane, not the table's.

        Everything else here reads chief's exemption TABLE.  This asks his
        gate -- see `_this_lanes_rows_in_chiefs_own_offender_set` -- so that
        the day the two disagree, the disagreement is a line in a test
        report and not a red gate nobody predicted.

        Written as a SUBSET check against a named, dated list rather than
        as `== {}`: at the flip his lookup will not be able to reach the
        grant he wrote, and a hard-empty assertion here would be this lane
        going red for his defect.  A subset check goes red for the thing
        that IS this lane's -- a NEW quest/shop name in a `lane_a_*` module
        -- and stays green through either of his two possible fixes, both
        of which empty the offender set.
        """
        offenders = self._this_lanes_rows_in_chiefs_own_offender_set()
        for name, symbols in sorted(offenders.items()):
            with self.subTest(module=name):
                self.assertEqual(
                    sorted(symbols - BLOCKED_ON_CHIEFS_LOOKUP.get(name, set())),
                    [],
                    "this lane offends chief's gate with a name he has not "
                    "read -- rename it; do not add it to "
                    "BLOCKED_ON_CHIEFS_LOOKUP, which is only for names he "
                    "granted and his lookup cannot find",
                )

    def test_every_blocked_on_lookup_entry_is_a_grant_he_actually_wrote(self):
        """So the exception list can never become a second allowance list.

        `BLOCKED_ON_CHIEFS_LOOKUP` suppresses part of the check above.  The
        only thing that entitles an entry to sit there is that chief HAS
        granted the symbol -- somewhere in his table, under some key that
        names this file -- and only his lookup cannot reach it.  Without
        this, the round after next could park an unread name in there and
        call it "blocked on chief".
        """
        offenders = self._this_lanes_rows_in_chiefs_own_offender_set()
        for name, symbols in sorted(BLOCKED_ON_CHIEFS_LOOKUP.items()):
            matches = [p for p in self._modules() if p.name == name]
            with self.subTest(module=name):
                self.assertTrue(
                    matches, "blocked-on-lookup entry names a dead module"
                )
                granted: set[str] = set()
                for path in matches:
                    granted |= self._granted_for(path)
                self.assertEqual(
                    sorted(symbols - granted),
                    [],
                    "this is not a lookup problem -- chief's table grants "
                    "this lane nothing by that name; withdraw the entry or "
                    "rename the symbol",
                )
                if not _the_flip_has_landed():
                    continue
                # Anti-rot, live only once his gate actually renders a
                # verdict on subpackages.  Before the flip his gate says
                # nothing about these files, so "not in the offender set"
                # means "not looked at", not "fixed".  After it, an entry
                # that is no longer an offender is a suppression with
                # nothing left to suppress -- chief's own
                # `test_every_symbol_exemption_is_still_earned` refuses the
                # same shape in his table, for the same reason.
                self.assertIn(
                    name,
                    offenders,
                    "chief's gate no longer reports this file -- his lookup "
                    "and his key agree now; delete this entry, the grant in "
                    "his table is doing the work",
                )

    def test_the_granted_name_is_still_an_import_in_that_module(self):
        """The mirror of the grant, same rule the pending list lived under.

        The allowance was argued as "an imported module name read for one
        integer".  The day it stops being an import, the argument is gone
        and the entry has to leave chief's table -- an exemption nobody can
        still earn pre-approves whatever re-uses the name tomorrow.  Read
        with `ast` for the reason the pending mirror gave: an f-string
        satisfies the guard's own reader on every interpreter now, and it
        must not satisfy this.

        BOTH HALVES, joined by the bound name.  pf-adversary (round
        `qqqtqp`, finding C) MEASURED the half-check this replaces going
        green on `import sys as columbus_quest_dispatch` with the integer
        read swapped for a literal `1`: the module not imported at all, the
        premise of the exemption false, and nothing red.  Chief's own
        `test_the_identity_tables_shop_hits_are_all_npc_title_data` checks
        the premise of HIS newest exemption line by line; the model was in
        hand and the first version of this did not follow it.
        """
        self.assertTrue(
            _reads_the_one_integer_off(
                self._granted_module().read_text(encoding="utf-8"),
                GRANTED_IMPORT_SYMBOL,
                GRANTED_IMPORT_ATTR,
            ),
            f"the granted allowance is no longer "
            f"'a module-level import of {GRANTED_IMPORT_SYMBOL} read for "
            f"{GRANTED_IMPORT_ATTR}' -- which is the whole argument chief "
            f"granted it on; ask him to drop it instead of leaving it "
            f"standing",
        )

    def test_chiefs_grant_is_reachable_by_the_key_shape_this_file_resolves(
        self,
    ):
        """Which key shape the grant is written in, recorded not assumed.

        Not a check on chief's lookup -- his `_offenders_in` reading
        `path.name` while his own new keys carry a `lane_hooks/` prefix is
        HIS defect and is asked about in
        `pf_bridge/notes_to_chief/20260905_0129_LANE-A-TO-CHIEF-exemption-
        key-with-subpackage-prefix-is-never-consulted.md`.
        A test here that went red for it would be this lane reporting his
        bug as its own red, which is exactly the confusion round `xf6eoi`
        was told to stop causing.

        What this DOES pin: the round he fixes the lookup, the fix moves
        the grant under one of the two shapes above, and this names which
        shape is live today so that a silent rekey cannot leave this lane
        allowed here and offending there.
        """
        table = chief_guard.QuestAndShopStateGuardTests.ALLOWED_SYMBOLS
        path = self._granted_module()
        by_relative, by_basename = self._keys_for(path)
        live = {
            "relative": GRANTED_IMPORT_SYMBOL in table.get(by_relative, ()),
            "basename": GRANTED_IMPORT_SYMBOL in table.get(by_basename, ()),
        }
        # MEASURED on `c055dbc`: `relative` only.  Deliberately NOT asserted
        # as exactly that: chief may close his defect either by fixing the
        # lookup (key stays relative) or by rekeying the entry to the
        # basename his lookup already reads, and BOTH leave this lane
        # correctly allowed.  Going red on his valid fix would be this file
        # spending a round of somebody else's to report good news.  What is
        # asserted is the only shape that actually hurts: an entry reachable
        # under NEITHER, which is a grant that exists in the file and for
        # nobody.
        self.assertTrue(
            any(live.values()),
            "chief's table grants this lane nothing under either key shape "
            f"({by_relative!r} / {by_basename!r}) -- the allowance was "
            "rekeyed or dropped and this lane's file is offending again",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
