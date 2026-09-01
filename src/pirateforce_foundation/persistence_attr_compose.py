"""LANE-DB: decide, per field, whether the server may put a value in an
``UpdateAttrVital`` (0x309A) attribute block at all -- and refuse to compose
the block when it may not.

WHY THIS FILE EXISTS.  The owner's rule, relayed verbatim in
``COO-DECISION 2026-09-01T10:59+07:00`` (``pf_bridge/notes_to_chief/
20260901_1059_COO-DECISION-owner-rules-attr-wire-new-db-lane-answers-1-vs-
2.md``): a block in which an unknown field is GUESSED TO BE ZERO must never
be sent.  ``COO-DECISION 2026-09-01T11:00+07:00`` then made typed columns in
this server's own database the source of truth, and the attribute block
something the server COMPOSES from those columns plus the character's own
proven construction values -- nothing else.

This module is the gate that makes both of those checkable instead of
promised.  It holds no wire encoder of its own (``gm/attr_wire.py`` owns the
55-row ``FIELDS`` table and the tag encoders; this module imports that table
read-only and never writes to that lane's files) and it opens no database.
It answers exactly one question, per field, before any encoder runs:

    where would the value for this field come from, and is that source
    evidence or a guess?

Four answers, and only the first two may ever reach a frame:

``SERVER_OWNED``
    A typed column in this server's own database is the truth for this field
    (level, hp, stats, exp, and -- this lane's first one -- walk speed).  The
    value must be handed in by the caller; this module NEVER substitutes a
    default for a server-owned field that the caller did not supply, because
    the substitute would be indistinguishable from the guessed zero the owner
    banned.  Fields whose typed column does not exist in ``migrations/`` yet
    are still SERVER_OWNED here: the source is named, it is simply not built,
    and until it is, a caller cannot supply the value and the block cannot be
    composed.  That is the intended, loud failure.
``CLIENT_DEFAULT``
    The client's own constructor writes a proven value into this offset, and
    the Codex corpus records both the value and the VA of the instruction
    that writes it (``PF_ATTR_FIELD_SEMANTICS.tsv`` columns ``default_value``
    / ``default_writer_va``, ``structural_status=PROVEN_EXACT``).  Re-sending
    that same value is not a guess -- but see RESEND ADJUDICATION below,
    which is why holding a proven default is NOT by itself enough to send.
``UNSOURCED``
    Seven fields have no typed column, no proven default, and no name.  There
    is no honest value for them, so there is no block.  Closing these seven is
    a Codex/RE question routed through chief, not a decision this lane may
    make by picking a number that "looks fine".  Re-derived across the WHOLE
    corpus this round, not just the semantics table: three of the seven (x=14
    ActorAttr+0x090, x=41 +0x140, x=42 +0x09B) have no row of any kind in any
    file, and the mask bit x=41/x=42 share (0x08000000) is assigned to nothing
    anywhere in the corpus; the other four (x=25 +0x0B0, x=36 +0x18C, x=43
    +0x0CC, x=54 +0x1B0) appear only in ``PF_A2_ACTOR_CODEC_CORRECTION.tsv``
    as gate corrections still marked ``OPEN_REDERIVED_IMAGE_CONFLICT``, and
    those rows carry no ``default_value`` column at all.  (The gate words in
    those rows, ``+0x1B4``/``+0x1B8``, are not an extra gate this encoder
    misses: all 50 ActorAttr correction rows' gate masks equal the field's own
    ``FIELDS`` mask bit exactly, low dword at +0x1B4 and high at +0x1B8, so
    those two words ARE the ActorAttr mask ``encode_block`` already emits.
    Measured before it was written down, because the first reading of these
    rows said the opposite.)
``REFUSED``
    ``gm/attr_wire.SENSITIVE_FIELDS`` (x=30, ActorAttr+0x148, named by the
    Codex corpus as an MD5 over the account's second password).  A proven
    construction default exists for it -- the empty sequence -- and that makes
    it MORE dangerous, not less: composing a "full block" from construction
    defaults would hand the client an empty value for a live credential-shaped
    field.  Refused unconditionally, in every direction, forever.

## WHY NOT THE CHARACTER'S OWN CREATION BLOB (the first thing to ask)

``COO-ORDER 20260901_1101`` told this lane to try a different second source
first: ``characters.actor_wire`` / ``characters.avatar_wire``
(``migrations/001_initial.sql:4``, real per-character BLOBs, byte-preserved
since creation) as the base, with typed values overlaid -- so that an unknown
field keeps THAT CHARACTER's own byte instead of a class-wide default.  That
is a better source than the one this module uses, and it is deliberately not
used here.  The reason is a measurement, not a preference:

  ``CHIEF-REPLY 20260831_1810`` (CORE-REQUEST-GM-044) measured the blob and
  found it is ``AvatarAttr`` -- a DIFFERENT class from the ``ActorAttr`` /
  ``BasicAttr`` pair ``UpdateAttrVital`` carries.  ``actor_wire.py:53-57`` in
  this repository says the same thing about its own payload, and the two
  containers disagree on mask width (``gm/attr_wire.py:342-344``: BasicAttr
  mask is a u16 at tag 0x12, ActorAttr's a u64 at tag 0x32).  Several offsets
  coincide (0x44 0x48 0x4C 0x50 0x54 0x58 0x5C 0x5E), which is what makes the
  overlay dangerous rather than merely wrong: it composes cleanly and writes
  body-proportion bytes into stat fields.

So the overlay is blocked on evidence, not on effort.  ``LANE-DB ASK 20260901_1201``
put that contradiction to COO and is still unanswered as of this round; if COO
rules that the blob IS a usable base (or RE finds an ActorAttr-shaped blob
somewhere), this module's ``CLIENT_DEFAULT`` class is what gets replaced, and
the RESEND ADJUDICATION problem below dissolves with it -- re-sending a
character's own byte needs no adjudication.  [สมมติของสาย DB - รอ COO ยืนยัน]

## RESEND ADJUDICATION -- the part that is deliberately not finished here

A construction default is what the client wrote into the object WHEN IT BUILT
IT.  For a field the client never touches again, that value is still true at
send time.  For a field the client itself maintains during play, it is not:
re-sending the constructor's value would reset live client state.  Measured in
the corpus this round, not assumed: all 28 fields that carry a construction
default also carry ``write_site_va``/``producer_va`` entries that are NOT the
``default_writer_va``, and 11 of the 28 carry at least one that falls outside
both VA clusters the remaining rows sit in (x=7 0x0045C11A, x=11 0x0045C0D6,
x=12 0x0045C0F9, x=15 0x00755171, x=26 0x004B45CB, x=27 0x004BF978, x=30
0x005DEC50, x=46 0x0053D3C4, x=49 0x0063A2D0, x=50 0x0063A390, x=51
0x0063A450).  Sitting outside the cluster is a shape, not a verdict: a codec
write and a gameplay write look identical in this table, and telling them apart
is an RE question this lane cannot answer from the corpus.  So no field is
adjudicated safe to re-send here:
``RESEND_ADJUDICATED`` is empty on purpose, and a full block therefore cannot
be composed today even if every column existed.  ``block_gaps`` reports that
as its own reason code rather than hiding it behind the missing columns.

## What this module guarantees, and how it is tested

1. No value ever leaves here that the caller did not supply or that the Codex
   corpus did not prove -- there is no ``dict.get(x, 0)`` anywhere in it.
2. A field whose source is missing produces a NAMED gap, never a silent
   substitution: ``compose_full_block`` raises and the exception lists every
   blocked field with its reason.
3. The partition is total and disjoint: every one of the 55 rows of ``FIELDS``
   has exactly one source, checked at import time (``_verify_partition``).
4. Every value is produced by ONE function, ``_value_for``.  It is tested
   directly, field by field, rather than only through ``compose_full_block``
   -- which today cannot return at all (x=30 is refused unconditionally), so a
   guarantee tested only through it would be vacuously green.

## WHAT THIS MODULE DOES NOT DO -- read before quoting its numbers

* It cannot tell a real typed-column read from a caller that passed zeros.
  ``compose_full_block`` proves the value came from ``typed_values``; proving
  ``typed_values`` came from the database is the caller's job, and no code
  here can check it.
* ``structural_status == PROVEN_EXACT`` is read on its own.  Measured: 12 of
  the 28 copied rows also carry a non-empty ``open_conflicts_with``, and the
  corpus's ``PF_ATTR_CONFLICTS_OPEN_WIRED.tsv`` lists 30 of these 55 fields as
  unruled.  For most of those the open dispute is about the mask/group gate
  rather than ``default_value`` -- but x=37 (``+0x164``) sits on the unruled
  side of an open SEMANTIC conflict, so its name here is not settled.
  ``gm/attr_wire.py:228-236`` says the same about this corpus in general.
* The corpus mirror it copies from declares itself stale
  (``reference_codex_attr/README_WHAT_THIS_IS.md:1``) and three different
  generation ids appear inside that one directory.  ``CORPUS_IMAGE_SHA256``
  below pins the client image the copied rows claim to describe, which is the
  part that matters for a value; it does NOT pin the generation.
* The 21 column names in ``SERVER_OWNED_FIELDS`` were this lane's own proposal
  for M4; ``migrations/006_character_typed_attribute_columns.sql`` builds them,
  so they are schema now.  What they are NOT is populated: 006 adds columns and
  writes no row, so every one of them reads NULL until something seeds it, and
  a NULL column is absent at this gate rather than zero.  The NAME
  ``speed_walk`` still encodes an unproven identification of BasicAttr+0x54.
  [สมมติของสาย DB - รอ RE]
"""
from __future__ import annotations

