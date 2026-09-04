"""(b'') redefined: the set is derived from the production login composer.

`COO-DECISION 2026-09-04T05:45+07:00` item 2 asked LANE-GM for two things a
test has to carry, and this file is where they live:

  * an IDENTICAL test (both branches, faction included) proving the derived
    set is the set production login actually composes -- so the day
    `player_wire` changes its mask, this file goes red rather than the wall
    quietly admitting a shape nobody has shipped;
  * the pinned masks, in hex, written where a reader can find them.

Nothing here claims a login-shaped 0x309A frame is safe to APPLY to an
existing actor.  That question belongs to the `/speed` (b'') game test on the
owner's screen (`0545` item 3), and every send door is still shut by its own
gate.
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import player_wire, world_faction_admission  # noqa: E402
from pirateforce_foundation.gm import attr_wire, login_mask  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

#: The masks measured on this commit, written down so a reader does not have
#: to run the derivation to know what it answers today.  These are NOT what
#: the code reads -- the code derives them every call.  A test that compared
#: the derivation against these numbers alone would pin a copy; the tests
#: below compare it against the PRODUCTION COMPOSER, and use these only to
#: say out loud what that comparison currently agrees on.
PINNED_PLAIN_MASKS = (0x034F, 0x0000000000000801)
PINNED_FACTION_MASKS = (0x074F, 0x0000000000000801)


def _legacy():
    return load_legacy(ROOT / "current/pf_login_game_server_v141.py")


class TheDerivationAgreesWithTheProductionComposerTests(unittest.TestCase):
    """The IDENTICAL test `COO-DECISION 0545` item 2 asked for, both branches."""

    def setUp(self):
        self.legacy = _legacy()
        self.scene = world_faction_admission.PROVEN_FACTION_SCENE_IDS[0]

    def _identical(self, produced: bytes, values: dict):
        body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 0x11, 0x22, values,
        )
        self.assertEqual(len(produced), len(body))
        self.assertEqual(produced, body)
        return basic_mask, actor_mask

    def test_the_plain_login_branch_is_byte_identical_to_its_derived_set(self):
        produced = player_wire.make_actor_attr_with_name_and_class(
            self.legacy, 0x11, 0x22, self.scene, 0, "Probe",
        )
        basic_mask, actor_mask = login_mask.parse_block_masks(self.legacy, produced)
        rows = login_mask.field_x_for_masks(basic_mask, actor_mask)
        values = _values_for(self.legacy, rows, self.scene, faction=False)
        self.assertEqual(self._identical(produced, values), (basic_mask, actor_mask))
        self.assertEqual((basic_mask, actor_mask), PINNED_PLAIN_MASKS)

    def test_the_faction_login_branch_is_byte_identical_to_its_derived_set(self):
        produced = player_wire.make_actor_attr_with_name_class_and_faction(
            self.legacy, 0x11, 0x22, self.scene, 0, "Probe",
            world_faction_admission.PROVEN_BASIC_FACTION,
        )
        basic_mask, actor_mask = login_mask.parse_block_masks(self.legacy, produced)
        rows = login_mask.field_x_for_masks(basic_mask, actor_mask)
        values = _values_for(self.legacy, rows, self.scene, faction=True)
        self.assertEqual(self._identical(produced, values), (basic_mask, actor_mask))
        self.assertEqual((basic_mask, actor_mask), PINNED_FACTION_MASKS)

    def test_the_derived_set_is_the_union_and_the_plain_branch_is_a_subset(self):
        shapes = login_mask.production_login_shapes(self.legacy)
        plain = set(login_mask.field_x_for_masks(*shapes["plain"]))
        factioned = set(login_mask.field_x_for_masks(*shapes["faction"]))
        self.assertTrue(plain < factioned)
        self.assertEqual(set(login_mask.login_field_x(self.legacy)), factioned)

    def test_the_derivation_does_not_depend_on_the_probe_arguments(self):
        # A derivation that changed with the probe would be measuring the
        # probe, not the composer.  Second probe, different in every field
        # the composer accepts.
        produced = player_wire.make_actor_attr_with_name_and_class(
            self.legacy, 0x7FFF, 0x1, self.scene, 0, "A much longer name",
            class_id=4, level=61, movement_speed=123.5,
            hp_current=7, hp_max=9,
        )
        self.assertEqual(
            login_mask.parse_block_masks(self.legacy, produced), PINNED_PLAIN_MASKS,
        )


class TheParserWalksTheBlockTheWayEncodeBlockWritesItTests(unittest.TestCase):
    def setUp(self):
        self.legacy = _legacy()

    def test_it_round_trips_every_field_in_the_table(self):
        # The widest possible block, including both wstr rows and the blob,
        # so the length-prefixed kinds are actually walked rather than only
        # the fixed-width ones the login block happens to use.
        values = _one_value_per_row()
        body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 1, 0, values,
        )
        self.assertEqual(
            login_mask.parse_block_masks(self.legacy, body), (basic_mask, actor_mask),
        )

    def test_it_round_trips_a_block_with_a_long_name(self):
        # wstr is the one kind whose length is not knowable from `FIELDS`.
        values = {1: "N" * 300, 2: 5, 3: 1, 4: 1, 7: 1.0, 9: 1, 10: 0, 13: 1, 24: 1}
        body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 1, 0, values,
        )
        self.assertEqual(
            login_mask.parse_block_masks(self.legacy, body), (basic_mask, actor_mask),
        )

    def test_a_body_that_is_not_a_dbattribute_body_is_refused_by_name(self):
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.parse_block_masks(self.legacy, b"\x00\x00\x00\x00")
        self.assertIn("not a DBAttribute body", str(caught.exception))

    def test_a_truncated_body_is_refused_rather_than_parsed(self):
        body, _b, _a = attr_wire.encode_block(self.legacy, 1, 0, {1: "Anne", 2: 3})
        with self.assertRaises(login_mask.LoginMaskError):
            login_mask.parse_block_masks(self.legacy, body[:-4])

    def test_a_refusal_is_an_attr_wire_error_so_existing_doors_still_catch_it(self):
        self.assertTrue(issubclass(login_mask.LoginMaskError, attr_wire.AttrWireError))


class TheSensitiveRowCanNeverRideTheLoginSetTests(unittest.TestCase):
    """`COO-DECISION 0545` item 5, in code: if the login mask ever holds x=30,
    raise -- do not send."""

    def setUp(self):
        self.legacy = _legacy()

    def test_todays_derived_set_does_not_hold_a_sensitive_row(self):
        rows = set(login_mask.login_field_x(self.legacy))
        self.assertEqual(rows & attr_wire.SENSITIVE_FIELDS, set())

    def test_a_mask_that_sets_the_sensitive_bit_raises_instead_of_answering(self):
        sensitive_x = sorted(attr_wire.SENSITIVE_FIELDS)[0]
        bit = attr_wire.BY_X[sensitive_x][2]
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.field_x_for_masks(PINNED_PLAIN_MASKS[0], PINNED_PLAIN_MASKS[1] | bit)
        self.assertIn("SENSITIVE_FIELDS", str(caught.exception))
        self.assertIn(str(sensitive_x), str(caught.exception))

    def test_a_mask_bit_no_row_is_bound_to_raises_rather_than_being_ignored(self):
        # Bit 31 of the ActorAttr mask is bound to no field ([PROVEN], see
        # `attr_wire.FIELDS`' own comment).  Silently dropping it would let a
        # frame carry a field this table cannot name.
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.field_x_for_masks(PINNED_PLAIN_MASKS[0], PINNED_PLAIN_MASKS[1] | (1 << 31))
        self.assertIn("no", str(caught.exception).lower())


class ThePairedBitsAreNotSplitByTheDerivationTests(unittest.TestCase):
    def test_one_shared_bit_yields_both_rows_of_the_pair(self):
        for a, b in ((39, 40), (41, 42)):
            bit = attr_wire.BY_X[a][2]
            self.assertEqual(bit, attr_wire.BY_X[b][2])
            rows = login_mask.field_x_for_masks(0, bit)
            self.assertEqual(rows, (a, b))


class TheWallNowAdmitsTheLoginShapeAndNothingElseTests(unittest.TestCase):
    def setUp(self):
        self.legacy = _legacy()
        self.scene = world_faction_admission.PROVEN_FACTION_SCENE_IDS[0]

    def test_a_login_shaped_block_builds_a_frame(self):
        rows = login_mask.login_field_x(self.legacy)
        values = _values_for(self.legacy, rows, self.scene, faction=True)
        pc, frame = attr_wire.make_update_attr_frame(self.legacy, 1, 0, values)
        self.assertTrue(frame)
        self.assertIn(struct.pack("<H", attr_wire.UPDATE_ATTR_VITAL_ID), frame)

    def test_the_plain_branch_shape_also_builds(self):
        shapes = login_mask.production_login_shapes(self.legacy)
        rows = login_mask.field_x_for_masks(*shapes["plain"])
        values = _values_for(self.legacy, rows, self.scene, faction=False)
        pc, frame = attr_wire.make_update_attr_frame(self.legacy, 1, 0, values)
        self.assertTrue(frame)

    def test_one_row_short_of_the_login_shape_is_refused(self):
        rows = login_mask.login_field_x(self.legacy)
        values = _values_for(self.legacy, rows, self.scene, faction=True)
        values.pop(24)
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.make_update_attr_frame(self.legacy, 1, 0, values)
        self.assertIn("not login-shaped", str(caught.exception))

    def test_one_row_MORE_than_the_login_shape_is_refused(self):
        # The half a subset check would have missed.  A wider frame changes
        # the mask, and `0545` item 2 says the mask must EQUAL login's.
        rows = login_mask.login_field_x(self.legacy)
        values = _values_for(self.legacy, rows, self.scene, faction=True)
        values[16] = 3
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.make_update_attr_frame(self.legacy, 1, 0, values)
        self.assertIn("not login-shaped", str(caught.exception))

    def test_the_one_row_speed_shape_that_killed_a_client_is_still_refused(self):
        with self.assertRaises(attr_wire.AttrWireError):
            attr_wire.make_update_attr_frame(self.legacy, 1, 0, {7: 400.0})

    def test_the_full_55_row_block_is_no_longer_the_admitted_shape(self):
        # The wall did not merely get narrower: the old shape is refused too,
        # because the mask it composes is not one production login composes.
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            attr_wire.make_update_attr_frame(self.legacy, 1, 0, _one_value_per_row())
        self.assertIn("not login-shaped", str(caught.exception))


class TheBuilderLaneBPlugsInTests(unittest.TestCase):
    """`COO-DECISION 20260904_0546` item 3: LANE-B does not define the set.

    And it does not pick the BRANCH either -- pf-adversary round `4fxkam`
    (D2) measured the first draft composing the faction shape for every
    connection, which both handed a faction bit to connections whose login
    withheld one and refused those same connections for a row (x=11) they
    never needed.  The shape is now a question asked of the connection.
    """

    def setUp(self):
        self.legacy = _legacy()

    def _hooks_for(self, shape):
        rows = login_mask.field_x_for_masks(*shape)
        named_rows, login_rows = attr_wire.split_sources(rows)
        full = _values_for(self.legacy, rows, 1, faction=(11 in rows))
        return _Hooks(
            named={x: full[x] for x in named_rows},
            login={x: full[x] for x in login_rows},
            masks=shape,
        ), full

    def test_it_refuses_an_override_outside_the_login_set(self):
        hooks, _full = self._hooks_for(PINNED_FACTION_MASKS)
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.build_login_shaped_frame(
                self.legacy, 7, 1, 0, {16: 3}, hooks=hooks,
            )
        self.assertIn("16", str(caught.exception))

    def test_it_refuses_a_sensitive_override_by_name(self):
        sensitive_x = sorted(attr_wire.SENSITIVE_FIELDS)[0]
        hooks, _full = self._hooks_for(PINNED_FACTION_MASKS)
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.build_login_shaped_frame(
                self.legacy, 7, 1, 0, {sensitive_x: b"\x00"}, hooks=hooks,
            )
        self.assertIn(str(sensitive_x), str(caught.exception))

    def test_on_a_real_boot_today_it_refuses_and_names_the_missing_mask_point(self):
        # The FIRST thing missing on a real boot is now the connection's own
        # login mask, not the value sources -- and the refusal says so, with
        # the request number that fixes it.
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            login_mask.build_login_shaped_frame(
                self.legacy, 7, 1, 0, {3: 50}, hooks=_NoHooks(),
            )
        self.assertIn(login_mask.LOGIN_MASK_READ_POINT, str(caught.exception))

    def test_with_the_mask_point_present_the_value_sources_are_named_next(self):
        hooks = _MaskHooks(PINNED_FACTION_MASKS)
        with self.assertRaises(attr_wire.AttrWireError) as caught:
            login_mask.build_login_shaped_frame(
                self.legacy, 7, 1, 0, {3: 50}, hooks=hooks,
            )
        self.assertIn(attr_wire.LIVE_VALUE_READ_POINT, str(caught.exception))

    def test_the_faction_branch_composes_its_own_shape(self):
        hooks, full = self._hooks_for(PINNED_FACTION_MASKS)
        pc, frame = login_mask.build_login_shaped_frame(
            self.legacy, 7, 1, 0, {3: 42}, hooks=hooks,
        )
        expected = dict(full)
        expected[3] = 42
        body, basic_mask, actor_mask = attr_wire.encode_block(self.legacy, 1, 0, expected)
        self.assertIn(body, frame)
        self.assertEqual((basic_mask, actor_mask), PINNED_FACTION_MASKS)

    def test_the_plain_branch_composes_ITS_shape_and_never_asks_for_x11(self):
        # pf-adversary D7: the first draft tested only the faction branch, so
        # the plain route through this builder had never once run -- and it
        # was the broken one.  This is its twin, and it asserts the thing D2
        # got wrong: no faction bit, and no demand for a row this connection's
        # login never sent.
        hooks, full = self._hooks_for(PINNED_PLAIN_MASKS)
        self.assertNotIn(11, full)
        pc, frame = login_mask.build_login_shaped_frame(
            self.legacy, 7, 1, 0, {3: 42}, hooks=hooks,
        )
        expected = dict(full)
        expected[3] = 42
        body, basic_mask, actor_mask = attr_wire.encode_block(self.legacy, 1, 0, expected)
        self.assertIn(body, frame)
        self.assertEqual((basic_mask, actor_mask), PINNED_PLAIN_MASKS)
        self.assertEqual(basic_mask & attr_wire.BY_X[11][2], 0)

    def test_a_plain_connection_is_not_refused_for_the_faction_row(self):
        # The other half of D2: composing the union asked the value sources
        # for x=11, which the store has no column for at all, so a plain
        # connection was refused with `absent=11` -- a shelf, not a gate.
        hooks, _full = self._hooks_for(PINNED_PLAIN_MASKS)
        named_rows, login_rows = attr_wire.split_sources(
            login_mask.field_x_for_masks(*PINNED_PLAIN_MASKS)
        )
        self.assertNotIn(11, named_rows)
        self.assertNotIn(11, login_rows)

    def test_the_sources_asked_for_are_exactly_the_login_set(self):
        named_rows, login_rows = attr_wire.login_scoped_sources(self.legacy)
        self.assertEqual(
            tuple(sorted(set(named_rows) | set(login_rows))),
            login_mask.login_field_x(self.legacy),
        )
        # x=9, x=10 and x=11 carry the value LOGIN sent this session, never a
        # typed column (`COO-DECISION 0545` item 2; pf-adversary D3 for why
        # x=9 in particular must not come from a column -- it selects which
        # pair of rows the client reads HP from).
        self.assertEqual(login_rows, (7, 9, 10, 11))
        self.assertEqual(set(named_rows), {1, 2, 3, 4, 13, 24})
        self.assertEqual(set(named_rows) & set(login_rows), set())


class TheConnectionMaskReadPointIsNamedAndMissingTests(unittest.TestCase):
    def setUp(self):
        self.legacy = _legacy()

    def test_the_read_point_name_is_spelled_once_and_does_not_exist_yet(self):
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.login_masks_for_connection(self.legacy, 7, hooks=_NoHooks())
        self.assertIn(login_mask.LOGIN_MASK_READ_POINT, str(caught.exception))
        self.assertIn("CORE-REQUEST-GM-053", str(caught.exception))

    def test_a_recorded_mask_production_never_composes_is_refused(self):
        hooks = _MaskHooks((0x0001, 0x0001))
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.login_masks_for_connection(self.legacy, 7, hooks=hooks)
        self.assertIn("not a production login mask", str(caught.exception))

    def test_a_recorded_mask_that_matches_a_branch_is_returned(self):
        hooks = _MaskHooks(PINNED_FACTION_MASKS)
        self.assertEqual(
            login_mask.login_masks_for_connection(self.legacy, 7, hooks=hooks),
            PINNED_FACTION_MASKS,
        )

    def test_a_read_point_that_raises_does_not_take_dispatch_down(self):
        hooks = _RaisingMaskHooks()
        with self.assertRaises(login_mask.LoginMaskError) as caught:
            login_mask.login_masks_for_connection(self.legacy, 7, hooks=hooks)
        self.assertIn("login_mask_read_point_raised", str(caught.exception))


class TheConsoleAndLetterTextIsAsciiTests(unittest.TestCase):
    """The bridge console is cp874; a refusal that cannot be printed is a
    refusal nobody reads."""

    def test_every_refusal_message_this_module_can_raise_is_ascii(self):
        legacy = _legacy()
        messages = []
        for call in (
            lambda: login_mask.parse_block_masks(legacy, b"\x00"),
            lambda: login_mask.field_x_for_masks(0, 1 << 31),
            lambda: login_mask.refuse_unless_login_shaped(legacy, 0, 0),
            lambda: login_mask.login_masks_for_connection(legacy, 7, hooks=_NoHooks()),
            lambda: login_mask.build_login_shaped_frame(
                legacy, 7, 1, 0, {16: 1}, hooks=_NoHooks(),
            ),
        ):
            with self.assertRaises(attr_wire.AttrWireError) as caught:
                call()
            messages.append(str(caught.exception))
        for message in messages:
            message.encode("ascii")


# -- helpers ---------------------------------------------------------------


def _values_for(legacy, rows, scene_id: int, *, faction: bool) -> dict:
    """A legal value for each row of a login-shaped set.

    The values match what the production composer puts on those rows, so the
    IDENTICAL tests above compare bytes rather than only masks.
    """
    values = {
        1: "Probe",
        2: player_wire.PLAYER_LOGIN_LEVEL,
        3: player_wire.PLAYER_LOGIN_HP_CURRENT,
        4: player_wire.PLAYER_LOGIN_HP_MAX,
        7: player_wire._login_movement_speed(None),
        9: scene_id,
        10: 0,
        11: world_faction_admission.PROVEN_BASIC_FACTION,
        13: player_wire.PLAYER_LOGIN_CLASS_ID,
        24: legacy.V116_INITIAL_CASH,
    }
    return {x: values[x] for x in rows}


def _one_value_per_row() -> dict:
    out = {}
    for x in attr_wire.all_field_x():
        kind = attr_wire.BY_X[x][5]
        if kind == "wstr":
            out[x] = "A"
        elif kind == "blob":
            out[x] = b"\x01"
        elif kind == "f32":
            out[x] = 1.0
        else:
            out[x] = 1
    return out


class _NoHooks:
    """A hooks object with none of the read points on it."""


class _Hooks:
    def __init__(self, named=None, login=None, masks=None):
        self._named = named or {}
        self._login = login or {}
        self._masks = masks

    def current_named_attr_values(self, character_id):
        return dict(self._named)

    def current_login_attr_bytes(self, character_id):
        return dict(self._login)

    def current_login_attr_masks(self, character_id):
        if self._masks is None:
            raise AssertionError("this stub was not given a login mask")
        return self._masks


class _MaskHooks:
    def __init__(self, masks):
        self._masks = masks

    def current_login_attr_masks(self, character_id):
        return self._masks


class _RaisingMaskHooks:
    def current_login_attr_masks(self, character_id):
        raise RuntimeError("boom")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
