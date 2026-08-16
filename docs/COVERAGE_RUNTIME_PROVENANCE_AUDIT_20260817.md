# Coverage runtime-provenance audit — 2026-08-17 (M13)

Scope: all 36 graded rows of `docs/FUNCTIONAL_COVERAGE.json` (the 15 `not_started`
rows carry no claim and are excluded). This audit answers the question opened as
item 6.2 of `pf_bridge/CHIEF_CONTINUATION.md`: **when a row says `runtime_pass`,
which server actually passed?**

No grade, status, `required`, `evidence_refs` or `test_refs` value was changed by
this audit. The only edit to the matrix is one stale clause in a `notes` string,
recorded in section 7.

---

## 1. The question was framed wrongly, and the correct framing is worse

Item 6.2 assumed two interchangeable servers: a frozen legacy scenario runner and
a Foundation server. That is not the architecture.

`src/pirateforce_foundation/app.py` line 106:

```python
legacy = load_legacy(root/'current/pf_login_game_server_v141.py')
```

and `src/pirateforce_foundation/runtime.py` line 74:

```python
class PersistentGameSessionState(legacy.GameSessionState):
```

The Foundation server is **4,269 lines that load the frozen 8,014-line V141
module at startup and subclass its session state**. `runtime.py` calls
`super().dispatch(parsed)` in seven places and, in the population lane, returns
`inherited_actions + population_actions` — legacy actions first, Foundation's
appended. `app.py` then replaces `legacy.GameSessionState`, wraps
`legacy.game_listener` and `legacy.main`, and silences the second self-test run.

**Consequence: "it passed on the Foundation server" carries no information about
who implemented the behavior.** Every Foundation run is a V141 run with a
Foundation state class in front of it. Anything Foundation does not override
falls through to frozen V141 and still reaches the client. A row can be green,
have been produced by a Foundation process, and still describe a behavior that no
Foundation code implements.

So the audit answers two independent questions per row:

- **Runtime host** — which process produced the retained artifact (mechanical:
  `FOUNDATION_*` / `[FOUNDATION]` markers appear only in `src/`, never in V141,
  so their presence in a server console log identifies the host).
- **Behavior owner** — which side of the seam produces the bytes. `FOUNDATION`
  = would not exist without `src/`; `LEGACY` = entirely frozen V141, Foundation
  only relays; `JOINT` = Foundation sequences or gates, legacy serializes;
  `CLIENT` = the behavior is client-side and neither server implements it;
  `NONE` = nothing implemented anywhere yet.

## 2. Headline result

| | count |
|---|---|
| graded rows audited | **36** |
| `FOUNDATION` owns the behavior | 14 |
| `JOINT` (Foundation sequences, legacy serializes) | 8 |
| **`LEGACY` — Foundation implements nothing** | **8** |
| `CLIENT` (client-side behavior, no server implementation) | 4 |
| `NONE` | 2 |

Restricted to the 18 rows graded `runtime_pass` — the rows that read as
"the game does this":

| owner | count | rows |
|---|---|---|
| FOUNDATION | 7 | 5 × `session_lifecycle`, `player_name_projection`, `action_acknowledgement` |
| JOINT | 5 | `backpack_open_display`, `scene_entry_placement`, `scene_actor_population_streaming`, `hostile_relation_and_target_selection`, `character_list_projection` |
| **LEGACY** | **5** | `npc_locomotion_presentation`, `teleport_transport`, `server_system_message`, `npc_conversation_handshake`, `conversation_operation_sequence` |
| CLIENT | 1 | `attack_command_producer` |

> 🔴 **5 of the 18 `runtime_pass` rows describe behavior the Foundation server
> does not implement at any line of `src/`.** They are green because frozen V141
> produced them — three of them inside a Foundation run, via the inherited
> dispatch path; two of them in a standalone legacy V-script run.

