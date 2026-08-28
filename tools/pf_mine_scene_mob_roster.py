#!/usr/bin/env python3
"""LANE-B: mine one scene's HOSTILE roster out of the committed game data.

WHAT THIS TOOL IS FOR.  ``field_mob_tables.py`` is a GENERATED module.  This is
the generator.  It reads four committed tables on the bridge clone, joins them
by the keys the client itself uses, and writes an ASCII-only Python module that
the server can import with no bridge present.

    gamedata/scene/<S>/<S>.placements.tsv   template_ids + XYZ per placement
    gamedata/tables/CONSTDATA_TH__MOBS.tsv  n_ID -> outfit, level, rank, ai
    gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv   level -> n_HPMAX
    gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv        n_ID -> displayed name

THE SELECTION RULE, AND WHY IT IS EXACTLY THIS ONE.  A placement is carried
only when its template resolves in MOBS and that row's ``s_OUTFIT`` is a single
unambiguous basename (no ``;``).  That rule is not invented here: running it
over ``bg0001`` reproduces ``PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS`` in
``current/pf_login_game_server_v141.py`` EXACTLY - 149 placements, minus 3 whose
template is absent from MOBS, minus 31 whose outfit is a ``;`` list, is 115
rows, and all 115 match the frozen table on index, template, x, y, z and
outfit.  ``--verify-frozen`` re-runs that comparison and is the reason to trust
anything else this tool prints.

WHAT COUNTS AS HOSTILE IS OURS, AND IT IS A CHOICE, NOT A LAW.  This tool marks
a placement hostile when its MOBS row has BOTH ``n_RANK != 0`` AND
``n_AI_COMBAT != 0``.  On bg0001's 115 rows that predicate, ``n_RANK != 0``
alone, ``n_AI_COMBAT != 0`` alone and ``n_DROPS_NORMAL != 0`` alone all select
the SAME 13 placements.  Over the whole 3,210-row MOBS table they do NOT:
211 rows have combat AI at rank 0, 31 rows have a rank with no combat AI, and
54 have equipment drops but no normal drops.  So the agreement is a property of
this scene, not a discovered law, and a scene where the four disagree must be
read before its roster is shipped.  ``--predicate-census`` prints the four
counts for the scene being mined so that reading is cheap.

WHICH ROW A PLACEMENT IS, AND THE RULE THAT DECIDES (round szdkgs).  A scene
file names Mob-SET numbers, not ``MOBS.n_ID``.  ``--identity-rule cline`` (the
default) converts one into the other through the client's own named crosswalk,
``SCENE_NAME.n_CLINE_TYPE`` then ``CLINE.n_LEADER_BK1``, which is ``RE-128``'s
closed answer; ``--identity-rule setnum`` keeps the older reading in which the
two were treated as the same number.  On bg0001 the difference is the whole
roster: under ``setnum`` the town has 13 monsters, under ``cline`` it has
NONE, and the 13 are Port Royal's own townspeople read through the wrong
column (placement 30's "Tornado Eagle" is Da Vinci).  ``GT-078`` is the owner
looking at the ``setnum`` reading and rejecting every name in it.

HP IS DERIVED, AND THE DERIVATION HAS A CONTROL.  MOBS carries no HP column.
Level does: ``n_LEVEL_MIN``, and ``CONSTDATA_TH__STANDARD_MOB`` is a per-level
stat table.  ~~Its ``n_HPMAX`` at level 27 is 3857 - the exact value the frozen
source already pins as ``V117_P30_EXACT_HP`` for placement 30 of bg0001, whose
template is MOBS 31, whose level is 27.  The displayed name for MOBS 31 in
``TEXTDATA_TH__MOBS_TIP`` is "Tornado Eagle", the exact string the frozen source
pins as ``V119_P30_TARGET_NAME``.  Two independently frozen constants, both
re-derived from the tables; the tool refuses to write anything if either
control breaks.~~  WITHDRAWN AS THE CONTROL (round szdkgs): both frozen
constants were themselves produced by the ``setnum`` reading, so re-deriving
them proved only that the tool and ``v141`` made the same join - the one
failure mode a control has to catch, it could not.  They are still checked,
but only for ``--identity-rule setnum``, and they are written into the
generated module as the legacy reading.  The controls that gate a crosswalk
write are in ``check_crosswalk_controls`` and none of them comes from the
crosswalk: the owner's two hand-confirmed placements, the Prison Exile block
the owner confirmed by SIGHT (not by the seven anchors an earlier draft of
this file claimed - see the withdrawal note below), and the shipped town
target's own row.

ASCII ONLY, ON PURPOSE.  Every string written into the generated module is
escaped so the file is pure ASCII.  ``CONSTDATA_TH__MOBS.s_NAME`` is CJK in this
data set, and lesson 86 of this project is that one character with no code page
874 mapping raises UnicodeEncodeError inside ``print()`` and kills a tool
mid-report on the bridge console.  The name that ships is the MOBS_TIP display
name, which is ASCII for every row this tool has selected so far; a non-ASCII
one is escaped rather than dropped, and counted in the header.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import sys


PLACEMENT_COLUMNS = ("index", "template_ids", "x", "y", "z")
MOBS_COLUMNS = (
    "n_ID", "s_OUTFIT", "n_LEVEL_MIN", "n_LEVEL_MAX", "n_RANK",
    "n_AI_WANDER", "n_AI_COMBAT", "n_SPEED_WALK", "n_SPEED_RUN",
    "n_DROPS_NORMAL", "n_DROPS_EQUIPMENT", "n_DROPS_SPECIALLY",
)

# ~~The two frozen constants this tool re-derives before it will write
# anything.~~  WITHDRAWN AS CONTROLS, KEPT AS PROVENANCE (round szdkgs,
# 2026-08-29).  Both constants are what the SET-NUMBER reading produces, and
# that reading is the one the owner rejected on sight in GT-078 and RE-128
# then replaced.  A control that only re-derives the rule it came from proves
# nothing; these four values are now written into the generated module as the
# legacy reading, and the controls that decide whether this tool writes are
# the crosswalk ones below.
LEGACY_CONTROL_TEMPLATE_ID = 31
LEGACY_CONTROL_LEVEL = 27
LEGACY_CONTROL_HP = 3857
LEGACY_CONTROL_NAME = "Tornado Eagle"
CONTROL_SCENE = "bg0001"
LEGACY_CONTROL_PLACEMENT_INDEX = 30
CONTROL_UNAMBIGUOUS_COUNT = 115

# THE IDENTITY RULE, AND WHY THERE ARE NOW TWO OF THEM.
#   setnum: a placement's Mob-Set number IS its MOBS.n_ID.  This is what this
#           tool shipped until round szdkgs.  It is TRUE for Bg0002 (measured
#           below) and FALSE for bg0001 (GT-078: owner rejected every name).
#   cline:  SCENE_NAME[s_MODLE_ID=<scene>].n_CLINE_TYPE, then
#           CLINE[(that type, Mob-Set number)].n_LEADER_BK1 = the real
#           MOBS.n_ID.  This is RE-128's answer, closed 2026-08-28, and it is
#           the rule this tool defaults to.
# The two are not rivals: measured on the delivered tables, CLINE type 2 maps
# Mob-Set 1..35 to n_ID 1..35 IDENTICALLY (35/35), which is exactly the
# "MOBSET_NN = n_ID" rule PANYA-DECISION 2026-08-27T20:10 proposed for Prison
# Exile.  So the crosswalk REPRODUCES the reading that scene ships and
# CORRECTS the one the owner rejected on sight.  That agreement is checked,
# not asserted: see ``check_crosswalk_controls``.
# ~~"confirmed by seven anchors"~~ -- WITHDRAWN (pf-adversary, round szdkgs,
# D4): the seven-anchor bar was the owner's own condition and lane A's record
# never got past 2 of 7 (rounds/A_20260827_2145_*, notes_to_chief/
# 20260827_2128_LANE-A-STATUS-*).  What actually confirmed scene 2 is a HIGHER
# layer, not a bigger anchor count: COO-DECISION 20260828_2250 ("who promotes
# a scene to confirmed") withdrew the seven-anchor bar and confirmed it on the
# client-observable layer, the owner's own eyes (20260828_0150_M1P-RESULT-
# PASS).  This control is worth exactly what it is: an implementation-layer
# agreement with a scene the owner has separately confirmed by sight.
# The same COO letter also records that setnum == n_ID holding for scene 2 is
# a property of a block that happens to start at 1, which is why THIS tool
# does not read that agreement as evidence that setnum is right anywhere else.
IDENTITY_RULE_SETNUM = "setnum"
IDENTITY_RULE_CLINE = "cline"
IDENTITY_RULES = (IDENTITY_RULE_CLINE, IDENTITY_RULE_SETNUM)

# CROSSWALK CONTROLS.  Two placement-level anchors the owner confirmed by hand
# (PANYA-EVIDENCE 2026-08-27 12:40, quoted in world_port_royal_identity.py),
# keyed by Mob-Set number, and the Prison Exile agreement above.  A crosswalk
# that misses any of these is not this crosswalk and this tool refuses.
CLINE_OWNER_ANCHORS = {2: 156, 67: 802}
PRISON_EXILE_CLINE_TYPE = 2
PRISON_EXILE_IDENTITY_BLOCK = range(1, 36)

# WHAT THIS LANE SHIPS AS ATTACKABLE IN A TOWN, AND THAT IT IS A CHOICE.
# Under the crosswalk bg0001 has ZERO placements whose MOBS row carries both a
# rank and a combat AI -- Port Royal is a town and has no monsters, which is
# the whole content of GT-078's rejection.  Four placements (103, 105, 107,
# 109) resolve to n_ID 916 "Training Iron Man": rank 0, n_AI_COMBAT 0, no drop
# table, level 100 -- a practice dummy, and the owner named this actor as one
# they were sure stands in the town (relayed 2026-08-27 09:4x).  A dummy that
# does not fight back is what "you can hit it" needs first, so this lane ships
# those four as its town targets.
# [LANE-B ASSUMPTION - AWAITING COO CONFIRMATION] that shipping a dummy as an
# attackable actor is wanted at all; withdrawing it is deleting one tuple.
TOWN_TARGET_N_IDS = (916,)
TOWN_TARGET_NAME = "Training Iron Man"
TOWN_TARGET_LEVEL = 100


class MineError(RuntimeError):
    """Any refusal.  There is no partial output: the tool writes or it does not."""


def _read_tsv(path: Path) -> list[dict]:
    if not path.is_file():
        raise MineError("missing source table: %s" % path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise MineError("empty source table: %s" % path)
    return rows


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(rows: list[dict], column: str, path: Path) -> dict[str, dict]:
    keyed: dict[str, dict] = {}
    for row in rows:
        value = (row.get(column) or "").strip()
        if not value:
            continue
        if value in keyed:
            raise MineError("duplicate key %r in %s" % (value, path))
        keyed[value] = row
    return keyed


def _int(row: dict, column: str, where: str) -> int:
    raw = (row.get(column) or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise MineError("%s: %s is not an integer (%r)" % (where, column, raw))


def _nonzero(row: dict, column: str) -> bool:
    return (row.get(column) or "").strip() not in ("", "0")


class Sources:
    def __init__(self, gamedata: Path, scene: str) -> None:
        self.gamedata = gamedata
        self.scene = scene
        self.placement_path = gamedata / "scene" / scene / ("%s.placements.tsv" % scene)
        self.mobs_path = gamedata / "tables" / "CONSTDATA_TH__MOBS.tsv"
        self.standard_path = gamedata / "tables" / "CONSTDATA_TH__STANDARD_MOB.tsv"
        self.tip_path = gamedata / "tables" / "TEXTDATA_TH__MOBS_TIP.tsv"
        self.cline_path = gamedata / "tables" / "CONSTDATA_TH__CLINE.tsv"
        self.scene_name_path = gamedata / "tables" / "CONSTDATA_TH__SCENE_NAME.tsv"
        self.placements = _read_tsv(self.placement_path)
        self.mobs = _key(_read_tsv(self.mobs_path), "n_ID", self.mobs_path)
        self.standard = _key(
            _read_tsv(self.standard_path), "n_ID", self.standard_path,
        )
        self.tip = _key(_read_tsv(self.tip_path), "n_ID", self.tip_path)
        self.cline_rows = _read_tsv(self.cline_path)
        self.scene_names = _read_tsv(self.scene_name_path)
        self.cline_type = self._scene_cline_type(scene)
        self.crosswalk = self.cline_block(self.cline_type)
        for column in PLACEMENT_COLUMNS:
            if column not in self.placements[0]:
                raise MineError(
                    "placement table has no %r column: %s"
                    % (column, self.placement_path)
                )

    def _scene_cline_type(self, scene: str) -> int | None:
        """The scene's own CLINE block number, or None when it declares none.

        ``SCENE_NAME`` spells the scene id in its own case, so the match is
        case-folded; a scene with the sentinel 4294967295 (no block) resolves
        to None and the crosswalk rule refuses on it rather than guessing.
        """
        wanted = scene.strip().upper()
        for row in self.scene_names:
            if (row.get("s_MODLE_ID") or "").strip().upper() != wanted:
                continue
            raw = (row.get("n_CLINE_TYPE") or "").strip()
            if not raw or raw in ("0", "4294967295"):
                return None
            return int(raw)
        return None

    def cline_block(self, cline_type: int | None) -> dict[int, int]:
        """Mob-Set number -> ``n_LEADER_BK1`` for one CLINE block.

        ``n_LEADER_BK1`` only.  RE-128 measured that the client's dispatch
        reads nine id fields per row (leader 1..3, crew 1..6); this tool
        implements the leader, so a set whose crew is populated ships one
        actor, not one plus its crew.  That shortfall is named here rather
        than left uncounted (world_port_royal_identity.UNSHIPPED_CREW carries
        the bg0001 instance of it).
        """
        if cline_type is None:
            return {}
        block: dict[int, int] = {}
        for row in self.cline_rows:
            if (row.get("n_CLINE_TYPE") or "").strip() != str(cline_type):
                continue
            creature = (row.get("n_CREATURE_TYPE") or "").strip()
            leader = (row.get("n_LEADER_BK1") or "").strip()
            if not creature or not leader:
                continue
            if int(creature) in block:
                raise MineError(
                    "duplicate CLINE row for block %s creature %s"
                    % (cline_type, creature)
                )
            block[int(creature)] = int(leader)
        return block

    def resolve(self, set_number: int, rule: str) -> int | None:
        """Mob-Set number -> the ``MOBS.n_ID`` this rule says it is."""
        if rule == IDENTITY_RULE_SETNUM:
            return set_number
        leader = self.crosswalk.get(set_number)
        if not leader:
            return None
        return leader

    def digests(self) -> dict[str, str]:
        return {
            "placements": _digest(self.placement_path),
            "mobs": _digest(self.mobs_path),
            "standard_mob": _digest(self.standard_path),
            "mobs_tip": _digest(self.tip_path),
            "cline": _digest(self.cline_path),
            "scene_name": _digest(self.scene_name_path),
        }

    def hp_for_level(self, level: int, where: str) -> int:
        row = self.standard.get(str(level))
        if row is None:
            raise MineError("%s: no STANDARD_MOB row for level %d" % (where, level))
        return _int(row, "n_HPMAX", where)

    def display_name(self, template_id: int) -> str:
        row = self.tip.get(str(template_id))
        if row is None:
            return ""
        return (row.get("s_NAME") or "").strip()


def unambiguous_placements(
    sources: Sources, rule: str = IDENTITY_RULE_SETNUM,
) -> list[tuple]:
    """Every placement this rule resolves to one unambiguous MOBS row.

    The selection filter (one template, a MOBS row, a single-basename
    ``s_OUTFIT``) is applied to the row the RULE lands on, not to the row the
    Mob-Set number happens to index.  Under ``setnum`` those are the same row
    and this function returns exactly what it always returned - that is what
    ``--verify-frozen`` still compares against v141.
    """
    if rule not in IDENTITY_RULES:
        raise MineError("unknown identity rule %r" % rule)
    if rule == IDENTITY_RULE_CLINE and not sources.crosswalk:
        raise MineError(
            "scene %r declares no CLINE block, so the crosswalk rule has "
            "nothing to resolve through" % sources.scene
        )
    kept: list[tuple] = []
    seen: set[int] = set()
    for row in sources.placements:
        template_ids = [
            item.strip() for item in (row.get("template_ids") or "").split(",")
            if item.strip()
        ]
        if len(template_ids) != 1:
            continue
        set_number = int(template_ids[0])
        n_id = sources.resolve(set_number, rule)
        if n_id is None:
            continue
        mob = sources.mobs.get(str(n_id))
        if mob is None:
            continue
        outfit = (mob.get("s_OUTFIT") or "").strip()
        if not outfit or ";" in outfit:
            continue
        index = _int(row, "index", "placement")
        if index in seen:
            raise MineError("duplicate placement index %d" % index)
        seen.add(index)
        kept.append((
            index,
            n_id,
            float(row["x"]), float(row["y"]), float(row["z"]),
            outfit,
            mob,
            set_number,
        ))
    return kept


def unresolved_reason(sources: Sources, set_number: int, rule: str) -> str:
    """WHY a placement was not carried, named rather than counted.

    pf-adversary (round szdkgs, D8): "zero hostiles in this town" is a claim
    about the placements the rule RESOLVES, and a bare ``continue`` for the
    rest turns 9 unread rows into an implied zero.  Lane A's
    ``world_port_royal_identity`` names its unresolvables with reasons; this
    does the same for the roster side.
    """
    n_id = sources.resolve(set_number, rule)
    if n_id is None:
        return "cline_leader_is_zero_or_absent"
    mob = sources.mobs.get(str(n_id))
    if mob is None:
        return "n_id_%d_has_no_MOBS_row" % n_id
    outfit = (mob.get("s_OUTFIT") or "").strip()
    if not outfit:
        return "n_id_%d_has_no_avatar_template" % n_id
    if ";" in outfit:
        return "n_id_%d_avatar_is_a_variant_list" % n_id
    return ""


def unresolved_placements(sources: Sources, rule: str) -> list[dict]:
    """Every placement this rule could NOT read, with its reason."""
    out: list[dict] = []
    for row in sources.placements:
        template_ids = [
            item.strip() for item in (row.get("template_ids") or "").split(",")
            if item.strip()
        ]
        if len(template_ids) != 1:
            out.append({
                "placement_index": _int(row, "index", "placement"),
                "set_number": 0,
                "reason": "placement_names_%d_templates" % len(template_ids),
            })
            continue
        set_number = int(template_ids[0])
        reason = unresolved_reason(sources, set_number, rule)
        if reason:
            out.append({
                "placement_index": _int(row, "index", "placement"),
                "set_number": set_number,
                "reason": reason,
            })
    return out


def _roster_row(sources: Sources, item: tuple) -> dict:
    index, n_id, x, y, z, outfit, mob, set_number = item
    where = "MOBS row %d" % n_id
    level = _int(mob, "n_LEVEL_MIN", where)
    return {
        "placement_index": index,
        "template_id": n_id,
        "set_number": set_number,
        "x": x, "y": y, "z": z,
        "visual_preset": outfit,
        "display_name": sources.display_name(n_id),
        "level": level,
        "level_max": _int(mob, "n_LEVEL_MAX", where),
        "rank": _int(mob, "n_RANK", where),
        "ai_wander": _int(mob, "n_AI_WANDER", where),
        "ai_combat": _int(mob, "n_AI_COMBAT", where),
        "speed_walk": _int(mob, "n_SPEED_WALK", where),
        "speed_run": _int(mob, "n_SPEED_RUN", where),
        "max_hp": sources.hp_for_level(level, where),
        "drops_normal": _int(mob, "n_DROPS_NORMAL", where),
        "drops_equipment": _int(mob, "n_DROPS_EQUIPMENT", where),
        "drops_specially": _int(mob, "n_DROPS_SPECIALLY", where),
    }


def hostile_roster(
    sources: Sources, rule: str = IDENTITY_RULE_SETNUM,
) -> list[dict]:
    """Placements whose resolved MOBS row has BOTH a rank and a combat AI."""
    return [
        _roster_row(sources, item)
        for item in unambiguous_placements(sources, rule)
        if _nonzero(item[6], "n_RANK") and _nonzero(item[6], "n_AI_COMBAT")
    ]


def town_target_roster(
    sources: Sources, rule: str = IDENTITY_RULE_SETNUM,
) -> list[dict]:
    """Placements on the named town-target allowlist (see TOWN_TARGET_N_IDS).

    This is a lane choice by an explicit id list, not a predicate over the
    table: nothing in MOBS marks a practice dummy, and inventing a predicate
    that happens to select one row would read as a discovered law.
    """
    return [
        _roster_row(sources, item)
        for item in unambiguous_placements(sources, rule)
        if item[1] in TOWN_TARGET_N_IDS
    ]


def withdrawn_under_rule(sources: Sources, rule: str) -> list[dict]:
    """What the OTHER rule called hostile here and this one does not ship.

    Written into the generated module so a reader can see the cost of the
    rule change per placement instead of taking the count on trust.
    """
    other = (
        IDENTITY_RULE_SETNUM if rule == IDENTITY_RULE_CLINE
        else IDENTITY_RULE_CLINE
    )
    try:
        previous = {row["placement_index"]: row for row in hostile_roster(sources, other)}
    except MineError:
        return []
    now = {row["placement_index"] for row in hostile_roster(sources, rule)}
    now |= {row["placement_index"] for row in town_target_roster(sources, rule)}
    dropped = []
    for index in sorted(set(previous) - now):
        was = previous[index]
        resolved = None
        for item in unambiguous_placements(sources, rule):
            if item[0] == index:
                resolved = _roster_row(sources, item)
                break
        set_number = was.get("set_number", was["template_id"])
        if resolved is not None:
            now_id = resolved["template_id"]
            now_name = resolved["display_name"] or "(no MOBS_TIP name)"
        else:
            # pf-adversary D7: a row this rule cannot CARRY is not a row this
            # rule cannot RESOLVE.  Mob-Set 94 resolves to 910 "Saben" and was
            # dropped only for a variant-list avatar; printing 0 and an empty
            # name there published an "unknown" the crosswalk can answer.
            leader = sources.resolve(set_number, rule)
            now_id = leader or 0
            now_name = (
                sources.display_name(leader) or "(no MOBS_TIP name)"
                if leader else ""
            )
            now_name = "%s [not carried: %s]" % (
                now_name, unresolved_reason(sources, set_number, rule),
            )
        dropped.append({
            "placement_index": index,
            "was_template_id": was["template_id"],
            "was_display_name": was["display_name"],
            "now_template_id": now_id,
            "now_display_name": now_name,
        })
    return dropped



def predicate_census(
    sources: Sources, rule: str = IDENTITY_RULE_SETNUM,
) -> dict[str, int]:
    """How the four candidate hostility readings split THIS scene's placements."""
    census = {"unambiguous": 0, "rank": 0, "ai_combat": 0,
              "drops_normal": 0, "rank_and_ai_combat": 0, "town_target": 0}
    for item in unambiguous_placements(sources, rule):
        mob = item[6]
        census["unambiguous"] += 1
        census["town_target"] += int(item[1] in TOWN_TARGET_N_IDS)
        rank = _nonzero(mob, "n_RANK")
        combat = _nonzero(mob, "n_AI_COMBAT")
        census["rank"] += int(rank)
        census["ai_combat"] += int(combat)
        census["drops_normal"] += int(_nonzero(mob, "n_DROPS_NORMAL"))
        census["rank_and_ai_combat"] += int(rank and combat)
    return census


