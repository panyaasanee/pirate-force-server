"""LANE-A: the level field an ordinary census never sent.

WHY THIS MODULE EXISTS.  ``GT-192`` put every warped-into actor on the
owner's screen at ``LV 1``.  The reason is not that the client applies only
part of a record it received: the ordinary census composers never encode a
level at all.  The frozen helper ``current/pf_login_game_server_v141.py``'s
``make_npc_attr`` (lines 1139-1195, frozen, chief's file, NOT touched here)
takes name / HP / speed / scene / seq and has no ``level`` parameter, and its
BasicAttr mask is ``0x0004|0x0008|0x0100|0x0200`` plus optional ``0x0001``
(name) and ``0x0040`` (speed).  Bit ``0x0002`` is never set, so the client
draws its own default.  HP is encoded, which is why HP looked right on the
same screen where level did not -- ``LV 1`` was never evidence that the
client ignores a level it was sent.  (Codex static audit
``CODEX_URGENT_20260901_2340_LEVEL-OMITTED-NOT-PARTIAL-DECODE.md``, and the
assignment to this lane in
``notes_to_chief/20260901_2358_CHIEF-TO-LANE-A-...-assigned.md``.)

WHAT THE FIELD IS, AND WHO PROVED IT.  ``RE-117``
(``20260828_0414_RE-117-RESULT-NPCATTR-INHERITS-LEVEL-MP-BITS.md``): the
NPCAttr serializer ``0x00466EB0`` always calls the common BasicAttr
serializer ``0x004656F0`` first, so a BasicAttr field proven on the owner's
own PC-actor probe is a field of an NPCAttr body too.  Level is BasicAttr
mask bit ``0x0002``, object ``+0x5E``, written as a ``u16`` under tag
``0x12`` (writer ``0x00465736..0x0046574A``, reader
``0x00465870..0x00465884``).

WHY A SPLICE AND NOT A NEW SERIALIZER.  ``field_mobs.hostile_npc_attr``
(lines 1564-1608) has shipped exactly this splice for hostile monsters since
RE-117 landed: widen the frozen body's own mask by the one bit and put the
one tagged value at its own ascending-mask-bit position.  This module is
that same operation with the faction half removed, so the ordinary census
gets the proven treatment rather than a second derivation of it.  Both
modules deliberately splice rather than re-serialize: re-implementing the
frozen body would mean a second thing to keep in step with chief's file, and
the splice REFUSES (it never guesses) the moment that file's layout moves.

WHERE THE VALUE COMES FROM.  Callers pass their own scene's mined
``MOBS.n_LEVEL_MIN`` (``SceneIdentity.level``, the same column the scene's
console line already prints).  This module never invents a level and has no
default: a scene with no mined level column -- bg0001/Port Royal today --
must not call this at all, because a made-up number on the owner's screen is
worse than the honest ``LV 1`` it replaces.

WHAT THIS MODULE DELIBERATELY DOES NOT TOUCH.  Name colour, label style,
actor type, identity sign, faction.  ``P0-2`` is not closed and the same
Codex letter is explicit that colour is a different boundary
(``BUILD_IMPACT_COLOR: NOT_READY_FOR_POLICY_CHANGE``); a level splice that
quietly changed one of those would make the next colour round's evidence
unreadable.
"""
from __future__ import annotations

from typing import Any

# BasicAttr mask bits, ascending -- the order the frozen serializer writes
# their values in, which is what makes the splice position computable.
BASIC_BIT_NAME = 0x0001
BASIC_BIT_LEVEL = 0x0002
BASIC_BIT_HP_CURRENT = 0x0004
BASIC_BIT_FACTION = 0x0400

LEVEL_TAG = 0x12
LEVEL_WIDTH = 2
LEVEL_SPLICE_BYTES = 1 + LEVEL_WIDTH

# A u16 field.  The floor is 1 because level 0 is the client's own
# uninitialised value and would be indistinguishable from "not sent".
LEVEL_MIN = 1
LEVEL_MAX = 0xFFFF


