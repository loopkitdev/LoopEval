#!/usr/bin/env python3
"""Generate a methodology report explaining the delivery-based ODR/UDR/IDB/RDB
metrics — RMS, risk-weighted-rate (duration-aware), raw U/hr, and quantiles.

Reads a trace JSON from `loop-eval simulate --trace-out=...` (closed-loop) or
`loop-eval bench --trace-out=...` (open-loop) and writes a self-contained HTML
report with embedded SVG charts. Designed to be read top-to-bottom: each chart
builds on the previous to make the metrics transparent.

usage: delivery_metrics_methodology_report.py <trace.json> <out.html>
"""
import json, sys, math, datetime as dt, io
from collections import namedtuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

if len(sys.argv) < 3:
    print("usage: delivery_metrics_methodology_report.py <trace.json> <out.html>", file=sys.stderr)
    sys.exit(2)

trace_path, out_path = sys.argv[1], sys.argv[2]
with open(trace_path) as f:
    trace = json.load(f)

def parse_t(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

preds = sorted(
    [(parse_t(p["t"]), p["baselineDose"], p["candidateDose"], p["deltaDose"], p["isf"]) for p in trace["predictions"]],
    key=lambda x: x[0]
)
actual = sorted(
    [(parse_t(a["t"]), a["bg"]) for a in trace["actual"]],
    key=lambda x: x[0]
)
baseline_label = trace["baselineLabel"]
candidate_label = trace["candidateLabel"]
closed_loop = trace.get("closedLoop", False)

actual_t = np.array([a[0].timestamp() for a in actual])
actual_bg = np.array([a[1] for a in actual])
pred_t   = np.array([p[0].timestamp() for p in preds])
pred_dB  = np.array([p[1] for p in preds])
pred_dC  = np.array([p[2] for p in preds])
pred_dD  = np.array([p[3] for p in preds])
pred_isf = np.array([p[4] for p in preds])

# ---- Clarke-Kovatchev risk functions (Python ports of BloodGlucoseRisk.swift) ----
def risk_function(g):
    g = np.asarray(g, dtype=float)
    out = np.zeros_like(g)
    pos = g > 0
    f = 1.509 * (np.log(np.where(pos, g, 1.0)) * 1.084 - 5.381)
    out[pos] = 10.0 * f[pos] * f[pos]
    return out

def rl(g):  # low-side
    g = np.asarray(g, dtype=float)
    out = risk_function(g)
    out[g >= 112.5] = 0
    return out

def rh(g):  # high-side
    g = np.asarray(g, dtype=float)
    out = risk_function(g)
    out[g <= 112.5] = 0
    return out

# ---- Linear interpolation of actual BG at arbitrary future times ----
def actual_at(t_unix):
    """Linear interp; returns nan if outside or bracketing samples >10 min apart."""
    out = np.full_like(t_unix, np.nan, dtype=float)
    valid = (t_unix >= actual_t[0]) & (t_unix <= actual_t[-1])
    idx = np.searchsorted(actual_t, t_unix, side='left')
    idx_lo = np.clip(idx - 1, 0, len(actual_t) - 2)
    idx_hi = np.clip(idx, 1, len(actual_t) - 1)
    gap = actual_t[idx_hi] - actual_t[idx_lo]
    frac = np.where(gap > 0, (t_unix - actual_t[idx_lo]) / np.maximum(gap, 1e-9), 0.0)
    interp = actual_bg[idx_lo] + frac * (actual_bg[idx_hi] - actual_bg[idx_lo])
    ok = valid & (gap > 0) & (gap <= 10 * 60)
    out[ok] = interp[ok]
    # Exact match case
    exact = valid & (gap == 0)
    out[exact] = actual_bg[idx_lo[exact]]
    return out

# ---- Compute delivery scores at one horizon ----
DANGER_LOW  = 70.0
DANGER_HIGH = 180.0

def compute_at_horizon(horizon_secs):
    t_future = pred_t + horizon_secs
    bg_future = actual_at(t_future)
    delta = pred_dD
    valid = ~np.isnan(bg_future)
    bg = bg_future[valid]
    d = delta[valid]
    over   = np.maximum(d, 0)
    under  = np.maximum(-d, 0)
    pre_low  = bg < DANGER_LOW
    pre_high = bg > DANGER_HIGH
    rl_w = rl(bg)
    rh_w = rh(bg)

    # RMS magnitude (count-normalized within bucket; duration-blind)
    n_low  = int(pre_low.sum())
    n_high = int(pre_high.sum())
    def rms(mask, weight, mag):
        if mask.sum() == 0: return 0.0, np.array([])
        m = mask & (mag > 0)
        events = mag[m]
        n = mask.sum()  # divides by ALL pre-X events, not just nonzero
        s = (weight[m] * events * events).sum() / max(n, 1)
        return math.sqrt(s), events
    odr, e_odr = rms(pre_low,  rl_w, over)
    rdb, e_rdb = rms(pre_low,  rl_w, under)
    udr, e_udr = rms(pre_high, rh_w, under)
    idb, e_idb = rms(pre_high, rh_w, over)

    # Risk-weighted rate (Σ risk·|Δ| / T_total in risk-U/hr) — duration-aware
    n_steps = len(d)
    eval_step_secs = (preds[1][0] - preds[0][0]).total_seconds() if len(preds) >= 2 else 300
    T_hours = (n_steps * eval_step_secs) / 3600.0
    def lin(mask, weight, mag):
        m = mask & (mag > 0)
        return float((weight[m] * mag[m]).sum() / max(T_hours, 1e-9))
    odr_rate = lin(pre_low,  rl_w, over)
    rdb_rate = lin(pre_low,  rl_w, under)
    udr_rate = lin(pre_high, rh_w, under)
    idb_rate = lin(pre_high, rh_w, over)

    # Raw U/hr — clinical interpretation, no risk weighting
    def raw(mask, mag):
        m = mask & (mag > 0)
        return float(mag[m].sum() / max(T_hours, 1e-9))
    odr_u = raw(pre_low,  over)
    rdb_u = raw(pre_low,  under)
    udr_u = raw(pre_high, under)
    idb_u = raw(pre_high, over)

    def quantiles(arr):
        if arr.size == 0: return (0, 0.0, 0.0, 0.0)
        return (int(arr.size), float(np.quantile(arr, 0.50)), float(np.quantile(arr, 0.90)), float(np.quantile(arr, 0.99)))

    return dict(
        horizon_min = horizon_secs / 60,
        n_low = n_low, n_high = n_high,
        odr = odr, udr = udr, idb = idb, rdb = rdb,
        odr_rate = odr_rate, udr_rate = udr_rate, idb_rate = idb_rate, rdb_rate = rdb_rate,
        odr_u = odr_u, udr_u = udr_u, idb_u = idb_u, rdb_u = rdb_u,
        q_odr = quantiles(e_odr), q_udr = quantiles(e_udr),
        q_idb = quantiles(e_idb), q_rdb = quantiles(e_rdb),
        T_hours = T_hours,
    )

# Compute at standard horizons
HORIZONS = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]
results = {h: compute_at_horizon(h * 60) for h in HORIZONS}
focus = results[90]   # 90-min for the worked-example callouts

