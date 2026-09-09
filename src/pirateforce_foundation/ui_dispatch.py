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

WHAT IT DID ON THE DAY IT LANDED, AND WHAT IT DOES NOW -- THESE ARE NOT
THE SAME SENTENCE, AND THIS PARAGRAPH USED TO CLAIM THEY WERE.  The seam
landed INERT: ``_ANSWERERS`` shipped empty, every one of the eight frames
took ``answer()``'s "no answerer" exit, and a player could not tell it
had landed.  That is what COO approved (route (b),
``pf_bridge/notes_to_chief/20260908_0142_COO-ROUND-0142-DECISIONS-*.md``
item 3, answering this lane's letter
``20260908_0031_LANE-UI-ASK-COO-eight-vitals-*``): the wiring lands
inert, and the first real answer is a later, separate, reviewable change.

That later change has happened, and THIS PARAGRAPH DOES NOT SAY HOW MANY
TIMES, on purpose.  Answerers ship in ``lane_hooks/lane_ui_*_answer.py``
with ``production_allowed = True``, so on a default flagless boot the ids
in ``_ANSWERER_OWNERS`` answer with a real frame and the rest still get
``[]``; that table is the count, and it is right by construction.
THE COUNT USED TO BE WRITTEN OUT HERE AND IT WAS WRONG THREE ROUNDS
RUNNING -- "TWO ... and six" survived party_cmd landing (m54yxh) and then
survived a round whose whole point, 190 lines below, was to stop
hand-counting the very same table (pf-adversary round `ncejt8`, F7,
caught it; round xqxadg's D6 caught the previous instance).  A header
that describes the day a file landed, in the present tense, becomes a
false statement about the system the first time somebody uses the file.
Anything below that reads "ships empty" is history, not behaviour.

``test_ui_dispatch.py``'s ``ShipsInertTests`` pins the EMPTY-registry
answer for all eight ids -- and read what that is worth honestly: its
isolation clears the process-global registry first, so it proves what
``answer()`` does with no answerer registered.  It does NOT and cannot
tell you how many lanes ship one (measured: a lane answering all eight
leaves that file 100% green).  The count above is the docstring's claim,
and the thing that keeps it true is a reader, not a test.

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

WHAT IS STILL OPEN, NAMED HERE BECAUSE A RESIDUAL NOBODY WRITES DOWN IS
A RESIDUAL NOBODY CLOSES (pf-adversary round vy1m79, D3).  Every table
in this file -- ``_ANSWERERS``, ``_SESSION_ANSWERS_SENT``, the
``_PROCESS_ANSWERS_SENT`` -- is module state, and a lane module
runs inside this process.  One line in a lane file,
``ui_dispatch._SESSION_ANSWERS_SENT.clear()``, hands every session a
fresh allowance (measured: 500 answers under an allowance of 32), and
``ui_dispatch._ANSWERERS[id] = ...`` is the same shape one level up --
the attack this file's ownership check (round 1gc6hl, D-A) closed only
for a forger borrowing the REVIEWED owner's name.  Neither is closable
by a patch here: a module cannot hide state from code running inside
its own interpreter, and every guard this file could add is one
attribute assignment away from being removed.  What closes it is the
seam owning registration outright -- ``lane_hooks._discover()`` writing
the table from a lane's declared ``ANSWERS_VITAL_ID`` instead of a lane
calling in -- which is CORE-REQUEST ``20260908_1553``.  IT IS ANSWERED
AND IT IS NOT LANDED, and those are different sentences (pf-adversary
round `asw0n3`, D7: this paragraph still read "filed, not answered yet"
two rounds after the answer arrived).  chief approved it in
``notes_to_chief/20260908_1703_FROM_CHIEF_R404-to-LANE-UI-*`` and then,
in ``20260908_2031_FROM_CHIEF_R406-*``, declined to wire ``_discover()``
for one measured reason this lane asked for: ``adopt_answerer`` is not on
``main`` yet, and wiring the seam to a function that is not there opens
the hole it is meant to close.  So the residual is UNCHANGED in effect --
registration is still a lane calling in -- and it is not described
anywhere as closed.  What moved is only who it waits on: a merge, not a
decision.

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
import weakref

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
_LANE_PACKAGE = "pirateforce_foundation.lane_hooks."


def _is_discoverable_lane(name):
    """Is ``name`` a module ``lane_hooks._discover()`` would import?

    THE SAME RULE IN ONE PLACE.  ``_discover()`` imports only
    ``lane_hooks/lane_*.py``, so those are the only modules that can
    register on a production boot and the only ones with a
    ``_PRODUCTION_ALLOWED`` entry to read.  ``_gating_module_names()``
    learned this the hard way (round 4, D-E) and ``register_answerer()``'s
    ownership check asks the same question, so the question is asked once.
    """
    if not isinstance(name, str) or not name.startswith(_LANE_PACKAGE):
        return False
    return name[len(_LANE_PACKAGE):].startswith("lane_")

ANSWERABLE_VITAL_IDS = frozenset(
    (0x37B1, 0x2466, 0xB9E9, 0x98A1, 0x6E12, 0xAF60, 0x8183, 0x3700)
)

# vital_id -> (module_name, answerer). One answerer per id, by refusal:
# see register_answerer().
_ANSWERERS = {}

# WHICH LANE MODULE MAY TAKE WHICH ID -- THE REVIEWED TABLE
# (pf-adversary round xqxadg, D9).  Registration used to be first-wins,
# and "first" was decided by ``pkgutil.iter_modules`` FILENAME ORDER: a
# ``lane_hooks/lane_ui_aaa_party.py`` with ``production_allowed = True``
# took ``0x37B1`` from the reviewed answerer beside it, answered the
# player's party invite with its own bytes, and ``tests/
# test_ui_dispatch.py`` stayed 100% green -- the incumbent-yield rule
# above only rescues a GATED incumbent, and this thief is not gated.
# Filename order is not a review, so it no longer decides anything: an
# id named here may be taken ONLY by the module named beside it.
#
# THE SAME REVIEW UNIT AS ``_OUTBOUND_FRAME_SHAPES`` AND
# ``_SESSION_VIEW_FIELDS``, for the same reason: adding a row is a diff
# in THIS file, so "who decided this module may answer this button" has
# a commit as its answer.  There is deliberately no register-your-own-
# ownership call.
#
# WHAT IT DOES NOT COVER, SAID PLAINLY.  The rule binds registrars
# INSIDE the lane package (``lane_hooks/lane_*.py`` -- the only files
# ``_discover()`` imports, so the only ones that can register on a
# production boot).  A test or a REPL registering from outside that
# package is unaffected, because refusing those would make this file
# untestable without also closing a route that cannot ship: nothing on
# the boot path imports a non-lane module that registers, and
# ``answer()``'s gate still demands a ``_PRODUCTION_ALLOWED`` entry,
# which only ``_discover()`` writes and only for ``lane_*.py``.
# An id with NO row here cannot be taken by a lane module at all: the
# ids nobody has written an answerer for stay unanswerable until a row
# for them is reviewed into this file.  THE COUNT IS DELIBERATELY NOT
# WRITTEN HERE (pf-adversary round `asw0n3`, D9: a hand-written "six"
# went false the moment the next row landed and nothing could catch it).
# The remaining ids are ``ANSWERABLE_VITAL_IDS`` minus this table's keys,
# which is a subtraction any reader -- and
# ``tests/test_ui_dispatch.py`` -- can do.
_ANSWERER_OWNERS = {
    0x37B1: _LANE_PACKAGE + "lane_ui_party_invite_answer",
    0x3700: _LANE_PACKAGE + "lane_ui_trade_invite_answer",
    0x2466: _LANE_PACKAGE + "lane_ui_party_cmd_answer",
    # THE FIRST OF THE FIVE ``CommunityModule_Client`` IDS, and the first
    # row here whose id is ALSO read on the production path by a
    # report-only hook (``lane_ui_friend_wire_log``).  Those are two
    # different questions: runtime.py fires the log hook and then calls
    # ``answer()``, so the log keeps printing what arrived and this row
    # is about who may put a byte back.
    #
    # AND WHAT "WHO MAY" MEANS IS THE OTHER WAY ROUND FROM HOW THIS
    # COMMENT FIRST PUT IT (pf-adversary round asw0n3, D2).  BEFORE this
    # row, ``_ANSWERER_OWNERS.get(0xB9E9)`` was ``None`` and NO lane
    # module could take the id by any route -- measured.  AFTER it, the
    # answer is "the module named here, OR anyone who can gate that
    # module and write into its namespace": the adversary drove
    # ``deadbeef`` out of the real ``state.dispatch()`` under this
    # label using the gated-incumbent-yield route and the residual
    # named at ``_install_answerer`` below, and a
    # ``production_allowed = False`` file that does nothing but IMPORT
    # the owner denies the button forever.  Those two mechanisms are the
    # seam's, not this row's, and are recorded as open residuals in this
    # file's own header -- what is new is that they now reach ``0xB9E9``,
    # and that the owner module's public ``arming_sample()`` is the
    # first reason another lane has ever had to import it.  Not fixed
    # here; carried as this lane's first item next round rather than
    # left for a reader to rediscover.
    0xB9E9: _LANE_PACKAGE + "lane_ui_friend_request_answer",
    # THE SECOND OF THOSE FIVE (round ncejt8).  Everything the paragraph
    # above says about what this table can and cannot decide applies
    # unchanged to this id: the row settles who may put a byte back, and
    # the two residuals it names -- the gated-incumbent-yield route and
    # the one at ``_install_answerer`` -- now reach ``0x98A1`` too.  That
    # cost is written up rather than left for a reader to find, in
    # pf_bridge ``notes_to_chief/20260908_2132_LANE-UI-ASK-COO-the-
    # answerer-public-api-*``.  What is different here: this module has
    # NO public API beyond its answerer, so the "first reason another
    # lane has ever had to import it" sentence above does not extend.
    0x98A1: _LANE_PACKAGE + "lane_ui_friend_remove_answer",
    # THE SIXTH BUTTON (round t4nxwq), and the residual named above still
    # unpaid: COO-DECISION ``20260909_1312_COO-DECISION-ui2132-*`` is
    # "keep adding buttons, the seam closes once, in chief's
    # ``_discover()``".  This row settles who may take ``0x6E12``, same
    # as every row above it; it does not touch the write-ownership gap.
    0x6E12: _LANE_PACKAGE + "lane_ui_mail_send_answer",
}


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
        if not _is_discoverable_lane(name):
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
    # THE REVIEWED OWNER, BEFORE ANY QUESTION OF WHO CAME FIRST
    # (pf-adversary round xqxadg, D9).  ``_ANSWERER_OWNERS`` names the one
    # lane module each answerable id belongs to; a lane-package registrar
    # that is not that module is refused whether or not the id is free, so
    # the winner of a race between two lane files is decided by this
    # table's diff and never by ``pkgutil.iter_modules`` filename order.
    # Registrars from outside the lane package are not judged here -- see
    # the table's own note for why that is not a route to production.
    if _is_discoverable_lane(module_name):
        owner = _ANSWERER_OWNERS.get(vital_id)
        owner_module = sys.modules.get(owner) if owner else None
        # THE OWNER REGISTERED IT, OR THE OWNER'S OWN CALLABLE IS WHAT IS
        # BEING REGISTERED.  The second clause keeps the legitimate case
        # the D1 fix exists to protect -- a helper lane doing the wiring
        # -- while still refusing a lane that wires a body nobody
        # reviewed for this id.  What may NOT vary is whose code runs.
        wires_the_owners_own = owner_module is not None and any(
            value is fn for value in vars(owner_module).values()
        )
        if owner != module_name and not wires_the_owners_own:
            _say(
                "UI_DISPATCH_REGISTER_REFUSED id=%s reason=not_the_reviewed_owner"
                " by=%s owner=%s"
                % (_hex(vital_id), module_name, owner or "-")
            )
            return False
    return _install_answerer(module_name, gating, vital_id, fn)


def _install_answerer(module_name, gating, vital_id, fn, token="REGISTER"):
    """Take the slot for ``vital_id``, or refuse and say why. Returns a bool.

    THE WRITE ITSELF, SHARED BY THE TWO WAYS IN (round ly40b5).  Two
    entry points now reach this registry -- ``register_answerer()``,
    where a lane wires itself and the registrar is read off the stack,
    and ``adopt_answerer()``, where ``lane_hooks._discover()`` wires a
    lane that declared its id and the registrar is the name the import
    machinery used.  What must NOT vary between them is the part that
    decides who holds an id: first-wins, the gated-incumbent yield, the
    single-statement store and the token that names the result.  Keeping
    that in one function is what makes "the two routes cannot disagree"
    a property of the file rather than a promise in a docstring.

    The CALLER owns the checks that differ (who may register, and how
    the registrar's name and gate were established); by the time this
    runs, ``module_name`` and ``gating`` are settled facts.
    """
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
            # THE REFUSED PARTY IS NAMED, NOT ONLY THE INCUMBENT
            # (pf-adversary round ly40b5, D4).  These two lines are
            # shared by both routes now, and on the adopt route they
            # printed ``UI_DISPATCH_REGISTER_REFUSED ... by=<incumbent>``
            # -- a refusal that greps as the OTHER route's token and does
            # not contain the name of the module that was turned away.
            # Measured on the very first boot chief's seam will make: a
            # lane that still calls ``register_answerer()`` AND declares
            # ``ANSWERS_VITAL_ID`` (the transition state this file's own
            # docs plan for) was denounced as its own thief. ``by=`` now
            # always means "the module this call was made for", on both
            # routes, and the incumbent has a key of its own.
            _say(
                "UI_DISPATCH_%s_REFUSED id=%s reason=already_taken by=%s"
                " incumbent=%s"
                % (token, _hex(vital_id), module_name, incumbent)
            )
            return False
        _say(
            "UI_DISPATCH_%s_REPLACED id=%s gated=%s by=%s"
            % (token, _hex(vital_id), incumbent, module_name)
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


def adopt_answerer(qualified_name, vital_id, module):
    """Wire the answerer a DISCOVERED lane module DECLARES, on its behalf.

    WHY THIS EXISTS (``NOW.md``, COO ``1441`` item 1: "a lane may not
    call ``register_answerer()``").  A lane that wires itself is a lane
    whose registration is a side effect of ``import``, and the registrar
    identity that decides the production gate is then read off the call
    stack.  ``lane_hooks._discover()`` is the one function that imports
    lane files, so it is the only place the registration can happen
    without being an import side effect -- and there the registrar name
    is not a guess at all: it is the ``sys.modules`` key the import
    machinery just used.  ``CORE-REQUEST`` ``20260908_1553`` asked chief
    for that seam; chief approved it (letter ``20260908_1703``) and
    bound it to this function's shape:

        vital_id = getattr(module, "ANSWERS_VITAL_ID", None)
        adopt = getattr(ui_dispatch, "adopt_answerer", None)
        if vital_id is not None and adopt is not None:
            adopt(qualified_name, vital_id, module)

    ``_discover()`` does not read the return value and does not
    interpret anything, so every refusal here is NAMED ON STDERR
    (chief's one added condition, letter section 4): a forged declaration
    that was refused and a lane that has not declared anything must not
    look the same on the console.

    WHAT IT REFUSES, AND WHY EACH ONE IS FAIL-CLOSED.  The id must be
    one ``runtime.py`` routes here; the declaring name must be a module
    ``_discover()`` can reach; ``sys.modules[qualified_name]`` must BE
    the module object handed over (the name is what the gate will judge,
    so a name that does not resolve to this object is not a name this
    function may register under); ``_ANSWERER_OWNERS`` must carry a
    reviewed row for the id and it must name this module; the module's
    own ``ANSWERS_VITAL_ID`` must be the id passed in (so a caller
    passing a different id cannot wire a lane to a button it never
    declared); and the callable must be declared explicitly as
    ``ANSWERS_WITH``.

    ``ANSWERS_WITH`` IS EXPLICIT ON PURPOSE.  The obvious alternative --
    "find the single ``answer_*`` function in the module" -- makes which
    bytes reach the wire depend on the set of helper names a lane file
    happens to define, so an ordinary refactor could silently change the
    answerer.  Two declaration lines in the lane cost nothing and leave
    the choice in the lane's own diff.

    Not checked here, deliberately: whether the lane is
    production-allowed.  That flag is a snapshot ``_discover()`` takes
    around this call, and the gate that reads it lives in ``answer()``,
    on every frame.  WHICH NAMES that gate is asked about is NOT the same
    on the two routes, and this sentence used to claim it was: see
    ``_lane_modules_answerable_for()`` for the difference and for the
    measured attack (round ly40b5, D1) that the difference let through.

    Nothing a lane file writes may raise out of this function: it is
    called from ``_discover()``, outside the try that guards a lane's
    import, so an exception here is a server that does not boot (D2).
    Every path returns a bool and names itself on stderr.
    """
    try:
        return _adopt_answerer(qualified_name, vital_id, module)
    except Exception as exc:  # a lane's own object raised, on the boot path
        # NOTHING A LANE FILE WRITES MAY STOP THE SERVER BOOTING
        # (pf-adversary round ly40b5, D2).  This call sits in
        # ``_discover()``, OUTSIDE ``_import_module_safely()``'s try --
        # that try covers the lane's import, not this -- so an exception
        # here is not "one button silent", it is ``lane_hooks`` failing to
        # import, so ``runtime`` failing to import, so nobody logging in.
        # Measured: ``ANSWERS_VITAL_ID = [0x37B1, 0x2466]`` (an author
        # wanting two buttons) killed the boot with ``TypeError:
        # unhashable type: 'list'`` at the membership test, and an object
        # with a raising ``__eq__`` killed it at the declared-id check.
        # The same typo through ``register_answerer()`` costs one skipped
        # lane and the server boots -- so the regression was created
        # purely by moving the call out of the lane's own import, and it
        # is exactly the shape chief refused to ship on his side.
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=declaration_raised by=%s"
            " exc=%s"
            % (
                _safe_hex(vital_id),
                qualified_name if type(qualified_name) is str else "-",
                type(exc).__name__,
            )
        )
        return False


def _safe_hex(vital_id):
    """``_hex()`` for a value a lane file supplied. Never raises."""
    try:
        return _hex(vital_id) if type(vital_id) is int else "-"
    except Exception:  # pragma: no cover - _hex on an int cannot raise
        return "-"


def _lane_modules_answerable_for(fn):
    """Every discoverable lane that DEFINED or HOLDS ``fn``, by identity.

    THE GATE MAY NOT REST ON ``fn.__module__`` ON THIS ROUTE
    (pf-adversary round ly40b5, D1 -- CRITICAL, measured end to end).
    ``register_answerer()`` binds the callable inside the lane's own
    import, so the lane's frame is on the registration stack and
    ``_gating_module_names()`` finds it there; ``__module__`` can only ADD
    a name, which is why this file says a forged value "cannot open the
    gate".  ``adopt_answerer()`` binds it LATER, from ``_discover()``'s
    frame, where NO lane frame exists -- so on that route ``__module__``
    is the only thing that can add the second name, and forging it
    REMOVES the name the gate needed.  Measured: a
    ``production_allowed = False`` lane that sets
    ``victim.ANSWERS_WITH = evil`` and ``evil.__module__ = victim`` put
    its own bytes on the wire under the reviewed owner's name, with the
    thief's name in no token, while discovery printed
    ``SKIPPED_NOT_PRODUCTION_ALLOWED`` for it.  That is round ``ihf029``'s
    D-A -- the deferred flush this seam was requested to CLOSE -- and it
    would have shipped as the sanctioned path.

    So the answer to "whose code is this" is taken from facts a lane
    file cannot rewrite after the fact:

    * the file the callable was COMPILED from (``__code__.co_filename``,
      set by the import machinery, not assignable like ``__module__``),
      mapped back to a lane by that module's ``__file__``;
    * every discoverable lane whose namespace HOLDS the object by
      identity -- the thief must keep ``evil`` somewhere to bind it, and
      a lane that hands its own callable to another lane's declaration
      is answerable for it either way.

    Both can only ADD names to the gate, never remove one, so this
    function cannot open a gate that would otherwise be closed.
    """
    import os  # noqa: PLC0415 - see the module header comment

    names = []

    def add(module_name):
        if _is_discoverable_lane(module_name) and module_name not in names:
            names.append(module_name)

    code = getattr(fn, "__code__", None)
    if code is None:  # a callable object, not a plain function
        call = getattr(type(fn), "__call__", None)
        code = getattr(call, "__code__", None)
    filename = getattr(code, "co_filename", None)
    for module_name, module in list(sys.modules.items()):
        if not isinstance(module_name, str) or module is None:
            continue
        if not _is_discoverable_lane(module_name):
            continue
        module_file = getattr(module, "__file__", None)
        if (
            filename
            and isinstance(module_file, str)
            and os.path.realpath(module_file) == os.path.realpath(filename)
        ):
            add(module_name)
        namespace = getattr(module, "__dict__", None)
        if isinstance(namespace, dict) and any(
            value is fn for value in list(namespace.values())
        ):
            add(module_name)
    return tuple(names)


def _adopt_answerer(qualified_name, vital_id, module):
    """``adopt_answerer()``'s body. See it for what this is and why."""
    name = qualified_name if type(qualified_name) is str else "-"
    if type(vital_id) is not int or vital_id not in ANSWERABLE_VITAL_IDS:
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=not_routed_here by=%s"
            % (_safe_hex(vital_id), name)
        )
        return False
    if not _is_discoverable_lane(name):
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=not_a_discoverable_lane by=%s"
            % (_hex(vital_id), name)
        )
        return False
    if module is None or sys.modules.get(name) is not module:
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=name_is_not_that_module by=%s"
            % (_hex(vital_id), name)
        )
        return False
    owner = _ANSWERER_OWNERS.get(vital_id)
    if owner is None:
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=no_reviewed_owner by=%s"
            % (_hex(vital_id), name)
        )
        return False
    if owner != name:
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=not_the_reviewed_owner"
            " by=%s owner=%s"
            % (_hex(vital_id), name, owner)
        )
        return False
    declared = getattr(module, "ANSWERS_VITAL_ID", None)
    if type(declared) is not int or declared != vital_id:
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=id_is_not_the_declared_one by=%s"
            % (_hex(vital_id), name)
        )
        return False
    fn = getattr(module, "ANSWERS_WITH", None)
    if not callable(fn):
        _say(
            "UI_DISPATCH_ADOPT_REFUSED id=%s reason=no_declared_callable by=%s"
            % (_hex(vital_id), name)
        )
        return False
    # WHO THE GATE MUST CLEAR, FROM FACTS A LANE CANNOT REWRITE.
    # ``_lane_modules_answerable_for()`` is the load-bearing term here --
    # see its docstring for the measured attack (round ly40b5, D1) that
    # ``_gating_module_names()`` alone lets through on this route, where
    # no lane frame is on the stack and ``fn.__module__`` is forgeable.
    # ``name`` is kept for the token's sake; ``answer()`` gates on
    # ``(module_name,) + gating`` as a union, so on this route it is
    # already covered and adding it changes no decision.
    # ``_gating_module_names()`` is kept because it can only ADD names.
    gating = tuple(dict.fromkeys(
        (name,)
        + _lane_modules_answerable_for(fn)
        + _gating_module_names(fn)
    ))
    return _install_answerer(name, gating, vital_id, fn, token="ADOPT")


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


