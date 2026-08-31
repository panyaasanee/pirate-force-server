"""A SANCTIONED destination is still a REFUSED one until its route exists.

Round 6vhfgh.  `notes_to_chief/20260829_1603_CHIEF-DECISION-var2-test-path-
scene126-registry-row-plus-gm-warp.md` is addressed to lane A and to this
lane and asks for two halves: lane A pins a registry row for scene 126
(`login_entry_allowed: false`), and this lane adds 126 "to the set /warp
accepts".

Measured on main in the round that read the letter, the two halves as
written cannot both be true.  `/warp <scene_id>` across scenes does not put
anything on the wire: it stages the account's NEXT LOGIN scene, and
`runtime.py` resolves that through `world_scene_entry.resolve_entry` with
`via_login` defaulted True at both of its call sites (5635, 5706), where
`login_entry_allowed: false` is refused.  So an admitted 126 would write a
config entry the very next login throws away -- one relog spent, nothing
reached, a console line the tester at the client cannot see.

This file pins what this lane shipped instead, and the first class is the
load-bearing one: THE SANCTION GRANTS NOTHING.  The stageable set is still
exactly what lane A's pins say.  What the sanction buys is a refusal that
names WHICH half of the route is missing, measured against lane A's registry
on every call, so it changes its own answer the hour lane A's row lands with
no edit in this lane.

NONCLAIM: nothing here is client-observable, and nothing here says a tester
can reach scene 126 -- the opposite.  It is one layer: wire/DB, headless.
No GM capability is granted by any test in this file.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    chat_command_action,
    login_scene_admission,
    login_scene_stage,
)
from pirateforce_foundation.model import Position  # noqa: E402

# Pinned as a literal for the reason every other file in this lane pins it:
# this file has to go RED when the set moves, not agree with whatever the
# registry says on the day it runs.
# Scene 14 joined it in LANE-A round vvy6q7 (COO-DECISION 20260829_2342
# opened Hell Volcano Island at login).  It arrived through the REGISTRY,
# which is this file's whole point: the sanctioned scene 126 still grants
# nothing, and 14 is here because a pinned row says open, not because a
# letter said so.  Scene 4 joined it round bq4mst the same way (COO-DECISION
# 20260830_1441, this lane's own census composer judged ready).  Scene 10
# joined it round 3t75jw, second door in the same queue.  Scene 5 joined it
# round l03cgh, third door, built+wired+opened in one round.  Scene 6
# joined it round fx0007, fourth door, same shape.  Scene 8 joined it round
# p4wire, fifth door, same shape.  Scene 3 joined it round p7wm17, sixth
# door, same shape.  Scene 7 joined it round 78zayw, seventh door, same
# shape.  Scene 9 joined it round ir0lpw, eighth door, same shape.  Scene 11
# joined it round 68mm02, ninth door, same shape (elevated-risk row,
# the_two_interiors, shared only with scene 10).  Scene 130 joined it this
# round (yfbqmg), TENTH AND LAST door, same shape, NOT elevated-risk --
# every one of the original ten doors is now open.
ADMISSIBLE_TODAY = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130, 278, 997)
# The one scene a chief letter sanctions today.
SANCTIONED = 126
# Pinned, named, and barred at login -- the shape scene 126 will have once
# lane A lands its row, and the shape the sanction has to survive.
BARRED_AT_LOGIN = 17


def _registry_with_sanctioned_row(*, login_entry_allowed: bool):
    """Lane A's registry with the scene-126 row landed, and nothing else.

    Built by copying a REAL row (scene 17: pinned, spawned, barred) rather
    than by hand: a hand-built stand-in satisfies whatever fields the test
    author remembered, and the predicate reads three.
    """
    registry = world_scene_travel.load_scene_registry()
    source = registry[BARRED_AT_LOGIN]
    landed = dataclasses.replace(
        source, n_id=SANCTIONED, login_entry_allowed=login_entry_allowed
    )
    # `SceneRegistry.__getitem__` is a linear scan returning the first row
    # whose n_id matches.  Lane A's real scene-126 row is on main now
    # (round R249, `pirate-force-server#332`), so `registry.destinations`
    # already carries one -- appending this stand-in after it would leave
    # `registry[SANCTIONED]` resolving to the real row instead of the
    # `login_entry_allowed` this helper's caller asked for. Drop any
    # existing row with the same id first.
    kept = tuple(d for d in registry.destinations if d.n_id != SANCTIONED)
    return dataclasses.replace(registry, destinations=kept + (landed,))


class TheSanctionSetGrantsNothingTests(unittest.TestCase):
    """The class this whole file exists for.  If it goes green wrongly, a
    tester is being sent at a destination their next login will refuse.

    SCOPE, said out loud since round ``znb56z`` because the class name alone
    now over-promises: this pins that the sanction grants nothing UNDER THE
    PLAIN RULE -- ``login_entry_is_pinned`` and ``stageable_scene_ids``.
    That rule is what the standalone map is judged by and what the login
    path's own guard asks, so every assertion here is still exactly as
    load-bearing as it was.  What changed is that a SECOND rule now exists
    for the map that is spent on use
    (``login_scene_admission.single_use_entry_is_admissible``, after
    ``CORE-REQUEST-GM-038`` landed), and under that one a sanctioned scene
    IS admitted once lane A's row exists.  It is pinned in
    ``tests/test_gm_login_scene_sanctioned_admission.py``; this file and that
    one together are the statement that the widening reached one map and not
    the other.  A future reader who deletes this class because "the sanction
    grants something now" would be deleting the guard on the map that must
    never widen.
    """

    def test_the_stageable_set_did_not_grow_by_the_sanctioned_scene(self):
        self.assertEqual(
            login_scene_admission.stageable_scene_ids(), ADMISSIBLE_TODAY
        )
        self.assertNotIn(SANCTIONED, login_scene_admission.stageable_scene_ids())

    def test_the_predicate_still_refuses_the_sanctioned_scene(self):
        self.assertFalse(login_scene_admission.login_entry_is_pinned(SANCTIONED))

    def test_it_still_refuses_after_lane_a_lands_the_barred_row(self):
        # The important one: the sanction must NOT turn into permission the
        # moment half one arrives.
        #
        # ~~Only chief's half can do that.~~ Chief's half HAS landed (#281),
        # and this assertion is still green and still right, which is the
        # point worth keeping: what chief's half unlocked is the SINGLE-USE
        # rule, not this one.  `login_entry_is_pinned` is the standalone
        # map's rule and the login guard's own question, and no half of any
        # request widens it.  If this ever goes red, the widening has
        # escaped the map it was scoped to.
        registry = _registry_with_sanctioned_row(login_entry_allowed=False)
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(
                SANCTIONED, scene_registry=registry
            )
        )
        self.assertNotIn(
            SANCTIONED,
            login_scene_admission.stageable_scene_ids(scene_registry=registry),
        )

    def test_the_login_path_agrees_with_the_refusal(self):
        # Not this lane's predicate quoting itself: the real login resolver,
        # asked the way runtime.py asks it, on the landed-row registry.
        registry = _registry_with_sanctioned_row(login_entry_allowed=False)
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_scene_entry.resolve_entry(
                Position(SANCTIONED, 0, 0.0, 0.0, 0.0, 0),
                registry=registry,
                emit=lambda _line: None,
            )
        self.assertEqual(
            caught.exception.reason,
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
        )

    def test_every_sanctioned_scene_is_one_the_predicate_refuses_today(self):
        # A sanction for a scene that is already admissible is dead weight
        # that reads like a grant.  If lane A ever opens one of these doors,
        # this test says so instead of leaving the entry to rot.
        for scene_id in login_scene_admission.SANCTIONED_BARRED_SCENES:
            with self.subTest(scene=scene_id):
                self.assertNotIn(
                    scene_id, login_scene_admission.stageable_scene_ids()
                )

    def test_the_map_refuses_an_item_assignment(self):
        # A TYPO GUARD, and pf-adversary (D8) was right that the first
        # version of this test sold it as more: it stops an accidental
        # `SANCTIONED_BARRED_SCENES[999] = ...` from a module that imported
        # this one, and nothing else.  It does not stop a rebind of the
        # module attribute, and there is no client-reachable path to
        # either.  The map selects a refusal STRING; it is not a
        # capability, and this test does not claim it is one.
        with self.assertRaises(TypeError):
            login_scene_admission.SANCTIONED_BARRED_SCENES[999] = "no"


    def test_blocker_none_means_exactly_what_the_predicate_admits(self):
        # The two functions check the same four conditions in a DIFFERENT
        # order (the blocker orders by remedy, `_target_is_admissible` by
        # cost), so the equivalence is asserted rather than assumed.  If
        # they ever disagree, the console line starts saying "nothing is
        # blocking" about a scene the stage still refuses.
        registries = {
            "shipped": None,
            "landed_barred": _registry_with_sanctioned_row(
                login_entry_allowed=False
            ),
            "landed_open": _registry_with_sanctioned_row(
                login_entry_allowed=True
            ),
        }
        for label, registry in registries.items():
            with self.subTest(registry=label):
                blocker = login_scene_admission.sanctioned_barred_blocker(
                    SANCTIONED, scene_registry=registry
                )
                admitted = login_scene_admission.login_entry_is_pinned(
                    SANCTIONED, scene_registry=registry
                )
                self.assertEqual(
                    blocker == login_scene_admission.BLOCKER_NONE, admitted
                )


class TheBlockerNamesTheMissingHalfTests(unittest.TestCase):
    def test_an_unsanctioned_scene_is_answered_as_such(self):
        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(BARRED_AT_LOGIN),
            login_scene_admission.BLOCKER_NOT_SANCTIONED,
        )

    def test_today_the_missing_half_is_lane_as_registry_row(self):
        # Measured against the shipped registry, not asserted from a doc.
        # This test FLIPS to the branch below the day lane A merges, and the
        # flip is the point: the console line changes with no edit here.
        landed = SANCTIONED in world_scene_travel.load_scene_registry().ids
        expected = (
            login_scene_admission.BLOCKER_LOGIN_PATH_BARS_IT
            if landed
            else login_scene_admission.BLOCKER_NO_REGISTRY_ROW
        )
        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(SANCTIONED),
            expected,
        )

    def test_a_landed_barred_row_reports_the_login_path_as_the_blocker(self):
        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(
                SANCTIONED,
                scene_registry=_registry_with_sanctioned_row(
                    login_entry_allowed=False
                ),
            ),
            login_scene_admission.BLOCKER_LOGIN_PATH_BARS_IT,
        )

    def test_a_row_opened_at_login_reports_nothing_blocking(self):
        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(
                SANCTIONED,
                scene_registry=_registry_with_sanctioned_row(
                    login_entry_allowed=True
                ),
            ),
            login_scene_admission.BLOCKER_NONE,
        )

    def test_a_spawnless_row_reports_the_spawn_not_the_login_flag(self):
        registry = _registry_with_sanctioned_row(login_entry_allowed=False)
        spawnless = dataclasses.replace(
            registry,
            destinations=tuple(
                dataclasses.replace(destination, spawn=None)
                if destination.n_id == SANCTIONED
                else destination
                for destination in registry.destinations
            ),
        )
        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(
                SANCTIONED, scene_registry=spawnless
            ),
            login_scene_admission.BLOCKER_NO_PINNED_SPAWN,
        )

    def test_a_stand_in_that_answers_about_another_scene_is_caught(self):
        class _Slipped:
            destinations = ()

            def __getitem__(self, _n_id):
                return world_scene_travel.load_scene_registry()[BARRED_AT_LOGIN]

        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(
                SANCTIONED, scene_registry=_Slipped()
            ),
            login_scene_admission.BLOCKER_ROW_IS_NOT_THE_ROW_ASKED_FOR,
        )

    def test_a_foreign_object_does_not_raise_into_a_console_line(self):
        class _NotARegistry:
            def __getitem__(self, _n_id):
                raise RuntimeError("not a registry")

        self.assertEqual(
            login_scene_admission.sanctioned_barred_blocker(
                SANCTIONED, scene_registry=_NotARegistry()
            ),
            login_scene_admission.BLOCKER_REGISTRY_UNREADABLE,
        )

    def test_this_modules_own_load_raises_where_a_person_can_see_it(self):
        # pf-adversary D4.  The whole module argues that the OWN-LOAD path
        # must raise (a bent registry is a thing to fix, not to swallow)
        # and that only a caller-supplied object gets the wide catch.  The
        # new function's copy of that rule was asserted nowhere, and
        # swallowing it survived the suite.
        class _NotARegistry:
            def __getitem__(self, _n_id):
                raise RuntimeError("bent row")

        with mock.patch.object(
            world_scene_travel, "load_scene_registry", return_value=_NotARegistry()
        ):
            with self.assertRaises(RuntimeError):
                login_scene_admission.sanctioned_barred_blocker(SANCTIONED)

    def test_a_bent_row_on_the_own_load_path_raises_too(self):
        # The second guarded block, not the first: the lookup succeeds and
        # the FIELD read is what explodes.
        class _BentRow:
            n_id = SANCTIONED

            @property
            def spawn(self):
                raise RuntimeError("bent field")

        class _Registry:
            destinations = ()

            def __getitem__(self, _n_id):
                return _BentRow()

        with mock.patch.object(
            world_scene_travel, "load_scene_registry", return_value=_Registry()
        ):
            with self.assertRaises(RuntimeError):
                login_scene_admission.sanctioned_barred_blocker(SANCTIONED)

    def test_an_unreadable_registry_is_not_reported_as_a_missing_row(self):
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            side_effect=OSError("no file"),
        ):
            self.assertEqual(
                login_scene_admission.sanctioned_barred_blocker(SANCTIONED),
                login_scene_admission.BLOCKER_REGISTRY_UNREADABLE,
            )

    def test_a_bool_does_not_ask_about_scene_one(self):
        # pf-adversary D3: the first version of this test could not fail.
        # `True == 1`, and scene 1 is not sanctioned, so `isinstance` and
        # `type(...) is` answered identically for every input it used.  The
        # guard is only reachable while scene 1 IS in the map, so the map
        # is what the test has to move.
        with mock.patch.object(
            login_scene_admission,
            "SANCTIONED_BARRED_SCENES",
            MappingProxyType({1: "a letter that does not exist"}),
        ):
            self.assertTrue(
                login_scene_admission.is_sanctioned_barred_scene(1)
            )
            self.assertFalse(
                login_scene_admission.is_sanctioned_barred_scene(True)
            )
            self.assertEqual(
                login_scene_admission.sanctioned_barred_blocker(True),
                login_scene_admission.BLOCKER_NOT_SANCTIONED,
            )

    def test_the_provenance_is_the_letter_and_only_for_a_sanctioned_scene(self):
        self.assertIsNone(
            login_scene_admission.sanctioned_barred_provenance(BARRED_AT_LOGIN)
        )
        provenance = login_scene_admission.sanctioned_barred_provenance(
            SANCTIONED
        )
        self.assertIn("CHIEF-DECISION", provenance)
        # Printed to a cp874 console beside the refusal.
        self.assertTrue(provenance.isascii())


class TheStagePathSaysWhichRefusalItIsTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        root = Path(self._dir.name)
        self.accounts_path = root / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["GM_ONE"]}), encoding="utf-8"
        )
        self.config_path = root / "gm_login_scene.json"

    def _stage(self, scene_id: int):
        return login_scene_stage.stage_login_scene(
            "GM_ONE",
            scene_id,
            gm_accounts_config_path=self.accounts_path,
            config_path=self.config_path,
        )

    def _disk_before_lane_a_merge(self):
        # Round R249 (chief, gate-red repair of `pirate-force-server#332`)
        # landed lane A's real scene-126 row on the real disk, so this
        # class's "not yet reachable" scenario has to build the pre-merge
        # disk explicitly now instead of reading it off the unmocked disk.
        registry = world_scene_travel.load_scene_registry()
        return dataclasses.replace(
            registry,
            destinations=tuple(
                d for d in registry.destinations if d.n_id != SANCTIONED
            ),
        )

    def test_the_sanctioned_scene_refuses_with_its_own_reason(self):
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            return_value=self._disk_before_lane_a_merge(),
        ):
            result = self._stage(SANCTIONED)
        self.assertFalse(result.staged)
        self.assertEqual(
            result.reason,
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
        )

    def test_an_ordinary_barred_scene_keeps_the_ordinary_reason(self):
        result = self._stage(BARRED_AT_LOGIN)
        self.assertFalse(result.staged)
        self.assertEqual(
            result.reason, login_scene_stage.REASON_NO_LOGIN_ENTRY
        )

    def test_the_refusal_writes_nothing_at_all(self):
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            return_value=self._disk_before_lane_a_merge(),
        ):
            self._stage(SANCTIONED)
        self.assertFalse(self.config_path.exists())

    def test_the_new_reason_is_classified_as_destination_shaped(self):
        # Another destination really would work, so a way out is owed.
        self.assertIn(
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            login_scene_stage.DESTINATION_SHAPED_REASONS,
        )
        self.assertNotIn(
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            login_scene_stage.NOT_DESTINATION_SHAPED_REASONS,
        )


class TheSanctionIsAskedOnlyAfterThePinRefusesTests(unittest.TestCase):
    """pf-adversary D2: the ORDER is the load-bearing property and it had
    no test.  Moving the sanction check above `login_entry_is_pinned` left
    the whole suite green -- and turns the map into a permanent BAN the day
    a sanctioned scene becomes admissible, which is the exact opposite of
    what it is for."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        root = Path(self._dir.name)
        self.accounts_path = root / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["GM_ONE"]}), encoding="utf-8"
        )
        self.config_path = root / "gm_login_scene.json"

    def test_a_sanctioned_scene_the_registry_admits_still_stages(self):
        # Scene 2 is admissible today.  Sanctioning it must change NOTHING:
        # the pin answers first, the write happens, and the sanction is
        # never consulted.  Under the inverted order this returns
        # `scene_sanctioned_but_route_incomplete` and the scene is barred
        # by the very map that was supposed to be a permit.
        admitted = ADMISSIBLE_TODAY[1]
        with mock.patch.object(
            login_scene_admission,
            "SANCTIONED_BARRED_SCENES",
            MappingProxyType({admitted: "a letter that does not exist"}),
        ):
            result = login_scene_stage.stage_login_scene(
                "GM_ONE",
                admitted,
                gm_accounts_config_path=self.accounts_path,
                config_path=self.config_path,
            )
        self.assertTrue(result.staged, result.reason)
        self.assertEqual(result.reason, login_scene_stage.REASON_OK)

    def test_an_unknown_scene_never_reaches_the_sanction_either(self):
        # The name-catalog check is upstream of both.  A sanction for an
        # id the client has no name for may not promote it into a
        # destination-shaped refusal that offers a way out.
        unnamed = 31337
        with mock.patch.object(
            login_scene_admission,
            "SANCTIONED_BARRED_SCENES",
            MappingProxyType({unnamed: "a letter that does not exist"}),
        ):
            result = login_scene_stage.stage_login_scene(
                "GM_ONE",
                unnamed,
                gm_accounts_config_path=self.accounts_path,
                config_path=self.config_path,
            )
        self.assertEqual(
            result.reason, login_scene_stage.REASON_UNKNOWN_SCENE
        )


