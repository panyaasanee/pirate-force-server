"""LANE-B: the AI_COMBAT rule language, parsed, and the AI_WANDER script read.

PANYA-DECISION 20260906_2032 (pf_bridge notes_to_chief/
20260906_2032_KA1A-PANYA-DECISION-COO-B-ai-rule-interpreter-wander-UI-wire-
coverage-bar.md), work item 1 for this lane: a parser for the seven-word rule
language, an evaluator that answers ONE line per tick, and a reader for the
wander script.  Nothing here sends a frame; this module turns two table
columns into a decision the AI tick can act on.

WHAT THE TABLE ACTUALLY LOOKS LIKE, MEASURED, NOT ASSUMED
    ``field_mob_ai_tables.AI_COMBAT_ROWS`` maps ``n_ID`` to the pair
    ``(s_CONDITOIN, s_ACTION)``.  Both columns are ONE string holding several
    rule lines, and the separator between those lines is the two characters
    BACKSLASH and ``n`` -- not a newline.  Measured on the shipped module:
    every row contains ``\\n`` as two characters and none contains chr(10).
    A parser that split on ``"\n"`` would read every row as a single line
    whose last token is ``GO(0)`` and would therefore answer the default on
    every tick, for every monster, forever, while looking like it worked.
    That is why ``RULE_SEPARATOR`` is a named constant with this paragraph
    attached to it.

WHAT THIS LANE MEASURED ABOUT THE SHIPPED SLICE (a nonclaim about the rest)
    The decision letter describes the full ``CONSTDATA_TH__AI_COMBAT`` table:
    276 rows, of which six are not parallel between the two columns and eight
    do not end with ``GO(0)``.  The module committed to THIS repository is the
    ``bg0001`` slice: 34 rows, and on those 34 rows

      * every row is parallel (``AI_COMBAT_PARALLEL`` is True for all 34), and
      * every row's condition column ends with exactly ``GO(0)``.

    So the six and the eight are outside the slice this repository can see.
    The parser still declares its behaviour for both shapes (see
    ``parse_program``) because the slice is expected to grow, and a shape that
    is declared only in prose is a shape nobody tested.

    Also measured, and NOT in the letter's vocabulary list: the shipped slice
    uses ``HP_ALLY<`` (rows 293 and 323), while ``BUFF_ENEMY`` and
    ``HP_ENEMY`` -- both named in the letter -- appear nowhere in it.  This
    module accepts the union of the two vocabularies, so neither a row the
    letter predicted nor a row the table actually ships can raise
    ``UnknownRuleToken`` on a tree where the other one is missing.

WHAT IS ASSUMED, NAMED HERE SO A LATER ROUND CAN CHANGE ONE CONSTANT
    A1  Tokens separated by ``;`` on one condition line are ANDed.  Nothing
        in the data distinguishes an OR; every multi-token line reads as a
        conjunction of narrowing tests.
    A2  ``RATE(n)`` is an n-percent chance PER EVALUATION, which is the
        reading the owner's decision letter names as the assumption to
        record.  ``RATE_IS_PER_EVALUATION`` carries it.
    A3  ``DOONCE(0)`` lets its line fire once per monster life.  The caller
        owns the memory (``EvalState.doonce_fired``) because this module
        holds no state between ticks.
    A4  ``BUFF_I(id, a, b)`` in the CONDITION column reads as "the monster
        itself carries buff ``id``".  The two trailing numbers are carried
        but not read: no measurement in this repository says what they mean.
    A5  ``CHASE(n)`` names slot ``n`` of ``MOBS.s_SKILLS``.  The letter says
        in as many words that the true meaning of ``n`` is unproven, so this
        module carries the integer and never resolves it to a skill id.

NOT ANSWERED HERE, and no caller may read it as if it were: whether the
client agrees with any of this.  Nothing in this module has been seen on a
screen.  It is the reading of a table, and the GT ticket that puts it in
front of a player is a separate piece of work.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple

# The two characters the table uses between rule lines.  See the module
# docstring: this is BACKSLASH + 'n', not a newline, and reading it as a
# newline silently reduces every monster to its GO(0) default.
RULE_SEPARATOR = "\\n"

# A2: the reading of RATE(n) this lane committed to.  One constant, one
# place to change it if a measurement ever contradicts it.
RATE_IS_PER_EVALUATION = True

# A3: the token that marks a line as once-per-life.
DOONCE_TOKEN = "DOONCE"


class UnknownRuleToken(ValueError):
    """A token the rule vocabulary does not contain.

    Raised rather than skipped.  A skipped token is a condition that silently
    stops narrowing, which turns a specific rule line into a more general one
    and makes the monster act on rules it was never given.
    """


@dataclass(frozen=True)
class Condition:
    """One condition token: its name, its comparison, and its arguments.

    ``op`` is ``'<'``, ``'>'`` or ``''`` (no comparison, e.g. ``RATE``).
    ``args`` holds the numbers inside the parentheses, in order, as floats --
    the table mixes integers (distances, buff ids) and fractions (HP), so one
    numeric type keeps the parse from deciding which a column is.
    """

    name: str
    op: str
    args: Tuple[float, ...]


@dataclass(frozen=True)
class Action:
    """One action token.  ``CHASE(n)`` is the only one the table ships."""

    name: str
    args: Tuple[float, ...]

    @property
    def skill_slot(self) -> Optional[int]:
        """A5: the slot number CHASE names, or None for any other action."""
        if self.name == "CHASE" and self.args:
            return int(self.args[0])
        return None


@dataclass(frozen=True)
class RuleLine:
    """One condition line and the action parallel to it.

    ``action`` is None when the condition column has more lines than the
    action column -- see ``parse_program`` for what that means and why it is
    not an error.
    """

    index: int
    conditions: Tuple[Condition, ...]
    action: Optional[Action]

    @property
    def is_default(self) -> bool:
        """True for the ``GO(0)`` line: no test, always taken if reached."""
        return any(c.name == "GO" for c in self.conditions)

    @property
    def is_once_per_life(self) -> bool:
        return any(c.name == DOONCE_TOKEN for c in self.conditions)


@dataclass(frozen=True)
class CombatProgram:
    """A parsed ``AI_COMBAT`` row.

    ``parallel`` records whether the two columns had the same number of lines
    AS PARSED -- it is this module's own measurement of the row in hand, not a
    copy of ``field_mob_ai_tables.AI_COMBAT_PARALLEL``, so the two can be
    compared instead of one standing in for the other.
    """

    row_id: int
    lines: Tuple[RuleLine, ...]
    parallel: bool
    ends_with_default: bool


_TOKEN_RE = re.compile(r"^([A-Z_]+)([<>]?)\(([^)]*)\)$")
_BARE_TOKEN_RE = re.compile(r"^([A-Z_]+)([<>]?)$")

# The union of the letter's vocabulary and what the shipped slice actually
# uses (module docstring, "WHAT THIS LANE MEASURED").  Value = how many
# arguments the token is allowed to carry; None = any number.
CONDITION_VOCABULARY: Dict[str, Optional[int]] = {
    "BUFF_I": None,
    "BUFF_ENEMY": None,
    "RATE": 1,
    "GO": 1,
    "KD_ENEMY": 1,
    "DOONCE": 1,
    "HP_I": 1,
    "HP_ENEMY": 1,
    "HP_ALLY": 1,
    "DISTANCE_ENEMY": 1,
}

ACTION_VOCABULARY: Dict[str, Optional[int]] = {
    "CHASE": 1,
}


def _parse_args(raw: str) -> Tuple[float, ...]:
    if not raw.strip():
        return ()
    out: List[float] = []
    for part in raw.split(","):
        part = part.strip()
        try:
            out.append(float(part))
        except ValueError as exc:
            raise UnknownRuleToken(
                "non-numeric argument %r" % (part,)) from exc
    return tuple(out)


def parse_condition_token(token: str) -> Condition:
    """One ``s_CONDITOIN`` token, or ``UnknownRuleToken``."""
    token = token.strip()
    if not token:
        raise UnknownRuleToken("empty condition token")
    match = _TOKEN_RE.match(token)
    if match is None:
        bare = _BARE_TOKEN_RE.match(token)
        if bare is not None and bare.group(1) in CONDITION_VOCABULARY:
            # A token spelled without parentheses.  The shipped slice has
            # none, so this stays a declared shape rather than a guess: it
            # parses as the same name with no arguments.
            return Condition(bare.group(1), bare.group(2), ())
        raise UnknownRuleToken("unparseable condition token %r" % (token,))
    name, op, raw = match.group(1), match.group(2), match.group(3)
    if name not in CONDITION_VOCABULARY:
        raise UnknownRuleToken("unknown condition %r" % (name,))
    args = _parse_args(raw)
    expected = CONDITION_VOCABULARY[name]
    if expected is not None and len(args) != expected:
        raise UnknownRuleToken(
            "condition %s takes %d argument(s), got %d"
            % (name, expected, len(args)))
    return Condition(name, op, args)


def parse_action_token(token: str) -> Action:
    """One ``s_ACTION`` token, or ``UnknownRuleToken``."""
    token = token.strip()
    if not token:
        raise UnknownRuleToken("empty action token")
    match = _TOKEN_RE.match(token)
    if match is None:
        raise UnknownRuleToken("unparseable action token %r" % (token,))
    name, _op, raw = match.group(1), match.group(2), match.group(3)
    if name not in ACTION_VOCABULARY:
        raise UnknownRuleToken("unknown action %r" % (name,))
    args = _parse_args(raw)
    expected = ACTION_VOCABULARY[name]
    if expected is not None and len(args) != expected:
        raise UnknownRuleToken(
            "action %s takes %d argument(s), got %d"
            % (name, expected, len(args)))
    return Action(name, args)


def _split_lines(column: str) -> List[str]:
    return [line for line in column.split(RULE_SEPARATOR) if line.strip()]


def parse_program(row_id: int, condition_column: str,
                  action_column: str) -> CombatProgram:
    """Parse one ``AI_COMBAT`` row into lines the evaluator can walk.

    THE TWO SHAPES THE LETTER NAMES, AND WHAT THIS DOES WITH THEM.

    A row whose columns are NOT parallel is not an error and is not dropped.
    Lines are zipped by position; a condition line with no action parallel to
    it keeps ``action=None`` and the evaluator treats reaching it as "this
    monster does nothing this tick" rather than falling through to a later
    line that belongs to a different condition.  Falling through would hand
    the monster an action the table never put on that line, which is the one
    outcome worse than doing nothing.  ``parallel`` records the fact so a
    caller can refuse the row instead if it wants to.

    A row that does NOT end with ``GO(0)`` is also kept.  Its
    ``ends_with_default`` is False, and ``choose`` returns None when no line
    matches -- an AI with no default is an AI that sometimes has nothing to
    do, which is what the absence of a default means.
    """
    condition_lines = _split_lines(condition_column)
    action_lines = _split_lines(action_column)
    lines: List[RuleLine] = []
    for index, raw_conditions in enumerate(condition_lines):
        conditions = tuple(
            parse_condition_token(tok)
            for tok in raw_conditions.split(";") if tok.strip()
        )
        action: Optional[Action] = None
        if index < len(action_lines):
            action_tokens = [
                tok for tok in action_lines[index].split(";") if tok.strip()
            ]
            if len(action_tokens) > 1:
                raise UnknownRuleToken(
                    "row %s line %d has %d actions; one line is one action"
                    % (row_id, index, len(action_tokens)))
            if action_tokens:
                action = parse_action_token(action_tokens[0])
        lines.append(RuleLine(index, conditions, action))
    ends_with_default = bool(lines) and lines[-1].is_default
    return CombatProgram(
        row_id=row_id,
        lines=tuple(lines),
        parallel=len(condition_lines) == len(action_lines),
        ends_with_default=ends_with_default,
    )


def parse_all(rows: Dict[int, Tuple[str, str]]) -> Dict[int, CombatProgram]:
    """Parse every row, or raise on the first token the vocabulary misses.

    The decision letter's acceptance test is "zero unparsed tokens over every
    shipped row", so this raises rather than reporting a count: a count that
    nobody reads is a count that can grow.
    """
    return {
        row_id: parse_program(row_id, columns[0], columns[1])
        for row_id, columns in sorted(rows.items())
    }


# ---------------------------------------------------------------------------
# Evaluation.  One tick asks one question: which line fires?


@dataclass
class EvalState:
    """Everything a condition can ask about, and nothing it cannot.

    Distances are in the world units the placements use -- the same units
    ``field_mob_ai_tables`` documents ``n_AGGRO`` in.  HP values are
    FRACTIONS in ``[0, 1]``, because the table compares them against 0.5 and
    0.7; a caller holding raw HP must divide before it gets here.

    ``doonce_fired`` is the caller's memory of A3.  It is mutated by
    ``choose`` when a once-per-life line fires, so a caller that keeps one
    EvalState per monster gets the once-per-life rule for free, and a caller
    that builds a fresh one every tick gets a line that fires every tick --
    which is why this is documented at the field rather than in prose.
    """

    distance_enemy: float = 0.0
    hp_self: float = 1.0
    hp_enemy: float = 1.0
    hp_ally: float = 1.0
    enemy_knocked_down: bool = False
    buffs_self: FrozenSet[int] = frozenset()
    buffs_enemy: FrozenSet[int] = frozenset()
    doonce_fired: set = field(default_factory=set)


def _compare(op: str, left: float, right: float) -> bool:
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    raise UnknownRuleToken("condition needs < or >, got %r" % (op,))


def _condition_holds(condition: Condition, state: EvalState,
                     roll: Callable[[], float]) -> bool:
    name = condition.name
    if name == "GO":
        return True
    if name == DOONCE_TOKEN:
        # Handled by choose(), which owns the per-line memory.  As a
        # condition on its own it never blocks the line.
        return True
    if name == "RATE":
        return roll() * 100.0 < condition.args[0]
    if name == "KD_ENEMY":
        # KD_ENEMY(1) asks for a knocked-down enemy; KD_ENEMY(0) for one that
        # is not.  The shipped slice only ever writes 1.
        return state.enemy_knocked_down == bool(condition.args[0])
    if name == "DISTANCE_ENEMY":
        return _compare(condition.op, state.distance_enemy, condition.args[0])
    if name == "HP_I":
        return _compare(condition.op, state.hp_self, condition.args[0])
    if name == "HP_ENEMY":
        return _compare(condition.op, state.hp_enemy, condition.args[0])
    if name == "HP_ALLY":
        return _compare(condition.op, state.hp_ally, condition.args[0])
    if name == "BUFF_I":
        # A4: presence of the buff on the monster itself.
        return int(condition.args[0]) in state.buffs_self
    if name == "BUFF_ENEMY":
        return int(condition.args[0]) in state.buffs_enemy
    raise UnknownRuleToken("no evaluation for condition %r" % (name,))


def choose(program: CombatProgram, state: EvalState,
           rng: Optional[random.Random] = None) -> Optional[RuleLine]:
    """The first line whose conditions all hold, or None.

    Lines are walked in table order and the FIRST match wins, which is what
    makes ``GO(0)`` at the bottom a default rather than an override.

    ``rng`` is required in spirit and optional in signature: RATE without a
    caller-owned generator would draw from the module-global stream, which is
    the thing this house refuses by name elsewhere.  A program with no RATE
    token never touches it, so demanding one for those rows would be a lie
    about what the row needs; a program WITH a RATE token and no rng raises.
    """
    for line in program.lines:
        if line.is_once_per_life:
            key = (program.row_id, line.index)
            if key in state.doonce_fired:
                continue

        def roll() -> float:
            if rng is None:
                raise UnknownRuleToken(
                    "row %s line %d rolls RATE and no rng was given"
                    % (program.row_id, line.index))
            return rng.random()

        if all(_condition_holds(c, state, roll) for c in line.conditions):
            if line.is_once_per_life:
                state.doonce_fired.add((program.row_id, line.index))
            return line
    return None


# ---------------------------------------------------------------------------
# The wander script.


@dataclass(frozen=True)
class WanderStep:
    """One ``IDLE;a;b`` or ``RUN;c;d`` step.

    THE UNITS ARE NOT KNOWN.  The decision letter says so, and this lane did
    not find a measurement that settles them.  This module reads a and b as
    the INCLUSIVE BOUNDS OF A DURATION IN SECONDS -- one reading, chosen
    because every shipped pair is small and ascending (9..15, 10..30, 0..1,
    1..2), which reads naturally as "idle between 9 and 15 seconds" and
    unnaturally as a distance for a monster that is standing still.  It is a
    reading, not a fact.  ``WANDER_UNIT_SECONDS`` is the one constant to
    change if a measurement contradicts it; nothing else in the module
    multiplies these numbers.
    """

    mode: str
    low: float
    high: float


WANDER_UNIT_SECONDS = 1.0

_WANDER_MODES = ("IDLE", "RUN")


@dataclass(frozen=True)
class WanderScript:
    steps: Tuple[WanderStep, ...]


def parse_wander(column: str) -> WanderScript:
    """Read ``s_WANDER`` (``IDLE;9;15\\nRUN;0;1``) into ordered steps."""
    steps: List[WanderStep] = []
    for raw in _split_lines(column):
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        if len(parts) != 3:
            raise UnknownRuleToken("wander step %r is not MODE;a;b" % (raw,))
        mode = parts[0].upper()
        if mode not in _WANDER_MODES:
            raise UnknownRuleToken("unknown wander mode %r" % (parts[0],))
        try:
            low, high = float(parts[1]), float(parts[2])
        except ValueError as exc:
            raise UnknownRuleToken(
                "wander step %r has non-numeric bounds" % (raw,)) from exc
        if high < low:
            raise UnknownRuleToken(
                "wander step %r has high < low" % (raw,))
        steps.append(WanderStep(mode, low, high))
    if not steps:
        raise UnknownRuleToken("empty wander script")
    return WanderScript(tuple(steps))


def wander_plan(script: WanderScript, rng: random.Random,
                cycles: int = 1) -> Tuple[Tuple[str, float], ...]:
    """``(mode, seconds)`` pairs for ``cycles`` passes through the script.

    The steps repeat in order, which is what makes the two-step scripts the
    table ships ("idle a while, run a while") a loop rather than a one-shot.
    Duration is drawn per step, inside the step's own bounds, from the
    caller's generator.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1")
    out: List[Tuple[str, float]] = []
    for _ in range(cycles):
        for step in script.steps:
            seconds = rng.uniform(step.low, step.high) * WANDER_UNIT_SECONDS
            out.append((step.mode, seconds))
    return tuple(out)
