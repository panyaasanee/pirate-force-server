"""MOVE-ISOLATION-001 headless probe: cross-session / cross-character and
cross-account isolation of the generalized free-slot item move (HYP-PF-010).

The generalized move request carries no owner/character field on the wire
(parse_item_operate_req -> (operation, destination_slot, item_identity)); the
target Backpack is entirely the session-bound selected character, and every
persistence read/write is guarded by _require_selected_session, whose SQL
predicate joins the open session to its own selected character within its own
account.  This probe proves that invariant to the wire and the DB on a real
server process over real TCP.

Runtime, serial (no concurrency required):

  Two characters of one development account, each seeded with its own
  identical four-item INITIAL Backpack (same contents, different character_id):

    session A: select character A, commit one real free-slot move
      (identity 1 from slot 0 to free slot 4).  Character A's rows must change
      to identity 1 at slot 4; character B's rows and updated_at must be
      byte-identical across A's move.
    session B (reconnect, new session): select character B, commit the exact
      same wire request.  Character B's rows must change; character A's rows
      must be byte-identical across B's move (they still carry only A's move).

  The two moves are byte-identical wire requests yet mutate disjoint row sets,
  proving item_identity resolves inside the session's own Backpack only.

DB guard (cross-account, defense in depth, not wire-reachable):

  A second account with its own character is seeded directly in the scratch DB.
  The exact _require_selected_session predicate is exercised against seeded
  rows and must:
    - accept  the owning open session for its own selected character;
    - reject  a foreign-account character for that session;
    - reject  a sibling same-account character the session did not select;
    - reject  a closed session.

Scope guard: sockets + one scratch DB only.  Never launches, touches, or
automates GameClient.  Never opens the canonical state DB.  No repo writes
(--db-file and --json must point outside the repo).  stdlib only.

Exit codes
  0  all passes held
  3  ran, but at least one expectation failed (details in JSON)
  4  socket/connection problem
  2  usage problem
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import time
from pathlib import Path


HEARTBEAT_FRAME_SHA256 = (
    "B4F6CFA26FF6181AD62E57BFA8B6813368F24FCF31E69E4FBFAE6E0AE452ACB1"
)

# The exact _require_selected_session predicate from store.py.  Copied here
# verbatim so the probe exercises the production isolation SQL, not a paraphrase.
GUARD_SQL = (
    "SELECT 1 FROM sessions s JOIN characters c "
    "ON c.id=s.selected_character_id AND c.account_id=s.account_id "
    "AND c.deleted_at IS NULL WHERE s.id=? AND s.selected_character_id=? "
    "AND s.closed_at IS NULL"
)


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest().upper()


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load_legacy(root: Path):
    path = root / "current" / "pf_login_game_server_v141.py"
    spec = importlib.util.spec_from_file_location("pf_probe_legacy_v141", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def recv_frame(sock: socket.socket) -> bytes | None:
    head = b""
    while len(head) < 8:
        chunk = sock.recv(8 - len(head))
        if not chunk:
            return None
        head += chunk
    _magic, nlen = struct.unpack("<II", head)
    body = b""
    while len(body) < nlen:
        chunk = sock.recv(nlen - len(body))
        if not chunk:
            return None
        body += chunk
    return head + body


def drain(sock, seconds):
    sock.settimeout(seconds)
    frames = []
    eof = False
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            frame = recv_frame(sock)
        except socket.timeout:
            break
        except OSError:
            eof = True
            break
        if frame is None:
            eof = True
            break
        frames.append((time.monotonic(), frame))
    return frames, eof


def non_heartbeats(stamped):
    return [(t, b) for t, b in stamped if _sha(b) != HEARTBEAT_FRAME_SHA256]


# --- DB helpers (read-only unless explicitly seeding) -----------------------

def _ro(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def active_characters(db_path: Path):
    db = _ro(db_path)
    try:
        return [
            (int(r[0]), int(r[1]), int(r[2]))
            for r in db.execute(
                "SELECT id, selector, account_id FROM characters "
                "WHERE deleted_at IS NULL ORDER BY selector"
            ).fetchall()
        ]
    finally:
        db.close()


def backpack_rows(db_path: Path, character_id: int):
    db = _ro(db_path)
    try:
        return [
            list(r) for r in db.execute(
                "SELECT item_identity,slot,quantity,template_id,"
                "raw_u8_38,raw_u8_39,detail_present "
                "FROM character_backpack_items WHERE character_id=? "
                "ORDER BY item_identity",
                (character_id,),
            ).fetchall()
        ]
    finally:
        db.close()


def backpack_updated_at(db_path: Path, character_id: int):
    db = _ro(db_path)
    try:
        row = db.execute(
            "SELECT updated_at FROM character_backpacks WHERE character_id=?",
            (character_id,),
        ).fetchone()
        return row[0] if row else None
    finally:
        db.close()


# --- wire flow --------------------------------------------------------------

def bootstrap_one_character(legacy, host, port, db_path, window):
    """One connection: log in and create a first character if none is active."""
    s = socket.create_connection((host, port), timeout=8.0)
    try:
        s.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
        drain(s, window)
        if not active_characters(db_path):
            s.sendall(legacy.frame_pc(legacy._V25_REAL_CREATE_PC))
            drain(s, window)
    finally:
        s.close()


def enter_runtime_ready(legacy, host, port, selector, window):
    """Log in a fresh session, select `selector`, reach runtime-ready."""
    s = socket.create_connection((host, port), timeout=8.0)
    s.sendall(legacy.frame_pc(legacy._synthetic_client_login_pc()))
    drain(s, window)
    s.sendall(legacy.frame_pc(legacy._synthetic_start_game_pc(selector)))
    drain(s, window)
    s.sendall(legacy.frame_pc(legacy.V136_EMPTY_RUNTIME_REQ_PC))
    drain(s, window)
    frames, _eof = drain(s, 2.6)
    heartbeats = len(frames) - len(non_heartbeats(frames))
    return s, heartbeats


def seed_second_character(db_path: Path, checks: dict) -> int:
    """Duplicate the first active character into a same-account sibling with
    its own identical INITIAL Backpack.  Returns the new character id."""
    db = sqlite3.connect(str(db_path))
    try:
        db.execute("PRAGMA foreign_keys=ON")
        src = db.execute(
            "SELECT id,account_id,selector,actor_wire,avatar_wire,"
            "avatar_typed_json,identity_lo,identity_hi "
            "FROM characters WHERE deleted_at IS NULL ORDER BY selector LIMIT 1"
        ).fetchone()
        (src_id, account_id, selector, actor_wire, avatar_wire,
         avatar_typed_json, identity_lo, identity_hi) = src
        now = _now()
        cur = db.execute(
            "INSERT INTO characters(account_id,selector,name,name_key,"
            "create_fingerprint,actor_wire,avatar_wire,avatar_typed_json,"
            "identity_lo,identity_hi,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, int(selector) + 1, "isoBravo", "isobravo",
             "seed-fingerprint-move-iso-002", actor_wire, avatar_wire,
             avatar_typed_json, int(identity_lo) + 0x10000, int(identity_hi),
             now, now),
        )
        new_id = int(cur.lastrowid)
        db.execute(
            "INSERT INTO character_positions"
            "(character_id,scene_id,scene_seq,x,y,z,updated_at,heading) "
            "SELECT ?,scene_id,scene_seq,x,y,z,?,heading "
            "FROM character_positions WHERE character_id=?",
            (new_id, now, src_id),
        )
        db.execute(
            "INSERT INTO character_backpacks"
            "(character_id,base_mask,base_identity,range_mask,updated_at) "
            "SELECT ?,base_mask,base_identity,range_mask,? "
            "FROM character_backpacks WHERE character_id=?",
            (new_id, now, src_id),
        )
        db.execute(
            "INSERT INTO character_backpack_items"
            "(character_id,item_identity,template_id,quantity,slot,"
            "raw_u8_38,raw_u8_39,detail_present) "
            "SELECT ?,item_identity,template_id,quantity,slot,"
            "raw_u8_38,raw_u8_39,detail_present "
            "FROM character_backpack_items WHERE character_id=?",
            (new_id, src_id),
        )
        db.commit()
        checks["seeded_sibling"] = {
            "source_character_id": src_id, "new_character_id": new_id,
            "account_id": int(account_id),
            "source_selector": int(selector), "new_selector": int(selector) + 1,
        }
        return new_id
    finally:
        db.close()


def seed_foreign_account_character(db_path: Path, checks: dict) -> tuple[int, int]:
    """Seed a second account with its own duplicated character.  Returns
    (foreign_account_id, foreign_character_id)."""
    db = sqlite3.connect(str(db_path))
    try:
        now = _now()
        cur = db.execute(
            "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
            ("iso-foreign-account", now),
        )
        foreign_account_id = int(cur.lastrowid)
        src = db.execute(
            "SELECT actor_wire,avatar_wire,avatar_typed_json,identity_lo,"
            "identity_hi FROM characters WHERE deleted_at IS NULL "
            "ORDER BY selector LIMIT 1"
        ).fetchone()
        actor_wire, avatar_wire, avatar_typed_json, identity_lo, identity_hi = src
        cur = db.execute(
            "INSERT INTO characters(account_id,selector,name,name_key,"
            "create_fingerprint,actor_wire,avatar_wire,avatar_typed_json,"
            "identity_lo,identity_hi,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (foreign_account_id, 0, "isoForeign", "isoforeign",
             "seed-fingerprint-move-iso-foreign", actor_wire, avatar_wire,
             avatar_typed_json, int(identity_lo) + 0x1000000, int(identity_hi),
             now, now),
        )
        foreign_character_id = int(cur.lastrowid)
        # No backpack is seeded for the foreign character: the guard predicate
        # joins sessions->characters only, so its existence under a separate
        # account is all the cross-account rejection test requires.
        db.commit()
        checks["seeded_foreign"] = {
            "foreign_account_id": foreign_account_id,
            "foreign_character_id": foreign_character_id,
        }
        return foreign_account_id, foreign_character_id
    finally:
        db.close()


def run_guard_predicate(db_path: Path, own_account_id: int, own_char_id: int,
                        sibling_char_id: int, foreign_char_id: int,
                        checks: dict) -> bool:
    """Exercise the exact _require_selected_session SQL against synthetic
    open/closed sessions on the own account."""
    db = sqlite3.connect(str(db_path))
    try:
        now = _now()
        open_sid = "isoguard-open-session"
        closed_sid = "isoguard-closed-session"
        # An open session on the own account that has selected its own char.
        db.execute(
            "INSERT INTO sessions(id,account_id,lease_generation,"
            "selected_character_id,opened_at,closed_at) VALUES (?,?,?,?,?,NULL)",
            (open_sid, own_account_id, 900, own_char_id, now),
        )
        # A closed session on the own account with the same selection.
        db.execute(
            "INSERT INTO sessions(id,account_id,lease_generation,"
            "selected_character_id,opened_at,closed_at) VALUES (?,?,?,?,?,?)",
            (closed_sid, own_account_id, 901, own_char_id, now, now),
        )
        db.commit()

        def guard(sid, char_id):
            return db.execute(GUARD_SQL, (sid, char_id)).fetchone() is not None

        results = {
            "accept_owning_session_own_char": guard(open_sid, own_char_id),
            "reject_foreign_account_char": guard(open_sid, foreign_char_id),
            "reject_unselected_sibling_char": guard(open_sid, sibling_char_id),
            "reject_closed_session": guard(closed_sid, own_char_id),
        }
        checks["guard_predicate"] = results
        ok = (
            results["accept_owning_session_own_char"] is True
            and results["reject_foreign_account_char"] is False
            and results["reject_unselected_sibling_char"] is False
            and results["reject_closed_session"] is False
        )
        checks["guard_predicate_ok"] = bool(ok)
        # Clean up synthetic sessions so the DB reflects only real activity.
        db.execute("DELETE FROM sessions WHERE id IN (?,?)",
                   (open_sid, closed_sid))
        db.commit()
        return ok
    finally:
        db.close()


def isolation_move_pass(legacy, request_pc, host, port, selector,
                        mover_char_id, other_char_id, db_path, window,
                        checks, tag):
    """One session: commit one real free-slot move on `mover_char_id` and
    prove `other_char_id`'s rows are byte-identical across the move."""
    ok = True
    s, heartbeats = enter_runtime_ready(legacy, host, port, selector, window)
    checks[f"{tag}_heartbeats_before_request"] = heartbeats
    try:
        mover_before = backpack_rows(db_path, mover_char_id)
        mover_upd_before = backpack_updated_at(db_path, mover_char_id)
        other_before = backpack_rows(db_path, other_char_id)
        other_upd_before = backpack_updated_at(db_path, other_char_id)

        s.sendall(legacy.frame_pc(request_pc))
        stamped, eof = drain(s, window)
        others = non_heartbeats(stamped)

        mover_after = backpack_rows(db_path, mover_char_id)
        mover_upd_after = backpack_updated_at(db_path, mover_char_id)
        other_after = backpack_rows(db_path, other_char_id)
        other_upd_after = backpack_updated_at(db_path, other_char_id)

        committed_reply = (not eof) and (len(others) >= 1)
        mover_changed = (mover_after != mover_before)
        # The moved item (identity 1) must now sit at slot 4.
        moved_row_ok = any(
            r[0] == 1 and r[1] == 4 for r in mover_after
        )
        other_unchanged = (
            other_after == other_before
            and other_upd_after == other_upd_before
        )

        checks[f"{tag}_committed_reply"] = bool(committed_reply)
        checks[f"{tag}_reply_frames"] = [
            {"bytes": len(b), "sha256": _sha(b)} for _t, b in others
        ]
        checks[f"{tag}_mover_rows_before"] = mover_before
        checks[f"{tag}_mover_rows_after"] = mover_after
        checks[f"{tag}_mover_changed"] = bool(mover_changed)
        checks[f"{tag}_mover_moved_id1_to_slot4"] = bool(moved_row_ok)
        checks[f"{tag}_mover_updated_at_before"] = mover_upd_before
        checks[f"{tag}_mover_updated_at_after"] = mover_upd_after
        checks[f"{tag}_other_rows_before"] = other_before
        checks[f"{tag}_other_rows_after"] = other_after
        checks[f"{tag}_other_unchanged_across_move"] = bool(other_unchanged)

        ok = (
            committed_reply and mover_changed and moved_row_ok
            and other_unchanged and heartbeats >= 1
        )
        checks[f"{tag}_ok"] = bool(ok)
        return ok
    finally:
        try:
            s.close()
        except OSError:
            pass


