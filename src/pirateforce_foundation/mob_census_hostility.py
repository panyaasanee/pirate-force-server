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
from . import mob_ledger_admission


class CensusHostilityError(ValueError):
    """~~A refusal raised by this module, never by the ones it calls.~~

    [CORRECTED, ROUND z096sw, pf-adversary on the wmomy7 diff (D5).]  That
    sentence is true about where this class is RAISED and dangerously
    misleading about what a call site must CATCH.  It reads as "this is
    the class to catch", and it is not: with a real roster,
    :func:`hostile_override_for_scene_id` raises
    ``mob_death.MobDeathContractError`` -- a class this module does not
    export -- long before anything here does.  MEASURED: a scene-2 roster
    against a bg0001 ledger refuses with ``ledger_disagrees_with_register
    ... target_not_in_ledger`` for identity ``0x2033``.

    So the accurate sentence is: this class marks refusals ORIGINATING
    here (a drifted owner-ruling literal, an unregistered refusal scene);
    it is NOT the exception surface of this module's public functions.  A
    call site inside ``runtime.py``'s census dispatch must catch broadly,
    exactly as the bg0002 branch already does -- ``v141:7440`` has no
    ``except`` and a narrow ``except CensusHostilityError`` would let the
    refusal that actually happens unwind the listener thread.
    """


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
    ledger: Any,
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

    ~~``ledger: Any = None``~~ THE DEFAULT IS GONE, ROUND y9s0xo.  It is item
    (1) of the chief's division (``pf_bridge/notes_to_chief/20260829_1924_
    CHIEF-TO-LANE-B-recompose-bg0002-three-measurements-and-the-division.md``),
    which carries COO-DECISION 2026-08-29T18:42 item 3: on a census that can
    be recomposed, a missing ledger must be refused loudly rather than
    defaulted.  A DEFAULT cannot be refused loudly -- it is the silence.  The
    keyword is required now, so a call site that forgets it gets a
    ``TypeError`` on its first boot instead of a census that heals every
    wounded monster with nothing failing and nothing logged.
    ``ledger=None`` PASSED EXPLICITLY still works and still means "compose
    without consulting HP": that is a real answer for a scene arriving before
    any combat, and :func:`describe_census_hostility` prints ``ledger=absent``
    for it.  What is refused is not saying.  MEASURED before landing: the one
    call site in this tree (``runtime.py``'s bg0002 arrival branch) already
    passes ``ledger=self.mob_combat_ledger`` explicitly, so this breaks
    nothing that exists.

    ~~And passing one that belongs to another scene is safe.~~ THAT WAS
    NEVER WRITTEN HERE AND IS WRITTEN HERE NOW BECAUSE A CALL SITE COULD
    REASONABLY HAVE ASSUMED IT.  ROUND z096sw, pf-adversary on the wmomy7
    diff (D5), MEASURED: a foreign-scene ledger is safe ONLY for an empty
    roster.  With a real one it raises
    ``mob_death.MobDeathContractError`` on the first identity the ledger
    cannot answer for -- scene-2 roster + bg0001 ledger refuses at
    ``0x2033``; scene-1 roster + Bg0002 ledger refuses at ``0x2068``.
    That is why the bg0002 census call site in ``runtime.py`` deliberately
    passes NO ledger today, and why every wounded scene-2 monster is
    therefore re-sent at its ceiling by a census recompose.

    ~~THE FIX IS DECIDED AND IS NOT IN THIS FUNCTION YET.~~  [BUILT, ROUND
    jop8ph.]  The decision -- ``pf_bridge/notes_to_chief/20260829_1849_LANE-
    B-DECISION-scene-bound-ledger-admission.md``, affirmed by ``COO-DECISION
    2026-08-29T18:42+07:00`` -- was to give ``mob_combat.CombatLedger`` its
    scene and let this lane admit or decline a ledger, three ways rather
    than two.  Both halves are now in the tree, and the admission itself
    lives in :mod:`mob_ledger_admission` rather than inline here, because
    the recompose path the COO's ruling names needs the same decision with
    a different escalation.

    SO THE SENTENCE THIS DOCSTRING USED TO END ON IS NO LONGER TRUE, and it
    is the whole point of the round: a caller no longer has to pass "a
    ledger for THIS scene or none at all".  It passes whatever ledger it
    holds.  A ledger for another scene, or one that cannot answer for part
    of this roster, is DECLINED -- not raised on -- and this function
    composes exactly as it would have with no ledger, which is the
    behaviour that was already live.  What it never does again is unwind
    the listener thread, and what a call site never has to do again is
    remember which scene its ledger came from.

    The decline is not silent: the record is on
    :func:`describe_census_hostility`'s line as ``ledger=<state>``, and a
    caller that does not pass the ledger to that line at all prints
    ``ledger=not_reported`` -- a named gap rather than a reassuring blank,
    exactly as ``override=`` already works.
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
    # The admission is asked about THE ROWS BEING COMPOSED, not about a
    # re-derivation of them.  Same rule ``census_backing_report`` states for
    # its own inputs: a check computed from a different copy of the thing it
    # is checking can agree with itself while the composition raises.
    # THE REGISTER GOES WITH IT, ROUND jop8ph-2 (pf-adversary D1).  This
    # function already holds the register the composer is about to use, and
    # two of the four refusals ``repopulation_entries`` can raise compare the
    # ledger against exactly that register.  Passing it is what makes "safe
    # to hand any ledger" true rather than merely claimed: without it this
    # call forwarded a ledger that was about to raise, having just printed
    # ``admitted=yes covered=12/12``.
    admitted = mob_ledger_admission.ledger_for_scene(
        scene_id, ledger, roster=roster, register=register,
    )
    return mob_death.full_roster_override(
        legacy, roster, register, ledger=admitted,
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

    ROUND z096sw, TWO FIELDS ADDED AFTER pf-adversary READ THIS FUNCTION
    (on the wmomy7 diff), BOTH MEASURED RATHER THAN ARGUED:

    ``refused_count`` (D11).  Nothing at boot could tell whether the
    owner-refusal filter was still doing anything.  A regeneration that
    dropped placements 92-96 from the generated table outright would
    produce a byte-identical console line and identical pins to one where
    the filter removed them -- so the day the filter stops mattering, or
    starts mattering more, looks exactly like every other day.  It is
    reported, not enforced: this function does not decide what the number
    should be.

    ``vacuous`` (D6).  ``fully_backed`` is ``True`` for a roster with ZERO
    rows, which is a vacuous truth and a trap for any caller that gates on
    it -- "every monster I ship has a body" is not the same sentence when
    you ship none.  ``fully_backed`` keeps its meaning (a scene with a
    genuinely empty table is fully backed, and that is a real answer);
    ``vacuous`` is what lets a caller tell the two apart.

    NOT FIXED HERE, AND NAMED SO IT IS NOT MISTAKEN FOR FIXED (D6, first
    half): this joins on BARE WIRE IDENTITY.  ``census_identities`` is not
    checked against ``scene_id``, and ``field_mobs`` says in its own words
    that the identity rule carries no scene component, so handing this one
    scene's id and another scene's census reports some of the first
    scene's monsters "backed" by bodies that are not theirs.  Measured:
    ``census_backing_report(1, <the Bg0002 census>)`` calls two of Port
    Royal's four backed by a census containing zero bg0001 actors.  The
    hazard is unrealised today (zero identity collisions between the two
    live scenes) and the fix belongs with the scene-component question
    already open in this lane's letters, not in a report function.
    """
    roster = field_mobs.roster_for_scene_id(scene_id)
    census_set = set(census_identities)
    roster_ids = tuple(mob.actor_identity for mob in roster)
    unbacked = tuple(sorted(i for i in roster_ids if i not in census_set))
    backed = tuple(sorted(i for i in roster_ids if i in census_set))
    scene = field_mobs.scene_for_scene_id(scene_id)
    refused = (
        field_mobs.owner_refused_placements(scene) if scene else ()
    )
    return {
        "scene_id": scene_id,
        "scene": scene,
        "roster_count": len(roster_ids),
        "census_count": len(census_set),
        "backed": backed,
        "backed_count": len(backed),
        "unbacked": unbacked,
        "unbacked_count": len(unbacked),
        "fully_backed": not unbacked,
        "vacuous": not roster_ids,
        "refused": refused,
        "refused_count": len(refused),
    }


_LEDGER_NOT_REPORTED = object()


def describe_census_hostility(
    scene_id: int,
    census_identities: Any,
    *,
    override: Any = None,
    ledger: Any = _LEDGER_NOT_REPORTED,
) -> tuple[str, ...]:
    """One ASCII console line for :func:`census_backing_report` (G-OBS).

    Plain ASCII, no escaping, so it prints on the bridge's cp874 console.
    One line, in the same shape as
    ``mob_death.describe_roster_override_coverage``, so a boot's console
    can be grepped for both without a parser.

    Printed unconditionally by a wiring call site, never inside an ``if``:
    ``unbacked=0/0`` for a scene with no monsters is a real answer, and
    "no line at all" is the state GT-084 already misread once.

    ``override=`` EXISTS BECAUSE THIS LINE WAS GREEN WHETHER OR NOT A
    SINGLE HOSTILE BYTE REACHED THE WIRE.  ROUND z096sw, pf-adversary on
    the wmomy7 diff (D2), MEASURED: the hostile splice does not change a
    census's identity MEMBERSHIP -- this round's own tests assert that --
    and membership is the only thing this line reads.  Before, after and
    with a no-op splice, it printed the identical
    ``roster=12 backed=12 unbacked=none``, while the pc went 17740 ->
    17896 bytes only in the real case.  Worse, ``runtime.py`` applies the
    splice inside ``if override:``, so any state that empties the override
    (lane A renaming the scene folder, the whole roster refused) leaves
    all 97 actors at faction 0 and still prints the greppable all-clear.
    The sibling bg0001 branch does not have this hole: it prints
    ``mob_death.describe_roster_override_coverage``, which is computed
    FROM the override dict and would show ``0``.

    So the number of identities the override actually carries is reported
    here, and a caller that does not supply it prints
    ``override=not_reported`` -- a named gap, visible at boot, rather than
    a reassuring line.  It is deliberately NOT defaulted to 0: "nobody
    told me" and "the override was empty" are the two states this whole
    finding is about, and collapsing them here would rebuild the defect.

    ``refused=`` is the D11 half: the count of placements the owner's
    ruling keeps out of this scene's roster, so a boot can tell whether
    the filter is still doing anything.

    ``ledger=`` IS THE jop8ph HALF, and it is on THIS line rather than on a
    new one on purpose.  Round jop8ph made
    :func:`hostile_override_for_scene_id` safe to hand any ledger, which
    means a call site can now pass one -- and the whole value of that is
    lost if a boot cannot tell whether the ledger it passed was CONSULTED.
    "The HP in this census came from the live ledger" and "the ledger was
    declined and every monster is at its ceiling" are the two states this
    round exists to separate, and they must not look alike in a log.

    A caller that does not pass ``ledger=`` prints ``ledger=not_reported``,
    the same named gap ``override=`` uses.  It is NOT defaulted to
    ``absent``: "I did not tell you" and "there was none" are different
    facts about different people, and a call site that forgot the keyword
    would otherwise print a line accusing itself of a defect it may not
    have.  Passing ``ledger=None`` explicitly is what prints ``absent``.

    The state names come from :mod:`mob_ledger_admission` unchanged, so one
    grep answers the question on either line.

    WHAT THIS LINE DOES NOT DO, SAID PLAINLY: it does not observe the
    decision :func:`hostile_override_for_scene_id` actually made.  It asks
    the same question again, and it resolves the roster a second time to do
    so, because a ``runtime.py`` call site holds the scene id and the
    ledger and never sees the roster in between.  The two answers agree
    because ``field_mobs.roster_for_scene_id`` is a pure function of
    committed tables -- there is no clock, no file read and no session
    state in it -- and ``tests/test_mob_ledger_admission.py`` pins that
    agreement rather than assuming it.  A future roster that depends on
    session state would break that equivalence silently, and this
    paragraph is where the next reader finds out why.
    """
    report = census_backing_report(scene_id, census_identities)
    unbacked = (
        "none" if not report["unbacked"]
        else ",".join("0x%X" % i for i in report["unbacked"])
    )
    if override is None:
        carried = "not_reported"
    else:
        try:
            carried = "%d" % len(override)
        except Exception:
            carried = "unreadable"
    if ledger is _LEDGER_NOT_REPORTED:
        admission = "not_reported"
    else:
        try:
            admission = mob_ledger_admission.admit_ledger(
                scene_id, ledger)["state"]
        except Exception:  # noqa: BLE001 - a console line never kills a boot
            admission = "undescribable"
    return (
        "MOB_CENSUS_HOSTILITY scene_id=%d scene=%s roster=%d backed=%d "
        "unbacked=%s refused=%d override=%s ledger=%s" % (
            report["scene_id"],
            report["scene"] if report["scene"] else "?",
            report["roster_count"],
            report["backed_count"],
            unbacked,
            report["refused_count"],
            carried,
            admission,
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

    ~~A guard nobody has watched fail is not a guard, so
    ``tests/test_mob_census_hostility.py`` breaks the join on synthetic
    data and requires this to refuse, rather than only running it against
    the two real scenes that already agree.~~

    [WITHDRAWN AS WRITTEN, ROUND z096sw, BY pf-adversary ON THE wmomy7 DIFF
    (D3).]  Line-traced: the two refusal branches below that read the
    SOURCE side -- "source is not a list" and "source row has wrong shape"
    -- had NEVER EXECUTED, and both survived being replaced with ``if
    False:`` against the whole suite.  What the tests actually broke was
    the LANE side (they mutate ``field_mobs.OWNER_REFUSED_PLACEMENTS`` in
    place); the sentence above claimed the source side had been driven and
    it had not.  Both branches are driven on synthetic data now, and the
    sentence is struck rather than deleted so the letter that quoted it can
    be corrected against something.

    THE SCENE SET IS THE OTHER HALF OF THE JOIN, AND IT WAS MISSING
    (pf-adversary, same review, D1 -- MEASURED end to end, not argued).
    This used to iterate ``_OWNER_RULING_SOURCE`` alone, so a scene named
    in the refusal literal with NO source entry was filtered at
    ``load_roster`` and joined against nothing: a bogus
    ``OWNER_REFUSED_PLACEMENTS['Bg0003']`` dropped three of that scene's
    four monsters from the ledger, the AI register and the census override
    while this guard returned clean.  A guard that only checks the scenes
    someone remembered to register is the silent-drift shape this whole
    literal-plus-guard split exists to refuse, pointed at itself.  The
    union is walked now, and a refusal literal with no source to justify it
    is itself a refusal.
    """
    import importlib

    literal_scenes = set(field_mobs.OWNER_REFUSED_PLACEMENTS)
    unsourced = sorted(literal_scenes - set(_OWNER_RULING_SOURCE))
    if unsourced:
        raise CensusHostilityError(
            "this lane refuses placements for scene(s) %s with no owner-"
            "ruling source registered in _OWNER_RULING_SOURCE: every "
            "refusal must be traceable to a table that carries the owner's "
            "own reason string, or it is this lane deciding which monsters "
            "a player meets" % (unsourced,)
        )

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
        source_reasons = set()
        for row in rows:
            if type(row) is not tuple or len(row) < 3:
                raise CensusHostilityError(
                    "owner-ruling source row for scene %r has wrong shape"
                    % (scene,)
                )
            index, reason = row[0], row[-1]
            if type(reason) is str and _OWNER_RULING_MARK in reason:
                source.add(index)
                source_reasons.add(reason)
        # THE REASON STRING IS CHECKED TOO, ROUND z096sw (pf-adversary on
        # the wmomy7 diff, D4 -- MEASURED).  ``OWNER_REFUSAL_REASON`` was a
        # WRITE-ONLY literal: one occurrence repo-wide, its own definition,
        # no reader in src/, tools/, tests/ or docs/, and replacing its
        # value with nonsense survived the whole suite.  It is a second
        # hand-copy of the source table's own reason string sitting beside
        # a literal this lane went to some trouble to guard, so it is
        # joined here like the indices are.  A ruling whose REASON changed
        # (the block's meaning finally proven, say) is exactly the day this
        # lane must stop copying the old sentence forward.
        declared_reason = field_mobs.OWNER_REFUSAL_REASON.get(scene)
        if source and source_reasons != {declared_reason}:
            raise CensusHostilityError(
                "owner-refusal REASON drift for scene %r: this lane records "
                "%r, the source table's own ruling rows carry %s -- "
                "reconcile field_mobs.OWNER_REFUSAL_REASON with %s.%s "
                "before shipping" % (
                    scene, declared_reason, sorted(source_reasons),
                    module_name, attribute,
                )
            )
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
