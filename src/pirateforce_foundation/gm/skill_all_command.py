"""GM `/skill all`: put every curriculum skill on the selected character.

PANYA-ORDER 2026-09-08 ~14:5x (`pf_bridge/notes_to_chief/20260908_1455_KA1A-
PANYA-ORDER-COO-gm-sandbox-skill-all-job-no-level-gate-class-weapons.md`,
section 2.1), routed by `COO-DECISION 20260908_1541`.  The owner wants ONE
GM character holding every class's skills, so that after `/job <class>` +
relog she can watch that class's own list come out on a training dummy
without rolling five characters and without levelling any of them.

WHAT THIS MODULE DOES.

  * IT WRITES `character_skills` rows through LANE-DB's `store.grant_gm_
    skills(character_id, skill_ids)`, ONE CALL FOR THE WHOLE LIST, and the
    rows it writes carry `source='gm_grant'`.
    ~~"through `store.grant_learned_skill`, ONE CALL PER SKILL"~~ -- STRUCK
    by `COO-DECISION 20260908_1943` (choice 2), answering this lane's own
    `20260908_1805` ask.  The old door writes `source='learned'`, and a row
    an operator was handed is not a row the character learned: that is a
    false sentence about the player in the owner's database, which
    `COO-DECISION 20260901_1059` forbids in as many words.  The new door
    writes the value `migrations/018_character_skills_gm_grant_source.sql`
    exists to admit, and is the only writer of it in the codebase.  It is
    also ONE `BEGIN IMMEDIATE` transaction over the whole list, so this
    command no longer has a partial-run state at all -- an operator's
    `/skill all` lands whole or leaves nothing behind.
    A SKILL THE CHARACTER ALREADY HOLDS KEEPS THE PROVENANCE IT HAS: the
    door is `INSERT OR IGNORE`, deliberately not `OR REPLACE`, so a
    `'starting_kit'` row is not re-minted as a GM grant.
    NO ROW ALREADY WRITTEN AS `'learned'` BY THE OLD CALLER IS REPAIRED,
    and not repairing them is a decision rather than an omission:
    `COO-DECISION 20260908_1943` records that those rows live in attended
    run copies rather than in any canonical database, so there is no
    backfill ticket and `character_skills` has no deleter for this lane to
    reach for.
  * THE SKILL IDS COME FROM THE COMMITTED TABLE, NEVER FROM A LIST IN THIS
    FILE.  `class_skill_curriculum` reads
    `data/class_skill_curriculum.tsv` under a sha256 pin, so a hand-edited
    table fails at import instead of quietly granting a different set.
    PANYA-ORDER section 2.1 forbids a hardcoded id list in as many words,
    and `tests/test_gm_job_and_skill_all_commands.py` pins that this module
    contains no skill-id literal at all.
  * IT IS IDEMPOTENT because the door is: `INSERT OR IGNORE` against
    `UNIQUE(character_id, skill_id)`.  Typing `/skill all` twice writes
    nothing the second time and reports `granted=0 already=<all of them>`,
    which is the answer that tells a tester the command ran rather than the
    answer that hides it.
  * THE COUNT COMES FROM THE DOOR'S OWN READ-BACK, NOT FROM THE FACT THAT
    THE CALL RETURNED, and `COO-DECISION 20260908_1943` makes that half of
    the swap a condition of it rather than a nicety: `grant_gm_skills`
    returns every distinct skill id on the row, read INSIDE its own
    transaction, so `granted=` is that set MINUS the set read before the
    call.  pf-adversary (round `wv0fpe`, D3) measured what an earlier draft
    did instead: it counted a call as a grant whenever the door returned,
    so a character already holding every id, on a store whose "what do you
    hold" reader was momentarily unreadable, printed `granted=<all of them>`
    after inserting nothing -- and the owner's `HEADLESS_PROOF:` grep reads
    exactly that number.  Two guards stand where that hole was: the opening
    read is MANDATORY (its refusal is `REFUSED_CANNOT_READ_CURRENT_SKILLS`),
    and a door whose return value cannot be measured makes the line say
    `granted_from=door_contract` so a derived number is never presented as
    a measured one.

THE 1024 BUCKET IS INCLUDED, AND SAYING SO IS PART OF THE PRODUCT.
`class_skill_curriculum`'s own docstring records that 1024 is NOT PROVEN to
be a sixth class or an every-class bucket -- what is measured is that it
holds 11 ids none of which fall inside any of the five class blocks, and
that three of them are the ids all five classes share.  The owner's order
says to grant it WITH the five and to say so out loud rather than silently
("if bucket 1024 makes the client misbehave, split it into `/skill all raw`
LATER -- do not go quiet"), so the console line names the buckets it drew
from, 1024 included, and this module carries no per-bucket opinion.

WHAT IT DOES NOT DO, so no ticket can over-read it.

  * NO FRAME.  The skill LIST the client draws is sent at login by LANE-CS's
    login-time skill-list composer (`#1079`), which has no caller in
    `runtime.py` yet -- that seam is LANE-CS's first job in `NOW.md` and not
    this lane's to wire.  So the rows land now and the K window fills in when
    that seam lands; until then this command's product is rows, and its
    console line says exactly that.  A row written is not a skill on screen.

    THAT MODULE'S NAME IS DELIBERATELY NOT SPELLED ANYWHERE IN THIS FILE,
    and the omission is load-bearing rather than shy -- the same discipline
    `gm/level_command.py`'s docstring records for two other modules.  Its own
    test file counts the files under `src/` whose TEXT contains its name and
    prints that count as `callers_in_src=<n>`; a citation here would raise
    that number by one without adding a caller, turning another lane's suite
    red and, worse, making their "nothing calls this yet" evidence read as
    false.  `tests/test_gm_job_and_skill_all_commands.py` -- which that scan
    does not read -- is where the tie to it can be written down.
  * NO LEVEL GATE IS TOUCHED, because there is none to touch.  PANYA-ORDER
    section 2.4 asks that a GM not be refused by `n_LEVEL_LEARN` and says a
    negative result is a result.  MEASURED this round, by grep over `src/`
    for both `n_LEVEL_LEARN` and `level_learn`: the column is read in two
    accessors only -- `skill_catalog.level_learn` and
    `class_skill_curriculum.level_learn`/`curriculum_by_level_learn` -- and
    the grep for callers of those accessors outside their own modules
    returns THIS FILE and nothing else.  They are readers; no learn path, no
    cast path and no grant path in this repository consults a level before
    allowing a skill.  So there is NO GATE TO UNLOCK today, and this module
    adds none.  (The negative is stated with its grep, per the house rule
    that a sentence saying "there is no X" carries the search that looked.)  `pf_bridge/notes_to_chief/<this round>_LANE-GM-TO-LANE-K-*`
    carries that as a debt for the day a production learn path exists.
  * NO SKILL POINTS ARE SPENT.  `grant_gm_skills` is the grant half only;
    LANE-CS's `skill_learn_wiring.learn_skill_spend` is the paying half and
    this is a GM tool, not a learn.  A GM sandbox that charged for its own
    skills would be a worse tool and a lie about the economy.  The row's
    `source='gm_grant'` is what keeps the two tellable apart afterwards,
    which is the second thing the provenance buys.

NOT AN M-ANYTHING.  Skills granted by a GM are a way to REACH a testable
state, never evidence that learning skills works
(`prompts/LANE-GM.md`, sentence 3).
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import class_skill_curriculum as _curriculum


#: The only argument `/skill` answers to today.  A word, not a flag: the
#: owner typed `/skill all` and the grammar keeps her spelling.  Spelled
#: once here and raised by `commands.parse_gm_command` from the same value,
#: so the parser and the usage sentence cannot drift apart.
SUBCOMMAND_ALL = "all"

REFUSED_ARGS_SHAPE = "args_not_a_one_string_tuple"
REFUSED_UNKNOWN_SUBCOMMAND = "unknown_skill_subcommand"
REFUSED_NO_CHARACTER = "no_selected_character"
REFUSED_NO_STORE = "no_store_on_this_session"
REFUSED_ROW_MISSING = "row_not_found"
REFUSED_NOTHING_GRANTED = "no_skill_could_be_granted"
#: THE GRANT DOOR THREW ITS OWN TRANSACTION AWAY.  `grant_gm_skills` raises
#: `RuntimeError` when its post-insert read-back cannot find an id it just
#: inserted, which on a database missing `migrations/018_character_skills_
#: gm_grant_source.sql` is EVERY id: the `CHECK` on `character_skills.source`
#: rejects `'gm_grant'` and `INSERT OR IGNORE` swallows that as quietly as
#: the UNIQUE conflict it is there for.  Named apart from
#: `REFUSED_NOTHING_GRANTED` because the thing to LOOK AT is specific --
#: `schema_migrations` on the database this process opened -- and the
#: generic reason would have sent the operator hunting a broken store.
REFUSED_GRANT_ROLLED_BACK = "grant_transaction_rolled_back"
#: HOW THIS MODULE RECOGNISES THAT ROLLBACK AND NOTHING ELSE (pf-adversary
#: round `ve2zs4`, D6).  `store` is annotated `object` on purpose -- any
#: object carrying the door is accepted -- so "the exception was a
#: `RuntimeError`" is NOT evidence that it came from the read-back above.
#: `RuntimeError` is also what a generator raises on a re-entered
#: `__next__`, what `dict` iteration raises when it is mutated underneath,
#: and what any wrapper store may raise for reasons of its own; every one
#: of those would have been reported to the operator as "go and read
#: `schema_migrations` on this database", sending her to inspect a database
#: that is fine.  `SQLiteStore.grant_gm_skills` opens its rollback message
#: with its own name, so the message IS the evidence, and a `RuntimeError`
#: that does not carry it falls through to the generic branch, which names
#: the exception TYPE instead of guessing a cause.
#: MATCHED AS A PREFIX, NOT AS A SUBSTRING, and that choice is measured
#: rather than tidy (pf-adversary, this round, D-D).  `in` accepts a WRAPPER
#: store's message that merely mentions the method it was calling -- the
#: commonplace `f"{fn.__name__}: {error}"` annotation -- and
#: `"connection pool exhausted while calling grant_gm_skills: giving up"`
#: would have been reported as a rolled-back grant, which is the exact
#: damage D6 exists to stop, only narrower.  `startswith` errs the other
#: way: a wrapper that PREFIXES the door's message loses the specific
#: reason and gets the generic one, which names the exception type and
#: sends the operator nowhere false.  Of the two mistakes only one lies to
#: her, so the comparison leans away from it.
#: THE COUPLING IS PINNED BY BEHAVIOUR, not by reading source
#: (pf-adversary, this round, D-A, which measured the source-reading
#: version passing green with the signature moved into a trailing comment,
#: and passing again through a `functools.wraps` decorator whose runtime
#: message carried nothing of the kind).  `test_the_grant_door_really_signs_
#: the_rollback_it_raises` opens a database stopped at migration 017, calls
#: the real door, and reads the message it really raised -- the cheap
#: version of a shared exception class, which would have to be declared in
#: `store.py` and that file is LANE-DB's zone, not this lane's.
GRANT_DOOR_ROLLBACK_SIGNATURE = "grant_gm_skills:"
#: The `before` read is MANDATORY, not best-effort, and that is a change of
#: posture rather than a new check (pf-adversary round `wv0fpe`, D3).  Every
#: number this command prints is derived from it; a store that cannot answer
#: "what does this character hold now" cannot be given a countable answer,
#: and the owner asked for a COUNTABLE token.  Refusing is honest; printing
#: `granted=137` for a run that inserted nothing is not.
REFUSED_CANNOT_READ_CURRENT_SKILLS = "current_skills_could_not_be_read"


class SkillArgumentError(ValueError):
    """`/skill`'s argument is not one this module will act on."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def usage() -> str:
    """The one sentence a human gets back for a bad argument."""
    return f"skill {SUBCOMMAND_ALL}"


