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

🔴 WHAT THIS FILE DOES **NOT** SAY, and the round note must not say either
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
     this file was written.  Until he grants it, chief's recursive guard
     WILL be red on `lane_a_choose_npc_roster_scenes.py`, and that red is
     LANE-A's, owned and expected -- not a surprise and not chief's to
     absorb.  `test_a_pending_request_is_not_quietly_a_grant` goes red the
     moment he does grant it, which is the round this lane moves the entry
     and stops calling it pending.

🔴 THIS FILE READS DIFFERENTLY ON 3.11 AND ON THE GATE'S 3.14 (PEP 701),
for exactly the reason chief's own 19-line warning at
`tests/test_npc_interaction_wire.py:545-563` gives for his two entries: on
<=3.11 an f-string is one `tokenize.STRING` token and `module_code_text()`
drops it whole, so a guard word inside an f-string is invisible; on >=3.12
its literal text is `FSTRING_MIDDLE` and reads as code.  The gate pins
3.14.  MEASURED this round: a planted `f"shop_state_{reason}_refused"` in a
`lane_a_*` hook is green on 3.11 and red on 3.13.  So a LANE-A author who
validates only on this cloud clone (3.11 is the only interpreter here with
pytest) can ship gate-red.  The direction is safe -- green local, red gate,
costing a round rather than laundering a defect -- but do not read a green
run here as proof.  If you have 3.12+ available, run this file under it.

THE RULE THIS ENFORCES.  It borrows chief's helpers rather than
re-implementing them, deliberately: a private copy of the matcher would
drift from the gate's copy and this test would go on passing while the gate
went red.  It says nothing about behaviour: this lane implements no quest
and no shop, and no word list could prove that either way.
"""
from __future__ import annotations

import ast
import pathlib
import sys
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

# Requested from chief, NOT granted (see limit (2) above).  An imported
# module name this lane reads ONE integer out of
# (`COLUMBUS_PLACEMENT_INDEX`, in `_scenes_where_columbus_collides`), on
# the same grounds chief's own table already allows the identical name in
# `world_m2_columbus_trigger_readiness.py` and `runtime.py`.
PENDING_CHIEF_GRANT = {
    "lane_a_choose_npc_roster_scenes.py": {"columbus_quest_dispatch"},
}


def _imported_names(source: str) -> set[str]:
    """Every name an `import` statement BINDS in this module.

    Read with `ast`, not with the guard's own token reader, because the
    mirror test below has to answer a different question than the guard
    does: not "does this text appear as a code name" (which an f-string can
    satisfy on 3.12+ -- MEASURED this round, pf-adversary finding A3) but
    "is this name still an import, which is the whole reason it was
    allowed".
    """
    bound = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
    return bound


class LaneAHookModulesAreGuardClean(unittest.TestCase):
    def _modules(self):
        modules = sorted(FOUNDATION.glob(LANE_A_GLOB))
        self.assertTrue(modules, "no LANE-A modules found to scan")
        return modules

    def _allowed_for(self, name: str) -> set[str]:
        """Chief's grant for this file, plus this lane's pending request."""
        granted = set(chief_guard.QuestAndShopStateGuardTests.ALLOWED_SYMBOLS.get(name, ()))
        return granted | set(PENDING_CHIEF_GRANT.get(name, ()))

    def test_no_lane_a_module_binds_an_unread_quest_or_shop_code_name(self):
        for path in self._modules():
            with self.subTest(module=path.name):
                found = set()
                for symbols in guard_hits_in_module(
                    path.read_text(encoding="utf-8")
                ).values():
                    found |= symbols
                self.assertEqual(
                    sorted(found - self._allowed_for(path.name)),
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
            matches = [p for p in self._modules() if p.name == name]
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
            granted = set(chief_guard.QuestAndShopStateGuardTests.ALLOWED_SYMBOLS.get(name, ()))
            with self.subTest(module=name):
                self.assertEqual(
                    sorted(expected & granted),
                    [],
                    "chief has granted this symbol -- move it out of "
                    "PENDING_CHIEF_GRANT; it is covered by his table now",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
