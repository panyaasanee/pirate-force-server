"""gm/lane_gate_name_audit.py: the lane_hooks strings nothing else checks.

Two halves, and they are graded differently ON PURPOSE:

* The HOOK POINT half is asserted repository-wide, because it is clean
  today and every future violation would be in the file of whoever wrote
  it.
* The GATE NAME half is asserted on everything EXCEPT a finding
  attributable to another lane's existing module.  It is not clean
  repository-wide: ``runtime.py:5887`` carries the live LANE-B defect this
  module was written from, that file is chief's, and chief's fix is in
  flight.  See ``gate_findings_in_lane_gm_scope``'s own docstring for why
  the rule is "not another lane's" rather than "starts with lane_gm_".

Most of the cases below were written from pf-adversary's review of this
file's first draft (round `lx4yib`, nine defects).  Each such test says
which one it closes, because a case whose reason is forgotten is a case a
later round deletes.
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.gm import lane_gate_name_audit as audit  # noqa: E402

#: Every synthetic tree needs a file that really imports the package, or
#: nothing in it resolves -- which is the D2 fix working.
IMPORT_LINE = "from pirateforce_foundation import lane_hooks\n"


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


class _TempTree:
    """A throwaway source tree.  Plain unittest, like the rest of this lane."""

    def __enter__(self) -> Path:
        import tempfile

        self._dir = tempfile.TemporaryDirectory()
        return Path(self._dir.name).resolve()

    def __exit__(self, *exc: object) -> None:
        self._dir.cleanup()


class _RootedAt:
    """Point the module's own audit root at a tree, then put it back.

    Rebinding the module constant rather than passing a root into the
    finding functions is deliberate.  The finding functions take no
    arguments so that a mutant which empties AUDIT_ROOT reds the
    non-vacuity tests; an argument would move that mutant to the caller,
    which is the remedy pf-adversary rejected from this lane in round
    `0ymgul`.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def __enter__(self) -> None:
        self._saved = audit.AUDIT_ROOT
        audit.AUDIT_ROOT = self._root

    def __exit__(self, *exc: object) -> None:
        audit.AUDIT_ROOT = self._saved


class _HooksDirAt:
    """Point the audit's lane_hooks directory at a throwaway one.

    So that a test needing a lane module ON DISK that the live registry has
    never heard of -- the import-failure state, and the package shape -- does
    not have to write an importable, `production_allowed = True` module into
    the production package to get it.  The first version of those two tests
    did exactly that, with an `rmdir` cleanup that raises the moment anything
    imports the file (pf-adversary, second pass, measured: the directory and
    its `__pycache__` survived the run).
    """

    def __init__(self, directory: Path) -> None:
        self._dir = directory

    def __enter__(self) -> None:
        self._saved = audit.LANE_HOOKS_DIR
        audit.LANE_HOOKS_DIR = self._dir

    def __exit__(self, *exc: object) -> None:
        audit.LANE_HOOKS_DIR = self._saved


class ClassifierTests(unittest.TestCase):
    """Every combination of the four facts, so no branch rests on the repo."""

    def test_every_fact_combination_has_the_verdict_the_docstring_claims(self):
        # (literal answer, stem answer, file exists, declares allowed)
        cases = {
            # THE RESOLVER WINS.  pf-adversary D1: the first draft asked the
            # filesystem first, so a lane module shipped as a PACKAGE (which
            # pkgutil.iter_modules discovers happily) had a WORKING gate
            # reported as "names no module", and this lane's own asserted
            # test went red over a call site that worked.
            (True, True, True, True): None,
            (True, True, True, False): None,
            (True, True, False, False): None,
            (True, False, False, False): None,
            (True, False, True, False): None,
            (True, True, False, True): None,
            (True, False, False, True): None,
            (True, False, True, True): None,
            # The runtime.py:5887 shape.
            (False, True, True, True): audit.FINDING_SPELLING_UNREACHABLE,
            (False, True, True, False): audit.FINDING_SPELLING_UNREACHABLE,
            (False, True, False, False): audit.FINDING_SPELLING_UNREACHABLE,
            (False, True, False, True): audit.FINDING_SPELLING_UNREACHABLE,
            # Nothing on disk under that name.
            (False, False, False, False): audit.FINDING_NAMES_NO_MODULE,
            (False, False, False, True): audit.FINDING_NAMES_NO_MODULE,
            # pf-adversary D7: the module SAYS it is allowed and the registry
            # refuses it under both spellings -- it never reached the
            # registry (an import failure `_discover` prints once and
            # forgets).  The first draft reported this as nothing at all.
            (False, False, True, True): (
                audit.FINDING_DECLARED_ALLOWED_BUT_UNREGISTERED
            ),
            # A module whose production_allowed is genuinely off.  A
            # decision, not a defect.
            (False, False, True, False): None,
        }
        self.assertEqual(len(cases), 16, "all four facts must be enumerated")
        for facts, expected in cases.items():
            literal_answer, stem_answer, exists, declares = facts
            with self.subTest(facts=facts):
                self.assertEqual(
                    audit._classify_gate_literal(
                        resolver_answers_for_literal=literal_answer,
                        resolver_answers_for_stem=stem_answer,
                        module_file_exists=exists,
                        module_declares_allowed=declares,
                    ),
                    expected,
                )


