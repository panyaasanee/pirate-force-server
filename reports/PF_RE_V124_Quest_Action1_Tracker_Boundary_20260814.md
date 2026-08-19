# Pirate Force RE checkpoint — V124 Quest action-1 tracker boundary

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

This checkpoint continues
`PF_RE_V123_Starter_Blade_Equip_From_Bag_Capture_20260814.md`. V124 preserved
the complete V123 bootstrap, four-item Backpack, equipment capture, isolated
P30/P91 population, and earlier shop/cash behavior. Its new delayed test packet
was one serializer-exact `QuestOperateVital 0x3E34` version 3 for decoded QUEST
row 243 and P91 actor context.

The live result corrects the pre-runtime interpretation of that packet. Action
1 is not a pre-accept offer that should cause a new operation-1 request. It is
an authoritative client-side post-request path that immediately inserts the
quest into the local tracker. V124 therefore produced a useful tracker/UI
semantics boundary, but its intended request-capture hypothesis failed.

## Exact packet tested

`QuestOperateVital` constructor `0x621810` writes nested version 3. Serializer
`0x621860` proves the complete body order and tags:

1. quest ID word at `+0x14`, tag `0x12`;
2. byte at `+0x16`, tag `0x08`;
3. action byte at `+0x17`, tag `0x08`;
4. dword at `+0x18`, tag `0x14`;
5. qword at `+0x20`, tag `0x32`;
6. byte at `+0x28`, tag `0x05`.

