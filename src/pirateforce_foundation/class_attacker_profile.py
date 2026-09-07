"""LANE-CS: the attacker profile of a REAL character -- the one place that
answers "what does THIS player's character swing as", instead of the single
pinned dummy every player currently swings as.

WHAT IS BROKEN TODAY, IN ONE LINE.  `runtime.py` builds ONE attacker profile
at import time (`MOB_COMBAT_DEFAULT_ATTACKER = mob_combat.pin_attacker()`)
and hands that same object to `mob_combat.attack_from_observed_action` for
every connection.  Its own comment says why, word for word: "[PROPOSED, not
measured] ... This project has no character battle-stat source anywhere --
`model.Position` carries an identity and an xyz and nothing else, so there is
no real per-player level or STR to read.  Until one exists, every attacker
this branch drives is given the ONE profile this project has ever watched
land on a real screen (HYP-PF-038 / GT-035's "MOB_WEAK" ladder, level 7 /
STR 132)".  The visible consequence is stated there too: "every player
currently deals the same damage numbers GT-035 already published".

    THAT PREMISE IS NO LONGER TRUE, AND THIS MODULE IS THE EVIDENCE.  A
    per-character battle-stat source DOES exist now, on `main`, in LANE-DB's
    territory: `migrations/006_character_typed_attribute_columns.sql` adds
    `characters.level` and `characters.class_id`, `migrations/
    009_character_birth_defaults.sql` gives `level` a `DEFAULT 1` (that
    file's own opening line says FOUR columns carry a DEFAULT -- `level`,
    `hp_current`, `hp_max`, `speed_walk`; an earlier draft here said "three",
    which is 009's count of a different list -- pf-adversary D11), and
    `store.py` already ships
    both reading doors -- `read_typed_attributes` (level) and
    `read_class_id_by_identity` ("`class_id` of the ACTIVE character carrying
    this wire identity").  Nothing in this module writes, migrates, or
    reaches into `store.py`; it takes the two values those doors already
    return and turns them into the record `mob_combat` asks for.

WHAT THIS MODULE IS NOT.  It is NOT a fourth copy of the damage formula.
`damage_by_skill.py`'s docstring already refused that ("there is no excuse
for a FOURTH copy of `ATK_BASE`/`K_ATK_STR`/etc") and this module holds that
line harder: it does not compute a damage number at all.  It builds a
`mob_combat.Combatant` -- the record whose `attack` property IS the formula,
owned by `mob_combat.py` -- and every constant it needs is imported from
there rather than restated.

    PRECISELY WHAT `class_id` DOES AND DOES NOT DO (pf-adversary D8).  It is
    a GATE, never an input to the record: two characters of different classes
    at the same level get IDENTICAL numbers out of this module, and the
    five-line headless block below is five labels over one number, not a
    per-class measurement.  The class decides WHETHER this module answers;
    the level decides WHAT it answers.  It is also NOT a wiring change: `runtime.py` is
outside this lane's write zone -- `prompts/LANE-CS.md` names `runtime.py`,
`app.py`, `store.py` and `gm/` as seams, one CORE-REQUEST per seam.  That
clause is an ENGLISH RENDERING of a Thai line, not a quotation of it; an
earlier draft presented it inside quote marks (pf-adversary D3), which is the
same defect this lane was hit for in round `75udgf`.  So the one line that
would put this module on the live path is a CORE-REQUEST, filed in the same
round as this file, NOT edited here.

THE HONEST HALF: LEVEL IS REAL, ABILITY STR IS STILL PINNED.
`profile_for_character` derives `level` from the character's own persisted
row and refuses -- by name, fail-closed -- when that row cannot answer.  It
does NOT derive `ability_str` from the character's class, and it does not
pretend to: `RE-229` closed the only question that would allow it as
CLOSED BOUNDED-NEGATIVE (LANE-DB's committed progression-table scaffold
quotes the finding: "no field or consumer anywhere in the committed corpus crosswalks
`CHARCREATE_CLASS.s_SCORE`'s six components to the five wire `ActorAttr`
ability fields").  Until an RE ticket reopens that, STR stays the one value
this project has watched land on a screen, imported from `mob_combat`, and
the class id is used for what it CAN honestly be used for: refusing a row
whose class is not one of the five selectable classes, so a corrupt or
unseeded `class_id` cannot quietly swing as a valid character.

    NONCLAIM, stated so no later round can read more into this file than it
    measured: this module has NEVER been observed changing a number on a
    player's screen.  It has no caller in `src/` as of the round that added
    it (that is what the CORE-REQUEST is for), the level->damage consequence
    below is arithmetic over `mob_combat`'s own constants rather than an
    observation, and no attended run has yet hit anything with a profile
    built here.  `GT` ticket body for that measurement ships with this round.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import class_catalog
from . import mob_combat

# [LANE-CS -- import withdrawn on COO-DECISION 20260907_2050, not lost]
# Round `hhmvit` imported LANE-DB's committed progression-table scaffold here
# to ask the one
# question that module exists to answer: is this character's level a level the
# client's own committed progression table actually carries?  That import made
# that module's own `NoProductionCallerTests` -- LANE-DB's declaration that it
# is still a scaffold and not wiring -- go red,
# and round `hhmvit` answered by ALLOWLISTING one name inside that pin.  COO
# named that for what it was and forbade it: the pin belongs to its owner
# (LANE-DB), who retires it in a LANE-DB ticket, and until then the CALLER
# withdraws.  So the import is gone from this module and the allowlist entry is
# gone from LANE-DB's test in the same commit.
#
# The module's IDENTIFIER is deliberately not spelled anywhere in this file.
# That is not coyness: the guard this withdrawal restores greps this file for
# that literal string, so writing it in a comment would keep the pin red for a
# mention rather than a call, and the obvious "fix" for that would be a second
# allowlist.  Its own test file names it in full.
#
# WHAT IS KEPT, AND HOW (pf-adversary round `b2cnxe`, D5): the first draft of
# this withdrawal simply fell back to `Combatant`'s own 1..1000 range and wrote
# a label saying what was lost.  That threw away a check this house already
# knows how to keep without the import -- `gm/level_command.py` hit exactly
# this wall in round `l86bt4` and solved it: spell the table's last level as a
# LITERAL here, and tie that literal to the real table from `tests/`, a tree
# the pin's text scan does not read.  A literal with a test on it, never a
# literal on its own.  So `TABLE_LAST_LEVEL` below is the ceiling this module
# refuses above, and `tests/test_class_attacker_profile.py` turns red the day
# it stops being the committed table's last row.
#
# WHAT IS STILL LOST, STATED PLAINLY: the withdrawn check was a REAL ROW READ,
# so a level inside the span but missing from the table refused.  A ceiling is
# a range comparison and cannot do that.  Today the two agree because the
# committed table is contiguous 1..TABLE_LAST_LEVEL, and a test below pins that
# contiguity -- the day the table grows a hole, that test goes red and says so
# rather than letting this module quietly accept the hole.
# On the round LANE-DB's retirement lands on main, restoring the import is this
# lane's FIRST job (<=30 minutes, COO-DECISION 20260907_2050 item 4), together
# with mutant M2 (a range comparison in place of a real row read) going red again.

#: Refusal reasons.  Every one of them names the row, not the caller: this
#: module is fail-closed on purpose, because the alternative -- quietly
#: substituting the pinned dummy when a character row cannot answer -- is
#: exactly the bug this module exists to end, and it would be invisible.
REFUSE_LEVEL_NOT_AN_INT = "level_is_not_an_int"
#: [withdrawn with the import above] While the import is withdrawn this reason
#: no longer means "the committed table does not carry this level"; it means
#: only "outside the range the combatant record accepts".  The STRING is kept
#: byte-identical so a caller already branching on it does not break on a
#: change that is a temporary retreat, not a contract change.
REFUSE_LEVEL_OFF_TABLE = "level_is_outside_the_committed_table"
REFUSE_CLASS_ID_NOT_AN_INT = "class_id_is_not_an_int"
REFUSE_CLASS_ID_UNKNOWN = "class_id_is_not_a_selectable_class"
REFUSE_ABILITY_STR_NOT_AN_INT = "ability_str_is_not_an_int"
#: pf-adversary D4: `_require_int` only ever checked TYPE, so an in-type but
#: out-of-range STR fell through to `Combatant.__post_init__` and came back
#: as `mob_combat.MobCombatContractError` -- a DIFFERENT exception class than
#: the one this module's own docstring tells callers to branch on.  That is
#: not hypothetical: `migrations/006` bounds `stat_str` and `bonus_str` at
#: 65535 each, so the obvious "this character's STR" (their sum) reaches
#: 131070, over `Combatant`'s 100000 ceiling.
REFUSE_ABILITY_STR_OUT_OF_RANGE = "ability_str_is_outside_the_combatant_range"

#: The bounds `mob_combat.Combatant.__post_init__` enforces on `ability_str`,
#: restated here ONLY as the pair this module checks first so it can refuse in
#: its own currency.  Kept beside the constant it mirrors so a reader sees the
#: duplication; a test asserts the two still agree by walking `Combatant`.
ABILITY_STR_MIN = 0
ABILITY_STR_MAX = 100000

#: The bounds `mob_combat.Combatant.__post_init__` enforces on `level`, mirrored
#: for the same reason and with the same duplication warning as the pair above.
#: A test walks `Combatant` itself and turns red if either drifts (pf-adversary
#: round `b2cnxe` D6: the first draft mirrored these without extending that
#: test, so lowering `Combatant`'s ceiling leaked `MobCombatContractError` --
#: a DIFFERENT class than this module's docstring tells a caller to branch on,
#: which is pf-adversary D4 of round `hhmvit` reopened).
COMBATANT_LEVEL_MIN = 1
COMBATANT_LEVEL_MAX = 1000

#: The FIRST and LAST level the client's committed progression table carries,
#: spelled here as literals instead of imported, for the reason the block at the
#: top of this file gives.  `tests/test_class_attacker_profile.py` reads the real
#: table and turns red if either stops matching it -- the `gm/level_command.py`
#: recipe, not an invention of this round.
TABLE_FIRST_LEVEL = 1
TABLE_LAST_LEVEL = 255

#: What `profile_for_character` actually refuses outside.  The client's table is
#: the narrower of the two and is the one that means something: a level the
#: client has no progression row for is not a level this server should swing at.
LEVEL_MIN = TABLE_FIRST_LEVEL
LEVEL_MAX = TABLE_LAST_LEVEL

#: The STR this project has actually watched, imported rather than restated.
#: Re-exported under a name that says WHY it is still a pin, so a reader of a
#: call site does not have to come back here to learn that it is one.
ABILITY_STR_PINNED_UNTIL_RE_229_REOPENS = mob_combat.PIN_ATTACKER_ABILITY_STR

#: The level the pinned dummy swings at.  Kept only so `pinned_profile` and
#: `describe_profile_change` can quote the thing they are replacing.
PINNED_LEVEL = mob_combat.PIN_ATTACKER_LEVEL


class ClassAttackerProfileError(RuntimeError):
    """A character row cannot answer "what do I swing as", by name.

    Carries the machine-readable ``reason`` (one of the ``REFUSE_*``
    constants) alongside the human sentence, the same shape
    ``mob_combat.MobCombatContractError`` uses, so a caller can branch on the
    reason without parsing prose.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _require_int(value: object, what: str, reason: str) -> int:
    """``value`` as an int, or a named refusal.

    ``type(value) is not int`` rather than ``isinstance``: ``bool`` is an
    ``int`` subclass, and ``True`` reaching the formula as level 1 is exactly
    the kind of silent coercion this lane has been bitten by before (round
    ``75udgf``, finding S3: an ``int()`` call that answered for
    ``max_hp=1.5``).  There is deliberately no coercion anywhere in this
    module.
    """
    if type(value) is not int:
        raise ClassAttackerProfileError(
            reason, "%s must be an int, got %r" % (what, value)
        )
    return value


