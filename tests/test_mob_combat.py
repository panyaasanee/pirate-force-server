"""LANE-B / MOB-COMBAT-001: the damage driver.

The load-bearing tests in this file are these four.

``test_the_formula_constants_are_the_proven_ones`` is the one that matters
most.  This module re-declares the damage formula instead of importing the
scenario-gated lanes that proved it, because a flagless build cannot reach a
probe lane - so the only thing keeping the copy honest is that it is compared,
value by value, against those lanes' own constants.  If someone edits a
constant here, the number a player sees stops being the number three proving
rounds measured, and this test is what says so.

``test_threat_rises_by_the_damage`` guards a silent failure that no exception
would ever announce: ``mob_aggro.apply_damage_threat`` adds threat only for a
NEGATIVE damage value and returns the state unchanged for a positive one.  A
driver that hands it the positive arithmetic value builds a monster that is
hit, bleeds, repaints its bar and never decides it has an enemy.  The first
draft of this module did exactly that.

``test_the_bar_frame_is_the_hostile_body_with_a_lower_hp`` pins the refresh
frame to the field_mobs hostile body at a lower HP, and pins that it carries no
movement attribute - which is how GT-035's own refresh steps were composed.  It
does NOT claim the frame is the one GT-035 watched: that lane's body carries no
faction field, and this one does.  The difference is five bytes and it is
written down in the module, in MOB_COMBAT_NONCLAIMS, and here.

``test_the_floor_holds_and_says_so`` pins the seam the death half attaches to.
"""

import ast
import builtins
import json
import sys
import tempfile
import threading
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    damage_model_hypothesis,
    field_mobs,
    hostile_hp_link_hypothesis,
    mob_aggro,
    mob_combat,
    mob_death,
    mob_loot,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import NPC_ATTR_ID
from pirateforce_foundation.mob_combat import (
    ATTACK_CADENCE_MS_PROVISIONAL,
    CHIT_RESULT_HEADER_WIRE_SIZE,
    CHIT_RESULT_VITAL_ID,
    AttackCadenceLedger,
    CadenceRecord,
    Combatant,
    CombatLedger,
    FLAGS_HIT,
    FLAGS_MISS,
    HIT_ELEMENT_WIRE_SIZE,
    HP_FLOOR,
    MobBalance,
    MobCombatContractError,
    announce_frames,
    apply_hit,
    apply_threat,
    attack_from_observed_action,
    bar_frames,
    check_attack_cadence,
    describe_cadence_rejection,
    describe_step,
    encode_hit_entry,
    mob_defender,
    open_cadence_ledger,
    open_ledger,
    pin_document,
    production_allowed,
    resolve_damage,
    strike,
    test_only,
)


PERFORMER = 0x750059

#: The composer whose call sites
#: ``mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS`` reports on.
UNDER_PUBLICATION_COMPOSER = (
    "remote_actors_preserving_the_ground_under_publication")


def call_site_status_of_source(source: str) -> str:
    """Which of the three registered words ONE file's source earns.

    THE SHAPES, WEAKEST FIRST, and why the middle one exists at all
    (LANE-A's letter ``20260903_0320``): a lane that must import on a tree
    where this composer does not exist yet cannot write its name in an
    ``import`` or a call -- it writes ``getattr(mob_combat, NAME)`` and calls
    the local it got back.  Matching the function's own name finds NOTHING
    there, and the constant then tells an operator "nothing is wired" about a
    process that composes every ChooseNPC answer through it.  So the lookup
    is a shape this scan knows, reported in a WEAKER word than a direct call
    because that is what it is: evidence that somebody fetches it, not that a
    frame goes through it.  What settles that is
    ``GROUND_UNDER_PUBLICATION_CALL_SITE_REACHED`` on the console.

    A CALL OR A LOOKUP, NEVER A SUBSTRING: a comment or a docstring naming
    the function sends no bytes and earns nothing here.
    """
    tree = ast.parse(source)
    if not _is_production_module(tree):
        # A module that declares itself out of production is not a production
        # call site (pf-adversary, this round, D5: a test-only module calling
        # it in a fixture scored "called" and would have put the strongest
        # word on an operator's console for a path no player reaches).
        return "composed_not_called"
    #: ``import X as Y`` defeated the name match once; it is resolved.
    names = {UNDER_PUBLICATION_COMPOSER}
    #: ...and a module-level ``NAME = "remote_actors_..."`` is how the
    #: string reaches ``getattr`` in the hook that does this today.
    spellings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if (alias.name == UNDER_PUBLICATION_COMPOSER
                        and alias.asname):
                    names.add(alias.asname)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            spellings.update(_names_bound_to_the_composer(node))
    status = "composed_not_called"
    for node in ast.walk(tree):
        # AN ATTRIBUTE REFERENCE IS EVIDENCE TOO, not only a Call: the
        # nearest refactor of the hook that owns this today is
        # ``if hasattr(mob_combat, NAME): return mob_combat.<name>``, which
        # reproduces LANE-A's original complaint one round later in a new
        # spelling (pf-adversary, this round, D5).  It is the WEAK word: a
        # name that is fetched is not a frame that goes through.
        if (isinstance(node, ast.Attribute)
                and node.attr == UNDER_PUBLICATION_COMPOSER):
            status = "wired_by_name_lookup"
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name in names:
            return "called"                       # the strongest evidence
        if name != "getattr" or len(node.args) < 2:
            continue
        wanted = node.args[1]
        if (isinstance(wanted, ast.Constant)
                and wanted.value == UNDER_PUBLICATION_COMPOSER):
            status = "wired_by_name_lookup"
        elif isinstance(wanted, ast.Name) and wanted.id in spellings:
            status = "wired_by_name_lookup"
    return status


def _is_production_module(tree: ast.Module) -> bool:
    """Does this module claim to run in production?

    The two convention markers every module in ``src/`` carries.  Absent, a
    module counts as production: the markers are what an author writes to opt
    OUT, and a missing marker must never be read as an opt-out.

    !! MODULE LEVEL ONLY, ROUND 91tlkk (pf-adversary D8 of that round, found
    on the sibling scan and true here word for word).  ~~``ast.walk``~~ IS
    STRUCK: it read a LOCAL VARIABLE named ``production_allowed`` -- at any
    nesting depth, in anybody's file -- as the whole module opting out of
    production.  An ordinary, entitled edit in another lane's file could
    therefore move this lane's status word, and the failure message would
    have told its author to move the label.  D4 of the round that wrote this
    scan exists to stop exactly that; this is the hole it left open.
    """
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if (target.id == "production_allowed"
                    and isinstance(node.value, ast.Constant)
                    and node.value.value is False):
                return False
            if (target.id == "test_only"
                    and isinstance(node.value, ast.Constant)
                    and node.value.value is True):
                return False
    return True


def _names_bound_to_the_composer(node) -> set:
    """Every local name this assignment binds to the composer's own string.

    TUPLE TARGETS ARE UNPACKED, and that is not a nicety (pf-adversary, this
    round, D4): the hook that owns this shape today may write

        ``COMPOSER, _OTHER = "remote_actors_..._publication", "..."``

    which is a spelling change with identical behaviour, blessed by its own
    lane's suite -- and a scan that skipped it would have turned ``main`` red
    from another lane's entitled edit.  This lane's guard must not be a trap
    laid in somebody else's file.
    """
    value = node.value
    targets = (node.targets if isinstance(node, ast.Assign)
               else [node.target])
    bound = set()
    for target in targets:
        if (isinstance(target, (ast.Tuple, ast.List))
                and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)):
            for one, item in zip(target.elts, value.elts):
                if (isinstance(one, ast.Name)
                        and isinstance(item, ast.Constant)
                        and item.value == UNDER_PUBLICATION_COMPOSER):
                    bound.add(one.id)
        elif (isinstance(target, ast.Name)
                and isinstance(value, ast.Constant)
                and value.value == UNDER_PUBLICATION_COMPOSER):
            bound.add(target.id)
    return bound


def call_site_status_of_tree(paths) -> str:
    """The strongest word any production file earns.  ``mob_combat.py``
    itself is skipped: it is where the composer is DEFINED."""
    rank = mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUSES
    best = rank[0]
    for path in sorted(paths):
        if path.name == "mob_combat.py":
            continue
        try:
            got = call_site_status_of_source(
                path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, SyntaxError, ValueError):
            # ROUND 91tlkk, pf-adversary D9.  A module that does not decode
            # as UTF-8 (this project writes Thai; cp874 files exist) or does
            # not parse cannot be imported, so it cannot host a running call
            # site.  Skipped rather than raised on -- though if the skipped
            # file is the one holding the call site, this still answers with
            # a weaker word and this lane's test still goes red, which is the
            # honest outcome and not an immunity.
            continue
        if rank.index(got) > rank.index(best):
            best = got
        if best == rank[-1]:
            break
    return best


class MobCombatTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [m for m in cls.roster if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX][0]
        cls.attacker = Combatant(level=27, ability_str=132, ability_con=10)

    # -- the arithmetic ---------------------------------------------------

    def test_the_formula_constants_are_the_proven_ones(self):
        for name in ("ATK_BASE", "K_ATK_STR", "K_ATK_LV", "DEF_BASE",
                     "K_DEF_CON", "K_DEF_LV", "MIN_HIT"):
            here = getattr(mob_combat, name)
            self.assertEqual(
                here, getattr(damage_model_hypothesis, name),
                "%s drifted from HYP-PF-024" % name)
            self.assertEqual(
                here, getattr(hostile_hp_link_hypothesis, name),
                "%s drifted from HYP-PF-038" % name)

    def test_the_wire_anchors_are_the_proven_ones(self):
        pairs = (
            ("CHIT_RESULT_VITAL_ID", "CHIT_RESULT_VITAL_ID"),
            ("CHIT_RESULT_VITAL_VERSION", "CHIT_RESULT_VITAL_VERSION"),
            ("CHIT_RESULT_HEADER_WIRE_SIZE", "CHIT_RESULT_HEADER_WIRE_SIZE"),
            ("HIT_ELEMENT_WIRE_SIZE", "HIT_ELEMENT_WIRE_SIZE"),
            ("HIT_COUNT_WIRE_SIZE", "HIT_COUNT_WIRE_SIZE"),
            ("DAMAGE_WIRE_MIN", "DAMAGE_WIRE_MIN"),
            ("DAMAGE_WIRE_MAX", "DAMAGE_WIRE_MAX"),
            ("FLAGS_HIT", "FLAGS_HIT"),
            ("FLAGS_MISS", "FLAGS_MISS"),
        )
        for here, there in pairs:
            self.assertEqual(
                getattr(mob_combat, here),
                getattr(hostile_hp_link_hypothesis, there),
                "%s drifted from HYP-PF-038" % here)

    def test_the_damage_is_recomputed_not_written_down(self):
        defender = mob_defender(self.mob)
        expected = (
            mob_combat.ATK_BASE
            + mob_combat.K_ATK_STR * self.attacker.ability_str
            + mob_combat.K_ATK_LV * self.attacker.level
        ) - (
            mob_combat.DEF_BASE
            + mob_combat.K_DEF_CON * defender.ability_con
            + mob_combat.K_DEF_LV * defender.level
        )
        self.assertEqual(resolve_damage(self.attacker, defender), expected)

    def test_a_hit_never_goes_below_the_minimum(self):
        weakest = Combatant(level=1, ability_str=0, ability_con=0)
        strongest = Combatant(level=1000, ability_str=0, ability_con=100000)
        self.assertEqual(
            resolve_damage(weakest, strongest), mob_combat.MIN_HIT)

    # -- the ledger -------------------------------------------------------

    def test_the_ledger_opens_at_every_ceiling_in_the_roster(self):
        ledger = open_ledger()
        self.assertEqual(len(ledger.balances), len(self.roster))
        for mob in self.roster:
            row = ledger.balance_of(mob.actor_identity)
            self.assertEqual(row.current_hp, mob.max_hp)
            self.assertEqual(row.max_hp, mob.max_hp)
        self.assertEqual(
            list(ledger.identities()), sorted(ledger.identities()))

    def test_the_announced_number_is_the_number_subtracted(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 964)
        self.assertEqual(outcome.damage, 964)
        self.assertEqual(outcome.damage_wire, -964)
        self.assertEqual(outcome.applied, 964)
        self.assertEqual(outcome.hp_before - outcome.hp_after, 964)
        self.assertEqual(
            ledger.balance_of(self.mob.actor_identity).current_hp,
            self.mob.max_hp - 964)

    def test_two_hits_stack_on_the_same_balance(self):
        ledger = open_ledger()
        ledger, _ = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 964)
        ledger, second = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 2122)
        self.assertEqual(second.hp_after, self.mob.max_hp - 964 - 2122)

    def test_the_floor_holds_and_says_so(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, self.mob.max_hp * 2)
        self.assertEqual(outcome.hp_after, HP_FLOOR)
        self.assertEqual(outcome.applied, self.mob.max_hp - HP_FLOOR)
        self.assertEqual(
            outcome.clamped_by, self.mob.max_hp * 2 - outcome.applied)
        self.assertTrue(outcome.at_floor)
        self.assertTrue(outcome.death_due)
        self.assertEqual(outcome.damage_wire, -outcome.applied)
        # and a hit on a monster already at the floor moves nothing at all
        ledger, again = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 500)
        self.assertEqual(again.applied, 0)
        self.assertEqual(again.flags, FLAGS_MISS)
        self.assertEqual(again.damage_wire, 0)
        self.assertTrue(again.death_due)

    def test_the_ledger_is_never_mutated_in_place(self):
        first = open_ledger()
        second, _ = apply_hit(first, PERFORMER, self.mob.actor_identity, 100)
        self.assertEqual(
            first.balance_of(self.mob.actor_identity).current_hp,
            self.mob.max_hp)
        self.assertNotEqual(first, second)

    def test_a_ledger_refuses_a_duplicate_identity(self):
        row = MobBalance(0x2001, 100, 100)
        with self.assertRaises(MobCombatContractError) as caught:
            CombatLedger((row, row))
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DUPLICATE_LEDGER_IDENTITY)

    def test_the_performer_may_not_be_the_target(self):
        ledger = open_ledger()
        with self.assertRaises(MobCombatContractError) as caught:
            apply_hit(
                ledger, self.mob.actor_identity, self.mob.actor_identity, 10)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_PERFORMER_IS_THE_TARGET)

    def test_an_unopened_target_is_refused_by_name(self):
        with self.assertRaises(MobCombatContractError) as caught:
            apply_hit(open_ledger(), PERFORMER, 0x7FFF, 10)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    # -- the threat seam --------------------------------------------------

    def test_threat_rises_by_the_damage(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            step.aggro_state.threat, ((PERFORMER, step.outcome.damage),))
        second = strike(
            self.legacy, mob_aggro, step.ledger, step.aggro_state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            second.aggro_state.threat,
            ((PERFORMER, step.outcome.damage + second.outcome.damage),))

    def test_a_hit_that_moves_nothing_adds_no_threat(self):
        ledger = open_ledger()
        ledger, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, self.mob.max_hp * 2)
        ledger, nothing = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 500)
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        self.assertIs(apply_threat(mob_aggro, state, nothing), state)

    def test_an_incomplete_aggro_handle_is_refused_by_name(self):
        ledger = open_ledger()
        _, outcome = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 10)
        with self.assertRaises(MobCombatContractError) as caught:
            apply_threat(object(), None, outcome)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_AGGRO_HANDLE_INCOMPLETE)

    # -- the wire ---------------------------------------------------------

    def test_the_announce_frame_carries_the_signed_number(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        entry = encode_hit_entry(
            self.legacy, self.mob.actor_identity, step.outcome.damage_wire,
            (self.mob.x, self.mob.y, self.mob.z), FLAGS_HIT)
        self.assertEqual(len(entry), HIT_ELEMENT_WIRE_SIZE)
        self.assertIn(
            bytes(self.legacy.u32tag(
                mob_combat.TAG_U32,
                step.outcome.damage_wire & 0xFFFFFFFF)),
            entry)
        self.assertIn(entry, step.announce_pc)
        self.assertIn(
            bytes(self.legacy.u16tag(
                mob_combat.TAG_U16, CHIT_RESULT_VITAL_ID)),
            step.announce_pc)
        self.assertEqual(step.announce_frame, self.legacy.frame_pc(
            step.announce_pc))

    def test_the_encoders_are_byte_identical_to_the_proven_lane(self):
        # The whole re-derivation stands or falls here.  This module refuses to
        # import HYP-PF-038 because that lane is scenario-gated and a flagless
        # build cannot reach it - but a re-derivation nobody compares is just a
        # second guess.  A test MAY reach the probe lane, so it does: same
        # target, same position, same damage, same flags, and the bytes must be
        # equal, not merely the same length.  ``_PROFILE`` is that lane's own
        # allowlisted scenario object and its unlock minter takes nothing else.
        unlock = hostile_hp_link_hypothesis.hostile_hp_link_wire_unlock(
            hostile_hp_link_hypothesis._PROFILE)
        target = hostile_hp_link_hypothesis.hostile_hp_link_target_identity()
        # ROUND 8ftmbx: ~~self.mob~~.  The probe lane is pinned to ONE target,
        # bg0001 placement 30, and that row left the shipped roster with
        # COO-DECISION 2026-08-29T00:41+07:00.  The comparison is against
        # THAT lane's bytes, so the subject has to stay that lane's actor;
        # rebuilt from the preserved row rather than looked up in a roster
        # that no longer has it.
        subject = field_mobs.gt035_observed_subject()
        self.assertEqual(target, subject.actor_identity)
        position = (subject.x, subject.y, subject.z)
        for damage_wire, flags in ((-964, FLAGS_HIT), (-2122, FLAGS_HIT),
                                   (0, FLAGS_MISS)):
            mine = encode_hit_entry(
                self.legacy, target, damage_wire, position, flags)
            theirs = hostile_hp_link_hypothesis.\
                encode_hostile_hp_link_hit_entry(
                    self.legacy, target, damage_wire, position,
                    hostile_hp_link_hypothesis.YAW_PINNED, flags, unlock)
            self.assertEqual(mine, theirs)
            self.assertEqual(
                mob_combat.encode_chit_result(self.legacy, PERFORMER, [mine]),
                hostile_hp_link_hypothesis.encode_hostile_hp_link_chit_result(
                    self.legacy, PERFORMER, [theirs], unlock))

    def test_a_positive_damage_number_is_refused_by_name(self):
        with self.assertRaises(MobCombatContractError) as caught:
            encode_hit_entry(
                self.legacy, self.mob.actor_identity, 964,
                (self.mob.x, self.mob.y, self.mob.z), FLAGS_HIT)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_DAMAGE_WIRE_POSITIVE)

    def test_a_miss_and_a_number_may_not_disagree(self):
        with self.assertRaises(MobCombatContractError) as caught:
            encode_hit_entry(
                self.legacy, self.mob.actor_identity, -964,
                (self.mob.x, self.mob.y, self.mob.z), FLAGS_MISS)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_FLAGS_DISAGREE_WITH_DAMAGE)

    def test_the_bar_frame_differs_from_gt035s_by_exactly_the_faction(self):
        # D1.  Stated as a test so nobody has to take the paragraph's word for
        # it: the frame this production driver refreshes is NOT the frame the
        # attended round watched.  It is eight bytes longer (five for
        # faction, three for RE-117's level) and its BasicAttr mask carries
        # bits 0x0400 and 0x0002.
        hp = self.mob.max_hp - 964
        mine = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        theirs = self.legacy.make_npc_attr(
            self.mob.template_id, self.mob.actor_identity,
            mob_combat.field_mobs.SCENE_ID,
            mob_combat.field_mobs.SCENE_SEQUENCE,
            self.mob.visual_preset, hp, self.mob.max_hp,
            movement_speed=float(self.mob.speed_walk),
            basic_name=self.mob.display_name,
        )
        self.assertEqual(
            len(mine),
            len(theirs)
            + field_mobs.FACTION_SPLICE_BYTES + field_mobs.LEVEL_SPLICE_BYTES)
        self.assertIn(
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
            mine)
        self.assertNotIn(
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
            theirs)

    def test_the_bar_frame_is_the_hostile_body_with_a_lower_hp(self):
        hp = self.mob.max_hp - 964
        pc, frame = bar_frames(self.legacy, self.mob, hp)
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        self.assertIn(body, pc)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        # the same monster at full HP differs only by the HP fields, and the
        # refresh carries no movement attribute at all
        full_pc, _ = bar_frames(self.legacy, self.mob, self.mob.max_hp)
        self.assertEqual(len(pc), len(full_pc))
        self.assertNotEqual(pc, full_pc)
        placed_pc, _ = bar_frames(
            self.legacy, self.mob, hp, with_movement=True)
        self.assertGreater(len(placed_pc), len(pc))

    def test_the_bar_frame_refuses_to_go_under_the_floor(self):
        # ~~0 was under the floor~~ - with the floor at 0 it is ON it, and a
        # LIVE body there satisfies neither side of the client's gate, so it
        # is refused by its own name and handed to mob_death.
        with self.assertRaises(MobCombatContractError) as caught:
            bar_frames(self.legacy, self.mob, 0)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_BAR_FRAME_FOR_A_DEAD_BODY)
        self.assertIn("mob_death", caught.exception.detail)
        with self.assertRaises(MobCombatContractError) as caught:
            bar_frames(self.legacy, self.mob, -1)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_VALUE_OUT_OF_RANGE)

    def test_the_bar_frame_is_a_one_entry_generation_open_risk_not_a_fix(self):
        # This test does not close anything - it PINS the shape the docstring
        # above now warns about, so the next round (or chief, or RE) has a
        # red test the moment anyone widens this to a full-roster generation
        # without meaning to, or narrows a fix down to zero entries by
        # mistake.  See the docstring citation: `pirate-force-server#63`
        # wired this onto the unflagged path 2026-08-26 16:49+07:00, and
        # `pf_bridge/notes_to_chief/20260826_1017_RE-082-RESULT-OBJECT-REF-IS-ELEMENT-
        # KEY.md` proved a sibling collection's consumer erases every entry a
        # nonempty generation omits.  Nobody has run that trace against THIS
        # collection's consumer yet, so this lane records the fact - one
        # entry, not zero, not the roster - rather than claiming a fix.
        hp = self.mob.max_hp - 964
        pc, _ = bar_frames(self.legacy, self.mob, hp)
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=hp)
        one_entry = self.legacy.make_remote_actor_entry(
            mob_combat.NPC_STYLE_ACTOR_TYPE, self.mob.actor_identity,
            [(mob_combat.NPC_ATTR_ID, body)])
        # ROUND jysbar: ~~compared against ``make_runtime_remote_actors``'s own
        # bytes~~ IS STRUCK, and struck by a MEASUREMENT rather than by a claim
        # (COO-DECISION 2026-09-02T10:44, items 3 and 4).  This frame now goes
        # out through the PRESERVE composer for the same carrier, so it is
        # v141's bytes with the ground-list bit set in the derived mask and one
        # empty ground record appended.  What this test exists for is UNCHANGED
        # and is asserted below in both directions: ONE entry, not zero, not
        # the roster -- and the entry is still v141's own actor entry, byte for
        # byte, at v141's own offset.
        composed = self.legacy.make_runtime_remote_actors([one_entry])[0]
        self.assertEqual(
            pc,
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, [one_entry])[0])
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[:offset], composed[:offset])
        self.assertEqual(pc[offset + 2:len(composed)], composed[offset + 2:])
        self.assertEqual(pc[len(composed):],
                         mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)
        self.assertIn(one_entry, pc)
        # The count field the client reads is still exactly one.
        self.assertEqual(pc[offset + 2:offset + 5],
                         self.legacy.u16tag(0x12, 1))

    def test_the_two_frames_come_back_in_the_watched_order(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, self.attacker)
        self.assertEqual(
            step.frames, (step.announce_frame, step.bar_frame))
        self.assertIn(NPC_ATTR_ID.to_bytes(2, "little"), step.bar_pc)

    # -- the ground-preserve opt-in (COO-DECISION 20260902_0646) -----------
    #
    # CHIEF-DEBT-003 says a site is not opted in until ONE test drives the
    # INSTALLED path and reaches the real composer.  So the first test here
    # goes through attack_from_observed_action -- the call the wiring line
    # makes -- and not through announce_frames, and it reads the bytes that
    # would leave the socket rather than a flag on a step.

    def test_a_real_hit_ships_the_preserve_tail_through_the_wired_call(self):
        ledger = open_ledger()
        step = attack_from_observed_action(
            self.legacy, None, ledger, None,
            {"field_qword_20": self.mob.actor_identity},
            PERFORMER, self.attacker,
        )
        self.assertIsNotNone(step)
        self.assertTrue(step.announce_pc.endswith(
            mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN),
            "the wired hit did not ship the preserved ground list")
        self.assertEqual(
            step.announce_frame, self.legacy.frame_pc(step.announce_pc))

    def test_only_the_last_record_moved_and_the_hit_itself_did_not(self):
        # The claim this round makes to the owner is "the damage number is the
        # same bytes as yesterday, and only the ground record changed".  That
        # is checked here by re-composing yesterday's frame from the same
        # payload and comparing everything in front of the tail.
        ledger = open_ledger()
        _, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 100)
        pc, frame = announce_frames(
            self.legacy, PERFORMER, self.mob, outcome)
        entry = encode_hit_entry(
            self.legacy, self.mob.actor_identity, outcome.damage_wire,
            (self.mob.x, self.mob.y, self.mob.z), FLAGS_HIT)
        payload = mob_combat.encode_chit_result(
            self.legacy, PERFORMER, [entry])
        yesterday_pc, _yesterday_frame = self.legacy.make_runtime_vitals(
            [(CHIT_RESULT_VITAL_ID, mob_combat.CHIT_RESULT_VITAL_VERSION,
              payload)])
        empty_tail = mob_loot.RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN
        preserve_tail = mob_loot.RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN
        self.assertTrue(yesterday_pc.endswith(empty_tail))
        self.assertEqual(
            pc[:len(pc) - len(preserve_tail)],
            yesterday_pc[:len(yesterday_pc) - len(empty_tail)],
            "the body in front of the ground record is not yesterday's body")
        self.assertNotEqual(pc, yesterday_pc)
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_a_refusing_preserve_composer_costs_the_ground_and_says_so(self):
        # COO-DECISION 0646 item 4.  A shim whose serializer has "moved" makes
        # the preserve composer refuse; the site must then ship v141's own
        # bytes -- the damage number is never the thing that gets lost -- and
        # print the token, once, naming the exception type.
        class MovedSerializer:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                # One extra byte, only in the re-derivation path this lane
                # owns, so the composer and mob_loot's derivation disagree.
                return self._real.u16tag(tag, value) + b"\x00"

        ledger = open_ledger()
        _, outcome = apply_hit(
            ledger, PERFORMER, self.mob.actor_identity, 100)
        expected_pc, expected_frame = announce_frames(
            self.legacy, PERFORMER, self.mob, outcome)
        shim = MovedSerializer(self.legacy)
        printed = []
        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
        try:
            pc, frame = mob_combat.runtime_vitals_preserving_the_ground(
                shim, [(CHIT_RESULT_VITAL_ID,
                        mob_combat.CHIT_RESULT_VITAL_VERSION, b"\x00")])
        finally:
            builtins.print = real_print
        yesterday = self.legacy.make_runtime_vitals(
            [(CHIT_RESULT_VITAL_ID, mob_combat.CHIT_RESULT_VITAL_VERSION,
              b"\x00")])
        self.assertEqual((pc, frame), yesterday)
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].startswith(
            mob_combat.GROUND_VITALS_PRESERVE_REFUSED_TOKEN + " "))
        self.assertIn("MobLootContractError", printed[0])
        self.assertIn(mob_combat.GROUND_VITALS_PRESERVE_SITE, printed[0])
        self.assertTrue(printed[0].isascii())
        # and the healthy path is untouched by the shim's existence
        self.assertEqual(
            announce_frames(self.legacy, PERFORMER, self.mob, outcome),
            (expected_pc, expected_frame))

    def test_the_console_line_is_the_four_fields_the_ruling_names(self):
        """pf-adversary 9jrsei D3: renaming the token to XYZZY, freezing the
        site, hardcoding the exception name and blanking the detail all left
        the whole suite green -- so the line the operator is promised was
        four fields nothing checked.  It is checked here, literally, and the
        two variable fields are driven by TWO different exceptions so a
        constant cannot satisfy both."""
        self.assertEqual(
            mob_combat.GROUND_VITALS_PRESERVE_REFUSED_TOKEN,
            "GROUND_VITALS_PRESERVE_REFUSED")
        self.assertEqual(
            mob_combat.GROUND_VITALS_PRESERVE_SITE,
            "mob_combat.announce_frames")

        class Boom(Exception):
            pass

        class Shim:
            def __init__(self, real, raiser):
                self._real = real
                self._raiser = raiser

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                raise self._raiser("wire is on fire")

        seen = []
        for raiser in (Boom, TypeError):
            printed = []
            real_print = builtins.print
            builtins.print = lambda *a, **k: printed.append(
                " ".join(str(x) for x in a))
            try:
                pc, frame = mob_combat.runtime_vitals_preserving_the_ground(
                    Shim(self.legacy, raiser),
                    [(CHIT_RESULT_VITAL_ID, 2, b"\x00")])
            finally:
                builtins.print = real_print
            self.assertEqual(len(printed), 1)
            fields = printed[0].split(" ", 3)
            self.assertEqual(fields[0], "GROUND_VITALS_PRESERVE_REFUSED")
            self.assertEqual(fields[1], raiser.__name__)
            self.assertEqual(fields[2], "mob_combat.announce_frames")
            self.assertIn("wire is on fire", fields[3])
            seen.append(fields[1])
            self.assertEqual(
                (pc, frame),
                self.legacy.make_runtime_vitals(
                    [(CHIT_RESULT_VITAL_ID, 2, b"\x00")]))
        self.assertEqual(len(set(seen)), 2, "the exception name is a constant")

    def test_the_console_line_cannot_cost_the_damage_number(self):
        """pf-adversary 9jrsei D2, measured twice on this project already
        (rounds 86 and 142): the bridge console is cp874 strict, and a
        console that raises inside the branch whose whole job is to keep the
        damage number would take the damage number with it."""
        class Nasty(Exception):
            pass

        class Shim:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                raise Nasty("bad detail \u4e2d\u6587 and\na newline")

        vitals = [(CHIT_RESULT_VITAL_ID, 2, b"\x00")]
        # (a) an unmappable character never reaches the encoder
        printed = []
        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(
            " ".join(str(x) for x in a))
        try:
            first = mob_combat.runtime_vitals_preserving_the_ground(
                Shim(self.legacy), vitals)
        finally:
            builtins.print = real_print
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].isascii())
        self.assertNotIn("\n", printed[0])
        printed[0].encode("cp874")            # the real encoder, not a StringIO
        # (b) a console that refuses every write costs the line, not the frame
        def refuse(*_args, **_kwargs):
            raise ValueError("I/O operation on closed file")

        builtins.print = refuse
        try:
            second = mob_combat.runtime_vitals_preserving_the_ground(
                Shim(self.legacy), vitals)
        finally:
            builtins.print = real_print
        self.assertEqual(first, second)
        self.assertEqual(second, self.legacy.make_runtime_vitals(vitals))

    def test_a_dead_vitals_composer_is_not_reported_as_a_ground_refusal(self):
        """pf-adversary 9jrsei D4.  The preserve composer DRIVES
        make_runtime_vitals, so a composer that is down raises through the
        same except -- and the first draft printed 'only the ground list was
        lost' at the exact moment the damage number was being lost."""
        class Dead:
            def __getattr__(self, name):
                def boom(*_a, **_k):
                    raise RuntimeError("v141 vitals composer down")
                return boom

        printed = []
        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(
            " ".join(str(x) for x in a))
        try:
            with self.assertRaises(RuntimeError):
                mob_combat.runtime_vitals_preserving_the_ground(
                    Dead(), [(CHIT_RESULT_VITAL_ID, 2, b"\x00")])
        finally:
            builtins.print = real_print
        self.assertEqual(
            printed, [],
            "a lost damage number was reported as a ground-list refusal")

    def test_the_fall_back_does_not_swallow_a_broken_vitals_composer(self):
        # The one exception the site must NOT absorb: if make_runtime_vitals
        # itself fails there is no damage number to ship, and answering with
        # a silent empty frame would be worse than raising.
        class NoVitals:
            def __getattr__(self, name):
                raise AttributeError(name)

        with self.assertRaises(AttributeError):
            mob_combat.runtime_vitals_preserving_the_ground(
                NoVitals(), [(CHIT_RESULT_VITAL_ID, 1, b"")])

    # -- the SAME opt-in for the actors carrier (COO-DECISION 1044) --------
    #
    # ROUND jysbar, and this block exists because pf-adversary's pass on that
    # round found the wrapper shipped with ZERO tests: ten mutants survived,
    # including the two the vitals sibling above bled for (swallow the
    # fallback exception; print before composing it).  These are those tests,
    # for the other carrier.

    def _one_entry(self):
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=self.mob.max_hp)
        return self.legacy.make_remote_actor_entry(
            mob_combat.NPC_STYLE_ACTOR_TYPE, self.mob.actor_identity,
            [(mob_combat.NPC_ATTR_ID, body)])

    def _capture_print(self):
        printed = []
        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(
            " ".join(str(x) for x in a))
        return printed, real_print

    def test_a_refusing_actors_composer_costs_the_ground_and_says_so(self):
        class MovedSerializer:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                return self._real.u16tag(tag, value) + b"\x00"

        entries = [self._one_entry()]
        shim = MovedSerializer(self.legacy)
        printed, real_print = self._capture_print()
        try:
            pc, frame = mob_combat.remote_actors_preserving_the_ground(
                shim, entries, mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        finally:
            builtins.print = real_print
        self.assertEqual(
            (pc, frame), self.legacy.make_runtime_remote_actors(entries),
            "the refusal took the bar frame with it")
        self.assertEqual(len(printed), 1)
        fields = printed[0].split(" ", 3)
        self.assertEqual(
            fields[0], mob_combat.GROUND_ACTORS_PRESERVE_REFUSED_TOKEN)
        self.assertEqual(fields[1], "MobLootContractError")
        self.assertEqual(fields[2], "mob_combat.bar_frames")

    def test_the_site_named_on_the_console_is_the_site_that_refused(self):
        # The line is what a tester greps for, so the site has to travel and
        # has to be a name that exists.  A wrapper that dropped the argument
        # and printed a constant would pass everything else in this file.
        class Dead:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                raise RuntimeError("moved")

        entries = [self._one_entry()]
        seen = []
        for site in (mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR,
                     mob_combat.GROUND_ACTORS_PRESERVE_SITE_DEATH):
            printed, real_print = self._capture_print()
            try:
                mob_combat.remote_actors_preserving_the_ground(
                    Dead(self.legacy), entries, site)
            finally:
                builtins.print = real_print
            seen.append(printed[0].split(" ", 3)[2])
        self.assertEqual(seen, [mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR,
                                mob_combat.GROUND_ACTORS_PRESERVE_SITE_DEATH])
        # Both names have to resolve to something a reader can open.
        self.assertTrue(hasattr(mob_combat, "bar_frames"))
        module, _dot, function = (
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_DEATH).partition(".")
        self.assertEqual(module, "mob_death")
        import pirateforce_foundation.mob_death as _mob_death
        self.assertTrue(hasattr(_mob_death, function))

    def test_a_dead_actors_composer_is_not_reported_as_a_ground_refusal(self):
        """The 9jrsei D4 lesson, for the carrier that carries the corpse:
        the preserve composer DRIVES make_runtime_remote_actors, so a
        composer that is down raises through the same except -- and printing
        'only the ground list was lost' while the corpse frame is being lost
        is a lie the console would carry."""
        class Dead:
            def __getattr__(self, name):
                def boom(*_a, **_k):
                    raise RuntimeError("v141 actors composer down")
                return boom

        printed, real_print = self._capture_print()
        try:
            with self.assertRaises(RuntimeError):
                mob_combat.remote_actors_preserving_the_ground(
                    Dead(), [b"\x01"],
                    mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        finally:
            builtins.print = real_print
        self.assertEqual(
            printed, [],
            "a lost corpse frame was reported as a ground-list refusal")

    def test_the_fall_back_does_not_swallow_a_broken_actors_composer(self):
        class NoActors:
            def __getattr__(self, name):
                raise AttributeError(name)

        with self.assertRaises(AttributeError):
            mob_combat.remote_actors_preserving_the_ground(
                NoActors(), [b"\x01"],
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)

    def test_a_console_that_cannot_be_written_costs_the_line_not_the_frame(self):
        class Nasty(Exception):
            pass

        class Shim:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                raise Nasty("bad detail 中文 and\na newline")

        entries = [self._one_entry()]
        printed, real_print = self._capture_print()
        try:
            first = mob_combat.remote_actors_preserving_the_ground(
                Shim(self.legacy), entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        finally:
            builtins.print = real_print
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].isascii())
        self.assertNotIn("\n", printed[0])
        printed[0].encode("cp874")

        def refuse(*_args, **_kwargs):
            raise ValueError("I/O operation on closed file")

        real_print = builtins.print
        builtins.print = refuse
        try:
            second = mob_combat.remote_actors_preserving_the_ground(
                Shim(self.legacy), entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        finally:
            builtins.print = real_print
        self.assertEqual(first, second)
        self.assertEqual(
            second, self.legacy.make_runtime_remote_actors(entries))

    def test_an_iterator_of_entries_is_not_drained_before_the_fall_back(self):
        """The mutant that survives if ``entries = list(entries)`` goes away:
        the preserve composer consumes the iterable, and the fall back would
        then compose a ZERO-entry collection -- which, against a
        replace-by-omission consumer (RE-092), is a world wipe rather than a
        lost ground list."""
        class Shim:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                if value == 0 and tag == mob_loot.ELEMENT_LIST_COUNT_TAG:
                    raise RuntimeError("ground record refused")
                return self._real.u16tag(tag, value)

        entries = [self._one_entry(), self._one_entry()]
        printed, real_print = self._capture_print()
        try:
            pc, _frame = mob_combat.remote_actors_preserving_the_ground(
                Shim(self.legacy), iter(entries),
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        finally:
            builtins.print = real_print
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[offset + 2:offset + 5], self.legacy.u16tag(0x12, 2))
        self.assertEqual(pc, self.legacy.make_runtime_remote_actors(entries)[0])

    def test_a_serializer_that_ignores_the_mask_value_refuses(self):
        """The byte-for-byte comparisons in the preserve composer are not a
        restatement of the equality above them: a primitive that ACCEPTS the
        preserve mask and writes something else passes that equality and is
        caught here.  Without them this ships a frame whose mask is not the
        mask this lane asked for."""
        class IgnoresTheValue:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u8tag(self, tag, value):
                if value == mob_loot.RUNTIME_RES_ACTORS_PRESERVE_DERIVED_MASK:
                    return self._real.u8tag(tag, 0x02)
                return self._real.u8tag(tag, value)

        with self.assertRaises(mob_loot.MobLootContractError) as caught:
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                IgnoresTheValue(self.legacy), [self._one_entry()])
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_COMPOSED_BYTES_OFF_PIN)

    # -- the gate the fourth carrier needs (round suovqw) ------------------

    def _reset_liveness_reports(self):
        before = set(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED)
        mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear()
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear(),
                mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.update(
                    before)))

    def test_the_bar_and_the_dead_frame_did_not_move_one_byte(self):
        """The default is TODAY.  ``COO-DECISION 1044`` item 4 ordered bar ->
        dying -> dead to preserve unconditionally, and adding a gate for a
        FOURTH carrier may not quietly narrow those three."""
        entries = [self._one_entry()]
        self.assertEqual(
            mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR),
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, entries))
        pc, _frame = bar_frames(
            self.legacy, self.mob, self.mob.max_hp - 100)
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[offset + 1], 0x0A)

    def test_a_count_of_zero_sends_the_bytes_the_server_sends_today(self):
        entries = [self._one_entry(), self._one_entry()]
        printed, real_print = self._capture_print()
        self._reset_liveness_reports()
        try:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                ground_rows_left=0)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(
            printed, [],
            "an empty floor is an ordinary frame, not a console event")

    def test_a_count_above_zero_keeps_the_ground_on_the_fourth_carrier(self):
        entries = [self._one_entry()]
        answer = mob_combat.remote_actors_preserving_the_ground(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            ground_rows_left=3)
        self.assertEqual(
            answer,
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, entries))

    def test_an_unreadable_count_is_said_once_per_site_and_never_per_click(self):
        """A cell that never reached the call site is a WIRING hole a tester
        reading GT-204 has to see -- and one that would otherwise print a
        line on every click of the session."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for _click in range(5):
                answer = mob_combat.remote_actors_preserving_the_ground(
                    self.legacy, entries,
                    mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                    ground_rows_left=mob_loot.GROUND_LIVENESS_UNKNOWN)
            other = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR,
                ground_rows_left="not a count")
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(
            other, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(len(printed), 2, printed)
        self.assertTrue(printed[0].startswith(
            mob_combat.GROUND_ACTORS_LIVENESS_UNKNOWN_TOKEN + " "))
        self.assertIn(
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, printed[0])
        self.assertIn(mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR, printed[1])

    def test_a_console_that_refuses_the_line_loses_the_line_not_the_frame(self):
        entries = [self._one_entry()]
        self._reset_liveness_reports()

        def refuse(*_args, **_kwargs):
            raise ValueError("I/O operation on closed file")

        real_print = builtins.print
        builtins.print = refuse
        try:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                ground_rows_left=mob_loot.GROUND_LIVENESS_UNKNOWN)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        # ...and the report was NOT spent on a write that never landed: the
        # next call, with a console that works, still says it.
        printed, real_print = self._capture_print()
        try:
            mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                ground_rows_left=mob_loot.GROUND_LIVENESS_UNKNOWN)
        finally:
            builtins.print = real_print
        self.assertEqual(len(printed), 1, printed)

    def test_a_site_name_the_bridge_console_cannot_encode_still_reports(self):
        # cp874 with errors='strict': one unmappable character inside print
        # raises, and the raise would come from the branch whose whole job is
        # to keep the frame.
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, "lane_hooks.\u4e2d\u0e04",
                ground_rows_left=mob_loot.GROUND_LIVENESS_UNKNOWN)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(len(printed), 1, printed)
        self.assertEqual(printed[0], printed[0].encode(
            "ascii", "strict").decode("ascii"))

    def test_none_is_not_a_count_here_either(self):
        """pf-adversary D2.  ``None`` used to mean "preserve unconditionally"
        in this function and "today's bytes" in the sibling three lines of
        docstring away -- so a lane wiring the click responder without a cell
        yet would have shipped the never-observed shape on 97 actors of every
        click, silently.  The default is a SENTINEL now."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                ground_rows_left=None)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("not_a_count", printed[0])

    def test_the_wrapper_never_disagrees_with_the_composer_it_ships(self):
        """One gate, not two implementations of one gate (pf-adversary D13):
        for every value, what comes out of this wrapper is what comes out of
        the sibling -- the sentinel default being the one exception, which is
        the bar / dying / dead behaviour this round may not move."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for value in (0, 1, 5, -1, mob_loot.GROUND_LIVENESS_NO_CELL,
                          mob_loot.GROUND_LIVENESS_CELL_REFUSED, None, True,
                          "3", 2.0, object()):
                with self.subTest(value=repr(value)):
                    self.assertEqual(
                        mob_combat.remote_actors_preserving_the_ground(
                            self.legacy, entries, "lane_hooks.agreement",
                            ground_rows_left=value),
                        (mob_loot
                         .preserve_ground_in_runtime_res_remote_actors_when_live(
                             self.legacy, entries, ground_rows_left=value)))
        finally:
            builtins.print = real_print

    def test_each_responder_gets_its_own_report_and_so_does_each_cause(self):
        """pf-adversary D3 and D4.  LANE-A has four responders; one shared
        site literal let the first to fire silence the other three forever.
        And a site whose cause changes has a second thing to say."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for scene_id in (1, 2, 14, 4001):
                mob_combat.remote_actors_preserving_the_ground(
                    self.legacy, entries, mob_combat.choose_npc_site(scene_id),
                    ground_rows_left=mob_loot.GROUND_LIVENESS_NO_CELL)
            # the same site again, same cause: silent
            mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, mob_combat.choose_npc_site(2),
                ground_rows_left=mob_loot.GROUND_LIVENESS_NO_CELL)
            # the same site, a DIFFERENT cause: it may say so
            mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, mob_combat.choose_npc_site(2),
                ground_rows_left=mob_loot.GROUND_LIVENESS_CELL_REFUSED)
        finally:
            builtins.print = real_print
        self.assertEqual(len(printed), 5, printed)
        for scene_id in (1, 2, 14, 4001):
            self.assertTrue(
                any("scene_%d " % scene_id in line for line in printed),
                (scene_id, printed))
        self.assertTrue(any(line.endswith("cell_refused")
                            for line in printed), printed)

    def test_the_wrapper_composes_through_the_sibling_not_its_own_copy(self):
        """N10, the one mutant the two-file battery let live: replacing the
        delegation with a second ``make_runtime_remote_actors`` call is
        byte-identical TODAY and is exactly the divergence D13 named (it also
        re-adds a call site the static verifier pins).  Pinned here so the
        two gates cannot drift apart in this file's own suite."""
        from unittest import mock
        entries = [self._one_entry()]
        sentinel = ("pc", "frame")
        self._reset_liveness_reports()
        with mock.patch.object(
                mob_loot,
                "preserve_ground_in_runtime_res_remote_actors_when_live",
                return_value=sentinel) as gate:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, "lane_hooks.delegation",
                ground_rows_left=0)
        self.assertIs(answer, sentinel)
        self.assertEqual(gate.call_count, 1)
        self.assertEqual(gate.call_args.kwargs["ground_rows_left"], 0)

    def test_the_reporter_says_whether_it_was_the_one_that_printed(self):
        # Its docstring claims the return value is what a test can drive, so
        # a test drives it (pf-adversary D5/M17).
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            first = mob_combat._report_liveness_unknown_once(
                "lane_hooks.probe", "no_cell")
            again = mob_combat._report_liveness_unknown_once(
                "lane_hooks.probe", "no_cell")
            other = mob_combat._report_liveness_unknown_once(
                "lane_hooks.probe", "cell_refused")
        finally:
            builtins.print = real_print
        self.assertEqual((first, again, other), (True, False, True))
        self.assertEqual(len(printed), 2, printed)

        def refuse(*_args, **_kwargs):
            raise ValueError("I/O operation on closed file")

        real_print = builtins.print
        builtins.print = refuse
        try:
            self.assertFalse(mob_combat._report_liveness_unknown_once(
                "lane_hooks.other", "no_cell"))
        finally:
            builtins.print = real_print

    def test_a_caller_that_names_a_site_per_click_cannot_grow_the_set(self):
        """"Once per site" is only bounded while the sites are literals.  A
        site string built per click would otherwise print every click AND
        leak a key for each one, for the life of the process."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for click in range(
                    mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_SITE_CAP + 40):
                mob_combat.remote_actors_preserving_the_ground(
                    self.legacy, entries, "lane_hooks.click_%d" % click,
                    ground_rows_left=mob_loot.GROUND_LIVENESS_UNKNOWN)
        finally:
            builtins.print = real_print
        # the cap is pinned as a LITERAL, not against itself: a round that
        # quietly lowers the reporting budget to 2 must go red here
        # (pf-adversary, second pass, D3).
        self.assertEqual(
            mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_SITE_CAP, 32)
        # THIS FAMILY'S LINES, not every line on the console: round t8z97r
        # added a once-per-process status line to this same path, and a
        # count of everything printed would make an unrelated line look
        # like a budget failure.
        printed = [line for line in printed
                   if line.startswith("GROUND_ACTORS_LIVENESS_")]
        self.assertEqual(len(printed), 33)
        self.assertEqual(
            len([line for line in printed if line.startswith(
                mob_combat.GROUND_ACTORS_LIVENESS_UNKNOWN_TOKEN + " ")]), 32)
        # ...and silence past the cap is ANNOUNCED, exactly once, so nobody
        # reads "no more lines" as "no more wiring holes".
        self.assertEqual(
            printed[-1], "%s 32" % (
                mob_combat.GROUND_ACTORS_LIVENESS_SUPPRESSED_TOKEN,))
        self.assertEqual(
            len(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED), 33)

    def test_a_site_whose_own_str_raises_is_still_reported(self):
        """pf-adversary, second pass, D5: a hole that cannot print its own
        name is still a hole, and reporting nothing for it hides it for the
        session."""
        class BadSite:
            def __str__(self):
                raise ValueError("cp874")

        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, BadSite(),
                ground_rows_left=mob_loot.GROUND_LIVENESS_NO_CELL)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("site_unprintable", printed[0])
        self.assertIn("BadSite", printed[0])

    def test_an_unhashable_count_costs_the_mask_and_not_the_frame(self):
        """pf-adversary, second pass, D14.  ``dict.get`` RAISES for a key it
        cannot hash, and the cause lookup runs outside every ``try`` on this
        path -- so a list or a dict in that keyword took the whole frame."""
        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for value in ([1], {"rows": 1}, {1}, bytearray(b"1"), (1,)):
                with self.subTest(value=repr(value)):
                    self.assertEqual(
                        mob_combat.remote_actors_preserving_the_ground(
                            self.legacy, entries, "lane_hooks.unhashable",
                            ground_rows_left=value),
                        self.legacy.make_runtime_remote_actors(entries))
        finally:
            builtins.print = real_print
        self.assertEqual(len(printed), 1, "one site, one cause, one line")
        self.assertIn("not_a_count", printed[0])

    def test_a_frame_the_player_never_got_does_not_spend_the_report(self):
        """pf-adversary, second pass, D6: compose FIRST, print SECOND -- the
        same ordering rule the refusal path below states three times.  A
        carrier that is down raises its own exception, and the one line the
        site will ever get must still be there for the call that works."""
        class DownCarrier:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def make_runtime_remote_actors(self, entries):
                raise RuntimeError("carrier is down")

        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            with self.assertRaises(RuntimeError):
                mob_combat.remote_actors_preserving_the_ground(
                    DownCarrier(self.legacy), entries, "lane_hooks.down",
                    ground_rows_left=mob_loot.GROUND_LIVENESS_NO_CELL)
            self.assertEqual(printed, [], "the frame was lost, not the count")
            answer = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries, "lane_hooks.down",
                ground_rows_left=mob_loot.GROUND_LIVENESS_NO_CELL)
        finally:
            builtins.print = real_print
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertEqual(len(printed), 1, printed)
        self.assertIn("no_cell", printed[0])

    def test_a_count_that_is_an_int_subclass_is_a_count(self):
        """pf-adversary, second pass, D2: ``type(x) is int`` cleared the loot
        of a responder counting rows with an ``IntEnum`` AND printed a
        wiring-hole line about a call site that was wired correctly."""
        import enum

        class Rows(enum.IntEnum):
            THREE = 3

        class Count(int):
            pass

        entries = [self._one_entry()]
        preserved = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, entries)
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            for value in (Rows.THREE, Count(2)):
                with self.subTest(value=repr(value)):
                    self.assertEqual(
                        mob_combat.remote_actors_preserving_the_ground(
                            self.legacy, entries, "lane_hooks.subclass",
                            ground_rows_left=value),
                        preserved)
            for value in (Count(0), Rows.THREE - 3):
                with self.subTest(value=repr(value)):
                    self.assertEqual(
                        mob_combat.remote_actors_preserving_the_ground(
                            self.legacy, entries, "lane_hooks.subclass",
                            ground_rows_left=value),
                        self.legacy.make_runtime_remote_actors(entries))
        finally:
            builtins.print = real_print
        self.assertEqual(printed, [], "a real count is not a wiring hole")
        # ...and bool is still not a count, which is the reason the naive
        # isinstance() check was refused in the first place.
        self.assertFalse(mob_loot.ground_liveness_is_readable(True))
        self.assertFalse(mob_loot.ground_liveness_is_readable(False))

    def test_a_refusal_on_the_live_path_still_falls_back_with_its_own_line(self):
        # The gate must not swallow the refusal path the wrapper existed for.
        class MovedSerializer:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def u16tag(self, tag, value):
                if value == 0 and tag == mob_loot.ELEMENT_LIST_COUNT_TAG:
                    raise RuntimeError("ground record refused")
                return self._real.u16tag(tag, value)

        entries = [self._one_entry()]
        self._reset_liveness_reports()
        printed, real_print = self._capture_print()
        try:
            pc, _frame = mob_combat.remote_actors_preserving_the_ground(
                MovedSerializer(self.legacy), entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                ground_rows_left=2)
        finally:
            builtins.print = real_print
        self.assertEqual(
            pc, self.legacy.make_runtime_remote_actors(entries)[0])
        self.assertEqual(len(printed), 1, printed)
        self.assertTrue(printed[0].startswith(
            mob_combat.GROUND_ACTORS_PRESERVE_REFUSED_TOKEN + " "))

    def test_the_announce_frame_refuses_a_mismatched_mob(self):
        ledger = open_ledger()
        _, outcome = apply_hit(ledger, PERFORMER, self.mob.actor_identity, 10)
        other = [m for m in self.roster if m.actor_identity
                 != self.mob.actor_identity][0]
        with self.assertRaises(MobCombatContractError) as caught:
            announce_frames(self.legacy, PERFORMER, other, outcome)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    # -- the inbound seam -------------------------------------------------

    def test_an_ea7d_action_on_a_monster_drives_a_hit(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        step = attack_from_observed_action(
            self.legacy, mob_aggro, ledger, state,
            {"field_qword_20": self.mob.actor_identity},
            PERFORMER, self.attacker,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step.outcome.target_identity, self.mob.actor_identity)
        self.assertLess(step.outcome.hp_after, self.mob.max_hp)

    def test_an_ea7d_action_on_a_townsperson_is_not_an_error(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        self.assertIsNone(attack_from_observed_action(
            self.legacy, mob_aggro, ledger, state,
            {"field_qword_20": 0x2001}, PERFORMER, self.attacker,
        ))

    def test_malformed_action_fields_are_refused_by_name(self):
        ledger = open_ledger()
        with self.assertRaises(MobCombatContractError) as caught:
            attack_from_observed_action(
                self.legacy, mob_aggro, ledger, None, {}, PERFORMER,
                self.attacker)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_ACTION_FIELDS_MALFORMED)

    # -- what the adversarial review of 2026-08-26 broke -------------------

    def test_an_outcome_cannot_announce_one_number_and_subtract_another(self):
        # D4.  This record used to be the only unvalidated one in the module,
        # and announce_frames / apply_threat / describe_step all took whatever
        # they were handed.  apply_hit is not the only builder: the chief's
        # wiring and the death lane both will be.
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -1, FLAGS_HIT,
                3857, 2893, 3857, 0, False, False)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_OUTCOME_SELF_CONTRADICTORY)
        with self.assertRaises(MobCombatContractError):
            # the balance moved 100 while the hit says 964
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -964, FLAGS_HIT,
                3857, 3757, 3857, 0, False, False)
        with self.assertRaises(MobCombatContractError):
            # at_floor that does not agree with hp_after
            mob_combat.HitOutcome(
                PERFORMER, self.mob.actor_identity, 964, -964, FLAGS_HIT,
                3857, 2893, 3857, 0, True, True)

    def test_two_hits_in_one_tick_cannot_both_be_committed(self):
        # The concurrency case: two players action the same monster before
        # either write lands.  Without a compare-and-swap both announce -964
        # and one subtraction is lost - 1928 announced, 964 subtracted.
        ledger = open_ledger()
        first = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER,
            self.attacker)
        second = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER + 1,
            self.attacker)
        self.assertEqual(first.base_generation, second.base_generation)
        stored = mob_combat.commit_step(ledger, first)
        self.assertEqual(stored.generation, ledger.generation + 1)
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.commit_step(stored, second)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_LEDGER_STALE)

    def test_a_hit_with_no_room_left_sends_nothing_at_all(self):
        # D5.  The first draft answered a real 964-damage hit on a floored
        # monster with a MISS frame: the wire told the client the player had
        # missed when the formula said otherwise.
        thumping = Combatant(level=1000, ability_str=100000, ability_con=0)
        ledger = open_ledger()
        first = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER, thumping)
        self.assertEqual(first.outcome.hp_after, HP_FLOOR)
        second = strike(
            self.legacy, None, first.ledger, None, self.mob, PERFORMER,
            thumping)
        self.assertTrue(second.outcome.no_room)
        self.assertEqual(second.frames, ())
        self.assertEqual(second.announce_frame, b"")
        self.assertGreater(second.outcome.clamped_by, 0)
        self.assertTrue(
            any("nothing sent" in line for line in describe_step(second)))

    def test_a_dropped_threat_fold_is_recorded_not_inferred(self):
        # D6.  mob_aggro absorbs damage silently in its return and dead phases
        # - its declared design - so a driver that cannot tell reports a
        # monster as aggroed when it is not.
        ledger = open_ledger()
        returning = mob_aggro.MobAiState(
            phase=mob_aggro.PHASE_RETURN,
            leash_origin=(self.mob.x, self.mob.y, self.mob.z),
            threat=(), target_identity=None, ticks_since_attack=0)
        step = strike(
            self.legacy, mob_aggro, ledger, returning, self.mob, PERFORMER,
            self.attacker)
        self.assertLess(step.outcome.hp_after, self.mob.max_hp)
        self.assertEqual(step.aggro_state.threat, ())
        self.assertFalse(step.threat_recorded)
        self.assertTrue(
            any("threat NOT recorded" in line for line in describe_step(step)))

    def test_the_threat_handle_is_optional_and_that_is_the_wiring(self):
        # D8.  Passing mob_aggro in makes a lane whose production_allowed is
        # False reachable from dispatch through an argument no static scan can
        # see.  The supported production wiring passes None.
        ledger = open_ledger()
        step = strike(
            self.legacy, None, ledger, None, self.mob, PERFORMER,
            self.attacker)
        self.assertFalse(step.threat_recorded)
        self.assertEqual(len(step.frames), 2)
        self.assertIn("None", mob_combat.MOB_COMBAT_WIRING)
        self.assertIn("commit_step", mob_combat.MOB_COMBAT_WIRING)
        self.assertTrue(mob_combat.MOB_COMBAT_THREAT_HANDLE_IS_OPTIONAL)

    def test_a_ledger_row_from_another_roster_is_refused(self):
        # D16.  With a mismatched ceiling the announced number came from the
        # roster row and the bar frame from the ledger row.
        row = MobBalance(self.mob.actor_identity, 100, 100)
        with self.assertRaises(MobCombatContractError) as caught:
            strike(
                self.legacy, None, CombatLedger((row,)), None, self.mob,
                PERFORMER, self.attacker)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER)

    def test_a_roster_ledger_desync_is_refused_not_silently_ignored(self):
        # D7.  This used to return None, indistinguishable from the ordinary
        # "the player actioned a townsperson" case, and that line had never
        # executed.
        rows = tuple(
            row for row in open_ledger().balances
            if row.actor_identity != self.mob.actor_identity)
        with self.assertRaises(MobCombatContractError) as caught:
            attack_from_observed_action(
                self.legacy, None, CombatLedger(rows), None,
                {"field_qword_20": self.mob.actor_identity}, PERFORMER,
                self.attacker)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    def test_an_unsorted_ledger_is_refused_not_quietly_re_sorted(self):
        # D12.  The module promises no silent coercion; the sibling
        # mob_aggro.MobAiState refuses this exact shape by name.
        rows = open_ledger().balances
        with self.assertRaises(MobCombatContractError) as caught:
            CombatLedger(tuple(reversed(rows)))
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_LEDGER_NOT_SORTED)

    def test_every_named_refusal_reason_can_actually_happen(self):
        # D11.  Two of the eighteen names could not occur: one was raised
        # nowhere and one sat behind an unreachable branch.  A named refusal
        # that cannot happen is a lie told to whoever counts them.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        raised = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise):
                continue
            call = node.exc
            if (isinstance(call, ast.Call)
                    and getattr(call.func, "id", "") == "MobCombatContractError"
                    and call.args
                    and isinstance(call.args[0], ast.Name)):
                raised.add(getattr(mob_combat, call.args[0].id))
        self.assertEqual(
            sorted(raised),
            sorted(mob_combat.MOB_COMBAT_REFUSAL_REASONS),
            "a refusal is declared and never raised, or raised and never "
            "declared")
        # and the one that used to be unreachable behind a range check
        with self.assertRaises(MobCombatContractError) as caught:
            mob_combat.require_damage_wire(mob_combat.DAMAGE_WIRE_MIN - 1)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DAMAGE_WIRE_OUT_OF_RANGE)

    # -- the lane's own rules ---------------------------------------------

    def test_this_lane_needs_no_flag(self):
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        # Checked on NAMES rather than on raw text: the pin document says
        # "no_scenario_flag" in a string value, and a substring search would
        # either fail on that or have to be weakened to nothing.  What must not
        # exist is a scenario or unlock SEAM - a constant, a parameter or a
        # function this lane could be gated behind.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.keyword) and node.arg:
                names.add(node.arg)
        for name in sorted(names):
            lowered = name.lower()
            self.assertNotIn(
                "scenario", lowered,
                "a production lane must not carry a scenario seam: %s" % name)
            self.assertNotIn(
                "unlock", lowered,
                "a production lane must not carry an unlock seam: %s" % name)

    def test_this_module_imports_no_probe_lane(self):
        # Walked with ast, not matched on line prefixes.  The first draft used
        # startswith("import ", "from ") and an adversarial review showed three
        # bypasses in one minute: an indented import inside a function, a
        # parenthesised multi-line import, and both together.  A tripwire with
        # a documented bypass is worse than none, because it is quoted.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_combat.py").read_text(
                encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported.extend(alias.name for alias in node.names)
        for name in imported:
            self.assertNotIn("hypothesis", name)
            self.assertNotIn("mob_aggro", name)
        self.assertIn("field_mobs", imported)

    def test_determinism_two_runs_agree(self):
        def run():
            ledger = open_ledger()
            state = mob_aggro.initial_state(
                (self.mob.x, self.mob.y, self.mob.z))
            step = strike(
                self.legacy, mob_aggro, ledger, state, self.mob,
                PERFORMER, self.attacker)
            return (step.ledger, step.aggro_state, step.outcome,
                    step.announce_frame, step.bar_frame)
        self.assertEqual(run(), run())

    def test_the_driver_reproduces_the_ladder_gt035_watched(self):
        # The strongest control this lane has.  Two observers watched a real
        # client walk this monster's bar 3857 -> 2893 -> 2893 -> 771 in GT-035
        # (2026-08-25).  Those numbers came out of a probe lane pinned to one
        # target; this is a general production driver, and it must land on the
        # SAME two damage numbers for the same two attacker profiles - or the
        # thing the owner boots without a flag is not the thing anybody saw.
        # ROUND 8ftmbx: ~~self.mob~~.  The bar those two observers watched
        # belonged to bg0001 placement 30 as the set-number reading rendered
        # it -- level 27, 3857 HP -- and COO-DECISION 2026-08-29T00:41+07:00
        # withdrew that row from the shipped roster.  The subject here is
        # therefore the actor the ladder was watched ON, rebuilt from the row
        # the generated table preserves for this, not the roster's new control
        # row: 916 is level 100 with 198,125 HP, and running this comparison
        # against it would have "reproduced" numbers nobody ever saw.
        subject = field_mobs.gt035_observed_subject()
        self.assertEqual(subject.max_hp, 3857)
        ledger = open_ledger(roster=(subject,))
        profiles = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_ATTACKER_PROFILES
        pinned = hostile_hp_link_hypothesis.HOSTILE_HP_LINK_DAMAGE_PINNED
        for name, expected_after in (("MOB_WEAK", 2893), ("MOB_STRONG", 771)):
            level, ability_str = profiles[name]
            attacker = Combatant(
                level=level, ability_str=ability_str, ability_con=0)
            damage = resolve_damage(attacker, mob_defender(subject))
            ledger, outcome = apply_hit(
                ledger, PERFORMER, subject.actor_identity, damage)
            self.assertEqual(outcome.damage_wire, pinned[name])
            self.assertEqual(outcome.hp_after, expected_after)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_ABILITY_CON,
            mob_combat.MOB_ABILITY_CON)
        self.assertEqual(
            hostile_hp_link_hypothesis.DEFENDER_LEVEL, subject.level)

    def test_the_committed_pin_is_what_the_code_produces(self):
        path = ROOT / "scenarios/combat_first_hit_001.json"
        raw = path.read_bytes()
        self.assertTrue(raw.decode("utf-8").isascii())
        committed = json.loads(raw.decode("ascii"))
        # ROUND 8ftmbx: ~~a roster lookup on PIN_PLACEMENT_INDEX~~.  The row
        # this pin's numbers were watched on is withdrawn from the shipped
        # roster (COO-DECISION 2026-08-29T00:41+07:00), and the pin
        # deliberately did NOT follow the table -- see mob_combat.pin_subject
        # on why moving it to the new control row would have compared today's
        # arithmetic against numbers nobody saw.
        pinned_mob = mob_combat.pin_subject()
        self.assertEqual(
            pinned_mob.placement_index, mob_combat.PIN_PLACEMENT_INDEX)
        self.assertNotIn(
            pinned_mob.placement_index,
            [m.placement_index for m in self.roster],
            "the GT-035 subject is a shipped roster row again: this pin has "
            "to be re-read before it can be trusted")
        self.assertEqual(committed, pin_document(self.legacy, pinned_mob))
        self.assertTrue(committed["production_allowed"])
        self.assertFalse(committed["test_only"])
        self.assertEqual(
            committed["selection"], "none_default_behaviour_no_scenario_flag")
        self.assertEqual(committed["damage_wire"], -964)
        self.assertEqual(committed["hp_after"], 2893)
        self.assertGreaterEqual(len(committed["nonclaims"]), 6)

    def test_the_pin_document_computes_its_numbers(self):
        pin = pin_document(self.legacy, self.mob, self.attacker)
        self.assertEqual(pin["target_name"], ascii(self.mob.display_name))
        self.assertTrue(pin["not_a_scenario"])
        self.assertEqual(
            pin["target_position"], [self.mob.x, self.mob.y, self.mob.z])
        self.assertEqual(pin["target_faction"], field_mobs.FIELD_MOB_FACTION)
        self.assertFalse(pin["threat_recorded"])
        self.assertEqual(pin["max_hp"], self.mob.max_hp)
        self.assertEqual(pin["damage_wire"], -pin["damage"])
        self.assertEqual(pin["hp_after"], pin["max_hp"] - pin["damage"])
        self.assertTrue(pin["production_allowed"])
        self.assertIn("runtime.py", pin["wiring"])

    def test_describe_step_names_the_floor_when_it_bites(self):
        ledger = open_ledger()
        state = mob_aggro.initial_state((self.mob.x, self.mob.y, self.mob.z))
        thumping = Combatant(level=1000, ability_str=100000, ability_con=0)
        step = strike(
            self.legacy, mob_aggro, ledger, state, self.mob,
            PERFORMER, thumping)
        lines = describe_step(step)
        # ~~"clamped by"~~ with the floor at 0 the clamp is overkill, not a
        # monster held one point above death, and the line says so.
        self.assertTrue(any("overkill by" in line for line in lines))
        self.assertTrue(any("death due" in line for line in lines))
        self.assertTrue(any("mob_death.kill" in line for line in lines))

    # -- attack cadence (PANYA-REFERENCE 2026-08-27 16:35, RE-110) ---------
    #
    # These pin the "spam-click = runaway damage" gate ahead of RE-110's
    # real number: a fast-second-attack rejection, an accept once the window
    # elapses, and no cross-performer blocking.  ``ATTACK_CADENCE_MS_
    # PROVISIONAL`` is used throughout rather than a hard-coded literal, so a
    # later round that swaps the constant does not also have to hand-edit
    # every test's arithmetic.

    OTHER_PERFORMER = 0x750060

    def test_the_first_attack_from_a_new_performer_is_accepted(self):
        cadence = open_cadence_ledger()
        check = check_attack_cadence(cadence, PERFORMER, 1_000)
        self.assertTrue(check.accepted)
        self.assertEqual(check.early_by_ms, 0)
        self.assertEqual(
            check.cadence.last_accepted_at(PERFORMER), 1_000)

    def test_a_second_attack_inside_the_window_is_rejected(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        too_soon_at = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL - 1
        second = check_attack_cadence(first.cadence, PERFORMER, too_soon_at)
        self.assertFalse(second.accepted)
        self.assertEqual(second.early_by_ms, 1)
        # a rejection must not move the ledger: the window is measured from
        # the last ACCEPTED attack, not from the last attempt.
        self.assertEqual(second.cadence, first.cadence)
        self.assertEqual(second.cadence.last_accepted_at(PERFORMER), 1_000)

    def test_an_attack_exactly_at_the_window_is_accepted(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        exactly_at = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL
        second = check_attack_cadence(first.cadence, PERFORMER, exactly_at)
        self.assertTrue(second.accepted)
        self.assertEqual(
            second.cadence.last_accepted_at(PERFORMER), exactly_at)

    def test_an_attack_after_the_window_elapses_is_accepted(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        well_after = 1_000 + ATTACK_CADENCE_MS_PROVISIONAL + 5_000
        second = check_attack_cadence(first.cadence, PERFORMER, well_after)
        self.assertTrue(second.accepted)

    def test_a_burst_of_rejects_does_not_slide_its_own_deadline(self):
        # Five rapid clicks after one accepted hit: the fifth is scored
        # against the SAME accepted timestamp as the second, not against the
        # fourth reject.
        cadence = open_cadence_ledger()
        cadence = check_attack_cadence(cadence, PERFORMER, 0).cadence
        early_by_values = []
        for offset in (10, 20, 30, 40, 50):
            check = check_attack_cadence(cadence, PERFORMER, offset)
            self.assertFalse(check.accepted)
            early_by_values.append(check.early_by_ms)
        expected = [
            ATTACK_CADENCE_MS_PROVISIONAL - offset
            for offset in (10, 20, 30, 40, 50)
        ]
        self.assertEqual(early_by_values, expected)

    def test_two_performers_are_not_cross_blocked(self):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        second = check_attack_cadence(
            first.cadence, self.OTHER_PERFORMER, 1_000 + 1)
        self.assertTrue(second.accepted)
        self.assertEqual(
            second.cadence.last_accepted_at(PERFORMER), 1_000)
        self.assertEqual(
            second.cadence.last_accepted_at(self.OTHER_PERFORMER), 1_001)

    def test_clock_skew_fails_closed_not_open(self):
        # A caller-supplied timestamp earlier than this performer's own last
        # accepted one must never be read as "plenty of time has passed".
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 10_000)
        second = check_attack_cadence(first.cadence, PERFORMER, 1)
        self.assertFalse(second.accepted)
        self.assertEqual(second.early_by_ms, ATTACK_CADENCE_MS_PROVISIONAL)

    def test_a_rejection_console_line_names_the_performer_and_the_shortfall(
        self,
    ):
        cadence = open_cadence_ledger()
        first = check_attack_cadence(cadence, PERFORMER, 1_000)
        second = check_attack_cadence(first.cadence, PERFORMER, 1_050)
        lines = describe_cadence_rejection(second)
        self.assertEqual(len(lines), 1)
        self.assertIn("0x%X" % PERFORMER, lines[0])
        self.assertIn("REJECTED", lines[0])
        self.assertIn("%d" % second.early_by_ms, lines[0])
        self.assertIn("RE-110", lines[0])
        self.assertTrue(lines[0].isascii())

    def test_describe_cadence_rejection_refuses_an_accepted_check(self):
        cadence = open_cadence_ledger()
        accepted = check_attack_cadence(cadence, PERFORMER, 1_000)
        with self.assertRaises(MobCombatContractError) as caught:
            describe_cadence_rejection(accepted)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_CADENCE_OUTCOME_SELF_CONTRADICTORY)

    def test_cadence_ledger_refuses_unsorted_rows(self):
        rows = (CadenceRecord(2, 0), CadenceRecord(1, 0))
        with self.assertRaises(MobCombatContractError) as caught:
            AttackCadenceLedger(rows)
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_CADENCE_NOT_SORTED)

    def test_cadence_ledger_refuses_duplicate_identity(self):
        rows = (CadenceRecord(1, 0), CadenceRecord(1, 5))
        with self.assertRaises(MobCombatContractError) as caught:
            AttackCadenceLedger(rows)
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_DUPLICATE_CADENCE_IDENTITY)

    def test_cadence_ledger_never_shrinks_and_keys_by_performer(self):
        cadence = open_cadence_ledger()
        cadence = check_attack_cadence(cadence, PERFORMER, 0).cadence
        cadence = check_attack_cadence(
            cadence, self.OTHER_PERFORMER, 0).cadence
        self.assertEqual(
            sorted(cadence.identities()),
            sorted((PERFORMER, self.OTHER_PERFORMER)))
        # a second accepted attack from the SAME performer replaces its row
        # rather than growing the ledger.
        cadence = check_attack_cadence(
            cadence, PERFORMER, ATTACK_CADENCE_MS_PROVISIONAL).cadence
        self.assertEqual(len(cadence.identities()), 2)

    def test_this_lane_needs_no_flag_covers_cadence_names_too(self):
        # The existing test_this_lane_needs_no_flag already re-scans the
        # whole module text, so this only pins that the new names are
        # actually present for it to have scanned.
        self.assertIn("check_attack_cadence", dir(mob_combat))
        self.assertIn("ATTACK_CADENCE_MS_PROVISIONAL", dir(mob_combat))


class TheGateReadsAndComposesUnderOnePublicationTests(unittest.TestCase):
    """COO-DECISION 20260902_1946, conditions a and b.

    a. The count that arms the gate and the frame it arms must be taken
       under one publication, or the call site must SAY the window is open.
    b. A read that retires rows must say how many, because
       ``enter_scene``'s boundary report reads ZERO after somebody else's
       read swept the rows it was going to count.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [m for m in cls.roster
                   if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX][0]

    def setUp(self):
        # The once-per-process status line is driven by its OWN test; here
        # it is marked said, so a test that asserts an empty console does
        # not depend on which test ran first.
        said = list(mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID)
        mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.append(True)
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.clear(),
                mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.extend(
                    said)))
        # ...and the same for the line that reports a caller ARRIVING here.
        # SAVED AND EMPTIED, never pre-marked: pre-marking is how the guard
        # that the PLAIN path stays silent came out vacuously true
        # (pf-adversary, this round, D1 -- a mutant that reported an arrival
        # from the bar frame survived the whole file).
        arrivals = set(mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED)
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        # ONE SITE IS PRE-MARKED, NOT THE WHOLE FAMILY: the tests in this
        # class that assert an empty console drive the ChooseNPC site, so
        # that one arrival is declared already reported -- which is what a
        # process that has been up for an hour looks like.  Marking the
        # family as a whole is what made the plain-path guard vacuous
        # (pf-adversary, this round, D1): every OTHER site, the bar frame's
        # included, still reports here, so a report from the wrong path is
        # still caught.
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.add(
            mob_combat._reached_site_field(
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC))
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear(),
                mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.update(
                    arrivals)))
        moved = set(mob_combat._GROUND_ROWS_LEDGER_MOVED_REPORTED)
        mob_combat._GROUND_ROWS_LEDGER_MOVED_REPORTED.clear()
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_ROWS_LEDGER_MOVED_REPORTED.clear(),
                mob_combat._GROUND_ROWS_LEDGER_MOVED_REPORTED.update(moved)))
        before = set(mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED)
        mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.clear()
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.clear(),
                mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.update(before)))
        unknown = set(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED)
        mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear()
        self.addCleanup(
            lambda: (
                mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear(),
                mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.update(
                    unknown)))

    def _one_entry(self):
        body = field_mobs.hostile_npc_attr(
            self.legacy, self.mob, current_hp=self.mob.max_hp)
        return self.legacy.make_remote_actor_entry(
            mob_combat.NPC_STYLE_ACTOR_TYPE, self.mob.actor_identity,
            [(NPC_ATTR_ID, body)])

    def _capture_print(self):
        printed = []
        real_print = builtins.print
        builtins.print = lambda *a, **k: printed.append(
            " ".join(str(x) for x in a))
        self.addCleanup(lambda: setattr(builtins, "print", real_print))
        return printed

    def _a_roll_that_really_drops(self, mob):
        """A roll with a row in it, BUILT rather than rolled.

        ~~``roll_drops(mob, random.Random(3))``~~ IS STRUCK (pf-adversary,
        round t8z97r, D1+D2): that seed drops nothing, and neither does any
        of the 40 mobs x 80 seeds the adversary searched, so every test that
        needed a standing row skipped PERMANENTLY -- six undeclared skips,
        and the six were exactly the tests that prove conditions a and b on
        a floor with something on it.  A fixture that decides whether the
        round is tested by rolling dice is not a fixture.
        """
        # ``or 1``: the set id is PROVENANCE, and the control mob's own
        # normal set is 0, which the record refuses as a set id.  What the
        # fixture needs is a row on the floor, not a plausible loot table.
        item = mob_loot.DropItem(
            2400046, 1, "DROPS_NORMAL", mob.drops_normal or 1, 1)
        return mob_loot.DropRoll(
            mob.template_id, mob.actor_identity, (item,), (), 1, ())

    def _a_cell_with_a_row(self, clock=None):
        cell = mob_loot.DropLedgerCell(clock=clock)
        record = mob_death.DeathRecord(
            self.mob.actor_identity, 0x10010001, self.mob.max_hp)
        cell.loot_a_kill(
            self.mob, record, self._a_roll_that_really_drops(self.mob),
            kill_token=1)
        self.assertTrue(
            cell.ledger.drops, "the fixture must leave a row standing")
        return cell

    # -- condition a ------------------------------------------------------

    def test_the_kill_cannot_land_between_the_read_and_the_composition(self):
        """THE WINDOW ITSELF, driven with a real second thread.

        The composer runs while another thread is trying to loot a kill into
        the same cell.  If the read and the composition were two acquisitions
        that kill would land in between; under one publication it cannot,
        and this test proves the ordering rather than asserting it.
        """
        cell = mob_loot.DropLedgerCell()
        entered = threading.Event()
        may_finish = threading.Event()
        landed = threading.Event()
        second = self.roster[1]
        record = mob_death.DeathRecord(
            second.actor_identity, 0x10010001, second.max_hp)

        def a_kill():
            entered.wait(5)
            cell.loot_a_kill(
                second, record, self._a_roll_that_really_drops(second),
                kill_token=2)
            landed.set()

        seen = []

        def compose(rows_left):
            seen.append(rows_left)
            entered.set()
            # Long enough for the other thread to reach the cell and block.
            may_finish.wait(0.5)
            self.assertFalse(
                landed.is_set(),
                "a kill landed between the read and the composition")
            return b"pc", b"frame"

        worker = threading.Thread(target=a_kill)
        worker.start()
        try:
            answer, rows, swept, moved = cell.compose_under_publication(
                compose)
        finally:
            may_finish.set()
            worker.join(5)
        self.assertEqual(answer, (b"pc", b"frame"))
        # A cell nobody has entered a scene into answers NO_SCENE, which is
        # the fail-closed sentinel and not a count -- the point of this test
        # is WHEN the answer was taken, not what it said.
        self.assertEqual(seen, [mob_loot.GROUND_LIVENESS_NO_SCENE])
        self.assertEqual(rows, mob_loot.GROUND_LIVENESS_NO_SCENE)
        self.assertEqual(swept, 0)
        self.assertFalse(moved, "the composer did not touch the ledger")
        self.assertTrue(landed.is_set(), "the other thread never ran")

    def test_the_closed_path_says_nothing_and_gates_on_the_live_count(self):
        cell = self._a_cell_with_a_row()
        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=cell)
        self.assertEqual(
            answer,
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, entries),
            "a row is standing and the ground was not preserved")
        self.assertEqual(printed, [], printed)

    def test_no_cell_composes_todays_bytes_and_says_the_window_is_open(self):
        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=None)
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        race = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")]
        self.assertEqual(len(race), 1, printed)
        self.assertIn(mob_combat.GROUND_ROWS_RACE_REASON_NO_CELL, race[0])

    def test_a_cell_that_cannot_host_the_composition_is_named_not_silent(self):
        class OldCell:
            def publication(self):
                return None, None, 0

        entries = [self._one_entry()]
        printed = self._capture_print()
        for _click in range(4):
            answer = (
                mob_combat
                .remote_actors_preserving_the_ground_under_publication(
                    self.legacy, entries,
                    mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                    cell=OldCell()))
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        race = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")]
        self.assertEqual(len(race), 1, "the line is once per site and cause")
        self.assertIn(
            mob_combat.GROUND_ROWS_RACE_REASON_CANNOT_HOST, race[0])

    def test_a_host_that_refuses_still_composes_and_is_named(self):
        class RefusingCell:
            def compose_under_publication(self, compose, scene=None):
                raise RuntimeError("the cell is gone")

        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            cell=RefusingCell())
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        race = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")]
        self.assertEqual(len(race), 1, printed)
        self.assertIn(
            mob_combat.GROUND_ROWS_RACE_REASON_CELL_REFUSED, race[0])

    def test_a_handle_whose_attribute_access_raises_still_gets_a_frame(self):
        """The listener thread has no ``except``; finding out that a handle
        is hostile may not cost the frame."""
        class Hostile:
            def __getattr__(self, name):
                raise KeyError(name)

        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=Hostile())
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        self.assertTrue(any(line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")
            for line in printed), printed)

    def test_a_lost_frame_is_raised_and_never_reported_as_a_race(self):
        """The composer's own exception means the LEGACY composer failed
        too, and that is a lost frame, not a ground-list condition."""
        class Broken:
            def __getattr__(self, name):
                raise ValueError("v141 is not here")

        cell = self._a_cell_with_a_row()
        printed = self._capture_print()
        with self.assertRaises(ValueError):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                Broken(), [], mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                cell=cell)
        self.assertEqual(
            [line for line in printed if line.startswith(
                mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN)], [])

    def test_another_scenes_cell_never_arms_this_frame(self):
        cell = self._a_cell_with_a_row()
        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            cell=cell, scene="Bg0014")
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries),
            "another scene's floor armed this frame")
        self.assertTrue(any(line.startswith(
            mob_combat.GROUND_ACTORS_LIVENESS_UNKNOWN_TOKEN + " ")
            for line in printed), printed)

    def test_the_call_site_status_is_re_derived_from_src_on_every_run(
            self):
        """pf-adversary D3: silence is not evidence that the window is shut.

        Zero ``GROUND_ROWS_RACE_WINDOW_OPEN`` lines is what a closed window
        and an UNWIRED closure both look like on a console.  This constant is
        the difference, and it is re-derived from ``src/``'s own AST here so
        it cannot drift in either direction -- as red for a status left too
        high after a call site is reverted as for one left too low after it
        lands.  A CALL or a NAME LOOKUP, never a substring: a comment naming
        the function satisfies a substring and sends nothing.
        """
        # EVERY PRODUCTION FILE, not runtime.py alone (pf-adversary, second
        # pass, R1): the site this closure is FOR is a ChooseNPC responder,
        # and those live in ``lane_hooks/``.  A guard that watched one file
        # stayed green with the closure wired in another -- measured, by
        # wiring it into lane_a_choose_npc_scene14.py.
        self.assertEqual(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS,
            call_site_status_of_tree(
                (ROOT / "src/pirateforce_foundation").rglob("*.py")),
            "src/ and GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS disagree "
            "about how a production call site reaches the closed path.  "
            "Either wiring landed and the constant was not moved, or the "
            "constant claims a closure nothing uses.")

    # -- condition b ------------------------------------------------------

    def test_a_read_that_retires_rows_says_how_many(self):
        ticks = [0.0, 0.0, 0.0, 0.0]

        def clock():
            return ticks[-1] if len(ticks) == 1 else ticks.pop(0)

        cell = self._a_cell_with_a_row(clock=clock)
        standing = len(cell.ledger.drops)
        self.assertTrue(standing)
        ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]
        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=cell)
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries),
            "every row expired, so there was nothing left to preserve")
        swept = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_SWEPT_BY_READ_TOKEN + " ")]
        self.assertEqual(len(swept), 1, printed)
        self.assertIn(" %d " % standing, swept[0])
        self.assertIn(
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, swept[0])

    def test_a_read_that_retires_nothing_says_nothing(self):
        cell = self._a_cell_with_a_row()
        printed = self._capture_print()
        mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, [self._one_entry()],
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=cell)
        self.assertEqual(printed, [], "an ordinary read is not a console event")

    def test_the_sweep_line_refuses_a_count_that_is_not_a_count(self):
        printed = self._capture_print()
        for value in (0, -1, None, True, "3", 2.0):
            self.assertFalse(
                mob_combat.report_rows_swept_by_read(value, "site"), value)
        self.assertEqual(printed, [])
        self.assertTrue(mob_combat.report_rows_swept_by_read(2, "site"))
        self.assertEqual(len(printed), 1)

    def test_a_read_that_dies_after_sweeping_still_reports_what_it_swept(
            self):
        """pf-adversary D5: the old shape hard-coded zero on this path -- the
        exact defect condition b exists to close, inside the method that
        closes it."""
        ticks = [0.0]

        def clock():
            return ticks[-1]

        cell = self._a_cell_with_a_row(clock=clock)
        standing = len(cell.ledger.drops)
        ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]
        real = mob_loot.ground_liveness_from_publication

        def boom(*_args, **_kwargs):
            raise RuntimeError("the read died after the sweep")

        mob_loot.ground_liveness_from_publication = boom
        self.addCleanup(
            setattr, mob_loot, "ground_liveness_from_publication", real)
        answer, rows, swept, moved = cell.compose_under_publication(
            lambda rows_left: ("composed", rows_left))
        self.assertEqual(answer, ("composed", mob_loot.GROUND_LIVENESS_CELL_REFUSED))
        self.assertEqual(rows, mob_loot.GROUND_LIVENESS_CELL_REFUSED)
        self.assertEqual(
            swept, standing,
            "the rows this read retired vanished with the exception")
        self.assertFalse(moved)

    def test_an_unfoldable_scene_never_touches_the_cell(self):
        """pf-adversary D6: the sibling documents this invariant; the new
        method used to fold the scene AFTER sweeping."""
        ticks = [0.0]
        cell = self._a_cell_with_a_row(clock=lambda: ticks[-1])
        standing = len(cell.ledger.drops)
        ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]
        answer, rows, swept, moved = cell.compose_under_publication(
            lambda rows_left: rows_left, scene=["unfoldable"])
        self.assertEqual(rows, mob_loot.GROUND_LIVENESS_BAD_SCENE)
        self.assertEqual(answer, mob_loot.GROUND_LIVENESS_BAD_SCENE)
        self.assertEqual((swept, moved), (0, False))
        # The cell's own sweep counter, because reading ``.ledger`` here
        # would sweep and hide exactly what this test is about.
        self.assertEqual(
            cell._swept_total, 0,
            "a call that refused the caller's scene retired the ground")
        self.assertEqual(standing, 1)

    def test_a_composer_that_moves_the_ledger_is_counted_and_named(self):
        """pf-adversary D7: the RLock lets a re-entrant composer proceed, so
        the frame can be armed by a count the composer itself made false.
        The sweep it causes is counted and the site is named."""
        ticks = [0.0]
        cell = self._a_cell_with_a_row(clock=lambda: ticks[-1])
        standing = len(cell.ledger.drops)

        def composer(rows_left):
            # The composer expires the floor it was just told about.
            ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]
            cell.publication_and_sweep()
            return ("composed", rows_left)

        answer, rows, swept, moved = cell.compose_under_publication(composer)
        self.assertEqual(answer[1], rows)
        self.assertEqual(rows, standing, "the count handed over was the truth")
        self.assertEqual(
            swept, standing, "the composer's own sweep went unreported")
        self.assertTrue(moved, "the ledger moved and nobody said so")

        printed = self._capture_print()
        entries = [self._one_entry()]

        class MovesTheLedger:
            def compose_under_publication(self, compose, scene=None):
                answer = compose(2)
                return answer, 2, 0, True

        mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            cell=MovesTheLedger())
        self.assertTrue(any(line.startswith(
            mob_combat.GROUND_ROWS_LEDGER_MOVED_TOKEN + " ")
            for line in printed), printed)

    def test_a_host_that_composed_then_failed_does_not_compose_twice(self):
        """Composing twice doubles every console line the composer writes."""
        calls = []

        class ComposesThenFails:
            def compose_under_publication(self, compose, scene=None):
                calls.append(compose(3))
                raise RuntimeError("the cell fell over after composing")

        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            cell=ComposesThenFails())
        self.assertEqual(len(calls), 1, "the composer ran twice")
        self.assertEqual(answer, calls[0])
        self.assertTrue(any(line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")
            for line in printed), printed)

    def test_a_host_that_wraps_the_composers_exception_is_not_the_culprit(
            self):
        """pf-adversary, second pass, R9: a wrapping host used to get the
        composer run TWICE, the composer's exception discarded, and a pure
        composition failure printed under the cell's name.  A lost frame is
        not a ground-list condition."""
        class WrapsTheException:
            def compose_under_publication(self, compose, scene=None):
                try:
                    return compose(1)
                except Exception as exc:
                    raise KeyError("wrapped") from exc

        attempts = []
        real = mob_combat.remote_actors_preserving_the_ground

        def counted(*args, **kwargs):
            attempts.append(1)
            return real(*args, **kwargs)

        mob_combat.remote_actors_preserving_the_ground = counted
        self.addCleanup(
            setattr, mob_combat, "remote_actors_preserving_the_ground", real)

        class Broken:
            def __getattr__(self, name):
                raise ValueError("v141 is not here")

        printed = self._capture_print()
        with self.assertRaises(ValueError):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                Broken(), [],
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                cell=WrapsTheException())
        self.assertEqual(
            len(attempts), 1, "the composer was run a second time")
        self.assertEqual(
            [line for line in printed if line.startswith(
                mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN)], [],
            "a composition failure was reported as a cell failure")

    def test_the_race_family_says_its_own_suppression_word(self):
        """pf-adversary D11: it used to borrow the liveness family's token,
        so a capped race family accused a family that never spoke."""
        printed = self._capture_print()
        for index in range(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_SITE_CAP
                           + 3):
            mob_combat._report_race_window_open_once(
                "site_%d" % index, mob_combat.GROUND_ROWS_RACE_REASON_NO_CELL)
        suppressed = [line for line in printed
                      if "SUPPRESSED" in line]
        self.assertEqual(len(suppressed), 1, printed)
        self.assertTrue(suppressed[0].startswith(
            mob_combat.GROUND_ROWS_RACE_SUPPRESSED_TOKEN + " "), suppressed)
        self.assertEqual(
            len(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED), 0,
            "the liveness family was charged for the race family's lines")

    def test_publication_still_answers_in_three_and_agrees_with_the_fourth(
            self):
        cell = self._a_cell_with_a_row()
        scene, view, elsewhere = cell.publication()
        scene2, view2, elsewhere2, swept = cell.publication_and_sweep()
        self.assertEqual((scene, elsewhere), (scene2, elsewhere2))
        self.assertEqual(view.drops, view2.drops)
        self.assertEqual(swept, 0)

    def test_a_host_that_answers_in_a_shape_this_lane_cannot_read(self):
        """pf-adversary, second pass, R2: the unpack ran unguarded on the
        listener thread, so a two-element or None answer cost the frame --
        with a composed frame sitting in hand."""
        class Answers:
            def __init__(self, shape):
                self._shape = shape

            def compose_under_publication(self, compose, scene=None):
                composed = compose(2)
                if self._shape == "two":
                    return composed, 0
                if self._shape == "none":
                    return None
                if self._shape == "generator":
                    return (x for x in (composed, 0, 0))
                return composed, 0, 0, False

        entries = [self._one_entry()]
        expected = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, entries)
        for shape in ("two", "none", "generator", "four"):
            with self.subTest(shape=shape):
                printed = self._capture_print()
                answer = (
                    mob_combat
                    .remote_actors_preserving_the_ground_under_publication(
                        self.legacy, entries,
                        mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
                        cell=Answers(shape)))
                self.assertEqual(answer, expected, "the frame was lost")
                del printed

    def test_the_moved_family_has_its_own_budget_and_its_own_word(self):
        """pf-adversary, second pass, R3: it borrowed the race family's, so
        a run of moved sites both mis-named the suppression and could
        silence a genuine open window."""
        printed = self._capture_print()
        for index in range(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_SITE_CAP
                           + 3):
            mob_combat._report_ledger_moved_once("moved_site_%d" % index)
        mob_combat._report_race_window_open_once(
            "a_real_open_window", mob_combat.GROUND_ROWS_RACE_REASON_NO_CELL)
        self.assertTrue(any(line.startswith(
            mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN + " ")
            for line in printed),
            "a run of moved sites silenced a genuine open window")
        suppressed = [line for line in printed if "SUPPRESSED" in line]
        self.assertEqual(len(suppressed), 1, suppressed)
        self.assertTrue(suppressed[0].startswith(
            mob_combat.GROUND_ROWS_LEDGER_MOVED_SUPPRESSED_TOKEN + " "),
            suppressed)

    def test_every_way_a_composer_can_sweep_is_counted(self):
        """pf-adversary, second pass, R4: the counter lived in the
        publication read, so 3 of the 5 nested sweep paths reported ZERO --
        a MOVED line with no number, and a boundary that then says 0."""
        for nested in ("publication_and_sweep", "publication",
                       "sweep_expired", "ledger", "enter_scene"):
            with self.subTest(nested=nested):
                ticks = [0.0]
                cell = self._a_cell_with_a_row(clock=lambda: ticks[-1])
                standing = len(cell.ledger.drops)

                def composer(rows_left, cell=cell, ticks=ticks,
                             nested=nested):
                    ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]
                    if nested == "enter_scene":
                        cell.enter_scene("Bg0014")
                    elif nested == "ledger":
                        cell.ledger
                    else:
                        getattr(cell, nested)()
                    return rows_left

                _answer, _rows, swept, moved = cell.compose_under_publication(
                    composer)
                self.assertEqual(
                    swept, standing,
                    "a nested %s swept in silence" % (nested,))
                self.assertTrue(moved, "the ledger moved and nobody said so")

    def test_a_composer_that_changes_the_scene_has_moved_the_ledger(self):
        """pf-adversary, second pass, R8: identity of ``_ledger`` alone
        cannot see a count that now describes another scene's floor."""
        cell = self._a_cell_with_a_row()
        def composer(rows_left):
            cell.enter_scene("Bg0014")
            return rows_left

        answer, rows, swept, moved = cell.compose_under_publication(composer)
        self.assertEqual(answer, rows)
        self.assertEqual(swept, 0, "nothing expired in this test")
        self.assertTrue(
            moved, "the count now describes a scene the frame is not for")

    def test_a_composer_that_raises_still_reports_what_the_read_swept(self):
        """pf-adversary, second pass, R6."""
        ticks = [0.0]
        cell = self._a_cell_with_a_row(clock=lambda: ticks[-1])
        standing = len(cell.ledger.drops)
        ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]

        class Broken:
            def __getattr__(self, name):
                raise ValueError("v141 is not here")

        printed = self._capture_print()
        with self.assertRaises(ValueError):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                Broken(), [],
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=cell)
        swept = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_SWEPT_BY_READ_TOKEN + " ")]
        self.assertEqual(len(swept), 1, printed)
        self.assertIn(" %d " % standing, swept[0])

    def test_the_fallback_read_reports_its_own_sweep(self):
        """pf-adversary, second pass, R7: the cell_refused fallback swept in
        silence, and the comment that excused it was false for that branch."""
        ticks = [0.0]
        real = self._a_cell_with_a_row(clock=lambda: ticks[-1])
        standing = len(real.ledger.drops)
        ticks[:] = [mob_loot.DROP_LIFETIME_SECONDS + 1.0]

        class Refuses:
            def __init__(self, inner):
                self._inner = inner

            def compose_under_publication(self, compose, scene=None):
                raise RuntimeError("not today")

            def publication(self):
                return self._inner.publication()

            @property
            def swept_total(self):
                return self._inner.swept_total

        entries = [self._one_entry()]
        printed = self._capture_print()
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
            cell=Refuses(real))
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))
        swept = [line for line in printed if line.startswith(
            mob_combat.GROUND_ROWS_SWEPT_BY_READ_TOKEN + " ")]
        self.assertEqual(len(swept), 1, printed)
        self.assertIn(" %d " % standing, swept[0])

    def test_the_call_site_status_reaches_the_console_once(self):
        """pf-adversary, second pass, R10: a source-only constant cannot
        tell an operator watching the console whether the silence means a
        shut window or an unwired closure."""
        mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.clear()
        printed = self._capture_print()
        entries = [self._one_entry()]
        for _frame in range(3):
            mob_combat.remote_actors_preserving_the_ground(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_BAR)
        status = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_TOKEN + " ")]
        self.assertEqual(len(status), 1, printed)
        self.assertIn(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS, status[0])
        # ...and the plain path never claims a caller ARRIVED at the closed
        # one.  This is the half that must stay silent on a build where
        # nothing is wired, or the runtime line is worth nothing.
        self.assertEqual(
            [line for line in printed if line.startswith(
                mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN)],
            [], printed)

    def test_a_caller_that_reaches_the_closed_path_is_said_once_with_its_site(
            self):
        """LANE-A ``20260903_0320``: the source scan cannot see a call made
        through a name lookup and a local variable, so the console says the
        arrival itself -- once, with the site, and after the status line so
        an operator reads what the tree allows above what the process did."""
        mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.clear()
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        printed = self._capture_print()
        entries = [self._one_entry()]
        for _call in range(3):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=None)
        reached = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]
        self.assertEqual(len(reached), 1, printed)
        # ...and a SECOND site is not silenced by the first (pf-adversary,
        # this round, D12): the site names are per scene, and the one an
        # operator most wants to see arrive is whichever landed last.
        mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries, "another_site", cell=None)
        self.assertEqual(
            [line.split()[1] for line in printed if line.startswith(
                mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")],
            [mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC,
             "another_site"], printed)
        self.assertEqual(
            reached[0].split(),
            [mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN,
             mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC],
            "the reached line is read as exactly two fields")
        status = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_TOKEN + " ")]
        self.assertEqual(len(status), 1, printed)
        self.assertLess(
            printed.index(status[0]), printed.index(reached[0]),
            "the status line is forced out before the arrival it explains")

    def test_a_site_carrying_a_space_still_leaves_two_fields(self):
        """``site`` is caller data.  A third field on this line would make
        the token's own grep -- the site is the second field -- wrong."""
        printed = self._capture_print()
        entries = [self._one_entry()]
        mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries, "a site with spaces", cell=None)
        reached = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]
        self.assertEqual(len(reached), 1, printed)
        self.assertEqual(len(reached[0].split()), 2, reached)

    def test_the_arrival_is_said_even_when_the_composition_then_fails(self):
        """It reports the CALL, not the frame: a call site that fired and
        then lost its frame is still a call site an operator must know
        about, and the loss has console lines of its own."""
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        printed = self._capture_print()

        class Exploding:
            def make_runtime_remote_actors(self, *_a, **_k):
                raise ValueError("v141 is gone")

        with self.assertRaises(Exception):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                Exploding(), [self._one_entry()],
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=None)
        self.assertEqual(
            len([line for line in printed if line.startswith(
                mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]),
            1, printed)

    def test_a_site_carrying_any_whitespace_still_leaves_two_fields(self):
        """Not just the space (pf-adversary, this round, D8): a tab, a
        vertical tab, a form feed and the ASCII separators are all ASCII, so
        they survive the console fold, and all of them split."""
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        entries = [self._one_entry()]
        for i, gap in enumerate([" ", "\t", "\x0b", "\x0c", "\x1c",
                                 "\x1d", "\x1e", "\x1f"]):
            with self.subTest(gap=repr(gap)):
                printed = self._capture_print()
                mob_combat.remote_actors_preserving_the_ground_under_publication(
                    self.legacy, entries, "site%s%d" % (gap, i), cell=None)
                reached = [line for line in printed if line.startswith(
                    mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]
                self.assertEqual(len(reached), 1, printed)
                self.assertEqual(len(reached[0].split()), 2, reached)

    def test_a_site_whose_str_raises_is_named_by_its_type_not_dropped(self):
        """pf-adversary, this round, D7, and this file's own prior finding
        sixty lines up: reporting NOTHING for it is how a hole stays
        invisible for a session."""
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        class Nasty:
            def __str__(self):
                raise RuntimeError("boom")

        printed = self._capture_print()
        entries = [self._one_entry()]
        answer = (
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                self.legacy, entries, Nasty(), cell=None))
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries),
            "a site that cannot be printed cost the frame")
        reached = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]
        self.assertEqual(len(reached), 1, printed)
        self.assertEqual(reached[0].split()[1], "site_unprintable_Nasty")

    def test_one_refused_write_does_not_delete_the_evidence_forever(self):
        """pf-adversary, this round, D6.  A bridge console detached at boot
        is one failed write; recording the site before the print spent the
        only runtime evidence of a wired call site on it, for the life of
        the process."""
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        printed = self._capture_print()
        # WRAPPED AROUND THE CAPTURE, not installed before it: the capture
        # replaces ``print`` itself, so a refusing print installed first is
        # never called and this test would prove nothing (it did, for one
        # commit -- the lossy mutant survived it).
        recorder = builtins.print
        self.addCleanup(lambda: setattr(builtins, "print", recorder))
        failures = [True, True]

        def flaky(*args, **kwargs):
            if failures:
                failures.pop()
                raise OSError("console detached")
            return recorder(*args, **kwargs)

        builtins.print = flaky
        entries = [self._one_entry()]
        for _call in range(4):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                self.legacy, entries,
                mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=None)
        self.assertEqual(
            len([line for line in printed if line.startswith(
                mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]),
            1, printed)

    def test_the_arrival_family_is_capped_and_says_so_in_its_own_name(self):
        """``site`` is caller data, so the set is bounded -- and the line
        that announces the bound is this family's own, never the liveness
        family's (pf-adversary, round t8z97r, D11)."""
        mob_combat._GROUND_UNDER_PUBLICATION_REACHED_REPORTED.clear()
        printed = self._capture_print()
        entries = [self._one_entry()]
        for i in range(mob_combat.GROUND_UNDER_PUBLICATION_REACHED_SITE_CAP
                       + 5):
            mob_combat.remote_actors_preserving_the_ground_under_publication(
                self.legacy, entries, "site_%d" % i, cell=None)
        reached = [line for line in printed if line.startswith(
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN + " ")]
        self.assertEqual(
            len(reached),
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_SITE_CAP, printed)
        self.assertEqual(
            len([line for line in printed if line.startswith(
                mob_combat.GROUND_UNDER_PUBLICATION_ARRIVALS_SUPPRESSED_TOKEN
                + " ")]),
            1, printed)

    def test_the_two_tokens_are_the_words_an_operator_greps_for(self):
        """pf-adversary, this round, D2 and D3.  Every other assertion in
        this file compares the token with itself, so a rename to garbage
        stayed green -- and the first spelling of the arrival token was the
        status token plus a suffix, so one line greppedas two."""
        self.assertEqual(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_TOKEN,
            "GROUND_UNDER_PUBLICATION_CALL_SITE")
        self.assertEqual(
            mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN,
            "GROUND_UNDER_PUBLICATION_REACHED")
        self.assertEqual(
            mob_combat.GROUND_UNDER_PUBLICATION_ARRIVALS_SUPPRESSED_TOKEN,
            "GROUND_UNDER_PUBLICATION_ARRIVALS_SUPPRESSED")
        family = [mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_TOKEN,
                  mob_combat.GROUND_UNDER_PUBLICATION_REACHED_TOKEN,
                  mob_combat.GROUND_UNDER_PUBLICATION_ARRIVALS_SUPPRESSED_TOKEN]
        for one in family:
            for other in family:
                if one is other:
                    continue
                self.assertFalse(
                    other.startswith(one),
                    "%s greps as %s" % (other, one))
            self.assertTrue(one.startswith("GROUND_UNDER_PUBLICATION"))

    def test_a_console_that_refuses_the_lines_loses_them_not_the_frame(self):
        real_print = builtins.print

        def refuse(*_args, **_kwargs):
            raise ValueError("I/O operation on closed file")

        builtins.print = refuse
        self.addCleanup(lambda: setattr(builtins, "print", real_print))
        # BOTH ONCE-PER-PROCESS LINES ARE ARMED HERE, not left marked said by
        # setUp: a refusing console must be driven through every line this
        # path can write, and the arrival line is one of them.
        mob_combat._GROUND_UNDER_PUBLICATION_STATUS_SAID.clear()
        entries = [self._one_entry()]
        answer = mob_combat.remote_actors_preserving_the_ground_under_publication(
            self.legacy, entries,
            mob_combat.GROUND_ACTORS_PRESERVE_SITE_CHOOSE_NPC, cell=None)
        self.assertEqual(
            answer, self.legacy.make_runtime_remote_actors(entries))


class TheCallSiteScanKnowsTheShapesItClaimsToKnowTests(unittest.TestCase):
    """The scan behind ``GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS``, driven
    on SOURCE THIS TEST WRITES.

    ON PURPOSE, and it is the rule the COO approved on 2026-09-03T00:55 as
    house rule b: a test that pins another lane's file as its baseline dies
    when that lane moves a line it is entitled to move.  ``lane_hooks/
    lane_a_ground_preserve.py`` is where the name-lookup shape lives today,
    and it is LANE-A's to rewrite; what this lane owes is a scan that reads
    the SHAPE, and a shape can be written down here.  The one test that does
    read the real tree is the guard above, whose whole job is to be red when
    ``src/`` and the constant disagree.
    """

    WANTED = UNDER_PUBLICATION_COMPOSER

    def test_a_direct_call_is_called(self):
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "def answer(a, b):\n"
                "    return mob_combat.%s(a, b, 's', cell=None)\n"
                % self.WANTED),
            "called")

    def test_an_aliased_import_is_called(self):
        self.assertEqual(
            call_site_status_of_source(
                "from ..mob_combat import %s as compose\n"
                "def answer(a, b):\n"
                "    return compose(a, b, 's', cell=None)\n" % self.WANTED),
            "called")

    def test_a_name_lookup_through_a_module_constant_is_seen(self):
        """LANE-A's shape, and the whole reason for the middle word: their
        module must import on a tree where the composer does not exist."""
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "COMPOSER = (\n    \"%s\")\n"
                "def composer():\n"
                "    return getattr(mob_combat, COMPOSER, None)\n"
                % self.WANTED),
            "wired_by_name_lookup")

    def test_a_name_lookup_through_a_literal_is_seen(self):
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "def composer():\n"
                "    return getattr(mob_combat, \"%s\", None)\n"
                % self.WANTED),
            "wired_by_name_lookup")

    def test_a_tuple_assignment_binds_the_name_too(self):
        """pf-adversary, this round, D4, and it is the one that would have
        turned ``main`` red from ANOTHER lane's entitled edit: pairing the
        constant with a second one is a spelling change with identical
        behaviour, and the scan used to see nothing in it."""
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "COMPOSER, OTHER = (\n"
                "    \"%s\",\n"
                "    \"remote_actors_preserving_the_ground\")\n"
                "def composer():\n"
                "    return getattr(mob_combat, COMPOSER, None)\n"
                % self.WANTED),
            "wired_by_name_lookup")

    def test_fetching_the_attribute_without_calling_it_is_seen(self):
        """The nearest refactor of the hook that owns this shape today:
        ``if hasattr(...): return mob_combat.<name>``.  It reproduces the
        letter's own complaint in a new spelling, so it is the WEAK word --
        a name that is fetched is not a frame that goes through."""
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "def composer():\n"
                "    if hasattr(mob_combat, \"%s\"):\n"
                "        return mob_combat.%s\n"
                "    return None\n" % (self.WANTED, self.WANTED)),
            "wired_by_name_lookup")

    def test_a_module_that_declares_itself_out_of_production_is_skipped(self):
        """A fixture is not a production call site.  Both markers, because
        both are this project's convention and either one is an opt-out."""
        body = ("from .. import mob_combat\n"
                "%s\n"
                "def answer(a, b):\n"
                "    return mob_combat.%s(a, b, 's', cell=None)\n")
        for marker in ("production_allowed = False", "test_only = True"):
            with self.subTest(marker=marker):
                self.assertEqual(
                    call_site_status_of_source(
                        body % (marker, self.WANTED)),
                    "composed_not_called")
        # ...and a module with no marker at all counts as production: the
        # marker is what an author writes to opt OUT.
        self.assertEqual(
            call_site_status_of_source(body % ("X = 1", self.WANTED)),
            "called")

    def test_a_name_lookup_for_some_other_attribute_is_nothing(self):
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "OTHER = \"remote_actors_preserving_the_ground\"\n"
                "def composer():\n"
                "    return getattr(mob_combat, OTHER, None)\n"),
            "composed_not_called")

    def test_naming_it_in_a_comment_or_a_docstring_is_nothing(self):
        """A substring sends no bytes.  This is the defect the first version
        of the guard was written against and it must stay closed."""
        self.assertEqual(
            call_site_status_of_source(
                "\"\"\"One day this module will call %s.\"\"\"\n"
                "# %s is not called here\n"
                "X = 1\n" % (self.WANTED, self.WANTED)),
            "composed_not_called")

    def test_a_direct_call_wins_over_a_lookup_in_the_same_file(self):
        self.assertEqual(
            call_site_status_of_source(
                "from .. import mob_combat\n"
                "COMPOSER = \"%s\"\n"
                "def fetched():\n"
                "    return getattr(mob_combat, COMPOSER, None)\n"
                "def answer(a, b):\n"
                "    return mob_combat.%s(a, b, 's', cell=None)\n"
                % (self.WANTED, self.WANTED)),
            "called")

    def test_the_three_words_are_the_registered_ones_weakest_first(self):
        """The scan's vocabulary is the module's, not a second copy: a word
        this file invented would be a word no console ever prints."""
        self.assertEqual(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUSES,
            ("composed_not_called", "wired_by_name_lookup", "called"))
        self.assertIn(
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUS,
            mob_combat.GROUND_UNDER_PUBLICATION_CALL_SITE_STATUSES)

    def test_the_strongest_word_of_a_tree_is_the_answer(self):
        """Across FILES, not just inside one: a lookup in one file and a
        direct call in another is a tree with a direct call in it."""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "lookup.py").write_text(
            "from .. import mob_combat\n"
            "COMPOSER = \"%s\"\n"
            "def fetched():\n"
            "    return getattr(mob_combat, COMPOSER, None)\n"
            % self.WANTED, encoding="utf-8")
        (root / "quiet.py").write_text("X = 1\n", encoding="utf-8")
        self.assertEqual(
            call_site_status_of_tree(root.rglob("*.py")),
            "wired_by_name_lookup")
        (root / "direct.py").write_text(
            "from .. import mob_combat\n"
            "def answer(a, b):\n"
            "    return mob_combat.%s(a, b, 's', cell=None)\n"
            % self.WANTED, encoding="utf-8")
        self.assertEqual(
            call_site_status_of_tree(root.rglob("*.py")), "called")

    def test_the_file_that_defines_it_is_not_its_own_call_site(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "mob_combat.py").write_text(
            "def %s(a, b, site, cell=None):\n"
            "    return %s(a, b, site, cell=cell)\n"
            % (self.WANTED, self.WANTED), encoding="utf-8")
        self.assertEqual(
            call_site_status_of_tree(root.rglob("*.py")),
            "composed_not_called")


if __name__ == "__main__":
    unittest.main()
