"""LANE-CS: the damage number a player SEES when hitting the lane's standard
test dummy, Training Iron Man (template 916).

WHY THIS MODULE EXISTS.  LANE-CS's own charter names Training Iron Man as the
lane's standard proving ground: every damage claim is measured against that
dummy before a real monster.  Until 2026-09-07 nobody had watched a damage
number land on it.  `GT-274` changed that: in the attended run R322C
(pf_bridge/notes_to_chief/20260907_0158_KA1A-R322C-RESULTS-GT274-PASS-mace-
284-GT178-NEGATIVE-no-ai-tick-scene14.md, `OBSERVER_CONFIRMED
2026-09-07T01:48+07:00`) a freshly created Paladin hit the town's Training
Iron Man four times, the owner photographed **891** on screen, and the server
console printed `damage announced -891, applied 891` with the dummy's HP
moving 192779 -> 189215.  Two independent layers, one number.

    That pair -- a number on a screen and the same number on the wire -- is
    the only thing that makes a damage formula more than arithmetic, and it
    is what this module pins.  `mob_combat.py` already carries one such pin
    (`pin_attacker`/`pin_subject`, the GT-035 ladder).  This is the SECOND
    watched ladder, on a different actor, and it is the first one on the
    dummy this lane actually tests against.

NO NEW ARITHMETIC, NO RE-TYPED CONSTANT.  Every number below that takes part
in the calculation comes from somewhere else and is imported, never copied:
the defender record is built by `mob_combat.mob_defender` from the roster row
`field_mobs.load_roster()` ships for template `field_mobs.TOWN_TARGET_N_ID`
(that function is also what production uses, so this module cannot drift from
it), and the subtraction is `mob_combat.resolve_damage` itself.  The only
literals this file defines are the four OBSERVED values from the letter named
above -- what the owner saw, not what the code computes -- so that the two can
be compared instead of one being derived from the other.  If a later round
changes `ATK_BASE`, `K_ATK_STR`, `K_ATK_LV`, `DEF_BASE`, `K_DEF_CON`,
`K_DEF_LV`, `MOB_ABILITY_CON`, or the dummy's mined level, the pin in
`tests/test_damage_town_target.py` goes red and says the player-visible number
moved.  That is the whole point.

WHAT THE MEASUREMENT DOES **NOT** SAY -- and this is the finding, not a
footnote.  891 does not depend on the character who swung.  Running the
arithmetic backwards from the watched number lands on level 7 / STR 132 --
`mob_combat.PIN_ATTACKER_LEVEL` and `mob_combat.PIN_ATTACKER_ABILITY_STR`,
i.e. `runtime.MOB_COMBAT_DEFAULT_ATTACKER` -- and NOT on the level-1 Paladin
the owner was actually playing.  `runtime.py`'s own comment above that
constant already says every player currently deals the same damage; R322C is
the first time that consequence was watched on a screen, on a named actor,
with the arithmetic closing to the digit.  So:

  - The class DOES change what the player sees happen (`GT-274` PASS: sword
    for Gladiator, mace for Paladin -- `POSE_PRODUCTION class=1 ... base=2
    behavior=280` vs `class=2 ... base=3 behavior=284`).
  - The class does NOT change the number.  `mob_combat.Combatant` has no
    class field and no skill field, so there is no place for it to enter --
    `tests/test_damage_town_target.py` asserts that structurally rather than
    leaving it as prose.

Closing that gap is not this module's job and not this lane's to close alone:
the attacker record is built in `runtime.py`, which is chief's write zone and
needs its own `CORE-REQUEST`.  This module gives that request a number to
argue with instead of an opinion.

NONCLAIMS.
  - Does not claim the formula is the client's.  It is the server's own
    frozen formula (`mob_combat.py`'s docstring carries its provenance); what
    R322C proves is that the server's number reaches the player's screen
    unchanged, not that the client would have computed the same one.
  - Does not claim anything about a weapon.  The Paladin in R322C was
    unarmed; step 3 of `GT-274` (equip, then hit again) was NOT run because
    `GT-272` has not passed.  Nothing here says what an equipped character
    does.
  - Does not claim a skill was involved.  The four hits were the bare-hit
    path (`mob_combat.attack_from_observed_action`, LANE-B's), which reads no
    skill id at all -- see `damage_by_skill.py`'s docstring for that split.
  - Does not move `production_allowed` for anything, and touches no module
    outside LANE-CS's write zone.
"""

