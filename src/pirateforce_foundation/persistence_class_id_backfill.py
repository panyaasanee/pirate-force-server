"""LANE-DB / PLAYER-CHARACTER piece 2: the WRITE half of the boot-time
``class_id`` backfill, ordered by ``COO-DECISION 20260904_0445``.

WHY THIS FILE EXISTS.  ``lifecycle.persist_class_id_from_starting_gear``
only ever reaches a character at the moment she is created
(``CharacterLifecycle.create``, called through
``store.write_typed_attribute_if_unset``).  Every character who existed
before that hookup landed is left with ``characters.class_id`` NULL
forever, unless something goes back for her.
``store.list_character_ids_missing_class_id`` is the READ half of "something"
-- a plain SELECT naming which characters that hookup never reached.  This
module is the WRITE half: it walks that list once, at boot, and resolves
each one exactly the way a fresh creation would have.

THE LETTER TRAIL THIS FILE ANSWERS, AND WHY THE SHAPE BELOW IS NOT WHAT
``COO-DECISION 20260904_0445`` LITERALLY SAYS.  That decision's rule (d)
named a console line shape (``BACKFILL cid=<n> class_id=<k> trio=<a,b,c>``)
before any of this existed.  ``pf_bridge/notes_to_chief/
20260904_0844_LANE-DB-CORE-REQUEST-boot-time-class-id-backfill-loop-in-app-
py.md`` (this lane, round ``b0ede7``) asked chief the one open question --
is that format still required, given the real function's own line already
exists and predates it -- and chief's reply, ``pf_bridge/notes_to_chief/
20260904_0938_CHIEF-TO-LANE-DB-boot-backfill-loop-deferred-to-next-round.md``,
settled it: *"the real format wins over the old letter's text"* -- the
existing ``CHARACTER_CLASS_ID cid=<n> written class_id=<k>`` /
``not_written reason=<...>`` line (``COO-DECISION 20260904_0446``/``0549``)
is sufficient, no ``trio`` needed. So this module prints nothing per row
itself -- ``lifecycle.persist_class_id_from_starting_gear`` already does,
once, every time it is called below -- and only adds the one line rule (c)
still requires that nothing else prints: the pre-write snapshot path.

WHY THIS CALLS ``lifecycle.persist_class_id_from_starting_gear`` INSTEAD OF
DECODING ``avatar_wire`` ITSELF.  This repository's AvatarAttr wire decoder
module is guarded by Rule 14.13(d) -- opened for exactly one caller by
``COO-DECISION 20260904_0446`` points 1-2 (a guard this docstring does not
name a second time, the same discipline ``persistence_class_id.py`` already
uses for a different sibling module it deliberately does not import):
``lifecycle.py`` is the ONLY file in this repository allowed to mention that
decoder at all -- a second module decoding the body itself, this one
included, would fail that guard at the gate.  ``store.list_character_ids_
missing_class_id``'s own docstring already names the intended shape: "a
caller loops over the ids this returns and calls the SAME creation-time
function on each one" -- not a second decoder.  So this module calls that
one function, and gets its ``resolve_class_id``-or-``None`` answer from its
return value, same as the creation-time caller does, same as the plain
inline loop letter ``0844`` sketched for ``app.py``.

WHY THIS IS NOT JUST THAT INLINE LOOP, THEN.  It is the same loop, wrapped
once, tested here instead of only ever exercised live on the owner's
database.  Two bugs a ``pf-adversary`` pass (round ``suh0aq``) found in an
earlier draft of THIS file are the reason for the shape below, not reasons
to go back to a bare loop with the same exposure: (1) a first draft added
its own pre-write "already set?" check, read before calling the writer --
between that read and the atomic write inside ``persist_class_id_from_
starting_gear``, a concurrent writer could set the row, and the pre-check's
stale answer would misreport a genuinely-resolved row as ``UNRESOLVED``.
Removed entirely below -- ``write_typed_attribute_if_unset``'s own
transaction is the only correct place that question gets answered, and this
module reads the row's REAL post-attempt state instead of guessing its
pre-attempt one. (2) a first draft's own post-write read-back (added for
rule (d) below) was not wrapped in ``try/except KeyError`` the way
``get_character`` already was (learned once before, per ``pf-adversary``'s
note inside letter ``0844`` itself) -- a row vanishing (soft-delete) in the
narrow window between the write and that read would raise, uncaught, out of
``tuple(_backfill_one(...) for cid in ids)``, aborting every remaining
character in that boot's pass, not just the one row.  Every read below that
touches a specific character id is now wrapped the same way
``get_character`` already was.

THE FOUR RULES ``COO-DECISION 20260904_0445`` MAKES MANDATORY, AND WHERE
EACH ONE LIVES BELOW.
(a) **One resolver, not two.**  Every resolution below goes through
    ``lifecycle.persist_class_id_from_starting_gear``, which itself calls
    ``persistence_class_id.resolve_class_id`` against the one committed
    ``CLASS_PRESETS`` table -- this module holds no second copy of that
    table and no second decode of ``avatar_wire``.
(b) **NULL rows only, never an overwrite.**  ``persist_class_id_from_
    starting_gear`` writes through ``store.write_typed_attribute_if_unset``,
    the same guarded, single-transaction ``UPDATE ... WHERE class_id IS
    NULL`` every other class-id writer uses -- the ONLY place this
    question is decided, per the note above.
(c) **Backup before the first write, path printed.**  ``backfill_missing_
    class_ids`` snapshots the live database (``persistence_backup.
    snapshot_database``, the same module ``SQLiteStore.migrate_with_backup``
    uses) BEFORE touching a single row, and prints the snapshot's path to
    the console -- not after, and not once per row.  Skipped only for an
    in-memory database (nothing on disk to lose, the same carve-out
    ``persistence_backup.should_snapshot`` documents for ``:memory:``); a
    missing snapshot for a real, on-disk database is a hard failure
    (``persistence_backup.BackupError`` propagates -- this module never
    catches it), the same "cannot protect it, will not touch it" contract
    ``migrate_with_backup`` already has.
(d) **One console line per row, read-back after every write.**  The line is
    ``CHARACTER_CLASS_ID ...`` (see the letter-trail note above for why, not
    a new ``BACKFILL`` line).  After every successful write this module
    additionally reads the row back (``store.read_typed_attributes``, the
    house "read back after write" rule) and raises loudly if the stored
    value disagrees with what was just written -- guarded against the row
    having vanished in the interim, in which case nothing is asserted (the
    write itself already succeeded, inside its own transaction, before this
    check ever runs).

WHAT THIS MODULE DOES NOT DO.  It does not decide WHEN it runs -- there is
no call site anywhere in this repository yet.  A boot path needs one line,
``persistence_class_id_backfill.backfill_missing_class_ids(store)``, after
``store.migrate_with_backup()`` returns; that hookup is chief's (``app.py``),
same as it was when letter ``0844`` asked for it as a bare inline loop --
this module exists so that one line can call something already tested here,
instead of app.py hand-rolling the loop letter ``0938`` said chief would
write from that sample. It does not touch ``lifecycle.py``, ``runtime.py``
or ``current/pf_login_game_server_v141.py``.  It writes no migration and
adds no column -- ``class_id`` already exists (``migrations/
006_character_typed_attribute_columns.sql``).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from . import lifecycle
from .persistence_backup import snapshot_database


def _say(line: str) -> None:
    """One ASCII console line, and never this backfill's exception.  Same
    wrapper discipline every other print on a boot/request path in this
    package uses (``lifecycle._say``, ``session.py``): a closed or broken
    stderr must not turn a successful backfill into a crashed boot."""
    try:
        print(line, file=sys.stderr)
    except Exception:
        pass


def _read_typed_attributes_or_none(store, character_id: int) -> dict | None:
    """``store.read_typed_attributes(character_id)``, or ``None`` if the
    row no longer exists (soft-deleted since the caller last looked).
    Every read below that names one specific character id goes through
    this, so a row vanishing mid-pass degrades a single outcome instead of
    raising an uncaught ``KeyError`` out of the whole pass -- the exact
    failure a ``pf-adversary`` pass (round ``suh0aq``) measured against an
    earlier draft that called ``store.read_typed_attributes`` directly."""
    try:
        return store.read_typed_attributes(character_id)
    except KeyError:
        return None


@dataclass(frozen=True)
class BackfillOutcome:
    """What happened to exactly one character id this pass considered.

    ``class_id`` is the row's value AFTER this pass finished with it,
    whoever set it -- not necessarily this pass's own write.  ``written``
    is ``True`` only when THIS call is the one that set it.  A row already
    resolved by a concurrent writer therefore reads
    ``(class_id=<k>, written=False)``, the same shape as a row this pass
    could not resolve reads as ``(class_id=None, written=False)`` --
    distinguishable from each other, never from a stale pre-write guess.
    """

    character_id: int
    class_id: int | None
    written: bool


@dataclass(frozen=True)
class BackfillReport:
    """The whole pass, once: every id considered and what came of it."""

    snapshot_path: Path | None
    outcomes: tuple[BackfillOutcome, ...]

    @property
    def written_count(self) -> int:
        return sum(1 for o in self.outcomes if o.written)

    @property
    def unresolved_count(self) -> int:
        return sum(
            1 for o in self.outcomes if not o.written and o.class_id is None
        )


def backfill_missing_class_ids(store, *, backups_root=None) -> BackfillReport:
    """Resolve and write ``class_id`` for every live character it is still
    NULL for, snapshotting the database first.  Idempotent: a character
    already resolved by an earlier pass (or by the creation-time hookup) is
    not in ``store.list_character_ids_missing_class_id()`` any more, so a
    second boot's pass over the same database writes nothing and reports an
    empty ``outcomes``.

    Never raises for an individual row -- a vanished row, an unreadable
    avatar body, or gear matching no single preset all fold into a plain,
    logged non-write (see ``_backfill_one``).  Only two things can raise
    out of this function: the pre-write snapshot itself failing on a real
    on-disk database (``persistence_backup.BackupError``, propagated
    unchanged -- a boot that cannot protect the owner's data must not go on
    to write it), and a read-back that disagrees with what THIS PASS itself
    just wrote for a row that still exists (rule (d)'s verification, a
    ``RuntimeError`` naming both values -- this should be unreachable given
    ``write_typed_attribute_if_unset``'s own single-transaction guarantee,
    and is checked anyway rather than trusted).
    """
    ids = store.list_character_ids_missing_class_id()
    if not ids:
        return BackfillReport(snapshot_path=None, outcomes=())

    if store.path == ":memory:":
        # Same carve-out `persistence_backup.should_snapshot` documents:
        # nothing on disk to lose.  Every headless/in-memory test fixture in
        # this repository that exercises this function depends on this
        # branch existing -- `snapshot_database` raises `BackupError` for a
        # path that does not exist on disk, and `:memory:` never does.
        snapshot_path = None
        _say("CLASS_ID_BACKFILL_SNAPSHOT skipped reason=in_memory_database")
    else:
        snapshot_path = snapshot_database(
            store.path,
            backups_root,
            label="classid_backfill",
            reason=(
                "LANE-DB class_id backfill before write "
                "(COO-DECISION 20260904_0445 rule c)"
            ),
        )
        _say(f"CLASS_ID_BACKFILL_SNAPSHOT path={snapshot_path}")

    outcomes = tuple(_backfill_one(store, cid) for cid in ids)
    return BackfillReport(snapshot_path=snapshot_path, outcomes=outcomes)


def _backfill_one(store, character_id: int) -> BackfillOutcome:
    """Resolve and, if resolvable and still NULL, write one character's
    ``class_id``.  ``lifecycle.persist_class_id_from_starting_gear`` prints
    its own ``CHARACTER_CLASS_ID`` line; this function adds no line of its
    own (see the module docstring's letter-trail note)."""
    try:
        character = store.get_character(character_id)
    except KeyError:
        # Vanished between the caller's SELECT and here (e.g. soft-deleted
        # mid pass).  Not decidable, never a guess.
        return BackfillOutcome(character_id, None, False)

    wrote = lifecycle.persist_class_id_from_starting_gear(store, character)
    if wrote is None:
        # Unresolvable gear, an unreadable body, a soft-delete that landed
        # between the two lines above, OR another writer already set this
        # row -- `persist_class_id_from_starting_gear` folds all four into
        # the same `None`, by design (its own docstring). Read the row's
        # real, current state to tell "someone else resolved it" apart from
        # "still NULL" for THIS report -- a read of what already happened,
        # not a decision this pass makes anything depend on.
        current = _read_typed_attributes_or_none(store, character_id)
        current_class_id = current.get("class_id") if current is not None else None
        return BackfillOutcome(character_id, current_class_id, False)

    # Rule (d): read back after every write this pass made.  `after is
    # None` means the row vanished between the write above and this read --
    # the write itself already committed, inside its own transaction,
    # before this line ever ran, so there is nothing left here to verify
    # against.  `after is not None` means the row still exists and its
    # `class_id` must be exactly what was just written, NULL (a schema this
    # module has never seen) included -- `.get("class_id")` returning
    # `None` for an existing, still-NULL row is exactly the mismatch this
    # check exists to catch, not a reason to skip it.
    after = _read_typed_attributes_or_none(store, character_id)
    if after is not None and after.get("class_id") != wrote:
        raise RuntimeError(
            f"class_id backfill read-back mismatch for cid={character_id}: "
            f"wrote {wrote!r}, read back {after.get('class_id')!r}"
        )
    return BackfillOutcome(character_id, wrote, True)
