#!/usr/bin/env python3
"""LANE-B: mine the AI rows the scene roster's monsters actually point at.

WHAT THIS TOOL IS FOR.  ``field_mob_tables.py`` carries two columns nothing in
``src/`` had ever used: ``n_AI_WANDER`` and ``n_AI_COMBAT``.  They are not
numbers, they are FOREIGN KEYS, and the tables they point into are committed on
the bridge clone:

    gamedata/tables/CONSTDATA_TH__AI_WANDER.tsv   n_ID -> wander script,
                                                  n_FACTION, n_OFFESIVE, n_AGGRO
    gamedata/tables/CONSTDATA_TH__AI_COMBAT.tsv   n_ID -> s_CONDITOIN, s_ACTION

READ AS an aggro radius in the same world units the placements are written in,
``n_AGGRO`` and its companion ``n_OFFESIVE`` (does the monster acquire a target
that never hit it) are the two profile values this project no longer has to
invent.  Until this tool ran, ``mob_aggro.MobAiProfile`` took both from the
caller with the module's own note that "this project has not established the
world coordinate scale and refuses to invent one silently".

THE NOVELTY CLAIM AN EARLIER DRAFT MADE HERE IS WITHDRAWN, and kept rather
than deleted.  It said these were "two columns nobody had read".
``pf_bridge/FACTPACK_R102_HOSTILE13_ROSTER.md`` (2026-08-20) read them SIX DAYS
EARLIER, by a live parse out of the client image at offset 0x329A46, and
published the same division this tool re-derives: Tornado Eagle retaliate-only
(OFFESIVE=0, AGGRO=0), and the aggressive three being Jungle Big Tiger 0x203B,
Ward Apes 0x2040 and Orc Chief 0x2085.  That is not a loss - it is the best
thing in this file.  An independent parse from a different direction reaching
the same reading is CORROBORATION, and it is the strongest evidence this lane
has that ``n_AGGRO`` means what it looks like.  What this tool adds is not the
reading: it is that a server with no bridge clone can hold the rows, joined to
the roster, with digests, and re-derive them.

WHAT THIS TOOL DOES NOT CLAIM.  Only two of the five profile values are in a
table.  ``leash_radius``, ``home_radius``, ``attack_range`` and
``attack_cadence_ticks`` are NOT columns anywhere in this data set, and this
tool does not pretend otherwise: it writes the two mined columns and nothing
else.  Whoever chooses the remaining four chooses them in the open, in
``mob_ai_control``, with a tag on each.

    - ``s_WANDER`` ("RUN;1;2\\nIDLE;10;30") is an idle-wander SCRIPT, not a
      combat rule, and this lane drives no wander.  It is carried verbatim
      because dropping a column is how a later reader concludes it was never
      there.
    - ``s_CONDITOIN``/``s_ACTION`` (the misspelling is the table's) LOOK like
      newline-joined PARALLEL lists: condition line i selecting action line i.
      THAT READING IS NOT UNIVERSAL and an earlier draft of this tool
      REFUSED on any row that broke it: SIX of the 276 shipped rows have
      mismatched lengths (1516, 1517, 1536, 1537, 1546, 1547) and EIGHT do not
      end with the ``GO(0)`` default (520, 1001, 1003, 1040, 1505, 1526, 9903,
      9904).  bg0001 touches none of them, so the refusal was green here and
      would have stopped the next scene dead over a reading this tool has no
      business enforcing.  The lengths are now RECORDED per row, not refused
      on, and ``AI_COMBAT_PARALLEL`` names which rows the reading holds for.
      The
      conditions name buffs and skills this project has never sent.  They are
      carried verbatim and PARSED BY NOBODY: the distances inside them
      (``DISTANCE_ENEMY<(275)``) are skill-selection bands, not a melee reach,
      and reading them as an attack range would be an invention wearing a
      table's clothes.
    - ``CONSTDATA_TH__AI_TACTIC.tsv`` also exists and is NOT mined: its rows are
      keyed by ``s_CREWID`` and speak of ``PET_AI`` and ``MASTER_TARGET``, so it
      is the player-crew/pet tactic table, not the monster AI table.

THE CONTROLS THIS TOOL REFUSES ON.  Three, and it writes nothing if any breaks:

    1. every ``ai_wander`` and ``ai_combat`` id in
       ``field_mob_tables.HOSTILE_PLACEMENTS`` resolves to exactly one row;
    2. the MOBS digest this tool reads equals the one
       ``field_mob_tables.SOURCE_DIGESTS['mobs']`` recorded when the roster was
       mined -- otherwise the two generated modules describe different data;
    3. no wander row is OFFENSIVE WITH A ZERO RADIUS.  That direction is the
       only one the table supports, and an earlier draft of this control
       asserted the biconditional instead - offensive if and only if a radius -
       which EIGHT of the 73 shipped rows break (24, 40, 41, 46, 103, 110,
       9000, 9001 are all n_OFFESIVE=0 carrying a radius of 500 to 5000).  The
       control was green only because bg0001 touches two rows and neither is
       one of them, and it would have refused the next scene outright, writing
       nothing.  A row that is offensive with NO radius has no reading at all -
       it says "charges, from nowhere" - so that one is still refused.

ASCII ONLY, ON PURPOSE -- lesson 86, the bridge console is code page 874.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import sys


WANDER_COLUMNS = ("n_ID", "s_WANDER", "n_FACTION", "n_OFFESIVE", "n_AGGRO")
COMBAT_COLUMNS = ("n_ID", "s_CONDITOIN", "s_ACTION")

# Control 2: the roster and these rows must have been mined from the same MOBS.
CONTROL_MOBS_DIGEST_KEY = "mobs"

# CONTROL 4, added after an adversarial review pointed out that the two AI
# digests were RECORDED and never COMPARED to anything: corrupting a value in a
# source TSV produced a green run and a wrong module.  These are the digests
# this tool was written against.  --accept-new-digests is the deliberate,
# noisy way to move them when the game data legitimately changes.
CONTROL_AI_DIGESTS = {
    "ai_wander":
        "0b3f1eb8e67915c4be5758c734cae17c575ac2aa76cb989e13242cfb6ad01a23",
    "ai_combat":
        "19cbc17fb124b5569dbe670fd793d22f00fec72645e6027348f09a6612d04a46",
}


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


def _key(rows: list[dict], column: str, path: Path) -> dict[int, dict]:
    keyed: dict[int, dict] = {}
    for row in rows:
        raw = (row.get(column) or "").strip()
        if not raw:
            continue
        try:
            value = int(raw)
        except ValueError:
            raise MineError("non-integer key %r in %s" % (raw, path))
        if value in keyed:
            raise MineError("duplicate key %d in %s" % (value, path))
        keyed[value] = row
    return keyed


def _int(row: dict, column: str, where: str) -> int:
    raw = (row.get(column) or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise MineError("%s: %s is not an integer (%r)" % (where, column, raw))


def _text(row: dict, column: str, where: str) -> str:
    raw = row.get(column)
    if raw is None:
        raise MineError("%s: no %s column" % (where, column))
    return raw.strip()


def _require_columns(rows: list[dict], columns: tuple[str, ...],
                     path: Path) -> None:
    for column in columns:
        if column not in rows[0]:
            raise MineError("%s has no %r column" % (path, column))


def load_roster_module(repo_root: Path):
    """Import the generated roster without importing the whole package."""
    return load_roster_modules(repo_root)[0]


def load_roster_modules(repo_root: Path) -> tuple:
    """Every scene roster this lane ships, without importing the package.

    ROUND 8ftmbx: ~~bg0001 alone~~.  bg0001 now ships four practice dummies
    and nothing else (COO-DECISION 2026-08-29T00:41+07:00 withdrew the nine
    set-number rows), so a bg0001-only mining resolves ONE wander row and no
    combat row at all -- and every Bg0002 monster, a scene this lane already
    loads, then fails ``profile_of`` with "ai_row_missing".  The AI rows are
    keyed by global n_ID like the drop sets are, so the union is a superset
    and never a merge of disagreeing rows.

    ROUND n8kq4r: added ``field_mob_tables_bg0015`` to the union.  Bg0015 is
    NOT registered in ``field_mobs._SCENE_TABLE_MODULES`` (that gate stays
    shut -- this tool does not touch it and neither does this round), so
    widening the union here changes nothing a player can reach today.  It
    only stops the FIRST swing a future registration would take from
    unwinding the listener thread with ``MobAiControlError: ai_row_missing``
    (measured end to end in ``mob_combat_bg0015_gates.py``, round 6cm6ry):
    Bg0015's 12 hostile rows want ``AI_COMBAT`` ids 102/134/273/301/323/333/
    472 and placement 87 wants ``AI_WANDER`` 22, none of which the
    bg0001+Bg0002-only union ever asked the bridge tables for.
    """
    sys.path.insert(0, str(repo_root / "src"))
    try:
        from pirateforce_foundation import field_mob_tables
        from pirateforce_foundation import field_mob_tables_bg0002
        from pirateforce_foundation import field_mob_tables_bg0015
    finally:
        sys.path.pop(0)
    return (field_mob_tables, field_mob_tables_bg0002, field_mob_tables_bg0015)


def mine(gamedata: Path, repo_root: Path,
         accept_new_digests: bool = False) -> tuple[dict, dict, dict, dict]:
    roster_modules = load_roster_modules(repo_root)
    # Every row the roster module SHIPS, not only the ones its hostility
    # predicate selected: from round szdkgs a scene can ship a named town
    # target (rank 0, no combat AI) whose n_AI_WANDER row is still a foreign
    # key something has to resolve.  Reading only HOSTILE_PLACEMENTS here is
    # what made a boot refuse with "ai_row_missing: placement 103 points at
    # AI_WANDER 21".  Older modules that carry no SHIPPED_PLACEMENTS are read
    # exactly as before.
    placements = []
    for roster_module in roster_modules:
        rows = getattr(roster_module, "SHIPPED_PLACEMENTS", None)
        if rows is None:
            rows = getattr(roster_module, "HOSTILE_PLACEMENTS", None)
        if type(rows) is not list or not rows:
            raise MineError(
                "the generated roster for scene %r is missing or empty"
                % (getattr(roster_module, "SCENE", roster_module),))
        placements.extend(rows)

    wander_path = gamedata / "tables" / "CONSTDATA_TH__AI_WANDER.tsv"
    combat_path = gamedata / "tables" / "CONSTDATA_TH__AI_COMBAT.tsv"
    mobs_path = gamedata / "tables" / "CONSTDATA_TH__MOBS.tsv"

    wander_rows = _read_tsv(wander_path)
    combat_rows = _read_tsv(combat_path)
    _require_columns(wander_rows, WANDER_COLUMNS, wander_path)
    _require_columns(combat_rows, COMBAT_COLUMNS, combat_path)
    wander = _key(wander_rows, "n_ID", wander_path)
    combat = _key(combat_rows, "n_ID", combat_path)

    digests = {
        "ai_wander": _digest(wander_path),
        "ai_combat": _digest(combat_path),
        CONTROL_MOBS_DIGEST_KEY: _digest(mobs_path),
    }

    # CONTROL 2 -- the roster and these rows must describe the same MOBS table.
    # ~~read off ``roster_module``~~ -- pf-adversary (round 8ftmbx, D1) proved
    # by execution that once this tool mined more than one scene, that name was
    # the LEAKED LOOP VARIABLE from the roster loop above, so the control only
    # ever checked the LAST module and bg0001 -- the scene this tool is named
    # for -- could go stale with no refusal.  Corrupting bg0001's recorded
    # digest mined normally; corrupting Bg0002's refused.  Every module is
    # checked now, and the refusal says WHICH scene drifted.
    for module in roster_modules:
        recorded = getattr(module, "SOURCE_DIGESTS", {}).get(
            CONTROL_MOBS_DIGEST_KEY)
        if recorded != digests[CONTROL_MOBS_DIGEST_KEY]:
            raise MineError(
                "MOBS digest drift: scene %r's roster was mined from %s and "
                "this tool reads %s -- regenerate that roster first"
                % (getattr(module, "SCENE", module), recorded,
                   digests[CONTROL_MOBS_DIGEST_KEY]))

    # CONTROL 4 -- the AI tables are the ones this tool was written against.
    if not accept_new_digests:
        for name, expected in sorted(CONTROL_AI_DIGESTS.items()):
            if digests[name] != expected:
                raise MineError(
                    "%s digest drift: expected %s, read %s.  If the game data "
                    "legitimately changed, re-run with --accept-new-digests "
                    "and update CONTROL_AI_DIGESTS in the same commit."
                    % (name, expected, digests[name]))

    # CONTROL 1 -- every foreign key resolves.
    wander_wanted: set[int] = set()
    combat_wanted: set[int] = set()
    links: list[tuple[int, int, int]] = []
    for ordinal, row in enumerate(placements):
        if type(row) is not tuple or len(row) != 16:
            raise MineError("roster row %d has wrong shape" % ordinal)
        placement_index, ai_wander, ai_combat = row[0], row[9], row[10]
        if ai_wander not in wander:
            raise MineError(
                "placement %d points at AI_WANDER %r, which has no row"
                % (placement_index, ai_wander))
        # n_AI_COMBAT 0 is not a dangling key, it is the table saying THIS
        # ACTOR HAS NO COMBAT AI - the shape of every NPC in a town, and of
        # the practice dummy this lane ships from round szdkgs.  It is carried
        # through as 0 with no row, and the consumer must handle "no combat
        # profile" rather than being handed an invented one.
        if ai_combat and ai_combat not in combat:
            raise MineError(
                "placement %d points at AI_COMBAT %r, which has no row"
                % (placement_index, ai_combat))
        wander_wanted.add(ai_wander)
        if ai_combat:
            combat_wanted.add(ai_combat)
        links.append((placement_index, ai_wander, ai_combat))

    wander_out = {}
    for identity in sorted(wander_wanted):
        row = wander[identity]
        where = "AI_WANDER %d" % identity
        wander_out[identity] = (
            _text(row, "s_WANDER", where),
            _int(row, "n_FACTION", where),
            _int(row, "n_OFFESIVE", where),
            _int(row, "n_AGGRO", where),
        )
        offensive, aggro = wander_out[identity][2], wander_out[identity][3]
        if offensive not in (0, 1):
            raise MineError("%s: n_OFFESIVE is %r, not 0 or 1"
                            % (where, offensive))
        if aggro < 0:
            raise MineError("%s: n_AGGRO is negative (%r)" % (where, aggro))
        # CONTROL 3 -- the one direction the table supports.  A non-offensive
        # row MAY carry a radius (8 of the 73 shipped rows do); an offensive
        # row with no radius has no reading and is refused.
        if offensive and not aggro:
            raise MineError(
                "%s: n_OFFESIVE=%d with n_AGGRO=%d has no reading - it says "
                "the monster charges from nowhere.  Read the row and rule on "
                "it." % (where, offensive, aggro))

    combat_out = {}
    parallel: dict[int, bool] = {}
    for identity in sorted(combat_wanted):
        row = combat[identity]
        where = "AI_COMBAT %d" % identity
        conditions = _text(row, "s_CONDITOIN", where)
        actions = _text(row, "s_ACTION", where)
        # RECORDED, NOT REFUSED -- see the header.  The split is on the two
        # characters the TSV literally stores, not on a real newline.
        parallel[identity] = (
            len(conditions.split("\\n")) == len(actions.split("\\n")))
        combat_out[identity] = (conditions, actions)

    return wander_out, combat_out, dict(links=links, parallel=parallel), digests


_HEADER = '''"""GENERATED - do not hand-edit.  LANE-B monster AI rows.

