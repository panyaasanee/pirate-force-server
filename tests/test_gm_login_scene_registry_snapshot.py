"""WHICH READING of lane A's registry a login-scene config is judged against.

Round 7hfrt0.  `notes_to_chief/20260829_1221_CHIEF-REPLY-LANE-GM-034-
answered-differently-and-035-queued.md` item 4 asked this lane to land the
`scene_registry=` parameter first, so chief's call site can pass
`runtime.py`'s boot snapshot into it.  This file is what "landed" means:
every function in the chain honours it, none of them reads the file when it
is supplied, and a caller-supplied object that is not a registry refuses
rather than raises.

THE TWO DIRECTIONS ARE NOT THE SAME PROBLEM, and only one of them is
already closed:

* The DISK WIDER than the snapshot (an entry the file approves and the
  running process would refuse) is closed at chief's own call site, by the
  `resolve_entry` probe they describe in item 3 of that letter.  Nothing
  here claims to close it again.
* The DISK NARROWER than the snapshot -- lane A's registry file edited to
  bar or drop a destination after boot -- is reachable by no gate at the
  call site, because by the time the call site sees anything the whole-file
  load has already raised and `consume_login_scene_override` has already
  answered `CONSUME_FAILED`.  ONE bad-for-disk entry turns off EVERY
  account's override, including accounts naming scenes the running process
  would place them in perfectly well.  That is what `SnapshotIsNarrower`
  and `SnapshotIsWider` below measure, end to end through the consumer.

NOT WIRED, and this file may not be read as evidence that it is: no caller
in this repository passes `scene_registry` today.  `runtime.py` is chief's
file and this lane does not edit it; `CORE-REQUEST-GM-036` asks for the two
call sites.  Every test here supplies the snapshot by hand, which is
exactly what a test can prove and no more -- the module-layer fact, not a
statement about any running server.

NONCLAIM: no evidence here is client-observable.  Nothing in this file was
measured against a game client, and no scene named in it has been shown to
be reachable by a person.  It is one layer -- wire/DB, headless.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    chat_command,
    chat_command_action,
    dispatch as gm_dispatch,
    login_scene_admission,
    login_scene_consume,
    login_scene_override,
    login_scene_stage,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Pinned as literals for the same reason `test_gm_login_scene_admission.py`
# pins its own: this file has to fail when the registry moves, not agree
# with whatever it happens to say today.
# Scene 14 joined it in LANE-A round vvy6q7 (COO-DECISION 20260829_2342
# opened Hell Volcano Island at login); see test_gm_login_scene_stage.py for
# the gate that had to arrive with it.  Scene 4 joined it round bq4mst
# (COO-DECISION 20260830_1441).  Scene 10 joined it round 3t75jw, second
# door in the same queue.  Scene 5 joined it round l03cgh, third door,
# built+wired+opened in one round.  Scene 6 joined it round fx0007, fourth
# door, same shape.  Scene 8 joined it round p4wire, fifth door, same
# shape.  Scene 3 joined it round p7wm17, sixth door, same shape.  Scene 7
# joined it round 78zayw, seventh door, same shape.  Scene 9 joined it round
# ir0lpw, eighth door, same shape.  Scene 11 joined it round 68mm02, ninth
# door, same shape (elevated-risk row, the_two_interiors, shared only with
# scene 10).  Scene 130 joined it this round (yfbqmg), TENTH AND LAST door,
# same shape, NOT elevated-risk -- and is therefore no longer a usable
# BARRED_ON_DISK example (every one of the original ten doors is now open),
# so that constant moves to scene 17: PERMANENT rather than another door
# this lane will eventually open.  126 (Atlantis) was considered and
# refused: this file's own fixtures drive ``login_scene_stage.stage``, the
# GM-gated path, whose OWN admissibility is the WIDENED single-use set
# (``login_scene_admission.SINGLE_USE_ADMISSIBLE_TODAY`` includes 126 by
# name, `CORE-REQUEST-GM-038`) -- 126 is NOT barred on this path, measured
# directly (four tests went red asserting it was refused when it was
# actually staged).  17 IS barred under every reading this file or its
# sibling `test_gm_login_scene_admission.py`/`test_gm_login_scene_
# sanctioned_barred.py` drives.  ``test_no_snapshot_can_make_a_written_
# file_unreadable_by_default`` below already iterates the literal 17
# alongside ``BARRED_ON_DISK`` in the same tuple, so this collapses two of
# its three cases into one scene id -- harmless (both still run, same
# assertions, same coverage of the same scene) rather than a distinct
# example, named here so a reader does not have to rediscover it.
ADMISSIBLE_ON_DISK_TODAY = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130, 278, 997)
# Named in the client's scene table ("a ship at sea") and pinned
# `login_entry_allowed: false` under EVERY admissibility reading this file
# drives (plain and GM single-use both refuse it), so the disk reading
# refuses it.
BARRED_ON_DISK = 17
# Admissible on disk today, so a snapshot that drops it is NARROWER.
ADMISSIBLE_ON_DISK = 2


def _registry_with_scene_allowed(scene_id: int):
    """The real registry, with one destination's login flag flipped ON.

    A hand-built stand-in would prove nothing about the real rows -- the
    predicate reads three fields and a fake could satisfy all three while
    the shipped file satisfies none.  So this is lane A's own loaded
    registry with exactly ONE boolean changed, which is precisely the edit
    an operator makes to `world_scene_registry_001.json` between two boots.
    """
    registry = world_scene_travel.load_scene_registry()
    return dataclasses.replace(
        registry,
        destinations=tuple(
            dataclasses.replace(destination, login_entry_allowed=True)
            if destination.n_id == scene_id
            else destination
            for destination in registry.destinations
        ),
    )


def _registry_without_scene(scene_id: int):
    """The real registry with one destination REMOVED -- the narrow case."""
    registry = world_scene_travel.load_scene_registry()
    return dataclasses.replace(
        registry,
        destinations=tuple(
            destination
            for destination in registry.destinations
            if destination.n_id != scene_id
        ),
    )


class _ExplodingLoader:
    """Asserts the file is not read at all when a snapshot is supplied.

    A test that only compared ANSWERS could not tell "the snapshot was
    used" from "the file happened to agree", and the file agrees about most
    scenes.  Patching the loader to raise makes the distinction structural:
    if any call below still reaches disk, it fails here rather than
    somewhere downstream that swallows it into a False.
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError(
            "load_scene_registry was called even though a scene_registry "
            "was supplied -- the caller's reading was not honoured"
        )


