# CHAT-CHANNEL-002 — server-side decoder and emitter for the shared-serializer `Channel_*Message` family (HYP-PF-019)

Date: 2026-08-18 · Implementation lane under the chief session · Additive,
scope-only (4 new files, no existing file modified) · Trigger: CHAT-CHANNEL-001
(`reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md`,
commit `b2e4669`) decoded the client-side wire schema of the five channels that
share serializer `0x65AD40` and observed that the server touches 1 of 17
channels and decodes 0 of 17.

## 1. What this lane changes

`src/pirateforce_foundation/chat_input_hypothesis.py` (CHAT-ECHO-001/002)
treats the first ten bytes of the captured `0xAC52` payload as **one opaque
pinned blob** (`CHAT_INPUT_PREFIX = 48000000004818000000`). Its own docstring
states that the `0x18` at index 6 is only a *candidate* length field and that
"nothing here claims or decodes it". Consequently the server can answer only a
request it has already received, byte-for-byte, at one fixed text length: the
echo lane is a mirror, not an emitter.

This lane implements the schema CHAT-CHANNEL-001 disassembled and makes the
server a **generator**:

```
decode:  payload                      -> (speaker, body)
encode:  (channel, speaker, body)     -> payload -> GSCN_RunTimeProtocolRes v4 PC/frame
```

No request template is required. The envelope is **not** rebuilt: composition
reuses the frozen v141 `make_runtime_vitals` one-vital collection helper that
CHAT-ECHO-001 already proved deliverable, so the only new bytes on the wire are
the payload and the 16-bit channel id.

## 2. Evidence this lane stands on (all pre-existing, not re-proven here)

| fact | source |
|---|---|
| client binary `GameClient.local.bin` SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623` | CHAT-CHANNEL-001 |
| five channels share Serialize `0x65AD40` (base `Channel_MessageVtial`, vtable +0x18) | CHAT-CHANNEL-001 §2, `tools/pf_chat_channel_family_static.py` (69 guards) |
| that serializer's field order = `wstring@+0x34` (speaker) then `wstring@+0x18` (body) | CHAT-CHANNEL-001 §2 |
| wstring codec `0x89A810`/`0x89A880` = tag `0x48` + u32 byte-length + UTF-16LE, no NUL | CHAT-CHANNEL-001 §2 |
| ids are the PF-NAMEID-HASH-001 hash (`0x89B220`) of the in-image class-name literal | CHAT-CHANNEL-001 §1 |
| anchor `name_id("Channel_LocalTalkMessageVital") == 0xAC52` == the id GT-006 captured on the wire | CHAT-CHANNEL-001 §1 |
| `Channel_WhisperVital` `0x556C` uses a **different** serializer `0x65AEA0` (third wstring @+0x50 + u8 result @+0x6C) | CHAT-CHANNEL-001 §2/§12 |
| the two captured GT-006 payloads and the CHAT-ECHO-001/002 response pins | `src/pirateforce_foundation/chat_input_hypothesis.py`, `scenarios/chat_input_hypothesis_echo.json`, `reports/PF_GT006_...md` |

The five accepted channels, ids **derived** at import time from the class-name
literals (not tabled by hand — `_require_derived_channel_ids`):

| class | id |
|---|---|
| `Channel_LocalTalkMessageVital` | `0xAC52` (44114) |
| `Channel_PartyMessageVital` | `0x82E6` (33510) |
| `Channel_GuildMessageVital` | `0x8189` (33161) |
| `Channel_ActorBoardcastMessageVital` | `0xEDFA` (60922) |
| `Channel_GMGlobalMessageVital` | `0x9F2C` (40748) |

## 3. What is proven here (grade B — offline wire-composition layer)

### 3.1 The captured payloads round-trip byte-exactly

```
decode(probe1) == ("", "PFCHATPROBE1")      decode(probe2) == ("", "PFCHATPROBE2")
encode("", "PFCHATPROBE1")
  = 48 00000000 48 18000000 500046004300480041005400500052004F00420045003100
  = CHAT_INPUT_PROBE_PAYLOADS["probe1"]   (34 B, sha256 0DC90C60BB22C92FDFF3649125703546E9BE324C2D7C265023C00DACA1C584CF)
