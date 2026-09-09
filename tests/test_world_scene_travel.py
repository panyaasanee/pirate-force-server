"""LANE-A BUILD-002: scene destinations.

The load-bearing tests in this file are the two that keep the module honest
about what it does not know:

* ``test_the_test_stage_is_not_marked_as_sent_before`` - scene 278 is
  addressable in the client's table and has never been sent to a client by
  anybody in this project.  If that distinction ever quietly disappears, a
  reader of the boot console will think a first-ever destination is routine.
* ``test_the_census_is_offered_only_where_the_census_is_true`` - the bg0001
  census is bg0001's.  Delivering it into a football field would be the first
  cross-build-order defect this project shipped.
"""

import json
import re
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.lane_hooks import lane_a_scene_census
from pirateforce_foundation.population import SCENE_SEQUENCE
from pirateforce_foundation.world_scene_travel import (
    CENSUS_SOURCE,
    CLIENT_REGISTERED_SCENE_COUNT,
    HOME_SCENE_ID,
    MEASURED_SCENE_IDS,
    REGISTRY_PATH,
    TEST_STAGE_SCENE_ID,
    SceneDestination,
    destination,
    entry_console_line,
    entry_fields,
    entry_report,
    home_return_position,
    load_scene_registry,
    login_teleport_fields,
    entry_position,
    is_position_persist_allowed,
    population_source,
    production_allowed,
    spawn_position,
    test_only,
)


def _raw() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="ascii"))


def _write(tmp: Path, data: dict) -> Path:
    path = tmp / "registry.json"
    path.write_text(json.dumps(data), encoding="ascii")
    return path


class SceneRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_scene_registry()

    def test_the_registry_pins_exactly_the_scenes_that_have_evidence(self):
        """Five since round 8pfksm, when the Columbus M2 crosswalk correction
        named scene 17.

        1 and 2 are the two this client has loaded.  17 (Bg1001) is the real
        M2 destination: round 8pfksm re-derived, from sha256-pinned gamedata
        tables, that Columbus (MOBS n_ID 156, bg0001 placement index 1) opens
        quest 3021, not 3023 as an earlier status letter assumed, and quest
        3021's Q_TELEPORT1 target is scene 17 - not the debug/test stage 278.
        278 is the stage the owner asked for as a walk-in debug tool. 997 is
        FilmScene, which COO-DECISION 20260826_0246 section 1.2 named for M2 -
        a green screen with fog and environment still on.  Round 4fhdxv
        pointed the travel gate at it and then pointed it back at 278 after
        the adversary pass; 997 stays pinned with the reasons on both sides,
        because the COO's ruling stands.  An id appearing here without a
        decision behind it is what this test is for.

        SIX SINCE ROUND vyi2ud (2026-08-29, LANE-A), AND THE DECISION BEHIND
        THE SIXTH.  14 is Hell Volcano Island (Bg0015), whose 81-actor roster
        has been in this repository since round 02k3w5 with no way for anyone
        to reach the scene: GT-134's blocker B2 read "the registry has no
        pinned destination, and pinning one needs the native .npc digest,
        which the cloud clone does not have".  That premise was false - the
        digest is a column of pf_bridge/gamedata/PF_GAMEDATA_SCENE_INDEX.tsv
        and has been all along.  This one is also the first spawn here that is
        neither a runtime historical choice, nor a borrowed monster placement,
        nor an owner decree: SCENE_NAME[14].n_MARKER -> MARKER[14] is the
        arrival point the map's own developers authored
        (world_scene_marker.py).  It is pinned with login_entry_allowed
        FALSE, and that is the round's own correction rather than caution:
        the first draft opened the door, and pf-adversary drove a login
        through it and measured three defects - the bg0001 census shipped
        into scene 14, a (scene 1, volcano XYZ) row written into
        character_positions, and the faction-1 byte silently dropped - all
        three because runtime.py reads the STORED scene id, which the
        login-scene override never rewrites.  So this row is DATA (the
        marker spawn, the table row, the native digest) and the entry stays
        refused until the runtime asks about the scene a character is
        actually in.  See the registry's own nonclaims, which name what has
        to change before the key flips.

        SIXTEEN SINCE ROUND ga91m5 (2026-08-29, LANE-A), AND THE TEN NEW ONES
        ARRIVED WITHOUT A DECISION EACH, WHICH IS THE POINT.  Every id above
        got here by a ruling of its own; 3, 4, 5, 6, 7, 8, 9, 10, 11 and 130
        did not, and asking for ten more rulings is exactly the cost
        COO-DECISION 20260829_0542 abolished.  They are every remaining scene
        the client's own table gives a non-zero n_MARKER (13 marker scenes,
        minus 1, 2 and 14, which were already here), each standing on the
        point SCENE_NAME[n].n_MARKER -> MARKER[n_MARKER] resolves to, each at
        evidence tier `authored`, none with a ground block, and none with a
        population.  130 is the row that earns its place twice over: it names
        marker 1000, so it is this registry's live example of why rule 2
        forbids indexing MARKER by a scene id.  An id appearing here with
        NEITHER a decision NOR a non-zero n_MARKER behind it is what this test
        is now for, and that second half is checked rather than asserted in
        tests/test_world_scene_registry_rule_1_scenes.py.

        AND ALL TEN ARE ADDRESSES, NOT DOORS.  Every one carries
        login_entry_allowed false, so this registry grew by ten rows and the
        set of scenes anything can enter did not grow at all.  The round
        intended to open them; pf-adversary refuted the safety case before the
        commit and the doors were shut instead - see
        tests/test_world_scene_registry_rule_1_scenes.py, class
        TheDoorIsShutAndThisIsTheLoadBearingTest, which carries both
        refutations and the shape of the test that failed to catch them.

        THE PARAGRAPH ABOVE ABOUT SCENE 14 IS KEPT, NOT CORRECTED, AND TWO OF
        ITS THREE DEFECTS ARE NOW CLOSED ON THE FLAGLESS PATH.  D1 (the bg0001
        census delivered into another map) and D2 (a character_positions row
        labelled scene 1 carrying another scene's XYZ) were closed by
        CHIEF-DECISION 20260829_0520 option A and the
        login_scene_override_visit branch that landed with it.  D3, the
        faction-1 byte, is still open.  Neither closure reaches the inherited
        v141 population branch, which composes scene-1 actors into whatever
        scene the player stands in on any boot that is not exactly flagless -
        that is what shut the ten, and it would reopen D1 for scene 14 too.
        """
        # 304 and 305 ADDED round n4vqxc (COO-DECISION 20260905_1748): the two
        # seas a sea-edge crossing at scene 126's own map edge leads to, each
        # pinned the same `decreed_arrival` way 126 itself is, tagged
        # `decreed_provisional` rather than `authored` -- see
        # world_sea_edge_crossing.py.  Also addresses, not doors:
        # login_entry_allowed is false for both.
        self.assertEqual(
            self.registry.ids,
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 17, 126, 130, 304, 305,
             TEST_STAGE_SCENE_ID, 997),
        )

    def test_scene_126_is_a_diagnostic_pin_not_a_destination(self):
        """SEVENTEEN SINCE THIS ROUND (LANE-A, 2026-08-30), AND IT IS NOT A
        RULE-1 SCENE AND NOT A DESTINATION.

        CHIEF-DECISION R229 (pf_bridge/notes_to_chief/20260829_1603_CHIEF-
        DECISION-var2-test-path-scene126-registry-row-plus-gm-warp.md)
        asked this lane for the smallest pin that lets chief open a GT
        ticket testing whether ``QUESTDATA_TH__QUEST`` row 3021's
        ``n_VARI_2 = 17`` is a scene id (today's reading,
        ``COLUMBUS_DEST_SCENE_ID``, COO-DECISION 20260829_0441) or a
        MARKER id (``MARKER[17].n_SCENE = 126`` at (3050,232,90), COO-
        DECISION 20260830_1351 holds this question for the owner).

        SCENE 126'S OWN ``SCENE_NAME.n_MARKER`` IS 0, so COO-DECISION
        20260829_0542's rule 1 does not reach it the way it reaches the
        ten scenes in ``tests/test_world_scene_registry_rule_1_scenes.py``
        - this is why that file's control case for "no marker and no
        ruling" moved to scene 18 instead: scene 126 now has a ruling
        (CHIEF-DECISION R229) but still has no self-referencing marker, so
        it is neither a rule-1 authored scene nor an unpinned one.  Its
        coordinate is MARKER[17]'s real x/y/z, reached by the REVERSE
        relation (MARKER[17].n_SCENE == 126) rule 2 forbids using as a
        shortcut FROM a scene id - used here explicitly the other
        direction, under a named decision, not as a silent shortcut.
        """
        row = destination(126, self.registry)
        # UPDATED 2026-09-08 (LANE-A round 9lv3fa, PANYA-DECISION
        # 20260908_1218): ~~self.assertFalse(row.login_entry_allowed)~~.  The
        # owner's permanent rule is that a login returns a character to the
        # point it logged out from in EVERY scene, so the door here is open.
        # The rest of this test is untouched on purpose and is the reason it
        # keeps its name: 126 is still not a rule-1 scene, its coordinate is
        # still not from its own marker, and an open login door does not
        # change either of those claims.  The RULE that keeps this True is
        # walked in tests/test_world_scene_registry_login_door.py.
        self.assertTrue(row.login_entry_allowed)
        self.assertEqual(row.spawn, (3050.0, 232.0, 90.0))
        # UPDATED 2026-09-05 (COO-DECISION 20260905_0251, LANE-A):
        # `sent_before` and `login_entry_allowed` are separate claims (COO's
        # own ruling item (c)) -- round R313 put a live client on the open
        # sea with `WORLD_SCENE scene_id=126` on the wire, so `sent_before`
        # is now True.  This does NOT make 126 a destination this server may
        # route a login into: `login_entry_allowed` is a different registry
        # field, unread by `sent_before`, and stays False here unchanged.
        self.assertTrue(row.sent_before)
        raw = {d["n_id"]: d for d in _raw()["destinations"]}[126]
        self.assertIs(raw["coordinate_provenance"]["from_marker"], False)
        self.assertIsNone(raw["coordinate_provenance"]["marker_n_id"])
        self.assertIs(
            raw["coordinate_provenance"]["deviates_from_rule_1"], False)
        # UPDATED 2026-09-05 (LANE-A round ihjytc, PANYA-DECISION
        # 20260905_1329 via COO-DECISION 20260905_1346 item 3): the tier moved
        # ~~decreed_provisional~~ -> `decreed_permanent`.  The owner pinned
        # this point permanently, so the expiry the provisional tier carried
        # is gone.  Everything this test asserts ABOVE the tier is unchanged
        # and deliberately so: `from_marker` stays False, `marker_n_id` stays
        # null and `n_MARKER` stays 0, because rule 1 still does not reach
        # this scene.  The decree is a SECOND route to an arrival point, in
        # its own block, not an edit to the rule-1 answer.
        self.assertEqual(
            raw["coordinate_provenance"]["evidence_tier"],
            "decreed_permanent",
        )
        self.assertEqual(raw["table_row"]["n_MARKER"], 0)
        self.assertIsNone(raw["ground"])

    def test_the_default_destination_is_still_home(self):
        # Nothing in this module may move where a player lands by existing.
        self.assertEqual(destination().n_id, HOME_SCENE_ID)
        self.assertEqual(entry_fields(destination()), (1, SCENE_SEQUENCE))

    def test_the_test_stage_is_addressed_by_its_table_row(self):
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        self.assertEqual(stage.model_id, "Bg1177")
        self.assertEqual(entry_fields(stage), (278, 0))
        self.assertEqual(stage.image_name, "BgNull")

    def test_the_test_stage_is_not_marked_as_sent_before(self):
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        self.assertFalse(stage.sent_before)
        self.assertIn("NO", entry_console_line(stage))
        for measured in MEASURED_SCENE_IDS:
            self.assertTrue(destination(measured, self.registry).sent_before)

    def test_the_census_is_offered_only_where_the_census_is_true(self):
        # GENERALIZED 2026-08-27 (PANYA-DECISION 20:10, M1-P): scene 2 now has
        # its own named source (world_population_bg0002.py's roster), not
        # bg0001's census and not None - see CENSUS_SOURCES.
        self.assertEqual(population_source(1), CENSUS_SOURCE)
        self.assertEqual(population_source(2), "bg0002_roster")
        self.assertIsNone(population_source(TEST_STAGE_SCENE_ID))

    def test_the_flat_ground_measurement_the_choice_rests_on_is_pinned(self):
        # The whole reason this scene was chosen.  Nine placements over 6195 x
        # 2209 units sharing one z to within float32 noise.
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        self.assertEqual(stage.native_placement_count, 9)
        self.assertLessEqual(stage.ground_z_spread, 0.002)
        extent_x, extent_y = stage.ground_extent
        self.assertGreater(extent_x, 6000.0)
        self.assertGreater(extent_y, 2000.0)

    def test_scene_17s_ground_is_pinned_from_its_own_placements_tsv(self):
        """Round kqrlhr: packages the numbers scene 17's own
        table_row_differences.ground_is_null_because already cited as
        'measured this round' into the same ground schema scene 278 uses -
        no re-derivation, nothing invented.

        UPDATED, round e0daaa (chief): this test originally asserted scene
        17's spawn stays null, on the assumption that only this ground block
        would land this round. Independently, in the same round,
        PANYA-DECISION 2026-08-27T14:45+07:00 decreed a PROVISIONAL spawn
        (0,0,0) for scene 17 -- NOT derived from this ground data, an owner
        override of the "no invented coordinate" rule for this scene only
        (see world_scene_registry_001.json's own merge note on this entry,
        and world_scene_travel._spawn()'s PROVISIONAL_SPAWN_PROVENANCE_PREFIX
        carve-out, which is why loading this pin does not refuse even though
        the decreed z=0.0 falls outside this very ground block's z bounds).
        RE-103 is still closed bounded-negative -- no MEASURED player-arrival
        marker exists -- so this scene's ground evidence and its spawn are
        independent facts, exactly as this test's own name says: the ground
        is pinned from placements.tsv, the spawn is a decree, and neither
        retracts the other.
        """
        sea = destination(17, self.registry)
        self.assertEqual(sea.native_placement_count, 8)
        self.assertEqual(sea.spawn, (0.0, 0.0, 0.0))
        self.assertTrue(sea.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE"))
        self.assertAlmostEqual(sea.ground_z_spread, 526.6963500976562)
        extent_x, extent_y = sea.ground_extent
        self.assertAlmostEqual(extent_x, 1815.9349365234375)
        self.assertAlmostEqual(extent_y, 2395.249755859375)
        # Nowhere near Bg1177's 0.002-unit-flat deck - the whole point of
        # pinning this is that scene 17 is NOT one flat plane.
        self.assertGreater(sea.ground_z_spread, 500.0)
        raw = [row for row in _raw()["destinations"] if row["n_id"] == 17][0]
        self.assertEqual(
            raw["ground"]["placements_tsv_sha256"],
            "5e4de48707a87061d9a95471a1c3c25c56f0469fe2ece7ef0709a9c79f40fec7",
        )

    def test_scene_17_is_open_at_login_like_every_other_pinned_scene(self):
        """~~test_scene_17_is_pinned_not_allowed_as_a_login_destination~~ --
        RENAMED AND INVERTED, LANE-A round 9lv3fa, 2026-09-08.

        WHAT THIS TEST USED TO SAY, kept because it is the reason the field
        exists at all: round 0z3kjx found that scene 17 had stopped being a
        scene with no pinned spawn (round e0daaa's owner decree), so the free
        login-time refusal that had protected a persisted row naming it
        (REFUSED_NO_PINNED_SPAWN) was gone, and login_entry_allowed=False was
        put in its place.

        WHY IT NOW SAYS THE OPPOSITE.  PANYA-DECISION 20260908_1218 is the
        owner's own permanent rule: logging in returns a character to the
        exact point it logged out from, IN EVERY SCENE, sea included.  Under
        that rule a shut door is not a fence around a half-known scene, it is
        a player who cannot get back into their own character.  The owner's
        letter also records that this pin was this project's belt-and-braces,
        not a fact about the original game.

        THE FIELD IS NOT DEAD and this file still proves it works - see
        tests/test_world_scene_registry_login_door.py, which walks the whole
        registry for the rule and refuses a synthetic pinned-False scene to
        prove the mechanism still bites."""
        sea = destination(17, self.registry)
        self.assertTrue(sea.login_entry_allowed)
        raw = [row for row in _raw()["destinations"] if row["n_id"] == 17][0]
        self.assertIs(raw["login_entry_allowed"], True)

    def test_every_other_destination_defaults_login_entry_allowed_true(self):
        """The optional field's absence must mean True, not merely 'False
        for the one row that sets it' - a mutation that flipped the default
        would silently lock every other destination out of login."""
        # DERIVED, not hand-listed - same reason as the persist-default test
        # below (pf-adversary, round vyi2ud, D12).
        rows = {row["n_id"]: row for row in _raw()["destinations"]}
        defaulted = [n_id for n_id, row in rows.items()
                     if "login_entry_allowed" not in row]
        self.assertTrue(defaulted, "no destination defaults this key any more")
        for n_id in defaulted:
            with self.subTest(n_id=n_id):
                self.assertTrue(destination(n_id, self.registry).login_entry_allowed)

    def test_scene_17_now_persists_its_position_like_every_other_scene(self):
        """Round jafskv: GT-106 (notes_to_chief/20260827_1710_GT106-RESULT-
        M2-Columbus-3021-enters-scene17-*) watched a character walk into
        scene 17 and come out of teardown with a character_positions row
        reading scene_id=1 carrying scene 17's XYZ - wrong on both columns.
        The obvious fix, persisting scene 17 for real, was refused on
        purpose: scene 17 already carries login_entry_allowed=false (round
        0z3kjx) precisely because a persisted row naming 17 is refused at the
        very next login, and this scene has no measured way back
        (return_ticket=REQUIRED). persist_position_allowed=false is the
        smaller, reversible answer - see
        world_scene_registry_001.json's persist_position_allowed_because for
        the full incident."""
        # INVERTED 2026-09-08 (LANE-A round 9lv3fa, PANYA-DECISION
        # 20260908_1218).  The docstring above is kept verbatim because every
        # sentence of it was true when written, and because its argument
        # names its own expiry: "persist_position_allowed=false is the
        # smaller, reversible answer" rested ENTIRELY on scene 17 being shut
        # at login.  The owner has opened that door in every scene, so
        # refusing to write is now the thing that strands a player - the
        # character comes back at wherever it last stood SOMEWHERE ELSE.
        # The GT-106 row (scene_id=1 carrying scene 17's XYZ) stays a real
        # bug and stays owned by the WRITER: lifecycle.checkpoint and
        # tests/test_lifecycle_persist_position_gate.py, not this pin.
        sea = destination(17, self.registry)
        self.assertTrue(sea.persist_position_allowed)
        self.assertTrue(is_position_persist_allowed(17, self.registry))
        raw = [row for row in _raw()["destinations"] if row["n_id"] == 17][0]
        self.assertIs(raw["persist_position_allowed"], True)

    def test_every_other_destination_defaults_persist_position_allowed_true(self):
        """The optional field's absence must mean True, not merely 'False for
        the one row that sets it' - a mutation that flipped the default
        would silently stop persisting positions for scenes that have never
        shown the GT-106 bug at all."""
        # DERIVED, not hand-listed (pf-adversary, round vyi2ud, D12): the
        # literal tuple this loop used to carry had to be edited by hand
        # every time a destination was added, in the same file as the
        # tripwire that exists to catch an unexplained addition.  "Every
        # other destination" now means what it says: every row that does not
        # set the key.
        rows = {row["n_id"]: row for row in _raw()["destinations"]}
        defaulted = [n_id for n_id, row in rows.items()
                     if "persist_position_allowed" not in row]
        self.assertTrue(defaulted, "no destination defaults this key any more")
        for n_id in defaulted:
            with self.subTest(n_id=n_id):
                raw = rows[n_id]
                self.assertTrue(
                    destination(n_id, self.registry).persist_position_allowed)
                self.assertTrue(is_position_persist_allowed(n_id, self.registry))

    def test_an_unpinned_scene_fails_open_for_position_persistence(self):
        """Deliberately the OPPOSITE default from login_entry_allowed and
        spawn_position, which both fail closed for a scene this registry does
        not pin. A scene not in the registry is, by definition, a scene this
        exact persistence bug has never had the chance to touch - fail-closed
        here would silently stop persisting positions for every future scene
        on the strength of a bug none of them exhibited. See
        is_position_persist_allowed's own docstring for the full argument."""
        self.assertTrue(is_position_persist_allowed(279, self.registry))
        with self.assertRaises(ValueError):
            is_position_persist_allowed(0, self.registry)

    def test_the_pin_carries_the_hashes_a_bridge_round_reverifies(self):
        # These are the values a bridge-side round re-checks against the client
        # files themselves; a silent edit here would break that crosswalk
        # without breaking anything else.
        raw = _raw()
        # This repository cannot open the sources, so this cannot verify them.
        # What it holds is that the pin still carries the exact strings a
        # bridge-side round re-runs sha256sum against, and the command to do it.
        self.assertIn("sha256sum", raw["provenance"]["reverify_on_the_bridge"])
        self.assertEqual(
            raw["provenance"]["scene_name_table_sha256"],
            "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b",
        )
        self.assertEqual(
            raw["provenance"]["scene_name_table_rows"],
            CLIENT_REGISTERED_SCENE_COUNT,
        )
        stage = [row for row in raw["destinations"] if row["n_id"] == 278][0]
        self.assertEqual(
            stage["native_sha256"],
            "7dbe6618c21edbc3d23da2789b9b799e9a035f2c2dd91a3a889fb39cd524bfc2",
        )
        self.assertEqual(
            stage["ground"]["placements_tsv_sha256"],
            "4f09dfeaa5b75d65a09009fe0ad58b01a4e6644e1f2eb64b55af3d7e7c4a0f02",
        )
        # Round uajlve, from a pf-adversary finding: scene 17's two hashes
        # were pinned in round kqrlhr and asserted NOWHERE, and its ground
        # source was missing from reverify_on_the_bridge as well - so both
        # halves of the crosswalk this test exists to protect were open for
        # scene 17 while being closed for 278.  Re-hashed on the bridge tree
        # this round and matched; asserted here so the next silent edit is
        # caught the same way 278's would be.
        sea = [row for row in raw["destinations"] if row["n_id"] == 17][0]
        self.assertEqual(
            sea["native_sha256"],
            "da5c560af6c483490a041f0605a1b0cfe047a7ee00e515de07567d0c1247e821",
        )
        self.assertEqual(
            sea["ground"]["placements_tsv_sha256"],
            "5e4de48707a87061d9a95471a1c3c25c56f0469fe2ece7ef0709a9c79f40fec7",
        )
        self.assertIn("Bg1001", raw["provenance"]["reverify_on_the_bridge"])

    def test_the_pin_does_not_claim_to_be_unread_by_the_runtime(self):
        """Round uajlve, pf-adversary finding.

        This file's own ``not_a_scenario`` and its last ``nonclaims`` line
        both said no runtime path reads it.  That was true when they were
        written and false at HEAD: runtime.py loads this registry at startup
        and asks it whether a character's position may be persisted, and
        ``login_entry_allowed``/``persist_position_allowed`` are enforced
        from it.  A reader who believed those sentences would read a live
        safety interlock as an inert note - which is the failure this test
        pins, not the wording.
        """
        raw = _raw()
        stale = "no runtime path reads it until"
        self.assertIn(stale, raw["not_a_scenario"])
        # Struck, not deleted - and the correction has to travel with it.
        self.assertIn("~~", raw["not_a_scenario"])
        self.assertIn("runtime.py:520", raw["not_a_scenario"])
        self.assertTrue(
            any("~~" in claim and "no runtime path reads it yet" in claim
                for claim in raw["nonclaims"]),
            "the nonclaim that this file is unread must stay struck",
        )

    def test_the_pin_file_is_pure_ascii(self):
        # The bridge console is cp874; a scene name in its source glyphs would
        # kill a round the way R171's emoji did.  The source names live in the
        # pin as utf-8 hex instead.
        REGISTRY_PATH.read_bytes().decode("ascii")

    def test_the_spawn_is_a_position_the_scene_author_used(self):
        """Not a synthetic point.  This is native placement 4, Mob_set_02 04.

        The first version of this pin was the centroid of the nine placements,
        which is 705 units from the nearest of them - the one position in this
        scene with nothing authored under it.  The centroid is kept in the pin
        as superseded history and must stay different from the live spawn, or
        the correction has been quietly undone.
        """
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        x, y, z = spawn_position(stage)
        self.assertEqual((x, y, z), (-13270.0576171875, 22794.2734375, -2492.7685546875))
        self.assertIn("placement index 4", stage.spawn_provenance)
        raw = [r for r in _raw()["destinations"] if r["n_id"] == 278][0]
        self.assertNotEqual(
            (raw["superseded_spawn"]["x"], raw["superseded_spawn"]["y"]),
            (x, y),
            "the superseded centroid must not creep back into the live spawn",
        )

    def test_a_scene_with_no_pinned_spawn_refuses_to_invent_one(self):
        made_up = SceneDestination(
            n_id=999, model_id="Bg9999", scene_name_ascii="nowhere",
            image_name="BgNull", native_placement_count=0, role="test_stage",
            status="never_sent_to_any_client_by_this_project", spawn=None,
            spawn_provenance=None, ground_z_spread=None, ground_extent=None,
            ground_box=None,
            save_flag=0, entry_marker=0, camera_type=0, limit_height=0,
        )
        with self.assertRaises(ValueError):
            spawn_position(made_up)

    def test_an_unpinned_scene_is_a_refusal_not_a_default(self):
        with self.assertRaises(KeyError):
            destination(279, self.registry)
        with self.assertRaises(ValueError):
            destination(0, self.registry)

    def test_the_entry_report_carries_what_a_console_reader_needs(self):
        report = entry_report(destination(TEST_STAGE_SCENE_ID, self.registry))
        self.assertEqual(report["scene_id"], 278)
        self.assertEqual(report["scene_seq"], 0)
        self.assertFalse(report["sent_before"])
        self.assertIsNone(report["population_source"])
        line = entry_console_line(destination(TEST_STAGE_SCENE_ID, self.registry))
        line.encode("ascii")
        self.assertTrue(line.startswith("WORLD_SCENE scene_id=278 seq=0"))

    def test_entry_fields_and_spawn_refuse_anything_but_a_destination(self):
        for bad in (278, "278", None, {"n_id": 278}):
            with self.assertRaises(ValueError):
                entry_fields(bad)
            with self.assertRaises(ValueError):
                spawn_position(bad)


class SceneRegistryRefusalTests(unittest.TestCase):
    """Every refusal below is reached by mutating the real pin, one field at a
    time, so each one is a guard that demonstrably fires."""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())

    def test_an_unknown_root_field_is_refused(self):
        data = _raw()
        data["extra"] = 1
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_destination_without_coordinate_provenance_is_refused(self):
        # COO-DECISION 20260829_0542 rule 3 as a load-time guard rather than
        # a convention: a row whose coordinate has no stated origin does not
        # load at all.  Without this the rule is a docstring, and the next
        # scene arrives with an unattributed point.
        data = _raw()
        del data["destinations"][0]["coordinate_provenance"]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_half_written_coordinate_provenance_is_refused(self):
        for missing in ("source", "from_marker", "marker_n_id",
                        "evidence_tier", "note"):
            with self.subTest(missing=missing):
                data = _raw()
                del data["destinations"][0]["coordinate_provenance"][missing]
                with self.assertRaises(ValueError):
                    load_scene_registry(_write(self.tmp, data))

    def test_a_row_that_claims_a_marker_without_naming_one_is_refused(self):
        # And its mirror: a row that disclaims a marker but carries an id.
        # Either way the field would record a decision nobody made.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["coordinate_provenance"]["marker_n_id"] = None
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 17:
                row["coordinate_provenance"]["marker_n_id"] = 17
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_marker_scene_cannot_flip_its_own_flag_out_of_the_rule(self):
        # THE EXACT ATTACK pf-adversary ran (round 8ubiku, D2): set scene
        # 14's from_marker to false and its tier to client-observed, leaving
        # the spawn byte-identical to MARKER[14].  Under the first version
        # of this round the whole suite stayed green and an authored point
        # had been promoted with no attended round.  The authority is now
        # table_row.n_MARKER, which the row does not get a vote on.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["coordinate_provenance"].update(
                    from_marker=False, marker_n_id=None,
                    evidence_tier="client-observed",
                )
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_row_that_names_a_marker_its_table_row_does_not_is_refused(self):
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["coordinate_provenance"]["marker_n_id"] = 2
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_marker_provenance_whose_spawn_is_not_the_marker_is_refused(self):
        # The check that stops the provenance field being edited in the same
        # commit as the coordinate it describes: the pinned crosswalk is a
        # second opinion sourced from the client's table, not from this file.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["spawn"]["x"] = row["spawn"]["x"] + 1.0
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_an_undeclared_deviation_from_rule_1_is_refused(self):
        # Scene 1 has marker 1 and declines to use it.  That stays possible,
        # but only as a labelled deviation a reader can grep for.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 1:
                row["coordinate_provenance"]["deviates_from_rule_1"] = False
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_deviation_declared_by_a_scene_with_no_marker_is_refused(self):
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 17:
                row["coordinate_provenance"]["deviates_from_rule_1"] = True
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_an_invented_evidence_tier_is_refused(self):
        # An open string field would let a round write "verified" and mean
        # nothing by it.
        for bad in ("confirmed", "verified", "authored-ish", "", None):
            with self.subTest(bad=bad):
                data = _raw()
                data["destinations"][0]["coordinate_provenance"][
                    "evidence_tier"] = bad
                with self.assertRaises(ValueError):
                    load_scene_registry(_write(self.tmp, data))

    def test_a_table_row_cannot_walk_a_scene_out_of_the_rule(self):
        # pf-adversary, round 8ubiku2, E3, escape 1.  Round 8ubiku declared
        # table_row.n_MARKER "the client's table" and compared it to nothing,
        # so zeroing it moved scene 14 out of rule 1 with its spawn still on
        # MARKER[14] and the full suite showing one red - a NEGATIVE test
        # that stopped raising.  The pinned crosswalk now gets a vote.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["table_row"]["n_MARKER"] = 0
                row["coordinate_provenance"].update(
                    from_marker=False, marker_n_id=None,
                    evidence_tier="client-observed",
                )
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_declared_deviation_must_actually_deviate(self):
        # E3, escape 2: n_MARKER left at 14, from_marker false, deviation
        # declared, spawn still exactly on the marker.  A label, not a
        # deviation, and it used to load.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 14:
                row["coordinate_provenance"].update(
                    from_marker=False, marker_n_id=None,
                    deviates_from_rule_1=True,
                    evidence_tier="client-observed",
                )
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_duplicated_scene_is_refused(self):
        data = _raw()
        data["destinations"].append(dict(data["destinations"][0]))
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_non_bool_login_entry_allowed_is_refused(self):
        for bad in (1, "false", None, 0):
            with self.subTest(bad=bad):
                data = _raw()
                for row in data["destinations"]:
                    if row["n_id"] == 17:
                        row["login_entry_allowed"] = bad
                with self.assertRaises(ValueError):
                    load_scene_registry(_write(self.tmp, data))

    def test_a_non_bool_persist_position_allowed_is_refused(self):
        for bad in (1, "false", None, 0):
            with self.subTest(bad=bad):
                data = _raw()
                for row in data["destinations"]:
                    if row["n_id"] == 17:
                        row["persist_position_allowed"] = bad
                with self.assertRaises(ValueError):
                    load_scene_registry(_write(self.tmp, data))

    def test_a_spawn_outside_the_pinned_ground_is_refused(self):
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 278:
                row["spawn"]["x"] = row["ground"]["x_min"] - 1.0
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_spawn_off_the_pinned_ground_plane_is_refused(self):
        # z matters more here than x or y: the whole claim about this scene is
        # that its ground is one plane, so a spawn above or below it is a
        # standing position in the air or under the floor.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 278:
                row["spawn"]["z"] = row["ground"]["z_max"] + 50.0
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_provisional_owner_decree_spawn_is_exempt_from_the_ground_bound_check(self):
        # Round e0daaa: scene 17's real pin has exactly this shape (a
        # PROVISIONAL-OWNER-DECREE spawn whose z falls outside its own
        # scene's ground z bounds) and it must still load. Proven here with
        # a mutated copy of 278 (rather than reading scene 17's own numbers)
        # so this test does not silently stop meaning anything the day some
        # other round changes scene 17's own data.
        data = _raw()
        out_of_bounds_z = None
        for row in data["destinations"]:
            if row["n_id"] == 278:
                out_of_bounds_z = row["ground"]["z_max"] + 999.0
                row["spawn"] = {
                    "x": row["ground"]["x_min"],
                    "y": row["ground"]["y_min"],
                    "z": out_of_bounds_z,
                    "provenance": "PROVISIONAL-OWNER-DECREE-TEST-ONLY",
                }
        registry = load_scene_registry(_write(self.tmp, data))
        stage = destination(278, registry)
        # Same mutation, non-provisional provenance: must still refuse - the
        # exemption is keyed on THIS spawn's own provenance text, not on
        # "some spawn somewhere is out of bounds and got let through".
        self.assertEqual(stage.spawn[2], out_of_bounds_z)
        self.assertTrue(stage.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE"))
        data["destinations"] = [
            dict(row, spawn=dict(row["spawn"], provenance="not a decree"))
            if row["n_id"] == 278 else row
            for row in data["destinations"]
        ]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_destination_missing_its_table_columns_is_refused(self):
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 278:
                del row["table_row"]["n_SAVE"]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_half_written_ground_block_is_refused_by_contract(self):
        data = _raw()
        # n_id lookup, not a positional index: scene 17 (round 8pfksm) sits
        # at index 2. It gained its own ground block in round kqrlhr, so this
        # deliberately mutates 278's instead - either destination's half-write
        # must be refused the same way, and 278 is the one this test has
        # always targeted.
        for row in data["destinations"]:
            if row["n_id"] == 278:
                del row["ground"]["z_min"]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_scene_17s_half_written_ground_block_is_also_refused(self):
        # The sibling of the test above, now that scene 17 has a ground block
        # of its own (round kqrlhr) - the contract has to hold for both.
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 17:
                del row["ground"]["z_max"]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_probe_flag_flip_is_refused(self):
        data = _raw()
        data["test_only"] = True
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_destination_missing_a_field_is_refused(self):
        data = _raw()
        for row in data["destinations"]:
            if row["n_id"] == 278:
                del row["ground"]
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))

    def test_a_non_ascii_scene_name_is_refused(self):
        data = _raw()
        # written as escapes so this test file itself stays 7-bit ASCII
        for row in data["destinations"]:
            if row["n_id"] == 278:
                row["scene_name_ascii"] = "\u6c99\u7058"
        with self.assertRaises(ValueError):
            load_scene_registry(_write(self.tmp, data))


