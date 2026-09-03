"""LANE-A: a click must not sweep the loot lying on the ground.

WHAT THIS FILE IS FOR.  Until round ``gx7xtp`` all four of this lane's
ChooseNPC responders composed their answer frame with
``legacy.make_runtime_remote_actors`` - v141's own composer, which does not
carry the ground list.  A player who killed a monster, watched the drop
land, and then CLICKED anything before picking it up got an answer frame
that re-declared the scene's actors without the ground rows, and the drop
went out from under them.  ``LANE-B``'s letter
``pf_bridge/notes_to_chief/20260902_1845_LANE-B-TO-LANE-A`` shipped the
composer that keeps them (``mob_combat.remote_actors_preserving_the_
ground``) and named the two lines this lane owes; ``COO-DECISION
20260902_1946`` approved the call-site half with two conditions.  This is
that half, tested in one file for all four responders because the defect
it prevents is a property of the LANE and not of any one scene.

WHAT IS PROVEN HERE AND WHAT IS NOT.

    PROVEN, WIRE LAYER.  With no cell wired - which is every boot on
    ``main`` today, because the ``runtime.py`` call site does not pass one
    yet - each responder returns the SAME BYTES it returned before this
    round, and says so on the console with the real cause rather than a
    guess.  "Same bytes" is checked against v141's own composer run on the
    same entries, not against a recorded blob.

    PROVEN, GATE.  With a cell that reports live ground rows, the composed
    frame is the preserving one; with a cell that reports none, it is
    v141's.  The gate is ``mob_loot``'s own, called through
    ``mob_combat``: this file drives it, it does not re-implement it.

    PROVEN, PER CALL SITE.  Each responder is driven END TO END through
    ``respond()`` with and without a cell, and the console token it emits
    is read back.  That is what makes a mis-wired call site red:
    pf-adversary (round ``gx7xtp``, D3) showed that swapping the last two
    arguments, or passing ``None`` where the cell goes, left the whole
    suite byte-identical when the only guard was a text scan.  ~~"the whole
    7,158-test suite"~~ - STRUCK, round ``nyxlqs``: that total was true the
    day it was written and is 7,233 in the gate subset today.  A total that
    moves every round does not belong in a sentence about a property.

    NOT PROVEN.  That any of this reaches a screen.  No attended ticket is
    scheduled to read ``GROUND_ACTORS_LIVENESS_UNKNOWN`` - LANE-B's letter
    says so plainly and this file does not pretend otherwise.  ``GT-204``
    is the chief's ticket and its scope is loot / left click / into the
    bag; the click-while-loot-is-down case is not in it.

WHO MAY AMEND THE BASELINES IN THIS FILE (``AGENTS.md`` section 7, ``COO-DECISION
20260903_0053`` rule b, and pf-adversary D2 of round ``nyxlqs`` - the rule
landed twenty minutes after this file was written and the cherry-pick that
recovered it carried the code without the rule).

    THIS FILE PINS ~~EIGHT~~ **TWELVE** FACTS THAT LANE-B OWNS, not one
    (round ``umlyof`` added four and pf-adversary D7 caught the header still
    saying eight; the four are named after the original eight): that
    ``mob_combat.remote_actors_preserving_the_ground_under_publication``
    exists; its signature (``legacy, entries, site`` positional, ``cell``
    and ``scene`` keyword-only); the three ``GROUND_ROWS_RACE_REASON_*``
    strings; the private report-once set ``mob_combat._GROUND_ROWS_RACE_
    WINDOW_REPORTED``; ``mob_loot.ground_rows_live_here`` folding an int
    scene id; the ``another_scenes_cell`` reason; and
    ``mob_loot.DropLedgerCell(scene=...)`` with ``compose_under_publication``.
    Added round ``umlyof``: ``caller_scene_fold``'s ``(key, refusal)`` return
    shape; the sentinels ``GROUND_LIVENESS_SCENE_ID_AMBIGUOUS`` and
    ``GROUND_LIVENESS_SCENE_ID_UNADDRESSED``; the reason word
    ``caller_scene_id_shares_a_folder``; and
    ``mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED``.
    (``world_scene_folder.SCENE_IDS_SHARING_AN_ADDRESSED_FOLDER`` and
    ``_FOLDER_BY_SCENE_ID`` are read too, but only for their SHAPE - see
    ``test_a_folder_shared_by_two_addressed_ids_arms_nothing``, which derives
    every expected value from the live registry for exactly this reason.)

    **LANE-B MAY AMEND EVERY ONE OF THEM WITHOUT ASKING THIS LANE**, in the
    same pull request that changes the thing being pinned.  They are pinned
    here because this lane's seam CALLS them and a silent change would be
    invisible until a click in a live scene - not to hold LANE-B still.
    ~~Measured cost if they are simply removed (pf-adversary, round
    ``nyxlqs``): this file goes ``11 failed, 12 passed``~~ - STRUCK, round
    ``umlyof`` (pf-adversary D7): ``11 + 12 = 23`` and this file has never
    had 23 tests (19 before this round, 20 after), so the number cannot be
    re-derived and a number nobody can check is the shape this project has
    been burned by twice.  The COST is real and unchanged in kind: removing
    any pinned fact turns a LANE-A file red over a LANE-B decision.  So:
    amend them, do not route around them.

WHY THE SCENE IS CARRIED ALL THE WAY DOWN (condition of the LANE-B letter,
and of pf-adversary's D16/D7 in that round): a session holds ONE loot cell
and that cell knows which scene its rows belong to.  A frame composed for
scene 1 must not be gated by a row standing in Bg0002, and naming the scene
is what turns that into ``another_scenes_cell`` - a stated cause and v141's
bytes - instead of a number.

    AND THE SCENE HAS TO BE NAMED IN THE FORM THE CELL USES.  ~~The letter
    passes ``scene_id`` straight through, which cannot gate anything~~ -
    STRUCK, round ``nyxlqs`` (pf-adversary D4): LANE-B FIXED THAT END in
    ``#615`` after round ``gx7xtp``'s letter reported it, so an int scene id
    folds now and the letter's literal shape gates correctly.  ~~The lane's
    own resolve stays because the cell publishes FOLDER names and this lane
    holds ids~~ - STRUCK, round ``umlyof`` (pf-adversary D8): the resolve is
    GONE.  The scene is carried down as an ``int`` SCENE ID, because the
    ambiguity card that keeps one scene's floor out of another scene's frame
    can only refuse an id, and a folder name is refused at this seam instead
    of forwarded.  What the test below pins is that the id and the name
    still fold to one scene at the reader that accepts both.
    See ``test_an_int_scene_id_and_the_folder_name_fold_to_one_scene``.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_combat                      # noqa: E402
from pirateforce_foundation import mob_loot                        # noqa: E402
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_ground_preserve as preserve,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_roster_scenes as roster_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene1 as scene1_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene2 as scene2_mod,
)
from pirateforce_foundation.lane_hooks import (                    # noqa: E402
    lane_a_choose_npc_scene14 as scene14_mod,
)
from pirateforce_foundation import world_scene_folder              # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy       # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The four call sites this lane owns, as (label, module, scene id).  A
#: responder added to this lane and NOT added here is the failure mode this
#: file's own last test refuses.
RESPONDERS = (
    ("scene1", scene1_mod, 1),
    ("scene2", scene2_mod, 2),
    ("scene14", scene14_mod, 14),
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _View:
    def __init__(self, rows: int) -> None:
        self.drops = tuple(range(rows))


class _Cell:
    """The narrowest stand-in for a session's loot cell: it answers the one
    call ``mob_loot.ground_rows_live_here`` makes - ``publication()`` ->
    ``(scene, view, elsewhere)`` - and nothing else.  A richer fake would be
    a second implementation of the thing under test.

    ``scene`` is a FOLDER NAME because that is what a real cell publishes;
    a fake that held a scene id would agree with a wiring bug rather than
    catch it.
    """

    def __init__(self, rows: int, scene: str) -> None:
        self._rows = rows
        self._scene = scene
        #: How many times anything asked this cell for its publication.
        #: "The cell is never touched by a scene the fold refuses" is an
        #: invariant about a CALL, and a fake that only returns values can
        #: never show that a call did not happen (round ``umlyof``).
        self.reads = 0

    def publication(self) -> tuple:
        self.reads += 1
        return (self._scene, _View(self._rows), 0)


class TheCallSitesAskTheGroundBeforeTheyCompose(unittest.TestCase):
    """Each responder accepts the cell and routes through the gate."""

    def test_every_responder_takes_a_mob_loot_cell_by_name(self) -> None:
        """It used to land in ``**_ignored``, which is how a wired call
        site can pass a cell for months and change nothing."""
        import inspect

        for label, module, _scene in RESPONDERS:
            with self.subTest(responder=label):
                parameters = inspect.signature(module.respond).parameters
                self.assertIn("mob_loot_cell", parameters)
                self.assertEqual(
                    parameters["mob_loot_cell"].kind,
                    inspect.Parameter.KEYWORD_ONLY)
                self.assertIsNone(parameters["mob_loot_cell"].default)

    def test_the_roster_responder_takes_it_too(self) -> None:
        """The roster module builds its responders in a factory, so its
        signature has to be read off a built one."""
        import inspect

        built = roster_mod._make_responder
        source = inspect.getsource(built)
        self.assertIn("mob_loot_cell: Any = None,", source)
        for scene in roster_mod.scenes_this_lane_answers_for():
            with self.subTest(scene=scene):
                entry = roster_mod._IDENTITY_OF_SCENE[scene]
                self.assertTrue(hasattr(entry, "SCENE_N_ID"))

    def test_no_responder_calls_v141s_composer_directly_any_more(
        self,
    ) -> None:
        """The property that keeps a fifth responder from being written the
        old way: the bare composer call is gone from every file in the
        lane's ChooseNPC family, and the preserving one is in each.
        """
        directory = ROOT / "src" / "pirateforce_foundation" / "lane_hooks"
        files = sorted(directory.glob("lane_a_choose_npc_*.py"))
        self.assertEqual(len(files), 4, [p.name for p in files])
        for path in files:
            with self.subTest(module=path.name):
                text = path.read_text(encoding="utf-8")
                body = "\n".join(
                    line for line in text.split("\n")
                    if not line.lstrip().startswith("#")
                )
                self.assertNotIn(
                    "legacy.make_runtime_remote_actors(entries)", body)
                self.assertIn("compose_answer(\n", body)


@contextlib.contextmanager
def _without_the_lock_holding_composer():
    """Run a block on a tree where the lock-holding composer does NOT exist.

    ROUND ``nyxlqs``.  It landed (LANE-B's ``#615``), so the hold-back branch
    can no longer be reached by simply calling the module - and a branch that
    can only be reached by the past is a branch nobody tests until the day it
    fires.  It still fires on a deploy older than ``#615``, which is what an
    operator rolling back has, so the branch is exercised by REMOVING the name
    rather than by hoping for its absence.

    IT MUST ALSO RUN ON THAT OLDER TREE (pf-adversary, round ``nyxlqs``, D3):
    the first draft read the name with a bare ``getattr``, so on a tree that
    really is pre-``#615`` the two tests whose whole purpose is "the hold-back
    branch still works there" raised ``AttributeError`` before their block
    ever ran.  Absent is now a case, not an error.

    WHAT IS AND IS NOT SIMULATED, said plainly because the docstring above
    reads bigger than the truth: only the NAME is removed.  ``mob_loot``
    keeps ``#615``'s int-folding.  That is enough for this branch and only
    this branch - it reaches ``mob_loot.GROUND_LIVENESS_UNKNOWN`` and
    ``mob_combat.remote_actors_preserving_the_ground``, both of which
    ``#615`` left untouched.  It is NOT a rollback of the tree.
    """
    name = preserve.UNDER_PUBLICATION_COMPOSER
    missing = object()
    landed = getattr(mob_combat, name, missing)
    if landed is not missing:
        delattr(mob_combat, name)
    try:
        yield
    finally:
        if landed is not missing:
            setattr(mob_combat, name, landed)


class TheHoldLiftsTheDayTheLockHoldingComposerLands(unittest.TestCase):
    """``COO-DECISION 20260902_1946`` approved the call site WITH two
    conditions - close the read-then-compose race, never sweep silently on
    a read - and LANE-B closed both in a LATER letter (``20260902_2048``)
    with ``remote_actors_preserving_the_ground_under_publication``.

    ~~"a composer that is not on ``main``.  chief measured the same absence
    and declined to wire it (``20260902_2208``).  So a cell that arrives
    today is held back rather than asked"~~ - STRUCK, round ``nyxlqs``,
    MEASURED: that composer reached ``main`` in LANE-B's ``#615`` while this
    lane's own round was being recovered, so the hold is OVER and the armed
    path is the live one.  ``lane_a_ground_preserve`` needed no edit for
    that - it looks the name up per call exactly so the hold could lift on a
    deploy - and these tests now pin BOTH sides: that it routes to the
    composer today, and that the hold-back branch still composes a frame on
    a tree that does not have it.

    WHAT DID NOT CHANGE, and it is the whole safety argument: ``runtime.py``
    still does not pass a cell, so every boot on ``main`` composes v141's own
    bytes either way.  The hold lifting is not a player-visible event.
    """

    def test_the_lock_holding_composer_has_landed(self) -> None:
        """The premise, checked rather than assumed - in the direction it
        now points.  When this goes red the composer left ``main`` again and
        the hold-back branch below is what production runs."""
        import inspect

        composer = preserve.under_publication_composer()
        self.assertIsNotNone(composer)
        parameters = inspect.signature(composer).parameters
        # The exact call shape ``compose_answer`` makes.  A composer that
        # moved its signature must be caught HERE, not by the frame-saving
        # ``except`` that would silently take today's bytes forever.
        for name in ("cell", "scene"):
            with self.subTest(parameter=name):
                self.assertEqual(
                    parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(
            [p for p, v in parameters.items()
             if v.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD],
            ["legacy", "entries", "site"])

    def test_a_cell_is_never_asked_while_the_composer_is_missing(
        self,
    ) -> None:
        """The cell object itself would raise if it were read, so this is
        not "the count came back unusable" - it is "nobody read it"."""
        class _Explodes:
            def publication(self):
                raise AssertionError("the cell was asked, and it must not be")

        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        expected = legacy.make_runtime_remote_actors(list(entries))
        preserve._HELD_BACK_REPORTED.clear()
        buffer = io.StringIO()
        with _without_the_lock_holding_composer():
            with contextlib.redirect_stdout(buffer):
                got = preserve.compose_answer(
                    legacy, list(entries), 1, _Explodes())
        self.assertEqual(got, expected)
        self.assertIn(preserve.CELL_HELD_BACK_TOKEN, buffer.getvalue())

    def test_the_held_back_line_is_one_ascii_token_per_scene(self) -> None:
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        preserve._HELD_BACK_REPORTED.clear()
        buffer = io.StringIO()
        with _without_the_lock_holding_composer():
            with contextlib.redirect_stdout(buffer):
                for _ in range(4):
                    preserve.compose_answer(
                        legacy, list(entries), 1, _Cell(3, "bg0001"))
                preserve.compose_answer(
                    legacy, list(entries), 2, _Cell(3, "Bg0002"))
        lines = [line for line in buffer.getvalue().split("\n")
                 if preserve.CELL_HELD_BACK_TOKEN in line]
        self.assertEqual(len(lines), 2, lines)
        for line in lines:
            with self.subTest(line=line):
                self.assertTrue(line.isascii())
                line.encode("cp874")
                self.assertIn("reason=", line)
                self.assertIn(preserve.UNDER_PUBLICATION_COMPOSER, line)

    def test_the_composer_is_handed_a_plain_int_not_the_callers_object(
        self,
    ) -> None:
        """pf-adversary D15, closed rather than left as a suspicion.

        This seam checks the scene and then hands it to readers that fold it
        AGAIN.  An ``int`` subclass that does not answer the two folds the
        same way would pass the check as one scene and arm the cell as
        another.  Not reachable from the four responders, which pass wire
        ints - which is exactly why it has to be pinned here rather than
        trusted to stay unreachable.
        """
        class _TwoFacedId(int):
            """Addressed scene 2 the first time it is asked, 14 after."""

            def __new__(cls, value: int) -> "_TwoFacedId":
                self = super().__new__(cls, value)
                self.asked = 0
                return self

            def __int__(self) -> int:
                self.asked += 1
                return 2 if self.asked == 1 else 14

        seen: dict = {}

        def _spy(legacy, entries, site, *, cell, scene=None):
            seen["scene"] = scene
            return (b"pc", b"frame")

        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        name = preserve.UNDER_PUBLICATION_COMPOSER
        landed = getattr(mob_combat, name)
        setattr(mob_combat, name, _spy)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                preserve.compose_answer(
                    legacy, list(entries), _TwoFacedId(2), _Cell(3, "Bg0002"))
        finally:
            setattr(mob_combat, name, landed)
        self.assertEqual(seen["scene"], 2)
        self.assertIs(type(seen["scene"]), int)

    def test_a_composer_that_raises_is_not_reported_as_a_missing_one(
        self,
    ) -> None:
        """pf-adversary D4, MEASURED and closed here.

        The hold-back line used to say ``<composer>_not_on_main`` for BOTH
        of its causes, so a composer that HAD landed and then raised - the
        exact case the ``except`` in ``compose_answer`` exists for - printed
        a sentence that was false about ``main``, once per scene, for the
        life of the process.  An operator grepping that line would go
        looking for a missing deploy.
        """
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        plain = legacy.make_runtime_remote_actors(list(entries))

        def _moved_signature(*_args, **_kwargs):
            raise TypeError("this composer moved its signature")

        name = preserve.UNDER_PUBLICATION_COMPOSER
        landed = getattr(mob_combat, name)
        preserve._HELD_BACK_REPORTED.clear()
        buffer = io.StringIO()
        setattr(mob_combat, name, _moved_signature)
        try:
            with contextlib.redirect_stdout(buffer):
                got = preserve.compose_answer(
                    legacy, list(entries), 2, _Cell(3, "Bg0002"))
        finally:
            setattr(mob_combat, name, landed)
        # The frame is never lost to this: v141's own bytes, as on any
        # other day the ground list cannot be armed.
        self.assertEqual(got, plain)
        out = buffer.getvalue()
        self.assertIn(preserve.HELD_BACK_COMPOSER_RAISED, out)
        self.assertNotIn(preserve.HELD_BACK_COMPOSER_ABSENT, out)
        # And the composer really was there while that line was printed,
        # which is what made the old wording false rather than merely vague.
        self.assertIsNotNone(preserve.under_publication_composer())

    def test_the_armed_path_reaches_the_landed_composer(self) -> None:
        """A cell arriving TODAY is asked under its own publication.

        Driven with a REAL ``mob_loot.DropLedgerCell`` rather than a fake:
        the point of the landed composer is that the count and the
        composition happen inside the cell's own lock, and a fake that
        merely answers ``publication()`` cannot host that - it would prove
        the fall back, which is what the other tests here are for.
        """
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        expected = legacy.make_runtime_remote_actors(list(entries))
        cell = mob_loot.DropLedgerCell(scene="Bg0002")
        self.assertTrue(callable(
            getattr(cell, "compose_under_publication", None)))
        preserve._HELD_BACK_REPORTED.clear()
        mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(legacy, list(entries), 2, cell)
        out = buffer.getvalue()
        # An empty floor gates to v141's own bytes - the ground list is kept
        # only while a row is actually standing.
        self.assertEqual(got, expected)
        # And none of the three race causes was reported, which is the whole
        # difference between the armed path and every fall back it has.
        self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)
        for reason in (mob_combat.GROUND_ROWS_RACE_REASON_NO_CELL,
                       mob_combat.GROUND_ROWS_RACE_REASON_CANNOT_HOST,
                       mob_combat.GROUND_ROWS_RACE_REASON_CELL_REFUSED):
            with self.subTest(reason=reason):
                self.assertNotIn(reason, out)

    def _cell_with_one_row_standing(self, scene: str):
        """A REAL ``DropLedgerCell`` publishing ``scene`` with one real row.

        pf-adversary D7 of this round: the frame-changing measurement was
        being taken through ``_Cell``, which cannot host a composition, so
        the composer that produced it was the RACY one - the very window
        ``COO-DECISION 20260902_1946`` condition 1 forbids.  Evidence for
        "the armed path changes the frame" has to come from the armed path.

        The row is built through ``GroundDrop``'s own constructor (which
        validates the key block, the f32 grid, the item and the scene), not
        through a stub, so a row this cell publishes is a row the rest of
        the lane would accept.
        """
        from pirateforce_foundation import field_drop_tables

        item_id = sorted(field_drop_tables.ITEMS)[0]
        drop = mob_loot.GroundDrop(
            drop_key=mob_loot.DROP_KEY_BASE,
            item_id=item_id,
            quantity=1,
            x=0.0, y=0.0, z=0.0,
            mob_identity=0x2001,
            killer_identity=0x1001,
            scene=scene,
        )
        ledger = mob_loot.DropLedger(
            drops=(drop,), generation=1,
            issued_through=mob_loot.DROP_KEY_BASE + 1)
        return mob_loot.DropLedgerCell(ledger=ledger, scene=scene)

    def test_the_armed_path_itself_changes_the_frame_when_a_row_stands(
        self,
    ) -> None:
        """The headline claim of this round, measured on the path it is
        about: a REAL cell, a REAL row, the LOCK-HOLDING composer, and no
        race line on the console.

        WHAT THE DELTA IS, and it is a wire fact, not a client one
        (pf-adversary D8): the preserving frame is a FIXED few bytes longer
        - the same delta for one row as for 255 - because it carries a
        MARKER, not the list.  That the client then keeps its ground pool
        is ``RE-130``'s claim about the client, proven nowhere in this repo
        and not proven here.
        """
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        base = legacy.make_runtime_remote_actors(list(entries))
        cell = self._cell_with_one_row_standing("Bg0002")
        publishing, view, _elsewhere = cell.publication()
        self.assertEqual(len(view.drops), 1, "the row must be standing")
        preserve._HELD_BACK_REPORTED.clear()
        mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            armed = preserve.compose_answer(legacy, list(entries), 2, cell)
        out = buffer.getvalue()
        self.assertNotEqual(armed, base)
        self.assertGreater(len(armed[1]), len(base[1]))
        # It really was the lock-holding composer: none of the three race
        # causes was reported, and the hold-back line is absent.
        self.assertNotIn(mob_combat.GROUND_ROWS_RACE_WINDOW_OPEN_TOKEN, out)
        self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)

    def test_the_composer_is_handed_the_scene_id_and_never_a_pre_fold(
        self,
    ) -> None:
        """~~"The composer is handed the FOLDER and never the raw id"~~ -
        STRUCK, round ``umlyof``, and the reversal is the round's headline.

        pf-adversary D5 of round ``qa86im`` measured that ``scene=folder``
        and ``scene=scene_id`` compose the same bytes for an ADDRESSED id
        and pinned the folder so the line could not be removed silently.
        LANE-B then named what the folder form COSTS (via chief,
        ``20260903_0505`` item three): ``mob_loot.caller_scene_fold``
        refuses an id whose folder is named by a second addressed id, and a
        name arriving pre-folded no longer knows which id it came from - so
        pre-folding here was the one caller that could arm scene 186's
        frame with scene 17's floor.  The pin is kept, pointed the other
        way: the ID must reach the fold.
        ``test_a_folder_shared_by_two_addressed_ids_arms_nothing`` is what
        makes the difference cost something rather than being a preference.
        """
        seen: dict = {}

        def _spy(legacy, entries, site, *, cell, scene=None):
            seen["scene"] = scene
            seen["site"] = site
            return (b"pc", b"frame")

        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        name = preserve.UNDER_PUBLICATION_COMPOSER
        landed = getattr(mob_combat, name)
        setattr(mob_combat, name, _spy)
        try:
            got = preserve.compose_answer(
                legacy, list(entries), 2, _Cell(1, "Bg0002"))
        finally:
            setattr(mob_combat, name, landed)
        self.assertEqual(got, (b"pc", b"frame"))
        self.assertEqual(seen["scene"], 2)
        self.assertIsInstance(seen["scene"], int)
        self.assertNotIsInstance(seen["scene"], str)
        # And it is still a scene the fold on the other side accepts, so
        # handing the id over is not "let the composer sort it out": the
        # gate that arms this frame reads the same count either way.
        self.assertEqual(
            mob_loot.caller_scene_fold(seen["scene"]),
            (mob_loot.scene_key("Bg0002"), 0))

    def test_a_cell_that_cannot_host_costs_the_ordering_not_the_frame(
        self,
    ) -> None:
        """The fall back the landed composer names for an older cell: it
        says ``cell_cannot_host_composition`` once and still answers."""
        legacy = _legacy()
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        entries = [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]
        preserve._HELD_BACK_REPORTED.clear()
        mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED.clear()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(
                legacy, list(entries), 2, _Cell(3, "Bg0002"))
        out = buffer.getvalue()
        self.assertEqual(len(got), 2)
        self.assertIn(mob_combat.GROUND_ROWS_RACE_REASON_CANNOT_HOST, out)
        self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)


class EachResponderReallyPassesItsOwnCellAndItsOwnScene(unittest.TestCase):
    """pf-adversary D3, closed.  Every one of these drives the REAL
    ``respond()``, so a call site with its arguments swapped, or one that
    drops the cell on the floor, goes red HERE - which a text scan of the
    source could never do."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _drive(self, module, scene, cell):
        """Call a responder for real and return its console output.

        ``_placements_by_index`` takes the legacy handle in one module and
        nothing in the others; asked for both rather than special-cased by
        name, so a fifth responder joins without editing this."""
        try:
            placements = module._placements_by_index(self.legacy)
        except TypeError:
            placements = module._placements_by_index()
        indices = tuple(sorted(placements))
        preserve._HELD_BACK_REPORTED.clear()
        # ROUND nyxlqs: the landed composer reports its own causes once per
        # (site, cause) for the life of the process, so a driver that does
        # not clear these reads an EMPTY console on every call after the
        # first and cannot tell "said it once" from "never said it".
        #
        # SAVED AND PUT BACK, not clobbered (pf-adversary D10): these two are
        # LANE-B's private module state and LANE-B's own tests save/restore
        # them.  A test file of ours that empties them and walks away decides
        # what another lane's tests see, purely by running first.
        borrowed = (
            mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED,
            mob_combat._GROUND_ROWS_RACE_WINDOW_REPORTED,
        )
        kept = tuple(set(each) for each in borrowed)
        for each in borrowed:
            each.clear()
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                answer = module.respond(
                    legacy=self.legacy,
                    chosen_identities=(0x2000 + indices[0] + 1,),
                    population_indices=indices,
                    last_target_pos=(0.0, 0.0, 0.0, 0.0),
                    scene_id=scene,
                    mob_loot_cell=cell,
                )
        finally:
            for each, before in zip(borrowed, kept):
                each.clear()
                each.update(before)
        return answer, buffer.getvalue()

    def test_no_cell_says_no_cell_and_a_cell_reaches_the_composer(
        self,
    ) -> None:
        """~~"and a cell says held back"~~ - STRUCK, round ``nyxlqs``: the
        lock-holding composer landed (LANE-B ``#615``), so a cell arriving
        at a real call site is now ASKED instead of held.  What this test is
        for has not moved an inch - a call site with its arguments swapped,
        or one that drops the cell, still cannot produce the second line."""
        for label, module, scene in RESPONDERS:
            if not hasattr(module, "_placements_by_index"):
                continue
            with self.subTest(responder=label):
                answer, out = self._drive(module, scene, None)
                self.assertIsNotNone(answer)
                # No cell: the cause the console names is the wiring hole,
                # and it is NOT the held-back one.
                self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)
                self.assertIn("no_cell", out)

                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                answer, out = self._drive(module, scene, _Cell(2, folder))
                self.assertIsNotNone(answer)
                # A cell that reached the gate flips the cause: this fake
                # cannot host a composition, so the landed composer names
                # THAT, which only a call site that really passed the cell
                # can produce.  The hold-back line must be gone.
                self.assertIn(
                    mob_combat.GROUND_ROWS_RACE_REASON_CANNOT_HOST, out)
                self.assertNotIn(preserve.CELL_HELD_BACK_TOKEN, out)
                self.assertNotIn("no_cell", out)

    def test_a_live_row_changes_the_frame_and_an_empty_floor_does_not(
        self,
    ) -> None:
        """~~"the frame is the same either way today"~~ - STRUCK, round
        ``nyxlqs``, MEASURED.  While the cell was held back that was true by
        construction; now that the composer is on ``main`` a cell reporting a
        LIVE ROW is exactly what the gate is armed for, so the bytes MUST
        differ - scene 2 measured 12,574 -> 12,577.  A cell publishing an
        EMPTY floor still composes v141's own bytes, which is the half that
        keeps this safe to land before chief's call-site line.

        THREE BYTES IS A MARKER, NOT A LIST (pf-adversary D8): the delta is
        the same for one row as for 255, so the frame does not carry the
        ground rows - it tells the client not to clear its pool.  This
        drives ``_Cell``, which cannot host a composition, so the composer
        it reaches is the RACY one; the armed path's own measurement is
        ``test_the_armed_path_itself_changes_the_frame_when_a_row_stands``.

        This is a frame nobody can reach from a client today: ``runtime.py``
        passes no cell, so both halves are reachable only from a test."""
        for label, module, scene in RESPONDERS:
            if not hasattr(module, "_placements_by_index"):
                continue
            with self.subTest(responder=label):
                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                without, _ = self._drive(module, scene, None)
                live, _ = self._drive(module, scene, _Cell(2, folder))
                empty, _ = self._drive(module, scene, _Cell(0, folder))
                self.assertNotEqual(without.frame, live.frame)
                self.assertGreater(len(live.frame), len(without.frame))
                # pf-adversary D9: the replaced test pinned the pc of the
                # cell path and this one dropped it, so a mutant that
                # corrupted the armed pc while keeping the frame length
                # survived.  Both halves are pinned now.
                self.assertNotEqual(without.pc, live.pc)
                self.assertEqual(without.pc, empty.pc)
                self.assertEqual(without.frame, empty.frame)


