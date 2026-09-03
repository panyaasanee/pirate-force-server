"""The class she picked is stored at creation and sent at login.

`PANYA-DECISION 20260904_0328` piece 1 -- "the class she chose must not be
dropped" -- reached this lane as the CORE-REQUEST in `pf_bridge/
notes_to_chief/20260904_0423_LANE-DB-CORE-REQUEST-class-id-resolver-built-
needs-two-hookups.md`, granted by `COO-DECISION 20260904_0446`.  LANE-DB
built the matcher (`persistence_class_id.resolve_class_id`, five committed
`CHARCREATE_CLASS` presets, exact match or `None`); the two hookups it could
not reach from its own write area are what this file measures:

  1. CREATE -- `lifecycle.persist_class_id_from_starting_gear` decodes the
     AvatarAttr body the store just stored, resolves the three starting-gear
     slots, and writes `characters.class_id` when and only when the answer is
     unambiguous.
  2. LOGIN -- `session.select_and_start` reads that column onto the character
     and `legacy_bridge.start_game` puts it on the wire, with the composer's
     `PLAYER_LOGIN_CLASS_ID` still standing for a row that has no class.

THE FIXTURE IS A SNIPER, AND THAT IS THE WHOLE DESIGN OF THIS FILE.  The
client's own preset actor wire -- `test01`, the only real character-creation
capture this project has -- is a GLADIATOR, and `player_wire.
PLAYER_LOGIN_CLASS_ID` is `1`, the Gladiator.  An end-to-end test built on
that preset alone cannot tell "the login read the row" from "the login sent
its own literal": both frames are byte-identical.  That is exactly the trap
`COO-DECISION 20260903_0054` caught the walk-speed seam in (a migration
default equal to the composer's constant made the seam unfalsifiable), and
the vitals seam next door answers it with a fixture no constant produces.
So every end-to-end assertion here runs on a body whose three gear slots have
been rewritten to the SNIPER row of the same sourced table -- class `4`, a
number no constant, default or migration in this repository holds.

WHAT THIS FILE DOES NOT PROVE (`G5`).  Nothing here is client-observable.
This is the wire/DB layer: a column holds the class, and the login frame
carries it.  Whether the client then draws her as a Sniper -- HUD, skill
window, model -- is an attended ticket and this file makes no claim about it.
It also proves nothing about characters born before this seam existed: their
column stays NULL until LANE-DB's backfill (`COO-DECISION 20260904_0445`)
runs, and a NULL row logging in on the constant is asserted here as the
correct, unchanged behaviour rather than a gap.
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lifecycle as lifecycle_module
from pirateforce_foundation import player_wire
from pirateforce_foundation import session as session_module
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Character, Position
from pirateforce_foundation.persistence_class_id import CLASS_PRESETS
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.world_avatar_attr import (
    decode_avatar_attr,
    with_named_fields,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

SCENE_ID = 1
SCENE_SEQ = 0
IDENTITY_LO = 0x10010001
IDENTITY_HI = 0

#: The Sniper row of `CONSTDATA_TH__CHARCREATE_CLASS.tsv`, taken from the
#: module under test rather than typed again here, so a corrected table
#: cannot leave this file asserting a number the server no longer resolves.
SNIPER = next(row for row in CLASS_PRESETS if row[0] == 4)
SNIPER_CLASS_ID, SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND = SNIPER

#: A triple no row of that table holds, for the "unknown stays unknown" case.
NO_SUCH_GEAR = (9_999_001, 9_999_002, 9_999_003)


def _named_wire(legacy, name):
    """The client's own preset actor wire carrying `name`.

    Same idiom as `tests/test_login_vitals_seam.py` and
    `tests/test_login_speed.py`: the lifecycle validates the wire's
    identity/selector/name, so a hand-rolled blob is refused long before this
    file could measure anything with it.
    """
    preset = legacy.get_preset_actor_wire()
    old = legacy.wstr_tag("test01")
    new = legacy.wstr_tag(name)
    assert len(new) == len(old), "test names must be six chars"
    return preset.replace(old, new, 1)


def _wire_wearing(legacy, name, chest, leggings, rhand):
    """The preset wire, with its embedded AvatarAttr wearing another class.

    The three slots are u32 fields already present in the preset body, so the
    re-encoded body is the same LENGTH as the one it replaces -- asserted
    here rather than hoped for, because `bind_actor_and_avatar_identity`
    locates the embedded body by an exact, unique substring search and a
    shorter or longer body would either move the actor's other fields or make
    that search ambiguous.
    """
    wire = _named_wire(legacy, name)
    body = legacy.extract_avatar_attr_wire_from_actor(wire)
    worn = with_named_fields(
        body,
        n_DRESS_CHEST=chest,
        n_DRESS_LEGGINGS=leggings,
        n_SLOT_RHAND=rhand,
    )
    assert len(worn) == len(body), "gear rewrite must not move the body"
    assert wire.count(body) == 1, "the embedded body must be unique"
    return wire.replace(body, worn, 1)


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def _class_tag(self, class_id):
        return self.legacy.u32tag(0x19, class_id)


class TheFixtureIsNotTheConstantTests(_LegacyCase):
    """The premise every end-to-end group below rests on, asserted.

    If a future table edit makes the Sniper row's class id `1`, or makes the
    preset's own gear stop resolving to the Gladiator, the groups below would
    quietly start grading nothing.  This group goes red first instead.
    """

    def test_the_client_preset_is_the_gladiator_the_constant_already_sends(self):
        body = decode_avatar_attr(
            self.legacy.extract_avatar_attr_wire_from_actor(
                self.legacy.get_preset_actor_wire()
            )
        )
        gladiator = next(row for row in CLASS_PRESETS if row[0] == 1)
        self.assertEqual(
            (
                body.named("n_DRESS_CHEST"),
                body.named("n_DRESS_LEGGINGS"),
                body.named("n_SLOT_RHAND"),
            ),
            gladiator[1:],
        )
        self.assertEqual(player_wire.PLAYER_LOGIN_CLASS_ID, gladiator[0])

    def test_the_sniper_fixture_is_a_class_no_constant_produces(self):
        self.assertNotEqual(SNIPER_CLASS_ID, player_wire.PLAYER_LOGIN_CLASS_ID)

    def test_the_rewritten_body_really_wears_the_sniper_gear(self):
        wire = _wire_wearing(
            self.legacy, "snipe1", SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND,
        )
        body = decode_avatar_attr(
            self.legacy.extract_avatar_attr_wire_from_actor(wire)
        )
        self.assertEqual(
            (
                body.named("n_DRESS_CHEST"),
                body.named("n_DRESS_LEGGINGS"),
                body.named("n_SLOT_RHAND"),
            ),
            (SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND),
        )


class _StoreCase(_LegacyCase):
    """A real SQLite store, real migrations, a real lifecycle."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = SQLiteStore(
            str(Path(self._tmp.name) / "pf.sqlite3"), ROOT / "migrations",
        )
        self.store.migrate()
        self.lifecycle = CharacterLifecycle(
            self.store, Position(SCENE_ID, SCENE_SEQ, 1.0, 2.0, 3.0),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.projector = LegacyProjector(self.legacy)

    def _born(self, login, wire):
        account_id, _sid, _characters = self.lifecycle.login(login)
        return self.lifecycle.create(account_id, login, wire)

    def _born_sniper(self, login="snipe1"):
        return self._born(
            login,
            _wire_wearing(
                self.legacy, login, SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND,
            ),
        )

    def _born_classless(self, login="nogear"):
        return self._born(
            login, _wire_wearing(self.legacy, login, *NO_SUCH_GEAR),
        )

    def _stored_class_id(self, character_id):
        return self.store.read_typed_attributes(character_id).get("class_id")


class CreateHookupTests(_StoreCase):
    """Hookup 1: the row carries the class the moment the character exists."""

    def test_a_sniper_creation_writes_the_sniper_class_id(self):
        character = self._born_sniper()
        self.assertEqual(self._stored_class_id(character.id), SNIPER_CLASS_ID)

    def test_the_clients_own_preset_writes_the_gladiator(self):
        character = self._born("glad01", _named_wire(self.legacy, "glad01"))
        self.assertEqual(self._stored_class_id(character.id), 1)

    def test_gear_matching_no_preset_leaves_the_column_null(self):
        """`None` is not `0` and not a guess (`COO-DECISION 20260901_1059`).

        The character is still created -- an unresolvable class is a named
        gap on a real character, never a refused creation.
        """
        character = self._born_classless()
        self.assertIsNone(self._stored_class_id(character.id))
        self.assertEqual(
            [c.id for c in self.store.list_characters(character.account_id)],
            [character.id],
        )

    def test_the_create_fingerprint_retry_is_idempotent(self):
        """The same submitted wire twice is one character, one class id.

        `store.create_character` returns the existing row on a matching
        create fingerprint; the hookup runs on that path too and must resolve
        the same body to the same number rather than raise or write a second
        one.
        """
        wire = _wire_wearing(
            self.legacy, "snipe1", SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND,
        )
        account_id, _sid, _characters = self.lifecycle.login("snipe1")
        first = self.lifecycle.create(account_id, "snipe1", wire)
        second = self.lifecycle.create(account_id, "snipe1", wire)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self._stored_class_id(second.id), SNIPER_CLASS_ID)


