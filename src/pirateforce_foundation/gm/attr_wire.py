"""Groundwork for GM `/lv` (and future `/item`/`/npc`/`/spawn`-adjacent stat
commands) -> a real `UpdateAttrVital` (0x309A) frame.

STATUS THIS ROUND: composer + per-connection cache only.  NOTHING in this
module sends a byte to a real client yet (`UPDATE_ATTR_VITAL_VERSION_CONFIRMED`
below is `None`), and no chat command dispatches into it
(`gm/chat_command_action.py` does not import this module this round).  That
is deliberate, per `COO-DECISION 2026-08-31T16:50+07:00`
(`pf_bridge/notes_to_chief/20260831_1650_COO-DECISION-attr-wire-unlock-
condition-revised-name-all-24-fields-replaced-with-lossless-preserve.md`):
this round's job is to "design and prove the raw-block-per-connection
mechanism ... before asking for a version-confirmation unlock", not to ship
a live send.

## History, briefly (full chain in the round file, not repeated here)

`COO-DECISION 20260831_0146` approved lifting the owner's own ad-hoc
`PF_ADHOC_ATTR_PROBE` experiment (`pf_bridge/notes_to_chief/
reference_adhoc_probe/adhoc_attr_probe.py`, a fork the owner ran live for
266 commands / 2h20m in one connection, no crash) into this lane, with three
hard conditions: (a) always send the FULL block, never a sparse delta
(the client's ActorAttr apply is a bulk copy of the incoming object, not a
merge -- v141 note on 0x464F30); (b) real DB persistence across relog; (c)
normal audit/gate/test discipline. This lane's own round `w8hnu9`-successor
found condition (a) impossible with the only wired encoder that existed
then (`stats_progression_hypothesis.encode_actor_attr`, 23/47 fields), so
`COO-DECISION 20260831_1244` shelved the work pending 24 more named fields.
`COO-DECISION 20260831_1650` then relaxed that: the encoder only has to
cover every NAMED field (this module's 55-row `FIELDS` table below, not a
100%-of-47 bar), and the remaining unnamed fields must be preserved
losslessly from whatever the real current block is -- not zeroed, not
invented. That is the mechanism this module exists to build.
`COO-DECISION 2026-09-01T00:43+07:00` (`pf_bridge/notes_to_chief/
20260901_0043_COO-DECISION-attr-wire-unlock-criteria-replaced-shelve-stays-
locked.md`) ratified this as the standing 3-point unlock definition -- (a)
encoder covers every named field, (b) unnamed fields preserved lossless,
never zeroed, (c) a version-confirmation constant gates the live send, same
shape as `warp`/`say`. That letter does NOT audit this module against the
three points, and neither does this note: (a) and (c) hold at the code
level (`FIELDS` covers every `known=True` row; the gate constant below
mirrors `teleport_wire`/`say_wire`'s pattern exactly), but (b) is NOT yet
true as an outcome -- this module's own "open part" section above already
says the first named-field send will still zero every currently-nonzero
UNNAMED field, because there is no raw-block source to preserve them from
today. Whether that gap is closed by path 1 (accept the risk) or path 2
(name-only, possibly not viable) is still routed to the owner
(`pf_bridge/notes_to_chief/20260831_2327_LANE-GM-TO-OWNER-attr-wire-path1-
vs-path2-after-re172-negative.md`), per `COO-DECISION 20260831_1843`.
Nothing below sends live until that answer lands, and (b) is not satisfied
until it does.

## The proven part

`FIELDS` below reproduces the probe's own 55-row table (12 BasicAttr rows +
43 ActorAttr rows: tag, byte offset, kind, mask bit, name-or-placeholder) --
DATA the owner's live session already exercised byte-for-byte, not logic
copied from that reference (`reference_adhoc_probe/README_WHAT_THIS_IS.md`
rule 2: "if you want to use this for real, rewrite it in your own lane's
zone, with tests -- not copy-paste". This is a rewrite: same numbers,
independently re-derived call shape, this lane's own tests).
`encode_field`/`encode_block`/`make_update_attr_frame` below are new code
built for this module, not the probe's; they happen to produce the same
bytes the probe proved the client accepts, which is the point.

## The open part, stated exactly (this is the "design and prove" COO asked for)

The probe's own module docstring makes a strong claim: "a sparse delta would
zero what it omits" -- i.e. any field whose mask bit is NOT set in a given
`UpdateAttrVital` send does not survive as "unchanged", it becomes 0 on the
client. That claim is STATIC (a read of the v141 client apply routine at
0x464F30), never empirically checked against a real PRE-EXISTING nonzero
value, because every probe session started from a freshly created character
via `ProbeState.reset()` -- there was never a real prior value to check
against. If the claim is right, "preserve unknown fields losslessly"
requires supplying their CURRENT TRUE VALUE on every send, not merely
omitting them.

Where would this module get that value from, for a field it does not know
the name of? Searched before writing this docstring (rule: ค้นก่อนถอด):

  1. `model.Character` (this repo's own server-side character record) has
     NO level/hp/stat fields at all -- `id, account_id, selector, name,
     actor_wire, avatar_wire, identity_lo, identity_hi, position`. There is
     nothing here to read.
  2. `characters.actor_wire` (`migrations/001_initial.sql`) is a real,
     per-character, byte-preserved BLOB -- but it is `CreateActorDataEx`
     (a DIFFERENT vital/codec from `gm/actor_wire.py`, this repo's own
     `Known-safe edits to the otherwise opaque CreateActorDataEx wire`),
     not a standalone ActorAttr/BasicAttr DBAttribute collection. WHETHER
     its embedded sub-structure shares this module's `FIELDS` offsets is an
     open, answerable, static question -- if yes, that BLOB is a ready-made
     raw-block source needing no runtime.py change at all; if no, there is
     no source at all today. NOT ANSWERED HERE -- routed to chief/RE, see
     the round's CORE-REQUEST-GM-044 letter. [สมมติของสาย GM - รอ RE]
  3. No `lane_hooks` point exists today that hands a lane the fields
     `runtime.py`'s login path is about to send for this shape, because
     (per point 1/2) runtime.py does not compose an ActorAttr/BasicAttr
     DBAttribute block at login at all -- there is nothing at that point to
     capture. A CORE-REQUEST asking chief to add one would be asking for a
     hook onto data that provably does not exist yet, so this round does
     NOT open one (would have been last round's first draft of this
     docstring's mistake, caught before writing the letter).

## This round's provisional decision (build now, do not stall)

Per this lane's own rule ("you do not answer questions, you build things --
what you do not know yet, ask; build what you already can"), this module
ships with a decision, tagged for COO confirmation:

  [สมมติของสาย GM - รอ COO ยืนยัน] Until question 2 above is answered, this
  module's public compose entry point (`build_named_field_update`) refuses
  to touch ANY field this table marks `known=False` -- their mask bits are
  NEVER set by this module, in any send, ever. This does not resolve the
  open question (if the probe's "omission = zero" claim is right, the very
  first named-field send this module ever makes will still zero every
  currently-nonzero unnamed field on that character, once, the same way the
  probe's own sessions would have on a non-fresh character) -- it bounds
  the scope of what THIS module claims to have solved to exactly the set
  COO's revised wording named ("every field with a confirmed name/offset"),
  and refuses to guess at the rest. Whether that first-send risk is
  acceptable is a COO/owner call, not this lane's to make alone, and is
  named again in the round letter and CORE-REQUEST-GM-044.

  RawBlockCache (below) is deliberately SOURCE-AGNOSTIC: whichever answer
  question 2 gets, `capture_initial()` takes a plain `{x: value}` dict, so
  this class needs no rewrite once a real source exists -- only a caller
  that seeds it does.

## The one unconditional guarantee this round DOES ship

`build_named_field_update` raises `AttrWireError` -- refuses to compose
anything at all -- for ANY connection whose `RawBlockCache` has never been
seeded via `capture_initial()`. No call site in this lane, this round, ever
calls it. That is what makes "nothing sends yet" true by construction
rather than by convention: there is no path through this module today that
can invent a baseline it was not handed.
"""
from __future__ import annotations

