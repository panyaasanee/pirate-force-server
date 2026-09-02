"""LANE-A's ChooseNPC responder for the roster islands (round `326kf4`).

WHAT THESE TESTS ARE FOR.  ``lane_hooks/lane_a_choose_npc_roster_scenes.py``
turns a click on scene 3's 62 actors from silence into an answered frame,
and REFUSES the nine sibling scenes whose placement tables collide with
Port Royal's Columbus index.  The evidence shape mirrors
``tests/test_lane_a_choose_npc_scene14.py`` -- drive ``respond()`` directly
with the real ``legacy`` seam and the real per-scene tables -- plus three
things a gated, multi-scene module needs that a single-scene one does not:

1. the gates are driven through ``_register_all`` and ``_skip_reason_for``
   -- the module's OWN code -- never re-implemented in a test body.  An
   earlier version of this file re-implemented the loop, and pf-adversary
   measured that deleting the refusal from the module left it green;
2. the spliced-source set is read out of ``world_population_handoff.py``
   with ``ast``, so a change of quote style or a line break inside the
   ``if`` cannot defeat it (both defeated the regex that came first);
3. the two wire constants are pinned against the FROZEN seam's own
   composer rather than against themselves, so a mutation to mask ``0x02``
   -- which ``v141:1078`` names by hand as client-breaking -- turns red.

NOT AN ATTENDED CLAIM.  Nothing here says a client renders the answer.
That is ``GT-210``; these tests measure the wire.
"""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_census_level  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_choose_npc_roster_scenes as responder_mod,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
QUALIFIED_MODULE = (
    "pirateforce_foundation.lane_hooks.lane_a_choose_npc_roster_scenes"
)
HANDOFF_SOURCE = (
    ROOT / "src" / "pirateforce_foundation" / "world_population_handoff.py"
)
MODULE_SOURCE = (
    ROOT / "src" / "pirateforce_foundation" / "lane_hooks"
    / "lane_a_choose_npc_roster_scenes.py"
)
# The scene this file serves TODAY, and the nine it deliberately does not.
# Written out rather than read from the module under test: a test that asks
# the module what it does can only ever agree with it.
EXPECTED_SCENES = (3,)
HELD_BACK_SCENES = (4, 5, 6, 7, 8, 9, 10, 11, 130)
COLUMBUS_REASON = (
    "columbus_placement_index_collision_needs_runtime_scene_guard"
)
# Scenes with a roster that must NOT be served from this module -- 1 and 14
# have their own responder files, 2 has no identity module of this family.
NOT_SERVED_HERE = (1, 2, 14)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _choose_npc_pc(legacy, *actor_ids):
    body = b"".join(
        legacy.u16tag(0x12, legacy.CHOOSE_NPC)
        + legacy.u8tag(0x0B, 0)
        + legacy.qwordtag(0x32, actor_id)
        for actor_id in actor_ids
    )
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, len(actor_ids))
        + body
    )


def _shut_registry(work: Path, scene_id: int):
    """A loaded registry with ONE scene's door shut, temp file only."""
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] == scene_id:
            row["login_entry_allowed"] = False
    path = work / f"registry_scene_{scene_id}_shut.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path)


