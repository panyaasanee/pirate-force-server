"""(b'') REDEFINED: the set a 0x309A frame must carry is THE SET PRODUCTION
LOGIN ITSELF SETS BITS FOR -- derived from the login composer, never typed.

ORDERED BY `COO-DECISION 2026-09-04T05:45+07:00`
(`pf_bridge/notes_to_chief/20260904_0545_COO-DECISION-lane-gm-b-double-prime-
is-redefined-as-the-login-mask-set-and-the-speed-gt-is-the-experiment-that-
answers-q3.md`), answering this lane's own alarm `20260904_0505`.  Item 1 of
that letter WITHDRAWS the previous wording (`COO-DECISION 0215` item 1, "every
`known=False` row must carry a byte") and the COO's own sentence in `0345`
("there is no safe value on a half block").  What withdrew them was a
measurement, not an opinion:

    (character name "Anne", 4 chars -- the block carries the name inline, so
    the BYTE COUNT moves with it while the MASK does not: "Probe" gives
    84/89, "Bob" 80/85.  pf-adversary round `4fxkam` D5: the first draft of
    this docstring quoted 82/87 without saying which name produced them.)

    player_wire.make_actor_attr_with_name_and_class(...)   -> 82 bytes
    attr_wire.encode_block(..., {1,2,3,4,7,9,10,13,24})    -> 82 bytes
    IDENTICAL: True   basic_mask 0x034F   actor_mask 0x00000801

    player_wire.make_actor_attr_with_name_class_and_faction(...) -> 87 bytes
    attr_wire.encode_block(..., {..., 11})                       -> 87 bytes
    IDENTICAL: True   basic_mask 0x074F   actor_mask 0x00000801

The server this house ships sends a NINE-row block (ten with the faction
branch `runtime.py` recomposes) to a real client at every single login, and
the client survives it every day.  So "a mask bit that is not set is a zero
on the client" (`RE-222` Q0, SHA-pinned, and the mechanism `GT-218` measured)
cannot mean that a block short of all 55 rows kills a client -- the shipped
login block IS short of all 55 rows.  The 55-row wall `COO-DECISION 0215`
asked for was a gate whose condition no source in this repository could ever
meet: `live_login_bytes` has a byte source for exactly 2 of the 28 unnamed
rows (x=7 and x=10, both of which login sends), so it refused forever.  A gate
whose condition cannot be met is not a gate, it is a shelf -- this module's
own `attr_wire.py` said that when it retired the previous (b).

WHAT THIS MODULE DOES *NOT* CLAIM.  It does not claim a login-shaped frame is
SAFE to apply to an already-created actor.  `GT-218` killed a client with a
one-row frame and nobody in this house has separated "an unset bit is zero" as
a property of the FRAME from the same thing as a property of ACTOR CREATION.
`COO-DECISION 0545` item 3 answers that question with a measurement on the
owner's screen (the existing `/speed` (b'') game test, one frame, STOP-on-HP-0,
cash/HP-max/MP/HP-bar unchanged), not with an RE ticket and not with this
module.  Until that test is graded, every door downstream of here stays shut
by its own gate (`speed_wire`'s wall, LANE-B's `MOB_HIT_FRAME_CONFIRMED=None`).
This module only changes WHICH SET is called complete.

WHY DERIVED AND NOT TYPED.  `COO-DECISION 0545` item 2: "no hand-typed list,
no constant 10 or 11".  A literal `{1,2,3,4,7,9,10,11,13,24}` here would be a
copy of a measurement, and a copy goes stale in silence on the day the login
composer gains a field -- which is exactly the shape of the drift this house
has been paying for all week.  So the set is read back OUT OF THE BYTES the
production composer produces, on every call, by walking the block the way
`attr_wire.encode_block` writes it.  A test cannot pin the answer either: it
pins that the derivation AGREES with the production path (see
`tests/test_gm_login_mask.py`), so the day `player_wire` changes its mask, the
derived set changes with it and the IDENTICAL test goes red rather than the
wall quietly admitting a shape nobody has ever shipped.

WHAT IS STILL MISSING, AND WHO OWES IT.  `COO-DECISION 0545` item 2 says the
unit is "the mask THIS CONNECTION's login block set" -- per connection, not
per repository.  Nothing records that today: `runtime.py` composes the block
and drops the mask on the floor.  This round pins the mask from the production
PATH instead (both branches), and opens `CORE-REQUEST-GM-053` asking chief to
record the composed mask on the session at login, from the one caller that
composes it.  When that lands, `login_masks_for_connection` below stops
falling back to the production shapes and reads the connection's own.  Until
then this module admits either shape the production composer can produce and
says so out loud -- it never invents a third.

X=30 CAN NEVER RIDE THIS SET (`COO-DECISION 0545` item 5).  Login does not set
that bit, so it is not in the derived set today.  If a future login composer
ever sets it, `login_field_x` RAISES rather than returning a set with x=30 in
it: "if the login mask ever contains x=30, raise, do not send" is the COO's
own wording, and the fail-closed half of it has to live where the set is born,
not in a caller that might forget to ask.
"""

