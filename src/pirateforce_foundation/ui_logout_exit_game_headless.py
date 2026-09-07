"""UI-B arming proof: the real Exit Game teardown on a real boot.

Why this file exists
--------------------
``NOW.md`` (PANYA ``0159`` / ``2148``) requires every attended ticket to
carry a ``HEADLESS_PROOF:`` line -- a console token from a headless run on
the CURRENT main commit showing the mechanism the ticket is about is armed,
plus a token saying the server actually sent something.  UI-B (queue item 1
of ``prompts/LANE-UI.md``) has had its code on ``main`` since the hookup at
``runtime.py``'s ``LOGOUT_VITAL_ID`` branch landed, and has had no ticket,
for exactly one reason: no single console line proved the branch fires on a
default, flagless boot.  This module IS that line.

It boots the REAL dispatcher (``make_state_class`` with
``logout_hypothesis_scenario`` left at its default ``None`` -- a real
player, not an attended hypothesis boot) on a throwaway database, drives
the REAL client bytes for one Exit Game click
(``logout_hypothesis.LOGOUT_REQUEST_PCS[1]``) through ``state.dispatch``,
and measures four things the button promises:

  * the ack action reaches the caller (``UI_LOGOUT_EXIT_GAME_ACK_THEN_
    SERVER_SOCKET_CLOSE``), so the branch is wired, not merely present;
  * the session lease row's ``closed_at`` goes from NULL to set -- read out
    of the database file, not out of the code;
  * the socket close is scheduled at the pinned delay and the scheduled
    callback really is the transport closer (it is fired, and the recording
    closer counts one call);
  * a fresh login afterwards can select the SAME character again -- the
    half of "exit game works" a player finds out about tomorrow.  Reported
    as ``relogin_after``, and pf-adversary F4 measured what it is NOT: a
    fresh login re-selects the same character with the lease still open and
    no exit click at all, so this field must never be read as evidence that
    the teardown is what unblocked the character.

It also drives the subcode-3 (UI-A, "back to character select") frame as a
negative control and asserts this lane composed nothing for it, because a
proof that fires on every logout frame would be proving the wrong branch.

What the token is entitled to say -- and what it is not
------------------------------------------------------
It says: on this commit, on a default boot with no flag and no scenario, a
real Exit Game click is answered by the server -- ack composed, lease
closed, socket close scheduled -- and the account can log back in.

It does NOT say what the real client draws after it receives that ack, that
any human has seen it, or that the window closes.  Those are the attended
ticket's questions and this proof does not answer one of them.

How to run it
-------------
From the repository root, with no PYTHONPATH and nothing installed::

    python3 src/pirateforce_foundation/ui_logout_exit_game_headless.py

``python3 -m pirateforce_foundation.ui_logout_exit_game_headless`` needs
``src`` on PYTHONPATH already and is NOT the documented form: the ticket's
re-run happens on a plain checkout.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
ROOT = _THIS_FILE.parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import logout_hypothesis  # noqa: E402
from pirateforce_foundation import ui_logout_exit_game  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

TOKEN_PREFIX = "UI_LOGOUT_EXIT_GAME_ARMED"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
ACK_LABEL = "UI_LOGOUT_EXIT_GAME_ACK_THEN_SERVER_SOCKET_CLOSE"
EXIT_GAME_SUBCODE = 1
BACK_TO_SELECT_SUBCODE = 3


def _refuse_a_foreign_checkout() -> None:
    """Every module in this proof must come from THIS tree, or say so loudly.

    The bootstrap above only inserts ``src`` when it is absent from
    ``sys.path``, so a PYTHONPATH naming another checkout's ``src`` FIRST
    wins: this file would drive that tree's module and dispatcher while the
    token names this commit.  ka1-A re-runs this proof before an attended
    boot and culls the ticket when it does not reproduce, so a token that
    can be produced by code from a different commit is worse than none.
    """
    home = str(ROOT / "src")
    for module in (
        "pirateforce_foundation.ui_logout_exit_game",
        "pirateforce_foundation.logout_hypothesis",
        "pirateforce_foundation.runtime",
        "pirateforce_foundation.store",
        "pirateforce_foundation.legacy_bridge",
    ):
        origin = Path(sys.modules[module].__file__).resolve()
        if not str(origin).startswith(home + "/") and not str(
            origin
        ).startswith(home + "\\"):
            raise RuntimeError(
                "%s came from %s, not from %s" % (module, origin, home)
            )


_refuse_a_foreign_checkout()


class _RecordingTimerFactory:
    """Deterministic stand-in for the threading.Timer close schedule."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self

    def fire_all(self) -> None:
        for _delay, callback in self.scheduled:
            callback()


