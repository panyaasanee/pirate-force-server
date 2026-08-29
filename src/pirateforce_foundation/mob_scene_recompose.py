"""LANE-B: the mid-session recompose census, scene by scene.

ROUND y9s0xo.  This is item (2) of the division the chief wrote in
``pf_bridge/notes_to_chief/20260829_1924_CHIEF-TO-LANE-B-recompose-bg0002-
three-measurements-and-the-division.md``: "a recompose composer of the Bg0002
shape (compare ``hostile_census_frames`` but over ``build_bg0002_population``
+ splice)".  It is built as a SCENE-DISPATCHED composer rather than a second
scene-2-only function, because the defect it closes is not "scene 2 has no
composer" -- it is "the recompose path knows exactly one scene", and a
scene-3 arriving later would rebuild the same hole.

WHAT THE PLAYER LOSES TODAY WITHOUT THIS, IN ONE SENTENCE.  A hit or a kill
in Prison Exile Island (Bg0002) falls into ``runtime.py``'s
``mob_combat_bar_census_compose_skipped_no_population_anchor`` /
``mob_death_frames_census_compose_skipped_no_population_anchor`` arm -- the
recompose guard there requires ``census_scene_id == world_population
.SCENE_ID`` (scene 1) -- so the frame that goes out is the ONE-ENTRY
collection ``RE-092`` proved is replace-by-omission: every other actor in
that map disappears from the client's registry on the first swing.  Scene 1
has been safe from that since ``mob_death.hostile_census_frames`` was wired;
scene 2 has not.

WHAT THIS MODULE DOES NOT DO, AND WHO OWNS IT.  It does not wire itself.  The
guard, the session state it reads and the choice of what to send when a
recompose is refused all live in ``runtime.py``, which is the chief's file and
which this lane does not edit (the lane's one reserved edit to that file was
spent in round ``z096sw``).  The chief's own half of the division -- "keep
anchor/count WITH the scene stamp that describes them at arrival, every
scene" -- is what :class:`CensusAnchor` exists to receive; see
:func:`census_anchor`.

THE SCENE-1 PATH IS DELEGATED, NOT REIMPLEMENTED.  Scene 1 already has a
composer that is live in production today and carries the five diagnostic
objects (``diag_multi_object_wiring.hostile_census_frames``).  This module
calls it, unchanged, with the caller's own arguments, and
``tests/test_mob_scene_recompose.py`` pins that the bytes it returns for
scene 1 are byte-identical to calling that function directly.  A second
implementation of a live path is a second thing to drift; there is exactly
one new composition here, and it is scene 2's.

IT NEVER RAISES ON A COMPOSITION FAILURE, IN EITHER SCENE.  Every real call
site is inside ``runtime.py``'s dispatch, where an escape unwinds the
listener thread and the player gets an empty world -- the same reasoning
``mob_ledger_admission.require_ledger_for_recompose`` already recorded when
it chose a FATAL line over a raise.  So a failure to compose comes back as a
RECORD with a named state and no frames, and the call site keeps whatever
fallback it already has.  Argument shapes are the one exception and they are
refused loudly with :class:`SceneRecomposeError` BEFORE any composition is
attempted: a wrong-typed anchor is a wiring bug that shows up on the first
boot, not a state a session can enter.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from . import diag_multi_object_wiring
from . import field_mobs
from . import mob_death
from . import mob_ledger_admission
from . import world_population
from . import world_population_bg0002


# No flag gates this module: it is lane B's always-on half, per CHARTER-02.
production_allowed = True
test_only = False

MOB_SCENE_RECOMPOSE_LANE = "B_COMBAT"
CONSOLE_TOKEN = "MOB_SCENE_RECOMPOSE"

# Composed and safe to send.
STATE_COMPOSED = "composed"
# The recompose was handed no ledger at all.  COO-DECISION 2026-08-29T18:42
# item 3: refuse loudly.  See :func:`recompose_frames` for why the refusal is
# a record and a FATAL line rather than a raise or a ceiling-HP compose.
STATE_NO_LEDGER = "refused_no_ledger"
# This lane ships no recompose composer for that scene.  A real answer, not a
# failure: it is what every scene except 1 and 2 is today.
STATE_NO_COMPOSER = "no_composer_for_scene"
# The composition itself refused.  The exception class name is appended, the
# same shape ``runtime.py``'s own fail-closed arms already log.
STATE_REFUSED_PREFIX = "refused_"
# COMPOSED, AND EVERY WOUNDED MONSTER IN THE FRAME IS AT ITS CEILING.  ROUND
# le2dox, MEASURED: this is what the scene-2 composer has done since it
# shipped, for every ledger the admission DECLINES -- another scene's ledger,
# an incomplete one, one whose rows disagree with the roster or the register.
# ``_compose`` passes ``admitted`` (which is ``None`` for all of those) into
# ``mob_death.full_roster_override``, and a roster override with no ledger
# composes at ceiling HP by design.  The frame that came back was reported as
# :data:`STATE_COMPOSED` and was BYTE-IDENTICAL to a census composed from an
# untouched ledger: a wounded monster's HP bar snapped back to full on the
# client and no line said so.
#
# That is COO-DECISION 2026-08-29T18:42 item 3's defect ("a recompose with no
# ledger heals every wounded monster") happening on the reachable input while
# :data:`STATE_NO_LEDGER` refuses it loudly on one that cannot occur --
# ``runtime.py:1134`` opens ``self.mob_combat_ledger`` at session
# construction and every path reassigns it, so ``ledger=None`` never reaches
# a bar frame.  The loud refusal guarded the impossible case.
#
# THE BYTES DO NOT CHANGE, and that is deliberate.  This lane already
# ratified the tradeoff in ``mob_ledger_admission
# .require_ledger_for_recompose``'s own words -- "Giving up 'one monster
# shows full HP' to get 'the world is empty' costs more than the defect
# does" -- and the call site's fallback for a non-composing state is the
# one-entry frame RE-092 proved erases every other actor.  So the frame is
# still sent (see :data:`COMPOSING_STATES` and ``SceneRecompose.composed``);
# what changes is that the record stops calling it a clean compose, names
# which identities it heals, and ``describe_recompose`` prints a FATAL line
# for it.
STATE_COMPOSED_HEALING = "composed_ledger_declined_at_ceiling"

# STATES WHOSE BYTES A CALL SITE MAY SEND.  ``SceneRecompose.composed`` reads
# THIS TUPLE rather than comparing against one state, so adding a composing
# state cannot silently turn a frame the call site used to send into the
# world-wipe fallback.  Until round le2dox this tuple had one member and no
# reader at all.
COMPOSING_STATES = (STATE_COMPOSED, STATE_COMPOSED_HEALING)


class SceneRecomposeError(ValueError):
    """An argument-shape refusal from this module.

    NOT the exception surface of :func:`recompose_frames` for anything that
    can happen mid-session -- see this module's docstring.  It is raised
    only for shapes a caller gets wrong once, at wiring time, and it is
    raised before any census is built.
    """


@dataclass(frozen=True)
class SceneComposer:
    """One scene's recompose composer, named rather than branched on inline."""

    scene_id: int
    scene: str
    kind: str


