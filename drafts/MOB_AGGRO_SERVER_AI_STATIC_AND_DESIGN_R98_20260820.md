# MOB AGGRO AND SERVER-DRIVEN AI -- static RE + design draft (chief round 98, 2026-08-20)

> **This is OUR design, not a recovery.** The original Pirate Force server is closed,
> was never published, and left no server->client capture of a monster deciding to
> attack a player. Nothing in this document is "how the original server did it."
> Everything below is either (a) a fact read out of the shipped client binary /
> our own proven lanes, marked [PROVEN] or [STATIC], or (b) a design we would build
> ourselves, marked [OUR DESIGN]. The coverage row `mob_aggro_and_server_ai` stays
> `not_started` until a real client is watched reacting to a frame we sent.

Scope: this draft answers "what would it take to give a scene NPC an aggro / attack
loop that the real GameClient renders" and picks the one honest first checkpoint.
It is a design + static-RE note only. It boots no server, opens no client, writes no
DB, adds no ledger entry, and moves no coverage grade. Provenance for every binary
offset and every [PROVEN] claim is a report already in `reports/` or a runtime pass
already in `docs/EXPERIMENT_LEDGER.md`; this draft does not re-derive them, it cites
them so a fresh clone can follow the chain.

Binary of record: `GameClient/GameClient.local.bin`
sha256 `9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623`.
Image base 0x400000. All VAs below are in that image.

---

## 0. The question this round was asked to open

`docs/FUNCTIONAL_COVERAGE.json` carries `mob_aggro_and_server_ai` as a REQUIRED,
`not_started` row whose note reads: "Scene actors are projected placements that never
react to the player. No aggro radius, threat table, chase, or attack loop exists on the
server." The standing continuation file recorded that "static RE for the server-AI line
does not exist yet." This round closes that specific gap: it maps every part of the
client that a mob-AI / attack lane would have to drive, and reports honestly which parts
are proven reachable and which are not.

The short version: **hostility is solved, death is solved, and attack is not.** A
mob-aggro lane can start today on proven ground (make the NPC present as hostile) but
cannot yet make the NPC swing, because the attack-animation trigger has no proven
server->client path.

---

## 1. What the client already contains (discovered this round)

Two structures were found in the client that no prior report had analysed:

**1a. A complete local mob-AI state machine (RTTI, VAs 0xC20054-0xC20164).** [STATIC]
`CAIControler`, `CAICondition`, `CAIBehavior`, `CAIState`, `CAIState_Dead`,
`CAIStateRamble` (+ `_Idle` / `_Walk`), `CAIStateCombat`, and
`CAIStateCombatProxy@CAIStateCombat`. Also `PatrolPath` and `MobLuaProxy_Client`.
The state graph is three-lane: Ramble(Idle/Walk) -> Combat(+Proxy) -> Dead.

The important negative: these AI type descriptors have **zero live code cross-references
outside the RTTI registrar** (0xBDA306-0xBDA506). The state-enter methods, the condition
that flips Ramble->Combat, and the push/construct sites are not statically reachable.
Across every runtime pass we have (SCENE-004..013) the projected Port-Royal NPC **never
entered combat and never attacked**. [PROVEN -- SCENE reports]

Conclusion: this FSM is a **client-side / offline mob system** (Lua-scriptable via
`MobLuaProxy_Client`), not the driver for a server-projected `CNetNPC`. A server that
projects actors through the actor-entry pipe does **not** get combat behaviour "for free"
by flipping this FSM -- there is no wire field that feeds it. [STATIC negative]