class _RecordingCloser:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def _boot(store_path: Path):
    """Bring one REAL session to in-world, flagless, with a closer attached.

    Nothing here is UI-B specific: it is the ordinary login -> create ->
    start-game -> runtime-request path every player walks, which is the
    point.  Two things are stand-ins, both of which the real listener also
    supplies: ``close_timer_factory`` (recorded instead of threaded) and the
    transport socket closer (recorded instead of a real socket), so the
    proof is deterministic.  That is also the limit of what it can say: it
    measures that the close was SCHEDULED and the recorded closer CALLED,
    never that a real TCP FIN reached anyone.
    """
    legacy = load_legacy(LEGACY_PATH)
    store = SQLiteStore(store_path, ROOT / "migrations")
    store.migrate()
    lifecycle = CharacterLifecycle(
        store,
        Position(
            1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
            legacy.V135_PLAYER_Z,
        ),
        legacy.extract_avatar_attr_wire_from_actor,
    )
    timers = _RecordingTimerFactory()
    closer = _RecordingCloser()
    state_type = make_state_class(
        legacy, lifecycle, LegacyProjector(legacy),
        close_timer_factory=timers,
    )
    state = state_type("uib_arming")
    state.attach_transport_socket_closer(closer)
    state.dispatch(legacy.parse_outer(legacy._synthetic_client_login_pc()))
    characters = store.list_characters(state.foundation.account_id)
    if not characters:
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        characters = store.list_characters(state.foundation.account_id)
    selector = characters[-1].selector
    state.dispatch(legacy.parse_outer(
        legacy._synthetic_start_game_pc(selector)))
    # pf-adversary F3 (round `uw3bxb`): an earlier draft set
    # `state.runtime_ack_sent = True` by hand here -- which is exactly the
    # latch `_refused("wrong_sequence")` guards, so the proof was skipping
    # the precondition it claims to exercise (measured: deleting that line
    # flipped the token to RESULT=FAIL, i.e. it was load-bearing).  A real
    # client sets it by sending a runtime request; send that frame instead.
    state.dispatch(legacy.parse_outer(legacy.V136_EMPTY_RUNTIME_REQ_PC))
    if not state.runtime_ack_sent or not state.teleport_sent:
        raise RuntimeError(
            "boot did not reach in-world state: runtime_ack_sent=%r "
            "teleport_sent=%r" % (state.runtime_ack_sent, state.teleport_sent)
        )
    return legacy, store, state, selector, timers, closer


def _closed_at(store: SQLiteStore, session_id) -> object:
    with store.connect() as db:
        row = db.execute(
            "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
        ).fetchone()
    return None if row is None else row["closed_at"]


