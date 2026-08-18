# PF-CORPUS-PIN-001 — Directory-scan survey: ทุกจุดที่ "นับไฟล์จากไดเรกทอรี" แล้วเอาตัวเลขไป pin

> **ชนิดงาน:** SURVEY อย่างเดียว (read-only) · ไม่แก้โค้ด ไม่แตะ `.gitignore` ไม่รัน server ไม่แตะ canonical DB
> **สำรวจที่ HEAD:** `6891372` · `git status --porcelain` ว่างตอนสำรวจ · วันที่ 2026-08-19
> **ขอบเขต:** `tools/` `tests/` `src/` (ข้าม `current/` ที่แช่แข็ง และ `backups/`) — แต่ *ปลายทางของ scan* หลายจุดชี้เข้า `backups/`, `analysis/`, และ `GameClient/` นอก repo จึงรายงานด้วย
> **ทุกตัวเลขในรายงานนี้มาจากคำสั่งที่รันจริง** คำสั่งครบอยู่ในภาคผนวก A

---

## บทสรุปผู้บริหาร (5 บรรทัด)

1. เจอ **13 จุด** ที่สแกนไดเรกทอรีเพื่อรวบรวม/นับชุดไฟล์ · ในนั้น **2 จุดเกรด A**, **2 จุดเกรด B**, **3 จุดเกรด C**, ที่เหลือ D/E
2. โรคหนักที่สุดอยู่ที่ `tools/pf_login_vital_req_static.py` **ทั้งสองบรรทัด (941, 981)** — ตัวเลข `archived_login_captures=63` และ `game_captures_with_the_same_account=44` ถูก pin ใน `reports/PF_MPOPT1B_*.md` และ `tests/test_login_vital_req_static.py` เทียบ **key-by-key แบบเท่ากันเป๊ะ**
3. **v141 เขียนไฟล์ลงในตัวส่วนทั้งสองชุดโดยตรง**: `current/pf_login_game_server_v141.py:7867` ตั้ง `capdir = Path("capture_v141")` (relative to cwd) แล้ว `:7401` เขียน `GAME_{stamp}.txt`, `:7945` เขียน `LOGIN_{stamp}.txt`, `:7372-7373` เขียนทับ `GAME_LIVE.txt` / `GAME_EVENTS_LIVE.txt` — ทุก boot ที่ cwd = repo root จึงขยับ **ทั้ง 63 และ 44/69** เงียบ ๆ เพราะ `capture_v141/` ติด `.gitignore:157` (`**/capture*/`)
4. ตอนนี้ `capture_v141/GAME_*.txt` = **69 ไฟล์ และในนั้นมี `GAME_LIVE.txt` + `GAME_EVENTS_LIVE.txt` ปนอยู่จริง 2 ไฟล์** (ตัวส่วนวันนี้ = 67 archived + 2 mutable) · `**/LOGIN_*.txt` = **63 ไฟล์ อยู่ใน `backups/` 59 + `analysis/` 4** ซึ่ง gitignore ทั้งคู่ (`.gitignore:1` = `/*`)
5. ของดีที่ควรลอกเป็นแบบ: `pf_structural_corpus_audit.py` (รายชื่อ input มาจาก config + sha256 pin, ไม่สแกนไดเรกทอรีเลย), `pf_multiplayer_readiness_audit` (pin ด้วยกฎ `>=` ไม่ใช่ `==`), `pf_teleportcheck` (pattern `GAME_2*` ตัดไฟล์ `GAME_LIVE` ออกโดยบังเอิญ), และ `pf_delete_refresh001_headless_replay.py:206-213` (บังคับ `--capture-root` นอก repo — ยาที่ chief ใส่ไว้แล้วหลังรอบ 81)

---

## ตารางจุดที่เจอทั้งหมด (เรียงตามเกรดความเสี่ยง)

