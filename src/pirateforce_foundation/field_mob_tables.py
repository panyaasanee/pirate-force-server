"""GENERATED - do not hand-edit.  LANE-B scene mob roster.

Written by ``tools/pf_mine_scene_mob_roster.py`` from the committed game data
on the bridge clone.  Regenerate rather than patch; the generator carries the
selection rule, the controls it refuses on, and the reasoning behind both.

The rows below are the placements of one scene whose MOBS row has a rank and a
combat AI.  Every value is copied from a table; nothing here was composed.
``max_hp`` is the one derived column: ``STANDARD_MOB[n_LEVEL_MIN].n_HPMAX``.

SOURCES AND THEIR DIGESTS AT MINING TIME
    mobs           3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
    mobs_tip       e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f
    placements     2e5b4115169160d609289d0e638e953d7da16a0000e267c12c118c7c1a4cfc5f
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            13
    drops_normal         13
    rank                 13
    rank_and_ai_combat   13
    unambiguous          115
"""

from __future__ import annotations


SCENE = 'bg0001'
SOURCE_DIGESTS = {
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': '2e5b4115169160d609289d0e638e953d7da16a0000e267c12c118c7c1a4cfc5f',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 13,
    'drops_normal': 13,
    'rank': 13,
    'rank_and_ai_combat': 13,
    'unambiguous': 115,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
HOSTILE_PLACEMENTS = [
    (12, 35, 17961.1796875, 25208.271484375, 452.3008117675781, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (30, 31, 1747.5244140625, -7837.69775390625, 931.0413208007812, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (33, 34, -216.15969848632812, 11168.337890625, 575.0142822265625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (58, 60, -5893.7265625, 15161.7578125, 314.1536865234375, 'M002_000_002_SP3', 'Jungle Big Tiger', 37, 1, 11, 123, 100, 9382, 2701002, 5400002, 2802208),
    (59, 61, 10755.4521484375, 7250.541015625, 2200.4453125, 'M004_000_002_SP1', 'Toxic Vine', 38, 1, 16, 140, 100, 10149, 2701002, 5400002, 2802219),
    (60, 62, 7663.41748046875, 1862.685546875, 2037.39404296875, 'M014_000_000_N', 'Ancient Civilization Alert Weapon', 39, 1, 16, 240, 100, 10962, 2701002, 5400002, 0),
    (63, 65, 9647.2890625, -4765.767578125, 1985.731201171875, 'M003_001_000_SP3', 'Ward Apes', 43, 1, 11, 133, 100, 14910, 2701002, 5400002, 2802215),
    (95, 94, -4945.591796875, 14081.251953125, 314.1182861328125, 'M020_001_000_SP1', 'An Gebo Little Firebird', 47, 1, 16, 300, 100, 19710, 2701003, 5400002, 2802253),
    (103, 97, 14455.2685546875, 9356.755859375, 2200.45849609375, 'M011_000_002_SP3', 'Mutant Green Eagle', 51, 1, 16, 214, 100, 25564, 2701003, 5400003, 2802236),
    (105, 97, 13236.265625, 9364.3427734375, 2200.4599609375, 'M011_000_002_SP3', 'Mutant Green Eagle', 51, 1, 16, 214, 100, 25564, 2701003, 5400003, 2802236),
    (107, 97, 15649.916015625, 9317.12109375, 2200.456298828125, 'M011_000_002_SP3', 'Mutant Green Eagle', 51, 1, 16, 214, 100, 25564, 2701003, 5400003, 2802236),
    (109, 97, 11789.4384765625, 9318.8798828125, 2200.461181640625, 'M011_000_002_SP3', 'Mutant Green Eagle', 51, 1, 16, 214, 100, 25564, 2701003, 5400003, 2802236),
    (132, 103, 3722.39990234375, 21294.939453125, 84.98320007324219, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
]
