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
from pirateforce_foundation.logout_hypothesis import (  # noqa: E402
    make_return_select_server_response,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS,
    PARTY_INVITE_VITAL_ID,
    make_state_class,
)

# ui_dispatch spells its eight ids as literals rather than importing them
# (see its own comment: two of the imported names are on
# tests/test_npc_interaction_wire.py's symbol guard list, and the fix for a
# red run there is to change the symbol, not to buy an exemption). The
# equality test below is what makes that safe, so it is the load-bearing
# test in this file, not a formality.
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
        # SAVE AND RESTORE, NOT CLEAR (pf-adversary D9). The draft called
        # clear_answerers() in setUp and again as cleanup, which empties a
        # PROCESS-GLOBAL dict: measured, a lane test whose module registers
        # an answerer at import passed alone and failed when this file ran
        # first in the same interpreter. Harmless only while the registry
        # ships empty -- which is the round this file was written, and not
        # the round after.
        saved = dict(ui_dispatch._ANSWERERS)

        def _restore():
            ui_dispatch._ANSWERERS.clear()
            ui_dispatch._ANSWERERS.update(saved)

        self.addCleanup(_restore)
        ui_dispatch._ANSWERERS.clear()

    def allow(self, fn=None):
        """Open the production gate for THIS test module, then close it.

        The gate keys on the module that CALLED register_answerer (see
        ui_dispatch._registering_module_name), which for this file is this
        file. `fn` is accepted and ignored so the call sites read the way
        they did before the D5 fix.

        Drives the REAL `lane_hooks.module_production_allowed()` by giving
        it the snapshot entry `_discover()` would have made for a lane
        module, rather than monkeypatching the gate away -- a mocked gate
        would prove nothing about the function the call site actually asks.
        """
        qualified = f"{lane_hooks.__name__}.{__name__}"
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

    def test_a_live_incumbent_keeps_the_id_against_a_second_registration(self):
        # The winner of a double registration must not depend on
        # pkgutil.iter_modules filename order: the frame-answering path is
        # not a place for a silent last-writer-wins.
        def first(session=None, vital_id=None, payload=None):
            return []

        def second(session=None, vital_id=None, payload=None):
            return []

        self.allow()
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

    def test_a_gated_incumbent_yields_the_id_instead_of_squatting_it(self):
        # pf-adversary D6. _discover() withdraws a not-production-allowed
        # module's HOOKS and cannot reach this registry, and imports run in
        # filename order -- so without this, a lane_ui_aaa_*.py with the
        # flag OFF would hold a vital against a lane_ui_zzz_*.py with the
        # flag ON, and the vital would answer [] forever.
        def gated(session=None, vital_id=None, payload=None):
            return []

        def live(session=None, vital_id=None, payload=None):
            return []

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(
                ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, gated)
            )
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertFalse(lane_hooks.module_production_allowed(module_name))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertTrue(
                ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, live)
            )
        self.assertIn("UI_DISPATCH_REGISTER_REPLACED", stderr.getvalue())
        _module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertIs(fn, live)