| # | เกรด | ไฟล์:บรรทัด | สแกนอะไร | match จริงตอนนี้ | mutable/live ปน | ไดเรกทอรี gitignore | pin ที่ไหน |
|---|------|-------------|----------|------------------|------------------|---------------------|------------|
| 1 | **A** | `tools/pf_login_vital_req_static.py:981` | `capture_v141/GAME_*.txt` | **69** | **ใช่ — `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`** | ใช่ (`.gitignore:157` `**/capture*/`) | `PF_MPOPT1B_*.md` COUNTS `game_captures_with_the_same_account: 44` + test เทียบ `==` |
| 2 | **A** | `tools/pf_login_vital_req_static.py:941` | `**/LOGIN_*.txt` recursive จาก repo root | **63** (backups 59 / analysis 4) | ไม่มีตอนนี้ แต่ v141:7945 เขียนไฟล์ใหม่เข้ามาได้ทุก boot | ใช่ (`.gitignore:1` `/*`) | `PF_MPOPT1B_*.md` COUNTS `archived_login_captures: 63` + `..._with_0x42bf: 63` + test เทียบ `==` |
| 3 | **B** | `tools/pf_vital_id_resolve_static.py:130` | `<CORPUS>/*.txt` (default `"capture_v141"` — **relative ต่อ cwd**) | **69** | **ใช่ — 2 ไฟล์ LIVE เดียวกัน** | ใช่ (`.gitignore:157`) | ข้อสรุป "unnamed เหลือ 0 / 3 ตัว resolve" ใน `PF_NAMEID_RESOLVE001_*.md` + manifest (manifest เขียนไว้ตรง ๆ ว่า corpus เป็น `(ref, unpinned)`) · guard เป็นแค่ `len>0` |
| 4 | **B** | `tools/pf_teleportcheck_0x4477_static.py:132-134` | `GameClient/capture_v131|v13[6-9]|v14[0-9]/GAME_2*.txt` | **10 ไฟล์ → 8 rows** | ไม่มี (`GAME_2*` ตัด `GAME_LIVE` ออก) | อยู่ **นอก git worktree ทั้งก้อน** (`<repo>/../GameClient`) | ตาราง "wire corpus 8 เฟรม" ใน `PF_TELEPORT_CHECK001_*.md` §4 · ถ้าหาไม่เจอ → `print("SKIP ...")` **ไม่ fail** |
| 5 | **C** | `tests/test_foundation_legacy_seam.py:471` | `reports/*.manifest` | **63** (tracked ครบ 63, ignored 0) | ไม่มี | `reports/` เป็น allowlist — ไฟล์ใหม่ที่ไม่อยู่ใน allowlist จะ **ถูก ignore โดยอัตโนมัติ** | assert เป็น floor (`>=22`) + set เท่ากันเป๊ะของ `LEGACY_FORMAT_MANIFESTS` |
| 6 | **C** | `tools/pf_multiplayer_readiness_audit.py:469` | `os.listdir(tests/)` `*.py` | **74** | ไม่มี | ไม่ ignore (`tests/` tracked ครบ, untracked 0) | `AUDIT_COUNTS.tests_total_files_at_head: 61` — เทียบด้วยกฎ `>=` (74 ≥ 61 จึงยังเขียว) |
| 7 | **C** | `tools/pf_split_operate_verb_panels_static.py:197` + `tests/test_split_operate_verb_panels_static.py:154` | `GameClient/Data/GUI/Model/` | tool `os.listdir` = **573 entries** · test `glob("*.model")` = **534** | ไม่มี | นอก git worktree | ข้อสรุปเชิงลบ "ไม่มี model ชื่อ split/divide" (วันนี้ตรงกับความจริง: match = **0**) pin ใน `PF_SPLIT_OPERATE003_*.md` + assert ในเทส |
| 8 | D | `tools/deploy_current.ps1:15` | `current/run_v<N>*.bat` | 1 (โดยดีไซน์) | ไม่มี | `current/` เป็น allowlist (`.gitignore` `/current/*`) | ไม่ pin — `throw` ทันทีถ้า count ≠ 1 (**ดังไม่เงียบ**) |
| 9 | D | `tools/build_foundation_release.py:10-12` | `src/**.py` (32), `migrations/*.sql` (4), `scenarios/*.json` (23) | 32 / 4 / 23 | ไม่มี | ไม่ ignore | ไม่มีรายงาน/เทสอ้างถึงเลย → **ความเสี่ยงต่ำ** |
| 10 | E | `tools/wait_for_pf_stage.py:40` | `rglob("*.txt")` กรองเฉพาะชื่อที่มี `GAME_LIVE`/`GAME_EVENTS_LIVE` | ขึ้นกับ argument ตอนรัน | **ตั้งใจให้เป็น live** | `capture*/` ignore | ไม่ pin (ใช้รอ stage เท่านั้น) → **ความเสี่ยงต่ำ** |
| 11 | E | `src/pirateforce_foundation/store.py:78` | `migrations/[0-9][0-9][0-9]_*.sql` | 4 | ไม่มี | ไม่ ignore | ไม่ pin เป็นตัวเลข (มี checksum ต่อไฟล์ + guard version ซ้ำ) → **ความเสี่ยงต่ำ** |
| 12 | E | `tools/pf_hp_death_respawn_static.py:789`, `tools/pf_stats_progression_static.py:1399` | `os.walk(src/pirateforce_foundation)` | 32 ไฟล์ | ไม่มี | ไม่ ignore | ผลที่ใช้คือ **content assertion เชิงลบ** (`hits == []`) ไม่ใช่จำนวนไฟล์ → **ความเสี่ยงต่ำ** |
| 13 | E | containment globs 12 จุด (ดู §13) | `src/pirateforce_foundation/*.py` | 32 ไฟล์ | ไม่มี | ไม่ ignore | assert เป็น **รายชื่อโมดูล** (`["app.py","runtime.py"]`) ไม่ใช่จำนวน → **ความเสี่ยงต่ำ** |

