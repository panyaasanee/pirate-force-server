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
readers accept.  MEASURED on `main` as of round `R249` (chief, gate-red
repair of `pirate-force-server#332`): lane A's registry row for 126 landed
(`sanctioned_barred_blocker(126) == login_path_bars_it_needs_core_request_gm_038`),
pinned at `(3050, 232, 90)` and barred at ordinary login -- so the single-use
widening NOW ADMITS scene 126 (`single_use_entry_is_admissible(126)` is
`True`), while the plain login-scene map still refuses it
(`stageable_scene_ids()` does not carry it).  The route this file's tests
guard is therefore live, not "one merge short" -- see
`TheSanctionNowAdmitsViaSingleUseOnlyTests` below.  Most tests in this file
never depended on which world was true: they supply a STAND-IN registry
(`registry_with_sanctioned_row`) so they exercise the SAME question
regardless of what lane A has landed on disk.

NONCLAIM (GM lane rule): every route exercised here is a GM shortcut.  A
tester who reaches scene 126 this way has skipped whatever in-game travel
would normally take them there; seeing the scene is not evidence that the
travel to it works.
"""
from __future__ import annotations

import contextlib
import io
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


def the_only_sanctioned_scene():
    """The id the sanction map names, taken from the map itself, or `None`.

    Not the literal 126: the map is where the chief letters are recorded,
    and a test that hardcodes its contents stops testing the rule the day a
    second letter lands.

    IT RETURNS `None` RATHER THAN RAISING `SkipTest`, and the difference is
    not style (pf-adversary D8, round `znb56z`).  This runs at IMPORT, and
    `login_scene_admission`'s own "HOW AN ENTRY DIES" block MANDATES
    emptying the sanction map the day its scene becomes ordinarily
    reachable -- so an import-time skip here is scheduled, not
    hypothetical.  MEASURED with the map emptied: it turned
    `test_gm_tests_collect_without_posix`'s import probe RED, for a reason
    that has nothing to do with POSIX, and it is not the kind of skip
    `docs/PYTEST_SKIP_PINS.json` can carry (that file requires a positive
    count, i.e. a skip that actually happens, and this one does not happen
    today).  A class-level `skipIf` costs nothing, keeps the module
    importable on every tree, and declares the condition where a reader
    looking at the class can see it.
    """
    ids = sorted(A.SANCTIONED_BARRED_SCENES)
    return ids[0] if ids else None


SANCTIONED = the_only_sanctioned_scene()

# Every test below asks about a sanctioned scene, so all of them are moot
# when no chief letter names one.  Applied per class rather than by raising
# at import: see `the_only_sanctioned_scene`.
requires_a_sanctioned_scene = unittest.skipIf(
    SANCTIONED is None,
    "no scene is sanctioned by any chief letter this lane holds, so the "
    "single-use widening has nothing to admit and nothing to refuse",
)


# The arrival point `CHIEF-DECISION 20260829_1603` item 1 asks lane A to pin
# for the sanctioned scene.  Used by the stand-in below so the fixture is not
# quietly testing HOME's coordinates under scene 126's id -- pf-adversary D9,
# round `znb56z`, which measured that the first version of this fixture
# differed from the row lane A will actually land in every field but three.
SANCTIONED_SPAWN_PER_CHIEF_DECISION = (3050.0, 232.0, 90.0)


def registry_with_sanctioned_row(*, login_entry_allowed=False, spawn=True):
    """Lane A's registry PLUS the row `CHIEF-DECISION 20260829_1603` asks for.

    A stand-in, and it says so: lane A owns that row and has not landed it
    (measured on main this round).  Built by copying a real pinned row so
    every field this lane does not care about is whatever lane A's own
    loader produces, rather than a shape invented here that could pass a
    predicate the real one would fail.

    WHAT THIS FIXTURE STILL IS NOT, stated because pf-adversary asked and
    the first version had no answer (D9).  Three fields are now the ones
    the decision names -- `n_id`, `login_entry_allowed` and the `spawn`
    COORDINATES.  Every other field is still HOME's:
    `persist_position_allowed`, `entry_marker`, `save_flag`, `role`,
    `status`, the ground bounds, the camera.  None of them is read by
    anything this file tests -- `login_entry_is_pinned`,
    `sanctioned_barred_blocker` and `resolve_entry`'s two refusals look at
    `n_id`, `login_entry_allowed` and `spawn is None`, and nothing else --
    so the fixture is honest for THIS lane's question and is not a
    rehearsal of lane A's row.  When that row lands, what proves the route
    is `TheSanctionAdmitsNothingOnMainTodayTests` going red against the
    real registry, not this stand-in going green.
    """
    base = world_scene_travel.load_scene_registry()
    template = base[world_scene_travel.HOME_SCENE_ID]
    row = replace(
        template,
        n_id=SANCTIONED,
        login_entry_allowed=login_entry_allowed,
        spawn=SANCTIONED_SPAWN_PER_CHIEF_DECISION if spawn else None,
    )
    # `SceneRegistry.__getitem__` is a linear scan returning the first row
    # whose n_id matches.  Since lane A landed the real n_id==SANCTIONED
    # row (round `oprday`, PR #332), `base.destinations` already carries
    # one -- appending the stand-in after it would make `registry[SANCTIONED]`
    # resolve to the REAL row instead of this fixture's variant, silently
    # feeding every caller of this helper the wrong shape.  Drop any
    # existing row with the same id before appending the stand-in so this
    # fixture keeps building the shape its `login_entry_allowed`/`spawn`
    # arguments ask for, independent of whether the real row exists yet.
    kept = tuple(d for d in base.destinations if d.n_id != SANCTIONED)
    return world_scene_travel.SceneRegistry(destinations=kept + (row,))


@requires_a_sanctioned_scene
class TheSanctionNowAdmitsViaSingleUseOnlyTests(unittest.TestCase):
    """The state of the route as measured, not as hoped.

    RENAMED from `TheSanctionAdmitsNothingOnMainTodayTests` in round
    `R249` (chief, gate-red repair of `pirate-force-server#332`): lane A
    landed the scene-126 registry row that round (pinned spawn, barred at
    ordinary login), which is exactly the event this class's old docstring
    said would turn it red "deliberately".  It did, and this is the
    "somebody has to come and say so" that docstring asked for -- the
    class now measures the OTHER true state: the single-use widening
    admits scene 126, the plain login-scene map still does not, and
    neither of the other two documents that sentence named needs a
    correction (`login_scene_admission`'s header never repeated the claim;
    the round letter is history and stays as written).
    """

    def test_lane_a_has_landed_the_row_barred_at_login(self):
        self.assertEqual(
            A.BLOCKER_LOGIN_PATH_BARS_IT,
            A.sanctioned_barred_blocker(SANCTIONED),
            "if this is anything else, lane A's registry row for scene "
            "126 either disappeared or changed shape (spawn/login_entry_"
            "allowed) since round R249 landed it on main -- re-read "
            "pirate-force-server#332 before touching this assertion",
        )

    def test_so_the_widening_admits_it_for_single_use_only(self):
        self.assertTrue(A.single_use_entry_is_admissible(SANCTIONED))
        self.assertNotIn(SANCTIONED, A.stageable_scene_ids())
        self.assertIn(SANCTIONED, A.single_use_stageable_scene_ids())
        self.assertEqual(
            set(A.single_use_stageable_scene_ids())
            - set(A.stageable_scene_ids()),
            {SANCTIONED},
            "the single-use map should widen by exactly the one sanctioned "
            "scene, not by more than the sanction map names",
        )


@requires_a_sanctioned_scene
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
        # Lane A's real row for 126 landed on main in round R249
        # (`pirate-force-server#332`), so the disk registry no longer
        # exercises "missing row" on its own -- build that shape through
        # the parameter instead, which is what this test's own comment
        # always intended ("asserted through the parameter rather than
        # through the disk so it keeps testing the rule after the row
        # lands").
        registry = world_scene_travel.load_scene_registry()
        registry = replace(
            registry,
            destinations=tuple(
                d for d in registry.destinations if d.n_id != SANCTIONED
            ),
        )
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


@requires_a_sanctioned_scene
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

    def test_the_readers_way_out_follows_the_readers_rule(self):
        """pf-adversary D3/M14: the reader picks a way out as well as a rule.

        MEASURED: pinning `way_out = stageable_scene_ids` unconditionally
        left the whole lane suite green.  The chat path's equivalent
        mutation is caught twice over; the READER's had nothing.  The
        console line an operator gets from a hand-edited config would then
        omit the sanctioned scene on the very file it is legal in, which
        `single_use_stageable_scene_ids`' own docstring calls worse than no
        way out.
        """
        registry = registry_with_sanctioned_row()
        ordinary = A.stageable_scene_ids(scene_registry=registry)
        self.assertNotIn(SANCTIONED, ordinary)
        # A file that is legal under the single-use rule except for ONE bad
        # row, so the refusal (and its way out) is printed for the bad row.
        unreachable = next(
            i for i in registry.ids if i not in A.single_use_stageable_scene_ids(
                scene_registry=registry
            )
        )
        self.gm_map_path.write_text(
            json.dumps(
                {
                    "gm_login_scene": {
                        self.GM_ACCOUNT: SANCTIONED,
                        "GM_TWO": unreachable,
                    }
                }
            ),
            encoding="utf-8",
        )
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            with self.assertRaises(login_scene_override.LoginSceneRefusedError):
                login_scene_override.load_login_scene_overrides(
                    self.gm_map_path, scene_registry=registry
                )
        line = buffer.getvalue()
        self.assertIn(
            f"stageable={A.single_use_stageable_scene_ids(scene_registry=registry)}",
            line,
            "the reader must offer the set ITS OWN rule admits",
        )
        self.assertIn(str(SANCTIONED), line.split("stageable=")[1])

    def test_the_reader_cannot_be_called_without_choosing_a_rule(self):
        # `single_use` is keyword-only and has no default, so a third map
        # cannot inherit whichever rule happened to be written first.
        with self.assertRaises(TypeError):
            login_scene_override._load_scene_id_map(
                self.gm_map_path, "gm_login_scene", None
            )


@requires_a_sanctioned_scene
class TheRefusalCarriesTheRuleThatRefusedTests(_ConfigCase):
    """A refusal says which rule it came from, so the remedy is right.

    `_refusal_cause` asks "would the DISK have taken this row" to tell
    "edit the config" from "restart the server".  Asked with the narrow
    rule about a single-use refusal of a sanctioned scene it answers no for
    a reason that has nothing to do with the disk, and the operator is sent
    to grep a file that is correct.
    """

    def test_a_single_use_refusal_is_flagged(self):
        # Lane A's real row for 126 landed on main in round R249
        # (`pirate-force-server#332`) with a pinned spawn, so the single-use
        # rule now ADMITS it -- the real disk can no longer stand in for "a
        # sanctioned scene refused by the single-use rule".  Use a stand-in
        # registry where the row exists but has no pinned spawn instead:
        # still refused (`BLOCKER_NO_PINNED_SPAWN`), still flagged
        # single_use, and no longer dependent on lane A never landing.
        self.write_gm_map(SANCTIONED)
        with self.assertRaises(
            login_scene_override.LoginSceneRefusedError
        ) as caught:
            login_scene_override.load_login_scene_overrides(
                self.gm_map_path,
                scene_registry=registry_with_sanctioned_row(spawn=False),
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
        """The two rules must be TOLD APART, not merely both asked.

        The first version of this test asserted that both rules agree on an
        ordinary scene and both refuse the sanctioned one today -- which is
        true, and which a probe that ignored `single_use` entirely would
        also satisfy.  MEASURED: deleting the `if single_use:` branch from
        `disk_admits_under_rule` left the whole lane suite green (957
        passed).  That is the rigged-pass shape this file's own docstring
        warns about, found in this file.

        So the case that separates them is the one that matters: a DISK
        that holds lane A's row.  There the single-use rule admits and the
        plain rule does not, and a probe that ignores the flag cannot
        answer both.
        """
        with lane_a_row_on_disk(registry_with_sanctioned_row()):
            self.assertTrue(
                A.disk_admits_under_rule(SANCTIONED, single_use=True),
                "the single-use rule admits a sanctioned scene whose only "
                "blocker is the login bar",
            )
            self.assertFalse(
                A.disk_admits_under_rule(SANCTIONED, single_use=False),
                "the plain rule -- the standalone map's rule -- must not",
            )
        # UPDATED round R249 (chief, gate-red repair of
        # `pirate-force-server#332`): lane A's row for 126 is on the real
        # disk now, pinned and barred at login -- so outside the mocked
        # "future" this context manager used to simulate, the single-use
        # rule already admits it, and only the plain rule still refuses.
        self.assertTrue(A.disk_admits_under_rule(SANCTIONED, single_use=True))
        self.assertFalse(A.disk_admits_under_rule(SANCTIONED, single_use=False))

    def test_the_remedy_word_follows_the_rule_that_refused(self):
        """The operator-visible payoff, walked rather than asserted about.

        Disk has lane A's row; the process's snapshot does not (lane A
        merged after this server booted).  A single-use entry naming the
        sanctioned scene is refused by the snapshot, and the remedy is
        RESTART THE SERVER -- not "edit the config", which is what the
        narrow rule would have said about a file that is correct.
        """
        from pirateforce_foundation.gm import login_scene_consume as C

        self.write_gm_map(SANCTIONED)
        # Lane A's row landed on the real disk in round R249
        # (`pirate-force-server#332`), so a plain snapshot of the disk can
        # no longer stand in for "booted before lane A merged" -- build
        # that shape explicitly instead of relying on which world happens
        # to be true today.
        disk_today = world_scene_travel.load_scene_registry()
        stale_snapshot = replace(
            disk_today,
            destinations=tuple(
                d for d in disk_today.destinations if d.n_id != SANCTIONED
            ),
        )
        with lane_a_row_on_disk(registry_with_sanctioned_row()):
            result = C.consume_login_scene_override(
                self.GM_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.gm_map_path),
                standalone_config_path=str(self.standalone_path),
                scene_registry=stale_snapshot,
            )
        self.assertEqual(C.CONSUME_FAILED, result.outcome)
        self.assertEqual(
            C.CAUSE_REGISTRY_STALE_SINCE_BOOT,
            result.cause,
            "asked with the narrow rule this says scene_not_admissible and "
            "sends the operator to grep a config file that is correct",
        )


@requires_a_sanctioned_scene
class TheWayOutMayNotNameAnUnnamedSceneTests(unittest.TestCase):
    """MEASURED GAP, fixed in the round that opened it.

    `single_use_stageable_scene_ids` re-applies `is_known_scene_id` to the
    sanctioned ids, and its docstring says why: the tuple is PRINTED to a
    person and an id with no name in the committed catalog is an
    instruction nobody can check.  Deleting that filter left the whole lane
    suite green (957 passed) -- because the one sanctioned id today, 126,
    IS in the name catalog, so no fixture could tell the difference.

    A claim no test can fail is a claim with no evidence behind it, which
    is exactly what `_admissible_ids`' own comment says cost this lane a
    pushed commit once already.  So the fixture supplies the case the
    sanction map cannot: a sanctioned id the catalog does not name.
    """

    def test_a_sanctioned_id_with_no_name_is_never_offered(self):
        from types import MappingProxyType
        from unittest import mock

        from pirateforce_foundation.gm import scene_catalog

        unnamed = next(
            i for i in range(9000, 12000) if not scene_catalog.is_known_scene_id(i)
        )
        registry = registry_with_sanctioned_row()
        # The row has to be admissible-but-barred, or the id would be
        # filtered out by the blocker instead and this would pass for the
        # wrong reason.
        template = registry[world_scene_travel.HOME_SCENE_ID]
        registry = world_scene_travel.SceneRegistry(
            destinations=registry.destinations
            + (replace(template, n_id=unnamed, login_entry_allowed=False),)
        )
        with mock.patch.object(
            A,
            "SANCTIONED_BARRED_SCENES",
            MappingProxyType({unnamed: "fixture: an id with no name"}),
        ):
            self.assertEqual(
                A.BLOCKER_LOGIN_PATH_BARS_IT,
                A.sanctioned_barred_blocker(unnamed, scene_registry=registry),
                "the fixture must reach the branch the filter guards",
            )
            self.assertTrue(
                A.single_use_entry_is_admissible(unnamed, scene_registry=registry),
                "admission does not consult the name catalog -- the READER "
                "does, and so does the way out; this pins which is which",
            )
            self.assertNotIn(
                unnamed,
                A.single_use_stageable_scene_ids(scene_registry=registry),
                "an id with no name in the committed catalog may not be "
                "PRINTED to a person as a destination they may pick",
            )


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


@requires_a_sanctioned_scene
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

    def test_the_way_out_can_name_what_this_snapshot_alone_cannot_stage(self):
        """The contradiction, asserted deliberately instead of by accident.

        pf-adversary D6 found this file holding both halves of it in two
        tests that pass without noticing: the way out computed from a
        snapshot offers the sanctioned id, and `/warp` on that SAME
        registry refuses, because staging asks the DISK first and a
        snapshot may only narrow.

        It is a real property of the two-reading design, not a test
        artifact, and it is NOT introduced by the widening --
        `stageable_scene_ids` has the identical one-reading shape and
        always has.  The sanctioned id makes an existing hole visible.  So
        it is pinned here, in one place, with the bound written down:
        the two answers differ only while lane A's file and the running
        process disagree, i.e. between a lane A merge and the next restart.
        The day somebody writes the function that compares the two
        readings, this test is where they will find out what it has to fix.
        """
        registry = registry_with_sanctioned_row()
        self.assertIn(
            SANCTIONED, A.single_use_stageable_scene_ids(scene_registry=registry)
        )
        # Lane A's real row landed on the real disk in round R249
        # (`pirate-force-server#332`), so an unmocked call no longer
        # exercises "before the merge" -- that state now has to be built
        # explicitly, the same way `TheRefusalCarriesTheRuleThatRefusedTests`
        # does it, rather than relied on as the ambient truth of the repo.
        disk_before_merge = replace(
            registry,
            destinations=tuple(
                d for d in registry.destinations if d.n_id != SANCTIONED
            ),
        )
        with lane_a_row_on_disk(disk_before_merge):
            result = self.stage(SANCTIONED, registry)
        self.assertFalse(
            result.staged,
            "the way out (computed from the snapshot) named a scene the "
            "disk (still missing the row) had to refuse",
        )
        # Both readings agreeing is what closes the gap, and it is the
        # state the day lane A merges AND the process is restarted.
        with lane_a_row_on_disk(registry):
            self.assertTrue(self.stage(SANCTIONED, registry).staged)

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
        #
        # Round R249 landed lane A's real row on the real disk, so "NOT on
        # disk" now has to be built explicitly (`lane_a_row_on_disk` mocked
        # to a row-less registry) instead of relied on as the ambient state
        # of the repo -- otherwise both the disk and the snapshot would
        # admit it and this test would stage the very thing it means to
        # refuse.
        disk_today = world_scene_travel.load_scene_registry()
        disk_before_merge = replace(
            disk_today,
            destinations=tuple(
                d for d in disk_today.destinations if d.n_id != SANCTIONED
            ),
        )
        with lane_a_row_on_disk(disk_before_merge):
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
        # Round R249 landed lane A's row on the real disk, so "a snapshot
        # that lacks the row" now has to be built explicitly rather than
        # read off the disk as-is -- the disk itself narrows nothing today.
        disk_today = world_scene_travel.load_scene_registry()
        missing_row = replace(
            disk_today,
            destinations=tuple(
                d for d in disk_today.destinations if d.n_id != SANCTIONED
            ),
        )
        self.assertFalse(self.stage(SANCTIONED, missing_row).staged)
        self.assertEqual({}, json.loads(self.gm_map_path.read_text())
                         .get("gm_login_scene", {}) if self.gm_map_path.exists()
                         else {})

    def test_the_refusal_names_the_sanction_rather_than_a_bare_no_entry(self):
        # Round R249 landed lane A's row on the real disk, so provoking the
        # DISK-refuses-it branch (the one this test is about) needs an
        # explicit "before merge" disk now, not the unmocked one.
        disk_today = world_scene_travel.load_scene_registry()
        disk_before_merge = replace(
            disk_today,
            destinations=tuple(
                d for d in disk_today.destinations if d.n_id != SANCTIONED
            ),
        )
        with lane_a_row_on_disk(disk_before_merge):
            result = self.stage(SANCTIONED, disk_before_merge)
        self.assertEqual(
            login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE, result.reason
        )


if __name__ == "__main__":
    unittest.main()
