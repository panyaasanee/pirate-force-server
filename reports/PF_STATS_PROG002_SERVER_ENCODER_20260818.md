# PF_STATS_PROG002 — the server can now put level, experience and the five ability values on the wire: a generic mask-gated `ActorAttr` encoder behind `UpdateAttrVital 0x309A`, proven offline against the one projection a real client has already accepted, and driven end to end through the real dispatcher — headless, opt-in, no client, no TCP

2026-08-18 · chief assistant (single-scope task) · milestone `character_management / stats_and_progression` (`in_progress`, **not** moved) · ledger **HYP-PF-020 appended (26 → 27)** · reproduce: `py -3 tools/verify_stats_progression_encoder.py` (85 guards, exit 0) + `py -3 -m pytest tests/test_stats_progression_hypothesis.py tests/test_stats_progression_dispatch.py -q` (64 tests)

Goal: unblock **GT-017** — *does the XP bar / level number / ability row on screen move when the server says so?* — by making the server able to say so at all. STATS-PROG-001 (round 76) proved every field byte-exactly and measured the gap: **19 named progression fields, 2 emitted** (the HP pair), **0 decoded**. This milestone moves the field half of that gap and nothing else, **without touching v141 (immutable), without touching the canonical DB, without booting a server, without opening GameClient, without any network**, and **without claiming anything about the ORIGINAL server**.

> **Headline results:**
> - **A generic, mask-driven `ActorAttr` encoder exists**, `src/pirateforce_foundation/stats_progression_hypothesis.py`: `(identity, {field: value}) -> sparse mask-gated body`, 23 implemented fields across the three chained blocks, fields emitted in **ascending mask-bit order**, plus the matching decoder.
> - **The encoder is not self-certified.** For the baseline field set it reproduces `player_wire.make_actor_attr_with_name` — a hand-written, field-by-field projection that has been in front of a real client since NAME-002 — **byte for byte, all 73 bytes**, for the pinned probe and for three unrelated identity/scene/name triples. Two independent code paths agreeing on every byte is what rules out a wrong tag, a wrong width, a wrong block boundary or an inverted field order.
> - **The field order is read off the report, not assumed.** STATS-PROG-001 §4/§5 record a gate-pin address for every gated field; in both tables those addresses **ascend strictly with the mask bit**. A linear serializer emits in code order, so ascending address is ascending emission order, and ascending mask bit is therefore the wire order. Both the module and the verifier re-check the pins so the argument cannot silently invert.
> - **The lane is wired to the wire.** A new opt-in scenario `scenarios/stats_progression_hypothesis_xp_sweep.json`, a new CLI flag `--stats-progression-hypothesis-scenario` (explicit existing `--db` required, mutually exclusive with every other mode), and a dispatch branch under the scenario gate: one accepted chat-input frame produces **nine `UpdateAttrVital 0x309A` frames** — baseline, experience #1, experience #2, level, then STR/CON/DEX/INT/PER one at a time — **3.0 s apart**, cumulative, composed and pinned before any of them is queued.
> - **Proven on dispatched bytes, not on a fixture:** nine actions in the pinned order, every frame carrying vital `0x309A` and an `ActorAttr` collection, every Attr body at the fixed envelope offset **re-decoding to exactly the declared cumulative field set**, all **27 per-step hashes** (body / PC / frame) matching the scenario pins, eighteen frames for two requests with no accumulated state, the database file **byte-identical** across accepted and refused windows, and every fail-closed family silent with a named event.
> - **Nothing was proven at the client layer.** No client has seen one of these frames; nothing in this project has ever seen a progression field on a wire in either direction. That is exactly GT-017.
>
> **Grade:** encoder + decoder + independent byte-exact cross-check + dispatcher-level wire proof = **B** (headless; the composition is a *designed* hypothesis on grade-A static field evidence) · **runtime/client behaviour = not claimed** · net: `character_management/stats_and_progression` stays **`in_progress`** and gains this milestone's evidence and test refs; it does **not** move to `runtime_pass`.

