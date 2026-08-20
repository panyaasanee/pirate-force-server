# LOOT-ROLL-001 -- Door 2 of the round-100 loot loop: a server-side loot roller, pure logic, no wire (GT-037)

2026-08-20 - chief round 100 queue item GT-037 - **pure server logic, offline, additive** - const data of record `B_CONSTDATA_TH.pc_.dec` SHA-256 `496DFB2EF2CF517482A7B426C9DD5EDF0278564FE11195B96F36DF90607F0D2D` (client data version 1.41.0000, built 2014-12-11), read only through the committed fact pack.

Reproduce: `py -3 tools/verify_loot_roller.py` (30 guards, exit 0), `py -3 -m pytest tests/test_loot_roll.py -q` (66 tests, 71 subtests).

> **This is OUR design, not a recovery.** The original Pirate Force server is
> closed, was never published, and left no capture of a monster dropping
> anything. The drop MODEL below is client-shipped data; the ROLL is ours. The
> original server's roll order and RNG are unrecoverable forever, and nothing
> here claims otherwise. Nothing in this checkpoint has ever touched a wire, a
> client, or a database, and nothing here can reach a player: Doors 3 and 4 of
> the loot loop (a ground object appearing, and pickup) still have NO known
> wire path.

## 0. What this checkpoint is, and why it is the only buildable door

The round-100 draft `drafts/MONSTER_SPAWN_LOOT_STATIC_AND_DESIGN_R100_20260820.md`
ranked the six doors a monster-loot loop needs and found exactly one buildable
today with no wire and no guessing:

* Door 1 (monster exists, is hostile, dies) is already ours.
* **Door 2 (what it drops -- the roll) is buildable now as pure server logic.**
* Door 3 (a lootable object appears) has NO known path: the actor-entry jump
  table `0x4469BD` accepts only actor_type 2..6 and has no item/object type;
  `DropThingGameObj` / `DropThingBoard` / `DropThingModule_Client` are
  registration NAMES with no transport, serializer, producer or capture.
* Door 4 (pickup) is `PickupTerrainThing`, a name-grade lead only.
* Door 5 (display a granted item) is static-only; Door 6 (persist it) has no
  writer.

This checkpoint is Door 2 and nothing else. It is section 5 proposal 1 of that
draft, built as proposed: a census-free module, its excerpt fixture, its
independent verifier, its tests, this report.

## 1. Provenance chain

The ONLY data source used is the committed round-100 fact pack
`FACTPACK_R100_CONSTDATA_MONSTER_LOOT.md` section 5 ("LOOT"), which itself
derives from `B_CONSTDATA_TH.pc_.dec` (8,443,000 bytes, sha256 `496DFB2E..0D2D`).
**The client image and the const-data blob do not exist on this machine and are
never required** by the module, the fixture, the tests or the verifier -- the
suite has no new precondition and no new skip.

What the chain carries, tagged the way the module tags it:

* **[PROVEN]** `MOBS.n_DROPS_* = prefix * 100000 + n_ID` of a row in the
  matching table: prefix 27 DROPS_NORMAL (62/62 low parts resolve), 28
  DROPS_SPECIALLY (107/107), 54 DROPS_EQUIPMENT (36/36), 87 DROPS_QUEST
  (311/2478 only).
* **[PROVEN]** item ids use the same scheme keyed on the item-category table:
  22 EQUIPMENT_BASE (2200201 -> 201), 24 ITEM_CONSUMABLES (2400046 -> 46),
  25 ITEM_QUEST (2500021 -> 21), 26 ITEM_MISC (2600041 -> 41).
* **[STATIC]** DROPS_NORMAL (049, 267 x 121) = `n_ID` + 30 slots of
  `(n_ITEM, f_RATE, n_MIN, n_MAX)`, per-slot independent percentage rates.
* **[STATIC]** DROPS_EQUIPMENT (048, 53 x 44) = one roll at `f_DROPS_RATE`,
  then `n_NUMBER_MIN..n_NUMBER_MAX` weighted picks over up to 20
  `(n_ITEM, n_WEIGHT)` pairs.
* **[STATIC]** DROPS_SPECIALLY (050, 584 x 64) = the same shape, 30 entries.
* **[STATIC]** E_DROPS_QUALITY (054, 26 x 9) = White/Green/Blue/Purple/Orange
  weights by `n_MOB_RANK` + level band. **Row 1201 (rank 4096) is G700 B299 P1
  and sums to 1000, not 100.**
* **[INFERENCE]** `n_ITEM = 0` with a nonzero rate is the money slot. The fact
  pack marks this reading [INFERENCE]; so does every money drop this roller
  emits, by tag.
