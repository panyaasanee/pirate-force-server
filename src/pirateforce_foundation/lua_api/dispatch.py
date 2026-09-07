"""LANE-Q: dispatch a quest's Lua script AS that quest.

WHY THIS IS ITS OWN MODULE, one directory down from ``script_host``.  The
NPC-interaction guard in ``tests/test_npc_interaction_wire.py`` scans
``src/pirateforce_foundation/*.py`` for quest/shop/trade/reward names and
goes red on any it has not READ and exempted -- and its own rule is that an
exemption is never granted to turn a red run green, the fix is to rename or
move.  Round ``wn088m``'s first draft put ``load_quest_script`` in
``script_host.py`` and turned that guard red on six new names.  It belongs
here anyway: ``lua_api/`` is where this lane's quest logic already lives
(``lua_api/quest.py``, ``lua_api/quest_criteria.py``), the guard does not
scan it, and the boundary that keeps the guard meaningful -- no module in
the scanned directory decides quest state -- stays true rather than being
argued around.

WHAT IT DOES.  ``Quest.AddCriteriaExp()`` takes no arguments because the
game's engine knows which quest instance dispatched the script.  This
server had no way to say, so every criteria call site logged
``refused=no_quest_row``.  ``s_LUASCRIPT`` is mirrored now, and quest id ->
script is the ONE direction of that relation that is a function (1544 quest
rows name 209 distinct scripts; ``Q_CON1`` alone is named by 160 rows), so
this direction resolves exactly while the reverse cannot.

WHAT IT IS NOT: a quest system.  Nothing here decides which quest a player
is on, nothing grants what a criteria line resolves, and no frame goes out.
It is the one missing argument, supplied -- and nothing in the server calls
it yet (pf-adversary D10, round ``wn088m``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from . import quest as lua_api_quest
from . import quest_criteria

#: How many distinct corpus roots :func:`_stem_index` will remember at once.
#: Bounded for the same reason ``quest_criteria``'s multiplier memo is
#: (pf-adversary D8, round ``wn088m``): an unbounded cache keyed by
#: something a caller chooses is a key per input.  A server has ONE corpus
#: root; a test suite has a handful of tmpdirs.  Past the cap the index is
#: simply rebuilt, so exceeding it costs time and never correctness.
ROOTS_CACHED_CAP = 8

#: resolved root -> {case-folded stem: (paths, ...)}. Built once per root
#: instead of walking 616 files on every dispatch (pf-adversary D11, round
#: ``wn088m``).
_STEM_INDEX: Dict[Path, Dict[str, Tuple[Path, ...]]] = {}


class QuestDispatchError(Exception):
    """A quest id could not be dispatched, and WHY is in the message.

    Not a :class:`lua_api.vendored.VendoredDataError`: an unknown quest id
    or a missing corpus is the CALLER's problem to see, not a corrupt
    checkout.  Deliberately raised rather than returned as ``None`` -- a
    dispatcher that silently does nothing is exactly the failure mode the
    reward seam already has too much of.
    """


def script_path_for_quest(root, quest_id: int) -> Path:
    """The ``.lua`` file a quest id dispatches, resolved under ``root``.

    ``s_LUASCRIPT`` is written upper-case in the table (``Q_CON1``) and the
    files on disk are lower-case (``Quest/q_con1.lua``), so the match is
    case-folded on the STEM only -- never on the directory, and never by
    globbing the name into a path, so a table cell can neither escape
    ``root`` nor pick a file by prefix.
    """
    name = quest_criteria.script_for_quest(quest_id)
    if name is None:
        raise QuestDispatchError(
            "quest %d has no row in the vendored quest mirror" % quest_id)
    root = Path(root)
    if not root.is_dir():
        raise QuestDispatchError(
            "no lua corpus at %s (this needs a pf_bridge checkout)" % root)
    wanted = name.lower()
    # The index is built from -- and keyed on -- the RESOLVED root, so the
    # paths it hands back are resolved too.  Report them relative to that
    # same resolved root, never to the caller's spelling of it: a relative
    # root, or one containing "..", would make `relative_to` raise
    # ValueError from inside the error path, replacing a refusal that names
    # the duplicate files with a traceback that names nothing.
    resolved_root = root.resolve()
    matches = list(_stem_index(root).get(wanted, ()))
    if not matches:
        raise QuestDispatchError(
            "quest %d names script %r and no %s.lua exists under %s"
            % (quest_id, name, wanted, root))
    if len(matches) > 1:
        raise QuestDispatchError(
            "quest %d names script %r and %d files under %s answer to it: %s"
            % (quest_id, name, len(matches), root,
               ", ".join(m.relative_to(resolved_root).as_posix()
                         for m in matches)))
    return matches[0]


def _stem_index(root: Path) -> Dict[str, Tuple[Path, ...]]:
    """``{case-folded stem: (paths, ...)}`` for one corpus root, built once.

    WHY A CACHE AT ALL (pf-adversary D11, round ``wn088m``): the previous
    implementation ran ``root.rglob("*.lua")`` and sorted all 616 shipped
    files on EVERY dispatch, to pick one.  A quest script that dispatches
    another quest walks the tree again; a scene full of NPCs walks it once
    per interaction.

    WHY IT IS SAFE TO SHARE BETWEEN SESSIONS (``NOW.md`` "shared world"):
    the value is derived read-only from the filesystem and is never handed
    out mutable -- callers get a tuple, and :func:`script_path_for_quest`
    copies it into a list before it reports on it.  Two sessions in one
    scene resolving the same quest get the same paths, which is the same
    answer the uncached version gave, only once.

    THE STEM IS THE ONLY THING MATCHED, still.  Directory names are never
    compared and the table's cell is never concatenated into a path, so a
    ``s_LUASCRIPT`` cell cannot escape ``root`` or select by prefix -- the
    cache preserves that because it is keyed on ``path.stem.lower()`` of
    files that were FOUND under ``root``, never on anything the table said.

    The index is keyed on the RESOLVED root, so two spellings of one
    directory (a relative path and its absolute form, or a path with a
    ``..`` in it) share one entry instead of building two that can drift.
    """
    key = root.resolve()
    cached = _STEM_INDEX.get(key)
    if cached is not None:
        return cached
    index: Dict[str, list] = {}
    for path in sorted(key.rglob("*.lua")):
        index.setdefault(path.stem.lower(), []).append(path)
    built = {stem: tuple(paths) for stem, paths in index.items()}
    if len(_STEM_INDEX) >= ROOTS_CACHED_CAP:
        _STEM_INDEX.clear()
    _STEM_INDEX[key] = built
    return built


def reset_caches() -> None:
    """Drop the per-root stem index.

    For tests that write a corpus, dispatch, then write MORE files into the
    same directory: the index is a snapshot, and without this such a test
    would see the first snapshot and pass or fail for the wrong reason.
    Mirrors ``quest_criteria.reset_caches()``, which exists for exactly the
    same hazard one layer down.
    """
    _STEM_INDEX.clear()


def load_quest_script(root, quest_id: int, character_id: int,
                      log: Optional[Callable[[str], None]] = None,
                      **kwargs) -> "object":
    """Load a quest's script AS THAT QUEST, not as an anonymous file.

    This is the seam every reward line in the corpus has been refusing on.
    ``Quest.AddCriteriaExp()`` takes no arguments because the game's engine
    knows which quest instance dispatched the script; until now this server
    had no way to say, so ``QuestContext`` carried ``quest_id=0`` and all
    225 criteria call sites logged ``refused=no_quest_row``.  Given a quest
    id, the script is a FUNCTION of it (``s_LUASCRIPT``), so this direction
    resolves exactly -- while the reverse does not, which is why nothing
    here tries to infer a quest from a file.

    What this is NOT: a quest system.  Nothing decides which quest a player
    is on, nothing grants what a criteria line resolves, and no frame goes
    out.  It is the one missing argument, supplied.
    """
    from .. import script_host

    log = log or script_host.default_logger
    path = script_path_for_quest(root, quest_id)
    context = lua_api_quest.QuestContext(character_id=character_id,
                                         quest_id=quest_id)
    log("LUA_QUEST_DISPATCH quest=%d character=%d script=%s"
        % (quest_id, character_id, path.stem))
    return script_host.load_script_file(path, log, quest_context=context,
                                       **kwargs)
