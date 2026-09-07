"""SKILL-LIST-AT-LOGIN-001 -- the character's persisted skill rows on the wire.

Pure offline pytest: a throwaway temp database with the real migrations, the
real ``SQLiteStore``, and the frozen v141 module for the envelope.  No network, no game
client, no UI.  (The client class name is deliberately not spelled here: the
Windows gate excludes any test module that contains it, which would hide this
file from the gate entirely.)

What these tests prove
----------------------
  * the ids come from ``character_skills`` and from nowhere else -- proved by
    changing the ROWS and watching the frame change, and by deleting a row and
    watching the frame shrink, neither of which the class table could do;
  * every refusal is a NAMED refusal of this module's own exception class, so
    a login-path caller has one ``except`` and never a bare ``KeyError``;
  * a character with no rows gets a refusal, never a count-0 frame;
  * the composed bytes are the GT-050-proven body and the frozen envelope,
    asserted by decoding them back with the owning module's own decoder;
  * the module is not wired: ``callers_in_src=0`` is MEASURED here by grepping
    every sibling module, so the token cannot go on saying it once it is false.

NOT tested here, because it is not claimed: that any client renders any of
this (GT-249 says 3 of 4 ids rendered from a TRIGGER, never from a login);
that a login is the right moment to send it; or that the movement regression
GT-249 recorded is absent -- the attended ticket filed with this round asks
exactly that, and ``production_allowed`` stays ``False`` until it answers.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import skill_list_at_login  # noqa: E402
from pirateforce_foundation.class_catalog import (  # noqa: E402
    starting_skill_ids,
)
from pirateforce_foundation.learn_skill_result_hypothesis import (  # noqa: E402
    LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
    LEARN_SKILL_RESULT_PROBE_FRAME_SHA256,
    LEARN_SKILL_RESULT_PROBE_PC_SHA256,
    LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
    LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
    LEARN_SKILL_RESULT_VITAL_ID,
    LearnSkillResultRecord,
    decode_learn_skill_result_payload,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.skill_list_at_login import (  # noqa: E402
    SkillListAtLoginError,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SRC = ROOT / "src" / "pirateforce_foundation"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x30000001, 0x30001000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )

    def _with_skills(self, skill_ids, login="acct01", name="Test01"):
        character = self._character(login=login, name=name)
        self.store.grant_starting_skills(character.id, tuple(skill_ids))
        return character


class TheIdsComeFromTheRowsNotFromTheClassTableTests(_Fixture):
    """The whole point of the order, proved by moving the rows."""

    def test_the_frame_carries_exactly_the_rows_that_are_in_the_table(self):
        wanted = (111, 40000, 99, 110)
        character = self._with_skills(wanted)
        self.assertEqual(
            wanted,
            skill_list_at_login.read_character_skill_ids(
                self.store, character.id
            ),
        )

    def test_ids_that_no_class_starts_with_still_reach_the_wire(self):
        # A class table could never answer this: 7/8/9 are not any class's
        # starting kit.  If this module were secretly resolving the class, the
        # frame would come back with the kit instead of these three.
        invented = (7, 8, 9)
        for class_id in (1, 2, 4, 16, 32):
            self.assertNotEqual(invented, starting_skill_ids(class_id)[:3])
        character = self._with_skills(invented)
        pc, _frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        records, trailing = self._decode(pc, 3)
        self.assertEqual(
            [7, 8, 9], [record.record_u32_0 for record in records]
        )
        self.assertEqual(skill_list_at_login.SKILL_LIST_TRAILING_BYTE, trailing)

    def test_a_second_grant_makes_the_frame_grow(self):
        character = self._with_skills((99,))
        before, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.store.grant_starting_skills(character.id, (110,))
        after, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.assertEqual(
            len(before) + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE, len(after)
        )
        records, _ = self._decode(after, 2)
        self.assertEqual([99, 110], [r.record_u32_0 for r in records])

    def test_two_characters_get_two_different_frames(self):
        one = self._with_skills((99,), login="acct01", name="Test01")
        two = self._with_skills((110, 111), login="acct02", name="Test02")
        pc_one, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, one.id
        )
        pc_two, _ = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, two.id
        )
        self.assertNotEqual(pc_one, pc_two)
        self.assertEqual(
            [99], [r.record_u32_0 for r in self._decode(pc_one, 1)[0]]
        )
        self.assertEqual(
            [110, 111], [r.record_u32_0 for r in self._decode(pc_two, 2)[0]]
        )

    def _decode(self, pc, count):
        size = (
            LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE
            + LEARN_SKILL_RESULT_RECORD_WIRE_SIZE * count
        )
        offset = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        return decode_learn_skill_result_payload(pc[offset:offset + size])


class RowsThatCannotAnswerAreRefusedByNameTests(_Fixture):

    def test_a_character_with_no_skill_rows_is_refused_not_sent_count_zero(self):
        character = self._character()
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.login_skill_list_response(
                self.legacy, self.store, character.id
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_NO_SKILL_ROWS, caught.exception.reason
        )

    def test_a_missing_character_is_a_named_refusal_not_a_key_error(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.read_character_skill_ids(self.store, 999999)
        self.assertEqual(
            skill_list_at_login.REFUSE_CHARACTER_ROW_MISSING,
            caught.exception.reason,
        )

    def test_a_bool_character_id_is_refused_before_the_store_sees_it(self):
        # `True == 1` and character 1 is a real row in a fresh database, so a
        # coercing check would read someone else's skills.
        self._with_skills((99,))
        for bad in (True, False):
            with self.subTest(character_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.read_character_skill_ids(
                        self.store, bad
                    )
                self.assertEqual(
                    skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
                    caught.exception.reason,
                )

    def test_a_bool_never_reaches_the_store_at_all(self):
        """The bool guard is a branch nobody walks unless a test walks it.

        Round `b2cnxe` mutant M3 (delete the `isinstance(..., bool)` half)
        stayed GREEN against the first version of this file: `True` is an
        `int` in python, so it sailed past the type check, and
        `list_character_skills` then raised its OWN `TypeError`, which
        `read_character_skill_ids` translates into the SAME reason string.
        Every assertion still passed while the guard was gone -- the exact
        defect class round `hhmvit` was caught by (its M4/M6).  So this test
        checks the thing the reason string cannot: that the store is never
        asked.  It matters beyond tidiness -- `sqlite3` binds `True` as `1`,
        so a store that is reached would answer with CHARACTER 1's skills.
        """
        class _StoreThatMustNotBeAsked:
            def list_character_skills(self, character_id):
                raise AssertionError(
                    "the store was consulted for %r" % (character_id,)
                )

        for bad in (True, False):
            with self.subTest(character_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.read_character_skill_ids(
                        _StoreThatMustNotBeAsked(), bad
                    )
                self.assertEqual(
                    skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
                    caught.exception.reason,
                )

    def test_a_string_character_id_is_refused_by_name(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.read_character_skill_ids(self.store, "1")
        self.assertEqual(
            skill_list_at_login.REFUSE_CHARACTER_ID_NOT_AN_INT,
            caught.exception.reason,
        )


class TheRecordListRefusesByNameTests(unittest.TestCase):

    def test_a_bool_skill_id_is_not_a_skill_id(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records((True,))
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_an_id_outside_u32_is_refused(self):
        for bad in (-1, 0x100000000):
            with self.subTest(skill_id=bad):
                with self.assertRaises(SkillListAtLoginError) as caught:
                    skill_list_at_login.skill_list_records((bad,))
                self.assertEqual(
                    skill_list_at_login.REFUSE_SKILL_ID_OUTSIDE_U32,
                    caught.exception.reason,
                )

    def test_a_duplicate_id_is_refused(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records((99, 99))
        self.assertEqual(
            skill_list_at_login.REFUSE_DUPLICATE_SKILL_ID,
            caught.exception.reason,
        )

    def test_a_string_is_not_a_list_of_ids(self):
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records("99")
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_NOT_AN_INT,
            caught.exception.reason,
        )

    def test_more_records_than_anyone_has_measured_is_refused_by_name(self):
        cap = skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT
        self.assertEqual(cap, len(skill_list_at_login.skill_list_records(
            tuple(range(1, cap + 1))
        )))
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.skill_list_records(tuple(range(1, cap + 2)))
        self.assertEqual(
            skill_list_at_login.REFUSE_TOO_MANY_UNMEASURED,
            caught.exception.reason,
        )

    def test_the_unmeasured_cap_is_below_the_wire_cap(self):
        # The two constants say different things: one is the u16 field width
        # (a fact about the serializer), the other is the largest count a
        # client was watched accepting (a fact about GT-249).  If they ever
        # collapse into one number this test says so.
        self.assertLess(
            skill_list_at_login.OBSERVED_ACCEPTED_RECORD_COUNT,
            skill_list_at_login.WIRE_MAX_RECORDS,
        )

    def test_the_id_lands_in_all_three_wire_positions(self):
        records = skill_list_at_login.skill_list_records((111, 99))
        self.assertEqual(
            (
                LearnSkillResultRecord(111, 111, 111),
                LearnSkillResultRecord(99, 99, 99),
            ),
            records,
        )


class TheComposedBytesAreTheProvenShapeTests(_Fixture):

    def test_the_vital_id_is_the_one_gt050_proved(self):
        character = self._with_skills((99, 110))
        pc, frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        self.assertIn(
            LEARN_SKILL_RESULT_VITAL_ID.to_bytes(2, "little"), pc
        )
        self.assertTrue(frame)

    def test_the_frame_is_byte_identical_to_the_one_gt249_already_rendered(
        self,
    ):
        """The strongest thing this module can honestly claim today.

        GT-249 (2026-09-05, real client, owner watching) sent step 6 of the
        pinned sweep -- class 1's four starting ids, trailing 0 -- and three
        of the four appeared in the skill window with correct name and icon.
        This module reaches the SAME 79-byte PC and 90-byte frame from a
        different direction entirely: four rows read out of
        `character_skills`, no scenario file, no flag, no pinned step index.

        That equality is the ticket's whole argument and its whole honesty at
        once.  It means an attended run of this module is not asking a client
        to accept anything new -- these exact bytes were already accepted and
        rendered.  It ALSO means the "from the database, not from a fixed
        table" difference is not visible in the bytes for any character alive
        today, because `lifecycle.py` wrote those rows from the same class
        table.  Both halves are true and this test pins both.
        """
        character = self._with_skills(starting_skill_ids(1))
        pc, frame = skill_list_at_login.login_skill_list_response(
            self.legacy, self.store, character.id
        )
        step = "COUNT4_REAL_SKILL_IDS_CLASS1_TRAIL0"
        self.assertEqual(
            LEARN_SKILL_RESULT_PROBE_PC_SHA256[step].lower(),
            hashlib.sha256(pc).hexdigest(),
        )
        self.assertEqual(
            LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[step].lower(),
            hashlib.sha256(frame).hexdigest(),
        )

    def test_an_id_above_u16_is_refused_by_this_module_not_by_a_value_error(
        self,
    ):
        # `record_u16_4` is the narrow position: 70000 fits both u32 slots and
        # not the middle one, so the encoder refuses with `ValueError` and the
        # login path would see an exception class it does not catch.
        with self.assertRaises(SkillListAtLoginError) as caught:
            skill_list_at_login.make_skill_list_response(
                self.legacy, (70000,)
            )
        self.assertEqual(
            skill_list_at_login.REFUSE_SKILL_ID_OUTSIDE_U32,
            caught.exception.reason,
        )


class TheLaneIsNotWiredAndSaysSoTests(unittest.TestCase):

    def test_production_allowed_is_false_while_the_regression_is_unisolated(
        self,
    ):
        # GT-249 recorded a client that stopped emitting movement frames after
        # this vital's sweep, cause never isolated.  Flipping this flag before
        # an attended run says movement survives is the failure mode this
        # test exists to make loud.
        self.assertFalse(skill_list_at_login.production_allowed)

    def test_the_callers_in_src_token_matches_the_tree(self):
        summary = [
            line for line in
            skill_list_at_login.describe_skill_list((99, 110))
            if line.startswith("SKILL_LIST_AT_LOGIN_SUMMARY")
        ]
        self.assertEqual(1, len(summary))
        here = Path(skill_list_at_login.__file__).resolve()
        callers = sorted(
            path.name
            for path in SRC.rglob("*.py")
            if path.resolve() != here
            and "skill_list_at_login" in path.read_text(encoding="utf-8")
        )
        # Whole token, not a substring: pf-adversary showed on the sibling
        # module (round `hhmvit` D2) that `assertIn("callers_in_src=1", ...)`
        # passes against `callers_in_src=12`.
        self.assertIn(
            "callers_in_src=%d" % len(callers), summary[0].split(),
        )
        self.assertEqual([], callers, "callers appeared: %r" % (callers,))

    def test_every_console_line_survives_the_bridge_console(self):
        for line in skill_list_at_login.describe_skill_list((111, 40000)):
            with self.subTest(line=line):
                line.encode("ascii")
                line.encode("cp874")


class TheHeadlessTokenIsMeasuredNotSpelledTests(_Fixture):
    """GT-307's ``HEADLESS_PROOF:`` command, pinned against its own database.

    The ticket names one line and says in as many words that it "must read
    from the real database, not from the class table".  Every test here
    grants ids that no class in ``CHARCREATE_CLASS`` starts with, so a
    version of this command that quietly fell back on the class table would
    print different ids and go red rather than look right.
    """

    def _run(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = skill_list_at_login.main(argv)
        return code, buffer.getvalue().strip()

    def test_the_token_carries_the_rows_that_are_in_the_database(self):
        character = self._with_skills((7, 8, 9))
        code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertEqual(0, code)
        fields = dict(
            token.split("=", 1) for token in line.split() if "=" in token
        )
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN "))
        self.assertEqual(str(character.id), fields["cid"])
        self.assertEqual("3", fields["rows"])
        self.assertEqual("(7,8,9)", fields["ids"])
        self.assertEqual("0", fields["trailing_u8"])
        self.assertEqual(
            str(skill_list_at_login.SKILL_LIST_TRAILING_BYTE),
            fields["trailing_u8"],
        )

    def test_the_byte_count_is_the_frame_the_proven_encoder_composed(self):
        character = self._with_skills((7, 8, 9))
        _pc, frame = skill_list_at_login.make_skill_list_response(
            self.legacy, (7, 8, 9)
        )
        _code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertIn("frame_bytes=%d" % len(frame), line.split())

    def test_deleting_one_row_shortens_the_token_and_the_frame(self):
        """GT-307 step (c), measured here so the attended run is a re-check.

        This is the one step that tells "read the rows" apart from "read the
        class table": the ids stay legal either way, only the count moves.
        """
        character = self._with_skills((7, 8, 9))
        _code, before = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "DELETE FROM character_skills WHERE character_id=? "
                "AND skill_id=?",
                (character.id, 9),
            )
        _code, after = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertIn("rows=3", before.split())
        self.assertIn("rows=2", after.split())
        self.assertIn("ids=(7,8)", after.split())
        self.assertLess(
            int(dict(t.split("=", 1) for t in after.split() if "=" in t)
                ["frame_bytes"]),
            int(dict(t.split("=", 1) for t in before.split() if "=" in t)
                ["frame_bytes"]),
        )

    def test_a_character_with_no_rows_prints_one_refusal_line_and_exits_1(self):
        character = self._character()
        code, line = self._run(
            ["--character", str(character.id), "--db", str(self.path)]
        )
        self.assertEqual(1, code)
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))
        self.assertIn(
            "reason=%s" % skill_list_at_login.REFUSE_NO_SKILL_ROWS,
            line.split(),
        )
        self.assertEqual(1, len(line.splitlines()))

    def test_a_missing_database_is_refused_and_never_created(self):
        """A proof command that can write to the canonical database is not one.

        ``SQLiteStore`` would happily create the file, and an attended run
        that mistypes the path would then get a green-looking empty database
        instead of a refusal.
        """
        missing = Path(self.tmp.name) / "not_here.sqlite3"
        code, line = self._run(["--character", "1", "--db", str(missing)])
        self.assertEqual(1, code)
        self.assertTrue(line.startswith("SKILL_LIST_AT_LOGIN_REFUSED "))
        self.assertFalse(missing.exists())

    def test_opening_a_delete_journal_database_flips_it_to_wal(self):
        """The one side effect, measured instead of denied.

        ``SQLiteStore.connect()`` runs ``PRAGMA journal_mode=WAL`` on every
        open, so this command is not read-only against a database that is
        not already in WAL.  Every canonical database is (the next test
        sha256s that case), but a claim that rots silently is worse than a
        side effect that is written down.
        """
        character = self._with_skills((7, 8, 9))
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(
                "delete",
                connection.execute("PRAGMA journal_mode").fetchone()[0],
            )
        self._run(["--character", str(character.id), "--db", str(self.path)])
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(
                "wal",
                connection.execute("PRAGMA journal_mode").fetchone()[0],
            )

    def test_the_command_does_not_write_to_the_database_it_reads(self):
        """Against a database already in WAL -- i.e. every canonical one."""
        character = self._with_skills((7, 8, 9))
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self._run(["--character", str(character.id), "--db", str(self.path)])
        self.assertEqual(
            before, hashlib.sha256(self.path.read_bytes()).hexdigest()
        )


class SentByIsReadOffTheTreeTests(unittest.TestCase):
    """``sent_by=`` is a measurement of ``runtime.py``, not a spelling.

    pf-adversary killed the sibling module's ``callers_in_src=0`` for being a
    zero inside a format string.  The same trap is one word away here: GT-307
    asks for a line ending ``sent_by=runtime``, and printing that word
    unconditionally would make the ticket's own proof unfalsifiable.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_runtime_that_names_the_entry_point_reads_as_runtime(self):
        path = self.dir / "runtime.py"
        path.write_text(
            "frame = %s(legacy, store, cid)\n"
            % skill_list_at_login.LOGIN_SEAM_SYMBOL,
            encoding="utf-8",
        )
        self.assertEqual("runtime", skill_list_at_login.seam_carrier(path))

    def test_a_runtime_without_the_entry_point_reads_as_module_only(self):
        path = self.dir / "runtime.py"
        path.write_text("class GameState:\n    pass\n", encoding="utf-8")
        self.assertEqual("module_only", skill_list_at_login.seam_carrier(path))

    def test_no_runtime_at_all_reads_as_unknown_not_as_runtime(self):
        self.assertEqual(
            "unknown", skill_list_at_login.seam_carrier(self.dir / "gone.py")
        )

    def test_the_shipped_tree_is_reported_truthfully_today(self):
        runtime = SRC / "runtime.py"
        expected = (
            "runtime"
            if skill_list_at_login.LOGIN_SEAM_SYMBOL
            in runtime.read_text(encoding="utf-8")
            else "module_only"
        )
        self.assertEqual(expected, skill_list_at_login.seam_carrier())

    def test_the_token_line_survives_the_bridge_console(self):
        line = skill_list_at_login.headless_token(1, (111, 40000), b"x" * 50,
                                                  "module_only")
        line.encode("ascii")
        line.encode("cp874")


