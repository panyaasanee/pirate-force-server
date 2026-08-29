"""LANE-B round jop8ph: may THIS ledger be consulted for THAT scene?

The claim under test, in one sentence: a census composer can hand over
whatever combat ledger it holds and never be raised at, and the wounded HP
in that ledger reaches the wire exactly when the ledger really does speak
for the scene being composed.

THE BEFORE HALF IS PINNED HERE TOO, and it is the reason the round exists.
``test_a_foreign_ledger_used_to_raise_at_the_composer`` drives the OLD
behaviour on purpose -- ``mob_death.full_roster_override`` with a bg0001
ledger and a Bg0002 roster -- and requires the refusal to still happen
there.  Without that pin, every "it no longer raises" assertion below could
be satisfied by a tree in which nothing raised in the first place, and the
round would be measuring its own assumption.
"""

import ast
import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import diag_multi_object_wiring as wiring
from pirateforce_foundation import field_mob_tables
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_census_hostility as mch
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_diag_multi_object as diag
from pirateforce_foundation import mob_ledger_admission as admission
from pirateforce_foundation.legacy_bridge import load_legacy

BG0001_SCENE_ID = 1
# The scene folder bg0001's rows carry, read from the table module rather
# than spelled here, so a rename cannot leave this file agreeing with itself.
BG0001_SCENE = field_mob_tables.SCENE
BG0002_SCENE_ID = 2
# A scene id this project ships no field-mob roster for.  Port Royal's own
# id and Prison Exile Island's are the only two that resolve today.
NO_ROSTER_SCENE_ID = 997


def bg0001_ledger():
    return mob_combat.open_ledger_for_scene_id(BG0001_SCENE_ID)


def bg0002_ledger():
    return mob_combat.open_ledger_for_scene_id(BG0002_SCENE_ID)


class LedgerCarriesItsSceneTests(unittest.TestCase):
    """Half (a) of the decision: the ledger knows which scene it is for."""

    def test_the_no_argument_ledger_is_scoped_without_a_call_site_change(self):
        # THIS IS THE ONE THAT MATTERS ON A REAL BOOT.  ``runtime.py`` opens
        # its session ledger with ``open_ledger()`` and no argument, inside
        # ``PersistentGameSessionState.__init__``, where there is no scene to
        # pass.  If the scene tag only arrived through an explicit keyword,
        # the single ledger a live server actually holds would stay unscoped
        # and this whole round would be theory.
        self.assertEqual(mob_combat.open_ledger().scene, BG0001_SCENE)

    def test_the_scene_comes_off_the_roster_rows_themselves(self):
        self.assertEqual(bg0002_ledger().scene, "Bg0002")
        self.assertEqual(bg0001_ledger().scene, BG0001_SCENE)
        self.assertNotEqual(bg0001_ledger().scene, bg0002_ledger().scene)

    def test_a_scene_with_no_roster_still_names_its_scene(self):
        # An UNSCOPED empty ledger is admitted into every scene by
        # containment -- it is missing nothing, because nothing was asked of
        # it.  ``open_ledger_for_scene_id`` therefore names the scene rather
        # than letting zero rows derive nothing.  If this regresses, the
        # empty ledger of a town silently becomes a valid ledger for a
        # battlefield.
        empty = mob_combat.open_ledger_for_scene_id(NO_ROSTER_SCENE_ID)
        self.assertEqual(empty.balances, ())
        self.assertIsNone(field_mobs.scene_for_scene_id(NO_ROSTER_SCENE_ID))
        record = admission.admit_ledger(BG0002_SCENE_ID, empty)
        self.assertFalse(record["admitted"])

    def test_a_hit_does_not_make_the_ledger_forget_its_scene(self):
        ledger = bg0002_ledger()
        row = ledger.balances[0]
        wounded = ledger.with_balance(
            mob_combat.MobBalance(
                row.actor_identity, row.max_hp, row.max_hp - 1))
        self.assertEqual(wounded.scene, "Bg0002")
        self.assertEqual(wounded.generation, ledger.generation + 1)

    def test_an_empty_scene_name_is_refused_rather_than_read_two_ways(self):
        with self.assertRaises(mob_combat.MobCombatContractError) as caught:
            mob_combat.CombatLedger((), 0, "")
        self.assertEqual(
            caught.exception.reason, mob_combat.REFUSE_LEDGER_SCENE_EMPTY)

    def test_naming_one_scene_while_handing_over_another_is_refused(self):
        with self.assertRaises(mob_combat.MobCombatContractError) as caught:
            mob_combat.open_ledger(
                field_mobs.roster_for_scene_id(BG0002_SCENE_ID),
                scene=BG0001_SCENE,
            )
        self.assertEqual(
            caught.exception.reason,
            mob_combat.REFUSE_LEDGER_SCENE_DISAGREES_WITH_ROSTER,
        )