# WHAT MUST BE TRUE OF THE SESSION BEFORE ANY ANSWERER RUNS
# (pf-adversary round xqxadg, D7).  ``runtime.py``'s dispatch is one long
# chain of ``if nested_id == ...`` branches, and the eight-vital branch
# this seam hangs off is a branch of that chain like any other: it is
# reached by the ID of the frame, NOT by where the session has got to.
# Measured through the real ``state.dispatch()``: a connection that has
# never sent LOGIN_VERIFY and never selected a character sent one
# PartyInviteVital and got the answerer's frame back, and could repeat it
# until the answerer's process-wide budget was spent -- after which the
# button was silent for every logged-in player until the server was
# restarted.  Two costs, one hole: bytes to a peer who never logged in,
# and a denial of the button to everyone who did.
#
# THE PRECONDITION IS THE ONE ``runtime.py`` ALREADY USES for in-game
# frames (``self.foundation.selected is None`` -- e.g.
# ``_dispatch_item_move_capture``): a session holds a selected character
# only after the login handshake, the character list and START_GAME_REQ
# have all succeeded.  All eight of these vitals are buttons the shipped
# client only draws in-game, so a frame carrying one before that point
# is not an early press; it is a peer that did not come through the door.
#
# READ HERE, NOT IN ``runtime.py``, and not by widening
# ``_SESSION_VIEW_FIELDS``: this is the seam's own admission check on the
# object the seam is handed, and the answerer still gets the same empty
# snapshot it gets today.  Fail-closed on anything unexpected -- a
# session shape without the attribute, or a property that raises, answers
# ``[]`` rather than guessing that it is logged in.
_SESSION_IN_GAME_READS = ("foundation.selected",)


