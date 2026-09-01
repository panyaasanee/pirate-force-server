"""LANE-A: the level field an ordinary census never sent.

WHY THIS MODULE EXISTS.  ``GT-192`` put every warped-into actor on the
owner's screen at ``LV 1``.  The reason is not that the client applies only
part of a record it received: the ordinary census composers never encode a
level at all.  The frozen helper ``current/pf_login_game_server_v141.py``'s
``make_npc_attr`` (lines 1139-1195, frozen, chief's file, NOT touched here)
takes name / HP / speed / scene / seq and has no ``level`` parameter, and its
BasicAttr mask is ``0x0004|0x0008|0x0100|0x0200`` plus optional ``0x0001``
(name) and ``0x0040`` (speed).  Bit ``0x0002`` is never set: the field is
MEASURED absent from the wire.  What the client draws in its place is
``[PROPOSED]`` -- "its own default" is the obvious reading, but the static
chain from ``BasicAttr +0x5E`` to the label formatter is Codex's own
still-to-prove item 1, so this module claims only that the server sent
nothing.  HP is encoded, which is why HP looked right on the same screen
where level did not -- ``LV 1`` was never evidence that the client ignores
a level it was sent.  (Codex static audit
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
(lines 1564-1608) has shipped the SAME TREATMENT of this one field for
hostile monsters since RE-117 landed: widen the frozen body's own mask by
the bit and put the tagged value at its own ascending-mask-bit position.
Not the same function, and this is not it "minus the faction half" -- that
one also asks the frozen serializer for the mined walk-speed field (bit
0x0040, which no census body carries and which this module never asks for:
see ``tests/test_npc_gait_wire.py``'s tripwire), and it cross-checks its
level position against a separately-derived faction offset, which an
ordinary census body has nothing to compare against.  This module therefore
carries its own independent position check (see ``with_level``), and both
modules splice rather than re-serialize for the same reason:
re-implementing the frozen body would mean a second thing to keep in step
with chief's file, and a splice can REFUSE when that file's layout moves.

WHERE THE VALUE COMES FROM.  Callers pass their own scene's mined
``MOBS.n_LEVEL_MIN``: ``SceneIdentity.level`` for the scenes that resolve
identities through one (and their per-actor console line already prints
it), ``Bg0002Placement.level`` for scene 2, whose rows carry the column
directly and whose console line does not print it.  This module never
invents a level and has no default -- a caller with no mined value cannot
call it at all, which is the point: a made-up number on the owner's screen
is worse than the honest ``LV 1`` it would replace.

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

LEVEL_TAG = 0x12
LEVEL_WIDTH = 2
LEVEL_SPLICE_BYTES = 1 + LEVEL_WIDTH

# The field the level is spliced in FRONT of: BasicAttr bit 0x0004/0x0008,
# the current/max HP pair, written as two u32 under tag 0x14.  Named here
# because the splice's position check is "the HP pair starts exactly where
# the level is about to go" -- a check that fails when the frozen layout
# moves, unlike an inverse-of-itself reduction, which cannot.
HP_TAG = 0x14

# A u16 field on the wire, but the mined domain is narrower: every row of
# the shipped ``CONSTDATA_TH__MOBS`` table has 1 <= n_LEVEL_MIN <= 255, and
# ``scene2_prison_exile_tables`` validates its own rows to that same range.
# The ceiling is the mined domain rather than the field width so that a
# caller handing this an HP value (or any other four-digit column by
# mistake) fails closed instead of shipping it.  Level 0 is the client's own
# uninitialised value and would be indistinguishable from "not sent".
LEVEL_MIN = 1
LEVEL_MAX = 255
# What the wire could carry if a mined level above the current domain ever
# appears: kept as a named fact so the ceiling above reads as a decision.
LEVEL_FIELD_MAX = 0xFFFF


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
    current_hp: int,
    max_hp: int,
) -> bytes:
    """``baseline`` with BasicAttr bit 0x0002 and its u16 level spliced in.

    ``baseline`` must be exactly what ``legacy.make_npc_attr`` returned for
    this actor, and ``current_hp``/``max_hp`` the pair it was built with.
    Everything else about the body is left byte-for-byte alone: the result
    is the baseline with one bit of the mask value set and
    ``LEVEL_SPLICE_BYTES`` inserted at the one position the mask order puts
    them.

    HOW THE POSITION IS CHECKED, AND WHY IT IS NOT CHECKED THE OBVIOUS WAY.
    An earlier draft of this function "verified" the splice by inverting it
    and comparing with the baseline.  pf-adversary showed that check is a
    tautology: the inverse uses the same offset the splice used, so it
    reproduces the baseline for ANY offset, correct or not, and it accepted
    a level deliberately spliced four bytes late, into the middle of the HP
    field, on a nameless body.  The check kept here is independent instead:
    the level goes in front of the current/max HP pair, so the bytes at the
    computed position must BE that pair, encoded from the caller's own HP
    values.  That is what goes red when the frozen body's layout moves --
    measured, not asserted: adding one field after the mask in a copy of the
    frozen serializer makes this refuse on named AND nameless bodies, where
    the old check refused only named ones (and 25 of bg0004's 109 shipped
    placements are nameless).

    Refuses, rather than producing bytes, when:

    * the body already sets bit 0x0002 -- a hostile entry from lane B's
      hostile encoder already carries its own level, and splicing a second
      one is the double-field/double-mask failure the assignment letter
      names for scene 14's hostile subset;
    * the mask's name bit disagrees with ``basic_name``, or the bytes where
      the name should be are not that name;
    * the HP pair is not where the mask order says it is (above);
    * the level is not a plain int in ``LEVEL_MIN..LEVEL_MAX``.
    """
    if type(baseline) is not bytes:
        raise CensusLevelError("baseline must be the frozen body's bytes")
    if type(basic_name) is not str:
        raise CensusLevelError("basic_name must be a str")
    _require_int(actor_identity, "actor identity", 0, 0xFFFFFFFFFFFFFFFF)
    _require_int(level, "level", LEVEL_MIN, LEVEL_MAX)
    _require_int(current_hp, "current hp", 0, 0xFFFFFFFF)
    _require_int(max_hp, "max hp", 0, 0xFFFFFFFF)

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
    # The independent position check (see this function's docstring): the
    # level's own place in the ascending mask order is immediately in front
    # of the current/max HP pair, so that pair must start exactly here.
    hp_pair = (
        bytes(legacy.u32tag(HP_TAG, current_hp))
        + bytes(legacy.u32tag(HP_TAG, max_hp))
    )
    if baseline[level_at:level_at + len(hp_pair)] != hp_pair:
        raise CensusLevelError(
            "frozen make_npc_attr body drift: the current/max HP pair does "
            "not start at offset %d, where the ascending mask order puts the "
            "field this splice inserts itself in front of -- the layout "
            "moved and the splice point is stale" % level_at
        )

    composed = (
        baseline[:mask_at]
        + int(mask | BASIC_BIT_LEVEL).to_bytes(2, "little")
        + baseline[mask_at + 2:level_at]
        + bytes(legacy.u16tag(LEVEL_TAG, level))
        + baseline[level_at:]
    )
    # Length is arithmetic, not a check: a 3-byte insert into a body always
    # grows it by 3.  It is asserted (not raised) so the statement stays in
    # the code without pretending to be a guard -- pf-adversary measured
    # that the equivalent raise can never fire.
    assert len(composed) == len(baseline) + LEVEL_SPLICE_BYTES
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
    movement_speed: float | None = None,
) -> bytes:
    """One census actor's NPCAttr body, with its mined level on the wire.

    The single call an ordinary scene composer's ``_entry`` makes instead of
    ``legacy.make_npc_attr`` directly.  Keyword-only on purpose: the frozen
    helper's first parameter is the serializer's own "MOBS/template u16 at
    +0x78" and takes the REAL ``MOBS.n_ID``, never the Mob-Set number, and a
    positional call site is exactly how ``GT-078`` put Mob-Set numbers on the
    owner's screen.

    ``movement_speed`` (round `2p4n3h`, LANE-A) is handed straight to the
    frozen helper, which sets BasicAttr bit 0x0040 and writes the f32 at
    +0x54 AFTER the current/max HP pair.  The level splice below goes in
    FRONT of that pair, so the two fields never contend for a position and
    this function's own layout check is unaffected by the parameter -- the
    HP-pair anchor it verifies is the same bytes either way.  ``None``
    keeps the pre-`2p4n3h` body byte-for-byte, which is what the callers
    that are not census composers still want.  See ``world_census_gait``
    for where the value comes from and what it gates.
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
        movement_speed=movement_speed,
    )
    return with_level(
        legacy, baseline,
        actor_identity=actor_identity,
        basic_name=basic_name,
        level=level,
        current_hp=current_hp,
        max_hp=max_hp,
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
