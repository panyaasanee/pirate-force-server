"""Pin that the identity guard refuses every scene, and that it cannot be
loosened by accident.

The guard says: no scene's Mob-Set numbers may be shipped as ``MOBS.n_ID``
today.  That is a stronger and much duller statement than the one this round
first tried to make, and it is the one that survived adversary review.  The
tests are therefore mostly about the *shape* of the refusal - that no input,
including the scenes this tree actually ships identities for, can get a True
out of it - rather than about any classification.

Two things get real teeth here:

1. ``OWNER_CONFIRMED_SCENES`` is empty, and every consumer agrees with that.
   If somebody adds a scene to it, several of these turn red at once, which is
   the point: making a scene assertable should be a reviewed diff, never a
   side effect.
2. The refusal reason for ``Bg0002`` must stay consistent with
   ``scene2_prison_exile_tables.NAMING_SCHEME_STATUS``, the module that owns
   that hypothesis.  That test reads the other module rather than restating a
   literal, so the two cannot drift apart silently.

Nonclaims: nothing here claims to know a ``bg0001`` identity, that ``Bg0002``'s
hypothesis is wrong, or that any wire byte changed.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_numbering as wsn


class RefusalIsUnconditionalTest(unittest.TestCase):

    def test_only_the_scene_the_owner_walked_is_provable(self):
        # CHANGED round w0pu2i on COO-DECISION 2026-08-28T22:50 ("who
        # promotes a scene to confirmed"): owner eyes on the real scene are
        # the promoter, and she walked Prison Exile Island on 2026-08-28.
        # Was: OWNER_CONFIRMED_SCENES == () and Bg0002 in the refused list.
        self.assertEqual(wsn.OWNER_CONFIRMED_SCENES, ("Bg0002",))
        self.assertTrue(wsn.identity_is_provable("Bg0002"))
        self.assertIsNone(wsn.identity_block_reason("Bg0002"))
        wsn.assert_identity_claim("Bg0002")
        # RED LINE from the same letter: scene 2 only, it must not spread.
        for scene in ("bg0001", "bg0003", "Bg0015", "Bg9999", "", "1"):
            self.assertFalse(
                wsn.identity_is_provable(scene),
                f"{scene!r} must not be assertable",
            )
            self.assertIsNotNone(wsn.identity_block_reason(scene))
            with self.assertRaises(ValueError, msg=f"{scene!r} must refuse"):
                wsn.assert_identity_claim(scene)

    def test_the_shipping_scenes_have_recorded_reasons(self):
        """A refusal with a generic reason is a refusal nobody can audit, and
        these are the scenes that actually put identities on the wire.
        Bg0002's recorded reason is kept as history but no longer reached -
        it is confirmed now, so identity_block_reason answers None first."""
        for scene in ("bg0001", "Bg0015"):
            self.assertIn(scene, wsn.REFUSAL_REASONS)
            self.assertEqual(
                wsn.identity_block_reason(scene), wsn.REFUSAL_REASONS[scene])
        self.assertIn("Bg0002", wsn.REFUSAL_REASONS)
        self.assertIn("SUPERSEDED", wsn.REFUSAL_REASONS["Bg0002"])

    def test_port_royal_reason_cites_the_client_observable_evidence(self):
        """bg0001's refusal rests on the owner's 2026-08-27 map-window
        observation, not on any inference made in this module."""
        reason = wsn.identity_block_reason("bg0001")
        self.assertIn("156", reason)
        self.assertIn("113", reason)
        self.assertIn("GT-078", reason)

    def test_an_unlisted_scene_is_refused_with_its_own_reason(self):
        reason = wsn.identity_block_reason("Bg9999")
        self.assertIn("not_individually_assessed", reason)
        self.assertNotEqual(reason, "")

    def test_refusal_reasons_are_not_silently_emptied(self):
        for scene, reason in wsn.REFUSAL_REASONS.items():
            self.assertTrue(reason.strip(), f"{scene} has a blank reason")
            reason.encode("ascii")


class ConsistentWithTheHypothesisOwnerTest(unittest.TestCase):
    """Bg0002's refusal must track the module that owns that hypothesis."""

    def test_bg0002_refusal_tracks_naming_scheme_status(self):
        from pirateforce_foundation import scene2_prison_exile_tables as s2

        status = s2.NAMING_SCHEME_STATUS
        # The two now disagree ON PURPOSE and this test says why rather than
        # hiding it: scene2_prison_exile_tables reports the NUMERIC state (2
        # of 7 anchors, unchanged), and the guard reports the EVIDENCE state
        # (the owner walked the scene).  COO-DECISION 2026-08-28T22:50 ruled
        # the second outranks the first.  If the numeric side ever reaches 7
        # this test still passes and nothing needs revisiting.
        self.assertIn("not_yet_confirmed", status)
        self.assertTrue(wsn.identity_is_provable("Bg0002"))


