"""LANE-CS: what the on-screen damage number becomes once the dispatcher
sends the CHARACTER'S OWN level instead of the pinned constant.

WHY THIS EXISTS.  `runtime.py` hands every hit the same attacker record --
the module-level `MOB_COMBAT_DEFAULT_ATTACKER = mob_combat.pin_attacker()`,
handed to the bare-hit path as `attacker=MOB_COMBAT_DEFAULT_ATTACKER` -- so
every class at every level prints exactly the same number on the practice
dummy.  CORE-REQUEST row 032 asks for one variable to move: the attacker's `level`,
read from the character row instead of the pin.  D10: THE ROW IS NOT IN THIS
REPOSITORY AND THAT IS WHY IT IS ADDRESSED BY PATH.  `grep -rn "CORE-REQUEST
row 032"` over this tree finds three files, all of them this lane's own
(this module, its test file, and the importer-census comment this lane wrote
in `tests/test_field_mobs.py`) -- a claim of two was itself wrong, which is
the shape of the problem; the row itself lives in the bridge repository, at
`pf_bridge/CHIEF_CONTINUATION.md` under the heading line that begins "032
CORE-REQUEST", registered by chief 2026-09-07T08:08+07:00, and the letter it
was opened from is
`pf_bridge/notes_to_chief/20260907_0618_LANE-CS-CORE-REQUEST-attacker-level-from-the-real-character.md`.
A reader who cannot open those two files cannot check ANY sentence below that
begins "row 032 says", which is worth saying out loud rather than leaving a
citation that looks local.  Chief's own letter
asks LANE-CS for the numbers that change when it lands, so that the new pin
and the wiring go in ONE commit rather than costing a round to ask for
afterwards (`COO-DECISION 20260907_0445` point 4 condition 1).

This module is that answer, computed rather than transcribed.

WHAT IT DOES NOT DO.  It does not read a character row, it does not touch
`runtime.py`, and it does not change how any hit is resolved: every number
below comes back out of `mob_combat.resolve_damage` unchanged, reached
through `damage_town_target.unclamped_hit_damage`, which is the same function
`tests/test_damage_town_target.py` already pins against R322C.  Those four
R322C numbers are NOT one layer of evidence: the per-hit 891 is what an owner
photographed on the client, while the 192779 -> 189215 hp pair came off the
SERVER console.  `damage_town_target.py` states that split in its own module
docstring, in the sentence beginning "the owner photographed"; the comment
block above its `R322C_OBSERVED_*` constants records their provenance and is
NOT where the split is stated.

    D9, AND IT IS THE THIRD VERSION OF THIS SENTENCE.  The first cited
    `:128`, which was wrong.  T1-F "fixed" it to `:8-13`, which was a line
    number for a docstring that had already moved once -- the same defect
    with a different number, and no test anywhere could tell.  A line number
    into another file is a pin that nothing pins.  The reference is a QUOTED
    PHRASE now, and `tests/test_damage_level_projection.py` greps the named
    file for it, so a future edit that moves or deletes the sentence turns
    this file red instead of leaving a citation that reads authoritative and
    points at nothing.

This module
inherits that split; it does not merge the two layers, and no claim here rests
on the console pair standing in for something seen on screen.  Nothing here is
a production caller and nothing here is reachable from a frame.

ONE VARIABLE, AND THE MODULE PROVES IT IS ONE -- WITH ITS BLIND SPOT NAMED.
The projected attacker is built with `dataclasses.replace` on
`mob_combat.pin_attacker()` -- not assembled here from typed numbers -- so the
day the pin grows a field, or its `ability_str` moves, this module follows it
instead of silently pinning an attacker nobody ships.
`require_only_level_differs` re-checks that claim at call time rather than
leaving it to the docstring, and it checks exactly the attributes it is able
to reason about: the declared `init=True` fields of `Combatant`.  Two kinds of
attribute it CANNOT reason about, because a value derived from `level` is
supposed to move when `level` moves:

  * a declared field with `init=False`, which `dataclasses.replace`
    recomputes, and
  * instance state assigned in `__post_init__`, which `dataclasses.fields`
    never sees at all.

Rather than pretend, the guard skips both and :func:`unchecked_attributes`
reports them by name.  On the `Combatant` shipped today that report is EMPTY,
so the "only level moves" claim is complete -- and
`tests/test_damage_level_projection.py` asserts the report is empty, so the
day someone adds a derived column the TEST goes red naming it instead of this
module refusing every level with a message blaming the caller.

WHY THE HITS COLUMN IS A CEILING AND NOT A DIVISION.  The last hit of a kill
is clamped to the room left (`mob_combat.apply_hit`), so a player watching the
screen sees a smaller number on the final swing -- the same trap
`damage_town_target.unclamped_hit_damage`'s docstring names.  The hit COUNT is
unaffected by that clamp, which is why this module can answer it in integer
arithmetic; `tests/test_damage_level_projection.py` proves the ceiling agrees
with walking the ladder one hit at a time through
`damage_town_target.hp_after_hits` rather than asserting it in prose.

AND THE CLAMPED SWING IS A COLUMN, NOT A CAVEAT (T1-D).  A row that said
`damage_per_hit=891, hits_to_fell=223` put back the exact claim this lane had
withdrawn: on this dummy the 223rd swing prints **323**, not 891.  The field
is now `unclamped_damage_per_hit`, `final_hit_damage` sits beside it, and both
are computed from the same room so they cannot drift apart.  Prose does not
survive the trip into a letter; a column does.

AND THE COUNT IS FROM FULL (T1-E).  `hits_to_fell` starts at `max_hp`, which
is a dummy nobody has touched.  R322C started at 192779 and takes 217 swings,
not 223.  :func:`hits_to_fell_from_hp` is the same count from a stated hp, so
the watched run and the full-bar table can never be quoted for each other.

THE ONE IMPORT FROM ANOTHER LANE'S MODULE, AND WHY IT STAYS (D7).  This file
names `field_mobs.TOWN_TARGET_N_ID`, which puts it in the textual importer
list `tests/test_field_mobs.py` pins -- LANE-B's file, widened by LANE-CS in
round `623ivx`.  pf-adversary was right that this needs deciding rather than
explaining, and right that `damage_town_target.py`'s own docstring calls a
move of that shape "trespassing to save one function call".  DECIDED: the
import stays, and here is the difference from the move that sentence refused,
because leaving the two files contradicting each other is worse than either
choice.

  RULED BY THE COO, NOT BY THIS LANE ALONE.  `COO-DECISION 20260907_1744`
  (`pf_bridge/notes_to_chief/20260907_1744_COO-DECISION-cs1658-trespass-line-
  and-two-connections-LANE-CS.md`, answering this lane's letter `1658`)
  upheld option (a) and raised the line below to a house rule for every
  lane: READING ONE PUBLIC CONSTANT TO COMPARE AN ARGUMENT AGAINST IS NOT
  TRESPASS (fill in the census with the reason); LOOKING A ROW UP OUT OF
  ANOTHER LANE'S TABLE AT RUN TIME IS.  The same ruling rejected the other
  two options in those words -- (b) breaks this lane's no-number-without-a-
  source rule, (c) "wakes T1-E back up in the shape of a parameter".  It
  also directed that the rule be written into `AGENTS.md` section 7 by chief, not
  by this lane, so nothing below edits that file.  Until it appears there,
  section 7 is not the citation for this; this decision letter is.

  * What `damage_town_target` refused was LOOKING THE ROW UP -- reading the
    default roster to find the dummy itself.  That is a dispatch: the module
    would decide WHICH monster it is about, out of another lane's table, at
    call time.  It takes the row as an argument instead, and still does.
  * What this module does is read ONE public integer constant to compare an
    argument against.  The caller still hands in the row.  It reads no
    roster, and `runtime.py`/`app.py` were grepped for it with zero hits.

  * The alternatives were weighed and are both worse.  Re-typing `916` here
    breaks the rule this lane is under -- no number without a source.  Taking
    the id as a caller-supplied argument hands the caller the power to say
    `subject_template_id=31`, which is EXACTLY the defect T1-E was raised
    about, dressed as a parameter.
  * And it is the mechanism that file offers on purpose: LANE-A's
    `world_scene_registry.py` and five LANE-B modules are in the same list by
    the same "WIDENED AGAIN" comment form.  Being in a textual importer
    census is not trespass; the census exists to be added to with a stated
    reason, which round `623ivx` did, and told LANE-B by letter.

WHOSE HP IS 192779, AND THEREFORE WHOSE COUNT IS 217 (D8).  Answered, not
deferred: it is ONE CONNECTION'S.  `damage_town_target.py`'s own docstring
says so in the sentence naming it as the dummy's hp inside
ONE connection's combat ledger -- `runtime.py` opens that ledger per
connection,
so a second player standing in the same scene at that instant would have
seen 198125.  Two consequences this module now carries in its own text
rather than leaving to a reader:

  * `hits_to_fell_from_hp(level, mob, 192779) == 217` is a statement about
    the connection R322C was watching, NOT about the dummy in the scene.
  * `hits_to_fell_at_level` (from `max_hp`) is not "the shared truth" either.
    It is the count for a connection whose ledger has just opened.  There is
    no per-scene hp for this dummy today to be the third answer.

  So neither column may be quoted as "how many hits the dummy takes"
  full stop, and the difference between them (223 vs 217) is not a
  discrepancy to be reconciled -- it is two connections.

  CONFIRMED, AND THE RECONCILIATION IS NOW FORBIDDEN RATHER THAN MERELY
  UNWISE.  `COO-DECISION 20260907_1744` item 2 made this lane's answer
  official and added the standing instruction that NOBODY may "make the two
  numbers agree" in a later round: collapsing them into one number requires
  a per-scene hp for this dummy to exist first, and building that is
  LANE-DB's and LANE-A's work, not this lane's.  A round that finds these
  two columns disagreeing has found the two connections, not a bug.

WHAT IS OPEN.  `ability_str` stays at the pin for every row here, because
CORE-REQUEST row 032 moves the level half only.  A character's real STR is
`RE-293`'s question, and `COO-DECISION 20260907_1441` closed it as a DESIGN
question rather than an RE one: there is no per-class starting-stat table in
anything this repository ships, so the formula carries no STR term that has no
source.  This module does not guess it, and every projection below is
explicitly "this character's level, the pinned STR", not "this character".

WHAT THIS MODULE DOES NOT IMPLEMENT, SAID HERE BECAUSE SILENCE READ AS
COVERAGE (T1-H).  CORE-REQUEST row 032 carries THREE conditions from
`COO-DECISION 20260907_0445` item 4, and this module implements none of them
-- it is the table the request asks for alongside the wiring, not the wiring.
They are listed because a reader who found three in the request and two here
would be entitled to assume the third was handled, which is the defect T1-H
was raised about and which a first version of this paragraph committed again
by naming only one of them:

  1. the 891 pin moves in the SAME commit as the wiring, with the expected
     new numbers and the reason;
  2. mob-to-player damage is NOT touched (that is LANE-B's, M4's);
  3. a level that cannot be read falls back to the pin together with a NAMED
     event, never a silent 0.

The wording above is a TRANSLATION, not a quotation: row 032 is written in
Thai and no English sentence in either repository matches it word for word.
pf-adversary was right that putting a translation in quotation marks is a
citation that cannot be checked, and right that the test which "verifies" it
only greps the module that wrote it -- there is no oracle for this one,
because `pf_gate_preflight` runs this suite with no `pf_bridge` beside it.
Said plainly here rather than left to look verified.  Nothing in this
module does that, and nothing in this module can: the read happens in
`runtime.py`, which is a CORE-REQUEST seam and not this lane's to write.  This
module is the projection table the request asks for alongside that change, so
a reader who finds all three conditions in the request and only two discussed
here would otherwise be entitled to assume the third was handled.
"""
from __future__ import annotations

