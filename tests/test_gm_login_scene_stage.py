"""`gm/login_scene_stage.py`: what may be written, and what must survive a refusal.

The two properties this file exists to hold, in the order they matter:

1. NOTHING HERE CAN GRANT ANYTHING.  Only the GM-gated map is writable, only
   for an account `gm_accounts.json` already lists, and only a scene_id the
   committed catalog knows.  The standalone map -- the one that works WITHOUT
   `gm_accounts.json` membership -- is not reachable from this module by any
   route, checked here against the module's own source as well as by
   behaviour, because a behavioural test only covers the paths someone
   thought to write.

2. A REFUSAL LEAVES THE FILE ALONE.  Every failure mode (not a GM, unknown
   scene, malformed config, unwritable directory, a read-back that disagrees)
   has to leave `config/gm_login_scene.json` byte-identical to what an
   operator had.  A config writer that "repairs" a file it did not understand
   is worse than one that refuses.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    login_scene_override,
    login_scene_stage,
)

# Three scene_ids the committed catalog knows (GM-004), pinned as literals
# rather than read out of the catalog: a catalog that lost Port Royal should
# fail this file loudly, not quietly agree with itself.
PORT_ROYAL = 1
PRISON_EXILE = 2
SPICE_PARADISE = 3
# Not in the 330-scene table.  If this ever becomes a real scene, this file
# fails and the number gets changed -- which is the correct amount of noise.
UNKNOWN_SCENE = 999999


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    OTHER_GM = "GM_TWO"
    PLAYER = "DECKHAND"

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT, self.OTHER_GM]}),
            encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"

    def stage(self, account, scene_id, **kwargs):
        kwargs.setdefault("gm_accounts_config_path", str(self.accounts_path))
        kwargs.setdefault("config_path", str(self.config_path))
        return login_scene_stage.stage_login_scene(account, scene_id, **kwargs)

    def entries(self):
        if not self.config_path.exists():
            return None
        return json.loads(self.config_path.read_text(encoding="utf-8"))


class GrantsNothingTests(_Case):
    def test_an_account_that_is_not_a_listed_gm_stages_nothing(self):
        result = self.stage(self.PLAYER, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_NOT_GM_ACCOUNT, result.reason)
        # Not "an empty entry" and not "a file with no entries": no file.
        self.assertFalse(self.config_path.exists())

    def test_an_unknown_scene_id_stages_nothing(self):
        result = self.stage(self.GM_ACCOUNT, UNKNOWN_SCENE)
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_UNKNOWN_SCENE, result.reason)
        self.assertFalse(self.config_path.exists())

    def test_staging_does_not_add_anyone_to_the_gm_allowlist(self):
        self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertFalse(
            gm_accounts.is_gm_account(self.PLAYER, str(self.accounts_path))
        )
        self.assertEqual(
            frozenset({self.GM_ACCOUNT, self.OTHER_GM}),
            gm_accounts.load_gm_accounts(str(self.accounts_path)),
        )

    def test_a_staged_entry_stops_applying_when_the_account_leaves_the_allowlist(self):
        # The entry is worth nothing on its own: `get_login_scene_override`
        # re-checks membership at LOGIN time, so removing the account from
        # gm_accounts.json is enough to disarm a staged entry -- an operator
        # does not have to find and delete the other file too.
        self.assertTrue(self.stage(self.GM_ACCOUNT, SPICE_PARADISE).staged)
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.OTHER_GM]}), encoding="utf-8"
        )
        self.assertIsNone(
            login_scene_override.get_login_scene_override(
                self.GM_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
                standalone_config_path=str(self.tmp / "nonexistent.json"),
            )
        )

    def test_the_standalone_map_is_not_reachable_from_this_module(self):
        # A behavioural test only covers routes someone thought to write, so
        # this reads the module's own source.  The standalone path grants a
        # login scene to an account with NO gm_accounts.json membership; a
        # writer that could reach it would be a way to give an unlisted
        # account a server-side effect.
        source = (
            REPO_ROOT
            / "src/pirateforce_foundation/gm/login_scene_stage.py"
        ).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        # The docstring names the standalone map to explain why it is barred;
        # strip it before scanning so the explanation cannot fail its own rule.
        import ast

        module = ast.parse(source)
        docstring = ast.get_docstring(module) or ""
        code = code.replace(docstring, "")
        for forbidden in (
            "standalone_login_scene",
            "gm_login_scene_standalone",
            "STANDALONE",
            "load_standalone_login_scene_overrides",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_staging_never_writes_the_standalone_config_file(self):
        standalone = self.tmp / "config" / "gm_login_scene_standalone.json"
        self.assertTrue(self.stage(self.GM_ACCOUNT, PRISON_EXILE).staged)
        self.assertFalse(standalone.exists())


class WritesWhatTheReaderReadsTests(_Case):
    def test_a_staged_scene_is_what_the_login_path_resolves(self):
        result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertTrue(result.staged)
        self.assertEqual(SPICE_PARADISE, result.scene_id)
        self.assertIsNone(result.previous_scene_id)
        self.assertEqual(
            SPICE_PARADISE,
            login_scene_override.get_login_scene_override(
                self.GM_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
                standalone_config_path=str(self.tmp / "nonexistent.json"),
            ),
        )

    def test_the_json_key_is_the_literal_the_reader_looks_for(self):
        # Pinned as a literal, not as the constant both sides import: a
        # renamed constant would otherwise keep every test green while the
        # login path read a key nobody writes (the mutation lesson from
        # round `nz0qt2`'s audit constants).
        self.stage(self.GM_ACCOUNT, PORT_ROYAL)
        self.assertEqual({"gm_login_scene": {"GM_ONE": 1}}, self.entries())

    def test_restaging_replaces_the_account_entry_and_reports_the_old_one(self):
        self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertTrue(result.staged)
        self.assertEqual(PRISON_EXILE, result.previous_scene_id)
        self.assertEqual({"gm_login_scene": {"GM_ONE": 3}}, self.entries())

    def test_another_gms_entry_and_unrelated_keys_survive(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(
                {
                    "_comment": "hand written by the operator",
                    "gm_login_scene": {self.OTHER_GM: PRISON_EXILE},
                }
            ),
            encoding="utf-8",
        )
        self.assertTrue(self.stage(self.GM_ACCOUNT, SPICE_PARADISE).staged)
        self.assertEqual(
            {
                "_comment": "hand written by the operator",
                "gm_login_scene": {"GM_TWO": 2, "GM_ONE": 3},
            },
            self.entries(),
        )

    def test_the_env_var_the_reader_obeys_is_the_file_the_writer_writes(self):
        # A writer that staged into the default path while the listener booted
        # with PF_GM_LOGIN_SCENE_CONFIG set would look like it worked and
        # change nothing the login path ever reads.
        env_target = self.tmp / "env" / "elsewhere.json"
        with mock.patch.dict(
            os.environ, {login_scene_override.ENV_OVERRIDE: str(env_target)}
        ):
            result = login_scene_stage.stage_login_scene(
                self.GM_ACCOUNT,
                PRISON_EXILE,
                gm_accounts_config_path=str(self.accounts_path),
            )
            self.assertTrue(result.staged)
            self.assertEqual(
                {self.GM_ACCOUNT: PRISON_EXILE},
                login_scene_override.load_login_scene_overrides(),
            )
        self.assertTrue(env_target.is_file())
        self.assertFalse(self.config_path.exists())

    def test_the_written_file_is_ascii_only(self):
        # cp874 consoles and editors: an escaped non-ASCII account name
        # round-trips through any editor, a raw UTF-8 one comes back mojibake
        # and gets "fixed" into something the allowlist no longer matches.
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["GM_ก"]}), encoding="utf-8"
        )
        self.assertTrue(self.stage("GM_ก", PRISON_EXILE).staged)
        raw = self.config_path.read_bytes()
        self.assertTrue(all(byte < 128 for byte in raw), raw)
        self.assertEqual(
            {"GM_ก": PRISON_EXILE},
            login_scene_override.load_login_scene_overrides(str(self.config_path)),
        )

    @unittest.skipIf(os.name == "nt", "POSIX mode bits; NTFS ignores this split")
    def test_the_config_file_is_not_world_readable(self):
        self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertEqual(0o600, self.config_path.stat().st_mode & 0o777)

    def test_no_temp_file_is_left_behind(self):
        self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        leftovers = [
            path.name
            for path in self.config_path.parent.iterdir()
            if path.name != self.config_path.name
        ]
        self.assertEqual([], leftovers)


class RefusalLeavesTheFileAloneTests(_Case):
    def _write_raw(self, text):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(text, encoding="utf-8")
        return self.config_path.read_bytes()

    def test_a_config_that_is_not_json_is_refused_and_untouched(self):
        original = self._write_raw("{not json at all")
        result = self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_CONFIG_UNREADABLE, result.reason
        )
        self.assertEqual(original, self.config_path.read_bytes())

    def test_a_config_whose_top_level_is_not_an_object_is_refused(self):
        original = self._write_raw("[1, 2, 3]")
        result = self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_CONFIG_UNREADABLE, result.reason
        )
        self.assertEqual(original, self.config_path.read_bytes())

    def test_a_config_the_login_path_would_reject_is_refused_not_repaired(self):
        # Someone else's entry names a scene the catalog does not know, so
        # `load_login_scene_overrides` raises at login.  Writing our entry
        # into that file would hide their typo under a working-looking config.
        original = self._write_raw(
            json.dumps({"gm_login_scene": {self.OTHER_GM: UNKNOWN_SCENE}})
        )
        result = self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_CONFIG_UNREADABLE, result.reason
        )
        self.assertEqual(original, self.config_path.read_bytes())

    @unittest.skipIf(os.name == "nt", "POSIX directory permissions")
    @unittest.skipIf(os.geteuid() == 0, "root ignores directory write bits")
    def test_an_unwritable_directory_is_refused_and_the_old_file_survives(self):
        original = self._write_raw(
            json.dumps({"gm_login_scene": {self.OTHER_GM: PRISON_EXILE}})
        )
        directory = self.config_path.parent
        directory.chmod(0o500)
        self.addCleanup(directory.chmod, 0o700)
        result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_WRITE_FAILED, result.reason)
        self.assertEqual(original, self.config_path.read_bytes())

    def test_a_read_back_that_disagrees_restores_the_original_bytes(self):
        # The last line of defence: whatever went wrong, the file we leave
        # behind is the file we found.  Simulated by making the read-back
        # return something else, which is what a racing writer would do.
        original = self._write_raw(
            json.dumps({"gm_login_scene": {self.OTHER_GM: PRISON_EXILE}})
        )
        real_loader = login_scene_override.load_login_scene_overrides
        calls = []

        def flaky(path=None):
            calls.append(path)
            if len(calls) > 1:
                return {}
            return real_loader(path)

        with mock.patch.object(
            login_scene_stage, "load_login_scene_overrides", flaky
        ):
            result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_WRITE_FAILED, result.reason)
        self.assertEqual(original, self.config_path.read_bytes())

    def test_a_failed_first_stage_leaves_no_file_at_all(self):
        # The same restore, in the case where the original was "no file":
        # a leftover empty config is not neutral, it is a file the operator
        # now has to reason about.
        real_loader = login_scene_override.load_login_scene_overrides
        calls = []

        def flaky(path=None):
            calls.append(path)
            if len(calls) > 1:
                return {}
            return real_loader(path)

        with mock.patch.object(
            login_scene_stage, "load_login_scene_overrides", flaky
        ):
            result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertFalse(result.staged)
        self.assertFalse(self.config_path.exists())


class TheOperatorsOwnFileTests(_Case):
    """Two ways this writer used to walk over an operator's intent, both found
    by probing rather than by reading, and both fixed in the same round."""

    @unittest.skipIf(os.name == "nt", "POSIX symlinks")
    def test_a_symlinked_config_is_written_THROUGH_not_replaced(self):
        # MEASURED, before the fix: `os.replace` renames onto the path it is
        # given, and the path it is given was the LINK.  The link became a
        # regular file, the target kept the old content, and the login path
        # silently started reading a different file from the one the operator
        # maintains.  Two configs, no error, no way to notice.
        real = self.tmp / "elsewhere" / "kept_here.json"
        real.parent.mkdir(parents=True)
        real.write_text(
            json.dumps({"gm_login_scene": {self.OTHER_GM: PRISON_EXILE}}),
            encoding="utf-8",
        )
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(real, self.config_path)

        self.assertTrue(self.stage(self.GM_ACCOUNT, SPICE_PARADISE).staged)
        self.assertTrue(self.config_path.is_symlink())
        self.assertEqual(
            {"gm_login_scene": {"GM_TWO": 2, "GM_ONE": 3}},
            json.loads(real.read_text(encoding="utf-8")),
        )

    @unittest.skipIf(os.name == "nt", "POSIX mode bits")
    @unittest.skipIf(os.geteuid() == 0, "root ignores the write bit")
    def test_a_config_the_operator_made_read_only_is_refused(self):
        # `os.replace` needs the DIRECTORY's write bit, not the file's, so
        # `chmod 400` -- an operator saying "do not touch this" in the only
        # way a file can say it -- was silently overwritten and came back
        # 0o600.  Measured before the fix; refusing costs one os.access call.
        original = json.dumps({"gm_login_scene": {}})
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(original, encoding="utf-8")
        self.config_path.chmod(0o400)
        self.addCleanup(self.config_path.chmod, 0o600)

        result = self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_CONFIG_NOT_WRITABLE, result.reason
        )
        self.assertEqual(original, self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(0o400, self.config_path.stat().st_mode & 0o777)

    def test_a_failed_rename_leaves_no_temp_file_behind(self):
        # The refusal is not the interesting half: a `.gm_login_scene.XXXX`
        # left in `config/` would be one more file an operator has to reason
        # about, next to the one they actually maintain.
        with mock.patch("os.replace", side_effect=OSError("boom")):
            result = self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_WRITE_FAILED, result.reason)
        self.assertEqual([], list(self.config_path.parent.iterdir()))


class HostileArgumentTests(_Case):
    def test_a_bool_is_not_a_scene_id(self):
        # bool subclasses int; `True` would otherwise stage scene 1.
        with self.assertRaises(TypeError):
            self.stage(self.GM_ACCOUNT, True)
        self.assertFalse(self.config_path.exists())

    def test_a_str_subclass_account_is_refused_outright(self):
        # The allowlist bypass `accounts.is_gm_account` documents: a subclass
        # lying through __eq__/__hash__ would otherwise become a dict KEY in
        # the config file, serialized as whatever __str__ says.
        class Liar(str):
            def __eq__(self, other):
                return True

            def __hash__(self):
                return hash("GM_ONE")

        with self.assertRaises(TypeError):
            self.stage(Liar("nobody"), PRISON_EXILE)
        self.assertFalse(self.config_path.exists())

    def test_an_empty_account_name_is_refused(self):
        with self.assertRaises(ValueError):
            self.stage("", PRISON_EXILE)


class RestoreTests(_Case):
    def restore(self, account, previous):
        return login_scene_stage.restore_login_scene(
            account,
            previous,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.config_path),
        )

    def test_restore_puts_back_the_previous_scene(self):
        self.stage(self.GM_ACCOUNT, PRISON_EXILE)
        result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertTrue(self.restore(self.GM_ACCOUNT, result.previous_scene_id))
        self.assertEqual({"gm_login_scene": {"GM_ONE": 2}}, self.entries())

    def test_restore_of_a_first_stage_removes_the_entry_entirely(self):
        result = self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertIsNone(result.previous_scene_id)
        self.assertTrue(self.restore(self.GM_ACCOUNT, None))
        self.assertEqual({"gm_login_scene": {}}, self.entries())
        self.assertIsNone(
            login_scene_override.load_login_scene_overrides(
                str(self.config_path)
            ).get(self.GM_ACCOUNT)
        )

    def test_restore_leaves_other_accounts_alone(self):
        self.stage(self.OTHER_GM, PRISON_EXILE)
        self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.assertTrue(self.restore(self.GM_ACCOUNT, None))
        self.assertEqual({"gm_login_scene": {"GM_TWO": 2}}, self.entries())

    def test_restore_works_after_the_account_left_the_allowlist(self):
        # A config edit between the stage and the undo must not strand the
        # entry the undo exists to remove.
        self.stage(self.GM_ACCOUNT, SPICE_PARADISE)
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.OTHER_GM]}), encoding="utf-8"
        )
        self.assertTrue(self.restore(self.GM_ACCOUNT, None))
        self.assertEqual({"gm_login_scene": {}}, self.entries())


if __name__ == "__main__":
    unittest.main()
