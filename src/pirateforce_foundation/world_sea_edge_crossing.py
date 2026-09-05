"""LANE-A: which scene a boundary crossing at scene 126's map edge leads to.

WHY THIS MODULE EXISTS
-----------------------
`NOW.md`'s M2 milestone names two things this project can build while the
"what opens the captain-report page" question sits with RE: the island-dock
path (`world_island_dock_table`, `world_m2_arrival`, blocked on `RE-265`) and
the SEA-EDGE crossing this module is for -- `COO-DECISION 20260905_1348`
item 6, sharpened by `20260905_1748` after LANE-A's own `20260905_1639`
measured the marker candidate sets were 7 and 11 rows, not the 3 and 3 the
first draft of that order assumed.

R318 (the M2 provisioning trial, `PF_M2_SURVEY_TRIAL=1`) sailed a ship near
scene 126's own map edges and observed `TriggerVital` (0x1FB2) fire with
wire ids **7** at the western edge (X <= -8090) and **69** at the southern
edge (Y <= -8384), alongside the two island-docking ids (2, 3) GT-228
already claimed. `lane_hooks/lane_a_island_trigger_log.py` is the module
that reports every wire id that arrives; this one answers the question that
log cannot -- **if this scene changed, which scene would it be, and does
this project already know how to land a character there** -- without
sending anything itself.

WHAT THIS MODULE DOES NOT DO, STATED BEFORE ANYONE QUOTES IT
--------------------------------------------------------------
IT SENDS NOTHING. No frame is composed, no bytes are queued, no session is
touched. `runtime.py`'s TriggerVital dispatch branch calls
`lane_hooks.fire("vital_inbound_trigger_vital", ...)` and, today, returns an
empty frame list regardless of what any subscriber does -- the same "report
only" shape `lane_a_island_trigger_log` already documents for the same
opcode. Composing and returning an actual crossing frame needs one line
inside `runtime.py`'s TriggerVital branch (chief's file, `AGENTS.md`
section 7) that this lane may not write: call `crossing_target` with the
session's current scene id and the wire id this frame carried, and on a
match, compose the SAME kind of live-teleport frame
`gm/chat_command_action._warp_teleport_action_no_coords` already builds for
a bare `/warp <scene>` (`gm/warp_executor.warp_no_coords_live_target` is
exactly the function this module calls for its own third gate below, so the
two paths cannot disagree about which scenes qualify) -- and persist
`scene_id`+spawn into `character_positions` at compose time, the same
`PANYA-DECISION 20260904_1430` shape `gm/warp_scene_persist` already gives
`/warp`. Handed to chief as a CORE-REQUEST this round rather than guessed at
here.

ONE THING THIS ROUND DELIBERATELY WIDENS, PF-ADVERSARY MEASURED, RECORDED
RATHER THAN LEFT TO BE FOUND. Pinning `decreed_arrival` on 304/305 so THIS
module's own third gate (below) can check them makes
`gm.warp_executor.warp_no_coords_live_target(304)`/`(305)` resolve too --
that function gates on `has_authored_entry`, which `has_decreed_arrival`
now satisfies. The first draft of this docstring and of both scenes'
registry `status` text claimed the opposite ("no /warp gate names this
scene either"); pf-adversary measured it false by calling the function.
So a bare GM `/warp 304` or `/warp 305` is LIVE TODAY, on this round's own
commit, independent of whichever line eventually calls `crossing_target`
from `runtime.py` -- the same widening `#838` already made for scene 126,
here as an accepted side effect of reusing that scene's own gate rather
than a decision made on purpose for these two. Still GM-only
(`accounts.is_gm_account` gates `/warp` itself, unchanged) and still with
no ground bounds composed for either scene. ~~and still with no ... census
composed for either scene -- see `tests/test_gm_warp_chain_census_shipped.
SCENES_WITH_NO_CENSUS_COMPOSER_YET`~~ -- STRUCK, and it had already gone
stale once before this round noticed: scene 304 got its cast in round
`yob0a2` and scene 305 in round `9zj630`, so BOTH scenes now compose a real
arrival census for a GM standing in them, and that tuple is empty. The
pointer is kept rather than deleted because the tuple is still the place a
future bare-warp destination with no composer would be named.
What is still NOT live is the ORDINARY-PLAYER route this module exists
for: a real ship crossing scene 126's map edge, which needs the
`runtime.py` hookup named above.

THE THREE-TIER SCOPE (COO-DECISION 20260905_1748 item 6)
-----------------------------------------------------------
`crossing_target()` refuses unless all three hold:

1. **Source scene.** The session must be IN scene 126 (`SEA_EDGE_SOURCE_
   SCENE_ID`). This responder is not a general trigger-to-scene table; it is
   scoped to the one scene R318 actually sailed.
2. **A pinned wire id.** The trigger id must be a key of
   `SEA_EDGE_TRIGGER_TARGETS`, a closed two-entry map. Nothing here widens
   to the third edge R318 also measured (id 48, north, Y >= +6413) -- COO's
   decision named only 7 and 69, and the east edge stayed silent in every
   captured crossing, so a third row would be inventing a target for an id
   that has never been observed. Also NOT in this map, and asserted disjoint
   from it below: ids 2 and 3, which `lane_a_island_trigger_log.
   M2_OBSERVED_ISLAND_TRIGGER_IDS` already claims for island docking under
   `GT-228`'s own hypothesis -- a wire id cannot mean both an island and a
   sea in the same scene without a capture showing it depends on something
   this module does not read, and none exists.
3. **A destination this project can actually land a character on.** The
   target scene id resolves through `gm.warp_executor.
   warp_no_coords_live_target`, the SAME live-warp gate `/warp <scene>`
   uses -- not a bespoke lookup that could quietly disagree with it. Fails
   closed: if scenes 304/305 were ever removed from the registry, or their
   `decreed_arrival` block were ever invalidated, this function starts
   returning `None` for both wire ids rather than composing a stale point.

NEITHER 304 NOR 305 HAS A TABLE-AUTHORED ARRIVAL POINT
--------------------------------------------------------
Both carry `SCENE_NAME.n_MARKER == 0`, the same shape scene 126 was in
before round `ihjytc` gave it a `decreed_arrival` block. Searched this round
for a committed table that maps the WIRE id (7, 69) straight to a
destination row, so the crossing would not need an owner-decreed fallback at
all: `CONSTDATA_TH__Trigger.tsv` and `TEXTDATA_TH__Trigger_TIP.tsv` both
carry an entry for ids 7 and 69, but id 7 there is "Viper Wicket" (a dungeon
entrance) and id 69 is "Ground Site Entrance" (a structure) -- ordinary
double-click props, not a sea, and NEITHER row carries a destination-scene
or coordinate column of any kind. That confirms, with a second measurement,
what `RE-265` already found for five of R318's seven observed ids: the wire
trigger id space and this catalog's `n_ID` space are not the same namespace.
So `COO-DECISION 20260905_1748` item 3's fallback governs both destinations:
`scenarios/world_scene_registry_001.json` pins each one's arrival point at
the MARKER candidate furthest in the direction a ship entering from scene
126's own edge would be travelling (furthest X for 304, entered from the
west; furthest Y for 305, entered from the south), tagged
`decreed_provisional` rather than `decreed_permanent` because the owner has
not ruled on either scene the way she ruled on 126 -- see that file's own
`table_row_differences` for the full seven- and eleven-row candidate sets
this round measured (`LANE-A 20260905_1639`).

WHAT CHANGES IF COO'S FALLBACK TURNS OUT WRONG
-------------------------------------------------
One JSON value each, no code edit: `scenarios/world_scene_registry_001.json`
rows 304/305's `decreed_arrival.marker_n_id` are the only things this module
reads through the registry, and `world_scene_marker.DECREED_ARRIVAL_ROWS` is
the only place that has to agree with a new choice. `GT-267` (drafted this
round, `pf_bridge/notes_to_chief/`) asks an attended tester to record where
the ship actually surfaces and which way it faces -- a wrong answer there
is a one-row fix, not a new ticket.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .gm import warp_executor

if TYPE_CHECKING:
    from .world_scene_travel import SceneDestination

production_allowed = True

# TIER 1.  The only scene this responder is scoped to -- the one R318 sailed.
SEA_EDGE_SOURCE_SCENE_ID = 126

# TIER 2.  Wire trigger id (TriggerVital 0x1FB2 tag 0x0F, the SAME field
# `lane_hooks.lane_a_island_trigger_log.first_tag_value` walks) -> the scene
# a crossing at that edge leads to.  Closed by design: see the module
# docstring for why id 48 (the north edge) and the east edge are not here.
SEA_EDGE_TRIGGER_TARGETS: dict[int, int] = {
    7: 304,   # western edge (R318: X <= -8090) -> Dark Fog Sea
    69: 305,  # southern edge (R318: Y <= -8384) -> Pale Silver Sea
}


def _assert_disjoint_from_island_docking_ids() -> None:
    """Refuse to import if this map ever collides with GT-228's island ids.

    A module-level check rather than a comment: `lane_a_island_trigger_log.
    M2_OBSERVED_ISLAND_TRIGGER_IDS` and this map are maintained by the same
    lane in two different files for two different hypotheses (island docking
    vs. sea-edge crossing), and nothing else stops a future edit to either
    one from quietly overlapping the other.
    """
    from .lane_hooks import lane_a_island_trigger_log as islands_hook

    overlap = set(SEA_EDGE_TRIGGER_TARGETS) & set(
        islands_hook.M2_OBSERVED_ISLAND_TRIGGER_IDS)
    if overlap:
        raise AssertionError(
            f"sea-edge trigger ids overlap island-docking trigger ids: "
            f"{sorted(overlap)}")


_assert_disjoint_from_island_docking_ids()


@dataclass(frozen=True)
class SeaEdgeCrossing:
    """One resolved crossing: which wire id, from where, to where."""

    wire_trigger_id: int
    source_scene_id: int
    destination: "SceneDestination"


def crossing_target(
    current_scene_id: object, wire_trigger_id: object,
) -> SeaEdgeCrossing | None:
    """The crossing this (scene, wire id) pair resolves to, or ``None``.

    Never raises on a bad type -- a caller holding whatever the dispatch
    layer handed it should get a refusal, not a traceback, the same posture
    `lane_a_island_trigger_log.first_tag_value` already takes on its own
    payload. Only a plain, non-bool ``int`` for either argument can match;
    anything else falls through to the "not this scene" refusal.
    """
    if type(current_scene_id) is not int or isinstance(current_scene_id, bool):
        return None
    if type(wire_trigger_id) is not int or isinstance(wire_trigger_id, bool):
        return None
    if current_scene_id != SEA_EDGE_SOURCE_SCENE_ID:
        return None
    dest_scene_id = SEA_EDGE_TRIGGER_TARGETS.get(wire_trigger_id)
    if dest_scene_id is None:
        return None
    target = warp_executor.warp_no_coords_live_target(dest_scene_id)
    if target is None:
        return None
    return SeaEdgeCrossing(
        wire_trigger_id=wire_trigger_id,
        source_scene_id=current_scene_id,
        destination=target,
    )


def crossing_plan_report(crossing: SeaEdgeCrossing) -> dict:
    """Facts about a resolved crossing, for a console line or a CORE-REQUEST.

    Spelled `plan=` rather than `crossing=` for the same reason
    `world_m2_arrival.arrival_readiness` spells its own field `arrival_plan=`:
    this is a fact about what THIS SERVER could compose, not a claim that a
    client has been sent anywhere.
    """
    dest = crossing.destination
    return {
        "wire_trigger_id": crossing.wire_trigger_id,
        "source_scene_id": crossing.source_scene_id,
        "dest_scene_id": dest.n_id,
        "dest_scene_name": dest.scene_name_ascii,
        "spawn": dest.spawn,
        "heading": dest.decreed_arrival_heading,
        "evidence_tier": dest.decreed_arrival_authority,
    }


def crossing_console_line(crossing: SeaEdgeCrossing | None,
                           wire_trigger_id: int) -> str:
    """The exact ASCII line a caller may print for a resolved or refused id.

    ``bytes_out=0`` on every line, matching `lane_a_island_trigger_log`'s own
    convention: this module never sends, so no line from it may look like one
    that did.
    """
    if crossing is None:
        return (
            f"SEA_EDGE_CROSSING id={wire_trigger_id} no_target "
            "no_responder bytes_out=0"
        )
    plan = crossing_plan_report(crossing)
    x, y, z = plan["spawn"]
    return (
        f"SEA_EDGE_CROSSING id={wire_trigger_id} "
        f"dest_scene={plan['dest_scene_id']} name={plan['dest_scene_name']} "
        f"spawn=({x:g},{y:g},{z:g}) heading={plan['heading']} "
        "no_responder bytes_out=0"
    )
