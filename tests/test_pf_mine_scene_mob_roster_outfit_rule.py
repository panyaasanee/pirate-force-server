"""LANE-B: s_OUTFIT no longer decides who is an enemy, and the bg0001
control was re-pinned rather than switched off.

ROUND nxcwdn.  Owner ruling of 2026-09-07 (PANYA 1313, relayed as
COO-DECISION 20260907_1346): an enemy is ``n_RANK`` plus ``n_AI_COMBAT`` and
NOTHING else.  The half this removes had been refusing a placement whose
``s_OUTFIT`` cell holds more than one value, and ``ka1-A`` measured before
the ruling that 565 of MOBS' 3,210 rows hold a list and 546 of those have
``rank > 0`` -- so that half was refusing nearly every field monster in the
game.  On bg0002 alone it refused 40 placements, every one of them for that
reason and no other.

WHY THIS FILE EXISTS RATHER THAN A LINE DELETED IN THE GENERATOR.  Ten scene
modules already committed here were mined under the old reading, and each has
a byte-for-byte regenerate test.  Deleting the half outright would have made
all ten stale in a round that cannot re-mine and re-review ten rosters, so
the old reading became a NAMED rule (``--outfit-rule unambiguous``, still the
default) and the owner's became the other one (``any``).  These tests pin
both halves of that claim:

* the rule the owner removed is genuinely gone from ``any`` -- and the count
  it changes is measured on the shipped tables, not asserted from the side;
* the default did not move, which is what keeps those ten modules honest;
* the bg0001 control against ``v141`` was RE-PINNED for the new rule, not
  skipped, xfailed or deleted.  COO-DECISION 20260907_1346 asks for that in
  the same commit, and ``0945``'s standing rule makes a silenced control an
  unpaid finding.

THE RE-PIN IS STRICTLY STRONGER THAN THE COUNT CHECK IT EXTENDS.  Under the
owner's rule bg0001 derives 146 rows where ``v141`` froze 115, so plain count
equality would now be a false alarm rather than a control.  The claim that
replaces it is a superset claim: all 115 frozen rows are still derived and
still carry the same index, template, x, y, z and outfit, and the derived
table is exactly 146 rows -- so the 31 rows the change gains are counted, and
what did NOT move is pinned as well.

NONCLAIMS.  Nothing here says a scene should be re-mined under the new rule,
and nothing here re-mines one: ``field_mob_tables_bg0002.py`` is untouched by
this round and this file asserts that it still reads as the older rule.  The
measured reason is in this round's own file: scene 2 under the owner's rule
carries templates 27..35, ``mob_death``'s ruling set for that scene is
``{31, 34, 35, 103}``, and ``NOW.md`` holds widening it in "rows waiting for
Panya to tick".  Nothing here says which avatar the client draws for a row
whose ``s_OUTFIT`` is a list, either; ``RE-296`` measured that the client
keeps every token and left open who picks one.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import field_mob_tables_bg0002  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"
LEGACY = ROOT / "current" / "pf_login_game_server_v141.py"

# MEASURED this round on the committed tables, both by running the generator
# and by counting the placements it gains.  Written here as numbers rather
# than as "more than before" so a drift in either direction fails by value.
BG0001_FROZEN_ROWS = 115
BG0001_ANY_OUTFIT_ROWS = 146
BG0002_HOSTILE_UNDER_OWNER_RULE = 52
# The committed module is still the SETNUM mining, whose list is 17 rows; the
# owner's do-not-place ruling cuts five of them at load, which is where the
# 12 the console line reports comes from.  Both numbers are pinned, because
# confusing them is exactly how a reader concludes the flip already happened.
BG0002_SHIPPED_ROWS_IN_THE_COMMITTED_MODULE = 17
BG0002_HOSTILE_UNDER_OLD_RULE = 12
BG0002_TEMPLATES_UNDER_OWNER_RULE = {27, 28, 29, 30, 31, 32, 33, 34, 35}


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster_outfit_rule", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OutfitRuleShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_the_two_rules_are_named_and_the_default_did_not_move(self):
        tool = _load_tool()
        self.assertEqual(
            tool.OUTFIT_RULES,
            (tool.OUTFIT_RULE_UNAMBIGUOUS, tool.OUTFIT_RULE_ANY),
        )
        # The default is the OLD reading on purpose: ten committed scene
        # modules were mined under it and compare themselves to the
        # generator byte for byte.  If this flips, those ten go stale
        # silently, which is the failure this assertion exists to catch.
        for function in (
            tool.unambiguous_placements,
            tool.hostile_roster,
            tool.town_target_roster,
            tool.predicate_census,
            tool.unresolved_reason,
            tool.unresolved_placements,
            tool.withdrawn_under_rule,
        ):
            self.assertIn(
                "outfit_rule", function.__code__.co_varnames,
                "%s does not take the outfit rule, so a caller cannot ask "
                "for the owner's reading through it" % function.__name__,
            )

    def test_an_unknown_outfit_rule_is_refused_rather_than_ignored(self):
        tool = _load_tool()
        with self.assertRaises(tool.MineError):
            tool.unambiguous_placements(
                object(), tool.IDENTITY_RULE_SETNUM, "whatever",
            )
        with self.assertRaises(tool.MineError):
            tool.render_module(
                "Bg0000", [], {}, {}, outfit_rule="whatever",
            )

    def test_bg0002_still_ships_the_older_rule_and_says_so_by_absence(self):
        """This round changed the generator, NOT this scene's table.

        The flip is blocked on a decision, not on code: under the owner's
        rule scene 2 carries templates 27..35, ``mob_death``'s ruling set
        for it is ``{31, 34, 35, 103}``, and widening that set is a row in
        ``NOW.md`` waiting for the owner to tick.  A module mined under the
        older rule carries NO ``OUTFIT_RULE`` line, so the absence below is
        the assertion, and it is what a reader of the table sees too.
        """
        self.assertFalse(
            hasattr(field_mob_tables_bg0002, "OUTFIT_RULE"),
            "field_mob_tables_bg0002 was re-mined under the owner's rule "
            "without the death-scope decision NOW.md is holding",
        )
        self.assertEqual(
            len(field_mob_tables_bg0002.HOSTILE_PLACEMENTS),
            BG0002_SHIPPED_ROWS_IN_THE_COMMITTED_MODULE,
        )
        self.assertEqual(field_mob_tables_bg0002.IDENTITY_RULE, "setnum")


@BRIDGE_GAMEDATA.skip_unless_present()
class OutfitRuleMeasuredTests(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_the_owner_rule_gains_bg0002_the_forty_rows_it_refused(self):
        BRIDGE_GAMEDATA.require(self)
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, "Bg0002")
        old = tool.hostile_roster(
            sources, tool.IDENTITY_RULE_CLINE, tool.OUTFIT_RULE_UNAMBIGUOUS,
        )
        new = tool.hostile_roster(
            sources, tool.IDENTITY_RULE_CLINE, tool.OUTFIT_RULE_ANY,
        )
        self.assertEqual(len(old), BG0002_HOSTILE_UNDER_OLD_RULE)
        self.assertEqual(len(new), BG0002_HOSTILE_UNDER_OWNER_RULE)
        # Every row the old rule kept is still kept: the ruling ADDS
        # monsters, it never moves or drops one that already shipped.
        old_indices = {row["placement_index"] for row in old}
        new_indices = {row["placement_index"] for row in new}
        self.assertTrue(old_indices <= new_indices)
        self.assertEqual(
            len(new_indices - old_indices),
            BG0002_HOSTILE_UNDER_OWNER_RULE - BG0002_HOSTILE_UNDER_OLD_RULE,
        )
        self.assertEqual(
            {row["template_id"] for row in new},
            BG0002_TEMPLATES_UNDER_OWNER_RULE,
        )

    def test_every_row_the_owner_rule_gains_was_refused_for_the_outfit_only(
        self,
    ):
        """The ruling's own premise, checked rather than repeated.

        COO-DECISION 20260907_1346 says those 40 placements fell to the
        outfit half "and nothing else".  If any of them had also failed the
        rank/AI predicate, the count above would be right for the wrong
        reason -- so each gained row is asked, under the OLD rule, why it
        was not carried, and the answer has to be the variant-list one.
        """
        BRIDGE_GAMEDATA.require(self)
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, "Bg0002")
        old_indices = {
            row["placement_index"] for row in tool.hostile_roster(
                sources, tool.IDENTITY_RULE_CLINE,
                tool.OUTFIT_RULE_UNAMBIGUOUS,
            )
        }
        gained = [
            row for row in tool.hostile_roster(
                sources, tool.IDENTITY_RULE_CLINE, tool.OUTFIT_RULE_ANY,
            )
            if row["placement_index"] not in old_indices
        ]
        self.assertTrue(gained)
        reasons = {
            tool.unresolved_reason(
                sources, row["set_number"], tool.IDENTITY_RULE_CLINE,
                tool.OUTFIT_RULE_UNAMBIGUOUS,
            )
            for row in gained
        }
        self.assertTrue(
            all(reason.endswith("_avatar_is_a_variant_list")
                for reason in reasons),
            "a gained row was refused for something other than its outfit: "
            "%r" % sorted(reasons),
        )
        # And under the owner's rule none of them has a refusal reason left.
        self.assertEqual(
            {
                tool.unresolved_reason(
                    sources, row["set_number"], tool.IDENTITY_RULE_CLINE,
                    tool.OUTFIT_RULE_ANY,
                )
                for row in gained
            },
            {""},
        )

    def test_the_bg0001_control_is_re_pinned_for_the_owner_rule(self):
        """The re-pin COO-DECISION 20260907_1346 asks for, run.

        Both halves, in one test, because the point is that neither
        replaced the other: the old rule still reproduces v141 exactly, and
        the new rule contains that table unchanged.
        """
        BRIDGE_GAMEDATA.require(self)
        tool = _load_tool()
        compared, mismatches = tool.verify_frozen(GAMEDATA, LEGACY)
        self.assertEqual(compared, BG0001_FROZEN_ROWS)
        self.assertEqual(mismatches, 0)
        derived, matched, any_mismatches = tool.verify_frozen_any(
            GAMEDATA, LEGACY,
        )
        self.assertEqual(derived, BG0001_ANY_OUTFIT_ROWS)
        self.assertEqual(matched, BG0001_FROZEN_ROWS)
        self.assertEqual(any_mismatches, 0)

    def test_the_re_pinned_control_actually_catches_a_moved_row(self):
        """A control nobody has seen fail is a control nobody has tested.

        The superset claim would be worthless if it passed whatever the
        derived table said, so this moves one derived row's x by a metre and
        demands the control notice.  Measured through the tool's own reader,
        not by editing a file.
        """
        BRIDGE_GAMEDATA.require(self)
        tool = _load_tool()
        original = tool.unambiguous_placements

        def moved(*args, **kwargs):
            rows = original(*args, **kwargs)
            if not rows:
                return rows
            first = list(rows[0])
            first[2] = first[2] + 1.0
            return [tuple(first)] + list(rows[1:])

        tool.unambiguous_placements = moved
        try:
            _derived, _matched, mismatches = tool.verify_frozen_any(
                GAMEDATA, LEGACY,
            )
        finally:
            tool.unambiguous_placements = original
        self.assertEqual(
            mismatches, 1,
            "the re-pinned control did not notice a placement that moved",
        )


if __name__ == "__main__":
    unittest.main()
