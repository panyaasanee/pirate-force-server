"""What a broken vendored file of OURS means, and where it is counted.

Two things live here, and the second is here BECAUSE of the first: the
exception type that says a mirror in this repository is broken, and the
per-mirror counter that records when one is.  Everything in ``lua_api``
that reads a shipped ``.tsv`` already imports this module for the
exception, and ``script_host`` imports ``lua_api`` -- so this leaf is
the only place the counter can live without an import cycle.  See the
comment block above ``MIRROR_API_SPEC`` for the two pf-adversary
findings (D3, D6) that moved it out of ``script_host.py``.

THE EXCEPTION TYPE: A BASE CLASS AND NOT A LIST.
``script_host._host_side_error_types()`` used to be a hand-maintained tuple naming each vendored file's own error
class, with nothing anywhere asserting the tuple was COMPLETE: a third
mirror added next year would raise an error nobody had listed, fall through
to the generic ``except Exception``, and be logged ``LUA_SCRIPT <file> ERR``
against whichever quest script happened to be loading -- the exact defect
pf-adversary D11 (round 7kxfe9) was raised to fix, arriving again through
the door the fix left open.  Deriving the classification from a base class
makes the tuple complete BY CONSTRUCTION: any loader that raises a subclass
of :class:`VendoredDataError` is host-side, whether or not anyone remembered
to add it to a list.

It also keeps ``script_host.py`` from having to name a per-namespace error
class, which matters for a second, unrelated reason: the quest/shop symbol
guard in ``tests/test_npc_interaction_wire.py`` reads every identifier in
that module, and a chief-granted exemption list is not the right price for
an import line.
"""
from __future__ import annotations

import dataclasses
import datetime
import threading
from typing import Any, Callable, Dict, Optional


class VendoredDataError(RuntimeError):
    """A mirror in THIS repository is missing, unreadable, or corrupt.

    Deliberately not something a Lua script can provoke: it means go fix
    this checkout, not go read that quest file.
    """


# ---------------------------------------------------------------------------
# WHERE A BROKEN MIRROR IS COUNTED, AND WHY IT LIVES IN THIS MODULE
#
# COO-DECISION `20260907_1441` item 3 asked for readable state rather than a
# log line nobody reads, and round `95aw54` built it -- in `script_host.py`,
# where it could only ever see ONE of the four mirrors this package ships.
# pf-adversary measured that and raised two findings the round shipped
# NAMED-BUT-NOT-FIXED:
#
#   D3  the counter covers `api_spec.tsv` alone, because that is the only
#       mirror a `ScriptHost` construction reads.  `message_catalog.tsv` and
#       the two `quest_criteria_*.tsv` are read lazily inside the namespace
#       closures, so a broken copy of any of them BUILDS A HOST FINE and
#       raises at call time, where a construction-time guard never sees it.
#   D6  the count is a bare increment with no key and no success signal, so
#       over the real 616-file corpus a reader sees `mirror_failures=616`,
#       still sees 616 after the file is repaired, and can answer neither
#       WHICH mirror is broken nor WHETHER IT STILL IS.
#
# Both are one defect -- state that cannot be asked a question -- so both are
# paid by one change: per-mirror keys, a `record_ok` beside `record`, and a
# home in the LEAF module every loader already imports.  `script_host.py`
# imports `lua_api`, so a loader in `lua_api` cannot import the counter back
# out of `script_host` without a cycle; `vendored.py` has no imports of its
# own beyond the standard library and is already the module that defines
# what "a mirror of ours is broken" MEANS.  `script_host` re-exports every
# name below, so its own callers and tests are unchanged.
# ---------------------------------------------------------------------------

#: The mirror keys this package ships, one per vendored file.  A key is a
#: short ASCII token, not a path: it is what a reader greps for and what a
#: future health check keys its output by, and it must not change when a
#: file moves.
MIRROR_API_SPEC = "api_spec"
MIRROR_MESSAGE_CATALOG = "message_catalog"
MIRROR_CRITERIA_CURVE = "criteria_curve"
MIRROR_CRITERIA_ROWS = "criteria_rows"
MIRROR_QUEST_VAR_ROWS = "quest_var_rows"
MIRROR_QUEST_VAR_SIGNEDNESS = "quest_var_signedness"