**นับรวม: 13 จุด** (จุดที่ 13 รวม 12 call site ที่เป็นโรคเดียวกันแบบไม่มีพิษ)

---

## รายละเอียดต่อจุด

### 1. `tools/pf_login_vital_req_static.py:981` — เกรด A (แย่สุด)

```python
GAME_CAPTURES = sorted(glob.glob(os.path.join(_ROOT, "capture_v141", "GAME_*.txt")))
```

* `_ROOT` = `tools/..` (บรรทัด 157) → ชี้ที่ `<repo>/capture_v141/`
* **match วันนี้ = 69 ไฟล์** และในนั้นมี `GAME_EVENTS_LIVE.txt` กับ `GAME_LIVE.txt` (ตรวจจริง: `[p for p in G if "LIVE" in p]` คืนสองชื่อนี้)
* ทั้งสองไฟล์ถูก **เขียนทับทุกครั้งที่ server รัน** — `current/pf_login_game_server_v141.py:7372-7373`:
  `live_path = capdir / "GAME_LIVE.txt"`, `event_path = capdir / "GAME_EVENTS_LIVE.txt"` โดย `capdir = pathlib.Path("capture_v141")` (บรรทัด 7867, **relative ต่อ cwd**)
* gitignore: `git check-ignore -v capture_v141` → `.gitignore:157: **/capture*/` → **ทุกความเคลื่อนไหวในไดเรกทอรีนี้ git มองไม่เห็น**
* pin ต่อไปที่ไหน: ตัวเศษ `_verify_hits` ถูกใส่ `COUNTS["game_captures_with_the_same_account"]` → pin ใน `reports/PF_MPOPT1B_LOGIN_VITAL_REQ_0X42BF_STATIC_20260819.md` (บรรทัด 237 prose "**44 of the capture_v141 GAME files**" และใน block `LOGIN_REQ_COUNTS`) → `tests/test_login_vital_req_static.py:124-129` เทียบ **ทุก key แบบ `assertEqual`**
* ตรวจจริงวันนี้: จำลองตรรกะทั้งดุ้น (ภาคผนวก A-3) ได้ **44 hits ตรงกับที่ pin** และ **ไฟล์ LIVE ยังไม่เข้าเงื่อนไข** (0 hits จาก LIVE)
* **ทำไมยังเป็น A ทั้งที่วันนี้ยังตรง:** ตัวส่วนไม่นิ่ง (69 รวม LIVE), ไฟล์ LIVE จะติดนับทันทีที่มี login จริงในรอบนั้น, และไฟล์ `GAME_<stamp>.txt` ใหม่ (บรรทัด 7401) งอกทุก boot ที่ไม่ override capture root — ทั้งหมดนี้ git มองไม่เห็น เท่ากับตัวเลข 44 เป็น **assertion ที่ผูกกับ working directory ของเครื่อง ไม่ใช่กับ commit**