import struct

AC_ATTR_ID = 0x12AD
UPDATE_ATTR_VITAL_ID = 0x309A
DB_ATTRIBUTE_IDENTITY_BIT = 1
ACTOR_ATTR_EXTRA_GROUP_VALUE = 1

# !! THIS LANE'S SEND GATE FOR 0x309A.  `None` means: no `UpdateAttrVital`
# frame this module composes may reach a real socket.  Deliberately not
# flipped this round -- see module docstring "STATUS THIS ROUND".  Shaped
# like `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` /
# `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED`: an `int` once a real
# vital_version byte is proven AND the raw-block-source question above is
# closed AND COO says the flip is allowed -- three conditions, not one.
UPDATE_ATTR_VITAL_VERSION_CONFIRMED: int | None = None

# x, block, mask_bit, offset, tag, kind, name, known, note
#
# kinds: u8 u16 u32 i32 f32 u64 wstr blob
# `known` mirrors the probe table's own "[รู้]"/"[ไม่รู้]"/"[รู้บางส่วน]"
# tags, collapsed to a bool: True only for a field this lane's own
# `build_named_field_update` is allowed to set a mask bit for (see module
# docstring, "This round's provisional decision"). "[รู้บางส่วน]" rows are
# `known=False` here -- a partial/unconfirmed name is not the same claim as
# a proven one, and this module's refusal gate cares about the stronger
# claim only.
FIELDS = (
    (1,  "basic", 0x0001, 0x028, 0x48, "wstr", "name",            True,  "LABEL_NAME"),
    (2,  "basic", 0x0002, 0x05E, 0x12, "u16",  "level",           True,  "GetLv"),
    (3,  "basic", 0x0004, 0x044, 0x14, "u32",  "hp_current",      True,  "HP bar"),
    (4,  "basic", 0x0008, 0x048, 0x14, "u32",  "hp_max",          True,  ""),
    (5,  "basic", 0x0010, 0x04C, 0x14, "u32",  "mp_current",      True,  ""),
    (6,  "basic", 0x0020, 0x050, 0x14, "u32",  "mp_max",          True,  ""),
    (7,  "basic", 0x0040, 0x054, 0x2A, "f32",  "basic_f32_54",    False, "unknown f32"),
    (8,  "basic", 0x0080, 0x058, 0x2A, "f32",  "death_timer",     True,  "dying countdown f32"),
    (9,  "basic", 0x0100, 0x05C, 0x12, "u16",  "category_5C",     False, "partial: ==8 swaps HP to x52/53"),
    (10, "basic", 0x0200, 0x060, 0x32, "u64",  "basic_q60",       False, "unknown"),
    (11, "basic", 0x0400, 0x068, 0x14, "u32",  "basic_faction",   True,  "1 = player side"),
    (12, "basic", 0x0800, 0x06C, 0x14, "u32",  "basic_u32_6C",    False, "unknown"),
    (13, "actor", 1 << 0,  0x08C, 0x19, "u32",  "class_id",        True,  "GetClass"),
    (14, "actor", 1 << 1,  0x090, 0x19, "u32",  "nameboard_key",   False, "partial: NameBoard nickname key"),
    (15, "actor", 1 << 2,  0x078, 0x26, "i32",  "actor_x26_78",    False, "unknown tag 0x26"),
    (16, "actor", 1 << 3,  0x07C, 0x19, "u32",  "skill_points",    True,  "SP"),
    (17, "actor", 1 << 4,  0x080, 0x12, "u16",  "unspent_points",  True,  "unspent stat points"),
    (18, "actor", 1 << 5,  0x082, 0x12, "u16",  "str",             True,  "LABEL_STR"),
    (19, "actor", 1 << 6,  0x084, 0x12, "u16",  "con",             True,  "LABEL_CON"),
    (20, "actor", 1 << 7,  0x086, 0x12, "u16",  "dex",             True,  "LABEL_DEX"),
    (21, "actor", 1 << 8,  0x088, 0x12, "u16",  "int_",            True,  "LABEL_INT"),
    (22, "actor", 1 << 9,  0x08A, 0x12, "u16",  "per",             True,  "LABEL_PER"),
    (23, "actor", 1 << 10, 0x0A0, 0x32, "u64",  "experience",      True,  "XP bar"),
    (24, "actor", 1 << 11, 0x0A8, 0x32, "u64",  "cash",            True,  "GetCash"),
    (25, "actor", 1 << 12, 0x0B0, 0x48, "wstr", "wstr_B0",         False, "unknown text 1"),
    (26, "actor", 1 << 13, 0x099, 0x0B, "u8",   "u8_99",           False, "unknown"),
    (27, "actor", 1 << 14, 0x09A, 0x0B, "u8",   "u8_9A",           False, "unknown"),
    (28, "actor", 1 << 15, 0x13E, 0x12, "u16",  "u16_13E",         False, "unknown"),
    (29, "actor", 1 << 16, 0x13C, 0x12, "u16",  "u16_13C",         False, "unknown"),
    # x=30: SENSITIVE, see SENSITIVE_FIELDS below. Never set via the named-
    # field API even once this field is renamed True by a future RE result.
    (30, "actor", 1 << 17, 0x148, 0x44, "blob", "blob_148",        False, "unknown hex; SEE SENSITIVE_FIELDS"),
    (31, "actor", 1 << 18, 0x182, 0x12, "u16",  "bonus_str",       True,  ""),
    (32, "actor", 1 << 19, 0x184, 0x12, "u16",  "bonus_con",       True,  ""),
    (33, "actor", 1 << 20, 0x186, 0x12, "u16",  "bonus_dex",       True,  ""),
    (34, "actor", 1 << 21, 0x188, 0x12, "u16",  "bonus_int",       True,  ""),
    (35, "actor", 1 << 22, 0x18A, 0x12, "u16",  "bonus_per",       True,  ""),
    (36, "actor", 1 << 23, 0x18C, 0x0B, "u8",   "u8_18C",          False, "unknown"),
    (37, "actor", 1 << 24, 0x164, 0x48, "wstr", "wstr_164_guild",  True,  "-> LABEL_GUILD (probe sent a character name here safely)"),
    (38, "actor", 1 << 25, 0x180, 0x0B, "u8",   "u8_180",          False, "unknown"),
    (39, "actor", 1 << 26, 0x098, 0x0B, "u8",   "u8_98_pairA",     False, "unknown, shares bit with x40"),
    (40, "actor", 1 << 26, 0x094, 0x19, "u32",  "u32_94_pairA",    False, "unknown, shares bit with x39"),
    (41, "actor", 1 << 27, 0x140, 0x32, "u64",  "q_140_pairB",     False, "unknown, shares bit with x42"),
    (42, "actor", 1 << 27, 0x09B, 0x0B, "u8",   "u8_9B_pairB",     False, "unknown, shares bit with x41"),
    (43, "actor", 1 << 28, 0x0CC, 0x48, "wstr", "wstr_CC",         False, "unknown text 2"),
    (44, "actor", 1 << 29, 0x198, 0x32, "u64",  "q_198",           False, "unknown"),
    (45, "actor", 1 << 30, 0x190, 0x32, "u64",  "q_190",           False, "unknown"),
    (46, "actor", 1 << 32, 0x1A0, 0x0B, "u8",   "u8_1A0",          False, "unknown"),
    (47, "actor", 1 << 33, 0x1A2, 0x12, "u16",  "u16_1A2",         False, "unknown"),
    (48, "actor", 1 << 34, 0x1A4, 0x12, "u16",  "u16_1A4",         False, "unknown"),
    (49, "actor", 1 << 35, 0x0E8, 0x48, "wstr", "wstr_E8",         False, "unknown text 3"),
    (50, "actor", 1 << 36, 0x104, 0x48, "wstr", "wstr_104",        False, "unknown text 4"),
    (51, "actor", 1 << 37, 0x120, 0x48, "wstr", "wstr_120",        False, "unknown text 5"),
    (52, "actor", 1 << 38, 0x1A8, 0x14, "u32",  "alt_hp_current",  True,  "used when x9 == 8"),
    (53, "actor", 1 << 39, 0x1AC, 0x14, "u32",  "alt_hp_max",      True,  ""),
    (54, "actor", 1 << 40, 0x1B0, 0x12, "u16",  "u16_1B0",         False, "unknown"),
    (55, "actor", 1 << 41, 0x1B2, 0x0B, "u8",   "u8_1B2",          False, "unknown"),
)
BY_X = {f[0]: f for f in FIELDS}
BY_NAME = {f[6]: f for f in FIELDS}