import collections.abc
import dataclasses
from typing import Any

from . import damage_town_target, field_mobs, mob_combat
from .mob_combat import Combatant

__all__ = [
    "LevelProjectionError",
    "LevelOutOfRangeError",
    "PinWillNotAssembleError",
    "NotTheTypedMobRecordError",
    "NotThePracticeDummyError",
    "UnorderedLevelRequestError",
    "HpWillNotReadAsAnIntError",
    "ProjectedRow",
    "attacker_at_level",
    "unchecked_attributes",
    "require_only_level_differs",
    "damage_at_level",
    "final_hit_damage_at_level",
    "hits_to_fell_at_level",
    "hits_to_fell_from_hp",
    "project_levels",
    "production_pin_row",
]


class LevelProjectionError(RuntimeError):
    """Base for every refusal this projection makes."""


class LevelOutOfRangeError(LevelProjectionError):
    """The CALLER's level is one the shipped `Combatant` will not accept."""


class PinWillNotAssembleError(LevelProjectionError):
    """The PIN itself will not rebuild -- nothing to do with the level asked.

    Kept apart from :class:`LevelOutOfRangeError` on purpose.  A single
    `except Exception` around `dataclasses.replace` blamed the caller's level
    for both, so the day `PIN_ATTACKER_ABILITY_STR` drifts outside the range
    `Combatant.__post_init__` enforces, `attacker_at_level(7)` would report
    "7 is not a level the shipped Combatant accepts" -- a true-sounding
    sentence about the wrong number, for every level, with the test class that
    asserts refusals still reporting green.
    """