def boot_server(root, db_path, scenario_rel, host, port, boot_wait):
    server = subprocess.Popen(
        [sys.executable, "-m", "pirateforce_foundation.app",
         "--db", str(db_path),
         "--item-move-hypothesis-scenario", str(root / scenario_rel)],
        cwd=root, env={**os.environ, "PYTHONPATH": str(root / "src")},
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + boot_wait
    while time.monotonic() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return server
        except OSError:
            time.sleep(0.4)
    server.terminate()
    return None


def stop_server(server):
    if server is None:
        return
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--game-port", type=int, default=10191)
    ap.add_argument("--db-file", required=True,
                    help="scratch DB OUTSIDE the repo; created fresh here")
    ap.add_argument("--json", required=True)
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--boot-wait", type=float, default=15.0)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    db_path = Path(args.db_file).resolve()
    for target in (db_path, Path(args.json).resolve()):
        try:
            target.relative_to(root)
        except ValueError:
            continue
        print(f"refusing repo write target: {target}", file=sys.stderr)
        return 2

    legacy = _load_legacy(root)
    sys.path.insert(0, str(root / "src"))
    from pirateforce_foundation.inventory import (  # noqa: E402
        INITIAL_BACKPACK,
        move_known_item_to_free_slot,
    )
    from pirateforce_foundation.item_move_capture import (  # noqa: E402
        ITEM_MOVE_CAPTURE_REQUEST_PC,
    )
    from pirateforce_foundation.store import SQLiteStore  # noqa: E402

    def request_pc(destination_slot: int, item_identity: int) -> bytes:
        pc = (
            ITEM_MOVE_CAPTURE_REQUEST_PC[:23]
            + struct.pack("<I", destination_slot)
            + ITEM_MOVE_CAPTURE_REQUEST_PC[27:28]
            + struct.pack("<Q", item_identity)
        )
        assert len(pc) == len(ITEM_MOVE_CAPTURE_REQUEST_PC)
        return pc

    # Sanity: identity 1 from slot 0 to free slot 4 is a valid free-slot move
    # on the exact INITIAL Backpack (not the same-slot no-op).
    transition = move_known_item_to_free_slot(INITIAL_BACKPACK, 1, 4)
    assert transition is not None
    move_request = request_pc(4, 1)

    verdict: dict = {"probe": "MOVE-ISOLATION-001", "checks": {}, "ok": False}
    checks = verdict["checks"]

    # Fresh scratch DB, migrated by the store's own migrator.
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLiteStore(db_path, root / "migrations").migrate()

    # Boot #1: bootstrap the first character over the wire.
    server = boot_server(root, db_path,
                         "scenarios/item_move_hypothesis_v111_slot2.json",
                         args.host, args.game_port, args.boot_wait)
    if server is None:
        print("bootstrap server did not open the GAME port", file=sys.stderr)
        return 4
    try:
        bootstrap_one_character(legacy, args.host, args.game_port, db_path,
                                args.window)
    finally:
        stop_server(server)

    chars = active_characters(db_path)
    if len(chars) != 1:
        verdict["error"] = f"expected exactly one bootstrapped character, got {chars}"
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
        print(json.dumps(verdict, indent=1))
        return 3
    char_a_id, char_a_selector, own_account_id = chars[0]

    # Seed a same-account sibling (character B) and a foreign-account character.
    char_b_id = seed_second_character(db_path, checks)
    _foreign_account_id, foreign_char_id = seed_foreign_account_character(
        db_path, checks)
    chars = {c[0]: c for c in active_characters(db_path)}
    char_b_selector = chars[char_b_id][1]
    checks["char_a"] = {"id": char_a_id, "selector": char_a_selector}
    checks["char_b"] = {"id": char_b_id, "selector": char_b_selector}

    # DB-guard predicate (no server needed).
    guard_ok = run_guard_predicate(
        db_path, own_account_id, char_a_id, char_b_id, foreign_char_id, checks)

    # Boot #2: run the two serial isolation sessions.
    results = []
    server = boot_server(root, db_path,
                         "scenarios/item_move_hypothesis_v111_slot2.json",
                         args.host, args.game_port, args.boot_wait)
    if server is None:
        print("isolation server did not open the GAME port", file=sys.stderr)
        return 4
    try:
        # Session A moves character A; character B must stay untouched.
        results.append(isolation_move_pass(
            legacy, move_request, args.host, args.game_port, char_a_selector,
            char_a_id, char_b_id, db_path, args.window, checks, "sessionA"))
        time.sleep(1.0)
        # Session B (reconnect) moves character B; character A must stay as it
        # was left after A's move (byte-identical across B's move).
        results.append(isolation_move_pass(
            legacy, move_request, args.host, args.game_port, char_b_selector,
            char_b_id, char_a_id, db_path, args.window, checks, "sessionB"))
    except (OSError, socket.timeout) as exc:
        verdict["error"] = repr(exc)
        stop_server(server)
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
        print(json.dumps(verdict, indent=1))
        return 4
    finally:
        stop_server(server)

    # Cross-request identity resolution: identical wire request, disjoint rows.
    same_request_disjoint = (
        checks.get("sessionA_mover_moved_id1_to_slot4") is True
        and checks.get("sessionB_mover_moved_id1_to_slot4") is True
        and char_a_id != char_b_id
    )
    checks["identical_request_disjoint_rows"] = bool(same_request_disjoint)

    verdict["ok"] = bool(
        all(results) and guard_ok and same_request_disjoint)
    code = 0 if verdict["ok"] else 3
    Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print(json.dumps(verdict, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