* **[NEGATIVE]** DROPS_QUEST: mobs reference 2478 distinct sets and only 311
  ship client-side, so ~87 pct of that model is absent.

## 2. What was built

`src/pirateforce_foundation/loot_roll.py` -- the roller. Pure server logic: it
sends nothing on the wire, opens no socket, touches no database, boots no
server, imports nothing from the runtime/dispatch layer (its whole import set
is `__future__, dataclasses, json, pathlib, random, types, typing`), and has
**no scenario flag**. It is deliberately unreachable from production dispatch:
`production_allowed = False`, `LOOT_ROLL_DISPATCH_REACHABLE = False`, and no
other module in `src/` mentions it. Importing it has no side effects.

The public surface:

* `load_loot_tables(path)` / `build_loot_tables(document)` -- strict loader.
  Every mapping it returns is a `MappingProxyType` of frozen dataclasses, so a
  roll cannot mutate its own inputs. A malformed excerpt is refused at load
  time with `LootTableError`, so a roll never reasons about impossible data.
* `decode_drop_set_id(raw, table, tables=None)` and `decode_item_id(raw)` --
  **total**: they return an `IdDecode` decision object and never raise. A wrong
  prefix for the table being addressed, a value of 0, a low part absent from
  the loaded table, a non-int, a negative, and a bool are each a NAMED refusal.
  There is no bare `KeyError` path and no silent skip.
* `rate_succeeds(rate, draw)` = `draw < rate / 100.0`.
* `uniform_quantity(low, high, draw)` = `low + int(draw * span)`, clamped.
* `weighted_pick(weights, draw)` -- an explicit cumulative-threshold walk in
  TABLE ORDER: the first index whose running sum strictly exceeds
  `draw * total`. No `random.choices`, no library internals; entry `i` owns
  exactly `[sum(w[:i]), sum(w[:i+1]))` of the target line, so every boundary is
  enumerable by hand. Normalization is by the ACTUAL sum, which is what makes
  row 1201 correct.
* `select_quality(tables, rank, level, draw)` -- the E_DROPS_QUALITY row whose
  rank matches and whose band contains the level, then a weighted pick.
* `roll_mob_loot(tables, mob, rng)` -- the whole roll. `rng` MUST be an
  injected `random.Random` (anything else refuses by name); every stochastic
  decision goes through `rng.random()` and nothing else; the module-global
  `random` is never called.
* `describe_loot_roll(result)` -- one ASCII line per decision. This is the
  canonical, pinned rendering.

Roll order (OURS, fixed, documented): DROPS_NORMAL slots in table order ->
DROPS_EQUIPMENT (gate roll, count, picks, quality per item) -> DROPS_SPECIALLY
(gate roll, count, picks) -> DROPS_QUEST refusal. The draw stream does not
depend on whether a row decodes: a slot that wins its rate roll consumes its
quantity draw even when its item id is then refused, and an equipment pick
consumes its quality draw even when its item id is then refused.

Nothing is ever silently dropped. A `LootRollResult` carries `drops`, `misses`
(every rate roll that did not fire), `refusals` (reason + table + detail), and
`padding_slots` (the unused columns of a fixed-width 30-slot row). The ten
refusal reasons are constants, all prefixed `loot_roll_refused_`, all ASCII,
all enumerated in `LOOT_ROLL_REFUSAL_REASONS`.

