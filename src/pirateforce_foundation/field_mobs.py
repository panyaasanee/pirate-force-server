"""LANE-B: named, hostile monsters built from real MOBS rows.

WHAT THIS MODULE IS FOR.  M3 asks for red-named monsters in a scene that were
not placed one at a time by hand, built from real ``MOBS`` rows rather than
from attributes we composed.  This module is the builder for that.  Every field
of every monster it emits was copied out of a committed game table by
``tools/pf_mine_scene_mob_roster.py`` into :mod:`field_mob_tables`; the only
derived column is HP, and its derivation has a control (below).

    placement index, XYZ  <- the scene's own .npc placement records
    template id           <- that placement's MOBS n_ID
    visual preset         <- MOBS.s_OUTFIT (the .avt basename the client loads)
    display name          <- TEXTDATA_TH__MOBS_TIP.s_NAME for that n_ID
    max HP                <- STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX

WHY THE SELECTION RULE CAN BE TRUSTED.  The generator keeps a placement when
its template resolves in MOBS and that row's outfit is a single unambiguous
basename.  Run over bg0001 that rule reproduces the frozen
``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` table in
``current/pf_login_game_server_v141.py`` exactly: 115 rows, zero mismatches on
index, template, x, y, z and outfit.  That table has been on the wire for
months, so the pipeline that feeds this module is checked against something the
project already trusts rather than against its own reasoning.

RE-098 (2026-08-27, RE runner, DONE / BOUNDED-NEGATIVE) closed off a shortcut
this module never took, worth naming so nobody reaches for it later: the raw
per-definition placement bytes carry three fields (``b5``, ``b15``,
``u32@11``) that could look like level/rank/spawn-rate shortcuts, and RE-098
measured that none of them are -- ``b5`` matches neither ``n_LEVEL_MIN`` nor
``n_LEVEL_MAX`` on any of 30 measured placements, ``b15`` matches ``n_RANK``
on only 1/30, and ``u32@11`` is constant (100) across every crosswalkable
definition regardless of how many placements its set has.  ``level``, ``rank``
and ``max_hp`` on :class:`FieldMob` come from ``MOBS``/``STANDARD_MOB`` proper
(via :mod:`field_mob_tables`'s mining pipeline), never from those raw payload
bytes, so this module needed no change -- RE-098 confirms there was no faster
path here to have mistakenly taken.

THE TWO CONTROLS ON THE DERIVED COLUMNS.  bg0001 placement 30 is the monster
the frozen source already names and gives HP to, independently of any table
this module reads: ``V117_P30_EXACT_HP = 3857`` and
``V119_P30_TARGET_NAME = "Tornado Eagle"``.  Placement 30's template is MOBS 31,
whose level is 27; ``STANDARD_MOB`` level 27 has ``n_HPMAX`` 3857, and
``MOBS_TIP`` 31 is named "Tornado Eagle".  Both frozen constants re-derive.
:func:`assert_frozen_controls` re-checks them against the legacy module at
runtime and refuses if either has drifted.

WHAT IS NEW HERE, STATED PLAINLY BECAUSE IT HAS NEVER BEEN ON THE WIRE.  The
body this module builds is a NAMED body and a HOSTILE body at the same time.
Each half is separately proven and the COMBINATION is not:

* named + HP, no faction: what the runtime sends for placement 30 today
  (V119/V117), rendered by a real client.
* faction, no name: the GT-032 ``HOSTILE_SPAWN`` frame (2026-08-21, PASS both
  layers) - the NPC became selectable as an enemy with a red target panel.
  GT-032's own ticket predicted and observed NO red name label, because that
  frame carried no name bit at all.
* named + faction together: THIS module, never sent, never observed.

So this module must not be read as claiming a red NAME.  What decides name
colour is ``RE-067``, which is open and belongs to lane C.
[STALE as of ``pf_bridge/CLIENT_RE_QUEUE.md`` chief R163/R165, 2026-08-25,
round `dvxb6f`] [MEASURED]: ``RE-067`` is CLOSED (PASS/MIXED) - the actor
half closed BOUNDED NEGATIVE (no colour-deciding read of ``actor_type``,
faction, or ``FONT_COLOR`` was found; the driver is unidentified, and the
"renders in PLAYER colour" theory this module never repeated was chief
R163's own retracted draft).  What decides name colour is still unknown,
but the search for it at the static layer is finished, not open; see
``mob_death.py``'s ``full_roster_override`` docstring for the full
citation trail.  What is claimed is
narrower and testable: the body is byte-for-byte the frozen ``make_npc_attr``
body for that monster, with the BasicAttr mask widened by exactly bit 0x0400
and exactly five bytes of tagged faction spliced in at the ascending-mask-order
position - the same splice GT-032 shipped, computed here from the legacy
serializers rather than from a fixed offset, because a name is variable-length
and the GT-032 constant (36) is only correct for a nameless body.

FACTION VALUES ARE OUR DESIGN.  1 for the player and 6 for the monster come
from SCENE-005 and are this project's composition; the original server's
faction semantics are unrecoverable.  Hostility needs BOTH halves: arena-v2
counted 1,023 neutral results for an NPC at faction 6 against a player left at
the constructor default, so a caller that does not put the player at faction 1
gets a monster that is merely present.  This module builds the monster half
only; the player half lives on the StartGame path, which is the chief's file.

WHAT THIS SCENE CANNOT DELIVER, MEASURED BEFORE THIS MODULE WAS COMMITTED.
bg0001 is a town and its monster placements are sparse.  All thirteen exist,
but no monster in this roster has ANOTHER monster within 1,000 units, and the
densest spot in the whole scene - the Mutant Green Eagle line near
(14455, 9357, 2200) - holds three within 2,000 units and four within about
3,900.  The nearest monster to a new character's spawn is 12,095 units away.
So this module delivers "the monsters this scene's own data defines exist and
are hostile", and it does NOT deliver "a field full of red names in one view".
That second thing needs a field scene, which is M2's delivery, and the same
code runs against it the moment the generator is pointed at one.
:func:`neighbour_census` computes those numbers rather than asserting them, so
a denser scene changes the answer loudly instead of leaving this paragraph to
rot.

NOTHING IS INSTALLED, AND THE IDENTITY SPACE IS SHARED.  This module sends
nothing, schedules nothing and persists nothing, and no module in ``src/``
imports it yet.  ``production_allowed`` is True because this is shippable
behaviour rather than a probe - it needs no scenario flag - but the flag is a
convention marker and no code branches on it.

    THE ONE INTEGRATION HAZARD, WRITTEN DOWN RATHER THAN LEFT TO BE FOUND.
    These monsters ARE members of the bg0001 census.  Their actor identities
    are ``0x2000 + placement_index + 1``, the same rule
    :mod:`world_population` uses, so sending this collection AND the lane-A
    census in the same generation would put thirteen identities on the wire
    twice with different bodies.  The correct wiring is the override, not the
    second collection: build the census and swap the hostile body in for the
    members :func:`hostile_placement_indices` names.  :func:`overlapping_
    identities` exists so a caller can assert the intersection instead of
    discovering it on screen.

CORRECTED 2026-08-26 (round `4z0efc`) - two sentences above are now false and are
kept rather than edited, per this project's own rule.  (1) "no module in
``src/`` imports it yet" stopped being true earlier the same day: this
module's ``load_roster()`` is imported by ``mob_combat.py`` (target
resolution) and ``mob_death.py`` (corpse override / repopulation), and
``runtime.py`` imports this module directly as of CORE-REQUEST-005
(commit ``6105d26``, "wire mob_combat+mob_death into runtime.py dispatch
(MOB-COMBAT-001)", 2026-08-26 09:27 UTC / 16:27 +07:00) -- NOT CORE-REQUEST-007
as an earlier draft of this correction said; 007 (round `keen-pasteur-r6hhp6`)
only added the `mob_ai_control` import, and never touched this one.  (2) the
override THE ONE INTEGRATION HAZARD
above calls for now EXISTS AS CODE: ``mob_death.full_roster_override()``
(this round) is exactly that override - it swaps every roster member's body
in for whatever the census would otherwise send, dead ones as corpses, living
ones (touched or not) hostile and named, reusing this module's own
:func:`hostile_actor_entry` under the hood.  What is STILL true, and is the
actual reason this docstring's headline claim ("never sent, never observed")
still holds: nothing in ``runtime.py`` calls ``full_roster_override`` yet -
its one existing census-override call site still calls the narrower
``corpse_override``, which is chief's file and this round's one-line request,
not a wiring line this lane can write itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mob_tables
from . import field_mob_tables_bg0002
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    SCENE_ID,
    SCENE_SEQUENCE,
)


# Convention marker only; nothing in this tree branches on it.
production_allowed = True
test_only = False

# The SCENE-005 pairing, carried here so this module does not import a
# scenario-gated probe lane to reach two integers.  Both values are OUR design.
FIELD_MOB_FACTION = 6
PLAYER_PAIR_FACTION = 1

# BasicAttr mask bit and wire tag for faction (u32 at object+0x68), and the
# nameless baseline mask the splice is defined against.
BASIC_BIT_NAME = 0x0001
BASIC_BIT_FACTION = 0x0400
FACTION_TAG = 0x14
FACTION_WIDTH = 4
FACTION_SPLICE_BYTES = 1 + FACTION_WIDTH

# BasicAttr mask bit and wire tag for level (u16 at object+0x5E), proven for
# an NPCAttr body specifically by RE-117 (not just the owner's PC-actor
# probe): NPCAttr serializer 0x466EB0 calls common BasicAttr serializer
# 0x4656F0 before its own derived fields, so this bit/offset/tag applies to
# the same object here.
BASIC_BIT_LEVEL = 0x0002
LEVEL_TAG = 0x12
LEVEL_WIDTH = 2
LEVEL_SPLICE_BYTES = 1 + LEVEL_WIDTH

# ~~The frozen constants the derived columns are checked against.~~
# ~~CONTROL_PLACEMENT_INDEX = 30 / CONTROL_TEMPLATE_ID = 31~~ -- withdrawn in
# round szdkgs: placement 30 is not in this scene's roster any more, because
# the crosswalk (RE-128) says Mob-Set 31 is n_ID 248 "Da Vinci", a townsman,
# and the town has no monsters at all.  The old pair is kept below under its
# own name: every sentence in this tree that cites "P30 / 0x201F / Tornado
# Eagle" was measured on a real actor the server really sent, so those
# measurements stand as measurements of THAT actor -- what changed is that
# the actor was never a monster and is no longer shipped as one.
LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX = 30
LEGACY_SETNUM_CONTROL_TEMPLATE_ID = 31

# The control row of the roster this lane actually ships for bg0001: the first
# of the four practice dummies, resolved through the crosswalk.
CONTROL_PLACEMENT_INDEX = 103
CONTROL_TEMPLATE_ID = 916

# The town-target decision, in code rather than in a comment: which n_ID this
# lane ships as attackable in a town, and the name it must still carry.  See
# tools/pf_mine_scene_mob_roster.py's TOWN_TARGET_N_IDS for the reasoning and
# the [LANE-B ASSUMPTION - AWAITING COO CONFIRMATION] label on it.
TOWN_TARGET_N_ID = 916
TOWN_TARGET_NAME = "Training Iron Man"

# The proven schedule: the identical collection is queued once immediately and
# once after model readiness.  Carried, not re-derived, from world_population.
INITIAL_REAPPLY_MS = 3000

# OUR synthetic cosmetic policy, NOT recovered per-placement data -- RE-116
# (2026-08-28, DONE / bounded negative, `pf_bridge` letter
# 20260828_0516_RE-116-RESULT-MOVEMENTATTR-IS-SPAWN-HEADING-SOURCE.md) closed
# this off after an exhaustive static search: CNetNPC's initial-apply path
# (`0x0045D34F`/`0x0045D355`) does read spawn heading from `MovementAttr+0x34`
# -- exactly the field `hostile_actor_entry`/`corpse` frames below already
# populate via `legacy.make_remote_movement_attr(..., mask=FULL_MOVEMENT_MASK)`
# (mask bit 0x02, object +0x34) -- so the WIRE MECHANISM this module uses was
# confirmed correct.  But RE-116 found no crosswalk from either the raw `.npc`
# placement bytes (T2: reader never touches offsets +0x08/+0x0C/+0x10/+0x14,
# only x/y/z) or `CONSTDATA_TH__MARKER.n_DIRTECTION` (T3: its one named
# consumer is player teleport/scene-entry orientation, not NPC placement) to
# an authentic per-placement heading value.  So this four-way round robin,
# keyed by `placement_index & 3`, stays what it always was: a value THIS
# PROJECT invented so spawned monsters do not all face one direction, not
# something recovered from client/gamedata.  Do not describe it elsewhere as
# authentic, and replace it the moment a real crosswalk is found (none exists
# today).
HEADINGS = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
_FLOAT32_MAX = 3.4028234663852886e38


class FieldMobContractError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class FieldMob:
    """One monster placement, every field copied from a table but ``max_hp``."""

    placement_index: int
    template_id: int
    x: float
    y: float
    z: float
    visual_preset: str
    display_name: str
    level: int
    rank: int
    ai_wander: int
    ai_combat: int
    speed_walk: int
    max_hp: int
    drops_normal: int
    drops_equipment: int
    drops_specially: int
    # ADDED this round (PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item 3):
    # which scene's roster this instance was mined from (or, for a
    # hand-built stand-in that never went through load_roster(), whichever
    # scene the caller says it belongs to).  Defaults to bg0001 so every
    # 16-positional-arg construction already in this tree (and every
    # keyword one) keeps working unchanged.  This is the field
    # mob_death.WIDENING_RULING_SCENES reads to stop a mob from ONE scene
    # riding a ruling that only ever named a DIFFERENT scene's roster, even
    # when the two share a template_id -- see that dict's own docstring
    # and field_mobs.assert_single_scene_tables' for the concrete
    # collision (31, 34, 35, 103 are hostile in both bg0001 and Bg0002).
    # It is a plain string a caller could still get wrong by hand -- see
    # assert_single_scene_tables' own "WHAT THIS DOES NOT COVER" note for
    # the residual this does NOT close.
    scene: str = field_mob_tables.SCENE

    @property
    def actor_identity(self) -> int:
        return 0x2000 + self.placement_index + 1


@dataclass(frozen=True)
class FieldMobGeneration:
    """One built collection: who is in it, its bytes, and nothing installed."""

    scene: str
    mob_count: int
    placement_indices: tuple[int, ...]
    actor_identities: tuple[int, ...]
    faction: int
    pc: bytes
    frame: bytes

    @property
    def pc_bytes(self) -> int:
        return len(self.pc)

    @property
    def frame_bytes(self) -> int:
        return len(self.frame)


def _require_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise FieldMobContractError("%s must be a finite float32 value" % label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
        raise FieldMobContractError("%s must be a finite float32 value" % label)
    return result


def _require_anchor(player_xyz: Any) -> tuple[float, float, float]:
    if type(player_xyz) is not tuple or len(player_xyz) != 3:
        raise FieldMobContractError("player XYZ must be an exact three-value tuple")
    x, y, z = (
        _require_float32(value, "player %s" % axis)
        for axis, value in zip("xyz", player_xyz)
    )
    return (x, y, z)


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise FieldMobContractError("%s must be an integer" % label)
    if not minimum <= value <= maximum:
        raise FieldMobContractError(
            "%s must be an integer in [%d,%d]" % (label, minimum, maximum)
        )
    return value


def assert_single_scene_tables(table_modules: Any) -> None:
    """Refuse the moment more than one scene's field-mob table would be merged.

    ``WIDENING_RULINGS`` (``mob_death.py``) keys a kill-permission purely by
    MOBS ``template_id``, with no scene dimension -- COO-DECISION
    2026-08-27T14:41+07:00 (answering ``CHIEF-ASK-COO`` 14:25) deferred
    adding one (a ``FieldMob.scene`` field and a scene-keyed
    ``WIDENING_RULINGS``) until a second scene actually needs it, and chose
    the lighter option instead: gate the load/merge point itself rather than
    trust every future caller to remember why merging scenes is unsafe. The
    danger is concrete, not theoretical -- bg0001's and a second scene's
    already-committed field-mob table (kept unwired by its own guard test,
    see that module's docstring) share four template ids: 31, 34, 35, 103.
    So a mob from the wrong scene could pass a ruling that only ever named
    the other one -- the same "an unnamed value passes a named check" shape
    pf-adversary caught in round ``67jejl`` for ``widened=`` strings, just at
    the scene boundary instead of the ruling-name boundary.

    [UPDATE, PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item 3] The day
    named above has arrived: :func:`load_roster` now takes a ``scene=``
    argument and can load ``field_mob_tables_bg0002`` as well as the
    original ``field_mob_tables`` (bg0001) -- and Bg0002's own mined roster
    is exactly the four-template collision this docstring warned about (31,
    34, 35, 103, the same set bg0015's already-committed, still-unwired
    table shares).  This function's OWN logic did not need to change to
    support that: it was already written generically over "the modules in
    this one tuple", never hardcoded to bg0001, so calling it with a single
    ``(field_mob_tables_bg0002,)`` tuple was already covered.  What changed
    is that COO's deferred heavier fix is now PARTLY done too, in
    ``mob_death.py`` rather than here: ``FieldMob`` carries a ``scene``
    field (set by :func:`load_roster` from the table module's own ``SCENE``
    constant) and ``mob_death.WIDENING_RULING_SCENES`` ties the bg0001 and
    Bg0002 rulings each to their own scene string, so ``kill()`` refuses a
    mob whose ``.scene`` disagrees with the ruling's, even when the
    template_id alone would have passed.  That is a call-site check paired
    with a scene-scoped ruling NAME (the lighter of the two options COO's
    decision named), not a full scene-keyed rewrite of every existing
    ``WIDENING_RULINGS`` entry -- the 916 (Training Iron Man) ruling, which
    names no real scene at all, is deliberately left untagged, and this
    function's own gate below is UNCHANGED, still doing exactly the one job
    it always did: refuse a single call site from merging two scenes'
    ``HOSTILE_PLACEMENTS`` into one roster.

    :func:`load_roster` calls this with its own one-module tuple for
    whichever scene it was asked to load, which always passes (each call
    names exactly one scene). The check exists for the day this module's
    own load/merge point is extended to combine more than one scene's rows
    into ONE roster in a SINGLE call -- which still never happens: bg0001
    and Bg0002 are each loaded by their own separate call, never merged.

    WHAT THIS DOES NOT COVER, NAMED RATHER THAN IMPLIED (pf-adversary, this
    round, re-confirmed this round). ``mob_death.kill()`` checks
    ``WIDENING_RULINGS``/``WIDENING_RULING_SCENES`` against a bare
    ``FieldMob`` argument -- it does not call :func:`load_roster` or this
    function. So a ``FieldMob`` obtained from some OTHER loader (a sibling
    function reading a scene's table, or a hand-built stand-in like
    ``mob_diag_multi_object``'s Mountain Deer body, never routed through
    this one) reaches ``kill()`` carrying whatever ``scene=`` string that
    OTHER code chose to set, unchecked by this function. This function
    closes the one call site named in COO-DECISION 2026-08-27T14:41+07:00
    (``load_roster()`` itself); it is not a cryptographic provenance tag on
    the record and cannot catch a caller that constructs a ``FieldMob`` by
    hand and sets ``scene=`` to the wrong string, deliberately or by
    mistake. Trusting a typed record's own self-reported field once
    constructed is the same trust boundary this codebase already accepts
    for every other ``FieldMob`` column (a hand-built stand-in could just as
    easily lie about ``template_id``); ``scene`` is not held to a higher
    standard than the rest of the record, and this paragraph says so rather
    than implying otherwise.
    """
    modules = tuple(table_modules)
    if not modules:
        raise FieldMobContractError("no field-mob table module given")
    scenes = []
    for module in modules:
        scene = getattr(module, "SCENE", None)
        if type(scene) is not str or not scene:
            raise FieldMobContractError(
                "field-mob table module %r has no SCENE constant" % (module,)
            )
        scenes.append(scene)
    if len(set(scenes)) > 1:
        raise FieldMobContractError(
            "refusing to merge more than one scene's field-mob table into "
            "one roster (scenes: %r) -- WIDENING_RULINGS has no scene "
            "dimension yet, see COO-DECISION 2026-08-27T14:41+07:00"
            % sorted(set(scenes))
        )


# The scene -> generated-table-module map :func:`load_roster` reads.  Adding
# a third scene means adding one line here and one new generated module --
# NOT touching the merge/guard logic, which is already scene-count-agnostic.
# Keyed by each module's own ``SCENE`` string so a typo here fails loudly
# (KeyError at import time) rather than silently loading the wrong table.
_SCENE_TABLE_MODULES = {
    field_mob_tables.SCENE: field_mob_tables,
    field_mob_tables_bg0002.SCENE: field_mob_tables_bg0002,
}
BG0002_SCENE = field_mob_tables_bg0002.SCENE


def load_roster(scene: str = field_mob_tables.SCENE) -> tuple[FieldMob, ...]:
    """Type and check ONE scene's generated roster.  No file read at import time.

    ``scene`` defaults to bg0001 (the live/default roster, unchanged from
    before this parameter existed), so every existing no-argument call site
    keeps returning exactly what it always returned.  Passing
    ``scene=field_mobs.BG0002_SCENE`` (or the literal ``"Bg0002"``) loads
    Bg0002's own mined roster instead -- a SEPARATE call, never merged with
    bg0001's: :func:`assert_single_scene_tables` runs against a one-module
    tuple for whichever scene was asked for, exactly as it always has, so
    the two scenes' rows can never land in the same returned tuple from one
    call.  Each returned :class:`FieldMob` carries the table module's own
    ``SCENE`` string, not a hardcoded literal, so the tag cannot drift from
    which table it actually came from.

    DISCOVERED, NOT FIXED, THIS ROUND: ``actor_identity`` is
    ``0x2000 + placement_index + 1`` with no scene component, so bg0001's
    and Bg0002's own small, independently-assigned placement indices
    collide on four identities (placements 58, 59, 60 and 95 -- eight
    different monsters, four shared wire identities two-by-two; see
    ``tests/test_field_mobs.py``'s
    ``test_bg0001_and_bg0002_actor_identities_are_NOT_disjoint_a_real_
    collision`` for the exact pairs).  This is harmless today because no
    caller sends both scenes' collections in one generation and this
    function itself refuses to merge their rows into one roster (see
    :func:`assert_single_scene_tables`); it would stop being harmless the
    moment a single process needs to reference both scenes' mobs at once.
    Fixing it means changing what ``actor_identity`` IS, which reaches
    ``world_population`` and the wire format -- named here rather than
    fixed, since this round was not asked to touch either.

    The generated module is data, so it is validated here rather than trusted:
    a duplicate placement, a template that cannot fit the u16 the client reads,
    a non-positive HP or an empty visual preset each refuse by name.
    """
    if type(scene) is not str or not scene:
        raise FieldMobContractError("scene must be non-empty text")
    module = _SCENE_TABLE_MODULES.get(scene)
    if module is None:
        raise FieldMobContractError(
            "no field-mob table module is registered for scene %r (known: "
            "%s)" % (scene, sorted(_SCENE_TABLE_MODULES))
        )
    assert_single_scene_tables((module,))
    return _parse_hostile_placements(module)


def _parse_hostile_placements(module: Any) -> tuple[FieldMob, ...]:
    """Type and check one table module's own ``HOSTILE_PLACEMENTS`` rows.

    The shared body :func:`load_roster` has always run, factored out
    unchanged so :func:`cross_scene_identity_collisions` (added this round)
    can read a scene's rows the SAME validated way without going through
    ``load_roster``'s own registered-scene gate (``_SCENE_TABLE_MODULES``) --
    that gate decides which scenes are LIVE/loadable, a decision this
    diagnostic function has no business making a side effect of.  A third
    scene's still-COO-gated-dormant table (see ``_KNOWN_SCENE_TABLE_MODULES_
    FOR_REPORTING`` below on why this file names it no more literally than
    that) can be measured here, by a caller who imports it from OUTSIDE this
    package, without becoming loadable through this module.
    """
    # ``SHIPPED_PLACEMENTS`` is what a table module generated from round
    # szdkgs on says this lane ships for its scene: the rows the hostility
    # predicate selects PLUS the named town targets it cannot select (a
    # practice dummy has rank 0 and no combat AI, so no predicate over MOBS
    # picks it out; see the generator's TOWN_TARGET_N_IDS).  Older modules
    # carry only ``HOSTILE_PLACEMENTS`` and are read exactly as before -- the
    # fallback is not a compatibility shim to remove later, it is the correct
    # answer for a scene whose whole roster IS its hostiles.
    rows = getattr(module, "SHIPPED_PLACEMENTS", None)
    if rows is None:
        rows = getattr(module, "HOSTILE_PLACEMENTS", None)
    if type(rows) is not list or not rows:
        raise FieldMobContractError("generated roster is missing or empty")
    mobs: list[FieldMob] = []
    seen: set[int] = set()
    # Added this round: a duplicate PLACEMENT INDEX was already refused
    # below, but two DIFFERENT placement indices sharing the exact same
    # spawn point were not -- that is the shape a hand-edited or
    # mis-mined table could still produce (two rows, two identities, one
    # spot two monsters visually stack on).  Keyed on the raw (x, y, z)
    # tuple, not on a distance threshold, because the client's own .npc
    # placements are exact coordinates, not an approximate grid -- an
    # exact match is the only claim this guard makes.  See
    # ``tests/test_field_mobs.py``'s
    # ``test_the_generator_never_places_two_monsters_on_one_spot`` for the
    # proof this actually fires on synthetic data, since the two real
    # scenes mined so far both already pass it.
    seen_positions: set[tuple[float, float, float]] = set()
    for ordinal, row in enumerate(rows):
        if type(row) is not tuple or len(row) != 16:
            raise FieldMobContractError("roster row %d has wrong shape" % ordinal)
        placement_index = _require_int(row[0], "placement index", 0, 0xDFFE)
        if placement_index in seen:
            raise FieldMobContractError("duplicate placement index in roster")
        seen.add(placement_index)
        template_id = _require_int(row[1], "template id", 1, 0xFFFF)
        x = _require_float32(row[2], "placement x")
        y = _require_float32(row[3], "placement y")
        z = _require_float32(row[4], "placement z")
        position = (x, y, z)
        if position in seen_positions:
            raise FieldMobContractError(
                "duplicate spawn position in roster: two placements share "
                "the exact same (x, y, z) -- placement %d lands on a spot "
                "another placement already claimed" % placement_index
            )
        seen_positions.add(position)
        visual_preset, display_name = row[5], row[6]
        if type(visual_preset) is not str or not visual_preset:
            raise FieldMobContractError("visual preset must be non-empty text")
        if type(display_name) is not str or not display_name:
            raise FieldMobContractError("display name must be non-empty text")
        level = _require_int(row[7], "level", 1, 255)
        # ~~rank and ai_combat were floored at 1~~ -- that floor WAS the
        # hostility predicate, asserted a second time in the parser: a row
        # could not reach here unless the generator had already selected it
        # for having both.  Round szdkgs ships a named town target (a practice
        # dummy: rank 0, no combat AI), so the floor would now refuse a row
        # this lane deliberately built.  Zero is a real value in MOBS and is
        # kept as one; what the roster ships is decided by the generator's
        # named lists, and re-checked against the crosswalk in
        # ``assert_frozen_controls`` -- not by squeezing a predicate into a
        # range check here.
        rank = _require_int(row[8], "rank", 0, 0xFFFF)
        ai_wander = _require_int(row[9], "ai wander", 0, 0xFFFF)
        ai_combat = _require_int(row[10], "ai combat", 0, 0xFFFF)
        speed_walk = _require_int(row[11], "speed walk", 0, 0xFFFF)
        max_hp = _require_int(row[12], "max hp", 1, 0xFFFFFFFF)
        mobs.append(FieldMob(
            placement_index, template_id, x, y, z, visual_preset, display_name,
            level, rank, ai_wander, ai_combat, speed_walk, max_hp,
            _require_int(row[13], "drops normal", 0, 0x7FFFFFFF),
            _require_int(row[14], "drops equipment", 0, 0x7FFFFFFF),
            _require_int(row[15], "drops specially", 0, 0x7FFFFFFF),
            scene=module.SCENE,
        ))
    return tuple(mobs)


def hostile_placement_indices() -> tuple[int, ...]:
    """The census members whose body must be replaced, for an override wiring."""
    return tuple(mob.placement_index for mob in load_roster())


def overlapping_identities(other_indices: Any) -> tuple[int, ...]:
    """Actor identities this roster shares with another placement selection.

    A non-empty result means the caller is about to send the same identity
    twice in one generation.  It is returned rather than raised because the
    intersection is the normal case for the bg0001 census: these monsters ARE
    census members, and the answer is to override their bodies, not to skip
    them.
    """
    if type(other_indices) not in (tuple, list, set, frozenset):
        raise FieldMobContractError("other indices must be a collection")
    other = set()
    for value in other_indices:
        other.add(_require_int(value, "placement index", 0, 0xDFFE))
    return tuple(
        mob.actor_identity for mob in load_roster()
        if mob.placement_index in other
    )


# The scene table modules this function compares by default: every scene
# load_roster can actually load (``_SCENE_TABLE_MODULES``).  Deliberately
# NOT the third scene's own mined table (Bg0015) here: COO-DECISION
# 2026-08-26T12:46+07:00 requires that module to stay unimported anywhere
# under this package until lane A's second travel gate and its
# geometry/reachability check pass -- this project's own test suite carries
# a dedicated guard for exactly that (walks this package's AST and a
# literal-string sweep of every file under it; deliberately not named more
# literally in THIS file, since the sweep is text-based and would flag its
# own name being spelled out here).  A module-level import of that table
# here would trip that guard even though this function only ever READS a
# module's rows, never wires one to a live path.  A caller OUTSIDE this
# package (this module's own tests among them) can still pass that third
# scene's module explicitly as one more entry in ``table_modules`` -- this
# function's own logic is scene-count-agnostic and does not care where a
# module comes from, only that it has a ``SCENE`` string and a
# ``HOSTILE_PLACEMENTS`` list.
_KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING = (
    field_mob_tables,
    field_mob_tables_bg0002,
)


def cross_scene_identity_collisions(
        table_modules: Any = None) -> tuple[dict, ...]:
    """Every placement two DIFFERENT scenes' tables both use, measured.

    ``FieldMob.actor_identity`` is ``0x2000 + placement_index + 1`` -- the
    same rule ``world_population`` uses on the wire -- with NO scene term at
    all (COO-DECISION 2026-08-27T14:41+07:00 deferred adding one; round
    `y7koj9`'s own ``load_roster`` docstring and
    ``tests/test_field_mobs.py``'s
    ``test_bg0001_and_bg0002_actor_identities_are_NOT_disjoint_a_real_collision``
    already name the four bg0001/Bg0002 pairs this finds).  Two scenes'
    placement indices are small numbers assigned independently by their own
    ``.npc`` files, so nothing stops two different scenes from mining a
    placement at the same index -- and when they do, both scenes' monsters
    compute the exact same wire ``actor_identity``.

    THIS IS A REPORT, NOT A FIX AND NOT A GUARD.  It does not raise when it
    finds a collision (a collision is the normal, expected finding for the
    tables this project has actually mined -- see the default set below);
    it returns every one it finds so a caller (a letter, a future guard, a
    console line) can act on the exact list instead of re-deriving it by
    hand.  Nothing in this tree calls it from a runtime path; it exists so
    the collision set is a computed fact any round can reproduce, not a
    number copied from a previous round's letter.

    ``table_modules`` defaults to the two scenes :func:`load_roster` can
    actually load today (``field_mob_tables`` / bg0001,
    ``field_mob_tables_bg0002`` / Bg0002).  It deliberately does NOT default
    to also including the third scene's own mined table (Bg0015): that
    module exists (mined, committed, generator-reproducible) but
    COO-DECISION 2026-08-26T12:46+07:00 requires it to stay unimported
    anywhere under this package until lane A's second travel gate and
    geometry/reachability check pass, and this project's own test suite
    walks this package's imports AND does a literal-string sweep to enforce
    that -- so a module-level import of it here would trip that guard even
    though this function only ever reads a module's own
    ``HOSTILE_PLACEMENTS``, through the same validated parse
    :func:`load_roster` uses (:func:`_parse_hostile_placements`), never
    registers it as loadable, and never wires it to a live path.  A caller
    OUTSIDE this package (this project's own tests among them) can still
    pass Bg0015's module explicitly -- ``table_modules`` accepts any modules
    with a ``SCENE`` string and a ``HOSTILE_PLACEMENTS`` list, regardless of
    where the caller imported them from.
    """
    modules = (
        _KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING
        if table_modules is None else tuple(table_modules)
    )
    if len(modules) < 2:
        raise FieldMobContractError(
            "need at least two scene table modules to compare")
    rosters: dict[str, tuple[FieldMob, ...]] = {}
    order: list[str] = []
    for module in modules:
        scene = getattr(module, "SCENE", None)
        if type(scene) is not str or not scene:
            raise FieldMobContractError(
                "field-mob table module %r has no SCENE constant" % (module,)
            )
        if scene in rosters:
            continue
        rosters[scene] = _parse_hostile_placements(module)
        order.append(scene)
    collisions: list[dict] = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            scene_a, scene_b = order[i], order[j]
            by_index_a = {mob.placement_index: mob for mob in rosters[scene_a]}
            by_index_b = {mob.placement_index: mob for mob in rosters[scene_b]}
            for placement_index in sorted(set(by_index_a) & set(by_index_b)):
                mob_a = by_index_a[placement_index]
                mob_b = by_index_b[placement_index]
                collisions.append({
                    "scene_a": scene_a,
                    "scene_b": scene_b,
                    "placement_index": placement_index,
                    "actor_identity": mob_a.actor_identity,
                    "template_a": mob_a.template_id,
                    "name_a": mob_a.display_name,
                    "template_b": mob_b.template_id,
                    "name_b": mob_b.display_name,
                })
    return tuple(collisions)


def describe_cross_scene_identity_collisions(
        table_modules: Any = None) -> tuple[str, ...]:
    """Console lines for :func:`cross_scene_identity_collisions`, ASCII-only.

    Same shape as :func:`describe_death`/:func:`describe_roster_override_coverage`
    in ``mob_death.py``: a tuple of plain-ASCII lines a caller can
    ``print()`` on the bridge's cp874 console with no further escaping, one
    per collision plus a count header.  Every display name this project has
    mined so far is plain ASCII (English monster names), so no
    cp874-mapping question exists here today; a future scene whose mined
    name is not would need this function to reject it rather than print
    garbage -- ``cross_scene_identity_collisions`` already only accepts
    ``str`` names, so a non-ASCII one would print as-is (that gap belongs to
    whoever wires ``print()`` calls to a cp874 console, not this pure
    string builder, matching every other ``describe_*`` in this codebase).
    """
    collisions = cross_scene_identity_collisions(table_modules)
    lines = [
        "FIELD_MOB_CROSS_SCENE_IDENTITY_COLLISIONS count=%d" % len(collisions)
    ]
    for collision in collisions:
        lines.append(
            "  identity=0x%X placement=%d %s(template=%d name=%s) vs "
            "%s(template=%d name=%s)" % (
                collision["actor_identity"], collision["placement_index"],
                collision["scene_a"], collision["template_a"], collision["name_a"],
                collision["scene_b"], collision["template_b"], collision["name_b"],
            )
        )
    return tuple(lines)


def assert_frozen_controls(legacy: Any) -> None:
    """Refuse if this scene's roster no longer agrees with the crosswalk.

    ~~This is the check that keeps the derived HP column and the mined name
    honest.  It compares against ``v141``'s own constants, which were pinned
    from a different direction (a live run, not a table join).~~
    WITHDRAWN AS THE CONTROL, round szdkgs (2026-08-29), and the withdrawal is
    the point of this round: ``V117_P30_EXACT_HP`` (3857) and
    ``V119_P30_TARGET_NAME`` ("Tornado Eagle") are what placement 30 looks
    like when a Mob-SET number is read as a ``MOBS.n_ID``.  ``v141`` pinned
    them from a live run of a server making that same read, so the two
    directions were never independent, and this check could not have caught
    the one thing that was wrong.  ``GT-078`` (the owner rejecting every name
    on sight) and ``RE-128`` (the client's own ``SCENE_NAME`` ->
    ``CLINE.n_LEADER_BK1`` crosswalk) between them settled it: bg0001
    placement 30 is Mob-Set 31 -> ``n_ID`` 248, "Da Vinci".  The two legacy
    constants are NOT deleted -- they are still true statements about the
    legacy reading, and the generated table records them as such in
    ``LEGACY_SETNUM_READING_OF_PLACEMENT_30``.

    WHAT IS CHECKED INSTEAD, and why it is not circular: every shipped row is
    held against :mod:`world_port_royal_identity`, which lane A mined from the
    same client tables INDEPENDENTLY (a different tool, a different round, its
    own owner anchors) and committed into this repository.  Two separately
    mined tables agreeing on ``n_ID``, avatar template and displayed name for
    every row this lane ships is a real second opinion; re-deriving one table
    from itself never was.  Scenes with no committed crosswalk table (Bg0002,
    whose Mob-Set numbers ARE its ``n_ID`` by the owner's own 2026-08-27
    ruling) are not held to it -- see the scene guard below.
    """
    from . import world_port_royal_identity

    roster = load_roster()
    if not roster:
        raise FieldMobContractError("roster is empty")
    scene_numbers = getattr(field_mob_tables, "SET_NUMBER_FOR_PLACEMENT", None)
    rule = getattr(field_mob_tables, "IDENTITY_RULE", None)
    if rule != "cline" or type(scene_numbers) is not dict:
        raise FieldMobContractError(
            "bg0001's table is not the crosswalk-resolved one (IDENTITY_RULE "
            "%r): regenerate it with tools/pf_mine_scene_mob_roster.py "
            "--identity-rule cline" % (rule,)
        )
    per_placement = getattr(
        field_mob_tables, "IDENTITY_RULE_PER_PLACEMENT", {},
    )
    for mob in roster:
        set_number = scene_numbers.get(mob.placement_index)
        if set_number is None:
            raise FieldMobContractError(
                "roster row %d carries no Mob-Set number, so its identity "
                "cannot be re-resolved" % mob.placement_index
            )
        if per_placement.get(mob.placement_index) != "cline":
            # A row the table itself labels as the legacy set-number reading,
            # kept for one more round with its migration named (see the
            # generated module's LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION).
            # It is held to the ONE thing that reading claims -- that the
            # shipped template id IS the scene file's Mob-Set number -- so a
            # row cannot drift into being neither reading.  It is deliberately
            # NOT held to the crosswalk: it is known not to match, and that
            # mismatch is written down per row rather than asserted away.
            if mob.template_id != set_number:
                raise FieldMobContractError(
                    "placement %d is labelled the legacy set-number reading "
                    "but ships n_ID %d for Mob-Set %d"
                    % (mob.placement_index, mob.template_id, set_number)
                )
            continue
        identity = world_port_royal_identity.resolve(set_number)
        if identity is None:
            raise FieldMobContractError(
                "Mob-Set %d (placement %d) does not resolve in the committed "
                "crosswalk" % (set_number, mob.placement_index)
            )
        if mob.template_id != identity.mobs_n_id:
            raise FieldMobContractError(
                "placement %d ships n_ID %d, the crosswalk says %d"
                % (mob.placement_index, mob.template_id, identity.mobs_n_id)
            )
        if mob.visual_preset != identity.outfit:
            raise FieldMobContractError(
                "placement %d ships avatar %r, the crosswalk says %r"
                % (mob.placement_index, mob.visual_preset, identity.outfit)
            )
        if mob.display_name != identity.name:
            raise FieldMobContractError(
                "placement %d ships name %r, the crosswalk says %r"
                % (mob.placement_index, mob.display_name, identity.name)
            )
    # The town targets are named, not predicated (see the generator).  A row
    # that lost its name or its rank-0/AI-0 shape is no longer the dummy this
    # lane decided to ship, so it refuses rather than shipping something else
    # under that decision.
    for mob in roster:
        if mob.template_id != TOWN_TARGET_N_ID:
            continue
        if mob.display_name != TOWN_TARGET_NAME:
            raise FieldMobContractError(
                "town target %d is named %r, not %r"
                % (mob.template_id, mob.display_name, TOWN_TARGET_NAME)
            )
        if mob.rank or mob.ai_combat:
            raise FieldMobContractError(
                "town target %d is no longer rank 0 / no combat AI "
                "(rank %r, ai_combat %r): it is not a practice dummy any more"
                % (mob.template_id, mob.rank, mob.ai_combat)
            )
    # ~~The legacy constants, kept reachable so a reader can see they were not
    # deleted.~~  Read, not asserted: v141 still carries them and they still
    # describe the legacy reading exactly.
    _ = (
        getattr(legacy, "V117_P30_EXACT_HP", None),
        getattr(legacy, "V119_P30_TARGET_NAME", None),
        getattr(legacy, "V112_MONSTER_INDEX", None),
    )


def _faction_splice_offset(
    legacy: Any,
    baseline: bytes,
    template_id: int,
    visual_preset: str,
) -> int:
    """Where bit 0x0400 lands: right after the BasicAttr block, before NPCAttr's.

    Computed from the legacy serializers rather than written down, because the
    BasicAttr block ends at a variable offset once a name is present.  The
    NPCAttr tail is fixed-shape, so the position is ``len(baseline) - len(tail)``.
    """
    npc_mask = 0x01 | (0x04 if visual_preset else 0)
    tail = (
        bytes(legacy.u8tag(0x0B, npc_mask))
        + bytes(legacy.u16tag(0x12, template_id))
    )
    if visual_preset:
        tail += bytes(legacy.wstr_tag(visual_preset))
    if not baseline.endswith(tail):
        raise FieldMobContractError(
            "frozen make_npc_attr tail drift: the NPCAttr block is no longer "
            "mask + template + preset, so the faction splice position is stale"
        )
    return len(baseline) - len(tail)


def hostile_npc_attr(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int | None = None,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> bytes:
    """The frozen named body plus its own mined speed and level, plus
    EXACTLY the faction bytes.

    The result is refused unless it equals ``legacy.make_npc_attr(...)`` for
    the same monster with the BasicAttr mask widened by exactly bits
    0x0002 (level) and 0x0400 (faction), each tagged value spliced in at its
    own ascending-mask-bit position.  Any other delta means a field landed
    somewhere else and no bytes come back.

    ``movement_speed`` (COO-DECISION 2026-08-28T01:46+07:00, answering
    PANYA-DECISION 2026-08-28T01:25+07:00 item 3) is always passed as
    ``float(mob.speed_walk)``.  ``legacy.make_npc_attr`` has carried this
    exact parameter, at this exact BasicAttr bit (0x0040, float at +0x54),
    with its own independent static RE chain (0x45C103 reads MOBS+0x3C /
    n_SPEED_WALK; 0x464960 the setter; 0x45D2EA/0x484580 the
    movement-control consumer) since before this module existed -- see that
    function's own docstring.  ``mob.speed_walk`` is ``field_mob_tables``'s
    own mined MOBS column for this exact monster, not a guess (every row
    mined so far in both live scenes is 100 -- see
    ``tests/test_field_mobs.py``'s
    ``test_the_speed_field_carries_the_mined_value_not_the_owners_pc_guess``).

    ``level`` (RE-117, this round) is spliced in the same way: bit 0x0002,
    u16 tag 0x12, at the position right after the mask value and the
    optional name -- computed here, not written into ``legacy.py``, because
    that module belongs to chief.  RE-117 traced NPCAttr serializer
    ``0x00466EB0`` calling common BasicAttr serializer ``0x004656F0`` before
    NPC-only fields, so the bit/offset/tag the owner's PC-actor probe found
    for this base object applies to an NPCAttr body too -- not just a leap
    off that probe.  ``mob.level`` is ``field_mob_tables``'s mined
    ``MOBS.n_LEVEL_MIN``/``n_LEVEL_MAX`` column, never a guess.  MP
    current/max are proven the same base-object bits (0x0010/0x0020) by
    RE-117 but are NOT added here: the mined gamedata this project has has
    no MP source for a mob/NPC, and inventing one would violate the
    two-layer evidence rule -- see RE-117's own nonclaims.

    What did NOT get either treatment, and why, is in
    ``pf_bridge/CLIENT_RE_QUEUE.md`` (see the round's PR body): every other
    x-numbered field in the owner's completeness table either has no
    NPCAttr/BasicAttr bit at all in this codebase (class id, epithet,
    sub-class, SP, STR/CON/DEX/INT/PER, EXP, money, guild, CP, alias -- the
    whole ``Actor`` b0-b41 block the table names) or is MP, covered above.
    """
    if type(mob) is not FieldMob:
        raise FieldMobContractError("mob must be the typed FieldMob record")
    if type(with_name) is not bool:
        raise FieldMobContractError("with_name must be a bool")
    _require_int(faction, "faction", 0, 0xFFFFFFFF)
    if faction == 0:
        raise FieldMobContractError(
            "faction 0 is the player constructor default: arena-v2 counted "
            "1,023 neutral results for that pairing, so it spawns a monster "
            "that is merely present"
        )
    hp = mob.max_hp if current_hp is None else _require_int(
        current_hp, "current hp", 0, 0xFFFFFFFF,
    )
    if hp == 0:
        raise FieldMobContractError(
            "a spawn at zero HP walks into the death lane's predicates and "
            "answers a different question than this module asks"
        )
    name = mob.display_name if with_name else ""
    baseline = legacy.make_npc_attr(
        mob.template_id,
        mob.actor_identity,
        scene_id,
        scene_sequence,
        mob.visual_preset,
        hp,
        mob.max_hp,
        movement_speed=float(mob.speed_walk),
        basic_name=name,
    )
    offset = _faction_splice_offset(
        legacy, baseline, mob.template_id, mob.visual_preset,
    )
    mask_at = _basic_mask_offset(legacy, baseline, mob.actor_identity)
    mask = int.from_bytes(baseline[mask_at:mask_at + 2], "little")
    if bool(mask & BASIC_BIT_NAME) is not bool(name):
        raise FieldMobContractError(
            "frozen make_npc_attr name bit drift: mask 0x%04X does not agree "
            "with a %s body" % (mask, "named" if name else "nameless")
        )
    if mask & BASIC_BIT_FACTION:
        raise FieldMobContractError(
            "frozen make_npc_attr already sets bit 0x0400; the splice below "
            "would double the field"
        )
    if mask & BASIC_BIT_LEVEL:
        raise FieldMobContractError(
            "frozen make_npc_attr already sets bit 0x0002; the level splice "
            "below would double the field"
        )
    name_bytes = bytes(legacy.wstr_tag(name)) if name else b""
    level_at = mask_at + 2 + len(name_bytes)
    if level_at > offset:
        raise FieldMobContractError(
            "level splice point falls after the faction splice point; the "
            "frozen body layout moved and this composer needs re-deriving"
        )
    composed = (
        baseline[:mask_at]
        + int(mask | BASIC_BIT_FACTION | BASIC_BIT_LEVEL).to_bytes(2, "little")
        + baseline[mask_at + 2:level_at]
        + bytes(legacy.u16tag(LEVEL_TAG, mob.level))
        + baseline[level_at:offset]
        + bytes(legacy.u32tag(FACTION_TAG, faction))
        + baseline[offset:]
    )
    if len(composed) != len(baseline) + FACTION_SPLICE_BYTES + LEVEL_SPLICE_BYTES:
        raise FieldMobContractError("hostile NPCAttr length drift")
    return composed


def _basic_mask_offset(legacy: Any, baseline: bytes, actor_identity: int) -> int:
    """The offset of the BasicAttr u16 mask VALUE inside a frozen body."""
    head = (
        bytes(legacy.u8tag(0x0B, 1))
        + bytes(legacy.qwordtag(0x32, actor_identity))
    )
    if not baseline.startswith(head):
        raise FieldMobContractError(
            "frozen make_npc_attr head drift: the body no longer opens with "
            "the DBAttribute mask and the tagged identity"
        )
    # +1 skips the mask's own tag byte and lands on the little-endian u16.
    return len(head) + 1


def hostile_actor_entry(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int | None = None,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> bytes:
    """One actor entry: hostile named NPCAttr plus the frozen full-mask movement.

    This is the piece an override wiring needs - build the census, then replace
    the entries for :func:`hostile_placement_indices` with these.
    """
    npc_attr = hostile_npc_attr(
        legacy, mob, current_hp=current_hp, scene_id=scene_id,
        scene_sequence=scene_sequence, faction=faction, with_name=with_name,
    )
    movement = legacy.make_remote_movement_attr(
        mob.actor_identity, mob.x, mob.y, mob.z,
        HEADINGS[mob.placement_index & 3],
        mask=FULL_MOVEMENT_MASK,
    )
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE,
        mob.actor_identity,
        [(NPC_ATTR_ID, npc_attr), (MOVEMENT_ATTR_ID, movement)],
    )


def nearest_first(
    player_xyz: tuple[float, float, float],
    roster: tuple[FieldMob, ...] | None = None,
) -> tuple[FieldMob, ...]:
    """Order the roster nearest-first, ties broken by placement index."""
    x, y, z = _require_anchor(player_xyz)
    mobs = load_roster() if roster is None else roster
    ordered = sorted(
        mobs,
        key=lambda mob: (
            (mob.x - x) ** 2 + (mob.y - y) ** 2 + (mob.z - z) ** 2,
            mob.placement_index,
        ),
    )
    return tuple(ordered)


def neighbour_census(radius: float) -> dict:
    """How many monsters share a neighbourhood of ``radius`` with another.

    The measurement behind this module's refusal to promise a crowded view.
    ``best`` is the placement with the most neighbours; ``best_count`` counts
    the neighbours only, not the placement itself.
    """
    limit = _require_float32(radius, "radius")
    if limit <= 0.0:
        raise FieldMobContractError("radius must be positive")
    roster = load_roster()
    limit_squared = limit * limit
    counts = {}
    for mob in roster:
        counts[mob.placement_index] = sum(
            1 for other in roster
            if other is not mob
            and (other.x - mob.x) ** 2
            + (other.y - mob.y) ** 2
            + (other.z - mob.z) ** 2 <= limit_squared
        )
    best = max(sorted(counts), key=lambda index: (counts[index], -index))
    return {
        "radius": limit,
        "mob_count": len(roster),
        "with_a_neighbour": sum(1 for value in counts.values() if value),
        "best": best,
        "best_count": counts[best],
        "counts": counts,
    }


def build_field_mob_population(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    mob_count: int | None = None,
    *,
    faction: int = FIELD_MOB_FACTION,
    with_name: bool = True,
) -> FieldMobGeneration:
    """Build the scene's monsters as ONE RuntimeRes collection, nearest first.

    Nothing is sent, scheduled or persisted.  The caller owns dispatch, owes
    the frame the reapply the accepted evidence was measured with
    (:data:`INITIAL_REAPPLY_MS`), and owes the player half of the pairing
    (faction :data:`PLAYER_PAIR_FACTION` on StartGame) without which these
    monsters are present but neutral.

    Sending this collection alongside the lane-A census duplicates thirteen
    actor identities - see :func:`overlapping_identities`.
    """
    assert_frozen_controls(legacy)
    roster = nearest_first(player_xyz)
    if mob_count is None:
        count = len(roster)
    else:
        count = _require_int(mob_count, "mob count", 1, len(roster))
    selected = roster[:count]
    entries = [
        hostile_actor_entry(
            legacy, mob, faction=faction, with_name=with_name,
        )
        for mob in selected
    ]
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise FieldMobContractError("frame drift")
    return FieldMobGeneration(
        field_mob_tables.SCENE,
        count,
        tuple(mob.placement_index for mob in selected),
        tuple(mob.actor_identity for mob in selected),
        faction,
        pc,
        frame,
    )


PIN_ID = "port_royal_field_mobs_hostile_001"
PIN_BUILD_ORDER = "BUILD-004 / FIELD-MOBS-001"
PIN_LANE = "B_COMBAT"


def pin_document(legacy: Any) -> dict:
    """The pin that ships in ``scenarios/`` - a description, not a switch.

    No flag loads this and no loader accepts it.  It exists so an attended
    ticket can state what this lane expects BEFORE the run, in the same shape
    lane A's ``world_population_full_001.json`` uses, and so the expectations
    cannot drift away from the code that produces them: a test compares the
    committed file against this function.
    """
    assert_frozen_controls(legacy)
    anchors = (
        ("v141_V134_PLAYER_XYZ",
         (legacy.V134_PLAYER_X, legacy.V134_PLAYER_Y, legacy.V134_PLAYER_Z)),
        ("v141_V135_PLAYER_XYZ",
         (legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y, legacy.V135_PLAYER_Z)),
    )
    roster = load_roster()
    built = [
        (label, build_field_mob_population(legacy, anchor))
        for label, anchor in anchors
    ]
    close = neighbour_census(1000.0)
    wide = neighbour_census(2000.0)
    return {
        "schema": 1,
        "id": PIN_ID,
        "lane": PIN_LANE,
        "build_order": PIN_BUILD_ORDER,
        "test_only": test_only,
        "production_allowed": production_allowed,
        "selection": "none_default_behaviour_no_scenario_flag",
        "not_a_scenario": (
            "this file is a pin, not a switch - no flag loads it and no "
            "scenario loader accepts it"
        ),
        "scene": field_mob_tables.SCENE,
        "source_digests": dict(field_mob_tables.SOURCE_DIGESTS),
        "predicate_census": dict(field_mob_tables.PREDICATE_CENSUS),
        "hostility": {
            "basic_attr_mask_bit": BASIC_BIT_FACTION,
            "wire_tag": FACTION_TAG,
            "npc_side_value": FIELD_MOB_FACTION,
            "player_side_value": PLAYER_PAIR_FACTION,
            "both_halves_required": True,
            "player_half_owner": "start_game_path_in_the_chiefs_file",
        },
        "population": {
            "trigger": "caller_owned_no_dispatch_in_this_module",
            "order": "nearest_first_by_squared_distance_then_placement_index",
            "initial_reapply_ms": INITIAL_REAPPLY_MS,
            "mob_count": len(roster),
            "distinct_templates": len({mob.template_id for mob in roster}),
            "actor_type": NPC_STYLE_ACTOR_TYPE,
            "shares_identity_space_with": "world_population_bg0001_census",
        },
        "anchors": [
            {
                "label": label,
                "x": generation_anchor[0],
                "y": generation_anchor[1],
                "z": generation_anchor[2],
                "pc_bytes": generation.pc_bytes,
                "frame_bytes": generation.frame_bytes,
                "placement_indices": list(generation.placement_indices),
            }
            for (label, generation_anchor), (_, generation)
            in zip(anchors, built)
        ],
        "roster": [
            {
                "placement_index": mob.placement_index,
                "actor_identity": mob.actor_identity,
                "template_id": mob.template_id,
                "display_name": mob.display_name,
                "visual_preset": mob.visual_preset,
                "level": mob.level,
                "max_hp": mob.max_hp,
                "x": mob.x,
                "y": mob.y,
                "z": mob.z,
                "drops_normal": mob.drops_normal,
                "drops_equipment": mob.drops_equipment,
                "drops_specially": mob.drops_specially,
            }
            for mob in roster
        ],
        "this_scene_cannot_crowd_one_view": {
            "with_a_neighbour_within_1000": close["with_a_neighbour"],
            "densest_placement_within_2000": wide["best"],
            "its_neighbour_count": wide["best_count"],
        },
        "nonclaims": [
            "faction 1 and 6 are OUR design, not the original server's",
            "named AND hostile in one body has never been on the wire: the "
            "named half is V119/V117, the hostile half is GT-032, the "
            "combination is new",
            "no claim about NAME COLOUR - what decides it is RE-067, open, "
            "lane C. [STALE as of pf_bridge/CLIENT_RE_QUEUE.md chief "
            "R163/R165, 2026-08-25, round dvxb6f] [MEASURED]: RE-067 is "
            "CLOSED (PASS/MIXED, actor half BOUNDED NEGATIVE) - still no "
            "claim about name colour, but the static-layer search is "
            "finished, not open; GT-084/RIDER-084-A carries the "
            "client-observable question now",
            "no aggro, no attack, no death, no drop: this lane builds the "
            "monster, not the fight",
            "max_hp is DERIVED from STANDARD_MOB by level; the two frozen "
            "controls it re-derives are placement 30 only",
            "nothing imports this module, so on its own it changes nothing "
            "the player sees",
            "RE-098 (2026-08-27, DONE / BOUNDED-NEGATIVE) closed off using "
            "the raw definition payload's b5/b15/u32@11 as level/rank/"
            "spawn-rate shortcuts - none of the three matched on the "
            "measured crosswalk. This module never read those bytes; "
            "level/rank/max_hp come from MOBS/STANDARD_MOB proper",
            "HEADINGS (the four spawn-facing values below) is OUR synthetic "
            "cosmetic round-robin, not recovered per-placement data - "
            "RE-116 (2026-08-28, DONE / BOUNDED-NEGATIVE) confirmed the "
            "wire mechanism (MovementAttr+0x34, mask bit 0x02, exactly what "
            "hostile_actor_entry already sends) but found no crosswalk from "
            "either the raw .npc placement bytes or "
            "CONSTDATA_TH__MARKER.n_DIRTECTION to an authentic per-mob "
            "heading value",
        ],
    }


def roster_report(legacy: Any, player_xyz: tuple[float, float, float]) -> dict:
    """What a ticket needs to pin expectations before an attended run.

    ASCII-safe by construction: every string in the roster is escaped on the
    way out, because this report is printed on a code page 874 console.
    """
    assert_frozen_controls(legacy)
    generation = build_field_mob_population(legacy, player_xyz)
    x, y, z = _require_anchor(player_xyz)
    rows = []
    for mob in nearest_first(player_xyz):
        distance = math.sqrt(
            (mob.x - x) ** 2 + (mob.y - y) ** 2 + (mob.z - z) ** 2
        )
        rows.append({
            "placement_index": mob.placement_index,
            "actor_identity": mob.actor_identity,
            "template_id": mob.template_id,
            "display_name": ascii(mob.display_name),
            "visual_preset": ascii(mob.visual_preset),
            "level": mob.level,
            "max_hp": mob.max_hp,
            "distance": round(distance, 3),
        })
    return {
        "scene": field_mob_tables.SCENE,
        "anchor": [x, y, z],
        "mob_count": generation.mob_count,
        "distinct_templates": len({mob.template_id for mob in load_roster()}),
        "faction": generation.faction,
        "player_pair_faction": PLAYER_PAIR_FACTION,
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
        "pc_bytes": generation.pc_bytes,
        "frame_bytes": generation.frame_bytes,
        "source_digests": dict(field_mob_tables.SOURCE_DIGESTS),
        "predicate_census": dict(field_mob_tables.PREDICATE_CENSUS),
        "mobs": rows,
    }