# ``kind`` is dispatched on in :func:`_compose`; it is a string rather than a
# callable so this table stays a description of what exists and cannot become
# a place where scene behaviour is smuggled in.
COMPOSER_DELEGATED = "delegated_to_diag_multi_object_wiring"
COMPOSER_BG0002 = "bg0002_population_plus_roster_override"

_COMPOSERS = {
    world_population.SCENE_ID: SceneComposer(
        world_population.SCENE_ID, "Bg0001", COMPOSER_DELEGATED,
    ),
    world_population_bg0002.SCENE2_N_ID: SceneComposer(
        world_population_bg0002.SCENE2_N_ID, "Bg0002", COMPOSER_BG0002,
    ),
}


# -------------------------------------------------------------------------
# SCENES THAT HAVE AN ARRIVAL CENSUS AND NO RECOMPOSE COMPOSER.
# -------------------------------------------------------------------------
# ROUND le2dox, answering ``pf_bridge/notes_to_chief/20260829_2340_CHIEF-TO-
# LANE-B-scene-14-has-a-census-but-no-recompose-composer.md`` item 1: name
# the scene, or declare that this lane will not compose it, and do it in the
# same PR rather than the next one.
#
# The entry is an ACKNOWLEDGEMENT, not a declination.  This lane WILL compose
# scene 14; what it cannot do is compose a map with no monsters in it.  The
# distinction matters because a declination would be a promise never to look
# again, and the tripwire below is built on the opposite promise.
#
# WHAT MAKES IT NOT A HOLE TODAY, MEASURED ROUND le2dox rather than quoted:
# ``field_mobs.scene_for_scene_id(14)`` returns ``None`` -- scene 14 is in
# NEITHER of field_mobs' two tables, so ``roster_for_scene_id(14)`` is not
# "zero rows for a known scene", it is "a scene this module cannot name".
# Every strike there is refused before a frame is composed.  (The chief's
# letter says "roster_for_scene_id(14) returns 0 rows", which is true and one
# layer above where the refusal actually happens.)
#
# WHAT OPENS IT: the first roster row in scene 14.  That is the day
# ``test_no_scene_with_roster_rows_lacks_a_composer`` goes red, which is item
# 2 of the same letter -- CI remembers this, nobody has to.
ACKNOWLEDGED_WITHOUT_COMPOSER = {
    14: (
        "Bg0015 -- lane A's arrival census composes it (lane_hooks/"
        "lane_a_scene_census.py); field_mobs names no scene 14 at all, so it "
        "has no combat roster and no strike can reach a recompose.  This "
        "lane composes it in the same round its first roster row lands."
    ),
}


def declared_without_composer() -> tuple[int, ...]:
    """Scene ids this lane has looked at and knowingly left uncomposed."""
    return tuple(sorted(ACKNOWLEDGED_WITHOUT_COMPOSER))


def scene_is_accounted_for(scene_id: Any) -> bool:
    """Whether THIS LANE HAS AN ANSWER for ``scene_id``: a composer, or a
    written acknowledgement that it knowingly has none yet.

    ~~``scenes_with_rows_and_no_composer()``, which walked every id
    addressing a live scene and reported the ones with roster rows and no
    composer.~~  WITHDRAWN IN THE ROUND THAT WROTE IT, le2dox: that tripwire
    ALREADY EXISTS as ``tests/test_mob_scene_recompose.py``'s
    ``test_every_scene_this_lane_ships_monsters_for_can_be_recomposed``,
    shipped in round y9s0xo, and a second spelling of a guard is a second
    thing to drift.  The lane's own standing order is to read what is there
    before writing anything, and this function was written without doing it.

    WHAT WAS ACTUALLY MISSING is the OTHER half, and it is the half the
    chief's letter (``20260829_2340``) is about: the existing pin fires on a
    scene with ROSTER ROWS.  Scene 14 has none -- it has an ARRIVAL CENSUS,
    composed by another lane's ``lane_hooks`` module, and nothing in this
    lane looks at that table at all.  That is how scene 14 arrived without
    this lane noticing, and no test could have caught it.
    ``tests/test_mob_scene_recompose.py`` crosswalks the lane_hooks census
    registry against this function, so the next scene another lane opens is
    red here on the commit that opens it.

    Never raises: an unusable scene id is simply not accounted for.
    """
    if type(scene_id) is not int or type(scene_id) is bool:
        return False
    return (
        scene_id in _COMPOSERS or scene_id in ACKNOWLEDGED_WITHOUT_COMPOSER
    )