### 2. `tools/pf_login_vital_req_static.py:941` — เกรด A

```python
LOGIN_CAPTURES = sorted(
    glob.glob(os.path.join(_ROOT, "**", "LOGIN_*.txt"), recursive=True)
)
```

* **match วันนี้ = 63 ไฟล์** กระจายเป็น `backups/` 59 · `analysis/` 4 (ไม่มีในที่อื่นเลย)
* ทั้งสองไดเรกทอรีติด `.gitignore:1` (`/*` = ignore ทุกอย่างที่ไม่ได้ allowlist)
* **ขอบเขต scan ไม่มีเพดาน** — `**` recursive จาก repo root: ไฟล์ `LOGIN_*.txt` ที่โผล่ *ที่ไหนก็ได้* ในต้นไม้จะถูกดูดเข้ามาทันที และ `current/pf_login_game_server_v141.py:7945` (`lp = capdir / f"LOGIN_{stamp}_{addr[1]}.txt"`) คือ writer ที่ทำแบบนั้นได้ทุก boot — เป็นเครื่องเดียวกับที่รอบ 81 ทำ corpus โต 69→72
* pin ต่อไปที่ไหน: `archived_login_captures: 63` และ `archived_login_captures_with_0x42bf: 63` ใน `LOGIN_REQ_COUNTS` + prose บรรทัด 213 ("in **all 63** archived login captures") และ 258 → เทียบ `==` ในเทส
* หมายเหตุ: รายงานมี **Re-pinning rule** เขียนไว้แล้วว่าเลขชุดนี้ "ควรขยับเมื่อ GT-020 รัน" — เจตนาถูก แต่กลไกผิด เพราะมันขยับได้จาก *อะไรก็ได้* ที่เขียนไฟล์ ไม่ใช่เฉพาะ GT-020 และไม่มีอะไรบอกว่าใครขยับ
* manifest ของรายงาน pin ไว้แค่ **1 ตัวแทน** (`analysis\...\LOGIN_20260814_152723_188831_59376.txt`) พร้อมคอมเมนต์ "the verifier reads all 63" → ไฟล์ที่เหลืออีก 62 ไม่มี sha ผูกไว้เลย

### 3. `tools/pf_vital_id_resolve_static.py:130` — เกรด B

```python
corpus_files = sorted(glob.glob(os.path.join(CORPUS, "*.txt")))
guard(len(corpus_files) > 0, f"golden corpus present ({len(corpus_files)} files under {CORPUS})")
```

* `CORPUS = sys.argv[2] if len(sys.argv) > 2 else "capture_v141"` (บรรทัด 75) — **relative path** → ผลลัพธ์ขึ้นกับ cwd ที่รัน
* **match วันนี้ = 69 ไฟล์** (`*.txt` ทั้งหมดใน `capture_v141/`) รวม `GAME_LIVE.txt` + `GAME_EVENTS_LIVE.txt`
* ตรวจจริง: วันนี้ไฟล์ LIVE **ไม่มีบรรทัด `STRUCTURAL_IDS` เลย (0 บรรทัด)** จึงยังไม่ทำให้ชุด id เพี้ยน — corpus ให้ named 7 tuple, unnamed 3 (`0x1B40`, `0x36DB`, `0xAC52`) ตรงกับที่รายงานเล่า
* gitignore: ใช่ (`.gitignore:157`)
* pin ต่อไปที่ไหน: ไม่มี COUNTS block และ **ไม่มีเทสไหน import เครื่องมือนี้เลย** (`grep pf_vital_id_resolve tests/` = ว่าง) — สิ่งที่ pin คือ *ข้อสรุปที่ได้จาก corpus* ใน `PF_NAMEID_RESOLVE001_*.md` ("เหลือ 0 unnamed", "6 golden named cross-checked") + manifest ซึ่งเขียนตรง ๆ ว่า corpus เป็น `(ref, unpinned)`
* เหตุที่เป็น B ไม่ใช่ A: guard เป็น floor (`>0`) ไม่ใช่ตัวเลขตายตัว และไม่มีเทส gate เทียบ — drift จะไม่ทำให้ gate แดง (ซึ่งก็แปลว่า **จะไม่มีใครรู้** เหมือนกัน แค่ไม่พังของคนอื่น)

