"""ATTACK-POSE-ONE-FIELD-AB-001: the opt-in gate over ActionVital ``+0x30``.

WHAT THIS IS FOR.  ``RE-110-RESULT`` (2026-08-27 18:32, static; the artifact
lives in ``pf_bridge/archive/notes_to_chief_2026-08/20260827_1832_RE-110-
RESULT-POSE-FIELD-POSITIVE-REPEAT-CADENCE-BOUNDED.md``, NOT in this repo)
pinned the field map: the inbound ActionVital handler reads ``u32 +0x30``,
feeds it to the behavior lookup at ``0x00702A10`` and builds a
``CActorTask_UseBehavior`` at ``0x0047AB30``.  Our reply copies the observed
``0xEA7D`` (60029) straight back, and that snapshot has NO ``BEHAVIOR.n_ID =
60029`` row.  ``COO-DECISION 20260904_2141`` ordered this lane to build an
opt-in way to send a resolvable id instead, so an attended run can answer
whether the client then plays an attack animation.

WHAT THIS REPOSITORY ALREADY MEASURED ABOUT THIS EXACT FIELD, which the
attended run must be read against and which pf-adversary was right that an
earlier draft of this docstring left out (D2):

* ``reports/PF_SCENE008_EA7D_INERT_ACTION_CONSUMER_RUNTIME_TRACE_20260816.md``
  (SCENE-008, instrumented runtime): our ACK reaches the handler and
  constructs one ``0xEA7D``/``0x203D`` action with **implementation pointer 0
  and terminal bit 0x08 already set**, which reaches the first update return
  with bit 8 unchanged.  ``docs/FUNCTIONAL_COVERAGE.json`` states the
  consequence plainly: "Acknowledgement is not combat."
* ``docs/EXPERIMENT_LEDGER.md`` SCENE-010: the ``0x702A10`` lookup received
  ``0xEA7D`` at the inbound handler return and was **null** 18 ms after the
  ACK -- AND "Null does not block generic ActionVital construction/queue".
  So a null lookup is not what makes the action inert, and a NON-null lookup
  is therefore not by itself proof that it will not be.
* SCENE-011: keys 278/279 were observed **non-null** in the same registry.
* SCENE-012: ``0x44EB1D -> 0x4758D0`` is a strict squared-distance gate for
  EA7D whose accepted keys carry ``n_RANGE = 75``; the live scalar was never
  captured, so an out-of-range click can refuse a perfectly resolvable id.

Taken together those say the A/B can come back negative for at least three
different reasons -- id does not resolve, id resolves but the action is still
built inert, id resolves but the range gate refuses -- and an eyeball on the
client cannot tell them apart.  That question is in the letter to COO with
this round (``pf_bridge/notes_to_chief/20260904_2240_LANE-B-TO-COO-...``) and
is NOT answered here.  This module ships the arm; it does not claim the
instrument is sufficient.

``reports/PF_COMBAT_BIND001_EA7D_BEHAVIOR_SELECTION_STATIC_CHECKPOINT_
20260816.md`` carries a standing stop rule that names "alter ActionVital" and
resumes only when a named item/container source reaches the actor raw byte.
That condition is NOT met -- ``equip_type_of_performer`` returning ``None`` is
this module's own statement that it is not met.  What lets this land anyway is
narrow and must stay narrow: nothing here alters production ActionVital.  With
``PF_POSE_TRIAL`` unset the composed bytes and the console are identical to
main, the alteration exists only inside one attended process an owner armed
by hand, and ``COO-DECISION 20260904_2141`` is the decision to run that one
attended experiment.  ``COO-DECISION 20260904_2346`` point 2 has since ruled
on the question this paragraph used to leave open: BIND001's stop rule guards
production ``ActionVital``, this module alters none of it (unarmed output is
byte-identical, pinned by test), the arm is opt-in per process and attended
only, and Panya's 21:15 live order is the standing authorization to run it --
so the module stays and is not withdrawn.

WHY AN ENVIRONMENT VARIABLE AND NOT AN ``--pose-trial`` COMMAND-LINE FLAG.
The ticket names the flag ``--pose-trial <behavior_id|auto>``; argument
parsing lives in ``app.py``, which is chief's file, and this lane may not
edit it.  ``gm/speed_wire.py``'s COO-approved ``PF_SPEED_TRIAL`` gate solved
the same problem by reading the PROCESS environment, and the attended bridge
already arms trials that way (``PFGM_FORCE=1``), so ``set PF_POSE_TRIAL=280``
before the boot needs nothing from anybody else.

TWO THINGS THE OPERATOR MUST KNOW, both raised by pf-adversary (D11/D12):
the variable arms the PROCESS, so every connection this server serves gets
the mutated selector, not one session; and ``set`` is per-window while
``setx`` writes the registry -- ``setx`` would arm every future boot
invisibly, so use ``set``.

FAIL-CLOSED.  Unset, empty, malformed or ``auto``-without-provenance all ship
the production bytes.  Only an explicitly named numeric selector changes a
byte, and the console says which one, next to what the request carried.
"""
import os

