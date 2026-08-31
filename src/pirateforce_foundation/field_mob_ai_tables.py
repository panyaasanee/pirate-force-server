"""GENERATED - do not hand-edit.  LANE-B monster AI rows.

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
    ai_combat      19cbc17fb124b5569dbe670fd793d22f00fec72645e6027348f09a6612d04a46
    ai_wander      0b3f1eb8e67915c4be5758c734cae17c575ac2aa76cb989e13242cfb6ad01a23
    mobs           3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
"""

from __future__ import annotations


SCENE = 'bg0001'
SOURCE_DIGESTS = {
    'ai_combat': '19cbc17fb124b5569dbe670fd793d22f00fec72645e6027348f09a6612d04a46',
    'ai_wander': '0b3f1eb8e67915c4be5758c734cae17c575ac2aa76cb989e13242cfb6ad01a23',
    'mobs': '3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b',
}

# n_ID -> (s_WANDER, n_FACTION, n_OFFESIVE, n_AGGRO)
AI_WANDER_ROWS = {
    11: ('RUN;1;2\\nIDLE;10;30', 6, 1, 1200),
    16: ('RUN;1;2\\nIDLE;10;30', 6, 0, 0),
    21: ('RUN;1;2\\nIDLE;10;30', 12, 1, 3000),
    22: ('IDLE;9;15\\nRUN;0;1', 4, 1, 5000),
}

# n_ID -> (s_CONDITOIN, s_ACTION)
AI_COMBAT_ROWS = {
    102: ('DISTANCE_ENEMY>(700);BUFF_I(4985,0,0)\\nDISTANCE_ENEMY<(701);RATE(30)\\nDISTANCE_ENEMY<(500);KD_ENEMY(1);RATE(90)\\nDISTANCE_ENEMY<(500);RATE(30);BUFF_I(4981,0,0);HP_I<(0.7)\\nGO(0)',
         'CHASE(2)\\nCHASE(1)\\nCHASE(3)\\nCHASE(4)\\nCHASE(1)'),
    134: ('BUFF_I(4984,0,0);HP_I<(0.6);RATE(25)\\nDISTANCE_ENEMY>(400);BUFF_I(4981,0,0);RATE(20)\\nDISTANCE_ENEMY>(1000);BUFF_I(4980,0,0);RATE(40)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)'),
    214: ('DOONCE(0)\\nBUFF_I(4984,0,0);RATE(10)\\nDISTANCE_ENEMY>(500);BUFF_I(4980,0,0);RATE(60)\\nDISTANCE_ENEMY<(500);BUFF_I(4982,0,0);RATE(15)\\nRATE(25)\\nDISTANCE_ENEMY<(400);BUFF_I(4981,0,0);RATE(15)\\nRATE(5)\\nGO(0)',
         'CHASE(5)\\nCHASE(5)\\nCHASE(2)\\nCHASE(4)\\nCHASE(1)\\nCHASE(3)\\nCHASE(3)\\nCHASE(1)'),
    273: ('HP_I>(0.7);RATE(30)\\nBUFF_I(4984,0,0);HP_I>(0.5);HP_I<(0.7);RATE(30)\\nBUFF_I(4984,0,0);HP_I<(0.5);RATE(30)\\nDISTANCE_ENEMY>(400);BUFF_I(4980,0,0);RATE(50)\\nBUFF_I(4983,0,0);HP_I<(0.8);RATE(20)\\nBUFF_I(4981,0,0);HP_I<(0.6);RATE(20)\\nHP_I<(0.5);RATE(15)\\nGO(0)',
         'CHASE(1)\\nCHASE(5)\\nCHASE(6)\\nCHASE(2)\\nCHASE(4)\\nCHASE(3)\\nCHASE(3)\\nCHASE(1)'),
    301: ('HP_I<(0.3);RATE(15)\\nBUFF_I(4983,0,0);HP_I<(0.4);RATE(10)\\nBUFF_I(4982,0,0);DISTANCE_ENEMY<(750);RATE(35)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(300);RATE(75)\\nGO(0)',
         'CHASE(5)\\nCHASE(4)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)'),
    323: ('BUFF_I(4984,0,0);HP_ALLY<(0.5);RATE(20)\\nBUFF_I(4981,0,0);HP_I<(0.8);RATE(25)\\nDISTANCE_ENEMY>(300);RATE(50)\\nBUFF_I(4982,0,0);HP_I>(0.5);DISTANCE_ENEMY<(600);RATE(15)\\nBUFF_I(4982,0,0);DISTANCE_ENEMY<(600);RATE(25)\\nGO(0)',
         'CHASE(6)\\nCHASE(5)\\nCHASE(2)\\nCHASE(3)\\nCHASE(4)\\nCHASE(1)'),
    332: ('BUFF_I(4983,0,0);BUFF_I(4982,0,1);RATE(40)\\nBUFF_I(4982,0,0);HP_I<(0.8);RATE(25)\\nBUFF_I(4983,0,0);HP_I<(0.5);RATE(25)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(450);RATE(60)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(4)\\nCHASE(2)\\nCHASE(1)'),
    333: ('BUFF_I(4983,0,0);BUFF_I(4982,0,1);RATE(40)\\nBUFF_I(4982,0,0);HP_I<(0.8);RATE(25)\\nBUFF_I(4983,0,0);HP_I<(0.5);RATE(25)\\nBUFF_I(4980,0,0);RATE(30)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(4)\\nCHASE(2)\\nCHASE(1)'),
    350: ('BUFF_I(4981,0,0);BUFF_I(4983,0,0);HP_I<(0.5);RATE(10)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(400);RATE(80)\\nDISTANCE_ENEMY<(275);RATE(80)\\nGO(0)',
         'CHASE(3)\\nCHASE(2)\\nCHASE(1)\\nCHASE(1)'),
    352: ('BUFF_I(4986,0,0);DISTANCE_ENEMY<(800);RATE(20)\\nBUFF_I(4981,0,0);BUFF_I(4983,0,0);HP_I<(0.7);RATE(30)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(400);RATE(80)\\nDISTANCE_ENEMY<(275);RATE(80)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)\\nCHASE(1)'),
    472: ('DISTANCE_ENEMY>(400);BUFF_I(4988,0,0);RATE(35)\\nHP_I<(0.6);DISTANCE_ENEMY<(500);RATE(25);BUFF_I(4983,0,0)\\nBUFF_I(4982,0,0);DISTANCE_ENEMY>(400);RATE(50)\\nBUFF_I(4982,0,0);RATE(20)\\nBUFF_I(4986,0,0);RATE(20)\\nBUFF_I(4981,0,0);RATE(35);HP_I<(0.8)\\nBUFF_I(4981,0,0);RATE(25)\\nBUFF_I(4985,0,0);RATE(25);HP_I<(0.4)\\nRATE(50)\\nGO(0)',
         'CHASE(10)\\nCHASE(9)\\nCHASE(8)\\nCHASE(4)\\nCHASE(7)\\nCHASE(6)\\nCHASE(3)\\nCHASE(5)\\nCHASE(2)\\nCHASE(1)'),
}

