"""Re-derive, on ANY clone, the pins that two image-gated verifiers carry.

``tools/pf_runtimeres_actor_entry_static.py`` and
``tools/pf_hp_death_respawn_static.py`` open the read-only client image at
import time.  Their test modules therefore skip on a fresh clone, and the
Windows gate's client-free subset excludes them outright - so anything those
files pin about OUR OWN ``src/`` rots in silence until somebody runs the full
suite by hand on the bridge.  On 2026-08-28 somebody finally did, and 38 tests
failed at once: eleven source pins had drifted, two of them wrong since the
commit that wrote them (at ``d9f9aac`` the tree already measured 21 and 23 while
that same commit pinned 16 and 21).

Neither verifier needs the image for the part that counts ``src/``.  This module
re-derives every one of those numbers from the source tree and asserts that
each place they are written down still agrees:

  * the ``guard(... == N)`` literals in the actor-entry verifier;
  * the ``RUNTIMERES_COUNTS`` block in its report;
  * the assertions inside ``tests/test_runtimeres_actor_entry_static.py`` -
    the copy that actually rotted, and the one the gate never runs;
  * the code-token discriminator the respawn verifier's two negatives rest on.

Deliberately independent, not a wrapper: it re-implements the regexes rather
than importing a verifier it cannot load.  Two implementations of one sentence
disagreeing is a finding, not noise.

It reads text files under this repository, opens no socket, touches no
database, boots no server, needs no third-party package, and never looks for
the proprietary image - so it runs everywhere the suite runs.

Re-pinning when a lane legitimately adds a call site: change the guard and the
name tuple in the verifier, the ``RUNTIMERES_COUNTS`` block in the report, and
the assertions in the bridge-only test module, all in the same commit, and name
the lane beside each number.  Every failure message below prints the measured
value and the modules holding it, so the repair is mechanical.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src" / "pirateforce_foundation"
TOOL = ROOT / "tools" / "pf_runtimeres_actor_entry_static.py"
BRIDGE_TEST = ROOT / "tests" / "test_runtimeres_actor_entry_static.py"
REPORT = (
    ROOT / "reports"
    / "PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md"
)
V141 = ROOT / "current" / "pf_login_game_server_v141.py"
COUNTS_BLOCK = re.compile(r"```json RUNTIMERES_COUNTS\n(?P<body>.*?)\n```", re.S)

sys.path.insert(0, str(ROOT / "tools"))
import pf_code_token_scan  # noqa: E402

# The patterns section [5] of the verifier counts with, copied deliberately.
# If the verifier changes one of them, this file has to change with it, and the
# disagreement is loud rather than silent.
ENTRY_PATTERN = r"make_remote_actor_entry\("
STREAM_PATTERN = r"make_runtime_remote_actors\("
VITAL_PATTERN = r"make_runtime_vitals\("
DEATH_TIMER_BIT = r"0x0080"
ZERO_HP_LITERAL = r"current_hp\s*=\s*0\b"
ZERO_HP_CONST = r"(?:HP_ZERO|HP_FLOOR|HP_WHEN_DEAD)\s*=\s*0\b"
FORBIDDEN_CONST = re.compile(r"(?m)^[A-Z0-9_]*FORBIDDEN[A-Z0-9_]*\s*=\s*0x0080\b")


def _modules() -> dict:
    return {p.name: p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(SRC_DIR.glob("*.py"))}


def _hits(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def _sites(pattern: str, modules: dict) -> int:
    return sum(_hits(pattern, text) for text in modules.values())


def _names(predicate, modules: dict) -> list:
    return sorted(name for name, text in modules.items() if predicate(text))


def _measure() -> dict:
    """Every ``RUNTIMERES_COUNTS`` key that is derived from our own sources."""
    modules = _modules()
    v141 = V141.read_text(encoding="utf-8", errors="replace")

    def builds(text):
        return _hits(ENTRY_PATTERN, text) > 0

    def sets_bit(text):
        return (builds(text) and _hits(DEATH_TIMER_BIT, text) > 0
                and not FORBIDDEN_CONST.search(text))

    def forbids_bit(text):
        return (builds(text) and _hits(DEATH_TIMER_BIT, text) > 0
                and bool(FORBIDDEN_CONST.search(text)))

    return {
        "src_actor_entry_call_sites": _sites(ENTRY_PATTERN, modules),
        "src_actor_stream_call_sites": _sites(STREAM_PATTERN, modules),
        "src_vital_stream_call_sites": _sites(VITAL_PATTERN, modules),
        "src_modules_building_actor_entries": len(_names(builds, modules)),
        "src_modules_building_actor_entries_names": _names(builds, modules),
        "src_modules_mentioning_basicattr_bit_0x0080":
            len(_names(lambda t: _hits(DEATH_TIMER_BIT, t) > 0, modules)),
        "src_modules_doing_both": len(_names(sets_bit, modules)),
        "src_modules_doing_both_names": _names(sets_bit, modules),
        "src_modules_forbidding_basicattr_bit_0x0080":
            len(_names(forbids_bit, modules)),
        "src_modules_forbidding_names": _names(forbids_bit, modules),
        "src_modules_passing_zero_hp_by_named_constant":
            _names(lambda t: _hits(ZERO_HP_CONST, t) > 0, modules),
        "server_call_sites_emitting_zero_current_hp":
            _sites(ZERO_HP_LITERAL, modules) + _hits(ZERO_HP_LITERAL, v141),
    }


def _guarded_int(symbol: str) -> int:
    """The literal the verifier guards `symbol` against, read from its source.

    Anchored at the start of a line on purpose: this repository quotes retired
    guards verbatim inside comments, and a commented-out pin must never be
    mistaken for the live one.
    """
    source = TOOL.read_text(encoding="utf-8")
    match = re.search(r"(?m)^guard\(%s == (\d+)" % re.escape(symbol), source)
    assert match, (
        "tools/pf_runtimeres_actor_entry_static.py no longer guards %s with a "
        "bare integer at the start of a line - this test pins that guard and "
        "must be updated with it" % symbol)
    return int(match.group(1))


def _guarded_module_names() -> list:
    source = TOOL.read_text(encoding="utf-8")
    match = re.search(
        r"(?m)^guard\(SRC_MODULES_WITH_ACTOR_ENTRY == \d+\n"
        r"\s*and SRC_MODULES_WITH_ACTOR_ENTRY_NAMES == \((?P<body>.*?)\),",
        source, re.S)
    assert match, (
        "the verifier no longer pins SRC_MODULES_WITH_ACTOR_ENTRY_NAMES as a "
        "literal tuple beside its count - this test pins that tuple and must "
        "be updated with it")
    return list(re.findall(r'"([^"]+)"', match.group("body")))


def _report_counts() -> dict:
    match = COUNTS_BLOCK.search(REPORT.read_text(encoding="utf-8"))
    assert match, "the report must carry a ```json RUNTIMERES_COUNTS block"
    return json.loads(match.group("body"))


def _bridge_test_pins() -> dict:
    """The `counts[...]` assertions inside the bridge-only test module.

    That module is excluded from the gate's client-free subset, so nothing else
    in the suite reads these numbers on a machine without the image.  They are
    the copy that went eleven rounds stale.
    """
    source = BRIDGE_TEST.read_text(encoding="utf-8")
    pins = {}
    for key, value in re.findall(
            r'counts\["(\w+)"\],\s*(\d+)\)', source):
        pins[key] = int(value)
    for key, body in re.findall(
            r'counts\["(\w+)"\],\s*\n?\s*\[(.*?)\]\)', source, re.S):
        pins[key] = re.findall(r'"([^"]+)"', body)
    assert pins, ("no counts[...] assertions found in %s - this test pins "
                  "them and must be updated with it" % BRIDGE_TEST.name)
    return pins


class SrcCensusMatchesEveryCopyOfItsPins(unittest.TestCase):
    """One measurement, compared against all three places it is written down."""

    @classmethod
    def setUpClass(cls):
        cls.measured = _measure()
        cls.report = _report_counts()
        cls.bridge = _bridge_test_pins()

    def test_the_src_package_is_readable_and_not_empty(self):
        self.assertGreaterEqual(
            len(_modules()), 30,
            "src/pirateforce_foundation looks unreadable or truncated; every "
            "census below would read zero and pass for the wrong reason")

    def test_the_verifiers_own_guards(self):
        for symbol, key in (
                ("SRC_ACTOR_ENTRY_SITES", "src_actor_entry_call_sites"),
                ("SRC_ACTOR_STREAM_SITES", "src_actor_stream_call_sites"),
                ("SRC_VITAL_STREAM_SITES", "src_vital_stream_call_sites"),
                ("SRC_MODULES_WITH_ACTOR_ENTRY",
                 "src_modules_building_actor_entries")):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    _guarded_int(symbol), self.measured[key],
                    "src/ measures %d for %s; the verifier's guard says "
                    "otherwise and would exit 1 on the bridge.  Modules: %s"
                    % (self.measured[key], key,
                       ", ".join(
                           self.measured.get(key + "_names")
                           or self.measured[
                               "src_modules_building_actor_entries_names"])))
        self.assertEqual(
            _guarded_module_names(),
            self.measured["src_modules_building_actor_entries_names"],
            "the verifier's named module census drifted from src/")

    def test_every_src_derived_number_in_the_report(self):
        for key, value in sorted(self.measured.items()):
            with self.subTest(key=key):
                self.assertIn(key, self.report,
                              "the report's RUNTIMERES_COUNTS block lost a key")
                self.assertEqual(
                    self.report[key], value,
                    "the report says %r for %s; src/ measures %r - re-pin the "
                    "report in the same commit that moved the code"
                    % (self.report[key], key, value))

    def test_the_bridge_only_test_module_is_pinned_too(self):
        """The copy the gate never runs is the copy that rotted.  Pin it here.

        Nothing else in a clone without the image reads these assertions, so
        without this test they can disagree with src/ for as long as nobody
        runs the full suite by hand - which is exactly what happened.
        """
        checked = 0
        for key, pinned in sorted(self.bridge.items()):
            if key not in self.measured:
                continue
            checked += 1
            with self.subTest(key=key):
                self.assertEqual(
                    pinned, self.measured[key],
                    "tests/test_runtimeres_actor_entry_static.py pins %r for "
                    "%s; src/ measures %r.  That module is excluded from the "
                    "gate's subset, so this is the only place the drift shows "
                    "before the bridge runs the full suite"
                    % (pinned, key, self.measured[key]))
        self.assertGreaterEqual(
            checked, 5,
            "expected to check at least 5 pins parsed out of %s; the parser "
            "found %d and may have gone blind" % (BRIDGE_TEST.name, checked))


class TheCensusCanActuallyFail(unittest.TestCase):
    """A pin that cannot be made to fail is a printout, not a pin."""

    def test_a_planted_call_site_moves_the_count(self):
        modules = _modules()
        before = _sites(ENTRY_PATTERN, modules)
        modules["zz_planted_for_this_test.py"] = (
            "entry = make_remote_actor_entry(actor)\n")
        self.assertEqual(_sites(ENTRY_PATTERN, modules), before + 1)

    def test_the_pin_readers_find_real_literals(self):
        self.assertGreater(_guarded_int("SRC_ACTOR_ENTRY_SITES"), 0)
        self.assertGreater(len(_guarded_module_names()), 0)
        self.assertGreater(len(_bridge_test_pins()), 0)

    def test_a_commented_out_guard_is_not_mistaken_for_the_live_one(self):
        source = TOOL.read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.lstrip().startswith("#") and "guard(SRC_" in line:
                self.fail(
                    "a retired guard is quoted in a comment (%r).  The pin "
                    "readers here anchor at the start of a line, so this is "
                    "safe today, but keep it that way." % line.strip()[:80])


class TheCodeTokenDiscriminatorHoldsUp(unittest.TestCase):
    """tools/pf_code_token_scan is what two NEGATIVE guards now rest on.

    It lives in the respawn verifier's module on the bridge and nowhere the
    gate can see, so these are the only tests it has.
    """

    STEMS = ("relive", "revive", "respawn")
    VALUES = (0x1AD4, 0x3DD6, 0x8B12)

    def scan(self, text):
        return pf_code_token_scan.scan(text, stems=self.STEMS,
                                       values=self.VALUES)

    def test_it_catches_every_shape_an_encoder_could_take(self):
        cases = {
            "def respawn_actor(x):\n    return x\n": (0, 1),
            "RELIVE_VITAL_ID = 0x1AD4\n": (1, 1),
            "wire = 6868\n": (1, 0),
            "wire = 6_868\n": (1, 0),
            'HANDLERS = {"ReliveVital": None}\n': (0, 1),
            'OPCODES = {"0x1AD4": None}\n': (1, 0),
            'OPCODES = {"6868": None}\n': (1, 0),
            'if verb == "Relive":\n    pass\n': (0, 1),
        }
        for source, expected in cases.items():
            with self.subTest(source=source.strip()[:40]):
                self.assertEqual(self.scan(source), expected)

    def test_it_ignores_prose_and_hash_literals(self):
        cases = (
            "# a respawned monster killed again is a NEW death\n",
            'MSG = "a respawned monster killed again is a NEW death"\n',
            'H = "524FEA50CFF0091A1C59F1C200F8188866537ACA060605C96868C88"\n',
            '"""player-chosen respawn scene, no persisted column"""\n',
        )
        for source in cases:
            with self.subTest(source=source.strip()[:40]):
                self.assertEqual(self.scan(source), (0, 0))

    def test_an_fstring_is_read_on_both_tokenizer_generations(self):
        """3.11 hands back one STRING; 3.12+ splits into FSTRING_* pieces.

        The bridge runs 3.14 and the runners do not, so a discriminator that
        only understood one of the two would answer differently per machine.
        """
        value, stem = self.scan('name = f"Relive{n}"\n')
        self.assertEqual((value, stem), (0, 1))

    def test_a_file_that_will_not_tokenize_reports_none_not_zero(self):
        """None is the caller's cue to fall back to the crude substring count.

        Returning 0 here would let a syntax error buy silence, which is the
        one thing a fail-closed negative must never allow.
        """
        self.assertIsNone(self.scan('x = """unterminated\n'))

    def test_the_scan_is_not_vacuous_on_the_real_tree(self):
        """It must find SOMETHING in a file known to carry the stems in prose.

        mob_loot.py holds three respawn sentences.  They are prose, so the code
        count is zero - but the raw count must not be, or the guard's second
        half is pinning a number that no longer measures anything.
        """
        text = (SRC_DIR / "mob_loot.py").read_text(encoding="utf-8")
        self.assertGreater(sum(text.count(t) for t in ("Respawn", "respawn")), 0)
        self.assertEqual(self.scan(text), (0, 0))


if __name__ == "__main__":
    unittest.main()
