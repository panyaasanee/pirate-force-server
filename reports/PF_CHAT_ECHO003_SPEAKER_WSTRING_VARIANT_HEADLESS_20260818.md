# CHAT-ECHO-002 — speaker-name wstring variant of the chat echo, headless wire pass (HYP-PF-014 v2)

Date: 2026-08-18 · Implementation lane under the chief session · Trigger:
attended GT-009 client acceptance of the CHAT-ECHO-001 byte-exact echo
(rendered `[ทั่วไป] : <text>` with an *empty* speaker slot) plus the
CHAT-ECHO-002 research candidate 1
(`reports/PF_CHAT_ECHO002_SPEAKER_FIELD_RESEARCH_20260818.md`), processed
under the owner's standing pre-approval of 2026-08-17 18:2x.

## Primary claim (grade B, wire layer only)

Behind the new separate opt-in
`scenarios/chat_input_hypothesis_speaker_echo.json` (response_policy
`speaker_wstring_echo_no_write_no_close`, `production_allowed: false`), the
Foundation server answers the exact pinned 34-byte ASCII-12 chat input frame
(vital `0xAC52`, unchanged request classification from CHAT-ECHO-001) with
the **designed speaker-name wstring composition**: wstring#1 — empty in
every captured client request — is filled with the selected character's
canonical `characters.name` (UTF-16LE behind the same tag-`0x48` u32-length
convention the request itself uses, grade-A proven for
CreateActorDataEx/ActorAttr names), and everything from the second wstring
header on is echoed byte-exactly, inside the same accepted
`GSCN_RunTimeProtocolRes` v4 one-vital collection envelope GT-009 proved
deliverable. The composed PC is always **56 + 2×len(name)** bytes; a real
server process on a fresh migrated scratch DB completed the full wire entry
(login → create → select → runtime-ready) and echoed all three sends
byte-equal to the new pins over real TCP, repeatably, with no DB write, no
socket action, and an undisturbed heartbeat.

## Composition and new pins (name = `test01`, the canonical V25 create name)

Variant payload = `48 <u32 2×len(name)> <name UTF-16LE> 48 <u32 len(text)>
<text UTF-16LE>` (payload bytes 0–4 replaced; bytes 5.. echoed byte-exactly).
Probe1 variant payload hex (46 B):

```
48 0C000000 740065007300740030003100 48 18000000
500046004300480041005400500052004F00420045003100
```

| pin | size | sha256 |
|---|---|---|
| variant payload probe1 | 46 B | `D702CEE2B3BD83E7568EBAFC93B73D3B87D9AF643EE8155B36D827A6E24B4A02` |
| variant payload probe2 | 46 B | `A9060FC24E676B8BB5752814A6404E8F95FB9438B9EA755727E480699A046921` |
| response PC probe1 | 68 B | `5D80E83CE4C60A3927C9AFE020B0833358763BFE3CA1ECAB3EFB28E98BC9EE17` |
| response PC probe2 | 68 B | `8717FC3F5282269CF591FEFE24C2152E443C843A63B9927A0514D424D6EBA9F2` |
| response frame probe1 | 79 B | `AA27B015AB9EA30537331408D5F262BC37EA489A0DB8E7B3BC7D4A1896D99D23` |
| response frame probe2 | 79 B | `79ABB34925D20793A0AC718246ACC717D8ECF8F41FB9DCDC0BD482E23FFE1FFA` |

Measured correction to the naive frame arithmetic: the research formula
`pc = 56 + 2×len(name)` holds exactly (68 = 56 + 12), but the frame is
**79 B, not 78** — once the PC exceeds 60 bytes the snappy raw-literal
header takes a second tag byte, so the frame gains one byte over the +10 the
56/66 pair suggested. Request-side pins (34 B payload, 54 B pc) are the
CHAT-ECHO-001 values, unchanged; the plain echo scenario file is
byte-identical (sha `1350C98A..5ABB`, pinned in the tests).

## Implementation (opt-in, fail closed, no write, no close, not one-shot)

- `scenarios/chat_input_hypothesis_speaker_echo.json` — second entry in the
  exact allowlist; the `requests` block is deliberately byte-identical to
  the plain echo scenario (CHAT-ECHO-002 changes only the composition); any
  tampered field fails the whole lane closed.
- `src/pirateforce_foundation/chat_input_hypothesis.py` —
  `compose_chat_input_speaker_payload` (name fail-closed: only a non-empty
  `str` encoding to exactly two UTF-16LE bytes per character composes; no
  surrogates) and `make_chat_input_speaker_echo_response` (structural pins:
  PC size exactly 56 + 2×len(name), variant payload byte-exact at the fixed
  envelope offset, text tail byte-exact; both probe forms under `test01`
  hash-pinned end to end).
- `src/pirateforce_foundation/runtime.py` — the existing
  `_dispatch_chat_input_hypothesis` branches on the scenario id only after
  the unchanged classification/selected/runtime-ready guards; the variant
  emits event `chat_input_hypothesis_speaker_echo_ack_ascii12`, action
  `HYP_PF_014_CHAT_INPUT_SPEAKER_ECHO_ASCII12`; an uncomposable name appends
  `chat_input_hypothesis_speaker_name_unavailable_no_reply` and returns
  nothing. No store call, no socket action, no one-shot latch.
