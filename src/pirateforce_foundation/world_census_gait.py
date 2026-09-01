"""LANE-A: the walk-speed field that gates the client's quest-icon board.

WHY THIS MODULE EXISTS.  No NPC this server ships has ever had a quest mark
over its head, and the reason measured here is not that the quest state is
wrong: it is that the client never even asks.  Every one of the ten rows of
``PF_ATTR_QUEST_MARK_SELECTOR.tsv`` (Codex checkpoint P0-3, mirrored at
``pf_bridge/notes_to_chief/reference_codex_attr/``) carries the SAME
``skip_conditions`` string, and its first clause is:

    "CNetNPC setter skips the board call when +0x70 mask 0x40 is clear,
     board +0x360 is null, or cached selector +0x364 is unchanged"

``+0x70`` is not a mystery offset.  ``PF_ATTR_FIELD_SEMANTICS.tsv`` has
exactly one field at ``+0x70`` in the whole BasicAttr family:
``BasicAttr@0x70``, ``semantic_name=field_presence_mask``,
``semantic_status=PROVEN_EXACT``, ``gate=ALWAYS`` -- the u16 mask
``make_npc_attr`` writes under tag ``0x12``.  Mask bit ``0x0040`` in that
same file is ``BasicAttr@0x54``, ``applies_to_class=CNetNPC``,
``semantic_name=MOBS.n_SPEED_WALK_to_initial_visual_horizontal_locomotion_scalar``,
``PROVEN_EXACT``, tag ``0x2A``, len 4.  So the clause reads: an actor whose
BasicAttr mask has no walk-speed bit never reaches the quest-icon board at
all.  Ordinary census bodies have never set that bit (``make_npc_attr``
sets it only when its ``movement_speed`` parameter is not ``None``, and the
thirteen census composers all left it ``None``), so for every townsperson
the owner has ever walked past, the selector in the letter above was never
even evaluated.

[LANE-A ASSUMPTION - AWAITING COO CONFIRMATION]  The reading above -- that
the ``+0x70`` in the selector rows' skip clause is BasicAttr's own
field-presence mask, and not some unrelated ``CNetNPC+0x70`` -- is this
lane's, taken because it is the only ``+0x70`` any Codex artifact resolves
and because the same artifacts write BasicAttr gates in exactly that
``+0x70 & 0x00NN`` notation.  See
``notes_to_chief/20260902_0437_LANE-A-ASK-COO-quest-board-gate-plus-0x70.md``.
Nothing in this module depends on the reading being right: the value it
sends is the shipped ``MOBS.n_SPEED_WALK`` for the row the actor already
is, which the hostile encoder has sent for months, so a wrong reading costs
a wrong REASON in the round file, not a wrong byte on the wire.

WHAT IS NOT CLAIMED.  That a mark will appear.  Opening a gate is not
drawing a texture: the selector still needs the actor's ``s_QUEST_BEGIN`` /
``s_QUEST_END`` candidates to survive ``Accept_Check`` / ``Report_Check``,
the board at ``+0x360`` must be non-null, and the whole selector table is
``source=IMAGE`` with no client-observable row behind it -- Codex's own
nonclaim.  ``GT-202`` is what decides.  What IS claimed, and is testable
here, is that the bit and the float leave this server, which is the one
input on the skip clause that this side owns.

WHY ``QuestAttr`` IS NOT WHAT THIS ROUND SENDS.  The assignment letter
(``20260902_0205_CHIEF-TO-LANE-A-...``) names sending ``QuestAttr`` as the
work.  Read against the selector rows, sending it is not the FIRST thing:
``QuestAttr`` lookup ``0`` and a MISSING entry are the same branch (Codex:
"QuestAttr lookup 0 includes both missing entry and stored zero"), so a
``QuestAttr`` that carries 0 -- the only value this server could honestly
send today, having no accepted-quest state anywhere -- is byte-for-byte
equivalent in effect to sending nothing.  The gate is not.  This module
therefore does the half that changes something, and the ``QuestAttr``
composer stays open with its reason written down rather than shipped as a
no-op that would look like progress.

WHERE THE VALUE COMES FROM.  ``CONSTDATA_TH__MOBS.n_SPEED_WALK``, the same
shipped column ``field_mob_tables`` mines for hostile mobs and the same one
``scene2_prison_exile_tables`` already carries per placement.  It is keyed
here by ``MOBS.n_ID`` rather than added as a column to each scene's identity
table for two measured reasons: the value is a property of the MOBS row and
not of the placement (scene 2's independently mined per-placement column
agrees with the shipped table on all 40 of its ids, checked in this module's
tests), and every one of those identity tables builds its rows with
``SceneIdentity(*row)``, whose own comment warns that a field inserted in the
middle silently re-maps every row instead of failing.

WHAT THIS MODULE DELIBERATELY DOES NOT TOUCH.  Name colour, faction, actor
type, identity sign (``P0-2`` is not closed and Codex has colour at
``NOT_READY_FOR_POLICY_CHANGE``), and the level splice, which stays exactly
where ``world_census_level`` put it -- walk speed is bit ``0x0040`` and
lands after the HP pair, level is bit ``0x0002`` and lands before it, so the
two never contend for a position.
"""
from __future__ import annotations

