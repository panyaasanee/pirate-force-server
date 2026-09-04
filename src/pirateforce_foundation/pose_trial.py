"""ATTACK-POSE-ONE-FIELD-AB-001: the opt-in gate over ActionVital ``+0x30``.

WHAT THIS IS FOR.  ``RE-110-RESULT`` (2026-08-27 18:32, static, closed
positive on this one point) pinned the field map: the inbound ActionVital
handler reads ``u32 +0x30``, feeds it to the behavior lookup at
``0x00702A10`` and builds a ``CActorTask_UseBehavior`` at ``0x0047AB30``.
Our reply copies the observed ``0xEA7D`` (60029) straight back, and the
gamedata snapshot has NO ``BEHAVIOR.n_ID = 60029`` row -- so today's reply
carries a selector the client cannot resolve, which is the standing
explanation for why a player walks up, stands still and watches damage
numbers appear instead of swinging.  The crosswalk that DOES resolve is
``EQUIP_VALUE.n_EQUIPTYPE -> n_ATTACK_SKILL -> BEHAVIOR.n_ID`` (chief
2026-09-04 14:05 re-confirmed it ``[PROVEN]``).

WHAT THIS IS NOT.  It is not a production change and it never becomes one
by itself.  ``RE-110``'s own ``BUILD_IMPACT`` forbids changing production
composition until an attended one-field A/B has answered whether the client
actually plays an attack animation for a resolvable id, and ``COO-DECISION
20260904_2141`` re-states that as this module's contract: with the
environment unset, a boot is byte-for-byte AND line-for-line the production
baseline (``tests/test_pose_trial.py`` pins both, against the real composer
and with a mutation of this module's own gate to prove the pin can fail).

WHY AN ENVIRONMENT VARIABLE AND NOT AN ``--pose-trial`` COMMAND-LINE FLAG.
The ticket names the flag ``--pose-trial <behavior_id|auto>``; argument
parsing lives in ``app.py``, which is chief's file, and this lane may not
edit it.  The same problem was already solved in this repository once, in
the shape this module copies: ``gm/speed_wire.py``'s ``PF_SPEED_TRIAL``
owner-only gate (COO-approved) reads the PROCESS environment, so the person
who opens the door is the owner, in her own session, in the minute she is
watching, and the door closes by itself when the process dies.  The attended
bridge already arms trials this way (``PFGM_FORCE=1``, ``PF_SPEED_TRIAL``),
so ``set PF_POSE_TRIAL=280`` before the boot needs nothing from anybody
else.  The PR body carries the one-line ask for chief to add
``--pose-trial`` in ``app.py`` as an alias that sets this same variable;
until that lands, the variable IS the flag and the trial is bootable.

FAIL-CLOSED, IN THE SAME SHAPE ``PF_SPEED_TRIAL`` USES.  Unset, empty,
malformed or ``auto``-without-provenance all ship the production bytes.
Only an explicitly named numeric selector changes a byte, and the console
says which one on every single reply, so the attended log can be read
without trusting the tester's memory of what she typed.
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

# RE-110-RESULT T2, verbatim: n_EQUIPTYPE -> n_ATTACK_SKILL (= BEHAVIOR.n_ID).
# Kept here as data rather than a comment because ``auto`` will need exactly
# this table the day an equipped-weapon type gets a provenance, and a second
# hand-copy of it is how the two start disagreeing.  The animation names the
# ids resolve to, from the same table: 280 `_C_ATTACK_000;30`, 284
# `_C_ATTACK_000;28`, 288 `_C_ATTACK_000;24`, 282 `_C_ATTACK_000;17`, 290
# `_C_ATTACK_000;24`, 286 `_C_ATTACK_018;28`.
ATTACK_BEHAVIOR_BY_EQUIP_TYPE = {
    1: 280,
    2: 284,
    8: 288,
    16: 282,
    32: 290,
    64: 286,
}

# The sweep order the ticket asks the attended run to walk, kept in the
# ticket's order and not sorted: 280 -> 284 -> 288 -> 282 -> 290 -> 286.
TICKET_SWEEP_ORDER = (280, 284, 288, 282, 290, 286)

U32_MAX = 0xFFFFFFFF

_HEX_DIGITS = "0123456789abcdefABCDEF"


def equip_type_of_performer(state=None):
    """The performer's equipped weapon type, or ``None`` when unknown.

    ``None`` today, always, and that is a measurement rather than a stub:
    ``RE-110`` nonclaim 5 refuses to pick an attack behavior for Arena01
    without an equip-type crosswalk for the current actor, and nothing in
    this server has ever read one -- there is no equipped-weapon column on
    the character row, no ``EQUIP_VALUE`` reader, and the login attr block
    carries no such field that anybody has named.  ``COO-DECISION
    20260904_2141`` point 2 spells out what follows: ``auto`` is available
    only where the equip type has a provenance, and where it does not, the
    trial takes an explicit ``<id>`` and NOTHING is guessed.

    This function exists so that the day a provenance does land, ``auto``
    turns on here, in one place, with one test -- instead of somebody
    reaching for "the character is probably a fighter, so 280".
    """
    return None


def _parse_selector(raw):
    """``(state, value)`` for one raw environment string.  Never raises."""
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
        if not text.isdigit() or not text.isascii():
            return (TRIAL_MALFORMED, None)
        value = int(text)
    if not 0 <= value <= U32_MAX:
        return (TRIAL_MALFORMED, None)
    return (TRIAL_ARMED, value)


def trial_opening(environ=None):
    """Which ONE selector the trial gate is armed for, if any.

    Returns ``(TRIAL_UNSET, None)``, ``(TRIAL_MALFORMED, None)``,
    ``(TRIAL_NO_PROVENANCE, None)`` or ``(TRIAL_ARMED, <u32>)``.  Never
    raises: a hostile or exotic mapping is a malformed environment, not an
    exception on the dispatch path -- ``action_ack`` is called from inside
    ``state.dispatch()`` and the frozen ``game_listener`` around it has zero
    except handlers (interlock X07), so a gate that raises kills the thread.
    That is the same posture, and the same reason, as
    ``gm/speed_wire.trial_opening``.
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(POSE_TRIAL_ENV)
    except Exception:  # noqa: BLE001 - see the docstring
        return (TRIAL_MALFORMED, None)
    if raw is None:
        return (TRIAL_UNSET, None)
    return _parse_selector(raw)


def console_token(sent, echoed, state):
    """The one line an attended run greps, for one composed reply.

    ``POSE_TRIAL sent=+0x30=<id> control|mutant`` is the shape
    ``ATTACK-POSE-ONE-FIELD-AB-001`` asks for.  ``control`` is not a
    constant compared against 60029: it means "we sent back exactly what the
    request carried", which is the property the A/B actually rests on, and
    it stays true if a future capture ever shows a request whose ``+0x30``
    is not ``0xEA7D``.  A refused arming keeps the same ``sent=`` field --
    so one grep finds every reply -- behind a different first word, because
    "the door was closed" and "the door was open at the echo value" are two
    different runs and must not read alike.
    """
    arm = "control" if sent == echoed else "mutant"
    if state == TRIAL_ARMED:
        return "POSE_TRIAL sent=+0x30=%d %s" % (sent, arm)
    return "POSE_TRIAL_REFUSED %s sent=+0x30=%d %s" % (state, sent, arm)


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
