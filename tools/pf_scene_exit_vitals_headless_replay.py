#!/usr/bin/env python3
"""SCENE-EXIT-VITALS: prove the scene-edge restate seam fires, headless.

WHAT THIS EXISTS FOR.  `GT-301` (LANE-DB) cannot enter an attended snapshot
without a `HEADLESS_PROOF:` line -- a console token, measured on the current
`main`, showing that the mechanism the ticket wants tested is armed in the
target scene rather than merely present in the tree.  The seam this drives
landed for `CORE-REQUEST` `pf_bridge/notes_to_chief/20260907_2032`.

WHAT IS REAL HERE AND WHAT IS A STAND-IN, stated first because a proof that
blurs the two is worth nothing:

  REAL   the login / create / start-game boot, through `state.dispatch` and
         the pinned v141 parser, on a throwaway SQLite database built by
         this repository's own `migrations/`.
  REAL   both position reports: authentic `TargetPosVital` frames, decoded
         by `parse_outer`, taking the same `position_report` branch a client
         takes.  The seam is NOT called directly by this script.
  STAND-IN  the scene relabel between the two reports.  In production a GM
         warp (or the travel gate, when it ships unflagged) rewrites
         `selected.position.scene_id`; here `foundation.checkpoint()` writes
         the same field the same way.  What that means for the proof: this
         measures that the seam FIRES on a confirmed scene change and names
         the scene that was LEFT.  It does not measure that any particular
         door produces that change.

  NOT CLAIMED AT ALL: that the client's panel then reads a different number.
  That is the whole of what `GT-301` asks a human to look at, and no headless
  run can answer it.

Read-only discipline: nothing outside a temporary directory is written, and
no canonical database is opened.  Runs on a cloud clone with no capture
corpus and no game client.

Usage:  python3 tools/pf_scene_exit_vitals_headless_replay.py [repo_root]
Exit 0 when the token was printed, 1 when it was not.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 \
    else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_scene_exit_vitals as exitv
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

LOGIN_SCENE = 1                 # the only kind of scene a login may resolve
OCEAN_SCENE = 126               # the scene the owner saw the symptom in


def target_pos_pc(legacy, x, y, z, heading=0.0):
    """An authentic TargetPosVital frame, byte for byte as the tests build
    it (tests/test_arena.py::target_pos_pc)."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + legacy.f32tag(x) + legacy.f32tag(y)
        + legacy.f32tag(z) + legacy.f32tag(heading)
        + legacy.u8tag(0x0B, 1)
        + legacy.u8tag(0x0B, 0)
    )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        store = SQLiteStore(Path(tmp) / "scene_exit.sqlite3",
                            ROOT / "migrations")
        store.migrate()
        # MEASURED WHILE WRITING THIS, and it is why the run makes TWO
        # crossings instead of one: a row parked in scene 126 is refused at
        # login by name (`WORLD_SCENE_ENTRY_REFUSED
        # [scene_not_allowed_at_login]`), so the ocean cannot be where a
        # session starts.  It has to be entered and then left, which is what
        # the owner's own session did.
        default = Position(LOGIN_SCENE, 0, legacy.V135_PLAYER_X,
                           legacy.V135_PLAYER_Y, legacy.V135_PLAYER_Z)
        lifecycle = CharacterLifecycle(
            store, default, legacy.extract_avatar_attr_wire_from_actor)
        state_type = make_state_class(
            legacy, lifecycle, LegacyProjector(legacy), None)
        state = state_type("scene-exit-headless")
        state.dispatch(legacy.parse_outer(legacy._synthetic_client_login_pc()))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = store.list_characters(state.foundation.account_id)[0]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)))

        def relabel(scene_id):
            """STAND-IN: the relabel a door performs in production."""
            here = state.foundation.selected.position
            state.foundation.checkpoint(Position(
                scene_id, here.scene_seq, here.x, here.y, here.z,
                here.heading))

        # REAL frame 1: the client reports from the login scene, so the
        # scene the first crossing names is a CONFIRMED one rather than a
        # label nobody ever stood in.
        state.dispatch(legacy.parse_outer(
            target_pos_pc(legacy, 11.0, 22.0, 33.0)))
        confirmed_before = state.client_confirmed_scene

        # Crossing 1: into the ocean.  The seam names scene 1, the scene left.
        relabel(OCEAN_SCENE)
        state.dispatch(legacy.parse_outer(
            target_pos_pc(legacy, 44.0, 55.0, 66.0)))

        # Crossing 2: OUT of the ocean -- the exit `GT-301` is about.  The
        # seam names scene 126.
        relabel(LOGIN_SCENE)
        state.dispatch(legacy.parse_outer(
            target_pos_pc(legacy, 77.0, 88.0, 99.0)))

    fired = [e for e in state.events if e.startswith("scene_exit_vitals_")]
    print("")
    print("confirmed_scene_before=%s after=%s"
          % (confirmed_before, state.client_confirmed_scene))
    print("seam events: %s" % (fired or "NONE"))
    if not fired:
        print("SCENE_EXIT_VITALS_HEADLESS RED - the seam did not fire on a")
        print("    confirmed scene change.  The token above is the whole")
        print("    proof; without it GT-301 must not be snapshotted.")
        return 1
    if not any(("_%d_to_" % OCEAN_SCENE) in event for event in fired):
        print("SCENE_EXIT_VITALS_HEADLESS RED - the seam fired, but never on")
        print("    the exit from scene %d, which is the one GT-301 is about."
              % OCEAN_SCENE)
        return 1
    print("SCENE_EXIT_VITALS_HEADLESS PASS - grep the lines above for %s;"
          % exitv.SCENE_EXIT_VITALS_CONSOLE_TOKEN)
    print("    printed to stderr by the seam, inside dispatch.  Two of them:")
    print("    scene=%d (entering the ocean) and scene=%d (leaving it) --"
          % (LOGIN_SCENE, OCEAN_SCENE))
    print("    each naming the scene that was LEFT, never the one entered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
