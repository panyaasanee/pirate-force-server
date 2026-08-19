# Pirate Force RE checkpoint — V132 Tab SELECT_TARGET negative boundary

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V132 derives from the passing V131 state but deliberately does not schedule
the Port Royal docking prompt or q3020 UI. It restores the V127/V128-proven
P30+100X local observation point and retains the exact isolated P0/P30/P91
population. P30/template 31 Tornado Eagle, identity `0x201F`, is the nearest
isolated usage-1 actor.

The focused hypothesis was data-backed: HOTKEY row 9 is `SELECT_TARGET`, its
physical key is KEY_TIP row 9 / Tab, and HOTKEY_TIP row 9 is
`เลือกศัตรูที่อยู่ใกล้ๆ`. Dispatcher `0x450B20` routes normalized hotkey ID 9
through `0x451032` into its local event fanout. V132 armed a capture-only
marker after the authoritative population reapply and recorded any following
structurally valid TargetVital without replying or mutating state.

The clean runtime is a negative boundary. With no prior mouse target, the user
pressed Tab exactly once after the arm marker. The client emitted zero
TargetVital and did not reach the positive P30 identity/kind oracle. The
session remained healthy for 88 heartbeats and closed without errors.

## Exact runtime result

The only pre-arm non-empty runtime action relevant to population setup was a
normal `TargetPosVital` at frame 40. It came from the controlled movement used
to trigger the local population and is not a mouse-selected actor target.

The exact population reapply completed at `01:35:19.312`. The server armed the
probe at `2026-08-15T01:35:19.323` and wrote:

`V132_SELECT_TARGET_HOTKEY9_TAB_PROBE_ARMED_AFTER_POPULATION_REAPPLY`

The recorded precondition was `no_prior_mouse_target`; the positive oracle
was actor identity `0x201F`, kind 2, with collection count observed rather than
predicted. No response or combat claim was attached.

After one Tab press:

- `TargetVital`: zero in the raw GAME log;
- `TargetVital`: zero in the live sidecar;
- positive V132 target marker: zero;
- event journal entries after the arm marker: zero;
- no alternate non-empty selection request was identified.

The final successful heartbeat was sequence 88 at `01:37:24.741`, exactly
125.418 seconds after the arm timestamp. Heartbeats 26 through 88 provide 63
successful post-arm heartbeats. The final received runtime request before that
was the normal empty RuntimeReq frame 105 at `01:37:22.888`; the earlier
frame-93 `UserSetting_UpdateServerSettingVital` was normal closure-time state.

Across all six flushed capture files there are zero matches for `ErrorData`,
VitalData version mismatch, read failure, fatal, exception, traceback,
disconnect, `28317`, or `SEND_FAILED`. Server stderr is empty.

## What the negative proves

Under this exact tested state—no prior mouse target, P30+100X local position,
authoritative isolated P0/P30/P91 population already reapplied, and one Tab
press—HOTKEY 9 did not emit TargetVital and did not select P30 on the server
wire.

This does not disprove the data labels or dispatcher path. It does not prove
that Tab can never select an actor under a different client-local state, target
class, range, UI focus, or selection list. None of those possible gates is
proven by this run, so do not guess one and do not modify actor fields merely
to force a request. A next target-selection experiment requires a separately
recovered exact gate or a controlled comparison with an already-proven client
selection state.

V132 is a negative evidence checkpoint only. Keep V131 as the current passing
baseline and do not promote V132.

## Build and artifact verification

After clean runtime closure, V132 passed `py_compile` and the complete inherited
self-test. The ZIP opens successfully, contains exactly three entries, and
each entry is byte-identical to its current/deployed artifact:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v132.py`, 298,084 bytes  
  `42A68173A7DFF784594478E5BC27B737E79CFDB42B5BE14A3678F43D6B2FA48A`
- `run_v132_port_royal_tab_nearby_enemy_probe.bat`, 480 bytes  
  `B6D9595B4B5B8C2A282462B33AE1AC34D2665472FC5C346711B0F2D5CDD34916`

Exact-three-file package SHA-256:

`0E5E3AAD9171F98FCF6B9AFA8DDC0EC36BCF1088CE81D7748CB7629E6C50B2BC`

Flushed capture hashes:

- raw GAME: `5563AB3D58279C07A77700E0138B6C1468EEA25D7F795D3145FDABAC99618136`
- event journal: `5908BC9BAAE56897F803F31764EBEB2993E3F76B73A64B7F1747653CF0677523`
- live GAME: `92FE2E9CE058B12ACFFEEA07A3D8BB0950246FB2D9DD85046FA2B82082999EFD`
- raw LOGIN: `891BC9CBBACDCE1FAE54ABA61B8B7799AD6340FA0F16D894479F6B04DAC74551`
- server console: `E10771AA4238B5DD6ED7FAB5BC87A090C40C32E939D3D6D2070E4EEB2F6C578D`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified negative checkpoint backup:

`backups/v132_tab_select_target_negative_20260815_014135/`

Its manifest covers the six flushed capture artifacts plus source, launcher,
and package: nine entries with zero mismatches. The final report,
`handoff.txt`, and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`568B2D7E4B1D3F0A2EC33BFF408745FB58037266C9258CD564AF41E9F1F30CD0`
