"""The relog half of `/warp 126`, ordered by `COO-DECISION 20260905_1746` item 4.

WHAT IS BEING PINNED.  A live `/warp` writes `character_positions` in the same
breath as the TeleportVital (`PANYA 20260904_1430`).  Scene 126's login door is
shut by `COO-DECISION 20260829_1444`, so that write is refused --
`warp_scene_persist` answers `login_would_refuse` and leaves the row alone,
which is correct and stays correct.  The relog therefore travels the other
road: the single-use login entry of `CORE-REQUEST-GM-038`, written at the
moment the warp goes out.

So the property under test is a DISAGREEMENT held on purpose: for scene 126 the
durable row and the next login answer differently, and every other scene keeps
one answer for both.

THE TWO CONSOLE LINES `1746` ITEM 4 ASKS FOR, both pinned below:
    GM_WARP_SCENE_PERSIST_FAILED scene=126 reason=login_would_refuse
    GM_WARP_RELOG_ENTRY_STAGED   scene=126 previous=none single_use=1

NONCLAIM -- GM USE, AND WHAT IT SKIPS.  Everything here is headless and
server-side.  A staged entry is an INSTRUCTION about the next login, not
evidence that the next login honours it; `GT-266`'s second criterion (close
the client, log back in, still in Rising Sun Sea) is the measurement and only
a person at the client can make it.  The GM road is used to reach scene 126 at
all -- an ordinary player has no route to it, which is the whole reason its
login door is shut -- so nothing in this file is evidence that scene 126 is
reachable by play, and no milestone may be read off it.  No account gains GM
status anywhere below: `warp_relog_stage` never writes `gm_accounts`, and the
non-GM case is pinned as a refusal.  `production_allowed` is never consulted by
the path under test, by this lane's charter rule 1.
"""
from __future__ import annotations

import ast
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import MappingProxyType
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command_action,
    dispatch as gm_dispatch,
    login_scene_admission,
    login_scene_override,
    login_scene_stage,
    warp_relog_stage,
    warp_scene_persist,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_bent_scene_registry as bent  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: ~~The scene the chief letter sanctions and the login path still bars.~~
#: NO SCENE IS SANCTIONED ON MAIN SINCE LANE-GM ROUND `xbfcsi` (2026-09-09,
#: `COO-DECISION 20260908_2141`): the map is empty.  126 is now the scene the
#: cases below STAND A SANCTION UP for, through `_install_a_sanction`, because
#: the road this module owns is only walkable for a sanctioned scene and the
#: rules on it (which refusal, in which order, printed or silent) are the
#: module's, not scene 126's.  What the retirement actually did to this road
#: on main is pinned by `test_retiring_the_sanction_is_loud_and_not_silent`
#: and `TheRetirementClosedThisRoadTests`, which read the real map.
SANCTIONED_SCENE = 126

#: The citation the retired row carried.  Only ever a console string.
SANCTION_CITATION = "CHIEF-DECISION 20260829_1603 item 2"


def _install_a_sanction(test, *, scene_id=SANCTIONED_SCENE):
    """Name one scene in the sanction map for the duration of one test.

    Without it every case that walks this road stops at the first gate
    (`scene_not_sanctioned`) and passes without reaching the rule it is
    named for -- a green that no change in `warp_relog_stage` can turn red.
    """
    patcher = mock.patch.object(
        login_scene_admission,
        "SANCTIONED_BARRED_SCENES",
        MappingProxyType({scene_id: SANCTION_CITATION}),
    )
    patcher.start()
    test.addCleanup(patcher.stop)

#: Marker-backed and login-allowed: the ordinary road, where the durable row
#: moves and no relog entry is written or wanted.
ORDINARY_SCENE = 2

#: Barred at login like 126, but named by no chief letter.  The refusal it
#: always had must survive this round untouched -- this is the "126 is the only
#: scene on this route" half of `1746` item 4.
BARRED_BUT_UNSANCTIONED_SCENE = 17


def _legacy():
    return load_legacy(LEGACY_PATH)