def bucket_codes() -> tuple[int, ...]:
    """Every bucket code this command draws from: the five classes + 1024.

    READ FROM THE COMMITTED TABLE, never retyped -- `CURRICULUM_CLASS_IDS`
    is built from the file's own distinct `n_PPCLASS` values MINUS the
    shared bucket, and `SHARED_BUCKET_CODE` is that bucket, so the two
    together are every code the table carries and a table that grows a
    bucket grows this command with it.
    """
    return tuple(
        sorted(
            (*_curriculum.CURRICULUM_CLASS_IDS, _curriculum.SHARED_BUCKET_CODE)
        )
    )


def all_skill_ids() -> tuple[int, ...]:
    """Every skill id in the curriculum table, ascending, no duplicates.

    `CURRICULUM_SKILL_IDS` is already the sorted distinct set across every
    bucket, so the five class blocks AND the 1024 bucket are in it, which is
    what the owner asked for.  Returned rather than iterated in place so a
    caller (and a test) can count it.
    """
    return tuple(_curriculum.CURRICULUM_SKILL_IDS)


@dataclass(frozen=True)
class SkillGrant:
    """What one `/skill all` did, in the shape the console line reads.

    `granted` is the grant door's own returned id set MINUS the set read
    before the call -- i.e. rows that were not on the row before and are now;
    `already` counts curriculum ids the character held before it ran;
    `failed` counts curriculum ids the row STILL does not hold after a
    refusal, and is zero on every success because the door is one
    transaction and cannot half-write.

    ~~"The three add up to `len(all_skill_ids())` on every path"~~ -- STRUCK
    (pf-adversary round `wv0fpe`, D8): they do not on the two refusals that
    return before the loop, and they need not under concurrency, where
    another writer's inserts land inside this run's two reads and `granted`
    honestly counts rows this process did not write.  `counts_are_complete`
    below says which of the two cases a reader is holding, instead of a
    docstring promising an invariant the code cannot keep.
    """

    granted: int
    already: int
    failed: int
    #: False when the grant door returned something this module could not
    #: turn into a set of ids, so `granted` fell back to the door's own
    #: CONTRACT (a return means every id handed in is on the row) instead of
    #: to a measurement.  The console line says `granted_from=door_contract`
    #: when this is False, and says nothing extra when it is True -- a
    #: derived number announces itself, a measured one does not need to.
    counts_are_complete: bool
    refusal: str | None
    detail: str
    #: WAS `store.grant_gm_skills` ACTUALLY ENTERED?  The one thing this
    #: module KNOWS about whether rows may be on disk, as opposed to the
    #: thing it used to assume (pf-adversary, this round, D-C).
    #:
    #: `granted == 0` was standing in for "nothing was written", and that
    #: substitution only holds for a store whose door is one transaction AND
    #: whose read-back reports every row it wrote -- i.e. for `SQLiteStore`,
    #: the very assumption D6 has just finished removing from the branch
    #: above.  A store that writes and then under-reports gives
    #: `granted == 0` with the whole curriculum on disk, and the dispatcher,
    #: reading no undo, told the operator "anything it had in hand was
    #: dropped with it".  That is `wv0fpe` D2 come back.
    #:
    #: This field asks a question with an answer instead: the call either
    #: happened or it did not.  `chat_command_action._skill_action` attaches
    #: its always-`False` undo -- which reaches the console as "the effect
    #: was KEPT" -- to every outcome where it did, because a refusal that
    #: MIGHT have left rows must not be announced as one that left none.
    #: Defaulted so the refusals that return before the call keep reading as
    #: five positional arguments, the shape that broke twice already
    #: (`nkb608` D-A, `nboppe` D1).
    door_was_called: bool = False

    @property
    def ok(self) -> bool:
        return self.refusal is None


