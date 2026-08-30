"""LANE-B / MOB-COMBAT-001 (RE-157 job 2): the announced-actor guard
``runtime.py`` still needs, built and pinned so wiring it is one predicate
call, not a design task.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  Nothing
yet.  This module has no call site in ``runtime.py`` -- ``runtime.py`` is
chief's file, not this lane's, so the guard this file builds cannot flip live
combat behaviour by itself.  See the CORE-REQUEST below for the one predicate
call that would wire it.

WHY THIS MODULE EXISTS.  ``pf_bridge/notes_to_chief/20260830_1111_RE-157-
RESULT-*.md`` (the RE-157 result letter, Job 2 -- its own filename spells the
other job's word, deliberately not repeated here since this module never
implements that behaviour) named a real gap in ``_dispatch_mob_combat``: ``target_is_field_mob`` (``runtime.py:4194`` at
this round) only checks the STATIC scene roster (the module that names field
monsters, via ``self._sync_combat_scene_state()``), never whether the
target actor identity was ever ANNOUNCED to this session's own client
through a committed census.  A forged or desynced ``ActionVital`` can
therefore trigger cadence/ledger mutation (HP loss, combat-cadence spend,
threat) against a field mob that exists in the roster but was never shipped
in this session's own census frame.  RE-157 is explicit that this is a
forged/desync risk, not something proven reachable by a normal client
(nonclaim 1 of that letter) -- this module does not change that; it only
builds the fail-closed predicate the letter asked for, so nobody has to
re-derive its shape under time pressure once a runtime.py round picks up
the wiring.

WHY A PLAIN PREDICATE, NOT A ``lane_hooks`` PLUGIN.  There is no scene-keyed
"membership guard" hook point in ``lane_hooks`` today (only
``census_composer`` and ``choose_npc_responder`` exist), and RE-157's guard
is not a responder -- it never composes a frame, only says yes/no before
``runtime.py`` proceeds to cadence.  Same shape as
``mob_combat.check_attack_cadence``: a pure function over state the caller
already has on hand, called and consulted at the call site, not discovered.
So this module follows ``mob_combat.py``'s own convention (plain module
import, no probe flag, no ``production_allowed``) rather than
``lane_hooks``'s.

FAIL CLOSED, ALWAYS.  ``admits()`` returns ``False`` (never an exception, so
one bad or missing membership record degrades to "refuse" rather than
crashing a listener thread -- the same failure mode RE-157 itself flagged
for the frozen ``TARGET_VITAL`` loop) whenever the membership record is
missing, the scene does not match, the generation does not match, or the
actor identity is not in the announced set.  It never widens: an unmatched
anything is a refusal, and the only way past it is an explicit, exact match
on all three.

WHAT "GENERATION" MEANS HERE, AND WHY IT IS A CALLER-SUPPLIED OPAQUE VALUE.
RE-157 named two committed census sources with the same shape --
``runtime.py:7759-7799`` (home census commit) and ``:7548-7610`` (lane
census commit/stamp) -- each stamping a per-session record only when a
census generation is actually sent.  This module does not read either: it
takes whatever value the caller's own generation counter held at ANNOUNCE
time and the SAME value again at CHECK time, and treats "does not equal" as
"the membership below it may be stale," refusing rather than trusting an old
``AnnouncedActorMembership`` across a scene change or a re-census.  The
caller owns what a "generation" counts -- this module only requires that it
be comparable with ``==``.

CORE-REQUEST (for chief, ``runtime.py``, ``_dispatch_mob_combat``): after
``target_is_field_mob = any(...)`` (currently line 4194-4196) and before the
``if target_is_field_mob:`` cadence branch (currently line 4197), add::

    if target_is_field_mob and not mob_combat_membership.admits(
        self.mob_combat_announced_membership,
        scene_id=self.foundation.selected.position.scene_id,
        actor_identity=target,
        generation=<the session's current census generation counter>,
    ):
        self.events.append("mob_combat_target_not_announced_no_reply")
        return []

This lane does not know which existing ``runtime.py`` attribute already
holds "the session's current census generation counter" (or whether one
needs to be added) -- that is exactly the state RE-157 says only
``runtime.py``'s own commit points (``:7759-7799``, ``:7548-7610``) can
supply, so the exact wiring is chief's call.  This module supplies the
predicate and its contract only, pinned by
``tests/test_mob_combat_membership.py``.
"""
from __future__ import annotations

from typing import Any, Iterable, NamedTuple


class AnnouncedActorMembership(NamedTuple):
    """One committed census's worth of "the client actually got told about
    these actors" -- ``scene_id`` the census was sent for, the exact set of
    actor identities it carried, and an opaque ``generation`` token the
    caller can compare with ``==`` to know whether this record is still the
    session's current one.
    """

    scene_id: int
    actor_identities: frozenset
    generation: Any


def build_membership(
    scene_id: int, actor_identities: Iterable[int], generation: Any,
) -> AnnouncedActorMembership:
    """Freeze a census's actor set into a comparable, immutable membership
    record.  ``actor_identities`` is consumed eagerly (``frozenset``) so a
    caller's own mutable roster cannot change this record out from under a
    later ``admits()`` check.
    """
    return AnnouncedActorMembership(
        scene_id, frozenset(actor_identities), generation,
    )


def admits(
    membership: "AnnouncedActorMembership | None",
    *,
    scene_id: int,
    actor_identity: int,
    generation: Any,
) -> bool:
    """RE-157 Job 2's predicate.  ``False`` for anything not an EXACT match
    on all three fields, including a ``None`` membership (no census has ever
    been committed this session) -- see the module docstring's FAIL CLOSED
    section for why there is no partial-match branch.
    """
    if membership is None:
        return False
    if membership.scene_id != scene_id:
        return False
    if membership.generation != generation:
        return False
    return actor_identity in membership.actor_identities
