"""Make the identity-uniqueness claim EXECUTABLE, over the data we ship today.

THIS MODULE WRITES NOTHING, SENDS NO BYTE, GRANTS NO GM STATUS AND CHOOSES NO
IDENTITY VALUE.  It reads the placement tables this repository already ships
and reports who claims which wire identity.

Why this lane, and why now
--------------------------
``NOW.md`` P-2 forbids, in its own words, guessing a signed-negative identity
"without closing uniqueness/registry".  ``gm/name_color_gate.py`` carries the
matching bounded negative from ``RE-195``, whose closing line asks for "a
coherent nonpositive identity mapping PLUS a typed/live gate proof".  The
typed/live half needs the client image and belongs to the RE runner.  The
uniqueness/registry half needs no image at all -- it is a question about OUR
tables -- and until this module there was nothing runnable to answer it.

What stood in its place was a COMMENT, hand-copied into fourteen scene
modules almost word for word:

    "Never sent in the same generation as another scene's census - every
    builder refuses any scene id but its own - so sharing the numeric space
    is a collision in the abstract only."

That sentence is a claim about data, repeated by hand, checked by nobody.
``field_mobs.load_roster``'s own docstring already calls the same hazard "not
fixed, only unrealised", and ``field_mobs.scene_for_scene_id`` records a round
where it WAS realised.  This module turns the claim into measurements a test
can hold, and it reports what it measures rather than what the comment says.

What it does NOT do, said before the API so nobody reads past it
----------------------------------------------------------------
* It does not propose, allocate, or validate a NEGATIVE identity scheme.
  Closing uniqueness/registry is a PRECONDITION named by ``NOW.md``, not
  permission; ``name_color_gate.p2_color_wiring_verdict()`` still refuses,
  and this module does not touch its blockers.
* It does not decide which family "should" win when two of them describe one
  identity.  ``world_population.apply_identity_override`` already decides
  that, keyed by identity alone, and this module's job is to say out loud
  what that door is keyed on and what it is standing on today.
* It does not renumber anything.  ``actor_identity`` stays exactly what each
  family says it is.
* It knows nothing about the client.  Every number here comes from this
  repository; no VA, no offset, no FontStyleID.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .. import field_mobs
from .. import population
from .. import scene2_prison_exile_tables
from .. import world_bg0003_identity
from .. import world_bg0004_identity
from .. import world_bg0005_identity
from .. import world_bg0006_identity
from .. import world_bg0007_identity
from .. import world_bg0008_identity
from .. import world_bg0009_identity
from .. import world_bg0010_identity
from .. import world_bg0011_identity
from .. import world_bg0015_identity
from .. import world_bg3001_identity
from .. import world_bg4001_identity

#: Grep token for an attended tester's console.  Same shape as this lane's
#: other tokens (``GM_CHAT_NO_BYTES_SENT``, ``GM_LOGIN_SCENE_CONFIG_REFUSED``)
#: so one grep pattern finds all of them.
CONSOLE_TOKEN = "GM_IDENTITY_CENSUS"

#: The two families of actor this project composes into one scene generation.
#: A THIRD one exists on the wire -- the player's own character -- and it is
#: deliberately NOT modelled here: its identity comes from the character row's
#: selector pair, not from a placement table, and this module refuses to guess
#: whether the two spaces can meet.  Named so the gap is visible.
FAMILY_SCENE_CENSUS = "scene_census"
FAMILY_FIELD_MOB_ROSTER = "field_mob_roster"
FAMILY_NOT_MODELLED_PLAYER_CHARACTER = "player_character_not_modelled_here"


class IdentityCensusError(ValueError):
    """An input or a table does not have the shape this module requires.

    ``ValueError`` to match this package's house style (``gm/commands.py``'s
    ``GmCommandArgsError``, ``gm/attr_wire.py``'s ``AttrWireError``).
    """


class IdentityFamilyUnavailable(IdentityCensusError):
    """A family exists for this scene but cannot be enumerated right now.

    Separate from a shape error on purpose.  "I could not look" and "I looked
    and the table is malformed" are different facts, and a census that
    conflates them reports an empty scene as a clean one -- which is the
    single most dangerous thing a uniqueness check can do.
    """


# ---------------------------------------------------------------------------
# The scene-census registry.  Hand-written, because import-time module
# scanning is magic that fails silently when a name changes; but NOT trusted
# to be complete -- ``tests/test_gm_identity_registry_census.py`` derives the
# expected set from the package directory and turns a missing scene red.
#
# Scene 1 is the odd one and stays odd: its placement rows live in the frozen
# ``pf_login_game_server_v141`` serializer, not in a module under this
# package, so it needs a ``legacy`` handed in.  Every other family enumerates
# from committed tables with no argument at all.
# ---------------------------------------------------------------------------
_LEGACY_BACKED_SCENE_ID = population.SCENE_ID

_SCENE_CENSUS_SOURCES: dict[int, tuple[str, Callable[[], Any]]] = {
    scene2_prison_exile_tables.SCENE_N_ID: (
        "scene2_prison_exile_tables",
        scene2_prison_exile_tables.load_known_placements,
    ),
}
def _register(scene_id: int, source: str, loader: Callable[[], Any]) -> None:
    # A duplicate scene id would silently overwrite a whole family and the
    # census would report the survivor as the scene's complete population --
    # a uniqueness checker whose own registry loses a table is worse than no
    # checker.  Loud at import, deliberately, the same posture `field_mobs`
    # takes with its scene->module map.
    if scene_id in _SCENE_CENSUS_SOURCES:
        raise IdentityCensusError(
            "two census families claim scene %d: %s and %s"
            % (scene_id, _SCENE_CENSUS_SOURCES[scene_id][0], source)
        )
    _SCENE_CENSUS_SOURCES[scene_id] = (source, loader)


for _module in (
    world_bg0003_identity,
    world_bg0004_identity,
    world_bg0005_identity,
    world_bg0006_identity,
    world_bg0007_identity,
    world_bg0008_identity,
    world_bg0009_identity,
    world_bg0010_identity,
    world_bg0011_identity,
    world_bg0015_identity,
    world_bg3001_identity,
    world_bg4001_identity,
):
    _register(
        _module.SCENE_N_ID,
        _module.__name__.rsplit(".", 1)[-1],
        _module.shippable_placements,
    )
del _module


def scene_ids_with_a_census() -> tuple[int, ...]:
    """Every scene id this module can enumerate a census family for.

    Includes scene 1, which needs ``legacy`` -- being unable to look today is
    not the same as there being nothing there.
    """
    return tuple(sorted(set(_SCENE_CENSUS_SOURCES) | {_LEGACY_BACKED_SCENE_ID}))


@dataclass(frozen=True)
class IdentityClaim:
    """One actor a family would put on the wire, and the identity it carries.

    ``template`` and ``display_name`` are carried because the interesting
    question is not only "does one number have two owners" but "do the two
    owners agree about what that number IS".  They came out different the
    first time this module was run -- see :func:`scene_verdict`.
    """

    scene_id: int
    family: str
    source: str
    placement_index: int
    identity: int
    template: int
    display_name: str


def _require_scene_id(value: object) -> int:
    # bool is an int subclass and ``True`` would silently census scene 1.
    if isinstance(value, bool) or type(value) is not int:
        raise IdentityCensusError(
            "scene id must be a plain int, got %s" % type(value).__name__
        )
    if value < 0:
        raise IdentityCensusError("scene id must not be negative: %d" % value)
    return value


def _template_of(row: Any, source: str) -> int:
    # THE QUANTITY THIS RETURNS IS THE ``CONSTDATA_TH__MOBS.n_ID`` TEMPLATE,
    # and the order of these two names is what makes that true rather than
    # nearly true.  In the ``world_bgXXXX_identity`` families ``template_id``
    # is the row's index in that scene's own mined table while ``n_id`` is
    # the MOBS template -- 810 rows expose both today and ALL 810 differ, so
    # reading ``template_id`` first would compare a table index in one family
    # against a MOBS id in another and call the difference a disagreement.
    # ``scene2_prison_exile_tables`` exposes ``n_id`` only; ``field_mobs``
    # rosters and the frozen scene-1 placements expose ``template_id`` only,
    # and in both of those it already IS the MOBS id (scene 2's twelve shared
    # identities agree across the two families, which is the cross-check).
    #
    # A row with NEITHER is a shape change, and this refuses rather than
    # defaulting to 0 -- a census that silently calls every template 0 would
    # report perfect agreement between families that agree about nothing.
    for name in ("n_id", "template_id"):
        value = getattr(row, name, None)
        if type(value) is int and not isinstance(value, bool):
            return value
    raise IdentityCensusError(
        "%s row %r exposes neither n_id nor template_id as a plain int"
        % (source, getattr(row, "placement_index", "?"))
    )


def _display_name_of(row: Any, source: str) -> str:
    # AN EMPTY NAME IS DATA, A MISSING ATTRIBUTE IS A SHAPE CHANGE, and the
    # two get different treatment.  ``world_bg0004_identity`` ships rows whose
    # ``display_name`` really is ``""`` (placement 90, template 917), and a
    # census that refused those would report the scene as unreadable instead
    # of reporting the scene.  A row with NEITHER attribute is the shape
    # change, and that still refuses by name.
    for name in ("display_name", "source_name"):
        value = getattr(row, name, None)
        if type(value) is str:
            return value
    raise IdentityCensusError(
        "%s row %r exposes neither display_name nor source_name as text"
        % (source, getattr(row, "placement_index", "?"))
    )


def _claim(scene_id: int, family: str, source: str, row: Any) -> IdentityClaim:
    index = getattr(row, "placement_index", None)
    identity = getattr(row, "actor_identity", None)
    for label, value in (("placement_index", index), ("actor_identity", identity)):
        if type(value) is not int or isinstance(value, bool):
            raise IdentityCensusError(
                "%s row exposes no plain int %s" % (source, label)
            )
    return IdentityClaim(
        scene_id=scene_id,
        family=family,
        source=source,
        placement_index=index,
        identity=identity,
        template=_template_of(row, source),
        display_name=_display_name_of(row, source),
    )


def census_claims(scene_id: int, *, legacy: Any = None) -> tuple[IdentityClaim, ...]:
    """The scene-census family's claims for ``scene_id``.

    Raises :class:`IdentityFamilyUnavailable` for scene 1 with no ``legacy``,
    and for any scene id no census family in this repository addresses.
    """
    scene_id = _require_scene_id(scene_id)
    if scene_id == _LEGACY_BACKED_SCENE_ID:
        if legacy is None:
            raise IdentityFamilyUnavailable(
                "scene %d's placements live in the frozen v141 serializer; "
                "hand this function that module as `legacy` to census it"
                % scene_id
            )
        rows = population.load_port_royal_placements(legacy)
        source = "population"
    else:
        entry = _SCENE_CENSUS_SOURCES.get(scene_id)
        if entry is None:
            raise IdentityFamilyUnavailable(
                "no census family in this repository addresses scene %d "
                "(known: %s)" % (scene_id, sorted(scene_ids_with_a_census()))
            )
        source, loader = entry
        rows = loader()
    return tuple(
        _claim(scene_id, FAMILY_SCENE_CENSUS, source, row) for row in rows
    )


def roster_claims(scene_id: int) -> tuple[IdentityClaim, ...]:
    """The field-mob family's claims for ``scene_id``; empty is a real answer.

    ``field_mobs.roster_for_scene_id`` already returns an empty tuple for
    every scene this project ships no monsters for, and that is a MEASURED
    empty rather than a failure to look -- so it is passed through as one.
    """
    scene_id = _require_scene_id(scene_id)
    rows = field_mobs.roster_for_scene_id(scene_id)
    return tuple(
        _claim(scene_id, FAMILY_FIELD_MOB_ROSTER, "field_mobs", row)
        for row in rows
    )


@dataclass(frozen=True)
class DisputedIdentity:
    """One identity two families both claim, with what each says it is.

    ``same_placement`` is the whole point.  Two families naming the SAME
    placement index are describing ONE actor -- that is containment, not a
    collision.  Two families naming DIFFERENT placement indices under one
    identity in one scene generation is the real thing, and nothing in this
    repository would resolve it.
    """

    identity: int
    scene_id: int
    claims: tuple[IdentityClaim, ...]
    same_placement: bool
    templates_agree: bool


@dataclass(frozen=True)
class SceneIdentityVerdict:
    """What one scene's identity space looks like across both families."""

    scene_id: int
    census_count: int
    roster_count: int
    distinct_identities: int
    #: Two families, one identity, DIFFERENT placements.  Empty today; the
    #: test pins the emptiness so the day it stops being empty is red.
    conflicting: tuple[DisputedIdentity, ...]
    #: Two families, one identity, one placement -- the override relationship
    #: ``world_population.apply_identity_override`` is keyed on.
    shared: tuple[DisputedIdentity, ...]
    #: Roster rows whose identity NO census row in the same scene claims.
    #: The override door refuses a key its generation does not carry, so this
    #: being non-empty is a boot-time refusal waiting to happen.
    roster_identities_absent_from_census: tuple[int, ...]

    def is_unique_within_the_scene(self) -> bool:
        """True iff no identity in this scene names two different placements."""
        return not self.conflicting