#: What a read that did not say which mirror it was reading is filed under.
#: Kept so `record(exc)` with no key stays legal for a caller outside this
#: package, and so an unnamed read is VISIBLY unnamed instead of silently
#: attributed to whichever mirror was named last.
MIRROR_UNNAMED = "unnamed"

#: Every key above, in the order a reader most often wants them.
KNOWN_MIRRORS: tuple = (
    MIRROR_API_SPEC,
    MIRROR_MESSAGE_CATALOG,
    MIRROR_CRITERIA_CURVE,
    MIRROR_CRITERIA_ROWS,
    MIRROR_QUEST_VAR_ROWS,
    MIRROR_QUEST_VAR_SIGNEDNESS,
)


def ascii_safe(exc: BaseException) -> str:
    """Console-safe text for any exception.

    AGENTS.md section 7: everything printed is ASCII, because the bridge
    console is cp874.  `script_host._ascii_safe` is now a thin alias of
    this, so the two can never drift apart.
    """
    return str(exc).encode("ascii", "backslashreplace").decode("ascii")


def _ascii_text(text: str) -> str:
    """Console-safe text for any string, not only an exception's."""
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _ascii_name(exc: BaseException) -> str:
    """The exception's CLASS NAME, escaped as well as its message.

    pf-adversary D10 (round `95aw54`): a `VendoredDataError` subclass whose
    name carries a character outside cp874 would otherwise reach `print`
    unescaped and kill a sweep mid-report.
    """
    return type(exc).__name__.encode("ascii", "backslashreplace").decode("ascii")


@dataclasses.dataclass(frozen=True)
class MirrorFailureTally:
    """What a reader can learn about mirror health WITHOUT opening a log.

    Returned in two shapes by the same class, distinguished by `mirror`:

    * `mirror is None` -- the ROLL-UP over every mirror seen in this
      process.  `failures` is their sum, `last_error`/`last_failed_at` are
      the most recent failure among them (ordered by an internal sequence
      number, not by the stamp: the stamp has one-second resolution and two
      mirrors can break inside one second), and `broken` names the ones
      whose LAST event was a failure.
    * `mirror` is a key -- that ONE mirror's state.  `broken` is then either
      empty or the one-tuple naming it, so a caller can treat both shapes
      the same way.

    `broken_now` is the field D6 asked for and the reason a bare count was
    not enough: a count only ever rises, so it answers "has this ever
    failed", never "did the last attempt fail".  `last_ok_at` is the other
    half -- a mirror that was broken and is then parsed successfully says
    so with a stamp, rather than leaving a reader to guess from a number
    that never comes down.

    WHAT `broken_now` AND `last_ok_at` DO **NOT** MEAN, MEASURED
    (pf-adversary D1, round `h20x7g`, and the strongest finding against
    this design).  They describe THE MOST RECENT PARSE ATTEMPT IN THIS
    PROCESS, not the file on disk.  Every one of the four mirrors is
    parsed at most once and then cached (`spec._TABLES`,
    `message._CATALOG_CACHE`, `quest_criteria._CURVE_CACHE`/`_ROWS_CACHE`),
    so once a mirror has been read successfully NOTHING READS IT AGAIN:
    delete the file and `broken_now` stays false and `last_ok_at` keeps
    the stamp of a read that happened before the deletion.  Measured with
    an injected clock: `api_spec.tsv` moved off disk, three further host
    constructions, `broken_now=false last_ok_at=<fifteen minutes later>`.

    So the transition this state can observe is broken -> healthy, and
    only that.  A healthy -> broken transition is unobservable for the
    life of the process, because there is no re-read to observe it with.
    THIS IS NOT A LIVENESS SIGNAL, and a health check built on it would
    report a deleted mirror as fine; the open design question -- whether
    anything should ever re-stat or re-parse a warm mirror -- is written
    up for COO rather than answered here, because the answer changes what
    the loaders do and this lane has no decision for that.
    """

    #: How many failed reads have been recorded (for this mirror, or in
    #: total).  Monotonic BY DESIGN: it is the history, not the state.
    failures: int
    #: `<ExceptionType>: <message>` of the most recent failure, ASCII-safe,
    #: or `None` if there has been none.
    last_error: Optional[str]
    #: ISO-8601 UTC stamp of the most recent failure, or `None`.
    last_failed_at: Optional[str]
    #: ISO-8601 UTC stamp of the most recent SUCCESSFUL read, or `None`.
    last_ok_at: Optional[str] = None
    #: Whether the most recent event was a failure.  THE STATE, as opposed
    #: to `failures`, which is the history.
    broken_now: bool = False
    #: The mirror this describes, or `None` for the roll-up.
    mirror: Optional[str] = None
    #: Every mirror whose last event was a failure, sorted.
    broken: tuple = ()

    def log_fields(self) -> str:
        """One ASCII field group, quoted so a reader can split on spaces.

        The first three fields keep the names and the order round `95aw54`
        published, because `tests/test_script_host_mirror_health.py` and a
        reader's grep both already know them; the four that answer D6 are
        appended rather than mixed in.

        THE KEY IS ESCAPED TOO (pf-adversary D7, round `h20x7g`).  Round
        `95aw54` escaped an exception's message and then its class name;
        the key was the third piece of caller-supplied text on this line
        and the one nothing escaped.  `record` takes an arbitrary key and
        its own docstring invites callers outside this package, so a key
        with a character outside cp874 would die inside `print` on the
        bridge console -- the same shape, one field along.  Every in-repo
        caller passes one of `KNOWN_MIRRORS`, so this was risk, not a live
        break.
        """
        return ('mirror_failures=%d last_failed_at="%s" last_error="%s" '
                'mirror="%s" broken_now=%s last_ok_at="%s" broken="%s"'
                % (self.failures, self.last_failed_at or "",
                   self.last_error or "", _ascii_text(self.mirror or ""),
                   "true" if self.broken_now else "false",
                   self.last_ok_at or "",
                   ",".join(_ascii_text(name) for name in self.broken)))


