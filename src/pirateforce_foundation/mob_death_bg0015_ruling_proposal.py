"""LANE-B / COO-DECISION 2026-09-01T08:47+07:00 item (b): replay the
methodology that produced bg0001's and Bg0002's death rulings against
Bg0015's own 7 unruled templates, and hand back OPTIONS -- not a ruling.

WHY THIS MODULE EXISTS AND WHAT IT DOES NOT DO.  ``mob_death.WIDENING_RULINGS``
is a dict this project's own rules say only the owner/COO may add an entry
to, by the ruling's exact quoted name (see that dict's own docstring: "there
is no leniency fallback for a ruling not yet catalogued").  This module adds
NO entry there and imports nothing that would let it.  It only re-derives the
DATA a ruling would need to be correct, the same way
``mob_combat_bg0015_gates.templates_without_a_death_ruling`` already
re-derives which templates are refused, so that the COO's decision is made
against measured numbers instead of a hand-typed guess.

THE METHODOLOGY, READ BACK OUT OF THE CODE THAT ALREADY SHIPPED IT (bg0001,
``COO-RULING-20260827-1350``; Bg0002, ``PANYA-DECISION 2026-08-27T20:10
+07:00``), rather than assumed:

  1. A letter from the owner or COO names either specific MOBS template ids,
     or "the roster" -- and when it names the roster, the covered set in
     ``mob_death.WIDENING_RULINGS`` is RE-DERIVED from the scene's own mined
     table in a test (``tests/test_mob_death.py``'s
     ``test_the_bg0002_ruling_covers_exactly_the_real_bg0002_rosters_
     templates``), never hand-copied from the census block the letter itself
     describes.
  2. The technical narrowing (which placements even get to be candidates) is
     ALREADY DONE by the mining tool before any letter is asked for: a row
     needs a rank AND a combat AI (the hostility predicate), AND its outfit
     must be a single unambiguous string, not a ";"-joined variant list.  A
     row that fails the outfit rule never reaches ``HOSTILE_PLACEMENTS`` at
     all -- it is recorded in ``UNRESOLVED_PLACEMENTS`` /
     ``WITHDRAWN_UNDER_THIS_RULE`` instead.  Bg0002's ruling comment is
     explicit that templates 27/28/29/30/32/33 are excluded from its covered
     set for exactly this reason, not because anyone read them and decided
     against them by hand.
  3. The ruling's NAME is additionally tied to one scene string in
     ``mob_death.WIDENING_RULING_SCENES``, so a template id shared by two
     scenes' rosters cannot be authorised in the wrong one
     (``test_a_bg0002_mob_is_refused_the_bg0001_ruling_despite_a_shared_
     template`` and its mirror test this scene check).
  4. A body that step 2's own technical rule would otherwise have EXCLUDED
     from the roster, but that a DIFFERENT process places in the scene
     anyway (Bg0002's Mountain Deer / template 27, placed by the GT-114
     diagnostic objects, not by the mined roster), gets its OWN separate
     ruling rather than being folded into the roster's.

WHERE THE REPLAY STOPS BEING MECHANICAL.  Steps 1-3 generalise cleanly to
Bg0015 and this module carries out the code side of all three (see
:func:`full_roster_template_ids`, :func:`overlaps_with_registered_rulings`).
Step 4 does NOT generalise to Bg0015's one open case (:data:`CARLOS_TEMPLATE_
ID`, MOBS 924 "Carlos"): Carlos is not excluded by step 2's technical rule --
its outfit (``P_MALE_033_000_CARLOS``) is a single, unambiguous string, so
the mining tool ships it in ``HOSTILE_PLACEMENTS`` exactly like the other six
templates, on the SAME predicate.  The only thing that makes Carlos different
is content the mining tool cannot see at all: a ``MOBS_TIP`` title and NPC
chat lines, flagged as an open, unanswered question by TWO earlier letters
(``pf_bridge/notes_to_chief/20260829_0739_LANE-A-STATUS-lane-B-edit-
confirmed-and-carlos-is-your-call.md`` item 4, and this lane's own
``scene_identity_rule.py`` module docstring, point 8: "It may well be a real
boss; nobody has looked.").  Mountain Deer's carve-out is therefore NOT a
precedent for carving Carlos out on the same GROUNDS -- it is a precedent for
carving out a body the mining tool's own rule rejects, and Carlos is not one
of those.  Replaying the OLD methodology by itself does not answer whether
Carlos should get the same treatment; that is a new content question, named
here as a fact rather than guessed at.

WHAT THIS MODULE MEASURES ABOUT THE ONE MECHANICAL DIFFERENCE THAT DOES
EXIST WITHIN BG0015'S OWN TWELVE ROWS: six of the seven templates ship an
outfit prefixed ``M0`` (a monster-model body); Carlos alone is prefixed
``P_`` (a player-model body) -- see :func:`player_body_template_ids`.  THIS
IS NOT OFFERED AS A GENERAL RULE ("P_-prefixed outfits are never monsters"):
this project already ships killable P_-prefixed bodies elsewhere (Navy
soldiers, ``scene2_prison_exile_tables.HOSTILE_PLACEMENTS``-shaped rows carry
``P_MALE_002_000_SP1``), and several probe-lane anchors use the exact same
outfit string for a body nobody claims is a person.  It is offered only as a
narrow, checkable FACT about Bg0015's specific twelve rows: within this one
roster, the prefix split is exact and lines up with the one row two lanes
already flagged by name.

THREE OPTIONS, NOT A RECOMMENDATION FORCED PAST WHAT IS MEASURED.  COO's
letter asks for "at most 2-3 options if the answer isn't clean" -- it isn't:
:func:`option_a_full_roster`, :func:`option_b_roster_minus_carlos` and
:func:`option_c_defer_the_whole_roster` are the three, and this lane's own
reading of which is weakest is written on :func:`option_c_defer_the_whole_
roster`'s own docstring, labelled as this lane's assumption, not as data.

WHAT IS STILL CLOSED AFTER THIS MODULE EXISTS.  Nothing:
``mob_death.WIDENING_RULINGS`` carries no new entry, ``mob_combat_bg0015_
gates.templates_without_a_death_ruling()`` still refuses all seven, and
``field_mobs._SCENE_TABLE_MODULES`` is untouched (gate 1, COO-DECISION
2026-09-01T08:47+07:00 item (c), stays locked pending item (b)'s answer).  A
player sees nothing different because this file exists.
"""