class NotThePracticeDummyError(LevelProjectionError):
    """The mob handed in is not the dummy this lane measures against.

    T1-E: `damage_at_level` used to answer for any typed `FieldMob` -- a
    `replace(dummy, template_id=31)` came back with a normal-looking number --
    even though every sentence in this module, and LANE-CS's charter, says the
    subject is Training Iron Man (`field_mobs.TOWN_TARGET_N_ID`).  A number
    computed for a monster nobody pinned is worse than a refusal because it
    reads exactly like a number that was.
    """


class NotTheTypedMobRecordError(LevelProjectionError):
    """The `mob` argument is not a record the shipped combat path will take.

    D3.  T1-A closed the leak on the PIN side of this module and left the
    MOB side open: `mob_combat.mob_defender` refuses anything that is not a
    typed `FieldMob` with `MobCombatContractError`, a class a caller reading
    THIS module's hierarchy has no reason to catch, and that refusal reached
    every public entry point unrenamed.  Measured, not argued: before this,
    `damage_at_level(7, SimpleNamespace(template_id=916, max_hp=198125,
    level=100))` came out of five entry points as `MobCombatContractError`
    while `except LevelProjectionError` -- the sentence the hierarchy invites
    -- caught nothing.  A duck-typed stand-in with the right `template_id`
    walked straight past :class:`NotThePracticeDummyError`, which only ever
    looked at that one attribute.

    Kept apart from :class:`NotThePracticeDummyError` on purpose, and checked
    BEFORE it: "this is not a roster record at all" and "this is a roster
    record for the wrong monster" are different mistakes, and collapsing them
    into one message is how a caller who handed in a `SimpleNamespace` goes
    looking for the wrong template id.  Checking it first is also what keeps
    `mob_defender`'s own type refusal on a path something walks -- adding the
    template gate for T1-E had left that sentence true of no reachable call.
    """


