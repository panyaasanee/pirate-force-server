"""LANE-B lane_hooks: the direct-call site mob_ai_scheduler.tick_session
needed and never got (round 256rvs, 2026-08-31), now with a concrete call
site named instead of a placeholder.

WHY THIS FILE EXISTS, IN ONE SENTENCE.  ``mob_ai_scheduler.tick_session``
(round 256rvs) is a pure, tested driver with zero callers; this file is the
thin option-(b) wrapper (COO-DECISION 20260829_0041, the same shape
``lane_a_scene_census.py``/``lane_a_choose_npc_scene14.py`` already use) a
runtime.py call site can reach through ``lane_hooks.module_production_
allowed`` -- it does NOT itself add that call site, because runtime.py is
the chief's file.  See ``LANE_B_MOB_AI_TICK_WIRING`` below for the exact
one it names.

WHY THIS IS A DIRECT CALL, NOT AN ``@hook``.  ``lane_hooks.fire()`` is
report-only by contract (its own docstring): it cannot hand a value back to
its caller.  ``tick_session`` MUST hand back the updated
``MobAiRegister`` -- the same reason ``census_composer``/
``choose_npc_responder`` are their own registries rather than ``fire()``
points.  A per-tick registry for exactly one entry would be a second
mechanism for the same option-(b) shape those two already prove out, so
this file skips inventing one: ``_discover()`` already records this
module's ``production_allowed`` flag the moment it imports (see
``lane_hooks/__init__.py``'s own ``_gate_module`` -- it gates every
``lane_*.py`` file it finds, not only ones that register a hook or a scene
composer), so a future runtime.py call site only ever needs this file's
bare name and its one function.

WHAT THE PLAYER WILL SEE DIFFERENTLY BECAUSE OF THIS FILE, STATED PLAINLY:
~~nothing today.  Nothing under ``src/pirateforce_foundation/runtime.py``
calls :func:`maybe_tick` yet (pinned by
``tests/test_lane_b_mob_ai_tick.py::test_nothing_in_runtime_py_calls_
maybe_tick_yet``) -- this file is readiness, not a wire change.~~
[STALE as of round `p05wire`, 2026-09-01, COO-DECISION 20260901_0145]
[MEASURED, by reading ``runtime.py``'s own ``dispatch()`` and this file's
own test]: the call site now exists.  ``runtime.py:dispatch()`` imports this
module and calls :func:`maybe_tick` on every inbound ``TARGET_POS_VITAL``
once a session already has a remembered target position
(``self.last_target_pos``), a selected character, a live
``mob_ai_register``, a live ``mob_combat_ledger``, and this module's own
``production_allowed`` gate reads True -- the exact
``LANE_B_MOB_AI_TICK_WIRING`` block below, pasted verbatim.  All six guard
conditions are ``and``-ed together in ``dispatch()``; this paragraph names
all six so a reader does not have to open ``runtime.py`` to know which
sessions are excluded.  The test that used to pin the negative
(``test_nothing_in_runtime_py_calls_maybe_tick_yet``) was flipped, not
deleted, to ``test_runtime_py_now_calls_maybe_tick_per_coo_decision_0145``
in the same round.  Still true, and the reason this section does not claim
more than that: called, it STILL composes no frame (``mob_ai_scheduler``'s
own NONCLAIMS, unchanged by this wrapper) -- it only lets the AI register
start recording proactive phase/threat truth (visible on the server console
as ``LANE_B_MOB_AI_TICK`` lines) instead of staying permanently idle between
hits.  Door B (turning an intent into bytes a client renders) is a
separate, larger decision this file still does not make.

THE CALL SITE THIS FILE NAMES, MEASURED RATHER THAN GUESSED.  256rvs left
``mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING`` deliberately vague about two
things: WHICH existing per-session dispatch point runs on a live cadence,
and WHERE a real player identity number comes from (the only identity this
project composes damage against, ``MOB_COMBAT_DEFAULT_ATTACKER``, is a
pinned STR/level profile for the damage FORMULA, not a real identity --
KA1B defect 1, still unresolved and irrelevant to this file, which asks for
no stat).  Both are now answered by reading, not guessing:

* THE DISPATCH POINT: ``runtime.py``'s own ``dispatch(self, parsed)``
  (currently ~line 5164) already runs once per parsed vital on one
  connection and already threads state across a whole boot from inside
  itself -- CORE-REQUEST-GM-030's warp-confirm window opens and closes
  around ``self._dispatch_with_lanes(parsed)`` in this exact method, which
  is the "existing per-session dispatch point that already runs on a live
  cadence" 256rvs asked for without naming.  Guarding on
  ``parsed.nested_id == legacy.TARGET_POS_VITAL`` (the same constant the
  GM-warp code in this same method already compares against, a few lines
  below) ties the tick to the vital a moving player already sends
  continuously, without composing anything on frames that are not one.
* THE PLAYER IDENTITY: ``self.foundation.selected.identity_hi``/
  ``identity_lo``, packed exactly as
  ``((selected.identity_hi & 0xFFFFFFFF) << 32) | (selected.identity_lo &
  0xFFFFFFFF)`` -- not invented for this file: it is the SAME formula
  runtime.py's own combat dispatch (``performer``, ~line 4142) and its
  scene007 EA7D action-ack path (~line 6728) already use for "this
  connection's own actor identity" today, on a path that already reaches
  real players.  Reused, not re-derived: the encoder that already ships.

``LANE_B_MOB_AI_TICK_WIRING`` below is the exact block, ready to paste.

WHAT THIS FILE DOES NOT DO.  It does not retry on a stale register the way
the damage_step/death_step call sites do (their own comments: unreachable
today because one connection's dispatch runs to completion before the next
starts on the SAME connection -- true here for the same reason, since this
file's only caller-to-be is that same single-threaded ``dispatch``).  It
does not swallow a contract mismatch: ``mob_ai_scheduler.MobAiSchedulerError``,
``mob_ai_control.MobAiControlError`` and ``mob_combat.MobCombatContractError``
all propagate unchanged, same as ``tick_session`` itself promises (its own
NONCLAIMS) -- a caller that wants a softer failure mode owns that choice at
the call site, this file does not make it silently.
"""
from __future__ import annotations

