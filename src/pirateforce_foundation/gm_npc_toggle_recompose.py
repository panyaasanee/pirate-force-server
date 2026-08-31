"""CORE-REQUEST-GM-041 read point.

``gm/``'s letter (20260830_1817) asked for one thing: a call site ``gm/``
can reach from inside its own tree that answers whether commanding
``npc on|off <mob_id>`` for a client-flagged GM-switch NPC
(``gm.npc_switch_catalog.is_gm_switchable_npc``) would feed the same
re-encode/admission cycle ``mob_scene_recompose.recompose_frames`` already
runs, every dispatch, for the mobs actually present in a scene.

Measured this round against ``mob_scene_recompose.recompose_frames``: its
``roster`` argument defaults to a static per-scene mined table (see that
function's own docstring) with no on/off column, and nothing that flows
into it is conditioned on the ``npc`` grammar in any way -- traced through
``runtime.py``'s three call sites (all pass a roster built by the same
static per-scene lookup) and confirmed the roster's own row type carries
no toggle field at all.  ``gm/commands.py``'s own docstring for ``npc``
also says the verb still only parses and logs (CORE-REQUEST-GM-032's audit
row), and ``gm/chat_command_action.py`` refuses ``npc`` before composing
any action, so there is no live path today by which a toggle could even
reach the roster.  So today's honest answer is NO for every mob_id,
switchable or not: recompose is not filtered by any toggle state, because
no toggle state is stored anywhere a recompose call site reads.

This function is the one place that answer lives.  A later round that adds
the missing on/off state store and threads it through the ``roster`` a
recompose call site passes changes THIS function's body; ``gm/``'s call
site does not change, which is the whole point of a read point instead of
``gm/`` importing ``mob_scene_recompose`` directly (it does not today, and
this module keeps it that way).
"""
from __future__ import annotations

from .gm.npc_switch_catalog import is_gm_switchable_npc


def npc_toggle_would_recompose(mob_id: int) -> bool:
    """Would toggling ``mob_id`` on/off change what the next recompose sends?

    Raises :class:`ValueError` for an id that is not one of the 7
    client-flagged GM-switch NPCs -- the question is only meaningful for a
    mob_id ``gm/commands.py``'s ``npc`` verb actually addresses; anything
    else is a caller bug, not a "no" answer.

    Returns ``False`` for every switchable mob_id today (see module
    docstring): no on/off state exists yet for a recompose call site to
    read.  Not a stub that always agrees with the caller's hope -- it is a
    measured negative, and it is expected to flip to a real per-mob check
    the round a state store lands, not to be deleted.
    """
    if not isinstance(mob_id, int) or isinstance(mob_id, bool):
        raise TypeError("mob_id must be an int")
    if not is_gm_switchable_npc(mob_id):
        raise ValueError(
            f"mob_id {mob_id} is not a GM-switchable NPC "
            "(gm.npc_switch_catalog.is_gm_switchable_npc is False) -- "
            "the recompose question is only defined for the 7 "
            "client-flagged rows"
        )
    return False
