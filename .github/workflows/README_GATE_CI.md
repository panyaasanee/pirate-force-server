# README_GATE_CI - the Windows gate on GitHub Actions

**What this is.** `gate-windows.yml` runs the part of the Pirate Force gate that
a GitHub `windows-latest` runner is actually able to run, on Windows, under
code page 874, with `py -3` pinned to the same interpreter series as the bridge.
It exists because the project is about to be gated from a cloud (Linux) chief,
and this project has already been bitten once by a failure that only Windows
could see: in round 142 `tools/pf_vital_thunk_census_static.py` printed U+1F534,
cp874 has no mapping for it, `print()` raised `UnicodeEncodeError`, and the tool
died having reported nothing. The Linux sandbox was green on the same bytes.
A Linux-only gate would let that class of bug through forever, and "green"
would quietly stop meaning what it means on the bridge.

**What this is NOT.** It is **not the whole gate**, and a green tick here is
**not** a gate pass. Nine named checks cannot run on a GitHub runner at all
because the evidence they read is not in this repository and cannot be put
there. They are skipped **by name, with a reason, in the log and in the job
summary**, never silently. The authoritative gate remains the per-round bridge
job (the most recent is `pf_bridge/done/147_round91_latchonly.ps1`).

**Correction you need before reading anything else.** `tools/verify_foundation.ps1`
is *not* the gate any more, although `README.md:15` and `AGENTS.md:117` still
say it is. No bridge job since roughly job 022 has invoked it, and it cannot
pass today: its pinned release-member list holds 79 entries while
`tools/build_foundation_release.py` now emits 105, so its
`assert set(z.namelist()) == expected` fails on any current checkout. This
workflow reproduces the *determinism* half of that check (build twice, compare
sha256) and deliberately does not reproduce the stale member list.

---

## BLOCKER - this workflow cannot run until `.gitignore` is changed

`.gitignore` line 1 is `/*`: the repository is an allowlist, and everything at
the root is excluded unless a later line re-includes it. `.github/` is not
re-included, so **git cannot see these two files at all**:

```
$ git check-ignore -v --no-index -- .github/workflows/gate-windows.yml
.gitignore:1:/*    .github/workflows/gate-windows.yml
```

GitHub only runs workflows that are committed. Until a negation is added these
files sit on Panya's disk and nowhere else - which is the exact failure the
`.gitignore` comments already describe as the round-87 lesson: *"the file exists
on the author's machine" is not "the file is in the repository."*

**This change was deliberately NOT made by the agent that wrote these files:
editing `.gitignore` is inside the `LOCK_GIT.txt` scope and requires the seam
test.** The chief decides. The minimal edit is two lines, in the directory
allowlist block, immediately after `!/scenarios/**` (currently line 101) and
before `!/tools/` (currently line 102):

```gitignore
!/.github/
!/.github/**
```

Any position after line 1 works - `.gitignore:1` is the only pattern that
currently matches `.github/`, so nothing later re-excludes it.

---

## The full check table

Source of truth for the check names and their pass criteria: the release note at
the head of `pf_bridge/LOCK_GIT.txt` and the job that wrote it,
`pf_bridge/done/147_round91_latchonly.ps1` (lines 106-192, 292-303).

Note two things about that release note, because they are easy to misremember:
the **"11 paths"** on line 4 is the number of files in the commit, not a number
of checks; and **`replayx=2` is the passing value** - that check is a negative
and exit 0 would be the failure.