class TheSuppliedRegistryIsTheOneAskedTests(unittest.TestCase):
    def test_a_supplied_snapshot_replaces_the_file_read_entirely(self):
        exploding = _ExplodingLoader()
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        with mock.patch.object(
            login_scene_admission.world_scene_travel,
            "load_scene_registry",
            exploding,
        ):
            self.assertTrue(
                login_scene_admission.login_entry_is_pinned(
                    BARRED_ON_DISK, scene_registry=snapshot
                )
            )
            self.assertIn(
                BARRED_ON_DISK,
                login_scene_admission.stageable_scene_ids(
                    scene_registry=snapshot
                ),
            )
        self.assertEqual(exploding.calls, 0)

    def test_without_a_snapshot_the_file_still_decides(self):
        # The default path is unchanged, and this is the test that says so:
        # the parameter must not have moved the answer for any caller that
        # does not pass it, which is every caller in the repository today.
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(BARRED_ON_DISK)
        )
        self.assertEqual(
            ADMISSIBLE_ON_DISK_TODAY,
            login_scene_admission.stageable_scene_ids(),
        )

    def test_a_narrower_snapshot_refuses_what_the_file_admits(self):
        snapshot = _registry_without_scene(ADMISSIBLE_ON_DISK)
        self.assertTrue(
            login_scene_admission.login_entry_is_pinned(ADMISSIBLE_ON_DISK)
        )
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(
                ADMISSIBLE_ON_DISK, scene_registry=snapshot
            )
        )
        self.assertNotIn(
            ADMISSIBLE_ON_DISK,
            login_scene_admission.stageable_scene_ids(scene_registry=snapshot),
        )

    def test_the_way_out_is_what_a_stage_would_actually_accept(self):
        # THE FIRST VERSION OF THIS TEST WAS A TAUTOLOGY (pf-adversary,
        # round 7hfrt0, D7): it asked `stageable_scene_ids` for a list and
        # then asked `login_entry_is_pinned` about each id, which is the
        # same predicate on the same object -- it could not detect a way out
        # naming an inadmissible scene, the one property it was named for.
        #
        # Graded against the WRITER instead, which is what a tester does
        # with the list: every id printed as a way out has to be one a
        # `/warp` under that same snapshot really accepts, and every id
        # NOT printed has to be one it really refuses.
        snapshot = _registry_without_scene(ADMISSIBLE_ON_DISK)
        way_out = set(
            login_scene_admission.stageable_scene_ids(scene_registry=snapshot)
        )
        self.assertTrue(way_out, "a way out that names nothing is no test")
        account = "gm_way_out"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accounts = root / "gm_accounts.json"
            accounts.write_text(
                json.dumps({"gm_accounts": [account]}), encoding="utf-8"
            )
            for scene_id in sorted(way_out | set(ADMISSIBLE_ON_DISK_TODAY)):
                with self.subTest(scene_id=scene_id):
                    config = root / f"scene_{scene_id}.json"
                    result = login_scene_stage.stage_login_scene(
                        account,
                        scene_id,
                        gm_accounts_config_path=accounts,
                        config_path=config,
                        scene_registry=snapshot,
                    )
                    self.assertEqual(
                        scene_id in way_out,
                        result.staged,
                        f"the way out and the writer disagree about "
                        f"{scene_id}",
                    )


