# Pirate Force RE checkpoint — V131 Port Royal docking-confirm request

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V131 derives from frozen V129, not V130. It preserves V129's stable
bootstrap, exact P0/P30/P91 isolated population, quest/inventory/shop/cash
regressions, and ordinary four-item Backpack. In particular, identity 4 /
Create Character Blade remains in proven Backpack slot 3 with constructor
default `+0x39=0xFF`; none of V130's rejected initial-equipped bytes are
present.

The focused milestone sends one statically exact server-initiated
`TeleportCheckVital 0x4477` value-1 UI trigger and captures the client's
positive docking-confirm request. The clean runtime passed: after one
confirmation click the client returned the expected 23-byte RuntimeReq exactly
once at frame 100. V131 sent no reply or mutation. The session continued for
another 72 heartbeats and closed normally with no error markers.

## Proven serializer boundary

Pooled constructor/reset `0x44B980` and serializer `0x5E6670` prove:

- nested VitalData ID `0x4477` (`TeleportCheckVital`);
- nested version 0;
- exactly one tagged u16 field at object `+0x14`;
- no additional nested body fields.

Post-runtime static correlation assigns the field more narrowly than the
frozen V131 source did: `+0x14=1` selects MARKER row ID 1, whose `n_SCENE1`
resolves Port Royal. The client displays `UI_CONFIRM` row 22:
`รายงานกัปตัน เรือกำลังเทียบท่า $V1`. Its confirmation callback sends
TeleportCheck only when the callback result is 1. The captured request is
therefore the positive Port Royal docking-confirm request, not an automatic
echo and not a version-mismatch reflection.

The outbound wrapper is exact `GSCN_RunTimeProtocolRes` version 4, mask
`0x02`, singleton count 1, and the required trailing derived mask `0B 00`.

Exact decompressed 25-byte docking-confirm UI trigger protocol:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 77 44 0B 00 0F 01 00 0B 00`

The transport frame was 35 bytes. It was scheduled two incremental seconds
after the preserved three-second population reapply, for cumulative schedule
`0 + 3 + 2 = 5` seconds after initial population.

The frozen capture gate accepts only this exact request shape after that
server UI trigger:

- `GSCN_RunTimeProtocolReq` version 0;
- outer mask `0x02`;
- singleton count 1;
- nested `TeleportCheckVital 0x4477` version 0;
- tagged u16 value 1;
- zero trailing bytes.

Wrong envelope, version, count, value, or trailing variants remain no-reply
and do not advance the milestone.

## Exact runtime result

The server UI trigger was sent at `2026-08-15T01:02:55.946`. Its frozen runtime
label predates the corrected UI semantics:

`SENT label=V131_TELEPORT_CHECK_SCENE1_CHALLENGE_ONCE frame_bytes=35`

After one user confirmation click, frame 100 arrived at
`2026-08-15T01:04:29.283` with exact decompressed 23-byte protocol:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 77 44 0B 00 0F 01 00`

The independent event journal decoded:

- event sequence 2, frame 100;
- outer RuntimeReq version 0, mask `0x02`, singleton;
- `TeleportCheckVital 0x4477`, nested version 0;
- `field_u16_14=1`;
- nested body bytes 3, trailing bytes 0;
- raw nested payload `0F0100`;
- no response.

There was exactly one TeleportCheck event. The only earlier journal entry was
the stable bootstrap `TeleportVital`; no q3020 UI packet was auto-scheduled in
V131.

## Runtime health and timing

Key live-sidecar timestamps:

- GAME connection: `01:00:48.077`;
- StartGameReq frame 36: `01:02:02.854`;
- StartGameRes: `01:02:02.958`;
- stable zero-target Teleport: `01:02:03.658`;
- first RuntimeReq / RuntimeRes ACK: `01:02:27.023` / `01:02:27.025`;
- V131 docking-confirm UI trigger: `01:02:55.946`;
- positive docking-confirm request frame 100: `01:04:29.283`;
- closure-time settings update: frame 157 at `01:06:24.275`;
- final heartbeat 145: `01:06:54.126`;
- final received frame 172: `01:06:54.317`.

There were 145 successful heartbeats total. Heartbeats 74 through 145 give 72
successful heartbeats after the exact request, ending 144.843 seconds after the
frame-100 timestamp. The final state remained connected and initialized.

Across all six flushed capture files there are zero matches for `ErrorData`,
VitalData version mismatch, read failure, fatal, exception, traceback,
disconnect, `28317`, or `SEND_FAILED`. Server stderr is empty.

## Scope and disposition

V131 proves this exact UI/request boundary:

`server RuntimeRes v4 TeleportCheck v0/MARKER 1 -> Port Royal docking prompt -> confirm result 1 -> one client RuntimeReq v0/value1`

The value is now data-backed as MARKER row 1 / `n_SCENE1` / Port Royal, and the
request is data-backed as the positive docking confirmation. It still does not
prove that the request itself is a completed teleport result, a quest
operation, vehicle state, or permission flag. It does not prove teleportation,
answer a quest-travel request, or authorize a gameplay response. Keep the
request no-reply until an independent response handler or original-server
capture proves the next server action.

The frozen V131 source, startup text, self-test labels, launcher/package name,
and this report's compatibility filename use candidate terms such as
`challenge`, `echo`, or `semantics_unassigned`. Those labels are superseded by
the static UI/MARKER correlation above. The source and package remain frozen
byte-for-byte so the verified runtime artifact is reproducible.

Promote V131 as the current verified evidence checkpoint. V130 remains a
separate negative equipment-state checkpoint and none of its rejected bytes
are promoted.

## Build and artifact verification

After clean runtime closure, V131 passed `py_compile` and the complete inherited
self-test. The ZIP opens successfully, contains exactly three entries, and
each entry is byte-identical to its deployed/current artifact:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v131.py`, 282,659 bytes  
  `E95EC1F593650159C0D2F6D8BF359091493A1924A851FEA9E68D3309B9D4A9EE`
- `run_v131_port_royal_teleport_check_challenge.bat`, 486 bytes  
  `2B156256BAE373F9192AAB0C4F1626810AC6F46E4E9D50EF729C9B887C50309F`

Exact-three-file package SHA-256:

`18F9092C0FA03B21EAD9B42DC8F91EAF0B25F29C40A6E6078C3C33FCE5F3A6B5`

Flushed capture hashes:

- raw GAME: `DB95F9C9D47451768DB9534284E07822EB4D22D1324D3940E0C2246CB900CBDE`
- event journal: `DFAD38E72D9079231D5DFB5B2F02C1BFFD53BD335E770B82397AE9185F8FA9F5`
- live GAME: `3CDB1A8EE6C4568074037DB376003EDC02877EB59134F470A89846AA9E230C5C`
- raw LOGIN: `BBC9F3AFE1808A8B888B83D7542C4898223282C652672FC6EC43767836404C90`
- server console: `B586C56087B546A1DD9D19298598EECC9EB3C06F95C98F1925A6F4CE6A193ADB`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified checkpoint backup:

`backups/v131_teleportcheck_challenge_echo_20260815_011204/`

Its manifest covers the six flushed capture artifacts plus source, launcher,
and package: nine entries with zero mismatches. The final report,
`handoff.txt`, and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`CA7D5017BBBBCD0F38BE643BA1EFE657942E63B3D8F1834F049451BA998D54CC`
