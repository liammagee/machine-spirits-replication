"""Tests, coder agreement and drama pairs for Findings 9 to 11, from the saved codes and readings."""
import json
import re
from math import comb

CODERS = ('opus-medium', 'sol-medium')
LESSON = re.compile(r'^(P|H|M|SB)-([A-Z0-9]+?)([BCRO])-l(\d+)(-x)?$')


def load_codes(archive, sources):
    """Return {study: {arm: {(world, learner, draw): {coder: code or None}}}}.

    A failed coder response is None and counts as no change, as in the paper.
    A lesson named with -x is the declared replacement for the lesson it follows.
    """
    studies = {}
    replaced = set()
    for member, source in sorted(sources.items()):
        study, filename = member.split('/')
        lesson, coder, _ = filename.split('.')
        world, arm, learner, draw, replacement = LESSON.match(lesson).groups()
        cell = world, learner, int(draw)
        if (study, arm, cell, coder) in replaced:
            continue
        if replacement:
            replaced.add((study, arm, cell, coder))
        code = None if source['status'] == 'failed' else json.loads(archive.read(member))
        studies.setdefault(study, {}).setdefault(arm, {}).setdefault(cell, {})[coder] = code
    return studies


def flag(code, measure):
    if code is None:
        return False
    if measure == 'tone':
        return code['made'] == 'yes' and 'tone' in (code['change_kind'] or '')
    return code[measure] == 'yes'


def lessons(studies, name, coder, measure='made', learner=None, min_draw=None):
    study, arm = name.split('/')
    return {cell: flag(codes[coder], measure) for cell, codes in studies[study][arm].items()
            if (learner is None or cell[1] == learner) and (min_draw is None or cell[2] >= min_draw)}


def sign_test(first_only, second_only):
    """One-sided exact sign test that the first arm is above the second, on discordant pairs."""
    n = first_only + second_only
    return sum(comb(n, k) for k in range(first_only, n+1)) / 2**n if n else 1.0


def fisher_two_sided(a, n1, c, n2):
    total = a + c
    def p(x):
        return comb(n1, x) * comb(n2, total-x) / comb(n1+n2, total)
    observed = p(a)
    return sum(p(x) for x in range(max(0, total-n2), min(n1, total)+1) if p(x) <= observed * (1+1e-9))


def kappa(first, second):
    n = len(first)
    agree = sum(x == y for x, y in zip(first, second))
    pa, pb = sum(first)/n, sum(second)/n
    expected = pa*pb + (1-pa)*(1-pb)
    return agree, ((agree/n - expected) / (1-expected) if expected < 1 else 1.0)


def same_p(computed, printed):
    """Compare a computed p-value or kappa with the printed text at the printed number of decimals."""
    if printed.startswith('< '):
        return computed < float(printed[2:])
    return round(computed, len(printed.split('.')[1])) == float(printed)


def check(spec, studies):
    """Return the computed values for one printed statistic and whether they equal the printed ones."""
    kind, printed = spec['kind'], spec['printed']
    computed, ok = {}, True
    if kind == 'sign':
        pairs, ps = [], []
        for coder in CODERS:
            a = lessons(studies, spec['a'], coder, min_draw=spec.get('min_draw'))
            b = lessons(studies, spec['b'], coder, min_draw=spec.get('min_draw'))
            cells = a.keys() & b.keys()
            first = sum(a[c] and not b[c] for c in cells)
            second = sum(b[c] and not a[c] for c in cells)
            pairs.append([first, second])
            ps.append(sign_test(first, second))
            ok &= 'matched' not in printed or len(cells) == printed['matched']
        computed = {'discordant': pairs, 'p': ps}
        ok &= 'discordant' not in printed or pairs == printed['discordant']
        ok &= all(same_p(p, text) for p, text in zip(ps, printed['p']))
    elif kind == 'fisher':
        ps = []
        for coder in CODERS:
            a = lessons(studies, spec['a'], coder)
            b = lessons(studies, spec['b'], coder)
            ps.append(fisher_two_sided(sum(a.values()), len(a), sum(b.values()), len(b)))
        computed = {'p': ps}
        ok = all(text is None or same_p(p, text) for p, text in zip(ps, printed['p']))
    elif kind == 'kappa':
        first, second = ([v for name in spec['sets'] for _, v in sorted(lessons(studies, name, coder).items())] for coder in CODERS)
        agree, value = kappa(first, second)
        computed = {'lessons': len(first), 'agree': agree, 'kappa': value}
        ok = len(first) == printed['lessons'] and same_p(value, printed['kappa'])
        ok &= 'agree' not in printed or agree == printed['agree']
    elif kind == 'count':
        rows = [lessons(studies, spec['set'], coder, spec.get('measure', 'made'), spec.get('learner')) for coder in CODERS]
        computed = {'lessons': [sum(r.values()) for r in rows], 'of': len(rows[0])}
        ok = computed['lessons'] == printed['lessons'] and computed['of'] == printed['of']
    else:
        raise ValueError(f'Unknown kind: {kind}')
    return computed, bool(ok)


