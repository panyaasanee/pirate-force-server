"""LANE-CS: `skill_learn_roundtrip` -- the first path in this tree that
charges a skill point, writes the row AND composes the client's
confirmation frame in one call.

The harness is `tests/test_skill_grant_wiring.py`'s, deliberately: the
round trip is a composer over that module, and running it against the same
real migrated store (plus the same fake for injecting a mid-grant failure)
is what keeps this file from proving that two of this lane's own fakes
agree with each other.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    lifecycle,
    skill_learn_roundtrip,
    skill_list_at_login,
    skill_learn_validator,
    skill_learn_wiring,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.learn_skill_result_frame import (  # noqa: E402
    LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
    decode_learn_skill_result_payload,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x30014000, 0x30015000))

#: Skill 99 ("Normal Attack") costs exactly 1.0 skill point.
_WHOLE_COST_SKILL_ID = 99


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _FakeGrantStore:
    """The real store for every call but `grant_learned_skill`.

    Only the grant is faked, and only so a mid-grant failure can be
    injected -- the window this module exists to stop being silent about
    cannot be reached any other way without corrupting a real database.
    """

    def __init__(self, store: SQLiteStore):
        self._store = store
        self._granted: "dict[int, list[int]]" = {}
        self._raise_on_grant: "Exception | None" = None
        self.grant_calls: "list[tuple[int, int]]" = []

    def fail_next_grant(self, exc: Exception) -> None:
        self._raise_on_grant = exc

    def get_skill_points(self, character_id):
        return self._store.get_skill_points(character_id)

    def spend_skill_points(self, character_id, cost):
        return self._store.spend_skill_points(character_id, cost)

    def read_character_vitals_or_none(self, character_id):
        # The level gate landed on `main` in #1166 and reads through this
        # door; the fake delegates it so the level a refusal is measured
        # against is the level a login would read, not one written here.
        return self._store.read_character_vitals_or_none(character_id)

    def grant_learned_skill(self, character_id, skill_id):
        self.grant_calls.append((character_id, skill_id))
        if self._raise_on_grant is not None:
            exc, self._raise_on_grant = self._raise_on_grant, None
            raise exc
        existing = self._granted.setdefault(character_id, [])
        if skill_id not in existing:
            existing.append(skill_id)
        return tuple(existing)


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(Path(self.tmp.name) / "state.sqlite3",
                                 MIGRATIONS)
        self.store.migrate()
        self.fake = _FakeGrantStore(self.store)

    def _make_character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )


class TheClientIsToldTests(_Fixture):
    """The half that was missing: bytes, not just a row."""

    def test_a_successful_learn_composes_a_frame_that_re_decodes(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertTrue(result.learned)
        self.assertEqual(4, result.points_remaining)
        self.assertEqual((_WHOLE_COST_SKILL_ID,), result.skills_after_grant)
        self.assertIsNotNone(result.pc)
        self.assertIsNotNone(result.frame)
        # The bytes are read back out of the composed pc, not out of the
        # values that were handed to the encoder.
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        records, trailing = decode_learn_skill_result_payload(
            result.pc[start:start + 5 + 13]
        )
        self.assertEqual(1, len(records))
        self.assertEqual(_WHOLE_COST_SKILL_ID, records[0].record_u32_0)
        self.assertEqual(4, records[0].record_u32_8)
        self.assertEqual(0, trailing)

    def test_the_record_members_constant_is_read_and_checked_here(self):
        """pf-adversary round `mfgv4m`, D7(b): `git grep
        RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN` under `src/ tests/ docs/`
        found exactly one hit -- its own definition -- so nothing would
        notice if the string and the real field assignment in
        `learn_skill_round_trip` drifted apart.  This test is the second
        hit: it parses the constant's own text and checks the real encoded
        record against what the text claims, so an edit to either side
        alone turns this test red.
        """
        mapping = dict(
            part.split("=", 1) for part in
            skill_learn_roundtrip.RECORD_MEMBERS_ARE_THIS_PROJECTS_DESIGN
            .split(", ")
        )
        self.assertEqual("skill_id", mapping["record_u32_0"])
        self.assertEqual("0", mapping["record_u16_4"])
        self.assertEqual("points_remaining", mapping["record_u32_8"])

        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        records, _trailing = decode_learn_skill_result_payload(
            result.pc[start:start + 5 + 13]
        )
        # The constant says record_u32_0 carries skill_id and record_u32_8
        # carries points_remaining -- checked against the two numbers this
        # same call already measured independently above, not re-derived.
        self.assertEqual(result.skill_id, records[0].record_u32_0)
        self.assertEqual(int(mapping["record_u16_4"]), records[0].record_u16_4)
        self.assertEqual(result.points_remaining, records[0].record_u32_8)

    def test_the_row_and_the_balance_really_moved_in_the_database(self):
        """The second layer, and it is not the frame.

        The frame proves what would go on the wire; this proves what the
        database now holds.  Neither is read out of the other.
        """
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 3, "level": 40})
        skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(2, self.store.get_skill_points(character.id))
        self.assertEqual(
            [(character.id, _WHOLE_COST_SKILL_ID)], self.fake.grant_calls,
        )

    def test_no_frame_travels_with_a_refusal(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(skill_learn_roundtrip.OUTCOME_REFUSED, result.outcome)
        self.assertIsNone(result.pc)
        self.assertIsNone(result.frame)
        self.assertEqual([], self.fake.grant_calls)
        self.assertEqual(0, self.store.get_skill_points(character.id))


class TheWindowBetweenTheSpendAndTheGrantTests(_Fixture):
    """`learn_and_grant_skill` is two store calls; this lane may not close
    that window, but it may refuse to let it be silent."""

    def test_a_grant_that_raises_after_the_spend_is_named_not_swallowed(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        self.fake.fail_next_grant(RuntimeError("character_skills is gone"))
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(
            skill_learn_roundtrip.OUTCOME_SPENT_BUT_NOT_GRANTED,
            result.outcome,
        )
        # Measured, not assumed: the point really is gone from the row.
        self.assertEqual(4, self.store.get_skill_points(character.id))
        self.assertEqual(5, result.points_before)
        self.assertEqual(4, result.points_remaining)
        self.assertIsNone(result.pc)

    def test_a_refusal_before_the_spend_is_not_reported_as_a_lost_point(self):
        """The outcome is decided by re-reading the balance, so a refusal
        that never spent anything must not borrow the loud name."""
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 1, "level": 39})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, 2950,
        )
        self.assertEqual(skill_learn_roundtrip.OUTCOME_REFUSED, result.outcome)
        self.assertEqual(1, self.store.get_skill_points(character.id))
        self.assertEqual([], self.fake.grant_calls)

    def test_when_the_re_read_itself_fails_the_outcome_says_unknown_not_refused(self):
        """pf-adversary round `mfgv4m`, D4: before this round, a grant that
        raised AND a re-read that also raised (`points_after is None`, e.g.
        "database is locked") fell through to `OUTCOME_REFUSED` -- the
        outcome that promises nothing was spent -- with no test covering
        that branch.  A point may genuinely be gone here; this pins that
        the caller is told "unknown", never told "refused".
        """
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        self.fake.fail_next_grant(RuntimeError("character_skills is gone"))

        real_get_skill_points = self.fake.get_skill_points
        seen: "list[int]" = []

        def _re_read_fails_on_third_call(character_id):
            seen.append(character_id)
            if len(seen) >= 3:
                raise RuntimeError("database is locked")
            return real_get_skill_points(character_id)

        self.fake.get_skill_points = _re_read_fails_on_third_call

        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(
            skill_learn_roundtrip.OUTCOME_SPEND_STATUS_UNKNOWN, result.outcome,
        )
        self.assertNotEqual(skill_learn_roundtrip.OUTCOME_REFUSED, result.outcome)
        self.assertEqual(5, result.points_before)
        # The re-read failed, so `points_remaining` falls back to the last
        # value this call actually measured (`points_before`) rather than
        # inventing a number the failed read never produced.
        self.assertEqual(5, result.points_remaining)
        self.assertIsNone(result.pc)
        self.assertIn(
            "RESULT=NOT_TOLD", skill_learn_roundtrip.headless_token(result),
        )


class TheRefusalReachesTheConsoleByNameTests(_Fixture):
    """A refusal an operator reads as a class name is a refusal nobody can
    act on.

    `SkillLearnValidatorError` carried its refusal only inside a sentence
    that interpolates ids, balances and levels; the round trip's token
    printed `reason=SkillLearnValidatorError` for every one of them.  The
    named half now travels beside the sentence -- matching on
    `error.args[0]` is the defect this lane was burned by in round
    `ixbs2f`, so nothing here reads the sentence.
    """

    def test_a_level_refusal_reaches_the_token_under_its_own_name(self):
        character = self._make_character()
        self.store.write_typed_attributes(
            character.id, {"skill_points": 99, "level": 39},
        )
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, 2950,
        )
        self.assertEqual(
            skill_learn_validator.REFUSED_LEVEL_TOO_LOW, result.reason,
        )
        self.assertIn(
            "reason=" + skill_learn_validator.REFUSED_LEVEL_TOO_LOW,
            skill_learn_roundtrip.headless_token(result),
        )
        # And the refusal really did cost her nothing.
        self.assertEqual(99, self.store.get_skill_points(character.id))

    def test_the_reason_is_never_the_human_sentence(self):
        character = self._make_character()
        self.store.write_typed_attributes(
            character.id, {"skill_points": 99, "level": 39},
        )
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, 2950,
        )
        self.assertNotIn(" ", result.reason)
        # The sentence is a paragraph; the token must carry the name only.
        self.assertNotIn(
            "cannot learn skill", skill_learn_roundtrip.headless_token(result),
        )
        skill_learn_roundtrip.headless_token(result).encode("cp874")

    def test_an_unadjudicated_level_is_named_too(self):
        """The other raise site in the wiring layer, which `refusal_to_learn`
        never sees because there is no level to hand it.

        A character created today gets an adjudicated level from the store
        itself (measured while writing this: the door answers for a fresh
        row), so the door is the thing faked here -- exactly and only the
        answer "nobody has adjudicated a level", which is what that raise
        site exists for.
        """
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        store, character_id = self.fake, character.id

        class _NoLevelStore:
            def get_skill_points(self, cid):
                return store.get_skill_points(cid)

            def spend_skill_points(self, cid, cost):
                return store.spend_skill_points(cid, cost)

            def read_character_vitals_or_none(self, cid):
                return None

            def grant_learned_skill(self, cid, skill_id):
                raise AssertionError("nothing may be granted")

        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, _NoLevelStore(), character_id, 99,
        )
        self.assertEqual(
            skill_learn_wiring.REFUSED_LEVEL_NEVER_ADJUDICATED,
            result.reason,
        )
        self.assertEqual(5, self.store.get_skill_points(character_id))


class TheRefusalsThatComeBeforeAnyPointIsSpentTests(_Fixture):
    def test_a_fresh_character_carries_a_measured_zero_not_a_null(self):
        """Measured while writing the test above, and worth keeping.

        `migrations/017` materialises `skill_points INTEGER DEFAULT 0`, so a
        character created today answers `0`, not `None` -- the unmeasured
        branch is reachable only on a row written before that migration.
        Writing this down is what stops a later round from "fixing" the
        unmeasured refusal by deleting it as dead code.
        """
        character = self._make_character()
        self.assertEqual(0, self.store.get_skill_points(character.id))

    def test_an_unmeasured_balance_refuses_and_never_spends(self):
        """A NULL balance cannot be produced through any store method this
        lane may call, so the store is faked for exactly that one answer --
        every other call in this file goes to the real migrated database."""

        class _NullBalanceStore:
            def __init__(self):
                self.spend_calls = []

            def get_skill_points(self, character_id):
                return None

            def spend_skill_points(self, character_id, cost):
                self.spend_calls.append((character_id, cost))
                raise AssertionError("nothing may be spent on a NULL balance")

            def grant_learned_skill(self, character_id, skill_id):
                raise AssertionError("nothing may be granted either")

        store = _NullBalanceStore()
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, store, 1, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(
            skill_learn_roundtrip.REFUSE_BALANCE_UNMEASURED, result.reason,
        )
        self.assertEqual([], store.spend_calls)

    def test_a_store_that_cannot_grant_is_refused_before_the_spend(self):
        """The finding this check exists for: without it the point is spent
        and only then does the missing method raise."""
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})

        class _SpendOnlyStore:
            def __init__(self, store):
                self._store = store

            def get_skill_points(self, character_id):
                return self._store.get_skill_points(character_id)

            def spend_skill_points(self, character_id, cost):
                return self._store.spend_skill_points(character_id, cost)

            def read_character_vitals_or_none(self, character_id):
                return self._store.read_character_vitals_or_none(character_id)

        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, _SpendOnlyStore(self.store), character.id,
            _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(
            skill_learn_roundtrip.REFUSE_STORE_CANNOT_GRANT, result.reason,
        )
        self.assertEqual(5, self.store.get_skill_points(character.id))

    def test_non_int_arguments_are_refused_by_name(self):
        self.assertEqual(
            skill_learn_roundtrip.REFUSE_CHARACTER_ID_NOT_AN_INT,
            skill_learn_roundtrip.preflight_refusal(self.fake, True, 99),
        )
        self.assertEqual(
            skill_learn_roundtrip.REFUSE_SKILL_ID_NOT_AN_INT,
            skill_learn_roundtrip.preflight_refusal(self.fake, 1, "99"),
        )


class TheTokenMeasuresTheArtifactTests(_Fixture):
    def test_the_token_counts_records_off_the_composed_pc(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        line = skill_learn_roundtrip.headless_token(result)
        self.assertIn("records=1", line)
        self.assertIn("trailing_u8=0", line)
        self.assertIn("frame_bytes=%d" % (len(result.frame),), line)
        self.assertIn("RESULT=TOLD", line)
        line.encode("ascii")
        line.encode("cp874")

    def test_a_refusal_prints_not_told_and_zero_records(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        line = skill_learn_roundtrip.headless_token(result)
        self.assertIn("RESULT=NOT_TOLD", line)
        self.assertIn("records=0", line)
        self.assertIn("frame_bytes=0", line)

    def test_the_result_word_is_not_typed_into_the_format_string(self):
        """A pc that carries no records must not read `TOLD`, whatever the
        outcome field says -- the D3 shape, one module to the left."""
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        start = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        emptied = bytearray(result.pc)
        emptied[start + 1:start + 3] = (0).to_bytes(2, "little")
        stripped = type(result)(
            result.outcome, result.reason, result.character_id,
            result.skill_id, result.points_before, result.points_remaining,
            result.skills_after_grant, bytes(emptied), result.frame,
        )
        self.assertIn("RESULT=NOT_TOLD",
                      skill_learn_roundtrip.headless_token(stripped))

    def test_skill_and_points_in_the_token_come_off_the_wire_not_the_fields(self):
        """pf-adversary round `mfgv4m`, D6: `skill=` and `points=` in the
        token used to be typed straight from `result.skill_id`/
        `result.points_remaining` -- so a composer bug that put the WRONG
        values on the wire would still print a token that read TOLD with
        the caller's own numbers, matching nothing it actually sent.  This
        builds exactly that lie (same shape as the test above: a real pc
        paired with fields that disagree with it) and checks the token
        reports what the bytes carry, not what the fields claim.
        """
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5, "level": 40})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        lying = type(result)(
            outcome=result.outcome, reason=result.reason,
            character_id=result.character_id,
            skill_id=999999, points_before=result.points_before,
            points_remaining=999999,
            skills_after_grant=result.skills_after_grant,
            pc=result.pc, frame=result.frame,
        )
        line = skill_learn_roundtrip.headless_token(lying)
        self.assertIn("skill=%d" % _WHOLE_COST_SKILL_ID, line)
        self.assertNotIn("skill=999999", line)
        self.assertIn("points=4", line)
        self.assertNotIn("points=999999", line)
        # cid is the one field this vital's bytes never carry (see the
        # module NONCLAIMS) -- it is unavoidably the argument's own value.
        self.assertIn("cid=%d" % character.id, line)


class LearningAFifthSkillCollidesWithTheLoginCapTests(_Fixture):
    """FLIPPED THIS ROUND (PANYA `2220` / COO-DECISION `20260909_1312`,
    LANE-CS) -- direction reversed, class name kept so the history of the
    collision this pins stays attached to it.

    Until this round, `skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT`
    was 4 -- the largest count a real client had ever been measured
    accepting (`GT-249`) -- and `COO-DECISION 20260908_1742` froze it there
    until an attended result moved it.  This test used to pin that a fifth
    row made the login route return a named refusal, unsent -- a claim
    about that function's Python return value, never an observation of any
    client screen (pf-adversary round `mfgv4m`, D8: the module's own
    NONCLAIMS disclaim any client-rendering claim, and this docstring's
    earlier "empty skill window on screen" wording read as one anyway).

    PANYA `2220`: no more self-imposed ceilings for "not yet measured";
    unmeasured is a reason to SEND and record what happens, not a reason to
    refuse in advance.  The COO-DECISION named above retires the cap and
    the refusal outright -- `OBSERVED_ACCEPTED_RECORD_COUNT` and
    `REFUSE_TOO_MANY_UNMEASURED` no longer exist in
    `skill_list_at_login` (`git grep` for both returns nothing under
    `src/`).  This test now pins the opposite: a character who has learned
    a fifth skill gets a login frame that CARRIES ALL FIVE rows, composed
    and decodable, same as it would for four or forty -- the u16 wire field
    (`WIRE_MAX_RECORDS`) is the only ceiling left, and this test is nowhere
    near it. No skip, no xfail (`2050`).
    """

    def test_the_fifth_row_is_sent_not_refused(self):
        character = self._make_character()
        self.store.write_typed_attributes(
            character.id, {"skill_points": 99, "level": 40},
        )
        lifecycle.grant_starting_skills_for_class(self.store, character, 1)
        before = skill_list_at_login.read_character_skill_ids(
            self.store, character.id,
        )
        self.assertEqual(4, len(before))
        pc, _frame = skill_list_at_login.make_skill_list_response(
            self.legacy, before,
        )
        self.assertEqual(4, skill_list_at_login.measured_record_count(pc))

        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.store, character.id, 2950,
        )
        self.assertTrue(result.learned)
        after = skill_list_at_login.read_character_skill_ids(
            self.store, character.id,
        )
        self.assertEqual(len(before) + 1, len(after))
        self.assertEqual(5, len(after))

        # PANYA `2220`: this used to be `assertRaises(...REFUSE_TOO_MANY_
        # UNMEASURED)`. It is now a plain compose -- the fifth row goes out
        # exactly like the first four, no special case, no named refusal.
        pc_after, frame_after = skill_list_at_login.make_skill_list_response(
            self.legacy, after,
        )
        self.assertEqual(
            5, skill_list_at_login.measured_record_count(pc_after),
        )
        self.assertEqual(
            0, skill_list_at_login.measured_trailing_byte(pc_after, 5),
        )
        self.assertEqual(
            tuple(sorted(after)),
            tuple(sorted(
                record.record_u32_0
                for record in skill_list_at_login.skill_list_records(after)
            )),
        )
        self.assertGreater(len(frame_after), 0)


class LearningTheSameSkillTwiceTests(_Fixture):
    """pf-adversary round `8wzpyw`, D1 -- the worst thing this module
    shipped with, paid in the same round it was found.

    `grant_learned_skill` is `INSERT OR IGNORE`.  Clicking "learn" twice on
    a skill she already holds wrote nothing the second time and charged her
    anyway: three clicks measured as three points gone, one row, and
    `outcome=learned RESULT=TOLD` every time.
    """

    def _character_at_forty(self):
        character = self._make_character()
        self.store.write_typed_attributes(
            character.id, {"skill_points": 10, "level": 40},
        )
        return character

    def test_the_second_click_is_refused_and_costs_nothing(self):
        character = self._character_at_forty()
        first = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.store, character.id, 2950,
        )
        self.assertTrue(first.learned)
        after_first = self.store.get_skill_points(character.id)

        second = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.store, character.id, 2950,
        )
        self.assertEqual(
            skill_learn_roundtrip.OUTCOME_REFUSED, second.outcome,
        )
        self.assertEqual(
            skill_learn_roundtrip.REFUSE_ALREADY_HOLDS_SKILL, second.reason,
        )
        self.assertIsNone(second.pc)
        self.assertEqual(after_first, self.store.get_skill_points(character.id))

    def test_three_clicks_cost_exactly_one_point(self):
        """The measurement that named the defect, turned into a pin."""
        character = self._character_at_forty()
        before = self.store.get_skill_points(character.id)
        for _ in range(3):
            skill_learn_roundtrip.learn_skill_round_trip(
                self.legacy, self.store, character.id, 2950,
            )
        self.assertEqual(before - 1, self.store.get_skill_points(character.id))
        # No starting kit was granted in this fixture, so the one learned
        # row is the only row -- three clicks, one row, one point.
        self.assertEqual(
            1, len(self.store.list_character_skills(character.id)),
        )

    def test_a_grant_that_writes_nothing_is_never_reported_as_learned(self):
        """The belt behind the preflight.

        A store that cannot list skills makes the preflight undecidable, so
        the duplicate reaches the grant; the size of the returned set is
        what catches it there.  This is the branch that survives when the
        preflight cannot answer.
        """
        real = self.store

        class _BlindLister:
            """Lists nothing, and grants without ever growing the set."""

            def get_skill_points(self, cid):
                return real.get_skill_points(cid)

            def spend_skill_points(self, cid, cost):
                return real.spend_skill_points(cid, cost)

            def read_character_vitals_or_none(self, cid):
                return real.read_character_vitals_or_none(cid)

            def list_character_skills(self, cid):
                return real.list_character_skills(cid)

            def grant_learned_skill(self, cid, skill_id):
                # INSERT OR IGNORE against a row that already exists.
                return real.list_character_skills(cid)

        character = self._character_at_forty()
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, _BlindLister(), character.id, 2950,
        )
        self.assertEqual(
            skill_learn_roundtrip.OUTCOME_SPENT_ON_NOTHING, result.outcome,
        )
        self.assertIsNone(result.pc)
        self.assertIn(
            "RESULT=NOT_TOLD",
            skill_learn_roundtrip.headless_token(result),
        )


#: The lane may not reach these at module import time, nor from any
#: function but `main` -- the console entry point that has to open a real
#: database.  One set, shared by both checks below on purpose: pf-adversary
#: round `mfgv4m`'s D5 finding, re-checked by its own pf-adversary review,
#: found the two checks had drifted to different forbidden sets (the
#: per-function `ImportFrom` branch never had `gm`/`lifecycle` at all) --
#: sharing the tuple is what stops that happening silently again.
_FORBIDDEN_IMPORT_COMPONENTS = ("store", "runtime", "app", "gm", "lifecycle")


def _import_bound_components(node: "ast.AST") -> "set[str]":
    """Every dotted-path component one `Import`/`ImportFrom` node binds a
    name THROUGH, not merely the exact string(s) written on the line.

    Three shapes had to agree here, and across two separate pf-adversary
    findings on this same file they never all did at once:
      * `from . import store as _db` -- module is `None` (or an absolute
        prefix for a non-relative `from`); the bound name lives ONLY in
        `alias.name`.  A check that reads `node.module` and never
        `alias.name` (this file's OLD per-function `ImportFrom` branch)
        cannot see this shape at all, relative or not.
      * `import pirateforce_foundation.store as _db` -- the single
        `alias.name` is the whole dotted string; comparing it UNSPLIT
        (this file's OLD module-level check, pf-adversary round `mfgv4m`
        D5) misses it because `"store" != "pirateforce_foundation.store"`.
      * `import store` inside a function, checked against only the FIRST
        split component (this file's OLD per-function `Import` branch) --
        correct for this shape alone, but the two branches beside it were
        not, so "the per-function walk already does this" (the claim this
        module's D5 fix made, and pf-adversary's own review of that fix
        disproved) was false for one of its own two branches.
    Splitting every dotted path -- the module part AND every alias name --
    and unioning the parts answers all three the same way, which is why
    every forbidden-import check in this file now goes through here.
    """
    components: "set[str]" = set()
    if isinstance(node, ast.ImportFrom):
        for part in (node.module or "").split("."):
            if part:
                components.add(part)
        for alias in node.names:
            for part in alias.name.split("."):
                components.add(part)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            for part in alias.name.split("."):
                components.add(part)
    return components


def _top_level_import_components(source: str) -> "set[str]":
    """Every component a MODULE-LEVEL import statement in `source` binds a
    dotted path through -- see `_import_bound_components` for the shapes
    this has to agree on."""
    tree = ast.parse(source)
    components: "set[str]" = set()
    for node in tree.body:
        components |= _import_bound_components(node)
    return components


def _functions_that_locally_import(
    source: str, forbidden: "tuple[str, ...]",
) -> "set[str]":
    """The name of every function whose body imports something whose
    dotted path carries one of `forbidden`'s components -- the
    per-function counterpart of `_top_level_import_components`, built on
    the SAME node-level helper so the two cannot drift the way
    pf-adversary round `mfgv4m` found them already had (see
    `_import_bound_components`'s docstring)."""
    tree = ast.parse(source)
    forbidden_set = set(forbidden)
    importers: "set[str]" = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, (ast.Import, ast.ImportFrom)):
                if _import_bound_components(inner) & forbidden_set:
                    importers.add(node.name)
    return importers


class ThisLaneStaysInsideItsOwnZoneTests(unittest.TestCase):
    def test_no_module_outside_this_lane_is_imported_at_import_time(self):
        """The question is not which characters appear in the file -- it is
        which modules this one pulls in, and where.  The AST answers that:
        at module level the lane may import only its own siblings, and the
        database layer may be reached only from the console entry point,
        the same posture the login lane's own AST pin takes.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "skill_learn_roundtrip.py").read_text(encoding="utf-8")
        top_level = _top_level_import_components(source)
        for forbidden in _FORBIDDEN_IMPORT_COMPONENTS:
            self.assertNotIn(forbidden, top_level)

        # And inside functions, the same names may be reached from `main`
        # only -- the console entry point that has to open a real database.
        importers = _functions_that_locally_import(
            source, _FORBIDDEN_IMPORT_COMPONENTS,
        )
        self.assertEqual({"main"}, importers)

    def test_the_absolute_dotted_form_of_a_forbidden_import_is_also_caught(self):
        """pf-adversary round `mfgv4m`, D5, reproduced directly: before this
        round's fix, the module-level check (then written inline without
        the split) returned `{"pirateforce_foundation.store"}` for this
        source, and `"store" in top_level` was `False` -- the exact shape
        of the bypass, proven here against a literal source string rather
        than against the module file (which does not itself carry the
        forbidden import, so a passing pin there cannot show the check
        would have caught one that did).
        """
        bypassing_source = (
            "import pirateforce_foundation.store as _db\n"
            "from . import skill_grant_wiring\n"
        )
        components = _top_level_import_components(bypassing_source)
        self.assertIn("store", components)
        self.assertIn("pirateforce_foundation", components)

    def test_a_relative_from_import_inside_a_non_main_helper_is_also_caught(self):
        """pf-adversary's OWN review of the D5 fix above found the fix's
        docstring overclaimed: it said the per-function walk already split
        dotted names the same way, but that walk's `ImportFrom` branch
        read only `inner.module` (empty for `from . import store as _db`,
        whose bound name lives in the alias) and its forbidden set there
        never had `gm`/`lifecycle` at all.  `[measured by pf-adversary]`:
        adding a non-`main` helper doing exactly this import to the real
        module passed the OLD check unchanged.  Reproduced here directly
        against `_functions_that_locally_import` so a future edit that
        reintroduces either gap (reading `alias.name`, or the shared
        forbidden set) turns this red.
        """
        source = (
            "def main():\n"
            "    from . import store as _db\n"
            "    return _db\n"
            "\n"
            "def _sneaky_helper_not_main():\n"
            "    from . import store as _db\n"
            "    return _db\n"
            "\n"
            "def _another_sneaky_helper():\n"
            "    from . import lifecycle\n"
            "    return lifecycle\n"
        )
        importers = _functions_that_locally_import(
            source, _FORBIDDEN_IMPORT_COMPONENTS,
        )
        self.assertIn("_sneaky_helper_not_main", importers)
        self.assertIn("_another_sneaky_helper", importers)

    def test_the_console_entry_point_exists_and_is_reachable(self):
        """The reason it exists: an attended ticket whose pass criterion is
        a console line nothing in the tree can print burns a slot on the
        owner's machine and comes back FAIL blaming the server."""
        self.assertTrue(callable(skill_learn_roundtrip.main))
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "skill_learn_roundtrip.py").read_text(encoding="utf-8")
        self.assertIn('if __name__ == "__main__":', source)
        self.assertIn("LEARN_SKILL_ROUND_TRIP", source)


