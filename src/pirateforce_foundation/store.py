import sqlite3
import hashlib
import math
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

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")

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
            cur = db.execute("INSERT INTO characters(account_id,selector,name,name_key,create_fingerprint,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (account_id,selector,name,name_key,fingerprint,wire,avatar_wire,None,lo,hi,now,now))
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

        After `006` all three columns are NULL on every existing character, so
        today this returns a resolution with three `vital_column_not_seeded`
        gaps and `complete` False for every character in the database.  That
        is the correct answer, not a failure: seeding waits on a value COO has
        not adjudicated (see `persistence_vitals`' docstring).

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
        wire field.  So on today's database, where nothing is seeded, this
        method refuses for every character, loudly, by design.

        The read and the write are ONE transaction on ONE connection
        (`BEGIN IMMEDIATE`).  That line is NOT decoration and the cost of
        losing it is measured, not feared: a `pf-adversary` pass deleted it
        and ran 8 threads x 60 hits of 1 damage at one character -- 232 of
        the 480 hits vanished (hp 99752 instead of 99520) and surfaced as
        `KeyError`, which this method's own contract says means "no such
        character".  A lost hit reported as a missing character is the worst
        shape this method could fail in, so the lock now has a test that
        fails without it (`tests/test_persistence_vitals.py`,
        `BeginImmediateHoldsTheWriteLockTests`).

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
        """
        from . import persistence_typed_attrs as typed_attrs
        from . import persistence_vitals as vitals

        columns = list(typed_attrs.TYPED_COLUMNS)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
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
    def _character(r):
        return Character(int(r['id']),int(r['account_id']),int(r['selector']),r['name'],bytes(r['actor_wire']),bytes(r['avatar_wire']),int(r['identity_lo']),int(r['identity_hi']),Position(int(r['scene_id']),int(r['scene_seq']),float(r['x']),float(r['y']),float(r['z']),float(r['heading'])))
