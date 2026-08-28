"""Typed player ActorAttr projections outside the immutable V141 source."""
import struct

# CORE-REQUEST-022: class was never emitted (ActorAttr +0x8C, mask bit
# 0x00000001), which left every login client-side class-default at 0 and
# blocked the skill window (GT learn-skill measured this directly).  Level
# was never emitted either (BasicAttr +0x5E, mask bit 0x0002).  Both offsets,
# tags and bits match report STATS-PROG-001's real gate addresses (GetClass
# 0x460160, GetLv 0x460050) -- corroborated independently by PANYA-DECISION
# 20260828_0125 row x13/x2. [MEASURED] offsets/tags/bits above.
# [PROPOSED, not measured] the specific values below: Gladiator (class 1) at
# level 1 as the fixed minimum every fresh boot sends -- not yet threaded
# from any real per-character class/level source, same status as runtime.py's
# MOB_COMBAT_DEFAULT_ATTACKER constant.
PLAYER_LOGIN_CLASS_ID = 1
PLAYER_LOGIN_LEVEL = 1

# CORE-REQUEST-023 "probe base 1" widening (PANYA-DECISION 20260828_0125),
# round x6a85q (R208): movement speed only.  MP current/max and STR/CON/DEX/
# INT/PER wire POSITIONS are equally [MEASURED] (same citations as speed,
# below) but are deliberately NOT wired here -- this repo has no committed
# source for what VALUE a level-1 Gladiator's MP or five ability scores
# actually are:
#   - PF_JOB001 (CHARCREATE_CLASS static boundary) enumerates that table's 37
#     named columns -- icons, appearance, equipment, s_SKILL_* strings -- and
#     none of them is a stat score; no "s_SCORE" column exists in that table
#     or anywhere else in this repository (grepped, zero hits).
#   - PF_STATS_PROG001 s8.4 says so explicitly: "the actual per-level
#     curves... remain unknown and would require decoding [external] data
#     files, which this milestone did not do." STANDARD_STATUS (n_HPMAX,
#     n_STAMINAMAX) and POTENTIAL (n_STRENGH, n_CONSTITUTION, n_AGILITY,
#     n_INTELLECT, n_PERCEPTION) are named but their column values were
#     never decoded.
# Shipping five flat, invented ability scores (or a guessed MP number) would
# look "complete" without being correct -- exactly the failure mode
# PANYA-DECISION 20260828_0125's own probe was reacting to (a character that
# LOOKS fine but silently blocks features/reads wrong later).  RE-117's own
# nonclaim #3 draws the identical line for mob MP ("do not invent a value,
# do not borrow the PC formula") -- the player side is held to the same
# rule.  See CLIENT_RE_QUEUE.md's new RE ticket (mined by RE runner,
# following RE-117's own static method) for the real numbers; wiring them in
# is then a one-line change to the constants below, not a new RE-position
# hunt, since the offsets/tags/masks are already proven:
#   MP:      BasicAttr +0x4C/+0x50, u32 tag 0x14, mask 0x0010/0x0020
#            (PF_STATS_PROG001 s4 gates 0x465772/0x465786; independently
#            confirmed by RE-117, notes_to_chief/20260828_0414_RE-117-
#            RESULT-NPCATTR-INHERITS-LEVEL-MP-BITS.md, disassembling
#            ``BasicAttr::Serialize`` 0x004656F0 directly).
#   STR/CON/DEX/INT/PER: ActorAttr +0x82/0x84/0x86/0x88/0x8A, u16 tag 0x12,
#            mask 0x20/0x40/0x80/0x100/0x200 (PF_STATS_PROG001 s5 gates
#            0x46631F..0x46638A).
#
# Speed IS wired: BasicAttr +0x54, f32 tag 0x2A, mask 0x0040 (PF_STATS_PROG001
# s4 gate 0x46579A; same bit/tag/offset mob_death.py's BASIC_BIT_MOVEMENT_
# SPEED already wires for field mobs).  [PROPOSED, not measured] the VALUE
# 400.0 -- unlike the MP/stat gap above, this is the owner's own single,
# deliberately-chosen client-observable value from her probe session (same
# status as PLAYER_LOGIN_CLASS_ID/PLAYER_LOGIN_LEVEL: one named constant an
# owner picked, not an invented placeholder standing in for unknown
# per-class data).
PLAYER_LOGIN_MOVEMENT_SPEED = 400.0

# BasicAttr mask bit added by this widening.
_BASIC_BIT_MOVEMENT_SPEED = 0x0040


def _encode_character_name(legacy, character_name: str) -> bytes:
    """Encode the persisted name with the exact ActorAttr+0x164 wstring codec."""
    if not isinstance(character_name, str):
        raise TypeError("character name must be str")
    if not character_name:
        raise ValueError("empty character name")
    try:
        encoded = character_name.encode("utf-16le")
    except UnicodeEncodeError as exc:
        raise ValueError("character name is not valid UTF-16") from exc
    if len(encoded) > 0xFFFFFFFF:
        raise ValueError("character name exceeds the PcBinary wstring length field")
    return legacy.wstr_tag(character_name)


def _make_actor_attr_with_name(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, *, basic_faction: int | None,
) -> bytes:
    """Project the exact ActorAttr name field and optional frozen faction field."""
    name_wire = _encode_character_name(legacy, character_name)
    basic_mask = 0x000C | 0x0100 | 0x0200
    faction_wire = b""
    if basic_faction is not None:
        basic_mask |= 0x0400
        faction_wire = legacy.u32tag(0x14, basic_faction)
    return (
        legacy.u8tag(0x0B, 1)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + legacy.u32tag(0x14, 100)
        + legacy.u32tag(0x14, 100)
        + legacy.u16tag(0x12, scene_id)
        + bytes([0x32]) + struct.pack("<Q", scene_seq)
        + faction_wire
        + bytes([0x32]) + struct.pack("<II", 0x01000800, 0)
        + legacy.u8tag(0x05, 1)
        + bytes([0x32]) + struct.pack("<Q", legacy.V116_INITIAL_CASH)
        + name_wire
    )


