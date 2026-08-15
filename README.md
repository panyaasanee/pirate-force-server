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
$env:PYTHONPATH = ".\src"
py -3 -m pirateforce_foundation.app --db .\state\pirateforce.sqlite3
```

Current state and evidence ceilings are in `STATUS.md` and
`docs/EXPERIMENT_LEDGER.md`.

## Legacy history

The active verified runtime checkpoint is V115 under `current\`. It preserves
V111's stateful Adventure Key stack merge, isolates exact data-backed P30
Tornado Eagle plus P91 Local people, positions the local actor through the
proven StartGameRes MovementAttr path, and opens the client-data-backed Sword
Soul shop through `TradeZoomVital 0x2A7A v2`. V115 corrects V114's one-byte
string-tag error (`0x44` ANSI to serializer-proven `0x48` UTF-16). Read
`reports\PF_RE_V111_to_V115_Inventory_Monster_Shop_20260814.md`.

To deploy the current version into the installed game directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\deploy_current.ps1 -Version 115
```

Then run this file from the GameClient directory:

```text
C:\Users\Panya\Desktop\Pirate Force\GameClient\run_v115_port_royal_monster_shop_milestone.bat
```

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
