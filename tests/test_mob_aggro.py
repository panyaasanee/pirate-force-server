"""MOB-AGGRO-001 -- the server-side threat table and decision tick, pure logic.

What this file proves, and where the proof stops:

  * DETERMINISM: no randomness exists in the module; the same profile + state
    + observation produce the identical TickResult on repeated calls, and a
    scripted four-tick fight renders one pinned list of ASCII lines;
  * every REFUSAL fires by name and nothing is silently clamped or coerced --
    non-numeric values (string radius, bool range, string position), non-
    finite values, non-positive radii, a leash smaller than the aggro radius,
    a home radius outside the leash, an attack range outside the aggro
    radius, a cadence below one, a non-positive identity, a damage outside
    signed 32-bit range, a non-int hp, a non-bool alive, a duplicate player
    identity, and a rehydrated state with an unknown phase or a malformed
    threat table;
  * the declared no-ops: a NON-NEGATIVE damage (meaning unknown, MISS
    included) adds no threat, and RETURN/DEAD phases absorb no threat;
  * the DISTANCE boundaries are inclusive and 3D: a player exactly ON the
    aggro radius is inside, one epsilon beyond is outside;
  * the THREAT rules: abs() of a signed damage, saturation at i32 max, MISS
    (damage 0) adds nothing, the proximity floor is 1 and never accumulates;
  * the SELECTION rules: highest threat wins, ties break to the LOWEST
    identity, selection is re-evaluated every tick, and an acquired attacker
    is kept even outside the aggro radius until leash or forgiveness;
  * the CADENCE: attacks fire only inside attack range, every N ticks, and an
    approach tick still advances the counter so arrival can attack at once;
  * the LEASH: breaking it clears all threat and yields RETURN intents until
    the mob is back inside the home radius, which yields IDLE that tick;
  * DEATH is absorbing and clears the table; damage folded into a dead mob's
    state is a no-op;
  * PURITY: frozen inputs are never mutated;
  * CONTAINMENT: the module imports only stdlib, has no import-time side
    effects, ~~is imported by no other module in ``src/``~~, is pure ASCII and
    cp874-safe, and declares ~~production_allowed False~~,
    ~~dispatch-reachable False~~ and attack-intent deliverable False.
    STRUCK IN PLACE, round `1tz15e` (2026-09-03).  THREE clauses, not two.
    The first two have been false since COO-DECISION 2026-08-26T04:02+07:00
    promoted this lane - ``production_allowed`` is True and two src/ modules
    import it by name.  The third was struck LATER IN THE SAME ROUND, after a
    pf-adversary pass caught this file re-certifying it as "still true" while
    ``runtime.py:4466`` calls ``mob_ai_control.damage_step`` from
    ``_dispatch_mob_combat``, which ``_dispatch_with_lanes`` calls at
    ``runtime.py:10440`` and which ``dispatch`` reaches through it - a THREE
    hop chain, corrected here after a second pf-adversary pass caught the
    first draft of this paragraph calling it two - and ``damage_step`` folds
    through ``mob_aggro.apply_damage_threat``.
    ``docs/FUNCTIONAL_COVERAGE.json`` (row ``mob_aggro_and_server_ai``) has
    said exactly that since 2026-08-26: "what changed is reachability, not
    observability".  The lesson is the round's own subject turned on itself -
    striking two stale claims out of a paragraph is not the same as walking
    the paragraph, and the walk stopped one clause short.
    What is still true and still proved: stdlib-only imports, no import-time
    side effects, ASCII/cp874, and attack intent NOT deliverable - nothing
    this lane decides reaches a client.
    ROUND `a7k5gy` (2026-09-03): the struck ``dispatch-reachable`` clause was
    ONE WORD FOR TWO FACTS, and COO-DECISION 2026-09-03T16:47+07:00 item 1
    split it.  ``MOB_AGGRO_DAMAGE_FOLD_REACHABLE`` (True) is the fold reached
    on every accepted hit; ``MOB_AGGRO_TICK_REACHABLE`` (False today) is the
    decision loop, gated shut at runtime.py:5887 by an argument that resolves
    to a key that does not exist.  Both are derived, neither is pinned.

NOT proven here: anything about a client, a wire, or a database.  The rules
are OUR design (the original server is unrecoverable forever); the attack
decision is named UNDELIVERABLE because Door B (round-98 draft) has no proven
server->client transport, and no emitter for any intent exists anywhere.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_aggro as ma  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_b_mob_ai_tick)

MODULE_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "mob_aggro.py"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"

ORIGIN = (0.0, 0.0, 0.0)


def _names_bound_to_an_importer(tree) -> set:
    """Local names in ``tree`` that are bound to importlib's import_module.

    ``from importlib import import_module as _load`` then ``_load("...")`` is
    an import.  pf-adversary shipped exactly that into mob_combat and the
    whole 8,692-test suite stayed green, so the alias is resolved rather than
    the callee name being matched literally.
    """
    bound = {"__import__", "import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    bound.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            value = node.value
            named = ""
            if isinstance(value, ast.Name):
                named = value.id
            elif isinstance(value, ast.Attribute):
                named = value.attr
            if named in ("import_module", "__import__"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        bound.add(target.id)
    return bound


def _is_this_lane(dotted: str) -> bool:
    """True only for THIS module, not for a sibling whose name starts alike.

    ``"mob_aggro" in name`` would accuse a future ``mob_aggro_tables`` of
    being the forbidden edge -- the false-accusation half of a card matters
    as much as the missed-detection half.
    """
    return dotted == "mob_aggro" or dotted.endswith(".mob_aggro")


def module_imports_mob_aggro(source: str) -> bool:
    """True when ``source`` binds this lane by any import form it can see.

    Round `1tz15e`.  The scan this replaces read ``ast.Import`` and
    ``ast.ImportFrom`` only, and a pf-adversary pass proved that is not the
    same question: ``__import__("pirateforce_foundation.mob_aggro",
    fromlist=["x"])`` is a live import, is invisible to those two node types,
    and is EXACTLY the arrangement COO-DECISION 2026-08-26T04:02+07:00 called
    the hole -- a production module reaching this lane by a route no scan of
    ``src/`` can see.  A whole suite stayed green with one in ``mob_combat``.

    WHAT IT SEES: plain imports, ``__import__``/``import_module`` with a
    literal, and those two under a local alias.
    WHAT IT DOES NOT SEE, stated rather than hidden (pf-adversary measured
    each one): a computed module name, ``sys.modules[...]`` lookup, an edge
    through a THIRD module (``mob_ai_control.mob_aggro.<attr>``), and an
    import under ``if TYPE_CHECKING`` counts as a real one.  This is a card
    against an edge somebody writes to keep the code tidy, not against one
    written to get past the card.  ``test_the_import_scan_sees_the_forms_it_claims``
    is the guard on every row of that list.
    """
    tree = ast.parse(source)
    importer_names = _names_bound_to_an_importer(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names = [base] + [base + "." + alias.name for alias in node.names]
        elif isinstance(node, ast.Call):
            callee = node.func
            called = ""
            if isinstance(callee, ast.Name):
                called = callee.id
            elif isinstance(callee, ast.Attribute):
                called = callee.attr
            if called not in importer_names:
                continue
            names = [
                argument.value for argument in node.args
                if isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)]
        else:
            continue
        if any(_is_this_lane(name) for name in names):
            return True
    return False


def functions_that_touch_this_lane(source: str) -> set:
    """Names of top-level functions in ``source`` whose own body uses the lane.

    This is what separates "dispatch reaches a module that happens to import
    mob_aggro" from "dispatch reaches a function that USES it".
    """
    touching = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        used = {
            inner.id for inner in ast.walk(node)
            if isinstance(inner, ast.Name)}
        used |= {
            inner.attr for inner in ast.walk(node)
            if isinstance(inner, ast.Attribute)}
        if "mob_aggro" in used:
            touching.add(node.name)
    return touching


def module_aliases(tree) -> dict:
    """Local name -> module stem, for every module imported in ``tree``.

    Without this the walk below is a tripwire on SPELLING: pf-adversary
    renamed ``mob_ai_control`` to ``_ctl`` in runtime.py -- a behaviour-neutral
    alias -- and the card declared the lane unreachable and went red on a fact
    that had not changed.
    """
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                stem = alias.name.rsplit(".", 1)[-1]
                aliases[alias.asname or stem] = stem
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
    return aliases


def _calls_the_tick(nodes, aliases) -> bool:
    """True when any statement in ``nodes`` calls this lane's tick entry."""
    for statement in nodes:
        for inner in ast.walk(statement):
            if not isinstance(inner, ast.Call):
                continue
            callee = inner.func
            if not isinstance(callee, ast.Attribute):
                continue
            if callee.attr != "maybe_tick":
                continue
            if not isinstance(callee.value, ast.Name):
                continue
            stem = aliases.get(callee.value.id, callee.value.id)
            if stem.rsplit(".", 1)[-1] == "lane_b_mob_ai_tick":
                return True
    return False