class UnorderedLevelRequestError(LevelProjectionError):
    """`project_levels` was handed a container that has no order to keep.

    T1-E: a `set` or a `dict` went through `tuple(levels)`, which invented an
    order, and `TheTableKeepsTheOrderItWasAsked` then vouched for "the order
    given" for a request that never had one.
    """


class HpWillNotReadAsAnIntError(LevelProjectionError):
    """An hp this projection was asked to count from is not a plain int.

    S4/D3-second-half.  `_room` used to open with `int(mob.max_hp)`, which
    does two bad things at once and did both silently:

      * `max_hp=1.5` was TRUNCATED to 1, so `hits_to_fell` came back as **1**
        and `ProjectedRow(level=7, ..., hits_to_fell=1, final_hit_damage=1)`
        was a full, ordinary-looking row computed for a dummy nobody could
        have measured.  That is the defect :class:`NotThePracticeDummyError`
        was raised about, in its own words: "a number computed for a monster
        nobody pinned is worse than a refusal because it reads exactly like a
        number that was."
      * `max_hp="198125"` or `max_hp=None` raised a raw `ValueError` /
        `TypeError` out of five public entry points -- the leak D3 closed on
        the record side, reopened one line lower by a builtin.

    Both are one question ("is this hp a plain int?") and it is asked here,
    with `type(...) is not int`, which also refuses `True`.  The refusal is
    this module's own so a caller under `except LevelProjectionError` sees it.
    """


@dataclasses.dataclass(frozen=True)
class ProjectedRow:
    """One row of the answer chief asked for: a level and what it prints.

    THE FIRST NUMBER IS NOT WHAT THE SCREEN SHOWS ON EVERY SWING, which is
    why the field is no longer called `damage_per_hit`.  T1-D: the row
    `(7, 891, 223)` reads as "223 swings of 891", but `mob_combat.apply_hit`
    clamps the last swing to the room left, so on this dummy the 223rd swing
    prints **323**.  This lane had already withdrawn that claim once in
    `damage_town_target.unclamped_hit_damage`'s docstring and the row put it
    straight back.  The clamped last swing is a number an owner watching the
    dummy die will photograph, so it is a COLUMN here, not a caveat in prose
    that a report can drop on its way to a letter.
    """

    level: int
    unclamped_damage_per_hit: int
    hits_to_fell: int
    final_hit_damage: int


