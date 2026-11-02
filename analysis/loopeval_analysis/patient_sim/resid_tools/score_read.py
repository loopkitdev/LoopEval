"""Read a score --detail log by HEADER NAME, not by column position. Ad-hoc awk indexing misread these three times in
one session, because the first argument to score is itself an arm.
    python sc.py <score log> [row ...]"""
import sys, pandas as pd
f = sys.argv[1]; want = sys.argv[2:]
rows = [l.split() for l in open(f) if l.strip()]
hdr = next(r for r in rows if r[:2] == ["tier", "stat"])
arms = [c[4:] for c in hdr if c.startswith("sim_")]
body = [r for r in rows if r is not hdr and len(r) == len(hdr) and r[0].isdigit()]
D = pd.DataFrame(body, columns=hdr)
for _, r in D.iterrows():
    if want and r["stat"] not in want: continue
    parts = "  ".join(f"{a} {float(r['sim_'+a]):8.3f}({float(r['gap_'+a]):.3f})" for a in arms)
    print(f"  t{r['tier']} {r['stat']:<18s} {r['group']:<10s} donors {float(r['real_p50']):8.3f} | {parts}")