#: The third answer `_read_skills` can give: the store answered, and what it
#: said is "there is no such character".  A sentinel rather than an exception
#: because this module's contract is that nothing here raises.
_ROW_MISSING = object()


def _read_skills(store: object, character_id: int) -> object:
    """Every skill id the row holds, or `None` for "could not be read".

    NEVER RAISES, AND NEVER SUBSTITUTES AN EMPTY SET FOR AN ANSWER IT DID
    NOT GET.  ~~"an unreadable before is not a reason to refuse... the
    read-back below corrects the totals"~~ -- STRUCK (pf-adversary round
    `wv0fpe`, D3): there was no read-back below, and an empty set stood in
    for "unknown" on both sides of the subtraction that produces `granted`.
    A character already holding every curriculum skill, on a store whose
    reader was momentarily unavailable, printed `granted=<all of them>`
    after inserting nothing.  `None` is the honest answer and the caller
    decides what to do with it.
    """
    reader = getattr(store, "list_character_skills", None)
    if reader is None:
        return None
    try:
        return frozenset(int(i) for i in reader(character_id))
    except KeyError:
        # A SEPARATE ANSWER FROM "the store could not be read" (pf-adversary
        # round `nkb608`, D-K).  `SQLiteStore.list_character_skills` raises
        # `KeyError` for a character id with no live row -- deleted, soft-
        # deleted, or never there -- and folding that into `None` sent the
        # operator to look at the store when the fault was the character.
        # Nothing is written on either branch; only the sentence differs.
        return _ROW_MISSING
    except Exception:  # noqa: BLE001 -- see the docstring
        return None


