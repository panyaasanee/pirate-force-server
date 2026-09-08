"""GM `/skill all`: put every curriculum skill on the selected character.

PANYA-ORDER 2026-09-08 ~14:5x (`pf_bridge/notes_to_chief/20260908_1455_KA1A-
PANYA-ORDER-COO-gm-sandbox-skill-all-job-no-level-gate-class-weapons.md`,
section 2.1), routed by `COO-DECISION 20260908_1541`.  The owner wants ONE
GM character holding every class's skills, so that after `/job <class>` +
relog she can watch that class's own list come out on a training dummy
without rolling five characters and without levelling any of them.

WHAT THIS MODULE DOES.

  * IT WRITES `character_skills` rows through LANE-DB's own existing door,
    `store.grant_learned_skill(character_id, skill_id)`, ONE CALL PER SKILL
    -- that door's own docstring says one skill per call is its contract,
    and this lane does not ask for a batch variant it does not need.
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
  * THE COUNTS COME FROM THE DOOR'S OWN READ-BACK, NOT FROM COUNTING CALLS
    THAT DID NOT RAISE.  `grant_learned_skill` returns every distinct skill
    id on the row, read inside its own transaction; a set that GREW across
    a call is the door saying it inserted, a set that stood still is
    `INSERT OR IGNORE` saying it ignored.  pf-adversary (round `wv0fpe`,
    D3) measured what the first draft did instead: it counted a call as a
    grant whenever the door returned, so a character already holding every
    id, on a store whose "what do you hold" reader was momentarily
    unreadable, printed `granted=<all of them>` after inserting nothing --
    and the owner's `HEADLESS_PROOF:` grep reads exactly that number.  Two
    guards now stand where that hole was: the opening read is MANDATORY
    (its refusal is `REFUSED_CANNOT_READ_CURRENT_SKILLS`), and a door whose
    return value cannot be measured makes the line say `granted_from=calls`
    so a fallback number is never presented as a measured one.

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
  * NO SKILL POINTS ARE SPENT.  `grant_learned_skill` is the grant half
    only; LANE-CS's `skill_learn_wiring.learn_skill_spend` is the paying
    half and this is a GM tool, not a learn.  A GM sandbox that charged for
    its own skills would be a worse tool and a lie about the economy.

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

    `granted` counts calls after which the grant door's own returned id set
    GREW -- i.e. rows it really inserted; `already` counts curriculum ids the
    character held before it ran; `failed` counts ids whose grant call
    raised.

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
    #: False when the CLOSING read of the row could not be made, so `granted`
    #: fell back to counting calls that returned.  The console line says
    #: `granted_from=calls` when this is False, and says nothing extra when
    #: it is True -- a degraded measurement announces itself, a good one
    #: does not need to.
    counts_are_complete: bool
    refusal: str | None
    detail: str

    @property
    def ok(self) -> bool:
        return self.refusal is None


def _read_skills(store: object, character_id: int) -> frozenset[int] | None:
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
    except Exception:  # noqa: BLE001 -- see the docstring
        return None


def grant_all(store: object, character_id: object) -> SkillGrant:
    """Grant every curriculum skill to `character_id`.  Never raises.

    THE ORDER IS: read what is there -> grant the rest, one door call per
    id -> count.  Each call is independent: one id that raises does not stop
    the others, because a tester with 136 of 137 skills has a usable sandbox
    and a tester with 0 has nothing.  The failures are COUNTED and named in
    the console line, never swallowed.

    EVERY failure comes back as a refusal object with a NAMED reason rather
    than an exception, for the reason `gm/level_command.write_level`'s
    docstring gives: an escaping exception on this dispatch unwinds the
    listener thread and parks the client on "connecting".
    """
    if type(character_id) is not int or isinstance(character_id, bool) or character_id <= 0:
        return SkillGrant(
            # `True` for the same reason the sibling refusal twenty lines
            # down passes it: nothing was attempted, so nothing FELL BACK to
            # counting calls, and `granted_from=calls` must not appear on a
            # line whose counts are three zeros.  The positional argument was
            # MISSING here and at REFUSED_NO_STORE below until pf-adversary
            # (round nboppe, D1) built the branch: `counts_are_complete` was
            # added to this dataclass in the same commit that answered round
            # wv0fpe, and five of the seven construction sites were updated.
            # These two were the pair with no test that reaches them, so the
            # suite proved the refusal WORD existed while the branch that
            # returns it raised TypeError.
            0, 0, 0, True, REFUSED_NO_CHARACTER,
            f"no usable selected character id on this connection ({character_id!r})",
        )
    granter = getattr(store, "grant_learned_skill", None)
    if granter is None:
        return SkillGrant(
            # The second of the pair -- see REFUSED_NO_CHARACTER above.
            0, 0, 0, True, REFUSED_NO_STORE,
            "this session's store has no grant_learned_skill door",
        )
    skill_ids = all_skill_ids()
    wanted = frozenset(skill_ids)
    before = _read_skills(store, character_id)
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
    granted = 0
    failed = 0
    first_error = ""
    row_missing = False
    counts_are_complete = True
    # THE BASELINE FOR "DID THIS CALL INSERT A ROW", and it is the door's own
    # answer rather than this module's bookkeeping.  `grant_learned_skill`
    # returns every distinct skill id on the row, read INSIDE its own
    # transaction, so the set GROWING by one across a call is the door
    # saying it inserted and the set standing still is the door saying
    # `INSERT OR IGNORE` ignored.  pf-adversary (round `wv0fpe`, D3)
    # measured what counting calls-that-returned instead cost: a full
    # `granted=` count for a run that inserted nothing, read straight off
    # the line the owner's `HEADLESS_PROOF:` block greps.
    known_size = len(before)
    for skill_id in skill_ids:
        if skill_id in before:
            continue
        try:
            returned = granter(character_id, skill_id)
        except KeyError:
            # The character has no live row.  Every remaining id would raise
            # the same way, so stop asking -- and the ids already written
            # stay written, which is why this refusal PRINTS ITS COUNTS
            # (pf-adversary round `wv0fpe`, D4: the one branch where a
            # partial write really happens was the one branch whose numbers
            # never reached the operator).
            row_missing = True
            break
        except Exception as error:  # noqa: BLE001 -- counted, never escaping
            failed += 1
            if not first_error:
                first_error = f"{type(error).__name__}: {error}"
            continue
        try:
            size = len({int(i) for i in returned})
        except Exception:  # noqa: BLE001 -- a door that returned another shape
            size = None
        if size is None:
            # CANNOT TELL, SO SAY SO.  The row very likely moved (the call
            # returned), so the count goes up -- but `counts_are_complete`
            # goes False and the console line says `granted_from=calls`,
            # because a number this module could not verify may not be
            # presented as one it measured.
            counts_are_complete = False
            granted += 1
            continue
        if size > known_size:
            granted += 1
        known_size = size
    if row_missing:
        return SkillGrant(
            granted, already, failed, counts_are_complete, REFUSED_ROW_MISSING,
            f"character {character_id} has no live row to grant against; "
            f"{granted} row(s) had already been written when it stopped",
        )
    if granted == 0 and already == 0:
        return SkillGrant(
            granted, already, failed, counts_are_complete,
            REFUSED_NOTHING_GRANTED,
            first_error or "no skill id could be written and none was already held",
        )
    if failed:
        return SkillGrant(
            granted, already, failed, counts_are_complete, None,
            f"{failed} of {len(skill_ids)} could not be written; "
            f"first: {first_error or 'unknown'}",
        )
    return SkillGrant(
        granted, already, failed, counts_are_complete, None,
        f"{granted} granted, {already} already held",
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
    and its writers are `grant_starting_skills` and `grant_learned_skill`,
    both `INSERT OR IGNORE`; there is no deleter, and this lane may not add
    one to another lane's table.  A deleter would also have no way to tell
    the rows THIS run inserted from rows the character already held, so the
    safe residue is a skill the GM did not ask to lose.  The command is
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
#: field by field in `tests/test_gm_skill_all_command.py`.
CONSOLE_TOKEN = "GM_SKILL_ALL"


def console_line(result: SkillGrant, character_id: object) -> str:
    """One ASCII line for the SERVER HOST's console.  Never the player's screen.

    `GM_SKILL_ALL cid=<n> granted=<k> already=<m> classes=<...>`, the shape
    PANYA-ORDER 2026-09-08 section 2.1 spells, plus `failed=<k>` ON THE
    PARTIAL PATH ONLY -- an extra field that appears exactly when it is
    non-zero, so the ordinary line stays the four the owner asked for and a
    partial run cannot read as a clean one.

    `classes=` lists the BUCKET CODES drawn from, `1024` included and not
    hidden, for the reason the module docstring gives.  The success wording
    says the rows are written and that no skill-list frame was sent, because
    both halves are what the tester has to know before she grades the K
    window.
    """
    classes = ",".join(str(code) for code in bucket_codes())
    failed = f" failed={result.failed}" if result.failed else ""
    degraded = "" if result.counts_are_complete else " granted_from=calls"
    if result.ok:
        return _ascii_only(
            f"{CONSOLE_TOKEN} cid={character_id} granted={result.granted} "
            f"already={result.already}{failed}{degraded} classes={classes} "
            "(rows written; no skill-list frame was sent to the live client)"
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
