"""NPC-HP-LINK-001/002/003 (HYP-PF-029) -- the lane's wiring, driven for real.

WHAT THIS FILE PROVES, AND WHAT IT DELIBERATELY DOES NOT
---------------------------------------------------------
``tests/test_npc_hp_link_hypothesis.py`` proves the encoder offline.  This file
proves the WIRING that surrounds it, and that wiring now has THREE layers built
by three checkpoints:

  * **NPC-HP-LINK-001 wired the ``app.py`` FLAG.**
  * **NPC-HP-LINK-002 wires the ``runtime.py`` DISPATCH BRANCH.**
    ``make_state_class`` now takes the ``npc_hp_link_hypothesis_scenario``
    keyword, derives the lane's wire unlock and resolves the frozen target once
    at construction behind that keyword, and answers one accepted chat-input
    frame with the eight-frame sweep through
    ``_dispatch_npc_hp_link_hypothesis``.  ``NpcHpLinkDispatchTests`` below
    drives that branch for real, headless, on a throwaway database.

  * **NPC-HP-LINK-003 joins the flag to the branch.**  ``app.py`` now hands
    ``make_state_class`` the ``npc_hp_link_hypothesis_scenario`` keyword, so
    the CLI flag reaches the branch and the scenario file's ``dispatch`` block
    describes the wiring that exists rather than a gap.  That correction had to
    be made in ONE pass across the JSON, ``_expected_scenario()`` and the
    offline verifier, because the composer pins the whole scenario tree by
    exact equality.  ``KnownWiringGapTests`` below measures that coupling
    against the corrected file, in both directions, so the JSON can never
    drift away from the code again.

What IS driven for real, by running the real ``app.py`` entry point in a
subprocess:

  * the flag ``--npc-hp-link-hypothesis-scenario`` exists and loads the one
    opt-in file;
  * without an explicit ``--db`` it refuses by name and boots nothing;
  * it is MUTUALLY EXCLUSIVE with every other scenario mode -- driven pairwise
    against every other scenario flag ``app.py`` accepts;
  * a scenario file outside the exact allowlist fails closed rather than
    booting a half-configured lane.

Plus containment: the lane touches no database (it has no write path and adds
no column), the two shipped tools run clean and print pure ASCII, and no
foreign lane's module is imported by this one.

NOT proven here, and this is the load-bearing limit: whether a real client
moves the target's HP bar when it receives these bytes.  **No client has ever
been shown one byte of this profile**, and whether the client renders the
intermediate value 37 on the target's bar is UNDECIDABLE from static analysis
and is the queued attended test.  The only thing proven so far is the negative:
505 damage delivered on 2026-08-20 and the bar did not move.

DISCIPLINE.  Every database in the dispatch class is a fresh ``tempfile`` one
that is deleted on exit.  The repository's canonical database is never opened
-- it is only ``stat``-ed, once at import and once at the end, so a regression
that reached for it would be reported rather than silently tolerated.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import npc_hp_link_hypothesis as nh  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "npc_hp_link_hypothesis_target_sweep.json"
APP_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "app.py"
RUNTIME_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
MODULE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "npc_hp_link_hypothesis.py"
)
VERIFY_TOOL = ROOT / "tools" / "verify_npc_hp_link_encoder.py"
REPLAY_TOOL = ROOT / "tools" / "pf_npc_hp_link_headless_replay.py"

# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")

FLAG = "--npc-hp-link-hypothesis-scenario"
# Every other scenario flag app.py accepts.  The lane must be refused
# alongside all of them, one pair at a time.
OTHER_MODE_FLAGS = {
    "--scenario": "arena_v1.json",
    "--scene-load-scenario": "scene2_load_only.json",
    "--population-scenario": "object_population_v94.json",
    "--item-move-hypothesis-scenario": "item_move_hypothesis_v111_slot2.json",
    "--logout-hypothesis-scenario": "logout_hypothesis_ack_echo.json",
    "--chat-input-hypothesis-scenario": "chat_input_hypothesis_echo.json",
    "--channel-message-hypothesis-scenario":
        "channel_message_hypothesis_channel_sweep.json",
    "--delete-actor-hypothesis-scenario":
        "delete_actor_hypothesis_soft_delete.json",
    "--delete-refresh-hypothesis-scenario":
        "delete_refresh_hypothesis_list_rebuild.json",
    "--stats-progression-hypothesis-scenario":
        "stats_progression_hypothesis_xp_sweep.json",
    "--hp-death-hypothesis-scenario": "hp_death_hypothesis_death_sweep.json",
    "--runtimeres-death-hypothesis-scenario":
        "runtimeres_death_hypothesis_spawn_then_kill.json",
    "--damage-model-hypothesis-scenario":
        "damage_model_hypothesis_npc_sweep.json",
    "--damage-hp-link-hypothesis-scenario":
        "damage_hp_link_hypothesis_link_sweep.json",
    "--remote-player-hypothesis-scenario":
        "remote_player_hypothesis_visibility_probe.json",
    "--npc-hostile-hypothesis-scenario":
        "npc_hostile_hypothesis_faction_pairing.json",
}


def _canonical_stat():
    """Size and mtime of the canonical database, WITHOUT opening it."""
    if not CANONICAL_DB.exists():
        return None
    info = CANONICAL_DB.stat()
    return (info.st_size, info.st_mtime_ns)


_CANONICAL_AT_IMPORT = _canonical_stat()


def tearDownModule():
    """Round 41's lesson, enforced: pytest may not move the canonical file."""
    if _canonical_stat() != _CANONICAL_AT_IMPORT:
        raise AssertionError(
            "this test module changed the canonical database's size or mtime; "
            "this lane writes nothing and this suite opens no database"
        )


