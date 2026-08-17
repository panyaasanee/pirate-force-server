# Roadmap to playable — derived from the functional coverage matrix

Date: 2026-08-17

This document does not introduce any claim. It is an ordering of the 51 required
capabilities already declared in `docs/FUNCTIONAL_COVERAGE.json`, plus an honest
statement of what is blocking each group. Statuses quoted here are whatever the
matrix says at the commit this document ships in; `tools/verify_functional_coverage.py`
is the authority, not this file.

Current position: **0 of 51 required capabilities complete, 7 of 7 domains open.**
Eighteen rows sit at `runtime_pass`, which by policy proves one controlled
observation and closes nothing.

## 1. The four kinds of blocker

Every open row is stuck behind exactly one of these. Naming the kind matters
because the remedies are completely different and only one of them is
engineering work.

| kind | meaning | example row | who unblocks it |
| --- | --- | --- | --- |
| **D — decision** | the work would exceed a hypothesis ceiling or widen the definition of the product | `move_known_item_any_free_slot` | project owner |
| **E — evidence** | the recovered corpus provably cannot answer the question | `damage_and_hit_result` | nobody, until a new source appears |
| **R — runtime** | the code path exists; nobody has run it against the real client yet | `client_chat_input` | in-game tester |
| **B — build** | ordinary implementation work with no ceiling problem | `chat_channels_and_routing` | server work |

The important asymmetry: **R work is the cheapest and it is the largest
untouched category.** Several rows are at `not_started` or `in_progress` purely
because no one has pointed the client at them, not because anything is hard.

## 2. Critical path

The order below is dependency-driven, not preference-driven.

### Tier 0 — already load-bearing (do not regress)

`visible_console_requirement`, `requested_stop_clean_exit`,
`character_select_to_scene_entry`, `session_row_persistence`,
`abrupt_loss_recovery`, `scene_entry_placement`, `backpack_open_display`,
`server_system_message`.

These eight `runtime_pass` rows are what makes a session start, survive and end.
Everything below assumes them. Any FAIL here is a regression that outranks all
new work; that is what `GT-001` in the test queue exists to catch.

### Tier 1 — R work available right now, no decision needed

| row | domain | status | queued as |
| --- | --- | --- | --- |
| `local_player_position_checkpoint` | movement | runtime_pass 2026-08-17 | `GT-005` (done) |
| `client_chat_input` | chat | not_started | `GT-006` |
| `concurrent_multi_client` | session lifecycle | not_started | `GT-003` |

This is the entire set of rows that can move without an owner decision, without
new reverse-engineering, and without touching `src/`. It is small, and that is
the single most important fact about the project's current position: **the
matrix is mostly blocked on decisions and evidence, not on effort.**

`local_player_position_checkpoint` was the highest-value of the three and is
**answered as of 2026-08-17**: GT-005 walked the character through the real
client, restarted the server, and found the character standing at the walked
position — see
`reports/PF_GT005_MOVEMENT_POSITION_PERSISTS_ACROSS_RESTART_RUNTIME_PASS_20260817.md`.
The row is `runtime_pass`, which upgrades one walk in one scene and does not
close the domain. The two remaining Tier 1 rows are unchanged.

### Tier 2 — behind the HYP-PF-008 ceiling decision (kind D)

`move_known_item_any_free_slot` → `same_slot_noop` → `occupied_destination_policy`
→ `split_stack` → `use_drop_sell`.

Five inventory rows, chained. The implementation for the first is already
written and sitting in the working tree, but HYP-PF-008's `accepted_ceiling`
permits one opt-in free-slot composition and its exact reconnect, and a
generalized move exceeds it. Options were written up for the owner (open a new
`HYP-PF-010`, widen HYP-PF-008 as a tracked second version, or defer). Until
that is answered these five rows cannot move, and no amount of engineering
changes that.

`persisted_projection_reconnect` and `stack_merge_and_limit` sit adjacent: both
are `in_progress`, and both close naturally once the generalized move exists and
can be exercised across a reconnect.

