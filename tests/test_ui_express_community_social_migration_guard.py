"""Guard test for the open pf-adversary question from LANE-UI round `rqwwp8`
(``pf_bridge/rounds/UI_20260906_1824_rqwwp8_mail_party_trade_wire_wstring_
tag_migration.md``): is there anything that goes red immediately if a future
round wires ``ui_community_social_wire.py`` into ``runtime.py`` before
migrating its own wstring call sites off the proven-wrong
``ui_social_wire.encode_untagged_wstring``/``read_untagged_wstring`` pair
(tag byte ``0x48`` missing -- see ``ui_friend_wire.py``, migrated in
``#934``, ``ui_mail_wire.py``/``ui_party_wire.py``/``ui_trade_wire.py``,
migrated in round `rqwwp8`, and ``ui_express_wire.py``, migrated in round
`me7s4u`)? ``ui_express_wire.py`` was originally guarded here too
(see ``_GUARDED_MODULES``'s comment below for why it was dropped once
migrated) -- the AST-parsing machinery below still names both modules in
its own history/examples since that predates the split.

Before this file: no. `runtime.py` importing either module while it still
calls the untagged pair would silently ship the same live misdecoding bug
those four modules had -- caught only if someone remembered to grep by
hand (`COO-DECISION 20260906_1649` forbids wiring either module before its
own migration, but nothing enforced it).

CORRECTION (round `u3pzcz`, pf-adversary): the first version of this file
used two regexes -- a MULTILINE ``^from \\.<module> import`` anchored to
line start for "is it wired", and a literal substring
``wire.encode_untagged_wstring(``/``wire.read_untagged_wstring(`` for "does
it still call the untagged pair". Both were defeated, reproducibly:
  1. ``runtime.py`` already contains a function-local, INDENTED
     ``from . import ui_logout_exit_game`` inside a dispatch branch (see
     line ~7585) -- the exact wiring shape a future round could reuse for
     ``ui_express_wire``/``ui_community_social_wire``. Because it is
     indented, ``^from`` never matches it under ``re.MULTILINE``, so the
     "is it wired" check silently returns "not wired" while the module is
     actually reachable and dispatching -- the guard produces zero
     failures in this scenario, the exact one it exists to catch.
  2. ``ui_express_wire.py``/``ui_community_social_wire.py`` import the
     buggy pair as ``from . import ui_social_wire as wire``; renaming that
     alias (e.g. ``as sw``) and updating the two call sites to match keeps
     the module functionally unmigrated while making the literal
     ``wire.encode_untagged_wstring(`` substring check report "clean".
Both are now caught by parsing `runtime.py` and the guarded module with
``ast`` instead of regex/substring matching: ``ast.walk`` finds an
``Import``/``ImportFrom`` node regardless of indentation or nesting depth
(fixing (1)), and the untagged-pair check resolves whatever alias
``ui_social_wire`` (or its two functions) were imported under before
matching call sites against that alias, not a fixed name (fixing (2)).
Both original defects are pinned as regression tests below
(``ImportDetectionTests``, ``UntaggedPairCallDetectionTests``) against
synthetic source strings, so a future edit that reintroduces either
regex-style shortcut fails those tests directly, not just by luck of
which import/alias shape a later round happens to pick.

What this guards, and what it does not
---------------------------------------
Parses `runtime.py`'s AST for any import of either guarded module --
``from .<module> import ...``, ``from . import <module>``, or
``import pirateforce_foundation.<module>`` -- at any nesting depth
(module level, inside a function, inside a branch), and only if one is
found does it check whether that module's own AST still contains a call
resolving to ``ui_social_wire.encode_untagged_wstring``/
``read_untagged_wstring`` under whatever import alias(es) that module
actually uses.

NOT claimed: that this is the only way either module could reach a real
client frame (a lane_hooks report-only subscriber wired directly to the
vital id without any `import` of the module in `runtime.py` at all -- e.g.
dynamic ``importlib.import_module`` -- would not trip this guard) -- this
covers real import statements, static or dynamic string-based module
loading is out of scope.

ALSO NOT claimed (found by pf-adversary reviewing round `me7s4u`, which
recovered this file, against three constructed inputs -- none of them
present in ``ui_community_social_wire.py`` today, confirmed by inspection):
the untagged-pair detector resolves only a direct
``<alias-or-module-name>.<func>(...)`` call shape. It does not follow a
local reassignment (``enc = wire.encode_untagged_wstring; enc(...)``), a
``getattr(wire, "encode_untagged_wstring")`` indirection, or an
attribute-of-attribute call (``self.wire = wire; self.wire.encode_
untagged_wstring(...)``, where the call's ``func.value`` is itself an
``ast.Attribute`` rather than the ``ast.Name`` this detector's alias
resolution expects). None of these shapes appear in either guarded
module as of this round; this is a disclosed residual gap for whoever
migrates ``ui_community_social_wire.py``'s remaining call sites to be
aware of, not a claim that today's guard is watertight against a
deliberately obfuscated future rewrite.
"""
from __future__ import annotations