**1b. A full attack-animation vocabulary, data-driven not literal.** [STATIC]
`Data/GC/A/` holds ~2,263 keyframe files; the attack verb alone has ~625 clips
(`_f_attack_*` + `_c_attack_*`) on a sparse global attack-id space. Only two animation
tokens are hardcoded in the binary and driven by a task: `_F_DIE_000` (0xF0F060) and
`_F_KNOCKED_002` (0xF48B4C). `_F_ATTACK_004.kf` exists only as a keyframe filename
(0xF25D10), **not** as a task literal -- so attack animation is selected by a BEHAVIOR
row (`s_ANIMATION`), not by a fixed task. The behavior contract ships as `.beh` files in
`Data/GC/ScriptB/` with the schema `s_ANIMATION` (+frame count), `s_HIT_KEYFRAME`,
`s_HITBACK` (e.g. `STUN(5)`), `n_RANGE`, `n_DAMAGE_AREA`, `n_AMOUNT_TARGET`.

---

## 2. The three doors, ranked by how proven they are

A mob-aggro lane needs three things to happen on the client: the NPC must look
**hostile**, it must **act** (swing / cast), and a hit must **land** (already solved by
the damage + death lanes). Here is exactly how proven each door is.

### Door A -- HOSTILITY. Solved on the wire today. [PROVEN]
Faction is `BasicAttr` bit `0x0400`, a u32 at `BasicAttr+0x68` (tag 0x14, width 4).
Hostility is relative: the client's relation lookup 0x4A1D50 compares two actors'
FACTION fields against a client-side faction table (`n_ID` / `s_ENEMY`). SCENE-005 is a
runtime pass: setting a faction field produced a hostile presentation (red name /
outline / target panel) and the client emitted a 31-byte `TargetVital` for the placement
identity. The actor-entry pipe we already own (HYP-PF-023, id 0x6E9D, derived mask 0x02)
carries a nested `BasicAttr`, so **adding bit 0x0400 to NPC 0x2001's BasicAttr in a SPAWN
frame is buildable now with two proven mechanisms** (SCENE-005 semantics + HYP-PF-023
transport). Caveat carried from SCENE-005: faction value 1 is our composition; the
original server's faction assignment is unknown. [PROVEN with caveat]

### Door B -- ATTACK / ACTION. Structurally located, NOT proven. [STATIC + PROVEN-inert]
The attack animation is triggered by a **behavior-id-bearing inbound vital** -> BEHAVIOR
registry lookup (singleton 0x102DAD8, lookup 0x702A10) -> row `s_ANIMATION` -> a
play-action task. Two carriers were statically identified:
 - `CHitResult` (0x16F7): reaction factory 0x48D870 reads a behavior id from
   `CHitResult+0x22` and a selector from `+0x28`, calls 0x702A10; missing row falls back
   to 0x48AE40. [STATIC consumer -- SCENE-010]
 - `CKnockdownVital` (0x3123): consumer 0x750700 uses raw `+0x20` as the BEHAVIOR key ->
   0x47CAD0 -> wrapper vtable 0xF0F7DC (flags 0x40000005) -> the actor+0x40 task queue.
   [STATIC consumer -- COMBAT-KNOCK-001]
The inbound `ActionVital` path (handler 0x7516C0, id 0x1AEA, action 0xEA7D) does its own
0x702A10 lookup but was **proven inert** (SCENE-008: action object built with
implementation=0 and terminal bit 0x08 preset; EA7D returned null in every capture).
**Net: the door exists in the binary but has never opened** -- zero original captures,
zero server encoders, and every observed behavior lookup returned null (SCENE-013 corpus
negative). This is the blocker for a real attack loop.

### Door C -- HIT LANDS (damage + death). Already ours. [PROVEN headless / attended]
`CHitResult` damage frames (HYP-PF-024, GT-024 attended: numbers drawn, MISS marker,
reaction flag) and the death path (`CActorTask_Dead`, id 0x80000005, vtable 0xF0F048 ->
`_F_DIE_000`; GT-019 attended: hp 0 + timer opens the death window). HYP-PF-026 already
links them (headless-proven, GT-031 pending). This door needs nothing new.

---

## 3. The task-id space (for the record)

