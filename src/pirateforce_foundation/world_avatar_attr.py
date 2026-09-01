"""Name the AvatarAttr body this server already replays, from the corpus
table that names it, and check the running code against that table.

WHY THIS FILE EXISTS -- AND WHAT IT DELIBERATELY DOES NOT DO
============================================================

``notes_to_chief/20260902_0205_CHIEF-TO-LANE-A-avatarattr-and-questattr-
assigned.md`` (item 1) reports that the Codex corpus closed ``AvatarAttr``
(-> ``DBAttribute``, NOT ``BasicAttr``) across all 22 entries, and that this
repository still treats the body as one opaque blob in three places
(``actor_wire.py:56``, ``lifecycle.py:35``, ``remote_player_hypothesis.py:1222``).

Rule 14.13 (d) is explicit about what a lane may do with a corpus claim of
that shape: OPEN A CHECK-FIRST TICKET AGAINST THE RUNNING CODE.  Do not
order a fix.  ``COO-DECISION 20260902_0543`` re-issued that to this lane as
the next round's work.

So this module is a CHECK, not a wiring.  It can produce a modified body,
and NOTHING in this repository calls that; ``tests/test_world_avatar_attr.py``
enforces the "no production caller" property two ways so that wiring it
later is a visible, reviewed change.  Nothing here is on a live path, and a
player sees nothing different because of it.  That is the intended state for
a 14.13 (d) round; the client-observable half is ``GT-203``.

WHERE THE FIELD TABLE COMES FROM -- read this before changing a row
===================================================================

``FIELDS`` below is transcribed from ONE source:

    pf_bridge/notes_to_chief/reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv
    (rows with class == AvatarAttr, order 5..25)

That file carries ``order``, ``offset``, ``tag``, ``storage_width``,
``mask_bit``, ``structural_type``, ``structural_status``, ``scope_status``
and ``semantic_name`` per field.  The ``mask_bit`` column states outright
which mask bit carries which field, so nothing here has to infer it.

  ROUND qtxdpr, RECORDED SO IT IS NOT REPEATED: the first draft of this
  module did not open that file.  It inferred the bit for each name by
  assuming the wire order equals ascending, densely packed object offsets
  from +0x2C -- the exact inference the assignment letter's own nonclaim
  forbids ("the order on the wire is the corpus ``order`` column, not the
  offset order").  It happens to hold for orders 5..19 and BREAKS at 20:
  the string field is +0x64 while the NEXT field on the wire is +0x60, and
  the last three run +0x5F, +0x84, +0x88.  The inference put ``n_SKIN``
  (+0x84) on bit 20; the corpus says bit 19.  Bit 20 is
  ``equip_projection_slot_0x200000`` at +0x88.  A reader asking "what skin
  does this character have" would have been handed an equipment id -- and
  the wrong answer was labelled an assumption, which does not help when the
  right answer was sitting in the repository unread.  pf-adversary found it
  by opening the file.  G1: do not declare a source absent without looking.

WHAT THE RUNNING CODE DOES, AND WHAT THE CHECK COMPARES
=======================================================

``current/pf_login_game_server_v141.py:2224 extract_avatar_attr_wire_from_actor``
is frozen (chief's zone, not touched here).  It slices the embedded
AvatarAttr out of a captured CreateActorDataEx by WALKING IT IN FULL::

    base_flags = c.u8(0x0B)              # common-Attr flags byte
    if base_flags & 0x01: c.raw8(0x32)   # common-Attr identity, u64
    mask = c.u32(0x26)                   # AvatarAttr's OWN mask, u32
    for bit in range(12):
        if mask & (1 << bit): c.u32(0x14)
    bit 12 -> u8 0x0B   bit 13 -> u8 0x08   bit 14 -> u8 0x08
    bit 15 -> astr      bit 16 -> u8 0x0B   bit 17 -> u32 0x14
    bit 18 -> u8 0x0B   bit 19 -> u8 0x0B   bit 20 -> u32 0x14

``legacy_bridge.py:87`` tags the slice as attr id ``0x16A0`` inside every
``StartGameRes``, so this is a live, flag-free path: the body named here is
the body the player is wearing.

THE CHECK, and what can make it come back negative
--------------------------------------------------

1. ``check_frozen_walk_against_the_corpus()`` compares the frozen walker's
   tag-and-width sequence, slot by slot, against ``FIELDS`` in ``mask_bit``
   order.  A disagreement raises.  This is a real comparison between two
   sources -- the corpus is not derived from the walker, and the walker
   predates the corpus rows.
2. ``decode_avatar_attr`` walks a body strictly and refuses trailing bytes,
   which the frozen walker cannot notice because it returns a slice.
3. The bit-identity half, which the first draft could NOT test at all: the
   only real body in evidence ships ``mask = 0xFFFFFFFF``, and with every
   bit set the byte stream is invariant under any permutation of the
   bit->slot assignment.  So the tests also build SPARSE-mask bodies from
   ``FIELDS`` and require the frozen walker to slice each one to exactly the
   bytes this module encoded.

   HOW FAR THAT REACHES, MEASURED AND NOT ROUNDED UP.  A single-bit body
   pins the SHAPE of that bit -- its tag and width -- and nothing more.  Two
   bits of the same shape produce identical bytes, so no test over the wire
   can tell them apart.  The shape classes are::

       (0x14, 4) : bits 0..11, 17, 20    (fourteen u32 slots)
       (0x0B, 1) : bits 12, 16, 18, 19
       (0x08, 1) : bits 13, 14
       (0x44, *) : bit 15

   pf-adversary demonstrated the consequence by REVERSING the frozen
   walker's twelve u32 branches: the suite stayed green, because that loop
   consumes one u32 per set bit no matter which bit it is.  So which of the
   fourteen u32 slots is ``n_HRID`` and which is ``n_SLOT_LHAND`` rests
   ENTIRELY on the corpus ``mask_bit`` column, an IMAGE fact, and on no
   measurement this repository can make.  What the sparse bodies do catch is
   a cross-shape error -- which is the class the first draft's ``n_SKIN``
   defect fell into (u8 bit 19 read as the u32 at bit 20), and is why a
   swap of those two goes red now.

WHAT IS STILL NOT SETTLED -- read before quoting any of this
============================================================

1. SCOPE.  Every AvatarAttr row in the corpus except order 22 carries
   ``scope_status = UNKNOWN``: the field layout is proven, but which
   concrete class consumes it is not (``PF_ATTR_UNRESOLVED_BUCKETS.tsv``:
   ``AvatarAttr / CONCRETE_CONSUMER_CLASS_UNKNOWN``).  The corpus ``source``
   for every row is ``IMAGE`` -- static analysis of the client binary, not
   an observed packet.
2. THE JOIN IS NOT MEASURED.  This module measures a WIRE fact (the tag and
   width sequence of one captured body) and reads an IMAGE fact (the corpus
   offsets and names).  Two layers agreeing is consistency, not proof that
   the object offset carries the name the corpus gives it.  [PROPOSED]
3. NOBODY HAS SEEN A SCREEN CHANGE.  No evidence here shows that writing
   ``n_GENDER`` makes the client draw a different model.  That is ``GT-203``
   and only ``GT-203``.
4. MASK BITS 21..31.  The real capture ships ``mask = 0xFFFFFFFF`` while the
   corpus's highest ``mask_bit`` is ``0x00100000`` (bit 20) and the frozen
   walker stops there.  So the top 11 bits are not presence bits in any
   sense this repository can observe.  A future body that DID carry a
   payload for bit 21 would be mis-sliced by the frozen walker, and by this
   module, in the same way.  ``decode_avatar_attr`` reports
   ``undefined_mask_bits`` so the condition is visible; it does not guess.
   The same capture ships ``base_flags = 0xFF`` with only bit 0 defined, so
   ``undefined_flag_bits`` reports that too -- the first draft reported one
   of these two identical situations and not the other.
5. THE ONLY BODY IN EVIDENCE IS THE PRESET.  The live path stores the
   CLIENT's create submit (``lifecycle.py:53``), whose bit-15 colour-map
   string may be non-empty and whose mask need not be all ones.  This
   module has never seen such a body.  ``GT-203`` is what produces one.
"""

