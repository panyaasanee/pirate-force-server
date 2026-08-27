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
    placements     e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f
    standard_mob   4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925

SELECTION CENSUS FOR THIS SCENE (see the generator on why this is printed)
    ai_combat            17
    drops_normal         17
    rank                 17
    rank_and_ai_combat   17
    unambiguous          49
"""

from __future__ import annotations


SCENE = 'Bg0002'
SOURCE_DIGESTS = {
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'mobs_tip': 'e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f',
    'placements': 'e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f',
    'standard_mob': '4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925',
}
PREDICATE_CENSUS = {
    'ai_combat': 17,
    'drops_normal': 17,
    'rank': 17,
    'rank_and_ai_combat': 17,
    'unambiguous': 49,
}

# (placement_index, template_id, x, y, z, visual_preset, display_name, level,
#  rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
#  drops_equipment, drops_specially)
HOSTILE_PLACEMENTS = [
    (50, 31, -13085.171875, -19977.615234375, 2012.8807373046875, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (58, 34, 18879.498046875, 1349.995361328125, 742.139404296875, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (59, 34, 18530.75390625, 6839.6767578125, 966.080322265625, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (60, 34, 21421.005859375, 9277.1123046875, 590.6787719726562, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (61, 35, 19111.2265625, -1607.8365478515625, 716.8709716796875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (77, 31, -10755.2109375, -19645.896484375, 2102.639892578125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (78, 31, -15819.3173828125, -19490.04296875, 2092.069580078125, 'M011_000_000_SP3', 'Tornado Eagle', 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (79, 35, 18347.130859375, 6794.07177734375, 985.388671875, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (80, 35, 19162.310546875, 1337.4029541015625, 708.5288696289062, 'M025_001_000_BOSS', 'Fighting Fish Sergeant', 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (86, 34, 20485.072265625, 8018.71337890625, 623.4412231445312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (87, 34, 18747.009765625, 5091.45166015625, 963.4185180664062, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (88, 34, 19234.421875, 2805.1865234375, 849.1326293945312, 'M025_001_000_N', 'Fighting Fish soldier', 25, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (92, 103, 17870.701171875, 6142.2685546875, 946.0828857421875, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (93, 103, 17646.60546875, 5751.74072265625, 1472.725830078125, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (94, 103, 17927.32421875, 5449.716796875, 920.7349853515625, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (95, 103, 17194.107421875, 6104.9345703125, 1016.1411743164062, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
    (96, 103, 17243.01171875, 5434.12158203125, 979.5286254882812, 'M023_000_001_SP3', 'Orc Chief', 58, 1, 11, 332, 100, 38728, 2701003, 5400003, 0),
]