- `app.py` untouched: the existing `--chat-input-hypothesis-scenario` flag
  loads the new file through the same exact allowlist.

## Loopback unit layer (sandbox)

`tests/test_chat_input_echo.py` — 27 tests (15 CHAT-ECHO-001 tests unchanged
and green, 12 new): variant payload fixtures re-derived and hash-pinned;
both probes echo byte-exactly through the real dispatch path under the
speaker scenario (action + 68/79 sizes + pinned hashes + payload at
pc[20:66] + persisted name binding); three consecutive sends each echoed
(not one-shot); database bytes identical across the chat dispatches and the
lease stays open; SHORT (20 B) and TOOLONG (46 B) payloads silent; no
selected character silent; an empty selected name fails closed with the
named event and no write; the maker refuses empty/non-str/surrogate names
and non-conforming payloads while composing any accepted payload under any
two-byte name at exactly 56 + 2×len(name); the tampered speaker scenario
(production flag, id, extra/missing field, swapped response_policy, wrong
probe name, wrong sizes/hashes) never loads; the plain echo scenario file is
byte-identical to its CHAT-ECHO-001 pin and still produces the plain
composition (no cross-leak). Run: `python3 -m pytest
tests/test_chat_input_echo.py -q` → **27 passed** (the repo-wide
`test_hypothesis_ledger` sha pin is expectedly red until the chief re-pins
the amended ledger; not touched here).

## Headless runtime layer (sandbox, real server process, real TCP)

Run 2026-08-18 03:35 (Asia/Bangkok), probe
`reports/chat_echo002_smoke/pf_chat_echo002_speaker_probe_20260818.py`
(sockets + scratch DB only; never touches GameClient or the canonical DB):
fresh scratch DB created by the app's own migrations in `/tmp`, server
booted as a real process (`python3 -m pirateforce_foundation.app --db …
--chat-input-hypothesis-scenario scenarios/chat_input_hypothesis_speaker_echo.json`),
then one connection drove the full pinned wire entry: login_verify (2 reply
frames) → real captured V25 create PC (1 reply; persisted name `test01` ==
the pinned probe speaker name) → start_game selector 0 (2 replies) → exact
empty runtime req (runtime-ready ack; the ack frame is the same empty
RuntimeRes as the heartbeat, so 2 non-heartbeat replies = welcome + music).

- **send 1 (probe1)**: exactly one non-heartbeat frame — 79 B, sha
  `AA27B015..9D23` (pinned) — at **+50.7 ms**; no EOF.
- **send 2 (probe2)**: 79 B, sha `79ABB349..1FFA` (pinned), **+51.5 ms**;
  no EOF.
- **send 3 (probe1 repeated)**: echoed **again** byte-exactly (+51.0 ms) —
  the variant lane is not one-shot; no EOF.
- **SHORT negative** (the GT-009-observed 20-byte 5-character form): zero
  reply frames, no EOF — classification unchanged, fail closed.
- **DB unchanged across the whole chat window including SHORT**: scratch-DB
  sha256 `2D1B8009..2BB0` before send 1 == after the SHORT window
  (`db_unchanged_across_chat: true`).
- Heartbeat cadence undisturbed: 1–2 heartbeats inside every echo window
  and 3 heartbeats / 0 dispatch frames in the 4.5 s tail.
- Probe exit 0, `ok: true`. Canonical `state/pirateforce.sqlite3` verified
  untouched after the run (sha `B5557E9F..C9ED`, unchanged).

Evidence (hash-pinned in the manifest):
`reports/chat_echo002_smoke/CHAT_ECHO002_sandbox_smoke_20260818_033516_transcript.txt`
(driver say-lines + verdict JSON) and `…_probe.json` (machine-readable
verdict), plus the probe script itself.

## Nonclaims

1. **No client-observable claim**: whether the real client renders the
   filled wstring#1 as the speaker name in front of `[ทั่วไป]` (and with
   what spacing), or rejects/truncates/desyncs on the longer payload — that
   is exactly GT-012 in attended big round #3. A desync would falsify the
   wstring#1 reading and re-weight the research's competing u32-value
   reading of payload bytes 1–4.
2. No Thai or non-ASCII speaker name has ever been on the wire (the smoke
   name is the canonical ASCII `test01`); non-BMP names fail closed by
   design and are not claimed at all.
3. The channel-tag selection mechanism (vital id vs payload field) stays
   open; no semantic name is assigned to `0xAC52` or its prefix bytes.
4. No original-server response-policy claim — the corpus still has no chat
   wire from the original server in either direction (no golden).
5. All CHAT-ECHO-001 nonclaims stand: no channel/whisper/broadcast
   semantics, no delivery to other clients, no persistence, no message
   lengths other than 12 characters, no non-ASCII text, no production or
   default-mode behavior (`production_allowed` stays false; without the
   flag the frame remains counted-and-ignored exactly as GT-006 observed).