class NoCommentClaimsADoorThisRegistryOpened(unittest.TestCase):
    """pf-adversary D9 of round ``sbqohw``: five sentences in this module
    said a scene's login door was shut, and the branch they sit on had
    opened every one of them.  (Nine, once this check was written.)

    Striking them is a fix for those nine.  This is the fix for the class of
    defect: an unstruck ``login_entry_allowed: false`` sentence is a defect
    only when the scene ITS OWN PARAGRAPH names is open in the registry.  A
    door that really is shut may say so unstruck, and the day a future round
    pins one shut again its sentence must be un-struck rather than left
    reading as false - which is why this is per-scene and not a blanket ban
    on the string.

    Strikethrough is the house's own convention for "this was true and is
    not"; a deleted sentence loses the record of who believed what, and a
    left-standing one is a comment that lies.

    WIDENED round ynfhoc (LANE-A), pf-adversary addendum on the sibling
    branch (B3): this used to read ONLY ``world_scene_travel.py`` and check
    ONLY the literal string ``"login_entry_allowed: false"``.  Two more
    places carry the exact same class of false claim and this check could
    not see either of them: the registry's own pin file (prose ``status``
    fields say things about a door the ``login_entry_allowed`` COLUMN right
    beside them already contradicts) and ``lane_hooks/lane_a_scene_census.py``
    (whose own admission-arm comments repeat the same "this scene's door is
    shut" claim the arms exist to work around).  Both are added below,
    scanned by the same struck-span-aware logic, so a scene reopened by a
    future round is caught in all three files at once instead of one.
    """

    TRAVEL_SOURCE = Path(world_scene_travel.__file__).read_text(
        encoding="utf-8")
    CENSUS_SOURCE = Path(lane_a_scene_census.__file__).read_text(
        encoding="utf-8")
    REGISTRY_SOURCE = Path(world_scene_travel.REGISTRY_PATH).read_text(
        encoding="utf-8")

    # Every regex below is matched case-insensitively.  Each one is a form
    # this codebase has actually been caught writing (see the pf-adversary
    # addendum this round), not a hypothetical.
    DOOR_SHUT_PATTERNS = (
        # Field-literal form: "login_entry_allowed: false", tolerant of the
        # line wrap and comment-hash a ``# ...`` continuation inserts
        # between the colon and the word.
        # ~~measured: this exact break occurs twice in
        # lane_a_scene_census.py~~ -- STRUCK, MEASURED FALSE, LANE-A round
        # 9ic0io (pf-adversary A1 on round ynfhoc).  Re-derived by running
        # both regexes over the file: the wrapped form
        # (`login_entry_allowed:` + newline + `# false`) occurs ONCE, at
        # `lane_a_scene_census.py:293`; the four other hits are the plain
        # one-line form a substring check would already catch.  The
        # tolerance is still worth having -- one dodge is a dodge -- but it
        # is bought for one site, not two, and the number was written here
        # without being counted.
        re.compile(r"login_entry_allowed\s*:?[\s#]*false", re.IGNORECASE),
        # Prose forms naming the same fact without the field syntax.
        re.compile(r"ordinary login (?:path )?(?:still )?refuses",
                    re.IGNORECASE),
        re.compile(r"login door is shut", re.IGNORECASE),
        # ADDED LANE-A round 9ic0io (pf-adversary A2 on round ynfhoc, which
        # is where this gap was measured rather than guessed): in
        # lane_a_scene_census.py a composer that is "registered, never
        # fired" is a composer the admission check declines, which is the
        # same claim as a shut door said in this file's own vocabulary.
        # Two of these survived a strike-and-replace in round ynfhoc,
        # sitting in the same sentence as their own replacement, and the
        # three patterns above matched neither - so the case that round
        # widened could not see the contradiction it was widened to catch.
        # The phrase is deliberately NOT written anywhere in this file
        # outside this pattern: the sources scanned include the file this
        # pattern is written in only insofar as they are read from disk, but
        # the census file's own explanatory prose is scanned, so an
        # explanation that quotes the phrase would flag itself.  That is
        # exactly the trap the strike comments in lane_a_scene_census.py:303
        # and :329 had to be re-worded around.
        # WIDENED in the same round it was added (pf-adversary D8): the
        # first version was `registered,?\s*(?:but\s*)?never fired`, which
        # carried none of the tolerance the field-literal pattern above
        # documents as necessary - and this very commit measured that the
        # line-wrap-plus-hash shape occurs in the file this pattern scans.
        # Driven: the same false claim about scene 4 written across two
        # comment lines survived the narrow form and is caught by this one.
        # `fires` is included because the present tense says the same thing.
        re.compile(r"registered,?[\s#]*(?:but[\s#]*(?:has[\s#]*)?|and[\s#]*)?"
                    r"never[\s#]*fire[sd]", re.IGNORECASE),
    )

    @staticmethod
    def _struck_spans(source):
        """Character ranges between paired ``~~`` markers."""
        marks = []
        start = source.find("~~")
        while start != -1:
            marks.append(start)
            start = source.find("~~", start + 2)
        if len(marks) % 2:
            raise AssertionError(
                "odd number of ~~ markers: a strike is unclosed and every "
                "span below would be off by one")
        return [(marks[i], marks[i + 1]) for i in range(0, len(marks), 2)]

    # A door-shut claim that is only describing the FLIP itself ("FALSE ->
    # TRUE by PANYA-DECISION ...") is history, correctly stated, not a
    # claim the door is currently shut - measured: this exact shape
    # ("login_entry_allowed FALSE -> TRUE") appears four times in the
    # shipped registry as the "DOOR OPENED" sentence LANE-A round 9lv3fa
    # added, and none of the four is a stale claim.
    _DESCRIBES_A_FLIP = re.compile(r"\s*->\s*true", re.IGNORECASE)
    # A claim explicitly framed as "READ AT THE TIME" is ALREADY a past-
    # tense, historical statement, not a present-tense one - measured: scene
    # 4's own paragraph in world_scene_travel.py was already corrected this
    # way (round 949y62, striking "still reads" and inserting this phrase)
    # and a literal-string check cannot tell tense apart from the field name
    # it is quoting, so this is checked explicitly rather than re-flagging
    # an already-fixed sentence.
    _DESCRIBES_THE_PAST = re.compile(r"at the time\s*[`\"']*\s*$",
                                      re.IGNORECASE)

    @classmethod
    def _named_scenes_by_prose(cls, window):
        """``scene 126`` / ``Scene 126`` - the two .py files' own style."""
        return {int(n) for n in re.findall(r"[Ss]cene (\d+)", window)}

    @classmethod
    def _named_scene_by_n_id(cls, source, at):
        """Which destination a JSON claim is about.

        PREFERS AN EXPLICIT ``scene N`` MENTION close before the match,
        because a claim in this registry routinely names a scene that is
        not the object it is sitting inside.
        ~~measured: destination 997's own status text quotes "scene 14 is
        pinned with login_entry_allowed FALSE" verbatim~~ -- STRUCK,
        MEASURED FALSE, LANE-A round 9ic0io (pf-adversary A1 on round
        ynfhoc).  What is actually there, re-derived by locating the string
        in the file and asking `json` which container holds it: the sentence
        is in the registry's TOP-LEVEL ``nonclaims`` array (index 12, and
        struck there since round ynfhoc), not in destination 997's status
        text - 997's own status reads
        ``never_sent_to_any_client_by_this_project``.

        THE EXAMPLE STILL HOLDS, and is in fact the sharper one: the nearest
        preceding ``"n_id"`` before that sentence IS 997, because the
        nonclaims array is written after the destinations, so the n_id
        fallback below would hand this claim to 997 - a destination the
        sentence has nothing to do with.  That is the misattribution the
        explicit-number branch exists to prevent, and it is a file-level
        claim being pulled into the last destination's object rather than
        one destination's prose being pulled into another's.

        THE "OTHER" WORD WINS OVER AN EXPLICIT NUMBER, CHECKED FIRST AND IN
        A WIDE ENOUGH WINDOW TO REACH ONE - a real, observed shape in this
        registry names the scene that opened ("Scene 4 ... is the first of
        these ten to open ...") in the SAME sentence group as a claim about
        every OTHER one of the ten ("the other nine are UNCHANGED ... still
        carry login_entry_allowed false").  A narrow window that only
        checked for "other" right next to the match would miss that the
        explicit "scene 4" a few dozen characters earlier belongs to the
        PREVIOUS clause, not this one - so "other" is checked in the SAME
        150-character window used for the explicit-number search, and wins
        when both are present, rather than letting an antecedent "scene N"
        from an unrelated clause outrank it.

        FALLS BACK to the nearest preceding ``"n_id": N`` - a claim written
        as "this scene" (no explicit number, no "other") means its own
        container.
        """
        window = source[max(0, at - 150):at]
        if re.search(r"\bother\b", window, re.IGNORECASE):
            return set()
        explicit = {int(n) for n in re.findall(r"[Ss]cene (\d+)", window)}
        if explicit:
            return explicit
        matches = list(re.finditer(r'"n_id"\s*:\s*(\d+)', source[:at]))
        if not matches:
            return set()
        return {int(matches[-1].group(1))}

    @classmethod
    def _offenders(cls, source, open_doors, *, attribute_by_n_id):
        """Lines carrying an unstruck claim about a scene that is OPEN."""
        spans = cls._struck_spans(source)
        found = []
        for pattern in cls.DOOR_SHUT_PATTERNS:
            for match in pattern.finditer(source):
                at = match.start()
                if any(lo < at < hi for lo, hi in spans):
                    continue
                tail = source[match.end():match.end() + 12]
                if cls._DESCRIBES_A_FLIP.match(tail):
                    continue
                head = source[max(0, at - 40):at]
                if cls._DESCRIBES_THE_PAST.search(head):
                    continue
                if attribute_by_n_id:
                    named = cls._named_scene_by_n_id(source, at)
                else:
                    window = source[max(0, at - 900):at]
                    named = cls._named_scenes_by_prose(window)
                wrong = sorted(named & open_doors)
                if wrong:
                    found.append(
                        (source.count("\n", 0, at) + 1, wrong,
                         match.group(0)))
        return found

    def test_no_unstruck_comment_says_a_door_the_registry_opened_is_shut(self):
        registry = world_scene_travel.load_scene_registry()
        open_doors = {
            d.n_id for d in registry.destinations if d.login_entry_allowed
        }
        self.assertTrue(open_doors, "no door is open, so this proves nothing")
        for label, source, by_n_id in (
            ("world_scene_travel.py", self.TRAVEL_SOURCE, False),
            ("lane_hooks/lane_a_scene_census.py", self.CENSUS_SOURCE, False),
            ("scenarios/world_scene_registry_001.json",
             self.REGISTRY_SOURCE, True),
        ):
            with self.subTest(file=label):
                self.assertEqual(
                    self._offenders(source, open_doors,
                                     attribute_by_n_id=by_n_id),
                    [],
                    "these lines of %s say a login door is shut for a "
                    "scene this registry has OPEN. Strike them (~~...~~) "
                    "rather than deleting them - the record of who "
                    "believed what is the point of the convention."
                    % (label,))

    def test_a_sentence_about_a_door_that_is_really_shut_is_left_alone(self):
        """The case above must not become a blanket ban on the string.

        Driven on a synthetic source rather than on this module, because the
        shipped registry has no shut door today and a case that could only
        run when one appears is a case nobody would notice had stopped
        measuring anything.
        """
        true_sentence = (
            "# scene 4242 is registered but not reachable: its row reads\n"
            "# ``login_entry_allowed: false`` and nothing here changes it.\n"
        )
        self.assertEqual(
            self._offenders(true_sentence, {1, 2, 17},
                             attribute_by_n_id=False),
            [],
            "a TRUE unstruck sentence about a genuinely shut scene was "
            "reported as a defect")
        self.assertEqual(
            [line for line, _, _ in self._offenders(
                true_sentence, {4242}, attribute_by_n_id=False)],
            [2],
            "the same sentence about a scene that is OPEN must be reported")

    def test_an_unclosed_strike_is_a_failure_and_not_a_free_pass(self):
        """An odd number of ``~~`` markers would shift every span by one and
        silently turn real offenders into "struck" text, which is the shape
        of check that passes forever while measuring nothing.
        """
        with self.assertRaises(AssertionError):
            self._struck_spans("# ~~one marker only\n")