import ast
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FOUNDATION_DIR = ROOT / "src" / "pirateforce_foundation"

_GUARDED_MODULES = ("ui_community_social_wire",)
# ``ui_express_wire`` migrated off the untagged pair in LANE-UI round
# `me7s4u` (see that module's docstring) -- dropped from this tuple per
# `test_guarded_modules_still_use_the_untagged_pair_today`'s own
# instruction ("update this test's expectations alongside whatever round
# migrated it"). Only ``ui_community_social_wire`` is still unmigrated and
# still needs this guard.
_UNTAGGED_PAIR_NAMES = ("encode_untagged_wstring", "read_untagged_wstring")


def _module_is_imported(source: str, module_name: str) -> bool:
    """True if `source` imports `module_name` anywhere, any nesting depth,
    any of the three shapes this codebase actually uses for a sibling
    `pirateforce_foundation` module (`from .<mod> import X`,
    `from . import <mod>`, `import pirateforce_foundation.<mod>`)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 1 and node.module == module_name:
                return True
            if node.level == 1 and node.module is None and any(
                alias.name == module_name for alias in node.names
            ):
                return True
            if node.level == 0 and node.module == (
                f"pirateforce_foundation.{module_name}"
            ):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in (
                    module_name, f"pirateforce_foundation.{module_name}",
                ):
                    return True
    return False


def _resolve_untagged_pair_aliases(tree: ast.AST) -> tuple[set[str], dict[str, set[str]]]:
    """Find every local name that resolves to the `ui_social_wire` module
    object, and every local name that resolves directly to one of its two
    untagged-wstring functions, regardless of `as`-alias."""
    module_aliases: set[str] = set()
    function_aliases: dict[str, set[str]] = {name: set() for name in _UNTAGGED_PAIR_NAMES}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 1 and node.module is None:
                for alias in node.names:
                    if alias.name == "ui_social_wire":
                        module_aliases.add(alias.asname or alias.name)
            elif (
                node.level == 1 and node.module == "ui_social_wire"
            ) or (
                node.level == 0
                and node.module == "pirateforce_foundation.ui_social_wire"
            ):
                for alias in node.names:
                    if alias.name in function_aliases:
                        function_aliases[alias.name].add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in (
                    "ui_social_wire", "pirateforce_foundation.ui_social_wire",
                ):
                    bound = alias.asname or alias.name.rsplit(".", 1)[-1]
                    module_aliases.add(bound)
    return module_aliases, function_aliases


def _module_calls_untagged_pair(source: str) -> bool:
    """True if `source` calls `ui_social_wire.encode_untagged_wstring`/
    `read_untagged_wstring` (or an `as`-aliased or directly-imported form
    of either), under whatever name(s) it actually imported them as."""
    tree = ast.parse(source)
    module_aliases, function_aliases = _resolve_untagged_pair_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in _UNTAGGED_PAIR_NAMES
            and isinstance(func.value, ast.Name)
            and func.value.id in module_aliases
        ):
            return True
        if isinstance(func, ast.Name) and any(
            func.id in aliases for aliases in function_aliases.values()
        ):
            return True
    return False


class ExpressCommunitySocialMigrationGuardTests(unittest.TestCase):
    def test_current_state_is_unwired(self):
        # Documents the state COO-DECISION 20260906_1649/1745 expects right
        # now: neither module is imported into runtime.py yet. This is not
        # itself the guard (see the next test) -- it just makes a silent,
        # accidental future wiring visible as a diff in this test instead
        # of only in `runtime.py`.
        runtime_source = (FOUNDATION_DIR / "runtime.py").read_text(
            encoding="utf-8"
        )
        for module_name in _GUARDED_MODULES:
            with self.subTest(module=module_name):
                self.assertFalse(
                    _module_is_imported(runtime_source, module_name),
                    f"{module_name} is now imported by runtime.py -- this "
                    "test needs updating alongside the migration that "
                    "wires it in (see the next test for the actual "
                    "guard).",
                )

    def test_wiring_before_migration_is_caught(self):
        runtime_source = (FOUNDATION_DIR / "runtime.py").read_text(
            encoding="utf-8"
        )
        for module_name in _GUARDED_MODULES:
            with self.subTest(module=module_name):
                if not _module_is_imported(runtime_source, module_name):
                    # Not wired yet -- nothing to guard for this module in
                    # this state. The moment a round imports it (any
                    # shape: module level, `from . import`, or inside a
                    # function/branch), this branch stops being taken and
                    # the check below starts running against that same
                    # round's diff.
                    continue
                module_source = (
                    FOUNDATION_DIR / f"{module_name}.py"
                ).read_text(encoding="utf-8")
                self.assertFalse(
                    _module_calls_untagged_pair(module_source),
                    f"{module_name} is wired into runtime.py but still "
                    "calls ui_social_wire.encode_untagged_wstring/"
                    "read_untagged_wstring -- migrate this module onto "
                    "wire.wstring_tag/wire.read_wstring_tag (tag 0x48, "
                    "same pair ui_friend_wire.py/ui_mail_wire.py/"
                    "ui_party_wire.py/ui_trade_wire.py already proved) "
                    "before wiring it, per COO-DECISION 20260906_1649.",
                )

    def test_guarded_modules_still_use_the_untagged_pair_today(self):
        # Sanity check on the guard itself: if either module had already
        # migrated on its own (nothing forbids fixing it early), the
        # previous test would pass trivially and look like it is guarding
        # something it is not. This pins today's actual state so a mutant
        # that always passes gets caught.
        for module_name in _GUARDED_MODULES:
            with self.subTest(module=module_name):
                module_source = (
                    FOUNDATION_DIR / f"{module_name}.py"
                ).read_text(encoding="utf-8")
                self.assertTrue(
                    _module_calls_untagged_pair(module_source),
                    f"{module_name} no longer calls the untagged pair -- "
                    "update this test's expectations alongside whatever "
                    "round migrated it.",
                )


class ImportDetectionTests(unittest.TestCase):
    """Regression coverage for pf-adversary defect 1 (round `u3pzcz`): a
    function-local, indented `from . import <module>` -- the exact shape
    `runtime.py` already uses for `ui_logout_exit_game` -- must be
    detected, not just a module-level `from .<module> import NAME`."""

    def test_module_level_from_x_import_name(self):
        source = "from .ui_express_wire import SOME_VITAL_ID\n"
        self.assertTrue(_module_is_imported(source, "ui_express_wire"))

    def test_module_level_parenthesized_multiline_import(self):
        source = textwrap.dedent(
            """
            from .ui_express_wire import (
                SOME_VITAL_ID,
                OTHER_VITAL_ID,
            )
            """
        )
        self.assertTrue(_module_is_imported(source, "ui_express_wire"))

    def test_function_local_indented_from_import_module(self):
        # The precise shape pf-adversary found already live in runtime.py
        # for ui_logout_exit_game, reproduced here for ui_express_wire.
        source = textwrap.dedent(
            """
            def _dispatch(self, parsed):
                if parsed.vital_id == SOME_ID:
                    from . import ui_express_wire
                    return ui_express_wire.dispatch(self, parsed)
                return []
            """
        )
        self.assertTrue(_module_is_imported(source, "ui_express_wire"))

    def test_absolute_import_form(self):
        source = "import pirateforce_foundation.ui_express_wire\n"
        self.assertTrue(_module_is_imported(source, "ui_express_wire"))

    def test_unrelated_module_is_not_a_false_positive(self):
        source = textwrap.dedent(
            """
            from . import ui_logout_exit_game
            from .ui_friend_wire import COMMUNITY_REMOVE_FRIEND_VITAL_ID
            """
        )
        self.assertFalse(_module_is_imported(source, "ui_express_wire"))
        self.assertFalse(_module_is_imported(source, "ui_community_social_wire"))


class UntaggedPairCallDetectionTests(unittest.TestCase):
    """Regression coverage for pf-adversary defect 2 (round `u3pzcz`): an
    `as`-aliased (or directly-imported) untagged-pair call must be
    detected under any alias, not just the literal `wire.` prefix."""

    def test_default_alias_matches(self):
        source = textwrap.dedent(
            """
            from . import ui_social_wire as wire
            def encode(fields):
                return wire.encode_untagged_wstring(fields.s)
            """
        )
        self.assertTrue(_module_calls_untagged_pair(source))

    def test_renamed_alias_matches(self):
        # pf-adversary's exact reproduction: rename `wire` to `sw`.
        source = textwrap.dedent(
            """
            from . import ui_social_wire as sw
            def encode(fields):
                out = sw.encode_untagged_wstring(fields.s)
                return out
            def decode(payload, offset):
                return sw.read_untagged_wstring(payload, offset)
            """
        )
        self.assertTrue(_module_calls_untagged_pair(source))

    def test_direct_name_import_with_alias_matches(self):
        source = textwrap.dedent(
            """
            from .ui_social_wire import encode_untagged_wstring as enc
            from .ui_social_wire import read_untagged_wstring as dec
            def encode(fields):
                return enc(fields.s)
            def decode(payload, offset):
                return dec(payload, offset)
            """
        )
        self.assertTrue(_module_calls_untagged_pair(source))

    def test_migrated_module_is_not_a_false_positive(self):
        source = textwrap.dedent(
            """
            from . import ui_social_wire as wire
            def encode(fields):
                return wire.wstring_tag(fields.s)
            def decode(payload, offset):
                return wire.read_wstring_tag(payload, offset)
            \"\"\"Docstring mentioning encode_untagged_wstring/
            read_untagged_wstring in prose must not trip the detector.\"\"\"
            """
        )
        self.assertFalse(_module_calls_untagged_pair(source))


if __name__ == "__main__":
    unittest.main()