def scene_verdict(scene_id: int, *, legacy: Any = None) -> SceneIdentityVerdict:
    """Census both families for one scene and compare them claim by claim.

    WHAT THE FIRST RUN OF THIS FUNCTION FOUND, recorded here because it is
    the reason the ``templates_agree`` field exists: in scene 1 the roster
    and the census DISAGREE about what four identities are.  Placement 103
    is template 97 to ``population`` and template 916 to ``field_mobs``, and
    the two carry different display names.  That is not a bug this module
    fixes or reports as one -- ``world_population.apply_identity_override``
    exists precisely to replace those census entries with the roster's bytes,
    so exactly one of the two reaches a client.  It IS worth a reader's
    attention, because an attended tester reading a server log will see one
    name where the census printed another, and until now nothing said so.
    """
    census = census_claims(scene_id, legacy=legacy)
    roster = roster_claims(scene_id)
    by_identity: dict[int, list[IdentityClaim]] = {}
    for claim in census + roster:
        by_identity.setdefault(claim.identity, []).append(claim)

    conflicting: list[DisputedIdentity] = []
    shared: list[DisputedIdentity] = []
    for identity in sorted(by_identity):
        claims = tuple(by_identity[identity])
        if len(claims) < 2:
            continue
        indices = {claim.placement_index for claim in claims}
        templates = {claim.template for claim in claims}
        disputed = DisputedIdentity(
            identity=identity,
            scene_id=claims[0].scene_id,
            claims=claims,
            same_placement=len(indices) == 1,
            templates_agree=len(templates) == 1,
        )
        (shared if disputed.same_placement else conflicting).append(disputed)

    census_identities = {claim.identity for claim in census}
    absent = tuple(
        sorted(
            claim.identity
            for claim in roster
            if claim.identity not in census_identities
        )
    )
    return SceneIdentityVerdict(
        scene_id=scene_id,
        census_count=len(census),
        roster_count=len(roster),
        distinct_identities=len(by_identity),
        conflicting=tuple(conflicting),
        shared=tuple(shared),
        roster_identities_absent_from_census=absent,
    )


