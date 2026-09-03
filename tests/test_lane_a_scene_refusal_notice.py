"""The refusal notice names the login it refused, and never dies trying.

These tests drive `world_scene_refusal_notice` against REAL refusals raised
by `world_scene_entry.resolve_entry` wherever one can be provoked, rather
than against handmade exception objects only: a notice that formats a stub
correctly and misreads the exception the tree actually raises would be worse
than no notice at all.

The composer decides nothing, so there is no admission test here on purpose.
What is tested is the property the round was ordered to deliver
(COO-DECISION 20260903_1249 point 4): the line is observable, it names the
subject exactly, and it cannot go quiet.

WHAT THE FIRST DRAFT OF THIS FILE DID NOT TEST, AND WHY EVERY ASSERTION NOW
GOES THROUGH `_fields`.  pf-adversary mutated `_int_token` to append a digit
- the console then named character 70 where the row said 7 - and all 22
tests stayed green, because each one asserted an unbounded substring
(`assertIn("refused_character_id=41", line)` matches `...=417` too).  The
single property this module exists to deliver was pinned by nothing.  Three
of the module's constants were in the same shape: mutating `CONSOLE_TOKEN`,
`MESSAGE_LIMIT` and `UNKNOWN` left the suite green because every assertion
compared them to themselves.  Both scars are pinned below.
"""

import ast
import io
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import model  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    world_scene_refusal_notice as notice,
)


def _character(name="Blackbeard", char_id=7, account_id=3, selector=0):
    return model.Character(
        id=char_id,
        account_id=account_id,
        selector=selector,
        name=name,
        actor_wire=b"",
        avatar_wire=b"",
        identity_lo=0,
        identity_hi=0,
        position=model.Position(scene_id=1, scene_seq=0, x=0.0, y=0.0, z=0.0),
    )


def _row(scene_id=278, scene_seq=0):
    return model.Position(
        scene_id=scene_id, scene_seq=scene_seq, x=1.0, y=2.0, z=3.0
    )


def _parse(line):
    """``(token, bracketed_reason, fields)``, parsed exactly - no substrings.

    Everything after the first ``refusal_message=`` is free text by the
    module's own contract and comes back whole under that key; every
    structured field precedes it, so a forged ``key=value`` inside the free
    text cannot shadow a real one.  The parser refuses a duplicated key,
    which is how a forged field would show up if the ordering contract ever
    broke.
    """
    marker = " refusal_message="
    head, sep, message = line.partition(marker)
    tokens = head.split(" ")
    fields = {}
    for token in tokens[2:]:
        key, eq, value = token.partition("=")
        assert eq, f"unparsable token {token!r} in {line!r}"
        assert key not in fields, f"duplicate field {key!r} in {line!r}"
        fields[key] = value
    if sep:
        fields["refusal_message"] = message
    return tokens[0], tokens[1], fields


class RealRefusalTests(unittest.TestCase):
    """Drive the composer with an exception the tree really raises."""

    def _real_refusal(self):
        row = model.Position(
            scene_id=0xFFFE, scene_seq=0, x=0.0, y=0.0, z=0.0
        )
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_scene_entry.resolve_entry(row, emit=lambda _line: None)
        return caught.exception, row

    def test_the_line_leads_with_token_and_bracketed_reason(self):
        error, row = self._real_refusal()
        line = notice.refusal_console_line(error, _character(), row)
        token, bracket, _fields = _parse(line)
        self.assertEqual(token, "WORLD_SCENE_ENTRY_REFUSED")
        self.assertEqual(bracket, f"[{error.reason}]")

    def test_the_exception_text_survives_verbatim_at_the_end(self):
        error, row = self._real_refusal()
        line = notice.refusal_console_line(error, _character(), row)
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refusal_message"], str(error))

    def test_line_names_the_subject_exactly(self):
        error, row = self._real_refusal()
        line = notice.refusal_console_line(
            error, _character(name="Anne", char_id=41, account_id=9), row
        )
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refused_character_id"], "41")
        self.assertEqual(fields["refused_account_id"], "9")
        self.assertEqual(fields["refused_selector"], "0")
        self.assertEqual(fields["refused_name"], "Anne")
        self.assertEqual(
            fields["refused_row_scene_id"], str(row.scene_id)
        )
        self.assertEqual(
            fields["refused_row_scene_seq"], str(row.scene_seq)
        )

    def test_an_id_one_digit_wrong_is_a_failure_not_a_pass(self):
        """The scar, pinned: a mutated id must not slip past this file."""
        error, row = self._real_refusal()
        line = notice.refusal_console_line(
            error, _character(char_id=7, account_id=3), row
        )
        _token, _bracket, fields = _parse(line)
        for wrong in ("70", "77", "007", "7 "):
            self.assertNotEqual(fields["refused_character_id"], wrong)
        self.assertEqual(fields["refused_character_id"], "7")


