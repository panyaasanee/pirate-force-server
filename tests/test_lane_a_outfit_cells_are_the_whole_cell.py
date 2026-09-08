"""LANE-A's crosswalk tables ship the WHOLE ``s_OUTFIT`` cell, not its head.

ROUND 2a2jqp (LANE-B), under ``COO-DECISION 2026-09-08 13:41 +07:00``
(pf_bridge ``notes_to_chief/20260908_1341_COO-DECISION-b-regenerates-the-lane-
a-outfit-table-under-1313-LANE-B.md``): LANE-B regenerates these tables, LANE-A
reviews.  The ruling behind it is the owner's, ``PANYA 1313`` -- ``s_OUTFIT``
decides nothing about who is an enemy -- and ``RE-296``, which measured the
client tokenising the cell itself (``L";\\t "``) and keeping every token.

WHAT THIS FILE IS FOR, AND WHY IT REPEATS 101 STRINGS.  The regeneration ran
off the pf_bridge clone, which the gate does not have.  A pin that read the
value back out of the module it is checking would pass on any value at all, so
the 101 raw cells are copied HERE, from the same MOBS extraction each module
already pins by sha256, and compared without a bridge.  A future regeneration
that truncates a cell again -- the exact regression this round removed -- goes
red on this file on a machine with no game data on it.

THE LIVE SCENE IS DELIBERATELY NOT IN THAT LIST.  ``world_port_royal_identity``
is the one scene a player has actually stood in, and its own module records a
measured wire claim: the server sends a single basename that the client formats
into ``.\\Data\\GC\\V\\%s.avt``, so a whole cell on THAT wire would name a file
that does not exist and the actor would arrive with no body.  RE-296 measured
the client's TABLE loader, not that field, so the two are not the same
question, and this round did not answer the second one.  Port Royal therefore
keeps its single basename and this file pins that it does, so the boundary is a
tested line rather than an omission (bridge letter
``20260908_LANE-B-ASK-COO-*whole-cell-on-the-wire*``).
"""

import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_port_royal_identity  # noqa: E402


