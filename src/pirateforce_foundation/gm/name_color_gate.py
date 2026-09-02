"""Refuse P-2 monster-name-colour wiring until its measured precondition holds.

THIS MODULE WRITES NO COLOUR, CARRIES NO STYLE ID IN CODE, AND SENDS NO BYTE.
It is a read-only refusal.  Its whole job is to make one already-measured
bounded negative *executable*, so a later round cannot wire the P-2 colour
rule on a premise the client image has already refuted, and so the refusal
names its own evidence instead of being prose in a letter nobody re-reads.

Evidence
--------
1. ``RE-191`` (DONE/PASS at the conditional-static + DATA layer; runtime
   pixels still open) closed the PALETTE question.  Its numbers are
   deliberately NOT here: that ticket's own forbidden-actions section rules
   out writing monster-colour code from it, and ``NOW.md`` P-2 adds
   "ห้าม hardcode FontStyleID" (``CODEX_URGENT 20260901_1627``).  Read the
   letter when a human needs a number.
2. ``RE-195`` (DONE/BOUNDED-NEGATIVE, opened for this lane out of
   ``CORE-REQUEST-GM-048``) closed the REACHABILITY question, negatively.

What RE-195 measured, and the ONE direction it measured it in
-------------------------------------------------------------
The client's canonical selector splits on the identity before it can reach
the typed ``CNetNPC`` tail that owns the "fighting" style.  RE-195 measured
one direction of that split and only one:

    a POSITIVE identity with a zero high dword  ==>  enters the
    positive-identity family the selector table names, and BYPASSES the
    typed CNetNPC tail entirely.

``field_mobs.FieldMob.actor_identity`` composes ``0x2000 + placement_index
+ 1``; every row that comes through ``load_roster`` (whose table parser
bounds the index to ``[0, 0xDFFE]``) lands in exactly that measured class.
RE-195 then closed the two escape routes a lane might reach for: the faction
comparator is called from ONE conditional fallback site inside the
relationship predicate, so earlier exits bypass it and faction alone cannot
force a style; and the ``CHitResult`` writers of the relevant bit require a
signed-NEGATIVE target identity, which the current positive identities fail
before the bit can be set.

!! THE CONVERSE IS NOT MEASURED, AND THIS MODULE MUST NEVER IMPLY IT.
"Not in the measured bypass class" does NOT mean the typed tail is
reachable.  ``CODEX_URGENT 20260901_1627`` records that the tail also
depends on death / offensive / bit / linked-actor / local-state gates that
nobody has walked, and RE-195's own closing line asks for "a coherent
nonpositive identity mapping PLUS a typed/live gate proof".  The first draft
of this module shipped ``typed_style61_tail_reachable()`` returning True for
any nonpositive identity -- affirming the consequent, and the precise thing
``NOW.md`` P-2 bans as "ห้ามเดา identity ติดลบโดยไม่ปิด uniqueness/registry".
pf-adversary (round ``wggs0i``, D2) killed it.  The public predicate below is
one-sided on purpose: it answers only the direction RE-195 walked, and
raises on every identity class RE-195 did not.

Scope this module does NOT cover
--------------------------------
* Which side of the split a zero identity sits on is inherited from a column
  label ("signed_nonpositive"), not from a quoted compare instruction --
  ``[PROPOSED]``.  Nothing here depends on it: ``0x2000 + idx + 1`` is never
  zero, and zero is outside the measured class, so it raises.
* Which dword of the identity PAIR the selector tests.  The wire quantity is
  a qword (``field_mobs`` writes ``qwordtag(0x32, actor_identity)``) and the
  selector table names an ``identity_pair``; RE-195 says only that today's
  value is "positive, high dword zero".  So the measured class is bounded on
  BOTH ends -- ``0 < identity < 2**32`` -- and a 64-bit value with a set high
  dword is refused rather than guessed (pf-adversary D9).
* Whether any style reaches a rendered pixel.  Controller allocation,
  lookup, local vslots and delivery order are all client gates neither
  ticket walked.
* Anything about GM status.  Nothing here grants, checks, or implies it.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Provenance.  Every constant below is a TRANSCRIPTION from a bridge letter,
# not something this repository can re-derive (the client image is not here).
# The test pins each one by value so a silent edit shows up as a test diff.
# ---------------------------------------------------------------------------

#: The client image both tickets were re-derived against.
CLIENT_IMAGE_SHA256 = (
    "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"
)
CLIENT_IMAGE_BYTES = 14_759_424

#: The canonical selector span RE-195 joined its matrix to.
SELECTOR_SPAN = (0x00443F50, 0x004443C5)
SELECTOR_SPAN_SHA256 = (
    "ee845ee6ef6337ea41ae57a5a4df8af5a8a8ac00e458ea1ce3e587aff1f9cdf9"
)

#: The relationship predicate, and the faction comparator it calls at ONE
#: conditional fallback site (RE-195's whole-image E8 census found exactly
#: one direct caller).
RELATIONSHIP_PREDICATE_SPAN = (0x0043C380, 0x0043C63C)
FACTION_COMPARATOR_VA = 0x004A1D50
FACTION_COMPARATOR_SOLE_CALL_SITE_VA = 0x0043C5E0

RE_191_RESULT_LETTER = (
    "notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md"
)
RE_195_RESULT_LETTER = (
    "notes_to_chief/"
    "20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md"
)

# ---------------------------------------------------------------------------
# The measured identity class.  Opaque name on purpose: this is one side of a
# split in the client's selector, NOT a gameplay noun, and NOT a style id.
#
# NO FontStyleID NUMBER APPEARS IN THIS MODULE'S CODE, and the round that
# wrote it kept them out of its prose too.  NOW.md P-2 forbids hardcoding
# one (a test below enforces the code half), and gm/attr_wire.py
# already keeps its own FontStyleID domain out of code for the same reason.
# The styles RE-195's matrix covers, and the further ones that
# CODEX_URGENT 20260901_1627 places behind the SAME identity lane (the first
# draft of this module wrongly called those "unmeasured" -- pf-adversary D5),
# are named ONLY in the letters and in PF_ATTR_NAME_COLOR_SELECTOR.tsv.
# ---------------------------------------------------------------------------

IDENTITY_CLASS_MEASURED_BYPASS = "positive_identity_high_dword_zero"

#: Half-open bounds of the identity class RE-195 actually measured.
MEASURED_BYPASS_IDENTITY_RANGE = (1, 2 ** 32)

#: Widest value this module will even look at: a 64-bit wire quantity in
#: either signed or unsigned spelling.
_ACCEPTED_MIN = -(2 ** 63)
_ACCEPTED_MAX = 2 ** 64 - 1


class NameColorGateError(ValueError):
    """An input does not have the shape this module requires.

    ``ValueError`` to match this package's own house style
    (``gm/commands.py::GmCommandArgsError``, ``gm/attr_wire.py::AttrWireError``).
    Callers must catch THIS class, not bare ``ValueError``: a generic
    input-validation handler swallowing a refusal is the failure mode this
    whole module exists to prevent.
    """


class NameColorGateUnmeasured(NameColorGateError):
    """The input is well-formed, but RE-195 did not measure its class.

    Separate from a shape error so a caller cannot conflate "you passed
    junk" with "nobody has measured this yet".  There is no answer to give
    here, and inventing one is exactly the overclaim pf-adversary killed.
    """


def _require_identity(value: object) -> int:
    # bool is an int subclass, and ``True`` would otherwise classify as a
    # positive identity and read like a deliberate answer.
    if isinstance(value, bool) or type(value) is not int:
        raise NameColorGateError(
            f"identity must be a plain int, got {type(value).__name__}"
        )
    if not (_ACCEPTED_MIN <= value <= _ACCEPTED_MAX):
        raise NameColorGateError(
            f"identity does not fit a 64-bit wire quantity: {value}"
        )
    return value


def is_measured_bypass_identity(identity: int) -> bool:
    """True iff this identity is in the class RE-195 measured as bypassing.

    The ONLY affirmative answer this module gives, and it is affirmative
    about a bypass -- never about reachability.  Anything well-formed but
    outside the measured class raises :class:`NameColorGateUnmeasured`
    rather than returning False, because False here would read as "does not
    bypass", which a caller would then read as "reaches the tail".
    """
    value = _require_identity(identity)
    low, high = MEASURED_BYPASS_IDENTITY_RANGE
    if low <= value < high:
        return True
    raise NameColorGateUnmeasured(
        f"identity {value} is outside the class RE-195 measured "
        f"({IDENTITY_CLASS_MEASURED_BYPASS}, {low} <= v < {high}); "
        "RE-195 measured the bypass direction only -- see "
        f"{RE_195_RESULT_LETTER} and do not infer reachability from this"
    )


# ---------------------------------------------------------------------------
# The verdict.  Fail-closed: no argument flips it, and the dataclass that
# carries the permission cannot be minted in the allowed state either
# (pf-adversary D8: the first draft's frozen dataclass was public and
# unvalidated, so a caller could build its own allowed verdict).
# ---------------------------------------------------------------------------

#: The three routes RE-195 checked and closed, in its own terms.  Each string
#: is what a future round has to defeat WITH EVIDENCE -- not a TODO to delete.
P2_COLOR_WIRING_BLOCKERS = (
    "identity_scheme_is_positive: field_mobs composes 0x2000+placement+1, "
    "so every roster row bypasses the typed CNetNPC tail "
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
    """Whether P-2 colour code may be written today, and why not.

    ``allowed`` exists so a call site reads honestly, not so it can be set:
    constructing this class with ``allowed=True`` raises.  When a round
    believes the blockers are retired it changes THIS class against a named
    ticket result, in one reviewable diff, and takes the tests with it.
    """

    allowed: bool
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.allowed is not False:
            raise NameColorGateError(
                "P2ColorWiringVerdict cannot be constructed in the allowed "
                "state while RE-195's bounded negative stands; retire the "
                "blockers in this module against a ticket result instead"
            )
        if not self.blockers:
            raise NameColorGateError("a refusal with no blocker names nothing")

    def reason(self) -> str:
        return " | ".join(self.blockers)


def p2_color_wiring_verdict() -> P2ColorWiringVerdict:
    """Refuse P-2 colour wiring, and say exactly what would have to change."""
    return P2ColorWiringVerdict(
        allowed=False,
        blockers=P2_COLOR_WIRING_BLOCKERS,
        evidence=(RE_191_RESULT_LETTER, RE_195_RESULT_LETTER),
    )
