"""Recover the observation records for six table entries from the extracted deposit."""
from collections import Counter
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent / 'evidence-register'
STRATEGIES = {'sarcasm', 'humour', 'challenge', 'parable', 'reverse-advocacy', 'role-reversal'}


def read(path):
    return json.loads(path.read_bytes())


def observations(view):
    with tempfile.TemporaryDirectory() as tmp:
        outputs = []
        for name in ('e11-finding8-model-families', 'c22-pacing-second-reader'):
            dest = Path(tmp) / name
            subprocess.run(['node', SCRIPTS / (name+'.mjs'), '--artifacts', view, '--observations', dest],
                           stdout=subprocess.DEVNULL, check=True)
            outputs.append(read(dest))
    historical = view / 'paper-claim-traceability-20261115/historical-marker'
    actor = read(historical/'actor-recount.json')['rows']
    answers = read(historical/'author-union-checked.json')['answers']
    fidelity = {}
    lessons = view / 'claude-drama-v2-dials-20261105/lessons'
    for path in sorted(lessons.glob('SB-*/attempts/*.request.json')):
        request = read(path)
        messages = '\n'.join(str(m['content']) for m in request['messages'])
        fidelity[str(path.relative_to(lessons))] = [request['role'], 'RESOLVED FIDELITY POLICY' in messages]
    return {'coder_comparisons': outputs[0], 'pacing': outputs[1], 'fidelity_requests': fidelity,
            'actor_audit': actor, 'playwright_audit': {k: a['curly'] for k,a in answers.items()}}


def calculate(data):
    result = {}
    qwen = data['coder_comparisons']
    labels = qwen['itemLabels']
    result['items_with_three_coders'] = len(set(labels))
    for name, lessons in zip(('qwen_in_place_of_opus','qwen_in_place_of_sol'), qwen['eligibleTurns']):
        counts, sizes = Counter(), Counter()
        for lesson, sequence in lessons.items():
            arm = lesson.split('-')[1][1]
            sizes[arm] += 1
            repeated = any(yes and prior_yes and strategy == prior and strategy in STRATEGIES
                           for (prior,prior_yes),(strategy,yes) in zip(sequence,sequence[1:]))
            counts[arm] += repeated
        if sizes != {'A':40,'R':40}:
            raise ValueError(f'Incomplete coder comparison: {sizes}')
        result[name] = dict(counts)
    unresolved = [last for possible,reading,last in data['pacing'] if possible and reading == 'unresolved']
    result['last_record_in_final'] = [sum(unresolved), len(unresolved)]
    actor = data['actor_audit']
    result['actor_text'] = [sum(a['actor'] for a in actor), sum(a['requests'] for a in actor), len(actor)]
    playwright = data['playwright_audit']
    result['curly_apostrophe'] = [sum(playwright.values()), len(playwright)]
    roles = {}
    for role, present in data['fidelity_requests'].values():
        entry = roles.setdefault(role,[0,0]); entry[0] += present; entry[1] += 1
    result['fidelity_policy_in_role_requests'] = roles
    expected = {'items_with_three_coders':409, 'qwen_in_place_of_opus':{'A':6,'R':22},
                'qwen_in_place_of_sol':{'A':6,'R':15}, 'last_record_in_final':[29,37],
                'actor_text':[40,6811,36], 'curly_apostrophe':[557,23103],
                'fidelity_policy_in_role_requests':{'superego':[65,65], 'tutor':[0,33],
                                                    'learner':[0,24], 'resistance-reader':[0,24]}}
    if result != expected:
        raise ValueError(f'Cited entries differ: {result}')
    return result


if __name__ == '__main__':
    result = observations(Path(sys.argv[1]).resolve())
    calculate(result)
    sys.stdout.buffer.write(gzip.compress(json.dumps(result,sort_keys=True,separators=(',',':')).encode(),mtime=0))
