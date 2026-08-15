import importlib.util, json, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("pf_structural_corpus_audit",ROOT/"tools/pf_structural_corpus_audit.py")
P=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=P; SPEC.loader.exec_module(P)

class StructuralCorpusAuditTests(unittest.TestCase):
 def test_anchored_parsers_only_and_malformed_fail(self):
  lines=["00000000 16 F7 raw", "STRUCTURAL_IDS [(0, 28271, 'Outer'), (15, 6602, 'ActionVital')] OUTER version=0 mask=0x02 count=1 nested_version=0", "2026-08-13T19:23:44.411 RECV frame=1 pc_len=45 ids=[(0, 17722, 'Login')]" ]
  frames=P.parse_lines(lines); self.assertEqual([x.ids[0][1] for x in frames],[28271,17722])
  for bad in ("STRUCTURAL_IDS nope", "2026-08-13T19:23:44.411 RECV broken", "STRUCTURAL_IDS [(1, 2, 'x')] OUTER version=0 mask=0x00 count=0 nested_version=None", "STRUCTURAL_IDS [(0, 1, 'x'), (15, 2, 'y')] OUTER version=0 mask=0x02 count=99 nested_version=0"):
   with self.assertRaises(ValueError): P.parse_lines([bad])
 def test_exact_guarded_corpus_and_determinism(self):
  config=P.load_config(P.DEFAULT_CONFIG); one=P.audit(config); two=P.audit(config)
  self.assertEqual(one,two); self.assertEqual(one["eligible_original_server_to_client_frames"],0)
  self.assertTrue(one["no_eligible_original_server_to_client_frames"]); self.assertFalse(one["bounded_target_negative"]); self.assertGreater(one["totals"]["decoded_frames"],0)
  self.assertEqual(set(one["combat_targets"]),{"5879","6890","6877","10716","12579","15887","16101"})
 def test_direction_duplicate_and_drift_fail(self):
  raw=json.loads(P.DEFAULT_CONFIG.read_text())
  for mutate in (lambda d:d["sources"][0].update(direction="unknown"),lambda d:d["sources"][0].update(direction="server_to_client",provenance="original_server_capture"),lambda d:d["targets"].update({"5879":"Changed"}),lambda d:d["sources"].append(dict(d["sources"][0])),lambda d:d["sources"][0].update(size=1)):
   data=json.loads(json.dumps(raw)); mutate(data)
   with tempfile.TemporaryDirectory() as td:
    path=Path(td)/"c.json"; path.write_text(json.dumps(data))
    with self.assertRaises(ValueError): P.load_config(path)
 def test_zip_member_guard_and_safe_output(self):
  config=P.load_config(P.DEFAULT_CONFIG); source=next(x for x in config["sources"] if x["container"]=="zip")
  self.assertIn("STRUCTURAL_IDS",P.source_text(source))
  with self.assertRaises(ValueError): P.output_path(ROOT/"reports/out.json")
  ok=P.DEFAULT_OUTPUT_ROOT/"audit.json"; self.assertEqual(P.output_path(ok),ok.resolve())
 def test_source_has_no_raw_search_or_mutation(self):
  source=Path(P.__file__).read_text()
  self.assertIn("line.startswith(\"STRUCTURAL_IDS \")",source); self.assertIn(" RECV ",source)
  for forbidden in ("GameClient","socket","sendall","hexdump","fromhex"):
   self.assertNotIn(forbidden,source)

if __name__=="__main__": unittest.main()