@dataclasses.dataclass
class _OneMirror:
    """The mutable per-key state behind one `MirrorFailureTally`."""

    failures: int = 0
    last_error: Optional[str] = None
    last_failed_at: Optional[str] = None
    last_ok_at: Optional[str] = None
    broken_now: bool = False
    #: Monotonic sequence number of this mirror's most recent FAILURE, used
    #: only to order the roll-up.  Never printed.
    last_failure_seq: int = 0


class MirrorHealth:
    """The counter behind `MirrorFailureTally`, keyed by mirror, safe to share.

    Process-wide by default (`MIRROR_HEALTH`) because the thing being
    counted is process-wide: a checkout whose `api_spec.tsv` is broken
    breaks every host in the process, and a broken `message_catalog.tsv`
    breaks every message call in it.  A caller that wants an isolated tally
    -- every test here does -- passes its own instance.

    WHAT THE LOCK IS AND IS NOT, MEASURED (same posture `lua_api/spec.py`
    takes about its own `_LOCK`).  Round `95aw54` measured that the
    16-thread test in this lane's tests does NOT kill a no-lock mutant:
    replacing `+= 1` with `self._failures = 1` goes red, but deleting the
    lock outright leaves the suite green, because CPython does not
    interleave that particular body often enough to lose a count in one
    run.  So the lock is [PROPOSED] protection against a caller with more
    contention than any test here produces -- and, now that a tally is
    assembled from several fields of several mirrors, protection against a
    reader seeing a roll-up built half from before an update and half from
    after -- not a guard some test proves is load-bearing.

    `clock` returns a `datetime`; an aware one is converted to UTC, a naive
    one is taken as UTC already (a test injecting a fixed clock is the only
    caller that passes one).  It is called with the lock held: it is one
    function call, this module never re-enters it, and reading it outside
    the lock would let two threads write a count and its stamp in opposite
    orders.
    """

    def __init__(self, clock: Optional[Callable[[], "datetime.datetime"]] = None):
        self._lock = threading.Lock()
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc))
        self._mirrors: Dict[str, _OneMirror] = {}
        self._seq = 0

    def _stamp_unlocked(self) -> str:
        now = self._clock()
        if now.tzinfo is not None:
            now = now.astimezone(datetime.timezone.utc)
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _state_unlocked(self, mirror: str) -> _OneMirror:
        state = self._mirrors.get(mirror)
        if state is None:
            state = _OneMirror()
            self._mirrors[mirror] = state
        return state

    def _tally_unlocked(self, mirror: str) -> MirrorFailureTally:
        state = self._state_unlocked(mirror)
        return MirrorFailureTally(
            failures=state.failures,
            last_error=state.last_error,
            last_failed_at=state.last_failed_at,
            last_ok_at=state.last_ok_at,
            broken_now=state.broken_now,
            mirror=mirror,
            broken=(mirror,) if state.broken_now else (),
        )

    def record(self, exc: BaseException,
               mirror: str = MIRROR_UNNAMED) -> MirrorFailureTally:
        """Count one failed read of `mirror`; return THAT mirror's tally.

        Returns the single-mirror shape, not the roll-up, so a caller that
        quotes a cause quotes ITS OWN cause (pf-adversary D7, round
        `95aw54`: a degraded host used to read a shared counter's latest
        error and could therefore blame another host's failure).
        """
        message = "%s: %s" % (_ascii_name(exc), ascii_safe(exc))
        with self._lock:
            state = self._state_unlocked(mirror)
            self._seq += 1
            state.failures += 1
            state.last_error = message
            state.last_failed_at = self._stamp_unlocked()
            state.last_failure_seq = self._seq
            state.broken_now = True
            return self._tally_unlocked(mirror)

    def record_ok(self, mirror: str = MIRROR_UNNAMED) -> MirrorFailureTally:
        """Record that `mirror` was read successfully; return its tally.

        The half D6 was missing.  `failures` is deliberately NOT reset --
        it is the history and a reader who wants "has this ever broken"
        must keep being able to ask -- but `broken_now` goes false and
        `last_ok_at` is stamped, so a repair is visible instead of being
        hidden behind a number that only rises.

        SUCCESS HERE MEANS "THIS PARSE ATTEMPT RAISED NOTHING", and no
        more than that -- see `MirrorFailureTally` for the two ways that
        is weaker than it sounds (a warm cache means there is no later
        attempt at all; a mirror that parses but is INCOMPLETE raises
        nothing and is recorded healthy, pf-adversary D2 of round
        `h20x7g`).
        """
        with self._lock:
            state = self._state_unlocked(mirror)
            state.last_ok_at = self._stamp_unlocked()
            state.broken_now = False
            return self._tally_unlocked(mirror)

    def tally_for(self, mirror: str) -> MirrorFailureTally:
        """One mirror's state.  A key never read yet reads as all-zero.

        READING NEVER CREATES A KEY.  `_state_unlocked` does create one,
        because a `record`/`record_ok` must have somewhere to write; going
        through it here would mean that merely ASKING about a mirror put it
        in `mirrors()`, which reports what has been READ.  A reader polling
        all four keys would then see all four listed and conclude every
        mirror had been touched.  Caught by this module's own test, not by
        review.
        """
        with self._lock:
            state = self._mirrors.get(mirror)
            if state is None:
                return MirrorFailureTally(
                    failures=0, last_error=None, last_failed_at=None,
                    mirror=mirror)
            return self._tally_unlocked(mirror)

    def tally(self) -> MirrorFailureTally:
        """The roll-up over every mirror recorded in this process.

        Kept as the no-argument reader round `95aw54` published, and kept
        returning a `MirrorFailureTally`, so every existing caller and the
        `MIRROR_HEALTH` read a health check would do are unchanged -- what
        changes is that the same object can now be ASKED which mirror and
        whether it is still broken.
        """
        with self._lock:
            total = 0
            newest: Optional[_OneMirror] = None
            newest_any: Optional[_OneMirror] = None
            last_ok_at: Optional[str] = None
            broken = []
            for name, state in self._mirrors.items():
                total += state.failures
                if state.failures and (newest_any is None
                                       or state.last_failure_seq
                                       > newest_any.last_failure_seq):
                    newest_any = state
                # THE QUOTED CAUSE IS TAKEN FROM A MIRROR THAT IS STILL
                # BROKEN, whenever one is (pf-adversary D4, round
                # `h20x7g`).  Ordering by sequence alone produced a line
                # that named `message_catalog` in `broken=` and quoted an
                # `api_spec` error that had already been repaired -- D7 of
                # round `95aw54` ("a host describing itself with another
                # host's error") arriving one level up, in the object a
                # health check is meant to read.  With nothing broken the
                # newest failure of all is the right answer, because then
                # the line is history and `broken=""` says so.
                if state.broken_now and state.failures and (
                        newest is None
                        or state.last_failure_seq > newest.last_failure_seq):
                    newest = state
                if state.last_ok_at is not None and (
                        last_ok_at is None or state.last_ok_at > last_ok_at):
                    last_ok_at = state.last_ok_at
                if state.broken_now:
                    broken.append(name)
            if newest is None:
                newest = newest_any
            return MirrorFailureTally(
                failures=total,
                last_error=None if newest is None else newest.last_error,
                last_failed_at=None if newest is None else newest.last_failed_at,
                last_ok_at=last_ok_at,
                broken_now=bool(broken),
                mirror=None,
                broken=tuple(sorted(broken)),
            )

    def mirrors(self) -> tuple:
        """Every key recorded into so far, sorted.  For a reader listing
        state, never for a decision: a key absent here means nothing has
        READ that mirror yet, not that it is healthy."""
        with self._lock:
            return tuple(sorted(self._mirrors))