def methods_reachable_from_dispatch(runtime_tree) -> set:
    """Method names ``dispatch`` reaches through ``self.<method>()``.

    pf-adversary D6 of round `a7k5gy`: the fold card walks FROM ``dispatch``
    before it will call anything reachable, and the tick card did not -- it
    accepted an ``if`` anywhere in the module.  Failure scenario it measured:
    the chief lands ticket 1648 and in the same commit moves the block into a
    helper he forgets to call from ``dispatch``.  The tick card would then go
    red demanding ``True``, this lane would dutifully publish
    ``mob_aggro_tick_reachable: true`` into the shipped pin, and the tick would
    still never run.  A card that pushes its own lane into an unmeasured claim
    is worse than no card.  Same standard for both constants now.
    """
    self_calls = {}
    for node in ast.walk(runtime_tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        mine = set()
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and isinstance(inner.func.value, ast.Name)
                    and inner.func.value.id == "self"):
                mine.add(inner.func.attr)
        self_calls.setdefault(node.name, set()).update(mine)
    seen = set()
    frontier = ["dispatch"]
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        frontier.extend(self_calls.get(name, ()))
    return seen


def _positive_conjuncts(test) -> list:
    """The operands of ``test`` that must ALL be truthy for the branch to run.

    pf-adversary D1 of round `a7k5gy`, and it was severe: the first draft
    searched ``ast.walk(node.test)`` for the gate call and never looked at how
    its RESULT was used.  Three edits at runtime.py:5888 -- ``not gate(...)``,
    ``gate(...) is False``, ``gate(...) or True`` -- each make the tick run on
    every frame while the card stays green and the shipped pin goes on saying
    the tick is refused.  (They died, but in LANE-A's census card by
    side-effect, which is a stranger holding the door shut, not a guard.)
    A gate reached through ``not``, a comparison, or an ``or`` is therefore not
    a gate this card will read: it is returned nowhere, and the caller raises.
    """
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        found = []
        for value in test.values:
            found.extend(_positive_conjuncts(value))
        return found
    return [test]


