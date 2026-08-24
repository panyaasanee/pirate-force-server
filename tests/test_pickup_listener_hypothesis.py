"""PICKUP-LISTENER-001 (HYP-PF-036) -- the PickupTerrainThing inbound
strict-decoder lane (vital id DERIVED 0x4543) and its dispatch hookup.

Pure offline pytest: no network, no GameClient, no UI; the dispatch half runs
the REAL ``make_state_class`` path against a throwaway temp database.

What these tests are actually proving
-------------------------------------
The committed delivery tables (pf_bridge/external/PF_SERIALIZER_FIELDS.tsv
rows 859-862, statically CLOSED) carry a byte-symmetric W/R body for
PickupTerrainThing:

    u32 tag 0x14 at object+0x14, then u8 tag 0x08 at object+0x18 -- 7 bytes.

This file proves the server-side strict decoder reads exactly that order and
nothing else -- tag bytes asserted literally at their byte positions,
round-trip through the module's own test-side encoder, refusal by named
reason on truncation, wrong tags and trailing bytes, the module/scenario
probe pins, and the dispatch path: an accepted frame is decoded, counted and
recorded (count, object_ref_u32, opaque_u8, raw body hex) with NO reply and
NO write, every refusal family is silent with a named event and a refusal
record, and with no scenario the branch does not exist.

NOT tested here, because it is not claimed: that any real client ever sends
vital id 0x4543 -- THE OPCODE IS DERIVED from the name-hash (the runtime id
slot is zero on disk) and the capture corpus holds ZERO PickupTerrainThing
frames in either direction; any MEANING for object_ref_u32 beyond the GT-046
source proof (copied from the selected live runtime drop-object -- NOT
claimed to be an element_key) or for opaque_u8 (never interpreted); any
pickup rule or any response frame; that this lane explains monster-drop
pickup (the undecoded FightingDrop* family may carry it instead); the
request envelope a real client would use (the accepted envelope is this
project's own design); and anything about the original server.
"""
from __future__ import annotations

from dataclasses import replace
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.ground_loot_hypothesis import (  # noqa: E402
    load_ground_loot_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.pickup_listener_hypothesis import (  # noqa: E402
    PICKUP_LISTENER_HYPOTHESIS_ID,
    PICKUP_LISTENER_OBJECT_REF_TAG,
    PICKUP_LISTENER_OPAQUE_U8_TAG,
    PICKUP_LISTENER_PAYLOAD_SIZE,
    PICKUP_LISTENER_PROBE_FIELDS,
    PICKUP_LISTENER_PROBE_ORDER,
    PICKUP_LISTENER_PROBE_PAYLOAD_SHA256,
    PICKUP_LISTENER_PROBE_PAYLOAD_SIZE,
    PICKUP_LISTENER_PROBE_REQUEST_PC_SHA256,
    PICKUP_LISTENER_PROBE_REQUEST_PC_SIZE,
    PICKUP_LISTENER_REJECTIONS,
    PICKUP_LISTENER_RUNTIME_ID_SLOT_VA,
    PICKUP_LISTENER_SCENARIO_ID,
    PICKUP_LISTENER_VITAL_ID,
    PICKUP_LISTENER_VITAL_ID_PROVENANCE,
    PICKUP_LISTENER_VITAL_VERSION,
    PickupListenerFields,
    classify_pickup_listener_attempt,
    compose_pickup_listener_probe_pc,
    decode_pickup_listener_payload,
    encode_pickup_listener_payload,
    load_pickup_listener_hypothesis_scenario,
    require_pickup_listener_hypothesis_scenario,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "pickup_listener_hypothesis_decode_probe.json"
)
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
ACCEPT_EVENT_PREFIX = "pickup_listener_hypothesis_decoded_no_reply"


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)