def _shipped_pin() -> Combatant:
    """`mob_combat.pin_attacker()` with its refusal renamed to this module's.

    T1-A.  This call used to sit OUTSIDE every `try` in the module, so the day
    `PIN_ATTACKER_ABILITY_STR` or `PIN_ATTACKER_LEVEL` drifts outside the
    range `Combatant.__post_init__` enforces, all seven public entry points
    let `mob_combat.MobCombatContractError` escape -- a class that a caller
    reading THIS module's exception hierarchy has no reason to catch.
    Measured, not argued: with `PIN_ATTACKER_ABILITY_STR = 200000` every entry
    point raised that class and `except LevelProjectionError` -- the sentence
    the hierarchy invites -- caught nothing.

    D4, PAID HERE: the first version of this wrapper opened with `except
    LevelProjectionError: raise` -- "already ours; keep its name".  Nothing
    inside `mob_combat` has ever heard of `LevelProjectionError`, so that
    branch was a sentence, not a path: it was the same defect (a branch no
    caller can walk, added in the commit that fixed a different one) that
    T1-C had just been raised about, reintroduced two functions away.
    Deleting it changes no behaviour REACHABLE FROM SHIPPED CODE, and that
    qualifier is the whole claim.  A first version of this paragraph said
    "changes no behaviour" and offered the suite staying at `50 passed` as
    the proof; pf-adversary pointed out the suite is green with the branch
    present too, so it was never evidence in either direction, and then
    showed the branch IS observable through the monkeypatch idiom five tests
    in this file already use (patch `mob_combat.pin_attacker` to raise
    `LevelOutOfRangeError`; with the branch that name survives, without it
    the caller gets `PinWillNotAssembleError`).  Nothing shipped can set that
    up, which is the point.
    A guard that cannot fire is not a cheap guard, it is a false statement
    about what the code does.

    Renaming it here is also what makes :class:`PinWillNotAssembleError`
    reachable from shipped code.  Before this, the only path into it ran
    through a test that replaced `mob_combat.pin_attacker` with a lambda
    returning a bare `object()`; a refusal class no shipped line can raise is
    a docstring, not behaviour.
    """
    try:
        return mob_combat.pin_attacker()
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise PinWillNotAssembleError(
            "the shipped pin will not build at all (%s: %s); no level was "
            "asked for yet, so no level is what failed"
            % (type(exc).__name__, exc)
        ) from exc


def attacker_at_level(level: int) -> Combatant:
    """The production-pinned attacker with `level` replaced and nothing else.

    Raises :class:`LevelOutOfRangeError` for a level `Combatant` itself would
    refuse, by asking `Combatant` rather than re-typing its bounds here: the
    range that matters is the one the shipped record enforces, and a second
    copy of it is how two range checks drift apart.

    Raises :class:`PinWillNotAssembleError` -- a DIFFERENT name -- when it is
    the pin, not the level, that will not go back together.  The pin is
    rebuilt at its own level first precisely so the two failures can never be
    reported with the same sentence.
    """
    if type(level) is not int or type(level) is bool:
        raise LevelProjectionError("level must be an int")
    pin = _shipped_pin()
    try:
        rebuilt_at_its_own_level = dataclasses.replace(pin, level=pin.level)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise PinWillNotAssembleError(
            "the shipped pin will not rebuild even at its own level %r; the "
            "level %r that was asked for is not what failed"
            % (getattr(pin, "level", None), level)
        ) from exc
    if level == pin.level:
        return rebuilt_at_its_own_level
    try:
        return dataclasses.replace(pin, level=level)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise LevelOutOfRangeError(
            "level %r is not one the shipped Combatant accepts" % (level,)
        ) from exc


def unchecked_attributes(sample: Any = None) -> tuple[str, ...]:
    """The attribute names :func:`require_only_level_differs` does NOT vouch
    for, sorted, so the blind spot is a value a test can assert on.

    Two kinds qualify, and both for the same reason: a value derived from
    `level` is SUPPOSED to move when `level` moves, so comparing it would
    refuse every honest projection.

      * a declared field with `init=False`, which `dataclasses.replace`
        recomputes for the new level, and
      * an instance attribute that `dataclasses.fields` does not declare at
        all, i.e. state assigned in `__post_init__`.

    `sample` defaults to the shipped pin.  On the `Combatant` shipped today
    this returns `()` -- which is the whole point: the emptiness is asserted
    in `tests/test_damage_level_projection.py`, so a derived column added
    tomorrow turns that test red BY NAME instead of turning this module into
    something that refuses every level.
    """
    record = _shipped_pin() if sample is None else sample
    declared = {field.name for field in dataclasses.fields(record)}
    derived = {field.name for field in dataclasses.fields(record)
               if not field.init}
    try:
        undeclared = set(vars(record)) - declared
    except TypeError:                             # no instance __dict__
        undeclared = set()
    return tuple(sorted(derived | undeclared))


def require_only_level_differs(projected: Combatant) -> None:
    """Refuse a projected attacker that moved anything except `level`.

    Compared field by field against `mob_combat.pin_attacker()` through
    `dataclasses.fields`, so a field added to `Combatant` tomorrow is compared
    too without an edit here.  This is the check that makes the module's
    "one variable" claim mechanical instead of editorial.

    Scope, stated because an unscoped version of this sentence was the defect:
    the comparison covers the declared `init=True` fields only.  Anything in
    :func:`unchecked_attributes` is skipped and the refusal message never
    pretends otherwise.
    """
    pin = _shipped_pin()
    if type(projected) is not Combatant:
        raise LevelProjectionError("projected must be the typed Combatant")
    skipped = set(unchecked_attributes(pin))
    for field in dataclasses.fields(pin):
        if field.name == "level" or field.name in skipped:
            continue
        if getattr(projected, field.name) != getattr(pin, field.name):
            raise LevelProjectionError(
                "projection moved %s as well as level" % (field.name,))


