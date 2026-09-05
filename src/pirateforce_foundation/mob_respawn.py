"""LANE-B (COMBAT): the one door that says "this monster is alive again".

WHAT A PLAYER SEES BECAUSE OF THIS FILE.  Today, on main: walk into scene 3,
kill the twelve monsters that stand there, and scene 3 is EMPTY -- not for
two minutes, not until you log out, but until somebody restarts the server
process.  Walk out to scene 4 and back and the twelve corpses are still
corpses, because ``runtime.py``'s scene-open block re-opens the roster at its
table's full HP and then zeroes one balance per row in the session's
``mob_death.DeathRegister``, and NOTHING in this tree has ever taken a row
out of that register.  ``mob_death_persistence``'s own docstring says it in
the plainest words this project has: "a dead monster is dead until something
respawns it, and NOTHING IN THIS TREE RESPAWNS ONE TODAY.  So there is no
sweep here, and ``WorldDeaths.forget`` exists unused-by-production and named,
waiting for the respawn round that will be its only caller."  This file is
that round, and this module is that caller.

M4 ITEM (4).  ``NOW.md``'s milestone ladder lists four things M4 ("you can
hit it, it can die") must show on screen, and the fourth is "it can be born
again" -- measured 3 Sep and recorded there as a zero, in that file's own
words: the arrival census drops the dead ones and there is no respawn.  This
module is the server half of that item.  (English only in this file on
purpose: the bridge console is cp874 and a non-ASCII byte in a module it
imports is a crash on the machine that reads these lines.)

WHY A SWEEP OF THE REGISTER AND NOT A FILTER AT THE CENSUS.  The tempting
shape is to leave the register alone and let the census composer skip a grave
that has aged out -- one function, no new state.  It is also the one shape
this lane is forbidden to ship, and the reason is written into
``mob_death.py`` already: the ledger and the register must agree.  A census
that reports a monster standing while the session's ``mob_combat.
CombatLedger`` still holds it at zero gives the player a monster that renders,
accepts a click, and then REFUSES EVERY HIT (``mob_combat`` answers
``no_room`` at the floor), and any later ``repopulation_entries(...,
ledger=...)`` refuses the pair outright with
``REFUSE_LEDGER_DISAGREES_WITH_REGISTER`` -- a refusal that reaches
``runtime.py``'s census dispatch from an ``else:`` its own ``try`` does not
cover, where it unwinds the v141 listener thread.  So respawn is a REMOVAL
from the books, at the one moment the ledger is rebuilt from the table
anyway.  ``mob_death_persistence.WorldDeaths.forget``'s docstring asked for
exactly this ("it must be a removal from these books and not a clear of
them") and this module obeys it rather than reinterpreting it.

WHERE THE REMOVAL IS SAFE, AND IT IS ONE PLACE, NOT ANY PLACE.  At a scene
change ``runtime.py`` builds ``mob_combat.open_ledger(roster)`` FRESH -- every
row at the table's full HP -- and only then zeroes the rows the register calls
dead.  A row this module has removed by then is therefore already standing at
its ceiling with no second write needed anywhere: the respawn costs exactly
one statement and touches no balance.  That is why
:data:`MOB_RESPAWN_WIRING` names that block and no other.  Sweeping anywhere
else -- mid-fight, on a tick, inside ``commit_death`` -- would open a grave
while the ledger still reads zero for it, which is the disagreement above
with the lanes reversed.

WHAT THE DELAY IS MEASURED FROM, STATED EXACTLY, BECAUSE IT IS NOT WHAT A
READER WOULD ASSUME.  Not the instant the monster died: ``mob_death.py`` may
not read a clock at all -- its own test refuses ``time`` in that file's
imports beside ``socket`` and ``random``, because that lane composes frames
from values and must give the same answer twice -- so ``kill()`` leaves
``DeathRecord.buried_at`` as ``None`` and THIS module dates a grave THE FIRST
TIME A SWEEP SEES IT.  Since the only sweep is at a scene change, the delay
therefore runs from the first scene boundary the killer crosses after the
kill, which is at worst one boundary later than the death and is never
earlier.  The practical shape of that, said plainly: a monster does not come
back while the player who killed it is still standing in the scene, and the
first time they walk out is when its clock starts.  ~~If the COO wants the
delay measured from the death itself, that is a clock argument on
``mob_death.kill`` and a pin to lift in ``tests/test_mob_death.py``, and the
letter carrying this round says so rather than leaving it to be
discovered.~~

RULED, AND THIS PARAGRAPH IS NOW A SPECIFICATION RATHER THAN A CONFESSION
(``COO-DECISION 20260905_2147``, item 2, answering LANE-B ``20260905_1953``).
THE CLOCK STARTS AT THE FIRST SCENE EDGE THE KILLER CROSSES AFTER THE KILL,
NOT AT THE SECOND OF DEATH, AND THAT IS THE WANTED BEHAVIOUR: a monster
standing back up in front of the player still looting it is the outcome the
COO ruled against, so "it does not respawn while you are still standing
there" is the FEATURE and not the limitation.  The ``time`` pin on
``mob_death.py`` STAYS PINNED -- a later round that reads this file and
reaches for ``mob_death.kill`` to "fix" the zero point is undoing a ruling,
not repairing a defect.  That sentence is here, in the module a fixer would
open, precisely so it is read before the pin is touched.

A GRAVE THIS MODULE HAS NEVER SEEN IS NEVER OPENED IN THE SAME BREATH.
Dating and opening are two passes and a freshly dated grave is kept, always:
opening one on the sweep that first dated it would treat "I do not know how
old this is" as "it is old enough", which is exactly the monster standing
back up over the player still looting it.

THE DELAY IS THIS LANE'S ASSUMPTION AND IT IS LABELLED AS ONE.  See
:data:`RESPAWN_DELAY_SECONDS`.

NEVER RAISES INTO A CALLER.  Same promise, for the same reason, that
``world_scene_registry`` and ``mob_death_persistence`` make: this code sits on
the scene-arrival path, and a respawn book that can take down the listener
thread would be a worse defect than the one it closes.  Every entry point
returns a value plus a named, counted reason; the refusals are printable so
that "nothing aged out" and "this sweep refused to run at all" can never be
the same console line.

THERE ARE TWO BOOKS, AND A SWEEP THAT MOVES ONLY ONE OF THEM IS A BUG.  A
draft of this module said the world grave book had no production writer and
made ``world=`` an optional extra.  THAT WAS FALSE, pf-adversary measured it,
and the correction is the reason this module reaches for that book BY
DEFAULT: ``mob_death.commit_death`` calls ``mob_death_persistence.
remember_death(step.record, world=world)`` on EVERY accepted kill, and
``remember_death`` resolves ``world=None`` to the process singleton
``world_deaths()``.  So both of ``runtime.py``'s ``commit_death`` call sites
-- neither of which passes ``world=`` -- have been writing the process-wide
grave book all along.  What ``runtime.py`` has no line for is READING it
(``mob_death_persistence.DEATH_SEED_WIRING``, still unwired), and that is a
different missing statement from the one LANE-B CORE-REQUEST
``20260905_1650`` asks for.  Two consequences, both of which this module now
handles rather than describes:

    * A sweep that opened a grave in the session register and left it on the
      process book would BE the "two books that can disagree about one
      monster" this file's own paragraph above calls the failure to avoid.
    * The day ``DEATH_SEED_WIRING`` lands, that seed re-admits from the
      process book -- carrying the record ``kill()`` composed, whose
      ``buried_at`` is ``None`` -- so a grave left there would be re-dated on
      every scene sync and could NEVER age out.  A permanent, silent zero.

Hence :func:`sweep_the_session_register` opens BOTH books unless a caller
names a different one, and a caller who genuinely wants the session half
alone has to say so with :data:`NO_WORLD_BOOK`.

WHAT THIS FILE DOES NOT MAKE TRUE.  A player STANDING IN the scene when a
grave ages out does not see the monster stand up: nothing here composes a
frame, and the respawn is observed when that session next opens the scene.
Making it visible without a scene open needs Door B's frame budget and is not
this round's claim.
"""