class RoundThreeFindingsTests(_RegistryIsolation):
    """The four defects pf-adversary round 3 measured, as tests.

    These build REAL modules under ``pirateforce_foundation.lane_hooks.``
    rather than faking a name, because every finding here is about which
    module a frame on the stack belongs to -- a fake would prove nothing
    about the thing the gate actually reads.
    """

    def _lane_module(self, stem, source, allowed):
        import types

        qualified = f"{lane_hooks.__name__}.{stem}"
        module = types.ModuleType(qualified)
        module.__file__ = f"<{stem}>"
        module.production_allowed = allowed
        sys.modules[qualified] = module
        self.addCleanup(sys.modules.pop, qualified, None)
        if allowed:
            lane_hooks._PRODUCTION_ALLOWED[qualified] = True
            self.addCleanup(
                lane_hooks._PRODUCTION_ALLOWED.pop, qualified, None,
            )
        exec(compile(source, f"<{stem}>", "exec"), module.__dict__)
        return module

    # ---- D1 -----------------------------------------------------------

    HELPER_SOURCE = (
        "from pirateforce_foundation import ui_dispatch\n"
        "def wire(vital_id, fn):\n"
        "    return ui_dispatch.register_answerer(vital_id, fn)\n"
    )

    def test_an_allowed_helper_does_not_launder_a_gated_lanes_decision(self):
        """pf-adversary round 3, D1 -- the measured attack, verbatim.

        A ``production_allowed = True`` helper exposing a one-line
        ``wire()``, called by a ``production_allowed = False`` lane, used
        to register successfully, print the helper's innocent name in the
        token, and put the gated lane's frame on the wire.  Nothing is
        forged here: this is how shared registration code is factored.
        """
        helper = self._lane_module(
            "lane_ui_zz_test_helpers", self.HELPER_SOURCE, allowed=True
        )
        experimental = self._lane_module(
            "lane_ui_zz_test_experimental",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_EXPERIMENTAL_UNREVIEWED_REPLY',"
            " b'\\x01', b'\\xde\\xad', 0.0)]\n",
            allowed=False,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(
                helper.wire(PARTY_INVITE_VITAL_ID, experimental.answerer)
            )
        # The helper IS the registrar, and the helper IS allowed --
        # which is exactly why the registrar alone was not enough.
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertEqual(module_name, helper.__name__)
        self.assertTrue(lane_hooks.module_production_allowed(module_name))
        self.assertIn(
            experimental.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        console = stderr.getvalue()
        self.assertIn("UI_DISPATCH_GATED", console)
        self.assertIn(experimental.__name__, console)

    def test_the_same_helper_still_works_for_an_allowed_lane(self):
        """The D1 fix must not close the gate on the legitimate case."""
        helper = self._lane_module(
            "lane_ui_zz_test_helpers2", self.HELPER_SOURCE, allowed=True
        )
        caller = self._lane_module(
            "lane_ui_zz_test_caller",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_ALLOWED_REPLY', b'\\x01',"
            " b'\\xde\\xad', 0.0)]\n",
            allowed=True,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(
                helper.wire(PARTY_INVITE_VITAL_ID, caller.answerer)
            )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""),
                [("UI_ALLOWED_REPLY", b"\x01", b"\xde\xad", 0.0)],
            )

    def test_a_forged_fn_dunder_module_cannot_replace_the_registrar_gate(
        self,
    ):
        """The D1 fix must not reopen round 2's R2/D5.

        ``gating`` includes ``fn.__module__``, a plain mutable attribute.
        It may only ADD a module the gate must clear -- never stand in
        for the registrar.
        """
        allowed = self._lane_module(
            "lane_ui_zz_test_allowed_target", "", allowed=True
        )

        def answerer(session=None, vital_id=None, payload=None):
            return [("UI_FORGED_REPLY", b"\x01", b"\xee", 0.0)]

        answerer.__module__ = allowed.__name__
        with contextlib.redirect_stderr(io.StringIO()):
            ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        # Registrar is this test module, which has no snapshot entry.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())

    def test_a_gated_lane_calling_the_helper_itself_is_caught_by_the_walk(
        self,
    ):
        """pf-adversary round 4, D-C.

        The D1 test above calls ``helper.wire(...)`` from THIS test
        method, so the gated lane never has a frame on the registration
        stack and the only thing catching it is ``fn.__module__`` -- the
        attribute the fix's own docstring says is not trusted alone.
        Deleting the whole stack walk left that test green (mutant M1).

        Here the gated lane calls the helper itself, and the answerer is
        wrapped by the helper so ``fn.__module__`` names the ALLOWED
        module.  Only the stack walk can catch this one.
        """
        helper = self._lane_module(
            "lane_ui_zz_test_wrapping_helper",
            "from pirateforce_foundation import ui_dispatch\n"
            "def wire(vital_id, fn):\n"
            "    def logged(session=None, vital_id=None, payload=None):\n"
            "        return fn(session=session, vital_id=vital_id,"
            " payload=payload)\n"
            "    return ui_dispatch.register_answerer(vital_id, logged)\n",
            allowed=True,
        )
        gated = self._lane_module(
            "lane_ui_zz_test_gated_caller",
            "from pirateforce_foundation.lane_hooks import"
            " lane_ui_zz_test_wrapping_helper as helper\n"
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_UNREVIEWED_REPLY', b'\\x03',"
            " b'\\x11\\x22', 0.0)]\n"
            "def install(vital_id):\n"
            "    return helper.wire(vital_id, answerer)\n",
            allowed=False,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(gated.install(PARTY_INVITE_VITAL_ID))
        # fn.__module__ names the ALLOWED helper -- the attribute half of
        # the gate cannot see the gated lane at all.
        _module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertEqual(fn.__module__, helper.__name__)
        self.assertIn(
            gated.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())
        self.assertIn(gated.__name__, stderr.getvalue())

    def test_a_helper_in_a_non_lane_file_is_not_treated_as_a_lane(self):
        """pf-adversary round 4, D-E.

        ``_discover()`` imports only ``lane_*`` stems, so a helper
        factored into ``lane_hooks/ui_answer_impl.py`` can never have a
        production flag read from it -- and the prefix-only test put it
        in the gate anyway, closing a correct allowed lane forever with a
        reason naming a switch nobody had been asked about.
        """
        impl = self._lane_module(
            "ui_answer_impl_zz_test",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_GOOD_REPLY', b'\\x01', b'\\x02', 0.0)]\n",
            allowed=False,
        )
        good = self._lane_module(
            "lane_ui_zz_test_good",
            "from pirateforce_foundation import ui_dispatch\n"
            "from pirateforce_foundation.lane_hooks import"
            " ui_answer_impl_zz_test as impl\n"
            "def install(vital_id):\n"
            "    return ui_dispatch.register_answerer("
            "vital_id, impl.answerer)\n",
            allowed=True,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(good.install(PARTY_INVITE_VITAL_ID))
        self.assertNotIn(
            impl.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""),
                [("UI_GOOD_REPLY", b"\x01", b"\x02", 0.0)],
            )

    def test_an_incumbent_yields_when_any_module_in_its_gate_is_closed(self):
        """pf-adversary round 4, D-D.

        ``answer()`` gates on ``(module_name,) + gating``; the yield rule
        asked only about ``module_name``, so an incumbent whose registrar
        was allowed but whose gate carried a closed module squatted the
        vital against a correct lane and printed ``UI_DISPATCH_GATED`` on
        every frame -- the exact symptom the yield rule exists for.
        """
        impl = self._lane_module(
            "lane_ui_zz_test_closed_impl",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return []\n",
            allowed=False,
        )
        incumbent = self._lane_module(
            "lane_ui_aaa_test_incumbent",
            "from pirateforce_foundation import ui_dispatch\n"
            "from pirateforce_foundation.lane_hooks import"
            " lane_ui_zz_test_closed_impl as impl\n"
            "def install(vital_id):\n"
            "    return ui_dispatch.register_answerer("
            "vital_id, impl.answerer)\n",
            allowed=True,
        )
        challenger = self._lane_module(
            "lane_ui_zzz_test_correct",
            "from pirateforce_foundation import ui_dispatch\n"
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return []\n"
            "def install(vital_id):\n"
            "    return ui_dispatch.register_answerer(vital_id, answerer)\n",
            allowed=True,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(incumbent.install(PARTY_INVITE_VITAL_ID))
        self.assertIn(
            impl.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertTrue(challenger.install(PARTY_INVITE_VITAL_ID))
        self.assertIn("UI_DISPATCH_REGISTER_REPLACED", stderr.getvalue())
        _module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertIs(fn, challenger.answerer)

    # ---- D8 -----------------------------------------------------------

    def test_an_allowed_challenger_takes_the_id_from_a_gated_incumbent(self):
        """pf-adversary round 3, D8.

        The old test for this had BOTH parties gated, so the scenario its
        docstring described -- an allowed lane taking the slot from a
        gated one -- had never executed; what it proved was last-writer-
        wins among gated modules.  Two real modules, one flag each.
        """
        gated = self._lane_module(
            "lane_ui_zz_test_incumbent",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return []\n",
            allowed=False,
        )
        live = self._lane_module(
            "lane_ui_zz_test_challenger",
            "from pirateforce_foundation import ui_dispatch\n"
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return []\n"
            "def take(vital_id):\n"
            "    return ui_dispatch.register_answerer(vital_id, answerer)\n",
            allowed=True,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            ui_dispatch.register_answerer(
                PARTY_INVITE_VITAL_ID, gated.answerer
            )
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertFalse(lane_hooks.module_production_allowed(module_name))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertTrue(live.take(PARTY_INVITE_VITAL_ID))
        self.assertIn("UI_DISPATCH_REGISTER_REPLACED", stderr.getvalue())
        module_name, fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertIs(fn, live.answerer)
        self.assertTrue(lane_hooks.module_production_allowed(module_name))

    # ---- D3 / D4 -------------------------------------------------------

    def test_a_label_with_a_space_cannot_forge_an_attended_stage_signal(self):
        """pf-adversary round 3, D3.

        ``tools/wait_for_pf_stage.py`` matches by SUBSTRING within a line,
        and the v141 sender writes ``SENT label=<label> frame_bytes=...``.
        A label carrying a space could therefore append a second, false
        ``SENT label=...`` to a real line and turn an attended round's
        Port Royal signal green from a party-invite frame.
        """
        forged = "UI_PARTY_INVITE_ACK SENT label=RUNTIME_RES_ACK_FIRST_REQ"
        self.assertFalse(ui_dispatch._label_is_this_lanes_own(forged))
        self.assertFalse(
            ui_dispatch._actions_are_well_formed(
                [(forged, b"\x01", b"\x02", 0.0)]
            )
        )

    def test_a_label_the_cp874_console_cannot_print_is_refused(self):
        """pf-adversary round 3, D4.

        v141 prints ``[G>] {label}`` on a cp874 stdout AFTER sendall, in a
        try whose only handler is a finally: a non-ASCII label kills the
        connection thread with the bytes already on the wire.
        """
        for label in ("UI_PARTY_INVITE_ACK_\u2713", "UI_\u4f60\u597d"):
            with self.subTest(label=label):
                self.assertFalse(
                    ui_dispatch._label_is_this_lanes_own(label)
                )

    def test_the_grammar_is_positive_and_every_accepted_label_is_ascii(self):
        """The rule is what a label MAY contain, not a blacklist.

        A blacklist has to be extended every time a consumer keys on a new
        separator, by a round that has no reason to know the consumer
        exists.  This is the boundary the round-2 file asked for and could
        not answer.
        """
        for label in ("UI_A", "UI_PARTY_INVITE_ACK", "UI_" + "A" * 64):
            with self.subTest(ok=label):
                self.assertTrue(
                    ui_dispatch._label_is_this_lanes_own(label)
                )
                self.assertTrue(label.isascii())
        for label in (
            "ui_lower", "UI_", "UI_" + "A" * 65, "UI_A-B", "UI_A=B",
            "UI_A B", "UI_A.B", "UI_A\tB", "UI_A\nB", "UI_A/B",
            "UI_PARTY_TELEPORT_A", "XX_UI_A", "", "UI_A\x00",
            # pf-adversary round 4, D-G: wait_for_pf_stage.py matches by
            # substring inside a line and one of its needles is a bare
            # all-caps token, so an otherwise well-formed label made
            # `wait_for_pf_stage <log> connected` report REACHED.
            "UI_PARTY_GAME_CONNECTED_ACK",
            "UI_ACK_RUNTIME_RES_ACK_FIRST_REQ",
        ):
            with self.subTest(bad=label):
                self.assertFalse(
                    ui_dispatch._label_is_this_lanes_own(label)
                )

    # ---- D7 -------------------------------------------------------------

    def test_the_answerer_is_called_with_keywords_not_positionally(self):
        """pf-adversary round 3, D7 -- the one mutant that survived.

        Every test answerer declared the three parameters in the calling
        order, so nothing distinguished ``fn(session, vital_id, payload)``
        from ``fn(session=..., vital_id=..., payload=...)`` and a future
        lane author had no pinned contract.  A keyword-only answerer
        raises TypeError under the positional form.
        """
        seen = []

        def answerer(*, session, vital_id, payload):
            seen.append((vital_id, payload))
            return []

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b"\x09"),
                [],
            )
        self.assertEqual(seen, [(PARTY_INVITE_VITAL_ID, b"\x09")])


class DeferredRegistrationTests(RoundThreeFindingsTests):
    """pf-adversary round 4, D-A: the registrar is not always the author.

    Every test here builds REAL modules under
    ``pirateforce_foundation.lane_hooks.`` (inherited ``_lane_module``)
    for the same reason the round-3 class does: the finding is about
    which module the gate believes wrote the answerer, and a faked name
    would prove nothing about what the gate reads.
    """

    # A table plus a flush loop.  No forgery, no metaprogramming: this
    # is how two files share one registration point.
    FLUSHER_SOURCE = (
        "from pirateforce_foundation import ui_dispatch\n"
        "PENDING = []\n"
        "def flush():\n"
        "    out = []\n"
        "    for vital_id, fn in PENDING:\n"
        "        out.append(ui_dispatch.register_answerer(vital_id, fn))\n"
        "    return out\n"
    )
    CLOSED_SOURCE = (
        "def answerer(session=None, vital_id=None, payload=None):\n"
        "    return [('UI_DEFERRED_UNREVIEWED_REPLY',"
        " b'\\x01', b'\\xde\\xad', 0.0)]\n"
    )

    def _deferred(self, stem_suffix, forge_dunder_module):
        flusher = self._lane_module(
            "lane_ui_zz_test_flusher_%s" % stem_suffix,
            self.FLUSHER_SOURCE,
            allowed=True,
        )
        closed = self._lane_module(
            "lane_ui_zz_test_deferred_%s" % stem_suffix,
            self.CLOSED_SOURCE,
            allowed=False,
        )
        if forge_dunder_module:
            # One assignment -- round 2's D5, in the one place where it
            # was the last witness standing.
            closed.answerer.__module__ = flusher.__name__
        flusher.PENDING.append((PARTY_INVITE_VITAL_ID, closed.answerer))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(flusher.flush(), [True])
        return flusher, closed

    def test_a_deferred_flush_does_not_launder_a_closed_lane(self):
        """The measured D-A attack: no closed frame is ever on the stack.

        The closed lane appended and RETURNED; the allowed flusher makes
        the call.  The stack walk therefore sees only the flusher, and
        before this fix the gate held only allowed names.
        """
        flusher, closed = self._deferred("plain", forge_dunder_module=False)
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertEqual(module_name, flusher.__name__)
        self.assertTrue(lane_hooks.module_production_allowed(module_name))
        self.assertIn(
            closed.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        console = stderr.getvalue()
        self.assertIn("UI_DISPATCH_GATED", console)
        self.assertIn(closed.__name__, console)

    def test_a_forged_dunder_module_does_not_survive_a_deferred_flush(self):
        """D-A + D5 together -- the shape that actually shipped bytes.

        With the stack carrying no closed frame, ``fn.__module__`` was
        the only name left, and it is one assignment deep.  Identity is
        not, so the gate still closes and still NAMES the real author.
        """
        _flusher, closed = self._deferred("forged", forge_dunder_module=True)
        self.assertIn(
            closed.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn(closed.__name__, stderr.getvalue())

    def test_a_deferred_flush_from_an_allowed_lane_still_answers(self):
        """The fix must not close the gate on the legitimate table.

        Same two files, both production-allowed: the actions come back.
        """
        flusher = self._lane_module(
            "lane_ui_zz_test_flusher_ok", self.FLUSHER_SOURCE, allowed=True
        )
        author = self._lane_module(
            "lane_ui_zz_test_deferred_ok",
            "def answerer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_DEFERRED_REVIEWED_REPLY',"
            " b'\\x01', b'\\xde\\xad', 0.0)]\n",
            allowed=True,
        )
        flusher.PENDING.append((PARTY_INVITE_VITAL_ID, author.answerer))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(flusher.flush(), [True])
            actions = ui_dispatch.answer(
                object(), PARTY_INVITE_VITAL_ID, b""
            )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], "UI_DEFERRED_REVIEWED_REPLY")

    @staticmethod
    def _forge_dunder_module(made, name):
        """Point every writable ``__module__`` on ``made`` at ``name``.

        Without this the subtests below prove nothing they claim: a
        callable INSTANCE inherits ``__module__`` from its class and a
        bound method reads it off its function, so the attribute route
        found the closed lane on its own and the identity route was
        never exercised.  Measured: with this helper absent, deleting
        ``_defining_module_names``' callable-instance branch left the
        whole file green.  Returns whether anything was forged, so a
        shape that silently stopped being forgeable cannot pass quietly.
        """
        forged = False
        for target in (made, getattr(made, "__func__", None), type(made)):
            if target is None:
                continue
            try:
                target.__module__ = name
            except Exception:
                continue
            forged = getattr(made, "__module__", None) == name
            if forged:
                break
        return forged

    def test_the_ordinary_wrappers_do_not_hide_the_author(self):
        """partial, bound method and callable instance all resolve.

        Each is registered by the ALLOWED flusher, so no closed frame is
        on the stack, and each has its ``__module__`` forged to name the
        flusher -- so the ONLY witness left is identity.  ``partial``
        carries ``functools`` there and cannot be forged; the gate
        ignores that name because it is not a lane module, which leaves
        identity as its only witness too.
        """
        import functools

        shapes = {
            "partial": (
                "def _answer(session=None, vital_id=None, payload=None):\n"
                "    return []\n"
                "import functools\n"
                "made = functools.partial(_answer)\n"
            ),
            "method": (
                "class Answerer:\n"
                "    def run(self, session=None, vital_id=None,"
                " payload=None):\n"
                "        return []\n"
                "made = Answerer().run\n"
            ),
            "instance": (
                "class Answerer:\n"
                "    def __call__(self, session=None, vital_id=None,"
                " payload=None):\n"
                "        return []\n"
                "made = Answerer()\n"
            ),
        }
        for label, source in sorted(shapes.items()):
            with self.subTest(shape=label):
                ui_dispatch._ANSWERERS.clear()
                flusher = self._lane_module(
                    "lane_ui_zz_test_flusher_w_%s" % label,
                    self.FLUSHER_SOURCE,
                    allowed=True,
                )
                closed = self._lane_module(
                    "lane_ui_zz_test_wrapped_%s" % label,
                    source,
                    allowed=False,
                )
                forged = self._forge_dunder_module(
                    closed.made, flusher.__name__
                )
                if label != "partial":
                    self.assertTrue(
                        forged, "%s is no longer forgeable" % label
                    )
                self.assertNotEqual(
                    getattr(closed.made, "__module__", None),
                    closed.__name__,
                    "%s still names its author by attribute" % label,
                )
                flusher.PENDING.append((PARTY_INVITE_VITAL_ID, closed.made))
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(flusher.flush(), [True])
                self.assertIn(
                    closed.__name__,
                    ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
                    "%s hid its author from the gate" % label,
                )
        del functools

    def test_a_class_registered_as_the_answerer_names_its_own_module(self):
        """Self-review of round `lkswyp`, found after the first push.

        A CLASS is callable: registering one and letting ``answer()``
        call it builds an instance, so its code lives on ``__init__`` /
        ``__call__`` ON the class.  ``type(a_class)`` is the METACLASS,
        which names nobody, so before this the only witness for a class
        was ``SomeClass.__module__`` -- the writable attribute the whole
        fix exists to stop relying on.  Forged here, exactly as the
        wrapper subtests forge theirs.
        """
        flusher = self._lane_module(
            "lane_ui_zz_test_flusher_cls", self.FLUSHER_SOURCE, allowed=True
        )
        closed = self._lane_module(
            "lane_ui_zz_test_class_answerer",
            "class Answerer:\n"
            "    def __init__(self, session=None, vital_id=None,"
            " payload=None):\n"
            "        self.actions = []\n"
            "    def __iter__(self):\n"
            "        return iter(self.actions)\n"
            "made = Answerer\n",
            allowed=False,
        )
        closed.made.__module__ = flusher.__name__
        self.assertNotEqual(closed.made.__module__, closed.__name__)
        flusher.PENDING.append((PARTY_INVITE_VITAL_ID, closed.made))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(flusher.flush(), [True])
        self.assertIn(
            closed.__name__,
            ui_dispatch.gating_module_names(PARTY_INVITE_VITAL_ID),
            "a class hid its author from the gate",
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())

    def test_the_identity_walk_names_a_fresh_callable_every_time(self):
        """Two hundred fresh instances, collections forced between them.

        WHAT THIS DOES NOT PROVE, SAID FIRST.  ``seen`` is an identity
        set and ``getattr(type(x), "__call__")`` builds a NEW object per
        access, so dropping the last reference to one lets CPython hand
        its address to the next object built in the same walk, which
        would then be skipped as "already seen".  ``_defining_module_
        names`` keeps an ``alive`` list for that reason -- and a mutant
        deleting that list SURVIVES this test.  So this is a smoke test
        of the walk, not a proof of the keep-alive: the failure it
        guards against is rare and load-dependent, and no test in this
        file has reproduced it.  The fix is kept as cheap insurance and
        is reported as an unkilled mutant, not as a paid finding.
        """
        import gc

        class Answerer:
            def __call__(self, session=None, vital_id=None, payload=None):
                return []

        missed = []
        for i in range(200):
            gc.collect() if i % 25 == 0 else None
            names = ui_dispatch._defining_module_names(Answerer())
            if names != (__name__,):
                missed.append((i, names))
        self.assertEqual(missed, [], "the identity walk lost a name")

    def test_an_attribute_that_raises_cannot_break_registration(self):
        """The unwrap chain runs answerer-controlled descriptors.

        ``_defining_module_names`` must not turn a hostile ``func``
        property into an exception out of ``register_answerer()``.
        """
        class Hostile:
            @property
            def func(self):
                raise RuntimeError("no")

            def __call__(self, session=None, vital_id=None, payload=None):
                return []

        self.allow()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertTrue(
                ui_dispatch.register_answerer(
                    PARTY_INVITE_VITAL_ID, Hostile()
                )
            )


class GateAndFailClosedTests(_RegistryIsolation):
    ACTION = ("UI_TEST_ACTION", b"\x07\x07", b"\x01\x02", 0.0)

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
        # Named for what it measures: the actions were accepted by the
        # validator, which is one layer short of the wire
        # (pf-adversary round 3, D5).
        self.assertIn("UI_DISPATCH_ACCEPTED", stderr.getvalue())
        self.assertNotIn("UI_DISPATCH_ANSWERED", stderr.getvalue())

    def test_the_answerer_gets_a_snapshot_that_holds_no_session(self):
        """pf-adversary round 3 D2, and round 4 D-B.

        D2: the answerer used to be handed the live session and could
        write to it while returning ``[]`` under a green token.  D-B: the
        first fix wrapped the session in a proxy, and five one-liners
        walked past the proxy to the object it was holding.  So it holds
        nothing now -- the escape routes have to come back empty, not be
        refused, which is why they are asserted one by one here.
        """
        import gc

        seen = []

        def answerer(session=None, vital_id=None, payload=None):
            seen.append((session, vital_id, payload))
            return []

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)

        class Session(object):
            def __init__(self):
                self.gm_warp_position_pending = False

        session = Session()
        with contextlib.redirect_stderr(io.StringIO()):
            ui_dispatch.answer(session, PARTY_INVITE_VITAL_ID, b"\xAA\xBB")
        self.assertEqual(len(seen), 1)
        snapshot = seen[0][0]
        self.assertIsNot(snapshot, session)
        self.assertEqual(seen[0][1], PARTY_INVITE_VITAL_ID)
        self.assertEqual(seen[0][2], b"\xAA\xBB")
        # The allowlist is empty, so the snapshot is empty.
        self.assertEqual(ui_dispatch._SESSION_VIEW_FIELDS, ())
        self.assertEqual(tuple(snapshot), ())
        with self.assertRaises(KeyError):
            snapshot.field("gm_warp_position_pending")
        # THE FIVE ROUTES THAT DEFEATED THE PROXY (round 4, D-B). None of
        # them may reach the session, and none of them may reach anything
        # that does.
        reachable = [snapshot]
        reachable.extend(gc.get_referents(snapshot))
        reachable.append(type(snapshot))
        reachable.extend(
            getattr(snapshot, "__reduce_ex__")(2)[1:]
        )
        for found in reachable:
            with self.subTest(route=type(found).__name__):
                self.assertIsNot(found, session)
        self.assertFalse(
            any(
                obj is session
                for obj in gc.get_referents(snapshot)
            )
        )
        self.assertFalse(session.gm_warp_position_pending)

    def test_an_answerer_cannot_arm_the_gm_warp_window_through_the_session(
        self,
    ):
        """The D2 attack itself, as a test: the write must not land.

        The answerer returns ``[]`` -- nothing this module validates ever
        sees a label -- and reaches for the consumer directly.  It must
        come back out of ``answer()`` as a caught error with the session
        untouched, not as a green empty answer with the flag flipped.
        """

        class Session(object):
            def __init__(self):
                self.gm_warp_position_pending = False
                self.move_authority_grace_remaining = 0

        session = Session()

        def answerer(session=None, vital_id=None, payload=None):
            # The round-4 D-B escape, which defeated the proxy fix:
            # go around the attribute protocol entirely.
            real = object.__getattribute__(session, "_session")
            real.gm_warp_position_pending = True
            real.move_authority_grace_remaining = 99
            return []

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(session, PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertFalse(session.gm_warp_position_pending)
        self.assertEqual(session.move_authority_grace_remaining, 0)
        self.assertIn("UI_DISPATCH_ANSWER_ERR", stderr.getvalue())

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
            ("wrong arity 3", [("UI_L", b"\x01", b"\x01")]),
            ("wrong arity 5", [("UI_L", b"\x01", b"\x01", 0.0, 0)]),
            ("empty label", [("", b"\x01", b"\x01", 0.0)]),
            ("label not str", [(1, b"\x01", b"\x01", 0.0)]),
            # D2: another subsystem's label must never reach the action
            # list -- _gm_warp_note_position_pending matches on it.
            ("another lane's label",
             [("GM_WARP_POSITION_PENDING", b"\x01", b"\x01", 0.0)]),
            ("no UI_ prefix", [("PARTY_INVITE_OK", b"\x01", b"\x01", 0.0)]),
            # D12: the v141 sender writes `SENT <label>` into the evidence
            # file attended rounds grep.
            ("newline in label",
             [("UI_OK\nSENT forged=1", b"\x01", b"\x01", 0.0)]),
            ("nul in label", [("UI_OK\x00", b"\x01", b"\x01", 0.0)]),
            ("pc is an int", [("UI_L", 1, b"\x01", 0.0)]),
            ("pc is a bool", [("UI_L", True, b"\x01", 0.0)]),
            ("pc is a str", [("UI_L", "1", b"\x01", 0.0)]),
            ("pc is None", [("UI_L", None, b"\x01", 0.0)]),
            ("frame is a str", [("UI_L", b"\x01", "\x01", 0.0)]),
            ("frame is a bytearray",
             [("UI_L", b"\x01", bytearray(b"\x01"), 0.0)]),
            ("frame is None", [("UI_L", b"\x01", None, 0.0)]),
            ("delay is negative", [("UI_L", b"\x01", b"\x01", -0.5)]),
            ("delay is a bool", [("UI_L", b"\x01", b"\x01", True)]),
            ("delay is a str", [("UI_L", b"\x01", b"\x01", "0")]),
            ("delay is nan", [("UI_L", b"\x01", b"\x01", float("nan"))]),
            ("delay is inf", [("UI_L", b"\x01", b"\x01", float("inf"))]),
            ("frame is empty", [("UI_L", b"\x01", b"", 0.0)]),
            ("one good one bad",
             [self.ACTION, ("UI_L", b"\x01", "bad", 0.0)]),
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
        actions.append(("UI_EXTRA", b"\x01", b"\x02", 0.0))
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

    def test_the_seam_names_ui_dispatch_on_exactly_two_lines(self):
        # RENAMED, and its claim narrowed, on pf-adversary D8: the old name
        # said "three added lines and no more", and a mutant that inserted
        # 24 lines of dead helpers into runtime.py -- naming ui_dispatch
        # nowhere -- SURVIVED it. A substring census is not a line budget.
        # What this test really pins is the SHAPE of the seam: the import,
        # the call that opens it, and its argument line. The three-added-
        # lines budget COO route (b) grants is a property of the DIFF
        # (`git diff origin/main..HEAD --numstat -- runtime.py` -> `3	1`)
        # and belongs to the reviewer, which is what it now says out loud
        # rather than pretending to measure.
        # CODE LINES ONLY (pf-adversary round 3, D10). Counting every
        # line whose text contains "ui_dispatch" made the assertion below
        # forbid anyone from ever writing the module's name in a
        # runtime.py COMMENT -- a rule about prose wearing the shape of a
        # rule about the seam. A comment cannot open the seam, so it is
        # not what this test is measuring.
        source = RUNTIME_PY.read_text(encoding="utf-8").split("\n")
        naming = [
            n for n, line in enumerate(source)
            if "ui_dispatch" in line and not line.lstrip().startswith("#")
        ]
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


class TheConventionIsTheRealDispatchersTests(_RegistryIsolation):
    """pf-adversary D1: validate what the dispatcher REALLY returns.

    The draft's validator demanded `pc` be an `int`. Every action this
    server actually sends carries `pc` as `bytes`, so the validator
    admitted exactly one shape -- the hand-written tuple in this file --
    and refused all five real ones. A hand-written fixture cannot catch
    that, so this class drives real actions out of the real dispatcher and
    feeds them back through the validator.
    """

    def setUp(self):
        super().setUp()
        self.legacy = _legacy()

    def test_a_real_dispatch_return_passes_the_validator(self):
        pc, frame = make_return_select_server_response(self.legacy)
        self.assertIsInstance(pc, bytes)
        self.assertTrue(
            ui_dispatch._actions_are_well_formed(
                [("UI_REAL_SHAPE", pc, frame, 0.0)]
            )
        )

    def test_an_int_pc_is_refused_because_the_sender_calls_len_on_it(self):
        # pf_login_game_server_v141.py does len(out_pc)/hexdump(out_pc) in
        # a connection loop whose try has only a finally -- and it does it
        # AFTER sendall(out_frame). An int there is a thread death with the
        # bytes already on the wire.
        _pc, frame = make_return_select_server_response(self.legacy)
        self.assertFalse(
            ui_dispatch._actions_are_well_formed([("UI_INT_PC", 7, frame, 0.0)])
        )


class ValidationOrderTests(_RegistryIsolation):
    """pf-adversary D3 and D4: the order the guard does things in."""

    def test_a_batch_cannot_be_rewritten_while_it_is_being_validated(self):
        # D3: validation runs the answerer's own code (a numbers.Real
        # subclass's comparisons), so the draft -- which validated the live
        # list and copied it afterwards -- shipped a str-where-bytes-must-be
        # and a delay of -99.0 under a green UI_DISPATCH_ANSWERED token.
        import numbers as _numbers

        smuggled = ("UI_SNUCK_PAST", b"\x01", "a str, not bytes", -99.0)

        class Sneaky(_numbers.Real):
            def __init__(self, holder):
                self.holder = holder

            def __ge__(self, other):
                self.holder[:] = [smuggled]
                return True

            def __float__(self):
                return 0.0

            # numbers.Real's abstract surface, unused by this test.
            def __abs__(self): return 0.0
            def __add__(self, o): return 0.0
            def __ceil__(self): return 0
            def __eq__(self, o): return False
            def __floor__(self): return 0
            def __floordiv__(self, o): return 0.0
            def __hash__(self): return 0
            def __le__(self, o): return True
            def __lt__(self, o): return False
            def __mod__(self, o): return 0.0
            def __mul__(self, o): return 0.0
            def __neg__(self): return 0.0
            def __pos__(self): return 0.0
            def __pow__(self, o): return 0.0
            def __radd__(self, o): return 0.0
            def __rfloordiv__(self, o): return 0.0
            def __rmod__(self, o): return 0.0
            def __rmul__(self, o): return 0.0
            def __round__(self, n=None): return 0
            def __rpow__(self, o): return 0.0
            def __rtruediv__(self, o): return 0.0
            def __truediv__(self, o): return 0.0
            def __trunc__(self): return 0

        holder = []
        holder.append(("UI_LOOKS_FINE", b"\x01", b"\x02", Sneaky(holder)))

        def answerer(session=None, vital_id=None, payload=None):
            return holder

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = ui_dispatch.answer(
                object(), PARTY_INVITE_VITAL_ID, b""
            )
        # What ships is the SNAPSHOT the guard checked, not whatever the
        # lane rewrote the list to afterwards. The smuggled tuple -- a str
        # where bytes must be, delay -99.0 -- never reaches the caller.
        self.assertNotIn(smuggled, actions)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], "UI_LOOKS_FINE")
        self.assertEqual(actions[0][2], b"\x02")
        # And the lane really did rewrite the list it handed over, so this
        # test would fail on the draft rather than pass for lack of a try.
        self.assertEqual(holder, [smuggled])

    def test_an_exception_from_inside_the_validator_does_not_escape(self):
        # D4: __float__ raising is the answerer's code running INSIDE the
        # check. It used to escape answer(), escape dispatch(), and reach a
        # connection loop with no except.
        import numbers as _numbers

        class Exploding(_numbers.Real):
            def __ge__(self, other):
                raise ValueError("lane bug inside a comparison")

            def __float__(self):
                raise ValueError("lane bug inside __float__")

            def __abs__(self): return 0.0
            def __add__(self, o): return 0.0
            def __ceil__(self): return 0
            def __eq__(self, o): return False
            def __floor__(self): return 0
            def __floordiv__(self, o): return 0.0
            def __hash__(self): return 0
            def __le__(self, o): return True
            def __lt__(self, o): return False
            def __mod__(self, o): return 0.0
            def __mul__(self, o): return 0.0
            def __neg__(self): return 0.0
            def __pos__(self): return 0.0
            def __pow__(self, o): return 0.0
            def __radd__(self, o): return 0.0
            def __rfloordiv__(self, o): return 0.0
            def __rmod__(self, o): return 0.0
            def __rmul__(self, o): return 0.0
            def __round__(self, n=None): return 0
            def __rpow__(self, o): return 0.0
            def __rtruediv__(self, o): return 0.0
            def __truediv__(self, o): return 0.0
            def __trunc__(self): return 0

        def answerer(session=None, vital_id=None, payload=None):
            return [("UI_OK", b"\x01", b"\x02", Exploding())]

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_ANSWER_ERR", stderr.getvalue())


class RoundTwoFindingsTests(_RegistryIsolation):
    """pf-adversary round 2: R1, R2, R3, R5, R7 -- each with its own pin."""

    def test_a_list_typed_action_is_refused_because_it_stays_shared(self):
        # R1. list(actions) copies the OUTER list only, so a list-typed
        # action stays the answerer's own object and can be rewritten from
        # inside a delay comparison AFTER its label was cleared. Measured
        # end to end: a party-invite frame shipped the GM warp label under
        # a green token. Refusing the mutable shape closes it at the type
        # check; every action this project emits is a tuple.
        self.assertFalse(
            ui_dispatch._actions_are_well_formed(
                [["UI_L", b"\x01", b"\x02", 0.0]]
            )
        )
        self.assertTrue(
            ui_dispatch._actions_are_well_formed(
                [("UI_L", b"\x01", b"\x02", 0.0)]
            )
        )

    def test_a_forged_dunder_name_does_not_open_the_gate(self):
        # R2. frame.f_globals["__name__"] is a dict entry the calling
        # module owns: one line in a production_allowed = False lane file
        # made the gate answer True and printed an innocent module's name
        # in the token. The sys.modules KEY is set by the import
        # machinery, so the registrar is resolved by identity now.
        from pirateforce_foundation.lane_hooks import lane_gm_run_command

        namespace = {
            "__name__": lane_gm_run_command.__name__,
            "ui_dispatch": ui_dispatch,
            "PARTY_INVITE_VITAL_ID": PARTY_INVITE_VITAL_ID,
        }
        source = (
            "def _answer(session=None, vital_id=None, payload=None):\n"
            "    return [('UI_FORGED', b'\\x01', b'\\x02', 0.0)]\n"
            "ok = ui_dispatch.register_answerer("
            "PARTY_INVITE_VITAL_ID, _answer)\n"
        )
        with contextlib.redirect_stderr(io.StringIO()):
            exec(compile(source, "<forged lane>", "exec"), namespace)
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        self.assertEqual(module_name, "<unknown>")
        self.assertFalse(lane_hooks.module_production_allowed(module_name))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())

    def test_a_ui_label_carrying_a_foreign_substring_is_refused(self):
        # R3. The prefix closes the consumer that compares labels for
        # equality; the one beside it asks `"TELEPORT" in action[0]`, and
        # UI_PARTY_INVITE_TELEPORT_A satisfies the prefix. Measured: the
        # move-authority grace window reopened on a party-invite frame,
        # with no forgery -- that is a name a lane would plausibly pick.
        for label in ("UI_PARTY_INVITE_TELEPORT_A",
                      "UI_TELEPORT", "UI_X_LOCAL_REFRESH_Y"):
            with self.subTest(label=label):
                self.assertFalse(
                    ui_dispatch._actions_are_well_formed(
                        [(label, b"\x01", b"\x02", 0.0)]
                    )
                )
        self.assertTrue(
            ui_dispatch._actions_are_well_formed(
                [("UI_PARTY_INVITE_ACK", b"\x01", b"\x02", 0.0)]
            )
        )

    def test_an_exception_whose_repr_raises_is_still_caught(self):
        # R5. The %r ran while building _say's argument, inside the except
        # block, so it escaped the handler that exists to stop it.
        class Boom(Exception):
            def __repr__(self):
                raise RuntimeError("repr blew up in the except handler")

        def answerer(session=None, vital_id=None, payload=None):
            raise Boom()

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_ANSWER_ERR", stderr.getvalue())

    def test_subclasses_of_list_and_tuple_are_refused_not_duck_typed(self):
        # R7: two surviving mutants turned the shipped type() checks into
        # isinstance(), which admits a subclass that can lie about its own
        # contents after the check.
        class SneakyList(list):
            pass

        class SneakyTuple(tuple):
            pass

        good = ("UI_L", b"\x01", b"\x02", 0.0)
        self.assertFalse(
            ui_dispatch._actions_are_well_formed(SneakyList([good]))
        )
        self.assertFalse(
            ui_dispatch._actions_are_well_formed([SneakyTuple(good)])
        )
        self.assertTrue(ui_dispatch._actions_are_well_formed([good]))


