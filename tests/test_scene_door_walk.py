"""LANE-B round pcsjfr: the three doors of M4/M5, walked on the shipped roster.

WHY THIS FILE EXISTS.  ``COO-DECISION 2026-09-04T14:50+07:00`` item 3 took
scene 4 out of the queue with a condition attached: no new scene is armed
until at least ONE armed scene has every door -- a monster you can hit, a
monster that dies, and an object on the ground when it does.  Three scenes
were armed (Bg0003, bg0005, Bg0015) and nothing in this tree could answer
that condition: it was answered by reading three modules and believing the
join.  ``scene_door_walk`` walks it instead, and this file is what holds the
walk to the roster the server actually ships.

WHAT THE WALK MEASURES TODAY.  These are the assertions below, not a
transcript, and ROUND j5v7mu2 (pf-adversary D7) corrected the field names --
the earlier version of this block invented ``refused_by_owner``/``withheld``,
which is not what ``describe_scene_doors`` prints and is not greppable::

    SCENE_DOORS scene='Bg0002' rows=12 owner_refusal_list=8 lane_withheld=0 ai=open target=12 kill=12 drop=12 every_door=yes short=none
    SCENE_DOORS scene='Bg0003' rows=12 owner_refusal_list=0 lane_withheld=0 ai=open target=12 kill=12 drop=12 every_door=yes short=none
    SCENE_DOORS scene='Bg0015' rows=11 owner_refusal_list=0 lane_withheld=1 ai=open target=11 kill=11 drop=11 every_door=yes short=none
    SCENE_DOORS scene='bg0001' rows=4 owner_refusal_list=0 lane_withheld=0 ai=open target=4 kill=4 drop=0 every_door=no short=103/t916,105/t916,107/t916,109/t916
    SCENE_DOORS scene='bg0005' rows=6 owner_refusal_list=0 lane_withheld=0 ai=open target=6 kill=6 drop=6 every_door=yes short=none
    SCENE_DOORS summary live_scenes=5 owner_refusal_list=8 lane_withheld=1(Bg0015:1) every_door=Bg0002,Bg0003,Bg0015,bg0005

``short=`` WAS MISSING FROM THIS BLOCK TWICE (pf-adversary D-C).  It is the
field that names WHICH rows fell short, which is the denominator question the
whole file is about, and it had no assertion anywhere in the repo -- a mutant
returning ``()`` from ``rows_short_of_every_door`` printed ``short=none`` for
bg0001's four undroppable dummies and nothing noticed.  It is asserted now, in
``test_the_short_field_names_the_rows_and_is_not_decoration``.

NOBODY PRINTS THESE (pf-adversary D7).  ``scene_door_walk`` has no production
caller -- grepped across ``src/``, ``tools/`` and ``current/``; the module's
own ``SCENE_DOOR_WALK_CENSUS_CALL`` is the line a boot WOULD add and says
plainly that no call site exists.  So a letter quoting these lines is
quoting a lane diagnostic, not a server console, and this file says so here
because two of this lane's letters said otherwise.

WHAT CHANGED IN ROUND j5v7mu, AND WHAT DID NOT.  The Bg0015 row above is the
whole diff: ``COO-DECISION 20260905_0545`` (answering this lane's ASK-COO of
04:52, option 3) withheld placement 87 -- Carlos -- from what this lane
ships, because a monster a player can take to 0 HP and then never kill is a
thing the player SEES and it contradicts M4's own criterion 2 directly.
Nothing about Carlos was fixed and this file does not pretend otherwise: he
is exactly as unkillable as he was, ``ARowNoLetterCoversStandsAtZeroTests``
still measures that end to end on the unfiltered table, and ``withheld=1``
travels beside scene 14's ``yes`` for the same reason ``refused_by_owner``
travels beside every other one.

``refused_by_owner`` IS PART OF THE CLAIM AND NOT DECORATION (pf-adversary
D2).  The verdict is a fraction over the rows ``load_roster`` hands a
session, and the owner can shrink the denominator: Bg0002 ships 20
placements and the roster hands over 12.  The two scenes this round reports
as finished, Bg0003 and bg0005, each refuse ZERO -- which is the sentence
the letter actually needs and the one a bare "every_door=yes" cannot make.

THE TWO NEGATIVES ARE PINNED AS HARD AS THE POSITIVES, because each is a
different fact and a file that only pinned the wins would let either turn
into a silent yes:

  * ``bg0001``'s four rows are template 916, the Training Iron Man.  Its MOBS
    row names NO drop set at all (``drops_normal``, ``drops_equipment`` and
    ``drops_specially`` are each 0), so it is KILLABLE AND DROPS NOTHING --
    which is what a training dummy is, not a hole.  ~~It names no drop set
    the shipped tables carry~~ IS STRUCK, pf-adversary D7: that is a
    DIFFERENT state, it would come back as a refusal rather than an empty
    sweep, and this file asserted the absence of refusals in the same breath.
  * ``Bg0015`` placement 87 (template 924, Carlos, identity 0x2058) ~~is
    TARGETABLE AND CANNOT DIE~~ IS NO LONGER SHIPPED, round j5v7mu.
    ``COO-RULING-20260901-1046`` covers six of that scene's seven templates
    and holds Carlos back on purpose, so ``mob_death.ruling_for`` refuses him
    -- and a player who swings at him takes him to 0 HP, gets no death
    frames, and is answered with silence for every swing after that.
    ``ARowNoLetterCoversStandsAtZero`` still measures that end to end, on the
    unfiltered table, because the state belongs to "a row no letter covers"
    and not to Carlos.  What changed is that ``load_roster`` no longer hands
    him to a session, so no player can reach it today.  The ruling that
    withheld him is ``COO-DECISION 20260905_0545``, it is a LANE ruling and
    not an owner one, and the two lists are carried apart in ``field_mobs``
    for that reason.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import (  # noqa: E402
    field_mob_hostile_bg0015,
    field_mobs,
    mob_combat,
    mob_death,
    mob_loot,
    scene_door_walk,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

V141 = ROOT / "current/pf_login_game_server_v141.py"

#: The scene COO-DECISION 2026-09-04T14:50+07:00 armed and this round is
#: reporting on.  Named once so a reader can see which claim is about it.
SCENE_THREE = "Bg0003"
CARLOS_PLACEMENT = 87
CARLOS_TEMPLATE = 924
CARLOS_IDENTITY = 0x2058
TRAINING_IRON_MAN = 916


class WalkTheShippedRosterTests(unittest.TestCase):
    """The walk, run once against the frozen serializer and the real tables."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)
        cls.walked = {
            one.scene: one
            for one in scene_door_walk.walk_live_scenes(cls.legacy)
        }

    def test_every_live_scene_was_walked_and_none_of_them_refused(self):
        self.assertEqual(
            set(self.walked), set(field_mobs.live_scenes()))
        for scene, one in self.walked.items():
            self.assertEqual(one.reason, "", scene)
            self.assertEqual(one.rows_walked, len(
                field_mobs.load_roster(scene=scene)), scene)

    def test_scene_three_has_every_door_on_every_shipped_row(self):
        """The condition COO-DECISION 2026-09-04T14:50 item 3 put on scene 4.

        Not "a monster in scene 3 can be killed" -- all twelve, through all
        three doors, which is the sentence that letter's item 3 is about.
        """
        scene_three = self.walked[SCENE_THREE]
        self.assertEqual(scene_three.rows_walked, 12)
        self.assertEqual(scene_three.targetable, 12)
        self.assertEqual(scene_three.killable, 12)
        self.assertEqual(scene_three.dropping, 12)
        self.assertEqual(scene_three.rows_short_of_every_door, ())
        self.assertTrue(scene_three.ai_register)
        self.assertTrue(scene_three.every_door_open)
        # AND THE DENOMINATOR IS WHOLE.  The verdict would be worth nothing
        # if the failing rows had simply not been shipped (pf-adversary D2).
        self.assertEqual(scene_three.owner_refused, ())

    def test_at_least_one_armed_scene_is_finished_and_it_is_named(self):
        """The condition itself, plus the two scenes that meet it today.

        DELIBERATELY NOT AN EXACT SET.  A lane arming a fourth scene would
        turn an ``assertEqual`` here red on a change that is none of this
        lane's business, and a tripwire in somebody else's way is a tripwire
        they will delete.  What is pinned is what this round claims: the
        condition is met, and it is met by scene 3 and scene 5.
        """
        finished = tuple(sorted(
            scene for scene, one in self.walked.items()
            if one.every_door_open))
        self.assertIn(SCENE_THREE, finished)
        self.assertIn("bg0005", finished)
        self.assertLessEqual(set(finished), set(self.walked))
        # Neither of the two this round reports on owes its verdict to a row
        # the owner refused to ship.
        for scene in (SCENE_THREE, "bg0005"):
            self.assertEqual(self.walked[scene].owner_refused, (), scene)

    def test_scene_fourteen_has_every_door_at_eleven_rows_carlos_withheld(self):
        """~~short by Carlos alone~~ IS STRUCK, and the number beside it is why.

        ``COO-DECISION 20260905_0545`` withheld placement 87 rather than
        fixing him, so this scene's verdict flipped from ``no`` to ``yes``
        WITHOUT ANYTHING CHANGING ABOUT CARLOS -- exactly the outcome the
        ``owner_refused`` docstring predicted one round earlier.  That is
        why ``lane_withheld`` is asserted here in the same breath as the
        verdict: a reader who sees ``every_door=yes`` for scene 14 and not
        the ``1`` beside it has been told something untrue.  The scene is
        NOT in the "finished with a whole denominator" class scene 3 and
        scene 5 are in, and :meth:`test_at_least_one_armed_scene_is_
        finished_and_it_is_named` still names only those two.
        """
        scene14 = self.walked["Bg0015"]
        self.assertEqual(scene14.rows_walked, 11)
        self.assertEqual(scene14.targetable, 11)
        self.assertEqual(scene14.killable, 11)
        self.assertEqual(scene14.dropping, 11)
        self.assertEqual(scene14.rows_short_of_every_door, ())
        self.assertTrue(scene14.every_door_open)
        # THE DENOMINATOR, both halves.  The owner refused nothing here; this
        # lane withheld one, and the two are reported apart on purpose.
        self.assertEqual(scene14.owner_refused, ())
        self.assertEqual(scene14.lane_withheld, (CARLOS_PLACEMENT,))
        # And the withheld row is the one this file has always named.
        self.assertNotIn(
            CARLOS_IDENTITY, {row.actor_identity for row in scene14.rows})
        self.assertNotIn(
            CARLOS_TEMPLATE, {row.template_id for row in scene14.rows})
        # The line this module's own reporter produces carries the number,
        # not just the record.
        #
        # ~~this is the string a boot prints and a tester reads~~ IS STRUCK,
        # ROUND j5v7mu2 (pf-adversary D7): NOTHING PRINTS IT.  Grepped across
        # `src/`, `tools/` and `current/` -- `scene_door_walk` is imported by
        # this test file and nothing else, and the module's own
        # `SCENE_DOOR_WALK_CENSUS_CALL` says in as many words that the call
        # site does not exist and this lane does not wait on one.  The
        # correct layer tag for every SCENE_DOORS line in this round's
        # letters is "output of a lane diagnostic function", not "server
        # console".
        line = scene_door_walk.describe_scene_doors(scene14)
        self.assertIn("rows=11", line)
        self.assertIn("lane_withheld=1", line)
        self.assertIn("every_door=yes", line)

    def test_the_short_field_names_the_rows_and_is_not_decoration(self):
        """pf-adversary D-C: the one field on the line nothing asserted.

        Pinned from both sides -- a scene with rows short must NAME them,
        and a scene with none must say ``none`` -- so neither "the field
        went blank" nor "the field always lists something" can pass.
        """
        town = scene_door_walk.describe_scene_doors(self.walked["bg0001"])
        self.assertIn(
            "short=103/t916,105/t916,107/t916,109/t916", town)
        for scene in (SCENE_THREE, "bg0005", "Bg0015"):
            line = scene_door_walk.describe_scene_doors(self.walked[scene])
            self.assertIn("short=none", line, scene)
        # And the field agrees with the record it is formatted from.
        for scene, one in self.walked.items():
            line = scene_door_walk.describe_scene_doors(one)
            named = line.split("short=")[1]
            for row in one.rows_short_of_every_door:
                self.assertIn(
                    "%d/t%d" % (row.placement_index, row.template_id),
                    named, scene)
            if not one.rows_short_of_every_door:
                self.assertEqual(named, "none", scene)

    def test_the_summary_line_says_which_scene_withheld_a_row(self):
        """ROUND j5v7mu2, pf-adversary D7.

        The summary carried a bare SUM over five scenes next to an
        ``every_door`` list naming four of them, so a reader could not tell
        which of the four owed its ``yes`` to a removed row -- which is the
        only thing that number is for.
        """
        lines = scene_door_walk.describe_live_scene_doors(self.legacy)
        summary = [one for one in lines if " summary " in one]
        self.assertEqual(len(summary), 1)
        summary = summary[0]
        self.assertIn("lane_withheld=1(Bg0015:1)", summary)
        # Bg0015 IS in the finished list, and that is exactly why the scene
        # has to be named beside the count rather than summed into it.
        self.assertIn("Bg0015", summary.split("every_door=")[1])
        # ASCII and bounded like every other line this module emits.
        self.assertTrue(summary.isascii())
        summary.encode("cp874")

    def test_a_walk_where_nobody_withholds_says_zero_not_an_empty_list(self):
        """The ordinary case stays one character (pf-adversary D7)."""
        nothing = scene_door_walk.SceneDoors("bg0001", ai_register=True)
        self.assertEqual(scene_door_walk._withheld_by_scene((nothing,)), "0")
        one = scene_door_walk.SceneDoors(
            "Bg0015", lane_withheld=(87,), ai_register=True)
        self.assertEqual(
            scene_door_walk._withheld_by_scene((nothing, one)), "1(Bg0015:1)")

    def test_the_scene_name_in_the_summary_is_bounded_and_cp874_safe(self):
        """pf-adversary D-G: the guard this helper's docstring claims.

        The first version of that claim was unfalsifiable -- the only names
        the test fed it were ``Bg0015`` and ``bg0001``, both short ASCII, so
        dropping ``_console_scene`` from the helper left the suite green.
        The two inputs below are the two failures ``_console_scene`` exists
        for and they are this module's own scars: a 5,000-character name
        turned a bounded report line into a 5,052-character one, and one
        U+2011 in a name copied out of a document made a cp874 ``print``
        raise inside the report.
        """
        long_name = scene_door_walk.SceneDoors(
            "x" * 5000, lane_withheld=(87,), ai_register=True)
        line = scene_door_walk._withheld_by_scene((long_name,))
        self.assertLess(
            len(line),
            scene_door_walk.SCENE_NAME_ON_A_CONSOLE_LINE + 32)
        non_ascii = scene_door_walk.SceneDoors(
            "Bg\u2011015", lane_withheld=(87,), ai_register=True)
        escaped = scene_door_walk._withheld_by_scene((non_ascii,))
        self.assertTrue(escaped.isascii())
        escaped.encode("cp874")
        # ESCAPED, NOT DROPPED: a name that was wrong stays recognisable in
        # the line that says so, same as every other field here.
        self.assertIn("Bg", escaped)

    def test_the_training_dummies_die_and_drop_nothing_and_that_is_the_row(self):
        """bg0001's four rows: killable, dropping nothing, by their own table.

        THE REASON IS READ OFF THE ROW, not inferred from the empty sweep
        (pf-adversary D7): ``drop_sets`` is how many of the three tables this
        template's own MOBS entry names, and for 916 it is zero.  A row that
        named a set and rolled nothing 32 times would look identical in the
        booleans and is a different fact.
        """
        town = self.walked["bg0001"]
        self.assertEqual(town.rows_walked, 4)
        self.assertEqual(town.targetable, 4)
        self.assertEqual(town.killable, 4)
        self.assertEqual(town.dropping, 0)
        for row in town.rows:
            self.assertEqual(row.template_id, TRAINING_IRON_MAN)
            self.assertEqual(row.drop_sets, 0)
            self.assertEqual(row.seeds_that_dropped, 0)
            # The sweep ran to the end and found nothing, which is a
            # different answer from a sweep that stopped early.
            self.assertEqual(row.seeds_walked, len(scene_door_walk.DROP_SEEDS))
            self.assertEqual(row.refusals, ())

    def test_a_row_that_drops_names_how_many_seeds_did(self):
        """The drop door is a SWEEP, so the evidence is a count not a bool.

        A row reported as dropping has to have a nonzero seed count and a row
        reported as not dropping has to have zero -- otherwise the boolean is
        a second, guessable source of truth for the same measurement.
        """
        for scene, one in self.walked.items():
            for row in one.rows:
                where = "%s placement %d" % (scene, row.placement_index)
                self.assertEqual(
                    row.drop, row.seeds_that_dropped > 0, where)
                # A PARTIAL SWEEP IS VISIBLE (pf-adversary D11): a refusal
                # stops it, so a count between 1 and N-1 must carry one.
                self.assertLessEqual(
                    row.seeds_that_dropped, row.seeds_walked, where)
                if 0 < row.seeds_walked < len(scene_door_walk.DROP_SEEDS):
                    self.assertTrue(row.refusals, where)
                if not row.kill:
                    self.assertEqual(row.seeds_walked, 0, where)