---

## 1. What the encoder is

`encode_actor_attr(legacy, identity_lo, identity_hi, fields)` builds the chain base first, exactly as STATS-PROG-001 §2 read it:

```
DBAttribute   u8 mask (tag 0x0B) = 0x01, then the identity qword (tag 0x32)
BasicAttr     u16 mask (tag 0x12), then every set field, ascending bit
ActorAttr     64-bit mask (tag 0x32), then the u8 extra-group flag
              (tag 0x05, value 1), then every set field, ascending bit
```

23 fields are implemented. Every one carries its own evidence string naming the report section and the gate pin:

| field | block | mask bit | offset | tag | width | evidence (STATS-PROG-001) |
|---|---|---|---|---|---|---|
| `level` | BasicAttr | `0x0002` | `+0x5E` | `0x12` | u16 | §4 gate `0x465736`; `GetLv` handler `0x460050` |
| `hp_current` | BasicAttr | `0x0004` | `+0x44` | `0x14` | u32 | §4 gate `0x46574A` |
| `hp_max` | BasicAttr | `0x0008` | `+0x48` | `0x14` | u32 | §4 gate `0x46575E` |
| `mp_current` | BasicAttr | `0x0010` | `+0x4C` | `0x14` | u32 | §4 gate `0x465772`; `PROGRESSBAR_MP` `0x53F1AD` |
| `mp_max` | BasicAttr | `0x0020` | `+0x50` | `0x14` | u32 | §4 gate `0x465786`; column `n_STAMINAMAX` |
| `scene_id` | BasicAttr | `0x0100` | `+0x5C` | `0x12` | u16 | §4 gate `0x4657C2` |
| `scene_sequence` | BasicAttr | `0x0200` | `+0x60` | `0x32` | qword | §4 gate `0x4657E3` |
| `class_id` | ActorAttr | `0x00000001` | `+0x8C` | `0x19` | u32 | §5 gate `0x466299`; `GetClass` `0x460160` |
| `skill_points` | ActorAttr | `0x00000008` | `+0x7C` | `0x19` | u32 | §5 gate `0x4662EC`; `NUMBERLABEL_SPNOW` `0x75C613` |
| `unspent_ability_points` | ActorAttr | `0x00000010` | `+0x80` | `0x12` | u16 | §5 gate `0x466304`; spinner cap `0x57DD7A` |
| `ability_str` | ActorAttr | `0x00000020` | `+0x82` | `0x12` | u16 | §5 gate `0x46631F`; getter `0x467A60` → `LABEL_STR` |
| `ability_con` | ActorAttr | `0x00000040` | `+0x84` | `0x12` | u16 | §5 gate `0x46633A`; getter `0x467AF0` → `LABEL_CON` |
| `ability_dex` | ActorAttr | `0x00000080` | `+0x86` | `0x12` | u16 | §5 gate `0x466355`; getter `0x467B80` → `LABEL_DEX` |
| `ability_int` | ActorAttr | `0x00000100` | `+0x88` | `0x12` | u16 | §5 gate `0x466370`; getter `0x467CA0` → `LABEL_INT` |
| `ability_per` | ActorAttr | `0x00000200` | `+0x8A` | `0x12` | u16 | §5 gate `0x46638A`; getter `0x467C10` → `LABEL_PER` |
| `experience` | ActorAttr | `0x00000400` | `+0xA0` | `0x32` | qword | §5 gate `0x4663A8`; XP bar `0x519299`/`0x5192C6` |
| `cash` | ActorAttr | `0x00000800` | `+0xA8` | `0x32` | qword | §5 gate `0x4663C6`; `GetCash` `0x4600AC` |
| `ability_bonus_str` | ActorAttr | `0x00040000` | `+0x182` | `0x12` | u16 | §5 gate `0x466490` |
| `ability_bonus_con` | ActorAttr | `0x00080000` | `+0x184` | `0x12` | u16 | §5 gate `0x4664AE` |
| `ability_bonus_dex` | ActorAttr | `0x00100000` | `+0x186` | `0x12` | u16 | §5 gate `0x4664CC` |
| `ability_bonus_int` | ActorAttr | `0x00200000` | `+0x188` | `0x12` | u16 | §5 gate `0x4664EA` |
| `ability_bonus_per` | ActorAttr | `0x00400000` | `+0x18A` | `0x12` | u16 | §5 gate `0x466508` |
| `character_name` | ActorAttr | `0x01000000` | `+0x164` | `0x48` | wstring | **derived, not a report pin — see §3** |

