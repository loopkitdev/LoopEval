"""Lift figure for the simulator guide (section 15): candidate sweeps vs the
insulin-needs reference, on the standard TIR / t<54 axes.

    python3 docs/simulator-guide/make_lift_asset.py <run-dir> <out.png> [alias] [min-mult]

<run-dir> holds a scores CSV (TIR, t54, mechanism, multiplier) with a row group
named "reference" plus one group per candidate mechanism, alongside the traces
and the dataset's outages/cgm-gaps CSVs. Every mechanism must be swept over the
SAME dial as the reference -- insulin-needs -- or the lift numbers are measured
against a baseline the candidates were not compared on (see the dial callout).

[min-mult] drops sweep points below that multiplier from the PLOT only. Deep in
the conservative tail every arm sits at t<54 = 0 and the curves are a flat line
carrying no information, so showing it wastes most of the x-axis. The lift
numbers printed below are always computed on the full sweep; state the full
swept range in the caption so the trim hides nothing.

Plotting goes through `frontier.plot_sweeps` rather than matplotlib directly, so
the lines are ordered by sweep multiplier (a TIR-ordered line zig-zags on any
non-monotonic sweep) and the axes keep the house convention: t<54 increasing
UPWARD, better = lower-right.
"""
import sys, glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'analysis'))
import pandas as pd
from loopeval_analysis.frontier import field_point, plot_sweeps, summarize_mechanisms

RUN, OUT = Path(sys.argv[1]), sys.argv[2]
ALIAS = sys.argv[3] if len(sys.argv) > 3 else 'donor'
MIN_MULT = float(sys.argv[4]) if len(sys.argv) > 4 else None

scores = next(iter(glob.glob(str(RUN / '*scores*.csv'))), None)
if scores is None:
    sys.exit(f'no scores CSV in {RUN}')
d = pd.read_csv(scores)
ref = d[d.mechanism == 'reference']
cand = d[d.mechanism != 'reference']
if ref.empty:
    sys.exit('scores CSV has no "reference" mechanism group')

outg = RUN / 'outages.csv'
gaps = RUN / 'cgm_gaps.csv'
trace = next(iter(sorted(glob.glob(str(RUN / '*.json')))), None)
field = None
if trace:
    f = field_point(trace,
                    outages_csv=str(outg) if outg.exists() else None,
                    cgm_gaps_csv=str(gaps) if gaps.exists() else None)
    field = {'TIR': f['TIR'], 't54': f['t54']}
    print(f"field: TIR {f['TIR']:.2f}  t54 {f['t54']:.3f}  "
          f"{f['days']:.1f} d  kept {f['kept_frac']:.4f}")

print(); print(summarize_mechanisms(ref, cand).to_string(index=False))
print(f'\nfull swept range: multiplier {d.multiplier.min():g}-{d.multiplier.max():g}, '
      f'TIR {d.TIR.min():.1f}-{d.TIR.max():.1f}')

if MIN_MULT is not None:          # plot-only trim; lift above used the full sweep
    shown = d[d.multiplier >= MIN_MULT]
    ref, cand = shown[shown.mechanism == 'reference'], shown[shown.mechanism != 'reference']
    print(f'plotting multiplier >= {MIN_MULT:g}: TIR {shown.TIR.min():.1f}-{shown.TIR.max():.1f}')

plot_sweeps(
    ref, cand, out=OUT, field=field, mark_mult=1.00, ylim=(0.0, 1.5),
    ref_label='insulin-needs sweep (reference)',
    title=f'Lift: candidate mechanisms vs the insulin-needs reference '
          f'({ALIAS}, {f["days"]:.0f} d)' if trace else
          f'Lift: candidate mechanisms vs the insulin-needs reference ({ALIAS})')
print('\nwrote', OUT)
