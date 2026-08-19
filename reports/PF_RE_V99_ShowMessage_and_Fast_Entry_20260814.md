# Pirate Force V99 system message and state-driven fast entry

Date: 2026-08-14

## Outcome

V99 adds the first non-NPC runtime feature after the movement/conversation
work: a server-originated system message. On the first Port Royal runtime
request the client displays `Pirate Force local server online` in its authentic
system/chat panel. The existing V94 population, V97 conversation, and V98 safe
conversation-facing behavior remain unchanged.

The passing runtime is preserved at:

`backups/v99_runtime_showmessage_fastentry_20260814_023154/`

## Static evidence

`ShowMessageVital` has protocol ID `0x36D2`. Client disassembly proves:

- constructor `0x5E4930`, vtable `0xF300EC`;
- exactly one wide-string member at object offset `+0x14`;
- serializer `0x5E6D00` reads/writes only that member;
- handler `0x5EFA70` forwards non-empty text to the client notification UI.

No unknown fields, flags, or guessed IDs are present.

## Runtime framing finding

The first run deliberately exposed a structural omission in the older
single-vital envelope helper. A `RunTimeProtocolRes v4` with the valid nested
ShowMessage but without the outer derived-class terminator produced client
`GSCN_RunTimeProtocolRes ErrorData=28317`.

V99 was corrected to use the already-proven collection builder. Its wire ends
with the required derived mask `0B 00`. The corrected packet grew from 100 to
102 framed bytes and was accepted: the message appeared and the client
continued sending normal runtime requests. This is a reusable protocol rule
for subsequent runtime systems.

## Regression result

After the message appeared, a single movement tap produced TargetPos and the
unchanged nearest-20 local population appeared normally. No runtime protocol
error occurred in the corrected run.

## Faster entry workflow

New read-only tooling removes fixed UI sleeps:

- `tools/analyze_login_timeline.py` now isolates the latest connection when a
  capture directory contains multiple launches;
- `tools/wait_for_pf_stage.py` polls decoded protocol milestones at 100 ms;
- `tools/PF_FAST_ENTRY_AUTOMATION.md` documents immediate Enter actions for
  server selection, confirmation, and character selection.

The server's `NotifyEnterCreateActor` is the exact character-ready signal;
`RUNTIME_RES_ACK_FIRST_REQ` is the exact Port Royal runtime-ready signal.
Client loading time remains unavoidable, but blind multi-second waits and
channel-row clicking are no longer part of the workflow.

## Verification

- Python compile: PASS
- project self-test: PASS
- exact ShowMessage serializer: PASS
- required RuntimeRes derived mask: PASS
- Snappy frame roundtrip: PASS
- live system message display: PASS
- continued runtime request stream after message: PASS
- V94 population regression: PASS
- V97 conversation/V98 facing self-test regressions: PASS

Package: `packages/PF_Login_Game_Test_v99.zip` (exactly three files)

SHA-256: `25A0EFF5FC6262538CD55D2724BF50819178B906AB3A71D8816146FCF1CCA481`
