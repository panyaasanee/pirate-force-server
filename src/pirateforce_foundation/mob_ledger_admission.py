"""LANE-B: may THIS combat ledger be consulted while composing THAT scene?

ROUND jop8ph.  This is the build half of the decision letter
``pf_bridge/notes_to_chief/20260829_1849_LANE-B-DECISION-scene-bound-ledger-
admission.md``, affirmed by ``COO-DECISION 2026-08-29T18:42+07:00``
(census race window accepted until recompose; the recompose path must never
take a silent ``ledger=None``).

WHAT WAS BROKEN.  A census recompose that re-sends a scene's actors reads
each monster's live HP out of the combat ledger, so a monster a player has
already wounded is re-sent wounded rather than at its ceiling.  That is the
whole of BUILD-005's promise at the wire layer.  It works in bg0001 and it
does not happen in Bg0002, for one reason: ``runtime.py``'s Bg0002 census
branch deliberately passes NO ledger, because passing the session's ledger
(bg0001's, opened before the session had a scene) RAISES.  MEASURED, round
z096sw: ``mob_death._balance_in`` refuses ``target_not_in_ledger`` at the
first identity the foreign ledger cannot answer for -- ``0x2033`` for a
scene-2 roster against a bg0001 ledger, ``0x2068`` the other way round --
and that refusal is raised inside a listener thread's census dispatch.

So the call site had two options and both were bad: pass the ledger and risk
unwinding the listener (a player logging into Prison Exile Island then gets
ZERO actors, because that branch is fail-closed with no frozen fallback),
or pass nothing and heal every wounded monster on the next recompose.  Ticket
1600 chose the second, correctly, for what it could measure.

WHAT THIS MODULE ADDS: the third option.  A caller hands over whatever ledger
it has, and gets back an ANSWER instead of an exception -- one of a small set
of named states, every one of them safe to act on, none of them silent.  The
ledger is forwarded only when it demonstrably covers the roster being
composed.  With this in place the wiring ask is one keyword
(``ledger=self.mob_combat_ledger``) that is safe on every path, in every
scene, including the ones this project has not built yet.

TWO SIGNALS, AND THEY ARE NOT EQUALS.

  * The DECLARATION is ``CombatLedger.scene`` (round jop8ph, this lane).  A
    ledger that names a different scene than the one being composed is
    declined on that alone -- an explicit disagreement is never overruled by
    a membership coincidence.
  * The GROUND TRUTH is CONTAINMENT: does the ledger carry a row for every
    identity in this scene's roster?  That, exactly, is the precondition
    ``mob_death.repopulation_entries`` raises on.  Nothing else is.

Containment is checked even when the scenes agree, and that is not
belt-and-braces.  A ledger opened for ``Bg0002`` BEFORE this lane's
owner-refusal filter changed which placements ship carries a different
identity set than today's roster for the same scene, and would raise with
both labels reading ``Bg0002``.  The label is a claim; the membership is the
thing the next line of code will actually do.

WHAT IT REFUSES TO DO.  It never raises for a ledger it dislikes -- a
census composer's job is to send the scene, and refusing to compose is
strictly worse for the player than composing with monsters at full HP.  It
never treats "nobody handed me a ledger" as "there was nothing to consult":
that state has a name (:data:`STATE_ABSENT`), it reaches the console, and on
the recompose path :func:`require_ledger_for_recompose` marks it FATAL per
the COO's ruling.  And it never reports ``admitted`` as evidence on its own:
an empty roster admits anything (it is missing nothing because nothing was
asked of it), so every record carries :data:`vacuous <admit_ledger>` beside
it, the same way ``mob_census_hostility.census_backing_report`` had to learn
to say ``vacuous`` next to ``fully_backed``.

NONCLAIMS.  This decides which HP numbers a census carries.  It does not
decide whether a player SEES a wounded monster stay wounded -- that is
``GT-084``/``RIDER-084-A``'s attended question, at a layer no module here can
observe.  It is not a ledger LIFETIME either: nothing here rebuilds a ledger
when a player crosses a travel gate, so a ledger for the scene behind them is
correctly DECLINED by this module and correctly still stale.  Declining is
the safe half; rebuilding is the chief's rebuild point, still open.

This module reads no files and imports only siblings, so it behaves
identically inside ``tools/build_foundation_release.py``'s ``*.py``-only
archive as it does in a source tree.
"""