`tests/golden/loot_roll_tables_r100.json` -- the excerpt. It carries a
`provenance` block naming the fact pack, the const-data sha, the design draft,
the true shipped row counts, and the statement that the real tables live only
in client const data this machine does not have. Every row declares
`source: factpack_r100_section_5` or `source: composed_for_test`. Published
rows: DROPS_NORMAL 1 and 1001, DROPS_EQUIPMENT 1 (itself a truncated excerpt --
the shipped row has 15 entries and the fact pack prints only two ids, which is
said in the row's own note), DROPS_SPECIALLY 1, and all 26 E_DROPS_QUALITY
rows. All ten MOBS-shaped rows are composed-for-test and say so in their notes.
DROPS_ACTIVITY is deliberately not carried (this checkpoint does not implement
event-time layering); DROPS_QUEST is deliberately not carried and the loader
refuses an excerpt that adds it.

`tools/verify_loot_roller.py` -- an INDEPENDENT re-derivation in the house
verifier style. It re-implements the decoding rule, the three primitives, the
quality selection and the entire roll order from the raw JSON with its own
code, and only then compares text with the module. 30 guards in five sections:
(A) the id rule against EVERY id in the excerpt, both readers agreeing;
(B) the primitives at their boundaries; (C) E_DROPS_QUALITY, including that
exactly one published row is not normalized to 100 and that its boundaries walk
700/1000 and 999/1000; (D) eleven full deterministic rolls compared line for
line; (E) containment and excerpt honesty. It exits non-zero with the drifted
guard list and prints an ASCII-only summary.

## 3. What was measured

```
py -3 -m pytest tests/test_loot_roll.py -q
66 passed, 71 subtests passed in 0.28s

py -3 tools/verify_loot_roller.py
guards run: 30
RESULT: PASS   (exit code 0)

CI-shaped whole-suite run (43 client-image test modules excluded by
--ignore, the list built with grep -lE 'GameClient|capture_v141'):
992 passed, 4 skipped, 1371 subtests passed in 36.57s
  -- baseline without this checkpoint: 926 passed, 4 skipped, 1300 subtests
  -- the same 4 pre-existing preconditions skips, unchanged: two
     [precondition:canonical_db], one [precondition:login_req_capture], one
     [precondition:backups_tree].  No new skip, so no skip pin moves.
```

The pinned determinism claim: excerpt + composed mob 900001 + seed 332 renders
11 ASCII lines -- a consumable item drop, a money drop, a WHITE-graded
equipment drop, three DROPS_SPECIALLY drops, three named misses and the
DROPS_QUEST refusal -- and the test asserts them against a hard-coded list. A
SEPARATE process (`sys.executable -c`, independent hash seed) re-derives the
same text byte for byte, and the verifier re-derives it a third time with its
own code.

Negative controls run against the verifier to prove its guards bite (transient,
in-memory monkeypatching only -- no file was modified): flipping
`rate_succeeds` from `<` to `<=` turned section B red (2 guards); flipping the
cumulative walk from `>` to `>=` turned section C red on the 1201 boundaries;
shifting `uniform_quantity` by one turned sections B and D red, with section D
naming the first drifting mob and seed. Exit code 1 in all three.

## 4. Where the fact pack was ambiguous, and which reading was chosen

Every one of these is OUR DESIGN, is listed in the module's
`LOOT_ROLL_CHOSEN_READINGS`, and could reasonably have been read otherwise.

1. **Roll order across the three sets.** The fact pack gives four independent
   tables and no order. Chosen: NORMAL, EQUIPMENT, SPECIALLY, then the
   DROPS_QUEST refusal -- the order the fact pack lists them in section 5, so
   the pins have a documented reason rather than an arbitrary one. The order
   is load-bearing only for the RNG stream, not for the drop set itself.
2. **What "rate percent" compares against.** Chosen `draw < rate / 100.0`
   (strict). It makes 0 pct impossible and 100 pct certain without a special
   case, and puts the fractional threshold at an exactly representable place
   (0.5 pct -> 0.005) so a test can sit on either side of it. A `<=` reading
   would make 0 pct fire on a draw of exactly 0.0, which is why it was rejected.
3. **Uniform quantity in [min, max].** Chosen `low + int(draw * span)` with a
   clamp, a flat span over `max - min + 1` values. Nothing in the data says the
   distribution is flat; flat is the least-assumption reading.
4. **Multi-item weighted picks.** DROPS_EQUIPMENT and DROPS_SPECIALLY pick
   `n_NUMBER_MIN..n_NUMBER_MAX` items and the data does not say whether picks
   are with or without replacement. Chosen: independent picks WITH replacement
   (an entry may repeat). Without-replacement would need an invented rule for
   what happens when the count exceeds the entry list, and the shipped row 1
   (3 entries, 1..3 items) would then be a guaranteed sweep of the whole row.
5. **Which drops get a quality.** E_DROPS_QUALITY is described as
   "equipment-drop quality". Chosen: quality is attached ONLY to
   DROPS_EQUIPMENT results, not to DROPS_SPECIALLY results even when a
   specially entry carries an EQUIPMENT_BASE (prefix 22) item.
6. **How a quality row matches a rank.** `MOBS.n_RANK` is described as a
   bitmask (0, 1, 2, 4, 64, 128, 512, 4096 observed) and the E_DROPS_QUALITY
   rows enumerate single values (1, 2, 4, 8, ... 4096). Chosen: EXACT equality,
   not a bitmask test -- only `DROPS_ACTIVITY.n_MOBRANK` is documented as a
   bitmask (1, 6, 192, 4095). Consequence: a rank-0 mob (1506 of the 3210
   shipped rows) has NO quality row and its equipment drop carries a named
   refusal and no invented quality, rather than silently defaulting to White.
7. **The eight quality rows with no printed level band** (301, 401, 501, 801,
   901, 1001, 1101, 1201). The fact pack prints no band for them. Chosen:
   treat the band as unbounded AND tag every drop that used such a row with
   `inference_quality_row_level_band_not_published_treated_as_unbounded`, so
   the assumption is visible in the output rather than buried. The fixture
   records those bands as `null` with `band_published: false` rather than
   inventing 1..999.
8. **The effective mob level.** MOBS carries a level BAND; which level a
   particular spawned mob has is Door 1b (spawn), which does not exist. Chosen:
   the caller supplies the level (`mob_at_level`), and the loader defaults it
   to `n_LEVEL_MIN`.
9. **`n_DROPS_* == 0`.** This is the commonest shipped value and plainly means
   "this mob declares no such set". The brief required a named refusal for a
   zero id, and the honest way to have both is what is built: the zero is a
   first-class refusal (`loot_roll_refused_drop_set_id_zero`) carried on the
   result with a detail saying the mob declares no set -- reported, never
   silent, and never mistaken for an error in the data.

One more honest gap, not an ambiguity: DROPS_EQUIPMENT row 1 is a TRUNCATED
excerpt. The shipped row has 15 entries at weight 100; the fact pack prints
only two ids, so the fixture carries two and says so. Rolling that row here is
not rolling the shipped row, and the fixture note says that too.

## 5. Census, containment, and what did NOT move

* No coverage grade moves. `monster_spawn_and_loot` stays `not_started` -- the
  row's note is about spawn timers, respawn cycles, loot objects and pickup,
  and this checkpoint delivers none of those. Nothing renders.
* No ledger entry, no hypothesis id, no scenario file, no CLI flag, no
  dispatch branch, no migration, no manifest. This lane is not reachable from
  production dispatch at all, on purpose.
* No existing file was modified. The whole checkpoint is five NEW paths.
* The skip census is unmoved (no new precondition, no new skip), and no
  ownership guard is touched: the module names no wire vital, no chat vital, no
  music control, no actor-entry emitter, and no BasicAttr bit.
* **`.gitignore` needs two allowlist lines from the chief** (not added here,
  per the scope rule): `!/tools/verify_loot_roller.py` and
  `!/reports/PF_LOOT_ROLL001_SERVER_SIDE_ROLLER_20260820.md`. `/tools/*` and
  `/reports/*` are ignore-by-default with per-file allowlists; `src/**` and
  `tests/**` are already allowlisted, so the module, the tests and the fixture
  are tracked as written.

## 6. Grade and NONCLAIMS

**Grade A on pure logic, and pure logic only.** Deterministic output pinned
against a hard-coded list and re-derived in a second process and by an
independent verifier; every refusal path exercised by name; the rate, quantity,
weighted-pick and quality boundaries enumerated on both sides of each edge; the
unnormalized quality row measured; the input tables proven unmutated. There is
no client layer, no wire layer and no persistence layer here to grade.

NONCLAIMS:

* **This roller is OUR reconstruction from client-shipped data.** The original
  server's roll order and its RNG are unrecoverable forever. Two servers using
  these same tables with different orders would both be consistent with all
  available evidence; ours is one of them, not the one.
* **No coverage grade moves.** `monster_spawn_and_loot` stays `not_started`.
* **Nothing here has ever touched a wire, a client, or a database.** No socket
  was opened, no server booted, no frame composed, no row written, and no
  client has ever been shown any consequence of a roll.
* **The fixture is a small documented excerpt, not the tables.** 2 of 267
  DROPS_NORMAL rows, 1 of 53 DROPS_EQUIPMENT rows (itself truncated), 1 of 584
  DROPS_SPECIALLY rows, 26 of 26 E_DROPS_QUALITY rows, and zero mined MOBS
  rows -- the ten mob rows are composed by us for tests. A green suite here is
  not a statement about the shipped tables.
* **Doors 3 and 4 still have NO known wire path**, so a roll result cannot
  reach a player. There is no item/object actor_type on the proven spawn pipe,
  and DropThing / PickupTerrainThing remain registration names with no
  transport, serializer, producer or capture.
* **DROPS_QUEST is refused, not deferred.** ~87 pct of the referenced sets are
  absent client-side; rolling one would be invention. There is no partial
  implementation here to mistake for one.
* Whether the original game rolled loot client-side or server-side is
  [UNKNOWN] and undecidable from data alone.
* The money-slot reading (`n_ITEM = 0` with a nonzero rate) is [INFERENCE],
  carried as a tag on every money drop, not a proven fact.
