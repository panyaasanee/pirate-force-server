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
had.  Measured at HEAD: 18 ``ui_*_wire.py`` modules with proven encoders
and green tests; 14 of them are named in neither ``runtime.py`` nor
``app.py``, and the other 4 are named only so the report-only hooks can
DECODE what arrives.  So five of them DO already run on the production
path (pf-adversary D10 measured exactly which).  What none of the 18 can
do is put a byte BACK on the wire.  An earlier draft of this sentence
said "zero of them reachable from a frame", which is false: it confused
inbound decode, which happens today, with answering, which does not.

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
  answer reaching the client is worse than none of it;
* an action carries a label, an id or a byte count that
  ``_OUTBOUND_FRAME_SHAPES`` -- the reviewed outbound registry this file
  owns (COO-DECISION 20260908_1142 item 7, route (b)) -- does not name.
  A lane with the flag set may answer, but only in a shape a human
  reviewed into this file.

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
import collections
import math
import numbers
import re
import sys

# NO ``from . import lane_hooks`` HERE (pf-adversary round 2, R4).
# ``runtime.py`` imports this module at line 30 and ``lane_hooks`` at
# line 47, so a module-level import here pulled ``lane_hooks`` -- and
# therefore ``_discover()`` -- in while THIS module was still half-built.
# Measured: a ``lane_ui_*.py`` that calls ``register_answerer`` at import
# time died with ``partially initialized module ... has no attribute
# 'register_answerer'``, was swallowed as ``LANE_HOOK_DISCOVERY ...
# IMPORT_FAILED``, and the vital answered [] forever -- while
# ``tests/test_ui_dispatch.py``, which happens to import ``lane_hooks``
# first, saw the working order and stayed green.  The first real answerer
# would have shipped dead under a green suite.  Imported inside the three
# functions that need it instead.

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
        from . import lane_hooks  # noqa: PLC0415 - see the header comment

        print(lane_hooks._console_safe(line), file=sys.stderr)
    except Exception:  # pragma: no cover - stderr itself is broken
        pass


_LANE_PACKAGE = "pirateforce_foundation.lane_hooks."


def _module_name_of_namespace(namespace):
    """``sys.modules`` key whose module dict IS ``namespace``, or ``None``.

    BY IDENTITY, NOT BY THE FRAME'S ``__name__`` (pf-adversary round 2,
    R2).  ``frame.f_globals["__name__"]`` is a plain dict entry the
    calling module owns: measured, one line -- ``__name__ = "<an allowed
    module>"`` -- in a real ``production_allowed = False`` lane file
    opened the gate for it and printed the innocent module's name in the
    token.  The KEY in ``sys.modules`` is set by the import machinery,
    not by the file.  A namespace that more than one key maps to (an
    alias a module inserted for itself) is refused rather than guessed
    at, and a non-str key cannot arise from import.
    """
    found = [
        name for name, module in list(sys.modules.items())
        if getattr(module, "__dict__", None) is namespace
        and isinstance(name, str)
    ]
    if len(found) != 1:
        return None
    return found[0]


def _gating_module_names(fn):
    """EVERY lane module the gate must clear for this registration.

    ONE FRAME IS NOT THE REGISTRAR (pf-adversary round 3, D1).  The
    previous version of this file read a fixed ``sys._getframe(2)`` and
    its docstring claimed a caller's module "cannot be borrowed that
    way".  It can, by the most ordinary factoring there is.  Measured: a
    ``lane_ui_helpers.py`` with ``production_allowed = True`` exposing
    ``def wire(vital_id, fn): return register_answerer(vital_id, fn)``,
    called from a ``lane_ui_experimental.py`` with ``production_allowed =
    False``, registered successfully, printed the helper's innocent name
    in the token, and put the experimental lane's frame on the wire --
    verbatim the R2 symptom this file said it had closed.  A decorator
    factory, a ``functools.partial(register_answerer)`` and a ``for
    vital_id, fn in TABLE: helpers.wire(...)`` loop all have that shape.

    So the gate stops asking WHO registered and asks WHO TOOK PART: every
    frame on the registration stack that belongs to a lane module, plus
    ``fn``'s own defining module when that is a lane module.  All of them
    must be production-allowed for a frame to go out (``answer()``).
    Borrowing an allowed helper no longer launders the decision, because
    the borrower's frame is still on the stack under it.

    ``fn.__module__`` is included here but is NOT trusted alone -- it is a
    plain mutable attribute, ``functools.wraps`` copies it off the wrapped
    function, and a closure built by a factory in an allowed module
    carries that module's name whoever called the factory (round 2, D5).
    Adding it can only ever ADD a module the gate must clear, never
    remove one, so a forged value cannot open the gate; the worst a lie
    achieves is closing the gate on its own registration.
    """
    names = []

    def add(name):
        # THE SAME RULE ``_discover()`` USES, NOT JUST THE PACKAGE PREFIX
        # (pf-adversary round 4, D-E).  ``_discover()`` imports only files
        # whose stem starts with ``lane_``, so a helper factored out into
        # ``lane_hooks/ui_answer_impl.py`` is never given a
        # ``_PRODUCTION_ALLOWED`` entry -- and the prefix-only test still
        # put it in the gate, which then reported
        # ``reason=not_production_allowed`` about a switch nobody had ever
        # asked for.  Measured: a correct ``production_allowed = True``
        # lane whose answerer lived in such a file was gated forever, and
        # writing the flag INTO that file did not help, because nothing
        # imports it.  A module discovery cannot reach is not a lane whose
        # flag can be read, so it is not a lane this gate can judge.
        if not isinstance(name, str) or not name.startswith(_LANE_PACKAGE):
            return
        if not name[len(_LANE_PACKAGE):].startswith("lane_"):
            return
        if name not in names:
            names.append(name)

    depth = 2
    while True:
        try:
            frame = sys._getframe(depth)
        except Exception:  # no more Python frames above us
            break
        add(_module_name_of_namespace(frame.f_globals))
        depth += 1
    add(getattr(fn, "__module__", None))
    return tuple(names)


