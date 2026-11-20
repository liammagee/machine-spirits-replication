#!/usr/bin/env python3
"""Paper 1's tables and reported numbers, recomputed from the reference score catalogue. No model calls.

    python3 scripts/paper1-tables.py --db <reference.sqlite> [--table TEXT] [--out DIR]

The list of numbers is the data file docs/papers/adaptive-tutor-conduct/paper1-numbers.json. Each entry gives the
table, row and column, the value printed in MANUSCRIPT-v2.md (or in the source PR or knowledge entry for results the
manuscript does not yet include), and a query. This script runs each query against the lab_ tables written by
scripts/import-run-archive.py, formats the result the way the manuscript prints it, and compares the two.

It writes, in --out (default docs/papers/adaptive-tutor-conduct/tables/):
  one Markdown and one CSV file per table, with printed and recomputed values side by side;
  CHECK.md: every number, mismatches first, then numbers whose runs are not in the database.
A mismatch is reported, never changed. --table limits the output to tables whose title contains TEXT.
The G1 and G2 rows show the published code count; the rows "G1 corrected count" and "G2 corrected count (programme item 11)" show each correction
stored in lab_guards under another method or version, or "not yet" while none exists.
"""
import argparse
import csv
import json
import math
import re
import sqlite3
from contextlib import closing
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NUMBERS = REPO / 'docs/papers/adaptive-tutor-conduct/paper1-numbers.json'
OUT = REPO / 'docs/papers/adaptive-tutor-conduct/tables'
# As in scripts/drama-v2-confirm.mjs DISRUPTIVE.
DISRUPTIVE = ['sarcasm', 'humour', 'challenge', 'parable', 'reverse-advocacy', 'role-reversal']
TYPES = ['B', 'C', 'R', 'O']
CODERS = 2


def truth(x):
    return int(bool(x)) if isinstance(x, bool) else len(x) if isinstance(x, list) else (x or 0)


