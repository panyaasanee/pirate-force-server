# Pirate Force RE checkpoint — V125 Quest OpenAccept operation-2 capture

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

This five-version checkpoint continues the corrected V124 action-1 tracker
boundary without changing the stable login/game bootstrap, the full four-item
Backpack, the V123 equipment capture, the isolated P30/P91 population, or the
earlier inventory/shop/cash behavior. V125 replaces only V124's disproven
automatic action-1 hypothesis with the statically distinct action-6
`OpenAcceptUI_Run` path and captures its exact operation-2 request without
replying or mutating quest state.

The runtime result is positive: the client accepted the exact action-6 packet
and emitted the predicted singleton `QuestOperateVital 0x3E34` version-3
request for quest 243, operation 2, with every remaining field at its
constructor default. The capture remained healthy afterward.

## Static basis

`QuestOperateVital` constructor `0x621810` sets nested version 3. Serializer
`0x621860` proves the complete body order and tags:

1. quest ID word at `+0x14`, tag `0x12`;
2. operation/action byte at `+0x16`, tag `0x08`;
3. action/result byte at `+0x17`, tag `0x08`;
4. dword at `+0x18`, tag `0x14`;
5. qword at `+0x20`, tag `0x32`;
6. byte at `+0x28`, tag `0x05`.

The action-6 consumer and operation-2 producer form one bounded chain:

1. action 6 reaches branch `0x61AD41`;
2. with the remaining byte zero it preserves the supplied P91 qword context;
3. `0x61AE2A` calls `0x619210` for quest 243 with literal
   `OpenAcceptUI_Run` at `0xF3367C`;
4. the UI event path stores action 6 at `0x61DBE5..0x61DBEB` and reaches the
   shared handler `0x61D1F0 -> 0x61D030`;
5. the final control branch at `0x61D0CA` calls producer `0x617800` with
   operation 2, quest 243, and dword zero;
6. constructor defaults leave `+0x17`, `+0x20`, and `+0x28` zero.

Unlike V124 action 1, this path does not call tracker insertion routine
`0x6193E0`. No QuestAttr, reward, progress, or continuation-state field was
invented.

## Exact outbound action-6 packet

V125 sent quest 243, constructor-default `+0x16=0`, action `+0x17=6`, dword
zero, existing P91 identity `0x205C` as the qword context, and final byte zero.
The complete 45-byte decompressed RuntimeRes v4, including its required
trailing derived mask `0B 00`, was:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E 0B 03 12 F3 00 08 00 08 06 14 00 00 00 00 32 5C 20 00 00 00 00 00 00 05 00 0B 00`

The framed packet was 55 bytes. It was sent at
`2026-08-14T22:29:33.908` under label
`V125_TEST_HARNESS_AUTO_QUEST243_ACTION6_OPEN_ACCEPT_UI`. The scheduler used
the already-proven population packet at delay zero, its reapply three seconds
later, then an incremental two-second delay for action 6: five seconds total
from initial population readiness.

## Exact inbound operation-2 capture

The client emitted one exact 43-byte decompressed RuntimeReq at
`2026-08-14T22:29:59.618`, frame 31. The event journal recorded it at
`22:29:59.621` as event sequence 2:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E 0B 03 12 F3 00 08 02 08 00 14 00 00 00 00 32 00 00 00 00 00 00 00 00 05 00`

Decoded fields:

- outer `GSCN_RunTimeProtocolReq` version 0, mask `0x02`;
- one nested vital;
- `QuestOperateVital 0x3E34`, version 3;
- quest ID 243;
- `+0x16 = 2` (operation 2);
- `+0x17 = 0`;
- `+0x18 = 0`;
- `+0x20 = 0x0000000000000000`;
- `+0x28 = 0`.

The runtime milestone was:

`V125_QUEST_OPERATE_REQUEST_CAPTURED_NO_REPLY fields=(243, 2, 0, 0, 0, 0) capture_count=1`

V125 sent no response and performed no quest mutation. The action-6 packet to
request interval was 25.710 seconds, allowing the user to operate the authentic
client UI rather than synthesizing a request.

## Runtime health and fast-entry timing

The final session sent 87 successful heartbeat responses. Heartbeats 14 through
87 (74 responses) followed the outbound action-6 UI packet; heartbeats 27
through 87 (61 responses) followed the captured request. Inbound runtime
traffic continued through frame 92 before clean client closure.