from __future__ import annotations

import struct

from . import attr_wire


class LoginMaskError(attr_wire.AttrWireError):
    """A login block could not be parsed, or the derived set is unsendable.

    SUBCLASSES `AttrWireError` ON PURPOSE.  Every door in this lane already
    refuses by catching `AttrWireError` (`speed_wire`'s wall, the seeding
    path, `chat_command_action`'s compose-refused branch).  A refusal from
    this module is the same KIND of event -- "no frame is built" -- and a
    fresh exception hierarchy would have silently fallen through those
    handlers into whatever catches `Exception`, turning a named refusal into
    an unnamed one.
    """


#: Name of the read point `CORE-REQUEST-GM-053` asks chief to add: the
#: BasicAttr/ActorAttr masks the production login block actually composed for
#: THIS connection.  Spelled once, here, so a test can pin the name this lane
#: waits on without importing a module that does not exist -- same posture as
#: `attr_wire.LIVE_VALUE_READ_POINT` / `attr_wire.LOGIN_BYTES_READ_POINT`.
LOGIN_MASK_READ_POINT = "current_login_attr_masks"

#: The identity/section tag bytes `attr_wire.encode_block` writes, named here
#: so the parser below reads by name instead of by magic number.  These are
#: not new constants: each one is the tag `encode_block` already passes to the
#: legacy helper on the line that writes that section.
_IDENTITY_TAG = 0x0B
_QWORD_TAG = 0x32
_BASIC_MASK_TAG = 0x12
_ACTOR_GROUP_TAG = 0x05

#: Byte length of one tagged field, by `FIELDS` kind.  Derived from
#: `attr_wire.encode_field`'s own branches (tag byte + payload), not from a
#: separate reading of the wire format; `wstr`/`blob` are absent on purpose --
#: they carry a 4-byte length prefix and are measured from the wire.
_FIXED_KIND_LENGTHS = {
    "u8": 1 + 1,
    "u16": 1 + 2,
    "u32": 1 + 4,
    "i32": 1 + 4,
    "f32": 1 + 4,
    "u64": 1 + 8,
}
_LENGTH_PREFIXED_KINDS = frozenset({"wstr", "blob"})


def _field_length(block: bytes, offset: int, field: tuple) -> int:
    """How many bytes the field starting at `offset` occupies."""
    kind = field[5]
    fixed = _FIXED_KIND_LENGTHS.get(kind)
    if fixed is not None:
        return fixed
    if kind in _LENGTH_PREFIXED_KINDS:
        if offset + 5 > len(block):
            raise LoginMaskError(
                f"truncated {kind} length prefix for x={field[0]} at offset {offset}"
            )
        (payload,) = struct.unpack_from("<I", block, offset + 1)
        return 1 + 4 + payload
    raise LoginMaskError(  # pragma: no cover - FIELDS-shape guard
        f"unknown field kind {kind!r} for x={field[0]}"
    )


def _basic_fields_by_bit() -> dict:
    """Bit -> the ONE BasicAttr row bound to it, or raise.

    The actor side deliberately maps a bit to a LIST (x39/x40 and x41/x42
    share bits).  The basic side has no such pair today, and the walker in
    `parse_block_masks` depends on that: it advances the offset by ONE
    field's width per set bit, so a second row sharing a bit would desync
    every offset after it -- including a wstr length prefix, then read from
    the middle of the previous field.  pf-adversary round `4fxkam` (S1) found
    the asymmetry: the guard was on the side the parser does not walk.  It is
    here now, fail-closed, rather than left as "true today".
    """
    by_bit: dict = {}
    for field in attr_wire.FIELDS:
        if field[1] != "basic":
            continue
        if field[2] in by_bit:
            raise LoginMaskError(
                f"BasicAttr bit 0x{field[2]:04X} is bound to more than one row "
                f"(x={by_bit[field[2]][0]} and x={field[0]}): this parser walks "
                "one field per set bit and cannot size a shared basic bit"
            )
        by_bit[field[2]] = field
    return by_bit