```

Zero bytes left over, both probes, both directions. The ten "opaque prefix"
bytes are now two parsed headers with a field name each.

### 3.2 Cross-check A — the generated LocalTalk response **is** the CHAT-ECHO-001 response

Composing the *generated* payload for `channel_id = 0xAC52` through
`legacy.make_runtime_vitals` reproduces the hashes pinned in
`scenarios/chat_input_hypothesis_echo.json`, which were produced by the older
opaque-splice path that never parsed anything:

| pin | size | sha256 | matches |
|---|---|---|---|
| response PC probe1 | 56 B | `B92C185ABB0C707EA6512409CAAF5ADC03D911E0399F0CC0DC60A2C49111FA06` | ✔ |
| response frame probe1 | 66 B | `06C23375BE9A115C59AF410E1446393E2EE3B3294254BCDF6EB88FADFF7E2323` | ✔ |
| response PC probe2 | 56 B | `539B177F430B4391348F440932E119C1D58788BF15BFA061BF16F56E4DDDFC2C` | ✔ |
| response frame probe2 | 66 B | `E97A12256A0D61F8CBB8B433336F97D9EEA2A93CADA5934EAAEB5B7D4706EA10` | ✔ |

The test reads those hashes **out of the scenario JSON file at run time**, not
from a copied constant.

### 3.3 Cross-check B — the generated speaker variant **is** the CHAT-ECHO-002 variant

`encode("test01", "PFCHATPROBE1")` reproduces the CHAT-ECHO-002 splice result:

```
48 0C000000 740065007300740030003100 48 18000000 500046004300480041005400500052004F00420045003100
```

| pin | size | sha256 | matches |
|---|---|---|---|
| variant payload probe1 | 46 B | `D702CEE2B3BD83E7568EBAFC93B73D3B87D9AF643EE8155B36D827A6E24B4A02` | ✔ |
| variant payload probe2 | 46 B | `A9060FC24E676B8BB5752814A6404E8F95FB9438B9EA755727E480699A046921` | ✔ |
| response PC probe1 | 68 B | `5D80E83CE4C60A3927C9AFE020B0833358763BFE3CA1ECAB3EFB28E98BC9EE17` | ✔ |
| response frame probe1 | 79 B | `AA27B015AB9EA30537331408D5F262BC37EA489A0DB8E7B3BC7D4A1896D99D23` | ✔ |

Two independently produced pin sets, reproduced from a schema-driven encoder.
A wrong field order, a wrong tag byte, a wrong length width, or a wrong
endianness cannot survive either cross-check. **This is the evidence that the
decode is real and not a plausible story.**

### 3.4 The five channels are wire-identical on composed bytes too

Composing the same `("", "PFCHATPROBE1")` message on all five ids gives five
56-byte PCs that are **byte-identical except for PC bytes `[16:18]`**, the
16-bit class id — CHAT-CHANNEL-001's central static finding, reproduced on
bytes this server generates:

| channel | response PC sha256 | response frame sha256 |
|---|---|---|
| `Channel_LocalTalkMessageVital` | `B92C185ABB0C707EA6512409CAAF5ADC03D911E0399F0CC0DC60A2C49111FA06` | `06C23375BE9A115C59AF410E1446393E2EE3B3294254BCDF6EB88FADFF7E2323` |
| `Channel_PartyMessageVital` | `23063CB9B2C66DC6DE59F52F9DAB1E3EE2F67D66BA0226BBAD0EA2F49EB44B03` | `73C2B4C15C63A42FB182D5537081122B9D6EB9FFA9A039B0FED5658C832BDD53` |
| `Channel_GuildMessageVital` | `E1B235C1F014E245FFCCC7E30A081755DFE4DEE4045D7DEBA5C5C7507F34A9CE` | `4CD610FE9C996E46D76E95B3A121160C9D0C32191CCCD7BB20BF6330C8589AA2` |
| `Channel_ActorBoardcastMessageVital` | `8EC02EC28784C7FEC46DED02421917E632015C71F972B403125D0E5915AB4FC4` | `A09A8C768A982C227492342947EFDDE70C358FD5A764562D615211AFC899760F` |
| `Channel_GMGlobalMessageVital` | `6F6566C0FAE8CAD9EE2C6B1CE1BC75EC7C6E93654666A6CE6C8E5B20228B8C5E` | `E9619EFA94A8FB02FD67E0477C2538367C32ED9B93422295D6DD348BB35BDEA3` |

Composition size rule: `len(PC) = 22 + len(payload)`; nested payload always at
PC offset 20; channel id always at PC `[16:18]` little-endian.

### 3.5 Fail-closed matrix (every row = no reply, no write, no partial result)

| rejected input | reason token |
|---|---|
| channel id outside the five (incl. Whisper `0x556C`, `JoinCustomChannel 0xBA58`, `CustomChannelMessage 0xE064`, `ForbidTalkNotification 0xFDF2`, non-int, `bool`, negative, out of range) | `channel_outside_shared_serializer` |
| payload shorter than a 5-byte wstring header at either field | `truncated_wstring_header` |
| tag byte != `0x48` at either header | `wrong_wstring_tag` |
| odd u32 byte-length (cannot be UTF-16LE) | `odd_wstring_byte_length` |
| declared length larger than the bytes remaining (incl. `0xFFFFFFFE`) | `wstring_length_exceeds_payload` |
| bytes left after the second wstring (e.g. a whisper-shaped 3rd wstring + result byte) | `trailing_bytes_after_body` |
| text that is not two bytes per character: non-BMP (surrogate pair), unpaired high or low surrogate — on decode **and** on encode | `text_not_two_bytes_per_character` |
| empty body (decode and encode) | `empty_body` |

An **empty speaker is accepted** on decode: that is exactly what every captured
client request contains. The encoder re-decodes its own output before
returning, so it can never emit something its decoder would refuse.

### 3.6 Containment

`test_only: true`, `production_allowed: false`, `persisted_post_state.
database_write: "none"` (chat has no table), loaded through an exact-allowlist
gate that rejects 10 distinct tamper mutations plus the two CHAT-ECHO scenario
files. The lane is **not wired into production dispatch**: a test asserts that
`runtime.py`, `app.py`, `connection.py` and `scenario.py` contain no reference
to the module, and that the immutable v141 snapshot contains neither the module
name nor any `Channel_` token. `scenarios/chat_input_hypothesis_echo.json` is
hash-pinned as untouched (`1350C98A0DE99B4690191BB998F66A0DFE7B8A7A41F15F33DBAD135DE0C75ABB`).

## 4. Explicit non-claims

1. **No client-render claim.** Nothing here says the client displays a message
   on any of the five channels, or how. Four of the five have never been sent
   to a client by this project. That is GT-016 (attended), not run.
2. **No wire observation of the four non-LocalTalk channels.** `0x82E6`,
   `0x8189`, `0xEDFA`, `0x9F2C` have never appeared on this project's wire in
   either direction. Their pins here are *composition* pins (what this server
   would emit), derived from the client's static schema — not captures.
3. **No original-server claim.** Routing, fan-out, channel scope, membership
   authority and whisper recipient resolution of the original server stay
   uncaptured; two concurrent sessions have never existed in this project.
   Nothing here says who *should* receive a message on a given channel.
4. **No delivery claim.** This lane composes bytes offline. It performs no
   fan-out, addresses no second session, and was not run against a live client
   or a live socket in this milestone (headless/attended wire passes are
   separate lanes).
5. **No whisper claim.** `Channel_WhisperVital 0x556C` is refused, not
   supported. The meaning of its `u8@+0x6C` result byte (`1` → system message
   `0x0B`, `2` → `0x18`) is still uninterpreted, exactly as CHAT-CHANNEL-001
   left it.
6. **No claim about non-ASCII rendering.** The encoder carries any BMP text
   because the schema is two bytes per character; that Thai/CJK text *renders*
   in the client's chat UI is not claimed. Non-BMP text is refused outright —
   this is a deliberate limitation, not a proof that the client rejects it.
7. **No production-behaviour claim.** Nothing is connected to the production
   dispatch path and `production_allowed` stays false.
8. **Not proven: that the original protocol allows a server-originated
   message on these ids at all.** The only capture is client→server on
   `0xAC52`. That the same class id is legal server→client is inferred from the
   bidirectional Serialize (`ret 8`, `bl` selects read/write codecs) and from
   the client-side dispatcher chain that downcasts inbound vitals of all five
   classes — strong, but it is an inference from static code, not a capture.
   GT-009 did prove a `0xAC52` server→client response is accepted and rendered;
   the other four are inference only.

## 5. One pre-existing gate test now fails by design — chief decision required

`tests/test_presentation_ownership.py::ChatInputOwnershipTests::
test_no_foundation_module_mentions_the_unknown_chat_vital` pins an **exact**
allowlist of Foundation modules permitted to mention the GT-006 chat vital id
(regex `(?i)AC52|44114`, allowlist `["chat_input_hypothesis.py",
"runtime.py"]`). This lane is a **second deliberate owner** of that id, so the
guard now reports:

```
AssertionError: Lists differ:
  ['channel_message_hypothesis.py', 'chat_input_hypothesis.py', 'runtime.py']
