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
rules forbid (docs/GM_LANE.md, nonclaim rule) -- so this module builds the
same-scene case only, via `ForcePos`, and refuses (`WarpExecutorError`)
rather than silently mis-executing anything else.

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

from .commands import GmCommand
from .teleport_wire import make_force_pos_frame


class WarpExecutorError(ValueError):
    """A `warp` command cannot be executed via `ForcePos` as given."""


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
    if command.name != "warp":
        raise WarpExecutorError(
            f"make_warp_force_pos_frame only applies to warp commands, got {command.name!r}"
        )
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
    return make_force_pos_frame(legacy, vital_version, x, y, z)


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


def _require_finite_float(value, label: str) -> float:
    try:
        parsed = float(value)
    except Exception as exc:
        raise WarpExecutorError(f"{label} must be a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise WarpExecutorError(f"{label} must be finite, got {value!r}")
    return parsed
