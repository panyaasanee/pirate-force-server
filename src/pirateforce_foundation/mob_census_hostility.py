"""LANE-B: the hostile-faction census override, scene by scene.

ROUND wmomy7.  ``world_population_bg0002.py``'s module docstring names the
hole this module fills, in its own words: "There is also no faction/hostile
bit on ANY entry here ... A caller that wants monsters 27-35 hostile owes
them the same override splice lane B's hostile-monster module and
``mob_death.py`` already use for bg0001, generalized to this scene - not
built here."  This is that generalization.

WHAT WAS ALREADY BUILT, AND IS NOT REBUILT HERE.  ``mob_death
.full_roster_override`` already turns a roster into identity -> hostile
body bytes, and is already scene-agnostic: it takes whatever roster it is
handed.  ``mob_death.roster_override_coverage`` already measures which of
those identities a built census actually carries.  ``field_mobs
.roster_for_scene_id`` (round k3qe9q) already resolves a scene id to that
scene's rows.  Every one of those is called, none is reimplemented.  What
did not exist is the SHAPE a ``runtime.py`` call site can use: the bg0001
branch of the census dispatcher spells the override out over four lines
with a hardcoded no-argument ``field_mobs.load_roster()``, and the Bg0002
branch has no override at all.  :func:`hostile_override_for_scene_id` is
one call that works for either scene, so the wiring ask this round hands
the chief is one line rather than a transcription.

WHAT THIS MODULE ADDS THAT DID NOT EXIST ANYWHERE: the census-backing
check.  A roster identity with no body in the census it is spliced into is
not a cosmetic gap -- the combat ledger opens on the roster, so such a row
is a monster the server will accept a strike against and no client has
ever been sent.  That is a defect that reads as green from either side
alone and only appears when the two are compared, which is what
:func:`census_backing_report` does.

NONCLAIMS.  This does not decide whether a player SEES a red monster.
``RE-067`` and ``RE-068`` both closed BOUNDED NEGATIVE on what drives an
actor name's colour -- nobody has identified the mechanism -- and
``GT-032``'s passing red-name result was measured on ``0x2001`` ("Navy
Transfer"), which is not a member of any field-mob roster.  What this
module claims is at the wire layer only: the bytes a census sends for a
roster identity carry the same five tagged faction bytes
``field_mobs.hostile_actor_entry`` already produces, instead of the
faction-0 body ``world_population_bg0002`` builds by default.  Whether
that is the thing a player's eye reacts to is ``GT-084``/``RIDER-084-A``'s
question, and this module does not pre-empt it.

This module reads no files and is import-light on purpose: everything it
touches is a ``.py`` in this package, so it behaves identically inside
``tools/build_foundation_release.py``'s archive (which ships ``*.py``
only) as it does in a source tree.  That is a live constraint, not a
hypothetical: round k3qe9q shipped a guard that read a JSON file and
would have killed a boot from the archive.
"""

from __future__ import annotations

from typing import Any

from . import field_mobs
from . import mob_death


class CensusHostilityError(ValueError):
    """A refusal raised by this module, never by the ones it calls."""


# Scene folder -> the module whose table carries the OWNER's own ruling
# about which placements may be shipped.  Only scenes with a ruling need an
# entry; a scene with no entry has nothing to disagree with.
#
# Imported lazily inside the guard rather than at module import, so this
# module stays cheap for the census path that only wants the override.
_OWNER_RULING_SOURCE = {
    'Bg0002': ('scene2_prison_exile_tables', 'UNRESOLVED_PLACEMENTS'),
}

# The substring that marks an owner ruling (as opposed to a row the mining
# rule simply could not read).  The source table carries both kinds in one
# list, and only this kind is a ruling this lane must obey.
_OWNER_RULING_MARK = 'owner_says_do_not_place'


def hostile_override_for_scene_id(
    legacy: Any,
    scene_id: int,
    register: Any,
    *,
    ledger: Any = None,
) -> dict[int, bytes]:
    """Identity -> hostile body bytes for the monsters standing in ``scene_id``.

    THE ONE LINE A CENSUS CALL SITE NEEDS.  Equivalent to what the bg0001
    branch of ``runtime.py``'s census dispatcher already spells out, except
    that the roster follows the scene the character is actually in instead
    of being ``field_mobs.load_roster()`` with no argument -- which is
    bg0001's roster in every scene, the defect round k3qe9q measured.

    An empty dict is a real answer and a safe one: a scene this lane ships
    no monsters for overrides nothing, and
    ``_apply_mob_death_census_override`` returns the generation untouched
    for a falsy override.  Callers must NOT read ``{}`` as "fall back to
    the default roster" -- that reading is the bug one layer down, and
    :func:`field_mobs.roster_for_scene_id` documents the same refusal.

    ``ledger`` is passed straight through and matters: without it a census
    rebuild heals every wounded monster back to its ceiling, which is the
    exact failure MOB-DEATH-001's wiring note called out.
    """
    # ~~if not roster: return {}~~ REMOVED, self-mutation sweep this round
    # (M2): that early return was DEAD CODE.  ``full_roster_override`` over
    # an empty roster already returns ``{}`` -- measured, not assumed -- so
    # the branch could be deleted with the whole suite still green, which
    # means it was never the thing making the empty-scene case safe.  The
    # test below it (``test_an_unaddressed_scene_overrides_nothing...``) now
    # exercises the REAL composer for that case instead of a shortcut around
    # it, which is what it was supposed to be pinning all along.
    roster = field_mobs.roster_for_scene_id(scene_id)
    return mob_death.full_roster_override(
        legacy, roster, register, ledger=ledger,
    )


