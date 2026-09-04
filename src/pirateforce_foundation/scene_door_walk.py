"""LANE-B: which of M4's three doors are OPEN in a scene, WALKED not read.

WHAT THIS ANSWERS, AND WHO ASKED.  ``COO-DECISION 2026-09-04T14:50+07:00``
item 3 (``pf_bridge/notes_to_chief/20260904_1450_COO-DECISION-lane-b-widen-
death-scope-bg0003-seven-templates-approved-stop-new-scenes-until-one-scene-
has-every-door.md``) took scene 4 out of the queue and put a condition on
getting it back: STOP arming new scenes until at least one armed scene has
EVERY door -- a monster you can hit, a monster that dies, and an object on
the ground when it does.  Three scenes are armed (Bg0003, bg0005, Bg0015)
and until this module nothing in this tree could answer the condition; it
was answered by reading three separate modules and believing the join.

WHY IT WALKS INSTEAD OF READING A TABLE, and the lesson is this lane's own,
paid for twice.  ``mob_combat_bg0015_gates`` records it in its own words:
earlier rounds assembled a "gate table" out of predicates that were already
readable (``live_scenes()``, ``composer_scene_ids()``, ``ruling_for``), not
one of which walked the path a swing actually takes -- and the raise that
mattered sat two lines below the call those drafts quoted.  So every answer
below is produced by CALLING the production function whose refusal is the
door: ``mob_ai_control.open_register`` + ``mob_combat.strike``,
``mob_death.ruling_for`` + ``mob_death.kill``, ``mob_loot.roll_drops`` +
``DropLedgerCell.loot_a_kill``.  A door is open because this module made it
open, once, on the roster the server ships to a session.

AND THE FIRST OF THOSE IS HERE BECAUSE THE SAME MISTAKE WAS MADE AGAIN
(pf-adversary D8 of round ``pcsjfr``).  The first draft of this module began
at ``strike`` -- one call BELOW ``mob_ai_control.open_register``, which is
exactly the raise ``mob_combat_bg0015_gates`` is a monument to, quoted in the
paragraph above and then walked past.  No false green came of it (both open
for all five live scenes at HEAD, measured), and the call is here now.

WHERE THE WALK STILL STOPS SHORT, said plainly rather than left for a reader
to discover: the kill door does NOT call ``mob_death.commit_death`` (the
compare-and-swap a live dispatch owes before sending a death frame, and the
only writer of the world's graves), and the drop door stops at
``loot_a_kill``, which returns RECORDS -- ``mob_drop_presence.sustain_a_kill``
is what turns them into bytes and this module deliberately does not call it.
So of the three doors, two compose frames and the third places rows.

WHAT IT TOUCHES: nothing outside the objects it builds itself.  A fresh
``CombatLedger``, a fresh ``DeathRegister`` and a fresh ``DropLedgerCell``
per row, and NO call to ``mob_drop_presence.sustain_a_kill`` -- that is the
function that writes the process-wide ``WorldGround`` floor, and a
diagnostic that seeds the world's floor with imaginary kills is a
diagnostic that changes the game (pf-adversary would find it; this module
declines to have it found).  Nothing here composes anything for a socket,
nothing here is a call site of anything that sends.

NONCLAIMS
---------
* NO claim about a client's screen.  Every "open" here is server-side, and
  ~~the bytes were composed~~ IS STRUCK for one of the three (pf-adversary
  D8): the target and kill doors composed frames, the DROP door placed rows
  and composed nothing.  What a player sees when they land in the scene is
  an attended round's answer, and NOW.md still forbids opening a monster-hit
  ticket for scenes 3/5/14 until P-2 (monster name colour) closes.
* NO claim that an open drop door means an item appears under a label.
  GT-045 measured a name label, brown dust and no model for ids that carry
  a nonzero ``drop_model_type``; ``field_drop_tables``'s own header says so
  at length.  "Open" here means a row was placed on this server's ground.
* NO claim that a scene's twelve open drop doors are twelve measurements
  (pf-adversary D13).  Within a scene every row of the shipped tables names
  the SAME ``drops_normal``/``drops_equipment`` set -- Bg0003's twelve rows
  across seven templates all name 2701002/5400002 -- so the drop door's
  answer is one table fact reported once per row.  The column that does vary
  per template, ``drops_specially``, contributed nothing in 32 seeds and is
  therefore unmeasured here.
* NO claim about scene 4.  This module reports the CONDITION in item 3, and
  it reports the OWNER-REFUSED count beside it, because the condition is a
  fraction and the cheapest way to satisfy it is to stop shipping the row
  that fails (pf-adversary D2).  The decision is the COO's.
* NOT A GT UNLOCK, in the same words the death rulings use: nothing here
  opens an entry in ``GAME_TEST_QUEUE.md``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from . import field_mobs
from . import mob_ai_control
from . import mob_combat
from . import mob_death
from . import mob_loot

#: Shippable with no scenario flag, like every module this lane writes: it
#: reads the same tables a boot reads and calls the same functions a swing
#: calls.  ~~`lane_hooks`'s own gate reads this name.~~ IS STRUCK, pf-adversary
#: D12 of this round: `lane_hooks._discover()` only ever looks at modules under
#: `lane_hooks/` whose stem starts with `lane_`, and
#: `lane_hooks.module_production_allowed("scene_door_walk")` measures False.
#: The name is the lane charter's declaration and nothing reads it here.
production_allowed = True

#: The three doors of M4/M5, in the order a player goes through them.
DOOR_TARGET = "target"
DOOR_KILL = "kill"
DOOR_DROP = "drop"
DOORS = (DOOR_TARGET, DOOR_KILL, DOOR_DROP)

#: One bounded ASCII console line per scene walked.
SCENE_DOORS_TOKEN = "SCENE_DOORS"
#: The walk could not run at all, by name.  Never an exception.
#: DELIBERATELY NOT A PREFIX OF THE OTHER (pf-adversary D5): a test that asked
#: `line.startswith(SCENE_DOORS_TOKEN)` was satisfied by a run in which every
#: scene refused, so the refusal token is checked for on its own.
SCENE_DOORS_REFUSED_TOKEN = "SCENE_DOORS_STOOD_DOWN"

REFUSE_NOT_A_LIVE_SCENE = "not_a_live_scene"
REFUSE_ROSTER_UNREADABLE = "roster_unreadable"
REFUSE_LEGACY_NOT_A_SERIALIZER = "legacy_not_a_serializer"

#: How much of a scene name may reach a console line, and it is a REAL bound
#: rather than a tidy one (pf-adversary D5): this module's own entry points
#: take the scene from a caller, the bridge console is cp874, and a name that
#: is 5,000 characters long or carries a U+2011 turns one report line into an
#: encode error inside a `print`.  Names are truncated and non-ASCII is
#: escaped before anything is formatted.
SCENE_NAME_ON_A_CONSOLE_LINE = 32

#: The attacker the walk swings with.  A ceiling combatant on purpose: this
#: module measures whether a door OPENS, not how long a monster survives, and
#: a walk that had to model the damage ladder would be measuring
#: ``mob_combat``'s arithmetic instead of the door.  The identity is the same
#: placeholder ``tests/test_mob_death.py`` swings with.
WALKER_IDENTITY = 0x750059
WALKER = mob_combat.Combatant(level=1000, ability_str=100000, ability_con=0)

#: How many seeded rolls decide the drop door for one row.  A drop is a
#: PERCENTAGE per slot, so one seed that rolls nothing is not a closed door
#: and one seed that rolls something is not a proof about the table -- the
#: sweep separates "this row drops sometimes" from "32 seeds and nothing".
#: ~~what separates "this row's sets are not in the shipped tables at all"
#: (0 of N, always, for every N) from "this row drops sometimes"~~ IS STRUCK,
#: pf-adversary D7: a set id genuinely absent from the shipped tables makes
#: `mob_loot._set_rows` REFUSE, which stops the sweep at its first seed, so the
#: sweep never produces that shape and cannot be the thing that separates it.
#: What tells the two apart is :attr:`RowDoors.drop_sets` (how many sets the
#: row's own MOBS entry names at all) read next to the seed count.
#: Bounded and fixed so two runs of this module answer identically.
DROP_SEEDS = tuple(range(32))


@dataclass(frozen=True)
class RowDoors:
    """One roster row, and which doors it went through."""

    placement_index: int
    template_id: int
    actor_identity: int
    target: bool = False
    kill: bool = False
    drop: bool = False
    #: How many of the three drop tables this row's own MOBS entry NAMES.
    #: Zero and "named sets that never rolled" are different facts and the
    #: booleans cannot tell them apart (pf-adversary D7).
    drop_sets: int = 0
    seeds_that_dropped: int = 0
    #: How many of :data:`DROP_SEEDS` were actually walked.  A refusal stops
    #: the sweep, so a count short of ``len(DROP_SEEDS)`` says the drop answer
    #: is PARTIAL rather than measured to the end (pf-adversary D11).
    seeds_walked: int = 0
    ruling: str = ""
    refusals: tuple = ()

    @property
    def every_door_open(self) -> bool:
        return self.target and self.kill and self.drop


@dataclass(frozen=True)
class SceneDoors:
    """One scene's rows, walked.  ``reason`` set means the walk never ran."""

    scene: str
    rows: tuple = field(default_factory=tuple)
    reason: str = ""
    #: The placement indices the OWNER's refusal list names for this scene.
    #: ``field_mobs.load_roster`` filters them out before the walk ever sees
    #: them.  CARRIED AND PRINTED BECAUSE THE VERDICT IS A FRACTION
    #: (pf-adversary D2): without this number "no shipped row failed" can be
    #: made true by not shipping the row that fails -- measured, putting
    #: Bg0015's placement 87 on this list turns that scene's verdict from
    #: ``no`` to ``yes`` while Carlos is exactly as unkillable as before.
    #:
    #: AN UPPER BOUND ON THE ROWS REMOVED, NOT THE COUNT, and the difference
    #: is live: ``Bg0002``'s list names eight indices, its shipped table
    #: carries seventeen rows, and only five of the eight are among them, so
    #: the roster hands over twelve.  The exact intersection needs the
    #: pre-filter table, which ``field_mobs`` keeps private on purpose; an
    #: EMPTY list is exact either way, which is what the two scenes this
    #: round reports on have.
    owner_refused: tuple = ()
    #: Did ``mob_ai_control.open_register`` open for this roster, and its name
    #: if it did not.  The register is the call the module header's own
    #: cautionary tale is about, and a scene whose register refuses has no
    #: target door at all no matter what ``strike`` says (pf-adversary D8).
    ai_register: bool = False
    ai_refusal: str = ""

    def _count(self, door: str) -> int:
        return sum(1 for row in self.rows if getattr(row, door))

    @property
    def rows_walked(self) -> int:
        return len(self.rows)

    @property
    def targetable(self) -> int:
        return self._count(DOOR_TARGET)

    @property
    def killable(self) -> int:
        return self._count(DOOR_KILL)

    @property
    def dropping(self) -> int:
        return self._count(DOOR_DROP)

    @property
    def every_door_open(self) -> bool:
        """Every row THE ROSTER HANDS A SESSION went through all three doors.

        ~~Every SHIPPED row~~ IS STRUCK BEFORE THIS EVER REACHED A LETTER
        (pf-adversary D2): the rows here are what ``field_mobs.load_roster``
        returns, which is the shipped placements MINUS the ones the owner
        refused, and those two are already different at HEAD -- ``Bg0002``
        ships 17 and the roster hands over 12.  The sentence this property can
        honestly support is the narrower one, and :attr:`owner_refused` is
        printed next to it so a reader can see the denominator rather than
        take it on trust.  Refusing a placement makes a scene EASIER to
        finish here, and that is exactly why the number travels.

        EVERY ROW AND NOT "AT LEAST ONE", because the condition COO-DECISION
        2026-09-04T14:50+07:00 item 3 sets is about a SCENE being finished,
        and a scene where eleven of twelve monsters die and the twelfth
        stands at 0 HP for ever is not a finished scene -- it is the exact
        state that letter's own item 3 exists to stop this lane walking past.
        A walk that never ran is never "open" (``reason`` is checked first),
        and neither is an empty roster, and neither is a scene whose AI
        register refused (:attr:`ai_register`) -- the roster may be perfect
        and still have no target door, which is the shape
        ``mob_combat_bg0015_gates`` was written about.
        """
        return (
            bool(self.rows) and not self.reason and self.ai_register
            and all(row.every_door_open for row in self.rows))

    @property
    def rows_short_of_every_door(self) -> tuple:
        """The rows that did NOT go through all three, in roster order."""
        return tuple(row for row in self.rows if not row.every_door_open)