Written by ``tools/pf_mine_mob_ai_rows.py`` from the committed game data on the
bridge clone.  Regenerate rather than patch; the generator carries the three
controls it refuses on and what each column is and is not.

These are the AI rows that ``field_mob_tables.HOSTILE_PLACEMENTS`` points at
through its ``ai_wander`` and ``ai_combat`` columns.  Every value is copied
from a table; nothing here was composed, parsed or rounded.

TWO COLUMNS ARE PROFILE VALUES AND THE REST ARE NOT
    n_AGGRO      the aggro radius, in the world units the placements use
    n_OFFESIVE   whether the monster acquires a target that never hit it
    s_WANDER     an idle-wander script.  This lane drives no wander.
    s_CONDITOIN  USUALLY parallel to s_ACTION, one line each.  Six of the 276
                 shipped rows are not, and eight do not end with the GO(0)
                 default, so AI_COMBAT_PARALLEL records the answer per row
                 instead of the generator enforcing a law that is not one.
                 The distances inside are skill-selection bands, NOT a melee
                 reach.  Nothing parses these; they are carried verbatim.

SOURCES AND THEIR DIGESTS AT MINING TIME
%(digest_block)s
"""

from __future__ import annotations


SCENE = %(scene)r
SOURCE_DIGESTS = %(digests)s

# n_ID -> (s_WANDER, n_FACTION, n_OFFESIVE, n_AGGRO)
AI_WANDER_ROWS = {
%(wander_rows)s}

# n_ID -> (s_CONDITOIN, s_ACTION)
AI_COMBAT_ROWS = {
%(combat_rows)s}

# n_ID -> does s_CONDITOIN have the same number of lines as s_ACTION.  RECORDED,
# not enforced: six of the 276 shipped rows are False, so the parallel-list
# reading is a property of most rows and not a law of the table.
AI_COMBAT_PARALLEL = {
%(parallel)s}

# (placement_index, ai_wander_id, ai_combat_id) -- the join this module exists
# to make checkable without the bridge clone present.
PLACEMENT_AI_LINKS = [
%(links)s]
'''


def render_module(scene: str, wander: dict, combat: dict, links: list,
                  digests: dict, parallel: dict) -> str:
    wander_rows = "".join(
        "    %d: (%s, %d, %d, %d),\n"
        % (identity, ascii(row[0]), row[1], row[2], row[3])
        for identity, row in sorted(wander.items())
    )
    combat_rows = "".join(
        "    %d: (%s,\n         %s),\n" % (identity, ascii(row[0]), ascii(row[1]))
        for identity, row in sorted(combat.items())
    )
    parallel_rows = "".join(
        "    %d: %r,\n" % (identity, value)
        for identity, value in sorted(parallel.items())
    )
    link_rows = "".join(
        "    (%d, %d, %d),\n" % link for link in sorted(links)
    )
    digest_block = "\n".join(
        "    %-14s %s" % (name, value) for name, value in sorted(digests.items())
    )
    body = _HEADER % {
        "scene": scene,
        "digests": _ascii_dict(digests),
        "digest_block": digest_block,
        "wander_rows": wander_rows,
        "combat_rows": combat_rows,
        "links": link_rows,
        "parallel": parallel_rows,
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
    parser.add_argument("--out", type=Path,
                        help="write the generated module here (default: stdout)")
    parser.add_argument("--accept-new-digests", action="store_true",
                        help="the AI tables changed on purpose; update "
                             "CONTROL_AI_DIGESTS in the same commit")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        wander, combat, joined, digests = mine(
            args.gamedata, repo_root, args.accept_new_digests)
    except MineError as error:
        sys.stderr.write("REFUSED: %s\n" % error)
        return 2

    roster_module = load_roster_module(repo_root)
    body = render_module(
        getattr(roster_module, "SCENE", "unknown"),
        wander, combat, joined["links"], digests, joined["parallel"],
    )
    if args.out is None:
        sys.stdout.write(body)
    else:
        args.out.write_text(body, encoding="ascii", newline="\n")
        sys.stderr.write(
            "wrote %s: %d wander rows, %d combat rows, %d links\n"
            % (args.out, len(wander), len(combat), len(joined["links"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