class AWrongObjectRefusesAndDoesNotRaiseTests(unittest.TestCase):
    """A wiring fault costs the lane's convenience, never a login.

    `runtime.py` swallows `TypeError` from this lane's call (chief measured
    it: `CHIEF-REPLY` 2026-08-29T12:21+07:00 item 2), so an exception
    escaping into that call site does not fail loudly -- it becomes
    `login_scene_override = None` and an event nobody reads.  Refusing is
    the only outcome that is both safe AND visible in the same terms as
    every other refusal.
    """

    # THE FIRST VERSION OF THIS TUPLE WAS CHOSEN TO PASS, not to probe --
    # every member happened to raise on attribute access, so it could not
    # reach the two shapes that actually broke the guarantee
    # (pf-adversary, round 7hfrt0, D1 and D7).  Both are here now:
    #   * `load_scene_registry().destinations` -- the tuple slip.  It is
    #     SUBSCRIPTABLE, so nothing raises; `registry[14]` returns the row
    #     at INDEX 14 and scene 14 was admitted on scene 278's evidence.
    #   * a `MagicMock` -- answers every attribute truthily, so scenes 3,
    #     17 and 999999 were all admitted.
    WRONG_OBJECTS = (
        object(),
        "a registry",
        42,
        [],
        {},
        {3: "not a destination"},
        mock.MagicMock(),
        world_scene_travel.load_scene_registry().destinations,
        list(world_scene_travel.load_scene_registry().destinations),
    )

    def test_a_non_registry_refuses_every_scene(self):
        for wrong in self.WRONG_OBJECTS:
            with self.subTest(wrong=type(wrong).__name__):
                self.assertFalse(
                    login_scene_admission.login_entry_is_pinned(
                        1, scene_registry=wrong
                    )
                )

    def test_a_non_registry_offers_no_way_out(self):
        for wrong in self.WRONG_OBJECTS:
            with self.subTest(wrong=type(wrong).__name__):
                self.assertEqual(
                    (),
                    login_scene_admission.stageable_scene_ids(
                        scene_registry=wrong
                    ),
                )

    def test_a_wrong_object_never_falls_back_to_the_file(self):
        # THE DIRECTION THAT MATTERS.  Falling back to disk on a bad
        # argument would answer the wider of the two questions -- the exact
        # direction this parameter exists to stop -- and would do it
        # silently, because the caller asked for a specific reading and got
        # another one that mostly agrees.
        exploding = _ExplodingLoader()
        with mock.patch.object(
            login_scene_admission.world_scene_travel,
            "load_scene_registry",
            exploding,
        ):
            self.assertFalse(
                login_scene_admission.login_entry_is_pinned(
                    1, scene_registry=object()
                )
            )
            self.assertEqual(
                (),
                login_scene_admission.stageable_scene_ids(
                    scene_registry=object()
                ),
            )
        self.assertEqual(exploding.calls, 0)

    def test_a_registry_whose_rows_raise_refuses_rather_than_escapes(self):
        class Hostile:
            @property
            def destinations(self):
                raise RuntimeError("no rows for you")

            def __getitem__(self, _key):
                raise RuntimeError("no rows for you")

        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(
                1, scene_registry=Hostile()
            )
        )
        self.assertEqual(
            (), login_scene_admission.stageable_scene_ids(
                scene_registry=Hostile()
            )
        )


class TheFilePathKeepsItsOldLoudnessTests(unittest.TestCase):
    """A bent row on the DEFAULT path still raises; it does not go quiet.

    THE REGRESSION THIS PINS (pf-adversary, round 7hfrt0, D3).  The guards
    that make a caller-supplied object refuse instead of raise were first
    written wide enough to cover this module's OWN load as well.  With
    `scene_registry=None` a genuinely bent lane-A row then stopped raising
    and became `False` / `()` -- "no scene is stageable" -- which
    `consume_login_scene_override` folds into `CONSUME_FAILED` and
    `runtime.py:5352` folds again.  A lane that quietly stops working
    instead of a fault somebody has to look at.

    So the file path keeps EXACTLY the catch it had before the parameter
    existed, and `trusted` is the flag that says so.
    """

    class _BentRow:
        # NOT scene 1: home short-circuits before `spawn` is read, so a
        # bent home row would prove nothing about the guard being tested.
        n_id = ADMISSIBLE_ON_DISK
        login_entry_allowed = True
        # No `spawn` attribute at all -- what a half-migrated lane A row
        # would look like to this module.

    def _bent_registry(self):
        registry = world_scene_travel.load_scene_registry()
        return dataclasses.replace(
            registry, destinations=(self._BentRow(),) + registry.destinations
        )

    def test_the_file_path_raises_on_a_bent_row(self):
        bent = self._bent_registry()
        with mock.patch.object(
            login_scene_admission.world_scene_travel,
            "load_scene_registry",
            lambda *a, **k: bent,
        ):
            with self.assertRaises(AttributeError):
                login_scene_admission.login_entry_is_pinned(
                    ADMISSIBLE_ON_DISK
                )
            with self.assertRaises(AttributeError):
                login_scene_admission.stageable_scene_ids()

    def test_a_lookup_that_fails_oddly_on_the_file_path_also_raises(self):
        # The OTHER half of the same guard, and the mutation battery found
        # it uncovered: `registry[scene_id]` raising anything that is not
        # `KeyError`.  `SceneRegistry.__getitem__` raises only `KeyError`,
        # so this is unreachable with lane A's real class today -- it is a
        # pin against a future registry type whose lookup fails differently,
        # which must stay LOUD on the file path for the same reason a bent
        # row does.
        class _OddLookup:
            destinations = ()

            def __getitem__(self, _key):
                raise TypeError("this registry indexes by something else")

        odd = _OddLookup()
        with mock.patch.object(
            login_scene_admission.world_scene_travel,
            "load_scene_registry",
            lambda *a, **k: odd,
        ):
            with self.assertRaises(TypeError):
                login_scene_admission.login_entry_is_pinned(ADMISSIBLE_ON_DISK)
        # Supplied by a caller, the same object only refuses.
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(
                ADMISSIBLE_ON_DISK, scene_registry=odd
            )
        )

    def test_the_same_bent_row_supplied_by_a_caller_only_refuses(self):
        # The other half of the same decision: an object this module cannot
        # vouch for must not raise into `runtime.py`, which swallows
        # `TypeError` from this lane's call site into a silent `None`.
        bent = self._bent_registry()
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(
                ADMISSIBLE_ON_DISK, scene_registry=bent
            )
        )
        # AND THE COST IS ONE SCENE, NOT THE LANE.  The bent row is
        # refused; the sound rows beside it still answer.  That asymmetry
        # with the file path above is the point of `trusted`: this module's
        # own load raising is a fault a person should see, while a
        # caller-supplied object degrading per row is the most this lane may
        # do with an object it cannot vouch for.
        self.assertEqual(
            tuple(
                scene_id
                for scene_id in ADMISSIBLE_ON_DISK_TODAY
                if scene_id != ADMISSIBLE_ON_DISK
            ),
            login_scene_admission.stageable_scene_ids(scene_registry=bent),
        )


