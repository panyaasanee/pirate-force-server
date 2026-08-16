# Pirate Force ServerProject

Persistent Codex workspace for the Pirate Force local server reverse-engineering
and NPC movement investigation.

## Start here

The active runtime-proven evidence checkpoint is V140. V141 is preserved as an
offline-tested legacy characterization baseline. New modular foundation code lives
under `src/pirateforce_foundation`; it does not create a gameplay V142.

Run deterministic verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\verify_foundation.ps1
```

Run the persistent lifecycle adapter (after offline gates pass):

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_foundation_visible.ps1 `
  -Database .\state\pirateforce.sqlite3
```

Every actual server run displays a visible console and mirrors its summary output
to deterministic UTF-8 files in the run capture root. Raw packet logs remain
file-only under `capture_v141`. Offline `--self-test-only` checks are the sole
console exception.

Current state and evidence ceilings are in `STATUS.md` and
`docs/EXPERIMENT_LEDGER.md`.

## Legacy history

V140 is the accepted runtime checkpoint. V141 is an offline characterization
baseline with an unaudited raw capture. Historical protocol findings and their
evidence ceilings remain in `AGENTS.md`, `handoff.txt`, and `reports/`; old deploy
commands are intentionally not repeated here.

## Layout

- `current` — active server and launcher
- `history` — V74-V82 implementations retained for comparison
- `tools` — bounded window recorder, video frame extractor, motion analyzer, and deployment helper
- `evidence` — selected logs, videos, and contact sheets
- `packages` — verified distributable ZIP
- `references` — read-only synchronized reverse-engineering source material

Runtime captures remain in:

```text
C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_v<version>
```

See `AGENTS.md` for the current findings, safety constraints, and test workflow.
