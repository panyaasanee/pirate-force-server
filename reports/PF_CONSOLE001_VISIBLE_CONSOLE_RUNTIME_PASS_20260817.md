# CONSOLE-001 — visible Foundation console runtime pass

Date: 2026-08-17
Scope: one controlled local server start/stop cycle on the platform console
requirement only. No gameplay, protocol, or inventory claim is added.

## Result

Grade B pass for the narrow platform claim: every actual Foundation server
invocation attaches or allocates a real Windows console, mirrors its summary
streams to deterministic UTF-8 files, and still stops cleanly through one
requested `CTRL_C_EVENT`.

Controlled run `console_m1_20260817_031427` (2026-08-17 03:14 ICT):

- The launcher `tools\run_foundation_visible.ps1` reported visible shim
  PID 11656; listeners came up owned by server PID 4840 within 1 second.
- The shim window title carried mode plus database name exactly:
  `Pirate Force Foundation Server | foundation | console_m1_20260817_031427.sqlite3`.
- One bounded `CTRL_C_EVENT` was attached to that console. The helper returned
  `attach_console=true`, `ctrl_c_sent=true`, `ctrl_c_error=null`, signalled at
  `2026-08-16T20:14:43.5510740Z`.
- The server exited at `2026-08-16T20:14:43.9189602Z` with **exit code 0**; the
  shim exited at `2026-08-16T20:14:43.9328771Z` with **exit code 0**.
- Mirrored stdout is 12021 bytes containing exactly one
  `[FOUNDATION] visible console` marker and exactly one `[FOUNDATION] stopped`
  marker. Mirrored stderr is 0 bytes.
- Zero listeners and zero `python`/`py` processes remained after exit.
- The disposable database copy was byte-identical before and after; the source
  database `EA1C4459F9E88322EE4689B2C2A13C0465CF57BE35F2B47FEB1ED6D74EDD8F3B`
  was not opened for write.

## Implementation and acceptance

The implementation landed on the `codex/server-visible-console` worktree as
commit `0e922b6` (14 files, 367+/5-) and was cherry-picked into `main` as
`6f730ac74b6f96129115a081c18d8b4ff4566c86`.

Acceptance on **main** (2026-08-17 04:32-04:34 ICT, Windows `py -3`):

| Gate | Command | Result |
|---|---|---|
| Ledger | `py -3 tools\verify_hypothesis_ledger.py` | `HYPOTHESIS_LEDGER PASS entries=16`, exit 0 |
| T0 hygiene | `git diff --check` | exit 0 |
| T1/T2 | `py -3 -m unittest discover -s tests` | 234 tests, `OK`, exit 0 |
| T3 full | `tools\verify_foundation.ps1` | `[FOUNDATION] deterministic verification PASS`, exit 0 |

`--self-test-only` remains exempt from the console requirement because it opens
no listener; that exemption is exercised inside the T3 verifier itself.

## Nonclaims

This proves one requested-stop path through this exact helper and console host
on this machine. It is **not** crash, power-loss, every-signal-source,
concurrent-client, remote-client, or authenticated multi-account proof. It adds
no protocol hypothesis and moves no accepted evidence ceiling. The
`HYPOTHESIS_LEDGER.json` canonical content hash is unchanged
(`6AB4BA02D59C4796CBE9925D710A72C2BFDA32F7AB685BE14B70586B38F05EF0`).

## Corrective recorded during acceptance

Reaching a green T3 on `main` required one hygiene correction that is worth
recording because it is easy to reintroduce:

1. **Duplicate emitter annotations.** Uncommitted M3 work-in-progress had added a
   second `# PF-HYPOTHESIS-LEDGER: HYP-PF-008 active` line to each of
   `inventory.py`, `lifecycle.py`, `repository.py`, `session.py`, and `store.py`.
   `verify_hypothesis_ledger.verify_source_annotations` binds annotations
   bidirectionally and permits exactly one annotation per `(path, hypothesis id)`
   pair, so the gate failed closed with
   `duplicate emitter annotation: ('src/pirateforce_foundation/inventory.py', 'HYP-PF-008')`.
   The five work-in-progress duplicates were removed and the original committed
   annotation in each file was kept. **No ledger field was edited and no accepted
   ceiling moved.**
2. **`.gitignore` line endings.** A cherry-pick had rewritten `.gitignore` with
   CRLF endings while its committed form is LF, so `git diff --check` reported
   trailing whitespace on all 142 lines and failed the T0 hygiene gate. The file
   was restored to its committed byte content; its content hash never differed.

Both corrections are hygiene-only. Neither changes an executable contract, a
release input, a verifier, or the canonical ledger.
