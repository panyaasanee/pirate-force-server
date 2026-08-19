# Pirate Force V93 result and V94 local population streaming

Date: 2026-08-14

## V93 result

The user reported that V93 looked the same and correctly noted that adding two
already-proven walkers did not answer a new project question. Do not continue
the version-by-version walker-count expansion. Preserve the locomotion results
as solved components, not as the main investigation.

## V94 new objective

V94 removes every synthetic lane mover. Its visible population consists only
of authentic single-outfit `bg0001.npc` placements.

At initial entry it selects the nearest 20 placements to the player's captured
TargetPosVital and sends their proven full position state. After the player has
travelled at least 1000 units from the last population scan anchor, it computes
the nearest 20 again.

If membership changes, one authoritative snapshot is sent:

- every retained member carries NPCAttr only, using the V92-passed static
  representation and avoiding repeated movement tasks;
- every entering member carries NPCAttr plus its authentic placement XYZ in
  MovementAttr;
- every leaving member is omitted, using the V91-proven removal semantics.

If the nearest membership is unchanged, no packet is sent. This avoids
timer-driven population churn. No route, animation, interaction, unknown field,
or deletion packet is guessed.

This is the first runtime test of actual local population streaming rather than
another locomotion demonstration.

## Verification

- Python compile: PASS
- project self-test: PASS
- stable bootstrap regression: PASS
- initial nearest population count 20: PASS
- initial MovementAttr count 20: PASS
- refresh authoritative population count 20: PASS
- retained actors omit MovementAttr: PASS
- entering actors alone carry MovementAttr: PASS
- exiting/entering sets differ across synthetic 5000-unit travel: PASS
- no ActionVital: PASS
- Snappy response roundtrip: PASS

Package: `packages/PF_Login_Game_Test_v94.zip` (exactly three files)

SHA-256: `1D0C735E0B7EE80E1D679F558A45BD725A57589D7B8E6EB89D53D55286F618BE`