class NoCommentClaimsAStaleRosterFactForScene17(unittest.TestCase):
    """pf-adversary addendum on the sibling branch (B3), one specific claim
    the door-shape check above cannot see because it is not about a door:
    scene 17's registry ``status`` field says (as of the round that wrote
    it) that ``world_population_handoff.ROSTER_COMPOSERS`` has no entry for
    ``bg1001_roster`` and that ``PENDING_CROSSING_SAFETY_REVIEW`` still
    names it.  Both are checked live against the module rather than assumed
    stale, so this stays true the day either one is reverted.
    """

    def test_scene_17_roster_composer_claim_matches_the_module(self):
        from pirateforce_foundation import world_population_handoff

        registry_text = Path(world_scene_travel.REGISTRY_PATH).read_text(
            encoding="utf-8")
        registered = "bg1001_roster" in world_population_handoff.ROSTER_COMPOSERS
        still_pending = (
            "bg1001_roster" in world_population_handoff
            .PENDING_CROSSING_SAFETY_REVIEW
        )
        if not (registered and not still_pending):
            return  # Nothing to check against - the module state reverted.
        claim = "ROSTER_COMPOSERS deliberately has no entry"
        spans = NoCommentClaimsADoorThisRegistryOpened._struck_spans(
            registry_text)
        at = registry_text.find(claim)
        while at != -1:
            struck = any(lo < at < hi for lo, hi in spans)
            self.assertTrue(
                struck,
                "scene 17's status field still claims (unstruck) that "
                "ROSTER_COMPOSERS has no bg1001_roster entry, but the "
                "module registers one and PENDING_CROSSING_SAFETY_REVIEW "
                "no longer names it - the claim is stale.")
            at = registry_text.find(claim, at + 1)