## 2. Why "ascending mask bit" is the field order and not a guess

The task allowed this to be recorded as an assumption. It is not one, and here is why.

STATS-PROG-001 §4 lists, for each of the twelve `BasicAttr` fields, the address of the mask test that gates it: `0x465727`, `0x465736`, `0x46574A`, `0x46575E`, `0x465772`, `0x465786`, `0x46579A`, `0x4657AE`, `0x4657C2`, `0x4657E3`, `0x465804`, `0x465825` — for bits `0x0001` through `0x0800` in order. §5 does the same for `ActorAttr`: `0x466299`, `0x4662EC`, `0x466304`, `0x46631F`, `0x46633A`, `0x466355`, `0x466370`, `0x46638A`, `0x4663A8`, `0x4663C6`, then `0x466490`…`0x466508` — for bits `0x1` through `0x400000` in order. In both tables **the gate address ascends strictly with the mask bit value**. `BasicAttr::Serialize 0x4656F0` and `ActorAttr::Serialize 0x466230` are linear serializers, so they emit in code order; ascending code address is therefore ascending emission order, and ascending mask bit is the wire order.

`_require_ascending_gate_pins()` re-checks that property on every call, and the verifier checks it as its own guard. If a future correction to the report reordered a pin, this lane would fail loudly instead of quietly emitting a scrambled body.

The order is additionally *confirmed on bytes* by §3: `player_wire`'s hand-written projection emits HP-cur, HP-max, scene-id, scene-seq, then cash, then name — which is exactly ascending bit order in both blocks — and the generic encoder reproduces it byte for byte.

## 3. The one bit that is a derivation, stated as such

STATS-PROG-001 §5 names `ActorAttr +0x164` as the persisted player-name wstring but gives it **no gate address**. Its mask bit is derived here, not transcribed: the mask v141 and `player_wire` have had on the wire since NAME-002 is `0x01000800`, whose only two bits are cash `0x00000800` (report-pinned) and one other, and the field emitted after the cash qword is the name wstring. Therefore the name bit is `0x01000000`. That is a two-line derivation from bytes a real client has accepted, and the module records it in the field's own evidence string as `derived:` rather than pretending it is a report pin. A test and a verifier guard both assert that `name_bit | cash_bit == 0x01000800`, so the derivation cannot rot silently.

## 4. The independent cross-check — this is the load-bearing evidence

`player_wire.make_actor_attr_with_name` is written field by field, by hand, and its output has been accepted by a real GameClient since NAME-002 (and is the `ActorAttr` every `start_game` carries today). `stats_progression_hypothesis.encode_actor_attr` is written mask by mask and knows nothing about it. For the baseline field set

```
hp_current=100, hp_max=100, scene_id=<actor>, scene_sequence=<actor>,
cash=legacy.V116_INITIAL_CASH, character_name=<actor>
```

the two produce **the same 73 bytes**:

```
0b01 32 0100011000000000 120c03 14 64000000 14 64000000 12 0100
32 0000000000000000 32 0008000100000000 0501 32 1027000000000000
48 0c000000 74 00 65 00 73 00 74 00 30 00 31 00
```

`_require_player_wire_crosscheck` runs this on **every** composition, so the lane cannot drift away from the proven projection at runtime, not just in tests. The verifier repeats it for three further identity/scene/name triples including the all-ones identity.

## 5. The sweep GT-017 will drive

Nine frames, one on-screen change each, cumulative, 3.0 s apart:

