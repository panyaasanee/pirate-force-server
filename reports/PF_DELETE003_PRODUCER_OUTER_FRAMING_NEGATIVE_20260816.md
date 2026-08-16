# DELETE-003 — DeleteActor producer and outer-framing negative

Date: 2026-08-16

## Primary claim

Both exact client images prove two class-specific producers of a nested
`DeleteActorVital` object and their common generic submission boundary. They do
not prove the outer protocol class, outer version/mask/count, a server response,
or any repository mutation.

The primary claim is therefore limited to the client-side nested-object producer
and submission boundary. No semantic name is assigned to raw operation values 1
or 2.

## Exact client provenance

The static result was checked against both 14,759,424-byte client images:

- `GameClient.bin`, SHA-256
  `C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
- `GameClient.local.bin`, SHA-256
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`

The relevant virtual addresses and bytes agree between the two images.

## Grade A static facts

- Registration function `0xBEE300` hashes the exact ASCII class name
  `DeleteActorVital` and stores its deterministic 16-bit class ID in
  `0x1081FD0`; getter `0x5E4D90` reads that value. The resulting nested ID is
  `0x36DB`.
- Constructor `0x5E4D00` installs vtable `0xF301A0` and initializes raw fields
  `+0x14=0`, `+0x15=0`, `+0x18=0`, and an empty wstring object at `+0x1C`.
  Exact codec `0x5E4E10` visits raw fields `+0x14` (u8), `+0x15` (u8),
  `+0x18` (u32), then `+0x1C` (wstring).
- Producer `0x4B2990`, called directly from `0x4E621D`, allocates the class at
  `0x4B29C0`, writes raw `+0x14=1` and `+0x15` from its selector argument,
  leaves constructor-default `+0x18=0`, copies an opaque UI-derived wstring into
  `+0x1C`, then submits the object through `0x4011A0 -> 0x5DD800` at
  `0x4B2A0B/0x4B2A12`.
- In the calling UI path, `0x4E6190` obtains the selector from
  `[object+0x10]+0x94`, obtains the opaque string through a UI virtual call, and
  invokes `0x4B2990`. Exact callers reach this path at `0x4E6325` and
  `0x4E6362`. These are UI/provenance facts only; the string's meaning is not
  proven.
- In `0x4B47A0`, the selected record supplies raw selector byte `record+0x18`.
  A local branch value is 1 when `record+0xF4==0` and 2 when nonzero. The value-2
  path allocates the class at `0x4B48AA`, writes raw `+0x14=2` and
  `+0x15=selector`, retains default `+0x18=0` and empty `+0x1C`, then submits
  through `0x4011A0 -> 0x5DD800` at `0x4B48B7/0x4B48BE`. The value-1 path opens
  a UI object, stores the selector at that UI object's `+0x94`, and can later
  reach `0x4E6190 -> 0x4B2990`.
- `0x5DD800` is a generic submission routine shared by many unrelated classes;
  it forwards the object through `0x5F3D60`. Reaching it does not identify an
  outer protocol envelope.
- The distinct registration `0xBEE070` hashes the exact class name
  `GSCN_LoginProtocol` into `0x1081C98`, and getter `0x5E3710` reads it. No exact
  dataflow from either DeleteActor producer to construction or field population
  of that outer class was recovered in the bounded direct chain.
- Class-specific inbound consumer `0x5EFDC0` forwards raw object values to
  `0x4BAEB0` as `(zero-extended +0x14, sign-extended +0x15, raw +0x18)`.
  `0x4BAEB0` has UI branches for raw first-argument values 1 through 4. This does
  not prove response meaning, success, refresh behavior, or persistence.

The strict nested-record parser in `src/pirateforce_foundation/delete_actor.py`
remains intentionally limited to the exact nested request record. Its rejection
of trailing data is a host safety boundary, not proof that the native client
codec enforces outer EOF.

## Bounded outer-framing negative

The direct producer chain proves only class-object construction and generic
submission. It does not establish:

- an outer class ID;
- outer version, mask, count, or nested-version fields;
- exact client-to-server envelope direction at the wire boundary;
- response class/order; or
- a server-side state transition.

The existing SCENE-013 hash-guarded structural corpus contains 2,621 decoded
frames across six unique logical sources. Its complete nested-ID inventory has no
`0x36DB` entry. Every source is GameClient-to-local-emulator, and none is an
original server-to-client capture. This is a bounded corpus negative only, not
protocol absence and not outer-envelope evidence.

## Isolated UI/capture result

The isolated run root is
`GameClient/capture_delete_disposable_25690816_105919`. It used the isolated
SQLite database
`state/delete_disposable_25690816_105919.sqlite3`.

Exact artifacts prove:

- the client sent and the Foundation server committed one CreateActor request for
  `DelTst01`; the final read-only database row has selector 0, non-null identity,
  and `deleted_at=NULL`;
- all retained login/game raw, live and decoded-event logs contain zero
  `0x36DB`/decimal-14043/DeleteActor structural markers;
- server stderr is empty;
- the before/after guard records the same 53,248-byte main database SHA-256
  `E448680C2FDADFDEB8C5425FFBAEB2757BF5B9CF1F31D36C14CCC5F437EC2361`,
  with WAL and SHM absent before and after, and verdict `PASS_UNCHANGED`.

The operator reported seeing the character-delete confirmation dialog and then
cancelled it. No screenshot artifact was retained, so that UI observation is not
claimed from the raw logs and is not promoted as visual-runtime proof. Because the
final affirmative action was not taken, this run proves no DeleteActor request,
response, list refresh, soft delete, hard delete, or other mutation.

Any future UI deletion attempt requires fresh action-time operator confirmation
before the final affirmative action. This report does not authorize deletion.

## Nonclaims and stop rule

Raw values 1 and 2 remain operation values only. They are not named delete,
schedule, cancel, restore, immediate, deferred, password, credential, or status.
The selector and opaque UTF-16LE bytes have no promoted account/character meaning.

Do not add an outer parser, response builder, dispatcher branch, repository call,
or `deleted_at` mutation from this checkpoint. Resume outer framing only after an
exact natural `0x36DB` wire is captured at structural boundaries or an exact
static edge binds the same nested object to a fully populated outer envelope.
Any destructive UI/runtime test additionally requires action-time confirmation.