class _Session:
    """The same minimal session shape the sibling warp tests drive."""

    def __init__(self, foundation):
        self.foundation = foundation
        self.events = []


class TheMapDecidesNotAConstantTests(unittest.TestCase):
    """`warp_relog_stage` follows the chief-letter map, not a hard-coded 126.

    If a future letter sanctions a second scene, the route follows it.  Until
    then this pins the reading `1746` item 4 rests on -- exactly one scene
    takes this road today -- so widening it is a decision somebody makes on
    purpose rather than a surprise in a diff.
    """

    def test_no_scene_is_sanctioned_today_so_this_road_is_closed(self):
        # ~~`test_exactly_one_scene_is_sanctioned_today_and_it_is_126`~~ --
        # 126's sanction was retired in LANE-GM round `xbfcsi`
        # (`COO-DECISION 20260908_2141`), so the pin turns over with it: the
        # map is empty, and this road therefore opens for NOBODY on main
        # today.  The claim is the same one it always was -- widening this
        # route is a decision somebody makes on purpose, visible in a diff
        # here -- and it still goes red if any id appears in the map without
        # this file being read.
        self.assertEqual(
            (), tuple(login_scene_admission.SANCTIONED_BARRED_SCENES),
        )

    def test_the_module_carries_no_scene_id_literal_of_its_own(self):
        """The guard is the map lookup, not a literal.

        Parsed rather than grepped: prose in this module's own comments says
        `126` a dozen times, and a text search would either pass on the
        comments or fail on them.  What matters is whether any scene id is
        baked into the CODE, so the question is asked of the syntax tree.
        """
        tree = ast.parse(
            Path(warp_relog_stage.__file__).read_text(encoding="utf-8")
        )
        numbers = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        }
        self.assertEqual(set(), numbers)

    def test_the_route_follows_the_map_when_the_map_changes(self):
        """Behavioural half of the same claim: sanction another scene and the
        route opens for it, with no edit here.

        The stage itself still refuses (17 has no route beyond the sanction),
        which is the correct second answer -- what is pinned is that the
        REFUSAL MOVED, from `scene_not_sanctioned` to the stage's own word.
        """
        with mock.patch.object(
            login_scene_admission,
            "SANCTIONED_BARRED_SCENES",
            {BARRED_BUT_UNSANCTIONED_SCENE: "a letter that does not exist"},
        ):
            stream = io.StringIO()
            with redirect_stderr(stream):
                word = (
                    warp_relog_stage
                    .stage_relog_entry_after_refused_persist(
                        warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                        BARRED_BUT_UNSANCTIONED_SCENE,
                        "RELOGGM",
                    ).outcome
                )
        self.assertNotEqual(
            warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word,
        )
        self.assertTrue(
            word.startswith(warp_relog_stage.OUTCOME_STAGE_REFUSED_PREFIX),
            word,
        )