| # | action label | new field | value | attr body | PC | frame |
|---|---|---|---|---|---|---|
| 1 | `HYP_PF_020_STATS_PROG_BASELINE` | — | — | 73 B | 106 B | 117 B |
| 2 | `HYP_PF_020_STATS_PROG_EXPERIENCE_1` | `experience` | 1234 | 82 B | 115 B | 126 B |
| 3 | `HYP_PF_020_STATS_PROG_EXPERIENCE_2` | `experience` | 987654 | 82 B | 115 B | 126 B |
| 4 | `HYP_PF_020_STATS_PROG_LEVEL` | `level` | 7 | 85 B | 118 B | 129 B |
| 5 | `HYP_PF_020_STATS_PROG_ABILITY_STR` | `ability_str` | 11 | 88 B | 121 B | 132 B |
| 6 | `HYP_PF_020_STATS_PROG_ABILITY_CON` | `ability_con` | 22 | 91 B | 124 B | 135 B |
| 7 | `HYP_PF_020_STATS_PROG_ABILITY_DEX` | `ability_dex` | 33 | 94 B | 127 B | 138 B |
| 8 | `HYP_PF_020_STATS_PROG_ABILITY_INT` | `ability_int` | 44 | 97 B | 130 B | 142 B |
| 9 | `HYP_PF_020_STATS_PROG_ABILITY_PER` | `ability_per` | 55 | 100 B | 133 B | 145 B |

Three design decisions worth stating, because each is a choice and not a proof:

1. **Frame 1 changes nothing.** It is the exact `ActorAttr` the client already received at `start_game`, re-sent through `UpdateAttrVital`. If the client's XP bar / level / ability rows move on frame 1, the transport itself is doing something unexpected and GT-017 learns that before any progression value is involved.
2. **Every frame is cumulative.** v141's own docstring on `make_update_attr_cash_only` records that the client's `ActorAttr` apply `0x464F30` **copies the complete object**, so a field dropped from a later delta is reset rather than left alone. A bare two-field delta would therefore blank the name, HP and scene on arrival. Every frame here carries the full baseline plus every change so far; the encoder is still a *sparse* mask-gated encoder, but this lane never uses it to ship a bare delta.
3. **The five ability values are distinct multiples of eleven** (11/22/33/44/55) and go out one frame at a time. If `LABEL_STR` shows 22, the offset-to-label binding STATS-PROG-001 §6 proved statically is off by one, and the attended tester can see that at a glance instead of inferring it.

The request side is the **same accepted 34-byte ascii12 chat-input frame** the HYP-PF-014 lane classifies. That is deliberate: it is the only client action an attended tester can trigger on demand, and reusing it means every guard on the path (`ascii12` shape, envelope, `selected`, `teleport_sent`, `runtime_ack_sent`) is one the project has already proven. **Nothing in the request is read** — a test asserts that three different accepted payloads produce byte-identical sweeps. The request is a trigger, not an input.

## 6. What was proven on dispatched bytes (`tests/test_stats_progression_dispatch.py`, 22 tests)

- one accepted trigger → exactly **nine** actions, in the scenario's declared label order;
- every frame carries `pc[16:18] == 0x309A` and a `u16tag(0x12, 0x12AD)` `ActorAttr` collection;
- the Attr body at the fixed offset `20 + 11 = 31` **re-decodes** to exactly the cumulative field set that step declares — the last frame decoding to `level=7`, `experience=987654`, `STR/CON/DEX/INT/PER = 11/22/33/44/55`;
- the baseline frame's body is byte-identical to `make_actor_attr_with_name` for the character the harness actually created;
- all 27 per-step hashes match the scenario pins **and** the module pins, independently;
- delays are `[0.0, 3.0 × 8]`, summing to 24.0 s on the frozen sender's cumulative deadline;
- two requests → eighteen frames, identical to each other, `sweep_count == 2`, no accumulated state;
- the database file is byte-identical across accepted and refused windows, and the session lease is never closed;
- fail-closed: wrong length (×4), wrong prefix, wrong text bytes (×3), wrong envelope (×3), not-yet-runtime-ready, no selected character — each returns `[]` with its own named event and never emits a sweep event;
- with no scenario the branch does not exist: zero `HYP_PF_020` actions, zero `stats_progression` events, `rx_frames` +1 exactly as the GT-006 baseline, database unmoved;
- the lane refuses to coexist with the chat-input, channel-message and logout scenarios (`mutually exclusive`), and refuses any scenario object outside the allowlist.

