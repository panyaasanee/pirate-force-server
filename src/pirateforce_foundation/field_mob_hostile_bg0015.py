"""LANE-B: Bg0015 (scene 14) hostile entry-byte composer, pre-wire.

COO-DECISION 2026-08-31T16:48+07:00 (pf_bridge/notes_to_chief) unlocked "layer
1" of the three-layer block this round's INDEX letter named: importing
``field_mob_tables_bg0015`` under ``src/pirateforce_foundation/`` is no longer
refused, now that lane A's login-entry door for scene 14 is merged
(``pirate-force-server#290``) and ``GT-134`` measured a monster there with a
real client on screen.  This module is that one approved importer --
``tests/test_field_mob_tables_bg0015.py``'s own AST+literal sweep now expects
exactly this file and no other under ``src/`` to name the table module.

THIS DOES NOT MAKE Bg0015 A LIVE ROSTER.  ``field_mobs.load_roster(scene=...)``
still refuses ``"Bg0015"`` -- this module does not touch ``field_mobs
._SCENE_TABLE_MODULES``, ``live_scenes()`` or
``_KNOWN_SCENE_TABLE_MODULES_FOR_REPORTING``, all of which 182 existing pinned
assertions across six test files depend on meaning "the two scenes shipped so
far" (measured this round with a grep before touching anything).  Registering
a third scene there is layer 2/3 work gated on chief's own ``runtime.py:7501``
branch (COO-DECISION's own division of labour) and is deliberately left for
that CORE-REQUEST, not slipped in here as a side effect of an import guard
unlocking.

WHAT THIS MODULE ACTUALLY BUILDS, AND WHY IT REUSES RATHER THAN RE-DERIVES.
``field_mobs.hostile_actor_entry`` is the ONE encoder this project already
ships for "a named, leveled, hostile-faction NPCAttr + full-mask movement",
proven against the frozen ``v141`` body for bg0001 and Bg0002
(``tests/test_field_mobs.py``).  This module calls that same function, unmod-
ified, over Bg0015's own mined ``HOSTILE_PLACEMENTS`` rows -- it does not open
a second encoder for a third scene, which is exactly the "changing which rows
are selected beats writing a second selector" instruction this round's
charter states directly.

WHO ASKED FOR THIS SHAPE.  LANE-A's design letter
(``pf_bridge/notes_to_chief/20260831_2007_LANE-A-TO-LANE-B-scene14-hostile-
splice-design-proposal-re092.md``) proposes exactly this split: lane B builds
``dict[actor_identity, hostile_entry_bytes]`` for the 12 placements using the
actor_identity formula already in use (``0x2000 + placement_index + 1``, the
same ``FieldMob.actor_identity`` property every other scene uses -- no new
formula invented here), and chief's future ``runtime.py`` branch feeds that
dict to ``mob_scene_recompose.splice_identity_override`` alongside lane A's
own ``world_population_bg0015.build_bg0015_population`` generation.  This
module is lane B's half of that letter, built rather than merely agreed to
(this round's own "you do not answer, you build" rule) --
:func:`scene14_splice_ready` below proves the plumbing end-to-end against a
synthetic generation, since the real ``runtime.py`` call site does not exist
yet for a live proof.

WHICH 12 PLACEMENTS, AND WHETHER ALL 12 SHIP HOSTILE.  Every row in
``field_mob_tables_bg0015.HOSTILE_PLACEMENTS`` ships hostile by default here
(:data:`DEFAULT_HOSTILE_PLACEMENT_INDICES` is the full set, all 12) -- lane
A's letter item 3 leaves "hostile or partly civilian" as lane B's call, and
this round's decision is "all 12, unchanged from what the table already
selects" because ``field_mob_tables_bg0015.py``'s own generator already ran
the hostility predicate (rank>0 AND ai_combat!=0) to produce exactly this
list; nothing here narrows it further.  :func:`scene14_hostile_overrides`
takes an explicit ``placement_indices`` argument so a future round (or the
joint letter, if lane A/chief want fewer) can narrow it without editing this
function's body -- narrowing is a caller argument, not a code change.

NONCLAIM.  Nothing here sends a frame, opens a ledger row, or is called from
``runtime.py``/``app.py`` -- grepped for both, zero hits outside this file
and its own test.  ``current/pf_login_game_server_v141.py`` is read (via the
caller-supplied ``legacy`` module, exactly like every other ``field_mobs``
caller) and never edited.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import field_mob_tables_bg0015
from . import field_mobs
from . import mob_scene_recompose


# Convention marker only; nothing in this tree branches on it (same
# convention every other lane module in this project already uses).
production_allowed = True
test_only = False


class FieldMobHostileBg0015Error(ValueError):
    """A refusal from this module, always with a reason in the message."""


# All 12 rows field_mob_tables_bg0015.HOSTILE_PLACEMENTS already selected
# under the hostility predicate (rank>0 AND ai_combat!=0) -- see module
# docstring "WHICH 12 PLACEMENTS" for why this is the whole set, not a
# hand-picked subset.
DEFAULT_HOSTILE_PLACEMENT_INDICES: tuple[int, ...] = tuple(
    sorted(row[0] for row in field_mob_tables_bg0015.HOSTILE_PLACEMENTS)
)


def scene14_hostile_roster() -> tuple[Any, ...]:
    """Bg0015's own ``HOSTILE_PLACEMENTS`` rows, typed and validated.

    Reuses ``field_mobs``'s own row parser -- the same one every live
    scene's ``load_roster()`` runs its rows through (duplicate placement
    index, duplicate spawn position, out-of-range fields all refused the
    same way) -- rather than re-implementing that validation for a third
    scene.  This does NOT go through ``load_roster()`` itself, because that
    function's registered-scene gate is the exact thing keeping Bg0015 off
    the live path (see module docstring); this calls the shared row-level
    validator directly, the same way ``field_mobs.cross_scene_identity_
    collisions`` already does for a caller-supplied module it does not
    register either.
    """
    return field_mobs._parse_hostile_placements(field_mob_tables_bg0015)


def scene14_hostile_overrides(
    legacy: Any,
    *,
    placement_indices: tuple[int, ...] = DEFAULT_HOSTILE_PLACEMENT_INDICES,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
) -> dict[int, bytes]:
    """``{actor_identity: hostile_entry_bytes}`` for the requested placements.

    Exactly the shape LANE-A's letter asks lane B to hand chief's future
    ``runtime.py`` branch for ``mob_scene_recompose.splice_identity_
    override(legacy, generation, override)``.  Built with ``field_mobs
    .hostile_actor_entry`` -- the SAME encoder bg0001/Bg0002 already ship
    with, not a re-derivation -- so a Bg0015 monster's body carries the same
    proven faction+level splice as every other scene's hostile.

    ``placement_indices`` defaults to every row Bg0015's own table already
    selected as hostile; passing a narrower tuple ships fewer of the 12
    without touching this function.  An index outside the roster's own set
    is refused by name rather than silently skipped -- a caller asking for
    placement 999 almost certainly mistyped it, and a silently-shorter dict
    is exactly the "shortfall as mystery" outcome this project's own charter
    forbids.
    """
    if type(placement_indices) is not tuple or not placement_indices:
        raise FieldMobHostileBg0015Error(
            "placement_indices must be a non-empty tuple"
        )
    roster = {mob.placement_index: mob for mob in scene14_hostile_roster()}
    missing = [i for i in placement_indices if i not in roster]
    if missing:
        raise FieldMobHostileBg0015Error(
            "placement index(es) not in Bg0015's hostile roster: %s (known: "
            "%s)" % (sorted(missing), sorted(roster))
        )
    overrides: dict[int, bytes] = {}
    for index in placement_indices:
        mob = roster[index]
        overrides[mob.actor_identity] = field_mobs.hostile_actor_entry(
            legacy, mob, faction=faction, with_name=with_name,
        )
    return overrides


def scene14_hostile_count() -> int:
    """How many placements :func:`scene14_hostile_roster` ships, measured.

    A thin, testable wrapper so a console line or a letter can report the
    number rather than re-deriving ``len(...)`` inline -- "count before you
    send" applied to a pre-wire module the same way it applies to a live one.
    """
    return len(scene14_hostile_roster())


@dataclass(frozen=True)
class SyntheticSceneCensus:
    """Minimal structural stand-in for a real census generation.

    Built ONLY so :func:`scene14_civilian_then_hostile_splice_proof` (and its
    test) can drive ``mob_scene_recompose.splice_identity_override`` end to
    end before chief's ``runtime.py`` branch exists to hand it a real
    generation.  Not a type any live path returns --
    ``splice_identity_override`` accepts it purely because its own guard is
    STRUCTURAL (duck-typed on ``actor_identities``/``entry_bytes``/``pc``,
    see that function's own docstring), not because this type is registered
    anywhere.
    """

    actor_identities: tuple[int, ...]
    entry_bytes: tuple[int, ...]
    pc: bytes
    frame: bytes


def _civilian_entry(legacy: Any, mob: Any) -> bytes:
    """One placement's plain (non-hostile) actor entry: the frozen NPCAttr
    body ``legacy.make_npc_attr`` already produces, no faction/level splice.
    This is the "what lane A would send today, before any splice" half of
    the proof below -- built with the SAME frozen serializer
    ``field_mobs.hostile_npc_attr`` itself diffs against as a baseline
    (``tests/test_field_mobs.py``'s own load-bearing test), not a new one.
    """
    npc_attr = legacy.make_npc_attr(
        mob.template_id, mob.actor_identity, field_mobs.SCENE_ID,
        field_mobs.SCENE_SEQUENCE, mob.visual_preset, mob.max_hp, mob.max_hp,
        movement_speed=float(mob.speed_walk), basic_name=mob.display_name,
    )
    movement = legacy.make_remote_movement_attr(
        mob.actor_identity, mob.x, mob.y, mob.z,
        field_mobs.HEADINGS[mob.placement_index & 3],
        mask=field_mobs.FULL_MOVEMENT_MASK,
    )
    return legacy.make_remote_actor_entry(
        field_mobs.NPC_STYLE_ACTOR_TYPE, mob.actor_identity,
        [(field_mobs.NPC_ATTR_ID, npc_attr),
         (field_mobs.MOVEMENT_ATTR_ID, movement)],
    )


def scene14_civilian_then_hostile_splice_proof(legacy: Any) -> dict[str, Any]:
    """Build Bg0015's 12 placements as a plain census, splice in this
    module's hostile override, and hand back both collections plus what
    changed.

    THE PROOF THIS ROUND OWES LANE A's LETTER: that
    ``scene14_hostile_overrides()``'s dict is exactly the shape
    ``mob_scene_recompose.splice_identity_override`` needs, with no
    ``runtime.py`` call site required to demonstrate it.  Every actor
    identity in the override dict must appear in the civilian collection
    (a real arrival census would carry these same 12 placements among its
    91, per lane A's letter) and must come back changed; every other
    identity in the collection is untouched -- both checked by
    ``tests/test_field_mob_hostile_bg0015.py``, not merely asserted here.

    Returns a plain dict rather than a NamedTuple so a future console line
    or letter can print a subset of it without importing this module's
    private types.
    """
    roster = scene14_hostile_roster()
    civilian_entries = [_civilian_entry(legacy, mob) for mob in roster]
    civilian_pc, civilian_frame = legacy.make_runtime_remote_actors(
        civilian_entries
    )
    civilian = SyntheticSceneCensus(
        actor_identities=tuple(mob.actor_identity for mob in roster),
        entry_bytes=tuple(len(entry) for entry in civilian_entries),
        pc=civilian_pc,
        frame=civilian_frame,
    )
    override = scene14_hostile_overrides(legacy)
    spliced = mob_scene_recompose.splice_identity_override(
        legacy, civilian, override,
    )
    changed = tuple(
        identity for identity in civilian.actor_identities
        if identity in override
    )
    return {
        "civilian": civilian,
        "spliced": spliced,
        "override_count": len(override),
        "changed_identities": changed,
    }
