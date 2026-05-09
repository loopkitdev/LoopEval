#!/usr/bin/env python3
"""Generate a methodology report explaining the closed-loop counterfactual
simulation: how the iteration steps forward, what state is mutated at each
step, what's fed back into the next decision, and where it diverges from the
linearized counterfactual.

Reads a closed-loop trace JSON from `loop-eval simulate --trace-out=...` (must
have `closedLoop: true` and a `counter` field) and writes a self-contained
HTML report with embedded SVG charts.

usage: closed_loop_methodology_report.py <trace.json> <out.html>
"""
import json, sys, math, datetime as dt, io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

if len(sys.argv) < 3:
    print("usage: closed_loop_methodology_report.py <trace.json> <out.html>", file=sys.stderr)
    sys.exit(2)

trace_path, out_path = sys.argv[1], sys.argv[2]
with open(trace_path) as f:
    trace = json.load(f)

if not trace.get("closedLoop"):
    print("ERROR: trace is not a closed-loop trace (closedLoop != true). "
          "Generate one with `loop-eval simulate --trace-out=...`.", file=sys.stderr)
    sys.exit(2)

def parse_t(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

baseline_label = trace["baselineLabel"]
candidate_label = trace["candidateLabel"]
duration_min = trace["activityDurationMinutes"]

preds = sorted(
    [(parse_t(p["t"]), p["baselineDose"], p["candidateDose"], p["deltaDose"], p["isf"]) for p in trace["predictions"]],
    key=lambda x: x[0]
)
actual = sorted([(parse_t(a["t"]), a["bg"]) for a in trace["actual"]], key=lambda x: x[0])
counter = sorted([(parse_t(c["t"]), c["bg"]) for c in trace["counter"]], key=lambda x: x[0])
curve = trace["insulinActivityCurve"]

pred_t   = np.array([p[0] for p in preds])
pred_dB  = np.array([p[1] for p in preds])
pred_dC  = np.array([p[2] for p in preds])
pred_dD  = np.array([p[3] for p in preds])
pred_isf = np.array([p[4] for p in preds])

actual_t = np.array([a[0] for a in actual])
actual_bg = np.array([a[1] for a in actual])
counter_t = np.array([c[0] for c in counter])
counter_bg = np.array([c[1] for c in counter])

curve_min = np.array([c["tMin"] for c in curve])
percent_delivered = np.array([c["percentDelivered"] for c in curve])
percent_remaining = np.array([c["percentRemaining"] for c in curve])

def lookup_pdelivered(min_after):
    if min_after < 0: return 0.0
    if min_after > duration_min: return 1.0
    idx = min_after / 5.0
    i0 = int(math.floor(idx))
    i1 = min(i0 + 1, len(percent_delivered) - 1)
    frac = idx - i0
    return percent_delivered[i0] * (1 - frac) + percent_delivered[i1] * frac

# ---- Pick illustrative samples from the trace ----
nonzero_mask = pred_dD != 0
nonzero_idx = np.where(nonzero_mask)[0]
# Pick a Δdose with a clean forward window: ~mid-trace, magnitude > P75
abs_d = np.abs(pred_dD)
big_thresh = np.quantile(abs_d[nonzero_mask], 0.85) if nonzero_idx.size else 0
candidates_idx = [i for i in nonzero_idx if abs_d[i] >= big_thresh and i > 144 and i < len(preds) - 144]
focus_step_idx = candidates_idx[len(candidates_idx) // 2] if candidates_idx else (nonzero_idx[len(nonzero_idx)//2] if nonzero_idx.size else 0)

# A 6-hour window around the focus step for the divergence-zoom chart
focus_t = pred_t[focus_step_idx]
zoom_start = focus_t - dt.timedelta(hours=2)
zoom_end   = focus_t + dt.timedelta(hours=4)

# ---- Charts ----
def fig_to_svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

def chart_state_diagram():
    """One-step iteration data-flow diagram."""
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, label, color="#eef0f2"):
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                           linewidth=1, edgecolor="#444", facecolor=color)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=9)

    def arrow(x1, y1, x2, y2, color="#444", style="-|>"):
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12,
                            color=color, linewidth=1.2)
        ax.add_patch(a)

    # State (left column, mutable)
    box(0.2, 7.5, 3.2, 1.3, "counter_glucose[]\n(mutable BG samples)", "#ffeec2")
    box(0.2, 5.5, 3.2, 1.3, "virtualDoses[]\n(accumulated Δdose history)", "#ffeec2")
    box(0.2, 3.5, 3.2, 1.3, "data.doses[]\n(actual delivered doses, frozen)", "#dcecf3")
    box(0.2, 1.5, 3.2, 1.3, "data.glucose[] (frozen reference)\nbaselineDoseByTime[t] (precomputed)", "#dcecf3")

    # Step body (middle column)
    box(4.2, 7.5, 3.5, 1.3, "1. snapshot counter glucose\n   into EvalGlucoseSamples", "#eef0f2")
    box(4.2, 5.7, 3.5, 1.3, "2. mergeSorted(actual + virtual)\n   → combinedDoses", "#eef0f2")
    box(4.2, 3.9, 3.5, 1.3, "3. LoopAlgorithm.generatePrediction\n   (with config flags)", "#cdeac0")
    box(4.2, 2.1, 3.5, 1.3, "4. computeDoseRecommendation\n   → candidateDose, deltaDose", "#cdeac0")

    # Output / feedback (right column)
    box(8.2, 7.5, 1.6, 1.3, "Step row\n(t, BG, doses)", "#eef0f2")
    box(8.2, 5.7, 1.6, 1.3, "feedback A:\nmutate counter_mgdl\n[i for i: t < t_i ≤ t+DIA]", "#ffd1d1")
    box(8.2, 3.9, 1.6, 1.3, "feedback B:\nappend virtual\nbolus at t", "#ffd1d1")

    # Arrows from state into step
    arrow(3.4, 8.1, 4.2, 8.1)   # counter_glucose -> snapshot
    arrow(3.4, 6.1, 4.2, 6.3)   # virtualDoses -> merge
    arrow(3.4, 4.1, 4.2, 6.0)   # data.doses -> merge
    arrow(7.7, 6.3, 7.7, 5.2)   # snapshot+merge feed predict (left side)
    arrow(7.7, 8.1, 7.7, 8.7); ax.text(7.85, 8.5, "→ generatePrediction", fontsize=8)
    arrow(5.95, 7.5, 5.95, 7.0)
    arrow(5.95, 5.7, 5.95, 5.2)
    arrow(5.95, 3.9, 5.95, 3.4)

    # Step → outputs
    arrow(7.7, 2.7, 8.2, 2.7)  # dose rec -> feedback B
    arrow(7.7, 4.5, 8.2, 4.5, color="#cf222e")  # also feedback A (glucose)
    arrow(7.7, 7.0, 8.2, 8.1, color="#888")    # to step row

    # Feedback loops back to state
    arrow(8.7, 5.7, 1.8, 7.5, color="#cf222e", style="-|>")   # mutate counter_glucose
    arrow(8.7, 3.9, 1.8, 5.5, color="#cf222e", style="-|>")   # append virtual

    # Labels
    ax.text(1.8, 9.4, "STATE  (carried across steps)", ha="center", fontsize=10, fontweight="bold")
    ax.text(5.95, 9.4, "ONE STEP at time t", ha="center", fontsize=10, fontweight="bold")
    ax.text(9.0, 9.4, "OUTPUT + FEEDBACK", ha="center", fontsize=10, fontweight="bold")
    ax.text(0.1, 0.7, "Frozen inputs in blue · Mutable state in yellow · Decision body in green · Feedback edges in red",
            fontsize=8, color="#444")
    return fig_to_svg(fig)

