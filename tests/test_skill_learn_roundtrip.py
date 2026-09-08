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


class LearningAFifthSkillCollidesWithTheLoginCapTests(_Fixture):
    """MEASURED THIS ROUND, and pinned so a player is not the first to find
    it.

    `skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT` is 4 -- the largest
    count a real client has ever been measured accepting (`GT-249`) -- and
    `COO-DECISION 20260908_1742` froze it there until an attended result
    moves it.  Every character alive today carries exactly the 4 starting
    kit rows, so nothing had ever produced a fifth.  This module produces
    one on the first successful learn, and the next login then composes NO
    SKILL FRAME AT ALL: a named refusal on the console, and an empty skill
    window on the screen.

    THE CAP IS NOT RAISED HERE and this test does not ask for it to be.  It
    pins the collision so that the day the cap moves, the test that moves it
    has to come here and say so -- and so that the ">4 rows" step this lane
    asked `GT-307` for has a reproducible way to reach it that needs no GM
    command at all.
    """

    def test_the_fifth_row_makes_the_login_frame_refuse_by_name(self):
        character = self._make_character()
        self.store.write_typed_attributes(
            character.id, {"skill_points": 99, "level": 40},
        )
        lifecycle.grant_starting_skills_for_class(self.store, character, 1)
        before = skill_list_at_login.read_character_skill_ids(
            self.store, character.id,
        )
        self.assertEqual(
            skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT, len(before),
        )
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
        with self.assertRaises(
            skill_list_at_login.SkillListAtLoginError
        ) as caught:
            skill_list_at_login.make_skill_list_response(self.legacy, after)
        self.assertEqual(
            skill_list_at_login.REFUSE_TOO_MANY_UNMEASURED,
            caught.exception.reason,
        )


class ThisLaneStaysInsideItsOwnZoneTests(unittest.TestCase):
    def test_the_module_names_no_write_zone_that_is_not_its_own(self):
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "skill_learn_roundtrip.py").read_text(encoding="utf-8")
        for forbidden in ("import runtime", "from .runtime",
                          "from .app", "from .store import"):
            self.assertNotIn(forbidden, source)

    def test_it_carries_no_scenario_flag_a_boot_could_switch_off(self):
        self.assertIs(True, skill_learn_roundtrip.production_allowed)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
