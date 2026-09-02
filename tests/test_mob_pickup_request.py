"""MOB-PICKUP-REQUEST-001 -- the production reader of an inbound pickup ask.

WHAT THESE TESTS ARE FOR.  The lane under test turns seven inbound bytes
into two numbers or into a named refusal, always-on, with no flag and no
scenario object anywhere in its condition.  Three questions decide whether
it is worth landing:

  1. Does it read the shape the committed delivery table declares, and does
     an INDEPENDENT derivation of those same bytes agree with it?  (The
     module deliberately keeps one decoder; the second derivation lives
     here, where it is executed on every run -- see the module docstring.)
  2. Does every registered refusal actually happen, from a byte string a
     stranger could send, through the public entry point?
  3. Does the line this lane hands the chief RUN -- guards included,
     against real objects, ending with an item in a real database row?

Question 3 is the one that matters most and the one a described paragraph
cannot answer.  It was also the one this file got wrong first: it exec'd
the two CALL lines and left the branch's control flow as prose in the
wiring note, and an adversarial pass then inverted, deleted and emptied
that prose without turning this file red, then crashed the branch-as-prose
with one trailing byte.  The control flow now lives in a function and this
file drives it -- refusals, readiness guards and all -- so a mutation to it
turns this file red rather than turning a round of the chief's red.
"""

import ast
import inspect
import io
import random
import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_SERIALIZER_TABLE  # noqa: E402

from pirateforce_foundation import (  # noqa: E402
    mob_loot,
    mob_pickup,
    mob_pickup_persist,
    mob_pickup_request,
)
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.mob_loot import (  # noqa: E402
    DropLedger,
    DropLedgerCell,
)
from pirateforce_foundation.mob_pickup_request import (  # noqa: E402
    ACCEPTED,
    MOB_PICKUP_REQUEST_REFUSAL_REASONS,
    MobPickupRequestRefused,
    PickupRequestFields,
    PickupRequestRead,
    classify_pickup_request,
    decode_pickup_request_payload,
    pickup_request_console_line,
    read_inbound_pickup_request,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MODULE_SOURCE = (
    ROOT / "src/pirateforce_foundation/mob_pickup_request.py"
).read_text(encoding="utf-8")

ITEM = 2400046
MOB = 0x2068
KILLER = 0x750059
# Far apart on all three axes on purpose: a permutation test that leaves two
# coordinates close together cannot tell a swapped argument from a correct
# one.  The claimant stands ON the drop, so an unpermuted pickup is well
# inside the lane's radius and every permutation is far outside it.
DROP_AT = (1000.0, 20.0, 3000.0)


def _body(object_ref, opaque):
    """One request body, composed the way the delivery table declares it."""
    return (
        bytes([mob_pickup_request.PICKUP_REQUEST_OBJECT_REF_TAG])
        + int(object_ref).to_bytes(4, "little")
        + bytes([mob_pickup_request.PICKUP_REQUEST_OPAQUE_U8_TAG, opaque])
    )


def _pc(legacy, body, *, vital_id=None, vital_version=0, outer_version=0,
        outer_mask=2, vital_count=1, outer_id=None):
    """One full client request PC around a body.

    Every envelope field is a parameter because every one of them is a way
    for a frame to be somebody else's, and the refusal tests drive them one
    at a time.
    """
    if vital_id is None:
        vital_id = mob_pickup_request.PICKUP_REQUEST_VITAL_ID
    if outer_id is None:
        outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
    return bytes(
        legacy.u16tag(0x12, outer_id)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, outer_version)
        + legacy.u8tag(0x0B, outer_mask)
        + legacy.u16tag(0x12, vital_count)
        + legacy.u16tag(0x12, vital_id)
        + legacy.u8tag(0x0B, vital_version)
        + body
    )


def _independent_unpack(payload):
    """The SECOND derivation of the same seven bytes.

    Deliberately not a paraphrase of the module's cursor walk: it asserts
    the whole fixed layout at once with ``struct`` and has no cursor to
    misplace.  It answers only "is this the shape, and what are the values";
    naming WHICH record was wrong stays the walk's job.
    """
    if len(payload) != 7:
        return None
    first_tag, object_ref, second_tag, opaque = struct.unpack("<BIBB", payload)
    if first_tag != 0x14 or second_tag != 0x08:
        return None
    return PickupRequestFields(object_ref, opaque)


def a_drop(key_offset=0, quantity=1):
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, quantity,
        mob_loot.as_wire_float(DROP_AT[0]),
        mob_loot.as_wire_float(DROP_AT[1]),
        mob_loot.as_wire_float(DROP_AT[2]),
        MOB, KILLER,
    )


def a_ground_cell(*drops):
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(DropLedger(tuple(drops), 1, issued, ()))


class LegacyFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def read(self, pc, *, echo=False):
        return read_inbound_pickup_request(
            self.legacy, self.legacy.parse_outer(pc), echo=echo)


# ---------------------------------------------------------------------------
# 1. The shape, and a second derivation of it
# ---------------------------------------------------------------------------

