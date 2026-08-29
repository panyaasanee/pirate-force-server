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
  * The GROUND TRUTH is what the composer will actually refuse on.
    ~~CONTAINMENT: does the ledger carry a row for every identity in this
    scene's roster?  That, exactly, is the precondition
    ``mob_death.repopulation_entries`` raises on.  Nothing else is.~~

THAT LAST SENTENCE WAS FALSE, AND IT WAS THE CLAIM THIS MODULE WAS BUILT
ON.  [CORRECTED, ROUND jop8ph-2, pf-adversary on the jop8ph diff, MEASURED.]
``repopulation_entries`` raises on FOUR things, not one, and the first
version of this module checked exactly one of them:

  1. containment -- the ledger cannot answer for a roster identity
     (``mob_death._balance_in``);
  2. an identity at 0 HP in the ledger that the death register does NOT hold
     dead (``mob_death.py:2140``) -- "the kill was computed and never
     finished";
  3. an identity above 0 HP that the register DOES hold dead
     (``mob_death.py:2160``);
  4. a register row whose ceiling disagrees with the roster's (``:2168``),
     which is the register's business and not this module's.

MEASURED at the time: a ledger built exactly as ``_sync_combat_scene_state``
builds it, with one identity taken to 0 HP and no death committed, was
printed ``state=same_scene admitted=yes covered=12/12 missing=none``,
forwarded, and RAISED -- and ``runtime.py`` documents that very state (a mob
at 0 HP with no registered owner ruling) as shipped and disclosed.  The
outcome is the one this module's opening paragraph exists to prevent.

So conditions 2 and 3 are checked here now, whenever the caller hands over
the register that can answer them, and a fifth check the composer does NOT
make is here too: a ledger row whose CEILING disagrees with the roster row of
the same identity ships a wrong HP number with no exception and no line
anywhere (``mob_combat.strike`` refuses that pair by name; the census path
did not).  A composed-wrong-number is worse than a refusal, because nothing
reports it.

Containment is still checked even when the scenes agree, and that is not
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
# ROUND jop8ph-2, pf-adversary D2.  A ledger row whose CEILING disagrees with
# the roster row of the same identity.  Containment says nothing about this:
# the identity sets match exactly and the HP the census then ships is a
# number from a different table.  ``mob_combat.strike`` already refuses this
# pair by name (REFUSE_LEDGER_ROW_DISAGREES_WITH_ROSTER); the census path had
# nothing.  MEASURED: roster ceiling 3857, ledger row 11571, admitted, and
# the composed bytes carried 11571 with no exception and no console line.
STATE_LEDGER_ROW_DISAGREES_WITH_ROSTER = "ledger_row_disagrees_with_roster"
# ROUND jop8ph-2, pf-adversary D1 -- THE ONE THAT REFUTED THIS MODULE'S
# HEADLINE CLAIM.  Containment is NOT the only precondition
# ``mob_death.repopulation_entries`` raises on; it has two more, both about
# the ledger disagreeing with the DEATH REGISTER (mob_death.py:2140 and
# :2160).  A ledger standing at 0 HP for an identity the register does not
# hold dead, or standing above 0 for one it does, raises -- inside the
# listener thread, from a ledger this module was printing ``admitted=yes
# covered=12/12`` for.  Checkable only when the caller hands over its
# register, which the census composer always has.
STATE_LEDGER_DISAGREES_WITH_REGISTER = "ledger_disagrees_with_register"
# The scene id itself could not be read, or the roster override was not a
# sequence of roster rows.  ROUND jop8ph-2, pf-adversary D6: this function
# promised "without raising" and then raised for both, because only the
# ``ledger`` argument was guarded -- the asymmetry was backwards, since the
# guarded argument is the one a caller is least sure of.
STATE_INPUTS_UNREADABLE = "inputs_unreadable"

ADMITTING_STATES = (STATE_SAME_SCENE, STATE_UNSCOPED_COVERS_ROSTER)

# What the recompose path must print when it was handed no ledger at all.
# The COO's 18:42 ruling allows a raise OR a FATAL line; this lane takes the
# line, for the reason the decision letter gives at length -- a fail-closed
# census is a player standing in an empty world, which is worse than the
# defect being reported.  "Refuse" here means refuse to be silent.
FATAL_TOKEN = "MOB_LEDGER_ADMISSION_FATAL"

# The HP a dead monster stands at, which is what both of the register
# disagreements at ``mob_death.py:2140``/``:2160`` compare against.  Spelled
# here rather than imported so this module keeps its one-sibling import and
# stays cheap on the census path; ``test_mob_ledger_admission`` joins it
# against ``mob_death.HP_WHEN_DEAD`` so the copy cannot drift silently -- the
# same literal-plus-guard split ``field_mobs.OWNER_REFUSED_PLACEMENTS`` uses.
HP_WHEN_DEAD = 0


