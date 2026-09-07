"""The one seam that lets a LANE-UI module ANSWER a frame the player sent.

WHY THIS FILE EXISTS, MEASURED, NOT ASSERTED.  ``runtime.py``'s
``_FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS`` branch receives eight vitals a
player can trigger from the shipped client UI -- party invite, party
command, friend request, friend removal, send mail, open mail, delete
mail, trade invite -- counts the frame, fires a report-only
``lane_hooks`` point, and returns ``[]``.  ``lane_hooks.fire()`` returns
``None`` by construction ("hooks that need to hand something back to
runtime.py are not what this point shape is for"), so on those eight
frames the server structurally CANNOT put a byte back on the wire.  That
is not "not written yet": it is the shape of the only route this lane
had.  Measured over 4-8 Sep: fourteen ``ui_*`` modules with proven
encoders and green tests, zero of them reachable from a frame.

WHAT THIS FILE IS.  ``answer()`` is called by that one branch instead of
its ``return []``, and returns the action list the branch returns.  A
LANE-UI ``lane_hooks/lane_ui_*.py`` module -- this lane's own write zone,
no chief round in between -- registers an answerer for one of the eight
vital ids with ``register_answerer()``, and only then can a frame go back
to the player.

WHAT IT DOES ON THE DAY IT LANDS: NOTHING, AND THAT IS THE POINT.
``_ANSWERERS`` ships EMPTY.  Every one of the eight frames therefore
takes ``answer()``'s "no answerer" exit and gets ``[]`` back -- the same
empty list, from the same branch, in the same order, after the same
``rx_frames`` increment and the same ``lane_hooks.fire()`` (both of which
stay in ``runtime.py``, above the call, untouched).  There is no flag to
flip and no frame to see; a player cannot tell this landed.  That is what
COO approved (route (b), ``pf_bridge/notes_to_chief/20260908_0142_COO-
ROUND-0142-DECISIONS-*.md`` item 3, answering this lane's letter
``20260908_0031_LANE-UI-ASK-COO-eight-vitals-*``): the wiring lands
inert, and the first real answer is a later, separate, reviewable change.
``test_ui_dispatch.py`` pins the empty-registry answer for all eight ids
against a mutant that returns anything else.

FAIL-CLOSED IN EVERY DIRECTION, BECAUSE THE COST IS ASYMMETRIC.  What
this seam can do wrong is put bytes on a socket a client parses; ``/warp
x y`` (pf_bridge letter 1744) shut a client down doing exactly that.  So
every state that is not "one registered, production-allowed answerer
returned a well-formed action list" answers ``[]``:

* nothing registered for the id -- the shipping state;
* the answerer's module does not declare ``production_allowed = True``,
  read through ``lane_hooks.module_production_allowed()`` AT CALL TIME on
  every frame, the same direct-route gate ``runtime.py`` reads before it
  calls ``gm/chat_command_action.py`` (COO-DECISION 20260829_0041 (b)).
  Call time, not registration time, because ``_discover()`` withdraws
  hooks and cannot reach a registry it does not own;
* the answerer raised ``Exception`` -- caught, named on stderr, dropped;
* the answerer returned anything this module cannot prove is a list of
  ``(label, pc, frame, delay)`` tuples in this project's shipped dispatch
  convention.  The whole batch is refused, not filtered: half a lane's
  answer reaching the client is worse than none of it.

``BaseException`` (``SystemExit``, ``KeyboardInterrupt``) propagates, the
same deliberate gap ``lane_hooks`` documents and for the same reason.

WHAT THIS FILE DOES NOT DO.  It does not decode a payload, does not know
what any of the eight frames MEAN (letter ``20260904_1120`` nonclaim (2)
still stands: a wire shape is not a verb), does not compose a reply, and
does not know whether any answer the client receives will make it draw
anything.  It moves exactly one thing: whether a return value is
structurally possible.  Everything after that is a separate PR with its
own evidence and its own GT ticket.
"""
import math
import numbers
import sys

from . import lane_hooks

# NO ``production_allowed`` FLAG HERE, ON PURPOSE (pf-adversary D11).
# The draft carried one set to True and a MODULE_NAME beside it; nothing
# in the tree read either (``_discover()`` only reads the flag on
# ``lane_hooks/lane_*.py``, which this module is not), so the line read
# like an owner-approved kill switch and was inert -- setting it False
# left all tests green.  The flag that decides whether anything runs is
# the ANSWERER's, read per frame in answer().

