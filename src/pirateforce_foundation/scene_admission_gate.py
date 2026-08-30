"""Whether the frozen legacy population may occupy the scene a session's row
names -- COO-DECISION 2026-08-29T09:41+07:00 item 2, partial (see SCOPE).

WHAT PROBLEM THIS CLOSES.  The inherited ``pf_login_game_server_v141.py``
P0/P30/P91 branch (``v141:4292``) queues three bg0001 PORT ROYAL placements
once its own precondition (``runtime_ack_sent`` and a known
``last_target_pos``) is met, and reads NOTHING about which scene the session
is in.  ``runtime.py`` disarms that branch at connection construction for
the sessions whose scene is known up front and is not scene 1
(``world_census_enabled`` / ``population_scenario`` / ``scene_load_scenario``).
It does NOT disarm it for the other opt-in lanes -- arena, second-password
bypass, the item-move/-swap/-merge hypotheses, and anything added later --
because those sessions keep the frozen three-actor population as their
MEASURED CONTROL, per the containment rule on ``world_census_enabled``
itself.  So the branch stays armed for their whole session, and once
BUILD-002 travel moves one of them off scene 1 it puts scene-1-shaped
actors into a scene nobody asked.  pf-adversary measured that reaching
(round vvy6q7, D1) the moment scene 14's door opened.

THE SHAPE OF THE FIX, AND WHY IT IS NOT A DISARM.
``current/pf_login_game_server_v141.py`` is pinned immutable, so the branch
cannot be changed.  A pre-dispatch disarm is also wrong, and was measured to
be wrong: the branch reads ``runtime_ack_sent`` AFTER the same dispatch call
sets it (``v141:3771`` then ``v141:4292``), so a check before
``super().dispatch()`` loses the transition frame.  What is left is to let
the branch run and then WITHHOLD its effects -- the same "correct it on the
way out" shape ``world_face_frame.rebuild_face_actions`` already uses on the
same return value.

WITHHOLD, NOT STRIP.  Dropping the two frames alone is not enough and was
measured to make one thing worse (pf-adversary, this round, D2).  The branch
also latches ``npc_spawn_sent``, ``npc_idle_action_sent``,
``population_indices`` and ``population_refresh_anchor``.  Leaving those set
while the frames are dropped breaks this project's own stated doctrine
(``runtime.py``, the ChooseNPC answerer): "evidence the client rendered
Columbus at all is exactly what ``population_indices`` recording placement
index 1 already is."  With the frames withheld and the indices left behind,
that field would attest to actors the gate had just deliberately prevented
the client from receiving, and the click answerer would compose full
position/heading frames for them at the wrong scene's coordinates.  It also
latches the branch permanently off (``v141:4308``), so a session withheld
once while away could never populate its home scene afterwards.

So the caller restores all four fields to their pre-dispatch values.  The
branch is then, from every reader's point of view, a branch that did not
fire on this frame: nothing shipped, nothing latched, and it stays armed for
a later frame on a scene this gate admits.

SCOPE -- WHAT THIS DOES *NOT* CLOSE.  Criterion 4(b) of COO-DECISION
0941 asks that all five actor-composing lines call one gate, "proven by
making the gate refuse and showing they all go silent".  THAT IS NOT TRUE OF
THIS MODULE and must not be claimed.  Measured (pf-adversary, this round,
D1): with ``admits_frozen_legacy_population`` forced to return False for
every input, a default boot still ships 108 actors on scene 1, 97 on
scene 2, and 81 on scene 14 -- only the fifth line goes silent.  This module
closes 4(a) and 4(c) and one fifth of 4(b).

THE LIMIT OF THE INPUT -- READ THIS BEFORE BUILDING ON THE GATE.  The
verdict rests entirely on ``selected.position.scene_id``, which is a row the
SERVER wrote.  ``world_travel_gate.py`` states the consequence in this
project's own words: "Nothing in this project can currently distinguish 'the
client is standing in scene 997' from 'the row says 997 and the client is
still in Port Royal'."  So this is, strictly, a ROW admission gate.  If a
crossing writes a non-home row for a client that never applied the teleport,
this withholds scene 1's population from a client standing in scene 1.  That
direction is a containment violation, and no test here can catch it, because
nothing observable from the client answers the question.  Until something
does, every claim built on this gate inherits the substitution.
"""

from __future__ import annotations

from . import world_population

# The frozen branch's own two output labels.  THIS IS A THIRD INDEPENDENT
# COPY of these strings, not a shared symbol: ``v141:4296``/``:4302`` is the
# original (pinned immutable, so it cannot be imported from), and
# ``runtime.py``'s ``_world_census_frozen_fallback`` re-emits its own second
# copy when it rebuilds the collection after a census refusal.  If any of the
# three spellings ever drifts apart, this gate stops matching and withholds
# nothing, silently.  ``test_scene_admission_gate.py`` pins all three
# together for exactly that reason.
FROZEN_LEGACY_POPULATION_LABELS = (
    "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
    "V134_P0_P30_P91_ISOLATED_REAPPLY_READY",
)

# The one scene the frozen rows are shaped for.  Re-exported from
# ``world_population`` rather than re-declared, so that if the home scene id
# ever changes, the census and this gate change together by construction.
HOME_SCENE_ID = world_population.SCENE_ID


def admits_frozen_legacy_population(scene_id) -> bool:
    """Return whether the frozen P0/P30/P91 rows may occupy ``scene_id``.

    Pure and total: any input that is not an ``int`` equal to
    ``HOME_SCENE_ID`` refuses, including ``None`` (no character selected --
    there is no scene to admit into).  ``type(...) is int`` rather than
    ``isinstance``: an ``int`` subclass whose ``__eq__`` is not an int's
    would decide this the wrong way, and the wrong way here is the
    containment direction (withholding on the home scene).  Nothing in this
    tree produces one today -- ``Position.scene_id`` comes from SQLite or
    from int-coerced registry JSON -- so this is a guard, not a fix.
    """
    return type(scene_id) is int and scene_id == HOME_SCENE_ID


def contains_frozen_legacy_population(actions) -> bool:
    """Whether the inherited branch queued its population on this frame."""
    return any(
        action[0] in FROZEN_LEGACY_POPULATION_LABELS for action in actions
    )


def without_frozen_legacy_population(actions):
    """``actions`` minus the frozen population tuples; a new list either way.

    Membership is exact against the two labels, never a prefix test: the
    frozen branch's neighbours share the ``V134_P0`` prefix
    (``V134_P0_Q3020_NPC_CONVERSATION_ONCE``) and must survive.
    """
    return [
        action for action in actions
        if action[0] not in FROZEN_LEGACY_POPULATION_LABELS
    ]
