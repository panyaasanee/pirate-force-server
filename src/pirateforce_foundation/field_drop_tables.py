"""GENERATED - do not hand-edit.  LANE-B drop sets for one scene.

Written by ``tools/pf_mine_scene_drop_tables.py`` from the committed game
data on the bridge clone.  Regenerate rather than patch; the generator
carries the id rule, the four controls it refuses on, and the reasons.

Every value below is copied from a table.  Nothing here was composed, no
rate was rounded, no weight was normalized and no zero-rate slot was
dropped: a zero rate is data, and the roller's refusal is tested against
a real row because of it.

DROPS_QUEST IS ABSENT ON PURPOSE.  Only 311 of the 2478 DROPS_QUEST
sets the mobs reference exist client-side, so ~87 pct of that model is
missing and any DROPS_QUEST row written here would be invention.
13 roster row(s) name one; they are carried without it.

``drop_model_type`` is copied for information and is NOT a claim, and
in particular it is NOT the switch that makes an item model appear:
GT-045 (CLOSED-ANSWERED 2026-08-25) put id 2200423, whose value here is
1, on a real client's wire and measured a NAME LABEL, brown dust and NO
MODEL AT ALL.  The column is carried as a fingerprint of the tables and
as the pair this tool's control 2 compares; nothing more.

SOURCES AND THEIR DIGESTS AT MINING TIME
    CONSTDATA_TH__DROPS_EQUIPMENT      06909f73fa00122216443b2e7ea6e58d1357bbf0ae0bf1292f9207c02ca31dd3
    CONSTDATA_TH__DROPS_NORMAL         f8df1d7c948139390e64ccedd634088a6e1d6f6f3d019dc93aed490d278ab913
    CONSTDATA_TH__DROPS_SPECIALLY      458742f2c43635a3665bdd5757a4e2efd3634d39446bdbb5944f0e5132beeca1
    CONSTDATA_TH__EQUIPMENT_BASE       dc39d8b338f78870ac32741b8bd1ddbe5a4696b137378fcfe739721fb6924c97
    CONSTDATA_TH__ITEM_CONSUMABLES     04586d54730fee23b7120ec03d7e7b5b17345d23fe4c1d946e7e71222e698e29
    CONSTDATA_TH__ITEM_MISC            8cd1774d42230938d429f8fe849f1073467489daac9ac265689bfa70302d5292
    CONSTDATA_TH__ITEM_QUEST           9bb9ca8f416812cf724284146d704a8ece86f61e612cdd688005caf9f860a05c
    CONSTDATA_TH__MOBS                 3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
    TEXTDATA_TH__EQUIPMENT_BASE_TIP    8fc17fee3213f22dc0581a952c5e3385f317253f46cca6b08930a6808489dbe9
    TEXTDATA_TH__ITEM_CONSUMABLES_TIP  8f9fac6170750bbdc4410420498f60563e15653523f1a4461cbae1a84f1046dc
    TEXTDATA_TH__ITEM_MISC_TIP         163cf4d0862e7f5797d9dcb0e110e4f5cd78e089800b5e9328326499a5585ed2
    TEXTDATA_TH__ITEM_QUEST_TIP        2818474f4e9c3ce983d74edcb9dc8f7207e1a351c04bb7146de5aacdc098b346
"""

from __future__ import annotations


SCENE = 'bg0001'
SOURCE_DIGESTS = {
    'CONSTDATA_TH__DROPS_EQUIPMENT': '06909f73fa00122216443b2e7ea6e58d1357bbf0ae0bf1292f9207c02ca31dd3',
    'CONSTDATA_TH__DROPS_NORMAL': 'f8df1d7c948139390e64ccedd634088a6e1d6f6f3d019dc93aed490d278ab913',
    'CONSTDATA_TH__DROPS_SPECIALLY': '458742f2c43635a3665bdd5757a4e2efd3634d39446bdbb5944f0e5132beeca1',
    'CONSTDATA_TH__EQUIPMENT_BASE': 'dc39d8b338f78870ac32741b8bd1ddbe5a4696b137378fcfe739721fb6924c97',
    'CONSTDATA_TH__ITEM_CONSUMABLES': '04586d54730fee23b7120ec03d7e7b5b17345d23fe4c1d946e7e71222e698e29',
    'CONSTDATA_TH__ITEM_MISC': '8cd1774d42230938d429f8fe849f1073467489daac9ac265689bfa70302d5292',
    'CONSTDATA_TH__ITEM_QUEST': '9bb9ca8f416812cf724284146d704a8ece86f61e612cdd688005caf9f860a05c',
    'CONSTDATA_TH__MOBS': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
    'TEXTDATA_TH__EQUIPMENT_BASE_TIP': '8fc17fee3213f22dc0581a952c5e3385f317253f46cca6b08930a6808489dbe9',
    'TEXTDATA_TH__ITEM_CONSUMABLES_TIP': '8f9fac6170750bbdc4410420498f60563e15653523f1a4461cbae1a84f1046dc',
    'TEXTDATA_TH__ITEM_MISC_TIP': '163cf4d0862e7f5797d9dcb0e110e4f5cd78e089800b5e9328326499a5585ed2',
    'TEXTDATA_TH__ITEM_QUEST_TIP': '2818474f4e9c3ce983d74edcb9dc8f7207e1a351c04bb7146de5aacdc098b346',
}
NON_ASCII_NAMES_ESCAPED = 0
MONEY_SLOTS_IN_CARRIED_SETS = 7

