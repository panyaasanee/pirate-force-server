"""LANE-A: a kill in scene 2 must not silence the island's clicks.

THE TEST THAT DID NOT EXIST, AND ITS ABSENCE IS THE WHOLE POINT.  On
2026-09-02 this lane shipped a ChooseNPC responder that read a combat
ledger and, on a body the ledger said was dead, refused THE WHOLE CLICK.
Four related test files were green (109 passed) and one of them asserted
that refusal AS DESIRED BEHAVIOUR, because no test in this repository ever
killed a monster in scene 2 and then clicked anybody.  chief did, on the
real dispatcher, and measured that one kill silences every click in the
scene until the player reconnects - ``_sync_combat_scene_state`` pulls the
death back out of ``mob_death_register`` on every re-entry, so leaving the
scene does not clear it (letter ``20260902_1918``).

``COO-DECISION 20260902_1945``: the dead guard judges the CLICKED body
only.  This file drives that with a REAL kill through the REAL dispatcher
rather than a hand-built ledger, and it is deliberately in a file of its
own so the property survives a rewrite of either responder's own suite.

WHY IT CALLS ``respond`` DIRECTLY AFTER THE KILL, AND WHY THAT IS STILL
END TO END.  ~~The ChooseNPC call site in ``runtime.py`` does NOT pass
``mob_combat_ledger`` today - chief withheld that line until this guard
narrowed, which is the whole reason this round exists.~~ CORRECTED ROUND
``qa86im``: chief landed ``mob_combat_ledger=`` at ``runtime.py:8800`` in
``server#619`` (R313, ``COO-DECISION 20260903_0251``), so that half is
production now.  ~~The sentence still holds for the OTHER keyword: the
call site passes no ``mob_death_register=`` yet, so a pure frame round
trip would exercise the ``register=None`` path and prove nothing about
the corpse answer this round added.~~ - STRUCK, round ``8o44lm``,
MEASURED on ``origin/main``: ``server#635`` landed
``mob_death_register=self.mob_death_register`` and an AST read of the
call site at ``runtime.py:8800`` now returns NINE keywords with no
``None`` among them.  Nothing here is hypothetical any more.  The ledger
and the register this file hands the responder are the SESSION's own,
after a real ``ACTION_VITAL`` killed a real monster in a real scene-2
arrival; ~~only the arguments chief has yet to add are supplied by
hand~~ - what is supplied by hand now is the ARGUMENT PASSING itself,
which is what lets one test drive the ``register=None`` path (still the
answer on a deploy older than ``#635``) beside the register one in the
same file.

WHAT ROUND ``qa86im`` ADDED HERE, AND WHY IT IS THE SAME FILE.  ``COO-
DECISION 20260903_0252``: "a corpse must answer with a body instead of
silence".  The refusal this file pinned in round ``4uztfj`` is still the
right answer when nothing can compose a corpse, so both halves are pinned
side by side -- with a register, the click on the dead body is ANSWERED
and carries the corpse; without one, it is refused by name, exactly as
before.

THE CONSOLE IS NOT THE FRAME (round ``8o44lm``, chief's letter
``20260903_0818`` item 3, and ``COO-DECISION 20260903_0846``'s house
rule that a claim about what a frame carries must be unpacked from the
COMPOSED frame).  Two cards in this file used to answer "is the whole
island still in this answer?" by looking for ``visible=97`` in
``console_lines[0]``.  That token is built from ``len(entries)`` BEFORE
``compose_answer`` is called, so it says what the responder INTENDED to
send.  Measured this round: compose the corpse answer out of the clicked
corpse alone and the frame goes from 12,543 bytes carrying 97 of 97
placements to 172 bytes carrying 1 -- the replace-by-omission shape
``RE-092`` names, which DELETES 96 actors off the player's screen -- and
this file stayed green at 14 passed, ``visible=97`` and all.  Both cards
now read the bytes that leave, through
``_assert_the_island_left_in_this_answer``; the console token is still
asserted beside them, because a console line that disagrees with its own
frame is a defect in its own right, but it no longer decides anything.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs                      # noqa: E402
from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_combat_membership           # noqa: E402
from pirateforce_foundation import mob_death                       # noqa: E402
from pirateforce_foundation import mob_loot                        # noqa: E402
from pirateforce_foundation import population                      # noqa: E402
from pirateforce_foundation import scene2_prison_exile_tables as tables  # noqa: E402
from pirateforce_foundation import world_census_level              # noqa: E402
from pirateforce_foundation import (                               # noqa: E402
    world_population_bg0002 as census,
)
from pirateforce_foundation import world_scene_travel              # noqa: E402
from pirateforce_foundation.gm.chat_command_action import (        # noqa: E402
    WARP_ACTION_LABEL,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget     # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (         # noqa: E402
    current_character_id,
    record_warp_target,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene2 as responder_mod,
)
from pirateforce_foundation.legacy_bridge import (                 # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle    # noqa: E402
from pirateforce_foundation.model import Position                  # noqa: E402
from pirateforce_foundation.runtime import make_state_class        # noqa: E402
from pirateforce_foundation.store import SQLiteStore               # noqa: E402
from pirateforce_foundation.world_population_handoff import (      # noqa: E402
    wire_count_of,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PRISON_EXILE = 2
DESTINATION_FOLDER = "Bg0002"
# The player position every click in this file is made from; the
# responder turns the clicked actor toward it.
PLAYER_X = 1.0
PLAYER_Y = 2.0


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class AKillDoesNotSilenceTheIslandTests(unittest.TestCase):
    """The harness shape is ``tests/test_mob_combat_dispatch_bg0002_kill.py``'s
    (LANE-B's file), reproduced rather than imported: importing another
    lane's test class would make this property die quietly the day that
    file is reorganised, and this one is a production guarantee."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.roster = field_mobs.load_roster(DESTINATION_FOLDER)
        self.clock_ms = 0

    def _clock(self):
        return self.clock_ms / 1000.0

    def _dispatch(self, state, pc):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return state.dispatch(self.legacy.parse_outer(pc))

    def _state(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            monotonic_clock=self._clock,
        )
        state = state_type(token)
        self._dispatch(state, self.legacy._synthetic_client_login_pc(token))
        self._dispatch(state, self.legacy._V25_REAL_CREATE_PC)
        character = self.store.list_characters(state.foundation.account_id)[-1]
        self._dispatch(
            state, self.legacy._synthetic_start_game_pc(character.selector),
        )
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.mob_loot_rng = random.Random(1)
        return state

    def _warp(self, state, scene_id):
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        target = WarpTarget(scene_id, spawn[0], spawn[1], spawn[2])
        self.assertTrue(
            record_warp_target(state, target, current_character_id(state))
        )
        real = state._dispatch_with_lanes

        def _one_warp_action(parsed):
            state._dispatch_with_lanes = real
            return [(WARP_ACTION_LABEL, b"", b"", 0.0)]

        state._dispatch_with_lanes = _one_warp_action
        self._dispatch(
            state, self.legacy._synthetic_client_login_pc(state.token),
        )
        self.assertEqual(
            state.foundation.selected.position.scene_id, scene_id,
            "the warp did not move the session's scene",
        )
        self.clock_ms += 1000

    def _action_vital_pc(self, target_identity):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _kill(self, state, target_identity):
        state._sync_combat_scene_state()
        row = state.mob_combat_ledger.balance_of(target_identity)
        state.mob_combat_ledger = state.mob_combat_ledger.with_balance(
            mob_combat.MobBalance(target_identity, row.max_hp, 1)
        )
        state.mob_combat_announced_membership = (
            mob_combat_membership.build_membership(
                state.foundation.selected.position.scene_id,
                (target_identity,),
                state.mob_combat_announced_membership_generation,
            )
        )
        self._dispatch(state, self._action_vital_pc(target_identity))
        self.clock_ms += 1000

    def _killed_session(self):
        """A live session standing in scene 2 with one monster really dead."""
        state = self._state("tok_lane_a_click_after_kill")
        self._warp(state, PRISON_EXILE)
        target = self.roster[0].actor_identity
        self._kill(state, target)
        balance = state.mob_combat_ledger.balance_of(target)
        self.assertEqual(
            balance.current_hp, 0,
            "the harness did not actually kill the monster",
        )
        return state, target

    def _hostile_indices(self):
        return responder_mod._hostile_mobs_by_placement_index()

    def _civilian_index(self):
        hostile = self._hostile_indices()
        return next(
            index for index in sorted(
                p.placement_index for p in tables.load_known_placements())
            if index not in hostile
        )

    def _click(
        self, state, placement_index, with_register=False,
        with_loot_cell=False,
    ):
        placement = next(
            p for p in tables.load_known_placements()
            if p.placement_index == placement_index
        )
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(placement.actor_identity,),
                population_indices=None,
                last_target_pos=(PLAYER_X, PLAYER_Y, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                # THE SESSION'S OWN REGISTER, not a hand-built one: the
                # kill above went through the real dispatcher, so this is
                # the object ``runtime.py`` hands over.  ~~the object
                # ``runtime.py`` would hand over the day chief adds the
                # keyword~~ - STRUCK, round ``8o44lm``: that day was
                # ``server#635``, measured on ``origin/main``.  The
                # argument is still passed by hand HERE so that one file
                # can drive both the register path and the ``None`` path
                # (still the answer on a deploy older than ``#635``).
                mob_death_register=(
                    state.mob_death_register if with_register else None),
                # THE ROUTE PRODUCTION ACTUALLY TAKES (pf-adversary,
                # round ``8o44lm``, D2).  ``runtime.py:1328`` binds
                # ``self.mob_loot_cell = mob_loot.DropLedgerCell()``
                # unconditionally per session and the call site passes it,
                # so EVERY live click composes through
                # ``mob_combat.remote_actors_preserving_the_ground_under_
                # publication``.  With no cell, ``compose_answer`` takes
                # the ``ground_rows_for_scene(None, ...)`` branch.
                # ~~into v141's own composer -- a different function~~ -
                # STRUCK, pf-adversary D6 (second pass): v141's composer
                # is reached on BOTH routes, from inside
                # ``mob_loot.preserve_ground_in_runtime_res_remote_
                # actors_when_live``; what differs is the wrapper, the
                # lock and whether a ground record is appended.  A card
                # that says it reads "the bytes that leave" has to be
                # able to run the composer that makes them.
                # THE SESSION'S OWN CELL, for the same reason the
                # register above is the session's own (pf-adversary D3,
                # second pass): a fresh ``DropLedgerCell()`` has no scene,
                # so the composer refuses it (``cell_has_no_scene``) and
                # composes the bytes it would have composed with no cell
                # at all -- a card driven that way measures the refusal
                # branch while claiming to measure production's.
                mob_loot_cell=(
                    state.mob_loot_cell if with_loot_cell else None),
            )
        return response, err.getvalue()

    def _dead_index(self, target):
        return next(
            index for index, mob in self._hostile_indices().items()
            if mob.actor_identity == target
        )

    # ------------------------------------------------------------------
    # READING THE COMPOSED FRAME, WHICH IS WHERE ``RE-092`` LIVES.  See
    # the module docstring, section ``THE CONSOLE IS NOT THE FRAME``:
    # every ``visible=`` token this file used to assert is computed
    # BEFORE ``compose_answer`` is called, so it cannot see an actor the
    # composer dropped.  These helpers read the bytes that leave.
    # ------------------------------------------------------------------

    def _entry_prefix(self, actor_identity: int) -> bytes:
        """The 11 bytes an actor entry for this identity starts with.

        ~~Taken from ``legacy.make_remote_actor_entry``'s own serializer~~
        - STRUCK, pf-adversary D4 (first pass): the first version never
        called that serializer and retyped ``0x0B``/``0x32`` itself.  It
        asks the serializer now, with the actor type read from
        ``population.NPC_STYLE_ACTOR_TYPE`` -- the constant the arrival
        census composes with -- rather than from the responder this file
        judges.  ~~"a reshaped header cannot slip past"~~ - STRUCK,
        pf-adversary D6 (second pass): following the serializer means a
        reshape moves both sides together; what catches that is
        ``test_the_actor_type_these_cards_read_is_the_census_own``, which
        reads a fixed offset of the census's own entry.

        WHERE THIS WEAK FORM IS STILL USED, AND IT IS ONE ROW: the CLICKED
        actor, whose entry carries a second attr whose heading is computed
        from the player position the caller passed.  Everything else in
        the answer is checked as a whole entry below.
        """
        return self.legacy.make_remote_actor_entry(
            population.NPC_STYLE_ACTOR_TYPE, actor_identity, [],
        )[:11]

    def _civilian_entry(self, placement) -> bytes:
        """The WHOLE entry a townsperson's row composes to.

        ~~"through the census's own ``leveled_npc_attr``, so nothing here
        is a transcription of the responder's arithmetic"~~ - HALF STRUCK,
        pf-adversary D5 (second pass), and the correction matters: what is
        borrowed is the ENCODER, and the ARGUMENTS were retyped literals.
        Measured cost of that: move ``world_population_bg0002.
        SCENE2_SEQUENCE`` and the census ships civilians under one
        sequence while a click restates them under another -- the exact
        defect class scene 14's responder exists to stop -- with this file
        and its sibling green.  The scene id and sequence are now READ
        FROM THE CENSUS MODULE, so that mutant is red here.
        """
        body = world_census_level.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=census.SCENE2_N_ID,
            scene_sequence=census.SCENE2_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.level,
        )
        return self.legacy.make_remote_actor_entry(
            population.NPC_STYLE_ACTOR_TYPE, placement.actor_identity,
            [(self.legacy.NPC_ATTR, body)],
        )

    def _clicked_civilian_entry(self, placement) -> bytes:
        """The WHOLE entry the CLICKED townsperson composes to.

        The one row whose entry carries two attrs: the body, and the
        MovementAttr that turns it to face the player.  ~~checked by its
        11-byte header, because its second attr carries a heading derived
        from the caller's player position~~ - STRUCK, pf-adversary D2/D6
        (second pass): the heading is derivable here from the same
        ``last_target_pos`` this file passes, and while the row stayed
        weak, five NUL bytes appended after it -- a parser desync with an
        honest header -- survived this file and its sibling, as did a
        clicked civilian redrawn at ``level=1`` and a clicked civilian
        that never turns to face the player at all.

        So there is no weak row left: all 97 are whole entries.
        """
        body = world_census_level.leveled_npc_attr(
            self.legacy,
            template_n_id=placement.n_id,
            actor_identity=placement.actor_identity,
            scene_id=census.SCENE2_N_ID,
            scene_sequence=census.SCENE2_SEQUENCE,
            visual_preset=placement.visual_preset,
            current_hp=placement.max_hp,
            max_hp=placement.max_hp,
            basic_name=placement.display_name,
            level=placement.level,
        )
        heading = self.legacy._heading_to_player(
            placement.x, placement.y, PLAYER_X, PLAYER_Y)
        movement = self.legacy.make_remote_movement_attr(
            placement.actor_identity,
            placement.x, placement.y, placement.z, heading,
            mask=responder_mod._FACE_MOVEMENT_MASK,
        )
        return self.legacy.make_remote_actor_entry(
            population.NPC_STYLE_ACTOR_TYPE, placement.actor_identity,
            [(self.legacy.NPC_ATTR, body),
             (self.legacy.MOVEMENT_ATTR, movement)],
        )

    def _hostile_entry(self, mob, register) -> bytes:
        """The WHOLE entry a hostile row composes to in THIS session.

        pf-adversary D2 (second pass) is why this exists: the 12 hostiles
        are the only rows a kill can change, and they were the rows left
        on the 11-byte form.  Measured escapes while they were: five NUL
        bytes appended after a hostile entry (parser desync, header
        honest) survived this file AND its sibling; live hostiles
        composed with the CIVILIAN encoder -- the hostility splice
        reverted on the wire, the confirmed scene-14 defect this
        responder's docstring names as its reason to exist -- survived
        this file.

        ~~"re-deriving that here would be a second copy of the
        responder's arithmetic"~~ - STRUCK: it is not.  Both shapes come
        from the modules that OWN them (``mob_death.corpse_npc_attr``,
        ``field_mobs.hostile_npc_attr``), which is what three cards in
        this file already did before this round, and the register decides
        which one applies rather than a rule copied from the responder.

        The HP of a live hostile is its table ceiling because in this
        harness the only ledger row below one belongs to the body that
        was killed, and that body is a grave.  A card that wounds a
        second monster without killing it would need the ledger's own
        number here; there is none in this file today, and that is the
        bound of this helper rather than a claim about the responder.
        """
        if register is not None and register.is_dead(
            mob.actor_identity, mob.scene,
        ):
            body = mob_death.corpse_npc_attr(
                self.legacy, mob,
                death_timer=mob_death.DEAD_TIMER_SECONDS,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            )
        else:
            body = field_mobs.hostile_npc_attr(
                self.legacy, mob, current_hp=mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE,
            )
        return self.legacy.make_remote_actor_entry(
            population.NPC_STYLE_ACTOR_TYPE, mob.actor_identity,
            [(self.legacy.NPC_ATTR, body)],
        )

    def _placements_not_exactly_once_in(
        self, frame: bytes, clicked_index: int, register,
    ) -> tuple:
        """Placement indices this frame does not carry exactly once.

        ALL 97 rows are checked as WHOLE entries -- attr count included,
        so nothing can be appended to one and nothing truncated off it,
        and no row can carry another row's body.  Each shape comes from
        the module that owns it: the census encoder for townspeople,
        ``field_mobs``/``mob_death`` for the twelve hostiles, and the
        clicked row's second attr from ``legacy`` itself.

        Reading the ``frame`` (the snappy carrier) rather than the ``pc``
        is sound while ``frame_pc``'s literal is ONE chunk.  ~~``frame_pc``
        emits a literal-only single chunk~~ - CORRECTED, pf-adversary D5
        (first pass): ``snappy_raw_literal`` (``v141:560``) chunks at
        **65,536 bytes**.  Today this scene's pc is ~12.5 KB, so there is
        one chunk and every entry appears verbatim;
        ``test_this_scenes_frame_is_still_one_snappy_chunk`` says so by
        name when that stops being true.

        ``!= 1`` rather than ``== 0``: an actor sent twice has also
        stopped being the census's frame.
        """
        missing = []
        for index, wanted in self._expected_entries(
            clicked_index, register,
        ):
            if frame.count(wanted) != 1:
                missing.append(index)
        return tuple(sorted(missing))

    def _expected_entries(self, clicked_index: int, register) -> list:
        """``(placement index, whole entry)`` for all 97, in wire order.

        Placement-index order is the responder's own, pinned by
        ``tests/test_lane_a_choose_npc_scene2.py::
        test_the_entries_are_in_placement_index_order``.
        """
        hostiles = self._hostile_indices()
        out = []
        for placement in sorted(
            tables.load_known_placements(),
            key=lambda row: row.placement_index,
        ):
            index = placement.placement_index
            if index in hostiles:
                wanted = self._hostile_entry(hostiles[index], register)
            elif index == clicked_index:
                wanted = self._clicked_civilian_entry(placement)
            else:
                wanted = self._civilian_entry(placement)
            out.append((index, wanted))
        return out

    def _assert_the_island_left_in_this_answer(
        self, response, clicked_index: int, register=None, trailing: int = 0,
    ) -> None:
        """The statements a complete answer has to satisfy.

        The header count and the payload are not the same claim.  A
        composer that drops 96 entries AND writes 1 into the count header
        is internally consistent and still clears the island; a composer
        that keeps the header at 97 and truncates the last entry by five
        bytes desyncs the client's parser on the tail, which costs the
        WHOLE frame rather than 96 actors of it.  ~~The header count
        alone is ``ErrorData=28317``'s side of the problem~~ - STRUCK,
        pf-adversary D1 (first pass): that mutant keeps the header honest
        and is still 28317.

        Both read a buffer the client never receives unless the ``pc``
        really is the frame's own content -- ``v141:7755`` sends
        ``out_frame`` and nothing else.  That third statement is a DRIFT
        ALARM and not a live gate: pf-adversary reached no route on which
        it fires, and it is kept as the thing that would notice the day
        one appears.

        ``register`` is the one the answer was composed with, so a frame
        with TWELVE graves in it is judged as twelve corpses rather than
        as twelve live bodies.  Passing nothing means "no grave in this
        answer", which is only correct for a click composed without a
        register.
        """
        self.assertIsNotNone(
            response,
            "the click was declined, so there is no answer to read the "
            "island out of",
        )
        self.assertEqual(
            wire_count_of(response.pc), len(tables.load_known_placements()),
            "the collection header does not declare the whole island",
        )
        self.assertEqual(
            self._placements_not_exactly_once_in(
                response.frame, clicked_index, register), (),
            "the frame that goes on the wire does not carry every "
            "placement on the island exactly once, as its own row "
            "composes it",
        )
        # CONTIGUITY, AND IT IS THE STATEMENT THE PER-ROW CHECK CANNOT
        # MAKE (pf-adversary D2, second pass).  Appending five NUL bytes
        # after any entry leaves every entry's own bytes intact as a
        # substring and the header count honest, so a per-row ``assertIn``
        # sees nothing -- while the client's parser desyncs on the tail
        # and loses the WHOLE frame.  Measured: with the per-row check
        # alone, junk after a hostile entry and junk after the clicked
        # entry both left this file green at 17 passed.  The 97 entries
        # must therefore appear as ONE run of bytes, in the responder's
        # own order, with nothing between them.
        run = b"".join(
            entry for _index, entry in self._expected_entries(
                clicked_index, register))
        self.assertEqual(
            response.frame.count(run), 1,
            "the 97 entries are not one contiguous run in wire order: "
            "something is between them, or the order moved",
        )
        # WHERE THE RUN STARTS AND WHERE IT ENDS.  Contiguity alone still
        # lets bytes be appended AFTER the last entry -- measured: five
        # NUL bytes there left this file green, and the client's parser
        # desyncs on that tail exactly as it does on junk in the middle.
        # The run must begin where the collection header ends and finish
        # where the pc does, except for the ground record the preserving
        # composer appends, whose length the caller MEASURES (it does not
        # type it) and passes as ``trailing``.
        head = census.WIRE_HEADER_BYTES
        self.assertEqual(
            response.pc[head:head + len(run)], run,
            "the actor collection does not start where its own header "
            "ends",
        )
        self.assertEqual(
            len(response.pc), head + len(run) + trailing,
            "something rides after the last entry that this answer's "
            "own route does not account for",
        )
        self.assertEqual(
            response.frame, self.legacy.frame_pc(response.pc),
            "the frame is not this pc's own carrier, so neither check "
            "above says anything about what the client receives",
        )

    def test_the_actor_type_these_cards_read_is_the_census_own(self) -> None:
        """pf-adversary, round ``8o44lm``, D4: without this, the frame
        cards follow the module they judge.

        ``_entry_prefix`` and ``_civilian_entry`` both build their entry
        with ``responder_mod._NPC_STYLE_ACTOR_TYPE``.  Measured: set that
        constant to 5 and both island cards stay green while every actor
        in the answer ships under an actor type the arrival census never
        used.  So the constant is pinned HERE against a byte this lane
        did not write -- the census's own corpse-override entry, composed
        by ``mob_death`` for the same identity.
        """
        state, target = self._killed_session()
        override = mob_death.corpse_override(
            self.legacy, tuple(self.roster), state.mob_death_register)
        census_entry = override[target]
        self.assertEqual(
            census_entry[:2],
            self.legacy.u8tag(0x0B, responder_mod._NPC_STYLE_ACTOR_TYPE),
            "the responder's actor type is not the one the census ships, "
            "so every frame card in this file is reading the wrong byte",
        )

    def test_this_scenes_frame_is_still_one_snappy_chunk(self) -> None:
        """The named bound of the ``assertIn``-over-a-frame technique
        (pf-adversary D5), and the card that names the cause when this
        scene outgrows it.  ~~fails FIRST~~ - STRUCK, pf-adversary D6
        (second pass): unittest orders alphabetically, so ``test_this_*``
        reports AFTER every ``test_the_*``; the island cards go red first
        and this one says why.

        ``snappy_raw_literal`` (``v141:560``) emits a fresh literal tag
        every 65,536 bytes.  Below that bound the pc appears verbatim in
        the frame and every ``assertIn`` in this file means what it says;
        above it, an entry straddling a chunk boundary would turn a
        correct frame red.  ~~"frame_pc emits a literal-only single
        chunk"~~ as an unconditional claim is STRUCK wherever this file
        said it.
        """
        state, target = self._killed_session()
        response, _stderr = self._click(
            state, self._dead_index(target), with_register=True)
        self.assertLessEqual(
            len(response.pc), 65536,
            "this scene's answer now spans more than one snappy literal "
            "chunk: the frame-level cards in this file need a decoder, "
            "not an assertIn, before they can be trusted again",
        )

    def test_the_island_survives_the_route_production_actually_takes(
        self,
    ) -> None:
        """pf-adversary D2: the other two island cards never run the
        composer a live click runs.

        ``runtime.py:1328`` binds ``self.mob_loot_cell = mob_loot.
        DropLedgerCell()`` unconditionally and the call site passes it, so
        every real click composes through ``mob_combat.remote_actors_
        preserving_the_ground_under_publication``.  With no cell,
        ``compose_answer`` routes to v141's own composer instead -- a
        different function, and the one the other cards were measuring.
        Same three statements, on the route that ships.
        """
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        rows = mob_loot.ground_rows_live_here(
            state.mob_loot_cell, DESTINATION_FOLDER)
        self.assertGreaterEqual(
            rows, 1,
            "this session's kill left nothing standing on the floor of "
            "Bg0002, so the armed branch of the composer is not the one "
            "this card would be measuring",
        )
        plain, _ = self._click(state, dead_index, with_register=True)
        response, _stderr = self._click(
            state, dead_index, with_register=True, with_loot_cell=True)
        self.assertNotEqual(
            response.pc, plain.pc,
            "the cell changed no byte, so the preserving composer was "
            "not reached and this card is measuring the route it was "
            "written to replace",
        )
        # The ground record's length is MEASURED against the same
        # answer composed without a cell, never typed here: this card
        # says the island survives the armed route, and says nothing
        # about how many bytes that route appends.
        self._assert_the_island_left_in_this_answer(
            response, dead_index, state.mob_death_register,
            trailing=len(response.pc) - len(plain.pc))

    def test_a_civilian_still_answers_after_a_real_kill(self) -> None:
        state, _target = self._killed_session()
        response, stderr = self._click(state, self._civilian_index())
        self.assertIsNotNone(
            response,
            "a kill in this scene silenced a click on a civilian - the "
            "state chief measured as indistinguishable from a dead server",
        )
        self.assertIn("dead_at_ceiling=1", response.console_lines[0])
        self.assertIn("dead_as_corpse=0", response.console_lines[0])
        self.assertIn(
            "_DEAD_BODY_AT_CEILING count=1 placements=", stderr)
        self.assertIn("identities=0x", stderr)

    def test_the_whole_island_is_still_in_that_answer(self) -> None:
        """``RE-092``: an omitted row is a DELETED actor.

        ~~This card asserted ``visible=`` in ``console_lines[0]``~~ -
        STRUCK, round ``8o44lm``: that token is built from ``len(entries)``
        BEFORE ``compose_answer`` runs, so it is true whatever the frame
        ends up holding.  The count is still asserted, because a console
        line that disagrees with the frame is its own defect, but the
        frame is what decides this card now.
        """
        state, _target = self._killed_session()
        civilian = self._civilian_index()
        response, _stderr = self._click(state, civilian)
        self._assert_the_island_left_in_this_answer(response, civilian)
        self.assertIn(
            f"visible={len(tables.load_known_placements())}",
            response.console_lines[0],
        )

    def test_clicking_the_dead_body_is_refused_by_its_own_placement(
        self,
    ) -> None:
        """STILL THE ANSWER WITHOUT A REGISTER, and that is the point of
        keeping this test beside the corpse ones below.  ~~every boot
        until chief adds the second keyword takes exactly this path~~ -
        STRUCK, round ``8o44lm`` (pf-adversary D3): no boot takes it since
        ``server#635``.  What it covers now is a deploy older than that
        commit, and the fail-closed contract itself -- a responder handed
        no register must refuse by name rather than invent a body."""
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        response, stderr = self._click(state, dead_index)
        self.assertIsNone(response)
        self.assertIn(
            "_IDENTITY_REFUSED reason=clicked_body_is_dead_needs_a_mob_"
            f"death_body placement={dead_index} identity=0x", stderr)

    def test_a_second_click_on_a_civilian_still_answers(self) -> None:
        """The failure chief measured was STICKY: it survived leaving and
        re-entering the scene.  One answer is not enough evidence that it
        is gone; the same session clicking twice is."""
        state, _target = self._killed_session()
        first, _ = self._click(state, self._civilian_index())
        second, _ = self._click(state, self._civilian_index())
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.frame, second.frame)

    # ------------------------------------------------------------------
    # ROUND ``qa86im``: the corpse answers instead of the silence
    # (``COO-DECISION 20260903_0252``).  Same session, same real kill; the
    # only difference is that the register the session already holds is
    # handed over the way chief's next line will hand it.
    # ------------------------------------------------------------------

    def test_the_session_register_really_holds_the_kill(self) -> None:
        """The premise of every test below it, measured not assumed."""
        state, target = self._killed_session()
        mob = self._hostile_indices()[self._dead_index(target)]
        self.assertEqual(mob.scene, DESTINATION_FOLDER)
        self.assertTrue(
            state.mob_death_register.is_dead(target, mob.scene),
            "the real dispatcher did not write this kill to the register",
        )

    def test_clicking_the_dead_body_answers_with_a_corpse(self) -> None:
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        response, stderr = self._click(state, dead_index, with_register=True)
        self.assertIsNotNone(
            response,
            "a click on a corpse is still answered with silence - the "
            "state COO-DECISION 20260903_0252 sent this round to close",
        )
        self.assertEqual(
            response.label,
            f"LANE_A_CHOOSE_NPC_SCENE2_CORPSE_P{dead_index}",
            "a corpse cannot turn to face the player, so the label must "
            "not claim a facing",
        )
        self.assertIn("dead_as_corpse=1", response.console_lines[0])
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn("_CLICKED_BODY_IS_A_CORPSE", stderr)
        self.assertNotIn("_IDENTITY_REFUSED", stderr)

    def test_that_frame_carries_the_composers_corpse_and_not_a_ceiling(
        self,
    ) -> None:
        state, target = self._killed_session()
        mob = self._hostile_indices()[self._dead_index(target)]
        response, _stderr = self._click(
            state, self._civilian_index(), with_register=True)
        self.assertIn(
            mob_death.corpse_npc_attr(
                self.legacy, mob,
                death_timer=mob_death.DEAD_TIMER_SECONDS,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE),
            response.frame,
            "the body in the frame is not mob_death's own corpse",
        )
        self.assertNotIn(
            field_mobs.hostile_npc_attr(
                self.legacy, mob, current_hp=mob.max_hp,
                scene_id=field_mobs.SCENE_ID,
                scene_sequence=field_mobs.SCENE_SEQUENCE),
            response.frame,
            "the dead monster stood back up at its ceiling in this frame",
        )
        self.assertIn("dead_at_ceiling=0", response.console_lines[0])
        self.assertIn("dead_as_corpse=1", response.console_lines[0])

    def test_that_corpse_is_the_census_overrides_own_entry(self) -> None:
        """THE STRONGEST STATEMENT THIS ROUND CAN MAKE, and it is an
        equality rather than an argument: a click does not invent a body
        for a dead monster, it sends the SAME entry ``mob_death.
        corpse_override`` hands the arrival census for that identity --
        the bytes this client has already accepted once for this scene."""
        state, target = self._killed_session()
        override = mob_death.corpse_override(
            self.legacy, tuple(self.roster), state.mob_death_register)
        self.assertIn(
            target, override,
            "the census override does not even hold this grave",
        )
        response, _stderr = self._click(
            state, self._civilian_index(), with_register=True)
        self.assertIn(
            override[target], response.frame,
            "the corpse in the click's frame is not the census's corpse",
        )

    def test_the_whole_island_is_still_in_the_corpse_answer(self) -> None:
        """``RE-092``: an omitted row is a DELETED actor.  A corpse answer
        that shipped 96 of 97 would clear somebody off the screen.

        ~~The card that said this asserted ``visible=`` on the console~~ -
        STRUCK, round ``8o44lm``: this is the hole chief reported in
        letter ``20260903_0818`` item 3, re-measured here rather than
        quoted.  Composing the corpse answer out of the clicked corpse
        alone takes this frame from 12,543 bytes and 97 of 97 placements
        to 172 bytes and 1 of 97, with ``visible=97`` still on the console
        line and this whole file green at 14 passed.  (chief's number was
        164; the shape of his mutant is not the shape of mine, and neither
        number is the point.)  With this card reading the frame, the same
        mutant is red.
        """
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        response, _stderr = self._click(
            state, dead_index, with_register=True)
        self._assert_the_island_left_in_this_answer(
            response, dead_index, state.mob_death_register)
        self.assertIn(
            f"visible={len(tables.load_known_placements())}",
            response.console_lines[0],
        )

    def test_the_corpse_answer_sends_no_movement_for_the_clicked_body(
        self,
    ) -> None:
        """A MovementAttr on a fallen body snaps it back to its roster row
        -- the reason ``mob_death.death_actor_entry`` defaults
        ``with_movement=False``.

        ~~This card forbade ONE byte string: the movement attr with
        ``mask=0x03`` and the heading to the caller's player position.~~ -
        STRUCK, pf-adversary D4 (second pass), MEASURED: give the answered
        corpse a movement attr with ``mask=0x01`` and the same
        coordinates -- the body still snaps back, which is the defect this
        docstring names -- and six related files stayed green, 119 passed.
        Any other mask, heading or position escaped it too.  The card now
        asserts the clicked corpse's WHOLE entry, attr COUNT included, so
        no added attribute of any shape survives; the old byte string is
        kept as a second, narrower statement rather than deleted.
        """
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        mob = self._hostile_indices()[dead_index]
        placement = next(
            p for p in tables.load_known_placements()
            if p.placement_index == dead_index
        )
        response, _stderr = self._click(
            state, dead_index, with_register=True)
        self.assertIn(
            self._hostile_entry(mob, state.mob_death_register),
            response.frame,
            "the clicked corpse's entry is not exactly one NPCAttr "
            "carrying mob_death's own corpse body",
        )
        heading = self.legacy._heading_to_player(
            placement.x, placement.y, PLAYER_X, PLAYER_Y)
        self.assertNotIn(
            self.legacy.make_remote_movement_attr(
                placement.actor_identity,
                placement.x, placement.y, placement.z, heading, mask=0x03),
            response.frame,
        )

    def test_a_grave_dug_in_another_scene_cannot_bury_this_body(
        self,
    ) -> None:
        """The register is keyed by ``(scene, identity)`` and this is what
        that key BUYS: scene 2 and scene 14 really do share identities."""
        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        mob = self._hostile_indices()[dead_index]
        foreign = mob_death.DeathRegister((
            mob_death.DeathRecord(
                actor_identity=mob.actor_identity,
                killer_identity=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY,
                max_hp=mob.max_hp,
                scene="Bg0015",
            ),
        ), 1)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(mob.actor_identity,),
                population_indices=None,
                last_target_pos=(PLAYER_X, PLAYER_Y, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                mob_death_register=foreign,
            )
        self.assertIsNone(response)
        self.assertIn(
            "clicked_body_is_dead_needs_a_mob_death_body", err.getvalue())

    def test_a_register_that_is_not_a_register_composes_nothing(
        self,
    ) -> None:
        """Fail CLOSED on the type: an object that merely answers
        ``is_dead`` is not a grave this lane may compose a body out of."""
        class _NotARegister:
            def is_dead(self, identity, scene=None):
                return True

        state, target = self._killed_session()
        dead_index = self._dead_index(target)
        mob = self._hostile_indices()[dead_index]
        with contextlib.redirect_stderr(io.StringIO()) as err:
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(mob.actor_identity,),
                population_indices=None,
                last_target_pos=(PLAYER_X, PLAYER_Y, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                mob_death_register=_NotARegister(),
            )
        self.assertIsNone(response)
        self.assertIn(
            "clicked_body_is_dead_needs_a_mob_death_body", err.getvalue())

    def test_a_frame_with_no_live_hostile_body_says_so_instead_of_lying(
        self,
    ) -> None:
        """FOUND BY THIS ROUND'S ADVERSARIAL PROBE, NOT BY A REVIEW.  With
        every hostile row buried, no body took its HP from the ledger AND
        none carried a ceiling -- and the old expression printed
        ``hp=ceiling`` about a frame that contained no ceiling at all."""
        state, _target = self._killed_session()
        hostile = self._hostile_indices()
        every_grave = mob_death.DeathRegister(tuple(sorted(
            (mob_death.DeathRecord(
                actor_identity=mob.actor_identity,
                killer_identity=mob_death.SANCTIONED_FIRST_TARGET_IDENTITY,
                max_hp=mob.max_hp, scene=mob.scene)
             for mob in hostile.values()),
            key=lambda row: (row.scene, row.actor_identity),
        )), len(hostile))
        with contextlib.redirect_stderr(io.StringIO()):
            response = responder_mod.respond(
                legacy=self.legacy,
                chosen_identities=(
                    next(
                        p.actor_identity
                        for p in tables.load_known_placements()
                        if p.placement_index == self._civilian_index()
                    ),
                ),
                population_indices=None,
                last_target_pos=(PLAYER_X, PLAYER_Y, 0.0, 0.0),
                scene_id=PRISON_EXILE,
                mob_combat_ledger=state.mob_combat_ledger,
                mob_death_register=every_grave,
            )
        line = response.console_lines[0]
        self.assertIn(f"dead_as_corpse={len(hostile)}", line)
        self.assertIn("dead_at_ceiling=0", line)
        self.assertIn("hp=no_live_body", line)
        self.assertNotIn("hp=ceiling", line)
        # pf-adversary D1 (second pass): this was the ONLY card in the
        # file that composed a frame with more than one grave in it, and
        # it read the console line and stopped -- inside the file whose
        # own docstring says the console is not the frame.  Measured
        # while it did: drop the entry for any grave that is not the
        # clicked one, but only when the register holds more than one,
        # and a player who kills TWO monsters and then clicks a
        # townsperson loses two actors off the screen (95 of 97) with
        # this file and its sibling green.  Twelve graves is the widest
        # frame this file can build, so it is where the island is owed
        # the most.
        self._assert_the_island_left_in_this_answer(
            response, self._civilian_index(), every_grave)

    def test_a_live_click_is_unchanged_when_a_register_is_passed(
        self,
    ) -> None:
        """The frame a player sees on every OTHER click must not move
        because this keyword arrived."""
        state, _target = self._killed_session()
        without, _ = self._click(state, self._civilian_index())
        with_register, _ = self._click(
            state, self._civilian_index(), with_register=True)
        self.assertNotEqual(
            without.frame, with_register.frame,
            "the corpse changed no byte - the register was not read",
        )
        self.assertEqual(without.label, with_register.label)
        self.assertIn("dead_at_ceiling=1", without.console_lines[0])
        self.assertIn("dead_at_ceiling=0", with_register.console_lines[0])


if __name__ == "__main__":
    unittest.main()