def _actor_x_by_bit() -> dict:
    """Bit -> every `x` that rides it.

    A bit maps to a LIST, not to one row: x39/x40 share ActorAttr bit 26 and
    x41/x42 share bit 27 (`attr_wire.encode_block` enforces "both or neither"
    for exactly that reason).  A dict keyed by bit with a single row as its
    value would silently drop half of each pair, and the dropped half is one
    the frame really does carry.
    """
    by_bit: dict = {}
    for field in attr_wire.FIELDS:
        if field[1] == "actor":
            by_bit.setdefault(field[2], []).append(field[0])
    return by_bit


def parse_block_masks(legacy, block: bytes) -> tuple[int, int]:
    """Read `(basic_mask, actor_mask)` back out of a composed DBAttribute body.

    Walks the block in exactly the order `attr_wire.encode_block` writes it:
    identity flag, identity qword, BasicAttr mask, the BasicAttr fields in
    ascending bit order, then the ActorAttr mask.  It stops there on purpose:
    the ActorAttr mask is the last thing this function needs, so the paired
    bits (x39/x40, x41/x42) and the unbound bit 31 never have to be walked
    past -- they sit AFTER the qword this function is reading.

    FAIL-CLOSED AT EVERY STEP.  A tag that is not the one `encode_block`
    writes there, a BasicAttr bit that no `FIELDS` row is bound to, a
    truncated field: each raises `LoginMaskError` rather than returning a
    mask assembled from a block this parser did not actually understand.  A
    mask read out of a misparsed block is worse than no mask -- it is a wrong
    number wearing a measurement's clothes, and this lane has paid for one of
    those already this week.
    """
    identity_prefix = legacy.u8tag(_IDENTITY_TAG, attr_wire.DB_ATTRIBUTE_IDENTITY_BIT)
    if not block.startswith(identity_prefix):
        raise LoginMaskError(
            "not a DBAttribute body: it does not start with "
            f"u8tag(0x{_IDENTITY_TAG:02X}, {attr_wire.DB_ATTRIBUTE_IDENTITY_BIT})"
        )
    offset = len(identity_prefix)

    if offset >= len(block) or block[offset] != _QWORD_TAG:
        raise LoginMaskError(f"expected identity qword tag at offset {offset}")
    offset += 1 + 8

    if offset + 3 > len(block) or block[offset] != _BASIC_MASK_TAG:
        raise LoginMaskError(f"expected BasicAttr mask tag at offset {offset}")
    (basic_mask,) = struct.unpack_from("<H", block, offset + 1)
    offset += 3

    basic_by_bit = _basic_fields_by_bit()
    for bit in sorted(basic_by_bit):
        if not basic_mask & bit:
            continue
        offset += _field_length(block, offset, basic_by_bit[bit])
    unbound = basic_mask & ~sum(basic_by_bit)
    if unbound:
        raise LoginMaskError(
            f"BasicAttr mask 0x{basic_mask:04X} sets bit(s) 0x{unbound:04X} that "
            "no FIELDS row is bound to -- this parser cannot walk past a field "
            "it cannot size"
        )

    if offset + 9 > len(block) or block[offset] != _QWORD_TAG:
        raise LoginMaskError(f"expected ActorAttr mask tag at offset {offset}")
    (actor_mask,) = struct.unpack_from("<Q", block, offset + 1)
    offset += 9

    group_prefix = legacy.u8tag(_ACTOR_GROUP_TAG, attr_wire.ACTOR_ATTR_EXTRA_GROUP_VALUE)
    if not block[offset:offset + len(group_prefix)] == group_prefix:
        raise LoginMaskError(
            f"expected the ActorAttr group flag after the mask at offset {offset}"
        )
    return basic_mask, actor_mask


