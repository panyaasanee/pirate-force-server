"""LANE-A (WORLD): push the pinned 0x709E response AT dialog-open time.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  Nothing
yet.  This module is a standalone, importable dispatch function; nothing in
``runtime.py`` calls it, so it changes zero wire behavior on ``main`` today.
``production_allowed`` below is ``False`` for the same two reasons
``lane_a_choose_npc_scene1.py`` gives its own flag: (1) unwired code cannot
be a live risk either way, and (2) even once wired, flipping this on is a
call for a LATER round, after the ``runtime.py`` wiring this file's own
docstring specifies below has actually landed and been read back by
pf-adversary at least once. See "WHAT THE CORE-REQUEST NEEDS TO DO, EXACTLY"
below for the one-line letter that turns this file from inert into live.

WHY THIS FILE EXISTS, AND WHY BRANCH 6 -- NOT 2 OR 3.  RE-189
(``pf_bridge/notes_to_chief/consumed/
20260901_1008_RE-189-RESULT-PLUS18-LOCAL-UI-AND-SERVER-BRANCH-MATRIX.md``,
Job 1) found, over the complete bounded client vtable/factory graph, that
``[SystemSetting_LogoutConfirm+0x18]`` -- the field every one of this
project's existing logout response shapes (PF-012 ack, PF-013 close,
PF-016/PF-028 response-first, PF-031 chat-push) has been trying to flip --
has exactly one writer in that graph, and it is the client's OWN
``BUTTON_CANCEL`` local-UI-tree lookup (``0x7196F8``), never an inbound
network payload.  That gate is a PRECONDITION every existing profile fails
structurally: they all reply to the LogoutVital 0x1B40 REQUEST itself, which
per this project's own R40 decode only ever arrives AFTER the client has
already built its logout-confirmation dialog locally (and hence already
either satisfied or failed to satisfy that precondition on its own, with no
help a reply to that same request could have offered).

RE-189's Job 2 rates six possible new server response shapes for the still-
open GT-033/GT-184/GT-186 question. Branches 2 (timer variants on the
existing ack/close profiles) and 3 (reorder/duplicate of the same
request-paired actions) are also rated ``BUILDABLE``, but both still fire
relative to the LogoutVital REQUEST -- i.e. still after the dialog (and its
``+0x18`` binding) already exists or doesn't, changing nothing about
whether the precondition was met. Branch 6 is different in kind, not just
in timing: this project's server ALREADY detects, byte-exactly, the one
inbound frame RE-016/HYP-PF-016 correlated 7/7 across two captured sessions
with the client's local logout-dialog actually opening -- the full-form
GetWorldInfoVital (0x3D4B), a deterministic 268-byte PC arriving 2-14s
BEFORE the LogoutVital that follows it -- and today deliberately does not
reply to it (``runtime.py``'s own ``_dispatch_worldinfo_observation``,
comment: "the observed server behavior at dialog-open time (no response) is
preserved"). Branch 6 pushes the already-pinned, byte-identical HYP-PF-028
``ReturnSelectServerVital`` (0x709E) response AT THAT MOMENT instead --
unsolicited, ahead of any LogoutVital -- so an attended run can, for the
first time, observe whether 0x709E lands while the dialog (and its
``+0x18`` field) is already known, by RE-189's own correlation evidence, to
exist. This module builds ONLY branch 6, per this round's instruction; it
does not build 2 or 3.

WHAT THIS FILE HONESTLY CANNOT CLAIM (see RE-189's own "nonclaims" section,
items 1-2, which this file inherits rather than overriding). RE-189 proved
the negative only over the complete bounded client vtable/factory graph it
measured -- it does not claim no pointer-aliased write to ``+0x18`` exists
anywhere in the whole client program, and it does not claim server traffic
can never influence the client's local UI construction indirectly. Nor does
this file's own trigger correlation claim causation: "GetWorldInfoVital
full-form correlates 7/7 with dialog-open across two sessions" is a
measured correlation, not a proof that the dialog is open at the exact
instant this module's response would be queued, and it is not a claim that
pushing 0x709E at this moment WILL transition the client -- that is exactly
what GT-184 and GT-186 exist to check, once this module is wired in AND run
attended (``pf_bridge/GAME_TEST_QUEUE.md``, both currently ``[BLOCKED]``
pending "whatever NEW response/sequence the implementing lane builds").

WHY THE GATE IS A MODULE FLAG, NOT A CLI SCENARIO FLAG. This lane's charter
forbids building anything reachable only behind a ``--something-scenario``
probe flag -- a probe is not the default runtime path and therefore not
this lane's work. ``production_allowed`` here is the OPT-IN-BY-DEFAULT-OFF
convention every ``lane_hooks`` module in this project already uses (see
``lane_hooks/lane_a_choose_npc_scene1.py``'s own docstring for the
identical argument): a module-scope boolean a human flips after reading the
tests and, ideally, after one attended parity check -- not a runtime CLI
flag a player's own session has to opt into for the fix to exist at all.
Today this module is not even IMPORTED by ``runtime.py``, so the flag is
inert either way; it exists now so the CORE-REQUEST wiring below has
something to gate on the day it lands, instead of shipping live the same
round it is first read.

WHAT THE CORE-REQUEST NEEDS TO DO, EXACTLY (written by someone else, not
this lane -- this is only the pointer that letter needs).

1. Counter init, mirroring the existing HYP-PF-031 one-shot latch exactly:
   ``runtime.py:1059`` currently reads
   ``self.logout_chat_push_count = 0`` (with its own comment, "HYP-PF-031
   one-shot latch: the unsolicited return-select push may leave this
   session exactly once."). Add, immediately alongside it, a new line:
   ``self.logout_dialog_open_push_count = 0`` with an equivalent comment
   naming this module's own hypothesis id (see "PROVISIONAL HYPOTHESIS ID"
   below).
2. Import, at the top of ``runtime.py`` alongside its other
   ``logout_hypothesis``/lane-module imports:
   ``from .logout_dialog_open_hypothesis import (
   dispatch_logout_dialog_open_hypothesis)``.
3. Call site: ``runtime.py``'s ``_dispatch_worldinfo_observation``
   (currently ``runtime.py:1983-2013``) is the ONLY place in ``runtime.py``
   that already both classifies an inbound 0x3D4B frame with
   ``classify_worldinfo_frame`` and sits behind the sequence guard
   (``self.teleport_sent``, ``self.runtime_ack_sent``,
   ``self.foundation.selected is not None``) this module's own guard
   re-derives independently. Two shapes were considered; **prefer (a)**
   (pf-adversary review this round, finding 4, ruled out (b) as written --
   see below):
   (a) **PREFERRED.** Add a NEW routing branch in the big
   ``nested_id``-keyed dispatch chain (``runtime.py`` around line
   5528-5538, right next to the existing
   ``LOGOUT_RESPONSE_POLICY_WORLDINFO_FIRST`` branch that currently routes
   0x3D4B to ``self._dispatch_worldinfo_observation(parsed)``) that instead
   calls ``dispatch_logout_dialog_open_hypothesis(self, parsed, legacy)``
   directly, keyed on a NEW ``logout_hypothesis_scenario.response_policy``
   value this lane does not define (that constant lives in
   ``logout_hypothesis.py``, which is also out of this lane's scope this
   round -- flag it back to this lane or to whoever owns that schema edit).
   Because this is a top-level routing branch, not a nested call, this
   module's own unconditional ``self.rx_frames += 1`` is the ONLY increment
   for that frame -- no double-count.
   (b) **NOT RECOMMENDED AS WRITTEN.** Threading a boolean/flag through
   ``_dispatch_worldinfo_observation`` itself so its own ``full_form``
   branch (``runtime.py:1996-2012``) calls
   ``dispatch_logout_dialog_open_hypothesis(self, parsed, legacy)`` in
   addition to that function's own body would double-count
   ``self.rx_frames`` for every such frame: ``_dispatch_worldinfo_observation``
   already increments it at its own entry (``runtime.py:1994``), and this
   module's dispatch function increments it again, unconditionally, with no
   parameter to suppress that for a nested-call scenario. This project
   already has the correct idiom for a nested, additively-invoked dispatch
   function NOT double-counting -- see ``_dispatch_mob_combat``
   (``runtime.py:4113-4127``), which documents explicitly that it skips its
   own ``rx_frames`` increment because the caller already counted the
   frame. If (b) is chosen anyway (e.g. to preserve call-site locality),
   the CORE-REQUEST must add that same carve-out -- do not wire (b) without
   it.
   Either shape must preserve the existing worldinfo-storage side effect
   (``self.worldinfo_last_payload``, ``self.worldinfo_stored_count``) for
   every OTHER scenario/policy untouched -- this module's dispatch function
   does not store anything itself (see "WHAT THIS MODULE DOES NOT DO"
   below), so if the storage behavior is still wanted under this new policy
   too, the wiring must call both.
4. A companion "leave LogoutVital unanswered under this policy" routing
   branch, mirroring HYP-PF-031's own
   ``_dispatch_logout_chat_push_logout_no_reply`` (``runtime.py:2105-2121``),
   may also be needed depending on which shape (3) takes -- this module
   does not build or specify that function; it is an open wiring question
   for the CORE-REQUEST author to resolve, not a decision this lane is
   making on runtime.py's behalf.

PROVISIONAL HYPOTHESIS ID.  ``docs/HYPOTHESIS_LEDGER.json`` and every
``HYP-PF-0NN`` tag already in ``src/`` top out at ``HYP-PF-039`` as of this
round (checked by grep, not reserved by this lane -- editing that ledger
file is out of this lane's scope this round). The success label below uses
``HYP_PF_040`` as a provisional tag; whoever writes the CORE-REQUEST and
registers the ledger entry should confirm ``040`` is still free at wiring
time and rename the label here (and in the paired test file) together with
the ledger entry if it is not.

WHAT THIS MODULE DOES NOT DO.  It does not touch ``self.worldinfo_last_payload``
or ``self.worldinfo_stored_count`` -- those belong to the existing
HYP-PF-016 storage behavior, and this module's caller decides whether both
run.  It never re-implements ``classify_worldinfo_frame`` or
``make_return_select_server_response`` -- both are imported from
``logout_hypothesis`` unchanged, the same way
``_dispatch_logout_chat_push_hypothesis`` reuses the latter for its own
composer.  It never reads the frame's payload bytes for content (the
full-form classification is the trigger, not an input to compose from), it
never writes to the store, and it never touches a socket.

ONE-SHOT, FAIL-CLOSED, SAME GUARD SHAPE AS HYP-PF-031's OWN CHAT-PUSH
DISPATCH.  Classification wrong -> named no-reply event.  No selected
character -> named no-reply event.  Wrong sequence (teleport/runtime-ack
not yet sent) -> named no-reply event.  Already pushed once this session ->
named no-reply event.  Composer refuses (frozen hash-pin drift) -> named
no-reply event, exception repr included for diagnosis.  Success -> exactly
one named event, one one-shot counter increment, and the single
``(label, pc, frame, delay)`` action tuple this project's dispatch
convention already returns everywhere else.
"""
from __future__ import annotations