def _payload_bytes(fields: PickupListenerFields) -> bytes:
    """The delivery-table layout, assembled independently of the encoder."""
    return (
        bytes([PICKUP_LISTENER_OBJECT_REF_TAG])
        + fields.object_ref_u32.to_bytes(4, "little")
        + bytes([PICKUP_LISTENER_OPAQUE_U8_TAG, fields.opaque_u8])
    )


def _accept_events(state):
    return [
        event for event in state.events
        if event.startswith(ACCEPT_EVENT_PREFIX)
    ]


class DerivedOpcodeNonclaimTests(unittest.TestCase):
    """The loudest nonclaim of this lane, pinned as tests."""

    def test_the_opcode_is_derived_0x4543_and_never_observed_on_wire(self):
        # 0x4543 (17731) is HASH-DERIVED from the class name only
        # (FACTPACK_L2_CLASSCENSUS001 row 1003) and has NEVER been observed
        # on any wire in either direction (PF_FIELD_VALIDATION rows 102-103,
        # NOT_OBSERVED); the runtime id slot 0x0108202C is zero on disk.
        # This test pins the constant AND the declared provenance so the
        # derivation can never silently masquerade as an observation.
        self.assertEqual(PICKUP_LISTENER_VITAL_ID, 0x4543)
        self.assertEqual(PICKUP_LISTENER_VITAL_ID, 17731)
        self.assertEqual(
            PICKUP_LISTENER_VITAL_ID_PROVENANCE,
            "derived_from_name_hash_never_observed_on_wire",
        )
        self.assertEqual(PICKUP_LISTENER_RUNTIME_ID_SLOT_VA, 0x0108202C)

    def test_the_derived_nonclaim_is_loud_in_module_and_scenario(self):
        module_source = (
            SRC_ROOT / "pickup_listener_hypothesis.py"
        ).read_text(encoding="utf-8")
        self.assertIn("DERIVED, NEVER OBSERVED", module_source)
        scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            scenario["wire"]["vital_id_provenance"],
            "derived_from_name_hash_never_observed_on_wire",
        )
        self.assertIn(
            "the_runtime_vital_id_which_is_hash_derived_never_observed",
            scenario["nonclaims"],
        )


class WireShapeTests(_LegacyCase):
    """The statically closed tag bytes, at their exact positions, literally."""

    def test_the_payload_is_the_seven_closed_bytes(self):
        fields = PickupListenerFields(0x04030201, 0x05)
        payload = encode_pickup_listener_payload(self.legacy, fields)
        self.assertEqual(
            payload,
            b"\x14\x01\x02\x03\x04"            # u32 tag 0x14 object+0x14
            + b"\x08\x05",                     # u8 tag 0x08 object+0x18
        )

    def test_the_encoder_matches_an_independent_assembly(self):
        for label in PICKUP_LISTENER_PROBE_ORDER:
            fields = PICKUP_LISTENER_PROBE_FIELDS[label]
            self.assertEqual(
                encode_pickup_listener_payload(self.legacy, fields),
                _payload_bytes(fields),
                label,
            )

    def test_the_payload_size_is_always_seven(self):
        for label in PICKUP_LISTENER_PROBE_ORDER:
            payload = encode_pickup_listener_payload(
                self.legacy, PICKUP_LISTENER_PROBE_FIELDS[label],
            )
            self.assertEqual(len(payload), PICKUP_LISTENER_PAYLOAD_SIZE)
            self.assertEqual(
                len(payload),
                PICKUP_LISTENER_PROBE_PAYLOAD_SIZE[label],
            )

    def test_the_probe_payload_pins_hold(self):
        for label in PICKUP_LISTENER_PROBE_ORDER:
            payload = encode_pickup_listener_payload(
                self.legacy, PICKUP_LISTENER_PROBE_FIELDS[label],
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                PICKUP_LISTENER_PROBE_PAYLOAD_SHA256[label],
                label,
            )

    def test_the_probe_request_pc_pins_hold(self):
        for label in PICKUP_LISTENER_PROBE_ORDER:
            pc = compose_pickup_listener_probe_pc(
                self.legacy, PICKUP_LISTENER_PROBE_FIELDS[label],
            )
            self.assertEqual(
                len(pc),
                PICKUP_LISTENER_PROBE_REQUEST_PC_SIZE[label],
                label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                PICKUP_LISTENER_PROBE_REQUEST_PC_SHA256[label],
                label,
            )

    def test_the_probe_pc_parses_back_through_the_frozen_parser(self):
        for label in PICKUP_LISTENER_PROBE_ORDER:
            fields = PICKUP_LISTENER_PROBE_FIELDS[label]
            parsed = self.legacy.parse_outer(
                compose_pickup_listener_probe_pc(self.legacy, fields)
            )
            self.assertEqual(
                parsed.nested_id, PICKUP_LISTENER_VITAL_ID, label,
            )
            self.assertEqual(
                parsed.nested_version,
                PICKUP_LISTENER_VITAL_VERSION,
                label,
            )
            self.assertEqual(
                decode_pickup_listener_payload(parsed.nested_payload),
                fields,
                label,
            )


