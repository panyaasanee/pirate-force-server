"""`ConsumeResult.cause`: WHY a login's staged scene was refused.

Asked for by chief in `CHIEF-REPLY` 2026-08-29T15:16+07:00 item 5.  Their
console line had to print `cause=not_carried_by_the_outcome` because
`CONSUME_FAILED` is one word covering ~~seven~~ every fault below, and the
remedies those faults need are not the same remedy: "fix a line in a config
file" and "restart the server so it re-reads the registry" send an operator
to opposite ends of the machine.  Chief could not name the cause because
this lane's result object did not carry one.

TWO THINGS ARE BEING PINNED HERE AND THEY PULL IN OPPOSITE DIRECTIONS.

1. The cause must be SPECIFIC enough to be worth ACTING ON.  The axis is
   the remedy, not the return site: pf-adversary measured that the first
   version's seven tokens split on "which read saw the bad bytes" -- which
   no operator can use -- while answering ONE word for both of the two
   remedies chief said were different.  `CauseIsReachableTests` drives each
   token, and `test_the_two_remedies_do_not_share_a_token` is the assertion
   that would have caught it.
2. The cause must be SAFE enough to print.  Round `9wy444` D1 established
   that no byte a client sent may reach the owner's console, and this token
   is going straight onto that console under this lane's name.  A cause
   built from `str(exc)` would carry a config file's contents there -- a
   JSON parse error quotes the offending line verbatim.  `NothingFromDisk
   OrExceptionsReachesTheCauseTests` drives every failure branch with a
   memorable secret planted in the file AND in the exception, and asks
   whether any of it survived -- in BOTH exception types, since the first
   version planted it only in `OSError` while the exception production
   actually raises is `ValueError`, whose message interpolates the config
   PATH and the ACCOUNT NAME.

The second is the one that matters more.  A vague cause costs an operator
some time; a cause that echoes a config file is this lane handing an
attacker a printer, and it would arrive wearing a token that says the line
is trustworthy.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import (  # noqa: E402
    login_scene_consume,
    login_scene_override,
    login_scene_stage,
)

C = login_scene_consume
PORT_ROYAL = 1
# Known to the client's scene table but pinned `login_entry_allowed=false`,
# so a config naming it is WELL-FORMED and still inadmissible.  Asserted in
# `RefusedSceneIsStillTheRightFixtureTests` rather than trusted, because the
# whole D1 fix rests on this scene having exactly that property.
REFUSED_SCENE = 17

# Planted in the places a careless implementation would read from: the file
# on disk and the exception's own message.  Chosen to be unmistakable -- if
# any of it turns up in a cause, the test does not have to argue about
# whether the leak was real.
SECRET = "hunter2-DO-NOT-PRINT-ME"


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"
        self.standalone_path = self.tmp / "config" / "standalone.json"

    def stage(self, scene_id=PORT_ROYAL):
        staged = login_scene_stage.stage_login_scene(
            self.GM_ACCOUNT,
            scene_id,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )
        self.assertTrue(staged.staged)

    def consume(self):
        return C.consume_login_scene_override(
            self.GM_ACCOUNT,
            gm_accounts_config_path=str(self.accounts_path),
            login_scene_config_path=str(self.config_path),
            standalone_config_path=str(self.standalone_path),
        )

    def assert_failed_with(self, result, cause):
        # All three every time.  The cause is an ADDITION to the guarantee,
        # never a softening of it: a named cause that came with a scene id
        # would mean the login was handed a scene whose override outlived
        # it, which is the state `COO-DECISION 0441` exists to forbid.
        self.assertIsNone(result.scene_id)
        self.assertEqual(C.CONSUME_FAILED, result.outcome)
        self.assertEqual(cause, result.cause)


class CauseIsReachableTests(_Case):
    """One test per cause, driven to the branch that produces it."""

    def test_a_malformed_config_says_the_config_was_rejected(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{not json", encoding="utf-8")
        self.assert_failed_with(self.consume(), C.CAUSE_CONFIG_REJECTED)

    def test_a_hand_typed_bad_scene_says_EDIT_THE_FILE_not_restart(self):
        # THE DEFECT THAT RESHAPED THIS ROUND (pf-adversary, D1).  This file
        # is well-formed; scene 17 is pinned `login_entry_allowed=false`, so
        # the registry this process holds will not admit the row.  The first
        # version answered `override_lookup_unreadable` here -- sending an
        # operator to grep a file with nothing wrong in it -- and answered
        # the SAME word for the malformed file above, which is precisely the
        # two remedies chief said were not the same remedy.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: REFUSED_SCENE}}),
            encoding="utf-8",
        )
        result = self.consume()
        # `scene_not_admissible` = edit the file.  The SECOND pf-adversary
        # pass measured the first fix answering `registry_refused_entry`
        # here, whose documented remedy is "restart the server" -- and a
        # restart cannot help, because no reading of the registry admits
        # scene 17, now or ever.  The two remedies had stopped sharing a
        # word without stopping being crossed.
        self.assert_failed_with(result, C.CAUSE_SCENE_NOT_ADMISSIBLE)
        self.assertNotIn("unreadable", result.cause)
        self.assertNotIn("stale", result.cause)

    def test_a_named_scene_that_is_simply_not_stageable_says_the_same(self):
        # Scene 7 HAS a name in the 330-row catalog and is still not
        # admissible.  pf-adversary called this the ~99% typo and it was
        # the case the inverted token sent to a pointless restart.  MOVED
        # this round from scene 3 (Spice Paradise Island, which opened this
        # round) to scene 7 (Voodoo Island), still one of the four doors
        # this lane has not yet opened.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: 7}}),
            encoding="utf-8",
        )
        self.assert_failed_with(self.consume(), C.CAUSE_SCENE_NOT_ADMISSIBLE)

    def test_a_registry_that_went_narrow_since_boot_says_RESTART(self):
        # The other remedy, and the only one a restart actually fixes: the
        # row is admissible on disk TODAY, and only the running process
        # disagrees because its snapshot predates the edit.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: PORT_ROYAL}}),
            encoding="utf-8",
        )
        narrow = {}  # a snapshot that admits nothing at all
        result = C.consume_login_scene_override(
            self.GM_ACCOUNT,
            gm_accounts_config_path=str(self.accounts_path),
            login_scene_config_path=str(self.config_path),
            standalone_config_path=str(self.standalone_path),
            scene_registry=narrow,
        )
        self.assert_failed_with(result, C.CAUSE_REGISTRY_STALE_SINCE_BOOT)

    def test_the_restart_answer_is_never_given_to_a_bare_caller(self):
        # With no snapshot the refusal already came from a fresh disk read,
        # so "restart" would be advice that cannot possibly help.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: REFUSED_SCENE}}),
            encoding="utf-8",
        )
        self.assertEqual(
            C.CAUSE_SCENE_NOT_ADMISSIBLE, self.consume().cause
        )

    def test_the_remedy_probe_can_never_cost_the_login(self):
        # A DIAGNOSTIC MAY NEVER ALTER DISPATCH: if the fresh read explodes,
        # the word falls back to the common case rather than escaping.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: PORT_ROYAL}}),
            encoding="utf-8",
        )
        from pirateforce_foundation.gm import login_scene_admission

        # THE PROBE'S OWN SEAM, and the reason it exists rather than
        # `login_entry_is_pinned` is measured, not stylistic.  Since
        # `CORE-REQUEST-GM-038` the CONFIG READER asks the admission module
        # too, so a mock on the shared predicate broke the reader as well
        # and a `RuntimeError` escaped `consume_login_scene_override`
        # entirely -- this test would then have been pinning the reader's
        # behaviour under a name that says "probe".  `disk_admits_under_rule`
        # has one caller (`_refusal_cause`), so exploding it observes only
        # what this test means to observe.
        with mock.patch.object(
            login_scene_admission,
            "disk_admits_under_rule",
            side_effect=RuntimeError("disk on fire"),
        ):
            result = C.consume_login_scene_override(
                self.GM_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
                standalone_config_path=str(self.standalone_path),
                scene_registry={},
            )
        self.assert_failed_with(result, C.CAUSE_SCENE_NOT_ADMISSIBLE)

    def test_the_two_remedies_do_not_share_a_token(self):
        # Stated as its own assertion because it is the whole point of the
        # field.  Both cases are driven above; this refuses a future edit
        # that quietly folds them back together.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{not json", encoding="utf-8")
        bad_bytes = self.consume().cause
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: REFUSED_SCENE}}),
            encoding="utf-8",
        )
        refused_row = self.consume().cause
        self.assertNotEqual(bad_bytes, refused_row)

    def test_the_accounts_file_going_unreadable_after_the_lookup(self):
        # The lookup reads the accounts file too, so a malformed file on
        # disk would fail EARLIER and never reach this branch.  Patching
        # this module's own name reaches the second call only.
        self.stage()
        with mock.patch.object(
            C, "is_gm_account", side_effect=OSError("gone")
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_GM_ACCOUNTS_UNREADABLE)

    def test_the_gm_map_going_unreadable(self):
        self.stage()
        with mock.patch.object(
            C, "load_login_scene_overrides", side_effect=OSError("gone")
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_GM_MAP_UNREADABLE)

    def test_the_gm_map_going_unreadable_after_a_lost_claim_says_the_same(self):
        # DELIBERATELY the same token as the test above.  An earlier version
        # split these two moments and pf-adversary showed the standalone
        # read has the identical two moments under ONE token -- the axis was
        # not applied consistently, and an operator does nothing different
        # about the two.  Pinned so the split is not "restored" by someone
        # reading only one half of the story.
        self.stage()
        with mock.patch.object(
            C,
            "load_login_scene_overrides",
            side_effect=[{self.GM_ACCOUNT: PORT_ROYAL}, OSError("gone")],
        ), mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_GM_MAP_UNREADABLE)

    def test_the_standalone_map_being_unreadable_pre_claim(self):
        self.stage()
        with mock.patch.object(
            C, "load_login_scene_overrides", return_value={}
        ), mock.patch.object(
            C,
            "load_standalone_login_scene_overrides",
            side_effect=OSError("gone"),
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_STANDALONE_MAP_UNREADABLE)

    def test_the_standalone_map_being_unreadable_post_claim(self):
        # THE SECOND CALL SITE of `_ask_the_standalone_map`, which had no
        # test at all until pf-adversary counted the reachable moments (D7)
        # and found 8 of them behind 7 syntactic return sites.
        self.stage()
        with mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ), mock.patch.object(
            C,
            "load_login_scene_overrides",
            side_effect=[{self.GM_ACCOUNT: PORT_ROYAL}, {}],
        ), mock.patch.object(
            C,
            "load_standalone_login_scene_overrides",
            side_effect=OSError("gone"),
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_STANDALONE_MAP_UNREADABLE)

    def test_the_claim_raising_for_any_exception_not_just_OSError(self):
        # `except Exception:` is what the source says; an earlier test drove
        # only `OSError`, so narrowing it to `(OSError, ValueError)` passed
        # the whole suite (pf-adversary).  RuntimeError is outside both.
        self.stage()
        for boom in (OSError("disk"), RuntimeError("anything at all")):
            with self.subTest(exc=type(boom).__name__):
                with mock.patch.object(
                    login_scene_stage, "claim_login_scene", side_effect=boom
                ):
                    result = self.consume()
                self.assert_failed_with(result, C.CAUSE_CLAIM_RAISED)

    def test_the_entry_still_being_there_after_the_claim(self):
        # No mock on the reads at all: the entry is genuinely on disk and
        # the remover genuinely declines to take it.
        self.stage()
        with mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_ENTRY_SURVIVED_CLAIM)
        self.assertEqual(
            PORT_ROYAL,
            login_scene_override.load_login_scene_overrides(
                str(self.config_path)
            )[self.GM_ACCOUNT],
        )


class TheConsoleWordsAreSpelledOutTests(unittest.TestCase):
    """The literal strings, because chief prints THESE, not the symbols.

    pf-adversary swapped the VALUES of `CAUSE_CLAIM_RAISED` and
    `CAUSE_ENTRY_SURVIVED_CLAIM` and the entire 4760-test suite stayed
    green: every assertion compared `result.cause` against `C.CAUSE_X`
    symbolically, so an inversion of the two words on the owner's console
    was invisible.  This file is the one place that names them.
    """

    def test_the_eight_words(self):
        self.assertEqual("config_rejected", C.CAUSE_CONFIG_REJECTED)
        self.assertEqual(
            "scene_not_admissible", C.CAUSE_SCENE_NOT_ADMISSIBLE
        )
        self.assertEqual(
            "registry_stale_since_boot", C.CAUSE_REGISTRY_STALE_SINCE_BOOT
        )
        # The word "unreadable" may not be applied to a file that reads:
        # five of six producers of the rejection token are valid JSON.
        self.assertNotIn("unreadable", C.CAUSE_CONFIG_REJECTED)
        self.assertEqual(
            "gm_accounts_unreadable", C.CAUSE_GM_ACCOUNTS_UNREADABLE
        )
        self.assertEqual("gm_map_unreadable", C.CAUSE_GM_MAP_UNREADABLE)
        self.assertEqual(
            "standalone_map_unreadable", C.CAUSE_STANDALONE_MAP_UNREADABLE
        )
        self.assertEqual("claim_raised", C.CAUSE_CLAIM_RAISED)
        self.assertEqual(
            "entry_survived_claim", C.CAUSE_ENTRY_SURVIVED_CLAIM
        )
        self.assertEqual("none", C.CAUSE_NONE)

    def test_the_set_is_closed_not_merely_named_closed(self):
        # `frozenset(` -> `set(` survived the full suite before this.
        self.assertIsInstance(C.CONSUME_FAILED_CAUSES, frozenset)


class EveryReturnSiteIsAccountedForTests(unittest.TestCase):
    """Counts the RETURN SITES IN THE SOURCE, not the constants.

    The first version asserted `len(CONSUME_FAILED_CAUSES) == 7` and called
    that a refusal of token reuse.  pf-adversary added an eighth
    `CONSUME_FAILED` return site borrowing an existing token: 23 passed,
    803 passed, whole suite green.  A count of constants cannot see a new
    branch, so this reads the source instead.
    """

    SOURCE_PATH = (
        REPO_ROOT
        / "src"
        / "pirateforce_foundation"
        / "gm"
        / "login_scene_consume.py"
    )

    # The ONE function allowed to compute a cause.  It returns a member of
    # the closed set on every path (including its own except arm), which is
    # pinned by `TheRemedyProbeIsClosedTests` below.
    CAUSE_HELPER = "_refusal_cause"

    def return_sites(self):
        # Parsed, not grepped.  A string scan picks up `ConsumeResult(` out
        # of comments and docstrings -- this file's own prose mentions it
        # several times -- and then reports a comment as a return site.
        #
        # HANDLES KEYWORD AND LITERAL FORMS, because the first version did
        # not and pf-adversary added a twelfth branch in each shape that the
        # whole suite accepted:
        #     ConsumeResult(None, "consume_failed", CAUSE_X)   <- literal
        #     ConsumeResult(None, outcome=CONSUME_FAILED, ...) <- keyword
        import ast

        tree = ast.parse(self.SOURCE_PATH.read_text(encoding="utf-8"))
        sites = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "ConsumeResult":
                continue
            kw = {k.arg: k.value for k in node.keywords}
            args = list(node.args)
            outcome = kw.get("outcome") or (args[1] if len(args) > 1 else None)
            is_failure = (
                isinstance(outcome, ast.Name)
                and outcome.id == "CONSUME_FAILED"
            ) or (
                isinstance(outcome, ast.Constant)
                and outcome.value == "consume_failed"
            )
            if not is_failure:
                continue
            third = kw.get("cause") or (args[2] if len(args) > 2 else None)
            sites.append(third)
        return sites

    def site_names(self):
        out = []
        import ast

        for node in self.return_sites():
            if isinstance(node, ast.Name):
                out.append(node.id)
            elif isinstance(node, ast.Call):
                out.append(
                    getattr(node.func, "id", None)
                    or getattr(node.func, "attr", None)
                )
            else:
                out.append(node)
        return out

    def test_every_failure_return_site_names_a_cause_constant(self):
        names = self.site_names()
        self.assertTrue(names, "found no CONSUME_FAILED return sites at all")
        for name in names:
            with self.subTest(site=name):
                self.assertIsNotNone(
                    name, "a CONSUME_FAILED site with no cause argument"
                )
                self.assertIsInstance(
                    name,
                    str,
                    "a CONSUME_FAILED site whose cause is not a plain "
                    "constant -- a literal or an f-string here is how a "
                    "config file's bytes reach the owner's console",
                )
                self.assertTrue(
                    name.startswith("CAUSE_") or name == self.CAUSE_HELPER,
                    f"{name!r} is neither a CAUSE_ constant nor the one "
                    "helper allowed to compute a cause",
                )
                if name == self.CAUSE_HELPER:
                    self.assertTrue(
                        self.helper_causes() <= C.CONSUME_FAILED_CAUSES,
                        "the cause helper can return something outside the "
                        "closed set",
                    )
                else:
                    self.assertIn(
                        getattr(C, name), C.CONSUME_FAILED_CAUSES
                    )

    def test_the_number_of_failure_return_sites_is_pinned(self):
        # THE ASSERTION THAT KILLS pf-adversary's D6 MUTATION (an eighth
        # branch borrowing an existing token, which every other check here
        # accepts).  Note what is NOT asserted: "no two sites share a
        # token".  That WAS the first version's rule and the remedy axis
        # deliberately broke it -- ~~`registry_refused_entry` is returned
        # from four sites~~ several tokens are returned from more than one
        # site, because a refused row is the same fault and the same remedy
        # wherever the loader met it.  (The struck half named a token that
        # was SPLIT and no longer exists, and a count nothing re-derives:
        # pf-adversary D8, round `npo898`.  The live count is the assertion
        # below, which AST-parses the source on every run.)
        #
        # So the pin is the COUNT.  Adding or removing a `CONSUME_FAILED`
        # branch is then a deliberate act: this number moves, and whoever
        # moves it has to say which remedy the new branch belongs to and
        # update the table in `docs/GM_LANE.md`.  A branch added silently
        # is a red test.
        self.assertEqual(11, len(self.return_sites()))

    def test_every_declared_cause_is_actually_used_by_some_site(self):
        # The other direction: a token nobody returns is a word chief could
        # never print, and a stale row in the docs table.
        used = set()
        for name in self.site_names():
            if name == self.CAUSE_HELPER:
                used |= self.helper_causes()
            elif name:
                used.add(getattr(C, name))
        self.assertEqual(C.CONSUME_FAILED_CAUSES, used)

    def helper_causes(self):
        # Every constant the helper can return, read out of its source.
        import ast

        tree = ast.parse(self.SOURCE_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == self.CAUSE_HELPER
            ):
                return {
                    getattr(C, r.value.id)
                    for r in ast.walk(node)
                    if isinstance(r, ast.Return)
                    and isinstance(r.value, ast.Name)
                }
        raise AssertionError("the cause helper is gone")


class TheChatSurfaceGetsTheSameDistinctionTests(_Case):
    """D6-R: the surface that reaches a PERSON, not just the console.

    pf-adversary's point was that the `ValueError`-subclass design, whose
    selling point is "every existing caller behaves exactly as before", is
    precisely what PRESERVED the misdiagnosis in `login_scene_stage` -- and
    that is the half a tester actually reads, in a chat reply, today.  The
    console cause is still printed by nothing.
    """

    def test_a_readable_file_with_a_bad_line_is_not_reported_unreadable(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {"GM_TWO": REFUSED_SCENE}}),
            encoding="utf-8",
        )
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT, "GM_TWO"]}),
            encoding="utf-8",
        )
        result = login_scene_stage.stage_login_scene(
            self.GM_ACCOUNT,
            PORT_ROYAL,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_EXISTING_ENTRY_NOT_ADMISSIBLE,
            result.reason,
        )

    def test_a_genuinely_malformed_file_still_says_unreadable(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{not json", encoding="utf-8")
        result = login_scene_stage.stage_login_scene(
            self.GM_ACCOUNT,
            PORT_ROYAL,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_CONFIG_UNREADABLE, result.reason
        )

    def test_the_two_reasons_are_different_words(self):
        self.assertNotEqual(
            login_scene_stage.REASON_CONFIG_UNREADABLE,
            login_scene_stage.REASON_EXISTING_ENTRY_NOT_ADMISSIBLE,
        )

    def test_the_new_reason_is_classified_for_the_way_out(self):
        # This module's partition rule: every non-OK reason belongs to
        # exactly one of the two sets, so a new one cannot be silently
        # dropped into "no way out" by being forgotten.
        self.assertIn(
            login_scene_stage.REASON_EXISTING_ENTRY_NOT_ADMISSIBLE,
            login_scene_stage.NOT_DESTINATION_SHAPED_REASONS,
        )
        self.assertNotIn(
            login_scene_stage.REASON_EXISTING_ENTRY_NOT_ADMISSIBLE,
            login_scene_stage.DESTINATION_SHAPED_REASONS,
        )


class EveryRefusalArmIsActuallyWalkedTests(_Case):
    """D5-R: three of the four refusal arms had never executed.

    Token coverage masked branch coverage -- one site used the token, so
    "every declared cause is used" passed while the other three arms were
    unreached.  pf-adversary then REORDERED each one behind the wide
    `except (OSError, ValueError)`, making it dead code, and the suite
    stayed green.  The comment on those arms says "ORDER MATTERS"; nothing
    tested it at three of the four places it is written.
    """

    def refused(self):
        return login_scene_override.LoginSceneRefusedError(
            "refused", scene_id=REFUSED_SCENE
        )

    def test_the_pre_claim_gm_map_arm(self):
        self.stage()
        with mock.patch.object(
            C, "load_login_scene_overrides", side_effect=self.refused()
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_SCENE_NOT_ADMISSIBLE)

    def test_the_post_claim_gm_map_arm(self):
        self.stage()
        with mock.patch.object(
            C,
            "load_login_scene_overrides",
            side_effect=[{self.GM_ACCOUNT: PORT_ROYAL}, self.refused()],
        ), mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_SCENE_NOT_ADMISSIBLE)

    def test_the_standalone_arm(self):
        self.stage()
        with mock.patch.object(
            C, "load_login_scene_overrides", return_value={}
        ), mock.patch.object(
            C,
            "load_standalone_login_scene_overrides",
            side_effect=self.refused(),
        ):
            result = self.consume()
        self.assert_failed_with(result, C.CAUSE_SCENE_NOT_ADMISSIBLE)

    def test_the_lookup_arm(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: REFUSED_SCENE}}),
            encoding="utf-8",
        )
        self.assert_failed_with(self.consume(), C.CAUSE_SCENE_NOT_ADMISSIBLE)


class TheResultSurvivesCopyAndPickleTests(unittest.TestCase):
    """D8-R: the immutability fix broke both, and `AttributeError` is NOT in
    `runtime.py`'s `(ValueError, OSError, TypeError)` -- so a `deepcopy` of
    an events structure holding one of these would have killed the login
    thread.  Strictly worse than the leak the immutability closed."""

    def results(self):
        return [
            C.ConsumeResult(1, C.CONSUMED),
            C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED),
        ]

    def test_copy_and_deepcopy_round_trip(self):
        import copy

        for original in self.results():
            with self.subTest(outcome=original.outcome):
                self.assertEqual(original, copy.copy(original))
                self.assertEqual(original, copy.deepcopy(original))

    def test_pickle_round_trips(self):
        import pickle

        for original in self.results():
            with self.subTest(outcome=original.outcome):
                self.assertEqual(
                    original, pickle.loads(pickle.dumps(original))
                )

    def test_a_round_trip_still_goes_through_validation(self):
        # Rebuilding via __init__ rather than restoring a state dict means
        # there is no round-trip that launders a forged cause.
        import pickle

        result = C.ConsumeResult(
            None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED
        )
        self.assertIn(
            pickle.loads(pickle.dumps(result)).cause,
            C.CONSUME_FAILED_CAUSES,
        )


class AllThreePrintedFieldsAreGuardedTests(unittest.TestCase):
    """D8-R: the first version guarded `cause` alone and advertised the
    str-subclass forgery as closed, while `runtime.py` interpolates
    `scene_id` into an event string and compares `outcome`."""

    def test_a_forged_outcome_is_refused(self):
        class Forged(str):
            def __str__(self):
                return "consumed effect=ok"

        with self.assertRaises(TypeError):
            C.ConsumeResult(1, Forged(C.CONSUMED))

    def test_a_forged_scene_id_is_refused(self):
        class Evil:
            def __str__(self):
                return "1\nGM_LOGIN_SCENE_OVERRIDE_CONSUMED 999"

        with self.assertRaises(TypeError):
            C.ConsumeResult(Evil(), C.CONSUMED)

    def test_an_honest_int_and_None_are_still_accepted(self):
        self.assertEqual(1, C.ConsumeResult(1, C.CONSUMED).scene_id)
        self.assertIsNone(
            C.ConsumeResult(None, C.NOTHING_STAGED).scene_id
        )

    def test_a_bool_is_not_an_acceptable_scene_id(self):
        # `type(...) is not int` rather than isinstance, so True does not
        # sail through as scene 1.
        with self.assertRaises(TypeError):
            C.ConsumeResult(True, C.CONSUMED)


class TheRemedyProbeIsClosedTests(unittest.TestCase):
    """The one function allowed to COMPUTE a cause is still closed.

    `_refusal_cause` is the single exception to "every cause is a literal at
    its return site", so it carries the whole safety argument for the four
    sites that call it.
    """

    def test_every_path_through_the_probe_returns_a_member_of_the_set(self):
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(C._refusal_cause))
        returns = [
            r.value for r in ast.walk(tree) if isinstance(r, ast.Return)
        ]
        self.assertTrue(returns)
        for value in returns:
            # A `Name` only -- never a call, an f-string or a literal, which
            # is how message text would get in.
            self.assertIsInstance(value, ast.Name)
            self.assertIn(getattr(C, value.id), C.CONSUME_FAILED_CAUSES)

    def test_the_probe_swallows_everything_rather_than_escaping(self):
        # A DIAGNOSTIC MAY NEVER ALTER DISPATCH.
        class Boom(LookupError):
            pass

        from pirateforce_foundation.gm import login_scene_admission

        refused = login_scene_override.LoginSceneRefusedError(
            "x", scene_id=PORT_ROYAL
        )
        for exc in (Boom(), MemoryError(), RuntimeError(SECRET)):
            with self.subTest(exc=type(exc).__name__):
                with mock.patch.object(
                    login_scene_admission,
                    "login_entry_is_pinned",
                    side_effect=exc,
                ):
                    cause = C._refusal_cause(refused, {})
                self.assertEqual(C.CAUSE_SCENE_NOT_ADMISSIBLE, cause)

    def test_a_forged_scene_id_on_the_exception_cannot_reach_the_cause(self):
        refused = login_scene_override.LoginSceneRefusedError(
            "x", scene_id=SECRET
        )
        cause = C._refusal_cause(refused, {})
        self.assertIn(cause, C.CONSUME_FAILED_CAUSES)
        self.assertNotIn(SECRET, cause)


class RefusedSceneIsStillTheRightFixtureTests(unittest.TestCase):
    def test_the_refused_scene_is_known_but_not_admissible(self):
        # If lane A ever pins scene 17 admissible, the D1 tests would
        # silently stop testing the refusal path.  Fail loudly here instead.
        from pirateforce_foundation.gm import (  # noqa: E402
            login_scene_admission,
            scene_catalog,
        )

        self.assertTrue(scene_catalog.is_known_scene_id(REFUSED_SCENE))
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(REFUSED_SCENE)
        )
        self.assertNotIn(
            REFUSED_SCENE, login_scene_admission.stageable_scene_ids()
        )


class NothingFromDiskOrExceptionsReachesTheCauseTests(_Case):
    """Round `9wy444` D1, one layer down: chief PRINTS this token.

    Each case plants `SECRET` where a careless implementation would pick it
    up, then asks whether any of it survived into anything chief can print.
    """

    def assert_clean(self, result):
        for surface in (result.cause, result.outcome, repr(result)):
            self.assertNotIn(SECRET, surface)
            self.assertNotIn("hunter2", surface)
        # Not merely "the secret is absent" -- the cause is one of the words
        # this lane wrote.  Absence can be an accident of formatting; a
        # closed set cannot.
        self.assertIn(result.cause, C.CONSUME_FAILED_CAUSES)

    def test_a_malformed_config_that_QUOTES_the_secret_in_its_parse_error(self):
        # The sharp one.  `json` raises with the offending text in the
        # message, so an implementation that did `cause=str(exc)` would put
        # the file's contents on the owner's console under this lane's own
        # token.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            '{"gm_login_scenes": {"' + SECRET + '": not-json}}',
            encoding="utf-8",
        )
        result = self.consume()
        self.assert_clean(result)
        self.assertEqual(C.CAUSE_CONFIG_REJECTED, result.cause)

    def test_the_registry_refusal_whose_ValueError_QUOTES_path_and_account(self):
        # THE LEAK THE FIRST VERSION COULD NOT SEE (pf-adversary, D3).  It
        # planted the secret only in `OSError`; the exception this module
        # actually meets is `LoginSceneRefusedError` (a `ValueError`) whose
        # message interpolates the config PATH and the ACCOUNT NAME.  A leak
        # conditioned on the real type was invisible to the test that
        # claimed to cover it.
        account = "GM_" + SECRET
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [account]}), encoding="utf-8"
        )
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {account: REFUSED_SCENE}}),
            encoding="utf-8",
        )
        result = C.consume_login_scene_override(
            account,
            gm_accounts_config_path=str(self.accounts_path),
            login_scene_config_path=str(self.config_path),
            standalone_config_path=str(self.standalone_path),
        )
        self.assert_clean(result)
        self.assertEqual(C.CAUSE_SCENE_NOT_ADMISSIBLE, result.cause)
        # And the exception really did carry the secret, so the test above
        # is not passing because there was nothing to leak.
        with self.assertRaises(ValueError) as caught:
            login_scene_override.load_login_scene_overrides(
                str(self.config_path)
            )
        self.assertIn(SECRET, str(caught.exception))

    def test_every_failure_branch_with_the_secret_in_BOTH_exception_types(self):
        # All seven, not the four the first version reached.
        self.stage()
        for boom in (OSError(SECRET), ValueError(SECRET)):
            cases = [
                (
                    C.CAUSE_GM_ACCOUNTS_UNREADABLE,
                    lambda b=boom: mock.patch.object(
                        C, "is_gm_account", side_effect=b
                    ),
                ),
                (
                    C.CAUSE_GM_MAP_UNREADABLE,
                    lambda b=boom: mock.patch.object(
                        C, "load_login_scene_overrides", side_effect=b
                    ),
                ),
                (
                    C.CAUSE_CLAIM_RAISED,
                    lambda b=boom: mock.patch.object(
                        login_scene_stage, "claim_login_scene", side_effect=b
                    ),
                ),
            ]
            for expected, patcher in cases:
                with self.subTest(cause=expected, exc=type(boom).__name__):
                    with patcher():
                        result = self.consume()
                    self.assert_clean(result)
                    self.assertEqual(expected, result.cause)

    def test_the_standalone_and_survived_branches_are_secret_tested_too(self):
        # `STANDALONE_MAP_UNREADABLE` and `ENTRY_SURVIVED_CLAIM` had no
        # secret test at all in the first version (pf-adversary, D3 item 2).
        self.stage()
        with mock.patch.object(
            C, "load_login_scene_overrides", return_value={}
        ), mock.patch.object(
            C,
            "load_standalone_login_scene_overrides",
            side_effect=ValueError(SECRET),
        ):
            result = self.consume()
        self.assert_clean(result)
        self.assertEqual(C.CAUSE_STANDALONE_MAP_UNREADABLE, result.cause)

        with mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ):
            survived = self.consume()
        self.assert_clean(survived)
        self.assertEqual(C.CAUSE_ENTRY_SURVIVED_CLAIM, survived.cause)

    def test_a_cause_cannot_be_rewritten_after_construction(self):
        # The path pf-adversary found: validation lived only in __init__, so
        # `result.cause = f"{TOKEN}: {exc}"` was a legal one-line change
        # that put the config PATH and an ACCOUNT NAME on the console and
        # survived all 23 tests.  The module claims "no path builds a
        # cause"; assignment was that path.
        result = C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED)
        with self.assertRaises(AttributeError):
            result.cause = f"{C.CAUSE_CLAIM_RAISED}: {SECRET}"
        with self.assertRaises(AttributeError):
            result.outcome = SECRET
        with self.assertRaises(AttributeError):
            result.scene_id = 9999
        with self.assertRaises(AttributeError):
            del result.cause
        self.assertEqual(C.CAUSE_CLAIM_RAISED, result.cause)

    def test_a_str_subclass_cannot_smuggle_a_forged_console_field(self):
        # Passes `in CONSUME_FAILED_CAUSES` by equality, then renders as
        # whatever `__str__` says when chief interpolates it -- a forged
        # `key=value`, or a forged second console line.
        class Forged(str):
            def __str__(self):
                return "claim_raised effect=ok\nGM_LOGIN_SCENE_OVERRIDE_CONSUMED 2"

        forged = Forged(C.CAUSE_CLAIM_RAISED)
        self.assertIn(forged, C.CONSUME_FAILED_CAUSES)  # equality says yes
        with self.assertRaises(TypeError):
            C.ConsumeResult(None, C.CONSUME_FAILED, forged)

    def test_an_account_name_never_becomes_part_of_the_cause(self):
        # REWRITTEN: the first version never wrote a config and never
        # staged, so it reached `nothing_staged` / `cause='none'` and its
        # assertion was a tautology on the happy path (pf-adversary, D5).
        # This one drives a real `CONSUME_FAILED`.
        nasty = "GM_" + SECRET
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [nasty]}), encoding="utf-8"
        )
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {nasty: PORT_ROYAL}}),
            encoding="utf-8",
        )
        with mock.patch.object(
            login_scene_stage,
            "claim_login_scene",
            side_effect=OSError("boom"),
        ):
            result = C.consume_login_scene_override(
                nasty,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
                standalone_config_path=str(self.standalone_path),
            )
        self.assertEqual(C.CONSUME_FAILED, result.outcome)
        self.assertEqual(C.CAUSE_CLAIM_RAISED, result.cause)
        self.assert_clean(result)

    def test_every_cause_survives_the_bridge_console_encoding(self):
        # cp874 is what the bridge console really enforces (round `9wy444`
        # D2: a line that cannot be encoded is a line the operator never
        # sees, and the guard swallows it silently).  A cause that cannot
        # be printed is a cause that does not exist.
        for cause in C.CONSUME_FAILED_CAUSES | {C.CAUSE_NONE}:
            with self.subTest(cause=cause):
                cause.encode("cp874")
                cause.encode("ascii")
                self.assertEqual(cause, cause.strip())
                self.assertTrue(cause)
                # One token, so it cannot forge a second field on chief's
                # `key=value` line.
                self.assertNotIn(" ", cause)
                self.assertNotIn("=", cause)
                self.assertNotIn("\n", cause)
                self.assertNotIn("\r", cause)


class TheVocabularyIsClosedTests(unittest.TestCase):
    """There is no path that sanitises a cause, because none builds one."""

    def test_a_cause_outside_the_set_is_refused(self):
        with self.assertRaises(ValueError):
            C.ConsumeResult(None, C.CONSUME_FAILED, "anything_at_all")

    def test_a_failure_must_carry_a_cause(self):
        # Without this, a branch added later could return the old two-arg
        # shape and chief would silently be back to printing
        # `cause=not_carried_by_the_outcome` for it.
        with self.assertRaises(ValueError):
            C.ConsumeResult(None, C.CONSUME_FAILED)

    def test_a_success_may_not_carry_a_cause(self):
        with self.assertRaises(ValueError):
            C.ConsumeResult(PORT_ROYAL, C.CONSUMED, C.CAUSE_CLAIM_RAISED)

    def test_refusing_is_fail_closed_for_the_login_not_fatal_to_it(self):
        # THIRD VERSION of this test, and the first two were both false
        # greens (pf-adversary, D4 then D2-R).  v1 grepped two loose
        # substrings that other text satisfied.  v2 found the real call and
        # searched a window after it -- which still passed when the call was
        # MOVED ONE LINE ABOVE the `try`, leaving it completely unguarded
        # while the handler sat untouched below.
        #
        # Containment is a tree question, so this asks the tree: find the
        # `try` whose handler catches the three types, and require the
        # consume call to be inside its BODY.
        import ast

        tree = ast.parse(
            (
                REPO_ROOT / "src" / "pirateforce_foundation" / "runtime.py"
            ).read_text(encoding="utf-8")
        )

        def calls_consume(node):
            return any(
                isinstance(n, ast.Call)
                and (
                    getattr(n.func, "id", None) == "consume_login_scene_override"
                    or getattr(n.func, "attr", None)
                    == "consume_login_scene_override"
                )
                for n in ast.walk(node)
            )

        guarded = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            caught = set()
            for handler in node.handlers:
                spec = handler.type
                parts = (
                    spec.elts if isinstance(spec, ast.Tuple) else [spec]
                )
                caught |= {
                    getattr(part, "id", None) for part in parts if part
                }
            if not {"ValueError", "OSError", "TypeError"} <= caught:
                continue
            if any(calls_consume(stmt) for stmt in node.body):
                guarded.append(node)

        self.assertEqual(
            1,
            len(guarded),
            "the consume call is not inside a try that catches "
            "(ValueError, OSError, TypeError) -- a cause this lane got "
            "wrong would stop costing the override and start costing the "
            "login, which is the ENTIRE argument for raising from "
            "ConsumeResult.__init__",
        )

    def test_a_refused_cause_really_does_come_back_as_a_ValueError(self):
        # The other half, exercised rather than grepped.
        with self.assertRaises(ValueError):
            C.ConsumeResult(None, C.CONSUME_FAILED, "not_a_real_cause")


class TheDocsAndTheConsoleAgreeTests(unittest.TestCase):
    """A tripwire instead of a label that rots -- SECOND version.

    v1 keyed on the presence of the literal `cause=not_carried_by_the_outcome`
    in `runtime.py`, and pf-adversary broke it both ways: chief wiring the
    print while leaving a `# was: cause=not_carried_by_the_outcome` history
    comment (this project's house style) kept it GREEN with the docs now
    false; and merely rewording the placeholder turned it RED with a message
    instructing the reader to make the docs lie.

    Both failures came from testing a PROXY (a literal's presence) instead
    of the goal.  The goal is: does anything outside this lane READ the
    cause?  That is what makes the docs sentence true or false, and it is
    an ast question.
    """

    DOC_SENTENCE = "**NOT YET PRINTED** (LANE-GM round `1fq5yf`)"

    @staticmethod
    def readers_of_cause():
        # `.cause` attribute access AND `getattr(x, "cause")`, which the
        # first regex walked straight past.
        import ast

        found = []
        for path in (REPO_ROOT / "src").rglob("*.py"):
            if path.name == "login_scene_consume.py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - not our file to fix
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "cause":
                    found.append(f"{path.name}:{node.lineno}")
                elif (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "getattr"
                    and len(node.args) > 1
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "cause"
                ):
                    found.append(f"{path.name}:{node.lineno} (getattr)")
        return found

    def test_the_docs_say_not_printed_exactly_while_nothing_reads_it(self):
        docs = (REPO_ROOT / "docs" / "GM_LANE.md").read_text(encoding="utf-8")
        readers = self.readers_of_cause()
        if readers:
            self.assertNotIn(
                self.DOC_SENTENCE,
                docs,
                f"{readers} now reads .cause -- CORE-REQUEST-GM-037 is "
                "wired, so DELETE the 'NOT YET PRINTED' paragraph in "
                "docs/GM_LANE.md, it is now false",
            )
        else:
            self.assertIn(
                self.DOC_SENTENCE,
                docs,
                "nothing outside this lane reads .cause, so GM_LANE.md must "
                "keep saying the cause is not printed yet",
            )


class SuccessOutcomesCarryNoCauseTests(_Case):
    def test_consumed(self):
        self.stage()
        result = self.consume()
        self.assertEqual(C.CONSUMED, result.outcome)
        self.assertEqual(C.CAUSE_NONE, result.cause)

    def test_nothing_staged(self):
        result = self.consume()
        self.assertEqual(C.NOTHING_STAGED, result.outcome)
        self.assertEqual(C.CAUSE_NONE, result.cause)

    def test_standalone_not_consumed(self):
        self.standalone_path.parent.mkdir(parents=True, exist_ok=True)
        self.standalone_path.write_text(
            json.dumps(
                {
                    login_scene_override.STANDALONE_JSON_KEY: {
                        self.GM_ACCOUNT: PORT_ROYAL
                    }
                }
            ),
            encoding="utf-8",
        )
        result = self.consume()
        self.assertEqual(C.STANDALONE_NOT_CONSUMED, result.outcome)
        self.assertEqual(C.CAUSE_NONE, result.cause)


class EqualityCountsTheCauseTests(unittest.TestCase):
    def test_two_failures_with_different_causes_are_not_equal(self):
        # Left out of `__eq__`, `== ConsumeResult(None, CONSUME_FAILED, X)`
        # would pass for cause Y -- an assertion that reads like it pins the
        # cause and pins nothing.
        self.assertNotEqual(
            C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED),
            C.ConsumeResult(
                None, C.CONSUME_FAILED, C.CAUSE_ENTRY_SURVIVED_CLAIM
            ),
        )

    def test_the_same_cause_is_still_equal(self):
        self.assertEqual(
            C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED),
            C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED),
        )

    def test_the_repr_names_the_cause(self):
        # It is what a stack trace or a debug log will show.
        self.assertIn(
            C.CAUSE_CLAIM_RAISED,
            repr(C.ConsumeResult(None, C.CONSUME_FAILED, C.CAUSE_CLAIM_RAISED)),
        )


if __name__ == "__main__":
    unittest.main()