class TheWalkTouchesNothingItDoesNotOwnTests(unittest.TestCase):
    """A diagnostic that changes the game is a diagnostic nobody may run."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_the_world_floor_is_not_seeded_by_walking(self):
        """The walk kills twelve monsters and never tells the world's floor.

        ~~a before/after count of ``world_ground().standing()``~~ IS STRUCK,
        pf-adversary D1 of this round, which put the mutant through it: a
        walk that DID call ``remember_generation`` passed the counting
        version of this test, for two reasons that both had to be understood
        before the guard could be rebuilt.  (a) ``unittest`` sorts methods,
        so a sibling in this class had already walked this scene and the
        "before" count was the seeded one; (b) every walk builds a fresh
        cell, so every walk mints the SAME drop keys, and ``WorldGround``
        dedups by key -- the second seeding is ``already_standing`` and the
        count does not move.  A guard whose failure mode is "the mutant
        seeded it twice" is not a guard.

        So the doors are watched instead of the floor: both functions that
        can reach the world are replaced for the duration of the walk and
        must not be called at all.  A count is checked too, but as the
        second line of defence rather than the first.
        """
        from pirateforce_foundation import mob_ground_persistence
        from pirateforce_foundation import mob_drop_presence

        called: list = []

        def spy(name, original):
            def watched(*args, **kwargs):
                called.append(name)
                return original(*args, **kwargs)
            return watched

        for module, name in (
                (mob_ground_persistence, "remember_generation"),
                (mob_ground_persistence, "persist_generation"),
                (mob_drop_presence, "sustain_a_kill"),
        ):
            original = getattr(module, name)
            setattr(module, name, spy(name, original))
            self.addCleanup(setattr, module, name, original)

        floor = mob_ground_persistence.world_ground()
        before = len(floor.standing(SCENE_THREE))
        walked = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        self.assertTrue(walked.every_door_open)
        self.assertEqual(called, [])
        self.assertEqual(len(floor.standing(SCENE_THREE)), before)

    def test_the_death_register_of_a_walk_does_not_escape_it(self):
        """Two walks answer identically; a shared register would not.

        A register kept between rows would refuse the second kill of the same
        identity (``mob_death`` records a death once), so a walk that leaked
        one would report a scene as finished on the first run and short on
        the second.
        """
        first = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        second = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        # THE ABSOLUTE NUMBER FIRST (pf-adversary D10): comparing two runs to
        # each other passes when a leaked register has already been drained by
        # an earlier test in the file, because both runs then read 0.  What a
        # leak cannot survive is the scene's own count on BOTH runs.
        self.assertEqual(first.killable, 12)
        self.assertEqual(second.killable, 12)
        self.assertEqual(first.rows_short_of_every_door,
                         second.rows_short_of_every_door)


class TheWalkRefusesRatherThanRaisesTests(unittest.TestCase):
    """Every entry point this lane writes fails closed with a name."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_a_scene_nobody_ships_is_refused_by_name(self):
        walked = scene_door_walk.walk_scene(self.legacy, "Bg9999")
        self.assertEqual(walked.reason, scene_door_walk.REFUSE_NOT_A_LIVE_SCENE)
        self.assertEqual(walked.rows, ())
        self.assertFalse(walked.every_door_open)
        self.assertIn(
            scene_door_walk.SCENE_DOORS_REFUSED_TOKEN,
            scene_door_walk.describe_scene_doors(walked))

    def test_a_scene_that_is_not_a_string_is_refused_by_name(self):
        for junk in (None, 3, b"Bg0003", ["Bg0003"]):
            walked = scene_door_walk.walk_scene(self.legacy, junk)
            self.assertEqual(
                walked.reason, scene_door_walk.REFUSE_NOT_A_LIVE_SCENE,
                repr(junk))
            self.assertEqual(walked.scene, "")

    def test_something_that_is_not_the_serializer_is_refused_by_name(self):
        for junk in (None, object(), "legacy"):
            walked = scene_door_walk.walk_scene(junk, SCENE_THREE)
            self.assertEqual(
                walked.reason,
                scene_door_walk.REFUSE_LEGACY_NOT_A_SERIALIZER, repr(junk))

    def test_a_row_the_walk_cannot_describe_does_not_unwind_the_walk(self):
        """"NEVER RAISES" covers the record too (pf-adversary D6).

        The three fields read off the mob used to sit outside every ``try``,
        so a row whose ``placement_index`` was ``None`` raised a ``TypeError``
        straight out of ``walk_scene`` -- out of the one entry point whose
        docstring promises a console line may call it.
        """
        class NoPlacement:
            placement_index = None
            template_id = 1
            actor_identity = 0x2001
            scene = SCENE_THREE
            drops_normal = drops_equipment = drops_specially = 0

        row = scene_door_walk._walk_row(self.legacy, NoPlacement(), True)
        self.assertEqual(row.placement_index, -1)
        self.assertFalse(row.every_door_open)
        self.assertTrue(row.refusals)

    def test_a_scene_name_cannot_break_the_line_it_is_printed_on(self):
        """A caller-supplied name is truncated and escaped (pf-adversary D5).

        Measured on the real console encoding of the bridge: an ordinary
        non-breaking hyphen pasted out of a document used to make the
        report's own ``print`` raise, and a long name made the "bounded"
        line 5,000 characters long.
        """
        for junk in ("Bg\u2011" + "x" * 5000, "\u4e1c\u4eac", "Caf\u00e9",
                     "B" * 400):
            line = scene_door_walk.describe_scene_doors(
                scene_door_walk.walk_scene(self.legacy, junk))
            line.encode("ascii")
            line.encode("cp874")
            self.assertLess(len(line), 200, len(line))
            self.assertTrue(
                line.startswith(scene_door_walk.SCENE_DOORS_REFUSED_TOKEN))

    def test_a_refused_walk_is_never_reported_as_every_door_open(self):
        for reason in ("", scene_door_walk.REFUSE_ROSTER_UNREADABLE):
            walked = scene_door_walk.SceneDoors(SCENE_THREE, (), reason)
            self.assertFalse(walked.every_door_open)

    def test_the_console_line_is_bounded_ascii_on_every_live_scene(self):
        """And NOT ONE OF THEM IS A STAND-DOWN LINE (pf-adversary D5).

        The first draft asked only ``startswith(SCENE_DOORS_TOKEN)``, which a
        run where every scene refused would also have satisfied -- the
        refusal token was a prefix of the good one.  It is not any more, and
        this test says which of the two it expects.
        """
        for line in scene_door_walk.describe_live_scene_doors(self.legacy):
            line.encode("ascii")
            line.encode("cp874")
            self.assertLess(len(line), 300, line)
            self.assertTrue(line.startswith(scene_door_walk.SCENE_DOORS_TOKEN))
            self.assertNotIn(
                scene_door_walk.SCENE_DOORS_REFUSED_TOKEN, line)

    def test_the_summary_line_names_the_finished_scenes(self):
        lines = scene_door_walk.describe_live_scene_doors(self.legacy)
        summary = lines[-1]
        self.assertIn("summary", summary)
        self.assertIn("live_scenes=%d" % len(field_mobs.live_scenes()), summary)
        named = summary.split("every_door=")[1].split()[0].split(",")
        self.assertIn(SCENE_THREE, named)
        self.assertIn("bg0005", named)
        # The summary is the per-scene lines' own answer, never a second one.
        walked = {one.scene: one
                  for one in scene_door_walk.walk_live_scenes(self.legacy)}
        self.assertEqual(
            sorted(named),
            sorted(s for s, one in walked.items() if one.every_door_open))


