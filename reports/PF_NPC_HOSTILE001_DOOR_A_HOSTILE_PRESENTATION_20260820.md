# NPC-HOSTILE-001 -- Door A of the mob-aggro design: a hostile presentation, on proven ground only (HYP-PF-027)

2026-08-20 - chief round 99 - **wire-layer + dispatch, headless, additive** - binary `GameClient/GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`

Reproduce: `py -3 tools/verify_npc_hostile_encoder.py` (63 guards, exit 0), `py -3 tools/pf_npc_hostile_headless_replay.py` (52 guards, exit 0), `py -3 -m pytest tests/test_npc_hostile_hypothesis.py tests/test_npc_hostile_dispatch.py -q`.

> **This is OUR design, not a recovery.** The original Pirate Force server is
> closed, was never published, and left no server->client capture of a monster
> deciding to be hostile to a player. The faction values used here (player 1,
> NPC 6) are our composition, chosen because they are the one pair a real
> client has already rendered as hostile. The original server's faction
> assignment is unknown and unrecoverable, and nothing below claims otherwise.
> No client has ever been shown one byte of this profile: whether NPC `0x2001`
> presents as hostile is GT-032, attended, not run.

## 0. What this round built, and the one question it will let the tester ask

The round-98 draft `drafts/MOB_AGGRO_SERVER_AI_STATIC_AND_DESIGN_R98_20260820.md`
ranked the three doors a fight needs -- HOSTILITY, ATTACK, HIT-LANDS -- by how
proven each one is, and named the only honest first checkpoint: **Door A,
hostile presentation, is the sole door already proven on the wire, so build
that and nothing else.** This lane (HYP-PF-027, milestone NPC-HOSTILE-001) is
that checkpoint.

It composes ONE frame and pairs it with one entry-side field. It answers one
clean attended question, GT-032: *does the real client render the
actor-entry-projected NPC `0x2001` as hostile -- red outline, red Tab target
panel/arrow -- when the server declares its faction, the way SCENE-005
rendered a faction on the scene-load NPC `0x203D`?* A negative is valuable: it
would say a spawn-time faction bit on this pipe does not reach the client's
relation read, which redirects Door A before anything is built on top of it.

## 1. The two proven mechanisms this lane rests on

**SCENE-005 semantics** (runtime pass, 2026-08-15,
`reports/PF_SCENE005_FACTION1_HOSTILE_RELATION_RUNTIME_PASS_20260815.md`).
Faction is `BasicAttr` bit `0x0400`, a u32 at object offset `+0x68` (wire tag
`0x14`). The client relation lookup `0x4A1D50` compares TWO actors' faction
fields against a client-side table. With the local player's StartGame ActorAttr
carrying faction **1** and the scene NPC carrying faction **6**, a real client
rendered the pink/red name, the red outline and the red target panel, and
emitted the 31-byte `TargetVital` kind 1. **Both halves of that pairing are
load-bearing:** the arena-v2 negative
(`reports/PF_FOUNDATION_ARENA_V2_FACTION_ONLY_NEGATIVE_20260815.md`) plus the
relation-comparator trace
(`reports/PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.md`, 1,023 comparator
calls) proved an NPC faction of 6 *alone*, against the unmodified player's
constructor-default faction 0, presents as neutral. A lane that set only the
NPC's faction would re-run a proven negative and answer nothing.

**HYP-PF-023 transport** (`runtimeres_death_hypothesis.py`, GT-022/GT-025
attended PASS). The actor-entry pipe -- `GSCN_RunTimeProtocolRes` id `0x6E9D`
version 4, derived change mask bit `0x02`, one actor entry, actor_type 4
(CNetNPC) -- delivers a spawn for placement identity `0x2001` that a real
client renders. Its SPAWN frame carries a nested `BasicAttr`, so the faction
field has a proven truck to ride on.

## 2. What is composed, byte for byte

**The sweep half.** ONE frame, `HOSTILE_SPAWN`. It is the HYP-PF-023 SPAWN
frame for the same frozen probe (placement 0, template 1, identity `0x2001`,
preset `P_MALE_002_000_SP1`, full-mask MovementAttr, HP 100/100) with EXACTLY
ONE delta: `BasicAttr` bit `0x0400` set, carrying u32 faction **6** -- five
bytes spliced in ascending mask-bit order after the `0x0200` scene sequence,
and a mask that differs by exactly that one bit (`0x030C -> 0x070C`). Pins:
`pc_size` 178, `pc_sha256` `A85DD9F7..C21B`, `frame_size` 190, `frame_sha256`
`BB2B5948..5983`. Three copies agree -- module dict, scenario file, composed
bytes.