@dataclass(frozen=True)
class CensusAnchor:
    """An anchor and a count, WITH the scene they were measured in.

    THIS TYPE IS THE POINT OF THE ROUND'S DEFENSIVE HALF, and it exists
    because of a defect pf-adversary measured on a shipped commit (round
    ``keen-pasteur-ahn7zb``, finding 2, quoted in ``runtime.py`` at the bar
    frame): ``population_refresh_anchor`` and ``world_census_actor_count``
    are two bare session attributes that DO NOT SAY WHICH SCENE THEY
    DESCRIBE, nothing clears them on scene departure, and the arena harness
    can overwrite the anchor outright.  The recompose guard in ``runtime.py``
    answers that today by comparing the player's CURRENT scene against
    ``world_population.SCENE_ID`` -- a guard that works only while exactly
    one scene can recompose, which is the thing this module ends.

    So the pair does not travel as two loose values here.  A composer for
    scene 2 cannot be handed scene 1's anchor without :func:`recompose_frames`
    refusing by name, and the refusal is structural rather than a rule the
    call site has to remember.

    ``actor_count`` is the count the ARRIVAL census committed, not a count
    this module chooses: a recompose that sends a different number of bodies
    than arrival did is a membership change dressed as a refresh.
    """

    scene_id: int
    anchor: tuple[float, float, float]
    actor_count: int


def census_anchor(
    scene_id: Any, anchor: Any, actor_count: Any,
) -> CensusAnchor:
    """Build a :class:`CensusAnchor`, refusing every shape that is not one.

    The one call the chief's half of the division needs at each arrival site:
    store this record instead of two bare attributes, and the recompose can
    never be composed against another scene's anchor.

    Refuses rather than coerces: an anchor arriving as a list, or a count
    arriving as a float or a bool, is a call site that has lost track of what
    it holds, and silently accepting it is how a scene-1 anchor reaches a
    scene-2 compose in the first place.
    """
    if type(scene_id) is not int or type(scene_id) is bool:
        raise SceneRecomposeError("scene id must be an int, not %r" % (scene_id,))
    if type(anchor) is not tuple or len(anchor) != 3:
        raise SceneRecomposeError(
            "anchor must be an exact three-value tuple, not %r" % (anchor,))
    for axis, value in zip("xyz", anchor):
        if type(value) not in (int, float) or type(value) is bool:
            raise SceneRecomposeError(
                "anchor %s must be a finite number, not %r" % (axis, value))
        if value != value or value in (float("inf"), float("-inf")):
            raise SceneRecomposeError(
                "anchor %s must be finite, not %r" % (axis, value))
    if type(actor_count) is not int or type(actor_count) is bool or actor_count < 1:
        raise SceneRecomposeError(
            "actor count must be a positive int, not %r" % (actor_count,))
    return CensusAnchor(
        scene_id, (float(anchor[0]), float(anchor[1]), float(anchor[2])),
        actor_count,
    )


@dataclass(frozen=True)
class SceneRecompose:
    """What one recompose attempt produced, including the ones that produced
    no bytes.  ``pc``/``frame`` are ``None`` for every state but
    :data:`STATE_COMPOSED`, so a caller cannot send a refusal by accident."""

    scene_id: int
    scene: str
    state: str
    pc: bytes | None = None
    frame: bytes | None = None
    # WHAT THE COMPOSITION ITSELF SAYS IT BUILT, or ``None`` when the composer
    # does not report it (the delegated scene-1 path returns bytes only).
    # ``requested_count`` is what the caller ASKED for and the two are NOT the
    # same number even on a healthy boot -- measured this round: a scene-1
    # recompose requested at ``world_population.CENSUS_COUNT`` (115) puts 108
    # bodies on the wire, because BUILD-001 closed at the 108-actor data
    # ceiling (COO-DECISION 2026-08-29T19:41).  The first draft of this record
    # reported the requested count as the composed one and printed
    # ``wire=MISMATCH:108`` on every healthy scene-1 recompose -- an alarm
    # that fires on the normal case teaches a tester to ignore the field.
    actor_count: int | None = None
    wire_actor_count: int | None = None
    requested_count: int | None = None
    # WHERE THE COUNT CAME FROM, reported for the reason the arrival census
    # line already reports ``source=``: the two lines describe the same
    # collection at two moments, and a reader comparing them needs the same
    # field on both.  It is here because of this round's OWN mutation sweep:
    # M15 changed the scene-2 build from ``COUNT_SOURCE_CALLER`` to
    # ``COUNT_SOURCE_FULL_ROSTER`` and SURVIVED the whole suite -- the
    # argument changed no bytes and nothing read it, so the paragraph in
    # :func:`_compose` explaining the choice was guarding nothing.
    count_source: str = "not_reported"
    ledger_state: str = mob_ledger_admission.STATE_ABSENT
    ledger_covered: int = 0
    ledger_roster: int = 0
    fatal: bool = False
    # WHETHER THE BYTES IN THIS RECORD RESEND A WOUNDED MONSTER AT ITS
    # CEILING.  See :data:`STATE_COMPOSED_HEALING`.  It is a field rather
    # than a state comparison because a reader asking "is this frame safe for
    # HP bars" is asking one question, and the day a second healing state
    # exists that reader must not have to learn its name.
    heals: bool = False
    # WHICH identities this frame heals, or ``None`` for NOT MEASURED -- the
    # distinction ``mob_ledger_admission`` keeps for ``missing_measured`` and
    # ``conflicts``, for the same reason: an empty tuple here means "looked,
    # found none wounded", and a declined ledger this module cannot read row
    # by row (another scene's, or one that will not answer ``balance_of``)
    # can produce neither answer honestly.  ``()`` with ``heals=True`` is a
    # real combination: the frame is composed at ceiling for a ledger that
    # happened to hold nothing wounded, which is harmless TODAY and is still
    # the declined-ledger path.
    healed_identities: tuple[int, ...] | None = None
    dead_timer: float | None = None
    detail: str = ""

    @property
    def composed(self) -> bool:
        """Whether a call site may put ``pc``/``frame`` on the wire.

        NOT ``state == STATE_COMPOSED``.  ``STATE_COMPOSED_HEALING`` carries
        real bytes for the whole scene, and the fallback a call site keeps
        for a non-composing record is the one-entry frame -- so reading this
        as an equality test would have answered a defect that heals one HP
        bar by erasing every actor in the map.
        """
        return self.state in COMPOSING_STATES