class TheDatabaseLayerIsReachedOnlyByTheTwoFunctionsThatNeedItTests(
    unittest.TestCase
):
    """``store`` and ``legacy_bridge`` are imported inside the functions.

    WHY THIS IS AN AST PIN AND NOT A ``sys.modules`` PIN.  The obvious
    stronger test -- boot a clean interpreter, import this module, assert
    ``pirateforce_foundation.store`` is not in ``sys.modules`` -- CANNOT
    pass and would not mean what it says if it did: the package's own
    ``__init__.py`` imports ``SQLiteStore`` on line 3, so importing ANY
    module in this package imports the store before this module's first
    line runs.  Measured, not assumed: the assertion below re-reads that
    ``__init__`` and fails if it ever stops being true, at which point the
    ``sys.modules`` pin becomes the right one to write.

    What is left to measure is this module's own top-level import list, and
    it is worth measuring: the login seam imports this module to compose a
    frame, and the two database names belong to the two functions that read
    a database, not to everybody who wants bytes.
    """

    _DATABASE_NAMES = ("store", "legacy_bridge")

    def _module_level_imports(self):
        tree = ast.parse(
            Path(skill_list_at_login.__file__).read_text(encoding="utf-8")
        )
        names = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                names.extend(alias.name.split(".")[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append((node.module or "").split(".")[-1])
        return names

    def test_the_package_init_still_imports_the_store(self):
        text = (SRC / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("from .store import", text)

    def test_no_database_name_is_imported_at_module_level(self):
        names = self._module_level_imports()
        for forbidden in self._DATABASE_NAMES:
            with self.subTest(name=forbidden):
                self.assertNotIn(forbidden, names)

    def test_the_pin_can_see_a_module_level_import_when_there_is_one(self):
        """The mutant, run here rather than trusted.

        Without this, a rewrite that made ``_module_level_imports`` return
        ``[]`` would keep the test above green forever.
        """
        tree = ast.parse("from .store import SQLiteStore\n")
        node = tree.body[0]
        self.assertEqual("store", (node.module or "").split(".")[-1])
        self.assertIn(
            "learn_skill_result_frame", self._module_level_imports()
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
