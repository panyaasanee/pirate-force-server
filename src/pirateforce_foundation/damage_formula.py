"""LANE-CS: one door for the damage arithmetic, and the committed table that
says which attacker numbers a level can even carry.

WHY THIS MODULE EXISTS.  This lane's charter names two jobs that have never
been in one place: "own the damage formula" and "check the numbers against the
committed tables".  The formula half already had a home -- ``mob_combat.py``,
LANE-B's, where ``Combatant.attack``/``Combatant.defence`` and
``resolve_damage`` live -- and this lane's own ``damage_by_skill.py`` refused
in as many words to make "a FOURTH copy of ``ATK_BASE``/``K_ATK_STR``/etc".
This module holds that line and adds the half nobody had written: the
arithmetic that says whether an attacker profile's ``ability_str`` is a number
the client's own committed progression table can account for at that level.

THIS FILE TYPES NO CONSTANT OF THE FORMULA.  Everything the formula needs is
imported from ``mob_combat`` and re-exported, so a caller of this lane's damage
door never imports ``mob_combat`` itself and there is no second place for the
numbers to drift to.  ``tests/test_damage_formula.py`` pins that twice: once by
scanning this file's own AST for an assignment to any formula name (there is
none), and once across the whole tree -- five modules type a full copy of
``ATK_BASE`` and its neighbours today (measured with ``ast``, not with the grep
for those names, which returns nine files because four of them only mention
them in prose or import them), and the test goes red the day one stops agreeing
with ``mob_combat``.  That is a drift detector, not a refactor: this lane does
not edit LANE-B's module or the two hypothesis lanes that copy it.

WHAT THE TABLE ACTUALLY SAYS, AND WHAT IT DOES NOT.
``data/standard_status.tsv`` is the client's own CONSTDATA table, 255 rows,
already committed and already parsed by one module in LANE-DB's write zone.
Its ``n_POINT_ABILITY`` column is the ability points a character is granted for
reaching that level.  Summed from level 1 up, it is an upper bound on how far
any ONE ability can have been raised by levelling: put every point granted so
far into strength and you get :meth:`AbilityPointTable.granted_through`.

    THE TABLE IS HANDED IN, NOT IMPORTED, AND THAT IS AN ORDER RATHER THAN A
    TASTE.  The module that parses that table carries its OWNER's declaration
    of who may call it -- a pin over ``src/``, ``tools/``, ``current/``,
    ``migrations/`` and ``scenarios/`` that lists the callers by name and goes
    red on a second lane wiring itself in.  ``COO-ORDER 20260907_2050`` settled
    what a caller does about that: the owner retires the pin in the owner's own
    ticket, and until then THE CALLER WITHDRAWS.  This lane already learnt that
    the expensive way in round ``hhmvit``, by allowlisting a name inside
    someone else's pin and being told to take it back out.  So this module
    never imports it, never names it (the pin is a text scan, and a mention
    would keep it red for a comment), and takes an :class:`AbilityPointTable`
    from its caller instead.  ``tests/`` is outside that scan by design, so the
    tie between this arithmetic and the REAL committed rows lives there, where
    it can be made without touching another lane's declaration.  A letter to
    LANE-DB filed in the same round asks for the declaration; the day it lands,
    a caller can build the table from the owner's own accessor in one line.

    IT IS A BOUND ON THE LEVELLING HALF ONLY, AND THE STARTING HALF IS NOT
    KNOWN.  A character does not start at zero in every ability, and this
    project cannot say what it starts at: ``RE-229`` closed the only question
    that would answer it as a bounded negative -- "no field or consumer
    anywhere in the committed corpus crosswalks ``CHARCREATE_CLASS.s_SCORE``'s
    six components to the five wire ``ActorAttr`` ability fields".  So
    :func:`ability_str_ceiling_at_level` REFUSES to guess: the caller states
    the starting value it is working from, and the function adds the table's
    grant to it.  A default here would be this project inventing a number and
    then quoting itself.

WHAT THIS MEASURES ABOUT THE ATTACKER EVERY PLAYER SWINGS AS TODAY.
``runtime.py`` hands every connection the same profile,
``mob_combat.pin_attacker()`` -- level 7, ability_str 132, the ladder GT-035
watched on a screen.  Run the table against it (:func:`describe_pinned_attacker`)
and the gap is not small: levelling from 1 to 7 grants six points on the
committed table, and the pin carries 132.  The
honest reading of that gap is NOT "the pin is wrong" -- it is that 132 is one
of this project's own numbers (``mob_combat``'s docstring says so: the original
server is unrecoverable and the arithmetic is ours), so it was never a sum of
this table's grants and does not become wrong by failing to be one.  What the
gap does buy is a refusal that can fire on a REAL character later: when
``store``'s character rows start carrying an ability score, a row claiming a
strength that no amount of levelling plus its own starting score could reach is
a corrupt row, and :func:`refuse_ability_str_above_ceiling` names it instead of
letting it swing.

NONCLAIMS, so no later round reads more into this file than it measured.
Nothing here has ever changed a number on a player's screen: this module has no
caller in ``src/`` (the ``runtime.py`` seam is chief's CORE-REQUEST, filed
2026-09-07T21:35+07:00, and is not edited here).  It does not claim
``n_POINT_ABILITY`` is spent on strength, or spent at all -- only that it
bounds what levelling can add.  It does not claim the starting ability scores
are recoverable, and it does not read ``s_SCORE``.  It does not touch monster
defence: ``n_DEFENCE_CONSTANT`` sits in the same committed row and is
deliberately left alone, because the defender half is LANE-B's and that lane
has an open, written decision to defer it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .mob_combat import (
    ATK_BASE,
    Combatant,
    DEF_BASE,
    K_ATK_LV,
    K_ATK_STR,
    K_DEF_CON,
    K_DEF_LV,
    MIN_HIT,
    PIN_ATTACKER_ABILITY_STR,
    PIN_ATTACKER_LEVEL,
    resolve_damage,
)
from typing import Mapping

__all__ = [
    "ATK_BASE",
    "Combatant",
    "DEF_BASE",
    "DamageFormulaError",
    "K_ATK_LV",
    "K_ATK_STR",
    "K_DEF_CON",
    "K_DEF_LV",
    "MIN_HIT",
    "REFUSE_ABILITY_STR_ABOVE_CEILING",
    "REFUSE_LEVEL_NOT_AN_INT",
    "REFUSE_LEVEL_OFF_TABLE",
    "REFUSE_STARTING_ABILITY_STR_INVALID",
    "AbilityPointTable",
    "AbilityStrVerdict",
    "REFUSE_TABLE_UNUSABLE",
    "ability_points_granted_through_level",
    "ability_str_ceiling_at_level",
    "attack_of",
    "damage_of",
    "defence_of",
    "describe_pinned_attacker",
    "headless_summary",
    "refuse_ability_str_above_ceiling",
    "verdict_for_ability_str",
]

#: Refusal reasons.  Each names the value that failed, never the caller: this
#: door is fail-closed, because the alternative -- silently clamping to the
#: table -- would hide exactly the corrupt row it exists to catch.
REFUSE_LEVEL_NOT_AN_INT = "level_is_not_an_int"
REFUSE_LEVEL_OFF_TABLE = "level_is_outside_the_committed_table"
REFUSE_STARTING_ABILITY_STR_INVALID = "starting_ability_str_is_not_a_count"
REFUSE_ABILITY_STR_ABOVE_CEILING = "ability_str_is_above_what_the_table_grants"
REFUSE_TABLE_UNUSABLE = "the_ability_point_table_cannot_be_summed"


class DamageFormulaError(ValueError):
    """A refusal from this door.  ``args[0]`` is one of the reasons above."""


class AbilityPointTable:
    """The ``n_POINT_ABILITY`` column, handed in by whoever owns the file.

    A caller builds one from the committed rows (see the module docstring for
    why this module does not read them itself).  The constructor is strict on
    purpose: a table with a hole in it silently turns every ceiling below the
    hole into an under-count, and an under-count REFUSES a character that was
    fine -- the expensive direction.
    """

    def __init__(self, points_by_level: Mapping[int, int]) -> None:
        levels = sorted(points_by_level)
        if not levels:
            raise DamageFormulaError(
                REFUSE_TABLE_UNUSABLE, "the ability-point table is empty"
            )
        if levels[0] != 1:
            raise DamageFormulaError(
                REFUSE_TABLE_UNUSABLE,
                "the table starts at level %d, not 1" % levels[0],
            )
        if levels != list(range(1, levels[-1] + 1)):
            missing = sorted(set(range(1, levels[-1] + 1)) - set(levels))
            raise DamageFormulaError(
                REFUSE_TABLE_UNUSABLE,
                "the table has holes at %s; a running sum over it would "
                "under-count every level above the first hole" % (missing[:8],),
            )
        running = 0
        cumulative = {}
        for level in levels:
            points = points_by_level[level]
            if isinstance(points, bool) or not isinstance(points, int) or points < 0:
                raise DamageFormulaError(
                    REFUSE_TABLE_UNUSABLE,
                    "level %d grants %r, which is not a count" % (level, points),
                )
            running += points
            cumulative[level] = running
        self._cumulative = cumulative
        self.first_level = levels[0]
        self.last_level = levels[-1]

    def granted_through(self, level: int) -> int:
        """Ability points granted on the way to ``level``, inclusive."""
        return self._cumulative[_require_level(self, level)]

    def __len__(self) -> int:
        return len(self._cumulative)


def _require_level(table: AbilityPointTable, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DamageFormulaError(
            REFUSE_LEVEL_NOT_AN_INT,
            "level must be an int, got %r" % (type(value).__name__,),
        )
    if not table.first_level <= value <= table.last_level:
        raise DamageFormulaError(
            REFUSE_LEVEL_OFF_TABLE,
            "level %d is outside the table's %d..%d"
            % (value, table.first_level, table.last_level),
        )
    return value


def _require_count(value: object, reason: str, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DamageFormulaError(
            reason, "%s must be an int >= 0, got %r" % (what, value)
        )
    return value


def ability_points_granted_through_level(
    table: AbilityPointTable, level: int
) -> int:
    """Ability points a character has been granted on reaching ``level``.

    The running sum of the table's per-level grants.  Level 1 carries 0 in the
    committed rows -- levelling has not happened yet -- so a level-1 character
    is granted nothing here and whatever strength it has came from its starting
    scores.
    """
    return table.granted_through(level)


def ability_str_ceiling_at_level(
    table: AbilityPointTable, level: int, *, starting_ability_str: int
) -> int:
    """The largest ``ability_str`` ``level`` can account for.

    ``starting_ability_str`` is the caller's, not this module's: see the
    docstring above on ``RE-229``.  The ceiling is the pessimistic one -- every
    point the table has granted, poured into strength alone.
    """
    start = _require_count(
        starting_ability_str,
        REFUSE_STARTING_ABILITY_STR_INVALID,
        "starting_ability_str",
    )
    return start + table.granted_through(level)


@dataclass(frozen=True)
class AbilityStrVerdict:
    """What the table says about one (level, ability_str) pair."""

    level: int
    ability_str: int
    starting_ability_str: int
    granted_points: int
    ceiling: int

    @property
    def within_the_table(self) -> bool:
        return self.ability_str <= self.ceiling

    @property
    def unaccounted_for(self) -> int:
        """How far past the ceiling the value sits.  0 when it is within."""
        return max(0, self.ability_str - self.ceiling)


def verdict_for_ability_str(
    table: AbilityPointTable,
    level: int,
    ability_str: int,
    *,
    starting_ability_str: int,
) -> AbilityStrVerdict:
    """Measure a pair against the table.  Never raises on the verdict itself.

    Refuses only inputs the table cannot be asked about (an off-table level, a
    negative count).  A strength ABOVE the ceiling is a finding, not an error
    -- see :func:`refuse_ability_str_above_ceiling` for the fail-closed door.
    """
    checked_level = _require_level(table, level)
    value = _require_count(
        ability_str, REFUSE_STARTING_ABILITY_STR_INVALID, "ability_str"
    )
    ceiling = ability_str_ceiling_at_level(
        table, checked_level, starting_ability_str=starting_ability_str
    )
    return AbilityStrVerdict(
        level=checked_level,
        ability_str=value,
        starting_ability_str=starting_ability_str,
        granted_points=table.granted_through(checked_level),
        ceiling=ceiling,
    )


def refuse_ability_str_above_ceiling(
    table: AbilityPointTable,
    level: int,
    ability_str: int,
    *,
    starting_ability_str: int,
) -> AbilityStrVerdict:
    """The fail-closed form: raise when the pair is not accountable.

    For the day a character row carries a real ability score.  Nothing in
    ``src/`` calls it today, and that is stated rather than implied.
    """
    verdict = verdict_for_ability_str(
        table, level, ability_str, starting_ability_str=starting_ability_str
    )
    if not verdict.within_the_table:
        raise DamageFormulaError(
            REFUSE_ABILITY_STR_ABOVE_CEILING,
            "ability_str %d at level %d is %d above the ceiling %d "
            "(starting %d + %d granted)"
            % (
                verdict.ability_str,
                verdict.level,
                verdict.unaccounted_for,
                verdict.ceiling,
                verdict.starting_ability_str,
                verdict.granted_points,
            ),
        )
    return verdict


def describe_pinned_attacker(table: AbilityPointTable) -> AbilityStrVerdict:
    """The profile every player swings as today, measured against the table.

    Its ``unaccounted_for`` is large on purpose: 132 is one of this project's
    own numbers, not a sum of this table's grants.  The verdict records the
    gap so a later round reads a measurement instead of an assumption.
    """
    return verdict_for_ability_str(
        table,
        PIN_ATTACKER_LEVEL,
        PIN_ATTACKER_ABILITY_STR,
        starting_ability_str=0,
    )


def attack_of(combatant: Combatant) -> int:
    """The attacker half of the formula, through the one door."""
    return combatant.attack


def defence_of(combatant: Combatant) -> int:
    """The defender half of the formula, through the one door."""
    return combatant.defence


def damage_of(attacker: Combatant, defender: Combatant) -> int:
    """One hit, unclamped by the target's remaining HP.

    Exactly ``mob_combat.resolve_damage``.  It is re-exported rather than
    reimplemented so that "one formula, many callers" is a fact about the
    import graph rather than a promise in a docstring.
    """
    return resolve_damage(attacker, defender)


def headless_summary(table: AbilityPointTable) -> str:
    """One ASCII line for a console that is cp874.  No characters above 0x7F.

    Takes the table for the same reason everything else here does.  The command
    that produces it therefore names the owning module at the CALL SITE, which
    is where a caller belongs, rather than inside this file:

        PYTHONPATH=src python3 -c "import pirateforce_foundation.damage_formula \
            as d, pirateforce_foundation.<owner> as t; \
            print(d.headless_summary(d.AbilityPointTable({l: \
            t.standard_status_row(l).point_ability for l in range(1, 256)})))"
    """
    verdict = describe_pinned_attacker(table)
    return (
        "DAMAGE_FORMULA table_levels=%d..%d pinned_level=%d "
        "granted_points=%d pinned_ability_str=%d ceiling_from_zero=%d "
        "unaccounted=%d"
        % (
            table.first_level,
            table.last_level,
            verdict.level,
            verdict.granted_points,
            verdict.ability_str,
            verdict.ceiling,
            verdict.unaccounted_for,
        )
    )
