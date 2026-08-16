# ITEM-MOVE-CAPTURE-001 — free-slot request runtime pass

Date: 2026-08-17
Scope: one opt-in local capture-only session; no move response or persistence.

## Result

Grade B pass for the narrow request-producer claim. With the exact merged
Backpack visible as `3/40`, identity 1 quantity 2 occupied slot 0, identity 2
occupied slot 1, slot 2 was empty, and identity 4 occupied slot 3. One drag from
slot 0 to slot 2 produced exactly one 36-byte `ItemOperateVitalReq`:

`12 6F6E 14 00000000 08 00 0B 02 12 0100 12 ED4B 0B 00 0B 04 14 02000000 32 0100000000000000`

The decoded fields are `operation=4`, `value32=2`, and
`item_identity=0x0000000000000001`. The retained event is frame 49 at
`2026-08-17T00:04:22.228+07:00`.

## No-reply and state oracle

- Capture-only mode emitted no `ItemOperateVitalRes`; the immediate server write
  after frame 49 was the ordinary runtime heartbeat sequence 32.
- The Backpack remained `3/40` and visually retained identity 1 quantity 2 in
  slot 0 (controlled UI observation; no screenshot retained).
- The post-run immutable read oracle records exact rows
  `[id1/template2600001/qty2/slot0, id2/2400901/qty1/slot1,
  id4/2200002/qty1/slot3]`, `integrity_check=ok`, and empty foreign-key check.
- Traffic continued through request frame 188 and heartbeat 116. Server stderr is
  empty. Client/log closure and one `[FOUNDATION] stopped` marker are retained.

The database main-file hash is a post-run snapshot only; no pre-run file hash was
retained, so this report does not claim byte-level `PASS_UNCHANGED`. The exact
scenario precondition, StartGame/UI state, capture-only implementation contract,
and post-run logical rows jointly bound the no-mutation observation.

## Evidence ceiling and next boundary

This proves the exact client producer for a free-slot move attempt and the
server's response-free capture boundary. It does not prove an original-server
response, accepted move, durable/reconnect policy, occupied-slot behavior,
swap/displacement, equipment semantics, or generalized inventory operations.

The next isolated milestone is the already ledgered, test-only HYP-PF-008 runtime
acceptance: enable only `ITEM-MOVE-HYP-001`, repeat this exact request, require one
hash-pinned composed response and slot-2 UI update, then reconnect to test the
same opt-in persisted state. Retire or correct it on any mismatch.