def make_actor_attr_with_name(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str,
) -> bytes:
    """Build the normal player ActorAttr with its persisted player name.

    This is the proven NAME-002 baseline byte-for-byte -- left untouched by
    CORE-REQUEST-022 because several other lanes crosscheck their own
    pinned bytes against this exact function.  The real login path uses
    ``make_actor_attr_with_name_and_class`` below instead; this function
    stays the frozen reference the other lanes compare against.
    """
    return _make_actor_attr_with_name(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        basic_faction=None,
    )


def _make_actor_attr_with_name_and_class(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, class_id: int, level: int, *,
    basic_faction: int | None,
) -> bytes:
    """Project name+class+level+speed and an optional frozen faction.

    CORE-REQUEST-023 (PANYA-DECISION 20260828_0125 / COO-DECISION 0146):
    every booted character must carry at least class id (or the skill window
    never opens, per GT learn-skill), a level, and movement speed. MP
    current/max and the five primary attributes are NOT added here -- see
    the module docstring above the constants for why (no committed value
    source; wiring them in later is a one-line change, the wire positions
    are already proven). Adds level+speed to the proven
    ``_make_actor_attr_with_name`` projection, in the same ascending-mask-bit
    emission order the rest of this codebase's field tables use: BasicAttr
    level 0x0002, hp_current/hp_max 0x0004/0x0008, movement speed 0x0040,
    scene id/seq 0x0100/0x0200; ActorAttr class_id 0x00000001, cash
    0x00000800, name 0x01000000 -- so this stays additive, not a rewrite of
    the proven frame. The optional faction field is spliced in at the exact
    same relative position ``_make_actor_attr_with_name`` uses for it.
    """
    name_wire = _encode_character_name(legacy, character_name)
    basic_mask = 0x0002 | 0x000C | _BASIC_BIT_MOVEMENT_SPEED | 0x0100 | 0x0200
    faction_wire = b""
    if basic_faction is not None:
        basic_mask |= 0x0400
        faction_wire = legacy.u32tag(0x14, basic_faction)
    return (
        legacy.u8tag(0x0B, 1)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + legacy.u16tag(0x12, level)
        + legacy.u32tag(0x14, 100)
        + legacy.u32tag(0x14, 100)
        + legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED)
        + legacy.u16tag(0x12, scene_id)
        + bytes([0x32]) + struct.pack("<Q", scene_seq)
        + faction_wire
        + bytes([0x32]) + struct.pack("<II", 0x01000801, 0)
        + legacy.u8tag(0x05, 1)
        + legacy.u32tag(0x19, class_id)
        + bytes([0x32]) + struct.pack("<Q", legacy.V116_INITIAL_CASH)
        + name_wire
    )


def make_actor_attr_with_name_and_class(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str,
    class_id: int = PLAYER_LOGIN_CLASS_ID, level: int = PLAYER_LOGIN_LEVEL,
) -> bytes:
    """Build the real login ActorAttr: proven baseline plus class+level+speed."""
    return _make_actor_attr_with_name_and_class(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        class_id, level, basic_faction=None,
    )


def make_actor_attr_with_name_class_and_faction(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, basic_faction: int,
    class_id: int = PLAYER_LOGIN_CLASS_ID, level: int = PLAYER_LOGIN_LEVEL,
) -> bytes:
    """The class+level+speed baseline above, plus the frozen faction-1 probe field.

    Same identity/scene/faction guard as ``make_actor_attr_with_basic_
    faction``.  CORE-REQUEST-022 needs this because runtime.py recomposes
    every flagless production login (and the scenario-gated HYP-PF-027
    pinned-identity probe) with ``basic_faction=1`` ON TOP OF the
    class+level-carrying baseline -- if that recompose kept using the
    frozen, class-less ``make_actor_attr_with_basic_faction``, its own
    length-drift guard would refuse on every call, since the two branches'
    lengths would no longer agree (see ``runtime.py``'s
    ``NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA`` check).  This keeps that delta
    exactly 5 bytes (one ``u32tag`` faction field), same as before.
    """
    if basic_faction != 1 or scene_seq != 0 or scene_id not in (1, 2):
        raise ValueError(
            "only the exact Scene2 or SCENE-007 Port Royal faction-1 probe is allowed"
        )
    return _make_actor_attr_with_name_and_class(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        class_id, level, basic_faction=basic_faction,
    )


# PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen
def make_actor_attr_with_basic_faction(
    legacy, identity_lo: int, identity_hi: int, scene_id: int, scene_seq: int,
    character_name: str, basic_faction: int,
) -> bytes:
    """Add the frozen faction value to the named player ActorAttr projection.

    Kept byte-for-byte as GT-032 proved it -- no longer called by
    ``LegacyProjector.start_game`` (see ``make_actor_attr_with_name_class_
    and_faction`` above), but still the frozen reference offline tests
    compare against directly.
    """
    if basic_faction != 1 or scene_seq != 0 or scene_id not in (1, 2):
        raise ValueError(
            "only the exact Scene2 or SCENE-007 Port Royal faction-1 probe is allowed"
        )
    return _make_actor_attr_with_name(
        legacy, identity_lo, identity_hi, scene_id, scene_seq, character_name,
        basic_faction=basic_faction,
    )