def _session_is_in_game(session):
    """Has this session actually reached in-game state?  Fail-closed."""
    for path in _SESSION_IN_GAME_READS:
        value = session
        for part in path.split("."):
            try:
                value = getattr(value, part)
            except Exception:
                return False
        if value is None:
            return False
    return True


# WHOSE ALLOWANCE IS SPENT WHEN A BUTTON IS ANSWERED
# (pf-adversary round 1gc6hl, D-B).  The two shipped answerers each kept
# a PROCESS-WIDE counter, and the reason given for it was true but did
# not follow: an answerer is handed no session identity, so a lane cannot
# count per session.  The seam can.  Measured on the branch that shipped
# the process-wide counter: session A, logged in correctly, answered 32
# invites and then session B -- a different account, a different socket,
# equally logged in -- got zero, and stayed at zero until the server was
# restarted.  One ordinary player, pressing an ordinary button, silenced
# the button for everybody.
#
# THE GUARD BELONGS WHERE THE SESSION IS VISIBLE, so it lives here and
# the lanes no longer keep a counter at all.  What it bounds is what the
# storm argument is actually about: a client that answers our answer with
# the same vital would trade frames with us forever, and a storm runs
# between the server and ONE socket.  A cap per session bounds that
# exactly; a cap per process bounds it too, and bounds every other
# session with it.
#
# COUNTED WHERE THE BATCH IS ACCEPTED, NOT WHERE THE FRAME ARRIVES (this
# also pays D-F).  The charge happens once the batch has passed every
# gate and is about to be returned -- one layer short of ``sendall``,
# named rather than glossed (D7) -- and only for a batch that carries
# actions.  So a refusal -- a wrong id, junk bytes, a
# payload over the reviewed budget, a missing envelope, an answerer that
# raised -- costs the session nothing, which is the property the lanes
# used to try to buy by ordering their own checks and could not, because
# the seam's own refusals happen after the lane has already counted.
#
# READ BEFORE THE ANSWERER RUNS, CHARGED AFTER IT SUCCEEDS: once the
# allowance is spent the lane's code is not entered at all, the same
# shape as the login door above.
SESSION_ANSWER_BUDGET = 32