M12 found this for one row (`npc_locomotion_presentation`) and suspected it was
systemic. It is systemic, and it is five times larger than the one row.

## 3. Second finding: the capabilities cannot be combined

`make_state_class` accepts five opt-in scenario modes and rejects more than one:

```python
if active_modes > 1:
    raise ValueError(...)
```

`tools\run_foundation_visible.ps1` — the launcher every full-loop demo uses —
passes none of them, so the playable server runs in the default `foundation`
mode. Classifying each retained capture by the scenario markers its log contains:

| server mode | `runtime_pass` rows reachable |
|---|---|
| `foundation` (default, what the playbook launches) | 10 |
| `scene-load` opt-in only | 3 |
| `population` opt-in only | 1 |
| no Foundation runtime at all | 4 |

> 🔴 **The modes are mutually exclusive, so no single server run can exhibit all
> the green rows at once.** A run that streams the authoritative NPC population
> cannot also be the run that acknowledges an attack; a run that captures an item
> move cannot do either. "0/51 required complete" already said the game is not
> finished, but the matrix does not currently record that several of the rows it
> *does* call green are only reachable one at a time under a flag the playable
> server never sets.

This is a fact about the code as it stands today, not a criticism of it — each
scenario mode was introduced deliberately, strictly opt-in, to keep an unproven
behavior out of the default path. The gap is that the matrix does not say so.

## 4. Third finding: the evidence base is intact — 316/316 verified

Nobody had ever re-verified the hash-pinned evidence. This audit rehashed every
line of all 22 `.manifest` files in `reports/`:

| | |
|---|---|
| manifests | **22** |
| artifact lines checked | **316** |
| sha256 matches | **316** |
| missing files | **0** |
| size or hash mismatches | **0** |

Every pinned artifact still exists and still hashes to the recorded value. That
is the single strongest positive result in this audit and it is worth stating
plainly: the evidence base has not drifted.

⚠️ **The first pass of this check silently verified only 307 of the 316 lines.**
`reports/` contains **two manifest formats**: 21 files use the house
`path|size|SHA256` shape, while
`PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.manifest` uses an earlier
`SHA256  bytes  relative_path` layout with a `#` header and paths relative to its
capture root rather than to the repository. A verifier written for one format
skips the other **without reporting anything**, which is exactly the failure mode
manifests exist to prevent. The nine lines in that file were then checked
separately and all nine match. `tests/test_foundation_legacy_seam.py` now parses
both shapes and pins the older-format set to exactly that one file, so a new
report cannot reintroduce the shape unnoticed.

**But manifest coverage is uneven.** 4 of the 18 `runtime_pass` rows cite no
report that has a manifest at all:

- `movement/npc_locomotion_presentation`
- `movement/teleport_transport`
- `npc_interaction/npc_conversation_handshake`
- `npc_interaction/conversation_operation_sequence`

For these the runtime claim rests on report prose alone. Their capture
directories are also gone from `GameClient/` (pruned V-runs from 2026-08-13/14),
so the claim cannot be re-derived from retained bytes today. Note the overlap:
**all four are also `LEGACY`-owned rows.** The rows Foundation does not implement
are the same rows whose evidence is least re-checkable.

## 5. Per-row table

`โฮสต์ที่รันจริง` is mechanical (log markers). `เจ้าของพฤติกรรม` is a reading of
`src/` against the row's claim, with the supporting scan in section 6.

