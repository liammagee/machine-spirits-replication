"""Counts for the eight catalogue omissions and Figure 5's opening strategies."""
import json
import math
import re
import zipfile
from collections import Counter, defaultdict

RULES = '20261108-claude-rules-by-reading-large'
RETURN = '20261107-claude-switch-back'
COMPLAINT = re.compile(r'tedious|repetit|same (question|thing|exercise)|worn me out|over and over|feels the same|same routine',re.I)


def additional_counts(db, data):
    assigned_counts = Counter()
    complaints = Counter()
    lost_returns = []
    with zipfile.ZipFile(data / 'selected-events.zip') as z:
        folders = defaultdict(dict)
        for name in z.namelist():
            if name.endswith('/events.jsonl'):
                _, run, _, _, lesson, _ = name.split('/')
                folders[run][lesson] = [json.loads(line) for line in z.read(name).splitlines()]
            elif name.endswith('variety-saved.json'):
                variety = json.loads(z.read(name))
        if len(folders[RULES]) != 80 or len(folders[RETURN]) != 24:
            raise ValueError('Expected 80 rules-by-reading and 24 bored-learner lessons')
        for lesson, events in folders[RULES].items():
            arm = lesson.split('-')[1][:2]
            # A revision of a draft can generate another event for the same tutor reply.
            withheld = {e['unitId'] for e in events if e['type']=='tutor_design_note_line_withheld' and re.fullmatch(r'reply-\d+',e['unitId'])}
            assigned = {e['unitId'] for e in events if e['type']=='strategy_assigned_by_rule'}
            assigned_counts[arm] += len(withheld)
            if arm == 'RR':
                for unit in withheld & assigned:
                    codes = db.execute("select delivered from lab_codes where run_id=? and lesson_id=? and unit_id=? and codebook='delivery' and position='first'", (RULES,lesson,unit)).fetchall()
                    if codes:
                        if len(codes)!=2:
                            raise ValueError('Incomplete delivery codes for '+lesson+' '+unit)
                        assigned_counts['first_assigned'] += 1
                        assigned_counts['both_yes'] += all(r[0]=='yes' for r in codes)
        pairs = db.execute('select on_lesson, off_lesson, published_verdict from lab_drama_pairs where run_id=? and learner=?',(RETURN,'B')).fetchall()
        if len(pairs)!=12:
            raise ValueError('Expected 12 matched bored-learner pairs')
        for on,off,verdict in pairs:
            for lesson,arm in [(on,'R'),(off,'E')]:
                msgs = [e['message'] for e in folders[RETURN][lesson] if e['type']=='message']
                complaints[arm] += any(m['speaker']=='learner' and COMPLAINT.search(m['text']) for m in msgs[:-1])
            if verdict=='off':
                lost_returns.append(any(e['type']=='strategy_return_taken' for e in folders[RETURN][on]))
    positives = complaints['R']+complaints['E']
    masses = {k:math.comb(12,k)*math.comb(12,positives-k) for k in range(13) if 0<=positives-k<=12}
    p = sum(v for v in masses.values() if v<=masses[complaints['R']])/sum(masses.values())
    eight = [assigned_counts[k] for k in ['RR','first_assigned','both_yes','RA']]+[f"{complaints[a]} of 12" for a in ('R','E')]+[round(p,3),f'{sum(lost_returns)} of {len(lost_returns)}']
    if eight != [64,62,56,2,'11 of 12','6 of 12',0.069,'1 of 6']:
        raise ValueError(f'Counts outside the catalogue disagree: {eight}')
    if len(variety)!=104:
        raise ValueError('Expected 104 sets of opening strategies')
    openings = {}
    for kind in 'BCRO':
        means = []
        for arm in ('learned','hardwired'):
            rows = [r for r in variety if r['type']==kind and r['arm']==arm]
            if len(rows)!=13 or any(len(r['openingList'])!=5 for r in rows):
                raise ValueError('Incomplete opening data')
            means.append(round(sum(len(set(r['openingList'])) for r in rows)/len(rows),2))
        openings[kind] = means
    if openings != {'B':[4.08,1.0],'C':[4.08,1.62],'R':[4.23,1.31],'O':[4.08,1.23]}:
        raise ValueError(f'Figure 5 opening-strategy means differ: {openings}')
    return {'withheld':dict(assigned_counts),'lessonsWithComplaint':dict(complaints),'pairsPerArm':12,
            'fisherTwoSided':p,'losingLessonsWithReturn':[sum(lost_returns),len(lost_returns)],
            'figure5OpeningMeansLearnedHardwired':openings}
