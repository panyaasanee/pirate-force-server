# Coverage evidence audit — 2026-08-17

Scope: read-only audit of `reports/` against `docs/FUNCTIONAL_COVERAGE.json`.
No source file, database, hypothesis ledger entry, capability status, or
`domain_complete` flag was changed by this audit. The only mutation it produced
is additional `evidence_refs` entries on capabilities that were already open,
listed in section 3.

## 1. Question this audit answers

The coverage matrix is meant to be the single index of what this project has
actually proven. If a report exists in `reports/` that no capability row cites,
one of three things is true:

1. the report is superseded lineage already represented by a cited successor;
2. the report belongs to a row that simply forgot to cite it — a traceability
   defect in the matrix, not a capability gap;
3. the report proves something that has **no row at all** — a real gap in the
   matrix, which means the matrix understates what exists.

Case 3 is the dangerous one, because a matrix that silently omits a proven
behaviour cannot be used as a completion gate.

## 2. Measurement

At the start of this audit:

| metric | value |
| --- | ---: |
| `reports/*.md` present | 82 |
| distinct report paths cited by the matrix | 55 |
| uncited reports | 27 |

After the section 3 corrections:

| metric | value |
| --- | ---: |
| `reports/*.md` present | 82 |
| distinct report paths cited by the matrix | 67 |
| uncited reports | 15 |

`tools/verify_functional_coverage.py` passes with `domains=7` before and after.
Every domain remains `INCOMPLETE`; no row changed status. Row count stays 51
required capabilities, 0 complete.

**Correction carried by this audit.** The commit message of `966d0b6` states
"16 of them are runtime_pass". The matrix as committed contains **18**
`runtime_pass` rows: 1 inventory, 5 session lifecycle, 4 movement, 3 combat,
2 character management, 1 chat, 2 NPC interaction. The matrix data itself was
correct; only the prose count in that commit message was wrong. Nothing in the
JSON needed changing to fix it, and the number is recorded here rather than by
rewriting history.

## 3. Case 2 — traceability defects corrected

Twelve reports were evidence for a row that already existed and already had a
non-`not_started` status. They were appended to `evidence_refs` only. No status,
`required` flag, `test_refs` entry, or `notes` string was modified.

| capability (status unchanged) | reports added |
| --- | --- |
| `inventory / backpack_open_display` (runtime_pass) | `PF_RE_V102_Inventory_Unlock`, `PF_RE_V103_One_Item_Backpack` |
| `inventory / move_known_item_any_free_slot` (blocked) | `PF_ITEM_MOVE_ORDER001_BACKPACK_IDENTITY_ORDER_STATIC_CHECKPOINT` |
| `inventory / move_negative_paths` (in_progress) | `PF_RE_V104_ItemOperate_Request_Capture`, `PF_RE_V105_ItemOperate_Response_Version_Boundary`, `PF_RE_V106_ItemOperate_V2_Accepted_Removal_Boundary` |
| `movement / scene_actor_population_streaming` (runtime_pass) | `PF_RE_V138_MARKER1_Nearest20_Population_Reapply_Pass` |
| `combat / hostile_relation_and_target_selection` (runtime_pass) | `PF_RE_V132_Tab_SelectTarget_Negative_Boundary`, `PF_RE_V133_P70_Relation_Display_Negative_Boundary` |
| `combat / attack_command_producer` (runtime_pass) | `PF_RE_V128_Wield_Z_ActionVital_Capture` |
| `npc_interaction / interaction_negative_paths` (in_progress) | `PF_RE_V134_Q3020_Conversation_Handshake_Operational_Negative`, `PF_RE_V126_Failed_Operational_P91_Mistarget` |

The `hostile_relation_and_target_selection` row is the clearest instance of the
defect: its `notes` string already argued from "the V132 negative" in prose
while `evidence_refs` did not contain V132. Prose citation without a path
reference is exactly what the matrix exists to eliminate.

