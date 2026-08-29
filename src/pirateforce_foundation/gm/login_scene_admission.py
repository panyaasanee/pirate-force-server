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

from types import MappingProxyType

from .. import world_scene_travel
from .scene_catalog import is_known_scene_id

# ---------------------------------------------------------------------------
# A SANCTIONED DESTINATION IS NOT AN ADMITTED ONE, and the whole value of the
# block below is that it keeps those two words apart.
#
# CHIEF-DECISION ``notes_to_chief/20260829_1603_CHIEF-DECISION-var2-test-path-
# scene126-registry-row-plus-gm-warp.md`` is addressed to lane A and to this
# lane, and asks for two halves:
#
#   item 1 (lane A)  add a registry row for scene 126, spawn (3050, 232, 90),
#                    pinned ``login_entry_allowed: false``
#   item 2 (this lane) add 126 to the set ``/warp`` accepts
#
# MEASURED ON main THIS ROUND, the two halves as written cannot both be true,
# and the measurement is the reason this block exists rather than a widened
# predicate:
#
# * ``/warp <scene_id>`` across scenes is not a wire teleport at all.  It
#   stages the account's NEXT LOGIN scene (``login_scene_stage``), which
#   ``runtime.py`` then resolves through ``world_scene_entry.resolve_entry``
#   with the default ``via_login=True``.  BOTH of its call sites default it,
#   measured on main this round rather than quoted: runtime.py:5635 (the
#   silenced probe that decides whether the override may apply at all) and
#   runtime.py:5706 (the call that actually places the character).  Neither
#   passes the parameter; ``grep -n via_login runtime.py`` returns one
#   comment and no argument.  The prose at runtime.py:5454 says the same
#   thing on purpose: "a destination pinned login_entry_allowed=False
#   (today: scene 17) still refuses via SceneEntryRefused below rather than
#   opening a side door around that guard."
# * ``resolve_entry`` refuses any destination pinned
#   ``login_entry_allowed: false`` when ``via_login`` is true
#   (world_scene_entry.py:390, ``REFUSED_NOT_ALLOWED_AT_LOGIN``).
#
# So a ``/warp 126`` that this lane simply ADMITTED would write a config entry
# that the very next login refuses -- the tester spends a relog and reaches
# nothing, which is the same shape of dead end ``REASON_NO_LOGIN_ENTRY``
# exists to prevent.  Widening ``login_entry_is_pinned`` is therefore refused
# here, on purpose: this lane does not own the login path's guard and will not
# route around it.  The one lawful shape is the one
# ``columbus_quest_dispatch`` already uses for a sanctioned non-login caller
# (``via_login=False``, columbus_quest_dispatch.py:464), and that call site is
# in ``runtime.py`` = chief's file = ``CORE-REQUEST-GM-038``.
#
# ~~Until that request lands, the ONLY thing this lane can honestly ship is a
# refusal that says WHICH half is missing ... Nothing in this block admits a
# scene~~ -- STRUCK, round ``znb56z``: ``CORE-REQUEST-GM-038`` LANDED
# (``pirate-force-server`` #281).  ``single_use_entry_is_admissible`` below
# does now admit a sanctioned scene, for the single-use map only, and
# ``sanctioned_barred_blocker`` is one of the two questions it asks.  The
# sentence above was accurate when written and stopped being accurate at that
# merge; it is struck rather than deleted because the REASONING above it --
# why this lane may not widen ``login_entry_is_pinned`` and may not route
# around the login path's own guard -- is unchanged and is what makes the
# widening lawful rather than a workaround.  What replaced the refusal is
# THE WIDENING, further down this file, which is narrower than it sounds:
# one blocker value, one map, one already-authorised operator.
#
# The blocker is still measured live rather than quoted from a doc that goes
# stale the hour lane A merges -- that part was right and is now load-bearing
# rather than merely diagnostic.
#
# ``TheSanctionSetGrantsNothingTests`` in
# ``tests/test_gm_login_scene_sanctioned_barred.py`` still holds and is still
# the guard, with its scope now said out loud: it pins that the sanction
# grants nothing UNDER THE PLAIN RULE -- ``login_entry_is_pinned`` and
# ``stageable_scene_ids``, which is exactly what the standalone map and the
# login path's own guard are judged by.  The single-use rule is pinned
# separately in ``tests/test_gm_login_scene_sanctioned_admission.py``, and the
# two files together are the statement that the widening reached one map and
# not the other.
#
# HOW AN ENTRY DIES, written the same round it was born, because pf-adversary
# asked and the map had no answer: an entry is RETIRED (deleted, with the
# round that deleted it named in the letter) the moment
# ``sanctioned_barred_blocker`` answers ``BLOCKER_NONE`` for it -- that is
# the scene becoming genuinely reachable, which is the whole point of having
# sanctioned it.  ``test_every_sanctioned_scene_is_one_the_predicate_refuses_
# today`` goes RED at exactly that moment so nobody has to remember.  An
# entry may NEVER be kept past that point: a sanction that outlives its
# blocker is a deny-list wearing a permit's name, and
# ``TheSanctionIsAskedOnlyAfterThePinRefusesTests`` is what stops the map
# from being read in that direction at all.
#
# [สมมติของสาย GM - รอ COO ยืนยัน] that "sanctioned by a chief letter" is the
# right key for this map at all.  The alternative -- a plain GM-lane allowlist
# with no letter behind each id -- is refused here because it would let this
# lane name its own exceptions to lane A's pin.  Asked in the round letter.
#
# THE PROXY IS A TYPO GUARD, NOT A CAPABILITY GUARD (pf-adversary D8), and
# the first version of this note claimed otherwise.  ``MappingProxyType``
# stops an in-process ``SANCTIONED_BARRED_SCENES[999] = ...`` from a module
# that imported it by accident.  It does NOT stop a rebind of this module
# attribute, and there is no client-reachable path to either -- both need
# code execution in this process, at which point this map is the least of
# anyone's problems.  It is worth having anyway because the map is small,
# public, and easy to reach for; it is NOT part of this lane's charter
# defence, and reading it as one would be reading a refusal string as a
# capability.
SANCTIONED_BARRED_SCENES = MappingProxyType(
    {
        # The VALUE is a citation and nothing else -- it is printed on a
        # console line beside the refusal, so it stays short enough to read
        # and ASCII enough for a cp874 terminal.  What the sanction means,
        # and what is still missing, is the blocker's job, not this string's.
        126: "CHIEF-DECISION 20260829_1603 item 2",
    }
)

