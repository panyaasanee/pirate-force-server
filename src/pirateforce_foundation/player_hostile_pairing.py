"""LANE-B / PLAYER-HOSTILE-PAIRING-001: the player's own half of the pairing,
generalized off the one pinned smoke identity, for a chief round to wire.

WHAT THIS MODULE IS FOR.  ``field_mobs.py``'s own header says it plainly:
"This module builds the monster half only; the player half lives on the
StartGame path, which is the chief's file."  That is still true of
``runtime.py`` itself -- this lane does not touch it, does not touch
``app.py``, and does not touch the frozen V141 source.  But the same header
also proves the pairing is provably incomplete without that other half, and
2026-08-27's ``GT-084`` cycle (see ``notes_to_chief/20260827_0520_*`` and
``notes_to_chief/20260827_0920_*``) measured it directly: on the flagless
boot the player is never sent with ``basic_faction`` set at all, so the
client renders a proven-neutral pair -- (0, 6) -- even on a boot whose
census composes all thirteen field-mob bodies hostile-shaped and byte-exact
(``mob_death.full_roster_override``, wired since commit ``3036b03``,
console-checkable since commit ``dd5c785``).  This module is this lane's
half of closing that gap: the SAME pure logic pattern this project already
used for ``mob_death.hostile_census_frames`` (CORE-REQUEST-008) -- write the
general-purpose composer here, in a module the chief's file can import and
call unconditionally, rather than hand the chief a paragraph to reimplement.

WHY THIS IS SAFE TO GENERALIZE, NOT A GUESS.  ``runtime.py``'s existing
``_npc_hostile_start_game_response`` (HYP-PF-027, the opt-in probe that
``GT-032`` PASSED against on 2026-08-21) already proves the WIRE HALF of
this exact composition end to end: it calls
``projector.start_game(selected, basic_faction=1, backpack=...)`` and gets
back the production StartGame response plus exactly
:data:`field_mobs.FACTION_SPLICE_BYTES` extra bytes.  The only thing that
function adds on top of the frozen serializer is an extra identity pin
(``NPC_HOSTILE_PLAYER_IDENTITY_LO/HI``) restricting it to the one smoke
character the HYP-PF-027 pins were computed for.  That pin is a probe-scope
choice, not a serializer requirement: the actual frozen encoder underneath,
``player_wire.make_actor_attr_with_basic_faction``, does not look at
identity at all -- it only rejects a ``basic_faction`` other than 1, a
``scene_seq`` other than 0, or a ``scene_id`` outside ``(1, 2)``.  And
``app.py``'s own default spawn is ``Position(1, 0, ...)``
(``legacy.V135_PLAYER_X/Y/Z``), read here, not edited -- so every character
created today starts inside that exact accepted range, and nothing in this
project's currently-wired travel path (``BUILD-002``/scene 278 is COO-held
off per ``20260827_0245_COO-DECISION-BUILD-002-scene278-stays-off-*``)
moves ``scene_id``/``scene_seq`` away from it (``runtime.py``'s move
checkpoint keeps both fields from ``selected.position`` unchanged, only
x/y/z/heading move).  So the guard this module relies on is not a loosened
rule -- it is the SAME frozen rule, called for characters the rule already
accepts, not for a pin someone added on top of it.

FAIL CLOSED FOR EVERY CHARACTER THE GUARD DOES NOT ACCEPT.  The day scene
278 (or any other scene/seq) opens, a character standing there hits the
frozen serializer's own ``ValueError`` and this module returns the
UNTOUCHED production StartGame bytes with a named event -- exactly the same
fail-closed shape ``_npc_hostile_start_game_response`` already uses, and
exactly this project's own rule ("Missing data means a smaller world, never
a fabricated one").  Nothing here invents a wider guard than the one the
serializer already enforces; this module only removes the EXTRA identity
pin that was never part of the serializer's own contract.

WHAT THIS MODULE DOES NOT DO.
  * It does not dispatch anything and it does not call ``runtime.py``.  No
    module in ``src/`` imports it yet; wiring it into the flagless StartGame
    reply at ``runtime.py`` (the block around the existing opt-in
    scenario-flag guard just above the entry-half probe hook, roughly
    lines 4472-4480) is CORE-REQUEST-009 -- one line for the chief, listed
    in this round's handback, not a call this lane makes itself.
  * It does not claim a client has ever rendered this.  ``GT-032`` proved
    the flagged pair (1, 6) renders hostile; this module's byte shape is
    identical to what ``GT-032`` sent for the player half, not a new,
    unproven shape -- but the FLAGLESS boot combination (this player half
    plus the already-wired ``field_mobs`` monster half) has never been shown
    to a client.  That is the open half of ``GT-084``/``RIDER-084-A``.
  * It does not touch ``field_mobs.py``, the flag-gated entry-half probe
    module the previous paragraph describes, or ``player_wire.py``.  Named
    once, deliberately, in this sentence and nowhere else in this file, so
    this module does not join that probe's own two-file containment
    allowlist (``app.py``/``runtime.py`` only) by accident.  It imports the
    constant it needs
    (``field_mobs.PLAYER_PAIR_FACTION``, ``field_mobs.FACTION_SPLICE_BYTES``)
    rather than redefining it, so the player and monster factions cannot
    drift out of sync with each other in two different modules.

production_allowed is True: this is shippable behaviour with no scenario
flag and no dispatch kwarg, same convention ``field_mobs.py`` uses.
"""
from __future__ import annotations

