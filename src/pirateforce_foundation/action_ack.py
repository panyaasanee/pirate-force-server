"""Strict SCENE-007 EA7D observation and no-damage acknowledgement."""
from dataclasses import dataclass
import math
import struct

from . import pose_trial
from .mob_loot import (
    MobLootContractError,
    preserve_ground_in_runtime_res_vitals,
)


@dataclass(frozen=True)
class SceneActionAck:
    action: int
    target_identity: int
    scene_id: int


def parse_scene006_ea7d(legacy, parsed, policy: SceneActionAck):
    """Return audited fields only for the exact SCENE-006 ActionVital shape."""
    if (parsed.outer_id != legacy.GSCN_RUNTIME_PROTOCOL_REQ
        or parsed.outer_version != 0 or parsed.outer_mask != 2
        or parsed.vital_count not in (2, 6)):
        return None
    try:
        cursor = legacy.Cursor(parsed.raw_pc)
        if (cursor.u16(0x12) != legacy.GSCN_RUNTIME_PROTOCOL_REQ
            or cursor.u32(0x14) != 0 or cursor.u8(0x08) != 0
            or cursor.u8(0x0B) != 2 or cursor.u16(0x12) != parsed.vital_count):
            return None
        expected = ([legacy.ACTION_VITAL, legacy.TARGET_POS_VITAL] if parsed.vital_count == 2
                    else [legacy.ON_LAND_VITAL] * 4 + [legacy.ACTION_VITAL, legacy.TARGET_POS_VITAL])
        fields = None
        for vital_id in expected:
            if cursor.u16(0x12) != vital_id or cursor.u8(0x0B) != 0:
                return None
            start = cursor.p
            if vital_id == legacy.ON_LAND_VITAL:
                for _ in range(4): cursor.f32(0x2A)
                cursor.u16(0x0F)
            elif vital_id == legacy.TARGET_POS_VITAL:
                for _ in range(4): cursor.f32(0x2A)
                cursor.u8(0x0B); cursor.u8(0x0B)
            else:
                body = parsed.raw_pc[start:start + 64]
                if len(body) != 64: return None
                cursor.p += 64
                isolated = legacy.ParsedOuter(
                    legacy.GSCN_RUNTIME_PROTOCOL_REQ, 0, 2, 1,
                    legacy.ACTION_VITAL, 0, body, 15, b"",
                )
                fields = legacy.parse_action_vital(isolated)
        if cursor.remain() != 0 or fields is None:
            return None
    except (ValueError, EOFError, struct.error):
        return None
    floats = tuple(fields[key] for key in (
        "heading_f32_38", "x_f32_3c", "y_f32_40", "z_f32_44",
    ))
    if (
        fields["consumed_bytes"] != 64
        or fields["field_qword_18"] != 0
        or fields["field_qword_20"] != policy.target_identity
        or fields["field_qword_28"] != 0
        or fields["action_u32_30"] != policy.action
        or fields["field_u32_34"] != 0
        or fields["field_u8_48"] != 0
        or fields["field_u16_4a"] != policy.scene_id
        or fields["field_u8_4c"] != 0
        or not all(math.isfinite(value) for value in floats)
    ):
        return None
    return fields


def _say(line):
    """Print one trial line, and never raise into ``state.dispatch()``.

    ``print`` to a closed stdout raises ``ValueError`` and to a broken pipe
    ``BrokenPipeError`` -- both measured by pf-adversary (D10) -- and the
    frozen ``game_listener`` above this call has no except handlers
    (interlock X07), so either one would kill the thread over a log line.
    """
    if line is None:
        return
    try:
        print(line)
    except Exception:  # noqa: BLE001 - a log line never kills the listener
        pass


