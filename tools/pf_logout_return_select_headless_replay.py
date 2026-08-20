#!/usr/bin/env python3
"""LOGOUT-RETURN-SELECT-001: headless replay for HYP-PF-028 (GT-033 B).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the return-select logout lane, driven through the REAL make_state_class
dispatcher on a throwaway COPY of the database, answers a pinned captured
LogoutVital with exactly two queued actions in order -- the designed
ReturnSelectServerVital (0x709E) response FIRST, then the byte-identical PF-012
ack -- commits the session lease ``closed_at`` before either byte is queued,
and schedules the PF-013 clean socket close.  An independent walker in this
file reads the 0x709E frame back from byte zero (envelope, nested vital id
0x709E version 0, the 16-byte body: 0x08 u8 = 0, 0x32 8-byte = 0, 0x44 empty
string) WITHOUT importing the module's composer for the read.

It proves NOTHING about a client.  No client has ever been shown one byte of
this profile; whether the real client transitions to character select on
0x709E is GT-033 (attended, not run).  The response is OUR design; round-100
static RE (agent D) proved an echo cannot transition the client and named
0x709E the strongest candidate while finding no client consumer, and the
original server's return-select response is unknown and unrecoverable.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.
The file named by ``--db`` (default ``state/pirateforce.sqlite3``) is read
once to copy it and once to hash it, and is never opened by SQLite for the
session; everything runs on the temporary copy, which is deleted on exit.
No repository file is written unless ``--evidence <path>`` is handed in.

Usage:
    py -3 tools/pf_logout_return_select_headless_replay.py
    py -3 tools/pf_logout_return_select_headless_replay.py --json
    py -3 tools/pf_logout_return_select_headless_replay.py --db state/pirateforce.sqlite3

Exit 0 = every wire guard held.  Exit 1 = at least one drifted.  Exit 2 = the
database file named on the command line does not exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
# The module under test.  This tool calls its loader and its composer ONCE (to
# build the OTHER side of the byte comparison); it NEVER asks the module to
# decode the dispatched bytes -- the walker below reads them by hand.
from pirateforce_foundation import logout_hypothesis as L  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "logout_hypothesis_return_select_server.json"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"

RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RSS_VITAL_ID = 0x709E
BODY_SIZE = 16
RESP_FRAME_SHA = (
    "08C2A925BD67CD3D0AFA7992F98D472ED8FD22787756521A5DF8CBF174E5CB8E"
)


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def walk_return_select_frame(pc: bytes) -> dict:
    """Read the one 0x709E response PC by hand, byte zero to the end."""
    if type(pc) is not bytes or len(pc) < 22:
        raise WalkError("the frame is shorter than the envelope")
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or _u32(pc, 4) != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != 4:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != 0x02:
        raise WalkError("the outer change mask is not 0x02")
    if pc[12] != 0x12 or _u16(pc, 13) != 1:
        raise WalkError("expected exactly one vital in the collection")
    if pc[15] != 0x12 or _u16(pc, 16) != RSS_VITAL_ID:
        raise WalkError("the nested vital id is not 0x709E")
    if pc[18] != 0x0B or pc[19] != 0x00:
        raise WalkError("the nested vital version is not 0")
    cur = 20
    if pc[cur] != 0x08:
        raise WalkError("field1 tag is not 0x08")
    field1 = pc[cur + 1]
    cur += 2
    if pc[cur] != 0x32:
        raise WalkError("field2 tag is not 0x32")
    field2 = int.from_bytes(pc[cur + 1:cur + 9], "little")
    cur += 9
    if pc[cur] != 0x44:
        raise WalkError("field3 tag is not 0x44")
    strlen = _u32(pc, cur + 1)
    cur += 5
    string = pc[cur:cur + strlen]
    cur += strlen
    # trailing derived-class change mask
    if pc[cur] != 0x0B or pc[cur + 1] != 0x00:
        raise WalkError("the trailing derived-class mask is not 0B 00")
    cur += 2
    if cur != len(pc):
        raise WalkError("the reader accounted for %d of %d bytes"
                        % (cur, len(pc)))
    return {"field1": field1, "field2": field2, "strlen": strlen,
            "string": string}


def table_row_counts(db_path: Path) -> dict:
    db = sqlite3.connect(str(db_path))
    try:
        names = [
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            name: db.execute('SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
            for name in names
        }
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class _RecordingTimerFactory:
    def __init__(self):
        self.scheduled = []

    def __call__(self, delay_seconds, callback):
        self.scheduled.append((delay_seconds, callback))
        return self

    def fire_all(self):
        for _delay, callback in self.scheduled:
            callback()


class _RecordingCloser:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


def main() -> int:
    want_json = "--json" in sys.argv
    db_source = DEFAULT_DB
    if "--db" in sys.argv:
        at = sys.argv.index("--db") + 1
        db_source = Path(sys.argv[at]) if at < len(sys.argv) else DEFAULT_DB
    db_source = db_source.resolve()
    if not db_source.is_file():
        print("no database file at %s" % ascii(str(db_source)))
        return 2

    failures: list[str] = []
    guards = 0

    def check(label, condition, detail=""):
        nonlocal guards
        guards += 1
        if condition:
            if not want_json:
                print("  PASS  %s" % label)
        else:
            failures.append(label)
            if not want_json:
                print("  FAIL  %s %s" % (label, detail))

    legacy = load_legacy(LEGACY_PATH)
    scenario = L.load_logout_hypothesis_scenario(SCENARIO)

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("the vital id and envelope agree with the module",
          RSS_VITAL_ID == L.RETURN_SELECT_SERVER_VITAL_ID
          and BODY_SIZE == L.RETURN_SELECT_SERVER_BODY_SIZE
          and RESP_FRAME_SHA == L.RETURN_SELECT_SERVER_RESPONSE_FRAME_SHA256)
    check("the response policy and hypothesis id agree",
          scenario.response_policy
          == L.LOGOUT_RESPONSE_POLICY_RETURN_SELECT_FIRST
          and scenario.hypothesis_id == "HYP-PF-028")
    check("production is not allowed", L.__dict__.get("production_allowed", None)
          is None and scenario.post_ack_action
          == L.LOGOUT_POST_ACK_ACTION_CLOSE_SOCKET)

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_logout_return_select001_")
    results: list[dict] = []
    try:
        db_path = Path(tmp) / "logout_return_select001.sqlite3"
        shutil.copyfile(db_source, db_path)
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real session "
                  "on it --")
        check("the copy lives in the temp directory, not at the source",
              db_path.is_file() and db_path.resolve() != db_source)
        check("the copy is byte-identical to the source before any use",
              sha256_file(db_path) == source_sha_before)
        store = SQLiteStore(db_path, ROOT / "migrations")
        check("the store is opened on the copy path ONLY",
              Path(store.path).resolve() == db_path.resolve()
              and Path(store.path).resolve() != db_source)
        store.migrate()
        projector = LegacyProjector(legacy)
        lifecycle = CharacterLifecycle(
            store,
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )
        timer_factory = _RecordingTimerFactory()

        def boot(token):
            closer = _RecordingCloser()
            state_type = make_state_class(
                legacy, lifecycle, projector,
                logout_hypothesis_scenario=scenario,
                close_timer_factory=timer_factory,
            )
            state = state_type(token)
            state.attach_transport_socket_closer(closer)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc(token)))
            characters = store.list_characters(state.foundation.account_id)
            if not characters:
                created = state.dispatch(
                    legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
                assert created and created[0][0] == "FOUNDATION_CREATE_COMMITTED"
                characters = store.list_characters(state.foundation.account_id)
            start = state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(characters[-1].selector)))
            assert start and start[0][0] in (
                "FOUNDATION_SELECTED_START_GAME",
                "SCENE2_LOAD_ONLY_SELECTED_START_GAME",
            )
            state.runtime_ack_sent = True
            return state, closer

        expected_rss = L.make_return_select_server_response(legacy)

        for subcode in (3, 1):
            state, closer = boot("logout_rs_%02d" % subcode)
            session_id = state.foundation.session_id
            check("subcode %02d: a character is selected on the copy" % subcode,
                  state.foundation.selected is not None)
            check("subcode %02d: the runtime-ready sequence flags are set"
                  % subcode,
                  state.teleport_sent is True and state.runtime_ack_sent is True)
            with store.connect() as db:
                pre = db.execute("SELECT closed_at FROM sessions WHERE id=?",
                                 (session_id,)).fetchone()
            check("subcode %02d: closed_at is NULL before the logout" % subcode,
                  pre is not None and pre["closed_at"] is None)

            before = table_row_counts(db_path)
            expected_ack = L.make_logout_ack_response(legacy, subcode)
            actions = state.dispatch(
                legacy.parse_outer(L.LOGOUT_REQUEST_PCS[subcode]))

            check("subcode %02d: exactly two actions, response then ack"
                  % subcode, len(actions) == 2, str(len(actions)))
            check("subcode %02d: action 0 is the return-select response label"
                  % subcode,
                  actions and actions[0][0] ==
                  "HYP_PF_028_LOGOUT_SUBCODE%02d_RETURN_SELECT_SERVER_"
                  "RESPONSE_FIRST" % subcode)
            check("subcode %02d: action 1 is the ack-then-close label" % subcode,
                  len(actions) > 1 and actions[1][0] ==
                  "HYP_PF_028_LOGOUT_SUBCODE%02d_ACK_THEN_SERVER_SOCKET_CLOSE"
                  % subcode)
            check("subcode %02d: the response bytes equal the composer's"
                  % subcode,
                  actions[0][1] == expected_rss[0]
                  and actions[0][2] == expected_rss[1])
            check("subcode %02d: the ack bytes are the unchanged PF-012 pins"
                  % subcode,
                  actions[1][1] == expected_ack[0]
                  and actions[1][2] == expected_ack[1])
            check("subcode %02d: neither action took a socket action inline"
                  % subcode, all(len(a) == 4 for a in actions))

            # Independent walk of the dispatched 0x709E frame.
            read = None
            error = ""
            try:
                read = walk_return_select_frame(bytes(actions[0][1]))
            except WalkError as exc:
                error = str(exc)
            check("subcode %02d: the dispatched 0x709E PC parses by hand"
                  % subcode, read is not None, error)
            if read is not None:
                check("subcode %02d: the walked body fields are all zero, "
                      "string empty" % subcode,
                      read["field1"] == 0 and read["field2"] == 0
                      and read["strlen"] == 0 and read["string"] == b"")
            check("subcode %02d: the dispatched response frame sha matches"
                  % subcode,
                  hashlib.sha256(bytes(actions[0][2])).hexdigest().upper()
                  == RESP_FRAME_SHA)
            check("subcode %02d: frame == frame_pc(pc) on the dispatched PC"
                  % subcode,
                  bytes(actions[0][2]) == legacy.frame_pc(bytes(actions[0][1])))

            with store.connect() as db:
                post = db.execute("SELECT closed_at FROM sessions WHERE id=?",
                                  (session_id,)).fetchone()
            check("subcode %02d: closed_at is committed after the logout"
                  % subcode,
                  post is not None and post["closed_at"] is not None)
            check("subcode %02d: the lease commit named the closed-before-ack "
                  "event" % subcode,
                  ("logout_hypothesis_subcode%02d_session_closed_before_ack"
                   % subcode) in state.events)
            check("subcode %02d: the return-select-before-ack event is named"
                  % subcode,
                  ("logout_hypothesis_subcode%02d_return_select_response_"
                   "before_ack" % subcode) in state.events)
            check("subcode %02d: the PF-013 close was scheduled at 250 ms"
                  % subcode,
                  state.logout_close_scheduled is True
                  and "logout_hypothesis_post_ack_socket_close_scheduled_250ms"
                  in state.events)

            after = table_row_counts(db_path)
            only_session_touched = all(
                after[name] == before[name]
                for name in after if name != "sessions"
            )
            check("subcode %02d: no table but sessions changed row count"
                  % subcode, only_session_touched,
                  json.dumps({k: (before[k], after[k]) for k in after
                              if before[k] != after[k]}))

            # Fire the close timer: the recorded closer runs exactly once.
            closer_before = closer.calls
            timer_factory.fire_all()
            check("subcode %02d: firing the scheduled timer closes once"
                  % subcode, closer.calls == closer_before + 1)
            timer_factory.scheduled.clear()

            results.append({
                "subcode": subcode,
                "response_label": actions[0][0],
                "response_frame_sha256":
                    hashlib.sha256(bytes(actions[0][2])).hexdigest().upper(),
                "closed_at_committed": post["closed_at"] is not None,
            })

        source_sha_after = sha256_file(db_source)
        if not want_json:
            print("-- 2. the source database was never touched --")
        check("the source database sha is unchanged end to end",
              source_sha_after == source_sha_before,
              "%s -> %s" % (source_sha_before, source_sha_after))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if want_json:
        print(json.dumps({
            "guards": guards,
            "failures": failures,
            "results": results,
            "source_sha256": source_sha_before,
        }, indent=2))
    else:
        print()
        print("guards run: %d" % guards)
    if failures:
        if not want_json:
            print("RESULT: FAIL - %d guard(s) drifted: %s"
                  % (len(failures), failures))
        return 1
    if not want_json:
        print("RESULT: PASS - the real dispatcher answers a captured "
              "LogoutVital with the pinned 0x709E response then the PF-012 "
              "ack, commits closed_at before either byte, schedules the "
              "PF-013 close, touches only the sessions table on a throwaway "
              "copy, and leaves the source database untouched (GT-033 is "
              "queued, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
