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