class TokenIsPinnedToItsConsumersTests(unittest.TestCase):
    """The token is compared to its TARGETS, not to itself.

    `CONSOLE_TOKEN` mutated to `WORLD_SCENE_ENTRY_REFUSED_V2` left the first
    draft of this file green, because every assertion read
    `notice.CONSOLE_TOKEN`.  The module's central promise is that the string
    is byte-identical to what `runtime.py` prints and what other test files
    grep for, so that is what is asserted: the literal, and the literal as it
    appears in those files on disk.
    """

    def test_the_token_is_the_literal_string(self):
        self.assertEqual(
            notice.CONSOLE_TOKEN, "WORLD_SCENE_ENTRY_REFUSED"
        )

    def test_the_token_is_the_one_runtime_prints_today(self):
        """UPDATED IN THE ROUND THAT WIRED THE NOTICE (chief, R322).

        This test used to pin the hand-rolled
        ``print(f"WORLD_SCENE_ENTRY_REFUSED {exc}")`` in ``runtime.py``.
        That line is GONE: the login-refusal handler now prints through
        ``refusal_console_line``, which is what
        ``CORE-REQUEST 20260903_1505`` asked for, so the literal no longer
        appears in ``runtime.py`` at all -- this module is its single
        producer, and that is the improvement, not a regression.

        The promise being pinned is unchanged: the token this module
        composes is the token that reaches the console.  It is now proven
        by DERIVING the producer from ``runtime.py``'s tree instead of
        retyping a line of it (house rule: no hand-copied lists).  The
        handler-level guards -- which handler, with which arguments, and
        that the GM-override probe stays untouched -- live in
        ``tests/test_scene_refusal_notice_wiring.py``.
        """
        runtime = (ROOT / "src" / "pirateforce_foundation" / "runtime.py")
        text = runtime.read_text(encoding="utf-8")
        module = notice.__name__.rsplit(".", 1)[-1]
        tree = ast.parse(text)
        self.assertIn(
            module,
            {
                alias.asname or alias.name
                for node in tree.body
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
            },
            "runtime.py stopped importing the only producer of the token",
        )
        composes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "refusal_console_line"
        ]
        self.assertEqual(
            len(composes),
            1,
            "runtime.py composes the refusal line zero times or more than "
            "once; the token on the console is no longer this module's",
        )
        self.assertNotIn(
            notice.CONSOLE_TOKEN,
            text,
            "the token literal is back in runtime.py beside the composer: "
            "two producers of one console line (COO 20260903_0054 item 2)",
        )

    def test_the_strictest_existing_reader_still_matches_a_composed_line(
        self,
    ):
        """`test_lane_a_scene_census.py` pins token + bracket, contiguous."""
        pinned = "WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]"
        census = ROOT / "tests" / "test_lane_a_scene_census.py"
        self.assertIn(pinned, census.read_text(encoding="utf-8"))
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN, "why"
        )
        line = notice.refusal_console_line(error, _character(), _row())
        self.assertIn(pinned, line)