def _require_serializer(legacy: Any) -> bool:
    """The frozen v141 handle, checked by the names this walk will call.

    The same shape check ``DropLedgerCell._boundary_frames`` makes, for the
    same reason: a walk handed something that is not the serializer refuses
    by name instead of unwinding out of a diagnostic with an
    ``AttributeError`` a reader has to decode.
    """
    return all(callable(getattr(legacy, name, None))
               for name in ("u32tag", "u8tag", "u16tag", "f32tag", "frame_pc"))


def _drop_sets_named(mob: Any) -> int:
    """How many of the three drop tables this row's own MOBS entry names.

    Read off ``FieldMob``'s own columns rather than through
    ``mob_loot._set_rows``, which RAISES for a set id the shipped tables do
    not carry: the point of this number is to tell "names nothing" from
    "names something that never rolled", and a function that refuses on the
    second case cannot be the thing that measures the first.
    """
    return sum(
        1 for name in ("drops_normal", "drops_equipment", "drops_specially")
        if isinstance(getattr(mob, name, 0), int) and getattr(mob, name, 0))


def _walk_row(legacy: Any, mob: Any, ai_open: bool) -> RowDoors:
    """One row through all three doors.  NEVER RAISES.

    Every door is tried even when an earlier one refused, so a report says
    "targetable, not killable, drops" rather than stopping at the first
    closed door and leaving the rest unmeasured -- which is how a scene gets
    called finished on the strength of the one door somebody checked.

    ``ai_open`` is the scene's AI register, opened once by the caller.  The
    TARGET door needs both halves: a live dispatch reaches
    ``mob_ai_control.open_register`` BEFORE it reaches ``mob_combat.strike``
    (``runtime._sync_combat_scene_state``, the call this lane's own
    ``mob_combat_bg0015_gates`` was written about), so a row whose scene
    cannot open a register is not targetable however well ``strike`` composes.
    """
    refusals: list = []
    target = kill = drop = False
    ruling = ""
    seeds_that_dropped = 0
    seeds_walked = 0
    outcome = None
    drop_sets = _drop_sets_named(mob)

    try:
        step = mob_combat.strike(
            legacy, None, mob_combat.open_ledger((mob,)), None, mob,
            WALKER_IDENTITY, WALKER)
        outcome = step.outcome
        target = bool(step.announce_frame or step.bar_frame) and ai_open
    except Exception as error:                          # noqa: BLE001
        refusals.append("%s:%s" % (DOOR_TARGET, _named(error)))

    if outcome is not None:
        try:
            ruling = mob_death.ruling_for(mob) or ""
        except Exception as error:                      # noqa: BLE001
            refusals.append("%s:%s" % (DOOR_KILL, _named(error)))
            ruling = ""
        else:
            try:
                death_step = mob_death.kill(
                    legacy, mob, outcome, widened=ruling or None)
                kill = bool(death_step.dying_frame and death_step.dead_frame)
            except Exception as error:                  # noqa: BLE001
                refusals.append("%s:%s" % (DOOR_KILL, _named(error)))

    if kill:
        for seed in DROP_SEEDS:
            seeds_walked += 1
            try:
                cell = mob_loot.DropLedgerCell()
                cell.enter_scene(mob.scene)
                fresh = mob_death.kill(
                    legacy, mob, outcome, widened=ruling or None)
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                rows = cell.loot_a_kill(
                    mob, fresh.record, roll,
                    kill_token=fresh.register.generation, position=None)
            except Exception as error:                  # noqa: BLE001
                refusals.append("%s:%s" % (DOOR_DROP, _named(error)))
                break
            if rows:
                seeds_that_dropped += 1
        drop = seeds_that_dropped > 0

    # THE RECORD IS BUILT INSIDE A ``try`` TOO, and that is not belt-and-
    # braces: three of its fields are read off the mob, and "never raises" is
    # a promise about the whole function, not about the part of it that was
    # interesting to write.  A row this cannot even describe comes back as a
    # row with every door shut and the reason on it.
    try:
        return RowDoors(
            placement_index=int(getattr(mob, "placement_index", -1)),
            template_id=int(getattr(mob, "template_id", -1)),
            actor_identity=int(getattr(mob, "actor_identity", -1)),
            target=target, kill=kill, drop=drop,
            drop_sets=drop_sets,
            seeds_that_dropped=seeds_that_dropped,
            seeds_walked=seeds_walked,
            ruling=ruling if type(ruling) is str else "",
            refusals=tuple(refusals),
        )
    except Exception as error:                          # noqa: BLE001
        return RowDoors(
            placement_index=-1, template_id=-1, actor_identity=-1,
            refusals=tuple(refusals) + ("row:%s" % _named(error),))


