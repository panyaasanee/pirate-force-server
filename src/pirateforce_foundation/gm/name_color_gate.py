"""Refuse P-2 monster-name-colour wiring until its measured precondition holds.

THIS MODULE WRITES NO COLOUR, HOLDS NO RGB VALUE, AND SENDS NO BYTE.
It is a read-only predicate.  Its whole job is to make one already-measured
bounded negative *executable*, so that a later round cannot wire the P-2
colour rule on a premise the client image has already refuted, and so that
the refusal names its own evidence instead of being prose in a letter that
nobody re-reads.

Where the two halves of the evidence come from
----------------------------------------------
1. ``RE-191`` (DONE/PASS, Codex static RE, bridge letter
   ``notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md``,
   consumed by LANE-GM round ``r2jfjm``) closed the *palette* question --
   which RGBA each FontStyleID resolves to.  Those numbers are DELIBERATELY
   NOT COPIED HERE: that ticket's own "ข้อห้าม" section forbids writing any
   monster-colour code from it, and a constant table in this package would
   be exactly the hardcoded palette its last paragraph tells implementers
   not to build ("อย่า hardcode สีหรือส่ง style ID ตรง ๆ").  Read the
   letter when a human needs the numbers.
2. ``RE-195`` (DONE/BOUNDED-NEGATIVE, bridge letter
   ``notes_to_chief/20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md``,
   opened for this lane by chief out of ``CORE-REQUEST-GM-048``) closed the
   *reachability* question, and its answer is negative: with the identity
   scheme this server ships today, the branch that would render the
   "fighting" style is never entered, so binding a colour rule to faction,
   to a template flag, or to emitting a hit would produce a rule that can
   never fire and that no screen test could distinguish from a bug.

What RE-195 measured, in the only form this module encodes
----------------------------------------------------------
The client's canonical selector span ``[0x00443F50,0x004443C5)``
(``span_sha256`` below) splits on the SIGN of the actor identity dword
before it can reach the typed ``CNetNPC`` tail that owns style 61:

    signed-nonpositive identity  ->  style 60 / the typed CNetNPC 61 tail
    positive identity            ->  the 56 / 58 / 59 family, and the
                                     typed 61 tail is bypassed entirely

``field_mobs.FieldMob.actor_identity`` composes ``0x2000 + placement_index
+ 1``.  Every value it can produce is positive, so every mob this server
ships today lands in the family that cannot reach style 61.  RE-195 checked
the two escape routes a lane might reach for and closed both: the faction
comparator ``0x004A1D50`` is called from ONE site (``0x0043C5E0``) and only
as a *fallback* inside the relationship predicate -- earlier exits bypass it
-- and ``CHitResult``'s ``+0x70 & 0x100`` writers require a signed-NEGATIVE
target identity, which the current positive identities fail before the bit
can ever be set.

What this module does NOT claim
-------------------------------
* It does not say what colour any style is.  See RE-191's letter.
* It does not classify styles 62 / 63.  RE-195's matrix covers 56..61 only;
  RE-191 places 63 on a ``CNetNPC`` vslot ``+0x3C`` lane inside a pinned
  scope.  Whether the identity-sign gate sits upstream of 62/63 the same way
  it sits upstream of 61 is NOT measured, so this module answers UNKNOWN for
  them rather than guessing -- and the verdict stays blocked either way.
* It does not claim any style reaches a rendered pixel.  Controller
  allocation, lookup, local vslots and delivery order are all client-side
  gates RE-191 lists and neither ticket walked.
* It is not a GM feature.  Nothing here grants, checks, or implies GM
  status, and no account changes state because of it.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Provenance.  Every constant below is a citation, not a tuning knob.
# ---------------------------------------------------------------------------

#: The client image both tickets were re-derived against (RE-195 rehashed it
#: before and after its analysis and it did not change).
CLIENT_IMAGE_SHA256 = (
    "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"
)
CLIENT_IMAGE_BYTES = 14_759_424

#: The canonical FontStyleID selector span RE-195 joined its matrix to.
SELECTOR_SPAN = (0x00443F50, 0x004443C5)
SELECTOR_SPAN_SHA256 = (
    "ee845ee6ef6337ea41ae57a5a4df8af5a8a8ac00e458ea1ce3e587aff1f9cdf9"
)

#: The relationship predicate, and the faction comparator it calls at ONE
#: conditional fallback site.  RE-195's whole-image E8 census found exactly
#: one direct caller of the comparator.
RELATIONSHIP_PREDICATE_SPAN = (0x0043C380, 0x0043C63C)
FACTION_COMPARATOR_VA = 0x004A1D50
FACTION_COMPARATOR_SOLE_CALL_SITE_VA = 0x0043C5E0

#: ``src/pirateforce_foundation/field_mobs.py`` as RE-195 measured it.  The
#: test that pins this lane's conclusion recomputes the file's hash and, when
#: it differs, tells the reader to re-derive rather than silently trusting a
#: bounded negative measured against a different file.
FIELD_MOBS_SHA256_AT_RE195 = (
    "a4fc6eaee6351d10e7bb44abb527db51966f217d474318a92078811bb79bb865"
)

RE_191_RESULT_LETTER = (
    "notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md"
)
RE_195_RESULT_LETTER = (
    "notes_to_chief/"
    "20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md"
)

# ---------------------------------------------------------------------------
# Identity lanes.  Opaque names on purpose: these are the two sides of a sign
# test in the client's selector, NOT gameplay nouns.  Nothing here is called
# "hostile", "fighting", "dead", or a colour.
# ---------------------------------------------------------------------------

IDENTITY_LANE_POSITIVE = "positive_identity"
IDENTITY_LANE_SIGNED_NONPOSITIVE = "signed_nonpositive_identity"

#: Which lane the typed ``CNetNPC`` tail that owns style 61 sits behind.
TYPED_STYLE61_TAIL_REQUIRES_LANE = IDENTITY_LANE_SIGNED_NONPOSITIVE

#: Styles RE-195's matrix actually covers.  62 and 63 are absent on purpose.
STYLES_COVERED_BY_RE195 = (56, 58, 59, 60, 61)

_INT32_MIN = -(2 ** 31)
_INT32_MAX = 2 ** 31 - 1


class NameColorGateError(ValueError):
    """An input does not have the shape this module requires.

    Same "regardless of source" posture the rest of this package takes (see
    ``gm/commands.py::GmCommandArgsError``): a caller that hands this module
    a ``bool``, a float that happens to compare, or an out-of-range value
    gets a module-specific error, never a quiet answer.  A gate that answers
    quietly on junk is worse than no gate, because the answer it gives on
    junk is the permissive one people remember.
    """


def _require_identity_dword(value: object, label: str) -> int:
    # bool is an int subclass, and ``True`` would otherwise classify as the
    # positive lane and read like a deliberate answer.
    if isinstance(value, bool) or type(value) is not int:
        raise NameColorGateError(
            f"{label} must be a plain int actor identity, got {type(value).__name__}"
        )
    if not (_INT32_MIN <= value <= _INT32_MAX):
        raise NameColorGateError(
            f"{label} does not fit the signed dword the selector tests: {value}"
        )
    return value


def identity_lane(identity: int) -> str:
    """Name the side of the selector's sign test this identity lands on.

    This is the ONE fact RE-195 measured that a server-side caller can act
    on, and it is deliberately a classification, not a permission.
    """
    value = _require_identity_dword(identity, "identity")
    if value <= 0:
        return IDENTITY_LANE_SIGNED_NONPOSITIVE
    return IDENTITY_LANE_POSITIVE


def typed_style61_tail_reachable(identity: int) -> bool:
    """Can the typed ``CNetNPC`` style-61 tail be entered for this identity?

    False for every identity ``field_mobs`` composes today.  This answers
    reachability of a client BRANCH, never whether a colour is drawn.
    """
    return identity_lane(identity) == TYPED_STYLE61_TAIL_REQUIRES_LANE


def style_lane_is_measured(style_id: int) -> bool:
    """Did RE-195's matrix cover this style id at all?

    62 and 63 return False: RE-191 placed them on a different, separately
    pinned lane and nobody has measured whether the identity-sign gate sits
    upstream of them.  A caller that wants to reason about them must open a
    ticket, not read an answer out of this module.
    """
    if isinstance(style_id, bool) or type(style_id) is not int:
        raise NameColorGateError(
            f"style_id must be a plain int, got {type(style_id).__name__}"
        )
    return style_id in STYLES_COVERED_BY_RE195


# ---------------------------------------------------------------------------
# The verdict.  Fail-closed: the only way ``allowed`` becomes True is for
# every blocker below to be retired by a ticket that says so, and no argument
# to this function can retire one.
# ---------------------------------------------------------------------------

#: The three routes RE-195 checked and closed, in its own terms.  Each string
#: is what a future round has to defeat WITH EVIDENCE before P-2 colour code
#: may be written -- not a TODO a round may delete.
P2_COLOR_WIRING_BLOCKERS = (
    "identity_scheme_is_positive: field_mobs composes 0x2000+placement+1, "
    "so every shipped mob bypasses the typed CNetNPC style-61 tail "
    f"(RE-195, {RE_195_RESULT_LETTER})",
    "faction_is_a_fallback_operand_only: BasicAttr+0x68 reaches the relation "
    f"comparator {hex(FACTION_COMPARATOR_VA)} from one conditional fallback "
    f"site {hex(FACTION_COMPARATOR_SOLE_CALL_SITE_VA)}; earlier predicate "
    "exits bypass it, so faction cannot force a style (RE-195 job 1)",
    "hit_writer_needs_a_signed_negative_target: the CHitResult writers that "
    "set +0x70 & 0x100 require a signed-negative target identity, which the "
    "current positive identities fail before the bit can be set (RE-195 job 3)",
)


@dataclass(frozen=True)
class P2ColorWiringVerdict:
    """Whether P-2 colour code may be written today, and why not."""

    allowed: bool
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]

    def reason(self) -> str:
        if self.allowed:
            return "allowed"
        return " | ".join(self.blockers)


def p2_color_wiring_verdict() -> P2ColorWiringVerdict:
    """Refuse P-2 colour wiring, and say exactly what would have to change.

    There is no argument that flips this to allowed, and that is the point:
    the premise it refuses lives in the client image and in ``field_mobs``,
    not in a caller's opinion.  When a round believes a blocker is retired,
    it changes THIS function against a named ticket result and takes the
    test below red with it, in one reviewable diff.
    """
    return P2ColorWiringVerdict(
        allowed=False,
        blockers=P2_COLOR_WIRING_BLOCKERS,
        evidence=(RE_191_RESULT_LETTER, RE_195_RESULT_LETTER),
    )
