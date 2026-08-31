"""LANE-B: RE-122 (2026-08-28) consumed and pinned as an enforced guard.

RE-122 RESULT (pf_bridge/notes_to_chief/20260828_0815_RE-122-RESULT-SCORE-
IS-SIX-AXIS-MP-UNPROVEN.md) proved CHARCREATE_CLASS.s_SCORE is a six-axis
character-create DISPLAY score with no proven crosswalk to the five ActorAttr
stat fields (STR/CON/DEX/INT/PER) or to MP current/max, and named the
consequence for both building lanes in its own BUILD_IMPACT line (Thai in
the original letter, paraphrased here in English per this project's
ASCII-only rule for anything under src/tools/tests): hard guard, no value
patch -- LANE-A and LANE-B must not ship MP=50/50, MP=100/100, flat stats
5/5/5/5/5, or a mapping from s_SCORE's first five components onto
STR/CON/DEX/INT/PER, in production.

Consuming that finding for LANE-B: none of this lane's modules (mob combat,
mob death, mob AI, mob loot/pickup, field-mob rosters) ever needed a PLAYER
stat value in the first place -- a monster's HP comes from
CONSTDATA_TH__STANDARD_MOB keyed by MOBS' own n_LEVEL_MIN
(field_mob_tables.py's own docstring: "max_hp is the one derived column:
STANDARD_MOB[n_LEVEL_MIN].n_HPMAX"), never from a player-stat table. So
RE-122 costs this lane no code today -- confirmed here by grep before this
file was written: zero real hits for STR/DEX/INT/PER/s_SCORE/STANDARD_BUFF/
CHARCREATE_CLASS/MP_PLACEHOLDER across every module this lane owns (the only
prior hits were substrings of unrelated words, e.g. "PER" inside "PER DROP").

What this file adds is the guard that keeps that true: a literal-text sweep
of every module this lane owns, refusing the exact identifiers RE-122's
BUILD_IMPACT names, plus the exact placeholder name (MP_PLACEHOLDER) chief's
own R208 round caught and reverted from a DIFFERENT file
(player_wire.py, pirate-force-server) before it shipped -- so a future PR
that pastes that same placeholder pattern into a combat module, instead of
the player composer it belongs nowhere near either, turns this test red
instead of shipping quietly.

This is a NONCLAIM formalized as a test, the same discipline
mob_pickup.py's THE WALL section already uses for
test_the_governed_allowlist_is_the_wall_this_lane_stops_at: RE-122 changes
no behaviour here, so this test changes no behaviour either -- it only makes
the current, already-true absence provable and future-proof, the way the
project's own rule (G-OBS: a human sees it or it did not happen) asks every
claim to be checked rather than merely stated.
"""

from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pirateforce_foundation"