def _typed_defender(mob: Any) -> Combatant:
    """`damage_town_target.town_target_defender(mob)` with its refusal renamed.

    D3.  This is the MOB-side twin of :func:`_shipped_pin`, and it exists for
    the same reason: the refusal that reaches a caller has to be one this
    module's hierarchy names.  It is also the only call that puts
    `mob_combat.mob_defender`'s "must be the typed FieldMob record" door back
    on a walked path -- see :class:`NotTheTypedMobRecordError`.

    Only `MobCombatContractError` is renamed, and nothing else is caught: a
    bare `except Exception` here would be the branch-nobody-walks defect this
    file has now been raised about twice (T1-C, D4).
    """
    try:
        return damage_town_target.town_target_defender(mob)
    except mob_combat.MobCombatContractError as exc:
        raise NotTheTypedMobRecordError(
            "this projection can only be computed for a record the shipped "
            "combat path accepts; %s" % (exc,)
        ) from exc


def damage_at_level(level: int, mob: Any) -> int:
    """One unclamped hit on `mob` from a character of `level`.

    `mob` must be a Training Iron Man row (`field_mobs.TOWN_TARGET_N_ID`),
    and it is checked in two steps because there are two different mistakes.

    FIRST, is it a roster record at all?  `mob_combat.mob_defender` decides
    that, and :func:`_typed_defender` is how its answer reaches the caller
    under a name from this module's own hierarchy (D3 --
    :class:`NotTheTypedMobRecordError`).  Asking it first is also what keeps
    that door walked: the template check below reads one attribute, so before
    D3 a `SimpleNamespace(template_id=916, ...)` sailed past it and the
    refusal that eventually fired came from a class this module never names.

    SECOND, is it the RIGHT roster record?  `mob_defender` has no opinion
    about WHICH monster, so a `replace(dummy, template_id=31)` used to come
    back with a perfectly ordinary number -- see
    :class:`NotThePracticeDummyError`.  The template check is here rather than
    inside the formula because the formula is general and this projection is
    not: every sentence in this module is about the dummy.
    """
    _typed_defender(mob)
    template = getattr(mob, "template_id", None)
    if template != field_mobs.TOWN_TARGET_N_ID:
        raise NotThePracticeDummyError(
            "this projection is only about Training Iron Man (template %r); "
            "the mob handed in is template %r"
            % (field_mobs.TOWN_TARGET_N_ID, template))
    attacker = attacker_at_level(level)
    require_only_level_differs(attacker)
    return damage_town_target.unclamped_hit_damage(attacker, mob)


def _require_hp_int(value: Any, label: str) -> int:
    """`value` if it is a plain int, else this module's own refusal (S3).

    `type(value) is not int` rather than `isinstance`, for the reason
    `mob_combat._require_int` gives on the line it copies: `True` is an
    `int` by inheritance and an hp of `True` is a caller mistake, not an hp
    of 1.  A `float` is refused rather than truncated -- truncating is how
    `max_hp=1.5` used to answer.
    """
    if type(value) is not int:
        raise HpWillNotReadAsAnIntError(
            "%s must be a plain int for this projection to count from; got "
            "%r (%s)" % (label, value, type(value).__name__))
    return value


def _room(mob: Any, current_hp: Any = None) -> int:
    """The hp between `current_hp` (default: FULL) and the floor.

    The default is the seam T1-E named: `max_hp` is the hp of a dummy nobody
    has touched, while the only run this lane has ever watched (R322C) started
    at 192779, not at 198125.  Callers who mean the watched run say so with
    `current_hp`; the default is documented as "full" everywhere it reaches a
    public name, so the two can never be quoted for each other.

    BOTH HP NUMBERS ARE ASKED THE SAME QUESTION NOW (S3).  `int(mob.max_hp)`
    was doing the ceiling's type check by coercion, which is not a check:
    `max_hp=1.5` truncated to 1 and the module ANSWERED (`hits_to_fell=1`),
    and `max_hp=None` came out as a raw `TypeError`.  The caller's hp was
    already refused by type; the record's now is too, through
    :class:`HpWillNotReadAsAnIntError`, and the coercion is gone -- there is
    no `int()` left in this function for a mutant to delete.

    `mob.max_hp` is read directly rather than through a `getattr` default,
    because every path here goes through :func:`damage_at_level` first and a
    record that reached it is a typed `FieldMob` with that field.  A default
    would be a branch nothing can walk, which is the defect T1-C and D4 were
    both raised about in this same file.
    """
    ceiling = _require_hp_int(mob.max_hp, "max_hp")
    start = ceiling if current_hp is None else _require_hp_int(
        current_hp, "current_hp")
    if not mob_combat.HP_FLOOR <= start <= ceiling:
        raise LevelProjectionError(
            "current_hp %r is outside [%r, %r] for this mob"
            % (start, mob_combat.HP_FLOOR, ceiling))
    return start - mob_combat.HP_FLOOR


