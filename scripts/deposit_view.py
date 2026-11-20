"""Prepare the directory names used by the original evidence-register scripts.

Each link points to a run in the unpacked Zenodo deposit. Source files are
read in place. The destination must be new.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('deposit', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
root = args.deposit.resolve(strict=True)
rows = json.loads((Path(__file__).resolve().parents[1]/'reference/archives.json').read_text())
aliases = Counter(row['sourceName'] for row in rows)
links = {}
for row in rows:
    run = root / row['directory']
    if not run.is_dir():
        raise SystemExit(f'Missing {run}. Extract the four deposit ZIPs and the Appendix L supplement first.')
    archive = row['archive']
    links[archive] = run.parent
    alias = row['sourceName']
    if aliases[alias] == 1 and alias != archive:
        links[alias] = run
    if archive in ('20261106-claude-fidelity-push-rerun','20261109-claude-opus-playwright-b'):
        links[alias] = run
args.destination.mkdir(parents=True, exist_ok=False)
for name, path in links.items():
    (args.destination/name).symlink_to(path,target_is_directory=True)
print(f'{len(rows)} archive directories available in {args.destination.resolve()}')