def field_x_for_masks(basic_mask: int, actor_mask: int) -> tuple[int, ...]:
    """Every `x` the two masks set a bit for, ascending.

    Raises if a set bit is bound to no row (the mask carries a field this
    table cannot name) or if any set bit belongs to `SENSITIVE_FIELDS` --
    `COO-DECISION 0545` item 5, "if the login mask ever holds x=30, raise, do
    not send".  That refusal lives here, at the birth of the set, rather than
    in a caller that could forget to ask.
    """
    basic_by_bit = _basic_fields_by_bit()
    actor_by_bit = _actor_x_by_bit()
    found: list[int] = []
    for bit, field in basic_by_bit.items():
        if basic_mask & bit:
            found.append(field[0])
    for bit, rows in actor_by_bit.items():
        if actor_mask & bit:
            found.extend(rows)
    unbound_basic = basic_mask & ~sum(basic_by_bit)
    unbound_actor = actor_mask & ~sum(actor_by_bit)
    if unbound_basic or unbound_actor:
        raise LoginMaskError(
            f"mask basic=0x{basic_mask:04X} actor=0x{actor_mask:016X} sets bits no "
            f"FIELDS row is bound to (basic=0x{unbound_basic:04X} "
            f"actor=0x{unbound_actor:016X})"
        )
    sensitive = sorted(set(found) & attr_wire.SENSITIVE_FIELDS)
    if sensitive:
        raise LoginMaskError(
            f"refusing a login-shaped set that carries SENSITIVE_FIELDS {sensitive}: "
            "COO-DECISION 20260904_0545 item 5 -- x=30 never leaves this server in "
            "a 0x309A frame, and a login composer that started setting its bit is a "
            "reason to raise, not a reason to send it"
        )
    return tuple(sorted(found))


#: The probe arguments the derivation composes with.  These are NOT the set
#: and they are not pinned values: they are throwaway inputs whose only job is
#: to make the production composer run so its MASK can be read back.  Every
#: one is a legal input the composer already accepts (`scene_seq=0` and an
#: admitted scene are what `make_actor_attr_with_name_class_and_faction`'s own
#: guard requires).  Changing any of them must not change the derived set --
#: `tests/test_gm_login_mask.py` proves that with a second, different probe.
_PROBE_IDENTITY = (0x11, 0x22)
_PROBE_NAME = "Probe"


def _probe_scene_id() -> int:
    """A scene the faction branch admits, read from the admission module's own
    proven floor rather than written as `1` here."""
    from .. import world_faction_admission  # noqa: PLC0415 - see module docstring

    return world_faction_admission.PROVEN_FACTION_SCENE_IDS[0]


def production_login_shapes(legacy) -> dict:
    """`{branch_name: (basic_mask, actor_mask)}` for every shape the
    production login composer can produce, measured by composing it.

    TWO BRANCHES, BOTH REAL.  `legacy_bridge.LegacyProjector.start_game`
    composes the plain branch; `runtime.py` recomposes with `basic_faction=1`
    on every login into a scene `world_faction_admission.admits`.  Which of
    the two a given connection got depends on ITS scene, which is exactly the
    fact `CORE-REQUEST-GM-053` asks chief to record.  Until it is recorded,
    both are shapes this server ships, so both are admitted -- and no third
    shape is.
    """
    from .. import player_wire  # noqa: PLC0415 - see module docstring
    from .. import world_faction_admission  # noqa: PLC0415 - see module docstring

    scene_id = _probe_scene_id()
    lo, hi = _PROBE_IDENTITY
    plain = player_wire.make_actor_attr_with_name_and_class(
        legacy, lo, hi, scene_id, 0, _PROBE_NAME,
    )
    factioned = player_wire.make_actor_attr_with_name_class_and_faction(
        legacy, lo, hi, scene_id, 0, _PROBE_NAME,
        world_faction_admission.PROVEN_BASIC_FACTION,
    )
    return {
        "plain": parse_block_masks(legacy, plain),
        "faction": parse_block_masks(legacy, factioned),
    }


