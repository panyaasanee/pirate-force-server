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

from . import player as lua_api_player
from . import quest as lua_api_quest
from . import quest_criteria
from . import quest_state_store as lua_api_quest_state_store

#: Console token for the half of the choice below that is GOOD news: this
#: dispatch's quest progress is going to a row that outlives the process.
#: Its opposite (``lua_api.quest_state_store.VOLATILE_TOKEN``) is emitted
#: by the resolver itself.  Both are ASCII (the bridge console is cp874).
DURABLE_TOKEN = "LUA_QUEST_STATE_DURABLE"


def resolve_quest_state_store(persistence, log=None):
    """The quest-state store one dispatch should use, chosen OUT LOUD.

    ``persistence`` is the server's own store object -- the thing that
    carries LANE-DB's quest-state doors
    (``pf_bridge/notes_to_chief/20260905_2212_LANE-DB-TO-LANE-Q-quest-
    state-doors-declared-and-opened-this-round.md``).  Carrying the four
    in ``quest_state_store.REQUIRED_DOORS`` buys the durable adapter;
    missing any of them buys ``lua_api.quest.InMemoryQuestStateStore``
    AND a ``LUA_QUEST_STATE_VOLATILE`` line naming the doors that were
    absent.  The fifth door (``increment_quest_counter``) is NOT required
    here and deliberately so -- see ``quest_state_store.OPTIONAL_DOORS``
    for why requiring a door with no production caller would trade a
    working durable store for a volatile one.

    THIS FUNCTION IS THE ONE-LINE SWAP COO-DECISION 2026-09-08T16:42
    ASKED FOR.  The lane was told to build its half against the contract
    while LANE-DB's rows are still not on ``main`` (measured again this
    round: ``grep -n "def set_quest_flag" store.py`` -> 0 hits), so that
    "the real one arrives" is a change at ONE call site rather than a
    hunt.  This is that call site.

    NEITHER OUTCOME IS SILENT, and that is the whole asymmetry this
    function removes: a server that persists says so once per dispatch,
    and a server that does not says so once per dispatch too.  A reader of
    the console can tell the two apart WITHOUT relogging a character to
    find out -- which, before this, was the only way to find out.

    THE ``persistence is None`` CASE IS NOT AN EXEMPTION FROM THAT
    (pf-adversary F2, round `7qw2tr`, correcting this function's first
    draft).  The draft resolved only when a caller named a store, so every
    caller that exists today -- all of which name none -- got the old
    silence back, under a docstring claiming nothing was silent any more.
    A default that is quiet is exactly the state a reader cannot
    distinguish from a persistent one.  So no store at all is reported
    like any other store that cannot hold quest state.

    ``durable`` IS READ HERE, not merely set (pf-adversary F4): the log
    line below asks the CHOSEN store whether it survives a relog rather
    than inferring it from which branch was taken, so an implementation
    whose attribute and whose behaviour disagree is visible in the
    console instead of only in a class body.
    """
    chosen = lua_api_quest_state_store.quest_state_store_for(persistence, log)
    if chosen is None:
        # `quest_state_store_for` has already said WHY, door by door.
        return lua_api_quest.InMemoryQuestStateStore()
    if log is not None:
        log("%s store=%s durable=%s"
            % (DURABLE_TOKEN, type(persistence).__name__,
               getattr(chosen, "durable", False)))
    return chosen


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
    """``{case-folded stem: (paths, ...)}`` for one corpus root, walked LIVE.

    NOT CACHED, AND THAT IS THE FINDING (pf-adversary finding 3, round
    ``8ou0zg``).  This round first answered D11 -- "``script_path_for_quest``
    rglobs 616 files on every dispatch" -- with a per-root index built once.
    The adversary then MEASURED what D11 was worth: **0.06 ms per dispatch**
    on the warm corpus, 0.1 s to dispatch all 1,213 quest rows once.  And it
    measured what the index cost: the corpus is not static (``pf_bridge``
    takes ``sync: N file(s) from the Windows bridge`` commits), so an index
    built before a sync is a STALE SNAPSHOT --

      * a second file with the same stem landing after the first dispatch
        was not seen, so the duplicate-stem refusal silently returned one
        of them; and
      * a file deleted after indexing turned into a bare
        ``FileNotFoundError`` from ``load_script_file``'s own
        ``read_bytes`` -- which is neither :class:`QuestDispatchError` (what
        callers are told to catch) nor a ``VendoredDataError`` (what
        ``script_host`` classifies as ours), so it landed in the generic
        ``except Exception`` and printed ``LUA_SCRIPT <file> ERR`` against
        an innocent script.  That is D11's ORIGINAL mis-attribution shape,
        re-opened by D11's own fix, and logged AFTER a
        ``LUA_QUEST_DISPATCH`` line claiming the dispatch had happened.

    Trading a measured 0.06 ms for two silent wrong answers is a bad trade,
    so it is not made.  D11 stands answered by measurement rather than by
    code: the walk is not a hot path.  If it ever becomes one, the cache
    that replaces this needs an invalidation story, which is the part the
    first attempt did not have.

    It also removes the module-level mutable state the index introduced --
    ``lua_api.dispatch`` is back to holding none, which is what lets this
    lane keep answering ``TWO_SESSIONS_SAME_SCENE`` with "nothing shared".

    THE STEM IS THE ONLY THING MATCHED.  Directory names are never compared
    and the table's cell is never concatenated into a path, so an
    ``s_LUASCRIPT`` cell can neither escape ``root`` nor select by prefix.
    """
    index: Dict[str, list] = {}
    for path in sorted(root.resolve().rglob("*.lua")):
        index.setdefault(path.stem.lower(), []).append(path)
    return {stem: tuple(paths) for stem, paths in index.items()}


