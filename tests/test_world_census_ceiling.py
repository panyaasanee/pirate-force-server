"""BUILD-001's last field: is 108/115 a shortfall or the data's own ceiling.

LANE-A round tz2eri.  ``RE-149`` came back DONE / BOUNDED-NEGATIVE for the
five CLINE leaders it covers, which is what lets the census stop at 108
without the target being quietly rewritten - the one thing CHARTER-02 and
BUILD-001's own red rule both forbid.  These tests pin the shape of that
verdict on the console line, and - more importantly - pin the ways it must
REFUSE to speak, because a citation that stretches to cover rows the ticket
never looked at is worse than no citation at all.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population
from pirateforce_foundation import world_port_royal_identity as identity_table
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.world_population import (
    CENSUS_COUNT,
    build_world_population,
    ceiling_console_token,
    census_console_line,
)

SHIPPED_CENSUS_COUNT = 108


class CeilingClassificationTests(unittest.TestCase):
    """``ceiling_class_for_leader`` - the three named reasons and the fourth."""

    #: (Mob-Set number, CLINE leader) for each of RE-149's five, as the
    #: frozen table records them.
    ADJUDICATED_ROWS = ((1, 155), (76, 819), (112, 937), (113, 942),
                        (110, 9107))

    def test_the_five_re149_adjudicated_are_the_no_avatar_source_class(
        self,
    ) -> None:
        for template_id, leader in self.ADJUDICATED_ROWS:
            self.assertEqual(
                identity_table.ceiling_class_for_placement(template_id, leader),
                identity_table.CEILING_CLASS_NO_AVATAR_SOURCE,
                "leader %d is one of RE-149's five" % leader,
            )

    def test_leader_zero_is_an_empty_slot_not_an_re149_finding(self) -> None:
        """The two of the seven that RE-149 never looked at.

        Placements 86 and 87 carry CLINE leader 0 - the table saying the slot
        is empty.  If this ever answered ``no_avatar_source`` the console
        would credit RE-149 with two rows outside its scope.
        """
        for template_id in (86, 87):
            self.assertEqual(
                identity_table.ceiling_class_for_placement(template_id, 0),
                identity_table.CEILING_CLASS_NO_CREATURE,
            )

    def test_leader_with_a_mobs_row_but_no_outfit_is_its_own_class(
        self,
    ) -> None:
        self.assertEqual(
            identity_table.ceiling_class_for_placement(101, 10002),
            identity_table.CEILING_CLASS_NO_OUTFIT_COLUMN,
        )

    def test_an_id_nobody_adjudicated_says_so_instead_of_citing_re149(
        self,
    ) -> None:
        """The finding this whole classification exists to make visible.

        A future data change that refuses some NEW leader must not be able to
        arrive on the console wearing RE-149's verdict.  RE-149 answered a
        question about five specific ids; anything else is unadjudicated
        until somebody adjudicates it.
        """
        for leader in (1, 156, 8529, 855, 99999):
            self.assertEqual(
                identity_table.ceiling_class_for_placement(999, leader),
                identity_table.CEILING_CLASS_UNADJUDICATED,
                "leader %d was never adjudicated by any ticket" % leader,
            )

    def test_the_verdict_does_not_outlive_the_fact_it_measured(self) -> None:
        """RE-149 measured a STATE - "no CONSTDATA MOBS row at all".

        Give leader 155 a MOBS row whose ``s_OUTFIT`` is empty - a different,
        already-named state - and the citation has to stop, even though the
        id has not moved.  Keying on the id alone let the verdict outlive the
        fact underneath it with nothing on the line to show the drift
        (pf-adversary, F4).
        """
        original = identity_table.UNRESOLVED[1]
        identity_table.UNRESOLVED[1] = (
            155, "MOBS row 155 has no s_OUTFIT avatar template")
        try:
            self.assertEqual(
                identity_table.ceiling_class_for_placement(1, 155),
                identity_table.CEILING_CLASS_NO_OUTFIT_COLUMN,
            )
        finally:
            identity_table.UNRESOLVED[1] = original
        self.assertEqual(
            identity_table.ceiling_class_for_placement(1, 155),
            identity_table.CEILING_CLASS_NO_AVATAR_SOURCE,
        )

    def test_a_number_collision_from_another_id_space_is_not_adjudicated(
        self,
    ) -> None:
        """``CHANGE_MODEL`` row 155 is a FIREARM, which RE-149 names as the
        number-collision temptation.  Asked about a Mob-Set number that is
        not a refused placement, the answer must not be RE-149's verdict just
        because the integer 155 appears in the pin."""
        self.assertEqual(
            identity_table.ceiling_class_for_placement(4242, 155),
            identity_table.CEILING_CLASS_UNADJUDICATED,
        )

    def test_the_two_name_collisions_re149_refused_are_not_adjudicated(
        self,
    ) -> None:
        """``Tuna`` 8529 and ``Jack`` 855 share a DISPLAY NAME with two of the
        five and are not crosswalked to them - RE-149's nonclaim 3, made
        executable.  Reading either as an avatar source is the specific
        mistake the ticket went out of its way to name."""
        self.assertNotIn(8529, identity_table.CEILING_ADJUDICATED_LEADERS)
        self.assertNotIn(855, identity_table.CEILING_ADJUDICATED_LEADERS)

    def test_a_non_integer_leader_is_refused_rather_than_classified(
        self,
    ) -> None:
        for bad in ("155", 155.0, None, True):
            with self.assertRaises(ValueError):
                identity_table.ceiling_class_for_placement(1, bad)
            with self.assertRaises(ValueError):
                identity_table.ceiling_class_for_placement(bad, 155)

    def test_every_leader_re149_adjudicated_is_still_a_refused_leader(
        self,
    ) -> None:
        """Today the pin and the refusal table agree, so nothing is stale."""
        refused = {leader for leader, _ in identity_table.UNRESOLVED.values()}
        for leader in identity_table.CEILING_ADJUDICATED_LEADERS:
            self.assertIn(leader, refused)
        self.assertEqual(identity_table.CEILING_TICKET_STALE_LEADERS, ())

    def test_a_stale_pin_is_reported_and_does_not_take_the_server_down(
        self,
    ) -> None:
        """The failure mode this must NOT have.

        If a data pack ever resolves one of the five, this module is
        describing a closed question - but it is imported by
        ``world_population``, which is imported by ``runtime.py``.  A raise
        here would mean: the day the town gets five residents back, nobody
        can log in at all.  The staleness travels to the console instead.

        Driven by recomputing the pin's own expression against a refusal
        table that has resolved leader 155, which is what a regeneration
        would produce.
        """
        # The module's OWN derivation, handed the refusal table a
        # regeneration that resolved leader 155 would produce.  An earlier
        # version of this test recomputed the expression itself, which meant
        # replacing the whole derivation with a literal ``()`` - disabling
        # staleness detection outright - kept it green (mutant M11).
        resolved_one = {
            leader
            for leader, _ in identity_table.UNRESOLVED.values()
            if leader != 155
        }
        self.assertEqual(
            identity_table.stale_adjudicated_leaders(resolved_one), (155,))
        self.assertEqual(
            identity_table.stale_adjudicated_leaders(set()),
            (155, 819, 937, 942, 9107),
            "a table refusing nobody leaves the whole pin stale",
        )
        # And the module is importable in that state - i.e. nothing about
        # this condition is expressed as an import-time raise.
        import importlib

        importlib.reload(identity_table)
        self.assertEqual(identity_table.CEILING_TICKET_STALE_LEADERS, ())


class CeilingConsoleTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            cls.legacy.V134_PLAYER_X,
            cls.legacy.V134_PLAYER_Y,
            cls.legacy.V134_PLAYER_Z,
        )

    def _full(self):
        """The census the way a BOOT asks for it, not the way a test would.

        ``census_count_for_dispatch()`` asks for ``CENSUS_COUNT`` (115) and
        lets the identity filter decide what comes back; this used to request
        the literal 108 instead.  The difference is not cosmetic
        (pf-adversary, F10): with a partially broken identity filter leaving
        110 available, the production path assembles 110 and the field goes
        to ``not_applicable``, while a test requesting 108 assembles exactly
        108 and prints a clean verdict - green suite, dark console.
        """
        return build_world_population(
            self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)

    def test_the_whole_census_names_the_ticket_the_verdict_and_the_classes(
        self,
    ) -> None:
        token = ceiling_console_token(self._full())
        self.assertEqual(
            token,
            "ceiling=108/115 client_data_bounded RE-149:BOUNDED-NEGATIVE "
            "no_avatar_source=5,no_creature=2",
        )

    def test_the_classes_account_for_every_placement_in_the_frozen_table(
        self,
    ) -> None:
        """108 + 5 + 2 = 115, read off the console line itself.

        This is BUILD-001's red rule in one assertion: the census that went
        out, plus every placement that did not with a named reason, is the
        whole target.  A shortfall with no reason attached would break it.
        """
        generation = self._full()
        token = ceiling_console_token(generation)
        classes = token.rsplit(" ", 1)[1]
        counted = dict(
            (part.split("=")[0], int(part.split("=")[1]))
            for part in classes.split(",")
        )
        self.assertEqual(
            generation.actor_count + sum(counted.values()), CENSUS_COUNT)
        self.assertNotIn(
            identity_table.CEILING_CLASS_UNADJUDICATED, counted,
            "every placement the census drops today has a recorded reason",
        )

    def test_the_token_is_on_the_census_line_after_the_names(self) -> None:
        line = census_console_line(self._full())
        self.assertIn("| ceiling=108/115 client_data_bounded", line)
        self.assertLess(
            line.index("undressable="), line.index("ceiling="),
            "who is missing comes before why they can never arrive",
        )

    def test_the_line_still_starts_with_the_prefix_every_reader_greps(
        self,
    ) -> None:
        """Appended, not spliced: the fields ahead of it are untouched."""
        line = census_console_line(self._full())
        self.assertTrue(line.startswith("WORLD_CENSUS assembled=108/115 wire=108"))

    def test_the_line_cannot_print_two_disagreeing_counts_of_itself(
        self,
    ) -> None:
        """``ceiling=N/115`` and ``assembled=N/115`` must be the same N.

        Both describe what this census composed, so they read the same source
        (``len(generation.indices)``, which is ``dispatch_report``'s
        ``assembled_count``).  Driven with a generation whose ``actor_count``
        has been forced out of step with its real membership - the shape a
        future splice bug would have - because that is the only state where
        reading the wrong field is visible at all.
        """
        import dataclasses

        generation = self._full()
        line = census_console_line(generation)
        self.assertIn("assembled=108/115", line)
        self.assertIn("ceiling=108/115", line)

        skewed = dataclasses.replace(generation, actor_count=42)
        self.assertIn("ceiling=108/115", ceiling_console_token(skewed))

    def test_a_diagnostic_rung_refuses_to_answer_a_question_nobody_asked(
        self,
    ) -> None:
        """A short rung is short because somebody asked for a short rung.

        Printing a ceiling verdict beside it would read as "this build can
        only manage 3 of 115", which is the exact shape of false report
        BUILD-001's rule exists to stop.
        """
        for size in (3, 20, 91):
            rung = build_world_population(
                self.legacy, self.anchor, size, scene_id=1)
            self.assertEqual(
                ceiling_console_token(rung), "ceiling=not_applicable")

    def test_no_rung_but_the_whole_census_can_reach_the_verdict(self) -> None:
        """The ``not_applicable`` guard, driven across every rung size.

        The guard is arithmetic - ``actor_count + len(undressable) ==
        CENSUS_COUNT`` - and arithmetic can be satisfied by coincidence, so
        this drives all 108 sizes rather than arguing that it cannot be.
        ``undressable`` is a property of the scene's frozen table and is the
        same seven on every rung, so the only size that can reach the verdict
        is the one where the census is whole.
        """
        verdicts = [
            size
            for size in range(1, SHIPPED_CENSUS_COUNT + 1)
            if not ceiling_console_token(
                build_world_population(
                    self.legacy, self.anchor, size, scene_id=1)
            ).endswith("not_applicable")
        ]
        self.assertEqual(verdicts, [SHIPPED_CENSUS_COUNT])

    def test_never_measured_and_measured_zero_stay_different_facts(
        self,
    ) -> None:
        """``not_recorded`` is "nobody asked", and it is not ``0``.

        Same distinction ``undressable=`` already draws.  A generation built
        before this measurement existed must not print a verdict it never
        made.
        """
        import dataclasses

        blank = dataclasses.replace(self._full(), undressable=None)
        self.assertEqual(ceiling_console_token(blank), "ceiling=not_recorded")

    def test_something_that_is_not_a_generation_cannot_produce_a_verdict(
        self,
    ) -> None:
        for bad in (None, "108", 108, object(), {}):
            self.assertEqual(ceiling_console_token(bad), "ceiling=not_recorded")

    def test_a_malformed_row_degrades_the_field_instead_of_killing_the_boot(
        self,
    ) -> None:
        """Nothing composed inside a boot's own log line may raise.

        A boot that dies printing its census line is strictly worse than one
        that prints a weaker field, which is why this path is caught rather
        than allowed to propagate.
        """
        import dataclasses

        broken = dataclasses.replace(
            self._full(),
            undressable=((0, 1, "not-an-int", "Port transportation"),) * 7,
        )
        token = ceiling_console_token(broken)
        self.assertTrue(token.startswith("ceiling=unavailable:"), token)
        self.assertTrue(token.isascii())

    def test_a_new_unadjudicated_refusal_reaches_the_console_as_such(
        self,
    ) -> None:
        """The regression that matters, driven rather than argued.

        A placement refused for a reason no ticket has covered must print
        under ``unadjudicated`` - it must not be absorbed into RE-149's
        count, which is what a reader would otherwise take as "somebody
        checked this".
        """
        import dataclasses

        generation = self._full()
        rows = list(generation.undressable)
        rows[0] = (0, 999, 4242, "Somebody New")
        mutated = dataclasses.replace(generation, undressable=tuple(rows))
        token = ceiling_console_token(mutated)
        self.assertIn("unadjudicated=1", token)
        self.assertIn("no_avatar_source=4", token)
        # AND THE SENTENCE A READER ACTUALLY READS (pf-adversary, F1).  The
        # first version of this test asserted only the tail counts and let
        # the headline claim through: the citation and its verdict still sat
        # at the head of the field, where an eye and a
        # ``grep 'ceiling=.*BOUNDED-NEGATIVE'`` both land.  An honest count
        # behind a false claim is worse than either alone.
        self.assertNotIn("client_data_bounded", token)
        self.assertNotIn("BOUNDED-NEGATIVE", token)
        self.assertIn("UNADJUDICATED=1", token)
        self.assertIn("verdict_withheld", token)

    def test_a_census_with_nothing_adjudicated_cites_nobody(self) -> None:
        """The pathological end of F1, driven rather than argued.

        Seven rows refused for reasons no ticket looked at: zero rows
        adjudicated by anybody, and the old field still printed
        ``RE-149:BOUNDED-NEGATIVE`` at the head.
        """
        import dataclasses

        generation = self._full()
        rows = tuple(
            (index, 999, 4242, "Somebody New")
            for index, _set, _lead, _name in generation.undressable
        )
        token = ceiling_console_token(
            dataclasses.replace(generation, undressable=rows))
        self.assertIn("UNADJUDICATED=7", token)
        self.assertIn("unadjudicated=7", token)
        self.assertNotIn("RE-149", token)
        self.assertNotIn("client_data_bounded", token)

    def test_a_whole_census_that_lost_a_row_does_not_read_as_a_small_rung(
        self,
    ) -> None:
        """F3: the two facts that used to print the same word.

        A placement dropped for a reason recorded NOWHERE - neither resolved
        nor refused - vanishes from both the census and the undressable
        roster, and this arithmetic is the only check in the tree that would
        notice.  A whole census that does not add up must say so, not borrow
        the word a three-actor diagnostic rung uses.
        """
        import dataclasses

        generation = self._full()
        short = dataclasses.replace(
            generation,
            undressable=generation.undressable[:-1],
            count_source=world_population.COUNT_SOURCE_IDENTITY_RESOLVED,
        )
        token = ceiling_console_token(short)
        self.assertTrue(token.startswith("ceiling=unaccounted:"), token)
        self.assertNotIn("not_applicable", token)
        # ...while a rung that really was asked for keeps the quiet word.
        rung = build_world_population(self.legacy, self.anchor, 3, scene_id=1)
        self.assertEqual(
            rung.count_source, world_population.COUNT_SOURCE_CALLER)
        self.assertEqual(ceiling_console_token(rung), "ceiling=not_applicable")

    def test_a_stale_pin_actually_reaches_the_console(self) -> None:
        """F2: the mitigation that replaced the boot-killing raise.

        Deleting the whole ``ticket_stale=`` suffix left the suite green -
        the branch had never executed in any test - so the field could have
        gone dark on precisely the boot it exists for.  This drives it.
        """
        generation = self._full()
        original = identity_table.CEILING_TICKET_STALE_LEADERS
        identity_table.CEILING_TICKET_STALE_LEADERS = (155, 819)
        try:
            token = ceiling_console_token(generation)
        finally:
            identity_table.CEILING_TICKET_STALE_LEADERS = original
        self.assertIn(" ticket_stale=155,819", token)
        self.assertTrue(token.isascii())
        token.encode("cp874")
        # and it is absent, not empty, when the pin is current
        self.assertNotIn("ticket_stale", ceiling_console_token(generation))

    def test_the_class_fields_are_ordered_not_incidentally_sorted(
        self,
    ) -> None:
        """F9: an exact-string assertion pins ordering only by luck.

        Today insertion order happens to equal sorted order, so dropping
        ``sorted()`` changed nothing.  Driven with rows whose insertion order
        is deliberately the reverse.
        """
        import dataclasses

        generation = self._full()
        rows = (
            (86, 86, 0, ""),
            (0, 1, 155, "Port transportation"),
        ) + generation.undressable[2:]
        token = ceiling_console_token(
            dataclasses.replace(
                generation,
                undressable=rows,
                count_source=world_population.COUNT_SOURCE_IDENTITY_RESOLVED,
            )
        )
        classes = token.rsplit(" ", 1)[1]
        keys = [part.split("=")[0] for part in classes.split(",")]
        self.assertEqual(keys, sorted(keys))

    def test_every_state_of_this_field_survives_the_bridge_console(
        self,
    ) -> None:
        """The bridge console is cp874.  Each state, not just the happy one."""
        import dataclasses

        generation = self._full()
        states = [
            ceiling_console_token(generation),
            ceiling_console_token(
                build_world_population(self.legacy, self.anchor, 3, scene_id=1)),
            ceiling_console_token(dataclasses.replace(
                generation, undressable=None)),
            ceiling_console_token(None),
            ceiling_console_token(dataclasses.replace(
                generation, undressable=((0, 1, "bad", "x"),) * 7)),
            census_console_line(generation),
        ]
        for token in states:
            self.assertTrue(token.isascii(), token)
            token.encode("ascii")
            token.encode("cp874")


class CeilingProvenanceTests(unittest.TestCase):
    """The pinned facts a reader of the console line would go looking for."""

    def test_the_ticket_and_its_verdict_are_named_exactly(self) -> None:
        self.assertEqual(identity_table.CEILING_TICKET, "RE-149")
        self.assertEqual(
            identity_table.CEILING_TICKET_VERDICT, "BOUNDED-NEGATIVE")
        self.assertEqual(
            identity_table.CEILING_TICKET_ANSWERED_AT,
            "2026-08-29T18:14+07:00",
        )

    def test_the_adjudicated_list_is_the_tickets_own_five(self) -> None:
        self.assertEqual(
            tuple(sorted(identity_table.CEILING_ADJUDICATED_LEADERS)),
            (155, 819, 937, 942, 9107),
        )

    def test_the_verdict_is_not_written_as_a_claim_of_impossibility(
        self,
    ) -> None:
        """RE-149 is bounded-negative at the static ceiling of the CURRENT
        corpus.  It does not claim another build lacks these five, and it
        does not claim from a screen that they cannot be drawn.  The console
        word is ``client_data_bounded`` for that reason, and a word like
        ``impossible`` here would be a claim the ticket refused to make."""
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        anchor = (
            legacy.V134_PLAYER_X, legacy.V134_PLAYER_Y, legacy.V134_PLAYER_Z)
        token = ceiling_console_token(build_world_population(
            legacy, anchor, SHIPPED_CENSUS_COUNT, scene_id=1))
        self.assertIn("client_data_bounded", token)
        for forbidden in ("impossible", "proved", "cannot_exist", "never"):
            self.assertNotIn(forbidden, token)


if __name__ == "__main__":
    unittest.main()