from __future__ import annotations

from typing import Any

from . import field_mobs


# Convention markers only; nothing in this tree branches on them.  There is
# no flag, no scenario and no opt-in bit anywhere in this module: the lane
# charter's first sentence is that what it writes must work without one.
production_allowed = True
test_only = False

MOB_LEDGER_ADMISSION_LANE = "B_COMBAT"


# The ledger was consulted.  Both signals agree and containment holds.
STATE_SAME_SCENE = "same_scene"
# The ledger names a different scene than the one being composed.  Declined
# on the declaration alone, whatever its membership happens to look like.
STATE_OTHER_SCENE = "other_scene"
# The ledger names this scene and CANNOT answer for part of its roster.  This
# is the state that would have raised.  Declined, loudly, never raised.
STATE_SAME_SCENE_INCOMPLETE = "same_scene_incomplete"
# The ledger names no scene (the shape every ledger in this tree had before
# round jop8ph) and covers the roster.  Consulted, on containment alone.
STATE_UNSCOPED_COVERS_ROSTER = "unscoped_covers_roster"
# The ledger names no scene and cannot answer for part of the roster.  This
# is what ``runtime.py``'s session ledger looks like from inside Bg0002
# today.  Declined.
STATE_UNSCOPED_INCOMPLETE = "unscoped_incomplete"
# Nobody handed one over.  A named state, not a default.
STATE_ABSENT = "absent"
# Something was handed over that does not answer like a ledger.  Declined
# without raising, because a census composer that dies on a malformed
# argument sends a player an empty world.
STATE_UNREADABLE = "ledger_unreadable"

ADMITTING_STATES = (STATE_SAME_SCENE, STATE_UNSCOPED_COVERS_ROSTER)

# What the recompose path must print when it was handed no ledger at all.
# The COO's 18:42 ruling allows a raise OR a FATAL line; this lane takes the
# line, for the reason the decision letter gives at length -- a fail-closed
# census is a player standing in an empty world, which is worse than the
# defect being reported.  "Refuse" here means refuse to be silent.
FATAL_TOKEN = "MOB_LEDGER_ADMISSION_FATAL"