# The variable an owner sets before the boot.  ASCII, ``PF_``-prefixed, the
# same family as ``PFGM_FORCE`` and ``PF_SPEED_TRIAL``.
POSE_TRIAL_ENV = "PF_POSE_TRIAL"

# The word that asks this module to resolve the selector itself.
AUTO = "auto"

# The four states the environment can be in.  Spelled as constants because
# an attended tester greps them off a cp874 console and the tests name the
# same strings; ASCII and no spaces, for the reason every console token in
# this lane is.
TRIAL_UNSET = "unset"
TRIAL_MALFORMED = "malformed"
TRIAL_NO_PROVENANCE = "auto_no_equip_type_provenance"
TRIAL_ARMED = "armed"

# *** THIS TABLE CANNOT BE RE-DERIVED INSIDE THIS REPOSITORY, and saying so is
# the point of this comment.  It is transcribed from ``RE-110-RESULT`` T2 (the
# pf_bridge archive path in the module docstring); chief re-confirmed the
# crosswalk ``EQUIP_VALUE.n_EQUIPTYPE -> n_ATTACK_SKILL -> BEHAVIOR.n_ID``
# [PROVEN] on 2026-09-04 14:05.  Neither ``CONSTDATA_TH__EQUIP_VALUE.tsv`` nor
# ``CONSTDATA_TH__BEHAVIOR.tsv`` is tracked here, so NO test in this repository
# can catch a mistyped row -- pf-adversary measured exactly that (D3: changing
# 280 to 281 leaves the suite green).  Two things bound the damage rather than
# hide it: the ticket sweeps all six ids one at a time, so a wrong row shows up
# as "that one value produced no pose" instead of a wrong conclusion; and the
# console token prints the number actually sent, so the attended log can be
# re-read against the table afterwards.  Anyone who lands the tables here
# should replace this comment with a test that re-derives the six rows.
#
# Animation names from the same table, for the attended log:
#   280 `_C_ATTACK_000;30`   284 `_C_ATTACK_000;28`   288 `_C_ATTACK_000;24`
#   282 `_C_ATTACK_000;17`   290 `_C_ATTACK_000;24`   286 `_C_ATTACK_018;28`
ATTACK_BEHAVIOR_BY_EQUIP_TYPE = {
    1: 280,
    2: 284,
    8: 288,
    16: 282,
    32: 290,
    64: 286,
}

# The order the ticket asks the attended run to walk the six ids in.  Stored
# as EQUIP TYPES, not as a second copy of the ids, so the module holds each
# behavior id exactly once and ``TICKET_SWEEP_ORDER`` cannot drift from the
# table above (pf-adversary D3: the earlier version carried the six numbers
# twice).  Resolves to 280 -> 284 -> 288 -> 282 -> 290 -> 286.
TICKET_SWEEP_EQUIP_TYPES = (1, 2, 8, 16, 32, 64)
TICKET_SWEEP_ORDER = tuple(
    ATTACK_BEHAVIOR_BY_EQUIP_TYPE[equip_type]
    for equip_type in TICKET_SWEEP_EQUIP_TYPES
)

U32_MAX = 0xFFFFFFFF

_HEX_DIGITS = "0123456789abcdefABCDEF"


