"""LEARN-SKILL-REQUEST-001 (HYP-PF-034) -- the CLearnSkillVital 0x36AA
inbound strict-decoder lane and its dispatch hookup.

Pure offline pytest: no network, no GameClient, no UI; the dispatch half runs
the REAL ``make_state_class`` path against a throwaway temp database.

What these tests are actually proving
-------------------------------------
The committed delivery tables (pf_bridge/external/PF_SERIALIZER_FIELDS.tsv,
re-verified against the image by GT-050 jobs 1-2) carry a byte-symmetric W/R
body for the request vital 0x36AA:

    u32 tag 0x14 at object+0x14, then u8 tag 0x0B at object+0x18 -- 7 bytes.

This file proves the server-side strict decoder reads exactly that order and
nothing else -- tag bytes asserted literally at their byte positions,
round-trip through the module's own test-side encoder, refusal by named
reason on truncation, wrong tags and trailing bytes, the module/scenario
probe pins, and the dispatch path: an accepted request is decoded, counted
and recorded with NO reply and NO write, every refusal family is silent with
a named event, and with no scenario the branch does not exist.

NOT tested here, because it is not claimed: the NATURAL DIRECTION of 0x36AA
(the client carries both W and R codecs and nobody has seen it on a wire --
the direction proof is bridge work, queued); any MEANING for the two request
fields (opaque values named by object offset only); any learn rule or any
result response; the request envelope a real client would use (the accepted
envelope is this project's own design); and anything about the original
server.
"""
from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.learn_skill_request_hypothesis import (  # noqa: E402
    LEARN_SKILL_REQUEST_HYPOTHESIS_ID,
    LEARN_SKILL_REQUEST_PAYLOAD_SIZE,
    LEARN_SKILL_REQUEST_PROBE_FIELDS,
    LEARN_SKILL_REQUEST_PROBE_ORDER,
    LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SHA256,
    LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SIZE,
    LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SHA256,
    LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SIZE,
    LEARN_SKILL_REQUEST_REJECTIONS,
    LEARN_SKILL_REQUEST_SCENARIO_ID,
    LEARN_SKILL_REQUEST_U8_TAG,
    LEARN_SKILL_REQUEST_U32_TAG,
    LEARN_SKILL_REQUEST_VITAL_ID,
    LEARN_SKILL_REQUEST_VITAL_VERSION,
    LearnSkillRequestFields,
    classify_learn_skill_request_attempt,
    compose_learn_skill_request_probe_pc,
    decode_learn_skill_request_payload,
    encode_learn_skill_request_payload,
    load_learn_skill_request_hypothesis_scenario,
    require_learn_skill_request_hypothesis_scenario,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "learn_skill_request_hypothesis_decode_probe.json"
)
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
ACCEPT_EVENT = "learn_skill_request_hypothesis_decoded_no_reply"


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)


def _payload_bytes(fields: LearnSkillRequestFields) -> bytes:
    """The delivery-table layout, assembled independently of the encoder."""
    return (
        bytes([LEARN_SKILL_REQUEST_U32_TAG])
        + fields.request_u32_0x14.to_bytes(4, "little")
        + bytes([LEARN_SKILL_REQUEST_U8_TAG, fields.request_u8_0x18])
    )