class EveryDefinedReasonTests(unittest.TestCase):
    """The vocabulary is derived from its owner - and still sanitised.

    Looping over `world_scene_entry.REFUSAL_REASONS` means a reason added
    there later is covered here the day it is added.  It does NOT mean the
    string is trusted: pf-adversary added a reason containing a newline and
    the composer emitted two console lines with the suite green, because
    this class looped without asserting the one-line invariant and the shape
    class asserted the invariant without looping.  Both now happen here.
    """

    def test_each_defined_reason_renders_as_itself_on_exactly_one_line(self):
        self.assertTrue(world_scene_entry.REFUSAL_REASONS)
        for reason in world_scene_entry.REFUSAL_REASONS:
            with self.subTest(reason=reason):
                error = world_scene_entry.SceneEntryRefused(reason, "why")
                line = notice.refusal_console_line(
                    error, _character(), _row()
                )
                _token, bracket, _fields = _parse(line)
                self.assertEqual(bracket, f"[{reason}]")
                self.assertNotIn("\n", line)
                self.assertNotIn("\r", line)
                line.encode("ascii")
                line.encode("cp874")

    def test_a_hostile_reason_string_cannot_split_the_line(self):
        """Derived is not trusted: the vocabulary is sanitised like a name."""

        class _Hostile(Exception):
            reason = "line_one\nline_two"

            def __str__(self):
                return "[line_one] hostile"

        original = world_scene_entry.REFUSAL_REASONS
        world_scene_entry.REFUSAL_REASONS = original + (_Hostile.reason,)
        try:
            line = notice.refusal_console_line(
                _Hostile(), _character(), _row()
            )
        finally:
            world_scene_entry.REFUSAL_REASONS = original
        self.assertNotIn("\n", line)
        self.assertIn("line_one_line_two", line)

    def test_a_reason_outside_the_vocabulary_is_reported_not_passed_through(
        self,
    ):
        @dataclass
        class _Foreign(Exception):
            reason: str = "scene_smells_wrong"

            def __str__(self):
                return "[scene_smells_wrong] invented"

        line = notice.refusal_console_line(_Foreign(), _character(), _row())
        _token, bracket, _fields = _parse(line)
        self.assertEqual(bracket, "[reason_unrecognised]")

    def test_an_error_with_no_reason_attribute_says_so(self):
        line = notice.refusal_console_line(
            LookupError("no reason attribute"), _character(), _row()
        )
        _token, bracket, _fields = _parse(line)
        self.assertEqual(bracket, "[reason_absent]")


class FreeTextCannotForgeAFieldTests(unittest.TestCase):
    """The message is the only field this module does not control.

    pf-adversary drove a row whose `scene_id` was a crafted string through
    the REAL `resolve_entry`; the refusal message then embedded
    `refusal_reason=...` and `refused_character_id=1`, and with the message
    second in the line a first-occurrence parser read a wrong reason and an
    innocent character id off a genuine console line.  The message is last
    now, and this is the test that keeps it there.
    """

    def _forged(self):
        forged = (
            "9 refused_character_id=1 refused_account_id=1 "
            "refused_name=Innocent"
        )
        row = model.Position(
            scene_id=forged, scene_seq=0, x=0.0, y=0.0, z=0.0
        )
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_scene_entry.resolve_entry(row, emit=lambda _line: None)
        return caught.exception, row

    def test_the_real_subject_is_read_first_and_the_forgery_is_free_text(self):
        error, row = self._forged()
        line = notice.refusal_console_line(
            error, _character(name="Anne", char_id=41, account_id=9), row
        )
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refused_character_id"], "41")
        self.assertEqual(fields["refused_account_id"], "9")
        self.assertEqual(fields["refused_name"], "Anne")
        # The forgery is still visible - it is evidence, not something to
        # delete - but it is inside the free text where it belongs.
        self.assertIn("refused_name=Innocent", fields["refusal_message"])

    def test_the_structured_half_has_no_duplicate_keys(self):
        error, row = self._forged()
        # _parse asserts on a duplicate key; this is the test that runs it
        # against the one input designed to produce one.
        _parse(notice.refusal_console_line(error, _character(), row))