def equip_type_of_performer():
    """The performer's equipped weapon type, or ``None`` when unknown.

    ``None`` today, always.  ``RE-110`` nonclaim 5 refuses to pick an attack
    behavior for Arena01 without an equip-type crosswalk for the current
    actor, and ``COO-DECISION 20260904_2141`` point 2 spells out what follows:
    ``auto`` is available only where the equip type has a provenance, and
    where it does not, the trial takes an explicit ``<id>`` and NOTHING is
    guessed.

    NOT "no source exists" -- pf-adversary was right to refuse that phrasing
    (D6), and the module that owns the AvatarAttr field table records this
    lane making exactly that mistake about exactly that block, in its own
    header (G1: do not declare a source absent without looking).  That module
    is described here rather than named, on purpose: a guard in its test file
    forbids every other module from mentioning it by name, and a docstring is
    not a reason to weaken a guard -- read it at
    ``src/pirateforce_foundation/`` for the AvatarAttr wire fields.

    What is MEASURED: there is no equipped-weapon column in ``migrations/``
    and no ``EQUIP_VALUE`` reader in this tree.  What is OPEN: that AvatarAttr
    table names four ``equip_projection_slot_0x…`` fields plus
    ``n_SLOT_RHAND`` and ``n_SLOT_LHAND``.  Whether any of those yields an
    equip TYPE (rather than an item key or a render slot) is unanswered, and
    answering it is an RE ask, not something to settle by reading a field
    name.

    AND EVEN WITH AN ANSWER, ``auto`` STILL WOULD NOT LIGHT UP FROM HERE
    ALONE: nothing plumbs an actor into this module -- ``selector_for_reply``
    is handed the request's echoed selector and nothing else -- so turning
    ``auto`` on needs a signature change through
    ``action_ack.make_scene007_action_ack`` as well.  An earlier draft of this
    docstring claimed "one place, one test"; pf-adversary measured that as
    false (D7) and it is withdrawn.
    """
    return None


def _parse_selector(raw):
    """``(state, value)`` for one raw environment string.

    Never raises -- see ``trial_opening``, which is where the guarantee is
    enforced, because a caller that reached this function directly would not
    get it.
    """
    if not isinstance(raw, str):
        return (TRIAL_MALFORMED, None)
    text = raw.strip()
    if text == "":
        # ``set PF_POSE_TRIAL=`` on the bridge's cmd.exe leaves an empty
        # string, not an absent key: the operator who cleared it did the
        # right thing and must not be told she made a mistake.
        return (TRIAL_UNSET, None)
    if text.lower() == AUTO:
        equip_type = equip_type_of_performer()
        if equip_type is None:
            return (TRIAL_NO_PROVENANCE, None)
        behavior = ATTACK_BEHAVIOR_BY_EQUIP_TYPE.get(equip_type)
        if behavior is None:
            return (TRIAL_NO_PROVENANCE, None)
        return (TRIAL_ARMED, behavior)
    body = text[2:] if text[:2].lower() == "0x" else None
    if body is not None:
        if body == "" or any(char not in _HEX_DIGITS for char in body):
            return (TRIAL_MALFORMED, None)
        value = int(body, 16)
    else:
        # Decimal digits ONLY.  ``int(text, 0)`` would also swallow ``0b1``,
        # ``0o7`` and ``1_0``, and a selector the operator did not mean to
        # type is exactly the thing that costs an attended round.
        #
        # LENGTH-CAPPED BEFORE ``int()``, because CPython >= 3.11 raises
        # ValueError past 4300 digits and this function runs on the dispatch
        # path: pf-adversary drove 4400 nines through the real dispatch and
        # watched the exception leave ``state.dispatch()`` (D1).  The cap is
        # belt to ``trial_opening``'s braces -- ten digits is already more
        # than a u32 can hold, so nothing an operator can mean is refused by
        # it.
        if len(text) > 10 or not text.isdigit() or not text.isascii():
            return (TRIAL_MALFORMED, None)
        value = int(text)
    if not 0 <= value <= U32_MAX:
        return (TRIAL_MALFORMED, None)
    return (TRIAL_ARMED, value)


