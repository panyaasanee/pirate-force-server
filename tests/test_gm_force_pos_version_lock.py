"""No ForcePos byte may leave this server until the write point that pairs with it exists.

WHY THIS FILE EXISTS (a rule that was held by a sentence, twice, and lost)
--------------------------------------------------------------------------
RE-129 answered on 2026-08-28T20:09+07:00: the `ForcePos` (0x0E80) vital
version byte is 0, read straight out of the prototype constructor
(`mov byte ptr [eax+0x10],cl` after `xor ecx,ecx`, 0x005E5186) and compared by
the generic reader with exact equality (0x005F3EFC). That is the answer this
lane had been blocked on for two days, and the obvious next move -- set
`teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED = 0` and let warps fly -- is
exactly the move COO forbade three hours later.

COO-DECISION 2026-08-28T21:30+07:00 (pf_bridge/notes_to_chief/
20260828_2130_COO-DECISION-position-ownership-after-gm-warp.md) ruled that the
owner of a character's position is the position the CLIENT confirmed, that the
server must never write a position it did not observe, and that the confirming
event is the first `TargetPos` after the frame. It then locked this lane: do
not change `FORCE_POS_VITAL_VERSION_CONFIRMED` from None until that confirmed
write point is on `main` -- EVEN THOUGH RE-129 has already answered.

WHAT THE FIRST VERSION OF THIS FILE GOT WRONG (pf-adversary, round `fo2lgh`)
----------------------------------------------------------------------------
It guarded a NAME. COO's order is about BYTES. The adversary put four working
bypasses through it, each with all five tests green:

* a one-line `# TODO(GM-030): GM_WARP_POSITION_CONFIRMED ...` comment in
  `runtime.py` satisfied the "write point exists" check -- a substring search
  cannot tell a write point from a note saying there is none;
* a sender added to `teleport_wire.py` ITSELF, the one file the inertness
  check skipped;
* a sender anywhere at all passing a literal `0` -- the version byte is not a
  secret any more, so nothing needs to mention the locked constant to send;
* a sender in `lane_hooks/__init__.py` and in a brand-new untracked file,
  neither of which the file set covered.

So the checks below are AST-based and ask about frames, not spelling:

1. The `runtime.py` write point must be a string CONSTANT INSIDE A CALL
   (`print(...)`, `events.append(...)`) -- a comment is invisible to the AST,
   and a docstring is not a call argument.
2. NO shipped module under `src/` may call a ForcePos/Teleport frame builder
   with a LITERAL version. The byte must come from the gated constant, so that
   turning the constant off turns every sender off with it.
3. The two `*_PROVEN_BY_RE129` records may be WRITTEN in their home file and
   READ nowhere in `src/` -- including their home file, which is where the
   adversary's second bypass lived.
4. No ForcePos/Teleport builder may default its `vital_version`, checked over
   every function `teleport_wire`/`warp_executor` expose rather than a
   hand-written list of four.

The file set is the union of `git ls-files` and a filesystem walk, so a new
file is covered before anyone remembers to `git add` it.

ENFORCED IN ONE DIRECTION ONLY, DELIBERATELY
---------------------------------------------
Landing the write point does NOT force the constant on. Lifting the lock is
COO's call, not a mechanical consequence of a grep.

!! RELEASE DAY NEEDS TWO FILES, NOT ONE. `tests/test_gm_chat_command_action.py`
::VersionGateTests::test_the_shipped_constant_is_still_none_so_no_bytes_can_go_out
asserts `assertIsNone` UNCONDITIONALLY and predates this file. Whoever lifts
the lock must edit that test too, or get three unexplained reds. It is named
here because the adversary found the release sequence documented in
`teleport_wire.py` and `docs/GM_LANE.md` did not mention it at all.

WHAT IT DOES NOT CLAIM
----------------------
* It does not stop a send composed by hand from `struct.pack` without touching
  either builder. It closes the routes an engineer would actually take, not
  every route that exists -- and it says so instead of implying otherwise.
* Nothing here says a version-correct ForcePos frame will move a character.
  RE-129 also measured that the handler the client has REGISTERED for ForcePos
  is the complete body [0x00710440,0x00710445) = `mov al,1; ret 4`: no payload
  read, no position write. The version byte was necessary, not sufficient, and
  GT-128 remains the only thing that can decide the on-screen half.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import teleport_wire, warp_executor  # noqa: E402

# The token CORE-REQUEST-GM-030 asks chief to put at the confirmed write site
# in runtime.py, in the same screaming-snake ASCII style as every other console
# token in this lane (LANE_GM_CHAT_ACTION, GM_UPDATE_STATE_AFTER_LOGIN). It is
# a literal here so that renaming it on either side goes red rather than silent.
CONFIRMED_WRITE_POINT_TOKEN = "GM_WARP_POSITION_CONFIRMED"

SRC_ROOT = REPO_ROOT / "src"
RUNTIME_PY = SRC_ROOT / "pirateforce_foundation" / "runtime.py"

# The two names that record RE-129's measurement without acting on it. They may
# be assigned in their home file and read nowhere: a record is not a switch.
RECORD_NAMES = (
    "FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129",
    "TELEPORT_VITAL_VERSION_PROVEN_BY_RE129",
)
RECORD_HOME = "src/pirateforce_foundation/gm/teleport_wire.py"

# Frame builders whose second argument is the version byte. A call to any of
# them is how a ForcePos or Teleport frame gets composed in this project.
# The `_with_body`/`_with_target` pair are the same two builders returning one
# extra value (round `z6gu2n`, so `runtime.py` can compare a durable row
# against where the warp actually sent the connection).  They are listed here
# for the reason the tripwire below exists: when `make_warp_force_pos_frame`
# was rewritten to delegate to `make_warp_force_pos_frame_with_target`, the
# scan's only remaining shipped `make_force_pos_frame` call site moved -- so a
# literal version passed to the NEW name would have walked straight through
# COO's lock while every test here stayed green.
VERSION_TAKING_BUILDERS = {
    "make_force_pos_frame": 1,
    "make_force_pos_frame_with_body": 1,
    "make_cwarp_result_frame": 1,
    "make_teleport_vital_frame": 1,
    "make_warp_force_pos_frame": 1,
    "make_warp_force_pos_frame_with_target": 1,
}


def _git_ls_files() -> list[str] | None:
    """Tracked .py paths under src/, or None when git cannot answer."""
    try:
        done = subprocess.run(
            ("git", "ls-files", "-z", "--", "src"),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
        )
    except (OSError, ValueError):
        # No git binary at all (subprocess raises FileNotFoundError, it does
        # not return a code). The first version of this file promised None
        # here and delivered an error instead; the walk below covers this case
        # on its own, so a missing git costs nothing.
        return None
    if done.returncode != 0:
        # git present, tree is not a repository -- an sdist, a vendored copy, a
        # tarball export. Same answer: fall back to the walk.
        return None
    return [p for p in done.stdout.split("\0") if p.endswith(".py")]


def _shipped_sources() -> list[pathlib.Path]:
    """Every shipped .py under src/: tracked, untracked and not-yet-added.

    The union matters. `git ls-files` cannot see a file nobody has `git add`ed
    -- and a brand-new module is the likeliest place for a first sender to
    appear, as this round proved on itself.
    """
    found = {p.resolve() for p in SRC_ROOT.rglob("*.py")}
    tracked = _git_ls_files()
    if tracked is not None:
        found |= {(REPO_ROOT / rel).resolve() for rel in tracked}
    return sorted(p for p in found if p.is_file())


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


def _version_argument(node: ast.Call, index: int) -> ast.expr | None:
    for keyword in node.keywords:
        if keyword.arg == "vital_version":
            return keyword.value
    if len(node.args) > index:
        return node.args[index]
    return None


class ConfirmedWritePointTests(unittest.TestCase):
    def test_the_switch_may_only_be_on_when_runtime_really_writes(self):
        confirmed = teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED
        if confirmed is None:
            return
        tree = _parse(RUNTIME_PY)
        self.assertIsNotNone(tree, "runtime.py did not parse: %s" % RUNTIME_PY)
        live = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for piece in ast.walk(node):
                if (
                    isinstance(piece, ast.Constant)
                    and isinstance(piece.value, str)
                    and CONFIRMED_WRITE_POINT_TOKEN in piece.value
                ):
                    live = True
                    break
            if live:
                break
        self.assertTrue(
            live,
            "FORCE_POS_VITAL_VERSION_CONFIRMED was changed from None to %r, but "
            "runtime.py has no live %s -- the token must appear as a string "
            "passed to a call (print(...) / events.append(...)), which is what "
            "CORE-REQUEST-GM-030 asks chief for. A comment or a docstring "
            "mentioning it does not count: pf-adversary satisfied the earlier "
            "substring version of this check with a one-line TODO saying the "
            "write point did NOT exist. COO-DECISION 2026-08-28T21:30+07:00 "
            "locks this constant at None until the confirmed-position write "
            "point is real: a ForcePos frame is a request, and the server must "
            "never write a position it did not observe. Send warps now and the "
            "client stands at the new point while the durable row keeps the "
            "old one -- aggro range, pickup range and the logout point all "
            "follow the row. Revert the constant, or land the write point."
            % (confirmed, CONFIRMED_WRITE_POINT_TOKEN),
        )


class NoLiteralVersionReachesAFrameTests(unittest.TestCase):
    def test_no_shipped_module_composes_a_frame_with_a_literal_version(self):
        offenders = []
        for path in _shipped_sources():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                index = VERSION_TAKING_BUILDERS.get(_called_name(node))
                if index is None:
                    continue
                argument = _version_argument(node, index)
                if isinstance(argument, ast.Constant) and isinstance(
                    argument.value, (int, float)
                ):
                    offenders.append(
                        "%s:%d passes %r" % (_rel(path), node.lineno, argument.value)
                    )
        self.assertEqual(
            offenders,
            [],
            "A shipped module composes a ForcePos/Teleport frame with a LITERAL "
            "version byte: %s. That puts a version-correct frame on the wire "
            "without ever mentioning FORCE_POS_VITAL_VERSION_CONFIRMED, so "
            "turning the constant off would not turn the sender off -- which is "
            "the whole property COO's lock exists to hold (the order is about "
            "bytes leaving the server, not about one name). RE-129 published the "
            "byte, so knowing it is not permission to send it. Pass the gated "
            "constant and refuse when it is None, the way "
            "gm/chat_command_action.py does." % ", ".join(offenders),
        )

    def test_the_scan_actually_sees_the_calls_it_claims_to_check(self):
        # Without this, a moved package or a renamed builder turns the suite
        # above into a green loop over zero call sites.
        sources = _shipped_sources()
        self.assertGreater(len(sources), 20, sources)
        self.assertIn(RECORD_HOME, [_rel(p) for p in sources])
        seen = set()
        cross_module = set()
        for path in sources:
            tree = _parse(path)
            if tree is None:
                continue
            defined_here = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = _called_name(node)
                    if name in VERSION_TAKING_BUILDERS:
                        seen.add(name)
                        if name not in defined_here:
                            # A call from a module that does not define the
                            # builder: a real composition site, not a
                            # back-compat wrapper delegating to its neighbour.
                            cross_module.add((_rel(path), name))
        self.assertIn("make_force_pos_frame_with_body", seen, sorted(seen))
        self.assertIn("make_warp_force_pos_frame_with_target", seen, sorted(seen))
        # !! THE ASSERTION ABOVE IS NOT ENOUGH ON ITS OWN, and this round found
        # that out the expensive way.  When `make_warp_force_pos_frame` was
        # rewritten to delegate, both names became reachable from inside their
        # OWN defining modules -- so pf-adversary deleted the only production
        # ForcePos composition site in `gm/chat_command_action.py`, replaced it
        # with `raise RuntimeError`, and this file still went green: the scan
        # was satisfied by two wrappers calling their neighbours.  A tripwire
        # that a delegation can satisfy is not a tripwire.  What the lock needs
        # to know is that a REAL caller still composes ForcePos frames, so the
        # check below counts only calls made from a module that does not define
        # the builder it calls.
        self.assertIn(
            ("src/pirateforce_foundation/gm/chat_command_action.py",
             "make_warp_force_pos_frame_with_target"),
            cross_module,
            "No shipped module OUTSIDE the composers themselves builds a "
            "ForcePos frame any more, so the literal-version scan above is a "
            "green loop over wrappers. Either the production call site moved "
            "(point this assertion at the new one) or it is gone (then COO's "
            "lock is guarding nothing and that is the finding). Call sites "
            "seen: %s" % sorted(cross_module),
        )


class RecordsAreInertTests(unittest.TestCase):
    def test_the_records_are_written_at_home_and_read_nowhere(self):
        loads = []
        stores = []
        for path in _shipped_sources():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Name) or node.id not in RECORD_NAMES:
                    continue
                where = "%s:%d %s" % (_rel(path), node.lineno, node.id)
                if isinstance(node.ctx, ast.Store):
                    stores.append(where)
                else:
                    loads.append(where)
                if isinstance(node.ctx, ast.Store) and _rel(path) != RECORD_HOME:
                    loads.append("%s (assigned outside its home file)" % where)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr in RECORD_NAMES
                    and not isinstance(node.ctx, ast.Store)
                ):
                    loads.append(
                        "%s:%d reads .%s" % (_rel(path), node.lineno, node.attr)
                    )
        self.assertEqual(
            loads,
            [],
            "A shipped module READS a *_PROVEN_BY_RE129 record: %s. Those names "
            "are a record of what RE-129 measured, not a switch. The only "
            "constant a send may gate on is FORCE_POS_VITAL_VERSION_CONFIRMED, "
            "which COO has locked at None; reading the record to build or gate a "
            "frame routes around the lock without changing the locked line. "
            "pf-adversary did exactly this inside teleport_wire.py itself, which "
            "an earlier version of this check skipped." % ", ".join(loads),
        )
        self.assertEqual(
            len(stores),
            len(RECORD_NAMES),
            "Expected each record assigned exactly once, in %s; found %s"
            % (RECORD_HOME, stores),
        )


class RecordedValuesTests(unittest.TestCase):
    def test_the_recorded_re129_values_are_what_the_result_letter_says(self):
        # Provenance for both: notes_to_chief/20260828_2009_RE-129-RESULT-
        # VERSION-ZERO-HANDLER-NOOP.md, T1 (ForcePos constructor writes 0 at
        # 0x005E5186) and T3 (TeleportVital constructor writes 4 at 0x005E5425).
        self.assertEqual(teleport_wire.FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129, 0)
        self.assertEqual(teleport_wire.TELEPORT_VITAL_VERSION_PROVEN_BY_RE129, 4)

    def test_the_two_recorded_values_are_different_measurements(self):
        # Guards the one-line mistake that would make the pair meaningless: if
        # both ever read the same value, the "there is no project-wide default"
        # argument that keeps every send gated stops being demonstrated by them.
        self.assertNotEqual(
            teleport_wire.FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129,
            teleport_wire.TELEPORT_VITAL_VERSION_PROVEN_BY_RE129,
        )


class NoBuilderDefaultsItsVersionTests(unittest.TestCase):
    def test_every_public_builder_makes_the_caller_say_the_byte_out_loud(self):
        # Every callable the two modules expose, not a hand-written list of
        # four: a make_force_pos_frame_v2 added tomorrow is covered the day it
        # appears. A default is a guess with a polite name, and GT-101 measured
        # what an unproven version does to a real client (modal error,
        # connection halted, socket closed).
        checked = 0
        for module in (teleport_wire, warp_executor):
            for name, func in vars(module).items():
                if name.startswith("_") or not inspect.isfunction(func):
                    continue
                if getattr(func, "__module__", None) != module.__name__:
                    continue
                parameter = inspect.signature(func).parameters.get("vital_version")
                if parameter is None:
                    continue
                checked += 1
                self.assertIs(
                    parameter.default,
                    inspect.Parameter.empty,
                    "%s.%s gained a default vital_version."
                    % (module.__name__, name),
                )
        self.assertGreaterEqual(checked, len(VERSION_TAKING_BUILDERS), checked)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