class _ConfigFixture(unittest.TestCase):
    """A GM account with one staged entry, in a temp directory."""

    ACCOUNT = "gm_snapshot_tester"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.accounts_path = root / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.ACCOUNT]}), encoding="utf-8"
        )
        self.scene_path = root / "gm_login_scene.json"
        self.standalone_path = root / "gm_login_scene_standalone.json"
        self.standalone_path.write_text(
            json.dumps({login_scene_override.STANDALONE_JSON_KEY: {}}),
            encoding="utf-8",
        )

    def write_staged(self, scene_id: int) -> None:
        self.scene_path.write_text(
            json.dumps({"gm_login_scene": {self.ACCOUNT: scene_id}}),
            encoding="utf-8",
        )

    def consume(self, scene_registry=None):
        return login_scene_consume.consume_login_scene_override(
            self.ACCOUNT,
            gm_accounts_config_path=self.accounts_path,
            login_scene_config_path=self.scene_path,
            standalone_config_path=self.standalone_path,
            scene_registry=scene_registry,
        )


class SnapshotIsWiderTests(_ConfigFixture):
    """The process would accept the destination; the file no longer does.

    Reachable without anybody editing anything by hand: lane A pins a new
    destination, the server boots with it, and the entry is then removed or
    barred in a later commit that the running process has not read.
    """

    def test_the_file_reading_refuses_and_takes_every_override_with_it(self):
        self.write_staged(BARRED_ON_DISK)
        result = self.consume()
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)
        self.assertIsNone(result.scene_id)
        # AND THE ENTRY IS STILL THERE, which is the part that makes this a
        # standing fault rather than one bad login: every later login takes
        # the same path and gets the same answer.
        self.assertEqual(
            {self.ACCOUNT: BARRED_ON_DISK},
            json.loads(self.scene_path.read_text(encoding="utf-8"))[
                "gm_login_scene"
            ],
        )

    def test_the_snapshot_reading_honours_the_entry_and_spends_it(self):
        self.write_staged(BARRED_ON_DISK)
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        result = self.consume(scene_registry=snapshot)
        self.assertEqual(login_scene_consume.CONSUMED, result.outcome)
        self.assertEqual(BARRED_ON_DISK, result.scene_id)
        # Single use is not weakened by the parameter: COO-DECISION
        # 20260829_0441 item 2 still holds, and the second read proves the
        # entry really came off disk rather than being reported as spent.
        self.assertEqual(
            login_scene_consume.NOTHING_STAGED,
            self.consume(scene_registry=snapshot).outcome,
        )


class SnapshotIsNarrowerTests(_ConfigFixture):
    """The file would accept the destination; the process would not.

    This direction is ALREADY handled at chief's call site by the
    `resolve_entry` probe, and the point of measuring it here is that the
    two are consistent: with the snapshot supplied, the entry is refused
    BEFORE it is spent, so there is nothing for that call site to restore.
    """

    def test_a_dropped_destination_is_refused_before_the_entry_is_spent(self):
        self.write_staged(ADMISSIBLE_ON_DISK)
        snapshot = _registry_without_scene(ADMISSIBLE_ON_DISK)
        result = self.consume(scene_registry=snapshot)
        self.assertEqual(login_scene_consume.CONSUME_FAILED, result.outcome)
        self.assertIsNone(result.scene_id)
        self.assertEqual(
            {self.ACCOUNT: ADMISSIBLE_ON_DISK},
            json.loads(self.scene_path.read_text(encoding="utf-8"))[
                "gm_login_scene"
            ],
        )

    def test_the_same_entry_is_spent_when_no_snapshot_is_supplied(self):
        # The control for the test above: nothing about the entry itself
        # refuses it, only the reading it was judged against.
        self.write_staged(ADMISSIBLE_ON_DISK)
        result = self.consume()
        self.assertEqual(login_scene_consume.CONSUMED, result.outcome)
        self.assertEqual(ADMISSIBLE_ON_DISK, result.scene_id)


