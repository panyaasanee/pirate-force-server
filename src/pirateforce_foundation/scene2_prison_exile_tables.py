"""Bg0002 (Prison Exile Island) placement roster - LANE-A build order M1-P.

RE-173 CORRECTION (round yfbqmg->this round, RE result 2026-09-01T03:03+07:00).
Placement 63 ("Columbus", ``MOBSET_36 01``) was originally built by taking its
Mob-Set number (36) directly as ``MOBS.n_ID``, the same rule every other row
in this table uses.  RE-173's CLINE crosswalk (scene 2's ``n_CLINE_TYPE=2``,
key ``(2,36)`` in ``CONSTDATA_TH__CLINE.tsv``) resolves that Mob-Set number to
``n_LEADER_BK1=360``, a DIFFERENT, real ``MOBS.n_ID`` row (also named
Columbus, same outfit) that ``world_m2_sea_destination.COLUMBUS_ROUTES``
already named for this home scene - the two tables were pointing at two
different real rows for the same island's Columbus.  This round regenerates
placement 63 from MOBS 360 per RE-173's BUILD_IMPACT (id, level range, walk
speed, derived max_hp - outfit/name/title/rank/AI/drops are unchanged,
RE-173 confirmed those columns match between MOBS 36 and 360).  RE-173 did
NOT re-audit the other 96 known placements' Mob-Set-number-as-n_ID
assumption - that stays an open question for a future round/ticket, not
something this fix answers.

HAND-ASSEMBLED THIS ROUND, NOT MACHINE-GENERATED.  ``field_mob_tables.py`` is
written by ``tools/pf_mine_scene_mob_roster.py``, which lives in ``tools/`` -
outside this lane's write zone this round.  Rather than touch that directory
without a mandate, the join below was run by hand against the exact same
committed tables that tool already reads, with the exact steps recorded so a
future ``tools/pf_mine_scene2_prison_exile_roster.py`` can reproduce every row
mechanically.  The digests below are what a regenerate must match.

SOURCES (bridge clone, sha256 at read time)
    placements   gamedata/scene/Bg0002/Bg0002.placements.tsv
                 e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f
    mobs         gamedata/tables/CONSTDATA_TH__MOBS.tsv
                 3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b
    standard_mob gamedata/tables/CONSTDATA_TH__STANDARD_MOB.tsv
                 4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925
    mobs_tip     gamedata/tables/TEXTDATA_TH__MOBS_TIP.tsv
                 e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f
(``mobs``/``standard_mob``/``mobs_tip`` are the SAME three files
``field_mob_tables.py`` already pins for bg0001 - same digests, checked again
here rather than assumed, because a hand join has no generator to catch drift.)

THE JOIN, EXACTLY, SO IT CAN BE MECHANISED LATER
1. Read every row of the placements TSV.  Its ``name`` column is
   ``"MOBSET_<NN> <MM>"`` (NN = a set number, MM = the instance within that
   set) - NOT ``bg0001``'s ``Mob_Set_<NN>`` naming, and the two must not be
   confused: bg0001's ordinal is checked (``field_mob_tables.py``'s own
   ``--verify-frozen``) against the frozen 115-row v141 table and matches it
   exactly; Bg0002 has no frozen table to check against, so NN here is a
   STRONG HYPOTHESIS, not an established identity - see ``ANCHOR REPORT``
   below and do not skip it.
2. The placements TSV ALSO carries a ``template_ids`` column.  Every single
   row's ``template_ids`` equals the NN parsed out of its own ``name`` column
   (checked for all 106 rows while building this table) - the two are the
   same underlying value, not independent evidence of each other.
3. NN is looked up in ``CONSTDATA_TH__MOBS.n_ID``.  One NN in this file (37,
   "Port transportation") has NO row in MOBS at all - MOBS_TIP names it but
   MOBS carries no outfit/level/rank for it, so it cannot be built into an
   actor entry and is UNRESOLVED, not placed, not guessed.
4. Four NN values (101, 102, 103, 104 - 8 placements total, NOT 5: see
   ``COUNT DISCREPANCY WITH THE OWNER'S LETTER`` below) are OUTSIDE the 1-41
   block the owner's evidence covers.  PANYA-DECISION 2026-08-27 20:10 is
   explicit: their meaning is unknown and they must not be placed or guessed.
   They are recorded as UNRESOLVED with that reason, at their real XYZ, so a
   later round that DOES learn what they are does not have to re-mine the
   file.
5. For every remaining row, ``visual_preset`` is ``MOBS.s_OUTFIT`` (see
   ``AMBIGUOUS OUTFIT`` below for the 53 rows where that field is a
   semicolon-separated list), ``display_name``/``title`` are
   ``MOBS_TIP.s_NAME``/``s_TITLE`` for that NN, and ``max_hp`` is
   ``STANDARD_MOB[MOBS.n_LEVEL_MIN].n_HPMAX`` - the exact derivation
   ``field_mob_tables.py`` already uses for bg0001, applied here to every row
   (not only the 13 that are monsters), because the table gives no other
   number to use and this project's rule is to derive from a real table
   rather than invent one.

COUNT DISCREPANCY WITH THE OWNER'S LETTER, STATED RATHER THAN SILENTLY FIXED.
PANYA-DECISION 2026-08-27 20:10 says "N = 101 if the 5 unknowns are cut".
Direct measurement of the placements TSV gives 106 total rows, of which 97
resolve to a named, buildable actor (KNOWN_PLACEMENTS below), 8 fall in the
101-104 block the owner marked unknown (not 5), and 1 more (NN 37) is
unresolved for an independent reason (no MOBS row at all - the owner's letter
does not mention this one).  97 + 8 + 1 = 106.  This module ships the
MEASURED 97, not the letter's 101; the discrepancy is for a human to reconcile
against her own count, not for this module to paper over.

AMBIGUOUS OUTFIT, NAMED RATHER THAN SILENTLY RESOLVED.  53 of the 97 known
rows have a MOBS.s_OUTFIT that is a semicolon-separated list of two or more
basenames (e.g. NN 3 "Navy soldier": ``P_MALE_002_000_SP1;P_MALE_002_000_PAK``).
bg0001's own mining tool REFUSES a placement whose outfit is such a list (that
refusal is exactly how it gets to "unambiguous"); this table has no such
per-instance disambiguation available (the placements TSV names an instance
only as "MM", not by which outfit variant it wears), so this module picks the
FIRST listed outfit for every ambiguous row and records ``ambiguous_outfit =
True`` on it.  That is a DEFAULT, not a measurement: the body a real client
would show for outfit-ambiguous instances 2..N of a set is unverified, and
``ambiguous_outfit`` exists so nothing downstream can forget that.

ANCHOR REPORT - THE STRONG HYPOTHESIS IS NOT YET FULLY CONFIRMED.
PANYA-DECISION 2026-08-27 20:10 names 7 anchors and forbids treating "NN =
MOBS.n_ID" as fact until all 7 match under one transform (HUD_x = placement_x,
HUD_y = placement_y - see the CORRECTION paragraph for why this is an
identity, not a sign flip).  Three of the anchors were previously
"photographic (evidence_screens/*.jpg this lane did not open)" - this round
opened all three committed files (no new capture, same evidence, first read):

CORRECTION (round 5irwkp, 2026-08-27).  The transform above was previously
documented as "negate X, keep Y", re-derived from Veronica's HUD reading.
Re-reading the SAME screenshot this round at higher zoom
(``pf_bridge/evidence_screens/REF_ORIGINAL_SERVER_PrisonExile_Veronica_
ApprenticeWitch_20260827.jpg``) shows the minimap actually prints
``X:-3,825`` - a minus sign the earlier description dropped, not a new
observation or a different frame.  Comparing that against Veronica's own
placement (-3598.77, 12550.46) with NO sign flip gives the SAME 248.76-unit
match distance as before (the old sign flip was self-cancelling for this one
anchor - both her HUD X and her placement X are negative - which is exactly
how the wrong transform rule went unnoticed).  The two transforms diverge for
every OTHER anchor, though: under the old (wrong) rule, Sebastian's placement
X of +23184.36 would predict a NEGATIVE HUD X.  This lane tried to read
Sebastian's own screenshot the same way at multiple zoom levels and filters
and could NOT do it with confidence either way - the frame is materially more
JPEG-compressed than Veronica's, and a stray minus-sign-shaped compression
artefact is exactly the kind of thing this lane will not treat as a digit.
No sign claim is made for Sebastian's HUD reading at all - see NAME/TITLE
MATCH below for what this lane could actually confirm from that photo.

* Veronica (NN 14): HUD (-3825, 12447) vs placement (-3598.77, 12550.46).  No
  sign flip: delta_x 226.23, delta_y 103.46, distance 248.76.  MATCHES the
  letter's own "227/103" to within rounding - the transform's sign convention
  changed, the match itself did not.  CONFIRMED (numeric).
* Legend Jack (6) / Legend Jack Men (7, x2) / Mountain Deer (27 instance 2):
  pairwise distances 601-1647 units - the group clusters together as the
  letter's screenshot describes, and the same evidence_screens/*.jpg image
  (opened this round) shows all four nameplates together in one frame:
  "Legend Jack" (Drunken Captain), "Legend Jack Men" x2, "Mountain Deer".
  CONFIRMED (numeric, clustering only - not a HUD coordinate match, because
  no HUD reading for this group was quoted to this lane).
* Navy Transfer (1) and Warden Sebastian (2) / Goliaon: opened this round -
  the SAME frame (``REF_ORIGINAL_SERVER_PrisonExile_NavyTransfer_at_dock_
  gate_20260827.jpg``) shows both nameplates together at what the image's own
  UI labels the "Prison Exile Island" entry gate: "Navy Transfer" close by,
  "Warden / Sebastian / Goliaon" visible through the gate opening beyond.
  Their placements measure 3079.9 units apart - the same order of magnitude
  as the already-accepted Columbus-Navy-Transfer pairing below.  SUPPORTIVE
  (numeric proximity + visual co-location in one frame), not a tight match -
  no HUD reading is legible in this frame either.
* Columbus (Mob-Set 36, MOBS n_id 360 since RE-173) near Navy Transfer (1):
  3935 units apart, both in the harbor quadrant - CONSISTENT, not a tight
  match; recorded as SUPPORTIVE, not CONFIRMED.
* Navy Transfer (1) sits 1147 units from the scene registry's ALREADY PINNED
  scene-2 arrival spawn (26905, 21185, 1680 -
  ``scenarios/world_scene_registry_001.json``) - SUPPORTIVE of "at the dock
  gate you arrive near", not a tight numeric match either.
* Sebastian (2) / Warden, and Pike (5) / Unemployed Sailor: opened this round
  for the first time.  Both screenshots' floating nameplates read EXACTLY the
  name/title pair this table already carries for those NN rows - "Warden" /
  "Sebastian" for NN 2, "Unemployed Sailor" / "Pike" for NN 5 - letter for
  letter, not a fuzzy match (checked programmatically against
  :data:`KNOWN_PLACEMENTS`, not eyeballed once and hardcoded - see
  ``PHOTO_NAME_TITLE_EVIDENCE`` / :func:`anchor_report`).  Pike's screenshot
  also shows a wooden-fenced enclosure with a lit torch, matching the
  letter's own "Pike in a wooden pen".  NEITHER frame has a legible HUD
  coordinate - both are far more JPEG-compressed than Veronica's; digit
  shapes are visible under 10x zoom but this lane will not quote numbers it
  cannot read with confidence.  NAME/TITLE MATCH (visual, no coordinate) -
  weaker than a numeric anchor, stronger than "not opened".  ("Goliaon"
  itself never appears in MOBS_TIP for NN 1-41 and is read as a scene
  prop/object, not an NPC placement - it is not and cannot be a row in this
  table; that stays true after opening the photo.)

So, after this round: 2 of 7 anchors are numerically confirmed, 3 are
supportive-but-not-tight (one new this round: Navy Transfer near Sebastian),
and 2 are name/title-confirmed-but-not-numeric (both new this round:
Sebastian, Pike).  Zero anchors remain entirely unopened.  THIS MODULE STILL
DOES NOT DECLARE "NN = MOBS.n_ID" A FACT - every anchor checked, in either
round, supports the hypothesis and none contradicts it, but a human
confirming names/positions in person (the M1-P headless-then-attended gate)
is still what promotes this from hypothesis to fact, exactly as the owner's
own letter requires.  What remains is upgrading name/proximity matches to
numeric HUD matches, which needs either a higher-resolution capture or the
attended session itself - not something this lane can manufacture from the
same compressed frames twice.
"""

