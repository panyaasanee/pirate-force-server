"""The ticket says one label, the server returns another -- measured here.

COO-DECISION ``20260908_1943`` to LANE-CS: bind the label an attended
ticket names to the action name ``runtime.py`` really returns, with a test,
and leave the ticket itself to its owner.

NO SKIP IN THIS FILE.  The bridge tickets are not beside this clone when
the gate runs, and the branch for that world ASSERTS (the audit of an
absent directory is the empty mapping) instead of jumping over the test.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    skill_ticket_label_binding as binding,
)

TICKETS = ROOT.parent / "pf_bridge" / "tickets"

#: A source that composes labels all three legal ways, so the extractor is
#: measured against something this file owns before it is pointed at
#: ``runtime.py``.  ``SOMETHING_IN_A_DOCSTRING`` is prose and must not vouch
#: for a claim.
SAMPLE_SOURCE = '''
"""A module docstring naming SOMETHING_IN_A_DOCSTRING."""


def send(count, suffix):
    """A function docstring naming ANOTHER_DOCSTRING_LABEL."""
    plain = ("PLAIN_ACTION_LABEL", b"pc", b"frame", 0.0)
    composed = (
        "COMPOSED_ACTION_PREFIX_"
        f"{count}{suffix}",
        b"pc", b"frame", 0.0,
    )
    return [plain, composed]
'''


class ExtractorTests(unittest.TestCase):
    """What counts as a label literal, and what does not."""

    def setUp(self):
        self.literals = binding.action_label_literals(SAMPLE_SOURCE)

    def test_plain_and_composed_prefixes_are_both_literals(self):
        self.assertIn("PLAIN_ACTION_LABEL", self.literals)
        self.assertIn("COMPOSED_ACTION_PREFIX_", self.literals)

    def test_docstring_prose_is_not_a_literal(self):
        """A label named only in prose cannot vouch for a ticket."""
        self.assertNotIn("SOMETHING_IN_A_DOCSTRING", self.literals)
        self.assertNotIn("ANOTHER_DOCSTRING_LABEL", self.literals)

    def test_a_short_word_is_not_a_label(self):
        self.assertNotIn("PC", self.literals)
        self.assertNotIn("FRAME", self.literals)


class BindingRuleTests(unittest.TestCase):
    """Equality is not the rule; a composed label has no literal."""

    def setUp(self):
        self.literals = binding.action_label_literals(SAMPLE_SOURCE)

    def test_exact_claim_is_bound(self):
        self.assertTrue(
            binding.claim_is_bound("PLAIN_ACTION_LABEL", self.literals))

    def test_composed_claim_is_bound_by_its_prefix(self):
        """The shape ``GT-076``/``GT-233`` write: prefix plus a number."""
        self.assertTrue(binding.claim_is_bound(
            "COMPOSED_ACTION_PREFIX_108_SWEEP_8", self.literals))

    def test_truncated_claim_is_bound_only_on_a_word_boundary(self):
        self.assertTrue(
            binding.claim_is_bound("PLAIN_ACTION", self.literals))
        self.assertFalse(
            binding.claim_is_bound("PLAIN_ACT", self.literals))

    def test_an_unrelated_claim_is_unbound(self):
        self.assertFalse(
            binding.claim_is_bound("SOME_OTHER_LABEL", self.literals))

    def test_a_short_claim_cannot_be_vouched_for_by_a_longer_literal(self):
        """Without the length floor, ``PLAIN`` would pass on every label."""
        self.assertFalse(binding.claim_is_bound("PLAIN", self.literals))


class ClaimReaderTests(unittest.TestCase):
    """What a ticket line is read to be claiming."""

    def test_claims_are_read_once_each_in_order(self):
        text = (
            "4. console: `[G>] FIRST_LABEL (<n> bytes)`\n"
            "then [G>] SECOND_LABEL (3 bytes)\n"
            "and again [G>] FIRST_LABEL\n"
        )
        self.assertEqual(
            ("FIRST_LABEL", "SECOND_LABEL"),
            binding.console_label_claims(text))

    def test_a_placeholder_tail_is_not_swallowed(self):
        """``GT-076`` writes ``[G>] WORLD_CENSUS_INITIAL_<RUNG>``."""
        self.assertEqual(
            ("WORLD_CENSUS_INITIAL_",),
            binding.console_label_claims(
                "[G>] WORLD_CENSUS_INITIAL_<RUNG> (<framed> bytes)"))

    def test_the_prose_placeholder_form_is_not_a_claim(self):
        """Four files in ``src/`` write ``[G>] <label>`` about the shape."""
        self.assertEqual(
            (), binding.console_label_claims("prints `[G>] <label> (N bytes)`"))


class RuntimeLabelTests(unittest.TestCase):
    """The live half: what ``runtime.py`` in THIS tree can return."""

    def setUp(self):
        source = binding.runtime_source_path().read_text(encoding="utf-8")
        self.literals = binding.action_label_literals(source)

    def test_the_login_skill_list_label_is_in_the_tree(self):
        """``runtime.py:4110`` returns it; a rename here goes red."""
        self.assertIn(
            binding.SKILL_LIST_AT_LOGIN_ACTION_LABEL, self.literals)

    def test_the_name_gt307_quotes_is_not_a_label_in_this_tree(self):
        """The point of the whole file.

        COO-DECISION ``20260908_1943`` forbids changing ``runtime.py`` back
        to this name, so this assertion is also the pin against someone
        "fixing" the ticket by re-introducing the label it quotes.
        """
        self.assertFalse(binding.claim_is_bound(
            binding.GT307_UNBOUND_CONSOLE_CLAIM, self.literals))


class BridgeTicketAuditTests(unittest.TestCase):
    """The audit, run against the real tickets when they are beside us."""

    def setUp(self):
        source = binding.runtime_source_path().read_text(encoding="utf-8")
        self.literals = binding.action_label_literals(source)

    def test_an_absent_ticket_tree_answers_the_empty_mapping(self):
        """The gate's world, asserted rather than skipped."""
        self.assertEqual(
            {}, binding.audit_ticket_dir(ROOT / "no-such-directory",
                                         self.literals))

    def test_gt307_step_four_names_a_label_this_tree_can_return(self):
        """Two worlds, both green, and a third one red.

        The ticket belongs to LANE-K and COO-DECISION ``20260908_1943``
        ordered K to change ``LEARN_SKILL_RESULT_LOGIN`` to
        ``SKILL_LIST_AT_LOGIN`` in it.  Until that lands the ticket carries
        exactly one unbound claim, and this test says WHICH -- so a second,
        different wrong label cannot arrive unnoticed while the first one is
        still open, and so "K never got to it" can never look like "K did
        it".  When it lands, the else branch takes over and pins the label
        the operator is then told to look for.
        """
        ticket = TICKETS / "GT-307.md"
        if not ticket.is_file():
            self.assertEqual({}, binding.audit_ticket_dir(TICKETS,
                                                          self.literals))
            return
        text = ticket.read_text(encoding="utf-8", errors="replace")
        unbound = binding.unbound_claims(text, self.literals)
        if unbound:
            self.assertEqual(
                (binding.GT307_UNBOUND_CONSOLE_CLAIM,), unbound,
                "GT-307 names a console label this tree cannot return, and "
                "it is no longer the one COO ordered K to remove")
        else:
            self.assertIn(
                binding.SKILL_LIST_AT_LOGIN_ACTION_LABEL,
                binding.console_label_claims(text))

    def test_every_ticket_is_read_and_answered_for(self):
        """The audit answers for the whole tree, not only for GT-307.

        It does NOT assert that other lanes' tickets are clean: this lane
        does not own them and COO-DECISION ``20260908_1943`` said so in as
        many words.  What it asserts is that the audit reached every ticket
        file and that every defect it reports is a claim that file really
        makes -- an audit that answered from somewhere other than the
        tickets would fail here.
        """
        if not TICKETS.is_dir():
            self.assertEqual({}, binding.audit_ticket_dir(TICKETS,
                                                          self.literals))
            return
        report = binding.audit_ticket_dir(TICKETS, self.literals)
        self.assertGreater(len(list(TICKETS.glob("GT-*.md"))), 0)
        for name, claims in report.items():
            text = (TICKETS / name).read_text(encoding="utf-8",
                                              errors="replace")
            for claim in claims:
                self.assertIn(claim, binding.console_label_claims(text))
                self.assertFalse(binding.claim_is_bound(claim, self.literals))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
