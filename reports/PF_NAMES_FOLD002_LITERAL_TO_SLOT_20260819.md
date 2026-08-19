# PF NAMES-FOLD-002 — literal → slot evidence for the 327-name candidate registry

**Round 85, lane A · 2026-08-19 · static only (no server, no client UI, no disassembler)**

---

## The answer, first

**273 of the 327 candidate names in `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`
survive the full admission rule of `docs/PF_VITAL_NAMES.json`; 54 do not.**
27 of the 273 were already in the table (and all 27 agreed name-for-name, which is the
independent corroboration that the tsv and the table describe the same binary), so
**246 names were folded in and the table went 52 → 298 entries.**

The tsv had only ever satisfied condition **(a)** of rule (4) — `wire_id(name) == id`.
Condition **(b)** — the name is a unique identifier literal in the client image whose push
sits in the round-62 registration thunk, and *which id-slot that thunk writes* — had never
been checked for any of the 327. That is what this round did, byte-exactly, for all of them.

Every number in this document is re-derived by:

```
python3 tools/pf_vital_name_thunk_static.py            # all guards, exit 0
python3 tools/pf_vital_name_thunk_static.py --list AMBIGUOUS
python3 -m pytest tests/test_vital_names_table.py -q
```

---

## 1. The numbers

| tier | count | meaning |
|---|---:|---|
| **PROVEN** | **273** | unique literal, **exactly one push of it in the whole image**, and that push is a complete registration thunk → carries an `id_slot_va` |
| **AMBIGUOUS** | **37** | literal is pushed from a second, non-thunk site (see §4) |
| **NO_THUNK** | **15** | literal exists, but no thunk anywhere claims it |
| **NO_LITERAL** | **2** | not present as a standalone NUL-terminated identifier literal |
| total | **327** | the tiers partition the candidate table exactly |

Breakdown of the fold:

| | |
|---|---:|
| PROVEN | 273 |
| — of which already in `docs/PF_VITAL_NAMES.json` | 27 |
| — **folded in this round** | **246** |
| `entry_count` before → after | **52 → 298** |
| entries with a non-null `id_slot_va` after the fold | 249 |
| `in_golden_corpus: true` among the 246 | **0** (see §5) |

Supporting counts from the same run:

| | |
|---|---:|
| registration thunks matching the byte template in the whole image | 519 |
| — distinct literals among them / distinct id-slots among them | 519 / 519 |
| — using the `66 89 05` store encoding | 0 (all 519 use `66 A3`) |
| candidates parsed from the tsv | 327 |
| candidates failing condition (a) HASH MATCH | 0 |
| duplicate ids in the candidate table | 0 |

Evidence files this round read (read-only):

| file | size | sha256 |
|---|---:|---|
| `GameClient/GameClient.local.bin` | 14 759 424 | `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` |
| `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` | 11 388 | `B5880451300D28618D3CBD9D835C6F297D4FD0FC48316C1477502561256FCE1F` |

---

## 2. Method — and why there is no disassembler in it

`tools/pf_vital_id_resolve_static.py` proves the same shape with capstone. Round 83 settled
that we do not trust "I swept the whole image" claims from a linear disassembler, and the
bash sandbox has no capstone at all. So `tools/pf_vital_name_thunk_static.py` never decodes
an instruction stream. It parses the PE header for `ImageBase` (`0x00400000`) and the
section table, then looks for **one exact contiguous byte template**:

```
p+0    68 <lit_va:u32>        push   offset <name literal>
p+5    E8 <rel32>             call   0x89C080     (once-init; target computed, must match exactly)
p+10   8B C8                  mov    ecx, eax
p+12   E8 <rel32>             call   0x89BD00     (id-assign; target computed, must match exactly)
p+17   66 A3 <slot:u32>       mov    word ptr [slot], ax
       (or 66 89 05 <slot:u32> — same instruction, other encoding)
then   C3                     ret
```

Call targets are resolved as *(VA of the next instruction) + rel32*, masked to 32 bits.

**Deliberately not accepted** (the rules are written into the tool's header so they can be
argued with rather than discovered): no gaps, padding or NOPs between the steps; no other
call target; no other store width or destination; `ret n` is not accepted, only bare `C3`;
the push must carry the literal's own VA — never "a push near the string".