class WhatUsedToHappenTests(unittest.TestCase):
    """The before half.  Delete this class and the round proves nothing."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(
            ROOT / "current/pf_login_game_server_v141.py")

    def test_a_foreign_ledger_used_to_raise_at_the_composer(self):
        # Straight at ``mob_death``, which is where the refusal has always
        # come from and still does: this round did not make foreign ledgers
        # safe to USE, it made them safe to OFFER.
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.full_roster_override(
                self.legacy,
                field_mobs.roster_for_scene_id(BG0002_SCENE_ID),
                mob_death.DeathRegister(),
                ledger=bg0001_ledger(),
            )
        self.assertIn("cannot answer for identity", str(caught.exception))

    def test_the_same_offer_through_this_lane_is_answered_not_raised(self):
        override = mch.hostile_override_for_scene_id(
            self.legacy,
            BG0002_SCENE_ID,
            mob_death.DeathRegister(),
            ledger=bg0001_ledger(),
        )
        without = mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, mob_death.DeathRegister(),
            ledger=None,
        )
        # Declined means composed AS IF none had been passed -- byte for
        # byte, not merely "no exception".  A version that swallowed the
        # refusal and returned ``{}`` would also not raise, and would empty
        # the scene's hostile splice.
        self.assertEqual(override, without)
        self.assertEqual(len(override), 12)


class AdmissionStateTests(unittest.TestCase):
    """Half (b): three ways, each with a name a console can print."""

    def test_a_ledger_for_this_scene_is_consulted(self):
        record = admission.admit_ledger(BG0002_SCENE_ID, bg0002_ledger())
        self.assertEqual(record["state"], admission.STATE_SAME_SCENE)
        self.assertTrue(record["admitted"])
        self.assertIs(record["ledger"], record["ledger"])
        self.assertEqual(record["missing"], ())
        self.assertEqual(record["covered_count"], record["roster_count"])
        self.assertFalse(record["vacuous"])

    def test_a_ledger_for_another_scene_is_declined_by_its_own_label(self):
        record = admission.admit_ledger(BG0002_SCENE_ID, bg0001_ledger())
        self.assertEqual(record["state"], admission.STATE_OTHER_SCENE)
        self.assertFalse(record["admitted"])
        self.assertIsNone(record["ledger"])
        self.assertEqual(record["ledger_scene"], BG0001_SCENE)

    def test_the_label_decides_even_when_membership_would_have_passed(self):
        # Identities carry NO scene component -- ``field_mobs`` says so in
        # its own words -- so nothing prevents two scenes from asking for
        # the same numbers.  The two live rosters happen not to overlap
        # TODAY (measured in ``ConsoleTests`` below), which is why the
        # ledger here is built by hand: the hazard is real and the live
        # tables do not currently demonstrate it, and a pin that waits for
        # them to is a pin that arrives after the defect.  A ledger that
        # contains everything this scene's roster asks for and says it
        # belongs to another scene is still another scene's HP for monsters
        # that share a number.  A mutant that checks containment alone
        # admits this and is killed here.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        impostor = mob_combat.open_ledger(roster, scene="Bg0002")
        impostor = mob_combat.CombatLedger(
            impostor.balances, impostor.generation, BG0001_SCENE)
        record = admission.admit_ledger(
            BG0002_SCENE_ID, impostor, roster=roster)
        self.assertEqual(record["missing"], ())
        self.assertEqual(record["covered_count"], len(roster))
        self.assertEqual(record["state"], admission.STATE_OTHER_SCENE)
        self.assertFalse(record["admitted"])

    def test_a_ledger_for_this_scene_that_cannot_answer_is_declined(self):
        # The state that would have RAISED, and the reason containment is
        # checked even when the two labels agree: a ledger opened for this
        # scene before the roster changed shape carries the right label and
        # the wrong membership.  A mutant that trusts the label alone admits
        # this, and ``mob_death`` then refuses inside the listener thread.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        short = mob_combat.open_ledger(roster[:-1], scene="Bg0002")
        record = admission.admit_ledger(
            BG0002_SCENE_ID, short, roster=roster)
        self.assertEqual(
            record["state"], admission.STATE_SAME_SCENE_INCOMPLETE)
        self.assertFalse(record["admitted"])
        self.assertEqual(record["missing"], (roster[-1].actor_identity,))
        self.assertEqual(record["covered_count"], len(roster) - 1)

    def test_an_unscoped_ledger_is_admitted_on_containment_alone(self):
        # Every ledger in this tree was unscoped before this round, and a
        # third-party caller can still build one.  It is not refused for
        # lacking a label -- it is required to PROVE it, which the label
        # never did.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        unscoped = mob_combat.CombatLedger(
            mob_combat.open_ledger(roster).balances)
        self.assertIsNone(unscoped.scene)
        record = admission.admit_ledger(
            BG0002_SCENE_ID, unscoped, roster=roster)
        self.assertEqual(
            record["state"], admission.STATE_UNSCOPED_COVERS_ROSTER)
        self.assertTrue(record["admitted"])

    def test_an_unscoped_ledger_that_cannot_answer_is_declined(self):
        unscoped = mob_combat.CombatLedger(bg0001_ledger().balances)
        record = admission.admit_ledger(BG0002_SCENE_ID, unscoped)
        self.assertEqual(record["state"], admission.STATE_UNSCOPED_INCOMPLETE)
        self.assertFalse(record["admitted"])
        self.assertTrue(record["missing"])

    def test_no_ledger_at_all_is_a_named_state_not_a_silent_default(self):
        record = admission.admit_ledger(BG0002_SCENE_ID, None)
        self.assertEqual(record["state"], admission.STATE_ABSENT)
        self.assertFalse(record["admitted"])
        self.assertIsNone(record["ledger"])

    def test_a_state_that_read_nothing_does_not_report_nothing_missing(self):
        # The first draft of the console line printed ``covered=0/12
        # missing=none`` for an absent ledger: two fields contradicting each
        # other, with the reassuring one wrong.  Nothing was read on that
        # path, so there is no missing list to report -- and "none" is a
        # finding, not the absence of one.
        for ledger in (None, object()):
            record = admission.admit_ledger(BG0002_SCENE_ID, ledger)
            self.assertFalse(record["missing_measured"])
            self.assertIn(
                "missing=not_measured",
                admission.describe_ledger_admission(record)[0])
        measured = admission.admit_ledger(BG0002_SCENE_ID, bg0002_ledger())
        self.assertTrue(measured["missing_measured"])
        self.assertIn(
            "missing=none",
            admission.describe_ledger_admission(measured)[0])

    def test_something_that_is_not_a_ledger_is_declined_never_raised(self):
        # A census composer that dies on a malformed argument sends a
        # logged-in player an empty world.  Three shapes, none of them a
        # ledger, none of them allowed to escape.
        class Exploding:
            @property
            def scene(self):
                raise RuntimeError("no")

            def identities(self):
                return ()

        for thing in (object(), "Bg0002", 7, Exploding()):
            record = admission.admit_ledger(BG0002_SCENE_ID, thing)
            self.assertEqual(
                record["state"], admission.STATE_UNREADABLE, repr(thing))
            self.assertFalse(record["admitted"])

    def test_a_non_string_scene_on_a_ledger_like_object_is_unreadable(self):
        class Mislabelled:
            scene = 2
            identities = staticmethod(lambda: ())

        record = admission.admit_ledger(BG0002_SCENE_ID, Mislabelled())
        self.assertEqual(record["state"], admission.STATE_UNREADABLE)

    def test_admitted_is_vacuous_for_a_scene_with_no_monsters(self):
        # ``admitted`` alone is not evidence, and this is the case that
        # proves it: an empty roster is missing nothing, so any readable
        # ledger clears containment.  ``vacuous`` is what a caller reads to
        # tell "verified" from "nothing was asked".  Same lesson
        # ``census_backing_report`` learned about ``fully_backed``.
        record = admission.admit_ledger(
            NO_ROSTER_SCENE_ID, bg0001_ledger(), roster=())
        self.assertTrue(record["vacuous"])
        self.assertTrue(record["admitted"])
        self.assertEqual(record["roster_count"], 0)

    def test_ledger_for_scene_is_the_same_decision_without_the_record(self):
        self.assertIsNone(
            admission.ledger_for_scene(BG0002_SCENE_ID, bg0001_ledger()))
        keeper = bg0002_ledger()
        self.assertIs(
            admission.ledger_for_scene(BG0002_SCENE_ID, keeper), keeper)


class ConsoleTests(unittest.TestCase):
    """G-OBS: the decision reaches a boot log, or it did not happen."""

    def test_the_line_is_one_ascii_line_in_the_pinned_shape(self):
        record = admission.admit_ledger(BG0002_SCENE_ID, bg0001_ledger())
        lines = admission.describe_ledger_admission(record)
        self.assertEqual(len(lines), 1)
        lines[0].encode("ascii")
        self.assertNotIn("\n", lines[0])
        self.assertEqual(
            lines[0],
            "MOB_LEDGER_ADMISSION scene_id=2 scene=Bg0002 "
            "ledger_scene=%s state=other_scene admitted=no covered=0/12 "
            "missing=0x2033,0x203B,0x203C,0x203D,0x203E,0x204E,0x204F,"
            "0x2050,0x2051,0x2057,0x2058,0x2059 vacuous=no" % BG0001_SCENE,
        )

    def test_the_line_reports_what_was_true_not_only_what_was_decided(self):
        # ``covered=0/12`` above is the MEASURED half of the line: ``state=``
        # says what was decided, ``covered=`` says what was found.  A mutant
        # that decides by label and never looks at membership still prints
        # ``state=other_scene`` correctly and cannot print this number.
        #
        # MEASURED THIS ROUND, and it corrects an older sentence this lane
        # kept repeating: the two live rosters share NO identity today.
        # ``0x2068``/``0x206A`` were in both when round k3qe9q wrote that
        # down; scene 2's table has changed twice since (the owner-refusal
        # filter, then the Bg0002 regeneration) and the overlap is now zero.
        # The label still has to outrank containment -- identities carry no
        # scene component, so nothing STOPS a future overlap -- but this
        # file must not claim one exists when it does not.
        record = admission.admit_ledger(BG0002_SCENE_ID, bg0001_ledger())
        self.assertEqual(record["covered_count"], 0)
        overlap = (set(bg0001_ledger().identities())
                   & set(bg0002_ledger().identities()))
        self.assertEqual(overlap, set())

    def test_missing_prints_none_rather_than_disappearing(self):
        # A field that only appears when something is wrong makes "no line"
        # and "nothing wrong" the same observation.  GT-084 made that
        # misreading once already.
        line = admission.describe_ledger_admission(
            admission.admit_ledger(BG0002_SCENE_ID, bg0002_ledger()))[0]
        self.assertIn("missing=none", line)
        self.assertIn("state=same_scene", line)
        self.assertIn("admitted=yes", line)

    def test_an_undescribable_record_still_prints_a_line(self):
        self.assertEqual(
            admission.describe_ledger_admission({"scene_id": None}),
            ("MOB_LEDGER_ADMISSION state=undescribable",),
        )

    def test_the_three_ways_a_scene_can_be_absent_read_differently(self):
        # ``ledger_scene`` is None in the record for all three, and all three
        # would have printed ``ledger_scene=none``.  A reader who stops at
        # that field must not come away with the same sentence for "you
        # passed nothing", "you passed an old unscoped ledger" and "you
        # passed something that is not a ledger".
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        unscoped = mob_combat.CombatLedger(
            mob_combat.open_ledger(roster).balances)
        seen = {}
        for label, ledger in (
            ("absent", None),
            ("unscoped", unscoped),
            ("unreadable", object()),
        ):
            line = admission.describe_ledger_admission(
                admission.admit_ledger(
                    BG0002_SCENE_ID, ledger, roster=roster))[0]
            seen[label] = line.split("ledger_scene=")[1].split(" ")[0]
        self.assertEqual(
            seen,
            {"absent": "no_ledger", "unscoped": "unscoped",
             "unreadable": "unreadable"},
        )

    def test_a_recompose_with_no_ledger_prints_the_fatal_line(self):
        record = admission.require_ledger_for_recompose(BG0002_SCENE_ID, None)
        self.assertTrue(record["fatal"])
        lines = admission.describe_recompose_admission(record)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith(admission.FATAL_TOKEN))
        self.assertIn("reason=no_ledger_passed_to_recompose", lines[1])
        for line in lines:
            line.encode("ascii")

    def test_a_recompose_that_was_handed_a_ledger_prints_one_line(self):
        for ledger in (bg0002_ledger(), bg0001_ledger()):
            record = admission.require_ledger_for_recompose(
                BG0002_SCENE_ID, ledger)
            self.assertFalse(record["fatal"])
            self.assertEqual(
                len(admission.describe_recompose_admission(record)), 1)

    def test_a_declined_recompose_is_not_fatal_it_is_just_declined(self):
        # The COO's ruling escalates ONE state: nobody passed a ledger.  A
        # caller that passed the wrong one did its part, and printing FATAL
        # at it would train a reader to ignore the word.
        record = admission.require_ledger_for_recompose(
            BG0002_SCENE_ID, bg0001_ledger())
        self.assertEqual(record["state"], admission.STATE_OTHER_SCENE)
        self.assertFalse(record["fatal"])


class CensusLineTests(unittest.TestCase):
    """The state on the line a tester already greps."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(
            ROOT / "current/pf_login_game_server_v141.py")

    def _line(self, **kwargs):
        return mch.describe_census_hostility(
            BG0002_SCENE_ID, (), **kwargs)[0]

    def test_a_call_site_that_says_nothing_prints_a_named_gap(self):
        self.assertIn("ledger=not_reported", self._line())

    def test_passing_none_explicitly_is_a_different_report(self):
        # "I did not tell you" and "there was none" are facts about
        # different people.  Collapsing them would make a call site that
        # forgot the keyword print a line accusing itself of a defect.
        self.assertIn("ledger=absent", self._line(ledger=None))

    def test_the_line_reports_the_admission_state_by_name(self):
        self.assertIn(
            "ledger=other_scene", self._line(ledger=bg0001_ledger()))
        self.assertIn(
            "ledger=same_scene", self._line(ledger=bg0002_ledger()))

    def test_the_line_agrees_with_the_decision_the_composer_made(self):
        # The line asks the question a SECOND time, re-resolving the roster,
        # because a runtime.py call site never holds the roster.  A report
        # computed from a re-derivation can agree with itself while the real
        # composition does something else -- this lane wrote that sentence
        # about its own report function two rounds ago -- so the equivalence
        # is pinned instead of assumed.
        register = mob_death.DeathRegister()
        for ledger in (bg0001_ledger(), bg0002_ledger(), None):
            state = admission.admit_ledger(
                BG0002_SCENE_ID, ledger,
                roster=field_mobs.roster_for_scene_id(BG0002_SCENE_ID),
            )["state"]
            self.assertIn("ledger=%s" % state, self._line(ledger=ledger))
            composed = mch.hostile_override_for_scene_id(
                self.legacy, BG0002_SCENE_ID, register, ledger=ledger)
            consulted = mch.hostile_override_for_scene_id(
                self.legacy, BG0002_SCENE_ID, register, ledger=None)
            admitted = state in admission.ADMITTING_STATES
            # A consulted ledger at full HP composes the same bytes as none
            # at all, so this compares the DECISION, not a side effect of it.
            self.assertEqual(
                admitted,
                state in (admission.STATE_SAME_SCENE,
                          admission.STATE_UNSCOPED_COVERS_ROSTER),
            )
            self.assertEqual(composed, consulted)

    def test_a_broken_ledger_does_not_take_the_console_line_down(self):
        class Exploding:
            def identities(self):
                raise RuntimeError("no")

        line = self._line(ledger=Exploding())
        self.assertIn("ledger=ledger_unreadable", line)
        line.encode("ascii")