class TheRetirementClosedThisRoadTests(unittest.TestCase):
    """What the retirement did to THIS road, read off the shipped map.

    No fixture and no patch: every other class here stands a sanction up to
    keep its rules reachable, and this one is the counterweight that says
    what an operator actually gets on main today.  `PANYA 1430` (still there
    after a relog) is off for scene 126 until lane A's login row lands, and
    the console says so rather than swallowing it -- which is the whole
    reason `COO-DECISION 20260908_2141` could take that cost.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["RELOGGM"]}), encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"

    def test_warp_126_is_no_longer_staged_and_the_console_announces_it(self):
        stream = io.StringIO()
        with redirect_stderr(stream):
            word = warp_relog_stage.stage_relog_entry_after_refused_persist(
                warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                SANCTIONED_SCENE,
                "RELOGGM",
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
            ).outcome
        printed = stream.getvalue()
        self.assertEqual(warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word)
        self.assertIn(warp_relog_stage.FAIL_CONSOLE_TOKEN, printed)
        self.assertIn(f"scene={SANCTIONED_SCENE}", printed)
        self.assertIn(
            f"reason={warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED}", printed,
        )
        # Announced, never written.
        self.assertFalse(self.config_path.exists())

    def test_the_line_is_printed_because_lane_a_decreed_an_arrival(self):
        # The split this road is built on: the announcement exists for a
        # scene the live warp really moved a character into.  If lane A's
        # decreed arrival for 126 ever goes away, the case above would be
        # pinning a silence instead, and this says so first.
        self.assertTrue(
            login_scene_admission.scene_has_decreed_arrival(SANCTIONED_SCENE)
        )


class TheRouteOpensOnlyForTheRefusedSanctionedCaseTests(unittest.TestCase):
    """Every non-126 shape returns before anything is written or printed."""

    def setUp(self):
        _install_a_sanction(self)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["RELOGGM"]}), encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"

    def _call(self, outcome, scene_id, account="RELOGGM"):
        stream = io.StringIO()
        with redirect_stderr(stream):
            word = warp_relog_stage.stage_relog_entry_after_refused_persist(
                outcome,
                scene_id,
                account,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
            )
        return word.outcome, stream.getvalue()

    def test_a_persisted_warp_stages_nothing_and_says_nothing(self):
        """The row already answers the next login.  A second answer here is
        the two-sources-of-truth defect this branch is shaped to prevent."""
        word, printed = self._call(
            warp_scene_persist.OUTCOME_PERSISTED, ORDINARY_SCENE,
        )
        self.assertEqual(warp_relog_stage.OUTCOME_NOT_A_REFUSED_LOGIN, word)
        self.assertEqual("", printed)
        self.assertFalse(self.config_path.exists())

    def test_a_refusal_for_some_other_reason_stages_nothing(self):
        """`no_character`, `readback_unavailable` and the rest are not this
        road: they mean the write failed, not that policy refused it."""
        word, printed = self._call(
            warp_scene_persist.OUTCOME_NO_CHARACTER, SANCTIONED_SCENE,
        )
        self.assertEqual(warp_relog_stage.OUTCOME_NOT_A_REFUSED_LOGIN, word)
        self.assertEqual("", printed)
        self.assertFalse(self.config_path.exists())

    def test_a_barred_but_unsanctioned_scene_keeps_the_refusal_it_had(self):
        word, printed = self._call(
            warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
            BARRED_BUT_UNSANCTIONED_SCENE,
        )
        self.assertEqual(warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word)
        # Silent on purpose: this is what every barred scene has always done,
        # and a line here would print on warps that did not change.
        self.assertEqual("", printed)
        self.assertFalse(self.config_path.exists())

    def test_retiring_the_sanction_is_loud_and_not_silent(self):
        """THE RETIREMENT THIS BRANCH USED TO SWALLOW.

        `COO-DECISION 20260908_1742` orders scene 126's sanction retired.
        The hour it is, this function stops staging for 126 -- the live warp
        still moves the character (lane A's row decrees the arrival, so
        `warp_no_coords_live_target` resolves it) and the relog is silently
        not arranged.  A tester warps, sees the new scene, relogs, and is
        back where they started with nothing on the console.

        This case is the map emptied, which is exactly the retirement, and
        it pins that the outcome is now ANNOUNCED.  It does not object to
        the retirement; it makes it visible.
        """
        with mock.patch.object(
            login_scene_admission, "SANCTIONED_BARRED_SCENES", {},
        ):
            word, printed = self._call(
                warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                SANCTIONED_SCENE,
            )
        self.assertEqual(warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word)
        self.assertIn(warp_relog_stage.FAIL_CONSOLE_TOKEN, printed)
        self.assertIn(
            f"reason={warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED}", printed,
        )
        self.assertIn(f"scene={SANCTIONED_SCENE}", printed)
        # Announced, never written: the whole point is that no entry is
        # created for a scene no letter names any more.
        self.assertFalse(self.config_path.exists())

    def test_a_scene_lane_a_never_decreed_stays_silent_when_unsanctioned(self):
        """The other side of the split, so the new line cannot be read as
        'print on every unsanctioned scene'.

        Scene 17 carries no `decreed_arrival` block, so the live route never
        resolved it and no character was moved: there is nothing for a
        console line to warn about, and this is the case the branch has
        always been silent for.
        """
        self.assertFalse(
            login_scene_admission.scene_has_decreed_arrival(
                BARRED_BUT_UNSANCTIONED_SCENE
            )
        )
        with mock.patch.object(
            login_scene_admission, "SANCTIONED_BARRED_SCENES", {},
        ):
            word, printed = self._call(
                warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                BARRED_BUT_UNSANCTIONED_SCENE,
            )
        self.assertEqual(warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word)
        self.assertEqual("", printed)

    def test_true_is_not_scene_one(self):
        """`bool` is an `int` subclass; `True` would otherwise ask about
        scene 1 and could be answered by a map that ever names it."""
        word, _printed = self._call(
            warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE, True,
        )
        self.assertEqual(warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word)
        self.assertFalse(self.config_path.exists())

    def test_a_non_int_scene_id_is_refused_rather_than_raised(self):
        """This runs inside a command whose frame already exists.  An
        exception escaping here would take down a warp that is about to move a
        real screen."""
        for shape in ("126", 126.0, None, object()):
            with self.subTest(shape=shape):
                word, _printed = self._call(
                    warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE, shape,
                )
                self.assertEqual(
                    warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED, word,
                )
        self.assertFalse(self.config_path.exists())


class FailClosedTests(unittest.TestCase):
    """Nobody who is not already a listed GM gets an entry out of this."""

    def setUp(self):
        _install_a_sanction(self)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["RELOGGM"]}), encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"

    def _call(self, account):
        stream = io.StringIO()
        with redirect_stderr(stream):
            word = warp_relog_stage.stage_relog_entry_after_refused_persist(
                warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                SANCTIONED_SCENE,
                account,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
            )
        return word.outcome, stream.getvalue()

    def test_a_player_account_stages_nothing_and_the_console_says_so(self):
        word, printed = self._call("DECKHAND")
        self.assertEqual(
            warp_relog_stage.OUTCOME_STAGE_REFUSED_PREFIX
            + login_scene_stage.REASON_NOT_GM_ACCOUNT,
            word,
        )
        self.assertIn(
            f"{warp_relog_stage.FAIL_CONSOLE_TOKEN} scene={SANCTIONED_SCENE} "
            f"reason={login_scene_stage.REASON_NOT_GM_ACCOUNT}",
            printed,
        )
        # Not an empty entry and not an empty file: no file.
        self.assertFalse(self.config_path.exists())

    def test_a_missing_account_handle_is_loud_not_silent(self):
        """A sanctioned scene with no usable account name is the state a
        tester must never have to infer: row not moved, relog not arranged."""
        for shape in (None, "", 7):
            with self.subTest(shape=shape):
                word, printed = self._call(shape)
                self.assertEqual(
                    warp_relog_stage.OUTCOME_STAGE_REFUSED_PREFIX
                    + "no_account_name",
                    word,
                )
                self.assertIn(
                    warp_relog_stage.FAIL_CONSOLE_TOKEN, printed,
                )
        self.assertFalse(self.config_path.exists())

    def test_staging_adds_nobody_to_the_gm_allowlist(self):
        self._call("RELOGGM")
        self.assertFalse(
            gm_accounts.is_gm_account("DECKHAND", str(self.accounts_path))
        )
        self.assertEqual(
            frozenset({"RELOGGM"}),
            gm_accounts.load_gm_accounts(str(self.accounts_path)),
        )

    def test_the_token_never_lands_on_stdout(self):
        """The `lane_hooks` JSON-artifact incident, guarded here too:
        `tools/pf_runtimeres_death_headless_replay.py --json` writes its
        artifact on stdout, so a token there corrupts it instead of informing
        anyone."""
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch.object(
            warp_relog_stage.sys, "stderr", None
        ):
            warp_relog_stage.stage_relog_entry_after_refused_persist(
                warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE,
                SANCTIONED_SCENE,
                "RELOGGM",
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
            )
        self.assertNotIn(warp_relog_stage.CONSOLE_TOKEN, out.getvalue())
        self.assertNotIn(warp_relog_stage.FAIL_CONSOLE_TOKEN, out.getvalue())


class ThroughTheRealWarpBranchTests(unittest.TestCase):
    """Real store, real lifecycle, real session, the branch a `/warp` takes."""

    def setUp(self):
        _install_a_sanction(self)
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(self.tmp / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(self.tmp / "no_standalone_map.json"),
        })
        env_pin.start()
        self.addCleanup(env_pin.stop)
        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": ["RELOGGM"]}), encoding="utf-8",
        )
        self.config_path = self.tmp / "config" / "gm_login_scene.json"
        self.store = SQLiteStore(
            self.tmp / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.home = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.home,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _session(self, login_name):
        foundation = FoundationSession(self.lifecycle, self.projector, login_name)
        _op, _has_actor, wire = self.legacy.parse_create_actor(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC),
        )
        character, _reply = foundation.create(
            self.legacy.decode_create_actor_data_ex(wire)["name"], wire,
        )
        foundation.select_and_start(character.selector)
        return _Session(foundation)

    def _row(self, session):
        return self.store.get_character(session.foundation.selected.id).position

    def _warp(self, session, scene_id):
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session,
                scene_id,
                self.legacy,
                token="RELOGGM",
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.config_path),
            )
        return verdict, stream.getvalue()

    def _entries(self):
        if not self.config_path.exists():
            return None
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def _shut_the_sanctioned_door(self):
        """Read the registry as it read before 1218 for the sanctioned scene.

        `gm/warp_scene_persist` holds its login reading in a module-level
        snapshot taken once per process, so the loader patch alone would
        leave `login_would_accept` answering from the shipped file; the
        context manager clears that snapshot on the way in and on the way
        out.
        """
        holder = bent.process_reads(bent.shut_at_login(SANCTIONED_SCENE))
        holder.__enter__()
        self.addCleanup(holder.__exit__, None, None, None)
        self.assertFalse(
            warp_scene_persist.login_would_accept(SANCTIONED_SCENE),
            "the bend did not reach the login snapshot, so the row would "
            "move and the disagreement this file measures would be gone",
        )

    def test_warp_126_sends_the_frame_leaves_the_row_and_stages_the_relog(self):
        """`1746` item 4 end to end, and its two console lines."""
        # PANYA-DECISION 20260908_1218 opened scene 126's login door in the
        # SHIPPED registry, and the disagreement this file is named for only
        # exists while that door is shut: the frame goes out, the row is
        # refused, the relog entry is staged.  So the shut door is installed
        # -- the real 126 row, its real spawn, one boolean flipped back to
        # what it read on 2026-09-07 -- and everything else is the real
        # warp branch.
        self._shut_the_sanctioned_door()
        session = self._session("relog01")
        verdict, printed = self._warp(session, SANCTIONED_SCENE)

        # THE LIVE HALF (`PANYA 1329`).  The frame exists; the refusal of the
        # row is not a refusal of the warp.
        self.assertIsNotNone(verdict.action)
        self.assertEqual(
            chat_command_action.OUTCOME_COMPOSED, verdict.audit_outcome,
        )

        # THE ROW IS UNTOUCHED, which is the point: 126's login door stays shut
        # (`COO 20260829_1444`) and nothing here opens it.
        self.assertEqual(1, self._row(session).scene_id)

        # BOTH LINES, in the order a tester reads them.
        self.assertIn(
            f"{warp_scene_persist.FAIL_CONSOLE_TOKEN} "
            f"scene={SANCTIONED_SCENE} "
            f"reason={warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE}",
            printed,
        )
        self.assertIn(
            f"{warp_relog_stage.CONSOLE_TOKEN} scene={SANCTIONED_SCENE} "
            f"previous=none single_use=1",
            printed,
        )
        self.assertLess(
            printed.index(warp_scene_persist.FAIL_CONSOLE_TOKEN),
            printed.index(warp_relog_stage.CONSOLE_TOKEN),
        )

        # THE RELOG HALF (`PANYA 1430`): a single-use entry naming 126 for
        # this one account.
        self.assertIn(
            chat_command_action.EVENT_WARP_RELOG_STAGE_PREFIX
            + warp_relog_stage.OUTCOME_STAGED,
            session.events,
        )
        self.assertIn(
            str(SANCTIONED_SCENE),
            json.dumps(self._entries()),
        )
        self.assertTrue(
            login_scene_override.get_login_scene_override is not None
        )

    def test_an_ordinary_scene_moves_the_row_and_stages_nothing(self):
        """The other 330 scenes are untouched by this round: one answer for
        the row and the next login, and no entry file at all."""
        session = self._session("relog02")
        verdict, printed = self._warp(session, ORDINARY_SCENE)

        self.assertIsNotNone(verdict.action)
        self.assertEqual(ORDINARY_SCENE, self._row(session).scene_id)
        self.assertNotIn(warp_relog_stage.CONSOLE_TOKEN, printed)
        self.assertNotIn(warp_relog_stage.FAIL_CONSOLE_TOKEN, printed)
        self.assertFalse(
            any(
                event.startswith(
                    chat_command_action.EVENT_WARP_RELOG_STAGE_PREFIX
                )
                for event in session.events
            )
        )
        self.assertIsNone(self._entries())

    def test_a_withheld_warp_takes_the_staged_entry_back_with_it(self):
        """The defect this round opened and closed in the same round.

        `_make_action` withholds a composed `/warp` when its `outcome` audit
        row cannot be appended (a full disk, a read-only capture directory)
        and runs `verdict.undo`.  For scene 126 the persist writes nothing, so
        `_persist_warp_scene` offers no undo -- and without the relog's own,
        the entry stayed on disk while ZERO BYTES went out, and the next login
        put the character into 126 off a command that never reached it.  Same
        shape as pf-adversary round `741zlx` finding 1, through the new door.
        """
        self._shut_the_sanctioned_door()  # see the case above
        session = self._session("relog04")
        verdict, _printed = self._warp(session, SANCTIONED_SCENE)

        # The entry is on disk and the verdict carries the handle to remove it.
        self.assertIn(str(SANCTIONED_SCENE), json.dumps(self._entries()))
        self.assertIsNotNone(verdict.undo)

        with redirect_stderr(io.StringIO()):
            self.assertTrue(verdict.undo())

        # Not "an empty entry": no entry for this account naming this scene.
        self.assertNotIn(str(SANCTIONED_SCENE), json.dumps(self._entries()))

    def test_an_ordinary_scene_still_undoes_the_row_not_an_entry(self):
        """The relog undo must not have displaced the persist's own.

        Scene 2 persists, so the verdict's undo is still the ROW rollback --
        wiring the new handle in must not have cost the old one.
        """
        session = self._session("relog05")
        verdict, _printed = self._warp(session, ORDINARY_SCENE)
        self.assertEqual(ORDINARY_SCENE, self._row(session).scene_id)
        self.assertIsNotNone(verdict.undo)
        with redirect_stderr(io.StringIO()):
            self.assertTrue(verdict.undo())
        self.assertEqual(1, self._row(session).scene_id)
        self.assertIsNone(self._entries())

    def test_the_pinning_holds_when_the_fix_is_reverted(self):
        """NOT VACUOUS, and this is how that is shown rather than claimed.

        With the relog call stubbed out the way the pre-round code behaved --
        no entry, no line -- the end-to-end test above must fail.  A test that
        still passes against the reverted code pins nothing, and pf-adversary
        has caught this lane shipping one before.
        """
        session = self._session("relog03")
        with mock.patch.object(
            warp_relog_stage,
            "stage_relog_entry_after_refused_persist",
            return_value=warp_relog_stage.RelogStageResult(
                warp_relog_stage.OUTCOME_SCENE_NOT_SANCTIONED
            ),
        ):
            _verdict, printed = self._warp(session, SANCTIONED_SCENE)
        self.assertNotIn(warp_relog_stage.CONSOLE_TOKEN, printed)
        self.assertIsNone(self._entries())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