# ``id(session)`` -> ``[weakref, {vital_id: answers_sent}]``.  Keyed by
# IDENTITY, not by the session as a dict key: a ``WeakKeyDictionary``
# would call the session class's own ``__hash__``/``__eq__``, and two
# sessions that compare equal would then share one allowance -- which is
# the very bug being fixed, reintroduced through the container.  The
# weakref's callback drops the row when the session is collected, so a
# long-lived server does not accumulate one entry per connection ever
# made.  CPython runs that callback during the object's deallocation,
# before its memory can be handed to a new object, so the id cannot
# already belong to somebody else by the time the row goes.
#
# PER VITAL INSIDE THE SESSION, AND THAT IS NOT DECORATION (pf-adversary
# round vy1m79, D1).  The first draft of this fix keyed on the session
# alone, and the file that removed the old per-module counters asserted
# in the same breath that "a storm on trade cannot silence party".
# Measured through the real ``state.dispatch()``: it did.  32 trade
# answers on one session, then the party button on that same session
# returned nothing.  The property the two separate module counters used
# to have is a property, not an accident, so it is kept explicitly here.
_SESSION_ANSWERS_SENT = {}

# THE CEILING THE OLD PER-MODULE COUNTERS ALSO BOUGHT (pf-adversary round
# vy1m79, D2).  ``ANSWER_BUDGET = 32`` was per PROCESS, and its comment
# said what it was for: "anything past that on one boot is a loop, not a
# player".  A per-session allowance does not bound a loop that
# RECONNECTS -- measured, four reconnects on one account produced 128
# answer frames from one process where the old design allowed 32.  So the
# process ceiling stays, at a number chosen to bound a runaway client
# without letting one player reach it: 32 answers x 128 sessions.
# [LANE-UI assumption - awaiting COO confirmation] the NUMBER is this
# lane's judgement (letter filed this round); that there must BE one is
# pf-adversary's measurement, not a judgement.
#
# PER VITAL, AND THAT WORD IS THE WHOLE POINT (pf-adversary round m54yxh,
# D1).  The counter behind this number was one integer for the process,
# shared by every session AND every vital -- so the arithmetic above was
# only true while ONE vital could be answered.  Measured on the round
# that added the third answerer: what one player could draw from the
# shared pot went 64 -> 96, the sessions needed to exhaust it went
# 64 -> 43, and after exhaustion a bystander who had pressed nothing got
# nothing back, permanently, until a restart.  Every future answerer on
# this seam would have taken another slice, and each could have said
# truthfully that its own per-session allowance changed nothing.  So the
# ceiling is kept PER VITAL ID: adding an answerer no longer shrinks the
# pot the shipped ones share, and the comment above can be re-derived at
# HEAD instead of describing the shape the file had two rounds ago.
# WHAT IT STILL IS NOT: a per-account bound (one account may hold several
# sessions) and not a promise that a determined crowd cannot exhaust ONE
# vital's pot -- a pot with a ceiling can always be emptied.  What it now
# refuses to do is let a new button quietly cost the old ones.
PROCESS_ANSWER_BUDGET = 4096