| domain | capability | สถานะ | โฮสต์ที่รันจริง | โหมดเซิร์ฟเวอร์ | manifest | เจ้าของพฤติกรรม |
|---|---|---|---|---|---|---|
| inventory | `backpack_open_display` | runtime_pass | Foundation | default | ✅ | **JOINT** |
| inventory | `persisted_projection_reconnect` | in_progress | Foundation (no marker in log) | default | ✅ | **FOUNDATION** |
| inventory | `move_known_item_any_free_slot` | blocked | Foundation | default | ✅ | **FOUNDATION** |
| inventory | `same_slot_noop` | blocked | — | — | ❌ | **FOUNDATION** |
| inventory | `move_negative_paths` | in_progress | V-run (capture pruned) | — | ❌ | **JOINT** |
| inventory | `stack_merge_and_limit` | in_progress | V-run (capture pruned) | — | ✅ | **JOINT** |
| inventory | `equip_unequip` | in_progress | V-run (capture pruned) | — | ❌ | **NONE** |
| session_lifecycle | `visible_console_requirement` | runtime_pass | Foundation | default | ✅ | **FOUNDATION** |
| session_lifecycle | `requested_stop_clean_exit` | runtime_pass | Foundation | default | ✅ | **FOUNDATION** |
| session_lifecycle | `character_select_to_scene_entry` | runtime_pass | Foundation | default | ✅ | **FOUNDATION** |
| session_lifecycle | `session_row_persistence` | runtime_pass | Foundation | default | ✅ | **FOUNDATION** |
| session_lifecycle | `abrupt_loss_recovery` | runtime_pass | Foundation | default | ✅ | **FOUNDATION** |
| movement | `scene_entry_placement` | runtime_pass | Foundation | default | ✅ | **JOINT** |
| movement | `local_player_position_checkpoint` | in_progress | Foundation | default | ✅ | **FOUNDATION** |
| movement | `npc_locomotion_presentation` | runtime_pass | **none retained** | — | ❌ | **LEGACY** |
| movement | `scene_actor_population_streaming` | runtime_pass | Foundation | population | ✅ | **JOINT** |
| movement | `teleport_transport` | runtime_pass | **legacy V-script** | — | ❌ | **LEGACY** |
| combat | `hostile_relation_and_target_selection` | runtime_pass | Foundation | arena, scene-load | ✅ | **JOINT** |
| combat | `attack_command_producer` | runtime_pass | Foundation | scene-load | ✅ | **CLIENT** |
| combat | `action_acknowledgement` | runtime_pass | Foundation | scene-load | ✅ | **FOUNDATION** |
| combat | `damage_and_hit_result` | blocked | Foundation | scene-load | ✅ | **NONE** |
| combat | `knockdown_and_reaction_states` | in_progress | V-run (capture pruned) | — | ❌ | **CLIENT** |
| combat | `skill_use` | in_progress | — | — | ❌ | **CLIENT** |
| combat | `behavior_range_gating` | in_progress | Foundation | scene-load | ✅ | **CLIENT** |
| character_management | `character_list_projection` | runtime_pass | Foundation | default | ✅ | **JOINT** |
| character_management | `player_name_projection` | runtime_pass | Foundation | scene-load | ✅ | **FOUNDATION** |
| character_management | `character_creation` | in_progress | — | — | ❌ | **FOUNDATION** |
| character_management | `character_deletion` | in_progress | Foundation | default | ✅ | **FOUNDATION** |
| character_management | `second_password_gate` | in_progress | V-run (capture pruned) | — | ❌ | **JOINT** |
| character_management | `appearance_and_avatar_binding` | in_progress | — | — | ❌ | **FOUNDATION** |
| chat | `server_system_message` | runtime_pass | Foundation | default | ✅ | **LEGACY** |
| npc_interaction | `npc_conversation_handshake` | runtime_pass | **none retained** | — | ❌ | **LEGACY** |
| npc_interaction | `conversation_operation_sequence` | runtime_pass | V-run (capture pruned) | — | ❌ | **LEGACY** |
| npc_interaction | `quest_accept_and_progress` | in_progress | V-run (capture pruned) | — | ❌ | **LEGACY** |
| npc_interaction | `shop_buy_sell` | in_progress | V-run (capture pruned) | — | ❌ | **LEGACY** |
| npc_interaction | `interaction_negative_paths` | in_progress | — | — | ❌ | **LEGACY** |

## 6. The scan behind the `LEGACY` verdicts

