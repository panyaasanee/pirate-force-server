"""LANE-A's ChooseNPC responder for the roster islands (rounds `326kf4`,
`gwwpmr`).

WHAT THESE TESTS ARE FOR.  ``lane_hooks/lane_a_choose_npc_roster_scenes.py``
turns a click on all ten roster islands' 692 actors from silence into an
answered frame.  ~~and REFUSES the nine sibling scenes whose placement
tables collide with Port Royal's Columbus index~~ -- round `gwwpmr`: chief's
scene guard landed in ``runtime.py``, the refusal retired, and the nine
joined.  What replaced the gate is
``TheNineAreSafeOnlyBecauseTheRuntimeGuardStandsTests`` below, which drives
the REAL dispatcher on scene 4 and fails if that guard is ever removed --
because nothing about the scene-blind index space itself was fixed.  The
evidence shape mirrors
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
That is ``GT-210`` for scene 3 and ``GT-212`` for the nine; these tests
measure the wire.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import sys
import tempfile
import unittest
from dataclasses import replace
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
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

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
EXPECTED_SCENES = (3, 4, 5, 6, 7, 8, 9, 10, 11, 130)
# ~~HELD_BACK_SCENES = (4, 5, 6, 7, 8, 9, 10, 11, 130)~~ -- round `gwwpmr`:
# chief's scene guard landed, so the nine register and NO scene is held
# back any more.  The name is DELETED rather than set to `()` (pf-adversary
# D4): three tests looped over it, and a loop over an empty tuple passes
# without executing a single assertion -- a vacuous green that the skip
# census in docs/PYTEST_SKIP_PINS.json cannot see either.  Where a refusal
# still has to be asserted, ask the MODULE (`skipped_scenes()`), which can
# disagree with this file.  The nine keep a name below for what they still
# are: the scenes whose freedom from Port Royal's quest conversation is on
# loan from one conjunct in runtime.py.
SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE = (4, 5, 6, 7, 8, 9, 10, 11, 130)
RUNTIME_SOURCE = (
    ROOT / "src" / "pirateforce_foundation" / "runtime.py"
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


def _target_pos_pc(legacy, xyz=(10.0, 20.0, 30.0), heading=0.0, moving=0,
                   derived=0) -> bytes:
    """One TargetPosVital, the frame that arms ``population_indices``.

    Same shape as ``tests/test_columbus_quest_dispatch_wiring.py``'s own
    helper, rebuilt here rather than imported so this file keeps no
    test-to-test coupling (the convention that file states for itself).
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, derived)
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

    def test_every_scene_in_the_table_has_a_responder_and_none_is_refused(
        self,
    ):
        """~~The point of the gate: NO responder for the held-back nine~~
        -- round `gwwpmr` retired that gate, so the assertion is inverted
        rather than looped over an empty tuple (pf-adversary D4: the
        emptied loop passed without executing anything).

        Both halves are asked of the MODULE, not of a constant in this
        file: every scene in its own table is registered TO IT, and its
        own refusal report is empty.  A module that failed to import its
        identity tables reports an empty refusal list too -- the first
        assertion is what separates that from success."""
        for scene_id in responder_mod._IDENTITY_OF_SCENE:
            with self.subTest(scene=scene_id):
                registered = lane_hooks.scene_choose_npc_responder(scene_id)
                self.assertIsNotNone(registered)
                self.assertEqual(registered.module, QUALIFIED_MODULE)
        self.assertEqual(responder_mod.skipped_scenes(), ())

    def test_it_reports_the_scenes_it_holds_and_the_reasons_it_refused(self):
        self.assertEqual(
            responder_mod.scenes_this_lane_answers_for(), EXPECTED_SCENES)
        self.assertEqual(len(EXPECTED_SCENES), 10)
        self.assertEqual(responder_mod.skipped_scenes(), ())

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
    """~~The gate that fires today~~ -- NO LONGER A GATE, round `gwwpmr`.

    ``runtime.py``'s Columbus branch used to read ``population_indices``
    with no scene check, and actor identity carries no scene component, so
    arming that field for a scene holding a placement at
    ``COLUMBUS_PLACEMENT_INDEX`` made Port Royal's quest conversation
    reachable there.  chief's conjunct (PR #570) closed that hop, this
    round registered the nine, and what is left here is the COLLISION
    ITSELF -- still real, still computed from the tables, and still the
    reason ``TheNineAreSafeOnlyBecauseTheRuntimeGuardStandsTests`` exists.
    """

    def test_the_collision_is_computed_from_the_tables_not_hardcoded(self):
        collided = responder_mod._columbus_collision_scenes()
        self.assertEqual(
            sorted(collided), sorted(SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE))
        for scene_id in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE:
            with self.subTest(scene=scene_id, expect="has index 1"):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                self.assertIn(
                    columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX,
                    {p.placement_index
                     for p in identity.shippable_placements()},
                )
        clear = set(EXPECTED_SCENES) - set(SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE)
        self.assertEqual(clear, {3})
        for scene_id in sorted(clear):
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
        for scene_id in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE:
            with self.subTest(scene=scene_id):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                collider = next(
                    p for p in identity.shippable_placements()
                    if p.placement_index
                    == columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX
                )
                self.assertEqual(collider.actor_identity, columbus)

    def test_the_module_decides_the_skip_and_the_test_does_not(self):
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