def chart_activity_curve():
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.plot(curve_min, percent_remaining*100, "-", color="#0969da", label="% remaining (IOB curve)")
    ax.plot(curve_min, percent_delivered*100, "-", color="#cf222e", label="% delivered (effect-on-BG)")
    ax.set_xlabel("minutes after dose")
    ax.set_ylabel("% of total dose effect")
    ax.set_title(f"Insulin activity curve (DIA = {duration_min:.0f} min)")
    ax.set_xlim(0, duration_min)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="center right")
    return fig_to_svg(fig)

def chart_one_step_pulse():
    """For the focus_step, show how Δdose × ISF × pd(τ) pulses out into future BG samples."""
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 5.5), sharex=True,
                             gridspec_kw={"height_ratios": [1, 2]})
    t0 = pred_t[focus_step_idx]
    delta = pred_dD[focus_step_idx]
    isf = pred_isf[focus_step_idx]

    # Top panel: Δdose impulse
    axes[0].axvline(0, color="#888", linewidth=0.5, alpha=0.5)
    axes[0].axhline(0, color="#888", linewidth=0.5, alpha=0.5)
    axes[0].vlines([0], 0, delta, color="#cf222e" if delta < 0 else "#1a7f37", linewidth=3)
    axes[0].scatter([0], [delta], s=80, color="#cf222e" if delta < 0 else "#1a7f37", zorder=3)
    axes[0].set_ylabel("Δdose (U)\n(candidate − baseline)")
    axes[0].set_title(f"One step at t = {t0.isoformat(timespec='minutes')}    "
                      f"Δdose = {delta:+.4f} U,  ISF = {isf:.0f} mg/dL/U")
    pad = max(abs(delta) * 1.2, 1e-6)
    axes[0].set_ylim(-pad if delta < 0 else -pad/4, pad if delta > 0 else pad/4)
    axes[0].grid(True, alpha=0.3)

    # Bottom panel: pulse applied to future BG samples
    horizons_min = np.arange(5, duration_min + 1, 5)
    pd_curve = np.array([lookup_pdelivered(m) for m in horizons_min])
    impact = -delta * isf * pd_curve   # impact ON BG (sign: more insulin → BG lower → counter_bg below actual)

    # Find actual BG values at each horizon for context (linear interp on stored counter trace
    # would re-derive what we already have, so use both actual and counter from trace).
    sample_minutes = horizons_min
    sample_times = np.array([t0 + dt.timedelta(minutes=int(m)) for m in horizons_min])
    actual_at_t = np.interp(
        np.array([(s - actual_t[0]).total_seconds() for s in sample_times]),
        np.array([(t - actual_t[0]).total_seconds() for t in actual_t]),
        actual_bg,
    )
    counter_after = actual_at_t + impact

    axes[1].plot(horizons_min, actual_at_t,    "-",  color="#0969da", linewidth=1.5, label="actual BG (frozen reference)")
    axes[1].plot(horizons_min, counter_after,  "-",  color="#cf222e", linewidth=1.5, label="counter BG after this Δdose only")
    axes[1].fill_between(horizons_min, actual_at_t, counter_after, color="#cf222e", alpha=0.15,
                         label=f"|impact| (peaks at {abs(impact).max():.1f} mg/dL)")
    axes[1].set_xlabel(f"minutes after t (only this Δdose's pulse, ignoring later steps)")
    axes[1].set_ylabel("BG (mg/dL)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", fontsize=9)
    axes[1].set_xlim(0, duration_min)

    return fig_to_svg(fig)

