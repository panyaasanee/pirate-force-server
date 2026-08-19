#!/usr/bin/env python3
"""DAMAGE-DISPATCH-001: headless wire proof for the HYP-PF-024 hit sweep.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in scenario
``scenarios/damage_model_hypothesis_hit_sweep.json`` and a THROWAWAY database,
answers ONE accepted client frame with FOUR ``GSCN_RunTimeProtocolRes`` id
``0x6E9D`` version 4 frames, each carrying one ``CHitResult`` ``0x16F7``
version 0 element inside the VitalData collection (BASE change mask 2, the
collection at object ``+0x18``; DERIVED change mask 0), and that those frames
are

  (a) **byte-for-byte** the frames ``build_damage_model_sweep`` composes for
      the SAME session actor -- same labels, same PCs, same framed bytes, same
      delays, compared with ``==`` on the bytes objects, not by hash summary
      alone; and
  (b) independently readable, by a tag walker written in THIS file that does
      not import the encoder's decoder, as the four-step sweep the round-90
      static RE and the encoder pins agree on:

        HIT_WEAK      damage -63   flags 0x0001   delay 0.0
        HIT_STRONG    damage -379  flags 0x0001   delay 6.0
        MISS          damage    0  flags 0x0000   delay 6.0   <- the control
        HIT_REACTION  damage  -63  flags 0x0009   delay 6.0

      with the damage field read SIGNED off the ``u32`` tag ``0x14`` at hit
      entry ``+0x08``, which is the only reading the client's four ``cmp/jge``
      sites make sense under; and

  (c) addressed to the SESSION's own selected character: the qword performer at
      header ``+0x18`` and the qword target at entry ``+0x00`` are equal to each
      other, equal across all four frames, and equal to the identity the
      dispatcher's own ``foundation.selected`` carries.  A sweep composed here
      against a DIFFERENT identity does NOT equal the dispatched bytes, which is
      what makes that a claim about the session rather than about a constant.

      Note, because it would otherwise look like a coincidence: in this harness
      the selected character's identity IS ``0x10010001``, the fixed probe
      identity the module's pins were composed from, because that is what the
      frozen V25 create wire commits.  That is exactly why the live sweep can be
      held to the pinned ``sha256`` values at all.  It does not make the guard
      circular -- the identity is read out of the dispatcher's session object,
      not assumed.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of this profile.**  That is the attended lane, not run here.
It does not prove that the number renders (0x750D45 reads a singleton this
project cannot read statically), it claims nothing about the meaning of any
individual flag bit, nothing about what a non-negative value at ``+0x08``
means, nothing about the original server's damage formula -- the formula here
is this project's own -- and nothing about hit points: this lane opens no write
path to HP at all.  ``production_allowed`` is False everywhere it appears.

WHAT GUARD 7 ("no database write") ACTUALLY MEASURES -- read this before quoting it
----------------------------------------------------------------------------------
The store runs SQLite in WAL mode, so hashing only the main ``.sqlite3`` file
would be a weak claim: a committed write can land in the ``-wal`` sidecar and
leave the main file byte-identical.  This tool therefore does NOT claim "the
lane cannot write".  It measures two narrower, checkable things:

  * every file in the throwaway database directory -- the ``.sqlite3`` file AND
    any ``-wal`` / ``-shm`` sidecar, by name, size and sha256 -- is identical
    immediately before and immediately after the sweep dispatch; and
  * the logical content of the database, taken as a full ``iterdump`` over a
    read-only connection, is identical before and after.

That is a statement about this one dispatch on this one temporary database.  It
is evidence for, not proof of, the absence of a write path.  The static claim
"the lane touches no store" belongs to a reading of the code, not to this file.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.  The
canonical database is never opened, never named and never reachable from any
path this file builds: everything runs on a fresh temporary SQLite file that is
deleted on exit.  While the sweep runs, ``socket.socket`` and its neighbours are
replaced with objects that record and refuse, so "no socket" is a measurement
here and not an assurance.  No repository file is written unless
``--evidence <path>`` is handed in.  Pure stdlib.

Usage:
    py -3 tools/pf_damage_model_headless_replay.py
    py -3 tools/pf_damage_model_headless_replay.py --json
    py -3 tools/pf_damage_model_headless_replay.py --profile hit_sweep
    py -3 tools/pf_damage_model_headless_replay.py \
        --evidence reports/damage_dispatch001_headless.json

Every byte this file prints is ASCII: it is expected to run on a Windows
console under code page 874, where one non-ASCII character is a crash.

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the list.
Exit 2 = the command line named a profile this tool does not have.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import damage_model_hypothesis as dmh  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
SCENARIO_BY_PROFILE = {"hit_sweep": SCENARIO}
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SWEEP_EVENT = "damage_model_hypothesis_hit_sweep_sent"
REPEAT_EVENT = "damage_model_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "damage_model_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "damage_model_hypothesis_wrong_sequence_no_reply"
WRONG_TEXT_EVENT = "damage_model_hypothesis_wrong_text_no_reply"
WRONG_ENVELOPE_EVENT = "damage_model_hypothesis_wrong_envelope_no_reply"
EVENT_PREFIX = "damage_model_hypothesis_"


# ---------------------------------------------------------------------------
# An INDEPENDENT reader.  It deliberately does not import
# decode_chit_result_frame: the point of this file is to check the dispatcher's
# bytes with a second pair of eyes.  Every constant below is written out here
# rather than imported, and cross-checked against the module's own constant in
# section 0 so the two cannot drift apart in silence.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
BASE_CHANGE_MASK_VITAL_COLLECTION = 0x02   # the collection at this+0x18
DERIVED_CHANGE_MASK_ABSENT = 0x00
CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0x00           # ctor 0x74F940 stores 0 at 0x74F979

TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32
TAG_ENVELOPE_VERSION = 0x08

CHIT_RESULT_HEADER_WIRE_SIZE = 22          # 9 + 3 + 3 + 5 + 2
HIT_ELEMENT_WIRE_SIZE = 37                 # 9 + 5 + 15 + 5 + 3
HIT_ENTRY_COUNT = 1
HEADER_RESERVED_VALUE = 0
YAW_PINNED = 0.0

EXPECTED_PC_SIZE = 84
EXPECTED_FRAME_SIZE = 95
EXPECTED_STEP_ORDER = ("HIT_WEAK", "HIT_STRONG", "MISS", "HIT_REACTION")
EXPECTED_LABEL_PREFIX = "HYP_PF_024_DAMAGE_MODEL_"
EXPECTED_DELAYS = (0.0, 6.0, 6.0, 6.0)
EXPECTED_DAMAGE = {
    "HIT_WEAK": -63, "HIT_STRONG": -379, "MISS": 0, "HIT_REACTION": -63,
}
EXPECTED_FLAGS = {
    "HIT_WEAK": 0x0001, "HIT_STRONG": 0x0001, "MISS": 0x0000,
    "HIT_REACTION": 0x0009,
}


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _tagged(pc: bytes, cursor: int, tag: int, width: int, label: str):
    if cursor + 1 + width > len(pc):
        raise WalkError("%s: truncated at %d" % (label, cursor))
    if pc[cursor] != tag:
        raise WalkError(
            "%s: tag 0x%02X != expected 0x%02X at %d"
            % (label, pc[cursor], tag, cursor)
        )
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def walk_chit_result_frame(pc: bytes) -> dict:
    """Read one GSCN_RunTimeProtocolRes CHitResult PC by hand, end to end.

    Strict: every tag byte is compared, every width is fixed, and the walk must
    land exactly on ``len(pc)``.  The damage field is read with ``<i``, signed,
    which is the whole point of the lane.
    """
    if type(pc) is not bytes:
        raise WalkError("the pc is not bytes")
    cursor = 0
    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "envelope id")
    envelope_id = struct.unpack("<H", raw)[0]
    if envelope_id != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    raw, cursor = _tagged(pc, cursor, TAG_U32, 4, "envelope error data")
    error_data = struct.unpack("<I", raw)[0]
    raw, cursor = _tagged(
        pc, cursor, TAG_ENVELOPE_VERSION, 1, "envelope version")
    envelope_version = raw[0]
    raw, cursor = _tagged(pc, cursor, TAG_U8, 1, "base change mask")
    base_mask = raw[0]
    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "vital count")
    vital_count = struct.unpack("<H", raw)[0]
    if vital_count != 1:
        raise WalkError("expected exactly one vital, found %d" % vital_count)
    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "vital id")
    vital_id = struct.unpack("<H", raw)[0]
    raw, cursor = _tagged(pc, cursor, TAG_U8, 1, "vital version")
    vital_version = raw[0]
    if vital_id != CHIT_RESULT_VITAL_ID:
        raise WalkError("the vital is not CHitResult 0x16F7")

    body_at = cursor
    raw, cursor = _tagged(pc, cursor, TAG_QWORD, 8, "performer")
    performer = struct.unpack("<Q", raw)[0]
    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "header field 2 (+0x20)")
    field2 = struct.unpack("<H", raw)[0]
    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "header field 3 (+0x22)")
    field3 = struct.unpack("<H", raw)[0]
    raw, cursor = _tagged(pc, cursor, TAG_U32, 4, "header field 4 (+0x24)")
    field4 = struct.unpack("<I", raw)[0]
    raw, cursor = _tagged(pc, cursor, TAG_U8, 1, "header field 5 (+0x28)")
    field5 = raw[0]
    header_wire_size = cursor - body_at

    raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "hit entry count")
    entry_count = struct.unpack("<H", raw)[0]
    entries = []
    for index in range(entry_count):
        entry_at = cursor
        raw, cursor = _tagged(pc, cursor, TAG_QWORD, 8, "entry target")
        target = struct.unpack("<Q", raw)[0]
        raw, cursor = _tagged(pc, cursor, TAG_U32, 4, "entry damage")
        # SIGNED.  The tag is the u32 tag 0x14, but 0x750919 and 0x750D45
        # compare the field with jge, so an unsigned reading is the wrong one.
        damage_signed = struct.unpack("<i", raw)[0]
        damage_unsigned = struct.unpack("<I", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = _tagged(
                pc, cursor, TAG_F32, 4, "entry position %s" % axis)
            position.append(struct.unpack("<f", raw)[0])
        raw, cursor = _tagged(pc, cursor, TAG_F32, 4, "entry yaw")
        yaw = struct.unpack("<f", raw)[0]
        raw, cursor = _tagged(pc, cursor, TAG_U16, 2, "entry flags")
        flags = struct.unpack("<H", raw)[0]
        entries.append({
            "index": index,
            "target_identity": target,
            "damage_signed": damage_signed,
            "damage_unsigned": damage_unsigned,
            "position": tuple(position),
            "yaw": yaw,
            "flags": flags,
            "wire_size": cursor - entry_at,
        })

    raw, cursor = _tagged(pc, cursor, TAG_U8, 1, "derived change mask")
    derived_mask = raw[0]
    if cursor != len(pc):
        raise WalkError(
            "the reader accounted for %d of %d bytes" % (cursor, len(pc))
        )
    return {
        "envelope_id": envelope_id,
        "error_data": error_data,
        "envelope_version": envelope_version,
        "base_change_mask": base_mask,
        "derived_change_mask": derived_mask,
        "vital_count": vital_count,
        "vital_id": vital_id,
        "vital_version": vital_version,
        "performer_identity": performer,
        "header_field2": field2,
        "header_field3": field3,
        "header_field4": field4,
        "header_field5": field5,
        "header_wire_size": header_wire_size,
        "entry_count": entry_count,
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Containment helpers.
# ---------------------------------------------------------------------------
class SocketOpened(RuntimeError):
    """Something tried to open a socket while the sweep was running."""


class _SocketTrap:
    """Records every attempt to build a socket, and refuses all of them."""

    def __init__(self):
        self.attempts: list[str] = []
        self._saved: dict[str, object] = {}

    def _refuse(self, name):
        def _call(*_args, **_kwargs):
            self.attempts.append(name)
            raise SocketOpened(
                "the HYP-PF-024 headless replay opens no socket (%s)" % name
            )
        return _call

    def __enter__(self):
        for name in (
            "socket", "socketpair", "create_connection", "create_server",
        ):
            if hasattr(socket, name):
                self._saved[name] = getattr(socket, name)
                setattr(socket, name, self._refuse("socket." + name))
        return self

    def __exit__(self, *_exc):
        for name, original in self._saved.items():
            setattr(socket, name, original)
        return False


def directory_digest(folder: Path) -> list[tuple[str, int, str]]:
    """Name, size and sha256 of every file in a folder, sorted.

    The store runs in WAL mode, so the ``-wal`` and ``-shm`` sidecars are part
    of the database state and hashing the main file alone would understate it.
    """
    rows = []
    for entry in sorted(os.listdir(folder)):
        path = folder / entry
        if not path.is_file():
            continue
        data = path.read_bytes()
        rows.append(
            (entry, len(data), hashlib.sha256(data).hexdigest().upper())
        )
    return rows


def logical_dump(store: SQLiteStore) -> str:
    """The whole database as SQL text, over a read-only connection."""
    with store.connect_read_only() as db:
        return "\n".join(db.iterdump())


def main() -> int:
    want_json = "--json" in sys.argv
    evidence_path = None
    if "--evidence" in sys.argv:
        evidence_path = Path(sys.argv[sys.argv.index("--evidence") + 1])
    profile_name = "hit_sweep"
    if "--profile" in sys.argv:
        profile_name = sys.argv[sys.argv.index("--profile") + 1]
    if profile_name not in SCENARIO_BY_PROFILE:
        print("unknown profile %r; pick one of %s"
              % (profile_name, sorted(SCENARIO_BY_PROFILE)))
        return 2
    scenario_path = SCENARIO_BY_PROFILE[profile_name]

    failures: list[str] = []
    notes: list[str] = []
    guards = 0

    def check(label, condition, detail=""):
        nonlocal guards
        guards += 1
        if condition:
            if not want_json:
                print("  PASS  %s" % label)
        else:
            failures.append(label)
            if not want_json:
                print("  FAIL  %s %s" % (label, detail))

    legacy = load_legacy(LEGACY_PATH)
    scenario = dmh.load_damage_model_hypothesis_scenario(scenario_path)
    pinned = json.loads(scenario_path.read_text(encoding="utf-8"))
    unlock = dmh.damage_model_wire_unlock(scenario)

    # -------------------------------------------------------------------
    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("envelope id 0x6E9D agrees with the module",
          RUNTIME_PROTOCOL_RES_ID == dmh.RUNTIME_PROTOCOL_RES_ID)
    check("envelope version 4 agrees with the module",
          RUNTIME_PROTOCOL_RES_VERSION == dmh.RUNTIME_PROTOCOL_RES_VERSION)
    check("BASE change mask 2 (VitalData at +0x18) agrees with the module",
          BASE_CHANGE_MASK_VITAL_COLLECTION
          == dmh.BASE_CHANGE_MASK_VITAL_COLLECTION == 2)
    check("DERIVED change mask 0 agrees with the module",
          DERIVED_CHANGE_MASK_ABSENT == dmh.DERIVED_CHANGE_MASK_ABSENT == 0)
    check("CHitResult 0x16F7 version 0 agrees with the module",
          CHIT_RESULT_VITAL_ID == dmh.CHIT_RESULT_VITAL_ID
          and CHIT_RESULT_VITAL_VERSION == dmh.CHIT_RESULT_VITAL_VERSION)
    check("the 22-byte header and 37-byte entry agree with the module",
          CHIT_RESULT_HEADER_WIRE_SIZE == dmh.CHIT_RESULT_HEADER_WIRE_SIZE
          and HIT_ELEMENT_WIRE_SIZE == dmh.HIT_ELEMENT_WIRE_SIZE)
    check("the step order and label prefix agree with the module",
          EXPECTED_STEP_ORDER == dmh.DAMAGE_MODEL_STEP_ORDER
          and EXPECTED_LABEL_PREFIX == dmh.DAMAGE_MODEL_ACTION_LABEL_PREFIX)
    check("the scenario profile carries the module's step plan",
          scenario.step_order == EXPECTED_STEP_ORDER
          and scenario.action_label_prefix == EXPECTED_LABEL_PREFIX
          and scenario.first_delay_seconds == EXPECTED_DELAYS[0]
          and scenario.spacing_seconds == EXPECTED_DELAYS[1])
    check("the lane is not production-allowed",
          dmh.production_allowed is False)
    check("the scenario file is the opt-in HYP-PF-024 file",
          pinned["hypothesis_id"] == dmh.DAMAGE_MODEL_HYPOTHESIS_ID
          == "HYP-PF-024"
          and pinned["test_only"] is True
          and pinned["production_allowed"] is False)

    # The module's own PC-offset documentation block is known-wrong and known-
    # dead (nothing reads it).  It is reported, never repaired here: this tool
    # may not edit src/.
    module_offsets = (
        dmh.BASE_CHANGE_MASK_OFFSET, dmh.VITAL_COUNT_TAG_OFFSET,
        dmh.VITAL_COUNT_OFFSET, dmh.VITAL_ID_TAG_OFFSET, dmh.VITAL_ID_OFFSET,
        dmh.VITAL_VERSION_TAG_OFFSET, dmh.VITAL_VERSION_OFFSET,
        dmh.CHIT_RESULT_PAYLOAD_OFFSET,
    )
    real_offsets = (11, 12, 13, 15, 16, 18, 19, 20)
    if module_offsets != real_offsets:
        notes.append(
            "REPORT ONLY (not repaired here, src/ is out of scope for this "
            "tool): the eight PC-offset constants BASE_CHANGE_MASK_OFFSET.."
            "CHIT_RESULT_PAYLOAD_OFFSET in damage_model_hypothesis.py are each "
            "one less than the composed byte position (module=%s real=%s).  "
            "No code path reads them, so no composed byte is affected."
            % (module_offsets, real_offsets)
        )

    rows: list[dict] = []
    actions: list = []
    trap = _SocketTrap()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        db_path = tmp_dir / "damage_dispatch001.sqlite3"
        store = SQLiteStore(db_path, ROOT / "migrations")
        store.migrate()
        projector = LegacyProjector(legacy)
        lifecycle = CharacterLifecycle(
            store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )

        def boot(token, *, enabled=True, select=True, ready=True):
            state_type = make_state_class(
                legacy, lifecycle, projector,
                damage_model_hypothesis_scenario=(
                    scenario if enabled else None
                ),
            )
            state = state_type(token)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc()
            ))
            created = state.dispatch(
                legacy.parse_outer(legacy._V25_REAL_CREATE_PC)
            )
            assert created and created[0][0] == "FOUNDATION_CREATE_COMMITTED"
            if select:
                characters = store.list_characters(state.foundation.account_id)
                selected = state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(characters[-1].selector)
                ))
                assert selected and (
                    selected[0][0] == "FOUNDATION_SELECTED_START_GAME"
                )
            state.runtime_ack_sent = ready
            return state

        def trigger(probe="probe1"):
            return legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 1. one accepted client frame in, four frames out --")
        state = boot("damage_dispatch001")
        check("the harness brought a character to selected + runtime ready",
              state.foundation.selected is not None
              and state.teleport_sent is True
              and state.runtime_ack_sent is True)

        selected = state.foundation.selected
        session_identity = (
            ((selected.identity_hi & 0xFFFFFFFF) << 32)
            | (selected.identity_lo & 0xFFFFFFFF)
        )

        # The encoder's own composition, built OUTSIDE the dispatcher against
        # the SAME session actor.  This is the expectation every dispatched
        # byte is measured against.
        session_actor = dmh.resolve_actor(legacy, selected)
        expected = dmh.build_damage_model_sweep(
            legacy, session_actor, unlock, scenario,
        )
        # And a second composition against a DIFFERENT identity, so that
        # "the frames name the session" is a falsifiable statement.
        other_actor = dmh.DamageModelActor(
            (selected.identity_lo ^ 0x00ABCDEF) & 0xFFFFFFFF, 0,
            float(legacy.V135_PLAYER_X), float(legacy.V135_PLAYER_Y),
            float(legacy.V135_PLAYER_Z),
        )
        other_sweep = dmh.build_damage_model_sweep(
            legacy, other_actor, unlock, scenario,
        )

        dump_before = logical_dump(store)
        dir_before = directory_digest(tmp_dir)

        with trap:
            actions = state.dispatch(trigger())

        dir_after = directory_digest(tmp_dir)
        dump_after = logical_dump(store)

        check("the dispatcher answered with four frames",
              len(actions) == len(EXPECTED_STEP_ORDER), str(len(actions)))
        check("in the scenario's pinned order",
              [row[0] for row in actions]
              == [EXPECTED_LABEL_PREFIX + step
                  for step in EXPECTED_STEP_ORDER],
              str([row[0] for row in actions]))
        check("and named the sweep event exactly once",
              state.events.count(SWEEP_EVENT) == 1)
        check("the dispatched labels equal the module's action labels",
              [row[0] for row in actions]
              == list(dmh.DAMAGE_MODEL_ACTION_LABELS))
        check("the dispatched labels equal the scenario file's action labels",
              [row[0] for row in actions]
              == list(pinned["dispatch"]["action_labels"]))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 2. the dispatcher's bytes ARE the encoder's bytes --")
        # The load-bearing comparison of this file: if the dispatcher ever
        # composes a sweep of its own, invents a delay, or reorders one step,
        # these guards go red on the raw bytes.
        check("the dispatcher emitted exactly as many actions as the encoder",
              len(actions) == len(expected))
        check("every dispatched action equals the encoder's, byte for byte",
              actions == expected)
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if index >= len(actions) or index >= len(expected):
                continue
            got, want = actions[index], expected[index]
            check("step %s: the label is identical" % step, got[0] == want[0])
            check("step %s: the PC bytes are identical" % step,
                  got[1] == want[1])
            check("step %s: the framed bytes are identical" % step,
                  got[2] == want[2])
            check("step %s: the delay is identical" % step, got[3] == want[3])
            check("step %s: frame == frame_pc(pc) on the dispatched PC" % step,
                  got[2] == legacy.frame_pc(got[1]))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 3. every dispatched frame, read by an independent "
                  "walker --")
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = EXPECTED_STEP_ORDER[index]
            pin = dmh.DAMAGE_MODEL_PINS[step]
            scenario_pin = pinned["target"]["per_step"][step]
            parsed = legacy.parse_outer(pc)
            check("frame %s parses with the frozen v141 outer parser" % step,
                  parsed is not None)
            read = walk_chit_result_frame(pc)
            entry = read["entries"][0]
            check("frame %s is envelope 0x6E9D version 4" % step,
                  read["envelope_id"] == RUNTIME_PROTOCOL_RES_ID
                  and read["envelope_version"] == RUNTIME_PROTOCOL_RES_VERSION)
            check("frame %s carries BASE change mask 2 and DERIVED 0" % step,
                  read["base_change_mask"] == BASE_CHANGE_MASK_VITAL_COLLECTION
                  and read["derived_change_mask"] == DERIVED_CHANGE_MASK_ABSENT,
                  "base=0x%02X derived=0x%02X"
                  % (read["base_change_mask"], read["derived_change_mask"]))
            check("frame %s carries exactly one CHitResult 0x16F7 version 0"
                  % step,
                  read["vital_count"] == 1
                  and read["vital_id"] == CHIT_RESULT_VITAL_ID
                  and read["vital_version"] == CHIT_RESULT_VITAL_VERSION)
            check("frame %s carries a 22-byte header whose four unknown "
                  "fields are all zero" % step,
                  read["header_wire_size"] == CHIT_RESULT_HEADER_WIRE_SIZE
                  and read["header_field2"] == HEADER_RESERVED_VALUE
                  and read["header_field3"] == HEADER_RESERVED_VALUE
                  and read["header_field4"] == HEADER_RESERVED_VALUE
                  and read["header_field5"] == HEADER_RESERVED_VALUE)
            check("frame %s carries exactly one 37-byte hit entry" % step,
                  read["entry_count"] == HIT_ENTRY_COUNT
                  and entry["wire_size"] == HIT_ELEMENT_WIRE_SIZE)
            check("frame %s: damage read SIGNED off tag 0x14 is %d"
                  % (step, EXPECTED_DAMAGE[step]),
                  entry["damage_signed"] == EXPECTED_DAMAGE[step],
                  str(entry["damage_signed"]))
            check("frame %s: the unsigned reading of the same four bytes is "
                  "the two's complement, so the SIGNED reading is a choice "
                  "this file makes deliberately" % step,
                  entry["damage_unsigned"]
                  == (EXPECTED_DAMAGE[step] & 0xFFFFFFFF))
            check("frame %s: flags are 0x%04X"
                  % (step, EXPECTED_FLAGS[step]),
                  entry["flags"] == EXPECTED_FLAGS[step],
                  "0x%04X" % entry["flags"])
            check("frame %s: damage and flags tell the same story" % step,
                  (entry["damage_signed"] == 0)
                  == (entry["flags"] & 0x0001 == 0))
            check("frame %s: the yaw is the pinned 0.0f" % step,
                  entry["yaw"] == YAW_PINNED
                  and struct.pack("<f", entry["yaw"]) == b"\x00\x00\x00\x00")
            check("frame %s: the position is the frozen V135 player spawn"
                  % step,
                  all(
                      struct.pack("<f", got) == struct.pack("<f", float(want))
                      for got, want in zip(
                          entry["position"],
                          (legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                           legacy.V135_PLAYER_Z),
                      )
                  ),
                  str(entry["position"]))
            check("frame %s: the delay is the pinned %.1f s"
                  % (step, EXPECTED_DELAYS[index]),
                  delay == EXPECTED_DELAYS[index], str(delay))
            check("frame %s: the label is the pinned label" % step,
                  label == EXPECTED_LABEL_PREFIX + step)
            check("frame %s reproduces its MODULE byte pins" % step,
                  len(pc) == pin["pc_size"] == EXPECTED_PC_SIZE
                  and len(frame) == pin["frame_size"] == EXPECTED_FRAME_SIZE
                  and hashlib.sha256(pc).hexdigest().upper()
                  == pin["pc_sha256"]
                  and hashlib.sha256(frame).hexdigest().upper()
                  == pin["frame_sha256"],
                  hashlib.sha256(pc).hexdigest().upper())
            check("frame %s reproduces its SCENARIO FILE byte pins" % step,
                  scenario_pin["pc_size"] == len(pc)
                  and scenario_pin["frame_size"] == len(frame)
                  and scenario_pin["pc_sha256"]
                  == hashlib.sha256(pc).hexdigest().upper()
                  and scenario_pin["frame_sha256"]
                  == hashlib.sha256(frame).hexdigest().upper())
            check("frame %s: the module pin and the scenario pin are the SAME "
                  "pin" % step,
                  scenario_pin["pc_sha256"] == pin["pc_sha256"]
                  and scenario_pin["frame_sha256"] == pin["frame_sha256"]
                  and scenario_pin["damage_wire"] == pin["damage_wire"]
                  == EXPECTED_DAMAGE[step]
                  and scenario_pin["flags"] == pin["flags"]
                  == EXPECTED_FLAGS[step])
            rows.append({
                "index": index,
                "step": step,
                "action_label": label,
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "envelope_id": read["envelope_id"],
                "envelope_version": read["envelope_version"],
                "base_change_mask": read["base_change_mask"],
                "derived_change_mask": read["derived_change_mask"],
                "vital_id": read["vital_id"],
                "vital_version": read["vital_version"],
                "performer_identity": read["performer_identity"],
                "target_identity": entry["target_identity"],
                "damage_signed": entry["damage_signed"],
                "damage_unsigned": entry["damage_unsigned"],
                "flags": entry["flags"],
                "yaw": entry["yaw"],
                "position": list(entry["position"]),
                "header_wire_size": read["header_wire_size"],
                "entry_wire_size": entry["wire_size"],
                "pc_hex": pc.hex(),
            })

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 4. the frames name the SESSION's own actor --")
        check("performer == target on every frame",
              all(row["performer_identity"] == row["target_identity"]
                  for row in rows))
        check("all four frames name ONE identity",
              len({row["performer_identity"] for row in rows}) == 1,
              str([hex(row["performer_identity"]) for row in rows]))
        check("that identity is the dispatcher's selected character 0x%X"
              % session_identity,
              rows[0]["performer_identity"] == session_identity,
              hex(rows[0]["performer_identity"]))
        check("a sweep composed against a DIFFERENT identity does NOT equal "
              "the dispatched bytes",
              [row[1] for row in other_sweep] != [row[1] for row in actions])
        check("the four steps read the same damage the module's formula "
              "produces, step by step",
              [row["damage_signed"] for row in rows]
              == [dmh.step_damage_wire(i)
                  for i in range(len(EXPECTED_STEP_ORDER))])
        check("exactly one frame is the MISS control (damage 0, flags 0)",
              [row["step"] for row in rows
               if row["damage_signed"] == 0 and row["flags"] == 0]
              == list(dmh.DAMAGE_MODEL_MISS_STEP_LABELS))
        check("the spacing is the scenario's spacing",
              [row["delay_seconds"] for row in rows]
              == [scenario.first_delay_seconds]
              + [scenario.spacing_seconds] * (len(rows) - 1))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 5. one-shot --")
        seen_pcs = {row[1] for row in actions}
        again = state.dispatch(trigger())
        again2 = state.dispatch(trigger("probe2"))
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [] and again2 == [])
        check("and says so with the named already-sent event, once per try",
              state.events.count(REPEAT_EVENT) == 2)
        check("the repeat put no new byte on the wire",
              not ({row[1] for row in again} | {row[1] for row in again2})
              - seen_pcs)
        check("the sweep counter stayed at one",
              state.damage_model_sweep_count == 1)

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 6. every refusal, and none of them emits a byte --")
        refusals = []

        no_select = boot("dm_no_select", select=False)
        out = no_select.dispatch(trigger())
        check("no selected character: no bytes",
              out == [] and no_select.damage_model_sweep_count == 0)
        check("no selected character: the named event, exactly",
              no_select.events.count(NO_SELECTED_EVENT) == 1
              and SWEEP_EVENT not in no_select.events)
        refusals.append({"case": "no_selected_character",
                         "event": NO_SELECTED_EVENT, "actions": len(out)})

        not_ready = boot("dm_not_ready", ready=False)
        out = not_ready.dispatch(trigger())
        check("not yet teleport + runtime ack: no bytes",
              out == [] and not_ready.damage_model_sweep_count == 0)
        check("not yet teleport + runtime ack: the named event, exactly",
              not_ready.events.count(WRONG_SEQUENCE_EVENT) == 1
              and SWEEP_EVENT not in not_ready.events)
        refusals.append({"case": "not_runtime_ready",
                         "event": WRONG_SEQUENCE_EVENT, "actions": len(out)})

        bad_text = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        bad_text[-1] ^= 0xFF
        wrong_text = boot("dm_wrong_text")
        out = wrong_text.dispatch(legacy.parse_outer(bytes(bad_text)))
        check("a frame that is not ascii12: no bytes",
              out == [] and wrong_text.damage_model_sweep_count == 0)
        check("a frame that is not ascii12: the named event, exactly",
              wrong_text.events.count(WRONG_TEXT_EVENT) == 1
              and SWEEP_EVENT not in wrong_text.events)
        refusals.append({"case": "not_ascii12_text",
                         "event": WRONG_TEXT_EVENT, "actions": len(out)})

        # A wrong envelope on the same vital id: outer version 1 instead of 0.
        wrong_env_pc = bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 1)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
            + bytes(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])[20:]
        )
        wrong_env = boot("dm_wrong_env")
        out = wrong_env.dispatch(legacy.parse_outer(wrong_env_pc))
        check("a wrong envelope on the same vital id: no bytes",
              out == [] and wrong_env.damage_model_sweep_count == 0)
        check("a wrong envelope on the same vital id: the named event, exactly",
              wrong_env.events.count(WRONG_ENVELOPE_EVENT) == 1
              and SWEEP_EVENT not in wrong_env.events)
        refusals.append({"case": "wrong_envelope",
                         "event": WRONG_ENVELOPE_EVENT, "actions": len(out)})

        check("no refusal path ever names the sweep event",
              not any(
                  SWEEP_EVENT in candidate.events
                  for candidate in (no_select, not_ready, wrong_text, wrong_env)
              ))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 7. containment: no database write, no socket, no lane "
                  "when the flag is absent --")
        check("no file in the database directory changed across the sweep "
              "(main file AND the WAL/SHM sidecars, by size and sha256)",
              dir_after == dir_before,
              "%s -> %s" % (dir_before, dir_after))
        check("the logical database content is identical across the sweep "
              "(full iterdump over a read-only connection)",
              dump_after == dump_before)
        check("the database this run built lives under the system temporary "
              "directory",
              Path(tempfile.gettempdir()).resolve()
              in db_path.resolve().parents)
        check("the database this run built is nowhere inside the repository's "
              "committed state directory, so the canonical database cannot be "
              "the file under test",
              (ROOT / "state").resolve() not in db_path.resolve().parents
              and ROOT.resolve() not in db_path.resolve().parents)
        check("no socket was constructed while the sweep ran",
              trap.attempts == [], str(trap.attempts))
        check("the sweep took no socket action (every action is a 4-tuple)",
              all(len(action) == 4 for action in actions))

        off = boot("dm_flag_off", enabled=False)
        off_actions = off.dispatch(trigger())
        off_labels = [row[0] for row in off_actions]
        check("with the scenario absent no HYP-PF-024 action is composed",
              not any(label.startswith(EXPECTED_LABEL_PREFIX)
                      for label in off_labels), str(off_labels))
        check("with the scenario absent none of the sweep's bytes appear",
              not ({row[1] for row in off_actions} & seen_pcs))
        check("with the scenario absent no damage-model event is named",
              not any(event.startswith(EVENT_PREFIX) for event in off.events))
        check("with the scenario absent the state carries no sweep count",
              getattr(off, "damage_model_sweep_count", 0) == 0)

    verdict = {
        "milestone": "DAMAGE-DISPATCH-001",
        "profile": profile_name,
        "hypothesis_id": dmh.DAMAGE_MODEL_HYPOTHESIS_ID,
        "scenario": scenario_path.relative_to(ROOT).as_posix(),
        "layer": "wire_only_no_client_no_socket_no_server_process",
        "guards_run": guards,
        "failures": failures,
        "notes": notes,
        "result": "PASS" if not failures else "FAIL",
        "dispatch": {
            "trigger": "one accepted 34-byte ascii12 chat-input frame",
            "trigger_vital_id": CHAT_INPUT_VITAL_ID,
            "frames_per_accepted_request": len(actions),
            "one_shot": True,
            "socket_action": "none",
            "socket_constructor_attempts": trap.attempts,
        },
        "identity": {
            "rule": "performer == target == the session's selected character",
            "session_identity": session_identity,
            "coincides_with_the_pinned_probe_identity": (
                session_identity == dmh.DAMAGE_PROBE_IDENTITY_LO
            ),
        },
        "database_guard": {
            "what_it_measures": (
                "every file in the throwaway database directory, including the "
                "WAL and SHM sidecars, is byte-identical immediately before and "
                "after the dispatch, and the full logical iterdump is identical "
                "as well"
            ),
            "what_it_does_not_measure": (
                "that no write path exists anywhere on the lane; that is a "
                "reading of the code, not a measurement of this run"
            ),
            "files_before": [list(row) for row in dir_before],
            "files_after": [list(row) for row in dir_after],
            "logical_dump_identical": dump_after == dump_before,
        },
        "refusals": refusals,
        "not_claimed": list(dmh.DAMAGE_MODEL_NONCLAIMS),
        "frames": rows,
    }
    if evidence_path is not None:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(verdict, indent=2) + "\n", encoding="utf-8",
        )
    if want_json:
        print(json.dumps(verdict, indent=2))
    else:
        for note in notes:
            print()
            print("  NOTE  %s" % note)
        print()
        print("guards run: %d" % guards)
        if failures:
            print("RESULT: FAIL - %d guard(s) drifted: %s"
                  % (len(failures), failures))
        else:
            print("RESULT: PASS - %d guards PASS - the real dispatcher emits "
                  "the encoder's four-step CHitResult hit sweep byte for byte "
                  "against the session's own actor (client layer = attended, "
                  "not run)" % guards)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