# The scene is not named by any chief letter this lane holds.  The ordinary
# refusal stands and nothing below applies.
BLOCKER_NOT_SANCTIONED = "not_sanctioned"
# Lane A's registry could not be read at all.  Same fail-closed answer the
# rest of this module gives, and deliberately NOT reported as "lane A has not
# landed the row yet" -- those have different remedies (fix the file vs. wait
# for a merge) and reporting one as the other is what the last two rounds of
# this lane were spent undoing.
BLOCKER_REGISTRY_UNREADABLE = "registry_unreadable"
# Half one of the chief decision has not landed: no row for this scene.
BLOCKER_NO_REGISTRY_ROW = "lane_a_registry_row_missing"
# The lookup answered about a different scene.  Same tuple-slip guard
# `_target_is_admissible` carries, kept distinct because its remedy is
# "the registry or the caller's stand-in is wrong", not "wait for a merge".
BLOCKER_ROW_IS_NOT_THE_ROW_ASKED_FOR = "registry_row_identity_mismatch"
# The row exists but pins no arrival point, so there is nowhere to put the
# character even if the login path allowed it.
BLOCKER_NO_PINNED_SPAWN = "lane_a_row_has_no_pinned_spawn"
# Half two: the row is pinned and barred at login, so the stage would be
# written and then refused by `resolve_entry`.  The remedy is the request.
BLOCKER_LOGIN_PATH_BARS_IT = "login_path_bars_it_needs_core_request_gm_038"
# Nothing is blocking: the ordinary predicate already admits this scene, so
# the sanction is moot and should be retired from the map above.
BLOCKER_NONE = "none"


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


