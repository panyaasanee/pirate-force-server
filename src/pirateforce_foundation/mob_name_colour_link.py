"""LANE-B (COMBAT): the per-(viewer, monster) link the name colour needs.

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Today, on main: every monster in a
field scene draws its name in the same colour for everybody, because every
session is sent the SAME NPCAttr bytes for that monster.  The client does not
decide a name colour from the monster alone -- it decides it from a PAIR, and
the second half of that pair is WHO IS LOOKING.  This module composes the one
field that carries the looker.

WHAT IS PROVEN, AND WHERE IT IS WRITTEN DOWN, SO NOBODY RE-DERIVES IT.
``pf_bridge/notes_to_chief/reference_codex_attr/PF_A2_ATTR_FIELD_DELTA.tsv``
lines 150 (R) and 151 (W) -- mirrored in ``PF_ATTR_FIELD_SEMANTICS.tsv``
line 274 -- carry an IMAGE-sourced row for the class chain
``PcRefObject>Attribute>DBAttribute>BasicAttr>NPCAttr``:

    object offset   0x98
    presence gate   (+0xBC & 0x08) != 0
    wire tag        0x32
    wire length     8            (actor_id_qword)
    semantic        associated_actor_id_for_name_color
    status          PROVEN_EXACT, both R and W directions present
    consumer span   0x00443F50..0x004443C5 (the name-style selector)

The W row matters more than the R row for this lane: it is the SERVER side.
This is not a guess and it does not need an RE round -- it needed a grep, and
the letter carrying this round records that grep.

THE TRAP THIS FILE EXISTS TO KEEP SOMEBODY OUT OF.  There are TWO different
fields at +0x98 in this client, in two different classes, and they are not
the same size, tag, or mask:

    ActorAttr+0x98   u8,  tag 0x0B, presence +0x1B4 & 0x04000000
                     -- the relation byte.  See gm/name_color_gate.py, whose
                     docstring already spells this one out.
    NPCAttr+0x98     u64, tag 0x32, presence +0xBC  & 0x08
                     -- the associated actor id.  THIS one.

A reader who has ``gm/name_color_gate.py`` open and then reads a letter about
"+0x98" will believe one of the two documents is wrong.  Neither is: they are
different classes.  Splicing the u8 shape into an NPCAttr body (or the u64
shape into an ActorAttr body) is the exact class of mistake ``GT-218`` proved
kills the client in one frame, so both shapes are named here rather than left
to be inferred from an offset that two classes share.

WHAT THIS MODULE DOES NOT DO.  It does not decide a COLOUR: the colour is the
client's, chosen by the selector span above from this field plus the relation
predicate.  It does not read a faction (faction-only remains banned,
``COO-DECISION 20260905_2348``) and it hardcodes no FontStyleID.  It sends
nothing: it takes a composed NPCAttr body and hands back a longer one, and
the day a caller exists, that caller is where a GT ticket points.

WHERE THE FIELD GOES IN THE BODY, AND WHAT PART OF THAT IS DERIVED RATHER
THAN OBSERVED.  The frozen composer (``make_npc_attr``) writes the NPC field
mask byte and then that mask's fields in ASCENDING BIT ORDER: bit 0x01 is the
template u16 (+0x78), bit 0x04 is the visual-preset wstring (+0x7C), and both
the bit order and the object-offset order agree.  ``field_mobs.
hostile_npc_attr``'s own docstring already states that rule for the BasicAttr
mask in the same body ("each tagged value spliced in at its own
ascending-mask-bit position").  Bit 0x08 is the next bit AND +0x98 is the
next offset, so this module APPENDS its field after the visual preset.

NONCLAIM, stated plainly because it is the one thing here that is inferred:
nobody in this tree has read the NPCAttr serializer's emission order for bit
0x08 itself.  The append position follows the two observed bits and the
ascending rule; it is not an observation of the 0x08 field being written
last.  A caller that puts these bytes on a real socket therefore needs the
attended confirmation the letter for this round asks for, and until then the
only cost of being wrong is carried by that caller, not by this file.
"""
from __future__ import annotations

from typing import Any

#: LANE-B owns this module; there is nothing here a scenario flag could gate
#: that the refusals below do not gate harder, and this lane does not ship
#: work that needs a flag turned on.
production_allowed = True


class MobNameColourLinkError(RuntimeError):
    """Raised, named, instead of composing a body nobody can vouch for."""


REFUSE_VIEWER_IDENTITY_NOT_POSITIVE = "REFUSE_VIEWER_IDENTITY_NOT_POSITIVE"
REFUSE_VIEWER_IS_THE_MONSTER = "REFUSE_VIEWER_IS_THE_MONSTER"
REFUSE_VIEWER_IDENTITY_OUT_OF_RANGE = "REFUSE_VIEWER_IDENTITY_OUT_OF_RANGE"
REFUSE_LINK_BIT_ALREADY_SET = "REFUSE_LINK_BIT_ALREADY_SET"
REFUSE_BODY_TAIL_DRIFT = "REFUSE_BODY_TAIL_DRIFT"

#: The presence bit in the NPC field mask (object +0xBC) that turns the
#: associated-actor id on.  PF_A2_ATTR_FIELD_DELTA.tsv:150/151.
NPC_MASK_BIT_LINKED_IDENTITY = 0x08

#: The wire tag and width of the field itself.  Same rows.
LINKED_IDENTITY_TAG = 0x32
LINKED_IDENTITY_WIRE_LEN = 8

