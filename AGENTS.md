# Pirate Force ServerProject

This is the persistent working project for the Pirate Force local login/game
server reverse-engineering effort.

## Working directories

- Project root: `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject`
- Runtime/test client: `C:\Users\Panya\Desktop\Pirate Force\GameClient`
- Current implementation: `current\`
- Previous implementations: `history\` (reference only)
- Captures and logs: `evidence\` (reference only)
- Reverse-engineering source corpus: `references\sources\` (read-only reference)

Do not edit, rename, move, or delete anything under `references\` or
`evidence\`. Copy a file elsewhere first if derived work is required.

## Foundation checkpoint (2026-08-15)

V140 remains the latest runtime-proven evidence checkpoint. V141 is closed as a
legacy characterization baseline only: its source self-test passes and its exact
three-file package is byte-consistent, but no V141 runtime capture/report/backup
exists. Do not call V141 runtime-passing.

The modular foundation under `src/pirateforce_foundation/` adds SQLite-backed
account/character/session/position lifecycle without a V142 gameplay hypothesis.
Actor and AvatarAttr bytes remain opaque; job/class is not inferred. See
`STATUS.md`, `docs/EXPERIMENT_LEDGER.md`, and ADRs under `docs/adr/`.

## Current baseline

The current verified evidence checkpoint is V140. It derives through V139/V138/V137/V136/V135/V134
from frozen V131, which derives from V129 rather than the rejected V130 equipment
experiment. It preserves the proven V94 population transport, V97 default-talk,
V98 safe facing, V99 system message, V100 current-scene music, V102 inventory
unlock, V111 stateful stack merge, exact P30/P91 V119 population, V120
operational Backpack range, V122 cash transport, V123 four-item/equip-from-bag
capture, and V131 Port Royal docking-confirm request boundary. V135 adds the
runtime-proven P0/q3020 conversation and accept handshake. V136 adds the passing,
explicitly compositional q3020 action1 -> next-empty-request -> MARKER1 docking
prompt -> positive-confirm boundary. V137 sends one exact RuntimeRes v4 singleton
TeleportVital v4 after that confirmation and proves a healthy same-connection
transition to decoded MARKER1 XYZ `(-10322,-755,671)`. This proves post-init
TeleportVital position ownership for this client. V138 consumes the exact
post-transition 76-byte ready batch and successfully restores an authoritative
MARKER1-nearest population of 20 full-MovementAttr actors. V139 adds the strict
P86 Target+Choose/safe-face/conversation boundary but was operationally blocked
by camera reachability. V140 makes that boundary selectable with an explicitly
synthetic P86 visual harness at MARKER1 `+100X,+50Y`, then runtime-proves the
exact interaction and default-talk UI. This synthetic position is not authentic
placement or original-server population evidence:

- `current\pf_login_game_server_v140.py`
- `current\run_v140_port_royal_p86_harness.bat`
- `packages\PF_Login_Game_Test_v140.zip`

V123 adds data-backed Create Character Blade identity 4/template 2200002 in
Backpack slot 3. Runtime captured exact ItemOperate version 0, operation 5,
mapped dword 8, identity 4, then continued for 167 heartbeats with no response
or mutation.

V124 is a corrected negative request boundary and positive client-local tracker
boundary. It sent exact QuestOperateVital `0x3E34` version 3, action 1, quest
243, P91 qword context, and constructor-default remaining fields. The client
emitted zero QuestOperate requests, but immediately displayed decoded quest
`Oblation ของ Devil Fish 1` and objective `0/25 Viper Tooth` in its tracker.
Action-1 handler `0x61AAC3` calls `0x619210` with `Accept_Run` and then
`0x6193E0(quest_id,1)`, which inserts the quest into the client-local tracker.

The frozen V124 source/self-test/startup wording that calls action 1 an offer,
a selectable accept path, or predicts a resulting operation-1 request is
disproved by runtime and must not be repeated as truth. V124 does not prove
server QuestAttr persistence, authentic acceptance, rewards, or continuation.
Detailed report:
`reports/PF_RE_V124_Quest_Action1_Tracker_Boundary_20260814.md`.
Exact-three-file package SHA-256:
`314FA3D641379FBD6A19DA95B0F2DEC4F2D4948029E42C57FA9A8889567DFBC0`.
Verified checkpoint backup:
`backups/v124_quest_action1_tracker_boundary_20260814_221820/` (10 manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`376FD2C85F4B958CA3E6D9101DF3C7B57930D12976CD7116C10710EBBA245A1B`).

V125 completes the bounded action-6 capture. It sent exact QuestOperateVital
version 3, action 6, quest 243, P91 qword context, and constructor-default
remaining fields. The client emitted one exact RuntimeReq v0/mask2 singleton
QuestOperateVital version 3: operation 2, quest 243, and all other fields zero.
V125 sent no reply or mutation. The session continued for 61 heartbeats after
the request (87 total) with zero error markers. This proves the
`OpenAcceptUI_Run` operation-2 request boundary, not QuestAttr persistence,
acceptance result, progress, rewards, or continuation.

Detailed V125 report:
`reports/PF_RE_V125_Quest_OpenAccept_Op2_Capture_20260814.md`.
Exact-three-file package SHA-256:
`EA80FC3115ECA97A2CD11CC8828ABDB3EAAFC67926E4DBA17C061911FAB1E9A9`.
Verified five-version checkpoint backup:
`backups/v125_quest_openaccept_op2_capture_20260814_223520/` (12 manifested
V124/V125 runtime/source/package entries, zero mismatches; manifest SHA-256
`D2C968C31092051AD544E2D0EE6A5175E9910BFEF0269C13859127B549A3A73A`).

V126's offline ActionVital parser/build passed, but its live run selected P91
instead of P30. With zero P30 arm and zero ActionVital, that capture is failed
operational evidence only and does not validate or reject the parser. Report:
`reports/PF_RE_V126_Failed_Operational_P91_Mistarget_20260814.md`.

V127 completes the bounded quest-accept response and deterministic P30 target
lanes. The first exact V125-proven quest-243 operation-2 request after action 6
received exactly one V124-proven action-1/P91 response. The client accepted the
RuntimeRes v4 / QuestOperateVital v3 response and remained healthy. This is a
client-local/session acceptance boundary only: no QuestAttr, server
persistence, progress, rewards, completion, quest 244, or authentic P91 quest
ownership is proven.

V127 changed only the local StartGame MovementAttr XYZ to the decoded P30
placement plus 100 X and preserved zero-target Teleport byte-for-byte. Runtime
then produced exact P30 TargetVital `0x201F`, kind 2, with embedded ChooseNPC
`0x201F`. Pressing G opened a client-local modal but emitted zero ActionVital
and no alternate action request. Final state remained
`p30_action_armed=True/action_capture_count=0`; the only later non-empty request
was a normal settings update during closure.

Static follow-up proves that G is the Guild hotkey, not the proposed
ActionVital producer: `HOTKEY_TIP` row 79 is `กิลด์`, `KEY_TIP` row 71 is `G`,
and Guild path `0x67E770` calls `0x449B30`, checks global player
`+0x3EC+0x18`, and opens `Common_MessageBox` ID 153 when null. The non-null
branch resolves `CGCGuildModule`. `UI_MESSAGE` row 153 is
`ท่านมีกิลด์แล้วหรือยัง?\nถ้าเข้าร่วมกิลด์ ก็จะได้รับพลังกิลด์และได้เข้าร่วมกิจกรรมกิลด์อีกด้วย !`.
The V126/V127 G-to-ActionVital/`0xEA7E` association is disproved. Retire that
wording and test instruction. The 64-byte parser may remain only as an offline
structural artifact; recover its real producer and action meaning independently.

The V127 session completed 263 heartbeats, including 210 after the quest
response and 178 after P30 selection, with zero runtime error markers and empty
stderr. Report:
`reports/PF_RE_V127_Quest_Accept_P30_G_Negative_Boundary_20260814.md`.
Exact-three-file package SHA-256:
`3F5D202DD70BBC666A22AD12311D52611FF0D967B1EF8273DDDE5476A902B771`.
Verified backup and manifest are recorded in the report.

V128 recovers and runtime-proves the real `ActionVital 0x1AEA` / `0xEA7E`
input producer. The key distinction is exact: physical key code 71 is G, but
HOTKEY row ID 71 is `WIELD`, has `n_KEY_2=90`, HOTKEY_TIP `เก็บอาวุธ`, and
KEY_TIP row 90 `Z`. Resolver `0x5D0CD0` maps the physical key to normalized
HOTKEY ID; keydown dispatcher `0x450B20`/table `0x4519C4` sends ID 71 through
`0x451026` to producer `0x44BC70`. G remains separate HOTKEY row 79 `GUILD`.

Live V128 selected exact P30 TargetVital `0x201F` kind 2, then one Z press
emitted an 84-byte RuntimeReq containing singleton ActionVital v0 with qwords
`0/0/0x201F`, action `0xEA7E`, dword `+0x34=0`, finite heading/XYZ, and
`+0x48/+0x4A/+0x4C = 0/1/0`. The capture-only gate journaled
`V128_TARGET_BOUND_WIELD_Z_ACTION_CAPTURED_NO_REPLY`; no response or mutation
was sent. Treat its proven meaning only as WIELD/`เก็บอาวุธ`, a neutral
wield/stow toggle—not attack, combat, damage, FightAttr, AI, or skill behavior.

The inherited V127 quest operation-2/action-1 lane passed unchanged. The
session completed 155 heartbeats, including 73 after the ActionVital milestone,
with zero runtime error markers and empty stderr. Detailed report:
`reports/PF_RE_V128_Wield_Z_ActionVital_Capture_20260814.md`.
Exact-three-file package SHA-256:
`10400E9D2AA7EE6F44B6BF0D9990DB02B4CF32C3DC9730A4954ABC2F7571366F`.
Verified checkpoint backup:
`backups/v128_wield_z_action_capture_20260814_235039/` (nine manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`820E83A1F846AE424CCF28C2EF3B447A36A681B37F9A0A617BDAEF6DA7B2EFB4`;
final report, handoff, and AGENTS.md preserved beside the manifest).

V129 replaces only the level-53 quest-243 harness with the decoded level-1
quest 3020 at P0/template 1, identity `0x2001`. MOBS row 1 links quest 3020;
QUEST row 3020 names `Q_TELEPORT_WITH_VEHICLE1`, whose decoded `Accept_Run`
calls `Player.TeleportWithVehicle(Quest.Var2)` with data-backed `Var2=1`.

Runtime completed the exact action-6 / operation-2 / action-1 client-accept
sequence. At frame 39 the client emitted singleton QuestOperateVital v3 tuple
`(3020,2,0,0,0,0)` and V129 returned exactly one action-1/P0 result. The
client accepted it, but the travel hypothesis failed: during 225.041 seconds
and 112 successful subsequent heartbeats there was no `TeleportCheckVital`,
no post-action-1 `TeleportVital` or `TargetPosVital`, and no visually observed
teleport. The only later non-empty request was closure-time
`UserSetting_UpdateServerSettingVital`.

Static tracing resolves the negative: `Player.TeleportWithVehicle` is
registered at `0x462601-0x46262B` through Lua bridge `0x460AE0` to native
`0x45FA00`, which is exactly `xor eax,eax; ret 4` and reads no state/argument.
`Player.Teleport`, `Player.TeleportCheck`, and
`Player.TeleportThenPlayMovie` bind the same no-op stub.

Promote V129 as the current evidence checkpoint for client acceptance and keep
travel as a resolved negative boundary. Do not claim quest persistence or
successful transport, answer TeleportCheck, or invent a missing server-side
travel field/prerequisite. Do not revisit this script lane unless a different
authentic non-stub implementation is recovered.
Detailed report:
`reports/PF_RE_V129_Quest3020_Accept_Travel_Negative_Boundary_20260815.md`.
Exact-three-file package SHA-256:
`9A5992689D98EBE94CFDA68AEE04907D47A03F83DCC54B0097992A6B6CBAC9CF`.
Verified backup:
`backups/v129_quest3020_accept_travel_negative_20260815_001754/` (nine
manifested runtime/source/package entries, zero mismatches; manifest SHA-256
`68B9EC4EDC75D2E0836B09422EF6CB6D4BEA3C40DB1618F2C4A250118BF3C320`;
final report, handoff, and AGENTS.md preserved
beside the manifest).

V130 is a clean negative equipment-state boundary and is not a passing
baseline. It changed identity 4/Create Character Blade only from
Backpack slot 3/`+0x39=FF` to signed slot `-1`/`+0x39=3`. Runtime showed
Backpack `3/40`, an empty Character `ITEM_RH_ONE`, and zero ItemOperate
operation 6 after controlled right-click and left double-click. The session
continued for 252 heartbeats with zero error markers and empty stderr.

Static tracing explains both failures. StartGame Backpack apply
`0x5A2970 -> 0x5A1240` sign-extends ItemAttr `+0x34` and rejects negative
slots at `0x5A124E`, so identity 4 never entered the live inventory manager.
Initialized capacities 40/40/80/40/30 and initializers
`0xBEB3C0..0xBEB4DF` prove slots `0..229`; equipment scans `0x5A1630` and
`0x5A1780` use the final reserved range `200..229`.

The Character equipment UI separately queries `CollectionBagAttr 0x3CD0` at
`0x5832EA`; V130 supplied none. Its exact serializer is vtable `0xF0EAF8`
slot 13 `0x471830`: ItemBag body plus constructor-default tagged u16
`+0x8A=8`. Operation-6 path `0x582730` first resolves an identity from the
CollectionBag-built equipment map and then looks up the same identity in live
inventory with `0x5A0120`, proving both states are required.

The exact absolute equipment slot inside `200..229` and original-server
allocation policy remain unresolved. Do not choose slot 200, 203, or another
member by guess, and do not build the next equipment version until that value
is evidence-backed. Detailed report:
`reports/PF_RE_V130_Equipped_Blade_Negative_Boundary_20260815.md`.
V130 exact-three-file package SHA-256:
`6DEA3EAFA75B5D08483299865FFBD8AB11326608D9916019BF2E7C96D53A15D9`.
Verified negative checkpoint backup:
`backups/v130_equipped_blade_negative_20260815_005123/` (nine manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`ABC349CA9D10220BE99FFABFE431AD4E7262AA0A2CFDAFB11D47825F8C5EB8E7`;
final report, handoff, and AGENTS.md preserved beside the manifest).

V131 derives from frozen V129 and deliberately inherits none of V130's
rejected equipped-state bytes. It sends one statically exact singleton
`TeleportCheckVital 0x4477` version 0/value 1 inside RuntimeRes version 4,
mask `0x02`, with the required trailing `0B 00`. Constructor/reset `0x44B980`
and serializer `0x5E6670` prove the nested version and sole tagged u16 field.

Static UI/data correlation after runtime proves that `+0x14=1` is MARKER row
ID 1, whose `n_SCENE1` resolves Port Royal. The client displays `UI_CONFIRM`
row 22, `รายงานกัปตัน เรือกำลังเทียบท่า $V1`, and its callback sends
TeleportCheck only for confirmation result 1. This is a positive Port Royal
docking-confirm request, not an automatic echo or mismatch reflection.

Runtime sent the exact 25-byte decompressed UI trigger at `01:02:55.946`.
After one confirmation click, frame 100 at `01:04:29.283` returned exactly one
23-byte RuntimeReq version 0/mask `0x02`/singleton request with nested version
0, value 1, and zero trailing bytes. V131 journaled it and sent no response or
mutation. The session completed 145 heartbeats, including 72 across 144.843
seconds after the request, with zero runtime error markers and empty stderr.

This proves the Port Royal docking-prompt/positive-confirm request boundary.
It does not prove completed teleportation, quest causality, vehicle state, or
the required server response; do not reply until an exact handler or original
capture proves the next action. Frozen V131 source/self-test/package labels
`challenge`, `echo`, and `semantics_unassigned` are superseded terminology;
the runtime artifacts remain frozen for byte-reproducibility. Detailed report:
`reports/PF_RE_V131_TeleportCheck_Challenge_Echo_Capture_20260815.md`.
Exact-three-file package SHA-256:
`18F9092C0FA03B21EAD9B42DC8F91EAF0B25F29C40A6E6078C3C33FCE5F3A6B5`.
Verified checkpoint backup:
`backups/v131_teleportcheck_challenge_echo_20260815_011204/` (nine manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`CA7D5017BBBBCD0F38BE643BA1EFE657942E63B3D8F1834F049451BA998D54CC`;
final report, handoff, and AGENTS.md preserved beside the manifest).

V132 is a clean negative HOTKEY-9 selection boundary and must not replace V131
as the passing baseline. Current-client data maps HOTKEY row 9 to
`SELECT_TARGET`, physical KEY_TIP row 9 to Tab, and HOTKEY_TIP row 9 to
`เลือกศัตรูที่อยู่ใกล้ๆ`; dispatcher `0x450B20` routes normalized ID 9 through
`0x451032`. V132 restored the V127/V128 P30+100X observation point, retained
isolated P0/P30/P91, and armed only after the exact population reapply.

With no prior mouse target, one Tab press emitted zero TargetVital and zero
positive P30 `0x201F`/kind-2 marker. The session completed 88 heartbeats,
including 63 over 125.418 seconds after the arm marker, with zero runtime error
markers and empty stderr. This proves only the negative under that exact state;
it does not disprove the data labels or establish an unproven range, UI-focus,
actor-class, or client selection-list gate. Do not modify unknown actor fields
to force a request. Detailed report:
`reports/PF_RE_V132_Tab_SelectTarget_Negative_Boundary_20260815.md`.
V132 exact-three-file package SHA-256:
`0E5E3AAD9171F98FCF6B9AFA8DDC0EC36BCF1088CE81D7748CB7629E6C50B2BC`.
Verified negative checkpoint backup:
`backups/v132_tab_select_target_negative_20260815_014135/` (nine manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`568B2D7E4B1D3F0A2EC33BFF408745FB58037266C9258CD564AF41E9F1F30CD0`;
final report, handoff, and AGENTS.md preserved beside the manifest).

V133 is a negative relation-display reproduction only. Its P70/template-71
actor wire is byte-identical to V74, but current session state produced a
TALK/yellow presentation and Tab emitted no target request. Do not guess a
faction/relation field; V133 was not promoted. V134 then introduced the exact
P0/template-1/q3020 conversation state machine, but its first operational run
missed the actor and produced only ground auto-run TargetPos requests. That run
did not validate or reject the handshake.

V135 is the proven prerequisite baseline. It preserves V134 packets and moves only
the local StartGame Y float by 50 units for a lateral observation harness. The
decompressed StartGame response differs from V134 at exactly offsets 222 and
223. Exact P0 remains at relative `(+100,+50,0)`; initial P0/P30/P91 population
and zero-target Teleport are byte-identical.

Runtime selected P0 at `04:34:31.454` with TargetVital actor `0x2001`, kind 2,
and embedded ChooseNPC. The server returned safe full facing plus one exact
39-byte NPCConversation carrying q3020. The UI rendered the conversation and
emitted exact QuestOperate v3 operation 1 at `04:35:01.301`; V135 sent exact
action 6 once. The UI then emitted exact operation 2 at `04:35:11.479`; V135
sent exact action 1 once. All request default fields were zero and both full
requests were 43 bytes. Both responses were 45-byte RuntimeRes payloads.

The session completed 101 heartbeats, including 53 after action 1, with zero
runtime error markers and empty stderr. This proves the ordered client-local
chain `ChooseNPC -> NPCConversation -> op1 -> action6 -> op2 -> action1`.
It does not prove QuestAttr persistence, rewards, progress, completion, travel,
vehicle state, or an original-server database transaction. Replays, wrong
tuples, wrong envelopes, and wrong ordering remain strict no-reply paths.

Detailed report:
`reports/PF_RE_V135_Q3020_Conversation_Handshake_Pass_20260815.md`.
V135 exact-three-file package SHA-256:
`0FE4C5E775C847D3294046168DEAFF84AA36FC884582B5629CE526CC5BB5DB62`.
Verified passing checkpoint backup:
`backups/v135_q3020_conversation_handshake_20260815_044150/`.

V136 is the current passing baseline. It preserves V135 byte-for-byte through
the action-1 response. That exact response arms one pending flag. The first
subsequent byte-exact 12-byte empty RuntimeReq version 0/mask 0/count 0 sends
the exact V131-proven MARKER1 Port Royal docking prompt once. The exact 23-byte
TeleportCheck version-0/value-1 positive-confirm request is captured once and
receives no reply.

Runtime repeated the full P0/q3020 conversation chain. Action 1 was sent at
`05:09:13.804`; the next exact empty request queued the MARKER1 prompt at
`05:09:14.217`, and the exact 25-byte prompt went out at `05:09:14.219`.
Positive confirmation produced exact TeleportCheck at `05:09:28.137`, captured
once at `05:09:28.142`. The session completed 119 heartbeats, including 65
after confirmation, with zero runtime error markers and empty stderr.

This is a passing compositional hypothesis connecting q3020's data-backed
`Var2=1` to the independently proven MARKER1 prompt. It does not establish the
original server's causal link and does not prove travel, vehicle state, quest
completion, QuestAttr persistence, destination direction, rewards, progress,
or the confirmation response. Do not add any such state without new evidence.

Detailed report:
`reports/PF_RE_V136_Q3020_MARKER1_Compositional_Docking_Pass_20260815.md`.
V136 exact-three-file package SHA-256:
`92ACDA5A642F275790CB333DE276B23620B477D881E8E50079F29F334B266797`.
Verified passing checkpoint backup:
`backups/v136_q3020_marker1_composition_20260815_051330/`.

V137 is the current passing baseline. It preserves V136 through the exact
positive MARKER1 confirmation, then sends one 64-byte RuntimeRes version 4 with
a singleton TeleportVital version 4. The target is decoded MARKER row 1:
scene 1, sequence 0, XYZ `(-10322,-755,671)`. Both target bytes and the final
u16 remain zero; direction 3 is not mapped. State is set before queueing, and
pre-sequence, malformed, and replay paths remain no-send.

The passing second runtime session captured the full P0/q3020 chain, queued the
transport once at `05:32:57.521`, and sent its exact 75-byte frame at
`05:32:57.526`. The same GAME connection emitted a three-vital transition batch
at `05:33:17.575`; the scene visibly reloaded at UI coordinates X -10322/Y -755.
A short W at `05:34:09.679` then produced singleton TargetPosVital payload
`2A004821C62A00C03CC42A00C027442A000000000B010B00`, whose first vec3 is
exactly the MARKER1 XYZ. This proves post-init TeleportVital transition and
local-position ownership. The session completed 127 heartbeats, including 62
after the V137 send, with 53 post-send receive frames, zero bad markers, and
empty stderr.

This remains an emulator-side composition. It does not prove authentic
original-server q3020/MARKER1 ordering, quest completion, QuestAttr persistence,
rewards, vehicle state, direction semantics, or original-server destination
policy. The first V137 attempt was operationally canceled by a PrintScreen
overlay/Escape before confirmation and produced no V137 send; preserve both raw
attempts in the checkpoint.

Detailed report:
`reports/PF_RE_V137_MARKER1_TeleportVital_Transport_Pass_20260815.md`.
V137 exact-three-file package SHA-256:
`DCF6AAEB1B6E14300C171F40548B3352A46F7A749E568A7035348C0719FFF74B`.
Verified passing checkpoint backup:
`backups/v137_marker1_teleport_transport_20260815_054009/`.

V138 is the current passing baseline. It gates on the exact live-derived
76-byte post-transition RuntimeReq version 0/mask 2/count 3 only after V137's
transport. The request carries Target clear, minimal Teleport ready, and
TargetPos at MARKER1. V138 immediately sends one authoritative destination
snapshot and commits one-shot/current membership state before queueing.

Membership is exactly
`[86,80,0,1,65,22,16,85,5,92,84,50,89,144,145,39,87,82,30,70]`.
All 20 receive full authentic placement MovementAttr. P30 retains exact
HP `3857/3857` and name `Tornado Eagle`; all others retain proven defaults.
The exact population PC is 3,152 bytes, SHA-256
`6B8DD30BBE29641D99849F96601B61C8F4791FD06F5C900CD095B67C50A40C64`;
the 3,165-byte frame is SHA-256
`7C844EC3CA4B39231AB9E25A2F14B00922BF7215357E3143E2840687846DAEA0`.

Runtime captured P0 Target/Choose, op1, op2, positive marker confirm, and the
exact 76-byte ready batch as event seq2 through seq6. The population queued at
`05:58:33.957` and sent once at `05:58:33.958`. The client remained at UI
coordinates X -10322/Y -755 and showed destination population including
`Prison Teller`. The session completed 192 heartbeats, with 57 heartbeats and
58 received frames after the V138 send, zero bad markers, and empty stderr.

No delayed reapply, message, music, ACK, StartGame, extra teleport, or
destination interaction is added. This does not prove authentic original-server
q3020 ordering, population timing/policy, quest completion, persistence,
rewards, vehicle state, interaction, or direction semantics.

V138 startup stdout retains one inherited V123-era sentence about a visible
blade at 4/40 and optional item-activation event-code-2 capture. It is stale
logging/documentation residue, not V138 runtime behavior. Remove or relabel it
in V139 without changing the passing protocol path.

Detailed report:
`reports/PF_RE_V138_MARKER1_Nearest20_Population_Reapply_Pass_20260815.md`.
V138 exact-three-file package SHA-256:
`C97BF8876FF3C7762ABD7675E285FBDE9E6C197DF2929428FEF76702A7F3432B`.
Verified passing checkpoint backup:
`backups/v138_marker1_population_reapply_20260815_060241/`.

V139 is a negative operational run and must not replace V138 as the passing
baseline. The full V137 transport and V138 population passed. At
`06:24:49.509`, the exact 44-byte singleton MARKER1 TargetPos armed the strict
P86 interaction once. It remained armed through 126 further heartbeats, but no
TargetVital/ChooseNPC for P86 actor `0x2057` occurred; consequently no V139
face snapshot or conversation was sent.

The blocker was camera/test reachability. Authentic P86 lies behind-left of the
marker at delta `(-652.885,-476.233)`, about 808.119 planar units away, while
the initial view showed P22/`Prison Teller` in front. Current Computer Use
cannot perform RMB-hold drag. Three short W attempts emitted the unchanged exact
marker TargetPos and did not move. V139 also deliberately disarms on a nonmarker
TargetPos, so walking toward P86 is not valid inside the armed sequence.

The session completed 191 heartbeats; 126 heartbeats and 126 received frames
followed the arm, with zero bad markers and empty stderr. This does not reject
the statically verified P86 Target+Choose parser, P30-preserving safe-facing
snapshot, or empty conversation; those paths were not reached.

Detailed report:
`reports/PF_RE_V139_P86_Interaction_Operational_Negative_20260815.md`.
V139 package SHA-256:
`311B77FE7D9239B51C6AE530463D81CFA0F0F0F3D914FE797427264DDA90D7BB`.
Verified negative checkpoint backup:
`backups/v139_p86_interaction_operational_negative_20260815_063044/`.

V140 is the current passing baseline. It preserves V139's strict exact-shape
interaction parser and every V138/V139 regression fixture. Its only runtime
harness change is P86 MovementAttr XYZ in the destination population and later
safe-face snapshot: MARKER1 `+100X,+50Y` at marker Z, exact
`(-10222,-705,671)`. This is synthetic operational geometry only, not authentic
placement, decoded ground, or original-server policy.

The V140 population PC/frame are 3,152/3,165 bytes with SHA-256
`0DB101113B5317822657CA965B1EBC50E239F9A423CF4CA307CA8B6006D1A188` /
`21F27276C9646EE961E68862041A1FD7F3F623AF36BD2402D8A3492F68FFA58E`.
They differ from frozen V138 only in nine P86 XYZ value bytes. The V140 face
PC/frame are 2,028/2,041 bytes with SHA-256
`B8F0B7E54B2A317109C174BBC31DD7EABC647EDE14E41874D12900EA1C983439` /
`6A682109699F6BD769F6A73B2C891BE43ED7534DFB7B64C93A9B371F0E2A4E89`;
they differ from frozen V139 only in twelve P86 XYZ/derived-heading value
bytes. P30 remains HP `3857/3857` and name `Tornado Eagle`.

Runtime queued the synthetic destination population once at `06:44:56.861`,
armed on exact marker TargetPos at `06:45:10.566`, and captured exact event
seq8/frame94 TargetVital actor `0x2057` kind2 plus embedded ChooseNPC at
`06:45:38.504`. It queued one full-20 P86-safe-face snapshot and unchanged
empty conversation at `06:45:38.509`. The client showed overhead title
`Vagabond Messenger`, dialog name `Mori Hiroko`, and expected local Thai
default chat. This proves interaction transport/client UI only; visible
name/text remain client-table data from an empty NPCConversation.

The run completed 153 heartbeats/raw frame162. After the V140 send it continued
for 67 heartbeats and 68 received frames over 134.810 seconds, with zero bad
markers and empty stderr. It does not prove authentic P86 position,
original-server order/population/timing, conversation persistence, quest/shop/
combat behavior, rewards, vehicle state, or travel completion.

Detailed report:
`reports/PF_RE_V140_P86_Synthetic_Harness_Interaction_Pass_20260815.md`.
V140 exact-three-file package SHA-256:
`4E199F2ADCF9325B949A82CC3C5B30F98D8EB29089D030575C4F98A7D56D0FF7`.
Verified passing checkpoint backup:
`backups/v140_p86_synthetic_harness_interaction_20260815_065019/`.

Do not repeat action 1 as an offer. Do not add QuestAttr or persistent quest
state until complete ownership and serialization are recovered.

V116 proves ActorAttr cash mask bit `0x800` and qword `+0xA8/+0xAC`; initial
cash is the data-backed Sword Soul price 10000. V117 sets exact P30/template31
Tornado Eagle HP to 3857/3857. V119 adds the exact target-panel name. V120
changes only live BackpackAttr `+0x68` from 0 to 1, enabling the base 40-slot
range and allowing the shop to see 37 free slots.

The exact runtime store sequence is now proven. One right-click on Sword Soul
emits `TradeCmdVital 0x23B5 v0` command 6, dword 0, detail identity 0,
template 2200009, quantity 1. Result 13 places it in the Buy cart. Buy plus
confirmation emits command 8, dword 0, no detail. V122 responds once with
RuntimeRes v4/trailing `0B 00` containing `UpdateAttrVital 0x309A v0` and the
complete current ActorAttr with only cash changed `10000 -> 0`. Runtime changed
the HUD from one gold to zero; a second Buy was blocked locally and emitted no
second command 8. There were 175 subsequent heartbeats and zero error markers.

V122 is not a complete purchase. It sends no TradeItemResult, BackpackAttr,
new ItemAttr, identity, slot, or ItemVaryAttr. Corpus/static audit proves that
incoming BackpackAttr replaces the visible item tree; result 15 and 17 both
reach ResetBuyItem; the client does not allocate identity or slot; response
ordering and Sword Soul vary wire remain unknown. Do not invent any of them.

Detailed report:
`reports/PF_RE_V121_to_V122_Final_Buy_Cash_Update_20260814.md`.
Exact-three-file package SHA-256:
`4A43C6841A9232A1119D43D90BB059530B2ED241F758B3C44D81D1A376752B9B`.
Verified checkpoint backup:
`backups/v122_cash_update_attr_boundary_20260814_203400/` (9 manifested
runtime/source/package entries, zero mismatches; manifest SHA-256
`38E42353849A8FBAD4782E5625E993752333BDDA223BF53911087778F7B3580C`;
final report, handoff, and AGENTS.md preserved beside the manifest).

V83 preserves all V82 packets, actor data, positions, and stable bootstrap. Its
only movement change is an absolute-deadline sender so logging and console
overhead do not stretch the intended 250 ms cadence.

Measured evidence:

- V82 stream intervals: 290-503 ms, average 357.2 ms.
- V83 stream intervals: 237-251 ms, average 249.3 ms.
- V83 sender lateness was normally 0.4-4.7 ms in the clean captured run.
- Baseline plus all 24 movement frames were byte-equivalent between V82/V83.
- Three subjects spawn on authentic Port Royal ground Z in separated lanes.
- The clean recording shows all three moving, holding, and returning together.

V84 preserves V83's bootstrap, model-ready baseline packet, three actor records,
lane geometry, 60-unit targets, 250 ms cadence, 240-unit range, and
absolute-deadline sender. It changes only the schedule: P84, P89, and P144 move
one at a time while full three-actor snapshots keep the inactive subjects at
their last proven home state. This resolves the identity ambiguity created by
overlapping labels before any actor-specific movement change is attempted.

Live V84 observation corrected the visual mapping: the P84/Qina phase moved
the green/gold model whose overhead label followed as Fighter Apprentice. All
three V84 models showed a run/stop/run presentation under the 60/0.25 stream.
The user confirmed that historical Atlantis was not present in V84.

V89 runtime passed completely. P5, P144, and P50 walked concurrently with
staggered starts, completed two 300x300 square cycles, returned exactly to their
starting points, and were visually smooth with no stops. Preserve V89 as the
golden concurrent ambient-walk baseline.

V90 runtime was tested and accepted by the user. Preserve it as the current
passing 20-actor local-population baseline: 17 nearest authentic static
placements plus the three V89-proven ambient walkers.

V92 runtime passed. It proves that every authoritative generation must retain
all 20 identities, while static actors can carry NPCAttr only and omit repeated
MovementAttr without disappearing or visibly stuttering. V93 preserves that
representation and adds the V72-proven P84/P89 walkers, for five walkers and 15
static members.

The user judged V93 repetitive and it added no new evidence. Do not continue
expanding walker count. V94 removes synthetic lane movement and tests actual
nearest-20 population streaming after 1000 units of player travel. Retained
members are NPCAttr-only; entrants receive authentic placement MovementAttr;
leavers are omitted from the new authoritative set.

V94 runtime proved repeated local membership refreshes. Some entrants make one
small stutter at spawn and then settle; this is explicitly deferred. V95 adds
TargetVital-aware facing: a current selected NPC gets heading-only MovementAttr
inside a complete 20-member snapshot; target clear/unknown identity gets no
response. V95 also suppresses ordering-only empty population refreshes.

V95 runtime rejected heading-only MovementAttr: clicking an NPC teleported it
to the player spawn area. Never send mask 0x02 alone for rotation. V96 derives
from V94 and sends no interaction response. It creates a live significant-event
journal so multiple user actions can be correlated in one session while raw
payloads remain intact. V96 also keeps the ordering-only refresh suppression.

V97 runtime passed. An empty, serializer-exact `NPCConversation` for a current
`ChooseNPC` opens the client's authentic local default-talk UI. Direct
`B_TEXTDATA_TH` parsing proves the apparent mismatches are two fields from the
same template record: MOBS_TIP `s_TITLE` is the overhead role label and
`s_NAME` is the dialog/person name. Confirmed pairs are Drunken Captain/Legend
Jack (template 6), Nautilus Leader/Carle (40), and Atlantis Prime
Minister/Plato (52). Their default Thai chat also matches the screenshots.

V98 runtime passed its focused safety test. It sends a complete 20-member
snapshot on `ChooseNPC`; only the selected actor has MovementAttr mask 0x03
with its exact placement XYZ plus heading toward the latest player target.
Atlantis/P50 remained at its placement, turned toward the player, and opened
the Plato default dialog. Never regress to V95's mask 0x02 heading-only packet.

V99 runtime passed. It adds binary-derived `ShowMessageVital` (`0x36D2`) with
one wide-string field and displays `Pirate Force local server online` once at
Port Royal runtime readiness. Runtime proved that every populated
`GSCN_RunTimeProtocolRes v4` must retain the trailing derived mask `0B 00`;
omitting it causes ErrorData=28317 even when the nested vital is valid.

V100 runtime passed. It adds constructor-default `MusicControlVital`
(`0x3EAF`): empty ANSI string plus mode 1. Constructor `0x5E4800`, serializer
`0x5E60D0`, and handler `0x5F06D0` prove this selects the current scene's local
music branch. The client accepted it, continued runtime traffic, and preserved
V99 message plus V94 population. Do not invent a track name or music ID.

V101 runtime passed. `BackpackAttr` is ID `0x1F81`, constructor `0x46AC70`,
vtable `0xF0EA88`, and serializer `0x469FA0`; its constructor-default wire is
`0B FF 32 00 00 00 00 00 00 00 00 0F 00 00 0F 00 00 0B 00`.
`StartGameRes` owns it as a separate collection member, not inside ActorAttr.
The client entered Port Royal, retained message/population behavior, and the bag
opened the authentic second-password prompt. A captured password submission
proved `CheckSecondPwdVital` ID `0x4B98` and a 32-byte uppercase digest payload.
No result response is sent until the handler result states are mapped exactly.

V102 runtime passed. Static handler branches map `CheckSecondPwdVital` result 1
to `OK` and result 2 to `Fail`; the related Change handler maps 1/2/3 to
`OK`/`CurrentPwdInvalid`/`NewPwdError`. V102 returns result 1, u32 zero, and an
empty ANSI string inside the required RuntimeRes v4 wrapper. The client opened
the authentic empty Backpack at `0 / 40`, heartbeats continued, and the final
raw log contained no error/exception/fatal/disconnect marker. Do not infer
password persistence or emit a populated ItemAttr until its complete identity,
slot, quantity, template, and container ownership are proven.

V102 report: `reports/PF_RE_V102_Inventory_Unlock_20260814.md`. Runtime/static
backup: `backups/v102_inventory_unlock_20260814_094550/`. Verified exact
three-file package SHA-256:
`D3273F1F6C0B56685816D4F55DBF099B586E6759D6BB34736B80F9A8620CCBCB`.

Post-V102 static recovery is complete for a one-item Backpack. `ItemAttr` is
ID `0x0ECD`, constructor `0x46B410`, vtable `0xF0EBB0`, serializer
`0x46BD30`; its exact nested order is qword instance sequence, dword global
template, word quantity, word signed slot, bytes `+0x38/+0x39`, then optional
nested-detail presence. `+0x36` is proven quantity and `+0x34` is proven slot.
ItemBag serializer `0x46F180` writes an ItemAttr collection followed by a qword
identity collection; insertion `0x46EC20` puts the same identity in both.
Lookup `0x4713C0` rejects negative slots and accepts slot 0.

The focused V103 candidate is client-data-backed: Store 1 lists global
template `2600001`, which is ITEM_MISC row 1 / `Adventure Key`, no equip/class
restriction, stack limit 25, usage/buff 0. Use server-issued item sequence 1,
quantity 1, slot 0, constructor defaults `+0x38=0`, `+0x39=0xFF`, no nested
detail, and the matching qword 1 in the second ItemBag container. Do not change
any other V102 behavior. Static report:
`reports/PF_RE_V102_ItemAttr_ItemBag_Static_20260814.md`.

V103 runtime passed and converts that static candidate into a verified client
state. The authentic Backpack opened at `1 / 40` and displayed one key-shaped
icon in slot zero. The exact 26-byte ItemAttr and 54-byte Backpack body passed
self-tests, CheckSecondPwd unlocked normally, heartbeats continued through 103,
and clean closure flushed complete logs with no error/fatal/28317/disconnect
match. This proves initial item construction and both ItemBag identity
containers; it does not yet prove item mutation, use, move, discard, buy, or
sell protocols. Report: `reports/PF_RE_V103_One_Item_Backpack_20260814.md`.
Verified exact-three-file package SHA-256:
`4AEC12B170D4AECC4399B12A4C48CE7CB555A53E9D5E25B1281BD6DC03C09B67`.
Verified backup: `backups/v103_one_item_backpack_20260814_103143/` (120
manifest entries, zero mismatches). V102 runtime files were then moved from
GameClient to the Recycle Bin; GameClient now contains only V103 runtime files.

V104 runtime captured one controlled drag of identity 1 from Backpack slot 0
onto slot 1. Exact request ID `0x4BED` resolves uniquely through the recovered
name-hash algorithm to `ItemOperateVitalReq`; the registered paired response is
`ItemOperateVitalRes = 0x4C13`. Request serializer `0x5E5AF0` proves byte/tag
`operation=4`, dword/tag value `1`, and qword/tag item identity `1`. The server
sent no response, the icon stayed in slot 0, heartbeats continued, and clean
closure flushed the logs with no error/fatal/28317/disconnect match.

Response serializer `0x5EDA20` and handler `0x5EF5E0` prove result byte,
optional ItemBagAttr, then a byte-counted list of qword identity + byte entries.
Deserializer `0x5EDB56` calls fixed ItemBagAttr allocator `0x46F4D0`; vtable
`0xF0ECB8` confirms serializer `0x46F180`, so this is not a guessed polymorphic
type. Handler `0x5A8A00` treats nonzero result as failure and processes the
ItemBagAttr/list only on zero. Combined with the independently proven ItemAttr
signed slot field, this supports exactly one next hypothesis: result zero, an
ItemBagAttr with identity 1 in both containers and slot changed from 0 to the
captured request dword, plus an empty affected-entry list. Do not add any other
field or operation.
Report: `reports/PF_RE_V104_ItemOperate_Request_Capture_20260814.md`.
Corrected exact-three-file package SHA-256:
`DC3F6B6253A5AB49020C726502DB3232AAC018F52E7F39A583B87B38B2449D83`.
Verified backup: `backups/v104_item_operate_capture_20260814_111326/` (164
manifest entries, zero mismatches), manifest SHA-256
`15645B9AACEA404E02FA819A13024B77D34DE7DDB906D2020D68A2753A091F73`.

V105 tested that one bounded response. The client recognized response ID
`0x4C13` but displayed `VitalData version mismatch` with decimal
`ErrorData=19475` (exactly `0x4C13`), so it never evaluated the ItemBagAttr
body and the key remained in slot 0. Constructor `0x5EBED0` supplies the exact
cause: after the base clears byte `+0x10`, instruction `0x5EBF3E` overwrites
that response version with constant 2. V105 incorrectly emitted version 0.
The only supported V106 change is nested ItemOperateVitalRes version 0 -> 2;
preserve every response-body and bootstrap byte. Report:
`reports/PF_RE_V105_ItemOperate_Response_Version_Boundary_20260814.md`.
V105 exact-three-file package SHA-256:
`968B395F91E1764CDAABA9F58FC810963D6789E261B54C105852B638E5E49935`.
Verified V105 boundary backup:
`backups/v105_item_operate_version_boundary_20260814_114147/` (22 manifest
entries, zero mismatches), manifest SHA-256
`660B8C8473228F55216D766DCB0E3D6820E290D4D60A9F619E92B3FE1BA76A42`.

V106 changed exactly one response-wire byte: nested ItemOperateVitalRes version
`0 -> 2`. Runtime accepted the registered response with no mismatch/error dialog
and continued normal requests/heartbeats. The proposed body was not a successful
move: after the response the Backpack counter changed to `0 / 40`; closing and
reopening it showed no item. This is a new body-semantics boundary, not evidence
for trying alternate unknown fields. Recover operation 4 and response
ItemBagAttr semantics statically before V107. Report:
`reports/PF_RE_V106_ItemOperate_V2_Accepted_Removal_Boundary_20260814.md`.
V106 exact-three-file package SHA-256:
`43A204C189973F945D4CAA78978581D05CFE4329302B8C304AEBFFF06B75371D`.
Verified V106 boundary backup:
`backups/v106_item_operate_v2_removal_boundary_20260814_120216/` (22 manifest
entries, zero mismatches), manifest SHA-256
`ED3994230D63C9156AA5FFE7CF24899D0617F9849A04EFF35B87F29E52F4D090`.

Original V72/V73 packages were recovered and compared. V72's fully smooth set
was P5/P84/P89; V73 added P50/P85/P144. Since V84 contained P144 but not
Atlantis, Atlantis is narrowed to P50 or P85. V85 spawns only P5/P50/P85 in
separated lanes and moves them sequentially with exact V72 walking cadence:
walk speed 150, two 150-unit targets 0.50 s apart, 300-unit leg, deliberate far
hold, and the same walking return. No ActionVital or unknown fields are added.

## Project constraints

- Work from the current version and change only what evidence supports.
- Do not brute-force or guess unknown protocol fields.
- Keep the stable login/game bootstrap unchanged unless direct evidence requires
  a change.
- Use `capture_v<version>` for runtime captures.
- Keep a live sidecar log that is readable while the game remains open.
- Compile and run the self-test before deploying a version.
- Compare serialized packets against the prior version when a change is intended
  to affect only scheduling or tooling.
- Verify package contents and SHA-256 when creating a ZIP.
- Deploy new test files directly to the GameClient directory.
- Once a new version is verified, move obsolete version files/capture folders in
  GameClient to the Recycle Bin so the runtime folder stays clean.
- Do not infer an NPC name solely from where a label appears on screen.

The user has relaxed the old requirement that every experiment ZIP contain
exactly three files when additional files materially improve progress. Prefer a
small, reproducible package; the V83 compatibility ZIP still contains exactly
`GameClient.local.bin`, the current server `.py`, and current `.bat`.

## Test workflow

1. Make a new version from `current\pf_login_game_server_v104.py` or its verified
   successor.
2. Run `py -3 -m py_compile <server.py>`.
3. Run `py -3 <server.py> --self-test-only`.
4. Deploy with `tools\deploy_current.ps1` after updating its version parameter.
5. Restart the server and client. Use `tools\wait_for_pf_stage.py` and
   `tools\PF_FAST_ENTRY_AUTOMATION.md`: press Enter as soon as each visible
   screen is ready, use `NotifyEnterCreateActor` for character readiness and
   `RUNTIME_RES_ACK_FIRST_REQ` for Port Royal readiness; do not add blind waits.
6. Start recording before pressing a movement key. Use
   `tools\capture_pf_window.py` for a bounded recording that stops itself.
7. Press one short movement key to produce the authentic `TargetPosVital` trigger.
8. Inspect `GameClient\capture_v<version>\GAME_LIVE.txt` while the game is open and
   correlate it with the recording.

## Corrected actor and display-name evidence

- V84 phase 1 proves P84/Qina is the green/gold model whose moving overhead
  label followed as Fighter Apprentice. This supersedes the prior visual-table
  row for P84.
- P89/Betula and P144/Jessica remain visually ambiguous until a complete
  sequential recording maps their phases.
- Historical Atlantis was absent from the P84/P89/P144 V84 set and is therefore
  narrowed to V73 additions P50/Plato or P85/Kaim.
- V85 and later runtime identity mapping proves Atlantis is P50/template 52.
- For templates 6, 40, and 52, the overhead labels are MOBS_TIP `s_TITLE`, while
  the conversation UI displays MOBS_TIP `s_NAME`. This is not an actor mismatch.
- A match to current client tables proves internal consistency for this client
  build; it does not by itself prove every remembered original-server costume
  or population choice.

These visual labels are observations, not proof that the placement-data names
are localized display names.