def is_sanctioned_barred_scene(scene_id: int) -> bool:
    """Does a chief letter this lane holds name this scene?

    A pure lookup in ``SANCTIONED_BARRED_SCENES``.  It says NOTHING on its
    own about whether the scene may be staged: ``login_entry_is_pinned`` is
    still the whole answer for the standalone map, and for the single-use
    map the answer is ``single_use_entry_is_admissible``, which asks this
    AND the blocker below and admits only on the pair.  This lookup alone
    has never granted anything and still does not.

    ``type(...) is not int`` rather than ``isinstance``, for the reason
    ``stage_login_scene`` gives: ``bool`` is a subclass of ``int``, and
    ``True`` would otherwise ask about scene 1.
    """
    if type(scene_id) is not int:
        return False
    return scene_id in SANCTIONED_BARRED_SCENES


def sanctioned_barred_provenance(scene_id: int) -> str | None:
    """The letter behind a sanctioned scene, or ``None``.

    Printed beside a refusal so an operator can go read the decision
    instead of taking this lane's word for it.
    """
    if not is_sanctioned_barred_scene(scene_id):
        return None
    return SANCTIONED_BARRED_SCENES[scene_id]


def sanctioned_barred_blocker(scene_id: int, *, scene_registry=None) -> str:
    """WHICH half of a sanctioned scene's route is missing, measured now.

    NO LONGER ONLY A DIAGNOSTIC, and the sentence that used to stand here
    ("it grants nothing, it is not consulted by ``login_entry_is_pinned``
    or ``stageable_scene_ids``") was true until ``CORE-REQUEST-GM-038``
    landed and is now only three-quarters true.  What is still exactly
    true: it is not consulted by ``login_entry_is_pinned`` or by
    ``stageable_scene_ids``, and a caller that treats a non-``BLOCKER_NONE``
    answer as permission has misread it.  What CHANGED:
    ``single_use_entry_is_admissible`` consults it and admits on exactly
    ONE of its answers (``BLOCKER_LOGIN_PATH_BARS_IT``), so this function
    is now load-bearing for the single-use map and a wrong word here is a
    wrong admission there, not merely a confusing console line.  Every
    OTHER answer it can give is still a refusal.

    Its whole job is otherwise unchanged -- to turn one refusal
    (``scene_has_no_login_entry``) into the sentence a person can act on:
    "lane A has not landed the row yet" and "chief has not wired
    ``via_login=False`` yet" are the SAME refusal today and have completely
    different remedies -- one is a merge to wait for, the other is a
    request to chase.

    The answer is measured against lane A's registry on every call, never
    cached and never copied into this lane, so it stops saying "row
    missing" the hour that row lands with no edit here.

    ``scene_registry`` means what it means everywhere else in this module,
    with one deliberate difference stated rather than implied: the refusal
    this blocker explains is produced by the DISK reading
    (``login_scene_stage`` asks the disk first and refuses there), so a
    caller explaining that refusal should pass nothing and get the disk
    answer.  The parameter exists so a caller can ask the same question
    about its own snapshot -- for a report, not for a stage.

    Order of the checks is the order of the remedies, outermost first:
    unreadable registry, missing row, wrong row, no spawn, barred at login.
    ``BLOCKER_NONE`` last means the ordinary predicate already admits this
    scene and the entry in ``SANCTIONED_BARRED_SCENES`` should be retired.
    The order differs from ``_target_is_admissible``'s on purpose (that one
    orders by cost), and the two are held to answering the SAME question by
    ``test_blocker_none_means_exactly_what_the_predicate_admits``.

    ONE CASE THIS VOCABULARY CANNOT NAME, said here rather than left for a
    tester to hit (pf-adversary D7, accepted as a gap and not half-fixed
    under time pressure).  This function is asked about ONE reading.  The
    running server holds TWO -- the file and the boot snapshot
    (``runtime.py:527``) -- and ``stage_login_scene``'s second branch
    refuses on the snapshot with the plain ``REASON_NO_LOGIN_ENTRY``, so no
    blocker is printed there at all.  A registry widened AFTER boot (lane A
    merges, the process is not restarted) therefore still produces one
    word, in exactly the case where the two readings disagree.  The remedy
    for it -- "restart the process" -- is not one of the five values above,
    and inventing a sixth that a single-reading function cannot actually
    measure would be worse than naming the hole.  Recorded in the round
    letter; a real fix has to compare the two readings, which is a
    different function than this one.
    """
    if not is_sanctioned_barred_scene(scene_id):
        return BLOCKER_NOT_SANCTIONED
    registry, trusted = _registry_to_ask(scene_registry)
    if registry is None:
        return BLOCKER_REGISTRY_UNREADABLE
    try:
        target = registry[scene_id]
    except KeyError:
        return BLOCKER_NO_REGISTRY_ROW
    except Exception:  # noqa: BLE001 - same rule as `_target_is_admissible`:
        # this module's own load may raise where a person can see it; a
        # caller-supplied object may not raise into a console line.
        if trusted:
            raise
        return BLOCKER_REGISTRY_UNREADABLE
    try:
        if getattr(target, "n_id", None) != scene_id:
            return BLOCKER_ROW_IS_NOT_THE_ROW_ASKED_FOR
        if scene_id != world_scene_travel.HOME_SCENE_ID and target.spawn is None:
            return BLOCKER_NO_PINNED_SPAWN
        if not target.login_entry_allowed:
            return BLOCKER_LOGIN_PATH_BARS_IT
    except Exception:  # noqa: BLE001 - see above
        if trusted:
            raise
        return BLOCKER_REGISTRY_UNREADABLE
    return BLOCKER_NONE