from dataclasses import dataclass

from .gm.attr_wire import BY_X, FIELDS, SENSITIVE_FIELDS

SERVER_OWNED = "server_owned"
CLIENT_DEFAULT = "client_default"
UNSOURCED = "unsourced"
REFUSED = "refused"

CODEX_TSV = (
    "pf_bridge/notes_to_chief/reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv"
)
# The client image every copied row below claims to describe (`image_sha256`
# column).  Pinned because that directory carries three different generation
# ids and its own README calls the mirror stale: a row re-derived from another
# image is not the row this table copied, and the test says so out loud.
CORPUS_IMAGE_SHA256 = (
    "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"
)


class AttrComposeError(ValueError):
    """A full attribute block cannot be composed from evidence as asked."""


@dataclass(frozen=True)
class ClientConstructionDefault:
    """One row of the Codex corpus, copied with its provenance attached.

    ``value`` is the corpus's ``default_value`` cell rendered into the python
    type ``FIELDS`` gives the field (``empty_sequence`` -> ``""`` / ``b""``,
    ``all_zero`` -> ``0``); ``writer_va`` is the corpus's ``default_writer_va``
    verbatim, so any claim made from this table can be walked back to the
    instruction it came from.
    """

    x: int
    value: object
    writer_va: str
    semantic_name: str


