"""LANE-Q: the first live wire connection into the ``Trigger`` status book.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST. Nothing.
No frame is composed, no bytes are queued, nothing is returned to the client.
This module only makes ``lua_api.trigger.trigger_status_registry()`` --
the SAME process-memory book ``Trigger.GetTriggerStatus``/``SetStatus``/
``NextStatus`` read and write when a script calls them -- receive one real
write per inbound ``TriggerVital`` (0x1FB2) frame, keyed by the wire's own
native trigger id. This is COMING, not DONE (see ``docs/SCRIPT_LANE.md``,
this round's own entry, and the round file's SCOREBOARD line): it proves the
wire reaches the registry, not that any specific ``t_*.lua`` file now runs.

WHY THIS DOES NOT RUN A SCRIPT, AND WHY THAT IS NOT A SHORTCUT.
``lua_api/trigger.py``'s own module docstring names the missing piece
precisely: "the trigger-id -> script-file mapping ... this round did not go
mine it". A first pass, ``RE-273`` (``pf_bridge/notes_to_chief/
20260906_1340_RE-273-RESULT-TGR-FILE-IS-THE-TRIGGER-ID-TO-LUA-TABLE.md``),
measured that per-scene ``.tgr`` files DO carry a small ``trigger_ordinal``
(u16) next to each script's filename, but left its own "what this ticket
does NOT answer" section explicit that this had not been shown to be the
same number as the wire's ``0x0F`` tag value this hook reads.

MEASURED NOW, NOT STILL OPEN. The narrowed follow-up (``pf_bridge/
notes_to_chief/20260906_1525_LANE-Q-RE-273-DECISION-*.md``, the same ticket
continued) came back positive (``pf_bridge/notes_to_chief/
20260908_2230_RE-273-RESULT-TGR-ORDINAL-COPIES-TO-WIRE-TAG-0F.md``): a
POSITIVE field crosswalk traced through the client's own data flow, not a
"the numbers happen to match" coincidence the house rule (``AGENTS.md``
Section 7, "ก่อนประกาศว่า ... ไม่เคยวัด ต้อง grep ให้ครบ") forbids --
the client reads the embedded u16 ordinal into the ``.tgr`` record at
``record+0x4E``, then copies THOSE SAME 16 bits into the outbound vital at
``vital+0x14``, which the serializer writes under tag ``0x0F``. So the
wire id this hook already keys the registry on IS the ``.tgr`` ordinal,
by construction, not by resemblance.

THIS STILL DOES NOT RUN A SCRIPT, for a DIFFERENT reason now. The
crosswalk (wire id <-> ordinal) is proven; the per-scene DATA (which
ordinal maps to which ``.lua`` filename, in the scene the player is
actually in) is not committed anywhere this lane can read without the
live client -- ``gamedata/scene/*/*.placements.tsv`` (checked this round)
carries mob-set placements, not trigger records, and the one full ``.tgr``
dump this project has (``RE-289``, ``Bg3001`` only) lives in a letter, not
a structured table. So this module still writes into the registry using
the wire id as the key and dispatches to NOTHING -- no script file is
looked up, no ``ScriptHost`` is built, no Lua runs -- but the key it
writes is now a MEASURED ``.tgr`` ordinal, not an unproven guess, and the
remaining gap is a data-extraction RE ticket (more scenes' ``.tgr`` files
dumped and turned into a committed ordinal->filename table), not a
crosswalk question. Whatever dispatches a real script can trust this
registry key outright.

WHY THE HOOK POINT ITSELF IS SAFE TO SHARE WITH LANE-A, MEASURED NOT ASSUMED
(``pf_bridge/notes_to_chief/
20260906_0727_LANE-A-TO-LANE-Q-world-registry-interface-and-trigger-hit-hook-point.md``,
cross-checked here against ``lane_hooks/__init__.py`` itself, not taken on
that letter's word):
  * ``fire()`` runs every hook registered on a point, in registration order
    -- this hook does not replace ``lane_a_island_trigger_log``'s.
  * fail-closed: an exception raised inside a hook is caught, logged by
    name, and does not stop dispatch or re-raise -- a bug in this file
    cannot break LANE-A's console line or the frozen dispatch loop.
  * report-only by construction: ``fire()`` returns nothing, so nothing this
    hook does can answer the frame or change what gets sent to the client;
    a real reply is a CORE-REQUEST, a separate and later concern.

SCENE RESOLUTION, AND WHY IT MAY LEGITIMATELY FAIL TODAY.
The state object ``runtime.py`` passes as ``session=self`` on this point is
the same class whose ``self.foundation.selected.position.scene_id`` chain
is already live and read repeatedly in ``runtime.py`` itself today (grepped,
not assumed: ``runtime.py:4586``, ``:4706``, ``:4919``, among others --
``model.Position`` itself declares ``scene_id: int`` as a plain field, not a
proposal). This module reads that same path, defensively: a session double built
by a test, or any future caller shape that has not grown that attribute chain
yet, resolves to ``None`` rather than raising. ``world_scene_folder.
scene_folder_for_scene_id`` is the ONE reader LANE-A's own module docstring
names for turning that integer into the folder key ``TriggerStatusRegistry``
takes (``mob_loot.scene_key`` case-folds it from there); an unaddressed scene
id, or an id of the wrong type, returns/raises through that reader and this
module treats either as "cannot resolve", never as scene 0 or the empty
string (``lua_api/trigger.py``'s own ``DEFAULT_CONTEXT`` docstring measures
why the empty string silently no-ops every write under it).

WHY THE PRODUCTION SINGLETON, NOT A PRIVATE INSTANCE.
``lua_api.trigger.trigger_status_registry()`` is the process's own book --
the same one a live ``Trigger.GetTriggerStatus``/``NextStatus`` call from a
running script would read and write, once something dispatches a script at
all. Nothing else touches this singleton in production today (``lua_api/
trigger.py``'s ``build_namespace`` gives every caller that does not ask for
it a fresh private instance, and no shipped call site asks for it yet) --
this hook is the first.

``production_allowed = True``: this module never sends a byte, never blocks
dispatch (fail-closed hook body below, on top of ``fire()``'s own fail-closed
wrapper), and only ever writes into a book this lane owns outright (LANE-Q
owns ``TriggerStatusRegistry``; see ``lua_api/trigger.py``'s own docstring on
why this is a separate book from LANE-A's world registry, not a second front
door to it).
"""
from __future__ import annotations