from typing import Any

from . import world_census_level

# BasicAttr mask bit and wire shape of the field, from
# ``PF_ATTR_FIELD_SEMANTICS.tsv`` (BasicAttr@0x54, CNetNPC, PROVEN_EXACT) and
# from the frozen writer's own V73 note in ``make_npc_attr``: "BasicAttr bit
# 0x0040 serializes float +0x54 (0x46579A).  Setter 0x464960 writes +0x54.
# CNetNPC template init 0x45C103 reads MOBS+0x3C (decoded n_SPEED_WALK) and
# feeds it to that setter."
BASIC_BIT_WALK_SPEED = 0x0040
WALK_SPEED_TAG = 0x2A
WALK_SPEED_WIDTH = 4

# The clause this round is about, quoted from every row of
# PF_ATTR_QUEST_MARK_SELECTOR.tsv so a future reader does not have to trust
# a summary of it.
QUEST_BOARD_SKIP_CLAUSE = (
    "CNetNPC setter skips the board call when +0x70 mask 0x40 is clear, "
    "board +0x360 is null, or cached selector +0x364 is unchanged"
)

# The mined domain.  Every value below is a shipped CONSTDATA_TH__MOBS
# n_SPEED_WALK; 0 occurs and is kept (it is what the table says for a
# handful of rows, and inventing a floor for them would be exactly the kind
# of made-up number this lane refuses to put on the wire).  The observed
# ceiling across the ids this census ships is 500.
WALK_SPEED_MIN = 0
WALK_SPEED_MAX = 500
# What the field could carry: it is a float on the wire, so the ceiling
# above is the mined domain and not the field width.  Kept as a named fact
# so the ceiling reads as a decision rather than as a limit of the format.
WALK_SPEED_FIELD_IS_F32 = True


class CensusGaitError(ValueError):
    """A census actor has no mined walk speed, or the value is not one."""


