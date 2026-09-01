"""Lifecycle-aware V141 state factory for the real legacy TCP listeners."""
from dataclasses import replace
import math
import random
import struct
import sys
import threading
import time

from . import columbus_quest_dispatch
from . import diag_multi_object_wiring
from . import field_mobs
from . import mob_ai_control
from . import mob_census_hostility
from . import mob_census_wire_count
from . import mob_combat
from . import mob_combat_membership
from . import mob_death
from . import mob_drop_presence
from . import mob_loot
from . import mob_pickup
from . import mob_scene_recompose
from . import scene_admission_gate
from . import trace_path
from . import world_density
from . import world_face_frame
from . import world_m2_crossing_handoff
from . import world_population
from . import world_population_bg0002
from . import world_population_handoff
from . import world_scene_entry
from . import world_scene_folder
from . import world_scene_liveness
from . import world_scene_travel
from . import world_travel_gate

from . import lane_hooks
from .lane_hooks import lane_b_mob_ai_tick
from .gm.accounts import is_gm_account
from .gm import chat_command_action
from .gm.dispatch import GM_RUN_GM_COMMAND_VITAL_ID
from .gm import state_wire
from .gm.state_wire import make_gm_update_state_frame
from .gm import login_scene_admission
from .gm import login_scene_stage
from .gm.login_scene_consume import (
    CONSUMED,
    CONSUME_FAILED,
    STANDALONE_NOT_CONSUMED,
    consume_login_scene_override,
)
from .gm.warp_target_record import (
    SESSION_ATTRIBUTE as GM_WARP_TARGET_SESSION_ATTRIBUTE,
    WarpTargetRecord,
    current_character_id,
    distance_to_target,
    position_matches_target,
    take_warp_target_with_reason,
)
from .gm.warp_executor import WarpTarget

from .model import Position
from .inventory import (
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    MERGED_V111_BACKPACK,
    is_exact_merge_request,
    make_item_merge_delta_response,
    make_item_move_delta_response,
    make_item_swap_delta_response,
    merge_known_item_into_occupied_slot,
    move_known_item_to_free_slot,
    parse_merge_candidate,
    swap_known_item_with_occupied_slot,
)
from .item_move_capture import (
    ITEM_MOVE_CAPTURE_FIELDS,
    classify_item_move_attempt,
    require_item_move_capture_scenario,
)
from .item_move_hypothesis import (
    classify_item_move_hypothesis_attempt,
    make_hypothesized_move_response,
    require_item_move_hypothesis_scenario,
)
from .chat_input_hypothesis import (
    CHAT_INPUT_SPEAKER_ECHO_SCENARIO_ID,
    CHAT_INPUT_VITAL_ID,
    classify_chat_input_attempt,
    make_chat_input_echo_response,
    make_chat_input_speaker_echo_response,
    require_chat_input_hypothesis_scenario,
)
from .channel_message_hypothesis import (
    CHANNEL_SWEEP_ACTION_LABEL_PREFIX,
    CHANNEL_SWEEP_FIRST_DELAY_SECONDS,
    CHANNEL_SWEEP_SPEAKER,
    SHARED_SERIALIZER_CHANNEL_IDS,
    channel_short_name,
    decode_channel_message_payload,
    make_channel_message_response,
    require_channel_message_hypothesis_scenario,
)
from .delete_actor import DELETE_ACTOR_VITAL_ID
from .delete_actor_hypothesis import (
    classify_delete_actor_attempt,
    make_delete_actor_ack_response,
    parse_accepted_delete_request,
    require_delete_actor_hypothesis_scenario,
)
from .delete_refresh_hypothesis import (
    DELETE_REFRESH_ACTION_LABEL,
    DELETE_REFRESH_GAP_SECONDS,
    assert_selector_absent,
    make_delete_actor_list_rebuild_response,
    require_delete_refresh_hypothesis_scenario,
)
from .logout_hypothesis import (
    LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET,
    LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER,
    LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT,
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
    LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH,
    LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST,
    LOGOUT_VITAL_ID,
    WORLDINFO_VITAL_ID,
    classify_logout_attempt,
    classify_worldinfo_frame,
    make_logout_ack_response,
    make_return_select_server_response,
    make_worldinfo_first_response,
    require_logout_hypothesis_scenario,
)
from . import logout_dialog_open_hypothesis
from .logout_dialog_open_hypothesis import (
    dispatch_logout_dialog_open_hypothesis,
)
from .population import (
    build_port_royal_initial_population,
    build_port_royal_membership_transition,
)
from .damage_hp_link_hypothesis import (
    DAMAGE_HP_LINK_EVENT_NAME,
    HP_LINK_PROBE_IDENTITY_HI,
    HP_LINK_PROBE_IDENTITY_LO,
    build_damage_hp_link_sweep,
    damage_hp_link_wire_unlock,
    require_damage_hp_link_hypothesis_scenario,
)
from .damage_model_hypothesis import (
    DAMAGE_MODEL_NPC_SCENARIO_ID,
    build_damage_model_sweep,
    damage_model_wire_unlock,
    require_damage_model_hypothesis_scenario,
    resolve_actor as resolve_damage_model_actor,
)
from .ground_loot_hypothesis import (
    make_ground_loot_frames, require_ground_loot_hypothesis_scenario,
)
from .ground_loot_nameprop_hypothesis import (
    GROUND_LOOT_NAMEPROP_LABELS,
    make_ground_loot_nameprop_frames,
    require_ground_loot_nameprop_scenario,
)
from .learn_skill_request_hypothesis import (
    LEARN_SKILL_REQUEST_VITAL_ID,
    classify_learn_skill_request_attempt,
    decode_learn_skill_request_payload,
    require_learn_skill_request_hypothesis_scenario,
)
from .learn_skill_result_hypothesis import (
    LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX,
    LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS,
    make_learn_skill_result_step_response,
    require_learn_skill_result_hypothesis_scenario,
)
from .pickup_listener_hypothesis import (
    PICKUP_LISTENER_VITAL_ID,
    classify_pickup_listener_attempt,
    decode_pickup_listener_payload,
    require_pickup_listener_hypothesis_scenario,
)
from .hostile_hp_link_hypothesis import (
    HOSTILE_HP_LINK_EVENT_NAME,
    HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
    HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
    HOSTILE_HP_LINK_SCENE_ID,
    HostileHpLinkValidationError,
    build_hostile_hp_link_sweep,
    hostile_hp_link_wire_unlock,
    require_hostile_hp_link_hypothesis_scenario,
    resolve_hostile_hp_link_target,
)
from .item_operate_res_hypothesis import (
    ITEM_OPERATE_RES_ACTION_LABEL_PREFIX,
    ITEM_OPERATE_RES_FIRST_DELAY_SECONDS,
    ITEM_OPERATE_RES_PROBE_IDENTITY_HI,
    ITEM_OPERATE_RES_PROBE_IDENTITY_LO,
    make_item_operate_res_step_response,
    require_item_operate_res_hypothesis_scenario,
)
from .skill_attr_hypothesis import (
    SKILL_ATTR_ACTION_LABEL_PREFIX,
    SKILL_ATTR_FIRST_DELAY_SECONDS,
    SKILL_ATTR_PROBE_IDENTITY_HI,
    SKILL_ATTR_PROBE_IDENTITY_LO,
    make_skill_attr_step_response,
    require_skill_attr_hypothesis_scenario,
)
from .move_authority_hypothesis import (
    evaluate_move_report, require_move_authority_hypothesis_scenario,
)
from .population_scenario import require_population_scenario
from .npc_hostile_hypothesis import (
    NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA,
    NPC_HOSTILE_PLAYER_IDENTITY_HI,
    NPC_HOSTILE_PLAYER_IDENTITY_LO,
    NPC_HOSTILE_PLAYER_PAIR_FACTION,
    build_npc_hostile_sweep,
    npc_hostile_wire_unlock,
    require_npc_hostile_hypothesis_scenario,
    resolve_probe as resolve_npc_hostile_probe,
)
from .npc_hp_link_hypothesis import (
    NPC_HP_LINK_EVENT_NAME,
    build_npc_hp_link_sweep,
    npc_hp_link_wire_unlock,
    require_npc_hp_link_hypothesis_scenario,
    resolve_npc_hp_link_target,
)
from .remote_player_hypothesis import (
    build_remote_player_sweep,
    remote_player_wire_unlock,
    require_remote_player_hypothesis_scenario,
    resolve_probes as resolve_remote_player_probes,
)
from .runtimeres_death_hypothesis import (
    build_runtimeres_death_sweep,
    require_runtimeres_death_hypothesis_scenario,
    resolve_probe as resolve_runtimeres_death_probe,
    runtimeres_death_lethal_unlock,
)
from .scenario import is_p30_target_observation, make_p30_target
from .session import FoundationSession
from .scene_object import (is_scene_remote_target, is_scene_remote_hostile_target,
                           make_scene_remote_actor)
from .stats_progression_hypothesis import (
    HP_DEATH_ACTION_LABEL_PREFIX,
    HP_DEATH_FIRST_DELAY_SECONDS,
    HP_DEATH_PROFILE_DEATH_SWEEP_NAME,
    STATS_PROGRESSION_ACTION_LABEL_PREFIX,
    STATS_PROGRESSION_FIRST_DELAY_SECONDS,
    StatsProgressionActor,
    hp_death_lethal_unlock,
    hp_death_profile_for_scenario,
    make_hp_death_step_response,
    make_stats_progression_step_response,
    require_hp_death_hypothesis_scenario,
    require_stats_progression_hypothesis_scenario,
)
from .second_password_bypass import (
    SECOND_PASSWORD_PULSE_INTERVAL_SECONDS,
    make_proactive_second_password_ok,
    require_second_password_mode,
)
from .action_ack import parse_scene006_ea7d, make_scene007_action_ack


def _active_arena_version(scenario) -> str:
    """Derive a label only while an opt-in Arena branch is active."""
    return "V2" if scenario.basic_faction is not None else "V1"


# CORE-REQUEST (COO-DECISION 2026-08-26T04:02+07:00, sections 1.3/2).  The
# wiring line MOB_COMBAT_WIRING/MOB_DEATH_WIRING hand to this file.  Both
# modules are ``production_allowed = True`` and take no scenario object; the
# whole reason this constant exists here is that nothing in src/ was calling
# either module before this round.
#
# [PROPOSED, not measured] the attacker profile.  This project has no
# character battle-stat source anywhere -- ``model.Position`` carries an
# identity and an xyz and nothing else, so there is no real per-player level
# or STR to read.  Until one exists, every attacker this branch drives is
# given the ONE profile this project has ever watched land on a real screen
# (HYP-PF-038 / GT-035's "MOB_WEAK" ladder, level 7 / STR 132), reproduced by
# ``mob_combat.pin_attacker()``.  That means every player currently deals the
# same damage numbers GT-035 already published against the sanctioned target,
# not numbers derived from their own character -- OURS, not the client's.
MOB_COMBAT_DEFAULT_ATTACKER = mob_combat.pin_attacker()

# Bound on the REFUSE_LEDGER_STALE / REFUSE_REGISTER_STALE retry loops below.
# [PROPOSED] Both loops are unreachable today -- the ledger and register are
# per-session state with exactly one writer (this dispatch method), so a
# stale-compare-and-swap refusal cannot actually occur under the current
# single-writer invariant (pf-adversary R177, confirmed by reading __init__).
# The cap exists so that if a future change ever breaks that invariant (a
# server-wide ledger, concurrent dispatch on one connection), the failure
# mode is a loud, named refusal instead of a silent infinite loop / DoS.
MOB_COMBAT_STALE_RETRY_LIMIT = 8


def _recompose_event_suffix(record):
    """The event suffix for a recompose that did NOT compose.

    KEEPS ONE OF THE TWO PREFIXES THIS TREE ALREADY GREPS FOR.  Before the
    scene-dispatched recompose there were exactly two shapes:
    ``..._refused_<ExceptionName>`` (the compose raised) and
    ``..._skipped_no_population_anchor`` (there was nothing to compose
    against).  ``mob_scene_recompose`` returns four states, two of which
    (``no_composer_for_scene``, ``refused_objects_outside_scene_1``) are
    neither -- and pf-adversary (round k882hm, D6) measured what that costs:
    ``tests/test_mob_combat_dispatch.py`` asserts that NO event starts with
    ``..._skipped_`` or ``..._refused_``, so a state outside both prefixes
    passes that assertion while the one-entry world-wipe frame goes out.

    So a ``refused_*`` state keeps its exact old spelling and every other
    non-composed state is named as the skip it is.  A caller must not pass a
    composed record: there is no event for success.
    """
    state = record.state
    if state.startswith(mob_scene_recompose.STATE_REFUSED_PREFIX):
        return state
    return "skipped_" + state


def _apply_mob_death_census_override(legacy, generation, override):
    """Splice ``mob_death.corpse_override`` entries into a built world census.

    ``world_population.WorldPopulationGeneration`` has no override parameter
    and ``world_population.py`` is out of this round's scope to edit, so this
    rebuilds the SAME collection with the SAME encoder
    (``legacy.make_runtime_remote_actors`` / ``legacy.frame_pc``) over a wider
    input: the original per-identity entry bytes, with any identity
    ``mob_death`` names replaced.  ``WIRE_HEADER_BYTES`` and ``entry_bytes``
    are read from ``world_population``'s own public fields/constants, not
    re-derived, and the entry order is ``generation.actor_identities`` /
    ``generation.entry_bytes`` -- the same order ``build_world_population``
    concatenated them in.
    """
    if not override:
        return generation
    offset = world_population.WIRE_HEADER_BYTES
    entries = []
    for identity, length in zip(
            generation.actor_identities, generation.entry_bytes):
        original = generation.pc[offset:offset + length]
        entries.append(override.get(identity, original))
        offset += length
    if offset != len(generation.pc):
        raise RuntimeError(
            "world population entry_bytes no longer accounts for the whole "
            "collection: the mob_death census override cannot be applied "
            "safely"
        )
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise RuntimeError("mob_death census-override frame drift")
    return replace(
        generation, pc=pc, frame=frame,
        entry_bytes=tuple(len(entry) for entry in entries),
    )


# SCENARIO-COMPOSE-001 (owner rulings, Panya 2026-08-24): the lane sets
# allowed to share one boot -- exactly one pair and exactly one triple.
# The pair (first ruling, chief cloud round R153) is one experiment in
# two halves, not two experiments -- the HYP-PF-032 spawner puts the
# ground object on the client screen and the HYP-PF-036 listener hears
# the click back, and the halves are structurally disjoint: the spawner
# rides alongside the TargetPos dispatch and latches on
# ground_loot_pair_sent, the listener keys on its own vital id 0x4543,
# and neither reads the other's state.  The triple (second ruling, ~21:1x
# +07:00, chief cloud round R155) adds the HYP-PF-037 ItemOperateVitalRes
# sweep to that same boot for the attended GT-060+GT-063 combined round:
# the sweep only ever fires on its own accepted chat trigger and writes
# no shared state, so the three lanes stay attributable -- and the
# owner's condition stands that a composed-round observation that cannot
# be attributed to one lane is NO-RESULT.  Membership is EXACT-SET: the
# triple being allowed does NOT allow its sub-pairs (item_operate_res
# with only one of the other two stays refused).  Every other
# combination of two or more lanes stays refused exactly as before, and
# a set enters this list only through another owner ruling, never by
# convenience.  (Constant renamed from COMPOSABLE_SCENARIO_LANE_PAIRS in
# R155 when the first non-pair member arrived.)
COMPOSABLE_SCENARIO_LANE_SETS = frozenset({
    frozenset({
        "ground_loot_hypothesis_scenario",
        "pickup_listener_hypothesis_scenario",
    }),
    frozenset({
        "ground_loot_hypothesis_scenario",
        "pickup_listener_hypothesis_scenario",
        "item_operate_res_hypothesis_scenario",
    }),
})


class _EventEchoList(list):
    """EVENT-EXPORT-001: an events list that echoes every append.

    Every event this build records -- dispatch and reject alike -- reaches
    the state through ``self.events.append`` and through nothing else, so
    swapping the freshly-initialized empty list for this one covers all of
    them without touching a single append site.  Equality, slicing and
    ``len`` are inherited from ``list``, so code and tests that compare
    event lists see no difference.
    """

    def __init__(self, exporter):
        super().__init__()
        self._exporter = exporter

    def append(self, item):
        super().append(item)
        self._exporter(item)


def make_stdout_event_exporter(stream=None):
    """EVENT-EXPORT-001: one ASCII line per recorded event.

    The bridge console is cp874: every character written here is forced
    into printable 7-bit ASCII (backslashreplace for non-ASCII, then a
    ``\\xNN`` escape for every remaining control character, newlines
    included), so no event payload can ever kill the console or break the
    one-line-per-event contract.  The line format is ``PF-EVENT <seq>
    <event>`` with seq counting from 1 per exporter; app.py builds exactly
    one exporter per process, so in a real boot the numbering is
    process-wide.  A diagnostic may never alter dispatch: any failure
    inside the export (a dead or closed stream, a hostile ``str``) is
    swallowed whole -- the echoed line is lost, the in-memory events list
    stays authoritative, and the frame's dispatch proceeds untouched.
    """
    counter = {"seq": 0}

    def export(event):
        try:
            out = stream if stream is not None else sys.stdout
            counter["seq"] += 1
            text = str(event).encode(
                "ascii", "backslashreplace",
            ).decode("ascii")
            text = "".join(
                ch if " " <= ch <= "~" else "\\x%02x" % ord(ch)
                for ch in text
            )
            out.write("PF-EVENT %d %s\n" % (counter["seq"], text))
            out.flush()
        except Exception:
            # Losing one diagnostic line beats burning a one-shot latch or
            # killing the game listener thread mid-frame.
            pass

    return export


def make_state_class(legacy, lifecycle, projector, scenario=None,
                     scene_load_scenario=None, session_factory=None,
                     connection_bindings=None, population_scenario=None,
                     item_move_capture_scenario=None,
                     item_move_hypothesis_scenario=None,
                     logout_hypothesis_scenario=None,
                     chat_input_hypothesis_scenario=None,
                     channel_message_hypothesis_scenario=None,
                     delete_actor_hypothesis_scenario=None,
                     delete_refresh_hypothesis_scenario=None,
                     stats_progression_hypothesis_scenario=None,
                     hp_death_hypothesis_scenario=None,
                     runtimeres_death_hypothesis_scenario=None,
                     damage_model_hypothesis_scenario=None,
                     damage_hp_link_hypothesis_scenario=None,
                     remote_player_hypothesis_scenario=None,
                     npc_hostile_hypothesis_scenario=None,
                     npc_hp_link_hypothesis_scenario=None,
                     move_authority_hypothesis_scenario=None,
                     ground_loot_hypothesis_scenario=None,
                     ground_loot_nameprop_scenario=None,
                     learn_skill_result_hypothesis_scenario=None,
                     learn_skill_request_hypothesis_scenario=None,
                     skill_attr_hypothesis_scenario=None,
                     pickup_listener_hypothesis_scenario=None,
                     item_operate_res_hypothesis_scenario=None,
                     hostile_hp_link_hypothesis_scenario=None,
                     event_exporter=None,
                     world_census_actor_count=None,
                     second_password_mode="required",
                     monotonic_clock=None,
                     close_timer_factory=None,
                     travel_gate_debug_enabled=False):
    active_lanes = frozenset(
        name for name, value in (
            ("scenario", scenario),
            ("scene_load_scenario", scene_load_scenario),
            ("population_scenario", population_scenario),
            ("item_move_capture_scenario", item_move_capture_scenario),
            ("item_move_hypothesis_scenario", item_move_hypothesis_scenario),
            ("logout_hypothesis_scenario", logout_hypothesis_scenario),
            ("chat_input_hypothesis_scenario", chat_input_hypothesis_scenario),
            ("channel_message_hypothesis_scenario",
             channel_message_hypothesis_scenario),
            ("delete_actor_hypothesis_scenario",
             delete_actor_hypothesis_scenario),
            ("delete_refresh_hypothesis_scenario",
             delete_refresh_hypothesis_scenario),
            ("stats_progression_hypothesis_scenario",
             stats_progression_hypothesis_scenario),
            ("hp_death_hypothesis_scenario", hp_death_hypothesis_scenario),
            ("runtimeres_death_hypothesis_scenario",
             runtimeres_death_hypothesis_scenario),
            ("damage_model_hypothesis_scenario",
             damage_model_hypothesis_scenario),
            ("damage_hp_link_hypothesis_scenario",
             damage_hp_link_hypothesis_scenario),
            ("remote_player_hypothesis_scenario",
             remote_player_hypothesis_scenario),
            ("npc_hostile_hypothesis_scenario",
             npc_hostile_hypothesis_scenario),
            ("npc_hp_link_hypothesis_scenario",
             npc_hp_link_hypothesis_scenario),
            ("move_authority_hypothesis_scenario",
             move_authority_hypothesis_scenario),
            ("ground_loot_hypothesis_scenario",
             ground_loot_hypothesis_scenario),
            ("ground_loot_nameprop_scenario",
             ground_loot_nameprop_scenario),
            ("learn_skill_result_hypothesis_scenario",
             learn_skill_result_hypothesis_scenario),
            ("learn_skill_request_hypothesis_scenario",
             learn_skill_request_hypothesis_scenario),
            ("skill_attr_hypothesis_scenario", skill_attr_hypothesis_scenario),
            ("pickup_listener_hypothesis_scenario",
             pickup_listener_hypothesis_scenario),
            ("item_operate_res_hypothesis_scenario",
             item_operate_res_hypothesis_scenario),
            ("hostile_hp_link_hypothesis_scenario",
             hostile_hp_link_hypothesis_scenario),
        ) if value is not None
    )
    # SCENARIO-COMPOSE-001: exactly the allow-listed sets pass (one pair,
    # one triple); any other combination of two or more lanes is refused
    # with the same message as always, so nothing outside the rulings got
    # looser.
    if len(active_lanes) > 1 and (
            active_lanes not in COMPOSABLE_SCENARIO_LANE_SETS):
        raise ValueError(
            "Arena, scene-load, population, item-move capture, item-move "
            "hypothesis, logout hypothesis, chat input hypothesis, channel "
            "message hypothesis, delete actor hypothesis, delete refresh "
            "hypothesis, stats progression hypothesis, hp death hypothesis, "
            "runtimeres death hypothesis, damage model hypothesis, damage "
            "hp link hypothesis, remote player hypothesis, npc hostile "
            "hypothesis, npc hp link hypothesis, move authority "
            "hypothesis, ground loot hypothesis, ground loot nameprop, "
            "learn skill result "
            "hypothesis, learn skill request hypothesis, skill attr "
            "hypothesis, pickup listener hypothesis, item operate res "
            "hypothesis, and hostile hp link hypothesis scenarios are "
            "mutually exclusive"
        )
    # CORE-REQUEST-004 (LANE-A / BUILD-002 / M2).  Parse the travel gate pin
    # ONCE, here, where a bad pin fails a boot in front of an operator
    # instead of failing every player's login.
    world_travel_gate.preload()
    # COO-DECISION 20260826T16:45+07:00: the walk-in-and-stand gate is no
    # longer part of the M2/production acceptance path (the owner ruled the
    # real route out of Port Royal is an NPC conversation with Columbus,
    # not a walk-in zone) -- kept as debug-only, off unless explicitly
    # opted in.  active_lanes is the runtime's own frozenset of the lanes
    # this boot selected (just above, in this same factory), so the
    # secondary conflict guard below still cannot drift from the runtime's
    # definition of "selected" when the debug opt-in is used.
    world_travel_lane_reason = world_travel_gate.lane_reason(
        active_lanes, debug_enabled=travel_gate_debug_enabled)
    # CORE-REQUEST-003 (LANE-A / BUILD-002 / v2 slice 1).  Load the scene
    # entry pin ONCE too, for the same reason: a broken pin should stop the
    # boot in front of an operator, not surface as a per-login refusal, and
    # a caller that passes a preloaded registry skips re-reading the file on
    # every login.
    scene_entry_registry = world_scene_travel.load_scene_registry()
    # CORE-REQUEST (LANE-A, notes_to_chief/20260826_1010 letter item 4-2).
    # Preloaded ONCE here too, same reason as the two pins just above: a
    # broken scene registry fails the boot in front of an operator instead
    # of every later login.  Report-only -- decide() below is always called
    # with rewrite left at its default False, so this ledger never writes a
    # row; it only makes a half-wired reporter visible in its counters
    # instead of looking like an honest empty ledger (world_scene_liveness.py
    # module docstring, "WHY THIS DOES NOT REWRITE ANYTHING").  Stood down
    # under the SAME predicate CORE-REQUEST-004 section 3 point 2 required
    # for the travel gate (scenario_stand_down(active_lanes), not
    # lane_reason(): this ledger has nothing to do with the debug-only
    # walk-in gate and must not go inert just because that flag is off).
    #
    # PF-ADVERSARY FINDING, round kdx85r, READ BEFORE READING THIS LEDGER'S
    # CONSOLE LINE IN PRODUCTION: travel_gate_debug_enabled is False by COO
    # ruling in every real boot (see world_travel_gate.lane_reason, just
    # above this block), so world_travel_gates.observe() returns inert on
    # every position report and NEVER calls _travel_gate_emit with a
    # WORLD_TRAVEL_SETTLED line -- only the one WORLD_TRAVEL_INERT line at
    # session construction.  That line still counts toward lines_seen (so
    # lines_seen alone does NOT distinguish a working half-wire from a
    # broken one), but settle_lines_seen ("settles=" in the console line)
    # stays 0 for the life of the process, by this design choice and not by
    # a gap in the wiring below.  An operator reading a wall of
    # "decision=flag reason=no_record ... settles=0" lines in production is
    # reading the expected, permanent state of every login, not a fault.
    scene_liveness_ledger = world_scene_liveness.SceneLivenessLedger.preload(
        registry=scene_entry_registry,
    )
    scene_liveness_stand_down_reason = world_travel_gate.scenario_stand_down(
        active_lanes)
    if scene_liveness_stand_down_reason is not None:
        scene_liveness_ledger.stand_down(scene_liveness_stand_down_reason)

    def _travel_gate_emit(line):
        # The same emit hook CORE-REQUEST-004 already writes the gate's
        # console lines through -- fanned out so the liveness ledger sees
        # every WORLD_TRAVEL_SETTLED line the gate ever prints, without a
        # second call site and without changing what the gate itself prints.
        # tests/test_world_scene_liveness_wiring.py drives a real crossing
        # through this exact closure (debug enabled) to prove the fan-out
        # actually reaches the ledger, not only that a line was printed.
        print(line)
        scene_liveness_ledger.observe_console_line(line)

    # CORE-REQUEST-007 (MOB-PICKUP-001), MOB_PICKUP_WIRING: "the server holds
    # ONE mob_pickup.BagCellRegistry the same way it holds [the scene's
    # ledger cell]" -- ONE PER SERVER, not per session, so it is built here,
    # once per boot, and closed over by every connection's session state
    # below, the same way scene_entry_registry just above is.
    mob_pickup_registry = mob_pickup.BagCellRegistry()
    # PF-HYPOTHESIS-LEDGER: HYP-PF-030 active
    # MOVE-AUTHORITY-002.  Re-checked here even though app.py already loaded
    # it: a caller that hands in a lookalike profile must not be able to gate
    # durable writes on budgets this project did not issue.
    if move_authority_hypothesis_scenario is not None:
        move_authority_hypothesis_scenario = (
            require_move_authority_hypothesis_scenario(
                move_authority_hypothesis_scenario
            )
        )
    # GROUND-LOOT-001.  Re-checked here even though app.py already loaded
    # it: a caller that hands in a lookalike profile must not be able to put
    # bytes this module did not pin onto a live socket.
    if ground_loot_hypothesis_scenario is not None:
        ground_loot_hypothesis_scenario = (
            require_ground_loot_hypothesis_scenario(
                ground_loot_hypothesis_scenario
            )
        )
    # GROUND-LOOT-NAMEPROP-001.  Same re-check for the selector lane: it is
    # a SEPARATE lane from GROUND-LOOT-001 and never shares a boot with it,
    # so a lookalike must not be able to reach a socket through either door.
    if ground_loot_nameprop_scenario is not None:
        ground_loot_nameprop_scenario = (
            require_ground_loot_nameprop_scenario(
                ground_loot_nameprop_scenario
            )
        )
    # LEARN-SKILL-RESULT-001.  Re-checked here even though app.py already
    # loaded it: a caller that hands in a lookalike profile must not be able
    # to put bytes this project did not pin onto a live socket.
    if learn_skill_result_hypothesis_scenario is not None:
        learn_skill_result_hypothesis_scenario = (
            require_learn_skill_result_hypothesis_scenario(
                learn_skill_result_hypothesis_scenario
            )
        )
    # LEARN-SKILL-REQUEST-001.  Re-checked here even though app.py already
    # loaded it: a caller that hands in a lookalike profile must not be able
    # to open an inbound decode path this project did not pin.
    if learn_skill_request_hypothesis_scenario is not None:
        learn_skill_request_hypothesis_scenario = (
            require_learn_skill_request_hypothesis_scenario(
                learn_skill_request_hypothesis_scenario
            )
        )
    # SKILL-ATTR-001.  Re-checked here even though app.py already loaded
    # it: a caller that hands in a lookalike profile must not be able to
    # put bytes this project did not pin onto a live socket.
    if skill_attr_hypothesis_scenario is not None:
        skill_attr_hypothesis_scenario = (
            require_skill_attr_hypothesis_scenario(
                skill_attr_hypothesis_scenario
            )
        )
    # PICKUP-LISTENER-001.  Re-checked here even though app.py already
    # loaded it: a caller that hands in a lookalike profile must not be able
    # to open an inbound decode path this project did not pin.
    if pickup_listener_hypothesis_scenario is not None:
        pickup_listener_hypothesis_scenario = (
            require_pickup_listener_hypothesis_scenario(
                pickup_listener_hypothesis_scenario
            )
        )
    # ITEMOP-RES-GREENLINE-001.  Re-checked here even though app.py already
    # loaded it: a caller that hands in a lookalike profile must not be able
    # to put bytes this project did not pin onto a live socket.
    if item_operate_res_hypothesis_scenario is not None:
        item_operate_res_hypothesis_scenario = (
            require_item_operate_res_hypothesis_scenario(
                item_operate_res_hypothesis_scenario
            )
        )
    # DELETE-REFRESH-001 and HYP-PF-015 key on the same vital id 0x36DB, so
    # they must never be able to see the same frame: the mutual-exclusion
    # check above refuses the pair outright and app.py refuses the two flags
    # together, which is why the ordering of the two dispatch branches below
    # cannot matter.
    if delete_refresh_hypothesis_scenario is not None:
        delete_refresh_hypothesis_scenario = (
            require_delete_refresh_hypothesis_scenario(
                delete_refresh_hypothesis_scenario
            )
        )
    if stats_progression_hypothesis_scenario is not None:
        stats_progression_hypothesis_scenario = (
            require_stats_progression_hypothesis_scenario(
                stats_progression_hypothesis_scenario
            )
        )
    # HP-DEATH-002.  The lethal unlock token is derived ONCE, here, from the
    # allowlisted scenario object.  It is the only value in this process that
    # can widen the encoder's field table to include BasicAttr bit 0x0080 (the
    # death timer the client's IsDead predicate reads), and with no hp-death
    # scenario it stays None, the lethal branch below does not exist, and the
    # encoder cannot name the field at all.
    #
    # HYP-PF-022 ships two named step-plan profiles behind that one token --
    # ``death_sweep`` (arm, kill, restore; ends alive) and ``dying_hold`` (arm,
    # kill, stop; ends dead on purpose, with the 20.0 s DURATION_DYING the
    # client image carries).  The profile is derived ONCE, here, from the same
    # allowlisted scenario object, so the dispatch loop below cannot pick a plan
    # of its own.
    hp_death_lethal = None
    hp_death_profile = None
    if hp_death_hypothesis_scenario is not None:
        hp_death_hypothesis_scenario = require_hp_death_hypothesis_scenario(
            hp_death_hypothesis_scenario
        )
        hp_death_lethal = hp_death_lethal_unlock(hp_death_hypothesis_scenario)
        hp_death_profile = hp_death_profile_for_scenario(
            hp_death_hypothesis_scenario
        )
        # Drift check, not decoration.  The label prefix and the first-frame
        # delay used to be read straight off these two module constants, and
        # other readers (the ledger's source pins, the headless replay tool,
        # the attended playbook) still name them.  Under the death_sweep
        # profile the profile-carried values must therefore still BE those
        # constants, or two readers of the same sweep would disagree about what
        # went out on the wire.
        if hp_death_profile.name == HP_DEATH_PROFILE_DEATH_SWEEP_NAME and (
            hp_death_profile.action_label_prefix != HP_DEATH_ACTION_LABEL_PREFIX
            or hp_death_profile.first_delay_seconds
            != HP_DEATH_FIRST_DELAY_SECONDS
        ):
            raise ValueError(
                "hp death hypothesis scenario object exceeds the allowlist"
            )
    # RUNTIMERES-DISPATCH-001 (HYP-PF-023; the ledger annotation for this lane
    # lives once per file, on the dispatch method below, exactly as HP-DEATH-002
    # does it).  Same shape as HP-DEATH-002 above and for the same reasons, with
    # one addition: the probe
    # is resolved ONCE, here, so a drift in the frozen placement source or in
    # the frozen V135 player spawn refuses at construction time rather than
    # killing a different NPC in the middle of an attended session.
    #
    # This lane is NOT the hp-death lane.  HP-DEATH-002 rides UpdateAttrVital
    # 0x309A, which round 85 proved can never reach the engine death chain;
    # this one rides GSCN_RunTimeProtocolRes 0x6E9D with the derived change
    # mask bit 0x02 (the actor-entry collection at +0x1C), whose inbound
    # handler 0x5E4060 feeds 0x446F30 -> vtable +0x20 -> 0x4446F0 -> 0x4437C0.
    runtimeres_death_lethal = None
    runtimeres_death_probe = None
    if runtimeres_death_hypothesis_scenario is not None:
        runtimeres_death_hypothesis_scenario = (
            require_runtimeres_death_hypothesis_scenario(
                runtimeres_death_hypothesis_scenario
            )
        )
        runtimeres_death_lethal = runtimeres_death_lethal_unlock(
            runtimeres_death_hypothesis_scenario
        )
        runtimeres_death_probe = resolve_runtimeres_death_probe(legacy)
    # DAMAGE-DISPATCH-001 (HYP-PF-024; the ledger annotation for this lane
    # lives once per file, on the dispatch method below).  Same shape as the
    # two lanes above: the unlock token is derived ONCE, here, from the
    # allowlisted scenario object, and it is the only value in this process
    # that lets anything name the signed damage integer at hit-entry +0x08 or
    # the flag word at +0x1C.  With no damage-model scenario it stays None and
    # no CHitResult can be composed at all.
    #
    # This lane is neither of the two death lanes.  It rides CHitResult 0x16F7
    # version 0 as an element of the VitalData collection -- the BASE change
    # mask bit 0x02, object +0x18 -- which is a DIFFERENT collection from the
    # actor-entry one RUNTIMERES-DISPATCH-001 uses, despite the matching bit
    # number.  The reader that validates the version byte is 0x5F3EFC.
    damage_model_unlock = None
    if damage_model_hypothesis_scenario is not None:
        damage_model_hypothesis_scenario = (
            require_damage_model_hypothesis_scenario(
                damage_model_hypothesis_scenario
            )
        )
        damage_model_unlock = damage_model_wire_unlock(
            damage_model_hypothesis_scenario
        )
    # DAMAGE-HP-LINK-001 (HYP-PF-026; the ledger annotation for this lane
    # lives once per file, on the dispatch method below).  Same shape as the
    # lanes above: the wire unlock token is derived ONCE, here, from the
    # allowlisted scenario object.  It is the only value in this process that
    # lets the link lane compose either of its two carriers, and with no
    # scenario it stays None, the dispatch branch below does not exist, and
    # the encoder cannot emit a byte.
    damage_hp_link_unlock = None
    if damage_hp_link_hypothesis_scenario is not None:
        damage_hp_link_hypothesis_scenario = (
            require_damage_hp_link_hypothesis_scenario(
                damage_hp_link_hypothesis_scenario
            )
        )
        damage_hp_link_unlock = damage_hp_link_wire_unlock(
            damage_hp_link_hypothesis_scenario
        )
    # REMOTE-PLAYER-DISPATCH-001 (HYP-PF-025; the ledger annotation for this
    # lane lives once per file, on the dispatch method below).  Same shape as
    # the three lanes above: the wire unlock token is derived ONCE, here, from
    # the allowlisted scenario object, and it is the only value in this
    # process that lets anything put actor_type 2 on the actor-entry wire.
    # The probes are resolved ONCE, here, so a drift in the frozen placement
    # source refuses at construction time rather than mid-session.
    #
    # This lane rides the SAME carrier as RUNTIMERES-DISPATCH-001 (0x6E9D,
    # derived mask bit 0x02, actor entries) but is a different experiment:
    # actor_type 2 (CNetActor) instead of 4, an ActorAttr with the name bit
    # instead of an NPCAttr, and a wrong-class negative control.  The mutual
    # exclusion above keeps the two lanes from ever seeing the same frame.
    remote_player_unlock = None
    remote_player_probes = None
    if remote_player_hypothesis_scenario is not None:
        remote_player_hypothesis_scenario = (
            require_remote_player_hypothesis_scenario(
                remote_player_hypothesis_scenario
            )
        )
        remote_player_unlock = remote_player_wire_unlock(
            remote_player_hypothesis_scenario
        )
        remote_player_probes = resolve_remote_player_probes(legacy)
    # NPC-HOSTILE-DISPATCH (HYP-PF-027; the ledger annotation for this lane
    # lives once per file, on the dispatch method below).  Same shape as the
    # lanes above: the wire unlock token is derived ONCE, here, from the
    # allowlisted scenario object, and it is the only value in this process
    # that lets anything put BasicAttr bit 0x0400 on the actor-entry wire.
    # The probe is resolved ONCE, here, so a drift in the frozen placement
    # source refuses at construction time rather than mid-session.
    #
    # This lane rides the SAME carrier and the SAME probe as the death lane
    # (0x6E9D, derived mask bit 0x02, NPC 0x2001) but asks a different
    # question: does a spawn-time faction field make the placement PRESENT
    # as hostile, paired with the SCENE-005 player faction on the entry side.
    # The mutual exclusion above keeps the lanes from ever seeing the same
    # frame.
    npc_hostile_unlock = None
    npc_hostile_probe = None
    if npc_hostile_hypothesis_scenario is not None:
        npc_hostile_hypothesis_scenario = (
            require_npc_hostile_hypothesis_scenario(
                npc_hostile_hypothesis_scenario
            )
        )
        npc_hostile_unlock = npc_hostile_wire_unlock(
            npc_hostile_hypothesis_scenario
        )
        npc_hostile_probe = resolve_npc_hostile_probe(legacy)
    # NPC-HP-LINK-002 (HYP-PF-029; the ledger annotation for this lane lives
    # once per file, on the dispatch method below).  Same shape as the lanes
    # above: the wire unlock token is derived ONCE, here, from the allowlisted
    # scenario object, and it is the only value in this process that lets the
    # target-link lane compose either of its two carriers.  With no scenario it
    # stays None, the dispatch branch below does not exist, and the encoder
    # cannot emit a byte.  The frozen Port Royal target is resolved ONCE, here,
    # so a drift in the frozen placement source refuses at construction time
    # rather than mid-session.
    #
    # This lane ALTERNATES the two collections of 0x6E9D that its parents ride
    # one at a time -- the VitalData/CHitResult carrier of HYP-PF-024 and the
    # actor-entry/NPCAttr carrier of HYP-PF-023 -- against the SAME frozen
    # probe those lanes drive (NPC 0x2001).  The mutual exclusion above keeps
    # the lanes from ever seeing the same frame.
    npc_hp_link_unlock = None
    npc_hp_link_target = None
    if npc_hp_link_hypothesis_scenario is not None:
        npc_hp_link_hypothesis_scenario = (
            require_npc_hp_link_hypothesis_scenario(
                npc_hp_link_hypothesis_scenario
            )
        )
        npc_hp_link_unlock = npc_hp_link_wire_unlock(
            npc_hp_link_hypothesis_scenario
        )
        npc_hp_link_target = resolve_npc_hp_link_target(legacy)
    # HOSTILE-HP-LINK-001 (HYP-PF-038; the ledger annotation for this lane
    # lives once per file, on the dispatch method below).  The unlock token is
    # derived ONCE, here, from the allowlisted scenario object and is the only
    # value in this process that lets this lane compose either carrier.
    #
    # THE TARGET IS NOT RESOLVED HERE, and that is the one structural
    # difference from the sibling lane: this lane places its target against
    # the LIVE player position, which does not exist yet at construction time.
    # It is resolved per accepted request instead, from the authoritative row
    # the frozen TargetPos write path checkpoints -- so a session that never
    # reached a position cannot compose a frame at all.
    hostile_hp_link_unlock = None
    if hostile_hp_link_hypothesis_scenario is not None:
        hostile_hp_link_hypothesis_scenario = (
            require_hostile_hp_link_hypothesis_scenario(
                hostile_hp_link_hypothesis_scenario
            )
        )
        hostile_hp_link_unlock = hostile_hp_link_wire_unlock(
            hostile_hp_link_hypothesis_scenario
        )
    if delete_actor_hypothesis_scenario is not None:
        delete_actor_hypothesis_scenario = (
            require_delete_actor_hypothesis_scenario(
                delete_actor_hypothesis_scenario
            )
        )
    if logout_hypothesis_scenario is not None:
        logout_hypothesis_scenario = require_logout_hypothesis_scenario(
            logout_hypothesis_scenario
        )
    if chat_input_hypothesis_scenario is not None:
        chat_input_hypothesis_scenario = require_chat_input_hypothesis_scenario(
            chat_input_hypothesis_scenario
        )
    if channel_message_hypothesis_scenario is not None:
        channel_message_hypothesis_scenario = (
            require_channel_message_hypothesis_scenario(
                channel_message_hypothesis_scenario
            )
        )
    if population_scenario is not None:
        population_scenario = require_population_scenario(population_scenario)
    if item_move_capture_scenario is not None:
        item_move_capture_scenario = require_item_move_capture_scenario(
            item_move_capture_scenario
        )
    if item_move_hypothesis_scenario is not None:
        item_move_hypothesis_scenario = require_item_move_hypothesis_scenario(
            item_move_hypothesis_scenario
        )
    # Occupied-destination swap activates only under the dedicated swap
    # profile of the item-move opt-in scenario.  Under the original profile
    # (and with no scenario at all) occupied destinations stay fail-closed
    # exactly as pinned by HYP-PF-010.
    item_swap_enabled = (
        item_move_hypothesis_scenario is not None
        and item_move_hypothesis_scenario.occupied_swap
    )
    # Occupied-destination same-template merge activates only under the
    # dedicated merge profile.  Under every other mode occupied destinations
    # keep their pinned behavior: HYP-PF-010 fail-closed silence, or the
    # HYP-PF-017 swap under the swap profile only.
    item_merge_enabled = (
        item_move_hypothesis_scenario is not None
        and item_move_hypothesis_scenario.occupied_merge
    )
    # WORLD-CENSUS-001 (LANE-A BUILD-001, wired here because runtime.py is the
    # chief's file).  The frozen dispatcher sends three of the 115 decoded
    # bg0001 placements on every boot (v141:4292, label
    # V134_P0_P30_P91_ISOLATED_*).  This lane replaces that ONE branch with the
    # same encoder over the same frozen table at census size.
    #
    # It is NOT behind a flag: on a default boot it is on.  What it IS behind
    # is "no opt-in lane is active at all".  Every hypothesis lane in this file
    # was measured against the three-actor baseline and several of them pin
    # actor identities inside the band the census occupies (0x2001..0x2095,
    # placement index + 0x2001, 34 gaps).  Widening the population underneath
    # a lane that is measuring something else would silently change that
    # lane's control, so an opt-in boot keeps exactly the population it has
    # always had.  This is a containment rule, not a gate on the feature.
    #
    # HYP-PF-009 is not a scenario object and so is not in active_lanes, but a
    # --second-password-mode other than "required" is an opt-in measurement
    # lane by every other test: it was characterized against the three-actor
    # baseline, and its whole question is what this client does with an
    # unsolicited frame.  Adding 17.9 KB of unmeasured population to that
    # socket would confound it, so it is contained here by name.
    # --export-events is deliberately NOT contained: it changes what is
    # printed, never what is sent, and GT-076 needs it.
    second_password_mode = require_second_password_mode(second_password_mode)
    world_census_enabled = (
        not active_lanes and second_password_mode == "required"
    )
    # None means "the census, capped by whatever MEASURED_CLIENT_ACTOR_CEILING
    # says at call time".  An explicit count is the attended staircase
    # instrument (GT-076, the actor-ceiling staircase): it selects a rung,
    # it does not enable the lane.  GT-078 is the acceptance ticket for the
    # unflagged default boot and must never be run with this argument set.
    # Validated here so a bad --world-census-actors fails at startup rather
    # than on a live client's first step.
    if world_census_actor_count is not None:
        world_population.effective_actor_count(world_census_actor_count)
    if monotonic_clock is None:
        monotonic_clock = time.monotonic
    if close_timer_factory is None:
        def close_timer_factory(delay_seconds, callback):
            timer = threading.Timer(delay_seconds, callback)
            timer.daemon = True
            timer.start()
            return timer
    class PersistentGameSessionState(legacy.GameSessionState):
        def __init__(self, token: str):
            super().__init__(token)
            if event_exporter is not None:
                # EVENT-EXPORT-001: installed before any dispatch can run,
                # so the echo list sees every event of the session from the
                # first frame on, dispatch and reject alike.
                self.events = _EventEchoList(event_exporter)
            self.foundation = (
                session_factory(token) if session_factory is not None
                else FoundationSession(
                    lifecycle, projector, token,
                    allow_hypothesized_item_move=(
                        item_move_hypothesis_scenario is not None
                    ),
                    allow_hypothesized_item_swap=item_swap_enabled,
                    allow_hypothesized_item_merge=item_merge_enabled,
                    allow_soft_delete=(
                        delete_actor_hypothesis_scenario is not None
                        or delete_refresh_hypothesis_scenario is not None
                    ),
                )
            )
            try:
                # CORE-REQUEST-004 (LANE-A / BUILD-002 / M2).  No file I/O
                # and no raise here -- everything that can refuse already
                # refused inside world_travel_gate.preload() at server
                # start, above.  A pin missing at this point means the lane
                # goes inert for the whole session rather than costing a
                # player their login.
                self.world_travel_gates = (
                    world_travel_gate.TravelGateSet.from_preloaded(
                        inert_reason=world_travel_lane_reason,
                        emit=_travel_gate_emit,
                    )
                )
                # Same process-wide ledger every session closes over -- kept
                # on self, mirroring world_travel_gates just above, so a
                # caller (a test, a future ops hook) can read what this
                # session's login actually saw without a second call site.
                self.scene_liveness_ledger = scene_liveness_ledger
                self.arena_scenario = scenario
                self.arena_spawned = False
                self.arena_target_captured = False
                self.item_move_capture_count = 0
                self.item_move_capture_last_fields = None
                self.item_move_hypothesis_count = 0
                self.item_move_generalized_count = 0
                self.item_swap_occupied_count = 0
                self.item_merge_occupied_count = 0
                self.logout_ack_count = 0
                self.logout_acknowledged = False
                self.logout_close_scheduled = False
                # HYP-PF-031 one-shot latch: the unsolicited return-select
                # push may leave this session exactly once.
                self.logout_chat_push_count = 0
                # HYP_PF_040 one-shot latch: the unsolicited return-select
                # push at dialog-open time (branch 6) may leave this
                # session exactly once.
                self.logout_dialog_open_push_count = 0
                # GROUND-LOOT-001 one-shot latch: the bit-0x08 pair frame
                # may leave this session exactly once, and a refused
                # composition latches too so drift can never retry itself
                # onto the wire.
                self.ground_loot_pair_sent = False
                # GROUND-LOOT-NAMEPROP-001 one-shot latch, its own and never
                # shared with the lane above: a refused composition latches
                # too, so drift can never retry itself onto the wire.
                self.ground_loot_nameprop_sent = False
                self.worldinfo_last_payload = None
                self.worldinfo_stored_count = 0
                self.chat_input_echo_count = 0
                self.channel_message_sweep_count = 0
                self.stats_progression_sweep_count = 0
                self.learn_skill_result_sweep_count = 0
                self.learn_skill_request_accepted_count = 0
                self.learn_skill_request_last_fields = None
                # PICKUP-LISTENER-001 (HYP-PF-036) observability surface:
                # accepted decodes append (count, object_ref_u32, opaque_u8,
                # raw body hex) to the record list; classification refusals
                # append (reason, raw body hex) to the refusal list.  Both
                # are in-memory only and never persisted.
                self.pickup_listener_accepted_count = 0
                self.pickup_listener_last_fields = None
                self.pickup_listener_records = []
                self.pickup_listener_refusals = []
                self.skill_attr_sweep_count = 0
                self.item_operate_res_sweep_count = 0
                self.hostile_hp_link_sweep_count = 0
                self.hp_death_sweep_count = 0
                self.runtimeres_death_sweep_count = 0
                self.damage_model_sweep_count = 0
                self.damage_hp_link_sweep_count = 0
                self.remote_player_sweep_count = 0
                self.npc_hostile_sweep_count = 0
                self.npc_hostile_player_faction_start_sent = False
                self.npc_hp_link_sweep_count = 0
                # MOVE-AUTHORITY-002 (HYP-PF-030): the gate keeps its own
                # accepted-position memory so a REFUSED report can never
                # become the baseline the next report is measured against.
                self.move_authority_accept_count = 0
                self.move_authority_refusal_count = 0
                self.move_authority_last_verdict = None
                self.move_authority_last_accepted_xyz = None
                self.move_authority_last_accepted_at = None
                # Zero on purpose.  Grace is granted when THE SERVER moves
                # the player, never because a connection is young: two
                # unmeasured writes at the start of every connection would be
                # an unbounded bypass a client could re-arm by reconnecting.
                self.move_authority_grace_remaining = 0
                # CORE-REQUEST-GM-030: armed when a GM warp action is queued,
                # cleared by the first TargetPos that actually WRITES.  It is
                # unconditional on purpose -- GT-128 boots with no scenario
                # flag at all, so a flag that lived behind one would never be
                # raised on the only boot shape the attended test uses.
                self.gm_warp_position_pending = False
                # Open for exactly one frame: the first TargetPos after the
                # warp.  dispatch() opens it, dispatch() closes it.
                self.gm_warp_confirm_window_open = False
                self.gm_warp_pending_character = None
                # CORE-REQUEST-GM-030/031: the destination `gm.warp_target_
                # record` handed back for this confirm window, or None when
                # nothing was parked (or the parked record did not survive
                # `take_warp_target_with_reason`'s checks -- see
                # `gm_warp_confirm_target_reason` for why in that case).
                # Read only inside the same frame the confirm window opened
                # and closed on -- see `_gm_warp_open_confirm_window` and
                # `_gm_warp_close_confirm_window`.
                self.gm_warp_confirm_target = None
                self.gm_warp_confirm_target_reason = None
                # CHIEF-DECISION 20260829_0520 option A, second half (round
                # ngwnnj/R223, added after pf-adversary measured what the
                # first half did on its own).  True for a session whose
                # login used a login-scene override: the character is
                # VISITING that scene, and this session writes no durable
                # position row for it.  See _checkpoint_exact_target.
                self.login_scene_override_visit = False
                self.delete_actor_soft_delete_count = 0
                self.delete_refresh_list_rebuild_count = 0
                self.transport_socket_closer = None
                self.second_password_bypass_sent = False
                self.second_password_bypass_keepalive_started = False
                self.second_password_bypass_last_sent_at = None
                # WORLD-CENSUS-001 observability.  ``world_census_actor_count``
                # is the number that actually went onto the wire this session,
                # not the number that was asked for.
                self.world_census_actor_count = None
                # CORE-REQUEST (LANE-B 20260829_2055): the recompose path's
                # own anchor, stamped with the scene it was measured in.
                # Initialized HERE beside its siblings rather than left to
                # the ``getattr(..., None)`` at the two read sites, so a
                # session that never composed a census carries the same
                # None both lanes' guards already read.
                self.census_anchor_record = None
                self.world_census_indices = None
                self.world_census_sent = False
                self.world_census_refused = False
                # Whether the census that is currently in force resolved its
                # identities through ``world_port_royal_identity``.  NOT the
                # same question as ``world_census_sent``: the frozen P0/P30/P91
                # fallback and every lane boot also set that flag, while
                # shipping Mob-Set numbers as identities.  ``world_face_frame``
                # may only correct a click frame when this is True - see the
                # AMENDMENT comment at its call site for what goes wrong
                # otherwise (pf-adversary, round c5nwjc, D2).
                self.world_census_identity_resolved = False
                # CORE-REQUEST (MOB-COMBAT-001 / MOB-DEATH-001).  UNCONDITIONAL,
                # like WORLD-CENSUS-001 above: no scenario flag gates this
                # state, held per session for the reason the ledger and the
                # register are frozen values -- a compare-and-swap needs
                # somewhere to hold the value it swaps.
                # [PROPOSED] PER-SESSION, not server-wide: two different
                # connections attacking the SAME field mob each get their own
                # ledger, so one player's hits do not lower HP another
                # player's session can see.  MOB_COMBAT_WIRING does not say
                # where the ledger lives; this follows the pattern every
                # other mutable structure on this class already uses.  A
                # server-wide ledger is a real follow-up, not a silent
                # decision -- see the handback.
                # COO-DECISION 2026-08-29T08:48+07:00 item 3 (chief's half):
                # the ledger and the AI register below open on ONE roster,
                # and _sync_combat_scene_state() re-opens both the first
                # time this session's selected character stands in a scene
                # whose folder differs from the one recorded here.  At
                # construction no character is selected and no scene is
                # known, so this opens on the same default roster it always
                # has (bg0001's) and records that roster's own scene tag --
                # derived from the rows, not retyped, so it cannot drift
                # from what the ledger actually holds.
                _boot_roster = field_mobs.load_roster()
                self.mob_combat_ledger = mob_combat.open_ledger(_boot_roster)
                self.mob_combat_scene_folder = (
                    _boot_roster[0].scene if _boot_roster else None
                )
                # CORE-REQUEST (LANE-B, 20260828_0337): the attack-cadence
                # gate MOB_COMBAT_CADENCE_WIRING asks for, opened next to
                # mob_combat_ledger for the same per-session reason.
                self.mob_combat_cadence = mob_combat.open_cadence_ledger()
                self.mob_death_register = mob_death.DeathRegister()
                self.mob_combat_hit_count = 0
                self.mob_combat_kill_count = 0
                # RE-157 job 2 / MOB-COMBAT-001 announced-actor guard.
                # ``mob_combat_membership.AnnouncedActorMembership`` (or
                # None, meaning "no census has ever committed this
                # session") -- the exact actor-identity set the LAST
                # committed census actually put on the wire for the
                # scene it was composed for, plus the generation counter
                # below.  Read by ``_dispatch_mob_combat`` via
                # ``mob_combat_membership.admits()`` before a
                # target-is-field-mob ActionVital is allowed to spend
                # cadence or mutate the ledger; written only at the
                # census commit points that already know the exact set
                # of identities they are shipping (bg0001 home census,
                # bg0002 census, and the lane composer census); cleared
                # on scene handoff (``_gm_warp_resync_selected_scene``)
                # so a stale scene's membership can never leak into a
                # new one.  UNCONDITIONAL, like the sibling mob-combat
                # state above -- no scenario flag gates it.
                self.mob_combat_announced_membership = None
                # Opaque counter this session owns and bumps by one on
                # every committed census (never read by anything but
                # this class and the ``admits()`` call it feeds), so an
                # ``AnnouncedActorMembership`` recorded for an earlier
                # census can never be mistaken for the current one even
                # when the scene id happens to repeat (a warp back to a
                # scene already visited this session).
                self.mob_combat_announced_membership_generation = 0
                # CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001).  Empty for every
                # account that is not in config/diag_multi_object.json, which
                # this repo does not ship: the default is a zero-length tuple
                # read per session.  See diag_multi_object_wiring.py's own
                # RUNTIME_WIRING_PATCH docstring for the full call-site list.
                self.diag_multi_objects = ()
                # CORE-REQUEST-014 (Columbus, MOBS n_ID 156, bg0001 placement
                # index 1).  UNCONDITIONAL, like WORLD-CENSUS-001/MOB-COMBAT-
                # 001 above -- no scenario flag gates this.  Per-session
                # because one ChooseNPC -> NPCConversation -> QuestOperateVital
                # sequence belongs to one connection, same as move_authority/
                # mob_combat state above.  See columbus_quest_dispatch.py for
                # what these flags gate.  UPDATED round e0daaa: the dispatch
                # no longer always refuses -- PANYA-DECISION 2026-08-27T15:25
                # +07:00 dropped the vehicle-bind requirement, so a matching
                # op1/3021 frame now sends a real teleport.  ``_dispatch_
                # attempted`` still latches permanently on the FIRST attempt,
                # success or refusal alike -- pf-adversary flagged this as a
                # real (not merely theoretical) stuck-player risk now that
                # success is possible: if that one teleport is ever lost
                # (dropped packet, or the client's own FSM state refusing an
                # unsolicited TeleportVital per RE-077 T3 -- never checked
                # for this call site), a retry from the client silently
                # no-ops here with no event and no reply.  Not fixed this
                # round; see CHIEF-STATUS 2026-08-27T15:45+07:00 and GT-106.
                self.columbus_quest3021_conversation_sent = False
                self.columbus_quest3021_dispatch_attempted = False
                # CORE-REQUEST-019 (Lane A, 2026-08-27T18:48+07:00): option 2
                # / quest 3205 (Q_BORNAGAIN) is a separate op1 the client can
                # send independently of quest 3021's, off the same two-entry
                # conversation above -- its own latch, not reuse of the 3021
                # one, so choosing one option does not block a later attempt
                # at the other.
                self.columbus_quest3205_dispatch_attempted = False
                # CORE-REQUEST-007 (MOB-AI-CONTROL-001).  Same per-session
                # choice as mob_combat_ledger/mob_death_register just above,
                # for the same reason: MOB_AI_CONTROL_WIRING does not say
                # where the register lives, and this follows the pattern
                # every other mutable structure on this class already uses.
                # epoch=0 because this class never rebuilds the roster
                # WITHIN one scene (the table read is frozen, not a live
                # reload) -- so REFUSE_REGISTER_EPOCH_MISMATCH and
                # mob_ai_control.reconcile() stay unreached.  A SCENE CHANGE
                # is not a rebuild: _sync_combat_scene_state() re-opens this
                # register (and the combat ledger above) on the new scene's
                # roster at epoch 0, because the old scene's mobs are gone
                # from the player's world, not renumbered within it.
                # Opened on the SAME _boot_roster as the ledger above
                # (COO-DECISION 2026-08-29T08:48+07:00 item 3): the two must
                # never hold different scenes' rows.
                self.mob_ai_register = mob_ai_control.open_register(
                    _boot_roster, epoch=0,
                )
                # CORE-REQUEST-007 (MOB-LOOT-001), MOB_LOOT_WIRING: "Hold ONE
                # mob_loot.DropLedgerCell for the scene" -- same per-session
                # scope as mob_combat_ledger/mob_death_register/
                # mob_ai_register just above, for the same reason (the
                # wiring text does not name a lifetime; this follows the
                # pattern every other mutable structure on this class
                # already uses).  self.mob_loot_rng is the random.Random
                # roll_drops requires "the server owns" -- created ONCE here,
                # never per call, so the draw stream is this session's own
                # and not the module-global stream _require_rng refuses by
                # name.
                self.mob_loot_cell = mob_loot.DropLedgerCell()
                self.mob_loot_rng = random.Random()
                # CORE-REQUEST-007 (MOB-PICKUP-001), MOB_PICKUP_WIRING step 0:
                # this session's claim against the server-wide
                # mob_pickup_registry (built once above).  None until
                # character select claims it; release() is owed back to the
                # registry at teardown (see close_connection below).
                self.mob_pickup_bag_cell = None
                self.mob_pickup_character_id = None
                if world_census_enabled:
                    # The inherited P0/P30/P91 branch is disarmed HERE, at
                    # construction, exactly the way the population and
                    # scene-load lanes disarm it -- not from inside dispatch.
                    #
                    # Doing it from dispatch was wrong twice over, and both
                    # were measured rather than argued.  (1) The frozen branch
                    # reads runtime_ack_sent AFTER the same dispatch call has
                    # set it (v141:3771 then v141:4292), so a pre-dispatch
                    # check loses the transition frame and the three-actor
                    # branch wins the session with nothing recording that it
                    # did.  (2) The frozen branch lives under
                    # "outer_id == GSCN_RunTimeProtocolReq and teleport_sent"
                    # (v141:3680); a pre-dispatch trigger without those
                    # conjuncts could set population_indices on a frame the
                    # inherited dispatcher ignored, leaving last_target_pos
                    # None -- and v141:4416 unpacks last_target_pos for any
                    # member of population_indices, so the next NPC click
                    # raised TypeError out of the listener thread.
                    #
                    # With the branch disarmed at init, the census composes
                    # AFTER super().dispatch() from state the inherited
                    # dispatcher has already updated on this frame, which is
                    # the same state the frozen branch would have read.
                    self.npc_spawn_sent = True
                    self.population_indices = None
                    self.events.append("world_census_armed")
                if population_scenario is not None:
                    # The typed capability owns TargetPos population state.  The
                    # inherited dispatcher must remain permanently unable to
                    # install its frozen P0/P30/P91 prerequisite in this session.
                    self.npc_spawn_sent = True
                    self.population_indices = None
                    self.object_population_membership = None
                    self.object_population_anchor = None
                    self.object_population_generation = 0
                if scene_load_scenario is not None:
                    # The load-only branch must never inherit V141 population.
                    self.npc_spawn_sent = True
                    self.population_indices = ()
                    if scene_load_scenario.remote_actor is not None:
                        self.scene_remote_spawned = False
                        self.scene_remote_target_captured = False
                        self.scene_action_ack_sent = False
                        self.scene_hostile_target_captured = False
                if connection_bindings is not None:
                    connection_bindings.bind(self)
            except BaseException as error:
                try:
                    self.foundation.close_connection()
                except BaseException as close_error:
                    error.add_note(
                        f"Foundation session cleanup also failed: {close_error!r}"
                    )
                raise

        def close_connection(self) -> bool:
            # CORE-REQUEST-007 (MOB-PICKUP-001), MOB_PICKUP_WIRING step 0:
            # "registry.release(character_id) on logout, disconnect or a
            # character switch."  close_connection is the one teardown path
            # every disconnect reaches regardless of which probe lane (if
            # any) is active, unlike the logout-hypothesis dispatch, which
            # only runs behind its own opt-in scenario.  A teardown that
            # never runs leaves the character claimed and the next select
            # refuses out loud (bag_already_claimed) -- the failure this
            # lane wants, per the module's own docstring.
            if self.mob_pickup_bag_cell is not None:
                mob_pickup_registry.release(self.mob_pickup_character_id)
                self.mob_pickup_bag_cell = None
                self.mob_pickup_character_id = None
            return self.foundation.close_connection()

        def attach_transport_socket_closer(self, closer) -> None:
            """Accept the one bound transport close lever from the adapter.

            The closer performs a clean shutdown+close of this connection's
            accepted GAME socket.  It is only ever pulled by the HYP-PF-013
            post-ack schedule below; without the close_socket scenario flag
            it is stored and never invoked.
            """
            if self.transport_socket_closer is not None:
                raise RuntimeError("transport socket closer already attached")
            if not callable(closer):
                raise TypeError("transport socket closer must be callable")
            self.transport_socket_closer = closer

        def _world_census_frozen_fallback(self, anchor):
            """Queue the shipped three-actor collection after a census refusal.

            The census disarms the inherited branch at construction, so a
            refusal cannot simply fall through to it - by the time the refusal
            happens that branch is already latched off for the session.  This
            rebuilds exactly what it would have built, under exactly its
            labels, schedule and bookkeeping, so a session that refuses is the
            session this project shipped yesterday and not a session with an
            empty town.

            If even the frozen builder raises, nothing is queued and the
            refusal is named: a listener thread that survives with no
            population beats one that dies with a traceback.
            """
            try:
                npc_pc, npc_frame, local_rows = (
                    legacy.make_v112_monster_shop_population_state()
                )
            except Exception as error:
                self.events.append(
                    f"world_census_fallback_refused_{type(error).__name__}"
                )
                return []
            self.world_census_sent = True
            # The frozen P0/P30/P91 rows ship Mob-Set numbers as identities.
            # The click frame must keep agreeing with THEM, wrong as they are,
            # rather than be corrected into disagreeing with what this login
            # already put on the client's screen.
            self.world_census_identity_resolved = False
            self.npc_idle_action_sent = False
            self.population_indices = tuple(row[0] for row in local_rows)
            self.population_refresh_anchor = anchor
            self.events.append("world_census_fell_back_to_frozen_p0_p30_p91")
            self.events.append(
                "v112_isolated_population_indices_"
                + "_".join(str(row[0]) for row in local_rows)
            )
            return [
                ("V134_P0_P30_P91_ISOLATED_INITIAL_READY",
                 npc_pc, npc_frame, 0.0),
                ("V134_P0_P30_P91_ISOLATED_REAPPLY_READY",
                 npc_pc, npc_frame, 3.00),
            ]

        def _sync_frozen_inventory_state(self) -> None:
            backpack = self.foundation.backpack
            if backpack is None:
                return
            item1 = next(item for item in backpack.items if item.identity == 1)
            source = next(
                (item for item in backpack.items if item.identity == 3), None,
            )
            self.item_slot = item1.slot
            self.item_quantity = item1.quantity
            self.stack_source_present = source is not None
            self.stack_source_slot = (
                legacy.V111_STACK_SOURCE_SLOT if source is None else source.slot
            )

        def _dispatch_v111_persistent_merge(self, parsed):
            self.rx_frames += 1
            if not is_exact_merge_request(legacy, parsed):
                self.events.append(
                    "foundation_v111_merge_candidate_wrong_envelope_no_reply"
                )
                return []
            if (
                self.foundation.selected is None
                or not self.teleport_sent
                or not self.runtime_ack_sent
            ):
                self.events.append(
                    "foundation_v111_merge_wrong_sequence_no_reply"
                )
                return []
            # Build the frozen exact response before opening the persistence
            # transaction. No successful bytes are queued unless the later
            # repository call commits the allowlisted post-state.
            pc, frame = legacy.make_item_operate_stack_merge_success()
            before = self.foundation.backpack
            try:
                applied = self.foundation.merge_v111_stack()
            except Exception as exc:
                if self.foundation.backpack is not before:
                    raise RuntimeError(
                        "repository failure changed in-memory Backpack state"
                    ) from exc
                self.events.append(
                    f"foundation_v111_merge_repository_failure_no_reply_{exc!r}"
                )
                return []
            self._sync_frozen_inventory_state()
            if not applied:
                self.events.append("foundation_v111_merge_replay_no_reply")
                return []
            if self.foundation.backpack != MERGED_V111_BACKPACK:
                raise RuntimeError("committed V111 Backpack state mismatch")
            self.stack_merge_count += 1
            self.events.append(
                "foundation_v111_merge_committed_before_response"
            )
            return [(
                "FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED",
                pc, frame, 0.0,
            )]

        def _dispatch_item_move_capture(self, parsed):
            """Own every ItemOperateReq in capture mode and never reply."""
            self.rx_frames += 1
            classification = classify_item_move_attempt(legacy, parsed)
            if classification != "exact":
                self.events.append(
                    f"item_move_capture_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append("item_move_capture_no_selected_no_reply")
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append("item_move_capture_wrong_sequence_no_reply")
                return []
            if self.foundation.backpack != MERGED_V111_BACKPACK:
                self.events.append("item_move_capture_wrong_current_state_no_reply")
                return []
            if self.item_move_capture_count:
                self.events.append("item_move_capture_duplicate_exact_no_reply")
                return []

            # Capture metadata is connection-local.  Backpack, frozen item_slot,
            # repository state, and response queue remain untouched.  The
            # future response/reconnect composition is still Grade D.
            before = (
                self.foundation.backpack,
                self.item_slot,
                self.item_quantity,
                self.stack_source_present,
            )
            self.item_move_capture_count += 1
            self.item_move_capture_last_fields = ITEM_MOVE_CAPTURE_FIELDS
            self.events.append(
                "item_move_capture_exact_op4_slot2_id1_no_reply"
            )
            after = (
                self.foundation.backpack,
                self.item_slot,
                self.item_quantity,
                self.stack_source_present,
            )
            if after != before:
                raise RuntimeError("capture-only item state mutated")
            return []

        # PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
        def _dispatch_item_move_hypothesis(self, parsed):
            """Commit the one tracked free-slot composition before replying."""
            self.rx_frames += 1
            classification = classify_item_move_hypothesis_attempt(legacy, parsed)
            if classification == "wrong_tuple":
                # A well-formed strict parse that is not the tracked HYP-PF-008
                # request stays owned by this opt-in mode and is offered to the
                # generalized HYP-PF-010 free-slot lane, which fails closed.
                return self._dispatch_item_move_generalized(parsed)
            if classification != "exact":
                self.events.append(
                    f"item_move_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append("item_move_hypothesis_no_selected_no_reply")
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append("item_move_hypothesis_wrong_sequence_no_reply")
                return []
            if self.foundation.backpack == HYPOTHESIZED_V111_SLOT2_BACKPACK:
                self.events.append("item_move_hypothesis_replay_no_reply")
                return []
            if self.foundation.backpack != MERGED_V111_BACKPACK:
                self.events.append("item_move_hypothesis_wrong_current_state_no_reply")
                return []

            # Response bytes are fully built and hash-checked before the DB
            # transaction.  They are not returned unless the exact post-state
            # commits and the in-memory snapshot is updated afterward.
            pc, frame = make_hypothesized_move_response(legacy)
            before = self.foundation.backpack
            try:
                applied = self.foundation.move_hypothesized_v111_slot2()
            except Exception as exc:
                if self.foundation.backpack is not before:
                    raise RuntimeError(
                        "repository failure changed hypothesized in-memory state"
                    ) from exc
                self.events.append(
                    f"item_move_hypothesis_repository_failure_no_reply_{exc!r}"
                )
                return []
            self._sync_frozen_inventory_state()
            if not applied:
                self.events.append("item_move_hypothesis_replay_no_reply")
                return []
            if self.foundation.backpack != HYPOTHESIZED_V111_SLOT2_BACKPACK:
                raise RuntimeError("committed HYP-PF-008 Backpack state mismatch")
            self.item_move_hypothesis_count += 1
            self.events.append(
                "item_move_hypothesis_committed_before_composed_response"
            )
            return [(
                "HYP_PF_008_ITEM_MOVE_ID1_SLOT0_TO_FREE_SLOT2_COMMITTED",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-010 active
        def _dispatch_item_move_generalized(self, parsed):
            """Route one governed free-slot move behind the same opt-in only.

            The exact HYP-PF-008 request never reaches this lane.  Occupied,
            unknown, and out-of-range destinations fail closed with no reply
            and no write; the exact same-slot request is a silent no-op.  The
            caller has already counted the frame.
            """
            if not (
                parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
                and parsed.outer_version == 0
                and parsed.outer_mask == 0x02
                and parsed.vital_count == 1
                and parsed.nested_version == 0
            ):
                self.events.append(
                    "item_move_generalized_wrong_envelope_no_reply"
                )
                return []
            try:
                operation, destination_slot, item_identity = (
                    legacy.parse_item_operate_req(parsed)
                )
            except (ValueError, TypeError):
                self.events.append("item_move_generalized_unparsed_no_reply")
                return []
            if operation != ITEM_MOVE_CAPTURE_FIELDS[0]:
                self.events.append(
                    "item_move_generalized_wrong_operation_no_reply"
                )
                return []
            if self.foundation.selected is None or self.foundation.backpack is None:
                self.events.append(
                    "item_move_generalized_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "item_move_generalized_wrong_sequence_no_reply"
                )
                return []
            # The pure transition validates the governed contents and fails
            # closed before any bytes or writes exist.  The response is fully
            # composed before the persistence transaction, exactly like the
            # tracked HYP-PF-008 lane, and is only queued after the atomic
            # commit re-validates that same post-state.
            try:
                transition = move_known_item_to_free_slot(
                    self.foundation.backpack, item_identity, destination_slot,
                )
            except FileExistsError as exc:
                # Only the dedicated swap and merge profiles may own an
                # occupied destination; every other mode keeps the pinned
                # HYP-PF-010 fail-closed silence.  The two profiles are
                # mutually exclusive at the scenario allowlist.
                if item_merge_enabled:
                    return self._dispatch_item_merge_occupied(
                        item_identity, destination_slot,
                    )
                if item_swap_enabled:
                    return self._dispatch_item_swap_occupied(
                        item_identity, destination_slot,
                    )
                self.events.append(
                    "item_move_generalized_fail_closed_no_reply_"
                    f"{type(exc).__name__}"
                )
                return []
            except (KeyError, ValueError) as exc:
                self.events.append(
                    "item_move_generalized_fail_closed_no_reply_"
                    f"{type(exc).__name__}"
                )
                return []
            if transition is None:
                self.events.append(
                    "item_move_generalized_same_slot_noop_no_reply"
                )
                return []
            expected_backpack, moved = transition
            pc, frame = make_item_move_delta_response(legacy, moved)
            before = self.foundation.backpack
            try:
                applied = self.foundation.move_backpack_item_to_free_slot(
                    item_identity, destination_slot,
                )
            except Exception as exc:
                if self.foundation.backpack is not before:
                    raise RuntimeError(
                        "repository failure changed generalized in-memory state"
                    ) from exc
                self.events.append(
                    f"item_move_generalized_repository_failure_no_reply_{exc!r}"
                )
                return []
            self._sync_frozen_inventory_state()
            if not applied:
                self.events.append(
                    "item_move_generalized_same_slot_noop_no_reply"
                )
                return []
            if self.foundation.backpack != expected_backpack:
                raise RuntimeError(
                    "committed HYP-PF-010 Backpack state mismatch"
                )
            self.item_move_generalized_count += 1
            self.events.append(
                "item_move_generalized_committed_before_composed_response"
            )
            return [(
                f"HYP_PF_010_ITEM_MOVE_ID{item_identity}"
                f"_TO_FREE_SLOT{destination_slot}_COMMITTED",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
        def _dispatch_item_swap_occupied(self, item_identity, destination_slot):
            """Commit one governed occupied-destination swap before replying.

            Reached only from the generalized lane's occupied branch under
            the dedicated swap profile: envelope, operation, selection,
            sequence, and occupancy are already established.  The pure
            transition re-validates everything, the two-item delta response
            is fully composed before the persistence transaction, and the
            response is queued only after the atomic commit re-validates the
            swapped post-state.  Any raise keeps fail-closed silence with no
            write.
            """
            try:
                transition = swap_known_item_with_occupied_slot(
                    self.foundation.backpack, item_identity, destination_slot,
                )
            except (LookupError, ValueError) as exc:
                self.events.append(
                    "item_swap_occupied_fail_closed_no_reply_"
                    f"{type(exc).__name__}"
                )
                return []
            expected_backpack, moved, displaced = transition
            pc, frame = make_item_swap_delta_response(legacy, moved, displaced)
            before = self.foundation.backpack
            try:
                applied = self.foundation.swap_backpack_item_with_occupied_slot(
                    item_identity, destination_slot,
                )
            except Exception as exc:
                if self.foundation.backpack is not before:
                    raise RuntimeError(
                        "repository failure changed swap in-memory state"
                    ) from exc
                self.events.append(
                    f"item_swap_occupied_repository_failure_no_reply_{exc!r}"
                )
                return []
            self._sync_frozen_inventory_state()
            if not applied:
                self.events.append("item_swap_occupied_not_applied_no_reply")
                return []
            if self.foundation.backpack != expected_backpack:
                raise RuntimeError(
                    "committed HYP-PF-017 Backpack state mismatch"
                )
            self.item_swap_occupied_count += 1
            self.events.append(
                "item_swap_occupied_committed_before_composed_response"
            )
            return [(
                f"HYP_PF_017_ITEM_SWAP_ID{item_identity}"
                f"_TO_SLOT{destination_slot}"
                f"_DISPLACING_ID{displaced.identity}"
                f"_TO_SLOT{displaced.slot}_COMMITTED",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-018 active
        def _dispatch_item_merge_occupied(self, item_identity, destination_slot):
            """Commit one governed same-template merge before replying.

            Reached only from the generalized lane's occupied branch under
            the dedicated merge profile: envelope, operation, selection,
            sequence, and occupancy are already established.  The pure
            transition re-validates everything (same template, identical
            variant bytes, governed post-state), the merge delta response --
            byte-identical in structure to the live-accepted V111 stack-merge
            response -- is fully composed before the persistence transaction,
            and the response is queued only after the atomic commit
            re-validates the merged post-state.  Different templates, the
            reversed direction outside the governed allowlist, and any other
            raise keep fail-closed silence with no write.
            """
            try:
                transition = merge_known_item_into_occupied_slot(
                    self.foundation.backpack, item_identity, destination_slot,
                )
            except (LookupError, ValueError) as exc:
                self.events.append(
                    "item_merge_occupied_fail_closed_no_reply_"
                    f"{type(exc).__name__}"
                )
                return []
            expected_backpack, merged, consumed = transition
            pc, frame = make_item_merge_delta_response(
                legacy, merged, consumed.identity,
            )
            before = self.foundation.backpack
            try:
                applied = self.foundation.merge_backpack_item_into_occupied_slot(
                    item_identity, destination_slot,
                )
            except Exception as exc:
                if self.foundation.backpack is not before:
                    raise RuntimeError(
                        "repository failure changed merge in-memory state"
                    ) from exc
                self.events.append(
                    f"item_merge_occupied_repository_failure_no_reply_{exc!r}"
                )
                return []
            self._sync_frozen_inventory_state()
            if not applied:
                self.events.append("item_merge_occupied_not_applied_no_reply")
                return []
            if self.foundation.backpack != expected_backpack:
                raise RuntimeError(
                    "committed HYP-PF-018 Backpack state mismatch"
                )
            self.item_merge_occupied_count += 1
            self.events.append(
                "item_merge_occupied_committed_before_composed_response"
            )
            return [(
                f"HYP_PF_018_ITEM_MERGE_ID{item_identity}"
                f"_INTO_ID{merged.identity}"
                f"_AT_SLOT{destination_slot}"
                f"_QTY{merged.quantity}_COMMITTED",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-012 active
        def _dispatch_logout_hypothesis(self, parsed):
            """Acknowledge one exact captured logout after a clean close.

            The session lease (``closed_at``) is committed before any ack
            byte is queued, mirroring the commit-before-response ordering of
            every other governed lane.  Wrong payloads, wrong sequences, and
            replays after the acknowledged logout fail closed with no reply
            and no write.
            """
            self.rx_frames += 1
            classification = classify_logout_attempt(legacy, parsed)
            if classification not in ("exact_01", "exact_03"):
                self.events.append(
                    f"logout_hypothesis_{classification}_no_reply"
                )
                return []
            subcode = int(classification[-2:])
            if self.foundation.selected is None:
                self.events.append("logout_hypothesis_no_selected_no_reply")
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append("logout_hypothesis_wrong_sequence_no_reply")
                return []
            # PF-HYPOTHESIS-LEDGER: HYP-PF-013 active
            # The close_socket shape is ack + delayed server-initiated clean
            # socket close.  If the transport lever is not attached the shape
            # cannot be fulfilled, so the whole lane fails closed before the
            # lease is touched: no write, no ack, no partial shape.
            close_socket_after_ack = (
                logout_hypothesis_scenario.post_ack_action
                == LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET
            )
            if close_socket_after_ack and self.transport_socket_closer is None:
                self.events.append(
                    "logout_hypothesis_close_unavailable_no_reply"
                )
                return []
            # HYP-PF-016: the response-first shape can only be fulfilled by
            # echoing a full GetWorldInfoVital payload this connection itself
            # produced.  Without one stored, no response byte exists without
            # invention, so the whole lane fails closed before the lease is
            # touched: no write, no response, no bare ack fallback (falling
            # back to ack-only would silently re-run the GT-007/GT-008
            # falsified shapes and contaminate the attended evidence).
            worldinfo_first = (
                logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST
            )
            if worldinfo_first and self.worldinfo_last_payload is None:
                self.events.append(
                    "logout_hypothesis_worldinfo_missing_no_reply"
                )
                return []
            # PF-HYPOTHESIS-LEDGER: HYP-PF-028 retired
            # The return_select_first shape composes one well-formed
            # ReturnSelectServerVital (0x709E) from the client serializer's own
            # field layout with all fields zero.  Unlike worldinfo_first it has
            # no per-connection precondition -- the body is a fixed template, so
            # no session ever fails closed for a "missing" payload here -- but
            # like every other shape the bytes are composed and pinned before
            # the lease is touched and nothing is queued unless the close
            # commits.  Static (agent D) proved this is the named-candidate the
            # attended A/B (GT-033) must decide; the server invents no content.
            return_select_first = (
                logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST
            )
            # RE-189 Job 2, branch 3 (CORE-REQUEST, see the
            # LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER constant comment in
            # logout_hypothesis.py for the full provenance).  This is the
            # exact reverse wire order of ``return_select_first`` above: the
            # pinned ack goes out first, then the pinned 0x709E response --
            # same two composers, same pins, no new byte.  No profile in
            # ``require_logout_hypothesis_scenario``'s allowlist can carry
            # this value yet, so this branch is provably unreachable from
            # any default boot; lane A wires the allowlisted profile and
            # scenario file in a later round, the same two-step pattern
            # HYP-PF-040 used.
            ack_first_reorder = (
                logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER
            )
            # The designed responses are fully composed and pinned before
            # the lease is touched; no bytes are queued unless the clean
            # close commits.
            worldinfo_response = None
            if worldinfo_first:
                worldinfo_response = make_worldinfo_first_response(
                    legacy, self.worldinfo_last_payload,
                )
            return_select_response = None
            if return_select_first or ack_first_reorder:
                return_select_response = make_return_select_server_response(
                    legacy,
                )
            pc, frame = make_logout_ack_response(legacy, subcode)
            try:
                closed = self.foundation.close_connection()
            except Exception as exc:
                self.events.append(
                    f"logout_hypothesis_repository_failure_no_reply_{exc!r}"
                )
                return []
            if not closed:
                self.events.append("logout_hypothesis_already_closed_no_reply")
                return []
            self.logout_acknowledged = True
            self.logout_ack_count += 1
            self.events.append(
                f"logout_hypothesis_subcode{subcode:02d}"
                "_session_closed_before_ack"
            )
            if close_socket_after_ack:
                # The ack action below is queued with zero delay and the
                # frozen listener sends it immediately after this dispatch
                # returns; the close timer starts now, so the close_delay_ms
                # budget (250 ms) covers the send and puts FIN strictly after
                # the ack bytes on the wire.  The wire ordering itself is the
                # falsifiable claim of the headless probe.
                delay_ms = logout_hypothesis_scenario.close_delay_ms
                close_timer_factory(
                    delay_ms / 1000.0, self.transport_socket_closer,
                )
                self.logout_close_scheduled = True
                self.events.append(
                    "logout_hypothesis_post_ack_socket_close_scheduled_"
                    f"{delay_ms}ms"
                )
                if worldinfo_first:
                    # Response first, pinned ack second, FIN last: the frozen
                    # listener sends queued actions strictly in list order on
                    # the one TCP stream, so the wire order is deterministic.
                    self.events.append(
                        f"logout_hypothesis_subcode{subcode:02d}"
                        "_worldinfo_response_before_ack"
                    )
                    info_pc, info_frame = worldinfo_response
                    return [
                        (
                            f"HYP_PF_016_LOGOUT_SUBCODE{subcode:02d}"
                            "_WORLDINFO_RESPONSE_FIRST",
                            info_pc, info_frame, 0.0,
                        ),
                        (
                            f"HYP_PF_016_LOGOUT_SUBCODE{subcode:02d}"
                            "_ACK_THEN_SERVER_SOCKET_CLOSE",
                            pc, frame, 0.0,
                        ),
                    ]
                # HYP-PF-028 emit (the ledger annotation for this id lives once
                # on the compose branch above).
                if return_select_first:
                    # ReturnSelectServerVital first, pinned ack second, FIN
                    # last: same deterministic in-order send on the one TCP
                    # stream.  This is the GT-033 variant B frame -- the named
                    # char-select candidate -- delivered so an attended run can
                    # observe whether the real client transitions on it.
                    self.events.append(
                        f"logout_hypothesis_subcode{subcode:02d}"
                        "_return_select_response_before_ack"
                    )
                    rss_pc, rss_frame = return_select_response
                    return [
                        (
                            f"HYP_PF_028_LOGOUT_SUBCODE{subcode:02d}"
                            "_RETURN_SELECT_SERVER_RESPONSE_FIRST",
                            rss_pc, rss_frame, 0.0,
                        ),
                        (
                            f"HYP_PF_028_LOGOUT_SUBCODE{subcode:02d}"
                            "_ACK_THEN_SERVER_SOCKET_CLOSE",
                            pc, frame, 0.0,
                        ),
                    ]
                # RE-189 Job 2, branch 3: the exact reverse wire order of
                # the return_select_first branch above -- same two pinned
                # composers, same pins, only the send order and which frame
                # goes first are swapped.  See the
                # LOGOUT_RESPONSE_POLICY_ACK_FIRST_REORDER constant comment
                # in logout_hypothesis.py for the full CORE-REQUEST
                # provenance.  Unreachable from any default boot until a
                # future round adds an allowlisted profile carrying this
                # response_policy value.
                if ack_first_reorder:
                    self.events.append(
                        f"logout_hypothesis_subcode{subcode:02d}"
                        "_ack_before_return_select_response"
                    )
                    rss_pc, rss_frame = return_select_response
                    return [
                        (
                            f"RE_189_BRANCH3_LOGOUT_SUBCODE{subcode:02d}"
                            "_ACK_FIRST",
                            pc, frame, 0.0,
                        ),
                        (
                            f"RE_189_BRANCH3_LOGOUT_SUBCODE{subcode:02d}"
                            "_RETURN_SELECT_SERVER_RESPONSE_THEN_SERVER_"
                            "SOCKET_CLOSE",
                            rss_pc, rss_frame, 0.0,
                        ),
                    ]
                return [(
                    f"HYP_PF_013_LOGOUT_SUBCODE{subcode:02d}"
                    "_ACK_THEN_SERVER_SOCKET_CLOSE",
                    pc, frame, 0.0,
                )]
            return [(
                f"HYP_PF_012_LOGOUT_SUBCODE{subcode:02d}"
                "_ACK_AFTER_CLEAN_CLOSE",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-016 active
        def _dispatch_worldinfo_observation(self, parsed):
            """Store the last exact full GetWorldInfoVital payload; no reply.

            Only the worldinfo_first scenario routes 0x3D4B here.  The full
            R40 248-byte form from a runtime-ready session is kept in
            connection-local memory (no table, no write path) so the logout
            lane can echo the client's own bytes back; the observed server
            behavior at dialog-open time (no response) is preserved.  The
            empty 2-byte form, malformed forms, and frames outside the
            runtime-ready sequence are never stored and never answered.
            """
            self.rx_frames += 1
            classification = classify_worldinfo_frame(legacy, parsed)
            if classification != "full_form":
                self.events.append(
                    f"logout_worldinfo_{classification}_no_store_no_reply"
                )
                return []
            if (
                self.foundation.selected is None
                or not self.teleport_sent
                or not self.runtime_ack_sent
            ):
                self.events.append(
                    "logout_worldinfo_wrong_sequence_no_store_no_reply"
                )
                return []
            self.worldinfo_last_payload = parsed.nested_payload
            self.worldinfo_stored_count += 1
            self.events.append("logout_worldinfo_full_form_stored_no_reply")
            return []

        # PF-HYPOTHESIS-LEDGER: HYP-PF-031 active
        # LOGOUT-CHAT-PUSH-001.  Registered in docs/HYPOTHESIS_LEDGER.json;
        # this annotation and that entry's source_refs bind each other both
        # ways.
        def _dispatch_logout_chat_push_hypothesis(self, parsed):
            """Push the pinned ReturnSelectServerVital on one chat trigger.

            THE BLOCKER THIS LANE EXISTS FOR.  GT-033 (attended) is stuck at
            the trigger, not at the response: the tester cannot click the
            client's HOME menu item, so the client never sends LogoutVital
            0x1B40, and both existing logout response-policy shapes -- the
            PF-013 ack+close and the PF-028 return-select-first -- REPLY to
            that request and therefore can never fire in the attended
            session.  What the tester CAN do reliably is type into chat
            (Return focuses the chat box), and the chat-input trigger path
            is already proven end to end by HYP-PF-027, which answers one
            accepted ascii12 chat-input frame with a composed spawn frame.

            THE QUESTION.  HYP-PF-028's frozen ReturnSelectServerVital
            (0x709E) response has never been delivered to a client because
            its request pairing never happens.  This lane decouples the two:
            one accepted 34-byte ascii12 chat-input frame makes the server
            push the byte-identical hash-pinned PF-028 response UNSOLICITED
            -- no LogoutVital request, no ack, no close -- exactly once, so
            an attended run can observe whether the response ALONE causes
            the client screen transition.  A negative is valuable too: it
            would say 0x709E does not transition the client even without
            request pairing, strengthening the reading that the operative
            lever is a connection teardown, not a response vital.

            NOTHING NEW GOES ON THE WIRE.  The pushed bytes are composed by
            the unchanged HYP-PF-028 composer, which refuses on any drift
            from the pinned 38-byte PC / 48-byte frame sha256 before a byte
            can be queued; a compose refusal here is a named no-reply event.
            Nothing in the chat request is read (the request is a trigger,
            not an input), no store call exists on this path, no session
            lease is touched, and no socket action is taken.

            ONE-SHOT: the value of an unsolicited push is that one frame
            maps to one on-screen observation; a second push would turn a
            legible A/B into noise.  A repeat trigger is refused with a
            named event and no bytes.

            The lane composes nothing at all when the scenario is absent,
            and a LogoutVital under this scenario is deliberately NOT
            answered (see the routing branch below): the session asks
            exactly one question.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"logout_chat_push_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "logout_chat_push_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "logout_chat_push_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.logout_chat_push_count:
                self.events.append(
                    "logout_chat_push_hypothesis_already_sent_no_reply"
                )
                return []
            # The composer independently re-pins the 0x709E PC/frame sha256
            # against the frozen HYP-PF-028 constants and raises on any
            # drift, so no unpinned byte can reach the queue on this path.
            try:
                pc, frame = make_return_select_server_response(legacy)
            except (ValueError, RuntimeError) as exc:
                self.events.append(
                    "logout_chat_push_hypothesis_compose_refused_no_reply_"
                    f"{exc!r}"
                )
                return []
            self.logout_chat_push_count += 1
            self.events.append(
                "logout_chat_push_hypothesis_return_select_pushed"
            )
            return [(
                "HYP_PF_031_LOGOUT_CHAT_PUSH_RETURN_SELECT_SERVER_UNSOLICITED",
                pc, frame, 0.0,
            )]

        def _dispatch_logout_chat_push_logout_no_reply(self, parsed):
            """Deliberately leave a LogoutVital unanswered under HYP-PF-031.

            The chat-push scenario asks ONE question -- does the unsolicited
            0x709E response transition the client -- and answering a later
            LogoutVital with any of the request-paired shapes (PF-012 ack,
            PF-013 close, PF-016/PF-028 response-first) would contaminate
            the attended evidence with a second stimulus.  So the frame is
            counted and refused by name: no reply, no write, no close, and
            the pre-existing logout profiles keep their own behavior only
            under their own scenario files.
            """
            self.rx_frames += 1
            self.events.append(
                "logout_chat_push_hypothesis_logout_vital_no_reply"
            )
            return []

        # PF-HYPOTHESIS-LEDGER: HYP-PF-014 active
        def _dispatch_chat_input_hypothesis(self, parsed):
            """Echo one exact-shape chat input frame (UNKNOWN_0xAC52) back.

            The designed echo is composed and pinned before it is queued; the
            lane never touches the store (chat has no table), never closes
            the socket, and never becomes one-shot: every accepted frame on
            the session is echoed.  Wrong shapes, wrong envelopes, and wrong
            sequences fail closed with no reply and no write.  Under the
            CHAT-ECHO-002 speaker scenario the same accepted frame is instead
            answered with the speaker-name wstring composition; the request
            classification and every guard above stay identical.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"chat_input_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append("chat_input_hypothesis_no_selected_no_reply")
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "chat_input_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if (
                chat_input_hypothesis_scenario.scenario_id
                == CHAT_INPUT_SPEAKER_ECHO_SCENARIO_ID
            ):
                # CHAT-ECHO-002 (HYP-PF-014 version 2): wstring#1 is filled
                # with the selected character's canonical name; everything
                # from the second wstring header on is echoed byte-exactly
                # (68B PC / 79B frame for the pinned probe forms).  The
                # payload re-passed the exact classification above, so the
                # only ValueError left is a name the fixed-size composition
                # cannot carry -- fail closed with no reply and no write.
                try:
                    pc, frame = make_chat_input_speaker_echo_response(
                        legacy, parsed.nested_payload,
                        self.foundation.selected.name,
                    )
                except ValueError:
                    self.events.append(
                        "chat_input_hypothesis_speaker_name_unavailable_no_reply"
                    )
                    return []
                self.chat_input_echo_count += 1
                self.events.append(
                    "chat_input_hypothesis_speaker_echo_ack_ascii12"
                )
                return [(
                    "HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_ASCII12",
                    pc, frame, 0.0,
                )]
            # The echo is fully composed and structurally pinned (56B PC /
            # 66B frame, payload byte-exact at the fixed envelope offset;
            # both GT-006 probes are additionally hash-pinned) before any
            # byte is queued.  No repository call exists on this path.
            pc, frame = make_chat_input_echo_response(
                legacy, parsed.nested_payload,
            )
            self.chat_input_echo_count += 1
            self.events.append("chat_input_hypothesis_echo_ack_ascii12")
            return [(
                "HYP_PF_014_CHAT_INPUT_ECHO_ASCII12",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-019 active
        def _dispatch_channel_message_hypothesis(self, parsed):
            """Sweep one accepted chat input frame across the five channels.

            CHAT-CHANNEL-003.  The request side is the SAME accepted shape the
            HYP-PF-014 echo lane classifies (exact 34-byte ascii12 0xAC52
            frame) and every guard is the same: wrong shape, wrong envelope, no
            selected character, and not-yet-runtime-ready all fail closed with
            no reply and no write.  What changes is the answer: the payload is
            *decoded* into (speaker, body) rather than spliced, and the decoded
            body is re-composed once per shared-serializer channel, in the
            scenario's order, with an EMPTY speaker so all five nested payloads
            are byte-identical and the 16-bit class id is the only difference
            on the wire.  Every frame is composed and pinned before any of them
            is queued.  The lane touches no store (chat has no table), takes no
            socket action, and is not one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"channel_message_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "channel_message_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "channel_message_hypothesis_wrong_sequence_no_reply"
                )
                return []
            try:
                # Decoded, not spliced: the body that goes back out is the one
                # the 0x65AD40 schema says is in the request.  Today every
                # ascii12 payload decodes by construction, so this is a
                # structural backstop rather than a live branch -- it exists so
                # that widening the accepted request shape can never leak an
                # undecodable payload onto the wire.
                _speaker, body = decode_channel_message_payload(
                    parsed.nested_payload
                )
            except ValueError:
                self.events.append(
                    "channel_message_hypothesis_undecodable_payload_no_reply"
                )
                return []
            actions = []
            for index, name in enumerate(
                channel_message_hypothesis_scenario.channel_order
            ):
                pc, frame = make_channel_message_response(
                    legacy, SHARED_SERIALIZER_CHANNEL_IDS[name],
                    CHANNEL_SWEEP_SPEAKER, body,
                )
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    CHANNEL_SWEEP_FIRST_DELAY_SECONDS if index == 0
                    else channel_message_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    CHANNEL_SWEEP_ACTION_LABEL_PREFIX + channel_short_name(name),
                    pc, frame, delay,
                ))
            self.channel_message_sweep_count += 1
            self.events.append(
                "channel_message_hypothesis_channel_sweep_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-020 active
        def _dispatch_stats_progression_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the progression sweep.

            STATS-PROG-002.  The request side is deliberately the SAME accepted
            shape the HYP-PF-014 echo lane classifies (exact 34-byte ascii12
            frame): it is the only client action an attended tester can trigger
            on demand, and reusing it means every guard here is one the project
            has already proven -- wrong shape, wrong envelope, no selected
            character and not-yet-runtime-ready all fail closed with no reply
            and no write.  Nothing in the request is read: the request is a
            trigger, not an input, and the answer is composed entirely from the
            selected character plus the scenario's pinned step plan.

            The answer is one UpdateAttrVital frame per step, in the scenario's
            order, spaced by ``spacing_seconds`` so an attended reader can
            attribute one on-screen change to one frame.  Each frame carries the
            cumulative field set: the exact baseline ActorAttr projection
            player_wire already puts on the wire at start-game, plus every
            progression change up to that step.  That is not decoration -- v141's
            note on the client's ActorAttr apply 0x464F30 says the incoming
            object is copied whole, so a field dropped from a later frame would
            be undone rather than left alone.  Every frame is composed, re-decoded
            and pinned before any of them is queued.  The lane touches no store
            (progression has no table), takes no socket action, and is not
            one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"stats_progression_hypothesis_{classification}_no_reply"
                )
                return []
            selected = self.foundation.selected
            if selected is None:
                self.events.append(
                    "stats_progression_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "stats_progression_hypothesis_wrong_sequence_no_reply"
                )
                return []
            position = selected.position
            actor = StatsProgressionActor(
                selected.identity_lo, selected.identity_hi,
                position.scene_id, position.scene_seq, selected.name,
            )
            actions = []
            for index, label in enumerate(
                stats_progression_hypothesis_scenario.step_order
            ):
                pc, frame = make_stats_progression_step_response(
                    legacy, actor, index,
                )
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    STATS_PROGRESSION_FIRST_DELAY_SECONDS if index == 0
                    else stats_progression_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    STATS_PROGRESSION_ACTION_LABEL_PREFIX + label,
                    pc, frame, delay,
                ))
            self.stats_progression_sweep_count += 1
            self.events.append(
                "stats_progression_hypothesis_xp_sweep_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-033 active
        def _dispatch_learn_skill_result_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the 0x673C sweep.

            LEARN-SKILL-RESULT-001.  The request side is deliberately the
            SAME accepted shape the HYP-PF-014 echo lane classifies (exact
            34-byte ascii12 frame): it is the only client action an attended
            tester can trigger on demand, and reusing it means every guard
            here is one the project has already proven -- wrong shape, wrong
            envelope, no selected character and not-yet-runtime-ready all
            fail closed with no reply and no write.  Nothing in the request
            is read: the request is a trigger, not an input, and the answer
            is composed entirely from the module's own frozen step plan.

            The answer is one 0x673C vital frame per step, in the scenario's
            order, spaced by ``spacing_seconds`` so an attended reader can
            attribute one on-screen effect (if any ever appears) to one
            frame: the count=0 edge with trailing 0, count=1 with trailing
            0, the same count=1 body with only the trailing byte moved to 1,
            and the count=3 multi-record body with varied opaque values
            under trailing 0 and again under trailing 1.  The body
            shape is the GT-050-proven one; the record SEMANTICS are unknown
            and unnamed, and the values are this project's own design.
            Every frame is composed, re-decoded and hash-pinned before any
            of them is queued.  The lane touches no store (learned skills
            have no table), takes no socket action, and is not one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"learn_skill_result_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "learn_skill_result_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "learn_skill_result_hypothesis_wrong_sequence_no_reply"
                )
                return []
            actions = []
            for index, label in enumerate(
                learn_skill_result_hypothesis_scenario.step_order
            ):
                pc, frame = make_learn_skill_result_step_response(
                    legacy, index,
                )
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS if index == 0
                    else learn_skill_result_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX + label,
                    pc, frame, delay,
                ))
            self.learn_skill_result_sweep_count += 1
            self.events.append(
                "learn_skill_result_hypothesis_learn_sweep_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-034 active
        def _dispatch_learn_skill_request_hypothesis(self, parsed):
            """Strictly decode one inbound 0x36AA request; reply with nothing.

            LEARN-SKILL-REQUEST-001.  The lane is deliberately decode-only:
            an accepted request is decoded to the two opaque declared values
            (named by object offset only -- no semantics are known), counted
            and recorded on the session state, and NOTHING is sent back --
            no learn rule exists and none is invented, and the sibling
            result-vital composer is never called from here.  Every refusal
            -- wrong envelope, truncation, a wrong tag, trailing bytes --
            is a named no-reply event.  The guards mirror the sibling sweep
            lane: no selected character and not-yet-runtime-ready both fail
            closed with no reply and no write.  No path here touches the
            database.
            """
            self.rx_frames += 1
            classification = classify_learn_skill_request_attempt(
                legacy, parsed,
            )
            if classification != "exact_request":
                self.events.append(
                    f"learn_skill_request_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "learn_skill_request_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "learn_skill_request_hypothesis_wrong_sequence_no_reply"
                )
                return []
            fields = decode_learn_skill_request_payload(
                bytes(parsed.nested_payload)
            )
            self.learn_skill_request_last_fields = (
                fields.request_u32_0x14, fields.request_u8_0x18,
            )
            self.learn_skill_request_accepted_count += 1
            self.events.append(
                "learn_skill_request_hypothesis_decoded_no_reply"
            )
            return []

        # PF-HYPOTHESIS-LEDGER: HYP-PF-036 active
        def _dispatch_pickup_listener_hypothesis(self, parsed):
            """Strictly decode one inbound 0x4543 pickup frame; reply nothing.

            PICKUP-LISTENER-001.  The lane is deliberately decode-count-and-
            record only: an accepted frame is decoded to the two declared
            values (object_ref_u32, proven by GT-046 job 5 to be copied from
            the selected live runtime drop-object, NOT claimed to be an
            element_key; opaque_u8, meaning unknown, never interpreted),
            counted, appended to the in-memory record list with its raw body
            hex, and logged as ONE ASCII event line -- and NOTHING is sent
            back: no pickup rule exists and none is invented.  Every byte
            mismatch is a named refusal drawn from the module's frozen
            rejection registry, recorded on the refusal list with its raw
            body hex, no-reply, no-crash.  The guards mirror the HYP-PF-034
            template lane: no selected character and not-yet-runtime-ready
            both fail closed with no reply and no write.  No path here
            touches the database.

            THE OPCODE 0x4543 IS DERIVED (name-hash; runtime id slot
            0x0108202C is zero on disk) AND HAS NEVER BEEN OBSERVED ON ANY
            WIRE; if the real id differs this branch never fires and the
            frame keeps the frozen fall-through behavior recorded in the
            module docstring.
            """
            self.rx_frames += 1
            classification = classify_pickup_listener_attempt(
                legacy, parsed,
            )
            if classification != "exact_pickup":
                body = parsed.nested_payload
                body_hex = (
                    bytes(body).hex().upper()
                    if type(body) in (bytes, bytearray) else ""
                )
                self.pickup_listener_refusals.append(
                    (classification, body_hex)
                )
                self.events.append(
                    f"pickup_listener_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "pickup_listener_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "pickup_listener_hypothesis_wrong_sequence_no_reply"
                )
                return []
            body = bytes(parsed.nested_payload)
            fields = decode_pickup_listener_payload(body)
            self.pickup_listener_last_fields = (
                fields.object_ref_u32, fields.opaque_u8,
            )
            self.pickup_listener_accepted_count += 1
            body_hex = body.hex().upper()
            self.pickup_listener_records.append((
                self.pickup_listener_accepted_count,
                fields.object_ref_u32,
                fields.opaque_u8,
                body_hex,
            ))
            self.events.append(
                "pickup_listener_hypothesis_decoded_no_reply_"
                f"count{self.pickup_listener_accepted_count}_"
                f"object_ref_0x{fields.object_ref_u32:08X}_"
                f"opaque_u8_0x{fields.opaque_u8:02X}_"
                f"payload_{body_hex}"
            )
            return []

        # PF-HYPOTHESIS-LEDGER: HYP-PF-035 active
        def _dispatch_skill_attr_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the attr-block sweep.

            SKILL-ATTR-001.  The request side is deliberately the SAME
            accepted shape the HYP-PF-014 echo lane classifies (exact
            34-byte ascii12 frame): it is the only client action an attended
            tester can trigger on demand, and reusing it means every guard
            here is one the project has already proven -- wrong shape, wrong
            envelope, no selected character and not-yet-runtime-ready all
            fail closed with no reply and no write.  Nothing in the request
            is read: the request is a trigger, not an input, and the answer
            is composed entirely from the module's own frozen step plan.

            IDENTITY IS PINNED, the HYP-PF-026 lesson: the sweep frames are
            hash-pinned absolutely, and the pinned attr body carries the
            canonical smoke identity in its DBAttribute chain, so the lane
            refuses to fire at all unless the selected actor IS that
            identity -- a tester sees the pinned bytes byte for byte or
            nothing, and no frame ever names an identity the session does
            not hold.

            The answer is one UpdateAttrVital 0x309A frame per step, in the
            scenario's order, spaced by ``spacing_seconds``: the empty
            record set (count 0), then one arbitrary probe record (key=1,
            both opaque fields 0 -- NOT claimed meaningful).  Whether either
            frame changes what the K key does is exactly the attended
            question this lane exists to unblock; RE-061's nonclaim stands
            that one packet is NOT proven sufficient.  Every frame is
            composed, re-decoded and hash-pinned before any of them is
            queued.  The lane touches no store (skill state has no table),
            takes no socket action, and is not one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"skill_attr_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "skill_attr_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "skill_attr_hypothesis_wrong_sequence_no_reply"
                )
                return []
            selected = self.foundation.selected
            identity_lo = getattr(selected, "identity_lo", None)
            identity_hi = getattr(selected, "identity_hi", None)
            if (
                identity_lo != SKILL_ATTR_PROBE_IDENTITY_LO
                or identity_hi != SKILL_ATTR_PROBE_IDENTITY_HI
            ):
                self.events.append(
                    "skill_attr_hypothesis_identity_not_pinned_no_reply"
                )
                return []
            actions = []
            for index, label in enumerate(
                skill_attr_hypothesis_scenario.step_order
            ):
                pc, frame = make_skill_attr_step_response(legacy, index)
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    SKILL_ATTR_FIRST_DELAY_SECONDS if index == 0
                    else skill_attr_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    SKILL_ATTR_ACTION_LABEL_PREFIX + label,
                    pc, frame, delay,
                ))
            self.skill_attr_sweep_count += 1
            self.events.append(
                "skill_attr_hypothesis_attr_sweep_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-037 active
        def _dispatch_item_operate_res_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the greenline sweep.

            ITEMOP-RES-GREENLINE-001.  The request side is deliberately the
            SAME accepted shape the HYP-PF-014 echo lane classifies (exact
            34-byte ascii12 frame): it is the only client action an attended
            tester can trigger on demand, and reusing it means every guard
            here is one the project has already proven -- wrong shape, wrong
            envelope, no selected character and not-yet-runtime-ready all
            fail closed with no reply and no write.  Nothing in the request
            is read: the request is a trigger, not an input, and the answer
            is composed entirely from the module's own frozen step plan.

            IDENTITY IS PINNED, the HYP-PF-026 lesson: the sweep frames are
            hash-pinned absolutely, so the lane refuses to fire at all
            unless the selected actor IS the canonical smoke identity -- a
            tester sees the pinned bytes byte for byte or nothing.

            The answer is one ItemOperateVitalRes 0x4C13 frame per step, in
            the scenario's order, spaced by ``spacing_seconds``: the RE-059
            capture replay control, then the proven bag-update shape
            carrying the RE-060 consumable at quantity 1, then at quantity
            5.  WHAT THE SCREEN SHOWS for any of them is exactly the
            attended GT-063 question this lane exists to unblock; nothing
            here claims a green line appears.  Every frame is composed,
            re-decoded and hash-pinned before any of them is queued.  The
            lane touches no store, takes no socket action, and is not
            one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"item_operate_res_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "item_operate_res_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "item_operate_res_hypothesis_wrong_sequence_no_reply"
                )
                return []
            selected = self.foundation.selected
            identity_lo = getattr(selected, "identity_lo", None)
            identity_hi = getattr(selected, "identity_hi", None)
            if (
                identity_lo != ITEM_OPERATE_RES_PROBE_IDENTITY_LO
                or identity_hi != ITEM_OPERATE_RES_PROBE_IDENTITY_HI
            ):
                self.events.append(
                    "item_operate_res_hypothesis_identity_not_pinned_no_reply"
                )
                return []
            actions = []
            for index, label in enumerate(
                item_operate_res_hypothesis_scenario.step_order
            ):
                pc, frame = make_item_operate_res_step_response(legacy, index)
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    ITEM_OPERATE_RES_FIRST_DELAY_SECONDS if index == 0
                    else item_operate_res_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    ITEM_OPERATE_RES_ACTION_LABEL_PREFIX + label,
                    pc, frame, delay,
                ))
            self.item_operate_res_sweep_count += 1
            self.events.append(
                "item_operate_res_hypothesis_greenline_sweep_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-022 active
        def _dispatch_hp_death_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the death sweep.

            HP-DEATH-002.  This is the lane that can make a character appear to
            DIE, so read what it does before changing it.  HP-DEATH-001 proved
            byte-exactly that the client derives death by itself: ``IsDead``
            (CNetActor/CMyActor vtable +0x40 = 0x454AC0) requires the f32 at
            ``BasicAttr +0x58`` to be greater than the 0.0f at 0xF0989C and the
            u32 at ``BasicAttr +0x44`` to be zero.  Those are mask bits 0x0080
            and 0x0004 of the same block this server already emits.  There is no
            death frame to send and none is composed here; those two attribute
            values ARE the whole trigger for the local player's own
            ``Main_Dead`` window, which ``IsDead`` re-reads every frame -- but
            round 85 static RE (see
            ``reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md``)
            proved that sentence FALSE for engine death:
            ``UpdateAttrVital``'s inbound handler (0x5F2400) contains zero
            vtable +0x20 dispatch shapes across its whole extent, so this frame
            never reaches the dead-state chain (latch [actor+0x70] |= 0x200,
            spawn ``CActorTask_Dead``, play L"_F_DIE_000") -- see that report
            for the full census.

            The request side is deliberately the SAME accepted shape the
            HYP-PF-014 echo lane classifies, for the same reason the progression
            lane reuses it: it is the only client action an attended tester can
            trigger on demand, and every refusal guard is one this project has
            already proven.  Nothing in the request is read.

            The answer is the frame list of whichever step profile the scenario
            selected, and the two profiles differ in exactly one thing -- how
            they end:

              * ``death_sweep`` sends four frames: the untouched baseline
                projection, then the death timer armed while HP is still full
                (which must NOT kill -- it isolates "the client accepts bit
                0x0080" from "the client dies"), then the zeroed current HP that
                completes the predicate, then the frame that restores the HP
                value and puts it back.  Ending alive is a requirement of that
                profile, not a courtesy, and the composer refuses a
                ``death_sweep``-shaped plan whose last step is not the restoring
                one.
              * ``dying_hold`` sends three: baseline, timer armed at the 20.0 s
                the client image itself carries for DURATION_DYING, then the
                kill -- and stops there, deliberately, because the question that
                profile exists to ask is what happens once the countdown runs
                out, and a restoring frame is the one thing that would stop the
                answer from being observable.

            Frames are cumulative because BasicAttr's copy 0x464B40
            copies the whole block with no mask consulted, so a field dropped
            from a later frame is overwritten rather than left alone.

            The lane touches no store (HP has no write path in this project),
            takes no socket action, and is not one-shot.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"hp_death_hypothesis_{classification}_no_reply"
                )
                return []
            selected = self.foundation.selected
            if selected is None:
                self.events.append("hp_death_hypothesis_no_selected_no_reply")
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append("hp_death_hypothesis_wrong_sequence_no_reply")
                return []
            position = selected.position
            actor = StatsProgressionActor(
                selected.identity_lo, selected.identity_hi,
                position.scene_id, position.scene_seq, selected.name,
            )
            actions = []
            for index, label in enumerate(
                hp_death_hypothesis_scenario.step_order
            ):
                pc, frame = make_hp_death_step_response(
                    legacy, actor, index, hp_death_lethal, hp_death_profile,
                )
                # The frozen V141 sender accumulates these onto one deadline
                # (send_deadline += delay, then sleep to it), so this field is
                # the gap before each send: 0.0 for the first frame and the
                # full spacing for every later one.
                delay = (
                    hp_death_profile.first_delay_seconds if index == 0
                    else hp_death_hypothesis_scenario.spacing_seconds
                )
                actions.append((
                    hp_death_profile.action_label_prefix + label,
                    pc, frame, delay,
                ))
            self.hp_death_sweep_count += 1
            self.events.append("hp_death_hypothesis_death_sweep_sent")
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-023 active
        # RUNTIMERES-DISPATCH-001.  Registered by the round-86 ledger append;
        # this annotation and that entry's source_refs bind each other both ways.
        def _dispatch_runtimeres_death_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the spawn-then-kill sweep.

            This is the lane that aims at the ENGINE death chain, not at the
            local player's own ``Main_Dead`` window, so read what it does
            before changing it.  ``UpdateAttrVital`` -- the carrier
            ``_dispatch_hp_death_hypothesis`` above uses -- cannot reach that
            chain at all: its inbound handler 0x5F2400..0x5F261A contains zero
            ``mov r,[reg+0x20]; call r`` dispatch shapes over its whole extent.
            The carrier that does is ``GSCN_RunTimeProtocolRes`` id 0x6E9D
            with the DERIVED change mask bit 0x02 (the actor-entry collection
            at +0x1C), whose inbound handler 0x5E4060 hands the list head to
            0x446F30, which has exactly one direct caller in the image.

            The request side is deliberately the SAME accepted 34-byte ascii12
            shape the HYP-PF-014 echo lane classifies, for the same reason the
            other three sweeps reuse it: it is the only client action an
            attended tester can fire on demand, and every refusal guard is one
            this project has already proven.  Nothing in the request is read --
            it is a trigger, not an input.  The selected character is required
            for the entry sequence only; the actor that dies is an NPC probe
            resolved from the frozen placement source, not the player.

            The answer is the encoder's whole three-frame sweep for ONE
            identity, composed, re-read by an independent tag walker and
            hash-pinned by ``build_runtimeres_death_sweep`` before a single
            byte is returned:

              * SPAWN -- the probe alive (HP 100, no BasicAttr bit 0x0080) with
                a MovementAttr that places it.  An actor cannot be born dead:
                an identity the client does not know takes 0x446990 -> vtable
                +0x10 and never touches the dead-state sync 0x4437C0, so the
                sweep MUST introduce the identity alive first.
              * DYING_LATCH -- the same identity, HP 0, timer 20.0f > 0.  That
                is vtable +0x40 (0x43BDA0), which gates ``[actor+0x70] |=
                0x200`` at 0x44384C.
              * DEATH_TASK -- the same identity, HP 0, timer 0.0f <= 0.  That
                is vtable +0x3C (0x43BD70), which gates 0x443990 and therefore
                ``call 0x472810`` -> ``CActorTask_Dead`` -> ``L"_F_DIE_000"``.

            The polarity is inverted from intuition and the two predicates are
            mutually exclusive on any one snapshot, which is why both sides
            have to be sent, in that order.

            ONE-SHOT, and that is not a convenience: the scenario declares
            ``"one_shot": true`` because a second sweep would re-send SPAWN for
            an identity the client now knows, which takes the vtable +0x20
            update path instead of the spawn path and would silently resurrect
            the probe.  A repeat trigger is refused with a named event and no
            bytes.

            The lane touches no store (nothing on this path has a write path),
            takes no socket action, and composes nothing at all when the
            scenario is absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"runtimeres_death_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "runtimeres_death_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "runtimeres_death_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.runtimeres_death_sweep_count:
                self.events.append(
                    "runtimeres_death_hypothesis_already_sent_no_reply"
                )
                return []
            actions = build_runtimeres_death_sweep(
                legacy, runtimeres_death_probe, runtimeres_death_lethal,
                runtimeres_death_hypothesis_scenario,
            )
            self.runtimeres_death_sweep_count += 1
            # RUNTIMERES-LATCHONLY-001 (round 91): the event names the PROFILE
            # that was sent, because there are now two and a log line saying
            # only that "the sweep" went out cannot tell an attended tester
            # which experiment they just ran.  The three-frame profile is named
            # spawn_then_kill, so this composes the byte-identical string the
            # ledger, the replay tool and the dispatch tests already pin.
            event = (
                "runtimeres_death_hypothesis_"
                + runtimeres_death_hypothesis_scenario.profile_name
                + "_sent"
            )
            # The three-frame profile must keep composing EXACTLY the string the
            # ledger's source markers, the replay tool and the dispatch tests
            # already pin.  Written out here once and compared, so renaming a
            # profile is an immediate RuntimeError rather than a published event
            # name that quietly changed.
            if runtimeres_death_hypothesis_scenario.ends_on_death_task and (
                event != "runtimeres_death_hypothesis_spawn_then_kill_sent"
            ):
                raise RuntimeError("HYP-PF-023 sweep event name drift")
            self.events.append(event)
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-024 active
        # DAMAGE-DISPATCH-001.  Registered by the round-90 ledger append; this
        # annotation and that entry's source_refs bind each other both ways.
        def _dispatch_damage_model_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the hit sweep.

            This is the lane that puts a NUMBER on the screen, and the number
            is ours.  Round 83 proved the client computes nothing: it carries
            no damage formula, applies no scaling and never subtracts damage
            from hit points, so the figure a player sees is exactly the signed
            i32 the server placed at hit-entry +0x08, printed through abs().
            There is therefore nothing to recover and everything to design, and
            the owner approved designing it (2026-08-19) within one signed
            integer and one flag word per target.

            The request side is the same accepted 34-byte ascii12 shape the
            other three sweeps reuse, for the same reason: it is the one client
            action an attended tester can fire on demand and every refusal
            guard on it is already proven.  Nothing in the request is read.

            The answer is four frames.  Under the hit_sweep profile both sides
            are the player's own actor, the only identity this lane can be
            sure the client knows; under the npc_target profile (round 95,
            DAMAGE-NPC-TARGET-001) the performer stays the player and the hit
            entry's target is the fixed NPC placement identity 0x2001, spaced
            15 s for photography -- GT-027 tests whether that identity is in
            the client's map at all (a target it cannot find is skipped at
            0x7508AD / 0x750D27; a performer it cannot find is NOT, per
            0x7507C3):

              * HIT_WEAK       -63, flags 0x0001
              * HIT_STRONG    -379, flags 0x0001
              * MISS             0, flags 0x0000  -- the control frame
              * HIT_REACTION   -63, flags 0x0009

            MISS is the experiment's control and the encoder refuses a sweep
            without one: if every frame showed a number, a tester could not
            tell our bytes from something the client draws on its own.

            ONE-SHOT.  A repeat trigger is refused with a named event and no
            bytes, because the value of the two hit numbers is that a tester
            can predict them before they appear; a second sweep interleaved
            with the first turns a legible sequence into noise.

            The lane touches no store, takes no socket action, opens no write
            path to hit points, and composes nothing at all when the scenario
            is absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"damage_model_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "damage_model_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "damage_model_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.damage_model_sweep_count:
                self.events.append(
                    "damage_model_hypothesis_already_sent_no_reply"
                )
                return []
            actor = resolve_damage_model_actor(
                legacy, self.foundation.selected,
            )
            actions = build_damage_model_sweep(
                legacy, actor, damage_model_unlock,
                damage_model_hypothesis_scenario,
            )
            self.damage_model_sweep_count += 1
            # DAMAGE-NPC-TARGET-001 (round 95): the event names the PROFILE
            # that was sent, because there are now two and a log line saying
            # only that "the sweep" went out cannot tell an attended tester
            # which experiment they just ran.  The player-target profile must
            # keep composing EXACTLY the string the ledger's source markers,
            # the replay tool and the dispatch tests already pin, so both
            # strings are written out here once and compared: renaming a
            # profile is an immediate RuntimeError rather than a published
            # event name that quietly changed.
            npc_profile = (
                damage_model_hypothesis_scenario.scenario_id
                == DAMAGE_MODEL_NPC_SCENARIO_ID
            )
            event = (
                "damage_model_hypothesis_npc_sweep_sent"
                if npc_profile else
                "damage_model_hypothesis_hit_sweep_sent"
            )
            if not npc_profile and event != (
                "damage_model_hypothesis_hit_sweep_sent"
            ):
                raise RuntimeError("HYP-PF-024 sweep event name drift")
            self.events.append(event)
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-026 active
        # DAMAGE-HP-LINK-001.  Registered by the round-97 ledger append; this
        # annotation and that entry's source_refs bind each other both ways.
        def _dispatch_damage_hp_link_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the hit -> bleed ->
            die link sweep.

            This is the lane that makes the damage lane's number COST
            something.  Round 83 proved the client computes nothing and never
            subtracts damage from hit points, and GT-024 confirmed on a real
            screen that the floating number leaves the HP bar untouched.  So
            if a hit is ever to reduce HP, the server must say both halves
            itself, and this lane is that sentence said once, end to end:

              * HP_BASELINE     ActorAttr, hp 100/100      (balance 100)
              * HIT_WEAK        CHitResult  -63, flags 0x0001
              * HP_AFTER_WEAK   ActorAttr, hp_current 37   (100 - 63)
              * MISS            CHitResult    0, flags 0x0000  -- control
              * HP_AFTER_MISS   ActorAttr, hp_current 37   (a miss moves nothing)
              * HIT_STRONG      CHitResult -379, flags 0x0001
              * HP_ZERO_DYING   ActorAttr, hp_current 0 + death timer 20.0
                                (37 - 379 clamped at the floor)
              * DYING_ELAPSED   ActorAttr, death timer 0.0

            The arithmetic is OURS (the same constants the damage lane pins,
            copied with drift tests, never imported), applied to a server-held
            balance whose whole ladder is refused unless it reproduces.  The
            original server's link between these frames is unrecoverable and
            is not claimed.

            IDENTITY IS PINNED.  Every neighbouring lane validates a live
            sweep structurally because live bytes depend on the session's
            identity; this lane goes one step narrower and refuses to fire at
            all unless the selected actor IS the canonical smoke identity the
            pins were computed for, so the bytes a tester sees are the pinned
            bytes, byte for byte, or nothing.

            ONE-SHOT, same reason as the damage lane: the value of the ladder
            is that a tester can predict every number before it appears.

            The lane touches no store, takes no socket action, adds no HP
            column anywhere, and composes nothing when the scenario is absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"damage_hp_link_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "damage_hp_link_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "damage_hp_link_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.damage_hp_link_sweep_count:
                self.events.append(
                    "damage_hp_link_hypothesis_already_sent_no_reply"
                )
                return []
            selected = self.foundation.selected
            identity_lo = getattr(selected, "identity_lo", None)
            identity_hi = getattr(selected, "identity_hi", None)
            if (
                identity_lo != HP_LINK_PROBE_IDENTITY_LO
                or identity_hi != HP_LINK_PROBE_IDENTITY_HI
            ):
                self.events.append(
                    "damage_hp_link_hypothesis_identity_not_pinned_no_reply"
                )
                return []
            actions = build_damage_hp_link_sweep(
                legacy, identity_lo, identity_hi,
                damage_hp_link_unlock, damage_hp_link_hypothesis_scenario,
            )
            self.damage_hp_link_sweep_count += 1
            event = "damage_hp_link_hypothesis_link_sweep_sent"
            if event != DAMAGE_HP_LINK_EVENT_NAME:
                raise RuntimeError("HYP-PF-026 sweep event name drift")
            self.events.append(event)
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-025 active
        # REMOTE-PLAYER-DISPATCH-001.  Registered by the round-96 ledger
        # append; this annotation and that entry's source_refs bind each
        # other both ways.
        def _dispatch_remote_player_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the visibility sweep.

            This is the lane that puts ``actor_type 2`` -- ``CNetActor``, the
            remote-player branch of the client's actor factory -- on the wire
            for the first time in this project's history, and the design is
            OURS: the original server is closed, was never published, and no
            corpus holds a server->client capture of a remote human player,
            so there is nothing to recover and everything to design.  The
            owner pre-approved multiplayer chunk 2 (2026-08-19 11:45).

            The request side is the same accepted 34-byte ascii12 shape the
            other sweeps reuse: the one client action an attended tester can
            fire on demand, with every refusal guard already proven.  Nothing
            in the request is read.

            The answer is five frames for three synthetic identities in the
            0x00A0_xxxx band (a DESIGN CHOICE, visibly fake, colliding with
            nothing): SPAWN_BARE (ActorAttr with the never-before-shipped
            BasicAttr name bit + full MovementAttr), SPAWN_AVATAR (the same
            plus the selected character's opaque AvatarAttr rebound to probe
            B -- the A/B comparison is the avatar experiment), MOVE_A_1 and
            MOVE_A_2 (a lone MovementAttr to a known identity, mask 0x01 then
            0x03), and NEGATIVE_CONTROL (a deliberately wrong-class NPCAttr
            that the bind gate 0x4697B0 must drop in silence; a name over
            that actor falsifies chunk 1 and stops the lane).

            ONE-SHOT: a second sweep would re-introduce identities the client
            now knows and turn spawns into updates.  15-second spacing, so an
            attended tester never races their camera (the round-84 lesson).

            The lane touches no store, takes no socket action, and composes
            nothing at all when the scenario is absent.  A compose-time
            refusal (a missing avatar wire, a probe/selected-identity
            collision, any pin drift) is caught HERE and turned into a named
            no-reply event: fail closed means the client sees silence and the
            log says exactly why.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"remote_player_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "remote_player_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "remote_player_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.remote_player_sweep_count:
                self.events.append(
                    "remote_player_hypothesis_already_sent_no_reply"
                )
                return []
            selected = self.foundation.selected
            selected_identity = (
                (int(selected.identity_hi) << 32) | int(selected.identity_lo)
            )
            try:
                actions = build_remote_player_sweep(
                    legacy, remote_player_probes, remote_player_unlock,
                    remote_player_hypothesis_scenario,
                    avatar_wire=selected.avatar_wire,
                    selected_identity=selected_identity,
                )
            except (ValueError, RuntimeError) as exc:
                self.events.append(
                    "remote_player_hypothesis_compose_refused_no_reply_"
                    f"{exc!r}"
                )
                return []
            self.remote_player_sweep_count += 1
            self.events.append(
                "remote_player_hypothesis_visibility_probe_sent"
            )
            return actions

        def _npc_hostile_start_game_response(self, pc, frame, position=None):
            """The entry half of HYP-PF-027: the SCENE-005 player faction.

            The relation the client renders is a PAIR: the arena-v2 negative
            proved an NPC faction of 6 alone, against the unmodified player's
            constructor-default 0, presents as neutral.  So under this lane's
            opt-in scenario the full-writable StartGame response is recomposed
            through the frozen ``player_wire.make_actor_attr_with_basic_
            faction`` serializer -- the exact SCENE-005/SCENE-007 probe, which
            accepts ONLY faction 1 -- and ONLY when the selected character is
            the canonical smoke identity the pins were computed for.

            FAIL CLOSED, in the direction of production: any other identity,
            and any serializer refusal, returns the untouched production
            bytes with a named event, and the sweep dispatch below then
            refuses by name -- the tester sees the full proven pairing or no
            experiment at all, never a half-paired one.

            ``position``: CORE-REQUEST-017 point 1's login-scene override,
            threaded through here too (pf-adversary, second pass) even
            though this whole method is a no-op for any character that
            isn't the pinned smoke identity below -- that identity check is
            the only thing making a real GM-login override coexisting with
            this opt-in scenario safe, and nothing in this file enforces
            the two never running together.  ``None`` (the default)
            reproduces the exact prior behaviour: ``start_game`` falls back
            to ``character.position`` itself.
            """
            selected = self.foundation.selected
            if (
                getattr(selected, "identity_lo", None)
                != NPC_HOSTILE_PLAYER_IDENTITY_LO
                or getattr(selected, "identity_hi", None)
                != NPC_HOSTILE_PLAYER_IDENTITY_HI
            ):
                self.events.append(
                    "npc_hostile_hypothesis_player_identity_not_pinned_"
                    "production_start_game"
                )
                return pc, frame
            try:
                faction_pc, faction_frame = self.foundation.projector.start_game(
                    selected,
                    position=position,
                    basic_faction=(
                        npc_hostile_hypothesis_scenario.player_pair_faction
                    ),
                    backpack=self.foundation.backpack,
                )
            except (ValueError, RuntimeError, TypeError) as exc:
                self.events.append(
                    "npc_hostile_hypothesis_player_faction_compose_refused_"
                    f"production_start_game_{exc!r}"
                )
                return pc, frame
            # The faction-1 response must be the production response plus
            # exactly one tagged u32 (five bytes).  Anything else means the
            # frozen serializer drifted, and production bytes go out instead.
            if len(faction_pc) != len(pc) + NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA:
                self.events.append(
                    "npc_hostile_hypothesis_player_faction_length_drift_"
                    "production_start_game"
                )
                return pc, frame
            self.npc_hostile_player_faction_start_sent = True
            self.events.append(
                "npc_hostile_hypothesis_player_faction1_start_game_sent"
            )
            return faction_pc, faction_frame

        # PF-HYPOTHESIS-LEDGER: HYP-PF-027 active
        # NPC-HOSTILE-DISPATCH.  Registered by the round-99 ledger append;
        # this annotation and that entry's source_refs bind each other both
        # ways.
        def _dispatch_npc_hostile_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the hostile spawn.

            This is Door A of the mob-aggro design (round-98 draft): make the
            first Port Royal placement PRESENT as hostile, on proven ground
            only.  The answer is ONE frame -- the HYP-PF-023 SPAWN for the
            same frozen probe (NPC 0x2001, alive, placed) with EXACTLY the
            five-byte BasicAttr faction splice (bit 0x0400, u32 value 6) --
            paired with the SCENE-005 player faction 1 that the entry hook
            above already put on this session's StartGame.  Both values are
            OUR composition; the original server's faction assignment is
            unrecoverable.

            The request side is the same accepted 34-byte ascii12 shape every
            other sweep reuses: the one client action an attended tester can
            fire on demand, with every refusal guard already proven.  Nothing
            in the request is read.

            THE PAIRING IS REQUIRED.  If the entry hook fell back to the
            production StartGame -- wrong identity, serializer refusal, length
            drift -- this dispatch refuses by name and composes nothing: an
            NPC faction against the constructor-default player faction is the
            arena-v2 proven NEGATIVE, and sending it would re-run a known
            neutral and answer nothing.

            ONE-SHOT: a second spawn for an identity the client already knows
            would take the vtable +0x20 update path and turn the experiment
            into a different one.  A repeat trigger is refused with a named
            event and no bytes.

            The lane touches no store, takes no socket action, and composes
            nothing at all when the scenario is absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"npc_hostile_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "npc_hostile_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "npc_hostile_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.npc_hostile_sweep_count:
                self.events.append(
                    "npc_hostile_hypothesis_already_sent_no_reply"
                )
                return []
            selected = self.foundation.selected
            if (
                getattr(selected, "identity_lo", None)
                != NPC_HOSTILE_PLAYER_IDENTITY_LO
                or getattr(selected, "identity_hi", None)
                != NPC_HOSTILE_PLAYER_IDENTITY_HI
            ):
                self.events.append(
                    "npc_hostile_hypothesis_player_identity_not_pinned_no_reply"
                )
                return []
            if not self.npc_hostile_player_faction_start_sent:
                self.events.append(
                    "npc_hostile_hypothesis_player_faction_not_applied_no_reply"
                )
                return []
            try:
                actions = build_npc_hostile_sweep(
                    legacy, npc_hostile_probe, npc_hostile_unlock,
                    npc_hostile_hypothesis_scenario,
                )
            except (ValueError, RuntimeError) as exc:
                self.events.append(
                    "npc_hostile_hypothesis_compose_refused_no_reply_"
                    f"{exc!r}"
                )
                return []
            self.npc_hostile_sweep_count += 1
            self.events.append(
                "npc_hostile_hypothesis_faction_pairing_sent"
            )
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-029 active
        # NPC-HP-LINK-002.  The dispatch branch NPC-HP-LINK-001 deliberately
        # withheld; this annotation and the HYP-PF-029 entry's source_refs
        # bind each other both ways.
        def _dispatch_npc_hp_link_hypothesis(self, parsed):
            """Answer one accepted chat input frame with the TARGET link sweep.

            This is the missing middle piece.  HYP-PF-024 puts a number on the
            screen and GT-024 proved the client draws it; HYP-PF-026 links that
            number to hit points but only for the PLAYER's own actor on the
            base VitalData carrier.  Nothing in this tree had ever moved a
            TARGET's hit points -- and on 2026-08-20 an attended test proved on
            video that 505 points of damage delivered as CHitResult frames
            moved a target's HP bar by exactly zero.  The client computes
            nothing, so the server must say BOTH halves, and this lane says
            them alternately, about one frozen NPC, end to end:

              * TARGET_SPAWN          NPCAttr, hp 100/100, alive, placed
              * HIT_WEAK              CHitResult  -63, flags 0x0001
              * TARGET_HP_AFTER_WEAK  NPCAttr, hp_current 37   (100 - 63)
              * MISS                  CHitResult    0, flags 0x0000 -- control
              * TARGET_HP_AFTER_MISS  NPCAttr, hp_current 37   (a miss moves
                                      nothing; byte-identical to the frame
                                      before it, on purpose)
              * HIT_STRONG            CHitResult -379, flags 0x0001
              * TARGET_HP_ZERO_DYING  NPCAttr, hp_current 0 + death timer 20.0
                                      (37 - 379 clamped at the floor)
              * TARGET_DYING_ELAPSED  NPCAttr, death timer 0.0

            The performer of every hit frame stays the session's OWN selected
            actor -- one side of a CHitResult must be the player or the
            six-stage visibility filter at 0x43FEF0 draws nothing -- and the
            target is the frozen Port Royal placement 0x2001 resolved once at
            construction.  The balance ladder is OURS and is re-walked by real
            arithmetic on every composition; a sweep that does not reproduce
            it is refused by the encoder before it can reach this method.

            The request side is the same accepted 34-byte ascii12 shape every
            neighbouring sweep reuses: the one client action an attended tester
            can fire on demand, with every refusal guard already proven.
            Nothing in the request is read.

            ONE-SHOT, the same reason as both parents: the value of the ladder
            is that a tester can predict 100 -> 37 -> 0 before it appears, and
            a second sweep interleaved with the first turns a legible sequence
            into noise -- and would spawn again an identity the client already
            knows, which is a different experiment.

            The lane touches no store, takes no socket action, adds no HP
            column anywhere, and composes nothing at all when the scenario is
            absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"npc_hp_link_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "npc_hp_link_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "npc_hp_link_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.npc_hp_link_sweep_count:
                self.events.append(
                    "npc_hp_link_hypothesis_already_sent_no_reply"
                )
                return []
            selected = self.foundation.selected
            actions = build_npc_hp_link_sweep(
                legacy, npc_hp_link_target,
                selected.identity_lo, selected.identity_hi,
                npc_hp_link_unlock, npc_hp_link_hypothesis_scenario,
            )
            self.npc_hp_link_sweep_count += 1
            # The event name is the module's constant, written out here once
            # and compared, exactly as the parent link lane does: renaming the
            # published event is an immediate RuntimeError rather than a string
            # that quietly drifted away from the ledger and the tests.
            event = "npc_hp_link_hypothesis_target_sweep_sent"
            if event != NPC_HP_LINK_EVENT_NAME:
                raise RuntimeError("HYP-PF-029 sweep event name drift")
            self.events.append(event)
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-038 active
        def _dispatch_hostile_hp_link_hypothesis(self, parsed):
            """HOSTILE-HP-LINK-001: seven frames at a REAL hostile, alive.

            The sibling lane HYP-PF-029 already showed a bar move on a screen,
            but on a synthetic identity with a synthetic 100-point ladder.
            This lane asks the one question that leaves open: does the same
            shape hold for placement 30 -- actor 0x201F, "Tornado Eagle" --
            carrying the 3857 HP baseline the CLIENT itself ships for that
            row.  Nothing else changes: same envelope, same two carriers, same
            arithmetic engine, same 34-byte ascii12 trigger.

            THE TARGET IS PLACED AGAINST THE PLAYER, and that is the reason
            this lane resolves its target HERE rather than at construction.
            The frozen world row for placement 30 is roughly twelve thousand
            units from the player spawn; a target sent there is a dot on the
            minimap and nothing on the screen, which is precisely the outcome
            an earlier attended round measured on a neighbouring lane.  The
            position comes from the authoritative row the frozen TargetPos
            write path checkpoints, so a session that has not reached a
            position composes nothing.

            NO LETHAL FRAME.  The ladder stops at 771, the encoder refuses a
            death timer by name and the plan validator refuses a floor
            balance: "does it die" is GT-036's question and belongs to a later
            version of this slot.

            ONE-SHOT, for the sibling lane's reason: the value of a ladder is
            that a tester can predict it before it appears, and a second sweep
            interleaved with the first would also re-spawn an identity the
            client already knows, which is a different experiment.

            The lane touches no store, takes no socket action, adds no HP
            column anywhere, and composes nothing at all when the scenario is
            absent.
            """
            self.rx_frames += 1
            classification = classify_chat_input_attempt(legacy, parsed)
            if classification != "ascii12":
                self.events.append(
                    f"hostile_hp_link_hypothesis_{classification}_no_reply"
                )
                return []
            if self.foundation.selected is None:
                self.events.append(
                    "hostile_hp_link_hypothesis_no_selected_no_reply"
                )
                return []
            if not self.teleport_sent or not self.runtime_ack_sent:
                self.events.append(
                    "hostile_hp_link_hypothesis_wrong_sequence_no_reply"
                )
                return []
            if self.hostile_hp_link_sweep_count:
                self.events.append(
                    "hostile_hp_link_hypothesis_already_sent_no_reply"
                )
                return []
            selected = self.foundation.selected
            if (
                selected.identity_lo
                != HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
                or selected.identity_hi
                != HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI
            ):
                # The attended ticket promises the tester that picking the
                # wrong row on the character screen produces NO BYTES AT ALL,
                # and an adversarial review of R162 found this lane shipping
                # without the guard that promise rests on.  ITEMOP-RES-
                # GREENLINE-001 pins the same identity for the same reason:
                # a sweep composed for an unpinned actor is a sweep whose
                # frames nobody can attribute afterwards.
                self.events.append(
                    "hostile_hp_link_hypothesis_identity_not_pinned_no_reply"
                )
                return []
            position = selected.position
            if position.scene_id != HOSTILE_HP_LINK_SCENE_ID:
                # The frozen placement row this lane pins belongs to one
                # scene.  A player standing in another one would be handed a
                # target placed next to them but addressed in a scene they are
                # not in, and the frame would answer nothing.
                self.events.append(
                    "hostile_hp_link_hypothesis_wrong_scene_no_reply"
                )
                return []
            try:
                target = resolve_hostile_hp_link_target(
                    legacy,
                    (float(position.x), float(position.y), float(position.z)),
                    hostile_hp_link_hypothesis_scenario,
                )
                actions = build_hostile_hp_link_sweep(
                    legacy, target,
                    selected.identity_lo, selected.identity_hi,
                    hostile_hp_link_unlock, hostile_hp_link_hypothesis_scenario,
                )
            except HostileHpLinkValidationError as exc:
                # Every refusal in this lane is a NAMED EVENT, including the
                # ones that come out of the encoder rather than out of a
                # guard here.  The frozen dispatch path this method runs
                # under has a try/finally with no except, so an exception
                # that escaped would take the connection's thread with it --
                # a lane that refuses is supposed to go quiet, not to hang up
                # on the tester mid-round.
                self.events.append(
                    "hostile_hp_link_hypothesis_refused_no_reply: %s"
                    % type(exc).__name__
                )
                return []
            self.hostile_hp_link_sweep_count += 1
            # The event name is the module's constant, written out here once
            # and compared, exactly as both neighbours do: renaming the
            # published event is an immediate RuntimeError rather than a
            # string that quietly drifted away from the ledger and the tests.
            event = "hostile_hp_link_hypothesis_target_sweep_sent"
            if event != HOSTILE_HP_LINK_EVENT_NAME:
                raise RuntimeError("HYP-PF-038 sweep event name drift")
            self.events.append(event)
            return actions

        # PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
        def _dispatch_delete_actor_hypothesis(self, parsed):
            """Soft-delete one owned character behind the explicit opt-in.

            Character-select-stage lane: the character list must have been
            sent and nothing may be selected.  The repository commit (the
            ``deleted_at`` write under the migration-004 partial unique
            indexes) happens before any ack byte is queued; the designed
            echo ack is composed and structurally pinned first, and wrong
            envelopes, wrong ops, wrong stages, and repository refusals all
            fail closed with no reply and no write.
            """
            self.rx_frames += 1
            classification = classify_delete_actor_attempt(legacy, parsed)
            if classification != "exact_op1":
                self.events.append(
                    f"delete_actor_hypothesis_{classification}_no_reply"
                )
                return []
            if (
                not self.select_actor_sent
                or self.start_game_reply_sent
                or self.foundation.selected is not None
            ):
                self.events.append(
                    "delete_actor_hypothesis_wrong_stage_no_reply"
                )
                return []
            request = parse_accepted_delete_request(parsed)
            pc, frame = make_delete_actor_ack_response(
                legacy, parsed.nested_payload,
            )
            try:
                self.foundation.soft_delete_character(request.selector)
            except Exception as exc:
                self.events.append(
                    f"delete_actor_hypothesis_repository_failure_no_reply_{exc!r}"
                )
                return []
            self.delete_actor_soft_delete_count += 1
            self.events.append(
                f"delete_actor_hypothesis_selector{request.selector:02d}"
                "_committed_before_ack"
            )
            return [(
                f"HYP_PF_015_DELETE_ACTOR_SELECTOR{request.selector:02d}"
                "_SOFT_DELETE_COMMITTED",
                pc, frame, 0.0,
            )]

        # PF-HYPOTHESIS-LEDGER: HYP-PF-021 active
        def _dispatch_delete_refresh_hypothesis(self, parsed):
            """Soft-delete, acknowledge, then rebuild the whole client list.

            DELETE-REFRESH-001.  UI-REFRESH-001 proved that the client keeps
            the character list in one buffer with no erase-by-key path at
            all, so the 0x36DB acknowledgement can never take a row off the
            screen; the only frame that can is a fresh SelectActorVital
            0x36EF, which resets the model, refills it and builds a new
            cStateCreateActor whose enter hook also zeroes the page variable
            the delete animation left set.  This lane therefore answers one
            accepted delete request with two frames: the unchanged pinned
            HYP-PF-015 echo ack, then the unchanged runtime-proven character
            list projection taken over the POST-DELETE character set, 0.35 s
            later (the same gap the login-time list has always used).

            Nothing is composed here: the rebuild is the projector's own
            output, verified and hash-pinned before it may be queued.  The
            lane fails closed as one unit -- if the post-delete list still
            carries the deleted selector, or the projection does not verify,
            NO bytes are queued at all, not even the ack.  The soft delete
            is committed before any byte is queued, exactly as HYP-PF-015
            pins it; a rebuild refusal therefore leaves the row deleted and
            the client silent, which is observable in the DB and named in
            the event log rather than guessed at on the wire.
            """
            self.rx_frames += 1
            classification = classify_delete_actor_attempt(legacy, parsed)
            if classification != "exact_op1":
                self.events.append(
                    f"delete_refresh_hypothesis_{classification}_no_reply"
                )
                return []
            if (
                not self.select_actor_sent
                or self.start_game_reply_sent
                or self.foundation.selected is not None
            ):
                self.events.append(
                    "delete_refresh_hypothesis_wrong_stage_no_reply"
                )
                return []
            request = parse_accepted_delete_request(parsed)
            ack_pc, ack_frame = make_delete_actor_ack_response(
                legacy, parsed.nested_payload,
            )
            try:
                self.foundation.soft_delete_character(request.selector)
            except Exception as exc:
                self.events.append(
                    "delete_refresh_hypothesis_repository_failure_no_reply_"
                    f"{exc!r}"
                )
                return []
            try:
                projection = self.foundation.character_list()
                record_count = assert_selector_absent(
                    self.foundation.characters, request.selector,
                )
                rebuild_pc, rebuild_frame = (
                    make_delete_actor_list_rebuild_response(
                        legacy, projection, record_count=record_count,
                    )
                )
            except Exception as exc:
                self.events.append(
                    "delete_refresh_hypothesis_rebuild_refused_no_reply_"
                    f"{exc!r}"
                )
                return []
            self.delete_actor_soft_delete_count += 1
            self.delete_refresh_list_rebuild_count += 1
            self.events.append(
                f"delete_refresh_hypothesis_selector{request.selector:02d}"
                "_committed_before_ack"
            )
            self.events.append(
                "delete_refresh_hypothesis_list_rebuild_records"
                f"{record_count:02d}_after_ack"
            )
            return [
                (
                    f"HYP_PF_021_DELETE_ACTOR_SELECTOR{request.selector:02d}"
                    "_SOFT_DELETE_COMMITTED",
                    ack_pc, ack_frame, 0.0,
                ),
                (
                    DELETE_REFRESH_ACTION_LABEL,
                    rebuild_pc, rebuild_frame, DELETE_REFRESH_GAP_SECONDS,
                ),
            ]

        def _checkpoint_exact_target(self, target) -> None:
            verdict = None
            stamp = None
            if move_authority_hypothesis_scenario is not None:
                verdict, stamp = self._move_authority_verdict(target)
                if not verdict.accepted:
                    self.move_authority_refusal_count += 1
                    self.move_authority_last_verdict = verdict
                    self.events.append(
                        f"move_authority_hypothesis_{verdict.reason}_no_write"
                    )
                    return
            x, y, z, heading, _flags, _moving = target
            selected = self.foundation.selected
            candidate = Position(
                selected.position.scene_id,
                selected.position.scene_seq,
                x, y, z, heading,
            )
            if candidate != selected.position and (
                self.login_scene_override_visit
            ):
                # A LOGIN-SCENE OVERRIDE IS A VISIT, NOT A MOVE (chief, round
                # ngwnnj/R223, from pf-adversary's measurement of the first
                # half of this round's change).  Once the in-memory character
                # names the scene it was actually sent to, this write -- the
                # first step the player takes -- would stamp that scene into
                # `character_positions` and make a SINGLE-USE override
                # permanent: the next login carries no override at all and
                # starts there anyway.  Measured at scene 278, whose registry
                # row is `sent_before=NO, return_ticket=REQUIRED`: a character
                # relocated there cannot walk home, and CHARTER-02 rule 2
                # calls a version that takes away what the last one could do
                # damage rather than a version.
                #
                # The in-memory position still tracks the player (the census,
                # the travel gates and this same helper all read it), so
                # nothing this session decides is stale -- only the DURABLE
                # row is withheld, and by name.  `is_position_persist_allowed`
                # cannot stand in for this: 1/2/278/997 are all pinned True,
                # which is right for a character who walked there and wrong
                # for one a GM staged there for one login.
                #
                # No GM_WARP_POSITION_CONFIRMED here either: that token means
                # a durable write survived (CORE-REQUEST-GM-030), and on this
                # branch there is none to survive.
                self.foundation.selected = replace(
                    self.foundation.selected, position=candidate,
                )
                self.events.append(
                    "gm_login_scene_override_visit_no_durable_write_scene_"
                    f"{candidate.scene_id}"
                )
            elif candidate != selected.position:
                self.foundation.checkpoint(candidate)
                if (
                    self.gm_warp_confirm_window_open
                    and world_scene_travel.is_position_persist_allowed(
                        candidate.scene_id, scene_entry_registry,
                    )
                ):
                    # CORE-REQUEST-GM-030.  AFTER the durable write survived,
                    # never at the entry: a refused move-authority verdict
                    # returns above and a candidate equal to the current row
                    # skips the write, and neither of those may print a token
                    # that says the position was confirmed.
                    #
                    # The persist gate is the same predicate the writer uses
                    # (lifecycle.checkpoint -> is_position_persist_allowed ->
                    # the store's save_position, write_position=).  Spelling
                    # that call out in full here would trip the caller-set pin
                    # in tests/test_move_authority_dispatch.py, which counts
                    # the literal on any line of any module.  pf-adversary
                    # measured the hole it closes: in a scene pinned
                    # persist_position_allowed=False -- scene 17 today, which
                    # this project's own Columbus lane teleports into --
                    # checkpoint() returns cleanly having written no row at
                    # all, and the token printed over an unchanged row.
                    #
                    # stderr, not stdout: lane_hooks/__init__.py records the
                    # incident this would repeat -- a token on stdout landed
                    # inside the JSON artifact of
                    # tools/pf_runtimeres_death_headless_replay.py --json.
                    self.gm_warp_confirm_window_open = False
                    print("GM_WARP_POSITION_CONFIRMED", file=sys.stderr)
                    self.events.append("gm_warp_position_confirmed")
                    # CORE-REQUEST-GM-030/031.  Strictly additive, and only
                    # ever reached immediately after the token above -- never
                    # instead of it, never gating it.  Whether the row that
                    # was just confirmed is also the point the GM's own
                    # /warp asked for, per gm.warp_target_record.
                    self._gm_warp_note_position_target(candidate)
            if verdict is not None:
                # Only now.  A checkpoint that raised (a stale or stolen lease
                # is the frozen path's own refusal) must not leave an event
                # saying the reading was admitted, a counter saying it was, or
                # a baseline pointing where no row points.
                self._move_authority_record_admitted(verdict, target, stamp)

        def _gm_warp_note_position_target(self, candidate) -> None:
            """CORE-REQUEST-GM-030/031: is the confirmed row the GM's target.

            Called ONLY from the branch above, immediately after
            ``GM_WARP_POSITION_CONFIRMED`` printed and its own event fired --
            never on any other path, and never able to change whether that
            token fires.  Purely diagnostic: nothing here may raise, and
            nothing here may be read by anything that decides whether a
            position is written.

            ``self.gm_warp_confirm_target`` is whatever
            ``_gm_warp_open_confirm_window`` parked for THIS confirm window
            (None if nothing was, or the parked record did not survive
            ``take_warp_target_with_reason``'s own checks -- see
            ``self.gm_warp_confirm_target_reason`` for which).
            """
            target = self.gm_warp_confirm_target
            if target is None:
                reason = self.gm_warp_confirm_target_reason or "unknown"
                self.events.append(f"gm_warp_position_target_unknown_{reason}")
                return
            try:
                matches = position_matches_target(target, candidate)
                distance = distance_to_target(target, candidate)
            except Exception:  # noqa: BLE001 - diagnostic only; see docstring
                self.events.append(
                    "gm_warp_position_target_unknown_compare_failed"
                )
                return
            if matches:
                print("GM_WARP_POSITION_TARGET_MATCH", file=sys.stderr)
                self.events.append("gm_warp_position_target_match")
                return
            if distance is not None:
                print("GM_WARP_POSITION_TARGET_MISMATCH", file=sys.stderr)
                self.events.append(
                    f"gm_warp_position_target_mismatch_{int(round(distance))}"
                )
                return
            reason = self._gm_warp_target_unknown_reason(target, candidate)
            self.events.append(f"gm_warp_position_target_unknown_{reason}")

        @staticmethod
        def _gm_warp_target_unknown_reason(target, position) -> str:
            """Why ``distance_to_target`` could not compare, for the event.

            Mirrors ``distance_to_target``'s own guards read-only -- this
            never gates anything, it only names, after the fact, whichever
            one of them is why the comparison came back None.  Never raises:
            an exception here would blame a diagnostic label for a listener
            thread crash.
            """
            try:
                scene_id = getattr(position, "scene_id", None)
                if type(scene_id) is not int or scene_id != target.scene_id:
                    return "different_scene"
                for axis in ("x", "y", "z"):
                    try:
                        reported = getattr(position, axis, None)
                    except Exception:  # noqa: BLE001
                        return "missing_axis"
                    if (
                        not isinstance(reported, (int, float))
                        or isinstance(reported, bool)
                    ):
                        return "missing_axis"
                    try:
                        reported = float(reported)
                    except (OverflowError, ValueError):
                        return "not_finite"
                    if not math.isfinite(reported):
                        return "not_finite"
                # Every axis was present and finite -- the None therefore
                # came from the squared-distance sum overflowing or landing
                # non-finite, which is the same family of answer.
                return "not_finite"
            except Exception:  # noqa: BLE001
                return "unknown"

        def _move_authority_verdict(self, target):
            """MOVE-AUTHORITY-002 (HYP-PF-030): decide, do not reply.

            Reached only when the opt-in move-authority scenario is loaded.
            Nothing is composed, queued or sent either way, because no
            corrective-reposition frame has ever been captured (see
            ``move_authority_hypothesis`` for why inventing one is refused).

            The baseline is seeded from the AUTHORITATIVE ROW, not from
            whatever the client reports first, so the first reading of a
            connection is measured like every other one; and the baseline
            advances only on readings this gate admitted, so a refused reading
            can never become the ground the next one is measured against.
            """
            policy = move_authority_hypothesis_scenario.policy
            now = monotonic_clock()
            if self.move_authority_last_accepted_xyz is None:
                position = self.foundation.selected.position
                self.move_authority_last_accepted_xyz = (
                    float(position.x), float(position.y), float(position.z),
                )
                self.move_authority_last_accepted_at = now
            grace = self.move_authority_grace_remaining > 0
            elapsed = now - self.move_authority_last_accepted_at
            verdict = evaluate_move_report(
                self.move_authority_last_accepted_xyz,
                target, elapsed, policy, grace=grace,
            )
            return verdict, now

        def _move_authority_record_admitted(self, verdict, target, stamp):
            """Commit the admitted reading, after the durable write survived."""
            if self.move_authority_grace_remaining > 0:
                self.move_authority_grace_remaining -= 1
            self.move_authority_accept_count += 1
            self.move_authority_last_verdict = verdict
            if len(target) >= 3:
                self.move_authority_last_accepted_xyz = (
                    float(target[0]), float(target[1]), float(target[2]),
                )
            self.move_authority_last_accepted_at = stamp
            self.events.append(
                f"move_authority_hypothesis_{verdict.reason}_admitted"
            )

        def _move_authority_note_server_moves(self, actions) -> None:
            """Reopen the grace window when THE SERVER moved the player.

            The gate measures a client's reading against the last position it
            admitted.  When the frozen dispatcher teleports the player itself
            -- scene entry, and the V137 marker transport mid-session, which
            lands about 2340 units away horizontally and 448 vertically -- the
            next honest reading is far from that baseline through no fault of
            the client, and without this the durable row would stay frozen for
            the rest of the session.  The server knows when it did that: the
            action it queued carries TELEPORT in its label.  Grace is therefore
            tied to a server-initiated move and to nothing else.
            """
            for action in actions or ():
                if action and "TELEPORT" in action[0]:
                    self.move_authority_grace_remaining = (
                        move_authority_hypothesis_scenario.policy
                        .teleport_grace_reports
                    )
                    self.events.append(
                        "move_authority_hypothesis_grace_reopened_after_"
                        "server_teleport"
                    )
                    return

        def _dispatch_object_population_target(self, parsed, target):
            """Own the exact TargetPos lane for the opt-in V94 capability."""
            if target is None or self.foundation.selected is None:
                self.rx_frames += 1
                self.events.append("object_population_target_rejected_no_reply")
                return []
            if self.foundation.selected.position.scene_id != population_scenario.scene_id:
                self.rx_frames += 1
                self.events.append("object_population_wrong_scene_no_reply")
                return []

            # Preserve the durable TargetPos contract first.  Any stale-lease or
            # repository failure therefore prevents population state and bytes
            # from being committed to the outbound queue.
            self._checkpoint_exact_target(target)
            if not (self.runtime_ack_sent and self.teleport_sent):
                inherited_actions = super().dispatch(parsed)
                self.events.append("object_population_not_runtime_ready_no_reply")
                return inherited_actions

            xyz = tuple(target[:3])
            if not all(math.isfinite(value) for value in xyz):
                self.events.append("object_population_nonfinite_no_reply")
                return []
            if self.object_population_membership is None:
                transition = build_port_royal_initial_population(legacy, xyz)
                action = (
                    "OBJECT_POP_V94_INITIAL_NEAREST20",
                    transition.pc, transition.frame, 0.0,
                )
                reapply = (
                    "OBJECT_POP_V94_INITIAL_MODEL_READY_REAPPLY",
                    transition.pc, transition.frame,
                    population_scenario.initial_reapply_ms / 1000.0,
                )
                population_actions = [action, reapply]
                inherited_actions = super().dispatch(parsed)
                self.object_population_membership = transition.current_indices
                self.object_population_anchor = xyz
                self.object_population_generation = 1
                self.events.append(
                    "object_population_v94_initial_membership_committed"
                )
                return inherited_actions + population_actions

            anchor = self.object_population_anchor
            if anchor is None:
                raise RuntimeError("population membership exists without anchor")
            travel2 = sum((value - prior) ** 2 for value, prior in zip(xyz, anchor))
            if not math.isfinite(travel2):
                raise ValueError("population travel distance is non-finite")
            if travel2 < population_scenario.refresh_distance ** 2:
                inherited_actions = super().dispatch(parsed)
                self.events.append("object_population_below_refresh_distance")
                return inherited_actions

            transition = build_port_royal_membership_transition(
                legacy, self.object_population_membership, xyz,
            )
            # V94 advances the scan anchor at the threshold even if the set is
            # unchanged.  Ordering-only changes emit no packet and do not replace
            # the installed membership ordering.
            if set(transition.current_indices) == set(self.object_population_membership):
                inherited_actions = super().dispatch(parsed)
                self.object_population_anchor = xyz
                self.events.append("object_population_unchanged_set_suppressed")
                return inherited_actions

            entered = sorted(transition.entrant_indices)
            left = sorted(transition.omitted_indices)
            label = (
                "OBJECT_POP_V94_REFRESH_ENTER["
                + ",".join(map(str, entered))
                + "]_LEAVE[" + ",".join(map(str, left)) + "]"
            )
            population_actions = [(label, transition.pc, transition.frame, 0.0)]
            inherited_actions = super().dispatch(parsed)
            self.object_population_anchor = xyz
            self.object_population_membership = transition.current_indices
            self.object_population_generation += 1
            self.events.append(
                f"object_population_generation_{self.object_population_generation}_committed"
            )
            return inherited_actions + population_actions

        def _sync_combat_scene_state(self):
            """The selected character's scene decides the combat roster.

            COO-DECISION 2026-08-29T08:48+07:00 item 3, the chief's half:
            resolve ``position.scene_id`` through ``world_scene_folder.
            scene_folder_for_scene_id`` -- THE one public reader, never the
            registry's ``model_id``, which spells six of the sixteen
            addressed scenes differently from their folders -- and hand back
            that scene's own roster.  The combat ledger and the AI register
            re-open on the same roster the moment the folder differs from
            the one they were opened on, so the three can never hold
            different scenes' rows (LANE-B letter 20260829_0744: a ledger
            still holding bg0001's four identities is why a Bg0002 mob was
            refused as ``target_not_in_ledger`` before any gate was asked).

            Returns ``None`` when the registry does not address the scene id
            at all -- a refusal, not an absence of data (world_scene_folder's
            own contract): the caller must ship NO roster and say so before
            composing any other verdict, never fall back to a default one.
            An ADDRESSED scene with no mined mob table (folder known, not in
            ``field_mobs.live_scenes()``) is different and legitimate: its
            truthful roster is empty, so an attack there resolves no target
            and answers with the existing not-a-field-mob silence.

            Re-opening on a scene change resets a scene's WOUNDS and AI
            state at epoch 0 -- but never its DEATHS.  mob_death_register is
            per-(identity, scene) and survives the trip on purpose, so a
            freshly re-opened ledger is rehydrated from it: every identity
            the register holds dead in this folder re-opens at 0 HP, not at
            its ceiling.  pf-adversary (this round, D1, measured on the real
            1<->278 debug-gate round trip) broke the first version of this
            method for skipping that: return to a scene you killed in and
            repopulation_entries refused BY DESIGN on every subsequent hit
            (dead in the register, standing at full HP in the ledger --
            mob_death.py's REFUSE_LEDGER_DISAGREES_WITH_REGISTER), degrading
            every bar/death frame to the one-entry shape RE-092 proved is
            replace-by-omission, and the corpse answered further hits with
            live damage numbers.  Re-entering a scene now looks exactly like
            never having left it, deaths included -- the same state an
            in-scene kill already leaves behind today.
            """
            scene_id = self.foundation.selected.position.scene_id
            folder = world_scene_folder.scene_folder_for_scene_id(scene_id)
            if folder is None:
                return None
            roster = (
                field_mobs.load_roster(folder)
                if folder in field_mobs.live_scenes()
                else ()
            )
            if folder != self.mob_combat_scene_folder:
                # LANE-B CORE-REQUEST 20260829_1955 item (3), COO 20:41:
                # an addressed scene with no mob table gives an EMPTY
                # roster, and open_ledger cannot derive a scene tag from
                # zero rows -- scene= declares it, and open_ledger joins
                # the declaration against what the rows say, so a
                # contradiction refuses instead of mislabeling.
                ledger = mob_combat.open_ledger(roster, scene=folder)
                ledger_identities = ledger.identities()
                for record in self.mob_death_register.records:
                    # record.scene is the mob's own table tag, which IS the
                    # folder name (each table module's SCENE constant), so
                    # this comparison never crosses the model_id spelling
                    # trap.  The identity guard keeps a record from outside
                    # this roster (a diag object's, or a shrunken future
                    # table's) from raising out of balance_of here.
                    if (
                        record.scene == folder
                        and record.actor_identity in ledger_identities
                    ):
                        ledger = ledger.with_balance(mob_combat.MobBalance(
                            record.actor_identity,
                            ledger.balance_of(record.actor_identity).max_hp,
                            0,
                        ))
                self.mob_combat_ledger = ledger
                self.mob_ai_register = mob_ai_control.open_register(
                    roster, epoch=0,
                )
                self.mob_combat_scene_folder = folder
            return roster

        def _dispatch_mob_combat(self, parsed):
            """MOB-COMBAT-001 / MOB-DEATH-001, wired the way each module's
            own docstring asks: see ``mob_combat.MOB_COMBAT_WIRING`` and
            ``mob_death.MOB_DEATH_WIRING`` for the exact sequence this method
            follows -- the sequence is not invented here, only followed.

            UNCONDITIONAL, called ADDITIVELY (see ``_dispatch_with_lanes``,
            which calls this only after every earlier, more specific branch
            -- including every scenario-gated EA7D reader -- has had first
            claim on the frame, and only alongside the inherited dispatch and
            every other unconditional tail lane, never instead of them).  No
            scenario flag gates this method and it does not call
            ``self.rx_frames += 1`` itself: the frame already passed through
            ``super().dispatch(parsed)`` by the time this runs, which already
            counted it once.

            NOT PROVEN: whether a real attack input produces the exact
            ActionVital shape this reads.  Both modules say so already and
            this method repeats nothing new about it -- see
            MOB_COMBAT_NONCLAIMS and MOB_DEATH_NONCLAIMS.
            """
            try:
                fields = legacy.parse_action_vital(parsed)
            except (ValueError, struct.error) as error:
                self.events.append(
                    "mob_combat_action_vital_parse_error_no_reply_"
                    f"{type(error).__name__}"
                )
                return []
            if self.foundation.selected is None:
                self.events.append("mob_combat_no_selected_no_reply")
                return []
            selected = self.foundation.selected
            performer = (
                ((selected.identity_hi & 0xFFFFFFFF) << 32)
                | (selected.identity_lo & 0xFFFFFFFF)
            )
            target = fields.get("field_qword_20")
            if type(target) is not int or target <= 0 or target == performer:
                self.events.append(
                    "mob_combat_target_not_positive_or_self_no_reply"
                )
                return []
            # COO-DECISION 2026-08-29T08:48+07:00 item 3: the roster is the
            # SELECTED SCENE's own, and an unaddressed scene id ships no
            # roster -- refused HERE, before the diag widen, the cadence
            # gate, or any ledger step composes a verdict of its own.
            roster = self._sync_combat_scene_state()
            if roster is None:
                self.events.append(
                    "mob_combat_scene_"
                    f"{self.foundation.selected.position.scene_id}"
                    "_unaddressed_no_roster_no_reply"
                )
                return []
            # CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001), point (2) of
            # GT_DIAG_MULTI_OBJECT_WIRING.  Off (self.diag_multi_objects ==
            # ()) this returns roster/self.mob_combat_ledger untouched.
            roster, self.mob_combat_ledger, diag_widen_refusal = (
                diag_multi_object_wiring.widen_for_combat(
                    roster, self.mob_combat_ledger, self.diag_multi_objects,
                )
            )
            if diag_widen_refusal is not None:
                self.events.append(diag_widen_refusal)
            # CORE-REQUEST (LANE-B, 20260828_0337): MOB_COMBAT_CADENCE_WIRING.
            # DEVIATION from the letter's literal recipe, found and fixed by
            # pf-adversary before push: the recipe said to gate every inbound
            # ActionVital unconditionally, but EA7D/ActionVital is a generic
            # "action on a target" shape (mob_combat.py's own
            # MOB_COMBAT_NONCLAIMS #1 -- the inbound half is unproven), not an
            # attack-specific one, and this roster already resolves who a
            # real hit could land on. Gating unconditionally meant an
            # ActionVital at a NON-monster target (a townsperson, another
            # player, anything not in ``roster``) silently spent the
            # performer's cadence window before ``attack_from_observed_
            # action`` ever got to say "not a field mob" -- reproduced: a
            # click on a non-monster at t=0 caused a genuine first attack on
            # a real monster 200ms later to be rejected as "cadence too
            # soon", even though no damage-bearing attack had happened yet.
            # Gate only when the target actually resolves to a roster member
            # -- the same membership test attack_from_observed_action itself
            # runs a few lines below -- so a miss-click never taxes the
            # window a real attack needs.  at_ms_wallclock is a reading this
            # method takes itself, once, per dispatch (mob_combat.py owns no
            # clock of its own, matching NOTHING IS INSTALLED there).
            target_is_field_mob = any(
                mob.actor_identity == target for mob in roster
            )
            # RE-157 job 2 / MOB-COMBAT-001: a target in the STATIC roster
            # is not enough -- it must also have been ANNOUNCED to THIS
            # session's own client, in the current scene and the current
            # census generation, via a committed census frame.  Fail
            # closed (mob_combat_membership.admits() never raises; it
            # returns False on any mismatch or missing record), before
            # cadence is spent or the ledger is touched, so a forged or
            # desynced ActionVital against a real roster member the
            # client was never told about cannot mutate combat state.
            if target_is_field_mob and not mob_combat_membership.admits(
                self.mob_combat_announced_membership,
                scene_id=self.foundation.selected.position.scene_id,
                actor_identity=target,
                generation=self.mob_combat_announced_membership_generation,
            ):
                self.events.append(
                    "mob_combat_target_not_announced_no_reply"
                )
                return []
            if target_is_field_mob:
                at_ms_wallclock = int(monotonic_clock() * 1000)
                cadence_check = mob_combat.check_attack_cadence(
                    self.mob_combat_cadence, performer, at_ms_wallclock,
                )
                if not cadence_check.accepted:
                    for line in mob_combat.describe_cadence_rejection(
                        cadence_check
                    ):
                        print(line)
                    self.events.append(
                        "mob_combat_cadence_rejected_no_reply"
                    )
                    return []
                self.mob_combat_cadence = cadence_check.cadence
            for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):
                try:
                    step = mob_combat.attack_from_observed_action(
                        legacy, None, self.mob_combat_ledger, None, fields,
                        performer, MOB_COMBAT_DEFAULT_ATTACKER, roster=roster,
                    )
                except mob_combat.MobCombatContractError as error:
                    self.events.append(
                        f"mob_combat_refused_{error.reason}_no_reply"
                    )
                    return []
                if step is None:
                    self.events.append(
                        "mob_combat_target_not_a_field_mob_no_reply"
                    )
                    return []
                try:
                    self.mob_combat_ledger = mob_combat.commit_step(
                        self.mob_combat_ledger, step,
                    )
                except mob_combat.MobCombatContractError as error:
                    if error.reason == mob_combat.REFUSE_LEDGER_STALE:
                        # Per-session ledger (see __init__): this retry is
                        # unreachable today because one dispatch call runs to
                        # completion before the next one on this connection
                        # can start.  Kept because MOB_COMBAT_WIRING requires
                        # it and a server-wide ledger would make it reachable.
                        continue
                    raise
                break
            else:
                self.events.append(
                    "mob_combat_ledger_stale_retry_limit_exceeded_no_reply"
                )
                return []
            # CORE-REQUEST-007 (MOB-AI-CONTROL-001), step (1) of
            # MOB_AI_CONTROL_WIRING: fold the accepted hit into the threat
            # table AFTER mob_combat.commit_step above, never before -- see
            # the module header for why the ordering matters.  No frame is
            # composed here (see MOB_AI_CONTROL_NONCLAIMS #2); a refusal to
            # commit degrades to "no threat update this hit", never to
            # unwinding the combat ledger commit that already succeeded.
            if self.mob_ai_register.is_tracked(step.outcome.target_identity):
                for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):
                    ai_damage_step = mob_ai_control.damage_step(
                        self.mob_ai_register, step.outcome,
                    )
                    try:
                        self.mob_ai_register = mob_ai_control.commit_step(
                            self.mob_ai_register, ai_damage_step,
                        )
                    except mob_ai_control.MobAiControlError as error:
                        if error.reason == mob_ai_control.REFUSE_REGISTER_STALE:
                            # Same per-session caveat as the combat-ledger
                            # retry above: unreachable today, kept because
                            # MOB_AI_CONTROL_WIRING requires the loop.
                            continue
                        raise
                    break
                else:
                    self.events.append(
                        "mob_ai_control_damage_register_stale_retry_limit_"
                        "exceeded"
                    )
            else:
                # WIRING step (1)'s own guard: the AI register and the
                # combat ledger are opened from the same roster today but
                # nothing in code couples them, so an untracked target would
                # otherwise raise REFUSE_NOT_TRACKED after the combat frames
                # above are already composed.  Not reachable today (same
                # roster, same session) but the guard costs nothing to keep.
                self.events.append(
                    "mob_ai_control_damage_target_not_tracked_skipped"
                )
            self.mob_combat_hit_count += 1
            for line in mob_combat.describe_step(step):
                print(line)
            actions = []
            if step.frames:
                actions.append((
                    "MOB_COMBAT_ANNOUNCE", step.announce_pc,
                    step.announce_frame, 0.0,
                ))
                if len(step.frames) > 1:
                    # CORE-REQUEST-008 (LANE-B, mob_death.hostile_census_
                    # frames): RE-092 proved the client's remote-actor
                    # consumer is replace-by-omission, so the one-entry
                    # ``step.bar_pc``/``step.bar_frame`` this lane still
                    # returns would wipe the whole town off the client's
                    # registry on the first hit if sent as-is. Recompose the
                    # bar frame over the FULL arrival census instead, same
                    # encoder, same anchor/count the arrival wiring already
                    # keeps in session state.
                    # CORE-REQUEST (LANE-B 20260829_2055): the recompose is
                    # SCENE-DISPATCHED through mob_scene_recompose, which
                    # delegates scene 1 byte-identically to the
                    # ``hostile_census_frames`` call that used to sit here
                    # (pinned in tests/test_mob_scene_recompose.py) and adds
                    # scene 2.  pf-adversary finding 2 (anchor/count do not
                    # say which scene they describe) is now closed in the
                    # DATA: ``census_anchor_record`` carries the scene it
                    # was measured in, and recompose_frames refuses a bare
                    # pair outright.  The current-scene comparison is KEPT
                    # -- generalized from ``== world_population.SCENE_ID``
                    # to ``== record.scene_id`` -- because the stamp says
                    # where the anchor was measured, not where the player
                    # stands now: a hit after a crossing whose arrival
                    # census refused must degrade to the one-entry frame,
                    # not recompose the previous map into this one.
                    anchor_record = getattr(
                        self, "census_anchor_record", None,
                    )
                    count = (
                        anchor_record.actor_count
                        if anchor_record is not None else None
                    )
                    census_scene_id = (
                        self.foundation.selected.position.scene_id
                        if self.foundation.selected is not None else None
                    )
                    if (
                        anchor_record is not None
                        and census_scene_id == anchor_record.scene_id
                    ):
                        # The five diagnostic objects are bg0001 placements
                        # (the module refuses them for any other scene by
                        # name); passing them conditionally keeps a
                        # scene-2 recompose composable in a session that
                        # committed them at a scene-1 arrival earlier.
                        recompose_record = (
                            mob_scene_recompose.recompose_frames(
                                legacy, anchor_record,
                                self.mob_death_register,
                                ledger=self.mob_combat_ledger,
                                roster=roster,
                                objects=(
                                    self.diag_multi_objects
                                    if anchor_record.scene_id
                                    == world_population.SCENE_ID else ()
                                ),
                            )
                        )
                        # The lane's wiring ask, point (3): the module's
                        # own line prints in every state a RECOMPOSE can
                        # return, composed or refused.
                        # HONEST LIMIT (pf-adversary, round k882hm, D4):
                        # this is inside the anchor guard, so the arm
                        # below -- no stamp, or a stamp from another
                        # scene -- still ships a one-entry frame with NO
                        # MOB_SCENE_RECOMPOSE line.  It is not silent
                        # (MOB_COMBAT_BAR_CENSUS_RECOMPOSE prints
                        # wire_actors=1 for it, outside every if), but the
                        # module's own line is absent from exactly the
                        # state the lane demanded it for.  Closing that
                        # needs a record for "no anchor", which is the
                        # lane's type to define, not this file's to
                        # invent; asked for in the round letter.
                        for line in mob_scene_recompose.describe_recompose(
                            recompose_record,
                        ):
                            print(line)
                        if recompose_record.composed:
                            bar_pc, bar_frame = (
                                recompose_record.pc, recompose_record.frame,
                            )
                        else:
                            # Every non-composed state degrades to the
                            # one-entry frame, exactly as the old except
                            # arm did.  THE EVENT NAME KEEPS ONE OF THE TWO
                            # OLD PREFIXES, always: pf-adversary (round
                            # k882hm, D6) measured that
                            # tests/test_mob_combat_dispatch.py:602 asserts
                            # no event starts with ``..._skipped_`` or
                            # ``..._refused_``, so a bare ``state`` of
                            # ``no_composer_for_scene`` would pass that
                            # assertion while the one-entry world-wipe
                            # frame is on the wire.  ``refused_*`` states
                            # keep their exact old spelling
                            # (``refused_<Exception>``); every other
                            # non-composed state is a skip and is named
                            # like one.
                            bar_pc, bar_frame = step.bar_pc, step.bar_frame
                            self.events.append(
                                "mob_combat_bar_census_compose_"
                                + _recompose_event_suffix(recompose_record)
                            )
                    else:
                        # Reached in ordinary play, not merely in theory:
                        # pf-adversary (round keen-pasteur-ahn7zb) ran this
                        # branch directly by attacking before any TargetPos
                        # report reaches the server -- foundation.selected
                        # is set at character selection, independent of the
                        # teleport_sent/runtime_ack_sent/last_target_pos
                        # gate the arrival census waits on. A real client
                        # that swings before its first position report, or
                        # one standing in a scene whose arrival census
                        # never committed a stamp, both land here. Degrade
                        # to the one-entry frame RE-092 flagged rather
                        # than recompose against a missing or
                        # wrong-scene anchor.
                        bar_pc, bar_frame = step.bar_pc, step.bar_frame
                        self.events.append(
                            "mob_combat_bar_census_compose_skipped_"
                            "no_population_anchor"
                        )
                    # COO's console gate (2026-08-27 03:45): a grep-able
                    # line proving which collection this hit put on the
                    # wire, same convention as
                    # MOB_DEATH_ROSTER_OVERRIDE_COVERAGE for arrival.  The
                    # token and the ``actor_count=`` field are UNCHANGED
                    # (ROUND z096sw, LANE B, the one edit to this block the
                    # lane's charter reserves for the world-wipe item), so
                    # every existing grep, ticket line and runbook keeps
                    # matching; ``wire_actors=`` is added beside it, read
                    # back off the composed collection's own header after
                    # checking the frame is this pc's frame.
                    #
                    # PRINTED OUTSIDE THE `if` AND OUTSIDE THE `try`, WHICH
                    # IS THE WHOLE POINT, and the first draft of this round
                    # got it wrong in exactly the way this file already
                    # warns about a few hundred lines below ("Printed
                    # OUTSIDE the `if` on purpose ... because 'no line' is
                    # the state GT-084 already mis-read once").
                    #
                    # pf-adversary, this round, MEASURED: with the print
                    # inside the success branch, the two FALLBACK paths --
                    # a compose that raised, and the no-anchor path this
                    # file's own comment says is "reached in ordinary
                    # play" -- put the one-entry frame on the wire (171
                    # bytes against arrival's 20112, header declaring 1
                    # actor, 107 of 108 arrival actors absent) and the
                    # console said NOTHING.  That frame IS the world wipe
                    # RE-092 proved is replace-by-omission, and it was the
                    # one state with no line.  `state.events` is never
                    # printed anywhere in this tree (276 appends, zero
                    # prints), so silence was the only signal.
                    #
                    # Printed here, the fallback prints `wire_actors=1`
                    # against `actor_count=108` -- and that gap is the ONLY
                    # way this line can ever disagree with itself on a
                    # production path, which makes it the reading that
                    # matters.  See the round record for why the
                    # compose-succeeded case cannot differ.
                    print(
                        mob_census_wire_count.describe_census_recompose(
                            legacy,
                            "MOB_COMBAT_BAR_CENSUS_RECOMPOSE",
                            bar_pc, bar_frame,
                            target_identity=step.outcome.target_identity,
                            input_count=count,
                        )
                    )
                    actions.append(("MOB_COMBAT_BAR", bar_pc, bar_frame, 0.0))
            if step.death_due:
                # attack_from_observed_action already matched ``target``
                # against this same roster, so it is here.
                mob = next(m for m in roster if m.actor_identity == target)
                death_step = None
                # CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001), point (3) of
                # GT_DIAG_MULTI_OBJECT_WIRING: dispatch by obj.label, not by
                # the bg0001 COO-RULING widened above.  diag_object_for
                # returns None for every real census identity, so an
                # ordinary bg0001 kill falls straight to the unchanged
                # retry loop in the else branch below.
                diag_obj = diag_multi_object_wiring.diag_object_for(
                    self.diag_multi_objects, target,
                )
                if diag_obj is not None:
                    dispatch = diag_multi_object_wiring.death_dispatch(
                        legacy, diag_obj, step.outcome, self.mob_death_register,
                    )
                    self.events.append(dispatch.event)
                    if dispatch.step is not None:
                        try:
                            self.mob_death_register = mob_death.commit_death(
                                self.mob_death_register, dispatch.step,
                            )
                        except mob_death.MobDeathContractError as error:
                            # Same per-session caveat as the ledger/register
                            # retries below: not reachable today.  Refuse by
                            # name rather than send frames for a death this
                            # session did not record.
                            self.events.append(
                                "diag_multi_object_commit_refused_"
                                f"{error.reason}"
                            )
                        else:
                            death_step = dispatch.step
                else:
                    for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):
                        try:
                            candidate = mob_death.kill(
                                legacy, mob, step.outcome,
                                self.mob_death_register,
                                # COO-DECISION 2026-08-29T08:48+07:00 item 3:
                                # the ONE letter that authorises killing THIS
                                # mob, derived from the registered rulings
                                # (narrower template set first, tie to the
                                # older letter, per that decision's item 1)
                                # instead of a per-scene literal that was the
                                # wrong letter for every Bg0002 row and would
                                # be wrong again for a third scene.  kill()'s
                                # own gate is not widened by one byte: this
                                # only selects among letters that already
                                # cover the mob, and returns None for the
                                # sanctioned first target, which kill()
                                # admits with no ruling at all.
                                widened=mob_death.ruling_for(mob),
                            )
                        except mob_death.MobDeathContractError as error:
                            # Honest degradation, not a bug.  A mob no
                            # registered owner letter covers refuses here --
                            # as a raise from ruling_for itself, thrown while
                            # the arguments are evaluated and before kill()
                            # is ever entered, caught by this same except
                            # (ruling_for returns None ONLY for the
                            # sanctioned first target, which kill() admits
                            # with no ruling; for an uncovered mob it raises,
                            # it does not return None -- pf-adversary, this
                            # round, D4).  The mob stays at 0 HP with no
                            # death frames and answers further hits with
                            # silence (mob_combat's own no_room path) -- the
                            # pre-death-half state this project already
                            # shipped and disclosed, not a new one.  What a
                            # boot's letters DO cover is printed at census
                            # time by mob_death.describe_widening_coverage(),
                            # so an uncovered scene is seen at boot, not in
                            # front of a tester.
                            self.events.append(
                                f"mob_death_refused_{error.reason}_"
                                "no_death_frames"
                            )
                            break
                        try:
                            self.mob_death_register = mob_death.commit_death(
                                self.mob_death_register, candidate,
                            )
                        except mob_death.MobDeathContractError as error:
                            if error.reason == mob_death.REFUSE_REGISTER_STALE:
                                # Same per-session caveat as the ledger retry
                                # above: unreachable today, kept for the contract.
                                continue
                            raise
                        death_step = candidate
                        break
                    else:
                        self.events.append(
                            "mob_death_register_stale_retry_limit_exceeded_"
                            "no_death_frames"
                        )
                if death_step is not None:
                    self.mob_combat_kill_count += 1
                    # CORE-REQUEST-007, step (2) of MOB_AI_CONTROL_WIRING:
                    # retire the AI row AFTER mob_death.commit_death above is
                    # accepted, on ``step.outcome`` -- the mob_combat step's
                    # outcome, NOT death_step's own record, exactly as the
                    # wiring text names it.  LOOP ON REFUSE_REGISTER_STALE
                    # exactly as the damage_step call above: a driver that
                    # gives up here leaves a corpse in the death register and
                    # an IDLE row with live threat in this one, forever.
                    if self.mob_ai_register.is_tracked(
                        step.outcome.target_identity
                    ):
                        for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):
                            ai_death_step = mob_ai_control.death_step(
                                self.mob_ai_register, step.outcome,
                            )
                            try:
                                self.mob_ai_register = (
                                    mob_ai_control.commit_step(
                                        self.mob_ai_register, ai_death_step,
                                    )
                                )
                            except mob_ai_control.MobAiControlError as error:
                                if (
                                    error.reason
                                    == mob_ai_control.REFUSE_REGISTER_STALE
                                ):
                                    continue
                                raise
                            break
                        else:
                            self.events.append(
                                "mob_ai_control_death_register_stale_"
                                "retry_limit_exceeded"
                            )
                    else:
                        self.events.append(
                            "mob_ai_control_death_target_not_tracked_"
                            "skipped"
                        )
                    for line in mob_death.describe_death(death_step):
                        print(line)
                    # CORE-REQUEST-008 (LANE-B, mob_death.hostile_census_
                    # frames), same reasoning as MOB_COMBAT_BAR above: the
                    # one-entry ``death_step.dying_*``/``dead_*`` frames this
                    # lane still returns are the same replace-by-omission
                    # risk RE-092 proved, so recompose both over the full
                    # census. ``self.mob_death_register`` is already the
                    # POST-commit register (mob_death.commit_death ran
                    # above), matching CORE-REQUEST-008 point (2)/(3)'s
                    # "register after commit" requirement.
                    # CORE-REQUEST (LANE-B 20260829_2055): scene-dispatched
                    # recompose, same shape and same reasoning as
                    # MOB_COMBAT_BAR above -- scene 1 delegates
                    # byte-identically to the calls that used to sit here,
                    # scene 2 stops falling to the one-entry frames.
                    anchor_record = getattr(
                        self, "census_anchor_record", None,
                    )
                    count = (
                        anchor_record.actor_count
                        if anchor_record is not None else None
                    )
                    census_scene_id = (
                        self.foundation.selected.position.scene_id
                        if self.foundation.selected is not None else None
                    )
                    if (
                        anchor_record is not None
                        and census_scene_id == anchor_record.scene_id
                    ):
                        death_objects = (
                            self.diag_multi_objects
                            if anchor_record.scene_id
                            == world_population.SCENE_ID else ()
                        )
                        recompose_dying = (
                            mob_scene_recompose.recompose_frames(
                                legacy, anchor_record,
                                self.mob_death_register,
                                ledger=self.mob_combat_ledger,
                                roster=roster,
                                dead_timer=mob_death.DYING_TIMER_SECONDS,
                                objects=death_objects,
                            )
                        )
                        recompose_dead = (
                            mob_scene_recompose.recompose_frames(
                                legacy, anchor_record,
                                self.mob_death_register,
                                ledger=self.mob_combat_ledger,
                                roster=roster,
                                objects=death_objects,
                            )
                        )
                        # Point (3) of the wiring ask: the module's line
                        # prints in every state.  Both records are
                        # described because the two composes are separate
                        # calls (same reasoning as the two RECOMPOSE
                        # console lines below).
                        for recompose_record in (
                            recompose_dying, recompose_dead,
                        ):
                            for line in (
                                mob_scene_recompose.describe_recompose(
                                    recompose_record,
                                )
                            ):
                                print(line)
                        if (
                            recompose_dying.composed
                            and recompose_dead.composed
                        ):
                            dying_pc, dying_frame = (
                                recompose_dying.pc, recompose_dying.frame,
                            )
                            dead_pc, dead_frame = (
                                recompose_dead.pc, recompose_dead.frame,
                            )
                        else:
                            # Either compose refusing degrades BOTH pairs,
                            # exactly as the old shared except arm did: a
                            # dying frame from one collection and a dead
                            # frame from another must never interleave.
                            dying_pc, dying_frame = (
                                death_step.dying_pc, death_step.dying_frame,
                            )
                            dead_pc, dead_frame = (
                                death_step.dead_pc, death_step.dead_frame,
                            )
                            failed = (
                                recompose_dying
                                if not recompose_dying.composed
                                else recompose_dead
                            )
                            self.events.append(
                                "mob_death_frames_census_compose_"
                                + _recompose_event_suffix(failed)
                            )
                    else:
                        # Reached in ordinary play, not merely in theory --
                        # same reasoning as MOB_COMBAT_BAR above
                        # (pf-adversary finding 3): a kill before the
                        # first TargetPos report, or one in a scene whose
                        # arrival census never committed a stamp, both
                        # land here. Degrade to the one-entry frames
                        # rather than recompose against a missing or
                        # wrong-scene anchor.
                        dying_pc, dying_frame = (
                            death_step.dying_pc, death_step.dying_frame,
                        )
                        dead_pc, dead_frame = (
                            death_step.dead_pc, death_step.dead_frame,
                        )
                        self.events.append(
                            "mob_death_frames_census_compose_skipped_"
                            "no_population_anchor"
                        )
                    # OUTSIDE the `if` and OUTSIDE the `try`, for the same
                    # reason spelled out at MOB_COMBAT_BAR above: the two
                    # fallback paths are the ones that put a one-entry
                    # frame on the wire, and they were the two with no
                    # console line at all.  Both pairs are reported: the
                    # DEAD pair is what a tester greps to ask whether the
                    # world survived the kill, and the DYING pair is
                    # reported separately because the two are composed by
                    # separate calls -- what that second line can actually
                    # catch is a pc and a frame that came apart (round
                    # z096sw mutant M6), NOT a different count, since the
                    # two composes differ only in dead_timer and cannot
                    # disagree on how many entries they carry.
                    for token, pc_, frame_ in (
                        ("MOB_DEATH_FRAMES_CENSUS_RECOMPOSE_DYING",
                         dying_pc, dying_frame),
                        ("MOB_DEATH_FRAMES_CENSUS_RECOMPOSE",
                         dead_pc, dead_frame),
                    ):
                        print(
                            mob_census_wire_count.describe_census_recompose(
                                legacy, token, pc_, frame_,
                                target_identity=(
                                    death_step.record.actor_identity),
                                input_count=count,
                            )
                        )
                    actions.append((
                        "MOB_DEATH_DYING", dying_pc, dying_frame, 0.0,
                    ))
                    actions.append((
                        "MOB_DEATH_DEAD", dead_pc, dead_frame,
                        death_step.hold_ms / 1000.0,
                    ))
                    # CORE-REQUEST-007 (MOB-LOOT-001), MOB_LOOT_WIRING: one
                    # call AFTER the whole death schedule above (including
                    # hold_ms), never between the dying and dead frames --
                    # the module header says no derived-mask-0x08 RuntimeRes
                    # may interleave into another lane's typed lethal
                    # sequence for the same actor.  roll_drops is called
                    # ONCE: commit_drops's own docstring forbids re-rolling
                    # on a retry ("do NOT re-roll, that would give one kill
                    # two rolls"), so the retry loop below retries
                    # loot_a_kill against the SAME roll, exactly like the
                    # ledger/register retries above retry the SAME
                    # step/candidate.
                    roll = mob_loot.roll_drops(mob, self.mob_loot_rng)
                    drops = ()
                    for _attempt in range(MOB_COMBAT_STALE_RETRY_LIMIT):
                        try:
                            drops = self.mob_loot_cell.loot_a_kill(
                                mob, death_step.record, roll,
                                kill_token=death_step.register.generation,
                                position=None,
                            )
                        except mob_loot.MobLootContractError as error:
                            if error.args[0] in (
                                mob_loot.REFUSE_LEDGER_GENERATION_MOVED,
                                mob_loot.REFUSE_LEDGER_STALE,
                            ):
                                # Same per-session-cell caveat as the
                                # combat-ledger/AI-register retries above:
                                # unreachable today (one cell, one lock, no
                                # concurrent mutator on this session), kept
                                # because MOB_LOOT_WIRING requires the loop.
                                drops = ()
                                continue
                            if (
                                error.args[0]
                                == mob_loot.REFUSE_MOB_ALREADY_LOOTED
                            ):
                                # Do NOT retry: this death was already
                                # looted (a replay), per MOB_LOOT_WIRING.
                                self.events.append(
                                    "mob_loot_refused_mob_already_looted_"
                                    "no_retry"
                                )
                                drops = ()
                                break
                            raise
                        break
                    else:
                        self.events.append(
                            "mob_loot_ledger_stale_retry_limit_exceeded_"
                            "no_drops"
                        )
                        drops = ()
                    # CORE-REQUEST 2246 (lane B, COO 2026-08-29T23:42): the
                    # generation is the WHOLE live ledger per kill (shape
                    # 4b), so no `if drops:` guard -- a kill that drops
                    # nothing must still re-announce the rows already on
                    # the ground, or the client registry loses them.  The
                    # old prune-after-announce loop is deleted, not
                    # replaced: expiry-per-row plus sustain_a_kill's own
                    # trim are the only bounds (no prune_previous_kills --
                    # it would delete rows still inside their 120s life).
                    step = mob_drop_presence.sustain_a_kill(
                        self.mob_loot_cell, legacy, drops)
                    print(mob_loot.drops_console_line(mob, drops))
                    print(mob_drop_presence.describe_presence(step))
                    actions.extend(mob_drop_presence.loot_actions(step))
                    self.events.append(
                        mob_drop_presence.presence_event(step))
            return actions

        def _dispatch_columbus_quest3021(self, parsed):
            """CORE-REQUEST-014: Columbus (MOBS n_ID 156, bg0001 placement
            index 1) NPCConversation -> QuestOperateVital op1/quest 3021.

            CORE-REQUEST-019 (Lane A, 2026-08-27T18:48+07:00) added a second
            quest to this same method despite the name: the ``ChooseNPC``
            branch below now composes a two-option conversation (3021 AND
            quest 3205 / Q_BORNAGAIN), and the ``QuestOperateVital`` branch
            gained its own parallel ``elif`` for op1/3205, with its own
            independent per-session latch
            (``columbus_quest3205_dispatch_attempted``) -- see
            ``columbus_quest_dispatch.dispatch_columbus_quest3205`` for why
            that half always refuses today. pf-adversary-flagged
            (round n2ws3l): widening the outer gate to
            ``not attempted3021 or not attempted3205`` means a session that
            completes 3021 but never deliberately triggers 3205 keeps
            parsing and checking every later ``QuestOperateVital`` frame
            (any quest) for the rest of that session, instead of the single
            early exit the pre-widening gate gave 3021 alone -- accepted
            for now (no wrong output, not client-visible, cost is one parse
            plus two dict-key checks per frame), not decoupled this round.

            UNCONDITIONAL and ADDITIVE, the same convention as
            ``_dispatch_mob_combat`` above: no scenario flag gates this, and
            it is called on every frame whose ``nested_id`` it cares about,
            after every earlier, more specific branch has already had first
            claim.  See ``columbus_quest_dispatch``'s module docstring for
            the full evidence trail -- RE-094 for the generic NPCConversation/
            QuestOperateVital wire shape this reuses, RE-085/RE-096 and
            ``scenarios/world_scene_registry_001.json`` for why the compound
            bind-vehicle-then-teleport action refuses every time it is
            reached today.  Both refusals are genuine, currently-open data
            gaps, not something this method papers over.

            PF-ADVERSARY FINDING, round 4txjyg (R192): the first draft called
            ``dispatch_columbus_quest3021`` without ``registry=``, which left
            ``resolve_entry`` re-reading and re-validating
            ``scenarios/world_scene_registry_001.json`` from disk on every
            attempt instead of using the SAME boot-loaded
            ``scene_entry_registry`` the login path above already threads
            through (see ``resolve_entry``'s own docstring on why that
            matters: a malformed pin belongs at boot, in front of an
            operator, not as an uncaught exception on a live player's
            connection).  Fixed by passing ``registry=scene_entry_registry``
            below, the same closure variable the login call site at
            ``runtime.py:4657`` already uses.

            THE CENSUS-MEMBERSHIP GATE ON THE FIRST BRANCH IS LOAD-BEARING,
            NOT DEFENSIVE.  ``self.population_indices`` is the same set
            ``v141:4409``'s inherited ChooseNPC handler already requires
            (``tests/test_world_census_wiring.py::...ignores_composes_
            nothing`` pins the invariant this follows: a ChooseNPC for an
            actor identity the arrival census never armed must compose
            nothing).  Answering a click for an NPC the client was never told
            about would be responding to an actor nobody's screen has -
            evidence the client rendered Columbus at all is exactly what
            ``population_indices`` recording placement index 1 already is.
            """
            nested_id = parsed.nested_id
            actions = []
            if (
                nested_id in (legacy.TARGET_VITAL, legacy.CHOOSE_NPC)
                and not self.columbus_quest3021_conversation_sent
                and self.population_indices is not None
                and columbus_quest_dispatch.COLUMBUS_PLACEMENT_INDEX
                in self.population_indices
            ):
                try:
                    chosen = legacy.extract_choose_npc_identities(parsed)
                except Exception as error:
                    self.events.append(
                        "columbus_choose_npc_parse_error_"
                        f"{type(error).__name__}"
                    )
                    return actions
                try:
                    columbus_identity = (
                        columbus_quest_dispatch.columbus_actor_identity(legacy)
                    )
                except columbus_quest_dispatch.ColumbusActorNotFound as error:
                    self.events.append(
                        f"columbus_actor_not_found_{error}"
                    )
                    return actions
                if columbus_identity in chosen:
                    try:
                        conv_pc, conv_frame = (
                            columbus_quest_dispatch
                            .make_columbus_conversation_two_options(
                                legacy, columbus_identity,
                            )
                        )
                    except Exception as error:
                        self.events.append(
                            "columbus_conversation_compose_refused_"
                            f"{type(error).__name__}"
                        )
                        return actions
                    self.columbus_quest3021_conversation_sent = True
                    self.events.append(
                        "core_request_014_columbus_npc_conversation_sent_once"
                    )
                    actions.append((
                        "CORE_REQUEST_014_COLUMBUS_Q3021_NPC_CONVERSATION_ONCE",
                        conv_pc, conv_frame, 0.0,
                    ))
                return actions
            if (
                nested_id == legacy.QUEST_OPERATE_VITAL
                and self.columbus_quest3021_conversation_sent
                and (
                    not self.columbus_quest3021_dispatch_attempted
                    or not self.columbus_quest3205_dispatch_attempted
                )
            ):
                try:
                    quest_fields = legacy.parse_quest_operate_vital(parsed)
                except Exception as error:
                    self.events.append(
                        "columbus_quest_operate_parse_error_"
                        f"{type(error).__name__}"
                    )
                    return actions
                if (
                    not self.columbus_quest3021_dispatch_attempted
                    and columbus_quest_dispatch.matches_columbus_dispatch(
                        quest_fields,
                    )
                ):
                    self.columbus_quest3021_dispatch_attempted = True
                    # PF-ADVERSARY FINDING, round e0daaa: emit=self.events.
                    # append alone (unlike the LOGIN resolve_entry call
                    # site above, which defaults to emit=print) never
                    # reaches the actual console unless the process was
                    # started with --export-events -- the SAME
                    # SCENE_ENTRY/WORLD_SCENE tokens both PANYA-DECISION
                    # 2026-08-27T14:45+07:00 and GT-106's own pass criteria
                    # require a human to be able to read off the console
                    # would silently never print. Printing AND recording
                    # matches this file's own PLAYER_FACTION convention a
                    # few hundred lines below.
                    def _emit(line):
                        print(line)
                        self.events.append(line)
                    try:
                        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
                            registry=scene_entry_registry,
                            emit=_emit,
                            # CORE-REQUEST (LANE-A 20260829_1422): report-only
                            # kwargs.  With these two, a successful crossing
                            # prints WORLD_POP_STOWAWAYS with the names still
                            # held within radius of the ARRIVAL anchor -- the
                            # point the boat lands (entry.teleport_fields),
                            # in the unmeasured shared-coordinate assumption
                            # stowaways_near itself discloses -- NOT the
                            # departure point (pf-adversary, round qb70g2);
                            # without them the same line prints "unmeasured".
                            # stowaways_on_crossing never raises (its own
                            # contract) and no frame is composed from it.
                            legacy=legacy,
                            held_indices=self.world_census_indices,
                            # CORE-REQUEST (LANE-A 20260829_1546): the third
                            # keyword on this same line -- the SCENE-1 row
                            # this character is standing on at the moment
                            # the crossing is taken.  The in-memory
                            # position is the row last read/written (the
                            # census, the travel gates and
                            # _checkpoint_exact_target all read/update it),
                            # so the printed drift is measured from where
                            # THIS character departed, not from the pinned
                            # new-character spawn.  The scene guard is part
                            # of the contract, not caution: a row already
                            # naming another scene is not a departure from
                            # home, and return_ticket validates a passed
                            # row even when it would not use it, so
                            # handing one over degrades the whole line to
                            # a reason-only "refused:ValueError" stub --
                            # None instead makes it print the full
                            # pinned-home ticket with the named absence
                            # (pf-adversary, this round, D4).  No branch
                            # here can raise: selected is only ever None
                            # or a frozen Character with a total position
                            # field, and dispatch is single-writer.
                            # return_leg_console_line itself never raises
                            # (its own contract) and no frame or row is
                            # composed from it.
                            departed_from=(
                                self.foundation.selected.position
                                if (
                                    self.foundation.selected is not None
                                    and self.foundation.selected.position
                                    .scene_id
                                    == world_scene_travel.HOME_SCENE_ID
                                )
                                else None
                            ),
                            # CORE-REQUEST (LANE-A, round czoo9t): the
                            # one-token flip columbus_quest_dispatch.py's own
                            # docstring names -- unconditional True is safe
                            # AT THIS CALL SITE ONLY because
                            # resolve_columbus_arrival always targets the
                            # fixed COLUMBUS_DEST_SCENE_ID (17) with a
                            # well-formed synthetic Position, so a successful
                            # dispatch here always composes a readable
                            # KIND_CLEAR handoff with sends_a_frame=True
                            # (pf-adversary, this round: confirmed by
                            # reading resolve_columbus_arrival and by a live
                            # probe).  The else-branch below always queues
                            # the frame this promises, in the same edit.
                            crossing_handoff_dispatched=True,
                        )
                    except columbus_quest_dispatch.ColumbusDispatchRefused as error:
                        for reason in error.reasons:
                            self.events.append(
                                f"columbus_quest3021_dispatch_refused_{reason}"
                            )
                    else:
                        # PANYA-DECISION 2026-08-27T15:25+07:00
                        # (M2-NO-VEHICLE-OWNER-20260827-1525): no vehicle
                        # frame -- just the same TeleportVital encoder the
                        # login path already uses (RE-077: proven the
                        # correct wire for moving an ALREADY-LIVE character
                        # too, not just at login).
                        tp_pc, tp_frame = legacy.make_login_teleport(
                            *entry.teleport_fields
                        )
                        # CORE-REQUEST (LANE-A, round czoo9t): this crossing
                        # sent TeleportVital alone -- the actor collection
                        # the client got at login (up to 115 actors;
                        # WORLD_POP_STOWAWAYS and RE-162 Job 4 independently
                        # found the same gap) was still standing in the
                        # water after the player sailed out.
                        #
                        # NO SECOND PRINT HERE (pf-adversary, this round,
                        # caught the first draft doing one): the dispatch
                        # call above already composed and reported this
                        # exact handoff through its own ``emit`` -- printing
                        # AND recording it once, correctly, in
                        # ``self.events`` -- now that
                        # ``crossing_handoff_dispatched=True`` makes that
                        # report true.  A second bare ``print`` here would
                        # bypass ``self.events`` and put a second,
                        # unrecorded line on the console for one crossing.
                        # Composed again here via this lane's own wrapper
                        # (world_m2_crossing_handoff.crossing_handoff, not
                        # the seam directly, so tests/
                        # test_world_population_bg0015.py's one-call-per-
                        # blessed-file census stays satisfied) ONLY to read
                        # back the bytes/slot/reset this block needs to
                        # queue -- composing a 27-byte CLEAR twice costs
                        # nothing today (world_m2_crossing_handoff.py's own
                        # docstring).  Mirrors the travel-gate call site
                        # above (runtime.py:7146) for dispatch_slot and
                        # reapply_ms: read from the handoff, never
                        # hardcoded.
                        handoff = world_m2_crossing_handoff.crossing_handoff(
                            legacy, entry,
                        )
                        crossing_actions = [(
                            "CORE_REQUEST_014_COLUMBUS_Q3021_TELEPORT_SCENE17_ONCE",
                            tp_pc, tp_frame, 0.0,
                        )]
                        if handoff.sends_a_frame:
                            handoff_actions = [(
                                handoff.label, handoff.pc, handoff.frame,
                                0.0,
                            )]
                            if handoff.reapply_ms is not None:
                                handoff_actions.append((
                                    handoff.label + "_REAPPLY",
                                    handoff.pc, handoff.frame,
                                    handoff.reapply_ms / 1000.0,
                                ))
                            if (
                                handoff.dispatch_slot
                                == world_population_handoff
                                .SLOT_BEFORE_TELEPORT
                            ):
                                crossing_actions = (
                                    handoff_actions + crossing_actions
                                )
                            else:
                                crossing_actions = (
                                    crossing_actions + handoff_actions
                                )
                        for action in crossing_actions:
                            actions.append(action)
                        # BOTH frozen-state membership fields together
                        # (MembershipReset's docstring), read AFTER the
                        # handoff is composed above, not before: the
                        # console line and WORLD_POP_STOWAWAYS both report
                        # world_census_indices, and resetting first would
                        # make both print 0 in the boot where they should
                        # report the real count (k882hm-D3).
                        reset = handoff.membership_reset
                        # RE-157 job 2 / LANE-B letter 1838: same gap as
                        # the travel-gate crossing site (this function's
                        # other membership-reset call, above) -- an M2
                        # (Columbus) crossing never touched mob-combat
                        # announced membership either.  Cleared
                        # unconditionally, mirroring
                        # ``_gm_warp_resync_selected_scene``'s own
                        # clear+generation-bump.
                        self.mob_combat_announced_membership = None
                        self.mob_combat_announced_membership_generation += 1
                        self.events.append(
                            "world_m2_crossing_mob_combat_membership_"
                            f"cleared_{handoff.scene_id}"
                        )
                        self.population_indices = reset.population_indices
                        self.population_refresh_anchor = (
                            reset.population_refresh_anchor
                        )
                        self.world_census_indices = (
                            reset.population_indices
                        )
                        self.events.append(
                            "core_request_014_columbus_scene17_teleport_sent"
                        )
                        self.events.append(
                            "world_m2_crossing_handoff_"
                            f"{handoff.kind}_scene_{handoff.scene_id}"
                        )
                elif (
                    not self.columbus_quest3205_dispatch_attempted
                    and columbus_quest_dispatch
                    .matches_columbus_bornagain_dispatch(quest_fields)
                ):
                    # CORE-REQUEST-019 (Lane A, 2026-08-27T18:48+07:00):
                    # option 2 / quest 3205 (Q_BORNAGAIN) -- same emit/
                    # refuse pattern as the 3021 branch above, but this
                    # module's own dispatch_columbus_quest3205 refuses
                    # every time today (no persisted home-marker column,
                    # no captured wire ack -- see the module docstring and
                    # RE-112), so there is deliberately no success branch.
                    self.columbus_quest3205_dispatch_attempted = True

                    def _emit(line):
                        print(line)
                        self.events.append(line)
                    try:
                        columbus_quest_dispatch.dispatch_columbus_quest3205(
                            emit=_emit,
                        )
                    except columbus_quest_dispatch.ColumbusDispatchRefused as error:
                        for reason in error.reasons:
                            self.events.append(
                                f"columbus_quest3205_dispatch_refused_{reason}"
                            )
            return actions

        def dispatch(self, parsed):
            # CORE-REQUEST-GM-030.  Open the confirm window BEFORE the lanes
            # run (the durable write happens inside them) and close it after,
            # so the window lives for exactly one frame: the first TargetPos
            # after a GM warp.  pf-adversary measured what a longer-lived
            # lock does -- the client ignores ForcePos (RE-129: mov al,1;
            # ret 4), so its first report repeats the old point and writes
            # nothing, and a lock that survived that would fire the token on
            # the next frame the tester walked by hand.
            warp_frame = self._gm_warp_open_confirm_window(parsed)
            actions = self._dispatch_with_lanes(parsed)
            # COO-DECISION 20260901_0145 / lane_hooks.lane_b_mob_ai_tick's own
            # LANE_B_MOB_AI_TICK_WIRING (round iok5z1 named this exact block,
            # this round pastes it): the one direct-call site
            # mob_ai_scheduler.tick_session had zero callers for. Guards on
            # the same vital a moving player already sends continuously, so
            # nothing new is composed on frames that are not one. Composes no
            # frame either way (Door B is a separate, larger decision this
            # does not make).
            if (parsed.nested_id == legacy.TARGET_POS_VITAL and
                    self.last_target_pos is not None and
                    getattr(self, "mob_ai_register", None) is not None and
                    getattr(self, "mob_combat_ledger", None) is not None and
                    self.foundation.selected is not None and
                    lane_hooks.module_production_allowed(
                        "lane_hooks.lane_b_mob_ai_tick")):
                selected = self.foundation.selected
                performer = (
                    (selected.identity_hi & 0xFFFFFFFF) << 32
                    | (selected.identity_lo & 0xFFFFFFFF)
                )
                x, y, z, _heading = self.last_target_pos
                self.mob_ai_register, _tick_results = (
                    lane_b_mob_ai_tick.maybe_tick(
                        self.mob_ai_register, self.mob_combat_ledger,
                        performer, (x, y, z),
                    )
                )
            if move_authority_hypothesis_scenario is not None:
                self._move_authority_note_server_moves(actions)
            self._gm_warp_close_confirm_window(warp_frame)
            self._gm_warp_note_position_pending(actions)
            return actions

        def _gm_warp_open_confirm_window(self, parsed) -> bool:
            """CORE-REQUEST-GM-030: this frame is the warp's TargetPos or none is.

            Disarms the pending lock on the first TargetPos that arrives after
            a GM warp, whatever that frame goes on to do.  The token itself is
            printed later, and only if that frame produced a durable write.
            """
            if not self.gm_warp_position_pending:
                return False
            if parsed.nested_id != legacy.TARGET_POS_VITAL:
                return False
            self.gm_warp_position_pending = False
            # CORE-REQUEST-GM-030/031.  Unconditional, on every pass that
            # reaches here -- whatever the character check just below decides
            # -- so a target parked for a character this connection has since
            # switched away from is taken (and therefore cleared) here rather
            # than surviving to leak onto a later, unrelated confirm window.
            record, reason = take_warp_target_with_reason(
                self, current_character_id(self),
            )
            self.gm_warp_confirm_target = record.target if record else None
            self.gm_warp_confirm_target_reason = reason if not record else None
            selected = self.foundation.selected
            if getattr(selected, "id", None) != self.gm_warp_pending_character:
                # The warp was armed for another character (re-select on the
                # same connection).  Disarm and name it: a token here would
                # put one character's warp on another character's row.
                #
                # NONCLAIM (pf-adversary, this round): gm_warp_pending_character
                # and record.character_id are always written from the same
                # `current_character_id(self)` at arm time
                # (chat_command_action.py's call to record_warp_target), so any
                # real re-select that would make take_warp_target_with_reason
                # return REASON_CHARACTER_MISMATCH also trips THIS guard first
                # and returns False before the window (and therefore
                # _gm_warp_note_position_target) ever runs.  That makes the
                # "gm_warp_position_target_unknown_character_mismatch" event in
                # _gm_warp_note_position_target unreachable from any real
                # dispatch path today -- it is proven only by a test that parks
                # a WarpTargetRecord directly, bypassing this call chain.  Left
                # in as defense-in-depth per CORE-REQUEST-GM-031 item 5, not as
                # a claim that this branch fires in production.  See
                # CORE-REQUEST-GM-031 follow-up reply for the guard-order
                # question this raises.
                self.events.append(
                    "gm_warp_position_not_confirmed_character_changed"
                )
                return False
            self.gm_warp_confirm_window_open = True
            return True

        def _gm_warp_close_confirm_window(self, warp_frame) -> None:
            """CORE-REQUEST-GM-030: a warp frame that did not write says so.

            Silence would be indistinguishable from "the wiring is dead", the
            failure GT-128 cannot afford, so the refusal is named on the event
            trail.  No console token: nothing was written.
            """
            if not warp_frame or not self.gm_warp_confirm_window_open:
                return
            self.gm_warp_confirm_window_open = False
            # CORE-REQUEST-GM-030/031: this frame's parked target (if any)
            # was for THIS confirm window, which just closed without a
            # durable write.  Leaving it set would let the next unrelated
            # frame -- one that opens no confirm window at all, because
            # gm_warp_position_pending is already False by now -- read a
            # target that has nothing to do with it (test d's regression).
            self.gm_warp_confirm_target = None
            self.gm_warp_confirm_target_reason = None
            reason = (
                "scene_load_scenario" if scene_load_scenario is not None
                else "no_durable_position_write"
            )
            self.events.append(
                f"gm_warp_position_not_confirmed_{reason}"
            )

        def _gm_warp_note_position_pending(self, actions) -> None:
            """CORE-REQUEST-GM-030: arm the "next TargetPos is the warp's" flag.

            Called UNCONDITIONALLY from dispatch, next to (never inside) the
            move-authority note above: GT-128 boots with no scenario object at
            all, and a flag raised only behind one would never be raised on the
            boot shape the attended test actually uses.

            Keyed on the EXACT GM warp labels (all three: same-scene ForcePos
            plus both cross-scene teleport variants), not on the substring
            TELEPORT that ``_move_authority_note_server_moves`` matches: scene
            entry and the Columbus lane also carry TELEPORT in their labels,
            and a token that fired for those would say "the GM's warp landed"
            about a frame no GM ever typed.

            CORE-REQUEST-GM-047 (pf-adversary, this round): this used to match
            only ``WARP_ACTION_LABEL`` (same-scene ForcePos, which
            ``warp_executor.make_warp_force_pos_frame_with_target`` refuses to
            emit cross-scene in the first place), so neither cross-scene warp
            label ever reached this branch and the resync below never fired
            for a real cross-scene warp -- ``selected.position.scene_id``
            stayed on the OLD scene while the client's x/y/z moved to the new
            one, corrupting the next persisted position row. Both cross-scene
            labels are safe to add here unconditionally:
            ``_gm_warp_resync_selected_scene`` already early-returns when the
            target scene equals the current one, so a same-scene call through
            either cross-scene label (if that ever happened) would be a no-op,
            not a double-resync.
            """
            _GM_WARP_LABELS = (
                chat_command_action.WARP_ACTION_LABEL,
                chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL,
                chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
            )
            for action in actions or ():
                if action and action[0] in _GM_WARP_LABELS:
                    if self.gm_warp_position_pending:
                        # Two warps before one write: the trail must not read
                        # like one warp that armed twice.
                        #
                        # CORE-REQUEST-GM-045 (pf-adversary, this round).
                        # record_warp_target unconditionally overwrites
                        # gm_last_warp_target on every new /warp -- by the
                        # time this branch runs, the record already parked
                        # is the SECOND warp's, not the first's. Skipping the
                        # resync here (as an early draft did) left
                        # selected.position.scene_id stuck on the FIRST
                        # warp's destination for the rest of the chain,
                        # reproducing CORE-REQUEST-GM-045's own measured
                        # symptom one warp later. The pending flag and
                        # character are deliberately NOT re-armed (the
                        # comment above is unchanged, and still true for the
                        # confirm-window/token side of this) -- only the
                        # scene label, which has nothing to do with which
                        # warp gets to open a confirm window.
                        self.events.append("gm_warp_position_pending_rearmed")
                        self._gm_warp_resync_selected_scene(
                            self.foundation.selected,
                        )
                        return
                    selected = self.foundation.selected
                    self.gm_warp_position_pending = True
                    self.gm_warp_pending_character = getattr(selected, "id", None)
                    self.events.append("gm_warp_position_pending_armed")
                    self._gm_warp_resync_selected_scene(selected)
                    return

        def _gm_warp_resync_selected_scene(self, selected) -> None:
            """CORE-REQUEST-GM-045: name the destination scene immediately.

            IN-MEMORY ONLY, the same shape as the login-scene-override resync
            (CORE-REQUEST-GM-033 / CHIEF-DECISION 20260829_0520 option A,
            above in ``dispatch``): a cross-scene warp is queued entirely
            inside ``gm/chat_command_action.py`` without ever touching
            ``runtime.py`` (its own docstring says so -- CORE-REQUEST-GM-045's
            letter quotes it), so nothing before this point has told
            ``self.foundation.selected.position`` it is no longer in the
            departure scene. WORLD-CENSUS-001 (later in this same dispatch)
            reads exactly that field to decide which scene's roster to
            compose -- GT-172 measured it composing the OLD scene's census
            while the client stood in the new one, four times, no exceptions.

            SCENE_ID ONLY, x/y/z/heading untouched, and this is deliberate,
            not an oversight: WORLD-CENSUS-001's anchor comes from
            ``last_target_pos`` (or the destination's own pinned spawn, when
            no TargetPosVital has arrived yet), never from
            ``selected.position``'s coordinates -- see that block's own
            comment. Only the scene label was ever wrong. Leaving x/y/z at
            the departure scene's last known row also keeps
            ``_checkpoint_exact_target``'s own change detection honest: that
            method treats an unchanged ``candidate`` as "nothing to write",
            and the first real TargetPos after a warp is expected to differ
            from the OLD row in x/y at least (RE-129's grace window exists
            for exactly that jump) -- resyncing x/y/z here as well would let
            a report that happens to echo the warp's own target look like no
            movement at all, silently skipping both the durable write and
            CORE-REQUEST-GM-030's own confirm token. Scene alone carries no
            such risk: it is compared as part of the same ``Position``
            equality either way, so a corrected scene_id still shows up as a
            change the moment a real report's x/y differs from the stale row
            (the overwhelmingly common case) and costs nothing when it does
            not.

            No durable write here, on purpose: ``_checkpoint_exact_target``
            still owns that (gated on move authority, the persist-allowed
            table, and the confirm window armed just above), unchanged. This
            only relabels the in-memory row so the very next frame -- the
            census dispatch included -- reads a scene the player is actually
            in, exactly as the override resync already does for a different
            GM entry path.

            Reads the just-parked ``WarpTargetRecord`` without consuming it:
            ``_gm_warp_open_confirm_window`` still needs to ``take`` the same
            record, unclaimed, on the next TargetPos report. Never raises and
            never disarms anything armed above -- a bad record here costs
            only this resync, not the confirm window or the durable write it
            guards.
            """
            try:
                record = getattr(
                    self, GM_WARP_TARGET_SESSION_ATTRIBUTE, None,
                )
            except Exception:  # noqa: BLE001 - see docstring
                return
            if not isinstance(record, WarpTargetRecord):
                return
            target = record.target
            if not isinstance(target, WarpTarget):
                return
            if target.scene_id == selected.position.scene_id:
                # Same-scene warp (the ForcePos form, RE-090): nothing to
                # relabel, and this method is about the cross-scene case.
                return
            self.foundation.selected = replace(
                self.foundation.selected,
                position=replace(selected.position, scene_id=target.scene_id),
            )
            self.events.append(
                f"gm_warp_selected_scene_resynced_{target.scene_id}"
            )
            # KA1A-ROOTCAUSE (20260901_1035): WORLD-CENSUS-001 gates on
            # ``world_census_sent``, initialised once per CONNECTION
            # (construction, above) and never reset -- so every scene after
            # the first one a session's census fires in dispatches a
            # teleport frame and nothing else, silent by construction (the
            # attended round that found this: ten cross-scene warps, two
            # censuses, both the first of their login). Relabelling the
            # scene here without also unlatching the census leaves every
            # later scene of the session permanently empty.
            #
            # Also clear ``last_target_pos`` and the composition state that
            # is keyed off the OLD scene: leaving ``last_target_pos`` set
            # would let the newly-unlatched census use the DEPARTURE
            # scene's coordinates as its anchor (this is F-1 from GT-172
            # arriving through a different door -- measured, not
            # hypothetical: GT-182 session 1 only looked correct because
            # the player had not walked in Port Royal yet, so this field
            # was already None and the anchor fell through to the
            # destination's own pinned spawn). ``population_indices`` and
            # its siblings describe placements in the OLD scene's index
            # space; leaving them set would point the next NPC click frame
            # at the previous map's roster.
            #
            # Deliberately NOT touching the scene-1 walk-before-census
            # disjunct (WORLD-CENSUS-001, later in this dispatch) here --
            # that is a separate, still-unsafe change gated on either
            # ``lane_hooks.lane_a_choose_npc_scene1.production_allowed`` or
            # a deferred ``population_indices`` install (KA1A-AMENDMENT
            # 20260901_1120); this method only fires on an already-armed
            # cross-scene GM warp, never on a fresh login.
            self.world_census_sent = False
            self.world_census_refused = False
            self.last_target_pos = None
            self.population_indices = None
            self.world_census_indices = None
            self.population_refresh_anchor = None
            self.census_anchor_record = None
            self.npc_idle_action_sent = False
            self.world_census_identity_resolved = False
            self.world_census_actor_count = None
            # RE-157 job 2 / MOB-COMBAT-001: the OLD scene's announced
            # membership must not leak into the new scene -- the census
            # that will (re-)build it below has not committed yet, so
            # until it does, ``mob_combat_membership.admits()`` must fail
            # closed for THIS scene too, not silently answer with the
            # departure scene's stale roster.  Clearing to None (rather
            # than a same-scene mismatch) is enough on its own since
            # ``admits()`` refuses a scene mismatch already, but a warp
            # BACK to a scene already visited this session must also be
            # refused until re-announced, which is exactly what bumping
            # the generation counter (never resetting it, so an old
            # generation for the same scene id can never be replayed as
            # current) guarantees.
            self.mob_combat_announced_membership = None
            self.mob_combat_announced_membership_generation += 1
            self.events.append(
                f"gm_warp_cross_scene_census_latch_cleared_{target.scene_id}"
            )

        def _dispatch_with_lanes(self, parsed):
            nested_id = parsed.nested_id
            if logout_hypothesis_scenario is not None and self.logout_acknowledged:
                # After the acknowledged logout (HYP-PF-012 lane below) the
                # lease is closed; every later frame on this connection is
                # counted and ignored so no other lane can write through a
                # closed session.
                self.rx_frames += 1
                self.events.append("logout_hypothesis_post_ack_frame_no_reply")
                return []
            if nested_id == trace_path.TRACE_PATH_REQ_VITAL_ID:
                # CORE-REQUEST-025 (LANE-A, 20260828_0427): the player's GO!
                # click in the map window sends CTracePathReqVital (0x4391)
                # and the server never answered -- client stays stuck on
                # "finding path..." forever (KA1A finding, 20260828_0235).
                # RE-119 (STATIC-ON-BRIDGE, PASS/DONE) proved an empty
                # CTracePathVital (record count=0) makes the client dispatch
                # EndFindPath and clear the stall; scope is empty-vector
                # only -- no waypoint/auto-walk semantics, per the letter's
                # explicit nonclaim (RE-119 T4 leaves the request's own
                # discriminator field bounded negative).
                self.rx_frames += 1
                if self.foundation.selected is None:
                    self.events.append("trace_path_no_selected_no_reply")
                    return []
                pc, frame = trace_path.make_trace_path_empty_response(legacy)
                self.events.append("trace_path_empty_vector_reply")
                return [("TRACE_PATH_EMPTY_VECTOR_REPLY", pc, frame, 0.0)]
            if (
                logout_hypothesis_scenario is not None
                and logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT
                and nested_id == LOGOUT_VITAL_ID
            ):
                # HYP-PF-031 only: the chat-push scenario deliberately does
                # NOT answer LogoutVital -- the lane stays one-question --
                # so the request-paired logout dispatch below must never see
                # this frame under this policy.  Under the four request-
                # paired logout profiles this branch is unreachable and
                # 0x1B40 keeps its pinned dispatch, byte-identical.
                return self._dispatch_logout_chat_push_logout_no_reply(parsed)
            if (
                logout_hypothesis_scenario is not None
                and logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_CHAT_PUSH_RETURN_SELECT
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # HYP-PF-031 only: the chat-input frame is this scenario's
                # TRIGGER.  The logout scenario mode is mutually exclusive
                # with every chat-keyed lane at construction (make_state_class
                # refuses any pair outright and app.py refuses the flags
                # together), so no other lane can see the same frame.
                return self._dispatch_logout_chat_push_hypothesis(parsed)
            if logout_hypothesis_scenario is not None and nested_id == LOGOUT_VITAL_ID:
                return self._dispatch_logout_hypothesis(parsed)
            # PF-HYPOTHESIS-LEDGER: HYP-PF-040 active
            # LOGOUT-DIALOG-OPEN-001.  Registered in
            # docs/HYPOTHESIS_LEDGER.json; this annotation and that entry's
            # source_refs bind each other both ways.
            if (
                logout_hypothesis_scenario is not None
                and logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_WORLDINFO_DIALOG_OPEN_PUSH
                and nested_id == WORLDINFO_VITAL_ID
                and logout_dialog_open_hypothesis.production_allowed
            ):
                # HYP_PF_040 only: this policy owns every 0x3D4B-bearing
                # frame the same way worldinfo_first does, but routes to the
                # dialog-open dispatch (branch 6, RE-189 Job 2) instead of
                # the silent observation path below.  This is a top-level
                # routing branch, not a nested call, so the dispatch
                # function's own unconditional ``self.rx_frames += 1`` is
                # the only increment for this frame -- see
                # logout_dialog_open_hypothesis.py's own module docstring,
                # "WHAT THE CORE-REQUEST NEEDS TO DO, EXACTLY", point 3(a).
                return dispatch_logout_dialog_open_hypothesis(
                    self, parsed, legacy
                )
            if (
                logout_hypothesis_scenario is not None
                and logout_hypothesis_scenario.response_policy
                == LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST
                and nested_id == WORLDINFO_VITAL_ID
            ):
                # HYP-PF-016 only: the worldinfo_first scenario owns every
                # 0x3D4B-bearing frame.  Under the two ack-only logout
                # scenarios this branch is unreachable and 0x3D4B keeps its
                # frozen inherited no-response path, byte-identical.
                return self._dispatch_worldinfo_observation(parsed)
            if (
                chat_input_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                return self._dispatch_chat_input_hypothesis(parsed)
            if (
                channel_message_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # CHAT-CHANNEL-003.  Both chat lanes are keyed on the same
                # vital id, so they must never be able to see the same frame:
                # make_state_class refuses the pair outright and app.py refuses
                # the two flags together, which is why the ordering of these
                # two branches cannot matter.
                return self._dispatch_channel_message_hypothesis(parsed)
            if (
                stats_progression_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # STATS-PROG-002.  This lane and both chat lanes are keyed on
                # the same vital id, so they must never be able to see the same
                # frame: make_state_class refuses any pair outright and app.py
                # refuses the flags together, which is why the ordering of these
                # branches cannot matter.
                return self._dispatch_stats_progression_hypothesis(parsed)
            if (
                hp_death_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # HP-DEATH-002.  This lane, the progression lane and both chat
                # lanes are keyed on the same vital id, so they must never be
                # able to see the same frame: make_state_class refuses any pair
                # outright and app.py refuses the flags together, which is why
                # the ordering of these branches cannot matter.
                return self._dispatch_hp_death_hypothesis(parsed)
            if (
                runtimeres_death_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # RUNTIMERES-DISPATCH-001.  This lane, the hp-death lane, the
                # progression lane and both chat lanes are keyed on the same
                # vital id, so they must never be able to see the same frame:
                # make_state_class refuses any pair outright and app.py refuses
                # the flags together, which is why the ordering of these
                # branches cannot matter.
                return self._dispatch_runtimeres_death_hypothesis(parsed)
            if (
                damage_model_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # DAMAGE-DISPATCH-001.  This lane and the four above are keyed
                # on the same vital id, so they must never be able to see the
                # same frame: make_state_class refuses any pair outright and
                # app.py refuses the flags together, which is why the ordering
                # of these branches cannot matter.
                return self._dispatch_damage_model_hypothesis(parsed)
            if (
                damage_hp_link_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # DAMAGE-HP-LINK-001.  This lane and the five above are keyed
                # on the same vital id, so they must never be able to see the
                # same frame: make_state_class refuses any pair outright and
                # app.py refuses the flags together, which is why the ordering
                # of these branches cannot matter.
                return self._dispatch_damage_hp_link_hypothesis(parsed)
            if (
                remote_player_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # REMOTE-PLAYER-DISPATCH-001.  This lane and the five above
                # are keyed on the same vital id, so they must never be able
                # to see the same frame: make_state_class refuses any pair
                # outright and app.py refuses the flags together, which is
                # why the ordering of these branches cannot matter.
                return self._dispatch_remote_player_hypothesis(parsed)
            if (
                npc_hostile_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # NPC-HOSTILE-DISPATCH.  This lane and the six above are
                # keyed on the same vital id, so they must never be able to
                # see the same frame: make_state_class refuses any pair
                # outright and app.py refuses the flags together, which is
                # why the ordering of these branches cannot matter.
                return self._dispatch_npc_hostile_hypothesis(parsed)
            if (
                npc_hp_link_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # NPC-HP-LINK-002.  This lane and the seven above are keyed
                # on the same vital id, so they must never be able to see the
                # same frame: make_state_class refuses any pair outright and
                # app.py refuses the flags together, which is why the ordering
                # of these branches cannot matter.
                return self._dispatch_npc_hp_link_hypothesis(parsed)
            if (
                learn_skill_result_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # LEARN-SKILL-RESULT-001.  This lane and the other chat-
                # input-keyed sweep lanes above are keyed on the same vital
                # id, so they must never be able to see the same frame:
                # make_state_class refuses any pair outright and app.py
                # refuses the flags together, which is why the ordering of
                # these branches cannot matter.
                return self._dispatch_learn_skill_result_hypothesis(parsed)
            if (
                skill_attr_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # SKILL-ATTR-001.  This lane and the other chat-input-keyed
                # sweep lanes above are keyed on the same vital id, so they
                # must never be able to see the same frame: make_state_class
                # refuses any pair outright and app.py refuses the flags
                # together, which is why the ordering of these branches
                # cannot matter.
                return self._dispatch_skill_attr_hypothesis(parsed)
            if (
                item_operate_res_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # ITEMOP-RES-GREENLINE-001.  This lane and the other chat-
                # input-keyed sweep lanes above are keyed on the same vital
                # id, so they must never be able to see the same frame:
                # make_state_class refuses any pair outright and app.py
                # refuses the flags together, which is why the ordering of
                # these branches cannot matter.
                return self._dispatch_item_operate_res_hypothesis(parsed)
            if (
                hostile_hp_link_hypothesis_scenario is not None
                and nested_id == CHAT_INPUT_VITAL_ID
            ):
                # HOSTILE-HP-LINK-001.  This lane and the other chat-input-
                # keyed sweep lanes above are keyed on the same vital id, so
                # they must never be able to see the same frame:
                # make_state_class refuses any pair outright and app.py
                # refuses the flags together, which is why the ordering of
                # these branches cannot matter.
                return self._dispatch_hostile_hp_link_hypothesis(parsed)
            # CORE-REQUEST-GM-029.  Bound before the branch, the way
            # gm_state_action is: the append site below runs for every frame
            # that gets there, and an unbound local would raise
            # UnboundLocalError on every non-chat frame.
            gm_action = None
            if (
                nested_id == CHAT_INPUT_VITAL_ID
                and self.foundation.selected is not None
                and lane_hooks.module_production_allowed("lane_gm_chat_command")
            ):
                # KILL SWITCH, RECONNECTED (round wi1m62, COO-DECISION
                # 20260829_0041 option (b), answering chief's own ASK
                # 20260829_0023).  The third clause above is the whole of
                # that decision: this branch reaches LANE-GM's code without
                # going through `lane_hooks.fire()`, so `_discover()`'s
                # withdrawal -- the thing that makes `production_allowed`
                # mean anything for a hook -- cannot see it.  For one round
                # the 0xAC52 route ran with no such gate over it at all,
                # dropping a switch PANYA-ORDER 20260827_1230 approved.
                # Reading the flag here restores it: flip
                # `production_allowed = False` in
                # lane_hooks/lane_gm_chat_command.py, RESTART THE PROCESS
                # (the flag is read once, at import, by lane_hooks'
                # discovery -- editing the file under a running listener
                # changes nothing), and this branch stands down, composing
                # nothing and writing no audit row.  That is the tree from
                # before GM-028, not before GM-029: GM-029 replaced a
                # `fire()` call that appended an event and printed a token
                # on every chat line of every player, so "switched off" is
                # quieter than either wired route ever was.  [pf-adversary,
                # round wi1m62, caught that comparison naming the wrong
                # round.]  Which is why the stand-down is NOT silent -- see
                # the else-branch below.
                #
                # WHAT THE DECISION ASKED FOR, AND WHERE THIS DIFFERS.  The
                # COO decision accepted a named cost: that chief would
                # `import` the LANE-GM module here.  This does not do that.
                # It reads the flag through lane_hooks instead, so a lane
                # file that is deleted or raises on import answers False and
                # closes the door, where a direct import would take boot
                # down for every other lane -- the exact failure lane_hooks'
                # second fail-closed layer exists to prevent.  The deviation
                # is reported to the COO in
                # pf_bridge/notes_to_chief/20260829_0103_CHIEF-REPLY-COO-gm-
                # kill-switch-reconnected-option-b.md; if it is refused,
                # the import is a one-round change.
                #
                # CORE-REQUEST-GM-029 (LANE-GM), replacing CORE-REQUEST-GM-028
                # at this same branch.  No scenario flag.  GM-028's
                # `lane_hooks.fire(...)` at the chat-local-talk point was
                # REMOVED in the same commit that added this call, on the
                # lane's own "wire one point only" rule: two call sites would
                # authorize one chat line twice, write two byte-identical
                # ndjson audit rows, and spend the rate limit twice.
                # tests/test_gm_chat_command_action.py OneOfTwoWiringTests
                # reads this file as text and fails if both -- or neither --
                # are present, so the pair cannot drift apart.
                #
                # PLACEMENT: after every chat-keyed scenario lane above,
                # each of which returns.  So a chat-keyed scenario boot
                # never reaches this line and keeps its behaviour to the
                # byte -- and, the other way round, the GM door is silently
                # absent under those lanes: on a --chat-input-hypothesis
                # boot the echo lane claims the frame and this line never
                # sees it.  A scenario boot that keys some OTHER vital does
                # reach this line; that is measured, not assumed
                # (pf-adversary, round lo7e03).
                #
                # WHAT IS AND IS NOT UNCHANGED.  Still no `return` and no
                # `rx_frames` bump, so the frame flows on exactly as before
                # and the counter is untouched -- pinned by
                # tests/test_gm_chat_command_dispatch_wiring.py.  What DOES
                # change, and callers who grade on it should know: on a chat
                # line the module accepts, dispatch() now returns ONE MORE
                # action than the tree without this branch (that is the whole
                # point of GM-029 -- the hook route could never put a byte on
                # the wire).  `self.events` gains one event per chat line for
                # every ordinary player, now in the `gm_chat_action_*`
                # namespace instead of `gm_chat_command_*`.
                #
                # THE CONSOLE IS QUIETER THAN GM-028's, NOT LOUDER, and the
                # first version of this comment had it backwards.  [MEASURED,
                # pf-adversary, round apk7ue] a non-GM chat line produces
                # stdout='' AND stderr='': LANE_GM_CHAT_ACTION prints only
                # after the allowlist passes (chat_command_action.py, above
                # the version gate), where `fire()` printed LANE_HOOK_FIRED
                # for every chat line of every account.  A grader who greps
                # the console per ordinary chat line will see nothing and
                # must not read that as dead wiring.
                #
                # WHY THE APPEND IS 800 LINES BELOW: `actions` does not exist
                # yet here -- it is bound at `actions = super().dispatch(...)`
                # further down, which is the only binding a chat frame ever
                # reaches (measured by line trace, round apk7ue).  So this
                # branch only composes; the append happens right after that
                # binding, guarded by `gm_action is not None`.
                #
                # READINESS GUARD: only after a character is selected.  The
                # neighbouring lanes guard the same way, and without it the
                # very first frame on a connection -- before any login
                # verify -- would be audited as a GM command.  Harmless
                # while nothing executes; not harmless the day an executor
                # is attached to this hook.
                #
                # IDENTITY, STATED HONESTLY: the hook hands
                # gm/chat_command.py `self.token`, which on this server is
                # the process-wide --token CLI value, NOT a per-connection
                # authenticated login (reports/PF_MULTIPLAYER_READINESS_
                # AUDIT001_*.md rows I01-I04: the account name a client puts
                # on the wire is never read).  A client therefore cannot
                # name itself and a non-GM cannot talk its way in -- but
                # every connection this listener accepts shares one identity,
                # so the allowlist cannot yet tell two humans apart.  That
                # question has to be answered before any executor is wired
                # onto this point, not after.
                #
                # PARSER CAVEAT: v141's parse_outer decodes the FIRST nested
                # vital only and hands back everything after it as
                # nested_payload, so on a frame carrying more than one vital
                # these bytes are not just the chat body.  gm/chat_command.py
                # refuses anything that is not the measured 10 + 2N shape, so
                # that is a refusal event and not a crash; all three captured
                # chat frames (GT-006/GT-009) carry exactly one vital.
                gm_action = chat_command_action.make_gm_chat_command_action(
                    session=self,
                    payload=bytes(parsed.nested_payload),
                    legacy=legacy,
                    # CORE-REQUEST-GM-036: the registry THIS process booted
                    # with decides what /warp may stage, not a fresh disk
                    # read that can disagree with it.  Deliberately the bare
                    # closure local, never getattr-with-None: if the name
                    # ever stops being visible here this must be a loud
                    # NameError, not a silent fall back to the wider
                    # read-the-file path.
                    scene_registry=scene_entry_registry,
                )
            elif (
                nested_id == CHAT_INPUT_VITAL_ID
                and self.foundation.selected is not None
            ):
                # THE SWITCH, SAID OUT LOUD.  Reached only when the branch
                # above stood down on `production_allowed` -- the two
                # conditions repeated here are the branch's first two, so
                # nothing else can land in it.
                #
                # Why this exists at all: with the stand-down silent, the
                # console and the event trail could not tell "the owner
                # switched the GM chat route off" apart from "the wiring is
                # dead" or "nobody typed anything" -- and GT-127 grades on
                # capture/gm_command_log.ndjson, which is empty in all three
                # cases.  That is the failure this file already refuses to
                # ship one lane over, for GM-030, in the same words
                # ("silence would be indistinguishable from 'the wiring is
                # dead'").  [pf-adversary, round wi1m62.]
                #
                # One event and one stderr line per chat line, which is what
                # GM-028's removed `fire()` did for every chat line of every
                # player, so the volume is a shape this tree has run before
                # -- and only while the switch is off, which is a deliberate
                # state, not the default.
                self.events.append("gm_chat_action_route_closed_not_production_allowed")
                print(
                    "LANE_GM_CHAT_ACTION route=closed"
                    " reason=lane_gm_chat_command_not_production_allowed",
                    file=sys.stderr,
                )
            if (
                learn_skill_request_hypothesis_scenario is not None
                and nested_id == LEARN_SKILL_REQUEST_VITAL_ID
            ):
                # LEARN-SKILL-REQUEST-001.  Keyed on its own vital id 0x36AA,
                # which no other lane keys on; with the scenario absent this
                # branch does not exist and a 0x36AA frame falls through to
                # the frozen v141 default path exactly as before.
                return self._dispatch_learn_skill_request_hypothesis(parsed)
            if (
                pickup_listener_hypothesis_scenario is not None
                and nested_id == PICKUP_LISTENER_VITAL_ID
            ):
                # PICKUP-LISTENER-001.  Keyed on its own DERIVED vital id
                # 0x4543 (name-hash; never observed on any wire), which no
                # other lane keys on, hooked exactly the way 0x36AA is
                # hooked above; with the scenario absent this branch does
                # not exist and a 0x4543 frame falls through to the frozen
                # v141 default path exactly as before: the first runtime
                # request earns the one-time empty RuntimeRes ack, every
                # later unmatched vital returns no reply and no per-vital
                # event.
                return self._dispatch_pickup_listener_hypothesis(parsed)
            if (
                delete_actor_hypothesis_scenario is not None
                and nested_id == DELETE_ACTOR_VITAL_ID
            ):
                return self._dispatch_delete_actor_hypothesis(parsed)
            if (
                delete_refresh_hypothesis_scenario is not None
                and nested_id == DELETE_ACTOR_VITAL_ID
            ):
                # DELETE-REFRESH-001.  This lane and HYP-PF-015 key on the
                # same vital id, so they must never be able to see the same
                # frame: make_state_class refuses the pair outright and
                # app.py refuses the two flags together, which is why the
                # ordering of these two branches cannot matter.
                return self._dispatch_delete_refresh_hypothesis(parsed)
            if nested_id == legacy.LOGIN_VERIFY_VITAL:
                self.rx_frames += 1
                out = []
                if not self.login_ack_sent:
                    pc, frame = legacy.make_game_login_ack(self.token)
                    out.append(("LOGIN_VERIFY_ACK_ONCE", pc, frame, 0.0))
                    self.login_ack_sent = True
                    self.events.append("login_verify_seen")
                else:
                    self.events.append("duplicate_login_verify_suppressed")
                if not self.select_actor_sent:
                    pc, frame = self.foundation.character_list()
                    out.append(("FOUNDATION_CHARACTER_LIST_ONCE", pc, frame, 0.35))
                    self.select_actor_sent = True
                    self.events.append("select_actor_sent")
                return out
            if nested_id == legacy.CREATE_ACTOR_VITAL:
                self.rx_frames += 1
                self.create_actor_seen = True
                try:
                    parsed_create = legacy.parse_create_actor(parsed)
                except Exception as exc:
                    self.last_actor_summary = {"decode_error": repr(exc)}
                    self.events.append("create_actor_unparsed")
                    return []
                if not parsed_create:
                    self.events.append("create_actor_unparsed")
                    return []
                op, has_actor, wire = parsed_create
                self.events.append(f"create_actor_op{op}_has{has_actor}")
                if op != 1 or has_actor != 1 or not wire:
                    return []
                if self.create_actor_reply_sent:
                    self.events.append("duplicate_create_actor_suppressed")
                    return []
                try:
                    summary = legacy.decode_create_actor_data_ex(wire)
                    character, (pc, frame) = self.foundation.create(summary["name"], wire)
                except Exception as exc:
                    self.last_actor_summary = {
                        "decode_error": repr(exc), "wire_len": len(wire)
                    }
                    self.events.append("foundation_create_rejected_no_reply")
                    return []
                self.last_actor_summary = summary
                self.create_actor_reply_sent = True
                self.events.append("create_actor_success_echo_sent")
                return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]
            if nested_id == GM_RUN_GM_COMMAND_VITAL_ID:
                # CORE-REQUEST-010 (LANE-GM).  ALWAYS ON, no scenario flag.
                # The actual authorize/capture/event logic moved to
                # lane_hooks/lane_gm_run_command.py (v6.3 lane_hooks
                # architecture, first move-out demo) -- this call site only
                # counts the frame and fires the hook point; no reply is
                # sent either way (GM_RunGMCommandResultVital's meaning is
                # unproven) and nothing here decodes or executes a command.
                self.rx_frames += 1
                lane_hooks.fire(
                    "vital_inbound_gm_run_command",
                    session=self,
                    payload=bytes(parsed.nested_payload),
                )
                return []
            if nested_id == legacy.START_GAME_REQ:
                self.rx_frames += 1
                self.start_game_seen = True
                selector = legacy.parse_start_game_req(parsed)
                self.events.append(f"start_game_req_selector_{selector!r}")
                if selector is None or self.start_game_reply_sent:
                    return []
                try:
                    _, (pc, frame) = self.foundation.select_and_start(selector)
                except (KeyError, PermissionError):
                    self.events.append("foundation_start_game_rejected_no_reply")
                    return []
                except (ValueError, RuntimeError) as exc:
                    # Gate 1 (character-select) can also fail inside the
                    # Backpack load: _load_backpack raises ValueError when
                    # require_known_backpack rejects the stored row, or
                    # RuntimeError when the row is missing outright. Neither
                    # was in the tuple above, so either one used to escape
                    # this handler uncaught and unwind the listener thread in
                    # silence -- the client was left parked on "connecting"
                    # with nothing logged, for a bag that was malformed today
                    # and not only on the day a new row shape ships. Same
                    # loud-refusal shape as the SceneEntryRefused handler
                    # above: print the reason, refuse by name, no latch.
                    print(f"BACKPACK_LOAD_REFUSED {exc}")
                    self.events.append("foundation_start_game_rejected_no_reply")
                    return []
                load_only = scene_load_scenario is not None
                entry = None
                gm_state_action = None
                # CORE-REQUEST-017 point 1: default "no override" for the
                # load_only path, where the block below that assigns this
                # never runs. Read again much further down (the flagless
                # basic_faction=1 recompose) to decide whether ITS OWN
                # start_game() recompose has to keep this round's overridden
                # position too -- see the comment there for why leaving that
                # one on the untouched character.position default would
                # silently undo this override on every real production boot.
                login_scene_override = None
                if not load_only:
                    # WORLD-SCENE-TRAVEL-001 / CORE-REQUEST-003
                    # (LANE-A BUILD-002 slice 1, v2), wired here because
                    # runtime.py is the chief's file.  The hardcoded 1
                    # was the only thing pinning a default boot to Port
                    # Royal; the guards RE-073 recorded all live on
                    # opt-in lanes and never see this path.
                    #
                    # resolve_entry() derives every login frame from ONE
                    # resolved position rather than reading the pin
                    # separately from the row, so the teleport and the
                    # ActorAttr/MovementAttr built from
                    # foundation.selected.position cannot name two
                    # different places -- GT-079's own "biggest trap".
                    # It also emits the WORLD_SCENE console line itself,
                    # before returning, so a destination is never held
                    # without the line GT-079's stop rule reads.  For
                    # scene 1 the teleport fields stay the frozen
                    # (1, 0, 0.0, 0.0, 0.0), argument for argument what
                    # this path sent before, so a player who stays home
                    # receives the identical bytes.
                    #
                    # Resolved BEFORE anything below commits (the inventory
                    # sync, start_game_reply_sent, the composed
                    # START_GAME_RES action): a refusal here must leave the
                    # session exactly as untouched as a refused
                    # select_and_start above, so start_game_reply_sent
                    # stays False and the client can retry.  Resolving this
                    # deep inside the "not teleport_sent" branch below, with
                    # start_game_reply_sent already latched True and the
                    # composed action already thrown away by a bare
                    # "return []", used to wedge the session permanently:
                    # no reply of any kind ever went out for that selector,
                    # and the retry guard at the top of this handler then
                    # silently no-ops every later START_GAME_REQ from the
                    # same client -- found by pf-adversary.
                    #
                    # CORE-REQUEST-017 point 1 (LANE-GM, 2026-08-27T15:24
                    # +07:00): fast-path per-account login-scene override
                    # for an already-listed GM account, wired here rather
                    # than through lane_hooks because it has to change
                    # WHICH position resolve_entry() below resolves, and
                    # lane_hooks.fire() is deliberately report-only (see
                    # lane_hooks/__init__.py's own docstring: "hooks that
                    # need to hand something back ... are not what this
                    # point shape is for") -- threading a value back into
                    # a chief-owned local is exactly this call site's job,
                    # the same way CORE-REQUEST-003/006 above and below it
                    # already are.  The override lookup re-checks
                    # gm_accounts.json itself on every call (fail-closed
                    # default: no override for anyone), so a non-GM
                    # account can never get one even if a malformed
                    # override config named it by mistake.  (That call is
                    # now consume_login_scene_override, which spends the
                    # entry as well as reading it -- CORE-REQUEST-GM-033 v2,
                    # in the block below; this paragraph describes the
                    # identity re-check both versions share.)  Only scene_id
                    # is substituted -- x/y/z/heading stay the character's
                    # own stored row -- so resolve_entry()'s own safety
                    # rules apply exactly as they do for every other
                    # login: a destination with no ground evidence at that
                    # XY lands on ITS pinned spawn instead (never a raw
                    # coordinate transplant), home is still never touched
                    # unless the override names home, and a destination
                    # pinned login_entry_allowed=False (today: scene 17)
                    # still refuses via SceneEntryRefused below rather than
                    # opening a side door around that guard.  This block only
                    # feeds resolve_entry() (the teleport packet) -- see the
                    # "resync pc/frame" block right after the try/except
                    # below for why the ActorAttr/MovementAttr frame already
                    # composed above ALSO has to be redone when an override
                    # actually applies, not just this half.
                    login_row = self.foundation.selected.position
                    # CORE-REQUEST-GM-033 v2 (LANE-GM, 2026-08-29T05:15
                    # +07:00) with COO-DECISION 20260829_0441 item 2
                    # (single use) and COO-DECISION 20260829_0542
                    # (the standalone map is NOT consumed): the reader is
                    # REPLACED by the consumer here, never called beside it.
                    # Two calls would be two reads, and the second read of a
                    # spent entry returns None -- a player sent to the
                    # override's scene by the first read and to the stored
                    # row's by the second is exactly the split-brain frame
                    # the resync block below exists to prevent.
                    # consume_login_scene_override() answers with an outcome
                    # as well as a scene, and it is fail-closed in the way
                    # this call site needs: CONSUME_FAILED carries scene_id
                    # None, so an entry that could not be spent grants no
                    # scene at all rather than one that would outlive the
                    # login.  It swallows its own config faults (OSError,
                    # ValueError) into that outcome; the except below stays
                    # for the caller-side errors it does raise by contract
                    # (an empty or non-str token).
                    # Not None only when THIS login took the entry off disk,
                    # which is the only case that can put it back if the
                    # destination is then refused (see the refusal handler).
                    override_consumed_scene = None
                    # CORE-REQUEST-GM-038: False on every login that has no
                    # applied override; only the probe block below can turn
                    # it on, and only for a CONSUMED (GM-gated) grant to a
                    # sanctioned-barred scene.
                    gm_sanctioned_bypass = False

                    def _put_back_consumed_override(scene_id):
                        """Give a spent staged entry back.  Best effort.

                        TWO sites decide this login is not going to the
                        staged destination after all -- the registry probe
                        below (CORE-REQUEST-GM-034) and the refusal handler
                        further down -- and both owe the operator the same
                        thing.  Written once so the two cannot drift into
                        restoring under different conditions, which is the
                        shape of bug that put a phantom entry in the
                        chat-writable GM map (see
                        test_gm_login_scene_override_standalone_at_login).

                        A failure here is not a reason to fail the login:
                        the entry is then genuinely gone, and the event the
                        caller appends is the only record there will be.
                        """
                        try:
                            # CORE-REQUEST-GM-036 item 3: the undo must
                            # judge the file with the SAME registry that
                            # admitted the entry, or a snapshot-approved
                            # line makes the disk-read loader refuse the
                            # whole file and the staged entry is lost to
                            # gm_login_scene_override_lost_to_refusal_<n>.
                            return login_scene_stage.restore_login_scene(
                                self.token, scene_id,
                                scene_registry=scene_entry_registry,
                            )
                        except (ValueError, OSError, TypeError):
                            return False

                    try:
                        override_result = consume_login_scene_override(
                            self.token,
                            scene_registry=scene_entry_registry,
                        )
                        login_scene_override = override_result.scene_id
                        if override_result.outcome == CONSUMED:
                            override_consumed_scene = override_result.scene_id
                            self.events.append(
                                "gm_login_scene_override_consumed_"
                                f"{override_result.scene_id}"
                            )
                        elif override_result.outcome == STANDALONE_NOT_CONSUMED:
                            self.events.append(
                                "gm_login_scene_override_standalone_kept_"
                                f"{override_result.scene_id}"
                            )
                        elif override_result.outcome == CONSUME_FAILED:
                            # CORE-REQUEST-GM-036 wired the boot snapshot
                            # into the consume call above, which moved the
                            # snapshot-refuses-the-staged-scene case from
                            # the probe below (which printed
                            # GM_LOGIN_SCENE_OVERRIDE_REFUSED) up to this
                            # outcome -- so without a line here that whole
                            # direction goes back to the silence
                            # CORE-REQUEST-GM-034 was filed about.
                            #
                            # CORE-REQUEST-GM-037: `cause` names the ONE
                            # remedy, so this line stopped offering both.
                            # Every cause is a closed literal written in
                            # gm/login_scene_consume.py before any client
                            # connected; the remedy table lives in
                            # docs/GM_LANE.md next to the vocabulary.
                            #
                            # Attribute access OUTSIDE the print guard, and
                            # no getattr default: a ConsumeResult that lost
                            # its `cause` field must raise, not fall back
                            # to a placeholder word on a live console.
                            consume_cause = override_result.cause
                            # Guarded like the probe's print: a diagnostic
                            # must never cost the login.
                            try:
                                print(
                                    "GM_LOGIN_SCENE_OVERRIDE_CONSUME_FAILED "
                                    "effect=login_at_own_row "
                                    f"cause={consume_cause}"
                                )
                            except Exception:
                                pass
                            self.events.append(
                                "gm_login_scene_override_consume_failed"
                            )
                    except (
                        ValueError, OSError, TypeError, AttributeError,
                    ) as error:
                        # Same refuse-by-name-not-by-crash shape as the
                        # is_gm_account() guard a few hundred lines below
                        # (CORE-REQUEST-006): nothing this call can raise
                        # is a reason to take down the listener thread for
                        # every other login.
                        # CORE-REQUEST-GM-039 added AttributeError to this
                        # net, REVERSING the GM-037-era carve-out that let
                        # a lost `cause` field escape: pf-adversary (D7,
                        # round npo898) measured that the lane's
                        # ConsumeResultMisuse only narrowed the hole to one
                        # class -- any OTHER AttributeError raised inside
                        # THIS try (the consume call itself, the override
                        # loader it drives, or a line written tomorrow)
                        # still unwound the game listener thread
                        # (v141:7440 has no except), leaving the login
                        # port alive over a dead game port for the rest of
                        # the process's life.
                        # WHAT THIS NET DOES NOT COVER, said plainly
                        # because the first draft of this comment claimed
                        # otherwise (pf-adversary, round k882hm, D1): the
                        # is_gm_account() call is NOT in this try.  It has
                        # its own, narrower net further down this method
                        # (`except (ValueError, OSError)`), so an
                        # AttributeError from the accounts loader still
                        # escapes there.  That is a separate hole and it
                        # is filed, not silently widened here.
                        # The priced cost, from the lane's own letter: a
                        # typo'd field name in this block now degrades to
                        # a refusal instead of a traceback -- accepted
                        # because CI catches exactly that typo before any
                        # boot (measured this round: `casue` reddens 11
                        # tests across 7 files), while the listener death
                        # had no test that could see it.
                        # The loud-failure contract is REDUCED, not moved
                        # (pf-adversary, round k882hm, D2): `state.events`
                        # is never printed on a default boot (app.py builds
                        # an exporter under --export-events only), so the
                        # events row below is not an operator-visible
                        # artifact.  The console line printed here is --
                        # it is what a default boot has instead of the
                        # traceback, and it is the reason this arm is not
                        # silent.  The wiring test pins both halves: a
                        # result which lost its `cause` lands HERE, named
                        # `..._lookup_failed_AttributeError`, with the
                        # character at its own row, AND the line below on
                        # the console.  No override is applied.
                        # Since the consumer replaced the reader
                        # (CORE-REQUEST-GM-033 v2) a malformed config no
                        # longer arrives here -- it comes back as the
                        # CONSUME_FAILED outcome above -- so what is left
                        # for this handler is the caller-side contract
                        # (a token that is empty or not a str) plus any
                        # error a future version of that call may raise.
                        login_scene_override = None
                        # Guarded exactly like the CONSUME_FAILED print
                        # above: a diagnostic must never cost the login.
                        # ASCII only, exception class name only -- never
                        # str(error), whose text this file does not own
                        # and which could carry bytes outside cp874 onto
                        # the bridge's console.
                        try:
                            print(
                                "GM_LOGIN_SCENE_OVERRIDE_LOOKUP_FAILED "
                                "effect=login_at_own_row "
                                f"error={type(error).__name__}"
                            )
                        except Exception:
                            pass
                        self.events.append(
                            "gm_login_scene_override_lookup_failed_"
                            f"{type(error).__name__}"
                        )
                    if login_scene_override is not None:
                        # CORE-REQUEST-GM-034.  The destination is checked
                        # against THE REGISTRY THIS PROCESS HOLDS before the
                        # override is applied, because that snapshot -- not
                        # the file on disk -- is what places the character a
                        # few lines below.  Lane GM's admission check reads
                        # the file fresh on every login, so the two readings
                        # are the AGE OF THE PROCESS apart, not the "few
                        # microseconds" that lane's own test used to say.
                        #
                        # Only one direction is dangerous, and it is this
                        # one: a registry edited WIDER after boot
                        # (login_entry_allowed false->true, a spawn added, a
                        # new destination) yields an override the disk
                        # approves and the snapshot then refuses.  Refused
                        # below, the login returns NO FRAMES, and because a
                        # standalone grant is never consumed the client's
                        # retry meets the same wall forever -- the permanent
                        # lockout lane GM's pf-adversary measured in round
                        # qq0i9u, arriving through a door their disk-side
                        # fix cannot see.  Narrowing (true->false) was
                        # already safe: the snapshot is then the stricter
                        # of the two, which is fail-closed.
                        #
                        # WHY resolve_entry ITSELF AND NOT A PREDICATE HERE.
                        # A private copy of "may this row enter at login"
                        # would be a THIRD reader of the registry, free to
                        # disagree with the two that already do -- which is
                        # the very defect this guard exists to close.  The
                        # probe is silenced (emit) so GT-079 still gets
                        # exactly ONE destination line on the console, the
                        # one for the destination actually used, printed by
                        # the real call below.  resolve_entry is pure apart
                        # from that emit, so the double call costs nothing
                        # but is otherwise unobservable.
                        candidate_row = replace(
                            login_row, scene_id=login_scene_override
                        )
                        # CORE-REQUEST-GM-038: a sanctioned-barred scene
                        # (today: 126 only, one chief letter per id in
                        # gm/login_scene_admission.py) may be resolved with
                        # via_login=False -- the same bypass shape
                        # columbus_quest_dispatch.py:464 already uses --
                        # but ONLY when this exact login took the entry off
                        # the GM-GATED map (override_consumed_scene is set
                        # solely on the CONSUMED outcome).  A standalone-map
                        # grant (STANDALONE_NOT_CONSUMED) never qualifies:
                        # that map answers for accounts that are not in
                        # gm_accounts.json, and widening it here would hand
                        # non-GM accounts a server-side result the GM
                        # charter forbids (the letter's own no-go #1).  A
                        # character's persisted row that happens to name a
                        # sanctioned scene never qualifies either: with no
                        # override, login_scene_override is None and this
                        # stays False, so the real call below keeps
                        # via_login=True (no-go #2).
                        gm_sanctioned_bypass = (
                            override_consumed_scene is not None
                            and login_scene_admission
                            .is_sanctioned_barred_scene(login_scene_override)
                        )  # initialized False above the consume call
                        try:
                            world_scene_entry.resolve_entry(
                                candidate_row,
                                registry=scene_entry_registry,
                                emit=lambda _line: None,
                                via_login=not gm_sanctioned_bypass,
                            )
                        except world_scene_entry.SceneEntryRefused as exc:
                            # Refuse the OVERRIDE, not the login.  The
                            # character keeps its own stored row and gets
                            # into the game; the console names the entry so
                            # the operator is not sent hunting for a silent
                            # door.
                            # THE REASON ALONE IS A LIE ON DISK, so it is
                            # not printed alone (pf-adversary, this round).
                            # resolve_entry's message says the destination
                            # "is pinned but not allowed as a login
                            # destination" -- and in the one situation this
                            # branch exists for, the registry FILE says
                            # login_entry_allowed true. An operator who
                            # greps the file after reading that line finds
                            # it contradicted and stops trusting the line
                            # rather than the process. So the line names
                            # the snapshot, and names the only thing that
                            # replaces a snapshot.
                            #
                            # Guarded like lane GM guards its equivalent
                            # (gm/login_scene_override.py:204-216): they
                            # measured an unencodable account name raising
                            # out of exactly this shape of print in round
                            # qq0i9u. Nothing here interpolates a name
                            # today, but this print is the ONLY statement
                            # between the refusal and the restore below --
                            # if it raises, the operator's staged entry is
                            # destroyed by a diagnostic.
                            try:
                                print(
                                    "GM_LOGIN_SCENE_OVERRIDE_REFUSED "
                                    f"{exc} "
                                    "source=boot_snapshot "
                                    "note=the_registry_FILE_may_disagree; "
                                    "this process read it once at boot, so "
                                    "an edit made since then is not in "
                                    "effect until the server is restarted"
                                )
                            except Exception:
                                pass
                            self.events.append(
                                "gm_login_scene_override_refused_by_"
                                f"registry_{login_scene_override}"
                            )
                            if override_consumed_scene is not None:
                                restored = _put_back_consumed_override(
                                    override_consumed_scene
                                )
                                self.events.append(
                                    "gm_login_scene_override_restored_after_"
                                    f"refusal_{override_consumed_scene}"
                                    if restored else
                                    "gm_login_scene_override_lost_to_"
                                    f"refusal_{override_consumed_scene}"
                                )
                                # Given back already: the handler below must
                                # not put it back a second time if the
                                # character's OWN row is refused too.
                                override_consumed_scene = None
                            login_scene_override = None
                        else:
                            login_row = candidate_row
                            self.events.append(
                                f"gm_login_scene_override_applied_{login_scene_override}"
                            )
                    try:
                        # CORE-REQUEST-GM-038, second half of the pair: the
                        # real call must agree with the probe above, or the
                        # probe admits a sanctioned destination the real
                        # call then refuses.  login_scene_override is None
                        # on every path where the override was refused or
                        # never granted, so a login resolving the
                        # character's OWN stored row always passes
                        # via_login=True here, sanctioned scene id or not.
                        entry = world_scene_entry.resolve_entry(
                            login_row,
                            registry=scene_entry_registry,
                            via_login=not (
                                gm_sanctioned_bypass
                                and login_scene_override is not None
                            ),
                        )
                    except world_scene_entry.SceneEntryRefused as exc:
                        # Deliberately a LookupError and not a KeyError
                        # (see world_scene_entry.SceneEntryRefused), so it
                        # reaches here instead of the except
                        # (KeyError, PermissionError) above, which would
                        # otherwise swallow it into total silence -- a
                        # client parked on "connecting" with nothing
                        # logged.  This is the deliberate handler that
                        # class asks for: print the reason, refuse the
                        # login by name, without latching the session shut.
                        print(f"WORLD_SCENE_ENTRY_REFUSED {exc}")
                        self.events.append(
                            "world_scene_entry_refused_no_reply"
                        )
                        # NO RESTORE HERE ANY MORE, AND THAT IS A DELETION,
                        # NOT AN OVERSIGHT (CORE-REQUEST-GM-034).  Round
                        # ngwnnj/R223 put the operator's spent entry back at
                        # this spot because the consumer spends it BEFORE
                        # resolve_entry can refuse the destination.  The
                        # probe above now refuses the OVERRIDE before it is
                        # ever applied, and gives the entry back there, so
                        # reaching this line with a spent entry in hand
                        # would need resolve_entry to accept a row at the
                        # probe and refuse THE SAME row -- same object, same
                        # registry, same via_login -- a few statements
                        # later.  It is a pure function of those three; it
                        # cannot.  A restore kept here would be a second
                        # write of an entry this login already gave back,
                        # reachable only by mocking resolve_entry, which is
                        # how the old test for it reached this branch.
                        #
                        # What still arrives here is the case that was
                        # always the real one: THE CHARACTER'S OWN STORED
                        # ROW names a destination this tree will not open.
                        # No override, nothing to give back, and the login
                        # is refused by name rather than latched shut.
                        return []
                    # CORE-REQUEST-017 point 1, continued: resync pc/frame.
                    # pc/frame were already composed above by
                    # select_and_start() -> projector.start_game(), FROM THE
                    # CHARACTER'S REAL STORED ROW -- entirely before this
                    # override was even computed.  Only entry (the teleport
                    # packet) was built from the overridden login_row.  Left
                    # alone, that is exactly world_scene_entry.py's own
                    # documented "biggest trap" (its module docstring: "the
                    # teleport carries one point while the ActorAttr and the
                    # MovementAttr built from the same row carry another...
                    # a boot whose answer depends on that is a boot that
                    # cannot be graded") -- found by pf-adversary reviewing
                    # this exact change, with a byte-level repro (ActorAttr
                    # encoding scene 1 while the teleport right after it
                    # carried scene 2). It was latent, not new: every
                    # pre-existing login is at HOME_SCENE_ID, where resolve_
                    # entry() never relocates away from the stored row, so
                    # entry.position and self.foundation.selected.position
                    # have always been equal in practice -- this override is
                    # the first login path in this project where they can
                    # differ. Recompose from entry.position (the ONE
                    # resolved position resolve_entry() already derived the
                    # teleport from, complete with the correct scene_seq for
                    # the destination, not login_row's stale one) so both
                    # frames name the same arrival, the same defensive shape
                    # HYP-PF-027's basic_faction recompose above already uses
                    # for this identical projector call: on any anomaly, fall
                    # back to the untouched production bytes rather than risk
                    # a malformed START_GAME_RES.
                    if login_scene_override is not None:
                        try:
                            override_pc, override_frame = (
                                self.foundation.projector.start_game(
                                    self.foundation.selected,
                                    position=entry.position,
                                    backpack=self.foundation.backpack,
                                )
                            )
                        except (ValueError, RuntimeError, TypeError) as exc:
                            self.events.append(
                                "gm_login_scene_override_frame_resync_"
                                f"refused_{type(exc).__name__}"
                            )
                        else:
                            if len(override_pc) == len(pc) and len(
                                override_frame
                            ) == len(frame):
                                pc, frame = override_pc, override_frame
                                self.events.append(
                                    "gm_login_scene_override_frame_resynced"
                                )
                            else:
                                self.events.append(
                                    "gm_login_scene_override_frame_resync_"
                                    "length_drift"
                                )
                    # CORE-REQUEST (LANE-A, notes_to_chief/20260826_1010
                    # letter item 4-2/4-3).  Report-only, appended right
                    # after CORE-REQUEST-003's own resolve_entry call: the
                    # rewrite keyword is never passed here, so decide() stays
                    # on its own default and this can never change what the
                    # player above actually receives.  self.foundation.
                    # selected.position is the stored row exactly as it was
                    # BEFORE resolve_entry ran -- nothing above this line
                    # writes it.
                    liveness_verdict = world_scene_liveness.decide(
                        self.foundation.selected.position,
                        scene_liveness_ledger,
                    )
                    print(world_scene_liveness.liveness_console_line(
                        liveness_verdict, scene_liveness_ledger,
                    ))
                    # CHIEF-DECISION 20260829_0520 option A, answering
                    # LANE-A's D1 and D2 (D3, the faction byte, is NOT
                    # touched by this and is still open) and
                    # CORE-REQUEST-GM-033:
                    # the in-memory character now names the scene it was
                    # actually sent to.  Every later frame of this session
                    # reads self.foundation.selected.position and NOT entry
                    # (the teleport packet is a local of this handler): the
                    # census dispatch decides bg0001/bg0002/away-from-home
                    # from it, and _checkpoint_exact_target writes the row
                    # it labels with it.  Left on the stored row, an
                    # overridden login was measured asking for scene 1's
                    # checkpoint and scene 1's census while the player stood
                    # in another map -- a checkpoint that mislabels WHERE a
                    # coordinate is, which is worse than no checkpoint.
                    #
                    # entry.position, not login_row: resolve_entry() is the
                    # one authority on where this login actually landed
                    # (a destination with no ground evidence lands on ITS
                    # pinned spawn, home is never relocated), and it is the
                    # same value the teleport and the resynced
                    # ActorAttr/MovementAttr above were both built from.
                    # Anything else here re-opens world_scene_entry.py's own
                    # "biggest trap" from the other side.
                    #
                    # DELIBERATELY BELOW world_scene_liveness.decide() above,
                    # whose comment states it reads the stored row exactly as
                    # it was before resolve_entry ran: moving this line up
                    # would silently change what every liveness report in
                    # the ledger means.  In-memory only -- this is not a
                    # checkpoint and writes no DB row (COO-DECISION
                    # 20260828_2130: the server may not record a position it
                    # did not observe; this one it did not merely observe, it
                    # sent it).  Guarded on the override because a login
                    # without one must come out of this handler with every
                    # field of selected untouched.
                    if login_scene_override is not None:
                        self.foundation.selected = replace(
                            self.foundation.selected,
                            position=entry.position,
                        )
                        # ...and the session is a VISIT from here on: no
                        # durable position row is written for it.  Set in the
                        # same block as the resync, deliberately, because the
                        # two are one decision -- the moment the in-memory
                        # character starts naming the overridden scene,
                        # _checkpoint_exact_target would otherwise make a
                        # one-login courtesy permanent on the player's first
                        # step.  See that method for the measurement.
                        self.login_scene_override_visit = True
                        self.events.append(
                            "gm_login_scene_override_selected_position_"
                            f"resynced_{entry.position.scene_id}"
                        )
                    # CORE-REQUEST-006 (LANE-GM / GM-001).  ALWAYS ON, no
                    # scenario flag: docs/GM_LANE.md's own wiring request is
                    # "call make_gm_update_state_frame after a successful
                    # login for any account where is_gm_account() is true,
                    # and send the resulting frame to that connection".
                    # self.token is the authenticated login name -- the same
                    # value FoundationSession was already built from
                    # (lifecycle.login(login_name) ->
                    # store.ensure_account(login_name); see
                    # legacy.make_game_login_ack(self.token) above), not a
                    # new field.  vital_version and the three payload fields
                    # are UNPROVEN (gm/state_wire.py's own tag, mirrored
                    # here in ASCII to keep this file pure ASCII: "assumed,
                    # by the GM lane -- awaiting RE").  [ASSUMED - awaiting
                    # RE] 1, 0, 0, 0 is the
                    # placeholder used here: version 1 because no other
                    # version has ever been observed for this vital, and
                    # 0/0/0 because a zeroed flag/level is the value least
                    # likely to visibly change anything on a client this
                    # project has not measured that change against. RE
                    # request: CORE-REQUEST-GM-001 (gm/state_wire.py
                    # header).
                    try:
                        is_gm = is_gm_account(self.token)
                    except (ValueError, OSError) as error:
                        # gm/accounts.py raises ValueError BY DESIGN on a
                        # malformed config/gm_accounts.json (its own
                        # docstring: "a typo does not silently resolve to
                        # nobody is GM").  That is right for a config-loading
                        # tool, but is_gm_account() is called here on EVERY
                        # login (not only a GM's), unconditionally -- letting
                        # this propagate would unwind through dispatch() and
                        # take down the whole game-listener thread for every
                        # player, not just whoever mistyped the config.
                        # Refuse by name instead: this login proceeds with no
                        # GM frame, same as an account that is simply not
                        # listed.  pf-adversary, round 3lzfhw.
                        is_gm = False
                        self.events.append(
                            f"gm_account_lookup_failed_{type(error).__name__}"
                        )
                    # CORE-REQUEST-016 (LANE-GM, 2026-08-27T15:24+07:00,
                    # citing GT-101 -- attended, OBSERVER_CONFIRMED): sending
                    # this frame with the unproven version=1 above KILLS the
                    # session (client rejects it by this vital's own id,
                    # halts, closes the socket) -- measured against the
                    # owner's own real GM account.  gm_accounts.json ships
                    # with no accounts today so nothing is live-broken by
                    # this repo yet, but the very next account added before
                    # RE-105 pins the real version would hit this exact
                    # crash on login.  Gated on the module's own confirmed-
                    # version constant, not a local guess: not sending this
                    # frame is always safe (every login before this lane
                    # existed did exactly that).
                    if (
                        is_gm
                        and state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED
                        is not None
                    ):
                        gm_pc, gm_frame = make_gm_update_state_frame(
                            legacy,
                            state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED,
                            # CORE-REQUEST-020 (LANE-GM, 2026-08-27T19:33+07:00):
                            # field_0x0b_second=1 -- RE-089/RE-104 proved
                            # wire+0x15==1 is the gate GMModule_Client+0x19
                            # (BT_GM button visibility) checks; this was 0,
                            # so the gate was always false.
                            0, 1, 0,
                        )
                        gm_state_action = (
                            "GM_UPDATE_STATE_AFTER_LOGIN", gm_pc, gm_frame, 0.0,
                        )
                    elif is_gm:
                        self.events.append(
                            "gm_update_state_frame_withheld_no_confirmed_"
                            "vital_version_re105_open"
                        )
                    # CORE-REQUEST-007 (MOB-PICKUP-001), MOB_PICKUP_WIRING
                    # step 0, "AT CHARACTER SELECT": claim this character's
                    # bag ONCE against the server-wide mob_pickup_registry
                    # (built once in make_state_class, closed over here the
                    # same way scene_entry_registry is).
                    # self.foundation.backpack is already the BackpackState
                    # select_and_start loaded above (store.get_backpack is
                    # shape-gated only since COO-DECISION 20260826_0950, and
                    # gate 2 behind it is no longer is_unmoved_baseline: as
                    # of COO-DECISION 20260829_0441 select_and_start asks
                    # bag_admission.may_enter_world, which admits a golden
                    # bag that ACQUIRED a pickup-shaped row and refuses the
                    # governed move/swap/merge family exactly as before.
                    # Gate 2 still walls CONTENT (a moved, missing or altered
                    # golden row, a drifted header, an acquired row that is
                    # not pickup-shaped); what no gate on this path walls any
                    # more is a PICKUP-SHAPED bag -- gate 3's
                    # make_backpack_attr was widened to shape-only by
                    # COO-DECISION 20260828_0844, so mob_pickup.py's "THE
                    # WALL" section describes a wall that no longer stands
                    # for this lane's own content.  What still stops M5 is
                    # that store.py cannot write an acquired row at all)
                    # -- reused here, not a second DB
                    # read.  Only the "ON AN INBOUND PICKUP REQUEST" half of
                    # MOB_PICKUP_WIRING stays unwired: there is no known
                    # vital id for a client-originated pickup request on
                    # this project's wire yet (see the CORE-REQUEST-007
                    # handback), so there is nothing to dispatch a claim to.
                    if self.mob_pickup_bag_cell is None:
                        # self.foundation.backpack is unconditionally set by
                        # a successful select_and_start just above (see
                        # session.py) -- no guard against it being None here:
                        # a name that cannot happen is a lie to whoever
                        # counts refusals (mob_loot.py states this rule for
                        # itself).  pf-adversary, round 3lzfhw.
                        character_id = self.foundation.selected.id
                        try:
                            self.mob_pickup_bag_cell = (
                                mob_pickup_registry.claim(
                                    character_id, self.foundation.backpack,
                                )
                            )
                        except mob_pickup.MobPickupContractError as error:
                            # bag_already_claimed is the only refusal this
                            # call can raise (a second live claim for the
                            # same character -- e.g. a reconnect whose old
                            # session never reached close_connection); every
                            # other MobPickupContractError name here would
                            # be this session's own bag failing structural
                            # validation, which is worth knowing about by
                            # name rather than swallowing.
                            self.events.append(
                                f"mob_pickup_claim_refused_{error.args[0]}"
                            )
                        else:
                            self.mob_pickup_character_id = character_id
                self._sync_frozen_inventory_state()
                if npc_hostile_hypothesis_scenario is not None:
                    # NPC-HOSTILE-DISPATCH (HYP-PF-027): the entry half of the
                    # SCENE-005 pairing.  Recompose the same StartGame response
                    # through the frozen faction-1 serializer, or fall back to
                    # the byte-identical production response with a named
                    # event -- in which case the sweep below refuses by name.
                    #
                    # CORE-REQUEST-017 point 1: this scenario is opt-in
                    # (never on in a real production boot) and its own
                    # recompose only fires for one hardcoded pinned smoke
                    # identity (see the method's own docstring) -- a real GM
                    # account's character will not match it in practice. Not
                    # provably unreachable by code, though (pf-adversary,
                    # second pass): pass the override position through
                    # anyway, same shape as the two other recompose sites,
                    # so this stays correct even if this scenario is ever
                    # left on against a real GM login.
                    pc, frame = self._npc_hostile_start_game_response(
                        pc, frame,
                        position=(
                            entry.position
                            if login_scene_override is not None
                            else None
                        ),
                    )
                elif not active_lanes:
                    # PANYA-CHASE 20260827_0915 item (1).2 -- no exceptions,
                    # no flag.  The client renders hostility from the
                    # FACTION PAIR, not from either side alone (proven by
                    # HYP-PF-027's SCENE-005/007 negative above): a field
                    # mob can carry faction 6 forever and GT-084 will never
                    # see red until the PLAYER half of the pair goes out
                    # too.  Unlike the hypothesis path above, this is not
                    # scoped to one pinned smoke identity -- every player on
                    # the truly flagless (production) boot gets
                    # basic_faction=1.
                    #
                    # Gated on "not active_lanes" -- runtime.py's OWN
                    # definition of "no opt-in lane is selected at all"
                    # (built once at factory time, ~line 423; the same
                    # frozenset world_census_enabled and the travel-gate
                    # scenario-stand-down already key on) -- NOT "not
                    # load_only", which pf-adversary caught this round: that
                    # would have let this branch fire under every OTHER
                    # opt-in hypothesis scenario too (damage_hp_link,
                    # npc_hp_link, logout, channel_message, ground_loot,
                    # ...), silently tagging a byte those controlled
                    # experiments never asked for and never measured
                    # against.  active_lanes already contains
                    # scene_load_scenario (so the scene-load milestone's OWN
                    # dedicated scenario.player_basic_faction plumbing in
                    # session.py's ReadOnlyFoundationSession.select_and_start
                    # is still never double-composed here) and
                    # npc_hostile_hypothesis_scenario (irrelevant here since
                    # that case already took the `if` branch above and never
                    # reaches this `elif`).
                    #
                    # Same frozen serializer, same fail-closed shape: any
                    # refusal or length drift falls back to the untouched
                    # production bytes with a named event, never a
                    # half-composed frame.  UPDATED 2026-08-30 by chief
                    # (LANE-A round `vvy6q7`, 20260830_0050 letter, item @2'):
                    # the "only scene_id in (1, 2)" half of this comment
                    # is STALE -- the composer now accepts {1, 2, 14} and
                    # decides by rule (registry login_entry_allowed AND
                    # n_SAVE == 1), not by a hardcoded list. The other half
                    # still holds: any OTHER pinned scene (e.g. 278, 997/
                    # FilmScene) still falls back to plain bytes here,
                    # because those scenes have n_SAVE == 0, not because of
                    # their scene_id -- and that fallback is now named
                    # (`faction_refused_scene_997_n_save_is_0_not_1`) instead
                    # of silent. Real for RE-073's FilmScene work and for any
                    # future world-travel unlock of a scene with n_SAVE == 0.
                    try:
                        faction_pc, faction_frame = (
                            self.foundation.projector.start_game(
                                self.foundation.selected,
                                # CORE-REQUEST-017 point 1: this recompose
                                # runs on every flagless production login,
                                # AFTER the override's own "resync pc/frame"
                                # block above -- left on the default (None ->
                                # character.position, the real unmodified
                                # row), it would silently discard that resync
                                # and put the character's real scene right
                                # back into the ActorAttr/MovementAttr this
                                # call composes, undoing the override on the
                                # one path every real login actually takes
                                # (found reasoning through pf-adversary's
                                # finding on the first version of this
                                # override, which predates this recompose
                                # existing in scope). entry is only None for
                                # load_only, where login_scene_override is
                                # also always None (see its own default
                                # above), so this is a no-op for every login
                                # that isn't this override.
                                position=(
                                    entry.position
                                    if login_scene_override is not None
                                    else None
                                ),
                                basic_faction=NPC_HOSTILE_PLAYER_PAIR_FACTION,
                                backpack=self.foundation.backpack,
                            )
                        )
                    except (ValueError, RuntimeError, TypeError) as exc:
                        self.events.append(
                            "player_faction1_compose_refused_production_"
                            f"start_game_{exc!r}"
                        )
                    else:
                        if (
                            len(faction_pc)
                            != len(pc) + NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA
                        ):
                            self.events.append(
                                "player_faction1_length_drift_production_"
                                "start_game"
                            )
                        else:
                            pc, frame = faction_pc, faction_frame
                            print(
                                "PLAYER_FACTION basic_faction="
                                f"{NPC_HOSTILE_PLAYER_PAIR_FACTION} "
                                "sent_on_flagless_start_game"
                            )
                            self.events.append(
                                "player_faction1_start_game_sent"
                            )
                self.start_game_reply_sent = True
                self.events.append("start_game_res_scene_identity_sent")
                actions = [(
                    "SCENE2_LOAD_ONLY_SELECTED_START_GAME" if load_only
                    else "FOUNDATION_SELECTED_START_GAME",
                    pc, frame, 0.10,
                )]
                if not self.teleport_sent:
                    if load_only:
                        # PF-HYPOTHESIS-LEDGER: HYP-PF-007 frozen
                        p = scene_load_scenario.position
                        tp_pc, tp_frame = legacy.make_login_teleport(
                            p.scene_id, p.scene_seq, p.x, p.y, p.z,
                        )
                    else:
                        tp_pc, tp_frame = legacy.make_login_teleport(
                            *entry.teleport_fields
                        )
                    actions.append((
                        "SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE" if load_only
                        else "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
                        tp_pc, tp_frame, 0.70,
                    ))
                    self.teleport_sent = True
                    self.events.append(
                        "scene2_load_only_marker2_teleport_sent" if load_only else
                        "v135_startgame_movement_p0_minus100x_minus50y_teleport_zero_sent"
                    )
                if gm_state_action is not None:
                    # CORE-REQUEST-006: rides ALONGSIDE the inherited
                    # dispatch, appended to the same action list, exactly
                    # like ground_loot_actions below does -- the frozen
                    # START_GAME_RES / teleport bytes above stay
                    # byte-for-byte untouched.
                    actions.append(gm_state_action)
                return actions

            if nested_id == legacy.ITEM_OPERATE_REQ_VITAL:
                if item_move_capture_scenario is not None:
                    return self._dispatch_item_move_capture(parsed)
                if item_move_hypothesis_scenario is not None:
                    return self._dispatch_item_move_hypothesis(parsed)
                candidate = parse_merge_candidate(legacy, parsed)
                if candidate is not None:
                    return self._dispatch_v111_persistent_merge(parsed)

            durable_target = legacy.parse_v141_refresh_target_pos(parsed)
            if (
                population_scenario is not None
                and nested_id == legacy.TARGET_POS_VITAL
            ):
                # This opt-in capability owns every TargetPos-shaped attempt so
                # malformed forms cannot seed the broader frozen V141 population.
                return self._dispatch_object_population_target(parsed, durable_target)
            remote = scene_load_scenario.remote_actor if scene_load_scenario is not None else None
            if (
                remote is not None and not self.scene_remote_spawned
                and self.runtime_ack_sent and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
            ):
                if durable_target is None:
                    return []
                # PF-HYPOTHESIS-LEDGER: DIAG-PF-001 frozen
                # PF-HYPOTHESIS-LEDGER: GEO-PF-002 frozen
                # PF-HYPOTHESIS-LEDGER: GEO-PF-003 frozen
                pc, frame = make_scene_remote_actor(legacy, remote)
                self.scene_remote_spawned = True
                self.events.append("scene2_p60_mobs34_single_committed")
                label = ("SCENE2_P60_MOBS34_HP3857_INITIAL"
                         if remote.diagnostic_hp is not None
                         else "SCENE2_P60_MOBS34_SINGLE_INITIAL")
                return [(label, pc, frame, 0.0)]
            if remote is not None and self.scene_remote_spawned and is_scene_remote_target(
                legacy, parsed, remote.actor_identity,
            ):
                if not self.scene_remote_target_captured:
                    self.scene_remote_target_captured = True
                    self.events.append("scene2_p60_target_kind2_captured_no_reply")
                return []
            ack = scene_load_scenario.action_ack if scene_load_scenario is not None else None
            if (ack is not None and remote is not None and self.scene_remote_spawned
                and is_scene_remote_hostile_target(legacy, parsed, remote.actor_identity)):
                self.scene_hostile_target_captured = True
                self.events.append("scene007_p60_target_kind1_captured_no_reply")
                return []
            if ack is not None and parsed.vital_count in (2, 6):
                fields = parse_scene006_ea7d(legacy, parsed, ack)
                if (
                    fields is None or self.scene_action_ack_sent
                    or not self.scene_remote_spawned
                    or not self.scene_hostile_target_captured
                    or self.foundation.selected is None
                ):
                    return []
                selected = self.foundation.selected
                performer = ((selected.identity_hi & 0xFFFFFFFF) << 32) | (selected.identity_lo & 0xFFFFFFFF)
                # PF-HYPOTHESIS-LEDGER: HYP-PF-002 frozen
                pc, frame = make_scene007_action_ack(legacy, fields, performer)
                self.scene_action_ack_sent = True
                self.events.append("scene007_ea7d_no_damage_action_ack_sent")
                return [("SCENE007_EA7D_ACTION_ACK_ONCE", pc, frame, 0.0)]
            # PF-HYPOTHESIS-LEDGER: HYP-PF-032 active
            # GROUND-LOOT-001 (GT-045): at the house scene-load moment --
            # first exact TargetPos after the runtime ack -- emit the two
            # pinned single-element RuntimeRes derived-bit-0x08 frames
            # (near, then far), exactly once per session.  ONE element per
            # frame on purpose: V43 measured ErrorData=28317 on a combined
            # multi-record derived-mask collection, and the attended run
            # must measure rendering, not the count.  The frames RIDE
            # ALONGSIDE the inherited dispatch (appended to the same action
            # list), so the frozen population and the position checkpoint
            # of the triggering frame stay byte-for-byte untouched.
            ground_loot_actions = []
            if (
                ground_loot_hypothesis_scenario is not None
                and not self.ground_loot_pair_sent
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
                and durable_target is not None
            ):
                try:
                    frames = make_ground_loot_frames(
                        legacy, ground_loot_hypothesis_scenario,
                        tuple(durable_target[:3]),
                    )
                except RuntimeError:
                    # Drift refuses forever: latch so the refusal cannot
                    # retry itself onto the wire on a later frame.
                    self.ground_loot_pair_sent = True
                    self.events.append(
                        "ground_loot_compose_refused_no_reply"
                    )
                else:
                    self.ground_loot_pair_sent = True
                    self.events.append(
                        "hyp_pf_032_ground_loot_bit08_pair_committed"
                    )
                    (near_pc, near_frame), (far_pc, far_frame) = frames
                    ground_loot_actions = [
                        ("GROUND_LOOT_BIT08_RENDER_NEAR_ONCE",
                         near_pc, near_frame, 0.0),
                        ("GROUND_LOOT_BIT08_RENDER_FAR_ONCE",
                         far_pc, far_frame, 0.10),
                    ]
            # PF-HYPOTHESIS-LEDGER: HYP-PF-039 active
            # GROUND-LOOT-NAMEPROP-001 (GT-069): the same trigger moment,
            # but a SEPARATE lane that never shares a boot with the one
            # above.  Two single-element bit-0x08 frames whose element mask
            # is 0x3A -- dword, the name-property GATE at +0x1B, position,
            # and the name-property INDEX at +0x1A -- so an attended tester
            # can answer whether the selector RE-067 pinned actually reaches
            # the floating item name label.  The two frames are 1.50 s apart
            # on purpose: the label's measured lifetime is 0.2-0.4 s, and
            # the previous round's 42 ms gap left the observer unable to say
            # which element she had seen.  The frames RIDE ALONGSIDE the
            # inherited dispatch, so the frozen population and the position
            # checkpoint of the triggering frame stay byte-for-byte
            # untouched.
            nameprop_actions = []
            if (
                ground_loot_nameprop_scenario is not None
                and not self.ground_loot_nameprop_sent
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
                and durable_target is not None
            ):
                try:
                    nameprop_frames = make_ground_loot_nameprop_frames(
                        legacy, ground_loot_nameprop_scenario,
                        tuple(durable_target[:3]),
                    )
                except RuntimeError:
                    # Drift refuses forever: latch so the refusal cannot
                    # retry itself onto the wire on a later frame.
                    self.ground_loot_nameprop_sent = True
                    self.events.append(
                        "ground_loot_nameprop_compose_refused_no_reply"
                    )
                else:
                    self.ground_loot_nameprop_sent = True
                    self.events.append(
                        "hyp_pf_039_ground_loot_nameprop_pair_committed"
                    )
                    nameprop_actions = [
                        (label, pc, frame, element.delay)
                        for label, (pc, frame), element in zip(
                            GROUND_LOOT_NAMEPROP_LABELS,
                            nameprop_frames,
                            ground_loot_nameprop_scenario.elements,
                        )
                    ]
            arena_actions = []
            suppress_inherited_population = (
                self.arena_scenario is not None
                and not self.arena_spawned
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and nested_id == legacy.TARGET_POS_VITAL
            )
            if suppress_inherited_population and (
                durable_target is None
                or self.foundation.selected.position.scene_id
                != self.arena_scenario.scene_id
            ):
                # Before Arena population exists, TargetPos is either the exact
                # trigger or a complete no-op.  Never let the broader frozen
                # dispatcher retain malformed coordinates for a later frame.
                return []
            if (
                self.arena_scenario is not None
                and not self.arena_spawned
                and self.runtime_ack_sent
                and self.teleport_sent
                and self.foundation.selected is not None
                and self.foundation.selected.position.scene_id == self.arena_scenario.scene_id
                and durable_target is not None
            ):
                # PF-HYPOTHESIS-LEDGER: GEO-PF-001 harness_only
                pc, frame, target = make_p30_target(
                    legacy, self.arena_scenario, durable_target,
                )
                # Commit scenario state before queueing and suppress the inherited
                # P0/P30/P91 population branch for this opt-in session only.
                self.arena_spawned = True
                self.npc_spawn_sent = True
                self.population_indices = (legacy.V112_MONSTER_INDEX,)
                self.population_refresh_anchor = tuple(durable_target[:3])
                arena_version = _active_arena_version(self.arena_scenario)
                version = arena_version.lower()
                self.events.append(f"arena_{version}_p30_test_only_population_committed")
                arena_actions = [
                    (f"ARENA_{arena_version}_P30_INITIAL", pc, frame, 0.0),
                    (f"ARENA_{arena_version}_P30_MODEL_READY_REAPPLY", pc, frame,
                     self.arena_scenario.reapply_ms / 1000.0),
                ]

            # COO-DECISION 2026-08-29T09:41+07:00 item 2 / scene_admission_
            # gate.py.  Snapshot the four fields the inherited P0/P30/P91
            # branch (v141:4292-4312) latches, so that if the gate refuses
            # the scene this session's row names, the branch can be undone
            # whole rather than half.  Read BEFORE super() runs because
            # that is the only moment their pre-branch values still exist.
            _frozen_pop_before = (
                self.npc_spawn_sent,
                self.npc_idle_action_sent,
                self.population_indices,
                self.population_refresh_anchor,
            )
            # CORE-REQUEST (LANE-A, letter 20260830_0909).  A scene with a
            # REGISTERED and ALLOWED lane_hooks ChooseNPC responder answers
            # TARGET_VITAL/CHOOSE_NPC itself instead of letting the
            # inherited branch below (v141:4395) run at all -- see
            # lane_hooks/lane_a_choose_npc_scene14.py's module docstring for
            # the exact KeyError that branch raises uncaught, unconditionally
            # over every entry of population_indices, the moment a scene's
            # real membership includes one index its own hardcoded
            # PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS table lacks.  Inert today: no
            # scene's responder module has production_allowed = True, so
            # module_production_allowed(...) is False and this branch never
            # takes over -- one registry lookup and a no-op on every other
            # frame, the same inert-until-a-lane-flips-its-own-flag shape
            # CORE-REQUEST-GM-040's hook takes just below in this file.
            #
            # !! pf-adversary (round `hd6tac`, MEASURED, not fixed here) --
            # TWO gaps a lane MUST read before flipping its own responder's
            # production_allowed, because skipping `super().dispatch(parsed)`
            # entirely skips everything else v141 does for that ONE frame,
            # not only the crash-prone ChooseNPC loop:
            #
            # (1) v141:3788-3816 unconditionally arms
            # `self.action_target_last_identity` / `_last_kind` /
            # `p30_action_target_armed` on every TARGET_VITAL frame, read
            # later by its own ACTION_VITAL handling (`exact_p30_target`,
            # v141:3818-3862) to gate `exact_target_bound_wield_action`.  A
            # claimed scene never arms these for that frame -- repro'd live:
            # `action_target_last_identity` stayed `None` through a claimed
            # click that would have set it.  Harmless for scene 14 today
            # only because `exact_p30_target`'s strict match wants an
            # arena-harness identity/index shape scene 14's real actors do
            # not have -- INCIDENTAL, not designed for.  A future scene
            # whose players use melee/skill targeting on the SAME connection
            # a responder claims must re-check this before flipping its flag.
            #
            # (2) `legacy.extract_choose_npc_identities` can name MORE THAN
            # ONE actor in a single frame (multi-select), and the frozen
            # path answers each distinct one with its own frame
            # (v141:4408).  Every responder in this registry today
            # (`ChooseNpcResponder.respond`) returns at most ONE
            # `ChooseNpcResponse` per call -- built to try each named
            # identity until ONE answers, not to answer all of them -- so a
            # multi-select click through a claimed scene sends one frame
            # where the inherited path would have sent several.  Degrades
            # gracefully (one honest answer beats a crash) but is not full
            # parity; `tests/test_lane_a_choose_npc_scene14.py::
            # TheGuardAnsweredTheClickInsteadOfCrashingTests::
            # test_a_multi_select_click_answers_only_the_first_identity`
            # pins this exact shape so it cannot silently get worse.
            #
            # Neither gap is fixed here: (1) has no safe fix without either
            # duplicating v141's arming logic (a second copy of frozen state
            # this project has refused elsewhere) or running `super().
            # dispatch()` and catching the crash mid-call, which this round
            # does not attempt; (2) needs `ChooseNpcResponse` to become a
            # collection to fix, a `lane_hooks`/lane_a design change outside
            # a runtime.py guard's scope.
            scene_choose_npc_responder = None
            if (
                nested_id in (legacy.TARGET_VITAL, legacy.CHOOSE_NPC)
                and self.foundation.selected is not None
            ):
                candidate = lane_hooks.scene_choose_npc_responder(
                    self.foundation.selected.position.scene_id
                )
                if candidate is not None and (
                    lane_hooks.module_production_allowed(candidate.module)
                ):
                    scene_choose_npc_responder = candidate
            if scene_choose_npc_responder is not None:
                try:
                    chosen_identities = tuple(
                        legacy.extract_choose_npc_identities(parsed)
                    )
                except Exception as error:  # noqa: BLE001 - fail-closed:
                    # a malformed frame this lane cannot parse must never
                    # take the listener thread down for every player.
                    self.events.append(
                        "scene_choose_npc_responder_parse_error_"
                        f"{type(error).__name__}"
                    )
                    chosen_identities = ()
                response = None
                if chosen_identities:
                    # WIRED-v2 evidence, on the production path, only for a
                    # frame this branch actually hands to the responder --
                    # not merely because the guard condition matched, the
                    # same distinction gm/chat_command_action.py's own
                    # CONSOLE_TOKEN comment draws.
                    lane_hooks.announce_direct_fire(
                        scene_choose_npc_responder.module,
                        "scene_choose_npc_responder",
                    )
                    try:
                        response = scene_choose_npc_responder.respond(
                            legacy=legacy,
                            chosen_identities=chosen_identities,
                            population_indices=self.population_indices,
                            last_target_pos=self.last_target_pos,
                            scene_id=self.foundation.selected.position.scene_id,
                            scene_entry_registry=scene_entry_registry,
                        )
                    except Exception as error:  # noqa: BLE001 - a lane's
                        # responder must never take the listener thread down
                        # for every player; named, not silent.
                        self.events.append(
                            "scene_choose_npc_responder_failed_"
                            f"{type(error).__name__}"
                        )
                        response = None
                if response is not None:
                    # Console-proof-before-frame, the same discipline the
                    # census call site uses for a lane's own printed lines.
                    for line in response.console_lines:
                        print(
                            lane_hooks.console_safe(line), file=sys.stderr,
                        )
                    actions = [
                        (response.label, response.pc, response.frame,
                         response.delay),
                    ]
                else:
                    # No honest answer for this click (nothing chosen, or
                    # every named identity declined) -- this scene has
                    # claimed the vital family, so the frozen branch's own
                    # crash-prone loop is skipped regardless, the same as an
                    # ordinary refusal: no bytes, not an invented frame.
                    self.events.append("scene_choose_npc_responder_declined")
                    actions = []
            else:
                actions = super().dispatch(parsed)
            # The frozen branch is the "fifth line" -- it queues
            # scene-1-shaped actors without reading what scene the session
            # is in.  It cannot be edited (v141 is pinned) and cannot be
            # disarmed before dispatch (it reads runtime_ack_sent after the
            # same call sets it), so it is allowed to run and then withheld.
            #
            # WITHHELD, NOT MERELY STRIPPED (pf-adversary, this round, D2 --
            # MEASURED).  Dropping the two frames while leaving the latched
            # state behind left population_indices attesting to three actors
            # this gate had just stopped the client from receiving -- and
            # the ChooseNPC answerer below reads exactly that field as its
            # evidence the client has the actor.  It also left the branch
            # latched off for good (v141:4308), so a session withheld once
            # while away could never populate its home scene afterwards.
            # Restoring the snapshot makes this, to every reader, a frame on
            # which the branch did not fire: nothing shipped, nothing
            # latched, still armed for a scene the gate admits.
            #
            # NOT the only place actions is appended to after this line (the
            # travel handoff and the census both add their own further
            # down); it is only the point at which THIS branch's output is
            # first visible. The census refusal fallback re-emits these same
            # two labels, and is deliberately not gated here -- it is
            # reachable only inside the home-scene branch, which the gate
            # admits by definition.
            if (
                not scene_admission_gate.admits_frozen_legacy_population(
                    self.foundation.selected.position.scene_id
                    if self.foundation.selected is not None else None
                )
                and scene_admission_gate.contains_frozen_legacy_population(
                    actions
                )
            ):
                actions = (
                    scene_admission_gate.without_frozen_legacy_population(
                        actions
                    )
                )
                (
                    self.npc_spawn_sent,
                    self.npc_idle_action_sent,
                    self.population_indices,
                    self.population_refresh_anchor,
                ) = _frozen_pop_before
                self.events.append(
                    "frozen_legacy_population_withheld_scene_"
                    + str(
                        self.foundation.selected.position.scene_id
                        if self.foundation.selected is not None else "none"
                    )
                )
            # CORE-REQUEST from LANE-A (2026-08-29T01:46+07:00), answered
            # here rather than in the frozen builder that carries the defect:
            # `current/pf_login_game_server_v141.py` is pinned immutable by
            # six independent checks (see world_face_frame's docstring), so
            # the click frame is corrected on the way out instead.  Without
            # this, every NPC click re-tags the actor under the frozen row's
            # Mob-Set number and the client draws a different PERSON than the
            # login census named - measured on the owner's screen at
            # 2026-08-29T00:17+07:00, Columbus answering as Sebastian.
            # Total and additive: a dispatch with no face frame in it gets
            # back exactly what it passed in.
            #
            # GATED ON THE CENSUS THAT IS ACTUALLY IN FORCE, not applied
            # unconditionally (pf-adversary, this round, D2 - MEASURED).  An
            # earlier version of this call had no gate, and on every lane boot
            # and on the frozen P0/P30/P91 fallback it made things WORSE, not
            # better: those paths ship the frozen rows' Mob-Set numbers at
            # login, so correcting the click frame made the two frames
            # disagree in the opposite direction, and dropped actor 0x2001
            # from a frame after login had announced it.  The rule is not "the
            # resolved identity is always right", it is "the click frame must
            # say what THIS login said".  Only the census built by
            # `world_population` resolves identities, and only it sets the
            # flag below.
            if self.world_census_identity_resolved:
                actions = world_face_frame.rebuild_face_actions(
                    legacy, actions, self.population_indices,
                    self.last_target_pos, self.events,
                )
            if gm_action is not None:
                # CORE-REQUEST-GM-029 (LANE-GM).  The action composed at the
                # 0xAC52 branch far above, appended here because this is the
                # first line at which `actions` exists on a chat frame's path.
                # Shape is gm_state_action's: (label, pc, frame, delay_before).
                actions = actions + [gm_action]
                # CORE-REQUEST-GM-040.  The one-bit "append really happened"
                # signal gm/commands.py's OUTCOME_QUEUED has waited on since
                # CORE-REQUEST-GM-032 item 3: this line is the only place that
                # ever runs the append above, so it is the only honest place
                # to say so.  Deliberately a value this lane (gm/, via
                # chat_command_action.make_gm_chat_command_action) sets on
                # itself before returning the action tuple -- chief only
                # FIRES it here, never reads back anything shaped by gm/'s
                # own code beyond the pairing below.  Nothing sets this
                # today, so this block is inert: one getattr and a no-op,
                # every frame, until a future GM-lane round wires the
                # setter.
                #
                # BOUND TO THE SPECIFIC ACTION, NOT A BARE "SOMETHING IS
                # PENDING" FLAG -- pf-adversary's own review of the first
                # version of this hook (round `hd6tac`, D1/D2) measured why
                # that matters: a callback set for a composed-then-withheld
                # action (`gm_action is None` that same call, so the append
                # above never ran for it) stayed on `self` unfired, and a
                # bare flag would have let it fire against the NEXT frame's
                # unrelated append instead -- crediting one player's command
                # with a different one's confirmation.  The pairing is
                # `(the exact gm_action object, the callback)`; the identity
                # check below (`is`, not `==`) means a leftover pairing from
                # a withheld frame can only ever match that same frame's own
                # object, which by construction is never appended again, so
                # it can never fire for the wrong action.  Cleared before the
                # callback runs, not after, so a callback that itself sets a
                # NEW pairing (for whatever action it names) is never
                # immediately overwritten by this block's own cleanup.
                pending_confirm = getattr(
                    self, "_gm_action_queued_confirm", None
                )
                if pending_confirm is not None and pending_confirm[0] is gm_action:
                    self._gm_action_queued_confirm = None
                    _, confirm_gm_action_queued = pending_confirm
                    try:
                        confirm_gm_action_queued()
                    except Exception as error:  # noqa: BLE001 - a GM-lane
                        # confirmation callback must never take the listener
                        # thread down for every player; named, not silent.
                        # Grep string, since this event has no declared
                        # constant (runtime.py's own events are bare string
                        # literals throughout, unlike gm/'s EVENT_* table):
                        # "gm_action_queued_confirm_failed_".
                        self.events.append(
                            "gm_action_queued_confirm_failed_"
                            f"{type(error).__name__}"
                        )
            if (
                second_password_mode == "bypass"
                and not self.second_password_bypass_sent
                and self.foundation.selected is not None
                and self.teleport_sent
                and self.runtime_ack_sent
            ):
                pc, frame = make_proactive_second_password_ok(
                    legacy, second_password_mode,
                )
                self.second_password_bypass_sent = True
                self.second_password_bypass_last_sent_at = monotonic_clock()
                self.events.append(
                    "hyp_pf_009_proactive_second_password_ok_committed"
                )
                actions = actions + [(
                    "HYP_PF_009_PROACTIVE_SECOND_PASSWORD_OK_ONCE",
                    pc, frame, 0.0,
                )]
            elif (
                second_password_mode == "bypass"
                and self.second_password_bypass_sent
                and self.foundation.selected is not None
                and self.teleport_sent
                and self.runtime_ack_sent
                and parsed.vital_count == 0
                and self.second_password_bypass_last_sent_at is not None
                and monotonic_clock() - self.second_password_bypass_last_sent_at
                >= SECOND_PASSWORD_PULSE_INTERVAL_SECONDS
            ):
                # The first live trial proved that an unsolicited OK delivered
                # before the UI challenge is not retained by this client.  Empty
                # runtime polls are the only exact, continuing client boundary;
                # pulse the same accepted response so an opened dialog receives
                # it without any PIN submission.  No credential is read or sent.
                # PF-HYPOTHESIS-LEDGER: HYP-PF-009 active
                pc, frame = make_proactive_second_password_ok(
                    legacy, second_password_mode,
                )
                self.second_password_bypass_last_sent_at = monotonic_clock()
                if not self.second_password_bypass_keepalive_started:
                    self.second_password_bypass_keepalive_started = True
                    self.events.append(
                        "hyp_pf_009_second_password_ok_keepalive_started"
                    )
                actions = actions + [(
                    "HYP_PF_009_SECOND_PASSWORD_OK_KEEPALIVE",
                    pc, frame, 0.0,
                )]
            if (
                scene_load_scenario is None
                and
                durable_target is not None
                and self.foundation.selected is not None
            ):
                self._checkpoint_exact_target(durable_target)
                # CORE-REQUEST-004 (LANE-A / BUILD-002 / M2).  observe()
                # never raises on a report -- every refusal is a named
                # console line and a None -- so nothing here needs a guard
                # against a bad report.  What CAN raise is the checkpoint
                # below (a stale lease, same as the frozen path above), and
                # by design that happens BEFORE confirmed_fields(): a write
                # that raises leaves no WORLD_TRAVEL_DEPART line and no
                # commit, and the pending crossing is discarded on the next
                # report with WORLD_TRAVEL_DEPART_ABANDONED.
                departure = self.world_travel_gates.observe(
                    self.foundation.selected.position,
                )
                if departure is not None:
                    self.foundation.checkpoint(departure.arrival)
                    tp_pc, tp_frame = legacy.make_login_teleport(
                        *departure.confirmed_fields()
                    )
                    # COO-DECISION 20260829_2254: the crossing population
                    # handoff, composed AFTER the crossing committed
                    # (confirmed_fields() above) and queued around the
                    # teleport frame in the slot the handoff itself names:
                    # a clear belongs to the scene the client still renders
                    # (before the teleport), a census to the scene it is
                    # loading (after).  handoff_on_crossing never raises
                    # (its own contract), which is what lets it live in
                    # this except-less block.  Scene 2 stays with its login
                    # populator (COO-DECISION 20260829_2245): the table
                    # answers a reasoned clear for it, never a roster.
                    handoff = world_population_handoff.handoff_on_crossing(
                        legacy,
                        departure.arrival.scene_id,
                        (
                            departure.arrival.x,
                            departure.arrival.y,
                            departure.arrival.z,
                        ),
                    )
                    print(
                        world_population_handoff
                        .handoff_console_line(handoff)
                    )
                    crossing_actions = [(
                        departure.action_label, tp_pc, tp_frame, 0.70,
                    )]
                    if handoff.sends_a_frame:
                        handoff_actions = [(
                            handoff.label, handoff.pc, handoff.frame, 0.0,
                        )]
                        if handoff.reapply_ms is not None:
                            handoff_actions.append((
                                handoff.label + "_REAPPLY",
                                handoff.pc, handoff.frame,
                                handoff.reapply_ms / 1000.0,
                            ))
                        if (
                            handoff.dispatch_slot
                            == world_population_handoff
                            .SLOT_BEFORE_TELEPORT
                        ):
                            crossing_actions = (
                                handoff_actions + crossing_actions
                            )
                        else:
                            crossing_actions = (
                                crossing_actions + handoff_actions
                            )
                    # BOTH frozen-state membership fields, from the one
                    # value the seam hands out so they cannot disagree
                    # (MembershipReset's docstring).  Applied on EVERY
                    # crossing, frame or no frame: an unavailable handoff
                    # deliberately clears both -- a membership nobody can
                    # answer for is a membership to drop.
                    #
                    # HOME ONLY (pf-adversary R235, D2 -- MEASURED).  The
                    # only ChooseNPC answerer in the tree (v141:4395)
                    # speaks the bg0001 table unconditionally: 16 of
                    # bg0015's 81 indices are not in
                    # PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS, so a roster
                    # membership written here is one click from a
                    # KeyError that kills the connection -- and the ones
                    # that ARE present would recompose Port Royal into
                    # the new map.  So a census into any other scene
                    # ships its frame but withholds the membership, with
                    # a named event, until a click answerer for roster
                    # scenes exists (ASK-COO, round t7t5yd).
                    # world_census_indices moves with the same decision:
                    # a stowaways line reading the login membership after
                    # a crossing is the k882hm-D3 shape (a field
                    # describing a census the client no longer holds).
                    reset = handoff.membership_reset
                    # RE-157 job 2 / LANE-B letter 1838: mob-combat
                    # announced membership is stamped only at login,
                    # GM /warp, and the bg0001/bg0002/lane-composer
                    # census points -- a normal (non-GM) travel-gate
                    # crossing never touched it, so a player walking
                    # into a new scene the ordinary way could keep the
                    # OLD scene's membership and either false-reject
                    # (fail closed, tolerable) or, worse, false-accept
                    # if the new scene's id happened to already have a
                    # membership from earlier this session.  Cleared
                    # unconditionally on EVERY crossing (both branches
                    # below), mirroring ``_gm_warp_resync_selected_scene``'s
                    # own clear+generation-bump: a membership nobody can
                    # answer for is a membership to drop.
                    self.mob_combat_announced_membership = None
                    self.mob_combat_announced_membership_generation += 1
                    self.events.append(
                        "world_travel_gate_crossing_mob_combat_membership_"
                        f"cleared_{departure.arrival.scene_id}"
                    )
                    home_census = (
                        handoff.kind
                        == world_population_handoff.KIND_CENSUS
                        and departure.arrival.scene_id
                        == world_scene_travel.HOME_SCENE_ID
                    )
                    if home_census:
                        self.population_indices = (
                            reset.population_indices
                        )
                        self.population_refresh_anchor = (
                            reset.population_refresh_anchor
                        )
                        self.world_census_indices = (
                            reset.population_indices
                        )
                        # The recompose stamp travels with the census in
                        # force, same as the login and lane commits do
                        # (pf-adversary R235, D6): a stale stamp is a
                        # wrong-anchor recompose on the next kill.
                        try:
                            self.census_anchor_record = (
                                mob_scene_recompose.census_anchor(
                                    departure.arrival.scene_id,
                                    reset.population_refresh_anchor,
                                    handoff.actor_count,
                                )
                            )
                        except mob_scene_recompose.SceneRecomposeError:
                            self.events.append(
                                "world_pop_handoff_anchor_stamp_refused"
                            )
                    else:
                        self.population_indices = None
                        self.population_refresh_anchor = None
                        self.world_census_indices = None
                        if (
                            handoff.kind
                            == world_population_handoff.KIND_CENSUS
                        ):
                            self.events.append(
                                "world_pop_handoff_membership_withheld_"
                                f"scene_{handoff.scene_id}"
                            )
                    self.world_census_identity_resolved = (
                        home_census
                        and reset.population_indices is not None
                    )
                    actions = actions + crossing_actions
                    self.events.append(
                        "world_travel_departed_scene_"
                        f"{departure.gate.to_scene_id}"
                    )
                    self.events.append(
                        "world_pop_handoff_"
                        f"{handoff.kind}_scene_{handoff.scene_id}"
                    )

            # WORLD-CENSUS-001.  Composed AFTER the inherited dispatch, on
            # exactly the conjunction the frozen branch stands on: its own
            # enclosing elif (v141:3680, outer_id + teleport_sent) and its own
            # guard (v141:4292, runtime_ack_sent + last_target_pos).  There is
            # no nested_id conjunct because the frozen branch has none either -
            # it sits outside the TargetPos block, on any RuntimeReq frame once
            # a position is known.  last_target_pos is read rather than
            # re-parsed because super() has already set it from THIS frame
            # (v141:4259), which is the anchor the frozen branch would use.
            #
            # CORE-REQUEST-026 (LANE-A, bg0002 only).  The frozen guard's
            # last_target_pos requirement is what leaves Prison Exile Island
            # empty until the player's first WASD press (nothing spawns a
            # TargetPosVital before then).  bg0001 keeps the frozen
            # requirement exactly as shipped -- this scene has no frozen
            # branch to stay parity with, so it is allowed to trigger on
            # arrival (teleport_sent + runtime_ack_sent alone) instead, using
            # the scene's own pinned spawn as the anchor when no
            # TargetPosVital has arrived yet.  A player who does move first
            # still gets last_target_pos as the anchor, unchanged.
            #
            # WIDENED FROM bg0002-ONLY TO "EVERY SCENE BUT HOME", chief round
            # `4w5j25`, on PANYA-ORDER 20260901_0215 section 4: "the server
            # must send NPCs itself before I have to start walking ... no
            # round should ever again require me to walk just to make spawn
            # call up NPCs."  The disjunct below now reads "not home" where it
            # read "== SCENE2_N_ID", so scenes 3..11, 14 and 130 (LANE-A's
            # world scenes -- every one of them pinned in
            # scene_entry_registry AND carrying a registered,
            # production-allowed census composer) compose on arrival exactly
            # as scene 2 has since CORE-REQUEST-026.  Nothing else moves: the
            # anchor fallback below was already scene-agnostic (it asks the
            # registry for whatever scene_id THIS session is in, never a
            # bg0002 path) and already fails closed for a scene with no
            # pinned spawn, which is why generalizing the trigger needed no
            # second selector.  A scene with no census composer (278, 997)
            # still reaches the same send-nothing latch it reached before,
            # only sooner.  A lane composer's own ADMISSION CHECK
            # (lane_a_scene_census.scene_is_open_to_players) is unchanged and
            # still decides whether a roster ships at all; this only decides
            # WHEN it is asked.
            #
            # HOME (bg0001) IS DELIBERATELY NOT WIDENED, and the reason is a
            # MEASURED uncaught crash rather than parity taste.  The bg0001
            # arm far below is the only census arm that arms
            # ``self.population_indices`` with no lane_hooks ChooseNPC
            # responder standing in front of it: the bg0002 arm sets those
            # fields on purpose never (see its own comment), and the lane arm
            # sets them only when the scene's responder is BOTH registered and
            # production_allowed -- and such a scene never reaches
            # ``super().dispatch(parsed)`` for TARGET_VITAL/CHOOSE_NPC at all
            # (the responder branch above returns its own actions instead).
            # v141:4395-4416 loops over every chosen identity whenever
            # ``population_indices is not None`` and unpacks
            # ``x,y,_z,_heading=self.last_target_pos`` for any index it finds
            # there, with NO None check.  Composing the home census on arrival
            # would therefore leave a session that has not yet sent a
            # TargetPosVital exactly one NPC click away from a TypeError out
            # of the listener thread (v141:7440 has no except) -- a dead
            # connection instead of a slow one, which is a worse answer to the
            # order than the walk it removes.  It is not fixable from this
            # disjunct: it needs either a deferred install of
            # population_indices at the first TargetPosVital, or a runtime.py
            # ChooseNPC guard for scene 1 shaped like the one
            # lane_hooks/lane_a_choose_npc_scene14.py already has for its own
            # scene.  Named in this round's handback as the follow-up rather
            # than smuggled in behind a trigger widening.
            census_actions = []
            if (
                world_census_enabled
                and not self.world_census_sent
                and not self.world_census_refused
                and parsed.outer_id == legacy.GSCN_RUNTIME_PROTOCOL_REQ
                and self.teleport_sent
                and self.runtime_ack_sent
                and self.foundation.selected is not None
                and (
                    self.last_target_pos is not None
                    or self.foundation.selected.position.scene_id
                    != world_population.SCENE_ID
                )
            ):
                scene_id = self.foundation.selected.position.scene_id
                if self.last_target_pos is not None:
                    x, y, z, _heading = self.last_target_pos
                    anchor = (float(x), float(y), float(z))
                else:
                    # Reachable for ANY scene but home (the disjunct above,
                    # widened in round `4w5j25`; bg0002-only before that),
                    # before any TargetPosVital has set last_target_pos.
                    # This call was always scene-agnostic -- it asks the
                    # registry for THIS session's scene_id and never took a
                    # bg0002 path -- so the widening needed no second
                    # selector here, only a wider set of scenes allowed to
                    # arrive at it.
                    # spawn_position() refuses rather than inventing a
                    # position for a scene with no pinned spawn -- but
                    # unlike a genuinely transient read, scene_entry_registry
                    # is loaded exactly once at boot (make_state_class /
                    # app.py) and never reloaded, so a missing/unpinned
                    # spawn here is a deterministic, permanent fact
                    # for the rest of this process's life, not a condition
                    # that could clear on the next poll.  Retrying it would
                    # mean re-raising and re-logging the identical failure on
                    # every RuntimeProtocolReq poll for the whole session
                    # (pf-adversary, round confident-ride-sf9kel).  Latch it
                    # exactly like the sibling population-build refusal a
                    # few lines below, instead.
                    #
                    # THE LATCH COSTS NOTHING A WIDER TRIGGER USED TO BUY
                    # (round `4w5j25`, checked rather than assumed): a scene
                    # that cannot answer this call is one the registry does
                    # not pin, and every census composer registered today
                    # refuses such a scene anyway -- lane_a_scene_census's
                    # own ADMISSION CHECK reads the same registry row and
                    # declines when it is missing, and the runtime's other
                    # two arms are for scenes 1 and 2, which are pinned.  So
                    # a refusal here can only replace a send-nothing skip
                    # that would have happened after the player moved, never
                    # a census that would have shipped.
                    try:
                        anchor = world_scene_travel.spawn_position(
                            world_scene_travel.destination(
                                scene_id, scene_entry_registry,
                            )
                        )
                    except Exception as error:
                        self.world_census_refused = True
                        # RENAMED in round `4w5j25` from the
                        # ``world_census_bg0002_arrival_anchor_refused_*``
                        # spelling this line carried while the trigger was
                        # bg0002-only: the string now has to be able to name
                        # scene 7 as honestly as scene 2, and a fixed
                        # "bg0002" in a line that can fire for another scene
                        # is a log that lies.  The scene id is IN the event
                        # for the same reason the sibling arms carry their
                        # own suffixes (pf-adversary: a shared spelling
                        # leaves the log unable to say which branch latched).
                        self.events.append(
                            "world_census_arrival_anchor_refused_scene_"
                            f"{scene_id}_{type(error).__name__}"
                        )
                        anchor = None
                if anchor is None:
                    pass
                elif scene_id == world_population_bg0002.SCENE2_N_ID:
                    # CORE-REQUEST-021 (LANE-A M1-P item 2).  Prison Exile
                    # Island's own census, parallel to the bg0001 branch
                    # below rather than a fork of it: a different builder,
                    # a different table, no faction bit (see
                    # world_population_bg0002.py's module docstring - the
                    # hostile-faction widening for this scene is LANE B's
                    # item, not this one).  Reachable only once a stored
                    # character row actually names scene 2, which nothing in
                    # this tree seeds today (see the handback).
                    try:
                        generation = (
                            world_population_bg0002.build_bg0002_population(
                                legacy, anchor, scene_id=scene_id,
                                count_source=(
                                    world_population_bg0002
                                    .COUNT_SOURCE_FULL_ROSTER
                                ),
                            )
                        )
                        # CORE-REQUEST (LANE-B 20260829_1600): hostile
                        # faction splice for this scene's census, INSIDE
                        # this same try on purpose -- the branch is
                        # fail-closed by design (v141:7440 has no except)
                        # and an escape from the splice must land in the
                        # same net as an escape from the builder.
                        # COO-DECISION 20260829_1842 (recompose, R231):
                        # the R230 shape deliberately passed NO ledger
                        # (self.mob_combat_ledger could hold another
                        # scene's rows, and full_roster_override raises on
                        # a mismatched pair), which left the measured
                        # narrow window: a frame that both wounds a
                        # scene-2 mob and triggers this census shipped
                        # that mob at full HP.  This is now the same safe
                        # symmetric route the sibling bg0001 branch
                        # already takes: sync ledger+roster to THIS scene
                        # first, then pass the synced ledger, so wounds
                        # survive the compose and the pair can never
                        # mismatch.  The invariant that carries this is
                        # SAME ROSTER, not same folder: measured over
                        # scene ids 0..999, field_mobs.roster_for_scene_id
                        # and the sync's load_roster-over-folder answer
                        # identical rosters everywhere (both filter
                        # through the same live-scene table membership),
                        # while the two FOLDER answers disagree on
                        # addressed-but-not-live ids (278 among them,
                        # pf-adversary this round) -- none of which can
                        # reach this scene-2-only branch.  So the ledger
                        # the sync opened and the roster the override
                        # loads are the same rows.  The COO's other half of that ruling
                        # -- the MODULE refusing a ledger-less recompose
                        # loudly instead of defaulting to None -- lives in
                        # lane B's files and is theirs to land; this call
                        # site simply never omits the ledger again.
                        synced_roster = self._sync_combat_scene_state()
                        if synced_roster is None:
                            # Registry does not address the scene: no
                            # roster, no override, said by name -- same
                            # latch as the bg0001 branch.  Unreachable
                            # while this branch only composes for scene 2,
                            # which the registry addresses.
                            override = {}
                            # _bg0002 suffix on purpose (pf-adversary,
                            # this round): the bg0001 arm below logs the
                            # unsuffixed string, and a shared spelling
                            # would leave the log unable to say which
                            # branch latched.
                            self.events.append(
                                "mob_death_census_override_skipped_"
                                "scene_unaddressed_bg0002"
                            )
                        else:
                            override = (
                                mob_census_hostility
                                .hostile_override_for_scene_id(
                                    legacy, scene_id,
                                    self.mob_death_register,
                                    ledger=self.mob_combat_ledger,
                                )
                            )
                        if override:
                            generation = _apply_mob_death_census_override(
                                legacy, generation, override,
                            )
                    except Exception as error:
                        # Fail closed, same reasoning as the bg0001 branch's
                        # own catch-all below: the builder reads frozen
                        # constants and calls frozen serializers, so drift can
                        # arrive as AttributeError or struct.error as easily
                        # as ValueError, and an escape here unwinds out of the
                        # listener thread (v141:7440 has no except).  There is
                        # no frozen bg0002 fallback the way bg0001 has
                        # ``_world_census_frozen_fallback``, so a refusal
                        # here sends NO frame at all rather than inventing
                        # one.
                        self.world_census_refused = True
                        self.events.append(
                            "world_census_bg0002_compose_refused_"
                            f"{type(error).__name__}"
                        )
                    else:
                        # Console proof, in this exact order, before the
                        # frame is queued - built ONCE from this one
                        # ``generation`` (never calling
                        # ``scene_and_census_console_lines`` separately,
                        # which would compose the whole roster a second
                        # time).
                        print(world_scene_travel.entry_console_line(
                            world_scene_travel.destination(
                                scene_id, scene_entry_registry,
                            )
                        ))
                        print(
                            world_population_bg0002.census_console_line(
                                generation,
                            )
                        )
                        for line in world_population_bg0002.actor_lines(
                            generation,
                        ):
                            print(line)
                        # CORE-REQUEST (LANE-B 20260829_1600): printed
                        # UNCONDITIONALLY, never inside the override's if
                        # -- "unbacked=none" is a real answer and "no line
                        # at all" is the state GT-084 already misread once.
                        # Computed from the census this boot actually
                        # built (post-splice identities), same as the
                        # bg0001 branch's own coverage line.
                        # LANE-B CORE-REQUEST 20260829_1955 item (2), COO
                        # 20:41: without these two fields the line prints
                        # override=not_reported ledger=not_reported forever,
                        # and "correctly silent" vs "silently broken" read
                        # identically off a boot console.
                        for line in mob_census_hostility.describe_census_hostility(
                                scene_id, generation.actor_identities,
                                override=override,
                                ledger=self.mob_combat_ledger):
                            print(line)
                        self.world_census_sent = True
                        self.events.append(
                            "world_census_bg0002_committed_actors_"
                            f"{generation.actor_count}_pc_"
                            f"{generation.pc_bytes}_frame_"
                            f"{generation.frame_bytes}"
                        )
                        # RE-157 job 2 / MOB-COMBAT-001: stamp exactly the
                        # actor identities THIS commit put on the wire, so
                        # ``_dispatch_mob_combat`` can refuse an ActionVital
                        # against a roster member that was never announced
                        # to this session.  ``generation.actor_identities``
                        # is the post-splice set the hostility coverage
                        # line just above already prints from -- not
                        # ``world_census_indices``, which bg0002 sets
                        # nowhere (mob_combat_membership.py's own docstring,
                        # nonclaim 4).  Bumped, never reused, so a stale
                        # membership from an earlier commit this same
                        # session cannot be mistaken for this one even if
                        # the scene id repeats.
                        self.mob_combat_announced_membership_generation += 1
                        self.mob_combat_announced_membership = (
                            mob_combat_membership.build_membership(
                                scene_id, generation.actor_identities,
                                self.mob_combat_announced_membership_generation,
                            )
                        )
                        # CORE-REQUEST (LANE-B 20260829_2055) chief's half,
                        # the bg0002 side: same stamped record as the bg0001
                        # commit, so a hit or a kill in this scene stops
                        # falling into the one-entry
                        # ``..._skipped_no_population_anchor`` arm RE-092
                        # proved is replace-by-omission.  ``anchor`` is this
                        # branch's own census anchor (durable target or
                        # pinned spawn), ``scene_id`` is the bg0002 id the
                        # disjunct above admitted.  This runs in the
                        # ``else`` clause, PAST the builder's fail-closed
                        # net, so a shape refusal is caught here by hand:
                        # losing the recompose stamp must degrade to the
                        # one-entry fallback the guard already has, never
                        # unwind the listener thread over a census that
                        # already shipped.
                        try:
                            self.census_anchor_record = (
                                mob_scene_recompose.census_anchor(
                                    scene_id, anchor,
                                    generation.actor_count,
                                )
                            )
                        except mob_scene_recompose.SceneRecomposeError:
                            self.events.append(
                                "world_census_bg0002_anchor_stamp_refused"
                            )
                        # Deliberately NOT set here: population_indices,
                        # population_refresh_anchor, world_census_indices,
                        # npc_idle_action_sent.  Those are read elsewhere by
                        # bg0001-placement-index-specific NPC-click/idle-
                        # action dispatch code; bg0002 has no click-dispatch
                        # system wired yet, and populating those fields with
                        # bg0002's placement indices would silently leak
                        # bg0001 semantics onto a table that means something
                        # different.  Out of this CORE-REQUEST's scope.
                        census_actions = [
                            (
                                "WORLD_CENSUS_BG0002_INITIAL_"
                                f"{generation.actor_count}",
                                generation.pc, generation.frame, 0.0,
                            ),
                            (
                                "WORLD_CENSUS_BG0002_REAPPLY_"
                                f"{generation.actor_count}",
                                generation.pc, generation.frame,
                                world_population_bg0002.INITIAL_REAPPLY_MS
                                / 1000.0,
                            ),
                        ]
                elif (
                    scene_id != world_population.SCENE_ID
                    and scene_id != world_population_bg0002.SCENE2_N_ID
                    and (
                        lane_census
                        := lane_hooks.scene_census_composer(scene_id)
                    ) is not None
                    and lane_hooks.module_production_allowed(
                        lane_census.module
                    )
                ):
                    # CORE-REQUEST (LANE-A 20260829_1845): the scene census
                    # point, table-driven instead of a fourth per-scene
                    # elif.  A lane registers a composer for a scene in its
                    # own lane_hooks/lane_<x>_*.py file
                    # (lane_hooks.census_composer(scene_id)); this branch
                    # asks the table and stands aside when the answer is
                    # None.  The fire() shape cannot serve here because a
                    # census must hand actors back (fire() is report-only
                    # by contract), so this is the COO-DECISION
                    # 20260829_0041 option (b) shape the 0xAC52 chat route
                    # already uses: read module_production_allowed() first,
                    # then call directly.
                    #
                    # NO REGRESSION PATH, by construction rather than by
                    # discipline: BOTH dedicated scenes are excluded in
                    # this elif's own condition, so a composer registered
                    # for scene 1 or scene 2 is simply never consulted and
                    # those scenes walk their existing branches to the
                    # byte.  The scene-2 conjunct is redundant with the
                    # scene-2 elif above at today's line order -- it is
                    # there so the guarantee survives a reordering of the
                    # chain, which pf-adversary (round 73fhoc) measured
                    # the whole suite failing to notice when the property
                    # lived in line order alone.  This table only ever
                    # claims scenes that today fall through to the
                    # "skipped, not home" latch below, i.e. scenes that
                    # send NOTHING.
                    #
                    # ~~Same trigger as every sibling branch: for a lane
                    # scene, `anchor` can only be last_target_pos (the
                    # arrival-trigger disjunct above is bg0002-only), so a
                    # lane census fires on the first TargetPosVital after
                    # the runtime ack -- the bg0001 requirement, not the
                    # bg0002 relaxation.  A lane that needs
                    # trigger-on-arrival for its scene opens a follow-up
                    # letter; widening the trigger is not smuggled in
                    # here.~~  STALE as of chief round `4w5j25` -- the
                    # follow-up that paragraph asked for is the owner's own
                    # order (PANYA-ORDER 20260901_0215 section 4) and it
                    # landed in the disjunct above, not here.  A lane census
                    # now fires on ARRIVAL (teleport_sent + runtime_ack_sent,
                    # first RuntimeProtocolReq), with the scene's pinned
                    # spawn as `anchor`, and on the first TargetPosVital only
                    # when the player somehow moved before that poll.  This
                    # branch itself is UNCHANGED: `anchor` is an (x, y, z)
                    # tuple either way, and every composer this table can
                    # reach uses it for nearest-first ORDER over its own
                    # table-absolute placements (world_population_bg0003.
                    # census_order and its siblings), never as the origin the
                    # actors are placed relative to -- and with
                    # `actor_count=None` (handoff_for_arrival's default,
                    # which lane_a_scene_census does not override) the WHOLE
                    # roster ships, so which anchor was used cannot change
                    # WHICH actors a player receives, only the order they are
                    # listed in.
                    # EVERYTHING that touches the composer's return value
                    # stays inside this one try.  pf-adversary (round
                    # 73fhoc) measured two escapes from a draft that only
                    # guarded the call itself: a well-typed
                    # SceneCensusResult carrying a str reapply-ms unwound
                    # the listener thread AFTER the committed event was
                    # logged (false green plus evidence laundering), and a
                    # truthy dict escaped as AttributeError with neither
                    # latch set.  So every field is coerced here, as
                    # untrusted lane input, before any latch or print --
                    # and only the coerced values are used after the net.
                    lane_declined = False
                    try:
                        composed = lane_census.compose(
                            legacy=legacy, anchor=anchor, scene_id=scene_id,
                            scene_entry_registry=scene_entry_registry,
                        )
                        if composed is None:
                            lane_declined = True
                        else:
                            lane_pc = bytes(composed.pc)
                            lane_frame = bytes(composed.frame)
                            lane_actor_count = int(composed.actor_count)
                            lane_reapply_seconds = (
                                float(composed.initial_reapply_ms) / 1000.0
                            )
                            # cp874 net on every lane-authored line: the
                            # one print in this block whose text another
                            # lane composed (bg0001/bg0002 print
                            # chief-owned strings), and the scar this
                            # guards (rounds 86, 142) raises INSIDE the
                            # print call itself.
                            lane_console_lines = [
                                lane_hooks.console_safe(str(line))
                                for line in composed.console_lines
                            ]
                            # CORE-REQUEST (LANE-A 20260829_2321) option
                            # (a): the membership walking back.  Coerced
                            # INSIDE this net like every other lane field:
                            # a malformed membership refuses the whole
                            # census rather than committing a frame whose
                            # server-side bookkeeping then explodes.  None
                            # (the field's default) means the composer
                            # said nothing and the three fields below stay
                            # exactly as they are.
                            lane_membership = composed.membership
                            if lane_membership is None:
                                lane_member_indices = None
                                lane_member_anchor = None
                            else:
                                lane_member_indices = (
                                    None
                                    if lane_membership.population_indices
                                    is None
                                    else tuple(
                                        int(index) for index in
                                        lane_membership.population_indices
                                    )
                                )
                                lane_member_anchor = (
                                    None
                                    if lane_membership
                                    .population_refresh_anchor is None
                                    else tuple(
                                        float(value) for value in
                                        lane_membership
                                        .population_refresh_anchor
                                    )
                                )
                    except Exception as error:
                        # Fail closed, the same net and the same reasoning
                        # as the bg0002 branch above: an escape here
                        # unwinds out of the listener thread (v141:7440
                        # has no except), and there is no frozen fallback
                        # for a lane scene, so a refusal sends NO frame at
                        # all rather than inventing one.
                        self.world_census_refused = True
                        self.events.append(
                            "world_census_lane_composer_refused_"
                            f"{type(error).__name__}"
                        )
                    else:
                        if lane_declined:
                            # The lane looked at the scene and declined --
                            # a permanent, named answer for this process
                            # (composers read boot-loaded registry data;
                            # see census_composer()'s docstring), same
                            # latch shape as the not-home skip below, but
                            # distinguishable from it in the event log.
                            self.world_census_sent = True
                            self.events.append(
                                "world_census_lane_composer_declined_"
                                f"scene_{scene_id}"
                            )
                        else:
                            # The FIRED token prints only on this commit
                            # path, never on refuse/decline, so a WIRED-v2
                            # grep that reads it as emission counts only a
                            # census that actually shipped (pf-adversary,
                            # round 73fhoc).
                            lane_hooks.announce_direct_fire(
                                lane_census.module,
                                f"scene_census_composer:{scene_id}",
                            )
                            # Console proof before the frame is queued --
                            # the lane's own lines, in the lane's own
                            # order, same discipline as the siblings.
                            for line in lane_console_lines:
                                print(line)
                            self.world_census_sent = True
                            # Byte counts derived by len() from the actual
                            # queued payloads, never composer-asserted, so
                            # this greppable line cannot disagree with the
                            # wire (pf-adversary, round 73fhoc).
                            self.events.append(
                                "world_census_lane_committed_actors_"
                                f"{lane_actor_count}_pc_"
                                f"{len(lane_pc)}_frame_"
                                f"{len(lane_frame)}"
                            )
                            # RE-157 job 2 / MOB-COMBAT-001.  JUDGMENT CALL,
                            # flagged for review: ``lane_hooks.
                            # SceneCensusResult`` (unlike ``generation`` from
                            # the bg0001/bg0002 builders) carries no per-
                            # actor identity list -- only opaque
                            # ``pc``/``frame`` bytes and, optionally,
                            # PLACEMENT indices via ``membership``, which
                            # this module's own docstring (nonclaim 4) says
                            # must never stand in for actor identities by
                            # coincidental equality.  So this commit cannot
                            # name what it announced and stamps an EMPTY
                            # membership for this scene/generation instead
                            # of a fabricated or stale one: fail closed
                            # means no field mob a lane composes for is
                            # attackable until a lane composer can hand its
                            # own actor identities back (a
                            # ``SceneCensusResult`` field, not this call
                            # site's to add -- lane_hooks is not in this
                            # round's scope).  Latent today, same as the
                            # comment above this block: no lane scene a
                            # player can stand in and fight in exists yet.
                            self.mob_combat_announced_membership_generation += 1
                            self.mob_combat_announced_membership = (
                                mob_combat_membership.build_membership(
                                    scene_id, (),
                                    self.mob_combat_announced_membership_generation,
                                )
                            )
                            # CORE-REQUEST (LANE-B 20260829_2055), THE
                            # THIRD ARRIVAL COMMIT.  pf-adversary (round
                            # k882hm, D3) measured that the round's own
                            # claim of "both arrival census commits" was
                            # short by one: this lane-composer commit
                            # ships a full census and set no stamp, so the
                            # first swing in a lane scene would send the
                            # one-entry frame RE-092 proved erases the
                            # map.  Latent today (no lane claims a scene
                            # a player can stand in and fight in), armed
                            # the day one does.  ``mob_scene_recompose``
                            # has no composer for a lane scene yet, so the
                            # stamp buys the NAMED refusal
                            # (``..._skipped_no_composer_for_scene`` plus
                            # the module's console line) instead of the
                            # silent anchor-less skip.
                            try:
                                self.census_anchor_record = (
                                    mob_scene_recompose.census_anchor(
                                        scene_id, anchor, lane_actor_count,
                                    )
                                )
                            except mob_scene_recompose.SceneRecomposeError:
                                self.events.append(
                                    "world_census_lane_anchor_stamp_refused"
                                )
                            # CORE-REQUEST (LANE-A 20260829_2321) option
                            # (a), the write half: all three server-side
                            # membership fields, from the one coerced
                            # value, in one place -- half-taking them is
                            # the ChooseNPC-recomposes-the-old-town
                            # failure the seam's MembershipReset exists
                            # to make unwritable.
                            #
                            # SAFE UNDER THE ARRIVAL TRIGGER (round
                            # `4w5j25`, checked because this is the one
                            # write that could have made it unsafe): from
                            # this round these fields can be armed while
                            # ``last_target_pos`` is still None, which is
                            # exactly the state v141:4395-4416 unpacks
                            # without a None check.  It cannot reach that
                            # code: ``lane_membership`` is non-None only
                            # when the scene's ChooseNPC responder is
                            # registered AND production_allowed, and such a
                            # scene's TARGET_VITAL/CHOOSE_NPC frames are
                            # answered by the responder branch far above
                            # WITHOUT calling ``super().dispatch(parsed)``
                            # at all.  The responder itself declines on a
                            # None ``last_target_pos``
                            # (lane_a_choose_npc_scene14.respond), so the
                            # pre-movement click is a named decline and no
                            # frame, never a crash.  A future responder
                            # that is allowed but does NOT claim the vital
                            # family would break that chain -- which is why
                            # it is written down here rather than left to
                            # be re-derived.
                            if lane_membership is not None:
                                self.population_indices = (
                                    lane_member_indices
                                )
                                self.population_refresh_anchor = (
                                    lane_member_anchor
                                )
                                self.world_census_indices = (
                                    lane_member_indices
                                )
                                self.events.append(
                                    "world_census_lane_membership_set_"
                                    + (
                                        "cleared"
                                        if lane_member_indices is None
                                        else str(len(lane_member_indices))
                                    )
                                )
                            census_actions = [
                                (
                                    f"WORLD_CENSUS_LANE_SCENE{scene_id}"
                                    f"_INITIAL_{lane_actor_count}",
                                    lane_pc, lane_frame, 0.0,
                                ),
                                (
                                    f"WORLD_CENSUS_LANE_SCENE{scene_id}"
                                    f"_REAPPLY_{lane_actor_count}",
                                    lane_pc, lane_frame,
                                    lane_reapply_seconds,
                                ),
                            ]
                elif scene_id != world_population.SCENE_ID:
                    # Away from home the bg0001 census is not merely useless,
                    # it is wrong: every actor in it is encoded with scene 1.
                    # The inherited branch is already disarmed, so this sends
                    # NOTHING rather than delivering dock NPCs into another
                    # map.  Reachable for any scene no lane's census
                    # composer claims (see the lane branch above) once
                    # BUILD-002 can move a boot off scene 1.
                    self.world_census_sent = True
                    self.events.append(
                        f"world_census_skipped_scene_{scene_id}_not_home"
                    )
                else:
                    count, count_source = (
                        world_population.census_count_for_dispatch()
                        if world_census_actor_count is None
                        else (
                            world_population.effective_actor_count(
                                world_census_actor_count
                            ),
                            world_population.COUNT_SOURCE_CALLER,
                        )
                    )
                    try:
                        generation = world_population.build_world_population(
                            legacy, anchor, count,
                            scene_id=scene_id, count_source=count_source,
                        )
                    except Exception as error:
                        # Catch-all on purpose.  The builder reads frozen
                        # constants by plain attribute access and calls frozen
                        # serializers, so drift can arrive as AttributeError or
                        # struct.error as easily as ValueError, and an escape
                        # from here unwinds out of the listener thread
                        # (v141:7440 has no except).  Fail closed to the wire
                        # that shipped: rebuild the frozen three-actor
                        # collection and queue it under its own labels, so a
                        # refusing session is byte-for-byte the old session
                        # rather than a session with no population at all.
                        self.world_census_refused = True
                        self.events.append(
                            "world_census_compose_refused_"
                            f"{type(error).__name__}"
                        )
                        census_actions = self._world_census_frozen_fallback(
                            anchor,
                        )
                    else:
                        # CORE-REQUEST (MOB-DEATH-001, MOB_DEATH_WIRING: "hand
                        # corpse_override to whatever builds the scene
                        # census... PASS THE LEDGER, or the rebuild heals
                        # every wounded monster back to its ceiling as
                        # well").  Not a no-op: full_roster_override returns
                        # all 13 roster identities unconditionally (dead,
                        # damaged, and untouched alike), not just the ones
                        # that changed, so every boot now overrides those 13
                        # placements to their hostile/dead body instead of
                        # letting world_population's default census entry
                        # stand. world_population.py has no override
                        # parameter and is out of this round's scope to
                        # edit, so this rebuilds the SAME bytes with the SAME
                        # encoder over the wider input instead.
                        # CORE-REQUEST (LANE-B 20260829_1445, the half R227
                        # left open): the ledger handed to this override MUST
                        # belong to the scene this census composes for, or
                        # full_roster_override raises
                        # ledger_disagrees_with_register OUTSIDE the
                        # fail-closed catch-all above and unwinds the
                        # listener thread (v141:7440 has no except).  This
                        # branch only composes for world_population.SCENE_ID,
                        # but mob_combat_ledger is re-opened lazily at attack
                        # time, so after a scene round trip with no attack
                        # since returning it still holds the OTHER scene's
                        # rows.  Re-sync ledger+roster from the same scene id
                        # and describe the override from the rows the sync
                        # returned, never from a second independent
                        # load_roster() call.
                        synced_roster = self._sync_combat_scene_state()
                        if synced_roster is None:
                            # Registry does not address the scene: no
                            # roster, no override.  Ship the census as
                            # built rather than pairing bg0001 rows with a
                            # ledger of unknown scene -- the exact mismatch
                            # measured above.  Unreachable while the
                            # registry addresses SCENE_ID; latched loudly
                            # in case that ever changes.
                            mob_death_override = ()
                            self.events.append(
                                "mob_death_census_override_skipped_"
                                "scene_unaddressed"
                            )
                        else:
                            mob_death_override = mob_death.full_roster_override(
                                legacy, synced_roster,
                                self.mob_death_register,
                                ledger=self.mob_combat_ledger,
                            )
                        if mob_death_override:
                            generation = _apply_mob_death_census_override(
                                legacy, generation, mob_death_override,
                            )
                        # GT-084 item (5).4, and the COO's console gate of
                        # 2026-08-27 03:45 ("verify with a headless boot and a
                        # grep of the console before opening any ticket that
                        # depends on hostiles").  Until this line the console
                        # printed ONE undifferentiated
                        # world_census_committed_actors_N / WORLD_CENSUS line
                        # per boot with no per-identity breakdown, so an
                        # attended tester could not tell a boot whose 13 field
                        # mobs went out hostile from one whose override matched
                        # nothing at all -- GT-084 grepped for FIELD_MOB /
                        # HOSTILE, labels that have never existed on this path,
                        # and read the silence as "no hostile bytes".  The
                        # answer is COMPUTED from the census this boot actually
                        # built (generation.actor_identities, post-splice), not
                        # from what the roster says it SHOULD contain, so a
                        # census that changed shape prints a real `missing`
                        # list instead of a reassuring 13/13.
                        #
                        # Printed OUTSIDE the `if` on purpose: an empty
                        # override is exactly the failure this gate exists to
                        # catch, and it has to print matched=0/0 rather than
                        # print nothing, because "no line" is the state GT-084
                        # already mis-read once.
                        print(mob_death.describe_roster_override_coverage(
                            mob_death_override, generation.actor_identities,
                        )[0])
                        # LANE-B letter 20260829_0744 point 3 (COO-DECISION
                        # 2026-08-29T08:48+07:00 item 3): which shipped mobs
                        # NO owner letter covers, said at boot next to the
                        # census gate above -- so an uncovered scene is seen
                        # the day it ships, not the day a tester stands in
                        # front of it.  G-OBS lines; the module composes
                        # them, only this file may print them.
                        for line in mob_death.describe_widening_coverage():
                            print(line)
                        self.world_census_sent = True
                        # This census resolved every identity it shipped
                        # (census_order drops what it cannot resolve), so the
                        # click frame may be corrected to agree with it.
                        self.world_census_identity_resolved = True
                        self.npc_idle_action_sent = False
                        # THE FIELD THAT KEEPS HOME OFF THE ARRIVAL TRIGGER
                        # (round `4w5j25`): reached only with a real
                        # last_target_pos, because the disjunct at the top of
                        # this block still requires one for
                        # world_population.SCENE_ID.  v141:4395-4416 unpacks
                        # last_target_pos for any chosen identity found in
                        # this tuple and has no None check, and no lane
                        # responder claims scene 1's clicks -- see the
                        # widening comment above for the two ways to fix that
                        # and why neither belongs in a trigger change.
                        self.population_indices = generation.indices
                        self.population_refresh_anchor = generation.anchor
                        self.world_census_actor_count = generation.actor_count
                        # CORE-REQUEST (LANE-B 20260829_2055) chief's half:
                        # the anchor and count travel WITH the scene they
                        # were measured in, so the recompose sites below can
                        # never be handed another scene's pair without the
                        # composer refusing by name.  The two bare
                        # attributes above are kept for their other readers
                        # (arena harness, frozen fallback, click dispatch);
                        # the recompose path reads only this record.  This
                        # branch is home-scene only (see the not-home skip
                        # above), so the stamp is the bg0001 scene id.
                        # Guarded by hand for the same reason the density
                        # console line below is: this runs PAST the
                        # builder's net, after world_census_sent is
                        # latched, and losing the recompose stamp must
                        # cost the recompose (its guard degrades to the
                        # one-entry frame), never the listener thread.
                        try:
                            self.census_anchor_record = (
                                mob_scene_recompose.census_anchor(
                                    world_population.SCENE_ID,
                                    generation.anchor,
                                    generation.actor_count,
                                )
                            )
                        except mob_scene_recompose.SceneRecomposeError:
                            self.events.append(
                                "world_census_anchor_stamp_refused"
                            )
                        self.world_census_indices = generation.indices
                        self.events.append(
                            "world_census_committed_actors_"
                            f"{generation.actor_count}_pc_{generation.pc_bytes}"
                            f"_frame_{generation.frame_bytes}"
                        )
                        # The lane's own console line, printed before the frame
                        # is queued: it carries the wire count read back out of
                        # the bytes and the body check beside the assembled
                        # count, which is the difference between "115 actors
                        # went out" and "the header says 115".  ASCII only --
                        # the bridge console is cp874.
                        print(world_population.census_console_line(generation))
                        try:
                            # This reads scenarios/world_scene_density_001.json
                            # from disk on every call with no caching, so a
                            # missing/corrupt file (bad deploy, wrong cwd,
                            # packaging miss) must never be allowed to escape
                            # here: it's a diagnostic console line, not the
                            # census itself, and an uncaught exception would
                            # unwind out of the listener thread (v141:7440 has
                            # no except) after world_census_sent is already
                            # latched -- killing the daemon GAME-listener
                            # thread for the whole process over a print().
                            print(world_density.m1_console_line(legacy, anchor))
                        except Exception as error:
                            self.events.append(
                                "world_density_console_line_failed_"
                                f"{type(error).__name__}"
                            )
                        # CORE-REQUEST (GT-DIAG-MULTI-OBJECT-001).  See
                        # diag_multi_object_wiring.py's own module docstring
                        # and RUNTIME_WIRING_PATCH for the full reasoning.
                        # Off (the default -- this repo ships no
                        # config/diag_multi_object.json) this block reads
                        # exactly two attributes and leaves census_pc/frame
                        # byte-identical to generation.pc/frame.
                        activation = diag_multi_object_wiring.activate(
                            self.token, scene_id,
                        )
                        if activation.event is not None:
                            self.events.append(activation.event)
                        self.diag_multi_objects = activation.objects
                        census_pc, census_frame = generation.pc, generation.frame
                        if activation.objects:
                            for line in diag_multi_object_wiring.console_lines(
                                activation.objects,
                            ):
                                print(line)
                            census_pc, census_frame, refusal = (
                                diag_multi_object_wiring.census_frames(
                                    legacy, generation, activation.objects,
                                )
                            )
                            if refusal is not None:
                                self.events.append(refusal)
                                self.diag_multi_objects = ()
                            print(diag_multi_object_wiring.describe_census(
                                generation, self.diag_multi_objects, census_pc,
                            ))
                        # RE-157 job 2 / MOB-COMBAT-001: stamp exactly the
                        # actor identities THIS commit put on the wire.
                        # ``generation.actor_identities`` is the base
                        # bg0001 set (post mob-death-override splice, which
                        # only rewrites entry bytes, never the identity
                        # set -- see ``_apply_mob_death_census_override``);
                        # unioned with any diag-widen actor identities when
                        # ``self.diag_multi_objects`` is non-empty (off by
                        # default -- see the comment above), since those
                        # extra actors are also announced in
                        # ``census_pc``/``census_frame`` below.  Not
                        # ``world_census_indices``, which is a PLACEMENT
                        # index, not an actor identity
                        # (mob_combat_membership.py's own docstring,
                        # nonclaim 4).
                        self.mob_combat_announced_membership_generation += 1
                        self.mob_combat_announced_membership = (
                            mob_combat_membership.build_membership(
                                scene_id,
                                frozenset(generation.actor_identities)
                                | frozenset(
                                    obj.mob.actor_identity
                                    for obj in self.diag_multi_objects
                                ),
                                self.mob_combat_announced_membership_generation,
                            )
                        )
                        # The count is in the LABEL too: v141 prints every
                        # queued action as "[G>] <label> (N bytes)" at SEND
                        # time (v141:7762), so the attended tester can tell the
                        # four staircase boots apart from the console alone,
                        # and a boot that composed but never sent is visibly
                        # different from one that sent.  Labels keep the
                        # CENSUS count (generation.actor_count) so no existing
                        # grep moves -- the DIAG_CENSUS line above carries the
                        # diagnostic +5 separately.
                        census_actions = [
                            (
                                "WORLD_CENSUS_INITIAL_"
                                f"{generation.actor_count}",
                                census_pc, census_frame, 0.0,
                            ),
                            (
                                "WORLD_CENSUS_REAPPLY_"
                                f"{generation.actor_count}",
                                census_pc, census_frame,
                                world_population.INITIAL_REAPPLY_MS / 1000.0,
                            ),
                        ]

            if self.arena_scenario is not None and self.arena_spawned:
                if (
                    is_p30_target_observation(legacy, parsed)
                    and not self.arena_target_captured
                ):
                    self.arena_target_captured = True
                    version = _active_arena_version(self.arena_scenario).lower()
                    self.events.append(
                        f"arena_{version}_p30_target_kind2_captured_no_reply"
                    )
            # CORE-REQUEST (MOB-COMBAT-001 / MOB-DEATH-001).  UNCONDITIONAL
            # and ADDITIVE: computed after everything above (including every
            # scenario-gated EA7D reader, which -- when its own flag is
            # active -- already consumed a 2-or-6-vital-count ActionVital
            # frame and returned before this line), so no existing pinned
            # dispatch loses or gains a byte.  A non-ActionVital frame, or an
            # ActionVital frame no earlier branch claimed, reaches this
            # unchanged and gets nothing extra unless its target resolves to
            # a field-mob identity.
            mob_combat_actions = (
                self._dispatch_mob_combat(parsed)
                if nested_id == legacy.ACTION_VITAL else []
            )
            # CORE-REQUEST-014 (Columbus/quest 3021).  Same UNCONDITIONAL,
            # ADDITIVE convention as MOB-COMBAT-001 just above: computed after
            # everything else has had first claim on the frame, and a no-op
            # for every nested_id this lane does not care about.
            columbus_quest_actions = (
                self._dispatch_columbus_quest3021(parsed)
                if nested_id in (
                    legacy.TARGET_VITAL, legacy.CHOOSE_NPC,
                    legacy.QUEST_OPERATE_VITAL,
                ) else []
            )
            return (actions + arena_actions + ground_loot_actions
                    + nameprop_actions + census_actions + mob_combat_actions
                    + columbus_quest_actions)
    return PersistentGameSessionState
