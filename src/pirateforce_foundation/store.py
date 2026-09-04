import random
import sqlite3
import hashlib
import math
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .inventory import (
    BackpackState,
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    INITIAL_BACKPACK,
    MERGED_V111_BACKPACK,
    ItemAttrState,
    merge_known_item_into_occupied_slot,
    move_known_item_to_free_slot,
    require_backpack_shape,
    swap_known_item_with_occupied_slot,
)
from .model import Character, Position
from .persistence_ground_drops import GroundDropRow

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


#: How long ONE `BEGIN IMMEDIATE` in the healing path may block on a database
#: another connection is writing, before SQLite gives up on that attempt.  The
#: attempt's real ceiling is this OR whatever is left of the budget below,
#: whichever is smaller, so the call cannot outrun the budget by a whole
#: ceiling -- a `pf-adversary` pass measured the version that could: budget
#: 1000 ms, ceiling 2000 ms, returned after 2006 ms with a message that
#: contradicted itself.
#:
#: WHY THIS EXISTS AND WHY IT IS NOT `connect`'s 5000.  `COO-DECISION
#: 20260902_1646`: the eight-thread lock test in
#: `tests/test_persistence_vitals_heal.py` closed a pull request belonging to
#: ANOTHER lane -- `server#582`, gate run 33613043185 -- whose diff touched
#: neither `store.py` nor that test.  LANE-B measured the mechanism on the
#: same primitives this method uses (WAL, `synchronous=FULL`,
#: `busy_timeout=5000`, `BEGIN IMMEDIATE`, a fresh connection per call) and
#: reported it in `pf_bridge/notes_to_chief/20260902_1642_LANE-B-TO-LANE-DB-*`:
#: at 8 threads x 60 heals, a transaction taking ~40ms makes a thread wait
#: 5,054ms and die with `OperationalError('database is locked')`.  SQLite's
#: busy handler makes no fairness guarantee, so the ceiling has to grow with
#: competitors x transaction time, and a Windows runner under load is exactly
#: where it does not.  The test was losing on TIME, not on logic.
#:
#: `SQLiteStore.connect` is NOT touched: it is an existing method and this
#: lane's charter (`COO-DECISION 20260901_1100`) forbids changing the
#: behaviour of one, and raising the number for every path in the server to
#: fix one path would be a change nobody measured.  This pragma is applied to
#: THIS path's own connection, after `connect` has opened it.
HEAL_LOCK_BUSY_TIMEOUT_MS = 30000

#: Total wall-clock budget for ACQUIRING the healing lock, across retries.
#: A bound, not a promise of success: when it is spent the call raises
#: `WriteLockTimeout` saying how long it waited and how many attempts it made,
#: instead of a bare `database is locked` that names nothing.
HEAL_LOCK_TOTAL_WAIT_S = 120.0

#: Backoff between attempts: a random wait in [0, HEAL_LOCK_RETRY_BACKOFF_S *
#: 2**min(attempt, 5)).  Randomised on purpose -- a fixed sleep re-synchronises
#: the very threads that just collided, which is the shape that starves one of
#: them.
HEAL_LOCK_RETRY_BACKOFF_S = 0.01

#: The message SQLite produces for the contention this retries, and NOTHING
#: else.  Every other `OperationalError` -- a missing table, a read-only
#: database, a corrupt file -- is re-raised on the first attempt.
#:
#: THE WIDTH IS LOAD-BEARING IN BOTH DIRECTIONS, measured by a `pf-adversary`
#: pass.  Too narrow and the starvation is not retried at all.  Too wide --
#: `"locked"` alone, the obvious "make it robust" edit -- and `SQLITE_LOCKED`
#: ("database TABLE is locked", a different condition that retrying cannot
#: fix) is retried for the whole budget: the same pass measured this file's
#: own suite going from 3.97 s to 123.95 s when the classification was
#: removed, which on the Windows gate turns a fast named failure into a
#: two-minute hang.  `tests/test_persistence_vitals_heal.py` pins both edges.
_LOCKED = "database is locked"


#: The DAMAGE door's OWN write-lock budget, in milliseconds, and it does NOT
#: share `HEAL_LOCK_*` with the two healing doors above.  `COO-DECISION
#: 20260903_1047` point 1 put `apply_hp_damage` behind
#: `_begin_immediate_under_contention` for one round, which meant a hit could
#: block for up to `HEAL_LOCK_TOTAL_WAIT_S` (120 s) -- a ceiling `FINDINGS_R18`
#: measured this server cannot afford, since it is strictly serial, one client
#: per listener: a hit that waits two minutes is a two-minute freeze of every
#: other player, the same shape `GT-193` killed a live session with once
#: already.  `COO-DECISION 20260903_1248` reversed that and gave this door its
#: own short budget instead.
#:
#: !! 3000 IS A SAFETY CEILING, NOT A MEASURED RESULT, and the docstring on
#: `_begin_immediate_for_damage` repeats this on purpose so a reader who only
#: opens that method still sees it.  Nobody has run combat's own pusher
#: against this number yet: `COO-DECISION 20260901_1142` wired LANE-B to call
#: `apply_hp_damage` from the aggro tick, but that call is not landed as of
#: this round, so nothing has ever waited on this budget under a real hit
#: rate.  LANE-B reports the real wait it measures once it is wired
#: (`COO-DECISION 20260903_1248` point 3); until then this number is a guess
#: at "short enough that a stuck lock cannot freeze the server the way 120 s
#: could", not a floor derived from combat's own timing.
#:
#: WHY THIS IS ALSO THE WHOLE BUDGET, AND NOT A PER-ATTEMPT CEILING UNDER A
#: LONGER ONE.  `COO-DECISION 20260903_1248` says the damage door must not
#: loop-retry `BEGIN IMMEDIATE` the way the healing doors do -- one attempt,
#: with SQLite's own busy handler doing the waiting for up to this many
#: milliseconds inside that ONE `sqlite3.Connection.execute("BEGIN
#: IMMEDIATE")` call.  There is no Python-level retry loop, no backoff and no
#: `HEAL_LOCK_RETRY_BACKOFF_S`-shaped sleep on this path at all -- see
#: `_begin_immediate_for_damage`.
DAMAGE_LOCK_BUSY_TIMEOUT_MS = 3000

#: Printed to stdout, once, the one time this budget is spent and the write
#: is refused -- so a hit that never lands is visible on the console instead
#: of only living inside a caught exception a combat caller might swallow.
#: `COO-DECISION 20260903_1248`: "หมดเวลาแล้ว ปฏิเสธการเขียนพร้อมบรรทัดคอนโซล
#: ห้ามวนรีทราย ห้ามเงียบ" -- refuse the write WITH a console line, no retry
#: loop, no silence.  Follows this file's own convention (`GROUND_VITALS_
#: PRESERVE_REFUSED` in `action_ack.py`, the `*_TOKEN` prints in
#: `mob_combat.py`) rather than inventing a new shape.
DAMAGE_WRITE_LOCK_REFUSED_TOKEN = "DAMAGE_WRITE_LOCK_REFUSED"

#: Printed to stdout, once per refusal, when a connection refuses to accept
#: `PRAGMA busy_timeout=...` at all -- a condition distinct from a refused
#: `BEGIN IMMEDIATE` (that one already prints `DAMAGE_WRITE_LOCK_REFUSED_
#: TOKEN` or raises `WriteLockTimeout`; this one, if it ever fires, fires
#: BEFORE either door even tries to acquire the lock).  Both
#: `_begin_immediate_under_contention` (healing) and
#: `_begin_immediate_for_damage` (damage) share this token and the counter
#: below -- `COO-DECISION 20260903_1248` point 4: "ให้ pragma ที่ถูกปฏิเสธ
#: นับและพิมพ์บรรทัด ห้ามลดตัวเองลงเงียบ ๆ กลับไป 5,000 ms" (a refused
#: pragma must be counted and printed, never silently swallowed, and must
#: not fall back to `connect()`'s 5,000 ms on its own).  NEITHER door's
#: other behaviour changes: a connection that refuses the pragma still goes
#: on to attempt `BEGIN IMMEDIATE` at whatever timeout it already has,
#: exactly as before this fix -- this only makes the refusal visible
#: instead of a bare `pass`.
PRAGMA_BUSY_TIMEOUT_REFUSED_TOKEN = "PRAGMA_BUSY_TIMEOUT_REFUSED"

#: Printed to stdout, once per refusal, by `commit_ground_drop` when the
#: table's own `UNIQUE(scene_fold, drop_key)` constraint (`migrations/
#: 010_ground_drops.sql`) refuses a write -- two callers minted the same
#: `drop_key` for the same scene.  `COO-DECISION 20260903_1843` point 4
#: requires this collision to "fail loudly at the table" rather than one
#: write silently overwriting or winning over the other; the console line
#: follows the same shape `DAMAGE_WRITE_LOCK_REFUSED_TOKEN` above already
#: uses for a different door's refusal, rather than inventing a new one.
GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN = "GROUND_DROP_KEY_COLLISION_REFUSED"

#: The longest `scene` value `commit_ground_drop`/`list_ground_drops_for_
#: scene` will accept -- mirrors `mob_loot.SCENE_NAME_MAX`.  Not imported
#: from `mob_loot` (see `_require_ground_drop_scene` below for why).
GROUND_DROP_SCENE_MAX = 32


def _require_ground_drop_scene(value):
    """A usable `scene` for the ground-drop door, returned exactly as given.

    pf-adversary (round `orpati`) measured that without this check, two
    scene spellings that differ only by a non-ASCII character with no
    plain-ASCII fold equivalent -- the German sharp s (U+00DF) and
    `"STRASSE"`, both `.casefold()` to `"strasse"` under full Unicode
    folding -- collide falsely at the
    table's `UNIQUE(scene_fold, drop_key)` constraint even though they are
    not the same scene, and the collision-refusal `print()` below crashes
    with `UnicodeEncodeError` the moment a non-ASCII `scene` reaches it,
    because this lane's console is cp874.  `migrations/010_ground_drops.
    sql`'s own comment already claims "every scene value this table ever
    holds is required ASCII" by `mob_loot._require_scene` -- true only
    once a LANE-B call site that constructs through `mob_loot.GroundDrop`
    exists (`COO-DECISION 20260903_1844`, not built as of this round); it
    was not true at THIS function's own boundary, which any direct caller
    (a test, a future admin tool) reaches without going through
    `mob_loot` at all.

    This duplicates `mob_loot._require_scene`'s checks rather than
    importing it, for the same lane-boundary reason `commit_ground_drop`'s
    docstring already gives for not importing `mob_loot`: the checks below
    are this table's OWN floor (ASCII-safe printing, fold-safe
    comparison), not a repeat of `mob_loot`'s domain rules (the f32-grid
    check, the drop-key lane-block range, the known-item check), which
    stay LANE-B's alone.
    """
    if type(value) is not str or not value:
        raise ValueError("scene must be a non-empty str")
    if len(value) > GROUND_DROP_SCENE_MAX:
        raise ValueError(
            "scene is %d characters; the ceiling is %d"
            % (len(value), GROUND_DROP_SCENE_MAX)
        )
    if not value.isascii():
        raise ValueError(
            "scene must be ASCII; the console this lane prints to is cp874"
        )
    if any(character.isspace() for character in value):
        raise ValueError("scene must not carry whitespace, got %r" % value)
    if not value.isprintable():
        raise ValueError("scene must be printable, got %r" % value)
    return value

#: Process-wide count of refusals noted through `PRAGMA_BUSY_TIMEOUT_REFUSED_
#: TOKEN` above, incremented by `_note_pragma_busy_timeout_refused` -- so a
#: reader (or a test) can ask "how many, not just whether any" without
#: parsing stdout.  Not reset between calls or characters on purpose: this
#: is a process lifetime count.
#:
#: NOT LOCKED, and a `pf-adversary` pass flagged this honestly rather than
#: asserting it away: `+= 1` on a plain module global is not atomic across
#: threads, so two threads refused at the same GIL-preemption boundary
#: could lose an increment.  Left this way because `PRAGMA busy_timeout`
#: refusing at all is a broken-or-closed-connection condition this
#: codebase has never observed outside a test double built to force it --
#: adding a lock for a race nobody has measured would be exactly the kind
#: of unmeasured change `COO-DECISION 20260901_1100` (this lane's charter)
#: warns against.  If a real refusal under real concurrency is ever
#: observed, that measurement is the thing that should decide whether this
#: needs a lock, not a guess made here.
PRAGMA_BUSY_TIMEOUT_REFUSED_COUNT = 0


def _note_pragma_busy_timeout_refused(door, requested_ms):
    """Counts and prints one `PRAGMA busy_timeout` refusal for `door`
    (`"heal"` or `"damage"`) at the timeout in milliseconds that was asked
    for and refused.  Does not raise and does not touch either caller's
    control flow -- the caller's bare `except sqlite3.Error: pass` becomes
    `except sqlite3.Error: _note_pragma_busy_timeout_refused(...)`, and
    nothing else about that `except` block changes: the caller still goes
    on to attempt `BEGIN IMMEDIATE` next, exactly as it did before this
    function existed.  See `PRAGMA_BUSY_TIMEOUT_REFUSED_TOKEN`.
    """
    global PRAGMA_BUSY_TIMEOUT_REFUSED_COUNT
    PRAGMA_BUSY_TIMEOUT_REFUSED_COUNT += 1
    print("%s door=%s requested_ms=%d count=%d" % (
        PRAGMA_BUSY_TIMEOUT_REFUSED_TOKEN, door, requested_ms,
        PRAGMA_BUSY_TIMEOUT_REFUSED_COUNT))


#: The wire field `/speed` writes: BasicAttr+0x54, `x=7`, whose column name is
#: resolved through `persistence_typed_attrs.column_for` rather than spelled
#: here, so a rename of the column cannot leave this door writing a stale name.
SPEED_WALK_FIELD_X = 7


class _SpeedWriteRefused(Exception):
    """Raised INSIDE `write_speed_by_identity`'s transaction so that
    `connect()` rolls it back, and caught by that method, which reports the
    refusal as `None`.  Private on purpose: it never crosses the boundary,
    and a caller must not learn to catch it instead of checking for `None`.
    """


