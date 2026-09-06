"""Offline guards for the npc_interaction coverage domain.

Five rows in that domain carried evidence and no test at all, which makes them
claims nobody watches. These tests cover exactly what the rows already say:

  * npc_conversation_handshake  — one click yields TargetVital plus an embedded
    ChooseNPC, and the server answers with one NPCConversation carrying one
    descriptor.
  * conversation_operation_sequence — operation 1/action 6 then operation
    2/action 1, in that order, once each, refused out of order.
  * quest_accept_and_progress — the accept path stops at the client-local
    boundary; no quest state is stored server-side.
  * shop_buy_sell — the store-5 open packet is a test harness, and nothing in
    the Foundation store implements shop inventory, prices or transactions.
  * interaction_negative_paths — the V140 P86 position is an explicit synthetic
    harness offset, not the decoded placement of that actor.

None of these tests upgrades a status. They fail if the claim drifts.
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# --------------------------------------------------------------------------
# The cross-lane quest/shop guard's reader.  Chief owns this block
# (COO-DECISION 20260904_1647); it is not any one lane's to edit.
#
# WHAT WENT WRONG, MEASURED, TWICE:
# 1. `\bquest\b` never matched `quest_id` and `\btrade\b` never matched
#    `settle_trade`, because `_` is a word character to `re`.  LANE-UI proved
#    it by planting a `settle_trade` in a Foundation module and watching the
#    guard stay green (pf_bridge/notes_to_chief/20260904_1600).
# 2. The first fix for that, in this same round, was itself defeated three
#    ways by pf-adversary before it was pushed: a word cleared file-level
#    skipped the symbol check entirely (so `runtime.py` accepted a working
#    `settle_trade`); `settleTrade` and `QUESTS` slipped the word edge; and a
#    docstring sentence saying a table is ABSENT bought blanket clearance for
#    a function that implements it.
#
# WHAT THIS READER DOES NOW, and why each piece exists:
# * It reads CODE TOKENS ONLY -- comments and string literals are dropped
#   before matching.  A comment cannot implement a shop, and the mined data
#   rows this package is full of ('Gold Shop', 'Merchant marine Trade Ship')
#   are string literals.  That single change deleted five of the six
#   file-level exemptions this guard used to need, and it is what makes a
#   `def drops_quest(...)` in a module whose docstring merely NAMES
#   DROPS_QUEST go red (pf-adversary D6).
# * It splits camelCase before lowercasing, so `TradeCmdVital` and
#   `settleTrade` are seen.  `.lower()` alone destroyed the only boundary
#   those names have.
# * It allows a trailing plural `s` and trailing digits, so `QUESTS`,
#   `trades` and `dispatch_columbus_quest3021` are seen -- but still no other
#   trailing letter, which is what keeps "question" and "request" out.
# * It reports the whole surrounding identifier, so an exemption can name one
#   symbol instead of clearing a file.
#
# * An f-string is read as code -- BOTH halves, its literal text and its
#   replacement fields (`fstring_code_text`).  This is the one exception to
#   the line above, and it is not a choice: from Python 3.12 the tokenizer
#   itself reads them as code, the gate pins 3.14, and a guard that reads one
#   thing here and another there is how #748 passed locally and died on the
#   gate.  The cost is real and is the reason it is written down: a mined data
#   row spelled as an f-string (`f"Gold Shop row {n}"`) now reports, where the
#   same row spelled `"Gold Shop row " + str(n)` does not.
#
# WHAT A GREEN RUN ENTITLES A READER TO BELIEVE -- the contract, written down
# because the test's own name over-promises (pf-adversary's closing question):
#   "No top-level module of `src/pirateforce_foundation` binds a CODE name --
#    or spells inside an f-string -- one of GUARD_WORDS that chief has not
#    read and exempted."
# It does NOT say the package implements no quest or shop behaviour.  Known,
# deliberate gaps, each pinned by a test below rather than left silent:
#   - subpackages (`gm/`, `lane_hooks/`, ...) are not scanned at all
#     (`test_the_unscanned_subpackages_are_named_and_counted`);
#   - behaviour named without any guard word (`def settle(...)`) is invisible
#     to any word list, and always was;
#   - two f-string shapes read differently on the gate than here, both named
#     in `fstring_code_text` and neither present in the package today.
# --------------------------------------------------------------------------
GUARD_WORDS = ("quest", "shop", "store5", "price", "reward", "trade")

_CAMEL_ACRONYM = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_HUMP = re.compile(r"([a-z0-9])([A-Z])")


def guard_normalise(text):
    """camelCase -> snake_case, then lowercase.  Run this before matching."""
    return _CAMEL_HUMP.sub(
        r"\1_\2", _CAMEL_ACRONYM.sub(r"\1_\2", text)
    ).lower()


def fstring_code_text(token_string):
    """One f-string token read the way a PEP 701 tokenizer reads it.

    Returns None when `token_string` is not an f-string.  This exists so the
    guard reaches the SAME verdict on every interpreter it runs on.  Up to
    Python 3.11 an f-string is one `tokenize.STRING` token, so ALL of
    `f"a_{x}"` vanished with the plain string literals; from 3.12 (PEP 701)
    the literal halves come back as `FSTRING_MIDDLE` and the replacement
    fields as ordinary tokens, none of which is `tokenize.STRING`, so both
    stayed in.  The gate pins 3.14 and that is the reading this repository is
    held to (`.github/workflows/gate-windows.yml`), so the 3.11 side is the
    one brought up to it -- never the other way round, which would blind the
    guard to `f"drops_quest_{set_id}"` and to `f"{shop.settle_trade()}"` on
    the interpreter that ships.

    Two rules keep the two readings from drifting, both learned from
    pf-adversary breaking the first version of this function:
      * literal halves are kept RAW, undecoded.  `f"\\N{TRADE MARK SIGN}"`
        carries the word `trade` on the gate, and decoding it to a glyph here
        would hide it.  A doubled brace becomes a space, because a 3.12+
        tokenizer ends its `FSTRING_MIDDLE` token on the brace and starts a
        new one after it -- `f"a{{b}}c"` is three tokens there, which the
        space reproduces (the brace itself is not a word character to
        `guard_hits`, so keeping or dropping it cannot change a verdict).
      * a replacement field is CODE, so it goes back through
        `module_code_text` -- which drops the string literals inside it, the
        same as the gate's tokenizer does.  Reading them would put mined data
        rows (`row['Gold Shop']`) in front of a guard whose whole contract is
        that string literals are not behaviour.

    Measured, not argued: over the 171 top-level modules of the package, all
    703 tracked `.py` files, and ~124,000 generated f-strings,
    `guard_hits_in_module` returns identical verdicts under 3.11-with-this
    and a real PEP 701 interpreter (3.13).

    Two named gaps, so neither can grow unnoticed:
      * PEP 701-only source -- a field holding a string in the f-string's own
        quote, `f'{d["k"].settle_trade()}'` -- is a syntax error before 3.12,
        and 3.11's `tokenize` splits it into pieces rather than failing, so
        no fallback fires and the call is read on the gate and missed here.
      * a 3.14 t-string (`t"..."`) is not a `tokenize.STRING` token there and
        is one here, so it is read on the gate and dropped here.
    Neither shape exists in this package today, and there is no 3.14 on this
    clone to measure with; the day either appears, this function needs it.
    """
    quote_at = min(
        (token_string.find(q) for q in ("'", '"') if q in token_string),
        default=-1,
    )
    if quote_at < 1 or "f" not in token_string[:quote_at].lower():
        return None
    body = token_string[quote_at:]
    for quote in ('"""', "'''", '"', "'"):
        if body.startswith(quote):
            body = body[len(quote):]
            if body.endswith(quote):
                body = body[: -len(quote)]
            break
    parts = []
    literal = []
    index = 0
    while index < len(body):
        char = body[index]
        if body[index:index + 2] in ("{{", "}}"):
            literal.append(" ")
            index += 2
            continue
        if char == "{":
            close = _closing_brace(body, index)
            parts.append("".join(literal))
            literal = []
            parts.append(module_code_text(body[index + 1:close]))
            index = close + 1
            continue
        if char == "}":
            literal.append(" ")
            index += 1
            continue
        literal.append(char)
        index += 1
    parts.append("".join(literal))
    return " ".join(part for part in parts if part)