def login_field_x(legacy) -> tuple[int, ...]:
    """THE (b'') SET: every `x` production login sets a bit for, ascending.

    The union of both branches, which is the faction branch (the plain branch
    is a strict subset of it) -- `COO-DECISION 0545` item 2 puts x=11 in the
    set by name.  Taking the UNION rather than naming a branch keeps this
    derived: if the plain branch ever gains a row the faction branch lacks,
    the set grows to hold it instead of this function having picked a winner.

    Derived on every call, deliberately.  A module-level constant computed at
    import would be a hand-typed list with extra steps: it would answer with
    the mask the composer had when the process started, and the whole point of
    `COO-DECISION 0545` item 2's last sentence ("your test must go red when
    production login changes its mask") is that a change must be visible, not
    cached.

    ~~The cost is two block compositions per frame~~ -- struck, MEASURED by
    pf-adversary round `4fxkam` (D5): `make_update_attr_frame` runs FOUR
    compositions (~142 us) and `build_named_field_update` EIGHT (~262 us),
    because each of them asks more than once.  Kept anyway, with the real
    number written down rather than hidden: `make_update_attr_frame` sits on
    LANE-B's per-hit path, not only on a per-login one, so 262 us is a cost a
    later round may have to buy down -- with a per-`legacy` memo that a
    CHANGE still invalidates, never with an import-time constant.
    """
    rows: set[int] = set()
    for basic_mask, actor_mask in production_login_shapes(legacy).values():
        rows.update(field_x_for_masks(basic_mask, actor_mask))
    return tuple(sorted(rows))


def admitted_masks(legacy) -> tuple[tuple[int, int], ...]:
    """Every `(basic_mask, actor_mask)` pair a 0x309A frame may carry today."""
    return tuple(sorted(production_login_shapes(legacy).values()))


def admitted_field_x_sets(legacy) -> tuple[tuple[int, ...], ...]:
    """The `x` set of each admitted shape, ascending by size.

    The KEY-level twin of `admitted_masks`, and it exists so the two checks
    cannot disagree.  A wall that demanded the union at the key level while
    admitting either mask would refuse the plain branch's own 9-row block --
    a shape this server composes at every login into a scene the faction gate
    does not admit -- and would have refused it with a message about missing
    rows, which is not what would have been wrong with it.
    """
    return tuple(
        sorted(
            (field_x_for_masks(basic, actor) for basic, actor in admitted_masks(legacy)),
            key=len,
        )
    )


def refuse_unless_login_shaped(legacy, basic_mask: int, actor_mask: int) -> None:
    """Raise unless the composed masks EQUAL a production login mask.

    `COO-DECISION 0545` item 2: "the 0x309A frame that leaves must have
    basic_mask/actor_mask EQUAL to that login mask, exactly".  Equality, not
    containment: a superset would put a bit on the wire that this connection's
    client has never been sent by the path that created its actor, and a
    subset is the partial block (b'') exists to refuse.
    """
    admitted = admitted_masks(legacy)
    if (basic_mask, actor_mask) not in admitted:
        shown = ", ".join(f"0x{b:04X}/0x{a:016X}" for b, a in admitted)
        raise LoginMaskError(
            f"frame mask 0x{basic_mask:04X}/0x{actor_mask:016X} is not a production "
            f"login mask (admitted: {shown}) -- COO-DECISION 20260904_0545 item 2 "
            "requires the frame's mask to equal the login block's mask exactly"
        )


def login_masks_for_connection(legacy, character_id, *, hooks=None) -> tuple[int, int]:
    """This connection's own login mask, once chief records it; else refuse.

    THE FALLBACK IS DELIBERATELY NOT A FALLBACK TO "THE FACTION BRANCH".  A
    connection that logged into a scene `world_faction_admission` does NOT
    admit was sent a block with no faction bit, on purpose and fail-closed;
    handing it a frame with x=11 set would overrule that gate from a lane that
    does not own it.  So when the read point is missing this function raises,
    and the callers that can still work without knowing WHICH branch (the wall
    in `attr_wire.make_update_attr_frame`, which only has to reject shapes
    production never composes) use `refuse_unless_login_shaped` instead.
    """
    if hooks is None:
        try:
            from .. import lane_hooks as hooks  # noqa: PLC0415 - see attr_wire
        except Exception as error:  # noqa: BLE001 - any import failure is a refusal
            raise LoginMaskError(
                f"no_login_mask_read_point: lane_hooks is unimportable "
                f"({type(error).__name__})"
            ) from None
    read_point = getattr(hooks, LOGIN_MASK_READ_POINT, None)
    if not callable(read_point):
        raise LoginMaskError(
            f"no_login_mask_read_point: lane_hooks.{LOGIN_MASK_READ_POINT} does not "
            "exist yet (asked for by CORE-REQUEST-GM-053, ordered by COO-DECISION "
            "20260904_0545 item 2)"
        )
    try:
        answer = read_point(character_id)
    except Exception as error:  # noqa: BLE001 - a hook may never take dispatch down
        raise LoginMaskError(
            f"login_mask_read_point_raised_{type(error).__name__}"
        ) from None
    if not (isinstance(answer, tuple) and len(answer) == 2):
        raise LoginMaskError(
            "not_a_mask_pair: the login mask read point returned "
            f"{type(answer).__name__}, expected (basic_mask, actor_mask)"
        )
    basic_mask, actor_mask = answer
    if not (isinstance(basic_mask, int) and isinstance(actor_mask, int)):
        raise LoginMaskError("not_a_mask_pair: both halves must be ints")
    refuse_unless_login_shaped(legacy, basic_mask, actor_mask)
    return basic_mask, actor_mask