def _splice_sources_in_the_handoff() -> set[str]:
    """Every string literal compared against ``composer.source`` in an
    ``if``/``elif`` test in ``world_population_handoff.py``.

    PARSED, NOT GREPPED.  The regex this replaced was line-anchored and
    double-quote-only; pf-adversary defeated it twice with one character
    (a single quote, and a newline after ``if (``), each time leaving a
    second live splice invisible to the gate that exists to catch it.  An
    AST walk sees the comparison wherever it is written and however it is
    quoted.
    """
    tree = ast.parse(HANDOFF_SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for compare in ast.walk(node.test):
            if not isinstance(compare, ast.Compare):
                continue
            left = compare.left
            if not (
                isinstance(left, ast.Attribute)
                and left.attr == "source"
                and isinstance(left.value, ast.Name)
                and left.value.id == "composer"
            ):
                continue
            for comparator in compare.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(
                    comparator.value, str
                ):
                    found.add(comparator.value)
    return found


class RegistrationTests(unittest.TestCase):
    """The gates registered what they say they registered, and nothing else."""

    def test_the_module_declares_production_allowed_true(self):
        self.assertIs(responder_mod.production_allowed, True)
        self.assertTrue(
            lane_hooks.module_production_allowed(QUALIFIED_MODULE))

    def test_the_served_scene_is_registered_to_this_module(self):
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                registered = lane_hooks.scene_choose_npc_responder(scene_id)
                self.assertIsNotNone(
                    registered, f"scene {scene_id} has no responder")
                self.assertEqual(registered.module, QUALIFIED_MODULE)

    def test_every_held_back_scene_has_no_responder_at_all(self):
        """The point of the gate: not merely 'not this module's' -- NO
        responder, so the census leaves membership withheld exactly as it
        did before this round."""
        for scene_id in HELD_BACK_SCENES:
            with self.subTest(scene=scene_id):
                self.assertIsNone(
                    lane_hooks.scene_choose_npc_responder(scene_id))

    def test_it_reports_the_scenes_it_holds_and_the_reasons_it_refused(self):
        self.assertEqual(
            responder_mod.scenes_this_lane_answers_for(), EXPECTED_SCENES)
        self.assertEqual(
            tuple(scene for scene, _ in responder_mod.skipped_scenes()),
            HELD_BACK_SCENES,
        )
        for _scene, reason in responder_mod.skipped_scenes():
            self.assertEqual(reason, COLUMBUS_REASON)

    def test_the_report_reads_the_registry_not_its_own_table(self):
        """pf-adversary D5: the first version subtracted ``_SKIPPED`` from
        the table and claimed in its own docstring to read the registry.
        Withdraw this module's registrations and the honest answer is
        'none' -- a subtraction would still say scene 3."""
        try:
            lane_hooks._withdraw(QUALIFIED_MODULE)
            self.assertEqual(responder_mod.scenes_this_lane_answers_for(), ())
        finally:
            responder_mod._register_all()
        self.assertEqual(
            responder_mod.scenes_this_lane_answers_for(), EXPECTED_SCENES)

    def test_it_does_not_claim_scenes_that_have_their_own_responder_file(self):
        for scene_id in NOT_SERVED_HERE:
            with self.subTest(scene=scene_id):
                registered = lane_hooks.scene_choose_npc_responder(scene_id)
                if registered is not None:
                    self.assertNotEqual(registered.module, QUALIFIED_MODULE)

    def test_every_table_scene_has_a_census_source_row(self):
        """A responder for a scene with no roster would arm membership for a
        census that never ships -- the two tables must agree."""
        for scene_id in responder_mod._IDENTITY_OF_SCENE:
            with self.subTest(scene=scene_id):
                self.assertIn(scene_id, world_scene_travel.CENSUS_SOURCES)


class TheColumbusCollisionGateTests(unittest.TestCase):
    """The gate that fires today -- see the module docstring.

    ``runtime.py``'s Columbus branch reads ``population_indices`` with no
    scene check, and actor identity carries no scene component, so arming
    that field for a scene holding a placement at
    ``COLUMBUS_PLACEMENT_INDEX`` makes Port Royal's quest reachable there.
    """

    def test_the_collision_is_computed_from_the_tables_not_hardcoded(self):
        collided = responder_mod._columbus_collision_scenes()
        self.assertEqual(sorted(collided), sorted(HELD_BACK_SCENES))
        for scene_id in HELD_BACK_SCENES:
            with self.subTest(scene=scene_id, expect="has index 1"):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                self.assertIn(
                    columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX,
                    {p.placement_index
                     for p in identity.shippable_placements()},
                )
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id, expect="no index 1"):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                self.assertNotIn(
                    columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX,
                    {p.placement_index
                     for p in identity.shippable_placements()},
                )

    def test_the_collision_actor_identity_really_is_columbus_own(self):
        """Why the index collision is a content collision: both resolve to
        the same actor identity on the wire."""
        legacy = _legacy()
        columbus = columbus_quest_dispatch.columbus_actor_identity(legacy)
        for scene_id in HELD_BACK_SCENES:
            with self.subTest(scene=scene_id):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                collider = next(
                    p for p in identity.shippable_placements()
                    if p.placement_index
                    == columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX
                )
                self.assertEqual(collider.actor_identity, columbus)

    def test_the_module_decides_the_skip_and_the_test_does_not(self):
        for scene_id in HELD_BACK_SCENES:
            with self.subTest(scene=scene_id):
                self.assertEqual(
                    responder_mod._skip_reason_for(scene_id), COLUMBUS_REASON)
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                self.assertIsNone(responder_mod._skip_reason_for(scene_id))


