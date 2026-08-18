#!/usr/bin/env python3
"""PF MULTIPLAYER-READINESS-AUDIT-001 -- deterministic counter behind
``reports/PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.md``.

This verifier exists for one reason: every number in that report has to be
re-derivable from the tree instead of typed by hand.  It is a *source scanner*,
not a claim.  It proves nothing about the client, the wire, or the original
server; it only asserts that the exact code sites the report cites are still
there, still in the file the report says, and still occur exactly as many times
as the report says.

Three families of number are produced:

  1. ASSUMPTION SITES -- the concrete places where the current server can only
     serve one player.  Each site is a (path, regex, expected occurrences)
     triple.  A site is graded ``immutable`` when it lives in
     ``current/pf_login_game_server_v141.py``, which project policy forbids
     editing: those sites cannot be fixed in place, only replaced from outside,
     and that split is the load-bearing architectural fact of the audit.

  2. READY SITES -- the places that are already keyed by session/account rather
     than by process, i.e. the parts of a second player that already work.
     Same triple shape, so "ready" is measured the same way as "not ready" and
     a standing note that turns out to be wrong shows up as a drifted guard.

  3. FRAME ANCHORS -- for every frame a second visible player needs, whether the
     client-side decoder is pinned by an existing report (``anchored``), pinned
     only outside the remote-actor context (``partial``), or absent
     (``guess``).  The evidence column is a repository path that must exist.

Line numbers are deliberately NOT pinned.  ``src/`` moves under concurrent
lanes; the report quotes the line numbers observed at HEAD ``5cc0eda`` and this
tool re-locates each site by content and prints where it landed today.  A moved
line is fine; a missing or duplicated site is a drift and exits nonzero.

Re-pinning procedure when a number legitimately moves: run this tool, take the
``--json`` output, and update the ``AUDIT_COUNTS`` fenced block in the report in
the same change.  ``tests/test_multiplayer_readiness_audit.py`` compares the two
and fails if they disagree, so the report cannot drift away from the tree.


TWO KINDS OF NUMBER, AND WHY THE SUITE TOTALS CHANGED SHAPE (SCAN-DEBT-001, round 84)
-------------------------------------------------------------------------------------
Everything above is a *live* measurement: it describes the tree as it is right
now and it must be exact.  Six of the numbers the report publishes are not that.
``tests_total_files_at_head``, ``tests_total_functions_at_head`` and the four
import-closure totals are **historical**: they describe the suite as it stood at
commit ``5cc0eda`` on 2026-08-18, which is what makes sentences like "package A
touches 53 % of the suite" mean anything.

They used to be compared with ``>=`` - "a suite may grow under a concurrent lane;
it may not shrink silently".  That rule cannot catch rot, only shrinkage.  By
round 84 the suite had gone 61 -> 77 files while the report still said 61, the
comparison stayed green the whole way (77 >= 61), and a reader doing the
percentage got a number that was wrong by a third.  A published number nobody can
falsify is not evidence.

So the historical values are now **pinned here as constants, with the commit and
the date they were measured at**, and they are *re-derived from that commit* on
every run: ``git ls-tree``/``git cat-file`` read the ``tests/`` tree of
``5cc0eda`` and count it again with the same AST walk used for today's tree.  If
the pin and the commit disagree, the pin was wrong and this tool exits nonzero.
If git cannot answer, this tool exits nonzero as well - a historical claim in a
checkout that cannot see its own history is unverifiable, and the honest report
of an unverifiable claim is red, not green.

The live suite size still ships, under ``tests_total_files_today`` /
``tests_total_functions_today``.  It is deliberately NOT in the report's
``AUDIT_COUNTS`` block: a number that changes whenever anyone adds a test does
not belong in a document that is not re-published when they do.

Report-only / additive: this tool reads files, writes nothing, opens no socket,
touches no database, and imports nothing from ``src/``.

Usage:
    py -3 tools/pf_multiplayer_readiness_audit.py            # human table
    py -3 tools/pf_multiplayer_readiness_audit.py --json     # machine output
Exit 0 = every pinned site and frame anchor reproduced; nonzero = drift.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(_HERE, ".."))

# ---------------------------------------------------------------------------
# 0. The historical pin (see the "TWO KINDS OF NUMBER" section of the docstring)
# ---------------------------------------------------------------------------
#: The commit the report's suite-size numbers describe, and the day it was cut.
#: These two strings are the whole reason the numbers below can be checked at
#: all: without them "61 test files" is a claim about no particular tree.
HEAD_COMMIT = "5cc0eda"
HEAD_MEASURED_AT = "2026-08-18"

#: What the suite looked like at HEAD_COMMIT.  Re-derived from that commit on
#: every run by ``_counts_at_head()``; a disagreement is a failure, not a
#: refresh.  Never edit these to make something green - if they are wrong, the
#: report they back is wrong and needs an erratum.
AT_HEAD = {
    "tests_total_files_at_head": 61,
    "tests_total_functions_at_head": 663,
    "package_a_closure_test_files_at_head": 29,
    "package_a_closure_test_functions_at_head": 351,
    "package_b_closure_test_files_at_head": 27,
    "package_b_closure_test_functions_at_head": 320,
}


class HistoryUnavailable(Exception):
    """git could not answer a question about ``HEAD_COMMIT``."""

V141 = "current/pf_login_game_server_v141.py"
CONNECTION = "src/pirateforce_foundation/connection.py"
SHUTDOWN = "src/pirateforce_foundation/shutdown.py"
STORE = "src/pirateforce_foundation/store.py"
SESSION = "src/pirateforce_foundation/session.py"
RUNTIME = "src/pirateforce_foundation/runtime.py"
APP = "src/pirateforce_foundation/app.py"
LIFECYCLE = "src/pirateforce_foundation/lifecycle.py"
POPULATION = "src/pirateforce_foundation/population.py"
POPULATION_SCENARIO = "src/pirateforce_foundation/population_scenario.py"
SCENE_OBJECT = "src/pirateforce_foundation/scene_object.py"
SCENE_LOAD = "src/pirateforce_foundation/scene_load.py"
RUNTIME_CONSOLE = "src/pirateforce_foundation/runtime_console.py"
INVENTORY = "src/pirateforce_foundation/inventory.py"
MIG_001 = "migrations/001_initial.sql"
MIG_002 = "migrations/002_character_integrity.sql"

# The one file project policy declares immutable.  Sites inside it are the
# reason [A] is a replacement rather than an edit.
IMMUTABLE_PATHS = frozenset({V141})


# ---------------------------------------------------------------------------
# 1. Single-player assumption sites
# ---------------------------------------------------------------------------
# (id, layer, path, regex, expected occurrences, one-line meaning)
ASSUMPTION_SITES = (
    # --- transport: one connection is served at a time -------------------
    ("T01", "transport", V141, r"s\.listen\(4\)", 2,
     "both listeners take a backlog of 4 and nothing services it in parallel"),
    ("T02", "transport", V141, r"c, a = s\.accept\(\)", 1,
     "GAME accept is followed by the whole connection handled inline in the same loop"),
    ("T03", "transport", V141, r"while not stop\.is_set\(\):", 1,
     "the GAME loop advances to the next accept only after the current connection ends"),
    ("T04", "transport", V141, r"c\.settimeout\(600\)", 2,
     "one stalled client holds its listener for up to 600 s before the next accept"),
    ("T05", "transport", V141, r"c, addr = s\.accept\(\)", 1,
     "LOGIN accept is likewise followed by inline handling in the same loop"),
    ("T06", "transport", V141,
     r"if parsed\.nested_id == LOGIN_REQ and not sent_login:", 1,
     "LOGIN per-connection flags live in the loop body, not in a per-connection object"),
    ("T07", "transport", V141, r"target=game_listener", 1,
     "exactly one GAME listener thread is ever started"),
    ("T08", "transport", CONNECTION, r"self\._local = threading\.local\(\)", 1,
     "the accepted-connection binding is thread-affine, so accept and state "
     "construction must happen on the same thread"),
    ("T09", "transport", CONNECTION,
     r'raise RuntimeError\("GAME connection already pending on listener thread"\)', 1,
     "a second accept before the first is released is a hard error, by construction"),
    ("T10", "transport", CONNECTION,
     r'raise RuntimeError\("GAME connection/state correlation mismatch"\)', 1,
     "release only accepts the single pending connection of the calling thread"),
    ("T11", "transport", CONNECTION, r"def abort_pending", 1,
     "listener teardown can abort at most one pending connection"),
    ("T12", "transport", SHUTDOWN,
     r'raise RuntimeError\("unexpected frozen GAME thread construction"\)', 1,
     "the managed threading seam refuses any Thread that is not the frozen "
     "4-argument GAME listener, so no per-connection worker can be created through it"),

    # --- identity: one account per process -------------------------------
    ("I01", "identity", V141, r'ap\.add_argument\("--token", default="localtest"\)', 1,
     "the account identity is a server-side CLI argument, not a client credential"),
    ("I02", "identity", V141, r"state = GameSessionState\(token\)", 1,
     "every accepted GAME connection is constructed with that same process-wide token"),
    ("I03", "identity", V141, r"login_pc, login_frame = make_login_res\(\)", 1,
     "one LOGIN response is built before the accept loop and replayed to every client"),
    ("I04", "identity", V141, r"^def parse_login", 0,
     "no parser for LSCN_LoginVitalReq (0x42BF) exists, so the account name the "
     "client puts on the wire is never read"),
    ("I05", "identity", SESSION,
     r"self\.account_id, self\.session_id, self\.characters = lifecycle\.login\(login_name\)", 1,
     "the Foundation session resolves its account from that token string"),
    ("I06", "identity", STORE,
     r'"UPDATE sessions SET closed_at=\? WHERE account_id=\? AND closed_at IS NULL",', 1,
     "open_session closes every open lease of the same account before inserting the new one"),
    ("I07", "identity", STORE, r"def expire_open_sessions", 1,
     "process start closes every open lease of every account, not just its own"),

    # --- world: population and outbound are shaped for one observer -------
    ("W01", "world", POPULATION, r"def build_port_royal_membership_transition", 1,
     "scene membership is a pure function of ONE player's XYZ"),
    ("W02", "world", POPULATION, r"def build_port_royal_initial_population", 1,
     "the initial generation is likewise a function of ONE player's XYZ"),
    ("W03", "world", POPULATION, r"NPC_STYLE_ACTOR_TYPE = 4", 1,
     "the only actor type the server can put in an actor entry is 4"),
    ("W04", "world", POPULATION_SCENARIO, r'"remote_player"', 1,
     "the population profile lists remote_player as an explicit nonclaim"),
    ("W05", "world", SCENE_OBJECT, r"make_remote_actor_entry\(4,", 1,
     "the scene-object lane also emits actor type 4 only"),
    ("W06", "world", SCENE_OBJECT, r"if profile_key not in \{", 1,
     "the remote-actor serializer allowlists two hardcoded profiles and refuses the rest"),
    ("W07", "world", SCENE_LOAD, r'entry\["required_character_name"\] != "Arena01"', 1,
     "the scene-load lane is pinned to one named character"),
    ("W08", "world", V141, r"actions = state\.dispatch\(parsed\)", 1,
     "outbound frames exist only as a return value of the requesting connection's dispatch"),
    ("W09", "world", V141, r"c\.sendall\(out_frame\)", 1,
     "the only outbound socket is the requesting connection's own -- there is no push channel"),
    ("W10", "world", V141, r"with send_lock:", 2,
     "the per-connection write lock is created inside the frozen listener body, so "
     "any writer outside it would race the heartbeat"),

    # --- capture / logging: one lane per process --------------------------
    ("L01", "capture", V141, r'live_path = capdir / "GAME_LIVE\.txt"', 1,
     "one shared live log per listener, appended by every connection"),
    ("L02", "capture", V141, r'event_path = capdir / "GAME_EVENTS_LIVE\.txt"', 1,
     "one shared event log per listener, likewise"),
    ("L03", "capture", V141, r'live\(f"HEARTBEAT seq=\{seq\}', 1,
     "live lines after SESSION_START carry no connection discriminator"),
    ("L04", "capture", V141, r'capdir = pathlib\.Path\("capture_v141"\)', 1,
     "the capture directory is resolved relative to the process CWD"),
    ("L05", "capture", APP, r"os\.chdir\(capture_root\)", 1,
     "the server chdirs the whole process into one capture root"),
    ("L06", "capture", RUNTIME_CONSOLE, r"sys\.stdout = _Mirror", 1,
     "stdout/stderr are swapped process-wide for one mirrored console"),

    # --- interlock: why a half-done fix is worse than none ----------------
    ("X01", "interlock", RUNTIME, r"self\.foundation\.checkpoint\(candidate\)", 1,
     "the position checkpoint is the one database write reached from dispatch"),
    ("X02", "interlock", RUNTIME, r"self\._checkpoint_exact_target\(", 2,
     "both checkpoint call sites sit at try-depth 0 inside dispatch (see X06)"),
    ("X03", "interlock", STORE,
     r'raise PermissionError\("stale or non-owning character session"\)', 2,
     "a stale lease raises out of the store rather than returning a status"),
    ("X04", "interlock", SHUTDOWN, r'controller\.request_stop\("server thread failure"\)', 1,
     "an exception escaping the listener stops the entire server"),
    ("X05", "interlock", STORE,
     r"SELECT COALESCE\(MAX\(lease_generation\),0\)\+1 FROM sessions WHERE account_id=\?", 1,
     "lease_generation is monotonic per account, so a takeover is silent to the old holder"),
)


# ---------------------------------------------------------------------------
# 2. Already-ready sites (question 2 of the audit)
# ---------------------------------------------------------------------------
READY_SITES = (
    ("R01", "schema", MIG_001,
     r"CREATE TABLE sessions \(id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts\(id\)", 1,
     "sessions is a row-per-lease table keyed by a UUID with an account foreign key"),
    ("R02", "schema", MIG_002,
     r"CREATE UNIQUE INDEX sessions_one_active_character ON sessions\(selected_character_id\) WHERE closed_at IS NULL", 1,
     "the uniqueness the schema enforces is one live session per CHARACTER, not per server"),
    ("R03", "persistence", STORE, r"def _require_selected_session", 1,
     "every backpack read and write is gated on (session_id, character_id) ownership"),
    ("R04", "persistence", STORE,
     r"EXISTS \(SELECT 1 FROM sessions WHERE id=\? AND selected_character_id=\? AND closed_at IS NULL\)", 1,
     "position writes are gated on the same open-session ownership predicate"),
    ("R05", "persistence", STORE, r"def soft_delete_character", 1,
     "delete is session-scoped and refuses a character selected by any open session"),
    ("R06", "persistence", STORE, r"def create_character", 1,
     "selector allocation is scoped to one account"),
    ("R07", "persistence", LIFECYCLE,
     r"lo = 0x10000000 \+ account_id \* 0x10000 \+ selector \+ 1", 1,
     "the character identity space is already partitioned by account (65536 x 256)"),
    ("R08", "persistence", STORE, r'db\.execute\("PRAGMA busy_timeout=5000"\)', 1,
     "the store already configures a busy timeout for contended writers"),
    ("R09", "persistence", STORE, r'db\.execute\("PRAGMA journal_mode=WAL"\)', 1,
     "the store already runs in WAL, which permits concurrent readers with a writer"),
    ("R10", "session", SESSION, r"class FoundationSession", 1,
     "all lifecycle state is instance state on one per-connection object"),
    ("R11", "transport", SHUTDOWN, r"self\._accepted: set\[ManagedSocket\] = set\(\)", 1,
     "the shutdown controller already tracks accepted sockets as a SET"),
    ("R12", "transport", SHUTDOWN, r"def register_accepted", 1,
     "and already registers every accepted socket individually"),
    ("R13", "transport", CONNECTION, r"def make_transport_socket_closer", 1,
     "there is already a precedent for handing one connection's raw socket to its state"),
    ("R14", "wire", V141, r"def make_remote_actor_entry\(actor_type: int, actor_identity: int,", 1,
     "the actor-entry serializer already takes an arbitrary actor type and attr list"),
    ("R15", "wire", V141, r"def make_runtime_remote_actors\(entries: list\[bytes\]\)", 1,
     "the actor-stream envelope already takes an arbitrary list of entries (u16 count)"),
    ("R16", "wire", V141, r"def make_select_res\(status: int, game_port: int", 1,
     "the LOGIN handshake already hands each client a game port as a response field"),
    ("R17", "correction", INVENTORY, r"_require_selected_session", 0,
     "CORRECTION: the session-ownership guard is NOT in inventory.py; it is store.py"),
)


# ---------------------------------------------------------------------------
# 3. Frame anchors for a second visible player
# ---------------------------------------------------------------------------
# (id, name, wire id, status, evidence path that must exist, note)
ANCHORED = "anchored"
PARTIAL = "partial"
GUESS = "guess"

FRAMES = (
    ("F1", "GSCN_RunTimeProtocolRes remote-actor stream", "0x6E9D", ANCHORED,
     "reports/PF_OBJECT_POP002_AUTHORITATIVE_SCENE_ACTOR_RUNTIME_PASS_20260816.md",
     "serializer chain 0x5F4070 -> 0x5E3EE0 -> 0x5E1C10/0x5E01D0 documented in v141; runtime_pass"),
    ("F2", "remote-actor entry container", "-", ANCHORED,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "client serializer 0x5E21D0: u8 actor type, qword identity, u8 attr count, per-attr u16 id"),
    ("F3", "MovementAttr", "0x2067", ANCHORED,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "Serial 0x4671C0, apply/merge 0x467130, delta 0x467040, direction-agnostic codec 0x89A600"),
    ("F4", "NPCAttr (+BasicAttr)", "0x0AD5", ANCHORED,
     "reports/PF_OBJECT_POP002_AUTHORITATIVE_SCENE_ACTOR_RUNTIME_PASS_20260816.md",
     "serializer 0x466EB0 / BasicAttr 0x4656F0 / name -> 0x51F920 / preset -> 0x45DAE0 -> 0x78AA50"),
    ("F5", "Channel_LocalTalkMessageVital", "0xAC52", ANCHORED,
     "reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md",
     "shared serializer 0x65AD40 both directions, dispatcher 0x659870 renders LocalTalk"),
    ("F6", "actor removal by omission from the next generation", "-", ANCHORED,
     "reports/PF_OBJECT_POP002_AUTHORITATIVE_SCENE_ACTOR_RUNTIME_PASS_20260816.md",
     "retained/entrant/omitted semantics are runtime-proven for NPC-style actors"),
    ("F7", "DeleteActorVital", "0x36DB", ANCHORED,
     "reports/PF_DELETE_SOFT002_NATURAL_0x36DB_DECODE_20260818.md",
     "decoded, but it is a character-select-stage delete, NOT a scene despawn"),

    ("F8", "ActorAttr", "0x12AD", PARTIAL,
     "reports/PF_STATS_PROG001_CHARACTER_STATS_AND_PROGRESSION_STATIC_20260818.md",
     "anchored on the local-player StartGame path only; never seen inside a remote actor entry"),
    ("F9", "AvatarAttr", "0x16A0", PARTIAL,
     "reports/PF_CHARACTER_NAME001_PLAYER_NAME_PROJECTION_STATIC_IMPLEMENTATION_20260816.md",
     "serializer 0x464560 known and the bytes are persisted opaquely; no field-level model exists"),

    ("G1", "actor_type value for a human player", "-", GUESS,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "only actor_type 4 (CNetNPC) has ever been emitted or proven; the client's "
     "actor_type -> class dispatch is not characterized anywhere -- STATICALLY ANSWERABLE"),
    ("G2", "attr composition of a remote human-player entry", "-", GUESS,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "which attrs, in what order, with which masks -- no capture and no static enumeration"),
    ("G3", "interest management (who sees whom)", "-", GUESS,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "the coverage row calls this entirely unknown"),
    ("G4", "server -> client remote update cadence", "-", GUESS,
     "reports/PF_MOVE_CADENCE001_CHECKPOINT_CADENCE_PER_WALK_HEADLESS_20260818.md",
     "MOVE-CADENCE-001 measured the client's own TargetPos cadence, not a remote push rate"),
    ("G5", "client-side interpolation between projections", "-", GUESS,
     "reports/PF_MOVE_PROJECT001_REMOTE_MOVEMENT_PROJECTION_STATIC_20260818.md",
     "uncaptured"),
    ("G6", "server-originated chat to a third party + what the client renders", "-", GUESS,
     "reports/PF_CHAT_CHANNEL002_SHARED_SERIALIZER_EMITTER_20260818.md",
     "the encoder exists; whether the protocol permitted it and what renders is GT-016"),
    ("G7", "Whisper/Party/Guild membership and routing authority", "-", GUESS,
     "reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_STATIC_20260818.md",
     "explicitly not claimed; needs two concurrent sessions"),
    ("G8", "LSCN_LoginVitalReq account/credential field roles", "0x42BF", GUESS,
     "reports/PF_GT006_UNATTENDED_SCHEDULED_ATTEMPT_OPERATIONAL_NEGATIVE_20260817.md",
     "the bytes exist in archived captures but every archived capture carries the same "
     "value 'test' -- DECODABLE WITH ONE ATTENDED RUN"),
    ("G9", "PvP damage between players", "-", GUESS,
     "reports/PF_SCENE013_STRUCTURAL_COMBAT_CORPUS_CAPABILITY_NEGATIVE_20260816.md",
     "damage_and_hit_result is blocked on a corpus negative; pvp_engagement is not_started"),
)

# The exact nested LSCN_LoginVitalReq record every archived LOGIN capture carries.
# Optional guard: skipped when the capture is absent (it is untracked evidence).
LOGIN_REQ_CAPTURE = (
    "analysis/lost_eden_leisure_runtime/capture_v110/"
    "LOGIN_20260814_152723_188831_59376.txt"
)
LOGIN_REQ_NESTED_HEX = (
    "bf420b004804000000" "0e000000" "440400000074657374"
)


# ---------------------------------------------------------------------------
# 4. Work packages [A] transport/session and [B] world/visibility
# ---------------------------------------------------------------------------
PACKAGE_A_FILES = (
    (CONNECTION, "modify", ("T08", "T09", "T10", "T11")),
    (SHUTDOWN, "modify", ("T12", "X04")),
    (STORE, "modify", ("I06", "I07", "X03", "X05")),
    (SESSION, "modify", ("I05",)),
    (RUNTIME, "modify", ("X01", "X02")),
    (APP, "modify", ("L05",)),
    ("src/pirateforce_foundation/<new concurrent listener>.py", "new",
     ("T01", "T02", "T03", "T04", "T05", "T06", "T07",
      "I01", "I02", "I03", "I04", "L01", "L02", "L03", "L04", "W08", "W09", "W10")),
)

PACKAGE_B_FILES = (
    ("src/pirateforce_foundation/<new remote player projection>.py", "new",
     ("W03", "W04", "W05")),
    ("scenarios/<new opt-in profile>.json", "new", ()),
    (RUNTIME, "modify", ("W01", "W02")),
    (APP, "modify", ()),
    (CONNECTION, "modify", ("W10",)),
)

# Test files whose assertions are ABOUT the behaviour each package changes.
# These are the ones that must be re-proven rather than merely re-run.
IMPACT_A_PINNED = (
    "tests/test_single_session_limitation.py",
    "tests/test_session_row_persistence.py",
    "tests/test_startup_stale_lease_recovery.py",
    "tests/test_connection_lifecycle.py",
    "tests/test_server_shutdown.py",
    "tests/test_runtime_console.py",
    "tests/test_foundation_legacy_seam.py",
)
IMPACT_B_PINNED = (
    "tests/test_population.py",
    "tests/test_population_adapter.py",
    "tests/test_scene_object.py",
    "tests/test_npc_gait_wire.py",
    "tests/test_remote_movement_projection_static.py",
    "tests/test_scene_load.py",
)

# Foundation modules each package edits, used for the broad import closure.
CLOSURE_A_MODULES = ("connection", "shutdown", "store", "session", "runtime", "app")
CLOSURE_B_MODULES = (
    "population", "population_scenario", "scene_object", "scene_load",
    "runtime", "connection",
)


# ---------------------------------------------------------------------------
# machinery
# ---------------------------------------------------------------------------
_failures: list[str] = []


def _fail(message: str) -> None:
    _failures.append(message)


def _read(relpath: str) -> str:
    with open(os.path.join(ROOT, relpath), "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _locate(relpath: str, pattern: str) -> list[int]:
    compiled = re.compile(pattern)
    return [
        number
        for number, line in enumerate(_read(relpath).splitlines(), start=1)
        if compiled.search(line)
    ]


def _scan(sites, label):
    rows = []
    for site_id, layer, path, pattern, expect, note in sites:
        try:
            lines = _locate(path, pattern)
        except OSError as error:
            _fail(f"{label} {site_id}: cannot read {path}: {error!r}")
            lines = []
        if len(lines) != expect:
            _fail(
                f"{label} {site_id}: {path} expected {expect} occurrence(s) of "
                f"{pattern!r}, found {len(lines)} at {lines}"
            )
        rows.append({
            "id": site_id,
            "layer": layer,
            "path": path,
            "expect": expect,
            "found": len(lines),
            "lines": lines,
            "immutable": path in IMMUTABLE_PATHS,
            "note": note,
        })
    return rows


def _checkpoint_try_depth() -> list[tuple[int, int]]:
    """Return (line, enclosing try depth) for every checkpoint call in runtime.py."""
    tree = ast.parse(_read(RUNTIME))
    found: list[tuple[int, int]] = []

    class Walk(ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0

        def visit_Try(self, node: ast.Try) -> None:  # noqa: N802
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            text = ast.unparse(node)
            if "_checkpoint_exact_target" in text or "foundation.checkpoint" in text:
                found.append((node.lineno, self.depth))
            self.generic_visit(node)

    Walk().visit(tree)
    return found


def _game_listener_handlers() -> list[tuple[int, int]]:
    """Return (try line, number of except handlers) for the frozen GAME listener."""
    tree = ast.parse(_read(V141))
    out: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "game_listener":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Try):
                    out.append((inner.lineno, len(inner.handlers)))
    return sorted(out)


# The two counters below take TEXT, not a path, so that the same definition of
# "a test function" and "a foundation import" is applied to today's working tree
# and to the blobs read out of HEAD_COMMIT.  Two counters would mean the
# historical re-derivation could agree with the pin for the wrong reason.
def _count_test_functions(text: str) -> int:
    tree = ast.parse(text)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test")
    )


def _count_foundation_imports(text: str) -> set[str]:
    modules: set[str] = set()
    modules.update(re.findall(r"from\s+pirateforce_foundation\.([A-Za-z_0-9]+)\s+import", text))
    modules.update(re.findall(r"import\s+pirateforce_foundation\.([A-Za-z_0-9]+)", text))
    return modules


def _test_functions(relpath: str) -> int:
    return _count_test_functions(_read(relpath))


def _test_files() -> list[str]:
    directory = os.path.join(ROOT, "tests")
    return sorted(
        "tests/" + name
        for name in os.listdir(directory)
        if name.endswith(".py")
    )


def _foundation_imports(relpath: str) -> set[str]:
    return _count_foundation_imports(_read(relpath))


def _closure(modules) -> dict:
    wanted = set(modules)
    files = [path for path in _test_files() if _foundation_imports(path) & wanted]
    return {
        "files": len(files),
        "functions": sum(_test_functions(path) for path in files),
        "names": files,
    }


# ---------------------------------------------------------------------------
# the historical re-derivation
# ---------------------------------------------------------------------------
def _git(args: list[str], stdin: bytes = b"") -> bytes:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks"] + args,
            cwd=ROOT, input=stdin, capture_output=True,
        )
    except OSError as error:
        raise HistoryUnavailable("git is not runnable: %r" % (error,)) from None
    if completed.returncode != 0:
        raise HistoryUnavailable(
            "git %s failed (%d): %s"
            % (" ".join(args), completed.returncode,
               completed.stderr.decode("utf-8", "replace").strip()))
    return completed.stdout


def _tests_tree_at(commit: str) -> dict[str, str]:
    """``{path: blob source}`` for every ``tests/*.py`` at ``commit``.

    One ``ls-tree`` plus one batched ``cat-file`` - not 61 subprocesses.
    """
    listing = _git(["ls-tree", commit, "tests/"]).decode("utf-8", "replace")
    blobs: dict[str, str] = {}
    for line in listing.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) != 3 or parts[1] != "blob" or not path.endswith(".py"):
            continue
        blobs[path] = parts[2]
    if not blobs:
        raise HistoryUnavailable(
            "commit %s has no tests/*.py - is that really the commit the report "
            "was measured at?" % commit)

    payload = ("\n".join(blobs.values()) + "\n").encode("ascii")
    stream = _git(["cat-file", "--batch"], stdin=payload)
    sources: dict[str, str] = {}
    offset = 0
    for path, sha in blobs.items():
        newline = stream.index(b"\n", offset)
        header = stream[offset:newline].decode("ascii").split()
        if len(header) != 3 or header[1] != "blob":
            raise HistoryUnavailable(
                "unexpected cat-file header for %s: %r" % (path, header))
        size = int(header[2])
        body = stream[newline + 1:newline + 1 + size]
        sources[path] = body.decode("utf-8", "replace")
        offset = newline + 1 + size + 1  # trailing newline after each object
    return sources


_RECOUNT_CACHE: dict[str, dict] = {}


def _counts_at_head(commit: str) -> dict:
    """Re-count the pinned commit's ``tests/`` tree with today's definitions."""
    if commit in _RECOUNT_CACHE:
        return dict(_RECOUNT_CACHE[commit])
    sources = _tests_tree_at(commit)
    names = sorted(sources)

    def closure(modules):
        wanted = set(modules)
        files = [n for n in names if _count_foundation_imports(sources[n]) & wanted]
        return len(files), sum(_count_test_functions(sources[n]) for n in files)

    files_a, functions_a = closure(CLOSURE_A_MODULES)
    files_b, functions_b = closure(CLOSURE_B_MODULES)
    _RECOUNT_CACHE[commit] = {
        "tests_total_files_at_head": len(names),
        "tests_total_functions_at_head":
            sum(_count_test_functions(sources[n]) for n in names),
        "package_a_closure_test_files_at_head": files_a,
        "package_a_closure_test_functions_at_head": functions_a,
        "package_b_closure_test_files_at_head": files_b,
        "package_b_closure_test_functions_at_head": functions_b,
    }
    return dict(_RECOUNT_CACHE[commit])


def _pinned_impact(paths) -> dict:
    total = 0
    per_file = {}
    for path in paths:
        if not os.path.isfile(os.path.join(ROOT, path)):
            _fail(f"impact set: {path} does not exist")
            continue
        count = _test_functions(path)
        per_file[path] = count
        total += count
    return {"files": len(per_file), "functions": total, "per_file": per_file}


def _login_capture_guard() -> str:
    path = os.path.join(ROOT, LOGIN_REQ_CAPTURE)
    if not os.path.isfile(path):
        return "skipped (untracked capture absent)"
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    match = re.search(r"DECOMPRESSED \d+\n((?:[0-9A-F]{8}  .*\n)+)", text)
    if match is None:
        _fail("login capture guard: no DECOMPRESSED block found")
        return "unreadable"
    payload = "".join(
        re.findall(r"^[0-9A-F]{8}  ((?:[0-9A-F]{2} ?)+)", match.group(1), re.M)
    ).replace(" ", "")
    raw = bytes.fromhex(payload)
    start = raw.find(b"\xbf\x42")
    if start < 0:
        _fail("login capture guard: nested LoginVitalReq id 0x42BF not present")
        return "missing id"
    nested = raw[start:].hex()
    if nested != LOGIN_REQ_NESTED_HEX:
        _fail(
            "login capture guard: nested record drifted, "
            f"expected {LOGIN_REQ_NESTED_HEX} got {nested}"
        )
        return "drifted"
    return "reproduced"


def build() -> dict:
    assumptions = _scan(ASSUMPTION_SITES, "assumption")
    ready = _scan(READY_SITES, "ready")

    depths = _checkpoint_try_depth()
    unguarded = [line for line, depth in depths if depth == 0]
    if len(unguarded) != len(depths) or not depths:
        _fail(
            "interlock X06: expected every runtime.py checkpoint call to sit at "
            f"try-depth 0, got {depths}"
        )

    handlers = _game_listener_handlers()
    bare_finally = [line for line, count in handlers if count == 0]
    if len(bare_finally) != 1:
        _fail(
            "interlock X07: expected exactly one try/finally with zero except "
            f"handlers in the frozen game_listener, got {handlers}"
        )

    by_layer: dict[str, int] = {}
    for row in assumptions:
        by_layer[row["layer"]] = by_layer.get(row["layer"], 0) + 1
    immutable = sum(1 for row in assumptions if row["immutable"])

    per_path: dict[str, int] = {}
    for row in assumptions:
        per_path[row["path"]] = per_path.get(row["path"], 0) + 1

    frames_by_status: dict[str, int] = {ANCHORED: 0, PARTIAL: 0, GUESS: 0}
    for _fid, _name, _wire, status, evidence, _note in FRAMES:
        frames_by_status[status] = frames_by_status.get(status, 0) + 1
        if not os.path.isfile(os.path.join(ROOT, evidence)):
            _fail(f"frame evidence missing: {evidence}")

    package_a_new = sum(1 for _p, kind, _s in PACKAGE_A_FILES if kind == "new")
    package_b_new = sum(1 for _p, kind, _s in PACKAGE_B_FILES if kind == "new")

    # The historical half.  A mismatch here means the report's published
    # suite-size numbers never described HEAD_COMMIT, which is a fact about the
    # report and not something to be fixed by editing the pin.
    try:
        recount = _counts_at_head(HEAD_COMMIT)
    except HistoryUnavailable as error:
        recount = None
        _fail(
            "historical pin: cannot re-derive the suite size at %s, so the "
            "report's *_at_head numbers are unverifiable here (%s)"
            % (HEAD_COMMIT, error))
    else:
        for key, pinned in sorted(AT_HEAD.items()):
            if recount[key] != pinned:
                _fail(
                    "historical pin: %s is pinned at %d but commit %s actually "
                    "has %d - the published number is wrong and needs an "
                    "erratum, not a re-pin"
                    % (key, pinned, HEAD_COMMIT, recount[key]))

    all_files = _test_files()
    return {
        "revision_note": "site counts are re-derived live; the *_at_head numbers "
                         "are historical and re-derived from commit " + HEAD_COMMIT,
        "measured_at_head_commit": HEAD_COMMIT,
        "measured_at_head_date": HEAD_MEASURED_AT,
        "historical_pin": ("reproduced from " + HEAD_COMMIT) if recount is not None
                          else "UNVERIFIABLE (git could not answer)",
        **AT_HEAD,
        "assumption_sites_total": len(assumptions),
        "assumption_sites_by_layer": by_layer,
        "assumption_sites_immutable": immutable,
        "assumption_sites_mutable": len(assumptions) - immutable,
        "assumption_sites_per_path": per_path,
        "ready_sites_total": len(ready),
        "checkpoint_calls_at_try_depth_zero": len(unguarded),
        "game_listener_try_blocks_without_except": len(bare_finally),
        "login_req_capture_guard": _login_capture_guard(),
        "frames_total": len(FRAMES),
        "frames_anchored": frames_by_status[ANCHORED],
        "frames_partial": frames_by_status[PARTIAL],
        "frames_guess": frames_by_status[GUESS],
        "package_a_files_touched": len(PACKAGE_A_FILES),
        "package_a_files_new": package_a_new,
        "package_a_sites_covered": sum(len(s) for _p, _k, s in PACKAGE_A_FILES),
        "package_b_files_touched": len(PACKAGE_B_FILES),
        "package_b_files_new": package_b_new,
        "package_b_sites_covered": sum(len(s) for _p, _k, s in PACKAGE_B_FILES),
        "impact_a_pinned": _pinned_impact(IMPACT_A_PINNED),
        "impact_b_pinned": _pinned_impact(IMPACT_B_PINNED),
        "impact_a_closure": _closure(CLOSURE_A_MODULES),
        "impact_b_closure": _closure(CLOSURE_B_MODULES),
        # Live suite size.  Named "_today" so that nobody can mistake it for the
        # historical figure the report publishes, which is what happened before.
        "tests_total_files_today": len(all_files),
        "tests_total_functions_today": sum(_test_functions(path) for path in all_files),
        "_rows": {"assumptions": assumptions, "ready": ready},
    }


def _print_table(result: dict) -> None:
    print("PF MULTIPLAYER-READINESS-AUDIT-001 -- source scan")
    print("=" * 78)
    print()
    print("1. SINGLE-PLAYER ASSUMPTION SITES")
    print("-" * 78)
    for row in result["_rows"]["assumptions"]:
        flag = "IMMUTABLE" if row["immutable"] else "         "
        where = ",".join(str(line) for line in row["lines"]) or "-"
        print(f"  {row['id']}  {flag}  {row['path']}:{where}")
        print(f"          {row['note']}")
    print()
    print(f"  total = {result['assumption_sites_total']}"
          f"  (immutable {result['assumption_sites_immutable']}"
          f" / mutable {result['assumption_sites_mutable']})")
    for layer, count in sorted(result["assumption_sites_by_layer"].items()):
        print(f"    {layer:10s} {count}")
    print()
    print("2. ALREADY-READY SITES")
    print("-" * 78)
    for row in result["_rows"]["ready"]:
        where = ",".join(str(line) for line in row["lines"]) or "(absent, as expected)"
        print(f"  {row['id']}  {row['path']}:{where}")
        print(f"          {row['note']}")
    print()
    print(f"  total = {result['ready_sites_total']}")
    print()
    print("3. FRAME ANCHORS FOR A SECOND VISIBLE PLAYER")
    print("-" * 78)
    for fid, name, wire, status, _evidence, note in FRAMES:
        print(f"  {fid:3s} {status.upper():9s} {wire:7s} {name}")
        print(f"          {note}")
    print()
    print(f"  anchored={result['frames_anchored']} "
          f"partial={result['frames_partial']} guess={result['frames_guess']} "
          f"total={result['frames_total']}")
    print()
    print("4. WORK PACKAGES")
    print("-" * 78)
    for label, package, impact_key, closure_key in (
        ("[A] transport/session", PACKAGE_A_FILES, "impact_a_pinned", "impact_a_closure"),
        ("[B] world/visibility", PACKAGE_B_FILES, "impact_b_pinned", "impact_b_closure"),
    ):
        print(f"  {label}")
        for path, kind, sites in package:
            print(f"    {kind:6s} {path}  sites={len(sites)} {list(sites)}")
        pinned = result[impact_key]
        closure = result[closure_key]
        print(f"    pinned impact : {pinned['files']} files / {pinned['functions']} test functions")
        print(f"    import closure: {closure['files']} files / {closure['functions']} test functions")
        print()
    print(f"  suite today   : {result['tests_total_files_today']} files / "
          f"{result['tests_total_functions_today']} test functions")
    print(f"  suite at {result['measured_at_head_commit']} "
          f"({result['measured_at_head_date']}, the figure the report publishes): "
          f"{result['tests_total_files_at_head']} files / "
          f"{result['tests_total_functions_at_head']} test functions "
          f"[{result['historical_pin']}]")
    print()
    print("5. INTERLOCK")
    print("-" * 78)
    print(f"  runtime.py checkpoint calls at try-depth 0 : "
          f"{result['checkpoint_calls_at_try_depth_zero']}")
    print(f"  frozen game_listener try blocks with 0 except handlers: "
          f"{result['game_listener_try_blocks_without_except']}")
    print(f"  archived LSCN_LoginVitalReq nested record  : "
          f"{result['login_req_capture_guard']}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable counts")
    args = parser.parse_args()

    result = build()
    if args.json:
        payload = {key: value for key, value in result.items() if not key.startswith("_")}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        _print_table(result)

    if _failures:
        print(f"RESULT: {len(_failures)} guard(s) drifted:", file=sys.stderr)
        for failure in _failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    if not args.json:
        print("RESULT: all multiplayer-readiness audit guards reproduced (exit 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
