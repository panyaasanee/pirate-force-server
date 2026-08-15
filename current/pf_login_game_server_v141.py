#!/usr/bin/env python3
"""Pirate Force localhost server experiment V141.

V116 preserves V115, V111's runtime-proven inventory stack merge, and every earlier
accepted behavior. It keeps the isolated test harness at two exact Port Royal
placements: P30/template 31 is a data-proven usage-1 monster and P91/template
91 is a nearby usage-2 NPC control. Usage 1 receives no NPC conversation or
facing response. Selecting P91 is explicitly a harness trigger for the
binary-derived TradeZoomVital v2 normal-store path; store 5 and its single
Sword Soul product are loaded by the client from decoded STORE_NORMAL data.
No NPC-to-store ownership is claimed and no purchase response is fabricated.

V112 runtime disproved the idea that TeleportVital's target vec3 positions the
local actor: the client still reported TargetPos=(0,0,931). V113 proved that
the local MovementAttr in StartGameRes positions the actor correctly, but P91
overlapped the player and a visual click was ambiguous. V114 used the already
bounded P91+100X observation point on the same Z and attempted store 5 as an
explicit delayed test-harness packet, without implying NPC ownership.

V114 runtime reached the registered TradeZoomVital but failed VitalData parsing
with ErrorData=0x2A7A. Static re-audit identified the exact cause: serializer
0x665332 calls 0x89A810, whose wire tag is 0x48 (UTF-16), for the string at
+0x24. V114 incorrectly sent tag 0x44 (ANSI). V115 changes only that empty
string's tag and preserves nested version 2 plus every other payload field.

V115 runtime accepted that correction and opened Store 5 with its one local
Sword Soul product. Static producer and handler evidence then proved that the
captured TradeCmd command 12 is the close-store notification, not a purchase.
The same audit proves player ActorAttr +0xA8 is the cash qword, serialized by
ActorAttr mask bit 0x800; the store cart compares that field with the purchase
total. V116 therefore changes only the initial local ActorAttr to carry exactly
10,000 cash, the decoded Sword Soul price, so one real Buy action can be
captured. No purchase response or inventory mutation is fabricated.

V117 changes only the isolated P30/template 31 Tornado Eagle's NPCAttr
current/max HP pair from the inherited 100/100 placeholder to the exact
client-data/static-derived level-27 STANDARD_MOB n_HPMAX value 3857/3857.
P91 remains the byte-identical 100/100 control. No FightAttr, ActionVital,
AI packet, skill, combat response, shop response, or inventory behavior is
added or changed.

V118 preserves V117 byte-for-byte outside the captured shop-cart path. Corrected
producer/controller tracing proves TradeCmd command 6/dword 0/detail is the
request to add a normal-store product to the buy cart: controller event type 8
is selected at 0x662CD2, but 0x662D0B explicitly supplies zero as the TradeCmd
dword serialized at +0x18. TradeItemResultVital result 13
dispatches the exact client event ``Trade_Shop/Store_ByItemOK``. V118 answers
only an exact command 6/dword 0/detail for Sword Soul template 2200009,
quantity 1. The response ItemAttr copies the captured identity/template/
quantity and retains constructor defaults: slot -1, +0x38=0, +0x39=0xFF,
and no nested detail. Command 8 and command 12 remain capture-only. Cash and
Backpack state are not mutated.

V119 preserves V118's exact shop-cart acknowledgment, cash, Backpack, isolated
P30/P91 population, and bootstrap. Its only population change is the statically
proven BasicAttr name field for P30/template 31: BasicAttr mask bit 0x0001 and
the exact current-client MOBS_TIP row-31 s_NAME ``Tornado Eagle``. P91 remains
byte-identical. Target selection and the HP/name target frame are client-local;
P30 TargetVital and ChooseNPC continue to receive no server response. No
FightAttr, ActionVital, AI, skill, combat, conversation, or facing field is
added.

V120 preserves V119 and changes exactly one live BackpackAttr wire byte. Static
client tracing proves the final tagged byte at BackpackAttr +0x68 is copied by
StartGame handler 0x5A2970 into inventory-manager range mask +0x30. Bit 0
enables the client's data-backed 40-slot base Backpack range; with the three
unchanged V111 items, free-slot counter 0x5A19E0 therefore reports 37 and the
normal-store UI caps that at its 18 buy cells. Bits 1/2 remain clear. The empty
Backpack constructor-default fixture remains zero, and no item, shop response,
cash, monster-name, population, or bootstrap field changes.

V121 preserves V120 byte-for-byte outside TradeCmd capture-state journaling.
Runtime V120 proved that the final Buy request is command 8/dword 0/no detail,
not the earlier static prediction of dword 11. V121 recognizes that exact wire
only after an exact cart-add request has received the proven result-13
``Store_ByItemOK`` acknowledgement, records the acknowledgement count and last
cart tuple, and deliberately emits no response or cash/Backpack mutation. The
captured command 12/dword 0/no-detail close attempt is journaled separately and
also receives no response; runtime showed that the shop remains open. Result
15-versus-17 selection and purchase-state transport remain unproven, so neither
is fabricated.

V122 implements only the independently proven cash transport boundary. After
one exact captured command-6 cart tuple has received the proven result-13 cart
acknowledgement, the first exact command-8/dword-0/no-detail request can change
the session cash from 10000 to zero. The response is one RuntimeRes v4 with its
required trailing derived mask, containing one UpdateAttrVital v0 and one full
56-byte ActorAttr whose only changed value is the proven cash qword. It sends
no TradeItemResult, BackpackAttr, ItemAttr, item identity, slot, detail, or
close response. Replays, wrong sequences, malformed/nonzero/detailed requests,
and any request after cash is zero receive no reply.

V123 preserves V122 and starts an independent starter-equipment display lane. The
initial full Backpack snapshot adds one client-data-backed Create Character
Blade: server identity 4, global template 2200002, quantity 1, bag slot 3,
constructor-default bytes, and no nested detail. EQUIPMENT_BASE row 2 has an
empty VARYDATA field, and the frozen real actor AvatarAttr independently carries
template 2200002 at both +0x54 and +0x58. The runtime milestone is bounded to
client acceptance of the full four-item Backpack and visible blade at 4/40.

Static producer tracing also proves the exact equip-from-bag capture boundary.
Item activation handler 0x5771E2 requires client event type 2 and passes the
selected item control's +0x94 value into 0x5A64A0. Its equipment path reads
decoded ``n_EQUIPSLOT`` through string 0xF0EC7C. For the blade row's exact
0x4000 value, 0x5A6814-0x5A683F maps the request dword to 8 by default or 16
when 0x448EC0(0x10) selects the alternate branch. Calls 0x5A6879/0x4DF1C0
recover the selected ItemAttr identity, and producer 0x59F800 writes operation
5, the mapped dword to request +0x18, and that identity qword to +0x20/+0x24.
V123 therefore journals only exact version-0, single-vital operation-5 requests
for identity 4 whose dword is 8 or 16, then emits no response or inventory
mutation. The new bag blade correctly retains constructor-default +0x39=0xFF;
that field belongs to the separate current-equipped/operation-6 lookup and is
not changed or guessed in this equip-from-bag capture.

V124 replaced only the delayed automatic Store-5 harness packet with one
serializer-exact QuestOperateVital v3 action-1 packet for client-data-backed
QUEST row 243 and the existing usage-2 P91 context. Runtime disproved the
offer interpretation: action 1 immediately applied the accepted quest to the
client, opened no conversation, emitted no QuestOperate request, and displayed
the exact local tracker ``Oblation of Devil Fish 1`` / Viper Tooth 0/25.
Static re-audit explains that result. Handler branch 0x61AAC3 invokes
``Accept_Run`` and 0x6193E0(qid, 1), which inserts the quest into the client
list and refreshes the tracker. Action 1 is therefore an acceptance result,
not an offer.

V125 derives from frozen V124 and changes only that automatic quest packet.
It sends handler action 6 at object +0x17 with quest 243 and the same P91 qword
context. Branch 0x61AD41 resolves ``s_ROLE_TALK`` and invokes the literal
``OpenAcceptUI_Run``. Its accept-control path at 0x61D030 sends operation 2
through producer 0x617800. V125 predicts and exactly gates only the complete
outer RuntimeReq v0/mask 0x02, singleton QuestOperateVital v3 request tuple
q243/op2 with +0x17, +0x18, +0x20, and +0x28 all zero. The action-6 packet is
scheduled two incremental seconds after the three-second model reapply, hence
five seconds after the initial population. The request is capture-only and
receives no reply; QuestAttr, rewards, progression, and continuation quest 244
remain outside this boundary.
Manual P91 selection retains V123's independently proven Store-5 harness path.

V126 preserves V125's corrected five-second action-6 OpenAcceptUI schedule and
all preceding runtime behavior. It adds only an exact, capture-only parser and
journal for the client-produced ActionVital 0x1AEA version 0. The focused gate
requires a preceding serializer-valid TargetVital version 0 selecting isolated
P30 identity 0x201F with kind 2. The next ActionVital must retain the statically
proved WIELD/``เก็บอาวุธ`` producer values: qwords 0/0/0x201F, action 0xEA7E,
dword +0x34 zero, final byte +0x4C zero, and finite heading/XYZ. Remaining
byte/word fields are decoded but deliberately left opaque. Every ActionVital
receives no response and consumes the target arm; no attack, combat, damage,
FightAttr, AI, or skill meaning is assigned to the target-bound wield/stow
toggle.

V127 derives from frozen V126 and combines two independently proven test lanes
in one session. First, the first exact quest-243 operation-2 request after the
action-6 accept UI receives exactly one serializer-exact action-1 acceptance
result with the retained P91 test-harness context. The client producer at
0x61D0DA sets quest-manager pending byte +0x88 to one after sending operation
2; incoming action-1 branch 0x61AAC3 clears the same byte, calls the literal
``Accept_Run``, and inserts a missing quest through 0x6193E0. Replays,
pre-offer requests, malformed packets, and wrong tuples receive no reply. This
is client-local/session-only acceptance: no QuestAttr, reward, progress,
continuation quest, or persistence is invented.

Second, the authoritative local StartGameRes MovementAttr uses a deliberate
P30+100X observation point
(1847.5244140625, -7837.69775390625, 931.0413208007812), mirroring the prior
proven P91+100X harness pattern. V112 proved that a nonzero TeleportVital target
does not position the avatar, so V127 preserves V126's stable zero-target
TeleportVital byte-for-byte and changes only the three local MovementAttr
position floats. P30 itself remains byte-exact at its decoded placement. This
is only a focused non-overlapping harness aid for selecting P30 and pressing Z,
not an authentic placement claim; V126's target arm, 64-byte ActionVital
parser, capture-only semantics, and every other bootstrap field remain
unchanged.

V128 preserves V127's packets and quest behavior byte-for-byte. It corrects the
ActionVital input provenance using current-client tables and exact dispatcher
code: HOTKEY row 71 is ``WIELD``, HOTKEY_TIP row 71 is ``เก็บอาวุธ``, its
physical key is KEY_TIP row 90 ``Z``, and keydown dispatch 0x450B20/0x4519C4
routes normalized hotkey ID 71 to 0x451026 -> producer 0x44BC70. Physical G is
HOTKEY row 79 ``GUILD`` and opens the local guild UI; it is not this producer.
V128 changes only descriptions, journal labels, self-test provenance, capture
folder, and launcher naming. It adds no response or gameplay semantics beyond
the neutral client-data label wield/stow toggle.

V129 derives from the runtime-passing V128 and preserves its WIELD/Z parser,
target arm, capture-only semantics, inventory, shop, and stable bootstrap. Its
focused quest lane moves from the level-53 q243 test harness to decoded
level-1 quest 3020 at authentic Port Royal placement P0/template 1, actor
identity 0x2001. MOBS row 1 links both QUEST_BEGIN and QUEST_END to 3020;
QUEST row 3020 names script Q_TELEPORT_WITH_VEHICLE1, whose decoded Accept_Run
calls Player.TeleportWithVehicle(Quest.Var2) with data-backed Var2=1. V129
sends the same serializer-proven action-6/op2/action-1 handshake using only the
new exact quest and actor tuple. It does not claim persistence, rewards, or a
server-side transport result.

The isolated authoritative population is expanded to exact placements
P0/P30/P91, and StartGame's local MovementAttr uses the deliberate P0+100X
observation point (-9039.95703125, -2780.045166015625, 223.29209899902344).
The stable zero-target TeleportVital remains byte-identical. After action 1,
every following nested RuntimeReq is journaled neutrally with raw bytes.
TeleportCheckVital 0x4477 is decoded only by its statically exact v0/u16 schema
and receives no response; no causal link to TeleportWithVehicle is asserted.

V131 derives from frozen V129, not V130. It therefore preserves V129's exact
four-item Backpack, including the Create Character Blade in ordinary bag slot
3 with constructor-default +0x39=0xFF; none of V130's disproven initial
equipped-state bytes are inherited. The q3020 action-6/op2/action-1 code remains
available as a regression lane, but V131 deliberately does not schedule the
action-6 UI packet in this runtime.

The isolated milestone is one server-initiated TeleportCheckVital challenge.
Pooled constructor/reset 0x44B980 and serializer 0x5E6670 prove nested version
0 and the single tagged u16 at +0x14. V131 sends value 1 in an exact singleton
RuntimeRes v4/mask 0x02 with the required trailing derived mask. It is scheduled
two incremental seconds after the preserved three-second population reapply,
so the absolute sequence is 0+3+2 = five seconds after initial population.
Only the exact client echo RuntimeReq v0/mask 0x02, singleton TeleportCheckVital
v0/value 1 reaches the milestone journal. It receives no reply. Wrong envelope,
version, count, value, or trailing variants remain no-reply and do not advance
the capture state. This is an isolated scene-1 challenge/echo boundary; it does
not assign teleport, quest, or vehicle semantics to the u16.

V134 derives from frozen V131 and returns to the exact, level-appropriate
P0/template-1 quest-3020 lane without inheriting V133's negative relation
experiment. It first exposes one nonempty NPCConversation descriptor for the
data-backed q3020 only after an exact current-P0 ChooseNPC. Static code proves
the descriptor wire (qid 3020 plus constructor-default byte zero), q3020's
special n_TYPE=20 row construction, and the selected-row producer that emits
QuestOperate operation 1. What that operation-1 request asks the server to do
in this combined path has not been observed live, so V134 labels the next
transition explicitly as a bounded integration hypothesis: only the exact op1
request after that conversation receives the already proven action-6
OpenAcceptUI packet. Only the exact subsequent op2 request receives the
already live-proven action-1 Accept_Run result. Replays, wrong order, malformed
envelopes, and every wrong tuple receive no reply.

V134 does not schedule V131's TeleportCheck challenge, and adds no QuestAttr,
reward, progression, persistence, teleport, inventory, or combat state. The
StartGame local MovementAttr uses P0-100X with heading zero: V133 runtime proved
this same structural observation pattern places an actor at +100X in the
initial camera view. P0 itself and the P0/P30/P91 population remain at their
exact decoded placements; stable zero-target Login Teleport is unchanged.

V135 derives from frozen V134 and changes only the local player's StartGame
MovementAttr Y coordinate for an operational visual harness. The V134 P0-100X
position put P0 on the avatar/cannon center line in the initial camera. V135
keeps the same X/Z and heading zero but moves the player 50 units below P0 on
Y, so P0 lies at relative (+100X,+50Y): a bounded 26.565-degree lateral angle.
The 50-unit offset is intentionally smaller than the proposed 100-unit side
offset, whose 45-degree angle has a higher risk of leaving the initial camera
frustum. No decoded placement or authentic ground claim is made for the player
harness point.

P0/P30/P91 population bytes, stable zero-target Teleport, NPCConversation,
op1/action6/op2/action1 packets and sequence gates, inventory, cash, bootstrap,
and every server-side gameplay semantic remain byte-identical to V134.

V136 derives from frozen V135 after its complete live quest-chain pass. It
preserves V135's exact visual harness, population, bootstrap, conversation,
op1/action6/op2/action1 wires, and strict quest sequence gates. After the exact
op2 request queues action1, V136 only arms a new pending state. The first exact
12-byte empty RuntimeReq v0/mask 0 request that follows queues the independently
V131-proven TeleportCheckVital v0/value-1 MARKER1 docking prompt exactly once.
The exact 23-byte positive-confirm request is journaled once and receives no
reply. Pre-sequence, replay, wrong envelope, wrong nested version/value, and
trailing variants never advance this state.

This is explicitly a compositional server hypothesis connecting q3020's
data-backed Var2=1 marker argument to the independently proven MARKER1 prompt.
It does not prove the original server's causal linkage and does not claim
travel, vehicle state, completion, persistence, direction mapping, or an
authentic destination response.

V137 derives from frozen, audited V136. Only after V136 captures the exact
positive MARKER1 confirmation does V137 queue one server-driven RuntimeRes v4
singleton TeleportVital v4. Its target is data-backed MARKER1: scene 1,
sequence 0, XYZ (-10322,-755,671). Every other TeleportVital field remains its
constructor default zero, including both target bytes and the final u16; the
decoded MARKER direction 3 is deliberately not mapped into either field. The
one-shot state is set before the packet is queued, so pre-sequence, malformed,
and replayed confirmation requests cannot send it.

This remains an isolated compositional transport hypothesis. It is not an
authentic original-server quest response, not a TeleportCheck reply, and not
evidence of completed travel, vehicle state, persistence, or direction-field
semantics.

V138 derives from frozen, runtime-passing V137. The client transition clears
the old world and then emits one exact 76-byte RuntimeReq v0/mask2/count3 batch:
TargetVital v0 clear, a minimal TeleportVital v4 ready record, and TargetPosVital
v0 at MARKER1. V138 gates by byte-exact raw PC only, requires the V137 transport
to have been sent, and queues one immediate authoritative nearest-20 population
snapshot. All 20 are new entrants with full authentic placement MovementAttr.
P30 alone retains its proven 3857/3857 HP and BasicAttr name ``Tornado Eagle``;
every other member retains the current proven default 100/100 and empty BasicAttr
name. State is set before queueing, and malformed, pre-sequence, or replayed
batches never send a second snapshot.

No delayed reapply, message, music, ACK, StartGame, or additional teleport is
sent. The current membership and refresh anchor become the exact marker-based
nearest 20, while ``npc_spawn_sent`` remains true. Destination interactions are
deliberately deferred because V137's last TargetPos is pre-transition and the
legacy facing builder would regress P30's proven HP/name. V138 makes no P86 or
other NPC interaction claim.

V139 derives from frozen V138 and adds one destination-interaction boundary
only. After V138 has sent its exact marker-nearest-20 authoritative snapshot,
one byte-exact singleton TargetPosVital v0 at MARKER1 replaces the stale
pre-transition player position and arms P86 exactly once. The following
interaction must match only complete V97-observed request shapes: TargetVital
v0 for P86/kind 2, followed by one or two ChooseNPC v0 records for P86, with an
optional final structurally complete TargetPosVital v0. Mixed identities,
Target-only requests, unknown tails, malformed records, wrong sequence, and
replays receive no response.

On that exact current-P86 interaction, V139 sends one complete authoritative
20-member snapshot preserving V138's NPCAttr semantics, including P30 HP
3857/3857 and BasicAttr name ``Tornado Eagle``. Only P86 receives MovementAttr
mask 0x03 with authentic placement XYZ and a heading toward the fresh marker
TargetPos; the other 19 retain NPCAttr only. It then sends the already
runtime-proven empty NPCConversation for P86. TargetVital alone never sends a
response. This is a bounded destination-facing/default-talk integration, not
an ownership, quest, shop, combat, or population-placement claim.

V140 derives only from frozen V139 and changes one operational harness detail.
In the destination population and the later safe facing snapshot, P86's
MovementAttr XYZ is overridden from its authentic placement to MARKER1
+100X,+50Y at the marker Z: (-10222,-705,671). The +50Y lateral offset follows
the bounded visual-harness pattern used to avoid direct avatar occlusion while
keeping the actor near the forward +X observation point. This is explicitly a
synthetic test position, not an authentic P86 placement or decoded-ground
claim. P86's NPCAttr/template/preset and every other actor's attributes remain
unchanged; P30 remains HP 3857/3857 with name ``Tornado Eagle``. The exact
marker TargetPos gate, strict actor-0x2057 interaction shapes, one-shot
behavior, empty conversation, bootstrap, quest, transport, and every other
wire remain V139-identical.

V141 derives only from the runtime-passing V140. It preserves every V140
bootstrap, quest, MARKER1 transport, destination population, exact P86
interaction, safe-face, and conversation wire byte. Its only functional
addition is the already runtime-proven V94/V95 local-population continuity
rule after the V140 P86 conversation has completed: when an exact decoded
TargetPos shows at least 1000 units of travel from the current refresh anchor,
recompute the nearest authentic 20 placements and send a new authoritative
snapshot only if set membership changed. Retained actors carry NPCAttr only;
entering actors carry their authentic placement MovementAttr.

P30 is special-cased in every V141 refresh snapshot to retain the proven
3857/3857 HP and BasicAttr name ``Tornado Eagle``. P86 remains at the V140
synthetic harness position only while retained, because retained members omit
MovementAttr. If P86 leaves and later re-enters, it receives its authentic
decoded placement MovementAttr like every entrant. This deliberately removes
the synthetic harness once the actor has crossed a real leave/re-entry
boundary; it does not claim the harness position was authentic. Ordering-only
nearest-list changes are suppressed by set comparison, and the refresh anchor
still advances after each >=1000-unit scan exactly as in V95.

Loopback only: 127.0.0.1. No historical service is contacted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import math
import pathlib
import socket
import struct
import threading
import time
from dataclasses import dataclass, field

HOST = "127.0.0.1"
LOGIN_PORT = 10188
MAGIC = 0x5F253EAC

LSCN_PROTOCOL = 0x249F
LOGIN_REQ = 0x42BF
LOGIN_RES = 0x42E3
SELECT_SERVER_REQ = 0x536E
SELECT_SERVER_RES = 0x5396

GSCN_LOGIN_PROTOCOL = 0x453A
GSCN_RUNTIME_PROTOCOL_REQ = 0x6E6F
GSCN_RUNTIME_PROTOCOL_RES = 0x6E9D
LOGIN_VERIFY_VITAL = 0x3784
SELECT_ACTOR_VITAL = 0x36EF
NOTIFY_ENTER_CREATE_ACTOR = 0x6539
CREATE_ACTOR_VITAL = 0x36CF
START_GAME_REQ = 0x1E87
START_GAME_RES = 0x1E9F
START_GAME_FAIL_VITAL = 0x4323
GET_WORLD_INFO_VITAL = 0x3D4B
TELEPORT_VITAL = 0x25A2
TELEPORT_CHECK_VITAL = 0x4477
TARGET_POS_VITAL = 0x2A90
TARGET_VITAL = 0x1ADD
ACTION_VITAL = 0x1AEA
ACTION_IDLE_NEUTRAL = 0xEA60
ON_LAND_VITAL = 0x1EB4
UPDATE_SERVER_SETTING_VITAL = 0x0F01
CHOOSE_NPC = 0x0FB6
CHOOSE_NPC_BY_TABLE_ID = 0x3BFB
NPC_CONVERSATION = 0x31D8
OPEN_CLOSE_UI = 0x1890
ACTION_PICK_VITAL = 0x300B
ACTOR_INSPECT_VITAL = 0x3E60
CARRYABLE_SERVICE_VITAL = 0x5D4B
STORAGE_OPEN_VITAL = 0x369A
TRADE_ZOOM_VITAL = 0x2A7A
TRADE_CMD_VITAL = 0x23B5
TRADE_ITEM_RESULT_VITAL = 0x557B
UPDATE_ATTR_VITAL = 0x309A
QUEST_OPERATE_VITAL = 0x3E34
UPDATE_NPC_APPEAR_VITAL = 0x515F
NPC_ATTR = 0x0AD5
ACTOR_ATTR = 0x12AD
MOVEMENT_ATTR = 0x2067
BACKPACK_ATTR = 0x1F81
ITEM_ATTR = 0x0ECD
TRIGGER_VITAL = 0x1FB2
SHOW_MESSAGE_VITAL = 0x36D2
MUSIC_CONTROL_VITAL = 0x3EAF
CHECK_SECOND_PWD_VITAL = 0x4B98
ITEM_OPERATE_VITAL = 0x36FE
USE_ITEM_VITAL = 0x1F4F
ITEM_OPERATE_REQ_VITAL = 0x4BED
ITEM_OPERATE_RES_VITAL = 0x4C13

NAMES = {
    LOGIN_REQ: "LSCN_LoginVitalReq",
    LOGIN_RES: "LSCN_LoginVitalRes",
    SELECT_SERVER_REQ: "LSCN_SelectServerReq",
    SELECT_SERVER_RES: "LSCN_SelectServerRes",
    GSCN_LOGIN_PROTOCOL: "GSCN_LoginProtocol",
    GSCN_RUNTIME_PROTOCOL_REQ: "GSCN_RunTimeProtocolReq",
    GSCN_RUNTIME_PROTOCOL_RES: "GSCN_RunTimeProtocolRes",
    LOGIN_VERIFY_VITAL: "LoginVerifyVital",
    SELECT_ACTOR_VITAL: "SelectActorVital",
    NOTIFY_ENTER_CREATE_ACTOR: "NotifyEnterCreateActor",
    CREATE_ACTOR_VITAL: "CreateActorVital",
    START_GAME_REQ: "StartGameReq",
    START_GAME_RES: "StartGameRes",
    START_GAME_FAIL_VITAL: "StartGameFailVital",
    GET_WORLD_INFO_VITAL: "GetWorldInfoVital",
    TELEPORT_VITAL: "TeleportVital",
    TELEPORT_CHECK_VITAL: "TeleportCheckVital",
    TARGET_POS_VITAL: "TargetPosVital",
    TARGET_VITAL: "TargetVital",
    ACTION_VITAL: "ActionVital",
    ON_LAND_VITAL: "COnLandVital",
    UPDATE_SERVER_SETTING_VITAL: "UserSetting_UpdateServerSettingVital",
    CHOOSE_NPC: "ChooseNPC",
    CHOOSE_NPC_BY_TABLE_ID: "ChooseNPCByTableID",
    NPC_CONVERSATION: "NPCConversation",
    OPEN_CLOSE_UI: "OpenCloseUI",
    ACTION_PICK_VITAL: "ActionPickVital",
    ACTOR_INSPECT_VITAL: "ActorInspectVital",
    CARRYABLE_SERVICE_VITAL: "CarryableServiceVital",
    STORAGE_OPEN_VITAL: "StorageOpenVital",
    TRADE_ZOOM_VITAL: "TradeZoomVital",
    TRADE_CMD_VITAL: "TradeCmdVital",
    TRADE_ITEM_RESULT_VITAL: "TradeItemResultVital",
    UPDATE_ATTR_VITAL: "UpdateAttrVital",
    QUEST_OPERATE_VITAL: "QuestOperateVital",
    UPDATE_NPC_APPEAR_VITAL: "UpdateNPCAppearVital",
    NPC_ATTR: "NPCAttr",
    ACTOR_ATTR: "ActorAttr",
    MOVEMENT_ATTR: "MovementAttr",
    BACKPACK_ATTR: "BackpackAttr",
    ITEM_ATTR: "ItemAttr",
    TRIGGER_VITAL: "TriggerVital",
    SHOW_MESSAGE_VITAL: "ShowMessageVital",
    MUSIC_CONTROL_VITAL: "MusicControlVital",
    CHECK_SECOND_PWD_VITAL: "CheckSecondPwdVital",
    ITEM_OPERATE_VITAL: "ItemOperateVital",
    USE_ITEM_VITAL: "UseItemVital",
    ITEM_OPERATE_REQ_VITAL: "ItemOperateVitalReq",
    ITEM_OPERATE_RES_VITAL: "ItemOperateVitalRes",
}


def hexdump(data: bytes, width: int = 16) -> str:
    out = []
    for off in range(0, len(data), width):
        c = data[off:off + width]
        hx = " ".join(f"{b:02X}" for b in c)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in c)
        out.append(f"{off:08X}  {hx:<{width * 3 - 1}}  |{asc}|")
    return "\n".join(out)


def read_varint(buf: bytes, pos: int = 0):
    v = 0
    s = 0
    while True:
        if pos >= len(buf):
            raise ValueError("truncated varint")
        b = buf[pos]
        pos += 1
        v |= (b & 0x7F) << s
        if not (b & 0x80):
            return v, pos
        s += 7
        if s > 35:
            raise ValueError("varint too long")


def write_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def snappy_raw_decompress(src: bytes) -> bytes:
    expected, pos = read_varint(src)
    out = bytearray()
    while pos < len(src) and len(out) < expected:
        tag = src[pos]
        pos += 1
        kind = tag & 3
        if kind == 0:
            code = tag >> 2
            if code < 60:
                ln = code + 1
            else:
                n = code - 59
                ln = int.from_bytes(src[pos:pos + n], "little") + 1
                pos += n
            out += src[pos:pos + ln]
            pos += ln
        elif kind == 1:
            ln = 4 + ((tag >> 2) & 7)
            off = ((tag & 0xE0) << 3) | src[pos]
            pos += 1
            for _ in range(ln):
                out.append(out[-off])
        elif kind == 2:
            ln = 1 + (tag >> 2)
            off = int.from_bytes(src[pos:pos + 2], "little")
            pos += 2
            for _ in range(ln):
                out.append(out[-off])
        else:
            ln = 1 + (tag >> 2)
            off = int.from_bytes(src[pos:pos + 4], "little")
            pos += 4
            for _ in range(ln):
                out.append(out[-off])
    if len(out) != expected:
        raise ValueError(f"Snappy size mismatch {len(out)} != {expected}")
    return bytes(out)


def snappy_raw_literal(data: bytes) -> bytes:
    out = bytearray(write_varint(len(data)))
    p = 0
    while p < len(data):
        chunk = data[p:p + 65536]
        n = len(chunk)
        nm1 = n - 1
        if n <= 60:
            out.append(nm1 << 2)
        else:
            nb = max(1, (nm1.bit_length() + 7) // 8)
            out.append((59 + nb) << 2)
            out += nm1.to_bytes(nb, "little")
        out += chunk
        p += n
    return bytes(out)


def u8tag(tag: int, v: int) -> bytes:
    return bytes([tag, v & 0xFF])


def u16tag(tag: int, v: int) -> bytes:
    return bytes([tag]) + struct.pack("<H", v & 0xFFFF)


def u32tag(tag: int, v: int) -> bytes:
    return bytes([tag]) + struct.pack("<I", v & 0xFFFFFFFF)


def wstr_tag(s: str) -> bytes:
    b = s.encode("utf-16le")
    return b"\x48" + struct.pack("<I", len(b)) + b


def astr_tag(s: str) -> bytes:
    b = s.encode("ascii")
    return b"\x44" + struct.pack("<I", len(b)) + b


def frame_pc(pc: bytes) -> bytes:
    comp = snappy_raw_literal(pc)
    return struct.pack("<II", MAGIC, len(comp)) + comp


def make_lscn_outer(msg_id: int, payload: bytes, vital_version: int) -> tuple[bytes, bytes]:
    pc = bytearray()
    pc += u16tag(0x12, LSCN_PROTOCOL)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 0)
    pc += u8tag(0x0B, 2)
    pc += u16tag(0x12, 1)
    pc += u16tag(0x12, msg_id)
    pc += u8tag(0x0B, vital_version)
    pc += payload
    pc = bytes(pc)
    return pc, frame_pc(pc)


def child_record(cid: int, status: int, name: str, unknown: int = 100, online: int = 1) -> bytes:
    return u32tag(0x14, cid) + u8tag(0x08, status) + wstr_tag(name) + u32tag(0x14, unknown) + u16tag(0x0F, online)


def world_record(wid: int, name: str, children: list[bytes]) -> bytes:
    return u32tag(0x14, wid) + wstr_tag(name) + u16tag(0x0F, len(children)) + b"".join(children)


def make_login_res() -> tuple[bytes, bytes]:
    payload = u8tag(0x08, 1) + u8tag(0x08, 1)
    worlds = [world_record(1, "Pirate Force Local", [child_record(1, 1, "Channel 1")])]
    payload += u16tag(0x0F, len(worlds)) + b"".join(worlds)
    return make_lscn_outer(LOGIN_RES, payload, 1)


def make_select_res(status: int, game_port: int, value32: int, host: str, token: str) -> tuple[bytes, bytes]:
    # Static serializer recovered from GameClient 1.41.01132.
    payload = (
        u8tag(0x08, status)
        + u16tag(0x12, game_port)
        + u32tag(0x14, value32)
        + astr_tag(host)
        + astr_tag(token)
    )
    return make_lscn_outer(SELECT_SERVER_RES, payload, 0)


def make_game_login_ack(token: str) -> tuple[bytes, bytes]:
    # Exact shape observed in the client's LoginVerifyVital request.
    verify_payload = b"\x0B\x68\x48\x04\x00\x00\x00\x0E\x00\x00\x00" + astr_tag(token)
    pc = bytearray()
    pc += u16tag(0x12, GSCN_LOGIN_PROTOCOL)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 0)
    pc += u8tag(0x0B, 2)
    pc += u16tag(0x12, 1)
    pc += u16tag(0x12, LOGIN_VERIFY_VITAL)
    pc += u8tag(0x0B, 0)
    pc += verify_payload
    pc = bytes(pc)
    return pc, frame_pc(pc)


def make_select_actor_empty_payload() -> bytes:
    """Runtime-proven v25 SelectActorVital v10 empty payload.

    Serializer 0x5EBAE0 writes exactly:
      0B u8(+38)
      14 u32(+14)
      14 u32(+3C)
      1F u32(+40)
      0B u8(+39)
      0B u8(actor_count)
    v25 accidentally emitted two extra trailing 0B 00 fields. The client
    tolerated them, but v30 uses the exact serializer shape.
    """
    # Runtime v26 proved that the 2-tail variant is rejected immediately
    # (GSCN_RunTimeProtocolRes ErrorData=28317) before the client emits Notify(0).
    # Restore the exact v25 wire shape that is runtime-proven to enter actor select.
    return (
        u8tag(0x0B, 0)
        + u32tag(0x14, 0)
        + u32tag(0x14, 0)
        + u32tag(0x1F, 0)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 0)
    )


def make_runtime_vitals(vitals: list[tuple[int, int, bytes]]) -> tuple[bytes, bytes]:
    """GSCN_RunTimeProtocolRes v4 carrying an arbitrary VitalData collection.

    Collection layout is the same binary-proven +0x1C serializer used by
    make_runtime_vital(); this helper only changes the count and repeats nested
    VitalData objects.
    """
    pc = bytearray()
    pc += u16tag(0x12, GSCN_RUNTIME_PROTOCOL_RES)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 4)
    pc += u8tag(0x0B, 2)
    pc += u16tag(0x12, len(vitals))
    for msg_id, vital_version, vital_payload in vitals:
        pc += u16tag(0x12, msg_id)
        pc += u8tag(0x0B, vital_version)
        pc += vital_payload
    # RuntimeRes v4 has a second (derived-class) change mask after the
    # inherited VitalData collection.  Empty RuntimeRes proved this exact
    # trailing 0B 00 on the wire; omitting it makes the client over-read the
    # collection response and raise ErrorData=28317.
    pc += u8tag(0x0B, 0)
    pc = bytes(pc)
    return pc, frame_pc(pc)


def make_update_npc_appear_payload(appear_id: int, visible: int = 1) -> bytes:
    """UpdateNPCAppearVital v0 payload, binary-proven serializer 0x738920.

    +0x14: tag 0x0F, u16 appearance-condition ID
    +0x16: tag 0x05, 1-byte state.  Client handler 0x738B60 passes these
           fields to NPCAppearModule_Client; the module path inserts the ID
           into its active set when state is non-zero and removes it when zero.
    """
    return u16tag(0x0F, appear_id & 0xFFFF) + u8tag(0x05, 1 if visible else 0)


def make_npc_appear_sweep_batches(start: int = 0, stop: int = 65536, batch: int = 256):
    """Build a complete u16 NPCAppear-condition activation sweep.

    V40.1 proved the UpdateNPCAppearVital wire/envelope is accepted by the
    client, but 0..255 produced no NPCs.  Binary analysis of the module shows
    the key is a full u16 and the update only changes the active condition set.
    Sweeping the complete key space is therefore a finite diagnostic for whether
    Port Royal already has locally-loaded .npc placements waiting on condition IDs.
    """
    result = []
    for lo in range(start, stop, batch):
        hi = min(stop, lo + batch)
        vitals = [
            (UPDATE_NPC_APPEAR_VITAL, 0, make_update_npc_appear_payload(i, 1))
            for i in range(lo, hi)
        ]
        pc, fr = make_runtime_vitals(vitals)
        result.append((lo, hi - 1, pc, fr))
    return result


def make_runtime_vital(msg_id: int, vital_version: int, vital_payload: bytes) -> tuple[bytes, bytes]:
    """GSCN_RunTimeProtocolRes v4, mask 0x02, one VitalData object.

    This exact envelope follows the binary serializer at 0x5E3EE0:
      outer 0x6E9D, protocol version 4
      mask 0x02 -> +0x1C VitalData collection present
      collection serializer -> tag 0x12, u16 count, then nested VitalData.
    """
    pc = bytearray()
    pc += u16tag(0x12, GSCN_RUNTIME_PROTOCOL_RES)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 4)
    pc += u8tag(0x0B, 2)
    pc += u16tag(0x12, 1)
    pc += u16tag(0x12, msg_id)
    pc += u8tag(0x0B, vital_version)
    pc += vital_payload
    pc = bytes(pc)
    return pc, frame_pc(pc)


def make_npc_conversation_empty(actor_identity: int) -> tuple[bytes, bytes]:
    """Binary-derived NPCConversation v0 with no conversation entries.

    GameClient.local.bin NPCConversation constructor 0x622A00 initializes the
    qword identity at +0x18/+0x1C and the collection at +0x20 as empty.
    Serializer 0x622F10 writes tag 0x32/qword identity, then tag 0x0F/u16
    collection count and repeats the nested serializer only when count > 0.
    V97 proved this constructor-valid empty collection invokes the client's
    authentic MOBS_TIP default-talk path without inventing quest/service data.
    """
    payload = qwordtag(0x32, actor_identity) + u16tag(0x0F, 0)
    return make_runtime_vitals([(NPC_CONVERSATION, 0, payload)])


def make_npc_conversation_quest3020(
    actor_identity: int = 0x2001,
) -> tuple[bytes, bytes]:
    """One serializer-exact q3020 descriptor for authentic placement P0.

    NPCConversation serializer 0x622F10 writes the actor qword, u16 entry
    count, then calls direct descriptor/base serializer 0x606890. That writes
    qid/+0x10 as tagged u16 and +0x12 as tagged u8. Factory 0x622130 initializes
    the latter byte to zero. Handler 0x61CD40 passes the list into 0x61CA50,
    which looks up q3020 and routes its decoded n_TYPE=20 row before consulting
    the descriptor byte. No unknown descriptor meaning is assigned here.
    """
    if actor_identity != V129_QUEST_ACTOR_ID:
        raise ValueError(
            f"V134 q3020 conversation actor must be P0: 0x{actor_identity:016X}"
        )
    payload = (
        qwordtag(0x32, actor_identity)
        + u16tag(0x0F, 1)
        + u16tag(0x12, V129_QUEST_ID)
        + u8tag(0x08, 0)
    )
    return make_runtime_vitals([(NPC_CONVERSATION, 0, payload)])


V112_STORE_ID = 5
V112_STORE_PRODUCT_TEMPLATE = 2200009  # STORE_NORMAL row 5: Sword Soul
V116_INITIAL_CASH = 10000  # STORE_NORMAL/EQUIPMENT_BASE decoded buy price
V122_FINAL_CASH = 0
V118_TRADE_CART_ADD_COMMAND = 6
V118_TRADE_CART_ADD_DWORD = 0
V118_TRADE_CART_ACK_RESULT = 13
V121_CAPTURED_FINAL_BUY_COMMAND = 8
V121_CAPTURED_FINAL_BUY_DWORD = 0
V121_CAPTURED_STORE_CLOSE_COMMAND = 12
V121_CAPTURED_STORE_CLOSE_DWORD = 0
V129_QUEST_ID = 3020  # QUEST row 3020, level 1, Q_TELEPORT_WITH_VEHICLE1.
V129_QUEST_OPEN_ACCEPT_UI_ACTION = 6
V129_QUEST_ACCEPT_SUCCESS_ACTION = 1
V129_QUEST_ACTOR_ID = 0x2001  # Exact data-backed P0/template-1 identity.
V126_ACTION_TARGET_ACTOR_ID = 0x201F  # Existing isolated P30 identity.
V126_ACTION_TARGET_KIND = 2
V128_WIELD_HOTKEY_ID = 71  # B_CONSTDATA_TH HOTKEY row 71.
V128_WIELD_KEY_CODE = 90  # HOTKEY n_KEY_2; B_TEXTDATA_TH KEY_TIP row 90 = Z.
V128_WIELD_HOTKEY_NAME = "WIELD"
V128_WIELD_THAI_LABEL = "เก็บอาวุธ"  # HOTKEY_TIP row 71.
V128_WIELD_ACTION_CODE = 0xEA7E  # Producer 0x44BC70 online branch.
V126_ACTION_VITAL_BODY_BYTES = 64
V131_TELEPORT_CHECK_VALUE = 1
V136_EMPTY_RUNTIME_REQ_PC = bytes.fromhex(
    '12 6F 6E 14 00 00 00 00 08 00 0B 00'
)
V136_MARKER1_CONFIRM_PC = bytes.fromhex(
    '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 '
    '12 77 44 0B 00 0F 01 00'
)
V137_MARKER_ID = 1
V137_MARKER_SCENE_ID = 1
V137_MARKER_SCENE_SEQ = 0
V137_MARKER_X = -10322.0
V137_MARKER_Y = -755.0
V137_MARKER_Z = 671.0
V138_MARKER1_READY_PC = bytes.fromhex(
    '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 03 00 '
    '12 DD 1A 0B 00 32 00 00 00 00 00 00 00 00 08 02 '
    '12 A2 25 0B 04 0B 02 0B 00 0B 00 0B 00 0F 00 00 '
    '12 90 2A 0B 00 2A 00 48 21 C6 2A 00 C0 3C C4 '
    '2A 00 C0 27 44 2A 00 00 00 00 0B 00 0B 00'
)
V138_MARKER1_NEAREST_INDICES=(
    86,80,0,1,65,22,16,85,5,92,84,50,89,144,145,39,87,82,30,70,
)
V139_P86_INDEX=86
V139_P86_ACTOR_ID=0x2000+V139_P86_INDEX+1
V139_MARKER1_TARGETPOS_PC=bytes.fromhex(
    '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 '
    '12 90 2A 0B 00 2A 00 48 21 C6 2A 00 C0 3C C4 '
    '2A 00 C0 27 44 2A 00 00 00 00 0B 01 0B 00'
)
V140_P86_HARNESS_X=V137_MARKER_X+100.0
V140_P86_HARNESS_Y=V137_MARKER_Y+50.0
V140_P86_HARNESS_Z=V137_MARKER_Z


def make_trade_zoom_store5() -> tuple[bytes, bytes]:
    """Open client-data-backed normal store 5 through TradeZoomVital v2.

    Constructor 0x664CA0, serializer 0x6652E0, and handler
    0x665530 -> 0x662F70 prove this exact field order. Command 2 and subtype 2
    enter the normal-store path; the client reads store ID 5 from +0x20 and
    loads its one product (Sword Soul, global template 2200009) from local
    STORE_NORMAL data. The qword, ANSI string, and list remain constructor
    defaults. This is a test-harness open packet, not an NPC ownership claim.
    """
    payload = (
        u8tag(0x08, 2)
        + u8tag(0x08, 2)
        + qwordtag(0x32, 0)
        + u32tag(0x14, V112_STORE_ID)
        + wstr_tag("")
        + u16tag(0x0F, 0)
    )
    return make_runtime_vitals([(TRADE_ZOOM_VITAL, 2, payload)])


def make_teleport_check_scene1_challenge() -> tuple[bytes, bytes]:
    """Exact singleton RuntimeRes v4 TeleportCheckVital v0/value 1.

    TeleportCheckVital reset 0x44B980 and serializer 0x5E6670 prove the nested
    v0/u16 shape. RuntimeRes v4 requires its trailing derived 0B 00 mask, so
    this helper intentionally uses ``make_runtime_vitals``. Value 1 is the
    bounded scene-1 challenge value; no transport meaning is assigned.
    """
    return make_runtime_vitals([(
        TELEPORT_CHECK_VITAL,
        0,
        u16tag(0x0F, V131_TELEPORT_CHECK_VALUE),
    )])


def make_v137_marker1_transport_probe() -> tuple[bytes, bytes]:
    """Exact RuntimeRes TeleportVital for decoded MARKER row 1.

    TeleportVital v4 serializer order is already proven by the stable bootstrap
    helper. V137 changes only the carrier from LoginProtocol to RuntimeRes and
    the target XYZ to MARKER1's decoded values. Target bytes and final u16 stay
    at constructor-default zero; MARKER direction 3 is not assigned to them.
    """
    payload=(
        u8tag(0x0B,2)
        + u8tag(0x0B,1)
        + make_teleport_target(
            V137_MARKER_SCENE_ID,V137_MARKER_SCENE_SEQ,
            V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,
        )
        + u8tag(0x0B,0)
        + u8tag(0x0B,0)
        + u16tag(0x0F,0)
    )
    return make_runtime_vitals([(TELEPORT_VITAL,4,payload)])


def make_quest3020_action6_accept_ui(
    actor_identity: int = V129_QUEST_ACTOR_ID,
) -> tuple[bytes, bytes]:
    """Open the client-local quest-3020 accept UI with exact P0 context.

    QuestOperateVital constructor 0x621810 and serializer 0x621860 prove the
    exact v3 wire body order: u16/+0x14, u8/+0x16, u8/+0x17, u32/+0x18,
    qword/+0x20, and u8/+0x28 with tags 12/08/08/14/32/05. Consumer
    0x61A950 dispatches +0x17 values 1..8. Jump-table entry 6 reaches
    0x61AD41, resolves s_ROLE_TALK through 0x6164C0, opens the PC-conversation
    UI, and passes literal ``OpenAcceptUI_Run`` to 0x619210. UI handler
    0x61D030 checks action 6 and, for its accept row, pushes value32=0, the
    chosen quest ID, and operation=2 into 0x617800. That producer writes quest
    ID/+0x14, operation/+0x16, and value32/+0x18. Runtime V124 independently
    proved action 1 is an acceptance result and must not be reused as an offer.
    MOBS row 1 links P0/template 1 to quest 3020. QUEST row 3020 is level 1,
    uses Q_TELEPORT_WITH_VEHICLE1, and has Var2=1. Only that data-backed quest,
    audited action, and exact P0 actor context differ from constructor defaults.
    """
    if actor_identity != V129_QUEST_ACTOR_ID:
        raise ValueError(f"V129 accept-UI actor must be P0: 0x{actor_identity:016X}")
    payload = (
        u16tag(0x12, V129_QUEST_ID)
        + u8tag(0x08, 0)
        + u8tag(0x08, V129_QUEST_OPEN_ACCEPT_UI_ACTION)
        + u32tag(0x14, 0)
        + qwordtag(0x32, actor_identity)
        + u8tag(0x05, 0)
    )
    return make_runtime_vitals([(QUEST_OPERATE_VITAL, 3, payload)])


def make_quest3020_action1_accept_success(
    actor_identity: int = V129_QUEST_ACTOR_ID,
) -> tuple[bytes, bytes]:
    """Acknowledge one exact quest-3020 operation-2 request.

    The body is the same serializer-exact action-1 tuple accepted live in
    V124. Static cross-audit now supplies the missing request/response link:
    0x61D0DA sends operation 2 and 0x61D0E2 sets manager pending byte +0x88;
    action 1 clears it at 0x61AB4B, invokes ``Accept_Run`` at 0x61AB5D, then
    calls 0x6193E0(qid, 1) at 0x61AB6D to insert/refresh the tracker. The
    request constructor leaves its qword zero, so the response restores the
    exact P0 context retained from the action-6 offer. This establishes only
    the client-local Accept_Run boundary; no persistent server quest state is
    fabricated.
    """
    if actor_identity != V129_QUEST_ACTOR_ID:
        raise ValueError(
            f"V129 accept-success actor must be P0: 0x{actor_identity:016X}"
        )
    payload = (
        u16tag(0x12, V129_QUEST_ID)
        + u8tag(0x08, 0)
        + u8tag(0x08, V129_QUEST_ACCEPT_SUCCESS_ACTION)
        + u32tag(0x14, 0)
        + qwordtag(0x32, actor_identity)
        + u8tag(0x05, 0)
    )
    return make_runtime_vitals([(QUEST_OPERATE_VITAL, 3, payload)])


def make_trade_item_result_store_buy_cart_ack(
    item_identity: int,
    item_template: int,
    item_quantity: int,
) -> tuple[bytes, bytes]:
    """Acknowledge one exact normal-store product added to the buy cart.

    TradeItemResultVital constructor 0x6646E0 leaves nested version, result,
    subcode, dword, and detail pointer at zero. Serializer 0x664BA0 writes
    result/tag08, subcode/tag08, dword/tag19, detail-presence/tag08, then the
    fixed ItemAttr serializer when present. Handler branch 0x663C88 maps
    result 13 to the literal client event ``Trade_Shop/Store_ByItemOK``.

    The three non-default ItemAttr fields come directly from the captured
    TradeCmd detail. ItemAttr constructor 0x46B410 proves slot=-1, +0x38=0,
    +0x39=0xFF, and no nested detail. This standalone ItemAttr is a Store UI
    event argument; it does not mutate Backpack/ItemBag or player cash.
    """
    if not 0 <= item_identity <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"item identity out of range: {item_identity}")
    if item_template != V112_STORE_PRODUCT_TEMPLATE:
        raise ValueError(f"unsupported store item template: {item_template}")
    if item_quantity != 1:
        raise ValueError(f"unsupported store item quantity: {item_quantity}")

    item_attr = (
        qwordtag(0x32, item_identity)
        + u32tag(0x14, item_template)
        + u16tag(0x0F, item_quantity)
        + u16tag(0x0F, 0xFFFF)  # ItemAttr constructor-default signed slot -1
        + u8tag(0x08, 0)        # ItemAttr +0x38 constructor default
        + u8tag(0x08, 0xFF)     # ItemAttr +0x39 constructor default
        + u8tag(0x0B, 0)        # no optional nested ItemAttr detail
    )
    payload = (
        u8tag(0x08, V118_TRADE_CART_ACK_RESULT)
        + u8tag(0x08, 0)        # constructor-default subcode; unused by result 13
        + u32tag(0x19, 0)       # constructor-default dword; unused by result 13
        + u8tag(0x08, 1)
        + item_attr
    )
    return make_runtime_vitals([(TRADE_ITEM_RESULT_VITAL, 0, payload)])


def make_show_message(text: str) -> tuple[bytes, bytes]:
    """Binary-derived ShowMessageVital v0 carrying one wide string.

    Constructor 0x5E4930 installs vtable 0xF300EC and constructs its sole
    field at +0x14. Serializer 0x5E6D00 reads/writes exactly that wide string;
    client handler 0x5EFA70 forwards non-empty text to the notification UI.
    """
    if not text:
        raise ValueError("ShowMessageVital text must be non-empty")
    # RuntimeRes v4 always ends with its derived-class change mask.  Reuse the
    # collection helper so the packet receives the proven trailing 0B 00; the
    # older one-vital helper predates that discovery and is retained only for
    # legacy login/bootstrap builders.
    return make_runtime_vitals([(SHOW_MESSAGE_VITAL, 0, wstr_tag(text))])


def make_music_control_current_scene() -> tuple[bytes, bytes]:
    """Binary-derived constructor-default MusicControlVital v0.

    Constructor 0x5E4800 installs vtable 0xF300A4, constructs the ANSI string
    at +0x14 as empty, and sets +0x30 to 1. Serializer 0x5E60D0 writes exactly
    that string followed by tag 0x08/u8 mode. Handler 0x5F06D0 proves mode 1
    plus an empty string selects the current scene's locally configured music.
    """
    payload = astr_tag("") + u8tag(0x08, 1)
    return make_runtime_vitals([(MUSIC_CONTROL_VITAL, 0, payload)])


def make_check_second_password_success() -> tuple[bytes, bytes]:
    """Binary-derived CheckSecondPwdVital v0 result=OK response.

    Constructor 0x4E5150 initializes result +0x14 and u32 +0x18 to zero and
    constructs the ANSI string at +0x1C empty. Serializer 0x5E6060 writes
    tag08/u8, tag19/u32, then the ANSI string. Handler 0x5F05B0 maps result 1
    to the literal UI state "OK" and result 2 to "Fail". Preserve all
    constructor defaults and change only the proven result byte.
    """
    payload = u8tag(0x08, 1) + u32tag(0x19, 0) + astr_tag("")
    return make_runtime_vitals([(CHECK_SECOND_PWD_VITAL, 0, payload)])


def _heading_to_player(npc_x: float, npc_y: float,
                       player_x: float, player_y: float) -> float:
    """Established client convention: +X=0, -Y=pi/2, -X=pi, +Y=3pi/2."""
    heading = math.atan2(-(player_y - npc_y), player_x - npc_x)
    return heading % (2.0 * math.pi)


def make_v98_conversation_face_state(population_indices: tuple[int, ...],
                                     selected_identity: int,
                                     player_x: float, player_y: float):
    """Retain the population and rotate one actor without a default position.

    V95 proved that mask 0x02 (heading only) makes the client apply an
    uninitialized/default position and teleport the NPC. V98 uses the already
    proven MovementAttr fields only: mask 0x03, authentic placement XYZ, and a
    heading derived from the player's latest TargetPosVital position.
    """
    by_idx = {row[0]: row for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    selected_idx = selected_identity - 0x2000 - 1
    if selected_idx not in population_indices:
        raise ValueError("selected identity is not in current population")
    entries = []
    for idx in population_indices:
        _, template_id, px, py, pz, preset, _ = by_idx[idx]
        aid = 0x2000 + idx + 1
        attrs = [(NPC_ATTR, make_npc_attr(template_id, aid, 1, 0, preset))]
        if idx == selected_idx:
            heading = _heading_to_player(px, py, player_x, player_y)
            attrs.append((
                MOVEMENT_ATTR,
                make_remote_movement_attr(
                    aid, px, py, pz, heading, mask=0x03
                ),
            ))
        entries.append(make_remote_actor_entry(4, aid, attrs))
    return make_runtime_remote_actors(entries), selected_idx


def make_login_vital(msg_id: int, vital_version: int, vital_payload: bytes) -> tuple[bytes, bytes]:
    """GSCN_LoginProtocol v0, mask 0x02, one VitalData object.

    Runtime evidence: all client CreateActorVital submits use this envelope, and
    LoginVerifyVital responses under the same GSCN_LoginProtocol envelope are
    already accepted by this client build. v30 keeps the CreateActor
    response envelope from RuntimeRes to LoginProtocol; the nested VitalData is
    byte-for-byte identical to v27.
    """
    pc = bytearray()
    pc += u16tag(0x12, GSCN_LOGIN_PROTOCOL)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 0)
    pc += u8tag(0x0B, 2)
    pc += u16tag(0x12, 1)
    pc += u16tag(0x12, msg_id)
    pc += u8tag(0x0B, vital_version)
    pc += vital_payload
    pc = bytes(pc)
    return pc, frame_pc(pc)


def qwordtag(tag: int, v: int) -> bytes:
    return bytes([tag]) + struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)


def f32tag(v: float) -> bytes:
    return bytes([0x2A]) + struct.pack("<f", float(v))


def make_npc_attr(template_id: int, actor_identity: int, scene_id: int = 1, scene_seq: int = 0,
                  visual_preset: str = "", current_hp: int = 100, max_hp: int = 100,
                  movement_speed: float = None, basic_name: str = "") -> bytes:
    """Binary-derived NPCAttr wire with the statically-proven visual preset field.

    NPCAttr serializer 0x466EB0 calls BasicAttr serializer 0x4656F0 and then
    writes its own one-byte mask at +0xBC.  Bit 0x01 serializes the MOBS/template
    u16 at +0x78.  Crucially, bit 0x04 serializes the std::wstring at +0x7C via
    PcBinary::wstring writer 0x89A810 (tag 0x48 + byte length + UTF-16LE).

    BasicAttr comparator 0x4654D0 assigns bit 0x0001 to the std::wstring at
    +0x28. BasicAttr serializer 0x4656F0 writes that string first through the
    same 0x89A810 UTF-16 writer, before current/max HP. Target-panel updater
    0x51F920 copies BasicAttr+0x28 into the local LABEL_NAME widget.

    Static chain proving +0x7C semantics:
      type-4 NPC vtable +0x60 -> 0x45DAE0
      0x45DAE0 copies NPCAttr+0x7C to appearance-descriptor+0x60
      descriptor vtable +0x14 -> 0x78AA50
      0x78AA50 formats `.\\Data\\GC\\V\\%s.avt` from descriptor+0x60
      and loads that avatar template.

    Therefore visual_preset is not guessed display text; it is the avatar-template
    basename consumed by the base NPC visual path.  For MOBS ID 1 the decoded
    client database gives s_OUTFIT=P_MALE_002_000_SP1.
    """
    # V64 static finding: BasicAttr bits 0x0004 and 0x0008 serialize the u32
    # pair at +0x44/+0x48.  0x43D730 compares those two fields for equality,
    # while 0x43BD70 only enters the dead path when +0x44 == 0 and +0x58 <= 0.
    # 0x43BDA0 handles the complementary +0x44 == 0 / +0x58 > 0 transitional
    # state.  Combined with the already runtime-proven ActorAttr 100/100 pair,
    # this resolves +0x44/+0x48 as current/max HP and +0x58 as a zero-HP
    # death/down-state timer rather than an alive flag.  V62 therefore sends
    # full HP and omits bit 0x0080 entirely.
    # V73: BasicAttr bit 0x0040 serializes float +0x54 (0x46579A).
    # Setter 0x464960 writes +0x54. CNetNPC template init 0x45C103 reads
    # MOBS+0x3C (decoded n_SPEED_WALK) and feeds it to that setter.
    # Initial visual apply 0x45D2EA passes +0x54 to movement control 0x484580.
    basic_mask = 0x0004 | 0x0008 | 0x0100 | 0x0200
    if basic_name:
        basic_mask |= 0x0001
    if movement_speed is not None:
        basic_mask |= 0x0040
    npc_mask = 0x01 | (0x04 if visual_preset else 0)
    out = (
        u8tag(0x0B, 1)
        + qwordtag(0x32, actor_identity)
        + u16tag(0x12, basic_mask)
    )
    if basic_name:
        out += wstr_tag(basic_name)
    out += u32tag(0x14, current_hp) + u32tag(0x14, max_hp)
    if movement_speed is not None:
        out += f32tag(movement_speed)
    out += (
        u16tag(0x12, scene_id)
        + qwordtag(0x32, scene_seq)
        + u8tag(0x0B, npc_mask)
        + u16tag(0x12, template_id)
    )
    if visual_preset:
        out += wstr_tag(visual_preset)
    return out


def make_remote_movement_attr(actor_identity: int, x: float = 0.0, y: float = 0.0,
                              z: float = 0.0, heading: float = 0.0,
                              mask: int = 0xFF,
                              mode_u8: int = 0, flags_u32: int = 0,
                              p40: float = 0.0, p44: float = 0.0, p48: float = 0.0) -> bytes:
    """Binary-derived MovementAttr serializer with an explicit field mask.

    Static RE at 0x4671C0 proves the MovementAttr derived mask is per-field:
      0x01 -> position vec3 (+0x28..+0x30)
      0x02 -> heading float (+0x34)
      0x04 -> u8 (+0x38)
      0x08 -> u32 (+0x3C)
      0x10 -> float (+0x40)
      0x20 -> float (+0x44)
      0x40 -> float (+0x48)

    V62 used mask 0xFF even for the live position update.  V64 keeps 0xFF for
    initial/full snapshots, but the one runtime movement probe uses ONLY bit
    0x01 so the client can merge a position delta without overwriting the
    existing locomotion/control fields with our synthetic zero defaults.
    """
    if mask & ~0xFF:
        raise ValueError("MovementAttr mask must fit u8")
    out = bytearray()
    out += u8tag(0x0B, 1)
    out += qwordtag(0x32, actor_identity)
    out += u8tag(0x0B, mask)
    if mask & 0x01:
        out += f32tag(x) + f32tag(y) + f32tag(z)
    if mask & 0x02:
        out += f32tag(heading)
    if mask & 0x04:
        out += u8tag(0x0B, mode_u8)
    if mask & 0x08:
        out += u32tag(0x26, flags_u32)
    if mask & 0x10:
        out += f32tag(p40)
    if mask & 0x20:
        out += f32tag(p44)
    if mask & 0x40:
        out += f32tag(p48)
    return bytes(out)


def make_remote_actor_entry(actor_type: int, actor_identity: int,
                            attrs: list[tuple[int, bytes]]) -> bytes:
    """Exact actor-entry serializer at 0x5E21D0.

    Wire: tag0B u8 actor type, tag32 qword identity, tag0B u8 attr count,
    then for each attr tag12 u16 Attr ID followed by that Attr's serializer.
    """
    if not (0 <= len(attrs) <= 255):
        raise ValueError("remote actor attr count must fit u8")
    out = bytearray()
    out += u8tag(0x0B, actor_type)
    out += qwordtag(0x32, actor_identity)
    out += u8tag(0x0B, len(attrs))
    for attr_id, attr_wire in attrs:
        out += u16tag(0x12, attr_id)
        out += attr_wire
    return bytes(out)


def make_runtime_remote_actors(entries: list[bytes]) -> tuple[bytes, bytes]:
    """GSCN_RunTimeProtocolRes v4 derived bit 0x02 remote-actor collection.

    Serializer chain proven in GameClient.local.bin:
      0x5F4070 inherited Runtime base -> mask 0 (no VitalData list)
      0x5E3EE0 RuntimeRes derived mask bit 0x02 -> object+0x1C
      0x5E1C10/0x5E01D0 -> tag12 u16 actor count + actor entries
      0x5E21D0 -> actor entry serializer.
    """
    if not (0 <= len(entries) <= 0xFFFF):
        raise ValueError("remote actor count must fit u16")
    pc = bytearray()
    pc += u16tag(0x12, GSCN_RUNTIME_PROTOCOL_RES)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 4)
    pc += u8tag(0x0B, 0)      # inherited VitalData collection absent
    pc += u8tag(0x0B, 0x02)   # RuntimeRes derived +0x1C actor-stream collection
    pc += u16tag(0x12, len(entries))
    for e in entries:
        pc += e
    pc = bytes(pc)
    return pc, frame_pc(pc)


def make_port_royal_npc_single_packets() -> list[tuple[int, int, bytes, bytes]]:
    """Build six one-actor RuntimeRes packets instead of one six-actor packet.

    V43 proved the combined actor stream triggers ErrorData=28317.  V42 proved a
    single actor entry in the same derived RuntimeRes field is parse-safe.  Keep
    each CNetNPC isolated in its own packet so every packet has the exact V42
    shape, but use the corrected Port Royal ground Z=931 and six nearby MOBS
    templates to maximize the chance that at least one resolves to a visible NPC.
    """
    specs = [
        (0x1001, 1,   0.0,   90.0),
        (0x1002, 2,  90.0,    0.0),
        (0x1003, 3,   0.0,  -90.0),
        (0x1004, 4, -90.0,    0.0),
        (0x1005, 5,  65.0,   65.0),
        (0x1006, 6, -65.0,   65.0),
    ]
    packets = []
    for actor_identity, template_id, x, y in specs:
        attrs = [
            (NPC_ATTR, make_npc_attr(template_id, actor_identity, 1, 0)),
            (MOVEMENT_ATTR, make_remote_movement_attr(
                actor_identity, x, y, 931.0, 0.0
            )),
        ]
        entry = make_remote_actor_entry(4, actor_identity, attrs)
        pc, fr = make_runtime_remote_actors([entry])
        packets.append((template_id, actor_identity, pc, fr))
    return packets



PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = [
    (0, 1, -9139.95703125, -2780.045166015625, 223.29209899902344, 'P_MALE_002_000_SP1', 'Navy Transfer'),
    (1, 2, -8013.458984375, -2780.045166015625, 223.29209899902344, 'M010_001_000_N', 'Sebastian'),
    (3, 4, 7538.6123046875, 6490.41845703125, 1985.6571044921875, 'M015_000_000_SP1', 'Mo Yuzi'),
    (4, 5, 10768.0673828125, 6792.431640625, 2200.44384765625, 'P_MALE_002_000_PAK', 'Pike'),
    (5, 6, -507.0028991699219, -616.3690795898438, 931.38623046875, 'M001_000_000_SP3', 'Legend Jack'),
    (6, 7, 3444.468017578125, -11757.7080078125, 983.5479736328125, 'M001_000_000_SP1', 'Legend Jack Men'),
    (7, 8, 12568.798828125, -3265.21630859375, 2266.031494140625, 'P_MALE_015_000_EDMON', 'Edmund'),
    (8, 9, 12568.798828125, -4831.4208984375, 2266.031494140625, 'M001_000_001_SP3', 'Baboza'),
    (9, 10, 11774.1796875, 8262.0517578125, 2200.4384765625, 'M001_000_001_SP1', 'Baboza Men'),
    (10, 11, 12421.771484375, 1962.24951171875, 2239.4462890625, 'P_MALE_015_000_X', 'X'),
    (11, 12, 18192.248046875, 16129.2626953125, 1152.5146484375, 'P_MALE_015_000_PAUL', 'Paul'),
    (12, 35, 17961.1796875, 25208.271484375, 452.3008117675781, 'M025_001_000_BOSS', 'Fighting Fish Sergeant'),
    (13, 14, 15391.181640625, 4611.3623046875, 2242.01513671875, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (14, 15, 14824.16015625, 6386.69970703125, 2251.57275390625, 'M074_000_001_N', 'Ferryman'),
    (15, 16, 14824.3232421875, 2845.75341796875, 2251.576171875, 'P_MALE_015_000_SLAVE', 'Silly Pirate Prisoner'),
    (16, 17, -4703.5263671875, -733.2506713867188, 699.3204956054688, 'P_MALE_015_000_SLAVE', 'Panic Pirate Prisoner'),
    (17, 18, 5600.25732421875, 11648.5673828125, 979.6317749023438, 'M001_003_000_N', 'Thin'),
    (18, 19, 9362.7060546875, -2827.5849609375, 2018.175048828125, 'P_MALE_015_000_MATT', 'Matt'),
    (19, 20, 11361.4921875, 5364.10205078125, 2231.169189453125, 'P_MALE_009_000_JEFFERY', 'Jefferson'),
    (20, 21, 16125.9091796875, -10905.7861328125, 2758.929931640625, 'P_MALE_015_000_X', 'X'),
    (21, 22, 21643.029296875, -12783.984375, 2747.52197265625, 'P_MALE_003_000_CLOUS', 'Kraus'),
    (22, 23, -6232.0, -1005.0001220703125, 724.6790771484375, 'P_MALE_015_000_SEVEN', 'Seven'),
    (23, 24, 14560.2509765625, 18320.109375, 718.7119140625, 'M001_001_000_SP3', 'Kuck'),
    (24, 26, 23571.3828125, 6723.6044921875, 2379.88134765625, 'P_MALE_015_000_SLAVE', 'Attempt to escape pirate Prisoner'),
    (27, 25, 9515.943359375, -14124.658203125, 995.7626953125, 'M009_000_000_N', 'Odyssey'),
    (30, 31, 1747.5244140625, -7837.69775390625, 931.0413208007812, 'M011_000_000_SP3', 'Tornado Eagle'),
    (33, 34, -216.15969848632812, 11168.337890625, 575.0142822265625, 'M025_001_000_N', 'Fighting Fish soldier'),
    (34, 13, 18953.4296875, 19083.3671875, 725.4708251953125, 'M009_000_000_N', 'Odyssey'),
    (35, 36, 12558.9072265625, -5593.716796875, 2210.97265625, 'M055_000_000_N', 'Columbus'),
    (37, 38, 20012.111328125, 15491.814453125, 1143.8961181640625, 'P_FEMALE_001_001_RENA', 'Reyna'),
    (38, 39, 20030.568359375, 17893.73046875, 1111.4010009765625, 'M015_000_000_SP2', 'Mo Yuzi'),
    (39, 40, 2022.517822265625, 82.60009765625, 930.32373046875, 'P_MALE_001_001_KARL', 'Carle'),
    (40, 41, 18188.087890625, 15878.7734375, 1034.9842529296875, 'P_MALE_010_000_MARTIN', 'Martin'),
    (41, 42, 21087.349609375, -650.0, 2746.367919921875, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (42, 43, 22330.390625, -650.0, 2746.367919921875, 'P_MALE_002_002_EION', 'Iain'),
    (43, 44, 19650.52734375, -6819.84228515625, 2797.673828125, 'M055_001_000_N', 'Magellan'),
    (44, 45, 20909.728515625, -12498.0458984375, 2747.08349609375, 'P_MALE_007_001_OLD_MAGELLAN', 'Magellan Old Man'),
    (45, 46, 22361.71484375, -12514.1455078125, 2747.3564453125, 'P_FEMALE_012_001_RULALA', 'Lulala'),
    (46, 47, 10270.14453125, 5851.11279296875, 2200.53857421875, 'P_MALE_001_002_JAMES', 'James'),
    (47, 48, 10280.369140625, 4554.76318359375, 2200.53857421875, 'P_MALE_009_001_N', 'Avaricious Spice Merchant'),
    (48, 49, 9218.4384765625, 13822.748046875, 981.9058837890625, 'M004_000_004_N', 'Alien exquisite'),
    (49, 50, 10548.947265625, 13881.953125, 983.651611328125, 'M015_000_000_SP1', 'Mo Yuzi'),
    (50, 52, 1133.16552734375, 696.114501953125, 971.0015258789062, 'M012_000_000_N', 'Plato'),
    (51, 53, 10304.927734375, 12387.5234375, 979.9110717773438, 'M012_000_000_N', 'Plato'),
    (52, 54, 12019.5498046875, -2838.721435546875, 2202.602783203125, 'P_FEMALE_018_000_LORA', 'Laura'),
    (58, 60, -5893.7265625, 15161.7578125, 314.1536865234375, 'M002_000_002_SP3', 'Jungle Big Tiger'),
    (59, 61, 10755.4521484375, 7250.541015625, 2200.4453125, 'M004_000_002_SP1', 'Toxic Vine'),
    (60, 62, 7663.41748046875, 1862.685546875, 2037.39404296875, 'M014_000_000_N', 'Ancient Civilization Alert Weapon'),
    (63, 65, 9647.2890625, -4765.767578125, 1985.731201171875, 'M003_001_000_SP3', 'Ward Apes'),
    (65, 67, -6961.044921875, -2562.861083984375, 207.54930114746094, 'M055_000_000_N', 'Columbus'),
    (66, 68, 21347.494140625, -5840.4609375, 2761.3046875, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (67, 69, 21694.0703125, -5071.00048828125, 2812.616943359375, 'M015_000_001_SP3', 'Mori Hiroko'),
    (68, 70, 5136.8564453125, -4594.1279296875, 4549.7294921875, 'M070_000_000_N', 'Wealthy slave buyer'),
    (69, 51, 21712.89453125, -6054.33154296875, 2772.748291015625, 'M070_000_001_N', 'Madisen'),
    (70, 71, 2195.447509765625, 5700.166015625, 983.5487060546875, 'M001_001_000_SP2', 'Lecherous slave buyer'),
    (71, 72, 20489.66796875, 14226.439453125, 932.6649169921875, 'M068_000_001_SP3', 'Battle Arena gambler'),
    (72, 73, 18952.591796875, 14936.1669921875, 932.3353271484375, 'M051_000_001_N', 'Angelina'),
    (73, 74, 18447.259765625, 16766.05859375, 931.7904052734375, 'M073_000_000_N', 'Aston'),
    (74, 75, 19451.37890625, 16853.583984375, 931.8806762695312, 'P_MALE_003_002_LARGIN', 'AstonLarkin'),
    (75, 76, 19984.349609375, 18249.3828125, 1111.4013671875, 'M023_000_001_SP1', 'Hasan'),
    (76, 77, 19927.845703125, 16956.8515625, 1111.401123046875, 'P_MALE_015_000_LING', 'Ringer'),
    (77, 78, 19551.431640625, 14194.8955078125, 932.6027221679688, 'P_MALE_015_000_BERULT', 'Beirut'),
    (78, 79, 18969.3046875, 16817.74609375, 931.8546142578125, 'P_FEMALE_015_000_MAYA', 'Maya'),
    (79, 80, 3475.299072265625, -6895.390625, 1405.065673828125, 'P_MALE_015_000_ZERALTIN', 'Salahuddin'),
    (80, 81, -11854.986328125, -771.3778076171875, 908.8687133789062, 'P_MALE_015_000_SLAVE', 'Unwanted slaves'),
    (81, 82, 8706.91015625, -4020.61865234375, 2027.12744140625, 'P_MALE_003_000_DANKEN', 'Duncan'),
    (82, 83, 3054.654541015625, 852.3408813476562, 2364.991943359375, 'P_MALE_003_002_CLOUZE', 'Kelas'),
    (84, 84, 1192.8818359375, -1175.2354736328125, 930.640625, 'M019_002_000_SP1', 'Qina'),
    (85, 85, -1939.2392578125, -298.05828857421875, 968.6619262695312, 'P_MALE_003_000_KAIM', 'Kaim'),
    (86, 86, -10974.884765625, -1231.232666015625, 747.3790893554688, 'M015_000_001_SP1', 'Mori Hiroko'),
    (87, 87, -15017.4814453125, -12759.953125, 308.2681884765625, 'M076_000_000_N', 'Sea Phantom'),
    (88, 88, 3021.427001953125, -7175.669921875, 935.0136108398438, 'P_FEMALE_030_000_KAREN', 'Karen'),
    (89, 89, 1536.47216796875, -721.6176147460938, 930.6406860351562, 'P_FEMALE_015_000_PETIRA', 'Betula'),
    (90, 90, 7873.7421875, 6701.62548828125, 1985.6571044921875, 'M073_000_001_N', 'Hood'),
    (91, 91, 1958.169921875, -8218.8662109375, 931.031982421875, 'M074_000_001_N', 'Local people'),
    (92, 92, 498.4258117675781, -4636.82373046875, 931.1251831054688, 'P_FEMALE_015_000_PENNY', 'Penny'),
    (95, 94, -4945.591796875, 14081.251953125, 314.1182861328125, 'M020_001_000_SP1', 'An Gebo Little Firebird'),
    (99, 42, 17748.896484375, -9097.921875, 2746.36865234375, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (100, 42, 17728.76171875, -12305.806640625, 2746.36865234375, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (101, 42, 16145.6015625, -11864.28125, 2758.929443359375, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (102, 42, 16105.7802734375, -9995.701171875, 2758.9296875, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (103, 97, 14455.2685546875, 9356.755859375, 2200.45849609375, 'M011_000_002_SP3', 'Mutant Green Eagle'),
    (105, 97, 13236.265625, 9364.3427734375, 2200.4599609375, 'M011_000_002_SP3', 'Mutant Green Eagle'),
    (107, 97, 15649.916015625, 9317.12109375, 2200.456298828125, 'M011_000_002_SP3', 'Mutant Green Eagle'),
    (109, 97, 11789.4384765625, 9318.8798828125, 2200.461181640625, 'M011_000_002_SP3', 'Mutant Green Eagle'),
    (111, 42, 21063.267578125, -1857.97265625, 2746.37060546875, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (112, 43, 22306.30859375, -1857.97265625, 2746.37060546875, 'P_MALE_002_002_EION', 'Iain'),
    (113, 42, 21060.810546875, -3240.96533203125, 2746.37060546875, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (114, 43, 22303.8515625, -3240.96533203125, 2746.37060546875, 'P_MALE_002_002_EION', 'Iain'),
    (115, 43, 22303.8515625, -4462.0361328125, 2746.361328125, 'P_MALE_002_002_EION', 'Iain'),
    (116, 42, 21060.810546875, -4462.0361328125, 2746.361328125, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (117, 68, 21166.662109375, -5410.67724609375, 2761.25537109375, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (118, 68, 22392.59765625, -5400.94775390625, 2746.361328125, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (119, 68, 22694.216796875, -5770.67431640625, 2759.498291015625, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (120, 68, 22032.599609375, -4393.92919921875, 2746.361328125, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (121, 68, 21370.984375, -3917.17724609375, 2746.361328125, 'P_FEMALE_012_000_VENONIKA', 'Veronica'),
    (122, 42, 21069.009765625, -9136.208984375, 2893.565673828125, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (123, 43, 22312.05078125, -9136.208984375, 2893.565673828125, 'P_MALE_002_002_EION', 'Iain'),
    (124, 42, 21053.298828125, -10310.2314453125, 2746.3798828125, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (125, 43, 22296.33984375, -10310.2314453125, 2746.3798828125, 'P_MALE_002_002_EION', 'Iain'),
    (126, 42, 21053.30078125, -11555.6259765625, 2746.3798828125, 'P_FEMALE_009_001_N', 'Excited Spice Merchant'),
    (127, 43, 22296.341796875, -11555.6259765625, 2746.3798828125, 'P_MALE_002_002_EION', 'Iain'),
    (128, 44, 18721.57421875, -6833.423828125, 2746.3798828125, 'M055_001_000_N', 'Magellan'),
    (129, 44, 24514.0546875, -6835.408203125, 2746.361328125, 'M055_001_000_N', 'Magellan'),
    (130, 44, 23669.044921875, -6820.1025390625, 2746.361328125, 'M055_001_000_N', 'Magellan'),
    (132, 103, 3722.39990234375, 21294.939453125, 84.98320007324219, 'M023_000_001_SP3', 'Orc Chief '),
    (140, 105, 24817.990234375, 7213.6826171875, 2379.879638671875, 'M055_000_000_N', 'Columbus'),
    (141, 106, 21962.94140625, 21118.892578125, 132.97219848632812, 'M070_000_000_N', 'Old Tom'),
    (142, 107, 22003.146484375, 21215.263671875, 132.97219848632812, 'M001_000_000_SP2', 'Port Side Pirates'),
    (143, 108, 23548.123046875, 6557.6337890625, 2379.87939453125, 'M015_000_003_SP2', 'Sea Devil'),
    (144, 109, 1788.796875, -1121.6756591796875, 930.423583984375, 'M072_000_000_N', 'Jessica'),
    (145, 110, 1788.796875, -1528.3853759765625, 930.423583984375, 'P_MALE_012_001_PHILI', 'Filet'),
    (146, 111, 5654.15185546875, -2501.903564453125, 1988.5660400390625, 'M010_000_001_SP3', 'Rob'),
    (147, 112, 5882.7294921875, -2021.7119140625, 1985.6571044921875, 'P_MALE_003_000_N', 'Rude pirates'),
    (148, 113, 13396.3779296875, -5367.951171875, 2210.97265625, 'M001_002_000_SP2', 'Pirates from afar'),
]

def make_v62_port_royal_population_snapshot(x: float, y: float, z: float):
    """Emit every currently unambiguous authentic Port Royal placement in one snapshot.

    V62 is the golden runtime-state baseline: base CNetNPC, NPCAttr template +
    visual preset, BasicAttr current/max HP 100/100, SceneID 1/Seq 0, and
    MovementAttr at the authentic placement XYZ.  V62 changes only MovementAttr heading (+0x34), while freezing all other
    actor semantics.  It keeps that proven packet shape from the nearest five
    to all 115 bg0001.npc placements whose MOBS row has exactly one non-empty
    s_OUTFIT preset.  Semicolon/multi-outfit rows remain excluded because their
    original server-side variant-selection rule is not yet statically resolved.

    Remote actor collection is snapshot/generation based, so all 115 actors are
    emitted together.  The identical snapshot is reapplied once after 3 seconds
    to preserve V59's proven model-ready -> idle initialization behavior.
    """
    chosen = list(PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS)
    entries = []
    for placement_idx, template_id, px, py, pz, visual_preset, display_name in chosen:
        aid = 0x2000 + placement_idx + 1
        npc_attr = make_npc_attr(template_id, aid, 1, 0, visual_preset)
        # V64 static-justified facing calibration. MovementAttr serializer 0x4671C0
        # proves bit 0x02 is float +0x34; CNetNPC::apply 0x45D34F/0x45D36D
        # copies MovementAttr+0x34 directly into the visual orientation fields
        # before normalization via 0x484450. Player TargetPos captures show the same
        # heading convention is a radian-like 0..2pi value. Use four cardinal values
        # deterministically by placement index so runtime can confirm sign/axis mapping
        # without touching any other NPC state.
        cardinal_headings = (0.0, 1.5707963267948966, 3.141592653589793, 4.71238898038469)
        heading = cardinal_headings[placement_idx & 3]
        mov_attr = make_remote_movement_attr(aid, px, py, pz, heading)
        entries.append(make_remote_actor_entry(4, aid, [
            (NPC_ATTR, npc_attr),
            (MOVEMENT_ATTR, mov_attr),
        ]))
    pc, fr = make_runtime_remote_actors(entries)
    label = f'V73_PORT_ROYAL_GOLDEN_POPULATION_{len(chosen)}'
    return label, pc, fr, chosen


V73_TICK = 0.50
V73_STEP = 150.0
V73_WALK_SPEED = 150.0
V73_MOVERS = (5,84,89,50,85,144)
V73_PHASE = {5:0,84:3,89:6,50:9,85:12,144:15}
V73_DIR0 = {5:0,84:1,89:2,50:3,85:0,144:1}
V73_DIRS=((0.0,-1.0,1.5707963267948966),(1.0,0.0,0.0),(0.0,1.0,4.71238898038469),(-1.0,0.0,3.141592653589793))
V73_STREAMS_PER_LEG=2
V73_HOLD_TICKS=5
V73_HOME_HOLD_TICKS=6

def _v73_cycle_len():
    return 4*(V73_STREAMS_PER_LEG+V73_HOLD_TICKS)

def _v73_cycle_target(dir0:int,rel:int,step:float=V73_STEP):
    if rel<0: return 0.0,0.0,None,'PRESTART'
    dirs=(dir0&3,(dir0+1)&3,(dir0+2)&3,(dir0+3)&3)
    dx=dy=0.0
    per_leg=V73_STREAMS_PER_LEG+V73_HOLD_TICKS
    for leg in range(4):
        leg_start=leg*per_leg
        ux,uy,h=V73_DIRS[dirs[leg]]
        if rel<leg_start: break
        local=rel-leg_start
        if local<V73_STREAMS_PER_LEG:
            n=local+1
            dx+=step*n*ux; dy+=step*n*uy
            return dx,dy,h,f'LEG_{leg+1}_STREAM_{n}'
        dx+=step*V73_STREAMS_PER_LEG*ux
        dy+=step*V73_STREAMS_PER_LEG*uy
        if local<per_leg: return dx,dy,h,f'HOLD_CORNER_{leg+1}'
    return dx,dy,V73_DIRS[dirs[3]][2],'HOME'

def _v73_target_for(placement_idx:int,global_tick:int):
    phase=V73_PHASE[placement_idx]; rel=global_tick-phase
    if rel<0: return 0.0,0.0,None,'PRESTART'
    step=V73_STEP
    c=_v73_cycle_len()
    if rel<c: return _v73_cycle_target(V73_DIR0[placement_idx],rel,step)
    hrel=rel-c
    if hrel<V73_HOME_HOLD_TICKS:
        return 0.0,0.0,V73_DIRS[(V73_DIR0[placement_idx]+3)&3][2],'HOLD_HOME_1'
    rel2=hrel-V73_HOME_HOLD_TICKS
    if rel2<c:
        dx,dy,h,state=_v73_cycle_target((V73_DIR0[placement_idx]+1)&3,rel2,step)
        return dx,dy,h,'CYCLE2_'+state
    return 0.0,0.0,V73_DIRS[V73_DIR0[placement_idx]][2],'HOLD_HOME_FINAL'

def make_v73_population_state(tick_index:int|None=None):
    chosen=list(PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS)
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    entries=[]
    for placement_idx,template_id,px,py,pz,visual_preset,display_name in chosen:
        aid=0x2000+placement_idx+1
        # V75: +0x54 is initialized once in the two model-ready baseline
        # snapshots. Runtime movement generations retain the client state and
        # do not re-enter movement-control setter 0x484580 every 0.50 seconds.
        speed=V73_WALK_SPEED if placement_idx in V73_MOVERS and tick_index is None else None
        npc_attr=make_npc_attr(template_id,aid,1,0,visual_preset,movement_speed=speed)
        base_h=headings[placement_idx&3]
        if tick_index is not None and placement_idx in V73_MOVERS:
            dx,dy,h,state=_v73_target_for(placement_idx,tick_index)
            if h is None: h=base_h
            mov_attr=make_remote_movement_attr(aid,px+dx,py+dy,pz,h,mask=0x03)
        else:
            mov_attr=make_remote_movement_attr(aid,px,py,pz,base_h)
        entries.append(make_remote_actor_entry(4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov_attr)]))
    return make_runtime_remote_actors(entries)

def make_v73_stateful_wander_sequence():
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    total=max(V73_PHASE.values())+2*_v73_cycle_len()+V73_HOME_HOLD_TICKS+8
    seq=[]
    for tick in range(total):
        pc,fr=make_v73_population_state(tick)
        states=[]
        for idx in V73_MOVERS:
            dx,dy,h,state=_v73_target_for(idx,tick)
            states.append(f'P{idx}:{by_idx[idx][6]}:{state}:DX{int(dx)}:DY{int(dy)}')
        seq.append((f"V75_SPEED_PIN_BASELINE_ONLY_TICK_{tick:02d}_"+','.join(states),pc,fr,0.0 if tick==0 else V73_TICK))
    return seq


# V89 brings the confirmed V87 walking formula back to V72's overlapping,
# stateful ambient scheduler. Only P5 (blue tiger), P144 (beer tray carrier),
# and P50 (Atlantis) exist. All three receive walk speed 150 in every complete
# generation and move on separated 300x300 squares, two rounds, with 150-unit
# targets every 0.50 seconds. Staggered starts exercise concurrent scheduling
# without visually stacking all turns on one frame. There are no artificial
# corner holds: every active tick advances to the next persistent target.
V89_TEST_INDICES=(5,144,50)
V89_LANE_X=(-500.0,0.0,500.0)
V89_HOME_Y=120.0
V89_WALK_SPEED=150.0
V89_STEP=150.0
V89_TICK=0.50
V89_STREAMS_PER_LEG=2
V89_CYCLES=2
V89_PHASE={5:0,144:2,50:4}
V89_DIR0={5:0,144:1,50:2}
V89_DIRS=(
    (0.0,-1.0,1.5707963267948966),
    (1.0,0.0,0.0),
    (0.0,1.0,4.71238898038469),
    (-1.0,0.0,3.141592653589793),
)

def _v89_cycle_len():
    return 4*V89_STREAMS_PER_LEG

def _v89_cycle_target(dir0:int,rel:int):
    dirs=(dir0&3,(dir0+1)&3,(dir0+2)&3,(dir0+3)&3)
    dx=dy=0.0
    for leg in range(4):
        ux,uy,h=V89_DIRS[dirs[leg]]
        leg_start=leg*V89_STREAMS_PER_LEG
        if rel<leg_start:
            break
        local=rel-leg_start
        if local<V89_STREAMS_PER_LEG:
            n=local+1
            dx+=V89_STEP*n*ux; dy+=V89_STEP*n*uy
            return dx,dy,h,f'LEG_{leg+1}_STREAM_{n}'
        dx+=V89_STEP*V89_STREAMS_PER_LEG*ux
        dy+=V89_STEP*V89_STREAMS_PER_LEG*uy
    return 0.0,0.0,V89_DIRS[dirs[3]][2],'HOME'

def _v89_target_for(idx:int,global_tick:int):
    rel=global_tick-V89_PHASE[idx]
    if rel<0:
        return 0.0,0.0,V89_DIRS[V89_DIR0[idx]][2],'PRESTART'
    cycle_len=_v89_cycle_len()
    if rel<V89_CYCLES*cycle_len:
        cycle=rel//cycle_len
        dx,dy,h,state=_v89_cycle_target(V89_DIR0[idx],rel%cycle_len)
        return dx,dy,h,f'CYCLE_{cycle+1}_{state}'
    return 0.0,0.0,V89_DIRS[V89_DIR0[idx]][2],'HOME_FINAL'

def make_v89_ground_state(player_x:float,player_y:float,player_z:float,
                          tick:int|None=None):
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    entries=[]
    for lane,idx in enumerate(V89_TEST_INDICES):
        _,template_id,_,_,_,preset,_=by_idx[idx]
        aid=0x3100+lane+1
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,movement_speed=V89_WALK_SPEED
        )
        dx=dy=0.0; heading=V89_DIRS[V89_DIR0[idx]][2]
        if tick is not None:
            dx,dy,heading,_=_v89_target_for(idx,tick)
        mov=make_remote_movement_attr(
            aid,player_x+V89_LANE_X[lane]+dx,player_y+V89_HOME_Y+dy,
            player_z,heading,mask=0xFF if tick is None else 0x03,
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov)]
        ))
    return make_runtime_remote_actors(entries)

def make_v89_ground_sequence(player_x:float,player_y:float,player_z:float):
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    total=max(V89_PHASE.values())+V89_CYCLES*_v89_cycle_len()
    seq=[]
    for tick in range(total):
        pc,fr=make_v89_ground_state(player_x,player_y,player_z,tick)
        states=[]
        for idx in V89_TEST_INDICES:
            dx,dy,_,state=_v89_target_for(idx,tick)
            states.append(f'P{idx}:{by_idx[idx][6]}:{state}:DX{int(dx)}:DY{int(dy)}')
        seq.append((
            f'V89_AMBIENT_WALK_TICK_{tick:02d}_'+','.join(states),
            pc,fr,0.0 if tick==0 else V89_TICK,
        ))
    return seq


# V90 local-population integration layer. Keep the three V89-proven movers in
# their safe player-relative lanes, then fill the snapshot with the nearest 17
# other unambiguous Port Royal placements at their authentic XYZ coordinates.
# Static placements are not assigned invented routes. This is the first bounded
# data-driven population step while actor-removal semantics remain unresolved.
V90_LOCAL_LIMIT=20
V90_STATIC_LIMIT=V90_LOCAL_LIMIT-len(V89_TEST_INDICES)

def _v90_nearest_static(player_x:float,player_y:float,player_z:float):
    movers=set(V89_TEST_INDICES)
    candidates=[]
    for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS:
        idx,_,px,py,pz,_,_=row
        if idx in movers:
            continue
        distance2=(px-player_x)**2+(py-player_y)**2+(pz-player_z)**2
        candidates.append((distance2,idx,row))
    candidates.sort(key=lambda item:(item[0],item[1]))
    return [item[2] for item in candidates[:V90_STATIC_LIMIT]]

def make_v90_local_state(player_x:float,player_y:float,player_z:float,
                         tick:int|None=None):
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    entries=[]

    # Proven ambient movers: unchanged V89 lane geometry and state machine.
    for lane,idx in enumerate(V89_TEST_INDICES):
        _,template_id,_,_,_,preset,_=by_idx[idx]
        aid=0x3100+lane+1
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,movement_speed=V89_WALK_SPEED
        )
        dx=dy=0.0; heading=V89_DIRS[V89_DIR0[idx]][2]
        if tick is not None:
            dx,dy,heading,_=_v89_target_for(idx,tick)
        mov=make_remote_movement_attr(
            aid,player_x+V89_LANE_X[lane]+dx,player_y+V89_HOME_Y+dy,
            player_z,heading,mask=0xFF if tick is None else 0x03,
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov)]
        ))

    # Data-selected local population: authentic placement XYZ and established
    # baseline facing only; no speculative movement or AI field.
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    for idx,template_id,px,py,pz,preset,_ in _v90_nearest_static(
        player_x,player_y,player_z
    ):
        aid=0x2000+idx+1
        npc_attr=make_npc_attr(template_id,aid,1,0,preset)
        mov=make_remote_movement_attr(
            aid,px,py,pz,headings[idx&3],mask=0xFF if tick is None else 0x03,
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov)]
        ))
    return make_runtime_remote_actors(entries)

def make_v90_local_sequence(player_x:float,player_y:float,player_z:float):
    static_rows=_v90_nearest_static(player_x,player_y,player_z)
    static_ids=','.join(f'P{row[0]}' for row in static_rows)
    total=max(V89_PHASE.values())+V89_CYCLES*_v89_cycle_len()
    seq=[]
    for tick in range(total):
        pc,fr=make_v90_local_state(player_x,player_y,player_z,tick)
        states=[]
        for idx in V89_TEST_INDICES:
            dx,dy,_,state=_v89_target_for(idx,tick)
            states.append(f'P{idx}:{state}:DX{int(dx)}:DY{int(dy)}')
        seq.append((
            f'V90_LOCAL20_TICK_{tick:02d}_'+','.join(states)+
            f'_STATIC[{static_ids}]',
            pc,fr,0.0 if tick==0 else V89_TICK,
        ))
    return seq


# V91 corrects the only V90 behavior implicated by the user's distant-NPC
# stutter observation. The baseline/reapply still contains all 20 actors, but
# cadence frames contain only the three actual movers. Static actors are not
# reconstructed and do not receive repeated same-position MovementAttr tasks.
def make_v91_movers_state(player_x:float,player_y:float,player_z:float,
                          tick:int):
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    entries=[]
    for lane,idx in enumerate(V89_TEST_INDICES):
        _,template_id,_,_,_,preset,_=by_idx[idx]
        aid=0x3100+lane+1
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,movement_speed=V89_WALK_SPEED
        )
        dx,dy,heading,_=_v89_target_for(idx,tick)
        mov=make_remote_movement_attr(
            aid,player_x+V89_LANE_X[lane]+dx,player_y+V89_HOME_Y+dy,
            player_z,heading,mask=0x03,
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov)]
        ))
    return make_runtime_remote_actors(entries)

def make_v91_local_sequence(player_x:float,player_y:float,player_z:float):
    total=max(V89_PHASE.values())+V89_CYCLES*_v89_cycle_len()
    seq=[]
    for tick in range(total):
        pc,fr=make_v91_movers_state(player_x,player_y,player_z,tick)
        states=[]
        for idx in V89_TEST_INDICES:
            dx,dy,_,state=_v89_target_for(idx,tick)
            states.append(f'P{idx}:{state}:DX{int(dx)}:DY{int(dy)}')
        seq.append((
            f'V91_MOVERS_ONLY_TICK_{tick:02d}_'+','.join(states),
            pc,fr,0.0 if tick==0 else V89_TICK,
        ))
    return seq


# V92 follows the runtime-proven authoritative-generation behavior from V91:
# omitting static actors despawns them. Keep all 20 identities in every cadence
# generation, but static entries carry NPCAttr only. This preserves membership
# without reissuing same-position MovementAttr tasks.
def make_v92_membership_state(player_x:float,player_y:float,player_z:float,
                              tick:int):
    by_idx={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    entries=[]
    for lane,idx in enumerate(V89_TEST_INDICES):
        _,template_id,_,_,_,preset,_=by_idx[idx]
        aid=0x3100+lane+1
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,movement_speed=V89_WALK_SPEED
        )
        dx,dy,heading,_=_v89_target_for(idx,tick)
        mov=make_remote_movement_attr(
            aid,player_x+V89_LANE_X[lane]+dx,player_y+V89_HOME_Y+dy,
            player_z,heading,mask=0x03,
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov)]
        ))

    for idx,template_id,_,_,_,preset,_ in _v90_nearest_static(
        player_x,player_y,player_z
    ):
        aid=0x2000+idx+1
        npc_attr=make_npc_attr(template_id,aid,1,0,preset)
        entries.append(make_remote_actor_entry(4,aid,[(NPC_ATTR,npc_attr)]))
    return make_runtime_remote_actors(entries)

def make_v92_local_sequence(player_x:float,player_y:float,player_z:float):
    total=max(V89_PHASE.values())+V89_CYCLES*_v89_cycle_len()
    seq=[]
    for tick in range(total):
        pc,fr=make_v92_membership_state(player_x,player_y,player_z,tick)
        states=[]
        for idx in V89_TEST_INDICES:
            dx,dy,_,state=_v89_target_for(idx,tick)
            states.append(f'P{idx}:{state}:DX{int(dx)}:DY{int(dy)}')
        seq.append((
            f'V92_MEMBERSHIP20_STATIC_NO_MOVEMENT_TICK_{tick:02d}_'+
            ','.join(states),pc,fr,0.0 if tick==0 else V89_TICK,
        ))
    return seq


# V94 local population streaming. V91 proved omitted members disappear and V92
# proved retained static members need only NPCAttr. Initial/new members receive
# their authentic placement position. There are no synthetic movers or routes.
V94_LOCAL_LIMIT=20
V94_REFRESH_DISTANCE=1000.0

def _v94_nearest_population(player_x:float,player_y:float,player_z:float):
    candidates=[]
    for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS:
        idx,_,px,py,pz,_,_=row
        distance2=(px-player_x)**2+(py-player_y)**2+(pz-player_z)**2
        candidates.append((distance2,idx,row))
    candidates.sort(key=lambda item:(item[0],item[1]))
    return [item[2] for item in candidates[:V94_LOCAL_LIMIT]]

def make_v94_population_state(player_x:float,player_y:float,player_z:float,
                              previous_indices:set[int]|None=None):
    rows=_v94_nearest_population(player_x,player_y,player_z)
    entries=[]
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    for idx,template_id,px,py,pz,preset,_ in rows:
        aid=0x2000+idx+1
        npc_attr=make_npc_attr(template_id,aid,1,0,preset)
        attrs=[(NPC_ATTR,npc_attr)]
        # Initial population and actors entering a refreshed population need a
        # proven position. Retained members deliberately omit MovementAttr.
        if previous_indices is None or idx not in previous_indices:
            mov=make_remote_movement_attr(
                aid,px,py,pz,headings[idx&3],mask=0xFF
            )
            attrs.append((MOVEMENT_ATTR,mov))
        entries.append(make_remote_actor_entry(4,aid,attrs))
    pc,fr=make_runtime_remote_actors(entries)
    return pc,fr,rows


# V129 expands the isolated V112 population with exact P0/template1. All three
# records and positions come directly from the decoded Port Royal placement
# table above. P0 and P91 are audited MOBS usage 2; P30/template31 is usage 1.
# Every first-generation entrant gets its complete placement MovementAttr. No
# locomotion schedule follows.
V112_TEST_INDICES=(0,30,91)
V112_USAGE_BY_TEMPLATE={1:2,31:1,91:2}
V129_QUEST_ACTOR_INDEX=0
V129_QUEST_ACTOR_TEMPLATE=1
V112_MONSTER_INDEX=30
V112_MONSTER_TEMPLATE=31
V112_MONSTER_ACTOR_ID=0x201F
V112_SHOP_TRIGGER_INDEX=91
V112_SHOP_TRIGGER_TEMPLATE=91
V112_SHOP_TRIGGER_ACTOR_ID=0x205C
V117_P30_EXACT_HP=3857
V119_BASICATTR_NAME_MASK=0x0001
V119_P30_TARGET_NAME="Tornado Eagle"
V112_PLAYER_X=1958.169921875
V112_PLAYER_Y=-8218.8662109375
V112_PLAYER_Z=931.031982421875
V116_PLAYER_X=V112_PLAYER_X+100.0
V116_PLAYER_Y=V112_PLAYER_Y
V116_PLAYER_Z=V112_PLAYER_Z
# Data-backed P30 placement plus the already proven 100-unit observation
# pattern. Keep the actor itself at the exact placement from the decoded row.
V127_PLAYER_X=1847.5244140625
V127_PLAYER_Y=-7837.69775390625
V127_PLAYER_Z=931.0413208007812
# Exact P0 placement plus the same proven 100-unit observation pattern.
V129_PLAYER_X=-9039.95703125
V129_PLAYER_Y=-2780.045166015625
V129_PLAYER_Z=223.29209899902344
# V134 mirrors V133's runtime-proven camera workaround: heading-zero player is
# 100 units below P0 on X, so the exact actor at +100X starts in view.
V134_PLAYER_X=-9239.95703125
V134_PLAYER_Y=V129_PLAYER_Y
V134_PLAYER_Z=V129_PLAYER_Z
# V135 retains P0-100X and adds a bounded 50-unit lateral offset. P0 is then
# relative (+100X,+50Y), 26.565 degrees off the heading-zero center line.
V135_PLAYER_X=V134_PLAYER_X
V135_PLAYER_Y=-2830.045166015625
V135_PLAYER_Z=V134_PLAYER_Z


def _v112_test_rows(indices: tuple[int, ...] = V112_TEST_INDICES):
    rows_by_index={row[0]:row for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    return [rows_by_index[idx] for idx in indices]


def make_v112_monster_shop_population_state(
    p30_hp: int = V117_P30_EXACT_HP,
    p30_basic_name: str = V119_P30_TARGET_NAME,
    indices: tuple[int, ...] = V112_TEST_INDICES,
):
    """Three exact entrants; P30 keeps proven HP/name, P0/P91 stay minimal."""
    rows=_v112_test_rows(indices)
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    entries=[]
    for idx,template_id,px,py,pz,preset,_name in rows:
        aid=0x2000+idx+1
        hp=p30_hp if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(p30_basic_name if idx==V112_MONSTER_INDEX else ""),
        )
        movement_attr=make_remote_movement_attr(
            aid,px,py,pz,headings[idx&3],mask=0xFF
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,movement_attr)]
        ))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame,rows


def make_v138_marker1_population_state():
    """Authoritative nearest-20 snapshot at decoded MARKER1 XYZ.

    This is an initial generation for the destination world, so every member
    receives its complete authentic placement MovementAttr. P30 preserves the
    exact V117 HP and V119 BasicAttr name instead of regressing to V94 defaults.
    """
    rows=_v94_nearest_population(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    if tuple(row[0] for row in rows)!=V138_MARKER1_NEAREST_INDICES:
        raise AssertionError('V138 MARKER1 nearest-20 membership drift')
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    entries=[]
    for idx,template_id,px,py,pz,preset,_name in rows:
        aid=0x2000+idx+1
        hp=V117_P30_EXACT_HP if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(V119_P30_TARGET_NAME if idx==V112_MONSTER_INDEX else ''),
        )
        movement_attr=make_remote_movement_attr(
            aid,px,py,pz,headings[idx&3],mask=0xFF
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,movement_attr)]
        ))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame,rows


def make_v140_marker1_population_state():
    """V138 destination snapshot with only P86 MovementAttr XYZ overridden."""
    rows=_v94_nearest_population(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    if tuple(row[0] for row in rows)!=V138_MARKER1_NEAREST_INDICES:
        raise AssertionError('V140 MARKER1 nearest-20 membership drift')
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    entries=[]
    for idx,template_id,px,py,pz,preset,_name in rows:
        aid=0x2000+idx+1
        hp=V117_P30_EXACT_HP if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(V119_P30_TARGET_NAME if idx==V112_MONSTER_INDEX else ''),
        )
        movement_xyz=(
            (V140_P86_HARNESS_X,V140_P86_HARNESS_Y,V140_P86_HARNESS_Z)
            if idx==V139_P86_INDEX else (px,py,pz)
        )
        movement_attr=make_remote_movement_attr(
            aid,*movement_xyz,headings[idx&3],mask=0xFF
        )
        entries.append(make_remote_actor_entry(
            4,aid,[(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,movement_attr)]
        ))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame,rows


def make_v141_population_refresh_state(
    player_x: float,
    player_y: float,
    player_z: float,
    previous_indices: set[int],
):
    """V95 nearest-20 refresh with current P30/P86 state preservation.

    Retained actors deliberately carry NPCAttr only. That omission preserves
    P86's existing V140 harness position while P86 remains in membership.
    Every entrant—including P86 after an actual leave—receives its authentic
    decoded placement MovementAttr. P30 keeps the V117/V119 HP/name fields in
    every refresh snapshot where it is a member.
    """
    rows=_v94_nearest_population(player_x,player_y,player_z)
    headings=(0.0,1.5707963267948966,3.141592653589793,4.71238898038469)
    entries=[]
    for idx,template_id,px,py,pz,preset,_name in rows:
        aid=0x2000+idx+1
        hp=V117_P30_EXACT_HP if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(V119_P30_TARGET_NAME if idx==V112_MONSTER_INDEX else ''),
        )
        attrs=[(NPC_ATTR,npc_attr)]
        if idx not in previous_indices:
            attrs.append((
                MOVEMENT_ATTR,
                make_remote_movement_attr(
                    aid,px,py,pz,headings[idx&3],mask=0xFF,
                ),
            ))
        entries.append(make_remote_actor_entry(4,aid,attrs))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame,rows


def make_v139_p86_face_state(player_x: float, player_y: float):
    """Preserve V138 NPC attrs and turn only current P86 toward fresh XYZ.

    The selected actor receives the V98-safe complete MovementAttr mask 0x03:
    authentic placement XYZ plus a derived heading. Every retained actor keeps
    the exact V138 NPCAttr construction; in particular P30 remains 3857/3857
    with BasicAttr name ``Tornado Eagle``. No retained actor other than P86
    receives MovementAttr in this facing generation.
    """
    by_idx={row[0]:row for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    if V139_P86_INDEX not in V138_MARKER1_NEAREST_INDICES:
        raise AssertionError('V139 P86 is not in V138 destination membership')
    entries=[]
    for idx in V138_MARKER1_NEAREST_INDICES:
        _,template_id,px,py,pz,preset,_name=by_idx[idx]
        aid=0x2000+idx+1
        hp=V117_P30_EXACT_HP if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(V119_P30_TARGET_NAME if idx==V112_MONSTER_INDEX else ''),
        )
        attrs=[(NPC_ATTR,npc_attr)]
        if idx==V139_P86_INDEX:
            attrs.append((
                MOVEMENT_ATTR,
                make_remote_movement_attr(
                    aid,px,py,pz,
                    _heading_to_player(px,py,player_x,player_y),
                    mask=0x03,
                ),
            ))
        entries.append(make_remote_actor_entry(4,aid,attrs))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame


def make_v140_p86_face_state(player_x: float, player_y: float):
    """V139 safe face with P86 consistently kept at its V140 harness XYZ."""
    by_idx={row[0]:row for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    if V139_P86_INDEX not in V138_MARKER1_NEAREST_INDICES:
        raise AssertionError('V140 P86 is not in V138 destination membership')
    entries=[]
    for idx in V138_MARKER1_NEAREST_INDICES:
        _,template_id,px,py,pz,preset,_name=by_idx[idx]
        aid=0x2000+idx+1
        hp=V117_P30_EXACT_HP if idx==V112_MONSTER_INDEX else 100
        npc_attr=make_npc_attr(
            template_id,aid,1,0,preset,current_hp=hp,max_hp=hp,
            basic_name=(V119_P30_TARGET_NAME if idx==V112_MONSTER_INDEX else ''),
        )
        attrs=[(NPC_ATTR,npc_attr)]
        if idx==V139_P86_INDEX:
            attrs.append((
                MOVEMENT_ATTR,
                make_remote_movement_attr(
                    aid,
                    V140_P86_HARNESS_X,
                    V140_P86_HARNESS_Y,
                    V140_P86_HARNESS_Z,
                    _heading_to_player(
                        V140_P86_HARNESS_X,V140_P86_HARNESS_Y,
                        player_x,player_y,
                    ),
                    mask=0x03,
                ),
            ))
        entries.append(make_remote_actor_entry(4,aid,attrs))
    pc,frame=make_runtime_remote_actors(entries)
    return pc,frame


def make_v64_nearest_position_delta(player_x: float, player_y: float, player_z: float):
    """High-information live-movement branch probe: position + movement mode 1.

    Static RE of CNetNPC tick 0x45D490 proves MovementAttr +0x38 is copied to
    CNetNPC+0x110 and tested as a strict zero/non-zero branch:
      mode == 0  -> direct/static transform path
      mode != 0  -> controller/locomotion path and CActorTask_ActorMove creation

    V62/V63 both preserved mode 0. V64 changes exactly one semantic state:
      - same actor identity and +300 X destination
      - same 115-actor generation / HP / NPCAttr / outfit / heading baseline
      - delta mask 0x05 = position (0x01) + movement mode (0x04)
      - mode_u8 = 1, the minimal representative of the disassembly-proven
        non-zero branch (not a sweep; not yet claimed to mean walk)
      - flags and auxiliary floats remain omitted/inherited
    """
    chosen = list(PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS)
    nearest = min(chosen, key=lambda r: (r[2]-player_x)**2 + (r[3]-player_y)**2 + (r[4]-player_z)**2)
    nearest_idx = nearest[0]
    entries=[]
    cardinal_headings=(0.0, 1.5707963267948966, 3.141592653589793, 4.71238898038469)
    for placement_idx, template_id, px, py, pz, visual_preset, display_name in chosen:
        aid = 0x2000 + placement_idx + 1
        npc_attr = make_npc_attr(template_id, aid, 1, 0, visual_preset)
        heading=cardinal_headings[placement_idx & 3]
        if placement_idx == nearest_idx:
            mov_attr = make_remote_movement_attr(
                aid, px + 300.0, py, pz, heading, mask=0x05, mode_u8=1
            )
        else:
            mov_attr = make_remote_movement_attr(aid, px, py, pz, heading)
        entries.append(make_remote_actor_entry(4, aid, [(NPC_ATTR,npc_attr),(MOVEMENT_ATTR,mov_attr)]))
    pc,fr=make_runtime_remote_actors(entries)
    return f'V64_EXISTING_NPC_POSITION_PLUS_NONZERO_MODE1_P{nearest[0]}_{nearest[6]}_DX300', pc, fr, nearest


def make_action_vital_payload(actor_identity: int, x: float, y: float, z: float, action_id: int = ACTION_IDLE_NEUTRAL, heading: float = 0.0) -> bytes:
    """Binary-derived ActionVital v0 body (serializer 0x74E6A0).

    Static RE after V55 proved that the locomotion-action family is 0xEA60..0xEA71.
    Function 0x4494D0 maps the no-direction movement state to 0xEA60 in the
    default mode, while 0x48E080 gives 0xEA60/0xEA69 explicit stationary
    handling distinct from the sixteen directional variants.  Therefore V56
    tests only 0xEA60 as the default neutral/idle locomotion action.

    The final u16 is kept at 1 because a real client-emitted ActionVital v0 in
    the V55 GAME log used that wire value.  Handler 0x7516C0 does not consume
    the field for the 0xEA60 locomotion branch.
    """
    return (
        qwordtag(0x32, actor_identity)
        + qwordtag(0x32, 0)
        + qwordtag(0x32, 0)
        + u32tag(0x14, action_id)
        + u32tag(0x19, 0)
        + f32tag(heading)
        + f32tag(x)
        + f32tag(y)
        + f32tag(z)
        + u8tag(0x0B, 0)
        + u16tag(0x12, 1)
        + u8tag(0x0B, 0)
    )


def make_v56_idle_action_packet(chosen) -> tuple[bytes, bytes]:
    """Send one ActionVital EA60 for every actor created by the V55 snapshot.

    This is intentionally a separate inherited-VitalData RuntimeRes sent after
    actor creation.  It contains NO derived remote-actor collection, so it cannot
    replace/reset the five-actor snapshot through generation semantics.
    """
    vitals = []
    for placement_idx, template_id, px, py, pz, visual_preset, display_name in chosen:
        aid = 0x2000 + placement_idx + 1
        vitals.append((ACTION_VITAL, 0, make_action_vital_payload(aid, px, py, pz)))
    return make_runtime_vitals(vitals)


def make_runtime_res_empty_exact() -> tuple[bytes, bytes]:
    """Binary-exact empty GSCN_RunTimeProtocolRes v4 heartbeat.

    Static correction from serializer chain:
      PcProtocol fields: ID / dword / version
      inherited Runtime base serializer 0x5F4070: tag0B mask for +0x18 VitalData list
      RuntimeRes serializer 0x5E3EE0: second tag0B mask for +0x1C/+0x20/+0x24

    With every optional pointer NULL (constructor 0x5E3720), the exact body ends
    in two consecutive zero masks.  This is intentionally NOT make_runtime_vital():
    that helper preserves the runtime-proven v25 SelectActor wire shape.
    """
    pc = bytearray()
    pc += u16tag(0x12, GSCN_RUNTIME_PROTOCOL_RES)
    pc += u32tag(0x14, 0)
    pc += u8tag(0x08, 4)
    pc += u8tag(0x0B, 0)  # inherited VitalData list absent
    pc += u8tag(0x0B, 0)  # RuntimeRes extension fields absent
    pc = bytes(pc)
    return pc, frame_pc(pc)


def make_runtime_select_actor_empty() -> tuple[bytes, bytes]:
    return make_runtime_vital(SELECT_ACTOR_VITAL, 10, make_select_actor_empty_payload())




def get_preset_actor_wire() -> bytes:
    """Return the runtime-proven actor object captured from the real v25 create submit.

    The actor serializer used by SelectActorVital is the same 0x5DFF60 actor-object
    serializer used by CreateActorVital. Keeping this exact captured object lets the
    emulator present a persistent character without asking the user to recreate one.
    """
    parsed = parse_outer(_V25_REAL_CREATE_PC)
    op, has_actor, actor_wire = parse_create_actor(parsed)
    if op != 1 or has_actor != 1 or not actor_wire:
        raise AssertionError('preset actor capture is invalid')
    return actor_wire


def extract_avatar_attr_wire_from_actor(actor_wire: bytes) -> bytes:
    """Extract the exact embedded AvatarAttr serialization from a captured actor object.

    Binary correlation: CreateActorDataEx serializer 0x5DFF60 serializes its embedded
    AvatarAttr with the same common Attr serializer (0x467790) and AvatarAttr serializer
    (0x464560) used by standalone AvatarAttr entries in StartGameRes.  Therefore the
    byte range beginning at the embedded Attr mask and ending after AvatarAttr's own
    bit-selected fields can be reused verbatim, preserving gender/body/equipment IDs
    instead of sending the mask=0 placeholder used in v31-v38.
    """
    c = Cursor(actor_wire)
    c.raw8(0x32)            # actor identity
    c.u8(0x0B)              # selector
    c.wstr()                # name
    c.u8(0x0B); c.u8(0x0B)  # appearance/create bytes
    c.u32(0x19)
    c.u16(0x12); c.u16(0x12)
    c.astr(); c.wstr()
    start = c.p

    base_flags = c.u8(0x0B)
    if base_flags & 0x01:
        c.raw8(0x32)
    mask = c.u32(0x26)
    for bit in range(12):
        if mask & (1 << bit):
            c.u32(0x14)
    if mask & (1 << 12): c.u8(0x0B)
    if mask & (1 << 13): c.u8(0x08)
    if mask & (1 << 14): c.u8(0x08)
    if mask & (1 << 15): c.astr()
    if mask & (1 << 16): c.u8(0x0B)
    if mask & (1 << 17): c.u32(0x14)
    if mask & (1 << 18): c.u8(0x0B)
    if mask & (1 << 19): c.u8(0x0B)
    if mask & (1 << 20): c.u32(0x14)
    return actor_wire[start:c.p]


def make_avatar_attr_from_preset() -> bytes:
    return extract_avatar_attr_wire_from_actor(get_preset_actor_wire())


def make_select_actor_preset_payload() -> bytes:
    """SelectActorVital v10 with one persisted actor.

    Direct serializer 0x5EBAE0 writes the five fixed fields, then tag0B actor-count,
    then each actor through actor serializer 0x5DFF60.  Two trailing zero masks are
    retained because the exact v25 RuntimeRes wire requires them for this client build.
    """
    actor_wire = get_preset_actor_wire()
    return (
        u8tag(0x0B, 0)
        + u32tag(0x14, 0)
        + u32tag(0x14, 0)
        + u32tag(0x1F, 0)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 1)
        + actor_wire
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 0)
    )


def make_runtime_select_actor_preset() -> tuple[bytes, bytes]:
    return make_runtime_vital(SELECT_ACTOR_VITAL, 10, make_select_actor_preset_payload())


def make_runtime_create_actor_success(actor_wire: bytes) -> tuple[bytes, bytes]:
    """CreateActorVital v8 success/update response.

    Binary-proven inbound handler 0x5EFD50 only inserts the actor object when
    byte +0x14 == 1 and actor pointer +0x18 is present. It then passes that
    same status byte to the character-create state handler. Therefore v30
    answers the captured submit (op=1) with op/status=1 and the exact actor
    object emitted by the client, without inventing server-side fields yet.
    """
    vital_payload = u8tag(0x08, 1) + u8tag(0x0B, 1) + actor_wire
    return make_login_vital(CREATE_ACTOR_VITAL, 8, vital_payload)



def make_actor_attr_minimal(identity_lo: int = 0, identity_hi: int = 0,
                            scene_id: int = 1, scene_seq: int = 0,
                            cash: int = V116_INITIAL_CASH) -> bytes:
    """ActorAttr bootstrap with alive pair + binary-proven scene identity.

    BasicAttr serializer 0x4656F0 maps:
      0x0004 -> +0x44 u32
      0x0008 -> +0x48 u32
      0x0100 -> +0x5C u16
      0x0200 -> +0x60 qword/tag0x32

    Binary xrefs now prove +0x5C is the current SceneID: code at 0x424FBA
    reads ActorAttr+0x5C and compares/caches it as the active scene identifier.
    Teleport-target construction at 0x4B4C67 copies ActorAttr+0x5C and +0x60
    directly into the TeleportVital target's SceneID and SceneSeq fields.

    V36 therefore supplies one non-zero scene id (1) plus zero SceneSeq while
    retaining the runtime-proven alive pair 100/100. V116 adds only the
    independently proven ActorAttr mask bit 0x800 and qword +0xA8 cash field.
    The cart validation at 0x4E7B7C and GetCash binding at 0x461B70 read this
    exact qword; no adjacent ActorAttr field is inferred.
    """
    basic_mask = 0x000C | 0x0100 | 0x0200
    return (
        u8tag(0x0B, 1)
        + bytes([0x32]) + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + u16tag(0x12, basic_mask)
        + u32tag(0x14, 100)
        + u32tag(0x14, 100)
        + u16tag(0x12, scene_id & 0xFFFF)
        + bytes([0x32]) + struct.pack("<Q", scene_seq & 0xFFFFFFFFFFFFFFFF)
        + bytes([0x32]) + struct.pack("<II", 0x800, 0)
        + u8tag(0x05, 1)
        + bytes([0x32]) + struct.pack("<Q", cash & 0xFFFFFFFFFFFFFFFF)
    )


def make_update_attr_cash_only(cash: int = V122_FINAL_CASH) -> tuple[bytes, bytes]:
    """Send the full current ActorAttr with only its proven cash qword changed.

    UpdateAttrVital is ID 0x309A, constructor 0x5E5D30, vtable 0xF303E0,
    and nested version 0. Serializer 0x5E42C0 delegates its AttrList to
    0x463DE0: tag12/u16 count, then tag12/u16 Attr ID, tag14/u32 body length,
    and the exact Attr body. Handler 0x5F2400 applies each incoming Attr to the
    current object. ActorAttr apply method 0x464F30 copies the complete object,
    so a constructor-default cash-only delta would reset unrelated live state.
    Reuse the exact bootstrap ActorAttr and alter only +0xA8 cash.
    """
    if cash != V122_FINAL_CASH:
        raise ValueError(f"V122 supports only the proven cash target zero: {cash}")
    actor_attr = make_actor_attr_minimal(cash=cash)
    if len(actor_attr) != 56:
        raise AssertionError(f"unexpected V122 ActorAttr length: {len(actor_attr)}")
    payload = (
        u16tag(0x12, 1)
        + u16tag(0x12, ACTOR_ATTR)
        + u32tag(0x14, len(actor_attr))
        + actor_attr
    )
    return make_runtime_vitals([(UPDATE_ATTR_VITAL, 0, payload)])



def make_avatar_attr_minimal(identity_lo: int = 0, identity_hi: int = 0) -> bytes:
    """Binary-derived minimum AvatarAttr object.

    AvatarAttr ID is 0x16A0 (global ID at 0x1033468). Its vtable
    points to serializer 0x464560. That serializer first invokes the common
    Attr serializer 0x467790, then unconditionally writes the AvatarAttr
    32-bit change mask from object+0x28 with PcBinary tag 0x26. If the mask
    is zero, no AvatarAttr-specific fields follow.

    We keep the same (0,0) identity as the ActorAttr/CreateActor experiment
    so the only new variable in v31 is presence of AvatarAttr itself.
    """
    return (
        u8tag(0x0B, 1)
        + bytes([0x32]) + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + u32tag(0x26, 0)
    )




def make_movement_attr_minimal(identity_lo: int = 0, identity_hi: int = 0,
                               x: float = 0.0, y: float = 0.0,
                               z: float = 0.0) -> bytes:
    """Binary-proven full constructor snapshot for MovementAttr.

    v35 correction: MovementAttr constructor/reset at 0x467030 sets object+0x4C
    to 0xFF, while serializer 0x4671C0 emits the seven known fields selected
    by bits 0x01..0x40.  v33/v34 used mask=0, which created the object but
    transmitted none of its movement state. V113 keeps mask=0xFF and every
    constructor-default field except the already-proven position vector.
    """
    f0 = bytes([0x2A]) + struct.pack("<f", 0.0)
    return (
        u8tag(0x0B, 1)
        + bytes([0x32]) + struct.pack("<II", identity_lo & 0xFFFFFFFF, identity_hi & 0xFFFFFFFF)
        + u8tag(0x0B, 0xFF)
        + f32tag(x) + f32tag(y) + f32tag(z)  # +0x28/+0x2C/+0x30 vector3
        + f0                    # +0x34
        + u8tag(0x0B, 0)        # +0x38
        + u32tag(0x26, 0)       # +0x3C
        + f0 + f0 + f0          # +0x40/+0x44/+0x48
    )


def make_teleport_target(scene_id: int = 1, scene_seq: int = 0,
                         x: float = 0.0, y: float = 0.0,
                         z: float = 0.0) -> bytes:
    """Binary-proven Teleport target object (serializer 0x5DF250).

    Layout: u16 SceneID, qword SceneSeq, two u8 flags, vec3 position.
    Handler 0x5F14B0 rejects the packet unless SceneID > 0.
    """
    return (
        u16tag(0x12, scene_id & 0xFFFF)
        + bytes([0x32]) + struct.pack("<Q", scene_seq & 0xFFFFFFFFFFFFFFFF)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 0)
        + f32tag(x) + f32tag(y) + f32tag(z)
    )


def make_login_teleport(scene_id: int = 1, scene_seq: int = 0,
                        x: float = 0.0, y: float = 0.0,
                        z: float = 0.0) -> tuple[bytes, bytes]:
    """TeleportVital v4 using only constructor/serializer-proven fields."""
    payload = (
        u8tag(0x0B, 2)
        + u8tag(0x0B, 1)
        + make_teleport_target(scene_id, scene_seq, x, y, z)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 0)
        + u16tag(0x0F, 0)
    )
    return make_login_vital(TELEPORT_VITAL, 4, payload)


def make_backpack_attr_empty() -> bytes:
    """Binary-proven constructor-default empty BackpackAttr wire.

    BackpackAttr constructor 0x46AC70 (size 0x98, vtable 0xF0EA88) calls the
    ItemBag-style base constructor 0x46F3F0, leaves both base containers empty,
    and initializes BackpackAttr+0x68 to zero. The exact serializer chain is:

      0x469FA0 BackpackAttr -> 0x46F180 container base -> 0x467790 Attr base

    Attr's constructor mask is 0xFF; serializer 0x467790 writes that byte and,
    because bit zero is set, the zero identity qword. Serializer 0x46F180 then
    writes two zero u16 collection counts. Serializer 0x469FA0 finally writes
    the constructor-default byte at +0x68. No ItemAttr objects are present.
    """
    return (
        u8tag(0x0B, 0xFF)
        + qwordtag(0x32, 0)
        + u16tag(0x0F, 0)
        + u16tag(0x0F, 0)
        + u8tag(0x0B, 0)
    )


V103_ITEM_SEQUENCE = 1
V103_ITEM_TEMPLATE = 2600001  # STORE_NORMAL row 1 -> ITEM_MISC row 1, Adventure Key
V103_ITEM_QUANTITY = 1
V103_ITEM_SLOT = 0
V110_CASK_SEQUENCE = 2
V110_CASK_TEMPLATE = 2400901  # STORE_NORMAL store 1 -> ITEM_CONSUMABLES row 901
V110_CASK_QUANTITY = 1
V110_CASK_SLOT = 1
V111_STACK_SOURCE_SEQUENCE = 3
V111_STACK_SOURCE_QUANTITY = 1
V111_STACK_SOURCE_SLOT = 2
V111_ADVENTURE_KEY_STACK_LIMIT = 25
V123_BLADE_SEQUENCE = 4
V123_BLADE_TEMPLATE = 2200002  # EQUIPMENT_BASE row 2, Create Character Blade
V123_BLADE_QUANTITY = 1
V123_BLADE_SLOT = 3
V123_EQUIP_FROM_BAG_OPERATION = 5  # producer 0x59F800 writes ItemOperateReq+0x14
V123_EQUIP_FROM_BAG_VALUE32 = (8, 16)  # 0x4000 row mask -> normal/alternate
V120_BACKPACK_BASE_RANGE_MASK = 0x01
V120_BACKPACK_BASE_SLOT_COUNT = 40
V120_SHOP_BUY_CELL_CAP = 18


def make_item_attr_adventure_key() -> bytes:
    """Serializer-exact basic ItemAttr with every unknown field at ctor default.

    ItemAttr serializer 0x46BD30 writes identity, global template, quantity,
    signed bag slot, two one-byte fields, and an optional-detail presence byte.
    The template is referenced by decoded STORE_NORMAL data; slot zero is the
    first client bag slot; sequence one is the server-owned first item identity.
    """
    return (
        qwordtag(0x32, V103_ITEM_SEQUENCE)
        + u32tag(0x14, V103_ITEM_TEMPLATE)
        + u16tag(0x0F, V103_ITEM_QUANTITY)
        + u16tag(0x0F, V103_ITEM_SLOT)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )


def make_item_attr_adventure_key_stack_source() -> bytes:
    """Second serializer-exact Adventure Key used by the stack-merge probe."""
    return (
        qwordtag(0x32, V111_STACK_SOURCE_SEQUENCE)
        + u32tag(0x14, V103_ITEM_TEMPLATE)
        + u16tag(0x0F, V111_STACK_SOURCE_QUANTITY)
        + u16tag(0x0F, V111_STACK_SOURCE_SLOT)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )


def make_item_attr_camouflage_cask() -> bytes:
    """Serializer-exact level-1 camouflage with constructor-default details.

    The global template is not inferred from a category prefix: decoded
    STORE_NORMAL store 1 explicitly contains 2400901, while the matching
    ITEM_CONSUMABLES and text rows prove its identity, level-1 condition, and
    visible transformation effect.
    """
    return (
        qwordtag(0x32, V110_CASK_SEQUENCE)
        + u32tag(0x14, V110_CASK_TEMPLATE)
        + u16tag(0x0F, V110_CASK_QUANTITY)
        + u16tag(0x0F, V110_CASK_SLOT)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )


def make_item_attr_create_character_blade() -> bytes:
    """Serializer-exact starter blade for the display/op5 capture lane.

    Decoded EQUIPMENT_BASE row 2 supplies global template 2200002, stack limit
    one, level-one/class-three conditions, and an empty VARYDATA field. The
    frozen real actor AvatarAttr independently carries 2200002 at +0x54 and
    +0x58. Identity four and slot three continue the established local initial
    snapshot policy after the three V111 identities; every ItemAttr-only field
    remains at its binary-proven constructor default. In particular +0x39 stays
    0xFF: V123 presents an unequipped bag item and does not invent an equipped
    slot assignment.
    """
    return (
        qwordtag(0x32, V123_BLADE_SEQUENCE)
        + u32tag(0x14, V123_BLADE_TEMPLATE)
        + u16tag(0x0F, V123_BLADE_QUANTITY)
        + u16tag(0x0F, V123_BLADE_SLOT)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )


def make_backpack_attr_three_items() -> bytes:
    """Three-item Backpack with only its proven base 40-slot range enabled.

    BackpackAttr serializer 0x469FA0 emits +0x68 as the final tagged byte.
    StartGame handler 0x5A2970 copies it to inventory-manager +0x30, where
    free-slot counter 0x5A19E0 uses bit 0 to traverse exactly the 40 base slots
    at global 0x102208C. Bits 1 and 2 would enable additional 40/80-slot ranges
    and remain clear because this test state has no evidence for them.
    """
    adventure_key = make_item_attr_adventure_key()
    cask = make_item_attr_camouflage_cask()
    stack_source = make_item_attr_adventure_key_stack_source()
    return (
        u8tag(0x0B, 0xFF)
        + qwordtag(0x32, 0)
        + u16tag(0x0F, 3)
        + adventure_key
        + cask
        + stack_source
        + u16tag(0x0F, 3)
        + qwordtag(0x32, V103_ITEM_SEQUENCE)
        + qwordtag(0x32, V110_CASK_SEQUENCE)
        + qwordtag(0x32, V111_STACK_SOURCE_SEQUENCE)
        + u8tag(0x0B, V120_BACKPACK_BASE_RANGE_MASK)
    )


def make_backpack_attr_four_items() -> bytes:
    """V123 full initial Backpack snapshot with one starter blade added.

    This is a complete StartGame-owned BackpackAttr, not an UpdateAttr delta:
    both collections contain identities 1-4, and the proven base-range mask
    remains one. Existing item wires are preserved byte-for-byte.
    """
    adventure_key = make_item_attr_adventure_key()
    cask = make_item_attr_camouflage_cask()
    stack_source = make_item_attr_adventure_key_stack_source()
    blade = make_item_attr_create_character_blade()
    return (
        u8tag(0x0B, 0xFF)
        + qwordtag(0x32, 0)
        + u16tag(0x0F, 4)
        + adventure_key
        + cask
        + stack_source
        + blade
        + u16tag(0x0F, 4)
        + qwordtag(0x32, V103_ITEM_SEQUENCE)
        + qwordtag(0x32, V110_CASK_SEQUENCE)
        + qwordtag(0x32, V111_STACK_SOURCE_SEQUENCE)
        + qwordtag(0x32, V123_BLADE_SEQUENCE)
        + u8tag(0x0B, V120_BACKPACK_BASE_RANGE_MASK)
    )


def make_item_bag_attr_adventure_key_move_delta(target_slot: int, quantity: int = V103_ITEM_QUANTITY) -> bytes:
    """ItemBagAttr delta with one updated item and no removal identities.

    ItemOperateVitalRes deserializer 0x5EDB56 allocates a fixed size-0x68
    ItemBagAttr through 0x46F4D0. Vtable 0xF0ECB8 selects serializer 0x46F180:
    Attr base, ItemAttr collection, then qword-identity collection. In response
    handler 0x5A8A00 the first collection reaches update calls 0x59FB40 and
    0x5A1240, while identities in the second collection reach removal call
    0x59FC50. V106 included identity 1 in both and visibly removed the item.
    V107 keeps the proven moved ItemAttr but makes only that removal collection
    empty; no unknown field changes.
    """
    if not 0 <= target_slot < 40:
        raise ValueError(f"bag slot out of range: {target_slot}")
    moved_item = (
        qwordtag(0x32, V103_ITEM_SEQUENCE)
        + u32tag(0x14, V103_ITEM_TEMPLATE)
        + u16tag(0x0F, quantity)
        + u16tag(0x0F, target_slot)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )
    return (
        u8tag(0x0B, 0xFF)
        + qwordtag(0x32, 0)
        + u16tag(0x0F, 1)
        + moved_item
        + u16tag(0x0F, 0)
    )


def make_item_operate_move_delta_success(target_slot: int, quantity: int = V103_ITEM_QUANTITY) -> tuple[bytes, bytes]:
    """ItemOperateVitalRes for proven operation-4 destination-slot requests.

    Response serializer 0x5EDA20 writes result byte, optional ItemBagAttr,
    then a byte-counted affected-identity list. Handler 0x5A8A00 proves result
    zero is the processing path. The list remains constructor-empty.
    """
    payload = (
        u8tag(0x08, 0)
        + u8tag(0x0B, 1)
        + make_item_bag_attr_adventure_key_move_delta(target_slot, quantity)
        + u8tag(0x08, 0)
    )
    # ItemOperateVitalRes constructor 0x5EBED0 overwrites VitalData +0x10
    # with constant 2 at 0x5EBF3E. V105's version 0 was rejected before body
    # deserialization with ErrorData=0x4C13; V106 proved version 2 is accepted.
    return make_runtime_vitals([(ITEM_OPERATE_RES_VITAL, 2, payload)])


def make_item_operate_stack_merge_success() -> tuple[bytes, bytes]:
    """Merge source identity 3 into Adventure Key identity 1.

    The first ItemBag collection updates the surviving target identity to
    quantity two. The second collection removes only the source identity.
    Handler 0x5A8A00 and the V106/V107 boundary prove these two collection
    roles independently; the affected-entry list remains empty as in V107.
    """
    merged_quantity = V103_ITEM_QUANTITY + V111_STACK_SOURCE_QUANTITY
    merged_item = (
        qwordtag(0x32, V103_ITEM_SEQUENCE)
        + u32tag(0x14, V103_ITEM_TEMPLATE)
        + u16tag(0x0F, merged_quantity)
        + u16tag(0x0F, V103_ITEM_SLOT)
        + u8tag(0x08, 0)
        + u8tag(0x08, 0xFF)
        + u8tag(0x0B, 0)
    )
    item_bag_delta = (
        u8tag(0x0B, 0xFF)
        + qwordtag(0x32, 0)
        + u16tag(0x0F, 1)
        + merged_item
        + u16tag(0x0F, 1)
        + qwordtag(0x32, V111_STACK_SOURCE_SEQUENCE)
    )
    payload = (
        u8tag(0x08, 0)
        + u8tag(0x0B, 1)
        + item_bag_delta
        + u8tag(0x08, 0)
    )
    return make_runtime_vitals([(ITEM_OPERATE_RES_VITAL, 2, payload)])


def make_login_start_game_res_actorattr(selector: int,
                                        player_x: float = 0.0,
                                        player_y: float = 0.0,
                                        player_z: float = 0.0) -> tuple[bytes, bytes]:
    """StartGameRes v3 with exactly one minimal ActorAttr collection entry.

    V29 proved the fixed StartGameRes header is accepted and begins the
    leave-character-select transition, but then the client emitted only
    heartbeats. Binary handler 0x5DDAE0 looks up four collection types:
      BackpackAttr 0x1F81 (optional branch)
      ActorAttr    0x12AD (required for actor-construction branch)
      AvatarAttr   0x16A0 (captured appearance snapshot)
      MovementAttr 0x2067 (nullable)

    The branch at 0x5DDC1F proceeds only when ActorAttr exists. It creates a
    local actor, copies ActorAttr's identity pair, attaches ActorAttr plus any
    optional Avatar/Movement attrs, and inserts the actor into the client-side
    manager. V30 therefore adds only ActorAttr; every other V29 field remains
    unchanged. Identity stays (0,0) to avoid changing CreateActor semantics in
    the same experiment.
    """
    actor_attr = make_actor_attr_minimal(0, 0, 1, 0)
    avatar_attr = make_avatar_attr_from_preset()
    movement_attr = make_movement_attr_minimal(
        0, 0, player_x, player_y, player_z
    )
    backpack_attr = make_backpack_attr_four_items()
    payload = (
        u8tag(0x08, selector)
        + u8tag(0x05, 0)
        + u8tag(0x0B, 2)
        + u16tag(0x0F, 3)
        + u16tag(0x0F, 0)
        + u8tag(0x0B, 4)
        + u16tag(0x12, 0x12AD)
        + actor_attr
        + u16tag(0x12, 0x16A0)
        + avatar_attr
        + u16tag(0x12, 0x2067)
        + movement_attr
        + u16tag(0x12, BACKPACK_ATTR)
        + backpack_attr
        + u8tag(0x0B, 0)
    )
    return make_login_vital(START_GAME_RES, 3, payload)



def make_world_info_object_minimal() -> bytes:
    """Binary-derived minimum object carried by GetWorldInfoVital.

    Proven from GameClient.local.bin:
      GetWorldInfoVital ctor 0x5E75C0, ID 0x3D4B, version 0, payload ptr +0x14.
      GetWorldInfoVital serializer 0x5EB800 writes 0B <has-object>, then calls
      nested serializer 0x5E06B0.

    Nested object constructor 0x5E1C40 (size 0x54) initializes:
      +0x10 = 0xFFFFFFFF
      +0x14 = empty std::wstring
      +0x34 = empty container; its count at +0x50 is zero

    Nested serializer 0x5E06B0 writes, in this exact order:
      14 <u32 +0x10>
      48 <UTF-16 string +0x14>
      0F <u16 container count +0x50>
      repeated nested records (none when count=0)
    """
    return (
        u32tag(0x14, 0xFFFFFFFF)
        + bytes([0x48]) + struct.pack('<I', 0)
        + u16tag(0x0F, 0)
    )


def make_login_get_world_info_minimal() -> tuple[bytes, bytes]:
    payload = u8tag(0x0B, 1) + make_world_info_object_minimal()
    return make_login_vital(GET_WORLD_INFO_VITAL, 0, payload)

def recv_exact(c: socket.socket, n: int):
    b = bytearray()
    while len(b) < n:
        q = c.recv(n - len(b))
        if not q:
            return None
        b += q
    return bytes(b)


def recv_frame(c: socket.socket):
    h = recv_exact(c, 8)
    if h is None:
        return None
    m, n = struct.unpack("<II", h)
    d = recv_exact(c, n)
    if d is None:
        return None
    return m, h + d, d


@dataclass
class ParsedOuter:
    outer_id: int
    outer_version: int
    outer_mask: int
    vital_count: int
    nested_id: int | None
    nested_version: int | None
    nested_payload: bytes
    nested_offset: int | None
    raw_pc: bytes


class Cursor:
    def __init__(self, data: bytes):
        self.data = data
        self.p = 0

    def remain(self) -> int:
        return len(self.data) - self.p

    def need(self, n: int) -> None:
        if self.p + n > len(self.data):
            raise ValueError(f"truncated at {self.p}, need {n}, len={len(self.data)}")

    def tag(self, wanted: int) -> None:
        self.need(1)
        got = self.data[self.p]
        if got != wanted:
            raise ValueError(f"tag mismatch at {self.p}: got 0x{got:02X}, want 0x{wanted:02X}")
        self.p += 1

    def u8(self, tag: int) -> int:
        self.tag(tag)
        self.need(1)
        v = self.data[self.p]
        self.p += 1
        return v

    def u16(self, tag: int) -> int:
        self.tag(tag)
        self.need(2)
        v = struct.unpack_from("<H", self.data, self.p)[0]
        self.p += 2
        return v

    def u32(self, tag: int) -> int:
        self.tag(tag)
        self.need(4)
        v = struct.unpack_from("<I", self.data, self.p)[0]
        self.p += 4
        return v

    def raw8(self, tag: int) -> bytes:
        self.tag(tag)
        self.need(8)
        b = self.data[self.p:self.p + 8]
        self.p += 8
        return b

    def f32(self, tag: int = 0x2A) -> float:
        self.tag(tag)
        self.need(4)
        v = struct.unpack_from("<f", self.data, self.p)[0]
        self.p += 4
        return v

    def astr(self, tag: int = 0x44) -> str:
        self.tag(tag)
        self.need(4)
        n = struct.unpack_from("<I", self.data, self.p)[0]
        self.p += 4
        self.need(n)
        b = self.data[self.p:self.p + n]
        self.p += n
        return b.decode("ascii", errors="replace")

    def wstr(self, tag: int = 0x48) -> str:
        self.tag(tag)
        self.need(4)
        n = struct.unpack_from("<I", self.data, self.p)[0]
        self.p += 4
        self.need(n)
        b = self.data[self.p:self.p + n]
        self.p += n
        return b.decode("utf-16le", errors="replace")


def parse_outer(pc: bytes) -> ParsedOuter:
    """Parse the common PcProtocol base + optional VitalData collection structurally.

    This deliberately does NOT scan for 0x12 xx xx byte patterns inside payloads.
    For all observed LSCN/GSCN login packets and GSCN RuntimeRes, outer mask bit
    0x02 denotes the VitalData collection.
    """
    c = Cursor(pc)
    outer_id = c.u16(0x12)
    _base_u32 = c.u32(0x14)
    outer_version = c.u8(0x08)
    outer_mask = c.u8(0x0B)

    vital_count = 0
    nested_id = None
    nested_version = None
    nested_payload = b""
    nested_offset = None

    if outer_mask & 0x02:
        vital_count = c.u16(0x12)
        if vital_count:
            # All client packets seen so far contain one nested vital. With more
            # than one, boundaries require each vital's serializer schema.
            nested_offset = c.p
            nested_id = c.u16(0x12)
            nested_version = c.u8(0x0B)
            nested_payload = pc[c.p:]
    return ParsedOuter(
        outer_id=outer_id,
        outer_version=outer_version,
        outer_mask=outer_mask,
        vital_count=vital_count,
        nested_id=nested_id,
        nested_version=nested_version,
        nested_payload=nested_payload,
        nested_offset=nested_offset,
        raw_pc=pc,
    )


def structural_ids(parsed: ParsedOuter):
    out = [(0, parsed.outer_id, NAMES.get(parsed.outer_id, f"0x{parsed.outer_id:04X}"))]
    if parsed.nested_id is not None:
        out.append((
            parsed.nested_offset if parsed.nested_offset is not None else -1,
            parsed.nested_id,
            NAMES.get(parsed.nested_id, f"0x{parsed.nested_id:04X}"),
        ))
    return out


def has_id(ids, wanted: int) -> bool:
    return any(v == wanted for _, v, _ in ids)


def parse_select_req(parsed: ParsedOuter):
    if parsed.nested_id != SELECT_SERVER_REQ:
        return None
    c = Cursor(parsed.nested_payload)
    return (c.u32(0x14), c.u32(0x14))


def parse_notify_enter_create_actor(parsed: ParsedOuter):
    if parsed.nested_id != NOTIFY_ENTER_CREATE_ACTOR:
        return None
    c = Cursor(parsed.nested_payload)
    return c.u8(0x05)


def parse_create_actor(parsed: ParsedOuter):
    if parsed.nested_id != CREATE_ACTOR_VITAL:
        return None
    c = Cursor(parsed.nested_payload)
    op = c.u8(0x08)
    has_actor = c.u8(0x0B)
    actor_wire = parsed.nested_payload[c.p:] if has_actor else b""
    return op, has_actor, actor_wire


def parse_start_game_req(parsed: ParsedOuter):
    if parsed.nested_id != START_GAME_REQ:
        return None
    c = Cursor(parsed.nested_payload)
    return c.u8(0x08)


def parse_target_pos_vital(parsed: ParsedOuter):
    """Decode client TargetPosVital v0 observed in Port Royal runtime traffic."""
    if parsed.nested_id != TARGET_POS_VITAL:
        return None
    c = Cursor(parsed.nested_payload)
    # nested_version (tag 0B) is already consumed by parse_outer().
    x = c.f32(0x2A)
    y = c.f32(0x2A)
    z = c.f32(0x2A)
    heading = c.f32(0x2A)
    moving = c.u8(0x0B) if c.remain() >= 2 else 0
    return x, y, z, heading, 0, moving


def parse_v141_refresh_target_pos(parsed: ParsedOuter):
    """Accept only the complete singleton TargetPos serializer shape for V141."""
    if not (
        parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
        parsed.outer_version==0 and parsed.outer_mask==0x02 and
        parsed.vital_count==1 and parsed.nested_id==TARGET_POS_VITAL and
        parsed.nested_version==0
    ):
        return None
    try:
        c=Cursor(parsed.nested_payload)
        x=c.f32(0x2A)
        y=c.f32(0x2A)
        z=c.f32(0x2A)
        heading=c.f32(0x2A)
        moving=c.u8(0x0B)
        derived_mask=c.u8(0x0B)
    except Exception:
        return None
    if c.remain()!=0 or derived_mask!=0:
        return None
    if not all(math.isfinite(value) for value in (x,y,z,heading)):
        return None
    return x,y,z,heading,0,moving


def parse_target_vital(parsed: ParsedOuter):
    """Decode only the V94 runtime-proven TargetVital prefix."""
    if parsed.nested_id != TARGET_VITAL:
        return None
    c=Cursor(parsed.nested_payload)
    actor_identity=struct.unpack('<Q',c.raw8(0x32))[0]
    target_kind=c.u8(0x08)
    return actor_identity,target_kind


def parse_choose_npc(parsed: ParsedOuter):
    """Decode the complete binary-proven ChooseNPC v0 payload.

    Serializer 0x6C0180 writes exactly tag 0x32 plus qword actor identity from
    object offset +0x18. V74, V90, and V96 runtime captures match that schema.
    """
    if parsed.nested_id != CHOOSE_NPC:
        return None
    c = Cursor(parsed.nested_payload)
    return struct.unpack('<Q', c.raw8(0x32))[0]


def extract_choose_npc_identities(parsed: ParsedOuter) -> list[int]:
    """Return ChooseNPC identities at proven VitalData boundaries.

    Runtime packets can contain TargetVital followed by one or more ChooseNPC
    records. This parser advances only through the two complete schemas proved
    by V94/V96 captures and stops at any other vital; it does not scan arbitrary
    payload bytes for an ID-like pattern.
    """
    if parsed.nested_id not in (TARGET_VITAL, CHOOSE_NPC):
        return []
    c=Cursor(parsed.nested_payload)
    current_id=parsed.nested_id
    found=[]
    for ordinal in range(parsed.vital_count):
        if current_id==TARGET_VITAL:
            c.raw8(0x32)
            c.u8(0x08)
        elif current_id==CHOOSE_NPC:
            found.append(struct.unpack('<Q',c.raw8(0x32))[0])
        else:
            break
        if ordinal+1>=parsed.vital_count or c.remain()<4:
            break
        current_id=c.u16(0x12)
        c.u8(0x0B)
    return found


def parse_v139_p86_interaction_shape(parsed: ParsedOuter):
    """Walk only the complete P86 interaction shapes observed by V97.

    Accepted order is TargetVital(P86,kind2), one or two ChooseNPC(P86), then
    optionally one fixed-schema TargetPosVital. All nested versions are zero,
    the outer envelope is RuntimeReq v0/mask2, every declared vital is consumed,
    and no unparsed tail is tolerated. This intentionally rejects Target-only,
    Choose-only, mixed-identity, unknown-tail, and count-outside-shape packets.
    """
    if not (
        parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
        parsed.outer_version==0 and
        parsed.outer_mask==2 and
        parsed.nested_id==TARGET_VITAL and
        parsed.nested_version==0 and
        2<=parsed.vital_count<=4
    ):
        return None
    try:
        c=Cursor(parsed.nested_payload)
        target_identity=struct.unpack('<Q',c.raw8(0x32))[0]
        target_kind=c.u8(0x08)
        if target_identity!=V139_P86_ACTOR_ID or target_kind!=2:
            return None
        choose_count=0
        trailing_target_pos=None
        for ordinal in range(1,parsed.vital_count):
            nested_id=c.u16(0x12)
            nested_version=c.u8(0x0B)
            if nested_version!=0:
                return None
            if nested_id==CHOOSE_NPC and trailing_target_pos is None:
                choose_identity=struct.unpack('<Q',c.raw8(0x32))[0]
                if choose_identity!=V139_P86_ACTOR_ID:
                    return None
                choose_count+=1
                if choose_count>2:
                    return None
            elif nested_id==TARGET_POS_VITAL and ordinal==parsed.vital_count-1:
                x=c.f32(0x2A)
                y=c.f32(0x2A)
                z=c.f32(0x2A)
                heading=c.f32(0x2A)
                moving=c.u8(0x0B)
                final_byte=c.u8(0x0B)
                if not all(math.isfinite(value) for value in (x,y,z,heading)):
                    return None
                trailing_target_pos=(x,y,z,heading,moving,final_byte)
            else:
                return None
        if choose_count not in (1,2) or c.remain()!=0:
            return None
        return choose_count,trailing_target_pos
    except (ValueError,struct.error):
        return None


CAPTURE_NOISE_IDS={TARGET_POS_VITAL,ON_LAND_VITAL,UPDATE_SERVER_SETTING_VITAL}


def parse_item_operate_req(parsed:ParsedOuter) -> tuple[int,int,int]:
    """Decode the binary-proven ItemOperateVitalReq serializer exactly.

    Serializer 0x5E5AF0 writes one byte, one dword, and one qword using tags
    0x0B, 0x14, and 0x32 respectively. Semantic names beyond the operation
    byte and opaque values remain deliberately unassigned in this capture
    checkpoint.
    """
    if parsed.nested_id!=ITEM_OPERATE_REQ_VITAL:
        raise ValueError(f'not ItemOperateVitalReq: {parsed.nested_id!r}')
    c=Cursor(parsed.nested_payload)
    operation=c.u8(0x0B)
    value32=c.u32(0x14)
    item_identity=struct.unpack('<Q',c.raw8(0x32))[0]
    if c.remain()!=0:
        raise ValueError(f'ItemOperateVitalReq trailing={c.remain()}')
    return operation,value32,item_identity


def parse_trade_cmd_vital(parsed:ParsedOuter) -> dict:
    """Decode only the statically proven TradeCmdVital serializer shape.

    Serializer 0x699910 writes u8/tag08, u32/tag19, a presence byte/tag08,
    then optionally the fixed 0x74CF90 record qword/tag32, dword/tag14,
    u16/tag0F. Field semantics remain deliberately neutral until runtime.
    """
    if parsed.nested_id!=TRADE_CMD_VITAL:
        raise ValueError(f'not TradeCmdVital: {parsed.nested_id!r}')
    c=Cursor(parsed.nested_payload)
    result={
        'field_u8':c.u8(0x08),
        'field_u32':c.u32(0x19),
        'has_detail':c.u8(0x08),
    }
    if result['has_detail']:
        result.update({
            'detail_identity':struct.unpack('<Q',c.raw8(0x32))[0],
            'detail_template':c.u32(0x14),
            'detail_quantity':c.u16(0x0F),
        })
    if c.remain()!=0:
        raise ValueError(f'TradeCmdVital trailing={c.remain()}')
    return result


def parse_quest_operate_vital(parsed:ParsedOuter) -> dict:
    """Decode the complete QuestOperateVital serializer at 0x621860.

    Names are kept offset-based except for the proven quest ID. The client
    request producer at 0x617800 writes its operation byte to +0x16 and its
    dword to +0x18; the server offer uses the UI action selector at +0x17.
    """
    if parsed.nested_id!=QUEST_OPERATE_VITAL:
        raise ValueError(f'not QuestOperateVital: {parsed.nested_id!r}')
    c=Cursor(parsed.nested_payload)
    result={
        'quest_id':c.u16(0x12),
        'field_u8_16':c.u8(0x08),
        'field_u8_17':c.u8(0x08),
        'field_u32_18':c.u32(0x14),
        'field_qword_20':struct.unpack('<Q',c.raw8(0x32))[0],
        'field_u8_28':c.u8(0x05),
    }
    if c.remain()!=0:
        raise ValueError(f'QuestOperateVital trailing={c.remain()}')
    return result


def parse_teleport_check_vital(parsed:ParsedOuter) -> dict:
    """Decode only the statically exact TeleportCheckVital v0 body.

    Pooled constructor/reset 0x44B980 zeros word +0x14, and serializer
    0x5E6670 writes exactly tag 0x0F plus that u16. The field remains named by
    offset because no captured request yet proves its runtime meaning. A
    singleton must end after the three-byte body; a multi-vital request must
    begin the following VitalData at the exact structural boundary.
    """
    if parsed.nested_id!=TELEPORT_CHECK_VITAL:
        raise ValueError(f'not TeleportCheckVital: {parsed.nested_id!r}')
    if parsed.nested_version!=0:
        raise ValueError(
            f'TeleportCheckVital nested version must be 0: {parsed.nested_version!r}'
        )
    c=Cursor(parsed.nested_payload)
    result={'field_u16_14':c.u16(0x0F)}
    if not first_vital_collection_shape_exact(parsed,c.p):
        raise ValueError(
            f'TeleportCheckVital collection boundary invalid '
            f'count={parsed.vital_count} trailing={c.remain()}'
        )
    result['consumed_bytes']=c.p
    result['trailing_bytes']=c.remain()
    return result


def first_vital_collection_shape_exact(parsed:ParsedOuter,consumed_bytes:int) -> bool:
    """Validate the boundary after a fixed-size first VitalData body.

    ``parse_outer`` intentionally exposes the rest of a multi-vital collection
    as one byte string because arbitrary VitalData bodies are not self-sized.
    TargetVital and ActionVital both have statically fixed serializers, so their
    first-body boundary is known. A singleton must end exactly there; a larger
    collection must begin its next nested vital with the proven ID/version tags.
    The following vital is left opaque and is never used to authorize a reply.
    """
    if consumed_bytes<0 or consumed_bytes>len(parsed.nested_payload):
        return False
    trailing=parsed.nested_payload[consumed_bytes:]
    if parsed.vital_count==1:
        return len(trailing)==0
    if parsed.vital_count>1:
        return (
            len(trailing)>=5 and
            trailing[0]==0x12 and
            trailing[3]==0x0B
        )
    return False


def parse_action_vital(parsed:ParsedOuter) -> dict:
    """Decode the exact fixed 64-byte ActionVital serializer at 0x74E6A0.

    Offset-based names deliberately preserve the RE boundary. The four floats
    are current heading and XYZ in the audited WIELD/Z producer, while +0x48
    and +0x4A remain opaque native-width values. A multi-vital RuntimeReq is allowed
    only when the byte immediately after this fixed body is another tagged
    VitalData header; later vitals are not interpreted here.
    """
    if parsed.nested_id!=ACTION_VITAL:
        raise ValueError(f'not ActionVital: {parsed.nested_id!r}')
    c=Cursor(parsed.nested_payload)
    result={
        'field_qword_18':struct.unpack('<Q',c.raw8(0x32))[0],
        'field_qword_20':struct.unpack('<Q',c.raw8(0x32))[0],
        'field_qword_28':struct.unpack('<Q',c.raw8(0x32))[0],
        'action_u32_30':c.u32(0x14),
        'field_u32_34':c.u32(0x19),
        'heading_f32_38':c.f32(0x2A),
        'x_f32_3c':c.f32(0x2A),
        'y_f32_40':c.f32(0x2A),
        'z_f32_44':c.f32(0x2A),
        'field_u8_48':c.u8(0x0B),
        'field_u16_4a':c.u16(0x12),
        'field_u8_4c':c.u8(0x0B),
    }
    if c.p!=V126_ACTION_VITAL_BODY_BYTES:
        raise ValueError(f'ActionVital consumed={c.p}')
    if not first_vital_collection_shape_exact(parsed,c.p):
        raise ValueError(
            f'ActionVital collection boundary invalid count={parsed.vital_count} '
            f'trailing={c.remain()}'
        )
    result['consumed_bytes']=c.p
    result['trailing_bytes']=c.remain()
    return result


def describe_capture_event(parsed:ParsedOuter,state) -> str|None:
    """Describe a significant inbound event without assigning unknown fields."""
    if parsed.outer_id!=GSCN_RUNTIME_PROTOCOL_REQ or parsed.nested_id is None:
        return None
    post_action1=bool(getattr(state,'quest3020_accept_success_sent',False))
    if parsed.nested_id in CAPTURE_NOISE_IDS and not post_action1:
        return None
    name=NAMES.get(parsed.nested_id,f'UNKNOWN_0x{parsed.nested_id:04X}')
    detail=''
    if parsed.nested_id==TARGET_VITAL:
        try:
            actor_identity,target_kind=parse_target_vital(parsed)
            if actor_identity==0:
                detail=f' target=clear kind={target_kind}'
            else:
                idx=actor_identity-0x2000-1
                rows={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
                row=rows.get(idx)
                current=(
                    state.population_indices is not None and
                    idx in state.population_indices
                )
                if row is None:
                    detail=(f' actor_id=0x{actor_identity:016X} placement=unknown'
                            f' current_member={int(current)} kind={target_kind}')
                else:
                    detail=(f' actor_id=0x{actor_identity:016X} placement=P{idx}'
                            f' data_name={row[6]!r} template={row[1]}'
                            f' current_member={int(current)} kind={target_kind}')
            embedded_choose=extract_choose_npc_identities(parsed)
            if embedded_choose:
                detail+=(' embedded_choose='+
                         ','.join(f'0x{x:016X}' for x in embedded_choose))
        except Exception as e:
            detail=f' target_decode_error={e!r}'
    elif parsed.nested_id==CHOOSE_NPC:
        try:
            actor_identity=parse_choose_npc(parsed)
            idx=actor_identity-0x2000-1
            rows={r[0]:r for r in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
            row=rows.get(idx)
            current=(
                state.population_indices is not None and
                idx in state.population_indices
            )
            if row is None:
                detail=(f' actor_id=0x{actor_identity:016X} placement=unknown'
                        f' current_member={int(current)}')
            else:
                detail=(f' actor_id=0x{actor_identity:016X} placement=P{idx}'
                        f' data_name={row[6]!r} template={row[1]}'
                        f' current_member={int(current)}')
        except Exception as e:
            detail=f' choose_decode_error={e!r}'
    elif parsed.nested_id==ACTION_VITAL:
        try:
            action=parse_action_vital(parsed)
            detail=(
                f" qword_18=0x{action['field_qword_18']:016X}"
                f" qword_20=0x{action['field_qword_20']:016X}"
                f" qword_28=0x{action['field_qword_28']:016X}"
                f" action_30=0x{action['action_u32_30']:08X}"
                f" u32_34={action['field_u32_34']}"
                f" heading_38={action['heading_f32_38']:.6g}"
                f" xyz_3c44=({action['x_f32_3c']:.6g},"
                f"{action['y_f32_40']:.6g},{action['z_f32_44']:.6g})"
                f" opaque_u8_48={action['field_u8_48']}"
                f" opaque_u16_4a={action['field_u16_4a']}"
                f" u8_4c={action['field_u8_4c']}"
                f" body_bytes={action['consumed_bytes']}"
                f" trailing_bytes={action['trailing_bytes']}"
                f" p30_target_armed={int(state.p30_action_target_armed)}"
            )
        except Exception as e:
            detail=f' action_vital_decode_error={e!r}'
    elif parsed.nested_id==ITEM_OPERATE_REQ_VITAL:
        try:
            operation,value32,item_identity=parse_item_operate_req(parsed)
            if operation==V123_EQUIP_FROM_BAG_OPERATION:
                detail=(f' operation={operation}'
                        f' value32_mapped={value32}'
                        f' item_identity=0x{item_identity:016X}')
            else:
                detail=(f' operation={operation} value32={value32}'
                        f' item_identity=0x{item_identity:016X}')
        except Exception as e:
            detail=f' item_operate_decode_error={e!r}'
    elif parsed.nested_id==TRADE_CMD_VITAL:
        try:
            trade=parse_trade_cmd_vital(parsed)
            detail=(
                f" field_u8={trade['field_u8']}"
                f" field_u32={trade['field_u32']}"
                f" has_detail={trade['has_detail']}"
            )
            if trade['has_detail']:
                detail+=(
                    f" detail_identity=0x{trade['detail_identity']:016X}"
                    f" detail_template={trade['detail_template']}"
                    f" detail_quantity={trade['detail_quantity']}"
                )
        except Exception as e:
            detail=f' trade_cmd_decode_error={e!r}'
    elif parsed.nested_id==QUEST_OPERATE_VITAL:
        try:
            quest=parse_quest_operate_vital(parsed)
            detail=(
                f" quest_id={quest['quest_id']}"
                f" field_u8_16={quest['field_u8_16']}"
                f" field_u8_17={quest['field_u8_17']}"
                f" field_u32_18={quest['field_u32_18']}"
                f" field_qword_20=0x{quest['field_qword_20']:016X}"
                f" field_u8_28={quest['field_u8_28']}"
            )
        except Exception as e:
            detail=f' quest_operate_decode_error={e!r}'
    elif parsed.nested_id==TELEPORT_CHECK_VITAL:
        try:
            teleport_check=parse_teleport_check_vital(parsed)
            detail=(
                f" field_u16_14={teleport_check['field_u16_14']}"
                f" body_bytes={teleport_check['consumed_bytes']}"
                f" trailing_bytes={teleport_check['trailing_bytes']}"
                " semantics=unassigned no_response=1"
            )
        except Exception as e:
            detail=f' teleport_check_decode_error={e!r} no_response=1'
    return (
        f'name={name} id=0x{parsed.nested_id:04X}'
        f' version={parsed.nested_version} vital_count={parsed.vital_count}'
        f' post_action1={int(post_action1)}'
        f' payload_bytes={len(parsed.nested_payload)}{detail}'
        f' payload_hex={parsed.nested_payload.hex().upper()}'
    )


def decode_create_actor_data_ex(actor_wire: bytes) -> dict:
    """Decode the captured CreateActorDataEx schema recovered from serializer 0x5DFF60.

    The nested polymorphic +0xF0 branch is intentionally unsupported here because
    the real v25 creation submit had it absent. This validator is used to make
    sure the actor blob is structurally complete before echoing it.
    """
    c = Cursor(actor_wire)
    ident = c.raw8(0x32)
    id_lo, id_hi = struct.unpack("<II", ident)
    selector = c.u8(0x0B)
    name = c.wstr()
    appearance1 = c.u8(0x0B)
    appearance2 = c.u8(0x0B)
    create_context = c.u32(0x19)
    field20 = c.u16(0x12)
    field22 = c.u16(0x12)
    token_ascii = c.astr()
    second_name = c.wstr()

    avatar_base_flags = c.u8(0x0B)
    avatar_base_id = None
    if avatar_base_flags & 0x01:
        avatar_base_id = struct.unpack("<Q", c.raw8(0x32))[0]

    avatar_mask = c.u32(0x26)
    avatar_u32 = {}
    for bit, off in enumerate(range(0x2C, 0x5C, 4)):
        if avatar_mask & (1 << bit):
            avatar_u32[off] = c.u32(0x14)

    avatar_misc = {}
    if avatar_mask & (1 << 12):
        avatar_misc[0x5C] = c.u8(0x0B)
    if avatar_mask & (1 << 13):
        avatar_misc[0x5D] = c.u8(0x08)
    if avatar_mask & (1 << 14):
        avatar_misc[0x5E] = c.u8(0x08)
    if avatar_mask & (1 << 15):
        avatar_misc[0x64] = c.astr()
    if avatar_mask & (1 << 16):
        avatar_misc[0x60] = c.u8(0x0B)
    if avatar_mask & (1 << 17):
        avatar_misc[0x80] = c.u32(0x14)
    if avatar_mask & (1 << 18):
        avatar_misc[0x5F] = c.u8(0x0B)
    if avatar_mask & (1 << 19):
        avatar_misc[0x84] = c.u8(0x0B)
    if avatar_mask & (1 << 20):
        avatar_misc[0x88] = c.u32(0x14)

    nested_present = c.u8(0x0B)
    if nested_present:
        raise ValueError("CreateActorDataEx +0xF0 nested polymorphic object present; schema not implemented")
    f4 = c.u32(0x14)
    f8 = c.u32(0x14)
    if c.remain() != 0:
        raise ValueError(f"CreateActorDataEx trailing bytes: {c.remain()} at offset {c.p}")

    return {
        "identity_lo": id_lo,
        "identity_hi": id_hi,
        "selector": selector,
        "name": name,
        "appearance1": appearance1,
        "appearance2": appearance2,
        "create_context": create_context,
        "field20": field20,
        "field22": field22,
        "token_ascii": token_ascii,
        "second_name": second_name,
        "avatar_base_flags": avatar_base_flags,
        "avatar_base_id": avatar_base_id,
        "avatar_mask": avatar_mask,
        "avatar_u32": avatar_u32,
        "avatar_misc": avatar_misc,
        "nested_present": nested_present,
        "f4": f4,
        "f8": f8,
        "wire_len": len(actor_wire),
    }


@dataclass
class GameSessionState:
    token: str
    login_ack_sent: bool = False
    select_actor_sent: bool = False
    notify_count: int = 0
    last_notify_value: int | None = None
    create_actor_seen: bool = False
    create_actor_reply_sent: bool = False
    start_game_seen: bool = False
    start_game_reply_sent: bool = False
    world_info_sent: bool = False
    teleport_sent: bool = False
    runtime_ack_sent: bool = False
    welcome_message_sent: bool = False
    current_scene_music_sent: bool = False
    item_move_count: int = 0
    item_slot: int = V103_ITEM_SLOT
    item_quantity: int = V103_ITEM_QUANTITY
    probe_item_slot: int = V110_CASK_SLOT
    stack_source_slot: int = V111_STACK_SOURCE_SLOT
    stack_source_present: bool = True
    stack_merge_count: int = 0
    equipment_capture_count: int = 0
    equipment_last_value32_mapped: int | None = None
    equipment_last_item_identity: int | None = None
    current_cash: int = V116_INITIAL_CASH
    shop_store5_open_sent: bool = False
    quest3020_conversation_sent: bool = False
    quest3020_op1_capture_count: int = 0
    quest3020_accept_ui_sent: bool = False
    quest3020_op2_capture_count: int = 0
    quest3020_accept_success_sent: bool = False
    quest_operate_capture_count: int = 0
    quest_operate_last_fields: tuple[int, int, int, int, int, int] | None = None
    teleport_check_challenge_sent: bool = False
    teleport_check_echo_capture_count: int = 0
    teleport_check_echo_last_value: int | None = None
    v136_docking_composition_pending: bool = False
    v136_marker1_prompt_sent: bool = False
    v136_marker1_confirm_capture_count: int = 0
    v136_marker1_confirm_last_value: int | None = None
    v137_marker1_transport_sent: bool = False
    v137_marker1_transport_send_count: int = 0
    v138_marker1_ready_capture_count: int = 0
    v138_marker1_population_sent: bool = False
    v138_marker1_population_send_count: int = 0
    v139_marker_targetpos_capture_count: int = 0
    v139_p86_interaction_armed: bool = False
    v139_p86_choose_capture_count: int = 0
    v139_p86_face_sent: bool = False
    v139_p86_conversation_sent: bool = False
    v141_population_refresh_count: int = 0
    post_action1_request_count: int = 0
    post_action1_last_request: tuple[int, int | None, int, str] | None = None
    p30_action_target_armed: bool = False
    action_target_last_identity: int | None = None
    action_target_last_kind: int | None = None
    action_vital_capture_count: int = 0
    action_vital_last_fields: dict | None = None
    trade_cart_ack_count: int = 0
    trade_cart_last_ack_detail: tuple[int, int, int] | None = None
    trade_final_buy_capture_count: int = 0
    trade_final_buy_last_cart_ack_count: int = 0
    trade_store_close_capture_count: int = 0
    npc_appear_sweep_sent: bool = False
    npc_spawn_sent: bool = False
    npc_idle_action_sent: bool = False
    rx_frames: int = 0
    events: list[str] = field(default_factory=list)
    last_actor_summary: dict | None = None
    last_target_pos: tuple[float, float, float, float] | None = None
    population_indices: tuple[int, ...] | None = None
    population_refresh_anchor: tuple[float, float, float] | None = None

    def dispatch(self, parsed: ParsedOuter) -> list[tuple[str, bytes, bytes, float]]:
        """Return outbound actions as (label, pc, frame, delay_before).

        v30 dispatch is keyed by structurally parsed nested VitalData ID + state.
        Outer GSCN_LoginProtocol alone never triggers a login replay.
        """
        self.rx_frames += 1
        outbound = []
        nested_id = parsed.nested_id

        if nested_id == LOGIN_VERIFY_VITAL:
            if not self.login_ack_sent:
                ack_pc, ack_frame = make_game_login_ack(self.token)
                outbound.append(("LOGIN_VERIFY_ACK_ONCE", ack_pc, ack_frame, 0.0))
                self.login_ack_sent = True
                self.events.append("login_verify_seen")
            else:
                self.events.append("duplicate_login_verify_suppressed")

            if not self.select_actor_sent:
                sel_pc, sel_frame = make_runtime_select_actor_preset()
                outbound.append(("SELECT_ACTOR_PRESET_ONE_ONCE", sel_pc, sel_frame, 0.35))
                self.select_actor_sent = True
                self.events.append("select_actor_sent")

        elif nested_id == NOTIFY_ENTER_CREATE_ACTOR:
            value = parse_notify_enter_create_actor(parsed)
            self.notify_count += 1
            self.last_notify_value = value
            if value == 0:
                self.events.append("character_select_ready_notify0")
            elif value == 1:
                self.events.append("character_create_notify1")
            else:
                self.events.append(f"notify_unparsed_{value!r}")
            # Client -> server notification. Deliberately no reply.

        elif nested_id == CREATE_ACTOR_VITAL:
            self.create_actor_seen = True
            parsed_create = parse_create_actor(parsed)
            if parsed_create is None:
                self.events.append("create_actor_unparsed")
            else:
                op, has_actor, actor_wire = parsed_create
                self.events.append(f"create_actor_op{op}_has{has_actor}")
                if has_actor:
                    try:
                        self.last_actor_summary = decode_create_actor_data_ex(actor_wire)
                    except Exception as e:
                        self.last_actor_summary = {"decode_error": repr(e), "wire_len": len(actor_wire)}

                # Binary-proven create success/update path: inbound CreateActorVital
                # status/op=1 + actor object. Send ONCE and only for the normal
                # creation submit captured in v25.
                if (
                    op == 1
                    and has_actor == 1
                    and actor_wire
                    and not self.create_actor_reply_sent
                    and self.last_actor_summary is not None
                    and "decode_error" not in self.last_actor_summary
                ):
                    out_pc, out_frame = make_runtime_create_actor_success(actor_wire)
                    outbound.append(("CREATE_ACTOR_LOGIN_ECHO_ONCE", out_pc, out_frame, 0.10))
                    self.create_actor_reply_sent = True
                    self.events.append("create_actor_success_echo_sent")
                elif self.create_actor_reply_sent:
                    self.events.append("duplicate_create_actor_suppressed")

        elif nested_id == START_GAME_REQ:
            self.start_game_seen = True
            value = parse_start_game_req(parsed)
            self.events.append(f"start_game_req_selector_{value!r}")
            # v30: one ActorAttr bootstrap StartGameRes experiment.  The nested wire
            # is constructor/serializer-derived; only +0x14 echoes the proven
            # selected-actor byte.  Keep the already-proven LoginProtocol outer
            # used by this state family and do not fabricate world objects.
            if value is not None and not self.start_game_reply_sent:
                out_pc, out_frame = make_login_start_game_res_actorattr(
                    value,V135_PLAYER_X,V135_PLAYER_Y,V135_PLAYER_Z
                )
                outbound.append(("START_GAME_RES_ACTORATTR_ONCE", out_pc, out_frame, 0.10))
                self.start_game_reply_sent = True
                self.events.append("start_game_res_scene_identity_sent")

                # V36: static analysis now proves BasicAttr+0x5C/+0x60 are copied
                # into TeleportVital target SceneID/SceneSeq. Send one structurally
                # valid TeleportVital v4 after StartGameRes, using the same scene
                # identity. SceneID=1 is the only experimental semantic value; every
                # envelope/version/field order is binary-proven.
                if not self.teleport_sent:
                    tp_pc, tp_frame = make_login_teleport(1,0)
                    outbound.append(("V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE", tp_pc, tp_frame, 0.70))
                    self.teleport_sent = True
                    self.events.append(
                        "v135_startgame_movement_p0_minus100x_minus50y_teleport_zero_sent"
                    )

        elif parsed.outer_id == GSCN_RUNTIME_PROTOCOL_REQ and self.teleport_sent:
            # V36 runtime evidence: immediately after entering Port Royal the client
            # sends GSCN_RunTimeProtocolReq (0x6E6F), count=2, carrying a TeleportVital
            # confirmation plus TargetPosVital.  The client then raises its yellow
            # "no Server data" watchdog because v36 sends nothing thereafter.
            # A constructor-exact empty RuntimeRes is the smallest binary-proven
            # server packet in this protocol family.  ACK the first runtime request
            # immediately; the heartbeat worker then keeps the receive watchdog fed.
            if self.quest3020_accept_success_sent and nested_id is not None:
                self.post_action1_request_count+=1
                self.post_action1_last_request=(
                    nested_id,parsed.nested_version,parsed.vital_count,
                    parsed.nested_payload.hex().upper(),
                )
                self.events.append(
                    'v129_post_action1_runtime_request_observed_'
                    f'id0x{nested_id:04X}_version{parsed.nested_version}_'
                    f'count{parsed.vital_count}_payload_'
                    f'{parsed.nested_payload.hex().upper()}'
                )

            exact_empty_runtime_req=(
                parsed.raw_pc==V136_EMPTY_RUNTIME_REQ_PC and
                parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
                parsed.outer_version==0 and
                parsed.outer_mask==0 and
                parsed.vital_count==0 and
                parsed.nested_id is None and
                parsed.nested_version is None and
                parsed.nested_payload==b''
            )
            if (
                self.v136_docking_composition_pending and
                not self.v136_marker1_prompt_sent and
                exact_empty_runtime_req
            ):
                prompt_pc,prompt_frame=make_teleport_check_scene1_challenge()
                self.v136_docking_composition_pending=False
                self.v136_marker1_prompt_sent=True
                outbound.append((
                    'V136_COMPOSITIONAL_Q3020_VAR2_1_MARKER1_DOCKING_PROMPT_ONCE',
                    prompt_pc,prompt_frame,0.0,
                ))
                self.events.append(
                    'v136_compositional_server_hypothesis_q3020_var2_1_'
                    'next_exact_empty_runtime_req_marker1_prompt_sent_once_'
                    'no_travel_vehicle_completion_claim'
                )

            exact_v138_marker1_ready=(
                parsed.raw_pc==V138_MARKER1_READY_PC
            )
            if (
                exact_v138_marker1_ready and
                self.v137_marker1_transport_sent and
                not self.v138_marker1_population_sent
            ):
                population_pc,population_frame,population_rows=(
                    make_v140_marker1_population_state()
                )
                # Commit one-shot/current-world state before queueing the
                # authoritative snapshot so replay/re-entry cannot duplicate it.
                self.v138_marker1_ready_capture_count+=1
                self.v138_marker1_population_sent=True
                self.v138_marker1_population_send_count+=1
                self.population_indices=tuple(
                    row[0] for row in population_rows
                )
                self.population_refresh_anchor=(
                    V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
                )
                outbound.append((
                    'V140_MARKER1_READY_NEAREST20_P86_OPERATIONAL_'
                    'HARNESS_REAPPLY_ONCE',
                    population_pc,population_frame,0.0,
                ))
                self.events.append(
                    'v140_exact_76b_marker1_ready_after_v137_transport_'
                    'nearest20_p86_operational_harness_population_sent_once_'
                    'no_delayed_reapply_message_music_ack_startgame_teleport'
                )
            elif exact_v138_marker1_ready:
                self.events.append(
                    'v138_exact_marker1_ready_wrong_sequence_or_replay_no_send_'
                    f'v137_transport_{int(self.v137_marker1_transport_sent)}_'
                    f'population_sent_{int(self.v138_marker1_population_sent)}'
                )

            if not self.runtime_ack_sent:
                hb_pc, hb_frame = make_runtime_res_empty_exact()
                outbound.append(("RUNTIME_RES_ACK_FIRST_REQ", hb_pc, hb_frame, 0.0))
                self.runtime_ack_sent = True
                self.events.append("runtime_req_first_ack")

            if self.runtime_ack_sent and not self.welcome_message_sent:
                msg_pc, msg_frame = make_show_message(
                    "Pirate Force local server online"
                )
                outbound.append(("V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE", msg_pc, msg_frame, 0.0))
                self.welcome_message_sent = True
                self.events.append("v99_show_message_local_server_online")

            if self.runtime_ack_sent and not self.current_scene_music_sent:
                music_pc, music_frame = make_music_control_current_scene()
                outbound.append(("V100_MUSIC_CONTROL_CURRENT_SCENE", music_pc, music_frame, 0.0))
                self.current_scene_music_sent = True
                self.events.append("v100_music_control_current_scene")

            if nested_id==TARGET_VITAL:
                try:
                    actor_identity,target_kind=parse_target_vital(parsed)
                except Exception as e:
                    self.p30_action_target_armed=False
                    self.action_target_last_identity=None
                    self.action_target_last_kind=None
                    self.events.append(
                        f'v126_target_arm_parse_error_disarmed_{e!r}'
                    )
                else:
                    self.action_target_last_identity=actor_identity
                    self.action_target_last_kind=target_kind
                    exact_p30_target=(
                        parsed.outer_version==0 and
                        parsed.outer_mask==0x02 and
                        parsed.nested_version==0 and
                        first_vital_collection_shape_exact(parsed,11) and
                        actor_identity==V126_ACTION_TARGET_ACTOR_ID and
                        target_kind==V126_ACTION_TARGET_KIND and
                        self.population_indices is not None and
                        V112_MONSTER_INDEX in self.population_indices
                    )
                    self.p30_action_target_armed=exact_p30_target
                    self.events.append(
                        'v126_target_arm_capture_only_'
                        f'identity_0x{actor_identity:016X}_kind_{target_kind}_'
                        f'exact_p30_v0_{int(exact_p30_target)}'
                    )

            if nested_id==ACTION_VITAL:
                armed_before=self.p30_action_target_armed
                try:
                    action=parse_action_vital(parsed)
                except Exception as e:
                    self.events.append(
                        f'v126_action_vital_parse_error_no_reply_{e!r}'
                    )
                else:
                    floats=(
                        action['heading_f32_38'],action['x_f32_3c'],
                        action['y_f32_40'],action['z_f32_44'],
                    )
                    exact_target_bound_wield_action=(
                        parsed.outer_version==0 and
                        parsed.outer_mask==0x02 and
                        parsed.nested_version==0 and
                        armed_before and
                        action['field_qword_18']==0 and
                        action['field_qword_20']==0 and
                        action['field_qword_28']==V126_ACTION_TARGET_ACTOR_ID and
                        action['action_u32_30']==V128_WIELD_ACTION_CODE and
                        action['field_u32_34']==0 and
                        all(math.isfinite(value) for value in floats) and
                        action['field_u8_4c']==0
                    )
                    if exact_target_bound_wield_action:
                        self.action_vital_capture_count+=1
                        self.action_vital_last_fields=dict(action)
                    self.events.append(
                        'v128_action_vital_wield_z_capture_no_reply_'
                        f"q1_0x{action['field_qword_18']:016X}_"
                        f"q2_0x{action['field_qword_20']:016X}_"
                        f"q3_0x{action['field_qword_28']:016X}_"
                        f"action_0x{action['action_u32_30']:08X}_"
                        f"u32_34_{action['field_u32_34']}_"
                        f"opaque_u8_48_{action['field_u8_48']}_"
                        f"opaque_u16_4a_{action['field_u16_4a']}_"
                        f"u8_4c_{action['field_u8_4c']}_"
                        f"armed_{int(armed_before)}_"
                        f"exact_{int(exact_target_bound_wield_action)}"
                    )
                # One ActionVital consumes the preceding target arm regardless
                # of validity. A new capture requires a new exact P30 selection.
                self.p30_action_target_armed=False

            if nested_id == CHECK_SECOND_PWD_VITAL:
                pwd_pc, pwd_frame = make_check_second_password_success()
                outbound.append(("V110_CHECK_SECOND_PASSWORD_OK", pwd_pc, pwd_frame, 0.0))
                self.events.append("v110_check_second_password_ok")

            if nested_id == ITEM_OPERATE_REQ_VITAL:
                try:
                    operation,value32,item_identity=parse_item_operate_req(parsed)
                except Exception as e:
                    self.events.append(f'v110_item_operate_parse_error_{e!r}')
                else:
                    equipment_capture_valid=(
                        parsed.nested_version==0 and
                        parsed.vital_count==1 and
                        operation==V123_EQUIP_FROM_BAG_OPERATION and
                        value32 in V123_EQUIP_FROM_BAG_VALUE32 and
                        item_identity==V123_BLADE_SEQUENCE
                    )
                    merge_valid=(
                        operation==4 and
                        item_identity==V111_STACK_SOURCE_SEQUENCE and
                        value32==self.item_slot and
                        self.stack_source_present and
                        self.item_slot==V103_ITEM_SLOT and
                        self.item_quantity + V111_STACK_SOURCE_QUANTITY
                        <= V111_ADVENTURE_KEY_STACK_LIMIT
                    )
                    valid=(
                        operation==4 and item_identity==V103_ITEM_SEQUENCE and
                        0 <= value32 < 40 and value32!=self.probe_item_slot and
                        (not self.stack_source_present or value32!=self.stack_source_slot)
                    )
                    if equipment_capture_valid:
                        self.equipment_capture_count+=1
                        self.equipment_last_value32_mapped=value32
                        self.equipment_last_item_identity=item_identity
                        self.events.append(
                            'v123_equip_from_bag_op5_id4_capture_no_reply_'
                            f'value32_mapped_{value32}'
                        )
                    elif merge_valid:
                        merge_pc,merge_frame=make_item_operate_stack_merge_success()
                        outbound.append((
                            "V111_ITEM_STACK_ID3_INTO_ID1_QTY2_SUCCESS",
                            merge_pc,merge_frame,0.0,
                        ))
                        self.item_quantity+=V111_STACK_SOURCE_QUANTITY
                        self.stack_source_present=False
                        self.stack_merge_count+=1
                        self.events.append(
                            'v111_item_stack_id3_into_id1_qty2_sent'
                        )
                    elif valid and value32!=self.item_slot:
                        source_slot=self.item_slot
                        move_pc,move_frame=make_item_operate_move_delta_success(
                            value32,self.item_quantity
                        )
                        outbound.append((
                            f"V111_ITEM_MOVE_ID1_SLOT{source_slot}_TO_SLOT{value32}_SUCCESS",
                            move_pc,move_frame,0.0,
                        ))
                        self.item_slot=value32
                        self.item_move_count+=1
                        self.events.append(
                            f'v111_item_move_id1_slot{source_slot}_to_slot{value32}_sent'
                        )
                    elif valid:
                        self.events.append('v110_item_move_same_slot_no_reply')
                    else:
                        self.events.append(
                            f'v110_item_operate_unsupported_no_reply_'
                            f'op{operation}_value{value32}_id{item_identity}'
                        )

            if nested_id == QUEST_OPERATE_VITAL:
                try:
                    quest=parse_quest_operate_vital(parsed)
                except Exception as e:
                    self.events.append(
                        f'v134_quest_operate_parse_error_no_reply_{e!r}'
                    )
                else:
                    fields=(
                        quest['quest_id'],quest['field_u8_16'],
                        quest['field_u8_17'],quest['field_u32_18'],
                        quest['field_qword_20'],quest['field_u8_28'],
                    )
                    exact_quest_envelope=(
                        parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
                        parsed.outer_version==0 and
                        parsed.outer_mask==0x02 and
                        parsed.nested_version==3 and
                        parsed.vital_count==1
                    )
                    exact_conversation_op1_request=(
                        exact_quest_envelope and
                        fields==(V129_QUEST_ID,1,0,0,0,0)
                    )
                    exact_action6_op2_request=(
                        exact_quest_envelope and
                        fields==(V129_QUEST_ID,2,0,0,0,0)
                    )
                    if exact_conversation_op1_request:
                        self.quest3020_op1_capture_count+=1
                        self.quest_operate_capture_count+=1
                        self.quest_operate_last_fields=fields
                    elif exact_action6_op2_request:
                        self.quest3020_op2_capture_count+=1
                        self.quest_operate_capture_count+=1
                        self.quest_operate_last_fields=fields
                    op1_sequence_valid=(
                        exact_conversation_op1_request and
                        self.quest3020_conversation_sent and
                        not self.quest3020_accept_ui_sent and
                        not self.quest3020_accept_success_sent
                    )
                    if op1_sequence_valid:
                        accept_ui_pc,accept_ui_frame=(
                            make_quest3020_action6_accept_ui()
                        )
                        # This op1->action6 link is the bounded V134 integration
                        # hypothesis. Arm it one time before returning the wire.
                        self.quest3020_accept_ui_sent=True
                        outbound.append((
                            'V134_BOUNDED_HYPOTHESIS_Q3020_OP1_TO_ACTION6_ONCE',
                            accept_ui_pc,accept_ui_frame,0.0,
                        ))
                        self.events.append(
                            'v134_bounded_integration_hypothesis_'
                            'q3020_op1_after_p0_conversation_action6_sent_once'
                        )
                    elif exact_conversation_op1_request:
                        self.events.append(
                            'v134_q3020_exact_op1_wrong_sequence_no_reply_'
                            f'conversation_sent_{int(self.quest3020_conversation_sent)}_'
                            f'action6_sent_{int(self.quest3020_accept_ui_sent)}_'
                            f'action1_sent_{int(self.quest3020_accept_success_sent)}'
                        )
                    op2_sequence_valid=(
                        exact_action6_op2_request and
                        self.quest3020_conversation_sent and
                        self.quest3020_accept_ui_sent and
                        not self.quest3020_accept_success_sent
                    )
                    if op2_sequence_valid:
                        accept_pc,accept_frame=(
                            make_quest3020_action1_accept_success()
                        )
                        # Flip the one-shot state before returning the packet so
                        # a replay can never queue a second Accept_Run response.
                        self.quest3020_accept_success_sent=True
                        self.v136_docking_composition_pending=True
                        outbound.append((
                            'V134_QUEST3020_P0_ACTION1_ACCEPT_SUCCESS_ONCE',
                            accept_pc,accept_frame,0.0,
                        ))
                        self.events.append(
                            'v134_quest3020_op2_after_action6_pending_'
                            'action1_accept_success_sent_once_'
                            'v136_docking_composition_armed'
                        )
                    elif exact_action6_op2_request:
                        self.events.append(
                            'v134_quest3020_exact_op2_wrong_sequence_no_reply_'
                            f'conversation_sent_{int(self.quest3020_conversation_sent)}_'
                            f'action6_sent_{int(self.quest3020_accept_ui_sent)}_'
                            'action1_sent_'
                            f'{int(self.quest3020_accept_success_sent)}'
                        )
                    self.events.append(
                        'v134_quest_operate_request_audit_'
                        f"outer_version{parsed.outer_version}_"
                        f"outer_mask0x{parsed.outer_mask:02X}_"
                        f"nested_version{parsed.nested_version}_"
                        f"count{parsed.vital_count}_"
                        f"quest{quest['quest_id']}_u8_16_{quest['field_u8_16']}_"
                        f"u8_17_{quest['field_u8_17']}_"
                        f"u32_18_{quest['field_u32_18']}_"
                        f"qword_20_{quest['field_qword_20']}_"
                        f"u8_28_{quest['field_u8_28']}_"
                        f"exact_q3020_conversation_op1_v3_singleton_"
                        f"{int(exact_conversation_op1_request)}_"
                        f"op1_sequence_valid_{int(op1_sequence_valid)}_"
                        f"exact_q3020_action6_op2_v3_singleton_"
                        f"{int(exact_action6_op2_request)}_"
                        f"op2_sequence_valid_{int(op2_sequence_valid)}"
                    )

            if nested_id == TELEPORT_CHECK_VITAL:
                try:
                    teleport_check=parse_teleport_check_vital(parsed)
                except Exception as e:
                    self.events.append(
                        f'v131_teleport_check_parse_error_no_reply_{e!r}'
                    )
                else:
                    exact_scene1_echo=(
                        parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
                        parsed.outer_version==0 and
                        parsed.outer_mask==0x02 and
                        parsed.nested_version==0 and
                        parsed.vital_count==1 and
                        teleport_check['field_u16_14']==V131_TELEPORT_CHECK_VALUE and
                        self.teleport_check_challenge_sent
                    )
                    exact_v136_marker1_confirm=(
                        parsed.raw_pc==V136_MARKER1_CONFIRM_PC and
                        parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
                        parsed.outer_version==0 and
                        parsed.outer_mask==0x02 and
                        parsed.nested_version==0 and
                        parsed.vital_count==1 and
                        teleport_check['field_u16_14']==V131_TELEPORT_CHECK_VALUE and
                        self.v136_marker1_prompt_sent and
                        self.v136_marker1_confirm_capture_count==0
                    )
                    if exact_scene1_echo:
                        self.teleport_check_echo_capture_count+=1
                        self.teleport_check_echo_last_value=(
                            teleport_check['field_u16_14']
                        )
                    if exact_v136_marker1_confirm:
                        self.v136_marker1_confirm_capture_count+=1
                        self.v136_marker1_confirm_last_value=(
                            teleport_check['field_u16_14']
                        )
                        if not self.v137_marker1_transport_sent:
                            # Set one-shot state before queueing so no re-entry or
                            # replay can emit a second transport probe.
                            self.v137_marker1_transport_sent=True
                            self.v137_marker1_transport_send_count+=1
                            transport_pc,transport_frame=(
                                make_v137_marker1_transport_probe()
                            )
                            outbound.append((
                                'V137_ISOLATED_COMPOSITIONAL_MARKER1_'
                                'TELEPORTVITAL_TRANSPORT_PROBE_ONCE',
                                transport_pc,transport_frame,0.0,
                            ))
                            self.events.append(
                                'v137_exact_marker1_positive_confirm_'
                                'server_driven_teleportvital_scene1_seq0_'
                                'xyz_minus10322_minus755_671_sent_once_'
                                'isolated_compositional_transport_hypothesis_'
                                'not_teleportcheck_reply_not_completed_travel'
                            )
                    self.events.append(
                        'v131_teleport_check_scene1_echo_capture_no_reply_'
                        f"field_u16_14_{teleport_check['field_u16_14']}_"
                        f"count{parsed.vital_count}_challenge_sent_"
                        f'{int(self.teleport_check_challenge_sent)}_'
                        f'exact_{int(exact_scene1_echo)}_semantics_unassigned'
                    )
                    self.events.append(
                        'v136_marker1_positive_confirm_capture_'
                        'no_teleportcheck_reply_'
                        f"field_u16_14_{teleport_check['field_u16_14']}_"
                        f"count{parsed.vital_count}_prompt_sent_"
                        f'{int(self.v136_marker1_prompt_sent)}_'
                        f'exact_{int(exact_v136_marker1_confirm)}_'
                        'compositional_q3020_var2_1_docking_hypothesis_'
                        'no_travel_vehicle_completion_claim'
                    )

            if nested_id == TRADE_CMD_VITAL:
                try:
                    trade = parse_trade_cmd_vital(parsed)
                except Exception as e:
                    self.events.append(f'v118_trade_cmd_parse_error_no_reply_{e!r}')
                else:
                    cart_add_valid = (
                        parsed.nested_version == 0
                        and parsed.vital_count == 1
                        and trade['field_u8'] == V118_TRADE_CART_ADD_COMMAND
                        and trade['field_u32'] == V118_TRADE_CART_ADD_DWORD
                        and trade['has_detail'] == 1
                        and trade['detail_identity'] == 0
                        and trade['detail_template'] == V112_STORE_PRODUCT_TEMPLATE
                        and trade['detail_quantity'] == 1
                        and self.trade_cart_ack_count == 0
                        and self.current_cash == V116_INITIAL_CASH
                    )
                    if cart_add_valid:
                        ack_pc, ack_frame = make_trade_item_result_store_buy_cart_ack(
                            trade['detail_identity'],
                            trade['detail_template'],
                            trade['detail_quantity'],
                        )
                        outbound.append((
                            'V118_TRADE_SHOP_STORE_BY_ITEM_OK_CART_ACK',
                            ack_pc, ack_frame, 0.0,
                        ))
                        self.trade_cart_ack_count += 1
                        self.trade_cart_last_ack_detail = (
                            trade['detail_identity'],
                            trade['detail_template'],
                            trade['detail_quantity'],
                        )
                        self.events.append(
                            'v118_trade_cmd6_dword0_sword_soul_qty1_cart_ack_sent_'
                            f"identity{trade['detail_identity']}"
                        )
                    elif (
                        parsed.nested_version == 0
                        and parsed.vital_count == 1
                        and trade['field_u8'] == V121_CAPTURED_FINAL_BUY_COMMAND
                        and trade['field_u32'] == V121_CAPTURED_FINAL_BUY_DWORD
                        and trade['has_detail'] == 0
                    ):
                        final_buy_sequence_valid = (
                            self.trade_cart_ack_count == 1
                            and self.trade_cart_last_ack_detail
                            == (0, V112_STORE_PRODUCT_TEMPLATE, 1)
                            and self.trade_final_buy_last_cart_ack_count
                            != self.trade_cart_ack_count
                            and self.current_cash == V116_INITIAL_CASH
                        )
                        if final_buy_sequence_valid:
                            cash_pc, cash_frame = make_update_attr_cash_only()
                            outbound.append((
                                'V122_UPDATE_ATTR_ACTOR_CASH_10000_TO_0_ONCE',
                                cash_pc, cash_frame, 0.0,
                            ))
                            self.trade_final_buy_capture_count += 1
                            self.trade_final_buy_last_cart_ack_count = (
                                self.trade_cart_ack_count
                            )
                            self.current_cash = V122_FINAL_CASH
                            identity, template, quantity = (
                                self.trade_cart_last_ack_detail
                            )
                            self.events.append(
                                'v122_trade_cmd8_dword0_no_detail_cash_update_sent_'
                                f'capture{self.trade_final_buy_capture_count}_'
                                f'cart_ack_count{self.trade_cart_ack_count}_'
                                f'last_identity{identity}_template{template}_'
                                f'quantity{quantity}_cash10000_to_0'
                            )
                        else:
                            self.events.append(
                                'v122_trade_cmd8_dword0_no_detail_final_buy_'
                                'wrong_sequence_no_reply_'
                                f'cart_ack_count{self.trade_cart_ack_count}_'
                                'last_final_cart_ack_count'
                                f'{self.trade_final_buy_last_cart_ack_count}_'
                                f'cash{self.current_cash}'
                            )
                    elif (
                        parsed.nested_version == 0
                        and parsed.vital_count == 1
                        and trade['field_u8'] == V121_CAPTURED_STORE_CLOSE_COMMAND
                        and trade['field_u32'] == V121_CAPTURED_STORE_CLOSE_DWORD
                        and trade['has_detail'] == 0
                    ):
                        self.trade_store_close_capture_count += 1
                        self.events.append(
                            'v121_trade_cmd12_dword0_no_detail_store_close_'
                            'captured_no_reply_'
                            f'count{self.trade_store_close_capture_count}'
                        )
                    else:
                        self.events.append(
                            'v121_trade_cmd_unsupported_no_reply_'
                            f"version{parsed.nested_version}_count{parsed.vital_count}_"
                            f"command{trade['field_u8']}_dword{trade['field_u32']}_"
                            f"detail{trade['has_detail']}"
                        )

            # V73 preserves the V62/V59 golden authentic-population state to all 115 unambiguous placements but supplies the statically
            # resolved BasicAttr current/max HP pair (+0x44/+0x48) at 100/100.
            # Emit all 115 together as ONE snapshot, then reapply once after model readiness.
            if nested_id == TARGET_POS_VITAL:
                try:
                    pos = parse_target_pos_vital(parsed)
                except Exception as e:
                    pos = None
                    self.events.append(f"target_pos_parse_error_{e!r}")
                if (
                    pos is not None and
                    not all(math.isfinite(value) for value in pos[:4])
                ):
                    self.events.append('v141_target_pos_nonfinite_rejected')
                    pos=None
                if (
                    pos is not None and
                    self.v138_marker1_population_sent and
                    self.v139_p86_conversation_sent and
                    parse_v141_refresh_target_pos(parsed) is None
                ):
                    self.events.append(
                        'v141_target_pos_nonexact_refresh_shape_rejected'
                    )
                    pos=None
                if pos is not None:
                    x, y, z, heading, _flags, _moving = pos
                    self.last_target_pos = (x, y, z, heading)
                    self.events.append(f"target_pos_{x:.2f}_{y:.2f}_{z:.2f}")
                    exact_v139_marker_targetpos=(
                        parsed.raw_pc==V139_MARKER1_TARGETPOS_PC
                    )
                    if (
                        exact_v139_marker_targetpos and
                        self.v138_marker1_population_sent and
                        self.npc_spawn_sent and
                        self.population_indices==V138_MARKER1_NEAREST_INDICES and
                        not self.v139_p86_interaction_armed and
                        not self.v139_p86_face_sent and
                        not self.v139_p86_conversation_sent
                    ):
                        self.v139_marker_targetpos_capture_count+=1
                        self.v139_p86_interaction_armed=True
                        self.events.append(
                            'v139_exact_44b_singleton_marker_targetpos_'
                            'fresh_p86_interaction_armed_once'
                        )
                    elif (
                        self.v139_p86_interaction_armed and
                        not exact_v139_marker_targetpos
                    ):
                        # Preserve exact sequencing: a later player-position
                        # update invalidates the marker position used by the
                        # bounded facing derivation.
                        self.v139_p86_interaction_armed=False
                        self.events.append(
                            'v139_intervening_nonmarker_targetpos_disarmed_'
                            'p86_interaction_no_send'
                        )

            if self.runtime_ack_sent and self.last_target_pos is not None and not self.npc_spawn_sent:
                x, y, z, heading = self.last_target_pos
                npc_pc,npc_frame,local_rows=make_v112_monster_shop_population_state()
                outbound.append((
                    'V134_P0_P30_P91_ISOLATED_INITIAL_READY',
                    npc_pc,npc_frame,0.0,
                ))
                # Preserve the proven model-ready reapply schedule while keeping
                # the authoritative set fixed at exactly these three entrants.
                outbound.append((
                    'V134_P0_P30_P91_ISOLATED_REAPPLY_READY',
                    npc_pc,npc_frame,3.00,
                ))
                self.events.append(
                    "v134_exact_p0_usage2_p30_usage1_p91_usage2_full_placements"
                )
                self.npc_spawn_sent = True
                self.npc_idle_action_sent = False
                self.population_indices=tuple(row[0] for row in local_rows)
                self.population_refresh_anchor=(x,y,z)
                self.events.append(
                    "v112_isolated_population_indices_"+
                    "_".join(str(row[0]) for row in local_rows)
                )

            # Before transport, retain the isolated P0/P30/P91 prerequisite.
            # After the exact V140 destination conversation, restore V95's
            # data-driven >=1000-unit nearest-set refresh. Retained actors carry
            # NPCAttr only, which preserves P86 at its current synthetic harness
            # XYZ. An actor that left the set is a new entrant later and receives
            # its authentic placement MovementAttr. P30's exact HP/name are built
            # by make_v141_population_refresh_state for every snapshot.
            elif (
                nested_id == TARGET_POS_VITAL
                and self.npc_spawn_sent
            ):
                if self.v138_marker1_population_sent:
                    if (
                        pos is not None and
                        parse_v141_refresh_target_pos(parsed)==pos and
                        self.v139_p86_conversation_sent and
                        self.last_target_pos is not None and
                        self.population_indices is not None and
                        self.population_refresh_anchor is not None
                    ):
                        x,y,z,_heading=self.last_target_pos
                        ax,ay,az=self.population_refresh_anchor
                        travel2=(x-ax)**2+(y-ay)**2+(z-az)**2
                        if travel2>=V94_REFRESH_DISTANCE**2:
                            new_rows=_v94_nearest_population(x,y,z)
                            new_indices=tuple(row[0] for row in new_rows)
                            old_indices=self.population_indices
                            old_set=set(old_indices)
                            new_set=set(new_indices)
                            # V95 advances the scan anchor even when only nearest
                            # ordering changed, but suppresses an empty snapshot.
                            self.population_refresh_anchor=(x,y,z)
                            if new_set!=old_set:
                                pc,frame,_=make_v141_population_refresh_state(
                                    x,y,z,old_set
                                )
                                entered=sorted(new_set-old_set)
                                left=sorted(old_set-new_set)
                                self.population_indices=new_indices
                                self.v141_population_refresh_count+=1
                                outbound.append((
                                    'V141_LOCAL_REFRESH_ENTER['+
                                    ','.join(map(str,entered))+']_LEAVE['+
                                    ','.join(map(str,left))+']',
                                    pc,frame,0.0,
                                ))
                                p86_state=(
                                    'retained_synthetic_no_movement'
                                    if V139_P86_INDEX in (old_set & new_set) else
                                    'reentered_authentic_movement'
                                    if V139_P86_INDEX in (new_set-old_set) else
                                    'left_or_absent'
                                )
                                self.events.append(
                                    'v141_population_refresh_enter_'+
                                    '_'.join(map(str,entered))+'_leave_'+
                                    '_'.join(map(str,left))+'_p86_'+p86_state
                                )
                            else:
                                self.events.append(
                                    'v141_population_scan_membership_unchanged'
                                )
                    elif not self.v139_p86_conversation_sent:
                        self.events.append(
                            'v141_destination_population_frozen_until_p86_'
                            'conversation_complete'
                        )
                else:
                    self.events.append(
                        'v129_isolated_population_retained_p0_p30_p91'
                    )

            # V97 runtime proved that an empty NPCConversation collection is the
            # authentic default-talk trigger: the client resolves this actor's
            # MOBS template to MOBS_TIP s_NAME/s_TITLE/s_NPC_CHATS locally. V98
            # keeps that exact response and adds a separate complete population
            # snapshot with authentic position + calculated heading for only the
            # chosen member. Never return to V95's mask 0x02 heading-only packet.
            if (
                nested_id in (TARGET_VITAL,CHOOSE_NPC) and
                self.population_indices is not None and
                not self.v138_marker1_population_sent
            ):
                try:
                    choose_identities=extract_choose_npc_identities(parsed)
                except Exception as e:
                    self.events.append(f'choose_npc_parse_error_{e!r}')
                else:
                    # A double-click can enqueue the same ChooseNPC repeatedly
                    # in one RuntimeReq. One response per distinct actor avoids
                    # opening the same client path several times.
                    for actor_identity in dict.fromkeys(choose_identities):
                        idx=actor_identity-0x2000-1
                        if idx in self.population_indices:
                            if idx==V112_MONSTER_INDEX:
                                self.events.append(
                                    'v112_choose_p30_usage1_no_npc_response'
                                )
                                continue
                            x,y,_z,_heading=self.last_target_pos
                            face_state,face_idx=make_v98_conversation_face_state(
                                self.population_indices,actor_identity,x,y
                            )
                            face_pc,face_frame=face_state
                            face_label=(
                                f'V112_TEST_HARNESS_FACE_PLAYER_P{face_idx}'
                                if idx==V112_SHOP_TRIGGER_INDEX else
                                f'V98_NPC_FACE_PLAYER_POSITION_HEADING_P{face_idx}'
                            )
                            outbound.append((
                                face_label,
                                face_pc,face_frame,0.0,
                            ))
                            self.events.append(
                                f'v112_safe_face_player_position_heading_p{idx}'
                            )
                            if idx==V112_SHOP_TRIGGER_INDEX:
                                if not self.shop_store5_open_sent:
                                    shop_pc,shop_frame=make_trade_zoom_store5()
                                    outbound.append((
                                        'V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL',
                                        shop_pc,shop_frame,0.0,
                                    ))
                                    self.shop_store5_open_sent=True
                                    self.events.append(
                                        'v112_test_harness_store5_open_for_p91_no_ownership_claim'
                                    )
                                else:
                                    self.events.append(
                                        'v112_store5_duplicate_open_suppressed'
                                    )
                            elif idx==V129_QUEST_ACTOR_INDEX:
                                # ``actor_identity`` reached this loop only via
                                # an exact ChooseNPC record. The outer packet may
                                # begin with TargetVital and carry ChooseNPC as a
                                # later tagged vital, as proved in V74/V96.
                                if not self.quest3020_conversation_sent:
                                    conv_pc,conv_frame=(
                                        make_npc_conversation_quest3020(actor_identity)
                                    )
                                    self.quest3020_conversation_sent=True
                                    outbound.append((
                                        'V134_P0_Q3020_NPC_CONVERSATION_ONCE',
                                        conv_pc,conv_frame,0.0,
                                    ))
                                    self.events.append(
                                        'v134_p0_q3020_npc_conversation_sent_once'
                                    )
                                else:
                                    self.events.append(
                                        'v134_p0_q3020_npc_conversation_duplicate_'
                                        'suppressed'
                                    )
                            else:
                                conv_pc,conv_frame=make_npc_conversation_empty(actor_identity)
                                outbound.append((
                                    f'V98_NPC_CONVERSATION_DEFAULT_P{idx}',
                                    conv_pc,conv_frame,0.0,
                                ))
                                self.events.append(
                                    f'v98_npc_conversation_default_p{idx}'
                                )
                        else:
                            self.events.append(
                                f'v98_choose_npc_noncurrent_ignored_0x{actor_identity:016X}'
                            )
            elif (
                nested_id in (TARGET_VITAL,CHOOSE_NPC) and
                self.population_indices is not None and
                self.v138_marker1_population_sent
            ):
                interaction_shape=parse_v139_p86_interaction_shape(parsed)
                if interaction_shape is None:
                    self.events.append(
                        'v139_destination_interaction_shape_rejected_no_send'
                    )
                elif not (
                    self.v139_p86_interaction_armed and
                    self.npc_spawn_sent and
                    self.population_indices==V138_MARKER1_NEAREST_INDICES and
                    self.last_target_pos is not None and
                    not self.v139_p86_face_sent and
                    not self.v139_p86_conversation_sent
                ):
                    self.events.append(
                        'v139_exact_p86_interaction_wrong_sequence_membership_'
                        'or_replay_no_send'
                    )
                else:
                    choose_count,_trailing_target_pos=interaction_shape
                    player_x,player_y,_player_z,_player_heading=(
                        self.last_target_pos
                    )
                    face_pc,face_frame=make_v140_p86_face_state(
                        player_x,player_y
                    )
                    conv_pc,conv_frame=make_npc_conversation_empty(
                        V139_P86_ACTOR_ID
                    )
                    # Commit the one-shot state before queueing either packet.
                    self.v139_p86_interaction_armed=False
                    self.v139_p86_choose_capture_count+=1
                    self.v139_p86_face_sent=True
                    self.v139_p86_conversation_sent=True
                    outbound.append((
                        'V140_P86_HARNESS_SAFE_FULL20_FACE_ONCE',
                        face_pc,face_frame,0.0,
                    ))
                    outbound.append((
                        'V140_P86_HARNESS_EMPTY_DEFAULT_CONVERSATION_ONCE',
                        conv_pc,conv_frame,0.0,
                    ))
                    self.events.append(
                        'v140_exact_current_p86_target_choose_shape_'
                        f'choose_records{choose_count}_full20_safe_face_then_'
                        'empty_conversation_sent_once'
                    )

        return outbound


def _synthetic_client_login_pc(token="localtest") -> bytes:
    payload = b"\x0B\x68\x48\x04\x00\x00\x00\x0E\x00\x00\x00" + astr_tag(token)
    pc = bytearray()
    pc += u16tag(0x12, GSCN_LOGIN_PROTOCOL) + u32tag(0x14, 0) + u8tag(0x08, 0)
    pc += u8tag(0x0B, 2) + u16tag(0x12, 1)
    pc += u16tag(0x12, LOGIN_VERIFY_VITAL) + u8tag(0x0B, 0) + payload
    return bytes(pc)


def _synthetic_notify_pc(value: int) -> bytes:
    pc = bytearray()
    pc += u16tag(0x12, GSCN_LOGIN_PROTOCOL) + u32tag(0x14, 0) + u8tag(0x08, 0)
    pc += u8tag(0x0B, 2) + u16tag(0x12, 1)
    pc += u16tag(0x12, NOTIFY_ENTER_CREATE_ACTOR) + u8tag(0x0B, 0) + b"\x05" + bytes([value])
    return bytes(pc)


_V25_REAL_CREATE_PC = bytes.fromhex("""
12 3A 45 14 00 00 00 00 08 00 0B 02 12 01 00 12
CF 36 0B 08 08 01 0B 01 32 00 00 00 00 00 00 00
00 0B 00 48 0C 00 00 00 74 00 65 00 73 00 74 00
30 00 31 00 0B 01 0B 01 19 01 00 00 00 12 01 00
12 01 00 44 20 00 00 00 35 35 42 38 36 38 39 32
46 39 33 34 34 37 39 39 38 30 44 46 39 44 37 39
43 31 32 34 37 46 37 41 48 0E 00 00 00 74 00 65
00 73 00 74 00 30 00 30 00 31 00 0B FF 32 01 00
00 00 00 00 00 00 26 FF FF FF FF 14 00 00 00 00
14 09 40 11 00 14 F0 EF 10 00 14 1A F0 10 00 14
00 00 00 00 14 7A 18 23 00 14 7B 18 23 00 14 00
00 00 00 14 00 00 00 00 14 00 00 00 00 14 C2 91
21 00 14 C2 91 21 00 0B 01 08 1E 08 1E 44 00 00
00 00 0B 00 14 00 00 00 00 0B 01 0B 01 14 00 00
00 00 0B 00 14 00 00 00 00 14 00 00 00 00
""")


def _synthetic_empty_gscn_pc() -> bytes:
    return (
        u16tag(0x12, GSCN_LOGIN_PROTOCOL)
        + u32tag(0x14, 0)
        + u8tag(0x08, 0)
        + u8tag(0x0B, 0)
    )


def _synthetic_start_game_pc(selector: int) -> bytes:
    pc = bytearray()
    pc += u16tag(0x12, GSCN_LOGIN_PROTOCOL) + u32tag(0x14, 0) + u8tag(0x08, 0)
    pc += u8tag(0x0B, 2) + u16tag(0x12, 1)
    pc += u16tag(0x12, START_GAME_REQ) + u8tag(0x0B, 0) + u8tag(0x08, selector)
    return bytes(pc)


def _synthetic_trade_cmd_pc(
    command: int,
    value32: int,
    detail: tuple[int, int, int] | None = None,
    *,
    nested_version: int = 0,
) -> bytes:
    """Build the exact one-vital client request shape used by V118 tests."""
    payload = u8tag(0x08, command) + u32tag(0x19, value32)
    payload += u8tag(0x08, 1 if detail is not None else 0)
    if detail is not None:
        identity, template, quantity = detail
        payload += (
            qwordtag(0x32, identity)
            + u32tag(0x14, template)
            + u16tag(0x0F, quantity)
        )
    return (
        u16tag(0x12, GSCN_RUNTIME_PROTOCOL_REQ)
        + u32tag(0x14, 0)
        + u8tag(0x08, 0)
        + u8tag(0x0B, 2)
        + u16tag(0x12, 1)
        + u16tag(0x12, TRADE_CMD_VITAL)
        + u8tag(0x0B, nested_version)
        + payload
    )


def _synthetic_quest_operate_pc(
    quest_id: int,
    field_u8_16: int,
    field_u8_17: int,
    field_u32_18: int,
    field_qword_20: int,
    field_u8_28: int,
    *,
    outer_version: int = 0,
    outer_mask: int = 0x02,
    nested_version: int = 3,
) -> bytes:
    """Build a serializer-exact singleton QuestOperate request fixture."""
    payload=(
        u16tag(0x12,quest_id)
        +u8tag(0x08,field_u8_16)
        +u8tag(0x08,field_u8_17)
        +u32tag(0x14,field_u32_18)
        +qwordtag(0x32,field_qword_20)
        +u8tag(0x05,field_u8_28)
    )
    return (
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)
        +u32tag(0x14,0)
        +u8tag(0x08,outer_version)
        +u8tag(0x0B,outer_mask)
        +u16tag(0x12,1)
        +u16tag(0x12,QUEST_OPERATE_VITAL)
        +u8tag(0x0B,nested_version)
        +payload
    )


def _synthetic_action_vital_pc(
    field_qword_18:int=0,
    field_qword_20:int=0,
    field_qword_28:int=V126_ACTION_TARGET_ACTOR_ID,
    action_u32_30:int=V128_WIELD_ACTION_CODE,
    field_u32_34:int=0,
    heading_f32_38:float=0.5,
    x_f32_3c:float=100.0,
    y_f32_40:float=200.0,
    z_f32_44:float=931.0,
    field_u8_48:int=0,
    field_u16_4a:int=1,
    field_u8_4c:int=0,
    *,
    outer_version:int=0,
    outer_mask:int=0x02,
    nested_version:int=0,
    extra_nested:bytes=b'',
) -> bytes:
    """Build a serializer-exact ActionVital request fixture for V126 tests."""
    body=(
        qwordtag(0x32,field_qword_18)
        +qwordtag(0x32,field_qword_20)
        +qwordtag(0x32,field_qword_28)
        +u32tag(0x14,action_u32_30)
        +u32tag(0x19,field_u32_34)
        +f32tag(heading_f32_38)
        +f32tag(x_f32_3c)
        +f32tag(y_f32_40)
        +f32tag(z_f32_44)
        +u8tag(0x0B,field_u8_48)
        +u16tag(0x12,field_u16_4a)
        +u8tag(0x0B,field_u8_4c)
    )
    vital_count=1+(1 if extra_nested else 0)
    return (
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)
        +u32tag(0x14,0)
        +u8tag(0x08,outer_version)
        +u8tag(0x0B,outer_mask)
        +u16tag(0x12,vital_count)
        +u16tag(0x12,ACTION_VITAL)
        +u8tag(0x0B,nested_version)
        +body
        +extra_nested
    )


def run_self_test(verbose: bool = True) -> None:
    """Offline regression + real v25 CreateActor replay tests."""
    st = GameSessionState("localtest")

    login_pc = _synthetic_client_login_pc()
    parsed = parse_outer(login_pc)
    out = st.dispatch(parsed)
    assert [x[0] for x in out] == ["LOGIN_VERIFY_ACK_ONCE", "SELECT_ACTOR_PRESET_ONE_ONCE"], out
    assert st.login_ack_sent and st.select_actor_sent

    # Exact v24 loop regression: outer GSCN_LoginProtocol is not enough to trigger login.
    notify0 = _synthetic_notify_pc(0)
    for _ in range(12):
        out = st.dispatch(parse_outer(notify0))
        assert out == [], f"Notify0 unexpectedly generated {out!r}"
    assert st.notify_count == 12 and st.last_notify_value == 0

    notify1 = _synthetic_notify_pc(1)
    out = st.dispatch(parse_outer(notify1))
    assert out == [], f"Notify1 unexpectedly generated {out!r}"
    assert st.last_notify_value == 1

    out = st.dispatch(parse_outer(login_pc))
    assert out == [], f"duplicate LoginVerifyVital unexpectedly generated {out!r}"

    # Empty 12-byte GSCN wrapper is structural count=0/no-op.
    hb = parse_outer(_synthetic_empty_gscn_pc())
    assert hb.outer_id == GSCN_LOGIN_PROTOCOL and hb.vital_count == 0 and hb.nested_id is None
    assert st.dispatch(hb) == []

    # Canonical SelectActorVital: RuntimeRes v4 / mask2 / one vital / v10,
    # exact v25-proven three-tail payload.
    sel_pc, _ = make_runtime_select_actor_empty()
    sel = parse_outer(sel_pc)
    assert sel.outer_id == GSCN_RUNTIME_PROTOCOL_RES
    assert sel.outer_version == 4 and sel.outer_mask == 2 and sel.vital_count == 1
    assert sel.nested_id == SELECT_ACTOR_VITAL and sel.nested_version == 10
    assert sel.nested_payload == make_select_actor_empty_payload()
    assert len(sel_pc) == 43, len(sel_pc)

    # V39 persisted actor list: same RuntimeRes/SelectActor v10 envelope, count=1,
    # exact captured actor wire, and the two runtime-required trailing zero masks.
    preset_pc, _ = make_runtime_select_actor_preset()
    preset = parse_outer(preset_pc)
    assert preset.outer_id == GSCN_RUNTIME_PROTOCOL_RES
    assert preset.outer_version == 4 and preset.outer_mask == 2 and preset.vital_count == 1
    assert preset.nested_id == SELECT_ACTOR_VITAL and preset.nested_version == 10
    expected_actor = get_preset_actor_wire()
    prefix = (u8tag(0x0B, 0) + u32tag(0x14, 0) + u32tag(0x14, 0) +
              u32tag(0x1F, 0) + u8tag(0x0B, 0) + u8tag(0x0B, 1))
    assert preset.nested_payload.startswith(prefix + expected_actor)
    assert preset.nested_payload.endswith(u8tag(0x0B, 0) + u8tag(0x0B, 0))
    assert decode_create_actor_data_ex(expected_actor)["selector"] == 0
    av_wire = make_avatar_attr_from_preset()
    # Exact embedded AvatarAttr from test01: common Attr flags+identity followed by
    # full 0xFFFFFFFF AvatarAttr mask.  This must not regress to the old mask=0 placeholder.
    assert av_wire.startswith(bytes.fromhex("0B FF 32")), av_wire[:16].hex()
    assert bytes.fromhex("26 FF FF FF FF") in av_wire[:20], av_wire[:24].hex()
    assert len(av_wire) > 100, len(av_wire)

    # Real v25 CreateActor packet: decode all 238 bytes exactly.
    real = parse_outer(_V25_REAL_CREATE_PC)
    assert real.outer_id == GSCN_LOGIN_PROTOCOL
    assert real.nested_id == CREATE_ACTOR_VITAL and real.nested_version == 8
    op, has_actor, actor_wire = parse_create_actor(real)
    assert op == 1 and has_actor == 1 and len(actor_wire) == 214
    actor = decode_create_actor_data_ex(actor_wire)
    assert actor["name"] == "test01"
    assert actor["second_name"] == "test001"
    assert actor["selector"] == 0
    assert actor["identity_lo"] == 0 and actor["identity_hi"] == 0
    assert actor["avatar_mask"] == 0xFFFFFFFF
    assert actor["avatar_u32"][0x54] == V123_BLADE_TEMPLATE
    assert actor["avatar_u32"][0x58] == V123_BLADE_TEMPLATE
    assert actor["f4"] == 0 and actor["f8"] == 0

    # The first real CreateActor submit gets exactly one binary-justified success/update echo.
    out = st.dispatch(real)
    assert [x[0] for x in out] == ["CREATE_ACTOR_LOGIN_ECHO_ONCE"], out
    rsp_pc = out[0][1]
    rsp = parse_outer(rsp_pc)
    assert rsp.outer_id == GSCN_LOGIN_PROTOCOL
    assert rsp.outer_version == 0 and rsp.outer_mask == 2 and rsp.vital_count == 1
    assert rsp.nested_id == CREATE_ACTOR_VITAL and rsp.nested_version == 8
    rop, rhas, ractor = parse_create_actor(rsp)
    assert rop == 1 and rhas == 1 and ractor == actor_wire

    # Duplicate create must never be replayed.
    assert st.dispatch(real) == []

    # V34 world bootstrap wire regression.
    wi_pc, wi_frame = make_login_get_world_info_minimal()
    wi_parsed = parse_outer(wi_pc)
    assert wi_parsed.outer_id == GSCN_LOGIN_PROTOCOL
    assert wi_parsed.nested_id == GET_WORLD_INFO_VITAL
    assert wi_parsed.nested_version == 0
    assert wi_pc.endswith(bytes.fromhex("0B 01 14 FF FF FF FF 48 00 00 00 00 0F 00 00"))
    assert snappy_raw_decompress(wi_frame[8:]) == wi_pc

    # StartGame gets exactly one binary-derived ActorAttr bootstrap response.
    sg = parse_outer(_synthetic_start_game_pc(0))
    assert parse_start_game_req(sg) == 0
    sg_out = st.dispatch(sg)
    assert [x[0] for x in sg_out] == [
        "START_GAME_RES_ACTORATTR_ONCE",
        "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
    ], sg_out
    assert st.start_game_seen and st.start_game_reply_sent and not st.world_info_sent
    sg_rsp = parse_outer(sg_out[0][1])
    assert sg_rsp.outer_id == GSCN_LOGIN_PROTOCOL
    assert sg_rsp.nested_id == START_GAME_RES and sg_rsp.nested_version == 3
    # v33: validate ActorAttr BasicAttr mask 0x000C + AvatarAttr payload structurally.
    sp = sg_rsp.nested_payload
    assert sp[:12] == bytes.fromhex("08 00 05 00 0B 02 0F 03 00 0F 00 00")
    assert bytes.fromhex("0B 04 12 AD 12") in sp
    assert bytes.fromhex("12 A0 16") in sp
    av_marker = bytes.fromhex("12 A0 16") + make_avatar_attr_from_preset()[:16]
    assert av_marker in sp, (av_marker.hex(), sp.hex())
    assert bytes.fromhex("26 FF FF FF FF") in sp
    assert bytes.fromhex("12 67 20 0B 01 32 00 00 00 00 00 00 00 00 0B FF") in sp
    p0_row=_v112_test_rows()[0]
    assert (
        p0_row[0]==V129_QUEST_ACTOR_INDEX and
        p0_row[1]==V129_QUEST_ACTOR_TEMPLATE and
        p0_row[2:5]==(
            V129_PLAYER_X-100.0,V129_PLAYER_Y,V129_PLAYER_Z
        )
    )
    expected_player_movement=make_movement_attr_minimal(
        0,0,V135_PLAYER_X,V135_PLAYER_Y,V135_PLAYER_Z
    )
    assert u16tag(0x12,MOVEMENT_ATTR)+expected_player_movement in sp
    frozen_v134_player_movement=make_movement_attr_minimal(
        0,0,V134_PLAYER_X,V134_PLAYER_Y,V134_PLAYER_Z
    )
    frozen_v134_start_pc,_=make_login_start_game_res_actorattr(
        0,V134_PLAYER_X,V134_PLAYER_Y,V134_PLAYER_Z
    )
    # V135 changes only the local MovementAttr Y float from frozen V134.
    # Actor, inventory, cash, appearance, X/Z/heading, zero-target Teleport,
    # population, quest packets, and every other bootstrap byte are inherited.
    assert frozen_v134_start_pc.count(frozen_v134_player_movement)==1
    assert frozen_v134_start_pc.replace(
        frozen_v134_player_movement,expected_player_movement,1
    )==sg_out[0][1]
    v135_start_diff=[
        (i,old,new)
        for i,(old,new) in enumerate(zip(frozen_v134_start_pc,sg_out[0][1]))
        if old!=new
    ]
    assert v135_start_diff==[(222,0xC0,0xE0),(223,0x2D,0x30)]
    # Position is the only changed MovementAttr value; heading and three
    # auxiliary constructor-default floats remain exact zero.
    assert sp.count(bytes([0x2A,0,0,0,0])) >= 4
    empty_backpack_wire = make_backpack_attr_empty()
    assert empty_backpack_wire == bytes.fromhex(
        "0B FF 32 00 00 00 00 00 00 00 00 0F 00 00 0F 00 00 0B 00"
    )
    item_wire = make_item_attr_adventure_key()
    expected_item_wire = bytes.fromhex(
        "32 01 00 00 00 00 00 00 00 14 41 AC 27 00 0F 01 00 "
        "0F 00 00 08 00 08 FF 0B 00"
    )
    assert item_wire == expected_item_wire and len(item_wire) == 26
    cask_wire = make_item_attr_camouflage_cask()
    expected_cask_wire = (
        qwordtag(0x32, 2) + u32tag(0x14, 2400901)
        + u16tag(0x0F, 1) + u16tag(0x0F, 1)
        + u8tag(0x08, 0) + u8tag(0x08, 0xFF) + u8tag(0x0B, 0)
    )
    assert cask_wire == expected_cask_wire and len(cask_wire) == 26
    stack_source_wire = make_item_attr_adventure_key_stack_source()
    expected_stack_source_wire = (
        qwordtag(0x32, 3) + u32tag(0x14, 2600001)
        + u16tag(0x0F, 1) + u16tag(0x0F, 2)
        + u8tag(0x08, 0) + u8tag(0x08, 0xFF) + u8tag(0x0B, 0)
    )
    assert stack_source_wire == expected_stack_source_wire
    assert len(stack_source_wire) == 26
    v122_backpack_wire = make_backpack_attr_three_items()
    expected_v122_backpack_wire = (
        bytes.fromhex("0B FF 32 00 00 00 00 00 00 00 00 0F 03 00")
        + expected_item_wire
        + expected_cask_wire
        + expected_stack_source_wire
        + bytes.fromhex(
            "0F 03 00 32 01 00 00 00 00 00 00 00 "
            "32 02 00 00 00 00 00 00 00 "
            "32 03 00 00 00 00 00 00 00 0B 01"
        )
    )
    assert v122_backpack_wire == expected_v122_backpack_wire
    assert len(v122_backpack_wire) == 124
    v119_backpack_wire = v122_backpack_wire[:-1] + bytes([0])
    assert v119_backpack_wire.endswith(bytes.fromhex("0B 00"))
    assert v122_backpack_wire.endswith(bytes.fromhex("0B 01"))
    assert [
        index for index, (before, after) in enumerate(
            zip(v119_backpack_wire, v122_backpack_wire)
        ) if before != after
    ] == [123]
    assert v119_backpack_wire[123] == 0
    assert v122_backpack_wire[123] == V120_BACKPACK_BASE_RANGE_MASK == 1
    assert v122_backpack_wire[:14] == bytes.fromhex(
        "0B FF 32 00 00 00 00 00 00 00 00 0F 03 00"
    )
    assert v122_backpack_wire[14:40] == expected_item_wire
    assert v122_backpack_wire[40:66] == expected_cask_wire
    assert v122_backpack_wire[66:92] == expected_stack_source_wire
    assert [struct.unpack_from('<H', wire, 18)[0] for wire in (
        expected_item_wire, expected_cask_wire, expected_stack_source_wire,
    )] == [V103_ITEM_SLOT, V110_CASK_SLOT, V111_STACK_SOURCE_SLOT] == [0, 1, 2]
    assert v122_backpack_wire[92:95] == u16tag(0x0F, 3)
    assert [
        struct.unpack_from('<Q', v122_backpack_wire, offset)[0]
        for offset in (96, 105, 114)
    ] == [V103_ITEM_SEQUENCE, V110_CASK_SEQUENCE, V111_STACK_SOURCE_SEQUENCE]

    blade_wire = make_item_attr_create_character_blade()
    expected_blade_wire = bytes.fromhex(
        "32 04 00 00 00 00 00 00 00 14 C2 91 21 00 0F 01 00 "
        "0F 03 00 08 00 08 FF 0B 00"
    )
    assert blade_wire == expected_blade_wire and len(blade_wire) == 26
    assert struct.unpack_from('<I', blade_wire, 10)[0] == V123_BLADE_TEMPLATE
    assert struct.unpack_from('<H', blade_wire, 18)[0] == V123_BLADE_SLOT
    assert blade_wire[22:24] == bytes.fromhex('08 FF')
    # x86 masks a byte shift count to five bits: +0x39=FF selects bit31.
    # Lookup 0x5A1630 first requires signed dword>0, so its allowed values have
    # no bit31 and cannot select this unequipped blade as the returned qword.
    assert (1 << (blade_wire[23] & 0x1F)) == 0x80000000
    assert ((1 << (blade_wire[23] & 0x1F)) & 0x7FFFFFFF) == 0
    backpack_wire = make_backpack_attr_four_items()
    expected_v123_from_v122 = (
        v122_backpack_wire[:11]
        + u16tag(0x0F, 4)
        + v122_backpack_wire[14:92]
        + expected_blade_wire
        + u16tag(0x0F, 4)
        + v122_backpack_wire[95:122]
        + qwordtag(0x32, V123_BLADE_SEQUENCE)
        + v122_backpack_wire[122:]
    )
    assert backpack_wire == expected_v123_from_v122
    assert len(backpack_wire) == 159 == len(v122_backpack_wire) + 35
    assert backpack_wire[:11] == v122_backpack_wire[:11]
    assert backpack_wire[11:14] == u16tag(0x0F, 4)
    assert backpack_wire[14:92] == v122_backpack_wire[14:92]
    assert backpack_wire[92:118] == expected_blade_wire
    assert backpack_wire[118:121] == u16tag(0x0F, 4)
    assert [
        struct.unpack_from('<Q', backpack_wire, offset)[0]
        for offset in (122, 131, 140, 149)
    ] == [1, 2, 3, 4]
    assert backpack_wire[157:] == bytes.fromhex("0B 01")
    occupied_base_slots = {
        V103_ITEM_SLOT, V110_CASK_SLOT, V111_STACK_SOURCE_SLOT,
        V123_BLADE_SLOT,
    }
    predicted_base_free_slots = (
        V120_BACKPACK_BASE_SLOT_COUNT - len(occupied_base_slots)
    )
    assert predicted_base_free_slots == 36
    assert min(predicted_base_free_slots, V120_SHOP_BUY_CELL_CAP) == 18
    assert u16tag(0x12, ITEM_ATTR) not in backpack_wire
    assert backpack_wire != empty_backpack_wire
    backpack_marker = u16tag(0x12, BACKPACK_ATTR) + backpack_wire
    assert sp.count(backpack_marker) == 1
    backpack_offset = sp.index(backpack_marker) + len(u16tag(0x12, BACKPACK_ATTR))
    reconstructed_v122_sp = (
        sp[:backpack_offset]
        + v122_backpack_wire
        + sp[backpack_offset + len(backpack_wire):]
    )
    assert len(sp) == len(reconstructed_v122_sp) + 35
    assert sp[:backpack_offset] == reconstructed_v122_sp[:backpack_offset]
    assert (
        sp[backpack_offset + len(backpack_wire):]
        == reconstructed_v122_sp[backpack_offset + len(v122_backpack_wire):]
    )
    # Preserve the independent StartGameRes-derived trailing mask.
    assert sp.endswith(bytes.fromhex("0B 00"))
    assert st.dispatch(sg) == []  # duplicate StartGame suppression

    # Snappy frame roundtrip for the CreateActor response.
    fr = frame_pc(rsp_pc)
    magic, clen = struct.unpack_from("<II", fr, 0)
    assert magic == MAGIC and clen == len(fr) - 8
    assert snappy_raw_decompress(fr[8:]) == rsp_pc

    # V36 scene bootstrap plus V116's statically proven cash field. ActorAttr
    # carries BasicAttr mask 0x030C, own mask bit 0x800, and qword cash=10000.
    aa = make_actor_attr_minimal(0, 0, 1, 0)
    assert bytes([0x12, 0x0C, 0x03]) in aa, aa.hex()
    assert bytes([0x12, 0x01, 0x00]) in aa, aa.hex()
    assert aa.endswith(bytes.fromhex(
        "32 00 08 00 00 00 00 00 00 05 01 32 10 27 00 00 00 00 00 00"
    )), aa.hex()
    v115_aa = aa[:-20] + bytes.fromhex(
        "32 00 00 00 00 00 00 00 00 05 01"
    )
    assert len(aa) == len(v115_aa) + 9
    assert [i for i, (old, new) in enumerate(zip(v115_aa, aa)) if old != new] == [
        len(v115_aa) - 9
    ]
    tp_pc, tp_fr = make_login_teleport(1, 0)
    expected_tp_pc = bytes.fromhex(
        "12 3A 45 14 00 00 00 00 08 00 0B 02 12 01 00 12 A2 25 "
        "0B 04 0B 02 0B 01 12 01 00 32 00 00 00 00 00 00 00 00 "
        "0B 00 0B 00 2A 00 00 00 00 2A 00 00 00 00 2A 00 00 00 00 "
        "0B 00 0B 00 0F 00 00"
    )
    assert tp_pc == expected_tp_pc and len(tp_pc) == 62
    assert sg_out[1][1] == expected_tp_pc and sg_out[1][2] == tp_fr
    tp = parse_outer(tp_pc)
    assert tp.outer_id == GSCN_LOGIN_PROTOCOL and tp.nested_id == TELEPORT_VITAL and tp.nested_version == 4
    ctp = Cursor(tp.nested_payload)
    assert ctp.u8(0x0B) == 2
    assert ctp.u8(0x0B) == 1
    assert ctp.u16(0x12) == 1
    assert ctp.raw8(0x32) == b"\x00" * 8
    assert ctp.u8(0x0B) == 0 and ctp.u8(0x0B) == 0
    parsed_xyz = []
    for _ in range(3):
        ctp.tag(0x2A)
        ctp.need(4)
        parsed_xyz.append(struct.unpack_from("<f", ctp.data, ctp.p)[0])
        ctp.p += 4
    assert parsed_xyz == [0.0,0.0,0.0]
    assert ctp.u8(0x0B) == 0 and ctp.u8(0x0B) == 0 and ctp.u16(0x0F) == 0
    assert ctp.remain() == 0
    assert snappy_raw_decompress(tp_fr[8:]) == tp_pc

    # V43 targeted remote NPC spawn: this is NOT the inherited VitalData list.
    # It must use RuntimeRes derived mask bit 0x02 followed by u16 actor count.
    npc_packets = make_port_royal_npc_single_packets()
    npc_pc, npc_fr = npc_packets[0][2], npc_packets[0][3]
    expected_prefix = (
        u16tag(0x12, GSCN_RUNTIME_PROTOCOL_RES)
        + u32tag(0x14, 0)
        + u8tag(0x08, 4)
        + u8tag(0x0B, 0)
        + u8tag(0x0B, 2)
        + u16tag(0x12, 1)
        + u8tag(0x0B, 4)
        + qwordtag(0x32, 0x1001)
        + u8tag(0x0B, 2)
        + u16tag(0x12, NPC_ATTR)
    )
    assert npc_pc.startswith(expected_prefix), npc_pc[:len(expected_prefix)+16].hex()
    # V64 NPCAttr: common identity, BasicAttr HP(+0x44/+0x48)=100/100 + scene 1/seq0,
    # then own mask1/template1. The 0x030C BasicAttr mask is serializer-backed.
    npc_attr_wire = make_npc_attr(1, 0x1001, 1, 0)
    assert (u16tag(0x12, 0x030C) + u32tag(0x14, 100) + u32tag(0x14, 100)
            + u16tag(0x12, 1) + qwordtag(0x32, 0)) in npc_attr_wire
    assert u16tag(0x12, 0x0380) not in npc_attr_wire
    assert npc_attr_wire.endswith(u8tag(0x0B, 0x01) + u16tag(0x12, 1)), npc_attr_wire.hex()
    assert u16tag(0x12, MOVEMENT_ATTR) in npc_pc
    assert npc_pc.count(struct.pack("<f", 931.0)) >= 1
    assert len(npc_packets) == 6
    for template_id, actor_identity, one_pc, one_fr in npc_packets:
        assert make_npc_attr(template_id, actor_identity, 1, 0) in one_pc
        assert one_pc.count(struct.pack("<f", 931.0)) >= 1
        assert snappy_raw_decompress(one_fr[8:]) == one_pc
    if verbose:
        print("[SELFTEST] PASS: legacy remote-actor serializer regression on Port Royal ground Z=931")

    # Exact empty RuntimeRes: constructor-default RuntimeRes has TWO masks:
    # inherited VitalData-list mask 0, then RuntimeRes-extension mask 0.
    # UpdateNPCAppear is intentionally NOT exercised here or at runtime; its
    # full range was already exhausted in earlier RE and is not a spawn path.

    hb_pc, hb_fr = make_runtime_res_empty_exact()
    assert hb_pc == bytes.fromhex("12 9D 6E 14 00 00 00 00 08 04 0B 00 0B 00")
    assert snappy_raw_decompress(hb_fr[8:]) == hb_pc

    # V37 watchdog regression: after scene teleport, the first observed RuntimeReq
    # receives one immediate exact-empty RuntimeRes ACK, then duplicates are left
    # to the periodic keepalive worker instead of generating an ACK flood.
    rst = GameSessionState("localtest")
    rst.teleport_sent = True
    runtime_req_pc = bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 02 00 "
        "12 A2 25 0B 04 0B 02 0B 00 0B 00 0B 00 0F 00 00 "
        "12 90 2A 0B 00 2A 00 00 00 00 2A 00 00 00 00 "
        "2A 00 00 C0 68 44 2A 00 00 00 00 0B 00 0B 00"
    )
    rp = parse_outer(runtime_req_pc)
    assert rp.outer_id == GSCN_RUNTIME_PROTOCOL_REQ and rp.vital_count == 2
    acts = rst.dispatch(rp)
    assert len(acts) == 3
    assert acts[0][0] == "RUNTIME_RES_ACK_FIRST_REQ"
    assert acts[1][0] == "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE"
    assert acts[2][0] == "V100_MUSIC_CONTROL_CURRENT_SCENE"
    assert acts[0][1] == hb_pc
    assert rst.runtime_ack_sent and rst.welcome_message_sent and rst.current_scene_music_sent and not rst.npc_spawn_sent

    # V99 regression: preserve V98 and add one serializer-exact system message.
    msg_pc,msg_frame=make_show_message("Pirate Force local server online")
    expected_msg=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+u32tag(0x14,0)+u8tag(0x08,4)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,SHOW_MESSAGE_VITAL)+
        u8tag(0x0B,0)+wstr_tag("Pirate Force local server online")+u8tag(0x0B,0)
    )
    assert msg_pc==expected_msg
    assert snappy_raw_decompress(msg_frame[8:])==msg_pc
    assert acts[1][1]==msg_pc and acts[1][2]==msg_frame
    music_pc,music_frame=make_music_control_current_scene()
    expected_music=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+u32tag(0x14,0)+u8tag(0x08,4)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,MUSIC_CONTROL_VITAL)+
        u8tag(0x0B,0)+astr_tag("")+u8tag(0x08,1)+u8tag(0x0B,0)
    )
    assert music_pc==expected_music
    assert snappy_raw_decompress(music_frame[8:])==music_pc
    assert acts[2][1]==music_pc and acts[2][2]==music_frame
    assert rst.dispatch(rp)==[]

    # V102 exact runtime capture: CheckSecondPwdVital carries result=0, u32=0,
    # and a 32-byte uppercase ANSI digest. The handler-proven OK response keeps
    # the constructor-default u32/string and changes only result to 1.
    check_req_pc=bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
        "98 4B 0B 00 08 00 19 00 00 00 00 44 20 00 00 00 "
        "37 44 30 31 34 45 35 34 31 41 46 41 41 34 33 32 "
        "36 37 43 41 38 30 42 43 43 42 43 33 46 44 36 42"
    )
    check_parsed=parse_outer(check_req_pc)
    assert check_parsed.outer_id==GSCN_RUNTIME_PROTOCOL_REQ
    assert check_parsed.nested_id==CHECK_SECOND_PWD_VITAL
    check_acts=rst.dispatch(check_parsed)
    assert len(check_acts)==1 and check_acts[0][0]=="V110_CHECK_SECOND_PASSWORD_OK"
    check_ok_pc,check_ok_frame=make_check_second_password_success()
    expected_check_ok=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+u32tag(0x14,0)+u8tag(0x08,4)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,CHECK_SECOND_PWD_VITAL)+
        u8tag(0x0B,0)+u8tag(0x08,1)+u32tag(0x19,0)+astr_tag("")+
        u8tag(0x0B,0)
    )
    assert check_ok_pc==expected_check_ok
    assert check_acts[0][1]==check_ok_pc and check_acts[0][2]==check_ok_frame
    assert snappy_raw_decompress(check_ok_frame[8:])==check_ok_pc
    assert b"7D014E541AFAA43267CA80BCCBC3FD6B" not in check_ok_pc

    # V111 preserves the exact V104 request decoder and V108 stateful response,
    # then adds one occupied-slot stack merge supported by the client producer.
    # The recovered registry algorithm is the
    # 16-bit sum of each signed ASCII byte multiplied by its one-based index.
    # ItemOperateVital itself remains a different class from the Req/Res wire.
    def protocol_name_id(name: str) -> int:
        return sum((index + 1) * ord(value) for index, value in enumerate(name)) & 0xFFFF

    assert protocol_name_id("ItemOperateVital") == ITEM_OPERATE_VITAL == 0x36FE
    assert protocol_name_id("UseItemVital") == USE_ITEM_VITAL == 0x1F4F
    assert protocol_name_id("ItemOperateVitalReq") == ITEM_OPERATE_REQ_VITAL == 0x4BED
    assert protocol_name_id("ItemOperateVitalRes") == ITEM_OPERATE_RES_VITAL == 0x4C13
    capst=GameSessionState("v111-stack-merge")
    capst.teleport_sent=True
    capst.runtime_ack_sent=True
    capst.welcome_message_sent=True
    capst.current_scene_music_sent=True
    capst.npc_spawn_sent=True
    merge_probe=bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 "
        "ED 4B 0B 00 0B 04 14 00 00 00 00 32 03 00 00 00 "
        "00 00 00 00"
    )
    merge_parsed=parse_outer(merge_probe)
    assert merge_parsed.nested_id==ITEM_OPERATE_REQ_VITAL
    assert NAMES[merge_parsed.nested_id]=="ItemOperateVitalReq"
    assert parse_item_operate_req(merge_parsed)==(4,0,3)
    assert merge_parsed.nested_version==0
    merge_actions=capst.dispatch(merge_parsed)
    assert len(merge_actions)==1
    assert merge_actions[0][0]=="V111_ITEM_STACK_ID3_INTO_ID1_QTY2_SUCCESS"
    expected_merged_item=(
        qwordtag(0x32,1)+u32tag(0x14,V103_ITEM_TEMPLATE)+
        u16tag(0x0F,2)+u16tag(0x0F,0)+u8tag(0x08,0)+
        u8tag(0x08,0xFF)+u8tag(0x0B,0)
    )
    expected_merge_bag=(
        u8tag(0x0B,0xFF)+qwordtag(0x32,0)+u16tag(0x0F,1)+
        expected_merged_item+u16tag(0x0F,1)+qwordtag(0x32,3)
    )
    assert len(expected_merged_item)==26
    assert len(expected_merge_bag)==52
    expected_merge_payload=(
        u8tag(0x08,0)+u8tag(0x0B,1)+expected_merge_bag+u8tag(0x08,0)
    )
    expected_merge_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+u32tag(0x14,0)+u8tag(0x08,4)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_RES_VITAL)+
        u8tag(0x0B,2)+expected_merge_payload+u8tag(0x0B,0)
    )
    merge_pc,merge_frame=make_item_operate_stack_merge_success()
    assert len(expected_merge_payload)==58 and len(expected_merge_pc)==80
    assert merge_actions[0][1]==merge_pc==expected_merge_pc
    merge_response_parsed=parse_outer(merge_pc)
    assert merge_response_parsed.nested_id==ITEM_OPERATE_RES_VITAL
    assert merge_response_parsed.nested_version==2
    assert merge_actions[0][2]==merge_frame
    assert snappy_raw_decompress(merge_frame[8:])==merge_pc
    assert capst.stack_merge_count==1 and not capst.stack_source_present
    assert capst.item_quantity==2 and capst.item_slot==0
    assert capst.dispatch(merge_parsed)==[]

    # After merging, stateful movement must retain quantity two.
    move_probe=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,4)+u32tag(0x14,3)+qwordtag(0x32,1)
    )
    assert parse_item_operate_req(parse_outer(move_probe))==(4,3,1)
    move_actions=capst.dispatch(parse_outer(move_probe))
    assert len(move_actions)==1
    assert move_actions[0][0]=="V111_ITEM_MOVE_ID1_SLOT0_TO_SLOT3_SUCCESS"
    moved_pc,_=make_item_operate_move_delta_success(3,2)
    assert move_actions[0][1]==moved_pc
    assert u16tag(0x0F,2) in moved_pc
    assert capst.item_move_count==1 and capst.item_slot==3
    assert capst.item_quantity==2

    unsupported=GameSessionState("unsupported-item-op")
    unsupported.teleport_sent=True
    unsupported.runtime_ack_sent=True
    unsupported.welcome_message_sent=True
    unsupported.current_scene_music_sent=True
    unsupported.npc_spawn_sent=True
    wrong_item_probe=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,3)+u32tag(0x14,1)+qwordtag(0x32,1)
    )
    assert parse_item_operate_req(parse_outer(wrong_item_probe))==(3,1,1)
    assert unsupported.dispatch(parse_outer(wrong_item_probe))==[]

    # V123 exact equip-from-bag capture. Item activation event code 2 reaches
    # 0x5A64A0. The selected blade's data row has n_EQUIPSLOT=0x4000;
    # 0x5A6814-0x5A683F maps it to wire dword 8 or alternate 16. Call 0x4DF1C0
    # supplies the selected ItemAttr identity qword and producer 0x59F800 emits
    # operation 5. +0x39 correctly remains FF for this unequipped bag item.
    default_equip_value32=8
    equip_item_identity=V123_BLADE_SEQUENCE
    equipment_probe=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,default_equip_value32)+qwordtag(0x32,equip_item_identity)
    )
    assert equipment_probe==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 '
        'ED 4B 0B 00 0B 05 14 08 00 00 00 32 04 00 00 00 '
        '00 00 00 00'
    )
    assert len(equipment_probe)==36
    equipment_parsed=parse_outer(equipment_probe)
    assert equipment_parsed.nested_version==0
    assert equipment_parsed.vital_count==1
    assert parse_item_operate_req(equipment_parsed)==(
        V123_EQUIP_FROM_BAG_OPERATION,default_equip_value32,equip_item_identity,
    )
    equipment_state=GameSessionState('v123-equipment-capture')
    equipment_state.teleport_sent=True
    equipment_state.runtime_ack_sent=True
    equipment_state.welcome_message_sent=True
    equipment_state.current_scene_music_sent=True
    equipment_state.npc_spawn_sent=True
    inventory_state_before=(
        equipment_state.item_slot,equipment_state.item_quantity,
        equipment_state.probe_item_slot,equipment_state.stack_source_slot,
        equipment_state.stack_source_present,equipment_state.stack_merge_count,
        equipment_state.current_cash,
    )
    assert equipment_state.dispatch(equipment_parsed)==[]
    assert equipment_state.equipment_capture_count==1
    assert equipment_state.equipment_last_value32_mapped==default_equip_value32
    assert equipment_state.equipment_last_item_identity==equip_item_identity
    assert any(
        event==(
            'v123_equip_from_bag_op5_id4_capture_no_reply_'
            'value32_mapped_8'
        )
        for event in equipment_state.events
    )
    assert inventory_state_before==(
        equipment_state.item_slot,equipment_state.item_quantity,
        equipment_state.probe_item_slot,equipment_state.stack_source_slot,
        equipment_state.stack_source_present,equipment_state.stack_merge_count,
        equipment_state.current_cash,
    )
    # The exact alternate producer branch is the same identity with dword 16.
    alternate_equip_value32=16
    second_equipment_probe=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,alternate_equip_value32)+qwordtag(0x32,equip_item_identity)
    )
    assert second_equipment_probe==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 '
        'ED 4B 0B 00 0B 05 14 10 00 00 00 32 04 00 00 00 '
        '00 00 00 00'
    )
    assert equipment_state.dispatch(parse_outer(second_equipment_probe))==[]
    assert equipment_state.equipment_capture_count==2
    assert equipment_state.equipment_last_value32_mapped==alternate_equip_value32
    assert equipment_state.equipment_last_item_identity==equip_item_identity
    assert any(
        event==(
            'v123_equip_from_bag_op5_id4_capture_no_reply_'
            'value32_mapped_16'
        )
        for event in equipment_state.events
    )
    unsupported_equipment_probes=(
        # Exact op5 body, but an unproven nested version.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,1)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,default_equip_value32)+qwordtag(0x32,equip_item_identity),
        # Exact vital, but an outer count other than the proven singleton.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,2)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,default_equip_value32)+qwordtag(0x32,equip_item_identity),
        # Producer consumes row mask 0x4000 but emits mapped dword 8 or 16.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,0x4000)+qwordtag(0x32,equip_item_identity),
        # Operation 5 for a different item identity is outside V123.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,V123_EQUIP_FROM_BAG_OPERATION)+
        u32tag(0x14,default_equip_value32)+qwordtag(0x32,5),
        # The same body with the operation-6 current-equipped lane is unsupported.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,ITEM_OPERATE_REQ_VITAL)+
        u8tag(0x0B,0)+u8tag(0x0B,6)+u32tag(0x14,default_equip_value32)+
        qwordtag(0x32,equip_item_identity),
        # Exact prefix plus one trailing field must fail the exact parser.
        equipment_probe+u8tag(0x08,0),
    )
    for unsupported_equipment_probe in unsupported_equipment_probes:
        assert equipment_state.dispatch(
            parse_outer(unsupported_equipment_probe)
        )==[]
    assert equipment_state.equipment_capture_count==2
    assert equipment_state.equipment_last_value32_mapped==alternate_equip_value32
    assert equipment_state.equipment_last_item_identity==equip_item_identity

    # V129 uses the serializer-exact action-6 OpenAcceptUI path for the exact
    # level-1 quest-3020/P0 data relationship.
    assert protocol_name_id("QuestOperateVital") == QUEST_OPERATE_VITAL == 0x3E34
    assert V129_QUEST_ACTOR_ID==0x2001
    assert V129_QUEST_ID==3020
    assert V129_QUEST_ACTOR_INDEX==0 and V129_QUEST_ACTOR_TEMPLATE==1
    quest_accept_ui_pc,quest_accept_ui_frame=make_quest3020_action6_accept_ui()
    expected_quest_accept_ui_pc=bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E "
        "0B 03 12 CC 0B 08 00 08 06 14 00 00 00 00 "
        "32 01 20 00 00 00 00 00 00 05 00 0B 00"
    )
    assert (
        quest_accept_ui_pc==expected_quest_accept_ui_pc
        and len(quest_accept_ui_pc)==45
    )
    frozen_v128_quest_accept_ui_pc=bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E "
        "0B 03 12 F3 00 08 00 08 06 14 00 00 00 00 "
        "32 5C 20 00 00 00 00 00 00 05 00 0B 00"
    )
    assert [
        (i,old,new)
        for i,(old,new) in enumerate(zip(
            frozen_v128_quest_accept_ui_pc,quest_accept_ui_pc
        )) if old!=new
    ]==[(21,0xF3,0xCC),(22,0x00,0x0B),(33,0x5C,0x01)]
    assert snappy_raw_decompress(quest_accept_ui_frame[8:])==quest_accept_ui_pc
    parsed_accept_ui=parse_outer(quest_accept_ui_pc)
    assert parsed_accept_ui.nested_version==3
    # parse_outer deliberately cannot infer the end of arbitrary nested
    # RuntimeRes payloads; remove the proven trailing derived mask for this
    # serializer-only assertion.
    parsed_accept_ui.nested_payload=parsed_accept_ui.nested_payload[:-2]
    assert parse_quest_operate_vital(parsed_accept_ui)=={
        'quest_id':V129_QUEST_ID,
        'field_u8_16':0,
        'field_u8_17':V129_QUEST_OPEN_ACCEPT_UI_ACTION,
        'field_u32_18':0,
        'field_qword_20':V129_QUEST_ACTOR_ID,
        'field_u8_28':0,
    }

    quest_conversation_pc,quest_conversation_frame=(
        make_npc_conversation_quest3020()
    )
    assert quest_conversation_pc==bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 D8 31 "
        "0B 00 32 01 20 00 00 00 00 00 00 0F 01 00 "
        "12 CC 0B 08 00 0B 00"
    )
    assert len(quest_conversation_pc)==39
    assert snappy_raw_decompress(
        quest_conversation_frame[8:]
    )==quest_conversation_pc
    assert quest_conversation_pc.count(u16tag(0x12,V129_QUEST_ID))==1
    try:
        make_npc_conversation_quest3020(V112_SHOP_TRIGGER_ACTOR_ID)
    except ValueError:
        pass
    else:
        raise AssertionError('V134 accepted q3020 conversation for non-P0 actor')

    # The selected q3020 row is statically proven to produce op1. Its use as
    # the trigger for action6 is intentionally bounded as the V134 integration
    # hypothesis; only the exact subsequent op2->action1 link is live-proven.
    quest_op1_pc=_synthetic_quest_operate_pc(
        V129_QUEST_ID,1,0,0,0,0
    )
    assert quest_op1_pc==bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E "
        "0B 03 12 CC 0B 08 01 08 00 14 00 00 00 00 "
        "32 00 00 00 00 00 00 00 00 05 00"
    ) and len(quest_op1_pc)==43
    quest_op1=parse_outer(quest_op1_pc)
    assert parse_quest_operate_vital(quest_op1)=={
        'quest_id':V129_QUEST_ID,
        'field_u8_16':1,
        'field_u8_17':0,
        'field_u32_18':0,
        'field_qword_20':0,
        'field_u8_28':0,
    }
    quest_request_pc=_synthetic_quest_operate_pc(V129_QUEST_ID,2,0,0,0,0)
    expected_quest_request_pc=bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E "
        "0B 03 12 CC 0B 08 02 08 00 14 00 00 00 00 "
        "32 00 00 00 00 00 00 00 00 05 00"
    )
    assert quest_request_pc==expected_quest_request_pc and len(quest_request_pc)==43
    frozen_v128_quest_request_pc=bytes.fromhex(
        "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E "
        "0B 03 12 F3 00 08 02 08 00 14 00 00 00 00 "
        "32 00 00 00 00 00 00 00 00 05 00"
    )
    assert [
        (i,old,new)
        for i,(old,new) in enumerate(zip(frozen_v128_quest_request_pc,quest_request_pc))
        if old!=new
    ]==[(21,0xF3,0xCC),(22,0x00,0x0B)]
    quest_request=parse_outer(quest_request_pc)
    assert quest_request.nested_version==3
    assert parse_quest_operate_vital(quest_request)=={
        'quest_id':V129_QUEST_ID,
        'field_u8_16':2,
        'field_u8_17':0,
        'field_u32_18':0,
        'field_qword_20':0,
        'field_u8_28':0,
    }

    quest_accept_pc,quest_accept_frame=(
        make_quest3020_action1_accept_success()
    )
    expected_quest_accept_pc=bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E "
        "0B 03 12 CC 0B 08 00 08 01 14 00 00 00 00 "
        "32 01 20 00 00 00 00 00 00 05 00 0B 00"
    )
    assert quest_accept_pc==expected_quest_accept_pc
    assert len(quest_accept_pc)==45
    frozen_v128_quest_accept_pc=bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E "
        "0B 03 12 F3 00 08 00 08 01 14 00 00 00 00 "
        "32 5C 20 00 00 00 00 00 00 05 00 0B 00"
    )
    assert [
        (i,old,new)
        for i,(old,new) in enumerate(zip(frozen_v128_quest_accept_pc,quest_accept_pc))
        if old!=new
    ]==[(21,0xF3,0xCC),(22,0x00,0x0B),(33,0x5C,0x01)]
    assert snappy_raw_decompress(quest_accept_frame[8:])==quest_accept_pc
    parsed_accept=parse_outer(quest_accept_pc)
    assert (
        parsed_accept.outer_id==GSCN_RUNTIME_PROTOCOL_RES and
        parsed_accept.outer_version==4 and
        parsed_accept.outer_mask==0x02 and
        parsed_accept.vital_count==1 and
        parsed_accept.nested_id==QUEST_OPERATE_VITAL and
        parsed_accept.nested_version==3 and
        parsed_accept.nested_payload[-2:]==u8tag(0x0B,0)
    )
    parsed_accept.nested_payload=parsed_accept.nested_payload[:-2]
    assert parse_quest_operate_vital(parsed_accept)=={
        'quest_id':V129_QUEST_ID,
        'field_u8_16':0,
        'field_u8_17':V129_QUEST_ACCEPT_SUCCESS_ACTION,
        'field_u32_18':0,
        'field_qword_20':V129_QUEST_ACTOR_ID,
        'field_u8_28':0,
    }

    # Exact op1 before a P0 conversation is captured but receives no response.
    quest_preoffer_state=GameSessionState('v134-quest-preconversation')
    quest_preoffer_state.teleport_sent=True
    quest_preoffer_state.runtime_ack_sent=True
    quest_preoffer_state.welcome_message_sent=True
    quest_preoffer_state.current_scene_music_sent=True
    assert quest_preoffer_state.dispatch(quest_op1)==[]
    assert quest_preoffer_state.quest3020_op1_capture_count==1
    assert not quest_preoffer_state.quest3020_accept_ui_sent
    assert any(
        event==(
            'v134_q3020_exact_op1_wrong_sequence_no_reply_'
            'conversation_sent_0_action6_sent_0_action1_sent_0'
        ) for event in quest_preoffer_state.events
    )

    # Conversation -> exact op1 queues action6 once. This transition is the
    # bounded hypothesis and is never described as an authentic server result.
    quest_capture_state=GameSessionState('v134-quest-handshake')
    quest_capture_state.teleport_sent=True
    quest_capture_state.runtime_ack_sent=True
    quest_capture_state.welcome_message_sent=True
    quest_capture_state.current_scene_music_sent=True
    quest_capture_state.quest3020_conversation_sent=True
    op1_actions=quest_capture_state.dispatch(quest_op1)
    assert op1_actions==[ (
        'V134_BOUNDED_HYPOTHESIS_Q3020_OP1_TO_ACTION6_ONCE',
        quest_accept_ui_pc,quest_accept_ui_frame,0.0,
    ) ]
    assert quest_capture_state.quest3020_accept_ui_sent
    assert quest_capture_state.quest3020_op1_capture_count==1
    assert quest_capture_state.quest_operate_capture_count==1
    assert any(
        event==(
            'v134_bounded_integration_hypothesis_'
            'q3020_op1_after_p0_conversation_action6_sent_once'
        ) for event in quest_capture_state.events
    )
    assert quest_capture_state.dispatch(quest_op1)==[]
    assert quest_capture_state.quest3020_op1_capture_count==2

    # Exact op2 before action6 is likewise a strict no-reply sequence failure.
    pre_action6=GameSessionState('v134-quest-pre-action6')
    pre_action6.teleport_sent=True
    pre_action6.runtime_ack_sent=True
    pre_action6.welcome_message_sent=True
    pre_action6.current_scene_music_sent=True
    pre_action6.quest3020_conversation_sent=True
    assert pre_action6.dispatch(quest_request)==[]
    assert pre_action6.quest3020_op2_capture_count==1
    assert not pre_action6.quest3020_accept_success_sent

    # The already proven action6 -> op2 -> action1 segment remains exact.
    quest_actions=quest_capture_state.dispatch(quest_request)
    assert len(quest_actions)==1
    assert quest_actions[0]==(
        'V134_QUEST3020_P0_ACTION1_ACCEPT_SUCCESS_ONCE',
        quest_accept_pc,quest_accept_frame,0.0,
    )
    assert quest_capture_state.quest3020_accept_success_sent
    assert quest_capture_state.v136_docking_composition_pending
    assert not quest_capture_state.v136_marker1_prompt_sent
    assert quest_capture_state.quest3020_op2_capture_count==1
    assert quest_capture_state.quest_operate_capture_count==3
    assert quest_capture_state.quest_operate_last_fields==(
        V129_QUEST_ID,2,0,0,0,0
    )
    assert any(
        event.endswith(
            'exact_q3020_action6_op2_v3_singleton_1_'
            'op2_sequence_valid_1'
        )
        for event in quest_capture_state.events
    )

    # TCP replays or repeated UI events must not rerun Accept_Run.
    assert quest_capture_state.dispatch(quest_request)==[]
    assert quest_capture_state.quest3020_op2_capture_count==2
    assert quest_capture_state.quest_operate_capture_count==4
    assert any(
        event==(
            'v134_quest3020_exact_op2_wrong_sequence_no_reply_'
            'conversation_sent_1_action6_sent_1_action1_sent_1'
        )
        for event in quest_capture_state.events
    )
    stable_counts=(
        quest_capture_state.quest3020_op1_capture_count,
        quest_capture_state.quest3020_op2_capture_count,
        quest_capture_state.quest_operate_capture_count,
    )
    # Full tuple/envelope/trailing negatives are tested for both operations.
    invalid_quest_pcs=[]
    for operation in (1,2):
        invalid_quest_pcs.extend((
            _synthetic_quest_operate_pc(V129_QUEST_ID+1,operation,0,0,0,0),
            _synthetic_quest_operate_pc(V129_QUEST_ID,operation,1,0,0,0),
            _synthetic_quest_operate_pc(V129_QUEST_ID,operation,0,1,0,0),
            _synthetic_quest_operate_pc(
                V129_QUEST_ID,operation,0,0,V129_QUEST_ACTOR_ID,0
            ),
            _synthetic_quest_operate_pc(V129_QUEST_ID,operation,0,0,0,1),
            _synthetic_quest_operate_pc(
                V129_QUEST_ID,operation,0,0,0,0,nested_version=2
            ),
            _synthetic_quest_operate_pc(
                V129_QUEST_ID,operation,0,0,0,0,outer_version=1
            ),
            _synthetic_quest_operate_pc(
                V129_QUEST_ID,operation,0,0,0,0,outer_mask=3
            ),
        ))
    invalid_quest_pcs.extend((
        quest_op1_pc[:12]+u16tag(0x12,2)+quest_op1_pc[15:],
        quest_request_pc[:12]+u16tag(0x12,2)+quest_request_pc[15:],
        quest_op1_pc+u8tag(0x08,0),
        quest_request_pc+u8tag(0x08,0),
        # Correct nested body inside the response outer ID is never a request.
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+quest_op1_pc[3:],
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+quest_request_pc[3:],
    ))
    for invalid_quest_pc in invalid_quest_pcs:
        assert quest_capture_state.dispatch(parse_outer(invalid_quest_pc))==[]
    assert (
        quest_capture_state.quest3020_op1_capture_count,
        quest_capture_state.quest3020_op2_capture_count,
        quest_capture_state.quest_operate_capture_count,
    )==stable_counts
    assert quest_capture_state.quest3020_accept_success_sent
    assert any(
        event.startswith('v134_quest_operate_parse_error_no_reply_')
        for event in quest_capture_state.events
    )

    # V136 composes two already-proven boundaries without claiming an original
    # server linkage. The exact op2/action1 above only arms pending state. Wrong
    # requests leave it armed; the first byte-exact 12-byte RuntimeReq v0/mask0
    # heartbeat sends the V131 MARKER1 prompt once on the next dispatch.
    assert V136_EMPTY_RUNTIME_REQ_PC==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 00'
    ) and len(V136_EMPTY_RUNTIME_REQ_PC)==12
    empty_runtime_req=parse_outer(V136_EMPTY_RUNTIME_REQ_PC)
    assert (
        empty_runtime_req.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
        empty_runtime_req.outer_version==0 and
        empty_runtime_req.outer_mask==0 and
        empty_runtime_req.vital_count==0 and
        empty_runtime_req.nested_id is None and
        empty_runtime_req.nested_version is None and
        empty_runtime_req.nested_payload==b'' and
        empty_runtime_req.raw_pc==V136_EMPTY_RUNTIME_REQ_PC
    )
    precomposition_state=GameSessionState('v136-precomposition')
    precomposition_state.teleport_sent=True
    precomposition_state.runtime_ack_sent=True
    precomposition_state.welcome_message_sent=True
    precomposition_state.current_scene_music_sent=True
    assert precomposition_state.dispatch(empty_runtime_req)==[]
    assert not precomposition_state.v136_marker1_prompt_sent
    assert not precomposition_state.v136_docking_composition_pending

    mask2_count0_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+
        u8tag(0x08,0)+u8tag(0x0B,2)+u16tag(0x12,0)
    )
    wrong_empty_runtime_pcs=(
        V136_EMPTY_RUNTIME_REQ_PC[:9]+bytes((1,))+V136_EMPTY_RUNTIME_REQ_PC[10:],
        mask2_count0_pc,
        V136_EMPTY_RUNTIME_REQ_PC+u8tag(0x08,0),
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+V136_EMPTY_RUNTIME_REQ_PC[3:],
        quest_op1_pc,
    )
    for wrong_empty_runtime_pc in wrong_empty_runtime_pcs:
        assert quest_capture_state.dispatch(
            parse_outer(wrong_empty_runtime_pc)
        )==[]
        assert quest_capture_state.v136_docking_composition_pending
        assert not quest_capture_state.v136_marker1_prompt_sent
    challenge_pc,challenge_frame=make_teleport_check_scene1_challenge()
    prompt_actions=quest_capture_state.dispatch(empty_runtime_req)
    assert prompt_actions==[ (
        'V136_COMPOSITIONAL_Q3020_VAR2_1_MARKER1_DOCKING_PROMPT_ONCE',
        challenge_pc,challenge_frame,0.0,
    ) ]
    assert not quest_capture_state.v136_docking_composition_pending
    assert quest_capture_state.v136_marker1_prompt_sent
    assert any(
        event==(
            'v136_compositional_server_hypothesis_q3020_var2_1_'
            'next_exact_empty_runtime_req_marker1_prompt_sent_once_'
            'no_travel_vehicle_completion_claim'
        ) for event in quest_capture_state.events
    )
    assert quest_capture_state.dispatch(empty_runtime_req)==[]
    assert quest_capture_state.v136_marker1_prompt_sent

    # V131 isolates one server-initiated TeleportCheck challenge/echo. The
    # exact RuntimeRes v4 challenge includes the required trailing derived
    # mask. Only an exact RuntimeReq v0/mask2/singleton/v0/value1 echo after
    # that challenge advances the capture milestone; every variant is no-reply.
    assert protocol_name_id("TeleportCheckVital")==TELEPORT_CHECK_VITAL==0x4477
    assert challenge_pc==bytes.fromhex(
        '12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 '
        '12 77 44 0B 00 0F 01 00 0B 00'
    )
    assert len(challenge_pc)==25
    assert snappy_raw_decompress(challenge_frame[8:])==challenge_pc
    marker1_transport_pc,marker1_transport_frame=(
        make_v137_marker1_transport_probe()
    )
    expected_marker1_transport_pc=bytes.fromhex(
        '12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 '
        '12 A2 25 0B 04 0B 02 0B 01 12 01 00 '
        '32 00 00 00 00 00 00 00 00 0B 00 0B 00 '
        '2A 00 48 21 C6 2A 00 C0 3C C4 2A 00 C0 27 44 '
        '0B 00 0B 00 0F 00 00 0B 00'
    )
    assert marker1_transport_pc==expected_marker1_transport_pc
    assert len(marker1_transport_pc)==64
    assert len(marker1_transport_frame)==75
    assert snappy_raw_decompress(
        marker1_transport_frame[8:]
    )==marker1_transport_pc
    parsed_marker1_transport=parse_outer(marker1_transport_pc)
    assert (
        parsed_marker1_transport.outer_id==GSCN_RUNTIME_PROTOCOL_RES and
        parsed_marker1_transport.outer_version==4 and
        parsed_marker1_transport.outer_mask==2 and
        parsed_marker1_transport.vital_count==1 and
        parsed_marker1_transport.nested_id==TELEPORT_VITAL and
        parsed_marker1_transport.nested_version==4 and
        marker1_transport_pc[-2:]==u8tag(0x0B,0)
    )
    zero_target_payload=(
        u8tag(0x0B,2)+u8tag(0x0B,1)+
        make_teleport_target(V137_MARKER_SCENE_ID,V137_MARKER_SCENE_SEQ,0,0,0)+
        u8tag(0x0B,0)+u8tag(0x0B,0)+u16tag(0x0F,0)
    )
    zero_target_runtime_pc,_=make_runtime_vitals([(
        TELEPORT_VITAL,4,zero_target_payload,
    )])
    assert len(zero_target_runtime_pc)==len(marker1_transport_pc)==64
    marker_transport_diff=[
        (i,old,new) for i,(old,new) in enumerate(zip(
            zero_target_runtime_pc,marker1_transport_pc
        )) if old!=new
    ]
    assert marker_transport_diff==[
        (42,0x00,0x48),(43,0x00,0x21),(44,0x00,0xC6),
        (47,0x00,0xC0),(48,0x00,0x3C),(49,0x00,0xC4),
        (52,0x00,0xC0),(53,0x00,0x27),(54,0x00,0x44),
    ]
    assert marker1_transport_pc[41:45]==struct.pack('<f',V137_MARKER_X)
    assert marker1_transport_pc[46:50]==struct.pack('<f',V137_MARKER_Y)
    assert marker1_transport_pc[51:55]==struct.pack('<f',V137_MARKER_Z)
    # Direction 3 is decoded MARKER data but deliberately has no target-field
    # mapping. Both target bytes and the final u16 retain constructor zero.
    assert marker1_transport_pc[36:40]==bytes.fromhex('0B 00 0B 00')
    assert marker1_transport_pc[55:62]==bytes.fromhex(
        '0B 00 0B 00 0F 00 00'
    )
    teleport_check_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+
        u16tag(0x12,TELEPORT_CHECK_VITAL)+u8tag(0x0B,0)+
        u16tag(0x0F,V131_TELEPORT_CHECK_VALUE)
    )
    assert teleport_check_pc==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 '
        '12 77 44 0B 00 0F 01 00'
    )
    teleport_check=parse_outer(teleport_check_pc)
    assert teleport_check_pc==V136_MARKER1_CONFIRM_PC
    assert parse_teleport_check_vital(teleport_check)=={
        'field_u16_14':1,'consumed_bytes':3,'trailing_bytes':0,
    }
    prechallenge_state=GameSessionState('v131-teleport-check-prechallenge')
    prechallenge_state.teleport_sent=True
    prechallenge_state.runtime_ack_sent=True
    prechallenge_state.welcome_message_sent=True
    prechallenge_state.current_scene_music_sent=True
    assert prechallenge_state.dispatch(teleport_check)==[]
    assert prechallenge_state.teleport_check_echo_capture_count==0
    assert prechallenge_state.v136_marker1_confirm_capture_count==0
    assert not prechallenge_state.v137_marker1_transport_sent
    assert prechallenge_state.v137_marker1_transport_send_count==0
    post_state=GameSessionState('v131-teleport-check-challenged')
    post_state.teleport_sent=True
    post_state.runtime_ack_sent=True
    post_state.welcome_message_sent=True
    post_state.current_scene_music_sent=True
    post_state.teleport_check_challenge_sent=True
    assert post_state.dispatch(teleport_check)==[]
    assert post_state.teleport_check_echo_capture_count==1
    assert post_state.teleport_check_echo_last_value==V131_TELEPORT_CHECK_VALUE
    assert any(
        event==(
            'v131_teleport_check_scene1_echo_capture_no_reply_'
            'field_u16_14_1_count1_challenge_sent_1_exact_1_'
            'semantics_unassigned'
        ) for event in post_state.events
    )
    teleport_event=describe_capture_event(teleport_check,post_state)
    assert teleport_event is not None
    assert 'name=TeleportCheckVital id=0x4477 version=0' in teleport_event
    assert 'post_action1=0' in teleport_event
    assert 'field_u16_14=1' in teleport_event
    assert 'semantics=unassigned no_response=1' in teleport_event
    assert f'payload_hex={teleport_check.nested_payload.hex().upper()}' in teleport_event
    teleport_check_value2=(
        teleport_check_pc[:-2]+bytes((2,0))
    )
    teleport_check_count2=(
        teleport_check_pc[:12]+u16tag(0x12,2)+teleport_check_pc[15:]+
        u16tag(0x12,TARGET_VITAL)+u8tag(0x0B,0)
    )
    invalid_teleport_checks=(
        teleport_check_pc[:19]+bytes([1])+teleport_check_pc[20:],
        teleport_check_pc+u8tag(0x08,0),
        teleport_check_count2,
        teleport_check_pc[:8]+u8tag(0x08,1)+teleport_check_pc[10:],
        teleport_check_pc[:10]+u8tag(0x0B,3)+teleport_check_pc[12:],
        teleport_check_value2,
    )
    for invalid_pc in invalid_teleport_checks:
        assert post_state.dispatch(parse_outer(invalid_pc))==[]
    assert post_state.teleport_check_echo_capture_count==1
    assert post_state.teleport_check_echo_last_value==V131_TELEPORT_CHECK_VALUE

    # The V136 positive-confirm lane is independent from the dormant V131
    # regression flag. It is strict one-shot, prompt-sequenced, and no-reply.
    assert quest_capture_state.teleport_check_challenge_sent is False
    transport_actions=quest_capture_state.dispatch(teleport_check)
    assert transport_actions==[ (
        'V137_ISOLATED_COMPOSITIONAL_MARKER1_'
        'TELEPORTVITAL_TRANSPORT_PROBE_ONCE',
        marker1_transport_pc,marker1_transport_frame,0.0,
    ) ]
    assert quest_capture_state.v136_marker1_confirm_capture_count==1
    assert (
        quest_capture_state.v136_marker1_confirm_last_value==
        V131_TELEPORT_CHECK_VALUE
    )
    assert quest_capture_state.v137_marker1_transport_sent
    assert quest_capture_state.v137_marker1_transport_send_count==1
    assert any(
        event==(
            'v137_exact_marker1_positive_confirm_'
            'server_driven_teleportvital_scene1_seq0_'
            'xyz_minus10322_minus755_671_sent_once_'
            'isolated_compositional_transport_hypothesis_'
            'not_teleportcheck_reply_not_completed_travel'
        ) for event in quest_capture_state.events
    )
    assert any(
        event==(
            'v136_marker1_positive_confirm_capture_'
            'no_teleportcheck_reply_'
            'field_u16_14_1_count1_prompt_sent_1_exact_1_'
            'compositional_q3020_var2_1_docking_hypothesis_'
            'no_travel_vehicle_completion_claim'
        ) for event in quest_capture_state.events
    )
    assert quest_capture_state.dispatch(teleport_check)==[]
    assert quest_capture_state.v136_marker1_confirm_capture_count==1
    assert quest_capture_state.v137_marker1_transport_send_count==1

    # V138 uses the exact live post-transition batch as one indivisible gate.
    # The following boundary walk consumes all three statically fixed records
    # without scanning for ID-like bytes inside a payload.
    assert len(V138_MARKER1_READY_PC)==76
    marker1_ready=parse_outer(V138_MARKER1_READY_PC)
    assert (
        marker1_ready.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
        marker1_ready.outer_version==0 and
        marker1_ready.outer_mask==2 and
        marker1_ready.vital_count==3 and
        marker1_ready.nested_id==TARGET_VITAL and
        marker1_ready.nested_version==0 and
        marker1_ready.raw_pc==V138_MARKER1_READY_PC
    )
    ready_cursor=Cursor(marker1_ready.nested_payload)
    assert struct.unpack('<Q',ready_cursor.raw8(0x32))[0]==0
    assert ready_cursor.u8(0x08)==2
    assert ready_cursor.u16(0x12)==TELEPORT_VITAL
    assert ready_cursor.u8(0x0B)==4
    assert ready_cursor.u8(0x0B)==2
    assert ready_cursor.u8(0x0B)==0  # target-object presence
    assert ready_cursor.u8(0x0B)==0  # TeleportVital +0x20 default
    assert ready_cursor.u8(0x0B)==0  # TeleportVital +0x21/default byte
    assert ready_cursor.u16(0x0F)==0 # TeleportVital +0x22 default
    assert ready_cursor.u16(0x12)==TARGET_POS_VITAL
    assert ready_cursor.u8(0x0B)==0
    assert ready_cursor.f32()==V137_MARKER_X
    assert ready_cursor.f32()==V137_MARKER_Y
    assert ready_cursor.f32()==V137_MARKER_Z
    assert ready_cursor.f32()==0.0
    assert ready_cursor.u8(0x0B)==0
    assert ready_cursor.u8(0x0B)==0
    assert ready_cursor.remain()==0

    marker_population_pc,marker_population_frame,marker_population_rows=(
        make_v138_marker1_population_state()
    )
    assert tuple(row[0] for row in marker_population_rows)==(
        V138_MARKER1_NEAREST_INDICES
    )
    assert len(marker_population_pc)==3152
    assert len(marker_population_frame)==3165
    assert hashlib.sha256(marker_population_pc).hexdigest().upper()==(
        '6B8DD30BBE29641D99849F96601B61C8F4791FD06F5C900CD095B67C50A40C64'
    )
    assert hashlib.sha256(marker_population_frame).hexdigest().upper()==(
        '7C844EC3CA4B39231AB9E25A2F14B00922BF7215357E3143E2840687846DAEA0'
    )
    assert snappy_raw_decompress(
        marker_population_frame[8:]
    )==marker_population_pc
    assert marker_population_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert marker_population_pc.count(u16tag(0x12,MOVEMENT_ATTR))==20
    p30_marker_row=next(
        row for row in marker_population_rows if row[0]==V112_MONSTER_INDEX
    )
    expected_marker_p30_npc_attr=make_npc_attr(
        p30_marker_row[1],V112_MONSTER_ACTOR_ID,1,0,p30_marker_row[5],
        current_hp=V117_P30_EXACT_HP,max_hp=V117_P30_EXACT_HP,
        basic_name=V119_P30_TARGET_NAME,
    )
    assert marker_population_pc.count(expected_marker_p30_npc_attr)==1

    v140_population_pc,v140_population_frame,v140_population_rows=(
        make_v140_marker1_population_state()
    )
    assert tuple(row[0] for row in v140_population_rows)==(
        V138_MARKER1_NEAREST_INDICES
    )
    assert len(v140_population_pc)==3152
    assert len(v140_population_frame)==3165
    assert hashlib.sha256(v140_population_pc).hexdigest().upper()==(
        '0DB101113B5317822657CA965B1EBC50E239F9A423CF4CA307CA8B6006D1A188'
    )
    assert hashlib.sha256(v140_population_frame).hexdigest().upper()==(
        '21F27276C9646EE961E68862041A1FD7F3F623AF36BD2402D8A3492F68FFA58E'
    )
    assert snappy_raw_decompress(v140_population_frame[8:])==v140_population_pc
    assert v140_population_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert v140_population_pc.count(u16tag(0x12,MOVEMENT_ATTR))==20
    assert v140_population_pc.count(expected_marker_p30_npc_attr)==1
    assert (V140_P86_HARNESS_X,V140_P86_HARNESS_Y,V140_P86_HARNESS_Z)==(
        -10222.0,-705.0,671.0
    )
    v140_population_diff=[
        offset for offset,(before,after) in enumerate(zip(
            marker_population_pc,v140_population_pc
        )) if before!=after
    ]
    assert v140_population_diff==[128,129,130,133,134,135,138,139,140]
    p86_marker_row=next(
        row for row in marker_population_rows if row[0]==V139_P86_INDEX
    )
    authentic_p86_initial_movement=make_remote_movement_attr(
        V139_P86_ACTOR_ID,p86_marker_row[2],p86_marker_row[3],
        p86_marker_row[4],3.141592653589793,mask=0xFF,
    )
    harness_p86_initial_movement=make_remote_movement_attr(
        V139_P86_ACTOR_ID,V140_P86_HARNESS_X,V140_P86_HARNESS_Y,
        V140_P86_HARNESS_Z,3.141592653589793,mask=0xFF,
    )
    assert marker_population_pc.count(authentic_p86_initial_movement)==1
    assert v140_population_pc.count(authentic_p86_initial_movement)==0
    assert v140_population_pc.count(harness_p86_initial_movement)==1

    pre_v138_ready=GameSessionState('v138-ready-presequence')
    pre_v138_ready.teleport_sent=True
    pre_v138_ready.runtime_ack_sent=True
    pre_v138_ready.welcome_message_sent=True
    pre_v138_ready.current_scene_music_sent=True
    pre_v138_ready.npc_spawn_sent=True
    pre_v138_ready.population_indices=V112_TEST_INDICES
    assert pre_v138_ready.dispatch(marker1_ready)==[]
    assert pre_v138_ready.v138_marker1_ready_capture_count==0
    assert not pre_v138_ready.v138_marker1_population_sent
    assert pre_v138_ready.v138_marker1_population_send_count==0

    invalid_v138_ready=GameSessionState('v138-ready-invalid')
    invalid_v138_ready.teleport_sent=True
    invalid_v138_ready.runtime_ack_sent=True
    invalid_v138_ready.welcome_message_sent=True
    invalid_v138_ready.current_scene_music_sent=True
    invalid_v138_ready.npc_spawn_sent=True
    invalid_v138_ready.population_indices=V112_TEST_INDICES
    invalid_v138_ready.v137_marker1_transport_sent=True
    wrong_v138_ready_pcs=(
        V138_MARKER1_READY_PC[:9]+bytes((1,))+V138_MARKER1_READY_PC[10:],
        V138_MARKER1_READY_PC[:13]+bytes((2,0))+V138_MARKER1_READY_PC[15:],
        V138_MARKER1_READY_PC[:19]+bytes((1,))+V138_MARKER1_READY_PC[20:],
        V138_MARKER1_READY_PC[:37]+bytes((3,))+V138_MARKER1_READY_PC[38:],
        V138_MARKER1_READY_PC[:-1]+bytes((1,)),
        V138_MARKER1_READY_PC+u8tag(0x08,0),
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+V138_MARKER1_READY_PC[3:],
    )
    for invalid_pc in wrong_v138_ready_pcs:
        assert invalid_v138_ready.dispatch(parse_outer(invalid_pc))==[]
    assert invalid_v138_ready.v138_marker1_ready_capture_count==0
    assert not invalid_v138_ready.v138_marker1_population_sent
    assert invalid_v138_ready.v138_marker1_population_send_count==0

    quest_capture_state.npc_spawn_sent=True
    quest_capture_state.population_indices=V112_TEST_INDICES
    stale_pretransition_target=(V135_PLAYER_X,V135_PLAYER_Y,V135_PLAYER_Z,0.0)
    quest_capture_state.last_target_pos=stale_pretransition_target
    v140_actions=quest_capture_state.dispatch(marker1_ready)
    assert v140_actions==[ (
        'V140_MARKER1_READY_NEAREST20_P86_OPERATIONAL_'
        'HARNESS_REAPPLY_ONCE',
        v140_population_pc,v140_population_frame,0.0,
    ) ]
    assert quest_capture_state.v138_marker1_ready_capture_count==1
    assert quest_capture_state.v138_marker1_population_sent
    assert quest_capture_state.v138_marker1_population_send_count==1
    assert quest_capture_state.population_indices==V138_MARKER1_NEAREST_INDICES
    assert quest_capture_state.population_refresh_anchor==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    assert quest_capture_state.npc_spawn_sent
    assert quest_capture_state.last_target_pos==stale_pretransition_target
    assert quest_capture_state.dispatch(marker1_ready)==[]
    assert quest_capture_state.v138_marker1_ready_capture_count==1
    assert quest_capture_state.v138_marker1_population_send_count==1
    assert any(
        event==(
            'v140_exact_76b_marker1_ready_after_v137_transport_'
            'nearest20_p86_operational_harness_population_sent_once_'
            'no_delayed_reapply_message_music_ack_startgame_teleport'
        ) for event in quest_capture_state.events
    )

    v136_invalid_confirm_state=GameSessionState('v136-invalid-confirm')
    v136_invalid_confirm_state.teleport_sent=True
    v136_invalid_confirm_state.runtime_ack_sent=True
    v136_invalid_confirm_state.welcome_message_sent=True
    v136_invalid_confirm_state.current_scene_music_sent=True
    v136_invalid_confirm_state.v136_marker1_prompt_sent=True
    wrong_v136_confirm_pcs=(
        teleport_check_pc[:19]+bytes((1,))+teleport_check_pc[20:],
        teleport_check_pc+u8tag(0x08,0),
        teleport_check_count2,
        teleport_check_pc[:8]+u8tag(0x08,1)+teleport_check_pc[10:],
        teleport_check_pc[:10]+u8tag(0x0B,3)+teleport_check_pc[12:],
        teleport_check_value2,
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+teleport_check_pc[3:],
    )
    for invalid_pc in wrong_v136_confirm_pcs:
        assert v136_invalid_confirm_state.dispatch(parse_outer(invalid_pc))==[]
    assert v136_invalid_confirm_state.v136_marker1_confirm_capture_count==0
    assert v136_invalid_confirm_state.v136_marker1_confirm_last_value is None
    assert not v136_invalid_confirm_state.v137_marker1_transport_sent
    assert v136_invalid_confirm_state.v137_marker1_transport_send_count==0

    # V112 combines two independent data-backed boundaries in one isolated scene:
    # usage-1 P30 is the monster transport/interaction control, while usage-2 P91
    # remains the manual test-harness trigger for the exact TradeZoom store-5 packet.
    assert protocol_name_id("TradeZoomVital") == TRADE_ZOOM_VITAL == 0x2A7A
    assert protocol_name_id("TradeCmdVital") == TRADE_CMD_VITAL == 0x23B5
    shop_pc,shop_frame=make_trade_zoom_store5()
    expected_shop_pc=bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 7A 2A "
        "0B 02 08 02 08 02 32 00 00 00 00 00 00 00 00 14 05 00 00 00 "
        "48 00 00 00 00 0F 00 00 0B 00"
    )
    assert shop_pc==expected_shop_pc and len(shop_pc)==48 and len(shop_frame)==58
    assert snappy_raw_decompress(shop_frame[8:])==shop_pc

    player_test_x=V135_PLAYER_X
    target_req_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,TARGET_POS_VITAL)+
        u8tag(0x0B,0)+f32tag(player_test_x)+f32tag(V135_PLAYER_Y)+
        f32tag(V135_PLAYER_Z)+f32tag(0.0)+u8tag(0x0B,1)+u8tag(0x0B,0)
    )
    target_pos_parsed=parse_outer(target_req_pc)
    acts=rst.dispatch(target_pos_parsed)
    assert [a[0] for a in acts]==[
        'V134_P0_P30_P91_ISOLATED_INITIAL_READY',
        'V134_P0_P30_P91_ISOLATED_REAPPLY_READY',
    ]
    assert abs(acts[1][3]-3.0)<1e-9
    assert abs(sum(action[3] for action in acts)-3.0)<1e-9
    assert acts[0][1]==acts[1][1] and acts[0][2]==acts[1][2]
    assert not rst.teleport_check_challenge_sent
    assert not rst.quest3020_conversation_sent
    assert not rst.quest3020_accept_ui_sent
    assert not rst.quest3020_accept_success_sent
    assert not rst.shop_store5_open_sent
    assert rst.population_indices==V112_TEST_INDICES
    assert rst.population_refresh_anchor==(
        float(struct.unpack('<f',struct.pack('<f',player_test_x))[0]),
        float(struct.unpack('<f',struct.pack('<f',V135_PLAYER_Y))[0]),
        float(struct.unpack('<f',struct.pack('<f',V135_PLAYER_Z))[0]),
    )
    population_pc,population_frame,population_rows=make_v112_monster_shop_population_state()
    assert acts[0][1]==population_pc and acts[0][2]==population_frame
    assert len(population_pc)==504 and len(population_frame)==517
    assert tuple(row[0] for row in population_rows)==V112_TEST_INDICES
    assert population_pc.startswith(bytes.fromhex(
        "12 9D 6E 14 00 00 00 00 08 04 0B 00 0B 02 12 03 00"
    ))
    assert population_pc.count(u16tag(0x12,NPC_ATTR))==3
    assert population_pc.count(u16tag(0x12,MOVEMENT_ATTR))==3
    assert population_pc.count(u16tag(0x12,ACTION_VITAL))==0
    assert population_pc.count(u16tag(0x12,0x1285))==0  # FightAttr is local-only.
    assert qwordtag(0x32,V129_QUEST_ACTOR_ID) in population_pc
    assert qwordtag(0x32,V112_MONSTER_ACTOR_ID) in population_pc
    assert qwordtag(0x32,V112_SHOP_TRIGGER_ACTOR_ID) in population_pc
    assert snappy_raw_decompress(population_frame[8:])==population_pc

    # V129 changes the frozen V128 population packet only by changing the
    # actor count 2->3 and prepending the exact P0 actor entry. P30/P91 bytes
    # remain in their original order and are otherwise byte-identical.
    frozen_v128_population_pc,frozen_v128_population_frame,_=(
        make_v112_monster_shop_population_state(indices=(30,91))
    )
    assert len(frozen_v128_population_pc)==348
    assert len(frozen_v128_population_frame)==361
    p0_placement={row[0]:row for row in _v112_test_rows()}[
        V129_QUEST_ACTOR_INDEX
    ]
    p0_npc_attr=make_npc_attr(
        V129_QUEST_ACTOR_TEMPLATE,V129_QUEST_ACTOR_ID,1,0,p0_placement[5],
        current_hp=100,max_hp=100,basic_name="",
    )
    p0_movement_attr=make_remote_movement_attr(
        V129_QUEST_ACTOR_ID,p0_placement[2],p0_placement[3],p0_placement[4],
        0.0,mask=0xFF,
    )
    exact_p0_entry=make_remote_actor_entry(
        4,V129_QUEST_ACTOR_ID,
        [(NPC_ATTR,p0_npc_attr),(MOVEMENT_ATTR,p0_movement_attr)],
    )
    assert len(exact_p0_entry)==156
    assert population_pc==(
        frozen_v128_population_pc[:14]+u16tag(0x12,3)+exact_p0_entry+
        frozen_v128_population_pc[17:]
    )

    # Within V119's name-bearing population shape, V117's entire HP delta from
    # the old 100/100 value remains the exact current/max pair for P30.
    # STANDARD_MOB row 27 supplies n_HPMAX=3857; P0/P91 remain inherited
    # 100/100 controls. Equal lengths and these four decompressed byte positions
    # prove the HP milestone introduced no other actor/population byte.
    v116_population_pc,v116_population_frame,_=(
        make_v112_monster_shop_population_state(p30_hp=100)
    )
    assert len(v116_population_pc)==len(population_pc)==504
    assert len(v116_population_frame)==len(population_frame)==517
    population_diff=[
        (i,old,new)
        for i,(old,new) in enumerate(zip(v116_population_pc,population_pc))
        if old!=new
    ]
    assert population_diff==[
        (235,0x64,0x11),(236,0x00,0x0F),
        (240,0x64,0x11),(241,0x00,0x0F),
    ],population_diff
    p30_name_wire=bytes.fromhex(
        "48 1A 00 00 00 "
        "54 00 6F 00 72 00 6E 00 61 00 64 00 6F 00 "
        "20 00 45 00 61 00 67 00 6C 00 65 00"
    )
    assert p30_name_wire==wstr_tag(V119_P30_TARGET_NAME)
    assert len(p30_name_wire)==31
    expected_p30_npc_attr=bytes.fromhex(
        "0B 01 32 1F 20 00 00 00 00 00 00 12 0D 03 "
        "48 1A 00 00 00 "
        "54 00 6F 00 72 00 6E 00 61 00 64 00 6F 00 "
        "20 00 45 00 61 00 67 00 6C 00 65 00 "
        "14 11 0F 00 00 14 11 0F 00 00 12 01 00 "
        "32 00 00 00 00 00 00 00 00 0B 05 12 1F 00 "
        "48 20 00 00 00 4D 00 30 00 31 00 31 00 5F 00 "
        "30 00 30 00 30 00 5F 00 30 00 30 00 30 00 5F 00 "
        "53 00 50 00 33 00"
    )
    test_rows_by_index={row[0]:row for row in _v112_test_rows()}
    expected_p0_control_attr=make_npc_attr(
        V129_QUEST_ACTOR_TEMPLATE,V129_QUEST_ACTOR_ID,1,0,
        test_rows_by_index[V129_QUEST_ACTOR_INDEX][5],current_hp=100,max_hp=100
    )
    expected_p91_control_attr=make_npc_attr(
        V112_SHOP_TRIGGER_TEMPLATE,V112_SHOP_TRIGGER_ACTOR_ID,1,0,
        test_rows_by_index[V112_SHOP_TRIGGER_INDEX][5],current_hp=100,max_hp=100
    )
    expected_v118_p30_npc_attr=make_npc_attr(
        V112_MONSTER_TEMPLATE,V112_MONSTER_ACTOR_ID,1,0,
        test_rows_by_index[V112_MONSTER_INDEX][5],current_hp=V117_P30_EXACT_HP,
        max_hp=V117_P30_EXACT_HP,basic_name=""
    )
    v118_population_pc,v118_population_frame,_=(
        make_v112_monster_shop_population_state(p30_basic_name="")
    )
    assert len(expected_v118_p30_npc_attr)==78
    assert len(expected_p30_npc_attr)==109
    assert len(v118_population_pc)==473 and len(v118_population_frame)==486
    assert snappy_raw_decompress(v118_population_frame[8:])==v118_population_pc
    old_p30_offset=v118_population_pc.index(expected_v118_p30_npc_attr)
    new_p30_offset=population_pc.index(expected_p30_npc_attr)
    assert old_p30_offset==new_p30_offset
    expected_v119_population=(
        v118_population_pc[:old_p30_offset+12]
        + bytes([0x0D])
        + v118_population_pc[old_p30_offset+13:old_p30_offset+14]
        + p30_name_wire
        + v118_population_pc[old_p30_offset+14:]
    )
    assert population_pc==expected_v119_population
    assert len(population_pc)-len(v118_population_pc)==len(p30_name_wire)==31
    assert population_pc.count(p30_name_wire)==1
    assert (0x030C|V119_BASICATTR_NAME_MASK)==0x030D
    assert expected_p30_npc_attr in population_pc
    assert expected_v118_p30_npc_attr in v118_population_pc
    assert expected_p30_npc_attr not in v118_population_pc
    assert expected_p0_control_attr in population_pc
    assert expected_p0_control_attr in v118_population_pc
    assert expected_p91_control_attr in population_pc
    assert expected_p91_control_attr in v118_population_pc
    assert population_pc.count(u16tag(0x12,ACTION_VITAL))==0
    assert population_pc.count(u16tag(0x12,0x1285))==0  # FightAttr local-only.
    assert snappy_raw_decompress(population_frame[8:])==population_pc

    target_far=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,TARGET_POS_VITAL)+
        u8tag(0x0B,0)+f32tag(5000.0)+f32tag(5000.0)+f32tag(931.0)+
        f32tag(0.0)+u8tag(0x0B,1)+u8tag(0x0B,0)
    )
    assert rst.dispatch(parse_outer(target_far))==[]
    assert rst.population_indices==V112_TEST_INDICES
    assert 'v129_isolated_population_retained_p0_p30_p91' in rst.events

    def choose_request(*actor_ids:int) -> bytes:
        return (
            u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
            u8tag(0x0B,2)+u16tag(0x12,len(actor_ids))+
            b''.join(
                u16tag(0x12,CHOOSE_NPC)+u8tag(0x0B,0)+qwordtag(0x32,aid)
                for aid in actor_ids
            )
        )

    # V139 accepts only one byte-exact singleton marker TargetPos after V138's
    # destination population, then one complete V97-observed P86 interaction
    # shape. The fresh position is the only heading source.
    assert V139_P86_ACTOR_ID==0x2057
    assert V139_P86_INDEX==86
    assert len(V139_MARKER1_TARGETPOS_PC)==44
    assert hashlib.sha256(V139_MARKER1_TARGETPOS_PC).hexdigest().upper()==(
        '6854DE6C2FE21897F710B3C74EF3AFD98718DF939A104B403AD744DE88759B02'
    )
    marker_targetpos=parse_outer(V139_MARKER1_TARGETPOS_PC)
    assert (
        marker_targetpos.outer_id==GSCN_RUNTIME_PROTOCOL_REQ and
        marker_targetpos.outer_version==0 and
        marker_targetpos.outer_mask==2 and
        marker_targetpos.vital_count==1 and
        marker_targetpos.nested_id==TARGET_POS_VITAL and
        marker_targetpos.nested_version==0 and
        parse_target_pos_vital(marker_targetpos)==(
            V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0,0,1
        )
    )

    def v139_destination_state(token: str, *, current_membership=True):
        state=GameSessionState(token)
        state.teleport_sent=True
        state.runtime_ack_sent=True
        state.welcome_message_sent=True
        state.current_scene_music_sent=True
        state.npc_spawn_sent=True
        state.v137_marker1_transport_sent=True
        state.v138_marker1_population_sent=True
        state.v138_marker1_population_send_count=1
        state.population_indices=(
            V138_MARKER1_NEAREST_INDICES
            if current_membership else V112_TEST_INDICES
        )
        state.population_refresh_anchor=(
            V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
        )
        state.last_target_pos=(V135_PLAYER_X,V135_PLAYER_Y,V135_PLAYER_Z,0.0)
        return state

    def v139_interaction_request(
        choose_ids=(V139_P86_ACTOR_ID,), *,
        target_id=V139_P86_ACTOR_ID, target_kind=2,
        outer_version=0, outer_mask=2, target_version=0,
        choose_versions=None, trailing_target_pos=False,
        target_pos_version=0, extra_tail=b'', declared_count=None,
    ) -> bytes:
        if choose_versions is None:
            choose_versions=(0,)*len(choose_ids)
        vitals=(
            u16tag(0x12,TARGET_VITAL)+u8tag(0x0B,target_version)+
            qwordtag(0x32,target_id)+u8tag(0x08,target_kind)
        )
        for actor_id,nested_version in zip(choose_ids,choose_versions):
            vitals+=(
                u16tag(0x12,CHOOSE_NPC)+u8tag(0x0B,nested_version)+
                qwordtag(0x32,actor_id)
            )
        if trailing_target_pos:
            vitals+=(
                u16tag(0x12,TARGET_POS_VITAL)+
                u8tag(0x0B,target_pos_version)+
                f32tag(V137_MARKER_X)+f32tag(V137_MARKER_Y)+
                f32tag(V137_MARKER_Z)+f32tag(0.0)+
                u8tag(0x0B,1)+u8tag(0x0B,0)
            )
        vitals+=extra_tail
        count=(
            1+len(choose_ids)+int(trailing_target_pos)
            if declared_count is None else declared_count
        )
        return (
            u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+
            u8tag(0x08,outer_version)+u8tag(0x0B,outer_mask)+
            u16tag(0x12,count)+vitals
        )

    pre_v139=v139_destination_state('v139-presequence')
    pre_v139.v138_marker1_population_sent=False
    assert pre_v139.dispatch(marker_targetpos)==[]
    assert pre_v139.v139_marker_targetpos_capture_count==0
    assert not pre_v139.v139_p86_interaction_armed
    wrong_membership=v139_destination_state(
        'v139-wrong-membership',current_membership=False
    )
    assert wrong_membership.dispatch(marker_targetpos)==[]
    assert wrong_membership.v139_marker_targetpos_capture_count==0
    assert not wrong_membership.v139_p86_interaction_armed

    invalid_marker_pcs=(
        V139_MARKER1_TARGETPOS_PC[:8]+u8tag(0x08,1)+
            V139_MARKER1_TARGETPOS_PC[10:],
        V139_MARKER1_TARGETPOS_PC[:10]+u8tag(0x0B,3)+
            V139_MARKER1_TARGETPOS_PC[12:],
        V139_MARKER1_TARGETPOS_PC[:12]+u16tag(0x12,2)+
            V139_MARKER1_TARGETPOS_PC[15:],
        V139_MARKER1_TARGETPOS_PC[:19]+bytes((1,))+
            V139_MARKER1_TARGETPOS_PC[20:],
        V139_MARKER1_TARGETPOS_PC[:-1]+bytes((1,)),
        V139_MARKER1_TARGETPOS_PC+u8tag(0x08,0),
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_RES)+
            V139_MARKER1_TARGETPOS_PC[3:],
    )
    for ordinal,invalid_pc in enumerate(invalid_marker_pcs):
        state=v139_destination_state(f'v139-invalid-marker-{ordinal}')
        assert state.dispatch(parse_outer(invalid_pc))==[]
        assert state.v139_marker_targetpos_capture_count==0
        assert not state.v139_p86_interaction_armed

    v139_state=v139_destination_state('v139-p86-face-conversation')
    assert v139_state.dispatch(marker_targetpos)==[]
    assert v139_state.v139_marker_targetpos_capture_count==1
    assert v139_state.v139_p86_interaction_armed
    assert v139_state.last_target_pos==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0
    )
    # Exact marker replay cannot increment or send anything.
    assert v139_state.dispatch(marker_targetpos)==[]
    assert v139_state.v139_marker_targetpos_capture_count==1
    assert v139_state.v139_p86_interaction_armed

    p86_target_only_pc=v139_interaction_request(
        choose_ids=(),declared_count=1
    )
    p86_target_only=parse_outer(p86_target_only_pc)
    assert parse_target_vital(p86_target_only)==(V139_P86_ACTOR_ID,2)
    assert parse_v139_p86_interaction_shape(p86_target_only) is None
    assert v139_state.dispatch(p86_target_only)==[]
    assert v139_state.v139_p86_interaction_armed
    p86_choose_only=parse_outer(choose_request(V139_P86_ACTOR_ID))
    assert parse_choose_npc(p86_choose_only)==V139_P86_ACTOR_ID
    assert parse_v139_p86_interaction_shape(p86_choose_only) is None
    assert v139_state.dispatch(p86_choose_only)==[]
    assert v139_state.v139_p86_interaction_armed

    p86_interaction_pc=v139_interaction_request()
    p86_interaction=parse_outer(p86_interaction_pc)
    assert parse_v139_p86_interaction_shape(p86_interaction)==(1,None)
    p86_face_pc,p86_face_frame=make_v139_p86_face_state(
        V137_MARKER_X,V137_MARKER_Y
    )
    p86_conv_pc,p86_conv_frame=make_npc_conversation_empty(
        V139_P86_ACTOR_ID
    )
    assert len(p86_face_pc)==2028 and len(p86_face_frame)==2041
    assert hashlib.sha256(p86_face_pc).hexdigest().upper()==(
        'A1438D64E154B13ABDB751276E842F1192F41B28B5E3E4E3849C733A1FFA2539'
    )
    assert hashlib.sha256(p86_face_frame).hexdigest().upper()==(
        'F78570AE5BF01FCC126590FAA36FEDCAA6A84B85AC6D719575758958553D35B3'
    )
    assert snappy_raw_decompress(p86_face_frame[8:])==p86_face_pc
    assert p86_face_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert p86_face_pc.count(u16tag(0x12,MOVEMENT_ATTR))==1
    p86_row=next(
        row for row in PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS
        if row[0]==V139_P86_INDEX
    )
    p86_heading=_heading_to_player(
        p86_row[2],p86_row[3],V137_MARKER_X,V137_MARKER_Y
    )
    expected_p86_movement=make_remote_movement_attr(
        V139_P86_ACTOR_ID,p86_row[2],p86_row[3],p86_row[4],p86_heading,
        mask=0x03,
    )
    assert p86_face_pc.count(expected_p86_movement)==1
    expected_p30_destination_attr=make_npc_attr(
        p30_marker_row[1],V112_MONSTER_ACTOR_ID,1,0,p30_marker_row[5],
        current_hp=V117_P30_EXACT_HP,max_hp=V117_P30_EXACT_HP,
        basic_name=V119_P30_TARGET_NAME,
    )
    assert p86_face_pc.count(expected_p30_destination_attr)==1
    v140_face_pc,v140_face_frame=make_v140_p86_face_state(
        V137_MARKER_X,V137_MARKER_Y
    )
    assert len(v140_face_pc)==2028 and len(v140_face_frame)==2041
    assert hashlib.sha256(v140_face_pc).hexdigest().upper()==(
        'B8F0B7E54B2A317109C174BBC31DD7EABC647EDE14E41874D12900EA1C983439'
    )
    assert hashlib.sha256(v140_face_frame).hexdigest().upper()==(
        '6A682109699F6BD769F6A73B2C891BE43ED7534DFB7B64C93A9B371F0E2A4E89'
    )
    assert snappy_raw_decompress(v140_face_frame[8:])==v140_face_pc
    assert v140_face_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert v140_face_pc.count(u16tag(0x12,MOVEMENT_ATTR))==1
    assert v140_face_pc.count(expected_p30_destination_attr)==1
    v140_face_diff=[
        offset for offset,(before,after) in enumerate(zip(
            p86_face_pc,v140_face_pc
        )) if before!=after
    ]
    assert v140_face_diff==[
        128,129,130,133,134,135,138,139,140,143,144,145
    ]
    harness_p86_heading=_heading_to_player(
        V140_P86_HARNESS_X,V140_P86_HARNESS_Y,
        V137_MARKER_X,V137_MARKER_Y,
    )
    harness_p86_face_movement=make_remote_movement_attr(
        V139_P86_ACTOR_ID,V140_P86_HARNESS_X,V140_P86_HARNESS_Y,
        V140_P86_HARNESS_Z,harness_p86_heading,mask=0x03,
    )
    assert v140_face_pc.count(expected_p86_movement)==0
    assert v140_face_pc.count(harness_p86_face_movement)==1
    assert len(p86_conv_pc)==34 and len(p86_conv_frame)==44
    assert hashlib.sha256(p86_conv_pc).hexdigest().upper()==(
        'AC77B65CE7A1C6C424466053435F07EE88613BC50BF436B452AE8EE5B2F1DFFC'
    )
    assert hashlib.sha256(p86_conv_frame).hexdigest().upper()==(
        '13C1F348992E471FB6BF1CCCB691112075C5F8431EDF1AD7903070AC3F1245BE'
    )
    assert snappy_raw_decompress(p86_conv_frame[8:])==p86_conv_pc

    v140_interaction_actions=v139_state.dispatch(p86_interaction)
    assert v140_interaction_actions==[
        ('V140_P86_HARNESS_SAFE_FULL20_FACE_ONCE',
         v140_face_pc,v140_face_frame,0.0),
        ('V140_P86_HARNESS_EMPTY_DEFAULT_CONVERSATION_ONCE',
         p86_conv_pc,p86_conv_frame,0.0),
    ]
    assert not v139_state.v139_p86_interaction_armed
    assert v139_state.v139_p86_choose_capture_count==1
    assert v139_state.v139_p86_face_sent
    assert v139_state.v139_p86_conversation_sent
    assert v139_state.dispatch(p86_interaction)==[]
    assert v139_state.v139_p86_choose_capture_count==1

    # The second observed shape (two Choose records plus final TargetPos) is
    # walked to its exact declared boundary and produces the same safe outputs.
    p86_double_tail_pc=v139_interaction_request(
        choose_ids=(V139_P86_ACTOR_ID,V139_P86_ACTOR_ID),
        trailing_target_pos=True,
    )
    assert parse_v139_p86_interaction_shape(
        parse_outer(p86_double_tail_pc)
    )[0]==2
    double_state=v139_destination_state('v139-double-choose-tail')
    assert double_state.dispatch(marker_targetpos)==[]
    assert double_state.dispatch(parse_outer(p86_double_tail_pc))==[
        ('V140_P86_HARNESS_SAFE_FULL20_FACE_ONCE',
         v140_face_pc,v140_face_frame,0.0),
        ('V140_P86_HARNESS_EMPTY_DEFAULT_CONVERSATION_ONCE',
         p86_conv_pc,p86_conv_frame,0.0),
    ]

    invalid_p86_interactions=(
        v139_interaction_request(target_id=V112_MONSTER_ACTOR_ID),
        v139_interaction_request(target_kind=1),
        v139_interaction_request(target_version=1),
        v139_interaction_request(choose_ids=(V112_MONSTER_ACTOR_ID,)),
        v139_interaction_request(choose_versions=(1,)),
        v139_interaction_request(outer_version=1),
        v139_interaction_request(outer_mask=3),
        v139_interaction_request(
            choose_ids=(V139_P86_ACTOR_ID,)*3
        ),
        v139_interaction_request(
            trailing_target_pos=True,target_pos_version=1
        ),
        v139_interaction_request(
            extra_tail=u16tag(0x12,SHOW_MESSAGE_VITAL)+u8tag(0x0B,0),
            declared_count=3,
        ),
        v139_interaction_request(declared_count=3),
        p86_interaction_pc+u8tag(0x08,0),
    )
    for ordinal,invalid_pc in enumerate(invalid_p86_interactions):
        state=v139_destination_state(f'v139-invalid-interaction-{ordinal}')
        assert state.dispatch(marker_targetpos)==[]
        assert state.v139_p86_interaction_armed
        assert parse_v139_p86_interaction_shape(parse_outer(invalid_pc)) is None
        assert state.dispatch(parse_outer(invalid_pc))==[]
        assert state.v139_p86_choose_capture_count==0
        assert not state.v139_p86_face_sent
        assert not state.v139_p86_conversation_sent

    intervening_state=v139_destination_state('v139-intervening-targetpos')
    assert intervening_state.dispatch(marker_targetpos)==[]
    assert intervening_state.v139_p86_interaction_armed
    assert intervening_state.dispatch(parse_outer(target_far))==[]
    assert not intervening_state.v139_p86_interaction_armed
    assert intervening_state.dispatch(p86_interaction)==[]

    # V141 restores only the V95 >=1000-unit set-membership refresh after the
    # V140 P86 conversation. Retained P86 receives no MovementAttr, so its live
    # synthetic harness position is preserved. After an actual leave/re-entry,
    # P86 is an entrant and receives the authentic decoded placement instead.
    def target_pos_request(x: float, y: float, z: float) -> ParsedOuter:
        pc=(
            u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+
            u8tag(0x08,0)+u8tag(0x0B,2)+u16tag(0x12,1)+
            u16tag(0x12,TARGET_POS_VITAL)+u8tag(0x0B,0)+
            f32tag(x)+f32tag(y)+f32tag(z)+f32tag(0.0)+
            u8tag(0x0B,1)+u8tag(0x0B,0)
        )
        parsed_target=parse_outer(pc)
        assert parse_target_pos_vital(parsed_target)==(x,y,z,0.0,0,1)
        assert parse_v141_refresh_target_pos(parsed_target)==(x,y,z,0.0,0,1)
        return parsed_target

    refresh_state=v139_destination_state('v141-population-continuity')
    refresh_state.v139_p86_face_sent=True
    refresh_state.v139_p86_conversation_sent=True
    refresh_state.last_target_pos=(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0
    )
    # Strictly below the threshold: no scan, no send, no anchor advance.
    assert refresh_state.dispatch(target_pos_request(
        V137_MARKER_X+999.0,V137_MARKER_Y,V137_MARKER_Z
    ))==[]
    assert refresh_state.population_refresh_anchor==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    assert refresh_state.v141_population_refresh_count==0

    negative_refresh=v139_destination_state('v141-invalid-targetpos')
    negative_refresh.v139_p86_face_sent=True
    negative_refresh.v139_p86_conversation_sent=True
    negative_refresh.last_target_pos=(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0
    )
    malformed_targetpos=(
        V139_MARKER1_TARGETPOS_PC[:20]+bytes((0x19,))+
        V139_MARKER1_TARGETPOS_PC[21:]
    )
    assert negative_refresh.dispatch(parse_outer(malformed_targetpos))==[]
    nan_targetpos_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+
        u8tag(0x08,0)+u8tag(0x0B,2)+u16tag(0x12,1)+
        u16tag(0x12,TARGET_POS_VITAL)+u8tag(0x0B,0)+
        f32tag(float('nan'))+f32tag(V137_MARKER_Y)+
        f32tag(V137_MARKER_Z)+f32tag(0.0)+u8tag(0x0B,1)+
        u8tag(0x0B,0)
    )
    assert negative_refresh.dispatch(parse_outer(nan_targetpos_pc))==[]
    trailing_targetpos=target_pos_request(
        V137_MARKER_X+5000.0,V137_MARKER_Y,V137_MARKER_Z
    ).raw_pc+u8tag(0x08,0)
    assert parse_v141_refresh_target_pos(parse_outer(trailing_targetpos)) is None
    assert negative_refresh.dispatch(parse_outer(trailing_targetpos))==[]
    assert negative_refresh.population_refresh_anchor==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    assert negative_refresh.last_target_pos==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0
    )
    assert negative_refresh.v141_population_refresh_count==0
    assert 'v141_target_pos_nonfinite_rejected' in negative_refresh.events

    # The exact 1000-unit marker->P65 vector rounds through f32 to just under
    # the threshold, so it must not trigger. The corresponding 1100-unit vector
    # is safely over and deterministically changes membership by P91/P70.
    p65_vector_1000=(-9447.74609375,-1225.26220703125,550.4468383789062)
    p65_vector_1000_travel=math.sqrt(sum(
        (value-anchor)**2 for value,anchor in zip(
            p65_vector_1000,
            (V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z),
        )
    ))
    assert abs(p65_vector_1000_travel-999.9997503660327)<1e-9
    assert p65_vector_1000_travel<V94_REFRESH_DISTANCE
    assert refresh_state.dispatch(target_pos_request(*p65_vector_1000))==[]
    assert refresh_state.population_refresh_anchor==(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z
    )
    assert refresh_state.v141_population_refresh_count==0

    # A separate exact-axis fixture proves V95 ordering-only suppression and
    # anchor advancement at an exactly representable >=1000 distance.
    ordering_state=v139_destination_state('v141-ordering-only-scan')
    ordering_state.v139_p86_face_sent=True
    ordering_state.v139_p86_conversation_sent=True
    ordering_state.last_target_pos=(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,0.0
    )
    assert ordering_state.dispatch(target_pos_request(
        V137_MARKER_X+V94_REFRESH_DISTANCE,
        V137_MARKER_Y,V137_MARKER_Z,
    ))==[]
    assert ordering_state.population_refresh_anchor==(
        V137_MARKER_X+V94_REFRESH_DISTANCE,
        V137_MARKER_Y,V137_MARKER_Z,
    )
    assert ordering_state.population_indices==V138_MARKER1_NEAREST_INDICES
    assert ordering_state.v141_population_refresh_count==0
    assert 'v141_population_scan_membership_unchanged' in ordering_state.events

    p65_vector_1100=(-9360.3203125,-1272.2884521484375,538.3915405273438)
    p65_vector_1100_travel=math.sqrt(sum(
        (value-anchor)**2 for value,anchor in zip(
            p65_vector_1100,
            (V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z),
        )
    ))
    assert abs(p65_vector_1100_travel-1100.000076181786)<1e-9
    assert p65_vector_1100_travel>V94_REFRESH_DISTANCE
    retained_pc,retained_frame,retained_rows=make_v141_population_refresh_state(
        *p65_vector_1100,set(V138_MARKER1_NEAREST_INDICES)
    )
    retained_indices=tuple(row[0] for row in retained_rows)
    assert retained_indices==(
        0,86,1,80,65,22,16,85,5,92,84,50,89,144,145,39,82,87,30,91
    )
    assert set(retained_indices)-set(V138_MARKER1_NEAREST_INDICES)=={91}
    assert set(V138_MARKER1_NEAREST_INDICES)-set(retained_indices)=={70}
    assert len(retained_pc)==2046 and len(retained_frame)==2059
    assert hashlib.sha256(retained_pc).hexdigest().upper()==(
        '0C21154D5A3058F81192A905DE7B82794CCB346DC7C45094EAA7DD0C42F7F457'
    )
    assert hashlib.sha256(retained_frame).hexdigest().upper()==(
        'B8E1B1D86595FB627C2FA5D2A64E989C3D4D1025B7BC28DD03E392685A4DE47C'
    )
    assert snappy_raw_decompress(retained_frame[8:])==retained_pc
    assert retained_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert retained_pc.count(u16tag(0x12,MOVEMENT_ATTR))==1
    assert retained_pc.count(expected_p30_destination_attr)==1
    assert retained_pc.count(authentic_p86_initial_movement)==0
    assert retained_pc.count(harness_p86_initial_movement)==0

    retained_actions=refresh_state.dispatch(target_pos_request(*p65_vector_1100))
    assert retained_actions==[ (
        'V141_LOCAL_REFRESH_ENTER[91]_LEAVE[70]',
        retained_pc,retained_frame,0.0,
    ) ]
    assert refresh_state.population_indices==retained_indices
    assert refresh_state.population_refresh_anchor==p65_vector_1100
    assert refresh_state.v141_population_refresh_count==1
    assert any(
        event.endswith('p86_retained_synthetic_no_movement')
        for event in refresh_state.events
    )

    # Travel to the proven V94 test point removes P86; returning to MARKER1
    # makes it an entrant. The re-entry wire must carry authentic P86 XYZ and
    # must never reapply the V140 synthetic harness XYZ.
    zero_x,zero_y,zero_z=0.0,0.0,931.0
    leave_pc,leave_frame,leave_rows=make_v141_population_refresh_state(
        zero_x,zero_y,zero_z,set(retained_indices)
    )
    leave_indices=tuple(row[0] for row in leave_rows)
    assert V139_P86_INDEX not in leave_indices
    leave_actions=refresh_state.dispatch(
        target_pos_request(zero_x,zero_y,zero_z)
    )
    assert leave_actions==[ (
        'V141_LOCAL_REFRESH_ENTER[60,68,70,79,88,146,147]_LEAVE[0,1,30,80,86,87,91]',
        leave_pc,leave_frame,0.0,
    ) ]
    assert len(leave_pc)==2381 and len(leave_frame)==2394
    assert hashlib.sha256(leave_pc).hexdigest().upper()==(
        '187CAEA3D442BD5666E730B225083556CF16DCEB0CC62C516D727643514254BB'
    )
    assert hashlib.sha256(leave_frame).hexdigest().upper()==(
        '76FE902F609BF990154D45325A6A1A1D43C9EB023D441D9EB27755C6D95050D1'
    )
    assert snappy_raw_decompress(leave_frame[8:])==leave_pc
    assert leave_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert leave_pc.count(u16tag(0x12,MOVEMENT_ATTR))==7
    assert refresh_state.population_indices==leave_indices
    assert refresh_state.v141_population_refresh_count==2

    reentry_pc,reentry_frame,reentry_rows=make_v141_population_refresh_state(
        V137_MARKER_X,V137_MARKER_Y,V137_MARKER_Z,set(leave_indices)
    )
    assert tuple(row[0] for row in reentry_rows)==V138_MARKER1_NEAREST_INDICES
    assert len(reentry_pc)==2340 and len(reentry_frame)==2353
    assert hashlib.sha256(reentry_pc).hexdigest().upper()==(
        '03754CB5E8B38368FFD19B7CCFE186B4172CF650954916BF49230F75FC6516E5'
    )
    assert hashlib.sha256(reentry_frame).hexdigest().upper()==(
        'F9C1424A2E8B4DF37878C3157CACBBAEF2367CF8EE7510C1481CF5CA349186C2'
    )
    assert snappy_raw_decompress(reentry_frame[8:])==reentry_pc
    assert reentry_pc.count(u16tag(0x12,NPC_ATTR))==20
    assert reentry_pc.count(u16tag(0x12,MOVEMENT_ATTR))==6
    assert reentry_pc.count(expected_p30_destination_attr)==1
    assert reentry_pc.count(authentic_p86_initial_movement)==1
    assert reentry_pc.count(harness_p86_initial_movement)==0
    reentry_actions=refresh_state.dispatch(marker_targetpos)
    assert reentry_actions==[ (
        'V141_LOCAL_REFRESH_ENTER[0,1,30,80,86,87]_LEAVE[60,68,79,88,146,147]',
        reentry_pc,reentry_frame,0.0,
    ) ]
    assert refresh_state.population_indices==V138_MARKER1_NEAREST_INDICES
    assert refresh_state.v141_population_refresh_count==3
    assert any(
        event.endswith('p86_reentered_authentic_movement')
        for event in refresh_state.events
    )

    p30_target_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,TARGET_VITAL)+
        u8tag(0x0B,0)+qwordtag(0x32,V112_MONSTER_ACTOR_ID)+u8tag(0x08,2)
    )
    p30_target=parse_outer(p30_target_pc)
    assert parse_target_vital(p30_target)==(V112_MONSTER_ACTOR_ID,2)
    p30_summary=describe_capture_event(p30_target,rst)
    assert 'placement=P30' in p30_summary and 'template=31' in p30_summary
    assert 'current_member=1' in p30_summary and 'payload_hex=' in p30_summary
    assert rst.dispatch(p30_target)==[]
    p30_choose=parse_outer(choose_request(V112_MONSTER_ACTOR_ID))
    assert parse_choose_npc(p30_choose)==V112_MONSTER_ACTOR_ID
    assert rst.dispatch(p30_choose)==[]
    assert 'v112_choose_p30_usage1_no_npc_response' in rst.events

    # Both audited actor classes emit the same runtime-proven TargetVital kind
    # 2. V119 therefore sends no target response: the name/HP frame is populated
    # locally from P30 BasicAttr by client paths 0x51F920/0x51F150.
    p91_target_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,TARGET_VITAL)+
        u8tag(0x0B,0)+qwordtag(0x32,V112_SHOP_TRIGGER_ACTOR_ID)+u8tag(0x08,2)
    )
    p91_target=parse_outer(p91_target_pc)
    assert parse_target_vital(p91_target)==(V112_SHOP_TRIGGER_ACTOR_ID,2)
    assert rst.dispatch(p91_target)==[]

    # V128 captures only the statically exact target-bound WIELD/Z action.
    # A fresh state and a new exact P30 TargetVital are required for every
    # ActionVital attempt; all paths remain capture-only and return no packet.
    # Data provenance: HOTKEY 71/WIELD/n_KEY_2 90, HOTKEY_TIP 71
    # `เก็บอาวุธ`, KEY_TIP 90 `Z`; dispatcher 0x450B20 -> 0x451026.
    assert V128_WIELD_HOTKEY_ID==71
    assert V128_WIELD_KEY_CODE==90
    assert V128_WIELD_HOTKEY_NAME=="WIELD"
    assert V128_WIELD_THAI_LABEL=="เก็บอาวุธ"
    assert V128_WIELD_ACTION_CODE==0xEA7E
    action_state=GameSessionState('v128-wield-z-action-capture')
    action_state.teleport_sent=True
    action_state.runtime_ack_sent=True
    action_state.welcome_message_sent=True
    action_state.current_scene_music_sent=True
    action_state.npc_spawn_sent=True
    action_state.population_indices=V112_TEST_INDICES
    action_state.last_target_pos=(
        player_test_x,V112_PLAYER_Y,V112_PLAYER_Z,0.0
    )

    def arm_p30_action_target() -> None:
        assert action_state.dispatch(p30_target)==[]
        assert action_state.p30_action_target_armed
        assert action_state.action_target_last_identity==V126_ACTION_TARGET_ACTOR_ID
        assert action_state.action_target_last_kind==V126_ACTION_TARGET_KIND

    action_pc=_synthetic_action_vital_pc()
    expected_action_pc=bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 '
        '12 EA 1A 0B 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 1F 20 00 00 00 00 00 00 '
        '14 7E EA 00 00 19 00 00 00 00 '
        '2A 00 00 00 3F 2A 00 00 C8 42 '
        '2A 00 00 48 43 2A 00 C0 68 44 '
        '0B 00 12 01 00 0B 00'
    )
    assert action_pc==expected_action_pc
    assert len(action_pc)==20+V126_ACTION_VITAL_BODY_BYTES==84
    action_parsed=parse_outer(action_pc)
    assert action_parsed.outer_version==0 and action_parsed.outer_mask==0x02
    assert action_parsed.vital_count==1
    assert action_parsed.nested_id==ACTION_VITAL
    assert action_parsed.nested_version==0
    action_fields=parse_action_vital(action_parsed)
    assert action_fields=={
        'field_qword_18':0,
        'field_qword_20':0,
        'field_qword_28':V126_ACTION_TARGET_ACTOR_ID,
        'action_u32_30':V128_WIELD_ACTION_CODE,
        'field_u32_34':0,
        'heading_f32_38':0.5,
        'x_f32_3c':100.0,
        'y_f32_40':200.0,
        'z_f32_44':931.0,
        'field_u8_48':0,
        'field_u16_4a':1,
        'field_u8_4c':0,
        'consumed_bytes':V126_ACTION_VITAL_BODY_BYTES,
        'trailing_bytes':0,
    }
    action_summary=describe_capture_event(action_parsed,action_state)
    assert 'name=ActionVital' in action_summary
    assert 'action_30=0x0000EA7E' in action_summary
    assert 'body_bytes=64' in action_summary
    arm_p30_action_target()
    assert action_state.dispatch(action_parsed)==[]
    assert action_state.action_vital_capture_count==1
    assert action_state.action_vital_last_fields==action_fields
    assert not action_state.p30_action_target_armed
    assert any(
        event.endswith('armed_1_exact_1') for event in action_state.events
    )

    # A replay without a new P30 TargetVital is deliberately not captured.
    assert action_state.dispatch(action_parsed)==[]
    assert action_state.action_vital_capture_count==1
    assert any(
        event.endswith('armed_0_exact_0') for event in action_state.events
    )

    # The fixed 64-byte body remains exact when the client batches another
    # tagged vital behind it. Later vital semantics are intentionally opaque.
    extra_target_pos=(
        u16tag(0x12,TARGET_POS_VITAL)+u8tag(0x0B,0)
        +f32tag(100.0)+f32tag(200.0)+f32tag(931.0)+f32tag(0.5)
        +u8tag(0x0B,1)+u8tag(0x0B,0)
    )
    multi_action=parse_outer(_synthetic_action_vital_pc(
        field_u8_48=7,field_u16_4a=0x1234,extra_nested=extra_target_pos
    ))
    multi_fields=parse_action_vital(multi_action)
    assert multi_action.vital_count==2
    assert multi_fields['consumed_bytes']==64
    assert multi_fields['trailing_bytes']==len(extra_target_pos)==29
    assert multi_fields['field_u8_48']==7
    assert multi_fields['field_u16_4a']==0x1234
    arm_p30_action_target()
    assert action_state.dispatch(multi_action)==[]
    assert action_state.action_vital_capture_count==2
    assert action_state.action_vital_last_fields==multi_fields

    # Every statically fixed gate field and both envelope versions are negative
    # controls. Opaque +0x48/+0x4A were positively accepted above and are never
    # assigned a guessed semantic or value restriction.
    invalid_action_pcs=[
        _synthetic_action_vital_pc(field_qword_18=1),
        _synthetic_action_vital_pc(field_qword_20=1),
        _synthetic_action_vital_pc(field_qword_28=V112_SHOP_TRIGGER_ACTOR_ID),
        _synthetic_action_vital_pc(action_u32_30=0xEA60),
        _synthetic_action_vital_pc(field_u32_34=1),
        _synthetic_action_vital_pc(heading_f32_38=float('nan')),
        _synthetic_action_vital_pc(field_u8_4c=1),
        _synthetic_action_vital_pc(outer_version=1),
        _synthetic_action_vital_pc(outer_mask=3),
        _synthetic_action_vital_pc(nested_version=1),
        action_pc+u8tag(0x0B,0),
    ]
    for invalid_pc in invalid_action_pcs:
        arm_p30_action_target()
        assert action_state.dispatch(parse_outer(invalid_pc))==[]
        assert action_state.action_vital_capture_count==2
        assert not action_state.p30_action_target_armed

    # Selecting the usage-2 P91 control disarms the P30 action boundary.
    assert action_state.dispatch(p91_target)==[]
    assert not action_state.p30_action_target_armed
    assert action_state.action_target_last_identity==V112_SHOP_TRIGGER_ACTOR_ID
    assert action_state.action_target_last_kind==2
    assert action_state.dispatch(action_parsed)==[]
    assert action_state.action_vital_capture_count==2

    # Fresh A/B state keeps the store one-shot assertion independent of the P30 path.
    shop_state=GameSessionState('shop-control')
    shop_state.teleport_sent=True
    shop_state.runtime_ack_sent=True
    shop_state.welcome_message_sent=True
    shop_state.current_scene_music_sent=True
    shop_state.npc_spawn_sent=True
    shop_state.population_indices=V112_TEST_INDICES
    shop_state.last_target_pos=(player_test_x,V135_PLAYER_Y,V135_PLAYER_Z,0.0)
    p0_choose=parse_outer(choose_request(V129_QUEST_ACTOR_ID))
    p0_target_then_choose=parse_outer(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,2)+
        u16tag(0x12,TARGET_VITAL)+u8tag(0x0B,0)+
        qwordtag(0x32,V129_QUEST_ACTOR_ID)+u8tag(0x08,2)+
        u16tag(0x12,CHOOSE_NPC)+u8tag(0x0B,0)+
        qwordtag(0x32,V129_QUEST_ACTOR_ID)
    )
    assert extract_choose_npc_identities(p0_target_then_choose)==[
        V129_QUEST_ACTOR_ID
    ]
    p0_state=GameSessionState('v134-p0-conversation')
    p0_state.teleport_sent=True
    p0_state.runtime_ack_sent=True
    p0_state.welcome_message_sent=True
    p0_state.current_scene_music_sent=True
    p0_state.npc_spawn_sent=True
    p0_state.population_indices=V112_TEST_INDICES
    p0_state.last_target_pos=(
        player_test_x,V135_PLAYER_Y,V135_PLAYER_Z,0.0
    )
    p0_actions=p0_state.dispatch(p0_target_then_choose)
    assert [action[0] for action in p0_actions]==[
        'V98_NPC_FACE_PLAYER_POSITION_HEADING_P0',
        'V134_P0_Q3020_NPC_CONVERSATION_ONCE',
    ]
    assert p0_actions[1][1]==quest_conversation_pc
    assert p0_actions[1][2]==quest_conversation_frame
    assert p0_state.quest3020_conversation_sent
    duplicate_p0=p0_state.dispatch(p0_choose)
    assert [action[0] for action in duplicate_p0]==[
        'V98_NPC_FACE_PLAYER_POSITION_HEADING_P0',
    ]
    assert 'v134_p0_q3020_npc_conversation_duplicate_suppressed' in p0_state.events

    p91_choose=parse_outer(choose_request(V112_SHOP_TRIGGER_ACTOR_ID))
    p91_summary=describe_capture_event(p91_choose,shop_state)
    assert 'placement=P91' in p91_summary and 'template=91' in p91_summary
    p91_actions=shop_state.dispatch(p91_choose)
    assert [a[0] for a in p91_actions]==[
        'V112_TEST_HARNESS_FACE_PLAYER_P91',
        'V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL',
    ]
    face_pc=p91_actions[0][1]
    assert face_pc.count(u16tag(0x12,NPC_ATTR))==3
    assert face_pc.count(u16tag(0x12,MOVEMENT_ATTR))==1
    assert face_pc.count(u16tag(0x12,ACTION_VITAL))==0
    assert face_pc.count(u16tag(0x12,0x1285))==0
    p91_row=next(row for row in population_rows if row[0]==91)
    expected_face_movement=make_remote_movement_attr(
        V112_SHOP_TRIGGER_ACTOR_ID,p91_row[2],p91_row[3],p91_row[4],
        _heading_to_player(p91_row[2],p91_row[3],player_test_x,V135_PLAYER_Y),
        mask=0x03,
    )
    assert expected_face_movement in face_pc
    assert snappy_raw_decompress(p91_actions[0][2][8:])==face_pc
    assert p91_actions[1][1]==shop_pc and p91_actions[1][2]==shop_frame
    assert u16tag(0x12,NPC_CONVERSATION) not in face_pc
    assert u16tag(0x12,NPC_CONVERSATION) not in shop_pc
    duplicate_p91=shop_state.dispatch(p91_choose)
    assert len(duplicate_p91)==1 and duplicate_p91[0][0]=='V112_TEST_HARNESS_FACE_PLAYER_P91'
    assert 'v112_store5_duplicate_open_suppressed' in shop_state.events

    mixed_state=GameSessionState('mixed-control')
    mixed_state.teleport_sent=True
    mixed_state.runtime_ack_sent=True
    mixed_state.welcome_message_sent=True
    mixed_state.current_scene_music_sent=True
    mixed_state.npc_spawn_sent=True
    mixed_state.population_indices=V112_TEST_INDICES
    mixed_state.last_target_pos=(player_test_x,V135_PLAYER_Y,V135_PLAYER_Z,0.0)
    mixed=parse_outer(choose_request(
        V112_MONSTER_ACTOR_ID,V112_SHOP_TRIGGER_ACTOR_ID
    ))
    assert extract_choose_npc_identities(mixed)==[
        V112_MONSTER_ACTOR_ID,V112_SHOP_TRIGGER_ACTOR_ID
    ]
    mixed_actions=mixed_state.dispatch(mixed)
    assert [a[0] for a in mixed_actions]==[
        'V112_TEST_HARNESS_FACE_PLAYER_P91',
        'V112_TEST_HARNESS_TRADE_ZOOM_STORE5_SWORD_SOUL',
    ]

    # Preserve V97/V98 for an ordinary data-backed usage-2 city actor outside
    # the special V112 test pair.
    legacy=GameSessionState('legacy-p5')
    legacy.teleport_sent=True
    legacy.runtime_ack_sent=True
    legacy.welcome_message_sent=True
    legacy.current_scene_music_sent=True
    legacy.npc_spawn_sent=True
    legacy.population_indices=(5,)
    legacy.last_target_pos=(0.0,0.0,931.0,0.0)
    p5_aid=0x2000+5+1
    legacy_actions=legacy.dispatch(parse_outer(choose_request(p5_aid)))
    assert [a[0] for a in legacy_actions]==[
        'V98_NPC_FACE_PLAYER_POSITION_HEADING_P5',
        'V98_NPC_CONVERSATION_DEFAULT_P5',
    ]
    noncurrent=GameSessionState('noncurrent')
    noncurrent.teleport_sent=True
    noncurrent.runtime_ack_sent=True
    noncurrent.welcome_message_sent=True
    noncurrent.current_scene_music_sent=True
    noncurrent.npc_spawn_sent=True
    noncurrent.population_indices=V112_TEST_INDICES
    noncurrent.last_target_pos=(player_test_x,V135_PLAYER_Y,V135_PLAYER_Z,0.0)
    assert noncurrent.dispatch(parse_outer(choose_request(0x2FFF)))==[]

    # V118's only response boundary is the statically mapped normal-store
    # add-to-buy-cart request. V120 runtime captured identity zero; it is copied
    # byte-exactly into the standalone response ItemAttr.
    captured_detail_identity = 0
    trade_req_pc = _synthetic_trade_cmd_pc(
        V118_TRADE_CART_ADD_COMMAND,
        V118_TRADE_CART_ADD_DWORD,
        (captured_detail_identity, V112_STORE_PRODUCT_TEMPLATE, 1),
    )
    expected_trade_req_pc=bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 '
        'B5 23 0B 00 08 06 19 00 00 00 00 08 01 '
        '32 00 00 00 00 00 00 00 00 14 C9 91 21 00 0F 01 00'
    )
    assert trade_req_pc==expected_trade_req_pc
    assert len(trade_req_pc)==46
    trade_parsed = parse_outer(trade_req_pc)
    assert parse_trade_cmd_vital(trade_parsed)=={
        'field_u8':V118_TRADE_CART_ADD_COMMAND,
        'field_u32':V118_TRADE_CART_ADD_DWORD,
        'has_detail':1,'detail_identity':captured_detail_identity,
        'detail_template':V112_STORE_PRODUCT_TEMPLATE,'detail_quantity':1,
    }
    trade_summary=describe_capture_event(trade_parsed,shop_state)
    assert 'name=TradeCmdVital' in trade_summary
    assert f'detail_template={V112_STORE_PRODUCT_TEMPLATE}' in trade_summary
    before_inventory=(
        shop_state.item_slot,shop_state.item_quantity,
        shop_state.stack_source_present,shop_state.stack_merge_count,
    )
    trade_actions=shop_state.dispatch(trade_parsed)
    assert [a[0] for a in trade_actions]==[
        'V118_TRADE_SHOP_STORE_BY_ITEM_OK_CART_ACK'
    ]
    expected_trade_result_pc=bytes.fromhex(
        '12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 '
        '7B 55 0B 00 08 0D 08 00 19 00 00 00 00 08 01 '
        '32 00 00 00 00 00 00 00 00 14 C9 91 21 00 0F 01 00 '
        '0F FF FF 08 00 08 FF 0B 00 0B 00'
    )
    assert len(expected_trade_result_pc)==59
    assert trade_actions[0][1]==expected_trade_result_pc
    assert trade_actions[0][2]==frame_pc(expected_trade_result_pc)
    assert len(trade_actions[0][2])==69
    assert snappy_raw_decompress(trade_actions[0][2][8:])==expected_trade_result_pc
    result_parsed=parse_outer(expected_trade_result_pc)
    assert result_parsed.outer_id==GSCN_RUNTIME_PROTOCOL_RES
    assert result_parsed.outer_version==4 and result_parsed.outer_mask==0x02
    assert result_parsed.vital_count==1
    assert result_parsed.nested_id==TRADE_ITEM_RESULT_VITAL
    assert result_parsed.nested_version==0
    assert result_parsed.nested_payload==bytes.fromhex(
        '08 0D 08 00 19 00 00 00 00 08 01 '
        '32 00 00 00 00 00 00 00 00 14 C9 91 21 00 0F 01 00 '
        '0F FF FF 08 00 08 FF 0B 00 0B 00'
    )
    assert shop_state.trade_cart_ack_count==1
    assert shop_state.trade_cart_last_ack_detail==(
        0,V112_STORE_PRODUCT_TEMPLATE,1
    )
    assert shop_state.trade_final_buy_capture_count==0
    assert (
        shop_state.item_slot,shop_state.item_quantity,
        shop_state.stack_source_present,shop_state.stack_merge_count,
    )==before_inventory
    assert shop_state.current_cash==V116_INITIAL_CASH
    assert u16tag(0x12,BACKPACK_ATTR) not in expected_trade_result_pc
    assert u16tag(0x12,ITEM_OPERATE_RES_VITAL) not in expected_trade_result_pc
    # The cash milestone is deliberately one-cart only. Replaying the exact
    # cart request before Buy does not receive a second acknowledgement.
    assert shop_state.dispatch(trade_parsed)==[]
    assert shop_state.trade_cart_ack_count==1
    assert shop_state.current_cash==V116_INITIAL_CASH

    # V120 runtime-proven final Buy boundary: exact 29-byte cmd8/u32=0/no-detail.
    # V122 recognizes it only after one exact cart acknowledgement and returns
    # one cash-only UpdateAttr. No purchase-result or inventory Attr is sent.
    expected_final_buy_pc=_synthetic_trade_cmd_pc(
        V121_CAPTURED_FINAL_BUY_COMMAND,V121_CAPTURED_FINAL_BUY_DWORD,None
    )
    assert expected_final_buy_pc==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 '
        'B5 23 0B 00 08 08 19 00 00 00 00 08 00'
    )
    assert len(expected_final_buy_pc)==29
    expected_final_buy=parse_trade_cmd_vital(parse_outer(expected_final_buy_pc))
    assert expected_final_buy=={
        'field_u8':8,'field_u32':0,'has_detail':0,
    }
    before_final_buy_inventory=(
        shop_state.item_slot,shop_state.item_quantity,
        shop_state.stack_source_present,shop_state.stack_merge_count,
    )
    final_buy_actions=shop_state.dispatch(parse_outer(expected_final_buy_pc))
    assert [a[0] for a in final_buy_actions]==[
        'V122_UPDATE_ATTR_ACTOR_CASH_10000_TO_0_ONCE'
    ]
    expected_cash_actor=bytes.fromhex(
        '0B 01 32 00 00 00 00 00 00 00 00 12 0C 03 '
        '14 64 00 00 00 14 64 00 00 00 12 01 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 00 08 00 00 00 00 00 00 05 01 '
        '32 00 00 00 00 00 00 00 00'
    )
    assert len(expected_cash_actor)==56
    assert make_actor_attr_minimal(cash=V122_FINAL_CASH)==expected_cash_actor
    initial_cash_actor=make_actor_attr_minimal(cash=V116_INITIAL_CASH)
    assert len(initial_cash_actor)==len(expected_cash_actor)==56
    assert initial_cash_actor[:48]==expected_cash_actor[:48]
    assert initial_cash_actor[48:56]==struct.pack('<Q',V116_INITIAL_CASH)
    assert expected_cash_actor[48:56]==struct.pack('<Q',V122_FINAL_CASH)
    assert [
        i for i,(before,after) in enumerate(zip(initial_cash_actor,expected_cash_actor))
        if before!=after
    ]==[48,49]
    expected_update_attr_payload=(
        u16tag(0x12,1)+u16tag(0x12,ACTOR_ATTR)
        +u32tag(0x14,len(expected_cash_actor))+expected_cash_actor
    )
    assert len(expected_update_attr_payload)==67
    assert expected_update_attr_payload==bytes.fromhex(
        '12 01 00 12 AD 12 14 38 00 00 00 '
        '0B 01 32 00 00 00 00 00 00 00 00 12 0C 03 '
        '14 64 00 00 00 14 64 00 00 00 12 01 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 00 08 00 00 00 00 00 00 05 01 '
        '32 00 00 00 00 00 00 00 00'
    )
    expected_cash_pc=bytes.fromhex(
        '12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 '
        '12 9A 30 0B 00 '
        '12 01 00 12 AD 12 14 38 00 00 00 '
        '0B 01 32 00 00 00 00 00 00 00 00 12 0C 03 '
        '14 64 00 00 00 14 64 00 00 00 12 01 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 00 08 00 00 00 00 00 00 05 01 '
        '32 00 00 00 00 00 00 00 00 0B 00'
    )
    assert len(expected_cash_pc)==89
    expected_cash_frame=frame_pc(expected_cash_pc)
    assert len(expected_cash_frame)==100
    assert expected_cash_frame==bytes.fromhex(
        'AC 3E 25 5F 5C 00 00 00 59 F0 58 '
        '12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 '
        '12 9A 30 0B 00 '
        '12 01 00 12 AD 12 14 38 00 00 00 '
        '0B 01 32 00 00 00 00 00 00 00 00 12 0C 03 '
        '14 64 00 00 00 14 64 00 00 00 12 01 00 '
        '32 00 00 00 00 00 00 00 00 '
        '32 00 08 00 00 00 00 00 00 05 01 '
        '32 00 00 00 00 00 00 00 00 0B 00'
    )
    assert final_buy_actions[0][1]==expected_cash_pc
    assert final_buy_actions[0][2]==expected_cash_frame
    assert snappy_raw_decompress(expected_cash_frame[8:])==expected_cash_pc
    cash_parsed=parse_outer(expected_cash_pc)
    assert cash_parsed.outer_id==GSCN_RUNTIME_PROTOCOL_RES
    assert cash_parsed.outer_version==4 and cash_parsed.outer_mask==0x02
    assert cash_parsed.vital_count==1
    assert cash_parsed.nested_id==UPDATE_ATTR_VITAL
    assert cash_parsed.nested_version==0
    # ParsedOuter intentionally exposes the remaining RuntimeRes bytes after
    # the nested Vital header, including the required derived trailing mask.
    assert cash_parsed.nested_payload==expected_update_attr_payload+u8tag(0x0B,0)
    assert expected_cash_pc.endswith(u8tag(0x0B,0))
    assert u16tag(0x12,TRADE_ITEM_RESULT_VITAL) not in expected_cash_pc
    assert u16tag(0x12,BACKPACK_ATTR) not in expected_cash_pc
    assert u16tag(0x12,ITEM_ATTR) not in expected_cash_pc
    assert u16tag(0x12,ITEM_OPERATE_RES_VITAL) not in expected_cash_pc
    assert shop_state.trade_final_buy_capture_count==1
    assert shop_state.trade_final_buy_last_cart_ack_count==1
    assert shop_state.current_cash==V122_FINAL_CASH
    assert (
        shop_state.item_slot,shop_state.item_quantity,
        shop_state.stack_source_present,shop_state.stack_merge_count,
    )==before_final_buy_inventory
    assert any(
        event==(
            'v122_trade_cmd8_dword0_no_detail_cash_update_sent_'
            'capture1_cart_ack_count1_last_identity0_'
            f'template{V112_STORE_PRODUCT_TEMPLATE}_quantity1_cash10000_to_0'
        )
        for event in shop_state.events
    )

    # A duplicate final Buy with no intervening acknowledged cart add is the
    # explicit wrong-sequence boundary and remains no-reply.
    assert shop_state.dispatch(parse_outer(expected_final_buy_pc))==[]
    assert shop_state.trade_final_buy_capture_count==1
    assert shop_state.current_cash==V122_FINAL_CASH
    assert any(
        'v122_trade_cmd8_dword0_no_detail_final_buy_wrong_sequence_no_reply_'
        in event for event in shop_state.events
    )
    # Replaying the cart add after the one acknowledged tuple/cash transition
    # is also no-reply and cannot create a second cash transaction.
    assert shop_state.dispatch(trade_parsed)==[]
    assert shop_state.trade_cart_ack_count==1
    assert shop_state.current_cash==V122_FINAL_CASH

    # The captured close sequence is cmd12/u32=0/no-detail. Each attempt is
    # journaled independently, receives no reply, and does not mark Store 5
    # closed because runtime showed the UI remained open.
    expected_store_close_pc=_synthetic_trade_cmd_pc(
        V121_CAPTURED_STORE_CLOSE_COMMAND,V121_CAPTURED_STORE_CLOSE_DWORD,None
    )
    assert expected_store_close_pc==bytes.fromhex(
        '12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 '
        'B5 23 0B 00 08 0C 19 00 00 00 00 08 00'
    )
    assert parse_trade_cmd_vital(parse_outer(expected_store_close_pc))=={
        'field_u8':12,'field_u32':0,'has_detail':0,
    }
    assert shop_state.shop_store5_open_sent
    assert shop_state.dispatch(parse_outer(expected_store_close_pc))==[]
    assert shop_state.dispatch(parse_outer(expected_store_close_pc))==[]
    assert shop_state.trade_store_close_capture_count==2
    assert shop_state.shop_store5_open_sent

    # Exact final Buy on a fresh state is rejected as wrong-sequence. Malformed,
    # wrong-version, nonzero, detailed, and unsupported requests never reply.
    wrong_sequence_state=GameSessionState('v122-final-buy-wrong-sequence')
    wrong_sequence_state.teleport_sent=True
    wrong_sequence_state.runtime_ack_sent=True
    wrong_sequence_state.welcome_message_sent=True
    wrong_sequence_state.current_scene_music_sent=True
    wrong_identity_cart_pc=_synthetic_trade_cmd_pc(
        V118_TRADE_CART_ADD_COMMAND,V118_TRADE_CART_ADD_DWORD,
        (1,V112_STORE_PRODUCT_TEMPLATE,1),
    )
    assert wrong_sequence_state.dispatch(parse_outer(wrong_identity_cart_pc))==[]
    assert wrong_sequence_state.trade_cart_ack_count==0
    assert wrong_sequence_state.current_cash==V116_INITIAL_CASH
    assert wrong_sequence_state.dispatch(parse_outer(expected_final_buy_pc))==[]
    assert wrong_sequence_state.trade_final_buy_capture_count==0
    assert any('wrong_sequence_no_reply' in e for e in wrong_sequence_state.events)
    detail_presence_two=bytearray(trade_req_pc)
    detail_presence_two[28]=2
    vital_count_two=bytearray(trade_req_pc)
    vital_count_two[13:15]=struct.pack('<H',2)
    unsupported_trade_requests=(
        _synthetic_trade_cmd_pc(7,0,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,1)),
        _synthetic_trade_cmd_pc(6,8,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,1)),
        _synthetic_trade_cmd_pc(6,0,None),
        _synthetic_trade_cmd_pc(6,0,(captured_detail_identity,2600001,1)),
        _synthetic_trade_cmd_pc(6,0,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,2)),
        _synthetic_trade_cmd_pc(8,1,None),
        _synthetic_trade_cmd_pc(8,0,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,1)),
        _synthetic_trade_cmd_pc(12,1,None),
        _synthetic_trade_cmd_pc(12,0,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,1)),
        bytes(detail_presence_two),
        bytes(vital_count_two),
        _synthetic_trade_cmd_pc(
            6,0,(captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,1),
            nested_version=1,
        ),
    )
    for unsupported_trade_pc in unsupported_trade_requests:
        assert shop_state.dispatch(parse_outer(unsupported_trade_pc))==[]
    malformed_trade_pc=(
        u16tag(0x12,GSCN_RUNTIME_PROTOCOL_REQ)+u32tag(0x14,0)+u8tag(0x08,0)+
        u8tag(0x0B,2)+u16tag(0x12,1)+u16tag(0x12,TRADE_CMD_VITAL)+
        u8tag(0x0B,0)+u8tag(0x08,6)+u32tag(0x19,0)+u8tag(0x08,1)
    )
    assert shop_state.dispatch(parse_outer(malformed_trade_pc))==[]
    assert shop_state.trade_cart_ack_count==1
    assert shop_state.trade_final_buy_capture_count==1
    assert shop_state.trade_store_close_capture_count==2
    invalid_result_args=(
        (-1,V112_STORE_PRODUCT_TEMPLATE,1),
        (0x10000000000000000,V112_STORE_PRODUCT_TEMPLATE,1),
        (captured_detail_identity,2600001,1),
        (captured_detail_identity,V112_STORE_PRODUCT_TEMPLATE,2),
    )
    for invalid_args in invalid_result_args:
        try:
            make_trade_item_result_store_buy_cart_ack(*invalid_args)
        except ValueError:
            pass
        else:
            raise AssertionError(f'V118 accepted invalid cart ack args {invalid_args!r}')

    if verbose:
        print("[SELFTEST] PASS: structural outer/nested parser; empty GSCN is no-op")
        print("[SELFTEST] PASS: initial LoginVerify -> ACK + runtime-proven v25 SelectActor v10 wire once")
        print("[SELFTEST] PASS: Notify(0/1) and duplicate LoginVerify -> no reply")
        print("[SELFTEST] PASS: runtime-proven SelectActor wire is 43 bytes")
        print("[SELFTEST] PASS: real v25 CreateActor decoded completely")
        print("[SELFTEST] PASS: V135 changes frozen V134 StartGame only by P0-50Y lateral harness; exact two-byte Y-float delta")
        print("[SELFTEST] PASS: V120 preserves V119 P30 BasicAttr name bit + exact Tornado Eagle UTF-16")
        print("[SELFTEST] PASS: V129 target-frame path is client-local; P0/P30/P91 TargetVital kind 2 retain prior semantics")
        print("[SELFTEST] PASS: V129 P30 keeps exact HP=3857/3857; P0/P91 are exact controls; zero FightAttr/ActionVital/AI/skills")
        print("[SELFTEST] PASS: V120 live Backpack differs from V119 by only +0x68 0B00->0B01; items/counts/slots/identities unchanged")
        print("[SELFTEST] PASS: V120 base Backpack predicts 40-3=37 free slots and Store UI cap 18")
        print("[SELFTEST] PASS: V123 adds exact identity4/template2200002/slot3 ItemAttr and matching full Backpack identity entry")
        print("[SELFTEST] PASS: V123 Backpack is the exact V122 wire plus one 26-byte item and one 9-byte identity; 36 free slots")
        print("[SELFTEST] PASS: V123 exact ItemOperate v0 op5/id4 accepts producer-mapped dword 8 or 16 and sends no response or mutation")
        print("[SELFTEST] PASS: V123 wrong-version/count/mask/identity/operation/trailing equipment probes remain no-reply")
        print("[SELFTEST] PASS: V134 exact P0 NPCConversation carries one q3020/type20 descriptor with constructor-default byte zero")
        print("[SELFTEST] PASS: V135 live-proven exact op1 after P0 conversation emits action6 once")
        print("[SELFTEST] PASS: V134 exact sequenced op2 emits the live-proven action1 Accept_Run result once")
        print("[SELFTEST] PASS: V134 pre-conversation/pre-action6/replay/wrong tuple/envelope/trailing probes stay no-reply")
        print("[SELFTEST] PASS: V131 emits exact 25-byte TeleportCheck v0/value1 RuntimeRes challenge with trailing mask")
        print("[SELFTEST] PASS: V131 exact 23-byte RuntimeReq echo is capture-only after challenge; wrong variants do not advance")
        print("[SELFTEST] PASS: V135 scheduler preserves V134 population-only cumulative 0+3s; no timed TeleportCheck or automatic quest UI")
        print("[SELFTEST] PASS: V136 op2/action1 arms only; first exact 12B RuntimeReq v0/mask0 queues V131 MARKER1 prompt once")
        print("[SELFTEST] PASS: V136 exact 23B MARKER1 confirm is one-shot capture with no TeleportCheck reply")
        print("[SELFTEST] PASS: V136 presequence/replay/wrong outer/mask/nested/value/trailing probes do not advance")
        print("[SELFTEST] PASS: V136 labels q3020 Var2=1 -> MARKER1 as compositional hypothesis; no travel/vehicle/completion claim")
        print("[SELFTEST] PASS: V137 exact 64B RuntimeRes TeleportVital v4 matches scene1/seq0/MARKER1 XYZ and Snappy roundtrip")
        print("[SELFTEST] PASS: V137 TeleportVital differs from zero-target wire only in nine nonzero XYZ value bytes")
        print("[SELFTEST] PASS: V137 target bytes/final u16 remain zero; MARKER direction3 is not mapped")
        print("[SELFTEST] PASS: V137 sends once only after exact V136 confirm; presequence/malformed/replay send nothing")
        print("[SELFTEST] PASS: V137 is an isolated compositional transport probe, not TeleportCheck reply or confirmed travel")
        print("[SELFTEST] PASS: V138 exact 76B count3 marker-ready gate decodes Target clear + Teleport ready + marker TargetPos")
        print("[SELFTEST] PASS: frozen V138 MARKER1 nearest20 snapshot retains exact PC/frame regression hashes")
        print("[SELFTEST] PASS: V140 destination snapshot changes only nine P86 XYZ value bytes to synthetic marker+100X+50Y/Z")
        print("[SELFTEST] PASS: V138 nearest20 preserves P30 HP3857/name Tornado Eagle; other actors retain proven defaults")
        print("[SELFTEST] PASS: V138 sends one immediate population only after V137 transport + exact raw ready; negatives/replay send nothing")
        print("[SELFTEST] PASS: V138 keeps npc_spawn true, marker anchor/current membership, and sends no delayed reapply/message/music/ACK/teleport")
        print("[SELFTEST] PASS: V139 exact 44B marker TargetPos arms only after V138 destination membership; malformed/presequence/replay are inert")
        print("[SELFTEST] PASS: V139 walks only Target(P86/kind2)+Choose1/2(+optional fixed TargetPos); mixed/unknown/Target-only shapes send nothing")
        print("[SELFTEST] PASS: frozen V139 face wire retains exact hash; V140 changes only P86 XYZ/derived-heading value bytes")
        print("[SELFTEST] PASS: V140 safe full20 facing preserves V138 attrs/P30 HP3857+name and gives harness mask03 MovementAttr only to P86")
        print("[SELFTEST] PASS: V140 exact P86 interaction sends harness-facing then unchanged empty conversation once; TargetVital alone/replay send nothing")
        print("[SELFTEST] PASS: V141 f32 marker->P65 1000 rounds below threshold; deterministic 1100 triggers enter91/leave70 after conversation")
        print("[SELFTEST] PASS: V141 restores V95 >=1000-unit set refresh; ordering-only scans advance anchor and send nothing")
        print("[SELFTEST] PASS: V141 retained actors are NPCAttr-only; entrants use authentic full-mask MovementAttr; every set remains 20")
        print("[SELFTEST] PASS: V141 retained P86 keeps the live synthetic harness; leave/re-entry restores authentic P86 placement")
        print("[SELFTEST] PASS: V141 every refresh preserves P30 HP3857/name Tornado Eagle; malformed/nonfinite/under-threshold are inert")
        print("[SELFTEST] PASS: V128 exact 64-byte ActionVital v0 parser accepts singleton or tagged multi-vital first body")
        print("[SELFTEST] PASS: V128 HOTKEY71 WIELD / KEY90 Z / เก็บอาวุธ provenance is exact")
        print("[SELFTEST] PASS: V128 P30 kind2 target arm + WIELD/Z EA7E/qwords 0,0,0x201F is capture-only")
        print("[SELFTEST] PASS: V128 wrong target/envelope/fixed action field/nonfinite/trailing probes remain no-reply")
        print("[SELFTEST] PASS: V122 accepts one exact cmd6 identity0 tuple and preserves the result13 cart ack")
        print("[SELFTEST] PASS: V122 exact cmd8 emits one UpdateAttr v0/full ActorAttr cash10000->0")
        print("[SELFTEST] PASS: V122 cash response has zero TradeItemResult/BackpackAttr/ItemAttr/ItemOperate/close reply")
        print("[SELFTEST] PASS: V122 duplicate/replay/wrong-sequence/nonzero/detail requests stay no-reply")
        print("[SELFTEST] PASS: V116 TradeZoom uses serializer-proven UTF-16 tag 0x48")
        print("[SELFTEST] PASS: V116 ActorAttr carries only proven mask 0x800 and cash qword 10000")
        print("[SELFTEST] PASS: V99 ShowMessage and V100 constructor-default current-scene music are sent exactly once")
        print("[SELFTEST] PASS: V111 Backpack has two Adventure Keys plus the data-proven Camouflage Item-Cask")
        print("[SELFTEST] PASS: V111 exact occupied-slot request merges id3 into id1 and preserves quantity 2 on later moves")
        print("[SELFTEST] PASS: V111 preserves V102's handler-proven CheckSecondPwd result=OK")
        print("[SELFTEST] PASS: Snappy response frame roundtrip")

def game_listener(port: int, capdir: pathlib.Path, ready: threading.Event, stop: threading.Event, token: str):
    live_path = capdir / "GAME_LIVE.txt"
    event_path = capdir / "GAME_EVENTS_LIVE.txt"
    def live(message: str):
        stamp = dt.datetime.now().isoformat(timespec="milliseconds")
        with live_path.open("a", encoding="utf-8") as live_file:
            live_file.write(f"{stamp} {message}\n")
    def event(message: str):
        stamp = dt.datetime.now().isoformat(timespec="milliseconds")
        with event_path.open("a", encoding="utf-8") as event_file:
            event_file.write(f"{stamp} {message}\n")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port))
        s.listen(4)
        s.settimeout(1)
        ready.set()
        print(f"[*] GAME listener ready on {HOST}:{port}")

        while not stop.is_set():
            try:
                c, a = s.accept()
            except socket.timeout:
                continue

            state = GameSessionState(token)
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            lp = capdir / f"GAME_{stamp}_{a[1]}.txt"
            print(f"\n[!!!] GAME CONNECTION from {a}")
            print(f"[+] game log {lp}")
            live(f"GAME_CONNECTED peer={a[0]}:{a[1]} raw={lp.name}")
            event(f"SESSION_START peer={a[0]}:{a[1]} raw={lp.name}")
            c.settimeout(600)
            event_seq=0
            last_event_time=time.monotonic()

            with c, lp.open("w", encoding="utf-8", buffering=1) as f:
                f.reconfigure(line_buffering=True, write_through=True)
                f.write(f"GAME_CONNECTED peer={a[0]}:{a[1]} local_port={port}\n")
                f.flush()
                conn_done = threading.Event()
                send_lock = threading.Lock()

                def heartbeat_worker():
                    seq = 0
                    # Server-data warning in V36 begins around 13 s.  Send a
                    # constructor-exact empty RuntimeRes every 2 s only after the
                    # proven scene Teleport has been scheduled.
                    while not conn_done.wait(2.0):
                        if not state.teleport_sent:
                            continue
                        hb_pc, hb_frame = make_runtime_res_empty_exact()
                        try:
                            with send_lock:
                                c.sendall(hb_frame)
                        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
                            f.write(f"RUNTIME_HEARTBEAT_SEND_FAILED {e!r}\n")
                            break
                        seq += 1
                        f.write(f"RUNTIME_HEARTBEAT_SENT seq={seq} pc_len={len(hb_pc)}\n")
                        f.flush()
                        live(f"HEARTBEAT seq={seq} pc_len={len(hb_pc)}")
                        print(f"[HB>] exact empty RuntimeRes v4 #{seq}")

                hb_thread = threading.Thread(target=heartbeat_worker, daemon=True)
                hb_thread.start()
                try:
                    while True:
                            try:
                                r = recv_frame(c)
                            except socket.timeout:
                                print("[*] game idle timeout")
                                break
                            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
                                print(f"[G!] game socket closed/reset: {e!r}")
                                f.write(f"SOCKET_CLOSED {e!r}\n")
                                break
                            if not r:
                                print("[*] game client closed")
                                break

                            m, frame, comp = r
                            try:
                                pc = snappy_raw_decompress(comp)
                                parsed = parse_outer(pc)
                                ids = structural_ids(parsed)
                            except Exception as e:
                                f.write(f"FRAME magic=0x{m:08X} compressed_len={len(comp)}\n{hexdump(frame)}\n")
                                f.write(f"ERROR {e!r}\n")
                                print("[G!]", e)
                                continue

                            is_empty_noop = (
                                parsed.outer_id == GSCN_LOGIN_PROTOCOL
                                and parsed.vital_count == 0
                                and parsed.nested_id is None
                            )

                            # Keep full packet evidence in the file, but suppress repetitive
                            # empty-GSCN console spam.
                            if is_empty_noop:
                                f.write(
                                    f"NOOP_GSCN frame_len={len(frame)} pc_len={len(pc)} "
                                    f"outer_version={parsed.outer_version} mask=0x{parsed.outer_mask:02X}\n"
                                )
                            else:
                                f.write(f"FRAME magic=0x{m:08X} compressed_len={len(comp)}\n{hexdump(frame)}\n")
                                f.write(
                                    f"DECOMPRESSED {len(pc)}\n{hexdump(pc)}\nSTRUCTURAL_IDS {ids!r} "
                                    f"OUTER version={parsed.outer_version} mask=0x{parsed.outer_mask:02X} "
                                    f"count={parsed.vital_count} nested_version={parsed.nested_version!r}\n"
                                )
                                print(f"[G< #{state.rx_frames + 1}] {len(pc)} bytes IDs={ids}")
                                print(hexdump(pc))
                                live(f"RECV frame={state.rx_frames + 1} pc_len={len(pc)} ids={ids!r}")

                            event_summary=describe_capture_event(parsed,state)
                            if event_summary is not None:
                                now=time.monotonic()
                                event_seq+=1
                                event(
                                    f'EVENT seq={event_seq} frame={state.rx_frames + 1}'
                                    f' delta_ms={(now-last_event_time)*1000.0:.1f} '
                                    f'{event_summary}'
                                )
                                last_event_time=now

                            notify_value = None
                            if parsed.nested_id == NOTIFY_ENTER_CREATE_ACTOR:
                                notify_value = parse_notify_enter_create_actor(parsed)
                                print(f"[STATE] NotifyEnterCreateActor value={notify_value!r} (CLIENT -> SERVER; no reply)")
                                if notify_value == 0:
                                    print("[MILESTONE] CHARACTER SELECT READY / PickActor state.")
                                elif notify_value == 1:
                                    print("[MILESTONE] CHARACTER-CREATE STATE ENTERED.")

                            create_before = state.create_actor_reply_sent
                            if parsed.nested_id == CREATE_ACTOR_VITAL:
                                op, has_actor, actor_wire = parse_create_actor(parsed)
                                f.write(
                                    f"CREATE_ACTOR op={op} has_actor={has_actor} actor_wire_len={len(actor_wire)}\n"
                                )
                                if has_actor:
                                    try:
                                        summary = decode_create_actor_data_ex(actor_wire)
                                        f.write(f"CREATE_ACTOR_DECODE {summary!r}\n")
                                        print(
                                            "[CREATE] "
                                            f"op={op} name={summary['name']!r} "
                                            f"selector={summary['selector']} "
                                            f"identity=({summary['identity_lo']},{summary['identity_hi']}) "
                                            f"wire={summary['wire_len']}"
                                        )
                                    except Exception as e:
                                        f.write(f"CREATE_ACTOR_DECODE_ERROR {e!r}\n")
                                        print("[CREATE!] decode failed:", e)

                            equipment_capture_before = state.equipment_capture_count
                            quest_capture_before = state.quest_operate_capture_count
                            quest_accept_ui_before = state.quest3020_accept_ui_sent
                            quest_accept_success_before = (
                                state.quest3020_accept_success_sent
                            )
                            post_action1_before = state.post_action1_request_count
                            marker1_prompt_before = state.v136_marker1_prompt_sent
                            marker1_confirm_before = (
                                state.v136_marker1_confirm_capture_count
                            )
                            marker1_transport_before = (
                                state.v137_marker1_transport_send_count
                            )
                            marker1_population_before = (
                                state.v138_marker1_population_send_count
                            )
                            marker_targetpos_before = (
                                state.v139_marker_targetpos_capture_count
                            )
                            p86_choose_before = (
                                state.v139_p86_choose_capture_count
                            )
                            population_refresh_before = (
                                state.v141_population_refresh_count
                            )
                            action_capture_before = state.action_vital_capture_count
                            actions = state.dispatch(parsed)
                            if state.equipment_capture_count != equipment_capture_before:
                                value32_mapped = state.equipment_last_value32_mapped
                                item_identity = state.equipment_last_item_identity
                                milestone = (
                                    'V123_EQUIP_FROM_BAG_REQUEST_CAPTURED_NO_REPLY '
                                    f'operation={V123_EQUIP_FROM_BAG_OPERATION} '
                                    f'value32_mapped={value32_mapped} '
                                    f'item_identity={item_identity} '
                                    f'item_identity_hex=0x{item_identity:016X} '
                                    f'capture_count={state.equipment_capture_count}'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if state.quest_operate_capture_count != quest_capture_before:
                                quest_fields=state.quest_operate_last_fields
                                response_status=(
                                    'ACTION1_ACCEPT_SUCCESS_SENT_ONCE'
                                    if (
                                        not quest_accept_success_before and
                                        state.quest3020_accept_success_sent
                                    )
                                    else (
                                        'ACTION6_SENT_ONCE_V135_LIVE_PROVEN_CHAIN'
                                        if (
                                            not quest_accept_ui_before and
                                            state.quest3020_accept_ui_sent
                                        )
                                        else 'NO_REPLY_WRONG_SEQUENCE_OR_REPLAY'
                                    )
                                )
                                milestone=(
                                    'V134_QUEST3020_OPERATE_REQUEST_CAPTURED '
                                    f'fields={quest_fields!r} '
                                    f'op1_count={state.quest3020_op1_capture_count} '
                                    f'op2_count={state.quest3020_op2_capture_count} '
                                    f'capture_count={state.quest_operate_capture_count} '
                                    f'result={response_status}'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if state.post_action1_request_count != post_action1_before:
                                post_fields=state.post_action1_last_request
                                milestone=(
                                    'V129_POST_ACTION1_RUNTIME_REQUEST_OBSERVED '
                                    f'fields={post_fields!r} '
                                    f'observation_count={state.post_action1_request_count} '
                                    'causal_linkage=unassigned'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                not marker1_prompt_before and
                                state.v136_marker1_prompt_sent
                            ):
                                milestone=(
                                    'V136_MARKER1_DOCKING_PROMPT_QUEUED_ONCE '
                                    'trigger=exact_12B_RuntimeReq_v0_mask0 '
                                    'hypothesis=compositional_q3020_var2_1 '
                                    'travel_vehicle_completion_claim=0'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                state.v136_marker1_confirm_capture_count !=
                                marker1_confirm_before
                            ):
                                milestone=(
                                    'V136_MARKER1_POSITIVE_CONFIRM_CAPTURED '
                                    f'value={state.v136_marker1_confirm_last_value!r} '
                                    'teleportcheck_reply=0 '
                                    'hypothesis=compositional_q3020_var2_1 '
                                    'travel_vehicle_completion_claim=0'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                state.v137_marker1_transport_send_count !=
                                marker1_transport_before
                            ):
                                milestone=(
                                    'V137_MARKER1_TELEPORTVITAL_TRANSPORT_PROBE_QUEUED_ONCE '
                                    'scene=1 seq=0 xyz=(-10322,-755,671) '
                                    'target_bytes=0 final_u16=0 direction_mapping=none '
                                    'teleportcheck_reply=0 authentic_quest_response=0 '
                                    'completed_travel_claim=0'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                state.v138_marker1_population_send_count !=
                                marker1_population_before
                            ):
                                milestone=(
                                    'V140_MARKER1_READY_NEAREST20_P86_HARNESS_POPULATION_QUEUED_ONCE '
                                    f'membership={state.population_indices!r} '
                                    f'anchor={state.population_refresh_anchor!r} '
                                    'all_full_movement=1 p86_synthetic_xyz=(-10222,-705,671) p30_hp=3857 '
                                    'p30_name=Tornado_Eagle delayed_reapply=0 '
                                    'message_music_ack_startgame_teleport=0 '
                                    'v139_fresh_target_interaction_pending=1'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                state.v141_population_refresh_count !=
                                population_refresh_before
                            ):
                                milestone=(
                                    'V141_DESTINATION_POPULATION_REFRESH_QUEUED '
                                    f'count={state.v141_population_refresh_count} '
                                    f'membership={state.population_indices!r} '
                                    f'anchor={state.population_refresh_anchor!r} '
                                    'retained_npcattr_only=1 '
                                    'entrant_authentic_movement_maskff=1 '
                                    'p30_hp=3857 p30_name=Tornado_Eagle'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if (
                                state.v139_marker_targetpos_capture_count !=
                                marker_targetpos_before
                            ):
                                milestone=(
                                    'V139_EXACT_MARKER_TARGETPOS_P86_INTERACTION_ARMED_ONCE '
                                    'pc_len=44 xyz=(-10322,-755,671) '
                                    f'membership={state.population_indices!r}'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if state.v139_p86_choose_capture_count != p86_choose_before:
                                milestone=(
                                    'V140_P86_HARNESS_FACE_AND_DEFAULT_CONVERSATION_QUEUED_ONCE '
                                    'actor=0x2057 full20=1 p86_movement_mask=0x03 '
                                    'p86_synthetic_xyz=(-10222,-705,671) '
                                    'p30_hp=3857 p30_name=Tornado_Eagle '
                                    'targetvital_alone_response=0'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            if state.action_vital_capture_count != action_capture_before:
                                action_fields=state.action_vital_last_fields
                                milestone=(
                                    'V128_TARGET_BOUND_WIELD_Z_ACTION_CAPTURED_NO_REPLY '
                                    f'fields={action_fields!r} '
                                    f'capture_count={state.action_vital_capture_count} '
                                    'semantic=wield_stow_toggle_not_attack_or_combat'
                                )
                                f.write(f'MILESTONE {milestone}\n')
                                f.flush()
                                event(f'MILESTONE {milestone}')
                                live(f'MILESTONE {milestone}')
                                print(f'[MILESTONE] {milestone}')
                            # Preserve the absolute-deadline sender for the initial
                            # delayed model-ready reapply.
                            # offsets on one monotonic timeline. Logging,
                            # console hexdumps, and filesystem flushes no longer stretch
                            # every 250 ms movement interval as they did in V82.
                            send_deadline = time.monotonic()
                            for label, out_pc, out_frame, delay in actions:
                                if delay:
                                    send_deadline += delay
                                    remaining = send_deadline - time.monotonic()
                                    if remaining > 0:
                                        time.sleep(remaining)
                                try:
                                    with send_lock:
                                        c.sendall(out_frame)
                                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
                                    print(f"[G!] send failed: {e!r}")
                                    f.write(f"SEND_FAILED {label} {e!r}\n")
                                    break
                                lateness_ms = max(0.0, (time.monotonic() - send_deadline) * 1000.0)
                                live(f"SENT label={label} frame_bytes={len(out_frame)} delay={delay:.2f} late_ms={lateness_ms:.1f}")
                                print(f"[G>] {label} ({len(out_frame)} bytes; late={lateness_ms:.1f} ms)")
                                if label.startswith((
                                    "V98_LOCAL_REFRESH_","V141_LOCAL_REFRESH_"
                                )):
                                    # Live timing plus the deterministic label contains all
                                    # fields needed for this focused cadence test. Avoid the
                                    # console/file hexdump cost inside the 250 ms stream.
                                    f.write(
                                        f"SENT {label} bytes={len(out_frame)} "
                                        f"late_ms={lateness_ms:.1f}\n"
                                    )
                                else:
                                    print(hexdump(out_pc))
                                    f.write(
                                        f"SENT {label} bytes={len(out_frame)}\n"
                                        f"PC {len(out_pc)}\n{hexdump(out_pc)}\n"
                                        f"FRAME\n{hexdump(out_frame)}\n"
                                    )
                                f.flush()

                            if parsed.nested_id == NOTIFY_ENTER_CREATE_ACTOR:
                                f.write(f"NO_REPLY NotifyEnterCreateActor value={notify_value!r}\n")

                            if parsed.nested_id == CREATE_ACTOR_VITAL:
                                if not create_before and state.create_actor_reply_sent:
                                    print("[MILESTONE] CreateActor success/update echo sent once.")
                                    print("[NEXT] Do not click repeatedly. Observe the next screen/request.")
                                    f.write("MILESTONE CREATE_ACTOR_SUCCESS_ECHO_SENT\n")
                                elif state.create_actor_reply_sent:
                                    f.write("MILESTONE CREATE_ACTOR_DUPLICATE_SUPPRESSED\n")
                                else:
                                    print("[!!!] CreateActor captured but not safely decodable; NO RESPONSE.")
                                    f.write("MILESTONE CREATE_ACTOR_CAPTURED_NO_SAFE_RESPONSE\n")

                            if parsed.nested_id == START_GAME_REQ:
                                selector = parse_start_game_req(parsed)
                                print(f"[!!!] MILESTONE: StartGameReq selector={selector!r} captured.")
                                f.write(f"MILESTONE START_GAME_REQ_CAPTURED selector={selector!r} ACTORATTR_REPLY={state.start_game_reply_sent}\n")

                            f.write(
                                "STATE "
                                f"rx={state.rx_frames} login_ack={state.login_ack_sent} "
                                f"select_sent={state.select_actor_sent} notify_count={state.notify_count} "
                                f"last_notify={state.last_notify_value!r} create_seen={state.create_actor_seen} "
                                f"create_reply={state.create_actor_reply_sent} start_seen={state.start_game_seen} start_reply={state.start_game_reply_sent} world_info={state.world_info_sent} teleport={state.teleport_sent} runtime_ack={state.runtime_ack_sent} npc_sweep={state.npc_appear_sweep_sent} "
                                f"equipment_capture_count={state.equipment_capture_count} "
                                f"equipment_value32_mapped={state.equipment_last_value32_mapped!r} "
                                f"equipment_item_identity={state.equipment_last_item_identity!r} "
                                f"quest_conversation={state.quest3020_conversation_sent} "
                                f"quest_accept_ui={state.quest3020_accept_ui_sent} "
                                f"quest_accept_success={state.quest3020_accept_success_sent} "
                                f"quest_op1_count={state.quest3020_op1_capture_count} "
                                f"quest_op2_count={state.quest3020_op2_capture_count} "
                                f"quest_capture_count={state.quest_operate_capture_count} "
                                f"quest_last_fields={state.quest_operate_last_fields!r} "
                                f"post_action1_request_count={state.post_action1_request_count} "
                                f"post_action1_last_request={state.post_action1_last_request!r} "
                                f"v136_docking_pending={state.v136_docking_composition_pending} "
                                f"v136_marker1_prompt={state.v136_marker1_prompt_sent} "
                                f"v136_marker1_confirm_count={state.v136_marker1_confirm_capture_count} "
                                f"v136_marker1_confirm_value={state.v136_marker1_confirm_last_value!r} "
                                f"v137_marker1_transport_sent={state.v137_marker1_transport_sent} "
                                f"v137_marker1_transport_count={state.v137_marker1_transport_send_count} "
                                f"v138_marker1_ready_count={state.v138_marker1_ready_capture_count} "
                                f"v138_marker1_population_sent={state.v138_marker1_population_sent} "
                                f"v138_marker1_population_count={state.v138_marker1_population_send_count} "
                                f"v139_marker_targetpos_count={state.v139_marker_targetpos_capture_count} "
                                f"v139_p86_armed={state.v139_p86_interaction_armed} "
                                f"v139_p86_choose_count={state.v139_p86_choose_capture_count} "
                                f"v139_p86_face_sent={state.v139_p86_face_sent} "
                                f"v139_p86_conversation_sent={state.v139_p86_conversation_sent} "
                                f"v141_population_refresh_count={state.v141_population_refresh_count} "
                                f"population_membership={state.population_indices!r} "
                                f"population_anchor={state.population_refresh_anchor!r} "
                                f"p30_action_armed={state.p30_action_target_armed} "
                                f"action_capture_count={state.action_vital_capture_count} "
                                f"action_last_fields={state.action_vital_last_fields!r}\n"
                            )
                            f.flush()
                            live(
                                f"STATE rx={state.rx_frames} start={state.start_game_reply_sent} "
                                f"teleport={state.teleport_sent} runtime_ack={state.runtime_ack_sent} "
                                f"npc_sweep={state.npc_appear_sweep_sent}"
                            )

                finally:
                    conn_done.set()
                    hb_thread.join(timeout=0.5)
            print(f"[+] closed game log {lp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-port", type=int, default=10189)
    ap.add_argument("--status", type=int, default=1)
    ap.add_argument("--value32", type=int, default=1)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--token", default="localtest")
    ap.add_argument("--self-test-only", action="store_true")
    args = ap.parse_args()

    run_self_test(verbose=True)
    if args.self_test_only:
        return

    capdir = pathlib.Path("capture_v141")
    capdir.mkdir(exist_ok=True)
    login_pc, login_frame = make_login_res()
    sel_pc, sel_frame = make_select_res(args.status, args.game_port, args.value32, args.host, args.token)

    print("\n[*] PF v141 - V140 interaction plus destination population continuity")
    print(f"[*] LOGIN {HOST}:{LOGIN_PORT}; GAME {HOST}:{args.game_port}")
    print("[*] Structural nested dispatch; empty 12-byte GSCN heartbeat is a no-op.")
    print("[*] LoginVerifyVital -> ACK + SelectActorVital v10 with one persisted actor; no character creation required.")
    print("[*] NotifyEnterCreateActor 0/1 -> no reply.")
    print("[*] CreateActorVital v8 op=1 -> LoginProtocol v0 / CreateActorVital v8 op=1 echo ONCE.")
    print("[*] Bounded visual harness is P0-100X-50Y: P0 lies at relative +100X,+50Y (26.565 degrees).")
    print("[*] The offset is operational only, not an authentic placement/ground claim.")
    print("[*] Stable zero-target Teleport and exact isolated P0/P30/P91 population are preserved.")
    print("[*] Incremental schedule 0+3 sends population only; no timed TeleportCheck or automatic quest UI.")
    print("[*] Exact current-P0 ChooseNPC sends safe full facing plus one q3020 NPCConversation descriptor.")
    print("[*] Exact op1 after that conversation sends action6 once; V135 live-proved the complete quest chain.")
    print("[*] Exact op2 after action6 sends the live-proven action1 Accept_Run result once.")
    print("[*] Action1 only arms V136; the next exact 12-byte RuntimeReq v0/mask0 sends V131 MARKER1 prompt once.")
    print("[*] Exact MARKER1 positive confirm is journaled once; no TeleportCheck reply is sent.")
    print("[*] This is a compositional q3020 Var2=1 hypothesis, not proof of original-server linkage.")
    print("[*] No QuestAttr, reward, progression, persistence, travel, vehicle, completion, inventory, or combat state is added.")
    print("[*] After exact confirm, V137 sends one RuntimeRes TeleportVital scene1/seq0 XYZ(-10322,-755,671).")
    print("[*] Target bytes/final u16 remain zero; MARKER direction3 is not mapped into unknown fields.")
    print("[*] This transport is not a TeleportCheck reply, authentic original-server quest response, or completed-travel claim.")
    print("[*] Exact 76-byte post-transport count3 ready batch queues one immediate marker-nearest20 population.")
    print("[*] Membership: P86/P80/P0/P1/P65/P22/P16/P85/P5/P92/P84/P50/P89/P144/P145/P39/P87/P82/P30/P70.")
    print("[*] Destination members retain V139 attrs; only P86 MovementAttr XYZ uses synthetic marker+100X+50Y at marker Z.")
    print("[*] P86 harness XYZ is (-10222,-705,671), operational only—not an authentic placement or decoded-ground claim.")
    print("[*] No delayed reapply, message, music, ACK, StartGame, or extra teleport is added.")
    print("[*] Exact singleton marker TargetPos arms one current-P86 interaction after V138 population.")
    print("[*] Accepted shapes are Target(P86/kind2)+Choose(P86) x1/x2, with optional fixed final TargetPos; unknown tails are rejected.")
    print("[*] The exact interaction keeps P86 at the same harness XYZ, sends mask03 MovementAttr only on P86, then unchanged empty conversation.")
    print("[*] P30 remains HP3857/name Tornado Eagle; TargetVital alone, wrong sequence, malformed shapes, and replay send nothing.")
    print("[*] After that conversation only, >=1000 units from the refresh anchor recomputes the authentic nearest-20 set.")
    print("[*] Set-unchanged scans only advance the anchor; retained actors are NPCAttr-only and entrants use authentic full-mask MovementAttr.")
    print("[*] Retained P86 keeps the live synthetic harness; if it leaves and later re-enters, authentic placement is restored.")
    print("[*] Every refresh keeps P30 HP3857/name Tornado Eagle; malformed/nonfinite/under-threshold TargetPos sends nothing.")
    print("[*] Runtime camera probe only: tap Q/E and Numpad 7/9 Rotate Left/Right repeatedly; observe visual camera/actor effect and journaled network traffic.")
    print("[*] The camera probe adds no protocol field or server response and must be reported as visual-only, actor rotation, or network-producing.")
    print("[*] P30 current/max HP is exact level-27 STANDARD_MOB 3857/3857; P0/P91 remain 100/100.")
    print("[*] P30 BasicAttr name is exact MOBS_TIP s_NAME 'Tornado Eagle'; P91 remains byte-identical.")
    print("[*] TargetVital kind 2 gets no response; the client fills target name/HP from local BasicAttr.")
    print("[*] Backpack base-range mask is 1: 40 slots - 4 items = 36 free; Store UI cap is 18.")
    print("[*] Identity4 is data-backed Create Character Blade template2200002 in bag slot3; +0x39 remains 0xFF and no nested detail.")
    print("[*] Backpack regression state remains the four-item 4/40 bag; V130's proposed equipped-state display was disproved and is not claimed.")
    print("[*] Exact ItemOperate v0 operation5/identity4/value32 8 or16 is journaled and receives no reply.")
    print("[*] V131 TeleportCheck wire is reused only after the exact V136 sequence/heartbeat gate.")
    print("[*] Exact P30 kind2 TargetVital arms one 64-byte ActionVital v0 capture; the action consumes that arm.")
    print("[*] HOTKEY 71 WIELD / KEY 90 Z / 'เก็บอาวุธ' maps to producer EA7E.")
    print("[*] EA7E is journaled only as a target-bound wield/stow toggle; no attack/combat meaning or response is added.")
    print("[*] One exact TradeCmd cmd6/dword0/identity0/Sword Soul qty1 receives Store_ByItemOK.")
    print("[*] First sequenced cmd8/dword0/no-detail sends UpdateAttr ActorAttr cash10000->0 only.")
    print("[*] No TradeItemResult, BackpackAttr, ItemAttr, identity, slot, or detail is sent for cmd8.")
    print("[*] Captured cmd12/dword0/no-detail close attempts are journaled separately and receive no reply.")

    ready = threading.Event()
    stop = threading.Event()
    threading.Thread(
        target=game_listener,
        args=(args.game_port, capdir, ready, stop, args.token),
        daemon=True,
    ).start()
    if not ready.wait(3):
        raise RuntimeError("GAME listener failed to become ready")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, LOGIN_PORT))
        s.listen(4)
        print(f"[*] LOGIN listener ready on {HOST}:{LOGIN_PORT}")

        while True:
            c, addr = s.accept()
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            lp = capdir / f"LOGIN_{stamp}_{addr[1]}.txt"
            print(f"\n[+] LOGIN connection {addr}")
            c.settimeout(600)
            sent_login = False
            sent_select = False

            with c, lp.open("w", encoding="utf-8", buffering=1) as f:
                f.reconfigure(line_buffering=True, write_through=True)
                f.write(f"LOGIN_CONNECTED peer={addr[0]}:{addr[1]}\n")
                f.flush()
                while True:
                    try:
                        r = recv_frame(c)
                    except socket.timeout:
                        print("[*] login idle timeout")
                        break
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
                        print(f"[L!] login socket closed/reset: {e!r}")
                        f.write(f"SOCKET_CLOSED {e!r}\n")
                        break
                    if not r:
                        print("[*] login client closed")
                        break

                    m, frame, comp = r
                    f.write(f"FRAME magic=0x{m:08X} compressed_len={len(comp)}\n{hexdump(frame)}\n")
                    try:
                        pc = snappy_raw_decompress(comp)
                    except Exception as e:
                        print("[L!]", e)
                        f.write(f"ERROR {e!r}\n")
                        continue

                    try:
                        parsed = parse_outer(pc)
                        ids = structural_ids(parsed)
                    except Exception as e:
                        print("[L!] structural parse:", e)
                        f.write(f"ERROR structural_parse {e!r}\n")
                        continue

                    print(f"[L<] {len(pc)} bytes IDs={ids}")
                    f.write(
                        f"DECOMPRESSED {len(pc)}\n{hexdump(pc)}\nSTRUCTURAL_IDS {ids!r} "
                        f"OUTER version={parsed.outer_version} mask=0x{parsed.outer_mask:02X} "
                        f"count={parsed.vital_count} nested_version={parsed.nested_version!r}\n"
                    )

                    if parsed.nested_id == LOGIN_REQ and not sent_login:
                        c.sendall(login_frame)
                        sent_login = True
                        print("[L>] LoginVitalRes + one local server/channel")
                        f.write(f"SENT_LOGIN_RES {len(login_frame)}\n{hexdump(login_frame)}\n")

                    if parsed.nested_id == SELECT_SERVER_REQ and not sent_select:
                        chosen = parse_select_req(parsed)
                        print(f"[L<] SELECT_SERVER_REQ world/channel={chosen}")
                        c.sendall(sel_frame)
                        sent_select = True
                        print(f"[L>] SelectServerRes -> {args.host}:{args.game_port}")
                        f.write(f"SELECT_IDS {chosen!r}\nSENT_SELECT_RES {len(sel_frame)}\n{hexdump(sel_frame)}\n")

            print(f"[+] closed login log {lp}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] stopped")