class Scene304And305DoNotCarryADuplicateDoorClaim(unittest.TestCase):
    """pf-adversary addendum on the sibling branch (B3): scenes 304 and 305
    each had a claim about their own login door struck once, correctly -
    and then the SAME field went on to state the unstruck claim again
    later in the same string, contradicting its own already-struck and
    corrected sentence a few hundred characters earlier.  A reader who
    stopped at the second occurrence would believe the door was shut again.
    """

    def test_no_status_field_repeats_an_already_struck_door_claim(self):
        data = json.loads(
            Path(world_scene_travel.REGISTRY_PATH).read_text(
                encoding="utf-8"))
        registry = world_scene_travel.load_scene_registry()
        open_doors = {
            d.n_id for d in registry.destinations if d.login_entry_allowed
        }
        pattern = re.compile(
            r"login_entry_allowed\s*:?[\s#]*false", re.IGNORECASE)
        for row in data["destinations"]:
            if row["n_id"] not in open_doors:
                continue
            status = row.get("status", "")
            if not status:
                continue
            spans = (
                NoCommentClaimsADoorThisRegistryOpened._struck_spans(status)
            )
            flip = NoCommentClaimsADoorThisRegistryOpened._DESCRIBES_A_FLIP
            unstruck = [
                m for m in pattern.finditer(status)
                if not any(lo < m.start() < hi for lo, hi in spans)
                and not flip.match(status[m.end():m.end() + 12])
            ]
            self.assertEqual(
                unstruck, [],
                "scene %s's status field repeats an unstruck door-shut "
                "claim (possibly a duplicate of an already-struck one "
                "earlier in the same field) for a scene this registry has "
                "OPEN: %r" % (
                    row["n_id"], [m.group(0) for m in unstruck]))