# module name -> {MOBS.n_ID: the raw s_OUTFIT cell}, copied out of
# CONSTDATA_TH__MOBS.tsv sha256
# 3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
RAW_CELLS = {
    'world_bg0003_identity': {
        55: 'M006_000_001_SP1;M006_000_001_SP2',
        56: 'M013_000_000_SP1;M013_000_000_SP2',
        57: 'M004_000_000_SP1;M004_000_000_SP2',
        58: 'M028_001_000_SP1;M028_001_000_SP2',
        59: 'M002_000_002_SP1;M002_000_002_SP2',
        63: 'M001_003_000_N;M001_003_000_SP1',
        64: 'M003_001_000_SP1;M003_001_000_SP2',
        908: 'P_MALE_015_000_SINGLE;P_MALE_015_000_SINGLE2;P_MALE_015_000_SINGLE3;P_MALE_015_000_SINGLE4;P_MALE_015_000_SINGLE5;P_MALE_015_000_SINGLE6;P_MALE_015_000_SINGLE7;P_MALE_015_000_SINGLE8;P_MALE_015_000_SINGLE9',
        7042: 'M024_001_001_SP1;M024_001_001_SP2',
    },
    'world_bg0004_identity': {
        93: 'M028_000_000_SP1;M028_000_000_SP2',
        95: 'M017_000_001_SP1;M017_000_001_SP2',
        96: 'M011_000_002_SP1;M011_000_002_SP2',
        98: 'M019_002_000_SP1;M019_002_000_SP2',
        99: 'M008_000_001_SP1;M008_000_001_SP2',
        100: 'M021_000_001_SP1;M021_000_001_SP2',
        101: 'M006_001_001_SP1;M006_001_001_SP2',
        102: 'M023_000_001_SP1;M023_000_001_SP2',
        7043: 'M024_001_001_SP1;M024_001_001_SP2',
    },
    'world_bg0005_identity': {
        138: 'M000_000_002_SP1;M000_000_002_SP2',
        139: 'M005_000_001_SP1;M005_000_001_SP2',
        140: 'M024_001_001_SP1;M024_001_001_SP2',
        141: 'M002_000_000_SP1;M002_000_000_SP2',
        142: 'M019_000_001_SP1;M019_000_001_SP2',
        143: 'M011_001_001_SP1;M011_001_001_SP2',
        145: 'M001_000_003_N;M001_000_003_SP1',
        147: 'M001_000_001_SP2;M001_000_001_SP3',
        149: 'M003_000_000_SP1;M003_000_000_SP2',
        7044: 'M024_001_001_SP1;M024_001_001_SP2',
    },
    'world_bg0006_identity': {
        219: 'M001_003_001_N;M001_003_001_SP1',
        220: 'M022_000_003_SP1;M022_000_003_SP2',
        221: 'M001_001_000_N;M001_001_000_SP1',
        223: 'M017_000_003_SP1;M017_000_003_SP2',
        224: 'M004_000_004_SP1;M004_000_004_SP2',
        225: 'M002_000_001_SP1;M002_000_001_SP2',
        227: 'M025_000_000_SP1;M025_000_000_SP2',
        228: 'M021_001_000_SP1;M021_001_000_SP2',
        229: 'M015_000_002_SP1;M015_000_002_SP2',
        7045: 'M024_001_001_SP1;M024_001_001_SP2',
    },
    'world_bg0007_identity': {
        385: 'M003_000_002_SP1;M003_000_002_SP2',
        386: 'M006_000_002_SP1;M006_000_002_SP2',
        387: 'M005_000_004_SP1;M005_000_004_SP2',
        389: 'M002_001_000_SP1;M002_001_000_SP2',
        391: 'M022_000_002_SP1;M022_000_002_SP2',
        392: 'M023_000_000_SP1;M023_000_000_SP2',
        394: 'M003_001_001_SP1;M003_001_001_SP2',
        396: 'M023_001_002_SP1;M023_001_002_SP2',
    },
    'world_bg0008_identity': {
        270: 'M024_000_000_SP1;M024_000_000_SP2',
        271: 'M005_000_003_SP1;M005_000_003_SP2',
        272: 'M025_000_002_SP1;M025_000_002_SP2',
        273: 'M003_000_001_SP1;M003_000_001_SP2',
        275: 'M013_001_001_SP1;M013_001_001_SP2',
        276: 'M006_001_002_SP1;M006_001_002_SP2',
        278: 'M021_000_000_SP1;M021_000_000_SP2',
        279: 'M024_001_002_SP1;M024_001_002_SP2',
        282: 'M025_000_001_SP1;M025_000_001_SP2',
        283: 'M000_000_002_SP1;M000_000_002_SP2',
    },
    'world_bg0009_identity': {
        307: 'M008_000_000_SP1;M008_000_000_SP2',
        308: 'M002_002_000_SP1;M002_002_000_SP2',
        309: 'M022_000_000_SP1;M022_000_000_SP2',
        310: 'M026_000_000_SP1;M026_000_000_SP2',
        311: 'M000_001_000_N;M000_001_000_SP1',
        312: 'M019_000_002_SP1;M019_000_002_SP2',
        313: 'M010_000_001_SP1;M010_000_001_SP2',
        315: 'M028_001_001_SP1;M028_001_001_SP2',
        316: 'M004_000_003_SP1;M004_000_003_SP2',
        318: 'M008_000_002_SP1;M008_000_002_SP2',
        319: 'M026_000_002_SP1;M026_000_002_SP2',
    },
    'world_bg0010_identity': {
        657: 'M026_000_000_SP1;M026_000_000_SP2',
        658: 'M026_000_002_SP1;M026_000_002_SP2',
        659: 'M026_000_001_SP1;M026_000_001_SP2',
        663: 'M008_000_000_SP1;M008_000_000_SP2',
        664: 'M024_000_000_SP1;M024_000_000_SP2',
        665: 'M024_000_001_SP1;M024_000_001_SP2',
        666: 'M024_001_001_SP1;M024_001_001_SP2',
        667: 'M024_001_000_SP1;M024_001_000_SP2',
        670: 'M025_000_001_N;M025_000_001_SP1',
        672: 'M016_000_000_SP1;M016_000_000_SP2',
        838: 'M071_000_003_SP2;M071_000_003_SP1',
        841: 'M071_000_003_SP2;M071_000_003_SP1',
    },
    'world_bg0011_identity': {
        688: 'M025_002_000_SP1;M025_002_000_SP2',
        689: 'M024_001_000_SP1;M024_001_000_SP2',
        690: 'M019_000_001_SP1;M019_000_001_SP2',
        691: 'M026_000_001_SP1;M026_000_001_SP2',
        692: 'M016_000_000_SP1;M016_000_000_SP2',
        694: 'M026_001_001_SP1;M026_001_001_SP2',
        695: 'M016_000_001_N;M016_000_001_SP1',
    },
    'world_bg0015_identity': {
        340: 'M005_001_000_SP1;M005_001_000_SP2',
        341: 'M011_000_001_SP1;M011_000_001_SP2',
        342: 'M004_000_001_SP1;M004_000_001_SP2',
        344: 'M022_000_001_SP1;M022_000_001_SP2',
        346: 'M005_000_002_SP1;M005_000_002_SP2',
        347: 'M000_001_001_N;M000_001_001_SP1',
        349: 'M017_000_002_SP1;M017_000_002_SP2',
        351: 'M006_001_000_SP1;M006_001_000_SP2',
        352: 'M003_000_003_SP1;M003_000_003_SP2',
        354: 'M023_001_000_SP1;M023_001_000_SP2',
    },
    'world_bg1001_identity': {
        2881: 'M024_000_001_SP1;M024_000_001_SP2',
        2883: 'M019_000_001_N;M019_000_001_SP1',
        2884: 'M001_000_001_SP1;M001_000_001_SP2',
    },
    'world_bg4001_identity': {
        894: 'P_FEMALE_001_000_N;P_FEMALE_002_000_MIX;P_FEMALE_004_000_N',
        898: 'P_MALE_004_000_N;P_MALE_002_000_SP1;P_MALE_001_000_ROLANCE',
    },}


