"""No GMGlobal `say` byte may leave this server until identity is honest.

WHY THIS FILE EXISTS
--------------------
COO-DECISION 2026-08-29T00:41+07:00 (pf_bridge/notes_to_chief/
20260829_0041_COO-DECISION-say-gate-lock-is-official-and-gt016-goes-first.md),
answering this lane's own ASK (20260828_2351_LANE-GM-ASK-COO-who-may-open-the-
say-gate.md), ruled that:

* conditions (A) per-connection identity and (B) the client-observable screen
  are an OFFICIAL LOCK on `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED`,
  at the same rank as `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED`;
* the constant stays `None`, and only a NEW COO-DECISION may change that --
  "not a round of the lane that wants the byte";
* RE-132 answering `0` does NOT open it, because "a correct byte does not mean
  the sender is who we think"; and
* this lane must write the enforcing test in its own suite.

That last instruction is why the assertions live here and not only in
`tests/test_gm_say_action.py`.  A lock the owning lane can lift in the same
commit that wants the byte is not a lock -- COO's words, agreeing with this
lane's own ASK.  The file that holds the rule has to be a separate artefact
whose whole reason for existing is the rule, so deleting it is a visible act.

WHAT THE ForcePos LOCK LEARNED, APPLIED HERE
--------------------------------------------
`tests/test_gm_force_pos_version_lock.py`'s first version guarded a NAME, and
pf-adversary walked four senders through it.  The lesson: the order is about
BYTES LEAVING THE SERVER, not about one constant's spelling.  So this file
does not stop at `assertIsNone`.  It also asks, over the lane's own zone:

1. is every `say` frame composed inside a function that reads the gate?
2. does anything compose a GMGlobal frame WITHOUT going through `say_wire` at
   all -- by reaching the shared channel codec directly?
3. does anything read the RE-132 static pin as if it were the gate?

All three ask about RESOLVED names, not spellings at the call site, and that
is not a refinement -- it is the finding that broke this file's first version.
pf-adversary reached the codec as `make_channel_message_response as _compose`
and every check passed while a real frame got composed with no gate anywhere
near it.  See `_alias_map`.  Check 2 is now enforced at the IMPORT as well as
the call, because the import is the one place the module's name has to appear
in full; three further probes (the composer under an alias, the codec under a
module alias, and `importlib.import_module` by string) were run against the
repaired file and all three go red.

Question 2 is the one that matters most here, and it is where `say` differs
from `ForcePos` in kind.  A ForcePos frame needs the locked version byte as an
ARGUMENT, so a literal-argument scan catches a bypass.  A `say` frame needs
nothing from the gate at all: `channel_message_hypothesis.make_channel_message_
response` already hardcodes the correct byte for every channel on serializer
0x65AD40.  Anyone in this zone can therefore compose a byte-perfect,
version-correct GMGlobal frame and never mention the locked constant.  The
gate is a POLICY CHECK standing beside the composer, not an ingredient of it --
which is exactly the shape that rots quietly.  Hence check 2.

WHY THE SCAN STOPS AT THIS LANE'S ZONE
---------------------------------------
COO's instruction is explicit: "do not let the test touch files outside the
lane's zone, so that someone else's PR does not go red on something they
cannot fix."  So the walk below covers `src/pirateforce_foundation/gm/` and
nothing else, and that boundary is a real limit, stated rather than implied:

* Every route from a typed `/say` to composed bytes lives in this zone today
  (`gm/chat_command_action.py` -> `gm/say_wire.py` -> the imported codec), so
  the lock covers the whole `say` feature as it exists.
* It does NOT cover another lane composing a channel message for its own
  feature.  That is that lane's decision on its own vital, not a bypass of
  this gate, and a red here would be a red they could not fix.
* `channel_message_hypothesis.py` itself is deliberately out of scope: it is
  another lane's proven work, this lane may not write to it, and it composed
  channel frames long before this gate existed.

WHAT THIS FILE DOES NOT CLAIM
------------------------------
* It does not stop bytes hand-rolled with `struct.pack` that never touch the
  composer or the codec.  It closes the routes an engineer would take.
* It does not claim the client draws a GMGlobal line.  RE-132 established that
  the handler is not a no-op -- it routes, reads the body at object+0x18 and
  calls a display sink -- which REMOVED the cheapest way (B) could fail, at the
  static rung.  Nobody has seen a line render.  GT-016 (which COO moved ahead
  of GT-133 in the same decision) is what decides (B).
* A nested function returned from a gated function and called elsewhere would
  satisfy check 1.  Named so the next reader does not have to discover it.

RELEASE DAY NEEDS THREE FILES, NOT ONE
---------------------------------------
`say_wire.py`'s own release-day note said release day edits ONE test, "because
this lane owns say_wire.py's suite outright and did not need a separate lock
file for it."  COO's decision is precisely the thing that made that sentence
false; it is corrected in `say_wire.py` in the same commit that adds this file.
Whoever lifts the lock -- with a NEW COO-DECISION in hand, and nothing less --
edits:

  1. `src/pirateforce_foundation/gm/say_wire.py`      (the constant)
  2. `tests/test_gm_say_action.py`                    (SayVersionGateTests, two
     unconditional `assertIsNone`s)
  3. `tests/test_gm_say_gate_lock.py`                 (this file)

and cites the new decision in all three.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import say_wire  # noqa: E402

# The decision that locked the constant. Asserted, not merely written above:
# COO asked for the citation to be part of the test, and a citation nothing
# checks is the kind that gets lost in a reformat -- which is how the lane
# lost a rule twice before (see test_gm_force_pos_version_lock.py's header).
LOCKING_DECISION = (
    "20260829_0041_COO-DECISION-say-gate-lock-is-official-and-gt016-goes-first"
)

# This lane's zone. The scan does not leave it, on COO's instruction -- but it
# must cover ALL of it, and the first version did not.
#
# !! pf-adversary (round `xk4wmz`, probe G) put an ungated `say` composer in
# `lane_hooks/lane_gm_chat_command.py` -- a file this lane OWNS (addendum G:
# the lane owns `lane_hooks/lane_<x>_*.py`) but which does not live under
# `gm/`. The whole suite stayed green, 4054 passed, while a lane-GM module
# composed GMGlobal frames with no gate anywhere near them. "This lane's zone"
# is not one directory; it is every file this lane may write to, and the scan
# has to mean the second thing. `lane_hooks/lane_gm_*.py` is added by GLOB, so
# a third lane-GM hook module is covered the day it appears rather than the day
# someone remembers this list.
_GM_PACKAGE = REPO_ROOT / "src" / "pirateforce_foundation" / "gm"
_LANE_HOOKS = REPO_ROOT / "src" / "pirateforce_foundation" / "lane_hooks"

# The one function that turns a parsed `say` into GMGlobal frame bytes.
SAY_COMPOSER = "make_say_broadcast_frame"
SAY_COMPOSER_HOME = "src/pirateforce_foundation/gm/say_wire.py"

# The gate a composer call must stand behind.
GATE_NAME = "GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED"

# The RE-132 measurement. A record, never a switch -- say_wire.py's own comment
# says it "is NEVER read by chat_command_action._say_action", and this is the
# check that makes that sentence cost something to break.
STATIC_PIN = "GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC"

# The shared channel codec. Calling any of these composes a real frame on
# serializer 0x65AD40 with the correct version byte already baked in, so a call
# from anywhere in this zone except `say_wire.py` is a second composition route
# that the gate does not stand in front of.
CODEC_ENTRY_POINTS = {
    "make_channel_message_response",
    "encode_channel_message",
    "encode_channel_message_payload",
}

# The module those live in. Checked at the IMPORT, not at the call -- see
# `_alias_map`'s docstring for the probe that made this necessary.
CODEC_MODULE = "channel_message_hypothesis"


def _zone_sources() -> list[pathlib.Path]:
    """Every .py in this lane's zone, tracked or not.

    A filesystem walk rather than `git ls-files`: a brand-new module nobody has
    `git add`ed yet is the likeliest place a first ungated sender appears, and
    the ForcePos lock found that out on itself.
    """
    found = {p for p in _GM_PACKAGE.rglob("*.py") if p.is_file()}
    found |= {p for p in _LANE_HOOKS.glob("lane_gm_*.py") if p.is_file()}
    return sorted(found)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _parse(path: pathlib.Path) -> ast.Module | None:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError:
        return None


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _alias_map(tree: ast.Module) -> dict[str, str]:
    """Local binding -> the name it was imported under.

    !! THIS FUNCTION EXISTS BECAUSE THE FIRST VERSION OF THIS FILE WAS BROKEN
    BY IT.  pf-adversary (round `xk4wmz`, probe B) dropped a module into this
    zone that reached the shared codec as

        from ..channel_message_hypothesis import (
            make_channel_message_response as _compose,
        )

    and called `_compose(legacy, _CHANNEL, speaker, text)`.  Every check in
    this file went green while that module composed a byte-perfect,
    version-correct GMGlobal frame that never mentioned the gate -- because
    the checks matched the spelling AT THE CALL SITE, and the call site said
    `_compose`.  Matching a call by its local name is matching a nickname.
    """
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                out[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out[alias.asname or alias.name.split(".")[0]] = alias.name
    return out


def _resolved_call_name(node: ast.Call, aliases: dict[str, str]) -> str:
    name = _called_name(node)
    return aliases.get(name, name)


def _touches_codec_module(tree: ast.Module) -> list[str]:
    """Ways this module could get its hands on the shared channel codec.

    Import-level, not call-level, and that is the point: to reach the codec a
    module has to name it SOMEWHERE, and the import is the one place an alias
    cannot hide it -- `... import make_channel_message_response as _compose`
    still spells the module out. Renaming the imported function is free;
    renaming the module it comes from is not.
    """
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and CODEC_MODULE in node.module:
                hits.append("line %d: from %s import ..." % (node.lineno, node.module))
            elif node.module is None or CODEC_MODULE not in (node.module or ""):
                for alias in node.names:
                    if alias.name == CODEC_MODULE:
                        hits.append(
                            "line %d: from ... import %s" % (node.lineno, alias.name)
                        )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if CODEC_MODULE in alias.name:
                    hits.append("line %d: import %s" % (node.lineno, alias.name))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # importlib.import_module("...channel_message_hypothesis") and
            # friends. A string is not proof of a dynamic import, but in this
            # zone there is no innocent reason to spell the codec module's
            # name and not be talking to it -- say_wire.py, which legitimately
            # discusses it in prose, is exempted by the caller.
            if CODEC_MODULE in node.value:
                hits.append("line %d: names the module in a string" % node.lineno)
    return hits


def _reads(tree: ast.AST, wanted: str) -> bool:
    """Does this subtree LOAD `wanted`, as a bare name or an attribute?

    Both spellings are live in this zone: `say_wire.py` would say `GATE`, while
    `chat_command_action.py` says `say_wire.GATE`. A check that saw only one of
    them would be satisfied by rewriting an import.
    """
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == wanted
            and not isinstance(node.ctx, ast.Store)
        ):
            return True
        if (
            isinstance(node, ast.Attribute)
            and node.attr == wanted
            and not isinstance(node.ctx, ast.Store)
        ):
            return True
    return False


def _functions_containing(tree: ast.Module, target: ast.AST) -> list[ast.AST]:
    """Every function whose body lexically contains `target`."""
    holders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(piece is target for piece in ast.walk(node)):
            holders.append(node)
    return holders


class GateIsShutTests(unittest.TestCase):
    def test_the_shipped_constant_is_none_and_only_coo_may_change_that(self):
        self.assertIsNone(
            say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED,
            "say_wire.%s was changed from None. COO-DECISION %s made this an "
            "OFFICIAL LOCK: it may be lifted by a NEW COO-DECISION and by "
            "nothing else -- explicitly not by a round of the lane that wants "
            "the byte, which is this lane. RE-132 answering 0 does not lift it "
            "either; the decision says so in as many words, because a correct "
            "byte does not make the sender who we think he is. What is still "
            "open is (A): every connection on this server shares the "
            "process-wide --token CLI value (runtime.py's IDENTITY, STATED "
            "HONESTLY comment), so opening this gate hands /say to whoever "
            "connects and the gm_accounts allowlist cannot tell two humans "
            "apart. Revert the constant, or land the decision that permits it."
            % (GATE_NAME, LOCKING_DECISION),
        )

    def test_this_file_names_the_decision_that_locked_the_constant(self):
        # COO asked for two things: the assertion above, and a header that
        # cites the decision. This is the second one, checked rather than
        # trusted -- the citation IS the lock's provenance, and a lock whose
        # provenance can be reformatted away is back to being a sentence.
        self.assertIn(LOCKING_DECISION, __doc__ or "")

    def test_the_identity_blocker_still_exists_to_be_cited(self):
        # (A) is the reason the gate is shut. If the anchor text ever leaves
        # runtime.py, either identity got fixed -- in which case this lane
        # takes the news to COO and asks for the unlock decision -- or the
        # citation rotted and every "why the gate is shut" paragraph in this
        # lane is now unsourced. Read-only, and it asserts the blocker is
        # PRESENT, so it cannot redden another lane's PR for adding anything.
        source = (
            REPO_ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8", errors="surrogateescape")
        self.assertIn("IDENTITY, STATED HONESTLY", source)


class NoUnGatedComposerTests(unittest.TestCase):
    def test_every_say_frame_composed_in_this_zone_stands_behind_the_gate(self):
        offenders = []
        for path in _zone_sources():
            tree = _parse(path)
            if tree is None:
                continue
            defines_it = any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == SAY_COMPOSER
                for node in ast.walk(tree)
            )
            if defines_it:
                # say_wire.py composes on demand; it is the tool, not the
                # policy. The gate stands at the caller, by design -- see this
                # module's header on why the gate is not an ingredient.
                continue
            aliases = _alias_map(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if _resolved_call_name(node, aliases) != SAY_COMPOSER:
                    continue
                holders = _functions_containing(tree, node)
                if not any(_reads(holder, GATE_NAME) for holder in holders):
                    offenders.append("%s:%d" % (_rel(path), node.lineno))
        self.assertEqual(
            offenders,
            [],
            "A module in this lane's zone composes a GMGlobal `say` frame "
            "without any enclosing function reading %s: %s. The gate is a "
            "policy check standing BESIDE the composer, not an ingredient of "
            "it -- %s needs nothing from the locked constant, because the "
            "imported codec already hardcodes the right version byte. So a "
            "composer call that does not consult the gate silently opens it. "
            "Read the constant and return None when it is None, the way "
            "gm/chat_command_action.py::_say_action does."
            % (GATE_NAME, ", ".join(offenders), SAY_COMPOSER),
        )

    def test_the_scan_still_sees_the_real_call_site(self):
        # Round `z6gu2n` learned this the expensive way on the ForcePos lock:
        # when the guarded call site moved, every check stayed green while the
        # repo could no longer compose a frame at all. A tripwire that a green
        # loop over zero call sites satisfies is not a tripwire, so name the
        # site and let a move be a deliberate edit here.
        seen = []
        for path in _zone_sources():
            tree = _parse(path)
            if tree is None:
                continue
            aliases = _alias_map(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and (
                    _resolved_call_name(node, aliases) == SAY_COMPOSER
                ):
                    seen.append(_rel(path))
        self.assertIn(
            "src/pirateforce_foundation/gm/chat_command_action.py",
            seen,
            "Nothing in this zone composes a `say` frame any more, so the gate "
            "check above is a loop over nothing. Either the composition site "
            "moved (point this assertion at the new one) or the `say` action "
            "path is gone (then the lock guards nothing, and that is the "
            "finding, not a passing test). Sites seen: %s" % sorted(set(seen)),
        )

    def test_the_zone_walk_is_actually_finding_files(self):
        # The cheapest way for all of the above to become decorative: the
        # package moves and every scan loops over an empty list.
        sources = [_rel(p) for p in _zone_sources()]
        self.assertGreater(len(sources), 10, sources)
        self.assertIn(SAY_COMPOSER_HOME, sources)
        # Both halves of the zone, so dropping either glob is loud rather than
        # a quietly smaller scan -- which is exactly how probe G got in.
        self.assertIn(
            "src/pirateforce_foundation/lane_hooks/lane_gm_chat_command.py",
            sources,
            "The lane_hooks half of this lane's zone is not being scanned. A "
            "lane-GM hook module can compose `say` frames as easily as a "
            "module under gm/, and pf-adversary demonstrated exactly that. "
            "Scanned: %s" % sources,
        )


class NoSecondCompositionRouteTests(unittest.TestCase):
    def test_only_say_wire_may_call_the_shared_channel_codec(self):
        offenders = []
        for path in _zone_sources():
            if _rel(path) == SAY_COMPOSER_HOME:
                continue
            tree = _parse(path)
            if tree is None:
                continue
            aliases = _alias_map(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = _resolved_call_name(node, aliases)
                if name in CODEC_ENTRY_POINTS:
                    offenders.append(
                        "%s:%d calls %s" % (_rel(path), node.lineno, name)
                    )
            for hit in _touches_codec_module(tree):
                offenders.append("%s %s" % (_rel(path), hit))
        self.assertEqual(
            offenders,
            [],
            "A module in this lane's zone other than %s calls the shared "
            "channel codec directly: %s. That composes a version-correct "
            "GMGlobal frame while walking around both the composer and the "
            "gate in front of it -- the codec hardcodes the byte, so nothing "
            "in such a call has to mention the locked constant for the bytes "
            "to be right. It is also the retracted second-codec mistake in a "
            "new shape (rounds/GM_20260827_1415_broadcast-wire-attempted-and-"
            "retracted.md): one adapter for this vital, in one file, behind "
            "one gate. Route through %s."
            % (SAY_COMPOSER_HOME, ", ".join(offenders), SAY_COMPOSER),
        )

    def test_the_codec_names_being_scanned_are_the_ones_say_wire_uses(self):
        # If the codec is renamed upstream, the scan above goes green against a
        # set of names nothing calls any more. Anchor it to the real import.
        tree = _parse(REPO_ROOT / SAY_COMPOSER_HOME)
        self.assertIsNotNone(tree)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and (
                "channel_message_hypothesis" in node.module
            ):
                imported |= {alias.name for alias in node.names}
        self.assertTrue(
            imported & CODEC_ENTRY_POINTS,
            "say_wire.py no longer imports any name this file scans for. The "
            "codec entry points were renamed or the import moved; update "
            "CODEC_ENTRY_POINTS. Imported: %s" % sorted(imported),
        )


class StaticPinIsNotASwitchTests(unittest.TestCase):
    def test_the_re132_pin_is_written_at_home_and_read_nowhere_in_the_zone(self):
        loads = []
        stores = []
        for path in _zone_sources():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == STATIC_PIN:
                    where = "%s:%d" % (_rel(path), node.lineno)
                    if isinstance(node.ctx, ast.Store):
                        stores.append(where)
                        if _rel(path) != SAY_COMPOSER_HOME:
                            loads.append("%s (assigned outside its home)" % where)
                    else:
                        loads.append(where)
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == STATIC_PIN
                    and not isinstance(node.ctx, ast.Store)
                ):
                    loads.append("%s:%d reads .%s" % (_rel(path), node.lineno, STATIC_PIN))
        self.assertEqual(
            loads,
            [],
            "A module in this lane's zone reads %s: %s. That name records what "
            "RE-132 MEASURED (the byte is 0); it is not permission to send. "
            "Two different questions were deliberately given two different "
            "constants -- 'what byte does the client write?' (answered) and "
            "'may this server put those bytes on a socket?' (locked by COO) -- "
            "and a send path that reads the record instead of the gate makes "
            "the lock decorative without editing the locked line. "
            "say_wire.py's own comment promises this never happens; this is "
            "the check that makes breaking the promise cost something."
            % (STATIC_PIN, ", ".join(loads)),
        )
        self.assertEqual(
            len(stores),
            1,
            "Expected the pin assigned exactly once, in %s; found %s"
            % (SAY_COMPOSER_HOME, stores),
        )
        self.assertTrue(
            stores[0].startswith(SAY_COMPOSER_HOME + ":"),
            "The pin is assigned somewhere other than its home file: %s. A "
            "second assignment is a second answer to a question RE-132 already "
            "settled once." % stores,
        )

    def test_the_pin_still_holds_the_value_the_result_letter_reported(self):
        # Provenance: notes_to_chief/20260829_0010_RE-132-RESULT-VERSION-ZERO-
        # RENDER-PATH.md, consumed by this lane in round `z6gu2n`. Pinned here
        # as well as in test_gm_say_action.py because THIS file is the one that
        # argues "the byte is not what is blocking"; if the byte ever stops
        # being the codec's byte, that argument changes and the lock's reasoning
        # has to be rewritten, not just its value.
        self.assertEqual(say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC, 0)
        self.assertEqual(
            say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_RE132_STATIC,
            say_wire.CHANNEL_CODEC_VITAL_VERSION,
        )


if __name__ == "__main__":
    unittest.main()