from __future__ import annotations

from dataclasses import dataclass, replace as _replace
import math
import time
from typing import Any

from . import mob_death

# Same convention every other shippable module in this project uses: True
# means "no scenario flag needed, safe for every connection".  This module
# composes no frame and writes no database row; what it changes is which rows
# a scene-open rebuild zeroes, and that is gameplay, not a trial.
production_allowed = True

#: How long a corpse stays a corpse.
#:
#: ~~[ASSUMPTION OF LANE B - AWAITING COO CONFIRMATION]~~ **CONFIRMED,
#: ``COO-DECISION 20260905_2147``** (answering LANE-B's letter
#: ``20260905_1953``, item 1): option (a) stands, 120.0 seconds, for the
#: reason this line already gave and the COO restated -- one duration for
#: "how long does the world remember this" rather than two numbers nobody
#: chose together, so the owner can taste-test the floor and the monster
#: with a single edit later.  The COO's own words on the other two options:
#: a number derived from the shipped tables is Panya's after real play and
#: not ours to invent, and the third was refused with this lane.  Nothing
#: below this comment changed; the label did.
#:
#: WHAT THE RULING DID NOT CHANGE, kept verbatim because it is a measurement
#: and not a label: nothing measured on the real client or in the shipped
#: tables gives this number, and this lane will not invent a fact and then
#: cite itself for it.  120.0 is chosen for one
#: reason that is not arbitrary: it is exactly ``mob_loot.
#: DROP_LIFETIME_SECONDS``, the only other "how long does the world remember
#: this" constant this project has ever shipped, so the floor and the monster
#: run on ONE DURATION rather than on two numbers nobody chose together.
#: SAME DURATION, DIFFERENT ZERO, and pf-adversary was right to refuse the
#: word "schedule" a draft of this line used: the drop's clock starts at the
#: death, this one starts at the first scene crossing after it (see the
#: docstring), so a player who kills and stands there for ten minutes loses
#: the drop at +120 s and starts the respawn clock at +600 s.  ~~The letter
#: that carries this round asks the COO to rule~~ THE COO HAS RULED (see the
#: head of this comment); a different number changes this line and nothing
#: else in this file, and only Panya's own play is expected to pick one.
RESPAWN_DELAY_SECONDS = 120.0