# ---- Charts ----
def fig_to_svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

def chart_risk_function():
    fig, ax = plt.subplots(figsize=(7.5, 3.5))
    bg = np.linspace(40, 400, 500)
    ax.plot(bg, rl(bg),  color="#cf222e", linewidth=2, label="r_l(BG) — low-side risk")
    ax.plot(bg, rh(bg),  color="#0969da", linewidth=2, label="r_h(BG) — high-side risk")
    ax.axvline(DANGER_LOW,  color="#cf222e", alpha=0.3, linestyle="--", label="<70 / >180 danger gates")
    ax.axvline(DANGER_HIGH, color="#0969da", alpha=0.3, linestyle="--")
    ax.axvline(112.5, color="#888", alpha=0.4, linestyle=":", label="112.5 (crossover)")
    ax.set_xlabel("Actual future BG (mg/dL)")
    ax.set_ylabel("Risk weight")
    ax.set_title("Clarke-Kovatchev risk function (rl, rh)")
    ax.set_xlim(40, 400)
    ax.set_ylim(0, max(rl(np.array([40])).max(), rh(np.array([400])).max()) * 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper center", fontsize=9)
    return fig_to_svg(fig)

def chart_grid_2x2():
    """The 2×2 sign × bucket grid, labelled with where each metric lives."""
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)

    # Quadrants
    cells = [
        ("ODR", -0.5,  0.5, "#ffd1d1", "COST", "candidate over-delivers\nactual future BG < 70 mg/dL\n→ extra insulin into hypo"),
        ("IDB",  0.5,  0.5, "#cdeac0", "BENEFIT", "candidate over-delivers\nactual future BG > 180 mg/dL\n→ correction landed when needed"),
        ("RDB", -0.5, -0.5, "#cdeac0", "BENEFIT", "candidate under-delivers\nactual future BG < 70 mg/dL\n→ held back before a hypo"),
        ("UDR",  0.5, -0.5, "#ffd1d1", "COST", "candidate under-delivers\nactual future BG > 180 mg/dL\n→ correction withheld"),
    ]
    for name, cx, cy, color, role, desc in cells:
        rect = mpatches.Rectangle((cx - 0.5, cy - 0.5), 1.0, 1.0, facecolor=color, edgecolor="#444", linewidth=1)
        ax.add_patch(rect)
        ax.text(cx, cy + 0.32, name, ha="center", va="center", fontsize=18, fontweight="bold")
        ax.text(cx, cy + 0.12, role, ha="center", va="center", fontsize=10, color="#444")
        ax.text(cx, cy - 0.18, desc, ha="center", va="center", fontsize=8.5, color="#222")

    # Axis labels
    ax.text(0, 1.05, "pre-low (BG < 70)        |        pre-high (BG > 180)", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.text(-1.05, 0, "over-deliver (Δ > 0)\n\nunder-deliver (Δ < 0)", ha="right", va="center", fontsize=10, fontweight="bold", rotation=0)
    ax.axhline(0, color="#444", linewidth=1)
    ax.axvline(0, color="#444", linewidth=1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_aspect("equal")
    return fig_to_svg(fig)

def chart_duration_demo():
    """Show two synthetic Δdose patterns with same total magnitude but different
    durations, side-by-side, and how RMS vs Rate disagree."""
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.2), sharey=True)

    # Scenario A: 1 spike of 0.5 U; one 5-min event
    # Scenario B: 12 ticks of 0.5 U over an hour; one 60-min event
    times_min = np.arange(0, 75, 5)
    A = np.zeros_like(times_min, dtype=float); A[3] = 0.5
    B = np.zeros_like(times_min, dtype=float); B[3:15] = 0.5

    axes[0].bar(times_min, A, width=4.5, color="#0969da")
    axes[0].set_title("A: one spike (5 min)")
    axes[0].set_xlabel("minutes")
    axes[0].set_ylabel("|Δdose| (U)")
    axes[0].set_ylim(0, 0.7)

    axes[1].bar(times_min, B, width=4.5, color="#0969da")
    axes[1].set_title("B: sustained ticks (60 min)")
    axes[1].set_xlabel("minutes")

    # Compute illustrative scores: assume actual future BG = 220 (rh = 1.0 nominal),
    # bucket = pre-high under-delivery, so under-bucket UDR/RDB.
    # rh(220) ≈ 1.07
    rhw = float(rh(np.array([220.0]))[0])
    nA, nB = 1, 12   # # nonzero events
    # n_high = the # of pre-high samples in window — same for both: 12 in scenario A and 12 in B
    # (only the magnitudes differ).
    nbucket = 12
    rms_A = math.sqrt((rhw * 0.5**2) * nA / nbucket)
    rms_B = math.sqrt((rhw * 0.5**2) * nB / nbucket)
    # rate = Σ rh·|Δ| / T_hr ; T = 75 min = 1.25 h
    T = 1.25
    rate_A = rhw * 0.5 * nA / T
    rate_B = rhw * 0.5 * nB / T

    fig.suptitle(
        f"RMS  →  A: {rms_A:.3f}    B: {rms_B:.3f}    (B / A = {rms_B/rms_A:.2f}×)\n"
        f"Risk-weighted rate (risk-U/hr) →  A: {rate_A:.3f}    B: {rate_B:.3f}    (B / A = {rate_B/rate_A:.2f}×)",
        fontsize=11, y=1.02
    )
    return fig_to_svg(fig)

