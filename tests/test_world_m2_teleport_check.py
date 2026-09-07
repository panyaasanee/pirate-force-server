"""The captain-report handshake: marker in, echo back, transport out.

Two-layer evidence, kept apart on purpose (AGENTS.md house rule): the WIRE
layer asserts bytes against ``current/pf_login_game_server_v141.py``'s own
proven helpers and its own decoder, and the RULE layer asserts the decisions
this lane makes about those bytes.  Neither is allowed to stand in for the
other -- in particular no test here calls a rule function and then asserts a
byte string this module also produced.
"""
import ast
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pirateforce_foundation import world_m2_teleport_check as tc  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.lua_api import player as lua_player  # noqa: E402


def _legacy():
    """The v141 module, loaded through the project's own loader.

    ``legacy_bridge.load_legacy`` is what the runtime itself uses; loading the
    file by hand instead put an unregistered module in front of
    ``dataclasses``, which needs the module in ``sys.modules`` to resolve its
    own annotations -- measured here, first draft of this file.
    """
    path = (Path(__file__).resolve().parents[1]
            / "current" / "pf_login_game_server_v141.py")
    if not path.exists():  # pragma: no cover - full checkouts have it
        raise unittest.SkipTest("current/pf_login_game_server_v141.py absent")
    return load_legacy(path)