def trial_opening(environ=None):
    """Which ONE selector the trial gate is armed for, if any.

    Returns ``(TRIAL_UNSET, None)``, ``(TRIAL_MALFORMED, None)``,
    ``(TRIAL_NO_PROVENANCE, None)`` or ``(TRIAL_ARMED, <u32>)``.  NEVER
    raises, and the whole read is inside the ``try`` for that reason: this
    runs inside ``state.dispatch()`` and the frozen ``game_listener`` around
    it has zero except handlers (interlock X07), so a gate that raises kills
    the thread.  An earlier version had only ``source.get`` inside the
    ``try``; pf-adversary reached the ``int()`` past it with a 4400-digit
    value and measured the exception escaping dispatch (D1).
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(POSE_TRIAL_ENV)
        if raw is None:
            return (TRIAL_UNSET, None)
        return _parse_selector(raw)
    except Exception:  # noqa: BLE001 - see the docstring
        return (TRIAL_MALFORMED, None)


def console_token(sent, echoed, state):
    """The one line an attended run greps, for one composed reply.

    The prefix ``POSE_TRIAL sent=+0x30=<id> control|mutant`` is the shape
    ``ATTACK-POSE-ONE-FIELD-AB-001`` asks for, so a grep written against the
    ticket still matches.  ``echo=`` is appended because the arm word alone
    lies in two directions (pf-adversary D5): ``control`` means "we sent back
    exactly what the request carried", so arming 280 against a request that
    itself carried 280 prints ``control``, and arming 60029 against a request
    carrying something else prints ``mutant``.  With both numbers on the line
    the reader can always tell which happened; with only the arm word she
    cannot.

    A refused arming keeps the same ``sent=`` field -- so one grep finds
    every reply -- behind a different first word, because "the door was
    closed" and "the door was open at the echo value" are two different runs
    and must not read alike.
    """
    arm = "control" if sent == echoed else "mutant"
    head = "POSE_TRIAL" if state == TRIAL_ARMED else (
        "POSE_TRIAL_REFUSED " + state)
    return "%s sent=+0x30=%d %s echo=%d" % (head, sent, arm, echoed)


def selector_for_reply(echoed, environ=None):
    """``(u32 to put at +0x30, console line or None)`` for one reply.

    With the environment unset this returns ``(echoed, None)``: the same
    integer the production line composes and NO console line at all.  Both
    halves are the contract -- ``COO-DECISION 20260904_2141`` point 2 says a
    boot without the flag is byte-identical to production, and a line that
    only appears in the log is still a difference an attended reader has to
    explain.
    """
    state, value = trial_opening(environ)
    if state == TRIAL_UNSET:
        return (echoed, None)
    sent = echoed if value is None else value
    return (sent, console_token(sent, echoed, state))


def parse_trial_list(raw):
    """``tuple[int, ...]`` or ``None`` for one comma-separated selector list.

    ``COO-DECISION 20260905_0248`` moves the trial from ``selector_for_reply``
    (one selector, armed for the whole process, read only by the SCENE-007
    scenario gate) to the production ``_dispatch_mob_combat`` path, which the
    ticket's own sweep needs to walk six ids one hit at a time:
    ``PF_POSE_TRIAL=280,284,288,282,290,286``.

    Reuses ``_parse_selector``'s per-token grammar (decimal digits only, or
    ``0x``-prefixed hex, length-capped before ``int()`` for the D1 reason
    given there) so a token this module already accepts alone is accepted
    the same way inside a list.  Returns ``None`` -- the whole list is
    malformed -- on ANY bad or empty token (a leading/trailing/doubled comma,
    ``auto`` without provenance, anything ``_parse_selector`` itself
    refuses) rather than dropping the bad token: an owner who meant to arm
    six ids must not silently get five, with no line saying which one it
    lost.
    """
    parts = [part.strip() for part in raw.split(",")]
    values = []
    for part in parts:
        state, value = _parse_selector(part)
        if state != TRIAL_ARMED:
            return None
        values.append(value)
    return tuple(values)


def trial_list_opening(environ=None):
    """``(state, tuple_or_None)`` for the list-cycling gate.

    Mirrors ``trial_opening``'s contract -- NEVER raises, the whole read is
    inside the ``try`` for the same reason (this runs inside
    ``state.dispatch()`` under the frozen, except-handler-free
    ``game_listener``, interlock X07) -- but for a comma-separated list
    instead of one selector.  Unset or blank is ``(TRIAL_UNSET, None)``,
    exactly like ``trial_opening``; a single bare value (no comma) is a
    well-formed one-element list, not a special case.
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(POSE_TRIAL_ENV)
        if raw is None:
            return (TRIAL_UNSET, None)
        text = raw.strip()
        if text == "":
            return (TRIAL_UNSET, None)
        values = parse_trial_list(text)
        if values is None:
            return (TRIAL_MALFORMED, None)
        return (TRIAL_ARMED, values)
    except Exception:  # noqa: BLE001 - see trial_opening
        return (TRIAL_MALFORMED, None)