def _run_app(args, timeout=180):
    """Run the REAL app.py entry point, in a subprocess, and report."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get(
        "PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "pirateforce_foundation.app", *args],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
        timeout=timeout,
    )


class AppFlagTests(unittest.TestCase):
    def test_the_flag_exists_and_is_the_pinned_spelling(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("pre.add_argument('%s')" % FLAG, source)
        self.assertIn("load_npc_hp_link_hypothesis_scenario", source)
        self.assertIn(
            "from .npc_hp_link_hypothesis import (", source)

    def test_the_app_carries_exactly_one_ledger_annotation_for_this_lane(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-029 active"), 1)

    def test_the_flag_demands_an_explicit_existing_database(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "'--npc-hp-link-hypothesis-scenario requires an explicit '",
            source,
        )
        result = _run_app([FLAG, str(SCENARIO_PATH)])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(
            "--npc-hp-link-hypothesis-scenario requires an explicit "
            "existing --db",
            result.stderr,
        )

    def test_the_flag_is_named_in_the_mutual_exclusion_message(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "'--npc-hp-link-hypothesis-scenario are mutually exclusive'",
            source,
        )

    def test_the_lane_is_refused_alongside_every_other_scenario_mode(self):
        """Driven pairwise through the real entry point, not asserted on
        source text: sixteen pairs, one per other scenario flag app.py takes."""
        self.assertGreaterEqual(len(OTHER_MODE_FLAGS), 15)
        for other_flag, other_file in OTHER_MODE_FLAGS.items():
            other_path = ROOT / "scenarios" / other_file
            with self.subTest(other=other_flag):
                self.assertTrue(other_path.is_file(), other_path)
                result = _run_app([
                    FLAG, str(SCENARIO_PATH), other_flag, str(other_path),
                ])
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("mutually exclusive", result.stderr)

    def test_a_scenario_outside_the_allowlist_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
            tree["dispatch"]["one_shot"] = False
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(tree), encoding="utf-8")
            result = _run_app([FLAG, str(bad)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scenario_file_exceeds_allowlist", result.stderr)

    def test_a_missing_scenario_file_fails_closed(self):
        result = _run_app([FLAG, str(ROOT / "scenarios" / "does_not_exist.json")])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scenario_file_exceeds_allowlist", result.stderr)

    def test_the_flag_is_in_the_existing_database_and_migrate_branches(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("or npc_hp_link_hypothesis is not None"), 2)
        self.assertIn("'npc-hp-link-hypothesis'", source)
        self.assertIn(
            "if npc_hp_link_hypothesis is not None else", source)

    def test_no_other_lanes_wiring_was_disturbed(self):
        """Every neighbouring lane's flag, error string and kwarg is still
        exactly where it was."""
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        for other_flag in OTHER_MODE_FLAGS:
            with self.subTest(other=other_flag):
                self.assertIn("pre.add_argument('%s')" % other_flag, source)
        for kwarg in (
            "damage_hp_link_hypothesis_scenario=damage_hp_link_hypothesis,",
            "npc_hostile_hypothesis_scenario=npc_hostile_hypothesis,",
            "runtimeres_death_hypothesis_scenario=runtimeres_death_hypothesis,",
            "damage_model_hypothesis_scenario=damage_model_hypothesis,",
        ):
            with self.subTest(kwarg=kwarg):
                self.assertIn(kwarg, source)


class DispatchBranchWiringTests(unittest.TestCase):
    """NPC-HP-LINK-002: the runtime branch EXISTS, and here is its shape.

    Source-text assertions only; ``NpcHpLinkDispatchTests`` further down drives
    the same branch for real.  These are the assertions the previous checkpoint
    wrote as their own negatives, flipped, so the two states can never be
    confused for one another.
    """

    def test_make_state_class_takes_this_lanes_keyword(self):
        parameters = inspect.signature(make_state_class).parameters
        self.assertEqual(
            nh.NPC_HP_LINK_DISPATCH_KWARG, "npc_hp_link_hypothesis_scenario")
        self.assertIn(nh.NPC_HP_LINK_DISPATCH_KWARG, parameters)
        self.assertIsNone(
            parameters[nh.NPC_HP_LINK_DISPATCH_KWARG].default)

    def test_the_runtime_branch_is_gated_on_the_scenario_and_the_vital_id(self):
        """The branch must read BOTH conditions, and there must be one of it."""
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "            if (\n"
            "                npc_hp_link_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID\n"
            "            ):\n",
            source,
        )
        # The unlock and the frozen target are derived once, behind the same
        # gate, at construction.
        self.assertIn(
            "    if npc_hp_link_hypothesis_scenario is not None:\n", source)
        self.assertIn("npc_hp_link_unlock = npc_hp_link_wire_unlock(", source)
        self.assertIn(
            "npc_hp_link_target = resolve_npc_hp_link_target(legacy)", source)
        # Exactly one call site, inside the branch: the dispatcher composes
        # nowhere else and nothing else composes for it.
        self.assertEqual(source.count("build_npc_hp_link_sweep("), 1)
        self.assertEqual(
            source.count("def _dispatch_npc_hp_link_hypothesis("), 1)
        self.assertEqual(
            source.count("self._dispatch_npc_hp_link_hypothesis("), 1)
        # The ledger annotation binds this file and the ledger entry both
        # ways, and verify_hypothesis_ledger.py rejects a duplicate per file.
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-029 active"), 1)

    def test_the_lane_is_named_in_the_runtime_mutual_exclusion_refusal(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("npc hp link hypothesis scenarios are mutually", source)

    def test_the_branch_emits_the_modules_event_name_and_only_that_one(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            nh.NPC_HP_LINK_EVENT_NAME,
            "npc_hp_link_hypothesis_target_sweep_sent")
        self.assertIn(nh.NPC_HP_LINK_EVENT_NAME, source)
        # One published success name, cross-checked against the constant so a
        # rename is a RuntimeError rather than a silent drift.
        self.assertEqual(source.count(nh.NPC_HP_LINK_EVENT_NAME), 1)
        self.assertIn("HYP-PF-029 sweep event name drift", source)

    def test_the_runtime_source_stays_pure_ascii(self):
        self.assertTrue(
            all(byte < 0x80 for byte in RUNTIME_SOURCE_PATH.read_bytes()))

    def test_the_trigger_the_lane_is_designed_for_is_written_down(self):
        tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            tree["dispatch"]["trigger"],
            "one_accepted_34_byte_ascii12_chat_input_frame")
        self.assertEqual(tree["dispatch"]["frames_per_accepted_request"], 8)


class KnownWiringGapTests(unittest.TestCase):
    """The wiring rungs, and the coupling that makes them move together.

    NPC-HP-LINK-003 closed the two gaps this class used to pin open:

    1.  ``app.py`` NOW hands ``make_state_class`` the lane's keyword, exactly
        as every sibling lane does, so the CLI flag reaches the runtime branch
        and an attended test against this lane is a live test rather than a
        dead one.

    2.  ``scenarios/npc_hp_link_hypothesis_target_sweep.json`` NOW declares
        ``dispatch.wired == true``, the wiring owner ``npc_hp_link_002_round_
        111`` and a ``runtime_dispatch_branch`` that names the real method.

    WHAT DID NOT CHANGE, AND MUST NOT: the scenario tree cannot be edited
    alone.  ``npc_hp_link_hypothesis._expected_scenario()`` pins the whole tree
    by EXACT equality and ``tools/verify_npc_hp_link_encoder.py`` pins the
    wiring owner independently, so any future edit to that JSON that the
    composer has not agreed to takes the lane offline with
    ``scenario_file_exceeds_allowlist``.  That coupling is a FEATURE -- it is
    what stops a scenario file from claiming wiring the code does not have,
    which is precisely the drift that produced the stale block these tests used
    to pin.  Only the pinned VALUES moved; the coupling is measured below,
    against the corrected file, in both directions.
    """

    def test_app_now_hands_make_state_class_the_keyword(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "npc_hp_link_hypothesis_scenario=npc_hp_link_hypothesis", source)
        self.assertNotIn(
            "NPC-HP-LINK-001 is DELIBERATELY ABSENT from this call", source)
        self.assertIn("NPC-HP-LINK-003 joins the flag to the branch", source)

    def test_the_scenario_files_dispatch_block_now_describes_real_wiring(self):
        tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        runtime_source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIs(tree["dispatch"]["wired"], True)
        self.assertEqual(
            tree["dispatch"]["runtime_dispatch_branch"],
            "runtime_py_dispatch_npc_hp_link_hypothesis_reached_from_the_app_"
            "flag_through_make_state_class")
        self.assertIn(
            "def _dispatch_npc_hp_link_hypothesis(", runtime_source)
        self.assertEqual(
            tree["dispatch"]["wiring_owner"], nh.NPC_HP_LINK_WIRING_OWNER)
        self.assertEqual(
            nh.NPC_HP_LINK_WIRING_OWNER, "npc_hp_link_002_round_111")
        self.assertNotIn(
            "no_runtime_dispatch_branch_this_checkpoint_wires_only_the_app_"
            "flag", tree["nonclaims"])
        self.assertIn(
            "the_runtime_dispatch_branch_exists_and_is_driven_headless_only_"
            "never_over_tcp_and_never_by_a_client", tree["nonclaims"])

    def test_the_composer_is_what_pins_that_block_so_it_cannot_be_edited_alone(self):
        """The coupling itself, measured -- not a promise about it.

        The file on disk loads.  Any of the three dispatch values moved on its
        own -- including moving one of them BACK to what NPC-HP-LINK-001 said
        -- is refused by the composer, so the JSON can never drift away from
        the code that pins it in either direction.
        """
        self.assertIsNotNone(
            nh.load_npc_hp_link_hypothesis_scenario(str(SCENARIO_PATH)))
        good = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        mutations = (
            ("wired", False),
            ("wiring_owner", "npc_hp_link_001_round_111"),
            ("runtime_dispatch_branch",
             "not_wired_this_checkpoint_the_app_flag_is_wired_and_the_runtime"
             "_branch_is_a_separate_checkpoint"),
            ("runtime_dispatch_branch",
             "runtime.py::_dispatch_npc_hp_link_hypothesis"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for number, (key, value) in enumerate(mutations):
                with self.subTest(key=key, value=value):
                    tree = json.loads(json.dumps(good))
                    tree["dispatch"][key] = value
                    edited = Path(tmp) / ("edited%d.json" % number)
                    edited.write_text(json.dumps(tree), encoding="utf-8")
                    with self.assertRaises(
                            nh.NpcHpLinkValidationError) as raised:
                        nh.load_npc_hp_link_hypothesis_scenario(str(edited))
                    self.assertIn(
                        "scenario_file_exceeds_allowlist", str(raised.exception))
            # The nonclaim list is pinned by the same exact-equality tree: the
            # reworded nonclaim cannot be reverted alone either.
            tree = json.loads(json.dumps(good))
            tree["nonclaims"][11] = (
                "no_runtime_dispatch_branch_this_checkpoint_wires_only_the_"
                "app_flag")
            edited = Path(tmp) / "edited_nonclaim.json"
            edited.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaises(nh.NpcHpLinkValidationError) as raised:
                nh.load_npc_hp_link_hypothesis_scenario(str(edited))
        self.assertIn("scenario_file_exceeds_allowlist", str(raised.exception))


class ToolTests(unittest.TestCase):
    def test_the_offline_verifier_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(VERIFY_TOOL)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)
        self.assertNotIn("FAIL", result.stdout)

    def test_the_headless_replay_runs_clean_and_needs_no_database(self):
        result = subprocess.run(
            [sys.executable, str(REPLAY_TOOL)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)

    def test_the_headless_replay_refuses_a_db_flag_in_pure_ascii(self):
        result = subprocess.run(
            [sys.executable, str(REPLAY_TOOL), "--db", "anything"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("takes no --db", result.stdout)
        self.assertTrue(all(ord(ch) < 0x80 for ch in result.stdout))

    def test_the_headless_replay_emits_machine_readable_json(self):
        result = subprocess.run(
            [sys.executable, str(REPLAY_TOOL), "--json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["result"], "PASS")
        self.assertEqual(verdict["hypothesis_id"], "HYP-PF-029")
        self.assertEqual(verdict["milestone"], "NPC-HP-LINK-001")
        self.assertIs(verdict["dispatcher_driven"], False)
        self.assertEqual(len(verdict["frames"]), 8)
        self.assertEqual(
            verdict["walked_balance_ladder"], [100, 100, 37, 37, 37, 37, 0, 0])

    def test_both_tool_sources_are_pure_ascii(self):
        for tool in (VERIFY_TOOL, REPLAY_TOOL):
            with self.subTest(tool=tool.name):
                self.assertTrue(
                    all(byte < 0x80 for byte in tool.read_bytes()))

    def test_the_tools_need_no_third_party_package(self):
        for tool in (VERIFY_TOOL, REPLAY_TOOL):
            text = tool.read_text(encoding="utf-8")
            with self.subTest(tool=tool.name):
                for banned in ("import numpy", "import requests",
                               "import pytest", "import yaml"):
                    self.assertNotIn(banned, text)


class ContainmentTests(unittest.TestCase):
    def test_the_lane_opens_no_write_path_of_any_kind(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        for banned in ("sqlite3", "INSERT", "UPDATE ", "SQLiteStore",
                       "store.", "commit("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, text)

    def test_the_lane_takes_no_socket_action(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        for banned in ("import socket", "sendall", "shutdown(", "close()"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, text)
        tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(tree["dispatch"]["socket_action"], "none")
        self.assertEqual(
            tree["persisted_post_state"]["database_write"], "none")

    def test_no_path_in_this_suite_names_the_canonical_database(self):
        text = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("pirateforce" + ".sqlite3", text)

    def test_the_canonical_database_has_not_moved_since_this_module_loaded(self):
        self.assertEqual(_canonical_stat(), _CANONICAL_AT_IMPORT)


# ===========================================================================
# NPC-HP-LINK-002.  The runtime branch, driven for real on a throwaway
# database: no server process, no socket, no client.
# ===========================================================================
SWEEP_EVENT = "npc_hp_link_hypothesis_target_sweep_sent"
REPEAT_EVENT = "npc_hp_link_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "npc_hp_link_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "npc_hp_link_hypothesis_wrong_sequence_no_reply"
EVENT_PREFIX = "npc_hp_link_hypothesis_"

EXPECTED_STEP_ORDER = (
    "TARGET_SPAWN", "HIT_WEAK", "TARGET_HP_AFTER_WEAK", "MISS",
    "TARGET_HP_AFTER_MISS", "HIT_STRONG", "TARGET_HP_ZERO_DYING",
    "TARGET_DYING_ELAPSED",
)
EXPECTED_KINDS = (
    "actor", "hit", "actor", "hit", "actor", "hit", "actor", "actor",
)
EXPECTED_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
EXPECTED_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}
EXPECTED_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
EXPECTED_TIMERS = {"TARGET_HP_ZERO_DYING": 20.0, "TARGET_DYING_ELAPSED": 0.0}
EXPECTED_DELAYS = tuple([0.0] + [6.0] * 7)
TARGET_IDENTITY = 0x2001

# Every other sweep counter and event prefix reachable from a connection.
# None of them may move while this lane runs, and none of their events may
# appear -- the shared dispatch selector is the thing being guarded.
FOREIGN_COUNTERS = (
    "chat_input_echo_count", "channel_message_sweep_count",
    "stats_progression_sweep_count", "hp_death_sweep_count",
    "runtimeres_death_sweep_count", "damage_model_sweep_count",
    "damage_hp_link_sweep_count", "remote_player_sweep_count",
    "npc_hostile_sweep_count",
)
FOREIGN_PREFIXES = (
    "chat_input_hypothesis_", "channel_message_hypothesis_",
    "stats_progression_hypothesis_", "hp_death_hypothesis_",
    "runtimeres_death_hypothesis_", "damage_model_hypothesis_",
    "damage_hp_link_hypothesis_", "remote_player_hypothesis_",
    "npc_hostile_hypothesis_",
)


class NpcHpLinkDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)
        self.db_path = self.tmp_dir / "state.sqlite3"
        # Round 41, enforced on every single test: this file's database lives
        # under the system temporary directory and nowhere near the repository.
        self.assertIn(
            Path(tempfile.gettempdir()).resolve(),
            self.db_path.resolve().parents,
        )
        self.assertNotIn(ROOT.resolve(), self.db_path.resolve().parents)
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = nh.load_npc_hp_link_hypothesis_scenario(SCENARIO_PATH)
        self.unlock = nh.npc_hp_link_wire_unlock(self.scenario)
        self.target = nh.resolve_npc_hp_link_target(self.legacy)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ---------------------------------------------------------

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            npc_hp_link_hypothesis_scenario=(self.scenario if sweep else None),
        )

    def _state(self, login, *, sweep=True, ready=True, select=True):
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _payload(self, probe="probe1"):
        return self._trigger(probe).nested_payload

    def _trigger_pc(self, payload, *, vital_id=CHAT_INPUT_VITAL_ID,
                    outer_version=0, nested_version=0):
        legacy = self.legacy
        return bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, vital_id)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _expected(self, state):
        """The encoder's composition, built without the dispatcher."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        return nh.build_npc_hp_link_sweep(
            self.legacy, self.target,
            selected.identity_lo, selected.identity_hi,
            self.unlock, self.scenario,
        )

    def _db_digest(self):
        """The whole database directory, because the store runs in WAL mode."""
        rows = []
        for name in sorted(os.listdir(self.tmp_dir)):
            path = self.tmp_dir / name
            if path.is_file():
                data = path.read_bytes()
                rows.append((name, len(data), hashlib.sha256(data).hexdigest()))
        return rows

    def _table_row_counts(self):
        connection = sqlite3.connect(str(self.db_path))
        try:
            tables = [
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "ORDER BY name"
                )
            ]
            return {
                table: connection.execute(
                    'SELECT COUNT(*) FROM "%s"' % table
                ).fetchone()[0]
                for table in tables
            }
        finally:
            connection.close()

    def _decoded(self, pc):
        return nh.decode_npc_hp_link_frame(pc)

    # ----- happy path ------------------------------------------------------

    def test_one_request_sweeps_the_eight_steps_in_the_pinned_order(self):
        state = self._state("nhl01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 8)
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(nh.NPC_HP_LINK_ACTION_LABELS),
        )
        self.assertEqual(
            list(nh.NPC_HP_LINK_STEP_ORDER), list(EXPECTED_STEP_ORDER))
        # The scenario file's own label list is the same list.
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.npc_hp_link_sweep_count, 1)

    def test_the_dispatched_bytes_are_the_encoders_bytes(self):
        """The dispatcher forwards; it does not compose a sweep of its own."""
        state = self._state("nhl02")
        expected = self._expected(state)
        self.assertEqual(state.dispatch(self._trigger()), expected)

    def test_every_dispatched_frame_reproduces_its_module_and_scenario_pins(self):
        """The pinned BYTES, not merely the pinned shape."""
        state = self._state("nhl03")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 8)
        for index, (_label, pc, frame, _delay) in enumerate(actions):
            step = EXPECTED_STEP_ORDER[index]
            pin = nh.NPC_HP_LINK_PINS[step]
            scenario_pin = self.pinned["probe"]["per_step"][step]
            with self.subTest(step=step):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(len(frame), pin["frame_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"])
                # The module pin and the scenario file pin must be the SAME pin.
                self.assertEqual(scenario_pin["pc_sha256"], pin["pc_sha256"])
                self.assertEqual(
                    scenario_pin["frame_sha256"], pin["frame_sha256"])
                self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_sweep_alternates_the_two_carriers_of_one_envelope(self):
        state = self._state("nhl04")
        actions = state.dispatch(self._trigger())
        for index, (_label, pc, _frame, _delay) in enumerate(actions):
            decoded = self._decoded(pc)
            with self.subTest(step=EXPECTED_STEP_ORDER[index]):
                self.assertEqual(decoded["kind"], EXPECTED_KINDS[index])
        self.assertEqual(
            [self._decoded(pc)["kind"] for _l, pc, _f, _d in actions],
            list(EXPECTED_KINDS),
        )
        self.assertEqual(
            self.pinned["dispatch"]["step_kinds"], list(EXPECTED_KINDS))

    def test_the_hit_frames_carry_the_pinned_damage_and_flag_pairs(self):
        state = self._state("nhl05")
        actions = state.dispatch(self._trigger())
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "hit":
                continue
            decoded = self._decoded(actions[index][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["damage_wire"], EXPECTED_DAMAGE[step])
                self.assertEqual(decoded["flags"], EXPECTED_FLAGS[step])
                self.assertEqual(decoded["target_identity"], TARGET_IDENTITY)

    def _basic_fields(self, pc):
        """The BasicAttr field map of the one NPCAttr in an actor-entry frame."""
        attrs = self._decoded(pc)["attrs"]
        bodies = [
            body for body in attrs.values()
            if isinstance(body, dict) and "fields" in body
        ]
        self.assertEqual(len(bodies), 1, attrs)
        return bodies[0]

    def test_the_target_frames_carry_the_server_held_ladder(self):
        """The whole point of the lane: the TARGET's bar shows what it cost."""
        state = self._state("nhl06")
        actions = state.dispatch(self._trigger())
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "actor":
                continue
            body = self._basic_fields(actions[index][1])
            fields = body["fields"]
            with self.subTest(step=step):
                self.assertEqual(body["identity"], TARGET_IDENTITY)
                self.assertEqual(
                    fields[nh.BASIC_BIT_CURRENT_HP],
                    EXPECTED_LADDER[index],
                )
                self.assertEqual(
                    fields[nh.BASIC_BIT_MAX_HP], nh.NPC_HP_LINK_HP_MAX)
                self.assertEqual(
                    fields.get(nh.BASIC_BIT_DEATH_TIMER),
                    EXPECTED_TIMERS.get(step),
                )
        self.assertEqual(
            list(nh.NPC_HP_LINK_BALANCE_LADDER), list(EXPECTED_LADDER))

    def test_the_two_post_miss_target_frames_are_byte_identical(self):
        """A miss moves nothing, and the frame says so by repeating itself."""
        state = self._state("nhl07")
        actions = state.dispatch(self._trigger())
        after_weak = EXPECTED_STEP_ORDER.index("TARGET_HP_AFTER_WEAK")
        after_miss = EXPECTED_STEP_ORDER.index("TARGET_HP_AFTER_MISS")
        self.assertEqual(actions[after_weak][1], actions[after_miss][1])
        self.assertEqual(actions[after_weak][2], actions[after_miss][2])

    def test_every_frame_of_the_sweep_is_about_the_one_frozen_target(self):
        state = self._state("nhl08")
        self.assertEqual(self.target.actor_identity, TARGET_IDENTITY)
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 8)
        for index, (_label, pc, _frame, _delay) in enumerate(actions):
            decoded = self._decoded(pc)
            with self.subTest(step=EXPECTED_STEP_ORDER[index]):
                # Both carriers name the same actor: the hit entry's target
                # and the actor entry's identity are the one frozen 0x2001.
                self.assertEqual(decoded["target_identity"], TARGET_IDENTITY)
                if decoded["kind"] == "actor":
                    self.assertEqual(
                        self._basic_fields(pc)["identity"], TARGET_IDENTITY)

    def test_the_performer_of_every_hit_frame_is_the_selected_character(self):
        state = self._state("nhl09")
        selected = state.foundation.selected
        identity = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )
        self.assertNotEqual(identity, TARGET_IDENTITY)
        for _label, pc, _frame, _delay in state.dispatch(self._trigger()):
            decoded = self._decoded(pc)
            if decoded["kind"] == "hit":
                self.assertEqual(decoded["performer_identity"], identity)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("nhl10")
        delays = [d for _l, _p, _f, d in state.dispatch(self._trigger())]
        self.assertEqual(delays, list(EXPECTED_DELAYS))
        self.assertEqual(nh.NPC_HP_LINK_SPACING_SECONDS, 6.0)
        self.assertEqual(nh.NPC_HP_LINK_FIRST_DELAY_SECONDS, 0.0)

    def test_the_sweep_takes_no_socket_action_and_writes_nothing(self):
        state = self._state("nhl11")
        before = self._db_digest()
        counts_before = self._table_row_counts()
        # The comparison must have teeth: the harness already wrote an
        # account, a session and a character.
        self.assertTrue(any(count > 0 for count in counts_before.values()))
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 8)
        self.assertTrue(all(len(action) == 4 for action in actions))
        self.assertEqual(self._db_digest(), before)
        self.assertEqual(self._table_row_counts(), counts_before)
        self.assertEqual(
            self.pinned["dispatch"]["socket_action"], "none")

    # ----- one-shot --------------------------------------------------------

    def test_the_sweep_is_one_shot(self):
        """A repeat trigger emits nothing at all, and says so by name."""
        state = self._state("nhl12")
        self.assertEqual(len(state.dispatch(self._trigger())), 8)
        before = self._db_digest()
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.dispatch(self._trigger("probe2")), [])
        self.assertEqual(state.npc_hp_link_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)
        self.assertEqual(state.events.count(REPEAT_EVENT), 2)
        self.assertEqual(self._db_digest(), before)

    def test_the_one_shot_is_per_connection_not_per_process(self):
        """Two connections each get their own sweep and their own counter."""
        first = self._state("nhl13")
        self.assertEqual(len(first.dispatch(self._trigger())), 8)
        self.assertEqual(first.dispatch(self._trigger()), [])
        second = self._state("nhl14")
        self.assertEqual(second.npc_hp_link_sweep_count, 0)
        self.assertEqual(len(second.dispatch(self._trigger())), 8)
        self.assertEqual(second.npc_hp_link_sweep_count, 1)

    # ----- fail closed -----------------------------------------------------

    def _refused(self, state, parsed, event_name):
        before = self._db_digest()
        counts_before = self._table_row_counts()
        self.assertEqual(state.dispatch(parsed), [])
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.events.count(event_name), 1, state.events)
        self.assertEqual(state.npc_hp_link_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)
        self.assertEqual(self._table_row_counts(), counts_before)

    def test_no_selected_character_fails_closed(self):
        self._refused(
            self._state("nhl15", select=False), self._trigger(),
            NO_SELECTED_EVENT,
        )

    def test_not_yet_teleport_and_runtime_ack_fails_closed(self):
        self._refused(
            self._state("nhl16", ready=False), self._trigger(),
            WRONG_SEQUENCE_EVENT,
        )

    def test_wrong_length_fails_closed(self):
        self._refused(
            self._state("nhl17"),
            self.legacy.parse_outer(self._trigger_pc(self._payload()[:-1])),
            EVENT_PREFIX + "wrong_length_no_reply",
        )

    def test_wrong_prefix_fails_closed(self):
        payload = bytearray(self._payload())
        payload[0] ^= 0xFF
        self._refused(
            self._state("nhl18"),
            self.legacy.parse_outer(self._trigger_pc(bytes(payload))),
            EVENT_PREFIX + "wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self._refused(
            self._state("nhl19"), self.legacy.parse_outer(bytes(pc)),
            EVENT_PREFIX + "wrong_text_no_reply",
        )

    def test_wrong_envelope_fails_closed(self):
        for index, kwargs in enumerate(
            ({"outer_version": 1}, {"nested_version": 1}),
        ):
            with self.subTest(**kwargs):
                self._refused(
                    self._state("nhl20_%d" % index),
                    self.legacy.parse_outer(
                        self._trigger_pc(self._payload(), **kwargs)
                    ),
                    EVENT_PREFIX + "wrong_envelope_no_reply",
                )

    def test_no_refusal_path_ever_emits_a_frame(self):
        cases = (
            ("nhl21", {"select": False}, self._trigger()),
            ("nhl22", {"ready": False}, self._trigger()),
            ("nhl23", {}, self.legacy.parse_outer(
                self._trigger_pc(self._payload()[:-1])
            )),
            ("nhl24", {}, self.legacy.parse_outer(
                self._trigger_pc(self._payload(), outer_version=1)
            )),
        )
        for login, kwargs, parsed in cases:
            with self.subTest(login=login):
                state = self._state(login, **kwargs)
                self.assertEqual(state.dispatch(parsed), [])
                self.assertEqual(state.npc_hp_link_sweep_count, 0)
                self.assertNotIn(SWEEP_EVENT, state.events)

    def test_a_refusal_does_not_burn_the_one_shot(self):
        """A refusal is not a send: once the session is ready, it still fires
        exactly once."""
        state = self._state("nhl25", ready=False)
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.events.count(WRONG_SEQUENCE_EVENT), 1)
        self.assertEqual(state.npc_hp_link_sweep_count, 0)
        state.runtime_ack_sent = True
        self.assertEqual(len(state.dispatch(self._trigger())), 8)
        self.assertEqual(state.npc_hp_link_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)

    def test_the_branch_answers_no_vital_id_other_than_the_chat_input_one(self):
        state = self._state("nhl26")
        actions = state.dispatch(self.legacy.parse_outer(
            self._trigger_pc(self._payload(), vital_id=0xBEEF)
        ))
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(nh.NPC_HP_LINK_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.npc_hp_link_sweep_count, 0)

    # ----- the scenario gate ------------------------------------------------

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for candidate in (
            object(),
            nh.NPC_HP_LINK_SCENARIO_ID,
            nh.NpcHpLinkHypothesisScenario(
                nh.NPC_HP_LINK_SCENARIO_ID,
                nh.NPC_HP_LINK_HYPOTHESIS_ID,
                tuple(reversed(nh.NPC_HP_LINK_STEP_ORDER)),
                nh.NPC_HP_LINK_SPACING_SECONDS,
                nh.NPC_HP_LINK_FIRST_DELAY_SECONDS,
                nh.NPC_HP_LINK_ACTION_LABEL_PREFIX,
            ),
        ):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(nh.NpcHpLinkValidationError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        npc_hp_link_hypothesis_scenario=candidate,
                    )
                self.assertIn(
                    "scenario_object_exceeds_allowlist", str(raised.exception))
                self.assertIsInstance(raised.exception, ValueError)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode_at_runtime(self):
        """make_state_class refuses the pair, not merely app.py's flags."""
        from pirateforce_foundation import (  # noqa: E402
            damage_hp_link_hypothesis as hpl,
            damage_model_hypothesis as dmh,
            npc_hostile_hypothesis as nho,
            remote_player_hypothesis as rph,
            runtimeres_death_hypothesis as rdh,
        )
        pairs = {
            "damage_hp_link_hypothesis_scenario": (
                hpl.load_damage_hp_link_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "damage_hp_link_hypothesis_link_sweep.json"
                )
            ),
            "damage_model_hypothesis_scenario": (
                dmh.load_damage_model_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "damage_model_hypothesis_npc_sweep.json"
                )
            ),
            "runtimeres_death_hypothesis_scenario": (
                rdh.load_runtimeres_death_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "runtimeres_death_hypothesis_spawn_then_kill.json"
                )
            ),
            "remote_player_hypothesis_scenario": (
                rph.load_remote_player_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "remote_player_hypothesis_visibility_probe.json"
                )
            ),
            "npc_hostile_hypothesis_scenario": (
                nho.load_npc_hostile_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "npc_hostile_hypothesis_faction_pairing.json"
                )
            ),
        }
        for kwarg, other in pairs.items():
            with self.subTest(other=kwarg):
                with self.assertRaises(ValueError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        npc_hp_link_hypothesis_scenario=self.scenario,
                        **{kwarg: other},
                    )
                self.assertIn("mutually exclusive", str(raised.exception))

    # ----- containment against the other lanes -----------------------------

    def test_no_other_chat_keyed_lane_is_reachable_while_this_one_runs(self):
        state = self._state("nhl27")
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [label for label, _pc, _f, _d in actions],
            list(nh.NPC_HP_LINK_ACTION_LABELS),
        )
        for counter in FOREIGN_COUNTERS:
            with self.subTest(counter=counter):
                self.assertEqual(getattr(state, counter), 0)
        for event in state.events:
            self.assertFalse(event.startswith(FOREIGN_PREFIXES), event)

    def test_the_foreign_counters_stay_zero_across_a_refusal_too(self):
        state = self._state("nhl28", ready=False)
        self.assertEqual(state.dispatch(self._trigger()), [])
        for counter in FOREIGN_COUNTERS:
            with self.subTest(counter=counter):
                self.assertEqual(getattr(state, counter), 0)
        for event in state.events:
            self.assertFalse(event.startswith(FOREIGN_PREFIXES), event)

    # ----- the lane off ----------------------------------------------------

    def test_trap_the_lane_composes_nothing_when_its_scenario_is_absent(self):
        """TRAP -- the failure mode: a branch that forgets its scenario gate.

        Two independent locks, because one of them is the kind a careless edit
        removes.  (a) with no scenario the trigger keeps its frozen baseline
        answer: no HYP-PF-029 action label, no lane event, and none of the
        sweep's bytes.  (b) even if a future edit reached the dispatch method
        WITHOUT the gate, it still cannot emit anything: the unlock, the target
        and the scenario profile are closed over as ``None``, so the composer
        raises instead of putting a frame on the wire.
        """
        state = self._state("nhl29", sweep=False)
        reference = self._state("nhl30")
        expected_pcs = {pc for _l, pc, _f, _d in self._expected(reference)}

        before = self._db_digest()
        actions = state.dispatch(self._trigger())
        self.assertFalse([
            label for label, _p, _f, _d in actions
            if label.startswith(nh.NPC_HP_LINK_ACTION_LABEL_PREFIX)
        ])
        self.assertFalse({pc for _l, pc, _f, _d in actions} & expected_pcs)
        self.assertFalse(
            [event for event in state.events if event.startswith(EVENT_PREFIX)]
        )
        self.assertEqual(state.npc_hp_link_sweep_count, 0)
        self.assertEqual(self._db_digest(), before)
        # (b) the second lock: the closed-over None cannot compose.
        with self.assertRaises(nh.NpcHpLinkValidationError):
            state._dispatch_npc_hp_link_hypothesis(self._trigger())

    def test_the_state_class_still_carries_the_counter_when_the_lane_is_off(self):
        """The counter is a per-connection field, not a scenario artefact."""
        state = self._state("nhl31", sweep=False)
        self.assertEqual(state.npc_hp_link_sweep_count, 0)

    def test_the_canonical_database_has_not_moved(self):
        self.assertEqual(_canonical_stat(), _CANONICAL_AT_IMPORT)


if __name__ == "__main__":
    unittest.main()