#: A delay may not exceed this.  Same shape and same reason as
#: ``mob_loot.MAX_DROP_LIFETIME_SECONDS``: an hour is far past any value a
#: game design would pick, and a caller that computed a delay from bad
#: arithmetic must hit a named refusal rather than bury a scene until reboot.
MAX_RESPAWN_DELAY_SECONDS = 3600.0

#: Printed once per sweep that opened at least one grave.  Grep-able on the
#: server console, which is where every claim this lane makes gets checked.
RESPAWN_TOKEN = "MOB_RESPAWN"

#: Printed instead when a sweep refused to run at all.  A DIFFERENT token on
#: purpose: "no grave was old enough" and "this sweep never looked" must not
#: read the same in a log a tester greps.
RESPAWN_REFUSED_TOKEN = "MOB_RESPAWN_REFUSED"

#: Pass this as ``world=`` to sweep the session register ALONE.  A sentinel
#: rather than ``None``, because ``None`` is what ``mob_death_persistence.
#: remember_death`` already spells "use the process book" and one word must
#: not mean opposite things two doors apart in the same feature.  A caller
#: who wants the session half only has to say so out loud.
NO_WORLD_BOOK = "no_world_book"

#: The default for ``world=``: reach for ``mob_death_persistence.
#: world_deaths()``, the same process singleton every production kill is
#: already buried in.
THE_PROCESS_BOOK = "the_process_book"

REFUSE_NOT_A_REGISTER = "not_a_death_register"
REFUSE_NOT_AN_OUTCOME = "not_a_respawn_outcome"
REFUSE_DELAY_NOT_A_DURATION = "delay_not_a_duration"
REFUSE_NOW_NOT_A_READING = "now_not_a_monotonic_reading"
REFUSE_CLOCK_RAISED = "clock_raised"
REFUSE_REGISTER_REFUSED_THE_REMOVAL = "register_refused_the_removal"
#: NOT a value of ``RespawnOutcome.refusal``.  A world book that raises is a
#: PARTIAL result, not a sweep that did not run: the session register really
#: did lose those rows.  ``refusal`` means "this sweep never looked", and
#: pf-adversary measured a draft of this file using one name for both -- so
#: this one is counted in ``world_failed`` and printed on its own line.
WORLD_RAISED = "world_raised"

