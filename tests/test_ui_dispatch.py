"""ui_dispatch: the one seam that lets a LANE-UI module answer a frame.

COO route (b), pf_bridge/notes_to_chief/20260908_0142_COO-ROUND-0142-
DECISIONS-*.md item 3, answering this lane's letter 20260908_0031.  The
approval is narrow and this file is written against it: ONE module with a
caller in the same commit, at most three lines in runtime.py, and DAY-ONE
BEHAVIOUR IDENTICAL TO TODAY -- `handled=False` on every frame, which in
this module's shape is "the registry is empty, so every one of the eight
vitals gets `[]` back".

The regression proof that nothing moved for a player is not in this file
but in tests/test_lane_ui_friend_mail_party_trade_dispatch_wiring.py,
which drives all eight classes through the REAL dispatcher and asserts
`actions == []`; it is unchanged by this PR and still passes.  What this
file adds is the other half: that the empty answer is a decision this
module makes and not an accident of a dead call site (the end-to-end test
at the bottom registers an answerer and watches a frame come back out of
`state.dispatch()`), and that every way an answerer can be wrong ends in
`[]` rather than on a client's socket.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import ui_dispatch  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS,
    PARTY_INVITE_VITAL_ID,
    make_state_class,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RUNTIME_PY = ROOT / "src" / "pirateforce_foundation" / "runtime.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """Same outer envelope the sibling dispatch-wiring test builds."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class _RegistryIsolation(unittest.TestCase):
    """Every test in this file leaves the shipped registry EMPTY.

    Not a convenience: `_ANSWERERS` is process-global, the production
    default is empty, and a test that leaked one entry would make the
    "ships inert" proofs below pass for the wrong reason in whatever file
    pytest happens to run next.
    """

    def setUp(self):
        self.addCleanup(ui_dispatch.clear_answerers)
        ui_dispatch.clear_answerers()

    def allow(self, fn):
        """Open the production gate for `fn`'s module, then close it.

        Drives the REAL `lane_hooks.module_production_allowed()` by giving
        it the snapshot entry `_discover()` would have made for a lane
        module, rather than monkeypatching the gate away -- a mocked gate
        would prove nothing about the function the call site actually asks.
        """
        qualified = f"{lane_hooks.__name__}.{fn.__module__}"
        lane_hooks._PRODUCTION_ALLOWED[qualified] = True
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.pop, qualified, None,
        )


class ShipsInertTests(_RegistryIsolation):
    def test_the_shipped_registry_is_empty(self):
        # The whole day-one claim in one line: nothing is registered, so
        # nothing can answer. Ships as a module-level {} and only a lane
        # module landing later changes it.
        ui_dispatch.clear_answerers()
        for vital_id in sorted(ui_dispatch.ANSWERABLE_VITAL_IDS):
            with self.subTest(vital_id=f"{vital_id:#06x}"):
                self.assertIsNone(ui_dispatch.registered_answerer(vital_id))

    def test_every_one_of_the_eight_ids_answers_with_an_empty_list(self):
        for vital_id in sorted(ui_dispatch.ANSWERABLE_VITAL_IDS):
            with self.subTest(vital_id=f"{vital_id:#06x}"):
                answer = ui_dispatch.answer(object(), vital_id, b"\x00\x01")
                self.assertEqual(answer, [])
                # A tuple would compare unequal to [] at the call site's
                # own assertion in the sibling wiring test, and the
                # dispatcher's callers extend this value.
                self.assertIsInstance(answer, list)

    def test_an_id_this_seam_does_not_route_also_answers_nothing(self):
        # runtime.py never calls answer() for anything outside its own
        # guard, but a future call site that did must not find a
        # different shape here.
        self.assertEqual(ui_dispatch.answer(object(), 0x0000, b""), [])

    def test_the_eight_ids_are_exactly_the_ones_runtime_routes_here(self):
        # The drift this pins: an id added to runtime.py's guard but not
        # here would reach answer() and silently never be answerable, and
        # an id here but not there would accept a registration nothing
        # ever calls. Both are dead code that reads as wired.
        self.assertEqual(
            set(ui_dispatch.ANSWERABLE_VITAL_IDS),
            set(_FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS),
        )
        self.assertEqual(len(ui_dispatch.ANSWERABLE_VITAL_IDS), 8)


