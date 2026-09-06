"""LANE-Q round `6775u1`: the message-wire seam, and the two names on it.

`Player.ShowMessage` (61 call sites) and `Trigger.TriggerShowMessage` (55)
become real against `lua_api/message.py`'s catalog + sink.  These tests pin
the RETURNED VALUE and the recorded SIDE EFFECT, never the presence of a
name -- the posture AGENTS.md section 7 ("WIRED means observed, not named")
requires of a new seam.

Round `7kxfe9` measured this module in the three machine states it can be
run in and found TWO classes that need something a fresh clone has not
got, where round `6775u1`'s own header claimed there were none ("no lupa
here on purpose: every test below ... runs with or without the Lua
runtime").  That sentence was false as written: three
`OneScriptHostSharesOneMessageSinkTests` tests build a real `ScriptHost`,
which raises without lupa, so on a lupa-free machine this module was RED
rather than skipped -- an unguarded dependency, which is exactly what
docs/PYTEST_SKIP_PINS.json exists to stop.  Both classes are now guarded
and pinned:

  * `OneScriptHostSharesOneMessageSinkTests` under LUPA_PACKAGE (3 tests).
  * `VendoredCatalogMatchesTheRealTableTests` under BRIDGE_GAMEDATA (2) --
    the drift tie between the vendored catalog and the game's own table.  It USED to live in `test_script_lua_corpus.py`, whose
composite key also demands lupa; comparing two TSV files never needed a Lua
runtime, so on a bridge machine with no lupa the one test that proves the
copy is honest was silently not running.  Moving it here is a strict
widening of where it runs (skip census re-measured in the same round).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_preconditions import BRIDGE_GAMEDATA, LUPA_PACKAGE, SIBLING

from pirateforce_foundation.lua_api import message, player, trigger

SOURCE_TABLE = (SIBLING / "pf_bridge" / "gamedata" / "tables"
                / "TEXTDATA_TH__MESSAGE.tsv")

# Every literal message id the 616-file corpus passes to one of the three
# message names, transcribed from the grep recorded in this round's file.
# If the vendored catalog ever stops covering one of them, the derivation in
# `message.py`'s docstring is wrong and this file says so out loud.
CORPUS_PLAYER_IDS = (1, 4, 421, 824, 855, 856, 859, 860, 882, 885, 890, 897)
CORPUS_TRIGGER_IDS = (914, 915, 916, 917, 918, 919, 920, 921)


class MessageCatalogTests(unittest.TestCase):

    def test_the_catalog_is_the_shipped_table_not_a_range(self):
        self.assertEqual(len(message.catalog()), 907)
        self.assertEqual(message.max_message_id(), 961)
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

    def test_an_individual_message_goes_to_the_characters_own_bucket(self):
        sink = message.InMemoryMessageSink()
        self.assertEqual(
            sink.record(None, 7, message.AUDIENCE_INDIVIDUAL, 856), 1)
        self.assertEqual(sink.record(None, 7, message.AUDIENCE_PARTY, 855), 2)
        self.assertEqual(sink.messages_for(7), ((0, 856), (1, 855)))
        self.assertEqual(sink.messages_for(8), ())

    def test_a_scene_message_goes_to_the_scene_not_the_triggering_character(self):
        # The defect this shape exists to prevent: an arena announcement
        # filed under one character is invisible to the second player in
        # the same scene.
        sink = message.InMemoryMessageSink()
        self.assertEqual(sink.record("bg2017", 7, message.AUDIENCE_SCENE, 918), 1)
        self.assertEqual(sink.record("bg2017", 7, message.AUDIENCE_CHANNEL, 919), 2)
        self.assertEqual(sink.messages_for(7), ())
        self.assertEqual(
            sink.broadcasts_for("bg2017"), ((2, 918, 7), (3, 919, 7)))
        # Player 9, who never fired anything, reads the same scene bucket.
        self.assertEqual(
            sink.broadcasts_for("bg2017")[0][:2], (message.AUDIENCE_SCENE, 918))
        self.assertEqual(sink.broadcasts_for("bg0002"), ())

    def test_a_scene_message_with_no_scene_is_refused_not_downgraded(self):
        sink = message.InMemoryMessageSink()
        for scene in (None, ""):
            with self.subTest(scene=scene):
                self.assertEqual(
                    sink.record(scene, 7, message.AUDIENCE_SCENE, 918), 0)
        self.assertEqual(sink.messages_for(7), ())

    def test_a_refused_write_returns_zero_so_a_drop_is_not_a_success(self):
        sink = message.InMemoryMessageSink(messages_per_character=2)
        self.assertEqual(sink.record(None, 7, 0, 856), 1)
        self.assertEqual(sink.record(None, 7, 0, 859), 2)
        self.assertEqual(sink.record(None, 7, 0, 855), 0)  # dropped, not "2"
        self.assertEqual(sink.messages_for(7), ((0, 856), (0, 859)))
        # The looping character did not consume anyone else's budget.
        self.assertEqual(sink.record(None, 8, 0, 855), 1)

    def test_a_full_sink_refuses_a_new_bucket_without_evicting_anyone(self):
        sink = message.InMemoryMessageSink(characters=1, scenes=1)
        sink.record(None, 7, 0, 856)
        self.assertEqual(sink.record(None, 8, 0, 856), 0)
        self.assertEqual(sink.messages_for(8), ())
        self.assertEqual(sink.messages_for(7), ((0, 856),))
        sink.record("bg2017", 7, 2, 918)
        self.assertEqual(sink.record("bg0002", 7, 2, 918), 0)
        self.assertEqual(sink.broadcasts_for("bg0002"), ())
        self.assertEqual(sink.broadcasts_for("bg2017"), ((2, 918, 7),))

    def test_one_scene_cannot_fill_another_scenes_bucket(self):
        sink = message.InMemoryMessageSink(messages_per_scene=1)
        self.assertEqual(sink.record("bg2017", 7, 2, 918), 1)
        self.assertEqual(sink.record("bg2017", 7, 2, 919), 0)
        self.assertEqual(sink.record("bg0002", 7, 2, 919), 1)

    def test_a_nonsense_cap_is_a_caller_error_and_raises(self):
        for kwargs in ({"characters": 0}, {"messages_per_character": 0},
                        {"scenes": 0}, {"messages_per_scene": 0},
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

            def record_refusal(self, _reason):
                return 0

            def messages_for(self, _character_id):
                return ()

            def broadcasts_for(self, _scene):
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

    def test_each_audience_lands_in_the_bucket_that_audience_names(self):
        for audience in sorted(message.AUDIENCES):
            with self.subTest(audience=audience):
                self.assertTrue(
                    self.namespace["TriggerShowMessage"](audience, 919))
        # 0/1 belong to the character; 2/3 belong to the scene, and the
        # scene entries carry which character's trigger fired them.
        self.assertEqual(self.sink.messages_for(0), ((0, 919), (1, 919)))
        self.assertEqual(
            self.sink.broadcasts_for("unscoped_default"),
            ((2, 919, 0), (3, 919, 0)))

    def test_a_second_player_in_the_scene_reads_the_same_broadcast(self):
        # The whole point of keying 2/3 by scene: player 9 never fired
        # anything and still has the announcement.
        first = trigger.build_namespace(
            frozenset({"TriggerShowMessage"}), self.lines.append,
            context=trigger.TriggerContext(scene="bg2017", trigger_id=26),
            sink=self.sink)
        first["TriggerShowMessage"](message.AUDIENCE_SCENE, 918)
        self.assertEqual(self.sink.broadcasts_for("bg2017"), ((2, 918, 0),))
        self.assertEqual(self.sink.messages_for(9), ())

    def test_an_audience_outside_the_domain_is_refused_not_clamped(self):
        for audience in (4, -1, 99):
            with self.subTest(audience=audience):
                self.assertEqual(
                    self.namespace["TriggerShowMessage"](audience, 919),
                    trigger.STUB_DEFAULT)
        self.assertEqual(self.sink.messages_for(0), ())
        self.assertEqual(self.sink.broadcasts_for("unscoped_default"), ())

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


@LUPA_PACKAGE.skip_unless_present()
class OneScriptHostSharesOneMessageSinkTests(unittest.TestCase):
    """Player and Trigger inside one host run land in ONE ordered record.

    Mutation guard: make `ScriptHost` stop normalizing the sink (let each
    build_namespace take its own private default) and this test fails --
    the two namespaces would each hold their own empty bucket.
    """

    def test_player_then_trigger_share_one_sink(self):
        from pirateforce_foundation.script_host import ScriptHost

        host = ScriptHost(log=lambda _line: None)
        self.assertEqual(host.namespaces["Player"]["ShowMessage"](856), 1)
        # An individual message from Player and a party message from
        # Trigger land in ONE character bucket, in order -- that is the
        # shared-sink property. (A 2/3 audience would land in the scene
        # bucket instead, which is a different bucket by design.)
        self.assertEqual(
            host.namespaces["Trigger"]["TriggerShowMessage"](1, 919), 2)
        self.assertEqual(
            host.namespaces["Player"]._sink.messages_for(0),
            ((0, 856), (1, 919)))

    def test_an_injected_sink_is_the_one_both_namespaces_write_to(self):
        from pirateforce_foundation.script_host import ScriptHost

        sink = message.InMemoryMessageSink()
        host = ScriptHost(
            log=lambda _line: None, message_sink=sink,
            trigger_context=trigger.TriggerContext(scene="bg2017", trigger_id=26))
        host.namespaces["Player"]["ShowMessage"](856)
        host.namespaces["Trigger"]["TriggerShowMessage"](2, 919)
        self.assertEqual(sink.messages_for(0), ((0, 856),))
        self.assertEqual(sink.broadcasts_for("bg2017"), ((2, 919, 0),))

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


class EscapeRoundTripTests(unittest.TestCase):
    """The vendored file is ASCII BY CONSTRUCTION, and reversibly so."""

    def test_every_shipped_row_survives_encode_then_decode_exactly(self):
        for message_id, (_type, _notify, text) in message.catalog().items():
            with self.subTest(message_id=message_id):
                escaped = message.escape_message_text(text)
                self.assertEqual(message.unescape_message_text(escaped), text)

    def test_the_escape_of_every_shipped_row_is_pure_ascii(self):
        for message_id, (_t, _n, text) in message.catalog().items():
            with self.subTest(message_id=message_id):
                escaped = message.escape_message_text(text)
                escaped.encode("ascii")  # raises if it is not

    def test_a_literal_backslash_does_not_become_an_escape_on_the_way_back(self):
        # The source table has no backslash today (grepped, round 7kxfe9:
        # zero of 907 rows).  That is a fact about TODAY's table, not a
        # property of the format, so the encoder escapes the backslash
        # itself and this test is what stops a future row from silently
        # turning `เ` typed by a translator into a Thai character.
        for text in ("a\\b", "\\u0e40", "\\\\", "back\\slash"):
            with self.subTest(text=text):
                escaped = message.escape_message_text(text)
                self.assertNotIn("\\\\", escaped.replace("\\u005c", ""))
                self.assertEqual(message.unescape_message_text(escaped), text)

    def test_tabs_and_newlines_cannot_break_the_row_shape(self):
        # A tab in a text column would split one row into two fields and a
        # newline would split it into two rows; both are escaped away.
        escaped = message.escape_message_text("a\tb\nc\r")
        self.assertNotIn("\t", escaped)
        self.assertNotIn("\n", escaped)
        self.assertNotIn("\r", escaped)
        self.assertEqual(message.unescape_message_text(escaped), "a\tb\nc\r")


class VendoredCatalogFileTests(unittest.TestCase):
    """What the vendored file can prove about ITSELF, with no bridge beside
    this clone -- which is the state most machines that run this suite are
    in.  The tie to the real table is the next class down; this one catches
    the half that does not need the source: a hand-edit that adds or drops
    a row, or a header that has stopped describing the body under it."""

    def setUp(self):
        self.path = (ROOT / "src" / "pirateforce_foundation" / "lua_api"
                     / "message_catalog.tsv")
        self.raw = self.path.read_bytes()

    def test_the_file_on_disk_is_pure_ascii(self):
        self.raw.decode("ascii")
        self.assertEqual([b for b in self.raw if b > 127], [])

    def test_the_header_names_its_source_and_a_digest_of_it(self):
        header = [line for line in self.raw.decode("ascii").splitlines()
                  if line.startswith("#")]
        joined = "\n".join(header)
        self.assertIn("# source: pf_bridge/gamedata/tables/"
                      "TEXTDATA_TH__MESSAGE.tsv", joined)
        self.assertIn("# regenerate: python3 "
                      "tools/pf_regen_lua_message_catalog.py", joined)
        digest = [line for line in header
                  if line.startswith("# source_sha256: ")]
        self.assertEqual(len(digest), 1)
        self.assertEqual(len(digest[0].split(": ", 1)[1]), 64)
        pulled = [line for line in header if line.startswith("# pulled: ")]
        self.assertEqual(len(pulled), 1)

    def test_the_header_row_count_is_the_body_row_count(self):
        # A header that says 907 over a body of 906 is a lie that no other
        # test in this file would notice: every id lookup would still work.
        text = self.raw.decode("ascii")
        declared = [int(line.split(": ", 1)[1]) for line in text.splitlines()
                    if line.startswith("# source_rows: ")]
        self.assertEqual(len(declared), 1)
        body = [line for line in text.splitlines()
                if line and not line.startswith("#")]
        self.assertEqual(declared[0], len(body) - 1)  # minus the column row
        self.assertEqual(declared[0], len(message.catalog()))

    def test_the_column_row_is_the_four_columns_the_loader_names(self):
        text = self.raw.decode("ascii")
        columns = [line for line in text.splitlines()
                   if line and not line.startswith("#")][0]
        self.assertEqual(tuple(columns.split("\t")), message.CATALOG_COLUMNS)


@BRIDGE_GAMEDATA.skip_unless_present()
class VendoredCatalogMatchesTheRealTableTests(unittest.TestCase):
    """The drift tie itself.

    pf-adversary (round 6775u1) mutated all 907 rows of the vendored file to
    garbage and every test then in this module still passed, because they
    checked the copy against ITSELF.  This is the tie to the source, and as
    of round 7kxfe9 it compares ALL FOUR columns, text included -- the
    column the previous round did not vendor at all.
    """

    def test_every_column_of_every_row_matches_the_shipped_table(self):
        import csv

        real = {}
        with SOURCE_TABLE.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                real[int(row["n_ID"])] = (
                    int(row["n_TYPE"]), int(row["n_NOTIFY_TYPE"]),
                    row["s_MESSAGE"])
        self.assertEqual(dict(message.catalog()), real)

    def test_the_regenerate_script_reports_no_drift(self):
        # The script is the thing a human runs; a test that only compared
        # dictionaries would leave the script itself unexercised, and a
        # regenerate script that has quietly stopped working is the same
        # failure as no script at all.
        import subprocess

        tool = ROOT / "tools" / "pf_regen_lua_message_catalog.py"
        done = subprocess.run(
            [sys.executable, str(tool), "--check"],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class CatalogIsLazyAndFailsLoudTests(unittest.TestCase):
    """pf-adversary D5, round 6775u1.

    The catalog used to be read at IMPORT time under `encoding="ascii"`.
    One stray byte, or the file simply missing from a wheel, turned into an
    ImportError raised from inside `lua_api/__init__` -- the module that
    installs every namespace hook -- so all 160 Lua API names vanished and
    the traceback named an import, not a data file.
    """

    def setUp(self):
        self._saved = message._CATALOG_CACHE

    def tearDown(self):
        message._CATALOG_CACHE = self._saved

    def test_a_missing_file_raises_a_named_error_that_carries_the_path(self):
        message._CATALOG_CACHE = None
        missing = ROOT / "no" / "such" / "message_catalog.tsv"
        saved_path = message._CATALOG_PATH
        try:
            message._CATALOG_PATH = missing
            with self.assertRaises(message.MessageCatalogError) as caught:
                message.catalog()
        finally:
            message._CATALOG_PATH = saved_path
        self.assertIn("message_catalog.tsv", str(caught.exception))

    def test_a_file_with_no_rows_is_an_error_not_an_empty_catalog(self):
        # An empty catalog would make is_known_message_id() False for every
        # id -- every message in the game silently refused, with no error.
        import tempfile

        message._CATALOG_CACHE = None
        saved_path = message._CATALOG_PATH
        with tempfile.TemporaryDirectory() as folder:
            empty = Path(folder) / "message_catalog.tsv"
            empty.write_text("# header only\nmessage_id\tmessage_type\t"
                             "notify_type\tmessage_text\n", encoding="ascii")
            try:
                message._CATALOG_PATH = empty
                with self.assertRaises(message.MessageCatalogError):
                    message.catalog()
            finally:
                message._CATALOG_PATH = saved_path

    def test_importing_the_module_does_not_read_the_file(self):
        # The property that makes the above possible at all: nothing is read
        # until something asks.  Measured by reloading the module and
        # checking the cache is still empty, not by reading the source.
        import importlib

        reloaded = importlib.reload(message)
        try:
            self.assertIsNone(reloaded._CATALOG_CACHE)
        finally:
            reloaded.catalog()  # leave the module usable for other tests

    def test_the_ceiling_is_the_same_before_and_after_the_first_load(self):
        message._CATALOG_CACHE = None
        first = message.max_message_id()
        second = message.max_message_id()
        self.assertEqual(first, second)
        self.assertEqual(first, 961)


class CatalogAccessorsTests(unittest.TestCase):

    def test_message_type_is_readable_not_merely_vendored(self):
        # pf-adversary D8, round 6775u1: the column was carried with no
        # reader at all.  It has one now, and a known row pins a real value.
        self.assertEqual(message.message_type(1), 35)
        self.assertIsNone(message.message_type(962))

    def test_message_text_returns_the_localized_string(self):
        text = message.message_text(1)
        self.assertIsInstance(text, str)
        self.assertTrue(text)
        # Non-ASCII by nature -- that is the whole point of the escape.
        self.assertRaises(UnicodeEncodeError, text.encode, "ascii")
        self.assertIsNone(message.message_text(962))

    def test_no_module_in_this_package_logs_the_localized_text(self):
        # House rule: everything printed to the bridge console is ASCII
        # (cp874 dies otherwise).  The text is for a UTF-16LE frame payload,
        # never for a log line -- pinned here rather than trusted, by
        # reading every source file in the package for a call to it.
        package = ROOT / "src" / "pirateforce_foundation" / "lua_api"
        callers = [path.name for path in sorted(package.rglob("*.py"))
                   if "message_text(" in path.read_text(encoding="utf-8")
                   and path.name != "message.py"]
        self.assertEqual(callers, [])


class RefusalCountersTests(unittest.TestCase):
    """pf-adversary D12, round 6775u1: a dropped message left one log line
    and nothing countable, in the exact place drops are EXPECTED (51 of the
    116 corpus call sites pass an unmined `Trigger.VarN`)."""

    def setUp(self):
        self.lines = []
        self.sink = message.InMemoryMessageSink()

    def test_a_clean_run_counts_nothing(self):
        self.sink.record(None, 7, message.AUDIENCE_INDIVIDUAL, 856)
        self.assertEqual(self.sink.refusals(), ())

    def test_an_unknown_id_from_player_show_message_is_counted(self):
        namespace = player.build_namespace(
            frozenset({"ShowMessage"}), self.lines.append,
            context=player.PlayerContext(character_id=7), sink=self.sink)
        namespace["ShowMessage"](962)
        namespace["ShowMessage"](963)
        self.assertEqual(dict(self.sink.refusals()),
                         {message.REFUSE_UNKNOWN_MESSAGE_ID: 2})

    def test_the_two_trigger_refusals_do_not_share_one_number(self):
        namespace = trigger.build_namespace(
            frozenset({"TriggerShowMessage"}), self.lines.append,
            context=trigger.TriggerContext(scene="bg0002", trigger_id=1),
            sink=self.sink)
        namespace["TriggerShowMessage"](9, 918)    # audience outside 0..3
        namespace["TriggerShowMessage"](2, 962)    # id with no row
        namespace["TriggerShowMessage"](2)         # wrong arity
        self.assertEqual(dict(self.sink.refusals()), {
            message.REFUSE_BAD_AUDIENCE: 1,
            message.REFUSE_UNKNOWN_MESSAGE_ID: 1,
            message.REFUSE_BAD_ARITY: 1,
        })

    def test_a_cap_refusal_is_counted_under_its_own_reason(self):
        small = message.InMemoryMessageSink(messages_per_character=1)
        small.record(None, 7, message.AUDIENCE_INDIVIDUAL, 856)
        small.record(None, 7, message.AUDIENCE_INDIVIDUAL, 856)
        self.assertEqual(dict(small.refusals()),
                         {message.REFUSE_BUCKET_FULL: 1})

    def test_a_scene_message_with_no_scene_is_counted_as_such(self):
        self.sink.record(None, 7, message.AUDIENCE_SCENE, 918)
        self.assertEqual(dict(self.sink.refusals()),
                         {message.REFUSE_NO_SCENE: 1})

    def test_every_reason_a_closure_can_raise_is_in_the_declared_set(self):
        for reason in (message.REFUSE_BAD_ARITY,
                       message.REFUSE_UNKNOWN_MESSAGE_ID,
                       message.REFUSE_BAD_AUDIENCE,
                       message.REFUSE_NO_SCENE,
                       message.REFUSE_BUCKET_FULL,
                       message.REFUSE_TOO_MANY_BUCKETS):
            self.assertIn(reason, message.REFUSAL_REASONS)


class SinkIsThreadSafeTests(unittest.TestCase):
    """pf-adversary D9, round 6775u1: this sink had no lock while both of
    its sibling stores in the same package do, and one world per scene is
    shared by every session in the process (AGENTS.md section 7)."""

    def test_concurrent_writers_lose_no_message_and_exceed_no_cap(self):
        import threading

        cap = 200
        writers = 8
        each = 50
        sink = message.InMemoryMessageSink(messages_per_character=cap)
        barrier = threading.Barrier(writers)

        def write():
            barrier.wait()
            for _ in range(each):
                sink.record(None, 7, message.AUDIENCE_INDIVIDUAL, 856)

        threads = [threading.Thread(target=write) for _ in range(writers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        stored = sink.messages_for(7)
        self.assertEqual(len(stored), cap)
        self.assertEqual(dict(sink.refusals()),
                         {message.REFUSE_BUCKET_FULL: writers * each - cap})

    def test_reading_while_writing_never_hands_back_a_moving_tuple(self):
        import threading

        sink = message.InMemoryMessageSink()
        stop = threading.Event()

        def write():
            while not stop.is_set():
                sink.record("bg0002", 7, message.AUDIENCE_SCENE, 918)

        writer = threading.Thread(target=write)
        writer.start()
        try:
            for _ in range(200):
                rows = sink.broadcasts_for("bg0002")
                self.assertTrue(
                    all(row == (message.AUDIENCE_SCENE, 918, 7)
                        for row in rows))
        finally:
            stop.set()
            writer.join()


class BodyDigestGuardsTheFileOnEveryMachineTests(unittest.TestCase):
    """pf-adversary D1/D3/D4/D5, round `7kxfe9`.

    The tie to the source table needs the source table, and the Windows
    gate -- the machine that decides whether a PR merges -- has no bridge
    checkout (`.github/workflows/gate-windows.yml` does not fetch one).
    Measured there by the adversary: replacing all 907 text cells with one
    repeated string left the suite green.  So did a hand-stripped trailing
    space on the eight rows that end in one, and a TAB pasted into a cell.

    A digest of the file's OWN body needs nothing but the file, so these
    run everywhere.  They do not prove the copy matches the source; they
    prove nobody edited the copy after it was generated.
    """

    def setUp(self):
        self.path = (ROOT / "src" / "pirateforce_foundation" / "lua_api"
                     / "message_catalog.tsv")
        self.text = self.path.read_text(encoding="ascii")

    def test_the_header_carries_a_digest_of_the_body_below_it(self):
        declared = [line[len(message.BODY_DIGEST_PREFIX):]
                    for line in self.text.splitlines()
                    if line.startswith(message.BODY_DIGEST_PREFIX)]
        self.assertEqual(len(declared), 1)
        self.assertEqual(declared[0], message.body_digest(self.text))

    def test_changing_one_character_of_one_row_breaks_the_digest(self):
        # The mutation the adversary actually ran, in miniature: if this
        # assertion could not fail, the test above would be decoration.
        mutated = self.text.replace("\\u0e40", "\\u0e41", 1)
        self.assertNotEqual(mutated, self.text)
        self.assertNotEqual(message.body_digest(mutated),
                            message.body_digest(self.text))

    def test_stripping_a_trailing_space_breaks_the_digest(self):
        # Eight rows end in a real space (id 150, 243, 391, 392, 619, 667,
        # 706, 799); `git apply --whitespace=fix`, an editor, or a
        # pre-commit hook silently removes those.
        stripped = "\n".join(line.rstrip() for line in self.text.splitlines())
        self.assertNotEqual(stripped + "\n", self.text)
        self.assertNotEqual(message.body_digest(stripped),
                            message.body_digest(self.text))

    def test_the_digest_ignores_the_header_so_a_restamp_is_not_drift(self):
        # Re-pulling on a later date rewrites `# pulled:` and must not read
        # as a body edit -- otherwise the check cries wolf and gets removed.
        restamped = self.text.replace("# pulled: ", "# pulled: 1999-01-01 #")
        self.assertNotEqual(restamped, self.text)
        self.assertEqual(message.body_digest(restamped),
                         message.body_digest(self.text))


class LoaderRefusesAMalformedRowTests(unittest.TestCase):
    """pf-adversary D3: a TAB inside a text cell splits one row into five
    fields, `csv.DictReader` files the surplus under restkey, and the
    message comes back TRUNCATED with the row count -- and therefore the
    header row-count check -- still agreeing."""

    def setUp(self):
        self._saved = message._CATALOG_CACHE
        self._saved_path = message._CATALOG_PATH

    def tearDown(self):
        message._CATALOG_CACHE = self._saved
        message._CATALOG_PATH = self._saved_path

    def _load(self, body):
        import tempfile

        message._CATALOG_CACHE = None
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "message_catalog.tsv"
            path.write_text("# header\n" + "\t".join(message.CATALOG_COLUMNS)
                            + "\n" + body, encoding="ascii")
            message._CATALOG_PATH = path
            return message.catalog()

    def test_a_five_field_row_is_an_error_not_a_truncated_message(self):
        with self.assertRaises(message.MessageCatalogError) as caught:
            self._load("1\t35\t0\thel\tlo\n")
        self.assertIn("fields", str(caught.exception))

    def test_a_three_field_row_is_an_error_too(self):
        with self.assertRaises(message.MessageCatalogError):
            self._load("1\t35\t0\n")

    def test_a_well_formed_row_still_loads(self):
        self.assertEqual(self._load("1\t35\t0\thello\n"), {1: (35, 0, "hello")})


class EncoderRefusesWhatItCannotRepresentTests(unittest.TestCase):
    """pf-adversary D2: `"\\u%04x" % 0x1F3C6` renders `\\u1f3c6`, which the
    four-hex-digit decoder reads as U+1F3C followed by a literal `6`.  It
    survived the round-trip test (which re-encodes what it just decoded)
    and `--check` (both sides share the encoder), so the corruption was
    invisible on every machine without the source table."""

    def test_a_non_bmp_character_raises_instead_of_corrupting(self):
        with self.assertRaises(ValueError) as caught:
            message.escape_message_text("\U0001F3C6 champion")
        self.assertIn("non-BMP", str(caught.exception))

    def test_the_highest_bmp_character_is_still_accepted(self):
        text = "￿"
        self.assertEqual(
            message.unescape_message_text(message.escape_message_text(text)),
            text)

    def test_the_shipped_table_is_all_bmp_today(self):
        # The fact that makes the guard a tripwire rather than a blocker.
        for message_id, (_t, _n, text) in message.catalog().items():
            with self.subTest(message_id=message_id):
                self.assertFalse([ch for ch in text if ord(ch) > 0xFFFF])


class InjectedSinkIsCheckedAtInjectionTests(unittest.TestCase):
    """pf-adversary D6: a sink written against last round's protocol passed
    every check there was until a script refused a message, at which point
    an AttributeError came out of the middle of a Lua call.  51 of the 116
    corpus call sites take that path."""

    class SinkFromLastRound:
        def record(self, scene, character_id, audience, message_id):
            return 1

        def messages_for(self, character_id):
            return ()

        def broadcasts_for(self, scene):
            return ()

    def test_an_incomplete_sink_is_refused_by_name_when_it_is_injected(self):
        for build in (player.build_namespace, trigger.build_namespace):
            with self.subTest(build=build.__module__):
                with self.assertRaises(TypeError) as caught:
                    build(frozenset({"ShowMessage", "TriggerShowMessage"}),
                          lambda _line: None, sink=self.SinkFromLastRound())
                self.assertIn("record_refusal", str(caught.exception))

    def test_the_complete_sink_this_package_ships_passes(self):
        self.assertIs(message.check_sink(message.InMemoryMessageSink()).__class__,
                      message.InMemoryMessageSink)


class RegenerateScriptSeparatesDriftFromInconclusiveTests(unittest.TestCase):
    """pf-adversary D8: `--check` exited 1 both when the copy had drifted
    and when there was no bridge checkout to compare against -- so anyone
    wiring it into CI gets a false RED on every gate run, the gate having
    no bridge.  The house convention for exactly this is
    pf_gate_preflight.py's own three states."""

    def _tool(self):
        import importlib

        sys.path.insert(0, str(ROOT / "tools"))
        try:
            return importlib.import_module("pf_regen_lua_message_catalog")
        finally:
            sys.path.remove(str(ROOT / "tools"))

    def test_a_missing_source_table_is_inconclusive_not_drift(self):
        tool = self._tool()
        saved = tool.SOURCE
        try:
            tool.SOURCE = ROOT / "no" / "such" / "table.tsv"
            self.assertEqual(tool.main(["--check"]), 2)
        finally:
            tool.SOURCE = saved
