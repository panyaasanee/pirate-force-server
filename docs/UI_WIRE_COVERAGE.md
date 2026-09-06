# UI wire-name coverage -- "n/327"

PANYA `2032` job 2, queued by `pf_bridge/notes_to_chief/20260906_2047_COO-DECISION-panya2032-job2-ui-wire-coverage-bar-after-captain-frame-LANE-UI.md`
after the wstring `0x48` migration PR (`1713`). This page is generated from
`tools/pf_ui_wire_name_census.py`; the artifact it checks against is
`reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv`. Regenerate both with:

```
python3 tools/pf_ui_wire_name_census.py --emit
```

and commit the artifact together with any code change that could move a name
across tiers (`tests/test_ui_wire_name_census.py` pins the counts below and
goes red on drift).

## What this number is, and what it is not

**n/327 = how many of the 327 Vital wire names in
`pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` this server's
source tree already references, mechanically (identifier found in a `.py`
file under `src/pirateforce_foundation/`).** This is the whole project's
number, not UI's alone -- every lane's wire modules count (A's Trigger*/
Teleport*, B's TargetVital/Action*, DB's Equipment_*, CS's CFightMsg/CBuff,
GM's GM_*/Cheat*, and UI's own Community_/Pets_/Channel_/... modules all
contribute rows). The COO-DECISION above is explicit that the official count
belongs here, not to any one lane's private tally (e.g. ka1-A's earlier
69/327 note was a different, narrower count).

**A `SOURCE` row is not a claim that the name is WIRED.** `AGENTS.md`
section 7 ("`ต่อสายแล้ว` / `WIRED`") requires a mutation test that makes the
feature provably die, a single-writer side-effect guard, and an observed
round trip -- none of which this census runs. This tool only answers "does
the identifier appear in our code," the same mechanical, grep-shaped
question the RE-ticket search rule already requires before opening a new RE
(`AGENTS.md` section 7, "ก่อนเปิดใบ RE ต้อง grep..."). Treat `SOURCE` as
"has a handler/encoder worth reading," not "done."

## Tiers

| Tier | Meaning | Evidence column |
|---|---|---|
| `SOURCE` | identifier appears on a non-comment line of a `.py` file under `src/pirateforce_foundation/` (any lane) | `path:line` of the first hit |
| `NAME-ONLY` | not in `SOURCE`, but the identifier appears in at least one of the project's three function-map files -- `docs/PF_VITAL_NAMES.json` (this repo's admitted-names table), `pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv` (serializer/handler VA table), `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` (proven wire layouts) -- or in this repo's own `docs/UI_LANE.md` function table | which of those file(s), `+`-joined |
| `UNTOUCHED` | none of the above; the name exists only as a row in the master catalog | `-` |

`family` = the substring before the name's first `_` (or `(unprefixed)` when
there is none) -- a mechanical split, not the informal groupings written by
hand in `prompts/LANE-UI.md`/`AGENTS.md`. The two disagree on a handful of
names that do not follow a clean `Prefix_Rest` shape (e.g. the eight
`CHitParade*Vital[_JP]` names land in several one-name families here instead
of the prose's single "HitParade\_ 5" bucket) -- this is the mechanical
number, the prose was Panya's own domain read, and they are allowed to
differ. `is_client_req` flags a name that contains `Req` as its own
PascalCase word (`tools/pf_ui_wire_name_census.py`'s `is_client_req()`) --
this catches both wire-naming conventions the master catalog actually uses
(`...VitalReq` and `...ReqVital[_REGION]`, e.g. `CTracePathReqVital`,
confirmed client-inbound by this repo's own `trace_path.py` docstring)
without also matching an unrelated word that merely starts the same way
(`Community_RequestBeFriendVital` tokenizes to `Request`, not `Req`, so it
is correctly not flagged). An earlier draft of this tool only checked for a
trailing `Req` suffix and missed every `...ReqVital` name; pf-adversary
caught it before this landed on `main`.

## Headline (regenerate; do not hand-edit these numbers)

```
n/327 known (SOURCE) = 160/327
  NAME-ONLY = 158  UNTOUCHED = 9
```

## By family

Run `python3 tools/pf_ui_wire_name_census.py --summary` for the live,
per-family SOURCE / NAME-ONLY / UNTOUCHED breakdown -- it is not duplicated
here so this page cannot go stale relative to the artifact without the
pinned test catching it first.

## Full per-name table

See `reports/PF_UI_WIRE_NAME_CENSUS_20260906.tsv` (327 rows, tab-separated:
`id`, `name`, `family`, `is_client_req`, `tier`, `evidence`).

## Scoreboard

Every UI PR from this round onward carries a permanent scoreboard row,
per the COO-DECISION above:

```
wire-names known n/327: 160/327
```

K folds this into `SCOREBOARD_FACTS.tsv`. This is not a milestone flag and
does not gate anything on its own -- it is a standing measurement, expected
to move (up, as names cross into `SOURCE`; rarely down, if a module is
removed) as every lane's normal work lands.

## Non-claims

1. This page does not claim any of the 161 `SOURCE` names are WIRED in the
   `AGENTS.md` section 7 sense -- see "What this number is, and what it is
   not" above.
2. `NAME-ONLY` does not mean "known wire shape" for every row in that tier --
   a name can appear in `PF_PROTOCOL_REGISTRY.tsv` (a VA table for static RE)
   without `PF_SERIALIZER_FIELDS.tsv` (proven layout) covering it. Check the
   `evidence` column, not just the tier, before opening or skipping an RE
   ticket for a specific name.
3. `UNTOUCHED` does not mean "unbuildable" -- it means nobody has referenced
   the identifier in code or in one of the four function-map files yet;
   some of the 9 may already be answerable from `PF_SERIALIZER_FIELDS.tsv`
   under a different literal (e.g. a `_JP` regional twin) that this
   exact-identifier match does not fold together on purpose (folding them
   would hide real per-id gaps).
4. `SOURCE` skips full-line comments (so a name used only as this
   codebase's own generic prose, like a comment reusing `VitalData` as a
   memory-layout term, no longer counts on that alone) but does NOT strip
   trailing inline comments or docstring bodies -- a name mentioned only in
   `some_code = 1  # also called FooVital elsewhere` still counts as
   `SOURCE` on that line. This is a known, disclosed gap in the mechanical
   method, not a claim that every `SOURCE` row is a real reference.
5. This is not a substitute for the per-function status table in
   `docs/UI_LANE.md` ("layout known / needs RE / needs capture / done") --
   that table tracks UI's own pickup order; this page tracks the whole
   project's name coverage. A name can be `SOURCE` here and still have no GT
   ticket, and a name can be UI's own queue item while sitting at
   `UNTOUCHED` here if nobody has started it.