def reset_caches() -> None:
    """No-op: this module holds no cache to drop (see :func:`_stem_index`).

    Kept as a named no-op rather than deleted because
    ``quest_criteria.reset_caches()`` exists one layer down and callers
    reasonably reach for the pair; a missing name would be an
    ``AttributeError`` in a test cleanup, which reads as a broken test
    rather than as "there is nothing to reset".
    """
    return None


def load_quest_script(root, quest_id: int, character_id: int,
                      log: Optional[Callable[[str], None]] = None,
                      persistence: object = None,
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
    # THE PLAYER HALF OF THE SAME ID.  This loader had the character the
    # caller proved and handed it to the quest namespace only, so `Player.*`
    # read the context default of 0 -- harmless while every Player name that
    # used it degraded quietly, and a hard refusal since
    # `Player.TeleportCheck` began requiring a bound character (a travel
    # order filed under 0 can never be consumed by its own echo).  Same id,
    # both namespaces, one call site (pf-adversary, round `nilasm`, H3).
    player_context = kwargs.pop(
        "player_context",
        lua_api_player.PlayerContext(character_id=character_id))
    # PASSING BOTH IS A PROGRAMMING ERROR, NOT A PRECEDENCE PUZZLE.
    # Silently preferring one would leave a caller believing quest progress
    # is on a row when it is in process memory -- the exact confusion
    # `resolve_quest_state_store` exists to end -- so the ambiguity is
    # refused where it is written rather than resolved by a rule nobody
    # reads.
    if persistence is not None and "quest_store" in kwargs:
        raise TypeError(
            "load_quest_script(): pass persistence or quest_store, not both")
    log("LUA_QUEST_DISPATCH quest=%d character=%d script=%s"
        % (quest_id, character_id, path.stem))
    # AFTER the dispatch line, deliberately: that line is the first thing
    # this function has always printed and two existing tests read it as
    # `calls[0]`.  A caller that injected its own `quest_store` has already
    # made the choice and is not told about one it did not make.
    if "quest_store" not in kwargs:
        kwargs["quest_store"] = resolve_quest_state_store(persistence, log)
    return script_host.load_script_file(path, log, quest_context=context,
                                        player_context=player_context,
                                        **kwargs)
