# ADR 0001: Evidence-constrained modular foundation

Status: accepted, 2026-08-15

## Decision

Use a typed Python domain core, a repository interface, migration-first SQLite,
and a thin compatibility projector into immutable V141 serializers. Keep Rust as
a later profiling-driven option. Do not introduce Django or FastAPI.

Persist the complete actor and AvatarAttr wires as opaque bytes. Typed columns are
limited to proven ownership fields: account, selector, identity, display name,
scene and position. In particular, no job/class field is inferred. AvatarAttr's
existing optional identity bit is preserved as-is; StartGame does not invent one.

The SQLite transaction commits before a protocol success is projected. Runtime
experiment flags remain connection-local and are never persisted.

Standalone releases are deterministic generated artifacts, not hand-edited source.
