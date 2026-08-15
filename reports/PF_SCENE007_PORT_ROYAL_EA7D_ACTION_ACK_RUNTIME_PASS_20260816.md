# SCENE-007 — Port Royal EA7D minimum ActionVital response runtime pass

Date: 2026-08-16

## Claim

The strict opt-in Port Royal scenario returns exactly one minimum base
ActionVital response after the selected hostile P60 produces target-bound action
`0xEA7D`. The response is accepted without disconnect or visible HP change and
the result repeats in a fresh client/server session.

The runtime harness also meets the operator requirement: the persisted player
starts at exact V74 scene-1 position `(0,0,931)`, while P60 uses the P144
beer-tray visual coordinates `(1788.796875,-1121.6756591796875,930.423583984375)`.
After the first bounded forward movement spawns P60, both actors are visible in
the default camera frame and no camera rotation is required.

## Evidence

Both sessions followed the same strict order: selected persisted player, remote
P60 spawned, exact TargetVital kind 1 for identity `0x203D`, then one structurally
parsed `0xEA7D` ActionVital request. Each request was the audited two-vital shape
`[ActionVital, TargetPos]` and each caused one 97-byte framed response containing
an 86-byte GSCN RuntimeRes v4 body with one ActionVital v0.

The response omits the request's trailing TargetPos. Within the echoed 64-byte
ActionVital body it preserves target `0x203D`, action `0xEA7D`, heading, XYZ,
scene 1 and the remaining exact fields; only qword performer changes from zero
to persisted selected identity `0x0000000010010001`.
The server sent no BasicAttr, FightAttr, UpdateAttr, HP or damage companion.

Direct client observation after each response showed a responsive client, player
HP `100/100`, P60 HP `3857/3857`, and the selected hostile target UI. The first
post-input frame showed approach movement; subsequent frames did not establish a
clear attack animation. Animation is therefore explicitly not promoted.
Both stderr files are empty. Both detached source-database guards returned
`PASS_UNCHANGED` for the main database, WAL and SHM. Artifact paths, sizes and
SHA-256 values are frozen in the adjacent manifest.

## Evidence ceiling

Proven: exact one-shot minimum ActionVital response transport for the controlled
hostile P60 `0xEA7D` request, performer-only field transformation within the
echoed 64-byte ActionVital body, fresh-session
repeat, client health, visible unchanged HP, unchanged persistence files, and the
no-camera-rotation Port Royal test placement.

Not proven: visible attack animation, original-server response policy, hit/miss,
range or cooldown authority, damage formula or HP mutation, FightAttr, AI, death,
loot, respawn, skills, or authentic player-faction assignment. The P144 heading
and P60 placement are a deterministic test harness, not authentic monster policy.
