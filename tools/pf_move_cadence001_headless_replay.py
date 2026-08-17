#!/usr/bin/env python3
"""MOVE-CADENCE-001: measure movement checkpoint cadence per walk, headless.

Wire layer   : decode every inbound frame of the authentic GT-005 boot1 capture
               with the pinned v141 parser (parse_outer / parse_v141_refresh_target_pos).
Gate layer   : replay the exact foundation dedup rule (_checkpoint_exact_target:
               write only when (x,y,z,heading) differs from the selected position).
DB layer     : drive the real SQLiteStore.save_position through that gate on a
               throwaway /tmp copy of the canonical DB and count actual UPDATEs.
Read-only discipline: capture + canonical DB are only read; all writes hit /tmp.
"""
import importlib.util, re, sys, math, shutil, sqlite3, os, hashlib, struct, tempfile

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/sessions/determined-vigilant-dirac/mnt/Pirate Force"
SRV  = f"{ROOT}/Pirate Force ServerProject"
CAP1 = f"{ROOT}/GameClient/capture_gt005_boot1_20260817_122339/capture_v141/GAME_20260817_122544_319475_53892.txt"
CAP2 = f"{ROOT}/GameClient/capture_gt005_boot2_20260817_123551/capture_v141/GAME_20260817_123751_896343_61985.txt"
TMP  = os.path.join(tempfile.gettempdir(), "pf_move_cadence001")

# GT-005 report anchors (reports/PF_GT005_..._RUNTIME_PASS_20260817.md A1)
BEFORE = (-9098.5507812500, -2866.8618164062, 186.0, 2.9943714142)
AFTER  = (-8094.6079101562, -3207.8305664062, 186.0, 2.4992544651)

sys.path.insert(0, f"{SRV}/src")
spec = importlib.util.spec_from_file_location("pf141", f"{SRV}/current/pf_login_game_server_v141.py")
m = importlib.util.module_from_spec(spec)
sys.modules["pf141"] = m
spec.loader.exec_module(m)

HEXLINE = re.compile(r"^[0-9A-Fa-f]{8}\s+((?:[0-9A-Fa-f]{2} )+)")