class WireShapeTests(_LegacyCase):
    """The proven tag bytes, at their exact byte positions, literally."""

    def test_the_payload_is_the_seven_proven_bytes(self):
        fields = LearnSkillRequestFields(0x04030201, 0x05)
        payload = encode_learn_skill_request_payload(self.legacy, fields)
        self.assertEqual(
            payload,
            b"\x14\x01\x02\x03\x04"            # u32 tag 0x14 object+0x14
            + b"\x0b\x05",                     # u8 tag 0x0B object+0x18
        )

    def test_the_encoder_matches_an_independent_assembly(self):
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            fields = LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
            self.assertEqual(
                encode_learn_skill_request_payload(self.legacy, fields),
                _payload_bytes(fields),
                label,
            )

    def test_the_payload_size_is_always_seven(self):
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            payload = encode_learn_skill_request_payload(
                self.legacy, LEARN_SKILL_REQUEST_PROBE_FIELDS[label],
            )
            self.assertEqual(len(payload), LEARN_SKILL_REQUEST_PAYLOAD_SIZE)
            self.assertEqual(
                len(payload),
                LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SIZE[label],
            )

    def test_the_probe_payload_pins_hold(self):
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            payload = encode_learn_skill_request_payload(
                self.legacy, LEARN_SKILL_REQUEST_PROBE_FIELDS[label],
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                LEARN_SKILL_REQUEST_PROBE_PAYLOAD_SHA256[label],
                label,
            )

    def test_the_probe_request_pc_pins_hold(self):
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            pc = compose_learn_skill_request_probe_pc(
                self.legacy, LEARN_SKILL_REQUEST_PROBE_FIELDS[label],
            )
            self.assertEqual(
                len(pc),
                LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SIZE[label],
                label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                LEARN_SKILL_REQUEST_PROBE_REQUEST_PC_SHA256[label],
                label,
            )

    def test_the_probe_pc_parses_back_through_the_frozen_parser(self):
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            fields = LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
            parsed = self.legacy.parse_outer(
                compose_learn_skill_request_probe_pc(self.legacy, fields)
            )
            self.assertEqual(
                parsed.nested_id, LEARN_SKILL_REQUEST_VITAL_ID, label,
            )
            self.assertEqual(
                parsed.nested_version,
                LEARN_SKILL_REQUEST_VITAL_VERSION,
                label,
            )
            self.assertEqual(
                decode_learn_skill_request_payload(parsed.nested_payload),
                fields,
                label,
            )


class RoundTripTests(_LegacyCase):
    def test_encode_then_decode_is_identity_at_the_width_edges(self):
        for fields in (
            LearnSkillRequestFields(0, 0),
            LearnSkillRequestFields(1, 255),
            LearnSkillRequestFields(0xFFFFFFFF, 0),
            LearnSkillRequestFields(0xFFFFFFFF, 0xFF),
            LearnSkillRequestFields(0x80000000, 0x80),
        ):
            payload = encode_learn_skill_request_payload(self.legacy, fields)
            self.assertEqual(
                decode_learn_skill_request_payload(payload), fields,
            )

    def test_decode_accepts_bytearray_and_returns_the_frozen_type(self):
        payload = bytearray(
            encode_learn_skill_request_payload(
                self.legacy, LearnSkillRequestFields(7, 9),
            )
        )
        fields = decode_learn_skill_request_payload(payload)
        self.assertIs(type(fields), LearnSkillRequestFields)
        self.assertEqual(fields, LearnSkillRequestFields(7, 9))


class FailClosedTests(_LegacyCase):
    def assert_decode_refuses(self, payload, reason):
        self.assertIn(reason, LEARN_SKILL_REQUEST_REJECTIONS)
        with self.assertRaises(ValueError) as caught:
            decode_learn_skill_request_payload(payload)
        self.assertEqual(
            str(caught.exception), "learn skill request rejected: " + reason,
        )

    def assert_encode_refuses(self, fields, reason):
        self.assertIn(reason, LEARN_SKILL_REQUEST_REJECTIONS)
        with self.assertRaises(ValueError) as caught:
            encode_learn_skill_request_payload(self.legacy, fields)
        self.assertEqual(
            str(caught.exception), "learn skill request rejected: " + reason,
        )

    def test_non_bytes_payloads_refuse(self):
        for payload in (None, 7, "1401020304 0b05", [0x14], object()):
            self.assert_decode_refuses(payload, "truncated_payload")

    def test_every_truncation_refuses(self):
        good = _payload_bytes(LearnSkillRequestFields(0x01020304, 0x05))
        for cut in range(len(good)):
            self.assert_decode_refuses(good[:cut], "truncated_payload")

    def test_a_wrong_u32_tag_refuses(self):
        good = _payload_bytes(LearnSkillRequestFields(1, 1))
        self.assert_decode_refuses(
            bytes([good[0] ^ 0x01]) + good[1:], "wrong_u32_tag",
        )

    def test_a_wrong_u8_tag_refuses(self):
        good = _payload_bytes(LearnSkillRequestFields(1, 1))
        self.assert_decode_refuses(
            good[:5] + bytes([good[5] ^ 0x01]) + good[6:], "wrong_u8_tag",
        )

    def test_trailing_bytes_refuse(self):
        good = _payload_bytes(LearnSkillRequestFields(1, 1))
        for extra in (b"\x00", b"\x14\x01\x02\x03\x04", good):
            self.assert_decode_refuses(
                good + extra, "trailing_bytes_after_object",
            )

    def test_no_partial_result_survives_a_refusal(self):
        good = _payload_bytes(LearnSkillRequestFields(0xDEADBEEF, 0x7F))
        for bad in (good[:6], good + b"\x00"):
            with self.assertRaises(ValueError):
                decode_learn_skill_request_payload(bad)

    def test_the_encoder_refuses_non_int_members(self):
        for fields in (
            LearnSkillRequestFields("1", 0),
            LearnSkillRequestFields(0, "1"),
            LearnSkillRequestFields(True, 0),
            LearnSkillRequestFields(0, False),
            LearnSkillRequestFields(1.0, 0),
        ):
            self.assert_encode_refuses(
                fields, "request_value_type_not_integer",
            )
        self.assert_encode_refuses(
            (1, 2), "request_value_type_not_integer",
        )

    def test_the_encoder_refuses_members_outside_their_width(self):
        for fields in (
            LearnSkillRequestFields(-1, 0),
            LearnSkillRequestFields(1 << 32, 0),
            LearnSkillRequestFields(0, -1),
            LearnSkillRequestFields(0, 256),
        ):
            self.assert_encode_refuses(
                fields, "request_value_outside_field_width",
            )