class ResolutionTests(unittest.TestCase):
    """pf-adversary D2/D3: matched through the imports, not by name."""

    def test_a_call_whose_argument_is_on_a_later_line_is_still_found(self):
        # THE FALSE ALARM THIS TEST EXISTS FOR.  Drafting this module, this
        # lane grepped for `fire(\s*"..."` and concluded LANE-GM's own
        # `vital_inbound_gm_run_command` hook was dead.  It is not: the real
        # call at runtime.py:7613 puts `lane_hooks.fire(` and the point name
        # on different lines.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + textwrap.dedent(
                    '''
                    def handle():
                        lane_hooks.fire(
                            "vital_inbound_gm_run_command",
                            session=None,
                        )
                    '''
                ),
            )
            scan = audit.scan_sources(root)
        self.assertEqual(
            [site.literal for site in scan.fire_calls],
            ["vital_inbound_gm_run_command"],
        )

    def test_an_unrelated_fire_in_a_file_that_never_imported_lane_hooks(self):
        # D2 scenario A, measured on the first draft: a
        # `cannon.fire("vital_inbound_gm_run_command")` in an unrelated
        # module made a genuinely dead LANE-GM hook report clean.  On a
        # pirate-ship server `fire` is a more ordinary word than `hook`.
        with _TempTree() as root:
            _write(
                root,
                "cannon_demo.py",
                'cannon.fire("vital_inbound_gm_run_command")\n',
            )
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_gm_run_command")\n'
                "def _on_thing():\n"
                "    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
                scan = audit.scan_sources(root)
        self.assertEqual(scan.fire_calls, ())
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_HOOK_POINT_NEVER_FIRED]
        )

    def test_an_unrelated_zero_argument_fire_does_not_disarm_the_half(self):
        # D2 scenario B: `def broadside(cannon): cannon.fire()` disarmed the
        # entire hook half of the first draft and reddened another lane's
        # file with a message about hook points.
        with _TempTree() as root:
            _write(root, "cannon_demo.py", "def broadside(c):\n    c.fire()\n")
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n"
                "    pass\n",
            )
            _write(
                root,
                "runtime.py",
                IMPORT_LINE + 'lane_hooks.fire("vital_inbound_one")\n',
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(findings, ())

    def test_an_unrelated_fire_in_a_file_that_DOES_import_lane_hooks(self):
        # The harder half of D2, and the one the early "this file imports
        # nothing" shortcut does not cover: `runtime.py` genuinely imports
        # lane_hooks, so a `cannon.fire(...)` in THAT file is reached by the
        # walker and has to be rejected by resolution instead.  Without this
        # case, mutating `_resolves_to` to match any attribute call by name
        # left the suite green.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'lane_hooks.fire("vital_inbound_one")\n'
                + 'cannon.fire("vital_inbound_two")\n'
                + 'cannon.module_production_allowed("lane_gm_no_such")\n',
            )
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n    pass\n",
            )
            with _RootedAt(root):
                scan = audit.scan_sources(root)
                findings = audit.dead_hook_point_findings()
                gate = audit.gate_name_findings()
        self.assertEqual([s.literal for s in scan.fire_calls], ["vital_inbound_one"])
        self.assertEqual(scan.gate_calls, ())
        self.assertEqual(findings, ())
        self.assertEqual(gate, ())

    def test_a_module_level_alias_of_the_package_is_followed(self):
        # pf-adversary, second pass: `_lh = lane_hooks` then
        # `_lh.module_production_allowed("lane_hooks.lane_gm_chat_command")`
        # killed the chat gate while every test here passed.  An alias is a
        # binding; the walker reads assignments to a fixpoint now.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "_lh = lane_hooks\n"
                + "_lh2 = _lh\n"
                + "_lh2.module_production_allowed"
                '("lane_hooks.lane_gm_chat_command")\n',
            )
            with _RootedAt(root):
                findings = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_SPELLING_UNREACHABLE]
        )

    def test_a_deeper_attribute_ending_in_the_package_name_is_not_a_call(self):
        # pf-adversary, second pass: matching the LAST dotted segment made
        # `self.config.lane_hooks.fire("not_a_point")` a hook registration.
        # A binding has to match whole.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'self.config.lane_hooks.fire("not_a_point")\n'
                + 'cannon.lane_hooks.module_production_allowed("lane_gm_no")\n',
            )
            with _RootedAt(root):
                scan = audit.scan_sources(root)
        self.assertEqual(scan.fire_calls, ())
        self.assertEqual(scan.gate_calls, ())

    def test_a_lane_shipped_as_a_package_is_inside_the_package(self):
        # pf-adversary, second pass: `lane_hooks/lane_x_big/__init__.py` has
        # parent `lane_x_big`, so its hooks AND its declaration were both
        # invisible -- the flagship defect hiding in the one shape D1's own
        # fix had just established as real.
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_gm_big/__init__.py",
                "from .. import hook\n"
                'registered_but_not_fired = ("vital_declared",)\n'
                '@hook("vital_declared")\n'
                "def _on_declared():\n    pass\n"
                '@hook("vital_dead")\n'
                "def _on_dead():\n    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [(f.kind, f.site.literal) for f in findings],
            [(audit.FINDING_HOOK_POINT_NEVER_FIRED, "vital_dead")],
        )

    def test_the_keyword_spelling_of_a_point_is_a_literal_not_a_refusal(self):
        # D3: `fire(point=...)` is what the signature offers, and the real
        # call already passes session=/payload= by keyword.  The first draft
        # asserted that a plain string literal was not a string literal, and
        # refused the whole half on it.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'lane_hooks.fire(point="vital_inbound_one", session=None)\n',
            )
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                "from . import hook\n"
                '@hook(point="vital_inbound_one")\n'
                "def _on_one():\n"
                "    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
                scan = audit.scan_sources(root)
        self.assertEqual([s.literal for s in scan.fire_calls], ["vital_inbound_one"])
        self.assertEqual(findings, ())

    def test_the_import_spellings_this_repository_actually_uses(self):
        for spelling, call in (
            (
                "from pirateforce_foundation import lane_hooks",
                'lane_hooks.module_production_allowed("lane_q_one")',
            ),
            (
                "import pirateforce_foundation.lane_hooks",
                "pirateforce_foundation.lane_hooks."
                'module_production_allowed("lane_q_one")',
            ),
            (
                "import pirateforce_foundation.lane_hooks as lh",
                'lh.module_production_allowed("lane_q_one")',
            ),
            (
                "from pirateforce_foundation.lane_hooks import "
                "module_production_allowed",
                'module_production_allowed("lane_q_one")',
            ),
        ):
            with self.subTest(spelling=spelling):
                with _TempTree() as root:
                    _write(root, "a.py", f"{spelling}\n{call}\n")
                    scan = audit.scan_sources(root)
                self.assertEqual(
                    [site.literal for site in scan.gate_calls], ["lane_q_one"]
                )

    def test_a_bare_gate_call_with_no_import_resolves_to_nothing(self):
        with _TempTree() as root:
            _write(root, "a.py", 'module_production_allowed("lane_q_one")\n')
            scan = audit.scan_sources(root)
        self.assertEqual(scan.gate_calls, ())

    def test_a_relative_from_dot_import_inside_the_package_binds_hook(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                'from . import hook\n@hook("vital_inbound_thing")\n'
                "def _on_thing():\n    pass\n",
            )
            scan = audit.scan_sources(root)
        self.assertEqual(
            [site.literal for site in scan.hook_registrations],
            ["vital_inbound_thing"],
        )

    def test_a_from_dot_import_outside_the_package_binds_nothing(self):
        with _TempTree() as root:
            _write(
                root,
                "elsewhere/thing.py",
                'from . import hook\n@hook("vital_inbound_thing")\n'
                "def _on_thing():\n    pass\n",
            )
            scan = audit.scan_sources(root)
        self.assertEqual(scan.hook_registrations, ())

    def test_a_non_literal_argument_is_kept_as_a_site_with_no_literal(self):
        with _TempTree() as root:
            _write(
                root,
                "a.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed(composer.module)\n",
            )
            scan = audit.scan_sources(root)
        self.assertEqual([site.literal for site in scan.gate_calls], [None])

    def test_a_file_that_does_not_parse_does_not_take_the_audit_down(self):
        with _TempTree() as root:
            _write(root, "broken.py", "def (:\n")
            _write(
                root,
                "good.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_q_one")\n',
            )
            scan = audit.scan_sources(root)
        self.assertEqual([site.literal for site in scan.gate_calls], ["lane_q_one"])

    def test_the_attribute_names_this_audit_follows_are_on_the_real_package(self):
        # pf-adversary's closing question: what makes this module's own
        # coupling to lane_hooks any better than the two it audits?  The
        # calls are matched through the import graph now, and the three
        # attribute names are pinned against the live package here -- so a
        # rename in lane_hooks reds this audit instead of leaving it
        # quietly auditing nothing.
        for name in (
            audit.GATE_FUNCTION_NAME,
            audit.HOOK_DECORATOR_NAME,
            audit.FIRE_FUNCTION_NAME,
        ):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(lane_hooks, name)))
        self.assertEqual(
            audit.LANE_HOOKS_PACKAGE, lane_hooks.__name__.rsplit(".", 1)[-1]
        )

    def test_the_keyword_names_this_audit_reads_are_the_live_parameters(self):
        # pf-adversary, second pass, D10: only the three ATTRIBUTE names were
        # pinned, so a parameter rename in `fire()` would silently degrade
        # every keyword call to "dynamic point" -- the audit refusing the
        # whole half with no rename signal anywhere.
        import inspect

        self.assertIn(
            audit.POINT_KEYWORD,
            inspect.signature(lane_hooks.fire).parameters,
        )
        self.assertIn(
            audit.POINT_KEYWORD,
            inspect.signature(lane_hooks.hook).parameters,
        )
        self.assertIn(
            audit.GATE_KEYWORD,
            inspect.signature(lane_hooks.module_production_allowed).parameters,
        )

    def test_the_production_flag_name_is_the_one_lane_hooks_reads(self):
        from pirateforce_foundation.lane_hooks import lane_gm_chat_command

        self.assertTrue(
            hasattr(lane_gm_chat_command, audit.PRODUCTION_FLAG_NAME)
        )
        self.assertIn(
            audit.PRODUCTION_FLAG_NAME,
            Path(lane_hooks.__file__).read_text(encoding="utf-8"),
        )


