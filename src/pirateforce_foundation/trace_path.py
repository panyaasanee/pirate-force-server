"""CTracePathReqVital (0x4391) inbound -> CTracePathVital (0x2F92) empty-vector reply only.

RE-119 (STATIC-ON-BRIDGE, PASS/DONE, 2026-08-28,
``notes_to_chief/20260828_0424_RE-119-RESULT-DISCRIMINATED-PATH-RECORDS-AND-UI-ACTIONS.md``)
proved that the client's registered ``CTracePathVital`` response handler
``[0x006EA9E0,0x006EACD3)`` treats an *empty* response (``u16`` record count
tag ``0x12`` = 0, no records following) as a clean signal: it looks up the
``Main_FindPath`` UI object and dispatches ``EndFindPath`` -- this is what
ends the "finding path..." stall the client shows after the player clicks
GO! in the map window (CTracePathReqVital / 0x4391 out, no reply ever came
back -- KA1A finding, ``20260828_0235_KA1A-FOUND-GO-button-*.md``).

A *nonempty* response (real waypoint records, auto-walk) is explicitly out
of scope here and must not be attempted: RE-119 T4 leaves the request's own
``u16@+0x14`` discriminator field (743 in the observed capture) bounded
negative between three unproven readings (a story-trigger id, an NPC id, a
list index) -- CORE-REQUEST-025 (LANE-A,
``20260828_0427_LANE-A-CORE-REQUEST-025-*.md``) scopes this module to the
empty-vector fallback only, and forbids using that field, or any guessed
record layout, to build a populated response.
"""

TRACE_PATH_REQ_VITAL_ID = 0x4391
TRACE_PATH_VITAL_ID = 0x2F92

# Unproven default. RE-119 did not need to pin this per-vital version byte
# to prove the empty-vector fallback (see module docstring); 0 matches this
# codebase's convention for reply vitals whose version byte RE has not
# separately pinned (e.g. CHIT_RESULT_VITAL_VERSION, PICKUP_LISTENER_VITAL_
# VERSION, LEARN_SKILL_REQUEST_VITAL_VERSION -- all 0).
TRACE_PATH_VITAL_VERSION = 0


def make_trace_path_empty_response(legacy):
    """Build the CTracePathVital(0x2F92) empty-vector (record count=0) reply.

    ``legacy`` is the loaded v141 module (``load_legacy`` result); this
    reuses its proven ``u16tag``/``make_runtime_vitals`` wire primitives
    rather than hand-rolling framing.
    """
    payload = legacy.u16tag(0x12, 0)
    return legacy.make_runtime_vitals(
        [(TRACE_PATH_VITAL_ID, TRACE_PATH_VITAL_VERSION, payload)],
    )