## 7. What was proven offline (`tests/test_stats_progression_hypothesis.py`, 42 tests)

Field table equals the report's table for all 23 fields; ascending-bit emission order in both blocks; gate pins ascend with the bits; the one derived bit declares itself; unimplemented bits are declared rather than silently missing; the `player_wire` cross-check for the probe and three other actors; every field round-trips through the decoder alone and all together; body bytes do not depend on the order the caller passed the dict; the envelope geometry, the vital id and the `frame_pc` relationship; the nine pinned steps; cumulativeness; determinism; and eight rejection families (unknown name, wrong type including `bool`, out-of-range, unencodable/empty name, bad identity, non-dict field set, damaged body, unimplemented mask bit in a decoded body).

## 8. Containment — what moved and why

- **`tests/test_presentation_ownership.py`: unchanged.** The new module never spells the chat vital id: it imports `CHAT_INPUT_VITAL_ID` by name in `runtime.py`, which was already on that allowlist. The allowlist stays at three modules.
- **`tools/pf_stats_progression_static.py` / `tests/test_stats_progression_static.py`: unchanged, and still green.** Their `src/` guard asserts that no Foundation module names any of the five progression **verbs**. This milestone implements the **delta pipe only** and names none of them — a containment test in the new suite asserts that on the module's own source, so the static milestone's "5 verbs, 0 encoders, 0 dispatch" statement stays literally true.
- **`tests/test_foundation_legacy_seam.py::GRADE_SUBSET_SHA256`: moved, deliberately.** `docs/FUNCTIONAL_COVERAGE.json` gains evidence and test refs on `character_management/stats_and_progression` (status unchanged), which is a graded field, so the digest had to move. Previous pin `B6002E45..E1F3` (round 77).
- **`tools/verify_hypothesis_ledger.py`: moved, deliberately.** `EXPECTED_IDS` and `EXPECTED_META` gain `HYP-PF-020` and `CANONICAL_CONTENT_SHA256` is recomputed, because the ledger grew by one appended entry (26 → 27). Every existing entry index is unchanged.
- **No other lane's module, scenario or test was touched.**

## 9. Explicit non-claims

- **Nothing about the ORIGINAL server.** No progression rule, no XP formula, no allocation validation, no level-up policy is claimed to be what any server ever did. The composition is a *designed* hypothesis on grade-A static field evidence.
- **No client has seen any of this.** Nothing in this project has ever observed a progression field on a wire in either direction, inbound or outbound. Whether the XP bar moves, whether the level number updates, whether the ability rows re-read, whether the client accepts nine `UpdateAttrVital` frames in 24 seconds without coalescing or erroring — all unmeasured, all GT-017.
- **Not driven over real TCP.** Like CHAT-CHANNEL-003 and unlike CHAT-ECHO-002, this lane has been proven through the dispatcher on a temp database only. No server process was started.
- **The on-screen XP percentage cannot be predicted.** The XP bar divides the value by `STANDARD_STATUS[level+1].n_EXP_CURRENTLV`, and those numbers live in **external static data**, not in the executable (STATS-PROG-001 §8.4). GT-017's observable is *whether the bar moved between frame 2 and frame 3*, not *that it reached N %*. `experience = 987654` may well clamp the bar at full or overflow it; either outcome is informative and neither is predicted here.
- **Sparse-delta semantics are not claimed.** Whether a frame that omits a field leaves that field alone on the client is exactly what v141's note on `0x464F30` says it does **not** do. This lane never tests the question because every frame is cumulative; the encoder can emit a bare delta, and doing so is unproven and discouraged.
- **The extra-group flag is reproduced, not understood.** `u8 tag 0x05 = 1` at `+0x1BC` is the value v141 has always sent with a zero high mask dword. What it would mean set differently, and what the high half of the 64-bit mask gates, is not claimed — every high-half bit is refused by construction.
- **The five progression verbs have no encoder here.** `AbilityDepoly*`, `CLearnSkill*` and `CRevertSkilt*` are untouched, in v141 and in `src/`.
- **The `POTENTIAL` column-to-offset binding stays unclaimed**, exactly as STATS-PROG-001 left it; the ability field *names* used here are the UI-label names (`LABEL_STR`…`LABEL_PER`), which is what the report proved.
- **No persistence.** Progression has no table and this lane opens none; `database_write` is `none` and the database file is proven byte-identical across a whole sweep window.
- **No `runtime_pass`.** The matrix row stays `in_progress`.