class SourceListingTests(unittest.TestCase):
    def test_a_file_git_has_never_seen_is_audited_anyway(self):
        # THIS REVERSES A DECISION ONE DRAFT OLD, and the reversal is the
        # point.  pf-adversary's first pass was right that an untracked
        # scratch file can move the verdict, and this module switched to
        # `git ls-files`.  Its second pass measured the bill: the subprocess
        # output decoded with the console codec raises UnicodeDecodeError on
        # the bridge's cp874 console for any non-ASCII tracked path, escaping
        # every `except` in the walker; and asking "is this a checkout" needs
        # a skipTest whose reason the gate census then carries undeclared
        # (measured: `UNDECLARED SKIP ... RESULT: FAIL, census exit=1`).
        #
        # The deciding argument is neither of those.  An audit's dangerous
        # failure is a FALSE NEGATIVE, and this lane has already reached that
        # conclusion once, in test_gm_say_gate_lock.py, which walks the disk
        # alone because "a brand-new module nobody has git added yet is the
        # likeliest place a first ungated sender appears".  The graded
        # verdict is still the tracked one: the gate runs on a clean
        # checkout, where the two sets are identical.
        import subprocess

        with _TempTree() as root:
            init = subprocess.run(
                ["git", "init", "-q", str(root)], capture_output=True
            )
            _write(
                root,
                "brand_new.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_zz_brand_new")\n',
            )
            seen = {site.literal for site in audit.scan_sources(root).gate_calls}
        self.assertIn("lane_zz_brand_new", seen)
        self.assertEqual(init.returncode, 0, "git init failed; the case above "
                         "still measured what it claims, since the walk never "
                         "asks git anything")

    def test_a_tree_that_is_not_a_checkout_falls_back_to_the_disk(self):
        with _TempTree() as root:
            _write(
                root,
                "a.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_q_one")\n',
            )
            scan = audit.scan_sources(root)
        self.assertEqual([site.literal for site in scan.gate_calls], ["lane_q_one"])

    def test_a_source_file_saved_in_cp874_is_audited_not_dropped(self):
        # pf-adversary, second pass: identical text, two encodings.  A
        # Windows editor save with one Thai comment made this lane's OWN
        # 5887-shaped defect invisible -- `read_text(encoding="utf-8")` threw
        # UnicodeDecodeError and the walker's `except ... continue` swallowed
        # the whole file, counting and naming nothing.
        with _TempTree() as root:
            source = (
                IMPORT_LINE
                + "# ทดสอบ\n"
                + 'lane_hooks.module_production_allowed'
                '("lane_hooks.lane_gm_chat_command")\n'
            )
            (root / "runtime.py").write_bytes(source.encode("cp874"))
            with _RootedAt(root):
                findings = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_SPELLING_UNREACHABLE]
        )

    def test_a_rewritten_file_is_rescanned_not_served_from_the_cache(self):
        # The scan cache is keyed on the tree's own (path, mtime, size)
        # fingerprint precisely so this holds.  A cache keyed on the root
        # path alone would serve the first answer forever, and every
        # synthetic case in this file that reuses a root would be measuring
        # a stale tree.
        with _TempTree() as root:
            target = _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_q_first")\n',
            )
            first = {s.literal for s in audit.scan_sources(root).gate_calls}
            target.write_text(
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_q_second")\n'
                + "# a second line, so the size moves too\n",
                encoding="utf-8",
            )
            second = {s.literal for s in audit.scan_sources(root).gate_calls}
        self.assertEqual(first, {"lane_q_first"})
        self.assertEqual(second, {"lane_q_second"})

    def test_the_tests_directory_is_not_audited(self):
        with _TempTree() as root:
            _write(
                root,
                "tests/test_thing.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_gm_deliberate")\n',
            )
            scan = audit.scan_sources(root)
        self.assertEqual(scan.gate_calls, ())


