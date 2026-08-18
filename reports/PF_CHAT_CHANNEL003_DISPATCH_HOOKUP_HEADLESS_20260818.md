# CHAT-CHANNEL-003 — channel-message dispatch hookup, headless wire pass (HYP-PF-019 v2)

Date: 2026-08-18 · Implementation lane under the chief session · Trigger:
CHAT-CHANNEL-002
(`reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md`) built the
shared-serializer codec and **deliberately did not wire it in**, so no composed
channel frame could ever leave the process and GT-016 stayed BLOCKED in
practice while being "unblocked" on paper. Processed under the owner's standing
pre-approval of 2026-08-17 18:2x.

## Primary claim (grade B, wire layer only)

Behind the new separate opt-in
`scenarios/channel_message_hypothesis_channel_sweep.json` (response_policy
`sweep_one_decoded_chat_input_across_five_shared_serializer_channels_no_write_no_close`,
`production_allowed: false`) and the new CLI flag
`--channel-message-hypothesis-scenario`, the Foundation server answers **one**
accepted chat input frame (vital `0xAC52`, the exact 34-byte ASCII-12 shape
`classify_chat_input_attempt` already accepts, request classification unchanged
from CHAT-ECHO-001) with **five composed frames**, one per shared-serializer
channel, in the order GT-016 asks to read them on screen:

| # | channel | id | action label | delay |
|---|---|---|---|---|
| 1 | Channel_LocalTalkMessageVital | `0xAC52` | `HYP_PF_019_CHANNEL_SWEEP_LOCALTALK` | 0.0 s |
| 2 | Channel_PartyMessageVital | `0x82E6` | `HYP_PF_019_CHANNEL_SWEEP_PARTY` | 3.0 s |
| 3 | Channel_GuildMessageVital | `0x8189` | `HYP_PF_019_CHANNEL_SWEEP_GUILD` | 3.0 s |
| 4 | Channel_GMGlobalMessageVital | `0x9F2C` | `HYP_PF_019_CHANNEL_SWEEP_GMGLOBAL` | 3.0 s |
| 5 | Channel_ActorBoardcastMessageVital | `0xEDFA` | `HYP_PF_019_CHANNEL_SWEEP_ACTORBOARDCAST` | 3.0 s |

The request payload is **decoded** with `decode_channel_message_payload` into
`(speaker, body)` — not spliced — and the decoded body is re-composed once per
channel through `make_channel_message_response`, inside the same accepted
`GSCN_RunTimeProtocolRes` v4 one-vital collection envelope GT-009 proved
deliverable. The speaker is **empty on all five by policy**, which is the whole
experiment: with an empty speaker the five nested payloads are identical byte
for byte, so whatever the client does differently between the five lines, it
did on the strength of the 16-bit class id alone.

The delay semantics were read out of the frozen V141 sender rather than
assumed: it does `send_deadline += delay` on one cumulative monotonic timeline
and sleeps to that deadline, so the fourth action-tuple field is the **gap
before each send**. First frame 0.0, each later frame the full 3.0 s spacing;
one sweep spans 12.0 s.

## Measured, on bytes the dispatcher produced

Everything below is asserted in `tests/test_channel_message_dispatch.py`
against actions returned by the real `make_state_class` dispatch path (login →
V25 create → start_game → runtime-ready), not against unit fixtures.

- **Five actions, in the pinned order.** The label list equals the scenario's
  own `dispatch.action_labels`, and the frames' `pc[16:18]` equal the
  scenario's `dispatch.channel_id_order`.
- **The five nested payloads are identical byte for byte.** All five are the
  same 34 bytes at `pc[20:54]`, one sha256
  `0DC90C60BB22C92FDFF3649125703546E9BE324C2D7C265023C00DACA1C584CF` — which
  is also the GT-006 captured request payload — and all five re-decode to
  `("", "PFCHATPROBE1")`.
- **The five composed PCs differ in exactly two bytes.** Pairwise diff over all
  five 56-byte PCs yields the index set `{16, 17}` and nothing else; blanking
  those two bytes collapses the five into one. This is CHAT-CHANNEL-001's
  "the channel id IS the selector" conclusion re-proven under dispatch.
- **All ten per-channel pins match** (probe1, speaker `""`, 56 B PC / 66 B
  frame each):