@dataclass(frozen=True)
class ServerOwnedField:
    """A field whose truth is a typed column in this server's database.

    ``column`` is the column name in ``characters`` this lane will use (or
    already uses -- ``name`` is real today).  ``column_exists`` says whether
    ``migrations/`` actually defines it yet; nothing in this module reads a
    database, so this flag exists to make the reason for a refusal precise
    ("no column yet") instead of merely absent.
    """

    x: int
    column: str
    column_exists: bool
    seed_from_client_default: bool


@dataclass(frozen=True)
class BlockGap:
    """One reason the block cannot be composed, named."""

    x: int
    field_name: str
    reason: str
    detail: str


# -- The 28 proven construction defaults -------------------------------------
# Every row below is `class` + `offset` matched against CODEX_TSV, taking only
# rows whose `structural_status` is PROVEN_EXACT.  Regenerating this table from
# the corpus is what `test_client_defaults_match_the_codex_corpus` does when
# the corpus is present, so a corpus revision cannot silently disagree with it.
_CLIENT_DEFAULT_ROWS = (
    (1, "", "0x00464AAF|0x00464ACF", "NameBoard_Player_LABEL_NAME_text"),
    # x=7: the VALUE (400.0, written at 0x00464AF2 by the BasicAttr
    # constructor) is a construction fact.  The NAME is not settled for the
    # player: the corpus scopes this row `applies_to_class = CNetNPC` and its
    # semantic name is a MOBS table field, while `gm/attr_wire.py:173` still
    # calls the same offset `basic_f32_54`, `known=False`, "unknown f32".  The
    # corpus gives it a second name too (`FightAttr_run_speed_formula_input`).
    # So "+0x54 is the player's walk speed" is [สมมติของสาย DB - รอ RE], and
    # `speed_walk` below is named on that unproven identification.
    (7, 400.0, "0x00464AF2", "MOBS.n_SPEED_WALK_to_initial_visual_horizontal_locomotion_scalar"),
    (8, 0.0, "0x00464B0E", "Main_Dead_threshold_operand_vs_DURATION_DYING_minus_0_5"),
    (9, 0, "0x00464AFA", "scene_id__SCENE_NAME.n_ID"),
    (10, 0, "0x00464B13|0x00464B16", "TeleportVital_qword_at_0x18_copied_from_BasicAttr_plus_0x60"),
    (11, 0, "0x00464B19", "CNetNPC.template.n_FACTION"),
    (12, 0, "0x00464B1C", "CNetNPC.template.n_ENEMY"),
    (15, 0, "0x00464CBA", "GetPpClass_value"),
    (26, 0, "0x00464D5D", "state_record_forced_flag"),
    (27, 0, "0x00464D63", "source_state_appearance_byte"),
    (28, 0x03FC, "0x00464D75", "CGCPotionModule_thousand_quotient_positive_flag_and_mod1000_value_u16"),
    (29, 1, "0x00464D91", "UNKNOWN"),
    (30, b"", "0x00464C73", "second_password_account_md5_upper_hex"),
    (37, "", "0x00464C84", "NameBoard_Player_LABEL_GUILD_text"),
    (38, 0, "0x00464DFC", "LABEL_GUILD_FontStyleID_selector"),
    (39, 0, "0x00464D69", "CNetActor_pair_relation_zero_gate"),
    (40, 0, "0x00464D6F", "UNKNOWN"),
    (44, 0, "0x00464DD0|0x00464DD6", "target_panel_enemy_actor_id"),
    (45, 0, "0x00464DDC|0x00464DE2", "target_panel_friend_actor_id"),
    (46, 0, "0x00464DE8", "Navy_Pirate_icon_selector"),
    (47, 0, "0x00464DEE", "two_decimal_digit_display_value"),
    (48, 0, "0x00464DF5", "UNKNOWN"),
    (49, "", "0x00464D2A", "residence_location_text"),
    (50, "", "0x00464D3B", "age_text"),
    (51, "", "0x00464D4C", "constellation_text"),
    (52, 0xFFFFFFFF, "0x00464E02", "GetBoatHealth_current"),
    (53, 1, "0x00464E0C", "GetBoatHealth_max"),
    (55, 0, "0x00464E16", "SELL_STALL_BASIC_addend_u8"),
)
CLIENT_CONSTRUCTION_DEFAULTS: dict[int, ClientConstructionDefault] = {
    row[0]: ClientConstructionDefault(*row) for row in _CLIENT_DEFAULT_ROWS
}