def build_action_vital_echo(legacy, fields, performer_identity: int,
                            action_selector: int, refusals=None):
    """``(pc, frame)``: one ActionVital echo, only performer and ``+0x30``
    (``action_selector``) differing from the audited request in ``fields``.

    Factored out of ``make_scene007_action_ack`` (COO-DECISION 20260905_0248)
    so the production ``_dispatch_mob_combat`` hit path
    (``make_production_hit_pose_echo``) composes through the SAME encoder as
    the SCENE-007 scenario gate instead of a second one -- the shape PR #782
    named for this lane's other composers ("composes exactly what the
    per-kill site composes, same encoder, not a second path").

    ``refusals``: optional list the caller may pass to learn that the ground
    preserving composer refused and the original bytes were shipped instead.
    A refusal is otherwise invisible to every artifact an attended run
    collects -- the events list, the DB and --export-events all look
    identical on both paths -- and "the absence of a console line" is not
    evidence.  pf-adversary raised this as D6 this round.
    """
    # PF-HYPOTHESIS-LEDGER: HYP-PF-002 frozen
    if not 0 < performer_identity <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("selected performer identity is outside uint64")
    payload = (
        legacy.qwordtag(0x32, performer_identity)
        + legacy.qwordtag(0x32, fields["field_qword_20"])
        + legacy.qwordtag(0x32, fields["field_qword_28"])
        + legacy.u32tag(0x14, action_selector)
        + legacy.u32tag(0x19, fields["field_u32_34"])
        + legacy.f32tag(fields["heading_f32_38"])
        + legacy.f32tag(fields["x_f32_3c"])
        + legacy.f32tag(fields["y_f32_40"])
        + legacy.f32tag(fields["z_f32_44"])
        + legacy.u8tag(0x0B, fields["field_u8_48"])
        + legacy.u16tag(0x12, fields["field_u16_4a"])
        + legacy.u8tag(0x0B, fields["field_u8_4c"])
    )
    vitals = [(legacy.ACTION_VITAL, 0, payload)]
    # COO-DECISION 20260902_0646 item 2: the FIRST opt-in site for the ground
    # preserving composer.  One site at a time, on purpose: the earlier ask --
    # one wrap over make_runtime_vitals in app.py -- was WITHDRAWN after it was
    # measured killing the game_listener thread on three live paths (chief
    # letter 20260902_0605) while helping P-1 on none.
    #
    # Item 4: a refusal ships the ORIGINAL bytes and says so out loud.  The
    # except is NARROW, and that is the whole safety argument, not a shortcut.
    # preserve_ground_in_runtime_res_vitals DRIVES legacy.make_runtime_vitals
    # itself (mob_loot.py:3415) and only raises MobLootContractError AFTER that
    # call has already returned.  So on this branch the fallback call is known
    # to work.  A broad except would be the bug it looks like a fix for: any
    # exception from the shared composer would print a reassuring "refused"
    # line and then re-raise out of state.dispatch(), and the frozen
    # game_listener has zero except handlers (interlock X07,
    # tools/pf_multiplayer_readiness_audit.py:701) -- the thread dies.  That is
    # exactly the failure letter 0605 withdrew the wrap for.  Measured by
    # pf-adversary this round against a composer patched to raise struct.error.
    # Anything that is not a refusal therefore propagates exactly as it does on
    # main today, where this line called the composer directly.
    #
    # Type name only, no exception message: COO 0646 item 4 says <ExcType>, and
    # this repo has written that rule down three times from measurement -- an
    # exception MESSAGE can carry non-cp874 bytes and raise UnicodeEncodeError
    # inside this very handler (gm/chat_command_action.py:1391,
    # lane_hooks/__init__.py:180, persistence_canon_gate.py:229).  The reason
    # name is not lost: it rides the event below, which --export-events keeps.
    # [ROUND yqbwri, pf-adversary]: this print used to be a bare ``print()``,
    # reachable only through ``make_scene007_action_ack`` -- the SCENE-007
    # scenario gate ``GT-247``'s own R314 result measured DEAD on a real
    # client (``is_scene_remote_hostile_target`` never admits an ActionVital
    # that also carries TargetPos).  This function is now ALSO called from
    # ``make_production_hit_pose_echo``, wired into the always-live
    # ``_dispatch_mob_combat`` -- so the exposure ``_say``'s own docstring
    # names (a closed stdout or a broken pipe killing the listener thread
    # over a log line) is reachable from production for the first time,
    # during the exact attended sweep this ticket exists to run.  Routed
    # through ``_say`` for that reason; the type-name-only content is
    # unchanged.
    try:
        return preserve_ground_in_runtime_res_vitals(legacy, vitals)
    except MobLootContractError as exc:
        _say("GROUND_VITALS_PRESERVE_REFUSED " + type(exc).__name__)
        if refusals is not None:
            # args[0] is this lane's own reason NAME (mob_loot.py:1082), an
            # ASCII constant -- safe to carry, unlike the message.
            refusals.append(str(exc.args[0]) if exc.args else "UNNAMED")
        return legacy.make_runtime_vitals(vitals)