class TheHookupNeverBreaksCreationTests(_LegacyCase):
    """The row is already committed when this runs, so it may not raise.

    Every failure below would, before this file existed, have reached a
    client as "character creation failed" for a character that exists -- the
    client would then be looking at a character list containing the character
    it was just told it could not have.
    """

    class _Recorder:
        def __init__(self, raises=None):
            self.writes = []
            self.raises = raises

        def write_typed_attributes(self, character_id, values):
            if self.raises is not None:
                raise self.raises
            self.writes.append((character_id, values))
            return dict(values)

    def _character(self, avatar_wire):
        return Character(
            id=7, account_id=1, selector=0, name="test01",
            actor_wire=b"", avatar_wire=avatar_wire,
            identity_lo=IDENTITY_LO, identity_hi=IDENTITY_HI,
            position=Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0),
        )

    def _run(self, store, character):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            written = lifecycle_module.persist_class_id_from_starting_gear(
                store, character,
            )
        return written, stderr.getvalue()

    def test_an_undecodable_body_writes_nothing_and_says_so(self):
        store = self._Recorder()
        written, console = self._run(store, self._character(b"\x99\x99\x99"))
        self.assertIsNone(written)
        self.assertEqual(store.writes, [])
        self.assertIn("avatar_body_unreadable", console)

    def test_a_missing_body_writes_nothing_and_says_so(self):
        store = self._Recorder()
        written, console = self._run(store, self._character(None))
        self.assertIsNone(written)
        self.assertEqual(store.writes, [])
        self.assertIn("not_written", console)

    def _sniper_body(self):
        return self.legacy.extract_avatar_attr_wire_from_actor(
            _wire_wearing(
                self.legacy, "snipe1",
                SNIPER_CHEST, SNIPER_LEGGINGS, SNIPER_RHAND,
            )
        )

    def test_a_resolvable_body_does_reach_the_write(self):
        """The positive control for the three refusals around it: without it,
        every test in this group would still pass on a hookup that resolves
        nothing at all."""
        store = self._Recorder()
        written, console = self._run(store, self._character(self._sniper_body()))
        self.assertEqual(written, SNIPER_CLASS_ID)
        self.assertEqual(store.writes, [(7, {"class_id": SNIPER_CLASS_ID})])
        self.assertIn(f"written class_id={SNIPER_CLASS_ID}", console)

    def test_a_refused_write_is_reported_not_raised(self):
        """A character soft-deleted between the INSERT and this write is the
        real shape of this: `write_typed_attributes` raises `KeyError` for a
        row it cannot see, and that must not become the creation's error."""
        store = self._Recorder(raises=KeyError(7))
        written, console = self._run(store, self._character(self._sniper_body()))
        self.assertIsNone(written)
        self.assertIn("write_refused", console)

    def test_every_console_line_is_ascii(self):
        """The bridge console is cp874; a byte outside it kills the tool that
        is reading the log (`AGENTS.md`, house rule on console output)."""
        store = self._Recorder()
        _written, console = self._run(store, self._character(b"\x99\x99"))
        console.encode("ascii")