class NameHandlingTests(unittest.TestCase):
    """A name is for a person to read, and the console it lands on is cp874."""

    def _fields_for(self, name):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )
        line = notice.refusal_console_line(
            error, _character(name=name), _row()
        )
        return _parse(line)[2]

    def test_ascii_name_is_exact(self):
        fields = self._fields_for("Blackbeard")
        self.assertEqual(fields["refused_name"], "Blackbeard")
        self.assertEqual(fields["refused_name_len"], "10")
        self.assertEqual(fields["refused_name_exact"], "yes")

    def test_non_ascii_name_is_substituted_and_flagged_with_its_true_length(
        self,
    ):
        # Five Thai characters, written as escapes so this file stays ASCII.
        fields = self._fields_for("\u0e01\u0e31\u0e19\u0e22\u0e32")
        self.assertEqual(fields["refused_name"], "?????")
        self.assertEqual(fields["refused_name_len"], "5")
        self.assertEqual(fields["refused_name_exact"], "no")

    def test_a_space_cannot_break_the_key_value_shape(self):
        fields = self._fields_for("Anne Bonny")
        self.assertEqual(fields["refused_name"], "Anne_Bonny")
        self.assertEqual(fields["refused_name_exact"], "no")

    def test_a_long_name_is_capped_at_the_declared_limit(self):
        fields = self._fields_for("x" * 100)
        self.assertEqual(
            fields["refused_name"], "x" * notice.NAME_LIMIT
        )
        self.assertEqual(len(fields["refused_name"]), 32)
        self.assertEqual(fields["refused_name_len"], "100")
        self.assertEqual(fields["refused_name_exact"], "no")

    def test_a_name_that_folds_to_nothing_is_not_confused_with_no_character(
        self,
    ):
        """Every character of the name is unprintable, but a name exists."""
        fields = self._fields_for("\t\u0e31\u0e19")
        self.assertEqual(fields["refused_name_exact"], "no")
        self.assertNotEqual(fields["refused_name_len"], "0")

    def test_a_name_whose_str_raises_is_reported_not_fatal(self):
        class _Explodes:
            def __str__(self):
                raise RuntimeError("boom")

        fields = self._fields_for(_Explodes())
        self.assertEqual(fields["refused_name"], notice.UNKNOWN)
        self.assertEqual(fields["refused_name_len"], "0")

    def test_no_character_at_all_still_produces_a_line(self):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )
        _token, _bracket, fields = _parse(
            notice.refusal_console_line(error)
        )
        self.assertEqual(fields["refused_character_id"], notice.UNKNOWN)
        self.assertEqual(fields["refused_row_scene_id"], notice.UNKNOWN)