def hits_to_fell_at_level(level: int, mob: Any) -> int:
    """Hits of :func:`damage_at_level` to take `mob` from FULL to the floor.

    The ceiling of (max hp above the floor) / (damage per hit), in integer
    arithmetic.  `max_hp` is read off the shipped record; the floor is
    `mob_combat.HP_FLOOR` rather than a typed zero, for the same reason
    `damage_town_target.applied_damage` reads it there.

    "From full" is load-bearing, not decoration: R322C did not start from
    full.  :func:`hits_to_fell_from_hp` is the same count from a stated hp,
    and on this dummy it answers 217 from 192779 where this one answers 223.

    D8: NEITHER NUMBER IS "THE DUMMY'S".  Both are per-CONNECTION, because
    the ledger the hp comes out of is per connection -- see the module
    docstring.  This one is the count for a connection whose ledger has just
    opened; 217 is the count for the one R322C watched.  A letter that
    quotes either as "how many hits Training Iron Man takes" has dropped the
    only qualifier that makes it true.
    """
    return hits_to_fell_from_hp(level, mob, None)


def hits_to_fell_from_hp(level: int, mob: Any, current_hp: Any = None) -> int:
    """Hits to take `mob` from `current_hp` (default full) to the floor."""
    per_hit = damage_at_level(level, mob)
    room = _room(mob, current_hp)
    return -(-room // per_hit)


def final_hit_damage_at_level(
    level: int, mob: Any, current_hp: Any = None,
) -> int:
    """What the LAST swing prints -- the clamped one (T1-D).

    The number is not computed here.  It is asked of
    `damage_town_target.applied_damage`, which owns the mirror of
    `mob_combat.apply_hit`'s clamp, at the hp the dummy is standing on when
    the last swing lands.  Adversary D2 is why: an arithmetic version of this
    (`room % per_hit or per_hit`) was not connected to the clamp it claimed
    to model -- nothing went red when the clamp was removed -- and it
    CONTRADICTED it at a legal argument, answering 891 for a dummy already at
    the floor, where the hit count beside it answers 0 swings.  A column that
    says "what the screen prints" has to go through the function that decides
    what the screen prints.

    `current_hp` defaults to FULL.  At the floor there is no last swing, and
    `applied_damage` is still the one that says so (it answers 0 for a hit on
    something already down) rather than a zero typed here.
    """
    attacker = attacker_at_level(level)
    require_only_level_differs(attacker)
    per_hit = damage_at_level(level, mob)
    room = _room(mob, current_hp)
    if not room:
        return damage_town_target.applied_damage(
            attacker, mob, mob_combat.HP_FLOOR)
    # The hp the dummy is standing on before the last swing.  Written as a
    # remainder rather than `room - (hits - 1) * per_hit` because `K_DEF_LV`
    # is 1, so a typed `1` here is a formula constant this module is
    # forbidden to carry -- `test_the_module_types_none_of_the_numbers_it_
    # reports` caught exactly this line.  A room that divides evenly means
    # the last swing starts at a FULL swing of room, which is the `or` branch.
    hp_before_last = mob_combat.HP_FLOOR + (room % per_hit or per_hit)
    return damage_town_target.applied_damage(attacker, mob, hp_before_last)


def _indexed_in_iteration_order(levels: Any) -> tuple:
    """`tuple(levels)`, but only once the index order IS that order (S4).

    `isinstance(x, collections.abc.Sequence)` is true of anything somebody
    called `Sequence.register()` on, whether or not it has `__getitem__`.
    This asks the object instead: length, then every index from `0` to
    `len - 1`, then that the result equals what iterating gives.  A
    registered `frozenset` fails at the first index; a container whose
    `__iter__` disagrees with its `__getitem__` fails the comparison, which
    is the only way "the order given" can be a single thing.
    """
    try:
        length = len(levels)
        indexed = tuple(levels[position] for position in range(length))
    except (TypeError, IndexError, KeyError) as exc:
        raise UnorderedLevelRequestError(
            "project_levels keeps the order it was given, so it reads the "
            "request by index; a %s says it is a Sequence but will not be "
            "indexed (%s)" % (type(levels).__name__, exc)) from exc
    walked = tuple(levels)
    if indexed != walked:
        raise UnorderedLevelRequestError(
            "project_levels keeps the order it was given, and a %s gives two "
            "different orders: by index %r, by iteration %r"
            % (type(levels).__name__, indexed, walked))
    return indexed


def project_levels(mob: Any, levels: Any) -> tuple[ProjectedRow, ...]:
    """The projection table for `levels`, in the order given, from FULL hp.

    Refuses an empty request rather than answering it with an empty table: a
    caller that asked for nothing has a bug, and an empty tuple reads like a
    measurement.

    Refuses an UNORDERED request for the same class of reason (T1-E): this
    function promises "the order given", and a `set` or a `dict` never gave
    one -- `tuple()` invented it.  A `str` is refused too: it iterates, so it
    would otherwise be read one character at a time.

    D6: THE CHECK IS A WHITELIST NOW, BECAUSE THE BLACKLIST WAS A LIST OF
    THREE TYPES AND NOT A TEST FOR ORDER.  `isinstance(levels, (set,
    frozenset, dict, str, bytes))` named the three unordered containers
    somebody thought of.  Measured, not argued: `dict.keys()` (a view, not a
    `dict`), a generator over a set, and any subclass of
    `collections.abc.Set` all walked through it, and the table then vouched
    for "the order given" for a request that never had one.  Enumerating the
    unordered types cannot work -- anyone can write a new one -- so the
    question asked is the positive one: is this a `Sequence`, the protocol
    that MEANS "indexed, and the index is the order"?  `list`, `tuple` and
    `range` are; views, sets, generators and iterators are not.  `str`,
    `bytes` and `bytearray` are Sequences and are still refused by name,
    for the reason above: they would be read one element at a time and every
    element is the wrong type.

    A generator is refused even when it happens to wrap a list.  That is
    deliberate and it is the cost of the rule: this function cannot see what
    a generator is walking, so it cannot tell the honest one from the one
    over a set, and guessing is what the whole class exists to stop.
    Callers with a generator write `tuple(...)` and say so.

    S4: `isinstance(levels, Sequence)` IS A REGISTRATION, NOT A PROOF, AND
    THE BYTES BLACKLIST STILL CARRIED WEIGHT.  Adversary measured both holes
    on the version above:

      * `memoryview(b'\\x07d')` walked through and was read byte by byte as
        `[7, 100]`, while the IDENTICAL `bytes` object was refused by name.
        A three-name list cannot be the test for "would be read one element
        at a time"; the buffer protocol is, so anything `memoryview()`
        accepts is refused here -- `bytes`, `bytearray`, `memoryview`,
        `array.array`, `mmap`, and whatever is written next.  `str` stays
        by name because it is the one that is NOT a buffer.
      * `Sequence.register(frozenset)` makes `isinstance` say yes to a
        container with no `__getitem__` at all.  Registration is a claim by
        whoever wrote the `register()` call.  So the order is MEASURED here:
        walking the indices `0..len-1` must reproduce iteration exactly.  A
        container that cannot be indexed raises on the first index and is
        refused; one whose index order differs from its iteration order is
        refused by name, because "the order given" would then mean two
        different things in one call.

    The cost is stated rather than hidden: an `array.array('l', [1, 2, 3])`
    is an ordered container of ints and is refused anyway, because this
    function will not try to tell a buffer of levels from a buffer of bytes.
    `tuple(...)` is one call and says which one the caller meant.
    """
    if isinstance(levels, str):
        raise UnorderedLevelRequestError(
            "project_levels takes levels, and a str would be read one "
            "element at a time -- one character per level; hand it a list "
            "or a tuple")
    try:
        memoryview(levels)
    except TypeError:
        pass
    else:
        raise UnorderedLevelRequestError(
            "project_levels takes levels, and a %s is a buffer that would be "
            "read one element at a time; hand it a list or a tuple"
            % (type(levels).__name__,))
    if not isinstance(levels, collections.abc.Sequence):
        raise UnorderedLevelRequestError(
            "project_levels keeps the order it was given, so it will only "
            "take a Sequence (an indexed container, where the index IS the "
            "order); a %s does not promise one -- hand it a list or a tuple"
            % (type(levels).__name__,))
    wanted = _indexed_in_iteration_order(levels)
    if not wanted:
        raise LevelProjectionError("project_levels needs at least one level")
    return tuple(
        ProjectedRow(
            level=level,
            unclamped_damage_per_hit=damage_at_level(level, mob),
            hits_to_fell=hits_to_fell_at_level(level, mob),
            final_hit_damage=final_hit_damage_at_level(level, mob),
        )
        for level in wanted
    )


def production_pin_row(mob: Any) -> ProjectedRow:
    """The row for the level production pins TODAY.

    This is the anchor of the whole table: it must reproduce, number for
    number, what the shipped pinned attacker already resolves against this
    same dummy.  `tests/test_damage_level_projection.py` asserts exactly that
    against `damage_town_target.unclamped_hit_damage(mob_combat.pin_attacker(),
    mob)` -- so the projection cannot drift away from the pin it is meant to
    replace without going red.
    """
    return project_levels(mob, (mob_combat.PIN_ATTACKER_LEVEL,))[0]
