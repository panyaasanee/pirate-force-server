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
    3. within the enemy half, SOMETHING picks the shade: the row whose table
       says ``n_OFFESIVE=1`` came back RED and the one that says 0 came back
       ORANGE.  READ RULE 3 AS A CORRELATION, NOT A CAUSE -- see the rival
       reading below, which this module refuses to paper over.
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
  * IT DOES NOT CLAIM ``n_OFFESIVE`` SELECTS THE SHADE, and the result
    letter's "the two rows differ in ONE field, template_id" is FALSE.
    pf-adversary (round ``gadxq5``) composed both bodies with the real
    ``field_mobs.hostile_npc_attr`` and diffed the wire bytes: they differ in
    SIX semantic fields -- identity, name, level (100 vs 27), current and max
    HP (198125 vs 3857), speed (150 vs 100), template (916 vs 31) and visual
    preset.  ``field_mob_ai_tables`` adds two more the letter's own nonclaim
    missed, ``n_FACTION`` (12 vs 6) and ``n_AGGRO``.
    A RIVAL READING FITS ALL SIX NON-POSITIVE ROWS WITH ONE FIELD and this
    boot cannot separate it: a level-relative "con colour" against the
    viewer, who was a level 1 character.  The four yellow rows carry NO level
    field on the wire at all (they are composed by the sweep's plain-NPC
    body, which splices neither level nor faction); the orange row carries
    level 27; the red row carries level 100.  Note also that ``n_OFFESIVE``
    is never on the wire anywhere -- no encoder in this tree writes it -- so
    the client cannot be reading the field the letter names; at best it is
    reading something the client derives from the template itself.
    THE ONE ROW THAT WOULD SETTLE IT, and which this lane is asking for:
    a monster on template 916 (``n_OFFESIVE=1``) composed with level spliced
    to 27.  Red -> the letter's rule survives.  Orange -> the shade is level.
    Until that row is booted, :func:`expected_name_colour` reproduces the
    MEASURED mapping and nothing more; its ``offensive`` parameter is the
    name of the row's table column, not a claim about what the client read.
  * It does not claim the template id selects the colour either -- that
    reading is DEAD: ``N-IDNEG-T916`` and ``M-IDNEG`` share template 916 and
    came back yellow and red.
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
    "SCENE_ID_CEILING",
    "MOB_IDENTITY_BASE",
    "SWEEP_RESERVED_IDENTITIES",
    "scene_band_bounds",
    "is_player_identity",
    "is_mob_identity",
    "identity_is_drawn",
    "refuse_undrawable_identity",
    "mob_wire_identity",
    "scene_and_placement_for",
    "expected_name_colour",
    "encode_wire_identity",
    "decode_wire_identity",
    "is_targetable_identity",
    "WIRE_IDENTITY_MASK",
]


class MobIdentitySignError(ValueError):
    """Raised when an identity cannot carry the colour it is asked to."""


#: The width of the identity field on the wire, as ``v141.qwordtag`` masks
#: it (line 1131).  Inbound parsers hand back a value in ``[0, this]``.
WIRE_IDENTITY_MASK = 0xFFFFFFFFFFFFFFFF

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

#: How many placement slots one scene owns inside the monster band.
#: Re-derived at HEAD by pf-adversary (round ``gadxq5``) after the first
#: draft of this line quoted "Bg0010 at 72 rows, 439 over eleven scenes"
#: from this lane's own round file -- those are the [PROPOSED] numbers a
#: blocked cross-lane table would produce, not rows anyone can load today.
#: What ``field_mobs.load_roster`` actually answers at HEAD: 143 rows over
#: twelve scenes, widest Bg0002 at 52.  4096 is six doublings above that,
#: and the widest scene-id space this tree names is ``gm/scene_catalog``'s
#: (max id 999; ``world_scene_travel`` counts 271 client-registered ones),
#: so every scene gets its own block without approaching the 64-bit floor.
#: Named rather than inlined because the inverse depends on it.
SCENE_STRIDE = 0x1000

