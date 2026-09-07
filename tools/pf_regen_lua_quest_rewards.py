"""Regenerate lua_api/quest_reward_rows.tsv and quest_column_groups.tsv.

LANE-Q, COO-DECISION ``20260908_0242`` item 4 (the half-transaction rule).
Two more vendored files from the SAME shipped table
``QUESTDATA_TH__QUEST.tsv`` that ``tools/pf_regen_lua_quest_vars.py``
already mirrors, and for the same reason: a rule nobody can re-derive is a
guess with a header.

  * ``quest_reward_rows.tsv``    <- the table's 24 reward cells
    ``n_REWARD_ITEM1..6`` / ``n_REWARD_NUM1..6`` / ``n_REWARD_CHOOSE1..6`` /
    ``n_REWARD_CHOOSENUM1..6``, copied VERBATIM.  These are what
    ``Quest.RewardItem1``..``Quest.RewardChooseNum6`` read, and until this
    file existed every one of them answered 0 -- so
    ``q_class.lua:64`` ``if (Quest.RewardItem1 > 0)`` was never true and
    the quest that had just taken 15,000 off the player handed back
    nothing.

  * ``quest_column_groups.tsv``  <- the same table cross-read against the
    Lua corpus.  Which columns of one row are the TAKE side and the GIVE
    side of ONE transaction, which API each side goes through, and the
    ``file:line`` that proves the membership.

WHY A GROUP IS (SCRIPT, LUA FUNCTION) AND NOT (SCRIPT) OR (QUEST ID)
--------------------------------------------------------------------
"One transaction" is a property of the CODE: the take and the give are in
one transaction exactly when one entry point performs both.  In
``Quest/q_class.lua`` that is ``Report_Run``, which calls
``Player.AddCash(Quest.Var4)`` on line 60 and ``Player.AddItem(
Quest.RewardItem1, Quest.RewardItemNum1)`` on line 64.  A group keyed by
the script alone would say the same thing about a script whose take and
give live in two different entry points a player can reach separately;
keyed by quest id it would restate one fact once per row (1544 rows name
209 scripts, and ``Q_CON1`` alone is named by 160 of them -- the same
argument ``quest_vars`` records for its own key).

A MEMBER MAY HAVE NO COLUMN (pf-adversary D1/D2, round ``l0rbyx``)
------------------------------------------------------------------
``Quest.AddCriteriaCash()`` and its five siblings pay out of the criteria
curve and read no cell.  They are members all the same, written with
``column`` = ``-`` and addressed by API name, because a gate that refused
only columns left them running: measured on ``q_class.lua``, that handed
the player 15,000 cash, 19,350 exp and 6,450 skill points per run instead
of taking 15,000.  They are also UNCONDITIONAL, which is what closes the
second half of the same mistake -- ``q_guild_boss2.lua`` rows name no
reward item, so a column-only reading called their group unexercised and
let a 10,000 charge through with nothing given back.

THE ENCLOSING FUNCTION IS THE LAST TOP-LEVEL ``function`` LINE ABOVE THE
CALL.  Every entry point in this corpus is declared at column 0
(``function Report_Run()``), so this needs no Lua parser and cannot be
fooled by nesting: a call inside a nested closure still reports the
top-level entry point that owns it, which is the unit a player reaches.

    python3 tools/pf_regen_lua_quest_rewards.py            # rewrite both
    python3 tools/pf_regen_lua_quest_rewards.py --check    # drift only
    python3 tools/pf_regen_lua_quest_rewards.py --explain  # show the scan

``--check`` exits 0 when both copies match the source, 1 when one has
drifted, and 2 -- INCONCLUSIVE, not a drift report -- when there is no
``pf_bridge`` checkout beside this repository, which is the case on the
Windows gate.  Same three exit codes, same reason, as the sibling tool.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_regen_lua_quest_vars import (  # noqa: E402
    BRIDGE, CORPUS_RELPATH, SOURCE_RELPATH, arguments_of, corpus_file_for,
    read_rows,
)
from pirateforce_foundation.lua_api.quest_criteria import (  # noqa: E402
    BODY_DIGEST_PREFIX, body_digest,
)
from pirateforce_foundation.lua_api.quest_rewards import (  # noqa: E402
    GIVE, GROUP_COLUMNS, NO_COLUMN, REWARD_COLUMNS, REWARD_SLOTS,
    SOURCE_COLUMNS, TAKE,
)
from pirateforce_foundation.lua_api.quest_vars import (  # noqa: E402
    KIND_MONEY, VAR_COUNT, load_signedness,
)

LUA_API = ROOT / "src" / "pirateforce_foundation" / "lua_api"
REWARD_TARGET = LUA_API / "quest_reward_rows.tsv"
GROUP_TARGET = LUA_API / "quest_column_groups.tsv"

#: The GIVE-side call shapes this lane recognises, as
#: ``api -> (0-based argument position, the Quest.<name> prefix there)``.
#: Closed and lane-authored, exactly like ``KIND_BY_API`` in the sibling
#: tool, and for the same reason: a give-side API nobody has read a call
#: site for is a HARD STOP, not a default.  ``Player.AddItem`` takes the
#: item id in argument 0; ``Quest.RewardItemSelect`` takes the choose id.
GIVE_BY_API = {
    "Player.AddItem": (0, "RewardItem", "n_REWARD_ITEM"),
    "Quest.RewardItemSelect": (0, "RewardChoose", "n_REWARD_CHOOSE"),
}

#: GIVE-side calls that carry NO column at all: the quest's own criteria
#: payout, called with no arguments, whose amount comes from the criteria
#: curve rather than from a cell.  A closed list, and the reason the
#: ``column`` field of a group member is allowed to be ``-``.
#:
#: WHY THEY HAVE TO BE MEMBERS (pf-adversary D1, round `l0rbyx`).  A gate
#: that refused only the columns left these three RUNNING: measured on the
#: shipped `q_class.lua` `Report_Run`, refusing `n_VARI_4` alone moved the
#: player from -14,930 to +70 -- the round would have handed out 15,000
#: cash, 19,350 exp and 6,450 skill points per run instead of taking
#: 15,000.  "An incomplete group refuses every column in it" is about the
#: TRANSACTION, and a give with no column is still in the transaction.
GIVE_UNCONDITIONAL_APIS = (
    "Quest.AddCriteriaCash", "Quest.AddCriteriaExp",
    "Quest.AddCriteriaSkillPoint", "Quest.AddLvCriteriaCash",
    "Quest.AddLvCriteriaExp", "Quest.AddLvCriteriaSkillPoint",
)

#: The TAKE-side call shape.  Only one exists in the corpus today and it is
#: not spelled here as a literal: a take is a ``VarN`` the SIGNEDNESS table
#: already classified as :data:`KIND_MONEY`, whose call site that table
#: recorded.  Deriving the take side from the file that already carries the
#: provenance, rather than re-scanning for it, is what keeps the two tables
#: from disagreeing about the same five cells.
TAKE_KIND = KIND_MONEY

TOOL = Path(__file__).name

_FUNCTION = re.compile(rb"^function\s+([A-Za-z_][A-Za-z_0-9]*)")
_BARE_REWARD = rb"^\s*Quest\.%s\s*$"


class SourceMissing(Exception):
    """No bridge checkout beside this repo.  Distinct from "drifted"."""


class UnclassifiedGiveSite(Exception):
    """A give-side call whose shape nobody has classified."""


def read_reward_rows(path: Path):
    """``[(quest_id, script, (24 cells in SOURCE_COLUMNS order))]``."""
    rows = []
    with path.open(encoding="utf-8", newline="", errors="strict") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            cells = tuple(int(row[name]) for name in SOURCE_COLUMNS)
            rows.append((int(row["n_ID"]), row["s_LUASCRIPT"].strip(), cells))
    return rows


def enclosing_function(lines, number: int):
    """The top-level ``function`` name owning 1-based line ``number``."""
    for index in range(number - 1, -1, -1):
        match = _FUNCTION.match(lines[index])
        if match is not None:
            return match.group(1).decode("ascii", "replace")
    return None


def give_sites(path: Path):
    """``[(function, slot, reward_name, api, line_number, text)]``.

    One entry per GIVE-side call that passes a bare ``Quest.RewardItemK`` /
    ``Quest.RewardChooseK`` at the classified argument position.  Bytes in,
    bytes matched, ASCII out -- ``q_kill_skxyz.lua`` proved (round
    ``yfeauz`` D12) that decoding a corpus file can raise on exactly the
    file a table needs.
    """
    data = path.read_bytes()
    lines = data.split(b"\n")
    found = []
    for number, line in enumerate(lines, start=1):
        for api in GIVE_UNCONDITIONAL_APIS:
            args = arguments_of(line, api.encode("ascii"))
            if args is None or [a for a in args if a.strip()]:
                continue
            text = line.decode("ascii", "replace").rstrip("\r").strip()
            found.append((enclosing_function(lines, number), 0, None, api,
                          number, text))
        for api in sorted(GIVE_BY_API):
            position, prefix, source_prefix = GIVE_BY_API[api]
            args = arguments_of(line, api.encode("ascii"))
            if args is None or position >= len(args):
                continue
            argument = args[position]
            for slot in range(1, REWARD_SLOTS + 1):
                name = b"%s%d" % (prefix.encode("ascii"), slot)
                if not re.match(_BARE_REWARD % name, argument):
                    continue
                text = line.decode("ascii", "replace").rstrip("\r").strip()
                found.append((enclosing_function(lines, number), slot,
                              source_prefix, api, number, text))
    return found


def scan_groups(rows, corpus: Path):
    """``[(script, group, side, column, api_name, call_site)]`` ascending.

    A group is emitted ONLY when the same Lua function holds both sides.  A
    script with a take and no give, or a give and no take, has nothing this
    rule can be wrong about and is deliberately absent: the table says what
    is COUPLED, and a row that says "not coupled" would be a guess about
    every script in the corpus rather than a fact about one.
    """
    scripts = {}
    for _quest_id, script, _cells in rows:
        scripts.setdefault(script.strip().lower(), script.strip())
    out = []
    for key in sorted(scripts):
        takes = [column for (column_script, _index), column
                 in sorted(load_signedness().items())
                 if column_script == key and column.kind == TAKE_KIND]
        if not takes:
            continue
        path = corpus_file_for(corpus, key)
        if path is None:
            continue
        relative = path.relative_to(corpus).as_posix()
        gives = give_sites(path)
        if not gives:
            continue
        take_by_function = {}
        for column in takes:
            number = int(column.call_site.rsplit(":", 1)[1])
            lines = path.read_bytes().split(b"\n")
            take_by_function.setdefault(
                enclosing_function(lines, number), []).append(column)
        for function, columns in sorted(take_by_function.items(),
                                        key=lambda item: item[0] or ""):
            members = [entry for entry in gives if entry[0] == function]
            if not members:
                continue
            for column in sorted(columns, key=lambda c: c.var_index):
                out.append((scripts[key], function, TAKE,
                            "n_VARI_%d" % column.var_index, column.api_name,
                            column.call_site))
            for _function, slot, source_prefix, api, number, _text in sorted(
                    members, key=lambda entry: (entry[2] or "", entry[3],
                                                entry[1])):
                column = (NO_COLUMN if source_prefix is None
                          else "%s%d" % (source_prefix, slot))
                out.append((scripts[key], function, GIVE, column, api,
                            "%s:%d" % (relative, number)))
    return out


def _header(source_note: str, source_sha256: str, count: int, pulled: str,
            rendered_body: str, note: str) -> str:
    lines = [
        "# VENDORED MIRROR -- do not hand-edit.",
        "# regenerate: python3 tools/%s" % TOOL,
        "# source: %s" % source_note,
        "# source_sha256: %s" % source_sha256,
        "# source_rows: %d" % count,
        "# pulled: %s" % pulled,
        "%s%s" % (BODY_DIGEST_PREFIX, body_digest(rendered_body)),
        "# %s" % note,
    ]
    return "\n".join(lines) + "\n"


def render_rewards(rows, digest: str, pulled: str) -> str:
    body = ["\t".join(REWARD_COLUMNS)]
    for quest_id, _script, cells in rows:
        body.append("%d\t%s" % (quest_id,
                                "\t".join("%d" % cell for cell in cells)))
    rendered = "\n".join(body) + "\n"
    return _header(
        "pf_bridge/%s" % SOURCE_RELPATH, digest, len(rows), pulled, rendered,
        "n_REWARD_ITEM1..6 / n_REWARD_NUM1..6 / n_REWARD_CHOOSE1..6 / "
        "n_REWARD_CHOOSENUM1..6 verbatim; the shipped table holds no "
        "negative reward cell (largest is 3509557), so unlike n_VARI_* "
        "there is no signedness reading to make here.") + rendered


def render_groups(groups, digest: str, pulled: str) -> str:
    body = ["\t".join(GROUP_COLUMNS)]
    for row in groups:
        body.append("\t".join(str(field) for field in row))
    rendered = "\n".join(body) + "\n"
    return _header(
        "pf_bridge/%s cross-read against pf_bridge/%s"
        % (SOURCE_RELPATH, CORPUS_RELPATH), digest, len(groups), pulled,
        rendered,
        "one row per member column of a take/give transaction group; group "
        "is the Lua entry point that performs both sides, call_site is the "
        "corpus line that proves the membership.") + rendered


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(pulled_rewards: str, pulled_groups: str):
    source = BRIDGE / SOURCE_RELPATH
    corpus = BRIDGE / CORPUS_RELPATH
    missing = [str(p) for p in (source, corpus) if not p.exists()]
    if missing:
        raise SourceMissing(
            "source not found: %s (this script needs a pf_bridge checkout "
            "beside this repository)" % ", ".join(missing))
    digest = _digest(source)
    rewards = read_reward_rows(source)
    groups = scan_groups(read_rows(source), corpus)
    return (render_rewards(rewards, digest, pulled_rewards),
            render_groups(groups, digest, pulled_groups))


def _pulled_of(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("# pulled: "):
            return line[len("# pulled: "):]
    return fallback


def _first_difference(want: str, have: str) -> str:
    want_lines, have_lines = want.splitlines(), have.splitlines()
    for index in range(max(len(want_lines), len(have_lines))):
        left = want_lines[index] if index < len(want_lines) else "<missing>"
        right = have_lines[index] if index < len(have_lines) else "<missing>"
        if left != right:
            return "line %d: on disk %r, from source %r" % (index + 1, right,
                                                            left)
    return "no line differs"


def explain() -> int:
    """Print the scan a person has to be able to argue with."""
    source = BRIDGE / SOURCE_RELPATH
    corpus = BRIDGE / CORPUS_RELPATH
    if not source.exists() or not corpus.exists():
        sys.stdout.write("INCONCLUSIVE no pf_bridge checkout beside this repo\n")
        return 2
    rows = read_rows(source)
    rewards = read_reward_rows(source)
    exercised = sum(1 for _id, _script, cells in rewards
                    if any(cells[index] for index in _GIVE_CELL_INDEXES))
    sys.stdout.write("rows=%d reward_cells=%d rows_with_a_reward=%d\n"
                     % (len(rewards), len(rewards) * len(SOURCE_COLUMNS),
                        exercised))
    largest = max(max(cells) for _id, _script, cells in rewards)
    sys.stdout.write("largest_reward_cell=%d wrapped_reward_cells=%d\n"
                     % (largest,
                        sum(1 for _id, _s, cells in rewards
                            for cell in cells if cell >= 1 << 31)))
    for row in scan_groups(rows, corpus):
        sys.stdout.write("  %s %s %s %s %s %s\n" % row)
    return 0


#: Positions inside :data:`SOURCE_COLUMNS` that hold an ID the script tests
#: with ``> 0`` before giving anything.  The NUM columns are not tested, so
#: a row whose only non-zero reward cell is a NUM gives nothing.
_GIVE_CELL_INDEXES = tuple(
    SOURCE_COLUMNS.index(name) for name in SOURCE_COLUMNS
    if name.startswith("n_REWARD_ITEM") or (
        name.startswith("n_REWARD_CHOOSE")
        and not name.startswith("n_REWARD_CHOOSENUM")))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="report drift, write nothing")
    parser.add_argument("--explain", action="store_true",
                        help="print the scan behind quest_column_groups.tsv")
    args = parser.parse_args(argv)
    if args.explain:
        return explain()
    today = date.today().isoformat()
    try:
        rewards, groups = build(_pulled_of(REWARD_TARGET, today),
                                _pulled_of(GROUP_TARGET, today))
    except SourceMissing as exc:
        sys.stdout.write("INCONCLUSIVE %s\n" % exc)
        return 2
    if args.check:
        drifted = False
        for target, want in ((REWARD_TARGET, rewards), (GROUP_TARGET, groups)):
            have = target.read_text(encoding="ascii") if target.exists() else ""
            if have != want:
                drifted = True
                sys.stdout.write("DRIFT %s: %s\n"
                                 % (target.name, _first_difference(want, have)))
        if drifted:
            return 1
        sys.stdout.write("OK %s %s\n" % (REWARD_TARGET.name, GROUP_TARGET.name))
        return 0
    REWARD_TARGET.write_text(rewards, encoding="ascii")
    GROUP_TARGET.write_text(groups, encoding="ascii")
    sys.stdout.write("WROTE %s %s\n" % (REWARD_TARGET.name, GROUP_TARGET.name))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
