"""LANE-GM tools: server-side GM allowlist, GM state wire, and GM command scaffolding.

Everything under this package exists to shorten how long a human tester
waits to reach a test-ready state (warp, toggle an event NPC, grant an item,
spawn a mob) -- not to prove that any of those systems work.  A GM action is
never cited as evidence that the underlying gameplay path is correct; see
docs/GM_LANE.md for the nonclaim rule this package's tests must follow.
"""