def _unnamed_store_failure(
    error: BaseException, already: int, outstanding: int
) -> SkillGrant:
    """The one sentence for a store exception this module cannot place.

    ONE function and not two copies of the same three lines, because the
    `RuntimeError` branch now hands its unrecognised cases here (pf-adversary
    round `ve2zs4`, D6) and two hand-written copies of "name the type" are
    two sentences that drift apart on the next edit.

    IT NAMES THE TYPE AND DOES NOT GUESS A CAUSE.  That is the whole
    difference from `REFUSED_GRANT_ROLLED_BACK`: this branch knows only that
    the door raised, so `RuntimeError: dictionary changed size during
    iteration` is what the operator reads, and she goes and looks at the
    store that raised it rather than at a `schema_migrations` table that has
    nothing wrong with it.  `granted` is zero here because the door raised
    instead of returning; `already` and `outstanding` are this run's own
    measurements from before the call and stay reported, for the reason
    `console_line` gives (a refusal that prints no numbers reads as "nothing
    happened").
    """
    return SkillGrant(
        0, already, outstanding, True, REFUSED_NOTHING_GRANTED,
        f"{type(error).__name__}: {error}",
        # THE DOOR WAS ENTERED, so this module cannot say the row is clean.
        door_was_called=True,
    )


def grant_all(store: object, character_id: object) -> SkillGrant:
    """Grant every curriculum skill to `character_id`.  Never raises.

    THE ORDER IS: read what the row holds -> hand the WHOLE id list to
    `store.grant_gm_skills` in ONE call -> count from what that door gave
    back.  There is no per-id loop and so there is no partial run any more:
    the door is a single `BEGIN IMMEDIATE` transaction, so a tester gets
    all 137 skills or none of them, and a run that did not land left
    nothing behind for anyone to clean up.
    ~~"one id that raises does not stop the others, because a tester with
    136 of 137 skills has a usable sandbox"~~ -- STRUCK with the loop it
    described.  That sentence was true of hundreds of independent writes;
    it is false of one transaction, and pf-adversary round `nboppe` D8 (the
    round that caught the count in it going stale) pinned the NUMBER, not
    the reasoning, so the pin moves to the sentence above.

    WHY THIS DOOR AND NOT `grant_learned_skill`, which this function called
    until now (`COO-DECISION 20260908_1943`, choice 2, answering this
    lane's own `20260908_1805` ask).  `grant_learned_skill` writes
    `source='learned'`, and a row an operator was handed is not a row the
    character learned -- exactly the false sentence in the owner's database
    that `COO-DECISION 20260901_1059` forbids.  `grant_gm_skills` writes
    `'gm_grant'`, the value `migrations/018_character_skills_gm_grant_
    source.sql` exists to admit, and it is the only writer of that value in
    the codebase.  A skill the character already holds as `'starting_kit'`
    or `'learned'` KEEPS the provenance it has: the door is `INSERT OR
    IGNORE`, deliberately not `OR REPLACE`.

    THE COUNT IS STILL THE DOOR'S OWN ANSWER, and that is the half of the
    decision the owner's `HEADLESS_PROOF:` grep actually reads.
    `grant_gm_skills` returns every distinct skill id on the row, read back
    INSIDE its own transaction, so `granted` is that set MINUS the set this
    function read before the call.  It is never `len(all_skill_ids())`,
    never a count of calls that returned, and under concurrency -- another
    writer landing the same rows between this command's read and its call
    -- it honestly counts rows now present that were not present before,
    the same caveat `SkillGrant` records for the loop it replaces.

    NOTHING IS WRITTEN ON ANY REFUSAL BRANCH BELOW, and that is a property
    of the door rather than a promise this function keeps by being careful:
    `grant_gm_skills` validates every id before it opens its transaction,
    checks the character row first inside it, and rolls the whole
    transaction back when its own read-back cannot find an id it inserted.
    The refusals therefore print `granted=0` and mean it.

    EVERY failure comes back as a refusal object with a NAMED reason rather
    than an exception, for the reason `gm/level_command.write_level`'s
    docstring gives: an escaping exception on this dispatch unwinds the
    listener thread and parks the client on "connecting".
    """
    if type(character_id) is not int or isinstance(character_id, bool) or character_id <= 0:
        # `counts_are_complete=True` and not an oversight: three zeroes ARE
        # the complete count of what a refusal before the door call wrote.
        # pf-adversary round `nkb608`, D-A: these two exits carried FIVE
        # positional arguments into a six-field record from the round that
        # inserted `counts_are_complete` -- a `TypeError` on the listener
        # thread, which is the escape `write_level`'s docstring exists to
        # forbid.  No test called this function with anything but a valid
        # id, so both lines had never once executed.
        return SkillGrant(
            # `True` for the same reason every sibling refusal below passes
            # it: nothing was attempted, so nothing FELL BACK to counting
            # calls, and `granted_from=calls` must not appear on a line whose
            # counts are three zeros.  THE ARGUMENT WAS MISSING here and at
            # REFUSED_NO_STORE below -- `counts_are_complete` was added to
            # this dataclass in the commit that answered round `wv0fpe`, and
            # five of the seven construction sites were updated -- so both
            # branches raised TypeError instead of refusing.  pf-adversary
            # (round `nboppe`, D1) built them and measured the cost: no
            # console line, no notice, and an `issued` audit row with no
            # `outcome` row.  Two rounds arrived at the same one-word fix
            # independently; what this round adds is the pair of tests that
            # REACH these branches, without which the suite went on proving
            # that the refusal WORDS existed while the code returning them
            # could not run.
            0, 0, 0, True, REFUSED_NO_CHARACTER,
            f"no usable selected character id on this connection ({character_id!r})",
        )
    granter = getattr(store, "grant_gm_skills", None)
    if granter is None:
        # A STORE CARRYING ONLY THE OLD DOOR LANDS HERE, and refusing is the
        # answer rather than falling back to it: `grant_learned_skill` would
        # write `'learned'` for an operator's grant, which is the provenance
        # this swap exists to stop.  A refusal names the missing door; a
        # fallback would put the wrong sentence in the database quietly.
        return SkillGrant(
            # The second of the pair -- see REFUSED_NO_CHARACTER above.
            0, 0, 0, True, REFUSED_NO_STORE,
            "this session's store has no grant_gm_skills door",
        )
    skill_ids = all_skill_ids()
    if not skill_ids:
        # THE DOOR REFUSES AN EMPTY SEQUENCE (`ValueError`, "grant nothing is
        # a caller bug"), so the empty curriculum is answered here instead of
        # being handed over to raise.  `class_skill_curriculum`'s sha pin
        # should fail at import long before this, which is why this is a
        # guard and not a branch anything is expected to take.
        return SkillGrant(
            0, 0, 0, True, REFUSED_NOTHING_GRANTED,
            "the curriculum table carries no skill id to grant",
        )
    wanted = frozenset(skill_ids)
    before = _read_skills(store, character_id)
    if before is _ROW_MISSING:
        return SkillGrant(
            0, 0, 0, True, REFUSED_ROW_MISSING,
            "the selected character has no live row to grant skills to; "
            "nothing was written",
        )
    if before is None:
        # NOTHING IS WRITTEN ON THIS BRANCH, deliberately: the write itself
        # would be harmless (the door is idempotent), but its REPORT would
        # not be, and the owner's `HEADLESS_PROOF:` block reads that report.
        return SkillGrant(
            0, 0, 0, True, REFUSED_CANNOT_READ_CURRENT_SKILLS,
            "this session's store cannot say which skills the character "
            "already holds, so no countable answer can be given; nothing "
            "was written",
        )
    already = len(before & wanted)
    #: What the row is still missing when the door refuses.  Reported as
    #: `failed` rather than as zero because the operator asked for these ids
    #: and did not get them; reporting zero on a refusal would let the line
    #: read as "nothing was needed" (pf-adversary round `wv0fpe`, D4, is the
    #: same lesson from the other side: a refusal that moved rows printed no
    #: numbers at all).
    outstanding = len(wanted - before)
    try:
        returned = granter(character_id, list(skill_ids))
    except KeyError:
        # The character has no live row.  `grant_gm_skills` looks that up as
        # the first statement inside its transaction, before any INSERT, so
        # this branch really did write nothing -- unlike the loop it
        # replaces, where the same refusal could arrive with rows on disk.
        return SkillGrant(
            0, already, outstanding, True, REFUSED_ROW_MISSING,
            f"character {character_id} has no live row to grant against; "
            "nothing was written",
            door_was_called=True,
        )
    except RuntimeError as error:
        # THE MIGRATION THE DOOR NAMES ITSELF.  `INSERT OR IGNORE` swallows a
        # CHECK violation as quietly as the UNIQUE conflict it is there for,
        # so on a database without `migrations/018_character_skills_gm_grant_
        # source.sql` every row of the grant is dropped on the floor; the
        # door's own read-back catches that and rolls back rather than
        # returning normally.  It gets its own reason because the thing to
        # LOOK AT is specific -- `schema_migrations` on the database this
        # process opened -- and `REFUSED_NOTHING_GRANTED` would have sent
        # the operator looking for a broken store instead.
        #
        # ~~"the remedy is to boot the server against that database once, so
        # `app.py`'s `migrate_with_backup()` applies 018"~~ -- STRUCK BEFORE
        # IT SHIPPED, and struck by MEASUREMENT (pf-adversary, this round,
        # D1): `app.py` reaches `migrate_with_backup()` on `--db <file>
        # --self-test-only` (ledger 17 -> 19) but NOT when
        # `--scene-load-scenario` is given as well (ledger 17 -> 17) --
        # that flag sits in the outer branch condition and is absent from
        # the inner one.  An operator told to reboot with the flags she
        # already used would have gone round the same loop and read the
        # same refusal; the sentence now names what to READ instead.  The
        # branch itself is chief's -- LANE-DB asked about it in
        # `pf_bridge/notes_to_chief/20260905_0254` and it is still open.
        #
        # ~~caught by TYPE alone~~ -- STRUCK (pf-adversary round `ve2zs4`,
        # D6).  See `GRANT_DOOR_ROLLBACK_SIGNATURE`: only the door's own
        # signed message earns this reason; every other `RuntimeError` is
        # re-raised into the generic handler below, which names its type.
        # Re-raising rather than duplicating that handler's body keeps ONE
        # place where an unrecognised store exception is turned into a
        # sentence, which is what stopped these two branches drifting apart.
        if not str(error).startswith(GRANT_DOOR_ROLLBACK_SIGNATURE):
            return _unnamed_store_failure(error, already, outstanding)
        return SkillGrant(
            0, already, outstanding, True, REFUSED_GRANT_ROLLED_BACK,
            f"the grant door rolled its whole transaction back: {error}",
            door_was_called=True,
        )
    except Exception as error:  # noqa: BLE001 -- named, never escaping
        # `WriteLockTimeout`, a `TypeError`/`ValueError` from a door whose
        # contract moved, an UNSIGNED `RuntimeError` handed down from the
        # branch above, or anything else a store can raise.  All of them
        # arrive before or instead of a commit, so the counts are zero and
        # the exception TYPE is named for the operator.
        return _unnamed_store_failure(error, already, outstanding)
    try:
        after = frozenset(int(i) for i in returned)
    except Exception:  # noqa: BLE001 -- a door that returned another shape
        after = None
    if after is None:
        # CANNOT MEASURE, SO SAY SO.  The call returned, and by the door's
        # own contract a return means every id handed in is on the row --
        # so the number below is derived from that contract rather than
        # counted.  The line says `granted_from=door_contract` so a reader
        # can tell it apart from a measured one, which is the rule
        # pf-adversary round `wv0fpe` D3 left behind: a number this module
        # could not verify may not be presented as one it measured.
        return SkillGrant(
            outstanding, already, 0, False, None,
            f"{outstanding} granted, {already} already held",
            door_was_called=True,
        )
    # SCOPED TO WHAT THIS COMMAND ASKED FOR.  The door returns the WHOLE
    # row, curriculum ids and anything else the character holds alike, so
    # `after - before` alone would let a concurrent writer's unrelated grant
    # land inside this command's two reads and be counted as a skill
    # `/skill all` put there.  Intersecting with `wanted` cannot hide a row
    # this command caused -- every id it handed over is in `wanted` -- and
    # it keeps the number to the one question the line is asked.
    granted = len((after - before) & wanted)
    short = wanted - after
    if short:
        # THE DOOR CONTRADICTED ITS OWN CONTRACT, and that is checkable
        # without assuming anything about how the store is built.
        # ~~"granted == 0 and already == 0 ... a store that answers this way
        # is not writing"~~ -- STRUCK (pf-adversary, this round, D-E), which
        # measured both halves wrong.  It is not a claim this module can
        # make (the store may have written and under-reported), and the
        # condition MISSED the case that matters: a character already
        # holding one curriculum id gives `already == 1`, so a door that
        # wrote 137 rows and returned a set missing all of them sailed
        # through as a SUCCESS printing `granted=0 ... (no new rows this
        # run)` -- the exact number the owner's `HEADLESS_PROOF:` block
        # greps, with `counts_are_complete=True` promising it was measured.
        #
        # What IS this module's to check is the contract `grant_gm_skills`
        # states in its own docstring: it returns EVERY distinct skill id
        # now on the row.  So an id handed in and missing from the return is
        # the door disagreeing with itself, whatever the reason, and the
        # honest answer is a refusal that says which -- not a count derived
        # from a return value already known to be wrong.  `door_was_called`
        # rides along so the dispatcher does not tell the operator the rows
        # were dropped: this branch is precisely the one where nobody knows.
        return SkillGrant(
            0, already, len(short), True, REFUSED_NOTHING_GRANTED,
            f"the grant door returned without every id it was handed: "
            f"{len(short)} of {len(wanted)} are absent from its own "
            f"read-back (first missing: {min(short)})",
            door_was_called=True,
        )
    return SkillGrant(
        granted, already, 0, True, None,
        f"{granted} granted, {already} already held",
        door_was_called=True,
    )


