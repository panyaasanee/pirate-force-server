# Test Arena V2 faction-only runtime result

Date: 2026-08-15

## Outcome

The exact P30 BasicAttr faction-6 diagnostic passed packet transport and target
selection, but did not produce stable hostile-monster presentation. The candidate
is retired under its predeclared stop rule.

## Runtime facts

- Arena V2 reused the persisted `Arena01` character and scene-1 position from the
  Arena V1 database; no new character was created.
- Full Flow completed through StartGame, Teleport and the first runtime request.
- The first accepted TargetPos sent a 217-byte Arena V2 P30 frame immediately and
  an identical frame exactly three seconds later.
- Independent regeneration from the captured player anchor reproduced both frames
  byte-for-byte. The only V1-to-V2 semantic delta is BasicAttr mask bit `0x0400`
  plus serializer-ordered u32 faction value 6.
- The wire retained P30 identity `0x201F`, template 31, name `Tornado Eagle`, HP
  3857/3857, scene 1, sequence 0 and the established test-only relative placement.
- One click produced the exact P30 TargetVital version 0, kind 2, with embedded
  ChooseNPC for the same identity. It was observation-only and required no reply.
- The capture continued for more than 60 post-target heartbeats. Stderr was empty
  and the audited bad-marker set was zero.

## Classification result

The stable client view remained a green overhead name, person-style target icon and
talk cursor after the initial packet and after the reapply.

A separate controlled shutdown run then recorded the game window at an actual rate
of about nine frames per second. The exit window was opened once and its confirmation
button was pressed once. The first frame after the dialog disappeared shows the
`Tornado Eagle` label in pink/red, a red outline around the actor, and a non-talk
pointer over its body. This reproduces the operator's earlier shutdown observation.
The following frames retain the same shutdown image until the client closes.

Frame 142 at 14.657 seconds still contains the confirmation dialog; frame 143 at
14.712 seconds is the first post-dialog frame, with a measured transition delta of
54 ms (the displayed timestamps are rounded). The selected frame-143 PNG SHA-256 is
`670B45D3C70D6B7AAD361EF1BE5F0BDF0165F0DFD6016612438AE9F983DD0DAD`.

This is evidence of a teardown-specific UI/relation transition, not a stable hostile
state during gameplay. It must not be used to claim attack availability or combat.

The result is therefore a runtime pass for the exact faction-only transport and a
negative for hostile classification. Target faction alone is insufficient in the
current player state. The next justified step is to recover the local player's
actual BasicAttr faction producer/value before another diagnostic.

Subsequent static tracing proves that the current StartGame ActorAttr omits mask
`0x0400`; the client BasicAttr constructor therefore leaves the local player at
faction 0. Faction row 6 does not list 0 as an enemy, which explains the observed
negative. No original-server StartGame capture currently proves the authentic
player faction, so faction 1 must not be sent as a guess.

## Evidence ceiling

Proven: persisted-character reuse, exact P30 faction-6 initial/reapply transport,
continued healthy runtime, and exact click-to-TargetVital transport.

Not proven: hostile relation, stable sword cursor or red label, local-player
faction, BasicAttr `+0x6C` semantics, FightAttr, AI, attack, combat, damage, death,
loot, authentic P30 placement or original-server policy.