def chart_horizon_scores():
    """Per-horizon line plot of all four cost/benefit metrics + their rate forms."""
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.5))
    hs = np.array([results[h]["horizon_min"] for h in HORIZONS])
    odr  = np.array([results[h]["odr"]      for h in HORIZONS])
    udr  = np.array([results[h]["udr"]      for h in HORIZONS])
    idb  = np.array([results[h]["idb"]      for h in HORIZONS])
    rdb  = np.array([results[h]["rdb"]      for h in HORIZONS])
    odrR = np.array([results[h]["odr_rate"] for h in HORIZONS])
    udrR = np.array([results[h]["udr_rate"] for h in HORIZONS])
    idbR = np.array([results[h]["idb_rate"] for h in HORIZONS])
    rdbR = np.array([results[h]["rdb_rate"] for h in HORIZONS])

    axes[0,0].plot(hs, odr, "-o", color="#cf222e", label="ODR (cost)")
    axes[0,0].plot(hs, udr, "-o", color="#bf6900", label="UDR (cost)")
    axes[0,0].set_title("Costs — RMS magnitude form")
    axes[0,0].legend(); axes[0,0].grid(True, alpha=0.3)
    axes[0,0].set_xlabel("horizon (min)")

    axes[0,1].plot(hs, idb, "-o", color="#1a7f37", label="IDB (benefit)")
    axes[0,1].plot(hs, rdb, "-o", color="#287f4e", label="RDB (benefit)")
    axes[0,1].set_title("Benefits — RMS magnitude form")
    axes[0,1].legend(); axes[0,1].grid(True, alpha=0.3)
    axes[0,1].set_xlabel("horizon (min)")

    axes[1,0].plot(hs, odrR, "-o", color="#cf222e", label="ODR rate")
    axes[1,0].plot(hs, udrR, "-o", color="#bf6900", label="UDR rate")
    axes[1,0].set_title("Costs — risk-weighted rate (duration-aware)")
    axes[1,0].set_xlabel("horizon (min)"); axes[1,0].set_ylabel("risk·U / hr")
    axes[1,0].legend(); axes[1,0].grid(True, alpha=0.3)

    axes[1,1].plot(hs, idbR, "-o", color="#1a7f37", label="IDB rate")
    axes[1,1].plot(hs, rdbR, "-o", color="#287f4e", label="RDB rate")
    axes[1,1].set_title("Benefits — risk-weighted rate (duration-aware)")
    axes[1,1].set_xlabel("horizon (min)"); axes[1,1].set_ylabel("risk·U / hr")
    axes[1,1].legend(); axes[1,1].grid(True, alpha=0.3)

    fig.tight_layout()
    return fig_to_svg(fig)

