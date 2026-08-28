"""`gm/login_scene_consume.py`: a staged login scene is spent by one login.

The condition `COO-DECISION 20260829_0441` attached to approving
`/warp <scene_id>`: the override must be single-use, so the blast radius of
a staged scene is one login rather than "until somebody deletes a file on
the bridge".  Every test here is about that sentence, and about the one way
this could go wrong quietly -- a consume that reports success and leaves the
entry on disk, which would be worse than not consuming at all, because the
audit trail would then say the scene was spent.
"""
from __future__ import annotations

import json
import os
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

# Two scene_ids that are BOTH in the committed catalog and pinned as having
# a login entry (`stageable_scene_ids()` == (1, 2, 278, 997) on main).  Pinned
# as literals: a catalog or pin table that lost one should fail this file
# loudly rather than quietly agree with itself.
PORT_ROYAL = 1
PRISON_EXILE = 2


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    OTHER_GM = "GM_TWO"
    PLAYER = "DECKHAND"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT, self.OTHER_GM]}),
            encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"
        self.standalone_path = self.tmp / "config" / "standalone.json"

    def stage(self, account, scene_id):
        return login_scene_stage.stage_login_scene(
            account,
            scene_id,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )

    def consume(self, account):
        return login_scene_consume.consume_login_scene_override(
            account,
            gm_accounts_config_path=str(self.accounts_path),
            login_scene_config_path=str(self.config_path),
            standalone_config_path=str(self.standalone_path),
        )

    def write_standalone(self, account, scene_id):
        self.standalone_path.parent.mkdir(parents=True, exist_ok=True)
        self.standalone_path.write_text(
            json.dumps(
                {login_scene_override.STANDALONE_JSON_KEY: {account: scene_id}}
            ),
            encoding="utf-8",
        )

    def entries(self):
        return login_scene_override.load_login_scene_overrides(
            str(self.config_path)
        )


class SingleUseTests(_Case):
    def test_the_first_login_gets_the_scene(self):
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        result = self.consume(self.GM_ACCOUNT)
        self.assertEqual(PORT_ROYAL, result.scene_id)
        self.assertEqual(login_scene_consume.CONSUMED, result.outcome)

    def test_the_second_login_does_not(self):
        # The condition itself.  Not "the file is smaller" -- the next login
        # is back to ordinary behaviour, which is what a tester will see.
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        self.consume(self.GM_ACCOUNT)
        second = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(second.scene_id)
        self.assertEqual(login_scene_consume.NOTHING_STAGED, second.outcome)

    def test_the_entry_is_off_disk_read_through_the_login_path_itself(self):
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        self.consume(self.GM_ACCOUNT)
        self.assertIsNone(self.entries().get(self.GM_ACCOUNT))
        self.assertIsNone(
            login_scene_override.get_login_scene_override(
                self.GM_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
                standalone_config_path=str(self.standalone_path),
            )
        )

    def test_consuming_one_account_leaves_another_accounts_entry_alone(self):
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        self.assertTrue(self.stage(self.OTHER_GM, PRISON_EXILE).staged)
        self.consume(self.GM_ACCOUNT)
        self.assertEqual({self.OTHER_GM: PRISON_EXILE}, self.entries())

    def test_nothing_staged_is_not_an_error(self):
        result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.NOTHING_STAGED, result.outcome)
        self.assertFalse(self.config_path.exists())

    def test_a_non_gm_named_in_BOTH_files_keeps_its_gm_map_line(self):
        # Found by self-review, and it is the sharp version of the test
        # below.  A non-GM gets its scene from the STANDALONE map, so the
        # stale hand-written line in the GM-gated file is not what answered
        # -- and the remover deliberately does not re-check the allowlist,
        # so consuming on the entry alone would delete an allowlist-less
        # account's config line on its behalf.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.PLAYER: PORT_ROYAL}}),
            encoding="utf-8",
        )
        self.write_standalone(self.PLAYER, PRISON_EXILE)
        result = self.consume(self.PLAYER)
        self.assertEqual(PRISON_EXILE, result.scene_id)
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, result.outcome
        )
        self.assertEqual({self.PLAYER: PORT_ROYAL}, self.entries())

    def test_an_account_that_is_not_a_gm_gets_nothing_and_spends_nothing(self):
        # A name someone put in the file by hand, for an account the
        # allowlist does not list.  The reader already refuses it; this
        # pins that the consumer does not "helpfully" delete it either --
        # that would be this module editing a config on behalf of a
        # non-GM, which is the one thing this lane never does.
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"gm_login_scene": {self.PLAYER: PORT_ROYAL}}),
            encoding="utf-8",
        )
        result = self.consume(self.PLAYER)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.NOTHING_STAGED, result.outcome)
        self.assertEqual({self.PLAYER: PORT_ROYAL}, self.entries())