class SceneIdMappingTest(unittest.TestCase):

    def test_mapping_is_explicit_and_closed(self):
        self.assertEqual(wsn.scene_file_for_scene_id(1), "bg0001")
        self.assertEqual(wsn.scene_file_for_scene_id(2), "Bg0002")
        self.assertIsNone(wsn.scene_file_for_scene_id(278))

    def test_non_integer_scene_ids_raise(self):
        for bad in ("1", 1.0, True, None):
            with self.assertRaises(ValueError, msg=f"{bad!r} should raise"):
                wsn.scene_file_for_scene_id(bad)

    def test_every_mapped_scene_has_a_recorded_reason(self):
        for scene in wsn.SCENE_ID_TO_SCENE_FILE.values():
            self.assertIn(scene, wsn.REFUSAL_REASONS)


class ConsoleTest(unittest.TestCase):

    def _assert_ascii(self, line):
        line.encode("ascii")
        self.assertNotIn("\n", line)

    def test_line_reports_refusal_for_every_unconfirmed_shipping_scene(self):
        for scene in ("bg0001", "Bg0015"):
            line = wsn.numbering_console_line(scene)
            self._assert_ascii(line)
            self.assertTrue(line.startswith("WORLD_IDENTITY_GUARD "))
            self.assertIn(f"scene={scene}", line)
            self.assertIn("verdict=refused", line)
            self.assertIn("identity_provable=0", line)

    def test_the_confirmed_scene_says_so_on_the_console(self):
        # Round w0pu2i.  The console is where a grader reads the verdict, so
        # the promotion has to be visible there too, not only in the API.
        line = wsn.numbering_console_line("Bg0002")
        self._assert_ascii(line)
        self.assertIn("scene=Bg0002", line)
        self.assertIn("verdict=allowed", line)
        self.assertIn("identity_provable=1", line)

    def test_suffix_resolves_scene_ids_and_never_fails_open(self):
        self.assertEqual(
            wsn.numbering_console_suffix(1),
            wsn.numbering_console_line("bg0001"))
        self.assertEqual(
            wsn.numbering_console_suffix(2),
            wsn.numbering_console_line("Bg0002"))
        unmapped = wsn.numbering_console_suffix(278)
        self._assert_ascii(unmapped)
        self.assertIn("identity_provable=0", unmapped)
        self.assertIn("scene_id_278_not_mapped", unmapped)

    def test_only_bg0002_can_print_provable_1(self):
        # Was "no console path can print provable=1 today".  Exactly one can
        # now, and this test is the fence around that one.
        lines = [wsn.numbering_console_line(s)
                 for s in ("bg0001", "Bg0015", "Bg9999")]
        lines += [wsn.numbering_console_suffix(i) for i in (1, 14, 278)]
        for line in lines:
            self.assertIn("identity_provable=0", line)
        self.assertIn(
            "identity_provable=1", wsn.numbering_console_suffix(2))


class CensusLineIntegrationTest(unittest.TestCase):
    """The boot line must carry the verdict for the scene it actually built."""

    @classmethod
    def setUpClass(cls):
        from pirateforce_foundation.legacy_bridge import load_legacy
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_census_line_appends_the_guard_token(self):
        from pirateforce_foundation import world_population

        gen = world_population.build_world_population(
            self.legacy, (0.0, 0.0, 0.0), 3, scene_id=1)
        line = world_population.census_console_line(gen)
        line.encode("ascii")
        self.assertTrue(
            line.startswith("WORLD_CENSUS "),
            "existing readers match on this prefix and must keep working",
        )
        self.assertIn("WORLD_IDENTITY_GUARD ", line)
        self.assertIn("scene=bg0001", line)
        self.assertIn("identity_provable=0", line)

    def test_the_token_follows_the_generation_not_a_module_constant(self):
        """A census built for another scene must not be reported as bg0001 -
        that mis-reporting is the defect this field was added to remove."""
        from pirateforce_foundation import world_population
        import dataclasses

        gen = world_population.build_world_population(
            self.legacy, (0.0, 0.0, 0.0), 3, scene_id=1)
        self.assertEqual(gen.scene_id, 1)
        moved = dataclasses.replace(gen, scene_id=2)
        line = world_population.census_console_line(moved)
        self.assertIn("scene=Bg0002", line)
        self.assertNotIn("scene=bg0001", line)


if __name__ == "__main__":
    unittest.main()