def _named(error: Exception) -> str:
    """A refusal NAME where there is one, the type where there is not.

    THE ``reason`` ATTRIBUTE FIRST, and it is not interchangeable with
    ``args[0]``: ``mob_death.MobDeathContractError`` joins its reason and its
    detail into ``args[0]`` (measured -- ``ruling_for``'s refusal arrives as
    244 characters of prose beginning with the name), while
    ``mob_loot.MobLootContractError`` keeps ``args[0]`` bare.  A walk that
    read only ``args[0]`` would report the death lane's refusals as
    ``MobDeathContractError`` and lose the one word a reader wants.  The type
    is the honest fallback for an error that carries neither -- an
    ``AttributeError`` out of a wrong handle, say.
    """
    try:
        reason = getattr(error, "reason", None)
        if type(reason) is str and reason:
            return reason[:60]
        first = error.args[0] if error.args else ""
        if type(first) is str and first and " " not in first:
            return first[:60]
    except Exception:                                   # noqa: BLE001
        # This runs INSIDE an ``except`` on a path that promises never to
        # raise, so an error whose own ``reason`` or ``args`` raises may not
        # be allowed to replace the refusal it was being named for.
        pass
    return type(error).__name__


def walk_scene(legacy: Any, scene: Any) -> SceneDoors:
    """Walk every row ``scene``'s roster hands a session, through all doors.

    NEVER RAISES, like every other entry point this lane writes that a
    console line may end up calling: a diagnostic that can unwind its caller
    is a diagnostic nobody may wire.  Including the loop itself and the
    record it builds -- pf-adversary D6 measured a ``TypeError`` escaping
    from the one field read that sat outside a ``try``.
    """
    label = scene if type(scene) is str else ""
    if not _require_serializer(legacy):
        return SceneDoors(label, reason=REFUSE_LEGACY_NOT_A_SERIALIZER)
    try:
        live = field_mobs.live_scenes()
    except Exception:                                   # noqa: BLE001
        return SceneDoors(label, reason=REFUSE_ROSTER_UNREADABLE)
    if label not in live:
        return SceneDoors(label, reason=REFUSE_NOT_A_LIVE_SCENE)
    try:
        roster = field_mobs.load_roster(scene=label)
        refused = tuple(field_mobs.owner_refused_placements(label))
    except Exception:                                   # noqa: BLE001
        return SceneDoors(label, reason=REFUSE_ROSTER_UNREADABLE)

    # THE REGISTER IS OPENED ONCE, FOR THE ROSTER, because that is how a live
    # dispatch does it (``runtime._sync_combat_scene_state``) and because the
    # refusal it can raise is about the SCENE's mined AI rows, not about one
    # monster.  Its name travels; a scene with no register has no target door.
    ai_open, ai_refusal = False, ""
    try:
        mob_ai_control.open_register(roster)
        ai_open = True
    except Exception as error:                          # noqa: BLE001
        ai_refusal = _named(error)

    try:
        rows = tuple(_walk_row(legacy, mob, ai_open) for mob in roster)
    except Exception:                                   # noqa: BLE001
        return SceneDoors(label, reason=REFUSE_ROSTER_UNREADABLE,
                          owner_refused=refused, ai_register=ai_open,
                          ai_refusal=ai_refusal)
    return SceneDoors(label, rows, "", refused, ai_open, ai_refusal)


