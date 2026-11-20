"""Rebuild Paper 1's retrospective whole-lesson assessment from saved codes.

Usage: python3 scripts/paper1-lesson-analysis.py ARTIFACT_DIR [--allow-partial]
No model calls. Raw inputs and outputs remain outside Git.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

CODERS = ('opus-medium', 'sol-medium')
CODEBOOK_SHA256 = '381abdb1cbba4686df0130d70c15b5e9faba3bda62ac79d0d0976d8048233ec6'
CONTRASTS = (
    ('F1', 'A', 'B'), ('F4', 'E', 'G'), ('F5', 'E', 'K'),
    ('F5', 'E', 'J'), ('F6', 'E', 'R'), ('F7-pilot', 'Z', 'M'),
    ('F7-main', 'TZ', 'TM'), ('F8-pilot', 'A', 'R'),
    ('F8-main', 'A', 'R'), ('F8-opus', 'A', 'R'),
    ('F8-sonnet', 'A', 'R'), ('F1-forty', 'A', 'B'),
)


def load(path):
    return json.loads(path.read_text())


def adapted(code):
    return (code['mismatch']['present'] and code['course_changed'] == 'yes'
            and code['held'] == 'yes' and code['inference_handed_over'] == 'no')


MEASURES = {
    'mismatch': lambda c: c['mismatch']['present'],
    'courseChanged': lambda c: c['course_changed'] == 'yes',
    'kept': lambda c: c['course_changed'] == 'yes' and c['held'] == 'yes',
    'adapted': adapted,
    'handedOver': lambda c: c['inference_handed_over'] == 'yes',
    'noMismatch': lambda c: not c['mismatch']['present'],
    'holdingUnobservable': lambda c: c['course_changed'] == 'yes' and c['held'] == 'na',
}


def agreement(pairs):
    n = len(pairs)
    if not n:
        return None
    left, right = Counter(a for a, b in pairs), Counter(b for a, b in pairs)
    count = sum(a == b for a, b in pairs)
    expected = sum(left[k] * right[k] for k in left.keys() | right.keys()) / n ** 2
    return {'n': n, 'agree': count, 'fraction': count / n,
            'kappa': (count / n - expected) / (1 - expected) if expected < 1 else None}


def paired_endpoint(pairs, baseline, candidate, field):
    """Exact two-sided McNemar test; the unit is a matched pair, not a code."""
    pairs = [g for g in pairs if g[baseline][field] is not None
             and g[candidate][field] is not None]
    plus = sum(g[candidate][field] and not g[baseline][field] for g in pairs)
    minus = sum(g[baseline][field] and not g[candidate][field] for g in pairs)
    discordant = plus + minus
    p = min(1, 2 * sum(math.comb(discordant, i)
                      for i in range(min(plus, minus) + 1)) / 2 ** discordant) if discordant else 1
    return {'pairs': len(pairs), 'candidateOnly': plus, 'baselineOnly': minus,
            'both': sum(g[candidate][field] and g[baseline][field] for g in pairs),
            'neither': sum(not g[candidate][field] and not g[baseline][field] for g in pairs),
            'pairedDifference': (plus - minus) / len(pairs) if pairs else None,
            'exactTwoSidedP': p}


def compare(rows, study, baseline, candidate):
    selected = [r for r in rows if r['study'] == study and r['arm'] in (baseline, candidate)]
    if not selected:
        return None
    if {r['arm'] for r in selected} != {baseline, candidate}:
        raise ValueError(f'{study}: missing contrast arm')
    groups = {}
    for row in selected:
        pair = (row['world'], row['type'], row['draw'])
        group = groups.setdefault(pair, {})
        if row['arm'] in group:
            raise ValueError(f'{study}: duplicate arm in pair {pair}')
        group[row['arm']] = row
    pairs = [g for g in groups.values() if set(g) == {baseline, candidate}
             and g[baseline]['read'] and g[candidate]['read']]
    return {'study': study, 'baseline': baseline, 'candidate': candidate,
            'pairs': len(pairs), 'endpoints': {
                f: paired_endpoint(pairs, baseline, candidate, f)
                for f in ('adapted', 'courseChanged', 'kept', 'deliveryCounted',
                          'opusAdapted', 'solAdapted') if all(f in r for r in selected)}}


def summarize_group(rows):
    complete = [r for r in rows if r['read']]
    comparable = [r for r in complete if r['deliveryCounted'] is not None]
    return {
        'eligible': len(rows), 'read': len(complete),
        **{name: sum(r[name] for r in complete) for name in MEASURES},
        'deliveryCounted': sum(r['deliveryCounted'] for r in rows
                               if r['deliveryCounted'] is not None),
        'deliveryAvailable': sum(r['deliveryCounted'] is not None for r in rows),
        'deliveryAdaptation': {
            'n': len(comparable),
            'both': sum(r['deliveryCounted'] and r['adapted'] for r in comparable),
            'deliveryOnly': sum(r['deliveryCounted'] and not r['adapted'] for r in comparable),
            'adaptationOnly': sum(not r['deliveryCounted'] and r['adapted'] for r in comparable),
            'neither': sum(not r['deliveryCounted'] and not r['adapted'] for r in comparable),
        },
        'binaryAgreement': agreement([(adapted(r['codes'][CODERS[0]]),
                                       adapted(r['codes'][CODERS[1]])) for r in complete]),
        'verdictAgreement': agreement([(r['codes'][CODERS[0]]['verdict'],
                                        r['codes'][CODERS[1]]['verdict']) for r in complete]),
        'courseAgreement': agreement([(r['codes'][CODERS[0]]['course_changed'],
                                       r['codes'][CODERS[1]]['course_changed']) for r in complete]),
        'mismatchAgreement': agreement([(
            r['codes'][CODERS[0]]['mismatch'].get('type', 'none') if r['codes'][CODERS[0]]['mismatch']['present'] else 'none',
            r['codes'][CODERS[1]]['mismatch'].get('type', 'none') if r['codes'][CODERS[1]]['mismatch']['present'] else 'none')
            for r in complete]),
        'byCoder': {coder: {
            'read': sum(coder in r['codes'] for r in rows),
            **{name: sum(fn(r['codes'][coder]) for r in rows if coder in r['codes'])
               for name, fn in MEASURES.items()},
            'verdicts': dict(Counter(r['codes'][coder]['verdict']
                                    for r in rows if coder in r['codes']))}
            for coder in CODERS},
    }


def analyze(root):
    coverage = load(root / 'COVERAGE.json')
    if not coverage:
        raise ValueError('No eligible lessons: no verification performed')
    if len({r['label'] for r in coverage}) != len(coverage):
        raise ValueError('Duplicate coverage label')
    key = load(root / 'coding/key-private.json')['lessons']
    rows, issues = [], []
    for source in coverage:
        row = {k: v for k, v in source.items() if k != 'status'}
        row['codes'] = {}
        kid = key[row['label']]['id']
        packet = load(root / 'public' / row['label'] / 'v4-public-packet.json')
        turns = {t['id']: t for t in packet['turns']}
        for coder in CODERS:
            file = root / 'coding/codes' / f'{kid}.{coder}.json'
            if not file.exists():
                continue
            code = load(file)
            row['codes'][coder] = code
            for field, value in (('lesson', kid), ('coder', coder),
                                 ('codebookSha256', CODEBOOK_SHA256)):
                if code.get(field) != value:
                    issues.append([row['label'], coder, 'wrong identity', field])
            if code['derivedAdapted'] != adapted(code) or adapted(code) != (code['verdict'] == 'adapted'):
                issues.append([row['label'], coder, 'verdict disagrees with fields'])
            mismatch = code['mismatch']
            if mismatch['present']:
                references = [(mismatch['first_turn'], 'learner')]
                references += [(t, 'learner') for t in mismatch['turns']]
                references += [(r['turn'], 'tutor') for r in code['responses']]
                if code['course_changed'] == 'yes':
                    references.append((code['change_turn'], 'tutor'))
                for turn, role in references:
                    if turn not in turns or turns[turn]['role'] != role:
                        issues.append([row['label'], coder, 'wrong turn role', turn, role])
        row['read'] = len(row['codes']) == len(CODERS)
        for field, coder in zip(('opusAdapted', 'solAdapted'), CODERS):
            row[field] = adapted(row['codes'][coder]) if coder in row['codes'] else None
        for name, fn in MEASURES.items():
            row[name] = all(fn(c) for c in row['codes'].values()) if row['read'] else None
        rows.append(row)
    cohorts = {}
    for study in dict.fromkeys(r['study'] for r in rows):
        selected = [r for r in rows if r['study'] == study]
        cohorts[study] = summarize_group(selected)
        for dimension in ('arm', 'type', 'world'):
            cohorts[study][dimension + 's'] = {
                value: summarize_group([r for r in selected if r[dimension] == value])
                for value in dict.fromkeys(r[dimension] for r in selected)}
    paired = [result for contrast in CONTRASTS if (result := compare(rows, *contrast))]
    summary = summarize_group(rows)
    summary.update({'partial': summary['read'] != len(rows), 'cohorts': cohorts,
                    'paired': paired, 'structuralIssues': issues,
                    'attempts': load(root / 'coding/ATTEMPTS.json')['used'],
                    'errors': len(list((root / 'coding/attempts').glob('*.error.json')))})
    return summary, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    summary, rows = analyze(args.root)
    for name, value in [('ANALYSIS.json', summary), ('ROWS.json', rows)]:
        (args.root / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ('eligible', 'read', 'attempts', 'errors',
                                            'binaryAgreement', 'structuralIssues')}, indent=2))
    if summary['structuralIssues']:
        raise SystemExit('Structural issues require review; see ANALYSIS.json')
    if summary['partial'] and not args.allow_partial:
        raise SystemExit('Assessment incomplete; no final result')


if __name__ == '__main__':
    main()
