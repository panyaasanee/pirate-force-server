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

from pirateforce_foundation import skill_learn_roundtrip  # noqa: E402
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
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
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
        self.store.write_typed_attributes(character.id, {"skill_points": 3})
        skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, _WHOLE_COST_SKILL_ID,
        )
        self.assertEqual(2, self.store.get_skill_points(character.id))
        self.assertEqual(
            [(character.id, _WHOLE_COST_SKILL_ID)], self.fake.grant_calls,
        )

    def test_no_frame_travels_with_a_refusal(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
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
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
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
        self.store.write_typed_attributes(character.id, {"skill_points": 1})
        result = skill_learn_roundtrip.learn_skill_round_trip(
            self.legacy, self.fake, character.id, 2950,
        )
        self.assertEqual(skill_learn_roundtrip.OUTCOME_REFUSED, result.outcome)
        self.assertEqual(1, self.store.get_skill_points(character.id))
        self.assertEqual([], self.fake.grant_calls)


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
        self.store.write_typed_attributes(character.id, {"skill_points": 5})

        class _SpendOnlyStore:
            def __init__(self, store):
                self._store = store

            def get_skill_points(self, character_id):
                return self._store.get_skill_points(character_id)

            def spend_skill_points(self, character_id, cost):
                return self._store.spend_skill_points(character_id, cost)

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
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
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
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
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
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
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