#: THE SWEEP'S NEGATIVE POOL IS NOT THIS BAND'S TO HAND OUT.
#: ``name_colour_sweep.NEGATIVE_IDENTITY_SLOTS`` allocates -1, -2, -3, ...
#: one per attended row.  pf-adversary (round ``gadxq5``) measured that the
#: first draft of :func:`mob_wire_identity` handed scene 0's first six
#: placements exactly -1..-6 -- a collision with all six sweep rows -- and
#: the sweep module writes the price of that collision itself: the client
#: keys an actor BY its identity, so two actors sharing one overwrite each
#: other and the board that survives answers a different question than the
#: one the tester is reading.  The production band therefore starts below a
#: reserved head.  Widen this rather than the sweep's pool if the sweep ever
#: needs more rows; the guard in ``tests/test_mob_identity_sign.py`` reads
#: the sweep's real tuple, so shrinking it here goes red.
SWEEP_RESERVED_IDENTITIES = 64

#: HOW MANY SCENE BLOCKS THE BAND DECLARES, which is the ceiling on the
#: scene component the way ``SCENE_STRIDE`` is the ceiling on the placement
#: component.  A band that ascends with BOTH components (see
#: :func:`mob_wire_identity`) has to know how many blocks it is stacking
#: before it can hand out the first one, so this is a declared bound and not
#: a derived one: a scene id at or above it is REFUSED rather than folded
#: back onto scene 0's block.  ``gm/scene_catalog`` is the widest scene-id
#: space this tree names -- 330 rows, ids 1..999 -- so 4096 leaves four
#: times the room the catalogue uses, and the most negative identity the
#: whole band can produce is -(64 + 4096*4096) = -16,777,280, which is
#: eleven orders of magnitude above :data:`MOB_IDENTITY_FLOOR` (-2**62 is
#: about -4.6e18; the ratio is 2.7e11).
SCENE_ID_CEILING = 0x1000

#: The most negative identity this allocator will ever hand out, kept one
#: bit away from ``-2**63`` (a factor of two, not the "full order of
#: magnitude" an earlier draft of this line claimed -- pf-adversary, round
#: 6okcq4) so a caller that adds an offset of its own cannot wrap the sign
#: bit back to positive.
MOB_IDENTITY_FLOOR = -(2**62)

#: The first (most negative) identity the band owns.  Every allocated value
#: is this plus a flat offset, which is what makes the band's order a single
#: total order rather than one order per scene.
MOB_IDENTITY_BASE = -(
    SWEEP_RESERVED_IDENTITIES + SCENE_ID_CEILING * SCENE_STRIDE)


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

    Called from the hostile-body composer, so a monster that no player could
    ever see cannot be handed to a census and then opened in the combat
    ledger.  Returns ``identity`` so it can be used inline.

    REACH, MEASURED (pf-adversary, round ``gadxq5``), because the first
    draft of this docstring oversold it: no input the composer can be handed
    TODAY reaches zero.  Every roster row parses through
    ``field_mobs`` line ~1346 with ``placement_index >= 0``, so
    ``actor_identity >= 0x2001``, and stubbing this refusal out kills no test
    but this module's own.  The one place in the tree that really does
    compose an identity-0 actor is the attended sweep's ``N-ID0`` row, which
    goes through the plain-NPC body and never touches this composer -- and
    that row is the measurement, so it is not this guard's job to stop it.
    This is a guard on the band that :func:`mob_wire_identity` is about to
    start handing out, placed before the first caller rather than after the
    first invisible monster.
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


def scene_band_bounds(scene_id: int) -> tuple[int, int]:
    """The (first, last) identity scene ``scene_id`` owns, both inclusive.

    Every scene declares the ceiling of its own block through this pair
    rather than through arithmetic spread over its callers, so "does scene
    ``n``'s block run into scene ``n+1``'s?" is a question a test can ask
    directly.  ``last - first + 1`` is always :data:`SCENE_STRIDE`, and a
    scene id the band does not own is refused here for the same reason
    :func:`mob_wire_identity` refuses it: a wrapped block hands two scenes
    the same identity, and the client keys an actor BY its identity.
    """
    _refuse_scene_id(scene_id)
    first = MOB_IDENTITY_BASE + scene_id * SCENE_STRIDE
    return first, first + SCENE_STRIDE - 1