class DeadHookPointTests(unittest.TestCase):
    def test_the_repository_registers_no_hook_point_that_nothing_fires(self):
        self.assertEqual(
            [finding.line() for finding in audit.dead_hook_point_findings()], []
        )

    def test_the_repository_scan_is_not_vacuously_clean(self):
        scan = audit.scan_sources(audit.AUDIT_ROOT)
        self.assertGreaterEqual(len(scan.hook_registrations), 2)
        self.assertGreaterEqual(len(scan.fire_calls), 1)
        self.assertGreaterEqual(len(scan.gate_calls), 2)

    def test_the_one_never_fired_point_in_the_tree_is_declared_by_its_lane(self):
        # The audit found a real registered-never-fired point on its first
        # run: LANE-GM's own `vital_inbound_chat_local_talk`, whose fire()
        # left runtime.py when CORE-REQUEST-GM-029 replaced the hook route
        # with a direct call.  It is an owner's decision with a written
        # rationale, so it is DECLARED in the lane's own file.
        #
        # This asserts LANE-GM's declaration is present and where it belongs.
        # It deliberately does NOT assert that no other lane declares one:
        # pf-adversary (D9) measured that the first draft's version of this
        # test reddened LANE-GM's file when LANE-B used the mechanism exactly
        # as advertised.
        declared = {
            (site.path, site.literal)
            for site in audit.scan_sources(audit.AUDIT_ROOT)
            .never_fired_declarations
        }
        self.assertIn(
            (
                "src/pirateforce_foundation/lane_hooks/lane_gm_chat_command.py",
                "vital_inbound_chat_local_talk",
            ),
            declared,
        )

    def test_a_declaration_for_a_point_that_is_fired_is_reported_stale(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                'registered_but_not_fired = ("vital_inbound_thing",)\n'
                '@hook("vital_inbound_thing")\n'
                "def _on_thing():\n    pass\n",
            )
            _write(
                root,
                "runtime.py",
                IMPORT_LINE + 'lane_hooks.fire("vital_inbound_thing")\n',
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [f.kind for f in findings],
            [audit.FINDING_STALE_NEVER_FIRED_DECLARATION],
        )
        self.assertIn("fired in this tree", findings[0].detail)

    def test_a_declaration_for_a_point_no_hook_registers_is_reported_stale(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                'registered_but_not_fired = ("vital_inbound_gone",)\n',
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [f.kind for f in findings],
            [audit.FINDING_STALE_NEVER_FIRED_DECLARATION],
        )
        self.assertIn("registered by no hook", findings[0].detail)

    def test_a_declaration_does_not_silence_another_module(self):
        # pf-adversary D4, scenario A: the first draft keyed `declared` on
        # the point name alone, so LANE-GM appending a name to its own tuple
        # silenced LANE-B's dead hook in LANE-B's file.
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                'registered_but_not_fired = ("vital_mob_tick",)\n'
                'registered_but_not_fired_placeholder = None\n',
            )
            _write(
                root,
                "lane_hooks/lane_b_thing.py",
                "from . import hook\n"
                '@hook("vital_mob_tick")\n'
                "def _on_tick():\n    pass\n",
            )
            with _RootedAt(root):
                kinds = sorted(f.kind for f in audit.dead_hook_point_findings())
        self.assertEqual(
            kinds,
            sorted(
                [
                    # LANE-B's hook is still dead...
                    audit.FINDING_HOOK_POINT_NEVER_FIRED,
                    # ...and LANE-GM's declaration is stale, because its own
                    # module registers nothing.
                    audit.FINDING_STALE_NEVER_FIRED_DECLARATION,
                ]
            ),
        )

    def test_another_module_registering_a_declared_point_is_still_reported(self):
        # D4 scenario B: lane_hooks/__init__.py leaves cross-lane
        # registration open.  A second lane registering an already-declared
        # point got silenced by the first draft's global set.
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                "from . import hook\n"
                'registered_but_not_fired = ("vital_inbound_chat",)\n'
                '@hook("vital_inbound_chat")\n'
                "def _on_chat():\n    pass\n",
            )
            _write(
                root,
                "lane_hooks/lane_b_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_chat")\n'
                "def _also_on_chat():\n    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [(f.kind, f.site.path) for f in findings],
            [
                (
                    audit.FINDING_HOOK_POINT_NEVER_FIRED,
                    "lane_hooks/lane_b_thing.py",
                )
            ],
        )

    def test_a_declaring_module_that_stops_registering_is_reported(self):
        # D4 scenario C: the promised inverse.  With another module also
        # registering the point, the first draft's global `registered` set
        # kept the stale guard asleep.
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_gm_thing.py",
                'registered_but_not_fired = ("vital_inbound_chat",)\n',
            )
            _write(
                root,
                "lane_hooks/lane_b_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_chat")\n'
                "def _on_chat():\n    pass\n",
            )
            with _RootedAt(root):
                kinds = sorted(f.kind for f in audit.dead_hook_point_findings())
        self.assertIn(audit.FINDING_STALE_NEVER_FIRED_DECLARATION, kinds)

    def test_a_declaration_that_holds_silences_exactly_one_point(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                'registered_but_not_fired = ("vital_inbound_one",)\n'
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n    pass\n"
                '@hook("vital_inbound_two")\n'
                "def _on_two():\n    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [(f.kind, f.site.literal) for f in findings],
            [(audit.FINDING_HOOK_POINT_NEVER_FIRED, "vital_inbound_two")],
        )

    def test_an_unreadable_declaration_silences_nothing_and_says_so(self):
        for value in ("POINTS", "()", '["a", VARIABLE]'):
            with self.subTest(value=value):
                with _TempTree() as root:
                    _write(
                        root,
                        "lane_hooks/lane_x_thing.py",
                        "from . import hook\n"
                        f"registered_but_not_fired = {value}\n"
                        '@hook("vital_inbound_one")\n'
                        "def _on_one():\n    pass\n",
                    )
                    with _RootedAt(root):
                        findings = audit.dead_hook_point_findings()
                self.assertEqual(
                    sorted(f.kind for f in findings),
                    sorted(
                        [
                            audit.FINDING_UNREADABLE_DECLARATION,
                            audit.FINDING_HOOK_POINT_NEVER_FIRED,
                        ]
                    ),
                )

    def test_a_declaration_hidden_inside_a_function_does_not_silence(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                "def _setup():\n"
                '    registered_but_not_fired = ("vital_inbound_one",)\n'
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_HOOK_POINT_NEVER_FIRED]
        )

    def test_a_declaration_outside_the_package_does_not_silence(self):
        with _TempTree() as root:
            _write(
                root,
                "elsewhere.py",
                'registered_but_not_fired = ("vital_inbound_one",)\n',
            )
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n    pass\n",
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_HOOK_POINT_NEVER_FIRED]
        )

    def test_one_dynamic_point_name_makes_the_whole_half_refuse(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                '@hook("vital_inbound_never_fired")\n'
                "def _on_thing():\n    pass\n",
            )
            _write(
                root, "runtime.py", IMPORT_LINE + "lane_hooks.fire(POINT_NAME)\n"
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            {f.kind for f in findings}, {audit.FINDING_UNDECIDABLE_DYNAMIC_POINT}
        )

    def test_a_dynamic_point_does_not_swallow_an_unreadable_declaration(self):
        with _TempTree() as root:
            _write(
                root,
                "lane_hooks/lane_x_thing.py",
                "from . import hook\n"
                "registered_but_not_fired = POINTS\n"
                '@hook("vital_inbound_one")\n'
                "def _on_one():\n    pass\n",
            )
            _write(
                root, "runtime.py", IMPORT_LINE + "lane_hooks.fire(POINT_NAME)\n"
            )
            with _RootedAt(root):
                findings = audit.dead_hook_point_findings()
        self.assertEqual(
            sorted({f.kind for f in findings}),
            sorted(
                [
                    audit.FINDING_UNDECIDABLE_DYNAMIC_POINT,
                    audit.FINDING_UNREADABLE_DECLARATION,
                ]
            ),
        )