class FailClosedTests(_Case):
    def test_an_entry_that_cannot_be_removed_costs_the_warp_not_the_guarantee(self):
        # The rule worth arguing about: rather than granting a scene whose
        # override would outlive the login, the login goes to the default.
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        with mock.patch.object(
            login_scene_stage, "claim_login_scene", return_value=None
        ):
            result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)
        # And the entry is still there for an operator to find, not
        # half-erased.
        self.assertEqual(PORT_ROYAL, self.entries()[self.GM_ACCOUNT])

    def test_a_claim_that_raises_is_the_same_answer(self):
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        with mock.patch.object(
            login_scene_stage,
            "claim_login_scene",
            side_effect=OSError("disk went away"),
        ):
            result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)

    def test_a_read_only_config_directory_refuses_FOR_REAL(self):
        # No mock anywhere in this one.  The three tests above pin the
        # branches; this pins that the branches are reachable from a real
        # operating system, which is the half a mock can never show.
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        euid = getattr(os, "geteuid", None)
        bits_bite = os.name == "posix" and euid is not None and euid() != 0
        if bits_bite:
            self.config_path.parent.chmod(0o500)
            self.addCleanup(self.config_path.parent.chmod, 0o700)
        else:
            # Windows ignores the bit and so does root, so take the write
            # away where the real chmod takes it away: the temp file the
            # writer makes before it renames.
            patcher = mock.patch.object(
                login_scene_stage.tempfile,
                "mkstemp",
                side_effect=PermissionError(13, "Permission denied"),
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)
        self.assertEqual(PORT_ROYAL, self.entries()[self.GM_ACCOUNT])

    def test_a_remover_that_LIES_is_caught_inside_the_lock(self):
        # The quiet failure worth the extra read: a delete that reports
        # success and changed nothing.  Without the read-back inside
        # `claim_login_scene`, this login would get the scene AND keep the
        # override, with an audit row saying it was spent.  (Mutation-tested:
        # removing that read-back leaves every other test in this file
        # green.)
        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        real = login_scene_stage._write_entry_locked

        def lying(account_name, scene_id, config_path, **kwargs):
            if scene_id is None:
                return login_scene_stage.StageResult(
                    True, login_scene_stage.REASON_OK, None, None
                )
            return real(account_name, scene_id, config_path, **kwargs)

        with mock.patch.object(
            login_scene_stage, "_write_entry_locked", lying
        ):
            result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)
        self.assertEqual(PORT_ROYAL, self.entries()[self.GM_ACCOUNT])

    def test_a_malformed_config_does_not_take_the_login_down(self):
        # The first version let this RAISE out of a function whose whole
        # contract is "four outcomes, fail-closed".
        self.standalone_path.parent.mkdir(parents=True, exist_ok=True)
        self.standalone_path.write_text(
            json.dumps({login_scene_override.STANDALONE_JSON_KEY: [1, 2, 3]}),
            encoding="utf-8",
        )
        result = self.consume(self.GM_ACCOUNT)
        self.assertIsNone(result.scene_id)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)

    def test_a_str_subclass_is_refused_by_THIS_module_not_by_a_collaborator(self):
        class Sneaky(str):
            pass

        # Asserted against this module's own door: patching the delegate out
        # would leave a test that measures the collaborator instead.
        with mock.patch.object(
            login_scene_consume, "get_login_scene_override"
        ) as delegate:
            with self.assertRaises(TypeError):
                self.consume(Sneaky(self.GM_ACCOUNT))
        delegate.assert_not_called()

    def test_an_empty_account_name_is_refused_at_this_door_too(self):
        # Both collaborators raise on it; accepting it here only buys a
        # permanently unremovable entry reported as a disk fault.
        with self.assertRaises(ValueError):
            self.consume("")