from __future__ import annotations


SCENE = "Bg0002"
SCENE_N_ID = 2
NAMING_SCHEME = "MOBSET_NN_MM_joined_to_MOBS_n_ID_equals_NN"
NAMING_SCHEME_STATUS = "strong_hypothesis_not_yet_confirmed_see_module_docstring"

SOURCE_DIGESTS = {
    "placements": (
        "e57841a7018b46ff50d31972e5ba0846612548288446fe8514d819a99be92f8f"
    ),
    "mobs": "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b",
    "standard_mob": (
        "4b2db7f9553c877c2ec471105754dd08982d9e80027cc468c1ceaee840d68925"
    ),
    "mobs_tip": "e25ac667c9029e07752fbfd5d13b548d2e62ea439936884f30187c0c553ce38f",
}

TOTAL_PLACEMENT_COUNT = 106
KNOWN_COUNT = 97
UNRESOLVED_COUNT = 9

# (placement_index, mm_instance, n_id, x, y, z, visual_preset, ambiguous_outfit,
#  display_name, title, level, level_max, rank, ai_wander, ai_combat,
#  speed_walk, max_hp, drops_normal, drops_equipment, drops_specially)
KNOWN_PLACEMENTS = [
    (0, 1, 1, 26078.626953125, 20389.92578125, 1735.293212890625, 'P_MALE_002_000_SP1', False, 'Navy Transfer', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (1, 1, 2, 23184.359375, 19336.71875, 1609.9774169921875, 'M010_001_000_N', False, 'Sebastian', 'Warden', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (2, 1, 3, 22630.751953125, 19938.427734375, 1619.0377197265625, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (3, 2, 3, 23386.4921875, 18592.341796875, 1608.38134765625, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (4, 3, 3, 17269.48828125, 15389.970703125, 2629.2978515625, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (5, 4, 3, 16271.927734375, 16683.76171875, 2617.783935546875, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (6, 1, 4, 19720.865234375, 19165.541015625, 1948.2030029296875, 'M015_000_000_SP1', False, 'Mo Yuzi', 'Naval Communications Bureau', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (7, 1, 5, 8691.017578125, 14834.017578125, 2642.457275390625, 'P_MALE_002_000_PAK', False, 'Pike', 'Unemployed Sailor', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (8, 1, 6, -8020.60009765625, 14586.2724609375, 829.67138671875, 'M001_000_000_SP3', False, 'Legend Jack', 'Drunken Captain', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (9, 1, 7, -8607.048828125, 14735.7958984375, 853.923828125, 'M001_000_000_SP1', False, 'Legend Jack Men', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (10, 2, 7, -7542.51416015625, 14951.322265625, 762.3306884765625, 'M001_000_000_SP1', False, 'Legend Jack Men', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (11, 1, 8, 4841.908203125, 2042.11572265625, 2407.792724609375, 'P_MALE_015_000_EDMON', False, 'Edmund', 'Witch Servant', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (12, 1, 9, -13335.009765625, -3996.00927734375, 5444.470703125, 'M001_000_001_SP3', False, 'Baboza', 'Madman Captain', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (13, 1, 10, -12784.14453125, -3994.05126953125, 5463.44482421875, 'M001_000_001_SP1', False, 'Baboza Men', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (14, 2, 10, -13361.701171875, -3565.4052734375, 5303.68701171875, 'M001_000_001_SP1', False, 'Baboza Men', '', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (15, 1, 11, -13581.6181640625, 516.99462890625, 4636.27099609375, 'P_MALE_015_000_X', False, 'X', 'Mystery Prisoner', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (16, 1, 12, -11158.27734375, -3970.618896484375, 5647.021484375, 'P_MALE_015_000_PAUL', False, 'Paul', 'Prison Gourmet', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (17, 1, 13, -11269.046875, -4258.24853515625, 5646.66943359375, 'M009_000_000_N', False, 'Odyssey', 'Witch Pirate', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (18, 1, 14, -3598.773681640625, 12550.455078125, 1845.3502197265625, 'P_FEMALE_012_000_VENONIKA', False, 'Veronica', 'Apprentice Witch', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (19, 1, 15, -9898.947265625, -3653.611083984375, 5659.7412109375, 'M074_000_001_N', False, 'Ferryman', 'Old Prisoner', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (20, 1, 16, -9287.0751953125, -5607.0859375, 5683.60205078125, 'P_MALE_015_000_SLAVE', False, 'Silly Pirate Prisoner', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (21, 1, 17, 9623.029296875, -8649.7626953125, 1399.2135009765625, 'P_MALE_015_000_SLAVE', False, 'Panic Pirate Prisoner', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (22, 1, 18, 4753.75341796875, -18173.619140625, 781.364501953125, 'M001_003_000_N', False, 'Thin', 'The Shipbuilding', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (23, 1, 19, 3269.935791015625, -19804.92578125, 593.609375, 'P_MALE_015_000_MATT', False, 'Matt', 'Fisherman', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (24, 1, 20, 10916.84765625, -12537.2060546875, 2493.982421875, 'P_MALE_009_000_JEFFERY', False, 'Jefferson', 'Bomber', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (25, 1, 21, 14859.78125, -10716.626953125, 2636.1748046875, 'P_MALE_015_000_X', False, 'X', 'Honorable Prisoners', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (26, 1, 22, 2378.70849609375, -17568.30078125, 693.63427734375, 'P_MALE_003_000_CLOUS', False, 'Kraus', 'Decadent Pirates', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (27, 1, 23, 11527.1787109375, -21149.78125, 1173.004150390625, 'P_MALE_015_000_SEVEN', False, 'Seven', 'Prison Teller', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (28, 1, 24, 15329.197265625, 2249.896728515625, 2227.724853515625, 'M001_001_000_SP3', False, 'Kuck', 'Miner', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (29, 1, 25, 15685.21484375, 1537.111328125, 2246.56103515625, 'M009_000_000_N', False, 'Odyssey', 'Pride', 20, 20, 0, 2, 0, 150, 1771, 0, 0, 0),
    (30, 1, 26, 13329.1689453125, 1803.8544921875, 2222.47705078125, 'P_MALE_015_000_SLAVE', False, 'Attempt to escape pirate Prisoner', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (31, 1, 28, 6924.79833984375, 11621.9033203125, 2491.86376953125, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (32, 2, 28, 7540.783203125, 9423.3486328125, 2339.728515625, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (33, 33, 28, 7904.90673828125, 7103.75732421875, 2399.0791015625, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (34, 44, 28, 7402.69091796875, 4605.966796875, 2431.791015625, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (35, 55, 28, 4553.7744140625, 2544.940673828125, 2383.078125, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (36, 3, 27, 3124.040283203125, 378.0357971191406, 2299.1484375, 'M005_000_000_SP1', True, 'Mountain Deer', '', 17, 19, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (37, 4, 27, 682.3438720703125, 1555.4178466796875, 2927.33740234375, 'M005_000_000_SP1', True, 'Mountain Deer', '', 17, 19, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (38, 1, 27, -5054.56982421875, 13031.8916015625, 1343.759765625, 'M005_000_000_SP1', True, 'Mountain Deer', '', 17, 19, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (39, 2, 27, -8637.4619140625, 13720.3984375, 867.1171875, 'M005_000_000_SP1', True, 'Mountain Deer', '', 17, 19, 1, 16, 150, 100, 1201, 2701001, 5400001, 2802222),
    (40, 1, 29, -5655.052734375, 1122.0823974609375, 3414.732421875, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (41, 2, 29, -7929.8720703125, 2489.582763671875, 3621.234130859375, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (42, 3, 29, -3454.65234375, -2209.150390625, 4429.8564453125, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (43, 1, 30, 20340.9921875, -11901.7119140625, 511.68829345703125, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (44, 3, 33, -5033.64111328125, -12530.1669921875, 4164.88330078125, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (45, 4, 33, -8911.7939453125, -14937.2421875, 3571.885009765625, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (46, 4, 30, -10866.1005859375, -18732.95703125, 2222.3076171875, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (47, 5, 30, -14330.3974609375, -19398.423828125, 2082.44189453125, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (48, 6, 30, 20598.708984375, -8844.66796875, 497.8904113769531, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (49, 7, 30, 19908.462890625, -4308.9296875, 510.07379150390625, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (50, 1, 31, -13085.171875, -19977.615234375, 2012.8807373046875, 'M011_000_000_SP3', False, 'Tornado Eagle', '', 27, 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (51, 1, 33, 9501.0439453125, -6198.6337890625, 1224.273681640625, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (52, 2, 33, 8349.6513671875, -11477.1435546875, 1509.3643798828125, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (53, 1, 32, 4840.14208984375, -16955.1328125, 924.340576171875, 'M006_000_000_SP1', True, 'Rock turtle', '', 23, 25, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    (54, 5, 33, -249.96929931640625, -11861.9306640625, 3094.955078125, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (55, 3, 30, 9124.7275390625, -21878.76953125, 995.5101928710938, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (56, 8, 30, 13341.11328125, -21878.73046875, 659.9921264648438, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (57, 2, 30, 17032.955078125, -18020.771484375, 565.7628784179688, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (58, 1, 34, 18879.498046875, 1349.995361328125, 742.139404296875, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (59, 2, 34, 18530.75390625, 6839.6767578125, 966.080322265625, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (60, 3, 34, 21421.005859375, 9277.1123046875, 590.6787719726562, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (61, 1, 35, 19111.2265625, -1607.8365478515625, 716.8709716796875, 'M025_001_000_BOSS', False, 'Fighting Fish Sergeant', '', 27, 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (62, 2, 32, -1726.652587890625, -19164.966796875, 564.5496826171875, 'M006_000_000_SP1', True, 'Rock turtle', '', 23, 25, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    # RE-173 CORRECTION: n_id 36->360, level 35/35->10/20, speed_walk
    # 150->400, max_hp 7980->421 - MOBS 360 is the CLINE-resolved row, not
    # the raw Mob-Set number.  Outfit/name/title/rank/AI/drops unchanged
    # (RE-173 confirmed those columns match between MOBS 36 and 360).
    (63, 1, 360, 29414.7890625, 22476.69921875, 766.94921875, 'M055_000_000_N', False, 'Columbus', 'Marine Transport Station', 10, 20, 0, 2, 0, 400, 421, 0, 0, 0),
    (64, 1, 38, 17218.734375, 17678.404296875, 2492.981689453125, 'P_FEMALE_001_001_RENA', False, 'Reyna', 'Spice Merchant', 35, 35, 0, 1, 0, 150, 7980, 0, 0, 0),
    (66, 5, 3, 16001.2880859375, 14566.0546875, 2515.841064453125, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (67, 1, 39, -10690.4873046875, -4295.1767578125, 5658.3505859375, 'M015_000_000_SP2', False, 'Mo Yuzi', 'Naval Communications Bureau', 35, 35, 0, 2, 0, 150, 7980, 0, 0, 0),
    (68, 1, 40, 17542.94140625, 5782.64404296875, 950.5944213867188, 'P_MALE_001_001_KARL', False, 'Carle', 'Nautilus Leader', 35, 35, 0, 1, 0, 150, 7980, 0, 0, 0),
    (69, 6, 33, 8191.88232421875, -4096.4951171875, 1863.89111328125, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (70, 5, 29, -8426.798828125, 426.71600341796875, 4405.99853515625, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (71, 4, 29, -9559.884765625, 2990.335205078125, 3840.907470703125, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (72, 9, 30, 20015.45703125, -6608.15185546875, 579.5313110351562, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (73, 10, 30, 15271.048828125, -20091.658203125, 598.2581787109375, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (74, 11, 30, 11696.0439453125, -21716.974609375, 896.9006958007812, 'M011_000_000_SP1', True, 'Desert Eagle', '', 25, 27, 1, 16, 210, 100, 3138, 2701001, 5400001, 2802234),
    (75, 7, 33, 4724.2880859375, -1465.498291015625, 2178.907958984375, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (76, 9, 33, 2360.637451171875, 1690.940673828125, 2691.794921875, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (77, 2, 31, -10755.2109375, -19645.896484375, 2102.639892578125, 'M011_000_000_SP3', False, 'Tornado Eagle', '', 27, 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (78, 3, 31, -15819.3173828125, -19490.04296875, 2092.069580078125, 'M011_000_000_SP3', False, 'Tornado Eagle', '', 27, 27, 1, 16, 214, 100, 3857, 2701001, 5400001, 2802234),
    (79, 2, 35, 18347.130859375, 6794.07177734375, 985.388671875, 'M025_001_000_BOSS', False, 'Fighting Fish Sergeant', '', 27, 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (80, 3, 35, 19162.310546875, 1337.4029541015625, 708.5288696289062, 'M025_001_000_BOSS', False, 'Fighting Fish Sergeant', '', 27, 27, 1, 16, 352, 100, 3857, 2701001, 5400001, 2802264),
    (81, 6, 29, -9434.8642578125, 796.3521728515625, 4436.84423828125, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (82, 8, 33, 6788.8017578125, -3051.13525390625, 2117.647705078125, 'M000_000_001_SP1', True, 'Sediment Wolf', '', 19, 21, 1, 16, 100, 100, 1569, 2701001, 5400001, 2802202),
    (83, 3, 28, 5726.9091796875, 3208.04736328125, 2385.8447265625, 'M001_000_000_N', True, 'Drunk wolf pirates', '', 16, 18, 1, 16, 110, 100, 1054, 2701001, 5400001, 0),
    (84, 7, 29, -11636.51171875, 1761.240478515625, 4462.7490234375, 'M001_000_001_SP1', True, 'Lion pirates', '', 19, 21, 1, 16, 110, 100, 1569, 2701001, 5400001, 0),
    (85, 3, 32, 1206.410400390625, -19004.802734375, 529.0416259765625, 'M006_000_000_SP1', True, 'Rock turtle', '', 23, 25, 1, 16, 164, 100, 2525, 2701001, 5400001, 2802228),
    (86, 4, 34, 20485.072265625, 8018.71337890625, 623.4412231445312, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (87, 5, 34, 18747.009765625, 5091.45166015625, 963.4185180664062, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (88, 6, 34, 19234.421875, 2805.1865234375, 849.1326293945312, 'M025_001_000_N', False, 'Fighting Fish soldier', '', 25, 27, 1, 16, 350, 100, 3138, 2701001, 5400001, 2802264),
    (91, 1, 41, 15623.923828125, 16146.267578125, 2548.3642578125, 'P_MALE_010_000_MARTIN', False, 'Martin', 'Commander', 35, 35, 0, 1, 0, 150, 7980, 0, 0, 0),
    (98, 6, 3, 7668.98046875, 7253.71875, 2352.601318359375, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (99, 7, 3, 14890.9775390625, 1068.11572265625, 2256.73291015625, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (100, 8, 3, 19427.466796875, -3220.5283203125, 508.7738952636719, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (101, 9, 3, 19822.87890625, -13487.4609375, 515.6417236328125, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (102, 10, 3, 12831.8359375, -11733.3876953125, 2521.014892578125, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (103, 11, 3, 389.71600341796875, -17971.91796875, 544.1934204101562, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (104, 12, 3, -9858.1005859375, -4983.369140625, 5609.0, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
    (105, 13, 3, -13152.33203125, -14155.1396484375, 5147.56982421875, 'P_MALE_002_000_SP1', True, 'Navy soldier', '', 20, 20, 0, 1, 0, 150, 1771, 0, 0, 0),
]

# (placement_index, n_id, mm_instance, x, y, z, reason)
UNRESOLVED_PLACEMENTS = [
    (65, 37, 1, 20123.71484375, 19428.177734375, 1934.6551513671875, 'no_mobs_row_for_this_n_id_no_body_data'),
    (89, 102, 1, 18343.75390625, -7367.54443359375, 421.8689880371094, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (90, 101, 1, 2472.8193359375, -19546.435546875, 606.6259765625, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (92, 103, 1, 17870.701171875, 6142.2685546875, 946.0828857421875, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (93, 103, 2, 17646.60546875, 5751.74072265625, 1472.725830078125, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (94, 103, 3, 17927.32421875, 5449.716796875, 920.7349853515625, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (95, 103, 4, 17194.107421875, 6104.9345703125, 1016.1411743164062, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (96, 103, 5, 17243.01171875, 5434.12158203125, 979.5286254882812, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
    (97, 104, 1, 2623.90478515625, 2412.135986328125, 2608.84326171875, 'n_id_101_104_block_meaning_unknown_owner_says_do_not_place'),
]


from dataclasses import dataclass
import math
from typing import Any

_FLOAT32_MAX = 3.4028234663852886e38


class Scene2TableError(ValueError):
    """A refusal from this module, always with a reason in the message."""


@dataclass(frozen=True)
class Bg0002Placement:
    """One Bg0002 placement resolved to a real, named, bodied actor."""

    placement_index: int
    mm_instance: int
    n_id: int
    x: float
    y: float
    z: float
    visual_preset: str
    ambiguous_outfit: bool
    display_name: str
    title: str
    level: int
    level_max: int
    rank: int
    ai_wander: int
    ai_combat: int
    speed_walk: int
    max_hp: int
    drops_normal: int
    drops_equipment: int
    drops_specially: int

    @property
    def actor_identity(self) -> int:
        # Same formula bg0001's census already uses (population.py's
        # SceneActorPlacement.actor_identity).  Never sent in the same
        # generation as the bg0001 census -- each scene's builder refuses
        # any scene id but its own -- so the two identity spaces sharing
        # numbers is not a collision in practice, only in the abstract.
        return 0x2000 + self.placement_index + 1


@dataclass(frozen=True)
class Bg0002UnresolvedPlacement:
    """One placement this round could not, and did not, turn into an actor."""

    placement_index: int
    n_id: int
    mm_instance: int
    x: float
    y: float
    z: float
    reason: str


def _require_float32(value: Any, label: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise Scene2TableError("%s must be a finite float32 value" % label)
    result = float(value)
    if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
        raise Scene2TableError("%s must be a finite float32 value" % label)
    return result


def _require_int(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or type(value) is bool or not low <= value <= high:
        raise Scene2TableError("%s must be an integer in [%d,%d]" % (label, low, high))
    return value


# CLINE-resolved MOBS ids that fall outside the default 1..41 Mob-Set number
# range this table's other 96 rows use directly (see the module docstring's
# "RE-173 CORRECTION" section).  Currently only placement 63 (Columbus)
# needs this - a future row that needs the same CLINE resolution should be
# added here one at a time, with its own citation.  This is deliberately
# NOT done by widening the range bound itself: RE-123's own fabrication
# guard (see ``test_scene2_prison_exile_tables.py``'s Mirage Reel tests,
# n_id 230) depends on the range staying tight for every row that has not
# been individually re-derived through the CLINE crosswalk.
CLINE_RESOLVED_N_IDS = frozenset({360})


def _require_n_id(value: Any) -> int:
    if type(value) is not int or type(value) is bool:
        raise Scene2TableError("n_id must be an integer in [1,41] or a CLINE-resolved id")
    if 1 <= value <= 41 or value in CLINE_RESOLVED_N_IDS:
        return value
    raise Scene2TableError("n_id must be an integer in [1,41] or a CLINE-resolved id")


def load_known_placements() -> tuple[Bg0002Placement, ...]:
    """Type-check and return the 97 resolved placements.  No file is read."""
    if len(KNOWN_PLACEMENTS) != KNOWN_COUNT:
        raise Scene2TableError("KNOWN_PLACEMENTS count drift")
    out: list[Bg0002Placement] = []
    seen: set[int] = set()
    for row in KNOWN_PLACEMENTS:
        if type(row) is not tuple or len(row) != 20:
            raise Scene2TableError("known placement row has the wrong shape")
        (idx, mm, n_id, x, y, z, preset, ambiguous, name, title, level,
         level_max, rank, ai_wander, ai_combat, speed_walk, max_hp,
         drops_normal, drops_equipment, drops_specially) = row
        idx = _require_int(idx, "placement index", 0, TOTAL_PLACEMENT_COUNT - 1)
        if idx in seen:
            raise Scene2TableError("duplicate placement index %d" % idx)
        seen.add(idx)
        if type(preset) is not str or not preset:
            raise Scene2TableError("placement %d: visual preset must be non-empty" % idx)
        if type(name) is not str or not name:
            raise Scene2TableError("placement %d: display name must be non-empty" % idx)
        if type(ambiguous) is not bool:
            raise Scene2TableError("placement %d: ambiguous_outfit must be bool" % idx)
        out.append(Bg0002Placement(
            placement_index=idx,
            mm_instance=_require_int(mm, "mm instance", 1, 0xFFFF),
            n_id=_require_n_id(n_id),
            x=_require_float32(x, "placement x"),
            y=_require_float32(y, "placement y"),
            z=_require_float32(z, "placement z"),
            visual_preset=preset,
            ambiguous_outfit=ambiguous,
            display_name=name,
            title=title if type(title) is str else "",
            level=_require_int(level, "level", 1, 255),
            level_max=_require_int(level_max, "level_max", 1, 255),
            rank=_require_int(rank, "rank", 0, 0xFFFF),
            ai_wander=_require_int(ai_wander, "ai_wander", 0, 0xFFFF),
            ai_combat=_require_int(ai_combat, "ai_combat", 0, 0xFFFF),
            speed_walk=_require_int(speed_walk, "speed_walk", 0, 0xFFFF),
            max_hp=_require_int(max_hp, "max_hp", 1, 0xFFFFFFFF),
            drops_normal=_require_int(drops_normal, "drops_normal", 0, 0x7FFFFFFF),
            drops_equipment=_require_int(drops_equipment, "drops_equipment", 0, 0x7FFFFFFF),
            drops_specially=_require_int(drops_specially, "drops_specially", 0, 0x7FFFFFFF),
        ))
    return tuple(out)


def load_unresolved_placements() -> tuple[Bg0002UnresolvedPlacement, ...]:
    """Type-check and return the 9 placements this round refused to guess."""
    if len(UNRESOLVED_PLACEMENTS) != UNRESOLVED_COUNT:
        raise Scene2TableError("UNRESOLVED_PLACEMENTS count drift")
    out: list[Bg0002UnresolvedPlacement] = []
    for row in UNRESOLVED_PLACEMENTS:
        if type(row) is not tuple or len(row) != 7:
            raise Scene2TableError("unresolved placement row has the wrong shape")
        idx, n_id, mm, x, y, z, reason = row
        if type(reason) is not str or not reason:
            raise Scene2TableError("placement %d: reason must be non-empty" % idx)
        out.append(Bg0002UnresolvedPlacement(
            placement_index=_require_int(idx, "placement index", 0, TOTAL_PLACEMENT_COUNT - 1),
            n_id=_require_int(n_id, "n_id", 1, 0xFFFF),
            mm_instance=_require_int(mm, "mm instance", 1, 0xFFFF),
            x=_require_float32(x, "placement x"),
            y=_require_float32(y, "placement y"),
            z=_require_float32(z, "placement z"),
            reason=reason,
        ))
    return tuple(out)


# ---------------------------------------------------------------------------
# ANCHOR VERIFICATION.  Computed from the table, not hardcoded, so a future
# edit to a row cannot silently leave a stale "it matched" claim behind.  See
# the module docstring's "ANCHOR REPORT" section for what each result means
# and what it does NOT mean.
# ---------------------------------------------------------------------------
VERONICA_N_ID = 14
# CORRECTED round 5irwkp (2026-08-27): was +3825.0.  A higher-zoom re-read of
# the same committed screenshot this round
# (pf_bridge/evidence_screens/REF_ORIGINAL_SERVER_PrisonExile_Veronica_
# ApprenticeWitch_20260827.jpg) shows the minimap prints "X:-3,825", not
# "X:3,825" - the minus sign the earlier round's description dropped.  See
# the module docstring's CORRECTION paragraph for why the match distance is
# unchanged even though the sign and the transform below both flipped.
VERONICA_HUD_X = -3825.0
VERONICA_HUD_Y = 12447.0
# How far the Veronica anchor is allowed to miss and still count as a match --
# set to the letter's own reported miss (227/103) plus a small margin, not to
# zero, because that is the exact size of error this lane can already explain
# (the letter attributes it to "the distance she was standing").
VERONICA_MATCH_TOLERANCE_UNITS = 260.0

LEGEND_JACK_N_ID = 6
LEGEND_JACK_MEN_N_ID = 7
MOUNTAIN_DEER_N_ID = 27
MOUNTAIN_DEER_CLUSTER_MM = 2
CLUSTER_RADIUS_UNITS = 1700.0

# RE-173: the CLINE-resolved MOBS id (360), not the raw Mob-Set number (36)
# every other anchor in this file still uses directly - see the module
# docstring's "RE-173 CORRECTION" section and CLINE_RESOLVED_N_IDS above.
COLUMBUS_N_ID = 360
NAVY_TRANSFER_N_ID = 1
COLUMBUS_NAVY_TRANSFER_MAX_UNITS = 5000.0

# NEW round 5irwkp: Navy Transfer and Sebastian appear together, one frame,
# at the scene-2 entry gate (see docstring).  Same tolerance order of
# magnitude as COLUMBUS_NAVY_TRANSFER_MAX_UNITS above, for the same reason
# (a "same quadrant, one screenshot" claim, not a tight coordinate claim).
SEBASTIAN_N_ID = 2
PIKE_N_ID = 5
NAVY_TRANSFER_SEBASTIAN_MAX_UNITS = 5000.0

# scenarios/world_scene_registry_001.json's OWN pinned scene-2 spawn -- copied
# here as a plain number, not imported, so this module stays a pure data
# module with no path/JSON dependency.  The test for this module cross-checks
# this constant against the live registry file so the two cannot drift apart
# in silence.
SCENE2_REGISTRY_SPAWN_X = 26905.0
SCENE2_REGISTRY_SPAWN_Y = 21185.0
NAVY_TRANSFER_SPAWN_MAX_UNITS = 1500.0

# NEW round 5irwkp: the two screenshots this round opened for the first time
# (evidence_screens/*.jpg, committed already, not a new capture).  Each
# entry's observed_name/observed_title is the exact floating-nameplate text
# read off that file; anchor_report() below checks it against
# KNOWN_PLACEMENTS programmatically rather than trusting this dict blindly,
# the same discipline the numeric anchors already use.
PHOTO_NAME_TITLE_EVIDENCE = {
    SEBASTIAN_N_ID: {
        "photo": (
            "pf_bridge/evidence_screens/"
            "REF_ORIGINAL_SERVER_PrisonExile_Warden_Sebastian_Goliaon_"
            "20260827.jpg"
        ),
        "observed_name": "Sebastian",
        "observed_title": "Warden",
    },
    PIKE_N_ID: {
        "photo": (
            "pf_bridge/evidence_screens/"
            "REF_ORIGINAL_SERVER_PrisonExile_Pike_UnemployedSailor_"
            "20260827.jpg"
        ),
        "observed_name": "Pike",
        "observed_title": "Unemployed Sailor",
    },
}


def hud_from_placement(x: float, y: float) -> tuple[float, float]:
    """The one transform this lane could re-derive: identity, no sign flip.

    CORRECTED round 5irwkp: previously documented (and coded) as "negate X,
    keep Y".  Re-derived again from the Veronica anchor, the only anchor this
    lane has a numeric HUD reading for - a higher-zoom re-read of the SAME
    screenshot shows her HUD X is itself negative ("X:-3,825"), which the
    earlier round's description missed.  Comparing that directly against her
    placement X (also negative, -3598.77) with no sign flip reproduces her
    reported HUD X to within the letter's own stated error, exactly as the
    old (wrong) flip-then-compare also happened to do for this one anchor
    (see the module docstring's CORRECTION paragraph for why that mistake
    went unnoticed).  No other axis combination was tried because no other
    anchor gives this lane a number to try it against.
    """
    return (float(x), float(y))


def _by_n_id(placements: tuple[Bg0002Placement, ...], n_id: int) -> list[Bg0002Placement]:
    return [p for p in placements if p.n_id == n_id]


def anchor_report() -> dict:
    """What this lane could check of PANYA-DECISION 2026-08-27 20:10's 7
    anchors, computed from :data:`KNOWN_PLACEMENTS` -- and, just as loudly,
    what it could NOT check.  ``all_seven_confirmed`` is always False here on
    purpose: even after round 5irwkp opened the three remaining screenshots,
    two of them (Sebastian, Pike) only yielded a name/title match, not a
    numeric one, and the letter's own rule is that the hypothesis is not fact
    until a human confirms all 7 in person.
    """
    placements = load_known_placements()

    veronica = _by_n_id(placements, VERONICA_N_ID)
    if len(veronica) != 1:
        raise Scene2TableError("Veronica anchor: expected exactly one n_id 14 row")
    hud_x, hud_y = hud_from_placement(veronica[0].x, veronica[0].y)
    delta_x = hud_x - VERONICA_HUD_X
    delta_y = hud_y - VERONICA_HUD_Y
    veronica_distance = math.hypot(delta_x, delta_y)
    veronica_match = veronica_distance <= VERONICA_MATCH_TOLERANCE_UNITS

    jack = _by_n_id(placements, LEGEND_JACK_N_ID)
    men = _by_n_id(placements, LEGEND_JACK_MEN_N_ID)
    deer = [p for p in _by_n_id(placements, MOUNTAIN_DEER_N_ID)
            if p.mm_instance == MOUNTAIN_DEER_CLUSTER_MM]
    if len(jack) != 1 or len(men) != 2 or len(deer) != 1:
        raise Scene2TableError("Legend Jack cluster anchor: unexpected row counts")
    cluster = [jack[0], men[0], men[1], deer[0]]
    cluster_pairs = []
    max_pair = 0.0
    for i in range(len(cluster)):
        for j in range(i + 1, len(cluster)):
            a, b = cluster[i], cluster[j]
            d = math.hypot(a.x - b.x, a.y - b.y)
            cluster_pairs.append(round(d, 1))
            max_pair = max(max_pair, d)
    cluster_match = max_pair <= CLUSTER_RADIUS_UNITS

    columbus = _by_n_id(placements, COLUMBUS_N_ID)
    navy = _by_n_id(placements, NAVY_TRANSFER_N_ID)
    if len(columbus) != 1 or len(navy) != 1:
        raise Scene2TableError("Columbus/Navy Transfer anchor: unexpected row counts")
    columbus_navy_distance = math.hypot(
        columbus[0].x - navy[0].x, columbus[0].y - navy[0].y)
    columbus_navy_match = columbus_navy_distance <= COLUMBUS_NAVY_TRANSFER_MAX_UNITS

    navy_spawn_distance = math.hypot(
        navy[0].x - SCENE2_REGISTRY_SPAWN_X, navy[0].y - SCENE2_REGISTRY_SPAWN_Y)
    navy_spawn_match = navy_spawn_distance <= NAVY_TRANSFER_SPAWN_MAX_UNITS

    sebastian = _by_n_id(placements, SEBASTIAN_N_ID)
    if len(sebastian) != 1:
        raise Scene2TableError("Sebastian anchor: expected exactly one n_id 2 row")
    navy_sebastian_distance = math.hypot(
        navy[0].x - sebastian[0].x, navy[0].y - sebastian[0].y)
    navy_sebastian_match = navy_sebastian_distance <= NAVY_TRANSFER_SEBASTIAN_MAX_UNITS

    # NEW round 5irwkp: check the two name/title-only anchors programmatically
    # against KNOWN_PLACEMENTS, instead of trusting PHOTO_NAME_TITLE_EVIDENCE
    # by eye - if a future edit to a display_name/title ever drifts from what
    # this lane actually read off the screenshot, this is where that shows up.
    photo_name_title_matches = []
    for n_id, evidence in PHOTO_NAME_TITLE_EVIDENCE.items():
        rows = _by_n_id(placements, n_id)
        if len(rows) != 1:
            raise Scene2TableError(
                f"photo name/title anchor: expected exactly one n_id {n_id} row"
            )
        row = rows[0]
        match = (
            row.display_name == evidence["observed_name"]
            and row.title == evidence["observed_title"]
        )
        photo_name_title_matches.append({
            "n_id": n_id,
            "table_name": row.display_name,
            "table_title": row.title,
            "observed_name": evidence["observed_name"],
            "observed_title": evidence["observed_title"],
            "photo": evidence["photo"],
            "match": match,
        })

    return {
        "hypothesis": NAMING_SCHEME,
        "hypothesis_status": NAMING_SCHEME_STATUS,
        "all_seven_confirmed": False,
        "confirmed_numeric": [
            {
                "name": "veronica_hud",
                "n_id": VERONICA_N_ID,
                "hud": [round(hud_x, 2), round(hud_y, 2)],
                "target": [VERONICA_HUD_X, VERONICA_HUD_Y],
                "distance": round(veronica_distance, 2),
                "match": veronica_match,
            },
            {
                "name": "legend_jack_men_deer_cluster",
                "n_ids": [LEGEND_JACK_N_ID, LEGEND_JACK_MEN_N_ID, MOUNTAIN_DEER_N_ID],
                "pairwise_distances": cluster_pairs,
                "max_pairwise_distance": round(max_pair, 1),
                "match": cluster_match,
            },
        ],
        "supportive_not_tight": [
            {
                "name": "columbus_near_navy_transfer",
                "distance": round(columbus_navy_distance, 1),
                "match": columbus_navy_match,
            },
            {
                "name": "navy_transfer_near_scene2_registry_spawn",
                "distance": round(navy_spawn_distance, 1),
                "match": navy_spawn_match,
            },
            {
                "name": "navy_transfer_near_sebastian_same_frame",
                "distance": round(navy_sebastian_distance, 1),
                "match": navy_sebastian_match,
                "photo": (
                    "pf_bridge/evidence_screens/"
                    "REF_ORIGINAL_SERVER_PrisonExile_NavyTransfer_at_dock_"
                    "gate_20260827.jpg"
                ),
            },
        ],
        "name_title_confirmed_no_coordinate": photo_name_title_matches,
        "not_independently_verified": [
            "goliaon_is_a_scene_prop_not_an_npc_row_no_placement_to_verify",
        ],
    }
