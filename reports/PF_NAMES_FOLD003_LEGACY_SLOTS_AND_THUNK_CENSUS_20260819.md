# PF NAMES-FOLD-003 — legacy slot VAs, and a census of the 209 classes the tsv never listed

**Round 86 · 2026-08-19 · static only (no server, no client UI, no disassembler, pure stdlib)**

---

## The answer, first

**Half (ก).** The name table had **49** entries inherited from the frozen v141 snapshot with a
null `id_slot_va` — not 38. Run through the *same* matcher, with *neither* condition widened:
**38 clear the rule and now carry the id-slot VA the client binary actually writes; 11 do not
and stay null, with the reason recorded.** The table's `entry_count` is unchanged at 298: this
half admitted no name, it only finished evidencing names the project already had.

**Half (ข).** The image holds **519** registration thunks. The tsv accounts for **310**.
The other **209** are now enumerated with slot VA, wire id and identifier literal — all 209,
none missing a field — in
`reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json`.
**Nothing from the census was admitted to the name table, and the reason is not caution, it is
that rule (4)(a) cannot be applied to them at all** (§4.2). 🔴

**Blind spot.** Exactly **3** identifier literals in the whole image exceed the round-62 sweep's
48-character bound. **2** of them are registered class names; the third is linker padding.
Both class names were already in the table. The blind spot cost the project nothing — by luck.

Re-derive every number here with:

```
python3 tools/pf_vital_name_thunk_static.py                  # halves (ก) is section [5]
python3 tools/pf_vital_name_thunk_static.py --list LEGACY
python3 tools/pf_vital_thunk_census_static.py                # half (ข), checks the artifact
python3 tools/pf_vital_thunk_census_static.py --list
python3 -m pytest tests/test_names_fold003_thunk_census.py -q
```

---

## 1. Half (ก) — the v141-inherited entries

### 1.1 Four buckets, with counts

| tier | count | meaning |
|---|---:|---|
| **PROVEN** | **38** | unique literal, exactly one push of it in the whole image, and that push is a complete registration thunk → now carries `id_slot_va` |
| **AMBIGUOUS** | **10** | exactly one well-formed thunk, but the literal is pushed from a second, non-registration site — fails rule (4)(b) "the SINGLE push" as written |
| **NO_THUNK** | **0** | — |
| **NO_LITERAL** | **1** | `ItemOperateVital` is not in the image as a standalone NUL-terminated literal at all |
| total | **49** | the tiers partition the legacy population exactly |

Condition (a) HASH MATCH holds for all 49 — it always did, and round 86 re-asserts it rather
than assuming it.

Of the 38 PROVEN: **24** are also candidates in the tsv (round 85 had already classified them
PROVEN and simply never wrote the slot back onto a `v141_NAMES` row), and **14** are not in the
tsv at all — they are part of the 209-class remainder of half (ข).

### 1.2 🔴 ERRATUM — the population is 49, not 38

The NAMES-FOLD-003 brief says "38 entries … carry no `id_slot_va`". **38 is the number that
QUALIFIES.** The number that carried no slot was **49** — every `v141_NAMES`-sourced row, which
is also the figure `tests/test_vital_names_table.py::is_v141_sourced` has always documented
("the 49 names grandfathered in from the frozen v141 snapshot") and the figure
`frozen_snapshot.names_entry_count` in the table header carries. Both numbers are now pinned
separately, in the tool and in the test, so they cannot be conflated again.

Nothing published before this round stated "38 entries lack a slot", so there is no earlier
document to correct — only the brief.

### 1.3 The 38 that qualified