class ARowNoLetterCoversStandsAtZeroTests(unittest.TestCase):
    """The Bg0015 hole, measured end to end rather than inferred from a table.

    This is the state ``runtime.py``'s except branch calls "honest
    degradation": the kill refuses, no death frames go out, and the monster
    is left at the floor.  What the walk found is the half that sentence does
    not say out loud -- the monster is a TARGET first, so a player can put it
    there, and every swing after that is answered with no frames at all.

    ROUND j5v7mu: KEPT DELIBERATELY, ON THE UNFILTERED ROSTER.  Carlos is no
    longer shipped (``COO-DECISION 20260905_0545``), so no player can reach
    this state today -- but the state is a property of "a row no letter
    covers", not of Carlos, and the next such row will arrive with a lane
    that has forgotten what it looks like.  ``COO-DECISION 20260905_0545``
    says in as many words to keep this class as the guard for that row.  It
    therefore reads ``field_mob_hostile_bg0015.scene14_hostile_roster()``,
    which parses all twelve and filters nothing, and
    :meth:`test_he_is_no_longer_in_the_live_roster` is the one assertion
    here that is about the ruling rather than about the mechanism.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)
        # The UNFILTERED parse: load_roster no longer hands him over, which
        # is the point of the ruling and would make this whole class vanish
        # into an IndexError in setUpClass -- a guard that disappears the
        # moment its subject does is not a guard.
        roster = field_mob_hostile_bg0015.scene14_hostile_roster()
        cls.carlos = [
            m for m in roster if m.template_id == CARLOS_TEMPLATE][0]
        cls.roster = roster

    def test_he_is_no_longer_in_the_live_roster(self):
        """COO-DECISION 20260905_0545, measured where a player would meet it.

        Both directions: gone from what a session is handed, still present
        in the table this class walks -- otherwise "withheld" and "never
        mined" would look identical here.
        """
        live = field_mobs.load_roster(scene="Bg0015")
        self.assertNotIn(
            CARLOS_IDENTITY, {m.actor_identity for m in live})
        self.assertNotIn(CARLOS_PLACEMENT, {m.placement_index for m in live})
        self.assertIn(
            CARLOS_IDENTITY, {m.actor_identity for m in self.roster})
        self.assertEqual(
            field_mobs.lane_withheld_placements("Bg0015"),
            (CARLOS_PLACEMENT,))
        # The reason travels with the ruling; a withheld list with no reason
        # beside it is the write-only literal this project already had once.
        self.assertIn(
            "924", field_mobs.lane_withheld_reason("Bg0015"))

    def test_no_registered_letter_covers_him(self):
        self.assertEqual(mob_death.rulings_covering(self.carlos), ())
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(self.carlos)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)

    def test_one_swing_takes_him_to_zero_and_the_kill_refuses(self):
        ledger = mob_combat.open_ledger(self.roster)
        step = mob_combat.strike(
            self.legacy, None, ledger, None, self.carlos,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        self.assertTrue(step.outcome.death_due)
        self.assertEqual(step.outcome.hp_after, 0)
        with self.assertRaises(mob_death.MobDeathContractError):
            mob_death.kill(
                self.legacy, self.carlos, step.outcome,
                widened=mob_death.ruling_for(self.carlos))

    def test_the_next_swing_answers_with_no_frames_at_all(self):
        """A monster at 0 HP that never died answers nothing, for ever.

        Pinned so the day somebody changes what a player may do to him, this
        test says which state they changed away from.
        """
        ledger = mob_combat.open_ledger(self.roster)
        first = mob_combat.strike(
            self.legacy, None, ledger, None, self.carlos,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        second = mob_combat.strike(
            self.legacy, None, mob_combat.commit_step(ledger, first), None,
            self.carlos, scene_door_walk.WALKER_IDENTITY,
            scene_door_walk.WALKER)
        self.assertEqual(second.frames, ())
        self.assertEqual(second.outcome.hp_after, 0)


class TheKillDoorAndTheLettersAgreeTests(unittest.TestCase):
    """The walk's kill door is the registered letters, not a second opinion."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_every_row_the_walk_kills_names_the_letter_it_travelled_under(self):
        for one in scene_door_walk.walk_live_scenes(self.legacy):
            for row in one.rows:
                if not row.kill:
                    continue
                mob = [
                    m for m in field_mobs.load_roster(scene=one.scene)
                    if m.placement_index == row.placement_index][0]
                if row.ruling:
                    self.assertIn(row.ruling, mob_death.WIDENING_RULINGS)
                    self.assertIn(row.ruling, mob_death.rulings_covering(mob))
                else:
                    # The sanctioned first target is the one row kill()
                    # admits with no letter at all; nothing else may be here.
                    self.assertEqual(
                        mob.actor_identity,
                        mob_death.SANCTIONED_FIRST_TARGET_IDENTITY)