class TheSpliceGateTests(unittest.TestCase):
    """``_SPLICED_SOURCES`` versus the file it is a statement about.

    This responder rebuilds a roster from the identity table, so a scene
    whose ARRIVAL census is spliced over that table must not be answered
    from here or the click silently reverts the splice on the wire (the
    measured R274 defect).
    """

    def test_the_constant_matches_every_splice_branch_in_the_handoff(self):
        self.assertEqual(
            _splice_sources_in_the_handoff(),
            set(responder_mod._SPLICED_SOURCES),
            "world_population_handoff now compares composer.source against a "
            "different set of literals than lane_a_choose_npc_roster_scenes."
            "_SPLICED_SOURCES names.  Read THE SPLICE GATE in that module's "
            "docstring: a scene whose arrival census is spliced must not be "
            "answered by a responder that rebuilds from the identity table.",
        )

    def test_the_ast_reader_sees_a_splice_the_old_regex_missed(self):
        """pf-adversary D4, pinned so the reader cannot regress to a regex:
        single quotes and a line break after ``if (`` both hid a real
        second splice from the line-anchored pattern this replaced."""
        source = (
            "def _roster_handoff(legacy, scene, anchor, composer):\n"
            "    if (\n"
            "        composer.source == 'bg0009_roster'\n"
            "    ):\n"
            "        generation = splice(generation)\n"
            '    if composer.source == "bg0015_roster":\n'
            "        generation = splice(generation)\n"
        )
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "handoff_mutant.py"
            path.write_text(source, encoding="ascii")
            global HANDOFF_SOURCE
            original = HANDOFF_SOURCE
            try:
                HANDOFF_SOURCE = path
                self.assertEqual(
                    _splice_sources_in_the_handoff(),
                    {"bg0009_roster", "bg0015_roster"},
                )
            finally:
                HANDOFF_SOURCE = original

    def test_no_registered_scene_uses_a_spliced_source(self):
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                self.assertNotIn(
                    world_scene_travel.CENSUS_SOURCES[scene_id],
                    responder_mod._SPLICED_SOURCES,
                )

    def test_a_scene_whose_source_becomes_spliced_loses_its_responder(self):
        """Driven through ``_register_all`` itself -- deleting the refusal
        from the module must turn this red.  pf-adversary D3: the version
        of this test that re-implemented the loop in its own body stayed
        green when the module's refusal was deleted."""
        scene_id = EXPECTED_SCENES[0]
        source = world_scene_travel.CENSUS_SOURCES[scene_id]
        original = responder_mod._SPLICED_SOURCES
        try:
            responder_mod._SPLICED_SOURCES = frozenset({source})
            lane_hooks._withdraw(QUALIFIED_MODULE)
            responder_mod._register_all()
            self.assertIsNone(
                lane_hooks.scene_choose_npc_responder(scene_id),
                "the splice gate did not refuse a scene whose census source "
                "is spliced -- a click there would revert the splice",
            )
            self.assertEqual(
                dict(responder_mod.skipped_scenes())[scene_id],
                f"spliced_source_{source}",
            )
        finally:
            responder_mod._SPLICED_SOURCES = original
            lane_hooks._withdraw(QUALIFIED_MODULE)
            responder_mod._register_all()
        self.assertEqual(
            responder_mod.scenes_this_lane_answers_for(), EXPECTED_SCENES)

    def test_a_scene_with_no_census_row_loses_its_responder_too(self):
        """The third refusal reason, driven the same way rather than left
        as unreachable prose."""
        scene_id = EXPECTED_SCENES[0]
        original = dict(world_scene_travel.CENSUS_SOURCES)
        try:
            del world_scene_travel.CENSUS_SOURCES[scene_id]
            lane_hooks._withdraw(QUALIFIED_MODULE)
            responder_mod._register_all()
            self.assertIsNone(
                lane_hooks.scene_choose_npc_responder(scene_id))
            self.assertEqual(
                dict(responder_mod.skipped_scenes())[scene_id],
                "no_census_sources_row",
            )
        finally:
            world_scene_travel.CENSUS_SOURCES.clear()
            world_scene_travel.CENSUS_SOURCES.update(original)
            lane_hooks._withdraw(QUALIFIED_MODULE)
            responder_mod._register_all()
        self.assertEqual(
            responder_mod.scenes_this_lane_answers_for(), EXPECTED_SCENES)