# -- Fields whose truth is a column in this server's database ----------------
# All twenty-two columns exist as of `migrations/006_character_typed_attribute
# _columns.sql`: `characters.name` since 001_initial.sql, the other twenty-one
# added by 006 (nullable, no defaults, no backfill).  `column_exists` is still
# a hand-written flag and still not trusted: `SchemaPinTests` builds a database
# from `migrations/` and compares `PRAGMA table_info(characters)` against it,
# so a future column added here without a migration -- or a migration whose
# column is renamed -- goes red rather than turning into a false reason in a
# letter.  `persistence_typed_attrs` is the runtime side of the same list.
# x=7 (walk speed) is the first one this lane was ordered to build
# (COO-ORDER 20260901_1101); its seed at character creation is the client's own
# proven 400.0 above -- a value with provenance, not a server invention -- and
# that seed is NOT written yet.  It no longer waits on the snapshot mechanism
# (`app.py:784`/`:787` call `SQLiteStore.migrate_with_backup`; CORE-REQUEST-DB
# -001 is answered on main).  It waits on the NUMBER: `COO-DECISION
# 20260901_1447` point 2 forbids seeding this column with 400.0 or with the
# 150.0 proven on the wire for NPCs until an RE says which a player uses.
# A built column is therefore NOT a supplied value: with nothing seeded, every
# one of these fields still gaps, now as `server_owned_value_not_supplied`.
_SERVER_OWNED_ROWS = (
    (1, "name", True, False),
    (7, "speed_walk", True, True),
    (2, "level", True, False),
    (3, "hp_current", True, False),
    (4, "hp_max", True, False),
    (5, "mp_current", True, False),
    (6, "mp_max", True, False),
    (13, "class_id", True, False),
    (16, "skill_points", True, False),
    (17, "unspent_points", True, False),
    (18, "stat_str", True, False),
    (19, "stat_con", True, False),
    (20, "stat_dex", True, False),
    (21, "stat_int", True, False),
    (22, "stat_per", True, False),
    (23, "experience", True, False),
    (24, "cash", True, False),
    (31, "bonus_str", True, False),
    (32, "bonus_con", True, False),
    (33, "bonus_dex", True, False),
    (34, "bonus_int", True, False),
    (35, "bonus_per", True, False),
)
SERVER_OWNED_FIELDS: dict[int, ServerOwnedField] = {
    row[0]: ServerOwnedField(*row) for row in _SERVER_OWNED_ROWS
}