class TheShapeTests(LegacyFixture):
    def test_the_pinned_geometry_is_the_delivery_tables_and_not_a_guess(self):
        """The four symmetric rows, transcribed, with the trap called out.

        The trailing record's tag is 0x08 -- the value the delivery table
        carries twice.  A reader who pattern-matched sibling lanes would
        write 0x0B here, so it is pinned rather than trusted.
        """
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_OBJECT_REF_TAG, 0x14)
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_OPAQUE_U8_TAG, 0x08)
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_OBJECT_REF_OBJECT_OFFSET, 0x14)
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_OPAQUE_U8_OBJECT_OFFSET, 0x18)
        self.assertEqual(mob_pickup_request.PICKUP_REQUEST_PAYLOAD_SIZE, 7)
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_SERIALIZER_LEN,
            mob_pickup_request.PICKUP_REQUEST_SERIALIZER_END_VA
            - mob_pickup_request.PICKUP_REQUEST_SERIALIZER_VA)

    def test_an_accepted_frame_yields_the_two_values_it_carried(self):
        for object_ref, opaque in (
            (0, 0),
            (mob_loot.DROP_KEY_BASE, 1),
            (0x12345678, 42),
            (0xFFFFFFFF, 0xFF),
        ):
            with self.subTest(object_ref=object_ref, opaque=opaque):
                read = self.read(_pc(self.legacy, _body(object_ref, opaque)))
                self.assertTrue(read.accepted)
                self.assertEqual(read.reason, ACCEPTED)
                self.assertEqual(
                    read.fields, PickupRequestFields(object_ref, opaque))

    def test_the_two_derivations_agree_on_every_body_that_matters(self):
        """The module's walk against an independent fixed-layout unpack.

        The corpus is not decorative: every single-byte mutation of an
        accepted body at every position, plus random bodies of every length
        from empty to nine.  Both derivations must accept the same bodies
        and read the same values out of them.
        """
        accepted = _body(0x12345678, 42)
        corpus = [accepted, b"", bytes(7)]
        for position in range(len(accepted)):
            for value in (0x00, 0x08, 0x0B, 0x14, 0xFF):
                corpus.append(
                    accepted[:position] + bytes([value])
                    + accepted[position + 1:])
        corpus.append(accepted[:-1])
        corpus.append(accepted + b"\x00")
        rng = random.Random(20260902)
        for length in range(0, 10):
            for _ in range(40):
                corpus.append(
                    bytes(rng.randrange(256) for _ in range(length)))
        for payload in corpus:
            with self.subTest(payload=payload.hex()):
                expected = _independent_unpack(payload)
                try:
                    got = decode_pickup_request_payload(payload)
                except MobPickupRequestRefused as exc:
                    self.assertIsNone(
                        expected,
                        "the walk refused a body the fixed layout accepted")
                    self.assertIn(
                        exc.reason, MOB_PICKUP_REQUEST_REFUSAL_REASONS)
                else:
                    self.assertEqual(
                        got, expected,
                        "the two derivations disagree about these bytes")

    def test_a_body_that_only_starts_right_is_not_a_pickup(self):
        """A malformed copy of the accepted request must not ride its prefix."""
        accepted = _body(mob_loot.DROP_KEY_BASE, 3)
        read = self.read(_pc(self.legacy, accepted + b"\x00"))
        self.assertFalse(read.accepted)
        self.assertEqual(read.reason, "trailing_bytes_after_object")
        self.assertIsNone(read.fields)


# ---------------------------------------------------------------------------
# 2. Every refusal, from bytes, through the public entry point
# ---------------------------------------------------------------------------

class EveryRefusalTests(LegacyFixture):
    def _cases(self):
        legacy = self.legacy
        good = _body(mob_loot.DROP_KEY_BASE, 1)
        return {
            "not_a_runtime_protocol_req": _pc(
                legacy, good, outer_id=legacy.GSCN_LOGIN_PROTOCOL),
            "wrong_outer_version": _pc(legacy, good, outer_version=1),
            "wrong_outer_mask": _pc(legacy, good, outer_mask=3),
            "vital_count_not_one": _pc(legacy, good, vital_count=2),
            "not_the_pickup_vital": _pc(legacy, good, vital_id=0x36AA),
            "wrong_vital_version": _pc(legacy, good, vital_version=1),
            "truncated_payload": _pc(legacy, good[:4]),
            "wrong_object_ref_tag": _pc(
                legacy, bytes([0x15]) + good[1:]),
            "wrong_opaque_u8_tag": _pc(
                legacy, good[:5] + bytes([0x0B]) + good[6:]),
            "trailing_bytes_after_object": _pc(legacy, good + b"\x99"),
        }

    def test_each_wire_refusal_is_reached_and_named(self):
        for reason, pc in self._cases().items():
            with self.subTest(reason=reason):
                read = self.read(pc)
                self.assertFalse(read.accepted)
                self.assertEqual(read.reason, reason)
                self.assertIsNone(read.fields, "a refusal returned fields")

    def test_the_registry_is_split_by_what_can_actually_produce_it(self):
        """A registry with a name nothing can produce is a lie in a tuple.

        The first draft of this test hand-added two names to the set it was
        checking and called the result a measurement.  An adversarial pass
        showed the two are NOT reachable from any byte string: the frame
        parser always hands over a bytes payload and always carries all
        seven envelope names.  They are kept as guards against a caller,
        and the registry now says which family each name belongs to.
        """
        wire = set(self._cases())
        readiness = set(
            mob_pickup_request.MOB_PICKUP_REQUEST_READINESS_REASONS)
        api_only = set(mob_pickup_request.MOB_PICKUP_REQUEST_API_ONLY_REASONS)
        self.assertEqual(
            wire | readiness | api_only,
            set(MOB_PICKUP_REQUEST_REFUSAL_REASONS),
            "a registered refusal reason belongs to no family, or one of "
            "the families names a reason the registry does not carry")
        self.assertEqual(
            wire & api_only, set(),
            "a reason cannot be both wire-reachable and API-only")

    def test_each_api_only_reason_is_produced_by_an_api_caller(self):
        """Kept as guards means driven, not merely listed."""
        with self.assertRaises(MobPickupRequestRefused) as caught:
            decode_pickup_request_payload(None)
        self.assertEqual(caught.exception.reason, "payload_not_bytes")

        class Half:
            outer_id = 0

        self.assertEqual(
            classify_pickup_request(self.legacy, Half()),
            "parse_object_missing_fields")

        class NoLegacy:
            pass

        good = self.legacy.parse_outer(
            _pc(self.legacy, _body(mob_loot.DROP_KEY_BASE, 0)))
        self.assertEqual(
            classify_pickup_request(NoLegacy(), good),
            "legacy_module_missing_fields")

        class Hostile:
            outer_id = 0
            outer_version = 0
            outer_mask = 0
            vital_count = 1
            nested_version = 0
            nested_payload = b""

            @property
            def nested_id(self):
                raise KeyError("hostile getter")

        self.assertEqual(
            classify_pickup_request(self.legacy, Hostile()),
            "parse_object_refused_to_answer")

    def test_the_refusal_type_cannot_carry_an_unregistered_reason(self):
        with self.assertRaises(RuntimeError):
            raise MobPickupRequestRefused("not_in_the_registry")

    def test_no_wire_input_raises_out_of_the_entry_point(self):
        """A listener that throws on a malformed frame hands over the session."""
        for pc in list(self._cases().values()) + [
            _pc(self.legacy, b""),
            _pc(self.legacy, b"\x14\x00"),
        ]:
            with self.subTest(pc=pc.hex()):
                read = self.read(pc)
                self.assertIsInstance(read, PickupRequestRead)