class TheConsoleLineCannotBreakTheRefusalTests(unittest.TestCase):
    """pf-adversary D1 and D5: two claims the comments made about this one
    printed line, neither of which any test could see."""

    def _line(self, scene_id, reason, **kwargs):
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            chat_command_action._print_warp_way_out(
                object(), "GM_ONE", scene_id, reason, **kwargs
            )
        return stream.getvalue()

    def test_a_blocker_that_raises_does_not_escape_the_printer(self):
        # D1.  The blocker is reached as a MODULE ATTRIBUTE, so the older
        # pin (which patches the imported `stageable_scene_ids` name)
        # cannot see it.  `_print_warp_way_out` is called UNguarded from
        # `_stage_action`, so an escape here turns a decided refusal into
        # an exception on the listener thread.
        with mock.patch.object(
            login_scene_admission,
            "sanctioned_barred_blocker",
            side_effect=RuntimeError("bent registry"),
        ):
            self._line(
                SANCTIONED,
                login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            )

    def test_a_provenance_that_raises_does_not_escape_either(self):
        with mock.patch.object(
            login_scene_admission,
            "sanctioned_barred_provenance",
            side_effect=RuntimeError("bent map"),
        ):
            self._line(
                SANCTIONED,
                login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            )

    def test_the_blocker_is_the_disk_reading_not_the_callers_snapshot(self):
        # D5.  The comment says the blocker must answer for the reading
        # that PRODUCED the refusal (the disk one), and no test made the
        # two readings differ, so the claim was decoration.  Here the
        # snapshot would answer `none` and the disk answers `row missing`.
        line = self._line(
            SANCTIONED,
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            scene_registry=_registry_with_sanctioned_row(
                login_entry_allowed=True
            ),
        )
        self.assertIn(
            f"blocker={login_scene_admission.sanctioned_barred_blocker(SANCTIONED)}",
            line,
        )
        self.assertNotIn(
            f"blocker={login_scene_admission.BLOCKER_NONE}", line
        )


