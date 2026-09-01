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
bg0001 is a town and its monster placements are sparse.  ~~All thirteen exist,
but no monster in this roster has ANOTHER monster within 1,000 units, and the
densest spot in the whole scene - the Mutant Green Eagle line near
(14455, 9357, 2200) - holds three within 2,000 units and four within about
3,900.  The nearest monster to a new character's spawn is 12,095 units away.
So this module delivers "the monsters this scene's own data defines exist and
are hostile"~~ -- ROUND szdkgs, and the correction is bigger than the numbers:
bg0001 is a town in the strong sense.  Resolved through the RE-128 crosswalk,
ZERO of its placements have both a rank and a combat AI; the ~~thirteen~~ four
rows
this module ships are four real practice dummies (n_ID 916 "Training Iron
Man", the line near (14455, 9357, 2200) that the struck-through paragraph
called Mutant Green Eagle) plus nine placements still carrying the legacy
set-number reading, which are Port Royal's own townspeople and are labelled as
such per row in the generated table.  The distances above still describe those
same placements, because no placement moved (~~thirteen~~ four of them ship
since round 8ftmbx).  What this module
delivers today is "the actors this scene's data defines exist, four of them
under their real identity", and it does NOT deliver "a field full of red names
in one view", nor -- until the remaining nine are migrated -- "every actor
under its real identity".
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
    census in the same generation would put every roster identity on the wire
    (~~thirteen~~ four since round 8ftmbx)
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

