"""Opening figures for the simulator guide (§1), from real simulate output.

Self-contained: give it an EvalCore data dir and an output dir, and it runs the
sims it needs. No run-directory layout is assumed.

    python3 docs/simulator-guide/make_opening_assets.py <data-dir> [out-dir]

<data-dir> holds glucose/doses/carbs/therapy.json (+ optional disruptions.csv).
Figures land next to this script by default: premise.png, realworld.png, paired.png.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[2]
BIN = REPO / '.build/release/loop-eval'
DATA = Path(sys.argv[1]).expanduser()
OUT = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else Path(__file__).resolve().parent

# Window: SHORT drives the three-panel premise figure, LONG the paired statistics.
SHORT_START, SHORT_END = '2026-06-01T00:00:00Z', '2026-06-06T00:00:00Z'
LONG_START, LONG_END = '2026-05-10T00:00:00Z', '2026-06-30T00:00:00Z'
# Divergence begins evalWarmupHours (16) + counterfactualBurnIn (6) after --start.
CF_ACTIVE = pd.Timestamp('2026-06-01T22:00:00Z')
PREMISE_HOURS = 12
REALWORLD_START, REALWORLD_DAYS = pd.Timestamp('2026-06-18T04:00:00Z'), 4

plt.rcParams.update({'figure.dpi': 150, 'font.size': 9.5,
                     'axes.grid': True, 'grid.alpha': .25, 'grid.linewidth': .5,
                     'axes.edgecolor': '#b6c4ca', 'axes.labelcolor': '#33444e',
                     'xtick.color': '#61737e', 'ytick.color': '#61737e',
                     'font.sans-serif': ['IBM Plex Sans', 'DejaVu Sans']})
FIELD, ACCENT, MUTED, WARN, BAND = '#2b4a6f', '#0d6e66', '#61737e', '#9a5416', '#dcebe3'
BOX = dict(boxstyle='round,pad=.35', fc='white', ec='none', alpha=.86)

work = Path(tempfile.mkdtemp(prefix='loopeval-opening-'))

def sim(tag, start, end, extra=()):
    out = work / f'{tag}.json'
    cmd = [str(BIN), 'simulate', '--data-dir', str(DATA), '--start', start, '--end', end,
           '--candidate-counterfactual', '--trace-out', str(out), *extra]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def trace(p, key):
    d = pd.DataFrame(json.load(open(p))[key])
    d['t'] = pd.to_datetime(d.t)
    return d.dropna(subset=['bg']) if 'bg' in d else d

print('running sims …')
nie_csv = work / 'nie.csv'
short_id = sim('short_id', SHORT_START, SHORT_END)
short_080 = sim('short_080', SHORT_START, SHORT_END, ['--candidate-insulin-needs', '0.80'])
short_125 = sim('short_125', SHORT_START, SHORT_END, ['--candidate-insulin-needs', '1.25'])
sim('short_fid', SHORT_START, SHORT_END,
    ['--candidate-infer-sensitivity', '--candidate-dump-nie-csv', str(nie_csv)])
long_ref = sim('long_ref', LONG_START, LONG_END)
long_cand = sim('long_cand', LONG_START, LONG_END, ['--candidate-insulin-needs', '1.05'])

# ---------------------------------------------------------------- 1. premise
LO, HI = CF_ACTIVE, CF_ACTIVE + pd.Timedelta(hours=PREMISE_HOURS)
cut = lambda d, k='t': d[(d[k] >= LO) & (d[k] < HI)]
hrs = lambda s: (s - LO).dt.total_seconds() / 3600
ar = cut(trace(short_id, 'actual'))
nr = cut(pd.read_csv(nie_csv, parse_dates=['t']))
noins = ar.bg.iloc[0] + nr.nie.cumsum()
c080, c125 = cut(trace(short_080, 'counter')), cut(trace(short_125, 'counter'))

fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.1))
for ax in (axes[0], axes[2]):
    ax.add_patch(Rectangle((0, 70), PREMISE_HOURS, 110, color=BAND, zorder=0)); ax.set_ylim(40, 320)
for ax in axes:
    ax.set_xlim(0, PREMISE_HOURS); ax.set_xticks(range(0, PREMISE_HOURS + 1, 3)); ax.set_xlabel('hours')

axes[0].plot(hrs(ar.t), ar.bg, '-', color=FIELD, lw=2.1)
axes[0].set_title('1 · RECORDING', color=FIELD, fontsize=11.5, fontweight='bold', loc='left')
axes[0].set_ylabel('BG (mg/dL)')
axes[0].text(.03, .035, 'CGM + delivered insulin + carbs,\nexactly as it ran', fontsize=9,
             color='#33444e', va='bottom', transform=axes[0].transAxes, bbox=BOX)

axes[1].add_patch(Rectangle((0, 70), PREMISE_HOURS, 110, color=BAND, zorder=0))
axes[1].plot(hrs(nr.t), noins, '--', color=MUTED, lw=2.2)
axes[1].plot(hrs(ar.t), ar.bg, '-', color=FIELD, lw=1.2, alpha=.35)
axes[1].set_ylim(40, 1250)
axes[1].set_title('2 · SUBSTRATE   (− E$_{field}$)', color=MUTED, fontsize=11.5, fontweight='bold', loc='left')
axes[1].set_ylabel('BG (mg/dL) — note scale')
axes[1].annotate('+%,d mg/dL in %d h with nothing\nopposing it — the scale of the work\ninsulin does continuously'
                 .replace('%,d', f'{int(noins.max() - noins.iloc[0]):,}') % PREMISE_HOURS,
                 xy=(PREMISE_HOURS * .93, noins.max() * .97), xytext=(.5, 620), fontsize=8.5,
                 color='#33444e', bbox=BOX,
                 arrowprops=dict(arrowstyle='->', color=MUTED, lw=.9))
axes[1].text(.03, .035, 'Non-insulin physiology: absorption, EGP,\nexercise, sensor noise  (recorded, faint)',
             fontsize=9, color='#33444e', va='bottom', transform=axes[1].transAxes, bbox=BOX)

axes[2].plot(hrs(ar.t), ar.bg, '-', color=FIELD, lw=1.3, alpha=.4, label='recorded')
axes[2].plot(hrs(c125.t), c125.bg, '-', color=ACCENT, lw=2.1, label='insulin-needs ×1.25')
axes[2].plot(hrs(c080.t), c080.bg, '-', color=WARN, lw=2.1, label='insulin-needs ×0.80')
axes[2].set_title('3 · COUNTERFACTUAL   (+ E$_{cand}$)', color=ACCENT, fontsize=11.5, fontweight='bold', loc='left')
axes[2].legend(loc='upper left', fontsize=8.2, framealpha=.95)
axes[2].text(.03, .035, 'Each arm runs its own closed loop\nforward on the same substrate',
             fontsize=9, color='#33444e', va='bottom', transform=axes[2].transAxes, bbox=BOX)
fig.suptitle('The counterfactual premise — borrow the physiology, re-run the insulin',
             fontsize=13, fontweight='bold', x=.004, ha='left', y=1.02)
fig.tight_layout(); fig.savefig(OUT / 'premise.png', bbox_inches='tight', facecolor='white'); plt.close()

# ------------------------------------------------------------- 2. real world
a = trace(long_ref, 'actual'); dl = trace(long_ref, 'delivery')
LO, HI = REALWORLD_START, REALWORLD_START + pd.Timedelta(days=REALWORLD_DAYS)
span = REALWORLD_DAYS * 24
H = lambda s: (pd.to_datetime(pd.Series(s)) - LO).dt.total_seconds().values / 3600
ar = cut(a)
a2 = a.copy(); a2['d'] = a2.t.diff().dt.total_seconds() / 60
gaps = cut(a2[a2.d >= 15])
mb = cut(dl[(dl.kind == 'bolus') & (~dl.automatic.fillna(False))])
dis_path = DATA / 'disruptions.csv'
dis = pd.read_csv(dis_path, parse_dates=['start', 'end']) if dis_path.exists() else pd.DataFrame()

fig, ax = plt.subplots(figsize=(13.4, 4.0))
ax.add_patch(Rectangle((0, 70), span, 110, color=BAND, zorder=0))
for _, r in gaps.iterrows():
    x = H([r.t])[0]; ax.axvspan(x - r.d / 60, x, color='#8fa3ad', alpha=.5, zorder=1)
if len(dis):
    for _, r in cut(dis, 'start').iterrows():
        col = {'loop_offline': WARN, 'suspend': FIELD}.get(r.reason, '#777')
        ax.axvspan(H([r.start])[0], max(H([r.end])[0], H([r.start])[0] + .25),
                   color=col, alpha=.17, zorder=1)
ax.plot(H(ar.t), ar.bg, '-', color=FIELD, lw=1.6, zorder=3)
ax.plot(H(mb.t), np.full(len(mb), 47), 'v', color='#0e1519', ms=6, zorder=5)
ax.set_xlim(0, span); ax.set_ylim(40, 345); ax.set_ylabel('BG (mg/dL)')
ax.set_xlabel('hours'); ax.set_xticks(range(0, span + 1, 12))
ax.set_title('What one record already contains — four consecutive days, nothing synthesised',
             fontsize=12.5, fontweight='bold', loc='left', pad=10)
ax.legend(handles=[
    Line2D([], [], color=FIELD, lw=1.6, label='recorded CGM'),
    Patch(facecolor=WARN, alpha=.17, label='loop offline — phone away, pod kept its schedule'),
    Patch(facecolor=FIELD, alpha=.17, label='pump suspend'),
    Patch(facecolor='#8fa3ad', alpha=.5, label='CGM gap ≥ 15 min'),
    Line2D([], [], color='#0e1519', marker='v', ls='', ms=6, label='manual bolus'),
], loc='upper center', bbox_to_anchor=(.5, -.20), ncol=5, fontsize=8.6, frameon=False)
fig.tight_layout(); fig.savefig(OUT / 'realworld.png', bbox_inches='tight', facecolor='white'); plt.close()

# ----------------------------------------------------------------- 3. paired
def daily(p):
    d = trace(p, 'counter').set_index('t'); g = d.groupby(d.index.floor('D')).bg
    return g.apply(lambda s: ((s >= 70) & (s <= 180)).mean() * 100), g.size()

ref, nr_ = daily(long_ref); cd, nc_ = daily(long_cand)
d = pd.concat([ref.rename('ref'), cd.rename('cand'), nr_.rename('na'), nc_.rename('nb')], axis=1).dropna()
d = d[(d.na > 250) & (d.nb > 250)]          # near-complete days only
d['delta'] = d.cand - d.ref
x = np.arange(len(d)); se = d.delta.std() / np.sqrt(len(d))
lo_ci, hi_ci = d.delta.mean() - 1.96 * se, d.delta.mean() + 1.96 * se

fig, (axl, axr) = plt.subplots(1, 2, figsize=(13.4, 4.0))
axl.plot(x, d.ref, 'o-', color=FIELD, ms=3.4, lw=1, alpha=.85, label='reference (stock settings)')
axl.plot(x, d.cand, 'o-', color=ACCENT, ms=3.4, lw=1, alpha=.85, label='candidate (insulin-needs ×1.05)')
axl.set_title('Daily TIR, in levels — SD %.1f pp' % d.ref.std(), fontsize=11.5, fontweight='bold', loc='left')
axl.set_xlabel('day'); axl.set_ylabel('TIR 70–180 (%)'); axl.legend(fontsize=8.4, loc='lower left')
axl.text(.98, .97, 'day-to-day physiology swamps\nthe %.1f pp effect' % d.delta.mean(),
         transform=axl.transAxes, ha='right', va='top', fontsize=9, color='#33444e', bbox=BOX)
axr.axhline(0, color=MUTED, lw=1)
axr.bar(x, d.delta, color=np.where(d.delta >= 0, ACCENT, WARN), alpha=.8, width=.78)
axr.axhline(d.delta.mean(), color='#0e1519', lw=1.6)
axr.axhspan(lo_ci, hi_ci, color='#0e1519', alpha=.13)
axr.set_title('Same days, paired difference — SD %.1f pp (%.1f× tighter)'
              % (d.delta.std(), d.ref.std() / d.delta.std()),
              fontsize=11.5, fontweight='bold', loc='left', color=ACCENT)
axr.set_xlabel('day'); axr.set_ylabel('Δ TIR (pp)')
axr.text(.98, .97, 'mean %+.2f pp   95%% CI %+.2f..%+.2f\nn = %d days'
         % (d.delta.mean(), lo_ci, hi_ci, len(d)),
         transform=axr.transAxes, ha='right', va='top', fontsize=9, color='#0e1519', bbox=BOX)
fig.suptitle('Why the comparison is within-person and paired: everything shared cancels',
             fontsize=13, fontweight='bold', x=.004, ha='left', y=1.02)
fig.tight_layout(); fig.savefig(OUT / 'paired.png', bbox_inches='tight', facecolor='white'); plt.close()

print('premise.png  realworld.png  paired.png  ->', OUT)
print('paired: n=%d  absSD %.2f  pairedSD %.2f  mean %+.2f  CI %+.2f..%+.2f'
      % (len(d), d.ref.std(), d.delta.std(), d.delta.mean(), lo_ci, hi_ci))