# vital_id -> answers sent for it since boot.  Never keyed by session:
# that is _SESSION_ANSWERS_SENT's job, and this one has to survive the
# session going away, which is the loop it exists to bound.
_PROCESS_ANSWERS_SENT = {}


def _drop_session_budget(key):
    def _drop(_ref):
        _SESSION_ANSWERS_SENT.pop(key, None)
    return _drop


def _session_row(session):
    """This session's allowance row, created if new.  ``None`` = unbounded.

    ``None`` means the seam cannot key this session at all, and every
    caller treats that as a refusal.  The row is created HERE, at the
    read, and not at the charge (pf-adversary round vy1m79, D5): the
    first draft read a spend of 0 for a session it could not key, ran the
    answerer in full on every frame, and threw the batch away on the last
    line -- fail-closed on bytes and wide open on work.
    """
    key = id(session)
    row = _SESSION_ANSWERS_SENT.get(key)
    if row is not None:
        return row
    try:
        ref = weakref.ref(session, _drop_session_budget(key))
    except TypeError:
        return None
    row = [ref, {}]
    _SESSION_ANSWERS_SENT[key] = row
    return row


def _session_answers_spent(session, vital_id):
    """How many answers this session has been sent for ``vital_id``."""
    row = _SESSION_ANSWERS_SENT.get(id(session))
    if row is None:
        return 0
    return row[1].get(vital_id, 0)