class ASnapshotMayOnlyNarrowAWriteTests(_ConfigFixture):
    """The file decides what may be WRITTEN; the snapshot may refuse on top.

    THE DEFECT THIS CLASS EXISTS FOR (pf-adversary, round 7hfrt0, D2).  An
    earlier version of this round let a boot snapshot WIDEN a write: stage
    a scene the snapshot admits and the file does not, and the entry lands
    in `config/gm_login_scene.json`.  `_load_scene_id_map` then refuses
    that file -- the WHOLE file, not the line -- so every other account's
    override dies with it.  And no removal path in this lane can clear it:
    `restore_login_scene` and `claim_login_scene` both re-validate the
    whole file first, so they refuse it too.  It takes a hand edit of a
    gitignored config.

    It needed no exotic wiring: one server RESTART re-reads the registry
    file, and the fresh (narrow) reading meets the entry the old (wide) one
    authorised.  THE ENTRY OUTLIVES THE PROCESS THAT WROTE IT, which is the
    whole asymmetry -- reading may honour one process's view, writing may
    not.
    """

    OTHER_ACCOUNT = "gm_innocent_bystander"

    def setUp(self) -> None:
        super().setUp()
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.ACCOUNT, self.OTHER_ACCOUNT]}),
            encoding="utf-8",
        )

    def stage(self, account, scene_id, scene_registry=None):
        return login_scene_stage.stage_login_scene(
            account,
            scene_id,
            gm_accounts_config_path=self.accounts_path,
            config_path=self.scene_path,
            scene_registry=scene_registry,
        )

    def test_a_wider_snapshot_does_not_let_a_write_through(self):
        result = self.stage(
            self.ACCOUNT,
            BARRED_ON_DISK,
            scene_registry=_registry_with_scene_allowed(BARRED_ON_DISK),
        )
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_NO_LOGIN_ENTRY, result.reason)
        self.assertFalse(self.scene_path.is_file())

    def test_a_narrower_snapshot_still_refuses(self):
        result = self.stage(
            self.ACCOUNT,
            ADMISSIBLE_ON_DISK,
            scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK),
        )
        self.assertFalse(result.staged)
        self.assertEqual(login_scene_stage.REASON_NO_LOGIN_ENTRY, result.reason)
        # REFUSED MEANS THE FILE IS UNTOUCHED, the same promise every other
        # refusal in `login_scene_stage` makes.
        self.assertFalse(self.scene_path.is_file())

    def test_no_snapshot_can_make_a_written_file_unreadable_by_default(self):
        # THE PROPERTY, stated as a property rather than as a case: whatever
        # snapshot a write is judged against, the file it leaves behind must
        # load under the DEFAULT (file) reading -- because that is the
        # reading the next process boots with.
        self.assertTrue(self.stage(self.OTHER_ACCOUNT, ADMISSIBLE_ON_DISK).staged)
        for scene_id in (BARRED_ON_DISK, 17, 999999):
            for snapshot in (
                _registry_with_scene_allowed(BARRED_ON_DISK),
                _registry_with_scene_allowed(17),
                None,
            ):
                with self.subTest(scene_id=scene_id, snapshot=bool(snapshot)):
                    self.stage(self.ACCOUNT, scene_id, scene_registry=snapshot)
                    # The default reader still loads the file, and the
                    # innocent third account still has its override.
                    self.assertEqual(
                        {self.OTHER_ACCOUNT: ADMISSIBLE_ON_DISK},
                        login_scene_override.load_login_scene_overrides(
                            self.scene_path
                        ),
                    )

    def test_the_bystanders_override_survives_and_is_still_removable(self):
        # The second half of D2: the poisoned file could not be CLEARED
        # either, because every removal path re-validates it first.  With
        # writes held to the file's own reading, both removal paths work
        # under either reading.
        self.assertTrue(self.stage(self.OTHER_ACCOUNT, ADMISSIBLE_ON_DISK).staged)
        self.stage(
            self.ACCOUNT,
            BARRED_ON_DISK,
            scene_registry=_registry_with_scene_allowed(BARRED_ON_DISK),
        )
        self.assertEqual(
            ADMISSIBLE_ON_DISK,
            login_scene_stage.claim_login_scene(
                self.OTHER_ACCOUNT, config_path=self.scene_path
            ),
        )


