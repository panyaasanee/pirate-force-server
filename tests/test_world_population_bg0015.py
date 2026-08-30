"""LANE-A M3: Bg0015's census, on the real frozen serializers.

The wire/DB half of the two-layer evidence rule for this scene.  What this
file can prove without a client: the collection header count equals the
number of bodies actually in the frame (the failure that produces
``ErrorData=28317``), every entry carries a real ``MOBS.n_ID`` rather than a
Mob-Set number, the builder refuses every scene but 14, and the console lines
a headless boot would print say the true numbers including the shortfall.

What it cannot prove, and does not: that a client draws any of it.  Nobody
has been in this scene.  ``GT-134`` is that ticket.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg0015_identity as identity  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0015 as census  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
ANCHOR = (10607.7216796875, 2047.006103515625, 4600.40234375)


class Bg0015Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)

    def _build(self, **kwargs):
        return census.build_bg0015_population(
            self.legacy, ANCHOR, scene_id=census.SCENE_N_ID,
            count_source=census.COUNT_SOURCE_FULL_ROSTER, **kwargs)

    def test_the_whole_roster_assembles(self) -> None:
        generation = self._build()
        self.assertEqual(generation.actor_count, 81)
        self.assertEqual(len(generation.placement_indices), 81)
        self.assertEqual(len(generation.n_ids), 81)

    def test_header_count_equals_the_bodies_in_the_frame(self) -> None:
        # The 28317 failure, checked directly rather than trusted.
        for count in (1, 7, 40, 81):
            with self.subTest(count=count):
                generation = census.build_bg0015_population(
                    self.legacy, ANCHOR, count, scene_id=census.SCENE_N_ID)
                report = census.dispatch_report(generation)
                self.assertEqual(report["wire_actor_count"], count)
                self.assertEqual(report["assembled_count"], count)
                self.assertTrue(report["counts_agree"])
                self.assertTrue(report["bodies_intact"])
                self.assertEqual(
                    report["body_bytes"], report["entry_bytes_total"])

    def test_every_entry_carries_a_real_mobs_n_id_ON_THE_WIRE(self) -> None:
        """The GT-078 regression, checked in the BYTES that go out.

        The first draft of this test read ``generation.n_ids`` -- a Python
        dataclass field built from the same placement objects the encoder
        reads.  pf-adversary changed ``placement.n_id`` to
        ``placement.template_id`` in ``_entry`` (putting the Mob-Set number
        back in make_npc_attr's template u16 at +0x78, the exact thing the
        owner rejected on sight) and all twelve tests in this file stayed
        green.  This is the sibling check ``test_world_population.py``
        already does properly for bg0001, brought over: NPCAttr writes the
        identity as ``u8tag(0x0B, mask)`` then ``u16tag(0x12, n_id)``
        (v141:1196-1197), so it looks for that exact two-tag sequence rather
        than a bare u16 that any coincidental byte pair could match.
        """
        generation = self._build()
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        for index in generation.placement_indices:
            placement = placements[index]
            with self.subTest(placement=index):
                id_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.n_id)
                )
                set_number_tags = (
                    self.legacy.u8tag(0x0B, 0x01 | 0x04)
                    + self.legacy.u16tag(0x12, placement.template_id)
                )
                self.assertIn(id_tags, generation.pc)
                self.assertNotIn(set_number_tags, generation.pc)
                self.assertIn(
                    self.legacy.wstr_tag(placement.visual_preset),
                    generation.pc)
                self.assertIn(
                    self.legacy.wstr_tag(placement.display_name),
                    generation.pc)

    def test_nearest_first_order_puts_the_anchor_placement_first(self) -> None:
        generation = self._build()
        self.assertEqual(generation.placement_indices[0], 32)
        self.assertEqual(generation.display_names[0], "Hell King Kong")

    def test_it_refuses_every_scene_but_fourteen(self) -> None:
        for scene_id in (1, 2, 13, 15, 278, "14", None):
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(census.Bg0015CensusError):
                    census.build_bg0015_population(
                        self.legacy, ANCHOR, scene_id=scene_id)

    def test_it_refuses_a_bad_anchor_or_count(self) -> None:
        for anchor in ((1.0, 2.0), [1.0, 2.0, 3.0], (1.0, 2.0, float("nan"))):
            with self.subTest(anchor=anchor):
                with self.assertRaises(census.Bg0015CensusError):
                    census.build_bg0015_population(
                        self.legacy, anchor, scene_id=census.SCENE_N_ID)
        for count in (0, -1, 82, True, 3.0):
            with self.subTest(count=count):
                with self.assertRaises(census.Bg0015CensusError):
                    census.build_bg0015_population(
                        self.legacy, ANCHOR, count,
                        scene_id=census.SCENE_N_ID)

    def test_the_console_line_states_the_true_shortfall(self) -> None:
        line = census.census_console_line(self._build())
        self.assertTrue(line.isascii())
        self.assertIn("assembled=81/91", line)
        self.assertIn("shippable=81", line)
        self.assertIn("wire=81", line)
        self.assertIn("bodies=ok", line)
        self.assertIn("unresolved=10", line)
        self.assertIn("shortfall=identity_unresolved=10", line)
        # The 91 target is never quietly rewritten to 81 (CHARTER-02).
        self.assertNotIn("assembled=81/81", line)

    def test_a_caller_truncated_census_says_so_instead_of_blaming_identity(
        self,
    ) -> None:
        generation = census.build_bg0015_population(
            self.legacy, ANCHOR, 12, scene_id=census.SCENE_N_ID)
        report = census.dispatch_report(generation)
        self.assertEqual(report["shortfall_reason"], "caller_requested=12")

    def test_the_headless_lines_name_every_actor_and_every_drop(self) -> None:
        lines = census.census_console_lines(self.legacy, ANCHOR)
        self.assertEqual(len(lines), 1 + 81 + 10)
        self.assertTrue(all(line.isascii() for line in lines))
        self.assertTrue(lines[0].startswith("WORLD_CENSUS_BG0015 "))
        self.assertEqual(
            sum(1 for line in lines if line.startswith("BG0015_UNSHIPPED ")),
            10)
        self.assertIn("Hell Ghoul", "\n".join(lines))

    def test_the_wire_constants_are_imported_not_redefined(self) -> None:
        self.assertIs(census.WIRE_HEADER_BYTES, world_population.WIRE_HEADER_BYTES)
        self.assertIs(census.COLLECTION_TAG, world_population.COLLECTION_TAG)
        self.assertIs(census.INITIAL_REAPPLY_MS, world_population.INITIAL_REAPPLY_MS)

    def test_no_entry_carries_a_faction_bit(self) -> None:
        """Hostility is lane B's splice, not this module's.

        The first draft asserted ``b"\\x00\\x04" not in pc[:2]``, which
        pf-adversary showed is unconditionally true: a two-byte slice of the
        collection header can only contain that pair by BEING it, which the
        header format forbids.  It could not have failed for any entry
        payload.  What actually decides the question is the BasicAttr mask
        each NPCAttr body carries, so this counts the mask this module's own
        encoder emits and pins that the hostile bit (0x0400, the one GT-032's
        splice widens the mask by) is absent from every entry.
        """
        generation = self._build()
        placements = {p.placement_index: p
                      for p in identity.shippable_placements()}
        hostile_mask_bit = 0x0400
        for index in generation.placement_indices:
            placement = placements[index]
            body = self.legacy.make_npc_attr(
                placement.n_id, placement.actor_identity,
                census.SCENE_N_ID, census.SCENE_SEQUENCE,
                placement.visual_preset,
                current_hp=placement.max_hp, max_hp=placement.max_hp,
                basic_name=placement.display_name,
            )
            with self.subTest(placement=index):
                # The body this module built is byte-identical to a plain
                # make_npc_attr call: no splice, no widened mask, nothing
                # added between the encoder and the wire.
                self.assertIn(body, generation.pc)
                self.assertNotIn(
                    self.legacy.u16tag(0x12, hostile_mask_bit)
                    + self.legacy.u16tag(0x12, placement.n_id),
                    generation.pc)
        # And it is deterministic, which the old test did check.
        self.assertEqual(generation.pc, self._build().pc)

    def test_a_full_roster_label_cannot_be_put_on_a_truncated_census(
        self,
    ) -> None:
        # pf-adversary: count_source was a caller assertion the console line
        # reported as provenance -- five actors could print
        # "assembled=5/91 source=bg0015_full_roster".
        with self.assertRaises(census.Bg0015CensusError):
            census.build_bg0015_population(
                self.legacy, ANCHOR, 5, scene_id=census.SCENE_N_ID,
                count_source=census.COUNT_SOURCE_FULL_ROSTER)
        self.assertEqual(self._build().actor_count, census.ROSTER_COUNT)

    def test_only_the_population_seam_imports_this_module(self) -> None:
        # ~~test_nothing_under_src_imports_this_module_yet~~ -- renamed and
        # widened in round 80x5ba (LANE-A), deliberately and in the same round
        # as the change that made it fail, which is exactly the protocol the
        # original comment demanded:
        #
        #     "the day runtime.py gains the scene-14 branch this test is the
        #      one that has to be updated, deliberately, in the same round --
        #      so 'wired' can never happen silently."
        #
        # WHAT CHANGED, AND WHAT DID NOT.  ``world_population_handoff`` now
        # imports this module, because the arrival seam composes THIS roster
        # for a scene-14 arrival instead of sending an empty collection to a
        # map this lane had already populated.  What has NOT changed is the
        # handback this test exists for: ``runtime.py`` still does not import
        # the seam, so no player reaches this roster yet.  The assertion is
        # therefore an EXACT SET, not a "contains" - a third importer, or the
        # seam being swapped for a direct runtime.py import, both fail here
        # and have to be argued for in a round of their own.
        #
        # An AST walk, not a text search: this module's NAME appears in
        # sibling docstrings on purpose (world_bg0015_identity points at it),
        # and a grep would call that wiring.
        import ast

        importers = []
        for path in (ROOT / "src").rglob("*.py"):
            if path.name == "world_population_bg0015.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                    if node.module:
                        names.append(node.module)
                if any("world_population_bg0015" in name for name in names):
                    importers.append(path.name)
                    break
        # UPDATED DELIBERATELY IN THE ROUND THAT WIRED IT, WHICH IS WHAT THE
        # PARAGRAPH ABOVE ASKED FOR (round ga91m5-r2).  The second importer is
        # `lane_hooks/lane_a_scene_census.py`, this lane's own composer file,
        # registered against the per-scene census point chief built in round
        # 73fhoc.  It reads this module only for its console readers
        # (census_console_line / actor_lines / unresolved_lines) and takes the
        # roster itself from the seam, so the seam is still the one composer.
        # Still an EXACT SET: a third importer has to be argued for in a round
        # of its own.
        self.assertEqual(
            sorted(importers),
            ["lane_a_scene_census.py", "world_population_handoff.py"])

        # ~~self.assertNotIn("runtime.py", importers)~~
        # ~~self.assertNotIn("world_population_handoff", runtime_source)~~
        #
        # BOTH STRUCK LINES WERE DEFEATED, MEASURED (pf-adversary, round
        # 80x5ba, D1).  They guarded the one route lane A cannot take - a
        # direct edit to runtime.py, which is chief's file - and left open the
        # route lane A CAN take alone: runtime.py:10 already imports
        # columbus_quest_dispatch, which already imports the seam at module
        # scope, and runtime.py already CALLS into that module on the M2
        # crossing.  The adversary appended two lines to
        # columbus_quest_dispatch that composed and printed a scene-14 handoff
        # on the live path, and the entire suite stayed green: neither struck
        # assertion fired, because runtime.py's own text never changed.  The
        # first was also dead on its own terms - it cannot fail if the exact
        # importer set above passed.
        #
        # The property the handback actually claims is about CALLS, not
        # imports, so that is what is asserted now: nothing under src/ calls
        # either entry point of the seam.  This one fails against the
        # adversary's own wiring.
        # ALIAS-RESOLVING, NOT NAME-MATCHING (pf-adversary, round ga91m5-r2,
        # D1).  The previous version matched the identifier at the call, so
        # `from .world_population_handoff import handoff_for_arrival as
        # _arrive` followed by `_arrive(...)` walked straight past it -
        # measured, in columbus_quest_dispatch.py, a file runtime.py already
        # imports and calls on the live path, with the whole suite green.
        # Every local name bound to an entry point is collected first, then
        # calls are matched against that set as well as against the
        # attribute form.
        entry_points = {"handoff_for_arrival", "handoff_on_crossing"}
        call_sites = []
        for path in (ROOT / "src").rglob("*.py"):
            # The seam's own file is excluded: handoff_on_crossing calls
            # handoff_for_arrival, which is the module wrapping itself in its
            # fail-closed contract, not a caller reaching the roster.
            if path.name == "world_population_handoff.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            local_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in entry_points:
                            local_names.add(alias.asname or alias.name)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute):
                    name = func.attr
                elif isinstance(func, ast.Name):
                    name = func.id
                else:
                    name = None
                if name in entry_points or name in local_names:
                    call_sites.append("%s:%d" % (path.name, node.lineno))
        # ~~self.assertEqual(call_sites, [], ...)~~ -- THE EMPTY SET WAS THE
        # RIGHT ASSERTION FOR EXACTLY ONE ROUND, AND THIS IS THE ROUND THAT
        # SPENDS IT (ga91m5-r2).  The seam now has exactly one caller under
        # src/: lane_hooks/lane_a_scene_census.py, the composer this lane
        # registered against chief's per-scene census point.  Asserting the
        # exact FILE rather than the count records WHERE the wiring that was
        # the point of three rounds actually lives.
        #
        # WHAT THIS ASSERTION IS NOT, STATED BECAUSE AN EARLIER VERSION OF
        # THIS COMMENT CLAIMED IT (pf-adversary, round ga91m5-r2, D1).  It is
        # NOT a containment guarantee that "nothing reaches this roster
        # except through a file this lane owns".  A static scan of one
        # module's call syntax cannot make that claim: the adversary reached
        # the roster twice without tripping it, once through an aliased
        # import (now resolved above) and once by calling this lane's own
        # composer factory from another file, which names neither the seam
        # nor this module's roster.  What actually contains the roster is the
        # ADMISSION CHECK in lane_hooks/lane_a_scene_census.py - it declines
        # for any scene the registry does not declare open, on every route
        # including those two - and it is driven in
        # tests/test_lane_a_scene_census.py, class
        # TheAdmissionCheckIsTheGateTests.  This assertion's job is smaller
        # and worth keeping: a new seam caller appearing under src/ is a
        # change somebody should have to write a sentence about.
        # THE SECOND CALLER, ARGUED FOR AS THIS COMMENT DEMANDS (round
        # t7t5yd, chief, carrying out COO-DECISION 20260829_2254): runtime.py
        # now calls handoff_on_crossing from the crossing-commit block --
        # the ONLY entry point whose contract never raises -- queues the
        # frame in the slot the handoff names, and applies MembershipReset.
        # Sorted WITH duplicates, not a set (pf-adversary R235, D3: the set
        # form let a rogue SECOND call site inside an already-blessed file
        # pass unseen -- exactly the double-populator shape COO-DECISION
        # 20260829_2245 bans).  One call site per blessed file; a second
        # one anywhere fails here and has to be argued for in a round of
        # its own.
        # THE THIRD CALLER, ARGUED FOR AS THIS COMMENT DEMANDS (LANE-A, the
        # M2 crossing-handoff round): world_m2_crossing_handoff.py composes
        # the handoff the ONE crossing a player can actually take today owes
        # -- Columbus, row 3021, scene 17 -- which runtime.py's Columbus
        # branch has never asked the seam for (RE-162 Job 4 found the same
        # gap independently).  IT REACHES NO PLAYER YET AND THAT IS WHY IT IS
        # ADMISSIBLE HERE ON A LANE-A ROUND: the call composes bytes for a
        # console line and returns them to a caller that queues nothing, so
        # it adds no route to this roster.  It cannot reach this roster in
        # particular by construction: scene 17 is in
        # SCENES_INTENTIONALLY_UNPOPULATED, so its answer is a CLEAR, and the
        # dispatch's destination is a constant.  When the chief's block
        # starts queueing those bytes, the route that appears is a CLEAR into
        # scene 17, not a bg0015 roster -- but this census should still be
        # re-argued in that round rather than inherited from this sentence.
        #
        # ONE PER FILE STILL HOLDS, and it was checked by breaking it: the
        # first draft of crossing_handoff called the seam once per branch and
        # this assertion caught it (two 'world_m2_crossing_handoff.py'
        # entries).  It was collapsed to a single call rather than the rule
        # widened.
        self.assertEqual(
            sorted(site.split(":")[0] for site in call_sites),
            [
                "lane_a_scene_census.py",
                "runtime.py",
                "world_m2_crossing_handoff.py",
            ],
            "the arrival seam's call sites under src/ changed -- this "
            "roster reaches players through ONE call in the lane-owned "
            "census file and ONE in the chief-owned crossing block, plus "
            "ONE compose-only call in the lane-owned M2 crossing report: %r"
            % (call_sites,),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
