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
    require_known_backpack,
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
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA synchronous=FULL")
        if self.path != ":memory:":
            db.execute("PRAGMA journal_mode=WAL")
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

    def ensure_account(self, name: str) -> int:
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO accounts(login_name,created_at) VALUES (?,?)", (name, _now()))
            return int(db.execute("SELECT id FROM accounts WHERE login_name=?", (name,)).fetchone()[0])

    def open_session(self, account_id: int) -> str:
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

    def save_position(self, sid: str, cid: int, pos: Position):
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
        db.execute(
            "INSERT INTO character_backpacks(character_id,base_mask,base_identity,range_mask,updated_at) "
            "VALUES (?,?,?,?,?)",
            (character_id, state.base_mask, state.base_identity, state.range_mask, stamp),
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
        return require_known_backpack(state)

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

    @staticmethod
    def _character(r):
        return Character(int(r['id']),int(r['account_id']),int(r['selector']),r['name'],bytes(r['actor_wire']),bytes(r['avatar_wire']),int(r['identity_lo']),int(r['identity_hi']),Position(int(r['scene_id']),int(r['scene_seq']),float(r['x']),float(r['y']),float(r['z']),float(r['heading'])))
