"""Pin the Foundation/legacy seam and the evidence manifests that back the matrix.

M13 established three facts that nothing in the suite was watching:

  1. The Foundation server is not an alternative to the frozen V141 scenario
     runner.  ``app.py`` loads ``current/pf_login_game_server_v141.py`` and
     ``runtime.make_state_class`` returns a subclass of ``legacy.GameSessionState``
     that calls ``super().dispatch()`` for everything it does not override.  A
     ``runtime_pass`` produced by a Foundation process therefore does not imply
     that Foundation code produced the behavior.
  2. The five opt-in scenario modes are mutually exclusive, so no single server
     run can exhibit every green row, and the launcher used by the playbook
     enables none of them.
  3. Every ``reports/*.manifest`` line still hashes to its recorded sha256, but
     four ``runtime_pass`` rows cite no manifest-backed report at all.

These tests freeze that state.  They are deliberately structural: they assert
what the seam *is*, not that any particular capability works.  A change that
re-points the legacy module, flattens the subclass, makes the modes composable,
or grows the manifest-debt list has to say so in the same commit.
"""

import ast
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
REPORTS = ROOT / "reports"
COVERAGE = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.runtime import make_state_class  # noqa: E402

# The frozen module the Foundation server is built on.  Changing this pin means
# the whole evidence base moves to a different legacy baseline.
PINNED_LEGACY_MODULE = "current/pf_login_game_server_v141.py"

# The five strictly opt-in scenario parameters of make_state_class.  At most one
# may be active in a run; see test_scenario_modes_are_mutually_exclusive.
SCENARIO_MODES = (
    "scenario",
    "scene_load_scenario",
    "population_scenario",
    "item_move_capture_scenario",
    "item_move_hypothesis_scenario",
)

# Rows graded runtime_pass whose evidence has no .manifest, i.e. whose runtime
# claim rests on report prose rather than on hash-pinned artifacts.  This is
# recorded debt, not an accepted practice: the set may shrink, and shrinking it
# is expected to update this list in the same commit.
MANIFEST_DEBT_RUNTIME_PASS = {
    "movement/npc_locomotion_presentation",
    "movement/teleport_transport",
    "npc_interaction/npc_conversation_handshake",
    "npc_interaction/conversation_operation_sequence",
}