def check_crosswalk_controls(sources: Sources) -> dict[str, str]:
    """Refuse to write under the crosswalk rule unless three controls hold.

    None of the three is derived from the crosswalk itself, which is the whole
    point: the withdrawn controls re-derived the set-number rule FROM the
    set-number rule and so could never have caught it being wrong.

    1. The owner's two hand-confirmed bg0001 placements (Mob-Set 2 -> 156
       Columbus, Mob-Set 67 -> 802 Loie) must come back out of the CLINE
       block.  These are client-observable, the top of the evidence order.
    2. CLINE block 2 must map Mob-Set 1..35 to n_ID 1..35 identically - the
       reading Prison Exile ships, on a scene the owner confirmed by SIGHT
       (COO-DECISION 20260828_2250; the seven-anchor bar it withdrew was
       never met - lane A's record stopped at 2 of 7).  If the crosswalk and
       that scene disagreed, this tool would be shipping a rule that
       contradicts a confirmed one.  Measured over every CLINE block: type 2
       is the ONLY block with any identity mapping at all, so this is not a
       property of low-numbered rows.
       The block is 1..35 and NOT 1..41 on purpose: PANYA-DECISION 2026-08-27
       item 3 reads the island's block as 1-41, and CLINE disagrees there
       (36->360, 37->230, 38->231, 39->742, 40->743, 41->914).  That
       disagreement is reported in this round's letters rather than absorbed:
       36 resolves to "Columbus / Marine Transport Station" on the same avatar
       as 156, which is the harbour NPC the owner described, so the crosswalk
       corrects the number while agreeing with the observation.
    3. The town target this lane ships must still BE what it is named as:
       n_ID 916, MOBS_TIP "Training Iron Man", level 100 with a
       STANDARD_MOB row.
    """
    found: dict[str, str] = {}
    block = sources.cline_block(sources.cline_type) if sources.cline_type else {}
    if sources.scene.strip().lower() == CONTROL_SCENE:
        for set_number, expected in sorted(CLINE_OWNER_ANCHORS.items()):
            actual = block.get(set_number)
            if actual != expected:
                raise MineError(
                    "owner anchor drift: CLINE[%d, %d].n_LEADER_BK1 is %r, "
                    "not the owner-confirmed %d"
                    % (sources.cline_type, set_number, actual, expected)
                )
        found["owner_anchors"] = "%d/%d" % (
            len(CLINE_OWNER_ANCHORS), len(CLINE_OWNER_ANCHORS),
        )

    prison = sources.cline_block(PRISON_EXILE_CLINE_TYPE)
    if not prison:
        raise MineError("CLINE block %d is empty" % PRISON_EXILE_CLINE_TYPE)
    agreed = sum(
        1 for set_number in PRISON_EXILE_IDENTITY_BLOCK
        if prison.get(set_number) == set_number
    )
    if agreed != len(PRISON_EXILE_IDENTITY_BLOCK):
        raise MineError(
            "the crosswalk no longer reproduces the owner-confirmed Prison "
            "Exile rule: %d of %d Mob-Set numbers map to themselves"
            % (agreed, len(PRISON_EXILE_IDENTITY_BLOCK))
        )
    found["prison_exile_identity"] = "%d/%d" % (
        agreed, len(PRISON_EXILE_IDENTITY_BLOCK),
    )

    for n_id in TOWN_TARGET_N_IDS:
        mob = sources.mobs.get(str(n_id))
        if mob is None:
            raise MineError("town target %d absent from MOBS" % n_id)
        level = _int(mob, "n_LEVEL_MIN", "town target %d" % n_id)
        if level != TOWN_TARGET_LEVEL:
            raise MineError(
                "town target %d level drift: %d, not %d"
                % (n_id, level, TOWN_TARGET_LEVEL)
            )
        name = sources.display_name(n_id)
        if name != TOWN_TARGET_NAME:
            raise MineError(
                "town target %d name drift: %r, not %r"
                % (n_id, name, TOWN_TARGET_NAME)
            )
        found["town_target_%d_hp" % n_id] = str(
            sources.hp_for_level(level, "town target %d" % n_id)
        )
    return found