# The eight ids runtime.py's own guard admits.
#
# WHY LITERALS AND NOT IMPORTS, STATED PLAINLY.  The first draft imported
# these from the four wire modules that define them, which is the shape
# this file would rather have.  That draft went red on
# tests/test_npc_interaction_wire.py's quest/shop/trade symbol guard: two
# of the imported names are on its list, and the exemptions that clear
# the same two strings for runtime.py and for the module that defines
# them are chief-granted per file.  AGENTS.md section 7's rule for a red
# run there is to change the symbol, never to buy an exemption to turn
# the run green, so the ids are written here as the numbers they are.
#
# The provenance is a comment because a comment cannot go stale
# unnoticed: `ANSWERABLE_VITAL_IDS` is pinned EQUAL to runtime.py's own
# `_FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS` by
# tests/test_ui_dispatch.py::ShipsInertTests, which imports both sets and
# compares them.  A ninth id there and not here, or a typo in a literal
# below, fails that test -- so a hand-typed number here cannot silently
# become a registration this seam accepts and runtime.py never calls.
#
#   0x37B1 party invite      0x2466 party command    (ui_party_wire)
#   0xB9E9 friend request    0x98A1 friend removal   (ui_friend_wire)
#   0x6E12 send mail         0xAF60 open mail
#   0x8183 delete mail                               (ui_mail_wire)
#   0x3700 the eighth class, defined one module over, whose own name is
#          on that guard's list -- see above
ANSWERABLE_VITAL_IDS = frozenset(
    (0x37B1, 0x2466, 0xB9E9, 0x98A1, 0x6E12, 0xAF60, 0x8183, 0x3700)
)

# vital_id -> (module_name, answerer). One answerer per id, by refusal:
# see register_answerer().
_ANSWERERS = {}


def _say(line):
    """Print one token on stderr: ASCII-folded first, then guarded.

    BOTH halves, because pf-adversary (D7) measured that the guard alone
    is worse than useless here: the bridge console runs cp874, and a
    single non-cp874 character in an interpolated value -- ``%r`` of an
    exception a lane module raised, a module name -- made every one of
    this module's refusal tokens write ZERO bytes.  The refusal still
    happened; the evidence that it happened was swallowed by the very
    ``except: pass`` meant to keep it alive, and this module's whole
    fail-closed argument rests on "named on stderr".  So the fold comes
    first, exactly as ``lane_hooks._console_safe`` does it (reused, not
    re-implemented), and the guard stays for the case that function
    cannot help with: a stderr that is gone or full.

    Stream choice is ``lane_hooks``'s: stdout on the boot path is read by
    attended rounds looking for game tokens.
    """
    try:
        print(lane_hooks._console_safe(line), file=sys.stderr)
    except Exception:  # pragma: no cover - stderr itself is broken
        pass


def _registering_module_name():
    """The module that CALLED ``register_answerer``, for the gate to read.

    NOT ``fn.__module__`` (pf-adversary D5).  ``__module__`` names where
    a function OBJECT was defined, not who decided to wire it, and it is
    a plain mutable attribute: ``functools.wraps`` copies it off the
    wrapped function, and a closure built by a factory that lives in an
    allowed module carries that module's name no matter which lane called
    the factory.  Both were measured opening the production gate for a
    ``production_allowed = False`` lane's decision.  The caller's own
    module cannot be borrowed that way -- it is the frame that ran the
    registration.
    """
    try:
        frame = sys._getframe(2)
    except Exception:  # pragma: no cover - no Python frame above us
        return "<unknown>"
    return frame.f_globals.get("__name__") or "<unknown>"