class ConstantsArePinnedTests(unittest.TestCase):
    """Each constant is compared to a value, not to itself."""

    def test_the_unknown_spelling_matches_this_lane_s_other_composers(self):
        self.assertEqual(notice.UNKNOWN, "none")
        travel = (
            ROOT / "src" / "pirateforce_foundation" / "world_scene_travel.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"spawn=none"', travel)

    def test_the_message_cap_is_enforced_at_its_declared_value(self):
        self.assertEqual(notice.MESSAGE_LIMIT, 240)
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "y" * 4000
        )
        line = notice.refusal_console_line(error, _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(
            len(fields["refusal_message"]), notice.MESSAGE_LIMIT
        )

    def test_the_name_cap_is_enforced_at_its_declared_value(self):
        self.assertEqual(notice.NAME_LIMIT, 32)


class TheCutMessageSaysItWasCutTests(unittest.TestCase):
    """COO-DECISION 20260903_1746 item 4, the ``MESSAGE_LIMIT`` half.

    `MESSAGE_LIMIT` was enforced and silent: 240 characters of a 4,000
    character message looked exactly like a 240 character message, and the
    one field whose length this module does NOT control was the one field
    that reported no length.  The name half has carried
    ``refused_name_len``/``refused_name_exact`` since round ``od1xso`` for
    this exact reason; these two are the same pair for the message.
    """

    def test_a_cut_message_reports_its_true_length_and_says_it_was_cut(self):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "y" * 4000
        )
        line = notice.refusal_console_line(error, _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refused_message_exact"], "no")
        self.assertEqual(
            fields["refused_message_len"], str(len(str(error)))
        )
        self.assertEqual(
            len(fields["refusal_message"]), notice.MESSAGE_LIMIT
        )

    def test_a_whole_message_says_so_and_agrees_with_what_was_printed(self):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "a short one"
        )
        line = notice.refusal_console_line(error, _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refused_message_exact"], "yes")
        self.assertEqual(
            fields["refused_message_len"],
            str(len(fields["refusal_message"])),
        )

    def test_the_size_fields_precede_the_free_text(self):
        """Otherwise they are fields inside free text, which is not a field.

        The module's whole parsing contract is that every structured field
        comes BEFORE anything ``str(error)`` can forge (see
        ``refusal_console_line``'s docstring).  A length printed after the
        message would be forgeable by the message.
        """
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED,
            "refused_message_len=1 refused_message_exact=yes",
        )
        line = notice.refusal_console_line(error, _character(), _row())
        head, _sep, _message = line.partition(" refusal_message=")
        self.assertIn("refused_message_len=", head)
        self.assertIn("refused_message_exact=", head)
        # `_parse` refuses a duplicated key; the forged copies live in the
        # free text, so the structured half must still parse cleanly.
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refused_message_exact"], "yes")
        self.assertEqual(
            fields["refused_message_len"], str(len(str(error)))
        )

    def test_an_unreadable_message_reports_an_unknown_size_not_a_zero(self):
        """pf-adversary D5.  A length that was never read is not ``0``.

        The first draft of this round pinned ``0``/``no`` here, which under
        the docstring's own rule reads "these 18 characters are a cut of a
        zero-character message".  Every other helper in this file refuses to
        print a plausible number for a value it could not read.
        """

        class Hostile:
            def __str__(self):
                raise RuntimeError("no")

        line = notice.refusal_console_line(Hostile(), _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refusal_message"], "message_unreadable")
        self.assertEqual(fields["refused_message_len"], notice.UNKNOWN)
        self.assertEqual(fields["refused_message_exact"], "no")

    def test_an_empty_message_is_exact_and_zero_because_it_was_measured(self):
        """pf-adversary D5, the other half: nothing was cut here."""

        class Empty:
            def __str__(self):
                return ""

        line = notice.refusal_console_line(Empty(), _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refusal_message"], "message_empty")
        self.assertEqual(fields["refused_message_len"], "0")
        self.assertEqual(fields["refused_message_exact"], "yes")

    def test_the_size_fields_survive_a_subject_half_that_died(self):
        """pf-adversary D3: on the degraded path they must not vanish.

        If the two fields were emitted from the report they would disappear
        exactly when `refused_subject=unreadable` is printed -- and the free
        text, which is `str(error)` and not this module's, would then supply
        the FIRST occurrence of both keys to any parser following this
        line's documented contract.  Measured before the fix: a hostile row
        printed `refused_message_len=9` while the module held 139.
        """

        class BaseExplodes:
            @property
            def name(self):
                raise BaseException("not an Exception")

        forged = (
            "refused_message_len=9 refused_message_exact=yes "
            "refused_character_id=1"
        )
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, forged
        )
        line = notice.refusal_console_line(error, BaseExplodes(), _row())
        self.assertIn("refused_subject=unreadable", line)
        head, sep, _message = line.partition(" refusal_message=")
        self.assertTrue(sep, "the free text marker went missing")
        self.assertIn(f"refused_message_len={len(str(error))}", head)
        self.assertIn("refused_message_exact=yes", head)


class TheBracketNeverPrintsAPrefixTests(unittest.TestCase):
    """COO-DECISION 20260903_1746 item 4, the ``NAME_LIMIT`` half.

    chief's report ``20260903_1605`` item 5: the leading bracket was capped
    at ``NAME_LIMIT``, a number sized for a character name, so a refusal
    reason of 33 characters would have been cut -- and the queue greps
    ``TOKEN [reason]`` as one contiguous string.  Two things changed: the
    reason got its OWN cap, derived from the vocabulary that owns the
    reasons, and a cut reason now prints a word that is not a reason instead
    of a prefix that reads like one.
    """

    @staticmethod
    def _line_for_reason(reason, message="why"):
        """Compose a line for a reason the vocabulary does not have yet.

        The membership check in `_reason_of` reads the vocabulary live, so
        a reason has to be registered for the composer to reach the cap at
        all.  Restored in `finally` so no other test in the process sees it.
        """
        original = world_scene_entry.REFUSAL_REASONS
        try:
            world_scene_entry.REFUSAL_REASONS = original + (reason,)
            error = world_scene_entry.SceneEntryRefused(reason, message)
            return notice.refusal_console_line(error, _character(), _row())
        finally:
            world_scene_entry.REFUSAL_REASONS = original

    def test_the_reason_cap_is_a_number_of_its_own_not_the_name_cap(self):
        """pf-adversary D1: this is the assertion the first draft lacked.

        The first draft asserted `REASON_LIMIT >= NAME_LIMIT` and
        `REASON_LIMIT >= 26`, both of which a one-line revert to
        `REASON_LIMIT = NAME_LIMIT` satisfies -- the mutant that restores
        the exact defect chief reported was GREEN across both test files.
        A reason one character past the NAME cap has to come out WHOLE.
        """
        reason = "scene_" + "y" * (notice.NAME_LIMIT - 5)
        self.assertGreater(len(reason), notice.NAME_LIMIT)
        self.assertLessEqual(len(reason), notice.REASON_LIMIT)
        _token, bracket, _fields = _parse(self._line_for_reason(reason))
        self.assertEqual(bracket, f"[{reason}]")

    def test_the_cap_does_not_move_when_the_vocabulary_does(self):
        """pf-adversary D2: a ceiling the bounded data can raise is not one.

        The first draft computed the cap from `REFUSAL_REASONS` at import.
        A vocabulary carrying a 430-character reason then RAISED the cap to
        430 and composed a 958-character console line -- removing the only
        bound the field had, and making the loud branch below dead code.
        """
        before = notice.REASON_LIMIT
        huge = "scene_" + "z" * 500
        line = self._line_for_reason(huge)
        self.assertEqual(notice.REASON_LIMIT, before)
        self.assertLessEqual(
            len(line),
            notice.REASON_LIMIT + notice.MESSAGE_LIMIT + 400,
            "the bracket stopped being bounded by anything",
        )

    def test_a_reason_past_the_cap_is_named_cut_never_shown_as_a_prefix(self):
        long_reason = "scene_" + "x" * 100
        self.assertGreater(len(long_reason), notice.REASON_LIMIT)
        line = self._line_for_reason(long_reason)
        _token, bracket, _fields = _parse(line)
        self.assertEqual(bracket, f"[{notice.REASON_TRUNCATED}]")
        self.assertNotIn(
            long_reason[: notice.REASON_LIMIT],
            bracket,
            "the bracket printed a prefix of a real reason, which reads "
            "like a real reason to anyone scanning a console",
        )

    def test_a_reason_carrying_a_bracket_cannot_forge_the_queue_s_grep(self):
        """pf-adversary D2, second input.  No truncation is involved.

        `scene_not_allowed_at_login]x` is under every cap and sanitises to
        itself, and the line it composed CONTAINED the contiguous string
        `WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]` that
        GAME_TEST_QUEUE.md:6678 and test_lane_a_scene_census.py:1013 grep --
        so a refusal that is not that reason satisfied both readers.  A
        superstring was always the other way to lie in this field, and it
        predates this round.
        """
        forging = world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN + "]x"
        self.assertLess(len(forging), notice.REASON_LIMIT)
        line = self._line_for_reason(forging)
        _token, bracket, _fields = _parse(line)
        self.assertEqual(bracket, f"[{notice.REASON_MALFORMED}]")
        self.assertNotIn(
            "%s [%s]"
            % (
                notice.CONSOLE_TOKEN,
                world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
            ),
            line,
            "a reason that is not scene_not_allowed_at_login satisfied the "
            "queue's contiguous grep for scene_not_allowed_at_login",
        )

    def test_the_cap_is_reached_without_touching_the_vocabulary_at_import(
        self,
    ):
        """pf-adversary D4: nothing about the cap runs untrusted code.

        The first draft iterated `REFUSAL_REASONS` at import behind
        `except Exception`; a vocabulary whose `__iter__` raised
        `SystemExit` stopped the module from LOADING, and `runtime.py`
        imports it to compose the only account of a refused login there is.
        A plain int cannot do that, and this pins that it stayed one.
        """
        self.assertIs(type(notice.REASON_LIMIT), int)
        source = (
            ROOT
            / "src"
            / "pirateforce_foundation"
            / "world_scene_refusal_notice.py"
        ).read_text(encoding="utf-8")
        self.assertIn("\nREASON_LIMIT = %d\n" % notice.REASON_LIMIT, source)


class TotalityTests(unittest.TestCase):
    """The composer runs inside an `except`: it may never raise from there.

    And it may never trade the half the console already has for the half
    this round adds: a broken SUBJECT costs the subject fields, never the
    reason or the message.
    """

    def test_nothing_it_can_be_handed_makes_it_raise(self):
        class _Exploding:
            @property
            def name(self):
                raise RuntimeError("boom")

            @property
            def id(self):
                raise RuntimeError("boom")

        class _StrExplodes(Exception):
            reason = world_scene_entry.REFUSED_SCENE_NOT_PINNED

            def __str__(self):
                raise RuntimeError("boom")

        class _BaseExplodes:
            @property
            def id(self):
                raise KeyboardInterrupt("not even this")

        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )
        cases = [
            (None, None, None),
            (object(), object(), object()),
            (error, object(), object()),
            (_StrExplodes(), _character(), _row()),
            (error, _Exploding(), _row()),
            (error, _character(), _Exploding()),
            (error, _BaseExplodes(), _row()),
            ("a string, not an exception", _character(), _row()),
            (error, _character(name=None), _row()),
        ]
        for index, (err, char, row) in enumerate(cases):
            with self.subTest(case=index):
                line = notice.refusal_console_line(err, char, row)
                self.assertTrue(line.startswith("WORLD_SCENE_ENTRY_REFUSED"))
                self.assertNotIn("\n", line)
                line.encode("cp874")

    def test_a_huge_integer_id_is_reported_not_fatal(self):
        """CPython caps int->str at 4300 digits; `str(value)` can raise."""
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )

        class _Huge:
            id = 10 ** 5000
            account_id = 3
            selector = 0
            name = "Blackbeard"

        line = notice.refusal_console_line(error, _Huge(), _row())
        _token, bracket, fields = _parse(line)
        self.assertEqual(bracket, "[scene_not_pinned]")
        self.assertEqual(fields["refused_character_id"], "not_an_int")
        # refusal_report is advertised for reports: it must not raise either.
        report = notice.refusal_report(error, _Huge(), _row())
        self.assertEqual(report["character_id"], "not_an_int")

    def test_a_broken_subject_does_not_cost_the_console_the_reason(self):
        """The half the console HAS today must survive the half being added.

        `runtime.py` prints `str(exc)` today and `str(exc)` never touches the
        character object.  If a raising property on that object collapsed the
        whole line, this round would have traded the reason for the subject -
        a regression wearing an improvement's clothes.
        """

        class _Exploding:
            @property
            def name(self):
                raise RuntimeError("boom")

            @property
            def id(self):
                raise RuntimeError("boom")

            @property
            def account_id(self):
                raise RuntimeError("boom")

        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN, "why"
        )
        line = notice.refusal_console_line(error, _Exploding(), _row())
        _token, bracket, fields = _parse(line)
        self.assertEqual(bracket, "[scene_not_allowed_at_login]")
        self.assertEqual(fields["refusal_message"], str(error))
        self.assertEqual(fields["refused_character_id"], notice.UNKNOWN)
        # The row is fine, so its fields are still there: one broken object
        # does not blank the other.
        self.assertEqual(fields["refused_row_scene_id"], "278")

    def test_an_exploding_str_is_reported_rather_than_swallowed(self):
        class _StrExplodes(Exception):
            reason = world_scene_entry.REFUSED_SCENE_NOT_PINNED

            def __str__(self):
                raise RuntimeError("boom")

        line = notice.refusal_console_line(
            _StrExplodes(), _character(), _row()
        )
        _token, bracket, fields = _parse(line)
        # The reason is still readable even though the message is not.
        self.assertEqual(bracket, "[scene_not_pinned]")
        self.assertEqual(fields["refusal_message"], "message_unreadable")

    def test_an_empty_message_is_named_rather_than_left_blank(self):
        class _Empty(Exception):
            reason = world_scene_entry.REFUSED_SCENE_NOT_PINNED

            def __str__(self):
                return ""

        line = notice.refusal_console_line(_Empty(), _character(), _row())
        _token, _bracket, fields = _parse(line)
        self.assertEqual(fields["refusal_message"], "message_empty")


