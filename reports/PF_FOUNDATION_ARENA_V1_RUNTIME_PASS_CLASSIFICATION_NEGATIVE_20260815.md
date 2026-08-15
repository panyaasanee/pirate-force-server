# Foundation + Test Arena V1 runtime result

Date: 2026-08-15

## Outcome

An assisted GameClient run passed the bounded Foundation lifecycle and Arena V1
object-spawn/target milestones. It did **not** prove hostile-monster behavior.

## Runtime facts

- A fresh Arena database returned an empty character list.
- The client created `Arena01`; the server committed it before replying and SQLite
  contained one live selector-0 character with that name.
- The character screen showed `Arena01`, level 1, Port Royal. Select/StartGame used
  the same persisted character identity.
- StartGame, scene-1 Teleport and the first Runtime ready request completed on the
  same GAME connection.
- The first exact singleton TargetPos caused one P30 initial population packet and
  one identical model-ready reapply three seconds later. No inherited P0/P91
  population was sent.
- The client visibly rendered the `Tornado Eagle` model near the player. The target
  panel showed name `Tornado Eagle`, level 1 and HP 3857. Clicking it emitted the
  expected TargetVital for identity `0x201F` and kind 2. No reply was required.
- More than 60 post-target runtime states continued without a bad marker, exception,
  disconnect or stderr output.
- After a normal client exit and relaunch, the same running server listed `Arena01`
  again and StartGame restored scene 1 at the persisted Port Royal coordinates.

## Classification result

The stable client presentation used a green overhead name, person-style target icon
and talk cursor. This is a negative for hostile-monster classification even though
the correct monster model rendered. The operator noticed a possible brief red name
and sword cursor during the first shutdown; because it was not captured and was not
reproduced in normal steady state, it remains only a teardown/hover hypothesis.

## Evidence ceiling

Proven: persisted Create/List/Select/StartGame continuity, same-server client
reconnect, scene-1 position reload, exact one-object P30 spawn/reapply, visible model,
name/HP panel and click-to-TargetVital transport.

Not proven: server-process restart/crash recovery, world-visible player name,
hostile relation, attack cursor in stable state, FightAttr, combat, AI, damage,
death, loot, authentic P30 placement or original-server policy.