# Every module this lane (COMBAT: mob/death/loot/field-mob) owns and writes
# to. Listed by hand, not globbed, so a new file added under a name this
# lane does not recognize as its own does not silently join the sweep --
# and so the list itself is a second, independent record of what this lane
# claims, next to the mob_*/field_mob_* prefix convention AGENTS.md names.
LANE_B_MODULES = (
    "field_drop_tables.py",
    "field_mob_ai_tables.py",
    # ROUND jqxe6v: the Bg0015 (scene 14) hostile entry-byte composer, built
    # against COO-DECISION 2026-08-31T16:48+07:00's layer-1 unlock.  No
    # player stat of any kind -- it reads MOBS-table rows the same validated
    # way every other scene's roster does. Listed in the same commit as the
    # module, same reason every other entry on this tuple gives.
    "field_mob_hostile_bg0015.py",
    "field_mob_tables.py",
    "field_mob_tables_bg0002.py",
    "field_mob_tables_bg0015.py",
    "field_mobs.py",
    "loot_roll.py",
    "mob_aggro.py",
    "mob_ai_control.py",
    # ROUND 256rvs: the deterministic, per-session caller mob_ai_control's
    # own header names as still missing (mob_ai_control.tick_step had no
    # production caller anywhere in this tree). No player stat of any kind
    # -- it reads a mob's own HP off the combat ledger and the ONE player
    # position a per-session driver already owns. Listed in the same commit
    # as the module, same reason every other entry on this tuple gives.
    "mob_ai_scheduler.py",
    # ROUND wmomy7: the scene-scoped hostile census override, and the
    # census-backing check that found five roster rows with no body.
    "mob_census_hostility.py",
    # ROUND z096sw: the count a recomposed census actually declares to the
    # client, read back off the transmitted collection's own header.  Added
    # in the same commit as the module -- this guard caught it missing on
    # the first full run, which is the tuple doing its job.
    "mob_census_wire_count.py",
    "mob_combat.py",
    # ROUND 6cm6ry: the combat-ledger half of Bg0015's hostile splice gap --
    # measures (never registers) that field_mobs._SCENE_TABLE_MODULES still
    # refusing Bg0015 means the already-sent census CORE-REQUEST's 12
    # visually-hostile identities would refuse every hit. No player stat of
    # any kind -- reads Bg0015's own mined rows through the one approved
    # composer and the two live scenes' rosters through field_mobs' own
    # public readers. Listed in the same commit as the module, same reason
    # every other entry on this tuple already gives.
    "mob_combat_bg0015_gap.py",
    # LANE-B round (this round): RE-157 job 2's fail-closed announced-actor
    # membership predicate, built with no runtime.py call site yet -- see the
    # module's own CORE-REQUEST. Listed in the same commit as the module,
    # same reason every other comment on this tuple already gives.
    "mob_combat_membership.py",
    "mob_death.py",
    # ROUND jop8ph: whether a combat ledger may be consulted while composing
    # a given scene's census -- the build half of the scene-bound ledger
    # admission decision.  Listed in the same commit as the module, because
    # round z096sw learned the hard way that this tuple is what makes a new
    # module part of the sweep at all.
    "mob_ledger_admission.py",
    "mob_diag_multi_object.py",
    # ROUND m0vp7m: MOB-DROP-PRESENCE-001, the whole-live-ledger generation
    # that stops the next kill erasing the last kill's drops (RE-130) and
    # stops the dispatch taking every key it just announced.  Listed in the
    # same commit as the module -- three rounds have now recorded that this
    # tuple is what makes a new module part of the sweep at all.
    "mob_drop_presence.py",
    "mob_loot.py",
    "mob_pickup.py",
    # ROUND uq2lxw: the pickup path's write half, joined to store.py's
    # STORE-INSERT-001.  Listed here the moment it was added, because this
    # tuple is the lane's own second record of what it owns and a module
    # missing from it is a module the fabrication sweep never reads.
    "mob_pickup_persist.py",
    # ROUND y9s0xo: the mid-session recompose census, scene by scene -- the
    # composer that keeps a hit or a kill in Bg0002 from shipping the
    # one-entry frame RE-092 proved erases every other actor.  Listed in the
    # same commit as the module, for the reason the two entries above already
    # record: a module missing from this tuple is a module the fabrication
    # sweep never reads.
    "mob_scene_recompose.py",
)

# The exact identifiers RE-122's own BUILD_IMPACT line names, plus the exact
# placeholder name R208 (pirate-force-server, player_wire.py / chief round)
# caught and reverted before it shipped. Every one of these belongs to the
# PLAYER stat/MP question, never to a monster's HP/level/drop table -- if any
# of them appears in a module this lane owns, that is the fabrication RE-122
# forbids, imported into the wrong domain.
FORBIDDEN_IDENTIFIERS = (
    "CHARCREATE_CLASS",
    "s_SCORE",
    "STANDARD_BUFF",
    "MP_PLACEHOLDER",
)


class MobStatFabricationGuardTests(unittest.TestCase):
    def test_every_lane_b_module_is_accounted_for_on_disk(self) -> None:
        # If this drifts, the sweep below is silently checking a stale list
        # -- the hand-picked LANE_B_MODULES tuple must equal every mob_*/
        # field_mob_*/field_drop_tables.py/loot_roll.py file that actually
        # exists today, in either direction.
        on_disk = {
            path.name
            for path in SRC.iterdir()
            if path.is_file()
            and (
                path.name.startswith(("mob_", "field_mob", "field_drop"))
                or path.name == "loot_roll.py"
            )
        }
        self.assertEqual(on_disk, set(LANE_B_MODULES))

    def test_no_lane_b_module_names_a_player_stat_fabrication_identifier(
        self,
    ) -> None:
        offenders: dict[str, list[str]] = {}
        for name in LANE_B_MODULES:
            text = (SRC / name).read_text(encoding="ascii")
            hits = [ident for ident in FORBIDDEN_IDENTIFIERS if ident in text]
            if hits:
                offenders[name] = hits
        self.assertEqual(
            offenders, {},
            "RE-122 forbids fabricating player MP/stat values; a combat "
            "module referencing %r is exactly that, imported into the "
            "wrong domain (see this file's own module docstring)"
            % (FORBIDDEN_IDENTIFIERS,),
        )

    def test_monster_hp_is_documented_as_coming_from_standard_mob_not_a_player_table(
        self,
    ) -> None:
        # Cheap, direct check that the ONE derived-HP module actually cites
        # the monster table RE-122 leaves untouched, rather than merely
        # trusting the sweep above by omission.
        text = (SRC / "field_mob_tables.py").read_text(encoding="ascii")
        self.assertIn("STANDARD_MOB", text)
        self.assertIn("n_HPMAX", text)


if __name__ == "__main__":
    unittest.main()