# MOBS.n_ID -> MOBS.n_SPEED_WALK, for every n_ID any of the thirteen census
# sources ships.  Transcribed from the shipped CONSTDATA_TH__MOBS table (the
# game data lives in pf_bridge, not in this repo, which is why every mined
# table in this package is a literal).  563 ids: the union of the twelve
# identity modules' resolved rows and scene 2's known placements.
WALK_SPEED_BY_MOBS_N_ID = {
    1: 150, 2: 150, 3: 150, 4: 150, 5: 150, 6: 150, 7: 150, 8: 150,
    9: 150, 10: 150, 11: 150, 12: 150, 13: 150, 14: 150, 15: 150, 16: 150,
    17: 150, 18: 150, 19: 150, 20: 150, 21: 150, 22: 150, 23: 150, 24: 150,
    25: 150, 26: 150, 27: 100, 28: 100, 29: 100, 30: 100, 31: 100, 32: 100,
    33: 100, 34: 100, 35: 100, 36: 150, 38: 150, 39: 150, 40: 150, 41: 150,
    42: 150, 43: 150, 44: 150, 45: 150, 46: 150, 47: 150, 48: 150, 49: 150,
    50: 150, 51: 150, 52: 150, 53: 150, 54: 150, 55: 100, 56: 100, 57: 100,
    58: 100, 59: 100, 60: 100, 61: 100, 62: 100, 63: 100, 64: 100, 65: 100,
    67: 150, 68: 100, 69: 150, 70: 100, 71: 150, 72: 150, 73: 150, 74: 150,
    75: 150, 76: 150, 77: 150, 78: 150, 79: 150, 80: 150, 81: 150, 82: 150,
    83: 150, 84: 150, 85: 150, 86: 150, 87: 150, 88: 150, 89: 150, 90: 150,
    91: 150, 92: 150, 93: 100, 94: 100, 95: 100, 96: 100, 97: 100, 98: 100,
    99: 100, 100: 100, 101: 100, 102: 100, 103: 100, 105: 150, 106: 150, 107: 150,
    108: 150, 109: 150, 110: 150, 111: 150, 112: 150, 113: 150, 114: 150, 115: 150,
    116: 150, 117: 150, 118: 150, 119: 150, 120: 150, 121: 150, 122: 150, 123: 150,
    124: 150, 125: 150, 126: 150, 127: 150, 128: 150, 129: 150, 130: 500, 131: 150,
    132: 150, 133: 150, 134: 150, 135: 150, 136: 150, 137: 150, 138: 100, 139: 100,
    140: 100, 141: 100, 142: 100, 143: 100, 144: 100, 145: 100, 146: 100, 147: 100,
    148: 100, 149: 100, 150: 100, 151: 150, 152: 150, 153: 150, 154: 150, 156: 150,
    157: 0, 158: 100, 159: 150, 160: 150, 161: 150, 162: 150, 163: 150, 164: 150,
    165: 150, 166: 100, 167: 150, 168: 150, 169: 150, 170: 150, 171: 150, 172: 150,
    173: 150, 174: 150, 175: 150, 176: 150, 177: 150, 178: 150, 179: 110, 180: 100,
    181: 150, 182: 150, 183: 150, 194: 100, 196: 150, 197: 150, 198: 150, 199: 150,
    200: 150, 201: 150, 202: 150, 203: 150, 204: 150, 205: 150, 206: 150, 207: 150,
    208: 150, 209: 150, 210: 150, 211: 150, 212: 150, 213: 150, 214: 150, 215: 150,
    216: 150, 217: 150, 218: 150, 219: 100, 220: 100, 221: 100, 222: 100, 223: 100,
    224: 100, 225: 100, 226: 100, 227: 100, 228: 100, 229: 100, 232: 150, 233: 150,
    234: 150, 235: 150, 236: 150, 237: 150, 238: 150, 239: 150, 240: 150, 241: 150,
    242: 150, 243: 150, 244: 150, 245: 150, 246: 100, 247: 150, 248: 150, 250: 150,
    251: 150, 252: 150, 253: 150, 254: 150, 255: 150, 256: 150, 257: 150, 258: 150,
    259: 150, 260: 150, 261: 150, 262: 150, 263: 150, 264: 150, 265: 150, 266: 150,
    267: 150, 268: 150, 269: 150, 270: 150, 271: 150, 272: 150, 273: 150, 274: 150,
    275: 150, 276: 150, 277: 150, 278: 150, 279: 150, 280: 150, 281: 150, 282: 150,
    283: 150, 285: 150, 286: 150, 287: 150, 288: 150, 289: 150, 290: 150, 291: 150,
    292: 150, 293: 150, 294: 150, 295: 150, 296: 150, 297: 150, 298: 150, 299: 150,
    300: 150, 301: 150, 302: 150, 303: 150, 304: 150, 305: 150, 306: 150, 307: 100,
    308: 100, 309: 100, 310: 100, 311: 100, 312: 100, 313: 100, 314: 100, 315: 100,
    316: 100, 317: 100, 318: 100, 319: 100, 320: 100, 322: 150, 323: 150, 324: 150,
    325: 150, 326: 150, 327: 150, 328: 150, 329: 150, 330: 150, 331: 150, 332: 150,
    333: 150, 334: 150, 335: 150, 336: 150, 337: 150, 338: 150, 339: 150, 340: 100,
    341: 100, 342: 100, 343: 100, 344: 100, 345: 100, 346: 100, 347: 100, 348: 100,
    349: 100, 350: 100, 351: 100, 352: 100, 353: 100, 354: 100, 355: 100, 356: 65,
    357: 65, 358: 150, 359: 150, 360: 400, 362: 150, 363: 150, 364: 150, 365: 150,
    366: 150, 367: 150, 368: 150, 369: 150, 370: 150, 371: 150, 372: 150, 373: 150,
    374: 150, 375: 150, 376: 150, 377: 150, 378: 150, 379: 150, 380: 150, 381: 150,
    382: 150, 383: 150, 384: 150, 385: 150, 386: 150, 387: 150, 388: 150, 389: 150,
    390: 150, 391: 150, 392: 150, 393: 150, 394: 150, 395: 150, 396: 150, 397: 150,
    465: 150, 515: 100, 519: 100, 523: 100, 525: 100, 526: 100, 527: 100, 528: 150,
    529: 150, 536: 100, 544: 100, 546: 440, 549: 100, 622: 150, 623: 150, 624: 150,
    625: 150, 626: 150, 627: 150, 631: 150, 632: 150, 633: 150, 634: 80, 635: 150,
    636: 100, 637: 0, 638: 150, 639: 150, 640: 150, 641: 150, 643: 150, 644: 150,
    645: 150, 646: 150, 647: 150, 648: 150, 649: 150, 650: 150, 651: 150, 652: 150,
    653: 150, 654: 150, 655: 150, 656: 150, 657: 100, 658: 100, 659: 100, 660: 100,
    661: 100, 662: 100, 663: 100, 664: 100, 665: 100, 666: 100, 667: 100, 668: 100,
    669: 100, 670: 100, 671: 100, 672: 100, 673: 100, 674: 100, 675: 150, 676: 150,
    677: 150, 678: 150, 679: 150, 680: 150, 681: 150, 682: 150, 683: 150, 684: 150,
    685: 150, 686: 150, 687: 150, 688: 100, 689: 100, 690: 100, 691: 100, 692: 100,
    693: 100, 694: 100, 695: 100, 696: 100, 697: 100, 717: 150, 718: 150, 719: 150,
    720: 150, 721: 150, 722: 150, 740: 150, 741: 150, 744: 150, 745: 150, 746: 150,
    747: 150, 748: 150, 750: 150, 753: 150, 757: 150, 767: 150, 796: 150, 797: 150,
    798: 150, 799: 150, 800: 150, 801: 150, 802: 150, 803: 150, 804: 150, 805: 150,
    815: 150, 816: 150, 817: 150, 818: 150, 820: 150, 821: 150, 822: 150, 824: 150,
    825: 150, 826: 150, 827: 150, 828: 100, 833: 150, 834: 150, 835: 440, 836: 150,
    837: 150, 838: 150, 839: 150, 841: 150, 854: 150, 855: 100, 871: 150, 882: 400,
    883: 0, 884: 0, 885: 0, 886: 0, 887: 0, 888: 0, 889: 0, 890: 0,
    891: 0, 892: 0, 893: 0, 894: 100, 895: 100, 896: 100, 897: 0, 898: 100,
    899: 0, 900: 100, 902: 0, 903: 100, 904: 150, 905: 150, 906: 0, 907: 100,
    908: 100, 909: 150, 910: 100, 911: 100, 913: 100, 915: 150, 916: 150, 917: 150,
    918: 0, 919: 100, 920: 100, 921: 150, 922: 150, 923: 0, 924: 150, 925: 150,
    926: 150, 927: 0, 928: 0, 929: 0, 930: 0, 933: 0, 934: 100, 7042: 150,
    7043: 150, 7044: 150, 7045: 150,
}