class TheStagingSideHonoursItTooTests(_ConfigFixture):
    """`/warp`'s writer, not just the login reader.

    The staging side is where a refusal can still reach a person: chief's
    call site can only refuse at a login, where this lane has no way to say
    anything to the tester (`gm/say_wire.py`'s send gate is shut on
    RE-132).  A `/warp` refused at the moment it is typed is the only
    refusal in this chain that a human is present for -- once the call
    sites in `CORE-REQUEST-GM-036` are wired.
    """

    def test_the_snapshot_narrows_what_a_warp_may_stage(self):
        # Without the snapshot this scene stages; with it, it does not.
        # That is the whole tester-facing effect of the parameter on this
        # side, and it is a NARROWING -- see `ASnapshotMayOnlyNarrowAWrite`.
        self.assertTrue(
            login_scene_stage.stage_login_scene(
                self.ACCOUNT,
                ADMISSIBLE_ON_DISK,
                gm_accounts_config_path=self.accounts_path,
                config_path=self.scene_path,
            ).staged
        )
        self.scene_path.unlink()
        self.assertFalse(
            login_scene_stage.stage_login_scene(
                self.ACCOUNT,
                ADMISSIBLE_ON_DISK,
                gm_accounts_config_path=self.accounts_path,
                config_path=self.scene_path,
                scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK),
            ).staged
        )

    def test_an_undo_reaches_a_file_only_the_snapshot_can_load(self):
        # THE HOP THE MUTATION BATTERY FOUND UNTESTED (pf-adversary, round
        # 7hfrt0, D4 row 1): `restore_login_scene` could drop the keyword
        # entirely and 4599 tests stayed green.
        #
        # A write can no longer put an entry in this file that the disk
        # reading refuses (`ASnapshotMayOnlyNarrowAWriteTests`), so the
        # reachable way in is the one that was always there: AN OPERATOR
        # WITH A TEXT EDITOR.  Both config files in this lane are hand-
        # edited in the field -- that is the whole reason the reader has an
        # admission check at all (round qq0i9u) -- and a boot snapshot from
        # before lane A narrowed the registry is exactly what makes such a
        # file loadable by the running process and not by a fresh read.
        #
        # Graded on the FILE: with the keyword dropped anywhere between
        # here and `_write_entry_locked`, the whole-file validation is done
        # with the disk reading, it refuses, and the entry this call exists
        # to remove is still there.
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        self.scene_path.write_text(
            json.dumps(
                {
                    "gm_login_scene": {
                        "hand_edited_other_account": BARRED_ON_DISK,
                        self.ACCOUNT: ADMISSIBLE_ON_DISK,
                    }
                }
            ),
            encoding="utf-8",
        )
        # The premise, asserted rather than assumed: the default reading
        # cannot load this file at all, and the snapshot can.
        with self.assertRaises(ValueError):
            login_scene_override.load_login_scene_overrides(self.scene_path)
        self.assertEqual(
            {
                "hand_edited_other_account": BARRED_ON_DISK,
                self.ACCOUNT: ADMISSIBLE_ON_DISK,
            },
            login_scene_override.load_login_scene_overrides(
                self.scene_path, scene_registry=snapshot
            ),
        )

        self.assertTrue(
            login_scene_stage.restore_login_scene(
                self.ACCOUNT,
                None,
                gm_accounts_config_path=self.accounts_path,
                config_path=self.scene_path,
                scene_registry=snapshot,
            )
        )
        self.assertEqual(
            {"hand_edited_other_account": BARRED_ON_DISK},
            login_scene_override.load_login_scene_overrides(
                self.scene_path, scene_registry=snapshot
            ),
        )

    def test_the_chat_undo_uses_the_same_reading_as_its_stage(self):
        # `chat_command_action`'s `_undo`, the hop above this one.  It runs
        # only when the outcome audit row cannot be written -- the rule
        # being enforced is "this house does not perform an effect it
        # cannot record", and an undo that refuses leaves exactly the
        # effect the rule forbids.
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        self.scene_path.write_text(
            json.dumps(
                {"gm_login_scene": {"hand_edited_other": BARRED_ON_DISK}}
            ),
            encoding="utf-8",
        )
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        gm_dispatch.reset_rate_limit_state_for_tests()
        session = _FakeSession(self.ACCOUNT)
        log_path = Path(self._tmp.name) / "capture" / "log.ndjson"
        with mock.patch.object(
            chat_command_action, "_log_outcome", lambda *a, **k: False
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                chat_command_action.make_gm_chat_command_action(
                    session,
                    _chat_payload(f"/warp {ADMISSIBLE_ON_DISK}"),
                    legacy,
                    config_path=str(self.accounts_path),
                    log_path=str(log_path),
                    login_scene_config_path=str(self.scene_path),
                    scene_registry=snapshot,
                )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_REVERTED, session.events
        )
        self.assertEqual(
            {"hand_edited_other": BARRED_ON_DISK},
            login_scene_override.load_login_scene_overrides(
                self.scene_path, scene_registry=snapshot
            ),
        )

    def test_a_claim_reaches_a_file_only_the_snapshot_can_load(self):
        # The post-claim READ-BACK hop (`claim_login_scene`'s `after`),
        # which the mutation battery found uncovered: it runs on the
        # SUCCESS path, inside the write lock, and its only vocabulary for
        # a load it cannot do is `None` -- which this function's caller is
        # required to read as "somebody else took it".  A spent entry
        # reported as a lost race is the worst answer available here.
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        self.scene_path.write_text(
            json.dumps(
                {
                    "gm_login_scene": {
                        "hand_edited_other": BARRED_ON_DISK,
                        self.ACCOUNT: ADMISSIBLE_ON_DISK,
                    }
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            login_scene_override.load_login_scene_overrides(self.scene_path)
        self.assertEqual(
            ADMISSIBLE_ON_DISK,
            login_scene_stage.claim_login_scene(
                self.ACCOUNT,
                config_path=self.scene_path,
                scene_registry=snapshot,
            ),
        )
        self.assertEqual(
            {"hand_edited_other": BARRED_ON_DISK},
            login_scene_override.load_login_scene_overrides(
                self.scene_path, scene_registry=snapshot
            ),
        )

    def test_a_claim_under_a_snapshot_takes_the_entry_off_disk(self):
        snapshot = _registry_without_scene(BARRED_ON_DISK)
        self.write_staged(ADMISSIBLE_ON_DISK)
        self.assertEqual(
            ADMISSIBLE_ON_DISK,
            login_scene_stage.claim_login_scene(
                self.ACCOUNT,
                config_path=self.scene_path,
                scene_registry=snapshot,
            ),
        )
        self.assertIsNone(
            login_scene_stage.claim_login_scene(
                self.ACCOUNT,
                config_path=self.scene_path,
                scene_registry=snapshot,
            )
        )


class TheStandaloneMapIsJudgedTheSameWayTests(_ConfigFixture):
    """The branch the first version of this file never executed.

    `_ConfigFixture` wrote an EMPTY standalone map, so every standalone hop
    was green because the loop had zero items (pf-adversary, round 7hfrt0,
    D4).  It is the worst branch to leave untested: `COO-DECISION
    20260829_0542` says the standalone map is NEVER consumed, so an entry
    there is permanent rather than one-shot.
    """

    PLAIN_ACCOUNT = "plain_tester_not_a_gm"

    def write_standalone(self, scene_id: int) -> None:
        self.standalone_path.write_text(
            json.dumps(
                {
                    login_scene_override.STANDALONE_JSON_KEY: {
                        self.PLAIN_ACCOUNT: scene_id
                    }
                }
            ),
            encoding="utf-8",
        )

    def consume_plain(self, scene_registry=None):
        return login_scene_consume.consume_login_scene_override(
            self.PLAIN_ACCOUNT,
            gm_accounts_config_path=self.accounts_path,
            login_scene_config_path=self.scene_path,
            standalone_config_path=self.standalone_path,
            scene_registry=scene_registry,
        )

    def test_a_narrower_snapshot_refuses_a_standing_standalone_entry(self):
        self.write_standalone(ADMISSIBLE_ON_DISK)
        kept = self.consume_plain()
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, kept.outcome
        )
        self.assertEqual(ADMISSIBLE_ON_DISK, kept.scene_id)

        refused = self.consume_plain(
            scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK)
        )
        self.assertEqual(login_scene_consume.CONSUME_FAILED, refused.outcome)
        self.assertIsNone(refused.scene_id)

    def test_the_standalone_entry_is_still_never_consumed(self):
        # COO-DECISION 20260829_0542 is not weakened by the parameter: the
        # entry is left on disk and answers again on the next login.
        self.write_standalone(ADMISSIBLE_ON_DISK)
        snapshot = _registry_without_scene(BARRED_ON_DISK)
        for _ in range(2):
            result = self.consume_plain(scene_registry=snapshot)
            self.assertEqual(
                login_scene_consume.STANDALONE_NOT_CONSUMED, result.outcome
            )
            self.assertEqual(ADMISSIBLE_ON_DISK, result.scene_id)
        self.assertEqual(
            {self.PLAIN_ACCOUNT: ADMISSIBLE_ON_DISK},
            json.loads(self.standalone_path.read_text(encoding="utf-8"))[
                login_scene_override.STANDALONE_JSON_KEY
            ],
        )


class TheLoserOfAClaimIsAskedUnderTheSameReadingTests(_ConfigFixture):
    """`_ask_the_standalone_map`, reached only by the loser of a claim.

    THE HOP THE MUTATION BATTERY FOUND UNCOVERED (pf-adversary, round
    7hfrt0, D4).  `consume_login_scene_override` calls this branch when the
    GM map held an entry a moment ago and no longer does -- another login
    took it, or the removal failed.  pf-adversary measured in an earlier
    round that the loser used to lose a STANDING standalone entry as well
    (420 of 420 losers over 60 trials x 8 threads), which is why the branch
    asks the standalone map instead of concluding by elimination.

    If the caller's reading does not reach that ask, the loser gets
    `CONSUME_FAILED` where it should get its standing standalone scene --
    the same class of regression, arriving through the parameter meant to
    prevent one.
    """

    def test_the_loser_keeps_a_standing_entry_the_snapshot_admits(self):
        snapshot = _registry_with_scene_allowed(BARRED_ON_DISK)
        self.write_staged(ADMISSIBLE_ON_DISK)
        # Hand-edited standalone entry naming a scene ONLY the snapshot
        # admits -- so a load done with the file reading refuses it.
        self.standalone_path.write_text(
            json.dumps(
                {
                    login_scene_override.STANDALONE_JSON_KEY: {
                        self.ACCOUNT: BARRED_ON_DISK
                    }
                }
            ),
            encoding="utf-8",
        )
        real_claim = login_scene_stage.claim_login_scene
        state = {"stolen": False}

        def lose_the_claim(account_name, *, config_path=None, scene_registry=None):
            # Another login takes the entry a moment before we do, so this
            # call's own claim comes back None.
            if not state["stolen"]:
                state["stolen"] = True
                real_claim(
                    account_name,
                    config_path=config_path,
                    scene_registry=scene_registry,
                )
            return real_claim(
                account_name,
                config_path=config_path,
                scene_registry=scene_registry,
            )

        with mock.patch.object(
            login_scene_stage, "claim_login_scene", lose_the_claim
        ):
            loser = self.consume(scene_registry=snapshot)
        self.assertTrue(state["stolen"], "the claim was never contested")
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, loser.outcome
        )
        self.assertEqual(BARRED_ON_DISK, loser.scene_id)