def admit_ledger(
    scene_id: int,
    ledger: Any,
    *,
    roster: Any = None,
) -> dict[str, Any]:
    """Decide, without raising, whether ``ledger`` speaks for ``scene_id``.

    Returns a record, never a bare bool, because every caller so far has
    needed the REASON as well as the verdict: the census path prints it, the
    recompose path escalates one particular reason to FATAL, and a test can
    tell "declined because it is another scene's" from "declined because it
    is this scene's and out of date" -- two states that would be one bit
    apart in a bool and are one code change apart in what the reader must do
    next.

    ``roster`` is an override for tests and for a caller that has already
    resolved the rows; by default the scene's own roster is loaded.  Passing
    the rows the caller is ACTUALLY composing is the more honest call: this
    module then answers about that composition rather than about a
    re-derivation of it.

    ``vacuous`` is true when the roster has no rows.  ``admitted`` is then
    true for any readable ledger and means nothing at all -- containment
    over an empty set is vacuous truth, and a caller that gates on
    ``admitted`` alone will read a town with no monsters as proof its ledger
    is the right one.  It is reported rather than folded into ``admitted``
    for the same reason ``census_backing_report`` reports ``vacuous`` beside
    ``fully_backed``: the two sentences differ and only the caller knows
    which one it needs.
    """
    scene = field_mobs.scene_for_scene_id(scene_id)
    rows = (
        field_mobs.roster_for_scene_id(scene_id) if roster is None else roster
    )
    wanted = tuple(mob.actor_identity for mob in rows)

    record: dict[str, Any] = {
        "scene_id": scene_id,
        "scene": scene,
        "ledger_scene": None,
        "roster_count": len(wanted),
        "covered_count": 0,
        "missing": (),
        "vacuous": not wanted,
        # WHETHER THE MISSING LIST WAS EVER COMPUTED.  Without this flag an
        # absent or unreadable ledger reports ``missing=()`` -- which is the
        # same value a fully covering ledger reports, and the console line
        # printed ``covered=0/12 missing=none`` for it: two fields that
        # contradict each other, and the reassuring one is the lie.  Nothing
        # was measured on those paths, and the line says so now.
        "missing_measured": False,
        "state": STATE_ABSENT,
        "admitted": False,
        "ledger": None,
    }
    if ledger is None:
        return record

    try:
        held = set(ledger.identities())
        ledger_scene = ledger.scene
    except Exception:  # noqa: BLE001 - see STATE_UNREADABLE
        # Deliberately broad, and deliberately not re-raised.  Anything that
        # does not answer ``identities()``/``scene`` is not a ledger this
        # module can reason about, and the caller's next line composes a
        # world for a player who is already logged in.
        record["state"] = STATE_UNREADABLE
        return record

    if ledger_scene is not None and type(ledger_scene) is not str:
        record["state"] = STATE_UNREADABLE
        return record

    missing = tuple(sorted(i for i in wanted if i not in held))
    covered = tuple(i for i in wanted if i in held)
    record["ledger_scene"] = ledger_scene
    record["missing"] = missing
    record["missing_measured"] = True
    record["covered_count"] = len(covered)

    both_named = ledger_scene is not None and scene is not None
    if both_named and ledger_scene != scene:
        # THE DECLARATION WINS HERE, and it wins even when containment would
        # have passed.  Two scenes that happen to share every identity in one
        # of their rosters (identities carry no scene component -- field_mobs
        # says so in its own words, and 0x2068/0x206A are in fact in both
        # live scenes) are still two scenes, and the HP in a ledger for the
        # other one is the HP of a different monster with the same number.
        record["state"] = STATE_OTHER_SCENE
        return record

    if missing:
        record["state"] = (
            STATE_UNSCOPED_INCOMPLETE if ledger_scene is None
            else STATE_SAME_SCENE_INCOMPLETE
        )
        return record

    record["state"] = (
        STATE_UNSCOPED_COVERS_ROSTER if ledger_scene is None
        else STATE_SAME_SCENE
    )
    record["admitted"] = True
    record["ledger"] = ledger
    return record


def ledger_for_scene(
    scene_id: int,
    ledger: Any,
    *,
    roster: Any = None,
) -> Any:
    """The ledger a composer for ``scene_id`` may safely use, or ``None``.

    The one-expression shape for a call site that does not want the record.
    ``None`` here means "compose without consulting HP", which is what every
    ledger-less path in this tree already does.
    """
    return admit_ledger(scene_id, ledger, roster=roster)["ledger"]