Task id is a KIND code written to `[task+0x10]` as `0x800000XX` in the ctor cluster
0x472000-0x476000; it is NOT per-class. Only four kinds appear: 0x80000002, 0x80000004,
0x80000005 (four vtables, incl. `CActorTask_Dead` 0xF0F048), 0x80000006 (five vtables).
The `CActorTask_*` family by NAME (RTTI, custom non-MSVC, so vtable->name is not
statically resolvable for most): `UseBehavior`, `PlayActionEvent`,
`PlaySimpleActionEvent`, `DrawSwordEvent`, `PlayCreateMissileEvent`(+`_Script`),
`Knockdown`, `Stun`, `Dodge`, `LearnSkill`, `ActorMove`, `MyActorMove`, `TracePath`,
`Idle`, `WaitServer`, `Dead`. There is **no** `CActorTask_Attack` -- attack rides
`UseBehavior` / `PlayActionEvent` off a BEHAVIOR row. [STATIC]

This matters for design: the client does have a `PlayActionEvent` / `UseBehavior` task,
which is presumably what a behavior-id vital ends up constructing. Walking those two
ctors (still unresolved) is the single highest-value next static step for Door B.

---

## 4. NPCAttr / BasicAttr field map (what a spawn frame can carry)

The actor entry's `NPCAttr` (id 0x0AD5) own u8 mask only carries `0x01` template id
(u16 @ +0x78) and `0x04` visual preset (wstring @ +0x7C); bits 0x02 / 0x08 are never
emitted and are unknown. **All AI-relevant state rides the nested `BasicAttr` u16 mask**,
not the NPCAttr own mask:

| bit | offset | meaning |
|---|---|---|
| 0x0001 | +0x28 | name (wstring) |
| 0x0002 | +0x5E | level (u16) |
| 0x0004 | +0x44 | HP current (u32) -- death predicate input |
| 0x0008 | +0x48 | HP max (u32) |
| 0x0010 / 0x0020 | +0x4C / +0x50 | MP cur / max |
| 0x0040 | +0x54 | move speed (f32) |
| 0x0080 | +0x58 | death / down timer (f32) |
| 0x0100 | +0x5C | scene category (u16; ==8 swaps HP source) |
| 0x0200 | +0x60 | scene sequence (qword) |
| 0x0400 | +0x68 | **FACTION (u32)** -- Door A |
| 0x0800 | +0x6C | (u32, unknown) |

There is **no** wire field in the actor entry for an aggro flag, a behavior id, or a
patrol path. Aggro is therefore not a bit you set on a spawn -- it is a server behaviour
that expresses itself as a sequence of frames over time. [STATIC]

---

## 5. [OUR DESIGN] the server-side model, and the honest first checkpoint

Because the client's own combat FSM is unreachable for projected NPCs, **all aggro
intelligence must live on our server** and be expressed only through frames the client
already renders. That is the "realistic, build-it-once" reading of the design principle:
the server owns the threat table and the decision to attack; the wire only carries the
observable consequences.

**Our server model (design, not built):** each hostile placement gets a lightweight
per-NPC AI record -- `faction`, `aggro_radius`, a `threat` map keyed by player identity,
`attack_range`, `attack_cadence`, `leash_origin`. A tick loop selects the highest-threat
player in range and drives a state: Idle -> Aggro(face+approach) -> Attack(cadence) ->
Dead/Leash. Every state maps to frames we can already emit or want to emit:
 - Idle/hostile presentation -> BasicAttr faction bit 0x0400 (Door A, proven).
 - Approach/face -> the position/movement write path we already proved
   (FINDINGS_R20/R22, TargetPos on the wire writes the row).
 - Attack -> Door B (unproven) -- a behavior-id vital.
 - Hit result -> Door C (proven, HYP-PF-024/026).
 - Death -> CActorTask_Dead (proven, HYP-PF-023/GT-019).

**Honest first checkpoint -- HYP-PF-027 "NPC HOSTILE PRESENTATION" (buildable next round).**
Scope it to exactly the proven substrate: an opt-in scenario that projects NPC 0x2001
through the actor-entry pipe with `BasicAttr` faction bit `0x0400` set, and NOTHING else
new -- no attack, no behavior id, no movement. It answers one clean attended question:
*does the real client render the placement as hostile (red name/outline/target panel)
when the server declares its faction, the way SCENE-005 rendered a faction we injected
onto the player?* This is the necessary precondition for aggro and is provable to the
wire headlessly today, with an attended GT to confirm the red presentation. A negative
result (no hostile presentation from a spawn-time faction bit) is itself valuable -- it
would say faction must be set some other way than the actor-entry BasicAttr.