def census_backing_report(
    scene_id: int,
    census_identities: Any,
) -> dict[str, Any]:
    """Does every monster this lane ships in ``scene_id`` have a census body?

    ``census_identities`` must be what the caller's build actually produced
    (``generation.actor_identities``), never a re-derivation of what it
    ought to contain -- a report computed from the same assumption it is
    meant to test cannot fail.

    ``unbacked`` is the list that matters.  A roster identity absent from
    the census is a monster the combat ledger will accept a strike against
    and no client was ever sent a body for.  It is not visible from the
    roster alone (the rows are well-formed) nor from the census alone (the
    bodies it sends are all real); only the comparison shows it.

    MEASURED, round wmomy7, before this round's owner-refusal filter
    landed: scene 2 shipped 17 roster rows against a 97-actor census, and
    five of them (``0x205D``-``0x2061``, placements 92-96) had no census
    body -- the five the owner had ruled "do not place".  After the filter:
    12 rows, ``unbacked`` empty.
    """
    roster = field_mobs.roster_for_scene_id(scene_id)
    census_set = set(census_identities)
    roster_ids = tuple(mob.actor_identity for mob in roster)
    unbacked = tuple(sorted(i for i in roster_ids if i not in census_set))
    backed = tuple(sorted(i for i in roster_ids if i in census_set))
    return {
        "scene_id": scene_id,
        "scene": field_mobs.scene_for_scene_id(scene_id),
        "roster_count": len(roster_ids),
        "census_count": len(census_set),
        "backed": backed,
        "backed_count": len(backed),
        "unbacked": unbacked,
        "unbacked_count": len(unbacked),
        "fully_backed": not unbacked,
    }


def describe_census_hostility(
    scene_id: int,
    census_identities: Any,
) -> tuple[str, ...]:
    """One ASCII console line for :func:`census_backing_report` (G-OBS).

    Plain ASCII, no escaping, so it prints on the bridge's cp874 console.
    One line, in the same shape as
    ``mob_death.describe_roster_override_coverage``, so a boot's console
    can be grepped for both without a parser.

    Printed unconditionally by a wiring call site, never inside an ``if``:
    ``unbacked=0/0`` for a scene with no monsters is a real answer, and
    "no line at all" is the state GT-084 already misread once.
    """
    report = census_backing_report(scene_id, census_identities)
    unbacked = (
        "none" if not report["unbacked"]
        else ",".join("0x%X" % i for i in report["unbacked"])
    )
    return (
        "MOB_CENSUS_HOSTILITY scene_id=%d scene=%s roster=%d backed=%d "
        "unbacked=%s" % (
            report["scene_id"],
            report["scene"] if report["scene"] else "?",
            report["roster_count"],
            report["backed_count"],
            unbacked,
        ),
    )


def assert_owner_refusals_match_scene_source() -> None:
    """Refuse if this lane's owner-refusal literal has drifted from its source.

    ``field_mobs.OWNER_REFUSED_PLACEMENTS`` is a literal on the hot roster
    path, deliberately not joined against the scene source table at load
    time.  This is the other half of that decision: the join runs here, in
    a function the suite calls, so a source table that gains or loses an
    owner ruling turns a test red instead of silently changing which
    monsters a player meets.

    A guard nobody has watched fail is not a guard, so
    ``tests/test_mob_census_hostility.py`` breaks the join on synthetic
    data and requires this to refuse, rather than only running it against
    the two real scenes that already agree.
    """
    import importlib

    for scene, (module_name, attribute) in _OWNER_RULING_SOURCE.items():
        module = importlib.import_module(
            "%s.%s" % (__package__, module_name)
        )
        rows = getattr(module, attribute, None)
        if type(rows) is not list:
            raise CensusHostilityError(
                "owner-ruling source %s.%s for scene %r is not a list"
                % (module_name, attribute, scene)
            )
        source = set()
        for row in rows:
            if type(row) is not tuple or len(row) < 3:
                raise CensusHostilityError(
                    "owner-ruling source row for scene %r has wrong shape"
                    % (scene,)
                )
            index, reason = row[0], row[-1]
            if type(reason) is str and _OWNER_RULING_MARK in reason:
                source.add(index)
        declared = set(field_mobs.owner_refused_placements(scene))
        if declared != source:
            raise CensusHostilityError(
                "owner-refusal drift for scene %r: this lane refuses %s, "
                "the source table's own ruling names %s -- reconcile "
                "field_mobs.OWNER_REFUSED_PLACEMENTS with %s.%s before "
                "shipping" % (
                    scene, sorted(declared), sorted(source),
                    module_name, attribute,
                )
            )
