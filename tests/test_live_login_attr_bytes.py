"""The live login-bytes read point: what it answers, and why it cannot
answer more without inventing a value.

CORE-REQUEST-GM's `LOGIN_BYTES_READ_POINT` (COO-DECISION 20260904_0216).
Same discipline as `tests/test_live_named_attr_values.py`: the tests that
matter here are the ones that go RED when a row this module cannot back
with the login composer's own source starts being invented, not the ones
that prove a happy path.
"""
from __future__ import annotations

import ast
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import live_login_attr_bytes as live  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402
from pirateforce_foundation.gm import attr_wire  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


class _Character:
    def __init__(self, scene_seq):
        self.position = Position(1, scene_seq, 0.0, 0.0, 0.0, 0.0)


class _StubStore:
    """Only the two read-only calls the source uses.

    Per-id rows, same reason `test_live_named_attr_values.py`'s stub gives
    for itself: a stub that ignores the id under test cannot test threading
    of the key.  ``columns`` feeds ``read_typed_attributes`` (which
    ``login_speed.resolve_for_character`` reads through when the /speed
    deferral is open; today it is shut by default, so this stub's columns
    do not change x=7's answer -- see the module-level note below).
    """

    def __init__(self, *, scene_seq=0, columns=None, raises=None,
                 character_raises=None):
        self._scene_seq = scene_seq
        self._columns = dict(columns or {})
        self._raises = raises
        self._character_raises = (
            character_raises if character_raises is not None else raises
        )

    def read_typed_attributes(self, character_id):
        if self._raises is not None:
            raise self._raises
        return dict(self._columns)

    def get_character(self, character_id):
        if self._character_raises is not None:
            raise self._character_raises
        return _Character(self._scene_seq)


# `gm.speed_wire.SPEED_LOGIN_READ_LANDED` defaults to `False` -- the /speed
# deferral gate is SHUT in every test process that does not explicitly open
# it, so `login_speed.resolve_for_character` always returns the fallback
# constant here regardless of what a stub's columns hold.  That is not a
# limit of this test file: it is the correct, current answer for x=7, and
# pinning it (rather than mocking it away) is what would catch this module
# reading the wrong fallback constant.
_EXPECTED_SPEED = player_wire.PLAYER_LOGIN_MOVEMENT_SPEED


class WhatTheSourceCanAnswerTests(unittest.TestCase):
    def test_it_answers_exactly_x7_and_x10_on_a_healthy_store(self):
        store = _StubStore(scene_seq=3)
        values = live.values_for(store, 7)
        self.assertEqual(values, {7: _EXPECTED_SPEED, 10: 3})

    def test_it_never_answers_a_row_outside_x7_x10(self):
        # THE HEART OF IT, same shape as the named-values sibling's
        # "nothing is invented" tests: the login composer has no source at
        # all for the other 26 unnamed rows, and this module must not
        # paper over that with a guess.
        store = _StubStore(scene_seq=9)
        values = live.values_for(store, 7)
        self.assertEqual(set(values), {7, 10})

    def test_an_unknown_character_still_answers_x7_only(self):
        # x=7 needs no character row at all while the /speed deferral is
        # shut (the default -- see the module-level note above): only
        # x=10's read fails for an unknown character, and it fails
        # independently, never taking x=7 down with it.
        store = _StubStore(character_raises=KeyError(7))
        self.assertEqual(live.values_for(store, 7), {7: _EXPECTED_SPEED})

    def test_a_broken_store_still_answers_x7_only(self):
        # A driver error on the character read must not unwind into the
        # listener thread, and must not cost x=7 either.
        store = _StubStore(character_raises=OSError("disk"))
        self.assertEqual(live.values_for(store, 7), {7: _EXPECTED_SPEED})

    def test_a_read_that_fails_says_so_instead_of_answering_silently(self):
        live.reset_console_announcements()
        self.addCleanup(live.reset_console_announcements)
        store = _StubStore(character_raises=OSError("no such column"))
        stream = io.StringIO()
        self.assertEqual(
            live.values_for(store, 7, stream=stream), {7: _EXPECTED_SPEED},
        )
        said = stream.getvalue()
        self.assertIn(live.READ_REFUSED_CONSOLE_TOKEN, said)
        self.assertIn("scene_seq", said)
        self.assertTrue(all(32 <= ord(c) <= 126 or c == "\n" for c in said))