class RegistrationTests(_RegistryIsolation):
    def test_a_routed_id_registers_and_is_readable_back(self):
        def answerer(session=None, vital_id=None, payload=None):
            return []

        self.assertTrue(
            ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        )
        module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertIs(fn, answerer)
        self.assertEqual(module_name, answerer.__module__)

    def test_an_unrouted_id_is_refused_by_name_and_registers_nothing(self):
        def answerer(session=None, vital_id=None, payload=None):
            return []

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(ui_dispatch.register_answerer(0x1234, answerer))
        self.assertIn("UI_DISPATCH_REGISTER_REFUSED", stderr.getvalue())
        self.assertIn("not_routed_here", stderr.getvalue())
        self.assertIsNone(ui_dispatch.registered_answerer(0x1234))

    def test_a_non_callable_is_refused(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(
                ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, "nope")
            )
        self.assertIn("not_callable", stderr.getvalue())
        self.assertIsNone(
            ui_dispatch.registered_answerer(PARTY_INVITE_VITAL_ID)
        )

    def test_a_second_registration_loses_and_the_first_keeps_the_id(self):
        # The winner of a double registration must not depend on
        # pkgutil.iter_modules filename order: the frame-answering path is
        # not a place for a silent last-writer-wins.
        def first(session=None, vital_id=None, payload=None):
            return []

        def second(session=None, vital_id=None, payload=None):
            return []

        self.assertTrue(
            ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, first)
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(
                ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, second)
            )
        self.assertIn("already_taken", stderr.getvalue())
        _module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertIs(fn, first)


class GateAndFailClosedTests(_RegistryIsolation):
    ACTION = ("UI_TEST_ACTION", 7, b"\x01\x02", 0.0)

    def _register_returning(self, value):
        def answerer(session=None, vital_id=None, payload=None):
            return value

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        return answerer

    def test_an_answerer_whose_module_is_not_production_allowed_is_gated(self):
        # The default for a test module: no _discover() snapshot entry, so
        # the real gate answers False and the answer never runs.
        answerer = self._register_returning([self.ACTION])
        self.assertFalse(
            lane_hooks.module_production_allowed(answerer.__module__)
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())

    def test_an_allowed_answerer_actually_answers(self):
        answerer = self._register_returning([self.ACTION])
        self.allow(answerer)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = ui_dispatch.answer(
                object(), PARTY_INVITE_VITAL_ID, b"\x09"
            )
        self.assertEqual(actions, [self.ACTION])
        self.assertIn("UI_DISPATCH_ANSWERED", stderr.getvalue())

    def test_the_answerer_receives_the_session_and_the_verbatim_payload(self):
        seen = []

        def answerer(session=None, vital_id=None, payload=None):
            seen.append((session, vital_id, payload))
            return []

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        session = object()
        with contextlib.redirect_stderr(io.StringIO()):
            ui_dispatch.answer(session, PARTY_INVITE_VITAL_ID, b"\xAA\xBB")
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0][0], session)
        self.assertEqual(seen[0][1], PARTY_INVITE_VITAL_ID)
        self.assertEqual(seen[0][2], b"\xAA\xBB")

    def test_an_answerer_that_raises_is_caught_named_and_answers_nothing(self):
        def answerer(session=None, vital_id=None, payload=None):
            raise ValueError("lane bug")

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        console = stderr.getvalue()
        self.assertIn("UI_DISPATCH_ANSWER_ERR", console)
        self.assertIn("lane bug", console)

    def test_base_exception_is_not_swallowed(self):
        # Same deliberate gap lane_hooks documents: a deliberate
        # interpreter shutdown must not die inside a diagnostic.
        def answerer(session=None, vital_id=None, payload=None):
            raise KeyboardInterrupt

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        with self.assertRaises(KeyboardInterrupt):
            with contextlib.redirect_stderr(io.StringIO()):
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b"")

    def test_none_is_the_ordinary_no_answer_and_is_not_an_error(self):
        answerer = self._register_returning(None)
        self.allow(answerer)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertNotIn("REFUSED", stderr.getvalue())

    def test_every_malformed_shape_is_refused_whole(self):
        # One bad action refuses the WHOLE batch: half a lane's answer
        # reaching a client is worse than none of it.
        bad_values = [
            ("a bare tuple, not a list of them", self.ACTION),
            ("a string", "frame"),
            ("bytes", b"\x01\x02"),
            ("an int", 5),
            ("a dict", {"frame": b""}),
            ("a generator", (a for a in ())),
            ("wrong arity 3", [("L", 1, b"\x01")]),
            ("wrong arity 5", [("L", 1, b"\x01", 0.0, 0)]),
            ("empty label", [("", 1, b"\x01", 0.0)]),
            ("label not str", [(1, 1, b"\x01", 0.0)]),
            ("pc is a bool", [("L", True, b"\x01", 0.0)]),
            ("pc is a str", [("L", "1", b"\x01", 0.0)]),
            ("frame is a str", [("L", 1, "\x01", 0.0)]),
            ("frame is a bytearray", [("L", 1, bytearray(b"\x01"), 0.0)]),
            ("frame is None", [("L", 1, None, 0.0)]),
            ("delay is negative", [("L", 1, b"\x01", -0.5)]),
            ("delay is a bool", [("L", 1, b"\x01", True)]),
            ("delay is a str", [("L", 1, b"\x01", "0")]),
            ("delay is nan", [("L", 1, b"\x01", float("nan"))]),
            ("one good one bad", [self.ACTION, ("L", 1, "bad", 0.0)]),
        ]
        for label, value in bad_values:
            with self.subTest(shape=label):
                ui_dispatch.clear_answerers()
                answerer = self._register_returning(value)
                self.allow(answerer)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(
                        ui_dispatch.answer(
                            object(), PARTY_INVITE_VITAL_ID, b""
                        ),
                        [],
                    )
                self.assertIn(
                    "UI_DISPATCH_ANSWER_REFUSED", stderr.getvalue()
                )

    def test_an_empty_answer_is_accepted_not_refused(self):
        answerer = self._register_returning([])
        self.allow(answerer)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertNotIn("REFUSED", stderr.getvalue())

    def test_the_returned_list_is_this_modules_own_object(self):
        # The dispatcher's callers append to what comes back; reaching
        # into a lane module's own list from there is a bug this shape
        # makes impossible.
        owned = [self.ACTION]
        answerer = self._register_returning(owned)
        self.allow(answerer)
        with contextlib.redirect_stderr(io.StringIO()):
            actions = ui_dispatch.answer(
                object(), PARTY_INVITE_VITAL_ID, b""
            )
        self.assertIsNot(actions, owned)
        actions.append(("EXTRA", 1, b"", 0.0))
        self.assertEqual(len(owned), 1)