# x=30 (ActorAttr +0x148): an UNADJUDICATED Codex checkpoint corpus
# (`pf_bridge/notes_to_chief/reference_codex_attr/`, still carrying open
# "CONFLICTS"/"UNRESOLVED_BUCKETS" files as of this round -- not treated as
# settled fact) names this offset as an MD5 of the account's second
# password plus its account name. Not cross-checked against a second
# source, and `known` above stays False for it either way -- but a
# SECURITY-shaped guess is worth refusing outright rather than merely
# leaving unnamed, in case a future round widens `known` from this same
# unresolved corpus without re-reading this comment first.
SENSITIVE_FIELDS = frozenset({30})


class AttrWireError(ValueError):
    """A `/lv`-family attribute update cannot be composed as given."""


def parse_value(kind: str, text: str):
    if kind in ("u8", "u16", "u32", "u64"):
        value = int(text, 0)
        width = {"u8": 1, "u16": 2, "u32": 4, "u64": 8}[kind]
        if value < 0 or value >= (1 << (8 * width)):
            raise AttrWireError(f"value out of range for {kind}: {text!r}")
        return value
    if kind == "i32":
        value = int(text, 0)
        if value < -(1 << 31) or value >= (1 << 31):
            raise AttrWireError(f"value out of range for i32: {text!r}")
        return value
    if kind == "f32":
        return float(text)
    if kind == "wstr":
        return text
    if kind == "blob":
        return bytes.fromhex(text)
    raise AttrWireError(f"unknown field kind {kind!r}")