### Tier 3 — combat, blocked on evidence (kind E)

`damage_and_hit_result` is `blocked` because SCENE-013 established that the
structural corpus available to this project cannot answer how damage is
computed. That is a negative result about the source material, not a to-do.
Three further rows queue behind it — `hp_death_and_respawn`,
`mob_aggro_and_server_ai`, `pvp_engagement` — because a damage number is a
precondition for all of them.

What *is* reachable in combat without solving damage: `knockdown_and_reaction_states`,
`skill_use` and `behavior_range_gating` are all `in_progress` with static
checkpoints already recorded, and each could be pushed toward `runtime_pass` by
observation runs in the same way Tier 1 rows can.

Combat is therefore the domain most likely to stay open longest, and it should
not be treated as a failure of execution.

### Tier 4 — build work, no blockers except sequencing (kind B)

- **Character management**: `character_creation`, `character_deletion`,
  `second_password_gate`, `appearance_and_avatar_binding` are all `in_progress`
  with static evidence; `stats_and_progression` is untouched. Creation is the
  declared next missing behaviour for the domain and gates the rest, because a
  character that cannot be created cannot be given stats.
- **Chat**: after `client_chat_input` is observed, `chat_channels_and_routing`
  and `chat_persistence_and_moderation` are ordinary server work.
- **NPC interaction**: `quest_accept_and_progress` and `shop_buy_sell` both have
  three static/runtime references each and no test refs at all. Adding tests is
  the cheapest progress available in this domain.
- **Movement**: `local_player_movement_authority` is `not_started` and is where
  the server stops trusting client-reported coordinates. It should not be
  now unblocked in principle: `local_player_position_checkpoint` reached
  `runtime_pass` on 2026-08-17, so the value being validated is one the server
  demonstrably persists across a restart.
  `remote_player_movement_projection` depends on `concurrent_multi_client`.

## 3. Ordering recommendation

1. Run the three Tier 1 tests. They are queued and cost one session each.
2. Resolve the HYP-PF-008 ceiling question. Five inventory rows plus the entire
   M3/M4 line are frozen behind it, and the working-tree implementation ages
   badly while it waits.
3. Add missing `test_refs` to the eight rows that carry evidence but no test at
   all — `equip_unequip`, `teleport_transport`, `server_system_message`,
   `npc_conversation_handshake`, `conversation_operation_sequence`,
   `quest_accept_and_progress`, `shop_buy_sell`, `interaction_negative_paths`.
   Five of the eight are in NPC interaction, which is the least test-guarded
   domain in the project. Nothing currently protects any of them from silent
   regression.
4. Push `knockdown_and_reaction_states`, `skill_use` and `behavior_range_gating`
   to observation runs, since they do not depend on the damage blocker.
5. Take `character_creation` as the first substantial build item.

Step 3 is deliberately placed above new features. A row with evidence and no
test is a claim with no guard, and the project's own policy treats an unguarded
claim as the thing most likely to quietly become false.

## 4. What "playable" would actually require

Completion policy is unchanged and is repeated here so the roadmap cannot be
read as a shortcut: a narrow fixture, a golden file, or a single controlled run
proves one fact and never closes a domain function. Full completion of a
capability requires the client/wire path, database persistence, reconnect
projection, and the negative paths together, and the domain banner in
`STATUS.md` must be published verbatim.

On that definition, none of the seven domains is close, and the honest summary
is: the session, scene-entry and inventory-display foundations are real and
runtime-proven, and everything that makes it a *game* — moving with authority,
fighting, creating a character, talking — is between one decision and one
unanswerable evidence question away from being startable.

## 5. Related

- `docs/FUNCTIONAL_COVERAGE.json` — the authoritative matrix and gate
- `docs/COVERAGE_EVIDENCE_AUDIT_20260817.md` — citation audit, and the one
  known domain-level gap (client presentation/audio) left open on purpose
- `docs/HYPOTHESIS_LEDGER.json` — ceilings and stop rules referenced above
- `pf_bridge/GAME_TEST_QUEUE.md` — the queued Tier 1 runs
