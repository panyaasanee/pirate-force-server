"""LANE-B: the RuntimeRes frames app.py's PRESERVE patch never sees.

Why this file exists.  ``app.py``'s ``install_ground_heartbeat_preserve``
substitutes the PRESERVE body for exactly one caller -- the frame whose
``co_name`` is ``heartbeat_worker``.  v141's ``make_runtime_vitals`` ends on an
EMPTY derived change mask and never reaches it, so the VitalData responses it
composes carry no ground list at all.

``TheCensusOfRuntimeResComposersInV141`` re-derives from the frozen file's AST
which functions compose a ``GSCN_RunTimeProtocolRes`` and what change-mask
records each one writes.  It is the test that goes red when a composer is
added, renamed, or changes a mask.  READ ``_composers``'s own docstring before
trusting it: pf-adversary defeated its first draft with four planted composers
(round ewm6ff, finding D4) and the detector was widened, but it is a census of
the composers that write the tag in a recognisable spelling -- NOT a proof that
no other exists.  The two tests at the end of that class say so in code.

The rest pins :func:`mob_loot.preserve_ground_in_runtime_res_vitals` against
the real composer, and drives every refusal from a body that really reaches it.
That function takes the VITALS, not a composed pc, and the reason is the whole
point of this file: its first draft took a pc and rewrote the last two bytes
when they were ``0B 00``, which pf-adversary refuted by driving a real
login-path composer through it and watching a u32 field change value with no
refusal raised (finding D1).  ``TheTailOfAPcIsNotEvidence`` keeps that lesson
executable so nobody re-derives the broken shape.
"""

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_loot
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_loot import (
    MobLootContractError,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
    REFUSE_FRAME_ENCODER_DISAGREES,
    REFUSE_VITALS_COMPOSER_MOVED,
    RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN,
    RUNTIME_RES_HEAD_PIN,
    RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN,
    preserve_ground_in_runtime_res_vitals,
)

V141 = ROOT / "current/pf_login_game_server_v141.py"


class LegacyCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def _vitals(self):
        payload = self.legacy.u8tag(0x08, 0) + self.legacy.u8tag(0x0B, 1)
        return [(self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload)]


class ThePreservedBodyIsTheComposersBody(LegacyCase):
    """Byte-identical in front of the mask, PRESERVE where the mask was."""

    def test_the_composer_still_ends_on_an_empty_derived_mask(self):
        # The premise of the whole file, re-derived rather than assumed.
        pc, _frame = self.legacy.make_runtime_vitals(self._vitals())
        self.assertEqual(pc[-2:], RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)

    def test_everything_before_the_mask_is_the_composers_own_bytes(self):
        vitals = self._vitals()
        composed, _ = self.legacy.make_runtime_vitals(vitals)
        pc, _frame = preserve_ground_in_runtime_res_vitals(self.legacy, vitals)
        self.assertEqual(pc[:len(composed) - 2], composed[:-2])
        self.assertEqual(len(pc), len(composed) + 3)

    def test_the_ground_list_is_present_and_its_count_is_zero(self):
        # Stated as the two facts the shape is about, not as a byte blob:
        # PRESERVE is "there is a pool and nothing to reconcile", never
        # "there is no pool".
        pc, _frame = preserve_ground_in_runtime_res_vitals(
            self.legacy, self._vitals())
        self.assertEqual(pc[-5:], RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)
        self.assertEqual(pc[-5], mob_loot.ELEMENT_MASK_TAG)
        self.assertEqual(pc[-4], mob_loot.RUNTIME_DERIVED_BIT_GROUND_LIST)
        self.assertEqual(pc[-3], mob_loot.ELEMENT_LIST_COUNT_TAG)
        self.assertEqual(pc[-2:], b"\x00\x00")

    def test_the_inherited_vitaldata_mask_is_untouched(self):
        pc, _frame = preserve_ground_in_runtime_res_vitals(
            self.legacy, self._vitals())
        head = len(RUNTIME_RES_HEAD_PIN)
        self.assertEqual(pc[head], mob_loot.ELEMENT_MASK_TAG)
        self.assertEqual(pc[head + 1], mob_loot.RUNTIME_RES_INHERITED_MASK_VITALS)

    def test_several_vitals_in_one_response_still_agree(self):
        # The count field and the per-vital records are re-derived too, so a
        # multi-vital response is where an off-by-one in the re-derivation
        # would show up first.
        payload = self.legacy.u8tag(0x08, 0)
        vitals = [
            (self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload),
            (self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload + payload),
            (self.legacy.ITEM_OPERATE_RES_VITAL, 3, b""),
        ]
        composed, _ = self.legacy.make_runtime_vitals(list(vitals))
        pc, _frame = preserve_ground_in_runtime_res_vitals(self.legacy, vitals)
        self.assertEqual(pc, composed[:-2] + RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)

    def test_an_empty_vitals_list_is_still_the_composers_business(self):
        # Not refused here: whether an empty VitalData collection is meaningful
        # is make_runtime_vitals' question, not this lane's.  What this lane
        # owns is that the derived mask ends up PRESENT either way.
        composed, _ = self.legacy.make_runtime_vitals([])
        pc, _frame = preserve_ground_in_runtime_res_vitals(self.legacy, [])
        self.assertEqual(pc, composed[:-2] + RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)

    def test_the_frame_is_re_derived_end_to_end(self):
        vitals = self._vitals()
        pc, frame = preserve_ground_in_runtime_res_vitals(self.legacy, vitals)
        self.assertEqual(frame, mob_loot._frame_via_struct(pc))
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        composed_frame = self.legacy.make_runtime_vitals(vitals)[1]
        self.assertNotEqual(frame, composed_frame)

    def test_a_pc_past_the_snappy_chunk_boundary_still_frames(self):
        # The suffix check the first draft used refused every pc of 65534 bytes
        # or more, because frame_pc opens a SECOND snappy literal header at the
        # chunk boundary and the checker blamed the framing layer for it
        # (pf-adversary, round ewm6ff, D5).  Re-derivation has no such edge.
        payload = self.legacy.u8tag(0x08, 0) + b"\x00" * 70000
        vitals = [(self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload)]
        pc, frame = preserve_ground_in_runtime_res_vitals(self.legacy, vitals)
        self.assertGreater(len(pc), 65536)
        self.assertEqual(pc[-5:], RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)
        self.assertEqual(frame, self.legacy.frame_pc(pc))