import struct
from dataclasses import dataclass

# The attr id ``legacy_bridge.py:87`` ships this body under, inside
# StartGameRes.  Named here so a test can assert the two agree.
AVATAR_ATTR_ID = 0x16A0

# Tags, spelled out rather than inlined, so a drift in one place is one edit.
TAG_U8 = 0x0B
TAG_S8 = 0x08
TAG_U32 = 0x14
TAG_MASK_U32 = 0x26
TAG_IDENTITY_U64 = 0x32
TAG_ASTR = 0x44

COMMON_FLAGS_IDENTITY_BIT = 0x01

# The mask offset, from the corpus's order-4 row.
MASK_OFFSET = 0x28

# The highest mask bit the corpus defines and the frozen walker walks.
LAST_DEFINED_MASK_BIT = 20

GENDER_FEMALE = 1


@dataclass(frozen=True)
class Field:
    """One AvatarAttr field, transcribed verbatim from the corpus row.

    ``width`` is the payload width in bytes after the tag byte; ``None``
    means variable (the corpus's ``5+N_bytes`` byte-string row).
    """

    order: int
    bit: int
    offset: int
    tag: int
    width: int | None
    structural_type: str
    name: str


# Transcribed from PF_ATTR_FIELD_SEMANTICS.tsv, class == AvatarAttr, orders
# 5..25, in mask_bit order.  ``bit`` is log2 of that row's ``mask_bit``.
# Names are the corpus's ``semantic_name`` VERBATIM -- an invented synonym
# here would make a later cross-check against the corpus come back empty and
# read as "never decoded".  The presentation-flags row's name is elided to
# its prefix because the corpus spells its whole bit legend into the name;
# ``PRESENTATION_FLAGS_FULL_NAME`` keeps the full string for grepping.
PRESENTATION_FLAGS_FULL_NAME = (
    "avatar_presentation_behavior_flags__0x1_pair_map_application_gate__"
    "0x4_0x8_effect_suppress__0x10_scale_1_3"
)

