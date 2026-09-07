"""The captain-report handshake: marker in, echo back, transport out.

Two-layer evidence, kept apart on purpose (AGENTS.md house rule): the WIRE
layer asserts bytes against ``current/pf_login_game_server_v141.py``'s own
proven helpers and its own decoder, and the RULE layer asserts the decisions
this lane makes about those bytes.  Neither is allowed to stand in for the
other -- in particular no test here calls a rule function and then asserts a
byte string this module also produced.
"""
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


class TheOutboundFrameCarriesTheMarkerIdAndNothingElse(unittest.TestCase):
    """The pin the COO order names: u16 == MARKER.n_ID."""

    def test_the_single_u16_is_the_marker_id_for_every_pinned_row(self):
        legacy = _legacy()
        seen = 0
        for marker_id in range(tc.MARKER_ID_MIN, tc.MARKER_ID_MAX + 1):
            try:
                tc.marker_destination(marker_id)
            except tc.TeleportCheckError:
                continue
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
        for marker_id in range(tc.MARKER_ID_MIN, tc.MARKER_ID_MAX + 1):
            try:
                pending = tc.open_check(marker_id)
            except tc.TeleportCheckError:
                continue
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
        for marker_id in range(tc.MARKER_ID_MIN, tc.MARKER_ID_MAX + 1):
            try:
                pending = tc.open_check(marker_id)
            except tc.TeleportCheckError:
                continue
            frames.add(tc.encode_transport(legacy, pending)[0])
        self.assertGreater(len(frames), 1)


class TheRefusals(unittest.TestCase):
    def test_a_bool_is_not_a_marker_id(self):
        """``True`` is a Python int and would resolve row 1."""
        with self.assertRaises(tc.TeleportCheckError) as caught:
            tc.marker_destination(True)
        self.assertIn(tc.CHECK_REFUSED_MARKER_ID_NOT_AN_INT, str(caught.exception))

    def test_out_of_table_ids_are_named_apart_from_unpinned_ones(self):
        for bad in (0, tc.MARKER_ID_MAX + 1, 70000):
            with self.assertRaises(tc.TeleportCheckError) as caught:
                tc.marker_destination(bad)
            self.assertIn(tc.CHECK_REFUSED_MARKER_ID_OUT_OF_TABLE,
                          str(caught.exception))

    def test_an_id_in_range_but_not_in_the_committed_copy_says_so(self):
        unpinned = [
            marker_id for marker_id in range(tc.MARKER_ID_MIN, tc.MARKER_ID_MAX + 1)
            if world_marker_copy_row(marker_id) is None
        ]
        self.assertTrue(unpinned, "the copy now pins all 390 rows; retire this test")
        with self.assertRaises(tc.TeleportCheckError) as caught:
            tc.marker_destination(unpinned[0])
        self.assertIn(tc.CHECK_REFUSED_MARKER_ROW_NOT_PINNED,
                      str(caught.exception))


def world_marker_copy_row(marker_id):
    from pirateforce_foundation import world_marker_copy
    return world_marker_copy.verbatim_marker_row(marker_id)


class TheWordingThePlayerWillSee(unittest.TestCase):
    def test_a_sea_destination_predicts_the_moving_ahead_confirm(self):
        for scene_id in tc.SEA_SCENE_IDS:
            self.assertEqual(tc.predicted_confirm_id(scene_id),
                             tc.CONFIRM_ID_MOVING_AHEAD)

    def test_every_other_destination_predicts_the_docking_confirm(self):
        self.assertEqual(tc.predicted_confirm_id(1), tc.CONFIRM_ID_DOCKING)
        self.assertEqual(tc.predicted_confirm_id(17), tc.CONFIRM_ID_DOCKING)


class TheConsoleLines(unittest.TestCase):
    def test_every_line_is_ascii(self):
        pending = tc.open_check(1)
        for line in (tc.prompt_console_line(pending),
                     tc.echo_console_line(pending, 1, None),
                     tc.echo_console_line(None, "x", tc.ECHO_REFUSED_NOTHING_PENDING),
                     tc.transport_console_line(pending, 23)):
            line.encode("ascii")
            self.assertTrue(line.startswith(tc.TOKEN))


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

    def test_the_wrong_arity_is_refused_and_counted(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"](), lua_player.STUB_DEFAULT)
        self.assertEqual(namespace["TeleportCheck"](1, 2), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.orders, [])
        self.assertEqual(len(sink.refusals), 2)

    def test_an_unusable_marker_id_is_refused_by_name_and_counted(self):
        sink = tc.InMemoryTeleportCheckSink()
        namespace = self._namespace(sink)
        self.assertEqual(namespace["TeleportCheck"]("boat"), lua_player.STUB_DEFAULT)
        self.assertEqual(namespace["TeleportCheck"](0), lua_player.STUB_DEFAULT)
        self.assertEqual(sink.orders, [])
        self.assertTrue(all(reason.startswith("CHECK_REFUSED_")
                            for reason in sink.refusals))

    def test_the_sink_default_is_fresh_and_private_per_namespace(self):
        first, second = self._namespace(), self._namespace()
        first["TeleportCheck"](1)
        self.assertEqual(first["TeleportCheck"](1), 1)
        self.assertEqual(second["TeleportCheck"](1), 1)

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