def mob_wire_identity(scene_id: int, placement_index: int) -> int:
    """The monster-band identity for one placement in one scene.

    THE ORDER IS THE CONTRACT, NOT A SIDE EFFECT: increasing order by
    placement is the contract, not a side effect.  Identities ASCEND with
    the placement index inside a scene, and ascend with the scene id across
    scenes, so sorting a roster by identity reproduces the order the table
    placed it in.  That sentence is the whole point of this function and it
    must survive any future rewrite of the arithmetic.

    WHO WILL DEPEND ON IT, AND WHEN.  Nothing in ``src/`` calls this
    function today: every ``FieldMob`` still derives ``0x2000 +
    placement_index + 1`` (``field_mobs`` line ~376), so the readers below
    depend on the LEGACY formula's rise, not on this one.  They inherit the
    dependency the day beat 2 flips a scene onto the band, which is why the
    order is written down now rather than discovered then.  THREE readers,
    counted after pf-adversary (round 6okcq4) measured that an earlier draft
    of this list had four:

      * ``field_mobs.load_roster`` hands its rows out in PLACEMENT order and
        does not sort;
      * ``mob_combat.CombatLedger`` REFUSES a roster that is not in ascending
        identity order rather than sorting for its caller (reason
        ``ledger_not_sorted``), and ``runtime`` opens that ledger during
        session build -- so a descending band does not cost one frame, it
        costs LOGIN, for every player;
      * ``mob_ai_control.open_register`` sorts by identity SILENTLY, so with
        a descending band its row zero is a different monster from the one
        the ledger calls first, and nothing anywhere says so out loud.

    THE CENSUS IS NOT ONE OF THEM, and an earlier draft of this docstring
    said it was.  Every census composer re-sorts by distance to the player
    before encoding -- ``field_mobs.nearest_first`` (line ~2164) and
    ``world_population_*.census_order`` (line ~139 in each) both key on
    ``((dx**2 + dy**2 + dz**2), placement_index)`` -- so the order actors go
    out in is a pure function of the viewer's anchor and the table, and
    permuting the roster does not move one byte of it.  Consequence worth
    writing down: the census wire order is NOT a reason to prefer this fix
    over re-sorting ``load_roster``, though the COO letter that approved
    this one gave it as such.  RE-CHECKED, ROUND k1hsp0: a later restatement
    of the same approval (handed to this round as four readers --
    ``load_roster``, ``CombatLedger``, ``open_register`` AND census) still
    names census as a fourth dependant.  It is not: the measurement above
    (``nearest_first`` / ``census_order`` re-sorting by distance every time)
    is unchanged and this round re-ran it rather than take the restatement's
    word for it.  A docstring that named a fourth reader here would be
    exactly the kind of claim this house refuses to fabricate -- see
    ``refuse_undrawable_identity`` two guards up for the same house rule
    applied to a wire value instead of a paragraph.

    Before this function ascended, the THREE agreed only because the legacy
    ``0x2000 + placement_index + 1`` formula happened to rise (this sentence
    counted four until round ``k1hsp0`` struck the census out of the list
    two paragraphs up and left the tally behind -- pf-adversary of that
    round reported the mismatch, and a docstring whose count disagrees with
    its own list is how a reader concludes the census still depends on this
    order); the collision
    is written up in ``tests/test_mob_identity_sign_inbound.py`` and in COO
    decision ``20260908_1642_COO-DECISION-roster-order-take-option-three``,
    which picked this fix over re-sorting ``load_roster`` (that would change
    the order actors go out on the census wire, which is a screen question)
    and over teaching ``open_ledger`` to sort (that would delete another
    module's stated reason for refusing).

    Non-positive by construction (rule 2), never 0 (rule 4), and carrying a
    SCENE COMPONENT -- which is the half ``FieldMob.actor_identity`` is
    documented as missing (``field_mobs`` line ~1013: "``0x2000 +
    placement_index + 1`` with no scene component, so two scenes' placements
    collide").  Two different scenes cannot produce the same value here.
    """
    _refuse_scene_id(scene_id)
    _refuse_non_integer(placement_index, "placement index")
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
    identity = MOB_IDENTITY_BASE + scene_id * SCENE_STRIDE + placement_index
    # NO FLOOR CHECK AND NO SIGN CHECK HERE, ON PURPOSE.  Both guards were
    # written and both were measured DEAD by pf-adversary (round 6okcq4):
    # with the scene id capped at SCENE_ID_CEILING and the placement at
    # SCENE_STRIDE, this function's whole range is [MOB_IDENTITY_BASE, -65],
    # so neither branch can fire, and deleting either left the suite green.
    # mob_combat line ~644 states the house rule this follows: "a named
    # refusal which cannot occur is a lie told to whoever counts them".  The
    # two ceilings above are what keep the range where it is; the range
    # itself is asserted in test_the_whole_band_stays_clear_of_the_floor.
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
    flat = identity - MOB_IDENTITY_BASE
    if flat < 0:
        raise MobIdentitySignError(
            f"identity {identity} is below the first identity the band owns "
            f"({MOB_IDENTITY_BASE})"
        )
    if flat >= SCENE_ID_CEILING * SCENE_STRIDE:
        raise MobIdentitySignError(
            f"identity {identity} is inside the reserved head this band does "
            f"not hand out (the first {SWEEP_RESERVED_IDENTITIES} negative "
            "values belong to name_colour_sweep's attended rows)"
        )
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