class ConsoleShapeTests(unittest.TestCase):
    """One ASCII line, or the bridge console cannot print it at all."""

    def _lines(self):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
            "scene 278 is pinned but not allowed as a login destination",
        )
        yield notice.refusal_console_line(error, _character(), _row())
        yield notice.refusal_console_line(
            error,
            _character(name="\u0e01\u0e31\u0e19 \u0e22\u0e32"),
            _row(),
            reply_frames=0,
        )
        yield notice.refusal_console_line(None)

    def test_every_line_is_single_line_ascii_and_cp874_safe(self):
        for line in self._lines():
            with self.subTest(line=line[:40]):
                self.assertNotIn("\n", line)
                self.assertNotIn("\r", line)
                line.encode("ascii")
                line.encode("cp874")

    def test_a_message_with_a_newline_in_it_cannot_split_the_line(self):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED,
            "first line\nsecond line",
        )
        line = notice.refusal_console_line(error, _character(), _row())
        self.assertNotIn("\n", line)
        # The newline is visible as `_` rather than deleted: a message that
        # silently loses a line break is a message a reader mis-parses.
        self.assertIn("first line_second line", line)


class ReplyFramesTests(unittest.TestCase):
    """What the caller does next is the caller's fact, not this module's."""

    def _fields(self, **kwargs):
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )
        line = notice.refusal_console_line(
            error, _character(**kwargs.pop("character", {})), _row(), **kwargs
        )
        return _parse(line)[2]

    def test_unset_reports_unreported_rather_than_guessing_zero(self):
        self.assertEqual(self._fields()["reply_frames"], "unreported")

    def test_zero_is_reported_as_zero(self):
        self.assertEqual(self._fields(reply_frames=0)["reply_frames"], "0")

    def test_a_non_integer_is_reported_not_rendered(self):
        self.assertEqual(
            self._fields(reply_frames="lots")["reply_frames"], "not_an_int"
        )

    def test_a_bool_id_is_a_defect_and_shows_as_one(self):
        fields = self._fields(character={"char_id": True})
        self.assertEqual(fields["refused_character_id"], "not_an_int")