## 10. Files

Created: `src/pirateforce_foundation/stats_progression_hypothesis.py`, `scenarios/stats_progression_hypothesis_xp_sweep.json`, `tests/test_stats_progression_hypothesis.py`, `tests/test_stats_progression_dispatch.py`, `tools/verify_stats_progression_encoder.py`, this report and its `.manifest`.
Modified: `src/pirateforce_foundation/app.py` (flag, mutual exclusion, `--db` requirement, mode label, wiring), `src/pirateforce_foundation/runtime.py` (import, mode exclusion, counter, dispatch method, gated branch), `docs/HYPOTHESIS_LEDGER.json` (HYP-PF-020 appended), `tools/verify_hypothesis_ledger.py` (inventory + canonical hash), `docs/FUNCTIONAL_COVERAGE.json` (surgical: evidence/test refs + notes on one row), `tests/test_foundation_legacy_seam.py` (grade digest), `.gitignore` (un-ignore the new report/manifest/tool).

## 11. How to reproduce

```
py -3 tools/verify_stats_progression_encoder.py                       # 85 guards, exit 0
py -3 tools/verify_hypothesis_ledger.py                               # entries=27
py -3 -m pytest tests/test_stats_progression_hypothesis.py -q         # 42 passed
py -3 -m pytest tests/test_stats_progression_dispatch.py -q           # 22 passed
py -3 -m pytest tests/ -q                                             # full gate
```

Nothing above touches the network, the canonical database, the GameClient process or v141; v141 is opened read-only through the existing `load_legacy` seam.

**Gate numbers as observed at the end of this milestone (Linux sandbox, CPython 3.10):** `818 passed, 1 failed, 397 subtests`. The one failure is the standing 3.10 baseline failure `tests/test_server_shutdown.py::ServerShutdownTests::test_primary_exception_is_preserved_with_cleanup_failure` (`__notes__` needs 3.11+); it is untouched and not special-cased. The pre-milestone baseline in the same environment was `717 passed, 1 failed`; this milestone adds **64** tests (42 + 22) and a **concurrent static lane** (`PF_MPAUDIT_FOLLOWUP001`, not part of this milestone) added a further 37 in the same window, which is the rest of the delta. The sandbox tool cap forced the gate to be run in two halves (`414 passed / 323 subtests` + `404 passed, 1 failed / 74 subtests`); the sum is the figure above.

## 12. Suggested next steps (not done here)

- **GT-017, attended:** run the sweep against a real client and read the XP bar, the level number and the five `Char_Info2` rows. It needs one session and answers the whole lane.
- If GT-017 shows the client accepts the frames but the bar does not move, the next suspect is the **level/experience pairing** (the bar reads `level+1`'s requirement, so `level = 7` with an unknown curve may produce a divide the client refuses to draw) — try level 1 and a small experience value before doubting the field offsets.
- The **inbound** half (what the client does with a progression verb echo) and the **persistence** half (no table exists) both remain untouched.
