#!/usr/bin/env node
// Evidence register c22: final-answer pacing check read by a second reader, and Printroom (no model call).
// Reads <artifacts>/claude-pacing-second-reader-20261114/: source/{v27-final,claude-final-answer-recount-20261108}/
// {deterministic.json,packets/,readings/runs/<key>/} (the first reader's 7 and 8 November readings), readings/runs/
// sol-<key>/ (the second reader), and deterministic.json, packets/, readings/runs/{fable,sol}-<key>/ for Printroom.
// A reading counts when validation.json status is structurally_checked (a ".repeat" folder is used if the first is not).
// Unresolved: the reader's class is "unresolved". Last needed record in the final tutor reply: from the packet text,
// the last of the scene's needed records is marked shown with the last tutor turn. Kappa on yes/no.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const R = path.join(opt('artifacts', path.join(os.homedir(), 'Dev/machinespirits/machinespirits-lab-artifacts')), 'claude-pacing-second-reader-20261114');
const rj = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const NEED = { 'harbour ledger': ['1', '3', '4'], 'seed bank': ['1', '2', '3'], 'museum label': ['1', '2', '3'], 'print room': ['1', '2', '3'] };
function lastInFinal(packet) {
  const t = rj(packet).text, scene = /SCENE \((.*?) lesson\)/.exec(t)[1];
  const turns = t.slice(t.indexOf('PUBLIC TRANSCRIPT')).split('\n--- turn ').slice(1);
  let last = null, tut = null;
  for (const x of turns) { const [, id, sp] = /(\S+) \((\w+)\)/.exec(x); if (sp === 'tutor') tut = id; for (const m of x.matchAll(/\[Record (\d) shown with this turn/g)) if (NEED[scene].includes(m[1])) last = id; }
  return last === tut;
}
function reading(base, key) {
  for (const s of ['', '.repeat']) { const d = path.join(base, key + s); const v = path.join(d, 'validation.json'); if (fs.existsSync(v) && rj(v).status === 'structurally_checked') { const r = rj(path.join(d, 'result.json')); return { cls: r.class, stated: r.answer_stated_as_conclusion_last_four_turns }; } }
  return null;
}
const rows = [];
for (const src of ['v27-final', 'claude-final-answer-recount-20261108']) {
  const S = path.join(R, 'source', src);
  for (const d of rj(path.join(S, 'deterministic.json'))) {
    const key = d.packet.slice(8, -5);
    rows.push({ world: d.world, resolvable: d.resolvable, lif: d.resolvable && lastInFinal(path.join(S, d.packet)), first: reading(path.join(S, 'readings', 'runs'), key), second: d.resolvable ? reading(path.join(R, 'readings', 'runs'), 'sol-' + key) : null });
  }
}
for (const d of rj(path.join(R, 'deterministic.json'))) {
  const key = d.packet.slice(8, -5);
  rows.push({ world: 'printroom', resolvable: d.resolvable, lif: d.resolvable && lastInFinal(path.join(R, d.packet)), first: reading(path.join(R, 'readings', 'runs'), 'fable-' + key), second: reading(path.join(R, 'readings', 'runs'), 'sol-' + key) });
}
const kappa = (pairs) => { const n = pairs.length, cats = [...new Set(pairs.flat())]; const po = pairs.filter(([a, b]) => a === b).length / n; const pe = cats.reduce((s, c) => s + (pairs.filter(([a]) => a === c).length / n) * (pairs.filter(([, b]) => b === c).length / n), 0); return Number(((po - pe) / (1 - pe)).toFixed(2)); };
function block(sel) {
  const both = sel.filter((r) => r.resolvable && r.first && r.second);
  const o = {};
  for (const w of ['first', 'second']) { const rr = sel.filter((r) => r.resolvable && r[w]); const un = rr.filter((r) => r[w].cls === 'unresolved'); o[w] = { resolvableRead: rr.length, unresolved: un.length, unresolvedLastInFinal: un.filter((r) => r.lif).length, notStated: rr.filter((r) => !r[w].stated).length, wrong: rr.filter((r) => r[w].cls === 'wrong').length }; }
  o.kappaUnresolved = kappa(both.map((r) => [r.first.cls === 'unresolved', r.second.cls === 'unresolved']));
  o.kappaUnresolvedLastInFinal = kappa(both.map((r) => [r.first.cls === 'unresolved' && r.lif, r.second.cls === 'unresolved' && r.lif]));
  o.kappaNotStated = kappa(both.map((r) => [!r.first.stated, !r.second.stated]));
  o.secondUnresolvedAmongFirst = both.filter((r) => r.second.cls === 'unresolved' && r.first.cls === 'unresolved').length;
  return o;
}
console.log(JSON.stringify({ threeScenes: block(rows.filter((r) => r.world !== 'printroom')), printroom: block(rows.filter((r) => r.world === 'printroom')), all: block(rows) }, null, 1));

if (opt('observations', null)) fs.writeFileSync(opt('observations'), JSON.stringify(rows.filter(r => r.world !== 'printroom').map(r => [r.resolvable, r.first?.cls ?? null, r.lif])));