def _client_echo_pc(legacy, marker_id: int) -> bytes:
    """The frame the CLIENT sends when the player confirms.

    Built here, not by :mod:`world_m2_teleport_check`, on purpose: a test that
    asked this lane's own encoder for both halves would only prove the encoder
    agrees with itself.  The shape is v141's own -- its self-check composes
    exactly these bytes and asserts them equal to ``V136_MARKER1_CONFIRM_PC``,
    the confirm frame that route has actually seen.  It differs from the
    server's outbound frame in the carrier (Req, not Res) and in having no
    trailing derived mask, which is why the inbound decoder rejects an
    outbound frame and why this helper has to exist.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0) + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2) + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TELEPORT_CHECK_VITAL)
        + legacy.u8tag(0x0B, 0)
        + legacy.u16tag(0x0F, marker_id)
    )


class TheVitalIdAgreesWithTheServerWeShipWith(unittest.TestCase):
    def test_the_two_places_that_name_0x4477_have_not_drifted(self):
        legacy = _legacy()
        self.assertEqual(tc.TELEPORT_CHECK_VITAL_ID, 0x4477)
        self.assertEqual(tc.TELEPORT_CHECK_VITAL_ID, legacy.TELEPORT_CHECK_VITAL)

    def test_the_version_byte_is_the_one_the_decoder_accepts(self):
        legacy = _legacy()
        parsed = legacy.parse_outer(tc.encode_prompt(legacy, 1)[0])
        self.assertEqual(parsed.nested_id, tc.TELEPORT_CHECK_VITAL_ID)
        self.assertEqual(parsed.nested_version, tc.TELEPORT_CHECK_VITAL_VERSION)
        # And the same version on the way back in, through the real decoder.
        legacy.parse_teleport_check_vital(
            legacy.parse_outer(_client_echo_pc(legacy, 1)))


class TheInboundDecoderRefusesEverythingButAnEcho(unittest.TestCase):
    """What `decode_echo` refuses, MEASURED -- it was prose before.

    `decode_echo`'s docstring named checks it does not make itself: the vital
    class and the nested version are v141's parser's, and the RuntimeRes v4
    carrier with its trailing derived mask is `parse_outer`'s, upstream of the
    object this is handed.  Inheriting them is correct (RE-292 forbids this
    lane from putting a decoder of its own in that path) but nothing pinned
    that the inheritance actually holds (pf-adversary, `ebh143`, D7).
    """

    def test_a_real_client_echo_decodes_to_its_marker_id(self):
        legacy = _legacy()
        for marker_id in (1, 17):
            self.assertEqual(
                tc.decode_echo(legacy,
                               legacy.parse_outer(_client_echo_pc(legacy, marker_id))),
                marker_id)

    def test_this_servers_own_outbound_prompt_is_not_an_echo(self):
        # The frame this server SENDS differs in carrier (Res, not Req) and in
        # carrying the derived change mask.  If it decoded, a reflected or
        # replayed outbound frame would consume the order it announced.
        legacy = _legacy()
        pc, _frame = tc.encode_prompt(legacy, 1)
        self.assertIsNone(tc.decode_echo(legacy, legacy.parse_outer(pc)))

    def test_another_vital_class_in_the_same_carrier_is_not_an_echo(self):
        legacy = _legacy()
        other = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0) + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2) + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TELEPORT_CHECK_VITAL + 1)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x0F, 17)
        )
        self.assertIsNone(tc.decode_echo(legacy, legacy.parse_outer(other)))

    def test_a_wrong_nested_version_is_not_an_echo(self):
        legacy = _legacy()
        wrong_version = (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0) + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2) + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TELEPORT_CHECK_VITAL)
            + legacy.u8tag(0x0B, tc.TELEPORT_CHECK_VITAL_VERSION + 1)
            + legacy.u16tag(0x0F, 17)
        )
        self.assertIsNone(tc.decode_echo(legacy, legacy.parse_outer(wrong_version)))


class TheWireArgumentIsCoercedWithoutThisDoorsBound(unittest.TestCase):
    """`coerce_wire_marker_id` answers "is this a number", nothing else."""

    def test_a_number_is_returned_unclamped_in_every_shape_lua_hands_over(self):
        for value, expected in ((1, 1), (1.0, 1), (0, 0), (-1, -1),
                                (70000, 70000), (10 ** 30, 10 ** 30)):
            self.assertEqual(tc.coerce_wire_marker_id(value), expected)
            self.assertIs(type(tc.coerce_wire_marker_id(value)), int)

    def test_everything_that_is_not_a_number_is_none(self):
        for value in (True, False, "17", None, 1.5, float("nan"),
                      float("inf"), float("-inf"), b"17", [17], object()):
            self.assertIsNone(tc.coerce_wire_marker_id(value), repr(value))

    def test_an_int_subclass_arrives_as_a_plain_int(self):
        # `_coerce_marker_id` downstream is a `type(x) is int` check, so an
        # IntEnum or a bool-like subclass that reached it unnormalised would
        # be refused as "not an int" while being one.
        class MarkerLike(int):
            pass

        self.assertEqual(tc.coerce_wire_marker_id(MarkerLike(17)), 17)
        self.assertIs(type(tc.coerce_wire_marker_id(MarkerLike(17))), int)

    def test_it_never_raises_for_anything_the_door_can_be_handed(self):
        class Hostile:
            def __int__(self):
                raise RuntimeError("no")

            def __index__(self):
                raise RuntimeError("no")

            def __eq__(self, other):
                raise RuntimeError("no")

        # A raise here would leave the Lua closure, where the traceback names
        # the script rather than the caller that passed the wrong object.
        self.assertIsNone(tc.coerce_wire_marker_id(Hostile()))


class TheOutboundFrameCarriesTheMarkerIdAndNothingElse(unittest.TestCase):
    """The pin the COO order names: u16 == MARKER.n_ID."""

    def test_the_single_u16_is_the_marker_id_for_every_pinned_row(self):
        legacy = _legacy()
        seen = 0
        for marker_id in _pinned_marker_ids():
            tc.marker_destination(marker_id)
            seen += 1
            pc, _frame = tc.encode_prompt(legacy, marker_id)
            parsed = legacy.parse_outer(pc)
            self.assertEqual(parsed.nested_id, tc.TELEPORT_CHECK_VITAL_ID)
            # The body is the tagged u16 and nothing else; the trailing bytes
            # after it are RuntimeRes v4's derived change mask, which
            # `make_runtime_vitals` owns and this lane does not touch.
            self.assertTrue(parsed.nested_payload.startswith(
                legacy.u16tag(tc.TELEPORT_CHECK_FIELD_TAG, marker_id)))
        self.assertGreater(seen, 1, "the committed copy pinned no rows at all")

    def test_marker_one_reproduces_the_frame_v141_already_sends(self):
        """The generalisation must not have changed the proven bytes."""
        legacy = _legacy()
        self.assertEqual(
            tc.encode_prompt(legacy, 1)[0],
            legacy.make_teleport_check_scene1_challenge()[0],
        )

    def test_the_inbound_echo_body_is_three_bytes_and_stops(self):
        legacy = _legacy()
        decoded = legacy.parse_teleport_check_vital(
            legacy.parse_outer(_client_echo_pc(legacy, 1)))
        self.assertEqual(decoded["trailing_bytes"], 0)
        self.assertEqual(decoded["field_u16_14"], 1)


class TheEchoIsWhatTurnsIntoATransport(unittest.TestCase):
    def test_a_matching_echo_is_accepted_and_answers_with_that_markers_scene(self):
        legacy = _legacy()
        pending = tc.open_check(1)
        # OK echoes the same class with the same value (RE-303 s.5).
        echoed = tc.decode_echo(
            legacy, legacy.parse_outer(_client_echo_pc(legacy, 1)))
        self.assertIsNone(tc.accept_echo(pending, echoed))
        pc, _frame = tc.encode_transport(legacy, pending)
        self.assertEqual(pc, legacy.make_v137_marker1_transport_probe()[0])

    def test_the_echo_gate_does_not_read_whether_a_window_was_shown(self):
        """RE-303 s.6.1: the client can answer with no window at all.

        A gate that also required "we think a window is open" would teleport
        on some approaches and hang on others.  Same pending, both values of
        the prediction, one verdict.
        """
        with_window = tc.open_check(1)
        without_window = with_window._replace(window_expected=False)
        self.assertIsNone(tc.accept_echo(with_window, 1))
        self.assertIsNone(tc.accept_echo(without_window, 1))

    def test_a_different_marker_id_is_refused_by_name(self):
        pending = tc.open_check(1)
        self.assertEqual(tc.accept_echo(pending, 2),
                         tc.ECHO_REFUSED_MARKER_ID_MISMATCH)

    def test_an_echo_with_nothing_pending_is_refused_by_name(self):
        self.assertEqual(tc.accept_echo(None, 1), tc.ECHO_REFUSED_NOTHING_PENDING)

    def test_an_undecodable_echo_is_refused_and_never_raises(self):
        pending = tc.open_check(1)
        for bad in (None, "1", 1.0, True):
            self.assertEqual(tc.accept_echo(pending, bad),
                             tc.ECHO_REFUSED_UNDECODABLE)

    def test_decode_echo_returns_none_for_a_frame_of_another_class(self):
        legacy = _legacy()
        other, _f = legacy.make_v137_marker1_transport_probe()
        self.assertIsNone(tc.decode_echo(legacy, legacy.parse_outer(other)))


class TheTransportGoesWhereTheMarkerRowSaysAndNowhereElse(unittest.TestCase):
    def test_every_pinned_row_encodes_its_own_scene_and_point(self):
        legacy = _legacy()
        rows = 0
        for marker_id in _pinned_marker_ids():
            pending = tc.open_check(marker_id)
            rows += 1
            pc, _frame = tc.encode_transport(legacy, pending)
            d = pending.destination
            expected_target = legacy.make_teleport_target(
                d.scene_id, legacy.V137_MARKER_SCENE_SEQ,
                float(d.x), float(d.y), float(d.z))
            self.assertIn(expected_target, pc)
        self.assertGreater(rows, 1)

    def test_two_different_markers_do_not_produce_the_same_transport(self):
        """A copy/paste that dropped the destination would pass every
        single-row assertion above and fail this one."""
        legacy = _legacy()
        frames = set()
        for marker_id in _pinned_marker_ids():
            frames.add(tc.encode_transport(legacy, tc.open_check(marker_id))[0])
        self.assertGreater(len(frames), 1)


class TheRefusals(unittest.TestCase):
    def test_a_bool_is_not_a_marker_id(self):
        """``True`` is a Python int and would resolve row 1."""
        with self.assertRaises(tc.TeleportCheckError) as caught:
            tc.marker_destination(True)
        self.assertIn(tc.CHECK_REFUSED_MARKER_ID_NOT_AN_INT, str(caught.exception))

    def test_ids_the_u16_field_cannot_carry_are_named_apart(self):
        for bad in (0, -1, tc.MARKER_ID_MAX + 1, 70000):
            with self.assertRaises(tc.TeleportCheckError) as caught:
                tc.marker_destination(bad)
            self.assertIn(tc.CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD,
                          str(caught.exception))

    def test_an_id_the_field_can_carry_but_the_table_does_not_know_says_so(self):
        known = set(_pinned_marker_ids())
        unpinned = next(m for m in range(tc.MARKER_ID_MIN, tc.MARKER_ID_MAX + 1)
                        if m not in known)
        with self.assertRaises(tc.TeleportCheckError) as caught:
            tc.marker_destination(unpinned)
        self.assertIn(tc.CHECK_REFUSED_MARKER_ROW_NOT_PINNED,
                      str(caught.exception))

    def test_this_module_does_not_import_the_release_less_copy_reader(self):
        """``tests/test_world_marker_copy.py`` pins this for the whole
        package; pinned again here because THIS module is the one that wanted
        those 18 rows and would be the one to reach for them again."""
        source = (Path(__file__).resolve().parents[1] / "src"
                  / "pirateforce_foundation" / "world_m2_teleport_check.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [getattr(node, "module", "") or ""] + [
                    alias.name for alias in node.names]
                self.assertFalse(
                    any(name.endswith("world_marker_copy") for name in names))


def _pinned_marker_ids():
    from pirateforce_foundation import world_scene_marker
    return [world_scene_marker.arrival_point(scene).marker_n_id
            for scene in world_scene_marker.scenes_with_an_arrival_point()]


class TheWordingThePlayerWillSee(unittest.TestCase):
    """Every number here is compared with a LITERAL, not with itself.

    pf-adversary, round `w4cp5c`: `CONFIRM_ID_DOCKING` and
    `CONFIRM_ID_MOVING_AHEAD` were only ever compared against the constants
    they name, so RE-303's two measured `UI_CONFIRM` rows were pinned nowhere
    and `SEA_SCENE_IDS = ()` left the sea test green by iterating an empty
    tuple.  A literal on the right-hand side is what makes those mutants die.
    """

    def test_the_two_confirm_rows_are_the_numbers_re303_measured(self):
        self.assertEqual(tc.CONFIRM_ID_MOVING_AHEAD, 21)
        self.assertEqual(tc.CONFIRM_ID_DOCKING, 22)

    def test_the_sea_is_exactly_the_five_type_8_scenes_re303_counted(self):
        self.assertEqual(tc.SEA_SCENE_IDS, (126, 127, 128, 304, 305))

    def test_a_sea_destination_predicts_the_moving_ahead_confirm(self):
        for scene_id in (126, 127, 128, 304, 305):
            with self.subTest(scene=scene_id):
                self.assertEqual(tc.predicted_confirm_id(scene_id), 21)

    def test_every_other_destination_predicts_the_docking_confirm(self):
        self.assertEqual(tc.predicted_confirm_id(1), 22)
        self.assertEqual(tc.predicted_confirm_id(17), 22)

    def test_the_moving_ahead_half_is_reachable_from_a_real_marker_row(self):
        # The half RE-303 exists for, and until this round it was unreachable
        # code: no marker id this server could build a prompt for landed in a
        # sea scene, so `predicted_confirm_id` could never answer 21 for a
        # real destination and no test noticed (pf-adversary, round `w4cp5c`).
        reached = {}
        for marker_id in sorted(tc._by_marker_id()):
            destination = tc.marker_destination(marker_id)
            if tc.predicted_confirm_id(destination.scene_id) == 21:
                reached[marker_id] = destination.scene_id
        self.assertEqual(reached, {17: 126, 343: 304, 345: 305})

    def test_a_decreed_row_that_disagrees_with_its_own_accessor_raises(self):
        # The `pragma: no cover` branches in _by_marker_id() are refusals, not
        # decoration, and this is the test they point at: drive them by giving
        # the module a decree table world_scene_marker does not back.
        import unittest.mock as mock
        with mock.patch.object(tc.world_scene_marker, "decreed_arrival_row",
                               lambda scene, marker: None):
            with self.assertRaises(tc.TeleportCheckError) as raised:
                tc._by_marker_id()
        self.assertIn(tc.CHECK_REFUSED_MARKER_ROW_NOT_PINNED,
                      str(raised.exception))

    def test_a_decreed_row_may_not_shadow_a_named_arrival_row(self):
        import unittest.mock as mock
        named = tc.world_scene_marker.arrival_point(1)
        with mock.patch.object(
                tc.world_scene_marker, "DECREED_ARRIVAL_ROWS",
                ((named.marker_n_id, 126, 1, 2, 3, 4),)):
            with mock.patch.object(tc.world_scene_marker,
                                   "decreed_arrival_row",
                                   lambda scene, marker: (1, 2, 3, 4)):
                with self.assertRaises(tc.TeleportCheckError) as raised:
                    tc._by_marker_id()
        self.assertIn("both a named and a decreed", str(raised.exception))

    def test_a_marker_id_that_is_also_a_scene_id_resolves_as_a_marker(self):
        # 17 is both a marker id (scene 126's decreed arrival row) and a real
        # scene id.  `world_scene_marker.decreed_arrival_row` takes both ids
        # so this can never be confused; pin the answer this module gives.
        self.assertEqual(tc.marker_destination(17).scene_id, 126)


class TheConsoleLines(unittest.TestCase):
    def test_every_line_is_ascii(self):
        pending = tc.open_check(1)
        for line in (tc.prompt_console_line(pending),
                     tc.echo_console_line(pending, 1, None),
                     tc.echo_console_line(None, "x", tc.ECHO_REFUSED_NOTHING_PENDING),
                     tc.transport_console_line(pending, 23)):
            line.encode("ascii")
            self.assertTrue(line.startswith("LANE_A_M2_TELEPORT_CHECK"))

    def test_the_console_token_is_the_string_the_bridge_greps_for(self):
        # Compared with the literal, not with itself: the token is what an
        # attended ticket's HEADLESS_PROOF line will be grepped for, so it is
        # an interface, not an implementation detail (pf-adversary, `w4cp5c`).
        self.assertEqual(tc.TOKEN, "LANE_A_M2_TELEPORT_CHECK")


class TheLuaNameIsRealNow(unittest.TestCase):
    def test_teleport_check_is_no_longer_a_stub(self):
        self.assertIn("TeleportCheck", lua_player.REAL_METHODS)
        self.assertNotIn("TeleportCheck", lua_player.STILL_STUBBED)

    def _namespace(self, sink=None):
        self.logged = []
        return lua_player.build_namespace(
            frozenset(lua_player.REAL_METHODS) | set(lua_player.STILL_STUBBED),
            self.logged.append, teleport_check_sink=sink)

    def test_a_good_call_records_one_order_for_this_character(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"](1), 1)
        self.assertEqual(len(sink.orders), 1)
        self.assertEqual(sink.orders[0].pending.marker_id, 1)
        self.assertTrue(any("Player.TeleportCheck" in line for line in self.logged))

    def test_the_wrong_arity_is_refused_under_its_own_name(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"](), lua_player.STUB_DEFAULT)
        self.assertEqual(namespace["TeleportCheck"](1, 2), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.orders, [])
        # BY NAME, not by count.  Counting two refusals passed while both of
        # them were spelled CHECK_REFUSED_MARKER_ID_NOT_AN_INT, which sends
        # the reader of a run's tally to look for a bad marker id in a script
        # that passed the wrong NUMBER of arguments (pf-adversary, `ebh143`,
        # D6).
        self.assertEqual(sink.refusals, [
            tc.CHECK_REFUSED_BAD_ARITY,
            tc.CHECK_REFUSED_BAD_ARITY,
        ])

    def test_an_unusable_marker_id_is_refused_by_name_and_counted(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"]("boat"), lua_player.STUB_DEFAULT)
        self.assertEqual(namespace["TeleportCheck"](0), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.orders, [])
        # The reasons BY NAME, in order.  The previous shape was
        # `all(... for reason in sink.refusals)`, which is True over an empty
        # list -- a test that passes when nothing is counted at all is not a
        # test that the refusals are counted (pf-adversary, round `w4cp5c`).
        self.assertEqual(sink.refusals, [
            tc.CHECK_REFUSED_MARKER_ID_NOT_AN_INT,
            tc.CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD,
        ])

    def test_marker_id_zero_is_the_tables_no_marker_sentinel_not_a_row(self):
        # The u16 field carries 0; the client's own SCENE_NAME rows spell
        # "this scene names no marker" with it.  Refusing it by that name is
        # what makes the mistake visible instead of resolving row 0.
        with self.assertRaises(tc.TeleportCheckError) as raised:
            tc.marker_destination(0)
        self.assertTrue(str(raised.exception).startswith(
            tc.CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD))

    def test_an_echo_consumes_one_order_and_only_the_right_one(self):
        sink = tc.InMemoryTeleportCheckSink()
        sink.record(7, tc.open_check(1))
        sink.record(9, tc.open_check(2))
        sink.record(7, tc.open_check(2))
        taken = sink.take(7, 2)
        self.assertIsNotNone(taken)
        self.assertEqual(taken.character_id, 7)
        self.assertEqual(taken.pending.marker_id, 2)
        # The replay: the same echo a second time takes nothing, and says so.
        self.assertIsNone(sink.take(7, 2))
        self.assertIn(tc.ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER, sink.refusals)
        # The other player's order is untouched by either call.
        self.assertEqual([(o.character_id, o.pending.marker_id)
                          for o in sink.orders], [(7, 1), (9, 2)])

    def test_an_echo_never_consumes_another_players_order(self):
        sink = tc.InMemoryTeleportCheckSink()
        sink.record(9, tc.open_check(2))
        self.assertIsNone(sink.take(7, 2))
        self.assertEqual(len(sink.orders), 1)

    def test_the_newest_order_for_a_repeated_marker_is_the_one_consumed(self):
        sink = tc.InMemoryTeleportCheckSink()
        first, second = tc.open_check(3), tc.open_check(3)
        sink.record(7, first)
        sink.record(7, second)
        self.assertIs(sink.take(7, 3).pending, second)

    def test_a_sink_without_the_recorder_methods_is_refused_at_build_time(self):
        class Broken:
            def record_refusal(self, reason):
                pass

        with self.assertRaises(TypeError):
            self._namespace(Broken())

    def test_the_sink_default_is_fresh_and_private_per_namespace(self):
        # THIS COMPARES THE CONTENTS OF THE TWO SINKS, not two return values.
        # The old shape called TeleportCheck three times and asserted each
        # returned 1, which is true whether the default is private or a
        # process-wide singleton -- pf-adversary swapped in a module-level
        # shared sink and the whole file stayed green (round `ebh143`, D3).
        # A singleton is exactly what the sink's own docstring says it must
        # never be: ORDER_CAP would become a 64-order ceiling for the entire
        # process, after which every player's TeleportCheck returns 0 forever.
        first, second = self._namespace(), self._namespace()
        for _ in range(3):
            self.assertEqual(first["TeleportCheck"](1), 1)
        self.assertEqual(second["TeleportCheck"](1), 1)
        # The default sink has no accessor (D2 in the same report says so),
        # so the private name is what a test has to read until one exists.
        first_sink = first._teleport_check_sink
        second_sink = second._teleport_check_sink
        self.assertIsNot(first_sink, second_sink)
        self.assertEqual(len(first_sink.orders), 3)
        self.assertEqual(len(second_sink.orders), 1)

    def test_an_out_of_field_marker_id_is_refused_under_its_own_name(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        # 70000 does not fit the u16 the wire carries and -1 is not a marker
        # id at all; both are CALLER bugs in a script, and the fix for them is
        # not the fix for a row this repository has not transcribed.  Before
        # this round the door range-checked first and handed `open_check` a
        # None, so every one of these arrived as "not an int" and
        # CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD -- a name this module ships and
        # documents -- could not be produced by any live call at all
        # (pf-adversary, `ebh143`, D6).
        for value in (70000, -1, 0x1_0000, 10 ** 30):
            self.assertEqual(
                namespace["TeleportCheck"](value), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.orders, [])
        self.assertEqual(sink.refusals,
                         [tc.CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD] * 4)

    def test_a_lua_float_still_reaches_the_row_it_names(self):
        # lupa hands every Lua number across as a float, so the door has to
        # accept an exact-integer float -- and only an exact-integer float.
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"](1.0), 1)
        self.assertEqual(sink.orders[0].pending.marker_id, 1)
        self.assertEqual(
            namespace["TeleportCheck"](1.5), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.refusals, [tc.CHECK_REFUSED_MARKER_ID_NOT_AN_INT])

    def test_the_console_prompt_line_is_printed_by_the_live_door(self):
        # The token exists to be grepped out of a real boot's console
        # (HEADLESS_PROOF).  Until this round nothing outside tests/ called
        # the composer, so the token could not be fired at all and the proof
        # could not be measured (pf-adversary, `ebh143`, D9).
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"](1), 1)
        prompts = [line for line in self.logged
                   if line.startswith(tc.TOKEN + " PROMPT")]
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0],
                         tc.prompt_console_line(sink.orders[0].pending))
        # The bridge console is cp874: a non-ASCII byte here kills the tool
        # that reads the proof, not just the line.
        prompts[0].encode("ascii")

    def test_no_prompt_line_is_printed_for_an_order_the_sink_refused(self):
        # stored=0 is a refusal at the cap.  A PROMPT line for it would name a
        # window no player is ever asked about, in the exact console a reader
        # is told to trust as evidence that the mechanism is armed.
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        for _ in range(tc.ORDER_CAP):
            namespace["TeleportCheck"](1)
        printed_before = len([line for line in self.logged
                              if line.startswith(tc.TOKEN + " PROMPT")])
        self.assertEqual(namespace["TeleportCheck"](1), 0)
        printed_after = len([line for line in self.logged
                             if line.startswith(tc.TOKEN + " PROMPT")])
        self.assertEqual(printed_before, tc.ORDER_CAP)
        self.assertEqual(printed_after, printed_before)

    def test_the_sink_is_readable_by_name_from_outside_the_namespace(self):
        # D2: while the recorder lived only in a private attribute, every
        # order Player.TeleportCheck accepted was unreachable from the code
        # that would have to turn it into a frame -- the module's own claim
        # that "one plug point remains" was false while that was true.
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertIs(namespace.teleport_check_sink, sink)
        default_namespace = self._namespace()
        self.assertIs(default_namespace.teleport_check_sink,
                      default_namespace._teleport_check_sink)
        self.assertIsNot(default_namespace.teleport_check_sink,
                         self._namespace().teleport_check_sink)

    def test_the_recorder_stops_at_its_cap_instead_of_growing_forever(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        for _ in range(tc.ORDER_CAP):
            self.assertEqual(namespace["TeleportCheck"](1), 1)
        self.assertEqual(namespace["TeleportCheck"](1), 0)
        self.assertEqual(len(sink.orders), tc.ORDER_CAP)
        self.assertIn(tc.ORDER_REFUSED_AT_CAP, sink.refusals)


if __name__ == "__main__":
    unittest.main()