def describe_ledger_admission(record: Any) -> tuple[str, ...]:
    """One ASCII console line for an admission record (G-OBS).

    Plain ASCII, one line, in the same shape as the lane's other console
    lines so a boot log can be grepped for all of them without a parser.  It
    prints ``missing=none`` rather than omitting the field, because a field
    that appears only when something is wrong makes "no line" and "nothing
    wrong" the same observation -- the exact misreading ``GT-084`` made once
    and this lane has now written into three modules.

    ``covered=`` is the number of roster identities the ledger can actually
    answer for.  It is the measured half of the line: ``state=`` reports what
    was decided, ``covered=N/M`` reports what was true.  A mutant that
    decides by scene label alone and never looks at membership prints
    ``covered=0`` and is caught by the pins in
    ``tests/test_mob_ledger_admission.py``.
    """
    try:
        scene = record["scene"] or "?"
        # "there was no ledger", "the ledger named no scene" and "the ledger
        # could not be read" all had ``ledger_scene=None`` in the record and
        # would all have printed ``ledger_scene=none``.  ``state=`` already
        # tells them apart, but a field that reads as an answer in all three
        # cases invites a reader to stop at it.
        if record["state"] == STATE_ABSENT:
            ledger_scene = "no_ledger"
        elif record["state"] == STATE_UNREADABLE:
            ledger_scene = "unreadable"
        else:
            ledger_scene = record["ledger_scene"] or "unscoped"
        if not record["missing_measured"]:
            # Nothing was read, so "none missing" is not a finding -- it is
            # the absence of one.  ``covered=0/12 missing=none`` was the
            # first draft of this line and it contradicted itself.
            missing = "not_measured"
        elif not record["missing"]:
            missing = "none"
        else:
            missing = ",".join("0x%X" % i for i in record["missing"])
        return (
            "MOB_LEDGER_ADMISSION scene_id=%d scene=%s ledger_scene=%s "
            "state=%s admitted=%s covered=%d/%d missing=%s vacuous=%s" % (
                record["scene_id"],
                scene,
                ledger_scene,
                record["state"],
                "yes" if record["admitted"] else "no",
                record["covered_count"],
                record["roster_count"],
                missing,
                "yes" if record["vacuous"] else "no",
            ),
        )
    except Exception:  # noqa: BLE001 - a console line never kills a boot
        return ("MOB_LEDGER_ADMISSION state=undescribable",)


def require_ledger_for_recompose(
    scene_id: int,
    ledger: Any,
    *,
    roster: Any = None,
) -> dict[str, Any]:
    """The admission record for a RECOMPOSE, where absence is fatal to report.

    THE DIFFERENCE FROM :func:`admit_ledger` IS ONE SENTENCE, AND IT IS THE
    COO'S (2026-08-29T18:42+07:00, item 3): on the recompose path a missing
    ledger must be refused loudly -- "raise or log at FATAL, not silently".
    A recompose is by definition a re-send of actors the player is already
    looking at, so a recompose with no ledger is the healing bug happening,
    not a possibility of it.

    THIS LANE TAKES THE LINE, NOT THE RAISE, and records why so the choice
    can be overruled cheaply: the recompose call sites live inside
    ``runtime.py``'s census dispatch, where a raise unwinds the listener
    thread and the player gets an empty world.  Giving up "one monster shows
    full HP" to get "the world is empty" costs more than the defect does.
    The record carries ``fatal`` and :func:`describe_recompose_admission`
    prints a line beginning ``MOB_LEDGER_ADMISSION_FATAL``, which is
    greppable and cannot be confused with the ordinary line.

    Every other state is passed through unchanged: a foreign or incomplete
    ledger on a recompose is the SAME declined-and-said-so as anywhere else,
    because the caller did its part and the ledger simply is not the right
    one.
    """
    record = admit_ledger(scene_id, ledger, roster=roster)
    record["fatal"] = record["state"] == STATE_ABSENT
    return record


def describe_recompose_admission(record: Any) -> tuple[str, ...]:
    """Console lines for :func:`require_ledger_for_recompose`.

    Always the ordinary line; plus the FATAL line when, and only when, the
    recompose was handed no ledger at all.  Two lines rather than a
    different one line, so the ordinary grep a tester already runs keeps
    matching on this path too.
    """
    lines = describe_ledger_admission(record)
    try:
        fatal = bool(record["fatal"])
    except Exception:  # noqa: BLE001 - a console line never kills a boot
        fatal = False
    if not fatal:
        return lines
    return lines + (
        "%s scene_id=%s reason=no_ledger_passed_to_recompose "
        "effect=every_wounded_monster_resent_at_its_ceiling" % (
            FATAL_TOKEN, record.get("scene_id", "?"),
        ),
    )