| id | name | id-slot VA |
|---|---|---|
| `0x0AD5` | `NPCAttr` | `0x10334A4` |
| `0x0ECD` | `ItemAttr` | `0x1033588` |
| `0x0F01` | `UserSetting_UpdateServerSettingVital` | `0x1088BD0` |
| `0x0FB6` | `ChooseNPC` | `0x1083240` |
| `0x12AD` | `ActorAttr` | `0x10334A0` |
| `0x1890` | `OpenCloseUI` | `0x1082034` |
| `0x1ADD` | `TargetVital` | `0x1082098` |
| `0x1AEA` | `ActionVital` | `0x108A2D8` |
| `0x1E87` | `StartGameReq` | `0x1081FD4` |
| `0x1EB4` | `COnLandVital` | `0x10820A8` |
| `0x1F4F` | `UseItemVital` | `0x1082030` |
| `0x1F81` | `BackpackAttr` | `0x103353C` |
| `0x1FB2` | `TriggerVital` | `0x1082844` |
| `0x2067` | `MovementAttr` | `0x10334A8` |
| `0x23B5` | `TradeCmdVital` | `0x1084AE8` |
| `0x25A2` | `TeleportVital` | `0x1081FF0` |
| `0x2A90` | `TargetPosVital` | `0x1081FE0` |
| `0x300B` | `ActionPickVital` | `0x108A2DC` |
| `0x31D8` | `NPCConversation` | `0x1083248` |
| `0x36CF` | `CreateActorVital` | `0x1081FCC` |
| `0x36D2` | `ShowMessageVital` | `0x1082094` |
| `0x3784` | `LoginVerifyVital` | `0x1081FC0` |
| `0x3BFB` | `ChooseNPCByTableID` | `0x1083244` |
| `0x3D4B` | `GetWorldInfoVital` | `0x1082068` |
| `0x3E34` | `QuestOperateVital` | `0x108324C` |
| `0x3E60` | `ActorInspectVital` | `0x1082078` |
| `0x3EAF` | `MusicControlVital` | `0x1082050` |
| `0x4323` | `StartGameFailVital` | `0x1081FDC` |
| `0x4477` | `TeleportCheckVital` | `0x1082074` |
| `0x453A` | `GSCN_LoginProtocol` | `0x1081C98` |
| `0x4B98` | `CheckSecondPwdVital` | `0x1082044` |
| `0x4BED` | `ItemOperateVitalReq` | `0x1082014` |
| `0x515F` | `UpdateNPCAppearVital` | `0x10898A4` |
| `0x557B` | `TradeItemResultVital` | `0x1084AEC` |
| `0x5D4B` | `CarryableServiceVital` | `0x1082088` |
| `0x6539` | `NotifyEnterCreateActor` | `0x1081FC8` |
| `0x6E6F` | `GSCN_RunTimeProtocolReq` | `0x1081C90` |
| `0x6E9D` | `GSCN_RunTimeProtocolRes` | `0x1081C94` |

Four of these (`ActorAttr`, `BackpackAttr`, `GetWorldInfoVital`, `GSCN_RunTimeProtocolReq`) are
additionally spelled out character-for-character in
`tests/test_names_fold003_thunk_census.py`, so a silent renumber cannot pass on count alone.

### 1.4 The 11 that did not, and why

The "would-be slot" column is **recorded, not admitted**. It is the slot the single well-formed
thunk writes. It is in this table so that a future round that amends rule (4)(b) does not have
to re-derive it — and so that nobody mistakes its absence from the JSON for ignorance.

| id | name | tier | pushes of the literal | would-be slot (NOT admitted) |
|---|---|---|---:|---|
| `0x1E9F` | `StartGameRes` | AMBIGUOUS | 2 | `0x01081FD8` |
| `0x2A7A` | `TradeZoomVital` | AMBIGUOUS | 2 | `0x01084AF0` |
| `0x309A` | `UpdateAttrVital` | AMBIGUOUS | 2 | `0x01082028` |
| `0x369A` | `StorageOpenVital` | AMBIGUOUS | 2 | `0x010862EC` |
| `0x36EF` | `SelectActorVital` | AMBIGUOUS | 2 | `0x01081FC4` |
| `0x36FE` | `ItemOperateVital` | **NO_LITERAL** | 0 | — |
| `0x42BF` | `LSCN_LoginVitalReq` | AMBIGUOUS | 2 | `0x01082344` |
| `0x42E3` | `LSCN_LoginVitalRes` | AMBIGUOUS | 2 | `0x01082348` |
| `0x4C13` | `ItemOperateVitalRes` | AMBIGUOUS | 2 | `0x01082018` |
| `0x536E` | `LSCN_SelectServerReq` | AMBIGUOUS | 2 | `0x0108234C` |
| `0x5396` | `LSCN_SelectServerRes` | AMBIGUOUS | 2 | `0x01082350` |

