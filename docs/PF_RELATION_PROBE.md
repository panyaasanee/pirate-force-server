# Relation comparator capture probe

`tools/pf_relation_probe.py` is a read-only Frida diagnostic for the guarded
32-bit `GameClient.local.bin`. It refuses to attach unless filename, file size,
SHA-256, PE machine/magic/image base/image size, and the bytes at every hook
match `tools/pf_relation_probe_config.json`.

The probe observes:

- the static StartGame observation address `0x5DDC57`;
- relation-comparator entry `0x43C380`;
- its two proven BasicAttr `+0x68` dword reads at `0x43C5CD` and `0x43C5D4`.

Static provenance does not yet identify which comparator operand is the local
actor and which is the target. JSONL therefore calls them `first` and `second`.
The raw u32 values are evidence, not an enemy/friendly interpretation.

Run only after starting the exact guarded client, writing output to the active
capture directory:

```powershell
py -3 tools\pf_relation_probe.py --pid <GameClient-PID> `
  --output "<capture-directory>\relation_probe.jsonl"
```

The file is UTF-8 JSONL, flushed after every validated event. The agent performs
bounded readable-range checks and contains no memory writes, native calls,
packet injection, or UI input. Stop with Ctrl+C. A completed runtime probe is
required before assigning roles or relation semantics. REL-001 now has one such
controlled run: its value injection correlates `first` with P30 and `second` with
the current local/default actor for that run only; authentic faction and policy
remain unknown.

The embedded agent uses Frida 17 `NativePointer` read methods rather than the
removed `Memory.read*` namespace functions. This distinction is covered by an
offline source-contract regression test.

The disk guard always compares every configured code byte exactly. At runtime,
ASLR adjustment is accepted only for the explicitly declared four-byte PE
relocation in the comparator-entry `push` operand; all opcode bytes and both
`+0x68` read instructions remain exact. The relocated operand must equal the
disk value plus the observed module-base slide.
