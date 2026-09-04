"""COO-DECISION 20260904_0848 item 4 -- one log-only console line per frame,
naming what `parse_outer` COULD see: `vital_count` and the first (only)
nested vital id it ever decodes.

Why this exists (LANE-A D13, chief 0910, both this round's letters):
`current/pf_login_game_server_v141.py:parse_outer` is frozen and decodes
exactly ONE nested vital per frame, by its own design comment ("with more
than one, boundaries require each vital's serializer schema"). A frame whose
outer envelope declares `vital_count >= 2` therefore carries nested vitals
this dispatcher cannot identify at all -- silently: no exception, no refusal
event, nothing in the events trail. R307's own capture of the frame family
`GT-228` is about to boot against recorded `vital_count = 2`
(`lane_a_island_trigger_log.py`'s own comment), so every hook written so far
against that family (LANE-A's walker included) can only ever fire if the
vital it wants is FIRST -- and nothing before this round told a tester
watching the console that a frame ever arrived with company.

This module does not attempt to decode a second vital (there is no generic
way to, per the paragraph above) and sends no byte anywhere. It only proves
the one new console line: it fires on every frame, unconditionally, and
tells the truth about what is and is not visible.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

TOKEN = "DISPATCH_NESTED_VITALS"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _outer(legacy, vital_count: int, nested_id: int, nested_body: bytes) -> bytes:
    """A minimal PcProtocol envelope with the outer VitalData mask set and a
    caller-chosen declared `vital_count` -- which `parse_outer` never
    validates against how many vitals are actually present in the bytes
    (it always decodes exactly one), so `vital_count=2` here is exactly the
    shape a real 2-vital frame has from `parse_outer`'s point of view: one
    decodable nested vital, and a declared count that says there was more.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, vital_count)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + nested_body
    )


class DispatchNestedVitalVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _login_and_start(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def test_a_single_vital_frame_reports_its_own_id_and_count_one(self):
        state = self._login_and_start("dnv1")
        pc = _outer(self.legacy, 1, self.legacy.TRIGGER_VITAL, b"")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(pc))
        console = stderr.getvalue()
        self.assertIn(TOKEN, console)
        self.assertIn("vital_count=1", console)
        self.assertIn(
            "first_nested_id=0x%04X" % self.legacy.TRIGGER_VITAL, console,
        )

    def test_a_frame_declaring_two_vitals_says_so_and_admits_the_second_is_unseen(self):
        # The dangerous shape this line exists to surface: a frame whose
        # SECOND vital (never decoded by parse_outer, never reachable by any
        # hook keyed on it) might be exactly the one GT-228 needs.
        state = self._login_and_start("dnv2")
        pc = _outer(self.legacy, 2, self.legacy.TRIGGER_VITAL, b"")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(pc))
        console = stderr.getvalue()
        self.assertIn(TOKEN, console)
        self.assertIn("vital_count=2", console)
        self.assertIn(
            "first_nested_id=0x%04X" % self.legacy.TRIGGER_VITAL, console,
        )
        self.assertIn("NOT visible", console)

    def test_a_frame_with_no_vitaldata_collection_prints_none_not_a_crash(self):
        # outer_mask without bit 0x02: parse_outer leaves nested_id as None.
        # The line must say so plainly rather than raise formatting a hex id
        # out of None -- this is the login/StartGame shape used by setUp
        # itself, so if this regresses, EVERY test in this suite fails first.
        state = self._login_and_start("dnv3")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_empty_gscn_pc()
            ))
        console = stderr.getvalue()
        self.assertIn(TOKEN, console)
        self.assertIn("vital_count=0", console)
        self.assertIn("first_nested_id=none", console)

    def test_the_line_fires_on_every_frame_unconditionally(self):
        # Not once-per-reason like `_vital_walk_say`'s refusal lines a few
        # hundred lines below in runtime.py -- COO-DECISION 20260904_0848
        # item 4 asks for "one line PER FRAME", and a tester cutting P1-c
        # live needs every frame, not a deduped first occurrence.
        state = self._login_and_start("dnv4")
        pc = _outer(self.legacy, 1, self.legacy.TRIGGER_VITAL, b"")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(pc))
            state.dispatch(self.legacy.parse_outer(pc))
            state.dispatch(self.legacy.parse_outer(pc))
        self.assertEqual(stderr.getvalue().count(TOKEN), 3)


if __name__ == "__main__":
    unittest.main()
