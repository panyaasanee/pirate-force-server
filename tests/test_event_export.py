"""EVENT-EXPORT-001 -- the opt-in console event exporter.

Pure offline pytest: no network, no GameClient, no UI; the dispatch half
runs the REAL ``make_state_class`` path against a throwaway temp database.

Why this lane exists: the GT-059 unattended round (2026-08-24) proved from
source that this build appends events to the in-memory ``self.events`` list
at 179 sites and never reads, prints or serializes one of them anywhere --
the only consumer is the test suite.  An attended or unattended ticket that
names an event string as its pass evidence therefore could never observe it.
The exporter closes that hole: behind ``--export-events`` (opt-in, default
off) every append -- dispatch and reject alike -- is echoed to stdout as one
line, ``PF-EVENT <seq> <event>``, forced into 7-bit ASCII so the cp874
bridge console can never die on an event payload.

What these tests prove
----------------------
The line format and the 1-based process-wide sequence; the ASCII forcing
(backslashreplace plus newline escaping) on hostile payloads; that the echo
list is a drop-in list (equality, slicing, len); that the default boot keeps
a PLAIN list and writes nothing (fail closed); and, on the real
make_state_class path, that both an accepted-dispatch event and a named
refusal event of an opt-in lane reach the exporter.

NOT tested here, because it is not claimed: that any real client ever
triggers any particular event; anything about the original server, which is
unrecoverable.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _EventEchoList,
    make_state_class,
    make_stdout_event_exporter,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.pickup_listener_hypothesis import (  # noqa: E402
    PICKUP_LISTENER_PROBE_FIELDS,
    PICKUP_LISTENER_VITAL_ID,
    PICKUP_LISTENER_VITAL_VERSION,
    compose_pickup_listener_probe_pc,
    load_pickup_listener_hypothesis_scenario,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "pickup_listener_hypothesis_decode_probe.json"
)


class ExporterFormatTests(unittest.TestCase):
    """The line format contract, without any server state at all."""

    def test_one_line_per_event_with_a_one_based_sequence(self):
        stream = io.StringIO()
        export = make_stdout_event_exporter(stream)
        export("first_event")
        export("second_event")
        self.assertEqual(
            stream.getvalue(),
            "PF-EVENT 1 first_event\nPF-EVENT 2 second_event\n",
        )

    def test_the_sequence_is_per_exporter_not_per_call_site(self):
        stream = io.StringIO()
        export = make_stdout_event_exporter(stream)
        for _ in range(3):
            export("x")
        other = io.StringIO()
        make_stdout_event_exporter(other)("y")
        self.assertIn("PF-EVENT 3 x", stream.getvalue())
        self.assertEqual(other.getvalue(), "PF-EVENT 1 y\n")

    def test_hostile_payloads_are_forced_into_ascii_single_lines(self):
        stream = io.StringIO()
        export = make_stdout_event_exporter(stream)
        export("caf\u00e9_\u0e01_event")
        export("two\nlines\rhere")
        # ASCII control characters survive backslashreplace, so they need
        # their own escaping rung: a form feed or vertical tab in a payload
        # must not become a second physical line (adversary R153 D2).
        export("page\x0cbreak\x0bhere\x1c")
        value = stream.getvalue()
        # Every byte survives both the strict ASCII and the cp874 console.
        value.encode("ascii")
        value.encode("cp874")
        lines = value.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "PF-EVENT 1 caf\\xe9_\\u0e01_event")
        self.assertEqual(lines[1], "PF-EVENT 2 two\\x0alines\\x0dhere")
        self.assertEqual(lines[2], "PF-EVENT 3 page\\x0cbreak\\x0bhere\\x1c")
        for line in lines:
            self.assertTrue(all(" " <= ch <= "~" for ch in line))

    def test_a_non_string_event_is_stringified_not_crashed(self):
        stream = io.StringIO()
        make_stdout_event_exporter(stream)(("tuple", 7))
        self.assertEqual(stream.getvalue(), "PF-EVENT 1 ('tuple', 7)\n")

    def test_a_dead_stream_never_raises_out_of_the_exporter(self):
        # A diagnostic may never alter dispatch: a closed or broken stream
        # loses the echoed line and nothing else (adversary R153 D1 -- the
        # unwrapped version burned one-shot latches and killed the game
        # listener thread when stdout died mid-session).
        class DeadStream:
            def write(self, value):
                raise BrokenPipeError("stdout is gone")

            def flush(self):
                raise BrokenPipeError("stdout is gone")

        export = make_stdout_event_exporter(DeadStream())
        export("event_while_stream_dead")  # must not raise
        seen = []
        events = _EventEchoList(export)
        events.append("still_recorded")
        self.assertEqual(events, ["still_recorded"])
        del seen

    def test_the_default_stream_is_the_live_sys_stdout(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            make_stdout_event_exporter()("default_stream_event")
        self.assertEqual(buf.getvalue(), "PF-EVENT 1 default_stream_event\n")


class EchoListTests(unittest.TestCase):
    """The echo list is a drop-in list, plus the echo."""

    def test_append_echoes_and_keeps_list_semantics(self):
        seen = []
        events = _EventEchoList(seen.append)
        events.append("a")
        events.append("b")
        self.assertEqual(seen, ["a", "b"])
        self.assertEqual(events, ["a", "b"])
        self.assertEqual(events[1:], ["b"])
        self.assertEqual(len(events), 2)


class RuntimePathTests(unittest.TestCase):
    """The exporter on the REAL make_state_class path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_pickup_listener_hypothesis_scenario(
            SCENARIO_PATH
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _ready_state(self, login, exporter):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            pickup_listener_hypothesis_scenario=self.scenario,
            event_exporter=exporter,
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        characters = self.store.list_characters(state.foundation.account_id)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        state.runtime_ack_sent = True
        return state

    def _probe(self, label="MID"):
        return self.legacy.parse_outer(
            compose_pickup_listener_probe_pc(
                self.legacy, PICKUP_LISTENER_PROBE_FIELDS[label],
            )
        )

    def _truncated_probe(self):
        legacy = self.legacy
        return legacy.parse_outer(bytes(
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, PICKUP_LISTENER_VITAL_ID)
            + legacy.u8tag(0x0B, PICKUP_LISTENER_VITAL_VERSION)
            + b"\x14"
        ))

    def test_dispatch_and_reject_events_both_reach_the_exporter(self):
        stream = io.StringIO()
        state = self._ready_state("evx01", make_stdout_event_exporter(stream))
        state.dispatch(self._probe("MID"))
        state.dispatch(self._truncated_probe())
        lines = stream.getvalue().splitlines()
        accepted = [
            line for line in lines
            if "pickup_listener_hypothesis_decoded_no_reply_" in line
        ]
        refused = [
            line for line in lines
            if "pickup_listener_hypothesis_" in line
            and "_no_reply" in line
            and "decoded" not in line
        ]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(refused), 1)
        for line in lines:
            self.assertRegex(line, r"^PF-EVENT \d+ \S")
        # The in-memory record the tests always consumed is untouched: the
        # echo list holds exactly what a plain list would.
        self.assertEqual(len(state.events), len(lines))
        # The whole stream survives the cp874 bridge console.
        stream.getvalue().encode("ascii")
        stream.getvalue().encode("cp874")

    def test_without_the_kwarg_the_events_list_stays_a_plain_list(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            pickup_listener_hypothesis_scenario=self.scenario,
        )
        state = state_type("evx02")
        self.assertIs(type(state.events), list)

    def test_the_default_boot_writes_no_event_line_at_all(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state_type = make_state_class(
                self.legacy, self.lifecycle, self.projector,
                pickup_listener_hypothesis_scenario=self.scenario,
            )
            state = state_type("evx03")
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc()
            ))
        self.assertNotIn("PF-EVENT", buf.getvalue())


