#!/usr/bin/env python3
"""Assemble the distribution-structure report as a self-contained HTML page.

Figures are inlined as data URIs from runs/.../web (downsampled copies).
Aliases only — nothing identifying reaches this file.
"""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import style as _S

OUT = _S.OUT
WEB = OUT / "web"
DST = OUT / "report.html"

HEAD = """<title>The Shape of Glucose</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root { color-scheme: light;
    --ground:#fbfaf7; --panel:#f3f1ea; --panel-2:#ebe8df; --plot:#fcfcfb;
    --ink:#14181d; --ink-2:#4a5661; --muted:#8a949e; --rule:#e0ddd4;
    --accent:#c94a26; --blue:#3b6ea5; --green:#158f64; --violet:#7c4fe0; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:#0f1216; --panel:#171b21; --panel-2:#1f242b; --plot:#f3f2ee;
    --ink:#e9e6df; --ink-2:#a7b0ba; --muted:#6d7681; --rule:#282e35;
    --accent:#f0764a; --blue:#78a6d8; --green:#3ecf9a; --violet:#a98bf0; } }
  :root[data-theme="dark"] { color-scheme: dark;
    --ground:#0f1216; --panel:#171b21; --panel-2:#1f242b; --plot:#f3f2ee;
    --ink:#e9e6df; --ink-2:#a7b0ba; --muted:#6d7681; --rule:#282e35;
    --accent:#f0764a; --blue:#78a6d8; --green:#3ecf9a; --violet:#a98bf0; }

  body { background:var(--ground); color:var(--ink); margin:0;
    padding:0 22px 110px;
    font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
    font-size:16.5px; line-height:1.62; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1460px; margin:0 auto; }
  .col { max-width:68ch; }
  p, li { color:var(--ink-2); }
  strong { color:var(--ink); font-weight:600; }
  em { font-style:italic; }
  a { color:var(--accent); }

  h1 { font-family:Spectral,Georgia,serif; font-weight:600;
       font-size:clamp(34px,5vw,58px); line-height:1.06; letter-spacing:-.02em;
       margin:76px 0 0; max-width:15ch; text-wrap:balance; color:var(--ink); }
  .lede { font-family:Spectral,Georgia,serif; font-size:clamp(18px,2.1vw,22px);
       line-height:1.5; color:var(--ink-2); max-width:56ch; margin:20px 0 0; }
  h2 { font-family:Spectral,Georgia,serif; font-weight:600;
       font-size:clamp(23px,2.7vw,31px); line-height:1.18; letter-spacing:-.012em;
       margin:0 0 6px; color:var(--ink); max-width:26ch; text-wrap:balance; }
  h3 { font-family:"IBM Plex Sans",sans-serif; font-weight:600; font-size:17px;
       margin:34px 0 6px; color:var(--ink); }

  .eyebrow { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11.5px;
       letter-spacing:.13em; text-transform:uppercase; color:var(--accent);
       margin:0 0 10px; display:flex; align-items:center; gap:10px; }
  .eyebrow::after { content:""; flex:1; height:1px; background:var(--rule); }

  section { margin:74px 0 0; }
  section > p, section > ul, section > ol, section > h3 { max-width:68ch; }

  figure { margin:30px 0 0; }
  figure img { width:100%; height:auto; display:block; border:1px solid var(--rule);
       border-radius:3px; background:var(--plot); }
  figcaption { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12px;
       line-height:1.55; color:var(--muted); margin:10px 0 0; max-width:100ch; }
  figcaption b { color:var(--ink-2); font-weight:500; }

  .read { border-left:2px solid var(--accent); padding:2px 0 2px 18px;
       margin:26px 0 0; max-width:66ch; }
  .read p { margin:0; color:var(--ink); }

  .scroll { overflow-x:auto; margin:26px 0 0;
       border:1px solid var(--rule); border-radius:3px; background:var(--panel); }
  table { border-collapse:collapse; width:100%;
       font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12.5px;
       font-variant-numeric:tabular-nums; }
  th, td { padding:7px 13px; text-align:right; white-space:nowrap;
       border-bottom:1px solid var(--rule); }
  th { color:var(--muted); font-weight:500; font-size:11px; letter-spacing:.06em;
       text-transform:uppercase; text-align:right; position:sticky; top:0;
       background:var(--panel-2); }
  td:first-child, th:first-child { text-align:left; color:var(--ink); }
  tbody tr:last-child td { border-bottom:none; }
  tbody tr:hover td { background:var(--panel-2); }

  .ledger { display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
       border-radius:3px; margin:30px 0 0;
       grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); }
  .cell { background:var(--panel); padding:17px 18px; }
  .cell .k { font-family:"IBM Plex Mono",monospace; font-size:10.5px;
       letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
  .cell .v { font-family:Spectral,Georgia,serif; font-size:29px; line-height:1.1;
       color:var(--ink); margin:7px 0 3px; font-variant-numeric:tabular-nums; }
  .cell .n { font-size:13px; line-height:1.45; color:var(--ink-2); }

  .swatch { display:inline-block; width:9px; height:9px; border-radius:2px;
       margin-right:5px; vertical-align:baseline; }
  code { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:13.5px;
       background:var(--panel-2); padding:1px 5px; border-radius:3px; color:var(--ink); }
  hr { border:0; border-top:1px solid var(--rule); margin:74px 0 0; }
  ul { padding-left:19px; }
  li { margin:7px 0; }
  li::marker { color:var(--muted); }
  .foot { color:var(--muted); font-size:14px; max-width:68ch; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
  @media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style>
"""


