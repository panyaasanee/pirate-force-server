"""Build a deterministic source-only standalone release archive (generated, ignored)."""
import argparse, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT/'current/pf_login_game_server_v141.py', *sorted((ROOT/'src').rglob('*.py')), *sorted((ROOT/'migrations').glob('*.sql'))]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output', default='release/pirateforce-foundation.zip'); args=ap.parse_args()
    out=ROOT/args.output; out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in FILES:
            info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes())
    print(out)
if __name__=='__main__': main()