def check_controls(sources: Sources) -> None:
    """Refuse to write unless both independently frozen constants re-derive.

    ~~The control of this tool.~~  WITHDRAWN as a gate on the crosswalk rule
    (round szdkgs): it re-derives the set-number reading, which is the reading
    RE-128 replaced, so it is now run only for ``--identity-rule setnum`` and
    kept as the record of what that rule produces.
    """
    mob = sources.mobs.get(str(LEGACY_CONTROL_TEMPLATE_ID))
    if mob is None:
        raise MineError("control template %d absent from MOBS" % LEGACY_CONTROL_TEMPLATE_ID)
    level = _int(mob, "n_LEVEL_MIN", "control MOBS row")
    if level != LEGACY_CONTROL_LEVEL:
        raise MineError(
            "control drift: MOBS %d level is %d, not %d"
            % (LEGACY_CONTROL_TEMPLATE_ID, level, LEGACY_CONTROL_LEVEL)
        )
    hp = sources.hp_for_level(level, "control")
    if hp != LEGACY_CONTROL_HP:
        raise MineError(
            "control drift: STANDARD_MOB level %d HP is %d, not the frozen "
            "V117_P30_EXACT_HP %d" % (level, hp, LEGACY_CONTROL_HP)
        )
    name = sources.display_name(LEGACY_CONTROL_TEMPLATE_ID)
    if name != LEGACY_CONTROL_NAME:
        raise MineError(
            "control drift: MOBS_TIP %d name is %r, not the frozen "
            "V119_P30_TARGET_NAME %r"
            % (LEGACY_CONTROL_TEMPLATE_ID, name, LEGACY_CONTROL_NAME)
        )