def _registering_module_name():
    """The module that CALLED ``register_answerer``, for the token to name.

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
    name = _module_name_of_namespace(frame.f_globals)
    return "<unknown>" if name is None else name


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
    gating = _gating_module_names(fn) if callable(fn) else ()
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
        from . import lane_hooks  # noqa: PLC0415 - see the header comment

        # THE WHOLE INCUMBENT GATE, NOT THE REGISTRAR NAME ALONE
        # (pf-adversary round 4, D-D).  ``answer()`` gates on
        # ``(module_name,) + gating``; this branch asked only about
        # ``module_name``, so the two went out of sync the moment ``gating``
        # existed.  Measured: an incumbent whose registrar was allowed but
        # whose gate carried a closed module held the vital against a
        # correct, self-contained ``production_allowed = True`` lane --
        # ``REGISTER_REFUSED ... already_taken`` followed by
        # ``UI_DISPATCH_GATED`` on every frame, which is verbatim the
        # symptom the yield rule was written for.
        incumbent_gate = (incumbent,) + tuple(_ANSWERERS[vital_id][1])
        if all(
            lane_hooks.module_production_allowed(name)
            for name in incumbent_gate
        ):
            _say(
                "UI_DISPATCH_REGISTER_REFUSED id=%s reason=already_taken by=%s"
                % (_hex(vital_id), incumbent)
            )
            return False
        _say(
            "UI_DISPATCH_REGISTER_REPLACED id=%s gated=%s by=%s"
            % (_hex(vital_id), incumbent, module_name)
        )
    # ONE STATEMENT, NOT A CHECK-THEN-ACT (pf-adversary round 3, D9).
    # The refusal above still reads the dict first, but the write that
    # takes the slot is a single dict store, so the "first wins" claim
    # does not additionally depend on nothing running between a read and
    # a write.  (D9 was a shape complaint, not a measured loss: 200
    # two-thread races lost no entry, because ``_discover()`` is
    # single-threaded and the GIL serialises the dict ops.)
    _ANSWERERS[vital_id] = (module_name, gating, fn)
    _say(
        "UI_DISPATCH_ANSWERER id=%s module=%s gating=%s"
        % (_hex(vital_id), module_name, ",".join(gating) or "-")
    )
    return True


def registered_answerer(vital_id):
    """``(module_name, fn)`` for ``vital_id``, or ``None``. Read-only.

    The public shape stays a two-tuple; the gating set stored beside it
    (round 3, D1) is read by ``answer()`` and by
    ``gating_module_names()``, not by callers of this.
    """
    entry = _ANSWERERS.get(vital_id)
    if entry is None:
        return None
    module_name, _gating, fn = entry
    return (module_name, fn)


def gating_module_names(vital_id):
    """Every lane module ``answer()`` must clear for ``vital_id``.

    ``()`` when nothing is registered, or when the registration came from
    outside the lane package (a test, a REPL) -- in which case the gate
    falls back to the single registrar name, exactly as before D1.
    """
    entry = _ANSWERERS.get(vital_id)
    return () if entry is None else entry[1]


def clear_answerers():
    """Empty the registry.  For tests; nothing on the boot path calls it."""
    _ANSWERERS.clear()


# WHAT AN ANSWERER MAY REACH OF THE RUNTIME -- THE WHOLE LIST
# (pf-adversary round 3, D2).  ``answer()`` used to hand the answerer
# ``session`` itself, the live state object.  Everything this module says
# about labels -- the prefix, the foreign-substring list, the measured
# paragraph about a party-invite frame arming ``gm_warp_position_pending``
# -- defends ONE route to those consumers, and the answerer was holding a
# reference that walks straight past it.  Measured end to end through the
# real ``state.dispatch()`` on a logged-in session: an answerer that
# returns ``[]`` flipped ``gm_warp_position_pending`` False -> True and
# reopened that lane's grace window (the counter beside the flag,
# named in prose only -- see the note below), while this module printed
# a green token and returned an empty list.  "Fail-closed in every
# direction" was true of the RETURN VALUE only.
#
# THE COUNTER IS NAMED IN PROSE HERE ON PURPOSE, exactly as the
# label note below names its consumer in prose: that lane's own
# containment test pins which foundation modules may spell its
# underscored identifier (``app.py`` and ``runtime.py``, and no
# others), and this module must not join that set.  Writing the
# identifier here turned the whole suite red on the tree that
# first carried this paragraph -- the fix for a containment defect
# breaking a containment pin.
#
# So the answerer no longer gets the session.  It gets this, and this
# exposes an EXPLICIT ALLOWLIST of attribute names -- today the empty
# tuple, because no answerer exists yet and nothing has argued for a
# name.  Reading anything else raises ``AttributeError``; writing or
# deleting anything raises ``TypeError``, inside ``answer()``'s ``try``,
# so a lane reaching for the runtime fails closed on its own frame
# instead of quietly reaching it.
#
# THIS TUPLE IS THE DECISION POINT.  Widening it is a reviewed edit to
# this file naming the answerer that needs the field and why -- one
# place, for every lane, instead of a rule each producer remembers.
_SESSION_VIEW_FIELDS = ()


class _SessionSnapshot(tuple):
    """The allowlisted session fields, COPIED OUT. Holds no session.

    THE WRAPPER WAS ONE LINE DEEP (pf-adversary round 4, D-B).  The first
    version of this was a ``_SealedSession`` proxy keeping the real object
    in a ``__slots__`` member and refusing attribute access by name.  Five
    one-liners walked straight past it -- ``object.__getattribute__(view,
    "_session")``, ``type(view)._session.__get__(view)``,
    ``view.__class__._session.__get__(view)``,
    ``view.__reduce_ex__(2)[2][1]["_session"]``,
    ``gc.get_referents(view)[0]`` -- and the D2 attack reproduced
    verbatim through the real ``answer()``: an answerer returning ``[]``
    armed ``gm_warp_position_pending`` and reopened the grace window under
    a green token, with the fix installed.  ``__getattr__`` is not a
    boundary; in Python a reference IS reach.

    So nothing is wrapped.  This is a ``tuple`` of the values named by
    ``_SESSION_VIEW_FIELDS``, read once by ``answer()`` and copied in --
    today the empty tuple, because no answerer exists yet and nothing has
    argued for a field.  There is no ``_session``, no closure over one,
    and no descriptor that reaches one, so the routes above return this
    object's own emptiness.  ``tuple`` also settles the write half for
    free: there is no mutation to refuse.

    THIS TUPLE IS THE DECISION POINT.  Widening ``_SESSION_VIEW_FIELDS``
    is a reviewed edit to this file naming the answerer that needs the
    field and why -- and note what it costs, honestly: a field whose
    VALUE is itself a mutable runtime object hands that object over, so
    the reviewer's question is never "may this lane read it" alone but
    "what can this lane do with what reading it returns".  Scalars only,
    until someone argues otherwise on a specific frame.
    """

    __slots__ = ()

    def __new__(cls, session):
        return super().__new__(
            cls,
            ((name, getattr(session, name, None))
             for name in _SESSION_VIEW_FIELDS),
        )

    def field(self, name):
        """The snapshot value for ``name``, or raise ``KeyError``."""
        for key, value in self:
            if key == name:
                return value
        raise KeyError(
            "ui_dispatch snapshots the session: %r is not in"
            " _SESSION_VIEW_FIELDS. Widening that tuple is a reviewed"
            " edit to ui_dispatch.py (pf-adversary round 3 D2, round 4"
            " D-B)." % (name,)
        )


_ReplyBase = collections.namedtuple(
    "_ReplyBase", "label vital_id version payload delay"
)


class VitalReply(_ReplyBase):
    """What an answerer returns when it wants a byte to reach the player.

    WHY A DESCRIPTION AND NOT A FRAME.  Composing a frame needs the
    envelope builder, which lives in the frozen v141 module, and this
    file must not name that module (its containment test pins the
    foundation modules allowed to spell that identifier to ``app.py``
    and ``runtime.py``, and the comment above ``_SessionSnapshot``
    already records that joining that set turned the suite red).  The
    obvious workarounds are worse than the rule: handing the answerer
    the session, or a closure over it, is not a boundary at all --
    pf-adversary round 4 (D-B) walked five one-liners past exactly that
    wrapper, and ``fn.__closure__[0].cell_contents`` walks past a
    closure the same way.  A reference IS reach.

    So the lane returns DATA and this module composes.  The lane never
    holds the runtime, never holds the envelope builder, and cannot
    choose a byte outside the payload it hands over:

    * ``vital_id`` must EQUAL the id of the frame being answered.  An
      answerer registered for the party invite cannot reply as a
      teleport, a login ack, or any of the other seven ids this branch
      routes -- narrower than the registry alone, which only says who
      may speak for an id, not what they may say.  RE-312 (pf_bridge
      ``notes_to_chief/20260908_1038_*``) is what makes "same id" a
      real answer rather than a limitation: all eight classes are
      ``INBOUND_YES``, each with a live handler in vtable slot
      ``+0x1C``, reached from the batch dispatcher at ``0x005F38B2``.
    * ``version`` is the vital version byte, ``payload`` the nested
      payload bytes, ``delay`` the same delay every action carries.

    The composed ``(label, pc, frame, delay)`` then goes through
    ``_actions_are_well_formed`` unchanged, so nothing this class adds
    can skip a check that already existed.
    """

    __slots__ = ()


LABEL_PREFIX = "UI_"
_LABEL_GRAMMAR = re.compile(r"\AUI_[A-Z0-9_]{1,64}\Z")

# Substrings a consumer downstream keys on, which a UI_-prefixed label
# must therefore not contain. Sources, grepped this round:
#   runtime.py's move-authority server-moves note -- "TELEPORT" in label
#   pf_login_game_server_v141.py -- startswith of two refresh prefixes,
#   already unreachable behind LABEL_PREFIX, listed for the next reader
# ``wait_for_pf_stage.py``'s OWN NEEDLE TABLE, folded in (pf-adversary
# round 4, D-G).  The D3 paragraph below cites that tool by line number
# for matching SUBSTRINGS inside a line, and then this list did not carry
# its needles: ``UI_PARTY_GAME_CONNECTED_ACK`` satisfies the grammar and
# made ``wait_for_pf_stage <log> connected`` report REACHED.  Only the
# bare ``[A-Z0-9_]`` needles can be reached at all (the rest carry ``=``
# or lower case, which the grammar refuses), so those are what is listed.
_FOREIGN_LABEL_SUBSTRINGS = (
    "TELEPORT",
    "LOCAL_REFRESH_",
    "GAME_CONNECTED",
    "RUNTIME_RES_ACK_FIRST_REQ",
)


def _label_is_this_lanes_own(label):
    """May this label go into the dispatcher's action list?

    Yes only for a non-empty ``str`` that starts with ``UI_`` and carries
    no control characters.

    THE PREFIX IS NOT TIDINESS (pf-adversary D2).  ``dispatch()`` feeds
    whatever came back into ``_gm_warp_note_position_pending`` and into
    the move-authority server-moves note beside it -- spelled here in
    prose and never as its underscored identifier, because that lane's
    own containment test pins the exact set of foundation modules whose
    text mentions it, and this module must not join that set.  Both of
    those match on the LABEL.  Measured on an ordinary logged-in non-GM session: an answerer
    returning ``chat_command_action.WARP_ACTION_LABEL`` on a party-invite
    frame flipped ``gm_warp_position_pending`` to ``True`` -- a player
    clicking "invite to party" arming the GM warp-confirm window, with no
    GM, no ``/warp`` and no chat frame anywhere.  The prefix closes the
    consumer that compares labels for EQUALITY.  It does NOT close one
    that matches a SUBSTRING, which is why the check also carries an
    explicit list of foreign substrings: the earlier draft of this
    paragraph claimed the prefix alone was enough, and round 2 measured a
    ``UI_``-prefixed label reopening the move-authority grace window with
    no forgery at all.

    THE CONTROL-CHARACTER RULE (D12).  The v141 sender writes
    ``SENT <label> ...`` into the evidence file attended rounds grep; a
    newline inside a label forges a line in that artifact.
    """
    # A POSITIVE GRAMMAR, NOT ``isprintable()`` (pf-adversary round 3,
    # D3 and D4).  ``' '.isprintable()`` is True and so is every printable
    # non-ASCII character, and both of those are live defects, not
    # tidiness:
    #
    #   D3 -- the evidence artifacts are matched by SUBSTRING, not by
    #   line.  ``tools/wait_for_pf_stage.py:53`` asks ``all(needle in line
    #   for needle in pattern)``, and the v141 sender writes ``SENT
    #   label=<label> frame_bytes=...``.  Measured: the label
    #   ``UI_PARTY_INVITE_ACK SENT label=RUNTIME_RES_ACK_FIRST_REQ``
    #   passed the old check and made ``wait_for_pf_stage`` report stage
    #   ``runtime-ready`` REACHED -- a green Port Royal signal, from a
    #   party-invite frame, in an attended round following
    #   ``tools/PF_FAST_ENTRY_AUTOMATION.md`` step 5.  The D12 paragraph
    #   reasoned about newlines forging a LINE; the forgeable thing was
    #   never the line boundary.
    #
    #   D4 -- ``current/pf_login_game_server_v141.py`` prints ``[G>]
    #   {label} ...`` on a cp874 stdout it never reconfigures, AFTER
    #   ``c.sendall(out_frame)``, inside a ``try`` whose only handler is a
    #   ``finally``.  Measured: ``UI_PARTY_INVITE_ACK_\u2713`` killed the
    #   connection thread with ``UnicodeEncodeError`` with the bytes
    #   already on the wire.  ``tests/test_name_colour_sweep_all.py:261``
    #   already asserts ``label.isascii()`` for the same reason.
    #
    # Both close the same way and only this way: say what a label MAY
    # contain instead of listing what it may not.  ``UI_`` then upper
    # case, digits and underscore, 1..64 of them.  No space, no ``=``, no
    # non-ASCII, no control character, and nothing a future consumer's
    # separator can hide in.
    # ``type()``, NOT ``isinstance()`` (pf-adversary round 4, D-H, and
    # this file's own R7 lesson two checks below).  A ``str`` subclass
    # overriding ``__contains__`` to return ``False`` carries the real
    # text ``UI_PARTY_INVITE_TELEPORT_A`` past the foreign-substring list.
    # It buys no reach at any consumer found today -- ``runtime.py``'s
    # ``"TELEPORT" in action[0]`` calls the same lying ``__contains__``
    # and also says no -- but a validator that can be lied to is not one
    # to leave standing on the argument that the lie happens to be
    # symmetric at every consumer that exists this week.
    if type(label) is not str or not label:
        return False
    if not _LABEL_GRAMMAR.match(label):
        return False
    # A PREFIX DOES NOT STOP A SUBSTRING MATCH (pf-adversary round 2, R3).
    # The prefix closes the consumer that compares labels for EQUALITY.
    # The one beside it asks ``"TELEPORT" in action[0]``, so
    # ``UI_PARTY_INVITE_TELEPORT_A`` satisfies the prefix and reopens the
    # move-authority grace window on a party-invite frame -- measured A/B
    # against a control, needing no forgery at all: it is a name a lane
    # answering a movement-ish UI vital would plausibly pick.
    # WHO OWNS THIS VOCABULARY is the question this round could not answer
    # (recorded in the round file): the list below is what a grep of the
    # consumers found today, not a boundary anyone maintains.
    return not any(word in label for word in _FOREIGN_LABEL_SUBSTRINGS)


def _hex(vital_id):
    """``0x37B1`` for an int, a bounded repr for anything else."""
    if isinstance(vital_id, int) and not isinstance(vital_id, bool):
        return "0x%04X" % (vital_id & 0xFFFF,)
    return repr(vital_id)[:32]


# THE OUTBOUND FRAME-SHAPE ALLOWLIST (COO-DECISION 20260908_1142 item 7,
# route (b)).  The decision reads: what goes out must come from a
# REVIEWED registry of frame shapes at ``answer()``'s send point, and the
# PR that registers the first real answerer is the one that pays for it.
# Route (b) landed the seam; the party answerer landed the first real
# answerer; this is that bill.
#
# WHAT IT ADDS OVER EVERY CHECK ALREADY HERE.  ``_label_is_this_lanes_own``
# says a name is well formed and belongs to no other consumer's
# vocabulary.  ``_actions_are_well_formed`` says an action has the right
# TYPES.  ``_compose`` says a reply may only answer the id it was sent.
# None of the three says that THESE BYTES, under THIS NAME, answering
# THIS id, are a shape a human reviewed.  Before this table, a lane with
# ``production_allowed = True`` could return
# ``("UI_ANYTHING_AT_ALL", b"..", b"..", 0.0)`` -- any label satisfying
# the grammar, any bytes at all, of any length -- and the seam would put
# it on the socket.  The registry closes that: an unlisted label leaves
# nothing, and a listed one may only carry the id, the version and the
# byte budget its entry names.
#
# THE ENTRIES ARE THE REVIEW UNIT.  Adding one is an edit to this file --
# the same rule ``_SESSION_VIEW_FIELDS`` already lives by -- so the
# question "who decided these bytes may reach a player" always has a
# diff as its answer.  A lane cannot add an entry from its own module,
# and there is deliberately no ``register_outbound_shape()``: a registry
# a lane can write to is a registry that reviews nothing.
#
# THE NUMBERS.  ``versions`` is the vital version byte set; ``0`` is what
# ``ui_party_wire``/``ui_trade_wire`` ship and their own headers mark it
# an unproven default, so the set is exactly what is shipped and nothing
# more.  ``max_payload_bytes`` 512: these two payloads are u8 + u64 +
# tagged wstring, measured at 26 bytes for a five-character name, and 512
# is far above any name the client can produce while still refusing a
# lane that wants a listed label to carry a blob.  ``max_frame_bytes``
# 1024: the envelope this project ships added 32 bytes to that 26-byte
# payload (58 on the wire, the arming proof prints it), so 1024 bounds a
# 512-byte payload with room to spare and still refuses a frame that is
# not this shape at all.
#
# THE IDS ARE LITERALS, PINNED BY TEST, for the reason given above
# ``ANSWERABLE_VITAL_IDS``: a comment cannot go stale unnoticed, so
# ``tests/test_ui_dispatch.py`` imports ``ui_party_wire`` and
# ``ui_trade_wire`` and compares these numbers against theirs.
_OutboundShape = collections.namedtuple(
    "_OutboundShape", "vital_id versions max_payload_bytes max_frame_bytes"
)

_OUTBOUND_FRAME_SHAPES = {
    "UI_PARTY_INVITE_ANSWERED": _OutboundShape(
        vital_id=0x37B1,
        versions=frozenset((0,)),
        max_payload_bytes=512,
        max_frame_bytes=1024,
    ),
    "UI_TRADE_INVITE_ANSWERED": _OutboundShape(
        vital_id=0x3700,
        versions=frozenset((0,)),
        max_payload_bytes=512,
        max_frame_bytes=1024,
    ),
}


def outbound_shape(label):
    """The reviewed outbound shape for ``label``, or ``None``.

    ``type(label) is not str`` FIRST, not ``isinstance`` and not a bare
    ``dict.get`` (the same lesson ``_label_is_this_lanes_own`` records).
    A ``str`` subclass carries whatever ``__hash__`` and ``__eq__`` it
    likes, so it can match a key here while telling every other consumer
    it is something else -- and a lookup that can be lied to is not a
    registry.  The exact-type check makes the key that matched the key
    that everyone downstream sees.
    """
    if type(label) is not str:
        return None
    return _OUTBOUND_FRAME_SHAPES.get(label)


def _outbound_shapes_are_registered(answered_id, actions):
    """Is every action a shape this file's registry names for this id?

    Runs at ``answer()``'s send point, AFTER ``_actions_are_well_formed``
    -- so every action here is already a 4-tuple of the right types and
    this function may read it without re-deriving that.  It applies to
    EVERY action, whatever its origin: a composed ``VitalReply`` and a
    plain 4-tuple an answerer built by hand face the same table.  Gating
    only the composed half would be a gate with a door beside it.

    ``answered_id`` is the id of the frame being answered, so a lane
    cannot borrow a listed label to answer a different vital: the entry
    names the id it belongs to, and this compares them.
    """
    for action in actions:
        label, pc, frame, _delay = action
        shape = outbound_shape(label)
        if shape is None:
            return False
        if shape.vital_id != answered_id:
            return False
        # ``pc`` is the packet content the frame carries, so it is
        # bounded by the frame budget too: a frame within budget whose
        # pc is not is a shape this table does not describe.
        if len(frame) > shape.max_frame_bytes:
            return False
        if len(pc) > shape.max_frame_bytes:
            return False
    return True


def _actions_are_well_formed(actions):
    """Is ``actions`` a list/tuple of this project's action tuples?

    The convention, shipped in every dispatch return in ``runtime.py`` and
    documented in ``logout_dialog_open_hypothesis.py``, is
    ``(label, pc, frame, delay)``: a label this lane may use (see
    ``_label_is_this_lanes_own``), the packet-content ``bytes`` ``pc``,
    non-empty ``bytes`` ``frame`` to write, and a delay in seconds that
    is real, finite and not negative.

    !! ``pc`` IS ``bytes``, AND THE FIRST DRAFT OF THIS FUNCTION SAID
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
        # ``tuple`` ONLY, not ``list`` (pf-adversary round 2, R1).  The
        # draft admitted a list-typed action, and ``list(actions)`` copies
        # only the OUTER list -- an inner list stayed the answerer's own
        # object.  Validating a ``numbers.Real`` delay runs the answerer's
        # ``__ge__``, and delay is checked LAST, so a lane could rewrite
        # label/pc/frame after they were cleared, on the object that gets
        # returned: measured, a party-invite frame shipped the GM warp
        # label and armed ``gm_warp_position_pending`` under a green
        # UI_DISPATCH_ANSWERED token -- verbatim the D2 symptom this
        # module claims to close.  Every action this project emits is a
        # tuple; refusing the mutable shape closes the hole at the type
        # check instead of by copying deeper.
        if type(action) is not tuple or len(action) != 4:
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