#: Why a grave that was looked at is still a grave.  Counted separately
#: because they answer different questions -- "it is not time yet", "this
#: sweep is the one that started its clock", "the reading it was compared
#: against is older than the grave" -- and reporting them as one number would
#: hide a register nothing is ageing behind a sweep that looks busy.
KEPT_TOO_YOUNG = "too_young"
KEPT_DATED_THIS_SWEEP = "dated_this_sweep"
KEPT_CLOCK_WENT_BACKWARDS = "clock_went_backwards"


@dataclass(frozen=True)
class RespawnOutcome:
    """What one sweep did, in numbers a console line and a test can both read.

    ``opened`` is ``(scene, actor_identity)`` pairs in the order they were
    removed, which is register order -- ``(scene, actor_identity)`` ascending.
    """

    opened: tuple[tuple[str, int], ...] = ()
    dated: int = 0
    kept_too_young: int = 0
    kept_clock_went_backwards: int = 0
    world_forgot: int = 0
    world_failed: int = 0
    world_detail: str = ""
    refusal: str = ""
    detail: str = ""

    @property
    def swept(self) -> bool:
        """True when this sweep ran.  ``opened`` may still be empty."""
        return not self.refusal

    @property
    def kept(self) -> int:
        return (self.kept_too_young + self.dated
                + self.kept_clock_went_backwards)


def age_of(record: Any, now: float) -> float | None:
    """How long this grave has been a grave, or ``None`` if it cannot say.

    ``None`` for a record with no clock AND for a reading that would make the
    age negative.  A caller must not have to tell those two apart to stay
    correct -- both mean "do not open this grave" -- and
    :func:`sweep_the_session_register` counts them apart for the console.
    """
    buried_at = getattr(record, "buried_at", None)
    if buried_at is None:
        return None
    try:
        age = float(now) - float(buried_at)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(age) or age < 0.0:
        return None
    return age


def _dated(record: Any, reading: float) -> Any:
    """The same grave, with its clock started.

    ``dataclasses.replace`` rather than a hand-built ``DeathRecord``: this
    module must not have to know how many columns that record carries, and a
    future one added by another round would be dropped silently by a
    positional rebuild here.
    """
    return _replace(record, buried_at=reading)


def _book(world: Any) -> tuple[Any, str]:
    """Resolve ``world=`` to a grave book, or to ``None`` with a reason.

    Never raises: a process book that cannot be built is a counted line, not
    an exception out of the scene-arrival path.
    """
    if world is NO_WORLD_BOOK:
        return (None, "world=NO_WORLD_BOOK, session register only")
    if world is THE_PROCESS_BOOK or world is None:
        # `world is None` lands here on purpose and NOT as "no book":
        # `mob_death_persistence.remember_death` already spells None that
        # way, and the burial half of this feature is the half that has been
        # running in production all along.
        try:
            from . import mob_death_persistence

            return (mob_death_persistence.world_deaths(), "")
        except Exception as error:  # noqa: BLE001 - counted, not raised
            return (None, "the process grave book could not be reached: %r"
                          % (error,))
    return (world, "")


def _reading(now: Any) -> tuple[float, str, str]:
    """Resolve ``now`` to a monotonic reading, or name why it could not be."""
    if now is None:
        try:
            now = time.monotonic()
        except Exception as error:  # noqa: BLE001 - reported by name
            return (0.0, REFUSE_CLOCK_RAISED, repr(error))
    if type(now) is bool or type(now) not in (int, float):
        return (0.0, REFUSE_NOW_NOT_A_READING,
                "now must be a number, not %r" % (type(now),))
    reading = float(now)
    if not math.isfinite(reading) or reading < 0.0:
        return (0.0, REFUSE_NOW_NOT_A_READING,
                "now must be finite and non-negative; got %r" % (reading,))
    return (reading, "", "")


def _duration(delay: Any) -> tuple[float, str, str]:
    if type(delay) is bool or type(delay) not in (int, float):
        return (0.0, REFUSE_DELAY_NOT_A_DURATION,
                "delay must be a number, not %r" % (type(delay),))
    seconds = float(delay)
    if not math.isfinite(seconds) or seconds < 0.0:
        return (0.0, REFUSE_DELAY_NOT_A_DURATION,
                "delay must be finite and non-negative; got %r" % (seconds,))
    if seconds > MAX_RESPAWN_DELAY_SECONDS:
        return (0.0, REFUSE_DELAY_NOT_A_DURATION,
                "delay %r is past the %r ceiling this lane will accept"
                % (seconds, MAX_RESPAWN_DELAY_SECONDS))
    return (seconds, "", "")