def _closing_brace(body, opened_at):
    """Index of the `}` that closes `body[opened_at]`, or the end of `body`.

    Depth-counted and quote-aware, because a replacement field may hold a
    dict display and, from 3.12, a string in the same quote as the f-string.

    Quote-awareness stops at the format spec.  After the `:` that opens one --
    the first colon that is not inside `()`, `[]` or `{}` -- only braces are
    structural and a quote is an ordinary fill character.  Reading `'` there
    as an opening quote is what made `f"{a:'>5}{settle_trade()}'"` swallow its
    own closing brace and hide a real call from the guard on 3.11 while the
    3.14 gate saw it (pf-adversary D1, second pass, this round).
    """
    depth = 0
    brackets = 0
    quote = None
    in_spec_at = None
    index = opened_at
    while index < len(body):
        char = body[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if body.startswith(quote, index):
                index += len(quote)
                quote = None
            else:
                index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        elif in_spec_at is not None and depth == in_spec_at:
            # inside the format spec: quotes are fill characters, not code
            pass
        elif char in "'\"":
            quote = body[index:index + 3] if body.startswith(
                char * 3, index
            ) else char
            index += len(quote)
            continue
        elif char in "([":
            brackets += 1
        elif char in ")]":
            brackets = max(brackets - 1, 0)
        elif char == ":" and depth == 1 and brackets == 0:
            in_spec_at = depth
        index += 1
    return len(body)


def module_code_text(source):
    """The module's code tokens only -- no comments, no string literals.

    An f-string is read as code on every interpreter: see `fstring_code_text`.
    Falls back to the raw source if the text will not tokenise, because a
    guard that goes quiet on a syntax error is worse than one that shouts.
    """
    try:
        kept = []
        for token_info in tokenize.generate_tokens(
            io.StringIO(source).readline
        ):
            if token_info.type == tokenize.COMMENT:
                continue
            if token_info.type == tokenize.STRING:
                inner = fstring_code_text(token_info.string)
                if inner:
                    kept.append(inner)
                continue
            kept.append(token_info.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    return " ".join(kept)


def guard_hits(text):
    """Map each guard word present to the full identifiers it appears inside.

    `text` must already be through `guard_normalise`.
    """
    found = {}
    for word in GUARD_WORDS:
        symbols = set(re.findall(
            rf"[a-z0-9_]*(?<![a-z0-9]){word}s?[0-9]*(?![a-z])[a-z0-9_]*", text
        ))
        if symbols:
            found[word] = symbols
    return found


def guard_hits_in_module(source):
    """Every guard hit among a module's code names, exemptions not applied."""
    return guard_hits(guard_normalise(module_code_text(source)))

from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

ACCEPT_UI_LABEL = "V134_BOUNDED_HYPOTHESIS_Q3020_OP1_TO_ACTION6_ONCE"

# Every table the Foundation store is allowed to own today. The npc_interaction
# rows all say server-side quest, shop and reward state does not exist; this set
# is how that sentence is enforced.
EXPECTED_TABLES = {
    "schema_migrations",
    "accounts",
    "characters",
    "character_positions",
    "sessions",
    "character_backpacks",
    "character_backpack_items",
    # ground_drops: world-state ledger of items dropped on the ground, not
    # quest/shop/reward state -- COO-DECISION 20260903_1843 ordered the table,
    # COO-DECISION 20260903_2050 approved this one-line whitelist addition in
    # the same round that lands it.
    "ground_drops",
    # character_skills: the starting-skill-kit door, not quest/shop/reward
    # state -- PANYA-DECISION 20260904_0328 piece 5 / COO-ORDER 20260904_0329
    # item 5 ordered the table (migrations/011_character_skills.sql).  Same
    # one-line whitelist pattern chief blessed for ground_drops above
    # (notes_to_chief/20260901_1416 / 20260901_1459): this pin counts tables,
    # it does not test this file's own npc_interaction behaviour.
    "character_skills",
    # character_home_marker: the "born again" home-scene persistence door,
    # not quest/shop/reward state -- COO-DECISION 20260905_1154 point 3(b)
    # ordered the table (migrations/013_character_home_marker.sql).  Same
    # one-line whitelist pattern chief blessed for ground_drops/
    # character_skills above (notes_to_chief/20260901_1416 / 20260901_1459):
    # this pin counts tables, it does not test this file's own
    # npc_interaction behaviour.
    "character_home_marker",
    # character_equipment: the equipped-item persistence door, not quest/
    # shop/reward state -- PANYA-ORDER 20260906_1312 arm (b) ordered the
    # table (migrations/015_character_equipment.sql).  Same one-line
    # whitelist pattern chief blessed for ground_drops/character_skills/
    # character_home_marker above (notes_to_chief/20260901_1416 /
    # 20260901_1459): this pin counts tables, it does not test this file's
    # own npc_interaction behaviour.
    "character_equipment",
}


class NpcConversationHandshakeTests(unittest.TestCase):
    """coverage row npc_interaction/npc_conversation_handshake."""

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def choose_packet(self, *, identities, lead_target=True):
        vitals = []
        if lead_target:
            vitals.append(
                self.v.u16tag(0x12, self.v.TARGET_VITAL)
                + self.v.u8tag(0x0B, 0)
                + self.v.qwordtag(0x32, identities[0])
                + self.v.u8tag(0x08, 2)
            )
        for identity in identities:
            vitals.append(
                self.v.u16tag(0x12, self.v.CHOOSE_NPC)
                + self.v.u8tag(0x0B, 0)
                + self.v.qwordtag(0x32, identity)
            )
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, len(vitals))
            + b"".join(vitals)
        )
        return self.v.parse_outer(pc)

    def test_one_click_composition_yields_exactly_one_identity(self):
        parsed = self.choose_packet(identities=[self.v.V129_QUEST_ACTOR_ID])
        self.assertEqual(
            self.v.extract_choose_npc_identities(parsed),
            [self.v.V129_QUEST_ACTOR_ID],
        )

    def test_target_vital_alone_yields_no_identity(self):
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.TARGET_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u8tag(0x08, 2)
        )
        self.assertEqual(
            self.v.extract_choose_npc_identities(self.v.parse_outer(pc)), []
        )

    def test_a_foreign_vital_stops_the_walk_instead_of_scanning_bytes(self):
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 2)
            + self.v.u16tag(0x12, self.v.TARGET_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u8tag(0x08, 2)
            + self.v.u16tag(0x12, self.v.SHOW_MESSAGE_VITAL)
            + self.v.u8tag(0x0B, 0)
            + self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
        )
        self.assertEqual(
            self.v.extract_choose_npc_identities(self.v.parse_outer(pc)), []
        )

    def test_empty_conversation_is_identity_plus_zero_entries(self):
        pc, frame = self.v.make_npc_conversation_empty(0x2001)
        vital = self.v.u16tag(0x12, self.v.NPC_CONVERSATION) + self.v.u8tag(0x0B, 0)
        self.assertEqual(pc.count(vital), 1)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.qwordtag(0x32, 0x2001)
            + self.v.u16tag(0x0F, 0)
            + self.v.u8tag(0x0B, 0),
        )
        self.assertEqual(frame, self.v.frame_pc(pc))

    def test_quest_conversation_carries_exactly_one_descriptor(self):
        pc, _ = self.v.make_npc_conversation_quest3020()
        vital = self.v.u16tag(0x12, self.v.NPC_CONVERSATION) + self.v.u8tag(0x0B, 0)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.qwordtag(0x32, self.v.V129_QUEST_ACTOR_ID)
            + self.v.u16tag(0x0F, 1)
            + self.v.u16tag(0x12, self.v.V129_QUEST_ID)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 0),
        )

    def test_quest_conversation_refuses_any_actor_other_than_p0(self):
        for identity in (0x2000, 0x2002, self.v.V139_P86_ACTOR_ID):
            with self.assertRaises(ValueError):
                self.v.make_npc_conversation_quest3020(identity)