def composer_scene_ids() -> tuple[int, ...]:
    """The scene ids this lane can recompose today, ascending."""
    return tuple(sorted(_COMPOSERS))


def composer_for_scene_id(scene_id: Any) -> SceneComposer | None:
    """The composer for a scene, or ``None``.  ``None`` is a real answer."""
    if type(scene_id) is not int or type(scene_id) is bool:
        return None
    return _COMPOSERS.get(scene_id)


def splice_identity_override(
    legacy: Any, generation: Any, override: dict[int, bytes],
) -> Any:
    """``world_population.apply_identity_override``, for ANY census generation.

    THE SAME ALGORITHM, DELIBERATELY NOT A THIRD COPY OF IT.  ``runtime.py``
    has a private duck-typed copy (``_apply_mob_death_census_override``) that
    the Bg0002 ARRIVAL branch already calls, and ``world_population
    .apply_identity_override`` is lane B's own tested reimplementation which
    type-checks its argument against ``WorldPopulationGeneration`` and so
    cannot be pointed at a ``Bg0002PopulationGeneration`` at all.  This
    module needs the splice for a generation of the second kind, from a
    module (``world_population_bg0002``) that belongs to lane A and that this
    lane does not edit.

    So this is that splice with the type gate replaced by a STRUCTURAL one:
    any generation carrying ``actor_identities``, ``entry_bytes`` and ``pc``
    in the frozen wire order works, and anything else is refused by name.
    ``tests/test_mob_scene_recompose.py`` pins it byte-identical to
    ``world_population.apply_identity_override`` over the real 115-actor
    bg0001 census, so the two cannot drift apart unnoticed.

    ``WIRE_HEADER_BYTES`` is read from ``world_population`` -- the same
    constant ``world_population_bg0002`` itself imports rather than
    redefining, so one header rule covers both scenes.

    INHERITED NONCLAIM, carried here rather than left for a reader to
    rediscover: the ``offset != len(pc)`` guard checks the SUM of
    ``entry_bytes``, so a permutation of those lengths that preserves the sum
    would misassign slices with no exception.  Named in
    ``world_population.apply_identity_override``'s own docstring, dormant for
    the same reason here (every generation this composes comes fresh from a
    builder), not fixed by this module.
    """
    identities = getattr(generation, "actor_identities", None)
    lengths = getattr(generation, "entry_bytes", None)
    pc = getattr(generation, "pc", None)
    if (
        type(identities) is not tuple or type(lengths) is not tuple
        or type(pc) is not bytes
    ):
        raise SceneRecomposeError(
            "a census generation must carry actor_identities, entry_bytes "
            "and pc; %r carries %r" % (type(generation).__name__, (
                type(identities).__name__, type(lengths).__name__,
                type(pc).__name__))
        )
    if len(identities) != len(lengths):
        raise SceneRecomposeError(
            "generation has %d identities and %d entry lengths: the splice "
            "cannot tell which bytes belong to which actor"
            % (len(identities), len(lengths))
        )
    if not override:
        return generation
    offset = world_population.WIRE_HEADER_BYTES
    entries = []
    for identity, length in zip(identities, lengths):
        original = pc[offset:offset + length]
        entries.append(override.get(identity, original))
        offset += length
    if offset != len(pc):
        raise SceneRecomposeError(
            "generation.entry_bytes does not account for the whole "
            "collection: the identity override cannot be applied safely"
        )
    for position, entry in enumerate(entries):
        # An entry that encodes to nothing still counts in the collection's
        # count field -- the stream-tail misalignment this client answers
        # with ErrorData=28317 (world_population's own words).
        if type(entry) is not bytes or not entry:
            raise SceneRecomposeError(
                "entry %d of the spliced collection is empty" % position)
    spliced_pc, spliced_frame = legacy.make_runtime_remote_actors(entries)
    if spliced_frame != legacy.frame_pc(spliced_pc):
        raise SceneRecomposeError("scene recompose frame drift")
    return replace(
        generation, pc=spliced_pc, frame=spliced_frame,
        entry_bytes=tuple(len(entry) for entry in entries),
    )


