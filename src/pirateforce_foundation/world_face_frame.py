"""Rebuild the ChooseNPC face frame so it names the same person the census did.

WHY THIS MODULE EXISTS.  On 2026-08-29T00:17+07:00 the owner clicked Columbus
at Port Royal on a flagless boot and the conversation window that opened was
titled ``Sebastian``, with Sebastian's voice and Sebastian's Prison Exile
Island line, while the target panel beside it still read ``Columbus``
(attended GT-102, which names the exact panel, and LANE-A's CORE-REQUEST of
01:46+07:00 which traced it).

Two frames, one actor, two people:

* The LOGIN CENSUS is right.  ``world_population._entry`` resolves each
  placement through ``world_port_royal_identity`` and ships MOBS 156,
  Columbus's avatar and Columbus's name.
* The CLICK FRAME is wrong.  ``make_v98_conversation_face_state``
  (``current/pf_login_game_server_v141.py``) ships the frozen row's SECOND
  field into ``make_npc_attr``'s first parameter.  That field is a Mob-Set
  number, 1..113; that parameter is, by ``make_npc_attr``'s own docstring,
  "the MOBS/template u16 at +0x78".  A Mob-Set number is not a MOBS.n_ID.
  For placement 1 the two numbering schemes collide on the literal 2, so the
  defect never appeared as a wrong number - it appeared as a wrong PERSON.

WHY THE FIX IS HERE AND NOT IN THE BUILDER THAT HAS THE DEFECT.  LANE-A's
CORE-REQUEST asked for three lines inside the frozen file.  It cannot be
done there.  ``current/pf_login_game_server_v141.py`` is not immutable by
convention, it is immutable by ENFORCEMENT, in six independent places that
were all measured going red on the attempt (round c5nwjc):

    tools/verify_hypothesis_ledger.py   IMMUTABLE_V141_SHA256 constant
    docs/HYPOTHESIS_LEDGER.json         entries[2].source_refs[0].sha256
    tests/test_foundation.py            test_v141_characterization_hash
    tests/test_item_move_capture.py     test_v141_is_still_the_exact_immutable_source
    tests/test_second_password_bypass.py  test_v141_is_immutable
    tests/test_server_shutdown.py       ..._and_v141_is_preserved

and a seventh rule, ``tests/test_runtime_console.py``, forbids that module
printing to the console outside its own self-test.  Editing the file is
therefore a change to something proven, which policy 14.3 reserves for the
owner - not a chief-level judgement call.  The letter
``notes_to_chief/20260829_0303_CHIEF-ASK-COO-v141-immutable-by-enforcement-not-convention.md`` puts that question where it
belongs; this module fixes the wire WITHOUT touching the frozen file, so the
player stops seeing the wrong person while that question is answered.

HOW IT WORKS.  ``runtime`` calls ``rebuild_face_actions`` on the action list
that comes back from the inherited ChooseNPC handler.  Any face-frame action
in it is rebuilt from the same inputs the frozen builder used, through the
same frozen serializers - ``make_npc_attr``, ``make_remote_movement_attr``,
``make_remote_actor_entry``, ``make_runtime_remote_actors`` and
``_heading_to_player`` are all READ from the legacy module, never
reimplemented.  No wire shape is duplicated here; only the identity the
shape is filled with changes.  Every other action passes through untouched.

TWO UNRESOLVABLE CASES, HANDLED THE WAY THE CENSUS ALREADY HANDLES THEM:

* A non-selected placement with no shippable identity is OMITTED, because
  ``world_population.census_order`` omits exactly the same placements at
  login (seven of the 115, P0 among them).  Shipping it here would re-add an
  actor the client was never told about, which is the opposite of making the
  two frames agree.
* If the SELECTED placement has no shippable identity there is no honest
  frame to send, so the action is DROPPED and the event log says so.  A
  click that opens nothing is a bug report; a click that opens the wrong
  person's dialogue is a lie the player cannot detect.

There is deliberately NO FALLBACK to the Mob-Set number.  That fallback is
the defect.
"""

from __future__ import annotations

from typing import Any

from . import world_port_royal_identity

# Both labels the frozen ChooseNPC branch emits for this frame.  Each ends in
# ``P<placement index>``, which is how the rebuild knows which actor the
# frame was rotated toward without re-parsing the client's request.
FACE_LABEL_PREFIXES = (
    "V98_NPC_FACE_PLAYER_POSITION_HEADING_P",
    "V112_TEST_HARNESS_FACE_PLAYER_P",
)