def _dotted(node) -> str:
    """``a.b.c`` for an attribute chain of plain names, else ``""``."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def tick_gate_argument(runtime_tree):
    """The value runtime.py's tick gate really hands ``module_production_allowed``.

    Round `a7k5gy`, COO-DECISION 2026-09-03T16:47+07:00 item 1: the tick bool
    must be DERIVED from the real gate, calling it with the same argument the
    call site uses, READ OUT OF THE AST rather than retyped here.  Retyping it
    is precisely how the bug this card exists for survived: the string lived in
    three files that all agreed with each other and none of which asked the
    gate.

    Returns ``(value, how)`` where ``how`` names the FORM found, so a failure
    message can say whether the call site passes a literal or the module's own
    ``MODULE_NAME``.

    WHAT IT ACCEPTS, widened after pf-adversary D2 measured three of the
    chief's plausible correct fixes going red with a message that accused him
    of removing wiring he had just repaired: the gate called as
    ``lane_hooks.module_production_allowed(...)`` or bare after a ``from``
    import; the argument passed positionally or as ``module_name=``; and the
    attribute written ``lane_b_mob_ai_tick.MODULE_NAME`` or
    ``lane_hooks.lane_b_mob_ai_tick.MODULE_NAME``.

    Raises ``AssertionError`` when the call site cannot be found, or is gated
    through a negation/comparison/``or`` (see ``_positive_conjuncts``), or
    passes an argument this card cannot resolve.  Silence is the one answer
    that must not be available: a card that quietly finds nothing is no card.
    """
    aliases = module_aliases(runtime_tree)
    reachable = methods_reachable_from_dispatch(runtime_tree)
    saw_the_branch = False
    for owner in ast.walk(runtime_tree):
        if not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if owner.name not in reachable:
            continue
        for node in ast.walk(owner):
            if not isinstance(node, ast.If):
                continue
            if not _calls_the_tick(node.body, aliases):
                continue
            saw_the_branch = True
            for operand in _positive_conjuncts(node.test):
                if not isinstance(operand, ast.Call):
                    continue
                callee = operand.func
                if isinstance(callee, ast.Attribute):
                    called = callee.attr
                elif isinstance(callee, ast.Name):
                    called = callee.id
                else:
                    continue
                if called != "module_production_allowed":
                    continue
                spelled = operand.args[0] if operand.args else None
                for keyword in operand.keywords:
                    if keyword.arg == "module_name":
                        spelled = keyword.value
                if spelled is None:
                    continue
                if isinstance(spelled, ast.Constant) and isinstance(
                        spelled.value, str):
                    return spelled.value, "a hand-typed string literal"
                dotted = _dotted(spelled)
                if dotted:
                    head, _, attribute = dotted.rpartition(".")
                    stem = aliases.get(head.split(".")[0], head.split(".")[0])
                    if (head.rsplit(".", 1)[-1] == "lane_b_mob_ai_tick"
                            or stem.rsplit(".", 1)[-1] == "lane_b_mob_ai_tick"):
                        return (getattr(lane_b_mob_ai_tick, attribute),
                                "lane_b_mob_ai_tick.%s" % attribute)
                raise AssertionError(
                    "runtime.py gates the tick on an argument this card "
                    "cannot resolve (%s): teach it the new form, do not "
                    "delete the card" % ast.dump(spelled))
            raise AssertionError(
                "runtime.py still branches on module_production_allowed "
                "around the tick, but the gate is no longer a bare positive "
                "conjunct of that branch's condition -- it is behind a not, a "
                "comparison, or an or.  That inverts what the gate MEANS "
                "without changing what it ANSWERS, which is the one shape "
                "this card cannot read and the one shape that would let the "
                "tick run while the shipped pin says it is refused.")
    raise AssertionError(
        "this card found no branch that calls lane_b_mob_ai_tick.maybe_tick "
        "inside a method runtime.py's dispatch() reaches. THIS IS NOT AN "
        "ACCUSATION THAT THE WIRING IS BROKEN: it is equally what a correct "
        "repair looks like if the branch moved somewhere this card does not "
        "walk. %s Either way the tick's reachability is no longer measured, "
        "so come and teach the card the new shape."
        % ("The branch exists but is gated in a shape this card rejects."
           if saw_the_branch else
           "No such branch was found at all."))


def profile(**overrides):
    values = dict(
        aggro_radius=10.0,
        leash_radius=30.0,
        home_radius=2.0,
        attack_range=3.0,
        attack_cadence_ticks=2,
        # Every test written before 2026-08-26 assumed a monster that charges,
        # because that was the only monster the profile could express.  The
        # default keeps those tests saying what they were written to say; the
        # tests that the mined n_OFFESIVE column added pass offensive=False.
        offensive=True,
    )
    values.update(overrides)
    return ma.MobAiProfile(**values)


def player(identity, position, alive=True):
    return ma.PlayerObservation(identity=identity, position=position,
                                alive=alive)


def observe(mob_position=ORIGIN, hp=100, players=()):
    return ma.MobObservation(position=mob_position, hp=hp,
                             players=tuple(players))


class ProfileContractTests(unittest.TestCase):
    def test_a_coherent_profile_builds_and_freezes_floats(self):
        built = profile()
        self.assertEqual(built.aggro_radius, 10.0)
        self.assertIsInstance(built.aggro_radius, float)

    def test_every_profile_refusal_fires_by_name(self):
        cases = [
            (dict(aggro_radius=float("nan")),
             ma.REFUSE_PROFILE_VALUE_NOT_FINITE),
            (dict(leash_radius=float("inf")),
             ma.REFUSE_PROFILE_VALUE_NOT_FINITE),
            # A ZERO AGGRO RADIUS USED TO BE REFUSED HERE.  It is a real row:
            # ~~ten~~ six of the thirteen bg0001 rows have n_AGGRO = 0 as of
            # round szdkgs (the four dummies carry 3000).  The case
            # is kept, inverted, rather than deleted.
            (dict(aggro_radius=-1.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(home_radius=0.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(attack_range=-1.0), ma.REFUSE_PROFILE_RADIUS_NOT_POSITIVE),
            (dict(offensive=1), ma.REFUSE_OFFENSIVE_NOT_BOOL),
            (dict(offensive=None), ma.REFUSE_OFFENSIVE_NOT_BOOL),
            (dict(leash_radius=5.0),
             ma.REFUSE_PROFILE_LEASH_SMALLER_THAN_AGGRO),
            (dict(home_radius=31.0), ma.REFUSE_PROFILE_HOME_OUTSIDE_LEASH),
            # THE BOUND MOVED from the aggro radius to the leash, so 11.0 -
            # outside the 10.0 aggro radius, inside the 30.0 leash - is now
            # ACCEPTED, and only a range outside the LEASH is refused.  A
            # monster you hit must be able to hit back, and a non-offensive
            # monster (aggro radius 0) is not an unarmed one.
            (dict(attack_range=31.0),
             ma.REFUSE_PROFILE_ATTACK_RANGE_OUTSIDE_LEASH),
            (dict(attack_cadence_ticks=0),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(attack_cadence_ticks=True),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(attack_cadence_ticks=2.0),
             ma.REFUSE_PROFILE_CADENCE_NOT_POSITIVE),
            (dict(aggro_radius="10"), ma.REFUSE_VALUE_NOT_NUMERIC),
            (dict(attack_range=True), ma.REFUSE_VALUE_NOT_NUMERIC),
        ]
        for overrides, reason in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    profile(**overrides)
                self.assertEqual(caught.exception.reason, reason)

    def test_every_refusal_reason_is_registered(self):
        for overrides in (dict(aggro_radius=-1.0), dict(leash_radius=5.0)):
            with self.assertRaises(ma.MobAiContractError) as caught:
                profile(**overrides)
            self.assertIn(caught.exception.reason,
                          ma.MOB_AGGRO_REFUSAL_REASONS)


class ObservationContractTests(unittest.TestCase):
    def test_player_identity_must_be_a_positive_int(self):
        for bad in (0, -1, True, "7"):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    player(bad, (1.0, 0.0, 0.0))
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_positions_must_be_finite_triples(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, (float("nan"), 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_POSITION_NOT_FINITE)
        with self.assertRaises(ma.MobAiContractError):
            observe(mob_position=(0.0, float("inf"), 0.0))
        with self.assertRaises(ma.MobAiContractError):
            ma.initial_state((0.0, 0.0))

    def test_a_string_position_component_is_refused_by_name_not_coerced(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, ("1.0", 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_VALUE_NOT_NUMERIC)

    def test_alive_must_be_an_actual_bool(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            player(7, (1.0, 0.0, 0.0), alive="false")
        self.assertEqual(caught.exception.reason, ma.REFUSE_ALIVE_NOT_BOOL)

    def test_hp_must_be_an_int_so_nan_hp_cannot_slip_through(self):
        for bad in ("0", 0.0, float("nan"), True):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    observe(hp=bad)
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_HP_NOT_INT)

    def test_duplicate_player_identities_are_refused_by_name(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            observe(players=[player(7, (2.0, 0.0, 0.0)),
                             player(7, (9000.0, 0.0, 0.0))])
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_DUPLICATE_PLAYER_IDENTITY)


class StateContractTests(unittest.TestCase):
    def test_a_rehydrated_state_is_validated_like_everything_else(self):
        cases = [
            (dict(phase="combat"), ma.REFUSE_PHASE_UNKNOWN),
            (dict(leash_origin=(float("nan"), 0.0, 0.0)),
             ma.REFUSE_POSITION_NOT_FINITE),
            (dict(threat=((7, 0),)), ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((7, ma.THREAT_MAX + 1),)),
             ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((9, 1), (7, 1))), ma.REFUSE_STATE_MALFORMED),
            (dict(threat=((7, 1), (7, 2))), ma.REFUSE_STATE_MALFORMED),
            (dict(target_identity=0), ma.REFUSE_STATE_MALFORMED),
            (dict(ticks_since_attack=-1), ma.REFUSE_STATE_MALFORMED),
        ]
        base = dict(phase=ma.PHASE_IDLE, leash_origin=ORIGIN, threat=(),
                    target_identity=None, ticks_since_attack=0)
        for overrides, reason in cases:
            with self.subTest(overrides=overrides):
                values = dict(base)
                values.update(overrides)
                with self.assertRaises(ma.MobAiContractError) as caught:
                    ma.MobAiState(**values)
                self.assertEqual(caught.exception.reason, reason)

    def test_a_well_formed_hand_built_state_constructs_and_describes_ascii(self):
        state = ma.MobAiState(phase=ma.PHASE_AGGRO, leash_origin=ORIGIN,
                              threat=((7, 63),), target_identity=7,
                              ticks_since_attack=1)
        result = ma.TickResult(state, ma.MobAiIntent(ma.INTENT_NONE, None))
        for line in ma.describe_mob_ai(result):
            line.encode("ascii")
            line.encode("cp874")


class ThreatTests(unittest.TestCase):
    def setUp(self):
        self.state = ma.initial_state(ORIGIN)

    def test_a_negative_damage_model_hit_adds_its_absolute_value(self):
        folded = ma.apply_damage_threat(self.state, 7, -63)
        self.assertEqual(folded.threat, ((7, 63),))

    def test_threat_accumulates_across_hits(self):
        folded = ma.apply_damage_threat(self.state, 7, -63)
        folded = ma.apply_damage_threat(folded, 7, -379)
        self.assertEqual(folded.threat, ((7, 442),))

    def test_threat_saturates_at_i32_max(self):
        folded = ma.apply_damage_threat(self.state, 7, -ma.DAMAGE_I32_MAX)
        folded = ma.apply_damage_threat(folded, 7, -ma.DAMAGE_I32_MAX)
        self.assertEqual(folded.threat, ((7, ma.THREAT_MAX),))

    def test_a_miss_adds_no_threat_and_is_not_an_error(self):
        folded = ma.apply_damage_threat(self.state, 7, 0)
        self.assertEqual(folded.threat, ())

    def test_a_positive_value_adds_no_threat_its_meaning_is_unknown(self):
        folded = ma.apply_damage_threat(self.state, 7, 500)
        self.assertEqual(folded.threat, ())

    def test_a_returning_mob_absorbs_no_damage_threat(self):
        returning = ma.tick(profile(), self.state,
                            observe(mob_position=(31.0, 0.0, 0.0))).state
        self.assertEqual(returning.phase, ma.PHASE_RETURN)
        folded = ma.apply_damage_threat(returning, 7, -5000)
        self.assertEqual(folded.threat, ())
        self.assertEqual(folded.phase, ma.PHASE_RETURN)

    def test_damage_outside_i32_is_refused_by_name(self):
        for bad in (ma.DAMAGE_I32_MAX + 1, ma.DAMAGE_I32_MIN - 1, 1.5, False):
            with self.subTest(bad=bad):
                with self.assertRaises(ma.MobAiContractError) as caught:
                    ma.apply_damage_threat(self.state, 7, bad)
                self.assertEqual(caught.exception.reason,
                                 ma.REFUSE_DAMAGE_OUTSIDE_I32)

    def test_attacker_identity_is_validated(self):
        with self.assertRaises(ma.MobAiContractError) as caught:
            ma.apply_damage_threat(self.state, 0, -63)
        self.assertEqual(caught.exception.reason,
                         ma.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_the_input_state_is_never_mutated(self):
        before = self.state.threat
        ma.apply_damage_threat(self.state, 7, -63)
        self.assertEqual(self.state.threat, before)


class AcquisitionTests(unittest.TestCase):
    def test_a_player_exactly_on_the_aggro_radius_is_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (10.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)
        self.assertEqual(result.state.threat, ((7, ma.PROXIMITY_THREAT),))

    def test_a_player_just_beyond_the_aggro_radius_is_not_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (10.000001, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertIsNone(result.state.target_identity)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_the_distance_is_3d(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (6.0, 6.0, 6.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_dead_player_inside_the_radius_is_not_acquired(self):
        result = ma.tick(profile(), ma.initial_state(ORIGIN),
                         observe(players=[player(7, (5.0, 0.0, 0.0),
                                                 alive=False)]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_non_offensive_mob_acquires_nobody_at_any_distance(self):
        # THE FLAG AND THE RADIUS ARE DELIBERATELY DECORRELATED HERE.  In every
        # profile the roster can build they agree, so an adversarial mutation
        # that replaced `if profile.offensive:` with `if aggro_radius > 0` left
        # the WHOLE SUITE green - the field was behaviourally indistinguishable
        # from the thing it was added to be distinguishable from.  These two
        # cases are the only place in the repo that can tell them apart.
        passive = profile(offensive=False, aggro_radius=10.0)
        for offset in (0.0, 1.0, 5.0, 10.0):
            with self.subTest(offset=offset):
                result = ma.tick(passive, ma.initial_state(ORIGIN), observe(
                    players=[player(7, (offset, 0.0, 0.0))]))
                self.assertEqual(result.state.phase, ma.PHASE_IDLE)
                self.assertEqual(result.state.threat, ())
                self.assertIsNone(result.state.target_identity)

    def test_an_offensive_mob_with_a_zero_radius_acquires_nobody_either(self):
        # The other half of the same decorrelation: a zero radius must not
        # admit a player standing exactly on the monster.  It does not, and
        # this is the case that proves _within's inclusive boundary is not the
        # thing keeping the passive monsters passive.
        charging_but_blind = profile(offensive=True, aggro_radius=0.0)
        result = ma.tick(charging_but_blind, ma.initial_state(ORIGIN), observe(
            players=[player(7, ORIGIN)]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        # ...and with the flag off, the identical observation acquires nobody.
        blind_and_passive = profile(offensive=False, aggro_radius=0.0)
        result = ma.tick(blind_and_passive, ma.initial_state(ORIGIN), observe(
            players=[player(7, ORIGIN)]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)

    def test_a_non_offensive_mob_that_is_hit_still_fights_back(self):
        passive = profile(offensive=False, aggro_radius=0.0)
        pulled = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -50)
        result = ma.tick(passive, pulled, observe(
            players=[player(7, (1.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)

    def test_a_saturating_fold_returns_the_very_same_state_object(self):
        # Two threat-reporting predicates exist in this project, one comparing
        # by identity (mob_combat.threat_was_recorded) and one by value
        # (mob_ai_control's step).  A hit on a row already at THREAT_MAX used
        # to build a NEW state EQUAL to the old, so the two answered
        # oppositely about the same fold and the console line named three
        # causes, none of which applied.
        saturated = ma.apply_damage_threat(
            ma.initial_state(ORIGIN), 7, -ma.THREAT_MAX)
        self.assertEqual(saturated.threat, ((7, ma.THREAT_MAX),))
        again = ma.apply_damage_threat(saturated, 7, -1)
        self.assertIs(again, saturated)
        self.assertEqual(again, saturated)

    def test_the_proximity_floor_never_accumulates(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (5.0, 0.0, 0.0))])
        for _ in range(3):
            state = ma.tick(profile(), state, snapshot).state
        self.assertEqual(state.threat, ((7, ma.PROXIMITY_THREAT),))


class SelectionTests(unittest.TestCase):
    def test_higher_damage_pulls_aggro(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 7, -63)
        state = ma.apply_damage_threat(state, 9, -379)
        snapshot = observe(players=[player(7, (5.0, 0.0, 0.0)),
                                    player(9, (6.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.target_identity, 9)

    def test_ties_break_to_the_lowest_identity(self):
        snapshot = observe(players=[player(9, (5.0, 0.0, 0.0)),
                                    player(7, (6.0, 0.0, 0.0))])
        result = ma.tick(profile(), ma.initial_state(ORIGIN), snapshot)
        self.assertEqual(result.state.target_identity, 7)

    def test_an_acquired_attacker_is_kept_outside_the_aggro_radius(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        snapshot = observe(players=[player(7, (20.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)
        self.assertEqual(result.state.target_identity, 7)
        self.assertEqual(result.intent.kind, ma.INTENT_FACE_AND_APPROACH)

    def test_an_absent_target_is_forgiven_and_the_next_takes_over(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 7, -379)
        state = ma.apply_damage_threat(state, 9, -63)
        snapshot = observe(players=[player(9, (5.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.target_identity, 9)
        self.assertEqual(result.state.threat, ((9, 63),))

    def test_everyone_gone_returns_the_mob_to_idle(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        result = ma.tick(profile(), state, observe(players=[]))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.state.ticks_since_attack, 0)


class CadenceTests(unittest.TestCase):
    def test_the_attack_fires_every_n_ticks_inside_attack_range(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        kinds = []
        for _ in range(5):
            result = ma.tick(profile(attack_cadence_ticks=2), state, snapshot)
            state = result.state
            kinds.append(result.intent.kind)
        self.assertEqual(kinds, [
            ma.INTENT_NONE,
            ma.INTENT_ATTACK_UNDELIVERABLE,
            ma.INTENT_NONE,
            ma.INTENT_ATTACK_UNDELIVERABLE,
            ma.INTENT_NONE,
        ])

    def test_cadence_one_attacks_every_tick(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        for _ in range(3):
            result = ma.tick(profile(attack_cadence_ticks=1), state, snapshot)
            state = result.state
            self.assertEqual(result.intent.kind,
                             ma.INTENT_ATTACK_UNDELIVERABLE)

    def test_an_approach_tick_advances_the_counter_so_arrival_attacks(self):
        state = ma.initial_state(ORIGIN)
        far = observe(players=[player(7, (8.0, 0.0, 0.0))])
        near = observe(players=[player(7, (2.0, 0.0, 0.0))])
        first = ma.tick(profile(attack_cadence_ticks=2), state, far)
        self.assertEqual(first.intent.kind, ma.INTENT_FACE_AND_APPROACH)
        second = ma.tick(profile(attack_cadence_ticks=2), first.state, near)
        self.assertEqual(second.intent.kind, ma.INTENT_ATTACK_UNDELIVERABLE)

    def test_the_counter_is_clamped_at_the_cadence(self):
        state = ma.initial_state(ORIGIN)
        far = observe(players=[player(7, (8.0, 0.0, 0.0))])
        for _ in range(10):
            state = ma.tick(profile(attack_cadence_ticks=3), state, far).state
        self.assertEqual(state.ticks_since_attack, 3)

    def test_the_attack_target_rides_the_intent(self):
        state = ma.initial_state(ORIGIN)
        snapshot = observe(players=[player(7, (2.0, 0.0, 0.0))])
        result = ma.tick(profile(attack_cadence_ticks=1), state, snapshot)
        self.assertEqual(result.intent.target_identity, 7)


class LeashTests(unittest.TestCase):
    def test_breaking_the_leash_clears_threat_and_returns(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -379)
        snapshot = observe(mob_position=(31.0, 0.0, 0.0),
                           players=[player(7, (30.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_RETURN)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_RETURN_TO_LEASH)

    def test_the_mob_exactly_on_the_leash_radius_holds_its_ground(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        snapshot = observe(mob_position=(30.0, 0.0, 0.0),
                           players=[player(7, (29.0, 0.0, 0.0))])
        result = ma.tick(profile(), state, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)

    def test_no_acquisition_while_returning(self):
        returning = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        snapshot = observe(mob_position=(15.0, 0.0, 0.0),
                           players=[player(7, (15.0, 1.0, 0.0))])
        result = ma.tick(profile(), returning, snapshot)
        self.assertEqual(result.state.phase, ma.PHASE_RETURN)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_RETURN_TO_LEASH)

    def test_the_return_completes_inside_the_home_radius(self):
        returning = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        result = ma.tick(profile(), returning,
                         observe(mob_position=(2.0, 0.0, 0.0)))
        self.assertEqual(result.state.phase, ma.PHASE_IDLE)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_after_coming_home_the_mob_can_acquire_again(self):
        state = ma.tick(
            profile(), ma.initial_state(ORIGIN),
            observe(mob_position=(31.0, 0.0, 0.0))).state
        state = ma.tick(profile(), state,
                        observe(mob_position=(1.0, 0.0, 0.0))).state
        result = ma.tick(profile(), state,
                         observe(players=[player(7, (5.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_AGGRO)


class DeathTests(unittest.TestCase):
    def test_hp_zero_kills_and_clears(self):
        state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
        result = ma.tick(profile(), state,
                         observe(hp=0, players=[player(7, (2.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_DEAD)
        self.assertEqual(result.state.threat, ())
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_dead_is_absorbing_even_if_hp_returns(self):
        dead = ma.tick(profile(), ma.initial_state(ORIGIN),
                       observe(hp=0)).state
        result = ma.tick(profile(), dead,
                         observe(hp=100, players=[player(7, (2.0, 0.0, 0.0))]))
        self.assertEqual(result.state.phase, ma.PHASE_DEAD)
        self.assertEqual(result.intent.kind, ma.INTENT_NONE)

    def test_damage_folded_into_a_dead_mob_is_a_no_op(self):
        dead = ma.tick(profile(), ma.initial_state(ORIGIN),
                       observe(hp=0)).state
        folded = ma.apply_damage_threat(dead, 7, -63)
        self.assertEqual(folded.threat, ())


PINNED_FIGHT = (
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=1"
    "|intent=face_and_approach|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=0"
    "|intent=attack_undeliverable|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=aggro|target=7|cadence=1"
    "|intent=none|intent_target=7",
    "threat|identity=7|value=63",
    "mob_aggro|MOB-AGGRO-001|phase=idle|target=-|cadence=0"
    "|intent=none|intent_target=-",
)


def scripted_fight():
    built = profile()
    state = ma.apply_damage_threat(ma.initial_state(ORIGIN), 7, -63)
    lines = []
    for snapshot in (
        observe(players=[player(7, (5.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0))]),
        observe(players=[player(7, (2.0, 0.0, 0.0), alive=False)]),
    ):
        result = ma.tick(built, state, snapshot)
        state = result.state
        lines.extend(ma.describe_mob_ai(result))
    return tuple(lines)


class DeterminismTests(unittest.TestCase):
    def test_the_scripted_fight_renders_the_pinned_lines(self):
        self.assertEqual(scripted_fight(), PINNED_FIGHT)

    def test_the_scripted_fight_is_identical_on_a_second_run(self):
        self.assertEqual(scripted_fight(), scripted_fight())

    def test_the_rendering_is_ascii(self):
        for line in scripted_fight():
            line.encode("ascii")

    def test_the_threat_table_representation_is_sorted_and_unique(self):
        state = ma.initial_state(ORIGIN)
        state = ma.apply_damage_threat(state, 9, -1)
        state = ma.apply_damage_threat(state, 7, -1)
        self.assertEqual(state.threat, ((7, 1), (9, 1)))


class VocabularyTests(unittest.TestCase):
    def test_the_attack_intent_says_undeliverable_in_its_name(self):
        self.assertIn("undeliverable", ma.INTENT_ATTACK_UNDELIVERABLE)
        self.assertIs(ma.ATTACK_INTENT_DELIVERABLE, False)

    def test_the_vocabularies_are_complete(self):
        self.assertEqual(ma.MOB_AGGRO_PHASES,
                         ("idle", "aggro", "return", "dead"))
        self.assertEqual(len(ma.MOB_AGGRO_INTENTS), 4)
        self.assertEqual(len(set(ma.MOB_AGGRO_REFUSAL_REASONS)),
                         len(ma.MOB_AGGRO_REFUSAL_REASONS))

    def test_a_shipped_roster_really_does_decide_to_attack(self):
        # ROUND `nfrrqa`.  THIS CARD EXISTS BECAUSE THE PROSE WAS WRONG.
        # mob_aggro.py's own comment said "every shipped roster is
        # non-offensive, so on a walk past an undamaged mob the tick returns
        # a register equal to the one it was given" -- true of bg0001's four
        # dummies, carried from there to "every roster", and never re-driven
        # against Bg0002, the scene the owner actually plays in.  It is
        # false there, and the sentence is struck in place in mob_aggro.py
        # with this measurement beside it.
        #
        # DERIVED, NOT PINNED TO A NUMBER THIS FILE TYPES: the counts come
        # out of the shipped table through the shipped driver.  The day a
        # mining round changes that table, this card reports the new truth
        # instead of accusing anybody.
        from pirateforce_foundation import (
            field_mob_tables_bg0002, field_mobs, mob_ai_control, mob_combat,
            mob_ai_scheduler,
        )
        roster = field_mobs._parse_hostile_placements(field_mob_tables_bg0002)
        register = mob_ai_control.open_register(roster)
        ledger = mob_combat.open_ledger(roster)
        orc_chief = next(m for m in roster if m.placement_index == 92)
        _after, results = mob_ai_scheduler.tick_session(
            register, ledger, 0x750059,
            (orc_chief.x, orc_chief.y, orc_chief.z))
        deciding = [
            r for r in results
            if r.intent_kind == ma.INTENT_ATTACK_UNDELIVERABLE
        ]
        acquired = [
            r for r in results if r.after_phase == ma.PHASE_AGGRO
        ]
        self.assertGreater(
            len(deciding), 0,
            "no row of the Bg0002 roster decides to attack a player standing "
            "on it: if a mining round made every row non-offensive, the "
            "struck sentence in mob_aggro.py is true again and should be "
            "unstruck -- with this measurement quoted")
        self.assertGreater(len(acquired), len(deciding))
        self.assertLess(len(acquired), len(results))
        # THE PROSE NUMBERS, PINNED (pf-adversary D11: the first draft
        # asserted only the inequalities, so every number the struck
        # sentence in mob_aggro.py quotes -- 17 rows, 5 acquiring,
        # placement 92, cadence 1 -- was unbacked prose).  Pinned as
        # DERIVED values, so a mining round that changes the table fails
        # here with the new truth rather than being told the old one.
        self.assertEqual(len(results), 17)
        self.assertEqual(len(acquired), 5)
        self.assertEqual([r.actor_identity for r in deciding],
                         [orc_chief.actor_identity])
        self.assertEqual(mob_ai_control.ATTACK_CADENCE_TICKS, 1)
        self.assertEqual(mob_ai_control.MELEE_ATTACK_RANGE, 275.0)
        # AND THE PART THAT DID NOT CHANGE, so nobody reads this card as
        # Door B opening: deciding to attack still sends no byte.
        self.assertIs(ma.ATTACK_INTENT_DELIVERABLE, False)

    def test_the_paid_debt_names_a_card_that_exists(self):
        # pf-adversary D11: the `[PAID, round nfrrqa]` note above cites a
        # test by path with no class, and nothing checked it.  Rename or
        # delete that card and the PAID claim would have survived it for
        # ever -- which is the exact failure mode this lane keeps paying
        # for, one file over.
        # READ, NOT IMPORTED: importing a sibling test module depends on
        # which directory pytest put on sys.path, and this card must mean
        # the same thing under the Windows gate as it does here.
        sibling = ast.parse(
            (Path(__file__).resolve().parent
             / "test_mob_ai_control_dispatch.py").read_text(encoding="utf-8"))
        defined = {
            node.name for node in ast.walk(sibling)
            if isinstance(node, ast.FunctionDef)
        }
        for name in (
            "test_a_target_pos_frame_really_runs_the_tick_not_only_the_gate",
            "test_the_tick_does_not_run_on_a_frame_that_is_not_a_target_pos",
        ):
            self.assertIn(
                name, defined,
                "the D7 debt above is marked PAID by citing %s in "
                "tests/test_mob_ai_control_dispatch.py, and it is not there: "
                "either it moved (and the citation must move with it) or the "
                "debt is unpaid again" % name)


class ContainmentTests(unittest.TestCase):
    """Pure server logic: no wire, no database, no dispatch, no scenario."""

    def setUp(self):
        self.source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_the_module_is_ascii_and_cp874_safe(self):
        self.source.encode("ascii")
        self.source.encode("cp874")

    def test_the_module_imports_only_stdlib_and_nothing_cross_layer(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertEqual(imported, {"__future__", "dataclasses", "math",
                                    "typing"})

    def test_the_module_has_no_import_time_side_effects(self):
        allowed = (
            ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
            ast.ClassDef, ast.FunctionDef,
        )
        for node in self.tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value,
                                                         ast.Constant):
                continue  # the module docstring
            self.assertIsInstance(node, allowed)

    def test_the_module_never_imports_a_clock_or_randomness(self):
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for banned in ("random", "time", "datetime", "secrets"):
            self.assertNotIn(banned, imported)

    def test_the_lane_is_not_reachable_from_production_dispatch(self):
        # RETIRED 2026-08-26 and INVERTED IN PLACE, kept under its old name so
        # that a reader who greps it in an older round note lands here and
        # reads why it says the opposite of what it used to.
        #
        # It used to assert production_allowed is False and that NOTHING in
        # src/ imports this module.  COO-DECISION 2026-08-26T04:02+07:00,
        # section 2, ruled that arrangement the hole rather than the safeguard:
        # the damage driver reached this lane through a HANDLE ARGUMENT, and no
        # scan of src/ can see an argument, so "nothing imports it" was a true
        # sentence that protected nothing.  The order was to promote the module
        # where the scan CAN see it.
        #
        # So the assertion is inverted, and what it now defends is the shape of
        # the promotion: exactly ONE importer, the controller, and the damage
        # driver's wiring line STILL does not name this module - because if it
        # did, the argument-shaped edge would be back.
        #
        # WIDENED round 256rvs: mob_ai_scheduler.py is a SECOND importer, and
        # it is not a second controller -- it owns no AI_STATE mutation, it
        # only calls mob_ai_control.tick_step/commit_step (the one controller
        # this comment already names) and imports mob_aggro solely to build
        # the MobObservation/PlayerObservation inputs those calls need.  The
        # invariant this test defends ("one controller") still holds; what
        # changed is that a controller can now have more than one CALLER, the
        # same relationship mob_ai_control already has with runtime.py.
        #
        # ROUND `1tz15e`: the line
        # ``assertIs(ma.MOB_AGGRO_IMPORTED_BY_A_PRODUCTION_MODULE, True)``
        # stood here and the flag it read is struck from the module.  It was a
        # bool that RESTATED the derivation below it, and a restatement cannot
        # fail when the fact does: someone who deleted the import would have
        # had to delete the flag as well for anything to go red.
        #
        # A pf-adversary pass on that same round showed the derivation below
        # was not the fortress the round called it either: it read ast.Import
        # and ast.ImportFrom ONLY, so an edge spelled
        # ``__import__("pirateforce_foundation.mob_aggro", fromlist=["x"])``
        # -- a live, working import, and precisely the shape COO-DECISION
        # 2026-08-26T04:02+07:00 named as the hole -- was invisible to it, and
        # a mob_combat module carrying one left the whole suite green.  The
        # walk now reads the CALL forms too.
        self.assertIs(ma.production_allowed, True)
        # RECURSIVE, and that is a fix: this walked SRC_ROOT.glob("*.py")
        # until pf-adversary pointed out that lane B's OWN hook package,
        # src/pirateforce_foundation/lane_hooks/, was invisible to it - so a
        # third importer could be added in this lane's own file and the census
        # below would not move.  tests/test_lane_b_mob_ai_tick.py has used
        # rglob for this same census since it was written; two lane-B files
        # had two different answers to "what is src/".
        importers = []
        mentions = []
        for path in sorted(SRC_ROOT.rglob("*.py")):
            if path.name == "mob_aggro.py":
                continue
            source = path.read_text(encoding="utf-8")
            if "mob_aggro" not in source:
                continue
            relative = path.relative_to(SRC_ROOT).as_posix()
            mentions.append(relative)
            if module_imports_mob_aggro(source):
                importers.append(relative)
        # ORDER MATTERS.  This sat AFTER the equality below, where it was
        # dead code: the expected list has two entries, so any run that
        # reached it had already proved len(importers) == 2.  Moving it first
        # buys a READABLE FAILURE, not new detection power - the equality
        # still catches every empty case, and pf-adversary was right to say
        # so.  It is kept for the message and described as that, not as a
        # guard.
        self.assertGreater(
            len(importers), 0,
            "no module in src/ imports mob_aggro by any form the scan can "
            "see: the promotion COO-DECISION 2026-08-26T04:02+07:00 ordered "
            "has been undone, or the edge has gone back to being an argument")
        # A THIRD IMPORTER, ROUND `nfrrqa`, AND THIS CARD GOING RED IS HOW IT
        # WAS ADDED -- which is the whole point of a census and the reason it
        # is widened here by hand rather than derived.  ``mob_ai_player_
        # damage`` reads ``mob_aggro.INTENT_ATTACK_UNDELIVERABLE`` (the
        # constant, never a copy of its spelling: a hand-typed literal is the
        # defect that kept the tick gate shut for three days) to decide which
        # tick results become an HP write.  It is an importer and not a
        # mention because a lane that only MENTIONS a constant is a lane that
        # re-spells it.
        self.assertEqual(
            sorted(importers),
            sorted([ma.MOB_AGGRO_IMPORTER + ".py", "mob_ai_player_damage.py",
                    "mob_ai_scheduler.py"]))
        self.assertEqual(
            sorted(mentions),
            ["lane_hooks/lane_b_mob_ai_tick.py", "mob_ai_control.py",
             "mob_ai_player_damage.py", "mob_ai_scheduler.py",
             "mob_combat.py"])
        # The edge that must NOT come back: the damage driver's wiring line
        # still passes None, so threat never arrives through an argument the
        # scan above cannot see.  It arrives through the importer named on the
        # line above, after the combat commit.
        from pirateforce_foundation import mob_combat, mob_ai_control
        # ``mob_combat.MOB_COMBAT_THREAT_HANDLE_IS_OPTIONAL`` was read here
        # too, and is struck in the same round for the same reason.  What it
        # carried is the next line: the damage driver's wiring line does not
        # name this module.
        #
        # A cross-check comparing MOB_COMBAT_THREAT_FOLD_OWNER's module half
        # against MOB_AGGRO_IMPORTER was written here in the same round and
        # REMOVED in it: pf-adversary showed both operands are already pinned
        # to literals within a few lines, so no source change exists for which
        # that line is the unique detector.  An assertion that can only fail
        # after another has already failed is decoration; this round's whole
        # subject is that a second copy of a claim is not a guard on it.
        self.assertNotIn("mob_aggro", mob_combat.MOB_COMBAT_WIRING)
        self.assertEqual(mob_combat.MOB_COMBAT_THREAT_FOLD_OWNER,
                         "mob_ai_control.damage_step")
        self.assertIs(mob_ai_control.production_allowed, True)

    def test_dispatch_reachability_is_derived_not_declared(self):
        # ROUND `1tz15e`.  ``MOB_AGGRO_DISPATCH_REACHABLE`` was pinned False by
        # (renamed ``MOB_AGGRO_DAMAGE_FOLD_REACHABLE`` in round `a7k5gy`, when
        # COO-DECISION 2026-09-03T16:47+07:00 item 1 split the one word that
        # was answering for two facts; this card owns the FOLD half only)
        # a bare assertIs here, by a second assertIs in
        # tests/test_mob_ai_control.py, and by a value published into
        # scenarios/combat_aggro_001.json - three copies of one bool, and the
        # bool had been WRONG since 2026-08-26, when the call site the prose
        # called "the last unbuilt step" was built.
        #
        # WHAT THIS CARD IS AND IS NOT, written after two pf-adversary passes
        # took two earlier drafts of it apart:
        #  * it is STATIC.  The behavioural proof of the same fact is
        #    tests/test_mob_ai_control_dispatch.py, which drives the real
        #    dispatcher headless and has existed since R179.  An earlier draft
        #    of this round wrote "nothing was measuring anything"; that was
        #    false, and the file that refutes it is named in the last sentence
        #    of the docs/FUNCTIONAL_COVERAGE.json note this round quotes.
        #    What was missing was not a measurement of the fold - it was
        #    anything at all tying the published CONSTANT to it.
        #  * it resolves import ALIASES, because keying on the spelling
        #    ``mob_ai_control.`` made a behaviour-neutral rename in runtime.py
        #    turn this card red on a fact that had not changed.
        #  * it requires the called function to USE the lane, not merely live
        #    in a module that imports it.
        #  * it does NOT claim the tick loop runs.  See
        #    test_the_tick_gate_is_reported_not_assumed below.
        touching = {}
        for path in sorted(SRC_ROOT.rglob("*.py")):
            if path.name == "mob_aggro.py":
                continue
            source = path.read_text(encoding="utf-8")
            if not module_imports_mob_aggro(source):
                continue
            touching[path.stem] = functions_that_touch_this_lane(source)
        self.assertIn("mob_ai_control", touching)

        runtime_tree = ast.parse(
            (SRC_ROOT / "runtime.py").read_text(encoding="utf-8"))
        aliases = module_aliases(runtime_tree)
        self_calls = {}
        outward_calls = {}
        for node in ast.walk(runtime_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            mine = set()
            theirs = set()
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Call):
                    continue
                callee = inner.func
                if not isinstance(callee, ast.Attribute):
                    continue
                if not isinstance(callee.value, ast.Name):
                    continue
                if callee.value.id == "self":
                    mine.add(callee.attr)
                else:
                    stem = aliases.get(callee.value.id, callee.value.id)
                    theirs.add((stem, callee.attr))
            self_calls.setdefault(node.name, set()).update(mine)
            outward_calls.setdefault(node.name, set()).update(theirs)
        self.assertIn("dispatch", self_calls,
                      "runtime.py has no dispatch(): this card is measuring "
                      "the wrong file")

        seen = set()
        frontier = ["dispatch"]
        reached = set()
        while frontier:
            name = frontier.pop()
            if name in seen:
                continue
            seen.add(name)
            reached |= outward_calls.get(name, set())
            frontier.extend(self_calls.get(name, ()))

        into_the_lane = sorted(
            "%s.%s" % (stem, attr) for stem, attr in reached
            if attr in touching.get(stem, ()))
        derived = bool(into_the_lane)
        # THE WHOLE CARD IS THIS ONE LINE.  It has no opinion about which
        # answer is right; it requires the published constant to be whatever
        # the walk found.  An earlier draft added ``assertIs(derived, True)``
        # underneath, which pinned the answer and made the card unable to
        # report False - re-committing, three lines below its own comment
        # about pins, the defect the round exists to remove.  pf-adversary
        # measured that: deleting the call site AND flipping the constant, the
        # change this card's prose demands, still failed.
        self.assertIs(
            ma.MOB_AGGRO_DAMAGE_FOLD_REACHABLE, derived,
            "MOB_AGGRO_DAMAGE_FOLD_REACHABLE says "
            f"{ma.MOB_AGGRO_DAMAGE_FOLD_REACHABLE}, but walking runtime.py "
            f"from dispatch reaches {into_the_lane} - one of the two has to "
            "change")

    def test_the_tick_gate_is_reported_not_assumed(self):
        # A SECOND pf-adversary pass found this and it is bigger than anything
        # else in the round that found it.  runtime.py:5887 guards the aggro
        # TICK behind
        #     lane_hooks.module_production_allowed("lane_hooks.lane_b_mob_ai_tick")
        # and lane_hooks.__init__ qualifies a name that does not already start
        # with its own __name__ by PREFIXING it -- so that argument becomes
        # "pirateforce_foundation.lane_hooks.lane_hooks.lane_b_mob_ai_tick",
        # a key that exists nowhere, and the fail-closed lookup returns False
        # on every frame forever.  The decision loop this module IS has
        # therefore never run for a player.
        #
        # runtime.py belongs to the chief, so this card does not fix it; it
        # REFUSES TO LET IT BE SILENT.
        #
        # ~~and the day the call site is corrected this test fails and the
        # lane that owns the fact must come and say what changed~~ STRUCK,
        # round `42vxv6`: THAT WAS FALSE AND A pf-adversary PASS MEASURED IT.
        # This card hardcoded both spellings and asked the RESOLVER; it never
        # read the call site at all, so correcting runtime.py:5888 left it
        # green.
        # ~~and it may not be cited as the thing standing guard over the
        # fix~~ -- THE STRIKE IS ITSELF STRUCK, round `a7k5gy`, because
        # COO-DECISION 2026-09-03T16:47+07:00 item 1 refused the shape rather
        # than the card: a bool pinned to a broken answer is not a measurement
        # of it.  This card no longer hardcodes anything.  It READS the
        # argument out of the AST of the real call site -- literal today,
        # lane_b_mob_ai_tick.MODULE_NAME once the chief lands ticket 1648 --
        # hands it to the REAL module_production_allowed, and requires the
        # published constant to equal the answer.  So it now does go red by
        # itself on the fix, on the true answer, and whoever lands it has to
        # come to mob_aggro.py and say so.  Measured both ways this round.
        #
        # IT IS NOT A DUPLICATE of
        # test_the_gate_answers_what_it_answered_at_every_hand_spelled_site.
        # That card is a census: every hand-typed spelling in src/, and it
        # goes red when a ROW moves - including rows this lane does not own.
        # This one asks one question about one call site and ties the answer
        # to the SHIPPED CONSTANT, which the census does not read at all.  The
        # census would stay green if mob_aggro's bool drifted; this card would
        # stay green if a sibling lane's spelling broke.  Neither covers the
        # other.
        from pirateforce_foundation import lane_hooks
        runtime_tree = ast.parse(
            (SRC_ROOT / "runtime.py").read_text(encoding="utf-8"))
        argument, how = tick_gate_argument(runtime_tree)
        derived = lane_hooks.module_production_allowed(argument)
        # The control half: the module IS production_allowed under its own
        # registered key, so a False above is the ARGUMENT failing to resolve,
        # never the lane being switched off.  Without this line a lane that
        # somebody had legitimately closed would read exactly like a typo --
        # which is a property of the gate, stated in its own docstring, not an
        # accident of this card.
        self.assertIs(
            lane_hooks.module_production_allowed(
                lane_b_mob_ai_tick.MODULE_NAME), True,
            "the hook module itself is not production_allowed: this card is "
            "measuring the wrong thing")
        # THE WHOLE CARD IS THIS ONE LINE, same shape as the fold card above:
        # no opinion about which answer is right, only that the shipped
        # constant is whatever the real gate answers the real call site.
        self.assertIs(
            ma.MOB_AGGRO_TICK_REACHABLE, derived,
            f"MOB_AGGRO_TICK_REACHABLE says {ma.MOB_AGGRO_TICK_REACHABLE}, "
            f"but runtime.py's tick gate passes {how} and the real "
            f"module_production_allowed answers {derived} to it - one of the "
            "two has to change, and if the gate has just started resolving "
            "that is good news nobody has written down yet: update "
            "mob_aggro's constant and prose and re-run "
            "tools/pf_write_mob_ai_pin.py")
        # The separation the old single bool did not make: the damage FOLD is
        # reached (the card above), the TICK is gated (this card), and neither
        # is observable by a player -- ATTACK_INTENT_DELIVERABLE is pinned
        # False by test_the_lane_is_not_reachable_from_production_dispatch,
        # and repeating it here would be a second copy, not a second guard.
        #
        # WHAT THIS CARD STILL DOES NOT MEASURE, and the next round owes it.
        # pf-adversary closed round `a7k5gy` on this question and it is the
        # right one: this card asks WHAT THE GATE ANSWERS to the argument the
        # call site passes.  The fact the constant is NAMED for is whether
        # maybe_tick() actually executes on a frame.  Those two coincide only
        # while the gate call is a bare positive conjunct of the branch
        # condition inside a method dispatch reaches -- which the helpers above
        # now require, and which is the whole reason they do.  But requiring
        # the SHAPE is not the same as watching the CALL happen.  So the day
        # the chief lands ticket 1648 and this card goes red, RED IS NOT
        # PERMISSION TO WRITE True HERE ON THE STRENGTH OF A DICTIONARY HIT:
        # the behavioural half belongs beside
        # tests/test_mob_ai_control_dispatch.py, which drives the real
        # dispatcher headless, and until a card there shows tick_step running
        # on a frame, the shipped pin must not carry a reachability claim
        # nobody executed.
        #
        # [PAID, round `nfrrqa`]  That card exists now:
        # tests/test_mob_ai_control_dispatch.py::
        # test_a_target_pos_frame_really_runs_the_tick_not_only_the_gate.  It
        # reads NO console token: a hit folds threat and leaves the row IDLE
        # (measured there, not assumed), then ONE real TargetPos frame
        # through the real dispatcher takes it to PHASE_AGGRO targeting this
        # player, in the register the session kept.  Its control card pins
        # that an ACTION frame does NOT tick.  So the True this constant
        # carries is now backed by an execution, not only by a dictionary
        # hit -- which is what the paragraph above was refusing to accept on
        # credit.

    # THE ANSWER THE GATE GIVES AT EVERY CALL SITE THAT SPELLS ITS OWN NAME.
    # Measured 2026-09-03, round `42vxv6`.  Key is "<file>::<spelling>", value
    # is what lane_hooks.module_production_allowed() returns for that spelling
    # RIGHT NOW -- not whether the spelling looks well formed.
    # ROUND `gjyxt5` (chief), COO-DECISION 20260903_1648 on LANE-B's
    # CORE-REQUEST 20260903_1639: the row
    # "runtime.py::lane_hooks.lane_b_mob_ai_tick": False IS GONE, and this
    # is the "a row that vanished" case the failure message below names,
    # SAID OUT LOUD AS THE MESSAGE ASKS.  runtime.py's tick gate no longer
    # types a name at all: it reads lane_b_mob_ai_tick.MODULE_NAME (COO
    # item 3, chosen over the bare stem precisely so a rename cannot
    # re-open the hole), so the site has no hand-typed spelling for this
    # table to answer for.  The tick IS alive now -- the gate answers True
    # there -- and the site is watched by
    # tests/test_mob_ai_tick_gate_wiring.py, which boots the real
    # dispatcher and reads the FIRED token off the console instead of
    # reading the source.  LANE-B owns the prose of the two cards above
    # and the shipped pin scenarios/combat_aggro_001.json; both still say
    # the tick is dead, and both are LANE-B's to correct (chief's letter
    # pf_bridge/notes_to_chief/20260903_1800_CHIEF-TO-LANE-B-*).
    GATE_ANSWERS_AT_HAND_SPELLED_SITES = {
        "runtime.py::lane_gm_chat_command": True,
    }

    def test_the_gate_answers_what_it_answered_at_every_hand_spelled_site(self):
        # ROUND `42vxv6`.  THE GENERAL SHAPE OF WHAT THE CARD ABOVE FOUND.
        #
        # The card above states one measured fact about one call site.  This
        # one asks the question that fact is an instance of, across the tree:
        # where a call site hands ``module_production_allowed()`` a STRING IT
        # TYPED ITSELF, what does the gate answer that site today?
        #
        # It matters because of a property that function documents and means:
        # "the closed answer is indistinguishable from the typo, on purpose".
        # Fail-closed is the right default -- guessing on behalf of an
        # owner-approved switch is worse -- but the price is that a misspelled
        # name is a lane silently removed from the product, and nothing was
        # watching for it.  This lane is paying that price now:
        # `lane_hooks.lane_b_mob_ai_tick` at runtime.py:5888 is neither the
        # bare stem nor the fully qualified name, so it is prefixed into
        # `pirateforce_foundation.lane_hooks.lane_hooks.lane_b_mob_ai_tick`,
        # a key that exists nowhere, and the gate has answered False there on
        # every frame since that wiring landed.
        #
        # IT ASSERTS ON THE GATE'S ANSWER, NOT ON THE SHAPE OF THE STRING, and
        # that is the whole design (pf-adversary D1/D3 of this round, both
        # measured against an earlier draft that compared spellings):
        #  * putting an ``f`` prefix on the string at runtime.py:5888 changes
        #    no behaviour and leaves the tick just as dead.  The spelling
        #    draft went RED on it and its own failure message then told the
        #    reader to publish "fixed" into three artifacts.  This one is
        #    GREEN, because the answer at that site did not move.
        #  * breaking the resolver's prefixing -- which closes the live GM
        #    chat kill switch at runtime.py:6911 along with everything else --
        #    left the spelling draft GREEN, since every spelling was still
        #    spelled correctly.  Here it is RED on the row for 6911.
        #  * the day runtime.py:5888 is corrected, the key moves AND the
        #    answer becomes True: red, twice over, and whoever corrected it
        #    has to come and say so.
        #
        # WHAT IT DOES NOT CLAIM (pf-adversary D5).  Nothing here is about
        # REACHABILITY.  A row is a place in the source where the gate is
        # asked with a hand-typed name; a call under ``if False:`` would earn
        # a row like any other, and no row is evidence that a frame ever
        # reaches it.  ``test_dispatch_reachability_is_derived_not_declared``
        # in this class walks from ``dispatch`` precisely so it can make that
        # claim; this card deliberately does not.  Nor is the table a
        # complete account of which lanes are live: a name read out of a
        # registration (``composer.module``, ``responder.module``) cannot be
        # misspelled and has no row here at all.
        from pirateforce_foundation import lane_hooks
        answers = {}
        for path in sorted(SRC_ROOT.rglob("*.py")):
            # A SIBLING'S BROKEN FILE IS NOT THIS LANE'S FAILURE, and this
            # card parses EVERY file in the package rather than only the ones
            # that mention this lane, so it needs the guard the sibling card
            # in tests/test_mob_loot_scene_boundary_wiring.py already has: a
            # file saved in cp874, or half-written, fails BY NAME instead of
            # as a UnicodeDecodeError out of pathlib (pf-adversary D6).
            relative = path.relative_to(SRC_ROOT).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, SyntaxError, ValueError) as exc:
                self.fail("%s cannot be read as Python source (%r): this card "
                          "cannot answer for a file it cannot parse, and says "
                          "so instead of failing somewhere else"
                          % (relative, exc))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                callee = node.func
                if isinstance(callee, ast.Attribute):
                    called = callee.attr
                elif isinstance(callee, ast.Name):
                    called = callee.id
                else:
                    continue
                if called != "module_production_allowed":
                    continue
                # POSITIONAL *OR* KEYWORD.  An earlier draft read node.args[0]
                # only and skipped the call outright when args was empty, so
                # ``module_production_allowed(module_name="...")`` -- the
                # spelling the parameter's own name invites -- walked straight
                # past it (pf-adversary D2, measured green on a planted typo).
                spelled = None
                if node.args:
                    spelled = node.args[0]
                for keyword in node.keywords:
                    if keyword.arg == "module_name":
                        spelled = keyword.value
                literal = self._string_literal(spelled)
                if literal is None:
                    continue
                answers["%s::%s" % (relative, literal)] = (
                    lane_hooks.module_production_allowed(literal))
        self.assertEqual(
            answers, self.GATE_ANSWERS_AT_HAND_SPELLED_SITES,
            "the gate's answers at hand-spelled call sites have moved. A row "
            "that turned True means a lane that was being refused is now let "
            "through -- if that is runtime.py::lane_b_mob_ai_tick, the aggro "
            "TICK has come alive and this table, mob_aggro's prose and the "
            "shipped pin scenarios/combat_aggro_001.json have to say so "
            "together. A row that turned False means a lane is now being "
            "refused where it was not: that is either an owner closing a "
            "switch on purpose or a name that stopped resolving, and the two "
            "are indistinguishable here BY DESIGN of the gate, so say which. "
            "A row that vanished means a call site stopped spelling its name "
            "literally and is no longer watched by anything. A NEW row is a "
            "gate name nobody has written an answer for yet."
        )

    @staticmethod
    def _string_literal(node) -> str | None:
        """The string a call site typed, or None if it did not type one.

        Unwraps an f-string with no interpolations in it, because ``f"x"`` and
        ``"x"`` are the same bytes to every reader except an AST walk -- the
        behaviour-neutral edit that took the first draft of the card above
        apart (pf-adversary D1).  A genuinely computed name (an f-string with
        a ``{}`` in it, a named constant, a variable) is NOT a hand-typed
        spelling and is deliberately not answered for: this card would be
        guessing, and guessing is the failure the gate itself exists to
        prevent.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr) and all(
                isinstance(part, ast.Constant) and isinstance(part.value, str)
                for part in node.values):
            return "".join(part.value for part in node.values)
        return None


    def test_the_import_scan_sees_the_forms_it_claims(self):
        # THE FIX FROM THE FIRST pf-adversary PASS HAD NO GUARD OF ITS OWN.
        # Deleting the whole ast.Call branch of module_imports_mob_aggro --
        # reverting it to the scan whose blindness the pass exploited -- left
        # every lane-B test green, because no module in src/ uses those forms
        # today.  A fix that is green because nothing reaches it is the same
        # defect as a flag that restates a fact.  So the scan is exercised
        # against sources written here, including the rows it CANNOT see,
        # which are asserted as False so the documented limits are a
        # measurement instead of a promise.
        lane = "pirateforce_foundation.mob_aggro"
        seen = {
            "plain": "from . import mob_aggro",
            "absolute": "import pirateforce_foundation.mob_aggro",
            "from_member": "from .mob_aggro import apply_damage_threat",
            "dunder": f'x = __import__("{lane}", fromlist=["a"])',
            "importlib": f'import importlib\nx = importlib.import_module("{lane}")',
            "from_importlib": (
                f'from importlib import import_module\nx = import_module("{lane}")'),
            "aliased_importlib": (
                f'from importlib import import_module as _load\nx = _load("{lane}")'),
            "rebound": (
                f'import importlib\n_load = importlib.import_module\n'
                f'x = _load("{lane}")'),
        }
        for label, source in seen.items():
            with self.subTest(sees=label):
                self.assertTrue(module_imports_mob_aggro(source), label)
        blind = {
            # Measured by pf-adversary, and true of this scan by construction.
            "computed_name": (
                'import importlib\n'
                'x = importlib.import_module("%s.%s" % ("a", "b"))'),
            "sys_modules": f'import sys\nx = sys.modules["{lane}"]',
            "third_module": (
                "from . import mob_ai_control\n"
                "x = mob_ai_control.mob_aggro.apply_damage_threat"),
        }
        for label, source in blind.items():
            with self.subTest(cannot_see=label):
                self.assertFalse(module_imports_mob_aggro(source), label)
        # And the false-accusation half: a sibling whose name merely starts
        # the same way is NOT this lane.
        self.assertFalse(
            module_imports_mob_aggro("from . import mob_aggro_tables"))

    def test_the_module_declares_which_rules_are_ours(self):
        self.assertIn("[OUR DESIGN]", self.source)
        self.assertIn("NONCLAIMS", self.source)
        for reading in (
            "threat_is_abs_damage_saturating_at_i32_max",
            "nonnegative_damage_including_miss_adds_no_threat_meaning_unknown",
            "return_and_dead_phases_absorb_no_damage_threat",
            "ties_broken_by_lowest_identity",
            "phase_dead_is_absorbing_revival_not_modeled",
        ):
            self.assertIn(reading, ma.MOB_AGGRO_CHOSEN_READINGS)


if __name__ == "__main__":
    unittest.main()