def chart_six_hour_zoom():
    """A 6-hour window around the focus step showing actual vs counter BG, plus Δdose marks."""
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 5.0), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})

    mask_a = (actual_t >= zoom_start) & (actual_t <= zoom_end)
    mask_c = (counter_t >= zoom_start) & (counter_t <= zoom_end)
    mask_p = (pred_t >= zoom_start) & (pred_t <= zoom_end)

    axes[0].plot(actual_t[mask_a],  actual_bg[mask_a],  "-", color="#0969da", linewidth=1.5, label="actual BG (frozen)")
    axes[0].plot(counter_t[mask_c], counter_bg[mask_c], "-", color="#cf222e", linewidth=1.5, label="counter BG (closed-loop)")
    axes[0].axhspan(70, 180, color="#1a7f37", alpha=0.06, label="70–180 mg/dL")
    axes[0].axvline(focus_t, color="#888", linewidth=0.5, linestyle=":", alpha=0.7)
    axes[0].set_ylabel("BG (mg/dL)")
    axes[0].set_title(f"6-hour zoom around the focus step ({focus_t.strftime('%Y-%m-%d %H:%M')} UTC)")
    axes[0].legend(loc="best", fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # Δdose stems
    pos = pred_dD[mask_p] > 0
    neg = pred_dD[mask_p] < 0
    axes[1].vlines(pred_t[mask_p][pos], 0, pred_dD[mask_p][pos], color="#1a7f37", linewidth=1)
    axes[1].vlines(pred_t[mask_p][neg], 0, pred_dD[mask_p][neg], color="#cf222e", linewidth=1)
    axes[1].axhline(0, color="#888", linewidth=0.5)
    axes[1].axvline(focus_t, color="#888", linewidth=0.5, linestyle=":", alpha=0.7)
    axes[1].set_ylabel("Δdose (U)")
    axes[1].set_xlabel("time (UTC)")
    axes[1].grid(True, alpha=0.3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    return fig_to_svg(fig)

# Drift — counter and actual live on different time grids (counter is on the
# 5-min step cadence, actual on the irregular CGM cadence). Interpolate actual
# onto counter's grid so per-sample drift is meaningful.
actual_t_secs  = np.array([(t - actual_t[0]).total_seconds() for t in actual_t])
counter_t_secs = np.array([(t - actual_t[0]).total_seconds() for t in counter_t])
actual_on_counter = np.interp(counter_t_secs, actual_t_secs, actual_bg,
                               left=np.nan, right=np.nan)
drift = counter_bg - actual_on_counter
drift_valid = drift[~np.isnan(drift)]

def chart_full_window():
    """Full-window actual vs counter trajectories."""
    fig, ax = plt.subplots(figsize=(9.0, 3.5))
    ax.plot(actual_t,  actual_bg,  "-", color="#0969da", linewidth=0.5, alpha=0.7, label="actual")
    ax.plot(counter_t, counter_bg, "-", color="#cf222e", linewidth=0.5, alpha=0.7, label="counter (closed-loop)")
    ax.axhspan(70, 180, color="#1a7f37", alpha=0.05)
    ax.set_ylabel("BG (mg/dL)")
    ax.set_title(f"Full {(actual_t[-1] - actual_t[0]).days}-day window — actual vs counter trajectories")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    fig.autofmt_xdate()

    mean_drift = float(np.nanmean(drift))
    p95_abs   = float(np.nanpercentile(np.abs(drift_valid), 95))
    ax.text(0.02, 0.96, f"mean(counter − actual) = {mean_drift:+.1f} mg/dL\nP95 |drift| = {p95_abs:.1f} mg/dL",
            transform=ax.transAxes, ha="left", va="top", fontsize=9,
            bbox=dict(facecolor="white", edgecolor="#888", boxstyle="round,pad=0.3"))
    return fig_to_svg(fig)

def chart_drift_histogram():
    """Distribution of the per-sample drift (counter − actual on counter's grid)."""
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    # Clip extreme tails for readability — note count of clipped values
    clip = 60.0
    plot_drift = np.clip(drift_valid, -clip, clip)
    ax.hist(plot_drift, bins=80, color="#444", alpha=0.7)
    ax.axvline(0, color="#0969da", linewidth=1)
    n_outliers = int(np.sum(np.abs(drift_valid) > clip))
    ax.set_xlabel(f"counter_BG − actual_BG (mg/dL)   (clipped to ±{int(clip)}; {n_outliers} outliers beyond)")
    ax.set_ylabel("# samples")
    ax.set_title("Drift distribution — closed-loop divergence per sample")
    ax.grid(True, alpha=0.3)
    return fig_to_svg(fig)

# ---- Stats for the report body ----
n_pred = len(preds)
n_actual = len(actual)
n_nonzero = int(nonzero_mask.sum())
focus_delta = pred_dD[focus_step_idx]
focus_isf   = pred_isf[focus_step_idx]
focus_dB    = pred_dB[focus_step_idx]
focus_dC    = pred_dC[focus_step_idx]

# ---- Build report ----
charts = {
    "state":     chart_state_diagram(),
    "activity":  chart_activity_curve(),
    "step":      chart_one_step_pulse(),
    "zoom":      chart_six_hour_zoom(),
    "fullwin":   chart_full_window(),
    "driftdist": chart_drift_histogram(),
}

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>Closed-loop counterfactual simulation — methodology</title>
<style>
  body {{ font-family: -apple-system, "SF Pro", Helvetica, Arial, sans-serif; max-width: 960px; margin: 30px auto; padding: 0 24px; color: #222; line-height: 1.55; }}
  h1 {{ font-size: 26px; }}
  h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 36px; }}
  h3 {{ margin-top: 28px; }}
  .formula {{ background: #f6f8fa; border: 1px solid #d0d7de; padding: 10px 14px; border-radius: 6px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 13px; }}
  .pseudo {{ background: #f6f8fa; border-left: 3px solid #0969da; padding: 10px 14px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12.5px; white-space: pre; overflow-x: auto; }}
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

<h1>Closed-loop counterfactual simulation — methodology</h1>
<div class="meta">Baseline: <b>{baseline_label}</b> &nbsp;·&nbsp; Candidate: <b>{candidate_label}</b></div>
<div class="meta">Window: {trace["intervalStart"]} → {trace["intervalEnd"]}</div>
<div class="meta">{n_pred:,} prediction steps · {n_actual:,} CGM samples · {n_nonzero:,} timesteps with nonzero Δdose · DIA = {duration_min:.0f} min</div>

<h2>1. The gap this fills</h2>
<p>The bench command's counterfactual is <b>linearized</b>: it computes the candidate's Δdose at each timestep against the <em>actual</em> CGM history, then convolves those Δdose impulses through the insulin activity curve and subtracts the result from the actual BG to produce a counterfactual trajectory. That's correct for small Δdose streams where the candidate's behaviour barely diverges from the baseline, because the input the candidate sees (actual BG, actual past doses) is approximately what it would have seen if it had been running.</p>
<p>For aggressive candidates — IRC, dynamic-ISF, asymmetric momentum at the extremes — the linearization breaks. Once the candidate's BG trajectory drifts from actual, every <em>future</em> decision should be made against the drifted BG, but the linearization keeps feeding the candidate the actual CGM. So the candidate keeps over-correcting (or under-correcting) by the same amount it always would have — there's no self-correction loop. Closed-loop simulation closes that loop.</p>

<h2>2. The per-step iteration</h2>
<p>The simulator walks forward in 5-minute steps. At each step <code>t</code>, it builds the candidate's <em>own</em> view of glucose history and dose history, asks LoopAlgorithm to make a prediction and dose recommendation against that view, then updates two pieces of state with the candidate's resulting decision before moving to the next step.</p>
{charts["state"]}
<p>Two pieces of mutable state live across steps:</p>
<ul>
  <li><b><code>counter_glucose[]</code></b> — the candidate's BG samples. Starts identical to <code>actual_glucose[]</code>; values get mutated as the candidate's decisions accumulate.</li>
  <li><b><code>virtualDoses[]</code></b> — the candidate's extra/reduced deliveries, one per step where Δdose ≠ 0. Each is a virtual instantaneous bolus of size Δdose at time <code>t</code>.</li>
</ul>
<p>Frozen inputs (read but never mutated):</p>
<ul>
  <li><b><code>data.glucose[]</code></b> — the actual CGM history, kept for reference and reporting.</li>
  <li><b><code>data.doses[]</code></b> — the actual delivered doses (what the user's pump did, on the historical day).</li>
  <li><b><code>baselineDoseByTime[t]</code></b> — the baseline configuration's <code>recommendedDeltaU</code> at every step, precomputed in one parallel sweep against actual data. The baseline runs <em>open-loop</em> against history because it's the reference; it doesn't need feedback.</li>
</ul>

<h2>3. What happens at one step (in code order)</h2>
<div class="pseudo">while t ≤ interval.end:
    # 1. Snapshot the candidate's effective glucose history.
    #    counter_mgdl is mutated by prior steps' Δdose impacts;
    #    snap into EvalGlucoseSamples preserving timestamps + metadata.
    counter_samples = [(s.t, counter_mgdl[i]) for i, s in enumerate(counter_glucose)]

    # 2. Merge actual doses and accumulated virtual doses (both already sorted by time).
    combined_doses = mergeSorted(data.doses, virtualDoses)

    # 3. Build the input window the algorithm needs (15-min momentum window,
    #    insulinLookbackHours of doses, etc.) using counter_samples + combined_doses.
    input = InputWindowBuilder(counter_samples, combined_doses, carbs, ...).buildInput(at: t)

    # 4. Run LoopAlgorithm against the candidate's view, with the candidate's flags.
    prediction = LoopAlgorithm.generatePrediction(
        glucose=input.glucose,                    #  <— uses counter, not actual
        doses=input.doses,                        #  <— actual + accumulated Δdose history
        sensitivity=input.sensitivity,            #  scaled per candidateConfig
        useIntegralRC=candidateConfig.useIntegralRC,
        useAsymmetricMomentum=candidateConfig.useAsymmetricMomentum,
        useHybridAsymmetricMomentum=candidateConfig.useHybridAsymmetricMomentum,
        ...
    )

    # 5. Translate prediction → actual recommendedDeltaU using the same dose-recommender
    #    Loop ships in production (suspendThreshold, maxBolus, application factor, etc.).
    candidateDose = computeDoseRecommendation(prediction, suspendThreshold, maxBolus, ...)
    baselineDose  = baselineDoseByTime[t]
    deltaDose     = candidateDose - baselineDose

    # 6. FEEDBACK A — propagate Δdose's BG impact onto FUTURE counter samples.
    #    Sign convention: positive Δdose means MORE insulin → BG goes DOWN.
    if deltaDose != 0 and isf > 0:
        for i, sample in enumerate(counter_glucose):
            tau = sample.t - t
            if tau ≤ 0: continue
            if tau > activityDuration: break
            pd = 1 − insulinModel.percentEffectRemaining(at: tau)   # cumulative % delivered
            counter_mgdl[i] -= deltaDose * isf * pd

        # 7. FEEDBACK B — append a virtual bolus so future IOB calculations
        #    include the candidate's extra/reduced delivery.
        virtualDoses.append(Bolus(t=t, volume=deltaDose, automatic=True))

    record_step(t, actualBG, counter_mgdl[at t], baselineDose, candidateDose, deltaDose, isf)
    t += evalStep
</div>

<h2>4. The two feedback paths</h2>
<p>The candidate's decision at <code>t</code> changes two things for the future:</p>

<h3>4a. Glucose feedback — Δdose's pharmacodynamic impact on counter_BG</h3>
<p>For every counter glucose sample at time <code>t' &gt; t</code> with <code>τ = t' − t ≤ DIA</code>:</p>
<div class="formula">
counter_mgdl[t']  −=  Δdose · ISF(t) · (1 − P<sub>rem</sub>(τ))
</div>
<p>where <code>P<sub>rem</sub>(τ)</code> is the insulin model's percent-effect-remaining at τ minutes after the dose, and <code>1 − P<sub>rem</sub>(τ)</code> is therefore the cumulative fraction of the dose's eventual BG impact that has manifested by τ. The activity curve used here:</p>
{charts["activity"]}
<p>This update is <em>cumulative</em>: every prior step's Δdose has already shifted these samples; this step's Δdose adds another shift on top. By the time step <code>t</code> runs, <code>counter_mgdl[t]</code> already reflects all earlier Δdose pulses that could reach it.</p>

<h3>4b. Dose feedback — append to virtualDoses[]</h3>
<p>The Δdose is also recorded as a virtual instantaneous bolus of size Δdose at time <code>t</code>. From the next step onward, that virtual bolus is in <code>combined_doses</code>, so the LoopAlgorithm's IOB calculation correctly accounts for the candidate having delivered (or withheld) that insulin. Without this, the candidate would forget its own deliveries and would over-correct again on the next step.</p>
<div class="callout">Sign matters. A positive Δdose (candidate delivered more than baseline) becomes a positive bolus, raising IOB. A negative Δdose (candidate held back) becomes a <em>negative</em> bolus, lowering IOB. The insulin model treats both linearly, so they're symmetric. The same Δdose magnitude is treated as adding-equivalent or subtracting-equivalent insulin in the BG response.</div>

<h2>5. One step in detail (sampled from this run)</h2>
<p>This is a real step from the trace, picked from the upper-quartile-magnitude band somewhere around the middle of the trace so the forward pulse window is fully visible.</p>
<table>
<tr><th>Field</th><th class="num">value</th></tr>
<tr><td>t</td>            <td class="num">{focus_t.isoformat(timespec='minutes')}</td></tr>
<tr><td>baselineDose</td> <td class="num">{focus_dB:+.4f} U</td></tr>
<tr><td>candidateDose</td><td class="num">{focus_dC:+.4f} U</td></tr>
<tr><td>Δdose</td>        <td class="num">{focus_delta:+.4f} U</td></tr>
<tr><td>ISF(t)</td>       <td class="num">{focus_isf:.0f} mg/dL/U</td></tr>
<tr><td>peak BG impact</td><td class="num">{abs(focus_delta) * focus_isf:.1f} mg/dL  (= |Δdose| · ISF, asymptote of the pulse)</td></tr>
</table>
{charts["step"]}
<p>The bottom panel shows the actual BG trajectory in blue and the counter trajectory in red, where the red is constructed by applying <em>only</em> this step's Δdose pulse (later steps are excluded for clarity). The shaded region shows the pulse magnitude; this is one term in an enormous sum that builds up the full counter trajectory.</p>

<h2>6. A 6-hour zoom — accumulating impact</h2>
<p>Now the actual vs counter divergence around the same focus step, with all Δdose decisions visible as stems below.</p>
{charts["zoom"]}
<p>Each green stem is a step where the candidate would have delivered more than the baseline; red stems are where it held back. The counter trajectory tracks actual closely until enough Δdose mass has accumulated, then diverges. A single big Δdose isn't always the cause — many small same-direction Δdoses can drift the trajectory just as far.</p>

<h2>7. Full-window drift</h2>
{charts["fullwin"]}
{charts["driftdist"]}
<p>If the histogram is centred near zero with a tight spread, the candidate's behaviour is close to the baseline overall — closed-loop and linearized counterfactuals will agree. A skewed distribution (asymmetric tails) means the candidate systematically biases delivery in one direction, which is precisely the case where the linearized counterfactual under-reports impact.</p>

<h2>8. When closed-loop disagrees with linearized</h2>
<p>Define <code>Δdose<sub>open</sub>(t)</code> as the candidate's Δdose computed against the <em>actual</em> CGM at <code>t</code> (what the bench's linearized form uses), and <code>Δdose<sub>closed</sub>(t)</code> as the closed-loop candidate's Δdose at <code>t</code> in this trace. Two reasons they differ:</p>
<ol>
  <li><b>Glucose feedback.</b> By time <code>t</code>, counter_BG has drifted from actual. The candidate's BG forecast — and therefore its dose recommendation — is computed against a different starting BG.</li>
  <li><b>IOB feedback.</b> The candidate's IOB at <code>t</code> includes virtual boluses from prior steps, while the linearized version sees only actual delivered IOB. A candidate that's been over-delivering will see higher IOB in closed-loop and may suspend; in linearized form it'll happily over-deliver again.</li>
</ol>
<p>For mild candidates the gap is small. For aggressive candidates (IRC, dynamic-ISF in some regimes, asym momentum's hybrid variant) the gap can flip the directional read of safety metrics — see the worked example earlier today where linearized said asymmetric momentum reduced &lt;70 by 0.4 pp but closed-loop said it increased &lt;70 by 0.5 pp on the same window.</p>

<h2>9. Limitations</h2>
<ul>
  <li><b>No physiology beyond the insulin model.</b> The simulator credits/debits BG by <code>Δdose · ISF · (1 − P<sub>rem</sub>)</code>. It does not model carb absorption divergence, glucagon, exercise, or Kalman-residual physiology not captured in ISF.</li>
  <li><b>Sensitivity is fixed at decision time.</b> ISF used to apply Δdose's BG impact is the value active at <code>t</code>; subsequent ISF changes (hourly schedule, dynamic-ISF boost) don't modify the in-flight pulse retroactively.</li>
  <li><b>Sequential by construction.</b> The candidate's prediction at <code>t</code> depends on earlier feedback; cannot parallelize across steps. Roughly 10× slower than bench. Use bench for first-pass sweeps, simulate for the candidates you actually want to recommend.</li>
  <li><b>No user-side compensatory action.</b> Real users notice high BG and bolus, low BG and eat — none of that is in the simulation. The counter trajectory is "what the algorithm would have produced if the user did exactly nothing differently."</li>
  <li><b>Baseline runs open-loop.</b> The baseline configuration's predictions are computed in a single parallel sweep against actual data, not closed-loop. That's deliberate: the baseline is the reference (what actually happened, predicted), and double-applying feedback would produce a counter-of-counter with no clear interpretation.</li>
</ul>

</body></html>
"""

with open(out_path, "w") as f:
    f.write(html)
print(f"Wrote {out_path}")
print(f"  Predictions: {n_pred:,}  CGM samples: {n_actual:,}  Δdose nonzero: {n_nonzero:,}")
print(f"  Focus step: idx={focus_step_idx} t={focus_t.isoformat()}  Δdose={focus_delta:+.4f}  ISF={focus_isf:.0f}")
print(f"  Drift: mean={float(np.nanmean(drift_valid)):+.2f}  median={float(np.nanmedian(drift_valid)):+.2f}  P95|drift|={float(np.nanpercentile(np.abs(drift_valid), 95)):.2f} mg/dL  (n_aligned={len(drift_valid):,})")