# set id -> ((slot_index, item_id, rate_percent, qty_min, qty_max), ...)
# Per-slot INDEPENDENT percentage rates, in table order.  item_id 0 is
# the money slot [INFERENCE, round-100 fact pack]: it has no item row.
DROPS_NORMAL = {
    2701001: (
        (1, 2400046, 30.0, 1, 1),
        (2, 2400047, 15.0, 1, 1),
        (3, 2600701, 0.5, 1, 1),
        (4, 2600751, 0.5, 1, 1),
        (5, 0, 1.0, 1, 1),
        (6, 0, 0.0, 0, 1),
    ),
    2701002: (
        (1, 2400046, 10.0, 1, 1),
        (2, 2400047, 5.0, 1, 1),
        (3, 2400519, 2.0, 1, 3),
        (4, 2400522, 2.0, 1, 3),
        (5, 2400525, 2.0, 1, 3),
        (6, 2600701, 0.5, 1, 1),
        (7, 2406957, 1.0, 1, 1),
        (8, 2406958, 1.0, 1, 1),
        (9, 2406959, 1.0, 1, 1),
        (10, 2600091, 0.5, 1, 1),
        (11, 2600751, 1.0, 1, 1),
        (12, 0, 1.0, 1, 1),
    ),
    2701003: (
        (1, 2400046, 10.0, 1, 1),
        (2, 2400047, 5.0, 1, 1),
        (3, 2400519, 2.0, 2, 4),
        (4, 2400522, 2.0, 2, 4),
        (5, 2400525, 2.0, 2, 4),
        (6, 2600701, 0.5, 1, 1),
        (7, 2406957, 1.0, 1, 1),
        (8, 2406958, 1.0, 1, 1),
        (9, 2406959, 1.0, 1, 1),
        (10, 2600091, 0.5, 1, 1),
        (11, 2600751, 1.0, 1, 1),
        (12, 0, 1.0, 1, 1),
    ),
}

# set id -> (rate_percent, number_min, number_max,
#            ((entry_index, item_id, weight), ...))
# ONE roll at rate_percent, then a weighted pick among the entries.
DROPS_EQUIPMENT = {
    5400001: (50.0, 1, 1, (
        (1, 2200201, 100),
        (2, 2200401, 100),
        (3, 2200601, 100),
        (4, 2200801, 100),
        (5, 2201001, 100),
        (6, 2201201, 100),
        (7, 2204001, 100),
        (8, 2204201, 100),
        (9, 2204401, 100),
        (10, 2204601, 100),
        (11, 2204801, 100),
        (12, 2205001, 100),
        (13, 2205201, 100),
        (14, 2205401, 100),
        (15, 2205601, 100),
        (17, 0, 100),
    )),
    5400002: (50.0, 1, 1, (
        (1, 2200202, 100),
        (2, 2200402, 100),
        (3, 2200602, 100),
        (4, 2200802, 100),
        (5, 2201002, 100),
        (6, 2201202, 100),
        (7, 2204002, 100),
        (8, 2204202, 100),
        (9, 2204402, 100),
        (10, 2204602, 100),
        (11, 2204802, 100),
        (12, 2205002, 50),
        (13, 2205202, 50),
        (14, 2205402, 50),
        (15, 2205602, 50),
        (17, 0, 100),
    )),
    5400003: (50.0, 1, 1, (
        (1, 2200222, 100),
        (2, 2200422, 100),
        (3, 2200622, 100),
        (4, 2200822, 100),
        (5, 2201022, 100),
        (6, 2201222, 100),
        (7, 2204026, 100),
        (8, 2204226, 100),
        (9, 2204426, 100),
        (10, 2204621, 100),
        (11, 2204821, 100),
        (12, 2205020, 30),
        (13, 2205220, 30),
        (14, 2205420, 30),
        (15, 2205620, 30),
        (17, 0, 100),
    )),
}

DROPS_SPECIALLY = {
    2802208: (0.0, 1, 1, (
        (1, 2414008, 100),
    )),
    2802215: (0.0, 1, 1, (
        (1, 2414015, 100),
    )),
    2802219: (0.0, 1, 1, (
        (1, 2414019, 100),
    )),
    2802234: (0.0, 1, 1, (
        (1, 2414034, 100),
    )),
    2802236: (0.0, 1, 1, (
        (1, 2414036, 100),
    )),
    2802253: (0.0, 1, 1, (
        (1, 2414053, 100),
    )),
    2802264: (0.0, 1, 1, (
        (1, 2414064, 100),
    )),
}

