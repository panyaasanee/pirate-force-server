# Pirate Force state-driven fast entry

Use Computer Use for all Windows input. Do not automate the game with
PowerShell/UIAutomation or raw input scripts.

The server's line-buffered `GAME_LIVE.txt` is the authoritative stage signal:

1. After launching the client, observe its window and click the bottom `เข้า`
   (Enter) button directly as soon as the server-selection screen is visible.
   The client already has the local server and Channel 1 selected. Never click
   either list row first unless a new observation explicitly shows no selection.
2. Refresh immediately. If the confirmation dialog is visible, press `Return`.
3. Poll the live log at 100-200 ms intervals until `NotifyEnterCreateActor`
   appears. This is the protocol-backed character-selection-ready signal.
4. Refresh the game window immediately. V117 proved that the persisted actor
   can be visible without being selected: `Return` alone then shows the Thai
   "select a character" warning. Click the actor model once and immediately
   click the Enter Game button; do not wait between those two ready-state
   actions. Use `Return` only when the actor is already visibly highlighted.
5. Poll until `SENT label=V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE`, then until
   `SENT label=RUNTIME_RES_ACK_FIRST_REQ`. The second signal proves Port Royal
   has loaded and sent its first runtime request.
6. Only then start the feature-specific action/capture. Do not insert fixed
   multi-second waits unless a captured client state proves one is required.

V117 measured two avoidable delays that this sequence must not repeat:

- `character-ready` to `StartGameReq`: 55.592 seconds, caused by relying on
  `Return` while the actor was not selected;
- `runtime-ready` to the first movement-triggered population packet: 41.859
  seconds, caused by delaying the short movement key.

For Test Arena V1 or V2, press the short movement key immediately after
`runtime-ready`; `ARENA_V1_P30_INITIAL` or `ARENA_V2_P30_INITIAL` should follow
without a human-timed pause. V2 is a faction-only diagnostic: if the stable
view remains green/person/talk, record the negative and stop without adding
FightAttr, AI, or local-player faction guesses. The no-scenario Full Flow
continues to use the legacy isolated P0/P30/P91 population.

## Fast Backpack PIN path (runtime-proven in V110)

The game accepts the complete PIN through one `type_text` action even though
the custom PIN field does not draw bullets or digits. Do not send four separate
digit actions and do not capture a screenshot after each digit:

1. Click the Backpack icon once and refresh once to prove the PIN dialog has
   focus.
2. Send the literal text `1234` in one Computer Use `type_text` action.
3. Refresh once, then press `Return` once to submit.
4. The opened `2 / 40` Backpack and captured `CheckSecondPwdVital` prove the
   complete string was accepted. An apparently blank custom field is not a
   failure signal.

This reduces the PIN path from five input actions (four digits plus submit) to
two input actions (one complete text entry plus submit). Do not click the
randomized on-screen keyboard unless direct text entry is disproven by a new
client build.

## Screenshot budget

- Observe the server list once, then click `เข้า` directly. Do not spend input
  actions re-selecting the local server or Channel 1.
- Refresh once for the deterministic confirmation modal, then `Return`.
- After confirming the server, satisfy the post-action refresh with a
  lightweight text-only window state. While the client is loading, use the
  live protocol milestones instead of waiting on an expensive screenshot.
- Observe the character screen once after `character-ready`, then `Return`.
- After entering the character, use another lightweight post-action refresh,
  wait for `runtime-ready`, then observe Port Royal once.
- After `type_text("1234")`, use a lightweight post-action refresh; do not spend
  a screenshot merely trying to see masked digits. Submit with `Return`, wait
  for `CheckSecondPwdVital`, and take one final Backpack screenshot.

Screenshots are state proof, not timers. Avoid commentary, report work, static
analysis, or unrelated shell inspection between a ready-state observation and
its input action.

`tools/analyze_login_timeline.py <capture_vNN>` summarizes the same milestones
and quantifies avoidable UI delay after a run.

For live polling, use `tools/wait_for_pf_stage.py`. For example:

```powershell
python .\tools\wait_for_pf_stage.py `
  "C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_arena_v2_YYYYMMDD_HHMMSS" `
  character-ready --poll-ms 100
```

The path may be one live log, a `capture_vNN` directory, or the outer capture
directory printed by the Arena launcher. The waiter finds nested `GAME_LIVE`
and `GAME_EVENTS_LIVE` files itself. Supported milestones include `connected`,
`character-list`, `character-ready`, `create-committed`, `start-game`,
`teleport`, `runtime-ready`, `population`, and `arena-target`. The tool is
read-only and exits as soon as the corresponding decoded protocol evidence exists.
