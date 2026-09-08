"""LANE-B: which side of zero a monster's 64-bit identity has to be on.

WHAT THIS IS AND WHERE THE NUMBERS COME FROM.  ``GT-288`` set 3 (the ALL
sweep) was booted on the owner's machine on 2026-09-08 between 12:39 and
13:05 +07:00 and PASSED; ka1-A's result letter is
``pf_bridge/notes_to_chief/20260908_1315_KA1A-R324A-RESULTS-GT288-set3-ALL-
PASS-colour-is-identity-sign-enemy-offensive.md``.  Twenty-four name boards
were composed in one boot and the owner read them off the screen one label
at a time.  This module is the LAW those twenty-four rows establish, written
as code that refuses rather than as prose that can go stale, plus the
allocator ``BUILD_PROPOSED: identity allocator | LANE-B`` in that same letter
asks this lane for.

THE ONE MEASURED SENTENCE, IN THE ORDER THE CLIENT DECIDES:

    1. identity > 0   -> the PLAYER formula.  Green when the actor's faction
       is not in the viewer's enemy set, pink when it is.  NOTHING ELSE
       REACHES THE COLOUR: level, HP (including current HP 0), speed,
       template id, visual preset, ``n_ENEMY`` at 0/1/2/6/12/0xFFFFFFFF, and
       a linked identity were each varied one at a time on a positive
       identity and every one of them stayed green or pink.
    2. identity < 0   -> the NPC/MONSTER formula.  Faction relation decides
       first: not an enemy -> YELLOW; an enemy -> orange or red.
    3. within the enemy half, ``n_OFFESIVE`` picks the shade: 1 -> RED,
       0 -> ORANGE.  The two rows that split here (``M-IDNEG`` template 916
       and ``M-IDNEG-T31`` template 31) differ in ONE field.
    4. identity == 0  -> the client DOES NOT DRAW THE ACTOR AT ALL.  The
       owner counted 23 boards of the 24 composed and named the missing one:
       ``N-ID0``.

WHY 0 IS A PRODUCTION HAZARD AND NOT A CURIOSITY.  An actor at identity 0
still exists on the server: the roster carries it, the combat ledger opens
on it, and the server will accept a strike against it.  No client has ever
been sent a drawable copy of it.  That is a defect that reads green from
either side alone -- the census says it shipped, the screen never had it --
which is why :func:`refuse_undrawable_identity` is a refusal on the
composition path rather than a report.

WHAT THIS MODULE DOES NOT CLAIM.
  * It does not claim any monster on ``main`` today carries a non-positive
    identity.  Every ``FieldMob`` still derives ``0x2000 + placement_index +
    1`` (``field_mobs`` line ~369), which is strictly positive, so every
    field monster a player meets today is drawn by rule 1 and is pink.
    Moving them is a census-identity-space change that this lane cannot make
    alone; the ask is written up in this round's build letter.
  * It does not claim the shade selector IS ``n_OFFESIVE`` rather than the
    template id.  Those two rows differ in one field and ``n_OFFESIVE`` is
    derived FROM the template, so a single boot cannot separate them.  The
    letter's own reading is recorded in :data:`R324A_ROWS` as what was seen
    (the colour) and not as what caused it; :func:`expected_name_colour`
    takes ``offensive`` as an argument for that reason -- a caller that
    disagrees about how ``n_OFFESIVE`` is derived still gets the measured
    mapping.
  * Nobody clicked, attacked or Tab-targeted any of the twenty-four actors
    (the ticket forbade it), so nothing here says a yellow/orange/red actor
    can be fought, or that the colour survives aggro.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "MobIdentitySignError",
    "IDENTITY_NOT_DRAWN",
    "NAME_COLOUR_GREEN",
    "NAME_COLOUR_PINK",
    "NAME_COLOUR_YELLOW",
    "NAME_COLOUR_ORANGE",
    "NAME_COLOUR_RED",
    "NAME_COLOUR_NOT_DRAWN",
    "R324A_ROWS",
    "SCENE_STRIDE",
    "is_player_identity",
    "is_mob_identity",
    "identity_is_drawn",
    "refuse_undrawable_identity",
    "mob_wire_identity",
    "scene_and_placement_for",
    "expected_name_colour",
    "encode_wire_identity",
]


class MobIdentitySignError(ValueError):
    """Raised when an identity cannot carry the colour it is asked to."""


#: The one value the client refuses to draw (R324A row 8, ``N-ID0``).
IDENTITY_NOT_DRAWN = 0

NAME_COLOUR_GREEN = "green"
NAME_COLOUR_PINK = "pink"
NAME_COLOUR_YELLOW = "yellow"
NAME_COLOUR_ORANGE = "orange"
NAME_COLOUR_RED = "red"

#: Not a colour: the actor never reached the screen.
NAME_COLOUR_NOT_DRAWN = "not-drawn"

#: The twenty-four boards of R324A, as the owner read them, in the order the
#: sweep composed them.  Each row is
#: ``(label, identity_sign, faction_is_enemy, offensive, colour_seen)`` where
#: ``identity_sign`` is -1, 0 or 1 and ``offensive`` is ``None`` wherever the
#: row does not sit in the enemy half of the non-positive formula (so no row
#: claims a shade selector was exercised when it was not).  This table is the
#: SCREEN, and :func:`expected_name_colour` is checked against it rather than
#: against itself -- see ``tests/test_mob_identity_sign.py``.
R324A_ROWS: tuple[tuple[str, int, bool, "bool | None", str], ...] = (
    ("N-BASE", 1, False, None, NAME_COLOUR_GREEN),
    ("M-BASE", 1, True, None, NAME_COLOUR_PINK),
    ("N-LVL", 1, False, None, NAME_COLOUR_GREEN),
    ("N-HP", 1, False, None, NAME_COLOUR_GREEN),
    ("N-SPD", 1, False, None, NAME_COLOUR_GREEN),
    ("N-TPL", 1, False, None, NAME_COLOUR_GREEN),
    ("N-PRE", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ID0", 0, False, None, NAME_COLOUR_NOT_DRAWN),
    ("N-IDNEG", -1, False, None, NAME_COLOUR_YELLOW),
    ("M-IDNEG", -1, True, True, NAME_COLOUR_RED),
    ("M-IDNEG-T31", -1, True, False, NAME_COLOUR_ORANGE),
    ("N-IDNEG-T916", -1, False, None, NAME_COLOUR_YELLOW),
    ("N-LNKP", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENM0", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENM1", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENM2", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENM6", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENM12", 1, False, None, NAME_COLOUR_GREEN),
    ("N-ENMFF", 1, False, None, NAME_COLOUR_GREEN),
    ("M-ENM1", 1, True, None, NAME_COLOUR_PINK),
    ("N-HP0", 1, False, None, NAME_COLOUR_GREEN),
    ("N-IDNEG-LNKP", -1, False, None, NAME_COLOUR_YELLOW),
    ("N-IDNEG-ENM1", -1, False, None, NAME_COLOUR_YELLOW),
    ("M-T001", 1, True, None, NAME_COLOUR_PINK),
)

#: How many placement slots one scene owns inside the monster band.  The
#: widest roster this lane has ever mined is Bg0010 at 72 rows (round
#: ``np8mhf``, 439 rows over eleven scenes), so 4096 is three doublings of
#: headroom and still lets every scene id in ``SCENE_NAME`` (271 rows, ids
#: below 2048) have its own block without coming anywhere near the 64-bit
#: floor.  Named rather than inlined because the inverse depends on it.
SCENE_STRIDE = 0x1000

#: The most negative identity this allocator will ever hand out, kept a full
#: order of magnitude away from ``-2**63`` so a caller that adds an offset of
#: its own cannot wrap the sign bit back to positive.
MOB_IDENTITY_FLOOR = -(2**62)


def is_player_identity(identity: int) -> bool:
    """True when ``identity`` takes the player colour formula (rule 1)."""
    _refuse_non_integer(identity)
    return identity > 0


def is_mob_identity(identity: int) -> bool:
    """True when ``identity`` takes the NPC/monster colour formula (rule 2)."""
    _refuse_non_integer(identity)
    return identity < 0


def identity_is_drawn(identity: int) -> bool:
    """True unless the client throws the actor away before drawing it."""
    _refuse_non_integer(identity)
    return identity != IDENTITY_NOT_DRAWN


def refuse_undrawable_identity(identity: int, *, what: str = "actor") -> int:
    """Refuse an identity the client will never put on screen.

    Called from the production hostile-body composer, so a monster that no
    player could ever see cannot be handed to a census and then opened in the
    combat ledger.  Returns ``identity`` so it can be used inline.
    """
    _refuse_non_integer(identity)
    if identity == IDENTITY_NOT_DRAWN:
        raise MobIdentitySignError(
            f"{what} identity 0 is never drawn by the client (R324A row 8, "
            "N-ID0: 23 of 24 boards reached the screen and this was the one "
            "that did not) -- a server-side actor nobody can see still "
            "accepts strikes, so the composition is refused here"
        )
    if identity < MOB_IDENTITY_FLOOR:
        raise MobIdentitySignError(
            f"{what} identity {identity} is below the monster-band floor "
            f"{MOB_IDENTITY_FLOOR}"
        )
    return identity


def mob_wire_identity(scene_id: int, placement_index: int) -> int:
    """The monster-band identity for one placement in one scene.

    Non-positive by construction (rule 2), never 0 (rule 4), and carrying a
    SCENE COMPONENT -- which is the half ``FieldMob.actor_identity`` is
    documented as missing (``field_mobs`` line ~1013: "``0x2000 +
    placement_index + 1`` with no scene component, so two scenes' placements
    collide").  Two different scenes cannot produce the same value here.
    """
    _refuse_non_integer(scene_id, "scene id")
    _refuse_non_integer(placement_index, "placement index")
    if scene_id < 0:
        raise MobIdentitySignError(f"scene id {scene_id} is not a scene id")
    if placement_index < 0:
        raise MobIdentitySignError(
            f"placement index {placement_index} is not a placement index"
        )
    if placement_index >= SCENE_STRIDE:
        raise MobIdentitySignError(
            f"placement index {placement_index} does not fit scene stride "
            f"{SCENE_STRIDE} -- widen SCENE_STRIDE in one commit with the "
            "inverse rather than letting one scene's block run into the next"
        )
    identity = -(1 + scene_id * SCENE_STRIDE + placement_index)
    if identity < MOB_IDENTITY_FLOOR:
        raise MobIdentitySignError(
            f"scene {scene_id} placement {placement_index} lands at "
            f"{identity}, below the monster-band floor {MOB_IDENTITY_FLOOR}"
        )
    return identity


def scene_and_placement_for(identity: int) -> tuple[int, int]:
    """The inverse of :func:`mob_wire_identity`.

    Refuses anything the allocator could not have produced, so a positive
    identity (a player, or a monster still on the legacy ``0x2000`` formula)
    cannot be silently read as a scene/placement pair.
    """
    _refuse_non_integer(identity)
    if identity >= 0:
        raise MobIdentitySignError(
            f"identity {identity} is not in the monster band (the band is "
            "strictly negative)"
        )
    if identity < MOB_IDENTITY_FLOOR:
        raise MobIdentitySignError(
            f"identity {identity} is below the monster-band floor "
            f"{MOB_IDENTITY_FLOOR}"
        )
    flat = -identity - 1
    return flat // SCENE_STRIDE, flat % SCENE_STRIDE


def expected_name_colour(
    identity: int,
    *,
    faction_is_enemy: bool,
    offensive: "bool | None" = None,
) -> str:
    """The colour R324A measured for this combination, on screen.

    ``offensive`` is only read on the one branch the sweep exercised it on
    (non-positive identity AND an enemy faction); it is REQUIRED there,
    because guessing a shade is exactly the thing the two-row split was
    booted to settle.
    """
    _refuse_non_integer(identity)
    if type(faction_is_enemy) is not bool:
        raise MobIdentitySignError("faction_is_enemy must be a bool")
    if identity == IDENTITY_NOT_DRAWN:
        return NAME_COLOUR_NOT_DRAWN
    if identity > 0:
        return NAME_COLOUR_PINK if faction_is_enemy else NAME_COLOUR_GREEN
    if not faction_is_enemy:
        return NAME_COLOUR_YELLOW
    if type(offensive) is not bool:
        raise MobIdentitySignError(
            "an enemy actor in the monster band needs offensive= as a bool: "
            "R324A separated red from orange on that field alone and this "
            "function will not guess which shade a caller meant"
        )
    return NAME_COLOUR_RED if offensive else NAME_COLOUR_ORANGE


def encode_wire_identity(identity: int) -> bytes:
    """The eight little-endian bytes ``v141.qwordtag`` would put on the wire.

    Measured, not assumed: ``current/pf_login_game_server_v141.py`` line 1131
    packs ``v & 0xFFFFFFFFFFFFFFFF``, so a negative identity leaves as its
    two's complement rather than raising -- which is why the monster band can
    be expressed as a plain negative Python int all the way down to the
    frozen encoder.  Reproduced here so a caller can pin the bytes without
    importing the frozen file.
    """
    _refuse_non_integer(identity)
    if identity >= 2**63 or identity < -(2**63):
        raise MobIdentitySignError(
            f"identity {identity} does not fit a signed 64-bit field"
        )
    return (identity & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little")


def _refuse_non_integer(value: Any, what: str = "identity") -> None:
    # `type(...) is not int` on purpose: bool subclasses int, and True as an
    # identity is the kind of thing that reads as 1 and draws a player.
    if type(value) is not int:
        raise MobIdentitySignError(f"{what} must be an int, got {value!r}")