def encode_field(legacy, field: tuple, value) -> bytes:
    """One tagged field, using the loaded `pf_login_game_server_v141`
    module's own tag helpers (`legacy_bridge.load_legacy`) -- this module
    does not re-derive `u8tag`/`u16tag`/`u32tag`/`qwordtag`, the same seam
    `gm/state_wire.py`/`gm/bt_gm_probe.py` already use."""
    tag, kind = field[4], field[5]
    if kind == "u8":
        if not (0 <= value <= 0xFF):
            raise AttrWireError(f"{field[6]}: u8 out of range: {value!r}")
        return legacy.u8tag(tag, value)
    if kind == "u16":
        if not (0 <= value <= 0xFFFF):
            raise AttrWireError(f"{field[6]}: u16 out of range: {value!r}")
        return legacy.u16tag(tag, value)
    if kind == "u32":
        if not (0 <= value <= 0xFFFFFFFF):
            raise AttrWireError(f"{field[6]}: u32 out of range: {value!r}")
        return legacy.u32tag(tag, value)
    if kind == "i32":
        if not (-(1 << 31) <= value < (1 << 31)):
            raise AttrWireError(f"{field[6]}: i32 out of range: {value!r}")
        return bytes([tag]) + struct.pack("<i", value)
    if kind == "f32":
        return bytes([tag]) + struct.pack("<f", float(value))
    if kind == "u64":
        if not (0 <= value <= 0xFFFFFFFFFFFFFFFF):
            raise AttrWireError(f"{field[6]}: u64 out of range: {value!r}")
        return legacy.qwordtag(tag, value)
    if kind == "wstr":
        if not isinstance(value, str):
            raise AttrWireError(f"{field[6]}: wstr requires str, got {value!r}")
        body = value.encode("utf-16le")
        return bytes([tag]) + struct.pack("<I", len(body)) + body
    if kind == "blob":
        raw = bytes(value)
        return bytes([tag]) + struct.pack("<I", len(raw)) + raw
    raise AttrWireError(f"unknown field kind {kind!r}")  # pragma: no cover - FIELDS-shape guard