| check | command | pass criterion | on `windows-latest`? |
|---|---|---|---|
| `latchver` | `py -3 tools\pf_runtimeres_death_encoder_static.py` | exit 0, 138 guards | **NO** - needs `..\GameClient\GameClient.local.bin` |
| `replay3` | `py -3 tools\pf_runtimeres_death_headless_replay.py` | exit 0, 64 guards | yes |
| `replay2` | `... --profile dying_latch_only` | exit 0, 68 guards | yes |
| `replayx` | `... --profile nonsense` | **exit 2** (negative) | yes |
| `dmenc` | `py -3 tools\verify_damage_model_encoder.py` | exit 0, 322 guards | yes |
| `dmreplay` | `py -3 tools\pf_damage_model_headless_replay.py` | exit 0, 136 guards | yes |
| `hpenc` | `py -3 tools\verify_hp_death_encoder.py` | exit 0 | yes |
| `damage` | `py -3 tools\pf_damage_hit_result_static.py` | exit 0 | **NO** - needs the client image |
| `runtimeres` | `py -3 tools\pf_runtimeres_actor_entry_static.py` | exit 0 | **NO** - needs the client image |
| `hpstatic` | `py -3 tools\pf_hp_death_respawn_static.py` | exit 0 | **NO** - needs the client image |
| `stats` | `py -3 tools\pf_stats_progression_static.py` | exit 0 | **NO** - client image + `capstone` |
| `census` | `py -3 tools\pf_vital_thunk_census_static.py` | exit 0 | **NO** - needs the client image |
| `mpaudit` | `py -3 tools\pf_multiplayer_readiness_audit.py` | exit 0 | yes, **only with `fetch-depth: 0`** |
| `corpus` | `py -3 tools\pf_capture_corpus.py` | exit 0 | **NO** - needs untracked `backups/**/capture_v131` |
| `hlhold` | `py -3 tools\pf_hp_death002_headless_replay.py --profile dying_hold` | exit 0 | yes |
| `pytest` | `py -3 -m pytest tests -q` | exit 0 | **partial** - client-free subset only, 39 modules excluded by name |
| `seam` | `py -3 -m pytest tests\test_foundation_legacy_seam.py -q` | exit 0 | yes |
| `ledger` | `py -3 tools\verify_hypothesis_ledger.py` | exit 0, `entries=31` | yes |
| `coverage` | `py -3 tools\verify_functional_coverage.py` | exit 0, `OPEN DOMAINS 8` | **NO, and not for a runner reason** - see below |
| `canonGuard` | sha256 of `state\pirateforce.sqlite3` vs `pf_bridge\CANON_SHA.txt` | unchanged | **NO** - both files live outside the repository |
| `v141Guard` | `git status --short -- current/pf_login_game_server_v141.py` | empty | runs, but **vacuous** in CI |
| `diffcheck` | `git diff --check` | exit 0 | runs, but **vacuous** in CI |
| `ignoreGuard` | `git check-ignore -q -- <new paths>` | non-zero (not ignored) | yes |

Everything in the "on `windows-latest`?" column was **measured**, not guessed:
the tracked file set was extracted with `git ls-files | tar -T -`, unpacked with
no sibling `GameClient/` directory, and each tool was run against it. The
"NO - needs the client image" rows each exited **1** with
`FileNotFoundError: 'GameClient/GameClient.local.bin'`. They **fail loudly, they
do not skip** - which is the right behaviour, and is why the workflow refuses to
run them rather than letting them turn the job red for a reason that says
nothing about the code.

### Why the client image cannot simply be committed

`..\GameClient\GameClient.local.bin` is 14,759,424 bytes, lives **outside** the
repository (a sibling of the repo root), and `.bin` is on the forbidden-tracked-
extension list that the gate itself enforces. Six checks read it.

