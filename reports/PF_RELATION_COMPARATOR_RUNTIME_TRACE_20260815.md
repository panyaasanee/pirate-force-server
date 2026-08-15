# Relation comparator runtime trace

Date: 2026-08-15

## Outcome

The exact-client, capture-only REL-001 probe attached successfully after two
guard corrections and recorded StartGame plus the relation comparator without
writing memory, packets or UI. The authoritative line-buffered JSONL was closed
and hash-stable after client exit, then all 3,087 lines passed the checked-in
event validator.

## Guard diagnostics

Two earlier one-line files are preserved but superseded:

1. `relation_probe.jsonl` records the initialization failure caused by removed
   Frida 17 `Memory.read*` APIs. The agent now uses read-only NativePointer methods.
2. `relation_probe_retry.jsonl` records a runtime code-guard mismatch because the
   comparator signature contained one ASLR-relocated absolute operand. The disk
   guard remains full-byte exact; runtime now accepts only the declared four-byte
   relocation when it equals the disk operand plus the observed module slide.

Neither failed attempt installed the complete hook set or contributes relation
evidence.

## Authoritative trace

- `probe_ready` occurred once at runtime module base `0x660000`.
- The StartGame observation hook occurred once.
- Sequences 1 through 1023 each contain exactly one comparator entry followed by
  `first` BasicAttr `+0x68` raw u32 value 6 and `second` raw u32 value 0.
- Both BasicAttr and field pointers remained stable across all 1,023 comparisons.
- There are no missing, reordered, extra or invalid events in those sequences and
  no `probe_error` in the authoritative file.
- After one exit confirmation, sequences 1024 through 1039 contain comparator
  entry only. None reached either instrumented `+0x68` read before client exit.
- The paired server trace captures exact TargetVital v0/kind 2 for actor `0x201F`,
  with embedded ChooseNPC for the same identity, and continues through heartbeat
  78 before logging normal game-client and login-client close. Server stderr and authoritative
  probe stdout/stderr are empty. The independent audit found zero `Traceback`,
  error, exception, bad-magic, Snappy-failure or unexpected-disconnect markers;
  the server's connection and StartGame milestone banners are not failure markers.

The Arena contained one emulator-created P30 whose exact V2 wire supplied value 6;
the current StartGame actor omits `0x0400` and retains constructor/default value 0.
That controlled differential correlates `first=6` with P30 and `second=0` with the
current local/default actor for this run. It does not establish the authentic
player faction or original-server relation policy.

The post-confirmation calls bypassed the `+0x68` comparison at an earlier gate.
Therefore the teardown-only pink/red label, outline and pointer transition is not
an observed faction mutation and is not evidence of stable hostility or attack.

## Frozen manifest

Authoritative capture directory:
`GameClient/capture_arena_v2_20260815_131741`

The nine authoritative live artifacts are enumerated by relative path, exact byte
count and SHA-256 in
`reports/PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.manifest` (983 bytes,
SHA-256 `A21737888E09AFF149B27927B1872D155FE77726A81FAE8AC43E55AACFBD1C4C`).
PID metadata is intentionally omitted. The two superseded JSONL diagnostics below
are preserved separately and are not members of the authoritative manifest.

| File | Bytes / lines | SHA-256 | Role |
|---|---:|---|---|
| `relation_probe_live.jsonl` | 662,860 / 3,087 | `6A93C2200E7B47B7196EA5EC478E266C0B88BC9751C4656C48ACA2DADC14FF04` | authoritative |
| `relation_probe.jsonl` | 112 / 1 | `975FD9D4C4B142FF483765EF6C15784D06CCDC27867D04E254718DD4C115F02A` | superseded Frida-17 diagnostic |
| `relation_probe_retry.jsonl` | 133 / 1 | `D05C206405833D815D2B575004AE24F880FAC68184F08A8CA85DEBD0A70C385C` | superseded ASLR diagnostic |

Probe source SHA-256:
`1C2E66B1256CB44174E8C289459E0E0B3A0B23377072F635971632E43FDD841D`

Probe config SHA-256:
`CAEE79081EAAB043A7279F3BC14ABA1094AEBA909AA6AF5AD76492EFF470CFD1`

The independently selected teardown frame remains frozen at SHA-256
`670B45D3C70D6B7AAD361EF1BE5F0BDF0165F0DFD6016612438AE9F983DD0DAD`.
It is visual evidence only for the post-confirmation UI transition.

## Evidence ceiling

Proven: guarded read-only instrumentation, StartGame observation, stable raw
operand values for the controlled P30/default-player pairing, and post-exit bypass
of both faction reads.

Not proven: authentic player faction, original-server faction assignment or enemy
table policy, generic local/target ordering outside this controlled run, stable
hostility, sword cursor, FightAttr, AI, attack, combat, damage, death or loot.