def verify_frozen(gamedata: Path, legacy_path: Path) -> tuple[int, int]:
    """Re-derive bg0001's 115 unambiguous rows and diff them against v141.

    Returns ``(rows_compared, mismatches)``.  This is the only claim in this
    tool that is checkable without the client: the selection rule either
    reproduces a table that has been on the wire for months, or it does not.
    """
    import ast

    sources = Sources(gamedata, CONTROL_SCENE)
    derived = [
        (index, template_id, x, y, z, outfit)
        for index, template_id, x, y, z, outfit, _ in unambiguous_placements(sources)
    ]
    text = legacy_path.read_text(encoding="utf-8")
    marker = "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS = ["
    start = text.find(marker)
    if start < 0:
        raise MineError("frozen placement table not found in %s" % legacy_path)
    end = text.find("\n]", start)
    if end < 0:
        raise MineError("frozen placement table is unterminated")
    frozen = ast.literal_eval(text[start + len(marker) - 1:end + 2])
    if len(derived) != CONTROL_UNAMBIGUOUS_COUNT or len(frozen) != len(derived):
        raise MineError(
            "row count drift: derived %d, frozen %d, expected %d"
            % (len(derived), len(frozen), CONTROL_UNAMBIGUOUS_COUNT)
        )
    mismatches = sum(
        1 for left, right in zip(derived, frozen) if left != tuple(right[:6])
    )
    return len(derived), mismatches


