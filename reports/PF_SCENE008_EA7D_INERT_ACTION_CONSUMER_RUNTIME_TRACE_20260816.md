# SCENE-008 — EA7D inert action-consumer runtime trace

Date: 2026-08-16

## Claim

The exact SCENE-007 ActionVital acknowledgement is consumed by the client and
enters the selected actor's action queue, but this build constructs it as a
generic action with no implementation object and with terminal bit `0x08`
already set. Its first observed update reaches the common return with that bit
unchanged.

This is an instrumented runtime claim (grade C) bounded to the controlled Port
Royal P60 `0xEA7D`/`0x203D` response. It explains the inert lifecycle observed
after SCENE-007; it is not a combat, animation or damage pass.

## Evidence

The final clean session produced one 113-byte RuntimeReq containing ActionVital
`0xEA7D` for target `0x203D`, followed by one 97-byte framed RuntimeRes
acknowledgement. The server event occurred at `01:09:25.190`; the consumer
handler observed the corresponding performer `0x0000000010010001`, action
`0xEA7D` and target `0x203D` at `01:09:25.246`.

The checksum/code-guarded observe-only probe then captured one exact ordered
chain:

1. inbound handler;
2. constructor return with action `0xEA7D`, implementation `0`, flags `8`;
3. handler attach call;
4. actor attach to the actor `+0x20` lane;
5. one queue insertion;
6. first update entry with implementation `0`, flags `8`;
7. common update return with flags still `8`.

The same object `0x1BB70B80` is preserved through construction, attachment,
queueing and update. Actor `0x27E6CF58` maps to expected/actual queue
`0x27E6CF78`. All seven relocated hook addresses match the guarded image at
runtime base `0x00CC0000`.

The final probe process exited while the client was still alive; probe stdout
and stderr are empty. Direct UI observation confirmed that the client remained
responsive, and the server log continued through multiple heartbeats after the
consumer chain without a server-side error or disconnect before controlled
close. The database main file, WAL and SHM returned `PASS_UNCHANGED`.

Earlier `004142`, `004933` and `010148` runs are retained only as superseded
operational diagnostics: respectively a false abort on unowned traffic, a valid
chain without bounded-exit evidence, and a valid chain followed by an explicit
cleanup timeout. They are not acceptance inputs. Artifact paths, sizes and
SHA-256 values for the final clean run are frozen in the adjacent manifest.

## Evidence ceiling

Proven: the exact SCENE-007 acknowledgement reaches the ActionVital consumer,
constructs the same `0xEA7D`/`0x203D` action object with null implementation and
terminal bit `8`, enters the selected actor's `+0x20` queue once, and reaches the
first common update return with terminal bit `8` unchanged.

Not proven: an attack animation or implementation execution, hit/miss, damage or
HP mutation, range/cooldown authority, FightAttr, AI, death, loot, respawn,
skills, authentic player faction, or an original-server response policy. Do not
compose HP, UpdateAttr or FightAttr packets from this result.
