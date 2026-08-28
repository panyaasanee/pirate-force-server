"""The condition that keeps `COO-DECISION 20260829_0542` true.

WHY THIS FILE EXISTS
--------------------
`COO-DECISION 2026-08-29T05:42+07:00` (pf_bridge/notes_to_chief/
20260829_0542_COO-DECISION-standalone-map-is-not-consumed.md) confirmed this
lane's assumption: the STANDALONE login-scene map
(`config/gm_login_scene_standalone.json`) is NOT consumed on use, while the
GM-gated map (`config/gm_login_scene.json`) stays single-use per
`COO-DECISION 20260829_0441` item 2.

The COO did not confirm it unconditionally.  Item 3 of that decision:

    if any path ever lets the client or a chat command write/modify the
    standalone file, THIS DECISION IS VOID IMMEDIATELY and the standalone
    map becomes single-use, without asking again.

Item 4 then assigns this lane one job, due this round: a test that pins item
3, so that "if somebody adds a write path later, the test goes RED".  That is
this file, and it is a separate artefact on purpose -- the same reasoning as
`tests/test_gm_say_gate_lock.py`.  A condition living only inside the test
file of the module it constrains is a condition that gets edited by whoever
is changing that module.  Deleting this file has to be a visible act.

WHAT IT ACTUALLY MEASURES, AND IN WHICH ORDER
---------------------------------------------
Two layers, and the weaker one is named as weak rather than left to look
like proof:

1. THE DOOR (primary).  Every command name the lane's own parser accepts is
   driven END TO END through the production entry point
   (`chat_command_action.make_gm_chat_command_action`), as a listed GM, with
   the standalone map pointed at a throwaway file that already holds an
   operator's line.  Afterwards that file must be byte-identical, its
   directory must hold no new file, the real cwd-relative production path
   must not have appeared, and no write-capable call recorded during the run
   may have named a file called `gm_login_scene_standalone.json`.  It
   watches the FILE and the CALLS rather than the source, so it does not
   care which module the write came from -- one that does not exist yet
   included.  The CLIENT half of item 3 is a second door and is driven too:
   `runtime.py`'s `0x51E9` branch -> `lane_hooks/lane_gm_run_command.py` ->
   `gm/dispatch.handle_gm_run_command_vital`, on client-supplied bytes.

   ASK ABOUT THE NAME, NOT ABOUT ONE RESOLVED PATH.  This is the finding
   that rebuilt the file.  The first version asserted only about the path
   its own fixture created; production resolves the map from
   `STANDALONE_ENV_OVERRIDE` or, unset, from a cwd-relative
   `config/gm_login_scene_standalone.json`, so a nine-line write to the
   REAL file passed the whole suite (4299 tests) green.  "The standalone
   file" is not one file -- it is whatever the process's environment and
   working directory name at that instant -- so the question has to be
   asked about the basename and about the production default, both.

   WHAT IT STILL DOES NOT COVER, stated rather than left to be discovered:
   the recorder wraps five families of Python-level call (`builtins.open`,
   `io.open`, `os.open`, and `os.replace/rename/remove/unlink/truncate`) --
   module attributes, not syscalls.  A write reaching the file through none
   of them (`os.symlink`/`os.link`, `os.write` on a descriptor opened
   before the watch, a subprocess) is caught only if it leaves a difference
   in the file, the directory listing, the production path or the reader's
   result -- which the same assertions do check.  One route evades both
   halves and is named rather than papered over: a write DEFERRED past the
   `with` block (a thread, a timer, `atexit`) lands after the assertions
   run.  So the claim is "no route that ran", not "no route that exists".
2. THE SCAN (early warning only).  A source scan over the lane's package for
   the standalone map's names.  pf-adversary has already defeated one scan of
   exactly this shape by splitting a string literal
   (`login_scene_stage._standalone_config_path`'s own comment records it), so
   nothing here rests on the scan alone.

THE TRIPWIRE FOR TOMORROW'S COMMAND.  A test that enumerates today's six
commands says nothing about the seventh.  So the exercise table is compared
against `commands.COMMAND_NAMES` itself: adding a command name without adding
a line here fails this file, which is the point -- the new command has to be
walked past this door before it ships.

NONCLAIM.  This file does not claim the standalone map is safe.  It skips
`gm_accounts.json` membership entirely, which is a STRONGER capability than
anything the GM-gated map grants, and this lane said so in the ASK the COO
answered.  All that is claimed is the property item 3 rests on: nothing a
client sends, or a chat line triggers, can write that file.  Its remaining
protection is that only an operator at the machine can create it.
"""
from __future__ import annotations