class TheReadPointOnTheRealPackageTests(unittest.TestCase):
    """`lane_hooks.current_login_attr_bytes` itself."""

    def setUp(self):
        self.addCleanup(
            setattr, lane_hooks, "_LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED",
            lane_hooks._LOGIN_ATTR_BYTES_NO_SOURCE_ANNOUNCED,
        )
        self.addCleanup(
            lane_hooks.register_login_attr_bytes_source,
            lane_hooks._LOGIN_ATTR_BYTES_SOURCE,
        )

    def test_the_read_point_exists_under_the_name_attr_wire_resolves(self):
        self.assertTrue(
            hasattr(lane_hooks, attr_wire.LOGIN_BYTES_READ_POINT)
        )
        self.assertTrue(
            callable(getattr(lane_hooks, attr_wire.LOGIN_BYTES_READ_POINT))
        )

    def test_with_no_source_installed_it_answers_nothing_and_does_not_raise(self):
        lane_hooks.register_login_attr_bytes_source(None)
        self.assertEqual(lane_hooks.current_login_attr_bytes(7), {})

    def test_a_source_that_raises_is_swallowed_named_on_stderr(self):
        lane_hooks.register_login_attr_bytes_source(
            lambda cid: (_ for _ in ()).throw(RuntimeError("no"))
        )
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_login_attr_bytes(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("LANE_HOOK", said)
        self.assertIn("current_login_attr_bytes", said)

    def test_a_source_returning_a_non_dict_answers_nothing(self):
        lane_hooks.register_login_attr_bytes_source(lambda cid: [1, 2])
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            answer = lane_hooks.current_login_attr_bytes(7)
            said = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertEqual(answer, {})
        self.assertIn("not dict", said)

    def test_string_keys_are_coerced_and_unusable_keys_dropped(self):
        lane_hooks.register_login_attr_bytes_source(
            lambda cid: {"7": 400.0, 10: 3, "not-an-int": 1}
        )
        self.assertEqual(
            lane_hooks.current_login_attr_bytes(7), {7: 400.0, 10: 3},
        )

    def test_the_announcement_re_arms_when_the_source_is_cleared(self):
        lane_hooks.register_login_attr_bytes_source(lambda cid: {7: 400.0})
        lane_hooks.register_login_attr_bytes_source(None)
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            lane_hooks.current_login_attr_bytes(7)
            first = sys.stderr.getvalue()
            lane_hooks.current_login_attr_bytes(7)
            second = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertIn("NO_SOURCE_REGISTERED", first)
        self.assertEqual(second.count("NO_SOURCE_REGISTERED"), 1)

    def test_a_non_callable_source_is_refused_at_registration(self):
        with self.assertRaises(TypeError):
            lane_hooks.register_login_attr_bytes_source(object())

    def test_registering_prints_a_token_a_wired_grep_can_find(self):
        captured, sys.stderr = sys.stderr, io.StringIO()
        try:
            lane_hooks.register_login_attr_bytes_source(lambda cid: {})
            first = sys.stderr.getvalue()
            lane_hooks.register_login_attr_bytes_source(lambda cid: {})
            second = sys.stderr.getvalue()
        finally:
            sys.stderr = captured
        self.assertIn("LANE_HOOK_LOGIN_ATTR_SOURCE REGISTERED", first)
        self.assertNotIn("REPLACED_AN_EARLIER_SOURCE", first)
        self.assertIn("REPLACED_AN_EARLIER_SOURCE", second)

    def test_the_store_backed_source_reaches_the_point_end_to_end(self):
        store = _StubStore(scene_seq=5)
        lane_hooks.register_login_attr_bytes_source(
            live.source_for_store(store)
        )
        values = lane_hooks.current_login_attr_bytes(7)
        self.assertEqual(values, {7: _EXPECTED_SPEED, 10: 5})


class WhatAttrWireDoesWithItTests(unittest.TestCase):
    """The consumer's answer through the REAL read point, not a fake."""

    def setUp(self):
        self.addCleanup(
            lane_hooks.register_login_attr_bytes_source,
            lane_hooks._LOGIN_ATTR_BYTES_SOURCE,
        )

    def test_the_refusal_now_names_26_rows_not_28(self):
        # THE WHOLE VALUE OF THIS ROUND IN ONE ASSERTION, same shape as the
        # named-values sibling's own headline test: x=7 and x=10 leave the
        # missing list, the other 26 unnamed rows stay in it -- named, not
        # guessed.
        store = _StubStore(scene_seq=0)
        lane_hooks.register_login_attr_bytes_source(
            live.source_for_store(store)
        )
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.live_login_bytes(7, hooks=lane_hooks)
        message = str(caught.exception)
        self.assertIn("missing_login_rows", message)
        self.assertNotIn("no_login_byte_read_point", message)
        self.assertNotIn("no_login_byte_source_registered", message)
        missing = sorted(
            set(attr_wire.unnamed_field_x()) - {7, 10}
        )
        for x in missing:
            self.assertIn(str(x), message)
        # Neither answered row appears in the ABSENT half of the message.
        self.assertNotIn("absent=7,", message)


class TheBootWiringTests(unittest.TestCase):
    def test_app_installs_the_source_unconditionally_in_the_boot_body(self):
        # Same AST-level proof as `test_live_named_attr_values.py`'s sibling
        # test, for the same reasons (pf-adversary D3/N3 on that file): a
        # substring-in-text or bare-ast.walk check would stay green for a
        # commented-out or dead-code call.
        tree = ast.parse(
            (ROOT / "src" / "pirateforce_foundation" / "app.py").read_text(
                encoding="utf-8"
            )
        )

        def installs_in(body):
            found = []
            for statement in body:
                if not isinstance(statement, ast.Expr):
                    continue
                call = statement.value
                if not isinstance(call, ast.Call):
                    continue
                func = call.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "register_login_attr_bytes_source"
                ):
                    found.append(call)
            return found

        unconditional = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                unconditional.extend(installs_in(node.body))
        unconditional.extend(installs_in(tree.body))

        every_call = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "register_login_attr_bytes_source"
        ]
        self.assertEqual(
            len(every_call), 1,
            "app.py must name the install exactly once (found %d)"
            % len(every_call),
        )
        self.assertEqual(
            len(unconditional), 1,
            "the install must be a plain statement of a module-level "
            "function's body -- not nested, not under an `if`, not in a "
            "helper nobody calls (found %d such, %d anywhere)"
            % (len(unconditional), len(every_call)),
        )

        argument = unconditional[0].args[0] if unconditional[0].args else None
        self.assertIsInstance(
            argument, ast.Call,
            "the installed source must be built by a call, not a name or a "
            "literal",
        )
        self.assertEqual(argument.func.attr, "source_for_store")
        self.assertEqual(
            [a.id for a in argument.args if isinstance(a, ast.Name)],
            ["store"],
            "the source must be bound to the store this boot opened",
        )


