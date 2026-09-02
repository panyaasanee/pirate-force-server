"""LANE-A (WORLD): compose a ChooseNPC answer without sweeping the ground.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Yesterday: kill a monster, watch
the drop land, click ANYTHING before picking it up, and the drop was gone -
this lane's four ChooseNPC responders composed their answer frame with
``legacy.make_runtime_remote_actors``, which re-declares the scene's actors
WITHOUT the ground list, and RE-130 says a generation that omits a live key
erases that key on the client.  This file is the seam that stops it: one
place where the four call sites decide how an answer frame is composed.

WHERE THIS CAME FROM.  ``LANE-B`` shipped the composer and wrote this lane
the two lines it owed - ``pf_bridge/notes_to_chief/20260902_1845_LANE-B-TO-
LANE-A`` - and ``COO-DECISION 20260902_1946`` approved the call-site half
WITH TWO CONDITIONS: close the read-then-compose race window, and never
sweep ground rows silently on a read.

    !! THOSE TWO CONDITIONS ARE NOT MET BY ANYTHING ON ``main`` TODAY, AND
    THIS FILE DOES NOT PRETEND OTHERWISE.  ~~"Both are the composer's own
    behaviour and this file does not reimplement either"~~ - STRUCK,
    pf-adversary, round ``gx7xtp``, MEASURED: LANE-B closed those two
    conditions in a LATER letter (``20260902_2048``, cc'd to this lane)
    with a DIFFERENT function, ``mob_combat.remote_actors_preserving_the_
    ground_under_publication(..., cell=..., scene=...)``, which reads the
    count and composes under the cell's single lock.  That function is not
    on ``main``: chief measured the same absence from the other side and
    declined to wire it for exactly this reason (``20260902_2208_CHIEF-TO-
    LANE-B``).  The composer this file can reach today reads the count
    FIRST and composes SECOND, which IS the window the first of those
    two conditions names.

SO THE CELL IS HELD BACK, AND THAT IS THE WHOLE SAFETY ARGUMENT.  Wiring
the four call sites is item 2 of LANE-B's letter and it lands here in full:
``mob_loot_cell`` is a real keyword-only parameter of every responder
instead of something that falls into ``**_ignored``.  But a cell that
arrives while only the racy composer exists is NOT asked for a count - it
is held back, the frame is v141's own bytes, and one bounded ASCII console
line per scene says so by name.  The day
``remote_actors_preserving_the_ground_under_publication`` reaches ``main``,
this file routes to it and the hold lifts with no call-site change.

    WHY HOLD RATHER THAN USE THE RACY ONE.  The failure it would buy is
    the exact failure the whole letter exists to prevent: a click whose
    count is read as "the floor is empty", a drop landing in the window,
    and a frame composed a moment later that erases the row.  A frame that
    keeps yesterday's behaviour is a bad day; a frame that eats a player's
    loot while a token says the ground is preserved is worse.

THE ONE CORRECTION TO LANE-B'S CALL-SITE BLOCK, AND IT IS MEASURED.  The
``1845`` letter's code reads ``mob_loot.ground_rows_live_here(mob_loot_
cell, scene_id)``.  Wired literally, that is a NO-OP FOREVER: this lane's
``scene_id`` is an int (1, 2, 14, 126, ...) while ``ground_rows_live_here``
folds its scene argument through ``mob_loot.scene_key``, which is
``_require_scene`` + ``casefold`` and REFUSES anything that is not a
``str``.  Every click would return ``GROUND_LIVENESS_BAD_SCENE``
(``caller_scene_unreadable``), take v141's bytes, and print a line blaming
a call site wired exactly as instructed.  The loot cell's scenes are
FOLDER names (``bg0001``, ``Bg0002``, ...), so this file resolves the id
through ``world_scene_folder.scene_folder_for_scene_id`` - the one public
reader ``COO-DECISION 20260829_0848`` item 3 names for this - and passes
THAT.  Reported to LANE-B in round ``gx7xtp``'s letter.

FAIL-CLOSED, IN THE ONLY DIRECTION THAT IS SAFE HERE.  An id this
project's registry does not address resolves to ``None``, and ``None``
reaching ``ground_rows_live_here`` means "keep the cell's own answer,
whatever scene it is publishing" - precisely the cross-scene gating the
letter and pf-adversary's D16 forbid.  So an unresolvable id never reaches
the cell at all.

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

#: The composer that satisfies ``COO-DECISION 20260902_1946``'s two
#: conditions, named rather than imported: it does not exist on ``main``
#: yet (LANE-B's own PR carries it), and importing a name that is not
#: there would make this module refuse to import at all.
UNDER_PUBLICATION_COMPOSER = (
    "remote_actors_preserving_the_ground_under_publication")

#: One bounded ASCII console token, printed once per scene for the life of
#: the process, when a cell arrives and this module declines to ask it.
#: Grep-able, space-free, and it names the scene AND the cause - an
#: operator reading it must not have to guess which of the two it is.
CELL_HELD_BACK_TOKEN = "LANE_A_GROUND_CELL_HELD_BACK"

#: Report-once memory for the token above.  Bounded by the number of scenes
#: this lane answers for (14 today), so it cannot grow without a new scene.
_HELD_BACK_REPORTED: set = set()


def under_publication_composer():
    """The lock-holding composer if it has landed, else ``None``.

    Looked up on every call rather than cached at import: the day it lands
    is a deploy, not a restart of this module's import.
    """
    return getattr(mob_combat, UNDER_PUBLICATION_COMPOSER, None)


def _report_held_back_once(scene_id: Any) -> None:
    key = repr(scene_id)
    if key in _HELD_BACK_REPORTED:
        return
    if len(_HELD_BACK_REPORTED) < 64:
        _HELD_BACK_REPORTED.add(key)
    try:
        print("%s scene=%s reason=%s_not_on_main" % (
            CELL_HELD_BACK_TOKEN,
            "".join(ch for ch in key if ch.isalnum() or ch in "._-")[:32],
            UNDER_PUBLICATION_COMPOSER))
    except Exception:                        # noqa: BLE001
        # A console that cannot be written to is a reason to lose the LINE,
        # never a reason to lose the FRAME.
        pass


def ground_rows_for_scene(mob_loot_cell: Any, scene_id: Any) -> int:
    """How many ground rows stand in ``scene_id``, as a liveness answer.

    Negative values are causes, not counts - see ``mob_loot``'s own
    ``GROUND_LIVENESS_*`` block.

    THIS DOES NOT RAISE ``Exception``, and that is not the same as "never
    raises" (pf-adversary, round ``gx7xtp``): ``mob_loot.ground_rows_live_
    here``'s own docstring names two things it cannot catch either - a
    handle whose ``publication()`` BLOCKS blocks this thread, and
    ``KeyboardInterrupt``/``SystemExit`` are not ``Exception`` and still
    propagate.  Pass a real ``DropLedgerCell``.
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

    Same return shape as ``legacy.make_runtime_remote_actors``, and the
    same BYTES as that call whenever nothing is standing here - which is
    every boot until BOTH the ``runtime.py`` call site passes a cell and
    the lock-holding composer lands.  See the module docstring for why the
    second half is a condition and not an accident.

    The site name is per SCENE, not per lane: the composer reports a
    wiring cause once per (site, cause) pair for the life of the process,
    so one shared name would let whichever responder fired first silence
    the other three.
    """
    site = mob_combat.choose_npc_site(scene_id)
    composer = under_publication_composer()
    if mob_loot_cell is not None and composer is not None:
        folder = None
        try:
            folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
        except Exception:                    # noqa: BLE001
            folder = None
        if folder is not None:
            try:
                return composer(
                    legacy, entries, site,
                    cell=mob_loot_cell, scene=folder)
            except Exception:                # noqa: BLE001
                # A composer that moved its signature must cost the ground
                # list, never the frame.  Falls through to today's shape.
                pass
    if mob_loot_cell is not None:
        # A cell reached this call site and the conditions of COO-DECISION
        # 20260902_1946 are not met by anything reachable: hold it back,
        # say so once per scene, and send the frame that worked yesterday.
        _report_held_back_once(scene_id)
        rows = mob_loot.GROUND_LIVENESS_UNKNOWN
    else:
        rows = ground_rows_for_scene(mob_loot_cell, scene_id)
    return mob_combat.remote_actors_preserving_the_ground(
        legacy, entries, site, ground_rows_left=rows,
    )
