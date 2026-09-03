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
        runtime = (ROOT / "src" / "pirateforce_foundation" / "runtime.py")
        text = runtime.read_text(encoding="utf-8")
        self.assertIn(
            'print(f"WORLD_SCENE_ENTRY_REFUSED {exc}")', text
        )
        self.assertIn(notice.CONSOLE_TOKEN, text)

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