def walk_live_scenes(legacy: Any) -> tuple:
    """Every live scene, walked, in ``field_mobs.live_scenes()`` order."""
    try:
        live = field_mobs.live_scenes()
    except Exception:                                   # noqa: BLE001
        return (SceneDoors("", reason=REFUSE_ROSTER_UNREADABLE),)
    return tuple(walk_scene(legacy, scene) for scene in live)


def _console_scene(scene: Any) -> str:
    """A scene name that cannot break the line it is printed on.

    TRUNCATED AND ASCII-ESCAPED, and both halves were measured on this
    module's own entry points (pf-adversary D5): ``walk_scene`` takes the
    scene from a caller, so a 5,000-character name produced a 5,052-character
    "bounded" line, and one U+2011 in a name copied out of a document made
    the bridge's cp874 ``print`` raise inside the report.  ``ascii()`` escapes
    rather than drops, so a name that was wrong is still recognisable in the
    line that says so.
    """
    text = scene if type(scene) is str else ""
    # ``ascii()`` of the slice, then its own quotes stripped: the escaping is
    # what is wanted, the quoting is added by the format string so that a
    # truncation marker sits outside it rather than inside the name.
    escaped = ascii(text[:SCENE_NAME_ON_A_CONSOLE_LINE])[1:-1]
    if len(text) > SCENE_NAME_ON_A_CONSOLE_LINE:
        return escaped + "..."
    return escaped