def read_frames(path):
    """Yield (frame_ordinal, heartbeat_count_before_frame, pc_bytes)."""
    frames, hb, collecting, buf = [], 0, False, []
    with open(path, "r", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line.startswith("RUNTIME_HEARTBEAT_SENT"):
                hb += 1
            if collecting:
                mm = HEXLINE.match(line)
                if mm:
                    buf.append(bytes.fromhex(mm.group(1).replace(" ", "")))
                    continue
                frames.append((len(frames) + 1, hb, b"".join(buf)))
                collecting, buf = False, []
            if line.startswith("DECOMPRESSED"):
                collecting, buf = True, []
    if collecting and buf:
        frames.append((len(frames) + 1, hb, b"".join(buf)))
    return frames

def decode(frames):
    rows = []
    for idx, hb, pc in frames:
        try:
            parsed = m.parse_outer(pc)
        except Exception as e:
            rows.append({"idx": idx, "hb": hb, "kind": f"parse_error:{e!r}"})
            continue
        if parsed.nested_id != m.TARGET_POS_VITAL:
            continue
        exact = m.parse_v141_refresh_target_pos(parsed)
        loose = m.parse_target_pos_vital(parsed)
        rows.append({"idx": idx, "hb": hb, "kind": "exact" if exact else "nonexact",
                     "pos": exact or loose})
    return rows

def main():
    os.makedirs(TMP, exist_ok=True)
    frames1 = read_frames(CAP1)
    frames2 = read_frames(CAP2)
    tp1 = decode(frames1)
    tp2 = decode(frames2)
    print(f"boot1 inbound frames={len(frames1)}  TargetPos rows={len(tp1)}")
    print(f"boot2 inbound frames={len(frames2)}  TargetPos rows={len(tp2)}")
    exact = [r for r in tp1 if r.get("kind") == "exact"]
    nonexact = [r for r in tp1 if r.get("kind") == "nonexact"]
    errors = [r for r in tp1 if "parse_error" in r.get("kind", "")]
    print(f"boot1 TargetPos: exact={len(exact)} nonexact={len(nonexact)} parse_errors={len(errors)}")

    # ---- gate layer: replica of runtime._checkpoint_exact_target dedup ----
    cur = BEFORE
    writes, dedup_skips = [], 0
    for r in exact:
        x, y, z, h, _flags, moving = r["pos"]
        cand = (x, y, z, h)
        if cand != cur:
            writes.append({**r, "cand": cand})
            cur = cand
        else:
            dedup_skips.append if False else None
            dedup_skips += 1
    print(f"\ngate: writes={len(writes)} dedup_skips={dedup_skips} (initial=BEFORE row)")
    mv = [r["pos"][5] for r in exact]
    print(f"moving flag: 1×{mv.count(1)} 0×{mv.count(0)} other×{len([v for v in mv if v not in (0,1)])}")

    # ordinal spacing via heartbeat counter (heartbeats between successive TargetPos)
    hbs = [r["hb"] for r in exact]
    gaps = [b - a for a, b in zip(hbs, hbs[1:])]
    print(f"heartbeat-gaps between TargetPos frames: min={min(gaps) if gaps else '-'} "
          f"max={max(gaps) if gaps else '-'} mean={sum(gaps)/len(gaps):.2f}" if gaps else "no gaps")
    idxs = [r["idx"] for r in exact]
    print(f"frame ordinals: first={idxs[0] if idxs else '-'} last={idxs[-1] if idxs else '-'} of {len(frames1)}")

    final = writes[-1]["cand"] if writes else cur
    match = all(abs(a - b) < 1e-4 for a, b in zip(final, AFTER))
    print(f"\nfinal simulated position = {final}")
    print(f"matches GT-005 AFTER row (±1e-4): {match}")

    # per-frame table
    print("\nidx  hb   x            y            z        heading   moving  write")
    for r in exact:
        x, y, z, h, _f, mvf = r["pos"]
        w = "W" if any(w2["idx"] == r["idx"] for w2 in writes) else "."
        print(f"{r['idx']:>4} {r['hb']:>4} {x:>12.4f} {y:>12.4f} {z:>8.2f} {h:>9.4f}   {mvf}      {w}")

    # ---- DB layer: real store on a /tmp copy of the canonical DB ----
    src_db = f"{SRV}/state/pirateforce.sqlite3"
    dst_db = f"{TMP}/pirateforce.sqlite3"
    for suf in ("", "-shm", "-wal"):
        s = src_db + suf
        if os.path.exists(s):
            shutil.copy(s, dst_db + suf)
    from pirateforce_foundation.store import SQLiteStore
    from pirateforce_foundation.model import Position
    store = SQLiteStore(dst_db, f"{SRV}/migrations")
    with store.connect() as db:
        row = db.execute("SELECT character_id,scene_id,scene_seq,x,y,heading FROM character_positions WHERE character_id=1").fetchone()
        if row is None:
            row = db.execute("SELECT character_id,scene_id,scene_seq,x,y,heading FROM character_positions ORDER BY character_id LIMIT 1").fetchone()
        cid, scene_id, scene_seq = row["character_id"], row["scene_id"], row["scene_seq"]
        acct = db.execute("SELECT account_id FROM characters WHERE id=?", (cid,)).fetchone()["account_id"]
        cols = [c["name"] for c in db.execute("PRAGMA table_info(sessions)")]
        sid = "cadence001aa"
        vals = {"id": sid, "account_id": acct, "selected_character_id": cid}
        names = [c for c in cols if c in vals or c.endswith("_at")]
        stamp = "2026-08-18T00:00:00Z"
        db.execute(
            f"INSERT INTO sessions({','.join(names)}) VALUES ({','.join('?'*len(names))})",
            [vals.get(c, None if c == "closed_at" else stamp) for c in names],
        )
    print(f"\nDB copy: character_id={cid} scene=({scene_id},{scene_seq}) session={sid}")
    db_writes = 0
    for w in writes:
        x, y, z, h = w["cand"]
        store.save_position(sid, cid, Position(scene_id, scene_seq, x, y, z, h))
        db_writes += 1
    with store.connect_read_only() as db:
        fin = db.execute("SELECT x,y,z,heading,updated_at FROM character_positions WHERE character_id=?", (cid,)).fetchone()
    ok = all(abs(fin[k] - v) < 1e-4 for k, v in zip(("x", "y", "z", "heading"), AFTER))
    print(f"DB layer: save_position succeeded ×{db_writes} (each verified rowcount==1 by store)")
    print(f"DB final row x={fin['x']:.10f} y={fin['y']:.10f} z={fin['z']} h={fin['heading']:.10f}")
    print(f"DB final row matches GT-005 AFTER (±1e-4): {ok}")

    # canonical untouched proof
    hsh = hashlib.sha256(open(src_db, "rb").read()).hexdigest().upper()
    print(f"\ncanonical DB sha256 (read-only) = {hsh[:8]}..{hsh[-4:]}")

if __name__ == "__main__":
    main()