def _require_identity_part(value: object) -> int:
    """One half of a wire identity pair, or `TypeError`/`ValueError`.

    `bool` is refused before `int` is accepted: SQLite binds `True` as `1`,
    so `identity_lo=True` would otherwise match, and write, the character
    whose identity really is `1`.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"identity part must be an int, got {type(value).__name__}"
        )
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"identity part {value!r} is outside [0, 0xFFFFFFFF]")
    return value


class WriteLockTimeout(sqlite3.OperationalError):
    """A write lock could not be acquired inside the budget, said in full.

    Subclasses `sqlite3.OperationalError` deliberately: a caller that already
    handles that type keeps working unchanged, and one that wants the detail
    (how long, how many attempts) can ask for this type by name.  Nothing has
    been written when it is raised -- it is raised at `BEGIN IMMEDIATE`, so
    the transaction never opened.
    """

class SQLiteStore:
    def __init__(self, path: str | Path, migrations: str | Path):
        self.path, self.migrations = str(path), Path(migrations)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA synchronous=FULL")
            if self.path != ":memory:":
                db.execute("PRAGMA journal_mode=WAL")
        except Exception:
            db.close()
            raise
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def connect_read_only(self):
        """Open the existing database without migrations, WAL changes or commits."""
        if self.path == ":memory:":
            raise ValueError("read-only milestone requires an existing file database")
        path = Path(self.path).resolve(strict=True)
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        try:
            yield db
        finally:
            db.close()

    def list_characters_for_login_read_only(self, login_name: str):
        with self.connect_read_only() as db:
            account = db.execute(
                "SELECT id FROM accounts WHERE login_name=?", (login_name,)
            ).fetchone()
            if account is None:
                raise KeyError(login_name)
            account_id = int(account[0])
            rows = db.execute(
                "SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z,p.heading "
                "FROM characters c JOIN character_positions p ON p.character_id=c.id "
                "WHERE c.account_id=? AND c.deleted_at IS NULL ORDER BY c.selector",
                (account_id,),
            ).fetchall()
        return account_id, [self._character(row) for row in rows]

    def migrate(self) -> None:
        with self.connect() as db:
            files = sorted(self.migrations.glob("[0-9][0-9][0-9]_*.sql"))
            versions = [int(path.name[:3]) for path in files]
            if len(versions) != len(set(versions)):
                raise RuntimeError("duplicate migration version")
            checksums = {
                version: hashlib.sha256(path.read_bytes()).hexdigest()
                for path, version in zip(files, versions)
            }
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT)")
            ledger_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(schema_migrations)")
            }
            if "checksum" not in ledger_columns:
                db.execute("BEGIN IMMEDIATE")
                db.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT")
                for row in db.execute("SELECT version FROM schema_migrations").fetchall():
                    version = int(row[0])
                    if version not in checksums:
                        raise RuntimeError("database schema is newer than this server")
                    db.execute(
                        "UPDATE schema_migrations SET checksum=? WHERE version=?",
                        (checksums[version], version),
                    )
                db.commit()
            applied = {
                int(r[0]): str(r[1])
                for r in db.execute("SELECT version,checksum FROM schema_migrations")
            }
            if set(applied) - set(versions):
                raise RuntimeError("database schema is newer than this server")
            for path, version in zip(files, versions):
                sql = path.read_text(encoding="utf-8")
                checksum = checksums[version]
                if version in applied:
                    if applied[version] != checksum:
                        raise RuntimeError(f"migration checksum mismatch: {path.name}")
                    continue
                stamp = _now()
                script = (
                    "BEGIN IMMEDIATE;\n" + sql + "\n"
                    + "INSERT INTO schema_migrations(version,applied_at,checksum) "
                    + f"VALUES ({version},'{stamp}','{checksum}');\nCOMMIT;"
                )
                try:
                    db.executescript(script)
                except Exception:
                    if db.in_transaction:
                        db.execute("ROLLBACK")
                    raise

    def migrate_with_backup(
        self, *, backups_root=None, label: str = "premigration"
    ):
        """`migrate()`, but the database is copied first when the copy could
        still matter -- returns the snapshot path, or `None` when no snapshot
        was needed.

        LANE-DB owns this method; `migrate()` above is deliberately NOT
        touched, so every existing caller keeps the exact behaviour it has
        today (LANE-DB charter, `pf_bridge/notes_to_chief/
        20260901_1100_COO-DECISION-create-lane-db-persistence-charter.md`:
        new methods in this file are allowed, changing an old one is not).
        This is the method a boot path should call once chief wires it in;
        the owner's rule it implements is `COO-DECISION 20260901_1112`
        point 3.

        The snapshot is taken BEFORE `migrate()` and any failure to take one
        raises `persistence_backup.BackupError` WITHOUT migrating: a boot
        that cannot protect the owner's only copy of the world must not go on
        to change its schema.
        """
        from .persistence_backup import should_snapshot, snapshot_database, pending_versions

        take, reason = should_snapshot(self.path, self.migrations)
        snapshot = None
        if take:
            # Read the ledger ONCE more, here, and hand the same answer to the
            # manifest that this call is acting on -- reading it again inside
            # snapshot_database would let `reason` and `pending_versions`
            # describe two different moments in the same manifest.
            snapshot = snapshot_database(
                self.path,
                backups_root,
                label=label,
                reason=reason,
                pending=pending_versions(self.path, self.migrations),
            )
        self.migrate()
        return snapshot

    def ensure_account(self, name: str) -> int:
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO accounts(login_name,created_at) VALUES (?,?)", (name, _now()))
            return int(db.execute("SELECT id FROM accounts WHERE login_name=?", (name,)).fetchone()[0])

    # PF-HYPOTHESIS-LEDGER: HYP-PF-011 active
    def open_session(self, account_id: int) -> str:
        # Single-session-per-account lease takeover: every open lease of the
        # same account is closed before the new row exists.  Together with the
        # serial accept loop in legacy v141 this is the recorded
        # known-limitation boundary (and interlock) that HYP-PF-011 governs.
        sid = uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE sessions SET closed_at=? WHERE account_id=? AND closed_at IS NULL",
                (_now(), account_id),
            )
            generation = int(db.execute(
                "SELECT COALESCE(MAX(lease_generation),0)+1 FROM sessions WHERE account_id=?",
                (account_id,),
            ).fetchone()[0])
            db.execute(
                "INSERT INTO sessions(id,account_id,lease_generation,opened_at) VALUES (?,?,?,?)",
                (sid, account_id, generation, _now()),
            )
        return sid

    def expire_open_sessions(self) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE sessions SET closed_at=? WHERE closed_at IS NULL", (_now(),)
            )

    def close_session(self, sid: str) -> None:
        with self.connect() as db:
            db.execute("UPDATE sessions SET closed_at=? WHERE id=? AND closed_at IS NULL", (_now(), sid))

    def create_character(self, account_id, name, name_key, fingerprint, build_wire, pos):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            retry = db.execute(
                "SELECT id FROM characters WHERE account_id=? AND create_fingerprint=? AND deleted_at IS NULL",
                (account_id, fingerprint),
            ).fetchone()
            if retry is not None:
                cid = int(retry[0])
                db.commit()
                return self.get_character(cid)
            used = {
                int(r[0]) for r in db.execute(
                    "SELECT selector FROM characters WHERE account_id=? AND deleted_at IS NULL",
                    (account_id,),
                )
            }
            selector = next((n for n in range(256) if n not in used), None)
            if selector is None:
                raise ValueError("no selector available")
            wire, avatar_wire, lo, hi = build_wire(selector)
            now = _now()
            # COO-DECISION 20260902_0443 point 1, chief's half in
            # 20260902_0444: the three vitals are written HERE, at birth, and
            # not as a schema DEFAULT (point 2 forbids that outright).
            #
            # WHY THIS METHOD AND NOT 007.  `migrations/007_character_vitals_
            # seed.sql` seeds a COHORT: the rows that exist the moment it
            # runs, and never again (the migration ledger stops it).  A
            # character created afterwards -- and EVERY character on a fresh
            # install, where 007 meets an empty table -- reached
            # `read_character_vitals(...).require()` with all three columns
            # NULL and was refused, on a server that had just been told what
            # those three numbers are.  This INSERT is the only place a
            # character is born, so it is the only place that can close it.
            #
            # THE NUMBERS COME FROM THE CALL, not from this file.  No literal
            # 1/100/100 appears here on purpose: the day an RE answers what
            # the original game's birth values were, `persistence_vitals.
            # _NEW_CHARACTER_VITALS` changes and nothing else does.
            # `tests/test_persistence_vitals_seed_007.py::...::test_the_
            # numbers_on_a_newborn_row_came_from_the_call_itself` measures
            # exactly that by making the function return numbers nobody could
            # type by accident and looking for THOSE on the row -- a literal,
            # a trigger, or a schema DEFAULT is red there even though all
            # three would hold 1/100/100.
            #
            # Module-attribute call (`vitals.new_character_vitals()`), the
            # same local-import idiom `read_character_vitals` and
            # `apply_damage_to_character` already use in this file, so the
            # name resolves at call time.
            from . import persistence_vitals as vitals
            # The same schema check every other vitals-writing method in this
            # file makes (lines ~1051, ~1204, ~1278, ~1398).  It was missing
            # here in the first draft and a `pf-adversary` pass named the
            # asymmetry: without it, a database where `006`'s columns have
            # been renamed -- the one rename `006`'s own header pre-announces
            # -- makes THIS method raise a raw `sqlite3.OperationalError`
            # from an INSERT, while every sibling raises a named
            # `SchemaDriftError`.  Character creation is rare enough that one
            # extra `PRAGMA table_info` is not a cost worth arguing about.
            vitals.verify_schema(db)
            birth = vitals.new_character_vitals()
            # NO FOURTH COLUMN (COO-DECISION 20260901_1447 point 2, restated
            # by LANE-DB 20260902_1032 point 3).
            #
            # HONEST ABOUT WHAT THIS GUARD IS, because the comment that stood
            # here made two claims a `pf-adversary` pass measured and refuted.
            # It said a short dict "would otherwise reach the INSERT below as
            # a KeyError DURING a transaction rather than before it".  Both
            # halves were wrong: a short dict cannot reach the INSERT at all
            # (`resolve()` reports the missing column as a gap and
            # `new_character_vitals()` raises on `resolution.gaps` before it
            # returns -- measured for both a short and an extra key), and this
            # line already runs INSIDE the transaction, since `BEGIN
            # IMMEDIATE` is this method's first statement ~25 lines above.
            #
            # So this is DEAD CODE against the shipped module and it is kept
            # deliberately, as a belt on a second belt: it is reachable only
            # if `new_character_vitals` is replaced (a monkeypatch, or a later
            # round rewriting it to return a partial mapping), and in that
            # case it fails loudly and writes nothing rather than composing an
            # INSERT out of whatever arrived.  Rollback is identical either
            # way; zero rows, measured.
            if set(birth) != set(vitals.VITAL_COLUMNS):
                raise vitals.VitalsError(
                    "new_character_vitals() must name exactly the three "
                    "vital columns for a birth INSERT; got %r"
                    % (sorted(birth),)
                )
            # Read by literal key, deliberately, so that a rename in
            # `persistence_vitals` fails loudly here instead of quietly
            # swapping hp_current and hp_max through a reordered tuple.
            birth_level = birth["level"]
            birth_hp_current = birth["hp_current"]
            birth_hp_max = birth["hp_max"]
            # One statement, inside the `BEGIN IMMEDIATE` this method already
            # opened: the row is never visible without its vitals, so there is
            # no window in which a login could read a half-born character.
            # No UPDATE, so there is no `WHERE` to get wrong and no way to
            # touch a row that is not this one -- the reset-a-veteran failure
            # `_second_birth` was written to catch cannot be spelled here.
            cur = db.execute("INSERT INTO characters(account_id,selector,name,name_key,create_fingerprint,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at,level,hp_current,hp_max) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (account_id,selector,name,name_key,fingerprint,wire,avatar_wire,None,lo,hi,now,now,birth_level,birth_hp_current,birth_hp_max))
            cid = int(cur.lastrowid)
            db.execute(
                "INSERT INTO character_positions(character_id,scene_id,scene_seq,x,y,z,updated_at,heading) VALUES (?,?,?,?,?,?,?,?)",
                (cid,pos.scene_id,pos.scene_seq,pos.x,pos.y,pos.z,_now(),pos.heading),
            )
            self._insert_initial_backpack(db, cid, now)
        return self.get_character(cid)

    # PF-HYPOTHESIS-LEDGER: HYP-PF-015 active
    def soft_delete_character(self, sid: str, selector: int) -> int:
        """Soft-delete one owned, active, unselected character by selector.

        Sets ``deleted_at`` (and ``updated_at``) only; child position and
        backpack rows survive as history behind the deleted parent, and the
        migration-004 partial unique indexes free the selector, identity, and
        fingerprint slots for a later create.  Every guard failure raises
        before any write: stale or closed sessions, characters the session's
        account does not own, already-deleted characters, and characters
        selected by any open session all fail closed.
        """
        if type(selector) is not int:
            raise TypeError("delete selector must be int")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT c.id FROM sessions s JOIN characters c "
                "ON c.account_id=s.account_id "
                "WHERE s.id=? AND s.closed_at IS NULL "
                "AND c.selector=? AND c.deleted_at IS NULL",
                (sid, selector),
            ).fetchone()
            if row is None:
                raise PermissionError(
                    "stale session or unknown active character"
                )
            cid = int(row[0])
            selected = db.execute(
                "SELECT 1 FROM sessions "
                "WHERE selected_character_id=? AND closed_at IS NULL",
                (cid,),
            ).fetchone()
            if selected is not None:
                raise PermissionError(
                    "character is selected by an open session"
                )
            now = _now()
            cur = db.execute(
                "UPDATE characters SET deleted_at=?, updated_at=? "
                "WHERE id=? AND deleted_at IS NULL",
                (now, now, cid),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    "soft delete target changed during transaction"
                )
        return cid

    def list_characters(self, account_id: int):
        with self.connect() as db:
            rows = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z,p.heading FROM characters c JOIN character_positions p ON p.character_id=c.id WHERE c.account_id=? AND c.deleted_at IS NULL ORDER BY c.selector", (account_id,)).fetchall()
        return [self._character(r) for r in rows]

    def get_character(self, cid: int):
        with self.connect() as db:
            row = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z,p.heading FROM characters c JOIN character_positions p ON p.character_id=c.id WHERE c.id=? AND c.deleted_at IS NULL", (cid,)).fetchone()
        if row is None: raise KeyError(cid)
        return self._character(row)

    def select_character(self, sid: str, selector: int):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z,p.heading FROM sessions s JOIN characters c ON c.account_id=s.account_id JOIN character_positions p ON p.character_id=c.id WHERE s.id=? AND s.closed_at IS NULL AND c.deleted_at IS NULL AND c.selector=?", (sid,selector)).fetchone()
            if row is None: raise KeyError(selector)
            db.execute("UPDATE sessions SET selected_character_id=? WHERE id=?", (row['id'],sid))
        return self._character(row)

    def save_position(self, sid: str, cid: int, pos: Position, *, write_position: bool = True):
        # write_position=False (CORE-REQUEST-018 / GT-106 (4).3, pf-adversary
        # finding 1): a caller that is skipping the actual column write for a
        # persist_position_allowed=False scene must still prove sid owns an
        # open, non-stale lease on cid -- this EXISTS/SELECT check is the
        # project's only detection signal for a stale/superseded session
        # (see the multiplayer-readiness audit report), and silently
        # short-circuiting it here would turn a loud PermissionError into a
        # no-op for exactly the scene this project already flagged riskiest.
        if not write_position:
            with self.connect() as db:
                owning = db.execute(
                    "SELECT 1 FROM sessions WHERE id=? AND selected_character_id=? AND closed_at IS NULL",
                    (sid, cid),
                ).fetchone()
            if owning is None:
                raise PermissionError("stale or non-owning character session")
            return
        if not (0 <= pos.scene_id <= 0xFFFF and 0 <= pos.scene_seq <= 0xFFFFFFFFFFFFFFFF):
            raise ValueError("position scene identity is outside wire bounds")
        if not all(math.isfinite(v) for v in (pos.x, pos.y, pos.z, pos.heading)):
            raise ValueError("position contains a non-finite value")
        with self.connect() as db:
            cur = db.execute("UPDATE character_positions SET scene_id=?,scene_seq=?,x=?,y=?,z=?,heading=?,updated_at=? WHERE character_id=? AND EXISTS (SELECT 1 FROM sessions WHERE id=? AND selected_character_id=? AND closed_at IS NULL)", (pos.scene_id,pos.scene_seq,pos.x,pos.y,pos.z,pos.heading,_now(),cid,sid,cid))
            if cur.rowcount != 1:
                raise PermissionError("stale or non-owning character session")

    @staticmethod
    def _insert_initial_backpack(db, character_id: int, stamp: str) -> None:
        state = INITIAL_BACKPACK
        # The counter is seeded FROM THE ROWS THIS FUNCTION IS ABOUT TO WRITE,
        # not left to the column's DEFAULT.  Migration 005's default of 5 is
        # correct only while INITIAL_BACKPACK's highest identity is 4; the day
        # someone adds a fifth starting row, a silent default would hand the
        # first pickup an identity a live row already holds -- which is the
        # exact bug the column exists to prevent, arriving through the one
        # door the column does not watch.
        db.execute(
            "INSERT INTO character_backpacks(character_id,base_mask,base_identity,range_mask,next_item_identity,updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                character_id, state.base_mask, state.base_identity,
                state.range_mask,
                max((item.identity for item in state.items), default=0) + 1,
                stamp,
            ),
        )
        db.executemany(
            "INSERT INTO character_backpack_items("
            "character_id,item_identity,template_id,quantity,slot,raw_u8_38,raw_u8_39,detail_present"
            ") VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    character_id, item.identity, item.template_id,
                    item.quantity, item.slot, item.raw_u8_38,
                    item.raw_u8_39, item.detail_present,
                )
                for item in state.items
            ],
        )

    @staticmethod
    def _load_backpack(db, character_id: int) -> BackpackState:
        header = db.execute(
            "SELECT base_mask,base_identity,range_mask FROM character_backpacks "
            "WHERE character_id=?",
            (character_id,),
        ).fetchone()
        if header is None:
            raise RuntimeError("character Backpack state is missing")
        rows = db.execute(
            "SELECT item_identity,template_id,quantity,slot,raw_u8_38,raw_u8_39,detail_present "
                # The serialized client container is keyed by item identity.
                # Keeping that order is byte-neutral for the two exact states;
                # its post-move reconnect use is governed by HYP-PF-008.
                "FROM character_backpack_items WHERE character_id=? ORDER BY item_identity",
            (character_id,),
        ).fetchall()
        state = BackpackState(
            int(header[0]), int(header[1]), int(header[2]),
            tuple(
                ItemAttrState(*(int(value) for value in row))
                for row in rows
            ),
        )
        # Shape only here (COO-DECISION 20260826_0950): this is the
        # character-select load path, and it must return a real player's bag
        # whatever its contents are.  Every mutation reached through this
        # loader (move/merge/swap) still re-validates full content via its
        # own require_known_backpack call in inventory.py before it commits
        # anything, so this relaxation does not widen those.
        return require_backpack_shape(state)

    @staticmethod
    def _require_selected_session(db, sid: str, character_id: int) -> None:
        owner = db.execute(
            "SELECT 1 FROM sessions s JOIN characters c "
            "ON c.id=s.selected_character_id AND c.account_id=s.account_id "
            "AND c.deleted_at IS NULL WHERE s.id=? AND s.selected_character_id=? "
            "AND s.closed_at IS NULL",
            (sid, character_id),
        ).fetchone()
        if owner is None:
            raise PermissionError("stale or non-owning character session")

    def get_backpack(self, sid: str, character_id: int) -> BackpackState:
        with self.connect() as db:
            self._require_selected_session(db, sid, character_id)
            return self._load_backpack(db, character_id)

    @staticmethod
    def _next_item_identity(db, character_id: int) -> int:
        row = db.execute(
            "SELECT next_item_identity FROM character_backpacks WHERE character_id=?",
            (character_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("character Backpack state is missing")
        return int(row[0])

    def backpack_issued_through(self, sid: str, character_id: int) -> int:
        """The highest item identity this character has EVER been issued.

        THE COLUMN AND THIS NUMBER ARE ONE APART, AND THE SUBTRACTION LIVES
        HERE SO IT HAPPENS ONCE.  Migration 005 spends a paragraph on the
        trap: ``character_backpacks.next_item_identity`` is EXCLUSIVE (the
        next free identity to hand out), while the ``issued_through``
        parameter of ``mob_pickup.next_item_identity`` -- and of
        ``mob_pickup.BagCell`` -- is INCLUSIVE (the highest identity already
        handed out, to which that lane adds one).  A call site that seeds a
        cell with the column's own value skips one identity per session:
        wasteful rather than unsafe, but wrong, and wrong in a way no test of
        either module alone can see.  Callers seeding a bag cell at character
        select ask for this and never read the column themselves.

        Not derived from the rows in the bag.  A bag that once held identity 5
        and has since spent it reports 5 here, which is the whole reason the
        column exists.
        """
        with self.connect() as db:
            self._require_selected_session(db, sid, character_id)
            return self._next_item_identity(db, character_id) - 1

    def commit_acquired_backpack_item(
        self, sid: str, character_id: int, item: ItemAttrState,
    ) -> BackpackState:
        """Persist one picked-up row AND advance the identity counter, or neither.

        This is the write half of a pickup.  ``mob_pickup`` owns what a picked
        up row looks like (its slot, its identity, its new-row constants) and
        composes it in memory; this method is the only thing in the codebase
        that puts such a row in the database, and it does that in ONE
        transaction with the counter advance.  A row at identity 5 with the
        counter still reading 5 is the failure this shape exists to make
        impossible: the next pickup would mint 5 again, and the client's
        clear-by-identity/place-by-slot apply loop cannot tell two rows
        wearing one identity apart.

        THE IDENTITY IS CHECKED AGAINST THE COLUMN, NOT TAKEN FROM THE BAG.
        The caller mints through ``mob_pickup.next_item_identity``, which is
        seeded from :meth:`backpack_issued_through`; if the two ever disagree
        this refuses by name rather than writing the caller's number.  It does
        not silently OVERWRITE the caller's identity with the column's either:
        the caller may already have composed the client's bag-delta bytes from
        that item (``mob_pickup.bag_delta_pc`` does exactly that, before the
        drop leaves the ground), so a store that quietly renumbered the row
        would put a different identity on the wire than in the database.

        Ownership is checked the way ``save_position`` checks it: a session
        that does not have this character selected cannot write into its bag.
        """
        if type(item) is not ItemAttrState:
            raise TypeError("acquired item must be an exact ItemAttrState")
        # WHAT THIS METHOD ACCEPTS MUST BE A SUBSET OF WHAT GATE 2 ADMITS,
        # and these two bounds are the difference.  ``require_backpack_shape``
        # below allows quantity 0 and template 0; gate 2 -- the
        # character-select admission predicate, named here by its role
        # because that gate's test file pins which modules may name it, and
        # a persistence method is not one of them -- refuses an
        # acquired row with either.  A row this method committed and that gate
        # refuses is UNREMOVABLE -- there is no delete-item path -- so the
        # character could never enter the world again without the
        # HYP-PF-008 opt-in.  Refused here, before the transaction, rather
        # than left unreachable-by-luck because ``place_in_bag`` happens to
        # bound them today.
        if item.quantity < 1:
            raise ValueError(
                "quantity %d is not a pickup quantity; gate 2 would refuse "
                "this row forever" % item.quantity
            )
        if item.template_id < 1:
            raise ValueError(
                "template id 0 is not a pickup template; gate 2 would refuse "
                "this row forever"
            )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            expected_identity = self._next_item_identity(db, character_id)
            if item.identity != expected_identity:
                raise ValueError(
                    "acquired identity %d is not this character's next free "
                    "identity %d" % (item.identity, expected_identity)
                )
            before = self._load_backpack(db, character_id)
            if any(row.slot == item.slot for row in before.items):
                raise ValueError(
                    "slot %d is occupied; a pickup goes to a free slot"
                    % item.slot
                )
            # Structure is validated on the value that is ABOUT to be written,
            # before anything is written: a duplicate identity or a bag that
            # would come back malformed refuses here rather than through an
            # IntegrityError with the database's wording instead of ours.
            expected = require_backpack_shape(BackpackState(
                before.base_mask, before.base_identity, before.range_mask,
                tuple(sorted(
                    before.items + (item,), key=lambda row: row.identity,
                )),
            ))
            inserted = db.execute(
                "INSERT INTO character_backpack_items("
                "character_id,item_identity,template_id,quantity,slot,raw_u8_38,raw_u8_39,detail_present"
                ") VALUES (?,?,?,?,?,?,?,?)",
                (
                    character_id, item.identity, item.template_id,
                    item.quantity, item.slot, item.raw_u8_38,
                    item.raw_u8_39, item.detail_present,
                ),
            )
            if inserted.rowcount != 1:
                raise RuntimeError("acquired row was not inserted")
            # The counter moves under its own read value: a second writer that
            # advanced it between this transaction's read and this statement
            # leaves rowcount 0, and the whole transaction rolls back rather
            # than stamping a stale number over a newer one.
            advanced = db.execute(
                "UPDATE character_backpacks SET next_item_identity=?,updated_at=? "
                "WHERE character_id=? AND next_item_identity=?",
                (item.identity + 1, _now(), character_id, expected_identity),
            )
            if advanced.rowcount != 1:
                raise RuntimeError(
                    "identity counter changed during the pickup transaction"
                )
            after = self._load_backpack(db, character_id)
            if after != expected:
                raise RuntimeError("acquired-row post-state validation failed")
            return after

    def apply_v111_stack_merge(
        self, sid: str, character_id: int,
    ) -> BackpackState | None:
        """Atomically install only the exact accepted identity3->identity1 state."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            before = self._load_backpack(db, character_id)
            if before == MERGED_V111_BACKPACK:
                return None
            if before != INITIAL_BACKPACK:
                raise ValueError("Backpack is outside the exact V111 pre-state")
            updated = db.execute(
                "UPDATE character_backpack_items SET quantity=2 "
                "WHERE character_id=? AND item_identity=1 AND template_id=2600001 "
                "AND quantity=1 AND slot=0 AND raw_u8_38=0 "
                "AND raw_u8_39=255 AND detail_present=0",
                (character_id,),
            )
            if updated.rowcount != 1:
                raise RuntimeError("exact V111 target row changed during transaction")
            removed = db.execute(
                "DELETE FROM character_backpack_items "
                "WHERE character_id=? AND item_identity=3 AND template_id=2600001 "
                "AND quantity=1 AND slot=2 AND raw_u8_38=0 "
                "AND raw_u8_39=255 AND detail_present=0",
                (character_id,),
            )
            if removed.rowcount != 1:
                raise RuntimeError("exact V111 source row changed during transaction")
            db.execute(
                "UPDATE character_backpacks SET updated_at=? WHERE character_id=?",
                (_now(), character_id),
            )
            after = self._load_backpack(db, character_id)
            if after != MERGED_V111_BACKPACK:
                raise RuntimeError("exact V111 post-state validation failed")
            return after

    # PF-HYPOTHESIS-LEDGER: HYP-PF-008 active
    def apply_hypothesized_v111_slot2_move(
        self, sid: str, character_id: int,
    ) -> BackpackState | None:
        """Atomically install only the governed merged-slot0 -> free-slot2 state."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            before = self._load_backpack(db, character_id)
            if before == HYPOTHESIZED_V111_SLOT2_BACKPACK:
                return None
            if before != MERGED_V111_BACKPACK:
                raise ValueError("Backpack is outside the HYP-PF-008 pre-state")
            moved = db.execute(
                "UPDATE character_backpack_items SET slot=2 "
                "WHERE character_id=? AND item_identity=1 AND template_id=2600001 "
                "AND quantity=2 AND slot=0 AND raw_u8_38=0 "
                "AND raw_u8_39=255 AND detail_present=0",
                (character_id,),
            )
            if moved.rowcount != 1:
                raise RuntimeError("HYP-PF-008 target row changed during transaction")
            db.execute(
                "UPDATE character_backpacks SET updated_at=? WHERE character_id=?",
                (_now(), character_id),
            )
            after = self._load_backpack(db, character_id)
            if after != HYPOTHESIZED_V111_SLOT2_BACKPACK:
                raise RuntimeError("HYP-PF-008 post-state validation failed")
            return after

    # PF-HYPOTHESIS-LEDGER: HYP-PF-010 active
    def move_backpack_item_to_free_slot(
        self, sid: str, character_id: int,
        item_identity: int, destination_slot: int,
    ) -> BackpackState | None:
        """Atomically move one governed item to one currently empty slot."""
        if type(item_identity) is not int:
            raise TypeError("item identity must be int")
        if type(destination_slot) is not int:
            raise TypeError("destination slot must be int")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            before = self._load_backpack(db, character_id)
            transition = move_known_item_to_free_slot(
                before, item_identity, destination_slot,
            )
            if transition is None:
                return None
            expected, current_item = transition
            moved = db.execute(
                "UPDATE character_backpack_items SET slot=? "
                "WHERE character_id=? AND item_identity=? AND slot=?",
                (
                    destination_slot, character_id,
                    item_identity,
                    next(
                        item.slot for item in before.items
                        if item.identity == current_item.identity
                    ),
                ),
            )
            if moved.rowcount != 1:
                raise RuntimeError("Backpack item changed during move transaction")
            db.execute(
                "UPDATE character_backpacks SET updated_at=? WHERE character_id=?",
                (_now(), character_id),
            )
            after = self._load_backpack(db, character_id)
            if after != expected:
                raise RuntimeError("free-slot move post-state validation failed")
            return after

    # PF-HYPOTHESIS-LEDGER: HYP-PF-017 active
    def swap_backpack_item_with_occupied_slot(
        self, sid: str, character_id: int,
        item_identity: int, destination_slot: int,
    ) -> BackpackState:
        """Atomically swap one governed item with the occupant of its target.

        The UNIQUE(character_id,slot) constraint forbids a direct two-row
        UPDATE, so the source row parks on the transient slot 65535 (lawful
        for the column CHECK, never visible outside this transaction, and
        re-validated away by the post-state load) while the occupant moves
        into the vacated slot.  Every step asserts its exact rowcount and the
        final state must equal the pure transition's post-state byte for
        byte, or the whole transaction rolls back.
        """
        if type(item_identity) is not int:
            raise TypeError("item identity must be int")
        if type(destination_slot) is not int:
            raise TypeError("destination slot must be int")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            before = self._load_backpack(db, character_id)
            expected, moved, displaced = swap_known_item_with_occupied_slot(
                before, item_identity, destination_slot,
            )
            source_slot = displaced.slot
            parked = db.execute(
                "UPDATE character_backpack_items SET slot=65535 "
                "WHERE character_id=? AND item_identity=? AND slot=?",
                (character_id, moved.identity, source_slot),
            )
            if parked.rowcount != 1:
                raise RuntimeError("swap source row changed during transaction")
            vacated = db.execute(
                "UPDATE character_backpack_items SET slot=? "
                "WHERE character_id=? AND item_identity=? AND slot=?",
                (
                    source_slot, character_id,
                    displaced.identity, destination_slot,
                ),
            )
            if vacated.rowcount != 1:
                raise RuntimeError("swap occupant row changed during transaction")
            landed = db.execute(
                "UPDATE character_backpack_items SET slot=? "
                "WHERE character_id=? AND item_identity=? AND slot=65535",
                (destination_slot, character_id, moved.identity),
            )
            if landed.rowcount != 1:
                raise RuntimeError("swap parked row changed during transaction")
            db.execute(
                "UPDATE character_backpacks SET updated_at=? WHERE character_id=?",
                (_now(), character_id),
            )
            after = self._load_backpack(db, character_id)
            if after != expected:
                raise RuntimeError("occupied-swap post-state validation failed")
            return after

    # PF-HYPOTHESIS-LEDGER: HYP-PF-018 active
    def merge_backpack_item_into_occupied_slot(
        self, sid: str, character_id: int,
        item_identity: int, destination_slot: int,
    ) -> BackpackState:
        """Atomically merge one governed item into its same-template target.

        The surviving target row takes the summed quantity and the consumed
        source row is deleted, both inside one transaction against the two
        named persistence tables; every step asserts its exact rowcount
        (keyed on identity, slot, template, and the pre-merge quantity) and
        the final state must equal the pure transition's post-state byte for
        byte, or the whole transaction rolls back.
        """
        if type(item_identity) is not int:
            raise TypeError("item identity must be int")
        if type(destination_slot) is not int:
            raise TypeError("destination slot must be int")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_selected_session(db, sid, character_id)
            before = self._load_backpack(db, character_id)
            expected, merged, consumed = merge_known_item_into_occupied_slot(
                before, item_identity, destination_slot,
            )
            survived = db.execute(
                "UPDATE character_backpack_items SET quantity=? "
                "WHERE character_id=? AND item_identity=? AND slot=? "
                "AND template_id=? AND quantity=?",
                (
                    merged.quantity, character_id, merged.identity,
                    merged.slot, merged.template_id,
                    merged.quantity - consumed.quantity,
                ),
            )
            if survived.rowcount != 1:
                raise RuntimeError("merge target row changed during transaction")
            removed = db.execute(
                "DELETE FROM character_backpack_items "
                "WHERE character_id=? AND item_identity=? AND slot=? "
                "AND template_id=? AND quantity=?",
                (
                    character_id, consumed.identity, consumed.slot,
                    consumed.template_id, consumed.quantity,
                ),
            )
            if removed.rowcount != 1:
                raise RuntimeError("merge source row changed during transaction")
            db.execute(
                "UPDATE character_backpacks SET updated_at=? WHERE character_id=?",
                (_now(), character_id),
            )
            after = self._load_backpack(db, character_id)
            if after != expected:
                raise RuntimeError("occupied-merge post-state validation failed")
            return after

    def read_typed_attributes(self, character_id: int) -> dict[str, int | float]:
        """Every typed attribute column of this character that HAS a value.

        LANE-DB owns this method (charter `COO-DECISION 20260901_1100`: new
        methods here are allowed, changing an old one is not); no existing
        method is touched by it.

        A column that is NULL is OMITTED from the result -- it is never
        rendered as `0`.  That omission is load-bearing rather than tidy:
        `persistence_attr_compose` refuses to compose an attribute block for
        a server-owned field it was handed no value for, so an unseeded
        column arrives there as absent and the owner's "never guess zero"
        rule (`COO-DECISION 20260901_1059`) holds without anything else
        having to remember it.  A caller can therefore treat `column in
        result` as "the database really knows this one".

        Raises `KeyError` for a character that does not exist or has been
        soft-deleted, matching `get_character`.
        """
        from . import persistence_typed_attrs as typed_attrs

        columns = list(typed_attrs.TYPED_COLUMNS)
        projection = ",".join(columns)
        with self.connect() as db:
            row = db.execute(
                f"SELECT {projection} FROM characters "
                "WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
        if row is None:
            raise KeyError(character_id)
        return {c: row[c] for c in columns if row[c] is not None}

    def read_typed_attributes_and_name(
        self, character_id: int
    ) -> tuple[dict[str, int | float], str]:
        """``(read_typed_attributes(character_id), name)`` from ONE connection.

        LANE-DB owns this method; no existing method is touched by it.

        Built for `persistence_attr_compose.live_typed_values_for`
        (`pf-adversary` round `1cajqi`, finding 2): that caller needs both the
        typed columns and the name for the SAME row, and two separate calls to
        `read_typed_attributes`/`get_character` -- each opening its own
        connection -- leaves a window between them where a concurrent write
        (or soft-delete) can make the two reads describe two different
        moments of the same character.  Measured, not merely reasoned about:
        the adversary pass reproduced both outcomes live -- a write landing in
        that window is missed by whichever half already ran, and a soft-delete
        landing in it makes one half raise `KeyError` while the other still
        returns.  One connection, one row, closes the window; the character's
        name comes from the SAME `SELECT`, not a second query.
        """
        from . import persistence_typed_attrs as typed_attrs

        columns = list(typed_attrs.TYPED_COLUMNS)
        projection = ",".join(columns)
        with self.connect() as db:
            row = db.execute(
                f"SELECT {projection},name FROM characters "
                "WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
        if row is None:
            raise KeyError(character_id)
        typed = {c: row[c] for c in columns if row[c] is not None}
        return typed, row["name"]

    def write_typed_attributes(
        self, character_id: int, values: dict[str, int | float]
    ) -> dict[str, int | float]:
        """Validate, then store, typed attribute columns for one character.

        LANE-DB owns this method; no existing method is touched by it.

        Every value goes through `persistence_typed_attrs.validate` FIRST, so
        a value that could not survive the wire encoder (a bool, a float in an
        integer field, a number outside the field's wire range, `None`) is
        refused before any SQL runs, with the column named.  The column's own
        SQL CHECK in `migrations/006_character_typed_attribute_columns.sql` is
        the second line of the same defence, for a writer that does not come
        through here.

        Returns the character's full typed-attribute state after the write
        (the same shape `read_typed_attributes` returns), so a caller does not
        have to guess whether the row it just wrote also has other values.
        That read-back happens INSIDE this method's own transaction, on the
        same connection.  An adversary pass measured what the obvious shape --
        commit, then call `read_typed_attributes` -- does under concurrency:
        another writer soft-deleting the character in that window made this
        method COMMIT the write and then raise `KeyError` (a caller catching
        `KeyError` would report "no such character" while the row on disk had
        changed), and another writer's value came back as "the state after
        this write".  Neither is possible while the read is under the same
        lock as the write.

        Raises `KeyError` for a character that does not exist or has been
        soft-deleted, and `persistence_typed_attrs.TypedAttrError` for a value
        this schema may not hold.  Nothing is written when anything is refused.
        """
        from . import persistence_typed_attrs as typed_attrs

        checked = typed_attrs.validate_all(values)
        assignments = ",".join(f"{column}=?" for column in checked)
        columns = list(typed_attrs.TYPED_COLUMNS)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM characters WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(character_id)
            # `deleted_at IS NULL` is repeated here on purpose.  The guard
            # above is the error message; this predicate is what makes the
            # write itself impossible on a soft-deleted row, so removing
            # either one alone cannot land a write where the API says it
            # cannot -- an adversary pass deleted the guard and every test
            # stayed green while the UPDATE landed.
            written = db.execute(
                f"UPDATE characters SET {assignments},updated_at=? "
                "WHERE id=? AND deleted_at IS NULL",
                (*checked.values(), _now(), character_id),
            ).rowcount
            if written != 1:
                raise KeyError(character_id)
            after = db.execute(
                f"SELECT {','.join(columns)} FROM characters WHERE id=?",
                (character_id,),
            ).fetchone()
        return {c: after[c] for c in columns if after[c] is not None}

    def write_typed_attribute_if_unset(
        self, character_id: int, column: str, value: int | float
    ) -> int | float | None:
        """Write ONE typed attribute column, but only while it is NULL.

        New method (LANE-DB's charter, `COO-DECISION 20260901_1100`: new
        methods here are allowed, changing an old one is not) added for the
        class-id creation hookup (`lifecycle.persist_class_id_from_starting_
        gear`, CORE-REQUEST `pf_bridge/notes_to_chief/20260904_0423`,
        pf-adversary D2 on `#705`, granted by `COO-DECISION 20260904_0549`
        item 1): `CharacterLifecycle.create` calls
        `store.create_character` and then, once the row is committed,
        writes the resolved class id -- but a re-sent `CreateActorDataEx`
        (the SAME fingerprint retry path `create_character` already
        tolerates) replays that call a second time, and unconditional
        `write_typed_attributes` would silently revert a class id written
        by ANY OTHER path in the meantime (LANE-DB's NULL-only backfill,
        `COO-DECISION 20260904_0445`, is exactly such a path).

        The guard is one `UPDATE ... WHERE column IS NULL` inside a single
        `BEGIN IMMEDIATE` transaction, not a read then a write: two calls
        would leave the exact TOCTOU window this method exists to close
        (the row could gain a value between them).

        Returns the value actually written, or ``None`` if the column
        already held something else -- the row is untouched either way,
        which is not an error: the resolved value did not change, only
        who is allowed to still write it.

        Raises `KeyError` for a character that does not exist or has been
        soft-deleted, and `persistence_typed_attrs.TypedAttrError` for a
        value this schema may not hold -- validated before any SQL runs,
        same as `write_typed_attributes`.
        """
        from . import persistence_typed_attrs as typed_attrs

        checked = typed_attrs.validate_all({column: value})
        (validated_column,) = checked
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM characters WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(character_id)
            written = db.execute(
                f"UPDATE characters SET {validated_column}=?,updated_at=? "
                f"WHERE id=? AND deleted_at IS NULL AND {validated_column} IS NULL",
                (checked[validated_column], _now(), character_id),
            ).rowcount
        return checked[validated_column] if written == 1 else None

    def list_character_ids_missing_class_id(self) -> tuple[int, ...]:
        """Ids of every live character whose ``class_id`` is still NULL.

        New method (LANE-DB's charter, `COO-DECISION 20260901_1100`: new
        methods here are allowed, changing an old one is not).  For the
        boot-time backfill `COO-DECISION 20260904_0445` ordered: the
        creation-time hookup (`lifecycle.persist_class_id_from_starting_gear`,
        called through `write_typed_attribute_if_unset` above) only reaches a
        character at the moment she is created, so every character who
        existed before that hookup landed is still NULL here and stays that
        way forever unless something goes back for her.  This method is the
        read half of "something" -- a plain, read-only SELECT, no write, no
        decode, no class resolution.  A caller loops over the ids this
        returns and calls the SAME creation-time function on each one
        (`persistence_class_id.resolve_class_id`'s NULL-only,
        never-a-guess contract is what makes that safe to repeat), which
        keeps this lane from writing a second class-id resolver -- rule (a)
        of `COO-DECISION 20260904_0445`.

        Excludes soft-deleted rows (`deleted_at IS NOT NULL`) for the same
        reason `get_character`/`list_characters` do: a deleted character is
        not on anyone's screen to backfill for, and `write_typed_attribute_
        if_unset` refuses a soft-deleted row anyway (`KeyError`), so
        including her here would only print a failure line for a character
        nobody is fixing.  Ordered by id so a boot log naming failures reads
        in a stable, reproducible sequence rather than in whatever order
        SQLite happens to walk the table.

        GUARDED AGAINST A DATABASE THAT HAS NOT RUN MIGRATION 006 YET
        (`KA1A-R314-RESULTS`, `pf_bridge/notes_to_chief/
        20260905_0233_...boot-crash-class-id-backfill.md`): `app.py`'s only
        call site for the module that loops over this method's result sits
        AFTER an `if/else` that does not call `migrate_with_backup()` on
        every boot path (a read-only `--scene-load-scenario` boot in
        particular) -- on a database that predates migration 006, the bare
        `class_id IS NULL` clause below raised
        `sqlite3.OperationalError: no such column: class_id` and took the
        whole boot down with it.  `app.py` is chief's write zone, not this
        lane's, so the fix lives here instead of at that call site: a
        database missing the column has nothing this method could truthfully
        call "missing its `class_id`" -- the column itself does not exist
        yet -- so this reports zero rows rather than crashing.  A boot path
        that DOES call `migrate_with_backup()` adds the column before this
        method ever runs, so this guard never fires for it and today's
        behaviour for every already-migrated database is unchanged byte for
        byte.
        """
        with self.connect() as db:
            columns = {
                str(row["name"])
                for row in db.execute("PRAGMA table_info(characters)")
            }
            if "class_id" not in columns:
                return ()
            rows = db.execute(
                "SELECT id FROM characters "
                "WHERE class_id IS NULL AND deleted_at IS NULL "
                "ORDER BY id"
            ).fetchall()
        return tuple(row["id"] for row in rows)

    def write_typed_attributes_and_compose_sparse(
        self, character_id: int, values: dict[str, int | float]
    ) -> dict[int, object]:
        """Persist typed columns, then hand back the SPARSE `{x: value}` for
        exactly the columns this call wrote -- ready for
        `gm/attr_wire.encode_block`.

        LANE-DB owns this method; no existing method is touched by it.  It is
        the entry point on the PERSISTENCE side for `/speed`
        (`COO-ORDER 20260901_1640` / `20260901_1641`), and it exists so that
        the four steps in between -- validate, write, read back, compose --
        cannot be assembled in the wrong order at the call site.

        IT IS NOT THE WIRE-SIDE ENTRY POINT, AND THE TWO DISAGREE.
        `gm/attr_wire.build_named_field_update` calls itself "the one entry
        point a future chat-command action should call", and it REFUSES x=7
        (`FIELDS` marks it `known=False`) and composes a merged FULL block --
        which is what `COO-ORDER 20260901_1641` forbids on this path.  So a
        caller of this method must hand the returned dict to `encode_block` /
        `make_update_attr_frame` directly, routing around that lane's policy
        gate.  That is deliberate, and the cost is worth stating: on this
        path `compose_sparse_block` is the ONLY thing between a caller and
        `SENSITIVE_FIELDS`.  An adversary pass found this collision; neither
        file said it before.

        DB FIRST, WIRE SECOND, on purpose: the value is validated and stored
        before any block exists, so a refused value never reaches a frame and
        a caller cannot show the player a speed the database never accepted.
        The composed value is taken from the row read back inside
        `write_typed_attributes`' own transaction rather than from the
        caller's dict -- but be honest about what that buys: no input has yet
        been found for which the two differ (SQLite round-trips a python float
        exactly and `as_f32` is idempotent), so the read-back is a structural
        choice, NOT a measured safety property.  An adversary pass replaced it
        with the caller's own dict and every test stayed green.

        WHICH DATABASE THIS WRITES TO IS NOT ENFORCED HERE.
        `COO-ORDER 20260901_1641` allows this path only against the attended
        round's run-copy and forbids pointing it at the canonical database.
        This method writes to whatever file its `SQLiteStore` was built
        against and cannot see which one that is, so that constraint lives at
        the call site and in the boot job -- it is not carried by this code,
        and no green test here means it was honoured.

        ONLY the columns named in `values` end up in the block.  The write
        returns the character's whole typed-attribute state (level, hp, ...
        whatever else that row already has), and composing THAT would quietly
        turn a one-field send into a multi-field one -- which is exactly what
        `COO-ORDER 20260901_1641` forbids on this path.  So the projection is
        `values`' own keys, and the sparse gate refuses anything outside
        `SPARSE_APPROVED_FIELDS` (x=7 today) on top of that.

        Raises `KeyError` for a character that does not exist or is
        soft-deleted, `persistence_typed_attrs.TypedAttrError` for a value the
        schema may not hold, and
        `persistence_attr_compose.AttrComposeError` for a field this path is
        not allowed to send.  Note the ordering: a refusal from the compose
        gate happens AFTER the write has committed, because the write is the
        durable truth and the block is a view of it -- a column this server
        owns is not made wrong by the fact that one send path may not carry
        it.  A caller must not read the exception as "nothing was stored".
        """
        from . import persistence_typed_attrs as typed_attrs
        from .persistence_attr_compose import compose_sparse_block

        stored = self.write_typed_attributes(character_id, values)
        written = {column: stored[column] for column in values}
        return compose_sparse_block(typed_attrs.typed_values_for_compose(written))

    def read_character_vitals(self, character_id: int):
        """This character's `level`/`hp_current`/`hp_max`, and every reason
        they are not usable -- `persistence_vitals.VitalsResolution`.

        LANE-DB owns this method (charter `COO-DECISION 20260901_1100`); no
        existing method is touched by it.  It is `read_typed_attributes`
        narrowed to the three columns M4 needs and passed through the vitals
        gate, so that a caller gets either three numbers that have survived
        every rule or a named list of what is missing -- never a zero standing
        in for a column nobody has written yet.

        WHAT THIS RETURNS TODAY changed with `migrations/007_character_vitals_
        seed.sql` (`COO-DECISION 20260902_0250`), and the sentence that used to
        be here -- "all three columns are NULL on every existing character" --
        is no longer true, so it is replaced rather than left to rot.  After
        `007` a character that EXISTED when the migration ran resolves
        complete, at `level 1, hp 100/100`.

        REWRITTEN AGAIN 2026-09-02 (chief, R308), and the sentence it replaces
        is quoted so a reader can see what changed: "A character created AFTER
        it does not: `create_character` writes none of the three ... so this
        still returns three `vital_column_not_seeded` gaps for every character
        born after the migration -- including every character on a fresh
        install."  Every clause of that is now false.  `create_character`
        writes all three at birth from `persistence_vitals.
        new_character_vitals()` (`COO-DECISION 20260902_0443` point 1), so a
        character born after `007` -- and every character on a fresh install,
        which is where the old sentence bit hardest -- resolves COMPLETE, by
        the same numbers, and this returns no gaps for it.

        A caller can therefore stop branching on when the row was made.  What
        it may still meet is a row written before `006`/`007` by a database
        this project no longer produces, and the `level = 0` case below.

        A THIRD answer exists from `COO-DECISION 20260902_0443` point 4: a row
        holding `level = 0` resolves with a `level_zero_is_not_an_adjudicated_
        level` gap even when all three columns have values.  Named here
        because this docstring used to enumerate "not seeded" as the only
        reason a caller gets gaps back, and a caller who read that and wrote
        `if not gaps` around the seeded case would now be wrong.  A zero level
        can be STORED (`write_typed_attributes` accepts it and `006`'s CHECK
        allows it); it is refused on the way out.

        Raises `KeyError` for a character that does not exist or has been
        soft-deleted, matching `get_character` and `read_typed_attributes`.
        """
        from . import persistence_typed_attrs as typed_attrs
        from . import persistence_vitals as vitals

        columns = list(typed_attrs.TYPED_COLUMNS)
        with self.connect() as db:
            vitals.verify_schema(db)
            row = db.execute(
                f"SELECT {','.join(columns)} FROM characters "
                "WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
        if row is None:
            raise KeyError(character_id)
        return vitals.resolve({c: row[c] for c in columns if row[c] is not None})

    def read_character_vitals_or_none(
        self, character_id: int
    ) -> "persistence_vitals.Vitals | None":
        """This character's `persistence_vitals.Vitals` if the database really
        holds all three and every rule passes, otherwise `None`.  Never a
        substitute number, and never a raise for the ordinary "not seeded
        yet" case a caller would have to remember to catch.

        LANE-DB owns this method (charter `COO-DECISION 20260901_1100`); no
        existing method is touched by it.  It adds nothing to
        `read_character_vitals` except a SHAPE, and the shape is the point:
        the resolution is a two-branch object (`complete` / `gaps`) whose
        numbers come out through `require()`, which RAISES.  A caller that
        must not raise -- a login projection is the case this exists for --
        would otherwise write the try/except itself, and the day someone
        writes `except VitalsError: level = 0` in it, the owner's banned
        guessed zero (`COO-DECISION 20260901_1059`) is back, in the one place
        where zero HP does not mean "unknown" but DEAD.

        WHAT `None` PROTECTS AND WHAT IT DOES NOT, measured rather than
        asserted, because a `pf-adversary` pass measured the earlier sentence
        here ("`None` cannot be added to, compared with `>`, or encoded") and
        found it too strong: `None > 0` does raise, but `None == 0` is False,
        `None != 0` is TRUE, `bool(None)` is False, and `json.dumps` turns it
        into `null`.  So a caller writing `if hp != 0: send_alive_block()`
        takes the ALIVE branch for an unknown HP.  What `None` really buys is
        that the value cannot be arithmetic'd or encoded silently -- not that
        every careless caller is caught.  This repository runs no type
        checker (`.github/workflows/gate-windows.yml` has no mypy, pyright or
        ruff step, checked), so the annotation below documents rather than
        enforces.  A caller that must branch on the REASON should call
        `read_character_vitals` instead and read the gaps: this door throws
        them away by design, and that loss is what not raising costs.
        (Two words this paragraph first used are refused inside a foundation
        module by another lane's guard in
        `tests/test_npc_interaction_wire.py`, which reserves a small
        vocabulary for behaviour this module must not grow.  Caught by the
        full suite, not by this lane's own files.)

        WHAT `None` MEANS AND WHAT IT DOES NOT.  It means "this database does
        not have a usable answer": no vital written at all, a partially
        written row, a stored `level = 0` (`COO-DECISION 20260902_0443`
        point 4 refuses it on the way out), `hp_current > hp_max`, and a zero
        `hp_max`.  Which characters are in that state is NOT written here,
        because it is a fact of today and `COO-DECISION 20260902_0444` is
        already in flight to change it: ask `vitals_seeding_census`.

        THREE THINGS STILL RAISE, and a caller that treats this as "never
        raises" is wrong on all three:

        * `KeyError` for a row that does not exist or has been soft-deleted,
          deliberately -- a caller asking about a character it has just
          selected has a bug rather than a gap, and turning that into `None`
          would hand it a fallback path instead of a traceback.  It inherits
          `read_character_vitals`' behaviour for a `character_id` of the
          wrong TYPE too, which is SQLite's affinity rather than a check.
        * `persistence_vitals.SchemaDriftError` when the database's columns
          and `persistence_typed_attrs` disagree -- `read_character_vitals`
          verifies the whole typed schema, not just three columns, so a
          renamed `speed_walk` raises here even though this method's own
          three columns are intact.  Loud is right for schema drift; it is
          named here because "the door that does not raise" would otherwise
          be a lie a login path discovers in production.
        * `persistence_vitals.VitalsError` for a resolution that reports no
          gaps while holding no values.  See the comment at the return.

        NOTHING IS SENT BY THIS METHOD.  Whether a login block may carry the
        ROW's numbers instead of `player_wire`'s literals is a send question,
        and send questions in this lane belong to COO (the precedent is
        `COO-DECISION 20260902_0742` point 4, which allowed `speed_walk` to be
        STORED and forbade anyone reading it to send it).  This method is the
        store half only.

        NO TEST PINS "nothing calls this", and that is a decision.
        Measured at the commit that added it -- zero call sites in `src/`,
        `tools/`, `scenarios/`,
        `current/` -- and left unpinned ON PURPOSE: the day a login path
        calls it, that call is the wiring this lane asked COO for, and a pin
        would turn another lane's PR red for doing the thing this method
        exists for.  The cost is real and is stated rather than hidden: a
        `pf-adversary` pass wrote a file that calls this door and composes
        `{2: 0, 3: 0, 4: 0}` -- the banned guessed zero, on HP -- and the
        whole suite stayed green.  What DOES fire on that shape is
        `NothingComposesFromThisDoorTests` in
        `tests/test_persistence_vitals_or_none.py`, which catches a file that
        names this door and calls the attribute composer; a hand-rolled
        `u32tag` path is caught by neither, and only review stands there.
        """
        resolution = self.read_character_vitals(character_id)
        if not resolution.complete:
            return None
        # `require()` and not a hand-built `Vitals`: `resolve()` is the only
        # builder of a resolution in SHIPPED code (`src/`, measured -- tests
        # build one by hand deliberately, including the tests for this
        # method), and it cannot report zero gaps with a column missing.  But
        # this method must not be the place that assumption is silently
        # relied on: if a resolution ever arrives complete-but-empty,
        # `require()` raises and that raise travels.  It is not converted
        # into `None`, because `None` here means "the database has no
        # answer" and that case is a BUG, which is a different sentence.
        return resolution.require()

    def vitals_seeding_census(self) -> dict:
        """How many characters in THIS database hold each vital, counted.

        LANE-DB owns this method; no existing method is touched by it.

        It replaces a text parser over `migrations/*.sql` that a
        `pf-adversary` pass defeated seven different ways -- `ADD COLUMN ...
        DEFAULT 100`, a BOM, a CTE, `REPLACE INTO`, a trigger body, `INSERT
        ... SELECT`, a `/* */` comment -- every one of them reporting "nothing
        seeds" while a real database held a seeded value in every row.  The
        parser also answered "nothing seeds" for a directory that did not
        exist, and read the repository's migrations directory rather than the
        one this store was actually built with.

        Counting rows cannot be wrong in that direction: it is the database
        the caller is holding, and a value is there or it is not, whichever
        statement in whichever file put it there.

        EVERY ROW IS COUNTED, soft-deleted ones included, and the two counts
        are reported side by side (`*_seeded_live` and `*_seeded_any`).  The
        first version of this method carried `WHERE deleted_at IS NULL` --
        matching every other read in this lane -- and a `pf-adversary` pass
        showed that a REPORT is not a read: a seeded character that is then
        soft-deleted made it answer `level_seeded: 0` over a row holding
        `level=9` on disk, permanently, because `004_character_soft_delete_
        reuse.sql` keeps those rows.  That is the same wrong answer in the
        same reassuring direction as the text parser this replaced.

        `database` is in the result on purpose: a census number quoted into a
        round file is worth nothing if a reader cannot tell which file it was
        counted from.

        WHAT IT STILL CANNOT TELL YOU, said here rather than discovered
        later: it counts values, not their provenance.  A value a migration
        put there with a blanket `DEFAULT` and a value COO adjudicated are
        the same bytes, and this method cannot distinguish them.  It answers
        "has anything been written", never "was what was written allowed".
        """
        from . import persistence_vitals as vitals

        with self.connect() as db:
            vitals.verify_schema(db)
            row = db.execute(vitals.census_sql()).fetchone()
        census = {key: (0 if row[key] is None else int(row[key]))
                  for key in row.keys()}
        census["database"] = self.path
        return census

    def typed_column_null_audit(self) -> dict:
        """How many rows in THIS database hold NULL in each ADJUDICATED
        column, live and on disk.

        LANE-DB owns this method; no existing method is touched by it.
        Ordered by `COO-DECISION 20260903_1047` point 2, and the caller it
        exists for is named in that decision: COO cannot rule on whether the
        `008` -> `009` cohort needs a backfill without knowing how many rows
        are in it.  A backfill remains FORBIDDEN until the number is seen.

        !! IT GOES THROUGH `connect_read_only`, AND THE FIRST DRAFT WENT
        THROUGH `connect()` WHILE CLAIMING TO WRITE NOTHING.  A
        `pf-adversary` pass measured the difference on a real file: `connect`
        executes `PRAGMA journal_mode=WAL` and commits on exit, so counting a
        rollback-journal database MOVED ITS BYTES (sha256 changed, header
        bytes 18/19 `01 01` -> `02 02`, mtime changed, `data_version` 1 -> 2).
        This method exists to be pointed at the owner's canonical database and
        at snapshots of it, where `AGENTS.md` requires the hash not to move,
        and where the whole point of keeping a snapshot is that reading it
        does not change it.  `connect_read_only` opens `?mode=ro` with
        `PRAGMA query_only=ON`: same ten numbers, zero bytes moved --
        measured, and pinned in `tests/test_persistence_null_audit.py`.

        !! A COUNT THAT COULD NOT BE TAKEN COMES BACK AS `None`, NOT `0`.
        `SUM()` over zero rows is SQL NULL, and an earlier draft coerced
        every value to an int -- which made a database with no characters at
        all print a report line for line identical to a fully seeded one.
        That is `COO-DECISION 20260901_1059`'s banned guessed zero arriving at
        the layer whose output goes into a letter.  `characters_any` is
        `COUNT(*)` and is always an int; every other value -- the per-column
        counts AND `characters_live`, which is a `SUM()` too -- is `int` or
        `None`, and `persistence_null_audit.format_report` prints `None` as
        `not-counted`.

        NOT the vitals seeding census, and the difference is the point.  That
        method counts values PRESENT in the three vitals, whose list lives on
        the write path; this one counts values ABSENT in four columns, the
        fourth being `speed_walk` -- which the census cannot see and must not
        be taught to, because its list is `persistence_vitals.VITAL_COLUMNS`
        and that tuple decides how a character is BORN.  The two numbers are
        not derivable from each other on a database with deleted rows.

        Raises `ValueError` for an in-memory store and `FileNotFoundError`
        for a path that does not exist -- both from `connect_read_only`, and
        both are honest: there is no file to count.
        """
        from . import persistence_null_audit as null_audit
        from . import persistence_vitals as vitals

        with self.connect_read_only() as db:
            vitals.verify_schema(db)
            row = db.execute(null_audit.audit_sql()).fetchone()
        audit = {}
        for key in row.keys():
            value = row[key]
            audit[key] = None if value is None else int(value)
        # `database` travels with the counts for the same reason the census
        # carries it: a number quoted into a letter without the file it was
        # counted from is worth nothing.  RESOLVED, not the string the caller
        # happened to construct the store with, so two operators quoting
        # "state.sqlite3" from two directories cannot look like one file.
        audit["database"] = str(Path(self.path).resolve()) \
            if self.path != ":memory:" else self.path
        return audit

    def apply_hp_damage(self, character_id: int, amount: int):
        """Subtract `amount` from this character's stored `hp_current`, with a
        floor of zero, and return the `persistence_vitals.DamageOutcome`.

        LANE-DB owns this method; no existing method is touched by it.  This
        is the DB half of M4 (`ตีได้ตายได้`): the one place a hit becomes a
        number on disk that survives a logout.

        FAIL-CLOSED ON AN UNSEEDED CHARACTER.  If either HP column has no
        value this raises `persistence_vitals.VitalsError` and writes nothing.
        Treating an absent `hp_current` as `0` would make the first hit on
        every unseeded character kill it -- the owner's banned guessed zero
        (`COO-DECISION 20260901_1059`) arriving as a death rather than as a
        wire field.  Before `migrations/007_character_vitals_seed.sql` that
        meant this method refused for every character on every database.  It
        now succeeds for a character that existed when `007` ran and still
        refuses -- loudly, by design -- for one created afterwards, since
        nothing seeds those (see `read_character_vitals` above).

        The read and the write are ONE transaction on ONE connection
        (`BEGIN IMMEDIATE`).  That line is NOT decoration and the cost of
        losing it is measured, not feared: a `pf-adversary` pass deleted it
        and ran 8 threads x 60 hits of 1 damage at one character -- 232 of
        the 480 hits vanished (hp 99752 instead of 99520) and surfaced as
        `KeyError`, which this method's own contract says means "no such
        character".  A lost hit reported as a missing character is the worst
        shape this method could fail in, so the lock now has TWO tests that
        fail without it, both in `tests/test_persistence_vitals.py`:
        `BeginImmediateHoldsTheWriteLockTests` (the lock is taken before the
        SELECT, measured through an outsider connection) and
        `DamageDoorHasItsOwnShortBudgetTests` (a hit that loses the race
        under a competitor SHORTER than the budget is not lost, measured
        through real threads and a real competing connection).  Note that the
        `BEGIN IMMEDIATE` this paragraph names is no longer spelled inline
        here -- it is opened by `_begin_immediate_for_damage`, so "delete the
        line" below means that call, and deleting it leaves a DEFERRED
        transaction exactly as before.

        The `UPDATE` also carries `hp_current=?` for the value it read.  An
        earlier draft of this docstring said no test could be made to fail by
        deleting that predicate.  That was true when it was written and is
        false now: `test_a_lost_write_would_not_be_reported_as_a_missing_
        character`, added in the same round thirty lines further down the
        test file, forces the predicate to miss and dies without it.  The
        sentence outlived the suite it described -- corrected here rather
        than left standing, since an under-claim is still a claim nobody
        re-derived.  What the predicate buys: if the guarded UPDATE matches
        nothing, this method says the write did not land instead of blaming a
        missing character.

        The new value goes out through `persistence_typed_attrs.validate` on
        the way in (inside `write_typed_attributes`' rules) so a number this
        schema may not hold cannot be reached by arithmetic either.

        Raises `KeyError` for a character that does not exist or is
        soft-deleted, and `persistence_vitals.VitalsError` for an unseeded or
        inconsistent character, or for an amount that is not a whole number of
        points of damage.  Nothing is written when anything is refused.

        ALSO RAISES `store.WriteLockTimeout`, AND ALSO BLOCKS, SINCE
        2026-09-03, and this paragraph is the notice.  This method opens its
        transaction through `_begin_immediate_for_damage`, so a refused write
        lock is waited out, briefly, rather than raised at once.  What a
        caller must plan for:

        * this call can BLOCK for up to `DAMAGE_LOCK_BUSY_TIMEOUT_MS`
          (3000 ms today) before it gives up, where before
          `COO-DECISION 20260903_1047` it gave up at `connect()`'s 5,000 ms;
        * there is exactly ONE attempt, not a retry loop -- unlike the
          healing doors below, a lock still held when the budget above is
          spent raises immediately, it does not sleep and try `BEGIN
          IMMEDIATE` again;
        * on giving up it raises `WriteLockTimeout`, which SUBCLASSES
          `sqlite3.OperationalError`, so an `except OperationalError` still
          catches it and the type is not a break -- the waiting is;
        * giving up ALSO prints `DAMAGE_WRITE_LOCK_REFUSED_TOKEN` to stdout
          first, so a lost hit is visible on the console even if a caller
          catches and swallows the exception.

        !! `HEAL_LOCK_TOTAL_WAIT_S` (120 s) IS NOT THIS DOOR'S BUDGET, AND
        NEVER WAS FOR MORE THAN ONE ROUND.  `COO-DECISION 20260903_1047`
        point 1 briefly put this method behind the healing doors' shared
        120 s / 30,000 ms budget; `pf_bridge/FINDINGS_R18_SERVER_IS_
        STRICTLY_SERIAL.md` measured this server as strictly serial, one
        client per listener, so a hit that waits two minutes is a two-minute
        freeze of every other player -- the question of what THIS door's own
        budget should be went to COO in LANE-DB round `r53lc8`, and
        `COO-DECISION 20260903_1248` answered it: a separate, short,
        non-looping budget, `DAMAGE_LOCK_BUSY_TIMEOUT_MS` above.  !! THAT
        NUMBER IS A SAFETY CEILING, NOT A MEASURED RESULT -- see the
        constant's own comment for why, and do not read "3000 ms" as
        anything combat's real hit rate has been checked against yet.

        "INCONSISTENT" WIDENED on 2026-09-02 and this sentence is the notice.
        `COO-DECISION 20260902_0443` point 4 made a stored `level = 0` a
        refusal, and this method resolves the whole vitals state before it
        subtracts anything -- so a row at `level = 0` holding a perfectly
        valid `hp 100/100` now refuses damage and writes nothing.  It is a
        deliberate tightening (that row's level is a number nobody
        adjudicated), but a caller cannot learn it from `persistence_vitals`
        without opening it, and this is where a caller of the store method
        reads.
        """
        from . import persistence_typed_attrs as typed_attrs
        from . import persistence_vitals as vitals

        columns = list(typed_attrs.TYPED_COLUMNS)
        with self.connect() as db:
            # WAS `db.execute("BEGIN IMMEDIATE")` until `COO-DECISION
            # 20260903_1047` point 1 (which briefly routed this door through
            # `_begin_immediate_under_contention`, the healing doors' shared
            # helper), and IS `_begin_immediate_for_damage` since
            # `COO-DECISION 20260903_1248`, which gave this door its own
            # budget instead.  The TRANSACTION shape is unchanged either way
            # -- it is still an IMMEDIATE one -- what changes is how a
            # refused `BEGIN IMMEDIATE` is handled:
            #
            # !! THREE THINGS CHANGE FOR THIS METHOD, versus a bare
            # `db.execute("BEGIN IMMEDIATE")`:
            #   * `PRAGMA busy_timeout` goes to `DAMAGE_LOCK_BUSY_TIMEOUT_MS`
            #     (3000 ms) for this one `BEGIN IMMEDIATE` call, in place of
            #     `connect()`'s 5,000 ms -- SHORTER, on purpose, not longer;
            #     see the constant's own comment for why 3000 and not 5000.
            #   * a lock still refused after that budget raises
            #     `WriteLockTimeout` instead of a bare
            #     `sqlite3.OperationalError('database is locked')`.
            #   * that same refusal ALSO prints `DAMAGE_WRITE_LOCK_REFUSED_
            #     TOKEN` to stdout before it raises.
            # All three are in the `Raises` paragraph above, where a caller
            # reads.  There is deliberately NO Python-level retry loop here
            # -- `COO-DECISION 20260903_1248` forbids one by name for this
            # door -- so unlike the healing doors' helper, this call cannot
            # sleep and try `BEGIN IMMEDIATE` a second time.
            self._begin_immediate_for_damage(db, character_id)
            vitals.verify_schema(db)
            row = db.execute(
                f"SELECT {','.join(columns)} FROM characters "
                "WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(character_id)
            stored = {c: row[c] for c in columns if row[c] is not None}
            current = vitals.resolve(stored).require()
            outcome = vitals.apply_damage(
                current.hp_current, current.hp_max, amount)
            if outcome.hp_after != outcome.hp_before:
                # `deleted_at IS NULL` is repeated from the SELECT above on
                # purpose, the same doubling `write_typed_attributes` carries
                # and for the same reason: removing EITHER one alone cannot
                # land a write where the API says it cannot.  Measured: each
                # alone leaves the suite green, removing both is caught.
                # `validate` on the stored value is belt-and-braces too --
                # `hp_after` is an int inside the range by construction, so
                # no test can fail on its removal.  Both are written down as
                # structural rather than counted as evidence.
                written = db.execute(
                    "UPDATE characters SET hp_current=?,updated_at=? "
                    "WHERE id=? AND deleted_at IS NULL AND hp_current=?",
                    (
                        typed_attrs.validate(
                            vitals.HP_CURRENT_COLUMN, outcome.hp_after),
                        _now(), character_id, outcome.hp_before,
                    ),
                ).rowcount
                if written != 1:
                    still_there = db.execute(
                        "SELECT hp_current FROM characters "
                        "WHERE id=? AND deleted_at IS NULL",
                        (character_id,),
                    ).fetchone()
                    # ONE branch, not two.  A first draft split this into
                    # `KeyError` when the row had vanished and `VitalsError`
                    # otherwise; a `pf-adversary` pass showed the KeyError
                    # half is unreachable by construction -- under
                    # `BEGIN IMMEDIATE`, on this connection, between this
                    # UPDATE and this SELECT, the row cannot disappear --
                    # and deleting it left every test green.  Either way the
                    # honest report is the same: the write did not land.
                    # Saying `KeyError` here would tell a caller the
                    # character is gone, which is the lie worth avoiding.
                    raise vitals.VitalsError(
                        "the guarded write matched no row (read hp_current="
                        "%r, row now %r): the damage was NOT applied"
                        % (outcome.hp_before,
                           None if still_there is None
                           else still_there["hp_current"])
                    )
        return outcome

    @staticmethod
    def _begin_immediate_under_contention(db):
        """`BEGIN IMMEDIATE`, kept waiting instead of allowed to starve.

        ONE CALLER AGAIN AS OF `COO-DECISION 20260903_1248`, and the prose
        below still says "healing" because that is what is true now, not
        because it was never touched.  For one round (`COO-DECISION
        20260903_1047` point 1, 2026-09-03) `apply_hp_damage` was ALSO put
        behind this helper, sharing `HEAL_LOCK_TOTAL_WAIT_S` (120 s) and
        `HEAL_LOCK_BUSY_TIMEOUT_MS` (30 s) with the two healing doors below.
        `20260903_1248` reversed that: the damage door gets its own short,
        non-looping budget instead (`DAMAGE_LOCK_BUSY_TIMEOUT_MS`, see
        `_begin_immediate_for_damage`), because `FINDINGS_R18` measured this
        server as strictly serial and a hit that waits up to 120 s is a
        two-minute freeze of every other player, not a budget "nobody is
        using yet".  `apply_hp_damage` calls `_begin_immediate_for_damage`
        now, not this method -- read every "heal" below as exactly that
        again, with no second door hiding behind the word.

        WHAT IT IS FOR.  `COO-DECISION 20260902_1646` -- and the measurement
        behind it in `pf_bridge/notes_to_chief/20260902_1642_LANE-B-TO-LANE-DB-*`
        -- named the defect: the healing lock is correct and the test that
        proves it was losing on TIME on a loaded runner, taking another lane's
        pull request down with it.  Four repairs were forbidden by name
        (weakening or removing `BEGIN IMMEDIATE`, shrinking the test's thread
        or heal counts, skipping or xfailing it, and any green that comes
        without a test proving no heal is lost or double-counted).  This is
        the fifth: tolerate contention.

        WHY RETRYING HERE CANNOT DOUBLE-APPLY A HEAL, which is the only reason
        a retry is safe at all.  The only statement retried is `BEGIN
        IMMEDIATE` itself, and only when SQLite refused it with
        `database is locked`.  A refused `BEGIN IMMEDIATE` has opened no
        transaction, so the read, the plan and the guarded `UPDATE` above have
        not run and there is nothing to repeat.  A lock lost or an error
        raised at any LATER statement is not retried by this method at all --
        it propagates, and the caller's `connect()` rolls back.  The
        write-once property therefore rests where it always rested: on
        `BEGIN IMMEDIATE` plus the `hp_current=?` predicate in the UPDATE.

        Raises `WriteLockTimeout` when the budget is spent, saying how long it
        waited and how many attempts it made -- the thing a bare
        `database is locked` never said, and the reason a reader of a red gate
        could not tell contention from a real defect.
        """
        started = time.monotonic()
        deadline = started + HEAL_LOCK_TOTAL_WAIT_S
        attempts = 0
        while True:
            attempts += 1
            # PER ATTEMPT, and never longer than the budget has left: SQLite
            # blocks inside `BEGIN IMMEDIATE` for the whole ceiling, so a
            # ceiling larger than the remaining budget would be spent past the
            # deadline before this loop could look at the clock again.  The
            # pragma stays in force for the rest of this connection's
            # statements too (the SELECT, the UPDATE, the COMMIT); that is a
            # wider effect than the name suggests and it is deliberate --
            # those statements are inside the same contended transaction.
            ceiling = min(
                HEAL_LOCK_BUSY_TIMEOUT_MS,
                max(1, int((deadline - time.monotonic()) * 1000.0)),
            )
            try:
                db.execute("PRAGMA busy_timeout=%d" % ceiling)
            except sqlite3.Error:
                # A connection that will not accept the pragma still gets its
                # attempts; it just makes them at whatever timeout it has.
                # `COO-DECISION 20260903_1248` point 4: count and print
                # instead of a silent `pass` -- landed in the same commit as
                # `_begin_immediate_for_damage`'s own copy of this fix below.
                _note_pragma_busy_timeout_refused("heal", ceiling)
            try:
                db.execute("BEGIN IMMEDIATE")
                return attempts
            except sqlite3.OperationalError as error:
                if _LOCKED not in str(error):
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WriteLockTimeout(
                        # SAID "healing" UNTIL 2026-09-03, AND THE DAMAGE
                        # DOOR MADE IT A LIE.  A `pf-adversary` pass ran the
                        # timeout through `apply_hp_damage` and read back
                        # "could not take the write lock for this
                        # character's healing" over a LOST HIT, briefly, while
                        # `apply_hp_damage` shared this helper too (see the
                        # method docstring above) -- the same shape this
                        # method's own docstring argues against for
                        # `KeyError`: an operator reading a red gate walks to
                        # the login-revive path for a defect in a different
                        # door.  "write" stays the word here even now that
                        # this door is heal-only again, so the sentence does
                        # not have to change back and forth with who is
                        # calling.
                        "could not take the write lock for this character's "
                        "write after %d attempt(s) over %.0f ms (budget "
                        "%.0f ms, per-attempt busy_timeout at most %d ms): %s"
                        % (attempts, (time.monotonic() - started) * 1000.0,
                           HEAL_LOCK_TOTAL_WAIT_S * 1000.0,
                           HEAL_LOCK_BUSY_TIMEOUT_MS, error)
                    ) from error
                window = HEAL_LOCK_RETRY_BACKOFF_S * (2 ** min(attempts, 5))
                time.sleep(min(random.random() * window, remaining))

    @staticmethod
    def _begin_immediate_for_damage(db, character_id):
        """`BEGIN IMMEDIATE` for `apply_hp_damage` ONLY, on a short budget
        this door does not share with the healing doors, and with NO
        Python-level retry loop -- `COO-DECISION 20260903_1248`, answering
        the open question `apply_hp_damage`'s own docstring sent to COO in
        LANE-DB round `r53lc8`.

        ONE ATTEMPT, NOT A LOOP.  Unlike `_begin_immediate_under_contention`
        above, this method does not catch a refused `BEGIN IMMEDIATE`, sleep,
        and try again -- COO's decision says so by name ("ห้ามวนรีทราย", no
        loop-retry).  The waiting a caller sees still happens, but it happens
        INSIDE SQLite's own busy handler, for up to
        `DAMAGE_LOCK_BUSY_TIMEOUT_MS` (3000 ms today), because that is what
        `PRAGMA busy_timeout` does to a single `execute("BEGIN IMMEDIATE")`
        call -- there is nothing here for a Python-level loop to add.  A
        thread that is still locked out after that one call gives up.

        !! `DAMAGE_LOCK_BUSY_TIMEOUT_MS` IS A SAFETY CEILING, NOT A MEASURED
        RESULT -- repeated here, not only on the constant, because a reader
        who lands on this method first should not have to go and find that
        out.  See the constant's own comment for why and for what would
        replace it.

        ON REFUSAL: print `DAMAGE_WRITE_LOCK_REFUSED_TOKEN` to stdout, THEN
        raise `WriteLockTimeout`.  Both, in that order, every time -- COO's
        decision ("ปฏิเสธการเขียนพร้อมบรรทัดคอนโซล ... ห้ามเงียบ", refuse the
        write WITH a console line, no silence) reads as a requirement on the
        refusal itself, not only on whatever the caller does with the
        exception; a caller that swallows `WriteLockTimeout` would otherwise
        make a lost hit invisible end to end.  Nothing is written before this
        raises: same as `_begin_immediate_under_contention`, a refused `BEGIN
        IMMEDIATE` opens no transaction, so there is nothing to roll back.
        """
        try:
            db.execute("PRAGMA busy_timeout=%d" % DAMAGE_LOCK_BUSY_TIMEOUT_MS)
        except sqlite3.Error:
            # `COO-DECISION 20260903_1248` point 4: count and print instead
            # of a silent `pass` -- mirrors `_begin_immediate_under_
            # contention`'s own copy of this fix above, landed in the same
            # commit.
            _note_pragma_busy_timeout_refused(
                "damage", DAMAGE_LOCK_BUSY_TIMEOUT_MS)
        started = time.monotonic()
        try:
            db.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as error:
            if _LOCKED not in str(error):
                raise
            waited_ms = (time.monotonic() - started) * 1000.0
            print("%s character=%s waited_ms=%.0f budget_ms=%d" % (
                DAMAGE_WRITE_LOCK_REFUSED_TOKEN, character_id, waited_ms,
                DAMAGE_LOCK_BUSY_TIMEOUT_MS))
            raise WriteLockTimeout(
                "could not take the write lock for this character's write "
                "after 1 attempt over %.0f ms (budget %d ms, no retry loop "
                "-- COO-DECISION 20260903_1248): %s"
                % (waited_ms, DAMAGE_LOCK_BUSY_TIMEOUT_MS, error)
            ) from error

    def _apply_hp_transition(self, character_id: int, plan):
        """The shared transactional body of the two HEALING doors below.

        `plan(vitals_module, current)` returns an outcome carrying
        `hp_before`, `hp_after` and the rest; this method does the reading,
        the locking, the guarded write and the honest report, once.

        `apply_hp_damage` above is DELIBERATELY NOT refactored onto this
        helper.  It is an existing method with an existing contract and
        LANE-DB's charter forbids this lane from changing the behaviour of
        one; a shared body would put every future edit to the heal path
        inside the damage path too.  The duplication is the cheaper of the
        two mistakes and it is written down rather than left to be
        discovered.

        THE SHAPE IS `apply_hp_damage`'s, AND WHICH PARTS OF IT ARE MEASURED
        HERE IS SPELT OUT RATHER THAN INHERITED.  An earlier draft of this
        docstring said the four items below hold "for the same measured
        reasons" as the damage path; a `pf-adversary` pass showed that
        borrowed a measurement made on a different method and promoted two
        items the cited docstring explicitly labels NOT evidence.  What is
        true of THIS body, each checked by deleting it and watching this
        lane's own file go red or stay green:

        * ONE transaction on ONE connection (`BEGIN IMMEDIATE`) so a
          concurrent heal cannot be lost and then reported as a missing
          character -- MEASURED (`BeginImmediateHoldsTheHealLockTests`;
          `BEGIN` and `BEGIN DEFERRED` also fail it).
        * `persistence_vitals.verify_schema` before the read, so a drifted
          schema is named instead of producing a confusing miss -- MEASURED
          (`SchemaDriftReachesTheHealDoorsTests`).
        * The read value repeated as `hp_current=?` in the UPDATE's
          predicate, so a write that does not land says the healing was not
          applied instead of blaming a missing row -- MEASURED
          (`test_a_lost_heal_is_reported_as_a_lost_heal`), which also
          executes the `written != 1` branch; without that test the branch
          had never run once in this repository.
        * `deleted_at IS NULL` doubled in the UPDATE, and
          `persistence_typed_attrs.validate` on the way in -- STRUCTURAL, NOT
          EVIDENCE.  Neither can be made to fail a test: the SELECT above
          already carries the same predicate, and `hp_after` is an int inside
          the column's range by construction.  They are written down as
          belt-and-braces, exactly as `apply_hp_damage`'s own comment writes
          down the same two, and nobody should cite them as measured.

        FAIL-CLOSED ON AN UNSEEDED CHARACTER, exactly as damage is: a row
        with no `hp_current` is refused rather than healed from a guessed
        zero.  Guessing zero here would be the owner's banned guess
        (`COO-DECISION 20260901_1059`) arriving as a RESURRECTION -- a
        character whose HP nobody knows would come back at full.

        Raises `KeyError` for a character that does not exist or is
        soft-deleted, and `persistence_vitals.VitalsError` for an unseeded or
        inconsistent character -- and, on the paths that TAKE an amount, for
        an amount that is not a whole number of points (`restore_hp_to_full`
        has no amount to refuse).  Nothing is written when anything is
        refused.
        """
        from . import persistence_typed_attrs as typed_attrs
        from . import persistence_vitals as vitals

        columns = list(typed_attrs.TYPED_COLUMNS)
        with self.connect() as db:
            self._begin_immediate_under_contention(db)
            vitals.verify_schema(db)
            row = db.execute(
                f"SELECT {','.join(columns)} FROM characters "
                "WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(character_id)
            stored = {c: row[c] for c in columns if row[c] is not None}
            current = vitals.resolve(stored).require()
            outcome = plan(vitals, current)
            if outcome.hp_after != outcome.hp_before:
                written = db.execute(
                    "UPDATE characters SET hp_current=?,updated_at=? "
                    "WHERE id=? AND deleted_at IS NULL AND hp_current=?",
                    (
                        typed_attrs.validate(
                            vitals.HP_CURRENT_COLUMN, outcome.hp_after),
                        _now(), character_id, outcome.hp_before,
                    ),
                ).rowcount
                if written != 1:
                    still_there = db.execute(
                        "SELECT hp_current FROM characters "
                        "WHERE id=? AND deleted_at IS NULL",
                        (character_id,),
                    ).fetchone()
                    raise vitals.VitalsError(
                        "the guarded write matched no row (read hp_current="
                        "%r, row now %r): the healing was NOT applied"
                        % (outcome.hp_before,
                           None if still_there is None
                           else still_there["hp_current"])
                    )
        return outcome

    def apply_hp_heal(self, character_id: int, amount: int):
        """Add `amount` to this character's stored `hp_current`, with a
        ceiling of `hp_max`, and return the `persistence_vitals.HealOutcome`.

        LANE-DB owns this method; no existing method is touched by it.  It is
        the other half of M4's `ตีได้ตายได้` on disk: `apply_hp_damage` can
        already take a character's HP down and nothing could put it back, so
        the first call site that needed to (a potion, a rest, a respawn)
        would have had to write its own `UPDATE characters SET hp_current`
        past every rule in `persistence_vitals`.

        WHAT IT DOES NOT DECIDE.  Whether a character at zero may be healed
        at all is LANE-B's rule; this method APPLIES the heal and reports
        `revived` so that the caller's rule is visible in its own code rather
        than hidden in a refusal here.

        Same raises as `apply_hp_damage`, and nothing is written when
        anything is refused.
        """
        return self._apply_hp_transition(
            character_id,
            lambda vitals, current: vitals.apply_heal(
                current.hp_current, current.hp_max, amount),
        )

    def restore_hp_to_full(self, character_id: int):
        """Heal this character's whole missing bar and return the
        `persistence_vitals.HealOutcome` -- the respawn arithmetic, named
        once so no call site writes `hp_max - hp_current` itself.

        `hp_max` is read from the ROW inside the same transaction as the
        write, so "full" means this character's own maximum and never a
        number a caller passed in.  On a character already at full nothing is
        written and the outcome reports `was_already_full`.

        It does NOT claim that respawn IS a full heal: that is a game rule
        LANE-B and the owner own.  This is the door for one.
        """
        return self._apply_hp_transition(
            character_id,
            lambda vitals, current: vitals.heal_to_full(
                current.hp_current, current.hp_max),
        )

    def write_speed_by_identity(
        self, identity_lo: int, identity_hi: int, speed: float
    ) -> "dict[int, float] | None":
        """Store `speed` on the ACTIVE character carrying this wire identity
        pair, and hand back `{x: value}` taken from the row READ BACK inside
        the same transaction -- or `None`, which means NOTHING WAS WRITTEN.

        LANE-DB owns this method (charter `COO-DECISION 20260901_1100`: a new
        method here is allowed, changing an old one is not); no existing
        method is touched by it.  It is the door LANE-GM asked for in
        `pf_bridge/notes_to_chief/20260902_0017_LANE-GM-TO-LANE-DB-request-
        speed-persistence-method.md`, built to that letter's shape, and the
        answer this lane sent back in `20260903_0525` is the contract below.

        WHY IT TAKES AN IDENTITY PAIR AND NOT A `character_id`.  The asking
        lane holds `identity_lo`/`identity_hi` from `session.foundation.
        selected` and no row id at all; making it reverse-engineer the
        `characters` schema from `gm/` is how a second, private idea of this
        table gets built.  The lookup is `deleted_at IS NULL`, which is
        exactly the predicate `migrations/004`'s partial unique index
        `characters_active_identity` is built on, so at most one row can
        match; two matching rows are refused rather than picked between.

        `None` IS THE ONLY FAILURE REPORT, AND IT IS AN HONEST ONE.  Every
        refusal below raises INSIDE `connect()`'s block, so the transaction
        is rolled back before this method returns: `None` therefore means the
        row is exactly as it was, never "written, then something went wrong".
        That is the property to test, and
        `tests/test_store_speed_by_identity.py` tests it on every branch.
        What earns `None`:

        * an identity part that is not an `int`, is a `bool`, or is outside
          `[0, 0xFFFFFFFF]`.  `bool` matters more than it looks and is
          MEASURED: SQLite binds `True` as `1`, so an unguarded
          `identity_lo=True` finds and writes the character whose identity
          really is `1`, and the test builds that character.  The RANGE half
          is belt-and-braces and is not evidence: a negative or oversized
          part matches no row anyway (`2**128` never reaches SQLite at all),
          so removing it leaves every test green.  It is written down as
          structural, exactly as `_apply_hp_transition`'s own doubled
          predicates are, and nobody should cite it as measured.

        THE REST OF THE STRUCTURAL LIST, because an earlier draft declared
        only one item and then claimed this door is tested "on every branch".
        A `pf-adversary` pass (D4) measured seven more mutants that survive
        the whole file, and hiding them is worse than owning them.  Still
        unkillable today, and each is belt-and-braces behind something that
        IS measured: `AND deleted_at IS NULL` in the UPDATE (the lookup's own
        predicate plus the write lock already cover it); the `after is None`
        branch (removing it turns into the same rolled-back `None` through
        `TypeError`); `type(stored) is not float` inside the read-back guard;
        `written != 1` narrowed to `written < 1`; composing before the commit
        rather than after it.  Two more were killable and are now killed
        rather than declared -- `LIMIT 2` / `len(rows) != 1` (see
        `TwoActiveRowsAreRefusedTests`, which builds by hand the state
        `migrations/004`'s partial unique index makes unconstructible through
        this API) and the transaction's `BEGIN IMMEDIATE` itself (see
        `TheReadAndTheWriteAreOneTransactionTests`).
        * no active character with that pair (including one soft-deleted
          between the caller reading it and this call).
        * a value `persistence_typed_attrs.validate` refuses for this column
          -- a bool, a non-number, `NaN`/`inf`, outside the f32 range, or a
          nonzero value that underflows to exactly `0.0` on the wire.
        * the write matching no row, or the read-back not being the number
          just validated.
        * a locked database, and a schema this database does not have.  Both
          are indistinguishable from a refusal HERE, by design -- this door
          may not raise across `gm/`'s boundary -- so a caller that needs the
          REASON must use `write_typed_attributes`, which names it.

        WHAT COMES BACK IS THE ROW'S NUMBER, AND IT IS A SOURCE RATHER THAN
        A FORMALITY -- CORRECTED HERE, BECAUSE THIS DOCSTRING SAID THE
        OPPOSITE AND WAS WRONG.  The read-back happens inside the same
        transaction as the write (the shape `write_typed_attributes` adopted
        after an adversary pass measured a commit-then-read returning another
        writer's value as "the state after this write"), and `COO-DECISION
        20260903_0447` point 2 made that a house rule rather than a
        preference: a module claiming wire == DB must send the value it read
        back, and "the write did not throw" is not evidence that a row
        changed.  An earlier draft then reasoned that the mismatch check
        below makes `stored` and `checked` "equal by construction", so
        composing from either could not be told apart -- and declared that
        undetectability MEASURED.  A `pf-adversary` pass (D1) refuted it with
        one input: `-0.0`.  `validate` keeps the sign (`as_f32` does), SQLite
        normalises it away on the way into a REAL column, and `-0.0 == 0.0`
        is True -- so the guard passes while the two values differ, and they
        differ in the sign BIT: `struct.pack("<f", 0.0)` is `00000000` and
        `-0.0` is `00000080`, four different bytes on the wire.  Composing
        from `checked` would send a number this database does not hold, which
        is the exact wire-vs-DB split the house rule exists to forbid.
        `NegativeZeroIsTheRowsZeroTests` pins it.

        THE `written != 1` CHECK, AND THE WRONG REASON THIS DOCSTRING GAVE
        FOR IT.  It used to say that a row already holding the value makes
        the read-back agree while the UPDATE landed nowhere.  That is FALSE
        about SQLite and the same pass measured it: `rowcount` counts rows
        MATCHED, not rows whose bytes changed, so re-writing the same value
        gives `1` and the door correctly reports a write.  What the check
        really catches is an UPDATE that matched NO row -- a `BEFORE UPDATE
        ... RAISE(IGNORE)` trigger is the reachable case, and it is what the
        test uses.  Both directions are pinned all the same: `None` means
        nothing was written, a dict means something was.

        THE LOCK DISCIPLINE IS `write_typed_attributes`', NOT THE HEALING
        DOOR'S, and the difference is deliberate.  `_begin_immediate_under_
        contention` waits up to `HEAL_LOCK_TOTAL_WAIT_S` (120 s) for the
        lock; this server is strictly serial (`pf_bridge/FINDINGS_R18_
        SERVER_IS_STRICTLY_SERIAL.md`), so a chat command that stalls the
        whole world for two minutes is worse than one that is refused and can
        be typed again.  A plain `BEGIN IMMEDIATE` under `connect()`'s
        `busy_timeout=5000` is what this door uses, and a lock it cannot get
        inside that comes back as `None`.

        NOTHING IS SENT BY THIS METHOD, and the returned dict is not a block.
        It is keyed by the wire field index so the caller does not have to
        map column names, but a caller that wants to SEND it must still go
        through `persistence_attr_compose.compose_sparse_block` (or
        `write_typed_attributes_and_compose_sparse`, which composes what it
        writes).  `COO-DECISION 20260902_2147` stands over the send side:
        neither `/speed` lock may be released until the attended round that
        tries a safe value has happened and has a result.  This door does not
        release either one -- it is a store method with no caller.
        """
        try:
            # INSIDE the `try`, and that is a fix rather than a style: this
            # module does not import `persistence_typed_attrs` at module
            # level (the house pattern for the circular import), so the first
            # call in a process really runs that module's body -- and
            # `_build()` there RAISES `TypedAttrError` for a wire kind with
            # no storage rule, an unsafe column name, or a duplicate one.
            # With this line above the `try`, the first `/speed` of a session
            # killed the caller's thread with the very drift this door
            # promises to report as `None`.  Measured by a `pf-adversary`
            # pass (D3), which also verified the one-line fix.
            from . import persistence_typed_attrs as typed_attrs

            column = typed_attrs.column_for(SPEED_WALK_FIELD_X)
            checked = typed_attrs.validate(column, speed)
            pair = (
                _require_identity_part(identity_lo),
                _require_identity_part(identity_hi),
            )
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                rows = db.execute(
                    "SELECT id FROM characters "
                    "WHERE identity_lo=? AND identity_hi=? AND deleted_at IS NULL "
                    "LIMIT 2",
                    pair,
                ).fetchall()
                if len(rows) != 1:
                    raise _SpeedWriteRefused(
                        f"identity {pair} matched {len(rows)} active characters"
                    )
                character_id = int(rows[0]["id"])
                written = db.execute(
                    f"UPDATE characters SET {column}=?,updated_at=? "
                    "WHERE id=? AND deleted_at IS NULL",
                    (checked, _now(), character_id),
                ).rowcount
                if written != 1:
                    raise _SpeedWriteRefused(
                        f"the write matched {written} rows, not 1"
                    )
                after = db.execute(
                    f"SELECT {column} FROM characters WHERE id=?",
                    (character_id,),
                ).fetchone()
                if after is None:
                    raise _SpeedWriteRefused("the row was gone at read-back")
                stored = after[column]
                if type(stored) is not float or stored != checked:
                    raise _SpeedWriteRefused(
                        f"read back {stored!r}, wrote {checked!r}"
                    )
                # `typed_values_for_compose` and not `{SPEED_WALK_FIELD_X:
                # stored}`: it re-validates on the way out and it derives the
                # key from the column table.  Both halves are honest about
                # their worth -- a `pf-adversary` pass (D9) showed the
                # literal-keyed mutant survives every test here, and a column
                # RENAME would not distinguish them either, since a rename
                # changes the column name and never `x`.  What this call
                # really buys is that the key and the value come from the
                # same table as the write did; the earlier comment here
                # claimed rename-safety it cannot deliver.
                composed = typed_attrs.typed_values_for_compose({column: stored})
            return composed
        except Exception:
            # Deliberately wide, and deliberately not `BaseException`.  The
            # asking lane's letter asked for a door that never raises across
            # its boundary, and a store method that raises into a chat
            # command handler is how one bad `/speed` kills the listener
            # thread.  `KeyboardInterrupt` and `SystemExit` are not caught.
            return None

    def commit_ground_drop(
        self,
        scene: str,
        drop_key: int,
        item_id: int,
        quantity: int,
        x: float,
        y: float,
        z: float,
        mob_identity: int,
        killer_identity: int,
    ) -> GroundDropRow:
        """Persist one dropped item on the ground, and read it straight back.

        Round `5d02mu`, `COO-DECISION 20260903_1843`.  This is the write
        half of the ground-drop door: `migrations/010_ground_drops.sql`
        gives the bare table, this method is the only thing in the
        codebase that puts a row in it, and `list_ground_drops_for_scene`
        below is the read half.  THE SCOPE IS EXACTLY "WRITE, THEN READ IT
        BACK" -- `COO-DECISION 20260903_1843` point 5, echoing letter
        `20260903_1740` question (c)-3 -- nothing here deletes a row,
        expires one, or decides what "still on the ground" means once a
        pickup exists; that is a later round's question.

        NOT SESSION-OWNED, ON PURPOSE.  Unlike `commit_acquired_backpack_
        item`, this method takes no `sid` and checks no session ownership:
        a ground drop is world state for a SCENE, not a character's own
        row, and `mob_loot.GroundDrop` (the in-memory object this table's
        columns mirror) carries no session or account field either.

        WHO VALIDATES WHAT.  This lane's charter (`COO-DECISION
        20260901_1100`) keeps `mob_loot.py` -- and the `GroundDrop`
        construction checks it already runs (the f32-grid check on `x`/`y`/
        `z`, the drop-key lane-block range, the known-item check) --
        entirely LANE-B's.  This method does not import `mob_loot` and does
        not repeat those checks; the guards below are the table's OWN
        floor, the same shape `save_position` uses for its own columns
        (`math.isfinite`, explicit range checks) rather than a copy of
        another lane's rules.

        THE COLLISION IS THE POINT.  `ground_drops` carries `UNIQUE(scene_
        fold, drop_key)` (see the migration for why the folded column and
        not the raw one).  Two callers minting the same `drop_key` for the
        same scene is refused here as a `ValueError`, loudly -- printing
        `GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN` first, the same shape
        `_begin_immediate_for_damage` already uses for a different door's
        refusal -- rather than the second write silently overwriting the
        first or the two merging.  `COO-DECISION 20260903_1843` point 4 is
        explicit that the server-wide `drop_key` issuer needed to make this
        never happen in practice is LANE-B's, not built as of this round
        (`20260903_1844`); this door's job is only to make a collision loud
        if one ever reaches it, not to prevent one from being minted.
        """
        scene = _require_ground_drop_scene(scene)
        if isinstance(drop_key, bool) or not isinstance(drop_key, int):
            raise TypeError("drop_key must be an int")
        if not 0 <= drop_key <= 0xFFFFFFFF:
            raise ValueError(
                "drop_key 0x%X is outside the u32 range" % drop_key
            )
        if isinstance(item_id, bool) or not isinstance(item_id, int):
            raise TypeError("item_id must be an int")
        if not 1 <= item_id <= 0xFFFFFFFF:
            raise ValueError("item_id %d is not a positive u32" % item_id)
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise TypeError("quantity must be an int")
        if not 1 <= quantity <= 0xFFFF:
            raise ValueError("quantity %d is not a pickup quantity" % quantity)
        for label, value in (("x", x), ("y", y), ("z", z)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("%s must be a number" % label)
            if not math.isfinite(value):
                raise ValueError("%s must be finite" % label)
        for label, value in (
            ("mob_identity", mob_identity), ("killer_identity", killer_identity),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("%s must be an int" % label)
            if not 0 <= value <= 0xFFFFFFFF:
                raise ValueError(
                    "%s %d is outside the u32 range" % (label, value)
                )
        scene_fold = scene.casefold()
        created_at = _now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                cursor = db.execute(
                    "INSERT INTO ground_drops("
                    "scene,scene_fold,drop_key,item_id,quantity,x,y,z,"
                    "mob_identity,killer_identity,created_at"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        scene, scene_fold, drop_key, item_id, quantity,
                        float(x), float(y), float(z),
                        mob_identity, killer_identity, created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                # NARROWED TO THE UNIQUE VIOLATION ON PURPOSE (`pf-adversary`,
                # round `5d02mu`): `sqlite3.IntegrityError` also covers a CHECK
                # or NOT NULL failure, and an earlier draft of this handler
                # caught all of them, printed the collision token, and raised
                # the collision message for EVERY one -- demonstrated live by
                # disabling one Python-side validator and watching a bad
                # `quantity` get diagnosed as "already on the ground".  Only
                # the constraint this method's own collision guard exists for
                # is reported as a collision; anything else re-raises as
                # itself, which is the CHECK backstop's own message rather
                # than a misleading one this method invented.
                if "UNIQUE constraint failed" not in str(exc):
                    raise
                print(
                    "%s scene=%r drop_key=0x%X"
                    % (GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN, scene, drop_key)
                )
                raise ValueError(
                    "drop_key 0x%X already on the ground in scene %r"
                    % (drop_key, scene)
                ) from exc
            row_id = cursor.lastrowid
            row = db.execute(
                "SELECT id,scene,drop_key,item_id,quantity,x,y,z,"
                "mob_identity,killer_identity,created_at "
                "FROM ground_drops WHERE id=?",
                (row_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("ground drop was not committed")
        return GroundDropRow(*row)

    def list_ground_drops_for_scene(self, scene: str) -> tuple[GroundDropRow, ...]:
        """Every row this door has ever written for one scene, oldest first.

        The read half of the door `commit_ground_drop` above writes.
        Lookup goes through `scene.casefold()`, matching `mob_loot.
        scene_key` exactly and matching the `scene_fold` column the write
        side keys its `UNIQUE` constraint against -- `"bg0002"` and
        `"Bg0002"` are one scene and this call answers the same either way.
        Ordered by `id` (insertion order); this method does not interpret
        "still on the ground" versus "already picked up" -- there is no
        removal path yet (see the migration's own docstring), so every row
        ever committed for this scene comes back, every time.
        """
        scene = _require_ground_drop_scene(scene)
        scene_fold = scene.casefold()
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,scene,drop_key,item_id,quantity,x,y,z,"
                "mob_identity,killer_identity,created_at "
                "FROM ground_drops WHERE scene_fold=? ORDER BY id",
                (scene_fold,),
            ).fetchall()
        return tuple(GroundDropRow(*row) for row in rows)

    def mark_ground_drop_taken(self, scene: str, drop_key: int) -> bool:
        """Mark one ground-drop row TAKEN.  Returns whether the row exists.

        Round `p6x3ee`, answering `notes_to_chief/20260904_1650_LANE-B-TO-
        LANE-DB-ground-drops-need-a-taken-marker.md`.  `migrations/
        012_ground_drops_taken_marker.sql` gives the `taken_at` column;
        this is the only thing in the codebase that sets it.  This is a
        MARK, not a `DELETE` -- `COO-DECISION 20260901_0253` ("no ledger
        row may be removed") stands, the same rule `commit_ground_drop`
        and its migration already answer to.

        IDEMPOTENT ON PURPOSE.  LANE-B's letter is explicit that pickup
        may be delivered more than once for the same `(scene, drop_key)`;
        calling this twice on the same row is not an error and does not
        move `taken_at` to the second call's time -- the `WHERE taken_at
        IS NULL` guard below means only the FIRST call actually writes,
        so the timestamp answers "when was this actually taken", not
        "when was this most recently asked about".

        THE RETURN VALUE ANSWERS ONE QUESTION ONLY: does a row for this
        `(scene, drop_key)` exist in this table at all (whether it was
        already taken, just got taken by this call, or is still standing
        after some other outcome)?  `True` either way a row exists;
        `False` only when the door was asked to mark a `drop_key` this
        scene never had a `commit_ground_drop` call for -- a caller with
        that gap has a bug LANE-B's side needs to see, not a value this
        door should paper over by pretending it happened anyway.
        """
        scene = _require_ground_drop_scene(scene)
        if isinstance(drop_key, bool) or not isinstance(drop_key, int):
            raise TypeError("drop_key must be an int")
        if not 0 <= drop_key <= 0xFFFFFFFF:
            raise ValueError(
                "drop_key 0x%X is outside the u32 range" % drop_key
            )
        scene_fold = scene.casefold()
        taken_at = _now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "UPDATE ground_drops SET taken_at=? "
                "WHERE scene_fold=? AND drop_key=? AND taken_at IS NULL",
                (taken_at, scene_fold, drop_key),
            )
            if cursor.rowcount:
                return True
            row = db.execute(
                "SELECT 1 FROM ground_drops WHERE scene_fold=? AND drop_key=?",
                (scene_fold, drop_key),
            ).fetchone()
            return row is not None

    def list_ground_drops_still_on_the_ground(
        self, scene: str
    ) -> tuple[GroundDropRow, ...]:
        """Every row for one scene that has NOT been marked taken, oldest first.

        The read half `mob_ground_persistence.restore_scene_ground` was
        refusing by name (`REFUSE_TAKEN_DOOR_IS_ABSENT`) until this method
        and `mark_ground_drop_taken` above both existed -- round `p6x3ee`,
        same letter as that method's docstring.  Same lookup shape as
        `list_ground_drops_for_scene` (fold-based, this door's own floor,
        no `mob_loot` import), with one extra `WHERE taken_at IS NULL`.

        `created_at` on the rows this returns is already the store's own
        `_now()` ISO-8601 format (`datetime.fromisoformat` parses it
        directly) -- a caller that wants to drop stale rows by age (LANE-B's
        letter raises the drop's own 120s lifetime) parses that column
        itself; whether a row is old enough to expire is `mob_loot.
        DROP_LIFETIME_SECONDS`, a gameplay constant this lane's charter
        keeps out of `store.py` on purpose (see `persistence_ground_drops.
        py`'s own docstring for why this door does not import `mob_loot`).
        This method answers "not yet marked taken", nothing about age.
        """
        scene = _require_ground_drop_scene(scene)
        scene_fold = scene.casefold()
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,scene,drop_key,item_id,quantity,x,y,z,"
                "mob_identity,killer_identity,created_at "
                "FROM ground_drops WHERE scene_fold=? AND taken_at IS NULL "
                "ORDER BY id",
                (scene_fold,),
            ).fetchall()
        return tuple(GroundDropRow(*row) for row in rows)

    def grant_starting_skills(
        self, character_id: int, skill_ids: "tuple[int, ...] | list[int]"
    ) -> tuple[int, ...]:
        """Persist a character's starting-kit skill ids, idempotently.

        `PANYA-DECISION 20260904_0328` piece 5 (`COO-ORDER 20260904_0329`
        item 5), the write half of `migrations/011_character_skills.sql`.
        LANE-DB owns this method; no existing method is touched by it.

        Every id is validated as a u32 skill id (0..4294967295) BEFORE any
        SQL runs, the same discipline `commit_ground_drop` uses for its own
        fields; an empty `skill_ids` is refused rather than treated as a
        silent no-op, matching `persistence_typed_attrs.validate_all`.

        IDEMPOTENT, NOT A COLLISION REFUSAL.  `migrations/
        011_character_skills.sql`'s own docstring explains why: a second
        grant of a skill a character already has (the create-fingerprint
        retry path in `CharacterLifecycle.create` can call this twice for
        one character) is a no-op here, via `INSERT OR IGNORE` against the
        table's `UNIQUE(character_id, skill_id)`, not a `ValueError` the way
        a ground-drop key collision is -- those are two different callers
        racing for one slot; this is the same caller confirming the same
        fact twice.  `INSERT OR IGNORE`, DELIBERATELY NOT `INSERT OR
        REPLACE` (pf-adversary): the two look interchangeable on an exact
        repeat, but `OR REPLACE` deletes-then-reinserts a colliding row,
        which gives it a NEW `id` and a NEW `granted_at` and -- because
        SQLite's rowid ordering follows insertion, not the caller's argument
        order -- moves it to the end of the "ordered by insertion" result.
        `tests/test_persistence_character_skills_011.py::
        test_an_overlapping_reordered_regrant_touches_no_existing_row` is
        what catches that swap.

        Returns every distinct skill id now on the row -- this call's own
        ids plus anything already there -- read back INSIDE this method's
        own transaction, ordered by insertion, so the write and the read
        agree about what "now on the row" means under concurrency (the same
        reason `write_typed_attributes` reads its own write back on the
        same connection rather than as a separate call).

        Raises `KeyError` for a character that does not exist or has been
        soft-deleted (matching `write_typed_attributes`), `TypeError` for a
        non-int/bool `character_id`, a non-sequence `skill_ids`, or a
        non-int/bool id inside it, and `ValueError` for an empty sequence or
        an id outside the u32 range.  Nothing is written when anything is
        refused.
        """
        if isinstance(character_id, bool) or not isinstance(character_id, int):
            raise TypeError("character_id must be an int")
        if isinstance(skill_ids, (str, bytes)) or not isinstance(
            skill_ids, (list, tuple)
        ):
            raise TypeError("skill_ids must be a list or tuple of int")
        if not skill_ids:
            raise ValueError("no skill ids to grant")
        checked: list[int] = []
        for skill_id in skill_ids:
            if isinstance(skill_id, bool) or not isinstance(skill_id, int):
                raise TypeError("skill_id must be an int")
            if not 0 <= skill_id <= 0xFFFFFFFF:
                raise ValueError(
                    "skill_id %d is outside the u32 range" % skill_id
                )
            checked.append(skill_id)
        granted_at = _now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM characters WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if row is None:
                raise KeyError(character_id)
            for skill_id in checked:
                db.execute(
                    "INSERT OR IGNORE INTO character_skills"
                    "(character_id,skill_id,source,granted_at) VALUES (?,?,?,?)",
                    (character_id, skill_id, "starting_kit", granted_at),
                )
            after = db.execute(
                "SELECT skill_id FROM character_skills "
                "WHERE character_id=? ORDER BY id",
                (character_id,),
            ).fetchall()
        return tuple(r["skill_id"] for r in after)

    def list_character_skills(self, character_id: int) -> tuple[int, ...]:
        """Every skill id ever granted to this character, oldest grant first.

        The read half of the door `grant_starting_skills` above writes.
        Raises `TypeError` for a non-int/bool `character_id` (the same
        refusal the write side above makes, for the same reason: `sqlite3`
        binds python `True`/`False` as `1`/`0` with no complaint, which
        would silently read a caller's typo of a bool as character 1's
        skills).  Raises `KeyError` for a character that does not exist or
        has been soft-deleted, matching `read_typed_attributes` -- unlike
        `list_ground_drops_for_scene`, which is scoped to a scene rather
        than to one character's own row and so has no such row to miss.
        """
        if isinstance(character_id, bool) or not isinstance(character_id, int):
            raise TypeError("character_id must be an int")
        with self.connect() as db:
            exists = db.execute(
                "SELECT id FROM characters WHERE id=? AND deleted_at IS NULL",
                (character_id,),
            ).fetchone()
            if exists is None:
                raise KeyError(character_id)
            rows = db.execute(
                "SELECT skill_id FROM character_skills "
                "WHERE character_id=? ORDER BY id",
                (character_id,),
            ).fetchall()
        return tuple(r["skill_id"] for r in rows)

    @staticmethod
    def _character(r):
        return Character(int(r['id']),int(r['account_id']),int(r['selector']),r['name'],bytes(r['actor_wire']),bytes(r['avatar_wire']),int(r['identity_lo']),int(r['identity_hi']),Position(int(r['scene_id']),int(r['scene_seq']),float(r['x']),float(r['y']),float(r['z']),float(r['heading'])))
