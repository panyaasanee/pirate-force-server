"""Watch the character-creation and appearance-binding claims directly.

The functional coverage rows ``character_management/character_creation`` and
``character_management/appearance_and_avatar_binding`` both cited only
``tests/test_foundation.py``, which is a module about the whole session loop.
That module proves the created identity is *present* in every projection, but it
never proves the two things those rows actually claim:

* creation is keyed by a **sha256 fingerprint of the submitted wire**, stores a
  **casefolded name key**, and refuses names that are not already normalized or
  that disagree with the name inside the opaque wire; and
* rebinding an actor to a server identity is **byte-preserving everywhere else** --
  the appearance is carried through opaquely rather than decoded, normalized or
  regenerated.

Every test here asserts an exact byte set or an exact stored value, so a change
that quietly replaces submitted appearance with a canonical preset, or that
dedupes creation by name instead of by wire, fails immediately.
"""

import hashlib
import sqlite3
import sys
import struct
import tempfile
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pirateforce_foundation.actor_wire import (
    bind_actor_and_avatar_identity,
    bind_common_attr_identity,
    bind_identity_and_selector,
    read_identity,
    read_name,
    read_selector,
)
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.store import SQLiteStore

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# One byte deep in the opaque tail of the preset actor wire. It is outside the
# identity window, the selector byte, the name field and the embedded AvatarAttr
# identity window, so flipping it is a pure appearance change.
OPAQUE_TAIL_OFFSET = 213


class CharacterIdentityBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.default = Position(
            1, 0,
            self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y,
            self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.default, self.legacy.extract_avatar_attr_wire_from_actor
        )
        self.preset_wire = self.legacy.get_preset_actor_wire()

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------------- helpers

    def preset(self, name="test01"):
        """The preset actor wire with its name field replaced, length preserved."""
        old = self.legacy.wstr_tag("test01")
        if name == "test01":
            return self.preset_wire
        self.assertEqual(self.preset_wire.count(old), 1)
        new = self.legacy.wstr_tag(name)
        self.assertEqual(len(new), len(old), "test names must be the same length")
        return self.preset_wire.replace(old, new, 1)

    def wire_named(self, name):
        """The preset wire carrying an arbitrary name, length not preserved."""
        old = self.legacy.wstr_tag("test01")
        self.assertEqual(self.preset_wire.count(old), 1)
        return self.preset_wire.replace(old, self.legacy.wstr_tag(name), 1)

    @staticmethod
    def diff_offsets(left: bytes, right: bytes) -> set[int]:
        assert len(left) == len(right)
        return {i for i in range(len(left)) if left[i] != right[i]}

    def identity_window(self) -> set[int]:
        """CreateActorDataEx identity bytes 1..8 plus the selector byte 10."""
        return set(range(1, 9)) | {10}

    def avatar_identity_window(self, actor_wire: bytes) -> set[int]:
        avatar = self.legacy.extract_avatar_attr_wire_from_actor(actor_wire)
        offset = actor_wire.find(avatar)
        self.assertGreaterEqual(offset, 0)
        return set(range(offset + 3, offset + 11))

    def name_window(self, actor_wire: bytes) -> set[int]:
        byte_length = struct.unpack_from("<I", actor_wire, 12)[0]
        return set(range(16, 16 + byte_length))

    def query(self, sql: str, parameters=()):
        # Closed explicitly: `with sqlite3.connect(...)` manages the transaction,
        # not the connection, and Windows refuses to unlink the still-open file
        # when TemporaryDirectory cleans up.
        db = sqlite3.connect(self.db_path)
        try:
            return db.execute(sql, parameters).fetchone()
        finally:
            db.close()

    def row(self, character_id: int):
        return self.query(
            "SELECT name,name_key,create_fingerprint,identity_lo,identity_hi,selector"
            " FROM characters WHERE id=?",
            (character_id,),
        )

    def character_count(self) -> int:
        return int(self.query("SELECT COUNT(*) FROM characters")[0])

    # ------------------------------------------------ appearance is preserved

    def test_identity_bind_changes_exactly_the_identity_and_selector_bytes(self):
        bound = bind_identity_and_selector(
            self.preset_wire, 0x11223344, 0x55667788, 7
        )
        self.assertEqual(len(bound), len(self.preset_wire))
        self.assertEqual(
            self.diff_offsets(self.preset_wire, bound), self.identity_window()
        )
        self.assertEqual(read_identity(bound), (0x11223344, 0x55667788))
        self.assertEqual(read_selector(bound), 7)
        self.assertEqual(read_name(bound), read_name(self.preset_wire))

    def test_full_bind_changes_exactly_the_two_identity_windows(self):
        expected = self.identity_window() | self.avatar_identity_window(
            self.preset_wire
        )
        bound, avatar = bind_actor_and_avatar_identity(
            self.preset_wire,
            0x11223344,
            0x55667788,
            7,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.assertEqual(len(bound), len(self.preset_wire))
        self.assertEqual(self.diff_offsets(self.preset_wire, bound), expected)
        # The returned AvatarAttr is the rebound one and it sits, exactly once,
        # at the same offset it occupied before the rebind.
        original = self.legacy.extract_avatar_attr_wire_from_actor(self.preset_wire)
        self.assertEqual(len(avatar), len(original))
        self.assertNotEqual(avatar, original)
        self.assertEqual(bound.count(avatar), 1)
        self.assertEqual(bound.find(avatar), self.preset_wire.find(original))

    def test_avatar_identity_is_rebound_to_the_same_identity_as_the_actor(self):
        bound, avatar = bind_actor_and_avatar_identity(
            self.preset_wire,
            0x0DEFACED,
            0x00C0FFEE,
            3,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.assertEqual(read_identity(bound), (0x0DEFACED, 0x00C0FFEE))
        self.assertEqual(
            struct.unpack_from("<II", avatar, 3), (0x0DEFACED, 0x00C0FFEE)
        )
        self.assertEqual(
            self.legacy.extract_avatar_attr_wire_from_actor(bound), avatar
        )

    def test_bind_refuses_an_ambiguous_embedded_avatar(self):
        blob = bytes([0x0B, 0x01, 0x32]) + bytes(8)
        forged = self.preset_wire[:16] + blob + blob
        with self.assertRaises(ValueError):
            bind_actor_and_avatar_identity(
                forged, 1, 0, 0, lambda _wire: blob
            )

    def test_bind_refuses_malformed_actor_and_attr_prefixes(self):
        broken_tag = bytearray(self.preset_wire)
        broken_tag[0] = 0x33
        broken_kind = bytearray(self.preset_wire)
        broken_kind[9] = 0x0C
        for candidate in (bytes(broken_tag), bytes(broken_kind), self.preset_wire[:11]):
            with self.assertRaises(ValueError):
                bind_identity_and_selector(bytes(candidate), 1, 0, 0)
        with self.assertRaises(ValueError):
            bind_identity_and_selector(self.preset_wire, 1, 0, 256)

        avatar = self.legacy.extract_avatar_attr_wire_from_actor(self.preset_wire)
        for index, value in ((0, 0x0C), (1, 0x00), (2, 0x33)):
            broken = bytearray(avatar)
            broken[index] = value
            with self.assertRaises(ValueError):
                bind_common_attr_identity(bytes(broken), 1, 0)
        with self.assertRaises(ValueError):
            bind_common_attr_identity(avatar[:10], 1, 0)

    def test_two_created_characters_keep_their_own_submitted_appearance(self):
        """Two names, one differing opaque byte: nothing else may drift."""
        account = self.store.ensure_account("appearance")
        first_wire = self.preset("aaaaaa")
        second_wire = bytearray(self.preset("bbbbbb"))
        second_wire[OPAQUE_TAIL_OFFSET] ^= 0xFF
        second_wire = bytes(second_wire)

        first = self.lifecycle.create(account, "aaaaaa", first_wire)
        second = self.lifecycle.create(account, "bbbbbb", second_wire)

        # Each stored wire differs from what was submitted only in the identity
        # windows -- the appearance bytes are carried through untouched.
        for character, submitted in ((first, first_wire), (second, second_wire)):
            allowed = self.identity_window() | self.avatar_identity_window(submitted)
            drifted = self.diff_offsets(submitted, character.actor_wire) - allowed
            # A subset, not an equality: the submitted wire carries a zero
            # identity, so identity bytes that are already zero legitimately do
            # not change. The byte-exact equality is asserted by the two direct
            # bind tests above, which control every identity byte.
            self.assertEqual(
                drifted, set(),
                "server rewrote appearance bytes outside the identity windows",
            )
            self.assertEqual(read_name(character.actor_wire), character.name)

        # And the difference between the two stored wires still carries the
        # opaque byte that only the second one submitted.
        self.assertNotEqual(
            first.actor_wire[OPAQUE_TAIL_OFFSET],
            second.actor_wire[OPAQUE_TAIL_OFFSET],
        )
        self.assertEqual(
            second.actor_wire[OPAQUE_TAIL_OFFSET],
            second_wire[OPAQUE_TAIL_OFFSET],
        )

    # ------------------------------------------------------- creation contract

    def test_create_fingerprint_is_the_sha256_of_the_submitted_wire(self):
        account = self.store.ensure_account("fingerprint")
        submitted = self.preset("aaaaaa")
        character = self.lifecycle.create(account, "aaaaaa", submitted)
        name, name_key, fingerprint, lo, hi, selector = self.row(character.id)
        self.assertEqual(fingerprint, hashlib.sha256(submitted).hexdigest())
        # Not the sha of what was stored: the stored wire has been rebound.
        self.assertNotEqual(
            fingerprint, hashlib.sha256(character.actor_wire).hexdigest()
        )
        self.assertEqual((name, selector), ("aaaaaa", character.selector))
        self.assertEqual((lo, hi), (character.identity_lo, character.identity_hi))

    def test_name_key_is_the_casefolded_name_and_the_name_keeps_its_case(self):
        account = self.store.ensure_account("casing")
        character = self.lifecycle.create(account, "AAAAAA", self.preset("AAAAAA"))
        name, name_key, _fingerprint, _lo, _hi, _selector = self.row(character.id)
        self.assertEqual(name, "AAAAAA")
        self.assertEqual(name_key, "aaaaaa")
        self.assertEqual(character.name, "AAAAAA")

    def test_retry_is_deduped_by_submitted_wire_and_not_by_name(self):
        account = self.store.ensure_account("retry")
        submitted = self.preset("aaaaaa")
        first = self.lifecycle.create(account, "aaaaaa", submitted)
        replay = self.lifecycle.create(account, "aaaaaa", submitted)
        self.assertEqual(replay.id, first.id)
        self.assertEqual(self.character_count(), 1)

        different_appearance = bytearray(submitted)
        different_appearance[OPAQUE_TAIL_OFFSET] ^= 0xFF
        twin = self.lifecycle.create(account, "aaaaaa", bytes(different_appearance))
        self.assertNotEqual(twin.id, first.id)
        self.assertEqual(self.character_count(), 2)
        self.assertNotEqual(twin.selector, first.selector)
        self.assertNotEqual(
            (twin.identity_lo, twin.identity_hi),
            (first.identity_lo, first.identity_hi),
        )
        self.assertEqual(self.row(twin.id)[1], self.row(first.id)[1])

    def test_fingerprint_dedup_is_scoped_to_one_account(self):
        submitted = self.preset("aaaaaa")
        one = self.store.ensure_account("account-one")
        two = self.store.ensure_account("account-two")
        self.assertNotEqual(one, two)
        first = self.lifecycle.create(one, "aaaaaa", submitted)
        second = self.lifecycle.create(two, "aaaaaa", submitted)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.character_count(), 2)
        self.assertNotEqual(
            (first.identity_lo, first.identity_hi),
            (second.identity_lo, second.identity_hi),
        )
        self.assertEqual(self.row(first.id)[2], self.row(second.id)[2])

    def test_created_identity_is_derived_from_account_and_selector(self):
        account = self.store.ensure_account("identity")
        first = self.lifecycle.create(account, "aaaaaa", self.preset("aaaaaa"))
        second = self.lifecycle.create(account, "bbbbbb", self.preset("bbbbbb"))
        for character in (first, second):
            self.assertEqual(
                character.identity_lo,
                0x10000000 + account * 0x10000 + character.selector + 1,
            )
            self.assertEqual(character.identity_hi, 0)
            self.assertEqual(
                read_identity(character.actor_wire),
                (character.identity_lo, character.identity_hi),
            )
            self.assertEqual(read_selector(character.actor_wire), character.selector)
        self.assertEqual((first.selector, second.selector), (0, 1))

    # -------------------------------------------------------- creation refuses

    def test_create_refuses_a_name_that_disagrees_with_the_wire(self):
        account = self.store.ensure_account("disagree")
        with self.assertRaises(ValueError):
            self.lifecycle.create(account, "aaaaaa", self.preset("bbbbbb"))
        self.assertEqual(self.character_count(), 0)

    def test_create_refuses_unnormalized_names_the_wire_itself_agrees_with(self):
        """Isolate the normalization guard from the name/wire agreement guard.

        Each wire below really does carry the rejected name, so the only rule
        that can refuse it is the NFKC-and-strip guard in ``create``.
        """
        account = self.store.ensure_account("normalize")
        # "ａ" is fullwidth 'a'; NFKC folds it to "a", so it is not normalized.
        for name in (" test01", "test01 ", "   ", "ａａａ"):
            wire = self.wire_named(name)
            self.assertEqual(read_name(wire), name)
            with self.assertRaises(ValueError):
                self.lifecycle.create(account, name, wire)
        self.assertEqual(self.character_count(), 0)

    def test_create_accepts_a_precomposed_name_and_pins_the_normal_form(self):
        """"tésty" is NFKC-stable but not NFKD-stable, so this pins NFKC exactly.

        Without it, swapping the server to NFKD would still pass every other
        test in this module while silently rejecting legitimate accented names.
        """
        account = self.store.ensure_account("precomposed")
        name = "tésty"
        self.assertNotEqual(name, unicodedata.normalize("NFKD", name))
        wire = self.wire_named(name)
        self.assertEqual(read_name(wire), name)
        character = self.lifecycle.create(account, name, wire)
        self.assertEqual(character.name, name)
        self.assertEqual(self.row(character.id)[1], name.casefold())

    def test_create_refuses_an_empty_name_the_wire_itself_agrees_with(self):
        account = self.store.ensure_account("empty")
        wire = self.wire_named("")
        self.assertEqual(read_name(wire), "")
        with self.assertRaises(ValueError):
            self.lifecycle.create(account, "", wire)
        self.assertEqual(self.character_count(), 0)

    def test_create_requires_the_opaque_avatar_extractor(self):
        account = self.store.ensure_account("no-extractor")
        blind = CharacterLifecycle(self.store, self.default, None)
        with self.assertRaises(ValueError):
            blind.create(account, "test01", self.preset_wire)
        self.assertEqual(self.character_count(), 0)


if __name__ == "__main__":
    unittest.main()
