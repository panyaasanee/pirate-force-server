# MONSTER SPAWN AND LOOT -- static RE + design draft (chief round 100, 2026-08-20)

> **This is OUR design, not a recovery.** The original Pirate Force server is closed,
> was never published, and left no server->client capture of a monster spawn cycle, a
> loot object appearing on the ground, or a player picking one up. Nothing in this
> document is "how the original server did it." Everything below is either (a) a fact
> read out of the shipped client binary / client const-data / our own proven lanes,
> marked [PROVEN] or [STATIC], or (b) a design we would build ourselves, marked
> [OUR DESIGN]. The coverage row `monster_spawn_and_loot` stays `not_started` until a
> real client is watched reacting to a frame we sent, and no grade in this commit moves.

Scope: this draft answers "what would it take to give Port Royal a real monster spawn
and loot loop that the GameClient renders" and picks the honest first checkpoints. It
is a design + static-RE note only. It boots no server, opens no client, writes no DB,
adds no ledger entry, and moves no coverage grade. It also records a MATERIAL CORRECTION
to the round-98 mob-aggro Door B finding (section 6), because the same round-100 static
dig that mapped the loot loop also resolved the attack-task constructors round 98 could
not reach.

Binary of record: `GameClient/GameClient.local.bin`
sha256 `9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623`. Image base
0x400000. Client const-data of record: the expanded
`B_CONSTDATA_TH.pc_.dec` (8,443,000 bytes, sha256 `496DFB2E..0D2D`); it self-identifies
as client data version 1.41.0000 built 2014-12-11. Provenance for every prior [PROVEN]
claim is a report already in `reports/` or a runtime pass already in the ledgers; this
draft cites them, it does not re-derive them.

---

## 0. The question this round was asked to open

`docs/FUNCTIONAL_COVERAGE.json` carries `monster_spawn_and_loot` as a REQUIRED,
`not_started` row whose note reads: "Scene actors are static placements. No spawn timer,
respawn cycle, drop table, loot object, or pickup path is captured or implemented." This
round maps every part of that loop and reports honestly which parts are proven reachable,
which are only in the shipped data, and which have no known path at all.

The short version: **the combat half is ours, the loot DATA MODEL is now fully in hand,
but the two middle hops -- a loot object appearing on the ground and a player picking it
up -- have NO KNOWN WIRE PATH.** A monster-loot lane can therefore start today on two
proven pieces (a server-authoritative loot roller built from client data; and the
"display a granted item" consumer we already proved has no prestate gate), but it cannot
yet make a lootable object appear in the world, because the actor-entry pipe has no
item/object type and the DropThing object family has no decoded transport.

---

## 1. The loot DATA MODEL the client already ships (mined this round) [STATIC]

The client const-data contains a COMPLETE, rollable drop model. This is new: no prior
report parsed past table 033. The full 120-table inventory is in
`outputs`-provenanced worker notes for this round; the load-bearing facts:

**1a. MOBS (table 028, 3210 rows x 54 cols).** Each monster row keys the whole loop:
 - level band `n_LEVEL_MIN..n_LEVEL_MAX`; rank bitmask `n_RANK`.
 - AI pointers `n_AI_WANDER` (+72), `n_AI_COMBAT` (+76), `n_AI_TACTIC` (+80) -- all
   resolve 100% into the AI_* tables.
 - skills `s_SKILLS` (semicolon id list) -> SKILL_CONTEXT (011) -> `s_CAST_BEHAVIOR` ->
   BEHAVIOR (012). MOBS does NOT reference BEHAVIOR directly.
 - drop refs `n_DROPS_NORMAL` / `n_DROPS_EQUIPMENT` / `n_DROPS_SPECIALLY` /
   `n_DROPS_QUEST`, `n_DROP_RANGE`.
 - MOBS carries NO faction and NO HP column. Faction rides
   `n_AI_WANDER -> AI_WANDER.n_FACTION`; HP rides level -> STANDARD_MOB.

**1b. The drop-id encoding rule (PROVEN on full data).**
`MOBS.n_DROPS_* = prefix*100000 + n_ID of a row in the matching DROPS_* table`. Prefix
27 -> DROPS_NORMAL (62/62 resolve), 28 -> DROPS_SPECIALLY (107/107), 54 -> DROPS_EQUIPMENT
(36/36), 87 -> DROPS_QUEST (only 311/2478 resolve client-side -- see negative). Item ids
inside the drop tables use the same scheme keyed on the item-category tables:
22 -> EQUIPMENT_BASE, 24 -> ITEM_CONSUMABLES, 25 -> ITEM_QUEST, 26 -> ITEM_MISC
(all probe-verified). `n_ITEM = 0` with a nonzero rate is the money slot.

