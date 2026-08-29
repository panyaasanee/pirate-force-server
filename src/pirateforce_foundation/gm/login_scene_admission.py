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

~~[สมมติของสาย GM - รอ COO ยืนยัน]~~ RULED, round 7gplcy:
``notes_to_chief/20260829_0941_COO-DECISION-standalone-map-refuses-an-
unreachable-scene-at-load.md`` approves option (a).  Refusing at ADMISSION
rather than at use is option (a) of ``notes_to_chief/20260829_0906_LANE-GM-
ASK-COO-standalone-map-admits-a-scene-no-login-can-enter.md``.  The letter
said the lane would walk option (a) if no answer arrived by the next round;
none had when it was written, and the ruling arrived while the round that
built it was being closed unmerged by the gate.  It does
NOT reverse ``COO-DECISION 20260829_0542``: that decision is about whether
an accepted entry is spent on use, and this is about whether the entry is
accepted at all.  If the COO rules otherwise, the reversal is this module
plus the two lines in ``login_scene_override._load_scene_id_map`` that call
it -- nothing else in the lane depends on the narrower admission.
"""
from __future__ import annotations

from .. import world_scene_travel
from .scene_catalog import is_known_scene_id


def login_entry_is_pinned(scene_id: int, *, scene_registry=None) -> bool:
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

    ``scene_registry`` -- WHICH READING OF THE REGISTRY THIS ANSWER IS FOR.
    Left ``None`` -- the default, and what this lane's own tests pass -- the
    pin file is read FRESH, and that is the reading this whole module was
    written against.  It is not the reading that places the character.  ``runtime.py`` loads the registry
    ONCE at boot (``runtime.py:527``) and every login is placed by that
    snapshot, so a disk reading and a placement reading are the AGE OF THE
    PROCESS apart -- chief measured this and gated the login path on the
    snapshot in ``CHIEF-REPLY`` 2026-08-29T12:21+07:00 item 3.

    Passing the caller's own registry makes this predicate answer FOR THAT
    SNAPSHOT instead of adding a reading of its own.  That is the entire
    point, and it is the opposite of what a casual reader assumes a new
    kwarg does: it does not add a third reader of the registry, it REMOVES
    this module as an independent reader for the caller that supplies one.
    A third reader free to disagree with the two that already exist is the
    defect this lane reported in ``CORE-REQUEST-GM-034``; chief's answer was
    to use ``resolve_entry`` itself at the login call site rather than write
    a private predicate, and this parameter is the same answer for the
    STAGING side, where the refusal can still reach a person.

    WIRED AT ALL THREE CALL SITES, which is a change of state and not a
    change of design: ``CORE-REQUEST-GM-036`` asked for the login consume,
    the chat command, and the put-back after a refused login (see
    ``login_scene_stage.restore_login_scene`` for why an undo judged against
    the other reading refuses and strands the entry it was called to
    remove).  Chief answered all three in ``CHIEF-REPLY``
    2026-08-29T15:16+07:00 and they reached main as ``pirate-force-server``
    #264, pinned from the runtime side by
    ``tests/test_gm_login_scene_registry_wiring_in_runtime.py``, which is
    RED on a tree where the kwarg is dropped at any one of the three.

    An earlier revision said "NOT WIRED BY ANY CALLER IN THIS COMMIT ...
    every caller is None"; it was accurate when written and stopped being
    accurate at that merge.  What is still true, and is the part worth
    keeping: ``None`` is still the default and still adds a fresh read, so
    a caller that does not pass one is NOT judged against the snapshot.
    """
    if type(scene_id) is not int:
        raise TypeError("scene_id must be an int")
    registry, trusted = _registry_to_ask(scene_registry)
    if registry is None:
        return False
    return _target_is_admissible(registry, scene_id, trusted=trusted)


def _registry_to_ask(scene_registry):
    """``(registry, trusted)`` -- which reading to use, and how far to trust it.

    ``trusted`` is True only for this module's OWN load, and it decides how
    wide the guards downstream may be.  Widening them for every caller was
    a measured regression (pf-adversary, round 7hfrt0, D3): with
    ``scene_registry=None`` a genuinely bent row used to RAISE out of here,
    and a wide catch turned that into "no scene is stageable" -- a lane that
    silently stops working instead of a fault somebody has to look at.  So
    the file path keeps exactly the catch it had before this parameter
    existed, and only a caller-supplied object -- which this module cannot
    vouch for -- gets the wide one.

    A registry this module cannot READ is ``(None, ...)`` for the reason
    ``login_entry_is_pinned``'s docstring gives: not being able to check is
    not a licence to admit.

    NO SHAPE GATE FOR THE CALLER'S OBJECT, and its absence is deliberate
    rather than an omission.  This round wrote one -- a duck-type check
    refusing any object without an iterable ``destinations`` -- and then
    measured that deleting it again left every test green, because the
    identity check in ``_target_is_admissible`` (the row that comes back
    must BE the row that was asked for) already refuses every shape the
    gate did: the ``.destinations`` tuple slip it was written for, and a
    ``MagicMock`` that answers everything truthily.  A second guard no test
    can tell apart from the first is a claim with no evidence behind it,
    and it invites the next reader to believe the wrong one is load-
    bearing.  One guard, measured.

    What that means for a caller, said plainly: a ``scene_registry`` this
    module cannot use does NOT fall back to the file.  It answers False for
    every scene and an empty way out -- the caller asked for a specific
    reading to be honoured, and quietly reading the FILE instead would
    answer a question nobody asked, in the exact direction (disk is the
    wider of the two) this parameter exists to stop.  A wiring fault costs
    the lane's convenience, never the guarantee.
    """
    if scene_registry is not None:
        return scene_registry, False
    try:
        return world_scene_travel.load_scene_registry(), True
    except Exception:  # noqa: BLE001 - a registry this module cannot read is
        # not a reason to admit into the dark; it is a reason to refuse.
        return None, True