The 10 AMBIGUOUS rows fail for exactly the reason round 85's 37 did: a second push of the same
literal by the string-table constructor around `0x0042xxxx`. **The matcher was not loosened to
take them.** Admitting them means amending rule (4)(b) on purpose, which is the chief's call.

`ItemOperateVital` is the one genuinely new thing in this list: **the frozen v141 snapshot names
`0x36FE` `ItemOperateVital`, and that string does not exist in the client image as a standalone
literal.** Only `ItemOperateVitalReq` (`0x4BED`) and `ItemOperateVitalRes` (`0x4C13`) do, and
they are separate classes with separate slots. The hash still matches, so the name is not
*wrong* — but it has no literal→slot backing and never will. It stays grandfathered and null.

### 1.5 "Byte-identical apart from the field" — proved, not asserted

`docs/PF_VITAL_NAMES.json` is exactly `json.dumps(obj, indent=1, ensure_ascii=False) + "\n"`;
that was checked *before* touching it, so a re-dump cannot reformat anything. Then:

| | |
|---|---|
| sha256 before | `3179d8e2ead31e54a061beb16531364b7bdbf2d3c913e35a8250beb7907e8ccd` |
| sha256 after | `781d745f6d32e4cb32661c7da96ea76ecb331d0d78ea7fbc95b1412f8bdd98cc` |

* **Structural proof** — entry-by-entry, key order compared list-to-list and every field other
  than `id_slot_va` compared for equality: **0 differences**; `id_slot_va` differs on exactly
  **38** entries.
* **Raw-text proof** — 4793 lines before, 4793 lines after, **38 lines differ**, and every one
  of the 38 old lines is literally `"id_slot_va": null,`. **0** lines outside that shape moved.

`evidence` was deliberately **not** touched, because the brief scoped this half to "only the
additive `id_slot_va` field". 🟡 Consequence for the chief: those 38 rows now publish a slot VA
whose provenance pointer is not in the row. Recommend a one-line follow-up appending
`"tools/pf_vital_name_thunk_static.py section [5] (NAMES-FOLD-003)"` to their `evidence`.
No existing test requires it (the evidence-quotes-the-slot rule is scoped to round-85 rows).

---

## 2. Half (ข) — the 209 classes nobody had looked at

### 2.1 The split, and what the tsv's filter really was

| | count |
|---|---:|
| registration thunks matching the byte template in the image | **519** |
| — literal reachable as a C string / identifier-shaped | 519 / 519 |
| — covered by the tsv | **310** |
| — **the census: not in the tsv at all** | **209** |

🔴 **The tsv's filter is a substring test, and its own header misdescribes it.** The header says
"Non-AV names only (AV* twins are client event-handler/wrapper classes …)". The sets say
something else entirely, and it is now guarded:

* every one of the 327 tsv names contains the substring `Vital` — **0** do not;
* every thunk in the image whose literal contains `Vital` is in the tsv — **310**, all of them;
* **not one** of the 209 census names contains `Vital`;
* **0** of the 209 names begin with `AV`.

So the 310/209 split *is* `"Vital" in name`, exactly. The tsv is the substring slice of the
registry, not a curated one, and the AV-twin story explains none of the 209.

The clearest casualty: **6 registered classes are spelled `...Vtial`** — a typo in the client's
own source — and the substring filter dropped every one of them:
`CNSS_BoardcastToAllActorVtial`, `CNSS_BoardcastToSpecifiedActorVtial`,
`Channel_ForbidTalkNotificationVtial`, `NavigationEx_AddSurveyDataVtial`,
`NavigationEx_RemoveSurveyDataVtial`, `NavigationEx_RequestSurveyVtial`.

### 2.2 What was recovered, for all 209

Every census row carries **slot VA, 16-bit wire id, and the identifier literal** — 209/209, no
partial rows. Additionally: slot VAs are distinct across all 209, wire ids are distinct across
all 209, and **0** census wire ids collide with a tsv candidate id.

