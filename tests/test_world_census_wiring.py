"""WORLD-CENSUS-001 -- the census on the REAL dispatcher, default boot.

``tests/test_world_population.py`` proves the builder offline: memberships,
nesting, byte counts, refusals.  It cannot say whether anything reaches a
client, because until this wiring landed nothing imported the module at all.
This file drives ``make_state_class`` headless -- no server process, no socket,
no client -- and proves the part that was missing:

  * a DEFAULT boot, constructed with no flag and no scenario of any kind, now
    queues the whole bg0001 census where it used to queue three actors, on the
    same trigger (first TargetPos after the runtime ack), with the same
    initial-plus-reapply schedule (0.0s then 3.0s);
  * the count is IN THE LABEL, because v141 prints one console line per queued
    action at send time and four staircase boots have to be distinguishable
    from that line alone;
  * ~~at rung 3 the wire is byte-identical to the frozen
    ``make_v112_monster_shop_population_state()`` collection, so the control
    rung is a control on the dispatch path and not only in the builder~~
    SUPERSEDED 2026-08-28 (RE-128): rung 3 carries the RESOLVED ``MOBS.n_ID``
    of each member and has dropped P0 (whose Mob-Set number resolves to a
    CLINE leader with no MOBS row), so it is neither byte-identical to the
    frozen collection nor the same three placements.  What the dispatch path
    is checked for now is that it queues the census module's own bytes and
    that every member on the wire carries its resolved identity;
  * CONTAINMENT: a boot that opted into any lane keeps the frozen three-actor
    population it was measured against.  This is the whole reason the wiring
    is keyed on "no lane is active" rather than on nothing at all;
  * the census is one-shot per session, and a compose refusal fails CLOSED to
    the shipped three-actor branch on the same frame and latches;
  * the anchor is THIS frame's TargetPos, not the previous one.

NOT proven here, and not provable without a person at a screen: whether the
client accepts a 108-actor RuntimeRes collection at all (115 before RE-128
dropped the seven placements with no shippable identity), and whether any of
those actors becomes a model on screen, or shows the name this lane now sends.
The highest count with a recorded result anywhere in this project is 20.  That
is GT-078, attended, not run.
"""
from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import world_density  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.ground_loot_hypothesis import (  # noqa: E402
    load_ground_loot_hypothesis_scenario,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _apply_mob_death_census_override, make_state_class,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
GROUND_LOOT_SCENARIO = (
    ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
)

# The wire, pinned as bytes, at ONE fixed anchor: (10.0, 20.0, 30.0).
#
# Why this exists.  Before it, the only stored byte check on this lane was
# rung 3, and every other assertion compared the dispatcher's output to
# build_world_population() -- the same producer, so a change inside the
# producer moved both sides together.  Measured: mutating one entry of
# HEADINGS, which mis-orients 28 of the 115 actors on the wire, left the whole
# suite green.  These digests cover 100% of the delivered bytes at every rung
# and that mutant turns them red.
#
# AMENDMENT 2026-08-26 (post-GT-078 OWNER-REJECTED name fix, this lane).
# ``_entry()`` in world_population.py stopped discarding SceneActorPlacement.
# source_name for every non-P30 member (see world_population.py:296), so
# every rung below grew by its members' own name-tag bytes and every digest
# below is RE-DERIVED -- run against the real code at PIN_ANCHOR, not
# hand-edited -- from the values GT-078's REJECTION made necessary.  The
# superseded digests, captured before that fix, are kept below rather than
# deleted, because they are still correct for what they described (a world
# with no NPC name line anywhere in it, which is the defect GT-078 rejected):
#
#   3:   pc=3B77557DB6FDBAD9C5DA6338E1C31937004D4EAAD43FEFC956137C5B584B71CD
#        frame=5D032431D84C41E38F045AD126243FD6F67CE2669AAB8C45E7FA36B49025CDBD
#   20:  pc=E1D2F7A0F69A74E9E5ECF490F666B75CA328A45EFDA33F99982CEE783F8FFC9F
#        frame=63E194F0275567CE30299274D98EC9F16E278DA12D2A35C2F7833A68D88A1528
#   60:  pc=A554F55A23DB79006438BD9B2DD00F76767272874657F8E433699913049B808C
#        frame=B66173DD2A256C6D30C721C4A719D33524215898D1BDB1CA08EB210A5B8FBB73
#   115: pc=B972F4F4463DDBB28303BC1F694C7BA6DA1CDED76D656D0A79D12D636EC361A6
#        frame=AD80E280F4908759F066A85204403723D07408EF353491585247667D73074EFE
#
# Rung 3's pc digest USED TO be the same value
# tests/golden/object_pop_002_baseline.json carries for the frozen V134
# collection -- that was the control rung being byte-identical to what
# shipped.  It no longer is, on purpose: rung 3 now names P0 and P91 and the
# frozen V134 collection still does not (nor should it -- this project does
# not edit it).  tests/test_world_population.py's
# ``test_rung_three_differs_from_the_shipped_default_by_exactly_the_two_
# added_names`` pins the narrower invariant that survives.
# AMENDMENT 2026-08-26 (round 1cwih0, runtime.py swapped corpse_override ->
# full_roster_override).  Every digest below moved again: full_roster_override
# puts all 13 mob_death roster identities on the wire unconditionally (a
# FACTION_SPLICE_BYTES=5 name+faction insert per identity versus the default
# census entry -- see mob_death.full_roster_override's own docstring, "WIRE
# LAYER, round 1cwih0" section, for the per-identity check that established
# this is the only mechanism and covers all four affected files, not just
# this one). Re-derived here from the real dispatcher at PIN_ANCHOR, not
# hand-typed, same as every prior amendment. The pre-swap (post-GT-078)
# digests this replaces are kept as comment history rather than deleted,
# because they are still correct for what they described (a census with no
# mob_death roster override at all, which is the gap full_roster_override
# closes):
#
#   3:   pc=638FC719659DE7181A8034ADAF2C5277292DAA731281E3375D8F66D16831B0C2
#        frame=C8323CB6F65479F5474C43DD24CFAFFC100188EE82BA4064BB8A502632408D18
#   20:  pc=4ED557ED0D7B86EB70FC2AB8F486900E76EE1F1F1033A5EFD70462F488292556
#        frame=214D7418094EED5F011D58D2B36D8BB0A756F6FD95AEE5CD152EBF2E4F6917E4
#   60:  pc=57BA09EC556CF778778F323EDF8DB1AE0C0A0C91E2D317EFC5E2A2F6E163583D
#        frame=1A50BE5CC31C9E6809AD289CBBA30F86F31F6EF3B99DB8E839B6A2B7B9D9DF35
#   115: pc=D0F55C5ECF93642BCB560AC928BEB6750B1856CAA0475C876E1FB0A76C904C47
#        frame=C77D1F5CE5F3AD7E39D320A5FC6DB302CF23A2B6EF4F0C5D6B8DD2DE6C60F55D
# AMENDMENT 2026-08-28 (COO-DECISION 2026-08-28T01:46+07:00, lane B).  Every
# digest below moved a THIRD time: field_mobs.hostile_npc_attr now always
# sends the mined MOBS speed (BasicAttr bit 0x0040, f32 @ +0x54) alongside the
# existing FACTION_SPLICE_BYTES=5 insert, so every full_roster_override'd
# identity on the wire carries 10 extra bytes, not 5 -- see
# field_mobs.hostile_npc_attr's own docstring and
# mob_death.BASIC_BIT_MOVEMENT_SPEED.  Re-derived here from the real
# dispatcher at PIN_ANCHOR, not hand-typed, same as every prior amendment.
# The pre-this-round (1cwih0-era) digests this replaces are kept as comment
# history rather than deleted, because they are still correct for what they
# described (a census whose overridden bodies carry no speed field):
#
#   3:   pc=EEFB8C3DE32C623FE5A593C694AC4F6DC1DF0C4431EF16DAB1E302C92EC729E7
#        frame=4EB642ED7FFA5B0010FA1BC2A35599047DE5C432B826C459E0749694353B9F50
#   20:  pc=1467DF0CEE8BA32BE6D37794A936BE02DDBB9127CD0A660C581AA5718CA78EC4
#        frame=751148EB2F60046C5709C2E273AE4018A9E8706430F2347E9850B90DA6C63239
#   60:  pc=25C7F8F75D65A5C0C3D8DF6475C7D73E011AEA11EAFEC23A243AD6D0F371BB6F
#        frame=7D37FE495273276C7DFEB2D8E02F7391785F7E2EB07AE092F284D832B682A651
#   115: pc=9C3BB2790E9B6BB7CDC61A1E366E87666755461B3BC8EE90ADE7F563E4C4FEED
#        frame=49E4A252B6258A575079C8656DA774ACEE5E9270F405D37178F03A890A677BA7
# AMENDMENT 2026-08-28 (RE-117, this round).  Every digest below moved a
# FOURTH time: field_mobs.hostile_npc_attr now also always sends the mined
# MOBS level (BasicAttr bit 0x0002, u16 tag 0x12 @ +0x5E), so every
# full_roster_override'd identity on the wire carries 3 more extra bytes on
# top of the existing faction+speed inserts.  Re-derived here from the real
# dispatcher at PIN_ANCHOR, not hand-typed, same as every prior amendment.
# The pre-this-round digests this replaces are kept as comment history:
#
#   3:   pc=0CF18E300AF2BC9916000A96BDE25388A183779E8CF89572BC879AD297643FEE
#        frame=25D452BF8EA5E2E071E0DB89C3C866EAE3964AA3DE5E7A7182A92546A4BE1FAE
#   20:  pc=7856DFD0021C927241C9B0866FD94BE5D36401DBD9729AA3EA7C59DF119454B1
#        frame=454E5E644177217DA11769E40B8B55B2E67C0ADB58C2A426C73D7B0B9ACCA4B8
#   60:  pc=D4F2FAB89B560F6C915B98E69B22B4825F26E789B666C4D5FC8BCF834B4BFB9A
#        frame=D897F247C9FA4808D988BA4B453195FBB56981AE3F4053FED4C5B00019CF2424
#   115: pc=3BE1911DD640E55BED181E92CEE8E465973ACC6049DDC69A08DBC970A1DA74E7
#        frame=60E179E88BFE4777DC5DF96B3D3AE1850433B7C1ACEBFD172E133896B5A7F1A3
# AMENDMENT 2026-08-28 (RE-128 / CLINE identities, this round).  Every digest
# below moved a FIFTH time, and this one is not a byte-size change: ``_entry()``
# in world_population.py now sends the RESOLVED ``MOBS.n_ID``, that MOBS row's
# own ``s_OUTFIT`` and its ``MOBS_TIP`` name instead of the scene file's Mob-Set
# number, its preset and its Mob-Set-numbered label -- which is the substitution
# GT-078 put on the owner's screen and had rejected.  MEMBERSHIP moved too: the
# seven placements whose Mob-Set number resolves to no MOBS row are dropped, so
# the top rung is 108 actors and rung 3 is (30, 91, 1) rather than (0, 30, 91).
# Re-derived here from the real dispatcher at PIN_ANCHOR, not hand-typed, same
# as every prior amendment.  The pre-this-round digests this replaces are kept
# as comment history rather than deleted, because they are still correct for
# what they described (a census that shipped Mob-Set numbers as identities):
#
#   3:   pc=C14D889362DEAE4093FBF81CFF097B6B50224A0670DD731E76F59DC44D572F3A
#        frame=A4A3EEA4B648B1AC853CF82B70589D3434D9A43DD90BBF46CF7F24CFB663B706
#   20:  pc=17FA4A6AADB21A2D5C4D52354676E313C7F25D5FEBFA8BFF41492F00D4BCE8F5
#        frame=CE0046A5CB4E42F67BF00DB5CED290CA90BBC7FDA1A8D083CA4573A9662EC300
#   60:  pc=4187E13AC7F6A0D77C8829689737F871D99F8B07DEECCCC0BF2BCBF27270FDE2
#        frame=39A9A2A6CE88201619DE91CF4AF1986823936D1B8AFFD7C81B4F6DB584FA4C5A
#   115: pc=2D43E2A626E48D882E5B8C76E342ED9F9D705E4948B8C7954C1B5D7EF9495DAB
#        frame=6D2E776F57CC2A0B1F4ABE371B95C23B18991DAD84131FB9B5BEACAB400F3A0A
#
# The key is still the rung that was ASKED for.  115 is a request; 108 is what
# assembled and what the label, the header and the console line all say.
CENSUS_WIRE_SHA256 = {
    3: ("393D3E9E4A2F4AB939E90F09EA0E5C6DC6B0E871D5D4D7DAB01946EABAF4B1DD",
        "11AB0C5C95C8A3F7EC3E85CC004508C0C34727E26AA0AA5B742FEBBBF8052AB9"),
    20: ("70D7D8914CD8BA2D7C909853ECED3C3320C7920EF9E12229B3A746F9486E1AAA",
         "DDABF41B17648CA9B8E3F4EB13039DF352A627124601DFA1398E42A9A336721B"),
    # AMENDMENT round szdkgs (LANE-B): the two rungs large enough to include
    # placements 103/105/107/109 moved, and THAT MOVEMENT IS THE ROUND'S
    # DELIVERABLE, not a regression: those four now ship n_ID 916 "Training
    # Iron Man" with avatar M016_000_000_N instead of Mob-Set 97 "Mutant Green
    # Eagle" with M011_000_002_SP3, which is 24 bytes shorter across the four.
    # Rungs 3 and 20 do not include those placements and are byte-identical,
    # which is the control that says only the intended rows moved.
    # ~~60:  pc=9CEF203F8DED6FE73EAA9DF8D044330FB98046776A2840728EFCE5EA046007C7
    #        frame=42DA2662CBF20BE6A774CD578C61DBDD77F779DCAB795F3DA8E2A26AA364F165
    # ~~115: pc=1E52C78765C59DC313313505BD690B1B7F0D2040FC4111D45AC66F7CF300C53E
    #        frame=FC1F9B1FA4C1853ED42F9BE22F50483B2C11E2FA516B9D7981FD9C68FBF2D4D7~~
    60: ("DB350F54119E20C06858028F55E2F1545CFA0F290787B24F9CB6E5859D42F074",
         "30984FB4FB1D53D35AA1614D587A538B6815709CF8EB6A71C83539679ABA97D0"),
    115: ("9A7BA9A5822E7E4809C51DD22B1C0E03396D3083F732A5EF63FA7334FC3C3D85",
          "41A71F1BBBF490E787E2A090372A15076AEFA7A1340B683BD8BE84CFC34B91E0"),
}
PIN_ANCHOR = (10.0, 20.0, 30.0)

# AMENDMENT 2026-08-28 (LANE-A, RE-128 / CLINE identities).  115 is still the
# frozen placement table's size and still the target every console line reports
# against; 108 is what ASSEMBLES, because seven of those placements have a
# Mob-Set number whose CLINE leader has no CONSTDATA MOBS row (or is 0, or has
# no avatar template) and therefore no identity that can be shipped without
# going back to the numbering GT-078 disproved.  Every "115" in this file that
# meant "the census as built" became this constant; the ones that mean "the
# size of the source table" stayed 115.  See
# world_population.unshippable_placements() for the seven, with reasons.
SHIPPED_CENSUS_COUNT = 108

INITIAL_PREFIX = "WORLD_CENSUS_INITIAL_"
REAPPLY_PREFIX = "WORLD_CENSUS_REAPPLY_"
FROZEN_LABELS = (
    "V134_P0_P30_P91_ISOLATED_INITIAL_READY",
    "V134_P0_P30_P91_ISOLATED_REAPPLY_READY",
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class WorldCensusWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
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

    def tearDown(self):
        self.tmp.cleanup()

    # ----- harness ----------------------------------------------------------

    def _state(self, token, *, ready=True, **kwargs):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector, **kwargs,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        state.runtime_ack_sent = ready
        state.welcome_message_sent = ready
        state.current_scene_music_sent = ready
        return state

    def _target_pos_pc(self, xyz, heading=0.0, moving=0, derived=0):
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + b"".join(
                self.legacy.f32tag(value) for value in (*xyz, heading)
            )
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, derived)
        )

    def _step(self, state, xyz=(10.0, 20.0, 30.0), **kwargs):
        return state.dispatch(
            self.legacy.parse_outer(self._target_pos_pc(xyz, **kwargs))
        )

    def _census(self, actions):
        return [
            action for action in actions
            if action[0].startswith("WORLD_CENSUS_")
        ]

    def _with_roster_override(self, generation, state):
        """The SAME override runtime.py's dispatch now applies, hung off an
        INDEPENDENTLY-built generation, so a test comparing the dispatcher's
        real output to a from-scratch build compares like with like.

        AMENDMENT 2026-08-26 (round 1cwih0, runtime.py swapped
        corpse_override -> full_roster_override).  Before this swap
        ``build_world_population`` alone WAS the expected wire, because the
        dispatch's corpse_override call returned an empty dict against a
        fresh register/ledger and was a no-op.  It no longer is:
        full_roster_override returns all 13 mob_death roster identities
        unconditionally, so an "expected" object that skips it is comparing
        against bytes runtime.py no longer sends.  ``state`` is passed in
        (not a fresh register/ledger) so this reuses the exact register and
        ledger the dispatch itself read from, not a reconstruction of it.
        """
        override = mob_death.full_roster_override(
            self.legacy, field_mobs.load_roster(),
            state.mob_death_register, ledger=state.mob_combat_ledger,
        )
        if not override:
            return generation
        return _apply_mob_death_census_override(
            self.legacy, generation, override,
        )

    def _choose_npc_pc(self, identity):
        vitals = [
            self.legacy.u16tag(0x12, self.legacy.TARGET_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, identity)
            + self.legacy.u8tag(0x08, 2),
            self.legacy.u16tag(0x12, self.legacy.CHOOSE_NPC)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.qwordtag(0x32, identity),
        ]
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, len(vitals))
            + b"".join(vitals)
        )

    # ----- the default boot is the census -----------------------------------

    def test_the_default_boot_queues_the_whole_census_twice(self):
        """The label said 115 until RE-128; it says 108 now, and that IS the
        whole census - the count in the label is what ASSEMBLED, and seven of
        the 115 frozen placements have no shippable identity.
        """
        state = self._state("census_default")
        actions = self._step(state)
        census = self._census(actions)
        self.assertEqual(
            [action[0] for action in census],
            [f"{INITIAL_PREFIX}{SHIPPED_CENSUS_COUNT}",
             f"{REAPPLY_PREFIX}{SHIPPED_CENSUS_COUNT}"],
        )
        self.assertEqual([action[3] for action in census], [0.0, 3.0])
        # The same collection twice, exactly as the frozen branch does it: the
        # V138 nearest-20 runtime pass that was accepted was an initial plus a
        # model-ready reapply, not a single frame.  Compared against an
        # INDEPENDENT build rather than against each other -- the dispatcher
        # queues one object twice, so census[0] == census[1] cannot fail and
        # would be decoration.
        independent = self._with_roster_override(
            world_population.build_world_population(
                self.legacy, (10.0, 20.0, 30.0), scene_id=1,
            ),
            state,
        )
        for action in census:
            self.assertEqual(action[1], independent.pc)
            self.assertEqual(action[2], independent.frame)
        self.assertEqual(
            census[1][3], world_population.INITIAL_REAPPLY_MS / 1000.0,
        )
        self.assertEqual(state.world_census_actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            len(state.world_census_indices), SHIPPED_CENSUS_COUNT)
        self.assertIs(state.world_census_refused, False)

    def test_the_frozen_three_actor_labels_are_gone_from_the_default_boot(self):
        """The point of the build order, stated as a negative."""
        state = self._state("census_replaces")
        labels = [action[0] for action in self._step(state)]
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, labels)

    def test_the_bookkeeping_the_frozen_branch_commits_is_committed(self):
        """Downstream frozen paths read this state; it has to match the wire."""
        state = self._state("census_books")
        # The inherited branch is disarmed at construction, not from inside
        # dispatch -- see the comment at that assignment for the two measured
        # reasons why.
        self.assertIs(state.npc_spawn_sent, True)
        self.assertIsNone(state.population_indices)
        self.assertIn("world_census_armed", state.events)
        actions = self._step(state)
        generation = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        self.assertIs(state.npc_idle_action_sent, False)
        self.assertEqual(state.population_indices, generation.indices)
        self.assertEqual(state.population_refresh_anchor, (10.0, 20.0, 30.0))
        overridden = self._with_roster_override(generation, state)
        self.assertEqual(self._census(actions)[0][1], overridden.pc)
        self.assertEqual(self._census(actions)[0][2], overridden.frame)

    def test_the_label_carries_the_count_that_actually_went_out(self):
        """v141 prints '[G>] <label> (N bytes)' per queued action at SEND time
        (v141:7762).  The rung has to be readable from that one line, or four
        attended boots of the GT-078 staircase are indistinguishable in the
        console the tester is actually watching.

        AMENDMENT 2026-08-28 (RE-128).  The label carries what ASSEMBLED, not
        what was requested, and those are now two different numbers at the top
        rung: a request for the whole 115-row census assembles 108 because
        seven placements have no shippable identity.  That is the point of the
        label - a tester reading one console line has to see the count that
        really went on the wire, not the count somebody asked for.
        """
        for rung in world_population.STAIRCASE_RUNGS:
            with self.subTest(rung=rung):
                assembled = (
                    SHIPPED_CENSUS_COUNT
                    if rung == world_population.CENSUS_COUNT else rung
                )
                state = self._state(
                    f"census_rung{rung}", world_census_actor_count=rung,
                )
                census = self._census(self._step(state))
                self.assertEqual(
                    [action[0] for action in census],
                    [f"{INITIAL_PREFIX}{assembled}",
                     f"{REAPPLY_PREFIX}{assembled}"],
                )
                self.assertEqual(state.world_census_actor_count, assembled)
                self.assertEqual(len(state.population_indices), assembled)

    def test_rung_three_carries_resolved_identities_the_frozen_collection_lacks(
        self,
    ) -> None:
        """Was ``test_rung_three_differs_from_the_frozen_collection_by_the_two_added_names``.

        The control rung, checked against the frozen encoder itself.
        ``make_v112_monster_shop_population_state`` is what a REFUSING session
        still falls back to, and this project does not edit it.

        SUPERSEDED HISTORY.  ~~Before GT-078's name fix, rung 3 matched it byte
        for byte.~~  ~~Then it differed by exactly the two name tags
        ``_entry()`` added for P0 and P91, plus the measured
        ``roster_splice_bytes`` full_roster_override inserts for P30, and the
        pinned sizes were 577/590.~~

        SUPERSEDED 2026-08-28 (RE-128 / CLINE identities).  Byte-delta
        equality is gone for good.  The frozen collection sends each
        placement's MOB-SET NUMBER and the scene file's preset as its identity
        -- the pair GT-078 put on the owner's screen and had rejected -- and
        rung 3 now sends the resolved ``MOBS.n_ID``, that row's ``s_OUTFIT``
        and its ``MOBS_TIP`` name.  Membership moved too: P0's Mob-Set 1
        resolves to CLINE leader 155, which has no MOBS row, so P0 is dropped
        and the third slot is the nearest resolvable placement at this anchor.

        What is asserted instead is the new invariant, plainly: the dispatcher
        queues exactly the census module's own rung-3 bytes (with the roster
        splice the dispatch applies), every member carries its resolved id and
        MOBS_TIP name, and none of those names appear in the frozen bytes.
        See tests/test_world_population.py's
        ``test_rung_three_ships_resolved_identities_the_frozen_default_never_had``
        for the same invariant proven without the dispatcher in between.
        """
        from pirateforce_foundation import world_port_royal_identity as identity
        from pirateforce_foundation.population import load_port_royal_placements

        state = self._state("census_control", world_census_actor_count=3)
        census = self._census(self._step(state))
        frozen_pc, frozen_frame, frozen_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        # The frozen collection is untouched by this lane, at its pinned size.
        self.assertEqual(len(frozen_pc), 504)
        self.assertEqual(len(frozen_frame), 517)
        self.assertEqual(tuple(row[0] for row in frozen_rows), (0, 30, 91))

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        plain_rung3 = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1, actor_count=3,
        )
        overridden_rung3 = self._with_roster_override(plain_rung3, state)
        self.assertEqual(census[0][1], overridden_rung3.pc)
        self.assertEqual(census[0][2], overridden_rung3.frame)
        roster_splice_bytes = len(overridden_rung3.pc) - len(plain_rung3.pc)
        self.assertEqual(
            len(overridden_rung3.frame) - len(plain_rung3.frame),
            roster_splice_bytes,
        )

        # P0 is gone from the control rung, for a recorded reason, and the two
        # pinned members that survive still lead it.
        self.assertEqual(plain_rung3.indices[:2], (30, 91))
        self.assertIsNotNone(
            identity.unresolved_reason(placements[0].template_id))
        self.assertNotIn(0, plain_rung3.indices)
        self.assertEqual(state.population_indices, plain_rung3.indices)

        queued_pc = census[0][1]
        for index in plain_rung3.indices:
            resolved = identity.resolve(placements[index].template_id)
            self.assertIsNotNone(resolved)
            if index == 30:
                # P30's census body does not survive to the wire on this path
                # at all: full_roster_override replaces it wholesale with
                # ``field_mobs.hostile_actor_entry``, whose identity comes from
                # LANE-B's mined roster row rather than from this crosswalk.
                # Recorded here so the exception is visible rather than
                # silently making the loop below weaker; the byte-for-byte
                # check of that substitution is
                # ``test_every_field_mob_body_in_the_queued_frame_is_the_
                # hostile_body`` below.
                self.assertIn(
                    field_mobs.hostile_actor_entry(
                        self.legacy,
                        [mob for mob in field_mobs.load_roster()
                         if mob.placement_index == 30][0],
                    ),
                    queued_pc,
                )
                continue
            self.assertIn(
                self.legacy.u8tag(0x0B, 0x01 | 0x04)
                + self.legacy.u16tag(0x12, resolved.mobs_n_id),
                queued_pc,
            )
            self.assertIn(self.legacy.wstr_tag(resolved.name), queued_pc)
            self.assertNotIn(
                self.legacy.wstr_tag(resolved.name), frozen_pc)
        # Pinned sizes, re-derived: 577/590 while rung 3 was (P0, P30, P91)
        # carrying the frozen table's own names.
        self.assertEqual(len(census[0][1]), 567)
        self.assertEqual(len(census[0][2]), 580)

    def test_the_census_is_one_shot_per_session(self):
        """The pc/frame byte counts below are RE-DERIVED, not hand-typed.

        AMENDMENT 2026-08-26 (post-GT-078 name fix).  17928/17942 were the
        full-census sizes before ``_entry()`` started putting every
        placement's own name on the wire; they became 20944/20958 because
        every one of the 115 members carries a name tag it did not carry
        before.  Computed here from the real encoder rather than hand-typed a
        second time, so this event string and the module's own numbers cannot
        drift apart silently.

        AMENDMENT 2026-08-26 (round 1cwih0, runtime.py swapped
        corpse_override -> full_roster_override).  20944/20958 moved again,
        to 21007/21021: full_roster_override puts all 13 mob_death roster
        identities on the wire, each carrying the same
        ``field_mobs.FACTION_SPLICE_BYTES``-sized insert (see
        ``_with_roster_override``'s docstring), so ``generation`` here is
        overridden the same way the dispatch itself overrides it before this
        event string is computed downstream.

        AMENDMENT 2026-08-28 (COO-DECISION 2026-08-28T01:46+07:00, lane B).
        21007/21021 moved a third time, to 21072/21086: field_mobs.
        hostile_npc_attr now always sends the mined MOBS speed field too
        (bit 0x0040), so each of the same 13 overridden identities carries
        one MORE tagged f32 (5 bytes) on top of its existing faction splice
        -- 13 * 5 = 65 extra bytes total, re-derived here, not hand-typed.

        AMENDMENT 2026-08-28 (RE-117, this round).  21072/21086 moved a
        fourth time, to 21111/21125: hostile_npc_attr now also always sends
        the mined MOBS level field (bit 0x0002), so each of the same 13
        overridden identities carries one MORE tagged u16 (3 bytes) --
        13 * 3 = 39 extra bytes total, re-derived here, not hand-typed.
        """
        state = self._state("census_once")
        self.assertEqual(len(self._census(self._step(state))), 2)
        self.assertEqual(self._census(self._step(state)), [])
        generation = self._with_roster_override(
            world_population.build_world_population(
                self.legacy, (10.0, 20.0, 30.0), scene_id=1,
            ),
            state,
        )
        self.assertEqual(
            [event for event in state.events
             if event.startswith("world_census_committed_")],
            [
                f"world_census_committed_actors_{SHIPPED_CENSUS_COUNT}_pc_"
                f"{generation.pc_bytes}_frame_{generation.frame_bytes}"
            ],
        )
        # ~~(20402, 20416)~~ round szdkgs: 24 bytes shorter, because the four
        # practice dummies carry a shorter avatar name than the eagles they
        # replace.  This number is the cheapest proof that this round's
        # identity change actually reaches the wire.
        self.assertEqual((generation.pc_bytes, generation.frame_bytes),
                          (20378, 20392))

    def test_world_density_line_is_printed_alongside_the_census_line(self):
        """world_density is LANE-A's tenth production lane (production_allowed
        = True) and was, until this wiring, imported by nothing at all. It
        rides the same scene_id == 1 guard the census line already sits
        behind, so proving it fired is a console-output check, not a new
        branch: the WORLD_DENSITY line has to appear on the same default boot
        that already prints WORLD_CENSUS, and neither line may crowd out the
        other.
        """
        state = self._state("census_density")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self._step(state)
        lines = captured.getvalue().splitlines()
        self.assertTrue(
            any(line.startswith("WORLD_DENSITY ") for line in lines),
            f"no WORLD_DENSITY line in captured output: {lines!r}",
        )
        self.assertTrue(
            any(line.startswith("WORLD_CENSUS ") for line in lines),
            f"no WORLD_CENSUS line in captured output: {lines!r}",
        )

    # ----- the anchor -------------------------------------------------------

    def test_the_census_is_anchored_on_this_frame_not_the_previous_one(self):
        """v141 sets last_target_pos from the CURRENT frame (v141:4259) before
        its population branch reads it (v141:4292).  This wiring runs BEFORE
        the inherited dispatch, so reading last_target_pos alone would anchor
        the census one step behind the player and silently order the census
        around a position they have already left.
        """
        far = (30000.0, 25000.0, 1000.0)
        state = self._state("census_anchor")
        census = self._census(self._step(state, xyz=far))
        expected = self._with_roster_override(
            world_population.build_world_population(
                self.legacy, far, scene_id=1,
            ),
            state,
        )
        self.assertEqual(census[0][1], expected.pc)
        self.assertEqual(state.population_refresh_anchor, far)
        # Not a tautology: a different anchor really does order the census
        # differently, so this test can fail.
        near = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        self.assertNotEqual(expected.indices, near.indices)

    # ----- containment ------------------------------------------------------

    def test_an_opt_in_lane_keeps_the_population_it_was_measured_against(self):
        """Several lanes pin actor identities inside the band the census
        occupies (115 identities spread over a 149-wide index space, 34 gaps).
        Widening the population underneath a lane that is measuring something
        else would change that lane's control without anyone noticing.
        """
        state = self._state(
            "census_contained",
            ground_loot_hypothesis_scenario=(
                load_ground_loot_hypothesis_scenario(GROUND_LOOT_SCENARIO)
            ),
        )
        labels = [action[0] for action in self._step(
            state, xyz=(
                state.foundation.selected.position.x,
                state.foundation.selected.position.y,
                state.foundation.selected.position.z,
            ),
        )]
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIsNone(state.world_census_actor_count)

    # ----- refusals ---------------------------------------------------------

    def test_an_impossible_rung_is_refused_at_construction(self):
        for bad in (0, -1, 116, 3.0, "3", True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        world_census_actor_count=bad,
                    )

    def test_a_compose_refusal_falls_back_to_the_shipped_branch_and_latches(self):
        """Fail closed means the player still gets what they got yesterday.

        A raise inside the builder must not kill the connection and must not
        leave the session with no population at all: npc_spawn_sent is left
        alone so the frozen three-actor branch runs on this very frame, and the
        refusal latches so it cannot retry itself onto the wire on every step.
        """
        original = world_population.build_world_population

        def explode(*args, **kwargs):
            raise ValueError("frozen placement source count drift")

        state = self._state("census_refused")
        world_population.build_world_population = explode
        try:
            labels = [action[0] for action in self._step(state)]
        finally:
            world_population.build_world_population = original
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIs(state.world_census_refused, True)
        self.assertIsNone(state.world_census_actor_count)
        self.assertIn(
            "world_census_compose_refused_ValueError", state.events,
        )
        # Latched: a later step neither retries nor emits a second refusal.
        self.assertEqual(self._census(self._step(state)), [])
        self.assertEqual(
            state.events.count("world_census_compose_refused_ValueError"), 1,
        )

    def test_a_world_density_console_line_failure_does_not_touch_the_census(
        self,
    ):
        """world_density.m1_console_line() reads a file off disk on every
        call with no try/except in its own chain.  A missing/corrupt
        scenarios/world_scene_density_001.json must not unwind out of
        dispatch (v141:7440 has no except around it), and -- unlike a
        compose refusal -- it must not touch the census at all: the census
        was already built and committed by the time this diagnostic line
        prints, so the fix's job is to lose nothing but the print.
        """
        original = world_density.m1_console_line

        def explode(*args, **kwargs):
            raise ValueError("world_scene_density_001.json missing")

        state = self._state("census_density_console_line_failed")
        world_density.m1_console_line = explode
        try:
            actions = self._step(state)
        finally:
            world_density.m1_console_line = original
        self.assertEqual(len(self._census(actions)), 2)
        self.assertEqual(state.world_census_actor_count, SHIPPED_CENSUS_COUNT)
        self.assertIs(state.world_census_sent, True)
        self.assertTrue(
            any(
                event.startswith("world_density_console_line_failed_")
                for event in state.events
            ),
            f"no world_density_console_line_failed_ event in {state.events!r}",
        )
        self.assertIn(
            "world_density_console_line_failed_ValueError", state.events,
        )

    # ----- what the wider membership changes downstream ---------------------

    def test_the_v138_destination_population_still_replaces_the_census(self):
        """A regression that was proposed and does not exist.

        The V139 P86 interaction gates compare population_indices against
        V138_MARKER1_NEAREST_INDICES (v141:4267, v141:4495), so a wider boot
        population looks like it must break them.  It does not: the V138
        marker branch REASSIGNS population_indices when it fires (v141:3742),
        and it does not read the boot population at all.  Pinned here because
        the argument is easy to make and wrong.
        """
        state = self._state("census_v138")
        self._step(state)
        self.assertEqual(len(state.population_indices), SHIPPED_CENSUS_COUNT)
        state.v137_marker1_transport_sent = True
        state.dispatch(self.legacy.parse_outer(
            self.legacy.V138_MARKER1_READY_PC
        ))
        self.assertIs(state.v138_marker1_population_sent, True)
        self.assertEqual(
            state.population_indices,
            self.legacy.V138_MARKER1_NEAREST_INDICES,
        )

    def test_the_wider_membership_widens_who_answers_a_click(self):
        """Declared, not hidden: this is a real behavioural change.

        The frozen ChooseNPC path answers only for actors in
        population_indices (v141:4409).  With three members, 112 placements
        were silently ignored; with the census they are members, so clicking
        one now composes the V98 face/conversation response -- and that
        response rebuilds the WHOLE population snapshot, so a click now costs
        a census-sized frame instead of a 564-byte one (the frozen three-actor
        rung's size after GT-078's name fix; it was 504 before).  Nothing here
        says a client does anything useful with either; that is attended work.
        """
        state = self._state("census_click")
        self._step(state)
        # CORE-REQUEST-014 (2026-08-27): placement index 1 is now Columbus
        # (MOBS n_ID 156) and gets an ADDITIONAL server response of its own
        # (see runtime.py's _dispatch_columbus_quest3021) on top of the V98
        # generic response this test is about, so this test picks a
        # different, still-non-special placement to keep testing "widened
        # membership in general" without entangling Columbus's own wiring.
        outsider = 0x2000 + 3 + 1  # placement 3, not one of P0/P30/P91/Columbus
        self.assertNotIn(3, world_population.SHIPPED_ISOLATED_INDICES)
        actions = state.dispatch(
            self.legacy.parse_outer(self._choose_npc_pc(outsider))
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "V98_NPC_FACE_PLAYER_POSITION_HEADING_P3",
                "V98_NPC_CONVERSATION_DEFAULT_P3",
            ],
        )
        self.assertGreater(len(actions[0][1]), 504)


    # ----- the wire itself, pinned as bytes at every rung -------------------

    def test_every_rung_matches_its_pinned_wire_digest(self):
        """The only assertion in this lane that a change to the BUILDER cannot
        move with it.  See CENSUS_WIRE_SHA256 for the mutant that motivated it.
        """
        for rung, (pc_sha, frame_sha) in sorted(CENSUS_WIRE_SHA256.items()):
            with self.subTest(rung=rung):
                state = self._state(
                    f"census_pin{rung}", world_census_actor_count=rung,
                )
                census = self._census(self._step(state, xyz=PIN_ANCHOR))
                self.assertEqual(len(census), 2)
                self.assertEqual(
                    hashlib.sha256(census[0][1]).hexdigest().upper(), pc_sha,
                )
                self.assertEqual(
                    hashlib.sha256(census[0][2]).hexdigest().upper(),
                    frame_sha,
                )

    # ----- the two ways the trigger used to be wrong ------------------------

    def test_the_census_fires_on_the_frame_that_sets_the_runtime_ack(self):
        """No test in this file may pre-set runtime_ack_sent, and this is why.

        v141 sets runtime_ack_sent INSIDE its dispatch (v141:3771) and only
        then reaches its population branch (v141:4292), so the flag is false
        on entry to the frame that arms it.  An earlier version of this wiring
        read the flag BEFORE super().dispatch and therefore lost that frame
        entirely: the frozen three-actor branch won the session, silently, with
        world_census_refused still False and no event saying so.  A client that
        reconnects mid-session sends TargetPos first, so that was not an exotic
        shape.
        """
        state = self._state("census_ack", ready=False)
        self.assertIs(state.runtime_ack_sent, False)
        actions = self._step(state)
        labels = [action[0] for action in actions]
        self.assertIn("RUNTIME_RES_ACK_FIRST_REQ", labels)
        self.assertIn(f"{INITIAL_PREFIX}{SHIPPED_CENSUS_COUNT}", labels)
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, labels)
        self.assertEqual(state.world_census_actor_count, SHIPPED_CENSUS_COUNT)

    def test_a_target_pos_the_inherited_dispatcher_ignores_composes_nothing(self):
        """The invariant v141:4416 relies on, restated as a test.

        The frozen population branch sits under "outer_id is
        GSCN_RunTimeProtocolReq and teleport_sent" (v141:3680), and
        last_target_pos is assigned only inside that same block (v141:4259).
        So population_indices being set implies last_target_pos is set, and
        v141:4416 unpacks last_target_pos for any member of
        population_indices.  A trigger without those conjuncts could set the
        first without the second, and the next NPC click then raised TypeError
        out of the listener thread -- which has no except clause (v141:7440).
        """
        pc = self._target_pos_pc((-9999.0, 8888.0, 777.0))
        # Same body, different outer envelope: the inherited dispatcher does
        # not look at this frame at all.
        foreign = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_LOGIN_PROTOCOL)
            + pc[len(self.legacy.u16tag(0x12, 0)):]
        )
        state = self._state("census_foreign")
        actions = state.dispatch(self.legacy.parse_outer(foreign))
        self.assertEqual(self._census(actions), [])
        self.assertIsNone(state.population_indices)
        self.assertIsNone(state.last_target_pos)
        # And the click that used to kill the thread is now a no-op.
        self.assertEqual(
            state.dispatch(
                self.legacy.parse_outer(self._choose_npc_pc(0x2002))
            ),
            [],
        )
        # A real frame afterwards still gets the census: nothing was latched.
        self.assertEqual(len(self._census(self._step(state))), 2)

    # ----- containment, part two -------------------------------------------

    def test_the_second_password_lane_keeps_its_measured_population(self):
        """HYP-PF-009 is an opt-in lane that is not a scenario object.

        Its whole measurement is what this client does with an unsolicited
        frame, and it was characterized against the three-actor baseline.  It
        is contained by name because active_lanes cannot see it.
        """
        state = self._state("census_2pw", second_password_mode="bypass")
        labels = [action[0] for action in self._step(state)]
        self.assertEqual(self._census([(label,) for label in labels]), [])
        for frozen in FROZEN_LABELS:
            self.assertIn(frozen, labels)
        self.assertIsNone(state.world_census_actor_count)
        self.assertNotIn("world_census_armed", state.events)

    def test_export_events_is_not_contained_because_it_sends_nothing(self):
        """The other flag outside active_lanes, and the opposite ruling.

        --export-events changes what is printed, never what is sent, and
        GT-076 needs it on the staircase boots.  Containing it would make the
        measurement boots differ from the boot being measured.
        """
        state = self._state(
            "census_events",
            event_exporter=lambda event: None,
        )
        labels = [action[0] for action in self._step(state)]
        self.assertIn(f"{INITIAL_PREFIX}{SHIPPED_CENSUS_COUNT}", labels)

    # ----- the refusal is byte-identical to what shipped --------------------

    def test_a_refusal_queues_the_frozen_collection_byte_for_byte(self):
        """Fail closed means the shipped wire, not an empty town.

        The inherited branch is disarmed at construction, so a refusal cannot
        fall through to it -- the fallback has to rebuild it.  The catch is
        deliberately Exception, not a tuple: the builder reads two frozen
        constants by plain attribute access and calls frozen serializers, so
        drift arrives as AttributeError or struct.error as readily as
        ValueError, and an escape unwinds out of a listener thread that has no
        except clause.
        """
        original = world_population.build_world_population

        def explode(*args, **kwargs):
            raise AttributeError("V117_P30_EXACT_HP")

        state = self._state("census_refused_bytes")
        world_population.build_world_population = explode
        try:
            actions = self._step(state)
        finally:
            world_population.build_world_population = original
        frozen_pc, frozen_frame, frozen_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        self.assertEqual(
            [(label, bytes(pc), bytes(frame), delay)
             for label, pc, frame, delay in actions
             if label in FROZEN_LABELS],
            [
                (FROZEN_LABELS[0], frozen_pc, frozen_frame, 0.0),
                (FROZEN_LABELS[1], frozen_pc, frozen_frame, 3.00),
            ],
        )
        self.assertEqual(self._census(actions), [])
        self.assertIs(state.world_census_refused, True)
        self.assertIs(state.world_census_sent, True)
        self.assertEqual(
            state.population_indices, tuple(row[0] for row in frozen_rows),
        )
        self.assertIn(
            "world_census_compose_refused_AttributeError", state.events,
        )
        self.assertIn("world_census_fell_back_to_frozen_p0_p30_p91",
                      state.events)
        # Latched: the next step neither retries nor re-sends the fallback.
        self.assertEqual(
            [action[0] for action in self._step(state)
             if action[0] in FROZEN_LABELS or action[0].startswith(
                 "WORLD_CENSUS_")],
            [],
        )

    # ----- away from home ---------------------------------------------------

    def test_a_scene_that_is_not_home_gets_no_population_at_all(self):
        """The bg0001 census encodes scene 1 into every actor it builds.

        Delivering it into another map would put dock NPCs in a scene they do
        not belong to, so this refuses rather than degrading to the frozen
        three -- which carry scene 1 just the same.
        """
        state = self._state("census_away")
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected, position=dataclasses.replace(
                selected.position, scene_id=278,
            ),
        )
        actions = self._step(state)
        self.assertEqual(self._census(actions), [])
        for frozen in FROZEN_LABELS:
            self.assertNotIn(frozen, [action[0] for action in actions])
        self.assertIs(state.world_census_sent, True)
        self.assertIn("world_census_skipped_scene_278_not_home", state.events)

    # ----- BUILD-004: the hostile bodies are IN the one census frame --------
    #
    # WHY THESE FOUR EXIST, and what was vacuous before them.  Every other
    # assertion in this file that touches the roster override compares the
    # dispatcher's pc against ``_with_roster_override(build_world_population(
    # ...))`` -- the same producer on both sides.  That comparison passes
    # unchanged if ``full_roster_override`` returns an EMPTY dict and no
    # hostile byte reaches the wire at all, because then both sides are the
    # un-overridden census.  GT-084 (attended, 2026-08-27 02:05) reported
    # "0 hostile frames" off exactly that blind spot, and the COO's 03:45
    # decision made a console-verified hostile frame a gate on every ticket
    # that depends on hostiles.
    #
    # So these read the DISPATCHER'S OWN QUEUED BYTES and walk them by
    # ``entry_bytes``, comparing each roster member's slice against a
    # ``field_mobs.hostile_actor_entry`` built independently from the roster
    # row -- a producer the census path does not go through.  They can fail.

    def _queued_entries_by_identity(self, generation):
        """Split a generation's pc back into identity -> entry bytes.

        Uses ``world_population``'s own public header constant and the
        generation's own ``entry_bytes``, the same two facts
        ``_apply_mob_death_census_override`` walks, and refuses if they do not
        account for the whole payload -- so a frame that silently lost or
        gained a body cannot be read as if it were intact.
        """
        offset = world_population.WIRE_HEADER_BYTES
        entries = {}
        for identity, length in zip(
                generation.actor_identities, generation.entry_bytes):
            entries[identity] = generation.pc[offset:offset + length]
            offset += length
        self.assertEqual(
            offset, len(generation.pc),
            "entry_bytes does not account for the whole collection",
        )
        return entries

    def test_the_default_boot_frame_still_carries_the_whole_population(self):
        """No shrinkage.  The hostile splice is a SUBSTITUTION, not a second
        collection: the frame that goes out has to still declare and contain
        all 115 census actors, at the same identities, in the same order.

        This is the assertion that would go red if anyone ever "wired in"
        ``field_mobs.build_field_mob_population`` as a second sender --
        ``make_runtime_remote_actors`` is replace-by-omission, so a 13-actor
        field-mob collection queued alongside the census wipes the other 102
        actors on the client, and the queued label/pc would say 13.
        """
        state = self._state("census_no_shrinkage")
        census = self._census(self._step(state))
        self.assertEqual(len(census), 2)
        plain = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        overridden = self._with_roster_override(plain, state)
        # The membership is untouched by the splice, in count AND in order.
        self.assertEqual(
            overridden.actor_identities, plain.actor_identities,
        )
        self.assertEqual(overridden.actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            world_population.wire_actor_count(overridden), SHIPPED_CENSUS_COUNT)
        # ...and that is what the dispatcher actually queued, both times.
        for action in census:
            self.assertEqual(
                action[0].endswith(f"_{SHIPPED_CENSUS_COUNT}"), True)
            self.assertEqual(action[1], overridden.pc)
            self.assertEqual(action[2], overridden.frame)
        self.assertEqual(state.world_census_actor_count, SHIPPED_CENSUS_COUNT)
        self.assertEqual(
            len(state.world_census_indices), SHIPPED_CENSUS_COUNT)

    def test_the_arrival_frame_queues_no_second_actor_collection(self):
        """The world-wipe guard, and it does not depend on counting encoder
        calls -- it reads the QUEUED BYTES.

        ``make_runtime_remote_actors`` writes a fixed 14-byte header before the
        actor count (world_population:191-197), so any queued pc that starts
        with that header IS a remote-actor collection, however it was built --
        composed on this frame, precomputed at import, or cached.  Under
        replace-by-omission (RE-092) a SECOND such frame on the arrival path
        despawns every identity the first one carried, so exactly two may be
        queued here and they must be the census, twice.

        Measured to catch the real regression: wiring
        ``field_mobs.build_field_mob_population`` in alongside the census
        turns this red.  ``_census()`` filters on the ``WORLD_CENSUS_`` label
        prefix, so a field-mob collection queued under any other label is
        invisible to every other assertion in this file -- which is why this
        one looks at all of ``actions``, not at ``_census(actions)``.
        """
        state = self._state("census_no_second_collection")
        actions = self._step(state)
        collection_header = self.legacy.make_runtime_remote_actors([])[0][
            :world_population.WIRE_COUNT_TAG_OFFSET
        ]
        self.assertEqual(len(collection_header), 14)
        collections = [
            action for action in actions
            if action[1].startswith(collection_header)
        ]
        self.assertEqual(
            [action[0] for action in collections],
            [f"{INITIAL_PREFIX}{SHIPPED_CENSUS_COUNT}",
             f"{REAPPLY_PREFIX}{SHIPPED_CENSUS_COUNT}"],
            "an actor collection other than the census was queued on the "
            "arrival frame: under replace-by-omission that despawns the "
            "actors the other frame carried",
        )
        # Both are the same 115-actor collection, and the count in the bytes
        # agrees with the count in the label.
        for action in collections:
            self.assertEqual(
                int.from_bytes(
                    action[1][
                        world_population.WIRE_COUNT_TAG_OFFSET + 1:
                        world_population.WIRE_COUNT_TAG_OFFSET + 3
                    ],
                    "little",
                ),
                SHIPPED_CENSUS_COUNT,
            )

    def test_every_field_mob_body_in_the_queued_frame_is_the_hostile_body(self):
        """The load-bearing one.  For all thirteen roster identities, the bytes
        the DISPATCHER queued at that identity's placement must equal
        ``field_mobs.hostile_actor_entry`` for that roster row -- byte for
        byte, including the BasicAttr faction bit 0x0400 and the five-byte
        tagged faction splice that makes the monster hostile rather than
        merely present.

        Non-vacuous in both directions: the count is asserted at 13 (so a
        roster that stopped overlapping the census fails instead of passing
        with zero comparisons), and the expected side is built from
        ``field_mobs`` directly, which is NOT the producer
        ``world_population`` uses for a default census member.
        """
        state = self._state("census_hostile_bodies")
        census = self._census(self._step(state))
        queued_pc = census[0][1]
        overridden = self._with_roster_override(
            world_population.build_world_population(
                self.legacy, (10.0, 20.0, 30.0), scene_id=1,
            ),
            state,
        )
        self.assertEqual(queued_pc, overridden.pc)
        entries = self._queued_entries_by_identity(overridden)
        roster = field_mobs.load_roster()
        self.assertEqual(len(roster), 13)
        checked = 0
        for mob in roster:
            self.assertIn(
                mob.actor_identity, entries,
                f"roster identity 0x{mob.actor_identity:X} "
                f"(placement {mob.placement_index}) is not in the census at "
                f"all, so nothing could be overridden for it",
            )
            self.assertEqual(
                entries[mob.actor_identity],
                field_mobs.hostile_actor_entry(self.legacy, mob),
                f"identity 0x{mob.actor_identity:X} is on the wire with a "
                f"body that is not its hostile body",
            )
            # The faction bit is what separates "hostile" from "named NPC";
            # asserted on the QUEUED bytes, not on the expected side.
            self.assertIn(
                bytes(self.legacy.u32tag(
                    field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
                entries[mob.actor_identity],
            )
            checked += 1
        self.assertEqual(checked, 13)
        # And the default census body for the same identity is NOT the
        # hostile body -- otherwise the assertion above proves nothing.
        plain = world_population.build_world_population(
            self.legacy, (10.0, 20.0, 30.0), scene_id=1,
        )
        plain_entries = self._queued_entries_by_identity(plain)
        self.assertNotEqual(
            plain_entries[roster[0].actor_identity],
            entries[roster[0].actor_identity],
        )

    def test_the_arrival_census_makes_exactly_one_collection_call(self):
        """ONE sender, one frame.  ``make_runtime_remote_actors`` is
        replace-by-omission (RE-092): every call replaces the client's whole
        network-actor registry with exactly the identities it carries.  Two
        senders on this path is one of them despawning the other's actors,
        whichever order they go out in -- which is precisely why
        ``field_mobs.build_field_mob_population`` must NOT be called here.

        Counted at the encoder, so a future "just add the field mobs too"
        wiring is caught by the call count rather than by a screen.
        """
        state = self._state("census_one_call")
        calls = []
        original = self.legacy.make_runtime_remote_actors

        def counting(entries):
            calls.append(tuple(len(entry) for entry in entries))
            return original(entries)

        self.legacy.make_runtime_remote_actors = counting
        try:
            census = self._census(self._step(state))
        finally:
            self.legacy.make_runtime_remote_actors = original
        self.assertEqual(len(census), 2)
        # build_world_population composes once; the override splice recomposes
        # the SAME collection once.  Two encoder calls, both over 115 entries,
        # and the second is the one that is queued -- never a third call over
        # a 13-entry field-mob-only collection.
        self.assertEqual(len(calls), 2, f"encoder call shapes: {calls!r}")
        for shape in calls:
            self.assertEqual(
                len(shape), SHIPPED_CENSUS_COUNT,
                "an actor collection was composed over something other than "
                "the full census",
            )
        self.assertNotIn(13, [len(shape) for shape in calls])
        # field_mobs' own dispatching builder stays uncalled on this path.
        self.assertFalse(
            any(len(shape) == len(field_mobs.load_roster())
                for shape in calls),
        )

    def test_the_roster_override_coverage_line_is_printed_on_a_default_boot(
            self):
        """The console gate.  COO decision 2026-08-27 03:45: a ticket that
        depends on hostiles may not be opened until a headless boot has been
        grepped for the hostile frame.  GT-084 grepped for ``FIELD_MOB`` /
        ``HOSTILE`` -- labels that have never existed on this path -- and read
        the silence as proof that no hostile byte went out.

        This pins the line that answers the question, with the numbers a
        grep can read: ``matched=13/13 missing=none``.  ASCII-only, because
        the bridge console is cp874.
        """
        state = self._state("census_coverage_line")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self._step(state)
        lines = captured.getvalue().splitlines()
        coverage = [
            line for line in lines
            if line.startswith("MOB_DEATH_ROSTER_OVERRIDE_COVERAGE")
        ]
        self.assertEqual(
            len(coverage), 1,
            f"expected exactly one coverage line: {lines!r}",
        )
        self.assertEqual(
            coverage[0],
            "MOB_DEATH_ROSTER_OVERRIDE_COVERAGE matched=13/13 missing=none",
        )
        coverage[0].encode("ascii")
        # It does not crowd out the two lines that were already there.
        self.assertTrue(any(l.startswith("WORLD_CENSUS ") for l in lines))
        self.assertTrue(any(l.startswith("WORLD_DENSITY ") for l in lines))

    def test_a_contained_boot_prints_no_coverage_line_because_it_sends_no_census(
            self):
        """The coverage line rides the census branch, so an opt-in boot -- the
        one that deliberately keeps the frozen three-actor population -- must
        not print it.  Without this, a green coverage assertion above could be
        satisfied by a line printed unconditionally somewhere else.
        """
        state = self._state(
            "census_coverage_contained",
            ground_loot_hypothesis_scenario=(
                load_ground_loot_hypothesis_scenario(GROUND_LOOT_SCENARIO)
            ),
        )
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self._step(state, xyz=(
                state.foundation.selected.position.x,
                state.foundation.selected.position.y,
                state.foundation.selected.position.z,
            ))
        self.assertNotIn(
            "MOB_DEATH_ROSTER_OVERRIDE_COVERAGE", captured.getvalue(),
        )

    # ----- BUILD-002 slice 1: the teleport that used to be a literal 1 ------

    def test_the_home_teleport_is_byte_identical_to_the_literal_it_replaced(self):
        """runtime.py:3675 was ``make_login_teleport(1, 0)``.

        It is now a table lookup, which is what lets a character whose row says
        another scene land there.  For a character whose row says scene 1 --
        every character that exists today -- the five arguments the table
        returns are (1, 0, 0.0, 0.0, 0.0), so the frame on the wire has to be
        the same bytes it has always been.  CHARTER-02's cumulative rule at the
        smallest scale there is: this is the assertion that says the change
        cannot cost a player anything.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("travel_home")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc("travel_home")
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        teleport = [
            action for action in actions
            if action[0] == "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE"
        ]
        self.assertEqual(len(teleport), 1)
        expected_pc, expected_frame = self.legacy.make_login_teleport(1, 0)
        self.assertEqual(teleport[0][1], expected_pc)
        self.assertEqual(teleport[0][2], expected_frame)
        self.assertEqual(teleport[0][3], 0.70)


if __name__ == "__main__":
    unittest.main()
