"""LANE-Q round `6775u1`: the message-wire seam, and the two names on it.

`Player.ShowMessage` (61 call sites) and `Trigger.TriggerShowMessage` (55)
become real against `lua_api/message.py`'s catalog + sink.  These tests pin
the RETURNED VALUE and the recorded SIDE EFFECT, never the presence of a
name -- the posture AGENTS.md section 7 ("WIRED means observed, not named")
requires of a new seam.

No lupa here on purpose: every test below is a namespace-contract test that
runs with or without the Lua runtime, so this file adds no new skip pin.
The Lua-integration half lives in `test_script_host_spike.py` /
`test_script_lua_corpus.py`, which already own the lupa pin.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.lua_api import message, player, trigger

# Every literal message id the 616-file corpus passes to one of the three
# message names, transcribed from the grep recorded in this round's file.
# If the vendored catalog ever stops covering one of them, the derivation in
# `message.py`'s docstring is wrong and this file says so out loud.
CORPUS_PLAYER_IDS = (1, 4, 421, 824, 855, 856, 859, 860, 882, 885, 890, 897)
CORPUS_TRIGGER_IDS = (914, 915, 916, 917, 918, 919, 920, 921)


class MessageCatalogTests(unittest.TestCase):

    def test_the_catalog_is_the_shipped_table_not_a_range(self):
        self.assertEqual(len(message.CATALOG), 907)
        self.assertEqual(message.MAX_MESSAGE_ID, 961)
        # 907 rows inside 1..961 means the id space has holes -- a plain
        # range check would wave through ids the game never shipped.
        self.assertFalse(message.is_known_message_id(962))
        self.assertFalse(message.is_known_message_id(0))
        holes = [i for i in range(1, 962) if not message.is_known_message_id(i)]
        self.assertTrue(holes, "a hole-free table would make this test vacuous")

    def test_every_literal_id_the_corpus_passes_has_a_row(self):
        for message_id in CORPUS_PLAYER_IDS + CORPUS_TRIGGER_IDS:
            with self.subTest(message_id=message_id):
                self.assertTrue(message.is_known_message_id(message_id))
                self.assertIsNotNone(message.notify_type(message_id))

    def test_notify_type_of_an_unknown_id_is_none_not_a_default(self):
        self.assertIsNone(message.notify_type(962))

    def test_the_audience_domain_is_the_four_the_corpus_branches_on(self):
        self.assertEqual(
            message.AUDIENCES,
            frozenset({0, 1, 2, 3}))
        self.assertEqual(
            [message.audience_name(a) for a in (0, 1, 2, 3)],
            ["individual", "party", "scene", "channel"])
        self.assertEqual(message.audience_name(4), "?")


class InMemoryMessageSinkTests(unittest.TestCase):

    def test_records_in_order_and_reports_the_count_read_back(self):
        sink = message.InMemoryMessageSink()
        self.assertEqual(sink.record(7, message.AUDIENCE_INDIVIDUAL, 856), 1)
        self.assertEqual(sink.record(7, message.AUDIENCE_SCENE, 919), 2)
        self.assertEqual(sink.messages_for(7), ((0, 856), (2, 919)))

    def test_one_character_cannot_read_or_fill_another_characters_record(self):
        sink = message.InMemoryMessageSink(messages_per_character=2)
        sink.record(7, 0, 856)
        sink.record(7, 0, 859)
        self.assertEqual(sink.record(7, 0, 855), 2)  # capped, not evicted
        self.assertEqual(sink.messages_for(7), ((0, 856), (0, 859)))
        # The looping character did not consume anyone else's budget.
        self.assertEqual(sink.record(8, 0, 855), 1)
        self.assertEqual(sink.messages_for(8), ((0, 855),))

    def test_a_full_sink_refuses_a_new_character_without_evicting_anyone(self):
        sink = message.InMemoryMessageSink(characters=1)
        sink.record(7, 0, 856)
        self.assertEqual(sink.record(8, 0, 856), 0)
        self.assertEqual(sink.messages_for(8), ())
        self.assertEqual(sink.messages_for(7), ((0, 856),))

    def test_a_nonsense_cap_is_a_caller_error_and_raises(self):
        for kwargs in ({"characters": 0}, {"messages_per_character": 0},
                        {"characters": True}, {"messages_per_character": 1.5}):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError):
                    message.InMemoryMessageSink(**kwargs)


class PlayerShowMessageTests(unittest.TestCase):

    def setUp(self):
        self.lines = []
        self.sink = message.InMemoryMessageSink()
        self.namespace = player.build_namespace(
            frozenset({"ShowMessage"}), self.lines.append,
            context=player.PlayerContext(character_id=7), sink=self.sink)

    def test_a_known_id_is_recorded_for_this_character_as_individual(self):
        self.assertEqual(self.namespace["ShowMessage"](856), 1)
        self.assertEqual(self.sink.messages_for(7),
                          ((message.AUDIENCE_INDIVIDUAL, 856),))
        self.assertEqual(self.sink.messages_for(0), ())

    def test_it_is_real_not_a_stub(self):
        self.namespace["ShowMessage"](856)
        self.assertEqual(
            [line for line in self.lines if line.startswith("LUA_API_STUB")], [])
        self.assertIn("LUA_PLAYER_REAL Player.ShowMessage", self.lines[0])

    def test_an_id_with_no_row_is_refused_and_never_recorded(self):
        self.assertEqual(self.namespace["ShowMessage"](962), player.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(7), ())
        self.assertTrue(self.lines[0].startswith("LUA_PLAYER_BAD_VALUE"))

    def test_a_lua_float_that_is_a_whole_number_is_accepted(self):
        # lupa hands Lua numbers back as floats; 856.0 IS message 856.
        self.assertEqual(self.namespace["ShowMessage"](856.0), 1)
        self.assertEqual(self.sink.messages_for(7), ((0, 856),))

    def test_a_bool_is_not_message_id_one(self):
        self.assertEqual(self.namespace["ShowMessage"](True), player.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(7), ())

    def test_wrong_arity_is_refused_and_never_recorded(self):
        for args in ((), (856, 2)):
            with self.subTest(args=args):
                self.assertEqual(
                    self.namespace["ShowMessage"](*args), player.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(7), ())
        self.assertTrue(all(
            line.startswith("LUA_PLAYER_BAD_ARITY") for line in self.lines))

    def test_a_broken_sink_raises_rather_than_degrading_to_silence(self):
        class Broken:
            def record(self, *_args):
                raise RuntimeError("sink is down")

            def messages_for(self, _character_id):
                return ()

        namespace = player.build_namespace(
            frozenset({"ShowMessage"}), self.lines.append, sink=Broken())
        with self.assertRaises(RuntimeError):
            namespace["ShowMessage"](856)


class TriggerShowMessageTests(unittest.TestCase):

    def setUp(self):
        self.lines = []
        self.sink = message.InMemoryMessageSink()
        self.namespace = trigger.build_namespace(
            frozenset({"TriggerShowMessage"}), self.lines.append,
            sink=self.sink)

    def test_each_audience_in_the_domain_is_recorded_as_given(self):
        for index, audience in enumerate(sorted(message.AUDIENCES)):
            with self.subTest(audience=audience):
                self.assertEqual(
                    self.namespace["TriggerShowMessage"](audience, 919),
                    index + 1)
        self.assertEqual(
            self.sink.messages_for(0),
            ((0, 919), (1, 919), (2, 919), (3, 919)))

    def test_an_audience_outside_the_domain_is_refused_not_clamped(self):
        for audience in (4, -1, 99):
            with self.subTest(audience=audience):
                self.assertEqual(
                    self.namespace["TriggerShowMessage"](audience, 919),
                    trigger.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(0), ())

    def test_an_id_with_no_row_is_refused_and_never_recorded(self):
        self.assertEqual(
            self.namespace["TriggerShowMessage"](2, 962), trigger.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(0), ())
        self.assertTrue(self.lines[0].startswith("LUA_TRIGGER_BAD_VALUE"))

    def test_wrong_arity_is_refused_and_never_recorded(self):
        for args in ((), (919,), (2, 919, 0)):
            with self.subTest(args=args):
                self.assertEqual(
                    self.namespace["TriggerShowMessage"](*args),
                    trigger.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(0), ())


class OneScriptHostSharesOneMessageSinkTests(unittest.TestCase):
    """Player and Trigger inside one host run land in ONE ordered record.

    Mutation guard: make `ScriptHost` stop normalizing the sink (let each
    build_namespace take its own private default) and this test fails --
    the two namespaces would each hold their own empty bucket.
    """

    def test_player_then_trigger_share_one_ordered_record(self):
        from pirateforce_foundation.script_host import ScriptHost

        host = ScriptHost(log=lambda _line: None)
        self.assertEqual(host.namespaces["Player"]["ShowMessage"](856), 1)
        self.assertEqual(
            host.namespaces["Trigger"]["TriggerShowMessage"](2, 919), 2)
        self.assertEqual(
            host.namespaces["Player"]._sink.messages_for(0),
            ((0, 856), (2, 919)))

    def test_an_injected_sink_is_the_one_both_namespaces_write_to(self):
        from pirateforce_foundation.script_host import ScriptHost

        sink = message.InMemoryMessageSink()
        host = ScriptHost(log=lambda _line: None, message_sink=sink)
        host.namespaces["Player"]["ShowMessage"](856)
        host.namespaces["Trigger"]["TriggerShowMessage"](2, 919)
        self.assertEqual(sink.messages_for(0), ((0, 856), (2, 919)))

    def test_two_hosts_do_not_share_the_default_sink(self):
        from pirateforce_foundation.script_host import ScriptHost

        first = ScriptHost(log=lambda _line: None)
        second = ScriptHost(log=lambda _line: None)
        first.namespaces["Player"]["ShowMessage"](856)
        self.assertEqual(
            second.namespaces["Player"]._sink.messages_for(0), ())


class NoLaneQModuleBuildsTheVitalTests(unittest.TestCase):
    """This lane records message IDS; it never builds `ShowMessageVital`.

    `tests/test_system_message_wire.py` already guards the top-level
    Foundation package with the same claim, but its glob is not recursive,
    so `lua_api/` -- where this round's code lives -- is outside it.  This
    is that guard for this lane's own directory, so the coverage row
    `chat/server_system_message` ("emitted by the frozen legacy seam, no
    Foundation module owns it") cannot go stale behind this package's back.
    """

    def test_no_lua_api_module_references_the_vital(self):
        # AST, not substring: `message.py`'s own docstring NAMES the vital
        # and the legacy builder on purpose (that is the handoff note for
        # whoever emits the frame).  Naming it in prose is the opposite of
        # owning it; what would be ownership is CODE that reaches for it,
        # which is what this walk looks for.
        import ast

        forbidden = {"make_show_message", "SHOW_MESSAGE_VITAL",
                     "ShowMessageVital"}
        offenders = []
        for path in sorted((ROOT / "src/pirateforce_foundation/lua_api").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            used = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used.add(node.attr)
                elif isinstance(node, ast.Constant) and isinstance(node.value, int):
                    if node.value == 0x36D2:
                        used.add("ShowMessageVital")
            if used & forbidden:
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_that_guard_would_actually_catch_a_module_that_did(self):
        import ast

        tree = ast.parse("from ..legacy import v\nPC = v.make_show_message('x')\n")
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertIn("make_show_message", attrs)

    def test_script_host_does_not_reference_the_vital_either(self):
        text = (ROOT / "src/pirateforce_foundation/script_host.py").read_text(
            encoding="utf-8")
        self.assertNotIn("SHOW_MESSAGE", text.upper())


if __name__ == "__main__":
    unittest.main()