Shape of the remainder:

| shape | count | examples |
|---|---:|---|
| `*Attr` / `*Attribute` | 52 | `ActorAttr`, `BackpackAttr`, `FightAttr`, `ItemBagAttr_Equiped`, `Attribute` |
| `*Module` / `*Module_Client` | 76 | `QuestModule`, `CSkillModule`, `TradeModule`, `PetsModule` |
| `*Res` / `*Reply` | 9 | `StartGameRes`, `GSCN_BlackMarketReply`, `ItemMallBagOpenRes` |
| `*Req` | 6 | `StartGameReq`, `LSCN_SelectServerReq`, `InstanceChooseRewardReq` |
| `...Vtial` (client typo) | 6 | see above |
| other | 60 | `CHitResult`, `PcProtocol`, `ForcePos`, `CWarpResult`, `PetsData`, `TriggerResult` |

Slot VAs span `0x01033458`–`0x0109B834`, the same table as everything else — the `*Attr` block
sits at the low end (`0x0103xxxx`), which is why no `Attr` name was ever near the tsv's range.

**17 of the 209 already have a name in `docs/PF_VITAL_NAMES.json`**, all from v141, and all 17
agree id-for-id with what the census derives. That agreement is the census's only independent
corroboration, and it is worth stating plainly: for these 17 the id came from v141, not from
the literal, so it is a real cross-check.

| id | name | id-slot VA |
|---|---|---|
| `0x0AD5` | `NPCAttr` | `0x010334A4` |
| `0x0ECD` | `ItemAttr` | `0x01033588` |
| `0x0FB6` | `ChooseNPC` | `0x01083240` |
| `0x12AD` | `ActorAttr` | `0x010334A0` |
| `0x1890` | `OpenCloseUI` | `0x01082034` |
| `0x1E87` | `StartGameReq` | `0x01081FD4` |
| `0x1E9F` | `StartGameRes` | `0x01081FD8` |
| `0x1F81` | `BackpackAttr` | `0x0103353C` |
| `0x2067` | `MovementAttr` | `0x010334A8` |
| `0x31D8` | `NPCConversation` | `0x01083248` |
| `0x3BFB` | `ChooseNPCByTableID` | `0x01083244` |
| `0x453A` | `GSCN_LoginProtocol` | `0x01081C98` |
| `0x536E` | `LSCN_SelectServerReq` | `0x0108234C` |
| `0x5396` | `LSCN_SelectServerRes` | `0x01082350` |
| `0x6539` | `NotifyEnterCreateActor` | `0x01081FC8` |
| `0x6E6F` | `GSCN_RunTimeProtocolReq` | `0x01081C90` |
| `0x6E9D` | `GSCN_RunTimeProtocolRes` | `0x01081C94` |

🟡 **Trap, flagged on purpose:** three of those rows — `StartGameRes`, `LSCN_SelectServerReq`,
`LSCN_SelectServerRes` — are AMBIGUOUS under half (ก) and their `id_slot_va` in the name table
is deliberately **null**, yet the census artifact prints a slot VA for them. That is not a
contradiction: the census reports what the thunk writes, the table reports what the admission
rule admits, and they are different questions. **The census must never be used as a back door
to fill those three in.** The test asserts they stay null.

### 2.3 🔴 Nothing was admitted — and the reason is structural, not timid

**0 of the 209 were added to `docs/PF_VITAL_NAMES.json`.** 192 of them carry names the table has
never held. Every one satisfies condition (4)(b) *by construction* — it is a thunk. The problem
is (4)(a):

> (a) HASH MATCH — `wire_id(name) == id`

That is evidence **only when `id` comes from somewhere other than the name.** The tsv's ids came
from an independent string sweep. v141's ids came from the frozen snapshot. In both cases the
agreement meant two sources agreed. For a class discovered from its own literal there is no
second source: its id can only be computed as `wire_id(name)`, so (a) is true by definition and
carries zero information.

Admitting the 192 would therefore not be *applying* rule (4); it would be *changing what (4)(a)
means* — and doing so would let in 192 names on strictly weaker evidence than the 37 + 10
AMBIGUOUS rows that are currently kept out. **That is a chief decision, in a round of its own.**
This lane admitted nothing and the artifact says so in its own header.