class TheConsoleEntryPointIsActuallyCalledTests(unittest.TestCase):
    """pf-adversary round `mfgv4m`, D1: stubbing `main`'s whole body with
    `return 0` still left `tests/test_skill_learn_roundtrip.py` at
    22 passed -- the ticket this file exists for (a console line an
    attended boot reads) had no test that ever RAN `main`, only one that
    checked it was `callable`.  These tests call it, for real, against a
    real file on disk, and read back what it printed and returned -- a
    mutant that guts the body fails both.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "cli_state.sqlite3"

    def _make_character_on_disk(self):
        """Populate the exact file `main` will later open by its `--db`
        path, through the same `SQLiteStore` it uses internally -- setup
        only, never imported by the module under test itself (see
        `ThisLaneStaysInsideItsOwnZoneTests` above: `store` is reachable
        from `main` only, and this class does not touch `main`'s AST)."""
        store = SQLiteStore(self.db_path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("cliacct01")
        store.open_session(account_id)
        character = store.create_character(
            account_id, "CliOne", "clione", "fp-cliacct01",
            _build_wire, _HOME,
        )
        store.write_typed_attributes(
            character.id, {"skill_points": 5, "level": 40},
        )
        return character.id

    def test_a_real_run_prints_told_and_exits_zero(self):
        character_id = self._make_character_on_disk()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = skill_learn_roundtrip.main([
                "--character", str(character_id),
                "--skill", str(_WHOLE_COST_SKILL_ID),
                "--db", str(self.db_path),
            ])
        self.assertEqual(0, exit_code)
        printed = buffer.getvalue().strip()
        self.assertIn("LEARN_SKILL_ROUND_TRIP", printed)
        self.assertIn("outcome=%s" % skill_learn_roundtrip.OUTCOME_LEARNED,
                      printed)
        self.assertIn("RESULT=TOLD", printed)
        self.assertIn("records=1", printed)

        # And the write really landed on the file `--db` named, not on some
        # other database `main` fell back to.
        store = SQLiteStore(self.db_path, MIGRATIONS)
        self.assertIn(
            _WHOLE_COST_SKILL_ID,
            store.list_character_skills(character_id),
        )

    def test_a_real_run_that_cannot_afford_it_prints_not_told_and_exits_one(self):
        character_id = self._make_character_on_disk()
        store = SQLiteStore(self.db_path, MIGRATIONS)
        store.write_typed_attributes(character_id, {"skill_points": 0})
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = skill_learn_roundtrip.main([
                "--character", str(character_id),
                "--skill", str(_WHOLE_COST_SKILL_ID),
                "--db", str(self.db_path),
            ])
        self.assertEqual(1, exit_code)
        printed = buffer.getvalue().strip()
        self.assertIn("RESULT=NOT_TOLD", printed)

    def test_a_db_path_that_does_not_exist_yet_is_migrated_not_lied_about(self):
        """The exact shape pf-adversary measured: `--db` naming a path with
        nothing at it.  Before the D1 fix this printed the specific-
        sounding `reason=skill_point_balance_has_never_been_written` for a
        database that had no `characters` table at all, and left a bare
        4096-byte file behind.  After it, the same run still refuses (there
        is no such character), but through a database that was actually
        migrated -- proven here by connecting to the path `main` was given
        and finding the real schema, not just an empty file."""
        fresh_path = Path(self.tmp.name) / "never_touched.sqlite3"
        self.assertFalse(fresh_path.exists())
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = skill_learn_roundtrip.main([
                "--character", "1",
                "--skill", str(_WHOLE_COST_SKILL_ID),
                "--db", str(fresh_path),
            ])
        self.assertEqual(1, exit_code)
        self.assertIn("RESULT=NOT_TOLD", buffer.getvalue())
        self.assertTrue(fresh_path.exists())
        # Migrated, not merely created: a store opened read-only against
        # this exact path can list characters (the table exists) and finds
        # none, rather than raising "no such table".
        store = SQLiteStore(fresh_path, MIGRATIONS)
        with store.connect() as db:
            names = {
                str(row[0]) for row in
                db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        self.assertIn("characters", names)
        self.assertIn("schema_migrations", names)

    def test_it_carries_no_scenario_flag_a_boot_could_switch_off(self):
        self.assertIs(True, skill_learn_roundtrip.production_allowed)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