import builtins
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands  # noqa: E402
from pirateforce_foundation.gm import dispatch as gm_dispatch  # noqa: E402
from pirateforce_foundation.gm import login_scene_consume  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

# Not the real accepted version -- RE-129 is open and GT-101 measured what an
# unproven one does to a live client.  Patched in only so the ForcePos branch
# of `/warp` is actually WALKED by this file rather than stopping at the gate:
# a door that is only tested with the corridor behind it shut proves little.
UNPROVEN_TEST_VERSION = 7

PORT_ROYAL = 1
PRISON_EXILE = 2

# Taken from the reader's own constant, never spelled here: the guard has to
# follow the file if it is ever renamed, and a hand-copied name would silently
# stop matching on the day that happens.
STANDALONE_BASENAME = Path(
    login_scene_override.STANDALONE_DEFAULT_CONFIG_PATH
).name

# One line per name in `commands.COMMAND_NAMES`, and the equality test below
# fails if that tuple ever grows past this table.  `/warp` gets three lines
# because it is the only command with more than one destination: same-scene
# (ForcePos), cross-scene (stages a login scene ON DISK), and the bare form.
COMMAND_EXERCISES: dict[str, tuple[str, ...]] = {
    "warp": (
        "/warp 1 100 200",  # same scene as the session -> ForcePos half
        "/warp 2 100 200",  # different scene -> stages the GM-gated map
        "/warp 2",  # no coordinates -> stages too
    ),
    "npc": ("/npc on 1001", "/npc off 1001"),
    "item": ("/item 5 3",),
    "lv": ("/lv 40",),
    "spawn": ("/spawn 1001",),
    "say": ("/say hello",),
}

# Lines that are not valid commands at all, run through the same door: a
# refusal path is still a path, and the parse-error branch is the one most
# likely to grow a "helpful" write someday.
HOSTILE_LINES = (
    "/warp",
    "/warp 999999",
    "/standalone_login_scene 2",
    "/warp ../config/gm_login_scene_standalone.json",
    "/say " + "x" * 600,
    "/nosuchcommand 1",
    "hello",
)