def _wire_actor_count(pc: bytes) -> int | None:
    """The collection count read back off the bytes, or ``None`` if the
    header is not the one both scenes' builders write.  Never raises: this
    feeds a console line, and a console line does not decide a boot."""
    header = world_population.WIRE_HEADER_BYTES
    tag_offset = world_population.WIRE_COUNT_TAG_OFFSET
    if (
        type(pc) is not bytes or len(pc) < header
        or pc[tag_offset] != world_population.COLLECTION_TAG
    ):
        return None
    return int.from_bytes(pc[tag_offset + 1:tag_offset + 3], "little")


def _healed_identities(ledger: Any, roster: Any, admission: Any) -> Any:
    """Roster identities the DECLINED ``ledger`` holds below their ceiling.

    ``None`` means NOT MEASURED and is returned for two different reasons,
    both of which are "could not look" rather than "found none":

    * the ledger names a scene other than this roster's
      (:data:`mob_ledger_admission.STATE_OTHER_SCENE`) or could not be read
      at all -- its rows are a different map's monsters that happen to share
      identity numbers, so "identity 0x2033 is at 40%" is a fact about
      somebody else and reporting it here would put another scene's HP in
      this scene's console line;
    * any single ``balance_of`` raises, which on an incomplete ledger is the
      ordinary case for the identities it does not hold.

    Never raises.  This decorates a console line and sets a boolean the call
    site reads; a count that cannot be taken must not cost the frame.
    """
    if admission == mob_ledger_admission.STATE_OTHER_SCENE:
        return None
    try:
        wounded = []
        for mob in roster:
            balance = ledger.balance_of(mob.actor_identity)
            if balance.current_hp < balance.max_hp:
                wounded.append(int(mob.actor_identity))
        return tuple(sorted(wounded))
    except Exception:  # noqa: BLE001 - a console field never kills a boot
        return None


