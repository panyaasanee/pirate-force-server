"""Guard test for the open pf-adversary question from LANE-UI round `rqwwp8`
(``pf_bridge/rounds/UI_20260906_1824_rqwwp8_mail_party_trade_wire_wstring_
tag_migration.md``): is there anything that goes red immediately if a future
round wires ``ui_express_wire.py``/``ui_community_social_wire.py`` into
``runtime.py`` before migrating their own wstring call sites off the proven-
wrong ``ui_social_wire.encode_untagged_wstring``/``read_untagged_wstring``
pair (tag byte ``0x48`` missing -- see ``ui_friend_wire.py``, migrated in
``#934``, and ``ui_mail_wire.py``/``ui_party_wire.py``/``ui_trade_wire.py``,
migrated in the round `rqwwp8` round this file follows)?

Before this file: no. `runtime.py` importing either module while it still
calls the untagged pair would silently ship the same live misdecoding bug
those four modules had -- caught only if someone remembered to grep by hand
(`COO-DECISION 20260906_1649` forbids wiring either module before its own
migration, but nothing enforced it).

What this guards, and what it does not
---------------------------------------
Reads `runtime.py`'s own source text for a real ``from .ui_express_wire
import`` / ``from .ui_community_social_wire import`` line (the same import
shape every other UI wire module already wired in uses -- see
`ui_friend_wire`/`ui_mail_wire`/`ui_party_wire`/`ui_trade_wire` above line 58
of `runtime.py`), and only if one is present does it check whether that
module's source still calls `wire.encode_untagged_wstring(` /
`wire.read_untagged_wstring(` -- the literal call-site shape distinguishing
an unmigrated module from a migrated one (docstrings on the four already-
migrated modules mention the two names in prose without calling them; a
substring match on the bare names would false-positive on that prose, so
this checks the call-site shape with `wire.` and the opening paren, not the
name alone).

NOT claimed: that this is the only way either module could reach a real
client frame (a lane_hooks report-only subscriber wired directly to the
vital id without a `runtime.py` import line would not trip this guard) --
this covers the one wiring shape every UI wire module in this tree has
used so far, not every conceivable one.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FOUNDATION_DIR = ROOT / "src" / "pirateforce_foundation"

_GUARDED_MODULES = ("ui_express_wire", "ui_community_social_wire")
_UNTAGGED_CALL_PATTERNS = (
    "wire.encode_untagged_wstring(",
    "wire.read_untagged_wstring(",
)


class ExpressCommunitySocialMigrationGuardTests(unittest.TestCase):
    def test_current_state_is_unwired(self):
        # Documents the state COO-DECISION 20260906_1649/1745 expects right
        # now: neither module has a `runtime.py` import line yet. This is
        # not itself the guard (see the next test) -- it just makes a
        # silent, accidental future wiring visible as a diff in this test
        # instead of only in `runtime.py`.
        runtime_source = (FOUNDATION_DIR / "runtime.py").read_text(
            encoding="utf-8"
        )
        for module_name in _GUARDED_MODULES:
            with self.subTest(module=module_name):
                self.assertIsNone(
                    re.search(
                        rf"^from \.{module_name} import\b",
                        runtime_source,
                        re.MULTILINE,
                    ),
                    f"{module_name} now has a runtime.py import line -- "
                    "this test needs updating alongside the migration that "
                    "wires it in (see the next test for the actual guard).",
                )

    def test_wiring_before_migration_is_caught(self):
        runtime_source = (FOUNDATION_DIR / "runtime.py").read_text(
            encoding="utf-8"
        )
        for module_name in _GUARDED_MODULES:
            with self.subTest(module=module_name):
                wired = re.search(
                    rf"^from \.{module_name} import\b",
                    runtime_source,
                    re.MULTILINE,
                )
                if wired is None:
                    # Not wired yet -- nothing to guard for this module in
                    # this state. The moment a round adds the import line
                    # above, this branch stops being taken and the check
                    # below starts running against that same round's diff.
                    continue
                module_source = (
                    FOUNDATION_DIR / f"{module_name}.py"
                ).read_text(encoding="utf-8")
                for pattern in _UNTAGGED_CALL_PATTERNS:
                    self.assertNotIn(
                        pattern,
                        module_source,
                        f"{module_name} is wired into runtime.py but still "
                        f"calls {pattern[:-1]} -- migrate this module onto "
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
                    any(
                        pattern in module_source
                        for pattern in _UNTAGGED_CALL_PATTERNS
                    ),
                    f"{module_name} no longer calls the untagged pair -- "
                    "update this test's expectations alongside whatever "
                    "round migrated it.",
                )


if __name__ == "__main__":
    unittest.main()