### 4. `tools/pf_teleportcheck_0x4477_static.py:132-134` — เกรด B

```python
for gl in sorted(glob.glob(os.path.join(root, "GameClient", "capture_v13[6-9]", "GAME_2*.txt"))
                 + glob.glob(os.path.join(root, "GameClient", "capture_v14[0-9]", "GAME_2*.txt"))
                 + glob.glob(os.path.join(root, "GameClient", "capture_v131", "GAME_2*.txt"))):
```

* `root = dirname(dirname(abspath(BIN)))` → `C:\Users\Panya\Desktop\Pirate Force` (พาเรนต์ของ repo) → สแกน `GameClient/capture_v1xx/`
* **match วันนี้ = 10 ไฟล์ → มี `TeleportCheckVital` 8 ไฟล์** (v131 ×1, v136 ×1, v137 ×2→1 hit, v138 ×1, v139 ×1, v140 ×1, v141 ×1, v142 ×2→1 hit) — ทั้ง 8 payload `77 44 0B 00 0F 01` = True ตรงกับตารางในรายงาน
* mutable ปน: **ไม่มี** — pattern `GAME_2*` (ขึ้นต้นด้วยปี) ตัด `GAME_LIVE.txt` ออกโดยอัตโนมัติ → **นี่คือรูปแบบที่ควรใช้แทน `GAME_*` ในจุด #1**
* gitignore: ไดเรกทอรีอยู่ **นอก git worktree ทั้งหมด** — ไม่ใช่ "ถูก ignore" แต่ "ไม่มี version control อยู่ตั้งแต่แรก"
* pin: ตาราง 8 แถวใน `PF_TELEPORT_CHECK001_*.md` §4 + prose "wire corpus 8 เฟรม"
* ความเสี่ยงเพิ่มอีกชั้น: `capture_v14[0-9]` จะ **ดูด `capture_v143..v149` ที่ยังไม่เกิด** เข้ามาเองในอนาคต และเมื่อไม่เจอไฟล์เลยโค้ดจะ `print("SKIP wire corpus ...")` แล้ว **ผ่านไปเฉย ๆ** (ไม่ fail) → verifier เขียวได้โดยไม่ได้ตรวจ corpus จริง

### 5. `tests/test_foundation_legacy_seam.py:471` — เกรด C

```python
self.manifests = sorted(REPORTS.glob("*.manifest"))
```

* **match วันนี้ = 63 manifest** · ตรวจแล้ว **tracked ครบ 63 ไฟล์, ถูก ignore 0 ไฟล์**
* แต่ `reports/` เป็น allowlist (`/reports/*` ignore แล้ว `!` ทีละไฟล์) → **manifest ใหม่ใด ๆ จะถูก ignore โดยอัตโนมัติจนกว่าจะเติมบรรทัดใน `.gitignore`** ระหว่างนั้น: git มองไม่เห็น แต่เทสเห็นและพยายาม parse
* assertion ที่ใช้: `assertGreaterEqual(len(self.manifests), 22)` (floor — ปลอดภัย), ต้อง parse ผ่านทุกไฟล์, ต้องมี `.md` คู่, และ `odd == LEGACY_FORMAT_MANIFESTS` (**set เท่ากันเป๊ะ** — manifest แปลกปลอมที่ format เก่าจะทำเทสแดงทันที)
* สรุป: ไม่ pin ตัวเลขลงรายงาน แต่เป็นช่องให้ไฟล์ที่ git มองไม่เห็นมีอำนาจทำ gate แดง/เขียว

### 6. `tools/pf_multiplayer_readiness_audit.py:469` — เกรด C (มียาแล้ว)

```python
def _test_files() -> list[str]:
    directory = os.path.join(ROOT, "tests")
    return sorted("tests/" + name for name in os.listdir(directory) if name.endswith(".py"))
```

