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

What is being DONE about the bounded negative, and what is not
--------------------------------------------------------------
Round ``5ddsii`` filed the ticket chief queued as ``RE-222`` (drawn as
~~``RE-211``~~; see :data:`RE_222_TICKET_ID` for why the number moved, and
:data:`RE_222_TICKET_LETTER`).  The refusal below did NOT move because of it
and this docstring is the wrong place to look for a result -- nothing in this
module reads one.

Read :func:`unaddressed_blockers` before :func:`open_questions`, in that
order.  The first names the route NOTHING is filed against; the second names
what one filed ticket bears on.  A lane that reads "a ticket is open" as
"P-2 is nearly unblocked" and writes colour code is the failure this pairing
exists to make awkward, so the gap is the half with the shorter name.

The ticket asks THREE questions and this module maps TWO of them.  Q3 (what
a nonpositive identity costs the client's own actor registry) prices the
direction; it does not retire any blocker below, so it maps to none of them
and :data:`RE_222_QUESTION_LABELS` is where all three are named.  pf-adversary
(round ``5ddsii``, O1) found the first draft describing Q3 in a comment while
no executable value carried it.

Nothing here PRINTS.  The first draft of this section said "prints", and had
a ``route_out()`` method that no call site in either repository ever called
(pf-adversary O4, and the same "no caller = no module" rule ``COO 1046``
item (c) used to reject a different module the same day).  It is deleted.

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

#: A SECOND, EARLIER gate inside the SAME predicate span, cross-referenced
#: this round against a bridge artifact ``faction_is_a_fallback_operand_only``
#: never cited: ``notes_to_chief/reference_codex_attr/PF_A2_ATTR_FIELD_DELTA
#: .tsv`` rows 6-7 name a branch at this span testing ``ActorAttr+0x98`` bit
#: ``0x04000000``, status ``PROVEN_ROLE_ONLY`` (that TSV's own words:
#: "structural/consumer role is proved but the broader gameplay noun or full
#: value domain is not unique").  The TSV's own ``semantic_name`` field for
#: this row spells out the two FontStyleID values this bit selects between --
#: deliberately NOT transcribed here, digits included, in either code or
#: prose: read the TSV row itself for them, per this module's existing rule
#: a few lines below ("kept them out of its prose too").
#:
#: ``0x0043C547 < FACTION_COMPARATOR_SOLE_CALL_SITE_VA`` (both inside
#: ``RELATIONSHIP_PREDICATE_SPAN``) -- this gate sits at a LOWER ADDRESS than
#: the faction comparator's call site.  That is the only claim the ordering
#: proves: a static layout fact, NOT a walked control-flow fact -- nothing
#: here says execution actually reaches this branch before the comparator,
#: only that it is placed earlier in the same span.  It is a candidate for
#: (one of) the "earlier exits" RE-195's prose names without an address.
#:
#: !! THIS DOES NOT RETIRE THE BLOCKER BELOW, AND NOTHING BELOW CONSUMES IT !!
#: ``PROVEN_ROLE_ONLY`` does not say whether ``field_mobs``' measured-bypass
#: identities ever reach this gate, nor what value ``ActorAttr+0x98`` carries
#: for them -- nobody has asked that question yet, so unlike every other
#: constant in this module these four are NOT wired into
#: :data:`P2_COLOR_WIRING_BLOCKERS` or :func:`p2_color_wiring_verdict` --
#: consuming an answer that does not exist yet would be the same overclaim
#: :class:`NameColorGateUnmeasured` exists to refuse, in constant form instead
#: of code form.  They are named here, pinned by value, only so a later round
#: does not have to re-discover this citation from a cold TSV grep; see the
#: RE ticket request this round files for the reachability question itself.
PAIR_RELATION_ZERO_GATE_SPAN = (0x0043C531, 0x0043C547)
#: CORRECTED by RE-263.  The round that first pinned this wrote
#: ``"ActorAttr+0x98 bit 0x04000000"``, which reads as "a bit inside the value
#: at +0x98" and is wrong twice over: +0x98 is a ONE-BYTE ``uint8_enum``
#: (PF_A2_ATTR_FIELD_DELTA.tsv rows 6-7, ``storage_width=1``, ``tag=0x0B``),
#: and ``0x04000000`` is the PRESENCE bit in the separate mask word at +0x1B4
#: that decides whether the byte appears on the wire at all -- a bit this
#: repository already models correctly one module away, in
#: ``gm/attr_wire.py`` (x=39, ``1 << 26`` on the mask, ``offset=0x098``).
#: The two published instructions in the span are byte compares against zero,
#: not a bit test: ``cmp byte ptr [esi+0x98], 0`` at 0x0043C531 and
#: ``cmp byte ptr [edi+0x98], 0`` at 0x0043C53A.
PAIR_RELATION_ZERO_GATE_OPERAND = (
    "ActorAttr+0x98 (u8), presence bit +0x1B4 & 0x04000000"
)
PAIR_RELATION_ZERO_GATE_CMP_LOCAL_VA = 0x0043C531
PAIR_RELATION_ZERO_GATE_CMP_TARGET_VA = 0x0043C53A
PAIR_RELATION_ZERO_GATE_STATUS = "PROVEN_ROLE_ONLY"
PAIR_RELATION_ZERO_GATE_SOURCE = (
    "notes_to_chief/reference_codex_attr/PF_A2_ATTR_FIELD_DELTA.tsv rows 6-7"
)

#: RE-263, CLOSED BOUNDED-NEGATIVE.  The route this lane opened last round --
#: "maybe the gate above reaches the name style without going through the
#: faction comparator" -- is a dead end, and NOT for the reason the ticket
#: anticipated.  The ticket guessed the predicate would be skipped along with
#: the typed CNetNPC tail; it is not (the predicate is called on the POSITIVE
#: identity lane at 0x00444018, which is the lane a FieldMob identity lands
#: in).  It is a dead end because the two sites that emit the name style are
#: not in the predicate at all: they sit at the VAs below, gated on the
#: receiver being the LOCAL CMyActor singleton -- the player's own nameboard,
#: which no field mob can ever be.  Separately, the gate's operand is the
#: constant this server always leaves it: the presence bit above is never set,
#: so the client never executes the wire read and the byte keeps its
#: constructor default of 0 for every actor.
#:
#: This changes NOTHING about the refusal below.  It closes a second route
#: that was never a blocker; ``faction_is_a_fallback_operand_only`` is
#: untouched and ``unaddressed_blockers()`` still returns exactly one.
LOCAL_ACTOR_NAME_STYLE_EMIT_SITE_VAS = (0x00443FE9, 0x00443FF2)
RELATION_PREDICATE_POSITIVE_LANE_CALL_SITE_VA = 0x00444018
ACTOR_ATTR_0X98_PRESENCE_GATE = "+0x1B4 & 0x04000000"
ACTOR_ATTR_0X98_CONSTRUCTOR_DEFAULT = 0
ACTOR_ATTR_0X98_DEFAULT_WRITER_VA = 0x00464D69
PAIR_RELATION_ZERO_GATE_ROUTE_VERDICT = "RE-263 BOUNDED-NEGATIVE: not a second route"

RE_191_RESULT_LETTER = (
    "notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md"
)
RE_195_RESULT_LETTER = (
    "notes_to_chief/"
    "20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md"
)

#: The ticket LANE-GM filed to attack the bounded negative rather than sit
#: behind it (``COO-DECISION 2026-09-03T10:46+07:00`` item (b), which lifted
#: that day's "no new RE tickets" rule for this ONE ticket, because a ticket
#: that PRODUCES a measurement from the client image is not a ticket that
#: consumes one).  It is filed, not answered: nothing below reads a result,
#: and the refusal is exactly as strong as it was before it was filed.
#:
#: THE NUMBER CHANGED AFTER THIS LANE DREW IT, and the old one is struck
#: through rather than deleted: ~~``RE-211``~~ -> ``RE-222``.  The draft
#: numbered itself off ``CLIENT_RE_QUEUE.md`` alone (highest ``RE`` = 210),
#: but rule (2) at the head of that file uses a counter SHARED with
#: ``GAME_TEST_QUEUE.md``, and ``GT-221`` had already landed -- so chief
#: (round ``kjtpza``, R319) queued the ticket as ``RE-222``.  There is no
#: ticket named ``RE-211`` in either queue file.  This matters here and not
#: only in a letter: :func:`open_questions` puts this id in front of an
#: operator, and an id no queue holds is an id nobody can look up, so a
#: result arriving against ``RE-222`` would have left the blockers below
#: refusing anyway (chief's letter ``20260903_1304``, point 2).
RE_222_TICKET_ID = "RE-222"
#: !! The LETTER's filename still carries the drawn number, because that is
#: the file that exists on the bridge -- it was written, consumed and copied
#: to ``consumed/`` under this name.  A later round "fixing" this path to say
#: ``RE-222`` breaks the only link between the id and the draft.
RE_222_TICKET_LETTER = (
    "notes_to_chief/"
    "20260903_1119_LANE-GM-RE-211-TICKET-"
    "typed-and-live-gate-for-nonpositive-identity.md"
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


def blocker_names() -> tuple[str, ...]:
    """The short name each blocker already carries, DERIVED not retyped.

    Every entry of :data:`P2_COLOR_WIRING_BLOCKERS` is ``"<name>: <prose>"``.

    A caveat this docstring used to omit, and pf-adversary (round ``5ddsii``)
    was right to call out: :data:`RE_222_QUESTION_FOR_BLOCKER` below IS a
    second hand-typed list of these names, eleven lines further down.  What
    ``COO 0846`` forbids is a SILENT second copy; that one is guarded by
    :func:`open_questions`, which refuses on any disagreement in either
    direction, including a rename that keeps the count the same.  A guarded
    copy is a different animal from an unguarded one -- but it is still a
    copy, and the guard is the only thing that makes it legal.

    A blocker name may contain neither ``":"`` nor ``" -> "``; both are
    separators this module parses on.  Enforced below rather than assumed.
    """
    names = []
    for blocker in P2_COLOR_WIRING_BLOCKERS:
        name, sep, _rest = blocker.partition(":")
        if not sep or not name or name != name.strip():
            raise NameColorGateError(
                f"blocker does not carry a leading '<name>:' key: {blocker!r}"
            )
        if " -> " in name:
            # `open_questions` joins name and question with this separator and
            # readers split on the FIRST one.  A name carrying it would parse
            # back as a shorter name, and the refusal that followed would name
            # a blocker nobody could find (pf-adversary, round `5ddsii`, s.4).
            raise NameColorGateError(
                f"blocker name may not contain ' -> ': {name!r}"
            )
        names.append(name)
    if len(set(names)) != len(names):
        raise NameColorGateError(f"two blockers share one name: {names}")
    return tuple(names)


#: All THREE questions the filed letter asks, by label.  Named here so a
#: reader can tell what the ticket covers WITHOUT opening the other
#: repository, and so a question that maps to no blocker is still visible
#: (pf-adversary, round `5ddsii`, O1: the first draft described Q3 in a
#: comment and carried it in no value, so a reader who grepped the module
#: concluded the ticket had two questions).
RE_222_QUESTION_LABELS = (
    "Q1: quote the compare that splits the positive identity family from the "
    "nonpositive one -- which dword, signed or unsigned, and where zero lands",
    "Q2: walk the gates from the nonpositive entry to the typed CNetNPC entry "
    "and say whether that tail is an object-TYPE test no identity can satisfy",
    "Q3: does the client's own actor registry key on a signed or an unsigned "
    "identity, and is a negative value refused, truncated or aliased",
)

#: Which question bears on which blocker.  THREE THINGS TO READ HERE, none of
#: them cheerful:
#:
#: 1. ``faction_is_a_fallback_operand_only`` is DELIBERATELY EMPTY.  RE-222
#:    does not reopen RE-195 job 1, and its own out-of-scope section says so
#:    in as many words.  ``unaddressed_blockers()`` is that gap, countable.
#: 2. The ``hit_writer`` value is THIS LANE'S INFERENCE, not something the
#:    letter says.  The letter never mentions the hit writer; the link is
#:    that "signed-negative" is the very thing Q1 asks the image to define.
#:    It is labelled ``[PROPOSED]`` in its own text because pf-adversary
#:    (round `5ddsii`, O2) found it shipped as if the letter had said it.
#: 3. Q3 maps to NOTHING.  It prices the direction; it retires no blocker.
#:    A ticket half of which retires nothing is the shape of this problem.
RE_222_QUESTION_FOR_BLOCKER = {
    "identity_scheme_is_positive": (
        "RE-222 Q1+Q2 [letter says so]: the split compare, then whether the "
        "typed CNetNPC tail is an object-TYPE test that no identity value can "
        "satisfy -- a 'no' there refuses this whole direction, which is worth "
        "more to this lane than a 'yes'"
    ),
    "faction_is_a_fallback_operand_only": "",
    "hit_writer_needs_a_signed_negative_target": (
        "RE-222 Q1 [PROPOSED -- this lane's inference, the letter does not "
        "say it]: 'signed-negative' is today a COLUMN LABEL and not a quoted "
        "instruction, so the compare Q1 asks for is what would decide whether "
        "a value this project could emit is negative to the client at all"
    ),
}


def open_questions() -> tuple[str, ...]:
    """``"<blocker name> -> <question>"`` for each blocker RE-222 bears on.

    Raises if the mapping above and :data:`P2_COLOR_WIRING_BLOCKERS` have
    drifted apart in EITHER direction.  A blocker with no key is a blocker
    whose status nobody decided; a key naming no blocker is a question aimed
    at a route that has already moved.  Both are silent today and loud here.
    """
    names = blocker_names()
    mapped = tuple(RE_222_QUESTION_FOR_BLOCKER)
    if set(mapped) != set(names):
        raise NameColorGateError(
            "RE_222_QUESTION_FOR_BLOCKER and P2_COLOR_WIRING_BLOCKERS "
            f"disagree: blockers={sorted(names)} mapped={sorted(mapped)}"
        )
    return tuple(
        f"{name} -> {RE_222_QUESTION_FOR_BLOCKER[name]}"
        for name in names
        if RE_222_QUESTION_FOR_BLOCKER[name]
    )


def unaddressed_blockers() -> tuple[str, ...]:
    """Blockers that the filed ticket does NOT bear on.  Not a TODO list."""
    names = blocker_names()
    open_questions()  # same drift guard, one source
    return tuple(name for name in names if not RE_222_QUESTION_FOR_BLOCKER[name])


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