def encode_block(legacy, identity_lo: int, identity_hi: int, values: dict) -> tuple[bytes, int, int]:
    """`values` (`{x: value}`) -> the DBAttribute body:
    `identity` -> `BasicAttr(mask u16 + fields asc)` -> `ActorAttr(mask u64
    + group flag + fields asc)`.  Only `x` keys present in `values` get a
    mask bit; the caller (`build_named_field_update`) is what enforces the
    `known`/`SENSITIVE_FIELDS` policy -- this function trusts its input,
    the same separation `gm/warp_executor.py` keeps between its parse-time
    catalog hint and its dispatch-time refusal.

    Paired mask bits (x39/x40 share one ActorAttr bit, as does x41/x42) are
    enforced HERE, not upstream: both halves of a pair must be present
    together or neither -- a caller that sets one without the other gets a
    named `AttrWireError`, never a frame with one half silently missing.
    """
    for a, b in ((39, 40), (41, 42)):
        if (a in values) != (b in values):
            raise AttrWireError(
                f"fields {a} and {b} share one mask bit -- set both or neither"
            )
    basic_mask = 0
    basic_body = b""
    actor_mask = 0
    actor_body = b""
    for field in FIELDS:
        x, block, bit = field[0], field[1], field[2]
        if x not in values:
            continue
        encoded = encode_field(legacy, field, values[x])
        if block == "basic":
            basic_mask |= bit
            basic_body += encoded
        else:
            actor_mask |= bit
            actor_body += encoded
    body = (
        legacy.u8tag(0x0B, DB_ATTRIBUTE_IDENTITY_BIT)
        + bytes([0x32])
        + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + legacy.u16tag(0x12, basic_mask)
        + basic_body
        + legacy.qwordtag(0x32, actor_mask)
        + legacy.u8tag(0x05, ACTOR_ATTR_EXTRA_GROUP_VALUE)
        + actor_body
    )
    return body, basic_mask, actor_mask