# ---------------------------------------------------------------------------
# 3. Observability
# ---------------------------------------------------------------------------

class ConsoleTests(LegacyFixture):
    def test_the_accepted_line_carries_both_values_and_stays_ascii(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            read = self.read(
                _pc(self.legacy, _body(0x00100005, 7)), echo=True)
        line = buffer.getvalue().strip()
        self.assertTrue(read.accepted)
        self.assertIn("MOB_PICKUP_REQUEST_DECODED", line)
        self.assertIn("0x00100005", line)
        self.assertIn("opaque_u8=7", line)
        line.encode("ascii")

    def test_the_refused_line_names_the_reason_and_stays_ascii(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.read(_pc(self.legacy, b"\x14\x00"), echo=True)
        line = buffer.getvalue().strip()
        self.assertIn("MOB_PICKUP_REQUEST_REFUSED", line)
        self.assertIn("truncated_payload", line)
        line.encode("ascii")

    def test_echo_off_prints_nothing_at_all(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.read(_pc(self.legacy, _body(1, 1)), echo=False)
        self.assertEqual(buffer.getvalue(), "")


# ---------------------------------------------------------------------------
# 4. It is a production lane, and it stays one
# ---------------------------------------------------------------------------

class ProductionLaneTests(unittest.TestCase):
    @staticmethod
    def _imported_names(source):
        names = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
                names.extend(alias.name for alias in node.names)
        return names

    def test_the_flag_is_on_and_there_is_no_gate_object(self):
        self.assertIs(mob_pickup_request.production_allowed, True)
        self.assertIs(mob_pickup_request.test_only, False)
        tree = ast.parse(MODULE_SOURCE)
        for node in ast.walk(tree):
            if isinstance(node, ast.arg):
                self.assertNotIn(
                    "scenario", node.arg,
                    "a production lane may not take a scenario argument")
            if isinstance(node, ast.Name):
                self.assertNotIn(
                    "scenario", node.id,
                    "a production lane may not read a scenario name")

    def test_a_production_lane_imports_no_probe_and_imports_nothing_dynamically(self):
        imported = self._imported_names(MODULE_SOURCE)
        for name in imported:
            self.assertNotIn("hypothesis", name)
        self.assertNotIn("importlib", imported)
        for node in ast.walk(ast.parse(MODULE_SOURCE)):
            if isinstance(node, ast.Call):
                target = getattr(
                    node.func, "attr", getattr(node.func, "id", ""))
                self.assertNotIn(target, ("import_module", "__import__"))

    def test_the_tripwire_would_catch_the_forms_that_defeated_it_elsewhere(self):
        for attack in (
            "from . import pickup_listener_hypothesis\n",
            "import pirateforce_foundation.pickup_listener_hypothesis\n",
            "from .ground_loot_hypothesis import GROUND_LIST_BIT\n",
        ):
            self.assertTrue(
                any("hypothesis" in name
                    for name in self._imported_names(attack)),
                "the tripwire is blind to %r" % attack)

    def test_it_calls_the_transaction_lanes_and_reimplements_neither(self):
        """The orchestration is here; the transaction is NOT copied here.

        The first draft banned these imports and published the control flow
        as prose instead -- which an adversarial pass then mutated six ways
        without turning the suite red.  Importing them is what let the
        branch become executable.  What stays banned is the part that would
        make this a second transaction: no database handle, no socket, no
        scenario-gated probe, and no re-implementation of the take.
        """
        imported = self._imported_names(MODULE_SOURCE)
        self.assertIn("mob_pickup_persist", imported)
        self.assertIn("mob_pickup", imported)
        for banned in ("sqlite3", "socket", "store", "mob_loot"):
            self.assertNotIn(banned, imported)
        for banned_call in ("commit_pickup", "place_in_bag", "resolve_claim",
                            "bag_delta_pc", "PickupClaim"):
            self.assertNotIn(
                banned_call, MODULE_SOURCE,
                "the reader must not reimplement the transaction")


# ---------------------------------------------------------------------------
# 5. The lane it was lifted from, and this one, still read the same bytes
# ---------------------------------------------------------------------------

class ProbeLaneAgreementTests(LegacyFixture):
    """The probe lane is scenario-gated and stays that way; it is not the
    source of these values.  It IS a second transcription of the same four
    delivery-table rows, made on a different round, so a disagreement means
    one of the two transcriptions moved -- worth a red test either way.
    """

    def test_the_probe_lanes_bodies_decode_here_to_the_same_pair(self):
        from pirateforce_foundation import pickup_listener_hypothesis as probe

        self.assertEqual(
            probe.PICKUP_LISTENER_VITAL_ID,
            mob_pickup_request.PICKUP_REQUEST_VITAL_ID)
        self.assertEqual(
            probe.PICKUP_LISTENER_PAYLOAD_SIZE,
            mob_pickup_request.PICKUP_REQUEST_PAYLOAD_SIZE)
        self.assertEqual(
            probe.PICKUP_LISTENER_SERIALIZER_SHA256,
            mob_pickup_request.PICKUP_REQUEST_SERIALIZER_SHA256)
        for label in probe.PICKUP_LISTENER_PROBE_ORDER:
            fields = probe.PICKUP_LISTENER_PROBE_FIELDS[label]
            payload = probe.encode_pickup_listener_payload(self.legacy, fields)
            with self.subTest(label=label):
                self.assertEqual(
                    decode_pickup_request_payload(payload),
                    PickupRequestFields(
                        fields.object_ref_u32, fields.opaque_u8))


# ---------------------------------------------------------------------------
# 6. The line handed to the chief, EXECUTED, wire bytes to database row
# ---------------------------------------------------------------------------

class TheWiringLineRunsTests(unittest.TestCase):
    """The published branch, EXECUTED -- guards included.

    The first draft of this file exec'd only the two call lines and left the
    branch's control flow (the readiness check, the refusal path, the order
    of the calls) as prose in the wiring note.  An adversarial pass mutated
    that prose six ways -- inverting the accepted check, deleting it,
    keying on the outer id, emptying the whole string -- and this file
    stayed GREEN through every one, then crashed the branch-as-written with
    one trailing byte.  The control flow now lives in a function and this
    class drives it, which is why a mutation to it turns red here.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("pickup-request-h6bl53")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "PickupRequestOne", "pickuprequestone",
            "fingerprint-pickup-request-h6bl53",
            lambda selector: (b"wire", b"avatar", 0x10000001 + selector, 0),
            home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.registry = mob_pickup.BagCellRegistry()

    @contextmanager
    def _raw(self):
        db = sqlite3.connect(self.path)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _rows(self):
        with self._raw() as db:
            return [
                tuple(row) for row in db.execute(
                    "SELECT item_identity,template_id,quantity,slot "
                    "FROM character_backpack_items WHERE character_id=? "
                    "ORDER BY item_identity",
                    (self.character.id,),
                )
            ]

    def _cell(self):
        return self.registry.claim(
            self.character.id,
            self.store.get_backpack(self.sid, self.character.id),
            self.store.backpack_issued_through(self.sid, self.character.id),
        )

    def _namespace(self, *, key_offset=0, position=DROP_AT, body=None,
                   bag_cell=True, ground=True):
        """Every name the published line uses, bound to a real object."""
        if body is None:
            body = _body(mob_loot.DROP_KEY_BASE + key_offset, 0)
        return {
            "mob_pickup_request": mob_pickup_request,
            "legacy": self.legacy,
            "parsed": self.legacy.parse_outer(_pc(self.legacy, body)),
            "store": self.store,
            "sid": self.sid,
            "character_id": self.character.id,
            "bag_cell": self._cell() if bag_cell else None,
            "drop_ledger_cell": (
                a_ground_cell(a_drop(key_offset)) if ground else None),
            "identity": KILLER,
            "x": position[0],
            "y": position[1],
            "z": position[2],
        }

    def _run(self, namespace):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exec(  # noqa: S102 - executing the published line IS the test
                "outcome = "
                + mob_pickup_request.MOB_PICKUP_REQUEST_HEADLINE_CALL,
                namespace)
        return namespace["outcome"], buffer.getvalue()

    # ----- the loop the round exists for --------------------------------

    def test_the_published_line_runs_and_the_click_ends_in_the_database(self):
        """Bytes a client would send in at the top; a real row out at the
        bottom; in between, only the exact string this lane publishes."""
        baseline = self._rows()
        self.assertEqual(len(baseline), len(INITIAL_BACKPACK.items))
        outcome, console = self._run(self._namespace())
        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.reason, ACCEPTED)
        self.assertIsNotNone(outcome.delta)
        rows = self._rows()
        self.assertEqual(
            len(rows), len(baseline) + 1, "the click did not become a row")
        landed = [row for row in rows if row not in baseline]
        self.assertEqual(len(landed), 1)
        self.assertEqual(landed[0][1], ITEM)
        self.assertIn("MOB_PICKUP_REQUEST_DECODED", console)

    # ----- the guards the prose used to carry ---------------------------

    def test_one_trailing_byte_is_refused_by_name_and_does_not_crash(self):
        """The exact input that crashed the branch-as-prose.

        A stranger appends one byte to the accepted body.  The published
        line must come back with a named refusal and an untouched world --
        not AttributeError on None out of the inbound dispatch.
        """
        baseline = self._rows()
        outcome, console = self._run(self._namespace(
            body=_body(mob_loot.DROP_KEY_BASE, 0) + b"\x99"))
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "trailing_bytes_after_object")
        self.assertIsNone(outcome.delta)
        self.assertEqual(self._rows(), baseline)
        self.assertIn("MOB_PICKUP_REQUEST_REFUSED", console)

    def test_a_connection_with_no_character_selected_is_refused_by_name(self):
        """No character selected means no bag cell at the call site.

        Every neighbouring inbound lane in the chief's file carries this
        guard; the first draft of this request published a branch without
        one, which handed the transaction a None bag cell.
        """
        baseline = self._rows()
        outcome, console = self._run(self._namespace(bag_cell=False))
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "session_has_no_bag_cell")
        self.assertIsNone(outcome.delta)
        self.assertEqual(self._rows(), baseline)
        self.assertIn("session_has_no_bag_cell", console)

    def test_a_scene_with_no_ground_cell_is_refused_by_name(self):
        outcome, _ = self._run(self._namespace(ground=False))
        self.assertFalse(outcome.handled)
        self.assertEqual(outcome.reason, "session_has_no_ground_cell")

    def test_a_reference_no_ledger_row_carries_is_refused_and_takes_nothing(
            self):
        """NONCLAIM 1's cost, measured: a wrong id grants nothing.

        The decoder accepts any well-formed body -- it is a reader, not an
        authority.  The transaction is the authority, and a reference that
        names no live row on this ground refuses by its own name, unwrapped.
        """
        baseline = self._rows()
        outcome, _ = self._run(self._namespace(body=_body(0xDEADBEEF, 0)))
        self.assertTrue(outcome.read.accepted)
        self.assertFalse(outcome.handled)
        self.assertIn(
            outcome.reason, mob_pickup.MOB_PICKUP_REFUSAL_REASONS,
            "a transaction refusal must reach the caller under its own name")
        self.assertEqual(self._rows(), baseline)

    def test_a_swapped_coordinate_in_that_line_is_caught_rather_than_granted(
            self):
        """The run above proves the line runs; this proves it is the right
        one.  Every permutation puts the claimant far outside the radius."""
        for permutation in (
            (DROP_AT[1], DROP_AT[0], DROP_AT[2]),
            (DROP_AT[0], DROP_AT[2], DROP_AT[1]),
            (DROP_AT[2], DROP_AT[1], DROP_AT[0]),
        ):
            with self.subTest(permutation=permutation):
                baseline = self._rows()
                outcome, _ = self._run(self._namespace(position=permutation))
                self.assertFalse(outcome.handled)
                self.assertEqual(self._rows(), baseline)
                self.registry.release(self.character.id)

    def test_nothing_the_wire_can_carry_raises_out_of_the_published_line(self):
        """The branch sits under a stranger's frame: it may not throw."""
        for body in (
            b"", b"\x14", b"\x14\x00\x00\x00\x00", bytes(7), bytes(64),
            _body(mob_loot.DROP_KEY_BASE, 0) + b"\x00",
            b"\x15" + _body(0, 0)[1:],
        ):
            with self.subTest(body=body.hex()):
                outcome, _ = self._run(self._namespace(body=body))
                self.assertIsInstance(
                    outcome, mob_pickup_request.PickupRequestOutcome)
                self.registry.release(self.character.id)

    # ----- the line itself, pinned against the lane it delegates to ------

    def test_the_published_line_is_the_one_this_module_actually_exposes(self):
        published = mob_pickup_request.MOB_PICKUP_REQUEST_HEADLINE_CALL
        self.assertIn(
            "mob_pickup_request.dispatch_inbound_pickup_request(", published)
        for name in ("legacy", "parsed", "store", "sid", "character_id",
                     "bag_cell", "drop_ledger_cell", "identity", "x", "y",
                     "z"):
            self.assertIn(name, published)

    def test_this_lane_passes_the_transaction_lane_its_own_published_args(
            self):
        """The delegation is pinned against the sibling's own headline.

        The sibling publishes its call as a string too.  If either lane
        renames or reorders an argument, these two stop matching and this
        test says so -- rather than a silent drift that only shows up as a
        wrong pickup months later.
        """
        sibling = mob_pickup_persist.MOB_PICKUP_PERSIST_HEADLINE_CALL
        self.assertTrue(sibling.startswith(
            "mob_pickup_persist.pickup_and_persist("))
        expected = [
            name.strip() for name in
            sibling.split("(", 1)[1].rstrip(")").split(",")]
        source = inspect.getsource(
            mob_pickup_request.dispatch_inbound_pickup_request)
        call = source.split("mob_pickup_persist.pickup_and_persist(", 1)[1]
        call = call.split("echo=echo)", 1)[0]
        actual = [
            part.strip() for part in call.replace("\n", " ").split(",")
            if part.strip()]
        self.assertEqual(len(actual), len(expected))
        for name, passed in zip(expected, actual):
            if name in ("object_ref_u32", "opaque_u8"):
                self.assertEqual(passed, "read.fields." + name)
            else:
                self.assertEqual(passed, name)

    def test_the_wiring_note_carries_the_decision_that_cleared_it(self):
        """The hold was the load-bearing sentence; now the clearance is.

        ROUND h6bl53 published this ask as HELD, because RE-125, COO-DECISION
        20260901_0245 and GT-146 forbade a production call site keyed on this
        id while COO-DECISION 20260902_0254 and 20260902_0348 ordered one.
        COO-DECISION 20260902_0541 answered that ASK-COO letter with option
        1: the prohibitions are withdrawn and this one line is excepted.

        This test moved WITH that decision rather than being deleted by it.
        What it pins now is the shape a reader can audit: the named decision
        that cleared the branch, the fact RE-125 measured (still true, and
        0541 requires it AT the call site), and every former blocker still
        present and struck through - not erased.
        """
        wiring = mob_pickup_request.MOB_PICKUP_REQUEST_WIRING
        self.assertTrue(wiring.startswith("STATUS: approved_by_coo_"))
        self.assertIn("THIS BRANCH IS CLEARED TO LAND", wiring)
        # Not the whole six-word sentence: pf-adversary round okdfge got a
        # green suite out of "THIS BRANCH IS STILL HELD, DO NOT LAND IT",
        # which re-imposes the hold in prose while the status says cleared.
        self.assertNotIn("DO NOT LAND", wiring.upper())
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_WIRING_STATUS,
            "approved_by_coo_20260902_0541")
        approval = mob_pickup_request.PICKUP_REQUEST_WIRING_APPROVAL
        for phrase in ("20260902_0541", "option 1", "withdrawn",
                       "persist-and-", "endorsed"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, approval)
        # 0541: "the fact of RE-125 is still true and must be written at the
        # call site".  A clearance that quietly drops the nonclaim is the
        # failure this line exists to catch.
        self.assertIn("NEVER been observed on any wire", wiring)
        self.assertIn("0541 item 2 ENDORSED it", wiring)
        blockers = mob_pickup_request.PICKUP_REQUEST_WIRING_BLOCKERS
        joined = " ".join(blockers)
        for ticket in ("RE-125", "20260901_0245", "GT-146", "20260902_0254"):
            self.assertIn(ticket, joined)
        for blocker in blockers:
            with self.subTest(blocker=blocker[:40]):
                self.assertRegex(
                    blocker, r"^(LIFTED|WITHDRAWN|REREAD|ANSWERED) by "
                             r"COO-DECISION 20260902_0541 -- was: ")
        # THE PREFIX IS NOT THE HISTORY.  pf-adversary round okdfge replaced
        # all four entries with their prefix plus a bare ticket number and
        # this test stayed green: the condition each blocker CARRIED - which
        # is the part a later round would be tempted to lose - was gone and
        # nothing said so.  These are the words that made each one a blocker.
        for phrase in (
            "until an attended click capture exists",
            "until GT-124 captures a real opcode",
            "must stay on screen first",
            "do not mention the three above",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, joined)


# ---------------------------------------------------------------------------
# 7. What this round does NOT claim
# ---------------------------------------------------------------------------

class PinnedNumbersAreHardPinnedEverywhereTests(unittest.TestCase):
    """The half of the cross-check that runs on the machine that decides.

    ROUND okdfge, pf-adversary defect 2, quoted because it is the whole
    reason this class exists: on the Windows gate - the one machine whose
    verdict merges or closes a pull request - the table this module's pins
    come from is not present, so ``DeliveryTableCrossCheckTests`` never runs
    and the only thing the skip census certifies there is THAT IT DID NOT
    RUN.  A round could have replaced those three test bodies with ``pass``
    and the gate would have reported the same numbers.

    So the two checks are split by what each machine can honestly answer:

      * HERE, everywhere, with no sibling repository and no artifact: the
        constants are compared against the literal values the table was read
        as, so an edit to a pin is red on the gate itself.
      * THERE, on the bridge and the cloud clone, where the table exists:
        those same constants are re-derived FROM the table, so a re-published
        table that moves a tag or an offset is red as well.

    Neither one alone is enough.  This one cannot notice the table changing;
    that one cannot run where it would matter for a merge.
    """

    def test_the_body_grammar_constants_are_the_values_the_table_was_read_as(
            self):
        module = mob_pickup_request
        self.assertEqual(module.PICKUP_REQUEST_OBJECT_REF_TAG, 0x14)
        self.assertEqual(module.PICKUP_REQUEST_OBJECT_REF_OBJECT_OFFSET, 0x14)
        self.assertEqual(module.PICKUP_REQUEST_OBJECT_REF_WIDTH, 4)
        self.assertEqual(module.PICKUP_REQUEST_OPAQUE_U8_TAG, 0x08)
        self.assertEqual(module.PICKUP_REQUEST_OPAQUE_U8_OBJECT_OFFSET, 0x18)
        self.assertEqual(module.PICKUP_REQUEST_OPAQUE_U8_WIDTH, 1)
        self.assertEqual(module.PICKUP_REQUEST_PAYLOAD_SIZE, 7)

    def test_the_serializer_span_constants_are_pinned_too(self):
        module = mob_pickup_request
        self.assertEqual(module.PICKUP_REQUEST_SERIALIZER_VA, 0x005E5E30)
        self.assertEqual(module.PICKUP_REQUEST_SERIALIZER_END_VA, 0x005E5E83)
        self.assertEqual(module.PICKUP_REQUEST_SERIALIZER_LEN, 83)
        self.assertEqual(module.PICKUP_REQUEST_PRODUCER_VA, 0x006B0639)
        self.assertEqual(
            module.PICKUP_REQUEST_SERIALIZER_END_VA
            - module.PICKUP_REQUEST_SERIALIZER_VA,
            module.PICKUP_REQUEST_SERIALIZER_LEN,
            "the span and its length are two spellings of one fact and must "
            "not drift apart",
        )

    def test_the_hard_pin_and_the_table_check_name_the_same_constants(self):
        """A constant added to one half and not the other is the bug.

        Read as text on purpose: the point is that a future round which adds
        a pin to the table cross-check without adding it here would leave the
        gate blind to that pin, which is exactly the hole this class closes.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        hard = source.split(
            "class PinnedNumbersAreHardPinnedEverywhereTests", 1)[1].split(
            "class DeliveryTableCrossCheckTests", 1)[0]
        table = source.split("class DeliveryTableCrossCheckTests", 1)[1]
        for name in (
            "PICKUP_REQUEST_OBJECT_REF_TAG",
            "PICKUP_REQUEST_OBJECT_REF_OBJECT_OFFSET",
            "PICKUP_REQUEST_OPAQUE_U8_TAG",
            "PICKUP_REQUEST_OPAQUE_U8_OBJECT_OFFSET",
            "PICKUP_REQUEST_PAYLOAD_SIZE",
            "PICKUP_REQUEST_SERIALIZER_VA",
        ):
            with self.subTest(constant=name):
                self.assertIn(name, hard)
                self.assertIn(name, table)


@BRIDGE_SERIALIZER_TABLE.skip_unless_present()
class DeliveryTableCrossCheckTests(unittest.TestCase):
    """Re-derive the pins from the SOURCE table, not from a sibling copy.

    Every pin in the module was transcribed by hand from the delivery table
    in the OTHER repository.  An adversarial pass showed the consequence:
    mutating the producer VA, or moving the serializer span, left the suite
    green, because the only cross-check was against a second in-repo
    transcription.  When the bridge checkout is beside this one -- which is
    the case on the cloud runner and on the bridge machine -- this class
    reads the table itself.  When it is not (a clone of this repo alone),
    it skips with a declared reason rather than pretending to check.

    THE SKIP IS DECLARED, NOT HAND-WRITTEN (round okdfge).  The first draft
    of this class wrote a bare ``skipTest`` in ``setUp``, and the Windows
    gate's skip census closed pull request #540 for exactly that:
    ``UNDECLARED SKIP: tests/test_mob_pickup_request.py skipped 3 test(s)``.
    The guard is ``BRIDGE_SERIALIZER_TABLE`` - the ONE file this class reads -
    and not the eight-table key, because the eight-table key hides this check
    on a machine that holds the table it needs (measured by pf-adversary this
    round on a sibling carrying seven of the eight).  Its count is pinned in
    ``docs/PYTEST_SKIP_PINS.json`` in the same commit as this line.

    WHAT THIS CLASS DOES NOT COVER, said here rather than left to be
    discovered: it never runs on the Windows gate, which is the machine whose
    verdict opens or closes a pull request.  What the gate can still catch is
    an edit to the constants themselves - see
    ``PinnedNumbersAreHardPinnedEverywhereTests`` below, which runs on every
    machine and needs no sibling at all.
    """

    TSV = ROOT.parent / "pf_bridge" / "external" / "PF_SERIALIZER_FIELDS.tsv"

    def setUp(self):
        self.rows = [
            line.split("\t")
            for line in self.TSV.read_text(
                encoding="utf-8", errors="replace").splitlines()
            if line.startswith("PickupTerrainThing\t")
        ]
        # A present-but-empty (or re-published, or truncated) table must fail
        # by NAME here, not as a KeyError three assertions later: the
        # precondition proves the file exists, never that it still carries
        # this object's rows.  pf-adversary round okdfge built the eight files
        # at zero bytes and measured the difference.
        self.assertTrue(
            self.rows,
            "%s exists but carries no PickupTerrainThing row: the table was "
            "re-published or truncated, and every pin below is unverifiable "
            "rather than wrong" % self.TSV,
        )

    def test_the_table_still_carries_four_symmetric_rows(self):
        self.assertEqual(len(self.rows), 4)
        self.assertEqual(
            sorted(row[1] for row in self.rows), ["R", "R", "W", "W"])
        for row in self.rows:
            self.assertEqual(row[6], "ALWAYS")

    def test_every_pinned_number_is_the_tables_number(self):
        module = mob_pickup_request
        by_order = {(row[1], row[2]): row for row in self.rows}
        for direction in ("W", "R"):
            first = by_order[(direction, "1")]
            second = by_order[(direction, "2")]
            self.assertEqual(
                int(first[3], 16), module.PICKUP_REQUEST_OBJECT_REF_TAG)
            self.assertEqual(
                int(first[4].lstrip("+"), 16),
                module.PICKUP_REQUEST_OBJECT_REF_OBJECT_OFFSET)
            self.assertEqual(
                int(first[5]), module.PICKUP_REQUEST_OBJECT_REF_WIDTH)
            self.assertEqual(
                int(second[3], 16), module.PICKUP_REQUEST_OPAQUE_U8_TAG)
            self.assertEqual(
                int(second[4].lstrip("+"), 16),
                module.PICKUP_REQUEST_OPAQUE_U8_OBJECT_OFFSET)
            self.assertEqual(
                int(second[5]), module.PICKUP_REQUEST_OPAQUE_U8_WIDTH)
            self.assertEqual(
                int(first[7], 16), module.PICKUP_REQUEST_SERIALIZER_VA)
            self.assertEqual(
                int(first[8], 16), module.PICKUP_REQUEST_SERIALIZER_END_VA)
            self.assertEqual(
                first[9], module.PICKUP_REQUEST_SERIALIZER_SHA256)

    def test_the_seven_byte_size_is_the_labelled_inference_it_claims_to_be(
            self):
        """The table states tags and widths; the byte count is derived.

        The module says so in its own provenance section.  Here that
        derivation is executed: two records, each one tag byte plus its
        declared width.
        """
        widths = sorted(int(row[5]) for row in self.rows if row[1] == "W")
        self.assertEqual(widths, [1, 4])
        self.assertEqual(
            sum(widths) + len(widths),
            mob_pickup_request.PICKUP_REQUEST_PAYLOAD_SIZE)


class NonclaimTests(unittest.TestCase):
    def test_the_two_nonclaims_the_clearance_leans_on_are_still_written(self):
        """Deleting a nonclaim must not be free.

        pf-adversary round okdfge removed NONCLAIM 5 ("nothing here is
        evidence that a player picked anything up") and NONCLAIM 7 (the
        history of the hold and the decision that lifted it) one at a time
        and the suite stayed green both times.  Both are load-bearing now
        that the branch is cleared: 5 is what stops a round reporting P-1's
        "picked up" half as done on the strength of an unwired module, and 7
        is the only place a reader learns that RE-125 once forbade this line
        and by whose decision it stopped forbidding it.
        """
        doc = mob_pickup_request.__doc__
        self.assertIn("NOTHING HERE IS EVIDENCE THAT A PLAYER PICKED "
                      "ANYTHING UP", doc)
        self.assertIn("no round may report P-1's", doc)
        self.assertIn("COO-DECISION 20260902_0541 -- WHICH DOES NOT MAKE "
                      "THE ID OBSERVED", doc)
        self.assertIn("RE-125", doc)

    def test_the_vital_id_is_marked_unobserved_and_the_negative_is_bounded(
            self):
        """The provenance line was rewritten this round, on evidence.

        The first draft said "derived from the name hash only", copying
        RE-125's premise -- which the Codex checkpoint of 2026-08-31 had
        already retired by closing 0x4543 as the ASSIGNED nested runtime
        type id at the IMAGE layer.  What did NOT change is the part that
        constrains this lane: never observed on any wire, and the capture
        negative is bounded rather than absolute.
        """
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_VITAL_ID_PROVENANCE,
            "assigned_nested_runtime_type_id_image_layer_never_observed_"
            "on_wire")
        self.assertIn(
            "bounded", mob_pickup_request.PICKUP_REQUEST_CAPTURE_STATUS)
        self.assertEqual(
            mob_pickup_request.PICKUP_REQUEST_RUNTIME_ID_SLOT_VA, 0x0108202C)

    def test_the_envelope_is_still_marked_our_design(self):
        self.assertIn(
            "our_acceptance_design",
            mob_pickup_request.PICKUP_REQUEST_VITAL_VERSION_PROVENANCE)

    def test_the_call_site_is_absent_or_is_the_published_one(self):
        """Not a skip: a live assertion on both sides of the hold.

        The first draft called ``skipTest`` the moment ``runtime.py``
        mentioned this module -- so the assertion vanished exactly when the
        branch landed, which is the only moment it could catch anything.
        Now: while the branch is absent, this pins that it is absent (the
        wiring note is a request, NONCLAIM 5, cleared to land by
        COO-DECISION 20260902_0541 and not landed by anyone yet); once it
        lands, this pins that what landed is the published call, that it
        keys on this lane's own constant, and that it carries the one fact
        0541 made a CONDITION of lifting RE-125's prohibition.
        """
        runtime_path = ROOT / "src/pirateforce_foundation/runtime.py"
        runtime = runtime_path.read_text(encoding="utf-8")
        if "mob_pickup_request" not in runtime:
            self.assertNotIn("dispatch_inbound_pickup_request", runtime)
            return
        self.assertIn(
            "dispatch_inbound_pickup_request(", runtime,
            "runtime.py names this lane but does not make its published "
            "call: a hand-written variant is exactly what the published "
            "string exists to prevent")
        self.assertIn(
            "PICKUP_REQUEST_VITAL_ID", runtime,
            "the branch must key on this lane's own nested id constant")
        # COO-DECISION 20260902_0541 item 1 lifts RE-125's prohibition ON
        # CONDITION that the fact RE-125 measured is written at the call
        # site.  pf-adversary round okdfge measured that nothing enforced
        # that condition: a clean landing with no comment left every test
        # green and the condition silently gone.  It is enforced here, in
        # the only file that can see both halves.
        lines = runtime.splitlines()
        anchors = [
            i for i, line in enumerate(lines)
            if "dispatch_inbound_pickup_request(" in line
        ]
        self.assertTrue(anchors)
        needle = "never been observed on any wire"
        for anchor in anchors:
            window = "\n".join(
                lines[max(0, anchor - 10):anchor + 11]).lower()
            with self.subTest(line=anchor + 1):
                self.assertIn(
                    needle, window,
                    "runtime.py:%d makes this lane's call without the "
                    "nonclaim COO-DECISION 20260902_0541 made a condition "
                    "of the exception it granted.  Put a comment carrying "
                    "the words '%s' within ten lines of the call: the id "
                    "0x4543 has never been seen on any wire, and a reader "
                    "of runtime.py must not have to find that out from "
                    "another repository." % (anchor + 1, needle))
        # THE TWO SUBSTRING CHECKS ABOVE ARE NOT ENOUGH, AND THAT WAS
        # MEASURED, NOT SUSPECTED.  pf-adversary (round ls5m3c) mutated the
        # landed call site ten ways and ran the full suite on each.  Two
        # mutations stayed GREEN and both are the kind this lane already has
        # scar tissue for:
        #   * keying the branch on the OUTER id instead of the nested one --
        #     the layer error MOB_PICKUP_REQUEST_WIRING forbids by name.  The
        #     branch simply becomes dead and every test passes.
        #   * swapping bag_cell and drop_ledger_cell inside the published
        #     call.  Every pickup then refuses type_not_typed_record forever,
        #     silently.  This is the SAME defect mob_pickup.py records an
        #     adversarial pass proving on the sibling lane, which is why
        #     MOB_PICKUP_REQUEST_HEADLINE_CALL is published as an executable
        #     string in the first place -- and nothing was comparing the call
        #     site against it.
        # So compare the parsed call against the published string, and pin
        # what the enclosing `if` tests.  A substring cannot see argument
        # order; an AST can.
        tree = ast.parse(runtime)
        published = ast.dump(ast.parse(
            mob_pickup_request.MOB_PICKUP_REQUEST_HEADLINE_CALL,
            mode="eval").body)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "dispatch_inbound_pickup_request"
        ]
        self.assertTrue(calls, "the call vanished from the AST")
        for call in calls:
            with self.subTest(line=call.lineno):
                self.assertEqual(
                    ast.dump(call), published,
                    "runtime.py:%d does not make the call this lane "
                    "PUBLISHES, argument for argument.  Compare it against "
                    "mob_pickup_request.MOB_PICKUP_REQUEST_HEADLINE_CALL: a "
                    "swapped pair of cells refuses every pickup for good and "
                    "no other test in this repository can see it."
                    % call.lineno)
        # And the branch must key on the NESTED id constant, never the outer
        # one: `nested_id == mob_pickup_request.PICKUP_REQUEST_VITAL_ID`.
        keyed_on_nested_id = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            if not (isinstance(node.left, ast.Name)
                    and node.left.id == "nested_id"):
                continue
            for comparator in node.comparators:
                if (isinstance(comparator, ast.Attribute)
                        and comparator.attr == "PICKUP_REQUEST_VITAL_ID"):
                    keyed_on_nested_id = True
        self.assertTrue(
            keyed_on_nested_id,
            "runtime.py makes this lane's call but nothing in it compares "
            "`nested_id` against PICKUP_REQUEST_VITAL_ID.  0x4543 is a NESTED "
            "runtime type id; keying on it at the top level is a layer error "
            "the wiring note forbids by name, and it fails silently -- the "
            "branch goes dead and every other test stays green.")


if __name__ == "__main__":
    unittest.main()