class CensusLevelError(ValueError):
    """The frozen body is not the shape this splice was derived on."""


def _require_int(value: Any, what: str, low: int, high: int) -> int:
    if type(value) is not int:
        raise CensusLevelError("%s must be a plain int, not %r" % (what, value))
    if not low <= value <= high:
        raise CensusLevelError(
            "%s %d is outside %d..%d" % (what, value, low, high))
    return value


def basic_mask_offset(legacy: Any, baseline: bytes, actor_identity: int) -> int:
    """Offset of the BasicAttr u16 mask VALUE inside a frozen NPCAttr body.

    Derived from the frozen head rather than written down as a constant, the
    same way ``field_mobs._basic_mask_offset`` derives it: the head is the
    DBAttribute mask byte plus the tagged identity qword, then the mask's own
    tag byte, then the little-endian u16.
    """
    head = (
        bytes(legacy.u8tag(0x0B, 1))
        + bytes(legacy.qwordtag(0x32, actor_identity))
    )
    if not baseline.startswith(head):
        raise CensusLevelError(
            "frozen make_npc_attr head drift: the body no longer opens with "
            "the DBAttribute mask and the tagged identity, so the mask "
            "offset this splice needs cannot be derived"
        )
    # +1 skips the mask's own tag byte and lands on the little-endian u16.
    return len(head) + 1


def with_level(
    legacy: Any,
    baseline: bytes,
    *,
    actor_identity: int,
    basic_name: str,
    level: int,
) -> bytes:
    """``baseline`` with BasicAttr bit 0x0002 and its u16 level spliced in.

    ``baseline`` must be exactly what ``legacy.make_npc_attr`` returned for
    this actor.  Everything else about the body is left byte-for-byte alone:
    the result is the baseline with two bits of the mask value changed and
    ``LEVEL_SPLICE_BYTES`` inserted at the one position the mask order puts
    them, checked by rebuilding the baseline back out of the result before
    returning it.

    Refuses, rather than producing bytes, when:

    * the body already sets bit 0x0002 -- a hostile entry from
      ``field_mobs.hostile_npc_attr`` already carries its own level, and
      splicing a second one is the double-field/double-mask failure the
      assignment letter names for scene 14's hostile subset;
    * the mask's name bit disagrees with ``basic_name``, or the bytes where
      the name should be are not that name -- either means the frozen layout
      moved and the insertion point is stale;
    * the level is not a plain int in ``LEVEL_MIN..LEVEL_MAX``.
    """
    if type(baseline) is not bytes:
        raise CensusLevelError("baseline must be the frozen body's bytes")
    if type(basic_name) is not str:
        raise CensusLevelError("basic_name must be a str")
    _require_int(actor_identity, "actor identity", 0, 0xFFFFFFFFFFFFFFFF)
    _require_int(level, "level", LEVEL_MIN, LEVEL_MAX)

    mask_at = basic_mask_offset(legacy, baseline, actor_identity)
    mask = int.from_bytes(baseline[mask_at:mask_at + 2], "little")
    if bool(mask & BASIC_BIT_NAME) is not bool(basic_name):
        raise CensusLevelError(
            "frozen make_npc_attr name bit drift: mask 0x%04X does not agree "
            "with a %s body" % (mask, "named" if basic_name else "nameless")
        )
    if mask & BASIC_BIT_LEVEL:
        raise CensusLevelError(
            "this body already sets bit 0x0002: it carries a level already "
            "(a hostile entry does), and a second splice would double the "
            "field"
        )
    if not mask & BASIC_BIT_HP_CURRENT:
        raise CensusLevelError(
            "frozen make_npc_attr mask drift: 0x%04X has no HP bit, so the "
            "field this splice inserts itself in front of is gone" % mask
        )

    name_bytes = bytes(legacy.wstr_tag(basic_name)) if basic_name else b""
    level_at = mask_at + 2 + len(name_bytes)
    if name_bytes and baseline[mask_at + 2:level_at] != name_bytes:
        raise CensusLevelError(
            "frozen make_npc_attr body drift: the name is no longer the "
            "field right after the mask, so the level splice point is stale"
        )

    composed = (
        baseline[:mask_at]
        + int(mask | BASIC_BIT_LEVEL).to_bytes(2, "little")
        + baseline[mask_at + 2:level_at]
        + bytes(legacy.u16tag(LEVEL_TAG, level))
        + baseline[level_at:]
    )
    if len(composed) != len(baseline) + LEVEL_SPLICE_BYTES:
        raise CensusLevelError("levelled NPCAttr length drift")
    # Rebuild the baseline out of the result: the ONLY differences allowed
    # are the one mask bit and the inserted field.  Anything else that moved
    # is a defect this catches before the bytes reach a client.
    rebuilt = (
        composed[:mask_at]
        + int(mask).to_bytes(2, "little")
        + composed[mask_at + 2:level_at]
        + composed[level_at + LEVEL_SPLICE_BYTES:]
    )
    if rebuilt != baseline:
        raise CensusLevelError(
            "levelled NPCAttr does not reduce back to the frozen body"
        )
    return composed


