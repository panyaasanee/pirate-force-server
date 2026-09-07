"""LANE-B (COMBAT), P-2: name the fields in which two NPCAttr bodies differ.

WHY THIS EXISTS.  ``GT-288`` set 2 came back on 2026-09-07 (ka1-A results
``pf_bridge/notes_to_chief/20260907_2027_KA1A-R323-RESULTS-...``, owner
confirmed 19:46) with six dummies drawn on one screen: every ``N-*`` row
green -- including the one carrying ``actor_type`` 5 and the one wearing a
different skin -- and every ``M-*`` row that had a nameplate pink.  So the
name colour is decided by neither the outer ``ActorEntry`` type tag nor the
avatar preset.  It is decided by something inside the ``NPCAttr`` BODY that
differs between the NPC prototype (``n_ID`` 1) and the monster prototype
(``n_ID`` 916).  COO-ORDER 2026-09-07T20:50+07:00 makes listing those fields
this lane's first job, and this module is how the list is produced: by
walking both bodies with the frozen encoders' own grammar and naming each
field, instead of eyeballing a hexdump.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Nothing, directly -- this module
sends no frame.  What it ships is the pin under ``name_colour_sweep`` set 3:
every candidate row in that set is asserted, by execution, to differ from its
own ``BASE`` in EXACTLY ONE named field of this walk.  That is what makes the
attended run readable ("the pink one is the row whose only change was X")
rather than a second hexdump.

HOW THE GRAMMAR IS DERIVED, AND FROM WHERE.  Not guessed:

* The tag widths are the frozen encoders in
  ``current/pf_login_game_server_v141.py`` (``u8tag``/``u16tag``/``u32tag``/
  ``qwordtag``/``f32tag``/``wstr_tag``) -- the same closed-set discipline
  ``lane_hooks/lane_a_island_trigger_log._TAG_WIDTHS`` already holds.  An
  unknown tag STOPS the walk; it never guesses a width.
* The emission ORDER is mask-driven and ascending by mask bit, which is the
  rule ``field_mobs.hostile_npc_attr`` states for BasicAttr and
  ``mob_viewer_link`` states (from the codex ``order`` column) for NPCAttr.
  This module therefore walks the two masks and expects each present bit's
  field in that order, rather than scanning for loose tag bytes.
* The offsets and semantic names are the codex, read not invented:
  ``pf_bridge/notes_to_chief/reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv``
  and ``PF_A2_ATTR_FIELD_DELTA.tsv``, ``class`` = ``BasicAttr`` / ``NPCAttr``,
  direction ``W`` (the server side).  Where the codex has NO row -- and it
  has none for BasicAttr bits 0x0002, 0x0004, 0x0008, 0x0010, 0x0020 -- the
  offset here is the string ``UNCITED`` and the source names the RE that gave
  us the bit.  A reader must be able to tell a codex offset from this
  project's own working belief at a glance; ``+0x44``/``+0x48`` for the HP
  pair, for instance, comes from ``make_npc_attr``'s own V64 docstring, not
  from the codex, and is written that way below.

WHAT THIS MODULE REFUSES TO DO.  It does not decide a colour, name a
``FontStyleID``, or rank the candidates.  A field being in the diff means the
two prototypes disagree about it, nothing more; which one the client's
selector reads is the attended question set 3 exists to ask.  It also refuses
bits nobody in this codebase ships (BasicAttr 0x0010/0x0020, the MP pair
RE-117 named but for which no mined source exists): their tag is unknown, so
walking past them would be a guess, and a guess here silently mis-names every
field after it.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Fixed-width tags, from the frozen encoders named in the docstring.
#: A closed set on purpose: unknown tag => refuse, never a guessed width.
TAG_WIDTHS = {
    0x0B: 1,   # u8tag
    0x12: 2,   # u16tag
    0x14: 4,   # u32tag (HP pair, faction, n_ENEMY)
    0x26: 4,   # u32tag (movement flags; not used by make_npc_attr bodies)
    0x2A: 4,   # f32tag
    0x32: 8,   # qwordtag
}
#: tag, then a u32 byte count, then that many bytes (wstr_tag/astr_tag).
TAG_LENGTH_PREFIXED = (0x44, 0x48)

UNCITED = "UNCITED"


class NpcAttrBodyWalkError(ValueError):
    """Raised instead of returning a field list nobody can vouch for."""


@dataclass(frozen=True)
class FieldSpec:
    """One emission slot: what it is called, where it lives, who says so."""

    key: str
    mask_bit: int | None  # None = always present
    tag: int
    offset: str
    semantic: str
    source: str


#: BasicAttr, ascending mask bit -- the order both composers splice into.
BASIC_ALWAYS = (
    FieldSpec(
        "attr_head", None, 0x0B, UNCITED, "leading u8 written 1 by every body",
        "current/pf_login_game_server_v141.py make_npc_attr (frozen encoder)",
    ),
    FieldSpec(
        "actor_identity", None, 0x32, UNCITED, "actor identity qword",
        "current/pf_login_game_server_v141.py make_npc_attr (frozen encoder)",
    ),
    FieldSpec(
        "basic_field_mask", None, 0x12, "BasicAttr+0x70", "field_presence_mask",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 0 (PROVEN_EXACT, W)",
    ),
)

BASIC_BIT_FIELDS = (
    FieldSpec(
        "basic_name", 0x0001, 0x48, "BasicAttr+0x28",
        "NameBoard_Player_LABEL_NAME_text",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 1 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "level", 0x0002, 0x12, UNCITED, "MOBS.n_LEVEL (level)",
        "RE-117 via field_mobs.BASIC_BIT_LEVEL/LEVEL_TAG -- no codex row",
    ),
    FieldSpec(
        "current_hp", 0x0004, 0x14, "BasicAttr+0x44 (not codex)", "current HP",
        "make_npc_attr V64 docstring (0x43D730/0x43BD70) -- no codex row",
    ),
    FieldSpec(
        "max_hp", 0x0008, 0x14, "BasicAttr+0x48 (not codex)", "max HP",
        "make_npc_attr V64 docstring (0x43D730/0x43BD70) -- no codex row",
    ),
    FieldSpec(
        "movement_speed", 0x0040, 0x2A, "BasicAttr+0x54",
        "MOBS.n_SPEED_WALK_to_initial_visual_horizontal_locomotion_scalar",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 7 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "dying_threshold", 0x0080, 0x2A, "BasicAttr+0x58",
        "Main_Dead_threshold_operand_vs_DURATION_DYING_minus_0_5",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 8 (PROVEN_ROLE_ONLY, W)",
    ),
    FieldSpec(
        "scene_id", 0x0100, 0x12, "BasicAttr+0x5C", "scene_id__SCENE_NAME.n_ID",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 9 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "scene_sequence", 0x0200, 0x32, "BasicAttr+0x60",
        "TeleportVital_qword_at_0x18_copied_from_BasicAttr_plus_0x60",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 10 (PROVEN_ROLE_ONLY, W)",
    ),
    FieldSpec(
        "faction", 0x0400, 0x14, "BasicAttr+0x68", "CNetNPC.template.n_FACTION",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 11 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "enemy_flag", 0x0800, 0x14, "BasicAttr+0x6C", "CNetNPC.template.n_ENEMY",
        "codex PF_ATTR_FIELD_SEMANTICS.tsv order 12 (PROVEN_EXACT, W)",
    ),
)

NPC_ALWAYS = FieldSpec(
    "npc_field_mask", None, 0x0B, "NPCAttr+0xBC", "npc_field_mask",
    "codex PF_A2_ATTR_FIELD_DELTA.tsv order 18 (PROVEN_EXACT, W)",
)

NPC_BIT_FIELDS = (
    FieldSpec(
        "template_id", 0x01, 0x12, "NPCAttr+0x78", "npc_mobs_template_id",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 19 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "quest_gate_flags", 0x02, 0x0B, "NPCAttr+0x7A",
        "quest_gate_flags__bit1_requires_bit2__bit2_CheckApproachTarget",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 20 (PARTIAL, W)",
    ),
    FieldSpec(
        "visual_preset", 0x04, 0x48, "NPCAttr+0x7C",
        "visual_preset_resource_basename",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 21 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "associated_actor_id", 0x08, 0x32, "NPCAttr+0x98",
        "associated_actor_id_for_name_color",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 22 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "hp_enemy_actor_id", 0x10, 0x32, "NPCAttr+0xA8", "hp_enemy_actor_id",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 23 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "target_panel_friendly_actor_id", 0x20, 0x32, "NPCAttr+0xA0",
        "target_panel_friendly_actor_id",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 24 (PROVEN_EXACT, W)",
    ),
    FieldSpec(
        "npc_linked_actor_id", 0x40, 0x32, "NPCAttr+0xB0",
        "npc_linked_actor_id_compared_to_local_player_and_used_for_actor_resolution",
        "codex PF_A2_ATTR_FIELD_DELTA.tsv order 25 (PROVEN_ROLE_ONLY, W)",
    ),
)

#: The BasicAttr bits RE-117 named (the MP pair) for which this codebase has
#: no source, no tag and no codex row.  Present in a body => refuse the walk.
BASIC_BITS_WITHOUT_A_KNOWN_TAG = 0x0010 | 0x0020

_BASIC_KNOWN = 0
for _spec in BASIC_BIT_FIELDS:
    _BASIC_KNOWN |= _spec.mask_bit
_NPC_KNOWN = 0
for _spec in NPC_BIT_FIELDS:
    _NPC_KNOWN |= _spec.mask_bit


@dataclass(frozen=True)
class WalkedField:
    """One field as it actually appeared in a body."""

    spec: FieldSpec
    body_offset: int
    raw: bytes
    value: object

    @property
    def key(self) -> str:
        return self.spec.key


def _read(body: bytes, at: int, spec: FieldSpec) -> tuple[object, bytes, int]:
    if at >= len(body):
        raise NpcAttrBodyWalkError(
            "body ends before field %s; the frozen layout moved" % spec.key
        )
    tag = body[at]
    if tag != spec.tag:
        raise NpcAttrBodyWalkError(
            "field %s expected tag 0x%02X at offset %d, found 0x%02X"
            % (spec.key, spec.tag, at, tag)
        )
    at += 1
    if tag in TAG_LENGTH_PREFIXED:
        if at + 4 > len(body):
            raise NpcAttrBodyWalkError("truncated length prefix for %s" % spec.key)
        size = int.from_bytes(body[at:at + 4], "little")
        at += 4
        if size > len(body) - at:
            raise NpcAttrBodyWalkError("length prefix of %s runs past the body" % spec.key)
        raw = body[at:at + size]
        at += size
        text = raw.decode("utf-16le") if tag == 0x48 else raw.decode("ascii")
        return text, raw, at
    width = TAG_WIDTHS.get(tag)
    if width is None:
        raise NpcAttrBodyWalkError("unknown tag 0x%02X for field %s" % (tag, spec.key))
    if at + width > len(body):
        raise NpcAttrBodyWalkError("truncated value for %s" % spec.key)
    raw = body[at:at + width]
    at += width
    if tag == 0x2A:
        import struct

        return struct.unpack("<f", raw)[0], raw, at
    return int.from_bytes(raw, "little"), raw, at


def walk(body: bytes) -> tuple[WalkedField, ...]:
    """Every field in ``body``, in emission order, named.

    Refuses -- rather than returning a partial or a guess -- on an unexpected
    tag, a truncated value, a mask bit this codebase has no tag for, or a body
    with trailing bytes the grammar does not account for.
    """
    if type(body) is not bytes:
        raise NpcAttrBodyWalkError("body must be bytes")
    out: list[WalkedField] = []
    at = 0
    for spec in BASIC_ALWAYS:
        value, raw, at = _read(body, at, spec)
        out.append(WalkedField(spec, at - len(raw), raw, value))
    basic_mask = out[-1].value
    if basic_mask & BASIC_BITS_WITHOUT_A_KNOWN_TAG:
        raise NpcAttrBodyWalkError(
            "BasicAttr mask 0x%04X sets a bit (0x0010/0x0020) this codebase "
            "has no tag for; walking past it would be a guess" % basic_mask
        )
    if basic_mask & ~(_BASIC_KNOWN | BASIC_BITS_WITHOUT_A_KNOWN_TAG):
        raise NpcAttrBodyWalkError(
            "BasicAttr mask 0x%04X sets an unknown bit" % basic_mask
        )
    for spec in BASIC_BIT_FIELDS:
        if basic_mask & spec.mask_bit:
            value, raw, at = _read(body, at, spec)
            out.append(WalkedField(spec, at - len(raw), raw, value))
    value, raw, at = _read(body, at, NPC_ALWAYS)
    out.append(WalkedField(NPC_ALWAYS, at - len(raw), raw, value))
    npc_mask = value
    if npc_mask & ~_NPC_KNOWN:
        raise NpcAttrBodyWalkError("NPCAttr mask 0x%02X sets an unknown bit" % npc_mask)
    for spec in NPC_BIT_FIELDS:
        if npc_mask & spec.mask_bit:
            fvalue, fraw, at = _read(body, at, spec)
            out.append(WalkedField(spec, at - len(fraw), fraw, fvalue))
    if at != len(body):
        raise NpcAttrBodyWalkError(
            "%d trailing bytes after the last field the masks account for"
            % (len(body) - at)
        )
    return tuple(out)


@dataclass(frozen=True)
class FieldDelta:
    """One way in which two bodies disagree."""

    spec: FieldSpec
    left: object   # None means: absent from the left body
    right: object  # None means: absent from the right body
    present_in_both: bool


def diff(left: bytes, right: bytes) -> tuple[FieldDelta, ...]:
    """The fields in which two walked bodies disagree, in emission order.

    A field counts as a difference when it is present in one body and absent
    from the other, or present in both with different values.  Nothing here
    ranks the results or calls one of them the colour: see the module
    docstring.
    """
    left_fields = {f.key: f for f in walk(left)}
    right_fields = {f.key: f for f in walk(right)}
    out: list[FieldDelta] = []
    for spec in BASIC_ALWAYS + BASIC_BIT_FIELDS + (NPC_ALWAYS,) + NPC_BIT_FIELDS:
        lhs = left_fields.get(spec.key)
        rhs = right_fields.get(spec.key)
        if lhs is None and rhs is None:
            continue
        if lhs is not None and rhs is not None:
            if lhs.raw == rhs.raw:
                continue
            out.append(FieldDelta(spec, lhs.value, rhs.value, True))
            continue
        out.append(
            FieldDelta(
                spec,
                None if lhs is None else lhs.value,
                None if rhs is None else rhs.value,
                False,
            )
        )
    return tuple(out)


def _show(value: object) -> str:
    if value is None:
        return "ABSENT"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return "%d (0x%X)" % (value, value)
    if isinstance(value, float):
        return "%.3f" % value
    return '"%s"' % value


def format_diff_lines(left_label: str, right_label: str, deltas) -> tuple[str, ...]:
    """ASCII console lines for a diff -- the bridge console is cp874."""
    lines = [
        "P2_BODY_DIFF %s vs %s fields=%d" % (left_label, right_label, len(deltas)),
    ]
    for index, delta in enumerate(deltas, start=1):
        lines.append(
            "P2_BODY_DIFF %02d %s %s %s: %s -> %s"
            % (
                index,
                delta.spec.offset,
                delta.spec.key,
                "both" if delta.present_in_both else "one-sided",
                _show(delta.left),
                _show(delta.right),
            )
        )
    return tuple(lines)