FIELDS: tuple[Field, ...] = (
    Field(5, 0, 0x2C, TAG_U32, 4, "uint32", "n_DRESS_HAT"),
    Field(6, 1, 0x30, TAG_U32, 4, "uint32", "n_HRID"),
    Field(7, 2, 0x34, TAG_U32, 4, "uint32", "n_HDID"),
    Field(8, 3, 0x38, TAG_U32, 4, "uint32", "n_FCID"),
    Field(9, 4, 0x3C, TAG_U32, 4, "uint32", "n_ETID"),
    Field(10, 5, 0x40, TAG_U32, 4, "uint32", "n_DRESS_CHEST"),
    Field(11, 6, 0x44, TAG_U32, 4, "uint32", "n_DRESS_LEGGINGS"),
    Field(12, 7, 0x48, TAG_U32, 4, "uint32", "equip_projection_slot_0x000800"),
    Field(13, 8, 0x4C, TAG_U32, 4, "uint32", "equip_projection_slot_0x001000"),
    Field(14, 9, 0x50, TAG_U32, 4, "uint32", "equip_projection_slot_0x002000"),
    Field(15, 10, 0x54, TAG_U32, 4, "uint32", "n_SLOT_RHAND"),
    Field(16, 11, 0x58, TAG_U32, 4, "uint32", "n_SLOT_LHAND"),
    Field(17, 12, 0x5C, TAG_U8, 1, "uint8_enum", "n_GENDER_1_female_other_male"),
    Field(18, 13, 0x5D, TAG_S8, 1, "int8", "s_BODYRATIO_component_0_height"),
    Field(19, 14, 0x5E, TAG_S8, 1, "int8", "s_BODYRATIO_component_1_width"),
    Field(
        20,
        15,
        0x64,
        TAG_ASTR,
        None,
        "byte_string",
        "item_definition_key_to_packed_color_low24_pair_map_text",
    ),
    Field(21, 16, 0x60, TAG_U8, 1, "uint8_flags", PRESENTATION_FLAGS_FULL_NAME),
    Field(22, 17, 0x80, TAG_U32, 4, "uint32", "opaque_u32_delta_member"),
    Field(23, 18, 0x5F, TAG_U8, 1, "uint8_enum", "avatar_render_record_lookup_key"),
    Field(24, 19, 0x84, TAG_U8, 1, "uint8", "n_SKIN"),
    Field(25, 20, 0x88, TAG_U32, 4, "uint32", "equip_projection_slot_0x200000"),
)

