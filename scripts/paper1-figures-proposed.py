#!/usr/bin/env python3
"""Paper 1's figures since 17 November 2026 (FIGURES-REVIEW-20261117.md). No model calls.

    python3 scripts/paper1-figures-proposed.py [--png]

Writes the paper's figures F1 to F6 and J1 to docs/papers/adaptive-tutor-conduct/figures/arxiv/ as SVG and PDF (and,
with --png, a PNG at twice the size for viewing; PNGs are not committed). The drafts were named P1 to P7 in the review.

The author chose the recommended set on 17 November 2026 ("A: recommended six"): F1 to F6 in the main text and J1 in
Appendix J. They replace F1-two-roles to F5-role-model-grid of scripts/paper1-figures.py, which ARXIV.md no longer
uses. The PDF needs rsvg-convert (librsvg).

Every number below was recomputed from the saved lesson, code and reading files with the evidence-register scripts or
the studies' own counting scripts, and equals the number printed in ARXIV.md. The review document names the script
and folder for each figure.
"""
import math
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FONT = 'Helvetica, Arial, sans-serif'
DARK, MID, GREY, LIGHT, RULE = '#222222', '#555555', '#8c8c8c', '#e9e9e9', '#d4d4d4'
BLUE, ORANGE, CREAM = '#2f6db3', '#d9822b', '#fff4e3'
FS = 1.12  # every text size is multiplied by this, so that the labels print at 6 points or more at the paper's text width


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.body = w, h, []

    def text(self, x, y, s, size=8.5, fill=DARK, bold=False, anchor='start', italic=False):
        a = (' font-weight="bold"' if bold else '') + (' font-style="italic"' if italic else '')
        self.body.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size * FS:.2f}" fill="{fill}" text-anchor="{anchor}"{a}>'
                         f'{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=DARK, width=0.8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                         f'stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill='none', stroke=None, rx=0, width=0.8, dash=None):
        s = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ''
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{h:.1f}" rx="{rx}" '
                         f'fill="{fill}"{s}{d}/>')

    def circle(self, x, y, r, fill=DARK, stroke=None):
        s = f' stroke="{stroke}" stroke-width="1"' if stroke else ''
        self.body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"{s}/>')

    def diamond(self, x, y, r, stroke=DARK, fill='#ffffff'):
        p = f'{x:.1f},{y - r:.1f} {x + r:.1f},{y:.1f} {x:.1f},{y + r:.1f} {x - r:.1f},{y:.1f}'
        self.body.append(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="1.1"/>')

    def arrow(self, x1, y1, x2, y2, stroke=MID, width=1.0, dash=None):
        self.line(x1, y1, x2, y2, stroke, width, dash)
        a = math.atan2(y2 - y1, x2 - x1)
        pts = ' '.join(f'{x2 - 6.5 * math.cos(a + d):.1f},{y2 - 6.5 * math.sin(a + d):.1f}' for d in (0.42, -0.42))
        self.body.append(f'<polygon points="{x2:.1f},{y2:.1f} {pts}" fill="{stroke}"/>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} '
                f'{self.h}" font-family="{FONT}"><rect width="{self.w}" height="{self.h}" fill="#ffffff"/>'
                + ''.join(self.body) + '</svg>\n')


OUT = REPO / 'docs/papers/adaptive-tutor-conduct/figures/arxiv'
PAPER_NAMES = {'P1-one-turn': 'F1-one-turn', 'P5-keep-line-delivery-and-drama': 'F2-keep-line-delivery-and-drama',
               'P2-change-by-tutor-model': 'F3-change-by-tutor-model', 'P3-layers-added-and-removed': 'F4-layers-added-and-removed',
               'P4-learned-draw-eighteen-tests': 'F5-learned-draw-eighteen-tests',
               'P6-drama-reader-pairs-whole-lessons': 'F6-drama-reader-pairs-whole-lessons',
               'P7-role-model-grid': 'J1-role-model-grid'}


def write(name, c):
    name = PAPER_NAMES[name]
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f'{name}.svg'
    p.write_text(c.svg())
    if not shutil.which('rsvg-convert'):
        sys.exit('rsvg-convert is not installed (brew install librsvg)')
    subprocess.run(['rsvg-convert', '-f', 'pdf', '-o', str(OUT / f'{name}.pdf'), str(p)], check=True)
    if '--png' in sys.argv:
        subprocess.run(['rsvg-convert', '-z', '2', '-b', 'white', '-o', str(OUT / f'{name}.png'), str(p)], check=True)
    print('wrote', p.relative_to(REPO))


def coder_legend(c, x, y):
    c.circle(x + 4, y - 3, 3.2)
    c.text(x + 11, y, 'Claude Opus 5.5 coder', 8)
    x += 11 + 0.5 * 8 * 21 + 14
    c.diamond(x + 4, y - 3, 3.8)
    c.text(x + 11, y, 'GPT-6 Sol coder', 8)
    x += 11 + 0.5 * 8 * 15 + 14
    c.diamond(x + 4, y - 3, 4.6)
    c.circle(x + 4, y - 3, 2.1)
    c.text(x + 12, y, 'both coders give the same count', 8)


def two_coders(c, xof, y, a, b, colour):
    """One row of a dot plot: the Opus coder's count (filled circle) and the GPT-6 Sol coder's (open diamond)."""
    if a != b:
        c.line(xof(a), y, xof(b), y, colour, 1.4)
        c.circle(xof(a), y, 3.2, fill=colour)
        c.diamond(xof(b), y, 3.8, stroke=colour)
    else:  # the two coders agree: the circle is drawn inside the diamond
        c.diamond(xof(b), y, 4.6, stroke=colour)
        c.circle(xof(a), y, 2.1, fill=colour)


# ---------------------------------------------------------------------------------------------------------------------
# P1: one learner turn (proposed in place of F1)
# ---------------------------------------------------------------------------------------------------------------------
def wrap(s, n):
    out, line = [], ''
    for w in s.split():
        if line and len(line) + 1 + len(w) > n:
            out.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    return out + ([line] if line else [])


def p1_one_turn():
    W = 600
    c = Svg(W, 10)
    CX, CW = 8, 250          # the steps
    RX, RW = 300, 292        # what the request contains
    MODEL, CODE, LEARN = (CREAM, ORANGE), ('#f3f3f3', GREY), ('#e8f0fa', BLUE)
    steps = [
        ('The learner writes a turn', 'model', LEARN,
         ['A live GPT-6 Sol low model with a written profile: bored, confused, resisting or over-confident.'], None, None),
        ('1. Resistance reader', 'classifier', CODE,
         ['Does the turn resist, and is it the same concern as before? Its label goes into the playwright\'s request.'],
         None, None),
        ('2. Playwright: strategy step', 'model call', MODEL,
         ['Answers: the reading (progressing, stalled, disengaged, confused, resisting); the strategy line (keep, or '
          'switch to a named strategy); the character line; the reply note. May rewrite the part.'],
         ['The scene rules (and fidelity rules at LOW or HIGH); the dialogue so far; the evidence graph; the part; her '
          'earlier notes; the strategy in force and those tried; the repertoire; the resistance label.'],
         'Removed with step 3 in NP (Finding 10)'),
        ('3. Rules, applied by the runner', 'code', CODE,
         ['Is a switch due? If so, the rules choose the strategy from her reading, or accept or refuse her proposal. '
          'When they override her, her character line is withheld.'], None, None),
        ('4. Actor writes the draft', 'model call', MODEL,
         ['Plays the character and writes the reply. A record is shown by its release mark or by quoting it whole.'],
         ['The actor text; the part; four guidelines; the scene material, with the records held privately; the dialogue '
          'so far, the learner\'s lines quoted as a scene partner\'s; her note on the character. While a strategy is in '
          'force: the strategy section, and a line for this reply (her reply note; at the reply where a strategy '
          'starts, the strategy\'s first-reply line). No fidelity rules.'],
         'Actor text and part header removed in "without the actor\'s texts"'),
        ('5. Playwright as critic', 'model calls', MODEL,
         ['KEEP, or REVISE with a reason. After REVISE the actor writes an amendment and the playwright reads it again '
          '(the recheck).'],
         ['The scene rules (and fidelity rules); the dialogue so far; the evidence graph; the part; her note; the draft '
          'and the records it would show; the strategy in force.'],
         'Removed in NV (Finding 10)'),
        ('6. Runner checks and sends the reply', 'code', CODE,
         ['Records which records were shown; refuses a reply that breaks the lesson\'s rules. The '
          'reply is the only text the learner sees.'], None, None),
    ]
    c.text(CX, 14, 'The steps of one learner turn', 9, bold=True)
    c.text(RX, 14, 'What the model\'s request contains', 9, bold=True)
    y, pos = 24, []
    for title, tag, (fill, stroke), lines, req, removed in steps:
        rows = sum((wrap(s, 50) for s in lines), [])
        rrows = sum((wrap(s, 62) for s in req), []) if req else []
        h = max(20 + 10.5 * len(rows) + 4, (16 + 10.5 * len(rrows) + 4) if req else 0)
        if removed:
            h += 11
        c.rect(CX, y, CW, h, fill, stroke, rx=5)
        c.text(CX + 7, y + 13, title, 8.6, bold=True)
        c.text(CX + CW - 6, y + 13, tag, 7, GREY, anchor='end')
        for k, r in enumerate(rows):
            c.text(CX + 7, y + 25 + 10.5 * k, r, 7.6)
        if removed:
            c.text(CX + 7, y + h - 5, removed, 7.2, MID, italic=True)
        if req:
            c.rect(RX, y, RW, h, '#ffffff', GREY, rx=5)
            for k, r in enumerate(rrows):
                c.text(RX + 7, y + 13 + 10.5 * k, r, 7.6)
            c.arrow(RX, y + h / 2, CX + CW + 1, y + h / 2, GREY, 0.8)
        pos.append((y, h))
        y += h + 13
    for (y1, h1), (y2, _) in zip(pos, pos[1:]):
        c.arrow(CX + CW / 2, y1 + h1, CX + CW / 2, y2 - 1)
    # The reply returns to the learner along the gap between the two columns.
    (y0, h0), (y6, h6) = pos[0], pos[-1]
    xr = CX + CW + 20
    c.line(CX + CW, y6 + h6 / 2, xr, y6 + h6 / 2, BLUE, 1.5)
    c.line(xr, y6 + h6 / 2, xr, y0 + h0 / 2, BLUE, 1.5)
    c.arrow(xr, y0 + h0 / 2, CX + CW + 1, y0 + h0 / 2, BLUE, 1.5)
    c.body.append(f'<text x="{xr + 4}" y="{(y0 + y6) / 2:.1f}" font-size="7.2" fill="{BLUE}" '
                  f'transform="rotate(90 {xr + 4} {(y0 + y6) / 2:.1f})" text-anchor="middle">the reply goes to the '
                  'learner</text>')
    c.text(CX, y + 2, 'Orange: a model call (GPT-6.1 Terra high in the main studies). Grey: code or a classifier. Not drawn: '
           'the setup, where the playwright writes the part', 7.2, MID)
    c.text(CX, y + 12, 'and a self-check call reads it. The plain tutor of Finding 9 has one model call per reply, from the '
           'character, the scene material and the dialogue.', 7.2, MID)
    c.h = int(y + 20)
    write('P1-one-turn', c)


# ---------------------------------------------------------------------------------------------------------------------
# P2: Finding 9 on four tutor models
# ---------------------------------------------------------------------------------------------------------------------
F9 = [  # model, [(arm, Opus coder, GPT-6 Sol coder, lessons)]; None = not run.  c01, c03, c16, c24 scripts.
    ('GPT-6.1 Terra (main studies)', [('Plain tutor', 1, 1, 20), ('Told the twelve strategies', 4, 5, 20),
                                  ('Given the earlier Appendix L', 11, 14, 20), ('Layered tutor', 15, 18, 20),
                                  ('Layered, without the actor\'s texts', 18, 20, 20)]),
    ('Claude Sonnet 5.5', [('Plain tutor (19 lessons)', 4, 3, 19), ('Told the twelve strategies', 9, 11, 20),
                           ('Given the earlier Appendix L', 17, 18, 20), ('Layered tutor', 19, 20, 20),
                           ('Layered, without the actor\'s texts', 17, 20, 20)]),
    ('GPT-6.1 Sol', [('Plain tutor', 2, 4, 20), ('Told the twelve strategies', 7, 7, 20), ('Given the earlier Appendix L', 11, 13, 20),
                     ('Layered tutor', 20, 20, 20), ('Layered, without the actor\'s texts', 17, 20, 20)]),
    ('Gemini 4 Hydrogen', [('Plain tutor', 1, 2, 20), ('Told the twelve strategies', None, None, 0),
                           ('Given the earlier Appendix L', None, None, 0), ('Layered tutor', 19, 20, 20),
                           ('Layered, without the actor\'s texts', 20, 20, 20)]),
]


def p2_finding9():
    W, X0, X1 = 520, 190, 440
    xof = lambda v: X0 + (X1 - X0) * v / 20
    rows = sum(1 + len(a) for _, a in F9)
    c = Svg(W, 0)
    c.text((X0 + X1) / 2, 13, 'Lessons of 20 with a tutor-started change of strategy', 8.6, bold=True, anchor='middle')
    c.text(W - 8, 13, 'Opus / Sol', 8, bold=True, anchor='end')
    top, y = 22, 22
    bottom = top + 14 * rows + 4
    for t in range(0, 21, 5):
        c.line(xof(t), top, xof(t), bottom, LIGHT if t else RULE, 0.8)
    for model, arms in F9:
        y += 14
        c.text(8, y - 3, model, 8.4, bold=True)
        for name, a, b, n in arms:
            y += 14
            colour = BLUE if name == 'Layered tutor' else DARK
            c.text(16, y - 3, name, 8, colour if colour == BLUE else DARK, bold=colour == BLUE)
            if a is None:
                c.text(X0 + 4, y - 3, 'not run', 7.6, GREY, italic=True)
                continue
            two_coders(c, xof, y - 6, a, b, colour)
            c.text(W - 8, y - 3, f'{a} / {b}', 8, anchor='end')
    c.line(X0, bottom, X1, bottom, DARK, 0.8)
    for t in range(0, 21, 5):
        c.line(xof(t), bottom, xof(t), bottom + 3, DARK, 0.8)
        c.text(xof(t), bottom + 12, str(t), 7.6, anchor='middle')
    coder_legend(c, X0 - 6, bottom + 28)
    c.h = int(bottom + 36)
    write('P2-change-by-tutor-model', c)


# ---------------------------------------------------------------------------------------------------------------------
# P3: Terra, the layers added and removed, with the drama reader against the layered tutor
# ---------------------------------------------------------------------------------------------------------------------
P3 = [  # group, [(arm, Opus, Sol, layered preferred, arm preferred, tie, no verdict)]. c01, c02, c04, c10b.
    ('One model plays the character: no playwright, no rules', [
        ('Plain tutor', 1, 1, 17, 1, 0, 2), ('Told the twelve strategies', 4, 5, 12, 0, 0, 4),
        ('Given the earlier Appendix L', 11, 14, 16, 3, 0, 1)]),
    ('Plain tutor with four parts added (Finding 11)', [
        ('Reading step, rules, strategy line, instruction', 15, 17, 9, 3, 0, 8)]),
    ('Layered tutor with one layer removed (Finding 10)', [
        ('Without the playwright\'s call between turns', 3, 3, 20, 0, 0, 0),
        ('Without the review of drafts', 18, 19, 4, 6, 1, 9),
        ('Without the actor\'s texts', 18, 20, 2, 10, 0, 8)]),
    ('The layered tutor (drama-v2.17)', [('Layered tutor', 15, 18, None, None, None, None)]),
]


def p3_layers():
    W = 640
    LX, AX0, AX1, AV = 8, 228, 368, 404
    xof = lambda v: AX0 + (AX1 - AX0) * v / 20
    MID_X, UNIT, NV = 520, 4.4, W - 8
    rows = sum(1 + len(a) for _, a in P3)
    c = Svg(W, 0)
    c.text((AX0 + AX1) / 2, 11, 'Lessons of 20 with a change', 8.4, bold=True, anchor='middle')
    c.text((AX0 + AX1) / 2, 21, 'of strategy', 8.4, bold=True, anchor='middle')
    c.text(AV, 21, 'Opus / Sol', 7.6, bold=True, anchor='middle')
    c.text(MID_X, 11, 'Drama reader, pairs against the layered tutor', 8.4, bold=True, anchor='middle')
    c.text(MID_X - 4, 21, 'layered preferred', 7.6, MID, anchor='end')
    c.text(MID_X + 4, 21, 'this arm preferred', 7.6, MID)
    c.text(NV, 21, 'no verdict', 7.6, MID, anchor='end')
    top, y = 28, 28
    bottom = top + 14 * rows + 2
    for t in range(0, 21, 5):
        c.line(xof(t), top, xof(t), bottom, LIGHT if t else RULE, 0.8)
    c.line(MID_X, top, MID_X, bottom, DARK, 0.8)
    for group, arms in P3:
        y += 14
        c.text(LX, y - 3, group, 8.2, bold=True)
        for name, a, b, lp, ap, tie, nv in arms:
            y += 14
            colour = BLUE if name == 'Layered tutor' else DARK
            c.text(LX + 8, y - 3, name, 7.9, colour, bold=colour == BLUE)
            two_coders(c, xof, y - 6, a, b, colour)
            c.text(AV, y - 3, f'{a} / {b}', 7.9, anchor='middle')
            if lp is None:
                c.text(MID_X + 6, y - 3, 'the comparison', 7.6, GREY, italic=True)
                continue
            c.rect(MID_X - lp * UNIT, y - 11, lp * UNIT, 9, GREY)
            c.rect(MID_X, y - 11, ap * UNIT, 9, ORANGE)
            c.text(MID_X - lp * UNIT - 3, y - 3.5, str(lp), 7.6, anchor='end')
            c.text(MID_X + ap * UNIT + 3, y - 3.5, str(ap), 7.6)
            c.text(NV, y - 3.5, str(nv) + (f' (tie {tie})' if tie else ''), 7.6, anchor='end')
    c.line(AX0, bottom, AX1, bottom, DARK, 0.8)
    for t in range(0, 21, 5):
        c.line(xof(t), bottom, xof(t), bottom + 3, DARK, 0.8)
        c.text(xof(t), bottom + 12, str(t), 7.6, anchor='middle')
    coder_legend(c, LX, bottom + 28)
    c.text(LX, bottom + 41, 'GPT-6.1 Terra high in every tutor role. Drama: a verdict counts when Claude Opus 5.5 and GPT-6.1 Sol '
           'readers each give it in both orders.', 7.2, MID)
    c.text(LX, bottom + 51, '"Told" has 16 pairs matched on world and learner.', 7.2, MID)
    c.h = int(bottom + 58)
    write('P3-layers-added-and-removed', c)


# ---------------------------------------------------------------------------------------------------------------------
# P4: Finding 12, the learned draw against the hardwired rule in eighteen final tests
# ---------------------------------------------------------------------------------------------------------------------
P4 = [  # group, [(test, (learned Opus, learned Sol), (hardwired Opus, hardwired Sol), hardwired pairs, learned pairs, nv)]
    ('Score: drawn strategy carried out, no fault (15 Nov)', [   # c13, d01, d02, d03
        ('GPT-6.1 Terra, old lines', (19, 20), (18, 18), 7, 5, 8), ('GPT-6.1 Terra, new lines', (14, 16), (15, 19), 4, 5, 11),
        ('GPT-6.1 Sol', (18, 20), (18, 20), 6, 2, 12), ('Claude Sonnet 5.5', (19, 19), (20, 20), 4, 6, 10)]),
    ('Score also on a later reply (16 Nov)', [   # later-reply-20261116/final.py
        ('GPT-6.1 Terra', (18, 19), (19, 19), 9, 3, 8), ('GPT-6.1 Terra, second run', (17, 17), (19, 18), 7, 2, 11),
        ('GPT-6.1 Sol', (16, 17), (20, 20), 3, 4, 13), ('GPT-6.1 Sol, second run', (17, 18), (19, 19), 4, 5, 11),
        ('Claude Sonnet 5.5', (19, 19), (20, 20), 9, 3, 8)]),
    ('Drama a quarter of the score', [   # drama-score-20261116/final.py
        ('GPT-6.1 Terra', (17, 20), (19, 20), 7, 3, 10), ('GPT-6.1 Sol', (17, 17), (20, 19), 6, 2, 12),
        ('Claude Sonnet 5.5', (19, 20), (20, 20), 7, 5, 8)]),
    ('Drama half the score, no cap', [   # cap-variety-20261116/final.py
        ('GPT-6.1 Terra', (18, 20), (16, 19), 3, 6, 11), ('GPT-6.1 Terra, second run', (15, 19), (18, 18), 5, 4, 11),
        ('GPT-6.1 Sol', (17, 16), (20, 20), 5, 5, 10), ('GPT-6.1 Sol, second run', (17, 18), (20, 20), 3, 1, 16),
        ('Claude Sonnet 5.5', (18, 19), (19, 19), 3, 5, 12), ('Claude Sonnet 5.5, second run', (20, 19), (19, 20), 4, 5, 11)]),
]
OPENINGS = [('Bored', 4.08, 1.0), ('Confused', 4.08, 1.62), ('Resisting', 4.23, 1.31), ('Over-confident', 4.08, 1.23)]


def p4_learned_draw():
    W = 640
    LX, AX0, AX1, AV = 8, 200, 350, 390
    lo, hi = -6, 4
    xof = lambda v: AX0 + (AX1 - AX0) * (v - lo) / (hi - lo)
    MID_X, UNIT, NV = 520, 6.0, W - 8
    rows = sum(1 + len(a) for _, a in P4)
    c = Svg(W, 0)
    c.text(LX, 11, 'A', 10, bold=True)
    c.text((AX0 + AX1) / 2, 11, 'Change of strategy: learned draw minus', 8.4, bold=True, anchor='middle')
    c.text((AX0 + AX1) / 2, 21, 'hardwired rule, lessons of 20', 8.4, bold=True, anchor='middle')
    c.text(AV, 21, 'Opus / Sol', 7.6, bold=True, anchor='middle')
    c.text(MID_X - 70, 11, 'B', 10, bold=True)
    c.text(MID_X, 11, 'Drama reader, pairs of 20', 8.4, bold=True, anchor='middle')
    c.text(MID_X - 4, 21, 'hardwired preferred', 7.6, MID, anchor='end')
    c.text(MID_X + 4, 21, 'learned preferred', 7.6, MID)
    c.text(NV, 21, 'no verdict', 7.6, MID, anchor='end')
    top, y = 28, 28
    bottom = top + 14 * rows + 2
    for t in range(lo, hi + 1):
        c.line(xof(t), top, xof(t), bottom, RULE if t == 0 else LIGHT, 1.2 if t == 0 else 0.6)
    c.line(xof(-4), top, xof(-4), bottom, GREY, 0.8, '3 2')
    c.line(MID_X, top, MID_X, bottom, DARK, 0.8)
    for group, tests in P4:
        y += 14
        c.text(LX, y - 3, group, 8.2, bold=True)
        for name, (lo_, ls), (ho, hs), hp, lp, nv in tests:
            y += 14
            c.text(LX + 8, y - 3, name, 7.9)
            two_coders(c, xof, y - 6, lo_ - ho, ls - hs, DARK)
            c.text(AV, y - 3, f'{lo_ - ho:+d} / {ls - hs:+d}'.replace('+0', '0'), 7.9, anchor='middle')
            c.rect(MID_X - hp * UNIT, y - 11, hp * UNIT, 9, GREY)
            c.rect(MID_X, y - 11, lp * UNIT, 9, BLUE)
            c.text(MID_X - hp * UNIT - 3, y - 3.5, str(hp), 7.6, anchor='end')
            c.text(MID_X + lp * UNIT + 3, y - 3.5, str(lp), 7.6)
            c.text(NV, y - 3.5, str(nv), 7.6, anchor='end')
    c.line(AX0, bottom, AX1, bottom, DARK, 0.8)
    for t in range(lo, hi + 1, 2):
        c.line(xof(t), bottom, xof(t), bottom + 3, DARK, 0.8)
        c.text(xof(t), bottom + 12, f'{t:+d}' if t else '0', 7.6, anchor='middle')
    c.text(xof(-4), bottom + 22, 'four lessons fewer', 7.2, MID, anchor='middle')
    coder_legend(c, LX, bottom + 36)
    # Panel C: different strategies opening five lessons of one learner type
    y0 = bottom + 58
    c.text(LX, y0, 'C', 10, bold=True)
    C0, C1 = 200, 470
    cx = lambda v: C0 + (C1 - C0) * (v - 1) / 4
    c.text((C0 + C1) / 2, y0, 'Different strategies opening five lessons with one learner type, mean over 13 final tests',
           8.4, bold=True, anchor='middle')
    yy = y0 + 6
    for t in range(1, 6):
        c.line(cx(t), yy, cx(t), yy + 14 * len(OPENINGS) + 4, LIGHT, 0.8)
    for name, learned, hard in OPENINGS:
        yy += 14
        c.text(LX + 8, yy - 3, name, 7.9)
        c.line(cx(hard), yy - 6, cx(learned), yy - 6, RULE, 1.4)
        c.circle(cx(hard), yy - 6, 3.4, fill=GREY)
        c.circle(cx(learned), yy - 6, 3.4, fill=BLUE)
        c.text(cx(learned) + 7, yy - 3, f'{learned:.1f}', 7.6)
        c.text(cx(hard) - 7, yy - 3, f'{hard:.1f}', 7.6, anchor='end')
    yy += 4
    c.line(C0, yy, C1, yy, DARK, 0.8)
    for t in range(1, 6):
        c.line(cx(t), yy, cx(t), yy + 3, DARK, 0.8)
        c.text(cx(t), yy + 12, str(t), 7.6, anchor='middle')
    c.circle(C1 + 18, y0 + 17, 3.4, fill=BLUE)
    c.text(C1 + 25, y0 + 20, 'learned draw', 7.8)
    c.circle(C1 + 18, y0 + 31, 3.4, fill=GREY)
    c.text(C1 + 25, y0 + 34, 'hardwired rule', 7.8)
    c.h = int(yy + 20)
    write('P4-learned-draw-eighteen-tests', c)


# ---------------------------------------------------------------------------------------------------------------------
# P5: F2 redrawn (Findings 4 and 5): later replies carried out and the drama reader, with every pair accounted for
# ---------------------------------------------------------------------------------------------------------------------
P5 = [  # label, default later (of, n), fix later (of, n), default pairs, fix pairs, tie, no verdict. ARXIV.md Tables 7, 8.
    ('Finding 4: both parts of the fix (drama-v2.3)', (51, 153), (75, 125), 48, 21, 2, 46),
    ('Finding 5: critic\'s check only (drama-v2.4)', (46, 156), (69, 120), 42, 24, 6, 48),
    ('Finding 5: both, disruptive only (drama-v2.4b)', (46, 156), (78, 145), 43, 25, 6, 46),
]


def p5_keep_line():
    W = 640
    LX, AX0, AX1 = 8, 210, 350
    xof = lambda v: AX0 + (AX1 - AX0) * v / 100
    MID_X, UNIT, NV = 488, 2.1, W - 8
    c = Svg(W, 0)
    c.text((AX0 + AX1) / 2, 11, 'Later replies carried out, %', 8.4, bold=True, anchor='middle')
    c.text((AX0 + AX1) / 2, 21, '(both delivery coders yes)', 7.6, MID, anchor='middle')
    c.text(MID_X, 11, 'Drama reader, pairs (117, 120, 120)', 8.4, bold=True, anchor='middle')
    c.text(MID_X - 4, 21, 'default preferred', 7.6, MID, anchor='end')
    c.text(MID_X + 4, 21, 'fix preferred', 7.6, MID)
    c.text(NV, 21, 'tie / none', 7.6, MID, anchor='end')
    top, y = 28, 28
    bottom = top + 22 * len(P5) + 4
    for t in range(0, 101, 20):
        c.line(xof(t), top, xof(t), bottom, LIGHT if t else RULE, 0.8)
    c.line(MID_X, top, MID_X, bottom, DARK, 0.8)
    for name, (da, dn), (fa, fn), dp, fp, tie, nv in P5:
        y += 22
        c.text(LX, y - 5, name, 7.9)
        d, f = 100 * da / dn, 100 * fa / fn
        c.line(xof(d), y - 8, xof(f), y - 8, RULE, 1.6)
        c.circle(xof(d), y - 8, 3.6, fill=GREY)
        c.circle(xof(f), y - 8, 3.6, fill=BLUE)
        c.text(xof(d) - 6, y - 5, f'{d:.0f}', 7.6, anchor='end')
        c.text(xof(f) + 6, y - 5, f'{f:.0f}', 7.6)
        c.rect(MID_X - dp * UNIT, y - 13, dp * UNIT, 10, GREY)
        c.rect(MID_X, y - 13, fp * UNIT, 10, BLUE)
        c.text(MID_X - dp * UNIT - 3, y - 5, str(dp), 7.6, anchor='end')
        c.text(MID_X + fp * UNIT + 3, y - 5, str(fp), 7.6)
        c.text(NV, y - 5, f'{tie} / {nv}', 7.6, anchor='end')
    c.line(AX0, bottom, AX1, bottom, DARK, 0.8)
    for t in range(0, 101, 20):
        c.line(xof(t), bottom, xof(t), bottom + 3, DARK, 0.8)
        c.text(xof(t), bottom + 12, str(t), 7.6, anchor='middle')
    x = LX
    for col, lab in ((GREY, 'default (drama-v2.2)'), (BLUE, 'the keep-line fix')):
        c.circle(x + 4, bottom + 25, 3.6, fill=col)
        c.text(x + 11, bottom + 28, lab, 7.8)
        x += 120
    c.text(LX, bottom + 41, 'GPT-6.1 Terra. Finding 4 and Finding 5 are separate runs of 120 lessons per arm (117 in Finding 4\'s fix arm); '
           'the two Finding 5 rows share one default arm.', 7.2, MID)
    c.h = int(bottom + 48)
    write('P5-keep-line-delivery-and-drama', c)


# ---------------------------------------------------------------------------------------------------------------------
# P6: the drama reader's pairs for the whole-lesson comparisons that have no other figure (Figure 5 shortened)
# ---------------------------------------------------------------------------------------------------------------------
P6 = [  # tested arm, comparison arm, tested preferred, comparison preferred, tie, no verdict, pairs. ARXIV.md, Appendix J.
    ('Finding 1: rules by learner type', 'the playwright chooses (drama-v2.1)', 16, 4, 2, 18, 40),
    ('Finding 6: planned return (drama-v2.7)', 'drama-v2.2', 17, 10, 0, 21, 48),
    ('Finding 7: personal material', 'none', 24, 2, 1, 13, 40),
    ('Finding 8: rules by reading (drama-v2.17)', 'drama-v2.16', 26, 2, 0, 12, 40),
    ('Finding 8 arms, Opus playwright: drama-v2.17', 'drama-v2.16', 3, 5, 0, 8, 16),
    ('Finding 8 arms, Sonnet tutor: drama-v2.17', 'drama-v2.16', 6, 1, 0, 9, 16),
    ('Tedium read as disengaged (drama-v2.20)', 'drama-v2.17, bored learner', 0, 3, 0, 9, 12),
]


def p6_drama_pairs():
    W = 640
    LX, MID_X, UNIT = 8, 430, 4.6
    c = Svg(W, 0)
    c.text(LX, 21, 'Tested arm', 8.4, bold=True)
    c.text(LX + 228, 21, 'against', 8.4, bold=True)
    c.text(MID_X - 4, 21, 'comparison preferred', 7.6, MID, anchor='end')
    c.text(MID_X + 4, 21, 'tested preferred', 7.6, MID)
    c.text(W - 46, 21, 'tie / none', 7.6, MID, anchor='end')
    c.text(W - 8, 21, 'pairs', 7.6, MID, anchor='end')
    top, y = 28, 28
    bottom = top + 22 * len(P6)
    c.line(MID_X, top, MID_X, bottom, DARK, 0.8)
    for name, comp, tp, cp, tie, nv, n in P6:
        y += 22
        c.text(LX, y - 9, name, 7.9)
        c.text(LX + 228, y - 9, comp, 7.9, MID)
        c.rect(MID_X - cp * UNIT, y - 17, cp * UNIT, 10, GREY)
        c.rect(MID_X, y - 17, tp * UNIT, 10, BLUE)
        c.text(MID_X - cp * UNIT - 3, y - 9, str(cp), 7.6, anchor='end')
        c.text(MID_X + tp * UNIT + 3, y - 9, str(tp), 7.6)
        c.text(W - 46, y - 9, f'{tie} / {nv}', 7.6, anchor='end')
        c.text(W - 8, y - 9, str(n), 7.6, anchor='end')
    c.text(LX, bottom + 12, 'Whole lessons, GPT-6.1 Terra high unless named. A verdict counts only when a Claude Opus 5.5 and a '
           'GPT-6.1 Sol reader each give it in both orders.', 7.2, MID)
    c.h = int(bottom + 20)
    write('P6-drama-reader-pairs-whole-lessons', c)


# ---------------------------------------------------------------------------------------------------------------------
# P7: one tutor role at a time on another model, drama-v2.17 against drama-v2.16 at 12 fork points (Appendix J)
# ---------------------------------------------------------------------------------------------------------------------
P7 = [  # role and model, first reply v2.17, v2.16, drama pairs v2.17, v2.16. Appendix J.
    ('Every role GPT-6.1 Terra', 11, 0, 5, 2), ('Playwright Claude Opus 5.5', 11, 3, 0, 8), ('Playwright GPT-6.1 Sol', 11, 1, 2, 5),
    ('Playwright Qwen 3.8 27B', 10, 1, 4, 6), ('Actor Claude Opus 5.5', 10, 1, 4, 2), ('Actor GPT-6.1 Sol', 12, 1, 5, 2),
    ('Actor Qwen 3.8 27B', 11, 1, 7, 3), ('Critic Claude Opus 5.5', 10, 3, 4, 2), ('Critic GPT-6.1 Sol', 11, 1, 5, 2),
    ('Critic Qwen 3.8 27B', 8, 2, 7, 2),
]


def p7_role_model_grid():
    W = 600
    LX, AX0, AX1, MID_X, UNIT = 8, 150, 300, 440, 6.0
    xof = lambda v: AX0 + (AX1 - AX0) * v / 12
    c = Svg(W, 0)
    c.text((AX0 + AX1) / 2, 11, 'First reply carried out, of 12', 8.4, bold=True, anchor='middle')
    c.text(MID_X, 11, 'Drama reader, pairs of 12', 8.4, bold=True, anchor='middle')
    c.text(MID_X - 4, 21, 'drama-v2.16 preferred', 7.6, MID, anchor='end')
    c.text(MID_X + 4, 21, 'drama-v2.17 preferred', 7.6, MID)
    c.text(W - 8, 21, 'neither', 7.6, MID, anchor='end')
    top, y = 28, 28
    bottom = top + 16 * len(P7) + 2
    for t in range(0, 13, 3):
        c.line(xof(t), top, xof(t), bottom, LIGHT if t else RULE, 0.8)
    c.line(MID_X, top, MID_X, bottom, DARK, 0.8)
    for name, r, a, dr, da in P7:
        y += 16
        c.text(LX, y - 4, name, 7.9)
        c.line(xof(a), y - 7, xof(r), y - 7, RULE, 1.4)
        c.circle(xof(a), y - 7, 3.2, fill=GREY)
        c.circle(xof(r), y - 7, 3.2, fill=BLUE)
        c.text(xof(a) - 6, y - 4.5, str(a), 7.6, anchor='end')
        c.text(xof(r) + 6, y - 4.5, str(r), 7.6)
        c.rect(MID_X - da * UNIT, y - 12, da * UNIT, 9, GREY)
        c.rect(MID_X, y - 12, dr * UNIT, 9, BLUE)
        c.text(MID_X - da * UNIT - 3, y - 4.5, str(da), 7.6, anchor='end')
        c.text(MID_X + dr * UNIT + 3, y - 4.5, str(dr), 7.6)
        c.text(W - 8, y - 4.5, str(12 - dr - da), 7.6, anchor='end')
    c.line(AX0, bottom, AX1, bottom, DARK, 0.8)
    for t in range(0, 13, 3):
        c.line(xof(t), bottom, xof(t), bottom + 3, DARK, 0.8)
        c.text(xof(t), bottom + 12, str(t), 7.6, anchor='middle')
    x = LX
    for col, lab in ((GREY, 'drama-v2.16'), (BLUE, 'drama-v2.17')):
        c.circle(x + 4, bottom + 25, 3.2, fill=col)
        c.text(x + 11, bottom + 28, lab, 7.8)
        x += 90
    c.text(x + 10, bottom + 28, 'Only the Opus playwright\'s 0 to 8 is significant (two-sided sign test, p = 0.008). '
           '"Neither": a tie or no verdict.', 7.2, MID)
    c.h = int(bottom + 36)
    write('P7-role-model-grid', c)


if __name__ == '__main__':
    p1_one_turn()
    p2_finding9()
    p3_layers()
    p4_learned_draw()
    p5_keep_line()
    p6_drama_pairs()
    p7_role_model_grid()