class GateIsKeyedOnTheRegistrarTests(_RegistryIsolation):
    """pf-adversary D5: functools.wraps must not carry the gate with it."""

    def test_the_gate_reads_the_registering_module_not_fn_dunder_module(self):
        import functools

        from pirateforce_foundation.lane_hooks import lane_gm_run_command

        def _inner(session=None, vital_id=None, payload=None):
            return [("UI_WRAPS_BYPASS", b"\x02", b"\xee", 0.0)]

        # Borrow an ALLOWED module's name the way functools.wraps does.
        _inner.__module__ = lane_gm_run_command.__name__
        self.assertTrue(
            lane_hooks.module_production_allowed(_inner.__module__)
        )
        wrapper = functools.wraps(_inner)(
            lambda session=None, vital_id=None, payload=None: _inner(
                session=session, vital_id=vital_id, payload=payload
            )
        )
        with contextlib.redirect_stderr(io.StringIO()):
            ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, wrapper)
        module_name, _fn = ui_dispatch.registered_answerer(
            PARTY_INVITE_VITAL_ID
        )
        # Registered under THIS module, which is not production-allowed.
        self.assertEqual(module_name, __name__)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(
                ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b""), []
            )
        self.assertIn("UI_DISPATCH_GATED", stderr.getvalue())

    def test_the_gate_is_read_on_every_frame_not_cached(self):
        # D5/N12: the docstring says "call time, not registration time"
        # twice and a caching mutant survived. Close the gate between two
        # answers on the same registration.
        def answerer(session=None, vital_id=None, payload=None):
            return [("UI_LIVE", b"\x01", b"\x02", 0.0)]

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow()
        with contextlib.redirect_stderr(io.StringIO()):
            first = ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b"")
        self.assertEqual(len(first), 1)
        qualified = f"{lane_hooks.__name__}.{__name__}"
        lane_hooks._PRODUCTION_ALLOWED[qualified] = False
        with contextlib.redirect_stderr(io.StringIO()):
            second = ui_dispatch.answer(object(), PARTY_INVITE_VITAL_ID, b"")
        self.assertEqual(second, [])