**1c. The drop tables themselves (schemas + samples read this round).**
 - DROPS_NORMAL (049, 267x121): n_ID + 30 slots of (item, f_RATE, n_MIN, n_MAX), each
   an independent percentage roll.
 - DROPS_EQUIPMENT (048, 53x44): one roll at `f_DROPS_RATE` then a weighted pick among
   up to 20 (item, weight) pairs.
 - DROPS_SPECIALLY (050, 584x64): same weighted-pick shape, 30 slots.
 - E_DROPS_QUALITY (054, 26x9): equipment-drop White/Green/Blue/Purple/Orange weights by
   mob rank + level band.
 - DROPS_ACTIVITY (003, 4x11): event-time bonus drop sets layered by rank band.
 - DROPS_QUEST (096, 311x101): quest-gated item drops; `n_ID` == the mob id; ~87% of
   quest-drop sets are absent from the shipped client table [NEGATIVE -- server-only].

**Honest assessment:** for normal / equipment / special drops the client tables carry
the entire model -- drop rates, quantity ranges, item weights, quality weights -- and
every referenced set resolves inside the client tables (62/62, 36/36, 107/107). This is
not presentation-only data; it is sufficient to roll loot deterministically. Whether the
original server rolled loot client-side or server-side is [UNKNOWN] and unrecoverable;
for our rebuild the tables are directly usable as the authoritative drop model.

**1d. STANDARD_MOB (027, 255x38)** is the per-level mob stat baseline (n_ID == level,
1..255): HPMAX, EXP, phys/magic damage, AC, resist floats. This is the only client-side
source of mob HP (e.g. level 27 -> HPMAX 3857). MOBS.f_RATIO_EXP/f_RATIO_SP scale the
reward columns; rank-4096 bosses carry ratio 48.0.

**1e. AI tables (client-local FSM parameters).** AI_WANDER (024, 73x5:
n_ID/s_WANDER/n_FACTION/n_OFFESIVE/n_AGGRO) is the faction + aggro-radius carrier;
AI_COMBAT (026, 276x3) is a condition->action script (CHASE(n) selects the n-th skill);
AI_TACTIC (025, 9x5) is target selection (MOST_DAM, CLOSEST_DAM, ...). These parameterize
the CLIENT'S local mob FSM -- which round 98 proved has no live xref and never fires for a
projected CNetNPC -- so on our architecture they are a design reference for the
SERVER-side threat/aggro model, not a wire path. [STATIC]

---

## 2. Port Royal's real population (mined this round) [STATIC]

Frozen placements resolve as `actor_identity = 0x2000 + placement_index + 1`;
`template_id = the NN in "Mob_Set_NN"` = MOBS.n_ID (from `population.py` and the
sha-pinned `PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS` in v141, 115 rows).

- Identity `0x2001` (the probe HYP-PF-023/027 drive) = placement idx 0 = template 1 =
  "Navy Transfer": a faction-4 TOWN NPC, wander AI only, `n_AI_COMBAT=0`, `s_SKILLS`
  empty, all drop sets 0. It has no combat AI and nothing to loot.
- **13 of the 115 placements are genuine faction-6 hostiles**, each with combat AI +
  skills + resolvable drop sets, e.g. `0x200D` template 35 "Fighting Fish Sergeant"
  (lvl 27, AI_WANDER 16 / AI_COMBAT 352 / AI_TACTIC 1, drops 2701001 / 5400001 /
  2802264), `0x203D` template 62 (lvl 39-41), `0x2085` template 103 "Orc Chief"
  (lvl 58-60). All 13 drop refs resolve client-side.

Design consequence: the round-99 Door A lane (HYP-PF-027) SYNTHESIZES hostility by
splicing faction 6 onto the town NPC 0x2001. That is a legitimate opt-in probe, but the
shipped data already contains real hostiles at other identities. A future "realistic"
hostile/aggro/loot lane should prefer a GENUINE faction-6 placement (which comes with a
real combat AI row and a real drop set) rather than a spliced town NPC -- this is the
"build it like the real thing" reading of the design principle. [OUR DESIGN note; does
not invalidate HYP-PF-027, which is a deliberately minimal presentation probe.]