class EverySceneStillHasItsOwnTableTests(unittest.TestCase):
    """The table is only safe if every row really is the same shape -- the
    held-back rows included, since a later round flips them on."""

    def test_each_identity_module_answers_for_the_scene_it_is_keyed_under(
        self,
    ):
        for scene_id, identity in responder_mod._IDENTITY_OF_SCENE.items():
            with self.subTest(scene=scene_id):
                self.assertEqual(identity.SCENE_N_ID, scene_id)

    def test_each_scenes_placements_carry_the_fields_the_encoder_needs(self):
        for scene_id, identity in responder_mod._IDENTITY_OF_SCENE.items():
            with self.subTest(scene=scene_id):
                placements = identity.shippable_placements()
                self.assertTrue(placements)
                one = placements[0]
                for field in (
                    "placement_index", "x", "y", "z", "n_id",
                    "actor_identity", "visual_preset", "display_name",
                    "max_hp",
                ):
                    self.assertTrue(
                        hasattr(one, field),
                        f"scene {scene_id} placement has no {field}",
                    )
                self.assertIsInstance(one.identity.level, int)

    def test_placement_indices_are_unique_within_each_scene(self):
        for scene_id, identity in responder_mod._IDENTITY_OF_SCENE.items():
            with self.subTest(scene=scene_id):
                indices = [
                    p.placement_index for p in identity.shippable_placements()
                ]
                self.assertEqual(len(indices), len(set(indices)))