def describe_scene_doors(walked: SceneDoors) -> str:
    """One bounded ASCII console line.  G-OBS."""
    if walked.reason:
        return "%s scene='%s' reason=%s" % (
            SCENE_DOORS_REFUSED_TOKEN, _console_scene(walked.scene),
            walked.reason[:60])
    return (
        "%s scene='%s' rows=%d owner_refusal_list=%d ai=%s target=%d kill=%d "
        "drop=%d every_door=%s short=%s"
        % (
            SCENE_DOORS_TOKEN, _console_scene(walked.scene),
            walked.rows_walked, len(walked.owner_refused),
            "open" if walked.ai_register else (walked.ai_refusal or "shut"),
            walked.targetable, walked.killable, walked.dropping,
            "yes" if walked.every_door_open else "no",
            ",".join(
                "%d/t%d" % (row.placement_index, row.template_id)
                for row in walked.rows_short_of_every_door) or "none",
        )
    )


def describe_live_scene_doors(legacy: Any) -> tuple:
    """The console block a boot can print: one line per live scene.

    THE LINE A READER IS LOOKING FOR IS THE LAST ONE.  ``every_door=yes`` on
    any scene is the condition COO-DECISION 2026-09-04T14:50+07:00 item 3
    puts on scene 4 coming back into the queue, so the summary states it
    once rather than leaving a reader to join the per-scene lines by eye --
    and it carries the owner-refused total beside it, because "no shipped row
    failed" is a fraction and the cheapest way to make it true is to stop
    shipping the row that fails (pf-adversary D2).
    """
    walked = walk_live_scenes(legacy)
    lines = [describe_scene_doors(one) for one in walked]
    finished = tuple(
        _console_scene(one.scene) for one in walked if one.every_door_open)
    lines.append(
        "%s summary live_scenes=%d owner_refusal_list=%d every_door=%s"
        % (SCENE_DOORS_TOKEN, len(walked),
           sum(len(one.owner_refused) for one in walked),
           ",".join(finished) or "none"))
    return tuple(lines)


# ---------------------------------------------------------------------------
# THE ONE LINE A CALL SITE WOULD ADD, kept as a string so a test can read it
# rather than a reader checking it by eye -- the discipline
# ``mob_pickup_request.MOB_PICKUP_REQUEST_HEADLINE_CALL`` is held to on this
# lane, and for the reason recorded there: a wiring note that is only ever
# grepped for substrings will carry a swapped argument order for days.
#
# THERE IS NO CALL SITE TODAY AND THIS MODULE DOES NOT ASK FOR ONE AS A
# BLOCKER.  The walk answers a question a round asks, and a round can call it
# from a test.  ``runtime.py`` is the chief's file; if he wants the block at
# census time next to ``mob_death.describe_widening_coverage()``, this is the
# line, and nothing in this lane waits on it.
# ---------------------------------------------------------------------------
SCENE_DOOR_WALK_CENSUS_CALL = (
    "for line in scene_door_walk.describe_live_scene_doors(legacy): "
    "print(line, file=sys.stderr)"
)
