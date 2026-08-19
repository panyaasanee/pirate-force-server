# Pirate Force RE checkpoint — V127 quest acceptance and P30 G negative boundary

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V127 preserves the verified V125 quest-open request, the isolated P30/P91
population, the complete four-item Backpack, and all earlier stable bootstrap
behavior. It adds two bounded changes: one exact action-1 reply to the first
sequenced quest-243 operation-2 request, and a P30+100X local observation point
that makes P30/Tornado Eagle unambiguous for the then-proposed, now-disproved
G-to-ActionVital test.

The quest lane passed. The client emitted the exact V125 operation-2 request,
V127 returned the exact V124-proven action-1 tuple once, and the client accepted
the bounded client-local acceptance sequence without error. P30 selection also
passed. The final G-action hypothesis is now disproved: pressing G opened the
client-local Guild message, not an ActionVital producer, and no `ActionVital`
or alternate action request was emitted. This corrects the hotkey association;
it is not a failure of the dormant generic parser.

## Quest operation 2 to action 1 — functional pass

At `2026-08-14T23:15:46.623`, frame 61, the client sent the exact 43-byte
decompressed request already captured by V125. The event journal decoded it at
`23:15:46.625`:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E 0B 03 12 F3 00 08 02 08 00 14 00 00 00 00 32 00 00 00 00 00 00 00 00 05 00`

Decoded fields are outer RuntimeReq version 0/mask `0x02`, one
`QuestOperateVital 0x3E34` version 3, quest 243, operation `+0x16=2`, and
`+0x17/+0x18/+0x20/+0x28` all zero.

V127 gated this exact request behind the already-sent action-6 UI and returned
one serializer-exact 45-byte RuntimeRes version 4 at `23:15:46.633`:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E 0B 03 12 F3 00 08 00 08 01 14 00 00 00 00 32 5C 20 00 00 00 00 00 00 05 00 0B 00`

It contains one `QuestOperateVital` version 3, action 1, quest 243, retained P91
context `0x205C`, constructor-default remaining fields, and the required
RuntimeRes trailing `0B 00`. The live milestone was:

`V127_QUEST_OPERATE_REQUEST_CAPTURED fields=(243, 2, 0, 0, 0, 0) capture_count=1 result=ACTION1_ACCEPT_SUCCESS_SENT_ONCE`

Static handler linkage remains the evidence boundary: the operation-2 producer
sets the quest-manager pending byte, while the action-1 consumer clears it,
calls literal `Accept_Run`, and inserts/refreshes the client-local tracker. This
does not prove server QuestAttr ownership, persistence, progress, rewards,
completion, quest 244 continuation, or authentic P91 quest ownership.

## P30 selection — pass

V127 changed only the local StartGame MovementAttr XYZ to the decoded P30
placement plus 100 units on X. The stable zero-target Teleport remained
byte-exact. Independent serialization audit proved that a V127 StartGame built
with the prior coordinates is byte-identical to V126, while the live V127
StartGame differs only in the three local position floats.

At `23:16:51.316`, frame 94, the client emitted an exact P30 TargetVital. The
event journal decoded it at `23:16:51.318` as identity `0x201F`, kind 2,
template 31/Tornado Eagle, current population member, with embedded
`ChooseNPC 0x201F`:

`32 1F 20 00 00 00 00 00 00 08 02 12 B6 0F 0B 00 32 1F 20 00 00 00 00 00 00`

Final raw state confirms `p30_action_armed=True` and
`action_capture_count=0`. V127 therefore resolved V126's operational P91
mistarget without altering the P30 actor record.

## G key — exact Guild-path correction and zero ActionVital

After the exact P30 arm, the user pressed G and observed a client-local modal.
Client data identifies the hotkey exactly: `HOTKEY_TIP` row 79 is `กิลด์` and
`KEY_TIP` row 71 is `G`. Static path `0x67E770` is the Guild path. It calls
`0x449B30`, then checks global player `+0x3EC+0x18`; when null it opens
`Common_MessageBox` ID 153 and returns, while the non-null branch resolves the
`CGCGuildModule` path.

`B_TEXTDATA` `UI_MESSAGE` row 153 is exactly:

`ท่านมีกิลด์แล้วหรือยัง?\nถ้าเข้าร่วมกิลด์ ก็จะได้รับพลังกิลด์และได้เข้าร่วมกิจกรรมกิลด์อีกด้วย !`

No `ActionVital 0x1AEA` arrived and the existing V126 milestone remained
absent. There was also no alternate non-empty action request. From the P30
target until normal closure, the only non-empty request was frame 263 at
`23:22:31.262`, `UserSetting_UpdateServerSettingVital 0x0F01`, emitted as part
of the client's closing/settings path. It is not an action candidate.

Consequently the V126/V127 association of G with ActionVital/`0xEA7E` is
disproved and must be retired. Frozen source comments, labels, self-test prose,
and runtime instructions that call G a generic target-bound action are not
evidence. The 64-byte generic parser may remain as an offline structural
artifact, but V127 does not validate its producer, action meaning, or runtime
reachability. Recover the real ActionVital producer chain independently; do not
repeat G or infer combat/attack semantics.

## Runtime health

The clean session sent 263 successful heartbeat responses. There were 210
heartbeats after the operation-2 request and 178 after the exact P30 target.
After P30 selection they ran from sequence 86 at `23:16:52.904` through
sequence 263 at `23:22:49.216`; intervals were 2002–2060 ms, average
2013.1 ms. Inbound traffic continued through frame 272 at `23:22:49.498`.

The finalized capture contains zero match for `ErrorData`, VitalData mismatch,
read failure, fatal, exception, traceback, disconnect, `28317`, or
`SEND_FAILED`. Server stderr is empty. Clean closure flushed raw GAME to
266,370 bytes, raw LOGIN to 2,326 bytes, live GAME to 66,252 bytes, and server
console to 65,548 bytes.

## Build and artifact verification

`py -3 -m py_compile` passed and the complete V127 self-test passed. The
self-test covers the exact 45-byte action-1 response, exact request gating,
pre-offer/replay/wrong-tuple/version/mask/count/trailing no-reply cases, the
P30+100X-only StartGame change, stable Teleport, V126 parser regressions, and
all inherited inventory/shop/bootstrap tests.

The package has exactly three entries and its embedded hashes match the frozen
current files:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v127.py`, 264,298 bytes  
  `403810D14708A491EA0DA39E77395D503C6AFD2900C19A74672950B9CD7A2605`
- `run_v127_port_royal_quest_accept_p30_g_capture.bat`, 477 bytes  
  `46C8E10F288E6008AE383226D49488B27C5A165B5DD7F8F9B4E6E118BF690223`

Exact-three-file package SHA-256:

`3F5D202DD70BBC666A22AD12311D52611FF0D967B1EF8273DDDE5476A902B771`

Flushed capture hashes:

- raw GAME: `82EE85CC22D64901A292BED963283652D19BD0482ED6C023E1B1AF2203C441C3`
- live GAME: `E5C174846EC4CC573F34F701B554EAA4C94C793542F18570572F6B439A8EEE34`
- event journal: `E167BAA8AD2683B055E01067FC970D2B1B583EE22484CCA2CCBEB583A12BC5CF`
- raw LOGIN: `0B87598C185D2D895FBA0C169323BCC3CA700AFD3D5C11DB979E8AE670401F61`
- server console: `59EC5CB634206EDEE5DAB0C0DB176721709C7874ED65A071D5C00E2211C14766`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified backup:

`backups/v127_quest_accept_p30_g_negative_20260814_232718/`

The manifest covers all six flushed capture artifacts plus the frozen source,
launcher, and package: nine entries with zero mismatches. The final report,
`handoff.txt`, and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`182036EFC7E6619081379B4E8941D89998D3F088EF183EE8F6980230395EB4B5`

## Disposition

Promote V127 to the current verified runtime checkpoint for its quest
operation-2/action-1 functional boundary and deterministic P30 selection.
Preserve the Guild-path correction and zero-ActionVital result as proof that G
is not the proposed producer. Do not claim a persistent server quest, do not
call the G modal an ActionVital, and do not reuse the disproved G/EA7E wording.