# ---------------------------------------------------------------------------
# THE WIDENING, AND THE ONE MAP IT MAY NOT REACH.
#
# `CORE-REQUEST-GM-038` landed (`pirate-force-server` #281, chief's letter
# `notes_to_chief/20260829_2222_CHIEF-TO-LANE-GM-gm-038-wired-plus-restore-
# rule-question.md`): `runtime.py` now resolves a sanctioned-barred scene with
# `via_login=False` -- the `columbus_quest_dispatch.py:464` shape -- so the
# refusal this module was built to prevent (`REFUSED_NOT_ALLOWED_AT_LOGIN` on
# every login and every retry, forever) no longer happens for that ONE set.
# The half of the route this lane owns is the admission below.
#
# THE WIDENING IS BOUND TO THE MAP THAT IS SPENT ON USE, and that is the whole
# safety argument rather than a scoping preference.  Chief's bypass is gated on
# `override_consumed_scene is not None` (runtime.py:5726), which is set on the
# CONSUMED outcome and on nothing else.  Only the GM-gated map
# (`gm_login_scene`) produces CONSUMED.  The standalone map is deliberately
# NEVER consumed (`COO-DECISION 20260829_0542`), so it yields
# STANDALONE_NOT_CONSUMED, `override_consumed_scene` stays None, the bypass
# stays False, and `resolve_entry` is asked with `via_login=True`.  A
# sanctioned scene admitted into THAT map would therefore be refused at login
# and refused identically on every retry, with the account unable to log in
# until somebody with shell access hand-edited a gitignored file -- the exact
# lockout this whole module exists to close, rebuilt by the fix for it.
#
# So: `single_use_entry_is_admissible` for the map that is spent,
# `login_entry_is_pinned` for the map that is not.  `login_scene_override.
# _load_scene_id_map` takes the rule as a REQUIRED argument rather than
# defaulting it, because a default is how a third map would quietly get the
# wrong one.  `tests/test_gm_login_scene_sanctioned_admission.py`'s
# `TheStandaloneMapNeverWidensTests` is what keeps the pairing true.
#
# WHAT THIS DOES NOT WIDEN, said plainly because the words are close enough to
# confuse: it does not widen `login_entry_is_pinned`, it does not widen
# `stageable_scene_ids`, it grants no GM status to anybody, and it does not
# let a client name its own destination -- `/warp` still runs behind
# `accounts.is_gm_account`, and the standalone map still grants a scene and
# nothing else.  It widens WHICH SCENE IDS one already-authorised operator may
# write into one already-gated file.