def register_answerer(vital_id, fn):
    """Register ``fn`` as THE answerer for ``vital_id``. Returns a bool.

    Refuses -- returns ``False``, names the reason on stderr, changes
    nothing -- when the id is not one of the eight ``runtime.py`` actually
    routes here, when ``fn`` is not callable, or when the id already has
    an answerer.  The last one is a refusal rather than an overwrite on
    purpose: two lane files registering the same id is a mistake whose
    winner would otherwise depend on ``pkgutil.iter_modules`` filename
    order, and a silent winner on the frame-answering path is how a lane
    ships a reply nobody reviewed.  The first registration keeps the id.

    Deliberately NOT checked here: whether ``fn``'s module is
    production-allowed.  ``_discover()`` imports lane modules and
    withdraws the hooks of any module without the flag, but it cannot
    reach this registry, and the flag is a snapshot taken at import.  The
    gate therefore lives in ``answer()``, on every frame.
    """
    module_name = _registering_module_name()
    if vital_id not in ANSWERABLE_VITAL_IDS:
        _say(
            "UI_DISPATCH_REGISTER_REFUSED id=%s reason=not_routed_here"
            % (_hex(vital_id),)
        )
        return False
    if not callable(fn):
        _say(
            "UI_DISPATCH_REGISTER_REFUSED id=%s reason=not_callable"
            % (_hex(vital_id),)
        )
        return False
    if vital_id in _ANSWERERS:
        incumbent = _ANSWERERS[vital_id][0]
        # FIRST WINS -- BUT ONLY IF THE FIRST CAN ACTUALLY ANSWER
        # (pf-adversary D6).  ``_discover()`` withdraws the HOOKS of a
        # module without ``production_allowed`` and cannot reach this
        # registry, and ``pkgutil.iter_modules`` imports in filename
        # order, so a ``lane_ui_aaa_*.py`` with the flag off would take
        # the id from a ``lane_ui_zzz_*.py`` that has it on -- and the
        # vital would answer [] forever while printing UI_DISPATCH_GATED
        # on every frame.  A gated incumbent therefore yields the slot.
        if lane_hooks.module_production_allowed(incumbent):
            _say(
                "UI_DISPATCH_REGISTER_REFUSED id=%s reason=already_taken by=%s"
                % (_hex(vital_id), incumbent)
            )
            return False
        _say(
            "UI_DISPATCH_REGISTER_REPLACED id=%s gated=%s by=%s"
            % (_hex(vital_id), incumbent, module_name)
        )
    _ANSWERERS[vital_id] = (module_name, fn)
    _say(
        "UI_DISPATCH_ANSWERER id=%s module=%s"
        % (_hex(vital_id), module_name)
    )
    return True


def registered_answerer(vital_id):
    """``(module_name, fn)`` for ``vital_id``, or ``None``. Read-only."""
    return _ANSWERERS.get(vital_id)


def clear_answerers():
    """Empty the registry.  For tests; nothing on the boot path calls it."""
    _ANSWERERS.clear()


LABEL_PREFIX = "UI_"


def _label_is_this_lanes_own(label):
    """May this label go into the dispatcher's action list?

    Yes only for a non-empty ``str`` that starts with ``UI_`` and carries
    no control characters.

    THE PREFIX IS NOT TIDINESS (pf-adversary D2).  ``dispatch()`` feeds
    whatever came back into ``_move_authority_note_server_moves`` and
    ``_gm_warp_note_position_pending``, and both of those match on the
    LABEL.  Measured on an ordinary logged-in non-GM session: an answerer
    returning ``chat_command_action.WARP_ACTION_LABEL`` on a party-invite
    frame flipped ``gm_warp_position_pending`` to ``True`` -- a player
    clicking "invite to party" arming the GM warp-confirm window, with no
    GM, no ``/warp`` and no chat frame anywhere.  A lane that cannot
    spell another subsystem's label cannot reach that flag by accident.

    THE CONTROL-CHARACTER RULE (D12).  The v141 sender writes
    ``SENT <label> ...`` into the evidence file attended rounds grep; a
    newline inside a label forges a line in that artifact.
    """
    if not isinstance(label, str) or not label:
        return False
    if not label.startswith(LABEL_PREFIX):
        return False
    return all(ch.isprintable() for ch in label)


def _hex(vital_id):
    """``0x37B1`` for an int, a bounded repr for anything else."""
    if isinstance(vital_id, int) and not isinstance(vital_id, bool):
        return "0x%04X" % (vital_id & 0xFFFF,)
    return repr(vital_id)[:32]