class TheDropDoorIsTheShippedTablesTests(unittest.TestCase):
    """A drop door opens on the mined tables, never on a composed row."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_a_scene_the_walk_calls_dropping_has_its_sets_in_the_table(self):
        import pirateforce_foundation.field_drop_tables as tables

        walked = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        self.assertIn(SCENE_THREE, tables.SCENES)
        for row in walked.rows:
            self.assertTrue(row.drop, row.placement_index)
            self.assertGreater(row.seeds_that_dropped, 0, row.placement_index)

    def test_the_walk_places_rows_through_the_cell_and_not_beside_it(self):
        """A placed row carries the scene it fell in, or it is not a row.

        ``GroundDrop.scene`` is the field the publication filter reads, so a
        walk that placed rows without a scene would report a door open on
        objects no player standing there could ever be shown.
        """
        import random

        roster = field_mobs.load_roster(scene=SCENE_THREE)
        mob = roster[0]
        cell = mob_loot.DropLedgerCell()
        cell.enter_scene(SCENE_THREE)
        step = mob_combat.strike(
            self.legacy, None, mob_combat.open_ledger((mob,)), None, mob,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        death = mob_death.kill(
            self.legacy, mob, step.outcome,
            widened=mob_death.ruling_for(mob))
        placed = ()
        for seed in scene_door_walk.DROP_SEEDS:
            roll = mob_loot.roll_drops(mob, random.Random(seed))
            placed = cell.loot_a_kill(
                mob, death.record, roll,
                kill_token=death.register.generation, position=None)
            if placed:
                break
            death = mob_death.kill(
                self.legacy, mob, step.outcome,
                widened=mob_death.ruling_for(mob))
        self.assertTrue(placed)
        for row in placed:
            self.assertIs(type(row), mob_loot.GroundDrop)
            self.assertEqual(row.scene, SCENE_THREE)


if __name__ == "__main__":
    unittest.main()