from typing import Any

from . import field_mobs

# Re-exported for callers that want the single source of truth without a
# second import; identical value to field_mobs.PLAYER_PAIR_FACTION.
PLAYER_PAIR_FACTION = field_mobs.PLAYER_PAIR_FACTION

REFUSAL_COMPOSE = "player_hostile_pairing_compose_refused"
REFUSAL_LENGTH_DRIFT = "player_hostile_pairing_length_drift"
SENT_EVENT = "player_hostile_pairing_start_game_sent"


def compose_start_game_with_player_pairing(
    projector: Any, selected: Any, backpack: Any, pc: bytes, frame: bytes,
) -> tuple[bytes, bytes, bool, str]:
    """Recompose a StartGame response with the player's faction-1 half.

    ``pc``/``frame`` are the untouched production StartGame bytes the
    caller already built (the inherited V141 dispatch's own composition);
    they are what this function returns unchanged on any refusal.

    ``projector`` is the caller's ``LegacyProjector`` (``self.foundation.
    projector`` in ``runtime.py``); ``selected`` is the caller's currently
    selected ``Character``; ``backpack`` is the caller's currently loaded
    ``BackpackState`` (``self.foundation.backpack``) -- the same three
    values ``_npc_hostile_start_game_response`` already reads today, just
    without that function's extra identity pin.

    Returns ``(pc_out, frame_out, sent, event)``.  ``sent`` is True only
    when the frozen serializer accepted the call AND the resulting bytes
    are exactly ``pc``/``frame`` plus :data:`field_mobs.FACTION_SPLICE_
    BYTES` -- the same length-drift guard the HYP-PF-027 probe uses, so a
    silent serializer change cannot ship a corrupted StartGame reply
    disguised as an untouched one.  ``event`` is always a short, stable,
    ASCII, cp874-safe name a caller can log or count without inventing its
    own wording; it is one of :data:`REFUSAL_COMPOSE`,
    :data:`REFUSAL_LENGTH_DRIFT`, or :data:`SENT_EVENT`.
    """
    try:
        faction_pc, faction_frame = projector.start_game(
            selected, basic_faction=PLAYER_PAIR_FACTION, backpack=backpack,
        )
    except (ValueError, RuntimeError, TypeError, AttributeError) as exc:
        # AttributeError alongside the frozen serializer's own ValueError:
        # a caller passing an unselected (None) character must fail closed
        # here too, not crash the connection thread that read this reply.
        # pf-adversary self-review, this round: found by calling this
        # function with selected=None before adding this line.
        return pc, frame, False, f"{REFUSAL_COMPOSE}_{exc!r}"
    if len(faction_pc) != len(pc) + field_mobs.FACTION_SPLICE_BYTES:
        return pc, frame, False, REFUSAL_LENGTH_DRIFT
    return faction_pc, faction_frame, True, SENT_EVENT


def describe_pairing_attempt(sent: bool, event: str) -> str:
    """One console-checkable line, same shape as ``mob_death.describe_
    roster_override_coverage`` -- so an attended round (GT-084/RIDER-084-A)
    can grep a stable token instead of re-discovering one, the exact
    mistake ``GT-084``'s first pass made against ``FIELD_MOB``/``HOSTILE``.
    """
    return f"PLAYER_HOSTILE_PAIRING_ATTEMPT sent={sent} event={event}"