def chart_quantiles():
    """Box-style chart of P50/P90/P99 in each cell at the focus horizon."""
    fig, ax = plt.subplots(figsize=(8.0, 3.5))
    cells = [("ODR", "q_odr", "#cf222e"),
             ("RDB", "q_rdb", "#287f4e"),
             ("IDB", "q_idb", "#1a7f37"),
             ("UDR", "q_udr", "#bf6900")]
    xs = np.arange(len(cells))
    p50 = []; p90 = []; p99 = []; ns = []; labels = []
    for name, key, _ in cells:
        n, a, b, c = focus[key]
        p50.append(a); p90.append(b); p99.append(c); ns.append(n)
        labels.append(f"{name}\n(n={n})")
    width = 0.25
    ax.bar(xs - width, p50, width, color="#cccccc", label="P50")
    ax.bar(xs,         p90, width, color="#888888", label="P90")
    ax.bar(xs + width, p99, width, color="#444444", label="P99")
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("|Δdose| (U) at 90-min horizon")
    ax.set_title("Magnitude distribution — distinguishes \"rare big spike\" from \"many small ticks\"")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    return fig_to_svg(fig)

def chart_decision_matrix():
    """Heatmap-style decision aid: combinations of (cost, benefit) → recommendation."""
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    rows = ["benefit\nLOW", "benefit\nMED", "benefit\nHIGH"]
    cols = ["cost\nLOW", "cost\nMED", "cost\nHIGH"]
    text = [
        ["no-op", "trade?", "REJECT"],
        ["trade?", "trade?", "REJECT"],
        ["ACCEPT", "trade?", "REJECT"],
    ]
    color = [
        ["#eef0f2", "#fff8c5", "#ffd1d1"],
        ["#fff8c5", "#fff8c5", "#ffd1d1"],
        ["#cdeac0", "#fff8c5", "#ffd1d1"],
    ]
    for r in range(3):
        for c in range(3):
            ax.add_patch(mpatches.Rectangle((c, 2 - r), 1, 1, facecolor=color[r][c], edgecolor="#444"))
            ax.text(c + 0.5, 2 - r + 0.5, text[r][c], ha="center", va="center",
                    fontsize=12, fontweight="bold")
    ax.set_xticks([0.5, 1.5, 2.5]); ax.set_xticklabels(cols, fontsize=10)
    ax.set_yticks([0.5, 1.5, 2.5]); ax.set_yticklabels(reversed(rows), fontsize=10)
    ax.set_xlim(0, 3); ax.set_ylim(0, 3)
    ax.set_aspect("equal")
    ax.set_title("Decision aid — read costs (ODR + UDR) against benefits (IDB + RDB)")
    return fig_to_svg(fig)