class TheConfigRefusalNamesTheCallersReadingTests(_ConfigFixture):
    """`GM_LOGIN_SCENE_CONFIG_REFUSED` and the `ValueError` beside it.

    The chat-layer way out was tested; this one -- the loader's own,
    the line an operator with a hand-edited config actually sees -- was
    not (pf-adversary, round 7hfrt0, D4).  It is also the line that goes
    through `console_safe`, so it is the one where a Thai account name is
    in play.
    """

    def test_the_refusal_and_its_way_out_both_come_from_the_snapshot(self):
        self.write_staged(ADMISSIBLE_ON_DISK)
        snapshot = _registry_without_scene(ADMISSIBLE_ON_DISK)
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            with self.assertRaises(ValueError) as caught:
                login_scene_override.load_login_scene_overrides(
                    self.scene_path, scene_registry=snapshot
                )
        # `load_login_scene_overrides` reads the GM-gated (single-use) map,
        # so its own way out is `single_use_stageable_scene_ids`, not the
        # plain `stageable_scene_ids` -- they have differed by one scene
        # (126) since round R249 landed lane A's row (chief, gate-red
        # repair of `pirate-force-server#332`, `CORE-REQUEST-GM-038`).
        expected = str(
            login_scene_admission.single_use_stageable_scene_ids(
                scene_registry=snapshot
            )
        )
        self.assertIn(expected, str(caught.exception))
        console = buffer.getvalue()
        self.assertIn("GM_LOGIN_SCENE_CONFIG_REFUSED", console)
        self.assertIn(f"stageable={expected}", console)
        # And the disk reading -- which admits this entry -- is not what
        # either of them named.
        self.assertNotEqual(
            expected, str(login_scene_admission.stageable_scene_ids())
        )


