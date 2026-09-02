"""LANE-B round 506kk0: no console WRITE in the pickup lane may cost a row.

WHAT THE COO ASKED, IN FULL, because half of it is the operative half.
``COO-DECISION 2026-09-02T13:45+07:00`` item 2: close every ``print()`` still
left in the transaction lane (``mob_pickup_persist``, the INSERT rows) before
going back to ``bag_delta_pc`` -- AND, if ``#573`` already closed them all,
"report one line saying grep print( in the transaction lane = 0 and go
straight to bag_delta_pc".  ``#573`` HAD closed them all.  So the one line is
reported (round file `B_20260902_1446_506kk0`, and the letter of the same
round), and this file is NOT what the letter asked for: it is what the lane
kept from the measurement, because the fact "zero today" has a shelf life of
one commit and the loss it prevents is an ITEM, not a log line.

THE MEASURED LOSS THIS GUARDS.  Round lh21ua, on this lane's own branch:
under a stdout that refuses every write -- the cp874 console this project
runs on is one bad byte away from that -- a bare console write between the
take and the INSERT raised, the drop had LEFT the ground, the backpack table
was unchanged, the loss report was never printed, and the exception unwound
into the connection listener.  The item existed nowhere.

THE RULE.  In the four modules the pickup transaction runs through, a console
write may appear in exactly two functions -- ``mob_pickup.say`` and
``mob_pickup_request._say`` -- and in those two, EVERY such write must sit
inside a ``try`` that swallows.  A console write here means: a call to
``print``, or a write/writelines/flush on ``sys.stdout`` / ``sys.stderr``, or
a reference to either stream at all.  Everything else in these modules
composes a LINE and hands it to a caller.

WHAT THIS CANNOT DO, written here rather than discovered later.  It is a
STATIC rule and a static rule reads spellings: ``p = print; p(x)``,
``getattr(sys, "stdout").write(x)``, a logging handler configured elsewhere,
or a C extension writing to fd 1 all defeat it.  pf-adversary measured the
first version of this file passing green on a ``sys.stdout.write`` mutant in
``mob_pickup_persist.persist_pickup`` that reproduced the whole lh21ua item
loss, which is why the rule below is about STREAMS and not only about the
name ``print``.  It is a tripwire on the shapes people actually type, never a
proof that no write can escape.  The proof that a write cannot cost a row
stays where it has always been: ``say``/``_say`` swallow, and
``mob_pickup_persist``'s precheck-before-take ordering.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pirateforce_foundation"

#: The modules the transaction runs through: the request decode, the
#: transaction itself, the persistence, and the ledger the take goes to.
TRANSACTION_LANE = (
    "mob_pickup.py",
    "mob_pickup_persist.py",
    "mob_pickup_request.py",
    "mob_loot.py",
)

#: The two guarded helpers, by ``module:function``.
GUARDED_SAY = frozenset((
    "mob_pickup.py:say",
    "mob_pickup_request.py:_say",
))

STREAMS = frozenset(("stdout", "stderr"))


def _innermost_functions(tree):
    """``id(node) -> innermost enclosing function name`` for a whole tree.

    INNERMOST, and that is pf-adversary's D8 on this file's first version:
    attributing to the OUTERMOST function let a nested ``def emit(text):
    print(...)`` inside ``say`` inherit ``say``'s allow-list entry while
    sitting outside its ``try`` and being handed to a caller.
    """
    holder = {}

    def descend(node, current):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                holder[id(child)] = current
                descend(child, child.name)
            else:
                holder[id(child)] = current
                descend(child, current)

    descend(tree, "<module level>")
    return holder


def _console_writes(tree):
    """``(function, lineno, what)`` for every console write in a tree.

    ``ast`` is what makes this honest about the other direction too: a
    comment quoting a print, and a docstring showing a caller how to use the
    module (``mob_drop_presence`` has three of those), are not writes and
    never appear here.
    """
    holder = _innermost_functions(tree)
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            found.append((holder.get(id(node), "<module level>"),
                          node.lineno, "print()"))
        elif (isinstance(node, ast.Attribute)
                and node.attr in STREAMS):
            found.append((holder.get(id(node), "<module level>"),
                          node.lineno, "sys.%s" % node.attr))
    return found


class TheTransactionLaneWritesToNoConsoleOfItsOwn(unittest.TestCase):

    def test_every_console_write_is_one_of_the_two_guarded_helpers(self):
        offenders = []
        for name in TRANSACTION_LANE:
            tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
            for function, lineno, what in _console_writes(tree):
                if "%s:%s" % (name, function) not in GUARDED_SAY:
                    offenders.append("%s:%d %s in %s"
                                     % (name, lineno, what, function))
        self.assertEqual(
            offenders, [],
            "a console write in the pickup transaction lane that nothing "
            "swallows.  A console that raises between the take and the "
            "INSERT costs the player the item (measured, round lh21ua).  "
            "Compose the line and hand it to mob_pickup.say instead: %s"
            % offenders)

    def test_the_persistence_module_writes_nothing_at_all(self):
        """The INSERT rows the COO's letter names, checked on their own.

        ``mob_pickup_persist`` sits between the take and the database write.
        It does not even own a guarded helper: every line it composes is
        printed by ``mob_pickup.say`` from a caller, so zero here is the
        whole rule rather than a subset of one.
        """
        tree = ast.parse(
            (SRC / "mob_pickup_persist.py").read_text(encoding="utf-8"))
        self.assertEqual(_console_writes(tree), [])

    def test_every_write_in_both_helpers_is_inside_a_try_that_swallows(self):
        """The allow-list is only safe while the two exceptions are real.

        Naming a function in ``GUARDED_SAY`` is a promise that its console
        write cannot escape.  This reads the promise off the tree rather than
        trusting the name, and it reads it for EVERY write in the function --
        pf-adversary's D8: the first version asked only whether SOME write
        sat inside a swallowing ``try``, so a second one added before the
        ``try`` passed green.
        """
        for entry in sorted(GUARDED_SAY):
            module, function = entry.split(":")
            tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
            target = None
            for node in ast.walk(tree):
                if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == function):
                    target = node
            self.assertIsNotNone(target, "%s no longer exists" % entry)
            swallowed = set()
            for node in ast.walk(target):
                if not isinstance(node, ast.Try):
                    continue
                catches_everything = any(
                    handler.type is None
                    or (isinstance(handler.type, ast.Name)
                        and handler.type.id == "Exception")
                    for handler in node.handlers)
                if not catches_everything:
                    continue
                for branch in node.body:
                    for inner in ast.walk(branch):
                        swallowed.add(id(inner))
            unguarded = []
            for node in ast.walk(target):
                is_write = (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ) or (
                    isinstance(node, ast.Attribute) and node.attr in STREAMS
                )
                if is_write and id(node) not in swallowed:
                    unguarded.append("%s:%d" % (entry, node.lineno))
            self.assertEqual(
                unguarded, [],
                "%s writes to a console outside a try that swallows; the "
                "allow-list in this file is what lets it write at all: %s"
                % (entry, unguarded))

    def test_neither_helper_hides_a_nested_function(self):
        """A nested def is a write this file's allow-list cannot follow.

        The two helpers are allow-listed by NAME.  A function defined inside
        one of them can be handed to a caller and run anywhere, so the
        allow-list would be covering a write it no longer bounds.
        """
        for entry in sorted(GUARDED_SAY):
            module, function = entry.split(":")
            tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node,
                                   (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == function):
                    continue
                nested = [
                    child.name for child in ast.walk(node)
                    if isinstance(child,
                                  (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child is not node
                ]
                self.assertEqual(nested, [], "%s defines %s" % (entry, nested))


if __name__ == "__main__":
    unittest.main()