def prove_the_exit_game_click() -> str:
    """Drive one real Exit Game click and report every promise it makes."""
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "uib_arming.sqlite3"
        legacy, store, state, selector, timers, closer = _boot(store_path)
        session_id = state.foundation.session_id
        before = _closed_at(store, session_id)

        actions = state.dispatch(legacy.parse_outer(
            logout_hypothesis.LOGOUT_REQUEST_PCS[EXIT_GAME_SUBCODE]))
        labels = [action[0] for action in actions]
        after = _closed_at(store, session_id)

        scheduled_ms = (
            int(round(timers.scheduled[0][0] * 1000))
            if timers.scheduled else -1
        )
        timers.fire_all()

        # The half a player finds out about tomorrow: log in again and take
        # the same character.  A fresh state object on the SAME store, the
        # way a reconnect really arrives.
        relogin_type = make_state_class(
            legacy, CharacterLifecycle(
                store,
                Position(
                    1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                    legacy.V135_PLAYER_Z,
                ),
                legacy.extract_avatar_attr_wire_from_actor,
            ), LegacyProjector(legacy),
        )
        relogin = relogin_type("uib_arming")
        relogin.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc()))
        relogin_actions = relogin.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(selector)))
        relogin_ok = any(
            action[0] == "FOUNDATION_SELECTED_START_GAME"
            for action in relogin_actions
        )

    ok = (
        ACK_LABEL in labels
        and before is None
        and after is not None
        and closer.calls == 1
        # pf-adversary F5: comparing against the dispatcher's own default is
        # a tautology -- setting DEFAULT_CLOSE_DELAY_MS = 0 (a known-bad
        # variant: HYP-PF-013 is "the ack is on the wire before the FIN")
        # still printed RESULT=PASS.  Pin the number PF_LOGOUT_CLOSE001
        # actually measured instead.
        and scheduled_ms == logout_hypothesis.LOGOUT_CLOSE_DELAY_MS
        and relogin_ok
    )
    # pf-adversary F4: `relogin=ok` is a token that fires when state
    # changes, not when the target is reached -- measured, a fresh login
    # re-selects the same character with the lease still OPEN and no exit
    # click at all.  It stays in the line because UI-B promises it, and it
    # is labelled `relogin_after` so nobody reads it as evidence that the
    # teardown is what unblocked the character.
    return (
        "%s subcode=%d ack=%d lease_closed=%d close_scheduled_ms=%d "
        "closer_called=%d relogin_after=%s RESULT=%s"
        % (
            TOKEN_PREFIX, EXIT_GAME_SUBCODE, int(ACK_LABEL in labels),
            int(before is None and after is not None), scheduled_ms,
            closer.calls, "ok" if relogin_ok else "no",
            "PASS" if ok else "FAIL",
        )
    )


def prove_back_to_select_is_left_alone() -> str:
    """Negative control: UI-A's frame must reach none of this module's work.

    UI-A (subcode 3) is paused by ``NOW.md`` and owned by LANE-A's refusal
    notice.  If this lane ever starts answering it, the line below flips to
    FAIL and the ticket that quotes this token stops being about UI-B.
    """
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "uia_control.sqlite3"
        legacy, store, state, _selector, timers, closer = _boot(store_path)
        session_id = state.foundation.session_id
        actions = state.dispatch(legacy.parse_outer(
            logout_hypothesis.LOGOUT_REQUEST_PCS[BACK_TO_SELECT_SUBCODE]))
        mine = [
            action[0] for action in actions
            if str(action[0]).startswith("UI_LOGOUT_")
        ]
        still_open = _closed_at(store, session_id) is None
    ok = not mine and still_open and not timers.scheduled and not closer.calls
    return (
        "%s_CONTROL subcode=%d ui_actions=%d lease_still_open=%d "
        "close_scheduled=%d RESULT=%s"
        % (
            TOKEN_PREFIX, BACK_TO_SELECT_SUBCODE, len(mine),
            int(still_open), len(timers.scheduled),
            "PASS" if ok else "FAIL",
        )
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--control" in argv:
        line = prove_back_to_select_is_left_alone()
        print(line)
        return 0 if line.endswith("RESULT=PASS") else 1
    lines = [prove_the_exit_game_click(), prove_back_to_select_is_left_alone()]
    for line in lines:
        print(line)
    failed = [line for line in lines if not line.endswith("RESULT=PASS")]
    print(
        "%s_SUMMARY cases=%d failed=%d RESULT=%s"
        % (TOKEN_PREFIX, len(lines), len(failed),
           "PASS" if not failed else "FAIL")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