@dataclass(frozen=True, kw_only=True)
class CharacterBattleRow:
    """The two persisted columns this module reads, and nothing else.

    Deliberately NOT a store row object: `store.py` is LANE-DB's and this
    lane does not type its rows.  A caller reads `read_typed_attributes` and
    `read_class_id_by_identity`, puts the two answers here, and this module
    never learns there was a database.
    """

    class_id: int
    level: int

    def __post_init__(self) -> None:
        _require_int(self.class_id, "class id", REFUSE_CLASS_ID_NOT_AN_INT)
        _require_int(self.level, "level", REFUSE_LEVEL_NOT_AN_INT)


def profile_for_character(
    row: CharacterBattleRow,
    ability_str: int = ABILITY_STR_PINNED_UNTIL_RE_229_REOPENS,
) -> mob_combat.Combatant:
    """The ``Combatant`` this character swings as, or a named refusal.

    ``row.level`` USED TO BE checked against the committed progression table
    LANE-DB carries -- a real read of the row, so a level inside the span but
    missing from the table still refused.  That import is WITHDRAWN (COO-DECISION
    20260907_2050; the block at the top of this module says why and what it
    costs), so what is left is ``Combatant``'s own ``LEVEL_MIN..LEVEL_MAX``
    range comparison and nothing more.  This paragraph is written in the past
    tense on purpose: a reader must not be able to take the old sentence for
    a description of what runs today.

    ``ability_str`` defaults to the pin and is a parameter rather than a
    constant read inside so that the day ``RE-229`` reopens, the caller that
    learns a real STR needs no change here.  ``ability_con`` is ``0``: the
    attacker half of ``Combatant`` reads ``level`` and ``ability_str`` only
    (that class's own docstring says so), and inventing a defence number for
    a record used as an attacker would be a number nobody asked for.
    """
    _require_int(row.class_id, "class id", REFUSE_CLASS_ID_NOT_AN_INT)
    if not class_catalog.is_known_class_id(row.class_id):
        raise ClassAttackerProfileError(
            REFUSE_CLASS_ID_UNKNOWN,
            "class id %d is not one of the %d selectable classes %r"
            % (row.class_id, class_catalog.CLASS_COUNT, class_catalog.CLASS_IDS),
        )
    level = _require_int(row.level, "level", REFUSE_LEVEL_NOT_AN_INT)
    if not LEVEL_MIN <= level <= LEVEL_MAX:
        raise ClassAttackerProfileError(
            REFUSE_LEVEL_OFF_TABLE,
            "level %d is outside the client's committed progression table, "
            "%d..%d -- NOTE this is a range comparison against that table's "
            "ends, not a read of the row itself; see the block at the top of "
            "this module for what that does and does not still catch"
            % (level, LEVEL_MIN, LEVEL_MAX),
        )
    strength = _require_int(
        ability_str, "ability str", REFUSE_ABILITY_STR_NOT_AN_INT
    )
    if not ABILITY_STR_MIN <= strength <= ABILITY_STR_MAX:
        raise ClassAttackerProfileError(
            REFUSE_ABILITY_STR_OUT_OF_RANGE,
            "ability str %d is outside the range the combatant record "
            "accepts, %d..%d" % (strength, ABILITY_STR_MIN, ABILITY_STR_MAX),
        )
    return mob_combat.Combatant(
        level=level, ability_str=strength, ability_con=0
    )


