# Pirate Force ServerProject

Persistent Codex workspace for the Pirate Force local server reverse-engineering
and NPC movement investigation.

## Start here

The active runtime-proven evidence checkpoint is V140. V141 is preserved as an
offline-tested legacy characterization baseline. New modular foundation code lives
under `src/pirateforce_foundation`; it does not create a gameplay V142.

Run deterministic verification:

```powershell
py -3 -m pytest tests -q
py -3 tools\verify_hypothesis_ledger.py
py -3 tools\verify_functional_coverage.py
```

Those three, plus the per-lane verifiers a change touches, are what decides
green here. Run them on Windows: this project verifies on two machines and only
the Windows one has the client image several verifiers read, and its console is
code page 874, which has caught tool output that was green in a UTF-8 sandbox
and fatal there.

> **`tools\verify_foundation.ps1` is NOT the gate, and it cannot pass.** It was
> the gate when this line was first written and it has been advertised as the
> gate ever since. Its deterministic-release step pins a set of 79 archive
> members inline, while `tools\build_foundation_release.py` emits more (**105**
> at round 93's re-derivation, **122** as of 2026-08-23; all 79 pinned members
> still present each time), so the step's set comparison fails on every run.
> Both counts were re-derived rather than repeated (build the archive, read
> `namelist()`, diff against the inline set) — re-derive again before citing a
> current number. Re-pinning it to the current count would make it green again, and that is
> deliberately not done here: a member census that is widened whenever it
> disagrees with the tree has stopped being a census, and whether this script
> should be re-pinned or retired outright is a decision rather than a repair.

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