def selector_for_hit(hit_number, environ=None):
    """``(selector, console line)`` for one accepted production hit, or
    ``(None, None)``/``(None, refusal line)`` when nothing should be sent.

    Unlike ``selector_for_reply`` (armed for the whole scenario-gated
    process, one selector, falls back to the request's own echoed value so
    SOMETHING is always composed) this gate feeds a call site that runs on
    an ORDINARY, unflagged boot for EVERY accepted hit against a real field
    mob (``COO-DECISION 20260905_0248``): the inherited v141 dispatch has
    already echoed that same request's own ``+0x30`` back before
    ``_dispatch_mob_combat`` ever runs, so unset or malformed both return
    ``None`` for the selector -- compose and send NOTHING extra -- rather
    than a redundant second echo of bytes main already sent.  Only an
    explicitly armed list changes what one hit puts on the wire.

    ``hit_number`` is the caller's own count of ACCEPTED hits this session
    (``state.mob_combat_hit_count``, already incremented for the hit this
    call answers) and is 1-indexed; it selects ``(hit_number - 1) %
    len(values)`` off the armed list, so hit 1 is always the first id and
    the sixth ticket sweep click lands on the sixth id, then wraps.
    """
    state, values = trial_list_opening(environ)
    if state == TRIAL_UNSET:
        return (None, None)
    if state == TRIAL_MALFORMED:
        return (None, "POSE_TRIAL_REFUSED malformed hit=%d" % hit_number)
    index = (hit_number - 1) % len(values) if hit_number >= 1 else 0
    sent = values[index]
    return (sent, "POSE_TRIAL sent=%d hit=%d" % (sent, hit_number))


def boot_banner(environ=None):
    """The line a boot prints when, and only when, the variable is set.

    WHY IT EXISTS (pf-adversary D4).  The reply token fires at most ONCE per
    process -- ``runtime.py`` latches ``scene_action_ack_sent`` -- and only
    after four preconditions hold (an ``action_ack`` scenario, the remote
    spawned, a kind-1 hostile target captured, a selected character).  An
    operator who arms the variable and boots without the scenario, or never
    gets the target capture, sees a console byte-identical to an unarmed
    boot.  "We ran the trial and the client did not swing" would then be
    unfalsifiable.  This line makes an armed boot say so at boot, so silence
    means unarmed and nothing else.

    Returns ``None`` while the variable is unset, which is what keeps an
    unarmed boot line-for-line identical to production.
    """
    state, value = trial_opening(environ)
    if state == TRIAL_UNSET:
        return None
    if state == TRIAL_ARMED:
        return "POSE_TRIAL_BOOT armed=%d" % value
    return "POSE_TRIAL_BOOT refused=" + state


def _announce_at_import():
    """Print ``boot_banner`` once, at import, and never raise doing it.

    Import time is the only hook this lane owns that runs on every boot:
    ``app.py`` and ``runtime.py`` belong to chief.  Guarded twice over -- the
    banner is ``None`` unless somebody armed the variable, and a print that
    raises (closed or broken stdout) must not take an import down with it.
    """
    try:
        line = boot_banner()
        if line is not None:
            print(line)
    except Exception:  # noqa: BLE001 - an import never fails on a log line
        pass


_announce_at_import()