**GT-032 prediction is now data-backed.** The shipped FACTION table (085, 38 rows,
n_ID/s_ENEMY) lists faction 1's enemies as "6;11;12;17;18;26" and faction 6's enemies as
"1;2;3;12;13;18" -- so faction 6 and faction 1 are MUTUALLY hostile. The round-99 lane
pairs player faction 1 with NPC faction 6, exactly a mutually-hostile pair in the shipped
relation table. This CORROBORATES the GT-032 "does the NPC turn red" prediction to the
data, but does NOT move the coverage grade: only an attended eyewitness of the red
presentation can do that, and the player-side faction value 1 remains OUR composition.

---

## 3. The loot loop, ranked door by door (how proven each is)

A monster-loot loop needs, in order: a monster to exist and die; a decision about what
it drops; a lootable object to appear; a pickup; the item to display; and the item to
persist. Here is exactly how proven each hop is.

### Door 1 -- MONSTER EXISTS, IS HOSTILE, AND DIES. Ours already. [PROVEN]
Spawn transport `GSCN_RunTimeProtocolRes 0x6E9D` v4, derived mask bit 0x02 -> actor-entry
collection, actor_type 4 = CNetNPC (RUNTIMERES-ACTOR-ENTRY-001, 150-guard). HYP-PF-023
spawn-then-kill ran attended (GT-022, corpse photographed). Hostility is Door A of
mob-aggro (HYP-PF-027, headless-proven round 99, GT-032 pending). Death opens the death
window (GT-019) and the damage->HP->death link is ours (HYP-PF-026, GT-031 pending). This
door needs nothing new for loot.

### Door 2 -- WHAT IT DROPS (the roll). Buildable now as pure server logic. [OUR DESIGN on PROVEN data]
Because section 1 gives us the complete drop model as client data that resolves 100% for
normal/equipment/special drops, a SERVER-SIDE loot roller is buildable today with NO wire
and NO guessing: given a dead mob's template id, look up MOBS.n_DROPS_*, resolve each set,
roll the per-slot rates / weighted picks / quality weights, and produce the exact item id
list a kill would yield. This is testable to Grade A against the frozen tables with no
client and no DB. It is the honest first BUILDABLE piece of this row (see section 5). The
nonclaim it must carry: our roller is OUR reconstruction from client data; the original
server's roll order and RNG are unrecoverable.

### Door 3 -- LOOT OBJECT APPEARS ON THE GROUND. No known path. [NEGATIVE / STATIC name-only]
The actor-entry jump table (`0x4469BD`) accepts EXACTLY actor_type 2..6
(2 CNetActor, 3 CMyActor, 4 CNetNPC, 5 CAvatarNPC, 6 Pet); anything else is silently
dropped. **There is no item/object actor_type** -- a ground item cannot ride the proven
spawn pipe. The client DOES register a DropThing object family
(`DropThingGameObj` / `DropThingBoard` / `DropThingModule_Client`, names proven in the
521-class registration table; derived ids 0x3415 / 0x295E / 0x651A via the validated
project name-hash) but no transport, serializer, producer, or capture exists for any of
them. Whether DropThing arrives via an undecoded `0x6E9D` sub-object (the unexamined
derived bits 0x04 `+0x24` / 0x08 `+0x20`), via its own vital, or via scene data is
[UNKNOWN]. **This is the blocker for a real ground-loot loop.**

### Door 4 -- PICKUP REQUEST. No known path. [NEGATIVE / STATIC name-only]
`PickupTerrainThing` is a registered client class (registration `0xBEE5E5`, derived id
0x4543) with no serializer pinned, no capture, and no server handler. It is a name-grade
lead only.

### Door 5 -- CLIENT DISPLAYS THE GRANTED ITEM. Strong static lead. [STATIC]
The `ItemOperateVitalRes 0x4C13` v2 ItemBag-delta result handler (ITEM-MOVE-CONSUMER-001,
Grade A static) clones the incoming identity/template/quantity/slot into the destination
slot object with NO destination-occupancy rejection and NO old-quantity comparison. A
never-before-seen item identity is therefore STRUCTURALLY displayable through this
carrier. This is the closest thing the repo has to a proven "client will show an item it
did not previously have." Caveat: it is static (never exercised for a novel grant), and
the UpdateAttr `0x309A` full-replacement carrier is the riskier alternative (a one-item
"delta" through it would delete every other item -- V121).