If you ever want those six back, the tools resolve `ROOT.parent / "GameClient" /
"GameClient.local.bin"`, so on a runner that is `${{ github.workspace }}\..\GameClient\`.
Restore it there from a cache or a self-hosted runner and drop the corresponding
skip. The tools pin the image by size and hash, so a wrong image fails loudly.

### Why `coverage` is red for a repository reason, not a runner reason

This is the most important finding in this document.

`tools/verify_functional_coverage.py` **exits 2 on a fresh clone** and exits 0 on
Panya's machine. The reason is not Windows and not the runner:

```
verify_functional_coverage.py: error: domains[0].capabilities[0].evidence_refs[2]
does not exist: reports/PF_RE_V102_Inventory_Unlock_20260814.md
```

**33 of the 112 `evidence_refs` in `docs/FUNCTIONAL_COVERAGE.json` cite reports
that exist only on Panya's disk.** They are on disk, they are matched by
`.gitignore:8` (`/reports/*`), and they were never re-included, so they are not
in the repository. `docs/HYPOTHESIS_LEDGER.json` is clean by the same test - 0 of
99 - because the check that was added after round 87 covers the **ledger** only,
not the **coverage matrix**.

So `coverage=0` in the LOCK_GIT release note is a **local** fact. It is not
reproducible from git by anyone, on any operating system. A cloud chief will hit
this on the first run.

The workflow therefore does two things instead of pretending:

1. A blocking step counts the unreachable `evidence_refs` and compares the count
   against `COVERAGE_EVIDENCE_DEBT_PIN` (currently `33`) at the top of the
   workflow. **If the debt grows, the job goes red** - a new claim was just
   backed by evidence nobody who clones this repository can read. If the debt
   shrinks, the job also goes red, telling you to lower the pin in the same
   commit. This is the same pinned-count idiom the seam test already uses for
   `MANIFEST_DEBT_RUNTIME_PASS`.
2. `verify_functional_coverage.py` itself is run for its log value but is **not
   blocking** while the pin is non-zero. Set the pin to `0` (after un-ignoring
   the 33 reports) and it becomes blocking automatically.

---

## How cp874 is enforced, in three layers

1. **Job-level environment.** `PYTHONIOENCODING=cp874:strict`,
   `PYTHONLEGACYWINDOWSSTDIO=1`, `PYTHONUTF8=0`, plus `chcp 874`. The `:strict`
   is the load-bearing half - without it an unmappable character degrades into
   `?` and the round-142 bug is invisible again. Verified locally:
   `sys.stdout.encoding sys.stdout.errors` reports exactly `cp874 strict`, and
   under it `print('\U0001F534')` exits non-zero while `print('ascii')` exits 0.
2. **A self-check that proves the tripwire is armed, on every single run.** The
   `SELF-CHECK` step asserts (a) a native exit code of 23 actually propagates -
   the same self-check `verify_foundation.ps1` opens with - and (b) that
   `py -3 -c "print('\U0001F534')"` **fails**. If the runner image ever defeats
   the encoding configuration, the job goes red at that step instead of
   producing a run of false negatives.
3. **A static tripwire with pinned counts.** Every tracked `.py` under `tools/`,
   `src/` and `current/` (84 files) is scanned for characters cp874 cannot
   encode. Three files carry pre-existing occurrences, all in comments,
   docstrings or a JSON artifact payload, none of them reachable from `print()`:

   | file | count |
   |---|---|
   | `tools/pf_move_cadence001_headless_replay.py` | 6 |
   | `tools/pf_vital_name_thunk_static.py` | 1 |
   | `tools/pf_vital_thunk_census_static.py` | 3 |

   `src/` and `current/` are currently 100% clean. The counts are pinned, so one
   **new** unmappable character anywhere in that scope turns the job red and
   names the file, line and codepoint.

   `tests/` is **out of scope on purpose**: several modules carry non-ASCII test
   *data* deliberately (fullwidth latin in `test_player_name.py`, U+00E9 in
   `test_character_identity_binding.py`). `docs/` and `reports/` are out of
   scope because a markdown file is never printed to a console - 85 of 448
   tracked text files would trip a repo-wide scan, all of them harmlessly.

**A latent cp874 landmine found while writing this, which the current gate does
not cover:** `tools/pf_move_cadence001_headless_replay.py` calls `print()` with
U+00D7 and U+00B1 on lines 96, 109, 152 and 154. Neither character is
cp874-encodable. That tool would die on the bridge console the moment anyone
ran it - it is simply not in the gate's tool list today. Chief's call; the file
was not touched.

---

## Fail-closed: how PowerShell is prevented from swallowing a failure

- Every native call's `$LASTEXITCODE` is captured into a `$results` table and
  compared against an **expected** value. Nothing relies on control flow
  reaching a later line - the same rule the bridge jobs use for `git commit`
  ("success is HEAD moving, not this line being reached").
- The verdict is one aggregate `$allGreen` at the end, and the step ends with an
  explicit `exit 1`. GitHub's `pwsh` shell only propagates the **last** command's
  exit code, so the explicit `exit` is required.
- `$ErrorActionPreference = 'Continue'` inside the gate step is **deliberate and
  is not a hole**. With `Stop` plus `2>&1`, any native command that writes a
  single byte to stderr becomes a terminating `NativeCommandError` - git does
  this for CRLF notices - and a warning would masquerade as a gate failure. The
  bridge job documents this exact trap at lines 218-219. Exit codes are checked
  by hand instead. `$PSNativeCommandUseErrorActionPreference = $false` is set
  explicitly so the behaviour does not depend on the runner's PowerShell version.
- The setup steps that *should* stop on any error use `$ErrorActionPreference =
  'Stop'` plus explicit `throw` on non-zero.

## Two runner requirements that are not obvious

- **`fetch-depth: 0`.** `tools/pf_multiplayer_readiness_audit.py` runs
  `git ls-tree 5cc0eda tests/` to re-derive a historical suite size. Under the
  default shallow checkout that command exits 128 and the whole audit exits 1.
  Measured: with history present and *without* the client image, the audit exits
  **0**.
- **The `py -3` shim.** The runner image ships its own `py.exe`, which would
  resolve to the image's Python rather than the one `actions/setup-python`
  pinned. A `py.cmd` shim is written into `RUNNER_TEMP` and prepended to `PATH`
  so that every `py -3` in the workflow is the pinned 3.14 interpreter. The
  environment-assertion step fails the job if it is not a `3.14.*`.

---

## Proving it has been red - "a check that has never been seen red is not a check"

Run these on a throwaway branch. Each recipe targets a different mechanism, and
each has a one-command revert.

### 1. The cp874 static tripwire

`src/` is currently 100% clean, so any unmappable character there trips it.

```powershell
git checkout -b ci/prove-red-cp874
Add-Content -LiteralPath 'src\pirateforce_foundation\__init__.py' -Value '# RED PROOF U+1F534'
# now replace the text U+1F534 with the actual character, e.g.:
py -3 -c "open('src/pirateforce_foundation/__init__.py','a',encoding='utf-8').write('# \U0001F534\n')"
git commit -am 'prove the cp874 tripwire fires'
git push -u origin ci/prove-red-cp874
```

Expected: the step **cp874 static tripwire** fails with
`RED src/pirateforce_foundation/__init__.py got=1 pinned=0` and
`line N: codepoint 0x1f534`.

*This one has already been rehearsed offline against the real tracked file set
and produced exactly that output; the rehearsal is described under "What was and
was not proven" below.*

Revert:

```powershell
git checkout master
git branch -D ci/prove-red-cp874
git push origin --delete ci/prove-red-cp874
```

### 2. The runtime cp874 crash - the round-142 bug, verbatim

This proves the *execution* path, not just the source scan.

```powershell
git checkout -b ci/prove-red-runtime-cp874
py -3 -c "p='tools/verify_hp_death_encoder.py'; s=open(p,encoding='utf-8').read(); open(p,'w',encoding='utf-8').write('print(\"\U0001F534\")\n'+s)"
git commit -am 'prove a print() that cp874 cannot encode kills the gate'
git push -u origin ci/prove-red-runtime-cp874
```

Expected: **two** red channels from one cause, exactly as round 142 saw - the
static tripwire fires, and `hpenc` in THE GATE exits non-zero with
`UnicodeEncodeError`. Revert as in recipe 1.

### 3. The negative check (`replayx`)

`replayx` passes on exit **2**. Make the validator accept an unknown profile and
the check must go red even though nothing "fails":

```powershell
git checkout -b ci/prove-red-negative
# in tools/pf_runtimeres_death_headless_replay.py, change the unknown-profile
# branch to exit 0 instead of 2
git commit -am 'prove the negative check is a real check'
git push -u origin ci/prove-red-negative
```

Expected: `replayx exit=0 expect=2 RED`. Revert as in recipe 1.

### 4. The coverage-debt pin

```powershell
git checkout -b ci/prove-red-covdebt
# add one evidence_ref to docs/FUNCTIONAL_COVERAGE.json pointing at a file that
# is not tracked, e.g. "reports/NOT_A_REAL_REPORT.md"
git commit -am 'prove the evidence-debt pin fires'
git push -u origin ci/prove-red-covdebt
```

Expected: `NOT in a fresh clone : 34 (pinned at 33)` and the step exits 1.

*Rehearsed offline: running the extracted script with `pin=32` against the real
repository exits 1, with `pin=33` exits 0.*

### 5. The self-checks (these run on every job, unprompted)

You do not need a branch. Recipes 1-4 all depend on the encoding being armed;
the `SELF-CHECK` step re-proves that on every run by asserting that
`print('\U0001F534')` fails and that exit code 23 propagates. If either
assertion stops holding, the job goes red immediately.

---

## What was and was not proven

**Proven, by running it:**

- The tracked file set was extracted (`git ls-files | tar`), unpacked with no
  sibling `GameClient/`, and each gate tool run against it. Exit codes in the
  table above are measurements.
- `ledger`, `replay3`, `replay2`, `replayx`(=2), `dmenc`, `dmreplay`, `hpenc`,
  `hlhold`, `seam`, `compileall`, `py_compile` of the v141 snapshot and
  `--self-test-only` all pass on a clone-only tree.
- `mpaudit` exits 1 without git history and 0 with it, without the client image.
- `coverage` exits 2 on a clone-only tree; 33 of 112 `evidence_refs` are
  untracked; the ledger's 99 refs are all tracked.
- `verify_foundation.ps1`'s release-member list is 79 vs 105 actually built.
- Both Python scripts embedded in the workflow were extracted from the YAML and
  run against the real repository: the cp874 tripwire passes at the pinned
  counts, and going red was rehearsed by injecting U+1F534 into
  `src/pirateforce_foundation/__init__.py` in a throwaway copy, which produced
  the exact `RED ... got=1 pinned=0 / line 6: codepoint 0x1f534` output. The
  coverage-debt script exits 0 at pin 33 and 1 at pin 32.
- The YAML parses, contains zero non-ASCII bytes, has no trailing whitespace and
  no tabs, so `git diff --check` has nothing to flag.

**NOT proven - do not read the above as more than it says:**

- **The workflow has never been executed.** No GitHub Actions run exists,
  because `.github/` is gitignored and the files have never been committed or
  pushed. Every claim about `windows-latest` behaviour is inference from the
  file contents plus Linux measurements.
- **Nothing was run on Windows.** All measurements are Linux/CPython 3.10.12 in
  the session sandbox. The bridge is CPython 3.14.7. Version-specific behaviour
  differences were not tested.
- **The `py.cmd` shim was never executed.** Its argument re-quoting loop is
  untested, including the `@'...'@ | py -3 -` stdin form used elsewhere in the
  project.
- **`chcp 874` on a GitHub runner was not tested.** Whether the runner image
  permits that code page, and whether `PYTHONLEGACYWINDOWSSTDIO` behaves as
  expected there, is unverified.
- **No pytest run was ever completed - not the full suite, not the subset.** The
  session sandbox runs under `bwrap --unshare-net`, so it has no network
  namespace at all, and every module that binds or connects a loopback socket
  blocks forever. The run stalls first at `tests/test_connection_lifecycle.py`;
  excluding the six obvious socket modules moves the stall to
  `tests/test_delete_actor_hypothesis.py` (roughly test 123 of 685 in that
  ordering) and it stalls again. This is a sandbox artifact, **not** a finding
  about the repository - the same suite passes on the bridge, where `pytest=0`.
  What it means here is that **whether the client-free pytest subset is green on
  a real runner, and how long it takes, is entirely unmeasured**. Collection is
  clean (1411 tests collect with zero import errors on a clone-only tree), which
  is the only pytest fact established. `timeout-minutes: 90` is a backstop, not
  evidence.
- **The 39-module pytest exclusion list is generated by a grep for
  `GameClient|capture_v141`.** It was checked by eye, not proven minimal or
  complete. A module that needs the client image without naming it would still
  be included and would go red.
- **The guard counts in the table** (138, 64, 68, 322, 136) are copied from the
  bridge job's comments, not re-derived.
- **No bridge file was modified.** `LOCK_*.txt`, `GAME_TEST_QUEUE.md`,
  `CHIEF_CONTINUATION.md`, `pf_bridge/inbox/`, `.gitignore`, `state/`,
  `current/pf_login_game_server_v141.py` were all read-only.

---

## Impact on the existing gate

Adding `.github/` **cannot turn the current bridge gate red**, for the blunt
reason that git cannot see it (`.gitignore:1` `/*`). If and when the chief
un-ignores it, it still does not disturb anything, and this was checked against
each file-list enforcer rather than assumed:

| enforcer | what it enumerates | affected by `.github/`? |
|---|---|---|
| `tools/build_foundation_release.py` lines 6-50 | an explicit list plus `src/**/*.py`, `migrations/*.sql`, `scenarios/*.json` | **no** - `.github/` is not globbed |
| `tools/verify_foundation.ps1` line 64 | forbidden tracked prefixes/extensions | **no** - `.github/` is not a listed prefix, `.yml`/`.md` are not listed extensions |
| `tools/verify_foundation.ps1` lines 86-166 | pinned release member list | **no** - unaffected (but already stale by 26 members, see the top of this file) |
| `tests/test_foundation_legacy_seam.py` lines 32-35 | `src/pirateforce_foundation`, `reports/`, `docs/FUNCTIONAL_COVERAGE.json` | **no** - no repo-wide enumeration exists in it |
| `tools/verify_hypothesis_ledger.py` line 582 | `src/**/*.py` + `scenarios/*.json` feeding `CANONICAL_CONTENT_SHA256` (line 190) | **no** |
| `tools/verify_functional_coverage.py` | `evidence_refs` only | **no** |

The one thing a future bridge job **must** adjust is its own hardcoded expected
path count - job 147 line 93 expects `11` dirty paths and lines 230/234 abort
unless exactly `11` paths are staged. Those numbers are per-job and the chief
sets them when writing the job.

Optional, not required: `.gitattributes` has no rule for `*.yml`. Adding
`*.yml text eol=lf` would match the treatment of `*.py`/`*.md`. GitHub Actions
accepts either line ending, so this is tidiness, not correctness.