def decode_wire_identity(wire: int) -> int:
    """The identity a caller MEANT, given the eight bytes that arrived.

    Exact inverse of :func:`encode_wire_identity` over the whole signed
    64-bit range: ``decode_wire_identity(int.from_bytes(encode_wire_identity(
    n), "little")) == n`` for every ``n`` the encoder accepts.

    WHY THIS EXISTS, MEASURED (pf-adversary, round ``gadxq5``, finding D4,
    confirmed as an order by COO-DECISION 20260908 14:41 beat 0):
    the outbound half already masks two's complement, but EVERY inbound
    parse point in ``current/pf_login_game_server_v141.py`` reads the same
    field with ``struct.unpack('<Q', ...)`` -- unsigned:

      * line ~3026 ``parse_target_vital``      -> ``actor_identity``
      * line ~3040 ``parse_choose_npc``        -> the single identity
      * line ~3061 ``extract_choose_npc_identities`` -> each identity
      * line ~3191 ``parse_quest_operate_vital`` -> ``field_qword_20``
      * line ~3264 ``parse_action_vital``      -> ``field_qword_18/20/28``

    So a monster-band identity of ``-2`` comes back as
    ``18446744073709551614``, no roster row equals it, and the player who
    clicked gets silence: no event, no log, no damage.  The frozen file is
    not edited (it is the client-derived reference and is never touched);
    the normalisation happens once, HERE, and every server-side reader of an
    inbound identity calls this before comparing it to anything.

    NOT A GUARD.  This function does not judge whether the identity is
    targetable, drawn, in band, or real -- see :func:`identity_is_drawn`,
    :func:`refuse_undrawable_identity` and :func:`is_targetable_identity`
    for that.  It only stops one number from having two meanings.
    """
    _refuse_non_integer(wire, "wire identity")
    if wire < 0 or wire > WIRE_IDENTITY_MASK:
        raise MobIdentitySignError(
            f"wire identity {wire} is not an unsigned 64-bit field value; "
            "this function decodes the bytes a parser produced, not an "
            "identity that was already decoded"
        )
    if wire >= 2**63:
        return wire - 2**64
    return wire


def is_targetable_identity(identity: int) -> bool:
    """True when an inbound frame may name ``identity`` as its target.

    The band moved, so the old shape of this test moved with it.  Before the
    monster band went negative, ``target <= 0`` was a serviceable stand-in
    for "not a real actor" at ``runtime.py`` line ~5227; the moment a monster
    can legitimately be ``-2`` that same test throws away every real hit on
    every monster.  What actually cannot be targeted is the one value the
    client refuses to draw (:data:`IDENTITY_NOT_DRAWN`) and anything outside
    the signed field the wire can carry.

    Takes an ALREADY DECODED identity: pass the result of
    :func:`decode_wire_identity`, never a raw parser value.
    """
    _refuse_non_integer(identity)
    if identity == IDENTITY_NOT_DRAWN:
        return False
    if identity >= 2**63 or identity < -(2**63):
        return False
    return True


def _refuse_scene_id(scene_id: Any) -> None:
    """One gate for the scene component, so both entry points agree.

    :func:`scene_band_bounds` and :func:`mob_wire_identity` must refuse the
    same set of scene ids or a caller could be told a block exists and then
    be refused when it asks for a row inside it.
    """
    _refuse_non_integer(scene_id, "scene id")
    if scene_id < 0:
        raise MobIdentitySignError(f"scene id {scene_id} is not a scene id")
    if scene_id >= SCENE_ID_CEILING:
        raise MobIdentitySignError(
            f"scene id {scene_id} is at or above the declared block ceiling "
            f"{SCENE_ID_CEILING} -- widen SCENE_ID_CEILING in one commit "
            "with the inverse rather than letting a scene wrap onto another "
            "scene's block"
        )


def _refuse_non_integer(value: Any, what: str = "identity") -> None:
    # `type(...) is not int` on purpose: bool subclasses int, and True as an
    # identity is the kind of thing that reads as 1 and draws a player.
    if type(value) is not int:
        raise MobIdentitySignError(f"{what} must be an int, got {value!r}")