### Door 6 -- ITEM PERSISTS. Schema-ready, no writer yet. [PROVEN db shape / NO PATH for new rows]
Tables `character_backpacks` + `character_backpack_items` (migration 003) will accept a
granted row -- the CHECK constraints freeze only header values, not new item rows -- and
persistence across reconnect is proven byte-exact for the V111 merge (ITEM-LIFECYCLE-001).
BUT **no code path anywhere inserts a NEW item row after character creation**
(FINDINGS_R21 A1); server-owned new-item identity and slot allocation is explicitly
unrecovered (V121). Any grant writer is new code that must follow the guarded merge-lane
pattern, because dispatch is unguarded and an escaping DB exception kills the server
(FINDINGS_R21 N1).

---

## 4. [OUR DESIGN] the server-side model

On our architecture ALL loot intelligence lives on the server and expresses itself only
through frames the client already renders (the same discipline as the mob-aggro draft).
Each hostile placement gets, on death, a server-side loot event: roll the drop sets
(Door 2), then GRANT the rolled item(s). The realistic-to-the-original expression is a
ground object the player walks over (Doors 3+4) -- but that path is unbuilt and unproven.
The design tension to resolve, explicitly, before building:

- **"Like the real thing"** wants a ground DropThing object + PickupTerrainThing request.
  That respects design principle #5 but sits entirely on [NEGATIVE/UNKNOWN] transport;
  it cannot be built honestly until Door 3's transport is decoded.