# Kept empty ON PURPOSE, and asserted empty by this module's tests: a census
# source that ships an actor whose MOBS row has no mined walk speed would
# belong here with its reason, the way ``world_census_level`` records the
# sources it cannot serve.  All thirteen resolve today.
CENSUS_SOURCES_WITHOUT_A_MINED_WALK_SPEED: tuple[str, ...] = ()


def walk_speed_for(mobs_n_id: int) -> int:
    """The shipped ``MOBS.n_SPEED_WALK`` for this row.

    Refuses rather than defaulting.  A census actor whose id is not in the
    mined table is an actor this lane has not measured, and a guessed gait
    would both move the actor wrongly and open the quest-icon gate on a
    claim nobody made.
    """
    if type(mobs_n_id) is not int:
        raise CensusGaitError(
            "MOBS n_ID must be a plain int, not %r" % (mobs_n_id,))
    try:
        return WALK_SPEED_BY_MOBS_N_ID[mobs_n_id]
    except KeyError:
        raise CensusGaitError(
            "MOBS n_ID %d has no mined n_SPEED_WALK in this table: a census "
            "source is shipping an actor this lane never mined" % mobs_n_id
        ) from None


def census_npc_attr(
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
    walk_speed: int | None = None,
) -> bytes:
    """One census actor's NPCAttr body, with its level AND its mined gait.

    The single call an ordinary scene composer's ``_entry`` makes.  It is a
    thin layer over ``world_census_level.leveled_npc_attr`` rather than a
    second serializer for the same reason that module gives: the frozen body
    stays the one source of the layout.

    ``walk_speed`` defaults to the mined value for ``template_n_id``.  Scene
    2 passes its own per-placement column explicitly -- it mined the same
    field independently, and the tests hold the two tables to each other
    rather than letting one quietly win.

    Keyword-only, for the same reason ``leveled_npc_attr`` is: the frozen
    helper's first positional parameter is the MOBS/template u16 at +0x78
    and takes the real ``MOBS.n_ID``, and a positional call site is exactly
    how ``GT-078`` put Mob-Set numbers on the owner's screen.
    """
    if walk_speed is None:
        walk_speed = walk_speed_for(template_n_id)
    elif type(walk_speed) is not int:
        raise CensusGaitError(
            "walk speed must be a plain int, not %r" % (walk_speed,))
    if not WALK_SPEED_MIN <= walk_speed <= WALK_SPEED_MAX:
        raise CensusGaitError(
            "walk speed %d is outside the mined domain %d..%d"
            % (walk_speed, WALK_SPEED_MIN, WALK_SPEED_MAX)
        )
    return world_census_level.leveled_npc_attr(
        legacy,
        template_n_id=template_n_id,
        actor_identity=actor_identity,
        scene_id=scene_id,
        scene_sequence=scene_sequence,
        visual_preset=visual_preset,
        current_hp=current_hp,
        max_hp=max_hp,
        basic_name=basic_name,
        level=level,
        movement_speed=float(walk_speed),
    )


