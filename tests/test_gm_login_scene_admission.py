"""ADMISSION: a login-scene config may only name a scene the login accepts.

Round qq0i9u.  Two config files in this lane point an account at a scene on
login -- the GM-gated one a chat `/warp` writes, and the standalone one an
operator hand-edits -- and until this round only the WRITER asked whether
the login path would accept the destination.  An entry that arrived through
a text editor was checked against the client's 330-row scene NAME table and
nothing else, so `{"plain_tester": 17}` (a named scene pinned
`login_entry_allowed: false`) loaded, applied, and was then refused by
`resolve_entry` with no reply -- on that login and, because the standalone
map is deliberately never consumed (`COO-DECISION 20260829_0542`), on every
retry after it.  The account was out of the game until somebody with shell
access deleted a file that is in `.gitignore`.

Measured through the real dispatcher in round 38c4tv; asked in pf_bridge's
`notes_to_chief/20260829_0906_LANE-GM-ASK-COO-standalone-map-admits-a-scene-
no-login-can-enter.md`, which named option (a) -- refuse at admission -- as
the one the lane would walk if no answer arrived by the next round.  None
did.  [สมมติของสาย GM - รอ COO ยืนยัน]

This file owns the predicate.  The two dispatcher-level consequences live
where the logins do: `test_gm_login_scene_override_standalone_at_login.py`
and `test_gm_login_scene_override_position_resync.py`.

WHAT IS NOT CLAIMED: nothing here says a tester CAN reach any scene.  It
says the server will not accept an instruction to send them somewhere the
login path would then refuse.  Reaching a scene is `GT-141`'s to decide, on
a screen.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    login_scene_admission,
    login_scene_override,
    login_scene_stage,
)
from pirateforce_foundation.model import Position  # noqa: E402

# Pinned as literals, not read from the registry: the point of this file is
# to fail when the registry moves, not to agree with whatever it says today.
ADMISSIBLE_TODAY = (1, 2, 278, 997)
HOME = 1
# In the client's name catalog (so it passes the older check) and pinned
# `login_entry_allowed: false` -- the exact entry that locked an account out.
BARRED_AT_LOGIN = 17
# Named in the client's catalog, absent from lane A's registry entirely.
NAMED_BUT_UNPINNED = 3


class ThePredicateTests(unittest.TestCase):
    def test_the_admissible_set_is_what_the_registry_pins_today(self):
        self.assertEqual(
            ADMISSIBLE_TODAY, login_scene_admission.stageable_scene_ids()
        )

    def test_every_admissible_scene_says_so_one_at_a_time(self):
        for scene_id in ADMISSIBLE_TODAY:
            with self.subTest(scene_id=scene_id):
                self.assertTrue(
                    login_scene_admission.login_entry_is_pinned(scene_id)
                )

    def test_a_scene_barred_at_login_is_refused(self):
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(BARRED_AT_LOGIN)
        )

    def test_a_named_but_unpinned_scene_is_refused(self):
        self.assertFalse(
            login_scene_admission.login_entry_is_pinned(NAMED_BUT_UNPINNED)
        )

    def test_a_scene_nobody_has_ever_heard_of_is_refused(self):
        self.assertFalse(login_scene_admission.login_entry_is_pinned(31337))

    def test_a_registry_this_process_cannot_read_admits_nothing(self):
        """Fail-closed: not being able to check is not licence to admit."""
        with mock.patch.object(
            login_scene_admission.world_scene_travel,
            "load_scene_registry",
            side_effect=OSError("registry gone"),
        ):
            self.assertFalse(
                login_scene_admission.login_entry_is_pinned(HOME)
            )
            self.assertEqual((), login_scene_admission.stageable_scene_ids())

    def test_a_bool_is_not_a_scene_id(self):
        # `True == 1` and 1 is admissible, so an isinstance check here would
        # admit `{"tester": true}` as Port Royal.
        with self.assertRaises(TypeError):
            login_scene_admission.login_entry_is_pinned(True)


class OneImplementationNotTwoTests(unittest.TestCase):
    """The writer and the reader must ask the SAME question.

    They did not, and that gap is the whole defect: `stage_login_scene` has
    asked lane A's registry since round 0z3kjx while the loader asked only
    the name table.  A copy of the predicate in each place would agree today
    and drift the first time one of them is fixed.
    """

    def test_the_staging_path_uses_the_admission_module_itself(self):
        self.assertIs(
            login_scene_stage.login_entry_is_pinned,
            login_scene_admission.login_entry_is_pinned,
        )
        self.assertIs(
            login_scene_stage.stageable_scene_ids,
            login_scene_admission.stageable_scene_ids,
        )

    def test_the_reader_uses_the_admission_module_itself(self):
        self.assertIs(
            login_scene_override.login_entry_is_pinned,
            login_scene_admission.login_entry_is_pinned,
        )


class TheRealLoginPathAgreesTests(unittest.TestCase):
    """The cross-check that makes this predicate more than a second opinion.

    `resolve_entry` is what the login actually calls, and it has THREE
    refusal reasons, not the one the staging path modelled: not pinned, not
    allowed at login, and pinned-with-no-spawn.  Admission that models a
    subset admits an entry the login then refuses -- which is the defect
    this module exists to close, reappearing one refusal reason later.

    So rather than trusting the model, this walks lane A's registry scene by
    scene and asks `resolve_entry` itself, in the shape `runtime.py`'s login
    calls it (no `via_login` keyword).  A fourth refusal reason added
    upstream, or a spawn removed from a pinned scene, turns this red instead
    of turning a tester's account into a locked door.
    """

    @staticmethod
    def _login_call(scene_id):
        return world_scene_entry.resolve_entry(
            Position(scene_id, 0, 1.0, 2.0, 3.0, 0.5),
            emit=lambda line: None,
        )

    def test_every_admitted_scene_is_accepted_by_resolve_entry(self):
        for scene_id in login_scene_admission.stageable_scene_ids():
            with self.subTest(scene_id=scene_id):
                self._login_call(scene_id)  # must not raise

    def test_every_registry_scene_admission_refuses_resolve_entry_refuses_too(
        self,
    ):
        """The other direction: admission must not be refusing for nothing.

        Without this, `return False` would pass every test above and quietly
        take the lane's only convenience away.
        """
        registry = world_scene_travel.load_scene_registry()
        admitted = set(login_scene_admission.stageable_scene_ids())
        refused_by_admission = [
            target.n_id
            for target in registry.destinations
            if target.n_id not in admitted
        ]
        self.assertTrue(
            refused_by_admission, "a registry with nothing to refuse proves "
            "nothing here -- pin the case back when lane A adds one"
        )
        for scene_id in refused_by_admission:
            with self.subTest(scene_id=scene_id):
                with self.assertRaises(world_scene_entry.SceneEntryRefused):
                    self._login_call(scene_id)


class TheSpawnConditionTests(unittest.TestCase):
    """The half of the predicate no live registry row can exercise.

    MEASURED, and the reason this class exists: with every other test in
    this file written, deleting the spawn condition from
    `_target_is_admissible` left the whole lane suite green -- **658 passed,
    0 failed**.  Every scene in the registry has a spawn today, so the
    cross-check above cannot reach the condition, and a guard no test can
    turn red is a guard that will be deleted by the next person who tidies
    up.  `resolve_entry` refuses a pinned, login-allowed, SPAWNLESS scene
    with `REFUSED_NO_PINNED_SPAWN`; admission has to refuse it too or the
    lockout comes back one refusal reason along.

    So the registry is bent for the length of these tests, through lane A's
    own loader, and both sides are asked about the same bent row.  This is
    the only thing in this file that is not a fact about today's data -- it
    is a fact about what happens the day lane A pins a scene it has not
    measured a spawn for yet.
    """

    SPAWNLESS = 278  # not home; home is exempt and gets its own test below

    @contextlib.contextmanager
    def _registry_without_a_spawn_on(self, scene_id):
        real = world_scene_travel.load_scene_registry()
        bent = dataclasses.replace(
            real,
            destinations=tuple(
                dataclasses.replace(target, spawn=None)
                if target.n_id == scene_id else target
                for target in real.destinations
            ),
        )
        self.assertIsNone(bent[scene_id].spawn, "the fixture bent nothing")
        self.assertTrue(
            bent[scene_id].login_entry_allowed,
            "this row must still be login-allowed, or it would be refused "
            "for the OTHER reason and prove nothing",
        )
        with mock.patch.object(
            world_scene_travel, "load_scene_registry", return_value=bent
        ):
            yield bent

    def test_the_login_path_really_does_refuse_a_spawnless_destination(self):
        """The premise, checked rather than assumed."""
        with self._registry_without_a_spawn_on(self.SPAWNLESS):
            with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
                world_scene_entry.resolve_entry(
                    Position(self.SPAWNLESS, 0, 1.0, 2.0, 3.0, 0.5),
                    emit=lambda line: None,
                )
        self.assertEqual(
            caught.exception.reason, world_scene_entry.REFUSED_NO_PINNED_SPAWN
        )

    def test_admission_refuses_it_too(self):
        with self._registry_without_a_spawn_on(self.SPAWNLESS):
            self.assertFalse(
                login_scene_admission.login_entry_is_pinned(self.SPAWNLESS)
            )
            self.assertNotIn(
                self.SPAWNLESS, login_scene_admission.stageable_scene_ids()
            )

    def test_a_config_naming_it_is_refused_when_the_map_is_read(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "gm_login_scene.json"
        path.write_text(
            json.dumps({"gm_login_scene": {"gm_runner": self.SPAWNLESS}}),
            encoding="utf-8",
        )
        with self._registry_without_a_spawn_on(self.SPAWNLESS):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(ValueError):
                    login_scene_override.load_login_scene_overrides(path)

    def test_home_stays_admissible_without_a_spawn_because_home_uses_the_row(
        self,
    ):
        """The carve-out, pinned so it is not quietly widened or dropped.

        `resolve_entry` never reads home's spawn -- a character arriving home
        keeps its own persisted position -- so refusing home for a missing
        spawn would break every ordinary login to make a scene nobody
        overrides safer.  Both sides must agree on THAT too.
        """
        with self._registry_without_a_spawn_on(HOME):
            self.assertTrue(login_scene_admission.login_entry_is_pinned(HOME))
            world_scene_entry.resolve_entry(
                Position(HOME, 0, 1.0, 2.0, 3.0, 0.5), emit=lambda line: None,
            )  # must not raise


class TheAdmissibleSetIsAlsoNamedTests(unittest.TestCase):
    """A pinned destination with no NAME may not be offered to anybody.

    This filter existed in the first version of the module and pinned
    nothing: mutation M10 deleted it and the whole lane suite stayed green,
    658 passed.  It then reached a pushed commit of this branch, because a
    review's mutation and the round's `git add` collided and no test could
    tell the difference.  The scar is the reason this class exists at all:
    the tuple it filters is PRINTED to a human -- in the console line and by
    `GT-141` -- and an id with no name in the client's own catalog is an
    instruction the tester cannot check.
    """

    UNNAMED = 60000

    def test_the_catalog_does_not_know_the_id_this_test_uses(self):
        # Or the test below proves nothing.
        from pirateforce_foundation.gm.scene_catalog import is_known_scene_id
        self.assertFalse(is_known_scene_id(self.UNNAMED))

    def test_a_pinned_but_unnamed_destination_is_not_offered(self):
        real = world_scene_travel.load_scene_registry()
        bent = dataclasses.replace(
            real,
            destinations=tuple(
                dataclasses.replace(target, n_id=self.UNNAMED)
                if target.n_id == 997 else target
                for target in real.destinations
            ),
        )
        with mock.patch.object(
            world_scene_travel, "load_scene_registry", return_value=bent
        ):
            offered = login_scene_admission.stageable_scene_ids()
        self.assertNotIn(self.UNNAMED, offered)
        self.assertEqual((1, 2, 278), offered)


class TheConsoleLineNeverAltersDispatchTests(unittest.TestCase):
    """`session.py`'s house rule, applied to this round's diagnostic.

    MEASURED by pf-adversary: the bridge console is `cp874`, an operator
    account name carrying a character it cannot encode raised
    `UnicodeEncodeError` out of the print, and `runtime_console._Mirror`
    writes to the console BEFORE the retained file -- so the refusal was
    recorded nowhere, and the exception the caller saw came from the
    encoder rather than from this module.  A diagnostic that changes what
    the caller sees is worse than no diagnostic.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "standalone.json"

    def _write(self, account):
        self.path.write_text(
            json.dumps(
                {login_scene_override.STANDALONE_JSON_KEY: {account: 17}}
            ),
            encoding="utf-8",
        )

    def _load(self):
        return login_scene_override.load_standalone_login_scene_overrides(
            self.path
        )

    def test_a_name_the_console_cannot_encode_still_gets_the_real_refusal(self):
        for account in ("张三", "café", "naïve…",
                        "ทดสอบ"):
            with self.subTest(account=account):
                self._write(account)
                buffer = io.TextIOWrapper(
                    io.BytesIO(), encoding="cp874", errors="strict"
                )
                with mock.patch.object(sys, "stderr", buffer):
                    with self.assertRaises(ValueError) as caught:
                        self._load()
                # The refusal, not the encoder's complaint.
                self.assertNotIsInstance(
                    caught.exception, UnicodeEncodeError,
                    "the diagnostic replaced the refusal it was explaining",
                )
                self.assertIn("names a", str(caught.exception))

    def test_the_token_still_reaches_a_cp874_console_for_such_a_name(self):
        self._write("张三")
        raw = io.BytesIO()
        buffer = io.TextIOWrapper(raw, encoding="cp874", errors="strict")
        with mock.patch.object(sys, "stderr", buffer):
            with self.assertRaises(ValueError):
                self._load()
            buffer.flush()
        console = raw.getvalue().decode("cp874")
        self.assertIn(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN, console
        )
        self.assertIn("scene_id=17", console)

    def test_a_closed_stderr_costs_the_line_and_nothing_else(self):
        self._write("plain_tester")
        closed = io.StringIO()
        closed.close()
        with mock.patch.object(sys, "stderr", closed):
            with self.assertRaises(ValueError) as caught:
                self._load()
        self.assertIn("names a", str(caught.exception))