class RoundTripTests(_LegacyCase):
    def test_encode_then_decode_is_identity_at_the_width_edges(self):
        for fields in (
            PickupListenerFields(0, 0),
            PickupListenerFields(1, 255),
            PickupListenerFields(0xFFFFFFFF, 0),
            PickupListenerFields(0xFFFFFFFF, 0xFF),
            PickupListenerFields(0x80000000, 0x80),
        ):
            payload = encode_pickup_listener_payload(self.legacy, fields)
            self.assertEqual(
                decode_pickup_listener_payload(payload), fields,
            )

    def test_decode_accepts_bytearray_and_returns_the_frozen_type(self):
        payload = bytearray(
            encode_pickup_listener_payload(
                self.legacy, PickupListenerFields(7, 9),
            )
        )
        fields = decode_pickup_listener_payload(payload)
        self.assertIs(type(fields), PickupListenerFields)
        self.assertEqual(fields, PickupListenerFields(7, 9))


class FailClosedTests(_LegacyCase):
    def assert_decode_refuses(self, payload, reason):
        self.assertIn(reason, PICKUP_LISTENER_REJECTIONS)
        with self.assertRaises(ValueError) as caught:
            decode_pickup_listener_payload(payload)
        self.assertEqual(
            str(caught.exception), "pickup listener rejected: " + reason,
        )

    def assert_encode_refuses(self, fields, reason):
        self.assertIn(reason, PICKUP_LISTENER_REJECTIONS)
        with self.assertRaises(ValueError) as caught:
            encode_pickup_listener_payload(self.legacy, fields)
        self.assertEqual(
            str(caught.exception), "pickup listener rejected: " + reason,
        )

    def test_non_bytes_payloads_refuse(self):
        for payload in (None, 7, "1401020304 0805", [0x14], object()):
            self.assert_decode_refuses(payload, "truncated_payload")

    def test_every_truncation_refuses(self):
        good = _payload_bytes(PickupListenerFields(0x01020304, 0x05))
        for cut in range(len(good)):
            self.assert_decode_refuses(good[:cut], "truncated_payload")

    def test_a_wrong_object_ref_tag_refuses(self):
        good = _payload_bytes(PickupListenerFields(1, 1))
        self.assert_decode_refuses(
            bytes([good[0] ^ 0x01]) + good[1:], "wrong_object_ref_tag",
        )

    def test_a_wrong_opaque_u8_tag_refuses(self):
        good = _payload_bytes(PickupListenerFields(1, 1))
        self.assert_decode_refuses(
            good[:5] + bytes([good[5] ^ 0x01]) + good[6:],
            "wrong_opaque_u8_tag",
        )

    def test_the_template_lane_u8_tag_0x0b_is_refused_here(self):
        # The HYP-PF-034 template body uses u8 tag 0x0B; THIS delivery table
        # says 0x08.  A frame composed with the template's tag must refuse,
        # or the codec mirror would silently be the wrong table's.
        good = _payload_bytes(PickupListenerFields(1, 1))
        self.assert_decode_refuses(
            good[:5] + bytes([0x0B]) + good[6:], "wrong_opaque_u8_tag",
        )

    def test_trailing_bytes_refuse(self):
        good = _payload_bytes(PickupListenerFields(1, 1))
        for extra in (b"\x00", b"\x14\x01\x02\x03\x04", good):
            self.assert_decode_refuses(
                good + extra, "trailing_bytes_after_object",
            )

    def test_no_partial_result_survives_a_refusal(self):
        good = _payload_bytes(PickupListenerFields(0xDEADBEEF, 0x7F))
        for bad in (good[:6], good + b"\x00"):
            with self.assertRaises(ValueError):
                decode_pickup_listener_payload(bad)

    def test_the_encoder_refuses_non_int_members(self):
        for fields in (
            PickupListenerFields("1", 0),
            PickupListenerFields(0, "1"),
            PickupListenerFields(True, 0),
            PickupListenerFields(0, False),
            PickupListenerFields(1.0, 0),
        ):
            self.assert_encode_refuses(
                fields, "pickup_value_type_not_integer",
            )
        self.assert_encode_refuses(
            (1, 2), "pickup_value_type_not_integer",
        )

    def test_the_encoder_refuses_members_outside_their_width(self):
        for fields in (
            PickupListenerFields(-1, 0),
            PickupListenerFields(1 << 32, 0),
            PickupListenerFields(0, -1),
            PickupListenerFields(0, 256),
        ):
            self.assert_encode_refuses(
                fields, "pickup_value_outside_field_width",
            )