`PF_RE_V126_Failed_Operational_P91_Mistarget` is cited deliberately as a
**failed operational run**, not as a negative result. Its own text states the
test procedure was never executed and that it must not be read as a positive or
negative runtime judgment. It is listed under interaction negative paths as
operational evidence about reachability, and the distinction is preserved here
so a later reader cannot upgrade it by accident.

## 4. Case 1 — remaining 15 uncited reports, and why they stay uncited

| report | classification |
| --- | --- |
| `PF_RE_V74_to_V84_Continuation` | lineage, superseded by cited `PF_RE_V67_to_V87_Walk_Gait` |
| `PF_RE_V84_Runtime_and_V85_Hypothesis` | lineage, same successor |
| `PF_RE_V85_Runtime_and_V86_Isolation` | lineage, same successor |
| `PF_RE_V87_Runtime_and_V88_Run_Cadence` | lineage, same successor |
| `PF_RE_V88_Runtime_and_V89_Ambient_Walk` | lineage, same successor |
| `PF_RE_V89_Runtime_and_V90_Local_Population` | lineage, superseded by cited `PF_RE_V93_Runtime_and_V94_Local_Population_Streaming` |
| `PF_RE_V90_Runtime_and_V91_Static_Once` | lineage, same successor |
| `PF_RE_V91_Runtime_and_V92_Authoritative_Membership` | lineage, superseded by cited `PF_OBJECT_POP002` |
| `PF_RE_V94_Runtime_and_V95_Target_Aware_Facing` | lineage, facing behaviour folded into `npc_locomotion_presentation` |
| `PF_RE_V95_Failure_and_V96_Multi_Action_Capture` | lineage, superseded by cited `PF_RE_V96_Runtime_and_V97_NPCConversation` |
| `PF_RE_V97_Runtime_Identity_and_V98_Facing` | lineage, same successor |
| `PF_RE_V131_TeleportCheck_Challenge_Candidate` | superseded by cited `PF_RE_V131_TeleportCheck_Challenge_Echo_Capture` |
| `PF_RE_V100_Data_and_Attribute_Roadmap` | static ID/table catalogue, asserts no runtime capability |
| `PF_RE_V102_ItemAttr_ItemBag_Static` | static structure catalogue, asserts no runtime capability |
| `PF_RE_V100_Current_Scene_Music` | **case 3 — see section 5** |

Citing superseded lineage would inflate `evidence_refs` counts without adding a
single new fact, and would make it harder to see which report a reviewer should
actually open. They stay uncited on purpose.

## 5. Case 3 — one genuine matrix gap, deliberately left open

`PF_RE_V100_Current_Scene_Music` records a runtime-accepted `MusicControlVital`
(protocol ID `0x3EAF`, constructor `0x5E4800`, serializer `0x5E60D0`, handler
`0x5F06D0`). The client accepted the packet without a protocol error and
continued its normal request stream.

No domain in the matrix covers client-side presentation control — audio, music,
weather, ambience, or scene mood. The seven current domains are inventory,
session lifecycle, movement, combat, character management, chat and NPC
interaction. A player-visible behaviour therefore exists with runtime evidence
and no row to hold it.

**This audit does not add that domain.** Adding an eighth domain is a scope
decision of the same class as the HYP-PF-008 ceiling question: it changes what
"playable, complete" is defined to mean, and the standing rule is that a matrix
row may not be created without an owner deciding the domain belongs in the
completion definition. The gap is recorded here so the decision is visible
rather than silently absorbed.

Recommendation to the project owner, stated as a recommendation only: a
`presentation` domain with roughly four rows — scene music control, system
message display (already runtime-proven and currently parked in `chat`), UI
error and dialog surfaces, and loading/transition screens — would close this
gap. It should be opened as one explicit decision, not grown row by row.

## 6. What this audit does not claim

- It does not claim the 67 cited reports are individually correct. It checked
  citation coverage, not the truth of each report's contents.
- It does not claim the 51 rows are a complete enumeration of a finished game.
  Section 5 is direct proof that the enumeration is not complete.
- It does not upgrade, downgrade, or close any capability, and it does not
  touch `docs/HYPOTHESIS_LEDGER.json`.
- It does not add runtime evidence. Every report cited here was already
  committed before this audit ran.
