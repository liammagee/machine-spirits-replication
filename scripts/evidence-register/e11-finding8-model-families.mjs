#!/usr/bin/env node
// Evidence register e11: Paper 1, "Finding 8 with other model families" and Appendix J (the item 21 checks), recounted
// from raw fork outputs, lesson events, delivery codes and drama readings. No model call.
//   <artifacts>/claude-item21-cross-model-20261108
//     live/<point>--<arm>[--r]/{RESULT.json,run/events.jsonl,run/attempts/*.request.json}   one fork; --r = replacement
//     coding/delivery/{key-private.json,codes/<id>.<coder>.json}   delivery codes of the fork replies (label point--arm)
//     readings/{key-private.json,runs/<pair>--drama-<opus|sol>-<AB|BA>[.retry]}   drama reader per point and swap set
//     reread/delivery/{key-private.json,codes/<id>.<coder>.json}   Qwen (exo-qwen) re-codes of the larger check's items
//     reread/readings/{key-private.json,runs/<pair>--drama-qwen-<AB|BA>[.retry]}   Qwen drama readings of its 40 pairs
//     learner/lessons/<id>, learner/coding/delivery     8 lessons with a Claude Sonnet 5.5 learner (arms CL<type>)
//   <artifacts>/claude-rules-by-reading-large-20261108   the larger check (its own codes and readings, for the swaps)
//   <artifacts>/claude-opus-playwright-20261109          16 lessons per arm, playwright on Opus 5.5 (PRA / PRR)
//   <artifacts>/claude-sonnet-tutor-21c-20261109         16 lessons per arm, Sonnet 5.5 in all tutor roles (SNA / SNR)
// Arms of a fork: T (all Terra), PW / AC / CR (playwright, actor, critic swapped) with o (Opus), q (Qwen), s (GPT-6.1
// Sol); design R (drama-v2.17) or A (drama-v2.16). Carried out = both coders delivered yes. Counted, guards and
// drama verdicts as in e10. Sign tests are exact binomial on the pairs with a verdict.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const ART = opt('artifacts', path.join(os.homedir(), 'Dev/machinespirits/machinespirits-lab-artifacts'));
const REPO = opt('repo', null);
const I21 = path.join(ART, 'claude-item21-cross-model-20261108');
const LARGE = path.join(ART, 'claude-rules-by-reading-large-20261108');
const DIS = ['sarcasm', 'humour', 'challenge', 'parable', 'reverse-advocacy', 'role-reversal'];
const REP = ['own-claim', 'parable', 'analogy', 'role-reversal', 'worked-example', 'fundamentals', 'representation', 'humour', 'sarcasm', 'challenge', 'gravity', 'reverse-advocacy'];
const TYPES = ['B', 'C', 'R', 'O'];
const rj = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const ex = (f) => fs.existsSync(f);
const evs = (d) => fs.readFileSync(path.join(d, 'events.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
const words = (s) => String(s ?? '').trim().split(/\s+/u).filter(Boolean).length;
const mean = (a) => (a.length ? Number((a.reduce((s, x) => s + x, 0) / a.length).toFixed(1)) : null);
const binom = (n, k) => { let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return r; };
const signOne = (hi, lo) => { const n = hi + lo; let p = 0; for (let i = hi; i <= n; i++) p += binom(n, i); return p / 2 ** n; }; // P(X >= hi)
const signTwo = (a, b) => Math.min(1, 2 * signOne(Math.max(a, b), Math.min(a, b)));
const r4 = (x) => Number(x.toPrecision(3));
let early = null;
if (REPO) early = (await import(pathToFileURL(path.join(REPO, 'src/adaptation/pacingHold.js')).href)).recordsReleasedEarly;
function kappa(pairs) {
  const n = pairs.length; if (!n) return null; const cats = [...new Set(pairs.flat())];
  const po = pairs.filter(([a, b]) => a === b).length / n;
  const pe = cats.reduce((s, c) => s + (pairs.filter(([a]) => a === c).length / n) * (pairs.filter(([, b]) => b === c).length / n), 0);
  return { n, agreePct: Number((100 * po).toFixed(1)), kappa: Number(((po - pe) / (1 - pe)).toFixed(3)) };
}
function ncdf(z) { const t = 1 / (1 + 0.2316419 * Math.abs(z)), d = 0.3989423 * Math.exp(-z * z / 2); const q = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return z > 0 ? 1 - q : q; }
function cmh(strata) { let num = 0, v = 0; for (const s of strata) { const n = s.nA + s.nB, m = s.yA + s.yB; if (!n) continue; num += s.yB - s.nB * m / n; v += n > 1 ? s.nA * s.nB * m * (n - m) / (n * n * (n - 1)) : 0; } const z = num / Math.sqrt(v); return { z: Number(z.toFixed(3)), pOneSided: r4(1 - ncdf(z)) }; }

// One drama reading folder: a pair has a verdict when every listed reader names the same lesson in both orders.
function readSide(runs, id, reader, order, onSideAB) {
  for (const suf of ['', '.retry']) {
    const d = path.join(runs, `${id}--drama-${reader}-${order}${suf}`);
    if (!ex(path.join(d, 'result.json'))) continue;
    if (ex(path.join(d, 'validation.json')) && rj(path.join(d, 'validation.json')).status !== 'structurally_checked') continue;
    const c = String(rj(path.join(d, 'result.json')).comparison ?? '').trim();
    const side = /^A\b/u.test(c) && !/^A and B/u.test(c) ? 'A' : /^B\b/u.test(c) ? 'B' : 'tie';
    const on = order === 'AB' ? onSideAB : (onSideAB === 'A' ? 'B' : 'A');
    return side === 'tie' ? 'tie' : side === on ? 'on' : 'off';
  }
  return 'missing';
}
function verdicts(keyFile, runsFor) { // runsFor: {reader: runsDir}
  const key = rj(keyFile), out = [];
  for (const [pair, k] of Object.entries(key)) {
    const id = pair.replace(/:drama$/u, ''), reads = [];
    for (const [reader, runs] of Object.entries(runsFor)) for (const o of ['AB', 'BA']) reads.push(readSide(runs, id, reader, o, k.onSideAB));
    out.push({ id, ...k, verdict: reads.every((x) => x === 'on') ? 'on' : reads.every((x) => x === 'off') ? 'off' : 'none' });
  }
  return out;
}
const tally = (ps) => ({ R: ps.filter((p) => p.verdict === 'on').length, A: ps.filter((p) => p.verdict === 'off').length, none: ps.filter((p) => p.verdict === 'none').length });

// ---- forks at the 12 first points ----
const points = rj(path.join(I21, 'POINTS.json')).points;
const first = points.filter((p) => p.kind === 'first');
const dkey = rj(path.join(I21, 'coding/delivery/key-private.json')).items;
const codesOf = (dir, id, coders) => coders.map((c) => { const f = path.join(dir, 'codes', `${id}.${c}.json`); return ex(f) ? rj(f) : null; });
const forkDir = (label) => { const r = path.join(I21, 'live', label + '--r'); return ex(path.join(r, 'run/events.jsonl')) ? r : path.join(I21, 'live', label); };
const arms = ['T'].concat(...['PW', 'AC', 'CR'].map((r) => ['o', 'q', 's'].map((m) => `${r}-${m}`)));
const forks = {};
for (const a of arms) for (const d of ['R', 'A', 'Rlater']) {
  const arm = d === 'Rlater' ? `${a}-R` : `${a}-${d}`, rows = [];
  for (const p of (d === 'Rlater' ? points.filter((x) => x.kind === 'later') : first)) {
    const label = `${p.id}--${arm}`, k = dkey[label], dir = forkDir(label);
    const c = k ? codesOf(path.join(I21, 'coding/delivery'), k.id, ['opus-medium', 'sol-medium']) : [null, null];
    const coded = c.every(Boolean);
    const ev = ex(path.join(dir, 'run/events.jsonl')) ? evs(path.join(dir, 'run')) : [];
    const unit = p.reply;
    const ts = ev.filter((e) => e.type === 'teaching_strategy' && e.unitId === unit).at(-1);
    const asg = ev.filter((e) => e.type === 'strategy_assigned_by_rule' && e.unitId === unit).at(-1);
    const withheld = ev.some((e) => e.type === 'tutor_design_note_line_withheld' && e.unitId === unit);
    const criticBack = ev.filter((e) => e.type === 'inner_amendment' && e.unitId === unit).length;
    // the actor's request for the delivered draft
    const msg = ev.find((e) => e.type === 'message' && e.message?.id === unit);
    const drafts = ev.filter((e) => e.type === 'attempt_request_persisted' && new RegExp(`^(amend\\d*-)?${unit}$`, 'u').test(e.unitId));
    const req0 = drafts.find((e) => e.unitId === unit);
    let thisReply = null, charInRequest = null;
    if (req0) {
      const rq = rj(path.join(dir, 'run', req0.path)), sys = String(rq.messages[0].content);
      const sec = sys.includes('HOW SHE IS TEACHING NOW') ? sys.slice(sys.indexOf('HOW SHE IS TEACHING NOW')) : '';
      thisReply = /^This reply: (.*)$/mu.exec(sec)?.[1] ?? null;
      const notes = rq.messages.filter((x) => x.role === 'user' && typeof x.content === 'string' && x.content.startsWith('A NOTE FROM THE PLAYWRIGHT'));
      charInRequest = Boolean(notes.length && /^CHARACTER: /mu.test(notes.at(-1).content));
    }
    rows.push({ point: p.id, arm, fork: path.basename(dir), replacement: dir.endsWith('--r'), coded, bothYes: coded && c.every((x) => x.delivered === 'yes'),
      handedOverBoth: coded && c.every((x) => x.inference_handed_over === 'yes'), unsupportedEither: coded && c.some((x) => x.unsupported_claim === 'yes'),
      strategy: ts?.inForce ?? null, outcome: ts?.outcome ?? null, how: ts?.how ?? null, proposed: ts?.proposed?.id ?? null, proposedAction: ts?.proposed?.action ?? null,
      assigned: asg?.assigned ?? null, overrode: Boolean(asg && asg.assigned !== ts?.proposed?.id), withheld, criticBack, thisReply, charInRequest, delivered: Boolean(msg) });
  }
  forks[d === 'Rlater' ? `${a}-R-later` : arm] = rows;
}
const forkSummary = {};
for (const a of arms) {
  const R = forks[`${a}-R`], A = forks[`${a}-A`];
  forkSummary[a] = { firstReplyYes: { R: R.filter((r) => r.bothYes).length, A: A.filter((r) => r.bothYes).length, codedR: R.filter((r) => r.coded).length, codedA: A.filter((r) => r.coded).length },
    g1both: { R: R.filter((r) => r.handedOverBoth).length, A: A.filter((r) => r.handedOverBoth).length },
    g3either: { R: R.filter((r) => r.unsupportedEither).length, A: A.filter((r) => r.unsupportedEither).length },
    criticSentBackForks: R.concat(A).filter((r) => r.criticBack > 0).length, replacements: R.concat(A).filter((r) => r.replacement).length,
    drama_v217_first_and_later: (() => { const RR = R.concat(forks[`${a}-R-later`]); return { forks: RR.length, g1both: RR.filter((r) => r.handedOverBoth).length, criticSentBackForks: RR.filter((r) => r.criticBack > 0).length, criticSendBacks: RR.reduce((s, r) => s + r.criticBack, 0) }; })() };
}
// the playwright forks under drama-v2.17: the rule's sentence in place of her note; the CHARACTER line withheld
const pwSets = { Terra: forks['T-R'], Opus: forks['PW-o-R'], 'GPT-6.1 Sol': forks['PW-s-R'], Qwen: forks['PW-q-R'] };
const playwright = Object.fromEntries(Object.entries(pwSets).map(([m, rs]) => [m, {
  rulesOverrodeHerChoice: rs.filter((r) => r.overrode).length,
  strategyDiffersFromHerAForkChoice: rs.filter((r) => { const a = forks[r.arm.replace(/-R$/u, '-A')].find((x) => x.point === r.point); return a && a.strategy !== r.strategy; }).length, assignedByRule: rs.filter((r) => r.assigned).length,
  thisReplyIsRuleSentence: rs.filter((r) => r.thisReply && r.how && r.outcome === 'switched_by_rule' && r.thisReply.trim() === r.how.trim()).length,
  characterWithheld: rs.filter((r) => r.withheld).length, characterAbsentFromRequest: rs.filter((r) => r.charInRequest === false).length,
  ruleSentenceWords: mean(rs.filter((r) => r.outcome === 'switched_by_rule').map((r) => words(r.how))),
}]));
const pwA = { Terra: forks['T-A'], Opus: forks['PW-o-A'], 'GPT-6.1 Sol': forks['PW-s-A'], Qwen: forks['PW-q-A'] };
for (const [m, rs] of Object.entries(pwA)) playwright[m].ownNoteWordsUnderA = mean(rs.filter((r) => r.how).map((r) => words(r.how)));
// drama reader at the fork points
const fv = verdicts(path.join(I21, 'readings/key-private.json'), { opus: path.join(I21, 'readings/runs'), sol: path.join(I21, 'readings/runs') });
const forkDrama = {};
for (const set of [...new Set(fv.map((p) => p.set))]) { const t = tally(fv.filter((p) => p.set === set)); forkDrama[set] = { ...t, oneSidedFavoured: r4(signOne(Math.max(t.R, t.A), Math.min(t.R, t.A))), twoSided: r4(signTwo(t.R, t.A)) }; }

// ---- Qwen in place of one coder, on the larger check's 409 items ----
const rk = rj(path.join(I21, 'reread/delivery/key-private.json')).items;
const qItems = Object.entries(rk).map(([label, k]) => {
  const get = (c, dir) => { const f = path.join(dir, 'codes', `${k.id}.${c}.json`); return ex(f) ? rj(f) : null; };
  return { label, ...k, opus: get('opus-medium', path.join(LARGE, 'coding/delivery')), sol: get('sol-medium', path.join(LARGE, 'coding/delivery')), qwen: get('exo-qwen', path.join(I21, 'reread/delivery')) };
});
const qOK = qItems.filter((x) => x.opus && x.sol && x.qwen);
const agreeQ = { qwenOpus: kappa(qOK.map((x) => [x.qwen.delivered, x.opus.delivered])), qwenSol: kappa(qOK.map((x) => [x.qwen.delivered, x.sol.delivered])), opusSol: kappa(qOK.map((x) => [x.opus.delivered, x.sol.delivered])) };
// counted measure with a chosen pair of coders on the larger check
const observations = [];
function countedWith(root, codeOf, idRe) {
  const out = {};
  const lessons = {}; observations.push(lessons);
  for (const id of fs.readdirSync(path.join(root, 'lessons')).filter((x) => idRe.test(x)).sort()) {
    const m = idRe.exec(id), arm = m[2].at(-1), ev = evs(path.join(root, 'lessons', id));
    if (!ev.some((e) => e.type === 'phase' && e.phase === 'WORKFLOW_COMPLETE')) continue;
    const ts = ev.filter((e) => e.type === 'teaching_strategy'); let directed = null;
    const rows = ev.filter((e) => e.type === 'message' && e.message.speaker !== 'learner').map((e) => {
      const t = ts.find((s) => s.unitId === e.message.id) ?? null, pos = t ? (t.before === t.inForce ? 'later' : 'first') : null;
      if (t && pos === 'first') directed = t.outcome === 'learner_directed' ? t.inForce : null;
      const yes = t && REP.includes(t.inForce) ? codeOf(`${id}:${e.message.id}:${t.inForce}:${pos}`) : false;
      return { s: t?.inForce, ok: Boolean(yes) && !(t && directed && directed === t.inForce) };
    });
    lessons[id] = rows.map(r => [r.s ?? null, r.ok]);
    let best = 0, cur = 0; rows.forEach((r, i) => { const ok = DIS.includes(r.s) && r.ok, p = rows[i - 1]; cur = ok ? (p && p.s === r.s && p.ok ? cur + 1 : 1) : 0; best = Math.max(best, cur); });
    out[arm] ??= 0; out[arm] += best >= 2 ? 1 : 0;
  }
  return out;
}
const byLabel = Object.fromEntries(qItems.map((x) => [x.label, x]));
const yes = (x, c) => x?.[c]?.delivered === 'yes';
const largeRe = /^([A-Z]+)-(R[AR])([BCRO])-l(\d+)$/u;
const qwenCoder = {
  qwenInPlaceOfOpus: countedWith(LARGE, (l) => yes(byLabel[l], 'qwen') && yes(byLabel[l], 'sol'), largeRe),
  qwenInPlaceOfSol: countedWith(LARGE, (l) => yes(byLabel[l], 'opus') && yes(byLabel[l], 'qwen'), largeRe),
  opusAndSol: countedWith(LARGE, (l) => yes(byLabel[l], 'opus') && yes(byLabel[l], 'sol'), largeRe),
  items: qItems.length, itemsWithAllThree: qOK.length, agreement: agreeQ,
};
const qRead = { qwenInPlaceOfOpus: tally(verdicts(path.join(LARGE, 'readings/key-private.json'), { qwen: path.join(I21, 'reread/readings/runs'), sol: path.join(LARGE, 'readings/runs') })),
  qwenInPlaceOfSol: tally(verdicts(path.join(LARGE, 'readings/key-private.json'), { opus: path.join(LARGE, 'readings/runs'), qwen: path.join(I21, 'reread/readings/runs') })) };

// ---- whole lessons: Opus playwright, Sonnet tutor roles, Sonnet learner ----
function wholeLessons(root, re, { keyDir = 'coding/delivery', armOf = (m) => m[2].at(-1) } = {}) {
  const key = rj(path.join(root, keyDir, 'key-private.json')).items;
  const prepared = ex(path.join(root, 'PREPARED.json')) ? rj(path.join(root, 'PREPARED.json')) : null;
  const ids = fs.readdirSync(path.join(root, 'lessons')).filter((x) => re.test(x)).sort();
  const ls = [];
  for (const id of ids) {
    const m = re.exec(id), dir = path.join(root, 'lessons', id), ev = evs(dir);
    const complete = ev.some((e) => e.type === 'phase' && e.phase === 'WORKFLOW_COMPLETE');
    const ts = ev.filter((e) => e.type === 'teaching_strategy'); let directed = null;
    const msgs = ev.filter((e) => e.type === 'message').map((e) => e.message);
    const rows = msgs.filter((x) => x.speaker !== 'learner').map((x) => {
      const t = ts.find((s) => s.unitId === x.id) ?? null, pos = t ? (t.before === t.inForce ? 'later' : 'first') : null;
      if (t && pos === 'first') directed = t.outcome === 'learner_directed' ? t.inForce : null;
      const k = t && REP.includes(t.inForce) ? key[`${id}:${x.id}:${t.inForce}:${pos}`] : null;
      const c = k ? codesOf(path.join(root, keyDir), k.id, ['opus-medium', 'sol-medium']) : null, coded = Boolean(c && c.every(Boolean));
      return { reply: x.id, s: t?.inForce ?? null, pos, byDir: Boolean(t && directed && directed === t.inForce), coded, bothYes: coded && c.every((z) => z.delivered === 'yes'),
        g1: coded && c.every((z) => z.inference_handed_over === 'yes'), g3: coded && c.some((z) => z.unsupported_claim === 'yes'),
        chosen: Boolean(t && pos === 'first' && DIS.includes(t.inForce) && t.outcome !== 'learner_directed' && !ev.some((e) => e.type === 'strategy_assigned_by_rule' && e.unitId === x.id)) };
    });
    let best = 0, cur = 0; rows.forEach((r, i) => { const ok = DIS.includes(r.s) && r.bothYes && !r.byDir, p = rows[i - 1]; cur = ok ? (p && p.s === r.s && DIS.includes(p.s) && p.bothYes && !p.byDir ? cur + 1 : 1) : 0; best = Math.max(best, cur); });
    let g2 = null;
    if (early && prepared && complete) {
      const cellId = id.replace(/-l\d+(-x)?$/u, ''), cell = prepared.cells.find((c) => c.id === cellId);
      if (cell) { const compiled = cell.compiledFile.replace(/^.*?\/(claude-[^/]*-2026\d{4}[a-z]?)\//u, (s, f) => path.join(ART, f) + '/'); const plan = rj(compiled).plan;
        g2 = early({ history: [...plan.scene.public.prefix, ...msgs].map((x) => ({ id: x.id, speaker: x.speaker, text: x.text })), releases: ev.filter((e) => e.type === 'document_release'), scene: plan.scene }).length; }
    }
    ls.push({ id, world: m[1], arm: armOf(m), type: m[3], replacementOf: id.endsWith('-x') ? id.slice(0, -2) : null, complete, counted: best >= 2,
      ownDisruptive: rows.some((r) => r.chosen), g1: rows.filter((r) => r.g1).length, g2, g3: rows.filter((r) => r.g3).length, g3Lessons: rows.some((r) => r.g3) ? 1 : 0 });
  }
  // a replaced lesson is used only through its replacement
  const used = ls.filter((l) => l.complete && !ls.some((x) => x.replacementOf === l.id && x.complete));
  const arm = (a, t) => used.filter((l) => l.arm === a && (!t || l.type === t));
  const sum = (a, f) => arm(a).reduce((s, l) => s + (l[f] ?? 0), 0);
  const strata = TYPES.map((t) => ({ nA: arm('A', t).length, yA: arm('A', t).filter((l) => l.counted).length, nB: arm('R', t).length, yB: arm('R', t).filter((l) => l.counted).length }));
  return { lessonsFound: ls.length, notComplete: ls.filter((l) => !l.complete).map((l) => l.id), replacements: ls.filter((l) => l.replacementOf).map((l) => l.id),
    A: { lessons: arm('A').length, counted: arm('A').filter((l) => l.counted).length, ownDisruptive: arm('A').filter((l) => l.ownDisruptive).length, g1: sum('A', 'g1'), g2: sum('A', 'g2'), g3: sum('A', 'g3'), g3Lessons: sum('A', 'g3Lessons') },
    R: { lessons: arm('R').length, counted: arm('R').filter((l) => l.counted).length, g1: sum('R', 'g1'), g2: sum('R', 'g2'), g3: sum('R', 'g3'), g3Lessons: sum('R', 'g3Lessons') },
    cmh: strata.every((s) => s.nA && s.nB) ? cmh(strata) : null, perLesson: used.map(({ id, arm, counted, g3 }) => ({ id, arm, counted, g3 })) };
}
function requestFiles(dir) { let n = 0; const walk = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { if (e.isDirectory()) walk(path.join(d, e.name)); else if (/\.request\.json$/u.test(e.name)) n++; } }; walk(dir); return n; }
const OPUS = path.join(ART, 'claude-opus-playwright-20261109'), SON = path.join(ART, 'claude-sonnet-tutor-21c-20261109');
const opusLessons = wholeLessons(OPUS, /^([A-Z]+)-(PR[AR])([BCRO])-l(\d+)(-x)?$/u);
const sonnetLessons = wholeLessons(SON, /^([A-Z]+)-(SN[AR])([BCRO])-l(\d+)(-x)?$/u);
const opusDrama = tally(verdicts(path.join(OPUS, 'readings/key-private.json'), { opus: path.join(OPUS, 'readings/runs'), sol: path.join(OPUS, 'readings/runs') }));
const sonnetDrama = tally(verdicts(path.join(SON, 'readings/key-private.json'), { opus: path.join(SON, 'readings/runs'), sol: path.join(SON, 'readings/runs') }));
// Sonnet learner lessons (arm CL<type>, drama-v2.17)
const learner = (() => { const root = path.join(I21, 'learner'), re = /^([A-Z]+)-(CL)([BCRO])-l(\d+)$/u; const r = wholeLessons(root, re, { armOf: () => 'R' }); const all = fs.readdirSync(path.join(root, 'lessons')).filter((x) => re.test(x)); return { lessons: all.length, raw: r }; })();
console.log(JSON.stringify({
  forks: { points: first.length, perArm: forkSummary, playwright, drama: forkDrama },
  qwenCoder, qwenReader: qRead,
  opusPlaywright: { ...opusLessons, drama: { ...opusDrama }, requestFiles: requestFiles(OPUS) },
  sonnetTutor: { ...sonnetLessons, drama: { ...sonnetDrama, oneSided: r4(signOne(Math.max(sonnetDrama.R, sonnetDrama.A), Math.min(sonnetDrama.R, sonnetDrama.A))) }, requestFiles: requestFiles(SON) },
  sonnetLearner: learner, item21RequestFiles: requestFiles(I21),
}, null, 1));

if (opt('observations', null)) fs.writeFileSync(opt('observations'), JSON.stringify({eligibleTurns: observations.slice(0,2), itemLabels: Object.keys(byLabel).filter(l => ['qwen','opus','sol'].every(c => byLabel[l][c]))}));