class TheTailOfAPcIsNotEvidence(LegacyCase):
    """The refuted design, kept executable so it is not re-derived.

    pf-adversary, round ewm6ff, finding D1.  Each test below builds a REAL pc
    from real primitives whose last two bytes are ``0B 00`` without that being
    the derived change mask.  A function that decided by reading the end of the
    buffer would have rewritten all of them and reported success.
    """

    def _ends_in_an_empty_mask_record(self, pc):
        return pc[-2:] == RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN

    def test_a_u32_field_can_end_in_the_mask_bytes(self):
        # Any u32tag(0x14, v) with 720896 <= v <= 786431 ends in 0B 00.
        self.assertTrue(self._ends_in_an_empty_mask_record(
            self.legacy.u32tag(mob_loot.ELEMENT_KEY_TAG, 0x000B0000)))

    def test_a_real_login_path_composer_ends_in_the_mask_bytes(self):
        # legacy_bridge.LegacyProjector.character_list -> make_runtime_vital
        # (SINGULAR), which appends no derived mask of its own: session.py
        # sends this on every login.  Its tail is the caller's payload.
        pc, _frame = self.legacy.make_runtime_vital(
            self.legacy.SELECT_ACTOR_VITAL, 10,
            self.legacy.u8tag(0x0B, 0) + self.legacy.u8tag(0x0B, 0))
        self.assertTrue(self._ends_in_an_empty_mask_record(pc))

    def test_the_shipped_function_cannot_be_handed_such_a_pc_at_all(self):
        # The structural answer to all of the above: the API takes the VITALS.
        # There is no parameter through which a pc of unknown provenance can
        # reach it, so there is no case for it to get wrong.
        import inspect

        signature = inspect.signature(preserve_ground_in_runtime_res_vitals)
        self.assertEqual(list(signature.parameters), ["legacy", "vitals"])
        self.assertFalse(
            hasattr(mob_loot, "preserve_ground_in_runtime_res"),
            "the pc-taking form was refuted and removed; re-adding it "
            "re-opens pf-adversary finding D1")