# -- The seven with no source at all ----------------------------------------
# Measured, not asserted: no row in CODEX_TSV carries a `default_value` for
# ActorAttr at these offsets, and `FIELDS` marks all seven `known=False`.
UNSOURCED_FIELDS: frozenset[int] = frozenset({14, 25, 36, 41, 42, 43, 54})

# -- Construction defaults adjudicated safe to RE-SEND on a live character ---
# Empty on purpose.  See the module docstring, "RESEND ADJUDICATION".
RESEND_ADJUDICATED: frozenset[int] = frozenset()

REASON_NO_TYPED_VALUE = "server_owned_value_not_supplied"
REASON_NO_COLUMN = "server_owned_column_not_built"
REASON_UNSOURCED = "no_proven_source"
REASON_SENSITIVE = "refused_sensitive"
REASON_RESEND_UNADJUDICATED = "client_default_not_adjudicated_for_resend"


def source_of(x: int) -> str:
    """Which of the four sources owns field ``x``.  Total over ``FIELDS``."""
    if x not in BY_X:
        raise AttrComposeError(f"unknown field x={x!r} (valid: 1..{len(FIELDS)})")
    if x in SENSITIVE_FIELDS:
        return REFUSED
    if x in SERVER_OWNED_FIELDS:
        return SERVER_OWNED
    if x in UNSOURCED_FIELDS:
        return UNSOURCED
    if x in CLIENT_CONSTRUCTION_DEFAULTS:
        return CLIENT_DEFAULT
    raise AttrComposeError(  # pragma: no cover - _verify_partition forbids it
        f"field x={x} has no source class; the partition is broken"
    )


def _verify_partition() -> None:
    """Every row of ``FIELDS`` has exactly one source.  Import-time, because a
    later round adding a row to ``gm/attr_wire.FIELDS`` (that lane's file, not
    this one) must not be able to slip a source-less field past this gate."""
    seen: dict[int, str] = {}
    for field in FIELDS:
        seen[field[0]] = source_of(field[0])
    if len(seen) != len(FIELDS):
        raise AttrComposeError("FIELDS has duplicate x values")
    overlap = set(SERVER_OWNED_FIELDS) & UNSOURCED_FIELDS
    if overlap:
        raise AttrComposeError(f"a field cannot be both owned and unsourced: {overlap}")
    clash = set(CLIENT_CONSTRUCTION_DEFAULTS) & UNSOURCED_FIELDS
    if clash:
        raise AttrComposeError(
            f"a field cannot have a proven default and be unsourced: {clash}"
        )
    unknown = (
        set(UNSOURCED_FIELDS) | set(SERVER_OWNED_FIELDS)
        | set(CLIENT_CONSTRUCTION_DEFAULTS)
    ) - set(BY_X)
    if unknown:
        raise AttrComposeError(f"source table names fields not in FIELDS: {unknown}")
    for x, default in CLIENT_CONSTRUCTION_DEFAULTS.items():
        if default.x != x:
            raise AttrComposeError(f"default table key {x} disagrees with row {default.x}")
    for x, owned in SERVER_OWNED_FIELDS.items():
        if owned.x != x:
            raise AttrComposeError(f"owned table key {x} disagrees with row {owned.x}")


_verify_partition()


def block_gaps(typed_values: dict[int, object]) -> tuple[BlockGap, ...]:
    """Every reason a full block cannot be composed from ``typed_values``.

    Returns them ALL, ordered by ``x`` -- a caller that fixes one gap should
    see the next one immediately rather than one per round.  An empty tuple
    means ``compose_full_block`` would succeed.
    """
    gaps: list[BlockGap] = []
    for field in FIELDS:
        x, name = field[0], field[6]
        source = source_of(x)
        if source == REFUSED:
            gaps.append(BlockGap(
                x, name, REASON_SENSITIVE,
                "gm/attr_wire.SENSITIVE_FIELDS: never composed, in any direction",
            ))
        elif source == UNSOURCED:
            gaps.append(BlockGap(
                x, name, REASON_UNSOURCED,
                f"no default_value row for this offset in {CODEX_TSV}; "
                "closing it is an RE question routed through chief",
            ))
        elif source == SERVER_OWNED:
            owned = SERVER_OWNED_FIELDS[x]
            if x in typed_values:
                continue
            if owned.column_exists:
                gaps.append(BlockGap(
                    x, name, REASON_NO_TYPED_VALUE,
                    f"characters.{owned.column} exists but the caller supplied "
                    "no value; this module never substitutes one",
                ))
            else:
                gaps.append(BlockGap(
                    x, name, REASON_NO_COLUMN,
                    f"no characters.{owned.column} column in migrations/ yet",
                ))
        elif x not in RESEND_ADJUDICATED:
            default = CLIENT_CONSTRUCTION_DEFAULTS[x]
            gaps.append(BlockGap(
                x, name, REASON_RESEND_UNADJUDICATED,
                f"construction default {default.value!r} proven at "
                f"{default.writer_va} ({default.semantic_name}), but nothing "
                "proves the client has not changed it since construction",
            ))
    return tuple(gaps)