class GateScopeTests(unittest.TestCase):
    def test_no_gate_name_in_this_lanes_scope_reaches_a_missing_key(self):
        # THE PERMANENT ASSERTION OF THIS FILE.  runtime.py:6911 reads
        # module_production_allowed("lane_gm_chat_command") before it
        # composes anything on the 0xAC52 chat route.
        findings = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.line() for f in findings],
            [],
            "THE FIX BELONGS IN THE FILE AND LINE EACH FINDING NAMES, not in "
            "this test.  A gate literal that reaches no registry key is a "
            "feature that is off and cannot be switched on; correct the "
            "spelling at the call site, or -- if the module really is gone -- "
            "delete the call site with it.  A finding carrying another lane's "
            "known prefix should never appear here; if one does, that is a "
            "defect in gate_findings_in_lane_gm_scope and belongs in "
            "pf_bridge notes_to_chief as a letter to LANE-GM, not a deletion.",
        )

    def test_the_asserted_subset_covers_the_gate_the_chat_route_reads(self):
        # pf-adversary D5: hoist runtime.py:6911's literal into a module
        # constant and the chat gate dies, the subset empties, and every
        # test here still passes.  The first fix pinned this NON-EMPTY, and
        # the second pass measured that non-emptiness is not coverage: add
        # one healthy `lane_gm_run_command` literal elsewhere, requalify the
        # chat one behind an alias, and the pin was satisfied by the wrong
        # literal while the chat gate answered False.  It names the literal
        # now.
        #
        # This DOES couple to runtime.py:6911's spelling.  That is the
        # intent: a legitimate refactor there reds this and a human decides,
        # which is the whole subject of this file.
        self.assertIn("lane_gm_chat_command", audit.lane_gm_gate_literals())

    def test_the_literal_pin_reads_the_tree_rather_than_a_constant(self):
        # Without this, the assertion above is satisfied by a function that
        # returns the expected name unconditionally -- a mutant that survived
        # until this case existed.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_gm_other")\n',
            )
            with _RootedAt(root):
                literals = audit.lane_gm_gate_literals()
        self.assertEqual(literals, ("lane_gm_other",))

    def test_another_lanes_typo_is_reported_but_not_asserted_here(self):
        # pf-adversary, second pass, the sharpest finding of it: the scope
        # rule required the named module to EXIST, and NAMES_NO_MODULE is
        # emitted only when it does not -- so no such finding could ever be
        # attributed to another lane, and one character in chief's file
        # (`lane_b_mob_ai_ticks`) reddened THIS lane's test file.  A lane
        # whose test file reds for another lane's typo has no answer to
        # "whose file do I edit", and the next round answers it by deleting
        # the assertion.
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed"
                '("lane_b_mob_ai_ticks")\n',
            )
            with _RootedAt(root):
                reported = audit.gate_name_findings()
                asserted = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in reported], [audit.FINDING_NAMES_NO_MODULE]
        )
        self.assertEqual(asserted, ())

    def test_the_known_lane_prefixes_are_derived_from_the_real_directory(self):
        prefixes = audit.known_lane_prefixes()
        self.assertIn("lane_gm_", prefixes)
        self.assertIn("lane_a_", prefixes)
        self.assertIn("lane_b_", prefixes)
        self.assertTrue(
            all(p.startswith("lane_") and p.endswith("_") for p in prefixes)
        )
        # DERIVED, not typed.  A hardcoded list is the failure mode here:
        # a prefix nobody owns would silently EXCLUDE that name from this
        # lane's assertion, which is how a typo gets attributed to a lane
        # that does not exist.
        self.assertNotIn("lane_c_", prefixes)
        self.assertNotIn("lane_zz_", prefixes)

    def test_the_live_repository_finding_is_the_one_this_module_was_written_for(
        self,
    ):
        # Reporting-only, and asserted as a SHAPE rather than a count: this
        # must not go red when chief repairs runtime.py:5887.  What it does
        # pin is that every repository-wide finding today is attributable to
        # another lane -- i.e. exactly the reason the asserted subset above
        # is a subset.
        for finding in audit.gate_name_findings():
            with self.subTest(finding=finding.line()):
                self.assertTrue(
                    audit._owned_by_another_lane(
                        audit._stem(finding.site.literal or "")
                    ),
                    "a gate finding appeared that this lane must act on; "
                    "the asserted subset above should have caught it",
                )

    def test_a_gate_name_with_the_5887_spelling_is_reported(self):
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed"
                '("lane_hooks.lane_gm_chat_command")\n',
            )
            with _RootedAt(root):
                findings = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in findings], [audit.FINDING_SPELLING_UNREACHABLE]
        )

    def test_a_misspelled_prefix_is_inside_the_asserted_subset(self):
        # pf-adversary D8: the first draft scoped on startswith("lane_gm_"),
        # so every way of MISSPELLING the prefix escaped the assertion --
        # protecting the spelling that was already right.
        for literal in (
            "lanegm_chat_command",
            "lane_gmchat_command",
            "Lane_GM_chat_command",
            "lane_gm_chat_command.py",
        ):
            with self.subTest(literal=literal):
                with _TempTree() as root:
                    _write(
                        root,
                        "runtime.py",
                        IMPORT_LINE
                        + "lane_hooks.module_production_allowed"
                        f'("{literal}")\n',
                    )
                    with _RootedAt(root):
                        findings = audit.gate_findings_in_lane_gm_scope()
                self.assertEqual(
                    [f.kind for f in findings], [audit.FINDING_NAMES_NO_MODULE]
                )

    def test_another_lanes_existing_module_is_reported_but_not_asserted(self):
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed"
                '("lane_hooks.lane_b_mob_ai_tick")\n',
            )
            with _RootedAt(root):
                reported = audit.gate_name_findings()
                asserted = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in reported], [audit.FINDING_SPELLING_UNREACHABLE]
        )
        self.assertEqual(asserted, ())

    def test_a_module_whose_flag_is_off_is_not_a_finding(self):
        # lane_a_choose_npc_scene1 declares production_allowed False today
        # and is withdrawn at discovery.  A call site naming it correctly
        # gets the answer the flag means.
        self.assertFalse(
            lane_hooks.module_production_allowed("lane_a_choose_npc_scene1")
        )
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed"
                '("lane_a_choose_npc_scene1")\n',
            )
            with _RootedAt(root):
                findings = audit.gate_name_findings()
        self.assertEqual(findings, ())

    def test_the_audit_reads_the_real_resolver_not_a_rule_of_its_own(self):
        # The discriminator this module rests on, measured against the live
        # package rather than asserted in prose.
        self.assertTrue(lane_hooks.module_production_allowed("lane_gm_chat_command"))
        self.assertFalse(
            lane_hooks.module_production_allowed("lane_hooks.lane_gm_chat_command")
        )

    def test_unauditable_sites_are_named_rather_than_counted_as_clean(self):
        sites = audit.unauditable_gate_call_sites()
        self.assertTrue(sites)
        self.assertTrue(all(site.literal is None for site in sites))