def make_chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape."""
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class FakePosition:
    def __init__(self, scene_id=PORT_ROYAL, x=10.0, y=20.0, z=30.0):
        self.scene_id = scene_id
        self.scene_seq = 0
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, position=None):
        self.position = position
        self.id = 1


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, token, position=None):
        self.token = token
        self.events = []
        self.foundation = FakeFoundation(FakeSelected(position))


class WriteWatch:
    """Records every path handed to a filesystem call that can change a file.

    Deliberately not a mock of one module's writer: the property under test is
    "no route at all", so this wraps the entry points a route would have to go
    through, whichever module it lives in.  `builtins.open` and `io.open` are
    both wrapped because they are separate module attributes bound to the same
    function -- patching one leaves `Path.open` going through the other.

    It is an over-approximation on purpose: it records reads it cannot tell
    from writes rather than risk missing a write.  The assertion is only ever
    "the standalone path is not in this list", so a false entry costs nothing
    and a missed one costs the whole guarantee.
    """

    WRITE_MODE_CHARS = set("wax+")

    def __init__(self):
        self.paths: list[str] = []
        self._patches: list = []

    def _record(self, target) -> None:
        if isinstance(target, int):
            # A file descriptor, not a path.  It got here through one of the
            # openers below, which recorded the path it came from.
            return
        try:
            self.paths.append(os.path.realpath(os.fspath(target)))
        except TypeError:  # pragma: no cover - defensive, non-path argument
            pass

    def __enter__(self):
        real_builtins_open = builtins.open
        real_io_open = io.open
        real_os_open = os.open

        def wrapped_open(file, mode="r", *args, **kwargs):
            if self.WRITE_MODE_CHARS & set(str(mode)):
                self._record(file)
            return real_builtins_open(file, mode, *args, **kwargs)

        def wrapped_io_open(file, mode="r", *args, **kwargs):
            if self.WRITE_MODE_CHARS & set(str(mode)):
                self._record(file)
            return real_io_open(file, mode, *args, **kwargs)

        write_flags = (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        )

        def wrapped_os_open(path, flags, *args, **kwargs):
            if flags & write_flags:
                self._record(path)
            return real_os_open(path, flags, *args, **kwargs)

        self._patches = [
            mock.patch.object(builtins, "open", wrapped_open),
            mock.patch.object(io, "open", wrapped_io_open),
            mock.patch.object(os, "open", wrapped_os_open),
        ]
        # The mutators: each records EVERY path argument, source and
        # destination alike.  A rename onto the standalone file and a rename
        # of it out of the way are both writes to it in the sense item 3
        # cares about.
        for name in ("replace", "rename", "remove", "unlink", "truncate"):
            self._patches.append(self._patch_mutator(name))
        for patch in self._patches:
            patch.start()
        return self

    def _patch_mutator(self, name: str):
        real = getattr(os, name)

        def wrapped(*args, **kwargs):
            for argument in args:
                self._record(argument)
            return real(*args, **kwargs)

        return mock.patch.object(os, name, wrapped)

    def __exit__(self, *exc_info):
        for patch in reversed(self._patches):
            patch.stop()
        self._patches = []
        return False

    def touched(self, path) -> bool:
        return os.path.realpath(os.fspath(path)) in self.paths

    def named_basename(self, basename: str) -> list[str]:
        """Every recorded path whose FILE NAME is `basename`, resolved or not.

        THE FINDING THIS METHOD EXISTS FOR, and it is the most important
        sentence in this file.  The first version asked only "was the path my
        fixture created written to?", and pf-adversary walked a nine-line
        write straight past it: production does not resolve the standalone
        map to the fixture's path.  It resolves it from
        `STANDALONE_ENV_OVERRIDE` or, when that is unset -- the ordinary
        deployment -- from the cwd-relative
        `config/gm_login_scene_standalone.json`.  A future command that
        resolves the path the way the neighbouring `login_scene_stage`
        resolves its own map writes the REAL file with the whole suite green.

        So the question is asked about the NAME, not about one resolved
        instance.  This also closes the `dir_fd` route, where the recorded
        path is a bare relative name that would never match a realpath.
        """
        return [
            candidate
            for candidate in self.paths
            if os.path.basename(candidate) == basename
        ]


class _Case(unittest.TestCase):
    GM_ACCOUNT = "GM_ONE"
    PLAYER_ACCOUNT = "DECKHAND"
    # The operator's own line, for an account that is NOT a GM -- which is the
    # whole point of the standalone map and the reason erasing it would be the
    # worse surprise the COO's decision names.
    OPERATOR_ENTRY = {
        login_scene_override.STANDALONE_JSON_KEY: {PLAYER_ACCOUNT: PRISON_EXILE}
    }

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

        self.accounts_path = self.tmp / "gm_accounts.json"
        self.accounts_path.write_text(
            json.dumps({"gm_accounts": [self.GM_ACCOUNT]}), encoding="utf-8"
        )
        self.log_path = self.tmp / "capture" / "gm_command_log.ndjson"
        self.login_scene_config_path = self.tmp / "config" / "gm_login_scene.json"

        # A REAL standalone file with real content, not an absent path: "the
        # file was never created" and "the file was rewritten" are different
        # failures, and only a pre-existing file can show the second one.
        self.standalone_dir = self.tmp / "standalone"
        self.standalone_dir.mkdir()
        self.standalone_path = (
            self.standalone_dir / "gm_login_scene_standalone.json"
        )
        self.standalone_path.write_text(
            json.dumps(self.OPERATOR_ENTRY), encoding="utf-8"
        )
        self.standalone_bytes = self.standalone_path.read_bytes()
        # The env var is how a real operator points the reader at their file,
        # so the door is tested through the same knob the deployment uses.
        env = mock.patch.dict(
            os.environ,
            {login_scene_override.STANDALONE_ENV_OVERRIDE: str(self.standalone_path)},
        )
        env.start()
        self.addCleanup(env.stop)

        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def production_default_paths(self) -> list[Path]:
        """Where the REAL map would land if a route ignored the env var.

        Two candidates because the default is cwd-relative: the process's
        current directory (what the code would actually resolve) and the
        repo checkout (where a run from anywhere else would still be a
        deliverable somebody could commit).
        """
        relative = Path(login_scene_override.STANDALONE_DEFAULT_CONFIG_PATH)
        return [Path.cwd() / relative, ROOT / relative]

    def assert_every_command_was_accepted(self, session):
        """Every command name in the table got past the allowlist and audit.

        `EVENT_ACCEPTED_PREFIX` is emitted only for a line that was
        authorized, decoded and recorded -- i.e. one that really reached a
        handler.  Without this, a refusal that empties the run leaves every
        "the file was not written" assertion true and worthless.
        """
        for name in COMMAND_EXERCISES:
            with self.subTest(name=name):
                self.assertIn(
                    f"{chat_command_action.EVENT_ACCEPTED_PREFIX}{name}",
                    session.events,
                    f"/{name} never reached a handler, so this run proved "
                    "nothing about it",
                )

    def act(self, session, text):
        return chat_command_action.make_gm_chat_command_action(
            session,
            make_chat_payload(text),
            self.legacy,
            config_path=str(self.accounts_path),
            log_path=str(self.log_path),
            login_scene_config_path=str(self.login_scene_config_path),
        )

    def assert_standalone_map_untouched(self, watch: WriteWatch, what: str):
        # BY NAME FIRST, and this ordering is the finding: a write to ANY
        # path called `gm_login_scene_standalone.json` violates item 3,
        # whether it is this fixture's copy, the cwd-relative production
        # default, or one resolved some third way.
        self.assertEqual(
            [],
            watch.named_basename(STANDALONE_BASENAME),
            f"{what} named the standalone map in a write-capable call; "
            "COO-DECISION 20260829_0542 item 3 makes that decision void -- "
            "the standalone map becomes single-use and this lane owes the COO "
            "a letter, not a green test",
        )
        # The PRODUCTION path, not just the fixture's. `login_scene_override`
        # falls back to this cwd-relative name whenever the env var is unset,
        # which is the normal deployment and was the hole a planted write
        # went through while all thirteen tests passed.
        for default_path in self.production_default_paths():
            self.assertFalse(
                default_path.exists(),
                f"{what} created the REAL standalone map at {default_path}",
            )
        self.assertTrue(self.standalone_path.exists(), f"{what} deleted the file")
        self.assertEqual(
            self.standalone_bytes,
            self.standalone_path.read_bytes(),
            f"{what} changed the operator's standalone config",
        )
        self.assertEqual(
            [self.standalone_path.name],
            sorted(p.name for p in self.standalone_dir.iterdir()),
            f"{what} left a new file beside the operator's standalone config",
        )
        # The reader still returns what the operator typed, which is the
        # property the bytes above only stand in for.
        self.assertEqual(
            {self.PLAYER_ACCOUNT: PRISON_EXILE},
            login_scene_override.load_standalone_login_scene_overrides(
                str(self.standalone_path)
            ),
            f"{what} changed what the login path reads",
        )


class TheExerciseTableCoversTheWholeCommandSurfaceTests(_Case):
    def test_every_parsed_command_name_has_an_exercise_here(self):
        # The tripwire for tomorrow's command.  If this fails, a new GM
        # command exists and nobody has walked it past the door below.
        self.assertEqual(
            set(commands.COMMAND_NAMES),
            set(COMMAND_EXERCISES),
            "a GM command name was added or removed without updating this "
            "file; every command has to be driven past the standalone map "
            "before it ships (COO-DECISION 20260829_0542 item 4)",
        )

    def test_no_command_can_satisfy_that_check_with_an_empty_exercise(self):
        # MEASURED by pf-adversary: adding a name to `COMMAND_NAMES` and
        # `"name": ()` to the table left all thirteen tests green, because
        # the equality above compares KEYS and the per-line loops never run
        # on an empty tuple.  A command shipped "walked past the door"
        # without ever reaching it.
        for name, lines in COMMAND_EXERCISES.items():
            with self.subTest(name=name):
                self.assertGreater(
                    len(lines), 0, f"{name} has no line that reaches the door"
                )

    def test_each_exercise_line_really_parses_as_the_command_it_claims(self):
        # Otherwise a typo turns a real exercise into a parse-error case and
        # this file goes on passing while covering nothing.
        for name, lines in COMMAND_EXERCISES.items():
            for line in lines:
                with self.subTest(line=line):
                    parsed = commands.parse_gm_command(line.lstrip("/"))
                    self.assertEqual(name, parsed.name)


class ChatCommandsCannotWriteTheStandaloneMapTests(_Case):
    def _drive(self, lines, position_scene_id=PORT_ROYAL):
        session = FakeSession(
            self.GM_ACCOUNT, FakePosition(scene_id=position_scene_id)
        )
        with WriteWatch() as watch:
            for line in lines:
                self.act(session, line)
        return session, watch

    def test_no_command_from_a_listed_gm_writes_the_standalone_map(self):
        lines = [line for lines in COMMAND_EXERCISES.values() for line in lines]
        session, watch = self._drive(lines)
        self.assert_standalone_map_untouched(watch, "the GM command surface")
        self.assert_every_command_was_accepted(session)

    def test_every_exercise_line_really_reaches_a_handler(self):
        # THE VACUOUS-RUN GUARD.  pf-adversary lowered the shared rate limit
        # to 3 and watched five of the six command names come back
        # `refused_rate_limited` -- never reaching a handler -- while every
        # "did not write" assertion above stayed green and meaningless.  The
        # live budget is 20 per 5s against 9 lines driven with no sleep, so
        # the margin is real but the table is designed to grow.  Pin the
        # acceptance, so the day it truncates is the day this goes red.
        lines = [line for lines in COMMAND_EXERCISES.values() for line in lines]
        session, _ = self._drive(lines)
        self.assert_every_command_was_accepted(session)
        refusals = [
            event
            for event in session.events
            if event.startswith(chat_command_action.EVENT_REFUSED_PREFIX)
        ]
        self.assertEqual([], refusals, "a valid GM line was refused at the door")

    def test_the_same_is_true_with_the_force_pos_gate_open(self):
        # The gate being shut removes a whole branch from the run.  RE-129
        # will open it one day; this file must have walked that branch first.
        lines = [line for lines in COMMAND_EXERCISES.values() for line in lines]
        with mock.patch.object(
            teleport_wire,
            "FORCE_POS_VITAL_VERSION_CONFIRMED",
            UNPROVEN_TEST_VERSION,
        ):
            _, watch = self._drive(lines)
        self.assert_standalone_map_untouched(
            watch, "the GM command surface with ForcePos open"
        )

    def test_malformed_and_hostile_lines_do_not_reach_it_either(self):
        _, watch = self._drive(HOSTILE_LINES)
        self.assert_standalone_map_untouched(watch, "a refused chat line")

    def test_a_non_gm_typing_the_same_lines_reaches_nothing(self):
        # The allowlist half.  A player is refused before the payload is even
        # decoded, so this should be the quietest run of all -- but "should"
        # is why it is measured.
        session = FakeSession(
            self.PLAYER_ACCOUNT, FakePosition(scene_id=PORT_ROYAL)
        )
        lines = [line for lines in COMMAND_EXERCISES.values() for line in lines]
        with WriteWatch() as watch:
            for line in lines + list(HOSTILE_LINES):
                self.assertIsNone(self.act(session, line))
        self.assert_standalone_map_untouched(watch, "a non-GM chat line")

    def test_the_cross_scene_warp_really_did_write_the_OTHER_map(self):
        # The negative above is worth nothing if nothing happened at all.
        # This is the control: the same run that leaves the standalone map
        # alone DOES put an entry in the GM-gated one, so the door was shut
        # against a command that was genuinely writing to disk.
        self._drive(["/warp 2"])
        self.assertTrue(
            self.login_scene_config_path.exists(),
            "the cross-scene warp staged nothing, so this file proved nothing",
        )
        staged = json.loads(
            self.login_scene_config_path.read_text(encoding="utf-8")
        )[login_scene_stage_key()]
        self.assertEqual({self.GM_ACCOUNT: PRISON_EXILE}, staged)


class TheOtherClientDoorTests(_Case):
    """Item 3 says "the client OR a chat command" -- there are TWO doors.

    MEASURED by pf-adversary: this file's first version drove only the chat
    route, and `runtime.py`'s `GM_RUN_GM_COMMAND_VITAL_ID` (`0x51E9`) branch
    fires `lane_hooks.fire("vital_inbound_gm_run_command", ...)` ->
    `lane_hooks/lane_gm_run_command.py` (`production_allowed = True`) ->
    `gm/dispatch.handle_gm_run_command_vital`, on bytes the client sent.  A
    write planted there changed the standalone map from a client frame while
    all thirteen tests passed -- and it did not even need a split literal,
    because the source scan globs the `gm/` package and `lane_hooks/` is not
    in it.  This class drives that door with the same watch.

    The capture root is pinned to a temp directory: the hook calls the
    dispatcher with its default, which writes under the checkout.  That is
    the ONLY thing substituted -- the hook, the dispatcher, the allowlist
    check and the capture body are all the real ones.
    """

    def _fire_the_inbound_vital(self, token, payloads):
        """Fire the real hook, and REACH THE AUTHORIZED HALF.

        THE FIRST VERSION OF THIS METHOD WAS VACUOUS, and it was caught the
        same way D5 was.  The hook calls the dispatcher with no config path,
        so the allowlist resolved to the checkout's non-existent
        `config/gm_accounts.json` -- which means NOBODY is a GM and every
        payload, `GM_ONE` included, came back
        `gm_run_command_refused_not_gm_account`.  A write planted on the
        AUTHORIZED half of that door (past the allowlist check, which is
        where a real GM feature would live) was never reached, and the class
        added to close D2 passed while covering only the refusal branch.

        The allowlist is therefore pinned through `accounts.ENV_OVERRIDE` --
        the same knob an operator uses -- rather than by patching, so the
        hook's own default resolution is what finds it.
        """
        import functools

        from pirateforce_foundation import lane_hooks
        from pirateforce_foundation.gm import accounts as gm_accounts
        from pirateforce_foundation.gm import dispatch as gm_dispatch
        from pirateforce_foundation.lane_hooks import lane_gm_run_command

        capture_root = self.tmp / "capture"
        pinned = functools.partial(
            gm_dispatch.handle_gm_run_command_vital,
            capture_root=str(capture_root),
        )
        session = FakeSession(token, FakePosition())
        with mock.patch.dict(
            os.environ, {gm_accounts.ENV_OVERRIDE: str(self.accounts_path)}
        ):
            with mock.patch.object(
                lane_gm_run_command, "handle_gm_run_command_vital", pinned
            ):
                with WriteWatch() as watch:
                    for payload in payloads:
                        lane_hooks.fire(
                            "vital_inbound_gm_run_command",
                            session=session,
                            payload=payload,
                        )
        return session, watch

    PAYLOADS = (
        b"",
        b"\x00" * 16,
        b"/warp 2",
        b"gm_login_scene_standalone.json",
        b"\x48\x08\x00\x00\x00" + "warp 2".encode("utf-16-le"),
        bytes(range(256)),
    )

    def test_an_inbound_0x51E9_from_a_player_writes_nothing(self):
        session, watch = self._fire_the_inbound_vital(
            self.PLAYER_ACCOUNT, self.PAYLOADS
        )
        self.assert_standalone_map_untouched(watch, "an inbound 0x51E9 vital")
        # And the run was not empty: the hook really ran and really refused.
        self.assertTrue(
            any(e.startswith("gm_run_command_") for e in session.events),
            f"the hook never fired; events were {session.events}",
        )

    def test_an_inbound_0x51E9_from_a_listed_gm_writes_nothing_either(self):
        # The authorized half, which is the one that reaches the capture
        # writer.  A GM is still not a route to the standalone map.
        session, watch = self._fire_the_inbound_vital(
            self.GM_ACCOUNT, self.PAYLOADS
        )
        self.assert_standalone_map_untouched(
            watch, "an inbound 0x51E9 vital from a GM"
        )
        # THE AUTHORIZED HALF WAS REALLY REACHED, not just the door.  Without
        # this the class passes while every payload is refused as not-GM,
        # which is exactly how the first version of it proved nothing -- and
        # a real GM feature would live PAST this line, not before it.
        self.assertNotIn(
            "gm_run_command_refused_not_gm_account",
            session.events,
            "the listed GM was refused as a non-GM, so the authorized half "
            f"was never walked; events were {session.events}",
        )
        self.assertTrue(
            any(
                event == "gm_run_command_authorized_capture"
                for event in session.events
            ),
            "no payload reached the capture writer, so this run covered only "
            f"refusals; events were {session.events}",
        )

    def test_the_hook_this_class_drives_is_the_one_runtime_actually_fires(self):
        # Otherwise this class drives a point nothing sends to, and the
        # door it claims to cover is untested.  Read runtime.py rather than
        # trusting the name: the call site is chief's and can move.
        runtime_source = (
            ROOT / "src/pirateforce_foundation/runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"vital_inbound_gm_run_command"', runtime_source)


class TheLoginPathDoesNotWriteItEitherTests(_Case):
    """Item 3 says "the client OR a chat command", and login is the client.

    The consume path is the one that spends the GM-gated map on login.  It is
    also the only lane code a client can reach without typing anything, so a
    future edit that made it "tidy up" the standalone map would satisfy every
    test in `test_gm_login_scene_consume.py` that only reads scene ids back.
    """

    def _consume(self, account_name):
        return login_scene_consume.consume_login_scene_override(
            account_name,
            gm_accounts_config_path=str(self.accounts_path),
            login_scene_config_path=str(self.login_scene_config_path),
            standalone_config_path=str(self.standalone_path),
        )

    def test_consuming_a_standalone_scene_does_not_write_the_file(self):
        with WriteWatch() as watch:
            result = self._consume(self.PLAYER_ACCOUNT)
        self.assertEqual(PRISON_EXILE, result.scene_id)
        self.assertEqual(
            login_scene_consume.STANDALONE_NOT_CONSUMED, result.outcome
        )
        self.assert_standalone_map_untouched(watch, "the login consume path")

    def test_a_gm_login_that_spends_the_other_map_leaves_this_one_alone(self):
        from pirateforce_foundation.gm import login_scene_stage

        self.assertTrue(
            login_scene_stage.stage_login_scene(
                self.GM_ACCOUNT,
                PRISON_EXILE,
                gm_accounts_config_path=str(self.accounts_path),
                config_path=str(self.login_scene_config_path),
            ).staged
        )
        with WriteWatch() as watch:
            result = self._consume(self.GM_ACCOUNT)
        self.assertEqual(login_scene_consume.CONSUMED, result.outcome)
        self.assert_standalone_map_untouched(
            watch, "a login that spent the GM-gated map"
        )

    def test_the_reader_alone_writes_nothing(self):
        with WriteWatch() as watch:
            login_scene_override.get_login_scene_override(
                self.PLAYER_ACCOUNT,
                gm_accounts_config_path=str(self.accounts_path),
                login_scene_config_path=str(self.login_scene_config_path),
                standalone_config_path=str(self.standalone_path),
            )
        self.assert_standalone_map_untouched(watch, "the override reader")


class TheEarlyWarningScanTests(_Case):
    """Secondary, and named secondary: a scan is not a door.

    `login_scene_stage._standalone_config_path` carries the record of
    pf-adversary defeating a scan of exactly this shape by splitting a string
    literal.  It stays because it fails EARLY -- at review time, on a diff,
    before anyone runs the end-to-end cases -- not because it is sufficient.
    """

    # `login_scene_override.py` IS the reader: the file name and the JSON key
    # are its own constants.  Every other module in the package is scanned --
    # including `login_scene_consume.py` and `login_scene_stage.py`, whose
    # docstrings explain at length why they do not touch that map.  Prose is
    # stripped before the scan (module docstring + comment lines, the same
    # technique `test_gm_login_scene_stage.py` uses) so an explanation cannot
    # fail its own rule while CODE naming the map still trips.
    ALLOWED = {"login_scene_override.py"}
    NAMES = ("gm_login_scene_standalone", "standalone_login_scene")

    # The one pure READ any module may do, removed before the scan rather
    # than allowlisting the whole file: `login_scene_consume` has to ask that
    # map directly (see its own comment on the concurrent-claim finding), and
    # the JSON key is a substring of the reader's NAME, so leaving the name in
    # would let a real write hide behind it.
    ALLOWED_READER = "load_standalone_login_scene_overrides"

    @staticmethod
    def _code_only(source: str) -> str:
        """Prose out, code in -- and in THIS order, which is the finding.

        MEASURED by pf-adversary: dropping `#` lines FIRST and then removing
        the module docstring by string replacement is a no-op whenever the
        docstring contains a line starting with `#` -- a markdown heading,
        which the docstrings in this package are full of.  The whole
        docstring then survived into the scan and any module explaining why
        it does not touch the map got flagged, whose natural fix under time
        pressure is to allowlist the file: a permanent hole in the one place
        this guard is weak.  Cut the docstring out of the ORIGINAL source
        first, then drop comment lines.
        """
        import ast

        docstring = ast.get_docstring(ast.parse(source)) or ""
        without_prose = source.replace(docstring, "") if docstring else source
        return "\n".join(
            line
            for line in without_prose.splitlines()
            if not line.strip().startswith("#")
        )

    def _modules(self) -> list[Path]:
        """Every module a GM write route could live in, subpackages included.

        `glob("*.py")` over `gm/` alone missed BOTH places pf-adversary put a
        working write: `lane_hooks/lane_gm_run_command.py` (this lane's own
        hook, outside the `gm` package) and any future `gm/data/*.py`.
        """
        src = ROOT / "src/pirateforce_foundation"
        return sorted(
            list((src / "gm").glob("**/*.py"))
            + list((src / "lane_hooks").glob("lane_gm_*.py"))
        )

    # Files that must be in the scan for it to mean anything.  A count floor
    # is a magic number that cannot notice the package shrinking; naming the
    # modules that actually carry the risk can.
    MUST_SCAN = (
        "login_scene_stage.py",
        "login_scene_consume.py",
        "chat_command_action.py",
        "commands.py",
        "dispatch.py",
        "lane_gm_run_command.py",
    )

    def test_only_the_reader_names_the_standalone_map_in_code(self):
        offenders = []
        for module in self._modules():
            if module.name in self.ALLOWED:
                continue
            code = self._code_only(module.read_text(encoding="utf-8"))
            code = code.replace(self.ALLOWED_READER, "")
            for name in self.NAMES:
                if name in code:
                    offenders.append(f"{module.name}: {name}")
        self.assertEqual(
            [],
            offenders,
            "a module outside the reader now names the standalone map in "
            "code; if it WRITES it, COO-DECISION 20260829_0542 is void "
            "(item 3)",
        )

    def test_the_scan_reaches_the_modules_that_could_carry_a_write(self):
        # A scan that silently scanned nothing, or scanned the wrong
        # directory, is the failure mode this project has had to fix twice.
        scanned = {module.name for module in self._modules()}
        for name in self.MUST_SCAN:
            with self.subTest(name=name):
                self.assertIn(name, scanned)

    def test_the_allowlist_names_files_that_exist(self):
        # An allowlist entry for a renamed file is a hole nobody can see.
        package = ROOT / "src/pirateforce_foundation/gm"
        for name in self.ALLOWED:
            with self.subTest(name=name):
                self.assertTrue((package / name).is_file())

    def test_a_markdown_heading_in_a_docstring_no_longer_defeats_the_strip(self):
        # The exact shape pf-adversary used.  Prose-only module, heading
        # inside the docstring, nothing in the code.
        prose_only = '"""Doc.\n\n# a markdown-ish heading\n\nstandalone_login_scene\n"""\nx = 1\n'
        self.assertNotIn(self.NAMES[1], self._code_only(prose_only))

    def test_the_scan_can_actually_see_a_planted_name(self):
        # The scan's own tripwire: pf-adversary defeated the last one of these
        # by splitting a literal, and a scan that cannot fail is worse than no
        # scan because it reads like coverage.
        planted = f"path = '{self.NAMES[0]}.json'"
        self.assertIn(self.NAMES[0], self._code_only(f'"""Doc."""\n{planted}\n'))

    def test_a_write_hidden_behind_the_allowed_reader_still_shows(self):
        planted = f'{self.ALLOWED_READER}(p)\nd["{self.NAMES[1]}"] = 2\n'
        stripped = self._code_only(f'"""Doc."""\n{planted}').replace(
            self.ALLOWED_READER, ""
        )
        self.assertIn(self.NAMES[1], stripped)

    def test_the_scan_can_actually_see_a_planted_name(self):
        # The scan's own tripwire: pf-adversary defeated the last one of these
        # by splitting a literal, and a scan that cannot fail is worse than no
        # scan because it reads like coverage.
        planted = f"path = '{self.NAMES[0]}.json'"
        self.assertIn(self.NAMES[0], self._code_only(f'"""Doc."""\n{planted}\n'))


def login_scene_stage_key() -> str:
    from pirateforce_foundation.gm import login_scene_stage

    return login_scene_stage.GM_LOGIN_SCENE_JSON_KEY


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