import sys

from . import hook
from . import lane_a_island_trigger_log as _trigger_frame
from .. import world_scene_folder
from ..lua_api import trigger as lua_api_trigger

production_allowed = True

POINT = "vital_inbound_trigger_vital"
TOKEN = "LANE_Q_TRIGGER_VITAL_DISPATCH"


def _scene_id_from_session(session: object) -> int | None:
    """``session.foundation.selected.position.scene_id``, or ``None``.

    Never raises: every attribute in that chain is read defensively, because
    the callers this hook actually sees in tests (bare doubles) and in a
    future production call site (the real state object) do not share a
    common base class that guarantees the chain exists.
    """
    try:
        scene_id = session.foundation.selected.position.scene_id  # type: ignore[attr-defined]
    except AttributeError:
        return None
    # ``type(x) is int`` rather than ``isinstance``: a bool IS an int
    # subclass in Python (``isinstance(True, int)`` is True) but
    # ``type(True) is int`` is False, so this one check already refuses a
    # bool -- the same posture ``lua_api/trigger.py``'s own ``_coerce_int``
    # takes explicitly rather than relying on the same accident.
    if type(scene_id) is not int:
        return None
    return scene_id


def _scene_folder(scene_id: int) -> str | None:
    """``world_scene_folder.scene_folder_for_scene_id``, refusal folded to
    ``None`` instead of letting its ``ValueError`` (wrong type) escape --
    ``_scene_id_from_session`` above already guarantees an ``int``, so this
    is a second, independent door, not a trust of the first."""
    try:
        return world_scene_folder.scene_folder_for_scene_id(scene_id)
    except ValueError:
        return None


def dispatch_line(session: object, payload: bytes) -> str:
    """The exact ASCII line this hook prints for one frame.  Never raises.

    Split out from the hook body, same shape as ``lane_a_island_trigger_log.
    console_line``, so a test can assert the line and the registry write
    together without standing up a session or capturing stderr.
    """
    trigger_id = _trigger_frame.first_tag_value(payload, _trigger_frame.TRIGGER_ID_TAG)
    if trigger_id is None:
        return f"{TOKEN} UNRESOLVED reason=no_trigger_id_tag"
    scene_id = _scene_id_from_session(session)
    if scene_id is None:
        return f"{TOKEN} UNRESOLVED reason=no_scene_id wire_trigger_id={trigger_id}"
    folder = _scene_folder(scene_id)
    if folder is None:
        return (
            f"{TOKEN} UNRESOLVED reason=unaddressed_scene"
            f" scene_id={scene_id} wire_trigger_id={trigger_id}"
        )
    registry = lua_api_trigger.trigger_status_registry()
    status = registry.next_status(folder, trigger_id)
    return (
        f"{TOKEN} scene={folder} wire_trigger_id={trigger_id} status={status}"
        " key=WIRE_NATIVE_ID_EQUALS_TGR_ORDINAL_RE273"
    )


# The point name is spelled as a string literal, not as ``POINT`` -- same
# reason ``lane_a_island_trigger_log.py`` gives for its own hook (measured
# there: ``gm/lane_gate_name_audit.py`` reads ``@hook()`` arguments from
# source, and a ``Name`` node makes the whole tree ungradable).
@hook("vital_inbound_trigger_vital")
def _on_trigger_vital(session: object = None, payload: object = b"", **_ignored) -> None:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raw = bytes(payload)
    else:
        print(
            f"{TOKEN} UNRESOLVED reason=bad_payload_type"
            f" type={type(payload).__name__}",
            file=sys.stderr,
        )
        return
    print(dispatch_line(session, raw), file=sys.stderr)