# ---- Build report ----
n_pred   = len(preds)
n_actual = len(actual)
n_nonzero = int((pred_dD != 0).sum())
n_pre_low_90  = int(((actual_at(pred_t + 90*60) < DANGER_LOW)).sum())
n_pre_high_90 = int(((actual_at(pred_t + 90*60) > DANGER_HIGH)).sum())

charts = {
    "risk":      chart_risk_function(),
    "grid":      chart_grid_2x2(),
    "duration":  chart_duration_demo(),
    "horizons":  chart_horizon_scores(),
    "quantiles": chart_quantiles(),
    "decision":  chart_decision_matrix(),
}

primary_cost_focus    = focus["odr"] + focus["udr"]
primary_benefit_focus = focus["idb"] + focus["rdb"]
ratio_focus           = primary_benefit_focus / max(primary_cost_focus, 1e-9)

primary_cost_rate    = focus["odr_rate"] + focus["udr_rate"]
primary_benefit_rate = focus["idb_rate"] + focus["rdb_rate"]
ratio_rate           = primary_benefit_rate / max(primary_cost_rate, 1e-9)

trace_kind = "closed-loop" if closed_loop else "open-loop"

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>Delivery metrics methodology — ODR / UDR / IDB / RDB + duration-aware rates</title>
<style>
  body {{ font-family: -apple-system, "SF Pro", Helvetica, Arial, sans-serif; max-width: 960px; margin: 30px auto; padding: 0 24px; color: #222; line-height: 1.55; }}
  h1 {{ font-size: 26px; }}
  h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 36px; }}
  h3 {{ margin-top: 28px; }}
  .formula {{ background: #f6f8fa; border: 1px solid #d0d7de; padding: 10px 14px; border-radius: 6px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 13px; }}
  .callout {{ background: #fff8c5; border-left: 4px solid #d4a72c; padding: 10px 14px; border-radius: 4px; margin: 16px 0; font-size: 14px; }}
  .callout.bad {{ background: #ffebe9; border-left-color: #cf222e; }}
  .callout.good {{ background: #dafbe1; border-left-color: #1a7f37; }}
  table {{ border-collapse: collapse; margin: 12px 0; width: 100%; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 12px; text-align: left; }}
  th {{ background: #f6f8fa; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: ui-monospace, monospace; }}
  .meta {{ color: #57606a; font-size: 13px; }}
  svg {{ display: block; margin: 14px 0; max-width: 100%; height: auto; }}
  code {{ font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; background: #f0f3f6; padding: 1px 4px; border-radius: 3px; font-size: 90%; }}
</style></head><body>

<h1>Delivery-based metrics — methodology walkthrough</h1>
<div class="meta">Baseline: <b>{baseline_label}</b> &nbsp; · &nbsp; Candidate: <b>{candidate_label}</b></div>
<div class="meta">Window: {trace["intervalStart"]} → {trace["intervalEnd"]} &nbsp; · &nbsp; trace type: <b>{trace_kind}</b></div>
<div class="meta">{n_pred:,} prediction steps · {n_actual:,} CGM samples · {n_nonzero:,} timesteps with nonzero Δdose</div>

<h2>1. Why these metrics exist</h2>
<p>An earlier pair of exploration metrics in this evaluation pipeline, <b>OPR</b> (over-prediction risk) and <b>UPR</b> (under-prediction risk), score how wrong the algorithm's BG forecast was — directionally, with risk weighting in the danger zones. They're useful for surfacing forecast bugs, but a wrong forecast isn't the same as a wrong delivery. A configuration that predicts perfectly but never acts on the prediction has zero OPR/UPR <em>and</em> zero clinical benefit. We needed metrics that score what actually reached the patient.</p>
<p>The delivery-based family — <b>ODR</b>, <b>UDR</b>, <b>IDB</b>, <b>RDB</b> — operates on the <em>difference</em> in insulin delivery between two configurations (<code>Δdose = candidate − baseline</code>), weighted by clinical risk at the actual future BG. They answer: <em>does the candidate dose differently from the baseline at moments that mattered?</em></p>

<h2>2. The four cells</h2>
<p>At each prediction timestep, look at <code>Δdose</code> sign (over-deliver vs under-deliver) and the actual future BG bucket at that horizon (pre-low <code>&lt; 70</code>, pre-high <code>&gt; 180</code>; in-range moments contribute to no cell). That's a 2×2 grid:</p>
{charts["grid"]}
<p>Mnemonic: <code>R</code> suffix = <b>R</b>isk (cost), <code>B</code> suffix = <b>B</b>enefit. Costs and benefits are reported separately so you can read trade-offs explicitly rather than collapsing them into a single signed number.</p>

<h2>3. Risk weighting</h2>
<p>Each event is weighted by Clarke-Kovatchev risk at the actual future BG. <code>r_l</code> ramps up rapidly below 70 mg/dL; <code>r_h</code> ramps up above 180. They share a common base function and meet at zero at the crossover BG of 112.5 mg/dL.</p>
{charts["risk"]}
<div class="formula">
risk_function(BG) = 10 · [ 1.509 · ( ln(BG) · 1.084 − 5.381 ) ]<sup>2</sup><br>
r_l(BG) = risk_function(BG) if BG &lt; 112.5 else 0<br>
r_h(BG) = risk_function(BG) if BG &gt; 112.5 else 0
</div>
<p>Why this matters: a Δdose of equal magnitude is more dangerous when the future BG is 50 mg/dL than 65 mg/dL. The risk weighting makes the metric track clinical reality, not just count events.</p>

<h2>4. Three flavors of each cell</h2>
<p>Each of ODR / UDR / IDB / RDB is reported in three flavors. They aggregate the same per-event evidence under different normalizations, and they answer different questions.</p>

<h3>4a. RMS magnitude — count-normalized, duration-blind</h3>
<div class="formula">
ODR&nbsp;=&nbsp;√( Σ&nbsp;r_l(actual) · max(Δdose, 0)<sup>2</sup>&nbsp;/&nbsp;n<sub>pre-low</sub> )<br>
UDR&nbsp;=&nbsp;√( Σ&nbsp;r_h(actual) · max(−Δdose, 0)<sup>2</sup>&nbsp;/&nbsp;n<sub>pre-high</sub> )<br>
IDB&nbsp;=&nbsp;√( Σ&nbsp;r_h(actual) · max(Δdose, 0)<sup>2</sup>&nbsp;/&nbsp;n<sub>pre-high</sub> )<br>
RDB&nbsp;=&nbsp;√( Σ&nbsp;r_l(actual) · max(−Δdose, 0)<sup>2</sup>&nbsp;/&nbsp;n<sub>pre-low</sub> )
</div>
<p>This is the original delivery-score form. It's a risk-weighted RMS magnitude: bigger spikes count more (squared), and the sum is normalised by <em>all</em> pre-low or pre-high samples, not just the nonzero ones.</p>
<p><b>Property:</b> a single 4-hour sustained event and a single 5-minute spike of equal Δdose contribute the <em>same</em> value because each shows up as one event in the count. The score is blind to event duration.</p>
<p>That's the right answer for "how big are the dangerous spikes?" but the wrong answer for "does this candidate keep BG in zone X for longer or shorter?" When two interventions differ in time-in-zone, the RMS form will mis-rank them.</p>

<h3>4b. Risk-weighted rate — duration-aware</h3>
<div class="formula">
ODR_rate&nbsp;=&nbsp;Σ&nbsp;r_l(actual) · max(Δdose, 0)&nbsp;/&nbsp;T<sub>total</sub>&nbsp;&nbsp;(units: risk·U / hr)
</div>
<p>Same numerator weighting, but linear in <code>|Δdose|</code> (not squared) and divided by total analysis duration in hours rather than the pre-bucket count. This is duration-aware: a 1-hour sustained event counts roughly 12× a 5-minute event of equal magnitude.</p>
<p>Side-by-side with two synthetic scenarios that have identical magnitudes per tick but different durations:</p>
{charts["duration"]}
<p>RMS rates them roughly equal; the rate form rates B as 12× A. Use the rate form when the candidate's hypothesis is about <em>persistence</em> ("don't suspend insulin for as long" or "hold a high BG longer before correcting") — duration is the variable.</p>

<h3>4c. Raw U/hr — clinically interpretable, no risk weighting</h3>
<div class="formula">
ODR_URate&nbsp;=&nbsp;Σ&nbsp;max(Δdose, 0)&nbsp;/&nbsp;T<sub>total</sub>&nbsp;&nbsp;(units: U / hr, in pre-low windows only)
</div>
<p>Strip the risk weighting and you get a number with concrete clinical meaning: "the candidate over-delivered, on average, X units of insulin per hour of analysis time, restricted to the moments where actual future BG ended up &lt; 70." This is the same "Δdose flow into a bucket" but un-weighted, so it's directly auditable: multiply by hours of use to get total U mis-delivered.</p>

<h3>4d. Magnitude quantiles (P50 / P90 / P99)</h3>
<p>The same total RMS or rate can come from many small ticks or a few huge spikes. The quantile reports tell you which:</p>
{charts["quantiles"]}
<p>High P99 with low P50 → "rare-but-severe" — the score is dominated by a handful of large dose deltas that warrant a closer look. Flat profile (P50 ≈ P99) → "small-but-persistent" — the candidate consistently differs from baseline in this bucket but never by much.</p>

<h2>5. Putting them together — how to read the four scores</h2>
<p>Costs come in two flavours (ODR + UDR) and benefits in two flavours (IDB + RDB). The headline questions are:</p>
<ol>
  <li><b>Did the candidate avoid dangerous deliveries?</b> — read costs.</li>
  <li><b>Did the candidate add useful deliveries?</b> — read benefits.</li>
  <li><b>Was the candidate's behaviour an improvement?</b> — read benefits ÷ costs (the "ratio" metric).</li>
</ol>
{charts["decision"]}
<div class="callout"><b>Important caveat:</b> the ratio is duration-blind in its RMS form, so a candidate that earns its high ratio by trading hyper-time for hypo-time can score well even though TIR went down. Read the ratio together with counterfactual TIR (separate methodology report).</div>

<h2>6. Per-horizon view — which forecast horizon is the metric most informative at?</h2>
<p>The Loop algorithm decides doses against forecasts at multiple horizons; the delivery metric is computed independently at each. A change that helps at 30 min may hurt at 240 min. The aggregate "weighted" score (Gaussian peak at 90 min, σ = 60 min) emphasises the horizon where the dose decision is most actionable. Per-horizon plots:</p>
{charts["horizons"]}

<h2>7. Worked example — this run</h2>
<p>Numbers below are from the {trace_kind} trace at <code>{trace_path.split('/')[-1]}</code>. Focus is the 90-min horizon (matches the Gaussian peak); aggregate weighting across all 12 horizons is shown for primary scores.</p>

<h3>7a. Counts at 90 min</h3>
<table>
<tr><th>Bucket</th><th class="num">n samples</th><th>Definition</th></tr>
<tr><td>pre-low</td>     <td class="num">{focus["n_low"]:,}</td>  <td>actual future BG &lt; 70 mg/dL</td></tr>
<tr><td>pre-high</td>    <td class="num">{focus["n_high"]:,}</td> <td>actual future BG &gt; 180 mg/dL</td></tr>
</table>

<h3>7b. The four cells, all three flavors</h3>
<table>
<tr><th>Cell</th><th class="num">RMS (U)</th><th class="num">rate (risk·U/hr)</th><th class="num">raw (U/hr)</th><th class="num">P50 / P90 / P99 (U)</th><th class="num">n events</th></tr>
<tr><td><b>ODR</b> — pre-low over-deliver (cost)</td>
    <td class="num">{focus["odr"]:.4f}</td><td class="num">{focus["odr_rate"]:.4f}</td><td class="num">{focus["odr_u"]:.4f}</td>
    <td class="num">{focus["q_odr"][1]:.4f} / {focus["q_odr"][2]:.4f} / {focus["q_odr"][3]:.4f}</td><td class="num">{focus["q_odr"][0]:,}</td></tr>
<tr><td><b>RDB</b> — pre-low under-deliver (benefit)</td>
    <td class="num">{focus["rdb"]:.4f}</td><td class="num">{focus["rdb_rate"]:.4f}</td><td class="num">{focus["rdb_u"]:.4f}</td>
    <td class="num">{focus["q_rdb"][1]:.4f} / {focus["q_rdb"][2]:.4f} / {focus["q_rdb"][3]:.4f}</td><td class="num">{focus["q_rdb"][0]:,}</td></tr>
<tr><td><b>IDB</b> — pre-high over-deliver (benefit)</td>
    <td class="num">{focus["idb"]:.4f}</td><td class="num">{focus["idb_rate"]:.4f}</td><td class="num">{focus["idb_u"]:.4f}</td>
    <td class="num">{focus["q_idb"][1]:.4f} / {focus["q_idb"][2]:.4f} / {focus["q_idb"][3]:.4f}</td><td class="num">{focus["q_idb"][0]:,}</td></tr>
<tr><td><b>UDR</b> — pre-high under-deliver (cost)</td>
    <td class="num">{focus["udr"]:.4f}</td><td class="num">{focus["udr_rate"]:.4f}</td><td class="num">{focus["udr_u"]:.4f}</td>
    <td class="num">{focus["q_udr"][1]:.4f} / {focus["q_udr"][2]:.4f} / {focus["q_udr"][3]:.4f}</td><td class="num">{focus["q_udr"][0]:,}</td></tr>
</table>

<h3>7c. Aggregates at 90 min</h3>
<table>
<tr><th>Aggregate</th><th class="num">value</th><th>meaning</th></tr>
<tr><td>primary cost   (ODR + UDR), RMS</td> <td class="num">{primary_cost_focus:.4f}</td>  <td>total dangerous-direction RMS at 90 min</td></tr>
<tr><td>primary benefit (IDB + RDB), RMS</td><td class="num">{primary_benefit_focus:.4f}</td><td>total beneficial-direction RMS at 90 min</td></tr>
<tr><td>benefit / cost (RMS ratio)</td>      <td class="num">{ratio_focus:.2f}</td>         <td>&gt; 1 ⇒ net safety-positive at this horizon</td></tr>
<tr><td>primary cost (ODR + UDR), rate</td>  <td class="num">{primary_cost_rate:.4f}</td>   <td>duration-aware, risk·U/hr</td></tr>
<tr><td>primary benefit (IDB + RDB), rate</td><td class="num">{primary_benefit_rate:.4f}</td><td>duration-aware</td></tr>
<tr><td>benefit / cost (rate ratio)</td>     <td class="num">{ratio_rate:.2f}</td>          <td>often differs from RMS ratio when events vary in duration</td></tr>
</table>
<div class="callout">If the two ratios disagree by more than ~2×, look at the magnitude quantiles to see whether the RMS form is being driven by a few large spikes (compare P99 to P50 within each cell).</div>

<h2>8. Limitations</h2>
<ul>
  <li><b>Pair coverage:</b> events with no actual-BG sample at the horizon (gaps &gt; 10 min in the CGM stream) are dropped. With a sparse stream, late-horizon scores can be based on far fewer events than early-horizon ones.</li>
  <li><b>Open-loop vs closed-loop traces:</b> open-loop bench evaluates Δdose against actual BG history. Closed-loop simulate evaluates Δdose against the candidate's <em>own</em> counterfactual BG history. The metrics are the same but the inputs differ; for aggressive candidates, prefer closed-loop.</li>
  <li><b>The ratio is not a TIR predictor.</b> It rates dose decisions at risky moments, weighted by clinical risk, and ignores time-in-zone. Pair it with counterfactual TIR before recommending an algorithm change.</li>
  <li><b>Risk function asymmetry:</b> Clarke-Kovatchev's risk grows much faster on the low side than on the high side. ODR / RDB cells will dominate any aggregate when both buckets see comparable Δdose magnitudes.</li>
</ul>

</body></html>
"""

with open(out_path, "w") as f:
    f.write(html)
print(f"Wrote {out_path}")
print(f"  Predictions: {n_pred:,}  CGM samples: {n_actual:,}  Δdose nonzero: {n_nonzero:,}")
print(f"  Pre-low at 90min: {focus['n_low']:,}   Pre-high at 90min: {focus['n_high']:,}")
print(f"  Primary cost RMS: {primary_cost_focus:.4f}  benefit RMS: {primary_benefit_focus:.4f}  ratio: {ratio_focus:.2f}")
print(f"  Primary cost rate: {primary_cost_rate:.4f}  benefit rate: {primary_benefit_rate:.4f}  ratio: {ratio_rate:.2f}")