The strongest guard is **cross-lane byte equality**: the parent lane's own
composer (its module, its profile object) recomposes its SPAWN frame, and this
lane's PC must equal that PC with the five faction bytes at the computed splice
offset and a one-bit-wider mask. Everything after the splice -- the scene
fields, the NPC own-mask, the template, the preset, the whole MovementAttr --
is asserted byte-identical to the parent. This lane can therefore drift from
its parent only by turning two verifiers red at once. The constants are copied,
not imported (a containment census forbids cross-lane module names).

**The entry half.** Under the opt-in scenario the runtime recomposes the
full-writable StartGame response through the frozen
`player_wire.make_actor_attr_with_basic_faction` serializer -- which accepts
ONLY faction 1, scene_seq 0, scene_id 1 or 2, the exact SCENE-005/SCENE-007
probe -- and ONLY when the selected character is the canonical smoke identity
`0x10010001/0` the pins were computed for. The faction-1 ActorAttr is the
production ActorAttr plus exactly five bytes; the runtime measures that delta
and, on any other identity or any serializer refusal or any length drift, falls
back to the byte-identical production StartGame with a named event -- in which
case the sweep dispatch refuses by name. **The tester sees the full proven
pairing or no experiment at all, never a half-paired one.**

## 3. Fail-closed, and what the walkers read back

`production_allowed` is False in the module and in the scenario file. The
scenario JSON is checked against an EXACT allowlist (one extra or missing key
anywhere refuses). `BasicAttr` bit `0x0400` cannot be emitted on this path
without the wire unlock token, which is derived once from the allowlisted
scenario object and compared by identity everywhere (a value-equal forgery
opens nothing). The validator's walker requires the `BasicAttr` mask to equal
`0x070C` **exactly** -- any missing bit, any extra bit (the death lane's timer
bit `0x0080` structurally included) refuses before a single field is read, so
this module never has to NAME `0x0080` at all. The NPC faction must be 6 and
the player faction 1, pinned; every other value refuses by name. Zero HP
refuses by name (a spawn at zero HP would walk into the death lane's
predicates and answer a different question).

The offline verifier's independent walker and the headless replay's independent
walker each re-read the dispatched bytes from byte zero -- neither imports the
module's decoder -- and confirm actor_type 4, identity `0x2001`, mask `0x070C`,
faction 6, HP 100, the placed MovementAttr, and (in the replay) that the
StartGame PC contains the frozen faction-1 ActorAttr bytes and not the
production ones. The headless replay runs the real `make_state_class` dispatcher
on a `shutil.copyfile` copy of the database, deletes the copy on exit, and
asserts the source file's SHA-256 unchanged; the sweep writes no row and takes
no socket action.

## 4. Census, containment, and what did NOT move

NPC-HOSTILE-001 is `src/`'s **seventh** actor-entry call site
(`src_actor_entry_call_sites` 6 -> 7, `src_modules_building_actor_entries`
5 -> 6, both re-pinned in `tools/pf_runtimeres_actor_entry_static.py` with the
new module named). The new module builds an actor entry and **never names the
death-timer bit** -- it forbids every non-`0x070C` bit by strict mask equality
rather than by name -- so the SET census stays exactly the death lane, the
FORBID census stays exactly the visibility probe, and
`src_modules_mentioning_basicattr_bit_0x0080` stays 5. All three timer censuses
staying put is the design working, not an omission. See the round-99 NOTE in
`reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md`.

Containment: only `app.py` and `runtime.py` reference the module; the module
opens no database and no socket, imports only `population` constants, and
carries exactly one ledger marker.

## 5. Grade and nonclaims

**Grade B (wire + dispatch, headless).** Byte-exact composition, cross-lane
equality against the parent's own composer, both halves of the pairing proven
to leave the real dispatcher on a database copy, every driven wrong hold
refused by name. The client layer is **not claimed**: no client has ever been
shown one byte of this profile, and no coverage row grade moves until GT-032
runs.

Nonclaims: the faction values 1 and 6 are our composition, not the original
server's, which is unrecoverable; that the relation pair (1, 6) behaves on an
actor-entry-projected NPC as it did on the scene-load NPC in SCENE-005 is the
untested question, not a result; this spawn carries no name bit, so the
observables are the outline and target panel, not a red name board; no aggro,
no threat table, no chase, no attack (Door B stays closed); no persistence
(faction has no write path and this lane opens none).