def _allowance_refusal(session, vital_id, count):
    """Why ``count`` more answers may not be sent, or ``""``.

    Read before the answerer runs with ``count`` of 1 -- an allowance
    already spent must not run the lane's code at all -- and again at the
    charge with the real batch size.
    """
    row = _session_row(session)
    if row is None:
        return "session_budget_unbounded"
    if row[1].get(vital_id, 0) + count > SESSION_ANSWER_BUDGET:
        return "session_budget_spent"
    if (_PROCESS_ANSWERS_SENT.get(vital_id, 0) + count
            > PROCESS_ANSWER_BUDGET):
        return "process_budget_spent"
    return ""


def _charge_session_answer(session, vital_id, count):
    """Spend ``count`` answers.  Returns "" when they were spent.

    ``count`` is the SIZE OF THE BATCH, not one per call (pf-adversary
    round vy1m79, D4): the first draft charged one whatever the answerer
    returned, so an answerer returning eight actions per press put 256
    frames on the socket against an allowance of 32.  The allowance is
    about frames, so it counts frames.

    The re-check here is not a duplicate of the pre-gate above: it is the
    concurrency backstop.  Two threads dispatching for one session both
    pass the read at ``answer()``'s gate and are serialised here, which is
    what holds the cap at exactly ``SESSION_ANSWER_BUDGET`` under eight
    threads (measured by pf-adversary, round vy1m79).
    """
    refusal = _allowance_refusal(session, vital_id, count)
    if refusal:
        return refusal
    row = _SESSION_ANSWERS_SENT[id(session)]
    row[1][vital_id] = row[1].get(vital_id, 0) + count
    _PROCESS_ANSWERS_SENT[vital_id] = (
        _PROCESS_ANSWERS_SENT.get(vital_id, 0) + count
    )
    return ""