class TheServedSceneAnswersAClickTests(unittest.TestCase):
    """The point of the round."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.scene_id = EXPECTED_SCENES[0]
        cls.identity = responder_mod._IDENTITY_OF_SCENE[cls.scene_id]

    def _answer(self, selected_position=0):
        placements = responder_mod._placements_by_index(self.identity)
        indices = tuple(sorted(placements))
        selected_idx = indices[selected_position]
        responder = lane_hooks.scene_choose_npc_responder(self.scene_id)
        answer = responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + selected_idx + 1,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        )
        return answer, selected_idx, indices, placements

    def test_a_click_is_answered(self):
        answer, selected_idx, indices, _ = self._answer()
        self.assertIsNotNone(answer)
        self.assertEqual(
            answer.label,
            f"LANE_A_CHOOSE_NPC_SCENE{self.scene_id}_FACE_P{selected_idx}",
        )
        self.assertTrue(answer.pc)
        self.assertTrue(answer.frame)
        self.assertEqual(answer.delay, 0.0)
        self.assertEqual(len(answer.console_lines), 1)
        line = answer.console_lines[0]
        self.assertIn(f"placement={selected_idx}", line)
        self.assertIn(f"visible={len(indices)}", line)
        self.assertIn("omitted=0", line)
        # cp874-encodable: the bridge console is cp874 and a line that
        # cannot be printed there is a line nobody can grep.
        line.encode("cp874")

    def test_every_actor_in_the_roster_can_be_the_clicked_one(self):
        placements = responder_mod._placements_by_index(self.identity)
        for position in range(len(placements)):
            answer, selected_idx, _, _ = self._answer(position)
            with self.subTest(placement=selected_idx):
                self.assertIsNotNone(answer)
                self.assertIn(f"_FACE_P{selected_idx}", answer.label)

    def test_the_frame_declares_the_whole_roster(self):
        """A header that declares more bodies than the payload carries is
        the client error (``ErrorData=28317``) this project has already paid
        for once -- read the count off the wire, never off the composer."""
        from pirateforce_foundation.world_population_handoff import (
            wire_count_of,
        )
        answer, _, indices, _ = self._answer()
        self.assertEqual(wire_count_of(answer.pc), len(indices))

    def test_the_answer_carries_the_level_the_arrival_census_carries(self):
        """The defect this project has now shipped twice: a rebuild through
        the BARE ``make_npc_attr`` drops the level splice, silently
        reverting round ``7ste68`` on the wire on the first click."""
        answer, _, _, placements = self._answer()
        placement = placements[min(placements)]
        leveled = world_census_level.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=self.scene_id,
            scene_sequence=0,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.identity.level,
        )
        bare = self.legacy.make_npc_attr(
            placement.n_id,
            placement.actor_identity,
            scene_id=self.scene_id,
            scene_seq=0,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
        )
        self.assertNotEqual(
            leveled, bare,
            "fixture drift: the leveled and bare encoders now agree, so this "
            "test can no longer tell them apart",
        )
        self.assertIn(leveled, answer.frame)
        self.assertNotIn(bare, answer.frame)

    def test_a_second_named_identity_is_tried_when_the_first_is_unknown(self):
        placements = responder_mod._placements_by_index(self.identity)
        indices = tuple(sorted(placements))
        good_idx = indices[0]
        responder = lane_hooks.scene_choose_npc_responder(self.scene_id)
        answer = responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + 999_999 + 1, 0x2000 + good_idx + 1),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        )
        self.assertIsNotNone(answer)
        self.assertIn(f"_FACE_P{good_idx}", answer.label)

    def test_a_real_wire_frame_drives_it_end_to_end(self):
        """No hand-built identity tuple: parse a real ChooseNPC frame with
        the frozen seam's own extractor, exactly as runtime.py does."""
        placements = responder_mod._placements_by_index(self.identity)
        indices = tuple(sorted(placements))
        actor_identity = 0x2000 + indices[0] + 1
        parsed = self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, actor_identity))
        chosen = self.legacy.extract_choose_npc_identities(parsed)
        self.assertEqual(chosen, [actor_identity])
        responder = lane_hooks.scene_choose_npc_responder(self.scene_id)
        self.assertIsNotNone(responder.respond(
            legacy=self.legacy,
            chosen_identities=tuple(chosen),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        ))


