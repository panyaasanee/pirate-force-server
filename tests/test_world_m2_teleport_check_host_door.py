"""LANE-A M2: the travel order has a door out of the Lua namespace.

`Player.TeleportCheck` records an order; it builds no frame and sends nothing
(lua_api/message.py's rule, kept for this name too).  Something OUTSIDE the
sandbox has to be able to pick that order up, or the recorded window is a
window no player is ever asked about -- pf-adversary measured exactly that in
round `ebh143` (D2): the sink lived in an attribute of the namespace object
and `ScriptHost` neither took one nor exposed one, so the module's claim that
"one plug point remains" was false while nothing could reach the orders at all.

Guarded by LUPA_PACKAGE only: a live `ScriptHost` is the subject here (the
namespace-level behaviour is pinned without Lua in
tests/test_world_m2_teleport_check.py), and this module reads no sibling
checkout.
"""
import unittest

from pf_preconditions import LUPA_PACKAGE

from pirateforce_foundation import script_host
from pirateforce_foundation import world_m2_teleport_check as tc
from pirateforce_foundation.lua_api import player as lua_player


PINNED_MARKER_ID = 1


def _host(log=None, **kwargs):
    return script_host.ScriptHost(log=log or (lambda _m: None), **kwargs)


@LUPA_PACKAGE.skip_unless_present()
class TheHostHandsTheTravelOrderOutTests(unittest.TestCase):
    def test_a_script_calling_teleport_check_lands_in_the_hosts_own_sink(self):
        # The whole point: the order is readable from the object the caller
        # that dispatches frames already holds, without reaching into the
        # namespace or naming a private attribute.
        host = _host()
        host.load("function Go() Player.TeleportCheck(%d) end" % PINNED_MARKER_ID)
        host.call("Go")
        sink = host.teleport_check_sink
        self.assertIsNotNone(sink)
        self.assertEqual(len(sink.orders), 1)
        self.assertEqual(sink.orders[0].pending.marker_id, PINNED_MARKER_ID)

    def test_the_sink_the_caller_supplied_is_the_one_that_is_written_to(self):
        supplied = tc.InMemoryTeleportCheckSink()
        host = _host(teleport_check_sink=supplied)
        self.assertIs(host.teleport_check_sink, supplied)
        host.load("function Go() Player.TeleportCheck(%d) end" % PINNED_MARKER_ID)
        host.call("Go")
        self.assertEqual(len(supplied.orders), 1)

    def test_two_hosts_never_share_one_sink(self):
        # A process-wide recorder would make ORDER_CAP a ceiling for the whole
        # server: after 64 orders every player's TeleportCheck returns 0
        # forever, and one player's echo could consume another's order.
        first, second = _host(), _host()
        self.assertIsNot(first.teleport_check_sink, second.teleport_check_sink)
        source = "function Go() Player.TeleportCheck(%d) end" % PINNED_MARKER_ID
        first.load(source)
        first.call("Go")
        first.call("Go")
        second.load(source)
        second.call("Go")
        self.assertEqual(len(first.teleport_check_sink.orders), 2)
        self.assertEqual(len(second.teleport_check_sink.orders), 1)

    def test_the_door_is_the_same_object_the_namespace_records_into(self):
        # Two ways to the same recorder must not be two recorders: an order
        # written through one and read through the other is the whole
        # mechanism.
        host = _host()
        namespace = host.namespaces["Player"]
        self.assertIs(host.teleport_check_sink, namespace.teleport_check_sink)
        self.assertIs(host.teleport_check_sink, namespace._teleport_check_sink)

    def test_a_load_script_file_host_carries_the_sink_through_too(self):
        import tempfile
        from pathlib import Path

        supplied = tc.InMemoryTeleportCheckSink()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "travel.lua"
            path.write_text(
                "function Go() Player.TeleportCheck(%d) end" % PINNED_MARKER_ID)
            host = script_host.load_script_file(
                path, log=lambda _m: None, teleport_check_sink=supplied)
            host.call("Go")
        self.assertIs(host.teleport_check_sink, supplied)
        self.assertEqual(len(supplied.orders), 1)

    def test_the_console_token_reaches_a_real_hosts_log(self):
        # What a HEADLESS_PROOF line is measured from: a boot, a script call,
        # and one greppable ASCII line on the console.  Before this round the
        # composer had no caller outside tests/ (pf-adversary, `ebh143`, D9).
        lines = []
        host = _host(log=lines.append)
        host.load("function Go() Player.TeleportCheck(%d) end" % PINNED_MARKER_ID)
        host.call("Go")
        prompts = [line for line in lines
                   if line.startswith(tc.TOKEN + " PROMPT")]
        self.assertEqual(len(prompts), 1)
        self.assertIn("marker=%d" % PINNED_MARKER_ID, prompts[0])
        prompts[0].encode("ascii")

    def test_a_script_passing_a_bad_id_is_refused_by_name_not_by_a_raise(self):
        # A raise out of a Lua closure names the script, not the caller that
        # wrote the wrong number; and the tally has to say WHICH mistake.
        host = _host()
        host.load(
            "function Bad() return Player.TeleportCheck(70000) end\n"
            "function Arity() return Player.TeleportCheck() end\n"
            "function Word() return Player.TeleportCheck('boat') end")
        self.assertEqual(host.call("Bad"), lua_player.STUB_DEFAULT)
        self.assertEqual(host.call("Arity"), lua_player.STUB_DEFAULT)
        self.assertEqual(host.call("Word"), lua_player.STUB_DEFAULT)
        self.assertEqual(host.teleport_check_sink.orders, [])
        self.assertEqual(host.teleport_check_sink.refusals, [
            tc.CHECK_REFUSED_MARKER_ID_OUT_OF_FIELD,
            tc.CHECK_REFUSED_BAD_ARITY,
            tc.CHECK_REFUSED_MARKER_ID_NOT_AN_INT,
        ])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