class GateUntouchedTests(unittest.TestCase):
    """The order said not to change the gate by one byte.  Measure it.

    The first draft of this class was a tautology: pf-adversary replaced the
    whole module with an eight-line stub and both tests passed, because they
    only proved that calling a function which does nothing changes nothing.
    These drive the properties directly - the composer opens no file, calls
    no resolver, and mutates neither argument - and then check that
    `resolve_entry` is unmoved.
    """

    def test_the_composer_opens_no_file_and_calls_no_resolver(self):
        opened = []
        real_open = io.open
        real_resolve = world_scene_entry.resolve_entry
        calls = []

        def _spy_open(*args, **kwargs):
            opened.append(args[:1])
            return real_open(*args, **kwargs)

        def _spy_resolve(*args, **kwargs):
            calls.append(args)
            return real_resolve(*args, **kwargs)

        io.open = _spy_open
        world_scene_entry.resolve_entry = _spy_resolve
        try:
            error = world_scene_entry.SceneEntryRefused(
                world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
            )
            notice.refusal_console_line(error, _character(), _row())
            notice.refusal_report(error, _character(), _row())
        finally:
            io.open = real_open
            world_scene_entry.resolve_entry = real_resolve
        self.assertEqual(opened, [])
        self.assertEqual(calls, [])

    def test_the_composer_mutates_neither_of_its_arguments(self):
        character = _character()
        row = _row()
        error = world_scene_entry.SceneEntryRefused(
            world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
        )
        before = (repr(character), repr(row), str(error), error.reason)
        notice.refusal_console_line(error, character, row, reply_frames=0)
        self.assertEqual(
            before, (repr(character), repr(row), str(error), error.reason)
        )

    def test_composing_a_notice_does_not_change_what_resolve_entry_does(self):
        row = model.Position(
            scene_id=0xFFFE, scene_seq=0, x=0.0, y=0.0, z=0.0
        )
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as first:
            world_scene_entry.resolve_entry(row, emit=lambda _line: None)
        notice.refusal_console_line(first.exception, _character(), row)
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as second:
            world_scene_entry.resolve_entry(row, emit=lambda _line: None)
        self.assertEqual(first.exception.reason, second.exception.reason)
        self.assertEqual(str(first.exception), str(second.exception))

    def test_a_home_login_still_resolves_after_a_notice_was_composed(self):
        home = model.Position(scene_id=1, scene_seq=0, x=0.0, y=0.0, z=0.0)
        before = world_scene_entry.resolve_entry(home, emit=lambda _l: None)
        notice.refusal_console_line(
            world_scene_entry.SceneEntryRefused(
                world_scene_entry.REFUSED_SCENE_NOT_PINNED, "why"
            ),
            _character(),
            home,
        )
        after = world_scene_entry.resolve_entry(home, emit=lambda _l: None)
        self.assertEqual(before.position, after.position)
        self.assertEqual(before.destination.n_id, after.destination.n_id)


if __name__ == "__main__":
    unittest.main()