class CliWiringTests(unittest.TestCase):
    """The flag is consumed by the pre-parser and wired to the factory."""

    def test_the_flag_rides_with_a_lane_and_the_db_gate_still_fires(self):
        from pirateforce_foundation import app
        saved = sys.argv[:]
        try:
            sys.argv = [
                "app.py", "--export-events",
                "--pickup-listener-hypothesis-scenario",
                str(SCENARIO_PATH),
            ]
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                with self.assertRaises(SystemExit) as ctx:
                    app.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn(
                "requires an explicit existing --db", buf.getvalue(),
            )
        finally:
            sys.argv = saved

    def test_the_wiring_is_ast_bound_not_a_source_substring(self):
        import ast
        source = (
            ROOT / "src" / "pirateforce_foundation" / "app.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        flag_added = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and any(
                isinstance(arg, ast.Constant)
                and arg.value == "--export-events"
                for arg in node.args
            )
            for node in ast.walk(tree)
        )
        self.assertTrue(flag_added)
        exporter_wired = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "make_state_class"
            and any(
                keyword.arg == "event_exporter" for keyword in node.keywords
            )
            for node in ast.walk(tree)
        )
        self.assertTrue(exporter_wired)


class SourceHygieneTests(unittest.TestCase):
    def test_this_test_file_is_ascii_and_survives_the_bridge_console(self):
        source = Path(__file__).read_text(encoding="utf-8")
        source.encode("ascii")
        source.encode("cp874")


if __name__ == "__main__":
    unittest.main()
