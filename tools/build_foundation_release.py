"""Build a deterministic source-only release archive (generated, ignored)."""
import argparse, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT/'current/pf_login_game_server_v141.py',
    ROOT/'docs/HYPOTHESIS_LEDGER.json',
    ROOT/'docs/FUNCTIONAL_COVERAGE.json',
    *sorted((ROOT/'src').rglob('*.py')),
    *sorted((ROOT/'migrations').glob('*.sql')),
    *sorted((ROOT/'scenarios').glob('*.json')),
    ROOT/'tools/PF_FAST_ENTRY_AUTOMATION.md',
    ROOT/'tools/pf_relation_probe.py',
    ROOT/'tools/pf_relation_probe_config.json',
    ROOT/'tools/pf_relation_matrix_probe.py',
    ROOT/'tools/pf_action_producer_probe.py',
    ROOT/'tools/pf_action_producer_probe_config.json',
    ROOT/'tools/pf_action_producer_probe_local_config.json',
    ROOT/'tools/pf_action_consumer_probe.py',
    ROOT/'tools/pf_action_consumer_probe_config.json',
    ROOT/'tools/pf_action_consumer_probe_local_config.json',
    ROOT/'tools/pf_hit_result_probe.py',
    ROOT/'tools/pf_hit_result_probe_config.json',
    ROOT/'tools/pf_hit_result_probe_local_config.json',
    ROOT/'tools/pf_behavior_lookup_probe.py',
    ROOT/'tools/pf_behavior_lookup_probe_config.json',
    ROOT/'tools/pf_behavior_lookup_probe_local_config.json',
    ROOT/'tools/pf_behavior_entry_probe.py',
    ROOT/'tools/pf_behavior_entry_probe_config.json',
    ROOT/'tools/pf_behavior_entry_probe_local_config.json',
    ROOT/'tools/pf_behavior_range_gate_probe.py',
    ROOT/'tools/pf_behavior_range_gate_probe_config.json',
    ROOT/'tools/pf_behavior_range_gate_probe_local_config.json',
    ROOT/'tools/pf_skill_trigger_probe.py',
    ROOT/'tools/pf_skill_trigger_probe_config.json',
    ROOT/'tools/pf_skill_trigger_probe_local_config.json',
    ROOT/'tools/pf_knockdown_consumer_probe.py',
    ROOT/'tools/pf_knockdown_consumer_probe_config.json',
    ROOT/'tools/pf_knockdown_consumer_probe_local_config.json',
    ROOT/'tools/pf_structural_corpus_audit.py',
    ROOT/'tools/pf_structural_corpus_audit_config.json',
    ROOT/'tools/verify_hypothesis_ledger.py',
    ROOT/'tools/verify_functional_coverage.py',
    ROOT/'tools/run_test_arena.ps1',
    ROOT/'tools/run_scene2_load_only.ps1',
    ROOT/'tools/run_foundation_visible.ps1',
    ROOT/'tools/scene_db_guard.py',
    ROOT/'tools/wait_for_pf_stage.py',
]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output', default='release/pirateforce-foundation.zip'); args=ap.parse_args()
    out=ROOT/args.output; out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in FILES:
            info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes())
    print(out)
if __name__=='__main__': main()
