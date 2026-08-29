"""LANE-A (WORLD): which scenes a player's faction-1 field may be sent into.

WHAT THIS FILE IS, IN ONE SENTENCE.  It is defect ``D3`` -- the faction byte
that is silently dropped in every scene but two -- turned from a literal tuple
inside a serializer into a policy that reads the scene registry, under the
blast radius the COO wrote out in
``pf_bridge/notes_to_chief/20260829_2342_COO-DECISION-open-scene14-door-gt134-d3-stays-open.md``.

    WHAT A PLAYER SEES BECAUSE OF THIS FILE.  On Hell Volcano Island
    (scene 14), which this round also opens, the login now ships a
    ``PLAYER_FACTION`` frame instead of dropping it.  NOTHING ELSE MOVES:
    every other scene answers exactly what it answered before this file
    existed.

    ~~``HYP-PF-027`` measured that hostility renders from a faction PAIR, so
    the 81 composed actors on that island can be read as hostile by the
    client rather than standing there as neutral scenery.~~ WITHDRAWN BY THE
    ROUND THAT WROTE IT, before it left draft, after pf-adversary refuted it
    (D5) with three of this project's own artifacts.  Struck rather than
    deleted, because it is the sentence the next round will reach for.

    THE HALF THAT IS TRUE: ``HYP-PF-027`` did measure that hostility renders
    from a faction PAIR, and this file supplies the PLAYER half of that pair
    where there was none.  THE HALF THAT IS FALSE: the other half is
    measurably absent, so the pair is not completed by this file and the
    actors do not thereby become readable as hostile.
      * Driven on the production path: ``MOB_CENSUS_HOSTILITY scene_id=14
        roster=0 backed=0 unbacked=none`` -- zero hostile backing for 81
        shipped actors.
      * ``lane_hooks/lane_a_scene_census.py``, this same lane, says it
        outright: "none of its 81 actors carries a faction bit".
      * ``player_hostile_pairing.py`` records the flagless pair ``(0, 6)``
        as PROVEN NEUTRAL, and the only code that sets an NPC faction bit
        at all is the scenario-gated NPC-hostile hypothesis lane, which is
        ``production_allowed = False``.  (That lane's module is deliberately
        NOT named here, not even in a citation: its own test file pins that
        exactly two foundation modules -- ``app.py`` and ``runtime.py`` --
        may mention it by name, and this round is not the one to widen
        another lane's containment rule for the sake of a footnote.)
    So the pair on the production path is (player 1, monster 0), nobody has
    measured what that renders as, and the one thing measured about faction
    0 is that it is the NEUTRAL value.  A monster that does not read as
    hostile in scene 14 is therefore the EXPECTED outcome today, which is
    exactly what ``GT-134``'s header already tells the tester -- and the
    reason that line was not withdrawn when D3 closed.

THE DEFECT, AS IT WAS MEASURED.  ``player_wire``'s faction-1 serializers
refuse any ``scene_id`` outside ``(1, 2)``, because the byte shape was only
ever proven at those two (``GT-032``).  ``runtime.py``'s production recompose
catches that refusal and latches
``player_faction1_compose_refused_production_start_game``, so a login into any
other scene ships the plain ``ActorAttr`` and no ``PLAYER_FACTION`` line at
all.  The refusal was correct when the only scenes that existed were 1 and 2.
It stopped being correct on the day this lane composed a cast for a third.

THE BLAST RADIUS, QUOTED RATHER THAN INVENTED.  The COO's ruling reads:
"extend the faction wire ONLY to scenes the registry declares open, and
``n_SAVE = 1``".  Both halves are conditions here, and neither is a literal
scene list:

  * ``login_entry_allowed`` -- the registry key this lane already treats as
    the single door.  A scene nobody may enter cannot need an entry frame.
  * ``n_SAVE == 1`` (``SceneDestination.save_flag``) -- the client's own
    column, and the one that separates a scene characters LIVE in from a
    stage.  It is doing real work rather than decorating the sentence:
    scenes 278 and 997 are open at login today and carry ``n_SAVE 0``, so
    the first condition alone would have admitted two stages.

TODAY THAT PAIR ANSWERS ``{1, 2, 14}`` AND THE SET IS NOT WRITTEN DOWN
ANYWHERE.  Scenes 1 and 2 pass on their own merits -- both carry ``n_SAVE 1``
and neither pins ``login_entry_allowed`` at all, so both default to allowed --
which is the property that matters most here: THIS FILE NEVER SUBTRACTS FROM
WHAT ``GT-032`` PROVED.  If it ever did, every flagless production login would
lose its faction frame, and the console would say so
(``player_faction1_compose_refused_production_start_game``) without anything
going red.  ``tests/test_world_faction_admission.py`` drives that case rather
than trusting this paragraph.

FAIL-CLOSED, IN EVERY DIRECTION THAT IS NOT AN EXPLICIT YES.  A scene the
registry does not hold, a registry that will not load, a row whose key is
false, a row whose ``n_SAVE`` is not 1, a malformed argument, and any error
raised while reading all answer the same thing: NOT ADMITTED.  Refusing the
faction field is what every boot before this file did, so a refusal can only
ever return the server to yesterday's behaviour.  This is deliberate and it is
the opposite of the shape ``pf-adversary`` has caught this lane in twice: a
guard that opens when its own lookup breaks.

WHAT THIS FILE IS NOT.
  * It is NOT a claim that the faction byte RENDERS correctly in scene 14.
    Nobody has stood in scene 14.  ``GT-134`` is the attended ticket that
    looks, and its own header now says that a monster which does not read as
    hostile is an expected symptom rather than a FAIL.
  * It does NOT touch ``make_actor_attr_with_basic_faction``, the class-less
    serializer ``GT-032`` froze byte-for-byte.  That one keeps its literal
    ``(1, 2)`` and stays frozen; the offline tests compare against it.  Only
    the serializer ``runtime.py``'s production path actually calls
    (``make_actor_attr_with_name_class_and_faction``) consults this policy.
  * It does NOT change ``basic_faction``.  The only admitted value is still
    1, and ``scene_seq`` must still be 0.  This widens WHERE, not WHAT.

WHY THIS MODULE CACHES THE REGISTRY, AND WHAT THAT COST BEFORE IT DID.
pf-adversary (round vvy6q7, D2) drove the version of this file that read the
registry off disk on every call.  It found a divergence nothing else in the
project has: every OTHER reader of ``login_entry_allowed`` -- ``resolve_
entry``, ``is_position_persist_allowed``, ``lane_a_scene_census.scene_is_
open_to_players`` -- is HANDED the snapshot the boot loaded, while this one
re-read the file.  So the two readings were, in ``runtime.py``'s own words
about the same hazard class, "the AGE OF THE PROCESS apart".  Measured: with
the registry truncated, deleted, or its scene-14 row flipped AFTER the boot,
a login still teleported and still shipped 81 actors, and only the faction
frame vanished -- silently, because ``runtime.py`` catches the refusal into a
latched event, and because ``GT-134``'s header tells the tester that a
missing ``PLAYER_FACTION`` line is not a FAIL.  The realistic trigger is not
exotic: ``pf_git_sync.ps1`` rewrites this repository's files on the bridge
while the server may be up, so a login can land inside a partial write.

The cache makes this module agree with every other reader by construction:
ONE successful load per process, reused thereafter.  A failure is NOT cached
-- a first call that lands inside a partial write refuses (fail-closed) and
the next call tries again -- so the cache can only ever remove the divergence,
never freeze a broken read in place.  ``forget_cached_registry()`` exists for
tests and is not called by production code.  An explicitly supplied
``registry`` argument always wins and is never cached; that is the path
``runtime.py`` would use if this policy is ever handed the boot snapshot
directly, which is the real fix and belongs in chief's file.
"""