def pair_readings(archive, source):
    """Return {contrast: [four readings per pair]} for one directory of drama readings.

    Each pair is read by two reader families in both orders. A reading is 'on' when it
    prefers the lesson the key names first, 'off' when it prefers the other, or 'tie'.
    """
    keys = json.loads(archive.read(source+'key-private.json'))
    names = set(archive.namelist())
    result = {}
    for pair, key in keys.items():
        readings = []
        for reader in ('opus', 'sol'):
            for order in ('AB', 'BA'):
                base = source+'runs/'+pair.removesuffix(':drama')+'--drama-'+reader+'-'+order
                for suffix in ('', '.retry'):
                    member = base+suffix+'/result.json'
                    if member not in names:
                        continue
                    validation = base+suffix+'/validation.json'
                    if validation in names and json.loads(archive.read(validation))['status'] != 'structurally_checked':
                        continue
                    comparison = json.loads(archive.read(member))['comparison']
                    side = comparison[:1] if comparison.startswith(('A ', 'B ')) else 'tie'
                    on = key['onSideAB']
                    if order == 'BA':
                        on = 'A' if on == 'B' else 'B'
                    readings.append('tie' if side == 'tie' else 'on' if side == on else 'off')
                    break
                else:
                    readings.append('missing')
        result.setdefault(key.get('contrast'), []).append(readings)
    return result


def verdicts(readings):
    """A pair has a verdict only when both reader families give it in both orders."""
    counts = {name: sum(set(r) == {name} for r in readings) for name in ('on', 'off', 'tie')}
    return {'pairs': len(readings), 'first': counts['on'], 'second': counts['off'], 'tie': counts['tie'],
            'no_verdict': len(readings) - sum(counts.values())}


DISRUPTIVE = ('parable', 'humour', 'sarcasm', 'challenge', 'reverse-advocacy')


def fisher_above(a, n1, b, n2):
    """One-sided Fisher's exact test that the first proportion is above the second."""
    total = a + b
    return sum(comb(total, x) * comb(n1+n2-total, n1-x) for x in range(a, min(total, n1)+1)) / comb(n1+n2, n1)


def delivery_rows(archive, source):
    """One row for each coded reply: its arm, strategy, position and each coder's delivery code."""
    names = set(archive.namelist())
    rows = []
    for item in json.loads(archive.read(source+'key-private.json'))['items'].values():
        members = [source+'codes/'+item['id']+'.'+coder+'.json' for coder in CODERS]
        if not all(m in names for m in members):
            continue
        rows.append({'arm': item['set'].split()[-1], 'strategy': item['strategy'], 'position': item['position'],
                     'by': {coder: json.loads(archive.read(m))['delivered'] for coder, m in zip(CODERS, members)}})
    return rows


def delivery_check(spec, rows):
    """Replies coded as carried out, layered arm then the arm without the actor's texts."""
    groups = {'disruptive': DISRUPTIVE, 'sarcasm': ('sarcasm',), 'other disruptive': tuple(s for s in DISRUPTIVE if s != 'sarcasm')}
    strategies = groups[spec['strategies']]
    coders = CODERS if spec.get('coder', 'both') == 'both' else (spec['coder'],)
    counts = []
    for arm in ('layered', 'without'):
        chosen = [r for r in rows if r['arm'] == arm and r['strategy'] in strategies
                  and spec.get('position') in (None, r['position'])]
        counts.append([sum(all(r['by'][c] == 'yes' for c in coders) for r in chosen), len(chosen)])
    p = fisher_above(*counts[0], *counts[1])
    printed = spec['printed']
    ok = counts == [printed['layered'], printed['without']] and ('p' not in printed or same_p(p, printed['p']))
    return {'layered': counts[0], 'without': counts[1], 'p': p}, ok


def line_counts(archive, source, strategy, version):
    """Replies drawn with one wording of a strategy's line: how many, and how many each coder coded as carried out."""
    counts = {'replies': 0, 'both': 0, 'opus': 0, 'sol': 0}
    for item in json.loads(archive.read(source+'key-private.json'))['items'].values():
        if (item['strategy'], item['version']) != (strategy, version):
            continue
        opus, sol = (json.loads(archive.read(source+'codes/'+item['id']+'.'+coder+'.json'))['delivered'] == 'yes' for coder in CODERS)
        counts['replies'] += 1
        counts['both'] += opus and sol
        counts['opus'] += opus
        counts['sol'] += sol
    return counts