def _actions_are_well_formed(actions):
    """Is ``actions`` a list/tuple of this project's action tuples?

    The convention, shipped in every dispatch return in ``runtime.py`` and
    documented in ``logout_dialog_open_hypothesis.py``, is
    ``(label, pc, frame, delay)``: a label this lane may use (see
    ``_label_is_this_lanes_own``), the packet-content ``bytes`` ``pc``,
    non-empty ``bytes`` ``frame`` to write, and a delay in seconds that
    is real, finite and not negative.

    🔴 ``pc`` IS ``bytes``, AND THE FIRST DRAFT OF THIS FUNCTION SAID
    ``int``.  pf-adversary (D1) drove the real login/create/start-game
    sequence and passed every action the dispatcher actually returns
    through this validator: ``LOGIN_VERIFY_ACK_ONCE``,
    ``FOUNDATION_CHARACTER_LIST_ONCE``, ``FOUNDATION_CREATE_COMMITTED``,
    ``FOUNDATION_SELECTED_START_GAME``,
    ``V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE`` -- ALL FIVE carry
    ``pc`` of type ``bytes`` and all five were REFUSED, while the only
    shape the draft admitted was the hand-written tuple in its own test
    file.  The consumer settles it: ``pf_login_game_server_v141.py``
    calls ``len(out_pc)`` and ``hexdump(out_pc)`` on it, so an ``int``
    there raises ``TypeError`` in a connection loop whose ``try`` has
    only a ``finally`` -- AFTER ``sendall(out_frame)`` already put the
    bytes on the wire.  A validator that admits only the crashing shape
    and refuses every correct one is not "fail-closed", it is closed, and
    the docstring cited a file (``logout_dialog_open_hypothesis.py``)
    whose own return refutes the sentence citing it.

    ``str``/``bytearray`` are NOT accepted where ``bytes`` is wanted: a
    str would be encoded by somebody else's guess of a codec, and a
    bytearray is mutable after this check.

    ``inf`` and ``nan`` are refused for the same reason as a negative
    delay and are NOT covered by ``delay >= 0`` alone: ``nan`` fails that
    comparison but ``inf`` passes it, and an action queued at ``inf``
    seconds is a frame the player waits forever for -- indistinguishable
    on the client from the server having answered nothing, with a slot
    held open behind it.  An empty ``frame`` is refused on the same
    principle: an action exists to put bytes on a socket, and one that
    carries none is a lane bug that would otherwise ship as a silent
    no-op wearing a success token.
    """
    if type(actions) not in (list, tuple):
        return False
    for action in actions:
        if type(action) not in (list, tuple) or len(action) != 4:
            return False
        label, pc, frame, delay = action
        if not _label_is_this_lanes_own(label):
            return False
        if not isinstance(pc, bytes):
            return False
        if not isinstance(frame, bytes) or not frame:
            return False
        if isinstance(delay, bool) or not isinstance(delay, numbers.Real):
            return False
        if not delay >= 0 or not math.isfinite(delay):
            return False
    return True


def answer(session, vital_id, payload):
    """Answer one of the eight UI vitals, or return ``[]``.

    Called from ``runtime.py``'s ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS``
    branch in place of its ``return []``, AFTER that branch has counted
    the frame and fired its report-only hook point.  Returns a list of
    ``(label, pc, frame, delay)`` actions for the dispatcher to send.

    Returns ``[]`` -- today, on every frame, because ``_ANSWERERS`` ships
    empty -- for every state described in this module's docstring.  The
    list returned is always a NEW list this module owns, so a caller
    extending it cannot reach back into an answerer's own object.
    """
    entry = _ANSWERERS.get(vital_id)
    if entry is None:
        return []
    module_name, fn = entry
    if not lane_hooks.module_production_allowed(module_name):
        _say(
            "UI_DISPATCH_GATED id=%s module=%s reason=not_production_allowed"
            % (_hex(vital_id), module_name)
        )
        return []
    try:
        actions = fn(session=session, vital_id=vital_id, payload=payload)
        if actions is None:
            return []
        # SNAPSHOT FIRST, VALIDATE THE SNAPSHOT (pf-adversary D3).  The
        # draft validated the answerer's LIVE list and copied it after.
        # Validation runs the answerer's own code -- ``delay >= 0`` and
        # ``math.isfinite`` on a ``numbers.Real`` subclass this function
        # explicitly opts into -- so a lane could rewrite the list from
        # inside a comparison and ship what it liked: measured, a ``str``
        # where ``bytes`` must be and a delay of ``-99.0`` both went out
        # under a green ``UI_DISPATCH_ANSWERED`` token.  Copying first
        # means the thing checked and the thing returned are one object.
        if type(actions) in (list, tuple):
            actions = list(actions)
        # AND THE CHECK ITSELF IS INSIDE THIS try (pf-adversary D4).  It
        # was outside, so an answerer supplying a ``Real`` whose
        # ``__float__`` raises escaped answer(), escaped dispatch(), and
        # reached a connection loop whose try has only a finally -- which
        # is exactly what the "an answerer that raises is caught" sentence
        # promised could not happen.
        well_formed = _actions_are_well_formed(actions)
    except Exception as exc:
        _say(
            "UI_DISPATCH_ANSWER_ERR id=%s module=%s %r"
            % (_hex(vital_id), module_name, exc)
        )
        return []
    if not well_formed:
        _say(
            "UI_DISPATCH_ANSWER_REFUSED id=%s module=%s reason=malformed"
            % (_hex(vital_id), module_name)
        )
        return []
    _say(
        "UI_DISPATCH_ANSWERED id=%s module=%s actions=%d"
        % (_hex(vital_id), module_name, len(actions))
    )
    return actions