!= ['chat_input_hypothesis.py', 'runtime.py']
```

That is exactly the signal the guard was built to raise: its own comment says
"growing this list means a new deliberate ownership movement". **This lane did
not hide the id to make the guard green** — deriving the id at import time from
the class-name hash would have silenced the scanner while leaving the module a
real owner, which would put a false statement into the repo's own evidence
system.

`tests/test_presentation_ownership.py` is outside this lane's 4-file scope, so
the one-line resolution is left to the chief:

```python
CHAT_VITAL_ALLOWED_MODULES = [
    "channel_message_hypothesis.py", "chat_input_hypothesis.py", "runtime.py",
]
```

(sorted order — that is what `modules_mentioning` returns). No other test in
the suite is affected; `tests/test_chat_input_echo.py` (33 tests) and
`tests/test_foundation_legacy_seam.py` stay green.

## 6. Coverage / ledger

- Milestone `chat / chat_channels_and_routing` stays **`in_progress`**; this
  lane does **not** flip `runtime_pass` (no live pass, no two-client capture).
- New hypothesis id used in the scenario: **HYP-PF-019**. Ledger entry and any
  `docs/FUNCTIONAL_COVERAGE.json` edit are the chief's to make — this lane
  touched neither, and created no `.manifest`.
- Server-side channel tally moves from **1 of 17 touched / 0 of 17 decoded** to
  **5 of 17 addressable / 5 of 17 decoded and composable** (one shared schema).

## 7. How to reproduce

```
py -3 -m pytest tests/test_channel_message_hypothesis.py -q      # 34 passed
py -3 -m pytest tests/test_chat_input_echo.py -q                 # unchanged, still green
py -3 -m pytest tests/test_foundation_legacy_seam.py -q          # unchanged, still green
py -3 tools/pf_chat_channel_family_static.py                     # 69 static guards, exit 0 (prior lane)

py -3 -m pytest tests/test_presentation_ownership.py -q          # 1 EXPECTED failure, see section 5
```

The new test file is pure offline pytest: no network, no database, no
GameClient, no UI. It loads the frozen v141 module only for its
`make_runtime_vitals` envelope helper (source import; no server is started, no
socket opened) and reads two scenario JSON files.

**Files added (4, additive; no existing file modified):**

- `src/pirateforce_foundation/channel_message_hypothesis.py` (692 lines)
- `scenarios/channel_message_hypothesis_shared_serializer.json` (108 lines)
- `tests/test_channel_message_hypothesis.py` (628 lines, 34 tests)
- `reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md` (this file)

No commit, no canonical DB access, no GameClient launch, no network egress, no
`.manifest`.