def _value_for(x: int, typed_values: dict[int, object]) -> object:
    """The ONE place a value is produced.  Every source class it cannot honour
    raises here rather than returning something.

    ``compose_full_block`` cannot return today (x=30 gaps unconditionally), so
    testing the guarantee only through it would be vacuous -- and the single
    most plausible future edit, "just leave a refused field out of the block",
    would otherwise walk straight past ``block_gaps`` into an emit site with no
    opinion of its own.  This function is that opinion, and it is tested
    directly, field by field.
    """
    source = source_of(x)
    if source == REFUSED:
        raise AttrComposeError(
            f"field x={x} ({BY_X[x][6]}) is in gm/attr_wire.SENSITIVE_FIELDS: "
            "no value is ever produced for it, not even its proven "
            "construction default"
        )
    if source == UNSOURCED:
        raise AttrComposeError(
            f"field x={x} ({BY_X[x][6]}) has no proven source; refusing to "
            "invent one"
        )
    if source == SERVER_OWNED:
        if x not in typed_values:
            raise AttrComposeError(
                f"field x={x} ({BY_X[x][6]}) is server-owned and no value was "
                f"supplied (column characters.{SERVER_OWNED_FIELDS[x].column})"
            )
        return typed_values[x]
    if x not in RESEND_ADJUDICATED:
        raise AttrComposeError(
            f"field x={x} ({BY_X[x][6]}) has a proven construction default but "
            "is not adjudicated safe to re-send on a live character"
        )
    return CLIENT_CONSTRUCTION_DEFAULTS[x].value


def compose_full_block(typed_values: dict[int, object]) -> dict[int, object]:
    """``{x: value}`` for all 55 fields, or ``AttrComposeError`` naming why not.

    ``typed_values`` are the caller's server-owned values (from typed columns).
    Values for fields this module does not consider server-owned are REFUSED
    outright rather than passed through: a caller cannot smuggle a value for a
    sensitive or unsourced field past the gate by putting it in this dict.
    """
    stray = {x for x in typed_values if x not in SERVER_OWNED_FIELDS}
    if stray:
        raise AttrComposeError(
            "typed values may only be supplied for server-owned fields; "
            f"refused for x={sorted(stray)} "
            f"(sources: {sorted((x, source_of(x)) for x in stray)})"
        )
    gaps = block_gaps(typed_values)
    if gaps:
        listed = ", ".join(f"x={g.x}({g.field_name}):{g.reason}" for g in gaps)
        raise AttrComposeError(
            f"cannot compose a full attribute block: {len(gaps)} field(s) have "
            f"no honest value -- {listed}"
        )
    return {field[0]: _value_for(field[0], typed_values) for field in FIELDS}


def unlock_report() -> dict[str, object]:
    """What is left before a full block can be composed at all, countable.

    Written for the round file and for the letter to COO: the point of this
    module is that the remaining work is a list with a length, not a mood.
    """
    gaps = block_gaps({})
    by_reason: dict[str, list[int]] = {}
    for gap in gaps:
        # written the long way on purpose: this module is checked by AST for
        # any defaulting lookup, and a grouping `setdefault` reads identically
        # to the one edit that would reintroduce a guessed value
        if gap.reason not in by_reason:
            by_reason[gap.reason] = []
        by_reason[gap.reason].append(gap.x)
    return {
        "total_fields": len(FIELDS),
        "blocked_fields": len(gaps),
        "by_reason": {reason: sorted(xs) for reason, xs in sorted(by_reason.items())},
        "server_owned_columns_built": sorted(
            x for x, owned in SERVER_OWNED_FIELDS.items() if owned.column_exists
        ),
    }