class ProductionFlagReadingTests(unittest.TestCase):
    """The D7 fact, read from source because an unimportable module is the
    state it answers a question about."""

    def test_the_flag_is_read_the_way_lane_hooks_reads_it(self):
        for source, expected in (
            ("production_allowed = True\n", True),
            ("production_allowed = 1\n", True),
            ("production_allowed = False\n", False),
            ("production_allowed = 0\n", False),
            ("production_allowed: bool = True\n", True),
            ("", False),
            ("production_allowed = SOME_NAME\n", False),
            # pf-adversary, second pass: reading the FIRST assignment turned
            # the way a lane is actually switched off in a hurry into an
            # accusation that the registry was refusing an allowed module,
            # and it reddened this lane's own assertion.  An import binds
            # the LAST one.
            (
                "production_allowed = True\n"
                "# INCIDENT: switched off until the crash is understood.\n"
                "production_allowed = False\n",
                False,
            ),
            ("production_allowed = False\nproduction_allowed = True\n", True),
            ("def f():\n    production_allowed = True\n", False),
            ("def (:\n", False),
        ):
            with self.subTest(source=source):
                self.assertIs(
                    audit._declares_production_allowed(source), expected
                )

    def test_the_live_lane_gm_modules_declare_the_flag(self):
        for stem in ("lane_gm_chat_command", "lane_gm_run_command"):
            with self.subTest(stem=stem):
                source = audit._module_source(stem)
                self.assertIsNotNone(source)
                self.assertTrue(audit._declares_production_allowed(source))

    def test_the_import_failure_finding_is_reachable_on_real_facts(self):
        # pf-adversary asked whether the D7 branch is a shape nothing can
        # produce.  It is not: a lane module that exists on disk and
        # declares the flag, while the registry has no key for it, is
        # exactly what an import failure leaves behind -- `_discover()`
        # prints IMPORT_FAILED once and records nothing.  Built here from
        # the real directory and the real resolver, not from a fact table.
        with _TempTree() as hooks_root:
            (hooks_root / "lane_gm_probe_import_fail").mkdir()
            (hooks_root / "lane_gm_probe_import_fail" / "__init__.py").write_text(
                "production_allowed = True\n", encoding="utf-8"
            )
            with _HooksDirAt(hooks_root):
                self._measure_import_failure_finding()

    def _measure_import_failure_finding(self):
        self.assertFalse(
            lane_hooks.module_production_allowed("lane_gm_probe_import_fail")
        )
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + "lane_hooks.module_production_allowed"
                '("lane_gm_probe_import_fail")\n',
            )
            with _RootedAt(root):
                findings = audit.gate_findings_in_lane_gm_scope()
        self.assertEqual(
            [f.kind for f in findings],
            [audit.FINDING_DECLARED_ALLOWED_BUT_UNREGISTERED],
        )

    def test_a_lane_module_shipped_as_a_package_is_found(self):
        # The D1 shape, at the layer that reads it: pkgutil.iter_modules
        # discovers packages, so `_module_source` has to see one.
        # NOT IN THE LIVE PACKAGE.  The first version of this test wrote an
        # importable `production_allowed = True` module into
        # src/.../lane_hooks/ and cleaned up with `rmdir`, which raises
        # `Directory not empty` the moment anything imports it and leaves a
        # permanent lane module behind (pf-adversary, second pass, measured).
        with _TempTree() as hooks_root:
            (hooks_root / "lane_gm_probe_pkg").mkdir()
            (hooks_root / "lane_gm_probe_pkg" / "__init__.py").write_text(
                "production_allowed = True\n", encoding="utf-8"
            )
            with _HooksDirAt(hooks_root):
                self.assertEqual(
                    audit._module_source("lane_gm_probe_pkg"),
                    "production_allowed = True\n",
                )