def pinned_profile() -> mob_combat.Combatant:
    """The profile every player swings as today, for comparison only.

    Delegates to ``mob_combat.pin_attacker`` instead of rebuilding it, so
    that if that pin ever moves this module cannot keep quoting the old one.
    """
    return mob_combat.pin_attacker()


def describe_profile_change(
    row: CharacterBattleRow,
    ability_str: int = ABILITY_STR_PINNED_UNTIL_RE_229_REOPENS,
) -> tuple[str, ...]:
    """ASCII console lines: what this character would swing for, vs the pin.

    This is the shape a GT ticket can quote a number from before anyone
    boots the client.  It states the delta in ATTACK, not in damage: damage
    also subtracts the defender's ``defence``, and which monster is being hit
    is not this module's business.
    """
    mine = profile_for_character(row, ability_str)
    pin = pinned_profile()
    return (
        "CLASS_ATTACKER_PROFILE class=%s class_id=%d level=%d str=%d attack=%d"
        % (
            class_catalog.class_name(row.class_id),
            row.class_id,
            mine.level,
            mine.ability_str,
            mine.attack,
        ),
        "CLASS_ATTACKER_PROFILE_PIN level=%d str=%d attack=%d"
        % (pin.level, pin.ability_str, pin.attack),
        "CLASS_ATTACKER_PROFILE_DELTA attack=%+d"
        % (mine.attack - pin.attack,),
    )