from typing import Any, Tuple

from . import announce_direct_fire, console_safe
from .. import mob_ai_player_damage
from .. import mob_ai_scheduler

# Deliberately NOT importing mob_ai_control/mob_combat here for their types:
# this file only ever passes those objects through to/from
# mob_ai_scheduler.tick_session, never constructs or inspects one itself, so
# a third containment edge in tests/test_mob_ai_control.py's/
# tests/test_mob_combat*.py's own "exactly these files import this lane"
# tripwires would be a real cost (one more file for those tests to widen)
# for zero benefit (nothing here reads either type). ``Any`` below says that
# honestly instead of importing for a signature no runtime check enforces.

# Same convention every other shippable lane module in this project uses:
# True means "no scenario flag needed, safe to run for every connection."
# Composes no frame either way (see module docstring), so there is nothing
# a flag could gate that calling tick_session itself does not already gate
# -- same reasoning mob_ai_scheduler.py gives for its own flag.
production_allowed = True

MODULE_NAME = "pirateforce_foundation.lane_hooks.lane_b_mob_ai_tick"

# One line per process, not one per frame: the storeless stand-down below
# fires on EVERY TargetPos a session with no lifecycle sends, and a truth
# repeated sixty times a second stops being read.  A list rather than a bool
# so a test can inspect and reset it without reaching for a global statement.
_STORELESS_ANNOUNCED: list = []
POINT = "vital_inbound_target_pos_mob_ai_tick"

