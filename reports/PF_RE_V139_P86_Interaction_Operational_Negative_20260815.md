# Pirate Force RE checkpoint — V139 P86 interaction operational negative

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V139 derives from the passing V138 destination-population checkpoint. Its
static/build boundary remains valid: after the exact V138 population, one
byte-exact singleton marker TargetPos arms a strict P86 interaction once; an
accepted Target(P86/kind2)+Choose(P86) shape would send one P30-preserving
full-20 safe-facing snapshot followed by an empty default conversation.

The runtime session did not reach that final user-input request. This is an
operational negative, not a protocol or serializer rejection. Keep V138 as the
current passing baseline.

## Exact live result

The complete prerequisite chain passed again:

- normal runtime at `06:22:58.811`;
- P0 TargetVital kind 2 plus embedded ChooseNPC at `06:23:30.450`;
- exact q3020 operation 1 at `06:23:47.235`;
- exact q3020 operation 2 at `06:23:51.272`;
- MARKER1 prompt queued at `06:23:51.657`;
- exact positive TeleportCheck confirmation at `06:24:07.373`;
- V137 transport queued once at `06:24:07.379`;
- exact V138 post-transition ready batch at `06:24:26.284`;
- V138 nearest-20 population queued once at `06:24:26.287`.

At `06:24:49.505`, event seq 7/frame 68 was the exact 44-byte singleton
TargetPos at `(-10322,-755,671)`. V139 recorded the arm milestone once at
`06:24:49.509`:

`V139_EXACT_MARKER_TARGETPOS_P86_INTERACTION_ARMED_ONCE`

Final state confirms:

- marker TargetPos capture count: 1;
- P86 interaction armed: true;
- P86 Choose capture count: 0;
- P86 safe-face sent: false;
- P86 conversation sent: false;
- V137 transport count: 1;
- V138 population count: 1.

There was no TargetVital for actor `0x2057`, no ChooseNPC for P86, no accepted
P86 interaction-shape milestone, and zero V139 face/conversation outbound
packets.

## Operational cause

Authentic placement P86 is at `(-10974.884765625,-1231.232666015625)`, which is
behind-left of MARKER1 by delta `(-652.884765625,-476.232666015625)`, planar
distance about `808.119` units. The initial camera instead showed P22, whose
overhead role label is `Prison Teller`, in front of the player. P22 is at
`(-6232,-1005.0001220703125)`, delta approximately `(+4090,-250)` from the
marker.

The current Computer Use backend cannot perform a true right-mouse-button hold
drag. Prior attempts to pass a right-button field were ignored and became
left-drag movement. Therefore it could not rotate the camera toward authentic
P86. Short W taps at `06:26:34.044`, `06:26:38.067`, and `06:26:42.078` did not
move the player; each emitted the same exact marker TargetPos payload and left
the V139 arm intact. No nonmarker TargetPos was captured.

This matters because V139 deliberately disarms the bounded interaction if a
nonmarker player-position update occurs after arming. Walking toward P86 would
therefore not be a valid substitute inside this exact test sequence even if W
movement had worked.

## Health and proof boundary

The session completed 191 heartbeats and ended at raw frame 194. After the exact
V139 arm, 126 heartbeats and 126 received frames continued; the final heartbeat
at `06:29:02.574` was 253.064 seconds after the arm milestone. Across all six
flushed artifacts there are zero ErrorData, version mismatch, `28317`,
traceback, fatal, SEND_FAILED, or disconnect markers. Server stderr is empty.

This run proves the V139 exact marker-TargetPos arming path integrates cleanly
after V138. It does not test or reject the P86 Target+Choose shape, safe-facing
snapshot, or empty conversation, because the required P86 selection never
occurred. A later operational harness must make authentic P86 selectable from
the marker or provide genuine RMB-hold camera rotation without guessing any
protocol field or changing P86's authentic placement.

## Frozen build verification

The independent pre-runtime audit passed `py_compile`, the full self-test,
strict shape/negative matrix, Snappy roundtrips, V138 serializer preservation,
and exact-three-entry ZIP integrity:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v139.py`, 354,769 bytes  
  `17796619037B41AB66DE612A4AECD7027950D7498C2398BE9F7772D6EED8D64F`
- `run_v139_port_royal_p86_interaction.bat`, 463 bytes  
  `A3F4A4636CA9E9083DA33032E8EF156F816DC32D782A64B64747A863986F68F1`

Package: `packages/PF_Login_Game_Test_v139.zip`, 4,383,018 bytes  
SHA-256: `311B77FE7D9239B51C6AE530463D81CFA0F0F0F3D914FE797427264DDA90D7BB`

Flushed runtime capture hashes:

- raw GAME: `2AE63778242E17C47BC1AA0C136CA1FB04EB20B9625A8F54950DC40A1959BA19`
- event journal: `34086F7D86DB9E6ABA37244B1A043BEC4419A9C03604885B73DAD8AF6A883998`
- live GAME: `4C7561F2F0E99EFC20E16D9B03A7181A2CE1B60DD8F5305EC72A72D4142355C3`
- raw LOGIN: `07DBCC8F2C400C558ABB2ACC57173BDB03C40E4E5D2A8CD782E0ACA286EB25B1`
- server console: `B48911F241F456FAFF2E564BF33532EFD386BBD15131DCCBD0A70A30D0A2964B`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified negative checkpoint backup:

`backups/v139_p86_interaction_operational_negative_20260815_063044/`

GameClient files remain in place. No cleanup was performed and no
`references/` or `evidence/` file was modified.