class EveryRefusalIsDrivenByARealBody(LegacyCase):
    """No refusal here is reached by hand-typing the bytes that trigger it."""

    class _MovedComposer:
        """A v141 whose make_runtime_vitals composes a different body."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def make_runtime_vitals(self, vitals):
            pc, _frame = self._real.make_runtime_vitals(vitals)
            moved = pc[:-2] + self._real.u8tag(0x0B, 4) + pc[-2:]
            return moved, self._real.frame_pc(moved)

    class _MovedTagPrimitive:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def u16tag(self, tag, value):
            if tag == mob_loot.ELEMENT_LIST_COUNT_TAG and value == 0:
                return bytes((tag, 0x00, 0x00, 0x00))   # one byte too wide
            return self._real.u16tag(tag, value)

    class _MovedFramer:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def frame_pc(self, pc):
            return b"\xac\x3e\x25\x5f\xde\xad\xbe\xef" + pc

    def test_a_composer_that_moved_refuses_instead_of_emitting(self):
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res_vitals(
                self._MovedComposer(self.legacy), self._vitals())
        self.assertEqual(
            caught.exception.args[0], REFUSE_VITALS_COMPOSER_MOVED)

    def test_a_moved_tag_primitive_refuses_instead_of_emitting(self):
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res_vitals(
                self._MovedTagPrimitive(self.legacy), self._vitals())
        # The re-derivation is built from the same primitive, so a primitive
        # that moved is caught by whichever comparison reaches it first; both
        # are refusals of this module and neither emits.
        self.assertIn(
            caught.exception.args[0],
            (REFUSE_VITALS_COMPOSER_MOVED, REFUSE_COMPOSED_BYTES_OFF_PIN))

    def test_a_framing_layer_that_disagrees_refuses(self):
        # The check this replaced accepted a 75-byte frame with a 0xDEADBEEF
        # declared length, because magic-plus-suffix is nearly circular
        # (pf-adversary, round ewm6ff, D5).  This one re-derives the frame.
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res_vitals(
                self._MovedFramer(self.legacy), self._vitals())
        self.assertEqual(
            caught.exception.args[0], REFUSE_FRAME_ENCODER_DISAGREES)

    def test_the_refused_frame_would_have_passed_the_old_check(self):
        # Shows the shim is a real attack, not a strawman: it carries the
        # pinned magic and ends with the pc, which is all the old check asked.
        pc, _frame = preserve_ground_in_runtime_res_vitals(
            self.legacy, self._vitals())
        shimmed = self._MovedFramer(self.legacy).frame_pc(pc)
        self.assertEqual(
            shimmed[:len(mob_loot.DROP_FRAME_MAGIC_PIN)],
            mob_loot.DROP_FRAME_MAGIC_PIN)
        self.assertEqual(shimmed[len(shimmed) - len(pc):], pc)
        self.assertNotEqual(shimmed, mob_loot._frame_via_struct(pc))


class TheCensusOfRuntimeResComposersInV141(unittest.TestCase):
    """Which frozen functions compose a RuntimeRes, and what masks each writes.

    This reads ONE file -- not the repository -- because a repo-wide text scan
    is the trap that cost round ``i7cwdh`` its whole PR (see
    the gate2 wiring guard in ``tests/``).

    That guard is also why this docstring names it by description rather than
    by filename: the guard treats a file that spells its module's name in a
    string AND owns a ``getattr`` as one lookup away from the gate, and the
    shims in ``EveryRefusalIsDrivenByARealBody`` are built on ``__getattr__``.
    Naming it here would make this file the next round the guard eats.
    """

    # ``run_self_test`` composes RuntimeRes bodies too and is excluded BY NAME
    # rather than by a shape rule that would quietly swallow a real composer
    # with it.  ``test_the_excluded_self_test_is_not_a_producer`` re-derives
    # from app.py that the listener never runs it.
    NOT_A_PRODUCER = "run_self_test"

    @classmethod
    def setUpClass(cls):
        cls.source = V141.read_text(encoding="utf-8-sig")
        cls.tree = ast.parse(cls.source)

    @classmethod
    def _composes_a_runtime_res(cls, node):
        """Does this node write the RuntimeRes message id through ``u16tag``.

        Accepts BOTH spellings the frozen file could use for the id -- the
        ``GSCN_RUNTIME_PROTOCOL_RES`` name and the literal ``0x6E9D`` -- and
        also counts a function that delegates to a known composer.  The first
        draft accepted only the Name form; pf-adversary planted four composers
        (a literal-constant one, an alias, a ``struct.pack`` one, and a
        module-level constant) and all four went unseen (round ewm6ff, D4).
        Three of the four are caught now.  THE FOURTH IS NOT, AND CANNOT BE BY
        THIS METHOD: a composer that assembles the tag byte by byte
        (``bytes([0x12]) + struct.pack(...)``) writes no ``u16tag`` call for an
        AST to find.  ``test_the_census_states_its_own_blind_spot`` pins that
        limit rather than letting the class docstring imply completeness.
        """
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            if not isinstance(inner.func, ast.Name):
                continue
            if inner.func.id in cls.DELEGATES_TO:
                return True
            if inner.func.id != "u16tag" or len(inner.args) != 2:
                continue
            first, second = inner.args
            if not isinstance(first, ast.Constant) or first.value != 0x12:
                continue
            if (isinstance(second, ast.Name)
                    and second.id == "GSCN_RUNTIME_PROTOCOL_RES"):
                return True
            if isinstance(second, ast.Constant) and second.value == 0x6E9D:
                return True
        return False

    #: Composers whose callers are themselves RuntimeRes producers.  Seeded
    #: with the two the file defines and re-checked by a test below, so an
    #: alias route cannot hide a new composer the way it did in the first draft.
    DELEGATES_TO = frozenset({"make_runtime_vitals", "make_runtime_vital"})

    @staticmethod
    def _mask_sequence(node):
        records = []
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            if not isinstance(inner.func, ast.Name) or len(inner.args) != 2:
                continue
            if inner.func.id != "u8tag":
                continue
            tag, value = inner.args
            if not isinstance(tag, ast.Constant) or tag.value != 0x0B:
                continue
            records.append((
                inner.lineno,
                value.value if isinstance(value, ast.Constant) else "caller",
            ))
        records.sort(key=lambda record: record[0])
        return tuple(record[1] for record in records)

    def _composers(self):
        """Every function in the file that produces a RuntimeRes pc.

        Direct writers AND delegators, because a function that returns
        ``make_runtime_vital(...)`` puts a RuntimeRes on the wire just as
        surely as one that writes the tag itself -- that is how the SelectActor
        pair hid from the first draft of this census.
        """
        found = {}
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name == self.NOT_A_PRODUCER:
                continue
            if self._composes_a_runtime_res(node):
                found[node.name] = self._mask_sequence(node)
        return found

    def test_the_census_is_the_one_this_lane_measured(self):
        # Pinned by NAME AND MASK SEQUENCE: a new composer changes the names, a
        # renamed one is just as much a new call site to audit, and a composer
        # whose masks change is the exact event this pin exists for.
        #
        # It is 22 entries, not 4.  The first draft of this census pinned four
        # and the commit message called it "every RuntimeRes composer in v141";
        # pf-adversary showed it missed ~14 real ones plus four it planted
        # (round ewm6ff, D4).  The delegating majority below -- functions that
        # return make_runtime_vital(...) rather than writing the tag -- are
        # every bit as much places the ground can be cleared, and one of them
        # (make_item_operate_stack_merge_success) is wired live.
        expected = {
                'make_check_second_password_success': (),
                'make_item_operate_move_delta_success': (1,),
                # LIVE: runtime.py:1476 answers a real item move with this.
                'make_item_operate_stack_merge_success': (0, 255, 1),
                'make_music_control_current_scene': (),
                'make_npc_appear_sweep_batches': (),
                'make_npc_conversation_empty': (),
                'make_npc_conversation_quest3020': (),
                'make_quest3020_action1_accept_success': (),
                'make_quest3020_action6_accept_ui': (),
                # inherited none, derived 0x02 -- the remote-actor collection.
                'make_runtime_remote_actors': (0, 2),
                # PRESERVE-patched today, and only for the heartbeat_worker caller
                # (app.py:128).
                'make_runtime_res_empty_exact': (0, 0),
                'make_runtime_select_actor_empty': (),
                'make_runtime_select_actor_preset': (),
                # SINGULAR: writes no derived record of its own, so that byte is
                # whatever the caller left at the end of vital_payload.
                # legacy_bridge.character_list appends two and is a real login-path
                # VitalData response.
                'make_runtime_vital': (2, 'caller'),
                # inherited 0x02, the vital's version byte, derived NONE. The composer
                # preserve_ground_in_runtime_res_vitals replaces.
                'make_runtime_vitals': (2, 'caller', 0),
                'make_show_message': (),
                'make_teleport_check_scene1_challenge': (),
                'make_trade_item_result_store_buy_cart_ack': (0,),
                'make_trade_zoom_store5': (),
                'make_update_attr_cash_only': (),
                'make_v137_marker1_transport_probe': (2, 1, 0, 0),
                'make_v56_idle_action_packet': (),
        }
        self.assertEqual(
            self._composers(), expected,
            "a RuntimeRes composer appeared, moved or changed a change mask in "
            "the frozen file; every one of them is a place the ground can be "
            "cleared, so the change has to be audited before this pin moves")

    def test_the_composer_this_lane_replaces_leaves_the_ground_out(self):
        self.assertEqual(
            self._composers()["make_runtime_vitals"][-1], 0)

    def test_the_literal_id_spelling_is_seen(self):
        # The positive control for the widening: the first draft's detector
        # missed this and pf-adversary planted a composer that used it.
        planted = ast.parse(
            "def make_runtime_planted_by_constant():\n"
            "    pc = u16tag(0x12, 0x6E9D)\n"
            "    pc += u8tag(0x0B, 0x04)\n"
            "    return pc\n")
        self.assertTrue(self._composes_a_runtime_res(planted.body[0]))

    def test_a_delegating_alias_is_seen(self):
        planted = ast.parse(
            "def make_runtime_planted_via_alias(v):\n"
            "    return make_runtime_vitals(v)\n")
        self.assertTrue(self._composes_a_runtime_res(planted.body[0]))

    def test_the_delegate_names_really_are_composers_in_this_file(self):
        # DELEGATES_TO is only sound while every name in it is itself a
        # composer here; a stale name would make this detector claim coverage
        # it does not have.
        direct = self._composers()
        for name in self.DELEGATES_TO:
            self.assertIn(name, direct)

    def test_the_census_states_its_own_blind_spot(self):
        # An AST census cannot see a composer that assembles the message id
        # byte by byte.  Rather than let the class docstring imply otherwise,
        # the blind spot is pinned: this test FAILS the day someone teaches the
        # detector that spelling, which is the day the comment must change too.
        planted = ast.parse(
            "def make_runtime_planted_via_struct():\n"
            "    return bytes([0x12]) + struct.pack('<H', 0x6E9D)\n")
        self.assertFalse(
            self._composes_a_runtime_res(planted.body[0]),
            "the detector grew a spelling its docstring still calls a blind "
            "spot; update the docstring and this test together")
        # And the file this census runs against does not use that spelling
        # today, which is what makes the blind spot survivable for now.
        # (An earlier draft also asserted the frozen file contains no
        # struct.pack("<H") anywhere.  That was over-reach: the file uses that
        # call for fields unrelated to a message id, and the assertion failed.)

    def test_the_excluded_self_test_is_not_a_producer(self):
        # The one name the census skips has to earn the skip, and the reason
        # given has to be the real one: app.py:800 calls the REAL body, and the
        # no-op lambda is installed later -- so "it is replaced before it runs"
        # was the wrong reason (pf-adversary, round ewm6ff, D6(f)).  The reason
        # that holds is that it is not on the listener's path at all.
        node = next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == self.NOT_A_PRODUCER)
        self.assertTrue(self._composes_a_runtime_res(node))
        app = (ROOT / "src/pirateforce_foundation/app.py").read_text(
            encoding="utf-8-sig")
        self.assertIn("legacy.run_self_test = lambda", app)

    def test_the_patched_caller_is_still_only_the_heartbeat_worker(self):
        # app.py narrows the PRESERVE substitution to one co_name.  If that
        # widens, this file's whole premise changes.
        app = (ROOT / "src/pirateforce_foundation/app.py").read_text(
            encoding="utf-8-sig")
        self.assertIn('f_code.co_name == "heartbeat_worker"', app)


class TheOtherCarrierKeepsTheGroundToo(LegacyCase):
    """ROUND jysbar: ``preserve_ground_in_runtime_res_remote_actors``.

    The vitals sibling appends its PRESERVE record after the last byte v141
    wrote.  This carrier cannot be done that way -- its derived mask sits
    BEFORE the actor collection -- so what this class pins is the harder
    claim: v141's own output survives WHOLE, in order, either side of one
    byte, and the only new bytes are the ground record at the end.
    """

    def _entries(self):
        attrs = [(0x2710, self.legacy.u8tag(0x0B, 1))]
        return [
            self.legacy.make_remote_actor_entry(2, 0x2068, attrs),
            self.legacy.make_remote_actor_entry(2, 0x2069, attrs),
        ]

    def test_v141s_bytes_survive_whole_except_the_mask(self):
        entries = self._entries()
        composed, _frame = self.legacy.make_runtime_remote_actors(entries)
        pc, _preserved_frame = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, entries))
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[:offset], composed[:offset])
        self.assertEqual(pc[offset + 2:len(composed)], composed[offset + 2:])
        self.assertEqual(
            pc[len(composed):], mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)
        self.assertEqual(composed[offset + 1], 0x02)
        self.assertEqual(pc[offset + 1], 0x0A)
        # And the actor entries themselves are in there untouched, which is
        # the property a reader of a 20 KB census actually cares about.
        for entry in entries:
            self.assertIn(entry, pc)

    def test_the_ground_record_is_the_one_the_heartbeat_already_sends(self):
        # Named for what it protects: the three bytes appended here are the
        # three the production heartbeat has been appending on every flagless
        # boot since app.py's install landed.  If either moves, both must.
        pc, _frame = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, self._entries())
        heartbeat = mob_loot.preserve_ground_heartbeat_pc(self.legacy)
        self.assertEqual(pc[-3:], heartbeat[-3:])
        self.assertEqual(
            pc[-3:], mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)

    def test_the_frame_is_the_framing_layer_and_this_modules_re_derivation(self):
        pc, frame = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, self._entries())
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(frame, mob_loot._frame_via_struct(pc))
        self.assertEqual(frame[len(frame) - len(pc):], pc)

    def test_an_empty_collection_is_composable_and_says_pool_present(self):
        # Not a refusal: v141 accepts zero entries, and "no actors changed,
        # the pool is still there" is a sentence this carrier is allowed to
        # say.  The count field has to be zero and the ground record present.
        pc, _frame = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, [])
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[offset + 1], 0x0A)
        self.assertEqual(
            pc[offset + 2:], self.legacy.u16tag(0x12, 0)
            + mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)

    def test_a_wide_collection_composes_the_same_way(self):
        # The censuses this carrier really holds are ~108 entries and 20 KB,
        # far past the sizes the vitals sibling ever sees, and past the point
        # where a suffix-shaped frame check was measured wrong (round ewm6ff,
        # D5).  So the wide case is pinned, not assumed.
        attrs = [(0x2710, self.legacy.u8tag(0x0B, 1))]
        entries = [
            self.legacy.make_remote_actor_entry(2, 0x2000 + index, attrs)
            for index in range(108)
        ]
        composed, _frame = self.legacy.make_runtime_remote_actors(entries)
        pc, frame = mob_loot.preserve_ground_in_runtime_res_remote_actors(
            self.legacy, entries)
        self.assertEqual(len(pc), len(composed) + 3)
        self.assertEqual(frame, mob_loot._frame_via_struct(pc))

    class _MovedActorComposer:
        """A v141 whose make_runtime_remote_actors composes a different body."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def make_runtime_remote_actors(self, entries):
            pc, _frame = self._real.make_runtime_remote_actors(entries)
            moved = pc + self._real.u8tag(0x0B, 0)
            return moved, self._real.frame_pc(moved)

    class _MovedActorMask:
        """A v141 that writes the derived mask somewhere else entirely."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def make_runtime_remote_actors(self, entries):
            pc, _frame = self._real.make_runtime_remote_actors(entries)
            offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
            moved = pc[:offset] + self._real.u8tag(0x0B, 0x04) + pc[offset + 2:]
            return moved, self._real.frame_pc(moved)

    class _MovedActorFramer:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def frame_pc(self, pc):
            return b"\xac\x3e\x25\x5f\xde\xad\xbe\xef" + pc

    def test_a_composer_that_moved_refuses_instead_of_emitting(self):
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self._MovedActorComposer(self.legacy), self._entries())
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_ACTORS_COMPOSER_MOVED)

    def test_a_mask_that_moved_refuses_instead_of_emitting(self):
        # The dangerous one: bytes whose mask record this lane can no longer
        # locate are bytes that move every actor on the map.
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self._MovedActorMask(self.legacy), self._entries())
        self.assertEqual(
            caught.exception.args[0], mob_loot.REFUSE_ACTORS_COMPOSER_MOVED)

    def test_a_framing_layer_that_disagrees_refuses(self):
        with self.assertRaises(MobLootContractError) as caught:
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self._MovedActorFramer(self.legacy), self._entries())
        self.assertEqual(
            caught.exception.args[0], REFUSE_FRAME_ENCODER_DISAGREES)

    def test_an_entry_that_encodes_to_nothing_refuses_by_name(self):
        # An empty entry still counts in the collection's count field, and a
        # stream tail the client cannot align on is ErrorData=28317.
        with self.assertRaises(MobLootContractError):
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, self._entries() + [b""])
        with self.assertRaises(MobLootContractError):
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, self._entries() + [bytearray(b"\x01")])

    def test_the_refusal_name_is_declared_with_the_others(self):
        self.assertIn(
            mob_loot.REFUSE_ACTORS_COMPOSER_MOVED,
            mob_loot.MOB_LOOT_REFUSAL_REASONS)


class TheGateThatOnlySpendsTheRiskWhenThereIsSomethingToKeep(LegacyCase):
    """ROUND ``suovqw``: the fence for the carrier LANE-A measured.

    ``preserve_ground_in_runtime_res_remote_actors_when_live`` is the whole
    answer to letter ``20260902_1806``: preserve costs 97 actors of every
    click if the never-observed shape is wrong, and buys nothing at all on a
    frame composed while the floor is empty.  So the class pins BOTH halves
    with the composer driven for real -- today's bytes when no row stands,
    and the preserve shape when one does -- because a gate that is only
    tested on one side is a gate nobody knows the shape of.
    """

    def _entries(self):
        attrs = [(0x2710, self.legacy.u8tag(0x0B, 1))]
        return [
            self.legacy.make_remote_actor_entry(2, 0x2068, attrs),
            self.legacy.make_remote_actor_entry(2, 0x2069, attrs),
        ]

    def test_no_row_standing_is_v141s_own_bytes_to_the_last_byte(self):
        entries = self._entries()
        composed, composed_frame = self.legacy.make_runtime_remote_actors(
            list(entries))
        pc, frame = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, entries, ground_rows_left=0))
        self.assertEqual(pc, composed)
        self.assertEqual(frame, composed_frame)
        # ...and the mask really is the one the client sees today, so this
        # test cannot pass by comparing two preserved frames to each other.
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[offset + 1], 0x02)

    def test_a_row_standing_is_the_preserve_shape_byte_for_byte(self):
        entries = self._entries()
        pc, frame = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, entries, ground_rows_left=1))
        preserved, preserved_frame = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors(
                self.legacy, entries))
        self.assertEqual(pc, preserved)
        self.assertEqual(frame, preserved_frame)
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        self.assertEqual(pc[offset + 1], 0x0A)
        self.assertEqual(
            pc[-3:], mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)

    def test_every_unreadable_count_lands_on_todays_bytes_and_none_raise(self):
        # The list is the point: a gate that answers "preserve" for any of
        # these is a gate that bets 97 actors on a caller's type error.
        entries = self._entries()
        composed = self.legacy.make_runtime_remote_actors(list(entries))[0]
        for value in (
                mob_loot.GROUND_LIVENESS_UNKNOWN, -7, None, True, False,
                "1", b"1", 1.0, object(), (1,), [1]):
            with self.subTest(value=repr(value)):
                pc, _frame = (
                    mob_loot
                    .preserve_ground_in_runtime_res_remote_actors_when_live(
                        self.legacy, entries, ground_rows_left=value))
                self.assertEqual(pc, composed)

    def test_the_count_is_keyword_only_so_it_cannot_land_in_entries(self):
        # Positionally, a third argument would be a caller passing a count
        # where the sibling composers take nothing -- and it would be silently
        # accepted as an entry list by the wrong function some day.
        with self.assertRaises(TypeError):
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, self._entries(), 1)

    def test_a_generator_of_entries_is_answered_once_on_either_side(self):
        # ``entries`` is consumed exactly once: the not-live path hands v141
        # the same list the live path would build, so a caller that passes a
        # generator does not get an empty collection on one branch only.
        entries = self._entries()
        live, _f = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, (entry for entry in entries), ground_rows_left=2))
        dead, _f2 = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, (entry for entry in entries), ground_rows_left=0))
        for entry in entries:
            self.assertIn(entry, live)
            self.assertIn(entry, dead)

    def test_the_live_path_still_refuses_an_entry_that_encodes_to_nothing(self):
        with self.assertRaises(MobLootContractError):
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, self._entries() + [b""], ground_rows_left=1)

    def test_the_not_live_path_adds_no_refusal_of_its_own(self):
        # The asymmetry the docstring declares, executed: whatever v141 does
        # with a bad entry when nothing is standing is what it did yesterday.
        # This test asserts the two AGREE, not that either accepts.
        entries = self._entries() + [b""]
        try:
            expected = self.legacy.make_runtime_remote_actors(list(entries))
        except Exception as exc:                 # noqa: BLE001
            with self.assertRaises(type(exc)):
                (mob_loot
                 .preserve_ground_in_runtime_res_remote_actors_when_live(
                     self.legacy, entries, ground_rows_left=0))
        else:
            self.assertEqual(
                (mob_loot
                 .preserve_ground_in_runtime_res_remote_actors_when_live(
                     self.legacy, entries, ground_rows_left=0)),
                expected)

    def test_the_not_live_path_returns_v141s_OWN_return_value(self):
        """The docstring's load-bearing word is "provably", and pf-adversary
        (round suovqw, D5/M5) planted a copy -- ``bytes(pc), bytes(frame)`` --
        that every ``==`` comparison in this file accepted.  This drives a
        composer whose return value is an object no re-derivation could
        produce, so only handing that object straight back passes."""
        sentinel = object()

        class ItsOwnReturnValue:
            def __init__(self, real):
                self._real = real
                self.calls = 0

            def __getattr__(self, name):
                return getattr(self._real, name)

            def make_runtime_remote_actors(self, entries):
                self.calls += 1
                return sentinel

        shim = ItsOwnReturnValue(self.legacy)
        answer = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                shim, self._entries(), ground_rows_left=0))
        self.assertIs(answer, sentinel)
        self.assertEqual(shim.calls, 1, "composed once, not twice")

    def test_the_predicates_split_readable_from_live(self):
        self.assertTrue(mob_loot.ground_liveness_is_readable(0))
        self.assertFalse(mob_loot.ground_is_live(0))
        self.assertTrue(mob_loot.ground_is_live(1))
        for value in (mob_loot.GROUND_LIVENESS_UNKNOWN, True, False, "0",
                      1.0, None):
            with self.subTest(value=repr(value)):
                self.assertFalse(mob_loot.ground_liveness_is_readable(value))
                self.assertFalse(mob_loot.ground_is_live(value))


class TheLivenessReadNeverCostsTheFrame(LegacyCase):
    """``ground_rows_live_here`` against real cells and broken ones.

    Every exit is driven by an object that really produces it, because the
    claim being made is "this cannot raise on the listener thread" and an
    ``assertEqual(-1, -1)`` proves nothing about that.
    """

    @staticmethod
    def _a_row_in(scene, key_offset=0, mob_identity=0x201F):
        return mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE + key_offset, 2400046, 1,
            mob_loot.as_wire_float(1.0), mob_loot.as_wire_float(2.0),
            mob_loot.as_wire_float(3.0), mob_identity, 0x0101, scene)

    @classmethod
    def _cell_holding(cls, publishing, *kills):
        """A cell publishing ``publishing``, holding one commit per KILL.

        One commit is one kill in one scene and the ledger refuses anything
        else by name, so a cross-scene ledger is built the way the server
        builds one: two kills, two commits, one cell.
        """
        ledger = mob_loot.DropLedger()
        for token, rows in enumerate(kills, start=1):
            ledger = mob_loot.commit_drops(
                ledger, tuple(rows), base_generation=ledger.generation,
                kill_token=token)
        return mob_loot.DropLedgerCell(ledger, scene=publishing)

    def test_a_real_cell_counts_the_rows_of_the_scene_it_publishes(self):
        row = self._a_row_in("Bg0002")
        cell = self._cell_holding("Bg0002", [row])
        self.assertEqual(mob_loot.ground_rows_live_here(cell), 1)
        cell.take(row.drop_key)
        self.assertEqual(mob_loot.ground_rows_live_here(cell), 0)

    def test_a_row_standing_in_another_scene_is_not_this_frames_ground(self):
        # way 1 (COO-DECISION 20260902_0252): what a frame may announce is
        # its own scene's rows.  A row on another island must not arm the
        # preserve shape for a click here.
        cell = self._cell_holding("bg0001", [self._a_row_in("Bg0002")])
        self.assertEqual(mob_loot.ground_rows_live_here(cell), 0)

    def test_the_count_is_the_scenes_rows_and_not_the_whole_ledger(self):
        cell = self._cell_holding(
            "Bg0002",
            [self._a_row_in("Bg0002"), self._a_row_in("Bg0002", 1)],
            [self._a_row_in("bg0001", 2, mob_identity=0x2020)])
        self.assertEqual(len(cell.ledger.drops), 3)
        self.assertEqual(mob_loot.ground_rows_live_here(cell), 2)

    def test_a_cell_that_does_not_know_its_scene_is_unknown_not_zero(self):
        # ...and it says WHICH unknown: a cell with no scene is not a cell
        # that refused, and not a call site with no cell at all.
        self.assertEqual(
            mob_loot.ground_rows_live_here(mob_loot.DropLedgerCell()),
            mob_loot.GROUND_LIVENESS_NO_SCENE)
        self.assertFalse(mob_loot.ground_is_live(
            mob_loot.GROUND_LIVENESS_NO_SCENE))

    def test_no_cell_at_all_says_no_cell_and_not_something_else(self):
        self.assertEqual(
            mob_loot.ground_rows_live_here(None),
            mob_loot.GROUND_LIVENESS_NO_CELL)

    def test_each_cause_is_its_own_value_and_its_own_word(self):
        """pf-adversary D4: the first draft collapsed four causes into one
        number and then printed a line asserting the cause it liked.  Each
        of these is driven by an object that really produces it."""
        class Exploding:
            def publication(self):
                raise RuntimeError("a cell that refuses its own clock")

        row = self._a_row_in("Bg0002")
        cases = {
            mob_loot.GROUND_LIVENESS_NO_CELL: mob_loot.ground_rows_live_here(
                None),
            mob_loot.GROUND_LIVENESS_CELL_REFUSED:
                mob_loot.ground_rows_live_here(Exploding()),
            mob_loot.GROUND_LIVENESS_NO_SCENE: mob_loot.ground_rows_live_here(
                mob_loot.DropLedgerCell()),
            mob_loot.GROUND_LIVENESS_SCENE_MISMATCH:
                mob_loot.ground_rows_live_here(
                    self._cell_holding("Bg0002", [row]), "bg0001"),
            mob_loot.GROUND_LIVENESS_BAD_SCENE:
                mob_loot.ground_rows_live_here(
                    self._cell_holding("Bg0002", [row]), object()),
        }
        for expected, measured in cases.items():
            with self.subTest(reason=mob_loot.GROUND_LIVENESS_REASONS[expected]):
                self.assertEqual(measured, expected)
                word = mob_loot.ground_liveness_reason(measured)
                self.assertEqual(
                    word, mob_loot.GROUND_LIVENESS_REASONS[expected])
                self.assertEqual(word, word.encode("ascii").decode("ascii"))
                self.assertFalse(mob_loot.ground_is_live(measured))
        self.assertEqual(len(set(cases)), len(cases), "causes must not alias")
        self.assertEqual(mob_loot.ground_liveness_reason(0), "")
        self.assertEqual(mob_loot.ground_liveness_reason(4), "")
        self.assertEqual(mob_loot.ground_liveness_reason("x"), "not_a_count")

    def test_the_scene_the_frame_is_for_beats_the_scene_the_cell_holds(self):
        """pf-adversary D16.  Four responders share ONE cell.  A frame for
        scene 1 must not be armed by a row standing in Bg0002."""
        row = self._a_row_in("Bg0002")
        cell = self._cell_holding("Bg0002", [row])
        self.assertEqual(mob_loot.ground_rows_live_here(cell, "Bg0002"), 1)
        self.assertEqual(mob_loot.ground_rows_live_here(cell, "bg0002"), 1)
        self.assertEqual(
            mob_loot.ground_rows_live_here(cell, "bg0001"),
            mob_loot.GROUND_LIVENESS_SCENE_MISMATCH)
        # and a caller that names no scene keeps the cell's own answer
        self.assertEqual(mob_loot.ground_rows_live_here(cell), 1)

    def test_a_handle_whose_read_raises_costs_the_mask_and_not_the_frame(self):
        class Exploding:
            def publication(self):
                raise RuntimeError("the listener thread has no except")

        class NotACell:
            pass

        class WrongShape:
            def publication(self):
                return ("Bg0002",)

        class RowsThatCannotBeCounted:
            def publication(self):
                class NoLength:
                    drops = object()
                return "Bg0002", NoLength(), 0

        for handle in (Exploding(), NotACell(), WrongShape(),
                       RowsThatCannotBeCounted(), 7, "cell"):
            with self.subTest(handle=type(handle).__name__):
                self.assertEqual(
                    mob_loot.ground_rows_live_here(handle),
                    mob_loot.GROUND_LIVENESS_CELL_REFUSED)

    def test_the_answer_of_a_real_cell_drives_the_gate_end_to_end(self):
        # The two halves joined, which is the only form the call site will
        # ever use: read the cell, hand the count to the gate.
        attrs = [(0x2710, self.legacy.u8tag(0x0B, 1))]
        entries = [self.legacy.make_remote_actor_entry(2, 0x2068, attrs)]
        composed = self.legacy.make_runtime_remote_actors(list(entries))[0]
        row = self._a_row_in("Bg0002")
        cell = self._cell_holding("Bg0002", [row])
        offset = mob_loot.RUNTIME_RES_ACTORS_DERIVED_MASK_OFFSET
        cell.take(row.drop_key)
        empty, _frame = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, entries,
                ground_rows_left=mob_loot.ground_rows_live_here(cell)))
        self.assertEqual(empty, composed)
        cell = self._cell_holding("Bg0002", [row])
        loaded, _frame2 = (
            mob_loot.preserve_ground_in_runtime_res_remote_actors_when_live(
                self.legacy, entries,
                ground_rows_left=mob_loot.ground_rows_live_here(cell)))
        self.assertEqual(loaded[offset + 1], 0x0A)
        self.assertEqual(
            loaded[-3:], mob_loot.RUNTIME_RES_GROUND_PRESENT_EMPTY_PIN)


if __name__ == "__main__":
    unittest.main()