def make_update_attr_frame(legacy, identity_lo: int, identity_hi: int, values: dict) -> tuple[bytes, bytes]:
    """Full runtime-vital envelope for one `UpdateAttrVital` (0x309A) send.

    Not gated on `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` -- same separation
    `state_wire.make_gm_update_state_frame` keeps from its own caller-side
    gate: this is a pure byte builder, exercised freely by this module's own
    tests; the gate lives at the one call site allowed to reach a real
    socket, which this round has none of (see module docstring).
    """
    body, _basic_mask, _actor_mask = encode_block(legacy, identity_lo, identity_hi, values)
    payload = (
        legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, AC_ATTR_ID)
        + legacy.u32tag(0x14, len(body))
        + body
    )
    return legacy.make_runtime_vitals(
        [(UPDATE_ATTR_VITAL_ID, 0, payload)]
    )


class RawBlockCache:
    """Per-connection memory of "the last full ActorAttr/BasicAttr block
    this module itself put on the wire for this character" -- deliberately
    SOURCE-AGNOSTIC (see module docstring, "This round's provisional
    decision"): `capture_initial` takes a plain `{x: value}` dict from
    whatever caller eventually seeds it (a decoded `characters.actor_wire`,
    a future runtime.py hand-off, or -- today -- nobody, which is exactly
    why nothing can send yet).

    One instance per connection, held on the session object by whatever
    future dispatch wiring adds it (out of scope this round -- no call site
    constructs one yet outside this module's own tests).
    """

    def __init__(self) -> None:
        self._values: dict[int, object] = {}
        self._captured = False

    def is_captured(self) -> bool:
        return self._captured

    def capture_initial(self, values: dict) -> None:
        """Seed the cache with the connection's real starting values.
        Idempotent by design (a reconnect may call this again) -- the LATEST
        capture always wins, never merged with a stale one."""
        self._values = dict(values)
        self._captured = True

    def current_values(self) -> dict:
        return dict(self._values)

    def merged_with(self, overrides: dict) -> dict:
        if not self._captured:
            raise AttrWireError(
                "RawBlockCache has no captured baseline for this connection "
                "-- refusing to synthesize one (see attr_wire module "
                "docstring, the one unconditional guarantee)"
            )
        merged = dict(self._values)
        merged.update(overrides)
        return merged

    def record_sent(self, values: dict) -> None:
        """Update the cache to exactly what a send just put on the wire --
        called by `build_named_field_update` after a successful compose, so
        the NEXT command in this connection builds on real prior state, not
        a second guess."""
        self._values = dict(values)
        self._captured = True


def build_named_field_update(
    legacy, cache: RawBlockCache, identity_lo: int, identity_hi: int, x: int, value,
) -> tuple[bytes, bytes]:
    """The one entry point a future chat-command action should call.

    Refuses, by name, every one of:
      * `x` not in `FIELDS` at all;
      * `x` in `SENSITIVE_FIELDS` (never settable through this API, known or
        not -- see that set's own comment);
      * `x` present but `known=False` (this round's provisional scope
        limit, [สมมติของสาย GM - รอ COO ยืนยัน] -- see module docstring);
      * `cache` never seeded (`RawBlockCache.merged_with` raises).

    On success, updates `cache` to the merged block it just composed (see
    `RawBlockCache.record_sent`) and returns `(pc, frame)` -- NOT sent by
    this function; same posture as `gm/warp_executor.py`/`gm/say_wire.py`,
    a caller sends.
    """
    field = BY_X.get(x)
    if field is None:
        raise AttrWireError(f"unknown field x={x!r} (valid: 1..{len(FIELDS)})")
    if x in SENSITIVE_FIELDS:
        raise AttrWireError(f"field x={x} ({field[6]}) is refused: SENSITIVE_FIELDS")
    if not field[7]:
        raise AttrWireError(
            f"field x={x} ({field[6]}) is not in this round's known-field "
            f"scope -- see attr_wire module docstring 'provisional decision'"
        )
    merged = cache.merged_with({x: value})
    pc, frame = make_update_attr_frame(legacy, identity_lo, identity_hi, merged)
    cache.record_sent(merged)
    return pc, frame
