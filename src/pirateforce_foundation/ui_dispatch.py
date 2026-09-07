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
import numbers
import sys

from . import lane_hooks
from .ui_friend_wire import (
    COMMUNITY_REMOVE_FRIEND_VITAL_ID,
    COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
)
from .ui_mail_wire import (
    COMMUNITY_DELETE_MAIL_VITAL_ID,
    COMMUNITY_GET_MAIL_CONTENT_VITAL_ID,
    COMMUNITY_SEND_MAIL_VITAL_ID,
)
from .ui_party_wire import PARTY_CMD_VITAL_ID, PARTY_INVITE_VITAL_ID
from .ui_trade_wire import TRADE_INVITE_VITAL_ID

# This module composes no frame and reads no store row of its own: with an
# empty registry it is a function that returns []. The flag that decides
# whether anything runs is the ANSWERER's, read per frame in answer().
production_allowed = True

MODULE_NAME = "ui_dispatch"

# The eight ids runtime.py's own guard admits, imported from the four wire
# modules that define them rather than retyped -- a ninth id typed here by
# hand would be a registration this seam accepts and runtime.py never
# calls, which is a silently dead answerer, the exact failure the branch
# comment upstairs spends ten lines avoiding for hook points.
ANSWERABLE_VITAL_IDS = frozenset(
    (
        PARTY_INVITE_VITAL_ID,
        PARTY_CMD_VITAL_ID,
        COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
        COMMUNITY_REMOVE_FRIEND_VITAL_ID,
        COMMUNITY_SEND_MAIL_VITAL_ID,
        COMMUNITY_GET_MAIL_CONTENT_VITAL_ID,
        COMMUNITY_DELETE_MAIL_VITAL_ID,
        TRADE_INVITE_VITAL_ID,
    )
)

# vital_id -> (module_name, answerer). One answerer per id, by refusal:
# see register_answerer().
_ANSWERERS = {}


def _say(line):
    """Print one token on stderr, never raising if stderr itself is gone.

    Same guarded-print shape and same stream choice as ``lane_hooks``:
    stdout on this project's boot path is read by attended rounds looking
    for game tokens, and a server started as ``python app.py 2>log`` on a
    full volume must not die inside a diagnostic.
    """
    try:
        print(line, file=sys.stderr)
    except Exception:  # pragma: no cover - stderr itself is broken
        pass


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
        _say(
            "UI_DISPATCH_REGISTER_REFUSED id=%s reason=already_taken by=%s"
            % (_hex(vital_id), _ANSWERERS[vital_id][0])
        )
        return False
    module_name = getattr(fn, "__module__", "") or "<unknown>"
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


def _hex(vital_id):
    """``0x37B1`` for an int, a bounded repr for anything else."""
    if isinstance(vital_id, int) and not isinstance(vital_id, bool):
        return "0x%04X" % (vital_id & 0xFFFF,)
    return repr(vital_id)[:32]


def _actions_are_well_formed(actions):
    """Is ``actions`` a list/tuple of this project's action tuples?

    The convention, shipped in every dispatch return in ``runtime.py`` and
    documented in ``logout_dialog_open_hypothesis.py``, is
    ``(label, pc, frame, delay)``: a non-empty ``str`` label, an ``int``
    packet counter, ``bytes`` to write, and a non-negative real delay in
    seconds.  ``bool`` is rejected where an int is wanted (it is an int in
    Python and never a real packet counter), and ``str``/``bytearray`` are
    NOT accepted as ``bytes``: a str would be encoded by somebody else's
    guess of a codec, and a bytearray is mutable after this check.
    """
    if type(actions) not in (list, tuple):
        return False
    for action in actions:
        if type(action) not in (list, tuple) or len(action) != 4:
            return False
        label, pc, frame, delay = action
        if not isinstance(label, str) or not label:
            return False
        if not isinstance(pc, int) or isinstance(pc, bool):
            return False
        if not isinstance(frame, bytes):
            return False
        if isinstance(delay, bool) or not isinstance(delay, numbers.Real):
            return False
        if not delay >= 0:
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
    except Exception as exc:
        _say(
            "UI_DISPATCH_ANSWER_ERR id=%s module=%s %r"
            % (_hex(vital_id), module_name, exc)
        )
        return []
    if actions is None:
        return []
    if not _actions_are_well_formed(actions):
        _say(
            "UI_DISPATCH_ANSWER_REFUSED id=%s module=%s reason=malformed"
            % (_hex(vital_id), module_name)
        )
        return []
    _say(
        "UI_DISPATCH_ANSWERED id=%s module=%s actions=%d"
        % (_hex(vital_id), module_name, len(actions))
    )
    return list(actions)