def leveled_npc_attr(
    legacy: Any,
    *,
    template_n_id: int,
    actor_identity: int,
    scene_id: int,
    scene_sequence: int,
    visual_preset: str,
    current_hp: int,
    max_hp: int,
    basic_name: str,
    level: int,
) -> bytes:
    """One census actor's NPCAttr body, with its mined level on the wire.

    The single call an ordinary scene composer's ``_entry`` makes instead of
    ``legacy.make_npc_attr`` directly.  Keyword-only on purpose: the frozen
    helper's first parameter is the serializer's own "MOBS/template u16 at
    +0x78" and takes the REAL ``MOBS.n_ID``, never the Mob-Set number, and a
    positional call site is exactly how ``GT-078`` put Mob-Set numbers on the
    owner's screen.
    """
    baseline = legacy.make_npc_attr(
        template_n_id,
        actor_identity,
        scene_id,
        scene_sequence,
        visual_preset,
        current_hp=current_hp,
        max_hp=max_hp,
        basic_name=basic_name,
    )
    return with_level(
        legacy, baseline,
        actor_identity=actor_identity,
        basic_name=basic_name,
        level=level,
    )


def read_level(legacy: Any, body: bytes, actor_identity: int) -> int | None:
    """The level a composed body actually carries, read back off the bytes.

    The wire-side half of the two-layer evidence rule for this field: a test
    (or a headless proof) reads the level out of the bytes that would go to
    the client rather than out of the roster the composer read.  Returns
    ``None`` when the body sets no level bit -- which is what every ordinary
    census entry answered before this module existed.
    """
    if type(body) is not bytes:
        raise CensusLevelError("body must be bytes")
    mask_at = basic_mask_offset(legacy, body, actor_identity)
    mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
    if not mask & BASIC_BIT_LEVEL:
        return None
    at = mask_at + 2
    if mask & BASIC_BIT_NAME:
        # The name is a tagged wstring.  Its header shape is measured off
        # the frozen writer itself (``wstr_tag("")`` is exactly the header),
        # never written down here, so a change to that writer moves this
        # reader with it instead of silently misreading a name length.
        empty = bytes(legacy.wstr_tag(""))
        header = len(empty)
        if body[at] != empty[0]:
            raise CensusLevelError(
                "name bit is set but the field at the name position is tag "
                "0x%02X, not the wstring tag 0x%02X" % (body[at], empty[0])
            )
        length = int.from_bytes(body[at + 1:at + header], "little")
        at += header + length
    if body[at] != LEVEL_TAG:
        raise CensusLevelError(
            "level bit is set but the field at the level position is tag "
            "0x%02X, not 0x%02X" % (body[at], LEVEL_TAG)
        )
    return int.from_bytes(body[at + 1:at + 1 + LEVEL_WIDTH], "little")
