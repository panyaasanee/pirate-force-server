"""LANE-B: closes the open design question pf-adversary left in round
`404m21` about ``mob_viewer_link`` -- pinned here rather than answered in
prose, per this project's own rule that a claim which is not a test is not
checked.

THE QUESTION.  One monster with N sessions watching it needs N different
composed bodies (the field this module appends IS the viewer). Round
`404m21`'s own file said the answer is "compose fresh at send time, a pure
function", but named that nothing yet GUARDS a future caller against getting
this wrong the other way: caching one composed body per session and re-
serving it on the next frame, or on a relog/second window, would hand a
session bytes built for a DIFFERENT viewer, or stale bytes built before the
monster's own state (HP, template) last changed.

WHAT THIS FILE PINS, IN TWO INDEPENDENT LAYERS (the project's own "two
layers, never one attesting the other" rule):

  1. STATIC: ``mob_viewer_link.py`` carries no module-level mutable
     container, no ``functools.lru_cache``/``cache`` decorator, and no
     ``global``/``nonlocal`` statement. A cache needs somewhere to live;
     this sweep proves the module has no such place, so a future edit that
     ADDS one turns this file red at review time instead of at a relog six
     months from now.
  2. BEHAVIOURAL: calling the composer for three interleaved "sessions" (A,
     B, A again) on the SAME monster returns byte-identical output for A
     both times, and calling it for two DIFFERENT monsters interleaved with
     the same viewer never lets one monster's composed tail leak into the
     other's. Neither property would hold if either function secretly kept
     the last body it built and patched it, instead of building fresh every
     call from its own arguments alone.

WHAT THIS FILE DOES NOT PROVE.  It does not prove ``runtemper.py`` (chief's
file, not this lane's) refrains from adding ITS OWN per-session cache above
this module -- that is CORE-REQUEST-GM-061's wiring, still open, and no test
in this repo can reach across that boundary. What it proves is that nothing
in the module this lane owns forces or invites that mistake, and that the
functions themselves are safe to call fresh on every frame, which is the
half of the contract this lane can actually build.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: F401  (import-time gate)
from pirateforce_foundation import field_mobs, mob_viewer_link
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import SCENE_ID, SCENE_SEQUENCE  # noqa: F401


VIEWER_A = 0x5150
VIEWER_B = 0x5151

MODULE_PATH = (
    Path(mob_viewer_link.__file__)
    if hasattr(mob_viewer_link, "__file__")
    else ROOT / "src" / "pirateforce_foundation" / "mob_viewer_link.py"
)

#: Names that would give a per-viewer or per-session composed body somewhere
#: to persist across calls. Not a style sweep: every one of these is a place
#: state could live between two calls to ``link_viewer_to_npc_attr``.
FORBIDDEN_CACHE_DECORATORS = ("lru_cache", "cache")


class _ModuleLevelStateVisitor(ast.NodeVisitor):
    """Collects every module-level assignment target and every decorator
    name used anywhere in the file, plus any ``global``/``nonlocal``.
    """

    def __init__(self) -> None:
        self.module_level_names: list[str] = []
        self.decorator_names: list[str] = []
        self.global_or_nonlocal: list[str] = []

    def visit_Module(self, node: ast.Module) -> None:  # noqa: N802
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.module_level_names.append(target.id)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(
                stmt.target, ast.Name
            ):
                self.module_level_names.append(stmt.target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        for dec in node.decorator_list:
            # A decorator is a Name (``@cache``), an Attribute
            # (``@functools.cache``), or a Call wrapping either
            # (``@functools.lru_cache(maxsize=None)``) -- unwrap the Call
            # first or a parameterised cache decorator is invisible here.
            target = dec.func if isinstance(dec, ast.Call) else dec
            name = target.id if isinstance(target, ast.Name) else getattr(
                target, "attr", None
            )
            if name:
                self.decorator_names.append(name)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:  # noqa: N802
        self.global_or_nonlocal.extend(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:  # noqa: N802
        self.global_or_nonlocal.extend(node.names)


class NoSessionCacheStaticSweep(unittest.TestCase):
    """Layer 1: the module has nowhere for a per-viewer cache to live."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(cls.source, filename=str(MODULE_PATH))
        visitor = _ModuleLevelStateVisitor()
        visitor.visit(tree)
        cls.visitor = visitor

    def test_no_module_level_mutable_container(self) -> None:
        """Every module-level binding must be a constant, not a container
        a function could quietly append/insert into across calls."""
        mutable_kinds = (dict, list, set)
        for name in self.visitor.module_level_names:
            value = getattr(mob_viewer_link, name, None)
            with self.subTest(name=name):
                self.assertNotIsInstance(
                    value,
                    mutable_kinds,
                    "module-level mutable container %r is exactly where a "
                    "per-session cache would live" % (name,),
                )

    def test_no_memoizing_decorator(self) -> None:
        for forbidden in FORBIDDEN_CACHE_DECORATORS:
            with self.subTest(decorator=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.visitor.decorator_names,
                    "a memoizing decorator on a viewer-keyed composer is "
                    "the per-session-cache mistake this file exists to "
                    "catch before a relog does",
                )

    def test_no_global_or_nonlocal_statement(self) -> None:
        self.assertEqual(
            self.visitor.global_or_nonlocal,
            [],
            "a function that reaches for module state via global/nonlocal "
            "is the other way a cache gets built by accident",
        )

    def test_module_level_names_are_the_expected_shape(self) -> None:
        """Every module-level binding this file has today is either a
        string, an int, or the ``production_allowed`` bool -- documented
        here as a closed set so a FUTURE binding of a different Python type
        (dict/list/set are already refused above; this also catches, say,
        a bare ``object()`` sentinel meant to key a cache elsewhere) is at
        least visible in this test's own failure, not silently new.

        This intentionally names TYPES, not identifiers, so a well-named
        constant that happens to contain the word "cache" while describing
        the ABSENCE of one (e.g. this round's own
        ``COMPOSE_AT_SEND_TIME_NOT_CACHED_PER_SESSION``) is not punished by
        its own name -- only by what it actually is.
        """
        allowed_types = (str, int, bytes)
        for name in self.visitor.module_level_names:
            value = getattr(mob_viewer_link, name, None)
            with self.subTest(name=name):
                self.assertIsInstance(value, allowed_types)