# The exact block a future runtime.py round can paste into dispatch(),
# right after ``actions = self._dispatch_with_lanes(parsed)`` and before the
# GM-warp close-window calls that already follow it there. Written where a
# reader of this module finds it, not only in a PR body -- same convention
# mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING and mob_ai_control.
# MOB_AI_CONTROL_WIRING already use for themselves.
#
# ROUND `a7k5gy`, COO-DECISION 2026-09-03T16:47+07:00 item 3 -- THE GATE
# STRING BELOW USED TO BE A HAND-TYPED LITERAL AND IT WAS WRONG.  This line
# said ``lane_hooks.module_production_allowed('lane_hooks.lane_b_mob_ai_tick')``
# and the chief pasted it into runtime.py:5888-5889 character for character,
# as an order from this file is meant to be pasted.  But lane_hooks.__init__
# (:550-554) prefixes any name that does not already start with its own
# ``__name__``, so that argument resolved to
# ``pirateforce_foundation.lane_hooks.lane_hooks.lane_b_mob_ai_tick`` -- a key
# that exists nowhere -- and the fail-closed lookup answered False on every
# frame from the day the wiring landed (5ac93b31, 2026-08-31: three days,
# not the eight a draft of this comment borrowed off a neighbouring fact --
# pf-adversary D4).  The tick never ran, for anyone.
#
# The COO's ruling on whose fault that is, kept here because it is the useful
# half: HALF THE DEBT IS THIS LANE'S.  The chief copied what this file told
# him to copy.  So the order now names ``lane_b_mob_ai_tick.MODULE_NAME``,
# which runtime.py can already reach (it imports this module at runtime.py:42)
# and which cannot drift from the key ``_discover()`` actually registered,
# because it IS that key.  A literal here can be wrong in a way no reader
# sees; an attribute cannot.  THE ORDER IS NOT THE CALL SITE: runtime.py
# still passes the old literal, and the tick is still refused on every
# frame, until the chief lands ticket 1648.
#
# tests/test_lane_b_mob_ai_tick.py::WiringLineTests refuses to let this line
# go back to a literal, and tests/test_mob_aggro.py reads the argument out of
# runtime.py's AST -- not out of this string -- so neither file is trusting
# the other's spelling.
LANE_B_MOB_AI_TICK_WIRING = (
    "runtime.py dispatch(self, parsed), immediately after "
    "'actions = self._dispatch_with_lanes(parsed)': "
    "if (parsed.nested_id == legacy.TARGET_POS_VITAL and "
    "self.last_target_pos is not None and "
    "getattr(self, 'mob_ai_register', None) is not None and "
    "getattr(self, 'mob_combat_ledger', None) is not None and "
    "self.foundation.selected is not None and "
    "lane_hooks.module_production_allowed("
    "lane_b_mob_ai_tick.MODULE_NAME)): "
    "selected = self.foundation.selected; "
    "performer = ((selected.identity_hi & 0xFFFFFFFF) << 32) | "
    "(selected.identity_lo & 0xFFFFFFFF); "
    "x, y, z, _heading = self.last_target_pos; "
    "self.mob_ai_register, _tick_results = "
    "lane_b_mob_ai_tick.maybe_tick(self.mob_ai_register, "
    "self.mob_combat_ledger, performer, (x, y, z), "
    "store=getattr(getattr(self.foundation, 'lifecycle', None), 'store', "
    "None), character_id=self.foundation.selected.id). "
    "MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD: the store=/character_id= pair "
    "above is the ONLY part of this line that is not already landed, and it "
    "is NOT to be pasted until the COO answers "
    "pf_bridge/notes_to_chief/20260903_1952_LANE-B-ASK-COO-* -- measured "
    "there: with it, a player inside 275 units of Bg0002 placement 92 loses "
    "one HP per TargetPos frame they send and no frame tells them. "
    "Everything else in this line is what runtime.py already does. "
    "Needs 'from .lane_hooks import lane_b_mob_ai_tick' added to "
    "runtime.py's own imports. Composes no frame either way (see this "
    "module's own NONCLAIMS), so this is safe to add without opening "
    "Door B (mob_aggro.ATTACK_INTENT_DELIVERABLE) in the same round."
)