class LoginThreadTests(_StoreCase):
    """Hookup 2: the login frame carries the row's class, end to end."""

    def test_the_login_sends_the_class_the_row_holds(self):
        character = self._born_sniper()
        session = FoundationSession(self.lifecycle, self.projector, "snipe1")
        selected, (_pc, frame) = session.select_and_start(character.selector)
        self.assertEqual(selected.class_id, SNIPER_CLASS_ID)
        self.assertIn(self._class_tag(SNIPER_CLASS_ID), frame)
        self.assertNotIn(
            self._class_tag(player_wire.PLAYER_LOGIN_CLASS_ID), frame,
        )

    def test_a_row_without_a_class_still_logs_in_on_the_constant(self):
        character = self._born_classless()
        session = FoundationSession(self.lifecycle, self.projector, "nogear")
        selected, (_pc, frame) = session.select_and_start(character.selector)
        self.assertIsNone(selected.class_id)
        self.assertIn(
            self._class_tag(player_wire.PLAYER_LOGIN_CLASS_ID), frame,
        )

    def test_a_recompose_of_the_same_character_carries_it_too(self):
        """The reason the class rides the character rather than an argument.

        `runtime.py` recomposes this frame up to three more times per
        production login (faction probe, scene-override resync, pinned
        identity), each from the object `session` resolved.  A class threaded
        into the login call only is a class the next recompose puts back to
        the constant -- green in a unit test, absent from the frame the
        client keeps.
        """
        character = self._born_sniper()
        session = FoundationSession(self.lifecycle, self.projector, "snipe1")
        selected, (_pc, frame) = session.select_and_start(character.selector)
        _pc2, recomposed = self.projector.start_game(selected)
        self.assertIn(self._class_tag(SNIPER_CLASS_ID), recomposed)
        self.assertEqual(len(recomposed), len(frame))

    def test_the_console_says_which_class_the_login_carries(self):
        character = self._born_sniper()
        session = FoundationSession(self.lifecycle, self.projector, "snipe1")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            session.select_and_start(character.selector)
        console = stderr.getvalue()
        console.encode("ascii")
        self.assertIn(f"LOGIN_CLASS_ID from_row class_id={SNIPER_CLASS_ID}",
                      console)

    def test_the_console_says_fallback_when_the_row_has_no_class(self):
        character = self._born_classless()
        session = FoundationSession(self.lifecycle, self.projector, "nogear")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            session.select_and_start(character.selector)
        console = stderr.getvalue()
        console.encode("ascii")
        self.assertIn("LOGIN_CLASS_ID fallback", console)
        self.assertIn(
            f"class_id={player_wire.PLAYER_LOGIN_CLASS_ID}", console,
        )


