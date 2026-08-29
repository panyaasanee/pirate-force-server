"""GM-005 ADMISSION: which scene ids a login-scene config may name at all.

Two different tables decide two different things, and this lane spent a
round discovering that the gap between them is where an account goes to
die:

* ``gm/scene_catalog.py`` is the client's own 330-row scene NAME table.  It
  answers "does this id have a name", and that is all it can answer -- it
  is a static gamedata pin (evidence grade A for names, no grade at all for
  behaviour).
* ``scenarios/world_scene_registry_001.json`` (lane A's, read through lane
  A's own loader, never through a copy of its rows) answers the question the
  LOGIN path actually asks: is there a pinned entry for this scene, and is
  that entry allowed to be a LOGIN destination (``login_entry_allowed``).

``login_scene_stage.stage_login_scene`` has asked the second table since
round 0z3kjx, because staging a named-but-unpinned scene wrote a valid-
looking entry that made the account's next login fail with
``WORLD_SCENE_ENTRY_REFUSED [scene_not_pinned]`` and no reply.  But staging
is only ONE of the two ways an entry reaches those config files; the other
is an operator with a text editor, and nothing asked the second table on
that path.  MEASURED by pf-adversary in round 38c4tv, walking the real
dispatcher with ``{"plain_tester": 17}`` in the standalone map (scene 17 is
in the name catalog, so it loaded, and is pinned ``login_entry_allowed:
false``, so the login path refused it):

    login #1: actions == []  events: standalone_kept_17, applied_17,
              world_scene_entry_refused_no_reply
    login #2: byte-for-byte identical

The standalone map is deliberately NOT consumed (``COO-DECISION
20260829_0542``), so the retry the client makes is refused in exactly the
same way, forever: that account could not log in again until somebody with
shell access hand-edited a file that is in ``.gitignore``.  No audit row,
no expiry, no in-game fix (the in-game fix needs a chat line, which needs a
login).

This module is the admission check that closes it, and it is deliberately
the SAME predicate the staging path already enforces rather than a second
one that could drift: one implementation, imported by both, so a config an
operator hand-writes is held to exactly the rule ``/warp`` is held to.

[สมมติของสาย GM - รอ COO ยืนยัน] Refusing at ADMISSION rather than at use
is option (a) of ``notes_to_chief/20260829_0906_LANE-GM-ASK-COO-standalone-
map-admits-a-scene-no-login-can-enter.md``.  The letter said the lane would
walk option (a) if no answer arrived by the next round; none did.  It does
NOT reverse ``COO-DECISION 20260829_0542``: that decision is about whether
an accepted entry is spent on use, and this is about whether the entry is
accepted at all.  If the COO rules otherwise, the reversal is this module
plus the two lines in ``login_scene_override._load_scene_id_map`` that call
it -- nothing else in the lane depends on the narrower admission.
"""
from __future__ import annotations

from .. import world_scene_travel
from .scene_catalog import is_known_scene_id


def login_entry_is_pinned(scene_id: int) -> bool:
    """Can the login path actually put a character INTO this scene?

    Asked through lane A's own registry loader, never through a copy of its
    data: ``world_scene_travel`` owns which scenes have a pinned entry and
    which are barred from being a login destination
    (``login_entry_allowed``, scene 17 today), and a second copy here would
    drift the moment lane A pins one more.

    Unknown-to-that-registry is False -- fail-closed, and deliberately the
    opposite default from ``is_position_persist_allowed``, because here an
    unknown destination is one the login path will refuse with no reply,
    which costs the account until someone with shell access deletes a
    config file.

    A registry this module cannot READ is also False, for the same reason:
    not being able to check is not a licence to admit.  The cost of that
    choice, said rather than implied: a broken registry file turns every
    login-scene override off (the loader that calls this raises, and
    ``consume_login_scene_override`` turns that into ``CONSUME_FAILED``, so
    logins land at their own stored row).  Nobody is locked out; the lane's
    convenience is what stops working.

    TWO REGISTRY CONDITIONS, not one, and the second was missing from the
    staging path this predicate came from.  ``world_scene_entry.resolve_entry``
    -- the call the login path actually makes -- refuses a destination for
    ``login_entry_allowed=False`` (``REFUSED_NOT_ALLOWED_AT_LOGIN``) AND for
    a pinned scene with no spawn position (``REFUSED_NO_PINNED_SPAWN``),
    home excepted because home arrives on the character's own row.  Asking
    only the first admitted a spawnless destination into exactly the same
    silent lockout this module exists to close.  No scene in the registry is
    spawnless today, so this half is a guard against lane A pinning one
    tomorrow rather than a fix for a live fault -- and
    ``tests/test_gm_login_scene_admission.py`` cross-checks the whole
    predicate against ``resolve_entry`` itself, scene by scene, so a third
    refusal reason added upstream shows up as a red test here instead of as
    a tester who cannot log in.
    """
    if type(scene_id) is not int:
        raise TypeError("scene_id must be an int")
    try:
        registry = world_scene_travel.load_scene_registry()
    except Exception:  # noqa: BLE001 - a registry this module cannot read is
        # not a reason to admit into the dark; it is a reason to refuse.
        return False
    return _target_is_admissible(registry, scene_id)


def _target_is_admissible(registry, scene_id: int) -> bool:
    try:
        target = registry[scene_id]
    except KeyError:
        return False
    if not target.login_entry_allowed:
        return False
    if target.n_id == world_scene_travel.HOME_SCENE_ID:
        return True
    return target.spawn is not None


def stageable_scene_ids() -> tuple[int, ...]:
    """Every scene a login-scene config may name today, in id order.

    ``GT-141`` prints this instead of telling a tester to pick any scene
    from the 330-row name table -- which is what the first version of that
    entry did, and what would have locked the test account out on the first
    try.  Since this round it is also the answer to "what may I put in the
    standalone login-scene map", because both config files are now held to
    the same rule.

    (The standalone file is named in prose rather than spelled out, on
    purpose: ``tests/test_gm_standalone_map_is_not_chat_writable.py`` scans
    for modules outside the reader that name it, and this module has no
    business being on that list -- it holds no write primitive at all.)
    """
    try:
        registry = world_scene_travel.load_scene_registry()
    except Exception:  # noqa: BLE001 - same reason as above
        return ()
    return tuple(
        sorted(
            target.n_id
            for target in registry.destinations
            if _target_is_admissible(registry, target.n_id)
        )
    )