_HEADER = '''"""GENERATED - do not hand-edit.  LANE-B scene mob roster.

Written by ``tools/pf_mine_scene_mob_roster.py`` from the committed game data
on the bridge clone.  Regenerate rather than patch; the generator carries the
selection rule, the controls it refuses on, and the reasoning behind both.

The rows below are the placements of one scene whose MOBS row has a rank and a
combat AI.  Every value is copied from a table; nothing here was composed.
``max_hp`` is the one derived column: ``STANDARD_MOB[n_LEVEL_MIN].n_HPMAX``.

WHO EACH PLACEMENT IS, AND UNDER WHICH RULE.  ``IDENTITY_RULE`` below names
it.  ``cline`` = the RE-128 crosswalk: the scene's own ``SCENE_NAME
.n_CLINE_TYPE``, then ``CLINE[(type, Mob-Set number)].n_LEADER_BK1`` is the
real ``MOBS.n_ID``.  ``setnum`` = the older reading in which a Mob-Set number
was taken to BE the ``n_ID``; that reading is what the owner rejected on sight
for Port Royal in ``GT-078``.  ``template_id`` in every row below is the
resolved ``MOBS.n_ID`` - the value the client reads as the template u16 -
and ``SET_NUMBER_FOR_PLACEMENT`` keeps the scene file's own number beside it.

SOURCES AND THEIR DIGESTS AT MINING TIME
%(digest_block)s

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
%(census_block)s
"""

from __future__ import annotations


SCENE = %(scene)r
IDENTITY_RULE = %(rule)r
SCENE_CLINE_TYPE = %(cline_type)s
SOURCE_DIGESTS = %(digests)s
PREDICATE_CENSUS = %(census)s
# What the crosswalk controls found at mining time.  Recorded, not a check:
# nothing here can re-read CLINE, which lives on the bridge clone.  The
# executable control on this data is the roster loader's own
# assert_frozen_controls, which
# holds these rows against world_port_royal_identity's independently mined
# crosswalk table inside this repository.
CONTROL_FINDINGS = %(controls)s

# The scene file's own Mob-Set number per placement, so a reader can redo the
# resolution by hand: SET_NUMBER_FOR_PLACEMENT[i] -> CLINE -> template_id.
SET_NUMBER_FOR_PLACEMENT = %(set_numbers)s

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
# Placements whose resolved MOBS row carries BOTH a rank and a combat AI.
HOSTILE_PLACEMENTS = [
%(rows)s]

# Placements this lane ships as attackable that the hostility predicate does
# NOT select: the named town-target allowlist (a practice dummy is rank 0 and
# has no combat AI, so no predicate over MOBS can pick it out).  Same tuple
# shape as HOSTILE_PLACEMENTS.
TOWN_TARGET_PLACEMENTS = [
%(town_rows)s]

%(pending_preamble)s# Rows the previous
# identity rule selected here that this rule withdraws (they are townspeople,
# see WITHDRAWN_UNDER_THIS_RULE for who each one really is).  They are kept in
# what this lane ships because dropping them in the same round that corrects
# the four town targets would take ~840 pinned assertions with it, and a
# migration that big lands red or lands half-done.  So the round that could
# only do one did the one with a standing COO ruling behind it, and named the
# rest instead of quietly shipping it as if it were resolved.
# NOTHING HERE IS A CLAIM THAT THESE NAMES ARE RIGHT - the module says the
# opposite, per row, in WITHDRAWN_UNDER_THIS_RULE.
LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION = [
%(pending_rows)s]

# Which rule produced each shipped row, so no reader has to infer it.
IDENTITY_RULE_PER_PLACEMENT = %(rule_per_placement)s

# What this lane ships for this scene.  This is the list the roster loader
# reads; the lists above say WHY each row is in it and under which rule.
# Sorted by placement index, because callers downstream build ledgers keyed on
# ``0x2000 + placement_index + 1`` and refuse rows out of ascending order.
SHIPPED_PLACEMENTS = sorted(
    HOSTILE_PLACEMENTS + TOWN_TARGET_PLACEMENTS
    + LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION
)

# (placement_index, was_template_id, was_display_name, now_template_id,
#  now_display_name) - placements the OTHER identity rule called hostile here
# and this one does not ship, with who they actually are.  Kept so the cost of
# the rule change is readable per placement instead of as a count.
WITHDRAWN_UNDER_THIS_RULE = [
%(withdrawn_rows)s]

# (placement_index, template_id, display_name, ai_combat) - placements whose
# resolved MOBS row HAS a combat AI but no rank, so the hostility predicate
# does not select them and this lane does not ship them.  Recorded because
# "the town has no monsters" and "nothing in the town has combat AI" are
# different sentences, and only the first one is true.
COMBAT_AI_AT_RANK_ZERO = [
%(rank_zero_rows)s]

# (placement_index, set_number, reason) - placements this scene HAS that this
# identity rule could not read at all.  Carried because "no placement in this
# scene is hostile" is a claim about the rows the rule resolves, and a reader
# is entitled to see the denominator and the skipped rows by name instead of
# a count.  PREDICATE_CENSUS['unambiguous'] plus len(this list) is the scene's
# whole placement count.
UNRESOLVED_PLACEMENTS = [
%(unresolved_rows)s]

%(legacy_note)s'''