class Catalogue:
    def __init__(self, db):
        self.db = db
        self._lessons = {}

    def lessons(self, run, arm=None, included=True, ltype=None):
        key = (run, arm, included, ltype)
        if key not in self._lessons:
            q = 'SELECT lesson_id, arm, learner_type, included, complete, report_json, in_report FROM lab_lessons WHERE run_id=?'
            rows = [dict(id=r[0], arm=r[1], type=r[2], included=r[3], complete=r[4], rep=json.loads(r[5]) if r[5] else {}, in_report=r[6])
                    for r in self.db.execute(q, (run,))]
            reported = any(r['in_report'] for r in rows)
            rows = [r for r in rows if r['in_report'] or not reported]
            rows = [r for r in rows if (arm is None or r['arm'] == arm) and (not included or r['included']) and (ltype is None or r['type'] == ltype)]
            self._lessons[key] = rows
        return self._lessons[key]

    def value(self, c):
        k = c['kind']
        run, arm = c.get('run'), c.get('arm')
        if k == 'counted':
            field = c.get('field', 'counted')
            mine = self.lessons(run, arm, ltype=c.get('type'))
            # atLeast: a numeric field (a run length) counts when it is at least this value.
            yes = sum(1 for l in mine if (truth(l['rep'].get(field)) >= c['atLeast'] if 'atLeast' in c else l['rep'].get(field)))
            n = len(self.lessons(run, arm, included=False, ltype=c.get('type'))) if c.get('lostAsFailures') else len(mine)
            return yes if c.get('value') == 'yes' else (yes, n)
        if k == 'starts':
            mine = self.lessons(run, arm, ltype=c.get('type'))
            x = sum(1 for l in mine if l['rep'].get('firstDisruptive'))
            return (x, len(mine)) if c.get('value') == 'of' else x
        if k == 'codes':
            strategies = c.get('strategies', DISRUPTIVE)
            yes = n = pob = 0
            for r_ in c.get('runs', [run]):
                ids = {l['id'] for l in self.lessons(r_, arm)}
                q = ("SELECT lesson_id, strategy, MIN(delivered='yes'), COUNT(*), MIN(delivered IN ('yes','part')), unit_id, position, label "
                     'FROM lab_codes WHERE run_id=? AND codebook=? GROUP BY label')
                rows = [r for r in self.db.execute(q, (r_, c.get('codebook', 'delivery')))
                        if r[3] == CODERS and r[0] in ids and (strategies == 'any' or r[1] in strategies)
                        and (c.get('position') is None or r[6] == c['position']) and (c.get('unit') is None or r[5] == c['unit'])
                        and not (c.get('excludeLabel') and c['excludeLabel'] in r[7])]
                if c.get('inForce'):
                    # Only replies at which the coded strategy was in force (the strategy step had not switched away).
                    force = {(a_, u): s for a_, u, s in self.db.execute('SELECT lesson_id, unit_id, in_force FROM lab_replies WHERE run_id=?', (r_,))}
                    rows = [r for r in rows if force.get((r[0], r[5])) == r[1]]
                if c.get('labelsOf'):
                    # The same replies as another codebook's items (labels compared without their last part).
                    same = {x[0].rsplit(':', 1)[0] for x in self.db.execute('SELECT DISTINCT label FROM lab_codes WHERE run_id=? AND codebook=?', (r_, c['labelsOf']))}
                    rows = [r for r in rows if r[7] in same]
                yes, n, pob = yes + sum(r[2] for r in rows), n + len(rows), pob + sum(r[4] for r in rows)
            if c.get('value') == 'n':
                return n
            if c.get('value') == 'yes':
                return yes
            return (pob, n) if c.get('value') == 'pob' else (yes, n)
        if k == 'complaints':
            mine = self.lessons(run, arm)
            items = [x for l in mine for x in l['rep'].get('complaints', [])]
            held = sum(1 for x in items if x.get('held'))
            return held if c.get('value') == 'held' else (held, len(items)) if c.get('value') == 'heldOf' else len(items)
        if k == 'lessonsum':
            return sum(truth(l['rep'].get(c['field'])) for l in self.lessons(run, arm))
        if k == 'lessonsWith':
            mine = self.lessons(run, arm, ltype=c.get('type'))
            x = sum(1 for l in mine if truth(l['rep'].get(c['field'])) > 0)
            return x if c.get('value') == 'yes' else (x, len(mine))
        if k == 'guard':
            # version: 'published' (default) or a correction stored beside it (programme item 11). forks: count the
            # complete forks of the arm, as the 'fork' kind does.
            mine = self.lessons(run, arm, included=not c.get('forks'))
            ids = {l['id'] for l in mine if not c.get('forks') or l['rep'].get('complete')}
            q = "SELECT lesson_id, value FROM lab_guards WHERE run_id=? AND guard=? AND method='code' AND version=?"
            return sum(v for i, v in self.db.execute(q, (run, c['guard'], c.get('version', 'published'))) if i in ids)
        if k == 'guardCorrected':
            ids = {l['id'] for l in self.lessons(run, arm)}
            q = "SELECT method, version, lesson_id, value FROM lab_guards WHERE run_id=? AND guard=? AND NOT (method='code' AND version='published')"
            out = {}
            for method, version, i, v in self.db.execute(q, (run, c['guard'])):
                if i in ids:
                    out[f'{method} {version}'] = out.get(f'{method} {version}', 0) + v
            return '; '.join(f'{k2}: {v}' for k2, v in sorted(out.items())) or 'not yet'
        if k == 'cmh' and c.get('runs'):
            # Pooled over runs: one stratum per run and learner type.
            strata = []
            for r_ in c['runs']:
                for t in TYPES:
                    a, b = self.lessons(r_, c['A'], ltype=t), self.lessons(r_, c['B'], ltype=t)
                    if a and b:
                        strata.append((len(a), len(b), sum(1 for l in a if l['rep'].get(c['field'])), sum(1 for l in b if l['rep'].get(c['field']))))
            return cmh(strata)[c['stat']]
        if k == 'cmh':
            strata = []
            for t in TYPES:
                a, b = self.lessons(run, c['A'], ltype=t), self.lessons(run, c['B'], ltype=t)
                na, nb = len(a), len(b)
                if c.get('lostAsFailures'):
                    na, nb = len(self.lessons(run, c['A'], included=False, ltype=t)), len(self.lessons(run, c['B'], included=False, ltype=t))
                if na and nb:
                    strata.append((na, nb, sum(1 for l in a if l['rep'].get(c['field'])), sum(1 for l in b if l['rep'].get(c['field']))))
            return cmh(strata)[c['stat']]
        if k == 'fisher':
            a = self.lessons(run, c['fewer'])
            b = self.lessons(run, c['than'])
            return fisher_less(sum(1 for l in a if truth(l['rep'].get(c['field'])) > 0), len(a),
                               sum(1 for l in b if truth(l['rep'].get(c['field'])) > 0), len(b))
        if k == 'replies':
            ids = {l['id'] for l in self.lessons(run, arm)}
            rows = [r for r in self.db.execute('SELECT lesson_id, in_force FROM lab_replies WHERE run_id=?', (run,)) if r[0] in ids]
            return (sum(1 for r in rows if r[1] == c['inForce']), len(rows))
        if k == 'sign':
            # One-sided sign test over the pairs with an 'on' or 'off' verdict (ties and no verdict left out): P(on or more of n).
            on, off = (self.value({**c, 'kind': 'drama', 'verdict': v}) for v in ('on', 'off'))
            n_ = on + off
            return sum(math.comb(n_, i) for i in range(on, n_ + 1)) / 2 ** n_
        if k == 'drama':
            votes = {}
            for pair, verdict in self.db.execute('SELECT pair_id, verdict FROM lab_drama_verdicts WHERE run_id=? ORDER BY family, reading_order', (run,)):
                votes.setdefault(pair, []).append(verdict)
            pairs = {p: (ct, lr) for p, ct, lr in self.db.execute('SELECT pair_id, contrast, learner FROM lab_drama_pairs WHERE run_id=?', (run,))}
            total = 0
            for p, v in votes.items():
                ct, lr = pairs[p]
                if c.get('contrast') and ct != c['contrast'] or c.get('learner') and lr != c['learner']:
                    continue
                combined = v[0] if len(v) == 4 and all(x and x != 'unread' and x == v[0] for x in v) else 'no verdict'
                total += combined == c['verdict']
            return total
        if k == 'fork':
            mine = [l for l in self.lessons(run, arm, included=False) if l['rep'].get('complete')]
            if c.get('strategy'):
                mine = [l for l in mine if l['rep'].get('strategy') == c['strategy']]
                return (sum(1 for l in mine if l['rep'].get('counted')), len(mine))
            v = c['value']
            if v in ('yes', 'part', 'no'):
                return sum(1 for l in mine if l['rep'].get('delivered') == v)
            return sum(truth(l['rep'].get(v)) for l in mine)
        if k == 'firstDisruptive':
            # One reply per lesson: the first reply of the lesson's first disruptive strategy (the report's firstDisruptive).
            fd = [l['rep']['firstDisruptive'] for l in self.lessons(run, arm) if l['rep'].get('firstDisruptive')]
            return (sum(1 for x in fd if x.get('bothYes')), len(fd))
        if k == 'kept2':
            # Lessons in which one disruptive strategy was in force at 2 or more consecutive replies, whatever the codes,
            # and how many of them count on the counted measure.
            kept = []
            for l in self.lessons(run, arm):
                seq = [r[0] for r in self.db.execute('SELECT in_force FROM lab_replies WHERE run_id=? AND lesson_id=? ORDER BY position', (run, l['id']))]
                if any(a == b and a in DISRUPTIVE for a, b in zip(seq, seq[1:])):
                    kept.append(l)
            return (sum(1 for l in kept if l['rep'].get('counted')), len(kept))
        if k == 'ratio':
            num, den = self.value(c['num']), self.value(c['den'])
            return (num if not isinstance(num, tuple) else num[0], den if not isinstance(den, tuple) else den[-1])
        if k == 'replyAt':
            mine = self.lessons(run, arm)
            ids = {l['id'] for l in mine}
            hits = {r[0] for r in self.db.execute('SELECT lesson_id FROM lab_replies WHERE run_id=? AND unit_id=? AND in_force=?', (run, c['unit'], c['inForce'])) if r[0] in ids}
            return (len(hits), len(mine))
        if k == 'switchesTo':
            ids = {l['id'] for l in self.lessons(run, arm)}
            rows = [r for r in self.db.execute('SELECT lesson_id, in_force FROM lab_replies WHERE run_id=? AND outcome=?', (run, c.get('outcome', 'switched'))) if r[0] in ids]
            return (sum(1 for r in rows if r[1] in c.get('strategies', DISRUPTIVE)), len(rows))
        if k == 'changes':
            ids = {l['id'] for l in self.lessons(run, arm)}
            return sum(1 for r in self.db.execute('SELECT lesson_id, before_strategy, in_force FROM lab_replies WHERE run_id=?', (run,)) if r[0] in ids and r[1] != r[2])
        if k == 'repliesWhere':
            # outcome: the strategy step's outcome; last: only the lesson's last reply.
            ids = {l['id'] for l in self.lessons(run, arm)}
            rows = [r for r in self.db.execute('SELECT lesson_id, reading, before_strategy, in_force, outcome, position FROM lab_replies WHERE run_id=?', (run,)) if r[0] in ids]
            last = {}
            for r in rows:
                last[r[0]] = max(last.get(r[0], r[5]), r[5])
            rows = [r for r in rows if (c.get('reading') is None or r[1] == c['reading']) and (c.get('inForce') is None or r[3] == c['inForce'])
                    and (not c.get('kept') or r[2] == r[3]) and (c.get('outcome') is None or r[4] == c['outcome'])
                    and (not c.get('last') or r[5] == last[r[0]])]
            return len(rows)
        if k == 'assigned':
            n = y = 0
            for l in self.lessons(run, arm, included=False):
                ids = {x['reply'] if isinstance(x, dict) else x for x in (l['rep'].get('assignedByRule') or [])}
                for x in l['rep'].get('rows', []):
                    if x['reply'] in ids:
                        n += 1
                        y += bool(x.get('bothYes'))
            return (y, n)
        if k == 'replyClass':
            # Rows of a per-reply table in the repository (a hand reading, e.g. docs/actor-follow-through/later-replies.tsv,
            # PR 1284) matching `where`; carried out is recomputed from lab_codes (both coders yes on the row's label).
            rows = list(csv.DictReader(open(REPO / c['file'], encoding='utf-8'), delimiter='\t'))
            rows = [r for r in rows if all(r.get(f) == v for f, v in c.get('where', {}).items())]
            q = "SELECT MIN(delivered='yes'), COUNT(*) FROM lab_codes WHERE run_id=? AND codebook='delivery' AND label=?"
            yes = 0
            for r in rows:
                both, coders = self.db.execute(q, (run, r['label'])).fetchone()
                yes += bool(both) and coders == CODERS
            return len(rows) if c.get('value') == 'n' else (yes, len(rows))
        if k == 'readings':
            return self.readings(c)
        if k == 'pairsKept':
            return self.pairs_kept(c)
        if k == 'pairsStart':
            votes = self.pair_verdicts(run)
            started = {l['id']: bool(l['rep'].get('firstDisruptive')) for l in self.lessons(run)}
            n = 0
            for p, (on, off, verdict) in votes.items():
                if on in started and off in started and started[off] and not started[on]:
                    n += verdict == c['verdict']
            return n
        if k == 'kappa':
            return self.kappa(c)
        if k == 'cited':
            row = self.db.execute('SELECT value_text FROM lab_cited WHERE cited_id=?', (c['id'],)).fetchone()
            return row[0] if row else None
        if k == 'notInDatabase':
            return None
        raise SystemExit(f'Unknown query kind {k}')

    def subjects(self, run, prefix, method=None):
        """lab_readings rows under one measure prefix, pivoted to {subject: {field: value, '_detail': {...}}}."""
        out = {}
        q = 'SELECT subject_id, measure, value_num, value_text, detail_json, method FROM lab_readings WHERE run_id=? AND measure LIKE ?'
        for s, m, num, text, detail, meth in self.db.execute(q, (run, prefix + '%')):
            if method and method not in meth:
                continue
            d = out.setdefault(s, {})
            d[m[len(prefix):]] = num if num is not None else text
            if detail:
                d['_detail'] = json.loads(detail)
        return out

    def readings(self, c):
        """Count readings: subjects under `prefix` matching `where` (fields, or detail fields with `detail.`), optionally
        only subjects that are included lessons of `arm` (`armVia: lesson`), or whose text field contains `contains`."""
        run = c['run']
        subs = self.subjects(run, c['prefix'], c.get('method'))
        ids = {l['id']: l['arm'] for l in self.lessons(run)} if c.get('armVia') == 'lesson' else None

        def ok(s, d):
            if c.get('subjects') and s not in c['subjects']:
                return False
            for f, v in c.get('where', {}).items():
                got = d.get('_detail', {}).get(f[7:]) if f.startswith('detail.') else d.get(f)
                if isinstance(v, bool):
                    got = bool(got) if got is not None else None
                if isinstance(v, list):
                    if got not in v:
                        return False
                elif isinstance(v, dict) and 'not' in v:
                    if got == v['not']:
                        return False
                elif got != v:
                    return False
            if ids is not None and (s not in ids or (c.get('arm') and ids[s] != c['arm'])):
                return False
            if c.get('contains') and c['contains'][1] not in str(d.get(c['contains'][0], '')):
                return False
            return True

        mine = [d for s, d in subs.items() if ok(s, d)]
        if c.get('value') == 'ypn':
            return tuple(sum(1 for d in mine if d.get(c['field']) == x) for x in ('yes', 'part', 'no')) + (len(mine),)
        if c.get('value') == 'of':
            return (sum(1 for d in mine if d.get(c['field']) == c['equals']), len(mine))
        if c.get('value') == 'sum':
            total = sum(d.get(c['field']) or 0 for d in mine)
            return int(total) if float(total).is_integer() else total
        return len(mine)

    def pair_verdicts(self, run):
        votes = {}
        for pair, verdict in self.db.execute('SELECT pair_id, verdict FROM lab_drama_verdicts WHERE run_id=? ORDER BY family, reading_order', (run,)):
            votes.setdefault(pair, []).append(verdict)
        out = {}
        for p, on, off in self.db.execute('SELECT pair_id, on_lesson, off_lesson FROM lab_drama_pairs WHERE run_id=?', (run,)):
            v = votes.get(p, [])
            out[p] = (on, off, v[0] if len(v) == 4 and all(x and x != 'unread' and x == v[0] for x in v) else 'no verdict')
        return out

    def kept_runs(self, run, lesson):
        """Strategies (not ordinary) in force at 2 or more consecutive replies, as scripts/keep-line-drama-why.py runs()."""
        seq = [r[0] for r in self.db.execute('SELECT in_force FROM lab_replies WHERE run_id=? AND lesson_id=? ORDER BY position', (run, lesson))]
        return {a for a, b in zip(seq, seq[1:]) if a == b and a not in (None, 'ordinary')}

    def pairs_kept(self, c):
        run, n = c['run'], 0
        for p, (on, off, verdict) in self.pair_verdicts(run).items():
            same = self.kept_runs(run, on) & self.kept_runs(run, off)
            hit = ('gravity' in same) if c['strategies'] == 'gravity' else bool(same & set(DISRUPTIVE))
            n += hit and (c.get('verdict') is None or verdict == c['verdict'])
        return n

    def kappa(self, c):
        subs = self.subjects(c['run'], 'verdict.')
        norm = lambda v: v if v in ('S', 'B3') else 'neither'
        pairs = [(norm(d[c['a']]), norm(d[c['b']])) for d in subs.values() if c['a'] in d and c['b'] in d]
        n = len(pairs)
        po = sum(a == b for a, b in pairs) / n
        cats = {x for p in pairs for x in p}
        pe = sum((sum(a == k for a, _ in pairs) / n) * (sum(b == k for _, b in pairs) / n) for k in cats)
        return (po - pe) / (1 - pe)


