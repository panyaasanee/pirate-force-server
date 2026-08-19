# Pirate Force RE checkpoint — V134 q3020 conversation handshake operational negative

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V134 derives from frozen V131 and adds a bounded, stateful quest handshake for
the exact Port Royal P0/template-1/q3020 relationship.  Static construction and
self-tests remain valid: an exact current-P0 `ChooseNPC` sends the 39-byte
one-entry `NPCConversation`; the exact 43-byte q3020 operation-1 request then
sends action 6 once; the already proven action-6/operation-2 segment sends
action 1 once.  Wrong tuples, envelopes, ordering, trailing data, and replays
receive no reply and cannot advance the state.

## Exact runtime result

The flushed capture contains two sessions.  Both entered the world, accepted
the stable bootstrap, acknowledged runtime, and sent the exact isolated
P0/P30/P91 population at 0 seconds plus its 3-second reapply.

Session 1 (`GAME_20260815_040118_199861_64590.txt`):

- connected at `04:01:18.200`;
- StartGame response at `04:02:02.419`;
- runtime acknowledgement at `04:02:25.813`;
- population initial/reapply at `04:02:57.038` / `04:03:00.038`;
- 193 runtime heartbeats, final heartbeat at `04:08:28.315`;
- eight `TargetPosVital` requests, but zero `TargetVital`, `ChooseNPC`, or
  `QuestOperateVital`.

Session 2 (`GAME_20260815_041348_421522_49804.txt`):

- connected at `04:13:48.422`;
- StartGame response at `04:14:12.671`;
- runtime acknowledgement at `04:14:39.164`;
- population initial/reapply at `04:15:15.047` / `04:15:18.048`;
- 58 runtime heartbeats, final heartbeat at `04:16:09.146`;
- nine `TargetPosVital` requests, but zero `TargetVital`, `ChooseNPC`, or
  `QuestOperateVital`.

The second session's nine positions changed continuously from approximately
`(-8919.192, -2811.749, 186)` to `(-4529.206, -3245.649, 194)` over 11.97
seconds.  This is the network signature of the observed ground auto-run, not an
NPC selection.

The first operational click missed P0 and landed on the ground.  A subsequent
automation experiment called `sky.drag({... mouse_button: 'right'})` over empty
sky.  The Computer Use backend accepted the extra field but ignored it, issued
a left drag, and again changed the character coordinates through repeated
`TargetPosVital` requests.  This proves a limitation of the current automation
gesture carrier; it does not prove that Pirate Force itself lacks right-drag
camera control.

Across all eight flushed capture files there is no ErrorData, version mismatch,
`28317`, traceback, fatal, or disconnect protocol marker.  Server stderr is
empty.  Session 1's raw log ends with the ordinary Windows socket-reset record
caused by client-side closure; it is not a protocol failure.

## Boundary and next test

V134's quest handshake was not exercised.  No `ChooseNPC` means the server
never emitted the q3020 conversation, so operation 1, action 6, operation 2,
and action 1 were all unreachable in this run.  The result is an operational
negative only, not a rejection of the V134 packet or state-machine hypothesis.

Retest V134 by clicking P0 directly without a drag gesture.  Do not use the
current `sky.drag` right-button override until the Computer Use backend exposes
a verified right-button carrier.  Keep V131 as the latest runtime-passing
baseline; do not promote V134 from this capture.

## Artifact verification

Frozen implementation artifacts were not changed:

- `pf_login_game_server_v134.py`, 293,574 bytes  
  `E0E5A2599CDF3976799A384998545A6A0BF58EFF13BD823B0EB5A6546E52C667`
- `run_v134_port_royal_p0_q3020_conversation_handshake.bat`, 469 bytes  
  `693B53E3B2A2A1583F23EE6852E660A39738346B5685422B8CF317BE28FBB8B9`
- `PF_Login_Game_Test_v134.zip`, 4,370,209 bytes  
  `75D389465E0E8F1E61402394C514C05194ADCCEBF43DB556B667DC0E022CD78A`

The package still contains exactly `GameClient.local.bin`, the V134 server,
and the V134 launcher.  Its integrity and embedded hashes passed the independent
pre-runtime audit.

Verified operational-negative backup:

`backups/v134_q3020_conversation_operational_negative_20260815_042000/`

Its manifest covers all eight flushed capture files plus the frozen source,
launcher, package, and this report.  V131 remains the passing baseline.
