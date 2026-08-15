# ADR 0001: Evidence-constrained modular foundation

Status: accepted, 2026-08-15

## Decision

Use a typed Python domain core, a repository interface, migration-first SQLite,
and a thin compatibility projector into immutable V141 serializers. Keep Rust as
a later profiling-driven option. Do not introduce Django or FastAPI.

Persist the complete actor and AvatarAttr wires as opaque bytes. Typed columns are
limited to proven ownership fields: account, selector, identity, display name,
scene and position. In particular, no job/class field is inferred. AvatarAttr's
proven common-Attr identity is rebound to the same server identity as the actor,
ActorAttr and MovementAttr; every other AvatarAttr byte remains opaque.

The SQLite transaction commits before a protocol success is projected. Runtime
experiment flags remain connection-local and are never persisted.

The current release builder produces a deterministic source archive. A generated
single-file standalone server remains a later migration gate and is not claimed yet.