def cmh(strata):
    """One-sided Cochran-Mantel-Haenszel test and the weighted risk difference, as scripts/drama-v2-forty.mjs cmh."""
    num = var = w_sum = rd = rd_var = 0.0
    for na, nb, ya, yb in strata:
        n, m1 = na + nb, ya + yb
        num += yb - nb * m1 / n
        var += na * nb * m1 * (n - m1) / (n * n * (n - 1)) if n > 1 else 0
        w = na * nb / n
        pa, pb = ya / na, yb / nb
        w_sum += w
        rd += w * (pb - pa)
        rd_var += w * w * (pa * (1 - pa) / na + pb * (1 - pb) / nb)
    z = num / math.sqrt(var) if var > 0 else 0
    diff, se = rd / w_sum, math.sqrt(rd_var) / w_sum
    return {'z': z, 'p': 1 - normal_cdf(z), 'difference': diff, 'interval': (diff - 1.96 * se, diff + 1.96 * se)}


def normal_cdf(z):
    """The same polynomial approximation as scripts/drama-v2-forty.mjs normalCdf."""
    t = 1 / (1 + 0.2316419 * abs(z))
    d = 0.3989423 * math.exp(-z * z / 2)
    q = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1 - q if z > 0 else q


def fisher_less(a, n1, c, n2):
    """One-sided Fisher exact test, as scripts/fidelity-push.mjs fisherLess: P(first group has at most a events)."""
    k, total = a + c, n1 + n2
    lc = lambda n: sum(math.log(i) for i in range(2, n + 1))
    ch = lambda n, r: lc(n) - lc(r) - lc(n - r)
    return min(1, sum(math.exp(ch(n1, x) + ch(n2, k - x) - ch(total, k)) for x in range(max(0, k - n2), min(a, k) + 1)))