def build_login_shaped_frame(
    legacy,
    character_id,
    identity_lo: int,
    identity_hi: int,
    overrides: dict,
    *,
    hooks=None,
    shape: tuple[int, int] | None = None,
) -> tuple[bytes, bytes]:
    """THE BUILDER LANE-B WAS TOLD TO PLUG IN (`COO-DECISION 20260904_0546`
    item 3: "you do not define the set yourself -- plug in the login-shaped
    builder LANE-GM ships").

    Composes ONE 0x309A frame whose mask equals a production login mask, from
    the live sources `COO-DECISION 0545` item 2 names, with the caller's own
    rows layered on top:

      * every `known=True` row in the login set  -> chief's live read point
      * x=7 and x=10                             -> the login byte read point
      * `overrides`                              -> the caller's own values
        (Door B's post-damage `hp_current`, `/speed`'s new speed)

    `overrides` MAY ONLY NAME ROWS THE LOGIN SET ALREADY CARRIES, and never a
    `SENSITIVE_FIELDS` row.  Both refusals are here rather than in the caller
    because this is the function two lanes share: a row outside the set would
    change the frame's mask (the wall then refuses it, but with a message
    about the mask instead of about the caller's mistake), and x=30 must be
    unreachable from every direction, not only from `build_named_field_update`.

    RETURNS `(pc, frame)`, IT DOES NOT SEND -- same posture as every other
    composer in this lane.  And it composes NOTHING today on a real boot:
    both read points are still missing, so this raises `AttrWireError` with
    their names in it.  That is the point of shipping it now -- the consumer
    exists, tested, before the round that first has something to send, and
    LANE-B can wire its call site against a function whose refusals are
    already the real ones.
    """
    if shape is None:
        # WHICH SHAPE THIS CONNECTION GOT IS A QUESTION, NOT A DEFAULT
        # (pf-adversary round `4fxkam`, D2, MEASURED).  Composing the union
        # here always set x=11, so a connection whose login composed the
        # PLAIN branch would have been handed a faction bit its login
        # deliberately withheld -- and, in the same breath, refused for a row
        # it never needed (`missing_named_rows: absent=11`, measured), which
        # is the "gate whose condition cannot be met" shape this module was
        # written to end.  So the shape comes from the connection, and when
        # nothing records it the answer is a refusal naming the request that
        # will fix that, not a guess.
        shape = login_masks_for_connection(legacy, character_id, hooks=hooks)
    refuse_unless_login_shaped(legacy, *shape)
    login_rows = field_x_for_masks(*shape)
    bad = sorted(set(overrides) - set(login_rows))
    if bad:
        raise LoginMaskError(
            f"overrides name rows {bad} that the login set does not carry "
            f"(login set: {list(login_rows)}) -- a row outside the set changes "
            "the frame's mask, which COO-DECISION 20260904_0545 item 2 requires "
            "to equal the login mask exactly"
        )
    sensitive = sorted(set(overrides) & attr_wire.SENSITIVE_FIELDS)
    if sensitive:
        raise LoginMaskError(
            f"overrides name SENSITIVE_FIELDS {sensitive}: no caller chooses that "
            "value through any door in this lane (COO-DECISION 20260904_0545 item 5)"
        )
    values = attr_wire.live_full_block_values(
        character_id, hooks=hooks, legacy=legacy, rows=login_rows,
    )
    values.update(overrides)
    return attr_wire.make_update_attr_frame(legacy, identity_lo, identity_hi, values)