#: The process-wide tally every reader of a vendored mirror records into
#: unless its caller hands it one of its own.  Deliberately ONE object and
#: not a spread of module-level globals: a future health check reads one
#: name and gets a consistent snapshot, rather than several that disagree.
#:
#: NOTHING IN THIS REPOSITORY READS THIS YET, AND THAT IS SAID OUT LOUD
#: RATHER THAN IMPLIED.  `grep -rn "def .*health\|/health" --include=*.py
#: src/` returns two lines, both in `world_scene_registry.py`
#: (`def remembers_health`, a scene predicate) -- no health-check endpoint
#: of any kind.  COO-DECISION `20260907_1441` item 4 forbids this lane from
#: inventing one.  What is closed is the half inside this lane's own walls:
#: the state EXISTS, is readable in one attribute, and can now be asked
#: WHICH mirror and WHETHER IT STILL FAILS.
MIRROR_HEALTH = MirrorHealth()


def read_mirror(mirror: str, read: Callable[[], Any],
                health: Optional[MirrorHealth] = None) -> Any:
    """Run `read`, recording the outcome against `mirror`, and RE-RAISE.

    The call-time half of D3.  A lazily-read mirror
    (`message_catalog.tsv`, `quest_criteria_*.tsv`) is read inside a
    namespace closure long after any host was built, so a construction-time
    guard cannot see it break.  Its loader wraps its read in this instead,
    which counts the failure and then lets it travel exactly as before --
    the callers above it already turn a `VendoredDataError` into a
    `LUA_HOST` line, and swallowing it here would be a behaviour change
    this lane has no decision for.

    Deliberately NOT the same function as `script_host.guard_mirrors`,
    which SWALLOWS its failure and returns `None` because a host must be
    built degraded rather than not at all.  Two different jobs, so two
    functions, rather than one with a flag that a reader has to trace.
    """
    health = MIRROR_HEALTH if health is None else health
    try:
        value = read()
    except VendoredDataError as exc:
        health.record(exc, mirror)
        raise
    health.record_ok(mirror)
    return value