# sha256 over every graded field of every row -- id, status, required, evidence
# refs, test refs, next_missing_behavior, domain_complete -- and nothing else.
# `notes` is excluded on purpose so prose corrections stay cheap while any grade
# movement has to be deliberate.
GRADE_SUBSET_SHA256 = (
    # This pin covers ONE deliberate movement, chief round 78 (2026-08-18):
    # character_management/stats_and_progression gains the STATS-PROG-002 evidence and
    # test refs (status already in_progress, unchanged, and deliberately NOT moved to
    # runtime_pass). evidence_refs
    # reports/PF_STATS_PROG002_SERVER_ENCODER_20260818.md and
    # scenarios/stats_progression_hypothesis_xp_sweep.json, test_refs
    # tests/test_stats_progression_hypothesis.py and
    # tests/test_stats_progression_dispatch.py. STATS-PROG-001 measured the gap at
    # nineteen named progression fields, two emitted, zero decoded; this milestone moves
    # the FIELD half of it. src/pirateforce_foundation/stats_progression_hypothesis.py is
    # a generic mask-driven ActorAttr encoder/decoder over 23 fields in the three chained
    # blocks, emitting in ascending mask-bit order -- which is read off the report rather
    # than assumed, because STATS-PROG-001 records a gate-test address per gated field and
    # those addresses ascend strictly with the bits in both tables. The encoder is pinned
    # externally, not self-certified: for the baseline field set it reproduces
    # player_wire.make_actor_attr_with_name byte for byte (73 bytes), a hand-written
    # projection a real client has accepted since NAME-002, and that check runs on every
    # composition. A new opt-in scenario plus the new --stats-progression-hypothesis-scenario
    # flag (explicit --db, mutually exclusive with every other mode including the two chat
    # lanes, which key on the same trigger vital) wires it into runtime.py: one accepted
    # ascii12 frame is a TRIGGER (nothing in it is read) answered with nine UpdateAttrVital
    # 0x309A frames 3.0 s apart -- baseline, exp 1234, exp 987654, level 7, then
    # STR/CON/DEX/INT/PER = 11/22/33/44/55 one at a time, cumulative because V141 records
    # that the client's ActorAttr apply 0x464F30 copies the incoming object whole. Proven on
    # dispatched bytes: nine actions in order, every Attr body at the fixed offset 31
    # re-decoding to the declared cumulative field set, all 27 per-step hashes matching the
    # scenario pins, eighteen frames for two requests with no accumulated state, database
    # byte-identical across accepted and refused windows. The ledger GROWS: HYP-PF-020
    # appended, count 26 -> 27, every existing index stable. NOT runtime_pass: no client has
    # seen one of these frames and no progression field has ever been on this project's wire
    # in either direction -- that is GT-017, attended, unblocked but unanswered. No other
    # lane's module, scenario or test was touched; tests/test_presentation_ownership.py and
    # the STATS-PROG-001 static guards needed no change (the new module spells neither the
    # chat vital id nor any of the five progression verb names).
    # Previous pin B6002E45..E1F3 (round 77) covered ONE deliberate movement:
    # chat/chat_channels_and_routing gains the CHAT-CHANNEL-003 evidence and test
    # refs (status already in_progress, unchanged, and deliberately NOT moved to
    # runtime_pass). evidence_refs
    # reports/PF_CHAT_CHANNEL003_DISPATCH_HOOKUP_HEADLESS_20260818.md and
    # scenarios/channel_message_hypothesis_channel_sweep.json, test_ref
    # tests/test_channel_message_dispatch.py. This is the dispatch hookup
    # CHAT-CHANNEL-002 withheld on purpose: the codec existed but nothing could
    # put a byte on the wire, so GT-016 was unblocked on paper and BLOCKED in
    # practice. A second opt-in scenario file plus the new
    # --channel-message-hypothesis-scenario flag (explicit --db required, mutually
    # exclusive with every other mode including --chat-input-hypothesis-scenario,
    # which keys on the same vital id) wires the lane into runtime.py: one
    # accepted 34-byte ascii12 0xAC52 frame, under the unchanged selected +
    # runtime-ready guards, is DECODED (not spliced) and answered with five
    # composed frames -- LocalTalk, Party, Guild, GMGlobal, ActorBoardcast -- 3.0 s
    # apart. Proven on dispatched bytes: five actions in pinned order, the five
    # nested payloads identical byte for byte (empty speaker by policy, one
    # sha256), the five 56-byte PCs differing in exactly the two bytes pc[16:18],
    # all ten per-channel hashes matching the scenario pins, ten frames for two
    # requests with no accumulated state, the database file byte-identical across
    # accepted and refused windows, and every fail-closed family silent with a
    # named event. The ledger does NOT grow: HYP-PF-019 is amended in place,
    # tracked_versions CHAT-CHANNEL-002 -> +CHAT-CHANNEL-003, count stays 26.
    # Note: tests/test_channel_message_hypothesis.py's containment test, which
    # asserted that NO runtime module imports the lane, was deliberately rewritten
    # in the same commit -- that assertion is precisely what this milestone had to
    # break. It was not worked around: no hidden id, no derived name, no lazy
    # import. The rewritten guard pins an exact importer list (app.py, runtime.py),
    # keeps connection.py/scenario.py clean, and requires every runtime mention to
    # sit inside the scenario gate. tests/test_presentation_ownership.py needed no
    # change: its chat-vital allowlist already covered both modules from round 76.
    # Previous pin CB3ADB10..F404 (round 76) covered two deliberate movements.
    # Unlike round 75 these are NOT both report-only: the ledger moves 25 -> 26.
    #  1. character_management/stats_and_progression not_started -> in_progress
    #     with STATS-PROG-001 (report-only static). evidence_ref
    #     reports/PF_STATS_PROG001_CHARACTER_STATS_AND_PROGRESSION_STATIC_20260818.md
    #     and test_ref tests/test_stats_progression_static.py. Fourteen attribute
    #     classes, every id derived from its in-image name literal by
    #     PF-NAMEID-HASH-001 and anchored on the three the delivered V141 snapshot
    #     already hardcodes (ActorAttr 0x12AD, NPCAttr 0x0AD5, UpdateAttrVital
    #     0x309A). Nineteen progression fields are named with an in-binary consumer
    #     each -- level BasicAttr u16 +0x5E (GetLv 0x460050), experience ActorAttr
    #     qword +0xA0 (XP bar 0x519299), the five ability u16 at +0x82..+0x8A and
    #     their bonuses at +0x182..+0x18A (LABEL_STR..PER getters), skill point
    #     +0x7C, unspent points +0x80, class +0x8C, HP/MP pairs on BasicAttr -- all
    #     mask-gated through UpdateAttrVital 0x309A. Five progression verbs pinned,
    #     of which AbilityDepolyAll 0x36AD is proven end to end (UP button ->
    #     pending counter -> five i16 tag 0x0F in STR,CON,DEX,INT,PER order).
    #     Evidenced negatives: the AddExp/AddAbilityPoint/AddSkillPoint script
    #     bindings only broadcast an in-process event through 0x5F9C70 and can grant
    #     nothing; Attribute 0x1306 and FightAttr 0x1285 have no wire fields at all
    #     (serializer slot is a bare ret 8 at 0x515EC0); and the curve numbers are
    #     not in the executable -- only column names and lookup code. Server gap:
    #     fourteen classes, zero ids in V141; nineteen progression fields, two
    #     emitted, zero decoded; five verbs, zero encoders and zero dispatch. Status
    #     is in_progress and NOT runtime_pass: no capture has ever carried a
    #     progression field. The POTENTIAL column-to-offset binding is NOT claimed
    #     (AGILITY<->DEX is cardinality inference, not a byte proof).
    #  2. chat/chat_channels_and_routing gains the CHAT-CHANNEL-002 evidence and
    #     test refs (status already in_progress, unchanged): evidence_refs
    #     reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md and
    #     scenarios/channel_message_hypothesis_shared_serializer.json, test_ref
    #     tests/test_channel_message_hypothesis.py. This one carries a ledger entry,
    #     HYP-PF-019 (ledger 25 -> 26): the shared serializer 0x65AD40 implemented
    #     both directions over the five channels that share it, with the five ids
    #     derived from the name hash at import rather than transcribed. The decode
    #     is pinned externally, not self-certified -- re-encoding the decoded GT-006
    #     capture reproduces both 34-byte payloads byte-for-byte AND reproduces the
    #     PC/frame sha256 that HYP-PF-014 pinned through a path that never parsed
    #     anything, plus the CHAT-ECHO-002 46/68/79-byte pins. Across all five
    #     channels the composed PC differs in exactly two bytes (pc[16:18] = class
    #     id), re-proving CHAT-CHANNEL-001's channel-id-is-the-selector conclusion on
    #     server-produced bytes. Opt-in only, production_allowed false, no DB write,
    #     not imported by runtime/app/connection/scenario. Whisper 0x556C is rejected
    #     on purpose (third wstring + result byte = different schema). Only 0xAC52
    #     has ever been on this project's wire: the other four channels' pins say
    #     what the bytes would be, NOT that they were observed. GT-016 unblocked.
    #     Note: tests/test_presentation_ownership.py's chat-vital allowlist grew
    #     from two modules to three in the same commit. That was deliberate and was
    #     not avoided -- deriving the id from the hash at import would have kept the
    #     scanner green while leaving the repo asserting something false.
    # Previous pin 70E1668D..48BD (round 75) recorded two deliberate movements, both
    # report-only static characterizations that left the ledger at 25:
    #  1. inventory/use_drop_sell not_started -> in_progress with USE-DROP-SELL-001.
    #     evidence_ref
    #     reports/PF_USE_DROP_SELL001_ITEM_OPERATE_USE_DROP_SELL_STATIC_20260818.md
    #     and test_ref tests/test_use_drop_sell_static.py. Byte-exact from the client
    #     binary: neither use nor sell rides ItemOperate. USE is its own class
    #     UseItemVital (vtable 0xF30950, single registration 0xBEE600 -> id-slot
    #     0x1082030, get-id 0x5BEA50) whose serializer 0x6C0180 emits one qword
    #     (tag 0x32) and nothing else; SELL is the Stall/BlackMarket/ItemMall system,
    #     whose StallOperateVital serializer 0x76A630 is a priced wire. No ItemOperate
    #     producer references any vendor/price string, retiring the sell-N candidate
    #     SPLIT-OPERATE-002 left open. op3's single caller 0x5B9D0C is a dialog
    #     callback (never e8-called; registered via 0x405D40 into dialog+0x12CC) that
    #     fires only on confirm: identity-only, no quantity, destination or
    #     counterparty. Server has no handler for op3, op6 or USE_ITEM_VITAL 0x1F4F,
    #     and the one shop route TradeCmdVital 0x23B5 is buy-only, so status stays
    #     in_progress. Which verb is literally drop/discard/destroy is NOT claimed.
    #  2. chat/chat_channels_and_routing not_started -> in_progress with
    #     CHAT-CHANNEL-001. evidence_ref
    #     reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md
    #     and test_ref tests/test_chat_channel_family_static.py. The seventeen
    #     Channel_*Vital classes register from one contiguous block
    #     0xBF72B0..0xBF74F0 in PF-NAMEID-HASH-001 shape, so every channel id derives
    #     from its in-image name literal; the anchor holds exactly
    #     (Channel_LocalTalkMessageVital = 0xAC52, the id GT-006 captured on the
    #     wire), no id is ever a code immediate once E8/E9 AND 0F 8x rel32 tails are
    #     excluded, and two independent naming routes converge 17/17. Recipient
    #     resolution is decoded: Whisper alone carries a third wstring
    #     (Serialize 0x65AEA0, recipient@+0x50) plus a u8 result code @+0x6C. Five
    #     channels share base serializer 0x65AD40, so the channel identifier IS the
    #     16-bit class id, not a payload selector, and the 34-byte GT-006 payload
    #     parses with zero bytes left over. Server carries no Channel_ token and none
    #     of the seventeen ids: seventeen client-side, one touched, zero decoded. The
    #     original server's fan-out/membership behaviour still needs two concurrent
    #     sessions, so this is NOT runtime_pass.
    # Previous pin C98EB5B8..B58C (rounds 73-74) recorded
    #  0. movement/remote_player_movement_projection not_started -> in_progress
    #     with MOVE-PROJECT-001. evidence_ref
    #     reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md
    #     and test_ref tests/test_remote_movement_projection_static.py. It
    #     characterizes byte-exact, from the read-only client binary cross-checked
    #     against the read-only server source, the transport a remote actor's
    #     movement projection rides -- MovementAttr 0x2067 inside every remote-actor
    #     entry of the RuntimeRes actor stream: runtime-assigned id wall (name
    #     @0xF0E840, single registration 0xBD9410 -> id-slot 0x10334A8, 0x2067 never
    #     a code immediate, one get-id stub 0x43BBB0), vtable 0xF0D0F8 (+0x2C delta
    #     0x467040, +0x30 apply/merge 0x467130, +0x34 Serial 0x4671C0), the
    #     mask-gated sparse wire schema (submask u8 + identity qword(0x32) + field
    #     mask u8, then per-bit pos vec3/heading f32/mode u8/flags u32(0x26)/three
    #     f32) matching make_remote_movement_attr byte-exact, and the projection
    #     apply/merge that completes a sparse delta against existing projected state
    #     (copies only fields whose target-mask bit is NOT set). Server only ever
    #     emits remote actors of actor_type 4 (CNetNPC): no authentic remote
    #     human-PLAYER capture exists, so status stays in_progress (interest
    #     management, cadence, interpolation uncaptured; not runtime_pass).
    #     Report-only additive: no server behavior changed; ledger stays 25. The
    #     movement domain has no not_started rows left; next_missing_behavior stays
    #     remote_player_movement_projection (first row still short of runtime_pass).
    # Previous pin 0F705C08..C4F8 (round 72) recorded
    # movement/local_player_movement_authority not_started -> in_progress with
    # MOVE-AUTHORITY-001 (TargetPosVital 0x2A90 producer + wire schema, server
    # accepts-as-given gap); E04F22D1..CCE8 (round 71) recorded inventory/stack_merge_and_limit
    # gaining the ITEM-MERGE-001 (HYP-PF-018) evidence/test refs; 594DEB56..DCF5
    # (round 69) recorded split_stack's second evidence set (SPLIT-OPERATE-002;
    # round 70 touched notes prose only so the digest held); 3A78B4B6..A766
    # (round 68) recorded split_stack not_started -> in_progress with
    # SPLIT-OPERATE-001; CF031345..BC3B (round 67) recorded
    # inventory/move_negative_paths isolation (MOVE-ISOLATION-001); 35082475..E228C0
    # (round 66) same_slot_noop blocked -> runtime_pass under HYP-PF-010;
    # 26D752FE..BA9A (round 65) occupied_destination_policy not_started ->
    # in_progress under HYP-PF-017 (ITEM-SWAP-001); see its lineage note before that
    # for round 53's 78558E56..6DC8.
    "0C16D38678FBF08312804AA127A9518FE747418D57F943EFE636EC096BE6FE90"
)



