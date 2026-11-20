"""Recompute the archived results with the Python standard library."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
from scripts.event_counts import additional_counts
from scripts.cited_counts import calculate, observations

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / 'reference'
DATA = ROOT / 'data'
CODERS = ('opus-medium', 'sol-medium')


def load(path):
    return json.loads(path.read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tables(out, work):
    db = work / 'catalogue.sqlite'
    connection = sqlite3.connect(db)
    try:
        with gzip.open(DATA / 'catalogue.sql.gz', 'rt', encoding='utf-8') as source:
            connection.executescript(source.read())
        for note in load(DATA / 'catalogue-notes.json'):
            columns = list(note)
            require(set(columns) == {r[1] for r in connection.execute('pragma table_info(lab_readings)')}, 'Wrong note schema')
            connection.execute('insert into lab_readings ('+', '.join(columns)+') values ('+', '.join('?' for _ in columns)+')', list(note.values()))
        connection.commit()
        extra = additional_counts(connection, DATA)
        (out / 'supplementary-counts.json').write_text(json.dumps(extra, indent=2)+'\n')
    finally:
        connection.close()
    dest = out / 'tables'
    subprocess.run([sys.executable, ROOT / 'scripts/paper1-tables.py', '--db', db, '--out', dest], check=True)
    expected = load(REFERENCE / 'tables.sha256.json')
    actual = {p.name: digest(p.read_bytes()) for p in dest.iterdir()}
    require(actual == expected, f'Table files differ: {[k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k)]}')
    print(f'{len(actual)} table files identical to the paper freeze. 664 matches, six cited constants and eight outside the catalogue.')


def whole_lessons(out, work):
    dest = work / 'whole-lessons'
    with zipfile.ZipFile(DATA / 'whole-lesson-inputs.zip') as z:
        z.extractall(dest)
    subprocess.run([sys.executable, ROOT / 'scripts/paper1-lesson-analysis.py', dest], check=True)
    analysis = (dest / 'ANALYSIS.json').read_bytes()
    require(digest(analysis) == load(REFERENCE / 'whole-lesson.sha256.json')['ANALYSIS.json'], 'Whole-lesson analysis differs from the archived original')
    (out / 'whole-lesson-analysis.json').write_bytes(analysis)
    print('Appendix K analysis identical to the archived JSON.')


def save_rows(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as file:
        w = csv.writer(file)
        w.writerow(fields)
        w.writerows(rows)


def changes(out):
    inputs = load(REFERENCE / 'code-sources.json')
    results = defaultdict(Counter)
    missing = Counter()
    with zipfile.ZipFile(DATA / 'strategy-change-codes.zip') as z:
        for member, source in inputs.items():
            study, filename = member.split('/')
            lesson, coder, _ = filename.split('.')
            arm = lesson.split('-')[1][:-1]
            key = study, arm, coder
            results[key]['lessons'] += 1
            if source['status'] == 'failed':
                missing[key] += 1
                continue
            data = z.read(member)
            require(digest(data) == source['sha256'], f'Code differs: {member}')
            c = json.loads(data)
            require(c['coder'] == coder and c['lesson'] in source['source'].split('/')[-1], f'Wrong code identity: {member}')
            results[key].update({
                'made': c['made'] == 'yes',
                'held': c['heldOutcome'] == 'yes',
                'tone': c['made'] == 'yes' and 'tone' in (c['change_kind'] or ''),
                'learner_directed': c['learner_directed_change'] == 'yes',
                'inference': c['inference_handed_over'] == 'yes',
            })
    fields = ['lessons','made','held','tone','learner_directed','inference']
    rows = [(*k, *(v[f] for f in fields), missing[k]) for k,v in sorted(results.items())]
    save_rows(out/'findings-9-11.csv', ['study','arm','coder',*fields,'missing_code'], rows)
    expected = load(REFERENCE / 'findings-9-11.json')
    for r in expected:
        v = [results[r['study'],r['arm'],c][r['measure']] for c in CODERS]
        require(v == r['printed'], f"{r['study']} {r['arm']} {r['measure']}: {v} versus {r['printed']}")
    print(f'Findings 9–11: {len(expected)} paired coder counts match the printed comparisons.')


def drama_votes(z, source):
    if source.endswith('.json'):
        records = json.loads(z.read(source))
        votes = [list(row['v'].values()) for row in records]
    else:
        keys = json.loads(z.read(source+'key-private.json'))
        votes = []
        for pair, key in keys.items():
            readings = []
            for coder in ('opus','sol'):
                for order in ('AB','BA'):
                    base = source+'runs/'+pair.removesuffix(':drama')+'--drama-'+coder+'-'+order
                    for suffix in ('','.retry'):
                        member = base+suffix+'/result.json'
                        if member not in z.NameToInfo:
                            continue
                        validation = base+suffix+'/validation.json'
                        if validation in z.NameToInfo and json.loads(z.read(validation))['status'] != 'structurally_checked':
                            continue
                        comparison = json.loads(z.read(member))['comparison']
                        side = comparison[:1] if comparison.startswith(('A ','B ')) else 'tie'
                        on = key['onSideAB']
                        if order == 'BA':
                            on = 'A' if on == 'B' else 'B'
                        readings.append('tie' if side == 'tie' else 'on' if side == on else 'off')
                        break
                    else:
                        readings.append('missing')
            votes.append(readings)
    require(len(votes)==20 and all(len(v)==4 for v in votes), f'Expected 20 pairs with four reading slots: {source}')
    hard = sum(set(v) == {'on'} for v in votes)
    learned = sum(set(v) == {'off'} for v in votes)
    return [hard, learned, len(votes)-hard-learned]


def final_tests(out):
    rows = []
    with zipfile.ZipFile(DATA / 'final-tests.zip') as z:
        for test in load(REFERENCE / 'final-tests.json'):
            records = json.loads(z.read(test['coding']))
            groups = defaultdict(list)
            for name, r in records.items():
                if name+'-x' in records:
                    continue
                arm = name.split('-')[1]
                groups[arm.startswith(test['learnedArmPrefix'])].append(r)
            require(len(groups[True]) == len(groups[False]) == 20, f"Incomplete final test {test['test']}")
            counts = [sum(r['byCoder'].get(c,{}).get('made')=='yes' for r in groups[g]) for g in (True,False) for c in CODERS]
            counts.extend(drama_votes(z,test['drama']))
            require(counts == test['expected'], f"Final test {test['test']}: {counts} versus {test['expected']}")
            rows.append([test['test'],test['group'],test['model'],*counts])
    require(len(rows)==18,'Expected 18 final tests')
    save_rows(out/'finding-12.csv',['test','study','model','learned_opus','learned_sol','hardwired_opus','hardwired_sol','drama_hardwired','drama_learned','remaining_pairs'],rows)
    print('Finding 12: 18 final tests match Figure 5 for both coders and the drama pairs.')


def figures(out, work):
    script = work / 'scripts/paper1-figures-proposed.py'
    script.parent.mkdir()
    shutil.copyfile(ROOT / 'scripts' / script.name, script)
    subprocess.run([sys.executable, script], check=True)
    directory = work / 'docs/papers/adaptive-tutor-conduct/figures/arxiv'
    actual = {p.name: digest(p.read_bytes()) for p in directory.glob('*.svg')}
    require(actual == load(REFERENCE / 'figures.sha256.json'), 'Figure SVGs differ from the paper freeze')
    directory.rename(out / 'figures')
    print('All seven SVG figures match the frozen originals.')


def deposit_checks(deposit, out, work):
    view = work / 'archive-view'
    subprocess.run([sys.executable, ROOT/'scripts/deposit_view.py', deposit, view], check=True)
    recovered = observations(view)
    with gzip.open(DATA / 'cited-inputs.json.gz', 'rt') as file:
        require(recovered == json.load(file), 'Observation records differ from the full deposit')
    calculate(recovered)
    print('The full deposit reproduces the observation records for all six cited entries.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New directory for the recomputed results')
    parser.add_argument('--figures', action='store_true', help='Render and verify the paper figures (requires rsvg-convert)')
    parser.add_argument('--deposit', type=Path, help='Verify the observation records against all five unpacked data parts (requires Node.js)')
    args = parser.parse_args()
    out = args.out.resolve()
    require(not out.exists(), f'Choose a new output directory: {out}')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        work = Path(tmp)
        result = work / 'results'
        result.mkdir()
        tables(result,work)
        print('Eight further catalogue entries match the event and coder records. Figure 5 opening means match across 104 sets.')
        with gzip.open(DATA / 'cited-inputs.json.gz', 'rt') as file:
            cited = calculate(json.load(file))
        (result / 'cited-entries.json').write_text(json.dumps(cited, indent=2)+'\n')
        print('All six cited entries match their observation records. All 678 table entries are accounted for.')
        whole_lessons(result,work)
        changes(result)
        final_tests(result)
        if args.figures:
            figures(result,work)
        if args.deposit:
            deposit_checks(args.deposit.resolve(),result,work)
        result.rename(out)
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