def reset_session_budgets_for_tests():
    """Forget every session's spend.  Tests and arming proofs only.

    NOT RE-EXPORTED BY ANY LANE MODULE (pf-adversary round vy1m79, D3).
    Both answerers used to carry a ``reset_budget_for_tests()`` that
    reset their own counter; delegating it here turned a helper in a
    ``production_allowed = True`` module into a public switch that
    clears the server's only storm guard for every session at once.  A
    test that wants a clean allowance asks this module for it.
    """
    _SESSION_ANSWERS_SENT.clear()
    _PROCESS_ANSWERS_SENT.clear()



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

    !! AND SO IS THE CALL STACK.  THIS SHAPE IS NOT A BOUNDARY, AND THE
    SENTENCE THAT USED TO STAND HERE -- "the lane never holds the
    runtime, never holds the envelope builder, and cannot choose a byte
    outside the payload it hands over" -- IS FALSE.  pf-adversary
    (round xqxadg, D1) measured it end to end through the real
    ``state.dispatch()`` on a logged-in session: a lane file with
    ``production_allowed = True``, registered by the real
    ``_discover()``, ran

        f = sys._getframe(1)          # ui_dispatch.answer()'s frame
        live = f.f_locals["session"]  # the live session
        env = f.f_locals["envelope"]  # the frozen v141 module

    armed ``gm_warp_position_pending`` on the live session, built a
    ``LogoutVital`` frame of its own with the envelope builder, and
    returned ``[]`` -- under a green ``UI_DISPATCH_ACCEPTED`` token.
    That is the round-3 D2 symptom reproduced verbatim with every
    round-3 and round-4 fix installed, because ``answer()`` calls the
    lane from a frame that holds both names and Python hands the callee
    that frame.  Deleting the locals does not close it either: the
    caller's frame in ``runtime.py`` holds the same objects one step
    further up.

    So read this class for what it IS: a way for a lane to describe a
    reply without NEEDING the runtime, which keeps an honest lane honest
    and keeps the composition reviewable in one place.  It is not a
    sandbox, and no allowlist in this file can make it one -- closing
    the reach means the lane must not run on the dispatch path at all
    (a data-only queue drained after ``answer()`` returns, or another
    process).  That is a design question filed for COO, not a docstring
    promise.  What the rules below DO still buy, against an honest lane
    and against a lane that only returns bad data, is real:

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
# more.
#
# ``max_payload_bytes`` 512 ON THE TWO WSTRING ROWS IS A BUDGET, NOT A
# CLAIM ABOUT NAMES, and pf-adversary (round `asw0n3`, D8) is why this
# paragraph now says so.  It used to read "512 is far above any name the
# client can produce", which is a statement about what the field MEANS
# -- exactly the reasoning letter ``20260904_1120`` nonclaim (2) forbids
# this file from doing, in the same file that forbids it.  What is
# actually measured: these payloads are u8 + u64 + tagged wstring, 26
# bytes for a five-character value, and this seam refuses to SEND more
# than 512.  What it does NOT bound is what a client may make an
# answerer PARSE: inbound length is `recv_frame`'s u32, so a two-million
# byte payload decodes and re-encodes (7.3 ms, measured) before anything
# here declines it.  Bounding that is `recv_frame`'s business, filed, not
# taken here -- but it must not be mistaken for a thing this row does.
#
# ``max_frame_bytes`` 1024 IS ALSO A BUDGET, AND THE ENVELOPE IS NOT A
# CONSTANT 32 BYTES (measured 32 / 34 / 35 for values of 5 / 100 / 248
# characters, because the envelope's own length fields widen).  The
# conclusion the row rests on survives the correction and is stated as
# an inequality rather than as an addition: the largest frame a 512-byte
# payload can produce stayed under 550 in every measurement, and 1024
# leaves room for an envelope this lane does not own to grow without
# turning somebody else's change into a dead button, while still
# refusing a frame that is not this shape at all.
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
    # A FIXED-WIDTH CLASS GETS A FIXED WIDTH, NOT HEADROOM.
    # ``PartyCmdVital`` is ``u8 + u64`` with no string, so every payload
    # the lane can emit is exactly 11 bytes -- measured, and pinned from
    # the encoder in ``tests/test_lane_ui_party_cmd_answer.py`` over
    # 4,000 random field pairs.  The two rows above need 512 because a
    # name makes their payload grow; this one does not, and headroom
    # nobody needs is reach nobody reviewed, so the answerer requires
    # EQUALITY against this number rather than treating it as a ceiling.
    # ``max_frame_bytes`` 64 is deliberately NOT exact: the envelope
    # around the payload is ``legacy.make_runtime_vitals``'s and not
    # this lane's, it measured 43 bytes on this commit (the arming proof
    # prints it), and pinning a number this file does not own would turn
    # somebody else's envelope change into this button going silent.
    # THE MEASUREMENT IS STILL TAKEN, ONE FILE OVER, AND THAT IS THE
    # POINT (pf-adversary round m54yxh, D9): the test file asserts the
    # frame is exactly 43 bytes, so an envelope change is caught -- as a
    # RED TEST, which is a message to a person, instead of as a refusal,
    # which is a dead button for a player.  The two places differ in
    # where the breakage lands, and this row chooses the harmless one.
    "UI_PARTY_CMD_ANSWERED": _OutboundShape(
        vital_id=0x2466,
        versions=frozenset((0,)),
        max_payload_bytes=11,
        max_frame_bytes=64,
    ),
    # THE SECOND FIXED-WIDTH CLASS, AND THE SAME CHOICE FOR THE SAME
    # REASON.  ``Community_RemoveFriendVital`` is ``u64 + u64 + u8`` with
    # no string, so every payload the lane can emit is exactly 20 bytes
    # -- measured from the encoder over 4,000 random field triples,
    # including both u64 extremes, in
    # ``tests/test_lane_ui_friend_remove_answer.py`` -- and the answerer
    # requires EQUALITY against this number rather than treating it as a
    # ceiling.  ``max_frame_bytes`` 64 is again deliberately NOT exact:
    # the envelope is ``legacy.make_runtime_vitals``'s and not this
    # lane's, it measured 52 bytes on this commit, and that measurement
    # is pinned in the test file (a RED TEST, which is a message to a
    # person) instead of here (a refusal, which is a dead button).
    "UI_FRIEND_REMOVE_ANSWERED": _OutboundShape(
        vital_id=0x98A1,
        versions=frozenset((0,)),
        max_payload_bytes=20,
        max_frame_bytes=64,
    ),
    # A WSTRING CLASS, SO A CEILING AND NOT A WIDTH.
    # ``Community_RequestBeFriendVital`` is ``u64 + tagged wstring + u8``,
    # so a name moves its width and the fixed-width row above would be
    # wrong here: the same 512/1024 pair the two wstring rows at the top
    # of this registry use, chosen for the same reason and measured the
    # same way (26 bytes for a five-character name, 58 on the wire with
    # ``make_runtime_vitals``'s envelope, which measured 32 bytes for
    # that name and is NOT a constant -- 32/34/35 at 5/100/248
    # characters).  512 still refuses a lane that wants this label to
    # carry a blob.  THE SENTENCE THAT USED TO FINISH THIS COMMENT --
    # "no name the client can type reaches it" -- IS GONE (pf-adversary
    # round asw0n3, D8, paid for the two rows at the top of this
    # registry in round `ncejt8` and here as soon as this row landed):
    # it is a claim about what the field MEANS, which letter
    # ``20260904_1120`` nonclaim (2) forbids this file from making.  512
    # is a send budget, and what a client can make an answerer PARSE is
    # bounded by ``recv_frame``'s u32, not by this row.
    "UI_FRIEND_REQUEST_ANSWERED": _OutboundShape(
        vital_id=0xB9E9,
        versions=frozenset((0,)),
        max_payload_bytes=512,
        max_frame_bytes=1024,
    ),
    # SIX WSTRING FIELDS, NOT ONE, SO THE CEILING IS WIDER BY THE SAME
    # FACTOR.  ``SendMailFields`` is ``u64 + wstring + u64 + wstring*5 +
    # u8`` -- nine positional slots total, two of them u64 and one u8,
    # the other SIX all wstring (one on its own between the two u64
    # fields, five more in a row after the second) -- and every one of
    # those six is the player's to move, the same "a name makes this
    # payload grow" reasoning the 512-byte wstring rows above use for
    # their one field.  Measured:
    # six 100-character fields encode to 1,250 bytes and the minimum
    # (all fields empty but one) encodes to 52.  4096 is chosen as a
    # reviewed budget, not a derived bound -- roughly 512 per field
    # slot, matching the single-field rows' own number rather than
    # inventing a new one -- and it is a CEILING like theirs, so the
    # answerer compares with ``>``.  ``max_frame_bytes`` 8192 keeps the
    # same 2x ratio those rows use for their own envelope headroom; the
    # envelope is ``legacy.make_runtime_vitals``'s, not this lane's, so
    # this number is deliberately not pinned exact here either.
    "UI_SEND_MAIL_ANSWERED": _OutboundShape(
        vital_id=0x6E12,
        versions=frozenset((0,)),
        max_payload_bytes=4096,
        max_frame_bytes=8192,
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
    # AN ENTRY THAT CLAIMS THE REVIEWED OWNER'S NAME MUST BE THE REVIEWED
    # OWNER'S CODE (pf-adversary round 1gc6hl, D-A).  `_ANSWERERS` is a
    # module global and `register_answerer()` is not the only way into it:
    # measured end to end through the real `state.dispatch()`, one line in
    # a `production_allowed = False` lane --
    # `ui_dispatch._ANSWERERS[0x37B1] = (VICTIM, (VICTIM,), forged)` --
    # put a `TeleportVital` frame on the wire under the party label,
    # printed `UI_DISPATCH_ACCEPTED module=<the victim>`, left the shipped
    # answerer's budget untouched, and kept the whole suite and both
    # arming proofs green.  Every check this file had asked about the
    # NAMES STORED IN THE TUPLE, which the writer of the tuple chooses.
    #
    # So when the stored registrar IS the id's reviewed owner, the
    # function is checked by IDENTITY against that module: the reviewed
    # module has to be where this callable actually lives.  A name is
    # copyable and `fn.__module__` is writable; being an attribute of an
    # imported module object is neither.
    #
    # WHAT THIS DOES NOT CLOSE, MEASURED AND NAMED, NOT IMPLIED.  A
    # forger who stores its OWN allowed lane name instead of the owner's
    # is not caught here -- it is then answering under its own name, with
    # its own flag, which is the case the gate above judges.  And nothing
    # in a process can stop a lane that writes into the owner module's
    # namespace.  The real question -- whether the unit of trust is a
    # file, a module object, a function object or a dict entry -- is a
    # COO letter this round, not a patch.
    owner = _ANSWERER_OWNERS.get(vital_id)
    if owner is not None and module_name == owner:
        owner_module = sys.modules.get(owner)
        if owner_module is None or not any(
            value is fn for value in vars(owner_module).values()
        ):
            _say(
                "UI_DISPATCH_GATED id=%s module=%s"
                " reason=not_the_reviewed_owners_own_callable"
                % (_hex(vital_id), module_name)
            )
            return []
    # THE DOOR, BEFORE THE LANE'S CODE RUNS OR ITS BUDGET MOVES
    # (pf-adversary round xqxadg, D7 -- see ``_SESSION_IN_GAME_READS``).
    # Placed after the production gate so a closed lane still reports the
    # reason it is closed, and before ``fn`` so an unauthenticated peer
    # cannot reach an answerer at all -- not its bytes, and not its
    # counter.
    if not _session_is_in_game(session):
        _say(
            "UI_DISPATCH_GATED id=%s module=%s reason=not_in_game"
            % (_hex(vital_id), module_name)
        )
        return []
    # THIS SESSION'S OWN ALLOWANCE FOR THIS VITAL, READ BEFORE THE LANE'S
    # CODE RUNS (pf-adversary round 1gc6hl D-B, round vy1m79 D1/D5 --
    # see ``SESSION_ANSWER_BUDGET``).  Nothing is charged here, because a
    # refusal must be free (D-F); what this decides is whether the lane
    # runs at all.  A session the seam cannot key is refused HERE and not
    # at the charge, or the answerer would do its whole decode /
    # re-encode / compare on every frame forever and only the bytes would
    # be stopped.
    refusal = _allowance_refusal(session, vital_id, 1)
    if refusal:
        _say(
            "UI_DISPATCH_GATED id=%s module=%s reason=%s"
            " budget=%d" % (_hex(vital_id), module_name, refusal,
                            SESSION_ANSWER_BUDGET)
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
    # THE CHARGE, AND IT IS AT THE ACCEPT POINT -- NOT THE SEND POINT
    # (pf-adversary round vy1m79, D7).  This comment said "send point",
    # in the words the token six lines down abandoned for being one layer
    # short of the wire: ``answer()`` returns to ``dispatch()``, which
    # returns to the connection loop, which calls ``sendall``.  A batch
    # that dies on ``SEND_FAILED`` therefore still spends, which is the
    # behaviour we want for a storm guard -- the frames were built and
    # handed over -- but it is not what "send point" means, so it no
    # longer says it.  Only a batch that carries actions costs anything:
    # an answerer returning ``[]`` is the ordinary "nothing for this
    # payload" and must not spend a player's allowance.
    if actions:
        refusal = _charge_session_answer(session, vital_id, len(actions))
        if refusal:
            _say(
                "UI_DISPATCH_ANSWER_REFUSED id=%s module=%s reason=%s"
                % (_hex(vital_id), module_name, refusal)
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
        "UI_DISPATCH_ACCEPTED id=%s module=%s actions=%d spent=%d/%d"
        % (_hex(vital_id), module_name, len(actions),
           _session_answers_spent(session, vital_id), SESSION_ANSWER_BUDGET)
    )
    return actions
