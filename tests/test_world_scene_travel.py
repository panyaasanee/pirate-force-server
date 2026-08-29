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
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel
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
        """
        self.assertEqual(
            self.registry.ids, (1, 2, 14, 17, TEST_STAGE_SCENE_ID, 997))

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

    def test_scene_17_is_pinned_not_allowed_as_a_login_destination(self):
        """Round 0z3kjx, adversary-flagged: scene 17 stopped being a scene
        with no pinned spawn (round e0daaa's owner decree), which means the
        free login-time refusal that used to protect a stored/persisted row
        naming it (REFUSED_NO_PINNED_SPAWN) is gone. login_entry_allowed=False
        is what replaces it - see world_scene_entry.resolve_entry's via_login
        parameter for who checks this and tests/test_world_scene_entry.py for
        the login-path regression this field exists to prove."""
        sea = destination(17, self.registry)
        self.assertFalse(sea.login_entry_allowed)
        raw = [row for row in _raw()["destinations"] if row["n_id"] == 17][0]
        self.assertIs(raw["login_entry_allowed"], False)

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

    def test_scene_17_is_pinned_not_allowed_to_persist_position(self):
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
        sea = destination(17, self.registry)
        self.assertFalse(sea.persist_position_allowed)
        self.assertFalse(is_position_persist_allowed(17, self.registry))
        raw = [row for row in _raw()["destinations"] if row["n_id"] == 17][0]
        self.assertIs(raw["persist_position_allowed"], False)

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

    def test_the_two_measured_scenes_do_not(self):
        for measured in MEASURED_SCENE_IDS:
            target = destination(measured, self.registry)
            self.assertTrue(target.has_authored_entry)
            self.assertTrue(target.persists_characters)
            self.assertIn("return_ticket=not_needed", entry_console_line(target))

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
        self.assertEqual(world_scene_travel.MEASURED_SCENE_IDS, (1, 2))
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