class TheWireShapesArePinnedAgainstTheFrozenSeamTests(unittest.TestCase):
    """pf-adversary D7: both wire constants were mutable to values this
    project documents as client-breaking with every test still green.

    They are pinned here against something OTHER than themselves: the
    frozen ``make_v98_conversation_face_state`` (v141:1076-1104), which is
    the shape this responder deliberately mirrors, and the arrival census
    frame, which carries the actor type.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.scene_id = EXPECTED_SCENES[0]
        cls.identity = responder_mod._IDENTITY_OF_SCENE[cls.scene_id]

    def test_the_face_mask_is_the_one_the_frozen_composer_uses(self):
        """``v141:1078`` names 0x02 by hand: "V95 proved that mask 0x02
        (heading only) makes the client apply an uninitialized/default
        position and teleport the NPC ... Never return to V95's mask
        0x02."  Read the mask the frozen composer actually writes rather
        than asserting this file's own constant back at itself."""
        legacy = self.legacy
        placements = responder_mod._placements_by_index(self.identity)
        placement = placements[min(placements)]
        heading = legacy._heading_to_player(
            placement.x, placement.y, 0.0, 0.0)
        ours = legacy.make_remote_movement_attr(
            placement.actor_identity,
            placement.x, placement.y, placement.z,
            heading, mask=responder_mod._FACE_MOVEMENT_MASK,
        )
        frozen = legacy.make_remote_movement_attr(
            placement.actor_identity,
            placement.x, placement.y, placement.z,
            heading, mask=0x03,
        )
        self.assertEqual(ours, frozen)
        heading_only = legacy.make_remote_movement_attr(
            placement.actor_identity,
            placement.x, placement.y, placement.z,
            heading, mask=0x02,
        )
        self.assertNotEqual(
            ours, heading_only,
            "fixture drift: masks 0x03 and 0x02 now encode identically, so "
            "this test can no longer catch the V95 regression",
        )

    def test_the_actor_type_is_the_one_the_arrival_census_shipped(self):
        """Pinned against the CENSUS FRAME, not against this file's own
        constant.

        pf-adversary D7: the first version of this test built both the
        expected and the rejected entry from ``_NPC_STYLE_ACTOR_TYPE``, so
        mutating the constant moved both and the test stayed green.  The
        arrival census composes its entries without reading anything in
        this module, so its bytes are an independent witness: the entry
        HEADER (``tag0B`` actor type + ``tag32`` identity, v141:1248-1260)
        that this responder emits must be the same header the census
        emitted for the same actor.
        """
        composer = lane_hooks.scene_census_composer(self.scene_id)
        composed = composer.compose(
            legacy=self.legacy, anchor=(0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        )
        self.assertIsNotNone(composed)
        placements = responder_mod._placements_by_index(self.identity)
        indices = tuple(sorted(placements))
        # A NON-selected actor: the selected one carries the face movement
        # attr, which the arrival census (full mask, per-index heading)
        # deliberately does not match.
        placement = placements[indices[1]]
        responder = lane_hooks.scene_choose_npc_responder(self.scene_id)
        answer = responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + indices[0] + 1,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        )
        header = (
            self.legacy.u8tag(0x0B, responder_mod._NPC_STYLE_ACTOR_TYPE)
            + self.legacy.qwordtag(0x32, placement.actor_identity)
        )
        self.assertIn(
            header, composed.frame,
            "the actor-entry header this responder emits is not the header "
            "this scene's own arrival census emitted for the same actor -- "
            "a client told one actor type at arrival and another on a click",
        )
        self.assertIn(header, answer.frame)
        # And the census really would have rejected a different type, so
        # the assertion above is a discriminator and not a tautology.
        wrong_header = (
            self.legacy.u8tag(0x0B, responder_mod._NPC_STYLE_ACTOR_TYPE + 1)
            + self.legacy.qwordtag(0x32, placement.actor_identity)
        )
        self.assertNotIn(wrong_header, composed.frame)