class ConsoleTokensSurviveCp874Tests(unittest.TestCase):
    """pf-adversary D7: a guarded print that writes nothing is not evidence."""

    def test_a_non_cp874_character_still_produces_a_token(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp874", errors="strict")
        try:
            sys.stderr, real = stream, sys.stderr
            ui_dispatch._say("UI_DISPATCH_ANSWER_ERR id=0x37B1 \u4f60")
        finally:
            sys.stderr = real
        stream.flush()
        self.assertIn(b"UI_DISPATCH_ANSWER_ERR", raw.getvalue())

    def test_a_broken_stderr_does_not_raise(self):
        class Broken:
            def write(self, _text):
                raise OSError(9, "Bad file descriptor")

            def flush(self):
                raise OSError(9, "Bad file descriptor")

        try:
            sys.stderr, real = Broken(), sys.stderr
            ui_dispatch._say("UI_DISPATCH_ANSWER_ERR id=0x37B1")
        finally:
            sys.stderr = real

    def test_a_non_integer_vital_id_renders_without_raising(self):
        # D12: _hex's fallback branch had never executed.
        self.assertEqual(ui_dispatch._hex("not-an-int"), "'not-an-int'")
        self.assertEqual(ui_dispatch._hex(0x37B1), "0x37B1")


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
            return [("UI_TEST_PARTY_INVITE_REPLY", b"\x03", b"\x11\x22", 0.0)]

        ui_dispatch.register_answerer(PARTY_INVITE_VITAL_ID, answerer)
        self.allow(answerer)
        state = self._login_and_start("uidisp-live")
        rx_before = state.rx_frames
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, PARTY_INVITE_VITAL_ID, b"\x00\x01")
            ))
        self.assertEqual(
            actions, [("UI_TEST_PARTY_INVITE_REPLY", b"\x03", b"\x11\x22", 0.0)],
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