def _ceiling_conflicts(ledger: Any, ceilings: Any) -> Any:
    """Identities whose ledger ceiling disagrees with the roster's (D2).

    ``None`` means the ledger could not be read row by row, which is the
    caller's cue to report :data:`STATE_UNREADABLE` rather than an empty
    list -- "no conflicts found" and "could not look" are the pair this
    module keeps having to separate.
    """
    try:
        conflicts = []
        for identity, ceiling in ceilings.items():
            if ledger.balance_of(identity).max_hp != ceiling:
                conflicts.append(identity)
        return tuple(sorted(conflicts))
    except Exception:  # noqa: BLE001 - never raise at a census composer
        return None


def _register_conflicts(ledger: Any, rows: Any, register: Any) -> Any:
    """Identities where the ledger and the death register contradict (D1).

    The two conditions are transcribed from the refusals themselves
    (``mob_death.py:2140`` and ``:2160``), not paraphrased: an identity the
    register does NOT hold dead standing at 0 HP in the ledger, and an
    identity it DOES hold dead standing above 0.  Either one raises out of
    ``repopulation_entries``.

    ``None`` means the register or the ledger could not be read.  The scene
    a record belongs to is ``mob.scene`` -- the roster row's own table tag,
    which is what ``repopulation_entries`` passes to ``is_dead`` -- so this
    asks the register the same question in the same words.
    """
    try:
        conflicts = []
        for mob in rows:
            standing = ledger.balance_of(mob.actor_identity).current_hp
            dead_in_register = register.is_dead(mob.actor_identity, mob.scene)
            if dead_in_register != (standing == HP_WHEN_DEAD):
                conflicts.append(mob.actor_identity)
        return tuple(sorted(conflicts))
    except Exception:  # noqa: BLE001 - never raise at a census composer
        return None


