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
from scripts.change_tests import check, delivery_check, delivery_rows, line_counts, load_codes, pair_readings, sign_test, same_p, verdicts

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


def change_tests(out):
    """Sign tests, Fisher tests, coder agreement and counts by learner type printed for Findings 9 to 11."""
    with zipfile.ZipFile(DATA / 'strategy-change-codes.zip') as z:
        studies = load_codes(z, load(REFERENCE / 'code-sources.json'))
    sources = load(REFERENCE / 'without-actor-code-sources.json')
    with zipfile.ZipFile(DATA / 'without-actor-texts-codes.zip') as z:
        for member, source in sources.items():
            require(digest(z.read(member)) == source['sha256'], f'Code differs: {member}')
        studies.update(load_codes(z, sources))
    specs = load(REFERENCE / 'findings-9-11-tests.json')
    rows = []
    for spec in specs:
        computed, ok = check(spec, studies)
        require(ok, f"{spec['where']}, {spec['what']}: {computed} versus {spec['printed']}")
        rows.append([spec['where'], spec['what'], spec['kind'], json.dumps(spec['printed']), json.dumps(computed)])
    save_rows(out/'findings-9-11-tests.csv', ['where','statistic','kind','printed','computed'], rows)
    print(f'Findings 9–11: {len(specs)} printed tests, agreement figures and counts match the saved codes.')


def drama_pairs(out):
    """Drama-pair results printed for Findings 9 to 11, from the saved readings of both reader families."""
    specs = load(REFERENCE / 'findings-9-11-drama.json')
    sources = load(REFERENCE / 'drama-sources.json')
    rows = []
    with zipfile.ZipFile(DATA / 'drama-readings-9-11.zip') as z:
        require(set(z.namelist()) == set(sources), 'Drama readings differ from the listed files')
        for member, expected in sources.items():
            require(digest(z.read(member)) == expected, f'Drama reading differs: {member}')
        for spec in specs:
            counts = verdicts(pair_readings(z, spec['source'])[spec['contrast']])
            printed = dict(spec['printed'])
            p = printed.pop('p_two_sided', None)
            require(all(counts[k] == v for k, v in printed.items()), f"{spec['where']}, {spec['first']} against {spec['second']}: {counts} versus {printed}")
            require(p is None or same_p(min(1, 2*sign_test(max(counts['first'], counts['second']), min(counts['first'], counts['second']))), p), f"{spec['where']}: two-sided p differs from {p}")
            rows.append([spec['where'], spec['first'], spec['second'], *counts.values()])
    save_rows(out/'findings-9-11-drama.csv', ['where','first_lesson','second_lesson','pairs','first_preferred','second_preferred','tie','no_verdict'], rows)
    print(f'Findings 9–11: {len(specs)} drama-pair results match the saved readings.')


def without_actor_delivery(out):
    """Replies carried out, with and without the actor's texts, from the saved delivery codes."""
    specs = load(REFERENCE / 'without-actor-texts-delivery.json')
    sources = load(REFERENCE / 'delivery-sources.json')
    rows, cache = [], {}
    with zipfile.ZipFile(DATA / 'without-actor-texts-codes.zip') as z:
        for member, expected in sources.items():
            require(digest(z.read(member)) == expected, f'Delivery code differs: {member}')
        def coded(source):
            if source not in cache:
                cache[source] = delivery_rows(z, source)
            return cache[source]
        for spec in specs:
            if spec['kind'] == 'total':
                computed = sum(len(coded(s)) for s in spec['sources'])
                ok = computed == spec['printed']
            else:
                computed, ok = delivery_check(spec, coded(spec['source']))
            require(ok, f"{spec['what']}: {computed} versus {spec['printed']}")
            rows.append([spec['what'], json.dumps(spec['printed']), json.dumps(computed)])
    save_rows(out/'without-actor-texts-delivery.csv', ['count','printed','computed'], rows)
    print(f"Without the actor's texts: {len(specs)} printed delivery counts match the saved codes.")


def strategy_lines(out):
    """Finding 12: replies carried out at saved moments under the present and the new strategy lines."""
    specs = load(REFERENCE / 'finding-12-strategy-lines.json')
    rows = []
    with zipfile.ZipFile(DATA / 'strategy-line-codes.zip') as z:
        for member, expected in load(REFERENCE / 'strategy-line-sources.json').items():
            require(digest(z.read(member)) == expected, f'Strategy-line code differs: {member}')
        for spec in specs:
            counts = line_counts(z, spec['source'], spec['strategy'], spec['version'])
            require(all(counts[k] == v for k, v in spec['printed'].items()), f"{spec['what']}: {counts} versus {spec['printed']}")
            rows.append([spec['what'], spec['version'], *counts.values()])
    save_rows(out/'finding-12-strategy-lines.csv', ['line','wording','replies','both_coders','opus','sol'], rows)
    print(f'Finding 12: {len(specs)} strategy-line counts at saved moments match the saved codes.')


def drama_votes(z, source):
    if source.endswith('.json'):
        records = json.loads(z.read(source))
        votes = [list(row['v'].values()) for row in records]
    else:
        votes = [readings for group in pair_readings(z, source).values() for readings in group]
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
    with zipfile.ZipFile(DATA / 'drama-readings-9-11.zip') as z:
        for member in z.namelist():
            require((deposit / member).read_bytes() == z.read(member), f'Drama reading differs from the full deposit: {member}')
        print(f'All {len(z.namelist())} drama reading files for Findings 9–11 are identical to the full deposit.')
    with zipfile.ZipFile(DATA / 'without-actor-texts-codes.zip') as z:
        for member, source in load(REFERENCE / 'without-actor-code-sources.json').items():
            require((deposit / source['source']).read_bytes() == z.read(member), f'Code differs from the full deposit: {member}')
        for member in load(REFERENCE / 'delivery-sources.json'):
            require((deposit / member).read_bytes() == z.read(member), f'Delivery code differs from the full deposit: {member}')
        print(f"All {len(z.namelist())} code files for the lessons without the actor's texts are identical to the full deposit.")
    with zipfile.ZipFile(DATA / 'strategy-line-codes.zip') as z:
        for member in z.namelist():
            require((deposit / member).read_bytes() == z.read(member), f'Strategy-line code differs from the full deposit: {member}')
        print(f'All {len(z.namelist())} strategy-line code files are identical to the full deposit.')


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
        change_tests(result)
        drama_pairs(result)
        without_actor_delivery(result)
        strategy_lines(result)
        final_tests(result)
        if args.figures:
            figures(result,work)
        if args.deposit:
            deposit_checks(args.deposit.resolve(),result,work)
        result.rename(out)
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