def sweep_the_session_register(
    register: Any,
    *,
    now: Any = None,
    world: Any = THE_PROCESS_BOOK,
    delay: Any = RESPAWN_DELAY_SECONDS,
) -> tuple[Any, RespawnOutcome]:
    """Open every grave in ``register`` that has been one for ``delay``.

    Returns ``(register, outcome)``.  THE REGISTER COMES BACK UNCHANGED --
    the same object, not an equal copy -- whenever nothing was dated, nothing
    aged out, or ``outcome.refusal`` is set: a caller that stores what it is
    handed then keeps the generation an in-flight ``commit_death`` was
    computed against, and a kill racing this sweep is not made to retry for
    nothing.  A world book that RAISES is not a refusal and does not put the
    register back -- those rows really did leave the session's books -- it is
    counted in ``outcome.world_failed`` and printed on its own line.

    When something DOES age out the register is a new value with
    ``generation + 1``, which is the same statement ``with_death`` makes for
    the same reason: the books moved, so a step computed from the old reading
    must be recomputed rather than committed on top.

    ``world`` DEFAULTS TO THE PROCESS GRAVE BOOK -- the same
    ``mob_death_persistence.world_deaths()`` singleton every production kill
    is already buried in through ``commit_death``.  A caller therefore gets
    both books moved with no argument at all, which is the only correct
    default: see this module's "THERE ARE TWO BOOKS" paragraph for what a
    one-book sweep costs.  Pass any object with a ``forget(scene, identity)``
    shape to use that instead, or :data:`NO_WORLD_BOOK` to sweep the session
    register alone.

    NEVER RAISES.  Every failure comes back named, in ``outcome.refusal``
    (this sweep did not run) or ``outcome.world_failed``/``world_detail``
    (it ran, and the grave book would not take some of it).
    """
    if type(register) is not mob_death.DeathRegister:
        return (register, RespawnOutcome(
            refusal=REFUSE_NOT_A_REGISTER,
            detail="register must be a typed mob_death.DeathRegister, not %r"
                   % (type(register),)))
    seconds, refusal, detail = _duration(delay)
    if refusal:
        return (register, RespawnOutcome(refusal=refusal, detail=detail))
    reading, refusal, detail = _reading(now)
    if refusal:
        return (register, RespawnOutcome(refusal=refusal, detail=detail))

    keep = []
    opened = []
    too_young = 0
    dated = 0
    backwards = 0
    for record in register.records:
        buried_at = getattr(record, "buried_at", None)
        if buried_at is None:
            # PASS ONE: start this grave's clock and keep it.  Never opened
            # in the same breath -- see the module docstring.
            #
            # WRAPPED even though DeathRegister has already checked that every
            # row is a typed DeathRecord and _reading() has already checked
            # that `reading` is one this record will accept.  "Never raises"
            # is a promise about this function on the scene-arrival path, and
            # a promise that holds only while two other checks stay correct is
            # not the promise this module made.
            try:
                keep.append(_dated(record, reading))
            except Exception as error:  # noqa: BLE001 - reported by name
                return (register, RespawnOutcome(
                    refusal=REFUSE_REGISTER_REFUSED_THE_REMOVAL,
                    detail="dating a grave raised %r" % (error,)))
            dated += 1
            continue
        age = age_of(record, reading)
        if age is None:
            # A reading older than the grave it is compared against.  On a
            # monotonic clock inside one process this cannot happen; a
            # caller that pinned `now` itself can make it happen, and the
            # safe answer is the one that never opens a grave early.
            backwards += 1
            keep.append(record)
            continue
        if age < seconds:
            too_young += 1
            keep.append(record)
            continue
        opened.append((record.scene, record.actor_identity))

    if not opened and not dated:
        # NOTHING MOVED: hand back the SAME OBJECT, not an equal copy, so a
        # caller that stores what it is given keeps the generation an
        # in-flight commit_death was computed against.
        return (register, RespawnOutcome(
            kept_too_young=too_young,
            kept_clock_went_backwards=backwards))

    try:
        swept = mob_death.DeathRegister(
            tuple(keep),
            # THE GENERATION MOVES FOR A REMOVAL AND NOT FOR A DATING.  A
            # removal changes WHO IS DEAD, which is what the compare-and-swap
            # in commit_death is about, and a step computed against the old
            # reading must retry.  A dating changes only how old a grave says
            # it is -- `buried_at` is `compare=False`, so the two registers
            # are the same VALUE -- and bumping the counter for it would make
            # every scene change lose a racing kill for nothing.
            register.generation + (1 if opened else 0))
    except mob_death.MobDeathContractError as error:
        # Unreachable by construction -- a subsequence of a sorted, unique
        # tuple is sorted and unique -- and named anyway, because "the
        # register refused its own subset" is a real answer and an exception
        # out of this function is not.
        return (register, RespawnOutcome(
            refusal=REFUSE_REGISTER_REFUSED_THE_REMOVAL,
            detail="%s: %s" % (error.reason, error)))

    if not opened:
        return (swept, RespawnOutcome(
            dated=dated, kept_too_young=too_young,
            kept_clock_went_backwards=backwards))

    book, book_detail = _book(world)
    forgot = 0
    failed = 0
    world_detail = book_detail
    if book is not None:
        for scene, actor_identity in opened:
            # EVERY grave, not "up to the first one that raises".  A draft of
            # this loop broke out, which meant one transient failure on the
            # second of twelve orphaned graves three through twelve on the
            # process book FOREVER -- and those are exactly the rows that a
            # future DEATH_SEED_WIRING would re-admit undated, so they would
            # never age out again either.  A book that raises on one row has
            # said nothing about the next one.
            try:
                if book.forget(scene, actor_identity):
                    forgot += 1
            except Exception as error:  # noqa: BLE001 - counted, not raised
                failed += 1
                if not world_detail:
                    world_detail = "%s %r" % (WORLD_RAISED, error)

    return (swept, RespawnOutcome(
        opened=tuple(opened), dated=dated, kept_too_young=too_young,
        kept_clock_went_backwards=backwards,
        world_forgot=forgot, world_failed=failed, world_detail=world_detail))