* **match วันนี้ = 74 ไฟล์** · `tests/` ไม่ถูก ignore และ untracked = 0
* ตัวเลขไหลไป `tests_total_files`, `tests_total_functions`, `impact_a_closure`, `impact_b_closure` → pin ใน `AUDIT_COUNTS` ของ `PF_MULTIPLAYER_READINESS_AUDIT001_*.md` (`tests_total_files_at_head: 61`, `tests_total_functions_at_head: 663`, closure 29/351 และ 27/320)
* **ยาที่ใส่ไว้แล้ว**: เทสประกาศชัดว่าเลขชุดนี้เทียบด้วย `>=` ("a suite may grow under a concurrent lane; it may not shrink silently") — วันนี้ 74 ≥ 61 จึงยังเขียวทั้งที่ห่างกัน 13 ไฟล์
* เหลือความเสี่ยงเชิงคุณภาพเท่านั้น: เลขในรายงาน (61/663) **ล้าไปแล้ว** เทียบกับต้นไม้จริง — คนอ่านรายงานจะเข้าใจสัดส่วน "53 % ของ suite" ผิด

### 7. `tools/pf_split_operate_verb_panels_static.py:197` + `tests/test_split_operate_verb_panels_static.py:154` — เกรด C

* tool: `models = os.listdir(GUI_MODEL)` → **573 entries** · test: `{p.name.lower() for p in GUI_MODEL.glob("*.model")}` → **534 ไฟล์**
  → **สองตัวใช้ตัวส่วนคนละชุดสำหรับ guard เดียวกัน** (573 vs 534)
