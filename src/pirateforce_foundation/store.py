import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
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

    def migrate(self) -> None:
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied = {r[0] for r in db.execute("SELECT version FROM schema_migrations")}
            for path in sorted(self.migrations.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(path.name[:3])
                if version not in applied:
                    db.executescript(path.read_text(encoding="utf-8"))
                    db.execute("INSERT INTO schema_migrations VALUES (?,?)", (version, _now()))

    def ensure_account(self, name: str) -> int:
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO accounts(login_name,created_at) VALUES (?,?)", (name, _now()))
            return int(db.execute("SELECT id FROM accounts WHERE login_name=?", (name,)).fetchone()[0])

    def open_session(self, account_id: int) -> str:
        sid = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO sessions(id,account_id,opened_at) VALUES (?,?,?)", (sid, account_id, _now()))
        return sid

    def close_session(self, sid: str) -> None:
        with self.connect() as db:
            db.execute("UPDATE sessions SET closed_at=? WHERE id=? AND closed_at IS NULL", (_now(), sid))

    def create_character(self, account_id, selector, name, wire, avatar_wire, lo, hi, pos):
        with self.connect() as db:
            now = _now()
            cur = db.execute("INSERT INTO characters(account_id,selector,name,actor_wire,avatar_wire,avatar_typed_json,identity_lo,identity_hi,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (account_id,selector,name,wire,avatar_wire,None,lo,hi,now,now))
            cid = int(cur.lastrowid)
            db.execute("INSERT INTO character_positions VALUES (?,?,?,?,?,?,?)", (cid,pos.scene_id,pos.scene_seq,pos.x,pos.y,pos.z,_now()))
        return self.get_character(cid)

    def list_characters(self, account_id: int):
        with self.connect() as db:
            rows = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z FROM characters c JOIN character_positions p ON p.character_id=c.id WHERE c.account_id=? AND c.deleted_at IS NULL ORDER BY c.selector", (account_id,)).fetchall()
        return [self._character(r) for r in rows]

    def get_character(self, cid: int):
        with self.connect() as db:
            row = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z FROM characters c JOIN character_positions p ON p.character_id=c.id WHERE c.id=?", (cid,)).fetchone()
        if row is None: raise KeyError(cid)
        return self._character(row)

    def select_character(self, sid: str, selector: int):
        with self.connect() as db:
            row = db.execute("SELECT c.*,p.scene_id,p.scene_seq,p.x,p.y,p.z FROM sessions s JOIN characters c ON c.account_id=s.account_id JOIN character_positions p ON p.character_id=c.id WHERE s.id=? AND s.closed_at IS NULL AND c.deleted_at IS NULL AND c.selector=?", (sid,selector)).fetchone()
            if row is None: raise KeyError(selector)
            db.execute("UPDATE sessions SET selected_character_id=? WHERE id=?", (row['id'],sid))
        return self._character(row)

    def save_position(self, cid: int, pos: Position):
        with self.connect() as db:
            db.execute("UPDATE character_positions SET scene_id=?,scene_seq=?,x=?,y=?,z=?,updated_at=? WHERE character_id=?", (pos.scene_id,pos.scene_seq,pos.x,pos.y,pos.z,_now(),cid))

    @staticmethod
    def _character(r):
        return Character(int(r['id']),int(r['account_id']),int(r['selector']),r['name'],bytes(r['actor_wire']),bytes(r['avatar_wire']),int(r['identity_lo']),int(r['identity_hi']),Position(int(r['scene_id']),int(r['scene_seq']),float(r['x']),float(r['y']),float(r['z'])))