class TheBytesAreUnchangedWhileNoCellIsWired(unittest.TestCase):
    """The whole safety argument for landing this before chief's line."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    def _entries(self):
        legacy = self.legacy
        attr = legacy.make_remote_movement_attr(
            0x2001, 1.0, 2.0, 3.0, 0.0, mask=0x03)
        return [legacy.make_remote_actor_entry(
            4, 0x2001, [(legacy.MOVEMENT_ATTR, attr)])]

    def test_no_cell_composes_exactly_what_v141_composes(self) -> None:
        entries = self._entries()
        expected = self.legacy.make_runtime_remote_actors(list(entries))
        for label, _module, scene in RESPONDERS + (("ocean", None, 126),):
            with self.subTest(responder=label):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    got = preserve.compose_answer(
                        self.legacy, list(entries), scene, None)
                self.assertEqual(got, expected)

    def test_an_int_scene_id_and_the_folder_name_fold_to_one_scene(
        self,
    ) -> None:
        """THE DEFECT THIS FILE EXISTS FOR, and it is measured rather than
        argued.

        ~~"``mob_loot.ground_rows_live_here`` folds its scene through
        ``scene_key``, which refuses anything but a ``str``.  Wired the way
        LANE-B's letter spells it - passing ``scene_id`` - every click on
        every scene reads ``caller_scene_unreadable`` and the gate can never
        open."~~ - STRUCK, round ``nyxlqs``, MEASURED: LANE-B FIXED IT at
        their end in ``#615`` after this lane reported it (round ``gx7xtp``'s
        letter, and their reply ``20260903_0152``).  ``ground_rows_live_here``
        now folds an int scene id through ``caller_scene_fold``, so the two
        shapes agree instead of one of them being a permanent no-op.

        The test stays, pointed at what is true now, because the property it
        buys is what mattered: THE TWO SHAPES MUST AGREE.

        ~~"If either side ever stops folding one of them, one of these two
        lines goes red"~~ - STRUCK before it shipped (pf-adversary D6 of
        this round, MEASURED both directions): making LANE-B's
        ``caller_scene_fold`` refuse ints again turns THIS test red, but
        deleting this lane's own resolve from ``ground_rows_for_scene``
        leaves it GREEN - the folder and the id fold alike for an addressed
        scene now, so this test cannot see that side.  What kills the
        LANE-A side is ``test_an_unaddressed_scene_id_never_reaches_the_
        cell`` (measured: 3 subfailures) and, in the armed path,
        ``test_the_composer_is_handed_the_folder_and_never_the_raw_id``.
        The claim is one-directional and now says so."""
        cell = _Cell(3, "Bg0002")
        # The letter's literal shape, since LANE-B's #615: a real count.
        self.assertEqual(mob_loot.ground_rows_live_here(cell, 2), 3)
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                mob_loot.ground_rows_live_here(cell, 2)),
            "")
        # The lane's shape since round ``umlyof``: hand the ID over and let
        # the one fold turn it into the cell's own name.
        self.assertEqual(preserve.ground_rows_for_scene(cell, 2), 3)
        # And they still disagree about the one thing they must: another
        # scene's floor never arms this frame, from either shape.
        for asked in (14, "bg0014"):
            with self.subTest(scene=asked):
                self.assertEqual(
                    mob_loot.ground_liveness_reason(
                        mob_loot.ground_rows_live_here(cell, asked)),
                    "another_scenes_cell")
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                preserve.ground_rows_for_scene(cell, 14)),
            "another_scenes_cell")
        for _label, _module, scene in RESPONDERS:
            with self.subTest(scene=scene):
                folder = world_scene_folder.scene_folder_for_scene_id(scene)
                self.assertIsNotNone(folder)
                self.assertEqual(
                    preserve.ground_rows_for_scene(_Cell(2, folder), scene),
                    2)

    def test_an_unaddressed_scene_id_never_reaches_the_cell(self) -> None:
        """Fail-closed in the only safe direction: ``None`` reaching
        ``ground_rows_live_here`` means "keep whatever scene the cell is
        publishing", which is the cross-scene gating this is meant to
        prevent.  An unresolvable id stops here instead.

        ~~"every one of them is ``caller_scene_unreadable``"~~ - STRUCK,
        round ``umlyof``: the fold that answers now is ``mob_loot.caller_
        scene_fold``, which tells the four cases APART.  The property this
        test buys is unchanged and is checked on every one of them: not
        live, and THE CELL IS NEVER ASKED.  The names are checked too,
        because "unaddressed id" and "not a scene id at all" are different
        bugs at a call site and a flat answer made an operator guess.
        """
        self.assertIsNone(
            world_scene_folder.scene_folder_for_scene_id(99999))
        expected = {
            99999: mob_loot.GROUND_LIVENESS_SCENE_ID_UNADDRESSED,
            None: mob_loot.GROUND_LIVENESS_BAD_SCENE,
            3.0: mob_loot.GROUND_LIVENESS_BAD_SCENE,
            True: mob_loot.GROUND_LIVENESS_BAD_SCENE,
            # A FOLDER NAME IS NOT A SCENE ID AT THIS SEAM, and these two
            # are why (pf-adversary D1 of this round, MEASURED, and D5 -
            # the first draft asserted "the cell is never asked" for every
            # case and then quietly skipped the assertion on the one case
            # where it read the cell).  ``mob_loot.caller_scene_fold``
            # applies the ambiguity card only on its ``int`` branch, so a
            # name forwarded there walks past the card this round exists to
            # reach; and the read itself is not free - a real cell retires
            # expired rows while answering a call it is going to refuse.
            "1": mob_loot.GROUND_LIVENESS_BAD_SCENE,
            "bg0001": mob_loot.GROUND_LIVENESS_BAD_SCENE,
            "Bg1001": mob_loot.GROUND_LIVENESS_BAD_SCENE,
        }
        for bad, want in expected.items():
            with self.subTest(scene_id=bad):
                cell = _Cell(9, "bg0001")
                answer = preserve.ground_rows_for_scene(cell, bad)
                self.assertEqual(answer, want)
                self.assertFalse(mob_loot.ground_is_live(answer))
                self.assertEqual(cell.reads, 0)
        # ``"bg0001"`` is the name this cell IS publishing, which is what
        # makes it the dangerous one: the fold on the other side would have
        # answered it with a live count.  Measured here so the refusal above
        # is known to cost something.
        self.assertEqual(
            mob_loot.ground_rows_live_here(_Cell(9, "bg0001"), "bg0001"), 9)
        # And the refusal value can never be mistaken for a waiver: handing
        # it on to any reader refuses again, without a cell being read.
        waived, why = preserve.scene_the_cell_may_be_asked_about("bg0001")
        self.assertEqual(why, mob_loot.GROUND_LIVENESS_BAD_SCENE)
        self.assertIsNotNone(waived)
        onward = _Cell(9, "bg0001")
        self.assertEqual(
            mob_loot.ground_rows_live_here(onward, waived),
            mob_loot.GROUND_LIVENESS_BAD_SCENE)
        self.assertEqual(onward.reads, 0)

    def test_a_folder_shared_by_two_addressed_ids_arms_nothing(self) -> None:
        """THE HOLE THAT ROUND ``umlyof`` CLOSED, driven rather than argued.

        ``world_scene_folder.SCENE_IDS_SHARING_AN_ADDRESSED_FOLDER`` names
        scene 17 and scene 186, both ``Bg1001``; only 17 is addressed today,
        which is why nothing is served wrongly right now.  This test
        addresses 186 for the length of one call - the registry reader is
        ``dict(_FOLDER_BY_SCENE_ID)`` per call, so the day is simulated
        honestly and not mocked away - and demands that the frame is
        v141's own and THE CELL IS NEVER READ.

        The second half is what makes it a regression test rather than a
        restatement: the PRE-FOLDED shape this round removed is run against
        the same cell on the same day, and it ARMS.
        """
        pair = world_scene_folder.SCENE_IDS_SHARING_AN_ADDRESSED_FOLDER[0]
        first, second, folder = pair
        # DERIVED, NOT PINNED (pf-adversary D6): asserting the literal
        # ``(17, 186, "Bg1001")`` here, or that 17 arms again afterwards,
        # would turn THIS LANE'S file red on the day somebody edits
        # ``world_scene_folder`` to address 186 - which is the day the whole
        # test was written for, and the exact cross-lane pinning this file's
        # own header forbids.  Only the SHAPE is asserted.
        self.assertIsInstance(first, int)
        self.assertIsInstance(second, int)
        self.assertIsInstance(folder, str)
        legacy = _legacy()
        entries = self._entries()
        plain = legacy.make_runtime_remote_actors(list(entries))
        registry = world_scene_folder._FOLDER_BY_SCENE_ID
        reported = set(mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED)
        # Both ids addressed to the same folder, whatever the registry says
        # today: the simulation must hold on the day one, both, or neither
        # of them is already there.
        world_scene_folder._FOLDER_BY_SCENE_ID = tuple(
            (sid, name) for sid, name in registry
            if sid not in (first, second)
        ) + ((first, folder), (second, folder))
        try:
            for scene_id in (first, second):
                with self.subTest(scene_id=scene_id):
                    cell = _Cell(3, folder)
                    answer = preserve.ground_rows_for_scene(cell, scene_id)
                    self.assertEqual(
                        answer,
                        mob_loot.GROUND_LIVENESS_SCENE_ID_AMBIGUOUS)
                    self.assertEqual(
                        mob_loot.ground_liveness_reason(answer),
                        "caller_scene_id_shares_a_folder")
                    self.assertEqual(cell.reads, 0)
                    armed = _Cell(3, folder)
                    with contextlib.redirect_stdout(io.StringIO()):
                        got = preserve.compose_answer(
                            legacy, list(entries), scene_id, armed)
                    self.assertEqual(got, plain)
                    self.assertEqual(armed.reads, 0)
            # WHAT THE NAME FORM ANSWERS on that same day, which is what
            # this file used to hand over and what any caller that folds
            # before asking still hands over.  It is NOT a re-run of the
            # deleted function (pf-adversary D12: a re-typed copy measures
            # the copy) - it is the reader on the other side, asked the way
            # a pre-folded caller asks it, and it comes back a COUNT: one
            # scene's frame armed by another scene's floor.
            pre_folded = _Cell(3, folder)
            self.assertEqual(
                mob_loot.ground_rows_live_here(pre_folded, folder), 3)
            self.assertEqual(pre_folded.reads, 1)
        finally:
            world_scene_folder._FOLDER_BY_SCENE_ID = registry
            mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.clear()
            mob_combat._GROUND_ACTORS_LIVENESS_UNKNOWN_REPORTED.update(
                reported)
        # And the day is over: with the registry restored, this lane's gate
        # answers whatever the LIVE registry allows for that id - derived
        # from the same authority rather than pinned to today's answer, so
        # this test cannot pass by leaving the gate shut for everyone and
        # cannot go red when the registry changes.
        _key, refusal_now = mob_loot.caller_scene_fold(first)
        open_again = _Cell(3, folder)
        self.assertEqual(
            preserve.ground_rows_for_scene(open_again, first),
            refusal_now if refusal_now else 3)

    def test_the_console_says_the_real_cause_not_a_guess(self) -> None:
        """``no_cell`` is a different fact from ``cell_refused`` and from
        ``another_scenes_cell``, and an operator has to be able to tell
        them apart from the line alone."""
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                mob_loot.ground_rows_live_here(None, 1)),
            "no_cell")
        self.assertEqual(
            mob_loot.ground_liveness_reason(
                preserve.ground_rows_for_scene(_Cell(3, "Bg0002"), 1)),
            "another_scenes_cell")

    def test_a_cell_from_another_scene_cannot_gate_this_frame(self) -> None:
        """The condition the LANE-B letter and pf-adversary D16 both put on
        this call site: rows standing in Bg0002 are not this frame's rows.
        """
        entries = self._entries()
        expected = self.legacy.make_runtime_remote_actors(list(entries))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            got = preserve.compose_answer(
                self.legacy, list(entries), 1, _Cell(3, "Bg0002"))
        self.assertEqual(got, expected)

    def test_the_gate_itself_is_not_decorative(self) -> None:
        """The scene resolve really does turn a cell into a live count, and
        a live count really does compose different bytes.

        ``compose_answer`` deliberately does NOT reach that shape today -
        it holds the cell back until the lock-holding composer lands, see
        ``TheCellIsHeldBackUntilTheLockHoldingComposerLands`` - so this
        drives the two halves separately.  Collapsing them into one call
        is what the hold forbids, not what it hides.
        """
        entries = self._entries()
        plain = self.legacy.make_runtime_remote_actors(list(entries))
        live = preserve.ground_rows_for_scene(_Cell(3, "bg0001"), 1)
        self.assertTrue(mob_loot.ground_is_live(live), live)
        self.assertEqual(live, 3)
        with contextlib.redirect_stdout(io.StringIO()):
            preserved = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, list(entries),
                mob_combat.choose_npc_site(1), ground_rows_left=live)
        self.assertNotEqual(preserved, plain)
        # An empty floor in the right scene is still v141's own bytes: the
        # gate turns on a row STANDING, not on a cell existing.
        empty = preserve.ground_rows_for_scene(_Cell(0, "bg0001"), 1)
        self.assertEqual(empty, 0)
        self.assertFalse(mob_loot.ground_is_live(empty))
        with contextlib.redirect_stdout(io.StringIO()):
            composed = mob_combat.remote_actors_preserving_the_ground(
                self.legacy, list(entries),
                mob_combat.choose_npc_site(1), ground_rows_left=empty)
        self.assertEqual(composed, plain)

    def test_each_responder_gets_its_own_site_name(self) -> None:
        """One shared name would let whichever responder fires first
        silence the other three for the life of the process - the console
        report is once per (site, cause) pair, by design."""
        names = {
            scene: mob_combat.choose_npc_site(scene)
            for _label, _module, scene in RESPONDERS
        }
        names[126] = mob_combat.choose_npc_site(126)
        self.assertEqual(len(set(names.values())), len(names), names)
        for scene, name in names.items():
            with self.subTest(scene=scene):
                self.assertTrue(name.isascii())
                self.assertNotIn(" ", name)


if __name__ == "__main__":
    unittest.main()