def _target_is_admissible(registry, scene_id: int, *, trusted: bool) -> bool:
    """Three registry conditions and one identity check.

    THE IDENTITY CHECK IS NOT PARANOIA (pf-adversary, round 7hfrt0, D1).
    ``SceneRegistry.__getitem__`` finds the row whose ``n_id`` matches, so
    with the real class ``target.n_id == scene_id`` is free.  Nothing else
    guarantees it, and a POSITIONALLY indexed stand-in answers about a
    different scene entirely -- admitting a barred destination on an
    admissible row's evidence, which is worse than any refusal.  So the row
    that comes back has to say it is the row that was asked for, and the
    check costs one comparison on the real object.

    ``trusted`` narrows or widens the catch, and the narrow case is the
    important one: for this module's own load the behaviour is EXACTLY what
    it was before the ``scene_registry`` parameter existed -- ``KeyError``
    is the ordinary "not pinned", and a malformed row still raises, where a
    person can see it.  For a caller-supplied object nothing may escape:
    ``runtime.py`` swallows ``TypeError`` from this lane's call site into a
    silent ``None`` (chief measured it, CHIEF-REPLY 2026-08-29T12:21+07:00
    item 2), so an exception is not the loud failure it looks like.

    ``Exception`` and not ``BaseException``, said rather than left implied:
    a ``KeyboardInterrupt`` or ``SystemExit`` raised by a caller-supplied
    object still escapes.  That is deliberate -- those two are not a
    registry misbehaving, they are the process being told to stop -- and it
    means the promise here is "no ORDINARY error escapes", not "nothing
    escapes".
    """
    try:
        target = registry[scene_id]
    except KeyError:
        # The ordinary answer: this scene is not pinned.
        return False
    except Exception:  # noqa: BLE001 - see the docstring
        if trusted:
            raise
        return False
    try:
        if getattr(target, "n_id", None) != scene_id:
            # Asked about one scene, answered about another.  See the
            # docstring: this is the tuple-slip guard, and it also refuses
            # any stand-in whose lookup does not agree with its rows.
            return False
        if not target.login_entry_allowed:
            return False
        if scene_id == world_scene_travel.HOME_SCENE_ID:
            return True
        return target.spawn is not None
    except Exception:  # noqa: BLE001 - same reason
        if trusted:
            raise
        return False


def stageable_scene_ids(*, scene_registry=None) -> tuple[int, ...]:
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

    ``scene_registry`` is the same parameter ``login_entry_is_pinned`` takes
    and means the same thing; see that docstring.  It matters MORE here than
    there, because this tuple is the WAY OUT a refused tester is handed: a
    way out computed from the disk reading can name a scene the running
    process would refuse, which is a worse answer than no answer -- it sends
    the tester to try the one destination that cannot work.  When the
    refusal itself came from the snapshot, the way out has to come from the
    same snapshot or the two contradict each other.

    An empty tuple can now mean a third thing, and it is said here rather
    than left for a reader to discover: not only "the registry could not be
    read" and "nothing is admissible", but also "a caller passed an object
    that is not a registry".  All three are the same instruction to a
    caller -- offer no destinations -- and none of them may print a name.
    """
    registry, trusted = _registry_to_ask(scene_registry)
    if registry is None:
        return ()
    if trusted:
        # EXACTLY the pre-parameter behaviour for the file path: a bent row
        # raises where somebody can see it, rather than becoming a silent
        # empty way out (pf-adversary, round 7hfrt0, D3).
        return _admissible_ids(registry, trusted=True)
    try:
        return _admissible_ids(registry, trusted=False)
    except Exception:  # noqa: BLE001 - a caller-supplied object that is not
        # a registry offers no destinations; it does not raise into a
        # console line or a chat refusal.  The guard is around the WHOLE
        # walk, not around the `.destinations` access alone: `target.n_id`
        # is read twice per row inside it and either read can be the one
        # that raises on a foreign object.
        return ()


def _admissible_ids(registry, *, trusted: bool) -> tuple[int, ...]:
    return tuple(
        sorted(
            target.n_id
            for target in registry.destinations
            if _target_is_admissible(registry, target.n_id, trusted=trusted)
            # A destination lane A pins that this lane's committed name
            # catalog does not know is not a scene this lane may offer: the
            # console line and `GT-141` both PRINT this tuple to a human,
            # and an id with no name in it is an instruction nobody can
            # check.  Dropping this filter left the whole lane suite green
            # (mutation M10) until `TheAdmissibleSetIsAlsoNamedTests` --
            # and, measured the hard way, that mutation reached a pushed
            # commit of this file before that test existed.
            and is_known_scene_id(target.n_id)
        )
    )