class ItDeclinesRatherThanGuessesTests(unittest.TestCase):
    """Every ordinary refusal is a ``None``, never an exception."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.scene_id = EXPECTED_SCENES[0]
        cls.responder = lane_hooks.scene_choose_npc_responder(cls.scene_id)

    def test_declines_when_membership_is_not_armed(self):
        self.assertIsNone(self.responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2001,),
            population_indices=None,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        ))

    def test_declines_when_no_target_position_is_known(self):
        """The first click after a warp: ``last_target_pos`` is None until
        the player moves once -- see the module docstring and GT-210."""
        self.assertIsNone(self.responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2001,),
            population_indices=(0,),
            last_target_pos=None,
            scene_id=self.scene_id,
        ))

    def test_declines_for_an_identity_outside_population_indices(self):
        self.assertIsNone(self.responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + 5 + 1,),
            population_indices=(1, 2, 3),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        ))

    def test_declines_for_a_scene_it_is_not_registered_for(self):
        """One island's crowd never answers for another's."""
        for other in HELD_BACK_SCENES:
            with self.subTest(other=other):
                self.assertIsNone(self.responder.respond(
                    legacy=self.legacy,
                    chosen_identities=(0x2001,),
                    population_indices=(0,),
                    last_target_pos=(0.0, 0.0, 0.0, 0.0),
                    scene_id=other,
                ))

    def test_fails_closed_on_a_placement_this_scenes_own_table_lacks(self):
        self.assertIsNone(self.responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + 999_999 + 1,),
            population_indices=(999_999,),
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=self.scene_id,
        ))

    def test_declines_when_the_registry_shuts_the_door(self):
        with tempfile.TemporaryDirectory() as work:
            raw = _shut_registry(Path(work), self.scene_id)
            identity = responder_mod._IDENTITY_OF_SCENE[self.scene_id]
            indices = tuple(sorted(
                responder_mod._placements_by_index(identity)))
            self.assertIsNone(self.responder.respond(
                legacy=self.legacy,
                chosen_identities=(0x2000 + indices[0] + 1,),
                population_indices=indices,
                last_target_pos=(0.0, 0.0, 0.0, 0.0),
                scene_id=self.scene_id,
                scene_entry_registry=raw,
            ))


class TheArrivalCensusMembershipTests(unittest.TestCase):
    """Registering a responder is ALSO what arms a scene's census
    membership, so this round changed the ARRIVAL path too -- for exactly
    one scene, and for none of the nine the gate holds back.  That is the
    property the round file and the letter to chief assert, so it is
    measured rather than reasoned."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _compose(self, scene_id):
        composer = lane_hooks.scene_census_composer(scene_id)
        self.assertIsNotNone(composer)
        return composer.compose(
            legacy=self.legacy, anchor=(0.0, 0.0, 0.0), scene_id=scene_id,
        )

    def test_the_served_scenes_census_now_carries_its_own_indices(self):
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                composed = self._compose(scene_id)
                self.assertIsNotNone(composed)
                self.assertIsNotNone(
                    composed.membership,
                    f"scene {scene_id} census still withholds membership, so "
                    "population_indices stays None and the click this round "
                    "added can never be reached",
                )
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                self.assertEqual(
                    sorted(composed.membership.population_indices),
                    sorted(responder_mod._placements_by_index(identity)),
                )

    def test_every_held_back_scenes_census_still_withholds_membership(self):
        """The regression this round refuses to ship: an armed
        ``population_indices`` on these scenes makes ``runtime.py``'s
        scene-blind Columbus branch reachable there."""
        for scene_id in HELD_BACK_SCENES:
            with self.subTest(scene=scene_id):
                composed = self._compose(scene_id)
                self.assertIsNotNone(composed)
                self.assertIsNone(
                    composed.membership,
                    f"scene {scene_id} census now arms membership -- the "
                    "Columbus placement-index collision is live again",
                )


class TheCountsThisRoundClaimsTests(unittest.TestCase):
    """The round file, the PR body and GT-210 all quote numbers.  Recount
    them here rather than trusting the prose."""

    def test_the_served_scene_holds_the_number_this_round_reports(self):
        identity = responder_mod._IDENTITY_OF_SCENE[EXPECTED_SCENES[0]]
        self.assertEqual(len(identity.shippable_placements()), 62)

    def test_the_whole_table_holds_the_number_the_letters_quote(self):
        total = sum(
            len(identity.shippable_placements())
            for identity in responder_mod._IDENTITY_OF_SCENE.values()
        )
        self.assertEqual(total, 692)

    def test_the_held_back_actors_are_the_difference(self):
        held = sum(
            len(responder_mod._IDENTITY_OF_SCENE[s].shippable_placements())
            for s in HELD_BACK_SCENES
        )
        self.assertEqual(held, 692 - 62)


class TheModuleIsAsciiTests(unittest.TestCase):
    """The bridge console is cp874; the source stays plain ASCII."""

    def test_the_module_and_this_test_are_ascii(self):
        for path in (MODULE_SOURCE, Path(__file__)):
            with self.subTest(path=path.name):
                path.read_text(encoding="ascii")


if __name__ == "__main__":
    unittest.main()