from __future__ import annotations

from . import field_mob_hostile_bg0015
from . import mob_death

# Convention markers only; nothing in this tree branches on them (same
# convention mob_combat_bg0015_gates.py and field_mob_hostile_bg0015.py use).
production_allowed = True
test_only = False

#: MOBS 924, "Carlos" -- the one row this module's analysis singles out.
#: Named as a constant rather than a bare literal so a caller filtering it
#: out (:func:`option_b_roster_minus_carlos`) reads as intentional, not as an
#: unexplained magic number.
CARLOS_TEMPLATE_ID = 924

#: The outfit-string prefix this module's narrow, roster-scoped fact keys on.
#: See the module docstring's "WHAT THIS MODULE MEASURES" section for why
#: this is NOT claimed to generalise past Bg0015's own twelve rows.
_PLAYER_BODY_OUTFIT_PREFIX = "P_"


class MobDeathBg0015ProposalError(ValueError):
    """A refusal from this module, always with a reason in the message."""


def full_roster_template_ids() -> tuple[int, ...]:
    """Distinct MOBS template ids Bg0015's own mined hostile roster ships,
    ascending -- re-derived from the same row parser every live scene's
    roster goes through (:func:`field_mob_hostile_bg0015.scene14_hostile_
    roster`), never hand-copied from the table module's own literal rows.

    This is the shape step 1 of the methodology needs when a letter names
    "the roster" rather than an explicit id list, and it is also exactly
    what ``mob_combat_bg0015_gates.templates_without_a_death_ruling()``
    reports today as refused -- ``tests/test_mob_death_bg0015_ruling_
    proposal.py`` cross-checks the two are the same tuple by execution
    rather than asserting it once and trusting it stays true.
    """
    return tuple(sorted({
        mob.template_id
        for mob in field_mob_hostile_bg0015.scene14_hostile_roster()
    }))


