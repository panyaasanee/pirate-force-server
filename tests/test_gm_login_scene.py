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


if __name__ == "__main__":
    unittest.main()