# The frozen walker's branch list, transcribed from
# ``extract_avatar_attr_wire_from_actor``.  Kept SEPARATE from ``FIELDS`` on
# purpose: the check below compares the two, and a single table would make
# that comparison vacuous.
FROZEN_WALK: tuple[tuple[int, int | None], ...] = (
    tuple((TAG_U32, 4) for _ in range(12))
    + (
        (TAG_U8, 1),
        (TAG_S8, 1),
        (TAG_S8, 1),
        (TAG_ASTR, None),
        (TAG_U8, 1),
        (TAG_U32, 4),
        (TAG_U8, 1),
        (TAG_U8, 1),
        (TAG_U32, 4),
    )
)

# The corpus's structural_type for these two rows is ``int8``, status
# PROVEN_EXACT -- so the signedness IS settled and this module reads them
# signed.  (The first draft called it unsettled because the wire tags 0x08
# and 0x0B are both read unsigned by the frozen Cursor.  That is true of the
# WIRE and says nothing about the field; the corpus answers it.)
SIGNED_TYPES = frozenset({"int8"})

_BY_BIT = {field.bit: field for field in FIELDS}
_BY_NAME = {field.name: field for field in FIELDS}


class AvatarAttrDrift(ValueError):
    """The body does not walk the way the running code assumes it does."""


def field_for_bit(bit: int) -> Field:
    field = _BY_BIT.get(bit)
    if field is None:
        raise AvatarAttrDrift(f"bit {bit} has no corpus row")
    return field


def field_for_name(name: str) -> Field:
    field = _BY_NAME.get(name)
    if field is None:
        raise KeyError(f"{name} is not a corpus AvatarAttr field name")
    return field


def check_frozen_walk_against_the_corpus() -> tuple[Field, ...]:
    """The 14.13 (d) check.  Returns ``FIELDS`` in wire order, or raises.

    Compares two sources that were produced independently of each other: the
    frozen walker's branch list (written long before these corpus rows) and
    the corpus's ``tag`` / ``storage_width`` columns, matched up by the
    corpus's own ``mask_bit``.
    """
    if len(FIELDS) != len(FROZEN_WALK):
        raise AvatarAttrDrift(
            f"the frozen walk has {len(FROZEN_WALK)} slots, the corpus has "
            f"{len(FIELDS)} fields"
        )
    ordered = tuple(sorted(FIELDS, key=lambda field: field.bit))
    if [field.bit for field in ordered] != list(range(len(FIELDS))):
        raise AvatarAttrDrift("the corpus mask bits are not 0..N without gaps")
    if [field.order for field in ordered] != [
        field.order for field in sorted(FIELDS, key=lambda f: f.order)
    ]:
        raise AvatarAttrDrift(
            "the corpus order column and its mask_bit column disagree about "
            "the sequence on the wire"
        )
    for field, (tag, width) in zip(ordered, FROZEN_WALK):
        if field.tag != tag or field.width != width:
            raise AvatarAttrDrift(
                f"bit {field.bit} ({field.name}): the frozen walk reads tag "
                f"0x{tag:02X} width {width}, the corpus says tag "
                f"0x{field.tag:02X} width {field.width}"
            )
    if len({field.offset for field in FIELDS}) != len(FIELDS):
        raise AvatarAttrDrift("two corpus rows claim the same object offset")
    if MASK_OFFSET + 4 != FIELDS[0].offset:
        raise AvatarAttrDrift("the mask does not sit immediately before +0x2C")
    if ordered[-1].bit != LAST_DEFINED_MASK_BIT:
        raise AvatarAttrDrift("LAST_DEFINED_MASK_BIT does not match the corpus")
    return ordered


