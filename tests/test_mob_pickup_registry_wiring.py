"""LANE-B: ``mob_pickup_registry`` claim/release call sites (CORE-REQUEST-007
MOB_PICKUP_WIRING step 0, wired into ``runtime.py`` at chief round 3lzfhw),
pinned by an EXECUTED test rather than by call-site reading alone.

``mob_pickup.py`` NONCLAIM 1 has said since round 3lzfhw: "[MEASURED by
call-site reading, NOT by an executed test -- no test in ``tests/``
references ``mob_pickup_registry``/``mob_pickup_bag_cell``]".
``grep -rln "mob_pickup_registry\\|mob_pickup_bag_cell" tests/`` at the start
of this round (LANE-B, `p3olrt`) confirmed that sentence was still true on
``main``: zero hits, even though the call sites themselves
(``runtime.py:6485`` claim, ``runtime.py:1337`` release) have been live since
26 Aug.  This file closes exactly that gap and nothing else -- it does not
touch ``runtime.py``, ``mob_pickup.py``'s claim/refusal rules, or the
registry's own implementation.

WHAT IT PROVES, THROUGH THE REAL ``make_state_class`` DISPATCH (login ->
create -> StartGame, the same harness shape
``tests/test_scene_scoped_combat_wiring.py`` already uses for this lane, so
this file adds no new fixture pattern to the codebase):

  1. StartGame claims the registry for the selected character:
     ``state.mob_pickup_bag_cell`` is not ``None`` and
     ``state.mob_pickup_character_id`` is the selected character's own id.
  2. A SECOND session on the SAME account, selecting the SAME character
     before the first releases -- the "reconnect whose old session never
     reached close_connection" case ``mob_pickup.BagCellRegistry.claim``'s
     own docstring names -- is refused BY NAME
     (``mob_pickup_claim_refused_bag_already_claimed`` in ``state.events``)
     and its own ``mob_pickup_bag_cell`` stays ``None``.  This is the fact an
     executed test can prove that a call-site reading cannot: that the
     registry really is ONE shared, server-wide object (the claim in the
     first session is visible to the second), not two per-session objects
     that happen to have the same name.
  3. ``close_connection()`` releases the claim: a THIRD session on the same
     account can then claim the same character cleanly, and its own
     ``mob_pickup_bag_cell`` is not ``None``.

WHAT THIS FILE DOES NOT PROVE.  Nothing about a real pickup transaction
(``mob_pickup.dispatch_pickup_request`` /
``mob_pickup_persist.pickup_and_persist``) runs here -- ``GT-146`` (attended,
still ``PENDING`` at the head of the attended queue as of this round) still
gates the inbound-pickup-request call site BUILD-006 needs, unchanged by this
file.  This is the registry claim/release seam alone, at character select and
at teardown -- the ONE thing NONCLAIM 1 named as unproven by execution.
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

from pirateforce_foundation import mob_pickup  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class MobPickupRegistryWiringTests(unittest.TestCase):
    """Same harness shape as ``test_scene_scoped_combat_wiring.py``'s own
    ``_login_and_create``/``_start_game`` -- reused rather than reinvented."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
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
        # ONE state_type for the whole test: mob_pickup_registry is built
        # once, per make_state_class call, and closed over by every state
        # instance that factory produces -- exactly the sharing this file
        # exists to prove.  A second make_state_class call would build a
        # SECOND, independent registry, which would silently make every
        # claim in this file succeed for the wrong reason.
        self.state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness, same shape as test_scene_scoped_combat_wiring.py ---

    def _login(self, token):
        state = self.state_type(token)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_client_login_pc(token)
            ))
        return state

    def _create(self, state):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._V25_REAL_CREATE_PC
            ))
        return self.store.list_characters(state.foundation.account_id)[-1]

    def _start_game(self, state, character):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)
            ))
        return buf.getvalue()

    # ----- tests ---------------------------------------------------------

    def test_start_game_claims_the_registry_for_the_selected_character(self):
        state = self._login("pickup-reg-a")
        character = self._create(state)
        self._start_game(state, character)
        self.assertIsNotNone(state.mob_pickup_bag_cell)
        self.assertEqual(state.mob_pickup_character_id, character.id)
        self.assertFalse(
            any(
                event.startswith("mob_pickup_claim_refused_")
                for event in state.events
            ),
            "the first session's own claim must not be refused",
        )

    def test_a_second_session_on_the_same_character_is_refused_by_name(self):
        token = "pickup-reg-b"
        first = self._login(token)
        character = self._create(first)
        self._start_game(first, character)
        self.assertIsNotNone(first.mob_pickup_bag_cell)

        # Same account (same login token -> CharacterLifecycle.login's own
        # ensure_account is get-or-create), same character, a SEPARATE state
        # instance -- the "reconnect whose old session never reached
        # close_connection" shape the registry's own docstring names.
        second = self._login(token)
        self._start_game(second, character)

        self.assertIsNone(
            second.mob_pickup_bag_cell,
            "a second live claim for the same character must not be granted",
        )
        self.assertIsNone(second.mob_pickup_character_id)
        # Read the reason off the module's own constant, not a hand-typed
        # copy of it -- coupling held by a string, named as such (this
        # project's own convention): a rename of the reason keeps this
        # assertion honest instead of silently pinning stale text.
        self.assertIn(
            "mob_pickup_claim_refused_"
            + mob_pickup.REFUSE_BAG_ALREADY_CLAIMED,
            second.events,
        )
        # The first session's own claim is untouched by the second's refusal.
        self.assertIsNotNone(first.mob_pickup_bag_cell)
        self.assertEqual(first.mob_pickup_character_id, character.id)

    def test_close_connection_releases_the_claim_for_the_next_session(self):
        token = "pickup-reg-c"
        first = self._login(token)
        character = self._create(first)
        self._start_game(first, character)
        self.assertIsNotNone(first.mob_pickup_bag_cell)

        first.close_connection()

        third = self._login(token)
        self._start_game(third, character)
        self.assertIsNotNone(
            third.mob_pickup_bag_cell,
            "release must free the character for the next session's claim",
        )
        self.assertEqual(third.mob_pickup_character_id, character.id)
        self.assertFalse(
            any(
                event.startswith("mob_pickup_claim_refused_")
                for event in third.events
            ),
        )

    def test_close_connection_is_a_no_op_when_no_claim_was_ever_made(self):
        """A session that never reached StartGame (login only, or a claim
        that was itself refused) must not raise or double-release on
        teardown -- ``BagCellRegistry.release`` is only called when
        ``mob_pickup_bag_cell is not None`` (``runtime.py:1336``); this pins
        that guard from the outside rather than by reading it."""
        state = self._login("pickup-reg-d")
        self.assertIsNone(state.mob_pickup_bag_cell)
        # Must not raise.
        state.close_connection()
        self.assertIsNone(state.mob_pickup_bag_cell)


if __name__ == "__main__":
    unittest.main()