def single_use_entry_is_admissible(scene_id: int, *, scene_registry=None) -> bool:
    """May the SINGLE-USE (GM-gated) map name this scene?

    Plain admission, OR a sanctioned scene whose ONLY remaining blocker is
    the login-path bar that ``CORE-REQUEST-GM-038`` now bypasses for it.

    The second arm is deliberately the BLOCKER and not
    ``is_sanctioned_barred_scene`` alone: a sanction is a chief letter
    saying "this destination is wanted", never a statement that the route
    exists.  A sanctioned scene lane A has not pinned yet
    (``BLOCKER_NO_REGISTRY_ROW`` -- MEASURED on main this round for the only
    id in the map, 126) has no arrival point at all, and admitting it would
    write an entry the login path refuses for a reason chief's bypass does
    not touch: ``REFUSED_NO_PINNED_SPAWN`` is not
    ``REFUSED_NOT_ALLOWED_AT_LOGIN``.  So exactly one blocker value admits,
    and the other five refuse -- including ``BLOCKER_NONE``, which cannot
    reach the second arm at all because the first arm already answered True
    for it.

    THE ORDER IS NOT COSMETIC.  ``login_entry_is_pinned`` is asked first so
    that a non-``int`` raises ``TypeError`` out of it exactly as it does for
    the plain predicate -- this function's contract for a bad type is the
    plain one's, not ``is_sanctioned_barred_scene``'s silent ``False``.

    ``scene_registry`` means what it means everywhere in this module: pass
    the reading you will be JUDGED against, or pass nothing for a fresh
    disk read.  Both arms are asked with the same one, which is the point:
    a widening that consulted the snapshot for one arm and the disk for the
    other would be a third reader with a casting vote.
    """
    if login_entry_is_pinned(scene_id, scene_registry=scene_registry):
        return True
    if not is_sanctioned_barred_scene(scene_id):
        return False
    return (
        sanctioned_barred_blocker(scene_id, scene_registry=scene_registry)
        == BLOCKER_LOGIN_PATH_BARS_IT
    )


def single_use_stageable_scene_ids(*, scene_registry=None) -> tuple[int, ...]:
    """The way out for a refusal on the SINGLE-USE map, in id order.

    ``stageable_scene_ids`` is still the way out for the standalone map and
    still means what it meant.  This one exists because the two maps now
    accept different sets, and handing a refused operator the OTHER map's
    list is the failure this lane already paid for once in the other
    direction: a way out that names a destination the caller cannot reach
    is worse than no way out, because it sends them to try the one thing
    that cannot work.

    Built ON TOP of ``stageable_scene_ids`` rather than beside it, so the
    trusted/untrusted and unreadable-registry behaviour is inherited rather
    than reimplemented: a caller-supplied object this module cannot use
    yields ``()`` there, and every sanctioned id then fails the same way
    here, so the union is empty for the same reason and by the same rule.

    ``is_known_scene_id`` is re-applied to the sanctioned ids for the reason
    ``_admissible_ids`` gives: this tuple is PRINTED to a person, and an id
    with no name in the committed catalog is an instruction nobody can
    check.  It is not redundant with the reader's own name check -- that
    one guards what may be WRITTEN, this one guards what may be OFFERED.
    """
    base = stageable_scene_ids(scene_registry=scene_registry)
    widened = set(base)
    for scene_id in SANCTIONED_BARRED_SCENES:
        if scene_id in widened or not is_known_scene_id(scene_id):
            continue
        if single_use_entry_is_admissible(scene_id, scene_registry=scene_registry):
            widened.add(scene_id)
    return tuple(sorted(widened))


def disk_admits_under_rule(scene_id: int, *, single_use: bool) -> bool:
    """Would the DISK reading take this row, under the rule that refused it?

    ONE CALLER, and naming it rather than letting that caller pick a
    predicate itself is the whole point.  ``login_scene_consume.
    _refusal_cause`` asks a question none of the predicates above ask: not
    "may this be staged" but "does the disk DISAGREE with the snapshot this
    login was judged against" -- because those two have different remedies
    (edit the config vs. restart the server) and printing one for the other
    sends an operator to grep a file that is correct.

    ``scene_registry`` is deliberately absent rather than defaulted: the
    disk reading is the only reading this question has any use for, and a
    caller that could pass a snapshot here would be asking the snapshot
    whether it disagrees with itself.

    IT IS ALSO THE SEAM, said plainly because the alternative bit this lane
    once.  A diagnostic that shares a mockable name with the CONFIG READER
    cannot be broken in a test without also breaking the reader, so the test
    that pins "a diagnostic may never alter dispatch" would be pinning the
    reader's behaviour instead -- and, measured this round, a mock aimed at
    the probe escaped through ``_load_scene_id_map`` and out of
    ``consume_login_scene_override`` as a ``RuntimeError``.  This name has
    exactly one caller and no other reader depends on it, so a test may
    explode it and observe only what it meant to.
    """
    if single_use:
        return single_use_entry_is_admissible(scene_id)
    return login_entry_is_pinned(scene_id)


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