from __future__ import annotations

import threading
from typing import Any

from . import world_scene_travel

# One successful registry load per process, so this module reads the same age
# of the world as every other reader of ``login_entry_allowed``.  Guarded
# because the server is strictly serial today (FINDINGS_R18) but this module
# is imported by a serializer, and a serializer is exactly the thing a future
# round is most likely to call from somewhere else.
_REGISTRY_LOCK = threading.Lock()
_CACHED_REGISTRY: Any = None


def forget_cached_registry() -> None:
    """Drop the cached registry.  For tests; production never calls this."""
    global _CACHED_REGISTRY
    with _REGISTRY_LOCK:
        _CACHED_REGISTRY = None


def _registry(registry: Any = None) -> Any:
    """The supplied registry, or this process's one cached load.

    A supplied registry always wins and is never cached.  A failed load is
    never cached either: refusing once and retrying next call is fail-closed
    in both directions, where caching a failure would turn one bad read into
    a permanently faction-less server.
    """
    global _CACHED_REGISTRY
    if registry is not None:
        return registry
    with _REGISTRY_LOCK:
        if _CACHED_REGISTRY is None:
            _CACHED_REGISTRY = world_scene_travel.load_scene_registry()
        return _CACHED_REGISTRY


# The scene ids GT-032 proved the faction-1 byte shape at, and therefore the
# floor this policy may never fall below.  It is not a copy of the admitted
# set -- the admitted set is derived from the registry below and is wider than
# this today.  It exists so that a registry edit, a load failure or a future
# rewrite of the conditions cannot silently take the production login's
# faction frame away: ``admits`` returns True for these two whatever the
# registry says, and a test drives that with a registry that refuses to load.
PROVEN_FACTION_SCENE_IDS: tuple[int, ...] = (1, 2)

# The only faction value any of this admits, unchanged from GT-032.
PROVEN_BASIC_FACTION = 1

# The only scene sequence ever measured, at scene 1 and scene 2 alike.
PROVEN_SCENE_SEQUENCE = 0

# n_SAVE as the COO's ruling names it: the column that marks a scene
# characters live in.  ``SceneDestination.save_flag`` carries it.
REQUIRED_SAVE_FLAG = 1


