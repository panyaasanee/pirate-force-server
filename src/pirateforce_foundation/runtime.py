"""Lifecycle-aware V141 state factory for the real legacy TCP listeners."""
import math
import threading
import time

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
    LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST,
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
from .population_scenario import require_population_scenario
from .npc_hostile_hypothesis import (
    NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA,
    NPC_HOSTILE_PLAYER_IDENTITY_HI,
    NPC_HOSTILE_PLAYER_IDENTITY_LO,
    build_npc_hostile_sweep,
    npc_hostile_wire_unlock,
    require_npc_hostile_hypothesis_scenario,
    resolve_probe as resolve_npc_hostile_probe,
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
                     second_password_mode="required",
                     monotonic_clock=None,
                     close_timer_factory=None):
    active_modes = sum(value is not None for value in (
        scenario, scene_load_scenario, population_scenario,
        item_move_capture_scenario, item_move_hypothesis_scenario,
        logout_hypothesis_scenario, chat_input_hypothesis_scenario,
        channel_message_hypothesis_scenario,
        delete_actor_hypothesis_scenario,
        delete_refresh_hypothesis_scenario,
        stats_progression_hypothesis_scenario,
        hp_death_hypothesis_scenario,
        runtimeres_death_hypothesis_scenario,
        damage_model_hypothesis_scenario,
        damage_hp_link_hypothesis_scenario,
        remote_player_hypothesis_scenario,
        npc_hostile_hypothesis_scenario,
    ))
    if active_modes > 1:
        raise ValueError(
            "Arena, scene-load, population, item-move capture, item-move "
            "hypothesis, logout hypothesis, chat input hypothesis, channel "
            "message hypothesis, delete actor hypothesis, delete refresh "
            "hypothesis, stats progression hypothesis, hp death hypothesis, "
            "runtimeres death hypothesis, damage model hypothesis, damage "
            "hp link hypothesis, remote player hypothesis, and npc hostile "
            "hypothesis scenarios are mutually exclusive"
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
    second_password_mode = require_second_password_mode(second_password_mode)
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
                self.worldinfo_last_payload = None
                self.worldinfo_stored_count = 0
                self.chat_input_echo_count = 0
                self.channel_message_sweep_count = 0
                self.stats_progression_sweep_count = 0
                self.hp_death_sweep_count = 0
                self.runtimeres_death_sweep_count = 0
                self.damage_model_sweep_count = 0
                self.damage_hp_link_sweep_count = 0
                self.remote_player_sweep_count = 0
                self.npc_hostile_sweep_count = 0
                self.npc_hostile_player_faction_start_sent = False
                self.delete_actor_soft_delete_count = 0
                self.delete_refresh_list_rebuild_count = 0
                self.transport_socket_closer = None
                self.second_password_bypass_sent = False
                self.second_password_bypass_keepalive_started = False
                self.second_password_bypass_last_sent_at = None
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
            # PF-HYPOTHESIS-LEDGER: HYP-PF-028 active
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
            # The designed responses are fully composed and pinned before
            # the lease is touched; no bytes are queued unless the clean
            # close commits.
            worldinfo_response = None
            if worldinfo_first:
                worldinfo_response = make_worldinfo_first_response(
                    legacy, self.worldinfo_last_payload,
                )
            return_select_response = None
            if return_select_first:
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

        def _npc_hostile_start_game_response(self, pc, frame):
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
            x, y, z, heading, _flags, _moving = target
            selected = self.foundation.selected
            candidate = Position(
                selected.position.scene_id,
                selected.position.scene_seq,
                x, y, z, heading,
            )
            if candidate != selected.position:
                self.foundation.checkpoint(candidate)

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

        def dispatch(self, parsed):
            nested_id = parsed.nested_id
            if logout_hypothesis_scenario is not None and self.logout_acknowledged:
                # After the acknowledged logout (HYP-PF-012 lane below) the
                # lease is closed; every later frame on this connection is
                # counted and ignored so no other lane can write through a
                # closed session.
                self.rx_frames += 1
                self.events.append("logout_hypothesis_post_ack_frame_no_reply")
                return []
            if logout_hypothesis_scenario is not None and nested_id == LOGOUT_VITAL_ID:
                return self._dispatch_logout_hypothesis(parsed)
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
                self._sync_frozen_inventory_state()
                if npc_hostile_hypothesis_scenario is not None:
                    # NPC-HOSTILE-DISPATCH (HYP-PF-027): the entry half of the
                    # SCENE-005 pairing.  Recompose the same StartGame response
                    # through the frozen faction-1 serializer, or fall back to
                    # the byte-identical production response with a named
                    # event -- in which case the sweep below refuses by name.
                    pc, frame = self._npc_hostile_start_game_response(
                        pc, frame,
                    )
                self.start_game_reply_sent = True
                self.events.append("start_game_res_scene_identity_sent")
                load_only = scene_load_scenario is not None
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
                        tp_pc, tp_frame = legacy.make_login_teleport(1, 0)
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

            actions = super().dispatch(parsed)
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
            return actions + arena_actions
    return PersistentGameSessionState