class _FakePosition:
    def __init__(self, scene_id=1):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = 10.0
        self.y = 20.0
        self.z = 30.0


class _FakeSelected:
    def __init__(self, position):
        self.position = position
        self.id = 4242


class _FakeFoundation:
    def __init__(self, selected):
        self.selected = selected


class _FakeSession:
    def __init__(self, token):
        self.token = token
        self.events = []
        self.foundation = _FakeFoundation(_FakeSelected(_FakePosition()))


def _chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class TheChatCommandCarriesItAllTheWayDownTests(_ConfigFixture):
    """`/warp` typed into the real dispatch, with a snapshot supplied.

    The signature chain from `make_gm_chat_command_action` down to
    `stage_login_scene` is four hops long and every hop is a place a keyword
    can be dropped without any existing test noticing -- the suite was green
    with the parameter added and not passed on.  So this drives the entry
    point chief's call site actually calls, and grades on the FILE and the
    console line rather than on any of the hops.
    """

    def setUp(self) -> None:
        super().setUp()
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.log_path = Path(self._tmp.name) / "capture" / "log.ndjson"
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def warp(self, session, scene_id, scene_registry=None):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            chat_command_action.make_gm_chat_command_action(
                session,
                _chat_payload(f"/warp {scene_id}"),
                self.legacy,
                config_path=str(self.accounts_path),
                log_path=str(self.log_path),
                login_scene_config_path=str(self.scene_path),
                scene_registry=scene_registry,
            )
        return buffer.getvalue()

    def staged_map(self):
        if not self.scene_path.is_file():
            return {}
        return json.loads(self.scene_path.read_text(encoding="utf-8"))[
            "gm_login_scene"
        ]

    def test_a_typed_warp_is_judged_against_the_supplied_snapshot(self):
        # Without the snapshot the scene stages; with a snapshot that has
        # dropped it, the same chat line does not.  Graded on the FILE,
        # which is the only thing the four hops between here and
        # `stage_login_scene` cannot fake.
        session = _FakeSession(self.ACCOUNT)
        self.warp(session, ADMISSIBLE_ON_DISK)
        self.assertEqual({self.ACCOUNT: ADMISSIBLE_ON_DISK}, self.staged_map())

        self.scene_path.unlink()
        session = _FakeSession(self.ACCOUNT)
        self.warp(
            session,
            ADMISSIBLE_ON_DISK,
            scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK),
        )
        self.assertEqual({}, self.staged_map())

    def test_a_wider_snapshot_does_not_let_a_typed_warp_through_either(self):
        # The same rule as `ASnapshotMayOnlyNarrowAWriteTests`, reached
        # through the real chat entry point rather than the writer: a
        # snapshot cannot widen what a `/warp` may put on disk, because the
        # entry outlives the process whose snapshot approved it.
        session = _FakeSession(self.ACCOUNT)
        self.warp(
            session,
            BARRED_ON_DISK,
            scene_registry=_registry_with_scene_allowed(BARRED_ON_DISK),
        )
        self.assertEqual({}, self.staged_map())

    def test_the_console_way_out_names_the_snapshot_set(self):
        # The refusal and the list printed with it have to come from ONE
        # reading.  Under a snapshot that drops scene 2, a way out still
        # naming 2 would send the tester to the one destination the running
        # process cannot give them.
        session = _FakeSession(self.ACCOUNT)
        console = self.warp(
            session,
            ADMISSIBLE_ON_DISK,
            scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK),
        )
        lines = [
            line
            for line in console.splitlines()
            if line.startswith(chat_command_action.WARP_REFUSED_CONSOLE_TOKEN)
        ]
        self.assertEqual(1, len(lines), console)
        self.assertEqual({}, self.staged_map())
        self.assertIn("stageable=", lines[0])
        # PARSED, NOT SUBSTRING-MATCHED.  The first version of this
        # assertion asked whether "2" appeared in the printed tuple and was
        # satisfied by the "2" inside 278 -- a green test that would have
        # stayed green while the line named the very scene it must not.
        printed = lines[0].split("stageable=", 1)[1].strip()
        ids = {
            int(part)
            for part in printed.strip("()").replace(",", " ").split()
        }
        self.assertNotIn(ADMISSIBLE_ON_DISK, ids)
        # `/warp` writes the GM-gated (single-use) map, so its way out is
        # `single_use_stageable_scene_ids`, not the plain
        # `stageable_scene_ids` -- they have differed by one scene (126)
        # since round R249 landed lane A's row (chief, gate-red repair of
        # `pirate-force-server#332`, `CORE-REQUEST-GM-038`).  Computed
        # against the SAME snapshot passed to `self.warp` above, since the
        # printed line and the refusal must come from one reading.
        self.assertEqual(
            set(
                login_scene_admission.single_use_stageable_scene_ids(
                    scene_registry=_registry_without_scene(ADMISSIBLE_ON_DISK)
                )
            ),
            ids,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
