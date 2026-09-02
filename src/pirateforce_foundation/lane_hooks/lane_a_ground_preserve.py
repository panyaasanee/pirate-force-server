"""LANE-A (WORLD): compose a ChooseNPC answer without sweeping the ground.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Yesterday: kill a monster, watch
the drop land, click ANYTHING before picking it up, and the drop was gone -
this lane's four ChooseNPC responders composed their answer frame with
``legacy.make_runtime_remote_actors``, which re-declares the scene's actors
WITHOUT the ground list, and RE-130 says a generation that omits a live key
erases that key on the client.  Today the same click keeps the row standing
whenever the session's loot cell says one is standing in THIS scene.

WHERE THIS CAME FROM.  ``LANE-B`` shipped the composer
(``mob_combat.remote_actors_preserving_the_ground``) and wrote this lane
the two lines it owed - ``pf_bridge/notes_to_chief/20260902_1845_LANE-B-TO-
LANE-A``.  ``COO-DECISION 20260902_1946`` approved the call-site half with
two conditions: close the race window, and never sweep rows silently on a
read.  Both are the composer's own behaviour and this file does not
reimplement either; what it owns is naming the scene correctly.

    THE ONE CORRECTION TO THAT LETTER, AND IT IS MEASURED.  The letter's
    code block reads ``mob_loot.ground_rows_live_here(mob_loot_cell,
    scene_id)``.  Wired literally, that is a NO-OP FOREVER: this lane's
    ``scene_id`` is an int (1, 2, 14, 126, ...) while ``ground_rows_live_
    here`` folds its scene argument through ``mob_loot.scene_key``, which
    is ``_require_scene`` + ``casefold`` and REFUSES anything that is not a
    ``str``.  Every click would therefore return
    ``GROUND_LIVENESS_BAD_SCENE`` (``caller_scene_unreadable``), take
    v141's bytes, and print a console line blaming a call site that was
    wired exactly as instructed.  The loot cell's scenes are FOLDER names
    (``bg0001``, ``Bg0002``, ...), so this file resolves the id to the
    folder through ``world_scene_folder.scene_folder_for_scene_id`` - the
    one public reader ``COO-DECISION 20260829_0848`` item 3 names for
    exactly this - and passes THAT.  Reported to LANE-B and the COO in
    round ``gx7xtp``'s letter.

FAIL-CLOSED, IN THE ONLY DIRECTION THAT IS SAFE HERE.  An id this project's
registry does not address resolves to ``None``, and ``None`` reaching
``ground_rows_live_here`` means "keep the cell's own answer, whatever scene
it is publishing" - which is precisely the cross-scene gating the letter
and pf-adversary's D16 forbid.  So an unresolvable id never reaches the
cell at all: it becomes ``GROUND_LIVENESS_BAD_SCENE`` here, the frame is
v141's own bytes, and the console says the cause.  The safe failure for a
frame is the frame that worked yesterday.

THIS IS ONE FUNCTION AND NOT FOUR COPIES on purpose: four responders that
each spelled the resolve step themselves would be four places for the next
scene-naming defect to hide in three of.
"""
from __future__ import annotations

from typing import Any

from .. import mob_combat
from .. import mob_loot
from .. import world_scene_folder

# Convention marker, same as every other module in this package.
production_allowed = True
test_only = False


def ground_rows_for_scene(mob_loot_cell: Any, scene_id: Any) -> int:
    """How many ground rows stand in ``scene_id``, as a liveness answer.

    Negative values are causes, not counts - see ``mob_loot``'s own
    ``GROUND_LIVENESS_*`` block.  This never raises: it is called while a
    player is waiting for a frame, on the v141 listener thread, which has
    no ``except`` of its own.
    """
    try:
        folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    except Exception:                        # noqa: BLE001 - see docstring
        return mob_loot.GROUND_LIVENESS_BAD_SCENE
    if folder is None:
        # An unaddressed scene id.  NOT passed through as ``None``: that
        # would ask the cell without a scene and accept another scene's
        # floor as this frame's gate.
        return mob_loot.GROUND_LIVENESS_BAD_SCENE
    return mob_loot.ground_rows_live_here(mob_loot_cell, folder)


def compose_answer(
    legacy: Any, entries: Any, scene_id: Any, mob_loot_cell: Any,
) -> tuple[bytes, bytes]:
    """``(pc, frame)`` for a ChooseNPC answer, ground list kept when live.

    Same return shape as ``legacy.make_runtime_remote_actors`` and the same
    bytes as that call whenever no row is standing here - which is every
    boot until the ``runtime.py`` call site starts passing a cell.  The
    site name is per SCENE, not per lane: the composer reports a wiring
    cause once per (site, cause) pair for the life of the process, so one
    shared name would let whichever responder fired first silence the
    other three.
    """
    return mob_combat.remote_actors_preserving_the_ground(
        legacy, entries, mob_combat.choose_npc_site(scene_id),
        ground_rows_left=ground_rows_for_scene(mob_loot_cell, scene_id),
    )