def wire_order_matches_offset_order() -> bool:
    """False, and it matters.

    The assignment letter's nonclaim says the wire order is the corpus
    ``order`` column and not the offset order.  This returns the answer from
    the table rather than leaving it as prose, because the first draft of
    this module assumed the opposite and put a field on the wrong bit.
    """
    offsets = [field.offset for field in sorted(FIELDS, key=lambda f: f.bit)]
    return offsets == sorted(offsets)


@dataclass(frozen=True)
class AvatarAttrBody:
    """Every byte of one AvatarAttr body, named, with nothing dropped.

    ``values`` is keyed by mask bit.  A body re-encoded from this dataclass
    is byte-identical to the body it was decoded from.
    """

    base_flags: int
    identity: bytes | None
    mask: int
    values: dict[int, int | bytes]
    undefined_mask_bits: tuple[int, ...]
    undefined_flag_bits: tuple[int, ...]

    def has(self, bit: int) -> bool:
        return bit in self.values

    def raw(self, name: str) -> int | bytes | None:
        """The stored value for a corpus field name, unsigned/verbatim."""
        return self.values.get(field_for_name(name).bit)

    def named(self, name: str) -> int | None:
        """Read a corpus-named numeric field, signed where the corpus says
        ``int8``.  ``None`` when this body omits the field."""
        field = field_for_name(name)
        value = self.values.get(field.bit)
        if value is None:
            return None
        if isinstance(value, bytes):
            raise AvatarAttrDrift(f"{name} is a string slot, not a number")
        if field.structural_type in SIGNED_TYPES and value > 0x7F:
            return value - 0x100
        return value

    @property
    def gender(self) -> int | None:
        return self.named("n_GENDER_1_female_other_male")

    @property
    def body_ratio(self) -> tuple[int | None, int | None]:
        """(height, width), signed -- the corpus names the components."""
        return (
            self.named("s_BODYRATIO_component_0_height"),
            self.named("s_BODYRATIO_component_1_width"),
        )

    @property
    def skin(self) -> int | None:
        """``n_SKIN``: corpus order 24, +0x84, u8, mask bit 19."""
        return self.named("n_SKIN")

    @property
    def colour_map_text(self) -> bytes | None:
        value = self.values.get(
            field_for_name(
                "item_definition_key_to_packed_color_low24_pair_map_text"
            ).bit
        )
        if value is None:
            return None
        assert isinstance(value, bytes)
        return value