from __future__ import annotations

from . import field_mobs
from . import mob_combat
from .mob_combat import Combatant


class TownTargetDamageError(RuntimeError):
    """Raised when the shipped roster no longer carries the practice dummy."""


# ---------------------------------------------------------------------------
# The four numbers a human watched.  Provenance: R322C results letter named in
# the module docstring, GT-274 PASS, OBSERVER_CONFIRMED 2026-09-07T01:48+07:00.
# These are OBSERVATIONS.  Nothing in this module computes from them.
# ---------------------------------------------------------------------------
R322C_OBSERVED_DAMAGE_PER_HIT = 891
R322C_OBSERVED_HITS = 4
R322C_OBSERVED_HP_BEFORE = 192779
R322C_OBSERVED_HP_AFTER = 189215


def town_target_mob() -> field_mobs.FieldMob:
    """The shipped Training Iron Man row, out of the default (town) roster.

    The town ships FOUR of these dummies, not one -- a first draft of this
    function refused on that and was wrong to.  What the damage number
    actually needs from the row is its level, and what the ladder needs is
    its max HP; the owner hit whichever one was nearest and the letter does
    not record which placement that was.  So this refuses on the thing that
    would really make the pin ambiguous -- the four rows disagreeing about
    level or max HP -- and otherwise returns the lowest placement index,
    which is a stable choice rather than roster order.

    Refuses by name when the roster ships none of them at all: "the dummy
    this lane measures against" stops meaning anything the moment it is gone.
    """
    matches = sorted(
        (mob for mob in field_mobs.load_roster()
         if mob.template_id == field_mobs.TOWN_TARGET_N_ID),
        key=lambda mob: mob.placement_index,
    )
    if not matches:
        raise TownTargetDamageError(
            "the default roster ships no row for template %d (%s); this "
            "lane's standard test dummy is gone"
            % (field_mobs.TOWN_TARGET_N_ID, field_mobs.TOWN_TARGET_NAME))
    shapes = {(mob.level, mob.max_hp) for mob in matches}
    if len(shapes) != 1:
        raise TownTargetDamageError(
            "the %d shipped rows for template %d disagree about level/max HP "
            "(%s); there is no single dummy to measure against"
            % (len(matches), field_mobs.TOWN_TARGET_N_ID, sorted(shapes)))
    return matches[0]


def town_target_defender() -> Combatant:
    """The defender record production builds for that row -- not a copy of it.

    Deliberately goes through `mob_combat.mob_defender` instead of assembling
    a `Combatant` here: that function is what the live hit path uses, so a
    change to how a monster's defence record is built cannot pass this module
    by.
    """
    return mob_combat.mob_defender(town_target_mob())


def on_screen_damage(attacker: Combatant) -> int:
    """What one hit from ``attacker`` prints on the player's screen.

    The name is the claim R322C earned: for this actor, on that date, the
    number this returns is the number the owner photographed.
    """
    return mob_combat.resolve_damage(attacker, town_target_defender())


def hp_after_hits(attacker: Combatant, hp_before: int, hits: int) -> int:
    """The dummy's HP after ``hits`` uninterrupted hits, floored at zero.

    Written as the trace R322C actually recorded (192779 -> 189215 over four
    hits) so the pin can check the ladder, not just one subtraction.
    """
    if type(hits) is not int or type(hits) is bool or hits < 0:
        raise TownTargetDamageError("hits must be a non-negative int")
    if type(hp_before) is not int or type(hp_before) is bool or hp_before < 0:
        raise TownTargetDamageError("hp_before must be a non-negative int")
    return max(0, hp_before - hits * on_screen_damage(attacker))