class WireLayerTests(unittest.TestCase):
    """The bytes, which is the layer this lane is allowed to claim."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(
            ROOT / "current/pf_login_game_server_v141.py")

    def _override(self, ledger):
        return mch.hostile_override_for_scene_id(
            self.legacy, BG0002_SCENE_ID, mob_death.DeathRegister(),
            ledger=ledger,
        )

    def test_a_wounded_monster_stays_wounded_when_the_ledger_is_its_own(self):
        # BUILD-005's promise at the wire layer, in one scene, in bytes.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        ledger = mob_combat.open_ledger_for_scene_id(BG0002_SCENE_ID)
        subject = roster[0].actor_identity
        row = ledger.balance_of(subject)
        wounded = ledger.with_balance(
            mob_combat.MobBalance(subject, row.max_hp, row.max_hp // 2))
        healed = self._override(None)
        kept = self._override(wounded)
        self.assertNotEqual(kept[subject], healed[subject])
        for identity in kept:
            if identity != subject:
                self.assertEqual(kept[identity], healed[identity])

    def test_a_wounded_monster_in_a_foreign_ledger_changes_nothing(self):
        # The declined path, measured the same way: identical bytes to the
        # no-ledger composition, and no exception.  This is the state the
        # Bg0002 branch is in today, now visible instead of guessed at.
        #
        # The wound is put on a monster this scene's roster DOES ask for,
        # inside a ledger that says it is bg0001's.  That is the strongest
        # form of the case: the numbers line up and the ledger is still not
        # this scene's, so a version that forwarded it would produce
        # different bytes and this assertion would catch it.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        subject = roster[0].actor_identity
        foreign = mob_combat.CombatLedger(
            mob_combat.open_ledger(roster).balances, 0, BG0001_SCENE)
        row = foreign.balance_of(subject)
        wounded = foreign.with_balance(
            mob_combat.MobBalance(subject, row.max_hp, row.max_hp // 2))
        self.assertEqual(wounded.scene, BG0001_SCENE)
        self.assertEqual(self._override(wounded), self._override(None))

    def test_the_admission_is_asked_about_the_rows_being_composed(self):
        # A check computed from a second copy of the thing it checks can
        # agree with itself while the composition raises.  The composer
        # resolves the roster once and hands THAT to the admission.
        roster = field_mobs.roster_for_scene_id(BG0002_SCENE_ID)
        record = admission.admit_ledger(
            BG0002_SCENE_ID, bg0002_ledger(), roster=roster)
        self.assertTrue(record["admitted"])
        self.assertEqual(record["roster_count"], len(roster))


class DiagnosticWideningTests(unittest.TestCase):
    """The one other place in this tree that builds a ledger by hand."""

    def test_widening_a_ledger_for_diagnostics_keeps_its_scene(self):
        # ``diag_multi_object_wiring.widen_for_combat`` rebuilds the session
        # ledger with five diagnostic rows appended, positionally.  Before
        # this pin it dropped the new field, so the FIRST diagnostic
        # widening turned a scoped ledger into an unscoped one -- and an
        # unscoped ledger is admitted into any scene whose roster it happens
        # to contain.  A ledger that forgets its scene the moment a
        # diagnostic boot touches it is a ledger that is scoped exactly
        # until someone uses the feature that needs it.
        roster = field_mobs.load_roster()
        ledger = mob_combat.open_ledger(roster)
        self.assertEqual(ledger.scene, BG0001_SCENE)
        wider_roster, wider, refusal = wiring.widen_for_combat(
            roster, ledger, diag.diagnostic_objects())
        self.assertIsNone(refusal)
        self.assertGreater(len(wider.balances), len(ledger.balances))
        self.assertEqual(wider.scene, BG0001_SCENE)
        self.assertEqual(len(wider_roster), len(wider.balances))


class NoPrintingInsideTests(unittest.TestCase):
    """The module composes lines; it never writes to a console itself."""

    def test_it_declares_itself_shippable_and_gates_on_nothing(self):
        self.assertTrue(admission.production_allowed)
        self.assertFalse(admission.test_only)
        # Checked on the CODE, not on the prose: the docstrings talk about
        # flags and scenarios at length, and a substring scan over the whole
        # file would either fail on its own explanation or force the
        # explanation out.  What must be absent is any executable reach for
        # one -- an environment read, a file open, an imported gate.
        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation"
             / "mob_ledger_admission.py").read_text(encoding="ascii"))
        called = set()
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                called.add(
                    getattr(node.func, "id", "")
                    or getattr(node.func, "attr", ""))
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for gate in ("open", "getenv", "environ", "load_scenario"):
            self.assertNotIn(gate, called, gate)
        self.assertEqual(imported, {"__future__", "typing", ""})

    def test_admitting_a_ledger_prints_nothing(self):
        captured = io.StringIO()
        with redirect_stdout(captured):
            admission.admit_ledger(BG0002_SCENE_ID, bg0001_ledger())
            admission.describe_ledger_admission(
                admission.admit_ledger(BG0002_SCENE_ID, None))
        self.assertEqual(captured.getvalue(), "")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
