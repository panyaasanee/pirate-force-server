"""Count tokens in Python source the way a claim about CODE means them.

Pulled out of ``tools/pf_hp_death_respawn_static.py`` for one reason: that
verifier opens the read-only client image at import time, so every test of it
skips on a clone that does not have the image and the Windows gate excludes the
whole module.  A discriminator that decides whether a negative claim is true
must not live where no test can reach it.  This module needs no image, no
third-party package and no network, so ``tests/test_static_verifier_pins_cloud``
exercises it directly on every machine.

The problem it solves.  A negative like "no Relive/Revive/Respawn encoder or
dispatch exists in our server" used to be counted with ``text.count("Respawn")``
over whole files.  On 2026-08-28 that guard was red with nine hits and every one
of them was English prose in a comment or a guard message, plus one "6868"
sitting inside a SHA-256 literal.  Prose cannot make a claim about code false,
and a guard that any comment can redden stops being read.

So the count is over tokens:

  NUMBER  compared by VALUE, so 0x1AD4, 6868, 6_868 and 0o15324 all count and
          no run of hex digits inside a string can collide;
  NAME    an identifier carrying a stem counts - ``def respawn_actor`` IS the
          thing a "no respawn encoder" claim forbids;
  STRING  a literal with NO whitespace counts, for a stem or for a wire id
          spelled as text, because that is the shape of a dispatch key
          (``{"ReliveVital": handler}``, ``{"0x1AD4": handler}``, which is how
          this repo writes expected-ack dicts).  A prose sentence carries
          spaces and is excluded by construction.

f-strings are read on both tokenizer generations: 3.11 hands back one STRING
token, 3.12+ splits them into FSTRING_START/MIDDLE/END, and the MIDDLE pieces
are scanned so ``f"Relive{n}"`` counts on the bridge's 3.14 exactly as it does
on a 3.11 runner.

``scan`` returns None when the text will not tokenize.  Callers must treat that
as "count it the old way" rather than as zero: a file that does not parse is
the one place where the crude substring count is the safer answer.
"""
from __future__ import annotations

import io
import re
import tokenize

_STRING_BODY = re.compile(r"^[A-Za-z]*('''|\"\"\"|'|\")(?P<body>.*)\1$", re.S)
_WHITESPACE = re.compile(r"\s")

# 3.12+ only; absent on 3.11, where an f-string is a single STRING token.
_FSTRING_MIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)


def _int_or_none(text):
    try:
        return int(text.replace("_", ""), 0)
    except (ValueError, AttributeError):
        return None


def _string_body(literal):
    match = _STRING_BODY.match(literal)
    return match.group("body") if match else literal


def scan(text, stems=(), values=()):
    """Count code-token hits.

    ``stems``  lower-case substrings looked for in identifiers and in
               whitespace-free string literals.
    ``values`` integers looked for in numeric literals, and in whitespace-free
               string literals that spell a number.

    Returns ``(value_hits, stem_hits)``, or None if ``text`` will not tokenize.
    """
    value_hits = stem_hits = 0
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None
    for token in tokens:
        kind, piece = token.type, token.string
        if kind == tokenize.NUMBER:
            number = _int_or_none(piece)
            if number is not None and number in values:
                value_hits += 1
            continue
        if kind == tokenize.NAME:
            low = piece.lower()
            stem_hits += sum(1 for stem in stems if stem in low)
            continue
        if kind == tokenize.STRING:
            body = _string_body(piece)
        elif _FSTRING_MIDDLE is not None and kind == _FSTRING_MIDDLE:
            body = piece
        else:
            continue
        if not body or _WHITESPACE.search(body):
            continue
        low = body.lower()
        stem_hits += sum(1 for stem in stems if stem in low)
        number = _int_or_none(body)
        if number is not None and number in values:
            value_hits += 1
    return value_hits, stem_hits