class AgainstARealMigratedStoreTests(unittest.TestCase):
    """The one test that is not duck-typed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = SQLiteStore(
            str(Path(self._tmp.name) / "pf.sqlite3"), MIGRATIONS,
        )
        self.store.migrate()

    def _born(self, tag, identity_base, *, scene_seq=0):
        def build_wire(selector):
            return b"wire", b"avatar", 0x20000001 + identity_base + selector, 0

        account_id = self.store.ensure_account(tag)
        return self.store.create_character(
            account_id, "Born%s" % tag, "born%s" % tag,
            "fingerprint-%s" % tag, build_wire,
            Position(3, scene_seq, 1.0, 2.0, 3.0, heading=0.0),
        )

    def test_a_newborn_answers_x7_and_x10(self):
        character = self._born("A", 0x1000, scene_seq=42)
        values = live.values_for(self.store, character.id)
        self.assertEqual(values, {7: _EXPECTED_SPEED, 10: 42})

    def test_an_id_that_is_not_a_character_answers_nothing_for_x10(self):
        # x=7 needs no character row at all while the /speed deferral is
        # shut (the default): the fallback constant does not touch the
        # store, so an unknown id still answers x=7.
        values = live.values_for(self.store, 999999)
        self.assertEqual(values, {7: _EXPECTED_SPEED})

    def test_two_characters_do_not_read_each_others_rows(self):
        first = self._born("D", 0x4000, scene_seq=7)
        second = self._born("E", 0x5000, scene_seq=99)
        source = live.source_for_store(self.store)
        self.assertEqual(source(first.id)[10], 7)
        self.assertEqual(source(second.id)[10], 99)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