#: The tag the frozen composer uses for the NPC field mask byte itself.
NPC_FIELD_MASK_TAG = 0x0B

#: The two NPC-mask bits the frozen composer already knows about, named so a
#: reader can see why 0x08 appends rather than splices into the middle.
NPC_MASK_BIT_TEMPLATE = 0x01
NPC_MASK_BIT_VISUAL_PRESET = 0x04

#: An unsigned qword is what the wire carries; the selector reads it as two
#: dwords and compares them for exact equality, so any value that does not
#: round-trip through eight bytes is refused here rather than by struct.
LINKED_IDENTITY_CEILING = (1 << 64) - 1

#: The other +0x98, named so nobody splices this shape into that class.  Not
#: used by this module -- it is documentation that has to live beside the
#: constant it is confused with.
OTHER_ACTORATTR_LINK_AT_0X98 = (
    "ActorAttr+0x98 (u8, tag 0x0B, presence +0x1B4 & 0x04000000) is a "
    "DIFFERENT field in a DIFFERENT class -- see gm/name_color_gate.py"
)


def _npc_mask_tail(
    legacy: Any,
    *,
    npc_mask: int,
    template_id: int,
    visual_preset: str,
) -> bytes:
    """The exact tail an NPCAttr body ends with, from the NPC mask byte on.

    The anchor deliberately starts at the NPC field mask and not earlier:
    everything before it (the BasicAttr region, the scene pair, and this
    lane's own faction splice) is another concern's, and an anchor that
    reached back into it would go red for changes that cannot move this
    field.  What it must cover exactly is the mask byte this function
    rewrites and every field that mask already turned on, because those are
    what the appended field lands after.
    """
    tail = (
        bytes(legacy.u8tag(NPC_FIELD_MASK_TAG, npc_mask))
        + bytes(legacy.u16tag(0x12, template_id))
    )
    if visual_preset:
        tail += bytes(legacy.wstr_tag(visual_preset))
    return tail


def npc_mask_for(visual_preset: str) -> int:
    """The NPC field mask the frozen composer builds for this monster."""
    return NPC_MASK_BIT_TEMPLATE | (
        NPC_MASK_BIT_VISUAL_PRESET if visual_preset else 0
    )


def link_viewer_to_npc_attr(
    legacy: Any,
    body: bytes,
    *,
    viewer_identity: int,
    monster_identity: int,
    template_id: int,
    visual_preset: str,
) -> bytes:
    """``body`` with the associated-actor id of ONE viewer spliced on.

    The body is refused unless it ends with exactly the tail the frozen
    composer builds, so a body whose layout moved comes back as a named
    refusal instead of bytes that would reach a client.
    """
    if isinstance(viewer_identity, bool) or not isinstance(viewer_identity, int):
        raise MobNameColourLinkError(REFUSE_VIEWER_IDENTITY_NOT_POSITIVE)
    if viewer_identity <= 0:
        raise MobNameColourLinkError(REFUSE_VIEWER_IDENTITY_NOT_POSITIVE)
    if viewer_identity > LINKED_IDENTITY_CEILING:
        raise MobNameColourLinkError(REFUSE_VIEWER_IDENTITY_OUT_OF_RANGE)
    # RE-195 result row 61(a): the selector wants an associated identity that
    # is nonzero and NOT the monster's own.  A body that links a monster to
    # itself is the one shape that is certainly wrong, so it is refused here
    # rather than sent and watched.
    if viewer_identity == monster_identity:
        raise MobNameColourLinkError(REFUSE_VIEWER_IS_THE_MONSTER)

    mask = npc_mask_for(visual_preset)
    if mask & NPC_MASK_BIT_LINKED_IDENTITY:
        raise MobNameColourLinkError(REFUSE_LINK_BIT_ALREADY_SET)
    tail = _npc_mask_tail(
        legacy,
        npc_mask=mask,
        template_id=template_id,
        visual_preset=visual_preset,
    )
    if not body.endswith(tail):
        raise MobNameColourLinkError(REFUSE_BODY_TAIL_DRIFT)
    widened = _npc_mask_tail(
        legacy,
        npc_mask=mask | NPC_MASK_BIT_LINKED_IDENTITY,
        template_id=template_id,
        visual_preset=visual_preset,
    )
    linked = bytes(legacy.qwordtag(LINKED_IDENTITY_TAG, viewer_identity))
    if len(linked) != LINKED_IDENTITY_WIRE_LEN + 1:
        # tag byte + eight value bytes; anything else means the legacy
        # encoder changed shape and this module must be re-derived.
        raise MobNameColourLinkError(REFUSE_BODY_TAIL_DRIFT)
    return body[: len(body) - len(tail)] + widened + linked


#: The one call site this module needs, named rather than described, for the
#: lane that owns it.  ``field_mobs.hostile_npc_attr`` grew the optional
#: ``viewer_identity`` keyword in the same round as this file; what is still
#: missing is the runtime binding of a SESSION to that keyword, which is
#: CORE-REQUEST-GM-061's ask and lives in the chief's file.
MOB_NAME_COLOUR_LINK_WIRING = (
    "runtime.py: the per-session census dispatch that calls "
    "field_mobs.hostile_actor_entry(...) must pass viewer_identity=<the "
    "identity of the session this frame is being composed FOR>. Composing "
    "one body for a scene and sending it to every session cannot carry this "
    "field, because the field IS the viewer. Nothing else changes: with the "
    "keyword absent the composer returns the same bytes it returns today."
)