def describe_sweep(outcome: Any) -> tuple[str, ...]:
    """Console lines for one sweep.  Empty when there is nothing to say.

    Deliberately silent for the common case -- a sweep that opened nothing --
    for the reason ``lane_b_mob_ai_tick`` gives about phase repeats: this runs
    on every scene change a player makes, and a line per crossing that always
    says zero is a line nobody reads.
    """
    if type(outcome) is not RespawnOutcome:
        # NAMED, not silent.  `sweep_the_session_register` returns
        # `(register, outcome)` and `describe_sweep(register)` is one
        # transposition away; answering that with `()` would look exactly
        # like the quiet case, in the one function whose whole job is making
        # this feature visible.
        return ("%s reason=%s detail=%r" % (
            RESPAWN_REFUSED_TOKEN, REFUSE_NOT_AN_OUTCOME, type(outcome)),)
    lines = []
    if outcome.refusal:
        lines.append("%s reason=%s detail=%s" % (
            RESPAWN_REFUSED_TOKEN, outcome.refusal, outcome.detail))
    for scene, actor_identity in outcome.opened:
        # "removed_from_the_death_register" and NOT "alive_again", which is
        # what a draft printed.  This function knows one thing: a row left
        # the books.  It has not seen the ledger being built, does not know
        # which scene the player is walking into, and composes no frame -- so
        # a token claiming the monster is alive would be a bookkeeping delta
        # wearing the goal's name, and a tester grepping for it would grade
        # a sweep in the wrong scene as the feature working.
        lines.append("%s scene=%s actor=0x%X removed_from_the_death_register"
                     % (RESPAWN_TOKEN, scene, actor_identity))
    if outcome.world_failed:
        lines.append("%s reason=%s failed=%d detail=%s" % (
            RESPAWN_REFUSED_TOKEN, WORLD_RAISED, outcome.world_failed,
            outcome.world_detail))
    if outcome.opened or outcome.dated:
        # A DATING-ONLY SWEEP SAYS SO, and a draft of this function was
        # silent for it.  That silence was indistinguishable from three other
        # things -- the statement never pasted, the statement pasted and
        # raising inside a caught branch, the sweep called on an empty
        # register -- for the first two minutes of every wipe, which is the
        # whole window in which somebody would be checking.
        lines.append(
            "%s opened=%d dated=%d world_forgot=%d world_failed=%d kept=%d "
            "(too_young=%d dated=%d backwards=%d)" % (
                RESPAWN_TOKEN, len(outcome.opened), outcome.dated,
                outcome.world_forgot, outcome.world_failed, outcome.kept,
                outcome.kept_too_young, outcome.dated,
                outcome.kept_clock_went_backwards))
    return tuple(lines)


