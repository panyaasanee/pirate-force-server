"""LANE-B: the expiry COO attached to the gate-2 shape rule is executable.

``COO-DECISION 20260829_0441`` approved ``bag_admission``'s shape rule for
gate 2 as an INTERIM and ordered its expiry written into the module (item 2).
Prose expires badly: a nonclaim that says "this is temporary" reads exactly
the same on the day it stopped being true.  These tests turn the two halves
of that expiry into things a run can fail on.

WHAT THIS FILE IS AND IS NOT.  It does not test the admission rule -- that is
``tests/test_bag_admission.py``, which enumerates the governed family.  It
tests that the RULE'S OWN SUNSET is still correctly described:

  1. the expiry condition is stated in the module, in both places a reader
     looks (the nonclaim tuple and a constant), and
  2. ~~the condition is still UNMET~~ WHICH NAMED FUNCTIONS MAY MEET IT.

BOTH HALVES OF THE CONDITION WERE MET IN ROUND 4gqnwm by STORE-INSERT-001,
and the two tests that said "not yet" were converted there rather than
deleted: they now pin the exact writers -- one INSERT for character
creation plus one for a pickup, one advance of the counter -- so a second
pickup path or a second counter writer still fails.  The replacement COO
specified (delete ``_classify_against``) was NOT performed in that round,
because deleting it was measured to admit the HYP-PF-008/010 bags this gate
refuses; the ask is no longer open -- COO-DECISION 20260829_0848 ruled
route 1 (the shape rule STAYS, the counter tightens it as
``may_enter_world``'s ``issued_through`` ceiling, wired in round hsz32u).
The measurement is recorded in ``bag_admission`` nonclaim 9 and in the
docstring of ``test_exactly_one_named_write_advances_the_identity_counter``.

DELIBERATELY A SOURCE-TEXT TEST.  ``bag_admission`` must not import ``store``
(it sits on the character-select path and pulling the store in to read a
boolean would be a worse defect than the one this guards).  So the second
half is measured the only honest way available from here: over the source of
``mob_pickup`` and ``store``, naming the tokens it looks for so a reader can
grep the same thing by hand.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import bag_admission


_SRC = Path(bag_admission.__file__).resolve().parent


def _source(module_name: str) -> str:
    return (_SRC / (module_name + ".py")).read_text(encoding="utf-8")


#: ROUND pksqwj (LANE-B), on COO-DECISION `20260908_0542` item 5, which
#: answers LANE-DB's `20260908_0602` about the owner's `20260908_0025`
#: item 4.  ONE RESERVED SEAT, AND IT IS NOT AN ALLOWLIST.
#:
#: The owner ordered a migration that gives every existing character the
#: weapon its class says it holds.  Carrying the old weapon forward is an
#: `INSERT INTO character_backpack_items`, and the row needs an identity, so
#: the migration is a lawful writer of a bag row -- and this file is the pin
#: that enumerates every function allowed to be one.  `store.py`'s own "THE
#: WRITING HALF IS WITHDRAWN, NOT FORGOTTEN" comment is the record of
#: LANE-DB withdrawing the caller rather than widening the pin, which is the
#: one answer NOW.md `2050` allows.  This is the pin owner's half of that
#: transaction, and it is deliberately shaped the same way round `4gqnwm`
#: shaped the seat it gave `commit_acquired_backpack_item`: one name, with
#: its reason on the line beside it.
#:
#: What a SEAT means here, written out so a later round cannot read it as a
#: general exemption:
#:   * exactly ONE name is reserved -- spelled out, not a pattern, not a
#:     module, not a prefix;
#:   * the required writers below stay REQUIRED: an empty seat is fine, a
#:     missing pickup write or a missing character-creation insert is red;
#:   * a FOURTH constant-SQL writer in either scanned module is still red,
#:     which is the whole property this file exists to hold;
#:   * no skip, no xfail, no allowlist file, and the scan itself is not
#:     narrowed by one byte.
#:
#: The seat is EMPTY on this commit: LANE-DB's writing half is not on main,
#: and the only occurrence of the name under `src/` is that comment.
#: Occupied or empty, the assertions below assert the same thing.
RESERVED_MIGRATION_WRITER = "apply_class_weapon_migration"

#: The writers that must be present whatever the seat holds.  Kept apart
#: from the seat so that a round which deletes the pickup write cannot
#: satisfy either assertion by leaning on the reservation.
REQUIRED_COUNTER_ADVANCERS = frozenset({"commit_acquired_backpack_item"})
REQUIRED_BACKPACK_ROW_INSERTERS = frozenset({
    "_insert_initial_backpack", "commit_acquired_backpack_item",
})

#: ROUND pksqwj, SECOND PASS, after pf-adversary broke the first one.  The
#: modules the write scans read.  ``persistence_class_weapon`` joins them in
#: the same round that made it a seated participant in bag-row writing:
#: pf-adversary D7 put a constant-SQL ``INSERT INTO character_backpack_items``
#: plus a counter ``UPDATE`` in that module under any name at all and every
#: pin here stayed green, because the scan read two modules and the seat had
#: just named a third.
SCANNED_WRITE_MODULES = ("store", "mob_pickup", "persistence_class_weapon")


def _addressable_defs(source: str, name: str) -> tuple:
    """Definitions of ``name`` a caller could actually reach, in order.

    Module level, or the body of a module-level class.  A ``def`` nested
    inside a function is a CLOSURE and is not ``store.<name>``; pf-adversary
    opened both gate-2 seats with exactly that (a stub returned by an
    unrelated helper, never called by anything).
    """
    tree = ast.parse(source)
    found = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                found.append(node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if (isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and child.name == name):
                    found.append(child)
    return tuple(found)


def _defs_anywhere(source: str, name: str) -> tuple:
    """Every ``def`` of ``name`` at any depth, closures included."""
    return tuple(
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def seat_is_occupied(source: str) -> bool:
    """Is the reserved seat actually filled, in this module's source?

    ROUND pksqwj, SECOND PASS.  THREE things, and each one is a hole
    pf-adversary walked through in the first pass:

      * at least one definition, so prose does not open the seat -- the
        module NAMES the function today, in a comment explaining that it is
        absent;
      * exactly one definition ANYWHERE, closures included, because the SQL
        scans attribute a statement to its INNERMOST enclosing function: a
        second body with the same name, nested inside the pickup write, was
        measured collapsing N writers into one seat;
      * that one definition is addressable, so a never-called nested stub
        cannot claim it.

    A definition is still not an implementation, and this predicate does not
    pretend otherwise -- what stops an EMPTY occupant is the counter rule at
    the point of use: a seated INSERT that does not also advance the counter
    fails, whatever its body looks like.
    """
    addressable = _addressable_defs(source, RESERVED_MIGRATION_WRITER)
    anywhere = _defs_anywhere(source, RESERVED_MIGRATION_WRITER)
    return len(addressable) == 1 and len(anywhere) == 1


def _seat_on_this_tree() -> set:
    """The one name the write pins may subtract, or nothing at all.

    ROUND pksqwj SECOND PASS (pf-adversary D1).  ``store.py`` is where the
    occupant has to live -- it is the module the write scans read and the
    module COO's order names -- so the seat is open exactly when that
    module holds it.
    """
    return ({RESERVED_MIGRATION_WRITER}
            if seat_is_occupied(_source("store")) else set())


def test_nonclaim_8_states_the_expiry_and_names_the_replacement() -> None:
    """The tuple a console reader sees carries the rule's full history.

    Pinned by content and not by index: a later round is free to renumber,
    but it may not quietly drop the record.  ~~"the sentence that says this
    rule dies"~~ IS STRUCK: COO-DECISION 20260829_0848 CANCELLED the sunset
    (route 1 -- the shape rule stays, the counter tightens it), so what may
    not be quietly dropped now is the cancellation itself and the ruling
    that ordered it, beside the 0441 history that created the expiry.
    """
    joined = "\n".join(bag_admission.BAG_ADMISSION_NONCLAIMS)
    assert "COO-DECISION 20260829_0441" in joined, (
        "the ruling that made this rule interim is not cited in the "
        "nonclaims a reader actually sees"
    )
    assert "COO-DECISION 20260829_0848" in joined, (
        "the ruling that cancelled the expiry and kept the shape rule is "
        "not cited in the nonclaims a reader actually sees"
    )
    assert "next_item_identity" in joined, (
        "the criterion is keyed to the identity counter; the nonclaims do "
        "not name it"
    )
    assert "_classify_against" in joined, (
        "the nonclaims must name the function 0848 ruled STAYS -- a reader "
        "grepping for its fate must find the answer here"
    )


def test_the_expiry_condition_is_two_named_facts_not_a_date() -> None:
    """A date cannot be evaluated by a test; these two facts can.

    Both are about ``store.py`` doing something it now does (since round
    4gqnwm) -- the constant survives as the record of what was evaluated,
    the supersession it once armed having been cancelled by 0848.  The
    order is meaningful -- the INSERT is what makes the counter advance
    possible -- and it is asserted so the constant cannot be reshuffled into
    a weaker pair.
    """
    condition = bag_admission.BAG_ADMISSION_EXPIRY_CONDITION
    assert len(condition) == 2
    assert "INSERT" in condition[0] and "store.py" in condition[0]
    assert "next_item_identity" in condition[1]
    assert all(text.isascii() for text in condition), (
        "this constant can reach the bridge console, which is cp874"
    )


def _executed_sql(module_name: str):
    """(enclosing function, sql text) for every string handed to a DB call.

    Two failures shaped this helper, both found by pf-adversary.

    A LINE SCANNER IS NOT ENOUGH.  ``store.py`` writes SQL split across
    adjacent string literals and, elsewhere in this codebase, hoisted into a
    module constant.  Both look like nothing to a per-line grep.  ``ast``
    folds implicit concatenation into one Constant, and module-level
    constants are resolved by name below, so both shapes are seen.

    PROSE IS NOT A STATEMENT.  Matching SQL text anywhere in a file finds
    ``mob_pickup``'s docstrings, which discuss at length the exact INSERT
    ``store.py`` must one day make, and its console token
    ``MOB_PICKUP_ROW_WOULD_INSERT table=character_backpack_items``.  A
    module that DESCRIBES a write is the opposite of a module that performs
    one -- that description is the whole reason the expiry is not met yet.
    So only strings that reach ``execute``/``executemany``/``executescript``
    count.
    """
    tree = ast.parse(_source(module_name))
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                owner[id(child)] = node.name
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name not in ("execute", "executemany", "executescript"):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            text = first.value
        elif isinstance(first, ast.Name) and first.id in constants:
            text = constants[first.id]
        else:
            continue
        out.append((owner.get(id(node), "<module>"), " ".join(text.split())))
    return out


def _writes_naming(module_name: str, column: str):
    """Executed statements that both name ``column`` and are a write.

    ``\bUPDATE\b`` and not ``"UPDATE" in text``: every write in
    ``store.py`` also sets ``updated_at``, and a substring test counts a
    pure SELECT of that column as a write.  The first version of this check
    did exactly that -- red on a read, green on the write it exists to
    catch.
    """
    hits = []
    for func, text in _executed_sql(module_name):
        if column not in text:
            continue
        upper = text.upper()
        if re.search(r"\bUPDATE\b", upper) or re.search(r"\bINSERT\b", upper):
            hits.append((func, text))
    return hits


def test_exactly_one_named_write_advances_the_identity_counter() -> None:
    """Half two of the expiry, CONVERTED BY THE ROUND THAT MET IT (4gqnwm).

    This test used to assert that nothing advanced the counter, and it went
    red the moment STORE-INSERT-001 landed -- which is what it was for.  It
    is not deleted, because "nobody writes this column" and "one named
    function writes this column" are different claims and the second is
    still worth failing on: ~~a second writer~~ AN UNNAMED writer is how a
    monotonic counter stops being monotonic.  So the tripwire becomes a pin.

    ROUND pksqwj SEATED A SECOND NAME AND SAYS SO HERE, NOT ONLY IN THE
    ASSERTION.  ``RESERVED_MIGRATION_WRITER`` above carries the reason and
    the decision (`0542` item 5, on the owner's `0025` item 4); the word
    that changed in the sentence above is "second" to "unnamed", and
    nothing else about this pin moved.  Two writers who each take their
    identity from this counter, both named here, is still a monotonic
    counter; a third, unnamed one is not, and is still red.

    WHAT THIS PIN CAN AND CANNOT SEE -- an adversarial pass BUILT the
    evasions rather than imagining them, and three of them were green
    against this test's first draft.  It reads statements handed to
    execute/executemany in ``store`` and ``mob_pickup`` whose SQL is a
    string CONSTANT (``_executed_sql`` documents that limit itself).  A
    writer whose SQL is BUILT -- ``%``-formatted, f-string, joined -- is
    invisible to it, and so is one added to a third module.  The scan was
    widened to both modules after the pass found a counter writer added to
    ``mob_pickup`` sailing past a store-only scan.  So: this catches the
    copy-paste, not the determined author, and no round may quote it as
    proof that a second writer cannot exist.

    THE REPLACEMENT THAT HALF TWO CALLED FOR IS NOT IN THIS ROUND, AND
    NOT SILENTLY.  COO-DECISION 20260829_0441 item 2 says the superseding
    round deletes ``_classify_against`` rather than keeping it.  Derived by
    running the counter-only rule over the shipped constants on this head,
    before the deletion was attempted (the script and its output are in
    ``pf_bridge/rounds/R224_4gqnwm_*``, and an adversarial pass re-derived
    it independently): with ``_classify_against`` gone and the counter as
    the sole criterion, ``HYPOTHESIZED_V111_SLOT2``
    (HYP-PF-008) and the free-slot move (HYP-PF-010) are ADMITTED -- both
    move a golden row without minting an identity, so a rule that only asks
    whether an identity was issued cannot see them, and every family test in
    ``tests/test_bag_admission.py`` requires them refused.  COO's answer
    ARRIVED: COO-DECISION 20260829_0848 ruled on that measurement -- route
    1, keep the shape rule, and require of an acquired row an identity the
    counter issued (the ``issued_through`` ceiling, wired in round hsz32u).
    Nonclaim 9 and this docstring were replaced together, as the previous
    version of this docstring required.
    """
    # BOTH modules, matching the inserter test below.  Scanning only
    # ``store`` left the sharpest evasion invisible: a second counter
    # advancer added to ``mob_pickup`` -- the module the sibling test
    # already reads -- passed this file while the docstring claimed in
    # capitals that a second writer fails.
    writes = [
        hit for module in SCANNED_WRITE_MODULES
        for hit in _writes_naming(module, "next_item_identity")
    ]
    # Seeding and advancing are different acts and are pinned apart.  The
    # seed writes the column once, at character create, as part of the row
    # that creates the bag; the advance is the pickup write.  A test that
    # lumped them would go green on a seed that had quietly become a second
    # allocator.
    seeds = {func for func, text in writes if re.search(r"\bINSERT\b", text.upper())}
    advances = {func for func, text in writes if re.search(r"\bUPDATE\b", text.upper())}
    # NO SEAT HERE, AND THAT IS DELIBERATE -- pf-adversary D6 asked why, so
    # the answer is written down instead of left as an accident.  SEEDING is
    # the act of creating a character's bag row, and creating bags is
    # character creation's job alone.  A migration that finds an old
    # character with NO `character_backpacks` row and mints one is not
    # carrying a weapon forward, it is minting a bag, and that is a
    # different ask that needs its own decision from the owner rather than
    # a seat granted in passing.  If LANE-DB needs it, this line is the one
    # to bring to COO -- and it will go red first, loudly, which is the
    # point.
    assert seeds == {"_insert_initial_backpack"}, (
        "the set of functions that SEED character_backpacks."
        "next_item_identity is %s, not character creation alone.  The seat "
        "reserved for %s does NOT cover seeding: see the comment above."
        % (sorted(seeds) or "empty", RESERVED_MIGRATION_WRITER)
    )
    # THE SEAT, SUBTRACTED ONCE, HERE (`0542` item 5, on `0025` item 4).
    # The migration may advance the counter because the row it carries
    # forward needs an identity nobody else holds -- which is the reason
    # this column exists, not an exception to it.  Subtracting one named
    # function leaves the assertion exactly as strict as it was: the pickup
    # write is still required by name, and a third advancer still fails.
    #
    # AND THE SUBTRACTION IS CONDITIONAL, WHICH THE FIRST PASS OF THIS ROUND
    # GOT WRONG.  pf-adversary D1: the gate-2 file gated its seats on the
    # occupant really existing and this file did not, so the reservation was
    # handed out on a tree where nothing had landed -- the commit message
    # advertised a safeguard that lived in the other file.  Same predicate,
    # both halves, now.
    advances_besides_the_seat = advances - _seat_on_this_tree()
    assert advances_besides_the_seat == set(REQUIRED_COUNTER_ADVANCERS), (
        "the set of functions that ADVANCE "
        "character_backpacks.next_item_identity is %s, not the single "
        "pickup write (plus, at most, the seat reserved for %s).  A counter "
        "with two unnamed writers is not a counter: the column exists so an "
        "identity is never handed out twice." % (
            sorted(advances) or "empty", RESERVED_MIGRATION_WRITER,
        )
    )


def test_the_only_backpack_row_insert_is_the_one_that_makes_a_character() -> None:
    """Half one: nothing INSERTs a bag row that a pickup produced.

    ~~Asserted by the absence of a token nobody writes
    (``MOB_PICKUP_ROW_DID_INSERT``).~~  pf-adversary showed that was a
    strawman: appending a real ``persist_pickup_row`` with a genuine INSERT,
    and leaving ``mob_pickup``'s WOULD token in place as stale prose, kept
    it green.  The honest question is not "is a token absent" but "which
    functions can put a row in the bag table", so that is what is asserted.

    ``_insert_initial_backpack`` is character creation.

    CONVERTED BY ROUND 4gqnwm, WHICH MET THIS HALF.  The second name is now
    here on purpose: ``commit_acquired_backpack_item`` is STORE-INSERT-001's
    pickup write.  The set is still pinned exactly, so ~~a third~~ A FOURTH
    (ROUND pksqwj: the third is the reserved seat above, one named function,
    and everything about the count moved by exactly one)
    constant-SQL inserter in either scanned module fails this test -- which
    is the property worth keeping now that "no pickup path exists" has
    stopped being true.  Same scope limit as the test above, and it is not
    theoretical here: ``reports/moveisol001_smoke/pf_move_isolation_probe.py``
    is a tracked file that INSERTs bag rows and is not scanned at all
    (SKIPPINS/probe cleanup ticket in pf_bridge names it).
    Why the replacement this half called for is not in that round, with the
    measurement that refuted its literal form, is in the docstring of
    ``test_exactly_one_named_write_advances_the_identity_counter`` above.
    """
    statement = re.compile(r"INSERT\s+INTO\s+character_backpack_items",
                           re.IGNORECASE)
    inserters = {
        func for module in SCANNED_WRITE_MODULES
        for func, text in _executed_sql(module)
        if statement.search(text)
    }
    # THE SEAT'S REASON, ENFORCED RATHER THAN ASSERTED.  This comment used to
    # say the migration's INSERT "takes its identity from the counter -- so
    # it arrives the way this test requires every row to arrive, not around
    # it", and NOTHING CHECKED IT.  pf-adversary D1 shipped a seated
    # `apply_class_weapon_migration` whose INSERT used the literal identity
    # 7 and never touched the counter, and the entire repository suite
    # exited 0.  So the rule is now a rule: an occupant that inserts a bag
    # row must also advance the counter, in the same module, or it loses the
    # seat and is a fourth inserter like any other.
    advancers = {
        func for module in SCANNED_WRITE_MODULES
        for func, text in _writes_naming(module, "next_item_identity")
        if re.search(r"\bUPDATE\b", text.upper())
    }
    seat = _seat_on_this_tree()
    if seat and RESERVED_MIGRATION_WRITER in inserters:
        assert RESERVED_MIGRATION_WRITER in advancers, (
            "%s INSERTs a backpack row and never advances "
            "character_backpacks.next_item_identity.  The seat this lane "
            "reserved for it was reserved on the ground that the row it "
            "carries forward TAKES an identity from the counter; a row that "
            "mints its own identity is the exact defect the pin exists to "
            "stop, and the seat does not cover it"
            % (RESERVED_MIGRATION_WRITER,)
        )
    inserters_besides_the_seat = inserters - seat
    assert inserters_besides_the_seat == set(
        REQUIRED_BACKPACK_ROW_INSERTERS
    ), (
        "the set of functions that INSERT a backpack row is %s, not "
        "character creation plus the one pickup write (plus, at most, the "
        "seat reserved for %s).  Every row a player owns has to come from a "
        "path that took an identity from the counter; a fourth inserter is "
        "a way for one to arrive without one." % (
            sorted(inserters), RESERVED_MIGRATION_WRITER,
        )
    )


def test_the_pickup_path_still_only_logs_the_row_it_would_write() -> None:
    """The token, kept as a SECOND signal rather than the only one.

    Weaker than the test above and labelled as such: it catches a rename,
    not a behaviour change.  It stays because the token is what a person
    greps the console for, and a silent rename would strand that habit.
    """
    assert "MOB_PICKUP_ROW_WOULD_INSERT" in _source("mob_pickup"), (
        "the console token this expiry is written around has been renamed; "
        "re-derive the expiry rather than deleting this test"
    )


def test_the_wire_this_nonclaim_describes_is_actually_there() -> None:
    """Nonclaim 3 says gate 2 calls this module.  Check it, do not report it.

    pf-adversary's finding: nonclaim 3 first said the wire was "in flight"
    when it had already merged, then told the reader to go and verify at
    their own head.  Both are reports.  This is the check, and it fails in
    both directions -- if the wire is reverted, nonclaim 3 becomes false
    and this goes red.
    """
    session = _source("session")
    assert "bag_admission.may_enter_world(" in session, (
        "session.select_and_start no longer calls "
        "bag_admission.may_enter_world.  Gate 2 is byte-identical again and "
        "nonclaim 3 in bag_admission.py -- which states the opposite in "
        "capitals -- must be struck through in the same commit as the "
        "revert."
    )


def test_classify_against_still_exists_so_the_expiry_has_a_subject() -> None:
    """The function the sunset names must be findable by that name.

    Guards the failure mode where a refactor renames ``_classify_against``
    and nonclaim 8's "DELETE this" instruction silently loses its referent,
    leaving a rule with an expiry nobody can carry out.
    """
    tree = ast.parse(_source("bag_admission"))
    names = {
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "_classify_against" in names, (
        "COO-DECISION 20260829_0848 ruled that _classify_against STAYS, but "
        "no function by that name exists; if it was renamed, update the "
        "nonclaims in the same commit as the rename"
    )


# ---------------------------------------------------------------------------
# The seat's own predicate, driven by PLANTED SOURCES rather than by the tree.
#
# ROUND pksqwj, SECOND PASS.  pf-adversary D5: both branches the first pass
# added were dead code at HEAD -- a probe that raised inside each of them
# left the suite green -- and D3: welding `return True` as the first line of
# the predicate also left the suite green.  A helper can be driven with
# planted sources; the live scan cannot.  This file's sibling
# (tests/test_gate2_bag_admission_wiring.py) already learned exactly this
# lesson once, in `ProseIsNotACallerButEveryDynamicRouteStillIs`, and the
# first pass of this round added new acting lines without the planted test
# its own precedent demands.
# ---------------------------------------------------------------------------

_A_COMMENT_NAMING_IT = (
    "class SQLiteStore:\n"
    "    # apply_class_weapon_migration was written and withdrawn; see 2050\n"
    "    def other(self):\n"
    "        return 1\n"
)
_A_METHOD = (
    "class SQLiteStore:\n"
    "    def apply_class_weapon_migration(self, character_id):\n"
    "        return character_id\n"
)
_A_MODULE_LEVEL_FUNCTION = (
    "def apply_class_weapon_migration(character_id):\n"
    "    return character_id\n"
)
_A_NESTED_STUB_NOBODY_CALLS = (
    "class SQLiteStore:\n"
    "    def _unrelated_helper(self):\n"
    "        def apply_class_weapon_migration():\n"
    "            return None\n"
    "        return apply_class_weapon_migration\n"
)
_A_SECOND_BODY_INSIDE_THE_PICKUP_WRITE = (
    "class SQLiteStore:\n"
    "    def apply_class_weapon_migration(self, character_id):\n"
    "        return character_id\n"
    "    def commit_acquired_backpack_item(self, row):\n"
    "        def apply_class_weapon_migration():\n"
    "            return None\n"
    "        return apply_class_weapon_migration()\n"
)
_TWO_METHODS_OF_THE_SAME_NAME = (
    "class SQLiteStore:\n"
    "    def apply_class_weapon_migration(self, character_id):\n"
    "        return character_id\n"
    "class OtherStore:\n"
    "    def apply_class_weapon_migration(self, character_id):\n"
    "        return character_id\n"
)


def test_prose_naming_the_seated_function_does_not_fill_the_seat() -> None:
    """The state of the shipped tree today, planted so it is measured."""
    assert seat_is_occupied(_A_COMMENT_NAMING_IT) is False


def test_a_method_or_a_module_level_function_fills_the_seat() -> None:
    assert seat_is_occupied(_A_METHOD) is True
    assert seat_is_occupied(_A_MODULE_LEVEL_FUNCTION) is True


def test_a_nested_stub_nobody_calls_does_not_fill_the_seat() -> None:
    """pf-adversary D3's payload against the first pass, verbatim in shape.

    ``mov al,1; ret`` opened the door there: any ``def`` at any depth was
    accepted, so a closure returned by an unrelated helper granted a seat
    that covered a DIFFERENT file.
    """
    assert seat_is_occupied(_A_NESTED_STUB_NOBODY_CALLS) is False


def test_a_second_body_of_the_same_name_forfeits_the_seat() -> None:
    """pf-adversary D2: N writers collapsing into one reserved name.

    The SQL scans attribute a statement to its INNERMOST enclosing function,
    so a closure named after the seat, sitting inside the pickup write, was
    measured writing a bag row AND resetting the counter with every pin
    green.  One seat means one function, so more than one definition of the
    name -- anywhere, at any depth -- is not a seat, it is a hiding place.
    """
    assert seat_is_occupied(_A_SECOND_BODY_INSIDE_THE_PICKUP_WRITE) is False
    assert seat_is_occupied(_TWO_METHODS_OF_THE_SAME_NAME) is False


def test_the_predicate_is_not_answerable_by_a_constant() -> None:
    """The mutant that killed the first pass's version: ``return True``.

    Four planted sources, two of each verdict, so neither a welded ``True``
    nor a welded ``False`` can satisfy this file.
    """
    verdicts = [
        seat_is_occupied(source) for source in (
            _A_COMMENT_NAMING_IT,
            _A_METHOD,
            _A_NESTED_STUB_NOBODY_CALLS,
            _A_MODULE_LEVEL_FUNCTION,
        )
    ]
    assert verdicts == [False, True, False, True], verdicts


def test_the_seat_is_shut_on_the_tree_this_test_runs_against() -> None:
    """Stated as a fact about TODAY, and it is allowed to change.

    When LANE-DB lands the occupant this goes red, and the round that lands
    it flips this one line -- which is the point: the tree's state is
    recorded, not assumed, and nobody can widen the seat without touching a
    line that says what they are doing.
    """
    assert _seat_on_this_tree() == set()