A *name literal* is the exact ASCII bytes, NUL-terminated, whose **preceding byte is not an
identifier character**. That last clause is what stops `CBuffVital` from matching the tail
of `AVCBuffVital`.

### Acceptance test — the tool proves itself before it is believed

Section `[0]` of the tool re-derives the three ids PF-NAMEID-RESOLVE-001 pinned *with*
capstone in round 62, and refuses to print any other number if it cannot:

| name | id | id-slot the capstone-free matcher found | round-62 pin |
|---|---|---|---|
| `LogoutVital` | `0x1B40` | `0x0108207C` | `0x108207C` ✅ |
| `DeleteActorVital` | `0x36DB` | `0x01081FD0` | `0x1081FD0` ✅ |
| `Channel_LocalTalkMessageVital` | `0xAC52` | `0x01084458` | `0x1084458` ✅ |

A second, unplanned acceptance signal: of the 273 PROVEN rows, 27 landed on ids the table
already held from v141 — and **all 27 carried the identical name**. Two independently
produced artefacts (Codex's v141 NAMES dict and a byte scan of the client) agreeing on 27
(id, name) pairs is a stronger statement about the matcher than any single pin.

---

## 3. What is PROVEN, and what is still only inferred

**PROVEN, byte-exactly, for each of the 246 folded names:**
- the exact characters of the name hash to the declared 16-bit id (condition (a));
- the name occurs exactly once in the image as a standalone identifier literal;
- that literal is pushed from exactly one instruction in the entire image;
- that push is a complete registration thunk of the shape above;
- the thunk stores the assigned 16-bit id into one specific id-slot VA, and no other thunk
  in the image writes that slot (519 thunks, 519 distinct slots).

**NOT proven — do not read these into the table:**
- **that any of these ids was ever seen on the wire.** The pinned golden corpus carries
  exactly **10 distinct wire ids**, all of which the table already held before round 85.
  Every folded entry therefore has `in_golden_corpus: false`, computed from
  `docs/PF_CAPTURE_CORPUS.json` via `tools/pf_capture_corpus.py`, never guessed.
- **that the server must implement them.** A registered class is a class the client can
  construct; it says nothing about frequency, direction or whether the shipped content
  ever reaches it.
- **payload layout for any of them.** This round touched names and slots only.
- **that the id-slot value is the id at runtime.** The slot is *written* by `0x89BD00` at
  static-init time. We read the destination, not the value. (The `0x89BD00` return value is
  what round 62 tied to the hash; that tie is inherited here, not re-proved.)

---

## 4. 🔴 Where our own assumption turned out to be wrong

### 4.1 Rule (4)(b)'s "the SINGLE push of that literal" is an accident of three names

Round 62 wrote the admission rule against `LogoutVital`, `DeleteActorVital` and
`Channel_LocalTalkMessageVital`. Each of those literals happens to be pushed exactly once in
the whole image, so "the single push of that literal sits in the thunk" read as a natural
description of the evidence.

It is not general. **37 candidates have exactly ONE well-formed registration thunk, and are
still not admissible**, because their literal is *also* pushed by a completely different
construct around `0x0042xxxx`:

```
push <lit> ; lea ecx,[esp+N] ; call ds:[0xC3B480]     ; string-table constructor
```

That site touches no id-slot and creates no ambiguity about which slot the name binds to —
but rule (4)(b) as written says *single push*, and **this round did not loosen it to get a
larger number**. The 37 are recorded in tier AMBIGUOUS with the reason
`literal pushed from more than one site`, and the tool pins that sub-count at 37 so it
cannot drift silently. Widening rule (4)(b) is a chief decision and deserves a round of its
own; it would move up to 37 more names (30 of them not yet in the table).

The 37: `CBuffVital`, `ItemLockVital`, `TradeZoomVital`, `CWebGMVital_GSGC`,
`CHitParadeVital`, `CTracePathVital`, `UpdateAttrVital`,
`Community_InitalizeActorCommunityVital`, `StorageOpenVital`, `SelectActorVital`,
`EquipFashionVital`, `Community_CommunityPropertyChangedVital`, `LSCN_LoginVitalReq`,
`LSCN_LoginVitalRes`, `FashionChangeVital`, `Gathering_UpdateSceneGatheringPointVital`,
`ItemOperateVitalRes`, `CStartCooldownVital`, `ServerAddedInfoVital`,
`GSSS_GuildDataVitalRes`, `CLearnSkillResultVital`, `GSSS_GuildEventVitalReq`,
`GSSS_GuildEventVitalRes`, `LSCN_ReloginVerifyVital`, `ItemMallGiftNotifyVital`,
`CHitParadeActorDataVital`, `GSSS_GuildStorageCmdVital`,
`ActorActivity_UpdateDailyActivityStateVital`, `GCSS_GuildStorageOpenVital`,
`GSSS_GuildUpdateEventVital`, `KnowledgeGuru_NewQuizVital`, `GSSS_GSInitialGuildDataVital`,
`DBSS_GuildStorageInitialVital`, `GCGSSS_GuildStorageResultVital`,
`ItemMallUpdatePersonalDataVital`, `UpdateConditionalStoreItemVital`,
`GSSS_GuildUpdateQuestMemberVital`.

### 4.2 The hash alone really is not enough — and now we can show it

A 16-bit hash over 327 names was always going to collide. It does. Among the 249 non-v141
ids the table now holds, **17 have at least one *other* identifier-style string in the image
with the same hash**, several of them obviously unrelated to the wire:

| id | name we admitted | other image identifier with the same hash |
|---|---|---|
| `0x162E` | `CheatVital` | `SyncUpdate` |
| `0x1666` | `Community_SetReceiveActiveChangeVital` | `__iob_func` |
| `0x1FCD` | `CPotionVital` | `LAYER7_UVINDEX` |
| `0x246F` | `RunFxSetVital` | `D3DERR_NOTFOUND` |

Condition (a) on its own would have been a coin flip for these. Condition (b) is what makes
them names instead of guesses — which is the whole reason NAMES-FOLD-002 existed.

### 4.3 The round-62 "unique preimage" sweep has a 48-character blind spot

Round 62's collision bound came from `re.finditer(rb"[\x20-\x7e]{3,48}", data)`. Two of the
folded names are longer than 48 characters (e.g.
`BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital`, 50 chars), so **they are not in that
string set at all** — the sweep would report their own name as *absent* while reporting an
unrelated string (`FORCE_GRAVITY`) as the sole preimage of their id. The new tool does not
use a length-bounded regex sweep; it searches for each candidate's exact bytes.

### 4.4 The tsv is not the complete registry

The image contains **519** registration thunks. The tsv lists 327 candidates, of which 310
have a thunk — so **209 registered classes are not in the tsv at all** (`ActorAttr`,
`BackpackAttr`, `Attribute`, `*Module_Client`, …). Several of them are names v141 already
knows. The tsv's header line ("Non-AV names only") describes a filter that was applied, but
the filter removed more than AV twins. **The tsv is a sample of the registry, not the
registry.** Nothing in the table depends on this; it is recorded so nobody later treats
"327" as "all the names the client has".

---

## 5. `in_golden_corpus` — measured, not assumed

Read through `tools/pf_capture_corpus.py` from the pinned set `game_v141_archived`
(67 archived captures, byte-verified, no strays). Every `STRUCTURAL_IDS` tuple across all 67
files yields exactly **10 distinct wire ids**:

```
named   : 7815 StartGameReq, 14031 CreateActorVital, 14212 LoginVerifyVital,
          15691 GetWorldInfoVital, 17722 GSCN_LoginProtocol, 19437 ItemOperateVitalReq,
          28271 GSCN_RunTimeProtocolReq
unnamed : 6976 (0x1B40), 14043 (0x36DB), 44114 (0xAC52)
```

All ten were already in the table. Hence `in_golden_corpus: false` on all 246 folded
entries, and the tool asserts it rather than trusting the generator.

---

## 6. 🔴 Blocker for the chief — an out-of-scope file must change before the gate is green

`tools/pf_vital_id_resolve_static.py` section `[2]` is **driven by the names table**: it
takes every id in `docs/PF_VITAL_NAMES.json` that v141 does not have, and asserts each one
is a *round-62-style golden-corpus resolution*. That was true when the set was 3 ids. It is
not true of a static fold. With 249 non-v141 ids in the table it will now fail:

| guard in section `[2]` | fails for |
|---|---:|
| `0x…: appears UNNAMED in golden corpus` | **246** of 249 |
| `0x…: unique identifier-style preimage among image strings` | **17** of 249 (see §4.2 / §4.3) |
| thunk shape + slot agreement | 0 (all 249 reproduce) |

No test module imports or runs that tool, so **pytest will not go red** — only the gate's
direct `py -3 tools/pf_vital_id_resolve_static.py` step will. That is itself worth noting: a
verifier with no test around it fails in a place nobody is watching.

That file is **not** in this lane's allowed scope, so it was not touched. The chief needs to
split section `[2]` into "golden-corpus resolutions" (the 3) and "static literal→slot folds"
(the rest) — or delegate the fold check entirely to
`tools/pf_vital_name_thunk_static.py`, which already proves all 249 slots agree with the
binary (`[4]`, `all 249 published id_slot_va values … 0 drift`).

### 6.1 Both new files are currently git-ignored

`.gitignore` is an allow-list (`/tools/*`, `/reports/*` deny everything, then each kept file
is re-included by name). `git check-ignore -v` on the two new files:

```
.gitignore:99:/tools/*     tools/pf_vital_name_thunk_static.py
.gitignore:8:/reports/*    reports/PF_NAMES_FOLD002_LITERAL_TO_SLOT_20260819.md
```

`.gitignore` is chief-only, so it was **not** edited. The two lines the chief needs, next to
the round-62 pair at `.gitignore:219-221`:

```
!/reports/PF_NAMES_FOLD002_LITERAL_TO_SLOT_20260819.md
!/tools/pf_vital_name_thunk_static.py
```

Without them `git status` shows only the two modified files and the commit silently drops
the tool and this report — the exact failure mode CORPUS-PIN-001 was written about.

### 6.2 Stale prose, also out of scope

`docs/COMMAND_HANDOFF.md:42` still says the table holds 52 entries, and
`docs/COMMAND_HANDOFF.md:80` / `docs/AI_TRANSFER_HANDOFF_20260817.md:204` still quote
"43 guards" for the resolve tool.

---

## 7. Available next step, deliberately not taken

38 of the 49 v141-grandfathered entries whose `id_slot_va` is `null` are **PROVEN** under the
same matcher — their slots are sitting there, unrecorded. Filling them in would strengthen
the grandfathered half of the table considerably. It was left alone because this lane's brief
was "add the PROVEN tier of the 327 candidates", and rewriting 38 inherited entries is a
different change that deserves its own review. (`10` of the remaining 11 are AMBIGUOUS by
§4.1, `1` has no literal.)

No `.manifest` was written for this report: `reports/*.manifest` is not in this lane's
allowed file list. The two evidence hashes are pinned inline in §1 instead, and the tool
re-checks the binary sha256 on every run.

---

## 8. Files this round touched

| file | change |
|---|---|
| `tools/pf_vital_name_thunk_static.py` | **new** — capstone-free literal→slot verifier, 4 tiers, all counts pinned as guards, acceptance test first |
| `docs/PF_VITAL_NAMES.json` | +246 entries (52 → 298), `entry_count` updated, `__doc__` (2) COVERAGE rewritten to tell the whole story including why 54 were kept out |
| `tests/test_vital_names_table.py` | 16 → 26 tests: sort/uniqueness, non-v141 entries must carry a slot VA, fold shape and evidence, header-tells-the-story, and four trap tests that watch the validators actually reject a bad table |
| `reports/PF_NAMES_FOLD002_LITERAL_TO_SLOT_20260819.md` | **new** — this document |

Both **new** files are git-ignored until `.gitignore` gains the two allow lines in §6.1.

Not touched, on purpose: `current/pf_login_game_server_v141.py` (frozen),
`GameClient/GameClient.local.bin` (read-only), `state/pirateforce.sqlite3`, the capture
corpus, `.gitignore`, `pf_bridge/LOCK.txt`, `pf_bridge/GAME_TEST_QUEUE.md`,
`pf_bridge/CHIEF_CONTINUATION.md`, and `tools/pf_vital_id_resolve_static.py` (see §6).
No commit was made — the chief commits.