def make_scene007_action_ack(legacy, fields, performer_identity: int,
                             refusals=None, *, environ=None):
    """Build one ActionVital; only performer differs from the audited request.

    ``environ``: the mapping the ``ATTACK-POSE-ONE-FIELD-AB-001`` trial gate
    reads instead of the process environment.  For tests only; the runtime
    call site does not pass it, and with it absent the gate reads
    ``os.environ`` exactly as an attended boot does.  "Only performer
    differs" above stays literally true on every unarmed boot: see
    ``pose_trial.selector_for_reply``, which returns the request's own
    ``+0x30`` and no console line while ``PF_POSE_TRIAL`` is unset.
    """
    # ATTACK-POSE-ONE-FIELD-AB-001 (COO-DECISION 20260904_2141).  The ONE
    # field the trial may move, and it moves nowhere unless an owner armed
    # PF_POSE_TRIAL in this process.  The line is computed here and PRINTED
    # AT THE EXIT below, after a frame exists: an earlier version printed
    # here, and pf-adversary pointed out (D5) that the composer below can
    # propagate anything that is not MobLootContractError, which would leave
    # the attended log claiming a selector for a frame that was never sent.
    action_selector, pose_line = pose_trial.selector_for_reply(
        fields["action_u32_30"], environ,
    )
    composed = build_action_vital_echo(
        legacy, fields, performer_identity, action_selector, refusals,
    )
    _say(pose_line)
    return composed


def make_production_hit_pose_echo(legacy, fields, performer_identity: int,
                                  hit_number: int, *, environ=None):
    """``(pc, frame)`` for one extra ActionVital echo on an accepted
    production mob-combat hit, or ``None`` -- compose and send NOTHING.

    ``ATTACK-POSE-ONE-FIELD-AB-001``, routed by ``COO-DECISION 20260905_0248``
    to the ORDINARY, unflagged ``_dispatch_mob_combat`` path instead of the
    SCENE-007 scenario gate above: ``GT-247``'s own R314 result measured that
    route dead twice over (``is_scene_remote_hostile_target`` wants
    ``vital_count == 1`` and the real client's ActionVital always carries
    TargetPos alongside it; separately, the head of ``main`` cannot even
    boot ``--scene-load-scenario`` right now -- ``COO-DECISION
    20260905_0250``).

    Returns ``None`` on an unset or malformed ``PF_POSE_TRIAL`` -- the
    inherited v141 dispatch already echoed this exact request's own
    ``+0x30`` back before ``_dispatch_mob_combat`` ever ran (see that
    method's own docstring: it is called UNCONDITIONALLY and ADDITIVELY
    after ``super().dispatch(parsed)``), so an unarmed or misconfigured
    boot must ship NOTHING beyond what main already sends today -- not a
    second, byte-identical echo of the same frame.

    ``hit_number``: the caller's own count of accepted hits this session
    (``state.mob_combat_hit_count``, already incremented for the hit this
    call answers), 1-indexed, and the only state this function or
    ``pose_trial.selector_for_hit`` carries across hits -- the list index
    is derived from it, not from any counter this module keeps itself.
    """
    action_selector, pose_line = pose_trial.selector_for_hit(
        hit_number, environ,
    )
    if pose_line is not None:
        _say(pose_line)
    if action_selector is None:
        return None
    return build_action_vital_echo(
        legacy, fields, performer_identity, action_selector,
    )