| channel | pc sha256 | frame sha256 |
|---|---|---|
| LocalTalk `0xAC52` | `B92C185ABB0C707EA6512409CAAF5ADC03D911E0399F0CC0DC60A2C49111FA06` | `06C23375BE9A115C59AF410E1446393E2EE3B3294254BCDF6EB88FADFF7E2323` |
| Party `0x82E6` | `23063CB9B2C66DC6DE59F52F9DAB1E3EE2F67D66BA0226BBAD0EA2F49EB44B03` | `73C2B4C15C63A42FB182D5537081122B9D6EB9FFA9A039B0FED5658C832BDD53` |
| Guild `0x8189` | `E1B235C1F014E245FFCCC7E30A081755DFE4DEE4045D7DEBA5C5C7507F34A9CE` | `4CD610FE9C996E46D76E95B3A121160C9D0C32191CCCD7BB20BF6330C8589AA2` |
| GMGlobal `0x9F2C` | `6F6566C0FAE8CAD9EE2C6B1CE1BC75EC7C6E93654666A6CE6C8E5B20228B8C5E` | `E9619EFA94A8FB02FD67E0477C2538367C32ED9B93422295D6DD348BB35BDEA3` |
| ActorBoardcast `0xEDFA` | `8EC02EC28784C7FEC46DED02421917E632015C71F972B403125D0E5915AB4FC4` | `A09A8C768A982C227492342947EFDDE70C358FD5A764562D615211AFC899760F` |

  The LocalTalk row is not a new pin: it is the hash CHAT-ECHO-001 already put
  on the wire through a code path that never parsed the payload, so the
  dispatcher reproducing it is an external check on the decode, not a
  self-certification. Every hash in the table was recomputed from scratch
  (`legacy.make_runtime_vitals` on a payload rebuilt from the wstring rules)
  before it was written into the scenario file.
- **Not one-shot, no accumulated state.** Three consecutive requests give
  3 × 5 = 15 frames; request 1 and request 3 (same probe) return byte-identical
  action tuples.
- **No database write.** The temp DB file is byte-identical before/after a
  three-sweep window and after refused frames; the session lease stays open.

## Implementation (opt-in, fail closed, no write, no close, not one-shot)

- `scenarios/channel_message_hypothesis_channel_sweep.json` — second entry in
  the exact allowlist. The CHAT-CHANNEL-002 file is **not** edited (its
  byte-hash `31D1E45A..E6B2` is now pinned in the tests). The new file carries
  the whole dispatch policy — trigger, channel order, channel id order,
  spacing, speaker policy, action labels, `one_shot: false`,
  `socket_action: none` — plus the per-channel payload/PC/frame pins, so a
  one-field edit anywhere in it fails the lane closed.
- `src/pirateforce_foundation/channel_message_hypothesis.py` —
  `CHANNEL_SWEEP_ORDER` / `CHANNEL_SWEEP_SPACING_SECONDS` /
  `CHANNEL_SWEEP_SPEAKER` / `CHANNEL_SWEEP_ACTION_LABEL_PREFIX`, the derived
  `channel_short_name` (label tokens derived from the class-name literal, like
  the ids, so there is no second table to drift), `_require_sweep_order`
  (the order must be a permutation of the five, LocalTalk first, no duplicate
  label), and the second scenario profile. The scenario dataclass gained
  `channel_order` / `spacing_seconds`, empty on the codec-only profile.
- `src/pirateforce_foundation/runtime.py` —
  `_dispatch_channel_message_hypothesis`: the same four guards as the echo
  lane (`ascii12` classification → `foundation.selected` → `teleport_sent` →
  `runtime_ack_sent`), then a decode, then five compositions. Every frame is
  composed and pinned before any is queued. Events:
  `channel_message_hypothesis_channel_sweep_sent` on success;
  `channel_message_hypothesis_{wrong_length,wrong_prefix,wrong_text,wrong_envelope}_no_reply`,
  `..._no_selected_no_reply`, `..._wrong_sequence_no_reply`,
  `..._undecodable_payload_no_reply` on refusal. No store call, no socket
  action, no one-shot latch.
- `src/pirateforce_foundation/app.py` — `--channel-message-hypothesis-scenario`
  in the same mutually exclusive group, requiring an explicit existing `--db`,
  entering console mode `channel-message-hypothesis`, running
  `store.migrate()` + `expire_open_sessions()` like every other opt-in lane.

The `..._undecodable_payload_no_reply` branch is a **structural backstop, not a
live branch**: today the ASCII-12 shape is a strict subset of the 0x65AD40
schema, so every accepted request decodes. `test_every_accepted_request_shape_is_decodable`
pins exactly that, so the day someone widens the accepted request shape the
backstop starts earning its keep instead of silently leaking.

## Containment test changed on purpose