class ConversationOperationSequenceTests(unittest.TestCase):
    """coverage row npc_interaction/conversation_operation_sequence."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "npc.sqlite3"
        self.store = SQLiteStore(db, ROOT / "migrations")
        self.store.migrate()
        self.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.v)
        default = Position(
            1, 0, self.v.V135_PLAYER_X, self.v.V135_PLAYER_Y, self.v.V135_PLAYER_Z
        )
        self.lifecycle = CharacterLifecycle(
            self.store, default, self.v.extract_avatar_attr_wire_from_actor
        )
        seed = FoundationSession(self.lifecycle, self.projector, "npc-user")
        actor = self.v.get_preset_actor_wire().replace(
            self.v.wstr_tag("test01"), self.v.wstr_tag("Arena01"), 1
        )
        self.character, _ = seed.create("Arena01", actor)
        self.scenario = load_scene_load_scenario(
            ROOT / "scenarios/scene2_fighting_fish_soldier.json"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, *, conversation_sent):
        factory = lambda token: ReadOnlyFoundationSession(
            self.store, self.projector, token, self.scenario
        )
        state = make_state_class(
            self.v,
            self.lifecycle,
            self.projector,
            scene_load_scenario=self.scenario,
            session_factory=factory,
        )("npc-user")
        state.dispatch(self.v.parse_outer(self.v._synthetic_client_login_pc()))
        state.dispatch(
            self.v.parse_outer(
                self.v._synthetic_start_game_pc(self.character.selector)
            )
        )
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        state.quest3020_conversation_sent = conversation_sent
        return state

    def quest_request(self, operation, *, quest_id=None, version=3):
        quest_id = self.v.V129_QUEST_ID if quest_id is None else quest_id
        body = (
            self.v.u16tag(0x12, quest_id)
            + self.v.u8tag(0x08, operation)
            + self.v.u8tag(0x08, 0)
            + self.v.u32tag(0x14, 0)
            + self.v.qwordtag(0x32, 0)
            + self.v.u8tag(0x05, 0)
        )
        pc = (
            self.v.u16tag(0x12, self.v.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.v.u32tag(0x14, 0)
            + self.v.u8tag(0x08, 0)
            + self.v.u8tag(0x0B, 2)
            + self.v.u16tag(0x12, 1)
            + self.v.u16tag(0x12, self.v.QUEST_OPERATE_VITAL)
            + self.v.u8tag(0x0B, version)
            + body
        )
        return self.v.parse_outer(pc)

    def labels(self, state, parsed):
        return [action[0] for action in state.dispatch(parsed)]

    def test_operation1_before_the_conversation_gets_no_reply(self):
        state = self.state(conversation_sent=False)
        self.assertEqual(self.labels(state, self.quest_request(1)), [])
        self.assertFalse(state.quest3020_accept_ui_sent)
        self.assertEqual(state.quest3020_op1_capture_count, 1)

    def test_operation2_before_the_accept_ui_gets_no_reply(self):
        state = self.state(conversation_sent=True)
        self.assertEqual(self.labels(state, self.quest_request(2)), [])
        self.assertFalse(state.quest3020_accept_success_sent)

    def test_ordered_sequence_answers_action6_then_action1_once_each(self):
        state = self.state(conversation_sent=True)
        first = state.dispatch(self.quest_request(1))
        self.assertEqual([action[0] for action in first], [ACCEPT_UI_LABEL])
        self.assertEqual(
            (first[0][1], first[0][2]), self.v.make_quest3020_action6_accept_ui()
        )
        second = state.dispatch(self.quest_request(2))
        self.assertEqual(len(second), 1)
        self.assertEqual(
            (second[0][1], second[0][2]),
            self.v.make_quest3020_action1_accept_success(),
        )
        self.assertTrue(state.quest3020_accept_success_sent)

    def test_replaying_either_operation_never_answers_twice(self):
        state = self.state(conversation_sent=True)
        state.dispatch(self.quest_request(1))
        state.dispatch(self.quest_request(2))
        for operation in (1, 2, 1, 2):
            self.assertEqual(self.labels(state, self.quest_request(operation)), [])
        self.assertEqual(state.quest3020_accept_ui_sent, True)
        self.assertEqual(state.quest3020_accept_success_sent, True)

    def test_another_quest_id_or_version_is_not_the_exact_request(self):
        for kwargs in ({"quest_id": 3021}, {"version": 2}):
            state = self.state(conversation_sent=True)
            self.assertEqual(self.labels(state, self.quest_request(1, **kwargs)), [])
            self.assertFalse(state.quest3020_accept_ui_sent)

    def test_action1_is_a_result_and_is_never_offered_as_the_opening_move(self):
        # V124 proved action 1 is an acceptance result. The accept-UI offer must
        # therefore be action 6, and the two builders must not be interchangeable.
        offer, _ = self.v.make_quest3020_action6_accept_ui()
        result, _ = self.v.make_quest3020_action1_accept_success()
        self.assertNotEqual(offer, result)
        self.assertEqual(self.v.V129_QUEST_OPEN_ACCEPT_UI_ACTION, 6)
        self.assertEqual(self.v.V129_QUEST_ACCEPT_SUCCESS_ACTION, 1)
        for builder in (
            self.v.make_quest3020_action6_accept_ui,
            self.v.make_quest3020_action1_accept_success,
        ):
            with self.assertRaises(ValueError):
                builder(0x2002)


class QuestAndShopStateGuardTests(unittest.TestCase):
    """coverage rows npc_interaction/quest_accept_and_progress and shop_buy_sell.

    Both notes state that nothing is persisted or implemented server-side. If
    someone lands quest tracking, a shop inventory or a price authority, these
    guards break so the matrix has to be re-graded first.
    """

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_store_schema_owns_no_quest_shop_or_reward_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "schema.sqlite3"
            store = SQLiteStore(db, ROOT / "migrations")
            store.migrate()
            import sqlite3

            connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    if not row[0].startswith("sqlite_")
                }
            finally:
                connection.close()
        self.assertEqual(tables, EXPECTED_TABLES)

    # CORE-REQUEST-014 re-grade (chief, R192, 2026-08-27): columbus_quest_
    # dispatch.py names "quest" throughout -- it is Columbus's NPCConversation/
    # QuestOperateVital dispatch. UPDATED round e0daaa (2026-08-27 ~15:2x):
    # dispatch_columbus_quest3021() no longer always refuses -- PANYA-DECISION
    # 2026-08-27T15:25+07:00 accepted M2 without a vehicle bind, so it now
    # teleports the player to scene 17 on a real op1/3021 dispatch. It still
    # stores nothing: no quest-state row, no tracker update, no completion,
    # no reward, no persistence of "this player did the Columbus quest" --
    # the teleport is a one-shot wire effect, not quest bookkeeping. The
    # quest_accept_and_progress row's note ("no quest state is stored
    # server-side") stays true for that reason, so the matrix does not need
    # to move off in_progress for this. Allow exactly this one file for
    # exactly the word "quest" -- any OTHER word from the list, or any OTHER
    # file, still trips this guard, on purpose.
    # AMENDMENT 2026-08-28 (LANE-A, RE-128).  world_port_royal_identity.py
    # trips the word "shop" three times and implements no shop behaviour at
    # all: the hits are inside the MOBS_TIP TITLE TEXT the client's own tables
    # give three NPCs ("Gold Shop", "PVP Shop", "Nutrition Jelly Shop"), which
    # this lane now sends as name/title data.  A title string is not a
    # capability, and deleting the word would mean shipping a different NPC's
    # label than the client's table has.  The exemption is kept honest by
    # ``test_the_identity_tables_shop_hits_are_all_npc_title_data`` below,
    # which fails the moment a "shop" appears anywhere in that file except in
    # a data row of the identity table.
    # AMENDMENT 2026-08-30 (LANE-B, RE-157 job 1).  trade_session_membership.py
    # names "trade" throughout its module docstring and identifiers
    # (ActiveStoreSession, build_session, admits()) but implements no cart,
    # price, product or purchase logic at all: it is a fail-closed
    # scene+actor+generation membership predicate over a caller-supplied
    # session record, the exact shape of mob_combat_membership.py's already-
    # allowed sibling predicate (that module trips no word from this list
    # only because its own vocabulary is "combat"/"census", not "trade").
    # There is still no call site in runtime.py for either guard -- see the
    # module's own CORE-REQUEST -- so nothing about store state, pricing or
    # a purchase outcome is decided here.
    # REPLACED round `oi2r2n` (chief, R340) -- COO-DECISION 20260904_1647.
    #
    # The old map was `{filename: {word}}`: clearing a word for a whole file.
    # Five of its six entries existed only because the guard matched COMMENTS
    # and MINED DATA STRINGS -- 'Gold Shop' in an NPC title column, "trade"
    # in a module docstring.  The reader above no longer looks at either, so
    # those five entries are simply gone, and with them the hole pf-adversary
    # opened this round: a `def shop_buy(...)` in world_port_royal_identity.py
    # was invisible while the file was cleared for "shop".
    #
    # What is left is per SYMBOL, and every symbol below is a name bound in
    # CODE.  Each is a PASS-THROUGH: a module name, a mined column or table
    # name, or a proven wire class name.  None of them decides a price, a
    # reward, a shop inventory, a trade outcome or quest state.  A new name
    # in any of these files -- `def settle_trade`, `settleTrade`, `QUESTS` --
    # is not on this list and goes red.
    #
    # 🔴 An exemption is a name chief has READ.  It is never granted to make
    # a red run green; the fix for a red run is to rename the symbol
    # (AGENTS.md section 7, the rule this round added).
    ALLOWED_SYMBOLS = {
        # LANE-Q's sandboxed Lua host, wiring the real Quest namespace into
        # ScriptHost.  GRANTED by chief (LANE-E) round `xcbnbn`/R364 on
        # CORE-REQUEST `pf_bridge/notes_to_chief/20260906_0209_LANE-Q-CORE-
        # REQUEST-*`, after reading the three names in this module rather
        # than taking the request's word for them: `lua_api_quest` is an
        # import alias, `quest` is that import's own source name, and
        # `quest_clock` is an injectable clock parameter.  None of the three
        # decides quest state, a reward, a completion, or any persistence --
        # the namespace's own logic is a pure clock read in
        # `lua_api/quest.py`, one directory down, which `glob("*.py")` above
        # does not scan.  Same shape as `columbus_quest_dispatch.py` below.
        # Residual hole, named rather than hidden: the bare symbol `quest`
        # being allowed here means a module-level `quest = {}` in THIS file
        # would also pass.  Accepted because a Lua host storing quest state
        # in Python contradicts `prompts/LANE-Q.md` itself; any NEW name
        # (`settle_quest_reward`, ...) is still red, and `reward`/`shop` are
        # their own guard words.
        "script_host.py": {
            "lua_api_quest",
            "quest",
            "quest_clock",
            # LANE-Q's shared QuestStateStore wiring: Trigger.QuestActive
            # Progress/QuestFinishProgress and Quest.*'s own newly-real names
            # (COO-DECISION 20260906_1846, pf_bridge round `7v7yn2`) must see
            # the SAME store within one script run. PRE-APPROVED by chief
            # (LANE-E) round `awnjat` on CORE-REQUEST `pf_bridge/notes_to_
            # chief/20260906_1951_...md`, landed here by LANE-Q in the same
            # PR as the wiring code it exempts (chief cannot grant an
            # exemption for code that does not exist yet --
            # test_every_symbol_exemption_is_still_earned refuses it).
            # `quest_context`/`quest_store` are parameter names (pass-
            # through only); `InMemoryQuestStateStore` is a class reference
            # this guard's CamelCase normalizer reports as
            # `_in_memory_quest_state_store` -- its own real logic lives in
            # lua_api/quest.py, one directory down, not scanned by this
            # guard, and is explicitly NOT the production persistence
            # answer (chief's real accessor landed round `awnjat`,
            # store.py's get_quest_flag/set_quest_flag/get_quest_counter/
            # set_quest_counter -- switching ScriptHost to it later is a
            # one-parameter change, not a new exemption).
            "quest_context",
            "quest_store",
            "_in_memory_quest_state_store",
        },
        # The quest module itself.  It is the one place quest dispatch lives,
        # by the design the npc_interaction rows describe: a one-shot wire
        # effect that stores nothing.  Naming it here rather than clearing
        # the file means a `def settle_trade` inside it still goes red.
        "columbus_quest_dispatch.py": {
            "columbus_quest_bornagain_id",
            "columbus_quest_bornagain_label_th_translit",
            "columbus_quest_bornagain_marker_id",
            "columbus_quest_id",
            "columbus_quest_op_dispatch",
            "dispatch_columbus_quest3021",
            "dispatch_columbus_quest3205",
            "quest_fields",
            "quest_id",
        },
        # LANE-B's refusal machinery plus the mined table names it refuses BY
        # NAME.  `_roll_quest` returns REFUSAL_QUEST_NOT_IMPLEMENTED and
        # touches `drops` nowhere (loot_roll.py:989-1013, re-read by
        # pf-adversary this round); `TABLE_DROPS_QUEST` appears at :627 inside
        # a `raise LootTableError(...)`.  2478 DROPS_QUEST sets are referenced
        # by mobs and 311 exist client-side, so a roll here would be
        # invention.  🔴 The exemption rests on that premise and only LANE-B
        # can keep it true -- chief wrote to them rather than editing their
        # module (pf_bridge/notes_to_chief/20260904_1708).
        "loot_roll.py": {
            "_roll_quest",
            "drops_quest",
            "item_table_quest",
            "refusal_quest_not_implemented",
            "table_drops_quest",
        },
        # Dispatch names, event-log tokens and imported module names.  The
        # quest behaviour they reach lives in columbus_quest_dispatch.py; the
        # trade names are the eight opcode ids CORE-REQUEST 1120 wired as
        # report-only branches (chief, R339) -- TradeCmdVital, the class that
        # would execute a trade, still has no call site anywhere in this
        # repository.  `make_v112_monster_shop_population_state` is a v141
        # legacy symbol this server calls; the word is inside somebody else's
        # frozen name.
        "runtime.py": {
            "_dispatch_columbus_quest3021",
            "_friend_mail_party_trade_dispatch",
            "_friend_mail_party_trade_dispatch_ids",
            "columbus_quest3021_conversation_sent",
            "columbus_quest3021_dispatch_attempted",
            # f-string prefixes: `f"columbus_quest3021_dispatch_refused_
            # {reason}"` / the 3205 sibling, appended to `self.events` only
            # inside `except columbus_quest_dispatch.ColumbusDispatchRefused`
            # (runtime.py:6156-6160, :6457). The guard extracts the static
            # text before `{reason}`, trailing underscore included. This is
            # the refusal telemetry, the direct sibling of loot_roll.py's
            # already-allowed `refusal_quest_not_implemented`: it fires only
            # when the dispatch was REFUSED, so it cannot be evidence of
            # quest state being implemented.
            #
            # These two entries used to be red off the 3.14 gate and green on
            # it: up to Python 3.11 the whole f-string was one
            # `tokenize.STRING` token that `module_code_text()` dropped, so
            # they matched nothing, while PEP 701 (3.12+) splits the static
            # text out as `FSTRING_MIDDLE` and it matched. The gate pins 3.14
            # (`.github/workflows/gate-windows.yml`), which is why the entries
            # exist at all -- #748 died gate-red on exactly this, recovered as
            # #754. `fstring_code_text` now gives every interpreter the
            # 3.14 reading (COO-DECISION 20260904_2153), so a red "still
            # earned" here is a real regression again, on any Python. Do not
            # delete the entries or weaken the check to silence it.
            "columbus_quest3021_dispatch_refused_",
            "columbus_quest3205_dispatch_attempted",
            "columbus_quest3205_dispatch_refused_",
            "columbus_quest_actions",
            "columbus_quest_dispatch",
            "dispatch_columbus_quest3021",
            "dispatch_columbus_quest3205",
            "make_v112_monster_shop_population_state",
            "parse_quest_operate_vital",
            "quest_fields",
            "quest_operate_vital",
            "trade_invite_vital_id",
            "trade_invite_vital_name",
            "ui_trade_wire",
            # CORE-REQUEST 20260904_0137, the pair (chief round `t0funk`,
            # answering lane A's own VENDOR_AND_MISSION_LATCH_WIRING in
            # lane_hooks/lane_a_choose_npc_scene1.py). Two frozen
            # once-per-session flags (v141:3534-3535) read once and
            # written back once, at the one call site that composes the
            # scene-1 responder's answer -- naming an attribute is not
            # settling a trade or granting a quest, the same premise this
            # file already accepts for `columbus_quest3021_conversation_
            # sent` four entries up. Both are inert on the wire today:
            # lane_a_choose_npc_scene1.production_allowed is False, so
            # this responder is never registered.
            "quest3020_conversation_sent",
            "shop_store5_open_sent",
        },
        # `TradeInviteVital` in snake_case -- the PROVEN wire class name -- and
        # its pure encode/decode pair.  Round md7pjz-recovery withdrew a
        # file-level exemption here after finding `\btrade\b` never matched
        # these at all; the reader above does match them, and they are the
        # exact strings that round argued were legitimate.  Naming an opcode
        # is not settling a trade.
        "ui_trade_wire.py": {
            "_trade_invite_fields",
            "decode_trade_invite_payload",
            "encode_trade_invite_payload",
            "trade_invite_vital_id",
            "trade_invite_vital_version",
        },
        # An imported module name.
        "world_m2_columbus_trigger_readiness.py": {"columbus_quest_dispatch"},
        # Same shape, same reason: an imported module name, not quest
        # behavior (chief round zwxuuk, answering
        # pf_bridge/notes_to_chief/20260904_2229_LANE-A-TO-CHIEF-one-line-
        # answer-columbus-quest-dispatch-exemption.md). Reads one integer,
        # COLUMBUS_PLACEMENT_INDEX, off the module in
        # _scenes_where_columbus_collides; renaming the import would only
        # hide the bind, not remove it, since the module it points at is not
        # this lane's to rename.
        "lane_hooks/lane_a_choose_npc_roster_scenes.py": {"columbus_quest_dispatch"},
        # Table pins named after the client's own table, CONSTDATA_TH__ITEM_QUEST
        # (chief round zwxuuk, answering pf_bridge/notes_to_chief/20260904_2230_
        # LANE-GM-TO-CHIEF-item-catalog-two-symbols-are-table-pins-exemption-
        # please.md). QUEST_ITEM_COUNT is a row count for the "quest" item
        # category (one of three the client ships: misc/consumable/quest), not
        # a quest count or quest state; SOURCE_SHA256_QUEST is a drift pin for
        # that category's source TSV, paired with SOURCE_SHA256_MISC /
        # SOURCE_SHA256_CONSUMABLE which the guard does not flag only because
        # those category names don't collide with the guarded word.
        "gm/item_catalog.py": {"quest_item_count", "source_sha256_quest"},
        # Mined QUESTDATA_TH__QUEST row 3021 columns, read into a report
        # string (`console_line`) and an internal consistency check
        # (`_self_check`).  Neither decides a destination; the module's own
        # docstring line 133 says it implements none of this.
        "world_m2_sea_destination.py": {
            "destination_quest_id",
            "destination_quest_row_var2",
        },
    }

    # A data row of world_port_royal_identity._RESOLVED_ROWS, e.g.
    #     (82, 833, 'M070_000_002_N', 'Brin', 'Gold Shop', 105),
    # WIDENED round `7ste68` (LANE-A): the row grew a sixth column, the mined
    # MOBS.n_LEVEL_MIN this scene's census now puts on the wire.  The point of
    # this pattern is unchanged -- "shop" may appear ONLY inside a data row's
    # title field -- and the level is matched as a bare int so a row that grew
    # anything else still goes red.
    IDENTITY_TABLE_ROW = re.compile(
        r"^ {4}\(\d+, \d+, '[^']*', '[^']*', '[^']*', \d+\),$"
    )

    def test_the_identity_tables_shop_hits_are_all_npc_title_data(self):
        """The premise of the one exemption above, checked rather than argued.

        Every line of world_port_royal_identity.py that contains the word
        "shop" must be a row of the crosswalk table - a tuple of (Mob-Set
        number, MOBS.n_ID, s_OUTFIT, MOBS_TIP name, MOBS_TIP title).  If a
        "shop" ever appears in code, in a function name or in a docstring
        promising behaviour, this goes red and the exemption has to be
        re-argued instead of silently covering it.
        """
        path = (
            ROOT / "src/pirateforce_foundation/world_port_royal_identity.py"
        )
        hits = [
            line for line in path.read_text(encoding="utf-8").splitlines()
            # FIXED round `oi2r2n`: this line used the same `\bword\b`
            # the round exists to remove, so `shop_buy` and `SHOP_STOCK`
            # were not even collected as hits and this test passed off the
            # data rows (pf-adversary D3, MEASURED with a planted
            # `def shop_buy`).  It reads the same normaliser the guard does.
            if "shop" in guard_hits(guard_normalise(line))
        ]
        self.assertTrue(hits)
        for line in hits:
            self.assertRegex(line, self.IDENTITY_TABLE_ROW)
            # ...and the word is in the TITLE field -- now the last QUOTED
            # field rather than the last field on the line, since the level
            # column follows it.
            title = line.rsplit("', '", 1)[-1].split("'", 1)[0]
            self.assertIn("shop", title.lower())

    FOUNDATION = ROOT / "src/pirateforce_foundation"

    def _offenders_in(self, directory):
        """The guard itself, over any directory.  ONE implementation.

        Shared with `test_the_guard_catches_what_it_was_blind_to` so that a
        regression in the gate is caught by the test that plants offenders,
        not merely by a test of the helper.  pf-adversary D1 MEASURED the
        previous shape: reverting the guard loop to `\\bword\\b` left both new
        tests green and a planted `settle_trade` invisible, because they
        exercised `guard_hits` directly and nothing exercised the gate.
        """
        # KEY SHAPE (LANE-A, 20260905_0129): keyed by the path RELATIVE to
        # `directory`, not the bare filename -- `ALLOWED_SYMBOLS` already
        # carries two subpackage-prefixed keys
        # (`lane_hooks/lane_a_choose_npc_roster_scenes.py`,
        # `gm/item_catalog.py`) that a bare-filename lookup can never match.
        # They are silently unreachable today only because `glob("*.py")`
        # below is not recursive; a `path.name`-keyed lookup would make both
        # exemptions vanish the moment this glob becomes recursive, turning
        # two already-granted exemptions red without anyone touching either
        # module.  Every existing top-level key (`columbus_quest_dispatch.py`,
        # `ui_trade_wire.py`, ...) is already a valid relative path, so this
        # changes no behavior for any file this guard scans today.
        offenders = {}
        for path in sorted(Path(directory).glob("*.py")):
            key = path.relative_to(directory).as_posix()
            allowed = self.ALLOWED_SYMBOLS.get(key, set())
            unexplained = {}
            source = path.read_text(encoding="utf-8")
            for word, symbols in guard_hits_in_module(source).items():
                left = sorted(s for s in symbols if s not in allowed)
                if left:
                    unexplained[word] = left
            if unexplained:
                offenders[key] = unexplained
        return offenders

    def test_no_foundation_module_implements_quest_or_shop_behavior(self):
        self.assertEqual(self._offenders_in(self.FOUNDATION), {})

    def test_the_guard_catches_what_it_was_blind_to(self):
        """The gate, driven over planted modules.  Not the helper -- the gate.

        Every row is a shape that reached `main` unseen at some point, or that
        pf-adversary planted this round and watched pass.  They are written
        into a temporary directory and run through the SAME `_offenders_in`
        the real guard uses, so a regression in the gate cannot pass this.
        """
        planted = {
            # LANE-UI's original demonstration.
            "plain_snake.py": "def settle_trade(a, b):\n    return a\n",
            # pf-adversary D4: `.lower()` destroys the only boundary a camel
            # name has, so the guard used to read `tradecmdvital`.
            "camel.py": "class TradeCmdVital:\n    def settleTrade(self):\n"
                        "        return 1\n",
            # pf-adversary D4: plurals and trailing digits.
            "plural.py": "QUESTS = {}\nSHOPS = {}\n",
            "digits.py": "def settle_trade2(a):\n    return a\n",
            # pf-adversary D2: this shape passed while the file was cleared
            # for the whole word at file level.
            "runtime_shaped.py": "def settle_trade(seller, buyer, cost):\n"
                                 "    seller.gold += cost\n",
            # pf-adversary D6: a docstring saying the table is ABSENT used to
            # buy clearance for the function that implements it.
            "prose_cover.py": '"""DROPS_QUEST IS ABSENT ON PURPOSE."""\n\n\n'
                              "def drops_quest(set_id, rng):\n    return 1\n",
            # An event token spelled inside an f-string.  Visible from Python
            # 3.12 (PEP 701) and invisible before it, so the guard used to
            # read one thing here and another on the 3.14 gate -- the split
            # that made pirate-force-server#748 pass locally and die on the
            # gate.  `fstring_code_text` closed it; this row keeps it shut.
            "fstring_token.py": "def emit(events, reason):\n"
                                '    events.append(f"shop_open_{reason}")\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, source in planted.items():
                (Path(tmp) / name).write_text(source, encoding="utf-8")
            offenders = self._offenders_in(tmp)
        for name in planted:
            with self.subTest(module=name):
                self.assertIn(
                    name, offenders,
                    "the guard is blind to this shape again",
                )

    def test_the_guard_still_lets_through_what_the_word_edge_protects(self):
        """The other half: over-matching would make the guard unusable noise.

        `request` is not a quest, `in question` is not a quest, and `store` on
        its own is the name of the SQLite persistence module -- which is why
        the word list carries `store5` and not `store`.
        """
        benign = {
            "a.py": "def handle_request(r):\n    return r\n",
            "b.py": "def resolve(x):\n    # the chain in question\n"
                    "    return x\n",
            "c.py": "from .store import SQLiteStore\n",
            "d.py": "def restore5d(x):\n    return x\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, source in benign.items():
                (Path(tmp) / name).write_text(source, encoding="utf-8")
            self.assertEqual(self._offenders_in(tmp), {})

    def test_comments_and_data_strings_are_not_code(self):
        """The contract that deleted five file-level exemptions, pinned.

        A word in a comment or in a mined data string is not behaviour, and
        treating it as one is what forced whole files to be cleared -- which
        is what let real behaviour in beside it.  The same word as a bound
        NAME in the same file must still go red.
        """
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "quiet.py").write_text(
                '"""This module holds no shop and settles no trade."""\n'
                "# price, reward, quest -- all prose\n"
                "ROWS = [(82, 833, 'Brin', 'Gold Shop', 105)]\n",
                encoding="utf-8",
            )
            self.assertEqual(self._offenders_in(tmp), {})
            (Path(tmp) / "loud.py").write_text(
                '"""This module holds no shop."""\n'
                "def shop_buy(npc_id):\n    return npc_id\n",
                encoding="utf-8",
            )
            self.assertEqual(
                self._offenders_in(tmp), {"loud.py": {"shop": ["shop_buy"]}},
            )

    def test_an_fstring_reaches_the_same_guard_verdict_on_any_version(self):
        """One verdict for `f"..."`, whichever interpreter runs the guard.

        Before this, `module_code_text` dropped the whole f-string up to
        Python 3.11 and kept its halves from 3.12 (PEP 701), so the guard was
        a different guard here than on the 3.14 gate -- the split that let
        pirate-force-server#748 pass here and die there.

        Every row is asserted as a guard VERDICT (`guard_hits_in_module`),
        never as the text a reader happens to build: the two tokenizers space
        and split their pieces differently, and pinning that spacing is how
        the first version of this test came out green on 3.11 and red on
        3.12+ (pf-adversary D1, this round).  The verdict is what the guard
        acts on, so the verdict is what has to match.
        """
        rows = [
            # The shape that forced the runtime.py exemption entries.
            ('e.append(f"columbus_quest3021_dispatch_refused_{reason}")',
             {"quest": {"columbus_quest3021_dispatch_refused_"}}),
            # A call inside a field is behaviour and must be seen.
            ('x = f"shop_{npc.settle_trade()}_done"',
             {"shop": {"shop_"}, "trade": {"settle_trade"}}),
            # Doubled braces are literal text; the word survives them.
            ('x = f"{{price}}_paid"', {"price": {"price"}}),
            # Nested field: the format spec carries its own field.
            ('x = f"reward_{amount:>{width}}"', {"reward": {"reward_"}}),
            # Escapes are NOT decoded -- `\\N{...}` spells a word on the gate.
            ('x = f"\\N{TRADE MARK SIGN}"', {"trade": {"trade"}}),
            # A string literal inside a field is prose here as on the gate.
            ("x = f\"{row['Gold Shop']}\"", {}),
            # An escape that GLUES a word to the next letter must not be
            # decoded either: the gate reads `shop`, so this reads `shop`.
            ('x = f"shop\\x73omething_{a}"', {"shop": {"shop"}}),
            # A backslash inside a replacement field is PEP 701 syntax, legal
            # only from 3.12.  The 3.11 reader must still see the call --
            # the first version of this function handed it to `ast.parse`,
            # got a SyntaxError and dropped the whole token in silence
            # (pf-adversary D2).
            ('x = f"{ m[\'a\\tb\'].settle_trade() }"',
             {"trade": {"settle_trade"}}),
            # Prefix-order and quoting variants.
            ("x = rf'''trade_{y}'''", {"trade": {"trade_"}}),
            ('x = F"quest_{y}"', {"quest": {"quest_"}}),
            # No field at all -- still an f-string, still code.
            ('x = f"drops_quest"', {"quest": {"drops_quest"}}),
            # A plain string is still prose, f-prefix or not.
            ('x = "shop_open"', {}),
        ]
        for source, expected in rows:
            with self.subTest(source=source):
                self.assertEqual(guard_hits_in_module(source), expected)
        self.assertIsNone(fstring_code_text('"shop_open"'))
        self.assertIsNone(fstring_code_text('b"shop_open"'))

    def test_the_fstring_reader_is_driven_directly_not_only_by_the_gate(self):
        """The rows above are inert on the interpreter that gates.  These are not.

        From 3.12 an f-string is FSTRING_START/MIDDLE/END, none of which is
        `tokenize.STRING`, so `module_code_text` never calls
        `fstring_code_text` there at all: `_closing_brace` is reached ZERO
        times on 3.13 over the whole package.  pf-adversary proved the
        consequence by replacing this function's body with `return None` --
        12 tests fail on 3.11 and all 30 stay green on 3.13 (D2, second
        pass).  The gate runs one interpreter, 3.14, so every row above is a
        check that cannot fail where CI looks.

        These assertions call the reader directly, so they discriminate on
        any interpreter.  Each row is a mutant pf-adversary found surviving.
        """
        # The format-spec fill character.  Reading `'` here as an opening
        # quote swallowed the field's own closing brace and hid a real call
        # from the guard on 3.11 while the 3.14 gate reported it (D1).
        self.assertEqual(_closing_brace("{a:'>5}{settle_trade()}'", 0), 6)
        self.assertEqual(
            guard_hits_in_module('def f(a):\n    return f"{a:\'>5}'
                                 '{settle_trade()}\'"\n'),
            {"trade": {"settle_trade"}},
        )
        # Quote-awareness outside a spec: a brace inside a string is not
        # structural.  Deleting the branch left every test green before (D4).
        self.assertEqual(_closing_brace("{d['}']}x", 0), 7)
        # A colon inside brackets does not open a format spec.
        self.assertEqual(_closing_brace("{f(x, ':')}", 0), 10)
        # A nested field inside the spec closes back into the spec.
        self.assertEqual(_closing_brace("{a:>{width}}", 0), 11)
        # Unbalanced input terminates at the end of the body.
        self.assertEqual(_closing_brace("{a", 0), 2)
        # The doubled-brace rule.  The `{{price}}` row above passes even
        # without it (the raw-source fallback puts `price` back); this one
        # does not -- delete the rule and the slice tokenizes as a dict
        # display whose key is a dropped string literal (D4).
        self.assertEqual(
            guard_hits_in_module('x = f"{{\'quest\': 1}}"\n'),
            {"quest": {"quest"}},
        )
        # ...and driven directly, so the row above cannot be the only witness
        # on 3.12+, where `guard_hits_in_module` never reaches this reader.
        self.assertIn("quest", fstring_code_text('f"{{\'quest\': 1}}"'))
        # Literal halves and fields, read directly.
        self.assertEqual(
            fstring_code_text('f"drops_quest_{set_id}"').split(),
            ["drops_quest_", "set_id"],
        )
        self.assertIsNone(fstring_code_text('"drops_quest"'))

    def test_a_guard_word_reached_by_getattr_is_named(self):
        """The one string-literal hole worth closing by hand.

        Dropping string literals means `getattr(mod, "settle_trade")` would
        be invisible (pf-adversary D4).  Rather than re-scan every string --
        which is what put mined data rows in front of this guard in the first
        place -- only the second argument of a `getattr` call is read.
        """
        for source, expected in (
            ('getattr(mod, "settle_trade")', True),
            ("getattr(mod, 'accept_quest')", True),
            ('getattr(mod, "position")', False),
        ):
            with self.subTest(source=source):
                names = re.findall(
                    r"""getattr\([^,]+,\s*['"]([A-Za-z0-9_]+)['"]""", source
                )
                hit = any(guard_hits(guard_normalise(n)) for n in names)
                self.assertEqual(hit, expected)

    def test_no_foundation_module_reaches_a_guard_word_by_getattr(self):
        offenders = {}
        for path in sorted(self.FOUNDATION.glob("*.py")):
            names = re.findall(
                r"""getattr\([^,]+,\s*['"]([A-Za-z0-9_]+)['"]""",
                path.read_text(encoding="utf-8"),
            )
            named = sorted(n for n in names if guard_hits(guard_normalise(n)))
            if named:
                offenders[path.name] = named
        self.assertEqual(offenders, {})

    def test_the_unscanned_subpackages_are_named_and_counted(self):
        """The guard's scope, measured instead of assumed.

        `glob("*.py")` is not recursive, so every subpackage of
        `pirateforce_foundation` has been outside this guard since it was
        written -- 46 modules at the time pf-adversary measured it (D5).
        Widening the scan is a cross-lane change chief did not make on his
        own; naming the gap is the honest half he can. This test fails when
        a NEW subpackage appears, so the gap cannot grow unnoticed, and it
        prints the count so nobody reads a green run as full coverage.
        """
        # "lua_api" added by LANE-Q round s2fxf6, re-arguing the scope as
        # this test's docstring requires: it is the package the charter
        # (prompts/LANE-Q.md) names for the game's 160-function script API,
        # one module per namespace as each stops being a stub.  Today it
        # holds only the frozen census reader (spec.py) and its TSV, which
        # define no wire symbol this guard looks for; the modules that WILL
        # (lua_api/trigger.py, quest.py, ...) do not exist yet.  The gap
        # this test exists to name therefore grows by a package that is
        # currently empty of the thing being guarded - and the round that
        # lands the first real namespace module is the round that has to
        # argue for widening the scan itself, not just this set.
        known = {"data", "gm", "lane_hooks", "lua_api", "world_data"}
        present = {
            child.name for child in self.FOUNDATION.iterdir()
            if child.is_dir() and not child.name.startswith("__")
        }
        self.assertEqual(
            present, known,
            "a subpackage appeared or vanished -- this guard does not scan "
            "any of them; re-argue the scope before changing this set",
        )
        unscanned = sum(
            1 for child in self.FOUNDATION.rglob("*.py")
            if child.parent != self.FOUNDATION
        )
        self.assertGreater(unscanned, 0)

    def test_every_symbol_exemption_is_still_earned(self):
        """An exemption that no longer matches anything is a hole.

        A per-symbol list rots in a way a per-file one cannot: rename
        `destination_quest_id` and the entry stays behind, pre-approving
        nothing today and whatever re-uses the name tomorrow.  Every entry
        must still be a live CODE hit in the module it is written under --
        the same text the guard reads, so an entry cannot be kept alive by a
        comment (pf-adversary D6/D7: the previous version scanned raw source
        and its docstring claimed a per-word check the data shape could not
        support).
        """
        for name, symbols in sorted(self.ALLOWED_SYMBOLS.items()):
            path = self.FOUNDATION / name
            with self.subTest(module=name):
                self.assertTrue(path.exists(), "exemption names a dead module")
                live = set()
                for found in guard_hits_in_module(
                    path.read_text(encoding="utf-8")
                ).values():
                    live |= found
                self.assertEqual(
                    sorted(set(symbols) - live), [],
                    "exemption no longer matches any code name here",
                )

    def test_the_ocean_panels_trade_hits_are_all_mined_npc_name_data(self):
        """The premise of the newest exemption above, checked not argued.

        Every line of world_bg3001_identity.py containing "trade" must be a
        row of that scene's crosswalk table with the word inside its QUOTED
        NAME field - the mined ``MOBS_TIP.s_NAME`` of three placements.  If
        the word ever appears in code, in a function name, or in a docstring
        promising behaviour, this goes red and the exemption is re-argued.
        """
        path = (
            ROOT / "src/pirateforce_foundation/world_bg3001_identity.py"
        )
        hits = [
            line for line in path.read_text(encoding="utf-8").splitlines()
            # FIXED round `oi2r2n`, same defect as its sibling above.
            if "trade" in guard_hits(guard_normalise(line))
        ]
        self.assertTrue(hits)
        for line in hits:
            with self.subTest(line=line.strip()[:60]):
                quoted = re.findall(r"'([^']*)'", line)
                self.assertTrue(
                    any("trade" in field.lower() for field in quoted),
                    "the word is outside every quoted data field",
                )
                without_data = re.sub(r"'[^']*'", "''", line)
                self.assertNotIn(
                    "trade", guard_hits(guard_normalise(without_data)),
                    "the word is doing something outside the data field",
                )

    def test_store5_open_packet_is_a_harness_with_no_product_list(self):
        pc, _ = self.v.make_trade_zoom_store5()
        vital = self.v.u16tag(0x12, self.v.TRADE_ZOOM_VITAL) + self.v.u8tag(0x0B, 2)
        body = pc[pc.index(vital) + len(vital):]
        self.assertEqual(
            body,
            self.v.u8tag(0x08, 2)
            + self.v.u8tag(0x08, 2)
            + self.v.qwordtag(0x32, 0)
            + self.v.u32tag(0x14, self.v.V112_STORE_ID)
            + self.v.wstr_tag("")
            + self.v.u16tag(0x0F, 0)
            + self.v.u8tag(0x0B, 0),
        )
        self.assertEqual(self.v.V112_STORE_ID, 5)


class InteractionNegativePathTests(unittest.TestCase):
    """coverage row npc_interaction/interaction_negative_paths.

    V140 only passed after an explicit synthetic harness position replaced the
    decoded placement of P86. These tests keep that substitution visible.
    """

    @classmethod
    def setUpClass(cls):
        cls.v = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_p86_identity_follows_the_index_rule(self):
        self.assertEqual(self.v.V139_P86_INDEX, 86)
        self.assertEqual(self.v.V139_P86_ACTOR_ID, 0x2000 + 86 + 1)

    def test_harness_position_is_an_explicit_offset_from_marker1(self):
        self.assertEqual(self.v.V140_P86_HARNESS_X, self.v.V137_MARKER_X + 100.0)
        self.assertEqual(self.v.V140_P86_HARNESS_Y, self.v.V137_MARKER_Y + 50.0)
        self.assertEqual(self.v.V140_P86_HARNESS_Z, self.v.V137_MARKER_Z)

    def test_harness_position_is_not_the_decoded_placement_of_p86(self):
        rows = self.v._v94_nearest_population(
            self.v.V137_MARKER_X, self.v.V137_MARKER_Y, self.v.V137_MARKER_Z
        )
        placements = {row[0]: (row[2], row[3], row[4]) for row in rows}
        self.assertIn(self.v.V139_P86_INDEX, placements)
        decoded = placements[self.v.V139_P86_INDEX]
        harness = (
            self.v.V140_P86_HARNESS_X,
            self.v.V140_P86_HARNESS_Y,
            self.v.V140_P86_HARNESS_Z,
        )
        self.assertNotEqual(decoded, harness)
        # No other decoded actor sits on the harness point either, so the
        # substitution can never be mistaken for real population data.
        self.assertNotIn(harness, set(placements.values()))

    def test_decoded_population_snapshot_never_carries_the_harness_position(self):
        _pc, _frame, rows = self.v.make_v138_marker1_population_state()
        placements = {row[0]: (row[2], row[3], row[4]) for row in rows}
        harness = (
            self.v.V140_P86_HARNESS_X,
            self.v.V140_P86_HARNESS_Y,
            self.v.V140_P86_HARNESS_Z,
        )
        self.assertNotIn(harness, set(placements.values()))

    def test_harness_snapshot_moves_only_p86(self):
        _pc, _frame, plain_rows = self.v.make_v138_marker1_population_state()
        harness_pc, _harness_frame, harness_rows = (
            self.v.make_v140_marker1_population_state()
        )
        self.assertEqual(
            [row[0] for row in plain_rows], [row[0] for row in harness_rows]
        )
        harness_xyz = b"".join(
            self.v.f32tag(value)
            for value in (
                self.v.V140_P86_HARNESS_X,
                self.v.V140_P86_HARNESS_Y,
                self.v.V140_P86_HARNESS_Z,
            )
        )
        self.assertEqual(harness_pc.count(harness_xyz), 1)


if __name__ == "__main__":
    unittest.main()