def _compose(envelope, answered_id, item):
    """One ``VitalReply`` -> one ``(label, pc, frame, delay)`` action.

    Raises on every refusal so the caller's own ``except Exception``
    (which already exists, and already fails the whole batch closed)
    is the single place a bad reply dies.  Nothing here is filtered:
    half a lane's answer reaching the client is worse than none of it,
    the same rule the batch validator states.
    """
    if envelope is None:
        raise ValueError(
            "ui_dispatch was not given the envelope module; a VitalReply"
            " cannot be composed and the batch is refused"
        )
    # EVERY FIELD READ EXACTLY ONCE, INTO A LOCAL.  ``VitalReply`` is a
    # namedtuple, but a lane may subclass it and make a field a property
    # -- and a field read twice (once to check, once to use) is a field
    # that can return two different values.  The checks below therefore
    # guard the SAME objects that go to the envelope builder.
    label = item.label
    vital_id = item.vital_id
    version = item.version
    payload = item.payload
    delay = item.delay
    # ``int`` EXACTLY, not ``==``.  ``!=`` runs the lane's own
    # ``__eq__``, so an object that simply answers "equal" would satisfy
    # the id rule and then be handed to the envelope builder itself --
    # the same class of hole as the forged ``__module__`` the gate above
    # was fixed for.  ``bool`` is an ``int`` and is refused with it.
    if type(vital_id) is not int:
        raise TypeError("VitalReply.vital_id must be an int")
    if vital_id != answered_id:
        raise ValueError(
            "a VitalReply may only answer the id it was sent: got %s,"
            " answering %s" % (_hex(vital_id), _hex(answered_id))
        )
    if type(version) is not int:
        raise TypeError("VitalReply.version must be an int")
    if not 0 <= version <= 0xFF:
        raise ValueError("VitalReply.version is a single byte")
    # ``bytes`` exactly, for the reason _actions_are_well_formed gives
    # for ``pc``/``frame``: a bytearray is mutable after this check and a
    # str would be encoded by somebody else's guess of a codec.
    if type(payload) is not bytes:
        raise TypeError("VitalReply.payload must be bytes")
    # THE REVIEWED SHAPE, BEFORE THE ENVELOPE IS EVEN ASKED TO BUILD ONE
    # (COO-DECISION 20260908_1142 item 7 route (b)).  ``version`` and
    # ``payload`` are visible HERE and nowhere later: once the frame is
    # built they are bytes inside it, and the send-point gate can only
    # bound lengths.  So the half of the entry that describes the reply
    # is spent here, on the same locals that go to the builder, and the
    # half that describes what leaves is spent at the send point.
    shape = outbound_shape(label)
    if shape is None:
        raise ValueError(
            "no reviewed outbound frame shape is registered for label"
            " %.64r; adding one is an edit to ui_dispatch.py"
            % (label,)
        )
    if shape.vital_id != answered_id:
        raise ValueError(
            "label %.64r is registered for %s, not for %s"
            % (label, _hex(shape.vital_id), _hex(answered_id))
        )
    if version not in shape.versions:
        raise ValueError(
            "version %d is not a reviewed version for label %.64r"
            % (version, label)
        )
    if len(payload) > shape.max_payload_bytes:
        raise ValueError(
            "payload of %d bytes exceeds the reviewed budget %d for"
            " label %.64r"
            % (len(payload), shape.max_payload_bytes, label)
        )
    pc, frame = envelope.make_runtime_vitals([(vital_id, version, payload)])
    # THE BUILDER'S OUTPUT IS CHECKED, NOT ASSUMED.  A payload inside
    # budget whose frame is not says the shape in the table is not the
    # shape being built, and the honest answer to that is to refuse.
    if len(frame) > shape.max_frame_bytes:
        raise ValueError(
            "composed frame of %d bytes exceeds the reviewed budget %d"
            " for label %.64r"
            % (len(frame), shape.max_frame_bytes, label)
        )
    return (label, pc, frame, delay)