def decode_avatar_attr(body: bytes) -> AvatarAttrBody:
    """Walk one AvatarAttr body strictly, refusing anything it cannot name.

    This walk does not call the frozen walker, and its slot table comes from
    the corpus rather than from that function -- but the two agreeing is
    still not "two independent opinions", because ``FROZEN_WALK`` above is a
    transcription.  What the transcription cannot fake is the walk: every
    step asserts a tag byte, a short read is refused, and TRAILING bytes are
    refused, which the frozen walker cannot notice because it returns a
    slice.  The sparse-mask tests are what pin the bit identities.
    """
    if len(body) < 2:
        raise AvatarAttrDrift("body is too short to hold the common flags")
    if body[0] != TAG_U8:
        raise AvatarAttrDrift(
            f"common flags tag drift: got 0x{body[0]:02X}, want 0x{TAG_U8:02X}"
        )
    base_flags = body[1]
    cursor = 2

    identity: bytes | None = None
    if base_flags & COMMON_FLAGS_IDENTITY_BIT:
        if len(body) < cursor + 9:
            raise AvatarAttrDrift("truncated common-Attr identity")
        if body[cursor] != TAG_IDENTITY_U64:
            raise AvatarAttrDrift("common-Attr identity tag drift")
        identity = bytes(body[cursor + 1:cursor + 9])
        cursor += 9

    if len(body) < cursor + 5:
        raise AvatarAttrDrift("truncated AvatarAttr mask")
    if body[cursor] != TAG_MASK_U32:
        raise AvatarAttrDrift(
            f"mask tag drift: got 0x{body[cursor]:02X}, want 0x{TAG_MASK_U32:02X}"
        )
    mask = struct.unpack_from("<I", body, cursor + 1)[0]
    cursor += 5

    values: dict[int, int | bytes] = {}
    for field in sorted(FIELDS, key=lambda f: f.bit):
        if not mask & (1 << field.bit):
            continue
        if cursor >= len(body):
            raise AvatarAttrDrift(f"truncated before bit {field.bit}")
        if body[cursor] != field.tag:
            raise AvatarAttrDrift(
                f"bit {field.bit} ({field.name}) tag drift: got "
                f"0x{body[cursor]:02X}, want 0x{field.tag:02X}"
            )
        cursor += 1
        if field.width is None:
            if len(body) < cursor + 4:
                raise AvatarAttrDrift(f"truncated string length at bit {field.bit}")
            length = struct.unpack_from("<I", body, cursor)[0]
            cursor += 4
            if len(body) < cursor + length:
                raise AvatarAttrDrift(f"truncated string body at bit {field.bit}")
            values[field.bit] = bytes(body[cursor:cursor + length])
            cursor += length
            continue
        if len(body) < cursor + field.width:
            raise AvatarAttrDrift(f"truncated value at bit {field.bit}")
        if field.width == 1:
            values[field.bit] = body[cursor]
        elif field.width == 4:
            values[field.bit] = struct.unpack_from("<I", body, cursor)[0]
        else:
            raise AvatarAttrDrift(
                f"bit {field.bit} has width {field.width}, which this codec "
                f"has no reader for"
            )
        cursor += field.width

    if cursor != len(body):
        raise AvatarAttrDrift(
            f"{len(body) - cursor} trailing byte(s) the walk cannot name"
        )

    return AvatarAttrBody(
        base_flags=base_flags,
        identity=identity,
        mask=mask,
        values=values,
        undefined_mask_bits=tuple(
            bit
            for bit in range(LAST_DEFINED_MASK_BIT + 1, 32)
            if mask & (1 << bit)
        ),
        undefined_flag_bits=tuple(
            bit
            for bit in range(1, 8)
            if base_flags & (1 << bit)
        ),
    )


def encode_avatar_attr(decoded: AvatarAttrBody) -> bytes:
    """Rebuild the body from names.  Must reproduce the original exactly."""
    out = bytearray()
    out.append(TAG_U8)
    out.append(decoded.base_flags & 0xFF)
    if decoded.base_flags & COMMON_FLAGS_IDENTITY_BIT:
        if decoded.identity is None or len(decoded.identity) != 8:
            raise AvatarAttrDrift("the flags claim an identity this body lacks")
        out.append(TAG_IDENTITY_U64)
        out.extend(decoded.identity)
    elif decoded.identity is not None:
        raise AvatarAttrDrift("an identity is present with the bit clear")
    out.append(TAG_MASK_U32)
    out.extend(struct.pack("<I", decoded.mask & 0xFFFFFFFF))
    for field in sorted(FIELDS, key=lambda f: f.bit):
        if not decoded.mask & (1 << field.bit):
            if field.bit in decoded.values:
                raise AvatarAttrDrift(
                    f"bit {field.bit} has a value with its mask bit clear"
                )
            continue
        if field.bit not in decoded.values:
            raise AvatarAttrDrift(f"bit {field.bit} is set but carries no value")
        value = decoded.values[field.bit]
        out.append(field.tag)
        if field.width is None:
            if not isinstance(value, bytes):
                raise AvatarAttrDrift(f"bit {field.bit} must hold bytes")
            out.extend(struct.pack("<I", len(value)))
            out.extend(value)
            continue
        if not isinstance(value, int):
            raise AvatarAttrDrift(f"bit {field.bit} must hold an integer")
        if field.width == 1:
            if not 0 <= value <= 0xFF:
                raise AvatarAttrDrift(f"bit {field.bit} does not fit one byte")
            out.append(value)
        elif field.width == 4:
            if not 0 <= value <= 0xFFFFFFFF:
                raise AvatarAttrDrift(f"bit {field.bit} does not fit four bytes")
            out.extend(struct.pack("<I", value))
        else:
            raise AvatarAttrDrift(
                f"bit {field.bit} has width {field.width}, which this codec "
                f"has no writer for"
            )
    return bytes(out)