- **A direct-to-backpack grant** (skip the ground object; on kill, send an ItemBag delta
  straight to the killer's backpack via Door 5, persist via Door 6) is buildable on
  proven-shaped carriers TODAY -- but it CONTRADICTS how the original game dropped loot,
  so under principle #5 it is a scaffold, not the destination. If built, it must be
  clearly marked a non-canonical convenience and carry the nonclaim that the original
  dropped a ground object.

The honest reading: build the parts that are both provable AND canonical first (the
roller), decode the blocker next (DropThing transport), and defer the grant-carrier
choice until Door 3 is understood.

---

## 5. The honest checkpoints (proposals only -- nothing built this round)

1. **LOOT-ROLL-001 (buildable next round, cheapest honest win).** A server-side,
   pure-logic loot roller built from the section-1 client tables: template id -> resolved
   item list, unit-tested to Grade A against the frozen DROPS_* tables. No wire, no DB, no
   client. It does not move `monster_spawn_and_loot` (nothing renders), but it is the
   first real server piece of the row and it is fully honest. It would live as a
   census-free module + tests, likely a ledger entry of its own, and it feeds every later
   door.

2. **DROPTHING-TRANSPORT-PROBE (static, the blocker).** Decode the DropThing object
   family transport: does a ground object ride an undecoded `0x6E9D` sub-object (derived
   bits 0x04/0x08), its own vital, or scene data? Start from the reconcile/removal pass
   `0x446FE1..0x4470E5` (named but never examined) and the DropThing registration sites.
   The most likely and most informative outcome is another [NEGATIVE] (no wire path in the
   client for a server-projected ground item), which would itself decide the architecture
   toward a direct-grant scaffold.

3. **GRANT-ITEM PROBE (only after 1, and only as a marked scaffold).** If the ground path
   is ruled out, a bounded direct-to-backpack grant through the Door 5 delta carrier +
   Door 6 guarded writer, opt-in scenario, identity-pinned, one-shot, with the non-canonical
   nonclaim attached. Attended question: does a never-seen item appear in the bag and
   survive reconnect.

Order: proven-and-canonical first (1), decode the blocker (2), scaffold last and marked (3).

---

## 6. MATERIAL CORRECTION to round-98 Door B (attack-task constructors) [STATIC]

The round-98 mob-aggro draft recorded Door B (a monster actually SWINGING) as
"structurally located, NOT proven," and listed "walk the CActorTask_UseBehavior /
PlayActionEvent ctors (unresolved custom RTTI)" as the highest-value open static question.
The round-100 dig RESOLVED those constructors. This section corrects the record; it does
NOT claim an attack loop works (see the standing blocker at the end).

**Method that unlocked it:** MSVC has no Complete-Object-Locator wiring vtable->name here,
but every game class carries a per-type token record and a slot-0 GetType thunk
(`mov eax,<token>; ret`), and each registrar stub binds the class NAME to that token.
Following name -> token -> GetType thunk -> vtable binds the whole CActorTask family
statically (reproduces the Dead=0xF0F048 anchor).

**Resolved bindings [STATIC]:**
 - `CActorTask_UseBehavior`: vtable **0xf0ef10**, ctor **0x47ab30** (thiscall, ret 0x30),
   GetType 0x471dc0 -> token 0x102ed50; writes [task+0x10]=8 (a flags word, NOT a
   0x800000XX prototype code -- which is why the 0x472000-0x476000 KIND scan round 98
   used could never find it).
 - `CActorTask_PlayActionEvent`: vtable **0xf0ef28**, GetType 0x471f50 -> token 0x102ecfc.
   It is the BASE task; no standalone ctor exists -- UseBehavior embeds/derives from it
   (UseBehavior vtable slots [6..13] == PlayActionEvent slots [0..7]). [STATIC / partial
   NEGATIVE: PlayActionEvent is instantiated only as UseBehavior's base subobject.]

**Who constructs it, and the actor gate [STATIC].** The clean path is the fight-vital
consumer `0x7516c0` (adjacent GetType resolves to CFightMsgVital -- high-confidence, not
proven to the adjustor): it resolves the TARGET actor from a handle in the vital
(`0x402a20 -> 0x446170`), does a BEHAVIOR lookup `0x702a10`, allocates a task
(`0x442d50`, pool 0x102dca4), pushes the actor + the vital's scalar params, and calls the
UseBehavior ctor at `0x751809`. The ONLY actor-type gate on the construct path is an is-a
check INSIDE the ctor against `CActorBaseClient` (token 0x102ce88) -- the universal
client-actor root that CMyActor, CNetActor AND a server-projected CNetNPC all derive from,
so a projection PASSES it. Task existence (vtable + KIND) is committed BEFORE any gate,
and the bail target `0x47ae91` still returns a fully-allocated task; the gates only skip
the optional animation-model wiring (needs `[actor+0x14]` != 0, a render/anim
sub-component). No branch requires "is local player" or any server-authority flag.

**Q2 corroborated [STATIC]:** the CAIStateCombat node is a name-only RTTI registration
with no vtable/ctor/instances; CAIStateCombatProxy (vtable 0xf14958) is an inert stub
whose only methods are GetType and a deleting-destructor -- no tick/enter/update, so it
reads no field for combat decisions. Combat is not decided by this client FSM (consistent
with server-authoritative combat). Boundary: the base CAIState (0xf14a70) IS a live class
with real virtual methods that were NOT disassembled; the inert claim is scoped to the
CAIStateCombat/*Proxy nodes.

**Q4 corroborated [STATIC]:** neither carried-debt singleton can silently blank the CORE
damage numbers. `[0x10339B0]` = CMacroActionFactory (macro record/playback, local-player
scope), not on the HUD path. `[localplayer+0x420]` is a default-on, user-toggleable byte
gating a SECONDARY combat-text routine (`0x43fde0`) during fight-vital processing;
toggling it off drops that feedback but not the primary damage sprites (pool 0x102dca4 is
ungated by it).

**What this DOES and does NOT change.** It changes Door B's status from "constructors
unresolved" to "constructors resolved, and the client's attack-task construction is NOT
gated against a projected NPC." It does NOT open the attack loop: the standing blocker is
intact -- every observed BEHAVIOR lookup `0x702a10` returned NULL, the inbound ActionVital
path is PROVEN inert (SCENE-008), there is no original capture of a monster attacking, and
no server encoder exists. What round 100 proved is that IF a non-null behavior row and a
delivered fight-vital existed for a projected NPC, the client machinery would build the
task -- the remaining unknowns are the wire delivery and a populated behavior row, not the
construct path. The `mob_aggro_and_server_ai` coverage row stays `not_started`.

---

## 7. Open static-RE questions (next dig, highest value first)

1. DropThing transport (Door 3 blocker): decode `0x446FE1..0x4470E5` (the named,
   never-examined reconcile/removal pass) and the DropThing registration sites -- does a
   ground object have ANY server->client transport?
2. Which populated BEHAVIOR row (if any) a fight-vital would have to name for `0x702a10`
   to return non-null for a projected NPC -- the last unknown on the Door B construct path
   now that the ctors are resolved.
3. Whether the `0x4C13` v2 delta carrier accepts a novel item identity end-to-end at
   runtime (Door 5), and the server-owned identity/slot allocation policy (Door 6, V121
   unrecovered).
4. The `INSTANCE` table (033, 338 rows) lifetime/refresh/exit columns -- the only data
   lead for a spawn/respawn cycle (Door 1b).

---

## 8. nonclaims

- No original-server behaviour is claimed anywhere. The original server is closed,
  unpublished, and unrecoverable. The loot roll order/RNG, the ground-object transport,
  and the new-item identity policy are all unrecoverable; our reconstructions are ours.
- The client drop tables are a complete model for normal/equipment/special drops (they
  resolve 100%), but whether the original rolled client- or server-side is [UNKNOWN];
  quest drops are ~87% absent client-side.
- Doors 3 and 4 (ground loot object + pickup) have NO KNOWN WIRE PATH. The DropThing /
  PickupTerrainThing class names and derived ids are registration facts only; no
  transport, serializer, or capture exists. No claim is made that a lootable object can
  be made to appear today.
- Door 5 (display a granted item) is STATIC only; Door 6 (persist a new item) has no
  writer today and the schema-acceptance is a structural fact, not an exercised path.
- The round-99 hostility on 0x2001 is a synthesized faction splice onto a TOWN NPC; the
  13 real Port Royal hostiles are a design note, not a claim that HYP-PF-027 is wrong.
  The (player 1, monster 6) pair is a mutually-hostile pair in the shipped FACTION table,
  but the player-side faction value 1 is our composition and the coverage grade does not
  move without an attended eyewitness (GT-032).
- Section 6 resolves the Door B constructors and proves the construct path is not gated
  against a projected NPC; it does NOT claim a monster can attack today. Every prior
  behavior lookup returned null, inbound ActionVital is proven inert, and no encoder
  exists. `mob_aggro_and_server_ai` stays `not_started`.
- This draft adds no code, no scenario, no ledger entry, no coverage grade; it moves
  nothing on the wire and touches no DB. Full RE provenance for section 1/2/6 is in this
  round's three worker fact packs; the packs are working notes, and every number they
  carry is re-derivable from the cited const-data tables and binary VAs.

---

## ERRATUM 1 (appended by chief round 102, 2026-08-20) - the Q4 corroboration overstated

The Q4 paragraph above says "neither carried-debt singleton can silently blank the CORE
damage numbers" and calls `[localplayer+0x420]` a byte "gating a SECONDARY combat-text
routine (0x43fde0) ... but not the primary damage sprites (pool 0x102dca4 is ungated
by it)".  A round-102 static pass (FACTPACK_R102_TARGETVITAL_AND_FXNUMBER_GATES_STATIC,
byte-exact, 41/41 guards) refutes the safety claim for the numbers this project
actually photographs:

- The CHitResult display chain proven in FINDINGS-R93 and re-confirmed on screen by
  GT-024/GT-027 is `0x750770 -> 0x43FDE0 -> 0x43FBB0 -> FxNumber ctor 0xA7C010 ->
  glyph builder 0xA7EBA0`.  The floating 63/379/MISS! the testers photograph are
  drawn by exactly the routine this draft called "SECONDARY" (`0x43FDE0`).
- That routine is hard-gated at `0x43FE2C` (`cmp byte [localplayer+0x420]` -> `je`
  no-draw): byte == 0 silences EVERY damage number and the MISS marker, with nothing
  visible in any server log.
- The byte is a user toggle: input command `0x27` flips it (`0x42C68A
  mov [eax+0x420],cl` after `sete cl`), and it defaults ON at object init
  (`0x44CAC2 mov byte [esi+0x420],1`, ctor `0x44C990`).

CORRECTED CLAIM: `[localplayer+0x420]` DOES gate the CHitResult-driven damage numbers
end-to-end.  A stray hotkey that lands on input command 0x27 (the round-8 attended
session already proved unfocused keystrokes reach the hotkey map) will blank all
damage numbers for that session while the wire stays byte-identical - which is the
leading explanation for the GT-027 tester sessions that saw no numbers while the
Panya-driven session saw all four.  What remains UNKNOWN and out of scope here is the
separate "pool 0x102dca4" path this draft mentioned: its characterization is neither
re-verified nor refuted by the round-102 pass, and no claim about it survives this
erratum.  The original Q4 text above is kept unchanged per house norm.