def minus(text):
    return text.replace('-', '−')


def fmt(value, how):
    if value is None:
        return None
    if how == 'int':
        return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    if how == 'of':
        return f'{value[0]} of {value[1]}'
    if how == 'ofpct':
        return f'{value[0]} of {value[1]} ({round(100 * value[0] / value[1])}%)'
    if how == 'ofpct1':
        return f'{value[0]} of {value[1]} ({100 * value[0] / value[1]:.1f}%)'
    if how == 'pct':
        return f'{round(100 * value[0] / value[1])}%'
    if how == 'f2':
        return minus(f'{value:.2f}')
    if how == 'f3':
        return minus(f'{value:.3f}')
    if how == 'interval2':
        return minus(f'{value[0]:.2f} to {value[1]:.2f}')
    if how == 'ypn':
        return f'{value[0]} / {value[1]} / {value[2]} of {value[3]}'
    if how == 'f4':
        return minus(f'{value:.4f}')
    if how == 'f5':
        return minus(f'{value:.5f}')
    if how == 'f6':
        return minus(f'{value:.6f}')
    if how == 'plt':
        return '< 0.0001' if value < 0.0001 else f'{value:.4f}'
    return str(value)


def slug(title):
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:70]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--numbers', type=Path, default=NUMBERS)
    p.add_argument('--out', type=Path, default=OUT)
    p.add_argument('--table', help='Only tables whose title contains this text')
    a = p.parse_args()
    numbers = json.loads(a.numbers.read_text(encoding='utf8'))['numbers']
    if a.table:
        numbers = [x for x in numbers if a.table.lower() in x['table'].lower()]
    with closing(sqlite3.connect(f'file:{a.db}?mode=ro', uri=True)) as db:
        cat = Catalogue(db)
        corrections = {}
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='lab_readings'").fetchone():
            for s, version, value, detail in db.execute("SELECT subject_id, version, value_text, detail_json FROM lab_readings WHERE subject_kind='reported-number' AND measure='printed'"):
                corrections.setdefault(s, {})[version] = (value, json.loads(detail) if detail else {})
        rows = []
        for x in numbers:
            got = fmt(cat.value(x['calc']), x['format'])
            printed = None if x['printed'] is None else str(x['printed'])
            fixed = sorted(v for v in corrections.get(x['id'], {}) if v.startswith('corrected'))
            if fixed:
                value, detail = corrections[x['id']][fixed[-1]]
                x = {**x, 'source': f"{x['source']}. Corrected from {printed} ({fixed[-1]}): {detail.get('note', '')}"}
                printed = value
            status = ('not in database' if x['calc']['kind'] == 'notInDatabase' else 'no printed value' if printed is None
                      else ('cited, ' if x['calc']['kind'] == 'cited' else '') + ('match' if got == printed else 'MISMATCH'))
            rows.append({**x, 'recomputed': got, 'printedText': printed, 'status': status})
    a.out.mkdir(parents=True, exist_ok=True)
    tables = {}
    for r in rows:
        tables.setdefault(r['table'], []).append(r)
    for title, items in tables.items():
        name = slug(title)
        with open(a.out / f'{name}.csv', 'w', newline='', encoding='utf8') as f:
            w = csv.writer(f)
            w.writerow(['row', 'column', 'printed', 'recomputed', 'status', 'source'])
            for r in items:
                w.writerow([r['row'], r['col'], r['printedText'] or '', r['recomputed'] or '', r['status'], r['source']])
        lines = [f'# {title}', '', f'Recomputed from the reference score catalogue by `python3 scripts/paper1-tables.py --db <reference> --table "{title}"`.',
                 'Each cell is the recomputed value; "printed" gives the value in the manuscript or source when it differs or is not in the database.', '']
        cols = list(dict.fromkeys(r['col'] for r in items))
        lines.append('| | ' + ' | '.join(cols) + ' |')
        lines.append('|---' * (len(cols) + 1) + '|')
        for row in dict.fromkeys(r['row'] for r in items):
            cells = []
            for col in cols:
                r = next((r for r in items if r['row'] == row and r['col'] == col), None)
                if r is None:
                    cells.append('')
                elif r['status'] in ('match', 'no printed value', 'cited, match'):
                    cells.append(r['recomputed'])
                elif r['status'] == 'not in database':
                    cells.append(f"{r['printedText']} (printed; not in database)")
                else:
                    cells.append(f"**{r['recomputed']}** (printed {r['printedText']})")
            lines.append(f'| {row} | ' + ' | '.join(cells) + ' |')
        (a.out / f'{name}.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    counts = {s: sum(1 for r in rows if r['status'] == s) for s in ('match', 'MISMATCH', 'cited, match', 'cited, MISMATCH', 'not in database', 'no printed value')}
    lines = ['# Paper 1 numbers: printed against recomputed', '',
             f"{len(rows)} numbers. From the lab_ tables: match {counts['match']}, mismatch {counts['MISMATCH']}. "
             f"Cited constants stored in lab_cited (no structured source): {counts['cited, match'] + counts['cited, MISMATCH']}. "
             f"Not in the database: {counts['not in database']}. No printed value yet: {counts['no printed value']}.", '',
             'A mismatch is reported here and not changed in the manuscript.', '']
    for status in ('MISMATCH', 'cited, MISMATCH', 'match', 'cited, match', 'not in database', 'no printed value'):
        part = [r for r in rows if r['status'] == status]
        if not part:
            continue
        lines += [f'## {status} ({len(part)})', '', '| Table | Row | Column | Printed | Recomputed | Note |', '|---|---|---|---|---|---|']
        for r in part:
            note = r['calc'].get('reason', '') if status == 'not in database' else r['source']
            lines.append(f"| {r['table']} | {r['row']} | {r['col']} | {r['printedText'] or ''} | {r['recomputed'] or ''} | {note} |")
        lines.append('')
    (a.out / ('CHECK.md' if not a.table else f'CHECK-{slug(a.table)}.md')).write_text('\n'.join(lines), encoding='utf8')
    print(json.dumps({'numbers': len(rows), **counts, 'tables': len(tables), 'out': str(a.out)}, indent=1))


if __name__ == '__main__':
    main()