class ClassifierTests(_LegacyCase):
    def _parsed(self, *, payload=None, outer_id=None, outer_version=0,
                nested_id=None, nested_version=None):
        legacy = self.legacy
        if payload is None:
            payload = _payload_bytes(LearnSkillRequestFields(5, 6))
        outer = (
            legacy.GSCN_RUNTIME_PROTOCOL_REQ if outer_id is None else outer_id
        )
        nested = (
            LEARN_SKILL_REQUEST_VITAL_ID if nested_id is None else nested_id
        )
        nver = (
            LEARN_SKILL_REQUEST_VITAL_VERSION if nested_version is None
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

    def test_the_exact_request_classifies_as_accepted(self):
        self.assertEqual(
            classify_learn_skill_request_attempt(self.legacy, self._parsed()),
            "exact_request",
        )

    def test_wrong_envelopes_classify_as_wrong_envelope(self):
        for parsed in (
            self._parsed(outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
            self._parsed(outer_version=1),
            self._parsed(nested_version=1),
        ):
            self.assertEqual(
                classify_learn_skill_request_attempt(self.legacy, parsed),
                "wrong_envelope",
            )

    def test_body_refusals_classify_by_their_named_reason(self):
        good = _payload_bytes(LearnSkillRequestFields(5, 6))
        for payload, reason in (
            (good[:4], "truncated_payload"),
            (bytes([good[0] ^ 0x01]) + good[1:], "wrong_u32_tag"),
            (good[:5] + bytes([good[5] ^ 0x01]) + good[6:], "wrong_u8_tag"),
            (good + b"\x00", "trailing_bytes_after_object"),
        ):
            self.assertEqual(
                classify_learn_skill_request_attempt(
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
        scenario = load_learn_skill_request_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(
            scenario.scenario_id, LEARN_SKILL_REQUEST_SCENARIO_ID,
        )
        self.assertEqual(
            scenario.hypothesis_id, LEARN_SKILL_REQUEST_HYPOTHESIS_ID,
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
        ]
        for name, edit in edits:
            tampered = json.loads(json.dumps(data))
            edit(tampered)
            path = Path(self.tmp.name) / f"{name}.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError, msg=name):
                load_learn_skill_request_hypothesis_scenario(path)

    def test_other_scenario_files_are_refused_by_name(self):
        for name in (
            "learn_skill_result_hypothesis_learn_sweep.json",
            "stats_progression_hypothesis_xp_sweep.json",
        ):
            with self.assertRaises(ValueError):
                load_learn_skill_request_hypothesis_scenario(
                    ROOT / "scenarios" / name,
                )
        with self.assertRaises(ValueError):
            load_learn_skill_request_hypothesis_scenario(
                Path(self.tmp.name) / "nope.json",
            )

    def test_a_lookalike_scenario_object_is_refused(self):
        scenario = load_learn_skill_request_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(),
            None,
            replace(scenario, hypothesis_id="HYP-PF-033"),
            replace(scenario, scenario_id="learn_skill_request_other"),
            replace(scenario, response_policy="reply_with_result"),
        ):
            with self.assertRaises(ValueError):
                require_learn_skill_request_hypothesis_scenario(bad)

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        # The two importers are named and the list is exact, so a third one
        # shows up here as a failure -- the containment shape every sibling
        # lane pins.  connection.py, scenario.py and the frozen v141 module
        # know nothing about any of it.
        module = "learn_skill_request_hypothesis"
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
        self.assertNotIn("0x36AA", legacy_source)
        self.assertNotIn("0x36aa", legacy_source)

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if learn_skill_request_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "learn_skill_request_hypothesis_scenario is not None\n"
            "                and nested_id == LEARN_SKILL_REQUEST_VITAL_ID",
            source,
        )
        self.assertEqual(
            source.count("_dispatch_learn_skill_request_hypothesis"), 2,
        )

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--learn-skill-request-hypothesis-scenario", source)
        self.assertIn(
            "'--learn-skill-request-hypothesis-scenario requires an explicit '\n"
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
            if entry["id"] != LEARN_SKILL_REQUEST_HYPOTHESIS_ID:
                continue
            self.assertEqual(entry["status"], "active")
            self.assertIs(entry["production_allowed"], False)
            self.assertEqual(
                entry["introduced_checkpoint"], "LEARN-SKILL-REQUEST-001",
            )
            self.assertIn("b9948741", entry["provenance"])
            self.assertIn("PF_SERIALIZER_FIELDS.tsv", entry["provenance"])
            return
        self.fail(
            "HYP-PF-034 is not registered in docs/HYPOTHESIS_LEDGER.json"
        )

    def test_the_coverage_row_stays_in_progress_not_runtime_pass(self):
        raw = json.loads(
            (ROOT / "docs" / "FUNCTIONAL_COVERAGE.json").read_text(
                encoding="utf-8",
            )
        )
        for domain in raw["domains"]:
            for cap in domain["capabilities"]:
                if cap["id"] != "skill_use":
                    continue
                self.assertEqual(cap["status"], "in_progress")
                self.assertIn(
                    "tests/test_learn_skill_request_hypothesis.py",
                    cap["test_refs"],
                )
                self.assertIn(
                    "scenarios/learn_skill_request_hypothesis_decode_probe"
                    ".json",
                    cap["evidence_refs"],
                )
                return
        self.fail("combat/skill_use row is missing from the coverage matrix")

    def test_the_module_never_calls_the_result_composer(self):
        # No learn rule and no reply: the decode lane must not import or
        # call anything from the sibling result-vital lane, in either the
        # module or its dispatch method.
        module_source = (
            SRC_ROOT / "learn_skill_request_hypothesis.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("learn_skill_result", module_source)
        runtime_tree = ast.parse(
            (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        )
        for node in ast.walk(runtime_tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_dispatch_learn_skill_request_hypothesis"
            ):
                body_dump = ast.dump(node)
                self.assertNotIn("learn_skill_result", body_dump)
                self.assertNotIn("make_learn_skill_result", body_dump)
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
        self.scenario = load_learn_skill_request_hypothesis_scenario(
            SCENARIO_PATH
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, probe=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            learn_skill_request_hypothesis_scenario=(
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
                compose_learn_skill_request_probe_pc(
                    self.legacy, LEARN_SKILL_REQUEST_PROBE_FIELDS[label],
                )
            )
        legacy = self.legacy
        return legacy.parse_outer(bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, LEARN_SKILL_REQUEST_VITAL_ID)
            + legacy.u8tag(0x0B, LEARN_SKILL_REQUEST_VITAL_VERSION)
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

    def test_an_accepted_request_is_decoded_counted_and_unanswered(self):
        state = self._state("req01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._request("MID"))
        self.assertEqual(actions, [])
        self.assertEqual(state.learn_skill_request_accepted_count, 1)
        self.assertEqual(
            state.learn_skill_request_last_fields, (1000001, 11),
        )
        self.assertIn(ACCEPT_EVENT, state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_each_probe_decodes_to_its_declared_pair(self):
        state = self._state("req-values")
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            fields = LEARN_SKILL_REQUEST_PROBE_FIELDS[label]
            self.assertEqual(state.dispatch(self._request(label)), [])
            self.assertEqual(
                state.learn_skill_request_last_fields,
                (fields.request_u32_0x14, fields.request_u8_0x18),
                label,
            )
        self.assertEqual(state.learn_skill_request_accepted_count, 3)
        self.assertEqual(state.events.count(ACCEPT_EVENT), 3)

    def test_the_lane_writes_nothing_to_the_database(self):
        state = self._state("req-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        for label in LEARN_SKILL_REQUEST_PROBE_ORDER:
            state.dispatch(self._request(label))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.learn_skill_request_accepted_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("req-nowrite-refused")
        before = self.db_path.read_bytes()
        good = _payload_bytes(LearnSkillRequestFields(5, 6))
        for payload in (good[:4], good + b"\x00"):
            self.assertEqual(
                state.dispatch(self._request(payload=payload)), [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.learn_skill_request_accepted_count, 0)
        self.assertIsNone(state.learn_skill_request_last_fields)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(ACCEPT_EVENT, state.events)
        self.assertEqual(state.learn_skill_request_accepted_count, 0)

    def test_every_body_refusal_family_is_silent_with_a_named_event(self):
        good = _payload_bytes(LearnSkillRequestFields(5, 6))
        for payload, reason in (
            (good[:4], "truncated_payload"),
            (bytes([good[0] ^ 0x01]) + good[1:], "wrong_u32_tag"),
            (good[:5] + bytes([good[5] ^ 0x01]) + good[6:], "wrong_u8_tag"),
            (good + b"\x00", "trailing_bytes_after_object"),
        ):
            state = self._state("req-" + reason.replace("_", "")[:10])
            self._assert_silent(
                state, self._request(payload=payload),
                f"learn_skill_request_hypothesis_{reason}_no_reply",
            )

    def test_a_wrong_envelope_is_silent_with_a_named_event(self):
        state = self._state("req-envelope")
        legacy = self.legacy
        payload = _payload_bytes(LearnSkillRequestFields(5, 6))
        pc = bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 1)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, LEARN_SKILL_REQUEST_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
            + payload
        )
        self._assert_silent(
            state, legacy.parse_outer(pc),
            "learn_skill_request_hypothesis_wrong_envelope_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("req-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertEqual(state.dispatch(self._request("MID")), [])
        self.assertIn(
            "learn_skill_request_hypothesis_no_selected_no_reply",
            state.events,
        )
        self.assertEqual(state.learn_skill_request_accepted_count, 0)

    def test_a_not_yet_ready_sequence_fails_closed(self):
        state = self._state("req-sequence", ready=False)
        self._assert_silent(
            state, self._request("MID"),
            "learn_skill_request_hypothesis_wrong_sequence_no_reply",
        )

    # ----- containment -----------------------------------------------------

    def test_without_the_scenario_the_branch_does_not_exist(self):
        # Proven by COMPARISON, not by absence: the lane-off state and a
        # plain no-scenario baseline state (make_state_class with no lane
        # kwargs at all) must produce the same actions and the same new
        # events for the same 0x36AA frame -- that is what "falls through to
        # the frozen path exactly as before this module existed" means.
        state = self._state("req-absent", probe=False)
        baseline_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        baseline = baseline_type("req-absent-base")
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
        self.assertEqual(state.learn_skill_request_accepted_count, 0)
        self.assertIsNone(state.learn_skill_request_last_fields)
        for event in state.events:
            self.assertNotIn("learn_skill_request_hypothesis", event)


class SourceHygieneTests(unittest.TestCase):
    def test_the_module_is_ascii_and_survives_the_bridge_console_encoding(self):
        source = (
            SRC_ROOT / "learn_skill_request_hypothesis.py"
        ).read_text(encoding="utf-8")
        source.encode("ascii")
        source.encode("cp874")

    def test_this_test_file_is_ascii_and_survives_the_bridge_console(self):
        source = Path(__file__).read_text(encoding="utf-8")
        source.encode("ascii")
        source.encode("cp874")


if __name__ == "__main__":
    unittest.main()