class OnlyOneLoginGetsItTests(_Case):
    """The condition is single-USE, which is a race, not a file edit.

    MEASURED by pf-adversary against the first version of this module: with
    two threads on a barrier, BOTH logins received the staged scene and both
    recorded `consumed`, 400 trials out of 400.  The read-then-remove shape
    could not lose, because the remover it used reports success for a delete
    whether or not it was the caller that removed anything.
    """

    def test_two_concurrent_logins_produce_exactly_one_winner(self):
        import threading

        for _ in range(50):
            self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
            barrier = threading.Barrier(2)
            results = []
            lock = threading.Lock()

            def run():
                barrier.wait()
                outcome = self.consume(self.GM_ACCOUNT)
                with lock:
                    results.append(outcome)

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            winners = [r for r in results if r.scene_id is not None]
            self.assertEqual(1, len(winners), results)
            self.assertEqual(login_scene_consume.CONSUMED, winners[0].outcome)
            self.assertEqual(PORT_ROYAL, winners[0].scene_id)
            losers = [r for r in results if r.scene_id is None]
            self.assertEqual(1, len(losers), results)
            self.assertEqual(
                login_scene_consume.NOTHING_STAGED, losers[0].outcome
            )
            self.assertIsNone(self.entries().get(self.GM_ACCOUNT))


class StandaloneMapTests(_Case):
    """[สมมติของสาย GM - รอ COO ยืนยัน] -- see the module docstring."""

    def test_a_standalone_entry_is_used_but_not_spent(self):
        self.write_standalone(self.PLAYER, PRISON_EXILE)
        result = self.consume(self.PLAYER)
        self.assertEqual(PRISON_EXILE, result.scene_id)
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, result.outcome
        )
        self.assertEqual(
            {self.PLAYER: PRISON_EXILE},
            login_scene_override.load_standalone_login_scene_overrides(
                str(self.standalone_path)
            ),
        )

    def test_a_standalone_entry_still_works_on_the_second_login(self):
        self.write_standalone(self.PLAYER, PRISON_EXILE)
        self.consume(self.PLAYER)
        self.assertEqual(PRISON_EXILE, self.consume(self.PLAYER).scene_id)

    def test_the_gm_map_wins_and_only_the_gm_map_is_spent(self):
        # Both maps naming the same account, and deliberately the SAME
        # scene: consuming by scene_id instead of by which map answered
        # would take the wrong entry, and only a same-scene case shows it.
        self.assertTrue(self.stage(self.GM_ACCOUNT, PRISON_EXILE).staged)
        self.write_standalone(self.GM_ACCOUNT, PRISON_EXILE)
        first = self.consume(self.GM_ACCOUNT)
        self.assertEqual(PRISON_EXILE, first.scene_id)
        self.assertEqual(login_scene_consume.CONSUMED, first.outcome)
        self.assertIsNone(self.entries().get(self.GM_ACCOUNT))
        # The standalone entry survives, so the account falls back to it.
        second = self.consume(self.GM_ACCOUNT)
        self.assertEqual(PRISON_EXILE, second.scene_id)
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, second.outcome
        )


class GrantsNothingTests(_Case):
    def test_consuming_does_not_add_anyone_to_the_gm_allowlist(self):
        from pirateforce_foundation.gm import accounts as gm_accounts

        self.assertTrue(self.stage(self.GM_ACCOUNT, PORT_ROYAL).staged)
        self.consume(self.GM_ACCOUNT)
        self.assertEqual(
            frozenset({self.GM_ACCOUNT, self.OTHER_GM}),
            gm_accounts.load_gm_accounts(str(self.accounts_path)),
        )
        self.assertFalse(
            gm_accounts.is_gm_account(self.PLAYER, str(self.accounts_path))
        )

    def test_this_module_cannot_reach_the_standalone_writer(self):
        # A behavioural test only covers routes someone thought to write.
        # The standalone map is the one that works with NO allowlist
        # membership; nothing here may write to it.
        source = (
            REPO_ROOT
            / "src/pirateforce_foundation/gm/login_scene_consume.py"
        ).read_text(encoding="utf-8")
        import ast

        module = ast.parse(source)
        docstring = ast.get_docstring(module) or ""
        code = source.replace(docstring, "")
        code = "\n".join(
            line for line in code.splitlines()
            if not line.strip().startswith("#")
        )
        for forbidden in (
            login_scene_override.STANDALONE_JSON_KEY,
            "STANDALONE_DEFAULT_CONFIG_PATH",
            "stage_login_scene",
        ):
            self.assertNotIn(forbidden, code, forbidden)

    def test_the_permanent_identity_nonclaim_is_stated_in_the_module(self):
        # COO-DECISION 20260829_0441 made this a permanent NONCLAIM of the
        # module rather than a round note, so it is pinned like one.
        doc = login_scene_consume.__doc__ or ""
        self.assertIn("NONCLAIM", doc)
        self.assertIn("per-connection", doc)


if __name__ == "__main__":
    unittest.main()