* guard คือข้อสรุปเชิงลบ: "ไม่มี model ชื่อที่มี split/divide" — ตรวจวันนี้ match = **0** (จริงตามที่อ้าง) และมี `Common_NumInput.model` จริง
* ไดเรกทอรีอยู่นอก worktree (game asset) — ไม่มี version control, ไม่มี sha pin ใน manifest ของรายงาน
* tool ยัง `print("SKIP ...")` เมื่อหาไดเรกทอรีไม่เจอ (เงียบเหมือนจุด #4) ส่วนเทสจะ error — พฤติกรรมไม่ตรงกันอีกจุด

### 8-13. จุดที่ประเมินแล้ว **ความเสี่ยงต่ำ**

* **8** `tools/deploy_current.ps1:15` — `Get-ChildItem current/ | Where Name -Like "run_v$Version*.bat"` แล้ว `throw` ถ้า count ≠ 1 · `current/` เป็น allowlist แต่ **พังดัง ไม่พังเงียบ** และไม่ pin ที่ไหน
* **9** `tools/build_foundation_release.py:10-12` — `src/**.py` = 32, `migrations/*.sql` = 4, `scenarios/*.json` = 23 · ไม่มีรายงานหรือเทสอ้างถึงไฟล์นี้เลย (grep = ว่าง) · zip ที่ได้เป็น artifact ที่ ignore อยู่แล้ว
* **10** `tools/wait_for_pf_stage.py:40` — `rglob("*.txt")` แล้วกรองเอา **เฉพาะ** `GAME_LIVE`/`GAME_EVENTS_LIVE` · ตั้งใจอ่านไฟล์ mutable โดยตรง แต่ผลใช้แค่รอ stage ไม่ถูก pin
* **11** `src/pirateforce_foundation/store.py:78` — `migrations/[0-9][0-9][0-9]_*.sql` = 4 ไฟล์ · มี checksum ต่อไฟล์ + guard version ซ้ำ + ไดเรกทอรี tracked → นับได้ปลอดภัย
* **12** `tools/pf_hp_death_respawn_static.py:789`, `tools/pf_stats_progression_static.py:1399` — `os.walk(src/pirateforce_foundation)` (32 ไฟล์) · ผลที่ใช้คือ `hits == []` (content negative) ไม่ใช่จำนวน → ไฟล์งอกจะทำให้ guard *เข้มขึ้น* ไม่ใช่เลื่อนตัวเลข
* **13** containment/ownership globs 12 จุดเหนือ `src/pirateforce_foundation/*.py` (tracked, 32 ไฟล์) — assert เป็นรายชื่อโมดูล ไม่ใช่จำนวน:
  `tests/test_channel_message_hypothesis.py:659` · `tests/test_equip_state_static.py:325` · `tests/test_foundation_legacy_seam.py:391` · `tests/test_npc_gait_wire.py:90` · `tests/test_npc_interaction_wire.py:332` · `tests/test_presentation_ownership.py:82` · `tests/test_stats_progression_hypothesis.py:610` · `tests/test_stats_progression_static.py:858` · `tests/test_system_message_wire.py:179` · `tools/verify_hp_death_encoder.py:429` · `tools/verify_stats_progression_encoder.py:254` · `tools/verify_hypothesis_ledger.py:482`

---

## ภาคผนวก A — คำสั่งที่ใช้นับ (รันซ้ำได้)

รันจาก repo root (`Pirate Force ServerProject`) ทุกคำสั่ง

**A-0. บริบท**
```
git --no-optional-locks rev-parse --short HEAD          # 6891372
git --no-optional-locks status --porcelain              # (ว่าง)
```

**A-1. หาจุดที่เป็นโรค**
```
grep -rn --include=*.py -E "glob\.glob|\.glob\(|\.rglob\(|os\.listdir|os\.walk|\.iterdir\(" tools/ tests/ src/ | grep -v __pycache__ | sort
grep -rn --include=*.py -E "os\.scandir|glob\.iglob|fnmatch|listdir" tools/ tests/ src/ | grep -v __pycache__
grep -rn --include=*.ps1 --include=*.psm1 --include=*.sh -E "Get-ChildItem|gci |find " tools/ tests/
```

**A-2. นับ corpus ของ MP-OPT1-B (จุด #1, #2) — จำลอง glob ตรง ๆ**
```
python3 - <<'EOF'
import glob, os, collections
R=os.path.abspath(".")
L=sorted(glob.glob(os.path.join(R,"**","LOGIN_*.txt"),recursive=True))
print("LOGIN glob count:",len(L))                                  # 63
print("by top dir:",dict(collections.Counter(
    os.path.relpath(os.path.dirname(p),R).split(os.sep)[0] for p in L)))  # analysis 4 / backups 59
G=sorted(glob.glob(os.path.join(R,"capture_v141","GAME_*.txt")))
print("GAME_*.txt in capture_v141:",len(G))                        # 69
print("LIVE among them:",[os.path.basename(p) for p in G if "LIVE" in p])
                                       # ['GAME_EVENTS_LIVE.txt','GAME_LIVE.txt']
print("all *.txt in capture_v141:",len(glob.glob(os.path.join(R,"capture_v141","*.txt"))))  # 69
EOF
```

**A-3. ยืนยันตัวเศษ 44 และดูว่าไฟล์ LIVE ติดนับหรือยัง (จุด #1)**
```
python3 - <<'EOF'
import glob,os,re
R=os.path.abspath(".")
def blocks(text):
    out=[]
    for m in re.finditer(r"DECOMPRESSED \d+\n((?:[0-9A-F]{8}  .*\n)+)",text):
        raw=bytearray()
        for line in m.group(1).splitlines():
            for tok in line[10:58].split(): raw.append(int(tok,16))
        out.append(bytes(raw))
    return out
PREFIX=bytes.fromhex("0B6848040000000E000000")   # 0x0B68 + wstring("test" hex-decoded)
G=sorted(glob.glob(os.path.join(R,"capture_v141","GAME_*.txt")))
hits=[os.path.basename(p) for p in G
      if any(PREFIX in b for b in blocks(open(p,encoding="utf-8",errors="replace").read()))]
print(len(G), len(hits), [h for h in hits if "LIVE" in h])   # 69 44 []
EOF
```

**A-4. corpus ของ NAMEID-RESOLVE (จุด #3)**
```
python3 -c "
import glob,os,re
files=sorted(glob.glob('capture_v141/*.txt'))
tup=re.compile(r\"\((\d+),\s*(\d+),\s*'([^']*)'\)\")
named=set();unnamed=set()
for f in files:
    for line in open(f,encoding='utf-8',errors='replace'):
        if 'STRUCTURAL_IDS' in line:
            for m in tup.finditer(line):
                wid,nm=int(m.group(2)),m.group(3)
                (unnamed if nm.startswith('0x') else named).add((wid,nm))
print(len(files),len(named),len(unnamed),sorted(unnamed))"
# 69 7 3 [(6976,'0x1B40'),(14043,'0x36DB'),(44114,'0xAC52')]
grep -c "STRUCTURAL_IDS" capture_v141/GAME_LIVE.txt capture_v141/GAME_EVENTS_LIVE.txt   # 0 / 0
```

**A-5. corpus ของ TELEPORT-CHECK (จุด #4) — รันจาก `<repo>/..`**
```
cd ".."   # C:\Users\Panya\Desktop\Pirate Force
python3 - <<'EOF'
import glob, os, collections
root=os.path.abspath(".")
pats=[os.path.join(root,"GameClient","capture_v13[6-9]","GAME_2*.txt"),
      os.path.join(root,"GameClient","capture_v14[0-9]","GAME_2*.txt"),
      os.path.join(root,"GameClient","capture_v131","GAME_2*.txt")]
files=sorted(sum((glob.glob(p) for p in pats),[]))
hits=[f for f in files if "TeleportCheckVital" in open(f,errors="replace").read()]
print(len(files), len(hits))                                          # 10 8
print(dict(collections.Counter(os.path.basename(os.path.dirname(f)) for f in files)))
print("LIVE among globbed:",[f for f in files if "LIVE" in f])        # []
EOF
```

**A-6. manifest / tests / GUI Model (จุด #5, #6, #7)**
```
ls reports/*.manifest | wc -l                                    # 63
git --no-optional-locks ls-files reports/ | grep -c manifest      # 63  (ignored = 0)
ls tests/*.py | wc -l                                            # 74
git --no-optional-locks ls-files --others --exclude-standard tests/   # (ว่าง)
grep -n "tests_total" reports/PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md
                                                                 # 61 / 663
ls "../GameClient/Data/GUI/Model"/*.model | wc -l                # 534
python3 -c "import os;print(len(os.listdir('../GameClient/Data/GUI/Model')))"   # 573
ls "../GameClient/Data/GUI/Model" | grep -ci "split\|divide"     # 0
```

**A-7. สถานะ gitignore ของทุกไดเรกทอรีเป้าหมาย**
```
for p in capture_v141 backups analysis reports evidence logs derived; do
  printf "%-14s -> " "$p"; git --no-optional-locks check-ignore -v "$p" || echo "NOT IGNORED"; done
# capture_v141 -> .gitignore:157  **/capture*/
# backups      -> .gitignore:1    /*
# analysis     -> .gitignore:1    /*
# reports      -> NOT IGNORED  (แต่ /reports/* ถูก ignore แล้ว allowlist ทีละไฟล์)
# evidence/logs/derived -> .gitignore:1  /*
```

**A-8. writer ที่ป้อนไฟล์เข้าตัวส่วน (v141)**
```
grep -n 'capdir\|LOGIN_{\|GAME_{\|_LIVE.txt' current/pf_login_game_server_v141.py
# 7372: live_path  = capdir / "GAME_LIVE.txt"
# 7373: event_path = capdir / "GAME_EVENTS_LIVE.txt"
# 7401: lp = capdir / f"GAME_{stamp}_{a[1]}.txt"
# 7867: capdir = pathlib.Path("capture_v141")      <-- relative to cwd
# 7945: lp = capdir / f"LOGIN_{stamp}_{addr[1]}.txt"
```

**A-9. ของดีที่ไม่เป็นโรค (ไว้อ้างอิงเวลาออกแบบยา)**
```
grep -n "glob\|listdir\|walk" tools/pf_structural_corpus_audit.py    # (ว่าง — input มาจาก config + sha256)
sed -n '206,213p' tools/pf_delete_refresh001_headless_replay.py      # บังคับ --capture-root นอก repo
```

---

## ภาคผนวก B — ไฟล์ที่แตะในรอบนี้

* เขียนใหม่ 1 ไฟล์: `reports/PF_CORPUS_PIN001_DIRECTORY_SCAN_SURVEY_20260819.md` (ไฟล์นี้)
* ไม่แก้ไฟล์อื่นใดทั้งสิ้น · ไม่แตะ `.gitignore` · ไม่ commit/push/reset/clean/stash · ไม่ลบไฟล์ · ไม่บูต server · ไม่เปิด GameClient · ไม่แตะ canonical DB
* **หมายเหตุถึง chief:** `reports/` ใช้ allowlist ใน `.gitignore` → ไฟล์นี้จะถูก ignore จนกว่าจะมีการเติมบรรทัด `!/reports/PF_CORPUS_PIN001_DIRECTORY_SCAN_SURVEY_20260819.md` ซึ่ง **ลูกมือไม่แตะตามกติกา**