Token counts across all of `src/pirateforce_foundation/*.py` versus frozen
`current/pf_login_game_server_v141.py`:

| behavior | modules in `src/` | hits in V141 |
|---|---|---|
| gait / `movement_speed` / `0x0040` | **none** | 11 |
| NPC conversation | **none** | 34 |
| quest | **none** | 68 |
| shop / trade | **none** | 82 |
| `ShowMessage` | **none** | 11 |
| equip | docstring only ("equipment … outside this module") | 98 |
| `DeleteActor` | `delete_actor.py` | **0** |
| session / lease | 5 modules | 3 |
| visible console | `runtime_console.py` | 9 (unrelated word sense) |

The last three rows are the control: where Foundation genuinely owns a behavior
the asymmetry runs the other way, which is what makes the first five meaningful
rather than an artifact of grepping.

For `chat/server_system_message` specifically:
`V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE` is emitted at
`current/pf_login_game_server_v141.py:3778` and the token appears nowhere in
`src/`. The chat line the operator sees in every full-loop demo — the one that
looks like proof the server talks to the player — is printed by the frozen
legacy module through the inherited dispatch path.

`movement/teleport_transport` is a different shape of the same problem. `src/`
does contain teleport code, but it is the once-only login/scene-entry teleport
(`runtime.py:457-471`, calling `legacy.make_login_teleport`). The row's claim is
the V137 standalone `TeleportVital` transport to a decoded MARKER row, which has
no owner in `src/` and was only ever run by the standalone V137 script.

## 7. Matrix edit made by this audit (one, and it is a correction)

`chat/server_system_message` `notes` ended with "…and it has no offline test, so
it is one observation rather than an owned feature." M9 (commit `896f715`) added
`tests/test_system_message_wire.py` and referenced it in that row's `test_refs`,
but the sentence was not updated. The clause is false as written.

The clause was corrected to say the test exists and what it does **and does not**
cover; the "no Foundation module owns it" half of the sentence — which this audit
independently re-confirmed — was left standing. Status, `required`,
`evidence_refs`, `test_refs` and `domain_complete` are byte-identical to `31494fe`
for every one of the 51 rows; `tests/test_foundation_legacy_seam.py` pins that.

## 7.1 What now watches these findings

`tests/test_foundation_legacy_seam.py`, 22 tests in three groups:

- **the seam** — `app.py` pins exactly one frozen legacy module and loads it via
  `load_legacy` rather than importing it; `PersistentGameSessionState` still has
  `legacy.GameSessionState` as its only base (parsed with `ast`, not grepped);
  `super().dispatch(parsed)` still exists; the five scenario modes still reject
  each other *and still say why*; the visible launcher still enables none of them.
- **the manifests** — both formats parse, sizes are non-negative (zero is
  load-bearing: an empty stderr file is the evidence for several clean-shutdown
  claims), no path is pinned twice, every manifest has its report, and the
  older-format set is pinned to one file.
- **the matrix** — a sha256 over every graded field of all 51 rows (`id`,
  `status`, `required`, `evidence_refs`, `test_refs`, `next_missing_behavior`,
  `domain_complete`) with `notes` deliberately excluded, plus the manifest-debt
  list and the corrected `server_system_message` note.

**Mutation check: 19 mutations, 18 expected to bite, all 18 bit; 1 control
expected to pass, and passed.** Run on copies under `/tmp`; the repository was
not touched.

