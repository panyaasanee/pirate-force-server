# OBJECT-POP-002 — authoritative scene-actor population runtime pass

Date: 2026-08-16
Result: Grade B controlled runtime pass

## Primary claim

The opt-in Foundation population adapter reproduced one exact authoritative
NPC-style scene-actor membership sequence through the unchanged GameClient:

- the first valid scene-1 TargetPos produced the nearest-20 initial generation;
- an exact byte-identical model-ready reapply followed after 3 seconds;
- one forward refresh retained 19 actors, admitted placement 87 with full
  MovementAttr, and omitted placement 82;
- one reverse refresh retained 19 actors, admitted placement 82 with full
  MovementAttr, and omitted placement 87, restoring the initial membership set.

Every captured population PC and frame is byte-identical to both the typed
Foundation builder at implementation commit `1d5a18d` and frozen V141
`make_v94_population_state`. Frozen V141 remained unchanged at SHA-256
`2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22`.

Capture root:
`GameClient/capture_object_pop002_25690816_161711`.
Isolated live database:
`state/object_pop002_25690816_161711.sqlite3`.

## Exact input and initial generation

At local time `16:21:20.296`, GAME frame 79 carried one exact 44-byte
TargetPos PC with SHA-256
`E98946FCF30D2DD2963D3940F7F1980AA61071AAC52A97E574D5FD30AE83E271`:

`x=-7363.837890625`, `y=-3010.798828125`, `z=186`,
`heading=4.327682018280029`, moving byte `0`, and final raw byte `0`.

Within that PC, the x tag is at offset `0x14` with data at `0x15..0x18`,
y at `0x19`/`0x1A..0x1D`, z at `0x1E`/`0x1F..0x22`, heading at
`0x23`/`0x24..0x27`, moving at `0x28`/`0x29`, and the final raw field at
`0x2A`/`0x2B`.

The server emitted `OBJECT_POP_V94_INITIAL_NEAREST20` at `16:21:20.319`:

- PC: 3,133 bytes, SHA-256
  `BB470F4A27FD69194E2A0D34E7E3C3C5FDCFFE733B6C1D2D7FBD24D625CC5912`;
- frame: 3,146 bytes, SHA-256
  `8501D9C18C30CEFECA2209EF1E99D578E90C9D982402E83896BE118A31F94630`;
- ordered placement indices:
  `65,1,0,22,16,86,80,85,5,92,84,89,145,50,144,39,30,91,88,82`.

The actor-stream count is 20 and the first actor begins at PC offset `0x11`.
The 20 actor-entry starts are:

`0x11,0xA5,0x139,0x1D5,0x275,0x315,0x3AD,0x44D,0x4EB,0x583,`
`0x627,0x6BF,0x765,0x805,0x899,0x92D,0x9CB,0xA63,0xAF7,0xB9B`.

All 20 entries have attr count 2 and exact attr order NPCAttr followed by full
MovementAttr. No actor is retained or omitted in this first generation. At
`16:21:23.319`, `OBJECT_POP_V94_INITIAL_MODEL_READY_REAPPLY` sent the same
3,133-byte PC and 3,146-byte frame byte for byte.

## Forward and reverse membership transitions

At `16:29:00.966`, GAME frame 310 carried exact TargetPos
`(-8377.1953125,-2894.089599609375,186)`, heading
`0.31856513023376465`, moving byte `1`, final raw byte `0`. Its 44-byte PC
SHA-256 is
`EF2FF9E2617A3531BD9BCF18EB6A3F7CE10AFCEE62E2AD2741FF6A0DE93214B0`.
The forward response followed at `16:29:00.995`:

- PC: 2,017 bytes, SHA-256
  `B629A2A56C60047ADD3BDA82425004561F11AC0B056E740125EB58A738D1538E`;
- frame: 2,030 bytes, SHA-256
  `DB1D9C4DC2078CE139B60AAFDD34DC433536190DDE0331E5685D64E157B1C205`;
- ordered current indices:
  `1,0,65,22,86,80,16,85,5,92,84,89,50,145,144,39,30,91,87,88`;
- entrant 87 begins at PC offset `0x6E3`, its NPCAttr ID tag is at `0x6F0`,
  and its MovementAttr ID tag is at `0x73D`;
- the other 19 entries carry NPCAttr only; placement 82 is absent.

At `16:29:51.663`, GAME frame 336 carried exact TargetPos
`(-7410.0771484375,-3178.767578125,186)`, heading
`0.31856513023376465`, moving byte `1`, final raw byte `0`. Its 44-byte PC
SHA-256 is
`DF5E8CC3F365687F48A6FD9CE73ECCA85CE445EBB3501C0930BB146FE2A6232C`.
The reverse response followed at `16:29:51.691`:

- PC: 2,031 bytes, SHA-256
  `7E0C9C4392F6E01FCC253C77A321CB500AAA3964ADF71213A398844F440D02F7`;
