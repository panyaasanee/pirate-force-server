"""GM-005: gm_login_scene override -- GM-gated, catalog-validated, default empty."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.login_scene_override import (
    get_login_scene_override,
    load_login_scene_overrides,
    load_standalone_login_scene_overrides,
)

KNOWN_SCENE_ID = 2  # Prison Exile Island -- see gm/scene_catalog.py
UNKNOWN_SCENE_ID = 999999


class GmLoginSceneDefaultTests(unittest.TestCase):
    def test_missing_config_file_means_no_override_for_anyone(self):
        with tempfile.TemporaryDirectory() as tmp:
            gm_accounts = Path(tmp) / "gm_accounts.json"
            gm_accounts.write_text(
                json.dumps({"gm_accounts": ["localtest"]}), encoding="utf-8"
            )
            missing_overrides = Path(tmp) / "does_not_exist.json"
            self.assertEqual(load_login_scene_overrides(missing_overrides), {})
            self.assertIsNone(
                get_login_scene_override("localtest", gm_accounts, missing_overrides)
            )

    def test_empty_gm_login_scene_map_means_no_override_for_anyone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene.json"
            path.write_text(json.dumps({"gm_login_scene": {}}), encoding="utf-8")
            self.assertEqual(load_login_scene_overrides(path), {})


class GmLoginSceneGatingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.gm_accounts_path = tmp / "gm_accounts.json"
        self.gm_accounts_path.write_text(
            json.dumps({"gm_accounts": ["localtest"]}), encoding="utf-8"
        )
        self.overrides_path = tmp / "gm_login_scene.json"
        self.overrides_path.write_text(
            json.dumps(
                {"gm_login_scene": {"localtest": KNOWN_SCENE_ID, "not_a_gm": KNOWN_SCENE_ID}}
            ),
            encoding="utf-8",
        )

    def test_listed_gm_account_with_entry_gets_its_scene_id(self):
        self.assertEqual(
            get_login_scene_override(
                "localtest", self.gm_accounts_path, self.overrides_path
            ),
            KNOWN_SCENE_ID,
        )

    def test_gm_account_without_entry_gets_none(self):
        self.gm_accounts_path.write_text(
            json.dumps({"gm_accounts": ["localtest", "other_gm"]}), encoding="utf-8"
        )
        self.assertIsNone(
            get_login_scene_override(
                "other_gm", self.gm_accounts_path, self.overrides_path
            )
        )

    def test_non_gm_account_gets_none_even_with_an_override_entry(self):
        # "not_a_gm" has an entry in gm_login_scene.json above but is absent
        # from gm_accounts.json -- the override config alone must never grant
        # anything; gm_accounts.json is the only place that grants GM status.
        self.assertIsNone(
            get_login_scene_override(
                "not_a_gm", self.gm_accounts_path, self.overrides_path
            )
        )

    def test_unlisted_player_gets_none(self):
        self.assertIsNone(
            get_login_scene_override(
                "some_player", self.gm_accounts_path, self.overrides_path
            )
        )


class GmLoginSceneMalformedConfigTests(unittest.TestCase):
    def test_non_dict_gm_login_scene_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene.json"
            path.write_text(json.dumps({"gm_login_scene": [1, 2]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_login_scene_overrides(path)

    def test_non_int_scene_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene.json"
            path.write_text(
                json.dumps({"gm_login_scene": {"localtest": "2"}}), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_login_scene_overrides(path)

    def test_bool_scene_id_raises(self):
        # bool is a subclass of int in Python -- must be rejected explicitly,
        # not silently accepted as scene_id 0 or 1.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene.json"
            path.write_text(
                json.dumps({"gm_login_scene": {"localtest": True}}), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_login_scene_overrides(path)

    def test_unknown_scene_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene.json"
            path.write_text(
                json.dumps({"gm_login_scene": {"localtest": UNKNOWN_SCENE_ID}}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_login_scene_overrides(path)

    def test_get_login_scene_override_rejects_non_str_account_name(self):
        with self.assertRaises(TypeError):
            get_login_scene_override(12345)

    def test_get_login_scene_override_rejects_a_str_subclass_regardless_of_dunders(self):
        # pf-adversary (gm/ package sweep): same failure shape as
        # accounts.is_gm_account's own EvilStr test -- a str subclass lying
        # through __eq__/__hash__ could otherwise resolve a dict.get() below
        # to a different account's override entry. type(account_name) is str
        # rejects it before either dict lookup runs.
        class EvilStr(str):
            def __eq__(self, other):
                return True

            def __hash__(self):
                return hash("localtest")

        with tempfile.TemporaryDirectory() as tmp:
            gm_accounts = Path(tmp) / "gm_accounts.json"
            gm_accounts.write_text(
                json.dumps({"gm_accounts": ["localtest"]}), encoding="utf-8"
            )
            overrides = Path(tmp) / "gm_login_scene.json"
            overrides.write_text(
                json.dumps({"gm_login_scene": {"localtest": KNOWN_SCENE_ID}}),
                encoding="utf-8",
            )
            self.assertEqual(
                get_login_scene_override("localtest", gm_accounts, overrides),
                KNOWN_SCENE_ID,
            )
            with self.assertRaises(TypeError):
                get_login_scene_override(
                    EvilStr("totally_not_a_gm"), gm_accounts, overrides
                )

    def test_non_object_top_level_json_raises_value_error(self):
        # A JSON list/string/null at the top level must fail loud with
        # ValueError like every other malformed shape here, not fall through
        # to an unhandled AttributeError from a bare dict.get() call.
        for bad_top_level in ([1, 2, 3], "not an object", None):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "gm_login_scene.json"
                path.write_text(json.dumps(bad_top_level), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_login_scene_overrides(path)


class GmLoginSceneRevocationTests(unittest.TestCase):
    def test_revoking_gm_status_removes_the_override_on_the_next_call(self):
        # Not cached: an account that loses its GM listing must stop getting
        # its scene override on the very next call, with no code change and
        # no restart -- this is the actual claim get_login_scene_override's
        # docstring makes ("checked fresh on every call, not cached").
        with tempfile.TemporaryDirectory() as tmp:
            gm_accounts_path = Path(tmp) / "gm_accounts.json"
            overrides_path = Path(tmp) / "gm_login_scene.json"
            gm_accounts_path.write_text(
                json.dumps({"gm_accounts": ["localtest"]}), encoding="utf-8"
            )
            overrides_path.write_text(
                json.dumps({"gm_login_scene": {"localtest": KNOWN_SCENE_ID}}),
                encoding="utf-8",
            )
            self.assertEqual(
                get_login_scene_override("localtest", gm_accounts_path, overrides_path),
                KNOWN_SCENE_ID,
            )

            gm_accounts_path.write_text(
                json.dumps({"gm_accounts": []}), encoding="utf-8"
            )
            self.assertIsNone(
                get_login_scene_override("localtest", gm_accounts_path, overrides_path)
            )


class GmLoginSceneStandaloneTests(unittest.TestCase):
    """Standalone path (GT-110 safety fix): scene override with no GM status.

    Answers notes_to_chief/20260827_2240_KA1A-NOTE-GT110-unsafe-until-0x5A19-
    payload-fixed-plus-M1P-jobs-staged.md's proposal to decouple the login-
    scene override from GM_UpdateGMStateVital (0x5A19) risk -- an account
    listed only here never becomes is_gm_account()==True, so runtime.py's
    guarded GM-state-frame block (CORE-REQUEST-016) never fires for it.
    [สมมติของสาย GM - รอ COO ยืนยัน]
    """

    def test_missing_standalone_file_means_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist.json"
            self.assertEqual(load_standalone_login_scene_overrides(missing), {})

    def test_standalone_entry_grants_override_with_no_gm_listing_anywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            gm_accounts_path = tmp / "gm_accounts.json"
            gm_accounts_path.write_text(
                json.dumps({"gm_accounts": []}), encoding="utf-8"
            )
            gm_login_scene_path = tmp / "gm_login_scene.json"
            gm_login_scene_path.write_text(
                json.dumps({"gm_login_scene": {}}), encoding="utf-8"
            )
            standalone_path = tmp / "gm_login_scene_standalone.json"
            standalone_path.write_text(
                json.dumps(
                    {"standalone_login_scene": {"gt110_tester": KNOWN_SCENE_ID}}
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                get_login_scene_override(
                    "gt110_tester",
                    gm_accounts_path,
                    gm_login_scene_path,
                    standalone_path,
                ),
                KNOWN_SCENE_ID,
            )

    def test_standalone_path_never_reads_or_requires_gm_accounts_file(self):
        # gm_accounts_config_path points at a file that does not exist at
        # all -- is_gm_account() must tolerate that (existing "absence is
        # empty" rule) and the standalone path must still resolve.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            missing_gm_accounts = tmp / "does_not_exist.json"
            standalone_path = tmp / "gm_login_scene_standalone.json"
            standalone_path.write_text(
                json.dumps(
                    {"standalone_login_scene": {"gt110_tester": KNOWN_SCENE_ID}}
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                get_login_scene_override(
                    "gt110_tester",
                    missing_gm_accounts,
                    missing_gm_accounts,
                    standalone_path,
                ),
                KNOWN_SCENE_ID,
            )

    def test_account_absent_from_standalone_config_gets_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            standalone_path = tmp / "gm_login_scene_standalone.json"
            standalone_path.write_text(
                json.dumps({"standalone_login_scene": {"someone_else": KNOWN_SCENE_ID}}),
                encoding="utf-8",
            )
            self.assertIsNone(
                get_login_scene_override(
                    "gt110_tester", None, None, standalone_path
                )
            )

    def test_gm_gated_path_still_wins_when_both_paths_have_an_entry(self):
        # Not a load-bearing claim (either path alone is documented as
        # sufficient) but pins current behavior: the GM-gated branch is
        # checked first, so an account present in both configs still gets a
        # deterministic single scene_id, not an error from two answers.
        # DELIBERATELY uses two DIFFERENT scene_ids for the gated vs.
        # standalone entries -- pf-adversary (round ccc9wj) found that the
        # original version of this test used the same scene_id for both,
        # which cannot distinguish "gated path answered" from "standalone
        # path answered" and would still pass a broken implementation that
        # checks standalone first.
        GATED_SCENE_ID = 2  # Prison Exile Island
        STANDALONE_SCENE_ID = 1  # Port Royal -- must NOT be what this returns
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            gm_accounts_path = tmp / "gm_accounts.json"
            gm_accounts_path.write_text(
                json.dumps({"gm_accounts": ["localtest"]}), encoding="utf-8"
            )
            gm_login_scene_path = tmp / "gm_login_scene.json"
            gm_login_scene_path.write_text(
                json.dumps({"gm_login_scene": {"localtest": GATED_SCENE_ID}}),
                encoding="utf-8",
            )
            standalone_path = tmp / "gm_login_scene_standalone.json"
            standalone_path.write_text(
                json.dumps(
                    {"standalone_login_scene": {"localtest": STANDALONE_SCENE_ID}}
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                get_login_scene_override(
                    "localtest",
                    gm_accounts_path,
                    gm_login_scene_path,
                    standalone_path,
                ),
                GATED_SCENE_ID,
            )

    def test_standalone_malformed_config_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene_standalone.json"
            path.write_text(
                json.dumps({"standalone_login_scene": [1, 2]}), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_standalone_login_scene_overrides(path)

    def test_standalone_unknown_scene_id_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gm_login_scene_standalone.json"
            path.write_text(
                json.dumps(
                    {"standalone_login_scene": {"gt110_tester": UNKNOWN_SCENE_ID}}
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_standalone_login_scene_overrides(path)


if __name__ == "__main__":
    unittest.main()