class ReportTests(unittest.TestCase):
    def test_the_report_line_carries_kind_location_and_detail(self):
        with _TempTree() as root:
            _write(
                root,
                "runtime.py",
                IMPORT_LINE
                + 'lane_hooks.module_production_allowed("lane_gm_no_such")\n',
            )
            with _RootedAt(root):
                report = audit.audit_report()
        self.assertEqual(len(report), 1)
        self.assertIn(audit.FINDING_NAMES_NO_MODULE, report[0])
        self.assertIn("runtime.py:2", report[0])
        self.assertIn("lane_gm_no_such", report[0])

    def test_nothing_in_the_module_writes_to_a_stream(self):
        # COO 0846: a console token needs a consumer.  This audit's consumer
        # is this file, so it must not write to a screen.  Checked as
        # substrings over the whole text rather than line starts: the first
        # draft's version walked past `sys.stdout.write` and past a `print`
        # that was not first on its line (pf-adversary D9).
        #
        # AST, not substrings.  The substring version this replaces went red
        # on `_fingerprint(` -- which contains `print(` -- so a helper's NAME
        # could fail a test about behaviour, and the obvious "fix" would have
        # been to rename the helper rather than to fix the check.
        import ast as _ast

        tree = _ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
        offenders = []
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name):
                if node.func.id == "print":
                    offenders.append(f"print at line {node.lineno}")
            if isinstance(node, _ast.Attribute) and node.attr in (
                "stdout",
                "stderr",
            ):
                value = node.value
                if isinstance(value, _ast.Name) and value.id == "sys":
                    offenders.append(f"sys.{node.attr} at line {node.lineno}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