def undo(store: object, character_id: object):
    """A zero-argument callable that reports what happened to the rows.

    IT ALWAYS RETURNS A CALLABLE AND THAT CALLABLE ALWAYS ANSWERS `False`,
    and both halves are deliberate rather than a stub.

    `_make_action` runs this only when the audit row could not be written,
    and it turns the answer into one of two console sentences: a callable
    that answered `False` prints "the audit row could not be written and the
    effect was KEPT"; NO callable at all prints "anything it had in hand was
    dropped with it".  For this command the first is true and the second is
    false -- the rows are on disk -- so passing no undo, which the first
    draft did, made the console lie about every unaudited run (pf-adversary
    round `wv0fpe`, D2).

    WHY IT CANNOT ACTUALLY PUT THE ROWS BACK, stated so nobody reads
    `False` as "the delete failed": `character_skills` is LANE-DB's table
    and its writers are `grant_starting_skills`, `grant_learned_skill` and
    `grant_gm_skills`, all three `INSERT OR IGNORE`; there is no deleter,
    and this lane may not add one to another lane's table -- `COO-DECISION
    20260908_1943` says so for this round in as many words ("`character_
    skills` has no delete door and I do not approve creating one in this
    round").  A deleter would also have no way to tell the rows THIS run
    inserted from rows the character already held, so the safe residue is a
    skill the GM did not ask to lose.  The command is
    idempotent, so re-running it after a fixed audit costs nothing.

    `store` and `character_id` are accepted and unused, so the call site
    reads like every other undo in this lane and a future deleter has the
    two values it would need without moving the call.
    """

    def _kept() -> bool:
        return False

    return _kept