def maybe_tick(
    ai_register: Any,
    combat_ledger: Any,
    player_identity: int,
    player_position: Tuple[float, float, float],
    player_alive: bool = True,
    store: Any = None,
    character_id: Any = None,
) -> Tuple[Any, tuple]:
    """One :func:`mob_ai_scheduler.tick_session` pass, with the
    project's console-proof convention wrapped around it.

    Prints the ``LANE_HOOK_FIRED`` token (via
    :func:`lane_hooks.announce_direct_fire`, same as every other
    direct-call ``lane_hooks`` consumer) exactly once per call, then one
    line per row THAT ACTUALLY CHANGED PHASE -- deliberately not one line
    per row per call: ``tick_session`` runs on every TargetPos a moving
    player sends, and a per-row line for every row on every step would
    flood the console with ``idle->idle`` repeats for the common case
    (measured against this file's own tests: a 17-row register, the
    largest this project has shipped, ticked every frame of a played
    session, would be seventeen no-op lines per movement step). A phase
    transition is the one event worth a tester's grep; a repeat is not.

    Returns exactly what :func:`mob_ai_scheduler.tick_session` returns --
    the new register and the full per-row result tuple, unchanged, so a
    caller that DOES want every row (e.g. a future headless proof) still
    has it.  Nothing here is dropped, only what prints is filtered.

    ``store``/``character_id`` (round ``nfrrqa``, COO-DECISION
    ``20260903_1745`` point 2) are the M4 half: pass BOTH and an attack
    decision this tick becomes a clamped, floored, read-back HP write
    through :func:`mob_ai_player_damage.apply_tick_damage`.  Pass neither --
    the default, and what ``runtime.py`` passes today -- and NOTHING
    touches the database, so this argument pair is the whole opt-in and
    there is no flag hiding behind it.

    ~~Passing exactly one is a caller contract error and raises, rather than
    half-working.~~ STRUCK, same round, MEASURED WRONG BY pf-adversary (D3)
    BEFORE IT SHIPPED, and the measurement is worth more than the rule: the
    published order fetches the store with
    ``getattr(getattr(self.foundation, 'lifecycle', None), 'store', None)``,
    and ``session.ReadOnlyFoundationSession`` -- which ``app.py`` installs
    for every scene-load scenario -- has a ``store`` but NO ``lifecycle``.
    So the order, pasted verbatim, hands this function ``store=None`` with a
    real ``character_id``, and the raise came out of ``dispatch()`` on a
    shipped session class.  A NONE STORE IS NOW A NAMED STAND-DOWN, WHICH IS
    WHAT THIS FILE'S OWN ORDER ALREADY PROMISED IN WORDS ("refused by name as
    store_cannot_be_asked, never crashed on") and did not do.  The half that
    stays a raise is the one that cannot be an environment fact: a real store
    with no character id would write against nobody.
    """
    if store is None and character_id is not None:
        if not _STORELESS_ANNOUNCED:
            _STORELESS_ANNOUNCED.append(character_id)
            print(console_safe(mob_ai_player_damage.stand_down_console_line(
                mob_ai_player_damage.REFUSE_STORE_CANNOT_BE_ASKED,
                character_id,
                "maybe_tick was given a character but no store: this session "
                "has no lifecycle to fetch one from (said once per process)")))
        character_id = None
    elif store is not None and character_id is None:
        raise mob_ai_player_damage.MobAiPlayerDamageError(
            mob_ai_player_damage.REFUSE_IDENTITY_NOT_POSITIVE,
            "maybe_tick was given a store but no character_id: a write with "
            "no character to write against is a caller defect, not an "
            "environment fact")
    announce_direct_fire(MODULE_NAME, POINT)
    register, results = mob_ai_scheduler.tick_session(
        ai_register, combat_ledger, player_identity, player_position,
        player_alive=player_alive,
    )
    if store is not None:
        mob_ai_player_damage.apply_tick_damage(store, character_id, results)
    for result in results:
        if result.before_phase == result.after_phase:
            continue
        print(console_safe(
            "LANE_B_MOB_AI_TICK actor=0x%X %s->%s intent=%s"
            % (
                result.actor_identity, result.before_phase,
                result.after_phase, result.intent_kind,
            )
        ))
    return register, results