class ClassifierTests(_LegacyCase):
    def _parsed(self, *, payload=None, outer_id=None, outer_version=0,
                nested_id=None, nested_version=None):
        legacy = self.legacy
        if payload is None:
            payload = _payload_bytes(PickupListenerFields(5, 6))
        outer = (
            legacy.GSCN_RUNTIME_PROTOCOL_REQ if outer_id is None else outer_id
        )
        nested = (
            PICKUP_LISTENER_VITAL_ID if nested_id is None else nested_id
        )
        nver = (
            PICKUP_LISTENER_VITAL_VERSION if nested_version is None
            else nested_version
        )
        return legacy.parse_outer(bytes(
            legacy.u16tag(0x12, outer)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, nested)
            + legacy.u8tag(0x0B, nver)
            + payload
        ))

    def test_the_exact_pickup_classifies_as_accepted(self):
        self.assertEqual(
            classify_pickup_listener_attempt(self.legacy, self._parsed()),
            "exact_pickup",
        )

    def test_wrong_envelopes_classify_as_wrong_envelope(self):
        for parsed in (
            self._parsed(outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
            self._parsed(outer_version=1),
            self._parsed(nested_version=1),
        ):
            self.assertEqual(
                classify_pickup_listener_attempt(self.legacy, parsed),
                "wrong_envelope",
            )

    def test_body_refusals_classify_by_their_named_reason(self):
        good = _payload_bytes(PickupListenerFields(5, 6))
        for payload, reason in (
            (good[:4], "truncated_payload"),
            (bytes([good[0] ^ 0x01]) + good[1:], "wrong_object_ref_tag"),
            (good[:5] + bytes([good[5] ^ 0x01]) + good[6:],
             "wrong_opaque_u8_tag"),
            (good + b"\x00", "trailing_bytes_after_object"),
        ):
            self.assertEqual(
                classify_pickup_listener_attempt(
                    self.legacy, self._parsed(payload=payload),
                ),
                reason,
            )


class ScenarioGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_committed_scenario_file_loads(self):
        scenario = load_pickup_listener_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(
            scenario.scenario_id, PICKUP_LISTENER_SCENARIO_ID,
        )
        self.assertEqual(
            scenario.hypothesis_id, PICKUP_LISTENER_HYPOTHESIS_ID,
        )

    def test_the_scenario_file_declares_the_gates(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(data["test_only"], True)
        self.assertIs(data["production_allowed"], False)
        self.assertEqual(data["dispatch"]["socket_action"], "none")
        self.assertEqual(
            data["dispatch"]["frames_emitted_per_accepted_request"], 0,
        )
        self.assertEqual(
            data["persisted_post_state"]["database_write"], "none",
        )

    def test_any_edit_to_the_scenario_file_is_refused(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        edits = [
            ("extra_key", lambda d: d.update(extra=1)),
            ("missing_key", lambda d: d.pop("nonclaims")),
            ("flip_production", lambda d: d.update(production_allowed=True)),
            (
                "widen_dispatch",
                lambda d: d["dispatch"].update(
                    frames_emitted_per_accepted_request=1,
                ),
            ),
            (
                "retype_size",
                lambda d: d["wire"].update(payload_wire_size=7.0),
            ),
            (
                "claim_observed_id",
                lambda d: d["wire"].update(
                    vital_id_provenance="observed_on_wire",
                ),
            ),
        ]
        for name, edit in edits:
            tampered = json.loads(json.dumps(data))
            edit(tampered)
            path = Path(self.tmp.name) / f"{name}.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError, msg=name):
                load_pickup_listener_hypothesis_scenario(path)

    def test_other_scenario_files_are_refused_by_name(self):
        for name in (
            "learn_skill_request_hypothesis_decode_probe.json",
            "skill_attr_hypothesis_attr_sweep.json",
        ):
            with self.assertRaises(ValueError):
                load_pickup_listener_hypothesis_scenario(
                    ROOT / "scenarios" / name,
                )
        with self.assertRaises(ValueError):
            load_pickup_listener_hypothesis_scenario(
                Path(self.tmp.name) / "nope.json",
            )

    def test_a_lookalike_scenario_object_is_refused(self):
        scenario = load_pickup_listener_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(),
            None,
            replace(scenario, hypothesis_id="HYP-PF-034"),
            replace(scenario, scenario_id="pickup_listener_other"),
            replace(scenario, response_policy="reply_with_result"),
        ):
            with self.assertRaises(ValueError):
                require_pickup_listener_hypothesis_scenario(bad)

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        # The two importers are named and the list is exact, so a third one
        # shows up here as a failure -- the containment shape every sibling
        # lane pins.  connection.py, scenario.py and the frozen v141 module
        # know nothing about any of it.
        module = "pickup_listener_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name,
            )
        legacy_source = LEGACY_PATH.read_text(encoding="utf-8")
        self.assertNotIn(module, legacy_source)
        self.assertNotIn("0x4543", legacy_source)
        self.assertNotIn("PickupTerrainThing", legacy_source)

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if pickup_listener_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "pickup_listener_hypothesis_scenario is not None\n"
            "                and nested_id == PICKUP_LISTENER_VITAL_ID",
            source,
        )
        self.assertEqual(
            source.count("_dispatch_pickup_listener_hypothesis"), 2,
        )

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--pickup-listener-hypothesis-scenario", source)
        self.assertIn(
            "'--pickup-listener-hypothesis-scenario requires an explicit '\n"
            "            'existing --db'",
            source,
        )

    def test_the_lane_is_registered_in_the_hypothesis_ledger(self):
        raw = json.loads(
            (ROOT / "docs" / "HYPOTHESIS_LEDGER.json").read_text(
                encoding="utf-8",
            )
        )
        for entry in raw["entries"]:
            if entry["id"] != PICKUP_LISTENER_HYPOTHESIS_ID:
                continue
            self.assertEqual(entry["status"], "active")
            self.assertIs(entry["production_allowed"], False)
            self.assertEqual(
                entry["introduced_checkpoint"], "PICKUP-LISTENER-001",
            )
            self.assertIn("8e439d4f", entry["provenance"])
            self.assertIn("PF_SERIALIZER_FIELDS.tsv", entry["provenance"])
            self.assertIn("DERIVED", entry["exact_value_or_transform"])
            self.assertIn("GT-046", entry["provenance"])
            return
        self.fail(
            "HYP-PF-036 is not registered in docs/HYPOTHESIS_LEDGER.json"
        )

    def test_the_coverage_row_stays_in_progress_not_runtime_pass(self):
        raw = json.loads(
            (ROOT / "docs" / "FUNCTIONAL_COVERAGE.json").read_text(
                encoding="utf-8",
            )
        )
        for domain in raw["domains"]:
            for cap in domain["capabilities"]:
                if cap["id"] != "monster_spawn_and_loot":
                    continue
                self.assertEqual(cap["status"], "in_progress")
                self.assertIn(
                    "tests/test_pickup_listener_hypothesis.py",
                    cap["test_refs"],
                )
                self.assertIn(
                    "scenarios/pickup_listener_hypothesis_decode_probe"
                    ".json",
                    cap["evidence_refs"],
                )
                self.assertIn(
                    "src/pirateforce_foundation/pickup_listener_hypothesis"
                    ".py",
                    cap["evidence_refs"],
                )
                return
        self.fail(
            "npc_interaction/monster_spawn_and_loot row is missing from "
            "the coverage matrix"
        )

    def test_the_dispatch_method_composes_no_reply_of_any_kind(self):
        # Listen-only: the dispatch method must not call any composer --
        # no make_* helper of any lane, no projector, no legacy vital
        # builder -- and the module itself must not import or name the
        # ItemOperate response carrier the GT-049 green line rides.
        module_source = (
            SRC_ROOT / "pickup_listener_hypothesis.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ItemOperate", module_source)
        self.assertNotIn("0x4C13", module_source)
        runtime_tree = ast.parse(
            (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        )
        for node in ast.walk(runtime_tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_dispatch_pickup_listener_hypothesis"
            ):
                body_dump = ast.dump(node)
                self.assertNotIn("make_", body_dump)
                self.assertNotIn("ItemOperate", body_dump)
                self.assertNotIn("projector", body_dump)
                break
        else:
            self.fail("runtime.py lost the dispatch method")


class DispatchTests(unittest.TestCase):
    """The runtime wire hookup, on the REAL make_state_class path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_pickup_listener_hypothesis_scenario(
            SCENARIO_PATH
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, probe=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            pickup_listener_hypothesis_scenario=(
                self.scenario if probe else None
            ),
        )

    def _state(self, login, *, probe=True, ready=True):
        state = self._state_type(probe=probe)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _request(self, label="MID", *, payload=None):
        if payload is None:
            return self.legacy.parse_outer(
                compose_pickup_listener_probe_pc(
                    self.legacy, PICKUP_LISTENER_PROBE_FIELDS[label],
                )
            )
        legacy = self.legacy
        return legacy.parse_outer(bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, PICKUP_LISTENER_VITAL_ID)
            + legacy.u8tag(0x0B, PICKUP_LISTENER_VITAL_VERSION)
            + payload
        ))

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    # ----- happy path ------------------------------------------------------

    def test_an_accepted_frame_is_decoded_counted_and_unanswered(self):
        state = self._state("pkl01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._request("MID"))
        self.assertEqual(actions, [])
        self.assertEqual(state.pickup_listener_accepted_count, 1)
        self.assertEqual(
            state.pickup_listener_last_fields, (305419896, 42),
        )
        self.assertEqual(len(_accept_events(state)), 1)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_the_record_carries_count_fields_and_raw_body_hex(self):
        state = self._state("pkl-record")
        fields = PICKUP_LISTENER_PROBE_FIELDS["MID"]
        raw_hex = _payload_bytes(fields).hex().upper()
        state.dispatch(self._request("MID"))
        self.assertEqual(
            state.pickup_listener_records,
            [(1, fields.object_ref_u32, fields.opaque_u8, raw_hex)],
        )
        # The one ASCII event line carries the same observables.
        (event,) = _accept_events(state)
        event.encode("ascii")
        self.assertIn("count1", event)
        self.assertIn(f"object_ref_0x{fields.object_ref_u32:08X}", event)
        self.assertIn(f"opaque_u8_0x{fields.opaque_u8:02X}", event)
        self.assertIn(f"payload_{raw_hex}", event)

    def test_each_probe_decodes_to_its_declared_pair(self):
        state = self._state("pkl-values")
        for index, label in enumerate(PICKUP_LISTENER_PROBE_ORDER):
            fields = PICKUP_LISTENER_PROBE_FIELDS[label]
            self.assertEqual(state.dispatch(self._request(label)), [])
            self.assertEqual(
                state.pickup_listener_last_fields,
                (fields.object_ref_u32, fields.opaque_u8),
                label,
            )
            self.assertEqual(
                state.pickup_listener_records[index],
                (
                    index + 1,
                    fields.object_ref_u32,
                    fields.opaque_u8,
                    _payload_bytes(fields).hex().upper(),
                ),
                label,
            )
        self.assertEqual(state.pickup_listener_accepted_count, 3)
        self.assertEqual(len(_accept_events(state)), 3)

    def test_the_lane_writes_nothing_to_the_database(self):
        state = self._state("pkl-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        for label in PICKUP_LISTENER_PROBE_ORDER:
            state.dispatch(self._request(label))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.pickup_listener_accepted_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("pkl-nowrite-refused")
        before = self.db_path.read_bytes()
        good = _payload_bytes(PickupListenerFields(5, 6))
        for payload in (good[:4], good + b"\x00"):
            self.assertEqual(
                state.dispatch(self._request(payload=payload)), [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.pickup_listener_accepted_count, 0)
        self.assertIsNone(state.pickup_listener_last_fields)
        self.assertEqual(state.pickup_listener_records, [])

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertEqual(_accept_events(state), [])
        self.assertEqual(state.pickup_listener_accepted_count, 0)

    def test_every_body_refusal_family_is_silent_and_recorded(self):
        good = _payload_bytes(PickupListenerFields(5, 6))
        for payload, reason in (
            (good[:4], "truncated_payload"),
            (bytes([good[0] ^ 0x01]) + good[1:], "wrong_object_ref_tag"),
            (good[:5] + bytes([good[5] ^ 0x01]) + good[6:],
             "wrong_opaque_u8_tag"),
            (good + b"\x00", "trailing_bytes_after_object"),
        ):
            state = self._state("pkl-" + reason.replace("_", "")[:10])
            self._assert_silent(
                state, self._request(payload=payload),
                f"pickup_listener_hypothesis_{reason}_no_reply",
            )
            self.assertEqual(
                state.pickup_listener_refusals,
                [(reason, payload.hex().upper())],
            )

    def test_a_wrong_envelope_is_silent_with_a_named_refusal_record(self):
        state = self._state("pkl-envelope")
        legacy = self.legacy
        payload = _payload_bytes(PickupListenerFields(5, 6))
        pc = bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 1)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, PICKUP_LISTENER_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
            + payload
        )
        self._assert_silent(
            state, legacy.parse_outer(pc),
            "pickup_listener_hypothesis_wrong_envelope_no_reply",
        )
        self.assertEqual(
            state.pickup_listener_refusals,
            [("wrong_envelope", payload.hex().upper())],
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("pkl-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertEqual(state.dispatch(self._request("MID")), [])
        self.assertIn(
            "pickup_listener_hypothesis_no_selected_no_reply",
            state.events,
        )
        self.assertEqual(state.pickup_listener_accepted_count, 0)

    def test_a_not_yet_ready_sequence_fails_closed(self):
        state = self._state("pkl-sequence", ready=False)
        self._assert_silent(
            state, self._request("MID"),
            "pickup_listener_hypothesis_wrong_sequence_no_reply",
        )

    # ----- containment -----------------------------------------------------

    def test_without_the_scenario_the_branch_does_not_exist(self):
        # Proven by COMPARISON, not by absence: the lane-off state and a
        # plain no-scenario baseline state (make_state_class with no lane
        # kwargs at all) must produce the same actions and the same new
        # events for the same 0x4543 frame -- that is what "falls through to
        # the frozen path exactly as before this module existed" means, and
        # it is also what keeps an attended run under a WRONG derived
        # opcode interpretable.
        state = self._state("pkl-absent", probe=False)
        baseline_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        baseline = baseline_type("pkl-absent-base")
        baseline.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = baseline.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(baseline.foundation.account_id)
        baseline.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[-1].selector)
        ))
        baseline.runtime_ack_sent = True
        events_before = len(state.events)
        baseline_events_before = len(baseline.events)
        lane_off_actions = state.dispatch(self._request("MID"))
        baseline_actions = baseline.dispatch(self._request("MID"))
        self.assertEqual(lane_off_actions, baseline_actions)
        self.assertEqual(
            state.events[events_before:],
            baseline.events[baseline_events_before:],
        )
        self.assertEqual(state.pickup_listener_accepted_count, 0)
        self.assertIsNone(state.pickup_listener_last_fields)
        self.assertEqual(state.pickup_listener_records, [])
        self.assertEqual(state.pickup_listener_refusals, [])
        for event in state.events:
            self.assertNotIn("pickup_listener_hypothesis", event)

    # ----- mutual exclusion ------------------------------------------------
    # The pickup+ground_loot pair matters most: composing the HYP-PF-032
    # spawner (the lane that could put a ground object on a client screen)
    # with THIS listener in one boot is exactly what an attended pickup
    # test would want, and exactly what the mutual-exclusion pattern
    # forbids without an owner ruling (see the HYP-PF-036 ledger entry's
    # falsification).  Both halves are behavioral, not source-substring.

    def test_the_lane_refuses_the_ground_loot_spawner_in_the_same_state(self):
        ground_loot = load_ground_loot_hypothesis_scenario(
            ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
        )
        with self.assertRaises(ValueError) as raised:
            make_state_class(
                self.legacy, self.lifecycle, self.projector,
                pickup_listener_hypothesis_scenario=self.scenario,
                ground_loot_hypothesis_scenario=ground_loot,
            )
        self.assertIn("mutually exclusive", str(raised.exception))

    def test_the_cli_flag_refuses_the_ground_loot_flag_in_the_same_boot(self):
        from pirateforce_foundation import app
        saved = sys.argv[:]
        try:
            sys.argv = [
                "app.py", "--db", "x",
                "--pickup-listener-hypothesis-scenario",
                str(SCENARIO_PATH),
                "--ground-loot-hypothesis-scenario",
                str(
                    ROOT / "scenarios"
                    / "ground_loot_hypothesis_bit08_render.json"
                ),
            ]
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    app.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("mutually exclusive", buf.getvalue())
        finally:
            sys.argv = saved


class SourceHygieneTests(unittest.TestCase):
    def test_the_module_is_ascii_and_survives_the_bridge_console_encoding(self):
        source = (
            SRC_ROOT / "pickup_listener_hypothesis.py"
        ).read_text(encoding="utf-8")
        source.encode("ascii")
        source.encode("cp874")

    def test_this_test_file_is_ascii_and_survives_the_bridge_console(self):
        source = Path(__file__).read_text(encoding="utf-8")
        source.encode("ascii")
        source.encode("cp874")


if __name__ == "__main__":
    unittest.main()
