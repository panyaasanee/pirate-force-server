"""The refusal notice is WIRED, and this file goes red on the day it is not.

CORE-REQUEST ``pf_bridge/notes_to_chief/20260903_1505_LANE-A-CORE-REQUEST-
CHIEF-wire-the-refusal-notice-at-runtime-8028.md`` asked for one line in
``runtime.py``, and asked it as a tracked letter for one reason: LANE-A's
own 38 tests certify a string that no runtime path produced, so nothing a
checkout could read went red while the console kept printing yesterday's
line.  This file is the missing red.

Everything here is DERIVED from the source it guards.  Nothing retypes a
handler's contents, a token, or a line number: a guard that keeps its own
copy of the thing it guards goes stale in the very commit that makes it
stale (house rule, ``AGENTS.md`` section 7).
"""

import ast
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import world_scene_refusal_notice  # noqa: E402


RUNTIME_PATH = (
    pathlib.Path(world_scene_refusal_notice.__file__).resolve().parent
    / "runtime.py"
)

# The probe handler refuses the GM OVERRIDE, not the login, and the letter
# forbids touching it.  It is told apart from the login handler by a string
# IT contains, read out of the tree -- not by a line number, which every
# commit above it moves.
PROBE_MARKER = "GM_LOGIN_SCENE_OVERRIDE_REFUSED"


def _runtime_tree():
    return ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))


def _is_scene_entry_refused(node):
    """``except world_scene_entry.SceneEntryRefused`` in any spelling."""
    if node.type is None:
        return False
    types = (
        node.type.elts
        if isinstance(node.type, ast.Tuple)
        else [node.type]
    )
    for item in types:
        if (
            isinstance(item, ast.Attribute)
            and item.attr == "SceneEntryRefused"
        ):
            return True
        if isinstance(item, ast.Name) and item.id == "SceneEntryRefused":
            return True
    return False


def _handlers():
    return [
        node
        for node in ast.walk(_runtime_tree())
        if isinstance(node, ast.ExceptHandler) and _is_scene_entry_refused(node)
    ]


def _strings_in(node):
    return {
        sub.value
        for sub in ast.walk(node)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
    }


def _calls_to(node, module_name, func_name):
    found = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == func_name
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == module_name
        ):
            found.append(sub)
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == func_name
            and isinstance(func.value, ast.Name)
            and func.value.id == module_name
        ):
            found.append(sub)
    return found


def _split_handlers():
    """(probe handler, login handler) -- derived, never assumed by order."""
    handlers = _handlers()
    probes = [h for h in handlers if PROBE_MARKER in " ".join(_strings_in(h))]
    logins = [h for h in handlers if h not in probes]
    return handlers, probes, logins


class SceneEntryRefusedHandlerShapeTests(unittest.TestCase):
    """How many handlers there are, and which is which, is derived."""

    def test_exactly_two_handlers_and_each_is_classified(self):
        handlers, probes, logins = _split_handlers()
        self.assertEqual(
            len(handlers),
            2,
            "runtime.py's SceneEntryRefused handler count changed.  A new "
            "one is not automatically wrong -- but it must be classified "
            "here (probe or login) before this file can keep its promise.",
        )
        self.assertEqual(len(probes), 1, "no single GM-override probe handler")
        self.assertEqual(len(logins), 1, "no single login-refusal handler")

    def test_the_module_is_imported_at_module_level(self):
        tree = _runtime_tree()
        imported = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        self.assertIn(
            world_scene_refusal_notice.__name__.rsplit(".", 1)[-1],
            imported,
            "runtime.py stopped importing the notice module",
        )