| # | mutation | outcome |
|---|---|---|
| M01 | legacy pin moved to `v140.py` | caught |
| M02 | legacy imported as a package instead of `load_legacy` | caught |
| M03 | state class no longer subclasses frozen V141 | caught |
| M04 | every `super().dispatch` fallthrough removed | caught |
| M05 | `active_modes > 1` relaxed to `> 5` (modes composable) | caught |
| M06 | exclusion still raises but stops saying "mutually exclusive" | caught |
| M07 | visible launcher starts passing `--population-scenario` | caught |
| M08 | one row promoted to `complete` | caught |
| M09 | one `evidence_ref` appended | caught |
| M10 | one `test_ref` removed | caught |
| M11 | a fifth `runtime_pass` row loses its manifest | caught |
| M12 | a recorded debt row quietly gains a manifest | caught |
| M13 | a manifest line loses its hash | caught |
| M14 | a manifest pins the same path twice | caught |
| M15 | a manifest orphaned from its report | caught |
| M16 | a second manifest reverts to the column format | caught |
| M17 | a Foundation module starts emitting the legacy system message | caught |
| M18 | the corrected note reverted to its false claim | caught |
| M19 | **control** — prose-only `notes` edit | still passes ✅ |

M06 and M19 are the two that matter most. M06 proves the exclusion test reads the
reason rather than merely counting exceptions — three of the five modes run their
own allowlist validator that also raises `ValueError`, so a test that only
asserted `assertRaises(ValueError)` would have passed against a broken guard.
M19 proves the grade digest does not make prose corrections expensive, which is
what keeps the matrix honest rather than frozen.

## 8. What is deliberately **not** done here

- **No grade was changed.** Whether a `LEGACY`-owned row may keep `runtime_pass`
  is a decision about what "playable" means, not an audit result. It is item 6.2
  in `CHIEF_CONTINUATION.md` and it is Panya's to make.
- **No `runtime_source` / `behavior_owner` field was added to the schema.** That
  is option (ก) of item 6.2 and adding it would pre-commit the decision.
- **No opt-in mode was made composable.** Merging scenario modes changes what the
  default server does and needs its own evidence; the mutual exclusion is a
  deliberate fail-closed design.
- **No pruned capture was regenerated.** Re-running a 2026-08-13 V-script to
  restore an artifact is a runtime test and belongs to the game-tester queue.

## 9. Decision material for item 6.2

The original three options assumed the row-level question "does a legacy pass
count". Given the seam, the sharper question is:

**(ก)** Keep the grades, add a `behavior_owner` field to every row so a reader
can see that 5 green rows are legacy passthrough. Cheapest, honest, changes no
numbers. Cost: one schema change + verifier update, ~1 round.

**(ข)** Demote the 5 `LEGACY` `runtime_pass` rows. The "playable" count drops
from 18 to 13 and Foundation's real surface becomes visible. This is the most
truthful reading of "the target is Foundation", and it makes the roadmap longer
but correct.

**(ค)** Keep the grades and record the finding in `notes` only — the de-facto
status quo after this audit.

A fourth option exists that the earlier framing hid:

**(ง)** Treat legacy passthrough as **acceptable and intended** — the frozen V141
is a component of the shipping server, not a rival to it — and instead grade on
*mode reachability*: a row is only green if the default `foundation` server can
exhibit it. That would demote the 4 opt-in-only rows rather than the 5 legacy
ones, and it maps directly onto "can Panya launch the server and play".

Options (ข) and (ง) demote almost disjoint sets of rows, which is a sign the
matrix is currently answering two different questions at once.

## 10. Non-claims

- Behavior-owner verdicts are a reading of the source against each row's claim.
  The mechanical token scan supports them but does not prove them; a reviewer who
  disagrees with a specific row should say which, not discard the table.
- "No retained artifact" means no capture directory survives in `GameClient/`
  today. It does not mean the run never happened — the reports document runs that
  predate the retention practice.
- The 307/307 manifest verification was performed on the Linux mount. It proves
  the bytes on disk match the pinned hashes; it does not re-prove the claims
  those bytes were originally read to support.
- The mode classification reads scenario markers out of server console logs. A
  run that entered a mode but never emitted its marker would be misfiled as
  `default`; no such case was observed, but the method cannot exclude it.
- This audit did not examine the 15 `not_started` rows and asserts nothing
  about them.