The finalized files contain zero match for `ErrorData`, VitalData mismatch,
read failure, fatal, exception, traceback, disconnect, `28317`, or
`SEND_FAILED`. Server stderr is empty. Clean closure flushed the raw GAME file
to 95,046 bytes and the raw LOGIN file to 2,326 bytes.

The event timeline also quantifies the improved entry workflow relative to the
immediately preceding V124 run:

| Milestone | V124 | V125 | Improvement |
| --- | ---: | ---: | ---: |
| GAME connection to `StartGameReq` | 51.836 s | 17.960 s | 33.876 s faster (65.4%) |
| runtime ACK to first `TargetPosVital` | 42.642 s | 2.332 s | 40.310 s faster (94.5%) |
| GAME connection to first `TargetPosVital` | 120.932 s | 37.836 s | 83.096 s faster (68.7%) |
| GAME connection to automatic quest packet | 128.937 s | 42.839 s | 86.098 s faster (66.8%) |

This measures the observed end-to-end runs, not a protocol guarantee. The
important operational change is immediate stage-driven entry and a short
movement trigger after `RUNTIME_RES_ACK_FIRST_REQ`, without multi-second blind
pauses between ready screens.

## What V125 proves and does not prove

V125 proves:

- serializer-exact action-6 transport is accepted for decoded quest 243 and
  the existing P91 context;
- the action-6 `OpenAcceptUI_Run` path can produce exact operation 2;
- the full operation-2 wire is version 3 with all non-operation fields zero in
  this observed request;
- the server can capture and journal the request without replying or disturbing
  the stable runtime;
- the faster stage-driven entry path materially reduced test setup time.

V125 does **not** prove:

- a successful or persistent server-side quest acceptance;
- a correct server response to operation 2;
- QuestAttr representation, progress, criteria, rewards, completion, or quest
  244 continuation;
- that P91 is the authentic original-server owner of quest 243;
- that the V124 client-local tracker survives relogging;
- any additional operation or unknown QuestOperate field semantics.

Do not respond to operation 2 until its authentic server result/state path is
recovered. Do not infer quest persistence from client UI alone.

## Build and artifact verification

`py -3 -m py_compile` passed. The complete inherited V125 self-test passed,
including exact 45-byte outbound and 43-byte inbound fixtures, nested version
3, outer version/mask/count gates, malformed/wrong-operation no-reply cases,
V123 equipment capture, V122 cash/shop, V111 inventory merge, stable bootstrap,
and Snappy roundtrip.

The ZIP has exactly three entries and its embedded server/launcher hashes match
the current files:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v125.py`, 236,662 bytes  
  `C35649F4DA01BDB1F01644DB7561B280DBFB0CA94E3BD5677A4A6ED1F71E27FD`
- `run_v125_port_royal_quest_accept_capture.bat`, 499 bytes  
  `1118AFB3CB982F1A76D32849665156CE709B19CDF3566F63D632E65E83424961`

Exact-three-file package SHA-256:

`EA80FC3115ECA97A2CD11CC8828ABDB3EAAFC67926E4DBA17C061911FAB1E9A9`

Flushed runtime hashes:

- raw GAME: `8B1247DA5A0390B4ED2C979173D36FE3218360CE7328CF021BCFD7D8C92133BA`
- live GAME sidecar: `0C629883A43D300499340524D1FA087BB0F91FE27EA0165CCC6FDE0B75C951A3`
- live event journal: `E283F22CD308D3F2329BF12DA6C4E7AB1F93BB160A96F85D1C9B49EB7B3EB8B3`
- raw LOGIN: `E5F4E0F1F8BE79517CC23EC4A4B2C5F679D7E5C9CF6D1CF06814F2ACADCEF3AA`
- server console: `9DBE396FBDAD055A25BD7922AC3A53006930D34DB2F6B1EF676232294E8BC672`
- empty server stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified backup:

`backups/v125_quest_openaccept_op2_capture_20260814_223520/`

The manifest preserves all six flushed V125 capture artifacts plus both V124
and V125 source/launcher/package triples: 12 entries with zero mismatches.
This report, `handoff.txt`, and `AGENTS.md` are preserved beside it. Manifest
SHA-256:

`D2C968C31092051AD544E2D0EE6A5175E9910BFEF0269C13859127B549A3A73A`

## Next evidence boundary

V125 closes the operation-2 request boundary but leaves the response/state
boundary intentionally open. The next quest change should be static-only until
a handler-backed response and complete QuestAttr ownership/serialization are
proven. Independent item, NPC shop, and monster work may continue from their
existing exact boundaries without altering this capture.
