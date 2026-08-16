# CHARACTER-NAME-002 — local-player world name runtime pass

Date: 2026-08-16
Result: Grade B controlled runtime pass

## Primary claim

The unchanged client consumed the CHARACTER-NAME-001 StartGame projection and
displayed persisted name `Arena01` above the selected local player in the Port
Royal world view. This closes only the local-player world-name projection.

## Exact retained evidence

Capture root:
`GameClient/capture_port_royal_fish_p60_ea7d_ack_20260816_115814`.

- The raw Game log records the 458-byte StartGame frame at
  `2026-08-16T11:59:57.891` with a 445-byte PC. At PC offset `0x20` is `0B04`;
  the ActorAttr ID begins at `0x22`, its version/tag is at `0x25`, and its
  identity qword begins at `0x28` with value `0x10010001`.
- BasicAttr mask is unchanged `0x070C`. ActorAttr low/high masks are exactly
  `0x01000800/0`; the mandatory bool is `1`, cash is `10000`, and the next field
  is tag `0x48`, byte length `14`, exact UTF-16LE `Arena01`.
- `GAME_LIVE.txt` records `RUNTIME_RES_ACK_FIRST_REQ` at
  `2026-08-16T12:00:44.897`, followed by continuing client requests/heartbeats:
  45 heartbeat responses were emitted and the final request was received at
  `12:01:26.850`. This label is the generic first-runtime-request acknowledgement,
  not the SCENE-007 ActionVital acknowledgement. The raw server log ends with
  `game client closed`.
- The Chief directly observed the `Arena01` label above the selected player in
  the Port Royal world view, separate from the target panel, and observed that
  the client remained responsive. The Chief initiated exit through the normal UI
  confirmation. The capture records peer closures but has no client exit-code
  sidecar, so it does not prove process exit code zero or a clean process exit.
  This UI fact is an operator observation: no screenshot was retained or tracked.
- The recorded server PID is `12908`; the Chief validated that exact PID before
  stopping it after the client closed. The PID file proves the recorded value,
  while validation/stopping are operator actions rather than packet evidence.
- Server stderr and both DB-guard monitor streams are empty. The after guard
  reports `PASS_UNCHANGED`; before and after main/WAL/SHM hashes are identical:
  main `E3F74B69D5467AE312B6818C6163F15922AE70B26AB6D547F21EA75F3C263862`,
  WAL `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`,
  SHM `FD4C9FDA9CD3F9AE7C962B0DDF37232294D55580E1AA165AA06129B8549389EB`.

The adjacent manifest fixes the exact path, byte count, and SHA-256 of all 11
retained artifacts used by this report.

The capture-root basename is inherited from the broader scenario launcher and is
misleading for this run: retained logs contain no P60 population, TargetVital,
EA7D request, or SCENE-007 ActionVital acknowledgement. None is claimed here.

## Evidence classification and ceiling

- Grade A static evidence remains CHARACTER-NAME-001: ActorAttr name mask
  `0x01000000`, wstring `+0x164`, and the exact `NameBoardPlayer` sink.
- Grade B runtime evidence here proves exact emitted StartGame bytes, client
  liveness, and the directly observed selected-local-player label.
- The UI observation has no screenshot artifact and is not represented as a raw
  log fact. The raw logs independently prove the wire and responsive traffic.

This result does not prove remote-player name projection, rename or uniqueness
policy, authenticated account ownership, name persistence across server-process
restart/crash, or any job/class/avatar-field semantics. It adds no packet or
gameplay hypothesis and does not change immutable V141.