# item id -> (table_code, low_id, display_name, drop_model_type)
ITEMS = {
    2200201: (22, 201, 'Dagger', 1),
    2200202: (22, 202, 'Sharp Dagger', 1),
    2200222: (22, 222, 'Soldier Sword', 1),
    2200401: (22, 401, 'Guard Hammer', 1),
    2200402: (22, 402, 'Red Hammer', 1),
    2200422: (22, 422, 'Obtuse Hammer', 1),
    2200601: (22, 601, 'Shield', 1),
    2200602: (22, 602, 'Shield', 1),
    2200622: (22, 622, 'Obtuse Shield', 1),
    2200801: (22, 801, 'Sky Stone', 1),
    2200802: (22, 802, 'Mountain Pumice', 1),
    2200822: (22, 822, 'Ground Horse Timepiece', 1),
    2201001: (22, 1001, 'Fist Gun', 1),
    2201002: (22, 1002, 'Strength Gun', 1),
    2201022: (22, 1022, 'Pirate Short Tube', 1),
    2201201: (22, 1201, 'Wood Stick', 1),
    2201202: (22, 1202, 'Gray Stick', 1),
    2201222: (22, 1222, 'Green Wisp', 1),
    2204001: (22, 4001, 'Exile Headdress', 2),
    2204002: (22, 4002, 'Ocean Headdress', 2),
    2204026: (22, 4026, 'Misty Headdress', 2),
    2204201: (22, 4201, 'Exile Armor', 2),
    2204202: (22, 4202, 'Ocean Armor', 2),
    2204226: (22, 4226, 'Misty Armor', 2),
    2204401: (22, 4401, 'Exile Legging', 2),
    2204402: (22, 4402, 'Ocean Legging', 2),
    2204426: (22, 4426, 'Misty Legging', 2),
    2204601: (22, 4601, 'Exile Glove', 2),
    2204602: (22, 4602, 'Ocean Glove', 2),
    2204621: (22, 4621, 'Misty Glove', 2),
    2204801: (22, 4801, 'Exile Sandal', 2),
    2204802: (22, 4802, 'Ocean Sandal', 2),
    2204821: (22, 4821, 'Misty Sandal', 2),
    2205001: (22, 5001, 'Blue Necklace', 3),
    2205002: (22, 5002, 'Gold Necklace', 3),
    2205020: (22, 5020, 'Moonstar Necklace', 3),
    2205201: (22, 5201, 'Blue Ring', 3),
    2205202: (22, 5202, 'Gold Ring', 3),
    2205220: (22, 5220, 'Moonstar Ring', 3),
    2205401: (22, 5401, 'Blue Talisman', 3),
    2205402: (22, 5402, 'Gold Talisman', 3),
    2205420: (22, 5420, 'Moonstar Talisman', 3),
    2205601: (22, 5601, 'Blue Wristband', 3),
    2205602: (22, 5602, 'Gold Wristband', 3),
    2205620: (22, 5620, 'Moonstar Wristband', 3),
    2400046: (24, 46, 'Blood Cubic Crystal', 11),
    2400047: (24, 47, 'Energy Cubic Crystal', 10),
    2400519: (24, 519, 'Coarse Red Crystal Maintain', 0),
    2400522: (24, 522, 'Coarse Blue Crystal Maintain', 0),
    2400525: (24, 525, 'Coarse Green Crystal Maintain', 0),
    2406957: (24, 6957, 'Light Color Red Crystal', 0),
    2406958: (24, 6958, 'Light Color Blue Crystal', 0),
    2406959: (24, 6959, 'Light Color Green Crystal', 0),
    2414008: (24, 14008, 'Jungle Tiger', 0),
    2414015: (24, 14015, 'Ward Kingkong', 0),
    2414019: (24, 14019, 'Toxic Vine', 0),
    2414034: (24, 14034, 'Desert Eagle', 0),
    2414036: (24, 14036, 'Forest Green Eagle', 0),
    2414053: (24, 14053, 'Craig Firebird', 0),
    2414064: (24, 14064, 'Fighting Fish soldier', 0),
    2600091: (26, 91, 'Damage Piece', 0),
    2600701: (26, 701, 'Wrought iron Relic', 0),
    2600751: (26, 751, 'Nutrition Soda', 0),
}

# set id -> the MOBS template ids that reference it, in roster order
REFERENCED_BY = {
    2701001: (35, 31, 34),
    2701002: (60, 61, 62, 65),
    2701003: (94, 97, 103),
    2802208: (60,),
    2802215: (65,),
    2802219: (61,),
    2802234: (31,),
    2802236: (97,),
    2802253: (94,),
    2802264: (35, 34),
    5400001: (35, 31, 34),
    5400002: (60, 61, 62, 65, 94),
    5400003: (97, 103),
}