class SeamIsRealTests(unittest.TestCase):
    """The three lines in runtime.py, pinned as a call and not as prose."""

    def test_runtime_calls_ui_dispatch_answer_exactly_once(self):
        tree = ast.parse(RUNTIME_PY.read_text(encoding="utf-8"))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "answer"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ui_dispatch"
        ]
        self.assertEqual(len(calls), 1)

    def test_the_call_is_the_return_of_the_eight_vital_branch(self):
        # Pins WHERE, not just THAT: a second call site for these frames,
        # or this one drifting onto another branch, is a change chief
        # reviews, not one a green suite hides.
        source = RUNTIME_PY.read_text(encoding="utf-8").split("\n")
        anchor = source.index(
            "            if nested_id in _FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS:"
        )
        body = "\n".join(source[anchor:anchor + 70])
        self.assertIn("return ui_dispatch.answer(", body)
        self.assertIn("self, nested_id, bytes(parsed.nested_payload))", body)

    def test_the_seam_is_three_added_lines_and_no_more(self):
        # COO route (b) allows "at most three lines in runtime.py". This
        # counts them where they are, so the budget is a measurement and
        # not a sentence in a PR body.
        source = RUNTIME_PY.read_text(encoding="utf-8").split("\n")
        naming = [n for n, line in enumerate(source) if "ui_dispatch" in line]
        # Two lines name the module: the import, and the `return` that
        # opens the call. The call's closing argument line is the third
        # added line and names nothing, so it is counted here by position
        # rather than by grep -- three added lines in total, which is the
        # whole budget route (b) grants.
        self.assertEqual(len(naming), 2)
        self.assertEqual(source[naming[0]], "from . import ui_dispatch")
        self.assertEqual(
            source[naming[1]].strip(), "return ui_dispatch.answer("
        )
        self.assertEqual(
            source[naming[1] + 1].strip(),
            "self, nested_id, bytes(parsed.nested_payload))",
        )


class EndToEndThroughTheRealDispatcherTests(_RegistryIsolation):
    """A frame the player sent comes back answered, through state.dispatch.

    This is the property the whole round exists for, and the reason the
    empty-registry proofs above are not circular: with an answerer
    registered, the SAME call site that returns `[]` today returns the
    lane's action, so `[]` today is a decision and not a dead branch.
    """

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _login_and_start(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def test_with_no_answerer_the_branch_still_answers_nothing(self):
        state = self._login_and_start("uidisp-inert")
        rx_before = state.rx_frames
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, PARTY_INVITE_VITAL_ID, b"\x00\x01")
            ))
        self.assertEqual(actions, [])
        self.assertEqual(state.rx_frames, rx_before + 1)

    def test_with_an_answerer_the_action_reaches_the_dispatchers_caller(self):
        seen = []

        def answerer(session=None, vital_id=None, payload=None):
            seen.append(payload)
            return [("UI_TEST_PARTY_INVITE_REPLY", 3, b"\x11\x22", 0.0)]

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        state = self._login_and_start("uidisp-live")
        rx_before = state.rx_frames
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, PARTY_INVITE_VITAL_ID, b"\x00\x01")
            ))
        self.assertEqual(
            actions, [("UI_TEST_PARTY_INVITE_REPLY", 3, b"\x11\x22", 0.0)],
        )
        # The report-only hook above the call still ran, and the frame is
        # still counted: this seam replaced a `return []`, not the branch.
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(seen, [b"\x00\x01"])

    def test_a_broken_answerer_cannot_take_the_dispatch_down(self):
        def answerer(session=None, vital_id=None, payload=None):
            raise RuntimeError("lane module bug on the production path")

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        state = self._login_and_start("uidisp-broken")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, PARTY_INVITE_VITAL_ID, b"\x00\x01")
            ))
        self.assertEqual(actions, [])
        self.assertIn("UI_DISPATCH_ANSWER_ERR", stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