def img(name: str) -> str:
    b = (WEB / f"{name}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode()


def build(body: str) -> None:
    def sub(m):
        return img(m.group(1))
    html = HEAD + body
    html = re.sub(r"\{\{FIG:([0-9a-z_]+)\}\}", sub, html)
    DST.write_text(html)
    print(f"wrote {DST}  ({DST.stat().st_size/1e6:.1f} MB)")


BODY = r"""
<div class="wrap">

<h1>The shape of glucose</h1>
<p class="lede">A hundred and fifty-nine people with type 1 diabetes on automated
insulin delivery. What kind of random variable glucose is, what kind of process its
increment is, and which of those properties belong to the person rather than to
the week.</p>

<section>
<p class="eyebrow">What this is</p>
<div class="col">
<p>Every summary we normally compute — time in range, mean, CV — assumes a shape
without ever checking it. This goes underneath that: quantile plots, tail
survival, structure functions, autocorrelations. The question in each case is
distributional, not clinical. Everyone is referred to by alias.</p>
</div>

<h3>Who this is</h3>
<div class="col">
<p><strong>159 people, 17,027 person-days.</strong> Records run a median of 114
days, and CGM wear covers a median <strong>96%</strong> of the elapsed time
(never below 70%), so these are near-continuous records rather than samples.</p>
<p>The spread between them is wide. Time in range has a median of
<strong>67%</strong>, with the middle 80% of people between 49% and 86% and the
full range 14% to 99%. Mean glucose is 158&nbsp;mg/dL (125–193), CV 36% (27–43),
time below 70&nbsp;mg/dL 1.3% (0.1–5.2), time below 54&nbsp;mg/dL 0.13%. Total
daily insulin is 44 units (24–82) and announced carbohydrate 100&nbsp;g/day
(17–225).</p>
<p>What they run matters as much as who they are. <strong>Every person here uses
an automated insulin-delivery system of the Loop family.</strong> Ninety-four let
the system act through temp basals and 65 through automatic boluses; they split
71 / 65 / 23 into heavy, moderate and rare announcers of carbohydrate. The
sensor is identifiable for 153 of them: <strong>87 wear a Libre&nbsp;3 through
twiist, 50 a Dexcom&nbsp;G7 and 14 a Dexcom&nbsp;G6</strong>. That mix is not
incidental — the vendor's processing measurably changes the shape of the trace,
and the instrument section reads differently for a smoothed stream than for a
raw one.</p>

<h3>Two strata, and why</h3>
<p>The cohort is built in two parts, kept separate because they answer different
questions.</p>
<p><strong>Sixty-three people were sampled to match the donor pool</strong>,
ordered by a hash of the donor id so that selection cannot track record volume
or outcome. Measured the same way over the same window against the other
<strong>7,859</strong> Tidepool donors running an automated system, this group is
indistinguishable from the pool: time in range 74.4% against 75.5%, mean glucose
150 against 145&nbsp;mg/dL, CV 32.7% against 34.3%, time below 54&nbsp;mg/dL 0.1%
against 0.2% — <strong>no difference a rank test can see</strong>, every p above
0.13. Any pooled claim in this document about <em>the donor population</em>
rests on these 63.</p>
<p><strong>Ninety-six more were sampled deliberately</strong>, to reach people a
faithful sample barely contains. Someone who announces hardly any carbohydrate
and lets the automation place the boluses is <strong>1.4%</strong> of donors on an
automated system, so a hash-ordered sample of sixty held exactly one. Four
sampling drives fill the gaps: 44 chosen to span the range of time in range, 19
who announce almost nothing, 18 to balance the pumps, and 15 to fill thin cells
of a bolus-frequency grid. None was selected on the outcome it is now measured
by — membership is behavioural and device-based, never glycaemic. Their time in
range lands at a median of <strong>64%</strong> against the matched group's 74%
anyway.</p>
<div class="read"><p><strong>It is the same glucose.</strong> Matched on sensor —
the comparison is otherwise dominated by which device each person wears — every
shape result in this document lands in the same place in both strata. A person
announcing nothing at 57% time in range has a glucose signal with the same
distributional shape as someone announcing 100&nbsp;g a day at 74%. What differs
is where the trace sits and how far it swings, not what kind of random variable
it is. So the figures show both strata together, and the one claim that needs the
pool-matched group alone is labelled where it appears.</p></div>
<div class="read"><p>The pool itself is the limit. Of the
<strong>16,268</strong> donors wearing a CGM for at least 70% of the window,
<strong>7,922</strong> run an automated system, and all of them chose these
devices and chose to donate. Read every number here as describing <em>people who
chose an automated system, donated their data, and kept it running</em>. That is a
selected group, spending more of the day between 70 and 180&nbsp;mg/dL than a
general population with type 1 diabetes does, and equipped differently. The
records carry no age, sex, weight or location, so nothing here is adjusted for
any of them and no claim here is a population estimate.</p></div>
</div>
<figure><img alt="Three panels describing the cohort: time in range across people, mean glucose against CV, and the composition by sensor, dosing strategy and carb announcement" src="{{FIG:00_population}}">
<figcaption><b>00</b> · Left, time in range across the 159 people — the dot strip is one person each, the bar their p10&ndash;p90, with the donor pool's distribution behind. Middle, where each person sits on level and variability. Right, what they run: sensor, how the system delivers, and how much carbohydrate they announce.</figcaption></figure>

<h3>Reading this page</h3>
<p>A few terms recur. <strong>Gaussian</strong> is the bell curve; a
<strong>Laplace</strong> distribution is its sharper-peaked, fatter-tailed
cousin, where big moves are rarer than small ones but far commoner than a bell
curve allows. <strong>Kurtosis</strong> measures that tail weight — zero for a
Gaussian, three for a Laplace, higher still when extremes dominate. The ratio
<strong>SD/MAD</strong> (standard deviation over mean absolute deviation) is a
scale-free fingerprint of shape: 1.253 for a Gaussian, 1.414 for a Laplace,
whatever the spread. A <strong>Q-Q plot</strong> draws a sample's quantiles
against a reference distribution's; a straight line means the sample belongs to
that family.</p>
<p>Two different quantities are easy to confuse and are named apart throughout.
<strong>Sensor noise</strong> is the error in a single reading. <strong>Local
volatility</strong> is an estimate, from the recent trace alone, of how large the
next five-minute change is likely to be. <strong>&lambda;</strong> is the Box-Cox
power that best normalises a distribution (λ = 0 is a log, λ = 1 leaves the data
alone). The <strong>Hurst exponent</strong> describes how the size of a change
grows with the time it spans: 0.5 is a random walk, higher means trends persist,
lower means they reverse. <strong>ICC</strong>, the intraclass correlation, is the
share of a feature's variation that lies between people rather than within one
person over time — near 1 it is a stable trait, near 0 it describes the week.
Percentiles are written p10, p50 (the median), p90.</p>
<p>Where a figure draws one line per person, everyone is drawn in faint grey and
a fixed sample of <strong>twelve representative people</strong> is coloured — the
same twelve in every figure, chosen to span the behaviour groups and the range of
time in range. Colour marks the group: <span class="swatch" style="background:#3b6ea5"></span>non-announcer,
<span class="swatch" style="background:#1baf7a"></span>moderate announcer,
<span class="swatch" style="background:#eb6834"></span>heavy announcer.</p>

<div class="ledger">
  <div class="cell"><div class="k">Box-Cox &lambda;</div><div class="v">&minus;0.05</div>
    <div class="n">Median power that normalises glucose. Range &minus;0.60 to 0.75; a log is the right centre.</div></div>
  <div class="cell"><div class="k">SD / MAD of &Delta;BG</div><div class="v">1.39</div>
    <div class="n">Median, range 1.323–1.530. Laplace is 1.414, Gaussian 1.253; all 159 are above Gaussian.</div></div>
  <div class="cell"><div class="k">Sensor noise per reading</div><div class="v">1.24</div>
    <div class="n">mg/dL, median; range 0.22–2.87. About 10% of the variance of a 5-minute change is measurement noise.</div></div>
  <div class="cell"><div class="k">Trending, 5&ndash;60 min</div><div class="v">0.78</div>
    <div class="n">Hurst exponent; a random walk is 0.5. Over the short run a move tends to continue — true of every person measured.</div></div>
  <div class="cell"><div class="k">Trending, 2&ndash;4 h</div><div class="v">0.32</div>
    <div class="n">The same exponent at long range: strong reversion toward a set point. Two regimes.</div></div>
  <div class="cell"><div class="k">Momentum crosses zero</div><div class="v">45<span style="font-size:17px"> min</span></div>
    <div class="n">Where increment autocorrelation turns negative, then dips to about &minus;0.10.</div></div>
  <div class="cell"><div class="k">Between-day variance</div><div class="v">17.5%</div>
    <div class="n">Median share; range 6&ndash;59%. Most variance is within the day. The shape is not an artefact of pooling days.</div></div>
  <div class="cell"><div class="k">Local volatility, p90/p10</div><div class="v">3.9&times;</div>
    <div class="n">How much the typical size of a 5-minute change varies within one person over time.</div></div>
  <div class="cell"><div class="k">Volatility is forecastable</div><div class="v">R&sup2; 0.17</div>
    <div class="n">Recent volatility predicts the next 30 minutes of it, out of sample. Glucose level manages far less.</div></div>
  <div class="cell"><div class="k">Insulin action from scheduled basal</div><div class="v">47%</div>
    <div class="n">Median; range 23–92%. The share of all BG-lowering that a basal-relative forecast books at zero.</div></div>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Fig 07 · The scale question</p>
<h2>Glucose is not normal, and a log very nearly fixes it</h2>
<div class="col">
<p>A normal Q-Q plot of glucose bends up on the right for all 159 people without
exception: the high tail is much fatter than Gaussian. The interesting part is
what happens when you go looking for the scale on which it <em>is</em> normal.</p>
<p>Fitting a Box-Cox power per person gives a median <strong>&lambda; =
&minus;0.05</strong>, so a plain log is the right centre. Skew drops from about
1.0 raw to about 0.1 logged, and one shared &lambda; produces a Q-Q plot straight
over roughly four standard deviations. But &lambda; does not cluster tightly —
across people it runs from <strong>&minus;0.60 to 0.75</strong>, with the middle
80% between &minus;0.30 and 0.25. A log is the right default and the right
centre, and an approximation to each individual rather than a description of
them.</p>
</div>
<div class="read"><p>Glucose behaves like a log-normal variable far more than
like a normal one, and closely enough that a single transform works for a whole
cohort rather than needing per-person fitting.</p></div>
<figure><img alt="Six panels: normal Q-Q of raw and log glucose, per-person Box-Cox lambda, skew and kurtosis under three transforms, and a shared-transform Q-Q" src="{{FIG:07_transform}}">
<figcaption><b>07</b> · Top left, raw glucose against a normal distribution — every line bends up. Top middle, the same after a log. Top right, the best power transform per person, clustered near zero. Bottom, skew and excess kurtosis under each transform, and a Q-Q using one shared &lambda; for everybody.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 01 · Fig 08 · Marginals and tails</p>
<h2>The two tails differ — and neither is fully observed</h2>
<div class="col">
<p>Plotted as densities, everyone's glucose distribution is a right-skewed hump.
On a log density axis the high tails run close to parallel — similar decay,
different offsets. The low tails do not: they differ between people by orders of
magnitude, and for several they seem to stop rather than decay.</p>
<div class="read"><p><strong>Neither tail is fully observed.</strong> The sensor
reports over a fixed range and clamps outside it, so a reading at the ceiling
means "at least that" and one at the floor means "at most that". As these
records arrive the limits land at <strong>39 and 401&nbsp;mg/dL</strong> — the
values round-trip through mmol/L — and only three records reach past the ceiling
at all. Both tails are interval-censored, and any statistic computed through the
limit describes the hardware rather than the person.</p></div>
<p>The censoring is small in the middle of the distribution and concentrated
exactly where a tail analysis wants to look. Mass piled at the ceiling reaches
<strong>14%</strong> of one person's samples and a median of 0.19%; the floor is
far lighter, a median of 0.00% and at most 1.2%. <strong>113 of the 159 top out
at the ceiling and 80 reach the floor</strong>, and the <strong>62</strong> whose record never goes
below 45 are the ones whose lower cliff really is defence rather than clamping.</p>
<p>What survives the correction: the high tail is close to straight against log
glucose <em>over its observed range</em>, so a power-law reading is defensible
below the limit and unavailable above it. The asymmetry between the tails also
survives, and its structural cause is unchanged — the high side is reached by
ordinary means while the low side is actively defended. What does not survive is
any quantitative claim about the extreme tail beyond the sensor's range. It is
not in the data and cannot be recovered from it.</p>
<p>The increment results in the next section are <strong>not</strong> affected:
only 0.29% of increments touch a limit at the median.</p>
</div>
<figure><img alt="Ridgeline of twelve representative glucose distributions ordered by time in range, with everyone's log density alongside" src="{{FIG:01_bg_marginals}}">
<figcaption><b>01</b> · Each person's glucose distribution, ordered by time in range. Colour marks behaviour group — <span class="swatch" style="background:#3b6ea5"></span>non-announcer, <span class="swatch" style="background:#1baf7a"></span>moderate, <span class="swatch" style="background:#eb6834"></span>heavy announcer. Right panel is the same curves on a log density axis.</figcaption></figure>
<figure><img alt="Survival curves for the upper and lower tails of glucose, with sensor-censored regions marked" src="{{FIG:08_tails}}">
<figcaption><b>08</b> · Upper-tail survival, lower-tail CDF, and the upper tail against log glucose. <b>Solid segments are inside the sensor's reporting range; dotted segments are in the clamped region and describe the instrument, not the person.</b> Read only the solid parts.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 02 · Fig 09 · The increment</p>
<h2>The five-minute increment is Laplace, and startlingly consistently so</h2>
<div class="col">
<p>This is the result I did not expect to be this clean. Plot the density of the
five-minute change on a log axis and you get a sharp peak with two near-straight
flanks. Straight on a log density axis means exponential decay in each direction
— that is a Laplace distribution, not a Gaussian.</p>
<p>It holds up under every check. The Q-Q against a Laplace is straight where the
Q-Q against a normal is a pronounced S; the survival function of the absolute
increment is an almost perfect exponential over four decades; and the shape ratio
— standard deviation over mean absolute deviation, 1.253 for a Gaussian and
1.414 for a Laplace — runs <strong>1.323 to 1.530 across all 159 people</strong>,
median <strong>1.393</strong>. Excess kurtosis over each person's whole record
has a median of <strong>2.30</strong>. Both land on the Laplace values rather
than beside them, and the population <em>straddles</em> them: 29% of people sit
above the shape ratio's Laplace value, 17% above its kurtosis.</p>
<p>So this is not Laplace-<em>ish</em>. At population scale the five-minute
increment is Laplace, and the spread around it is the spread of people, not a
departure from the family. <strong>Every one of the 159 sits above the Gaussian
ratio of 1.253</strong>, without exception.</p>
<h3>It is not a level effect</h3>
<p>An obvious objection: moves are bigger at high glucose, so perhaps the tail is
just a mixture of levels, and differencing <em>log</em> glucose would give Gaussian
increments. It does the opposite. The increment of log glucose has a shape ratio
of <strong>1.42</strong> — still Laplace — and nearly twice the kurtosis
(median 4.4). The person's own best Box-Cox power does no better, and a stronger
transform overshoots badly.</p>
<p>The reason is visible in how spread depends on level. Raw, the increment SD in
the top glucose quintile is <strong>1.45&times;</strong> the bottom; after a log
it is <strong>0.56&times;</strong>. Spread grows with level, but
sub-proportionally — the log over-corrects. And even the right power would not
help, because the heavy tail lives <em>within</em> a level: at any given glucose
some five-minute intervals are calm and some are violent, and no transform of the
level can touch that mixture.</p>
<p>Nor does it thin out with horizon. Central-limit intuition says aggregating to
30 or 120 minutes should push things toward Gaussian; excess kurtosis falls from
2.30 at five minutes to 1.57 at thirty, 0.98 at two hours and
<strong>0.64 at four</strong> — still clear of zero. The increments are too
dependent for the limit to bite.</p>
</div>
<div class="read"><p>If anything in the stack assumes Gaussian glucose
increments — a Kalman filter's process noise, a confidence band, a risk
calculation — it is using the wrong family, and wrong in the direction that
underestimates rare large moves.</p><p>The two directions are not mirror images, and which one wins depends on the
size of the move. Counting how many rises of at least <em>x</em> a person had for
every fall of at least <em>x</em>: at 2&nbsp;mg/dL per five minutes the ratio is
<strong>0.87</strong> — small falls slightly outnumber small rises — and it crosses
1 at a median of <strong>5.5&nbsp;mg/dL</strong>, reaching <strong>1.23</strong> at
10&nbsp;mg/dL and <strong>1.41</strong> at 15. Glucose comes down in many small steps
and goes up in fewer large ones, which is what a controller with a slow actuator
against fast carbohydrate should produce.</p>
</div>
<figure><img alt="Four panels of glucose velocity marginals: log density with a Gaussian reference, rise/fall exceedance ratio, 30-minute increments, and spread against kurtosis" src="{{FIG:02_velocity_marginals}}">
<figcaption><b>02</b> · Velocity densities on a log axis against a Gaussian of the same SD. The near-linear flanks are the Laplace signature. Top right counts exceedances rather than estimating densities — how many rises of at least x there were for every fall of at least x — evaluated on each person's own value grid, with each line stopping where either side has fewer than 40 moves left. Bottom left shows the 30-minute increment, where the rise/fall asymmetry is plain.</figcaption></figure>
<figure><img alt="Six panels testing the distributional family of glucose velocity against normal and Laplace" src="{{FIG:09_velocity_family}}">
<figcaption><b>09</b> · Q-Q against a normal (an S, so heavy-tailed) and against a Laplace (straight). Top right, the survival of the absolute increment against an exponential reference. Bottom left, excess kurtosis versus horizon. Bottom middle, where five-minute raw deltas can land at all: the sensor reports on a discrete lattice — a whole mg/dL for 146 of the 159, while the other 13 arrive by more than one upload path and sit on no single lattice — and no reading falls between its points. Dots are the median share of a person's samples at that value, bars the p10–p90 across people. Bottom right, the SD-over-MAD ratio, clustered just above the Laplace line.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 10 · Dynamics</p>
<h2>Two regimes: trending under an hour, mean-reverting over one</h2>
<div class="col">
<p>The structure function — how the spread of the change grows with horizon —
does not follow a single power law. Between 5 and 60 minutes the scaling exponent
has a median of <strong>0.78</strong>, well above the 0.5 of a random walk:
glucose trends, and a move under way tends to continue. Between 2 and 4 hours it
falls to <strong>0.32</strong>: strong mean reversion, the closed loop and
physiology pulling back toward a set point. <strong>All 159 exceed 0.5 at
5&ndash;60 minutes</strong> and only 5% exceed it at 2&ndash;4 hours — the
two-regime split is universal, not a property of one sample.</p>
<p>The increment autocorrelation tells the same story from the other side. It
starts positive, crosses zero at a median of <strong>45 minutes</strong> —
between 33 and 62 for the middle 80% of people — and then goes <em>negative</em>,
bottoming near &minus;0.10 around an hour before returning to zero.</p>
<p>That negative lobe is a real signature of overshoot: a rise now predicts a
fall in an hour, above and beyond the level. Whether that is the controller
overcorrecting or physiology self-correcting is not something these statistics can
separate. The least-automated people in the panel show it too, which argues
against it being purely a controller artefact, but everyone here runs the same
controller, so the data cannot rule that out.</p>
</div>
<figure><img alt="Six panels on volatility and scaling: volatility-standardised Q-Q, volatility density, absolute-increment autocorrelation, signed autocorrelation, structure function, and Hurst exponents" src="{{FIG:10_volatility}}">
<figcaption><b>10</b> · Top left, increments standardised by trailing two-hour volatility, much closer to normal. Top right, the autocorrelation of |&Delta;BG| — volatility clustering with long memory. Bottom middle, the structure function against random-walk and pure-trend references. Bottom right, the scaling exponent in each regime.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 11 · The instrument</p>
<h2>A five-minute delta is mostly real</h2>
<div class="col">
<p>The difference over &tau; minutes should have variance going to zero as &tau;
does. It does not — the structure function hits a positive intercept, and if the
record is a smooth signal plus independent measurement error, that intercept is
exactly twice the per-reading noise variance. Fitting
<code>Var[&Delta;&tau;] = 2&middot;noise&sup2; + C&middot;&tau;^(2H)</code> over the short lags
recovers the per-reading noise without needing any reference method.</p>
<p>That per-reading noise lands at a median of <strong>1.24 mg/dL</strong>, with
the middle 80% between 0.67 and 1.97 and the whole range 0.22 to 2.87. It
accounts for about <strong>10% of the variance</strong> of a five-minute delta at
the median, and never more than 29% of it. The lag-1 autocorrelation of the
increment sits far above the &minus;0.5 floor that pure noise would produce.</p>
<div class="read"><p>It is a property of the <em>reported stream</em>, not of the
sensor's physics. A vendor that smooths before upload reports lower noise by this
measure, because the intercept can only see roughness that survives to the file
— which is why the cohort's sensor mix belongs beside every number in this
section.</p></div>
<p>The practical reading is that five-minute deltas are worth taking seriously
rather than smoothing away — the thing that makes them look unreliable is
volatility, not noise, and those call for different responses. It is also a
per-person sensor-quality estimate available from the trace alone.</p>
</div>
<figure><img alt="Six panels estimating measurement noise from the structure function intercept" src="{{FIG:11_measurement_noise}}">
<figcaption><b>11</b> · Left, structure functions with the fitted intercept marked at &tau;=0. Middle and right, the implied per-reading sensor noise and its share of five-minute velocity variance. Bottom middle, the increment autocorrelation against the pure-noise floor.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 13 · Pooling</p>
<h2>The shape lives inside single days</h2>
<div class="col">
<p>Months of readings pool days with very different mean levels, and a mixture of
well-behaved days with drifting centres would look skewed and fat-tailed when
combined. That would be a completely different explanation for everything above,
so it is worth ruling out.</p>
<p>It does not hold. Only <strong>17.5%</strong> of glucose variance is
between-day at the median (6% to 59%), and subtracting each day's own mean barely straightens
the Q-Q plot — the right tail is there inside single days.</p>
<p>What days do differ in is level, and higher days are proportionally wider: the
17,027 person-days give a mean-to-SD slope of 0.40. The coefficient of variation
is flat in the level, which is the actual reason CV rather than SD is the stable
summary. Day-to-day memory of the mean is real but weak.</p>
</div>
<figure><img alt="Six panels decomposing glucose variance into within-day and between-day components" src="{{FIG:13_mixture}}">
<figcaption><b>13</b> · Left, the between-day share of variance. Middle and right of the top row, Q-Q plots pooled and after removing each day's mean — barely different. Bottom, every person-day's mean against SD and against CV, and the day-to-day autocorrelation of the daily mean.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 03 · Fig 04 · Phase structure</p>
<h2>The restoring force, and where each system actually sits</h2>
<div class="col">
<p>Plotting glucose against its own velocity gives a phase plane, and the mean
velocity at each glucose level is the restoring force the whole system — loop,
behaviour, physiology together — applies. It crosses zero at the level that
system genuinely defends, which is not the target anyone has configured, and it
slopes downward with a steepness that measures how hard the pull is. Those are
two separable properties, and people differ on both independently.</p>
<p>Volatility also rises steadily with glucose level, so the phase cloud is a
wedge rather than an ellipse — one more reason a fixed-width forecast band is
mis-specified.</p>
</div>
<figure><img alt="A grid of phase-plane panels of glucose against velocity with restoring-force curves" src="{{FIG:03_phase_plane}}">
<figcaption><b>03</b> · Log density of every sample, for the twelve representative people. The green line is mean velocity at each glucose, on its own &plusmn;4 scale because it is a small signal inside a wide cloud.</figcaption></figure>
<figure><img alt="Restoring force curves, volatility against glucose, and set point against stiffness" src="{{FIG:04_restoring_force}}">
<figcaption><b>04</b> · Everyone's restoring-force curve together, the sample in colour, the volatility-versus-level relation, and each person located by where their curve crosses zero against how steeply it falls.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 05 · Fig 06 · Fig 12 · Insulin</p>
<h2>Insulin is slow and smooth; glucose is fast and rough</h2>
<div class="col">
<p>Expressing insulin delivery as BG-lowering per five minutes puts it in the same
units as velocity, and the contrast is stark. Insulin activity is strongly
autocorrelated for <em>hours</em> — a six-hour convolution kernel guarantees it —
where velocity's memory runs out in under one. They are variables on completely
different timescales, and the correlation between them across the whole record
runs only <strong>&minus;0.36 to +0.06</strong>, median &minus;0.16.</p>
<p>Conditioning does show real structure: moving from the lowest to the highest
insulin-activity quintile shifts mean velocity by roughly one velocity SD and
widens the spread by about half again. But this is association, not effect — the
controller doses <em>because</em> glucose is high or rising, so the conditioning
is endogenous, and a few people even come out with the sign reversed.</p>
<p>Subtracting insulin activity off velocity, which leaves everything non-insulin
— glucose production, carbs, exercise — does not make the increment distribution
better behaved. Its Q-Q against a Laplace is <em>worse</em> than raw velocity's.
The non-insulin side is where the awkward shape lives. Mean non-insulin
appearance runs from 36 to 178&nbsp;mg/dL per hour and — as it must over months —
balances mean insulin action to within 0.6% at the median.</p>
<p>One number connects this to the basal-relative accounting question separately
under discussion: the <strong>scheduled</strong> basal stream — the schedule
itself, not temp basals layered on it — supplies a median <strong>47%</strong> of
all BG-lowering delivered, ranging from 23% to 92%, and a basal-relative forecast
values that stream at exactly zero. The distinction from <em>delivered</em> basal
matters because the population splits on how automated insulin arrives: 94 of the
159 run a temp-basal strategy, where every correction Loop makes is delivered as
basal, and 65 an automatic-bolus strategy. Counted by delivery, "basal share" is
0.24 for the bolus group against 0.73 for the temp-basal group — a gap of 0.49
that is purely an artefact of how the insulin is labelled. Counted by schedule the
gap shrinks to 0.07 (0.43 against 0.50), so the scheduled share is much the less
strategy-dependent of the two, though not entirely free of it.</p>
</div>
<figure><img alt="Insulin activity distributions, the basal share of insulin action, and activity against glucose" src="{{FIG:05_insulin_activity}}">
<figcaption><b>05</b> · Insulin activity in absolute terms and net of the basal schedule, and the difference between those two conventions across people.</figcaption></figure>
<figure><img alt="Non-insulin flux distributions and their relationship to glucose level" src="{{FIG:06_non_insulin}}">
<figcaption><b>06</b> · Velocity plus insulin activity — everything insulin did not do. Lower left is the balance check; lower right shows non-insulin flux falling steeply as glucose rises.</figcaption></figure>
<figure><img alt="Velocity conditioned on insulin-activity quintile, autocorrelation comparison, and Laplace Q-Q with and without insulin removed" src="{{FIG:12_insulin_joint}}">
<figcaption><b>12</b> · Velocity by insulin-activity quintile, the mean shift and spread ratio across everyone, and insulin activity's autocorrelation (coloured) against velocity's (grey).</figcaption></figure>
</section>

<hr>

<section>
<p class="eyebrow">Fig 14 · The estimator</p>
<h2>How well local volatility can be estimated</h2>
<div class="col">
<p>Local volatility here means one number per five-minute step: an estimate,
from the recent trace alone, of how large the next change is likely to be. Three
ways of computing it were fitted on the first 30% of each person's record and
scored on the rest: a trailing standard deviation, an exponentially weighted
moving average (EWMA) of recent squared changes, and a fitted GARCH(1,1). All
three treat a record as a set of gap-free runs rather than one series, and all
work in minutes rather than samples.</p>
<p><strong>The EWMA wins, narrowly and usefully.</strong> Out of sample, it
predicts the next 30 minutes of realised volatility with a median R&sup2; of
<strong>0.17</strong> against 0.16 for GARCH and 0.15 for the rolling window, and
it is the best of the three for <strong>99 of the 159</strong>. Its single
parameter is a memory length: a median half-life of <strong>15 minutes</strong>,
with the middle 80% of people between 7 and 33. Glucose volatility is
short-memoried — what happened an hour ago barely bears on the next five minutes'
spread.</p>
<p>Two properties matter more than the ranking. The estimate is <strong>calibrated
across its whole range</strong>: bin the steps by predicted volatility and the
realised size of the change tracks it linearly from the calmest decile to the
wildest. And a confidence band built from it is only correctly sized if the
innovation is treated as Laplace: a nominal 99% band drawn at &plusmn;2.58
standard deviations covers <strong>98.2%</strong>, under-covering for
<strong>all 159 of 159 people</strong>, while the Laplace equivalent at
&plusmn;3.26 covers 99.4%. The Gaussian band misses in the far tail, which is
precisely where a safety margin lives.</p>
<p>One floor is physically required: the fitted variance cannot fall below twice
the measurement-noise variance, the smallest a difference of noisily-measured
values can have. And every estimator here looks only backwards. The same data
scored with a window <em>centred</em> on the change it is scaling appears to lose
most of its excess kurtosis and look Gaussian — a large move inflates its own
denominator — which is the grey strip in the figure, and not a window any
controller could compute.</p>
<figure><img alt="Six panels evaluating three causal volatility estimators" src="{{FIG:14_volatility_estimator}}">
<figcaption><b>14</b> · Each panel is a distribution across the 159 people. Q-Q of increments after conditioning, under each estimator; excess kurtosis before and after; out-of-sample R&sup2;; how volatility is spread within a person; calibration of predicted against realised change size; and far-tail coverage of a Gaussian versus a Laplace band.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 15 · The two decisions</p>
<h2>What recent volatility says about lows, and about highs</h2>
<div class="col">
<p>Both questions are asked out of sample, at matched glucose level and
30-minute trend, so they test what recent volatility adds beyond what level and
trend already say. One row per person, with a bootstrap interval.</p>

<h3>Lows</h3>
<p>Among the 108 people with enough hypoglycaemia to measure, a recent trace in
its most volatile third carries a median <strong>2.0&times;</strong> the rate of
dropping below 70 within 30 minutes, compared with the calmest third at the same
level and trend. Twenty-eight have intervals clearly above 1; <strong>none is
clearly below</strong>.</p>

<h3>Highs</h3>
<p>Restricted to readings above 180, a volatile recent trace is
<strong>3.1&times;</strong> more likely to be followed by a low within two hours
than a calm one, with 55 of 82 sufficiently-measured people clearly above 1 and
one below. Read the other way: <strong>a high that is calm rarely becomes a
low.</strong> That state covers a median <strong>4.1%</strong> of a person's
record.</p>
<p>These are associations in observed data, where dosing had already responded
to the same state. They describe what recent volatility carries information
about; they do not say what would happen if a controller acted on it.</p>
<figure><img alt="Forest plots of hypoglycaemia rate ratios by volatility tercile for lows and highs, plus exposure" src="{{FIG:15_therapy}}">
<figcaption><b>15</b> · Rate ratios with 90% bootstrap intervals, out of sample, one row per person. Green intervals exclude 1 upward; pale rows have too few events and are excluded from the summaries. Right: the share of each record spent above 180, and the part of that spent calm.</figcaption></figure>
</section>

<hr>

<section>
<p class="eyebrow">Fig 22 · How universal</p>
<h2>How much of this is true of everyone</h2>
<div class="col">
<p>Each property above has a population distribution, and the width of that
distribution is itself a finding.</p>
<p><strong>Three hold without exception.</strong> Every one of the 159 sits above
the Gaussian shape ratio — not one person's increments are Gaussian. Every one
has a 5&ndash;60 minute scaling exponent above the random-walk 0.5. And only 5%
exceed 0.5 at 2&ndash;4 hours. Whatever else varies, the two-regime structure
does not.</p>
<p><strong>Three vary enough to matter.</strong> The Box-Cox exponent spans
&minus;0.60 to 0.75, so the transform that normalises one person's glucose is a
rough fit to another's. Sensor noise runs from 0.22 to 2.87&nbsp;mg/dL — a
thirteen-fold range, and a property of the reported stream rather than of
physiology. The between-day variance share runs from 6% to 59%: for some people
almost all variation is within the day, for others a substantial part is which
day it is.</p>
<p>The shape statistics sit in between — tightly enough clustered that the
Laplace reading is a population fact rather than an average of dissimilar people,
wide enough that individuals are visibly distributed around it rather than piled
on it.</p>
</div>
<figure><img alt="Population distributions of eight glucose statistics across the cohort" src="{{FIG:22_scale_check}}">
<figcaption><b>22</b> · Each statistic computed over every person's full record. Black line = median; ticks are individual people. Reference values marked where a distribution has a natural one.</figcaption></figure>
</section>

<hr>

<section>
<p class="eyebrow">Fig 19 · Fig 20 · Fig 21 · Trait or state</p>
<h2>What a single week tells you about a person</h2>
<div class="col">
<p>Everything above describes a population. This asks a different question: which
of these properties belong to the <em>person</em>, and which just describe the
week you happened to measure? The statistic is the intraclass correlation — split
each record into weekly blocks, compute a feature per block, and take the share of
its variance that lies <em>between</em> people rather than within them. Near 1 the
feature is a stable property; near 0 it is weather. <strong>159 people, 2,346
person-weeks.</strong></p>

<div class="read"><p><strong>The method audits itself.</strong> Sensor noise
comes out at <strong>0.29</strong> — a state, not a trait. That is exactly right
and nothing in the setup forced it: sensors are replaced every ten days or so, so
noise belongs to the sensor session rather than the person. Had it landed among
the traits, the whole table would be suspect.</p></div>

<h3>What is stable</h3>
<p>Glucose level and spread are traits, which is unsurprising. Two dynamical
properties join them and are not obvious. <strong>The short-run trending exponent
is a trait (0.72)</strong> — how strongly a person's glucose keeps moving once it
starts is as much a fixed property of them as their mean (0.78). And
<strong>volatility level is a trait (0.80)</strong> while <strong>volatility
spread is a state (0.39)</strong>: how volatile someone runs is personal, how
much that volatility swings week to week is not.</p>

<h3>What is not</h3>
<p>The least personal features measured are <strong>volatility memory
(0.27)</strong>, sensor noise (0.29) and the between-day variance share (0.29) —
how long a person's volatility remembers itself, and how much of their variation
is which day it is, are properties of the week rather than of them. The Box-Cox
exponent lands at 0.36, which says the transform that normalises a person's
glucose is only mildly theirs, consistent with one shared value being a rough fit
for everybody. Tail shape and tail weight sit together in the middle: the Laplace
ratio SD/MAD at 0.52 and increment kurtosis at 0.49 are half personal, half
weekly.</p>

<h3>One cloud, with an axis that tracks dosing strategy</h3>
<p>Restricting to the trait-like features and averaging per person, the first two
principal components carry <strong>63%</strong> of the variation, so people
differ along a small number of axes rather than in every feature independently. A
gap statistic against a uniform null prefers a <em>single</em> cluster, so there
is no clean boundary in this space. But the dominant axis is not arbitrary:
<strong>it tracks dosing strategy.</strong> Split the space in two anyway and the
halves come out 54 automatic-bolus against 5 temp-basal on one side, 89
temp-basal against 10 automatic-bolus on the other — <strong>143 of 158 people
on the strategy-consistent side</strong>. The temp-basal side runs lower and
calmer: mean glucose 153 against 164, time in range 71% against 63%, and about
two-thirds the local volatility. Whether the
strategy produces the calm or calm people choose the strategy, these statistics
cannot say; only that the largest axis of variation in stable glucose traits
lines up with how automated insulin is delivered.</p>

<p class="foot">Robustness: some records span windows and lengths of their own
while most share one. Re-running on the uniform-window subset alone moves no ICC
by more than <strong>0.041</strong> and preserves the ordering almost exactly
(rank correlation 0.99), so the mixture is not what is producing the ranking.</p>
</div>
<figure><img alt="Intraclass correlation for every feature, with between- versus within-person spread" src="{{FIG:19_trait_vs_state}}">
<figcaption><b>19</b> · ICC per feature with 90% bootstrap intervals over people. Green = trait, orange = state. The right panel shows the magnitude ICC hides: a feature can be a near-perfect trait and still barely vary across the population.</figcaption></figure>
<figure><img alt="Weekly tracks per person for one trait and one state" src="{{FIG:20_trait_tracks}}">
<figcaption><b>20</b> · One line per person per week. On the left people hold their rank across the record; on the right the lines cross constantly.</figcaption></figure>
<figure><img alt="Principal components of the trait space, with loadings and cluster test" src="{{FIG:21_trait_space}}">
<figcaption><b>21</b> · Trait-like features only, averaged per person. Scree, positions coloured by dosing strategy, and loadings. The gap statistic prefers a single cluster.</figcaption></figure>

<div class="scroll">
<table>
<thead><tr><th>feature</th><th>ICC</th><th>90% CI</th><th>p10</th><th>median</th><th>p90</th></tr></thead>
<tbody>
__TRAIT_ROWS__
</tbody>
</table>
</div>
<p class="foot" style="margin-top:12px">p10 / median / p90 are across people, of each person's own average — the spread a trait actually has in the population. The circadian amplitude is measured only for those with enough coverage at every hour.</p>
</section>

<hr>

<section>
<p class="eyebrow">Fig 23 · Trait or state, insulin side</p>
<h2>The insulin side is stable in a way the glucose side is not</h2>
<div class="col">
<p>The same weekly-block question, asked of the quantities that need dose, carb
and therapy streams, split three ways: the person's metabolic operating point,
how they run the system, and what their settings say.</p>
<p><strong>Everything here is a trait.</strong> The lowest ICC on the insulin
side — 0.70 for the velocity–insulin correlation — is higher than most of the
glucose dynamics. Insulin action and non-insulin appearance both sit at 0.80,
about level with mean glucose. Total daily dose is 0.94. Carbohydrate announced
per day (0.83) and manual boluses per day (0.86) are stable enough to call
announcing a personal habit rather than a phase.</p>
<p><strong>Settings are near-constants, and that is a finding about behaviour.</strong>
Carb ratio, ISF and scheduled basal each score 0.98, with week-to-week variation
inside a person of a few per cent. Records show steady settings edits — people
nudge — but the edits are small. Whatever moves in a person's glucose from week
to week is not, in the main, their settings moving.</p>
<p>One contrast is worth isolating. The share of a person's total daily dose that
is basal scores <strong>0.95</strong>, but the share of their insulin
<em>action</em> that comes from the <em>scheduled</em> basal stream scores only
<strong>0.74</strong>. The first is stable because it encodes a choice — how the
pump is configured — while the second moves with how much correction insulin the
week actually needed. Configuration is a trait; what the week demanded on top of
it is not.</p>
<p><strong>The automated share of boluses is 0.98</strong> — the most fixed
operational choice in the data, which is what a dosing strategy is. It does not
drift.</p>
</div>
<figure><img alt="Intraclass correlation and within-person variation for insulin-side features" src="{{FIG:23_trait_insulin}}">
<figcaption><b>23</b> · ICC with 90% intervals over people (left) and median week-to-week variation as a share of the person's own level (right). Blue = metabolic operating point, orange = how the system is run, gold = settings.</figcaption></figure>
</section>

<hr>

<section>
<p class="eyebrow">Per person</p>
<h2>The numbers behind the figures</h2>
<div class="scroll">
<table>
<thead><tr>
<th>alias</th><th>TIR</th><th>&lambda;</th><th>SD/MAD</th><th>noise mg/dL</th>
<th>noise&nbsp;%</th><th>H 5–60m</th><th>H 2–4h</th><th>ACF&nbsp;zero</th>
<th>between-day</th><th>basal&nbsp;share</th>
</tr></thead>
<tbody>
__ROWS__
</tbody>
</table>
</div>
<p class="foot" style="margin-top:12px">&lambda; is the Box-Cox power normalising glucose; SD/MAD is 1.253 for a Gaussian and 1.414 for a Laplace; "noise" is per-reading sensor noise in mg/dL and noise&nbsp;% its share of five-minute velocity variance; H is the scaling exponent in each regime (0.5 = random walk); ACF zero is where increment autocorrelation turns negative; basal share is the fraction of insulin action coming from scheduled basal.</p>
</section>

<section>
<p class="eyebrow">What bounds these numbers</p>
<h2>Limits worth carrying</h2>
<div class="col">
<ul>
<li><strong>Both tails are censored, at 39 and 401&nbsp;mg/dL as these records
arrive.</strong> The sensor clamps rather than reporting beyond its range; 113 of
the 159 pile mass at the ceiling, up to 14% of one person's samples. Nothing
about the distribution outside that window is recoverable from CGM.</li>
<li><strong>The lower tail is intervened upon</strong> — by the controller, by
counter-regulation, by rescue carbs. Between clamping and intervention it is not a
free-running distribution and should not be modelled as one.</li>
<li><strong>The instrument is in every shape number.</strong> A vendor that
smooths before upload yields smaller five-minute steps, higher lag-1 correlation
and lower apparent sensor noise, and this cohort is 87 Libre&nbsp;3 to 64 Dexcom.
Within-person comparisons on people who switched sensors mid-window move the SD
of the five-minute step by more than half its between-person spread. Level,
scaling and shape-ratio results survive that; step size, noise, lag-1 and tail
weight are partly instrumental.</li>
<li><strong>Tail statistics depend on the window.</strong> Kurtosis over a week
and over four months are different numbers for the same person; every figure here
uses the whole record unless it says otherwise.</li>
<li><strong>Impossible steps are removed, not kept.</strong> A change faster than
8&nbsp;mg/dL per minute cannot be physiology, so each record is split at those
points rather than interpolated across them — a median of three such steps per
person over the window, up to 182, and none at all for 51 of the 159. Sensor
restarts inflate kurtosis and this is what keeps them out of it.</li>
<li><strong>Gaps are slightly informative.</strong> Coverage is high — a median
3.1% of time inside gaps — and no statistic is ever computed across a gap. But
the last reading before a gap sits 0.14&nbsp;SD above the person's mean, with
both tails over-represented (4.1% against 1.4% below 70, 13.1% against 8.8%
above 250). Sensors drop out from unusual glucose slightly more often than from
ordinary glucose, so the observed extremes are marginally under-sampled — in the
same direction as the censoring at the ceiling: the true tails are at least as
heavy as what is plotted, never lighter.</li>
<li><strong>The insulin model is unknown for most people.</strong> Insulin
activity is the convolution of delivery with a model curve, and the model comes
from the recorded insulin brand. <strong>139 of the 159</strong> carry the
rapid-acting-adult curve, and the record cannot say which of those chose it and
which merely lack a brand; where the true insulin is faster, their activity is
placed later than it really occurred. Level statistics are unaffected;
timing-sensitive ones carry that error.</li>
<li><strong>Only eleven records are individually validated.</strong> Those had
their replay configuration checked against their own field outcomes; the other
148 did not. They are kept distinguishable in every figure and never pooled
silently.</li>
<li><strong>Association, not effect.</strong> Anything conditioned on insulin is
observational data in which dosing already responded to state. None of it
identifies what would happen if a controller acted differently.</li>
</ul>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Sources</p>
<div class="col">
<p>All Loop users, all from the Tidepool Big Data Donation Project, all referred
to by alias. Eligibility is a CGM-wear floor, a closed-loop floor and a
total-daily-dose window, applied before any behavioural or glycaemic
measurement.</p>
<p>Built by <code>analysis/loopeval_analysis/{dists,volatility,traits}.py</code>
and <code>analysis/dist_views/</code>. Every number in the prose is regenerated
by <code>analysis/dist_views/claims.py</code>. The panel reproduces each
record's time in range, time below 54, mean glucose and carbohydrate per day
independently, and total absorbed insulin matches total delivered to within a
per cent.</p>
</div>
</section>

</div>
"""


TRAIT_NAMES = {
    "v_sd": "increment SD",
    "sigma_med": "local volatility, level",
    "sigma_disp": "local volatility, spread",
    "sigma_meas": "sensor noise",
    "bg_mean": "mean glucose",
    "bg_sd": "glucose SD",
    "bg_cv": "glucose CV",
    "bg_iqr": "glucose IQR",
    "bg_skew": "glucose skew",
    "tir": "time in range",
    "t70": "time below 70",
    "t180": "time above 180",
    "hurst_short": "trending, 5\u201360 min",
    "hurst_long": "trending, 2\u20134 h",
    "acf_zero_min": "momentum crosses zero",
    "acf_min": "overshoot depth",
    "sd_over_mad": "SD / MAD of \u0394BG",
    "v_kurtosis": "increment kurtosis",
    "v_skew": "increment skew",
    "boxcox_lambda": "Box-Cox \u03bb",
    "between_day_frac": "between-day variance share",
    "vol_cluster_60m": "volatility memory, 60 min",
    "circadian_amp": "circadian amplitude",
}


def trait_rows() -> str:
    """The ICC table, from trait_icc.csv and the per-person block averages."""
    import pandas as pd
    import numpy as np
    I = pd.read_csv(OUT / "trait_icc.csv")
    F = pd.read_pickle(OUT / "trait_blocks.pkl")
    per = F.groupby("alias").mean(numeric_only=True)
    out = []
    for _, r in I.sort_values("icc", ascending=False).iterrows():
        f = r["feature"]
        s = per[f].dropna() if f in per.columns else pd.Series(dtype=float)
        if len(s):
            p10, p50, p90 = (np.percentile(s, p) for p in (10, 50, 90))

            def g(v):
                # ".3g" printed 7.63e-17 for a Box-Cox median of zero and "7"
                # for 6.97 — scale the decimals instead, and floor tiny values.
                a = abs(v)
                if a < 5e-3:
                    return "0.00"
                if a >= 100:
                    return f"{v:.0f}"
                if a >= 10:
                    return f"{v:.1f}"
                if a >= 1:
                    return f"{v:.2f}"
                return f"{v:.3f}"
            cells = f"<td>{g(p10)}</td><td>{g(p50)}</td><td>{g(p90)}</td>"
        else:
            cells = "<td>\u2013</td><td>\u2013</td><td>\u2013</td>"
        out.append(f"<tr><td>{TRAIT_NAMES.get(f, f)}</td><td>{r['icc']:.2f}</td>"
                   f"<td>{r['lo']:.2f}\u2013{r['hi']:.2f}</td>{cells}</tr>")
    return "\n".join(out)


def rows() -> str:
    import pandas as pd
    import numpy as np
    m = pd.read_csv(OUT / "merged.csv")
    f = lambda v, fmt: ("–" if (v is None or (isinstance(v, float) and np.isnan(v))) else fmt.format(v))
    out = []
    for _, r in m.iterrows():
        out.append(
            "<tr><td>{a}</td><td>{tir}</td><td>{lam}</td><td>{sb}</td><td>{sig}</td>"
            "<td>{ns}</td><td>{hs}</td><td>{hl}</td><td>{zx}</td><td>{bd}</td><td>{bs}</td></tr>".format(
                a=r["alias"], tir=f(r["tir"], "{:.1f}"), lam=f(r["lam"], "{:+.2f}"),
                sb=f(r["sd_over_mad"], "{:.3f}"), sig=f(r["sigma"], "{:.2f}"),
                ns=f(r["noise_share"] * 100 if pd.notna(r["noise_share"]) else np.nan, "{:.0f}%"),
                hs=f(r["H_short"], "{:.2f}"), hl=f(r["H_long"], "{:+.2f}"),
                zx=f(r["zero_x"], "{:.0f} min"), bd=f(r["betw_day"] * 100, "{:.0f}%"),
                bs=f(r["ia_sched_share"] * 100 if pd.notna(r["ia_sched_share"]) else np.nan, "{:.0f}%")))
    return "\n".join(out)


if __name__ == "__main__":
    build(BODY.replace("__ROWS__", rows()).replace("__TRAIT_ROWS__", trait_rows()))