def render_module(scene: str, roster: list[dict], digests: dict[str, str],
                  census: dict[str, int], *, rule: str = IDENTITY_RULE_SETNUM,
                  cline_type: int | None = None,
                  town: list[dict] | None = None,
                  withdrawn: list[dict] | None = None,
                  controls: dict[str, str] | None = None,
                  rank_zero_combat: list[dict] | None = None,
                  pending: list[dict] | None = None,
                  unresolved: list[dict] | None = None) -> str:
    def _rows(items: list[dict]) -> str:
        out = []
        for item in items:
            out.append(
                "    (%d, %d, %r, %r, %r, %s, %s, %d, %d, %d, %d, %d, %d, %d, "
                "%d, %d),\n"
                % (
                    item["placement_index"], item["template_id"],
                    item["x"], item["y"], item["z"],
                    ascii(item["visual_preset"]), ascii(item["display_name"]),
                    item["level"], item["rank"], item["ai_wander"],
                    item["ai_combat"], item["speed_walk"], item["max_hp"],
                    item["drops_normal"], item["drops_equipment"],
                    item["drops_specially"],
                )
            )
        return "".join(out)

    town = town or []
    pending = pending or []
    withdrawn = withdrawn or []
    rule_per_placement = "{\n%s}" % "".join(
        "    %d: %r,\n" % (item["placement_index"], which)
        for which, items in ((rule, roster + town),
                             (IDENTITY_RULE_SETNUM, pending))
        for item in sorted(items, key=lambda row: row["placement_index"])
    )
    withdrawn_rows = "".join(
        "    (%d, %d, %s, %d, %s),\n"
        % (item["placement_index"], item["was_template_id"],
           ascii(item["was_display_name"]), item["now_template_id"],
           ascii(item["now_display_name"]))
        for item in withdrawn
    )
    pending_preamble = ""
    if pending:
        pending_preamble = (
            "# !! STILL THE OLD READING, ON PURPOSE, FOR ONE MORE ROUND.\n"
        )
    legacy_note = ""
    if scene.strip().lower() == CONTROL_SCENE and pending:
        legacy_note = (
            "\n# ~~The two constants this table used to be checked "
            "against.~~  Kept as the\n"
            "# record of the reading RE-128 replaced: under ``setnum`` this "
            "scene's\n"
            "# placement 30 read as MOBS 31 \"Tornado Eagle\", level 27, HP "
            "3857 -- the\n"
            "# values ``v141`` froze as V119_P30_TARGET_NAME / "
            "V117_P30_EXACT_HP.  Under\n"
            "# ``cline`` that placement is Mob-Set 31 -> n_ID 248 "
            "\"Da Vinci\".\n"
            "LEGACY_SETNUM_READING_OF_PLACEMENT_30 = {\n"
            "    'template_id': 31, 'display_name': 'Tornado Eagle', "
            "'level': 27,\n"
            "    'max_hp': 3857,\n"
            "}\n"
        )
    unresolved_rows = "".join(
        "    (%d, %d, %s),\n"
        % (item["placement_index"], item["set_number"], ascii(item["reason"]))
        for item in (unresolved or [])
    )
    rank_zero_rows = "".join(
        "    (%d, %d, %s, %d),\n"
        % (item["placement_index"], item["template_id"],
           ascii(item["display_name"]), item["ai_combat"])
        for item in (rank_zero_combat or [])
    )
    set_numbers = "{\n%s}" % "".join(
        "    %d: %d,\n" % (item["placement_index"], item["set_number"])
        for item in sorted(roster + town + pending,
                           key=lambda row: row["placement_index"])
    )
    digest_block = "\n".join(
        "    %-14s %s" % (name, value) for name, value in sorted(digests.items())
    )
    census_block = "\n".join(
        "    %-20s %d" % (name, value) for name, value in sorted(census.items())
    )
    body = _HEADER % {
        "scene": scene,
        "rule": rule,
        "cline_type": repr(cline_type),
        "digests": _ascii_dict(digests),
        "census": _ascii_dict(census),
        "controls": _ascii_dict(controls or {}),
        "set_numbers": set_numbers,
        "digest_block": digest_block,
        "census_block": census_block,
        "rows": _rows(roster),
        "town_rows": _rows(town),
        "withdrawn_rows": withdrawn_rows,
        "rank_zero_rows": rank_zero_rows,
        "unresolved_rows": unresolved_rows,
        "pending_preamble": pending_preamble,
        "legacy_note": legacy_note,
        "pending_rows": _rows(pending),
        "rule_per_placement": rule_per_placement,
    }
    if not body.isascii():
        raise MineError("generated module is not pure ASCII")
    return body