`tests/test_channel_message_hypothesis.py` previously asserted the strongest
possible statement — the string `channel_message_hypothesis` appeared in **no**
runtime module, so the lane was unreachable by construction rather than by
flag. That assertion is the thing this milestone had to break, and it was
broken openly: it is now
`test_this_lane_is_reachable_only_through_the_opt_in_scenario`, with a
docstring saying what moved and why. The id was **not** hidden from any
scanner and no derived/lazy import was used to keep a guard green. What the
rewritten guard still enforces:

- the importer list is **exact**: `["app.py", "runtime.py"]` — a third one
  fails here;
- `connection.py` and `scenario.py` still never mention it, and the frozen
  v141 module still carries no `Channel_` token;
- every `runtime.py` mention sits inside the
  `channel_message_hypothesis_scenario is not None` gate, and the composer has
  exactly one call site;
- both profiles keep `test_only: true`, `production_allowed: false`,
  `database_write: none`;
- the CLI flag requires an explicit `--db`.

`tests/test_presentation_ownership.py` needed **no** change: its chat-vital
allowlist (`channel_message_hypothesis.py`, `chat_input_hypothesis.py`,
`runtime.py`) was already settled by chief round 76 and both new mentions are
inside it.

## Test layer (sandbox)

- `tests/test_channel_message_dispatch.py` (new, 25 tests) — the dispatch
  proof above: order, labels, channel ids, identical payloads, two-byte PC
  delta, ten pinned hashes, composer equivalence, spacing, decode-not-splice
  on an uncaptured body, repeatability, no-write (accepted **and** refused),
  six fail-closed families, no-scenario baseline, both mutual-exclusion pairs,
  tampered-object and tampered-file rejection, and the codec-only profile
  proven unable to drive a sweep.
- `tests/test_channel_message_hypothesis.py` — 34 → 40 tests; the six added
  ones are the rewritten containment guard plus the sweep profile's own
  allowlist/pin checks and the CHAT-CHANNEL-002 scenario-file byte-hash pin.

Repo-wide: `python3 -m pytest tests/ -q` → **693 passed, 1 failed, 324 subtests
passed**, against a **662 passed, 1 failed, 321 subtests passed** baseline
measured before any edit in this milestone. That is +31 tests (25 in the new
file, 6 in the existing one) and +3 subtests (the three manifest-iterating
subtests in `test_foundation_legacy_seam.py` picking up this report's own
manifest). The single failure is the pre-existing sandbox-Python-3.10 one
(`test_server_shutdown.py::test_primary_exception_is_preserved_with_cleanup_failure`
needs `__notes__`, 3.11+); it is untouched and not special-cased.

## Proven vs not proven

**Proven (headless, wire layer):** that five channel frames leave the
dispatcher for one accepted chat frame, in the pinned order, with the pinned
channel ids, with byte-identical payloads and a two-byte PC delta, matching ten
pinned hashes, repeatably, with zero database bytes changed and zero socket
action, and only when the opt-in scenario is handed in.

**Not proven (client layer, GT-016):** whether the real client renders any of
the five lines at all; which channel tag it prefixes each with; whether an
empty speaker renders the same way on the four non-LocalTalk channels as
GT-009 showed for LocalTalk; and whether 3.0 s is enough spacing for five
separate lines rather than a coalesced burst. Nothing in this milestone
observed a client.

## Nonclaims

1. **No client-observable claim whatsoever.** Only `0xAC52` has ever been on
   this project's wire in either direction. The other four channels' pins say
   "if the server sends this, these are the bytes", not "this was captured",
   and not "the client accepted it". That is exactly GT-016.
2. **This is not fan-out, routing or membership.** A sweep is five frames back
   to the one connection that asked for them. Delivery to any other session,
   channel membership, join/leave authority and the original server's routing
   policy remain entirely uncaptured and need two concurrent sessions.
3. **Not driven over real TCP.** Unlike CHAT-ECHO-002 there is no real-server
   loopback smoke run in this milestone: the proof is through the real
   dispatcher on a temp database, one layer below a socket.
4. **No persistence.** Chat has no table; `database_write` is `none` and the
   no-write claim is verified by byte-comparing the database file.
5. **No production or default-mode behaviour changed.** `production_allowed`
   stays false on both profiles; without the flag the 0xAC52 frame remains
   counted-and-ignored exactly as GT-006 observed.
6. All CHAT-CHANNEL-002 nonclaims stand: Whisper `0x556C` is refused by
   construction (different schema), the undecoded `0x08` / `+0x3C` / `+0x28`
   family fields are untouched, and no original-server response policy is
   claimed — the corpus still has no chat wire from the original server in
   either direction.