class TheLoaderTests(unittest.TestCase):
    """Both config files, held to the rule, at the moment they are read."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.gm_path = Path(self.tmp.name) / "gm_login_scene.json"
        self.standalone_path = Path(self.tmp.name) / "standalone.json"

    def _write(self, path, key, mapping):
        path.write_text(json.dumps({key: mapping}), encoding="utf-8")

    def _load_gm(self):
        return login_scene_override.load_login_scene_overrides(self.gm_path)

    def _load_standalone(self):
        return login_scene_override.load_standalone_login_scene_overrides(
            self.standalone_path
        )

    def test_the_gm_gated_map_refuses_a_barred_scene(self):
        self._write(self.gm_path, "gm_login_scene", {"gm_runner": BARRED_AT_LOGIN})
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(ValueError) as caught:
                self._load_gm()
        message = str(caught.exception)
        self.assertIn("gm_runner", message)
        self.assertIn(str(BARRED_AT_LOGIN), message)
        # The way out is in the error, not in a doc somebody has to find.
        self.assertIn(str(ADMISSIBLE_TODAY), message)

    def test_the_standalone_map_refuses_a_barred_scene(self):
        self._write(
            self.standalone_path,
            login_scene_override.STANDALONE_JSON_KEY,
            {"plain_tester": BARRED_AT_LOGIN},
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(ValueError):
                self._load_standalone()

    def test_the_console_token_names_the_file_the_account_and_the_way_out(self):
        self._write(
            self.standalone_path,
            login_scene_override.STANDALONE_JSON_KEY,
            {"plain_tester": BARRED_AT_LOGIN},
        )
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(ValueError):
                self._load_standalone()
        console = stderr.getvalue()
        self.assertIn(
            login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN, console
        )
        self.assertIn("plain_tester", console)
        self.assertIn(f"scene_id={BARRED_AT_LOGIN}", console)
        self.assertIn(str(self.standalone_path), console)
        self.assertIn(f"stageable={ADMISSIBLE_TODAY}", console)

    def test_an_admissible_entry_still_loads_and_prints_nothing(self):
        self._write(self.gm_path, "gm_login_scene", {"gm_runner": 2})
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual({"gm_runner": 2}, self._load_gm())
        self.assertEqual("", stderr.getvalue())

    def test_one_bad_entry_refuses_the_whole_map_rather_than_part_of_it(self):
        """Fail-closed on the FILE, deliberately, and said out loud.

        A loader that dropped the bad line and returned the rest would send
        the other listed accounts to their scenes while silently ignoring
        one operator instruction -- the same silence this round is closing,
        one row down.  The caller
        (`consume_login_scene_override`) turns the raise into
        `CONSUME_FAILED`, so the cost is: every override in that file stops
        working until the typo is fixed, and every account logs in at home.
        Nobody is locked out.
        """
        self._write(
            self.gm_path,
            "gm_login_scene",
            {"good_runner": 2, "bad_runner": BARRED_AT_LOGIN},
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(ValueError):
                self._load_gm()

    def test_an_absent_file_is_still_simply_empty(self):
        self.assertEqual({}, self._load_gm())
        self.assertEqual({}, self._load_standalone())


if __name__ == "__main__":
    unittest.main()