V124 sent quest 243, constructor-default `+0x16=0`, action `+0x17=1`, dword
zero, P91 identity `0x205C` as the qword context, and final byte zero. The
complete 45-byte decompressed RuntimeRes v4, including the required trailing
derived mask `0B 00`, was:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E 0B 03 12 F3 00 08 00 08 01 14 00 00 00 00 32 5C 20 00 00 00 00 00 00 05 00 0B 00`

The framed packet was 55 bytes. It was sent at
`2026-08-14T22:11:33.542` under the label
`V124_TEST_HARNESS_AUTO_QUEST243_ACTION1_ACCEPT_CAPTURE`.

The data selection itself remains exact and local-client-backed:

- QUEST row: 243;
- scene: 4;
- Lua script: `Q_GATHER1`;
- continuation quest: 244;
- quest title: `Oblation ของ Devil Fish 1`;
- target item template: 2500090;
- required quantity: 25;
- context actor: existing P91 identity `0x205C`.

## Corrected action-1 semantics

The static consumer explains the runtime result:

1. `0x61A950` dispatches action 1 to `0x61AAC3`.
2. `0x61AAC3..0x61AACF` copies the supplied qword into the quest UI context.
3. `0x61AB5D` calls `0x619210` with quest 243, the literal `Accept_Run`, and
   the qword context.
4. `0x61AB6D` calls `0x6193E0(quest_id, 1)`.
5. `0x6193E0` reads the decoded quest row, walks the tracker collection at
   object `+0x44`, inserts a missing quest ID through `0x60B940`, and refreshes
   the tracker when its second argument is nonzero.

That local insertion is why the client immediately displayed the quest title
and `0/25 Viper Tooth` objective even though no conversation/accept window was
visible and the user made no quest selection.

The separately proven operation-1 producer at `0x61BEB0` is not a request that
follows this action-1 response. It is the request that would precede an
original-server action-1 response when the user selects a genuine quest-choice
row. Sending action 1 directly skipped that prerequisite and executed the
client's post-request tracker behavior.

## Runtime result

The live V124 run establishes both a positive and a negative boundary:

- **Positive:** the client accepted the exact version-3 packet and inserted
  QUEST row 243 into its local tracker. The screenshot
  `capture_v124/V124_action1_tracker_runtime.png` records the quest title and
  `0/25 Viper Tooth` objective without a conversation window.
- **Negative:** the client emitted zero `QuestOperateVital` requests. Frames
  49 through 194 after the action-1 packet were empty RuntimeReq traffic only;
  the live event journal contains no quest request or quest milestone.

The session stayed healthy through inbound frame 194 and heartbeat 179. There
were 140 successful heartbeat responses after the action-1 packet. The game
and server then closed cleanly; raw GAME and LOGIN logs flushed to 167,828 and
2,326 bytes respectively. Raw GAME, live GAME, event journal, console, and
stderr contain zero match for `ErrorData`, VitalData mismatch/read failure,
fatal, exception, traceback, disconnect, `28317`, or `SEND_FAILED`. Server
stderr is empty.

Screenshot evidence:

- `capture_v124/V124_action1_tracker_runtime.png`
- SHA-256:
  `D1A7AB3795B0F4D053867A5A392B24D3E68D5387A17A616680B8EAE37111BB75`

## Explicit retraction of pre-runtime labels

The deployed V124 source, startup banner, and self-test contain statements that
action 1 is an "offer", opens a "selectable accept path", and should lead to
an exact operation-1 request. Runtime and the corrected consumer trace disprove
those statements. Preserve them only as the frozen tested hypothesis; do not
repeat them as established behavior in later source, reports, or handoffs.

The self-test remains valuable for packet construction, exact version/body
bytes, parsing, inherited regression, Snappy roundtrip, and package integrity.
It does not validate the claimed action-1 UI sequencing because that semantic
assertion was synthetic rather than observed.

## What V124 proves and does not prove

V124 proves:

- `QuestOperateVital` ID `0x3E34`, nested version 3, and six-field serializer;
- exact action-1 transport acceptance for quest 243 and P91 context;
- client-local action-1 tracker insertion and objective rendering from decoded
  client data;
- zero resulting QuestOperate request in the tested sequence;
- preservation of V123 and stable runtime health.

V124 does **not** prove:

- an authentic server-side quest acceptance or persistent QuestAttr state;
- that action 1 is a pre-accept offer;
- a selectable conversation/accept UI from action 1;
- a resulting operation-1 request;
- rewards, criteria progress, completion, continuation quest 244, or quest
  persistence across sessions;
- any response to a QuestOperate request.

Do not add QuestAttr state or server rewards based only on the client-local
tracker presentation.

## Build and artifact verification

The frozen V124 build passed the complete inherited self-test and exact packet
fixture, but its offer/request wording is semantically retracted above. The ZIP
has exactly three entries, passes integrity checking, and its embedded server
and launcher hashes match the current files.

Artifacts and SHA-256:

- `current/pf_login_game_server_v124.py`  
  `F806BE1C2EDBE52E797AADB7A69C16BD729345CDD96388FE7FD1D61EF2885641`
- `current/run_v124_port_royal_quest_accept_capture.bat`  
  `EEA98BFA845B28030446D6104B39AC1C112F74E458FD91F4045C16885ABCEC89`
- `packages/PF_Login_Game_Test_v124.zip`  
  `314FA3D641379FBD6A19DA95B0F2DEC4F2D4948029E42C57FA9A8889567DFBC0`
- raw GAME  
  `4C279E4704C958E6D16DAF7A5C3732E85D35571A06E9A1F3238758866B366383`
- live GAME sidecar  
  `16C916E6F1BDA99CB0FCF2DEB57717E923CF480D25693E280BA00951FC1C23CF`
- live event journal  
  `3F8557E044CE1923BB4E1FEF554CC946EA81B390ED36E56AC04862A629F36C67`
- raw LOGIN  
  `9A63630016AE16AF26A8648BD08FA75D901AF493AEA7BACB6DF6708020296DFD`
- server console  
  `7D223FFE3CD4AD93AD40B44F239D5C947C8ECB7CBC74C638EB452C82E42B283F`

Verified backup:

`backups/v124_quest_action1_tracker_boundary_20260814_221820/`

The manifest covers all seven flushed capture artifacts plus the source,
launcher, and package: 10 entries with zero mismatches. This corrected report,
the live handoff, and AGENTS.md are preserved beside it. Manifest SHA-256:

`376FD2C85F4B958CA3E6D9101DF3C7B57930D12976CD7116C10710EBBA245A1B`

## Next evidence boundary

Do not repeat action 1 as an offer. Static cross-audit supports a separate,
focused action-6 test because that consumer calls literal `OpenAcceptUI_Run`
and its final UI control produces operation 2 through `0x617800` without the
action-1 tracker insertion. That should be a new capture-only version with its
own exact body, negative tests, and no quest response or mutation.
