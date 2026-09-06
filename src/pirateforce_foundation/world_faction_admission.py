"""LANE-A (WORLD): which scenes a player's faction-1 field may be sent into.

WHAT THIS FILE WAS, THROUGH ROUND vvy6q7.  It used to answer the WHERE
question for the faction wire from the scene registry: a login was admitted
only into a scene the registry declared ``login_entry_allowed`` AND
``n_SAVE == 1`` (COO-DECISION 20260829_2342), on top of the ``(1, 2)`` floor
``GT-032`` proved byte-for-byte.  That was itself the fix for an EARLIER
defect (D3): a login into any scene outside a literal ``(1, 2)`` shipped the
plain ``ActorAttr`` with no faction line at all, so a composed cast on the
one other scene that had one (Hell Volcano Island, 14) could not read as
hostile -- ``HYP-PF-027`` measured that hostility renders from a faction
PAIR and this file supplied the PLAYER half where there was none.

WHY THAT VERSION ITSELF BECAME THE DEFECT (ka1-A round R321, `1255` S1,
2026-09-06).  A GM single-use relog ticket landed a login inside scene 126
(the Atlantis ocean panel, ``login_entry_allowed: false``, ``n_SAVE: 0`` --
a row this file's OLD rule refused on both conditions at once).  The refusal
is silent by design (``runtime.py`` catches it and latches
``player_faction1_compose_refused_production_start_game``, no traceback, no
red test) -- so that login shipped ``FOUNDATION_SELECTED_START_GAME`` with
``basic_mask=0x034F`` and no ``basic_faction`` field, where a land login
ships ``0x074F`` with it.  Measured client-observable consequence: the
client does not read the field again later (no census or teleport resends
it), so that whole session stayed "factionless" in EVERY scene it
subsequently warped to -- monster names green, unclickable -- until the
player logged in fresh on land.  ``COO-DECISION`` (letter
``20260906_1347_COO-DECISION-ka1a1255-...-LANE-A.md``) reads: send
``basic_faction`` on every login scene, no hardcoded scene numbers, no
server-side level check.

THE FIX, AND WHY IT DOES NOT REOPEN ANY DOOR.  The registry-gated WHERE
question this file used to answer was never about scene ACCESS -- that is
``world_scene_entry.resolve_entry``'s job (``login_entry_allowed`` there
decides whether a character's PERSISTED row may resolve into a scene at
all; scene 126's row still reads ``login_entry_allowed: false`` there,
UNCHANGED by this file, so no ordinary player gains a new way to land in
126). This file only ever decided whether the ALREADY-CHOSEN scene's login
frame carries an extra, fixed-cost, additive field. Nothing about the wire
SHAPE varies by scene (the same 5-byte splice, proven at 1 and 2, already
carried unmodified to 14 with no new byte-level evidence beyond "the
serializer is generic"); the registry gate was a BLAST-RADIUS throttle on
top of that, not a technical requirement, and a throttle that a login can
route around today (via the GM single-use bypass, and tomorrow via the real
M2 sailing feature landing a persisted row at sea) rather than one that
protects anything downstream from it. So the fix removes the throttle
instead of adding scene 126 to it: ``admits`` now says yes to every
well-typed scene id and no only to what could never legally be a scene id
in the first place. It does not check the player's level (measured
irrelevant by ka1-A's own table: LV 1 and LV 5 both reproduced pink/green by
scene, not by level) and it does not hardcode a scene number, which is
exactly what the COO's letter asked for.

WHAT THIS FILE IS NOT, STILL.
  * It is NOT a claim that any given scene is reachable by an ordinary
    player.  That is ``world_scene_entry.resolve_entry``'s ``login_entry_
    allowed`` gate, a different module, untouched here.
  * It does NOT touch ``make_actor_attr_with_basic_faction``, the class-less
    serializer ``GT-032`` froze byte-for-byte.  That one keeps its literal
    ``(1, 2)`` and stays frozen; the offline tests compare against it.
  * It does NOT change ``basic_faction``.  The only admitted value is still
    1, and ``scene_seq`` must still be 0.  This widens WHERE, not WHAT.

FAIL-CLOSED, IN THE ONE DIRECTION LEFT.  A ``scene_id`` that is not a plain
``int`` (a ``str``, ``None``, a ``bool``, anything the wire's own ``u16tag``
could not have produced) is refused, same as before.  Refusing the faction
field is what every boot before D3's fix did, so a refusal can only ever
return the server to an earlier, safe behaviour.
"""

