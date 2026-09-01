"""Bridges a parsed GM-003 `warp` command into a real outbound wire frame.

`gm/commands.py` parses `warp <scene_id> [x y]` into a `GmCommand` but does
not execute it -- its own docstring says executing `warp` needs
`TeleportVital`/`ForcePos` wiring. That wiring is now partly possible:
RE-090 (PASS/DONE) pinned `ForcePos`'s byte layout in full, with zero
positional-only/unproven fields (`gm/teleport_wire.py`'s own docstring:
"ForcePos ... carries no presence bit, scene id, sequence, string or
control field"). That completeness is also `ForcePos`'s limit: it has no
scene id field at all, so it can only reposition a connection within the
scene it is already in -- it cannot honor the scene-crossing half of what
`warp <scene_id> x y` reads as. Crossing scenes needs `TeleportVital`,
whose `target`/`aux` sub-objects still carry several positional-only
fields RE-090 leaves unproven (`field_0x10`, `field_0x11`, `field_0x18`,
`field_0x20`, `field_0x22`, and every `TeleportAux` field except `text`).
Inventing values for those here would be exactly the guess this lane's
rules forbid (docs/GM_LANE.md, nonclaim rule) -- so `gm/teleport_wire.py`'s
own parameterized `TeleportVital` builder (`make_teleport_vital_frame`) is
never used here for that reason, and stays unused today.

CROSS-SCENE WARP, RESOLVED A DIFFERENT WAY (COO-DECISION
2026-08-31T14:41+07:00, `pf_bridge/notes_to_chief/20260831_1441_COO-
DECISION-warp-cross-scene-opens-gt106r2-passed.md`).  The positional-field
gap above is real and unchanged -- nobody has proven what `field_0x10`/
`field_0x18`/the `TeleportAux` fields mean, and this module still will not
guess them.  But `legacy.make_login_teleport`
(`current/pf_login_game_server_v141.py:2431`) is a SEPARATE, narrower
encoder that never asks for those fields at all: it hardcodes
`TeleportVital`'s `target` present and `aux` absent, and every
positional-only field to the same constructor-default value the client's
own `TeleportVital` prototype writes (RE-129) -- the identical bytes
`runtime.py` already sends LIVE, mid-session, from three call sites this
lane does not own or write -- NO LINE NUMBERS FOR A FILE THIS LANE DOES NOT
OWN (this module's own docstring convention; `gm/chat_command_action.py`
names why: chief's file rots a pinned number silently, twice in one day the
one round this lane tried it): the Columbus dispatch (`_dispatch_columbus_
quest3021`), the world-travel-gate crossing (`departure.confirmed_fields()`
feeding the same `legacy.make_login_teleport` call, right after `self.
foundation.checkpoint(departure.arrival)`), and the scene-load path (the
`SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE`/`V113_TELEPORT_SCENE1_STABLE_
ZERO_TARGET_ONCE` action labels).  Grep those, not a line number.  RE-162 measured
that mechanism as really wired on main; GT-106-R2 (OBSERVER_CONFIRMED
2026-08-31T10:0x+07:00, `pf_bridge/notes_to_chief/20260831_1036_GT106R2-
RESULT-PASS-*.md`) measured a real client rendering the destination scene
when it fires mid-session rather than only at login (scene 17, X=834
Y=-598, via the Columbus-dispatch call site above -- not through this
lane's `/warp` command, which had never fired it before this round).  So
this module now has a SECOND way to honor `warp <scene_id> x y`'s
cross-scene half that needs no unproven field at all: reuse that exact
encoder, exactly as chief's own call sites already call it, rather than
compose a `TeleportVital` from scratch through `teleport_wire.py`'s general
builder.  See `make_warp_teleport_frame_with_target` and
`WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED` below.

WHAT THIS DOES NOT CLOSE.  The bare `warp <scene_id>` form (no x/y) still
has no position for either composer to carry -- this module does not
invent a spawn point, and `gm/login_scene_stage.py`'s stage-for-next-login
remains the only honest answer for that shape (see
`gm/chat_command_action.py::_warp_action`'s routing rule).  RE-162 also
found that the destination scene's census/actor population does not
follow a mid-session `TeleportVital` -- not even chief's own Columbus
dispatch sends one -- and this module inherits that exact gap rather than
fixing it; fixing it is outside a wire-builder's zone.  And per the G-OBS
rule this lane has held since before this round, every destination beyond
scene 17 still needs its own attended, client-observable pass before this
lane or anyone else calls it PASS -- GT-106-R2 answers the MECHANISM
("does a mid-session TeleportVital move the client's screen at all"), not
every scene id in the catalog.

`pf-adversary` (this round) found that a `GmCommand` handed to this module
is not guaranteed to have gone through `parse_gm_command`'s own
`_require_int`/`_require_number` checks -- `docs/GM_LANE.md` explicitly
commits to accepting a `GmCommand` "regardless of source," the same policy
choice `gm/commands.py` itself makes, and `z` is not part of the `warp`
grammar at all so it NEVER passes through those checks even on the intended
call path. A bare `int(...)`/`float(...)` conversion here would (a) build a
frame containing NaN/Inf coordinates silently -- exactly the "landmine for
whoever wires real warp execution against this parser later" `commands.py`'s
own `_require_number` comment warns about, just reachable through the one
axis (`z`) that comment does not cover -- and (b) raise a bare `ValueError`
instead of this module's own `WarpExecutorError` for a malformed `scene_id`,
breaking the refusal contract this module's docstring and tests promise.
This module therefore re-validates every numeric field itself (finite,
correctly typed) and wraps every conversion so any failure surfaces as
`WarpExecutorError`, never a bare `ValueError` -- the guarantee holds at the
point bytes are actually built, not only for callers that happened to route
through `parse_gm_command`.

The same round's docstring in `gm/say_wire.py` names a second, identical gap
this module carried and its author left unfixed at the time: `command.args`
was measured/indexed with plain `len()`/`[0]`/`[1]`/`[2]`, which raises a
bare `TypeError`/`KeyError`/`IndexError` (never `WarpExecutorError`) for an
`args` container of the wrong *shape* (`None`, a `set`, a `dict`), not just
the wrong value -- `say_wire.py` fixed its own copy of this gap and flagged
this module's copy as a known follow-up. This round applies the same guard
here, then a `pf-adversary` pass on the fix itself (same round) found two
gaps the `say_wire.py`-style three-type catch (`TypeError`/`KeyError`/
`IndexError`) still left open, reproduced live against a crafted `args`
object: (a) a custom `__len__`/`__getitem__` that raises anything outside
those three types (e.g. `AttributeError`, `ValueError`) still leaked past
this module's own "every failure surfaces as `WarpExecutorError`" promise,
so both guards now caught `Exception` broadly instead of three named types;
(b) a `str`/`bytes` scalar of length 3 (e.g. `"123"`) is not a crash at
all -- it passes `len(args) == 3` and is positionally indexable, so it was
silently read as a real `(scene_id, x, y)` tuple instead of being refused
as the wrong container shape, so `args` was rejected by `isinstance` before
either guard ran.

A later round applied the identical broad-catch-plus-`str`/`bytes`-guard
fix to `gm/say_wire.py`'s own copy of this gap, and `pf-adversary` broke it
again the same day: an integer-keyed `dict` (e.g. `{0: 1, 1: 2, 2: 3}`) is
exactly the "mapping" shape `docs/GM_LANE.md` already names as one of the
three canonical wrong shapes, yet `len(d)` and `d[0]`/`d[1]`/`d[2]` all
succeed normally for it -- no exception is ever raised, so neither the
`str`/`bytes` guard nor either `except Exception` clause fires, and the
identical gap applies here (`{0: 1, 1: 2, 2: 3}` builds a real `ForcePos`
frame from a dict that was never the intended `(scene_id, x, y)` tuple).
Enumerating one more forbidden shape every time adversary finds one that
happens not to raise is an unbounded blacklist against a `tuple[str, ...]`-
typed field (`gm/commands.py`'s `GmCommand.args` annotation) with exactly
one legitimate shape, so this module now asserts that shape directly
(`isinstance(args, tuple)`) instead: every non-`tuple` `args` -- `None`, a
`set`, a `dict` of any key type, a `str`/`bytes` scalar, a `bytearray`, a
custom object, a `list` -- is refused up front, before `len()`/indexing
ever runs.

This module does not read off a live socket, does not track player state,
and does not send anything -- it returns frame bytes for a caller to send.
Wiring a real send is CORE-REQUEST territory, same as every other GM
wire-builder in this package (see docs/GM_LANE.md, CORE-REQUEST-011).
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from .. import world_scene_travel
from ..population import SCENE_SEQUENCE
from ..world_scene_entry import is_position_within_scene_ground
from .commands import GmCommand
from .scene_catalog import is_known_scene_id
from .teleport_wire import make_force_pos_frame_with_body

# COO-DECISION 2026-08-31T14:41+07:00 (pf_bridge/notes_to_chief/
# 20260831_1441_COO-DECISION-warp-cross-scene-opens-gt106r2-passed.md)
# authorizes this module to compose a LIVE, mid-session cross-scene warp via
# legacy.make_login_teleport, replacing the stage-only policy COO-DECISION
# 20260828_2130/20260830_2048 held for exactly this shape: `/warp <scene_id>
# x y` naming a scene the connection is NOT already in.
#
# UNLIKE `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` ABOVE THIS
# MODULE'S OWN ForcePos PATH, this is not a byte waiting on RE proof --
# TeleportVital v4 built by `legacy.make_login_teleport` is the SAME encoder
# `runtime.py` already sends live, mid-session, on main today (see the
# module docstring's "CROSS-SCENE WARP, RESOLVED A DIFFERENT WAY" section),
# and GT-106-R2 proved a real client renders the destination scene when that
# exact mechanism fires mid-session.  What stayed shut until this round was
# POLICY, not an unmeasured byte: COO-DECISION 20260830_2048 held it shut
# pending that result, on this lane's own G-OBS principle (do not ship an
# unproven mid-session behaviour), and lifted it once the result was PASS.
#
# So this is a named boolean, not a None-until-RE constant -- a future
# revocation flips it back to False, and `tests/test_gm_warp_executor.py`
# pins both the value and this citation, the same discipline
# `FORCE_POS_VITAL_VERSION_CONFIRMED`'s own history holds for its constant.
WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED = True


class WarpExecutorError(ValueError):
    """A `warp` command cannot be executed via `ForcePos`/`TeleportVital` as
    given.
    """


@dataclass(frozen=True)
class WarpTarget:
    """Where one accepted `warp` actually sent the connection, in wire terms.

    Every field is the value the OUTBOUND FRAME CARRIES, not the value the GM
    typed: `x`/`y`/`z` are IEEE binary32, read back out of the built payload
    for the ForcePos composer (`teleport_wire.make_force_pos_frame_with_body`)
    or reproduced by the identical binary32 round trip for the TeleportVital
    composer (`make_warp_teleport_frame_with_target`, which does not get a
    payload handed back to decode -- see that function's own comment).

    `scene_id` means one of two things depending on WHICH composer built this
    target, and that is a real difference in kind, not just in value:
      * `make_warp_force_pos_frame_with_target` -- the connection's CURRENT
        scene, proven equal to it, because ForcePos carries no scene id at
        all and this module refuses to use it to cross scenes.
      * `make_warp_teleport_frame_with_target` -- the DESTINATION scene the
        TeleportVital frame names, which DOES carry a scene id (RE-090).
    A reader comparing this against a later position report does not need to
    know which composer built it first: `warp_target_record.distance_to_target`
    already treats a reported position in a different scene as NOT
    COMPARABLE rather than as a mismatch, which is exactly the right answer
    for both cases -- a same-scene target the GM never reached, and a
    cross-scene target the client has not yet confirmed by arriving.

    !! WHAT A `WarpTarget` IS EVIDENCE OF, AND IT IS ONE THING.  It says
    "these bytes went out".  It is not evidence that the client moved THIS
    CHARACTER TO THIS EXACT POINT: RE-129 measured the client's registered
    ForcePos handler as `mov al,1; ret 4` -- ForcePos targets carry no such
    thing.  A TeleportVital target is a different case in one respect and
    the same case in the one that matters here: GT-106-R2 measured that the
    MECHANISM moves a real client's screen, but that is a fact about the
    mechanism, not about any one `WarpTarget` value -- it is not a per-frame
    delivery receipt, and this dataclass still does not become one just
    because the composer that built it is now proven live.  Comparing a
    later durable position row against this target is exactly how a reader
    tells "sent" from "arrived" apart, which is why chief asked this lane to
    expose it (`CHIEF-REPLY 20260828_2301`, appendix item 5) -- not so that a
    match can be assumed.
    """

    scene_id: int
    x: float
    y: float
    z: float


def make_warp_force_pos_frame(
    legacy,
    vital_version: int,
    command: GmCommand,
    current_scene_id: int,
    z: float,
) -> tuple[bytes, bytes]:
    """Build a server->client `ForcePos` frame for a same-scene `warp`.

    `current_scene_id` is the connection's actual current scene -- this
    module has no notion of player state, so the caller (runtime.py, which
    does) must supply it. The command's own `scene_id` argument is checked
    against it: if they differ, this function refuses instead of sending an
    in-scene hop for a command that asked to leave the scene, which would
    misrepresent what `ForcePos` actually did. Same policy for the
    scene-only `warp <scene_id>` form (no x/y) -- there is no position to
    send at all in that case.

    `z` is required for the same reason `state_wire.make_gm_update_state_frame`
    requires `vital_version` rather than guessing one: the GM-003 `warp`
    grammar carries no z argument, so a caller must supply one explicitly
    (typically the target connection's own current z) instead of this
    module inventing an elevation. Every numeric field (`scene_id`, `x`,
    `y`, `z`) is re-validated here regardless of whether `command` came from
    `parse_gm_command` -- see module docstring's pf-adversary note.
    """
    pc, frame, _target = make_warp_force_pos_frame_with_target(
        legacy, vital_version, command, current_scene_id, z
    )
    return pc, frame


def make_warp_force_pos_frame_with_target(
    legacy,
    vital_version: int,
    command: GmCommand,
    current_scene_id: int,
    z: float,
) -> tuple[bytes, bytes, WarpTarget]:
    """`make_warp_force_pos_frame`, plus where those bytes send the connection.

    Identical validation, identical refusals, identical bytes -- the function
    above is this one with the target dropped.  It is written in this
    direction on purpose: a second copy of the argument validation would be
    free to disagree with the frame, and a target that disagrees with the
    bytes is worse than no target at all, because a reader comparing a
    durable row against it would blame the client for this module's drift.
    The one validation pass also matters against the threat model this
    module's docstring already carries -- a hand-built `GmCommand` whose
    `args` elements have a `__float__` that returns a different number every
    call would otherwise put one value on the wire and record another.
    """
    if command.name != "warp":
        raise WarpExecutorError(
            f"make_warp_force_pos_frame only applies to warp commands, got {command.name!r}"
        )
    args = _require_args_tuple(command)
    if len(args) != 3:
        raise WarpExecutorError(
            "warp <scene_id> with no x/y has no position for ForcePos to carry; "
            "cross-scene warp needs TeleportVital, not built yet -- see module docstring"
        )
    raw_scene_id, raw_x, raw_y = args[0], args[1], args[2]
    scene_id = _require_int(raw_scene_id, "scene_id")
    if scene_id != current_scene_id:
        raise WarpExecutorError(
            f"warp target scene_id {scene_id} != current_scene_id {current_scene_id}: "
            "ForcePos carries no scene id and cannot cross scenes; cross-scene warp "
            "needs TeleportVital, not built yet -- see module docstring"
        )
    x = _require_finite_float(raw_x, "x")
    y = _require_finite_float(raw_y, "y")
    z = _require_finite_float(z, "z")
    _refuse_if_outside_ground(scene_id, x, y)
    pc, frame, body = make_force_pos_frame_with_body(legacy, vital_version, x, y, z)
    # `body`, not `(x, y, z)`: see WarpTarget's docstring -- the target has to
    # be the wire's own binary32 values, or every later comparison inherits an
    # encoding error that grows with the coordinate's magnitude.
    return pc, frame, WarpTarget(scene_id, body.x, body.y, body.z)


def make_warp_teleport_frame_with_target(
    legacy,
    command: GmCommand,
    z: float,
) -> tuple[bytes, bytes, WarpTarget]:
    """Build a server->client `TeleportVital` frame for a cross-scene `warp`.

    See the module docstring's "CROSS-SCENE WARP, RESOLVED A DIFFERENT WAY"
    section for why this is safe to compose without any of the unproven
    `TeleportVital` fields `teleport_wire.py`'s general builder would need:
    `legacy.make_login_teleport` hardcodes every one of them to the same
    constructor-default value the client's own prototype writes, so this
    function only ever supplies the four fields `warp`'s own grammar and the
    connection's own state can honestly provide -- `scene_id`, `x`, `y` from
    the command, `z` from the caller (same reason
    `make_warp_force_pos_frame_with_target` takes it as a parameter: the
    `warp` grammar carries no elevation at all).

    `scene_seq` is NOT a parameter, on purpose, and it is not a guess either:
    `SCENE_SEQUENCE` (`population.py`) is the same `0` every scene-crossing
    call site in this project already sends, cited there as "the only value
    ever measured, at scene 1 and at scene 2 alike" -- reused here rather
    than re-derived, so a future correction to that constant fixes this
    module for free instead of leaving a second copy to drift.

    ONLY THE `warp <scene_id> x y` FORM REACHES THIS FUNCTION.  The bare
    `warp <scene_id>` form has no x/y for a `TeleportVital` target to carry
    either, exactly the same refusal `make_warp_force_pos_frame_with_target`
    raises for that shape -- this module does not invent a spawn point for
    either composer.  (Routing which form reaches which function at all is
    `gm/chat_command_action.py::_warp_action`'s job, not this one's; this
    function refuses the coordinate-less shape itself too, so a caller
    mistake in that routing fails closed here rather than composing a
    frame from missing data.)

    `scene_id` IS RE-CHECKED AGAINST THE SCENE CATALOG, unlike the
    same-scene ForcePos path (which never needs to, because its `scene_id`
    is proven equal to the connection's own current scene by the refusal
    two lines up in that function).  A cross-scene target is NOT already
    known to be a real scene, and `scene_catalog.is_known_scene_id` is the
    one check this lane has always applied before letting a GM name a
    destination at all (`gm/login_scene_stage.py` applies the identical
    check before staging).  Deliberately NOT the heavier
    `login_scene_admission` check that gates STAGING: that table is about
    whether the LOGIN path can enter a scene at boot, a different
    mechanism this live mid-session frame does not go anywhere near, and
    scene 17 -- the one destination GT-106-R2 actually measured working
    live -- is proof the two checks disagree: `is_known_scene_id(17)` is
    True, `login_scene_admission.single_use_entry_is_admissible(17)` is
    False.  Gating this function on the wrong table would refuse the one
    destination this round can cite evidence for.

    Every numeric field is re-validated here regardless of whether
    `command` came from `parse_gm_command`, same as
    `make_warp_force_pos_frame_with_target` -- see this module's docstring,
    pf-adversary note.
    """
    if command.name != "warp":
        raise WarpExecutorError(
            f"make_warp_teleport_frame_with_target only applies to warp "
            f"commands, got {command.name!r}"
        )
    args = _require_args_tuple(command)
    if len(args) != 3:
        raise WarpExecutorError(
            "cross-scene warp <scene_id> with no x/y has no position for "
            "TeleportVital to carry either; that form still stages the "
            "next login instead -- see gm/login_scene_stage.py"
        )
    raw_scene_id, raw_x, raw_y = args[0], args[1], args[2]
    scene_id = _require_int(raw_scene_id, "scene_id")
    if not is_known_scene_id(scene_id):
        raise WarpExecutorError(
            f"scene_id {scene_id} is not a scene gm/scene_catalog.py names; "
            "refusing rather than sending a TeleportVital frame at an "
            "unknown destination"
        )
    x = _require_finite_float(raw_x, "x")
    y = _require_finite_float(raw_y, "y")
    z = _require_finite_float(z, "z")
    _refuse_if_outside_ground(scene_id, x, y)
    pc, frame = legacy.make_login_teleport(scene_id, SCENE_SEQUENCE, x, y, z)
    # No payload comes back to decode the way `make_force_pos_frame_with_body`
    # hands one back -- `legacy.make_login_teleport` is a fixed constructor,
    # not a builder this module composes a payload for.  Its `x`/`y`/`z`
    # still land on the wire through `f32tag`, the identical IEEE-754
    # single-precision encode `teleport_wire._read_tag_f32` would decode back
    # out, so redoing that exact round trip here reproduces the wire's own
    # values byte-for-byte without needing to parse the frame this function
    # already built -- see WarpTarget's own docstring for why this has to be
    # the wire's value and not the Python float argument.
    wire_x = struct.unpack("<f", struct.pack("<f", x))[0]
    wire_y = struct.unpack("<f", struct.pack("<f", y))[0]
    wire_z = struct.unpack("<f", struct.pack("<f", z))[0]
    return pc, frame, WarpTarget(scene_id, wire_x, wire_y, wire_z)


def warp_no_coords_live_target(scene_id: int):
    """The `world_scene_travel` destination for GM-A's bare `warp <scene_id>`
    (no x/y), or ``None`` when this scene id keeps the OLD stage-only rule.

    GM-A (`pf_bridge/notes_to_chief/20260901_0215_PANYA-ORDER-*.md` section
    3, chief's `R278` broadcast) asks for a bare `/warp <scene_id>` to land
    LIVE at "that destination map's standard spawn point ... resolved via
    `SCENE_NAME[n].n_MARKER`" (`GT-182`'s own objective, quoting
    `COO-DECISION 20260829_0542`) rather than only staging the next login
    the way this shape always has.  `world_scene_travel.py` already carries
    exactly that per-scene pinned point (`destination`/`spawn_position`,
    the same anchor `runtime.py`'s bg0002 eager-census arrival path uses,
    per `R278`) -- this function is the one place that decides whether a
    given scene id has one, so `_warp_action`'s routing and this module's
    frame builder below cannot disagree about which scenes qualify.

    GATED ON `has_authored_entry` (`entry_marker != 0`, i.e. n_MARKER != 0),
    NOT ON "world_scene_travel has ANY spawn pinned" -- those are different
    questions and conflating them would be a real regression.  Four scene
    ids in the registry today (17, 126, 278, 997) carry a pinned `spawn`
    with NO marker (`n_MARKER == 0`): an owner-decreed or native-placement
    point, `evidence_tier` "authored"/"decreed_provisional", never a
    developer-authored ARRIVAL marker.  `GT-182` nonclaim 4 is explicit that
    those scenes "keep the OLD rule" (stage-only) on purpose -- and scene
    278 specifically already has a PINNED TEST asserting that
    (`tests/test_gm_chat_command_action.py::ProductionCallShapeTests::
    test_the_default_argument_call_stages_where_gt141_says_it_does`, GT-141)
    that this function's gate must not silently flip.  Checking
    `has_authored_entry` instead of "spawn is not None" is what keeps that
    test's answer unchanged while still opening the marker-backed scenes
    (1-11, 14, 130 today) GT-182 itself names as the shape to build (its own
    example list: "scene 4/5/6/8/10").

    Never raises for an unpinned, markerless, or entirely unknown scene id
    -- all three answer `None`, the same "caller falls back to staging"
    signal, and telling them apart is not this function's job.  Only a
    scene_id that is not a plain int raises, the same contract every other
    `_require_int` call in this module keeps.
    """
    scene_id = _require_int(scene_id, "scene_id")
    try:
        target = world_scene_travel.destination(scene_id)
    except (KeyError, ValueError):
        # KeyError: scene_id is not in world_scene_travel's registry at all
        # (a scene LANE-A has not opened yet, or never will).  ValueError:
        # `destination`'s own `_require_int` on a scene_id outside its
        # 1..0xFFFF wire range -- already validated above by this function's
        # own `_require_int`, kept here only so a future change to either
        # module's range cannot turn into an uncaught exception.
        return None
    if not target.has_authored_entry or target.spawn is None:
        return None
    return target


def make_warp_teleport_frame_no_coords_with_target(
    legacy,
    scene_id: int,
) -> tuple[bytes, bytes, WarpTarget]:
    """Build a live `TeleportVital` for GM-A's bare `warp <scene_id>` shape.

    Sibling of `make_warp_teleport_frame_with_target` above, with ONE
    difference that is the entire point of this function: `x`/`y`/`z` come
    from `world_scene_travel.spawn_position` (the destination's own pinned
    marker point), never from a `GmCommand`'s typed arguments or from the
    caller's current z -- this is the fix for `GT-172`'s finding F-2 (a
    coordinate-carrying warp sends the OLD scene's z, so the character
    floats or sticks at the new one).  A bare `warp <scene_id>` has no typed
    x/y to begin with, so there is nothing to disagree with the marker
    point; F-2 is dodged by construction for this shape, not patched.

    `scene_id` IS RE-CHECKED here via `warp_no_coords_live_target`, not
    trusted from a caller that already checked it once -- the same
    single-validation-pass discipline `make_warp_force_pos_frame_with_target`
    documents for its own duplicate-caller threat model.  Routing (deciding
    whether a `warp` command reaches this function at all) stays
    `gm/chat_command_action.py::_warp_action`'s job, same split as the
    with-coordinates sibling.

    `scene_seq` is `SCENE_SEQUENCE` (0), the identical constant the
    with-coordinates sibling uses and the only value ever measured at any
    scene crossing in this project -- see that function's own comment.
    """
    target = warp_no_coords_live_target(scene_id)
    if target is None:
        raise WarpExecutorError(
            f"scene_id {scene_id} has no world_scene_travel authored-marker "
            "entry (n_MARKER == 0, or not in that registry at all) -- GM-A's "
            "live no-coordinate warp only reaches marker-backed scenes; this "
            "scene id keeps the old stage-only behaviour (GT-182 nonclaim 4)"
        )
    x, y, z = world_scene_travel.spawn_position(target)
    pc, frame = legacy.make_login_teleport(target.n_id, SCENE_SEQUENCE, x, y, z)
    # Same wire-value round trip as `make_warp_teleport_frame_with_target`'s
    # own comment explains: no payload comes back from a fixed constructor
    # to decode, so binary32 round-tripping the composer's own input
    # reproduces the wire's value byte-for-byte without re-parsing the frame
    # this function just built.
    wire_x = struct.unpack("<f", struct.pack("<f", x))[0]
    wire_y = struct.unpack("<f", struct.pack("<f", y))[0]
    wire_z = struct.unpack("<f", struct.pack("<f", z))[0]
    return pc, frame, WarpTarget(target.n_id, wire_x, wire_y, wire_z)


def warp_command_scene_id(command: GmCommand) -> int:
    """The scene_id a parsed `warp` command names, validated once, here.

    `gm/chat_command_action.py` has to know WHICH scene a warp asks for
    before it can decide between `/warp`'s halves: the same-scene half this
    module composes a `ForcePos` for, the cross-scene-with-coordinates half
    this module now composes a live `TeleportVital` for
    (`make_warp_teleport_frame_with_target`, COO-DECISION 1441), and the
    cross-scene-with-no-coordinates half `gm/login_scene_stage.py` still
    stages for the next login.  It reads the scene_id through this function
    rather than indexing `command.args` itself, so the shape checks that
    protect the frame builders protect the decision too -- a hand-built
    `GmCommand` whose `args[0].__int__` returns a different number on each
    call cannot route one way and act on another.
    """
    if command.name != "warp":
        raise WarpExecutorError(
            f"warp_command_scene_id only applies to warp commands, got {command.name!r}"
        )
    args = _require_args_tuple(command)
    if not args:
        raise WarpExecutorError("warp <scene_id> needs a scene_id, got no arguments")
    return _require_int(args[0], "scene_id")


def warp_command_has_coordinates(command: GmCommand) -> bool:
    """True for the `warp <scene_id> x y` form, False for bare `warp <scene_id>`.

    The parser (`gm/commands.py`) only ever produces those two shapes; this
    is the one place that reads which one arrived, so the two callers cannot
    disagree about what "has coordinates" means.
    """
    if command.name != "warp":
        raise WarpExecutorError(
            f"warp_command_has_coordinates only applies to warp commands, "
            f"got {command.name!r}"
        )
    return len(_require_args_tuple(command)) == 3


def _require_args_tuple(command: GmCommand) -> tuple:
    args = command.args
    if type(args) is not tuple:
        # GmCommand.args is typed tuple[str, ...] (gm/commands.py) -- every
        # legitimate caller, parse_gm_command included, produces a plain
        # tuple. A blacklist of individually-discovered wrong shapes (None,
        # a set, a dict, a str/bytes scalar) is unbounded: pf-adversary
        # defeated the str/bytes-scalar blacklist entry with an
        # integer-keyed dict (len()/[i] both succeed normally for e.g.
        # {0: 1, 1: 2, 2: 3}, so no exception was ever raised for it to
        # catch). An isinstance(args, tuple) allowlist closed that but was
        # itself defeated by a tuple *subclass* overriding
        # __len__/__getitem__ to raise something other than
        # WarpExecutorError -- exactly the "regardless of source,
        # hand-built GmCommand" threat model this docstring already claims
        # to defend against, since nothing in GmCommand (a plain frozen
        # dataclass, gm/commands.py) stops a caller from constructing one.
        # Requiring the exact type, not an isinstance match, rejects every
        # subclass outright -- a real tuple can never raise on
        # len()/indexing, so there is no dunder left to lie through.
        raise WarpExecutorError(f"warp command args must be a tuple, got {args!r}")
    return args


def _require_int(value, label: str) -> int:
    # A hand-built GmCommand (accepted "regardless of source") can carry an
    # args element whose __int__ raises anything -- AttributeError, KeyError,
    # a custom exception -- not just TypeError/ValueError. This module's own
    # contract is that every failure here surfaces as WarpExecutorError, so
    # the conversion itself is guarded the same broad way the args-container
    # shape check already is, one field deeper.
    try:
        return int(value)
    except Exception as exc:
        raise WarpExecutorError(f"{label} must be an integer, got {value!r}") from exc


def _refuse_if_outside_ground(scene_id: int, x: float, y: float) -> None:
    """Refuse an (x, y) this project's own ground data proves is off the map.

    Closes the gap LANE-GM opened against LANE-A for (`pf_bridge/
    notes_to_chief/20260901_2028_LANE-GM-TO-LANE-A-warp-coordinate-bound-
    needs-a-public-ground-check.md`): before this, `_require_finite_float`
    only rejected NaN/Inf, so `/warp 2 100000 200` composed a real frame for
    a point `world_scene_entry.py` elsewhere calls `RELOCATED_OUTSIDE_GROUND`
    against the scene's own `ground_extent`. LANE-A opened
    `world_scene_entry.is_position_within_scene_ground` for this (reply:
    `.../20260901_2252_LANE-A-REPLY-to-lane-gm-ground-check-api-ready.md`);
    this function is the one place that decides what this module DOES with
    its three-valued answer.

    NOT a hard gate for a scene whose ONLY spawn evidence is a
    PROVISIONAL-OWNER-DECREE (scene 17 today, per `world_scene_travel`'s own
    registry). `is_position_within_scene_ground`'s underlying
    `_ground_evidence` returns `False` there for EVERY (x, y) -- including
    (834, -598), the EXACT coordinate GT-106-R2 measured a real client
    receiving and rendering, and that COO-DECISION 2026-08-31T14:41+07:00
    already authorized `/warp 17 834 -598` to send
    (`tests/test_gm_warp_executor.py::WarpTeleportCrossSceneTests::
    test_scene_seq_is_always_the_shared_scene_sequence_constant` pins that
    exact call). A hard gate on that `False` would silently revoke the one
    cross-scene destination this project has ever proven live -- a worse
    outcome than the unbounded-coordinate gap this function exists to close.
    So: only refuse when the destination's OWN evidence is not decree-only.
    This reads `spawn_provenance`, a field `world_scene_travel.destination`
    already computes and this module already imports that module for -- it
    does not re-derive or copy `_ground_evidence`'s radius arithmetic (the
    one thing the request letter's own "ข้อควรระวัง" section asked the
    consumer to avoid).

    Every scene with NO ground evidence at all (`ground_extent is None` --
    every scene this registry carries today except 17 and 278) answers
    `None` here and is never refused; a caller that types `/warp 1 100000
    200` still gets no protection from this function, the same as before
    this round -- see the round file's nonclaim for why that gap stays
    open (there is no ground data to check it against yet).
    """
    try:
        target = world_scene_travel.destination(scene_id)
    except (KeyError, ValueError):
        # Unknown scene id: the caller's own scene_id checks
        # (is_known_scene_id / current_scene_id equality, above this
        # function's call sites) already own refusing that shape; nothing
        # for a ground check to add for a destination that is not real.
        return
    if (
        target.spawn_provenance is not None
        and target.spawn_provenance.startswith("PROVISIONAL-OWNER-DECREE")
    ):
        return
    if is_position_within_scene_ground(scene_id, x, y) is False:
        raise WarpExecutorError(
            f"({x}, {y}) is outside scene {scene_id}'s ground_extent -- "
            "refusing rather than sending a warp frame off the map"
        )


def _require_finite_float(value, label: str) -> float:
    try:
        parsed = float(value)
    except Exception as exc:
        raise WarpExecutorError(f"{label} must be a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise WarpExecutorError(f"{label} must be finite, got {value!r}")
    return parsed