def _selected_index(label: str) -> int | None:
    """The placement index a face-frame label names, or None if not one."""
    for prefix in FACE_LABEL_PREFIXES:
        if label.startswith(prefix):
            suffix = label[len(prefix):]
            if suffix.isdigit():
                return int(suffix)
            return None
    return None


def is_face_label(label: str) -> bool:
    """Whether this action label is one of the two face-frame labels."""
    return _selected_index(label) is not None


def build_face_state(
    legacy: Any,
    population_indices: tuple[int, ...],
    selected_idx: int,
    player_x: float,
    player_y: float,
) -> tuple[bytes, bytes]:
    """The V98 face frame, with every actor under its resolved identity.

    Same inputs, same frozen serializers and same frame shape as
    ``legacy.make_v98_conversation_face_state``; the only difference is that
    the NPCAttr carries ``identity.mobs_n_id`` / ``identity.outfit`` /
    ``basic_name=identity.name`` instead of the frozen row's Mob-Set number,
    its Mob-Set-numbered avatar and no name at all.

    Raises ``ValueError`` if the selected placement is not in the population
    (the frozen builder's own precondition, kept) or has no shippable
    identity (the new one).
    """
    by_idx = {row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    if selected_idx not in population_indices:
        raise ValueError("selected identity is not in current population")

    entries = []
    for idx in population_indices:
        _, template_id, px, py, pz, _preset, _name = by_idx[idx]
        identity = world_port_royal_identity.resolve(template_id)
        if identity is None:
            if idx == selected_idx:
                raise ValueError(
                    f"selected placement {idx} (mob-set {template_id}) has "
                    "no shippable identity: "
                    f"{world_port_royal_identity.unresolved_reason(template_id)}"
                )
            # Omitted, exactly as census_order omits it.  Not silent: the
            # caller records one event per omission.
            continue
        aid = 0x2000 + idx + 1
        attrs = [(
            legacy.NPC_ATTR,
            legacy.make_npc_attr(
                identity.mobs_n_id, aid, 1, 0, identity.outfit,
                basic_name=identity.name,
            ),
        )]
        if idx == selected_idx:
            heading = legacy._heading_to_player(px, py, player_x, player_y)
            attrs.append((
                legacy.MOVEMENT_ATTR,
                legacy.make_remote_movement_attr(
                    aid, px, py, pz, heading, mask=0x03
                ),
            ))
        entries.append(legacy.make_remote_actor_entry(4, aid, attrs))
    return legacy.make_runtime_remote_actors(entries)


def omitted_indices(
    legacy: Any, population_indices: tuple[int, ...]
) -> tuple[int, ...]:
    """Which requested placements have no shippable identity.

    On the production path this is empty, because the indices come from a
    census that already dropped them.  A non-empty result means some other
    path armed the population, which is worth a line in the event log.
    """
    by_idx = {row[0]: row for row in legacy.PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS}
    return tuple(
        idx for idx in population_indices
        if idx in by_idx
        and world_port_royal_identity.resolve(by_idx[idx][1]) is None
    )


def rebuild_face_actions(
    legacy: Any,
    actions: list,
    population_indices: tuple[int, ...] | None,
    last_target_pos: tuple[float, float, float, float] | None,
    events: list,
) -> list:
    """Return ``actions`` with every face frame rebuilt under real identities.

    ADDITIVE AND TOTAL: an action list with no face frame in it comes back
    the same object's contents, in the same order, with nothing added and
    nothing dropped.  This is the only reason it is safe to call on every
    dispatch rather than only on ChooseNPC.
    """
    if not actions or population_indices is None or last_target_pos is None:
        return actions

    x, y = last_target_pos[0], last_target_pos[1]
    rebuilt = []
    for action in actions:
        label = action[0]
        selected_idx = _selected_index(label)
        if selected_idx is None:
            rebuilt.append(action)
            continue
        for omitted in omitted_indices(legacy, population_indices):
            if omitted != selected_idx:
                events.append(f"face_frame_omitted_unresolvable_p{omitted}")
        try:
            pc, frame = build_face_state(
                legacy, population_indices, selected_idx, x, y
            )
        except ValueError as error:
            # No honest frame exists for this click.  Drop it rather than
            # let the frozen builder's version through: passing it on is
            # what put Sebastian's window on the owner's screen.
            events.append(
                f"face_frame_dropped_unresolvable_p{selected_idx}_"
                f"{type(error).__name__}"
            )
            continue
        events.append(f"face_frame_identity_resolved_p{selected_idx}")
        rebuilt.append((label, pc, frame) + tuple(action[3:]))
    return rebuilt
