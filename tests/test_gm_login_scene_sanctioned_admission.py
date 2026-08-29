"""The single-use map may name a sanctioned-barred scene; the other may not.

WHAT LANDED, and what this file is here to stop from quietly un-landing.
`CORE-REQUEST-GM-038` wired `via_login=False` into `runtime.py` for a
sanctioned-barred destination, gated on the CONSUMED outcome
(runtime.py:5726).  That removed the login path's refusal for exactly one
set of scenes, and this lane's half is the admission that lets an entry
naming one of them reach that path at all
(`gm/login_scene_admission.single_use_entry_is_admissible`).

THE THREE PROPERTIES, because the widening is only safe if all three hold
together and each is cheap to break by accident:

1. The widening is BOUND TO THE MAP THAT IS SPENT.  The standalone map is
   never consumed (`COO-DECISION 20260829_0542`), so chief's bypass never
   applies to it, so a sanctioned scene admitted there would be refused at
   login and on every retry -- the permanent lockout `login_scene_admission`
   was written to close.  `TheStandaloneMapNeverWidensTests`.
2. A SANCTION IS NOT A ROUTE.  Only the blocker the bypass actually fixes
   (`BLOCKER_LOGIN_PATH_BARS_IT`) admits.  A sanctioned scene with no lane A
   row, or a row with no spawn, is still refused -- those refuse for reasons
   `via_login=False` does not touch.  `OnlyTheBlockerTheBypassFixesTests`.
3. CONSUME AND RESTORE BELIEVE THE SAME RULE.  This is the question chief's
   letter of 2026-08-29T22:22+07:00 asked (pf-adversary D5): if the widening
   went in on the consume side alone, the put-back after a refused login
   would judge the same entry by the narrow rule, refuse the whole file, and
   the operator's entry would be DESTROYED
   (`gm_login_scene_override_lost_to_refusal_<n>`) instead of returned.
   `TheUndoBelievesTheSameRuleTests`.

WHAT IS NOT CLAIMED HERE.  Nothing in this file claims a byte reached a
client, that anybody warped anywhere, or that scene 126 is reachable in
game.  These are module-layer facts about which scene ids two config
readers accept.  MEASURED on main this round: lane A's registry row for 126
does not exist yet (`sanctioned_barred_blocker(126) ==
lane_a_registry_row_missing`), so the widening admits NOTHING today and the
route is still one merge short.  The tests below that need the row supply a
STAND-IN registry rather than waiting for it -- which is also what makes
them keep working the day the real row lands.

NONCLAIM (GM lane rule): every route exercised here is a GM shortcut.  A
tester who reaches scene 126 this way has skipped whatever in-game travel
would normally take them there; seeing the scene is not evidence that the
travel to it works.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import login_scene_admission  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402

A = login_scene_admission


def the_only_sanctioned_scene() -> int:
    """The id the sanction map names, taken from the map itself.

    Not the literal 126: the map is where the chief letters are recorded,
    and a test that hardcodes its contents stops testing the rule the day a
    second letter lands.
    """
    ids = sorted(A.SANCTIONED_BARRED_SCENES)
    if not ids:
        raise unittest.SkipTest("no sanctioned scene to test the widening with")
    return ids[0]


SANCTIONED = the_only_sanctioned_scene()


def registry_with_sanctioned_row(*, login_entry_allowed=False, spawn=True):
    """Lane A's registry PLUS the row `CHIEF-DECISION 20260829_1603` asks for.

    A stand-in, and it says so: lane A owns that row and has not landed it
    (measured on main this round).  Built by copying a real pinned row so
    every field this lane does not care about is whatever lane A's own
    loader produces, rather than a shape invented here that could pass a
    predicate the real one would fail.
    """
    base = world_scene_travel.load_scene_registry()
    template = base[world_scene_travel.HOME_SCENE_ID]
    row = replace(
        template,
        n_id=SANCTIONED,
        login_entry_allowed=login_entry_allowed,
        spawn=template.spawn if spawn else None,
    )
    return world_scene_travel.SceneRegistry(destinations=base.destinations + (row,))


class TheSanctionAdmitsNothingOnMainTodayTests(unittest.TestCase):
    """The state of the route as measured, not as hoped.

    This class goes RED the day lane A lands the row -- deliberately.  At
    that moment the sentence "the widening admits nothing today" in this
    file's docstring, in `login_scene_admission`'s header, and in the round
    letter all stop being true at once, and somebody has to come and say so
    rather than leaving three documents lying.
    """

    def test_lane_a_has_not_landed_the_row_yet(self):
        self.assertEqual(
            A.BLOCKER_NO_REGISTRY_ROW,
            A.sanctioned_barred_blocker(SANCTIONED),
            "if this is red, lane A landed the row: re-read this file's "
            "docstring and the round letter, both of which say it had not",
        )

    def test_so_the_widening_admits_nothing_today(self):
        self.assertFalse(A.single_use_entry_is_admissible(SANCTIONED))
        self.assertEqual(
            A.stageable_scene_ids(), A.single_use_stageable_scene_ids()
        )


class OnlyTheBlockerTheBypassFixesTests(unittest.TestCase):
    """A sanction is a letter saying a destination is wanted, not a route."""

    def test_the_login_bar_alone_is_admitted(self):
        registry = registry_with_sanctioned_row()
        self.assertEqual(
            A.BLOCKER_LOGIN_PATH_BARS_IT,
            A.sanctioned_barred_blocker(SANCTIONED, scene_registry=registry),
        )
        self.assertTrue(
            A.single_use_entry_is_admissible(SANCTIONED, scene_registry=registry)
        )

    def test_a_row_with_no_spawn_is_still_refused(self):
        # `REFUSED_NO_PINNED_SPAWN` is not `REFUSED_NOT_ALLOWED_AT_LOGIN`,
        # and chief's bypass only removes the second.  Admitting this would
        # write an entry the login path refuses for a reason nothing in this
        # lane has bypassed.
        registry = registry_with_sanctioned_row(spawn=False)
        self.assertEqual(
            A.BLOCKER_NO_PINNED_SPAWN,
            A.sanctioned_barred_blocker(SANCTIONED, scene_registry=registry),
        )
        self.assertFalse(
            A.single_use_entry_is_admissible(SANCTIONED, scene_registry=registry)
        )

    def test_a_missing_row_is_still_refused(self):
        # The state on main today, asserted through the parameter rather
        # than through the disk so it keeps testing the rule after the row
        # lands.
        registry = world_scene_travel.load_scene_registry()
        self.assertEqual(
            A.BLOCKER_NO_REGISTRY_ROW,
            A.sanctioned_barred_blocker(SANCTIONED, scene_registry=registry),
        )
        self.assertFalse(
            A.single_use_entry_is_admissible(SANCTIONED, scene_registry=registry)
        )

    def test_an_unsanctioned_scene_gains_nothing(self):
        # The widening is not "barred scenes are now fine".  Scene 17 is
        # pinned `login_entry_allowed: false` and named by no letter.
        registry = world_scene_travel.load_scene_registry()
        for scene_id in registry.ids:
            if scene_id in A.SANCTIONED_BARRED_SCENES:
                continue
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    A.login_entry_is_pinned(scene_id, scene_registry=registry),
                    A.single_use_entry_is_admissible(
                        scene_id, scene_registry=registry
                    ),
                    "the widening may differ from the plain rule ONLY for a "
                    "scene a chief letter names",
                )

    def test_the_plain_predicate_is_not_widened(self):
        registry = registry_with_sanctioned_row()
        self.assertFalse(
            A.login_entry_is_pinned(SANCTIONED, scene_registry=registry),
            "`login_entry_is_pinned` is the standalone map's rule and the "
            "login path's own question; widening it is the reversal this "
            "whole design refused",
        )
        self.assertNotIn(
            SANCTIONED, A.stageable_scene_ids(scene_registry=registry)
        )
        self.assertIn(
            SANCTIONED, A.single_use_stageable_scene_ids(scene_registry=registry)
        )

    def test_a_bad_type_raises_the_way_the_plain_predicate_does(self):
        for value in ("126", 126.0, True, None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    A.single_use_entry_is_admissible(value)


class _ConfigCase(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.gm_map_path = self.tmp / "gm_login_scene.json"
        self.standalone_path = self.tmp / "gm_login_scene_standalone.json"

    def write_gm_map(self, scene_id):
        self.gm_map_path.write_text(
            json.dumps({"gm_login_scene": {self.GM_ACCOUNT: scene_id}}),
            encoding="utf-8",
        )

    def write_standalone_map(self, scene_id):
        self.standalone_path.write_text(
            json.dumps(
                {
                    login_scene_override.STANDALONE_JSON_KEY: {
                        self.GM_ACCOUNT: scene_id
                    }
                }
            ),
            encoding="utf-8",
        )


class TheStandaloneMapNeverWidensTests(_ConfigCase):
    """Property 1: the map that is never spent never gets the wide rule.

    THE FAILURE THIS PREVENTS, spelled out because it is the reason the
    widening is scoped at all.  A standalone grant yields
    `STANDALONE_NOT_CONSUMED`, so `override_consumed_scene` stays None, so
    `gm_sanctioned_bypass` stays False, so `resolve_entry` is asked with
    `via_login=True`, so a sanctioned-barred scene is refused with
    `REFUSED_NOT_ALLOWED_AT_LOGIN` -- on that login and, because the map is
    deliberately not consumed, on every retry after it, until somebody with
    shell access edits a gitignored file.
    """

    def test_the_single_use_map_accepts_the_sanctioned_scene(self):
        registry = registry_with_sanctioned_row()
        self.write_gm_map(SANCTIONED)
        loaded = login_scene_override.load_login_scene_overrides(
            self.gm_map_path, scene_registry=registry
        )
        self.assertEqual({self.GM_ACCOUNT: SANCTIONED}, loaded)

    def test_the_standalone_map_refuses_the_same_scene_and_the_same_registry(self):
        registry = registry_with_sanctioned_row()
        self.write_standalone_map(SANCTIONED)
        with self.assertRaises(login_scene_override.LoginSceneRefusedError):
            login_scene_override.load_standalone_login_scene_overrides(
                self.standalone_path, scene_registry=registry
            )

    def test_the_standalone_map_still_accepts_an_ordinarily_pinned_scene(self):
        # The refusal above must be about the SANCTION, not about the
        # standalone reader having been broken.
        registry = registry_with_sanctioned_row()
        ordinary = A.stageable_scene_ids(scene_registry=registry)[0]
        self.write_standalone_map(ordinary)
        loaded = login_scene_override.load_standalone_login_scene_overrides(
            self.standalone_path, scene_registry=registry
        )
        self.assertEqual({self.GM_ACCOUNT: ordinary}, loaded)

    def test_the_reader_cannot_be_called_without_choosing_a_rule(self):
        # `single_use` is keyword-only and has no default, so a third map
        # cannot inherit whichever rule happened to be written first.
        with self.assertRaises(TypeError):
            login_scene_override._load_scene_id_map(
                self.gm_map_path, "gm_login_scene", None
            )


class TheRefusalCarriesTheRuleThatRefusedTests(_ConfigCase):
    """A refusal says which rule it came from, so the remedy is right.

    `_refusal_cause` asks "would the DISK have taken this row" to tell
    "edit the config" from "restart the server".  Asked with the narrow
    rule about a single-use refusal of a sanctioned scene it answers no for
    a reason that has nothing to do with the disk, and the operator is sent
    to grep a file that is correct.
    """

    def test_a_single_use_refusal_is_flagged(self):
        self.write_gm_map(SANCTIONED)
        with self.assertRaises(
            login_scene_override.LoginSceneRefusedError
        ) as caught:
            login_scene_override.load_login_scene_overrides(
                self.gm_map_path,
                scene_registry=world_scene_travel.load_scene_registry(),
            )
        self.assertTrue(caught.exception.single_use)
        self.assertEqual(SANCTIONED, caught.exception.scene_id)

    def test_a_standalone_refusal_is_not(self):
        self.write_standalone_map(SANCTIONED)
        with self.assertRaises(
            login_scene_override.LoginSceneRefusedError
        ) as caught:
            login_scene_override.load_standalone_login_scene_overrides(
                self.standalone_path,
                scene_registry=world_scene_travel.load_scene_registry(),
            )
        self.assertFalse(caught.exception.single_use)

    def test_the_probe_asks_with_the_flagged_rule(self):
        # The disk holds the widened answer only for a single-use refusal.
        registry = registry_with_sanctioned_row()
        original = A.SANCTIONED_BARRED_SCENES
        self.assertTrue(
            A.disk_admits_under_rule.__doc__,
            "the probe seam is documented; see why it is separate",
        )
        # Asked about a scene the disk admits under BOTH rules, both agree.
        ordinary = A.stageable_scene_ids()[0]
        self.assertTrue(A.disk_admits_under_rule(ordinary, single_use=True))
        self.assertTrue(A.disk_admits_under_rule(ordinary, single_use=False))
        # Asked about the sanctioned scene, both refuse TODAY (no lane A
        # row), and that is the honest state rather than a rigged pass.
        self.assertFalse(A.disk_admits_under_rule(SANCTIONED, single_use=True))
        self.assertFalse(A.disk_admits_under_rule(SANCTIONED, single_use=False))
        self.assertIs(original, A.SANCTIONED_BARRED_SCENES)


class lane_a_row_on_disk:
    """THE DAY LANE A'S ROW LANDS, and not one day earlier.

    `stage_login_scene` asks BOTH readings and lets a caller's snapshot only
    NARROW what may be written, never widen it -- so a stand-in registry
    passed as `scene_registry` alone cannot make a sanctioned scene
    stageable, and MEASURED here, it does not: the disk is asked first and
    refuses.  That rule is load-bearing and this file does not route around
    it; it moves the DISK instead, which is exactly the change lane A's
    merge will make.

    Patched at `world_scene_travel.load_scene_registry`, the function
    `login_scene_admission._registry_to_ask` calls by module attribute, so
    the substitution reaches the same reader the running server uses rather
    than a private copy.  Nothing about the sanction map, the admission
    rule, or the write path is mocked -- only the contents of lane A's file.
    """

    def __init__(self, registry):
        self.registry = registry
        self._patch = None

    def __enter__(self):
        from unittest import mock

        self._patch = mock.patch.object(
            world_scene_travel, "load_scene_registry", return_value=self.registry
        )
        self._patch.start()
        return self.registry

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class TheUndoBelievesTheSameRuleTests(_ConfigCase):
    """Property 3 -- chief's D5 question, answered by construction.

    THE ANSWER THIS LANE GIVES: the undo believes the rule the WRITE
    believed, and it does so because there is only one rule to believe.  The
    widening lives in the READER (`_load_scene_id_map` for the single-use
    key); `stage_login_scene` writes through `_write_entry`, which
    re-validates the whole file through that same reader, and
    `restore_login_scene` is `_write_entry` with `allow_delete`.  Consume,
    stage and undo therefore cannot disagree without someone deleting the
    shared reader -- which is a different change from forgetting to widen a
    second call site, and a much harder one to make by accident.

    The alternative chief's letter describes -- widening consume alone --
    would have left `restore_login_scene` judging by the narrow rule, so the
    put-back would refuse the file it was called to repair and the
    operator's entry would be destroyed rather than returned.
    """

    def stage(self, scene_id, registry):
        return login_scene_stage.stage_login_scene(
            self.GM_ACCOUNT,
            scene_id,
            gm_accounts_config_path=str(self.accounts_path),
            config_path=str(self.gm_map_path),
            scene_registry=registry,
        )

    def test_a_sanctioned_scene_can_be_staged_once_lane_a_lands_the_row(self):
        with lane_a_row_on_disk(registry_with_sanctioned_row()) as registry:
            result = self.stage(SANCTIONED, registry)
            self.assertTrue(result.staged, f"refused with {result.reason}")
            self.assertEqual(
                {self.GM_ACCOUNT: SANCTIONED},
                login_scene_override.load_login_scene_overrides(
                    self.gm_map_path, scene_registry=registry
                ),
            )

    def test_a_snapshot_alone_cannot_make_it_stageable(self):
        # A SNAPSHOT MAY NOT WIDEN A WRITE.  Same registry, NOT on disk:
        # the disk reading is asked first and refuses, so nothing is
        # written.  This is what makes the test above a statement about
        # lane A's merge rather than about a mock.
        result = self.stage(SANCTIONED, registry_with_sanctioned_row())
        self.assertFalse(result.staged)
        self.assertEqual(
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE, result.reason
        )
        self.assertFalse(self.gm_map_path.exists())

    def test_the_undo_puts_a_sanctioned_entry_back_rather_than_losing_it(self):
        # The D5 walk end to end: stage it, take it off (what a login's
        # consume does), then put it back (what `_put_back_consumed_override`
        # does when the probe refuses).  The put-back must SUCCEED; a False
        # here is the `gm_login_scene_override_lost_to_refusal_<n>` event and
        # a destroyed operator entry.
        with lane_a_row_on_disk(registry_with_sanctioned_row()) as registry:
            self.assertTrue(self.stage(SANCTIONED, registry).staged)
            claimed = login_scene_stage.claim_login_scene(
                self.GM_ACCOUNT,
                config_path=str(self.gm_map_path),
                scene_registry=registry,
            )
            self.assertEqual(SANCTIONED, claimed)
            restored = login_scene_stage.restore_login_scene(
                self.GM_ACCOUNT,
                claimed,
                gm_accounts_config_path=str(self.accounts_path),
                config_path=str(self.gm_map_path),
                scene_registry=registry,
            )
            self.assertTrue(
                restored,
                "the undo refused an entry the write accepted: consume and "
                "restore are on different rules again (chief\'s D5)",
            )
            self.assertEqual(
                {self.GM_ACCOUNT: SANCTIONED},
                login_scene_override.load_login_scene_overrides(
                    self.gm_map_path, scene_registry=registry
                ),
            )

    def test_an_unrelated_entry_survives_the_undo_of_a_sanctioned_one(self):
        # `_write_entry` refuses to write into a file the reader would
        # refuse, so a sanctioned entry belonging to ANOTHER account must
        # not make the whole file unreadable to the undo path.
        other = "GM_TWO"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT, other]}),
            encoding="utf-8",
        )
        with lane_a_row_on_disk(registry_with_sanctioned_row()) as registry:
            ordinary = A.stageable_scene_ids(scene_registry=registry)[0]
            self.assertTrue(self.stage(SANCTIONED, registry).staged)
            self.assertTrue(
                login_scene_stage.stage_login_scene(
                    other,
                    ordinary,
                    gm_accounts_config_path=str(self.accounts_path),
                    config_path=str(self.gm_map_path),
                    scene_registry=registry,
                ).staged
            )
            self.assertTrue(
                login_scene_stage.restore_login_scene(
                    other,
                    None,
                    gm_accounts_config_path=str(self.accounts_path),
                    config_path=str(self.gm_map_path),
                    scene_registry=registry,
                )
            )
            self.assertEqual(
                {self.GM_ACCOUNT: SANCTIONED},
                login_scene_override.load_login_scene_overrides(
                    self.gm_map_path, scene_registry=registry
                ),
            )

    def test_a_snapshot_that_lacks_the_row_still_narrows_the_write(self):
        # A SNAPSHOT MAY NOT WIDEN A WRITE, and it may still narrow one.
        # The disk has no row for the sanctioned scene today, so this is
        # also the live state: staging it against the real registry refuses.
        self.assertFalse(
            self.stage(SANCTIONED, world_scene_travel.load_scene_registry()).staged
        )
        self.assertEqual({}, json.loads(self.gm_map_path.read_text())
                         .get("gm_login_scene", {}) if self.gm_map_path.exists()
                         else {})

    def test_the_refusal_names_the_sanction_rather_than_a_bare_no_entry(self):
        result = self.stage(SANCTIONED, world_scene_travel.load_scene_registry())
        self.assertEqual(
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE, result.reason
        )


if __name__ == "__main__":
    unittest.main()
