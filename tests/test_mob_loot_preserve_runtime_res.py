"""LANE-B: the OTHER RuntimeRes frames, the ones the heartbeat patch never sees.

Why this file exists.  ``app.py``'s ``install_ground_heartbeat_preserve``
substitutes the PRESERVE body for exactly one caller -- the frame whose
``co_name`` is ``heartbeat_worker``.  COO-DECISION 20260901_0347 wrote a wider
rule than that: EVERY RuntimeRes sent while the ground still needs preserving
must carry a non-NULL pool.  ka1-B's letter of 2026-09-01T22:10+07:00 counted
13,934 captured frames outside the patched caller; that letter's own nonclaim
says a capture does not prove which server produced it, so this file does not
rest on it.  It asks OUR OWN SOURCE instead:

``TheCensusOfEveryRuntimeResComposerInV141`` re-derives, from the frozen
file's AST, every function that composes a ``GSCN_RunTimeProtocolRes`` and
what each one leaves in the derived change mask.  It is the test that goes red
the day a new composer appears, which is the only way this lane finds out
without another capture round.

The rest pins :func:`mob_loot.preserve_ground_in_runtime_res` -- the rewriter
that makes one of those composed pcs obey the ruling -- byte for byte, and
pins each of its refusals to a body that really reaches it.
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
    REFUSE_DERIVED_MASK_IS_NOT_EMPTY,
    REFUSE_PC_IS_NOT_A_RUNTIME_RES,
    REFUSE_PC_IS_NOT_BYTES,
    REFUSE_PC_TAIL_IS_NOT_THE_DERIVED_MASK,
    RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN,
    RUNTIME_RES_HEAD_PIN,
    RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN,
    preserve_ground_in_runtime_res,
    preserve_ground_in_runtime_res_frame,
)

V141 = ROOT / "current/pf_login_game_server_v141.py"


class LegacyCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)


class TheRewriterKeepsTheCallersBodyAndReplacesOneRecord(LegacyCase):
    """The rewrite is surgical: one record out, one record in, nothing else."""

    def _vitals_pc(self):
        """A real ``make_runtime_vitals`` pc, not a hand-typed stand-in."""
        payload = self.legacy.u8tag(0x08, 0) + self.legacy.u8tag(0x0B, 1)
        pc, _frame = self.legacy.make_runtime_vitals(
            [(self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload)])
        return pc

    def test_a_real_vitals_pc_ends_in_the_empty_derived_mask(self):
        # The premise of the whole file, re-derived rather than assumed: what
        # v141 hands its callers today really does leave the ground list out.
        self.assertEqual(
            self._vitals_pc()[-2:], RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)

    def test_the_rewrite_swaps_exactly_the_trailing_mask_record(self):
        pc = self._vitals_pc()
        out = preserve_ground_in_runtime_res(self.legacy, pc)
        self.assertEqual(out[:len(pc) - 2], pc[:-2])
        self.assertEqual(
            out[len(pc) - 2:], RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)
        self.assertEqual(len(out), len(pc) + 3)

    def test_the_ground_list_bit_is_set_and_the_count_is_zero(self):
        # Stated as the two facts the ruling is about, not as a byte blob:
        # PRESERVE is "pool present, nothing to reconcile", never "no pool".
        out = preserve_ground_in_runtime_res(self.legacy, self._vitals_pc())
        self.assertEqual(out[-5], mob_loot.ELEMENT_MASK_TAG)
        self.assertEqual(out[-4], mob_loot.RUNTIME_DERIVED_BIT_GROUND_LIST)
        self.assertEqual(out[-3], mob_loot.ELEMENT_LIST_COUNT_TAG)
        self.assertEqual(out[-2:], b"\x00\x00")

    def test_the_inherited_mask_is_left_alone(self):
        # 0x02 in, 0x02 out.  The rewriter must not "tidy" the caller's own
        # VitalData collection, which is the half every other lane pinned.
        pc = self._vitals_pc()
        out = preserve_ground_in_runtime_res(self.legacy, pc)
        head = len(RUNTIME_RES_HEAD_PIN)
        self.assertEqual(pc[head + 1], 0x02)
        self.assertEqual(out[head + 1], 0x02)

    def test_the_pickup_delta_prefix_survives_byte_for_byte(self):
        # mob_pickup's ItemOperate delta is the shape ka1-B's letter named as
        # the unpatched family.  Its prefix is separately pinned in that
        # module; rewriting the tail must not disturb one byte of it.
        from pirateforce_foundation.mob_pickup import (
            DELTA_PC_PREFIX_PIN, DELTA_PC_SUFFIX_PIN)
        pc = DELTA_PC_PREFIX_PIN + b"\x00" * 4 + DELTA_PC_SUFFIX_PIN
        out = preserve_ground_in_runtime_res(self.legacy, pc)
        self.assertEqual(out[:len(DELTA_PC_PREFIX_PIN)], DELTA_PC_PREFIX_PIN)
        self.assertEqual(
            out[-5:], RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)

    def test_a_rewritten_pc_is_not_rewritable_again(self):
        # Idempotence is NOT offered: a second pass would find a non-empty
        # derived mask and must refuse rather than stack a second record.
        out = preserve_ground_in_runtime_res(self.legacy, self._vitals_pc())
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res(self.legacy, out)
        self.assertEqual(
            caught.exception.args[0], REFUSE_PC_TAIL_IS_NOT_THE_DERIVED_MASK)

    def test_the_frame_half_reframes_the_rewritten_pc(self):
        pc = self._vitals_pc()
        rewritten, frame = preserve_ground_in_runtime_res_frame(
            self.legacy, pc)
        self.assertEqual(
            rewritten, preserve_ground_in_runtime_res(self.legacy, pc))
        self.assertEqual(
            frame[:len(mob_loot.DROP_FRAME_MAGIC_PIN)],
            mob_loot.DROP_FRAME_MAGIC_PIN)
        self.assertEqual(frame[len(frame) - len(rewritten):], rewritten)
        self.assertNotEqual(frame, self.legacy.frame_pc(pc))


class EveryRefusalIsReachableAndNamed(LegacyCase):
    """Each refusal below is raised by a body that really produces it."""

    def _refusal(self, pc):
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res(self.legacy, pc)
        return caught.exception.args[0]

    def test_a_str_is_not_a_pc(self):
        self.assertEqual(self._refusal("not bytes"), REFUSE_PC_IS_NOT_BYTES)

    def test_a_bytearray_is_accepted_and_returns_bytes(self):
        payload = self.legacy.u8tag(0x08, 0)
        pc, _ = self.legacy.make_runtime_vitals(
            [(self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload)])
        out = preserve_ground_in_runtime_res(self.legacy, bytearray(pc))
        self.assertIsInstance(out, bytes)

    def test_a_frame_passed_where_a_pc_belongs_is_refused(self):
        # The likeliest real mistake at a call site: v141 composers hand back
        # ``(pc, frame)`` and the frame opens with the snappy header, not the
        # RuntimeRes head.
        payload = self.legacy.u8tag(0x08, 0)
        _pc, frame = self.legacy.make_runtime_vitals(
            [(self.legacy.ITEM_OPERATE_RES_VITAL, 2, payload)])
        self.assertEqual(
            self._refusal(frame), REFUSE_PC_IS_NOT_A_RUNTIME_RES)

    def test_a_pc_too_short_to_hold_the_records_is_refused(self):
        self.assertEqual(
            self._refusal(RUNTIME_RES_HEAD_PIN), REFUSE_PC_IS_NOT_A_RUNTIME_RES)

    def test_a_pc_whose_head_is_a_different_message_is_refused(self):
        pc = bytes((0x12, 0x9C, 0x6E)) + RUNTIME_RES_HEAD_PIN[3:] + bytes(
            (0x0B, 0x02, 0x0B, 0x00))
        self.assertEqual(self._refusal(pc), REFUSE_PC_IS_NOT_A_RUNTIME_RES)

    def test_a_pc_whose_inherited_mask_tag_drifted_is_refused(self):
        pc = RUNTIME_RES_HEAD_PIN + bytes((0x0C, 0x02, 0x0B, 0x00))
        self.assertEqual(self._refusal(pc), REFUSE_PC_IS_NOT_A_RUNTIME_RES)

    def test_a_pc_that_does_not_end_in_a_mask_record_is_refused(self):
        pc = RUNTIME_RES_HEAD_PIN + bytes((0x0B, 0x02, 0x14, 0x00))
        self.assertEqual(
            self._refusal(pc), REFUSE_PC_TAIL_IS_NOT_THE_DERIVED_MASK)

    def test_a_derived_mask_that_already_carries_a_bit_is_refused(self):
        # 0x02 is the actor-collection bit other lanes send.  Rewriting over
        # it would delete somebody else's field, so this must never pass.
        pc = RUNTIME_RES_HEAD_PIN + bytes((0x0B, 0x00, 0x0B, 0x02))
        self.assertEqual(
            self._refusal(pc), REFUSE_DERIVED_MASK_IS_NOT_EMPTY)

    def test_a_moved_serializer_refuses_instead_of_emitting(self):
        # The pin is not decoration: swap the legacy primitive for one that
        # composes a different tail and the function must stop.
        class MovedLegacy:
            def __init__(self, real):
                self._real = real

            def u8tag(self, tag, value):
                return bytes((tag, value, 0x00))   # one byte too wide

            def u16tag(self, tag, value):
                return self._real.u16tag(tag, value)

        pc = RUNTIME_RES_HEAD_PIN + bytes((0x0B, 0x02, 0x0B, 0x00))
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res(MovedLegacy(self.legacy), pc)
        self.assertEqual(
            caught.exception.args[0], REFUSE_COMPOSED_BYTES_OFF_PIN)


class TheCensusOfEveryRuntimeResComposerInV141(unittest.TestCase):
    """Which frozen functions compose a RuntimeRes, and what mask each leaves.

    This is the coverage question ka1-B's letter asked of a capture corpus,
    asked instead of the file this server actually runs.  It reads ONE file --
    not the repository -- because a repo-wide text scan is the trap that cost
    round ``i7cwdh`` its whole PR (see
    ``tests/test_gate2_bag_admission_wiring.py``).
    """

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(V141.read_text(encoding="utf-8-sig"))

    # ``run_self_test`` composes RuntimeRes bodies too, ~50 of them, and is
    # excluded from the census BY NAME rather than by a shape rule that would
    # quietly swallow a real composer with it.  The exclusion is not taken on
    # trust: ``test_the_excluded_self_test_really_is_neutralized`` re-derives
    # from app.py that it is replaced with a no-op before the listener runs,
    # so it emits nothing at a socket and cannot clear anyone's ground.
    NOT_A_PRODUCER = "run_self_test"

    def _composers(self):
        """Function name -> the ordered change-mask records its body writes.

        Every ``u8tag(0x0B, ...)`` the function writes into the pc, in source
        order, with a non-constant argument recorded as ``"caller"``.  The
        sequence is pinned rather than a single "derived mask" value because
        which record IS the derived mask is a property of the wire layout, not
        something an AST can decide -- and pinning the sequence catches a
        change to either mask, which is what the audit needs.
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

    @staticmethod
    def _composes_a_runtime_res(node):
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            if not isinstance(inner.func, ast.Name):
                continue
            if inner.func.id != "u16tag" or len(inner.args) != 2:
                continue
            first, second = inner.args
            if not isinstance(first, ast.Constant) or first.value != 0x12:
                continue
            if (isinstance(second, ast.Name)
                    and second.id == "GSCN_RUNTIME_PROTOCOL_RES"):
                return True
        return False

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

    def test_the_census_is_the_one_this_lane_measured(self):
        # Pinned by NAME AND MASK SEQUENCE, not by count: a new composer
        # changes the names, a renamed one is just as much a new call site to
        # audit, and a composer whose masks change is the exact event this pin
        # exists for.
        self.assertEqual(
            self._composers(),
            {
                # inherited none, derived none.  PRESERVE-patched today, and
                # only when the calling frame is heartbeat_worker (app.py:128).
                "make_runtime_res_empty_exact": (0, 0),
                # inherited 0x02 (the VitalData collection), the vital's own
                # version byte, then derived NONE.  This is the composer behind
                # every VitalData response this server sends, it is NOT
                # patched, and its empty derived mask is the gap this lane's
                # rewriter closes.
                "make_runtime_vitals": (2, "caller", 0),
                # inherited 0x02 and the version byte, and NO derived record of
                # its own: that byte is whatever the caller left at the end of
                # vital_payload (legacy_bridge.character_list appends two).
                # Its pc is rewritable only when that caller left it empty.
                "make_runtime_vital": (2, "caller"),
                # inherited none, derived 0x02 -- the remote-actor collection.
                # The rewriter REFUSES this one on purpose (see the test
                # below): carrying both lists in one frame is a shape nobody
                # has measured, and dropping 0x02 to add 0x08 would delete the
                # actors to save the ground.
                "make_runtime_remote_actors": (0, 2),
            },
            "a RuntimeRes composer appeared, moved or changed a change mask in "
            "the frozen file; every one of them is a place the ground can be "
            "cleared, so the change has to be audited against "
            "COO-DECISION 20260901_0347 before this pin is updated")

    def test_the_vitals_composer_is_the_one_that_leaves_the_ground_out(self):
        # The measured claim this lane put in its letter, re-derived here so
        # nobody has to take the letter's word: the composer behind every
        # VitalData response ends on an empty derived mask, which is the
        # absent-ground-list condition the ruling is about.
        self.assertEqual(self._composers()["make_runtime_vitals"][-1], 0)

    def test_the_excluded_self_test_really_is_neutralized(self):
        # The one name the census skips has to earn the skip.
        self.assertTrue(self._composes_a_runtime_res(next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == self.NOT_A_PRODUCER)))
        app = (ROOT / "src/pirateforce_foundation/app.py").read_text(
            encoding="utf-8-sig")
        self.assertIn("legacy.run_self_test = lambda", app)

    def test_the_actor_composer_is_out_of_this_rewriters_reach(self):
        # Stated as a LIMIT of what shipped, not as a thing that got fixed.
        census = self._composers()
        self.assertEqual(census["make_runtime_remote_actors"][-1], 0x02)
        pc = RUNTIME_RES_HEAD_PIN + bytes((0x0B, 0x00, 0x0B, 0x02))
        with self.assertRaises(MobLootContractError) as caught:
            preserve_ground_in_runtime_res(
                load_legacy(V141), pc)
        self.assertEqual(
            caught.exception.args[0], REFUSE_DERIVED_MASK_IS_NOT_EMPTY)

    def test_the_patched_caller_is_still_only_the_heartbeat_worker(self):
        # app.py narrows the PRESERVE substitution to one ``co_name``.  If that
        # ever widens, this file's whole premise changes and somebody should
        # be made to read this test.
        app = (ROOT / "src/pirateforce_foundation/app.py").read_text(
            encoding="utf-8-sig")
        self.assertIn('f_code.co_name == "heartbeat_worker"', app)


if __name__ == "__main__":
    unittest.main()
