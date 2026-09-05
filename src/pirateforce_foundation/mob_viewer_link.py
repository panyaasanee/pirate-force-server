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
different classes.  Both shapes are therefore named here rather than left to
be inferred from an offset that two classes share.

(A draft of this file said splicing one shape into the other class was "the
mistake ``GT-218`` proved kills the client in one frame".  That sentence was
false twice and is struck rather than quietly deleted, because it would have
been quoted forward: ``RE-222-RESULT`` says at its own line 85 that there was
"no tag-width-order framing error", at :93 that the measured error was
"sending a sparse ActorAttr to an apply path with full-object replacement
semantics, not malformed framing", and at :148 "do not retry by tweaking tags
or length"; and the GT-218 run itself killed the CHARACTER, not the client
process -- the owner closed the window herself and re-logged fine.  What a
wrong shape here actually risks is a body the client reads as a different
field, which is bad enough to justify naming both shapes, and is not a crash
precedent.  pf-adversary D6, round ``404m21``.)

WHAT THIS MODULE DOES NOT DO.  It does not decide a COLOUR: the colour is the
client's, chosen by the selector span above from this field plus the relation
predicate.  It does not read a faction (faction-only remains banned,
``COO-DECISION 20260905_2348``) and it hardcodes no FontStyleID.  It sends
nothing: it takes a composed NPCAttr body and hands back a longer one, and
the day a caller exists, that caller is where a GT ticket points.

WHERE THE FIELD GOES IN THE BODY, AND WHY THAT IS READ RATHER THAN INFERRED.
The rows cited above carry an ``order`` column, and it answers this directly:
``+0x7C`` is order 21 and ``+0x98`` is order 22, so bit 0x08's field is
emitted immediately after the visual-preset wstring.  This module therefore
APPENDS, and the append position is a citation, not a guess.

DO NOT RESTATE THIS AS "ASCENDING OFFSET".  A draft of this file argued the
position from "bit order and object-offset order agree", which is true for
the two bits this composer already writes and FALSE two bits later: order 23
is ``+0xA8`` and order 24 is ``+0xA0``, descending.  The rule that holds is
ascending EMISSION ORDER as the codex records it -- the same shape
``field_mobs.hostile_npc_attr``'s own docstring states for the BasicAttr mask
("each tagged value spliced in at its own ascending-mask-bit position").
Anyone extending this to bit 0x10 must read the ``order`` column again rather
than continue a pattern.  (pf-adversary D5, round ``404m21``.)

WHAT IS STILL NOT PROVEN, so a caller knows what it is buying: no capture in
this project has yet shown a CLIENT accepting a body with this field on it.
The layout is IMAGE-proven from the client's own codec, which is the encoding
a server must satisfy; it is not an observation of this server's bytes being
accepted.  That confirmation is an attended run, and the letter carrying this
round asks for it.
"""
from __future__ import annotations

from typing import Any

#: LANE-B owns this module; there is nothing here a scenario flag could gate
#: that the refusals below do not gate harder, and this lane does not ship
#: work that needs a flag turned on.
production_allowed = True


class MobViewerLinkError(RuntimeError):
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
        raise MobViewerLinkError(REFUSE_VIEWER_IDENTITY_NOT_POSITIVE)
    if viewer_identity <= 0:
        raise MobViewerLinkError(REFUSE_VIEWER_IDENTITY_NOT_POSITIVE)
    if viewer_identity > LINKED_IDENTITY_CEILING:
        raise MobViewerLinkError(REFUSE_VIEWER_IDENTITY_OUT_OF_RANGE)
    # RE-195 result row 61(a): the selector wants an associated identity that
    # is nonzero and NOT the monster's own.  A body that links a monster to
    # itself is the one shape that is certainly wrong, so it is refused here
    # rather than sent and watched.
    if viewer_identity == monster_identity:
        raise MobViewerLinkError(REFUSE_VIEWER_IS_THE_MONSTER)

    mask = npc_mask_for(visual_preset)
    tail = _npc_mask_tail(
        legacy,
        npc_mask=mask,
        template_id=template_id,
        visual_preset=visual_preset,
    )
    widened = _npc_mask_tail(
        legacy,
        npc_mask=mask | NPC_MASK_BIT_LINKED_IDENTITY,
        template_id=template_id,
        visual_preset=visual_preset,
    )
    # THE ORDER OF THESE TWO CHECKS IS THE FIX, NOT DECORATION (pf-adversary
    # D4, round `404m21`).  The first draft tested `npc_mask_for(...) & 0x08`,
    # which is a value this module computes itself and which is 0x01 or 0x05
    # and never anything else -- a refusal that could not fire.  The case it
    # was named for is REAL and is this one: a caller that links the SAME
    # body twice, which is exactly the shape a per-session re-send takes when
    # it feeds its own output back in.  Such a body no longer ends with the
    # narrow tail, so without this check it came back as BODY_TAIL_DRIFT --
    # a refusal that sends the reader to look for a layout change in somebody
    # else's file instead of at their own second call.
    if widened in body:
        raise MobViewerLinkError(REFUSE_LINK_BIT_ALREADY_SET)
    if not body.endswith(tail):
        raise MobViewerLinkError(REFUSE_BODY_TAIL_DRIFT)
    linked = bytes(legacy.qwordtag(LINKED_IDENTITY_TAG, viewer_identity))
    if len(linked) != LINKED_IDENTITY_WIRE_LEN + 1:
        # tag byte + eight value bytes; anything else means the legacy
        # encoder changed shape and this module must be re-derived.
        raise MobViewerLinkError(REFUSE_BODY_TAIL_DRIFT)
    return body[: len(body) - len(tail)] + widened + linked


#: The one call site this module needs, named rather than described, for the
#: lane that owns it.  ``field_mobs.hostile_npc_attr`` grew the optional
#: ``viewer_identity`` keyword in the same round as this file; what is still
#: missing is the runtime binding of a SESSION to that keyword, which is
#: CORE-REQUEST-GM-061's ask and lives in the chief's file.
MOB_VIEWER_LINK_WIRING = (
    "runtime.py: the per-session census dispatch that calls "
    "field_mobs.hostile_actor_entry(...) must pass viewer_identity=<the "
    "identity of the session this frame is being composed FOR>. Composing "
    "one body for a scene and sending it to every session cannot carry this "
    "field, because the field IS the viewer. Nothing else changes: with the "
    "keyword absent the composer returns the same bytes it returns today."
)