def admits(scene_id: Any, registry: Any = None) -> bool:
    """May a player entering ``scene_id`` carry the faction-1 field?

    THE ADMISSION CHECK FOR D3.  Read the module docstring before changing
    this.  Two conditions, both from the COO's written blast radius, plus a
    floor that can only ever widen the answer:

      1. the scene is one ``GT-032`` proved (never subtract), OR
      2. the registry declares it open at login AND its ``n_SAVE`` is 1.

    Fail-closed: anything that is not an explicit yes is a no, including a
    registry that will not load.  A no returns the server to the behaviour
    every boot had before this module existed -- the plain ``ActorAttr`` and
    a named refusal event -- which is why a no is always safe and a wrong
    yes is not.
    """
    if type(scene_id) is not int or isinstance(scene_id, bool):
        return False
    if scene_id in PROVEN_FACTION_SCENE_IDS:
        return True
    try:
        destination = world_scene_travel.destination(scene_id, _registry(registry))
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return False
    if not bool(getattr(destination, "login_entry_allowed", False)):
        return False
    return getattr(destination, "save_flag", None) == REQUIRED_SAVE_FLAG


def refusal_reason(scene_id: Any, registry: Any = None) -> str:
    """Why ``admits`` said no, in words a console line can carry.

    An operator who reads "refused" and cannot tell WHICH condition refused
    will go and invent one -- this lane has watched that happen with
    ``world_m2_sea_destination``'s arrival point, where a refusal that said
    only "not authored" sent a reader off to make up a coordinate for a scene
    the client had authored all along.  So each no names itself.

    Never raises: a reporter that raised here would turn a login into a
    traceback, which is a strictly worse outcome than a login with no faction
    frame.
    """
    if type(scene_id) is not int or isinstance(scene_id, bool):
        return "faction_refused_scene_id_is_not_an_int"
    if scene_id in PROVEN_FACTION_SCENE_IDS:
        return "faction_admitted_proven_scene"
    try:
        destination = world_scene_travel.destination(scene_id, _registry(registry))
    except Exception as exc:  # noqa: BLE001 - a reason, never a raise
        return (
            f"faction_refused_scene_{scene_id}_not_readable_from_registry_"
            f"{type(exc).__name__}"
        )
    if not bool(getattr(destination, "login_entry_allowed", False)):
        return f"faction_refused_scene_{scene_id}_not_open_at_login"
    if getattr(destination, "save_flag", None) != REQUIRED_SAVE_FLAG:
        return (
            f"faction_refused_scene_{scene_id}_n_save_is_"
            f"{getattr(destination, 'save_flag', None)}_not_{REQUIRED_SAVE_FLAG}"
        )
    return f"faction_admitted_scene_{scene_id}_open_at_login_and_n_save_1"


def admitted_scene_ids(registry: Any = None) -> tuple[int, ...]:
    """Every scene this policy admits today, ascending, derived not listed.

    FOR EVIDENCE AND FOR TESTS, NOT FOR THE SERIALIZER.  ``admits`` asks about
    one scene and never builds this set, so a caller cannot accidentally make
    the answer depend on the registry holding a row for some unrelated scene.
    An attended round grepping the console wants the whole set on one line,
    and a round that widens the conditions wants a test that will notice.

    Fail-closed like everything else here: a registry that will not load
    yields only the proven floor.
    """
    admitted = set(PROVEN_FACTION_SCENE_IDS)
    try:
        registry = _registry(registry)
        # ``SceneRegistry.ids``, NOT ``tuple(registry)``.  ``SceneRegistry``
        # defines ``__getitem__`` keyed by SCENE ID, so the legacy iteration
        # protocol would ask it for scene 0, scene 1, scene 2 ... and raise
        # KeyError on the first miss -- which this function's own except
        # clause would then swallow into "only the proven floor", silently.
        # A fail-closed default is the right answer to a broken registry and
        # the wrong answer to a registry that is fine.
        scene_ids = tuple(registry.ids)
    except Exception:  # noqa: BLE001 - fail-closed, see the docstring
        return tuple(sorted(admitted))
    for scene_id in scene_ids:
        if type(scene_id) is int and admits(scene_id, registry):
            admitted.add(scene_id)
    return tuple(sorted(admitted))


def console_line(registry: Any = None) -> str:
    """The one line an attended round greps to see this policy's whole state.

    Printed by the caller, not here: this module has no opinion about who
    owns stdout.  ``GT-134`` needs to distinguish "the faction frame was
    refused" from "the faction frame was never attempted", and a set printed
    once at the top of a boot is what makes the difference legible.
    """
    ids = admitted_scene_ids(registry)
    return (
        "WORLD_FACTION_ADMISSION scenes="
        + ",".join(str(scene_id) for scene_id in ids)
        + f" rule=login_entry_allowed_and_n_save_{REQUIRED_SAVE_FLAG}"
        + f" proven_floor={','.join(str(i) for i in PROVEN_FACTION_SCENE_IDS)}"
    )