- frame: 2,044 bytes, SHA-256
  `B9B647CBE0169971E5ED122D6626021EDC9AE1C6E3C8E8486EF2E22EF87F867D`;
- ordered current indices:
  `1,65,0,22,16,86,80,85,5,92,84,89,145,50,144,39,30,91,88,82`;
- entrant 82 begins at PC offset `0x74D`, its NPCAttr ID tag is at `0x75A`,
  and its MovementAttr ID tag is at `0x7B5`;
- the other 19 entries carry NPCAttr only; placement 87 is absent.

The reverse current set is exactly the initial set. Within these two captured
transition packets, omission is the only representation of a leaving member:
across 370 decoded `STRUCTURAL_IDS` lines in the retained GAME (368) and
LOGIN (2) logs, there are zero DeleteActor/ID `0x36DB` occurrences and no
explicit DeleteActor label.

## Runtime health and direct UI observation

Seventy heartbeats followed the reverse response, from sequence 298 at
`16:29:53.095` through sequence 367 at `16:32:11.981`. Requests continued
through frame 407 and processed state at `16:32:12.268`. Client and server
stderr are both empty.

The Chief directly observed a populated radar and scene models in the client UI.
The Chief also directly observed a new human scene actor in the forward view and
a large Warden-style model in the reverse view (operator observation; no
screenshot retained). These observations are not bound to placement 87 or 82 and
do not prove that any particular omitted actor visibly despawned.

## Database semantic allowlist

The immutable pre-run database is 53,248 bytes/SHA-256
`2641F30BB8122BDE2F02CDC2095B867F934EEE2EBEE1C6D0F598B7A94B4C99F1`.
The immutable final database is 53,248 bytes/SHA-256
`41E2CBE45400DAEFF74E0AC01ABC46E02FDAF1302DE4473D891B3824E3753C5E`.
Both return integrity `ok` and zero foreign-key violations.

The account row, non-deleted `Arena01`, selector 0, identity
`0x10010001:0`, name/name key, creation fingerprint, character timestamps,
208-byte actor wire SHA-256
`DC16B24104E863D428B4BEF7F7CB47CCE8E5CB9FBF025AE36E558FA18704C66D`,
103-byte avatar wire SHA-256
`B8F3CBEBF0F7CCC071C3D4D46EF24BAF33DF2A2FEB87FA8CEF692D1551EC32C0`,
and migration versions/checksums are unchanged.

The complete pre-to-final logical-row semantic delta is limited to:

1. one new selected session
   `1ccb8ec1b7af4c69b0dfb2822bc48251`, generation 12, opened
   `2026-08-16T09:18:31.050925+00:00` and closed
   `2026-08-16T09:32:12.647542+00:00`; and
2. the selected character position changing from scene 1/sequence 0
   `(-7292.4833984375,-3187.03759765625,186)`, heading
   `0.18130016326904297`, to scene 1/sequence 0
   `(-7006.71337890625,-3136.764892578125,186)`, heading
   `0.31856513023376465`.

The final position timestamp is
`2026-08-16T09:29:53.244454+00:00`. Its XYZ and heading fields exactly match
the final raw TargetPos in GAME frame 338 received at local `16:29:53.228`;
that 44-byte PC has SHA-256
`844D1B88C74C7C121EEF86348F449BA3CBC623BFF3C316F4BA9CB43AFBFAFB78`.
TargetPos does not carry scene/sequence; those remain separate persisted Position
fields. No prior session row changed.

## Shutdown and artifact audit

Server stdout records the client connection closing, the GAME log closing, and
exactly one `[FOUNDATION] stopped`. The retained helper says it attached to the
console associated with exact server PID 21236, returned `ctrl_c_sent=true`,
then observed `server_running=false` and no listeners. Its UTC window is
`2026-08-16T09:33:39.3276386Z..09:33:40.2143660Z`. There is no server or
client exit-code sidecar, so this checkpoint does not claim exit code 0.

The adjacent manifest pins all 15 currently retained artifacts by exact path,
size and SHA-256. It contains the two audit scripts and their outputs, all four
retained protocol logs, both empty client streams, both immutable database main
snapshots, both server streams, and the shutdown helper result. No WAL or SHM
artifact is part of this checkpoint.

## Evidence ceiling and stop rule

This is a Grade B pass for one opt-in authoritative NPC-style wire population,
one exact three-second reapply, one forward membership change, and one natural
reverse reentry. It proves deterministic attr count/order, typed/V141 byte
parity, continued transport health, a durable final TargetPos checkpoint, and a
connection-local session close.

It does not classify any actor as a monster or remote player, prove authentic
world-population policy, bind the operator-observed models to exact placement
IDs, prove client-visible despawn, persist population membership, or establish
combat, faction, AI, item/container, vehicle, portal/environment, concurrency,
remote-client, or authenticated multi-account behavior. The runtime stop rule is
met; no additional run is needed for this primary wire-membership claim.