class TheLoginRefusalNamesTheLoginTests(unittest.TestCase):
    """The one line the CORE-REQUEST asked for, proven from the tree."""

    def setUp(self):
        _handlers_all, probes, logins = _split_handlers()
        self.probe = probes[0]
        self.login = logins[0]

    def test_the_login_handler_prints_the_composed_notice(self):
        module = world_scene_refusal_notice.__name__.rsplit(".", 1)[-1]
        calls = _calls_to(self.login, module, "refusal_console_line")
        self.assertEqual(
            len(calls),
            1,
            "the login-refusal handler no longer composes the notice "
            "exactly once; the console is back to a line that does not "
            "name the character (CORE-REQUEST 20260903_1505)",
        )
        prints = [
            node
            for node in ast.walk(self.login)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        self.assertTrue(
            any(
                calls[0] in list(ast.walk(printed))
                for printed in prints
            ),
            "the notice is composed but never printed",
        )

    def test_the_notice_is_given_the_character_and_the_row_IN_THAT_ORDER(
        self,
    ):
        """ORDER, not presence.  pf-adversary D1/D5, measured this round.

        The first shape of this test asked ``len(args) >= 3`` and then
        ``"selected" in ast.dump(call)``.  Swapping argument two and three
        -- character and row, nothing else -- printed a line whose every
        subject field read ``none``, which is the whole deliverable of
        ``CORE-REQUEST 20260903_1505`` destroyed, and 8749 tests stayed
        green including this one.  Renaming the attributes to
        ``selected_x`` / ``login_row_x`` did the same, because a substring
        of a longer name is still a substring.  Both are red now, and the
        value-layer test in this file catches them a second time.
        """
        module = world_scene_refusal_notice.__name__.rsplit(".", 1)[-1]
        call = _calls_to(self.login, module, "refusal_console_line")[0]
        self.assertEqual(
            len(call.args),
            3,
            "the notice is not called with exactly (error, character, row)",
        )
        error, character, row = call.args
        self.assertIsInstance(error, ast.Name)
        self.assertEqual(
            error.id,
            self.login.name,
            "argument one is not the exception this handler caught",
        )
        self.assertIsInstance(
            character,
            ast.Attribute,
            "argument two is not the selected character",
        )
        self.assertEqual(character.attr, "selected")
        self.assertIsInstance(character.value, ast.Attribute)
        self.assertEqual(character.value.attr, "foundation")
        self.assertIsInstance(row, ast.Name)
        self.assertEqual(
            row.id,
            "login_row",
            "argument three is not the row the login was refused on",
        )

    def test_reply_frames_is_the_return_in_the_same_handler(self):
        module = world_scene_refusal_notice.__name__.rsplit(".", 1)[-1]
        call = _calls_to(self.login, module, "refusal_console_line")[0]
        keywords = {kw.arg: kw.value for kw in call.keywords}
        self.assertIn("reply_frames", keywords, "reply_frames not passed")
        value = keywords["reply_frames"]
        self.assertIsInstance(value, ast.Constant)
        returns = [
            node
            for node in ast.walk(self.login)
            if isinstance(node, ast.Return)
        ]
        self.assertTrue(returns, "the handler no longer returns at all")
        for node in returns:
            self.assertIsInstance(
                node.value,
                ast.List,
                "this handler returns something other than a list of "
                "frames; reply_frames can no longer be derived from it, "
                "and the console line would keep claiming a count it did "
                "not measure",
            )
            self.assertEqual(
                value.value,
                len(node.value.elts),
                "reply_frames disagrees with what this handler actually "
                "returns to the player; the day the refusal answers, the "
                "number moves with it or this test goes red",
            )

    def test_the_handler_still_refuses_the_login_the_same_way(self):
        strings = " ".join(_strings_in(self.login))
        self.assertIn(
            "world_scene_entry_refused_no_reply",
            strings,
            "the event the gate's own tests read was dropped; the letter "
            "forbids changing the gate by one byte",
        )

    def test_the_handler_prints_once_and_not_into_a_sink(self):
        """pf-adversary D3: the composed line went to ``file=_sink``.

        A mutant printed the notice into a sink and printed yesterday's
        f-string -- built from ``CONSOLE_TOKEN`` so no literal appeared --
        to the console.  49 tests stayed green and the console was
        byte-identical to before the round.  One print, no ``file=``.
        """
        prints = [
            node
            for node in ast.walk(self.login)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        self.assertEqual(
            len(prints),
            1,
            "the login-refusal handler prints more than once; two "
            "producers of one console line is the shape COO 20260903_0054 "
            "item 2 outlawed",
        )
        self.assertEqual(
            [kw.arg for kw in prints[0].keywords],
            [],
            "the console line is being redirected somewhere the operator "
            "is not looking",
        )


class NobodyElseProducesThisLineTests(unittest.TestCase):
    """One producer, proven across the PACKAGE, not one file.

    pf-adversary D11: both single-producer checks read ``runtime.py`` and
    only ``runtime.py``, and this file's own report leaned on "the literal
    left runtime.py (0 hits)" -- a one-file scan used to prove an absence,
    which is the thing ``AGENTS.md`` section 7 forbids.  This walks every
    module in the package instead.
    """

    def test_no_module_prints_the_token_except_through_the_composer(self):
        token = world_scene_refusal_notice.CONSOLE_TOKEN
        package = RUNTIME_PATH.parent
        offenders = []
        module_name = world_scene_refusal_notice.__name__.rsplit(".", 1)[-1]
        for path in sorted(package.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            own_token = None
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "CONSOLE_TOKEN"
                        and isinstance(node.value, ast.Constant)
                    ):
                        own_token = node.value.value
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    continue
                for sub in ast.walk(node):
                    literal = (
                        isinstance(sub, ast.Constant)
                        and isinstance(sub.value, str)
                        and token in sub.value
                    )
                    # `CONSOLE_TOKEN` is a name several lanes use for their
                    # OWN token (gm/chat_command_action.py, gm/
                    # warp_chain_preflight.py).  Resolve it before calling
                    # it a second producer, or this guard cries wolf on
                    # five prints that have nothing to do with refusals.
                    qualified = (
                        isinstance(sub, ast.Attribute)
                        and sub.attr == "CONSOLE_TOKEN"
                        and isinstance(sub.value, ast.Name)
                        and sub.value.id == module_name
                    )
                    bare = (
                        isinstance(sub, ast.Name)
                        and sub.id == "CONSOLE_TOKEN"
                        and own_token == token
                    )
                    if literal or qualified or bare:
                        offenders.append(f"{path.name}:{node.lineno}")
                        break
        self.assertEqual(
            offenders,
            [],
            "something other than refusal_console_line prints the refusal "
            f"token: {offenders}.  One line, one producer.",
        )


class TheProbeHandlerIsUntouchedTests(unittest.TestCase):
    """The letter's one red line: do not wire the FIRST handler."""

    def setUp(self):
        _handlers_all, probes, _logins = _split_handlers()
        self.probe = probes[0]

    def test_the_probe_does_not_compose_the_login_notice(self):
        module = world_scene_refusal_notice.__name__.rsplit(".", 1)[-1]
        self.assertEqual(
            _calls_to(self.probe, module, "refusal_console_line"),
            [],
            "the GM-override probe was wired too.  Its token is "
            f"{PROBE_MARKER}, other files grep it, and the login was never "
            "refused there.",
        )

    def test_the_probe_keeps_its_own_token(self):
        self.assertIn(
            PROBE_MARKER,
            " ".join(_strings_in(self.probe)),
            "the probe's token changed; readers that grep it go silent",
        )


class TheTokenTheGrepsReadTests(unittest.TestCase):
    """The composed line still leads with the token other files grep."""

    def test_the_token_is_the_one_the_census_test_pins(self):
        tests_dir = pathlib.Path(__file__).resolve().parent
        census = tests_dir / "test_lane_a_scene_census.py"
        if not census.exists():  # the pinning file was renamed, not deleted
            census = next(
                (
                    path
                    for path in tests_dir.glob("test_*.py")
                    if path != pathlib.Path(__file__).resolve()
                    and world_scene_refusal_notice.CONSOLE_TOKEN
                    in path.read_text(encoding="utf-8")
                ),
                None,
            )
        self.assertIsNotNone(
            census,
            "no test in this tree pins the refusal token any more",
        )
        self.assertIn(
            world_scene_refusal_notice.CONSOLE_TOKEN,
            census.read_text(encoding="utf-8"),
        )

    def test_the_composed_line_leads_with_that_token(self):
        class _Refusal(LookupError):
            reason = "scene_not_pinned"

        line = world_scene_refusal_notice.refusal_console_line(
            _Refusal("[scene_not_pinned] nothing pinned"),
            None,
            None,
            reply_frames=0,
        )
        self.assertTrue(
            line.startswith(world_scene_refusal_notice.CONSOLE_TOKEN + " ["),
            f"the composed line no longer leads with the token: {line[:80]}",
        )


class TheConsoleNamesTheLoginItRefusedTests(unittest.TestCase):
    """THE VALUE LAYER, not the shape layer.  pf-adversary D12, this round.

    Everything above asks "is the call there, in the right handler, with the
    right arguments?" -- questions about the SHAPE of a statement.  The
    CORE-REQUEST asked something else: does the console name the player who
    is stuck?  Two mutants (swap arguments two and three; rename the
    attributes) keep the shape perfectly, print ``refused_character_id=none``
    for every field, and 8749 tests could not tell.

    So this drives a REAL refusal through the REAL dispatcher, captures
    stdout, and compares the printed id against the id the store actually
    handed the login.  The expected value is DERIVED from the fixture; there
    is no hand-typed id anywhere in this class.

    The refusal fixture (a registry with scene 14's login door shut) is
    imported from ``test_lane_a_scene_census``, which owns it, rather than
    copied -- a second copy would go stale in the commit that changed the
    first.
    """

    @classmethod
    def setUpClass(cls):
        import test_lane_a_scene_census as census

        cls.census = census

    def _refuse_a_login_and_capture_the_console(self):
        census = self.census
        legacy = census._legacy()
        with tempfile.TemporaryDirectory() as work:
            work = pathlib.Path(work)
            _unused, patched = census._registry_with_door_shut(work)
            real_loader = census.world_scene_travel.load_scene_registry
            census.world_scene_travel.load_scene_registry = (
                lambda *a, _f=real_loader, _p=patched, **k: _f(_p)
            )
            self.addCleanup(
                setattr,
                census.world_scene_travel,
                "load_scene_registry",
                real_loader,
            )
            store = census.SQLiteStore(
                work / "state.sqlite3", ROOT / "migrations"
            )
            store.migrate()
            lifecycle = census.CharacterLifecycle(
                store,
                census.Position(
                    1, 0,
                    legacy.V135_PLAYER_X,
                    legacy.V135_PLAYER_Y,
                    legacy.V135_PLAYER_Z,
                ),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = census.make_state_class(
                legacy, lifecycle, census.LegacyProjector(legacy)
            )
            state = state_type("driver")
            state.dispatch(
                legacy.parse_outer(
                    legacy._synthetic_client_login_pc("driver")
                )
            )
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id
            )[-1]
            spawn = census.world_scene_travel.spawn_position(
                census.world_scene_travel.destination(census.VOLCANO)
            )
            store.select_character(
                state.foundation.session_id, character.selector
            )
            store.save_position(
                state.foundation.session_id,
                character.id,
                census.Position(
                    census.VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0
                ),
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                state.dispatch(
                    legacy.parse_outer(
                        legacy._synthetic_start_game_pc(character.selector)
                    )
                )
            return character, buf.getvalue()

    @staticmethod
    def _refusal_line(console):
        token = world_scene_refusal_notice.CONSOLE_TOKEN
        lines = [line for line in console.splitlines() if token in line]
        return lines

    @staticmethod
    def _field(line, key):
        for chunk in line.split(" "):
            if chunk.startswith(key + "="):
                return chunk[len(key) + 1:]
        return None

    def test_the_printed_character_id_is_the_one_the_store_refused(self):
        character, console = self._refuse_a_login_and_capture_the_console()
        lines = self._refusal_line(console)
        self.assertEqual(
            len(lines),
            1,
            "the refused login printed no refusal line, or more than one",
        )
        line = lines[0]
        self.assertEqual(
            self._field(line, "refused_character_id"),
            str(character.id),
            "the console names a different character than the one the "
            "store refused -- or names nobody.  This is the whole "
            "deliverable of CORE-REQUEST 20260903_1505, and it is the one "
            "thing an AST guard cannot see.",
        )
        self.assertEqual(
            self._field(line, "refused_selector"),
            str(character.selector),
            "the selector on the console is not the refused login's",
        )
        self.assertNotEqual(
            self._field(line, "refused_name"),
            world_scene_refusal_notice.UNKNOWN,
            "the console could not read the character's name at all",
        )

    def test_the_line_still_leads_with_what_the_greps_read(self):
        _character, console = self._refuse_a_login_and_capture_the_console()
        line = self._refusal_line(console)[0]
        self.assertTrue(
            line.startswith(world_scene_refusal_notice.CONSOLE_TOKEN + " ["),
            "readers that grep TOKEN + bracket contiguous went silent",
        )
        self.assertTrue(line.isascii(), "a cp874 console cannot print this")

    def test_the_refusal_still_answers_the_player_with_nothing(self):
        """reply_frames is not a decoration: it is measured here too."""
        _character, console = self._refuse_a_login_and_capture_the_console()
        line = self._refusal_line(console)[0]
        self.assertEqual(
            self._field(line, "reply_frames"),
            "0",
            "the console claims a reply count the handler did not send",
        )


class TheBracketCannotBeTruncatedTests(unittest.TestCase):
    """pf-adversary D9: the leading bracket is capped at NAME_LIMIT.

    ``GAME_TEST_QUEUE.md:6667`` and ``tests/test_lane_a_scene_census.py``
    grep ``TOKEN [reason]`` as one contiguous string.  Every refusal reason
    fits under the cap today; a longer one added later would silently
    truncate the bracket and take both greps with it.  Derived from the
    vocabulary, so the day someone adds a long reason this is red BEFORE
    the greps go quiet.
    """

    def test_every_refusal_reason_fits_inside_the_cap(self):
        from pirateforce_foundation import world_scene_entry

        reasons = sorted(world_scene_entry.REFUSAL_REASONS)
        self.assertTrue(reasons, "the refusal vocabulary is empty")
        longest = max(reasons, key=len)
        self.assertLessEqual(
            len(longest),
            world_scene_refusal_notice.NAME_LIMIT,
            f"refusal reason {longest!r} is longer than the composer's cap "
            f"({world_scene_refusal_notice.NAME_LIMIT}); the leading "
            "bracket would be truncated and every contiguous "
            "TOKEN-plus-bracket grep in the queue would go quiet",
        )


if __name__ == "__main__":  # pragma: no cover - parity with the suite
    unittest.main()