from __future__ import annotations

from typing import Any

# The scene ids GT-032 proved the faction-1 byte shape at, and therefore the
# floor this policy may never fall below regardless of anything else this
# module ever grows.  Kept as a named floor (not just "the smallest two
# ints") because a future reader asking "why 1 and 2 specifically" should
# find the proof, not have to infer it from the fact that ``admits`` happens
# to return True for them along with everything else.
PROVEN_FACTION_SCENE_IDS: tuple[int, ...] = (1, 2)

# The only faction value any of this admits, unchanged from GT-032.
PROVEN_BASIC_FACTION = 1

# The only scene sequence ever measured, at scene 1 and scene 2 alike.
PROVEN_SCENE_SEQUENCE = 0


def forget_cached_registry() -> None:
    """No-op, kept for callers written against the registry-gated version.

    This module no longer reads the scene registry at all (see the module
    docstring: the WHERE question is answered without it now), so there is
    no cache left to drop.  Kept rather than deleted so an older test or
    tool that calls it does not need to know the internal shape changed.
    """


def _scene_id_is_well_typed(scene_id: Any) -> bool:
    return type(scene_id) is int and not isinstance(scene_id, bool)


def admits(scene_id: Any, registry: Any = None) -> bool:
    """May a player entering ``scene_id`` carry the faction-1 field?

    THE ADMISSION CHECK FOR THE `1347` COO-DECISION.  Read the module
    docstring before changing this.  Every scene a login can legally carry
    (any plain ``int``) is admitted; the ``PROVEN_FACTION_SCENE_IDS`` floor
    is still named above because it is what ``GT-032`` proved, not because
    it is still doing any narrowing work.

    ``registry`` is accepted and ignored -- kept so every existing call site
    (``player_wire.py``, ``gm/login_mask.py``, every test that still passes
    one) keeps working unmodified.  Fail-closed on the one thing that was
    never a scene id to begin with: anything that is not a plain ``int``
    (a ``bool`` included -- ``True == 1`` in Python, and scene 1 is
    admitted, so this is checked explicitly rather than left to fall out of
    the type check).
    """
    return _scene_id_is_well_typed(scene_id)


def refusal_reason(scene_id: Any, registry: Any = None) -> str:
    """Why ``admits`` said no, in words a console line can carry.

    Never raises: a reporter that raised here would turn a login into a
    traceback, which is a strictly worse outcome than a login with no
    faction frame.
    """
    if _scene_id_is_well_typed(scene_id):
        return f"faction_admitted_scene_{scene_id}_every_login_scene"
    return "faction_refused_scene_id_is_not_an_int"


def admitted_scene_ids(registry: Any = None) -> tuple[int, ...]:
    """The floor ``GT-032`` proved, ascending.

    FOR EVIDENCE AND FOR TESTS, NOT FOR THE SERIALIZER.  ``admits`` now says
    yes to any well-typed scene id, which is not an enumerable set (a scene
    id this process has never heard of still answers True) -- so this
    function can no longer return "every admitted scene", only the named
    floor that is true regardless of which scene a caller asks about next.
    ``registry`` is accepted and ignored, same reason as ``admits``.
    """
    return PROVEN_FACTION_SCENE_IDS


def console_line(registry: Any = None) -> str:
    """The one line an attended round greps to see this policy's whole state.

    Printed by the caller, not here: this module has no opinion about who
    owns stdout.
    """
    return (
        "WORLD_FACTION_ADMISSION rule=every_login_scene"
        f" proven_floor={','.join(str(i) for i in PROVEN_FACTION_SCENE_IDS)}"
    )