# The exact block a runtime.py round pastes, written where a reader of this
# module finds it rather than only in a PR body -- the same convention
# mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING and lane_b_mob_ai_tick.
# LANE_B_MOB_AI_TICK_WIRING already use for themselves.  ONE STATEMENT plus
# its console lines, at ONE call site, and the reason it is that call site and
# not another is this module's own docstring ("WHERE THE REMOVAL IS SAFE").
#
# tests/test_mob_respawn.py::WiringLineTests reads runtime.py's own source and
# pins the negative -- nothing calls this yet -- so the day the paste lands,
# the test that flips is named and in this lane's file, not a surprise in
# somebody else's.
MOB_RESPAWN_WIRING = (
    "runtime.py _sync_combat_scene_state(), inside the "
    "'if folder != self.mob_combat_scene_folder:' block. THREE edits, and "
    "the THIRD one is the one a reader will be tempted to skip. "
    "(1) Immediately AFTER 'ledger_identities = ledger.identities()' and "
    "BEFORE 'for record in self.mob_death_register.records:', add ONE "
    "statement that assigns a LOCAL, never the field: "
    "'respawned, respawn_outcome = mob_respawn.sweep_the_session_register("
    "self.mob_death_register)'. "
    "(2) Change that loop's iterable from 'self.mob_death_register.records' "
    "to 'respawned.records'. "
    "(3) Assign the field ONLY in the three-assignment block at the bottom "
    "of the branch, beside 'self.mob_combat_ledger = ledger': add "
    "'self.mob_death_register = respawned', and print the console lines "
    "AFTER those assignments with "
    "'for line in mob_respawn.describe_sweep(respawn_outcome): "
    "print(lane_hooks.console_safe(line))' (lane_hooks.console_safe, NOT a "
    "bare console_safe: runtime.py has no such bare name and the paste would "
    "be a NameError inside a caught branch -- pf-adversary D5). "
    "Needs 'from . import mob_respawn' in runtime.py's own imports. "
    "WHY EDIT (3) EXISTS -- pf-adversary D3: that three-assignment block is "
    "ATOMIC ON PURPOSE (its own comment says so, from round pk14rf). "
    "mob_ai_control.open_register between the loop and those assignments can "
    "raise REFUSE_PROFILE_UNBUILDABLE BY DESIGN, and _sync_combat_scene_at_"
    "edge swallows it -- so a field assigned above that raise leaves the "
    "death register on the NEW scene while ledger and folder stay on the "
    "departed one. Measured consequence of getting this wrong: the session "
    "latches into ledger_disagrees_with_register on the next census, which "
    "is the refusal that unwinds the v141 listener thread. Latent today "
    "(no shipped table makes open_register raise) and still not to be "
    "pasted the short way. "
    "WHY THIS CALL SITE AND NOWHERE ELSE: the ledger just above is rebuilt "
    "by mob_combat.open_ledger(roster) at the table's full HP, and the loop "
    "zeroes one balance per row still in the register -- so a row this sweep "
    "removed is already standing at its ceiling and NO balance is written by "
    "the respawn at all. Sweeping mid-fight, on a tick, or inside "
    "commit_death opens a grave while that session's ledger still reads zero "
    "for it, which is the same refusal by the other route. "
    "COMPOSES NO FRAME, WRITES NO DATABASE ROW, OPENS NO DOOR B. "
    "DO NOT PASS world=: the default already reaches "
    "mob_death_persistence.world_deaths(), which is the book every "
    "production kill is buried in through commit_death, and both books must "
    "move together. "
    "TWO_SESSIONS_SAME_SCENE: the session half of this sweep is per-session, "
    "so a second player standing in the scene keeps their own corpse until "
    "their own next scene open; the process-wide grave book is opened for "
    "everyone by the same call. The remaining divergence is a named debt of "
    "the missing READER (mob_death_persistence.DEATH_SEED_WIRING), not of "
    "this statement."
)