class ReturnTicketTests(unittest.TestCase):
    """A scene a character cannot leave is not a feature, it is damage.

    Row 278 carries n_MARKER = 0 (no authored arrival point) and n_SAVE = 0,
    and no transition sequence is known, so the way back has to be part of the
    same delivery as the way there.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_scene_registry()

    def test_the_test_stage_declares_that_it_owes_a_return_ticket(self):
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        self.assertFalse(stage.has_authored_entry)
        self.assertFalse(stage.persists_characters)
        self.assertTrue(entry_report(stage)["needs_return_ticket"])
        self.assertIn("return_ticket=REQUIRED", entry_console_line(stage))

    def test_the_authored_measured_scenes_do_not(self):
        # UPDATED 2026-09-05 (COO-DECISION 20260905_0251, LANE-A): the
        # expanded `MEASURED_SCENE_IDS` is no longer "every measured scene
        # owes no return ticket" -- the COO's own ruling item (c) says the
        # two ideas do not have to march together ("scenes reached by
        # whatever door the client actually drew count the same" for
        # `sent_before`, independent of the table's save/marker columns).
        # Scene 126 (Atlantis, the ocean panel) is measured -- a client HAS
        # rendered it -- but its own table row carries n_SAVE=0/n_MARKER=0,
        # same as the unmeasured test stage, because this server's login
        # door into it stays shut (see `ATLANTIS_OCEAN_PANEL_SCENE_ID`).  So
        # this test asserts the return-ticket claim for the scenes that
        # actually authored one, and asserts 126 is the measured exception
        # rather than silently dropping it from the loop.
        no_return_ticket_owed = tuple(
            n_id for n_id in MEASURED_SCENE_IDS if n_id != 126
        )
        self.assertEqual(no_return_ticket_owed, (1, 2, 3, 4, 5, 14))
        for measured in no_return_ticket_owed:
            target = destination(measured, self.registry)
            self.assertTrue(target.has_authored_entry)
            self.assertTrue(target.persists_characters)
            self.assertIn("return_ticket=not_needed", entry_console_line(target))

    def test_the_measured_ocean_panel_still_owes_a_return_ticket(self):
        # The one id in `MEASURED_SCENE_IDS` that is not also a no-return-
        # ticket destination: see the note on the test above.
        #
        # UPDATED 2026-09-05 (LANE-A round ihjytc).  Scene 126 gained an
        # owner-decreed arrival point this round (PANYA-DECISION
        # 20260905_1329), so ~~`has_authored_entry` is False~~ that property
        # now answers True for it -- and THE RETURN TICKET IS STILL OWED,
        # which is the whole reason this assertion was rewritten rather than
        # deleted.  A place to land is not a way back: n_SAVE is still 0 and
        # the login door is still shut, so a character warped here has no
        # in-game route home and whoever sends one owes it `home_return_
        # position`.  The report reads `has_table_authored_entry` for exactly
        # this reason; if a later round makes the two march together again,
        # this test is where that has to be argued.
        atlantis = destination(126, self.registry)
        self.assertTrue(atlantis.sent_before)
        self.assertFalse(atlantis.has_table_authored_entry)
        self.assertTrue(atlantis.has_decreed_arrival)
        self.assertTrue(atlantis.has_authored_entry)
        self.assertFalse(atlantis.persists_characters)
        self.assertTrue(entry_report(atlantis)["needs_return_ticket"])
        self.assertIn("return_ticket=REQUIRED", entry_console_line(atlantis))

    def test_the_way_home_is_a_row_that_can_be_written_back(self):
        home = home_return_position(self.registry)
        self.assertEqual((home.scene_id, home.scene_seq), (1, 0))
        # the V135 spawn - where this runtime stands a fresh character today
        self.assertEqual(home.x, -9239.95703125)
        self.assertEqual(home.y, -2830.045166015625)
        self.assertEqual(home.z, 223.29209899902344)

    def test_the_columns_that_carry_the_warning_are_pinned_for_every_scene(self):
        # D2: nine table columns separate 278 from both measured scenes.  The
        # four that decide anything are on the destination itself, so a reader
        # of the console line cannot miss them.
        stage = destination(TEST_STAGE_SCENE_ID, self.registry)
        self.assertEqual(
            (stage.save_flag, stage.entry_marker, stage.camera_type,
             stage.limit_height), (0, 0, 0, 0))
        home = destination(HOME_SCENE_ID, self.registry)
        self.assertEqual(
            (home.save_flag, home.entry_marker, home.camera_type,
             home.limit_height), (1, 1, 1, 30000))

    def test_an_unmeasured_scene_is_reported_as_not_sent_before(self):
        # UPDATED 2026-09-05 (COO-DECISION 20260905_0251, LANE-A): widened
        # from `(1, 2)` -- see `MEASURED_SCENE_IDS`'s own per-id citations
        # for why each of these seven, and no others, is in the tuple.
        self.assertEqual(
            world_scene_travel.MEASURED_SCENE_IDS, (1, 2, 3, 4, 5, 14, 126)
        )
        self.assertFalse(destination(TEST_STAGE_SCENE_ID, self.registry).sent_before)


class LoginTeleportTests(unittest.TestCase):
    """The wiring surface: five arguments, and a control that must not move."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_scene_registry()

    def test_home_reproduces_the_call_the_runtime_makes_today(self):
        # runtime.py:3675 calls make_login_teleport(1, 0), which defaults the
        # three coordinates to 0.0.  Wiring this function in must therefore be
        # a no-op for a player who stays home - that is the control, and it is
        # what makes the change safe to land before anybody has measured 278.
        self.assertEqual(
            login_teleport_fields(destination(HOME_SCENE_ID, self.registry)),
            (1, 0, 0.0, 0.0, 0.0),
        )

    def test_scene_two_reproduces_the_position_of_the_one_measured_pass(self):
        # SCENE-001 stood a live client on marker2 at scene 2.  If this
        # function cannot reproduce the arguments of the only non-home entry
        # this project has ever landed, it is not modelling entry correctly.
        self.assertEqual(
            login_teleport_fields(destination(2, self.registry)),
            (2, 0, 26905.0, 21185.0, 1680.0),
        )

    def test_the_test_stage_carries_its_own_spawn(self):
        scene_id, scene_seq, x, y, z = login_teleport_fields(
            destination(TEST_STAGE_SCENE_ID, self.registry))
        self.assertEqual((scene_id, scene_seq), (278, 0))
        self.assertEqual(
            (x, y, z), (-13270.0576171875, 22794.2734375, -2492.7685546875))
        self.assertGreater(scene_id, 0, "handler 0x5F14B0 rejects SceneID <= 0")

    def test_the_entry_position_is_a_row_the_store_would_accept(self):
        row = entry_position(destination(TEST_STAGE_SCENE_ID, self.registry))
        self.assertEqual(row.scene_id, 278)
        self.assertEqual(row.scene_seq, 0)
        self.assertEqual(row.heading, 0.0)
        # store.update_position bounds scene_id at 0..0xFFFF
        self.assertTrue(0 <= row.scene_id <= 0xFFFF)
        self.assertAlmostEqual(row.z, -2492.7685546875, places=9)

    def test_the_entry_position_refuses_a_heading_that_is_not_a_number(self):
        with self.assertRaises(ValueError):
            entry_position(destination(TEST_STAGE_SCENE_ID, self.registry), "0")


if __name__ == "__main__":
    unittest.main()