def _module(name):
    return importlib.import_module("pirateforce_foundation." + name)


class LaneAShipsTheWholeOutfitCellTests(unittest.TestCase):
    """One assertion per row, named by module and MOBS id when it fails."""

    def test_every_multi_variant_row_ships_the_whole_cell(self) -> None:
        wrong = []
        for name, rows in RAW_CELLS.items():
            module = _module(name)
            fields = {row.mobs_n_id: row.outfit
                      for row in module.IDENTITIES.values()}
            for n_id, raw in rows.items():
                shipped = fields.get(n_id)
                if shipped != raw:
                    wrong.append("%s MOBS %d ships %r, the cell is %r"
                                 % (name, n_id, shipped, raw))
        self.assertEqual(wrong, [])

    def test_the_pin_covers_every_multi_variant_row_the_tables_ship(
            self) -> None:
        """The other direction: a row that grew a ';' without being pinned."""
        missing = []
        for name, rows in RAW_CELLS.items():
            module = _module(name)
            for row in module.IDENTITIES.values():
                if ";" in row.outfit and row.mobs_n_id not in rows:
                    missing.append("%s MOBS %d" % (name, row.mobs_n_id))
        self.assertEqual(missing, [])

    def test_no_row_ships_an_empty_avatar_token(self) -> None:
        """``rule any`` still requires a body: an empty token names no file."""
        bad = []
        for name in RAW_CELLS:
            module = _module(name)
            for row in module.IDENTITIES.values():
                if any(not token for token in row.outfit.split(";")):
                    bad.append("%s MOBS %d %r"
                               % (name, row.mobs_n_id, row.outfit))
        self.assertEqual(bad, [])

    def test_port_royal_the_only_live_scene_still_ships_one_basename(
            self) -> None:
        """The line this round did NOT cross, asserted rather than assumed."""
        lists = [row.outfit for row in world_port_royal_identity._BY_TEMPLATE
                 .values() if ";" in row.outfit]
        self.assertEqual(lists, [])


if __name__ == "__main__":
    unittest.main()