def _headless_summary() -> tuple[str, ...]:
    """Every selectable class at birth level, then the pin, then a verdict.

    Printed by ``python3 -m pirateforce_foundation.class_attacker_profile``.
    The last line is the token a ``HEADLESS_PROOF:`` block quotes; it says
    ARMED rather than WIRED on purpose -- nothing in ``src/`` calls this
    module yet, and a token that said otherwise would be claiming a wiring
    that was named but never observed, which the house round rules forbid.
    (pf-adversary, round ``hhmvit``, D3: an earlier draft put that phrase in
    quotation marks and attributed it to a named file.  It appears in no
    file in either repository -- it was this module's own words dressed as
    a citation.)

    ``callers_in_src=0`` IS A WRITTEN CLAIM, NOT A RUNTIME MEASUREMENT, and
    saying so here is the point: a src module has no business scanning its
    own package at import time.  The measurement lives in
    ``tests/test_class_attacker_profile.py``
    (``CallersInSrcTokenIsMeasuredTests``), which greps every sibling module
    and fails the day this number stops matching the tree -- which is the day
    the CORE-REQUEST filed with this round lands.
    """
    lines: list[str] = []
    for class_id in class_catalog.CLASS_IDS:
        row = CharacterBattleRow(
            class_id=class_id, level=LEVEL_MIN
        )
        lines.extend(describe_profile_change(row)[:1])
    pin = pinned_profile()
    lines.append(
        "CLASS_ATTACKER_PROFILE_PIN level=%d str=%d attack=%d"
        % (pin.level, pin.ability_str, pin.attack)
    )
    lines.append(
        "CLASS_ATTACKER_PROFILE_SUMMARY classes=%d birth_level=%d "
        "callers_in_src=0 RESULT=ARMED"
        % (class_catalog.CLASS_COUNT, LEVEL_MIN)
    )
    return tuple(lines)


if __name__ == "__main__":  # pragma: no cover - console entry point
    for _line in _headless_summary():
        print(_line)
