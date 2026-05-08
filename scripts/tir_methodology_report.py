#!/usr/bin/env python3
"""Generate a methodology report explaining the counterfactual TIR simulation.

Reads a trace JSON produced by `loop-eval bench --trace-out=...` and writes a
self-contained HTML report with embedded SVG charts. Designed to be read top-to-
bottom: each chart builds on the previous to make the simulation transparent.
"""
import json, sys, os, datetime as dt, base64, io, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

if len(sys.argv) < 3:
    print("usage: tir_methodology_report.py <trace.json> <out.html>", file=sys.stderr)
    sys.exit(2)

trace_path, out_path = sys.argv[1], sys.argv[2]
with open(trace_path) as f:
    trace = json.load(f)

# ---- Load ----
def parse_t(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

preds = [(parse_t(p["t"]), p["baselineDose"], p["candidateDose"], p["deltaDose"], p["isf"]) for p in trace["predictions"]]
preds.sort(key=lambda x: x[0])
actual = [(parse_t(a["t"]), a["bg"]) for a in trace["actual"]]
actual.sort(key=lambda x: x[0])
curve = trace["insulinActivityCurve"]
duration_min = trace["activityDurationMinutes"]
baseline_label = trace["baselineLabel"]
candidate_label = trace["candidateLabel"]

# ---- Detect closed-loop trace ----
closed_loop = trace.get("closedLoop", False)
counter_provided = trace.get("counter")  # closed-loop trajectory if present

# ---- Compute counterfactual BG ----
# Linearized: at each actual sample t, sum Δdose × ISF × (1 − percentRemaining(t − t')) over t' ≤ t.
# Closed-loop: read the precomputed counter directly from the trace.

# Precompute curve as numpy lookup (5-min step)
curve_min = np.array([c["tMin"] for c in curve])
percent_delivered = np.array([c["percentDelivered"] for c in curve])
percent_remaining = np.array([c["percentRemaining"] for c in curve])

def lookup_pdelivered(min_after):
    """% effect delivered at min_after minutes after dose."""
    if min_after < 0: return 0.0
    if min_after > duration_min: return 1.0
    # Linear interp in 5-min bins
    idx = min_after / 5.0
    i0 = int(math.floor(idx))
    i1 = min(i0 + 1, len(percent_delivered) - 1)
    frac = idx - i0
    return percent_delivered[i0] * (1 - frac) + percent_delivered[i1] * frac

# For each actual sample, find paired Δdose impacts from the past `duration_min`
pred_t = np.array([p[0].timestamp() for p in preds])
pred_delta = np.array([p[3] for p in preds])
pred_isf = np.array([p[4] for p in preds])

actual_t = np.array([a[0].timestamp() for a in actual])
actual_bg = np.array([a[1] for a in actual])

counter_bg = np.empty_like(actual_bg)
duration_s = duration_min * 60
lo = 0
for i, t in enumerate(actual_t):
    earliest = t - duration_s
    while lo < len(pred_t) and pred_t[lo] < earliest:
        lo += 1
    impact = 0.0
    j = lo
    while j < len(pred_t) and pred_t[j] <= t:
        tau_min = (t - pred_t[j]) / 60.0
        if 0 <= tau_min <= duration_min:
            pd = lookup_pdelivered(tau_min)
            impact += pred_delta[j] * pred_isf[j] * pd
        j += 1
    counter_bg[i] = actual_bg[i] - impact

# Closed-loop trace: read directly and interpolate to actual_t grid.
# Mask out-of-range samples (the closed-loop sim only covers post-warmup).
counter_bg_closed = None
counter_bg_closed_mask = None  # True where closed-loop value is valid
if counter_provided:
    cl_t = np.array([parse_t(c["t"]).timestamp() for c in counter_provided])
    cl_bg = np.array([c["bg"] for c in counter_provided])
    # Linear interp; mark out-of-range with NaN, then mask for downstream use.
    counter_bg_closed = np.interp(actual_t, cl_t, cl_bg)
    counter_bg_closed_mask = (actual_t >= cl_t[0]) & (actual_t <= cl_t[-1])
    counter_bg_closed = np.where(counter_bg_closed_mask, counter_bg_closed, np.nan)

# ---- Charts ----
def fig_to_svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

def make_activity_curve():
    fig, ax = plt.subplots(figsize=(8, 4.0))
    ax.plot(curve_min, percent_remaining * 100, label="% effect remaining (IOB curve)", color="#3a7", lw=2)
    ax.plot(curve_min, percent_delivered * 100, label="% effect delivered (1 − remaining)", color="#c43", lw=2)
    ax.set_xlabel("Minutes since dose")
    ax.set_ylabel("Percent")
    ax.set_title(f"Insulin activity curve (rapid-acting model, duration {int(duration_min)} min)")
    ax.set_ylim(0, 100)
    ax.set_xlim(0, duration_min)
    ax.grid(alpha=0.3)
    ax.legend(loc="center right")
    ax.set_xticks(np.arange(0, duration_min + 1, 60))
    return fig_to_svg(fig)

def make_impulse_response(unit_dose=1.0, isf=50.0):
    fig, ax = plt.subplots(figsize=(8, 4.0))
    impact = unit_dose * isf * percent_delivered
    ax.plot(curve_min, -impact, color="#c43", lw=2)
    ax.set_xlabel("Minutes after dose")
    ax.set_ylabel("BG impact (mg/dL)")
    ax.set_title(f"Single-impulse response: candidate gives {unit_dose:+.1f} U extra at t=0 (ISF={isf:.0f})")
    ax.axhline(0, color="black", lw=0.5)
    ax.grid(alpha=0.3)
    ax.set_xlim(0, duration_min)
    ax.set_xticks(np.arange(0, duration_min + 1, 60))
    # annotate final value
    ax.annotate(f"final ΔBG = {-impact[-1]:.1f} mg/dL", xy=(duration_min - 5, -impact[-1]),
                xytext=(duration_min - 90, -impact[-1] + 3),
                arrowprops={"arrowstyle": "->"}, fontsize=10)
    return fig_to_svg(fig)

def make_24h_example():
    """Pick a 24-hour window with meaningful candidate activity."""
    # Find a 24h window with the largest absolute Δdose sum
    win_s = 24 * 3600
    best_score, best_start = 0, actual_t[0]
    for i in range(0, len(pred_t) - 24*12, 12):  # step ~1h
        end = pred_t[i] + win_s
        mask = (pred_t >= pred_t[i]) & (pred_t < end)
        score = np.sum(np.abs(pred_delta[mask]))
        if score > best_score:
            best_score = score; best_start = pred_t[i]
    win_start = best_start
    win_end = best_start + win_s

    a_mask = (actual_t >= win_start) & (actual_t <= win_end)
    p_mask = (pred_t >= win_start) & (pred_t <= win_end)

    a_dt = [dt.datetime.fromtimestamp(t) for t in actual_t[a_mask]]
    a_bg = actual_bg[a_mask]
    a_cb = counter_bg[a_mask]
    a_cb_closed = counter_bg_closed[a_mask] if counter_bg_closed is not None else None
    p_dt = [dt.datetime.fromtimestamp(t) for t in pred_t[p_mask]]
    p_d = pred_delta[p_mask]

    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(a_dt, a_bg, color="#000", lw=1.5, label="actual CGM")
    ax.plot(a_dt, a_cb, color="#c43", lw=1.5, ls="--", label=f"linearized counterfactual")
    if a_cb_closed is not None:
        ax.plot(a_dt, a_cb_closed, color="#37a", lw=1.7, label=f"closed-loop counterfactual ({candidate_label})")
    ax.axhline(70, color="#a00", lw=0.6, ls="--", alpha=0.4)
    ax.axhline(180, color="#a60", lw=0.6, ls="--", alpha=0.4)
    ax.fill_between(a_dt, 70, 180, color="#aea", alpha=0.18)
    ax.set_ylabel("BG (mg/dL)")
    upper = max(a_bg.max(), a_cb.max())
    if a_cb_closed is not None: upper = max(upper, a_cb_closed.max())
    ax.set_ylim(40, max(280, upper + 10))
    ax.legend(loc="upper right")
    title = "24-hour worked example: actual vs counterfactual BG"
    if closed_loop: title += " (linearized vs closed-loop)"
    ax.set_title(title)
    ax.grid(alpha=0.3)

    ax2 = axes[1]
    pos = np.where(p_d > 0, p_d, 0)
    neg = np.where(p_d < 0, p_d, 0)
    ax2.bar(p_dt, pos, width=1/(24*4), color="#c43", label="Δdose > 0 (candidate gives more)")
    ax2.bar(p_dt, neg, width=1/(24*4), color="#37a", label="Δdose < 0 (candidate gives less)")
    ax2.axhline(0, color="black", lw=0.5)
    ax2.set_ylabel("Δdose (U)\nper 5-min step")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(alpha=0.3)

    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    return fig_to_svg(fig)

def make_delta_histogram():
    fig, ax = plt.subplots(figsize=(8, 4.0))
    deltas = pred_delta[pred_delta != 0]
    if len(deltas) == 0:
        ax.text(0.5, 0.5, "No nonzero Δdose events", ha="center", va="center", transform=ax.transAxes)
        return fig_to_svg(fig)
    bins = np.linspace(min(deltas.min(), -0.5), max(deltas.max(), 0.5), 60)
    ax.hist(deltas, bins=bins, color="#666", edgecolor="white")
    ax.axvline(0, color="black", lw=0.6)
    ax.set_xlabel("Δdose (U) per 5-min step")
    ax.set_ylabel("Count of timesteps")
    ax.set_title(f"Distribution of Δdose across {len(deltas):,} non-zero timesteps")
    ax.grid(alpha=0.3)
    return fig_to_svg(fig)

def make_bg_distribution():
    fig, ax = plt.subplots(figsize=(8, 4.0))
    bins = np.linspace(40, 300, 53)
    # For fair comparison, restrict ALL distributions to the closed-loop's
    # valid sample range when closed-loop is available — otherwise warm-up
    # samples skew the comparison.
    if counter_bg_closed is not None and counter_bg_closed_mask is not None:
        mask = counter_bg_closed_mask
        ax.hist(actual_bg[mask], bins=bins, color="#666", alpha=0.6, label="actual BG", edgecolor="white")
        ax.hist(counter_bg[mask], bins=bins, color="#c43", alpha=0.4, label=f"linearized counterfactual", edgecolor="white")
        ax.hist(counter_bg_closed[mask], bins=bins, color="#37a", alpha=0.4, label=f"closed-loop counterfactual", edgecolor="white")
    else:
        ax.hist(actual_bg, bins=bins, color="#666", alpha=0.6, label="actual BG", edgecolor="white")
        ax.hist(counter_bg, bins=bins, color="#c43", alpha=0.4, label=f"linearized counterfactual", edgecolor="white")
    ax.axvspan(0, 70, color="#a00", alpha=0.07)
    ax.axvspan(180, 1000, color="#a60", alpha=0.07)
    ax.axvline(70, color="#a00", lw=0.6, ls="--")
    ax.axvline(180, color="#a60", lw=0.6, ls="--")
    ax.set_xlim(40, 300)
    ax.set_xlabel("BG (mg/dL)")
    ax.set_ylabel("Count of CGM samples")
    ax.set_title("BG distribution: actual vs counterfactual")
    ax.legend()
    ax.grid(alpha=0.3)
    return fig_to_svg(fig)

def compute_tir_metrics():
    # When closed-loop is available, restrict ALL metrics to the closed-loop's
    # valid range so the comparison is apples-to-apples.
    if counter_bg_closed is not None and counter_bg_closed_mask is not None:
        mask = counter_bg_closed_mask
        a = actual_bg[mask]
        c = counter_bg[mask]
        cl = counter_bg_closed[mask]
    else:
        a = actual_bg; c = counter_bg; cl = None
    n = len(a)
    def frac(arr, lo, hi): return ((arr >= lo) & (arr <= hi)).sum() / n
    def below(arr, t): return (arr < t).sum() / n
    def above(arr, t): return (arr > t).sum() / n
    m = {
        "tir_act":  frac(a, 70, 180),
        "tir_cand": frac(c, 70, 180),
        "below70_act":  below(a, 70),
        "below70_cand": below(c, 70),
        "below54_act":  below(a, 54),
        "below54_cand": below(c, 54),
        "above180_act":  above(a, 180),
        "above180_cand": above(c, 180),
        "above250_act":  above(a, 250),
        "above250_cand": above(c, 250),
        "mean_act":  a.mean(),
        "mean_cand": c.mean(),
        "n": n,
    }
    if cl is not None:
        m.update({
            "tir_cl":  frac(cl, 70, 180),
            "below70_cl":  below(cl, 70),
            "below54_cl":  below(cl, 54),
            "above180_cl": above(cl, 180),
            "above250_cl": above(cl, 250),
            "mean_cl":  cl.mean(),
        })
    return m

def make_tir_bars(m):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    cats = ["TIR\n(70-180)", "<70", "<54", ">180", ">250"]
    a = [m["tir_act"], m["below70_act"], m["below54_act"], m["above180_act"], m["above250_act"]]
    c = [m["tir_cand"], m["below70_cand"], m["below54_cand"], m["above180_cand"], m["above250_cand"]]
    has_cl = "tir_cl" in m
    if has_cl:
        cl = [m["tir_cl"], m["below70_cl"], m["below54_cl"], m["above180_cl"], m["above250_cl"]]
    x = np.arange(len(cats))
    w = 0.27 if has_cl else 0.36
    if has_cl:
        ax.bar(x - w, [v*100 for v in a], w, color="#666", label="actual")
        ax.bar(x,    [v*100 for v in c], w, color="#c43", label="linearized counterfactual")
        ax.bar(x + w,[v*100 for v in cl], w, color="#37a", label=f"closed-loop ({candidate_label})")
        for xi, va, vc, vcl in zip(x, a, c, cl):
            ax.text(xi - w,    va*100 + 0.5, f"{va*100:.1f}%",  ha="center", fontsize=8)
            ax.text(xi,        vc*100 + 0.5, f"{vc*100:.1f}%",  ha="center", fontsize=8)
            ax.text(xi + w,    vcl*100 + 0.5, f"{vcl*100:.1f}%", ha="center", fontsize=8)
    else:
        ax.bar(x - w/2, [v*100 for v in a], w, color="#666", label="actual")
        ax.bar(x + w/2, [v*100 for v in c], w, color="#c43", label=f"counterfactual ({candidate_label})")
        for xi, va, vc in zip(x, a, c):
            ax.text(xi - w/2, va*100 + 0.5, f"{va*100:.1f}%", ha="center", fontsize=9)
            ax.text(xi + w/2, vc*100 + 0.5, f"{vc*100:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(cats)
    ax.set_ylabel("% of CGM samples")
    title = "TIR aggregation: % of samples in each zone"
    if has_cl: title += " (linearized vs closed-loop)"
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return fig_to_svg(fig)

# ---- Build report ----
metrics = compute_tir_metrics()
charts = {
    "activity": make_activity_curve(),
    "impulse": make_impulse_response(),
    "example24h": make_24h_example(),
    "deltahist": make_delta_histogram(),
    "bgdist": make_bg_distribution(),
    "tirbars": make_tir_bars(metrics),
}

n_pred = len(preds)
n_nonzero = int((pred_delta != 0).sum())
mean_pos = float(pred_delta[pred_delta > 0].mean()) if (pred_delta > 0).any() else 0.0
mean_neg = float(pred_delta[pred_delta < 0].mean()) if (pred_delta < 0).any() else 0.0

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>Counterfactual TIR Methodology — {candidate_label} vs {baseline_label}</title>
<style>
  body {{ font-family: -apple-system, "SF Pro", Helvetica, Arial, sans-serif; max-width: 920px; margin: 30px auto; padding: 0 24px; color: #222; line-height: 1.55; }}
  h1 {{ font-size: 26px; }}
  h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 36px; }}
  h3 {{ margin-top: 28px; }}
  .formula {{ background: #f6f8fa; border: 1px solid #d0d7de; padding: 10px 14px; border-radius: 6px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 13px; }}
  .callout {{ background: #fff8c5; border-left: 4px solid #d4a72c; padding: 10px 14px; border-radius: 4px; margin: 16px 0; font-size: 14px; }}
  .callout.bad {{ background: #ffebe9; border-left-color: #cf222e; }}
  .callout.good {{ background: #dafbe1; border-left-color: #1a7f37; }}
  table {{ border-collapse: collapse; margin: 12px 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 12px; text-align: left; }}
  th {{ background: #f6f8fa; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: ui-monospace, monospace; }}
  .meta {{ color: #57606a; font-size: 13px; }}
  svg {{ display: block; margin: 14px 0; max-width: 100%; height: auto; }}
</style></head><body>

<h1>Counterfactual TIR — methodology walkthrough</h1>
<div class="meta">Baseline: <b>{baseline_label}</b> &nbsp; · &nbsp; Candidate: <b>{candidate_label}</b></div>
<div class="meta">Window: {trace["intervalStart"]} → {trace["intervalEnd"]}</div>
<div class="meta">{n_pred:,} prediction steps · {len(actual):,} CGM samples · {n_nonzero:,} timesteps with nonzero Δdose</div>

<h2>1. The gap this metric closes</h2>
<p>The benefit/cost ratio metric (ODR/UDR/IDB/RDB) measures the <b>intensity of dose-deltas at risky moments</b>, weighted by Clarke-Kovatchev risk at the actual future BG. Each event contributes the same RMS-style weight regardless of how long the user spent in that zone. A 5-minute hyper and a 4-hour hyper both contribute one event each.</p>
<p>That's a real blind spot when comparing interventions that differ in <b>time-in-zone duration</b>. Counterfactual TIR fills the gap by estimating what BG <em>would have been</em> if the candidate algorithm had been running, then computing the standard time-in-range / time-below / time-above percentages on that estimated trajectory.</p>

<h2>2. The math</h2>
<div class="formula">
counter_BG(t)&nbsp;&nbsp;=&nbsp;&nbsp;actual_BG(t)&nbsp;&nbsp;−&nbsp;&nbsp;Σ<sub>t' ≤ t</sub>&nbsp;Δdose(t')&nbsp;·&nbsp;ISF(t')&nbsp;·&nbsp;(1 − P<sub>rem</sub>(t − t'))
</div>
<ul>
  <li><code>actual_BG(t)</code> is the historical CGM value — the trajectory that actually happened.</li>
  <li><code>Δdose(t') = candidate_dose(t') − baseline_dose(t')</code> is the difference in delivery the candidate would have made at time t' relative to baseline, in units (U) over the 5-min eval step.</li>
  <li><code>ISF(t')</code> is the insulin sensitivity in mg/dL/U active at the dose decision time.</li>
  <li><code>P<sub>rem</sub>(τ)</code> is the insulin model's <em>percent effect remaining</em> at τ minutes after the dose. <code>1 − P<sub>rem</sub></code> is the fraction of the dose's eventual BG impact that has already manifested by time τ.</li>
</ul>
<p>Sign convention: if the candidate gives <em>more</em> insulin (Δdose > 0), then more insulin reduces BG, so the impact term is added with a negative sign (counter_BG ends up below actual_BG). If the candidate gives <em>less</em>, counter_BG ends up above actual_BG.</p>

<h2>3. The insulin activity curve</h2>
<p>The dosing impact at any output time depends on how much of the dose's effect has already manifested by then. This comes from the insulin pharmacokinetic model (here: rapid-acting adult, total activity duration {int(duration_min)} min).</p>
{charts["activity"]}
<p class="meta">P<sub>rem</sub>(0) = 100% — a freshly delivered unit hasn't acted yet. P<sub>rem</sub>(360 min) ≈ 0 — by 6 hours, essentially all of its BG-lowering effect has occurred. (1 − P<sub>rem</sub>) is what we multiply Δdose × ISF by.</p>

<h2>4. A single-dose impulse response</h2>
<p>If the candidate gives 1.0 U more than baseline at exactly t=0 (and ISF = 50 mg/dL/U), the BG impact over time is just <code>1 × 50 × (1 − P<sub>rem</sub>(t))</code> — i.e., the activity curve scaled by 50:</p>
{charts["impulse"]}
<p class="meta">By 6 hours after the dose, 1 extra unit has manifested its full ~50 mg/dL drop. Note this is the BG impact <em>at each time</em>, not a cumulative integral.</p>

<h2>5. Convolving the dose-delta timeline</h2>
<p>In a real evaluation, candidate vs baseline differ at many timesteps. At each output time t, we sum the <em>still-active</em> impacts from all past Δdose events. Events older than the activity duration ({int(duration_min)} min) drop out automatically. This is a discrete convolution of the Δdose timeline with the activity-delivered curve, multiplied by ISF at each event.</p>

<h3>Distribution of Δdose for this comparison</h3>
{charts["deltahist"]}
<p class="meta">{n_nonzero:,} timesteps had nonzero Δdose. Mean positive Δdose: {mean_pos:.4f} U. Mean negative Δdose: {mean_neg:.4f} U.</p>

<h2>6. A real 24-hour example</h2>
<p>The window picked is the most-active 24 hours in the dataset (largest sum of |Δdose|). Top: actual CGM in black, counterfactual candidate trajectory in red, target zone (70-180) shaded green. Bottom: the Δdose timeline driving the difference.</p>
{charts["example24h"]}
<p class="meta">Where Δdose &gt; 0 (candidate would have given more), the red counterfactual trace falls below the black actual trace within ~1-2 hours, with full effect by ~6 hours. Where Δdose &lt; 0, the trace lifts above. Subtle Δdose accumulations matter: many 0.01 U deltas over an hour can compound to a meaningful BG difference.</p>

<h2>7. BG distribution across the full window</h2>
{charts["bgdist"]}
<p class="meta">If candidate primarily over-delivered relative to baseline, the distribution shifts left (more time below 70). If primarily under-delivered, it shifts right. The shape change tells you how the candidate redistributes BG-zone time, beyond just where the means land.</p>

<h2>8. Aggregating to TIR percentages</h2>
<p>Each CGM sample is binned into the standard zones. The percentages reported in the bench output are simply the fraction of the {len(actual):,} CGM samples that fall in each zone, computed once for actual_BG and once for counterfactual_BG.</p>
{charts["tirbars"]}

<h3>Numeric summary</h3>
{("<table>"
"<tr><th>Metric</th><th class='num'>actual</th><th class='num'>linearized</th><th class='num'>closed-loop</th><th class='num'>Δ closed-loop</th></tr>"
f"<tr><td>Time in 70-180 (TIR)</td><td class='num'>{metrics['tir_act']*100:.2f}%</td><td class='num'>{metrics['tir_cand']*100:.2f}%</td><td class='num'>{metrics['tir_cl']*100:.2f}%</td><td class='num'>{(metrics['tir_cl']-metrics['tir_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time below 70</td><td class='num'>{metrics['below70_act']*100:.2f}%</td><td class='num'>{metrics['below70_cand']*100:.2f}%</td><td class='num'>{metrics['below70_cl']*100:.2f}%</td><td class='num'>{(metrics['below70_cl']-metrics['below70_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time below 54</td><td class='num'>{metrics['below54_act']*100:.2f}%</td><td class='num'>{metrics['below54_cand']*100:.2f}%</td><td class='num'>{metrics['below54_cl']*100:.2f}%</td><td class='num'>{(metrics['below54_cl']-metrics['below54_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time above 180</td><td class='num'>{metrics['above180_act']*100:.2f}%</td><td class='num'>{metrics['above180_cand']*100:.2f}%</td><td class='num'>{metrics['above180_cl']*100:.2f}%</td><td class='num'>{(metrics['above180_cl']-metrics['above180_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time above 250</td><td class='num'>{metrics['above250_act']*100:.2f}%</td><td class='num'>{metrics['above250_cand']*100:.2f}%</td><td class='num'>{metrics['above250_cl']*100:.2f}%</td><td class='num'>{(metrics['above250_cl']-metrics['above250_act'])*100:+.2f}</td></tr>"
f"<tr><td>Mean BG</td><td class='num'>{metrics['mean_act']:.1f} mg/dL</td><td class='num'>{metrics['mean_cand']:.1f} mg/dL</td><td class='num'>{metrics['mean_cl']:.1f} mg/dL</td><td class='num'>{metrics['mean_cl']-metrics['mean_act']:+.1f}</td></tr>"
"</table>") if 'tir_cl' in metrics else
("<table>"
"<tr><th>Metric</th><th class='num'>actual</th><th class='num'>counterfactual</th><th class='num'>Δ pp</th></tr>"
f"<tr><td>Time in 70-180 (TIR)</td><td class='num'>{metrics['tir_act']*100:.2f}%</td><td class='num'>{metrics['tir_cand']*100:.2f}%</td><td class='num'>{(metrics['tir_cand']-metrics['tir_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time below 70</td><td class='num'>{metrics['below70_act']*100:.2f}%</td><td class='num'>{metrics['below70_cand']*100:.2f}%</td><td class='num'>{(metrics['below70_cand']-metrics['below70_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time below 54</td><td class='num'>{metrics['below54_act']*100:.2f}%</td><td class='num'>{metrics['below54_cand']*100:.2f}%</td><td class='num'>{(metrics['below54_cand']-metrics['below54_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time above 180</td><td class='num'>{metrics['above180_act']*100:.2f}%</td><td class='num'>{metrics['above180_cand']*100:.2f}%</td><td class='num'>{(metrics['above180_cand']-metrics['above180_act'])*100:+.2f}</td></tr>"
f"<tr><td>Time above 250</td><td class='num'>{metrics['above250_act']*100:.2f}%</td><td class='num'>{metrics['above250_cand']*100:.2f}%</td><td class='num'>{(metrics['above250_cand']-metrics['above250_act'])*100:+.2f}</td></tr>"
f"<tr><td>Mean BG</td><td class='num'>{metrics['mean_act']:.1f} mg/dL</td><td class='num'>{metrics['mean_cand']:.1f} mg/dL</td><td class='num'>{metrics['mean_cand']-metrics['mean_act']:+.1f}</td></tr>"
"</table>")}

<h2>9. Caveats and limitations</h2>
<div class="callout">
  <strong>This is a linearized counterfactual, not a full forward simulation.</strong>
</div>
<ul>
  <li><b>No feedback loop.</b> The candidate's earlier dose deltas don't change its later dose decisions. If candidate at 09:00 gives more insulin, the prediction at 10:00 sees the same actual BG (not a counterfactual lower BG) when deciding what to do at 10:00. The candidate's behavior at every t is computed against the actual past, not its own past.</li>
  <li><b>Constant ISF assumption per event.</b> ISF used for an event's impact is the ISF at the dose decision time, not the (potentially different) ISF that would be active at the time the effect manifests. With mid-absorption ISF this matches Loop's actual dose calculation, so the counterfactual is consistent with how Loop sized the dose.</li>
  <li><b>No real-world compensation.</b> If candidate's extra insulin would have driven BG to 50 mg/dL, in reality the user would notice and eat. The simulation does not model rescue carbs, alarms, or behavioral response. Absolute hypo time percentages are upper-bound estimates of what would happen if the user took candidate's dose with no compensation.</li>
  <li><b>Bounded drift.</b> Because counter_BG is anchored to actual_BG at every output time (additive correction, not multiplicative chain), errors are bounded by the magnitude of the dose-delta impacts. Compare to true open-loop forward simulation, which would diverge over hours.</li>
</ul>
<p>For the comparative use case (ranking interventions), the linearized form is sufficient: the relative ordering of candidates is reliable. For absolute "would the user have spent X% time in hypo" claims, treat the magnitudes as upper-bounds and account for compensation.</p>

<h2>10. What this simulation does NOT cover</h2>
<ul>
  <li>Differences in <em>recommended carb absorption modeling</em> if the candidate uses a different model (we don't apply candidate's dynamic-absorption to actual carb effects).</li>
  <li>Closed-loop interactions where, e.g., the candidate's earlier suspension changes the user's eating behavior or vice versa.</li>
  <li>Insulin-on-board interactions across multiple doses if the candidate stacks doses differently than baseline (in practice these effects are small in well-tuned systems).</li>
  <li>Sensor noise: the actual BG used as the anchor includes sensor error, which propagates into counter_BG unchanged.</li>
</ul>

</body></html>"""

with open(out_path, "w") as f:
    f.write(html)

print(f"Wrote {out_path}")
print(f"  Predictions: {n_pred:,}  CGM samples: {len(actual):,}  Δdose nonzero: {n_nonzero:,}")
print(f"  TIR actual: {metrics['tir_act']*100:.2f}%  candidate: {metrics['tir_cand']*100:.2f}%  Δ {(metrics['tir_cand']-metrics['tir_act'])*100:+.2f}pp")
