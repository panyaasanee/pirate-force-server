import importlib.util, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scene_db_guard", ROOT/"tools/scene_db_guard.py")
GUARD = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(GUARD)

class SceneDbGuardTests(unittest.TestCase):
    def test_unchanged_main_and_missing_sidecars_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            db=Path(raw)/"state.sqlite3"; db.write_bytes(b"stable")
            before=GUARD.snapshot(db); after=GUARD.snapshot(db)
            self.assertEqual(GUARD.compare(before,after),(True,[]))
            self.assertFalse(before["files"]["-wal"]["exists"])
            self.assertFalse(before["files"]["-shm"]["exists"])
    def test_main_mutation_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            db=Path(raw)/"state.sqlite3"; db.write_bytes(b"before")
            before=GUARD.snapshot(db); db.write_bytes(b"after")
            passed,changed=GUARD.compare(before,GUARD.snapshot(db))
            self.assertFalse(passed); self.assertEqual(changed,["main"])
    def test_created_sidecars_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            db=Path(raw)/"state.sqlite3"; db.write_bytes(b"stable")
            before=GUARD.snapshot(db)
            Path(str(db)+"-wal").write_bytes(b"wal"); Path(str(db)+"-shm").write_bytes(b"shm")
            passed,changed=GUARD.compare(before,GUARD.snapshot(db))
            self.assertFalse(passed); self.assertEqual(changed,["-wal","-shm"])

if __name__=="__main__": unittest.main()
