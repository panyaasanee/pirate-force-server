"""Gate 2 is wired to ``bag_admission.may_enter_world`` -- COO-DECISION
20260829_0441.

The predicate itself is enumerated in ``tests/test_bag_admission.py`` (both
goldens x every item x every slot, through the three real ``inventory``
mutators).  This file asserts the ONE thing that file no longer can, now that
its anti-wiring guard is gone: that
``session.FoundationSession.select_and_start`` -- the production character
select path -- actually asks that predicate, that the answer changes what the
player gets, and that the refusal prints the token an operator needs.

The bags are NOT assembled here.  The admitted one is the return value of the
real ``mob_pickup.place_in_bag``; the refused ones are the return values of
the real ``inventory`` mutators and the shipped ``HYPOTHESIZED_V111_SLOT2``
constant.  A test that hand-built the bag it then admits would prove that the
predicate agrees with this file's idea of a pickup, not that a pickup gets in.

WHAT THIS DOES NOT PROVE.  The bag reaches ``select_and_start`` through a
lifecycle stub, because nothing writes an acquired row to the database yet --
``store.py`` has no INSERT and does not advance ``next_item_identity`` (that
is this round's open ticket, ``STORE-INSERT-001``).  So this file pins the
gate, not the round trip: "pick an item up, relog, it is still there" stays
un-proven end to end until that INSERT exists, and no line here should be
quoted as evidence for M5.
"""
from pathlib import Path
import io
import sys
import unittest
from contextlib import redirect_stderr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    bag_admission, mob_loot, mob_pickup,
)
from pirateforce_foundation.inventory import (  # noqa: E402
    HYPOTHESIZED_V111_SLOT2_BACKPACK,
    INITIAL_BACKPACK,
    move_known_item_to_free_slot,
)
from pirateforce_foundation.session import FoundationSession  # noqa: E402

ITEM = 2400046  # the roster's most common drop, as tests/test_mob_pickup.py uses
MOB = 0x2068
KILLER = 0x750059


def a_drop():
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE, ITEM, 1,
        mob_loot.as_wire_float(10.0),
        mob_loot.as_wire_float(20.0),
        mob_loot.as_wire_float(30.0),
        MOB, KILLER,
    )


class StubProjector:
    """Records what the session handed the client, if it got that far."""

    def __init__(self):
        self.started_with = []

    def start_game(self, selected, *, backpack):
        self.started_with.append((selected, backpack))
        return b"start-game-frame"


class StubLifecycle:
    """The two calls ``select_and_start`` makes before gate 2, and no more."""

    def __init__(self, backpack):
        self._backpack = backpack
        self.store = None

    def login(self, login_name):
        return 1, "session-1", []

    def select(self, session_id, selector):
        return ("character", selector)

    def backpack(self, session_id, selected):
        return self._backpack


def enter(backpack, *, allow_hypothesized_item_move=False):
    """Run the real gate.  Returns ``(session, stderr_text, error_or_None)``."""
    projector = StubProjector()
    session = FoundationSession(
        StubLifecycle(backpack), projector, "gate2-user",
        allow_hypothesized_item_move=allow_hypothesized_item_move,
    )
    captured, error = io.StringIO(), None
    with redirect_stderr(captured):
        try:
            session.select_and_start(0)
        except PermissionError as exc:
            error = exc
    return session, captured.getvalue(), error


class Gate2AdmitsAnAcquiredRow(unittest.TestCase):
    def test_a_bag_a_real_pickup_produced_enters_the_world(self):
        acquired, _item = mob_pickup.place_in_bag(INITIAL_BACKPACK, a_drop())
        self.assertGreater(len(acquired.items), len(INITIAL_BACKPACK.items))

        session, stderr, error = enter(acquired)

        self.assertIsNone(error, "gate 2 refused a bag mob_pickup produced")
        self.assertEqual(session.backpack, acquired)
        self.assertEqual(len(session.projector.started_with), 1)
        # The refusal token is for refusals.  An admitted bag printing one
        # would train an operator to ignore the line that matters.
        self.assertNotIn("BAG_ADMISSION", stderr, stderr)

    def test_a_golden_bag_still_enters_the_world(self):
        session, stderr, error = enter(INITIAL_BACKPACK)

        self.assertIsNone(error)
        self.assertEqual(session.backpack, INITIAL_BACKPACK)
        self.assertNotIn("BAG_ADMISSION", stderr, stderr)


class Gate2StillRefusesTheGovernedFamily(unittest.TestCase):
    def test_the_shipped_hyp_pf_008_post_state_is_still_refused(self):
        _session, stderr, error = enter(HYPOTHESIZED_V111_SLOT2_BACKPACK)

        self.assertIsInstance(error, PermissionError)
        self.assertIn("HYP-PF-008", str(error))
        # The whole point of the printed line: the operator sees WHICH
        # refusal this was, beside a message that names one hypothesis.
        self.assertIn("BAG_ADMISSION", stderr, stderr)
        self.assertIn("verdict=", stderr)

    def test_a_moved_item_from_the_real_mutator_is_still_refused(self):
        item = INITIAL_BACKPACK.items[0]
        moved, _identity = move_known_item_to_free_slot(
            INITIAL_BACKPACK, item.identity, 7,
        )

        _session, stderr, error = enter(moved)

        self.assertIsInstance(error, PermissionError)
        self.assertIn("BAG_ADMISSION", stderr, stderr)

    def test_the_opt_in_still_admits_the_governed_state(self):
        session, _stderr, error = enter(
            HYPOTHESIZED_V111_SLOT2_BACKPACK,
            allow_hypothesized_item_move=True,
        )

        self.assertIsNone(error, "the HYP-PF-008 opt-in lane regressed")
        self.assertEqual(session.backpack, HYPOTHESIZED_V111_SLOT2_BACKPACK)

    def test_a_malformed_bag_is_refused_even_with_the_opt_in_on(self):
        """The one deliberate difference from the pre-wiring condition.

        The old second term was a bare ``or allow_hypothesized_item_move``,
        so with the opt-in on gate 2 admitted a value that is not a Backpack
        at all.  Gate 1 raises on such a value first in production, so this
        is unreachable there -- which is exactly why it needs a test here.
        """
        _session, stderr, error = enter(
            "not a backpack", allow_hypothesized_item_move=True,
        )

        self.assertIsInstance(error, PermissionError)
        self.assertIn(
            f"verdict={bag_admission.VERDICT_MALFORMED}", stderr, stderr,
        )
        self.assertIn(
            f"reason={bag_admission.REASON_MALFORMED}", stderr, stderr,
        )


class TheConsoleLineIsAsciiOnly(unittest.TestCase):
    """The bridge console is cp874.  A non-ASCII byte kills the report."""

    def test_every_refusal_line_encodes_as_ascii(self):
        for label, bag in (
            ("hyp-008", HYPOTHESIZED_V111_SLOT2_BACKPACK),
            ("malformed", object()),
        ):
            with self.subTest(label):
                _session, stderr, error = enter(bag)
                self.assertIsInstance(error, PermissionError)
                stderr.encode("ascii")


if __name__ == "__main__":
    unittest.main()
