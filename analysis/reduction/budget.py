"""Per-person low-side budget for the generator scores (gen.py scores_*.csv): for each arm, pooled TIR / t<70 / t<54 and
the share of people over the consensus targets (t<70 > 4 % or t<54 > 1 %), on CGM and true glucose, against gr_p0.
usage: python budget.py <scores csv>..."""
import sys
import pandas as pd

def report(path):
    d = pd.read_csv(path)
    v = lambda k: d.pivot_table(index="alias", columns="arm", values=k)
    out = []
    for src in ("cgm", "true"):
        tir, t70, t54 = v(f"{src}_tir"), v(f"{src}_t70"), v(f"{src}_t54")
        over = (t70 > 4) | (t54 > 1)
        for a in tir.columns:
            k = tir[a].notna() & tir["gr_p0"].notna()
            newly = (over[a] & ~over["gr_p0"])[k]
            out.append(dict(src=src, arm=a, n=int(k.sum()), tir=tir[a][k].mean(), t70=t70[a][k].mean(), t54=t54[a][k].mean(),
                            over=over[a][k].mean() * 100, newly_over=newly.mean() * 100,
                            over70=(t70[a][k] > 4).mean() * 100, over54=(t54[a][k] > 1).mean() * 100))
    t = pd.DataFrame(out).round(2)
    print(path.split("/")[-1]); print(t.sort_values(["src", "tir"]).to_string(index=False))

for p in sys.argv[1:]: report(p)