[STALE as of commit ``5a272a0``, "Wire two CORE-REQUESTs: measured stowaways
line and scene-consistent census override", 2026-08-29 (see
``pf_bridge/notes_to_chief/20260829_1603_CHIEF-REPLY-two-core-requests-wired-
stowaways-and-census-override-sync.md``)] [MEASURED, by call-site reading,
round qlrf4j 2026-09-01]: the sentence above is now false in the direction
that matters.  ``runtime.py`` DOES call ``mob_death.full_roster_override``
(grep ``mob_death_override = mob_death.full_roster_override(`` in
``runtime.py``'s world-census composer) - the narrower ``corpse_override``
call site this paragraph described is gone, replaced by the wider override.
So this module's headline claim ("never sent, never observed") is ALSO
stale: the named+hostile combination this module builds IS on the wire now,
on every boot that reaches that composer, gated on the scene's ledger being
in sync (see ``runtime.py``'s own comments at that call site for the one
case - an unaddressed registry - where the override still does not fire).
What remains unmeasured is unchanged from the rest of this docstring: no
attended round has separately confirmed the CLIENT renders a named+hostile
body correctly (RE-067 is CLOSED per the correction above, but what
actually decides name colour is still unidentified); this correction only
fixes the WIRING claim, not a new client observation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mob_tables
from . import field_mob_tables_bg0002
# Lane A's scene-id registry, read-only: the ONE public reader from a scene
# id to that scene's own folder name (COO-DECISION 2026-08-29T08:48+07:00
# item 3).  Imported for :func:`scene_for_scene_id`; nothing here writes to
# it, and this module ships no second copy of that mapping.
from . import world_scene_folder
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
# tools/pf_mine_scene_mob_roster.py's TOWN_TARGET_N_IDS for the reasoning.
# ~~and the [LANE-B ASSUMPTION - AWAITING COO CONFIRMATION] label on it.~~
# The label is gone because the answer came: COO-DECISION 2026-08-29T00:41+07:00
# approved shipping these four, enemy-coloured name included, ON THE CONDITION
# that 916 is never counted as a monster of Port Royal.  It is a practice dummy:
# rank 0, no combat AI, no drop table, and it is in TOWN_TARGET_PLACEMENTS, not
# in HOSTILE_PLACEMENTS -- which is empty for bg0001 and stays empty.
TOWN_TARGET_N_ID = 916
TOWN_TARGET_NAME = "Training Iron Man"
# STANDARD_MOB[100].n_HPMAX, the derived column's value for this actor.
TOWN_TARGET_LEVEL = 100
TOWN_TARGET_MAX_HP = 198125

# Which placements this lane ships under which identity rule.  Hand-written
# here so the generated table cannot certify its own labelling: relabelling a
# row in field_mob_tables.py now contradicts this file instead of escaping the
# check (pf-adversary, round szdkgs).  Both sets move only in a round that
# means to move them.
# ~~EXPECTED_LEGACY_PLACEMENTS = frozenset({12, 30, 33, 58, 59, 60, 63, 95,
# 132})~~  MIGRATED, round 8ftmbx (2026-08-29): the nine rows the set-number
# reading selected are withdrawn from what this lane ships, on the one-round
# ceiling COO-DECISION 2026-08-29T00:41+07:00 put on them.  The set is empty
# rather than deleted so the gate keeps its teeth in the other direction: a
# row that reappears labelled 'setnum' now fails the shape gate instead of
# being silently accepted, which is what deleting the branch would have done.
# Who each of those nine placements really is stays readable per row in the
# generated module's WITHDRAWN_UNDER_THIS_RULE.
EXPECTED_CROSSWALK_PLACEMENTS = frozenset({103, 105, 107, 109})
EXPECTED_LEGACY_PLACEMENTS: frozenset[int] = frozenset()

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
    see that module's docstring) ~~share four template ids: 31, 34, 35, 103~~
    -- round 8ftmbx: bg0001 ships only n_ID 916 now, so today they share none.
    The guard stays because the danger is structural, not a property of one
    roster: a mob from the wrong scene could pass a ruling that only ever
    named the other one -- the same "an unnamed value passes a named check" shape
    pf-adversary caught in round ``67jejl`` for ``widened=`` strings, just at
    the scene boundary instead of the ruling-name boundary.

    [UPDATE, PANYA-DECISION 2026-08-27T20:10+07:00 "M1-P" item 3] The day
    named above has arrived: :func:`load_roster` now takes a ``scene=``
    argument and can load ``field_mob_tables_bg0002`` as well as the
    original ``field_mob_tables`` (bg0001) -- and Bg0002's own mined roster
    is exactly the four-template collision this docstring warned about (31,
    34, 35, 103, ~~the same set bg0015's already-committed, still-unwired
    table shares~~ -- NO LONGER TRUE since round ua236k: that table was
    re-mined through the crosswalk per COO-DECISION 20260829_0345 and its
    templates are now 343/345/348/350/353/355/924, which overlap Bg0002's
    set on nothing.  Bg0002 itself still ships under the older reading, so
    its own four templates are unchanged).  This function's OWN logic did not need to change to
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


def assert_scene_table_keys_match_their_own_modules(table: Any) -> None:
    """Refuse a scene->module table whose key is not that module's own SCENE.

    ROUND qf83nz (carried six rounds as debt item 4 before this one closed
    it).  ``_SCENE_TABLE_MODULES`` is written today so this can never actually
    fire -- every key literal IS ``module.SCENE`` read off the module, not a
    retyped string -- but that is a property of how the dict happens to be
    spelled, not something anything checked.  A future hand-edit that adds a
    third scene by pasting an existing line and forgetting to swap the value
    (``field_mob_tables_bg0002.SCENE: field_mob_tables,`` -- right-hand side
    stale) would silently serve one scene's real MOBS rows under another
    scene's name: exactly the kind of mismatch this M3 module exists to rule
    out, just moved into its own registry instead of the mined tables it
    reads.  ``load_roster`` would still return rows (no KeyError, because the
    lookup key that broke is the map's OWN key, not a caller's), so nothing
    downstream would raise -- a player would just see one field map's
    monsters standing in another field map.

    Deliberately independent of :func:`assert_single_scene_tables`: that
    guard stops two DIFFERENT scenes' rows from being merged into one
    roster; this one stops a single scene's own table from being filed
    under the wrong name in the first place.  Neither implies the other.
    """
    mismatched = [
        (key, module, getattr(module, "SCENE", None))
        for key, module in table.items()
        if getattr(module, "SCENE", None) != key
    ]
    if mismatched:
        raise FieldMobContractError(
            "scene table module(s) filed under the wrong key: %s -- each "
            "key must equal that module's own SCENE constant"
            % [
                "%r maps to %r whose own SCENE is %r" % row
                for row in mismatched
            ]
        )


assert_scene_table_keys_match_their_own_modules(_SCENE_TABLE_MODULES)


def live_scenes() -> tuple[str, ...]:
    """The scenes :func:`load_roster` will actually load, in a stable order.

    ROUND j0u64p.  ``_SCENE_TABLE_MODULES`` has always been the one place that
    decides which scenes are LIVE (as opposed to mined-but-dormant, which
    ``_KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING`` covers), and a caller that
    needs to walk every shipped roster had no way to ask without reaching into
    a private name.  ``mob_death.describe_widening_coverage`` is the first
    such caller: it reports which shipped monsters an owner letter authorises
    killing, so it must walk the same scene list ``load_roster`` obeys and not
    a second hand-typed copy of it that can drift.  That drift is not
    hypothetical to guard against -- a stale copy here would make a
    REGISTERED scene's whole roster vanish from that report with no line
    saying so -- so ``tests/test_mob_death_wired_widening.py`` pins this to
    ``_SCENE_TABLE_MODULES`` by set equality, not merely by "everything it
    returns loads".

    Sorted rather than dict-ordered, so a caller that pins this value is
    pinning the SET of live scenes and not the order two module-level
    assignments happen to appear in.
    """
    return tuple(sorted(_SCENE_TABLE_MODULES))


# (scene folder) -> placement indices the OWNER ruled out by hand, with the
# source table's own reason string beside them.  ROUND wmomy7.
#
# WHY THIS LIVES HERE AND NOT IN THE GENERATED TABLE.  ``field_mob_tables_
# bg0002.py`` says "GENERATED - do not hand-edit ... Regenerate rather than
# patch", and the generator reads game data that exists only on the bridge
# clone, so it cannot be re-run here.  A hand-edit of the generated rows
# would be silently undone by the next real regeneration.  The generated
# module is DATA (which placements resolve, under this lane's identity
# rule); an owner's ruling about which resolved rows this lane may ship is
# POLICY, and policy belongs at the loader, which is this lane's own code
# and survives regeneration.
#
# WHAT THE OWNER ACTUALLY RULED.  ``scene2_prison_exile_tables
# .UNRESOLVED_PLACEMENTS`` carries placements 92-96 with the reason
# ``n_id_101_104_block_meaning_unknown_owner_says_do_not_place``.  Lane A's
# census reads that table and therefore never sends those five bodies (97
# actors, ids 0x2001..0x206A, with 0x205D-0x2061 absent -- MEASURED, round
# wmomy7).  This lane's generated table resolves them anyway under the
# ``setnum`` rule, as five "Orc Chief" rows, because the two rules disagree
# about the 101-104 n_id block -- and the owner settled that disagreement.
#
# The literal is kept here rather than joined against the scene table at
# load time on purpose: this is the hot roster path, and a cross-lane import
# join is exactly the shape that fails silently.  The agreement between this
# literal and the source table is checked instead by
# ``mob_census_hostility.assert_owner_refusals_match_scene_source()``, which
# the suite runs, so drift goes red in a test rather than on a player's
# screen.
# THE WHOLE RULING, NOT THE PART THAT BITES TODAY.  The owner's ruling on
# the n_id 101-104 block covers EIGHT placements (89, 90, 92-97); this
# lane's generated table happens to ship only five of them (92-96) under
# the current mining rule.  The literal carries all eight on purpose: a
# regeneration that starts resolving placement 89 or 97 must be refused
# without anyone having to notice, and the drift guard compares against the
# ruling, not against today's intersection with it.
# (Placement 65 is in the same source list under a DIFFERENT reason --
# "no_mobs_row_for_this_n_id_no_body_data" -- which is a mining limit, not
# an owner ruling, and is deliberately NOT carried here.)
# CONFIRMED RETROACTIVELY BY THE COO, round z096sw.  ``pf_bridge/notes_to_
# chief/20260829_1741_COO-DECISION-owner-refused-block-filter-confirmed-
# aggro-ticket-before-m6.md`` (answering this lane's ASK-COO of 16:05)
# rules that this literal, the ``load_roster`` filter and
# ``assert_owner_refusals_match_scene_source`` are the STANDING line until
# the meaning of the n_id 101-104 block is PROVEN -- and that the only way
# back into the roster for these placements is evidence of that meaning
# plus a fresh ruling, never a regeneration under a different mining rule
# ("regenerating under another rule is guessing a new identity scheme,
# which the same owner order already forbids").  The ruling also states
# that this lane did not need approval to STOP disobeying an owner order,
# which is why the filter shipped in wmomy7 rather than waiting here.
OWNER_REFUSED_PLACEMENTS: dict[str, tuple[int, ...]] = {
    'Bg0002': (89, 90, 92, 93, 94, 95, 96, 97),
}
OWNER_REFUSAL_REASON: dict[str, str] = {
    'Bg0002': 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place',
}


def owner_refused_placements(scene: str) -> tuple[int, ...]:
    """Placement indices this lane refuses to ship for ``scene``, ascending.

    An empty tuple for a scene with no owner ruling is the normal answer,
    not a missing entry: bg0001 has no refused block and returns ``()``.
    """
    if type(scene) is not str or not scene:
        raise FieldMobContractError("scene must be non-empty text")
    return tuple(sorted(OWNER_REFUSED_PLACEMENTS.get(scene, ())))


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
    ``0x2000 + placement_index + 1`` with no scene component, so two scenes'
    own small, independently-assigned placement indices can land on the same
    wire identity.  ~~bg0001's and Bg0002's collide on four identities
    (placements 58, 59, 60 and 95).~~  ROUND 8ftmbx: ZERO today -- all four
    bg0001 sides were among the nine rows COO-DECISION 2026-08-29T00:41+07:00
    withdrew, and what the town still ships (103/105/107/109) meets nothing
    Bg0002 ships.  THE HAZARD IS NOT FIXED, only unrealised: the identity rule
    is unchanged, so the next roster either scene grows can bring it straight
    back.  ``tests/test_field_mobs.py``'s
    ``test_bg0001_and_bg0002_actor_identities_no_longer_collide`` pins the
    empty set so that day is noticed.  This is harmless today because no
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
    parsed = _parse_hostile_placements(module)
    # ROUND wmomy7.  The owner-refusal filter is applied HERE, at the one
    # point every downstream consumer already goes through, so the combat
    # ledger, the AI register and the census hostile override all shrink
    # together.  Filtering in only one of them is what produces the defect
    # this round found: a ledger row for a body no client was ever sent, so
    # a strike resolves server-side against a monster that is on nobody's
    # screen.
    #
    # ``_parse_hostile_placements`` still validates the FULL generated table
    # first (above), so a refused row that is malformed is still refused by
    # name -- the filter narrows what this lane SHIPS, it does not weaken
    # what this lane CHECKS.
    refused = set(owner_refused_placements(scene))
    if not refused:
        return parsed
    kept = tuple(mob for mob in parsed if mob.placement_index not in refused)
    if not kept:
        raise FieldMobContractError(
            "the owner-refusal list for scene %r removes every row this "
            "lane ships; an empty roster must come from an empty table, "
            "not from a filter" % (scene,)
        )
    return kept


def scene_for_scene_id(scene_id: int) -> str | None:
    """The LIVE field-mob scene a player standing in ``scene_id`` is inside.

    ROUND k3qe9q.  THE HALF THIS LANE OWED.  ``runtime.py`` composes the
    roster and the combat ledger from ``load_roster()`` with no argument --
    bg0001's rows, always, whatever scene the session is actually in -- so
    ``mob_combat.strike`` refuses almost every monster a player in Bg0002 is
    standing in front of.  Round ``j0u64p`` asked chief for two lines and
    could only name one owner, because "the scene id the session holds" had
    no reader into a scene NAME then.  It has one now: lane A landed
    ``world_scene_folder`` (COO-DECISION 2026-08-29T08:48+07:00 item 3, "THE
    ONE PUBLIC READER"), so the missing half is this function, and it
    belongs to whoever owns the rosters.

    ~~cannot land a hit on anything there~~ -- STRUCK THE SAME ROUND,
    pf-adversary defect 1, re-derived here before it was accepted.  The
    Bg0002 census (``world_population_bg0002.build_bg0002_population``, 97
    actors) hands out identities ``0x2001..0x206a``, and identity is
    ``0x2000 + placement index + 1`` with NO SCENE COMPONENT -- the hazard
    :func:`load_roster` already names as "not fixed, only unrealised".  It
    is realised here: ``0x2068`` and ``0x206a`` are bg0001 roster rows AND
    Bg0002 census actors, so a player in Bg0002 who clicks one of those two
    bodies today lands a hit that debits a PORT ROYAL monster.  That is
    worse than a refusal, and this function does not fix it -- it takes
    those two wrong hits away and adds twelve right ones, leaving 85 of the
    97 census actors unhittable because this lane ships no roster row for
    them.  A step, stated as a step.

    Returns ``None`` for every scene this lane ships no monsters for, which
    is the overwhelming majority of them.  ``None`` means SHIP NO ROSTER --
    never "ship the default one".  That is lane A's own stated contract for
    an unaddressed id, and it is also the only safe reading here: falling
    back to bg0001 is exactly today's defect, one layer down.

    Three ways this returns ``None``, all deliberate, none an error:

    * lane A's registry does not address that scene id at all (255 of the
      client's 271 scene rows today) -- nothing vetted, so nothing shipped;
    * it addresses it, but this lane ships no table for that folder (a town,
      or Bg0015, which is mined-but-dormant: it is in
      ``_KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING`` and deliberately NOT in
      ``_SCENE_TABLE_MODULES``, so a scene id resolving to it must stay
      empty until someone makes it live on purpose);
    * ``scene_id`` is not an id this process could have got off the wire.

    ONE SPELLING, NOT TWO.  The match against ``_SCENE_TABLE_MODULES`` is
    exact and case-sensitive on purpose.  The client's own folder names are
    NOT consistently cased -- scene 1 is ``bg0001`` and scene 2 is
    ``Bg0002``, and this project's table modules carry those two spellings
    verbatim -- so a case-folding match here would be a second, looser
    spelling rule living next to lane A's, and the first table module whose
    ``SCENE`` string drifted from the client's folder would be papered over
    by it instead of being caught.  The drift that rule would hide is worth
    more than the drift it would absorb: a live scene that lane A's registry
    cannot address, or spells differently, means that scene's monsters
    vanish with nothing raising -- so
    :func:`assert_live_scenes_are_addressable` exists to make that case fail
    in the test suite rather than in a player's client, and
    ``tests/test_field_mobs_scene_binding.py`` runs it.
    """
    # ``type(x) is not int`` already refuses ``True``/``False``, because
    # ``type(True)`` is ``bool`` and not ``int`` -- the extra ``is bool``
    # clause this line used to carry was dead code, and pf-adversary killed
    # a mutant that deleted it to prove so.  Booleans are still refused;
    # ``test_a_scene_id_that_is_not_an_integer_is_refused_by_name`` passes
    # them explicitly, so the behaviour is pinned by a test rather than by
    # a clause that never runs.
    if type(scene_id) is not int:
        raise FieldMobContractError("scene id must be an integer")
    folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    if folder is None:
        return None
    return folder if folder in _SCENE_TABLE_MODULES else None


def roster_for_scene_id(scene_id: int) -> tuple[FieldMob, ...]:
    """The rows that actually stand in ``scene_id``, or no rows at all.

    ROUND k3qe9q.  This is the shape a ``runtime.py`` call site wants: it
    holds a scene id, not a scene name, and it needs a roster it can hand
    straight to :func:`mob_combat.open_ledger`.

    ~~and to :func:`build_field_mob_population`~~ -- STRUCK THE SAME ROUND,
    pf-adversary defect 7: that function takes no roster parameter at all
    (``legacy, player_xyz, mob_count=None, *, faction, with_name``), builds
    its own with ``nearest_first()``, and stamps the generation with
    ``field_mob_tables.SCENE`` unconditionally.  Nothing can be handed to
    it.  The sentence read as a measured statement about an existing API and
    was not one.

    An empty tuple is a real, safe answer and not a failure: a ledger opened
    on it holds nothing, so every strike in that scene refuses by name
    (``target_not_in_ledger``) instead of accepting a hit against a monster
    standing in a different scene -- which is what happens today.  Callers
    must not read ``()`` as "fall back to the default roster".
    """
    scene = scene_for_scene_id(scene_id)
    if scene is None:
        return ()
    return load_roster(scene)


def assert_live_scenes_are_addressable() -> None:
    """Refuse if any LIVE scene's monsters are unreachable through a scene id.

    ROUND k3qe9q.  :func:`scene_for_scene_id` is a join between two tables
    owned by two different lanes: this lane's ``_SCENE_TABLE_MODULES`` keys
    and lane A's scene-id registry.  A join like that fails silently in the
    direction that matters most -- a live roster nothing can reach returns
    ``()`` for every scene id, so the scene simply has no monsters and
    nothing anywhere raises or prints.  This function is the guard that
    turns that into a loud failure in the suite.

    Measured today: bg0001 is addressed by scene id 1 and by no other, and
    Bg0002 by scene id 2 and by no other.  Neither appears in lane A's
    ``scene_ids_sharing_a_folder`` list of 45 folders that two scene ids
    both name, so neither has a second id that could reach it.

    ~~a live scene that DID have [a second scene id] would need lane A to
    address both ids, and this guard is where that would be noticed.~~
    STRUCK THE SAME ROUND, pf-adversary defect 6, which broke it by driving
    it: with ``(186, "bg0001")`` added to lane A's registry this guard still
    PASSED and scene 186 quietly served Port Royal's four monsters, because
    the test below is ``if not scene_ids_addressing(scene)`` -- a truthiness
    test, which one id and two ids both satisfy.  WHAT ACTUALLY NOTICES a
    second id is the tuple pin in
    ``tests/test_field_mobs_scene_binding.py``
    (``test_each_live_scene_is_addressed_by_exactly_one_scene_id``), and
    that pin is the thing to keep looking at.  This guard catches ZERO ids
    and nothing else; the sentence that claimed more has been struck rather
    than deleted so the difference stays readable.
    """
    unreachable = []
    for scene in live_scenes():
        if not scene_ids_addressing(scene):
            unreachable.append(scene)
    if unreachable:
        raise FieldMobContractError(
            "live field-mob scenes no scene id can reach: %s -- their "
            "monsters would be absent from every scene with nothing "
            "raising (live scenes today: %s)"
            % (sorted(unreachable), sorted(live_scenes()))
        )


def scene_ids_addressing(scene: str) -> tuple[int, ...]:
    """Every scene id lane A's registry resolves to ``scene``, ascending.

    ROUND k3qe9q.  The mapping still comes from lane A's public per-id
    reader, so this stays a caller of the ONE public reader COO-DECISION
    2026-08-29T08:48+07:00 item 3 named.

    ~~The candidate ids are the CLIENT's own scene rows, read out of lane A's
    curated copy (``scene_folder_index``, 271 rows, public) ... asking the
    client's full row set rather than only the ids lane A already addresses
    is the point.~~  WITHDRAWN THE SAME ROUND, pf-adversary defect 5, and it
    was a defect in two ways at once:

    * ``world_scene_folder.load_copy()`` reads
      ``world_data/world_scene_folder_crosswalk.json``, and
      ``tools/build_foundation_release.py`` collects ``*.py`` ONLY -- so that
      file is NOT in the release archive the server actually runs from.
      Measured out of a built archive, the whole guard raised
      ``SceneFolderCopyError`` (another lane's ``RuntimeError`` subclass, so
      not even catchable as ``FieldMobContractError``).  A guard that cannot
      run where the server runs is not a guard, and this one would have taken
      boot down with it the moment chief asserted it at start-up as the
      docstring invited.
    * it bought nothing anyway: every candidate is filtered through
      ``scene_folder_for_scene_id``, whose whole domain IS
      ``_FOLDER_BY_SCENE_ID``, so the wider candidate set could not have
      changed one answer.  A mutant that replaced the copy read with a plain
      integer range survived the entire suite, which is the measurement that
      says the read was decoration.

    The candidate ids are therefore the registry's own, which is a
    module-level literal in lane A's file: always importable, no file read,
    no release-archive dependency.  Reaching one private name to fix that is
    the smaller cost, and it is named here rather than hidden.
    """
    if type(scene) is not str or not scene:
        raise FieldMobContractError("scene must be non-empty text")
    found = []
    for scene_id, _folder in world_scene_folder._FOLDER_BY_SCENE_ID:
        if world_scene_folder.scene_folder_for_scene_id(scene_id) == scene:
            found.append(scene_id)
    return tuple(sorted(found))


def describe_scene_roster_binding(scene_id: int) -> str:
    """One ASCII console line naming what a scene id resolved to.  G-OBS.

    ROUND k3qe9q.  The bridge console is cp874, so this stays inside 7-bit
    ASCII, the same rule ``world_population.census_console_line()`` and
    ``world_scene_folder.folder_console_suffix()`` already follow.

    RETURNS A LINE; DOES NOT PRINT IT.  The printer would be ``runtime.py``,
    which is not this lane's file -- the wiring ask is one line in the PR
    body, exactly as ``mob_death.describe_widening_coverage()`` was asked
    for in round ``j0u64p``.  Stated plainly so nobody greps for this token
    in a boot log and concludes the binding is unwired because it is
    missing: nothing prints it yet.
    """
    scene = scene_for_scene_id(scene_id)
    folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
    return (
        "MOB_SCENE_ROSTER scene_id=%d folder=%s live=%d mobs=%d"
        % (
            scene_id,
            folder if folder is not None else "?",
            1 if scene is not None else 0,
            len(roster_for_scene_id(scene_id)),
        )
    )


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


def gt035_observed_subject() -> FieldMob:
    """The actor GT-035's damage ladder was watched on.  NOT a shipped row.

    WHY THIS EXISTS.  ``GT-035`` is the only client-observable damage evidence
    this project has: two observers watched a ladder of numbers land on a real
    screen, on bg0001 placement 30 as the SET-NUMBER reading rendered it --
    "Tornado Eagle", level 27, 3857 HP.  Round 8ftmbx withdrew that row from
    the shipped roster (it is Da Vinci, a townsman, under the RE-128
    crosswalk; COO-DECISION 2026-08-29T00:41+07:00), and the pins that
    cross-check this lane's damage driver against what was SEEN would
    otherwise have had to either move to a different actor -- comparing
    today's arithmetic against numbers nobody watched on it -- or be deleted.
    Neither is acceptable, so the actor is rebuilt here from the row the
    generated table preserves for exactly this purpose.

    WHAT THIS IS NOT.  It is not a roster member and must never be added to
    one: it does not appear in :func:`load_roster` and it is not in any
    census.  ~~and nothing in a runtime path may call this~~ -- FALSE, and
    pf-adversary (round 8ftmbx, D14) was right to call it: :func:`
    assert_frozen_controls` calls this, and that is called by
    :func:`build_field_mob_population`, :func:`pin_document` and
    :func:`roster_report`, so every census composition depends on it.  What
    that dependency IS and IS NOT: the returned mob is only ever COMPARED
    here -- no caller puts it in a collection, an override or a frame (traced
    caller by caller, same round) -- but deleting
    ``GT035_OBSERVED_SETNUM_ROW`` from the generated table would make
    ``assert_frozen_controls`` refuse every boot.  That is the honest shape:
    a boot-time dependency on a preserved constant describing a row this lane
    deliberately does not ship.  Whether the client would
    render such an actor with that name is settled and settled NEGATIVE --
    it would not, which is why the row was withdrawn.  What this preserves is
    narrower and still true: the numbers the damage driver produces for a
    level 27 / 3857 HP defender are the numbers two people watched.
    """
    row = getattr(field_mob_tables, "GT035_OBSERVED_SETNUM_ROW", None)
    if type(row) is not tuple:
        raise FieldMobContractError(
            "the generated table carries no GT035_OBSERVED_SETNUM_ROW: "
            "regenerate it with tools/pf_mine_scene_mob_roster.py "
            "--identity-rule cline"
        )

    class _Holder:
        SCENE = field_mob_tables.SCENE
        HOSTILE_PLACEMENTS = [row]

    subject = _parse_hostile_placements(_Holder)[0]
    if subject.placement_index in {
            mob.placement_index for mob in load_roster()}:
        raise FieldMobContractError(
            "placement %d is in the shipped roster again: this function "
            "exists only for a row that is NOT shipped, and returning a live "
            "roster member from it would let a pin quietly change subject"
            % subject.placement_index
        )
    return subject


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
    ``test_bg0001_and_bg0002_actor_identities_no_longer_collide``
    carry the count this finds -- ~~four bg0001/Bg0002 pairs~~ zero since
    round 8ftmbx, for the reason that docstring gives).  Two scenes'
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
    return tuple(
        collision for collision in _identity_collisions(modules)
        if not collision["same_scene"]
    )


def same_scene_identity_collisions(
        table_modules: Any = None) -> tuple[dict, ...]:
    """Every placement two tables of the SAME scene both use, measured.

    THE GAP THIS CLOSES, and it is not hypothetical.  Lane A's letter
    ``pf_bridge/notes_to_chief/20260829_0014_LANE-A-STATUS-bg0015-collides-
    with-lane-B-committed-table.md`` (ADDRESSEE: LANE-B) reported that
    :func:`cross_scene_identity_collisions` could not see two tables of ONE
    scene disagreeing, by construction: it keyed its rosters by ``SCENE`` and
    ``continue``d on a repeat, so a second table for a scene it had already
    read was dropped without a word.  Lane A had just committed a second
    identity table for the third scene -- the still-COO-gated-dormant one
    this file may not name literally, see
    ``_KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING`` -- that disagrees with this
    lane's committed table for the SAME scene ~~on 16 of 17 placements~~ --
    it DID, and this function is why that was measurable; since round ua236k
    the two tables agree on all 12 placements they share, because this lane
    re-mined its table the same way lane A mined theirs.  The report is kept
    and still runs: agreement today is not a guarantee, and the function
    existing is what makes the next divergence visible on the day it lands.
    The disagreement it was built for was: one
    scene, one ``0x2000 + placement_index + 1`` identity, two different
    monsters.  The report that exists to find exactly that kind of clash
    returned nothing.  Fixing it was named as this lane's, so here it is.

    WHY IT MATTERS ON THE WIRE.  Same-scene is the WORSE half of the two.
    Cross-scene collisions share an identity in two places a player cannot be
    at once; a same-scene pair puts two different monsters on one identity in
    ONE census, and by ``RE-092`` (replace by omission) the collection that
    arrives second deletes the first with nothing in any log to say so.

    Same contract as its cross-scene sibling in every other respect: a REPORT,
    never a guard -- it does not raise on a finding, and nothing in this tree
    calls it from a runtime path.  ``scene_a`` and ``scene_b`` are equal in
    every row it returns.
    """
    modules = (
        _KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING
        if table_modules is None else tuple(table_modules)
    )
    if len(modules) < 2:
        raise FieldMobContractError(
            "need at least two scene table modules to compare")
    return tuple(
        collision for collision in _identity_collisions(modules)
        if collision["same_scene"]
    )


def _identity_collisions(modules: tuple) -> tuple[dict, ...]:
    """Every placement any two of these tables both use, same scene or not.

    Keyed by MODULE, not by scene name.  Keying by scene is what made the
    same-scene case invisible, and a report whose subject can be removed by
    the data it reports on is not a report.
    """
    rosters: list[tuple[str, tuple[FieldMob, ...]]] = []
    seen: list = []
    for module in modules:
        scene = getattr(module, "SCENE", None)
        if type(scene) is not str or not scene:
            raise FieldMobContractError(
                "field-mob table module %r has no SCENE constant" % (module,)
            )
        # The SAME module passed twice is not two tables; comparing it with
        # itself would report every one of its own rows as a collision.  Two
        # DIFFERENT modules naming the same scene is the case this exists for.
        if any(module is other for other in seen):
            continue
        seen.append(module)
        rosters.append((scene, _parse_hostile_placements(module)))
    collisions: list[dict] = []
    for i in range(len(rosters)):
        for j in range(i + 1, len(rosters)):
            scene_a, roster_a = rosters[i]
            scene_b, roster_b = rosters[j]
            by_index_a = {mob.placement_index: mob for mob in roster_a}
            by_index_b = {mob.placement_index: mob for mob in roster_b}
            for placement_index in sorted(set(by_index_a) & set(by_index_b)):
                mob_a = by_index_a[placement_index]
                mob_b = by_index_b[placement_index]
                collisions.append({
                    "scene_a": scene_a,
                    "scene_b": scene_b,
                    "same_scene": scene_a == scene_b,
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


def describe_same_scene_identity_collisions(
        table_modules: Any = None) -> tuple[str, ...]:
    """Console lines for :func:`same_scene_identity_collisions`, ASCII-only.

    A separate function rather than extra lines inside
    :func:`describe_cross_scene_identity_collisions`, because that one's
    header line and per-row shape are already pinned by tests and by whatever
    reads the bridge console: two different findings, two different reports.
    The row names the ONE scene once instead of twice -- printing
    ``bg0015 vs bg0015`` would read as a typo rather than as the finding.
    """
    collisions = same_scene_identity_collisions(table_modules)
    lines = [
        "FIELD_MOB_SAME_SCENE_IDENTITY_COLLISIONS count=%d" % len(collisions)
    ]
    for collision in collisions:
        lines.append(
            "  identity=0x%X placement=%d in %s: template=%d name=%s vs "
            "template=%d name=%s" % (
                collision["actor_identity"], collision["placement_index"],
                collision["scene_a"], collision["template_a"],
                collision["name_a"], collision["template_b"],
                collision["name_b"],
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
    # THE SHAPE GATE, and it exists because pf-adversary (round szdkgs, D2)
    # proved the first draft of this function passed on a table with the four
    # crosswalk rows DELETED, and on a table that relabelled them 'setnum'
    # with a doctored Mob-Set number.  A control whose subject can be removed
    # by the data it checks is not a control.  The expected split is written
    # HERE, in hand-written code, not read out of the generated module.
    expected = {
        "cline": EXPECTED_CROSSWALK_PLACEMENTS,
        "setnum": EXPECTED_LEGACY_PLACEMENTS,
    }
    actual = {"cline": set(), "setnum": set()}
    for mob in roster:
        rule = per_placement.get(mob.placement_index)
        if rule not in actual:
            raise FieldMobContractError(
                "placement %d carries identity rule %r, which is neither "
                "reading" % (mob.placement_index, rule)
            )
        actual[rule].add(mob.placement_index)
    for rule, wanted in expected.items():
        if actual[rule] != wanted:
            raise FieldMobContractError(
                "the %s rows of this scene are %s, not the %s this lane "
                "ships" % (rule, sorted(actual[rule]), sorted(wanted))
            )
    for mob in roster:
        set_number = scene_numbers.get(mob.placement_index)
        if set_number is None:
            raise FieldMobContractError(
                "roster row %d carries no Mob-Set number, so its identity "
                "cannot be re-resolved" % mob.placement_index
            )
        if per_placement.get(mob.placement_index) != "cline":
            # ~~A row the table itself labels as the legacy set-number
            # reading, kept for one more round with its migration named.~~
            # ROUND 8ftmbx: UNREACHABLE, and said so rather than left looking
            # like a live check (pf-adversary, D12).  With
            # EXPECTED_LEGACY_PLACEMENTS empty, the shape gate above only
            # lets control past here when actual["setnum"] is empty too, so
            # every surviving row is labelled "cline" and this branch cannot
            # execute.  It is KEPT, not deleted, because it is the correct
            # handling the day a ruling ships set-number rows again -- and
            # because deleting it would make that day's reviewer write it
            # from scratch.  The gate that actually refuses a returning
            # set-number row is the expected/actual comparison above.
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
        # THE DERIVED COLUMN, which the first draft of this round left with no
        # check at all (pf-adversary D2): the withdrawn control's one real job
        # was holding max_hp, and dropping it meant 198125 could become 4242
        # and nothing would notice.  These two literals are hand-written here,
        # in a file the generator does not write, exactly as V117_P30_EXACT_HP
        # was -- STANDARD_MOB[100].n_HPMAX for a level-100 actor.
        if (mob.level, mob.max_hp) != (TOWN_TARGET_LEVEL, TOWN_TARGET_MAX_HP):
            raise FieldMobContractError(
                "town target %d ships level %r / max HP %r, not the mined "
                "%d / %d" % (mob.template_id, mob.level, mob.max_hp,
                             TOWN_TARGET_LEVEL, TOWN_TARGET_MAX_HP)
            )
    # ~~The legacy constants, kept reachable so a reader can see they were not
    # deleted.~~  ASSERTED AGAIN, but about what they actually describe.  They
    # are no longer the control on this roster's identity -- they were made by
    # the reading this round replaced -- but they ARE exact statements about
    # the legacy reading that nine of these rows still ship, so holding the
    # table to them is a real check with a real subject, and it is the one
    # that makes the ``legacy`` parameter mean something again (pf-adversary
    # D2: assert_frozen_controls(None) used to pass).
    legacy_hp = getattr(legacy, "V117_P30_EXACT_HP", None)
    legacy_name = getattr(legacy, "V119_P30_TARGET_NAME", None)
    legacy_index = getattr(legacy, "V112_MONSTER_INDEX", None)
    if legacy_index != LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX:
        raise FieldMobContractError(
            "frozen monster index drift: %r" % (legacy_index,)
        )
    # ~~a lookup in the shipped roster~~ -- ROUND 8ftmbx: the nine set-number
    # rows are withdrawn (COO-DECISION 2026-08-29T00:41+07:00), so the roster
    # no longer contains placement 30 and this check would refuse every boot.
    # The check itself is NOT dropped: what it holds is a statement about the
    # LEGACY READING, and that reading is preserved in the generated module
    # precisely so the statement stays checkable.  So the subject is the
    # preserved row, and the check keeps doing the job pf-adversary's D2 gave
    # it -- reading real values off ``legacy`` and refusing a drift.
    control = gt035_observed_subject()
    if control.placement_index != LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX:
        raise FieldMobContractError(
            "the preserved legacy row is placement %d, not the %d v141 froze"
            % (control.placement_index, LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX)
        )
    # ~~a second check here that the withdrawn row is not back in the
    # roster~~ -- REMOVED, round 8ftmbx, because pf-adversary's D11 mutation
    # showed it can never execute: ``gt035_observed_subject()`` on the line
    # above makes exactly that check and raises first, so this branch was an
    # unreachable copy that LOOKED like a second line of defence.  One
    # reachable guard, tripped by
    # tests/test_field_mobs.py::test_both_withdrawn_row_guards_actually_raise,
    # is worth more than two where only one runs.
    if (control.template_id, control.display_name, control.max_hp) != (
            LEGACY_SETNUM_CONTROL_TEMPLATE_ID, legacy_name, legacy_hp):
        raise FieldMobContractError(
            "placement %d no longer reproduces the legacy reading v141 froze "
            "(%r/%r/%r vs %r/%r/%r)"
            % (LEGACY_SETNUM_CONTROL_PLACEMENT_INDEX,
               control.template_id, control.display_name, control.max_hp,
               LEGACY_SETNUM_CONTROL_TEMPLATE_ID, legacy_name, legacy_hp)
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

    Sending this collection alongside the lane-A census duplicates every roster
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
        # pf-adversary (round szdkgs, D3): the round labelled the split in the
        # generated module and left the SHIPPED artifact presenting all
        # every shipped row identically.  The pin is what a report quotes, so the
        # split travels with it: which rule produced each row, who the legacy
        # rows really are, and the placements no rule could read at all.
        "identity_rule": field_mob_tables.IDENTITY_RULE,
        "identity_rule_per_placement": {
            str(index): rule for index, rule
            in sorted(field_mob_tables.IDENTITY_RULE_PER_PLACEMENT.items())
        },
        "legacy_setnum_pending_migration": sorted(
            row[0] for row
            in field_mob_tables.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION
        ),
        "withdrawn_under_this_rule": [
            {
                "placement_index": row[0],
                "was_template_id": row[1],
                "was_display_name": row[2],
                "now_template_id": row[3],
                "now_display_name": row[4],
            }
            for row in field_mob_tables.WITHDRAWN_UNDER_THIS_RULE
        ],
        "unresolved_placements": [
            {"placement_index": row[0], "set_number": row[1],
             "reason": row[2]}
            for row in field_mob_tables.UNRESOLVED_PLACEMENTS
        ],
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
            "max_hp is DERIVED from STANDARD_MOB by level.  ~~the two "
            "frozen controls it re-derives are placement 30 only~~ - round "
            "szdkgs: those two v141 constants came out of a run of the same "
            "set-number reading they were checking, so they are no longer "
            "the control on identity.  ~~they are held as a pin on the "
            "LEGACY reading nine of these rows still ship~~ - round 8ftmbx: "
            "no row ships that reading any more, so the two constants are "
            "held against the row the generated table PRESERVES for it "
            "(gt035_observed_subject), which is not in this roster; the "
            "derived column is checked against a hand-written level/HP "
            "literal for the four crosswalk rows",
            "~~nine of the thirteen rows below still carry the set-number "
            "reading this round's own finding calls false~~ - WITHDRAWN, "
            "round 8ftmbx, on the one-round ceiling COO-DECISION "
            "2026-08-29T00:41+07:00 put on them: this scene ships FOUR rows, "
            "all of them n_ID 916 practice dummies, and the nine townspeople "
            "are listed per row under withdrawn_under_this_rule as what they "
            "really are.  This nonclaim is kept rather than deleted because "
            "it is the record of what a reader of an older pin was told",
            "a row this module ships is not a monster: bg0001's "
            "hostile_placements is EMPTY (nothing in this town has both a "
            "rank and a combat AI), and the four rows it does ship are "
            "practice dummies - rank 0, no combat AI, no drop table - "
            "approved as attackable targets by COO-DECISION "
            "2026-08-29T00:41+07:00 on the express condition that nobody "
            "counts them as monsters of Port Royal",
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