def recompose_frames(
    legacy: Any,
    anchor: CensusAnchor,
    register: Any,
    *,
    ledger: Any,
    roster: Any = None,
    dead_timer: float = mob_death.DEAD_TIMER_SECONDS,
    objects: tuple = (),
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
) -> SceneRecompose:
    """The full-census frame for a hit or a kill, in whichever scene it happened.

    ``ledger`` HAS NO DEFAULT, and that is item (1) of the chief's division
    ("ban the ``ledger=None`` default on the recompose path") in the form
    that actually binds: a call site that forgets it gets a ``TypeError`` on
    the first boot rather than a census that quietly heals every wounded
    monster back to its ceiling.  ``mob_death.hostile_census_frames`` states
    the same rule for the scene-1 composer in its own words -- "every real
    call site of THIS function already holds a live ledger, and one that
    omits it is not a legitimate early-boot caller".

    PASSING ``None`` EXPLICITLY IS REFUSED, NOT HEALED AND NOT RAISED ON.
    The record comes back with :data:`STATE_NO_LEDGER`, ``fatal=True`` and no
    bytes, and :func:`describe_recompose` prints
    ``mob_ledger_admission``'s ``MOB_LEDGER_ADMISSION_FATAL`` line for it.
    The third option -- composing the whole census at ceiling HP and only
    logging -- was considered and NOT taken: it would put a frame on the wire
    that silently resurrects every wounded monster's HP bar, which is the
    exact defect COO-DECISION 2026-08-29T18:42 item 3 named, and a lane does
    not get to send the defect as long as it also prints about it.  What the
    call site sends instead when this state comes back is the call site's
    decision and it is the chief's to make; today ``runtime.py`` degrades to
    the one-entry frame, which is a WORSE outcome than either -- that
    tradeoff is written into this lane's wiring ask rather than settled here
    by a module that cannot see the dispatch.

    THE PARAGRAPH ABOVE GUARDED A STATE THAT CANNOT HAPPEN, AND THE STATE
    THAT CAN HAPPEN WENT OUT UNANNOUNCED.  [ROUND le2dox, MEASURED.]
    ``runtime.py:1134`` opens ``self.mob_combat_ledger`` at session
    construction and every later path reassigns it, so ``ledger=None`` never
    reaches a bar or death frame -- :data:`STATE_NO_LEDGER` is a loud refusal
    of the unreachable input.  Meanwhile a ledger the admission DECLINES
    (another scene's after a scene round trip, an incomplete one, one whose
    rows disagree with the roster or the register) was reported as
    :data:`STATE_COMPOSED`, and its scene-2 frame measured BYTE-IDENTICAL to
    a census composed from an untouched ledger: the wounded monster healed on
    the client, the record said "composed", no line anywhere.  That is the
    same COO-DECISION 2026-08-29T18:42 item 3 defect this function's own
    docstring says it will not ship, arriving through the door the docstring
    did not check.  It is now :data:`STATE_COMPOSED_HEALING` -- same bytes,
    named state, measured ``healed_identities``, FATAL console line.

    ``roster`` defaults to the scene's own rows (``field_mobs
    .roster_for_scene_id``).  A caller that has already widened its roster --
    ``diag_multi_object_wiring.widen_for_combat``'s five diagnostic
    identities, which the scene-1 path requires whenever ``objects`` is
    nonempty -- must pass the WIDENED one, exactly as it does today when it
    calls the scene-1 composer directly.

    ``objects`` is accepted for scene 1 and REFUSED for any other scene: the
    five diagnostic bodies are bg0001 placements with bg0001 identities, and
    appending them to another map's census would put actors in a scene they
    do not stand in.  The refusal is a record, not a raise.
    """
    if type(anchor) is not CensusAnchor:
        raise SceneRecomposeError(
            "recompose needs a CensusAnchor, which carries the scene its "
            "anchor and count were measured in, not a bare %r -- see "
            "census_anchor()" % (type(anchor).__name__,)
        )
    if type(objects) is not tuple:
        raise SceneRecomposeError("objects must be a tuple, not %r" % (objects,))
    if type(dead_timer) not in (int, float) or type(dead_timer) is bool:
        raise SceneRecomposeError(
            "dead timer must be a number, not %r" % (dead_timer,))

    scene_id = anchor.scene_id
    composer = composer_for_scene_id(scene_id)
    scene = field_mobs.scene_for_scene_id(scene_id) or (
        composer.scene if composer else "?")
    if composer is None:
        return SceneRecompose(
            scene_id, scene, STATE_NO_COMPOSER,
            dead_timer=float(dead_timer),
            detail="this lane recomposes scenes %s only" % (
                ",".join(str(i) for i in composer_scene_ids()),),
        )
    if objects and composer.kind != COMPOSER_DELEGATED:
        return SceneRecompose(
            scene_id, scene, STATE_REFUSED_PREFIX + "objects_outside_scene_1",
            dead_timer=float(dead_timer),
            detail="the diagnostic objects are bg0001 placements",
        )

    if roster is None:
        roster = field_mobs.roster_for_scene_id(scene_id)
    # THE ROSTER IS CHECKED HERE OR IT ESCAPES.  ``require_ledger_for_recompose``
    # walks ``mob.actor_identity`` over these rows on the very next line, and
    # it does that OUTSIDE the ``try`` below -- so rows that are not roster
    # rows would raise an ``AttributeError`` straight past this module's
    # "every composition failure comes back as a record" contract.  A roster
    # is an argument, so it is refused the way the other argument shapes are:
    # loudly, by name, before anything is composed.
    if type(roster) not in (tuple, list) or any(
        not hasattr(row, "actor_identity") for row in roster
    ):
        raise SceneRecomposeError(
            "roster must be a sequence of roster rows carrying "
            "actor_identity, not %r" % (type(roster).__name__,)
        )

    # Asked about THE ROWS BEING COMPOSED, never about a re-derivation of
    # them -- the rule mob_census_hostility states for its own inputs, for
    # the same reason: a check computed from a different copy of the thing it
    # checks can agree with itself while the composition raises.
    # ``register=`` IS PASSED, AND IT WAS NOT UNTIL ROUND le2dox.  The
    # argument exists on this function already; the admission call left it
    # out, so ``register_checked`` came back False on every recompose this
    # module has ever done -- while ``admit_ledger``'s own docstring names
    # this path as the one that must check: "A caller composing entries HAS
    # a register -- mob_death.repopulation_entries requires one -- so the
    # path that can actually raise is the path that can always check."
    #
    # WHAT PASSING IT CHANGES, MEASURED, NOT ASSUMED.  A ledger that
    # contradicts the register used to be ADMITTED here (D1 never ran), get
    # handed to ``full_roster_override``, and raise ``MobDeathContractError``
    # from inside the composer -- caught below as ``refused_...``, no bytes,
    # and the call site's one-entry world wipe.  It is now DECLINED by the
    # admission instead, which on the scene-2 path composes at ceiling and
    # comes back as :data:`STATE_COMPOSED_HEALING`: the whole map, one or
    # more HP bars wrong, a FATAL console line, and a frame the client can
    # actually draw.  That is the same tradeoff this lane's admission module
    # already took for the ledger it cannot get, applied to the ledger it
    # can get and cannot trust.  [LANE-B assumption - awaiting COO
    # confirmation; the letter carrying it is 20260830_LANE-B-ASK-COO-a-
    # declined-ledger-heals-what-a-refusal-erases.]
    admission = mob_ledger_admission.require_ledger_for_recompose(
        scene_id, ledger, roster=roster, register=register,
    )
    covered = int(admission.get("covered_count") or 0)
    roster_rows = int(admission.get("roster_count") or len(roster))

    if ledger is None:
        return SceneRecompose(
            scene_id, scene, STATE_NO_LEDGER,
            ledger_state=admission["state"], ledger_covered=covered,
            ledger_roster=roster_rows, fatal=True,
            dead_timer=float(dead_timer),
            detail="a recompose with no ledger heals every wounded monster",
        )

    try:
        pc, frame, composed_count, count_source = _compose(
            legacy, composer, anchor, roster, register,
            ledger=ledger, admitted=admission["ledger"],
            dead_timer=float(dead_timer), objects=objects,
            faction=faction, with_name=with_name,
        )
    except Exception as error:  # noqa: BLE001 - see the module docstring
        return SceneRecompose(
            scene_id, scene, STATE_REFUSED_PREFIX + type(error).__name__,
            ledger_state=admission["state"], ledger_covered=covered,
            ledger_roster=roster_rows,
            dead_timer=float(dead_timer),
            detail=str(error)[:200],
        )
    # HEALING IS A PROPERTY OF THE COMPOSER, NOT OF THE ADMISSION.  Only the
    # scene-2 composer derives its HP from ``admitted``; the delegated
    # scene-1 path is handed the RAW ledger and keeps every wounded row it
    # holds even when the admission declines (measured round le2dox: a
    # declined scene-1 recompose does not reach this line at all -- the live
    # composer raises and comes back as ``refused_MobDeathContractError``
    # above).  Flagging on the admission alone would print a healing warning
    # over a scene-1 frame whose HP is correct.
    heals = composer.kind == COMPOSER_BG0002 and admission["ledger"] is None
    return SceneRecompose(
        scene_id, scene, STATE_COMPOSED_HEALING if heals else STATE_COMPOSED,
        pc, frame, composed_count,
        _wire_actor_count(pc), anchor.actor_count, count_source,
        ledger_state=admission["state"], ledger_covered=covered,
        ledger_roster=roster_rows, dead_timer=float(dead_timer),
        heals=heals,
        healed_identities=(
            _healed_identities(ledger, roster, admission["state"])
            if heals else None
        ),
    )