For what it is worth, the recommendation: these 192 are *better* evidenced as class names than
anything the hash alone ever produced — the binary registers each of them under that exact
spelling. What they lack is any claim to have been seen on the wire. A separate provenance
value (e.g. `source: "client-registry census"`, `in_golden_corpus: false`, no claim of (a)) would
be the honest way in, if the chief wants them.

### 2.4 The artifact

`reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json` — 71 KB, JSON,
`indent=1`, LF, one object per class:

```json
{"name": "ActorAttr", "literal_readable": true, "literal_is_identifier": true,
 "literal_va": "0x00F0E82C", "thunk_va": "0x00BD93D0", "id_slot_va": "0x010334A0",
 "wire_id": "0x12AD", "wire_id_dec": 4781, "shape": "Attr",
 "in_names_table": true, "longer_than_round62_sweep": false}
```

plus `counts`, `binary` (path + sha256 + ImageBase), `round62_sweep_blind_spot`, and
`"admitted_to_names_table": 0`. Its `__doc__` opens with **"THIS IS NOT A NAME TABLE"**, and the
tool re-derives the whole file on every run and fails if the committed bytes differ — so the
artifact cannot drift away from the binary without turning the suite red.

---

## 3. The 48-character blind spot, measured instead of bounded

Round 62's sweep was `re.finditer(rb"[\x20-\x7e]{3,48}", data)`. A printable run longer than 48
bytes is chopped into a 48-byte token and a remainder, so a longer name never appears in that
string set as itself.

**Exactly 3** standalone NUL-terminated identifier literals in the whole image exceed 48
characters:

| length | VA | identifier | is it a class? |
|---:|---|---|---|
| 51 | `0x00F3BA20` | `BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital` | **yes** — registered, in the table |
| 49 | `0x00F3B3FC` | `Equipment_RefreshLuckyEnhancementProbabilityVital` | **yes** — registered, in the table |
| 107 | `0x010F4995` | `PADPADDINGXXPADDINGPADDINGXX…` | no — linker filler |

So: **2 vital/attr-style class names exceed the bound, and both are already in the table.** No
third name is hiding behind that regex. Round 85's "at least 2" is now closed at exactly 2.

(For completeness: 1944 *printable runs* of any kind exceed 48 bytes — paths, format strings,
XML. Only 3 of them are identifier-shaped. The identifier count is the one that mattered.)

### 3.1 🔴 ERRATUM to `PF_NAMES_FOLD002_LITERAL_TO_SLOT_20260819.md` §4.3

That document says `BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital` is **50 chars**. It is
**51**. The conclusion it supported is unaffected (>48 either way), and the old number is left
in place per project practice — this is the correction.

---

## 4. What contradicts, or sharpens, something already published

1. **"38 legacy entries lack a slot"** (task brief) → the population is **49**; 38 is how many
   qualify. §1.2.
2. **`BuildingCrystal_IncreaseCrystalSlotMaxNutrientVital` is 50 chars** (FOLD-002 §4.3) → **51**.
   §3.1.
3. **"The tsv's header line ('Non-AV names only') describes a filter that was applied, but the
   filter removed more than AV twins"** (FOLD-002 §4.4) → correct, and now exact: the filter is
   `"Vital" in name`, nothing else. 0 of the 209 begin with `AV`. §2.1.
4. **"at least 2 longer names escaped the string set"** (round 85) → exactly **2**, and both were
   already in the table. §3.
5. **`ItemOperateVital` (0x36FE)**, a name v141 has always carried, has **no standalone literal
   in the client image**. Not previously stated anywhere. §1.4.
6. **6 registered classes are misspelled `Vtial` in the client's own source** and are therefore
   absent from every name list the project has ever had. Not previously stated. §2.1.

Nothing here contradicts a *verified-state* claim in `MEMORY.md`.

---

## 5. 🔴 Blocker for the chief — `.gitignore` must change before these files can be committed

`.gitignore` uses `/tools/*` and `/reports/*` with per-file `!` whitelists. `git check-ignore -v`
says both new files are currently **ignored**:

```
.gitignore:99:/tools/*     tools/pf_vital_thunk_census_static.py
.gitignore:8:/reports/*    reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json
```

`.gitignore` is on this lane's do-not-touch list, so the chief must add:

```
!/reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.md
!/reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json
!/tools/pf_vital_thunk_census_static.py
```

`tests/**` is already whitelisted, so `tests/test_names_fold003_thunk_census.py` is fine, and
`tools/pf_vital_name_thunk_static.py` + `docs/PF_VITAL_NAMES.json` are tracked already.
Per the project rule, this is a seam-touching edit: run the seam test before that commit.

---

## 6. Tooling — why one file was extended and one was added

`tools/pf_vital_name_thunk_static.py` gained section **[5]** and the constants for half (ก).
That is the same question the file already answers (does this name clear the rule?), asked of a
different list, so it belongs there — and its section [0] acceptance gate still runs first and
still reproduces `LogoutVital → 0x0108207C`, `DeleteActorVital → 0x01081FD0`,
`Channel_LocalTalkMessageVital → 0x01084458` before anything else is printed. The acceptance
loop was factored into `run_acceptance()`; it is unchanged in behaviour.

Half (ข) went into a **sibling**, `tools/pf_vital_thunk_census_static.py`, for two reasons:
it must *write* an artifact (the admission verifier reads and asserts and writes nothing — that
is a property worth keeping), and it answers a question the admission rule structurally cannot
answer (§2.3). The sibling **imports** `Image`, `run_acceptance` and `load_candidates` from the
gate tool, so there is exactly one copy of the byte template and one acceptance gate in the
project; the sibling refuses to print a census row until that same gate passes. A test asserts
both facts — the shared origin of the symbols, and that the sibling's source contains no second
copy of the opcode template.

**Guard counts:** thunk tool **41** guards, of which **15** are the new section [5] (so 26
before); census tool **31** guards. Both exit 0.

---

## 7. Tests, honestly

```
python3 -m pytest tests/test_names_fold003_thunk_census.py -q
    18 passed, 1002 subtests passed
python3 -m pytest tests/test_names_fold003_thunk_census.py tests/test_vital_names_table.py \
                  tests/test_vital_id_resolve_scope.py -q
    53 passed, 5 skipped, 1617 subtests passed
```

The 5 skips are pre-existing, in `tests/test_vital_id_resolve_scope.py::ToolRunTests`, and are
`capstone`-not-installed skips. Nothing in NAMES-FOLD-003 skipped.

**What was NOT run here, and why.** The full suite could not be completed in this sandbox: 18
test modules fail *collection* with `ModuleNotFoundError: capstone` / `pefile` (pre-existing —
neither new file imports either), and a whole-suite run exceeds the sandbox's per-command time
cap. **The real gate is Windows `py -3`, and these numbers are not a substitute for it.** Both
new tools and the new test are pure stdlib and have no import that could fail there.

The new test runs both verifiers **for real** via `subprocess` and asserts exit 0, absence of
any `FAIL` line, the three acceptance pins, and the section-[5] counts — and separately
re-states the load-bearing numbers from the table and the artifact so that the tool and the test
have to agree. If the client image is absent, `ToolRunTests` skips loudly with the reason in the
message; the table and artifact classes always run.

---

## 8. Files touched

| file | change |
|---|---|
| `tools/pf_vital_name_thunk_static.py` | + `run_acceptance()`, `is_v141_sourced()`, section [5], legacy pins, `--list LEGACY`, [4] lookup fix |
| `tools/pf_vital_thunk_census_static.py` | **new** — half (ข) verifier + artifact emitter |
| `docs/PF_VITAL_NAMES.json` | 38 `id_slot_va` values, nothing else (§1.5) |
| `reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.md` | **new** — this file |
| `reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.json` | **new** — the 209-class census |
| `tests/test_names_fold003_thunk_census.py` | **new** — runs both tools for real, pins both halves |

Not touched: `current/pf_login_game_server_v141.py`, `state/`, `references/`, `evidence/`,
`.gitignore`, `pf_bridge/*`, the tsv. No commit, no server, no client UI.