class ComposeFreshNotCachedBehaviour(unittest.TestCase):
    """Layer 2: the functions behave as if they hold no state, because they
    hold none."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = list(field_mobs.load_roster())
        assert len(cls.roster) >= 2, (
            "this test needs two distinct monster rows to prove one "
            "viewer's link on monster X never leaks into monster Y"
        )
        cls.mob_x = cls.roster[0]
        cls.mob_y = cls.roster[1]

    def _entry(self, mob, viewer_identity=None):
        return field_mobs.hostile_actor_entry(
            self.legacy, mob, viewer_identity=viewer_identity
        )

    def test_revisiting_the_same_viewer_reproduces_the_same_bytes(self) -> None:
        """Sessions A, B, A again on ONE monster: A's second answer must be
        byte-identical to A's first, which only holds if nothing cached B's
        call (or anything else) into the state A's composition reads."""
        mob = self.mob_x
        first_a = self._entry(mob, VIEWER_A)
        _ = self._entry(mob, VIEWER_B)  # a different session, interleaved
        second_a = self._entry(mob, VIEWER_A)
        self.assertEqual(first_a, second_a)

    def test_two_monsters_interleaved_for_the_same_viewer_never_cross(
        self,
    ) -> None:
        """One session, two monsters, interleaved: neither composed body
        may carry the other monster's identity, mask, or tail -- which a
        naive "last body built" cache keyed only on viewer would risk."""
        x_first = self._entry(self.mob_x, VIEWER_A)
        y_first = self._entry(self.mob_y, VIEWER_A)
        x_second = self._entry(self.mob_x, VIEWER_A)
        y_second = self._entry(self.mob_y, VIEWER_A)
        self.assertEqual(x_first, x_second)
        self.assertEqual(y_first, y_second)
        self.assertNotEqual(x_first, y_first)

    def test_hp_change_between_two_calls_for_the_same_viewer_is_reflected(
        self,
    ) -> None:
        """A cached body would still show the OLD hp on the next frame.
        A fresh composition never can -- this is the concrete player-
        visible failure a cache would cause: a monster shown at the wrong
        HP to a viewer who was already looking at it last frame."""
        mob = self.mob_x
        full_hp = self._entry(mob, VIEWER_A)
        damaged = field_mobs.hostile_actor_entry(
            self.legacy, mob, current_hp=1, viewer_identity=VIEWER_A
        )
        self.assertNotEqual(full_hp, damaged)
        healed_again = self._entry(mob, VIEWER_A)
        self.assertEqual(full_hp, healed_again)


if __name__ == "__main__":
    unittest.main()