def _compose(
    legacy: Any,
    composer: SceneComposer,
    anchor: CensusAnchor,
    roster: Any,
    register: Any,
    *,
    ledger: Any,
    admitted: Any,
    dead_timer: float,
    objects: tuple,
    faction: int,
    with_name: bool,
) -> tuple[bytes, bytes, int | None, str]:
    """Build one scene's full-census frame.  Raises; :func:`recompose_frames`
    is the only caller and it turns every raise into a named record."""
    if composer.kind == COMPOSER_DELEGATED:
        # THE LIVE SCENE-1 PATH, CALLED RATHER THAN COPIED.  The RAW ledger
        # goes in, not the admitted one: this call must stay byte-identical
        # to what ``runtime.py`` sends today (pinned in the tests), and
        # ``mob_death.hostile_census_frames`` refuses ``ledger=None``
        # outright -- handing it a declined ledger's ``None`` would turn a
        # scene-1 recompose that works today into a refusal.  The admission
        # is still MEASURED and reported for scene 1; it just does not
        # decide anything there.
        pc, frame = diag_multi_object_wiring.hostile_census_frames(
            legacy, anchor.anchor, anchor.actor_count, roster, register,
            ledger=ledger, objects=objects, dead_timer=dead_timer,
            faction=faction, with_name=with_name,
        )
        # NOT ``anchor.actor_count``: that is what was asked for, and this
        # composer returns bytes without saying how many bodies it put in
        # them.  ``None`` is the honest answer to "what does the composition
        # report" here; the wire count is measured from the bytes either way.
        #
        # The count source is the one this composer's own chain applies:
        # ``mob_death.hostile_census_frames`` defaults to
        # ``world_population.COUNT_SOURCE_CALLER`` and this module does not
        # override it, so the value is READ from that module rather than
        # spelled again here -- a second spelling is a second thing to drift.
        return pc, frame, None, world_population.COUNT_SOURCE_CALLER
    if composer.kind != COMPOSER_BG0002:
        raise SceneRecomposeError(
            "unknown composer kind %r for scene %d" % (
                composer.kind, composer.scene_id))

    # SCENE 2, THE ONE NEW COMPOSITION IN THIS MODULE.  The same three calls
    # ``mob_death.hostile_census_frames`` makes for scene 1 -- build, roster
    # override, splice -- with the scene-2 builder in the first position,
    # because ``world_population.build_world_population`` refuses anywhere
    # but scene 1 by design and it is not this lane's business to loosen it.
    #
    # ``count_source`` is CALLER, not FULL_ROSTER: the count comes off the
    # arrival census the player is already looking at (``anchor.actor_count``),
    # and a recompose that quietly re-derives the full roster count would
    # change membership on a frame that is supposed to refresh it.
    generation = world_population_bg0002.build_bg0002_population(
        legacy, anchor.anchor, anchor.actor_count,
        scene_id=composer.scene_id,
        count_source=world_population_bg0002.COUNT_SOURCE_CALLER,
    )
    # ``admitted`` here, not ``ledger``: a ledger that cannot answer for
    # these rows makes ``repopulation_entries`` raise, and round jop8ph's
    # whole point is that the answer to that is a named decline, not an
    # exception in the listener thread.  A declined ledger composes the
    # census at ceiling HP -- which is what this path did before the ledger
    # existed at all -- and ``describe_recompose`` says so on the line.
    override = mob_death.full_roster_override(
        legacy, roster, register, ledger=admitted, faction=faction,
        with_name=with_name, dead_timer=dead_timer,
    )
    composed = splice_identity_override(legacy, generation, override)
    return (
        composed.pc, composed.frame, composed.actor_count,
        composed.count_source,
    )