def _ascii_only(line: str) -> str:
    """Printable ASCII, with everything else replaced by `?`.

    ENFORCED, not asserted: a store exception's message is a reachable
    carrier of foreign text on the partial path, and the bridge console is
    cp874 -- a byte outside it kills the tool reading the line.
    """
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in line)


#: The console token PANYA-ORDER section 2.1 asks for by name.  Its shape is
#: an interface (the owner's `HEADLESS_PROOF:` block greps for it), pinned
#: field by field in `tests/test_gm_job_and_skill_all_commands.py`.
CONSOLE_TOKEN = "GM_SKILL_ALL"


def console_line(result: SkillGrant, character_id: object) -> str:
    """One ASCII line for the SERVER HOST's console.  Never the player's screen.

    `GM_SKILL_ALL cid=<n> granted=<k> already=<m> classes=<...>`, the shape
    PANYA-ORDER 2026-09-08 section 2.1 spells, plus `failed=<k>` ON A
    REFUSAL THAT LEFT IDS OUTSTANDING -- an extra field that appears exactly
    when it is non-zero, so the ordinary line stays the four the owner asked
    for.  A SUCCESS LINE NEVER CARRIES IT NOW: the grant is one transaction,
    so there is no half-written run left to describe, and `failed=` on a
    refusal means "this many curriculum ids the row still does not hold"
    rather than "this many calls raised".

    `classes=` lists the BUCKET CODES drawn from, `1024` included and not
    hidden, for the reason the module docstring gives.  The success wording
    says whether THIS RUN actually wrote a row and that no skill-list frame
    was sent, because both halves are what the tester has to know before she
    grades the K window.

    `(rows written; ...)` NAMES THIS RUN, NOT THE CHARACTER'S HISTORY
    (pf-adversary round `ve2zs4`, D7).  The first draft printed that clause
    on every success, including the idempotent rerun this module's own
    docstring calls out (`granted=0 already=<all of them>`) -- a run that
    wrote nothing on this call claimed "(rows written)" anyway, which is
    exactly the false-positive the door's `INSERT OR IGNORE` idempotence was
    built to make legible, not to hide.  The clause now reads
    `result.granted`, the one field the door's own read-back measured for
    THIS call: `(rows written; ...)` only when it is non-zero, `(no new
    rows this run; ...)` when every id was already on the row.  Either way
    "no skill-list frame was sent" stays true and stays printed.
    """
    classes = ",".join(str(code) for code in bucket_codes())
    failed = f" failed={result.failed}" if result.failed else ""
    degraded = (
        "" if result.counts_are_complete else " granted_from=door_contract"
    )
    if result.ok:
        wrote = "rows written" if result.granted else "no new rows this run"
        return _ascii_only(
            f"{CONSOLE_TOKEN} cid={character_id} granted={result.granted} "
            f"already={result.already}{failed}{degraded} classes={classes} "
            f"({wrote}; no skill-list frame was sent to the live client)"
        )
    if result.granted or result.already or result.failed:
        # A REFUSAL THAT WROTE SOMETHING STILL PRINTS ITS NUMBERS.
        # pf-adversary (round `wv0fpe`, D4) measured the alternative: a
        # character soft-deleted mid-run left 40 rows on disk and the
        # console said `REFUSED [row_not_found]` with no count anywhere, so
        # the operator's only reading was "nothing happened".
        return _ascii_only(
            f"{CONSOLE_TOKEN} REFUSED [{result.refusal}] "
            f"cid={character_id} granted={result.granted} "
            f"already={result.already}{failed}{degraded}: {result.detail}"
        )
    return _ascii_only(
        f"{CONSOLE_TOKEN} REFUSED [{result.refusal}]: {result.detail}"
    )


def parse_subcommand(args: object) -> str:
    """`args` (a `GmCommand.args`) -> the subcommand, or raise.

    SECOND check, deliberately, for the reason
    `gm/job_command.parse_class_id` gives: a module that writes database
    rows repeats the shape check rather than inheriting it.
    """
    if type(args) is not tuple or len(args) != 1 or type(args[0]) is not str:
        raise SkillArgumentError(
            REFUSED_ARGS_SHAPE,
            f"skill takes exactly one string argument; got {args!r}",
        )
    word = args[0].strip().lower()
    if word != SUBCOMMAND_ALL:
        raise SkillArgumentError(
            REFUSED_UNKNOWN_SUBCOMMAND,
            f"skill has no {word!r} form; {usage()}",
        )
    return word