def _ascii_dict(mapping: dict) -> str:
    items = "".join(
        "    %s: %s,\n" % (ascii(key), ascii(value))
        for key, value in sorted(mapping.items())
    )
    return "{\n%s}" % items


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gamedata", required=True, type=Path,
                        help="pf_bridge/gamedata directory on the bridge clone")
    parser.add_argument("--scene", default=CONTROL_SCENE)
    parser.add_argument("--out", type=Path,
                        help="write the generated module here (default: stdout)")
    parser.add_argument("--legacy", type=Path,
                        default=Path(__file__).resolve().parents[1]
                        / "current" / "pf_login_game_server_v141.py")
    parser.add_argument("--verify-frozen", action="store_true",
                        help="re-derive bg0001's 115 rows and diff against v141")
    parser.add_argument("--predicate-census", action="store_true",
                        help="print how the four hostility readings split the scene")
    parser.add_argument("--keep-withdrawn-rows", action="store_true",
                        help="also ship the rows the previous rule selected "
                             "that this one withdraws, labelled per row as "
                             "the legacy reading pending migration")
    parser.add_argument("--identity-rule", default=IDENTITY_RULE_CLINE,
                        choices=list(IDENTITY_RULES),
                        help="how a Mob-Set number becomes a MOBS.n_ID "
                             "(default: cline, the RE-128 crosswalk)")
    args = parser.parse_args(argv)

    try:
        if args.verify_frozen:
            compared, mismatches = verify_frozen(args.gamedata, args.legacy)
            print("verify-frozen: %d rows compared, %d mismatches"
                  % (compared, mismatches))
            if mismatches:
                return 1

        sources = Sources(args.gamedata, args.scene)
        rule = args.identity_rule
        controls: dict[str, str] = {}
        if rule == IDENTITY_RULE_SETNUM:
            check_controls(sources)
            controls = {"legacy_setnum_controls": "re-derived"}
        else:
            controls = check_crosswalk_controls(sources)
        census = predicate_census(sources, rule)
        if args.predicate_census:
            for name, value in sorted(census.items()):
                print("census %-20s %d" % (name, value))
        roster = hostile_roster(sources, rule)
        town = town_target_roster(sources, rule)
        if not roster and not town:
            raise MineError(
                "scene %r ships nothing under rule %r: no placement has both "
                "a rank and a combat AI, and none is on the town-target "
                "allowlist" % (args.scene, rule)
            )
        withdrawn = withdrawn_under_rule(sources, rule)
        pending = []
        if args.keep_withdrawn_rows and rule != IDENTITY_RULE_SETNUM:
            kept = {item["placement_index"] for item in withdrawn}
            pending = [
                row for row in hostile_roster(sources, IDENTITY_RULE_SETNUM)
                if row["placement_index"] in kept
            ]
        rank_zero_combat = [
            _roster_row(sources, item)
            for item in unambiguous_placements(sources, rule)
            if _nonzero(item[6], "n_AI_COMBAT") and not _nonzero(item[6], "n_RANK")
        ]
        module = render_module(
            args.scene, roster, sources.digests(), census,
            rule=rule, cline_type=sources.cline_type, town=town,
            withdrawn=withdrawn, controls=controls,
            rank_zero_combat=rank_zero_combat, pending=pending,
            unresolved=unresolved_placements(sources, rule),
        )
    except MineError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 2

    print("scene %s rule %s: %d hostile + %d town-target + %d legacy-pending "
          "placements, "
          "%d distinct templates, %d withdrawn"
          % (args.scene, rule, len(roster), len(town), len(pending),
             len({item["template_id"] for item in roster + town}),
             len(withdrawn)))
    for item in withdrawn:
        print("  withdrawn placement %-4d %-34s -> %s"
              % (item["placement_index"], item["was_display_name"],
                 item["now_display_name"] or "(no MOBS_TIP name)"))
    if args.out:
        args.out.write_text(module, encoding="ascii")
        print("wrote %s (%d bytes)" % (args.out, len(module)))
    else:
        sys.stdout.write(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