def measured_identity_offset(*, legacy: Any = None) -> int:
    """The one number every family adds to a placement index, MEASURED.

    Deliberately not a constant in this file.  Each family composes its own
    identity, this reads them all back and refuses if they ever disagree --
    so the day one family renumbers, this raises by name instead of a
    hardcoded ``0x2000`` quietly disagreeing with the wire.
    """
    offsets: dict[int, list[str]] = {}
    for scene_id in scene_ids_with_a_census():
        try:
            claims = census_claims(scene_id, legacy=legacy)
        except IdentityFamilyUnavailable:
            claims = ()
        for claim in claims + roster_claims(scene_id):
            offsets.setdefault(
                claim.identity - claim.placement_index, []
            ).append("%s:%d" % (claim.source, claim.scene_id))
    if not offsets:
        raise IdentityCensusError(
            "no family could be enumerated, so no offset was measured"
        )
    if len(offsets) > 1:
        raise IdentityCensusError(
            "families disagree about the identity offset: %s"
            % {key: sorted(set(value)) for key, value in offsets.items()}
        )
    return next(iter(offsets))


@dataclass(frozen=True)
class CrossSceneAmbiguity:
    """One identity value that more than one scene hands out."""

    identity: int
    scenes: tuple[int, ...]


def cross_scene_ambiguities(*, legacy: Any = None) -> tuple[CrossSceneAmbiguity, ...]:
    """Identity values claimed in more than one scene, ascending.

    THIS IS THE UNIQUENESS ANSWER, and it is a negative one: an identity is
    NOT a key on its own.  ``(scene_id, identity)`` is.  Anything that
    resolves an identity without knowing the scene is reading an ambiguous
    number -- which is exactly the defect ``field_mobs.scene_for_scene_id``
    documents from the round a player in Bg0002 landed a hit on a Port Royal
    monster.

    A scene this module cannot enumerate is simply absent from the result;
    it is not counted as unambiguous.  Callers who need to know what was
    skipped ask :func:`scene_ids_with_a_census` and compare.
    """
    scenes_by_identity: dict[int, set[int]] = {}
    for scene_id in scene_ids_with_a_census():
        try:
            claims = census_claims(scene_id, legacy=legacy)
        except IdentityFamilyUnavailable:
            continue
        for claim in claims + roster_claims(scene_id):
            scenes_by_identity.setdefault(claim.identity, set()).add(
                claim.scene_id
            )
    return tuple(
        CrossSceneAmbiguity(identity=identity, scenes=tuple(sorted(scenes)))
        for identity, scenes in sorted(scenes_by_identity.items())
        if len(scenes) > 1
    )


def describe_scene(scene_id: int, *, legacy: Any = None) -> str:
    """One console line an attended tester can grep for.

    ASCII, one line, no caller-supplied text -- the same discipline every
    console line in this lane carries, for the same reason (the bridge
    console is cp874 and a name off a table is not this lane's text).
    """
    verdict = scene_verdict(scene_id, legacy=legacy)
    return (
        "%s scene=%d census=%d roster=%d distinct=%d conflicting=%d "
        "shared=%d roster_absent_from_census=%d unique_within_scene=%s"
        % (
            CONSOLE_TOKEN,
            verdict.scene_id,
            verdict.census_count,
            verdict.roster_count,
            verdict.distinct_identities,
            len(verdict.conflicting),
            len(verdict.shared),
            len(verdict.roster_identities_absent_from_census),
            "yes" if verdict.is_unique_within_the_scene() else "NO",
        )
    )
