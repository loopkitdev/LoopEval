"""Figure for the 'sweep insulin-needs, not ISF alone' callout (guide section 15).

Sweeps the STOCK algorithm on both aggressiveness dials over one donor and one
window, with every other flag identical, and plots the two reference curves on
the standard axes via `frontier.plot_sweeps`.

    python3 docs/simulator-guide/make_dial_asset.py <trace-dir> <out.png> [outages.csv]

<trace-dir> holds isf_<m>.json and needs_<f>.json traces produced with identical
flags apart from the dial. The sanity check this figure rests on: both dials at
1.00 are the SAME stock config, so they must score identically -- the script
asserts it, because a mismatch means the two arms were not configured alike.
(That assertion is not theoretical: the first attempt at this figure reused two
sweeps from one run directory that had been produced two days apart, and they
disagreed at the stock point by 0.034 pp with no surviving script to explain why.)

Produce the traces with ONE flag set, varying only the dial -- substitute the
donor's own deployment-faithful flags from PRIVATE.md for BASE:

    BASE="--data-dir <dir>|--nightscout-url <url> --start <S> --end <E> \
          --candidate-counterfactual --candidate-infer-sensitivity \
          <donor emulation flags> --outages-csv <outages.csv>"
    for f in 0.60 0.70 0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.20 1.30; do
      loop-eval simulate $BASE --candidate-insulin-needs $f --trace-out needs_$f.json
    done
    for m in 0.70 0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.15 1.20 1.30 1.40 1.60 1.80 2.00; do
      loop-eval simulate $BASE --candidate-sensitivity-multiplier $m --trace-out isf_$m.json
    done

`--candidate-infer-sensitivity` matters here beyond matching project practice: it
puts the plant at the SCHEDULED ISF for both arms, so an ISF-multiplier sweep moves
only the controller's belief. Without it the plant is coupled to that belief
(guide section 10) and the ISF arm is confounded by a body whose sensitivity moves
with the dial. On a cold guest Nightscout host, warm the cache with one serial run
before parallelising.
"""
import sys, glob, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'analysis'))
import numpy as np, pandas as pd
from loopeval_analysis.scoring import score_counterfactual as score
from loopeval_analysis.frontier import plot_sweeps

SRC, OUT = Path(sys.argv[1]), sys.argv[2]
DIS = sys.argv[3] if len(sys.argv) > 3 else None

def sweep(pat):
    rows = []
    for f in sorted(glob.glob(str(SRC / pat))):
        m = float(re.search(r'_([0-9.]+)\.json$', f).group(1))
        s = score(f, outages_csv=DIS)
        rows.append(dict(multiplier=m, TIR=s['TIR'], t54=s['t54'],
                         days=s['days'], kept=s['kept_frac']))
    return pd.DataFrame(rows).sort_values('multiplier')

needs, isf = sweep('needs_*.json'), sweep('isf_*.json')
for name, d in (('insulin-needs', needs), ('ISF-only', isf)):
    print(f'=== {name} ==='); print(d.to_string(index=False)); print()

# Both sweeps must cover the same window, and must agree at the shared stock point.
assert abs(needs.days.mean() - isf.days.mean()) < 0.01, 'sweeps cover different windows'
n1 = needs.loc[np.isclose(needs.multiplier, 1.0)].iloc[0]
i1 = isf.loc[np.isclose(isf.multiplier, 1.0)].iloc[0]
assert abs(n1.TIR - i1.TIR) < 1e-6 and abs(n1.t54 - i1.t54) < 1e-6, (
    f'dials disagree at the stock point -- arms not configured alike: '
    f'needs {n1.TIR:.4f}/{n1.t54:.4f} vs isf {i1.TIR:.4f}/{i1.t54:.4f}')
print(f'window {needs.days.mean():.2f} d, kept {needs.kept.mean():.4f}; '
      f'stock point agrees exactly at TIR {n1.TIR:.4f} / t54 {n1.t54:.4f}')
print(f'floors -- ISF-only {isf.t54.min():.3f} (TIR {isf.loc[isf.t54.idxmin()].TIR:.1f}), '
      f'insulin-needs {needs.t54.min():.3f} (TIR {needs.loc[needs.t54.idxmin()].TIR:.1f})')

isf = isf.assign(mechanism='ISF-only sweep  (--candidate-sensitivity-multiplier)')
plot_sweeps(
    needs, isf, out=OUT,
    ref_label='insulin-needs sweep  (--candidate-insulin-needs: basal x f, ISF / f, CR / f)',
    mark_mult=1.00, ylim=(0.0, 1.5), label_ref_points=True,
    title='The two aggressiveness dials on one donor and window - only the dial differs')
print('wrote', OUT)