from typing import Any

from .logout_hypothesis import (
    classify_worldinfo_frame,
    make_return_select_server_response,
)

# See "WHY THE GATE IS A MODULE FLAG, NOT A CLI SCENARIO FLAG" above. Flip
# only after the CORE-REQUEST wiring (see this module's own docstring,
# "WHAT THE CORE-REQUEST NEEDS TO DO, EXACTLY") has landed on runtime.py AND
# this lane has re-read tests/test_logout_dialog_open_hypothesis.py with
# pf-adversary at least once more, ideally with an attended GT-184/GT-186
# pass confirming (or falsifying) the client transition.
production_allowed = False

DIALOG_OPEN_PUSH_EVENT = "logout_dialog_open_hypothesis_return_select_pushed"
DIALOG_OPEN_PUSH_LABEL = (
    "HYP_PF_040_LOGOUT_DIALOG_OPEN_RETURN_SELECT_SERVER_UNSOLICITED"
)


def dispatch_logout_dialog_open_hypothesis(
    self: Any, parsed: Any, legacy: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Push the pinned 0x709E response once, on the dialog-open frame only.

    Duck-typed on ``self`` exactly the way every other HYP-PF dispatch
    function in ``runtime.py`` is: this reads ``self.events`` (a list, will
    be appended to), ``self.foundation.selected``, ``self.teleport_sent``,
    ``self.runtime_ack_sent``, and ``self.logout_dialog_open_push_count``
    (an ``int`` one-shot latch the caller must initialize to ``0`` -- see
    the module docstring's CORE-REQUEST section, point 1, for the exact
    sibling init line this new one belongs next to). ``self.rx_frames`` is
    incremented on every call, mirroring ``_dispatch_worldinfo_observation``
    and ``_dispatch_logout_chat_push_hypothesis``'s own convention so a
    frame this dispatch sees is still counted even when refused.

    ``parsed`` must expose whatever ``classify_worldinfo_frame`` itself
    reads (``outer_id``, ``outer_version``, ``outer_mask``, ``nested_id``,
    ``nested_version``, ``vital_count``, ``nested_payload``) -- this
    function does not read any of those fields directly; it only forwards
    ``parsed`` to that classifier, unchanged, and reuses its answer.

    ``legacy`` is forwarded to both ``classify_worldinfo_frame`` and
    ``make_return_select_server_response`` unchanged; this function does
    not import or open ``current/pf_login_game_server_v141.py`` itself.

    Returns ``[]`` on every refusal path (each one paired with a distinct
    named event on ``self.events`` so an attended run's console log can be
    lined up against screenshot timestamps -- same discipline
    ``lane_a_choose_npc_scene1.py``'s own console lines follow), or exactly
    one ``(label, pc, frame, delay)`` tuple -- the same 4-tuple shape every
    other dispatch function in this project already returns -- on success.
    """
    self.rx_frames += 1
    classification = classify_worldinfo_frame(legacy, parsed)
    if classification != "full_form":
        self.events.append(
            f"logout_dialog_open_hypothesis_{classification}_no_reply"
        )
        return []
    if self.foundation.selected is None:
        self.events.append(
            "logout_dialog_open_hypothesis_no_selected_no_reply"
        )
        return []
    if not self.teleport_sent or not self.runtime_ack_sent:
        self.events.append(
            "logout_dialog_open_hypothesis_wrong_sequence_no_reply"
        )
        return []
    if self.logout_dialog_open_push_count:
        self.events.append(
            "logout_dialog_open_hypothesis_already_sent_no_reply"
        )
        return []
    # The composer independently re-pins the 0x709E PC/frame sha256 against
    # the frozen HYP-PF-028 constants and raises on any drift, so no
    # unpinned byte can reach the queue on this path -- same guarantee
    # HYP-PF-031's own chat-push dispatch relies on for the same composer.
    try:
        pc, frame = make_return_select_server_response(legacy)
    except (ValueError, RuntimeError) as exc:
        self.events.append(
            "logout_dialog_open_hypothesis_compose_refused_no_reply_"
            f"{exc!r}"
        )
        return []
    self.logout_dialog_open_push_count += 1
    self.events.append(DIALOG_OPEN_PUSH_EVENT)
    return [(DIALOG_OPEN_PUSH_LABEL, pc, frame, 0.0)]