# Two manifest formats exist in reports/.  PIPE is the house format used by 21 of
# the 22 manifests; COLUMNS is a single earlier file whose paths are relative to
# its capture root rather than to the repository.  Both are accepted, but the
# COLUMNS set is pinned so a new report cannot quietly reintroduce the old shape.
MANIFEST_PIPE = re.compile(r"^(?P<path>[^|]+)\|(?P<size>\d+)\|(?P<sha>[0-9A-F]{64})$")
MANIFEST_COLUMNS = re.compile(r"^(?P<sha>[0-9A-F]{64})\s+(?P<size>\d+)\s+(?P<path>\S.*)$")

LEGACY_FORMAT_MANIFESTS = {
    "PF_RELATION_COMPARATOR_RUNTIME_TRACE_20260815.manifest",
}


def grade_subset(document):
    """Every field the matrix grades on, in file order, excluding prose."""
    return [
        (
            domain["id"],
            domain.get("domain_complete"),
            [
                (
                    row["id"],
                    row["status"],
                    row["required"],
                    tuple(row["evidence_refs"]),
                    tuple(row["test_refs"]),
                    row.get("next_missing_behavior"),
                )
                for row in domain["capabilities"]
            ],
        )
        for domain in document["domains"]
    ]


def grade_digest(document):
    payload = json.dumps(grade_subset(document), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def parse_manifest(text, pattern=MANIFEST_PIPE):
    """Return parsed rows, or raise ValueError naming the first bad line."""
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if match is None:
            raise ValueError(f"line {number} does not match the manifest format: {line!r}")
        rows.append((match["path"], int(match["size"]), match["sha"]))
    return rows


def parse_any_manifest(path):
    pattern = MANIFEST_COLUMNS if path.name in LEGACY_FORMAT_MANIFESTS else MANIFEST_PIPE
    return parse_manifest(path.read_text(encoding="utf-8"), pattern)


def modules_mentioning(root, pattern):
    found = []
    for path in sorted(Path(root).glob("*.py")):
        if re.search(pattern, path.read_text(encoding="utf-8")):
            found.append(path.name)
    return found


class FoundationLegacySeamTests(unittest.TestCase):
    """The architectural facts behind every runtime_pass grade."""

    def test_app_pins_exactly_one_frozen_legacy_module(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        pins = re.findall(r"current/pf_login_game_server_v\d+\.py", source)
        self.assertEqual(pins, [PINNED_LEGACY_MODULE])
        self.assertTrue((ROOT / PINNED_LEGACY_MODULE).is_file())

    def test_app_loads_the_legacy_module_rather_than_importing_a_package(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("load_legacy(", source)
        # A plain import would make the frozen script a build-time dependency and
        # silently change which copy runs.
        self.assertNotIn("import pf_login_game_server", source)

    def test_the_foundation_state_class_subclasses_frozen_v141(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "PersistentGameSessionState"
        ]
        self.assertEqual(len(classes), 1)
        bases = [ast.unparse(base) for base in classes[0].bases]
        self.assertEqual(bases, ["legacy.GameSessionState"])

    def test_dispatch_still_falls_through_to_the_frozen_implementation(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        # If this ever drops to zero, Foundation stopped relaying legacy actions
        # and every passthrough row in the coverage matrix needs re-grading.
        self.assertGreater(source.count("super().dispatch(parsed)"), 0)

    def test_scenario_modes_are_mutually_exclusive(self):
        for first in range(len(SCENARIO_MODES)):
            for second in range(first + 1, len(SCENARIO_MODES)):
                kwargs = {
                    SCENARIO_MODES[first]: object(),
                    SCENARIO_MODES[second]: object(),
                }
                with self.subTest(modes=(SCENARIO_MODES[first], SCENARIO_MODES[second])):
                    with self.assertRaises(ValueError) as raised:
                        make_state_class(None, None, None, **kwargs)
                    self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_single_mode_is_never_refused_for_being_exclusive(self):
        """The exclusion must reject pairs, not reject scenarios generally.

        Three of the five modes run their own allowlist validator that also
        raises ValueError, so the discriminating signal is the message, not the
        exception type.
        """
        for mode in SCENARIO_MODES:
            with self.subTest(mode=mode):
                try:
                    make_state_class(None, None, None, **{mode: object()})
                except Exception as error:  # noqa: BLE001 - any failure is fine here
                    self.assertNotIn("mutually exclusive", str(error))
                else:
                    self.fail("a bare object cannot produce a usable state class")

    def test_the_visible_launcher_enables_no_scenario_mode(self):
        launcher = (ROOT / "tools" / "run_foundation_visible.ps1").read_text(encoding="utf-8")
        for flag in (
            "--scenario", "--scene-load-scenario", "--population-scenario",
            "--item-move-capture-scenario", "--item-move-hypothesis-scenario",
        ):
            self.assertNotIn(flag, launcher)


class EvidenceManifestTests(unittest.TestCase):
    """Manifests are the only re-checkable link between a claim and bytes."""

    def setUp(self):
        self.manifests = sorted(REPORTS.glob("*.manifest"))

    def test_reports_carry_manifests_at_all(self):
        self.assertGreaterEqual(len(self.manifests), 22)

    def test_every_manifest_line_is_well_formed(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                rows = parse_any_manifest(manifest)
                self.assertTrue(rows, "an empty manifest pins nothing")
                for path, size, _sha in rows:
                    # Zero is legitimate and load-bearing: an empty stderr file is
                    # itself the evidence for several clean-shutdown claims.
                    self.assertGreaterEqual(size, 0)
                    self.assertNotIn("..", path)

    def test_only_the_recorded_manifests_use_the_older_column_format(self):
        odd = set()
        for manifest in self.manifests:
            try:
                parse_manifest(manifest.read_text(encoding="utf-8"), MANIFEST_PIPE)
            except ValueError:
                odd.add(manifest.name)
        self.assertEqual(odd, LEGACY_FORMAT_MANIFESTS)

    def test_no_manifest_pins_the_same_path_twice(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                paths = [row[0] for row in parse_any_manifest(manifest)]
                self.assertEqual(len(paths), len(set(paths)))

    def test_every_manifest_belongs_to_a_report_that_exists(self):
        for manifest in self.manifests:
            with self.subTest(manifest=manifest.name):
                self.assertTrue(manifest.with_suffix(".md").is_file())

    def test_the_parser_rejects_a_damaged_manifest(self):
        """A guard that never fails is not a guard."""
        good = "GameClient/capture_x/server.out.txt|12|" + "A" * 64
        self.assertEqual(len(parse_manifest(good)), 1)
        for damaged in (
            "GameClient/capture_x/server.out.txt|12",                      # no sha
            "GameClient/capture_x/server.out.txt|12|" + "A" * 63,          # short sha
            "GameClient/capture_x/server.out.txt|12|" + "a" * 64,          # lowercase
            "GameClient/capture_x/server.out.txt|-1|" + "A" * 64,          # negative
            "GameClient/capture_x/server.out.txt|12|" + "G" * 64,          # non-hex
            "A" * 64 + "  12  server.out.txt",                             # wrong format
        ):
            with self.subTest(damaged=damaged):
                with self.assertRaises(ValueError):
                    parse_manifest(damaged)

    def test_the_column_parser_rejects_a_pipe_line(self):
        good = "A" * 64 + "  12  server.out.txt"
        self.assertEqual(len(parse_manifest(good, MANIFEST_COLUMNS)), 1)
        with self.assertRaises(ValueError):
            parse_manifest(
                "GameClient/capture_x/server.out.txt|12|" + "A" * 64,
                MANIFEST_COLUMNS,
            )


class CoverageProvenanceTests(unittest.TestCase):
    """Ratchets that keep the M13 findings from being reopened quietly."""

    def setUp(self):
        self.document = json.loads(COVERAGE.read_text(encoding="utf-8"))
        self.rows = {
            f"{domain['id']}/{row['id']}": row
            for domain in self.document["domains"]
            for row in domain["capabilities"]
        }

    def test_grade_fields_match_the_pinned_digest(self):
        self.assertEqual(grade_digest(self.document), GRADE_SUBSET_SHA256)

    def test_the_digest_would_notice_a_single_status_change(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        row = mutated["domains"][0]["capabilities"][0]
        row["status"] = "complete" if row["status"] != "complete" else "blocked"
        self.assertNotEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def test_the_digest_ignores_prose_only_edits(self):
        mutated = json.loads(COVERAGE.read_text(encoding="utf-8"))
        mutated["domains"][0]["capabilities"][0]["notes"] += " (edited)"
        self.assertEqual(grade_digest(mutated), GRADE_SUBSET_SHA256)

    def _manifest_debt(self):
        debt = set()
        for key, row in self.rows.items():
            if row["status"] != "runtime_pass":
                continue
            backed = any(
                (ROOT / ref).with_suffix(".manifest").is_file()
                for ref in row["evidence_refs"]
            )
            if not backed:
                debt.add(key)
        return debt

    def test_manifest_debt_matches_the_recorded_list(self):
        self.assertEqual(self._manifest_debt(), MANIFEST_DEBT_RUNTIME_PASS)

    def test_every_recorded_debt_row_still_exists_and_is_runtime_pass(self):
        for key in MANIFEST_DEBT_RUNTIME_PASS:
            with self.subTest(row=key):
                self.assertIn(key, self.rows)
                self.assertEqual(self.rows[key]["status"], "runtime_pass")

    def test_the_system_message_row_records_its_legacy_ownership(self):
        notes = self.rows["chat/server_system_message"]["notes"]
        self.assertIn("no Foundation module owns it", notes)
        self.assertNotIn("has no offline test", notes)
        self.assertTrue(self.rows["chat/server_system_message"]["test_refs"])

    def test_no_foundation_module_emits_the_legacy_system_message(self):
        self.assertEqual(modules_mentioning(SRC_ROOT, r"ShowMessage"), [])
        legacy = (ROOT / PINNED_LEGACY_MODULE).read_text(encoding="utf-8")
        self.assertIn("V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE", legacy)

    def test_the_source_scanner_would_notice_a_module_that_emitted_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "clean.py").write_text("nothing to see\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), [])
            (root / "chat.py").write_text("SHOW = legacy.ShowMessage\n", encoding="utf-8")
            self.assertEqual(modules_mentioning(root, r"ShowMessage"), ["chat.py"])


if __name__ == "__main__":
    unittest.main()