def answer(session, vital_id, payload, envelope=None):
    """Answer one of the eight UI vitals, or return ``[]``.

    Called from ``runtime.py``'s ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH_IDS``
    branch in place of its ``return []``, AFTER that branch has counted
    the frame and fired its report-only hook point.  Returns a list of
    ``(label, pc, frame, delay)`` actions for the dispatcher to send.

    Returns ``[]`` -- for every state described in this module's
    docstring.  The list returned is always a NEW list this module owns,
    so a caller extending it cannot reach back into an answerer's own
    object.

    ``envelope`` is the module that owns ``make_runtime_vitals``, passed
    down by ``runtime.py`` because this file may not name it (see
    ``VitalReply``).  It is a keyword with a default so that every
    caller which does not pass it -- a test, an older call site --
    keeps the behaviour it has today: a ``VitalReply`` cannot be
    composed without it, so the batch is REFUSED, not sent half-built.
    """
    entry = _ANSWERERS.get(vital_id)
    if entry is None:
        return []
    module_name, gating, fn = entry
    from . import lane_hooks  # noqa: PLC0415 - see the header comment

    # EVERY LANE MODULE THAT TOOK PART, NOT JUST THE ONE THAT CALLED
    # (pf-adversary round 3, D1).  ``gating`` is the set collected at
    # registration: the lane modules on the registration stack plus
    # ``fn``'s defining module.  A helper in an allowed module no longer
    # launders a ``production_allowed = False`` lane's decision, because
    # that lane's frame was under the helper's when the slot was taken.
    # THE REGISTRAR IS ALWAYS IN THE GATE, AND ``gating`` ONLY ADDS TO IT.
    # The first draft of this fix read ``gating or (module_name,)``, so a
    # non-empty ``gating`` REPLACED the registrar -- and ``gating``
    # includes ``fn.__module__``, which is a plain mutable attribute.  Its
    # own suite caught it: ``test_the_gate_reads_the_registering_module_
    # not_fn_dunder_module`` and ``test_a_forged_dunder_name_does_not_
    # open_the_gate`` both went green->red->green, because one line
    # ``fn.__module__ = "<an allowed lane module>"`` in a module the gate
    # was closed on now answered the frame.  That is round 2's R2/D5
    # regression, reintroduced by round 3's D1 fix.  Union, never
    # substitution: adding a name can only ever CLOSE the gate harder.
    for name in (module_name,) + tuple(gating):
        if not lane_hooks.module_production_allowed(name):
            _say(
                "UI_DISPATCH_GATED id=%s module=%s blocked=%s"
                " reason=not_production_allowed"
                % (_hex(vital_id), module_name, name)
            )
            return []
    try:
        actions = fn(
            session=_SessionSnapshot(session),
            vital_id=vital_id,
            payload=payload,
        )
        if actions is None:
            return []
        # SNAPSHOT FIRST, VALIDATE THE SNAPSHOT (pf-adversary D3).  The
        # draft validated the answerer's LIVE list and copied it after.
        # Validation runs the answerer's own code -- ``delay >= 0`` and
        # ``math.isfinite`` on a ``numbers.Real`` subclass this function
        # explicitly opts into -- so a lane could rewrite the list from
        # inside a comparison and ship what it liked: measured, a ``str``
        # where ``bytes`` must be and a delay of ``-99.0`` both went out
        # under a green ``UI_DISPATCH_ANSWERED`` token.  This copy is
        # SHALLOW and on its own was NOT enough -- round 2 of the review
        # got the same payload through a list-typed action, whose inner
        # list this copy does not touch.  What closes that is the
        # ``type(action) is not tuple`` check in the validator; this copy
        # only settles the outer container.
        if type(actions) in (list, tuple):
            actions = list(actions)
            # COMPOSE BEFORE VALIDATING, INSIDE THIS ``try``.  A
            # ``VitalReply`` is this lane's own data; turning it into an
            # action runs ``make_runtime_vitals`` on a payload the lane
            # chose, so it belongs under the same handler that already
            # catches an answerer raising -- not outside it, which is
            # the D4 mistake one paragraph down.  A batch may mix
            # composed replies with the plain 4-tuples answerers could
            # already return; both shapes then face the SAME validator
            # below, so nothing added here skips a check.
            actions = [
                _compose(envelope, vital_id, item)
                if isinstance(item, VitalReply) else item
                for item in actions
            ]
        # AND THE CHECK ITSELF IS INSIDE THIS try (pf-adversary D4).  It
        # was outside, so an answerer supplying a ``Real`` whose
        # ``__float__`` raises escaped answer(), escaped dispatch(), and
        # reached a connection loop whose try has only a finally -- which
        # is exactly what the "an answerer that raises is caught" sentence
        # promised could not happen.
        well_formed = _actions_are_well_formed(actions)
    except Exception as exc:
        # ``%r`` OF THE EXCEPTION IS ITSELF ANSWERER CODE (pf-adversary
        # round 2, R5).  It ran while building _say's argument, inside
        # the except block, so an exception whose ``__repr__`` raises
        # escaped answer() -- out of the handler that exists to stop
        # exactly that.
        try:
            detail = repr(exc)
        except Exception:
            detail = "<exception whose repr raised>"
        _say(
            "UI_DISPATCH_ANSWER_ERR id=%s module=%s %s"
            % (_hex(vital_id), module_name, detail)
        )
        return []
    if not well_formed:
        _say(
            "UI_DISPATCH_ANSWER_REFUSED id=%s module=%s reason=malformed"
            % (_hex(vital_id), module_name)
        )
        return []
    # THE SEND POINT (COO-DECISION 20260908_1142 item 7 route (b)).  The
    # whole batch dies on one unlisted action, for the reason ``_compose``
    # already states: half a lane's answer reaching the client is worse
    # than none of it.  This is deliberately the LAST gate before the
    # return, so nothing that is composed, validated or copied after it
    # can reintroduce a shape nobody reviewed.
    if not _outbound_shapes_are_registered(vital_id, actions):
        _say(
            "UI_DISPATCH_ANSWER_REFUSED id=%s module=%s"
            " reason=frame_shape_not_registered"
            % (_hex(vital_id), module_name)
        )
        return []
    # NAMED FOR WHAT IT MEASURES (pf-adversary round 3, D5).  This line
    # was ``UI_DISPATCH_ANSWERED``, and it fires here -- after the
    # validator liked the shape, BEFORE the dispatcher hands the batch to
    # ``sendall``.  Two states print it while nothing reaches the client:
    # an answerer returning ``[]`` (the natural "nothing for this
    # payload", which ``test_an_empty_answer_is_accepted_not_refused``
    # blesses) prints ``actions=0``, and a batch that later dies on
    # ``SEND_FAILED`` leaves a line claiming ``actions=2``.  A token read
    # as evidence that a button answered must not be one layer short of
    # the wire, so it says what it knows: the actions were ACCEPTED.
    _say(
        "UI_DISPATCH_ACCEPTED id=%s module=%s actions=%d"
        % (_hex(vital_id), module_name, len(actions))
    )
    return actions