# n_ID -> does s_CONDITOIN have the same number of lines as s_ACTION.  RECORDED,
# not enforced: six of the 276 shipped rows are False, so the parallel-list
# reading is a property of most rows and not a law of the table.
AI_COMBAT_PARALLEL = {
    102: True,
    134: True,
    214: True,
    273: True,
    301: True,
    323: True,
    332: True,
    333: True,
    350: True,
    352: True,
    472: True,
}

# (placement_index, ai_wander_id, ai_combat_id) -- the join this module exists
# to make checkable without the bridge clone present.
PLACEMENT_AI_LINKS = [
    (22, 16, 301),
    (24, 11, 323),
    (27, 11, 102),
    (29, 11, 273),
    (31, 11, 134),
    (44, 16, 301),
    (45, 16, 301),
    (46, 16, 301),
    (47, 16, 301),
    (50, 16, 214),
    (51, 16, 301),
    (58, 16, 350),
    (59, 16, 350),
    (60, 16, 350),
    (61, 16, 352),
    (70, 11, 333),
    (77, 16, 214),
    (78, 16, 214),
    (79, 16, 352),
    (80, 16, 352),
    (86, 16, 350),
    (87, 16, 350),
    (87, 22, 472),
    (88, 16, 350),
    (92, 11, 332),
    (93, 11, 332),
    (94, 11, 332),
    (95, 11, 332),
    (96, 11, 332),
    (103, 21, 0),
    (105, 21, 0),
    (107, 21, 0),
    (109, 21, 0),
]