def admit_ledger(
    scene_id: int,
    ledger: Any,
    *,
    roster: Any = None,
    register: Any = None,
) -> dict[str, Any]:
    """Decide, without raising, whether ``ledger`` speaks for ``scene_id``.

    Returns a record, never a bare bool, because every caller so far has
    needed the REASON as well as the verdict: the census path prints it, the
    recompose path escalates one particular reason to FATAL, and a test can
    tell "declined because it is another scene's" from "declined because it
    is this scene's and out of date" -- two states that would be one bit
    apart in a bool and are one code change apart in what the reader must do
    next.

    ~~``roster`` ... this module then answers about that composition rather
    than about a re-derivation of it.~~  [CORRECTED, ROUND jop8ph-2,
    pf-adversary D5.]  ``roster`` IS the rows the caller is composing, and
    passing them is still the right call -- but the sentence claimed a
    measurement that does not exist today: the default is
    ``field_mobs.roster_for_scene_id(scene_id)``, the same pure call with
    the same argument the census composer makes, so deleting the keyword at
    that call site survives the whole suite.  It is plumbing for the day
    those two differ, not evidence that they do.
    ``test_the_roster_override_is_measured_equivalent_today`` pins the
    equivalence, so the day it stops holding is a noticed day.

    ``register`` IS EVIDENCE, and it is the argument this function was
    missing.  ROUND jop8ph-2, pf-adversary D1, MEASURED: containment is NOT
    the only precondition ``mob_death.repopulation_entries`` raises on, and
    the first version of this module said in its own docstring that it was
    ("Nothing else is").  Two further refusals live at ``mob_death.py:2140``
    and ``:2160``, both comparing the ledger against the DEATH REGISTER: an
    identity at 0 HP the register does not hold dead, and an identity above
    0 HP that it does.  Either one raises out of a census composition this
    module had just printed ``admitted=yes covered=12/12 missing=none`` for
    -- inside a listener thread, which is the exact outcome (a logged-in
    player receiving zero actors) the module exists to prevent.

    Without a register those two cannot be checked, so ``register_checked``
    is reported next to the verdict and the console line says
    ``register=unchecked``.  A caller composing entries HAS a register --
    ``mob_death.repopulation_entries`` requires one -- so the path that can
    actually raise is the path that can always check.

    ``vacuous`` is true when the roster has no rows.  ``admitted`` is then
    true for any readable ledger and means nothing at all -- containment
    over an empty set is vacuous truth, and a caller that gates on
    ``admitted`` alone will read a town with no monsters as proof its ledger
    is the right one.  It is reported rather than folded into ``admitted``
    for the same reason ``census_backing_report`` reports ``vacuous`` beside
    ``fully_backed``: the two sentences differ and only the caller knows
    which one it needs.
    """
    try:
        scene = field_mobs.scene_for_scene_id(scene_id)
        rows = tuple(
            field_mobs.roster_for_scene_id(scene_id) if roster is None
            else roster
        )
        wanted = tuple(mob.actor_identity for mob in rows)
        ceilings = {mob.actor_identity: mob.max_hp for mob in rows}
    except Exception:  # noqa: BLE001 - see STATE_INPUTS_UNREADABLE
        # D6.  The promise on this function's first line is "without
        # raising", and it applied to one argument out of three.  A bad
        # scene id went out through field_mobs, and a bad roster override
        # went out through the generator expression below it, both
        # uncaught.
        return {
            "scene_id": scene_id,
            "scene": None,
            "ledger_scene": None,
            "roster_count": 0,
            "covered_count": 0,
            "missing": (),
            "conflicts": None,
            "vacuous": False,
            "missing_measured": False,
            "register_checked": False,
            "state": STATE_INPUTS_UNREADABLE,
            "admitted": False,
            "ledger": None,
        }

    record: dict[str, Any] = {
        "scene_id": scene_id,
        "scene": scene,
        "ledger_scene": None,
        "roster_count": len(wanted),
        "covered_count": 0,
        "missing": (),
        # Identities whose ledger row contradicts the roster's ceiling (D2)
        # or the death register (D1).  Separate from ``missing``, which stays
        # containment-only: "the ledger cannot answer for it" and "the ledger
        # answers something else" are different failures with different fixes.
        #
        # ``None`` until the check RUNS, and the console prints
        # ``conflicts=not_measured`` for it.  Every state that returns early
        # -- absent, unreadable, other_scene, either incomplete -- never
        # reaches the comparison, and reporting ``none`` there would be the
        # ``covered=0/12 missing=none`` self-contradiction rebuilt in a new
        # field one round after it was found in the old one.
        "conflicts": None,
        "vacuous": not wanted,
        # Whether the two register-disagreement preconditions (D1) could be
        # checked at all.  Reported rather than assumed either way: "checked
        # and clean" and "not checkable" are the two states the whole finding
        # is about, and collapsing them would rebuild it.
        "register_checked": False,
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

    # THE DECLARATION WINS HERE, and it wins even when containment would have
    # passed.  Identities carry no scene component -- field_mobs says so in
    # its own words -- so a ledger built from another scene's rows can contain
    # everything this scene's roster asks for and still be the HP of different
    # monsters that share a number.
    #
    # ~~if both_named and ledger_scene != scene:~~ [CORRECTED, ROUND
    # jop8ph-2, pf-adversary D3, MEASURED.]  Requiring BOTH names made this
    # check structurally dead for every scene the project ships no table for:
    # ``scene_for_scene_id`` returns None for exactly those scenes, so
    # ``admit_ledger(997, <a bg0001 ledger>)`` printed
    # ``scene=? ledger_scene=bg0001 state=same_scene admitted=yes`` -- a line
    # that contradicts itself on its own face -- and FORWARDED the ledger.
    # The bytes were harmless (an empty roster overrides nothing); the
    # EVIDENCE was not, and a state name is evidence.  A ledger that names a
    # scene we cannot even name is a ledger we cannot show belongs here.
    if ledger_scene is not None and ledger_scene != scene:
        record["state"] = STATE_OTHER_SCENE
        return record

    if missing:
        record["state"] = (
            STATE_UNSCOPED_INCOMPLETE if ledger_scene is None
            else STATE_SAME_SCENE_INCOMPLETE
        )
        return record

    # D2.  Containment compares identity SETS and says nothing about the
    # numbers on the rows.  A ledger row whose ceiling disagrees with the
    # roster row of the same identity composes a body carrying HP from a
    # different table -- no exception, no console line, a monster the client
    # is told has three times its real health.  ``mob_combat.strike`` refuses
    # this exact pair by name and the census path had nothing.
    disagreeing = _ceiling_conflicts(ledger, ceilings)
    if disagreeing is None:
        record["state"] = STATE_UNREADABLE
        return record
    record["conflicts"] = disagreeing
    if disagreeing:
        record["state"] = STATE_LEDGER_ROW_DISAGREES_WITH_ROSTER
        return record

    # D1.  The two preconditions this module used to say did not exist.
    if register is not None:
        conflict = _register_conflicts(ledger, rows, register)
        if conflict is None:
            record["state"] = STATE_UNREADABLE
            return record
        record["register_checked"] = True
        record["conflicts"] = conflict
        if conflict:
            record["state"] = STATE_LEDGER_DISAGREES_WITH_REGISTER
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
    register: Any = None,
) -> Any:
    """The ledger a composer for ``scene_id`` may safely use, or ``None``.

    The one-expression shape for a call site that does not want the record.
    ``None`` here means "compose without consulting HP", which is what every
    ledger-less path in this tree already does.
    """
    return admit_ledger(
        scene_id, ledger, roster=roster, register=register)["ledger"]


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
        if record["conflicts"] is None:
            conflicts = "not_measured"
        elif not record["conflicts"]:
            conflicts = "none"
        else:
            conflicts = ",".join("0x%X" % i for i in record["conflicts"])
        return (
            "MOB_LEDGER_ADMISSION scene_id=%s scene=%s ledger_scene=%s "
            "state=%s admitted=%s covered=%d/%d missing=%s conflicts=%s "
            "register=%s vacuous=%s" % (
                record["scene_id"],
                scene,
                ledger_scene,
                record["state"],
                "yes" if record["admitted"] else "no",
                record["covered_count"],
                record["roster_count"],
                missing,
                conflicts,
                "checked" if record["register_checked"] else "unchecked",
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
    register: Any = None,
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
    record = admit_ledger(
        scene_id, ledger, roster=roster, register=register)
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