def read_walk_speed(legacy: Any, body: bytes, actor_identity: int) -> float | None:
    """The walk speed a composed body actually carries, read off the bytes.

    The wire half of the two-layer evidence rule for this field: a test reads
    the float out of the bytes that would go to the client, not out of the
    table the composer read.  Returns ``None`` when the body sets no
    ``0x0040`` bit -- which is what every ordinary census entry answered
    before this module existed, and what the quest-icon skip clause is about.

    The walk speed sits after the current/max HP pair and before the scene
    id, so its position is walked field by field from the mask rather than
    written down: name (bit 0x0001), level (bit 0x0002, the splice
    ``world_census_level`` owns), then the HP pair (bits 0x0004/0x0008).
    """
    import struct

    if type(body) is not bytes:
        raise CensusGaitError("body must be bytes")
    mask_at = world_census_level.basic_mask_offset(legacy, body, actor_identity)
    mask = int.from_bytes(body[mask_at:mask_at + 2], "little")
    if not mask & BASIC_BIT_WALK_SPEED:
        return None
    at = mask_at + 2
    if mask & world_census_level.BASIC_BIT_NAME:
        empty = bytes(legacy.wstr_tag(""))
        header = len(empty)
        if body[at] != empty[0]:
            raise CensusGaitError(
                "name bit is set but the field at the name position is tag "
                "0x%02X, not the wstring tag 0x%02X" % (body[at], empty[0])
            )
        length = int.from_bytes(body[at + 1:at + header], "little")
        at += header + length
    if mask & world_census_level.BASIC_BIT_LEVEL:
        if body[at] != world_census_level.LEVEL_TAG:
            raise CensusGaitError(
                "level bit is set but the field at the level position is tag "
                "0x%02X, not 0x%02X"
                % (body[at], world_census_level.LEVEL_TAG)
            )
        at += 1 + world_census_level.LEVEL_WIDTH
    # Both HP bits or neither: the frozen writer emits the pair together.
    if not mask & world_census_level.BASIC_BIT_HP_CURRENT:
        raise CensusGaitError(
            "frozen make_npc_attr mask drift: 0x%04X sets the walk-speed bit "
            "but no HP bit, so the field order this reader walks is stale"
            % mask
        )
    at += 2 * (1 + 4)
    if body[at] != WALK_SPEED_TAG:
        raise CensusGaitError(
            "walk-speed bit is set but the field at the walk-speed position "
            "is tag 0x%02X, not 0x%02X" % (body[at], WALK_SPEED_TAG)
        )
    return struct.unpack(
        "<f", body[at + 1:at + 1 + WALK_SPEED_WIDTH])[0]


def quest_board_gate_is_open(legacy: Any, body: bytes, actor_identity: int) -> bool:
    """Whether this body clears the ONE half of the quest-board skip clause
    that this server controls.

    True means the BasicAttr mask carries bit ``0x0040``, so the CNetNPC
    setter's first skip condition does not fire for this actor.  It says
    nothing about the board pointer at ``+0x360``, the cached selector at
    ``+0x364``, the quest predicates, or whether any pixel is drawn: those
    are the client's, and ``GT-202`` is what looks at them.
    """
    return read_walk_speed(legacy, body, actor_identity) is not None