def build_body(
    mask_bits: tuple[int, ...],
    values: dict[int, int | bytes],
    *,
    base_flags: int = COMMON_FLAGS_IDENTITY_BIT,
    identity: bytes = b"\x00" * 8,
) -> bytes:
    """Compose a body carrying exactly ``mask_bits``.

    This exists so the tests can build SPARSE-mask bodies -- the only input
    that can tell one bit->field assignment from another, since the single
    real capture sets every bit and is therefore invariant under any
    permutation of them.  It is a test instrument, not a wiring.
    """
    mask = 0
    for bit in mask_bits:
        field_for_bit(bit)
        mask |= 1 << bit
    return encode_avatar_attr(
        AvatarAttrBody(
            base_flags=base_flags,
            identity=identity if base_flags & COMMON_FLAGS_IDENTITY_BIT else None,
            mask=mask,
            values={bit: values[bit] for bit in mask_bits},
            undefined_mask_bits=(),
            undefined_flag_bits=(),
        )
    )


def describe_avatar_body(body: bytes) -> str:
    """One console-safe ASCII line naming what a stored avatar body holds.

    ``GT-203`` has an attended tester create a character in the real client
    and then read this line off her own session database, so the screen she
    chose from and the bytes the server kept can be compared without any
    change to what the server sends.  The bridge console is cp874, so this
    stays inside plain ASCII on purpose.
    """
    decoded = decode_avatar_attr(body)
    parts = [
        f"AVATAR_DECODE len={len(body)}",
        f"mask=0x{decoded.mask:08X}",
        f"undefined_mask_bits={len(decoded.undefined_mask_bits)}",
        f"undefined_flag_bits={len(decoded.undefined_flag_bits)}",
    ]
    for field in sorted(FIELDS, key=lambda f: f.bit):
        if field.width is None:
            text = decoded.colour_map_text
            parts.append(
                f"{field.name}="
                + ("absent" if text is None else f"len{len(text)}")
            )
            continue
        value = decoded.named(field.name)
        if value is None:
            parts.append(f"{field.name}=absent")
        elif field.width == 4:
            # Four-byte ids read as hex, because that is how the corpus and
            # the game data tables spell them.
            parts.append(f"{field.name}=0x{value:08X}")
        else:
            # One-byte fields read as decimal, signed where the corpus says
            # int8 -- a tester comparing against a creation screen wants 30
            # and -7, not 0x1E and 0xF9.
            parts.append(f"{field.name}={value}")
    return " ".join(parts)


def with_named_fields(body: bytes, **changes: int) -> bytes:
    """Return the body with named fields replaced and every other byte kept.

    NOT CALLED FROM ANYWHERE IN THIS REPOSITORY, ON PURPOSE.  Rule 14.13 (d)
    says a corpus claim gets a check first, not a fix, and no evidence in
    this repository shows the client redraws a model when these bytes change
    -- that is ``GT-203``.  ``tests/test_world_avatar_attr.py`` asserts that
    no module outside this file mentions it, by AST walk AND by plain text
    scan, across the package and the frozen server and the tool directories.
    """
    decoded = decode_avatar_attr(body)
    values = dict(decoded.values)
    for name, value in changes.items():
        field = field_for_name(name)
        if field.bit not in values:
            raise AvatarAttrDrift(
                f"{name} is absent from this body; setting it would have to "
                f"move the mask, and no evidence says the client accepts that"
            )
        if field.width == 1 and field.structural_type in SIGNED_TYPES:
            value = value & 0xFF
        values[field.bit] = value
    return encode_avatar_attr(
        AvatarAttrBody(
            base_flags=decoded.base_flags,
            identity=decoded.identity,
            mask=decoded.mask,
            values=values,
            undefined_mask_bits=decoded.undefined_mask_bits,
            undefined_flag_bits=decoded.undefined_flag_bits,
        )
    )
