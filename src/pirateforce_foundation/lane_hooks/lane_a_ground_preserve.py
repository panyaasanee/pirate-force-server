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

    ~~!! THOSE TWO CONDITIONS ARE NOT MET BY ANYTHING ON ``main`` TODAY~~ -
    STRUCK, round ``nyxlqs``, MEASURED: they are met now.  The history is
    kept because the hold-back branch below is still live code and this is
    the only place that says why it exists.  ~~"Both are the composer's own
    behaviour and this file does not reimplement either"~~ - STRUCK,
    pf-adversary, round ``gx7xtp``, MEASURED: LANE-B closed those two
    conditions in a LATER letter (``20260902_2048``, cc'd to this lane)
    with a DIFFERENT function, ``mob_combat.remote_actors_preserving_the_
    ground_under_publication(..., cell=..., scene=...)``, which reads the
    count and composes under the cell's single lock.  ~~That function is not
    on ``main``: chief measured the same absence from the other side and
    declined to wire it for exactly this reason (``20260902_2208_CHIEF-TO-
    LANE-B``)~~ - STRUCK, round ``nyxlqs``: **it reached ``main`` in LANE-B's
    ``#615``**, so the reason chief declined has expired.  The OTHER composer
    this file can also reach reads the count FIRST and composes SECOND, which
    IS the window the first of those two conditions names - which is why the
    routing below prefers the lock-holding one and why the hold-back branch
    is not simply deleted: a deploy older than ``#615`` still has only the
    racy one, and on that tree the safe answer is still to hold.

SO THE CELL WAS HELD BACK, AND THAT WAS THE WHOLE SAFETY ARGUMENT.  Wiring
the four call sites is item 2 of LANE-B's letter and it lands here in full:
``mob_loot_cell`` is a real keyword-only parameter of every responder
instead of something that falls into ``**_ignored``.  A cell that arrives
while only the racy composer exists is NOT asked for a count - it is held
back, the frame is v141's own bytes, and one bounded ASCII console line per
scene says so by name.  ~~The day
``remote_actors_preserving_the_ground_under_publication`` reaches ``main``,
this file routes to it and the hold lifts with no call-site change.~~ - that
day was ``2026-09-03`` and it happened exactly that way: the lookup is per
call, so no edit here was needed and no call site moved.

    !! WHAT THAT CHANGES FOR WHOEVER WIRES ``runtime.py``, and it is the
    one sentence that is no longer true from ``#609``'s PR body: the line
    chief is asked to add is NO LONGER byte-identical.  With the composer
    on ``main``, a cell reaching a responder while a row is STANDING in
    that scene now composes the preserving frame - measured on scene 2,
    12,574 -> 12,577 bytes.  THOSE THREE BYTES ARE A MARKER AND NOT THE
    LIST (pf-adversary D8, MEASURED: the same delta for 1 row as for 255);
    that the client then keeps its ground pool is ``RE-130``'s claim about
    the CLIENT and is proven nowhere in this repository.  That is the whole point of the seam and it is
    what ``COO-DECISION 20260902_1946`` approved, but it is a behaviour
    change on the day the call site is wired, not a no-op, and nobody
    should read an older sentence and believe otherwise.  With an EMPTY
    floor, or with no cell at all, the bytes are still v141's own.

    WHY HOLD RATHER THAN USE THE RACY ONE.  The failure it would buy is
    the exact failure the whole letter exists to prevent: a click whose
    count is read as "the floor is empty", a drop landing in the window,
    and a frame composed a moment later that erases the row.  A frame that
    keeps yesterday's behaviour is a bad day; a frame that eats a player's
    loot while a token says the ground is preserved is worse.

THE ONE CORRECTION TO LANE-B'S CALL-SITE BLOCK, AND LANE-B HAS SINCE FIXED
ITS OWN END.  The ``1845`` letter's code reads ``mob_loot.ground_rows_live_
here(mob_loot_cell, scene_id)``.  ~~Wired literally, that is a NO-OP
FOREVER: this lane's ``scene_id`` is an int (1, 2, 14, 126, ...) while
``ground_rows_live_here`` folds its scene argument through ``mob_loot.
scene_key``, which is ``_require_scene`` + ``casefold`` and REFUSES
anything that is not a ``str``.  Every click would return ``GROUND_
LIVENESS_BAD_SCENE`` (``caller_scene_unreadable``), take v141's bytes, and
print a line blaming a call site wired exactly as instructed.~~ - STRUCK,
round ``nyxlqs`` (pf-adversary D4), MEASURED: that was true when it was
written and LANE-B CLOSED IT in ``#615`` after round ``gx7xtp`` reported
it.  ``ground_rows_live_here(cell, 2)`` now returns a count, because their
``caller_scene_fold`` folds an int scene id.  The paragraph is kept struck
rather than deleted because it is why this file exists at all.

~~The loot cell's scenes are FOLDER names (``bg0001``, ``Bg0002``, ...), so
this file resolves the id through ``world_scene_folder.scene_folder_for_
scene_id`` - the one public reader ``COO-DECISION 20260829_0848`` item 3
names for this - and passes THAT.  It still does, for two reasons that
survive ``#615``: an id this registry does not address must never reach the
cell (below), and the ARMED path hands the composer a scene that then
travels into another lane's publication, where a folder name is the form
every other reader uses.~~ - STRUCK, round ``umlyof``: THE SCENE ID IS NOW
HANDED OVER AS AN ID, and the fold that turns it into a name is
``mob_loot.caller_scene_fold`` - the one fold every liveness guard on the
other side already uses.  Both reasons above survive as PROPERTIES; neither
survives as a reason to fold here:

* an unaddressed id is refused by that fold WITHOUT READING AND WITHOUT
  LOCKING the cell (``DropLedgerCell.compose_under_publication``, pf-adversary
  R12 over there), which is the same invariant, bought at the authority that
  owns it, and it comes back NAMED - ``caller_scene_id_unaddressed`` rather
  than this lane's flatter ``caller_scene_unreadable``;
* a folder name reaching that fold is still a folder name, so the ARMED
  path's scene travels exactly as far as it did.

WHAT FOLDING HERE COST, and it is a hole rather than a nicety (LANE-B via
chief, ``pf_bridge/notes_to_chief/20260903_0505`` item three; the mechanism
is ``mob_loot.caller_scene_fold``'s own fail-closed block).  A FOLDER NAME
IS NOT A SCENE IDENTITY.  ``world_scene_folder.SCENE_IDS_SHARING_AN_
ADDRESSED_FOLDER`` names the pair inside its own registry: scene 17 and
scene 186 both name ``Bg1001``.  ``caller_scene_fold`` refuses an id whose
folder is named by another ADDRESSED id
(:data:`mob_loot.GROUND_LIVENESS_SCENE_ID_AMBIGUOUS`) - and it can only
refuse an ID, because a folder name arriving pre-folded no longer knows
which of the two it came from.  So this file's own resolve was the one
caller in the project that could ARM SCENE 186'S FRAME WITH SCENE 17'S
FLOOR, silently, on the day somebody addresses the second id - the exact
cross-scene gating the paragraph below and pf-adversary's D16 forbid, let
in through the door built to keep it out.  MEASURED TODAY: no addressed
folder is shared (the same loop the fold reads), so every one of the
scenes this lane answers for - FOURTEEN registered responder scene ids, of
which thirteen are ``production_allowed`` today (pf-adversary D7: the two
numbers are different facts and this file used to print both as one) -
composes the same bytes as before.
This is a card for the day the registry grows, not a change a player sees
in this deploy.

WHAT A SCENE IS AT THIS SEAM, DECLARED RATHER THAN DELEGATED (pf-adversary
of this round, D1 and the closing question, MEASURED).  It is an ``int``
SCENE ID and nothing else.  The first draft of this change forwarded
whatever the caller brought, and ``caller_scene_fold`` applies the
ambiguity card ONLY on its ``int`` branch: a ``str`` folds straight to a
comparison key, so a caller spelling ``"Bg1001"`` walked past the very card
this round exists to reach - AND reached the cell, where a read RETIRES
EXPIRED ROWS (measured: ``swept_total`` 0 -> 1 for a refused call).  The
type gate below is therefore not defensive typing; it is the identity rule
this seam is about, applied where this file can still enforce it.  A caller
who has a folder NAME has already thrown the identity away and must not be
served here.

FAIL-CLOSED, IN THE ONLY DIRECTION THAT IS SAFE HERE.  A refusal hands
back :data:`SCENE_NO_READER_CAN_FOLD` - never ``None``.  ``None`` at
``ground_rows_live_here``'s and ``compose_under_publication``'s ``scene``
means "do not check the scene at all", so a refusal spelled ``None`` is a
WAIVER wearing a refusal's clothes: one caller reading the first element
and forgetting the second would arm this frame with another scene's floor
(pf-adversary D2, MEASURED by deleting the ordering below).  The sentinel
folds to :data:`mob_loot.GROUND_LIVENESS_BAD_SCENE` at every reader on the
other side, so a caller who ignores the refusal ENTIRELY still refuses
everywhere downstream, and the safety is a property of the value rather
than of the order of two lines in one function.

THE ARGUMENT CONTRACT MOVED EVEN THOUGH NO SCENE'S BYTES DID (pf-adversary
D14).  For an unaddressed id the answer is now
``caller_scene_id_unaddressed`` (``-7``) where it was
``caller_scene_unreadable`` (``-6``), and that case no longer prints
``LANE_A_GROUND_CELL_HELD_BACK`` because it never reaches the hold-back
branch.  Nothing this lane's fourteen registered responders pass is
affected; a reader of the console should still not have to find that out
from a diff.

THIS IS ONE FUNCTION AND NOT FOUR COPIES on purpose: four responders that
each spelled the resolve step themselves would be four places for the next
scene-naming defect to hide in three of.
"""
from __future__ import annotations

from typing import Any

from .. import mob_combat
from .. import mob_loot

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

#: Report-once memory for the token above, keyed by (scene, cause) so one
#: cause never silences the other for the same scene.  Bounded by the number
#: of scene ids this lane registers a responder for (14 today) times the two
#: causes below, and by the cap in the reporter either way.
_HELD_BACK_REPORTED: set = set()

#: Why a cell was held back, as the console spells it.  TWO CAUSES, NOT ONE
#: (pf-adversary D4, MEASURED): the earlier line said the composer was "not
#: on main" for BOTH of them, so a composer that had landed and then raised
#: - the exact case the ``except`` below exists for - printed a sentence
#: that was false about ``main`` once per scene for the life of the process.
HELD_BACK_COMPOSER_ABSENT = "%s_not_on_main" % UNDER_PUBLICATION_COMPOSER
HELD_BACK_COMPOSER_RAISED = "%s_raised" % UNDER_PUBLICATION_COMPOSER

#: The scene a refused fold hands back instead of ``None``.  It is an object
#: no reader on the other side can fold, so it is refused
#: (:data:`mob_loot.GROUND_LIVENESS_BAD_SCENE`) BEFORE any cell is read or
#: locked - unlike ``None``, which every one of them reads as "do not check
#: the scene at all".  See the module docstring's fail-closed block.
SCENE_NO_READER_CAN_FOLD = object()


def under_publication_composer():
    """The lock-holding composer if it has landed, else ``None``.

    Looked up on every call rather than cached at import: the day it lands
    is a deploy, not a restart of this module's import.
    """
    return getattr(mob_combat, UNDER_PUBLICATION_COMPOSER, None)


def _report_held_back_once(scene_id: Any, reason: str) -> None:
    key = (repr(scene_id), reason)
    if key in _HELD_BACK_REPORTED:
        return
    if len(_HELD_BACK_REPORTED) < 64:
        _HELD_BACK_REPORTED.add(key)
    try:
        print("%s scene=%s reason=%s" % (
            CELL_HELD_BACK_TOKEN,
            "".join(ch for ch in key[0] if ch.isalnum() or ch in "._-")[:32],
            reason))
    except Exception:                        # noqa: BLE001
        # A console that cannot be written to is a reason to lose the LINE,
        # never a reason to lose the FRAME.
        pass


def scene_the_cell_may_be_asked_about(scene_id: Any) -> tuple[Any, int]:
    """``(scene, 0)`` when a cell may be asked about it, else
    ``(SCENE_NO_READER_CAN_FOLD, why)``.

    TWO GATES, AND THE ORDER IS THE POINT.

    1. THE TYPE, WHICH THIS SEAM OWNS: an ``int`` scene id, ``bool``
       excluded (``True`` arriving in a "which scene?" parameter is an "is
       there one?" answer, and scene 1 is a real scene).  A ``str`` is a
       folder NAME, and a name is not an identity - scene 17 and scene 186
       are both ``Bg1001`` - so a name cannot be gated by the card below and
       is refused here rather than forwarded to a fold whose ``str`` branch
       predates that card (pf-adversary D1, MEASURED: forwarding it both
       skipped the card AND retired an expired row inside the cell).
    2. THE IDENTITY, WHICH ``mob_loot.caller_scene_fold`` OWNS: addressed?
       unambiguous?  Asked at the authority that owns it, so this hook
       cannot disagree with the racy read, the publication-held read or the
       composer about what a caller was allowed to say.

    The scene handed back is a plain ``int``, not the fold's key and not the
    caller's own object: the readers downstream fold again, a folded key
    would hide which id it came from, and an ``int`` SUBCLASS could answer
    the two folds differently (pf-adversary D15).

    NEVER RAISES ``Exception``, which is not the same as "never raises"
    (pf-adversary, round ``gx7xtp``): ``KeyboardInterrupt``/``SystemExit``
    are not ``Exception`` and still propagate.
    """
    if not isinstance(scene_id, int) or isinstance(scene_id, bool):
        return SCENE_NO_READER_CAN_FOLD, mob_loot.GROUND_LIVENESS_BAD_SCENE
    try:
        scene = int(scene_id)
        _key, refusal = mob_loot.caller_scene_fold(scene)
    except Exception:                        # noqa: BLE001 - see docstring
        return SCENE_NO_READER_CAN_FOLD, mob_loot.GROUND_LIVENESS_BAD_SCENE
    if refusal:
        return SCENE_NO_READER_CAN_FOLD, refusal
    return scene, 0


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
    scene, refusal = scene_the_cell_may_be_asked_about(scene_id)
    if refusal:
        return refusal
    return mob_loot.ground_rows_live_here(mob_loot_cell, scene)


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
    scene, refusal = scene_the_cell_may_be_asked_about(scene_id)
    if mob_loot_cell is not None and refusal:
        # A scene the one fold refuses NEVER TOUCHES THE CELL, and the
        # refusal travels under its own name instead of being reported as
        # the composer being absent - which is what the hold-back branch
        # below would have said, and it would have been false.
        return mob_combat.remote_actors_preserving_the_ground(
            legacy, entries, site, ground_rows_left=refusal,
        )
    composer_raised = False
    if mob_loot_cell is not None and composer is not None:
        try:
            return composer(
                legacy, entries, site,
                cell=mob_loot_cell, scene=scene)
        except Exception:                    # noqa: BLE001
            # A composer that moved its signature must cost the ground
            # list, never the frame.  Falls through to today's shape - and
            # the console must say THIS happened, not that the composer is
            # missing from ``main`` (pf-adversary D4).
            composer_raised = True
    if mob_loot_cell is not None:
        # A cell reached this call site and the conditions of COO-DECISION
        # 20260902_1946 are not met by anything reachable: hold it back,
        # say so once per scene AND cause, and send yesterday's frame.
        _report_held_back_once(
            scene_id,
            HELD_BACK_COMPOSER_RAISED if composer_raised
            else HELD_BACK_COMPOSER_ABSENT)
        rows = mob_loot.GROUND_LIVENESS_UNKNOWN
    else:
        rows = ground_rows_for_scene(mob_loot_cell, scene_id)
    return mob_combat.remote_actors_preserving_the_ground(
        legacy, entries, site, ground_rows_left=rows,
    )
