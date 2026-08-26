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
}

# n_ID -> (s_CONDITOIN, s_ACTION)
AI_COMBAT_ROWS = {
    123: ('DISTANCE_ENEMY>(700);BUFF_I(4986,0,0);RATE(30)\\nDISTANCE_ENEMY<(700);BUFF_I(4985,0,0);RATE(40)\\nDISTANCE_ENEMY<(700);BUFF_I(4981,0,0);RATE(15)\\nGO(0)',
         'CHASE(2)\\nCHASE(4)\\nCHASE(3)\\nCHASE(1)'),
    133: ('BUFF_I(4984,0,0);HP_I<(0.6);RATE(10)\\nDISTANCE_ENEMY>(400);BUFF_I(4981,0,0);RATE(20)\\nDISTANCE_ENEMY>(1000);BUFF_I(4980,0,0);RATE(40)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)'),
    140: ('DISTANCE_ENEMY>(500);HP_I<(0.5);BUFF_I(4981,0,0);RATE(8)\\nDISTANCE_ENEMY>(500);RATE(20)\\nGO(0)',
         'CHASE(3)\\nCHASE(2)\\nCHASE(1)'),
    214: ('DOONCE(0)\\nBUFF_I(4984,0,0);RATE(10)\\nDISTANCE_ENEMY>(500);BUFF_I(4980,0,0);RATE(60)\\nDISTANCE_ENEMY<(500);BUFF_I(4982,0,0);RATE(15)\\nRATE(25)\\nDISTANCE_ENEMY<(400);BUFF_I(4981,0,0);RATE(15)\\nRATE(5)\\nGO(0)',
         'CHASE(5)\\nCHASE(5)\\nCHASE(2)\\nCHASE(4)\\nCHASE(1)\\nCHASE(3)\\nCHASE(3)\\nCHASE(1)'),
    240: ('DISTANCE_ENEMY>(400);RATE(95)\\nDISTANCE_ENEMY<(450);RATE(60)\\nGO(0)',
         'CHASE(2)\\nCHASE(2)\\nCHASE(1)'),
    300: ('HP_I<(0.3);RATE(3)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(300);RATE(60)\\nBUFF_I(4982,0,0);DISTANCE_ENEMY<(650);RATE(20)\\nRATE(30)\\nGO(0)',
         'CHASE(5)\\nCHASE(2)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)'),
    332: ('BUFF_I(4983,0,0);BUFF_I(4982,0,1);RATE(40)\\nBUFF_I(4982,0,0);HP_I<(0.8);RATE(25)\\nBUFF_I(4983,0,0);HP_I<(0.5);RATE(25)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(450);RATE(60)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(4)\\nCHASE(2)\\nCHASE(1)'),
    350: ('BUFF_I(4981,0,0);BUFF_I(4983,0,0);HP_I<(0.5);RATE(10)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(400);RATE(80)\\nDISTANCE_ENEMY<(275);RATE(80)\\nGO(0)',
         'CHASE(3)\\nCHASE(2)\\nCHASE(1)\\nCHASE(1)'),
    352: ('BUFF_I(4986,0,0);DISTANCE_ENEMY<(800);RATE(20)\\nBUFF_I(4981,0,0);BUFF_I(4983,0,0);HP_I<(0.7);RATE(30)\\nBUFF_I(4980,0,0);DISTANCE_ENEMY>(400);RATE(80)\\nDISTANCE_ENEMY<(275);RATE(80)\\nGO(0)',
         'CHASE(4)\\nCHASE(3)\\nCHASE(2)\\nCHASE(1)\\nCHASE(1)'),
}

# n_ID -> does s_CONDITOIN have the same number of lines as s_ACTION.  RECORDED,
# not enforced: six of the 276 shipped rows are False, so the parallel-list
# reading is a property of most rows and not a law of the table.
AI_COMBAT_PARALLEL = {
    123: True,
    133: True,
    140: True,
    214: True,
    240: True,
    300: True,
    332: True,
    350: True,
    352: True,
}

# (placement_index, ai_wander_id, ai_combat_id) -- the join this module exists
# to make checkable without the bridge clone present.
PLACEMENT_AI_LINKS = [
    (12, 16, 352),
    (30, 16, 214),
    (33, 16, 350),
    (58, 11, 123),
    (59, 16, 140),
    (60, 16, 240),
    (63, 11, 133),
    (95, 16, 300),
    (103, 16, 214),
    (105, 16, 214),
    (107, 16, 214),
    (109, 16, 214),
    (132, 11, 332),
]