class TheTurnToFaceIsInTheFrameAndNotOnlyInTheLabelTests(unittest.TestCase):
    """pf-adversary D2, round `gwwpmr`: the headline sentence was untested.

    This file's module says "the clicked actor turns to face the player"
    and the action label ends `_FACE_P<idx>`, and until this class existed
    NOT ONE assertion read a movement attr out of `answer.frame`.  Three
    module mutants survived the whole 7,549-test suite because of it:

      M4  `if idx == selected_idx:` -> `if False and ...` (no turn-to-face
          attr is ever emitted, on any of the ten scenes)
      M5  the computed heading -> `0.0` (the actor faces a fixed direction
          rather than the player)
      M6  the wrong-scene guard -> `if False:` (one island's crowd can be
          delivered into another)

    The old wire-shape test could not catch M4 or M5: it compares
    `make_remote_movement_attr(..., mask=_FACE_MOVEMENT_MASK)` against
    `mask=0x03`, which pins the constant against ITSELF and never touches
    the composed frame.  Everything below reads the frame.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _answer_on(self, scene_id, player_xy=(1234.0, -567.0)):
        identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
        placements = responder_mod._placements_by_index(identity)
        indices = tuple(sorted(placements))
        selected_idx = indices[0]
        responder = lane_hooks.scene_choose_npc_responder(scene_id)
        answer = responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + selected_idx + 1,),
            population_indices=indices,
            last_target_pos=(player_xy[0], player_xy[1], 0.0, 0.0),
            scene_id=scene_id,
        )
        return answer, placements[selected_idx], player_xy

    def _face_attr_bytes(self, placement, heading):
        return self.legacy.make_remote_movement_attr(
            placement.actor_identity,
            placement.x, placement.y, placement.z,
            heading, mask=responder_mod._FACE_MOVEMENT_MASK,
        )

    def test_the_clicked_actor_carries_a_face_attr_in_the_frame(self):
        """Kills M4.  Not "a movement attr exists somewhere" -- the exact
        bytes for the clicked actor, at the heading this scene's own table
        and the player's own position imply."""
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                answer, placement, (px, py) = self._answer_on(scene_id)
                self.assertIsNotNone(answer)
                heading = self.legacy._heading_to_player(
                    placement.x, placement.y, px, py,
                )
                self.assertIn(
                    self._face_attr_bytes(placement, heading), answer.frame,
                    f"scene {scene_id}: the clicked actor's turn-to-face "
                    "bytes are not in the composed frame, so the label's "
                    "_FACE_ and the module's first paragraph are both false",
                )

    def test_the_heading_is_the_players_and_not_a_fixed_direction(self):
        """Kills M5.  Two clicks from two player positions on opposite
        sides of the same actor must produce DIFFERENT bytes; a constant
        heading (0.0 or any other) makes them identical."""
        for scene_id in EXPECTED_SCENES:
            with self.subTest(scene=scene_id):
                far = 99999.0
                east, placement, _ = self._answer_on(
                    scene_id, player_xy=(far, 0.0))
                west, _placement2, _ = self._answer_on(
                    scene_id, player_xy=(-far, 0.0))
                self.assertIsNotNone(east)
                self.assertIsNotNone(west)
                self.assertNotEqual(
                    east.frame, west.frame,
                    f"scene {scene_id}: the same click from opposite sides "
                    "of the actor composes identical bytes, so the heading "
                    "is not being computed from the player's position",
                )
                zero = self._face_attr_bytes(placement, 0.0)
                real = self.legacy._heading_to_player(
                    placement.x, placement.y, far, 0.0,
                )
                if real != 0.0:
                    self.assertNotIn(
                        zero, east.frame,
                        f"scene {scene_id}: a zero heading is on the wire "
                        "where a computed one belongs",
                    )

    def test_an_unclicked_actor_carries_no_face_attr(self):
        """The other half of M4: the attr must be on the CLICKED actor
        only.  An implementation that faces everybody would pass the two
        tests above and turn the whole island at once."""
        scene_id = EXPECTED_SCENES[0]
        answer, placement, (px, py) = self._answer_on(scene_id)
        identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
        placements = responder_mod._placements_by_index(identity)
        other_idx = sorted(placements)[1]
        other = placements[other_idx]
        heading = self.legacy._heading_to_player(
            other.x, other.y, px, py,
        )
        self.assertNotIn(self._face_attr_bytes(other, heading), answer.frame)
        self.assertIsNotNone(placement)

    def test_a_responder_refuses_a_scene_that_is_not_its_own(self):
        """Kills M6.  The call site keys the registry by the player's own
        scene, so this cannot happen from production today -- which is
        exactly why nothing measured it, and why deleting the guard was
        invisible to 7,549 tests.  Driving it directly is cheap."""
        scene_id = EXPECTED_SCENES[0]
        other_scene = EXPECTED_SCENES[1]
        identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
        placements = responder_mod._placements_by_index(identity)
        indices = tuple(sorted(placements))
        responder = lane_hooks.scene_choose_npc_responder(scene_id)
        self.assertIsNone(responder.respond(
            legacy=self.legacy,
            chosen_identities=(0x2000 + indices[0] + 1,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=other_scene,
        ))


class EveryRefusalSaysWhichSceneAndWhyTests(unittest.TestCase):
    """pf-adversary D7, round `gwwpmr`: a silent decline and a build with
    no responder look identical to a tester, and the commonest first
    experience of a newly opened island is the pre-movement click this
    responder refuses.  ``_decline`` prints; these drive each branch."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def _decline_line(self, **overrides):
        scene_id = EXPECTED_SCENES[0]
        identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
        indices = tuple(sorted(responder_mod._placements_by_index(identity)))
        kwargs = dict(
            legacy=self.legacy,
            chosen_identities=(0x2000 + indices[0] + 1,),
            population_indices=indices,
            last_target_pos=(0.0, 0.0, 0.0, 0.0),
            scene_id=scene_id,
        )
        kwargs.update(overrides)
        responder = lane_hooks.scene_choose_npc_responder(scene_id)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            answer = responder.respond(**kwargs)
        return answer, stderr.getvalue()

    def test_the_pre_movement_click_names_itself_and_the_step_that_fixes_it(
        self,
    ):
        answer, printed = self._decline_line(last_target_pos=None)
        self.assertIsNone(answer)
        self.assertIn(
            f"LANE_A_CHOOSE_NPC_SCENE{EXPECTED_SCENES[0]}_DECLINED", printed)
        self.assertIn("walk_one_step", printed)

    def test_an_unarmed_membership_is_named_differently(self):
        answer, printed = self._decline_line(population_indices=None)
        self.assertIsNone(answer)
        self.assertIn("membership_not_armed", printed)

    def test_an_identity_this_scene_cannot_answer_is_named(self):
        answer, printed = self._decline_line(chosen_identities=(0xDEAD,))
        self.assertIsNone(answer)
        self.assertIn("no_named_identity", printed)

    def test_the_wrong_scene_refusal_names_the_responders_own_scene(self):
        answer, printed = self._decline_line(scene_id=EXPECTED_SCENES[1])
        self.assertIsNone(answer)
        self.assertIn(
            f"this_responder_is_{EXPECTED_SCENES[0]}", printed)

    def test_a_successful_click_prints_no_decline_line(self):
        answer, printed = self._decline_line()
        self.assertIsNotNone(answer)
        self.assertNotIn("_DECLINED", printed)


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
        """One island's crowd never answers for another's.

        A FOURTH VACUOUS LOOP, found by deleting ``HELD_BACK_SCENES``
        rather than setting it to ``()`` (pf-adversary D4 named three;
        this one only surfaced as a NameError).  It now walks every OTHER
        scene this module serves, which is a stronger check than the one
        it replaces: those nine are the scenes whose rosters could
        actually be delivered to the wrong island."""
        others = [s for s in EXPECTED_SCENES if s != self.scene_id]
        self.assertEqual(len(others), 9)
        for other in others:
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

    def test_a_scene_the_module_refuses_gets_no_census_membership(self):
        """~~The regression this round refuses to ship~~ -- round `gwwpmr`
        registered the nine, so no scene is refused today.

        REWRITTEN RATHER THAN EMPTIED (pf-adversary D4).  The old version
        looped over a constant this file owned; when that constant became
        empty the test passed without executing an assertion.  This one
        asks the MODULE which scenes it refuses and asserts the census
        agrees for each -- so it is honest whether the answer is nine
        scenes, one, or (as today) none, and it starts working again by
        itself the day the splice gate fires."""
        refused = [scene for scene, _ in responder_mod.skipped_scenes()]
        self.assertEqual(
            refused, [],
            "the module now refuses a scene; this test just became live "
            "and its subtests below are the check that matters",
        )
        for scene_id in refused:
            with self.subTest(scene=scene_id):
                composed = self._compose(scene_id)
                self.assertIsNotNone(composed)
                self.assertIsNone(
                    composed.membership,
                    f"scene {scene_id} census arms membership although the "
                    "module refused it a responder",
                )

    def test_the_nine_now_arm_the_membership_the_gate_used_to_withhold(self):
        """The other half of what round `gwwpmr` shipped, measured.

        Registering a responder is what arms a scene's
        ``population_indices``; without this the click added above could
        never be reached on those nine scenes.  This is the census half,
        the click half is ``TheServedSceneAnswersAClickTests``.
        """
        for scene_id in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE:
            with self.subTest(scene=scene_id):
                composed = self._compose(scene_id)
                self.assertIsNotNone(composed)
                self.assertIsNotNone(
                    composed.membership,
                    f"scene {scene_id} census still withholds membership",
                )
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                self.assertEqual(
                    sorted(composed.membership.population_indices),
                    sorted(responder_mod._placements_by_index(identity)),
                )


class TheCountsThisRoundClaimsTests(unittest.TestCase):
    """The round file, the PR body and GT-210 all quote numbers.  Recount
    them here rather than trusting the prose."""

    def test_the_served_scene_holds_the_number_this_round_reports(self):
        identity = responder_mod._IDENTITY_OF_SCENE[3]
        self.assertEqual(len(identity.shippable_placements()), 62)

    def test_the_ten_served_scenes_hold_the_number_gwwpmr_reports(self):
        """692 across ten islands is the number round `gwwpmr`'s PR body
        and ``GT-212`` both quote.  Counted from the registry's own view of
        what this module answers for, not from the table, so a scene that
        lost its registration cannot leave the number standing."""
        served = responder_mod.scenes_this_lane_answers_for()
        self.assertEqual(served, EXPECTED_SCENES)
        self.assertEqual(
            sum(
                len(responder_mod._IDENTITY_OF_SCENE[s].shippable_placements())
                for s in served
            ),
            692,
        )

    def test_the_whole_table_holds_the_number_the_letters_quote(self):
        total = sum(
            len(identity.shippable_placements())
            for identity in responder_mod._IDENTITY_OF_SCENE.values()
        )
        self.assertEqual(total, 692)

    def test_the_nine_on_loan_are_the_difference_between_the_two_rounds(self):
        """What round `gwwpmr` added on top of `326kf4`: 630 actors."""
        added = sum(
            len(responder_mod._IDENTITY_OF_SCENE[s].shippable_placements())
            for s in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE
        )
        self.assertEqual(added, 692 - 62)


class TheNineAreSafeOnlyBecauseTheRuntimeGuardStandsTests(unittest.TestCase):
    """Round `gwwpmr` deleted this file's Columbus gate.  This is what it
    put in its place, and it is the load-bearing test of that round.

    THE GATE DID NOT BECOME UNNECESSARY, IT BECAME REDUNDANT WITH SOMEONE
    ELSE'S CONJUNCT.  ``population_indices`` is still a placement-index
    space with no scene in it, an actor identity is still
    ``0x2000 + placement_index + 1``, and placement index 1 is still
    ``0x2002`` on nine of these ten islands as well as on Columbus's own.
    What changed is that ``runtime.py``'s Columbus branch now asks
    ``self.foundation.selected.position.scene_id ==
    world_scene_travel.HOME_SCENE_ID`` first (chief, PR #570, answering
    this lane's CORE-REQUEST ``20260902_1207``).

    SO THIS LANE OWES A TEST THAT FAILS WHEN THAT CONJUNCT GOES.  chief's
    own ``tests/test_columbus_quest_dispatch_wiring.py::
    ColumbusSceneGuardTests`` already fails then -- deliberately not
    relied on here, and the difference is not redundancy: chief's test
    proves the guard REFUSES, this one proves the nine islands are
    ANSWERED AND SAFE IN THE SAME FRAME, which is a property that only
    exists since this round registered them and which nothing in chief's
    file knows about.  If the guard is ever removed, the honest fix is to
    restore this file's own skip rule, not to weaken this test.

    WHAT IS DRIVEN: the real ``make_state_class`` dispatcher, headless,
    through a full login/create/start-game, then moved into scene 4 the
    way A GM WARP leaves the session (``_gm_warp_resync_selected_scene``
    rewrites ``scene_id`` alone), the scene's own membership armed the way
    its arrival census arms it, and then ONE real ``ChooseNPC`` frame
    naming ``0x2002``.

    NOT "or a travel-gate crossing", WHICH AN EARLIER DRAFT OF THIS
    DOCSTRING CLAIMED (pf-adversary D3, MEASURED).  That route leaves the
    OPPOSITE state: the crossing sets ``population_indices = None`` for
    every non-home arrival and never resets ``world_census_sent``, so the
    arrival census does not re-arm and these nine stay dark for the life
    of that session.  It is latent today (walk-in travel gates are
    disabled by default) and it is not this lane's line to change, but a
    test file may not name a route it has not driven.  Reported to chief
    in round `gwwpmr`'s letter with the stale comment at the withhold site
    that still says a click answerer for roster scenes does not exist.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _real_state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.dispatch(self.legacy.parse_outer(_target_pos_pc(self.legacy)))
        return state

    def _stand_on_island(self, state, scene_id):
        """Move the session to an island and arm THAT island's membership.

        Both halves matter.  Rewriting ``scene_id`` alone is what a GM warp
        leaves behind; the membership is what the arrival census installs a
        moment later.  A test that moved the scene without re-arming would
        be driving Port Royal's index set through an island's responder --
        which is a state no player is ever in, and would let a real defect
        hide behind an unrealistic input.
        """
        selected = state.foundation.selected
        state.foundation.selected = replace(
            selected, position=replace(selected.position, scene_id=scene_id),
        )
        composer = lane_hooks.scene_census_composer(scene_id)
        self.assertIsNotNone(composer, f"scene {scene_id} has no composer")
        composed = composer.compose(
            legacy=self.legacy, anchor=(10.0, 20.0, 30.0), scene_id=scene_id,
        )
        self.assertIsNotNone(composed)
        self.assertIsNotNone(
            composed.membership,
            f"scene {scene_id} withholds membership -- this round's own "
            "census half is not in force, so the click half proves nothing",
        )
        state.population_indices = tuple(
            composed.membership.population_indices)
        return state

    def _click(self, state, identity):
        actions = state.dispatch(self.legacy.parse_outer(
            _choose_npc_pc(self.legacy, identity)
        ))
        return [action[0] for action in actions]

    def test_the_collider_identity_is_the_same_on_the_island_and_at_home(self):
        """The premise, restated as a measurement rather than inherited
        from the docstring: the byte a client sends for the island's
        placement-index-1 actor is the byte it sends for Columbus."""
        columbus = columbus_quest_dispatch.columbus_actor_identity(self.legacy)
        for scene_id in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE:
            with self.subTest(scene=scene_id):
                identity = responder_mod._IDENTITY_OF_SCENE[scene_id]
                collider = next(
                    p for p in identity.shippable_placements()
                    if p.placement_index
                    == columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX
                )
                self.assertEqual(collider.actor_identity, columbus)

    def test_a_click_on_the_island_collider_answers_and_opens_no_quest(self):
        """One frame in, two things asserted about what comes out.

        THE POSITIVE HALF is this round's whole claim: a click on scene 4's
        placement-index-1 actor now gets this lane's roster answer, where
        yesterday it got nothing.  THE NEGATIVE HALF is the one the gate
        used to buy: no Columbus conversation rides along with it.  Both in
        the SAME dispatch, because that is the frame a player actually
        sends -- asserting them in two tests would let a change break the
        pairing while both stayed green.
        """
        columbus = columbus_quest_dispatch.columbus_actor_identity(self.legacy)
        state = self._stand_on_island(
            self._real_state("tok-island-collider"), 4)
        labels = self._click(state, columbus)
        self.assertIn(
            "LANE_A_CHOOSE_NPC_SCENE4_FACE_P"
            + str(columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX),
            labels,
            f"scene 4's own click answer is missing; got {labels}",
        )
        self.assertNotIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE", labels,
        )
        self.assertNotIn(
            "core_request_014_columbus_npc_conversation_sent_once",
            state.events,
        )
        self.assertFalse(state.columbus_quest3021_conversation_sent)

    def test_no_island_in_the_table_opens_the_quest_on_the_collider(self):
        """All nine, one subtest each -- the letter's own list, driven."""
        columbus = columbus_quest_dispatch.columbus_actor_identity(self.legacy)
        for scene_id in SCENES_THE_RUNTIME_GUARD_KEEPS_SAFE:
            with self.subTest(scene=scene_id):
                state = self._stand_on_island(
                    self._real_state("tok-island-%d" % scene_id), scene_id)
                labels = self._click(state, columbus)
                self.assertIn(
                    "LANE_A_CHOOSE_NPC_SCENE%d_FACE_P%d" % (
                        scene_id,
                        columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX,
                    ),
                    labels,
                )
                self.assertNotIn(
                    "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE",
                    labels,
                )
                self.assertFalse(state.columbus_quest3021_conversation_sent)

    def test_the_quest_still_opens_where_it_is_supposed_to(self):
        """The guard must not have cost Port Royal its own quest -- and
        this round must not have taken it away either.  Without this, a
        change that broke the quest everywhere would leave every assertion
        above green."""
        columbus = columbus_quest_dispatch.columbus_actor_identity(self.legacy)
        state = self._real_state("tok-island-home")
        self.assertEqual(
            state.foundation.selected.position.scene_id,
            world_scene_travel.HOME_SCENE_ID,
        )
        labels = self._click(state, columbus)
        self.assertIn(
            "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE", labels)
        self.assertTrue(state.columbus_quest3021_conversation_sent)

    def test_the_runtime_guard_this_lane_leans_on_is_named_in_its_source(self):
        """A cheap second reading of the same dependency, in the shape that
        says WHICH LINE this lane is standing on.

        Deliberately narrow: it asserts that the conjunct exists in the
        Columbus branch's own guard, parsed rather than grepped, so a
        reformat cannot defeat it and a DELETION cannot pass.  It does not
        assert anything about how the branch is written otherwise -- that
        is chief's file and chief's shape.
        """
        tree = ast.parse(RUNTIME_SOURCE.read_text(encoding="utf-8"))
        guards_with_the_index_read = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            source = ast.dump(node.test)
            if (
                "COLUMBUS_PLACEMENT_INDEX" in source
                and "population_indices" in source
            ):
                guards_with_the_index_read.append(source)
        self.assertTrue(
            guards_with_the_index_read,
            "no guard in runtime.py reads COLUMBUS_PLACEMENT_INDEX against "
            "population_indices any more -- the branch this lane's nine "
            "scenes were measured against has moved or gone; re-measure "
            "before trusting this file's registrations",
        )
        for source in guards_with_the_index_read:
            self.assertIn(
                "HOME_SCENE_ID", source,
                "runtime.py reads the scene-blind Columbus index without a "
                "HOME_SCENE_ID conjunct -- nine islands in this module must "
                "go back behind _skip_reason_for's retired Columbus rule",
            )


class TheModuleIsAsciiTests(unittest.TestCase):
    """The bridge console is cp874; the source stays plain ASCII."""

    def test_the_module_and_this_test_are_ascii(self):
        for path in (MODULE_SOURCE, Path(__file__)):
            with self.subTest(path=path.name):
                path.read_text(encoding="ascii")


if __name__ == "__main__":
    unittest.main()