class TheLoginReadNeverRaisesTests(unittest.TestCase):
    """`runtime.py`'s START_GAME_REQ handler catches KeyError,
    PermissionError, ValueError and RuntimeError only, and v141 wraps the
    per-connection loop in try/finally with no except at all: anything else
    escaping this read parks the client on "connecting" forever
    (`COO-DECISION 20260903_1943` point 3 -- a login must not fail because
    this column could not be read)."""

    def test_no_store_reads_none(self):
        self.assertIsNone(session_module._class_id_on_the_row(None, 1))

    def test_no_character_id_reads_none(self):
        self.assertIsNone(session_module._class_id_on_the_row(object(), None))

    def test_a_store_without_the_method_reads_none(self):
        self.assertIsNone(session_module._class_id_on_the_row(object(), 1))

    def test_every_exception_class_reads_none(self):
        for error in (
            KeyError(1), PermissionError(), ValueError(), RuntimeError(),
            TypeError(), AttributeError(), MemoryError(),
        ):
            with self.subTest(error=type(error).__name__):
                class Raiser:
                    def read_typed_attributes(self, character_id):
                        raise error

                self.assertIsNone(
                    session_module._class_id_on_the_row(Raiser(), 1)
                )

    def test_a_null_column_reads_none(self):
        class Empty:
            def read_typed_attributes(self, character_id):
                return {}

        self.assertIsNone(session_module._class_id_on_the_row(Empty(), 1))

    def test_the_console_line_never_raises_on_a_stub_character(self):
        line = session_module._class_id_console_line(object())
        self.assertIsInstance(line, str)
        line.encode("ascii")


class TheFramelessBaselineTests(_LegacyCase):
    """A character with no class composes byte-for-byte what main composes.

    This is the "changes nothing until the row says otherwise" half of the
    change: the empty splat leaves the composer's own signature default in
    place, and the field is fixed-width either way, so the recompose length
    guards in `runtime.py` see the same number of bytes.
    """

    def _character(self, class_id=None):
        return Character(
            id=1, account_id=1, selector=0, name="test01",
            actor_wire=b"", avatar_wire=b"",
            identity_lo=IDENTITY_LO, identity_hi=IDENTITY_HI,
            position=Position(SCENE_ID, SCENE_SEQ, 0.0, 0.0, 0.0),
            class_id=class_id,
        )

    def setUp(self):
        self.projector = LegacyProjector(self.legacy)

    def test_none_composes_the_frame_the_constant_composes(self):
        _pc, without = self.projector.start_game(self._character(None))
        _pc2, with_constant = self.projector.start_game(
            self._character(player_wire.PLAYER_LOGIN_CLASS_ID)
        )
        self.assertEqual(without, with_constant)

    def test_another_class_keeps_the_frame_length(self):
        _pc, baseline = self.projector.start_game(self._character(None))
        _pc2, sniper = self.projector.start_game(
            self._character(SNIPER_CLASS_ID)
        )
        self.assertEqual(len(sniper), len(baseline))
        self.assertNotEqual(sniper, baseline)


if __name__ == "__main__":
    unittest.main()