def describe_recompose(record: Any) -> tuple[str, ...]:
    """ASCII console lines for one recompose (G-OBS).

    Printed by a call site UNCONDITIONALLY, outside whatever ``if`` chose the
    frame -- the rule this lane has now written into three modules, and the
    one ``runtime.py``'s two recompose arms had to be corrected for in round
    ``z096sw``: the states that put a one-entry frame on the wire were the
    states with no line at all.

    Plain ASCII for the bridge's cp874 console, one line, plus the admission
    lines ``mob_ledger_admission`` already prints so a boot log can be
    grepped for the ledger decision on this path with the same expression
    that finds it on the arrival path.
    """
    if type(record) is not SceneRecompose:
        return (
            "%s state=undescribable detail=not_a_SceneRecompose" % CONSOLE_TOKEN,
        )
    lines = (
        "%s scene_id=%d scene=%s state=%s requested=%s actors=%s wire=%s "
        "source=%s pc=%sB frame=%sB "
        "ledger=%s covered=%d/%d dead_timer=%s fatal=%s heals=%s" % (
            CONSOLE_TOKEN,
            record.scene_id,
            record.scene or "?",
            record.state,
            "none" if record.requested_count is None else record.requested_count,
            "none" if record.actor_count is None else record.actor_count,
            # MISMATCH is reserved for a composer that CONTRADICTS ITS OWN
            # BYTES.  A composer that does not report a count cannot
            # contradict anything, and the requested count legitimately
            # differs from both (see SceneRecompose.actor_count).
            "none" if record.wire_actor_count is None else (
                record.wire_actor_count
                if record.actor_count is None
                or record.wire_actor_count == record.actor_count
                else "MISMATCH:%d" % record.wire_actor_count),
            record.count_source,
            "none" if record.pc is None else len(record.pc),
            "none" if record.frame is None else len(record.frame),
            record.ledger_state,
            record.ledger_covered,
            record.ledger_roster,
            "none" if record.dead_timer is None else record.dead_timer,
            "yes" if record.fatal else "no",
            # THREE ANSWERS, NOT TWO.  ``no`` is "these bytes carry the HP
            # the ledger holds".  ``N`` is "N wounded rows went out at their
            # ceiling and here is how many".  ``unmeasured`` is "this frame
            # heals and this module could not count what" -- the state a
            # foreign or unreadable ledger produces, which must not print as
            # ``0``: a zero a reader trusts is worse than a word that makes
            # them look.
            "no" if not record.heals else (
                "unmeasured" if record.healed_identities is None
                else len(record.healed_identities)),
        ),
    )
    if record.detail:
        lines = lines + (
            "%s scene_id=%d detail=%s" % (
                CONSOLE_TOKEN, record.scene_id, record.detail),
        )
    if record.fatal:
        lines = lines + (
            "%s scene_id=%d reason=no_ledger_passed_to_recompose "
            "effect=no_full_census_frame_composed" % (
                mob_ledger_admission.FATAL_TOKEN, record.scene_id),
        )
    if record.heals:
        # THE SAME TOKEN AS THE NO-LEDGER LINE, ON PURPOSE.  A tester
        # grepping ``MOB_LEDGER_ADMISSION_FATAL`` is asking "did a census go
        # out that lies about HP" -- one expression, both ways it can
        # happen.  The ``reason=`` field is what separates them, and it
        # carries the admission's own state name rather than a paraphrase,
        # so the recompose line and the admission line can be read as one
        # sentence.
        lines = lines + (
            "%s scene_id=%d reason=ledger_declined_%s "
            "effect=wounded_rows_resent_at_ceiling identities=%s" % (
                mob_ledger_admission.FATAL_TOKEN, record.scene_id,
                record.ledger_state,
                "unmeasured" if record.healed_identities is None else (
                    "none" if not record.healed_identities else ",".join(
                        "0x%04X" % i for i in record.healed_identities)),
            ),
        )
    return lines


# -------------------------------------------------------------------------
# THE WIRING THIS MODULE IS WAITING ON -- runtime.py, the chief's file.
# -------------------------------------------------------------------------
# Written here, beside the functions it calls, the same convention
# ``mob_death.MOB_DEATH_WIRING`` and ``diag_multi_object_wiring
# .RUNTIME_WIRING_PATCH`` already use.  Every line is inside
# ``PersistentGameSessionState``; none of it changes what a scene-1 session
# sends today.
SCENE_RECOMPOSE_WIRING = r'''
# (1) AT ARRIVAL, EVERY SCENE -- replace the two bare attributes with the
#     stamped record.  Both scene branches, not just bg0002: the guard below
#     stops being "am I in scene 1" only when both sides carry a stamp.
self.census_anchor_record = mob_scene_recompose.census_anchor(
    scene_id, tuple(durable_target[:3]), generation.actor_count,
)

# (2) AT THE BAR FRAME AND AT THE DEATH FRAMES -- one call replaces the
#     scene-1-only guard, and the fallback arm keeps its current bytes.
record = mob_scene_recompose.recompose_frames(
    legacy, self.census_anchor_record, self.mob_death_register,
    ledger=self.mob_combat_ledger, roster=roster,
    dead_timer=mob_death.DYING_TIMER_SECONDS,   # DEAD_TIMER_SECONDS for the
    objects=self.diag_multi_objects,            # dead frame and the bar frame
)
for line in mob_scene_recompose.describe_recompose(record):
    print(line)
if record.composed:
    bar_pc, bar_frame = record.pc, record.frame
else:
    bar_pc, bar_frame = step.bar_pc, step.bar_frame
    self.events.append(
        "mob_combat_bar_census_compose_skipped_" + record.state)

# (3) THE DECISION THIS MODULE CANNOT MAKE FOR THE CALL SITE.  Today the
#     fallback above is the ONE-ENTRY frame RE-092 proved erases every other
#     actor by omission.  That is the right fallback for
#     ``no_composer_for_scene`` (there is nothing else to send) and the wrong
#     one for ``refused_no_ledger``, where the session holds a census it
#     could resend unchanged.  Keeping the previous full-census frame per
#     scene and resending it is the shape this lane would build if the chief
#     wants it; it needs session state this lane does not own.
'''