class TheConsoleLineCarriesTheBlockerTests(unittest.TestCase):
    def _way_out(self, scene_id: int, reason: str) -> str:
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            chat_command_action._print_warp_way_out(
                object(), "GM_ONE", scene_id, reason
            )
        return stream.getvalue()

    def test_the_sanctioned_refusal_names_the_blocker_and_the_letter(self):
        line = self._way_out(
            SANCTIONED, login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE
        )
        self.assertIn("blocker=", line)
        self.assertIn("CHIEF-DECISION", line)
        # The way out is still there: this reason is destination-shaped.
        self.assertIn("stageable=", line)

    def test_an_ordinary_refusal_gains_no_blocker(self):
        line = self._way_out(
            BARRED_AT_LOGIN, login_scene_stage.REASON_NO_LOGIN_ENTRY
        )
        self.assertIn("stageable=", line)
        self.assertNotIn("blocker=", line)

    def test_a_console_that_cannot_take_the_line_is_not_a_refusal_change(self):
        # The refusal is already decided by the time this prints; a broken
        # console may not turn it into an exception on the listener thread.
        class _Exploding(io.StringIO):
            def write(self, _text):
                raise ValueError("closed")

        with mock.patch.object(chat_command_action.sys, "stderr", _Exploding()):
            chat_command_action._print_warp_way_out(
                object(),
                "GM_ONE",
                SANCTIONED,
                login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
            )

    def test_a_reason_without_a_sanction_never_prints_the_word_none(self):
        # Reachable only if the REASON and the sanction map disagree, which
        # is a bug in this lane.  The line must still read as a line: the
        # pair `blocker=not_sanctioned sanction='unknown'` says so, where
        # `sanction='None'` would look like the letter was called None.
        line = self._way_out(
            BARRED_AT_LOGIN,
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE,
        )
        self.assertIn(
            f"blocker={login_scene_admission.BLOCKER_NOT_SANCTIONED}", line
        )
        self.assertIn("sanction='unknown'", line)
        self.assertNotIn("None", line)


if __name__ == "__main__":
    unittest.main()