def _template_outfits() -> dict[int, str]:
    """``{template_id: the one outfit string every placement of it ships}``.

    Fails closed rather than picking one arbitrarily: if a future data
    change ever ships two DIFFERENT outfits under one template id in this
    roster, the split this module reports would silently become wrong, so
    this refuses instead of guessing which outfit "counts".
    """
    outfits: dict[int, set[str]] = {}
    for mob in field_mob_hostile_bg0015.scene14_hostile_roster():
        outfits.setdefault(mob.template_id, set()).add(mob.visual_preset)
    disagreeing = {
        template_id: sorted(seen)
        for template_id, seen in outfits.items() if len(seen) != 1
    }
    if disagreeing:
        raise MobDeathBg0015ProposalError(
            "template id(s) ship more than one outfit string in Bg0015's "
            "own hostile roster, so 'the outfit for this template' is not "
            "a well-defined question: %r" % (disagreeing,))
    return {
        template_id: next(iter(seen)) for template_id, seen in outfits.items()
    }


def player_body_template_ids() -> tuple[int, ...]:
    """Which of :func:`full_roster_template_ids` ship a player-model outfit
    (prefix ``P_``) rather than a monster-model one (prefix ``M0``, every
    other row Bg0015 ships) -- ``(924,)`` at HEAD, i.e. Carlos alone.

    Narrow and roster-scoped on purpose; see the module docstring for why
    this is not offered as a rule that would hold outside Bg0015's own
    twelve rows.
    """
    outfits = _template_outfits()
    return tuple(sorted(
        template_id for template_id, outfit in outfits.items()
        if outfit.startswith(_PLAYER_BODY_OUTFIT_PREFIX)
    ))


def overlaps_with_registered_rulings() -> frozenset[int]:
    """Intersection of Bg0015's 7 candidate templates with every template id
    ANY currently-registered ``mob_death.WIDENING_RULINGS`` entry already
    covers -- measured, not assumed from ``field_mobs.py``'s own comment
    that the two overlap on nothing.  Empty at HEAD.

    This answers only the TEMPLATE axis.  It says nothing about
    ``WIDENING_RULING_SCENES`` (whether a shared template id would also
    need to share a scene to collide) because there is nothing to say: an
    empty intersection here means the scene axis is never even reached for
    Bg0015's candidates against today's registered rulings.
    """
    candidates = set(full_roster_template_ids())
    covered: set[int] = set()
    for templates in mob_death.WIDENING_RULINGS.values():
        covered |= templates
    return frozenset(candidates & covered)


def option_a_full_roster() -> tuple[int, ...]:
    """OPTION A -- one ruling naming every template Bg0015's own hostility
    predicate already selected, mirroring bg0001 ("all N real MOBS-table
    field mobs in bg0001") and Bg0002 ("its own hostile roster") exactly:
    no carve-out, Carlos included.  This is the mechanical, no-new-judgement
    replay of steps 1-3 of the methodology.
    """
    return full_roster_template_ids()


def option_b_roster_minus_carlos() -> tuple[int, ...]:
    """OPTION B -- the same ruling, minus Carlos, held back pending a
    separate answer to whether a named, dialogue-bearing body should be
    killable at all.

    STRUCTURALLY the same SHAPE as Mountain Deer's carve-out from Bg0002's
    ruling (one template named separately rather than folded into the
    roster's).  NOT the same REASON: Mountain Deer was carved out because
    it fails the mining tool's own outfit-unambiguous rule -- a fact about
    the DATA.  Carlos passes that same rule; the only reason to hold it back
    is a content judgement the methodology has no prior instance of making.
    Offered because two prior letters already flagged Carlos as open and
    unanswered, not because replaying the old methodology produces it on
    its own.
    """
    carlos = frozenset(player_body_template_ids())
    return tuple(
        template_id for template_id in full_roster_template_ids()
        if template_id not in carlos
    )


def option_c_defer_the_whole_roster() -> tuple[int, ...]:
    """OPTION C -- rule on none of the seven yet.

    [ASSUMPTION OF LANE B - AWAITING COO] Offered only because COO's letter
    asks for options, not because this lane thinks it is the right call:
    six of the seven templates carry no open content question at all (see
    :func:`player_body_template_ids`, which names exactly one), so deferring
    all seven withholds a ruling from six templates the methodology answers
    the same way bg0001's and Bg0002's letters already did.
    """
    return ()