Follow it, only after A lands, with **HYP-PF-028 "attack probe"** against Door B: a single
`CKnockdownVital` (id 0x3123) whose `+0x20` behavior key targets a `.beh` row we believe
is populated (start from `7101.beh`: `_F_ATTACK_018`, `n_RANGE=75`), performer NPC 0x2001,
target the player -- headless-proven at the wire, attended to see whether the NPC plays
ANY attack/knockback animation. Expected outcome is uncertain and the negative (the
lookup returns null, as every prior lookup has) is the most likely and most informative
result. Do NOT build B before A: hostility is the cheap proven win; attack is the
expensive unproven gamble, and the standing rule is proven-ground first.

---

## 6. Build discipline notes for whoever implements HYP-PF-027

- New `src/` module that builds an actor entry -> the RUNTIMERES-ACTOR-ENTRY census will
  move (round 96's expensive lesson): re-pin `pf_runtimeres_actor_entry_static.py` counts
  + report + tests in the SAME commit, and keep the SET/FORBID census honest (a
  hostile-spawn module SETS an entry, unlike the damage lanes).
- Follow the standard pattern exactly: opt-in scenario flag, `production_allowed=False`,
  whole-tree scenario allowlist, identity-pinned dispatch (fire only for 0x2001),
  one-shot, named refusals, a verifier + a headless replay whose independent walker
  re-reads the faction bit from the dispatched bytes, cross-lane byte equality against
  HYP-PF-023's SPAWN composer for everything except the added 0x0400 field.
- New ledger ENTRY (HYP-PF-024 is 3/3 full; HYP-PF-026 is reserved for the damage link).
  This is a new capability, not a profile of an existing lane.
- The BasicAttr faction field is a real balance value we choose -- carry the nonclaim that
  faction 1/6 is our composition, exactly as SCENE-005 already records.

---

## 7. Open static-RE questions (next dig, highest value first)

1. Walk the `CActorTask_UseBehavior` / `CActorTask_PlayActionEvent` ctors (unresolved
   custom RTTI) -- this is the missing half of Door B and would tell us whether a
   behavior-id vital can construct an attack task for a `CNetNPC`.
2. Pin which server field (if any) `CAIStateCombatProxy` reads -- currently unreachable by
   xref, so "is combat server-authoritative" is undecided.
3. Populate a real `.beh` behavior id -> confirm a row exists that maps to a live
   `_F_ATTACK_*` clip (parse `Data/B_CONSTDATA_TH.pc_`, the packed const table that likely
   holds the monster->behavior binding).
4. Decide the `[0x10339B0]` / `[localplayer+0x420]` singletons (carried debt since round
   90) -- either can suppress a number silently and would confuse an attended read.

---

## 8. nonclaims

- No original-server behaviour is claimed anywhere in this document. The original server
  is closed, unpublished, and unrecoverable.
- The client's combat FSM (`CAIStateCombat`/Proxy/`MobLuaProxy_Client`) is present but has
  NO live xref and NEVER fired for a projected `CNetNPC`; nothing here claims it can be
  driven from the wire.
- Door B (attack animation) is UNPROVEN: zero captures, zero encoders, all prior behavior
  lookups returned null, and inbound `ActionVital` is proven inert. No claim is made that
  an NPC can be made to attack today.
- Door A (hostility) is proven only for a faction injected onto the LOCAL PLAYER
  (SCENE-005); projecting the same bit onto an NPC via the actor-entry pipe is the
  untested question HYP-PF-027 would answer.
- This draft adds no code, no scenario, no ledger entry, no coverage grade; it moves
  nothing on the wire and touches no DB.
