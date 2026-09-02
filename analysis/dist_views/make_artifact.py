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
<p class="lede">Seventy-three people, sixty-nine with full insulin data. What kind of random variable glucose is, what
kind of process its increment is, and which of those properties belong to the
person rather than to the week.</p>

<section>
<p class="eyebrow">What this is</p>
<div class="col">
<p>Every summary we normally compute — time in range, mean, CV — assumes a shape
without ever checking it. This goes underneath that: quantile plots, tail
survival, structure functions, autocorrelations. The question in each case is
distributional, not clinical.</p>
<p>Everyone is referred to by alias.</p>
</div>

<h3>Who this is</h3>
<div class="col">
<p><strong>73 people, 8,095 person-days.</strong> Sixty donors over one common
window of up to 113 days, eleven more over 61 days inside it, and two Nightscout
sites over a year. Sensor coverage is a median of 96% of the elapsed time, so
these are near-continuous records rather than samples.</p>
<p>The spread between them is wide. Time in range has a median of
<strong>74%</strong>, with the middle 80% of people between 53% and 89% and the
full range 44% to 98%. Mean glucose is 152 mg/dL (111–184), CV 33% (26–42), time
below 70 mg/dL 1.4% (0.2–6.2), time below 54 mg/dL 0.15%. Total daily insulin is
42 units (24–68) and announced carbohydrate 126 g/day (36–236).</p>
<p>What they run matters as much as who they are. <strong>Every person here uses
an automated insulin-delivery system of the Loop family.</strong> Of the 69 whose
insulin records were exported alongside their glucose, 42 let the system act
through temp basals and 27 through automatic boluses, and they split 35 / 27 / 7
into heavy, moderate and rare announcers of carbohydrate. Of the 60 donors whose
uploads name a sensor, <strong>38 wear a Libre 3 through twiist, 13 a Dexcom G7
and 3 a Dexcom G6</strong>. That mix is not incidental: the vendor's
processing measurably changes the shape of the trace, and view 11 reads
differently for a smoothed stream than for a raw one.</p>
<p>Within the pool they came from, they are ordinary. Measured the same way over
the same 30 days, against all <strong>8,026</strong> Tidepool donors running an
automated system: time in range 74.6% against 74.7%, mean glucose 151 against
147&nbsp;mg/dL, CV 33.9% against 34.3%, time below 54 both 0.1% — no difference
that a rank test can see (every p above 0.6). The equipment matches too: 70 / 24
/ 6% Libre&nbsp;3, Dexcom&nbsp;G7, Dexcom&nbsp;G6 here against 72 / 23 / 4% in
that pool. So these 73 are not a lucky corner of the donors; they are the middle
of them.</p>
<div class="read"><p>The pool itself is the limit. Of 18,601 donors with enough
CGM in that window, 43% run an automated system, and all of them are people who
chose these devices and chose to donate. So: read every number here as describing
<em>people who chose an automated system, donated their data, and kept it
running</em>. That is a
selected group — better controlled than a general population with type 1
diabetes, and equipped differently. Nothing in the export says how old anyone is,
what sex they are, how long they have had diabetes, what they weigh or where they
live, so none of it can be adjusted for, and no claim here should be read as a
population estimate.</p></div>
</div>
<figure><img alt="Three panels describing the cohort: time in range across people, mean glucose against CV, and the composition by sensor, dosing strategy and carb announcement" src="{{FIG:00_population}}">
<figcaption><b>00</b> · Left, time in range across the 73 people — the dot strip is one person each, the bar their p10&ndash;p90. Middle, where each person sits on level and variability. Right, what they run: sensor, how the system delivers, and how much carbohydrate they announce.</figcaption></figure>

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
<p><strong>σ</strong> is used for two different things and each is named where it
appears: the <em>sensor noise</em> in a single reading, and the <em>local
volatility</em> of the recent trace — an estimate of how large the next
five-minute change is likely to be. <strong>&lambda;</strong> is the Box-Cox
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
  <div class="cell"><div class="k">Box-Cox &lambda;</div><div class="v">&minus;0.10</div>
    <div class="n">Median power that normalises glucose, over 73 people. Range &minus;0.60 to 0.70; a log is the right centre.</div></div>
  <div class="cell"><div class="k">SD / MAD of &Delta;BG</div><div class="v">1.40</div>
    <div class="n">Median over 73 people, range 1.326–1.498. Laplace is 1.414, Gaussian 1.253; everyone is above Gaussian.</div></div>
  <div class="cell"><div class="k">Sensor noise per reading</div><div class="v">1.27</div>
    <div class="n">mg/dL, median over 73 people; range 0.13–2.45. Only about 9% of the variance of a 5-minute change is measurement noise.</div></div>
  <div class="cell"><div class="k">Trending, 5&ndash;60 min</div><div class="v">0.77</div>
    <div class="n">Hurst exponent; a random walk is 0.5. Over the short run a move tends to continue — true of every person measured.</div></div>
  <div class="cell"><div class="k">Trending, 2&ndash;4 h</div><div class="v">0.30</div>
    <div class="n">The same exponent at long range: strong reversion toward a set point. Two regimes.</div></div>
  <div class="cell"><div class="k">Momentum crosses zero</div><div class="v">40<span style="font-size:17px"> min</span></div>
    <div class="n">Where increment autocorrelation turns negative, then dips to about &minus;0.09.</div></div>
  <div class="cell"><div class="k">Between-day variance</div><div class="v">16%</div>
    <div class="n">Median share; range 6&ndash;40%. Most variance is within the day. The shape is not an artefact of pooling days.</div></div>
  <div class="cell"><div class="k">Local volatility, p90/p10</div><div class="v">3.9&times;</div>
    <div class="n">How much the typical size of a 5-minute change varies within one person over time.</div></div>
  <div class="cell"><div class="k">Volatility is forecastable</div><div class="v">R&sup2; 0.18</div>
    <div class="n">Recent volatility predicts the next 30 minutes of it, out of sample. Glucose level manages 0.03.</div></div>
  <div class="cell"><div class="k">Insulin action from scheduled basal</div><div class="v">48%</div>
    <div class="n">Median of 69; range 3–81%. The share of all BG-lowering that a basal-relative forecast books at zero.</div></div>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Fig 07 · The scale question</p>
<h2>Glucose is not normal, and a log very nearly fixes it</h2>
<div class="col">
<p>A normal Q-Q plot of glucose bends up on the right for all 73 people
without exception. The high tail is much fatter than Gaussian. That is not news
in itself, but the interesting part is what happens when you go looking for the
scale on which it <em>is</em> normal.</p>
<p>Fitting a Box-Cox power per person gives a median <strong>&lambda; =
&minus;0.10</strong> over 73 people, so a plain log is the right centre. Skew drops from about 1.0 raw to about 0.1 logged, and one shared &lambda; produces a Q-Q plot
straight over roughly four standard deviations.</p>
<p>How well one shared exponent serves everybody depends on how tightly
&lambda; clusters, and it does not cluster tightly: across 73 people it runs from
<strong>&minus;0.60 to 0.70</strong>. A log is the right default and the right
centre, but it is an approximation to each individual rather than a description of
them.</p>
</div>
<div class="read"><p>Glucose behaves like a log-normal variable far more than
like a normal one, and closely enough that a single transform works for a whole
cohort rather than needing per-person fitting.</p></div>
<figure><img alt="Six panels: normal Q-Q of raw and log glucose, per-person Box-Cox lambda, skew and kurtosis under three transforms, and a shared-transform Q-Q" src="{{FIG:07_transform}}">
<figcaption><b>07</b> · Top left, raw glucose against a normal distribution — every line bends up. Top middle, the same after a log. Top right, the best power transform per person, tightly clustered near zero. Bottom, skew and excess kurtosis under each transform, and a Q-Q using one shared &lambda; for everybody.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 01 · Fig 08 · Marginals and tails</p>
<h2>The two tails differ — and neither is fully observed</h2>
<div class="col">
<p>Plotted as densities, everyone's glucose distribution is a right-skewed hump.
On a log density axis the high tails run close to parallel — similar decay,
different offsets. The low tails do not: they differ between people by orders of
magnitude, and for several they seem to stop rather than decay.</p>
<div class="read"><p><strong>Neither tail is fully observed.</strong> CGM reports
only 40–400 mg/dL and clamps outside that range, so a reading of 400 means "at
least 400" and one of 40 means "at most 40". Both tails are interval-censored, and
any statistic computed through the limit describes the hardware rather than the
person.</p></div>
<p>The censoring is small in the middle of the distribution and concentrated
exactly where a tail analysis wants to look. Mass piled at the ceiling reaches
<strong>3.3%</strong> of one person's samples and exceeds 0.3% for 21 of the
73; the floor is far lighter, a median of 0.01% against the ceiling's 0.02%.
Forty-nine of the 73 reach the floor at all and 44 top out at the ceiling — and the
18 whose record never goes below 45 are the ones whose lower cliff really is
defence rather than clamping. The limits are not the same for everyone: three
records run past 400, one to 500.</p>
<p>What survives the correction: the high tail is close to straight against log
glucose <em>over its observed range</em>, so a power-law reading is defensible
below the limit and unavailable above it. The asymmetry between the tails also
survives, and its structural cause is unchanged — the high side is reached by
ordinary means while the low side is actively defended. What does not survive is
any quantitative claim about the extreme tail beyond the sensor's range. It is
not in the data and cannot be recovered from it.</p>
<p>The increment results in the next section are <strong>not</strong> affected.
Only 0.10% of increments touch a censoring limit at the median, 3.1% at worst, and
excluding them moves the shape ratio from 1.400 to 1.400 and excess kurtosis from
3.00 to 2.99.</p>
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
Q-Q against a normal is a pronounced S. The survival function of the absolute
increment is an almost perfect exponential over four decades. And the shape ratio
— standard deviation over mean absolute deviation, which is 1.253 for a Gaussian
and 1.414 for a Laplace — comes out between <strong>1.326 and 1.498 across all 73
people</strong>, median 1.40.</p>
<p>Across 73 people the ratio runs <strong>1.326 to 1.498</strong> with a median
of <strong>1.403</strong>, and excess kurtosis, over each person's whole record, has a median of <strong>3.05</strong>.
Both land on the Laplace values — 1.414 and 3.0 — rather than beside them: 41% of
people sit above the shape ratio's Laplace value and 51% above its kurtosis. The
population straddles the distribution rather than clearing it.</p>
<p>So this is not Laplace-<em>ish</em>. At population scale the five-minute
increment is Laplace, and the spread around it is the spread of people, not a
departure from the family.</p>
<h3>It is not a level effect</h3>
<p>An obvious objection: moves are bigger at high glucose, so perhaps the tail is
just a mixture of levels, and differencing <em>log</em> glucose would give Gaussian
increments. It does the opposite. The increment of log glucose has a shape ratio
of <strong>1.43</strong> — still Laplace — and two-thirds more kurtosis
(median 5.0). The person's own best Box-Cox power does no better, and a stronger
transform overshoots badly. All 69 stay above Gaussian under
every transform.</p>
<p>The reason is visible in how spread depends on level. Raw, the increment SD in
the top glucose quintile is 1.45× the bottom; after a log it is 0.59×. Spread
grows with level, but sub-proportionally — the log over-corrects. And even the
right power would not help, because the heavy tail lives <em>within</em> a level:
at any given glucose some five-minute intervals are calm and some are violent, and
no transform of the level can touch that mixture.</p>
<p>The part that was never in doubt is the part that matters most: <strong>every
one of the 73 sits above the Gaussian ratio of 1.253</strong>, without exception.</p>
<p>Nor does it thin out with horizon. Central-limit intuition says aggregating to
30 or 120 minutes should push things toward Gaussian; the excess kurtosis at four
hours is still around 1 for the median person, well clear of zero. The increments are too
dependent for the limit to bite.</p>
</div>
<div class="read"><p>If anything in the stack assumes Gaussian glucose
increments — a Kalman filter's process noise, a confidence band, a risk
calculation — it is using the wrong family, and wrong in the direction that
underestimates rare large moves.</p><p>The two directions are not mirror images, and which one wins depends on the
size of the move. Counting how many rises of at least <em>x</em> a person had for
every fall of at least <em>x</em>: at 2&nbsp;mg/dL per five minutes the ratio is
<strong>0.88</strong> — small falls slightly outnumber small rises — and it crosses
1 at a median of <strong>5&nbsp;mg/dL</strong>, reaching <strong>1.22</strong> at
10&nbsp;mg/dL and <strong>1.39</strong> at 15. Glucose comes down in many small steps
and goes up in fewer large ones, which is what a controller with a slow actuator
against fast carbohydrate should produce.</p>
</div>
<figure><img alt="Four panels of glucose velocity marginals: log density with a Gaussian reference, rise-to-fall density ratio, 30-minute increments, and spread against kurtosis" src="{{FIG:02_velocity_marginals}}">
<figcaption><b>02</b> · Velocity densities on a log axis against a Gaussian of the same SD. The near-linear flanks are the Laplace signature. Top right counts exceedances rather than estimating densities — how many rises of at least x there were for every fall of at least x — evaluated on each person's own value grid, with each line stopping where either side has fewer than 40 moves left. Bottom left shows the 30-minute increment, where the rise/fall asymmetry is plain.</figcaption></figure>
<figure><img alt="Six panels testing the distributional family of glucose velocity against normal and Laplace" src="{{FIG:09_velocity_family}}">
<figcaption><b>09</b> · Q-Q against a normal (an S, so heavy-tailed) and against a Laplace (straight). Top right, the survival of the absolute increment against an exponential reference. Bottom left, excess kurtosis versus horizon. Bottom middle, where five-minute raw deltas can land at all: a sensor reports on a discrete value grid — whole mg/dL for 66 people, 0.1 mmol/L (1.8 mg/dL) for three — and no reading falls between its points. Dots are the median share of a person's samples at that value, bars the p10–p90 across people. Bottom right, the SD-over-MAD ratio, clustered just above the Laplace line.</figcaption></figure>
</section>


<section>
<p class="eyebrow">Fig 10 · Dynamics</p>
<h2>Two regimes: trending under an hour, mean-reverting over one</h2>
<div class="col">
<p>The structure function — how the spread of the change grows with horizon —
does not follow a single power law. Between 5 and 60 minutes the scaling exponent
has a median of <strong>0.77</strong> over 73 people, well above the 0.5 of a random
walk:
glucose trends, and a move under way tends to continue. Between 2 and 4 hours it
falls to <strong>0.30</strong> (median over 73): strong mean reversion, the closed loop and physiology pulling back
toward a set point. Only 3% of people exceed 0.5 at that range, while
<strong>100% exceed it at 5&ndash;60 minutes</strong> — the two-regime split is
universal, not a property of the original sample.</p>
<p>The increment autocorrelation tells the same story from the other side. It starts positive (median 0.63 at one step), crosses zero at a median of
<strong>40 minutes</strong> — between 30 and 55 for the middle 80% of people —
and then goes <em>negative</em>, bottoming near &minus;0.12 around an hour before
returning to zero.</p>
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
<p>That per-reading noise lands at a median of <strong>1.27 mg/dL</strong>
across 73 people, with the middle 80% between 0.57 and 1.94 and the whole range
0.13 to 2.45. It accounts for about <strong>9% of the variance</strong> of a
five-minute delta at the median, and never more than a quarter of it. The lag-1
autocorrelation of the increment sits far above the &minus;0.5 floor that pure
noise would produce.</p>
<p>The practical reading is that five-minute deltas are worth taking seriously
rather than smoothing away — the thing that makes them look unreliable is
volatility, not noise, and those call for different responses. It is also a
per-person sensor-quality estimate available from the trace alone, which may be
useful on its own.</p>
</div>
<figure><img alt="Six panels estimating measurement noise from the structure function intercept" src="{{FIG:11_measurement_noise}}">
<figcaption><b>11</b> · Left, structure functions with the fitted intercept marked at &tau;=0. Middle and right, the implied per-reading sensor noise and its share of five-minute velocity variance. Bottom middle, the increment autocorrelation against the pure-noise floor.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 13 · Pooling</p>
<h2>The shape lives inside single days</h2>
<div class="col">
<p>Two months of readings pool days with very different mean levels, and a
mixture of well-behaved days with drifting centres would look skewed and
fat-tailed when combined. That would be a completely different explanation for
everything above, so it is worth ruling out.</p>
<p>It does not hold. Only <strong>14%</strong> of glucose variance is between-day
at the median (6% to 32%), and subtracting each day's own mean barely straightens
the Q-Q plot — the right tail is there inside single days.</p>
<p>What days do differ in is level, and higher days are proportionally wider: the 7,528 person-days give a mean-to-SD slope of 0.40 with r = 0.73. The coefficient
of variation is flat in the level at a median of 29%, which is the actual reason
CV rather than SD is the stable summary. Day-to-day memory of the mean is real
but weak, around 0.2 to 0.4 at one day.</p>
</div>
<figure><img alt="Six panels decomposing glucose variance into within-day and between-day components" src="{{FIG:13_mixture}}">
<figcaption><b>13</b> · Left, the between-day share of variance. Middle and right of the top row, Q-Q plots pooled and after removing each day's mean — barely different. Bottom, 7,528 person-days of mean against SD and against CV, and the day-to-day autocorrelation of the daily mean.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 03 · Fig 04 · Phase structure</p>
<h2>The restoring force, and where each system actually sits</h2>
<div class="col">
<p>Plotting glucose against its own velocity gives a phase plane, and the mean
velocity at each glucose level is the restoring force the whole system — loop,
behaviour, physiology together — applies. It crosses zero at the level that
system genuinely defends, which is not the target anyone has configured, and it
slopes downward with a steepness that measures how hard the pull is.</p>
<p>Those are two separable properties, and people differ on both independently.
Volatility also rises steadily with glucose level, so the phase cloud is a wedge
rather than an ellipse — one more reason a fixed-width forecast band is
mis-specified.</p>
</div>
<figure><img alt="Fifteen phase-plane panels of glucose against velocity with restoring-force curves" src="{{FIG:03_phase_plane}}">
<figcaption><b>03</b> · Log density of every sample. The green line is mean velocity at each glucose, on its own &plusmn;4 scale because it is a small signal inside a wide cloud.</figcaption></figure>
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
different timescales, and the correlation between them across the whole record is only &minus;0.30 to +0.06.</p>
<p>Conditioning does show real structure: moving from the lowest to the highest
insulin-activity quintile shifts mean velocity by roughly one velocity SD and
widens the spread by about half again. But this is association, not effect — the
controller doses <em>because</em> glucose is high or rising, so the conditioning
is endogenous, and two people even come out with the sign reversed.</p>
<p>Subtracting insulin activity off velocity, which leaves everything non-insulin
— glucose production, carbs, exercise — does not make the increment distribution
better behaved. Its Q-Q against a Laplace is <em>worse</em> than raw velocity's.
The non-insulin side is where the awkward shape lives.</p>
<p>One number connects this to the basal-relative accounting question separately
under discussion: the <strong>scheduled</strong> basal stream — the schedule
itself, not temp basals layered on it — supplies a median <strong>48%</strong> of
all BG-lowering delivered, ranging from 3% to 81% across 69 people, and a
basal-relative forecast values that stream at exactly zero. The distinction from
<em>delivered</em> basal matters because the population splits on how automated
insulin arrives: <strong>about 60% of long-record Loop users run a temp-basal
strategy</strong>, where every correction Loop makes is delivered as basal, and
40% an automatic-bolus strategy. Counted by delivery, "basal share" is 0.26 for
the bolus group and 0.71 for the temp-basal group — a gap of 0.45 that is purely
an artefact of how the insulin is labelled. Counted by schedule the gap shrinks
to 0.08 (0.43 against 0.51), so the scheduled share is much the less
strategy-dependent of the two, though not entirely free of it.</p>
<p>Mean non-insulin appearance runs from 36 to 178 mg/dL per hour, and — as it
must over months — it balances mean insulin action to within 0.3% at the median
and 4.3% at worst across all 69.</p>
</div>
<figure><img alt="Insulin activity distributions, the basal share of insulin action, and activity against glucose" src="{{FIG:05_insulin_activity}}">
<figcaption><b>05</b> · Insulin activity in absolute terms and net of the basal schedule. The bar chart is the difference between those two conventions, per person.</figcaption></figure>
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
predicts the next 30 minutes of realised volatility with a median R&sup2; of <strong>0.18</strong> against 0.17 for GARCH and 0.16 for the rolling window, and it is the best of the three for 44 of 69 people. Its single parameter is a memory
length: a median half-life of <strong>16 minutes</strong>, with the middle 80% of people between 8 and 31. Glucose volatility is short-memoried — what happened
an hour ago barely bears on the next five minutes' spread.</p>
<p>Two properties matter more than the ranking. The estimate is <strong>calibrated
across its whole range</strong>: bin the steps by predicted volatility and the
realised size of the change tracks it linearly from the calmest decile to the
wildest. And a confidence band built from it is only correctly sized if the
innovation is treated as Laplace: a nominal 99% band drawn at &plusmn;2.58
standard deviations covers <strong>98.2%</strong>, under-covering for <strong>all 69 of 69 people</strong>, while the Laplace equivalent at &plusmn;3.26 covers
99.4%. The Gaussian band misses in the far tail, which is precisely where a safety
margin lives.</p>
<p>One floor is physically required: the fitted variance cannot fall below twice
the measurement-noise variance, the smallest a difference of noisily-measured
values can have. And every estimator here looks only backwards. The same data
scored with a window <em>centred</em> on the change it is scaling appears to lose
93% of its excess kurtosis and look Gaussian — a large move inflates its own
denominator — which is the grey strip in the figure, and not a window any
controller could compute.</p>
<figure><img alt="Six panels evaluating three causal volatility estimators" src="{{FIG:14_volatility_estimator}}">
<figcaption><b>14</b> · Each panel is a distribution across 69 people. Q-Q of increments after conditioning, under each estimator; excess kurtosis before and after; out-of-sample R&sup2;; how volatility is spread within a person; calibration of predicted against realised change size; and far-tail coverage of a Gaussian versus a Laplace band.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig 15 · The two decisions</p>
<h2>What recent volatility says about lows, and about highs</h2>
<div class="col">
<p>Both questions are asked out of sample, at matched glucose level and
30-minute trend, so they test what recent volatility adds beyond what level and
trend already say. One row per person, with a bootstrap interval.</p>

<h3>Lows</h3>
<p>Among the 55 people with enough hypoglycaemia to measure, a recent trace in its
most volatile third carries a median <strong>2.2&times;</strong> the rate of
dropping below 70 within 30 minutes, compared with the calmest third at the same
level and trend. Fifteen of the 55 have intervals clearly above 1; <strong>none
is clearly below</strong>.</p>

<h3>Highs</h3>
<p>Restricted to readings above 180, a volatile recent trace is <strong>2.4&times;</strong>
more likely to be followed by a low within two hours than a calm one, with 24 of
37 sufficiently-measured people clearly above 1 and none below. Read the other
way: <strong>a high that is calm rarely becomes a low.</strong> That state covers a
median <strong>3.5%</strong> of a person's record.</p>
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
distribution is itself a finding. Some are near-constants across people; others
are personal enough that a cohort median describes nobody in particular.</p>
<p><strong>Three hold without exception.</strong> Every one of the 73 sits above
the Gaussian shape ratio — not one person's increments are Gaussian. Every one has
a 5&ndash;60 minute scaling exponent above the random-walk 0.5, so short-run
trending is universal. And only <strong>3%</strong> exceed 0.5 at 2&ndash;4 hours,
so the reversal to mean-reversion at longer range is near-universal too. Whatever
else varies, the two-regime structure does not.</p>
<p><strong>Three vary enough to matter.</strong> The Box-Cox exponent spans
&minus;0.60 to 0.70, so the transform that normalises one person's glucose is a
rough fit to another's. Sensor noise runs from 0.13 to 2.45 mg/dL — an
eighteen-fold range, and a property of hardware rather than physiology. The
between-day variance share runs from 6% to 40%: for some people almost all
variation is within the day, for others a substantial part is which day it is.</p>
<p>The shape statistics sit in between. The increment ratio and its kurtosis are
tightly enough clustered that the Laplace reading is a population fact rather than
an average of dissimilar people, but wide enough that individuals are visibly
distributed around it rather than piled on it.</p>
</div>
<figure><img alt="Population distributions of eight glucose statistics across 73 people" src="{{FIG:22_scale_check}}">
<figcaption><b>22</b> · Each statistic computed over every person's full record. Black line = median; ticks are individual people. Reference values marked where a distribution has a natural one.</figcaption></figure>
</section>

<hr>

<section>
<p class="eyebrow">Fig 19 · Fig 20 · Fig 21 · Trait or state</p>
<h2>What a single week tells you about a person</h2>
<div class="col">
<p>Everything above describes a population. This asks a different question: which
of these properties belong to the <em>person</em>, and which just describe the
week you happened to measure?</p>
<p>The cohort was widened for it — <strong>73 people, 1,113 person-weeks</strong>.
Beyond the eleven fully-exported donors and two Nightscout sites, sixty more were
pulled directly from the donor pool, glucose only. Selection was Loop users with at
least 105 days inside one fixed window, ordered by a hash of the donor id rather
than by record volume: ordering by volume selects multi-device duplicate
uploaders, whose records carry the same reading several times over.</p>
<p>The statistic is the intraclass correlation — split each record into weekly
blocks, compute a feature per block, and take the share of its variance that lies
<em>between</em> people rather than within them. Near 1 the feature is a stable
property; near 0 it is weather.</p>

<div class="read"><p><strong>The method audits itself.</strong> Sensor noise
comes out at <strong>0.32</strong> — a state, not a trait. That is exactly right
and nothing in the setup forced it: sensors are replaced every ten days or so, so
noise belongs to the sensor session rather than the person. Had it landed among
the traits, the whole table would be suspect.</p></div>

<h3>What is stable</h3>
<p>Glucose level and spread are traits, which is unsurprising. Two dynamical
properties join them and are not obvious. <strong>The short-run trending exponent
is a trait (0.70)</strong> — how strongly a person's glucose keeps moving once it
starts is as much a fixed property of them as their mean. And
<strong>volatility level is a trait (0.79)</strong> while <strong>volatility
spread is a state (0.38)</strong>: how volatile someone runs is personal, how
much that volatility swings week to week is not.</p>

<h3>What is not</h3>
<p>Tail weight separates from tail shape. The Laplace ratio SD/MAD is trait-ish
(0.51), but <strong>increment kurtosis is the least personal feature measured
(0.12)</strong> — the extremeness of a person's worst moves is a property of the
week. So is the between-day variance share (0.22), and so is volatility memory
(0.29). The Box-Cox exponent lands at 0.36, which says the transform that
normalises a person's glucose is only mildly theirs — consistent with the earlier
finding that one shared value is a rough fit for everybody.</p>

<h3>Two clouds, and what separates them</h3>
<p>Restricting to the trait-like features and averaging per person, the first two
principal components carry <strong>67%</strong> of the variation, so people
differ along a small number of axes rather than in every feature independently.
A gap statistic against a uniform null cannot decide between one cluster and two
(0.86 against 0.87 — inside the noise of the test), so there is no clean boundary
in this space. But the best two-way split is not arbitrary: <strong>it is dosing
strategy</strong>. Of the 69 people with full data, one cloud holds 35 temp-basal
users and 4 automatic-bolus users; the other holds 23 automatic-bolus users and 7
temp-basal. The temp-basal cloud runs lower and calmer — mean glucose 136 against
165, time in range 81% against 64%, half the volatility. Whether the strategy
produces the calm or calm people choose the strategy, these statistics cannot
say; only that the largest axis of variation in stable glucose traits lines up
with how automated insulin is delivered.</p>

<p class="foot">Robustness: fourteen of the datasets span windows and lengths of their own while the fifty-nine others share one. Re-running on the uniform-window subset alone moves no ICC by more than <strong>0.041</strong> and preserves the ordering almost exactly (rank correlation 0.99), so the mixture is not what is producing the ranking.</p>
</div>
<figure><img alt="Intraclass correlation for every feature, with between- versus within-person spread" src="{{FIG:19_trait_vs_state}}">
<figcaption><b>19</b> · ICC per feature with 90% bootstrap intervals over people. Green = trait, orange = state. The right panel shows the magnitude ICC hides: a feature can be a near-perfect trait and still barely vary across the population.</figcaption></figure>
<figure><img alt="Weekly tracks per person for one trait and one state" src="{{FIG:20_trait_tracks}}">
<figcaption><b>20</b> · One line per person per week. On the left people hold their rank across the record; on the right the lines cross constantly.</figcaption></figure>
<figure><img alt="Principal components of the trait space, with loadings and cluster test" src="{{FIG:21_trait_space}}">
<figcaption><b>21</b> · Trait-like features only, averaged per person. Scree, positions, and loadings. The gap statistic prefers a single cluster.</figcaption></figure>

<div class="scroll">
<table>
<thead><tr><th>feature</th><th>ICC</th><th>90% CI</th><th>p10</th><th>median</th><th>p90</th></tr></thead>
<tbody>
<tr><td>v_sd</td><td>0.83</td><td>0.78–0.87</td><td>4.42</td><td>5.84</td><td>8.64</td></tr>
<tr><td>bg_mean</td><td>0.82</td><td>0.77–0.85</td><td>112</td><td>150</td><td>185</td></tr>
<tr><td>t180</td><td>0.80</td><td>0.75–0.84</td><td>3.6</td><td>24.7</td><td>46.3</td></tr>
<tr><td>bg_sd</td><td>0.79</td><td>0.73–0.83</td><td>31.3</td><td>47.6</td><td>72</td></tr>
<tr><td>sigma_med</td><td>0.79</td><td>0.73–0.84</td><td>3.52</td><td>4.64</td><td>7.16</td></tr>
<tr><td>tir</td><td>0.79</td><td>0.74–0.82</td><td>52.5</td><td>74.5</td><td>91.1</td></tr>
<tr><td>bg_iqr</td><td>0.78</td><td>0.72–0.82</td><td>37.3</td><td>60.9</td><td>102</td></tr>
<tr><td>hurst_short</td><td>0.71</td><td>0.62–0.77</td><td>0.689</td><td>0.771</td><td>0.813</td></tr>
<tr><td>bg_cv</td><td>0.68</td><td>0.60–0.73</td><td>25</td><td>32.4</td><td>40.8</td></tr>
<tr><td>t70</td><td>0.65</td><td>0.56–0.70</td><td>0.234</td><td>1.46</td><td>6.04</td></tr>
<tr><td>acf_zero_min</td><td>0.53</td><td>0.36–0.62</td><td>32.8</td><td>41.9</td><td>51.1</td></tr>
<tr><td>sd_over_mad</td><td>0.51</td><td>0.45–0.57</td><td>1.35</td><td>1.39</td><td>1.44</td></tr>
<tr><td>acf_min</td><td>0.50</td><td>0.41–0.57</td><td>-0.219</td><td>-0.147</td><td>-0.0958</td></tr>
<tr><td>hurst_long</td><td>0.47</td><td>0.38–0.55</td><td>0.1</td><td>0.288</td><td>0.415</td></tr>
<tr><td>circadian_amp</td><td>0.40</td><td>0.32–0.47</td><td>0.0731</td><td>0.123</td><td>0.198</td></tr>
<tr><td>sigma_disp</td><td>0.39</td><td>0.31–0.45</td><td>3.05</td><td>3.43</td><td>4.02</td></tr>
<tr><td>boxcox_lambda</td><td>0.36</td><td>0.27–0.43</td><td>-0.369</td><td>-0.0772</td><td>0.171</td></tr>
<tr><td>sigma_meas</td><td>0.32</td><td>0.25–0.38</td><td>0.83</td><td>1.21</td><td>1.75</td></tr>
<tr><td>bg_skew</td><td>0.31</td><td>0.24–0.36</td><td>0.563</td><td>0.88</td><td>1.21</td></tr>
<tr><td>v_skew</td><td>0.30</td><td>0.22–0.41</td><td>0.0749</td><td>0.301</td><td>0.589</td></tr>
<tr><td>vol_cluster_60m</td><td>0.30</td><td>0.22–0.35</td><td>0.0775</td><td>0.119</td><td>0.161</td></tr>
<tr><td>between_day_frac</td><td>0.23</td><td>0.16–0.28</td><td>0.0642</td><td>0.109</td><td>0.174</td></tr>
<tr><td>v_kurtosis</td><td>0.12</td><td>0.04–0.23</td><td>1.61</td><td>2.65</td><td>3.99</td></tr>
</tbody>
</table>
</div>
<p class="foot" style="margin-top:12px">p10 / median / p90 are across people, of each person's own average — the spread a trait actually has in the population.</p>
</section>

<hr>

<section>
<p class="eyebrow">Fig 23 · Trait or state, insulin side</p>
<h2>The insulin side is stable in a way the glucose side is not</h2>
<div class="col">
<p>The same weekly-block question, asked of the quantities that need dose, carb
and therapy streams — 69 people, and split three ways: the person's metabolic
operating point, how they run the system, and what their settings say.</p>
<p><strong>Everything here is a trait.</strong> The lowest ICC on the insulin
side, 0.69 for the velocity–insulin correlation, is higher than
most of the glucose dynamics. Insulin action and non-insulin appearance sit at
0.87 — a person's metabolic operating point is more stable week
to week than their mean glucose (0.82). Total daily dose is 0.93.
Carbs announced per day, 0.84, and manual boluses per day,
0.77, are stable enough to call announcing a personal
habit rather than a phase.</p>
<p><strong>Settings are near-constants, and that is a finding about behaviour.</strong>
ISF, carb ratio and scheduled basal each score 0.98–0.97
with a within-person week-to-week variation of <strong>1–4%</strong>. Records show
steady settings edits — a median of six distinct schedule shapes across the window,
and 28 for the busiest tenth — but
the edits are small: people nudge, they do not overhaul. Whatever moves in a
person's glucose from week to week is not, in the main, their settings moving.</p>
<p>One contrast is worth isolating. The share of a person's total daily dose
that is basal scores 0.94, but the share of their insulin <em>action</em> that
comes from the <em>scheduled</em> basal stream scores only 0.74, with a within-person variation of 14%. The first number is stable because it encodes a
choice — how the pump is configured — while the second moves with how much
correction insulin the week actually needed. Configuration is a trait; what the
week demanded on top of it is not.</p>
<p><strong>The automated share of boluses is 0.96</strong> — the
most fixed operational choice in the data, which is what a dosing strategy is. It
does not drift.</p>
<p>The right-hand panel asks the companion question ICC cannot: how far does a
person's own value move week to week? The velocity–insulin correlation moves
about 30% of its own level, manual boluses 25%, carbs and IOB around 20%; insulin
action, appearance and TDD around 10%; settings 1–3%.</p>
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
<p class="foot" style="margin-top:12px">&lambda; is the Box-Cox power normalising glucose; SD/MAD is 1.253 for a Gaussian and 1.414 for a Laplace; "noise" is per-reading sensor noise in mg/dL and noise&nbsp;% its share of five-minute velocity variance; H is the scaling exponent in each regime (0.5 = random walk); ACF zero is where increment autocorrelation turns negative; basal share is the fraction of insulin action coming from scheduled basal (blank for the four people with glucose only).</p>
</section>

<section>
<p class="eyebrow">What bounds these numbers</p>
<h2>Limits worth carrying</h2>
<div class="col">
<ul>
<li><strong>Both tails are censored at 40 and 400 mg/dL.</strong> The sensor
clamps rather than reporting beyond its range, and up to 3.3% of one person's
samples sit piled at the ceiling. Nothing about the distribution outside that
window is recoverable from CGM.</li>
<li><strong>The lower tail is intervened upon</strong> — by the controller, by
counter-regulation, by rescue carbs. Between clamping and intervention it is not a
free-running distribution and should not be modelled as one.</li>
<li><strong>Tail statistics depend on the window.</strong> Kurtosis over a week and
over four months are different numbers for the same person; every figure here
states which it used.</li>
<li><strong>The extreme tails contain sensor artefacts.</strong> Rate outliers
above 5 mg/dL per minute occur about once every two days for the median person and
up to five times a day for the busiest tenth, including a 108&nbsp;mg/dL jump in
60 seconds. Those are sensor restarts, not physiology, and
they inflate kurtosis; nothing here filters them.</li>
<li><strong>Gaps are slightly informative.</strong> Coverage is high — median 96% of expected samples present, 4.0% of time inside gaps — and no statistic is
ever computed across a gap. But the last reading before a gap sits +0.12 SD from the person's mean, with both tails over-represented (3.8% vs 2.2% below 70, 11.3% vs 7.5% above 250). Sensors drop out from unusual glucose slightly more often than from
ordinary glucose, so the observed extremes are marginally under-sampled — in the
same direction as the censoring at 400: the true tails are at least as heavy as
what is plotted, never lighter.</li>
<li><strong>The insulin model is unknown for most of the wide cohort.</strong>
Insulin activity is the convolution of delivery with a model curve, and the
model comes from the recorded insulin brand. Thirty-eight of fifty-six wide
donors record no brand and default to rapid-acting adult; where the true insulin
is faster, their activity is placed later than it really occurred. Level
statistics are unaffected; timing-sensitive ones carry that error.</li>
<li><strong>The wide cohort is not individually validated.</strong> The eleven
reference donors each had their replay configuration checked against their own
field outcomes; the fifty-six added did not. They are kept distinguishable in every
figure and never pooled silently.</li>
<li><strong>Association, not effect.</strong> Anything conditioned on insulin is
observational data in which dosing already responded to state. None of it
identifies what would happen if a controller acted differently.</li>
<li><strong>Sensitivity to sampling.</strong> These are Loop users with long,
near-complete records — people whose data is this good are not a random sample of
anyone.</li>
</ul>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Sources</p>
<div class="col">
<p>All Loop users. 73 people for anything computable from glucose alone; 69 with
full dose, carb and therapy streams for the insulin-side views. Eleven of those
are donors whose replay configuration was individually validated against field
outcomes, two are Nightscout sites, and sixty were added from the wider donor pool
without that validation — fifty-six of them with full insulin data. Selection was Loop users with at least 105 days
inside one fixed window. Everyone is referred to by alias.</p>
<p>Built by <code>analysis/loopeval_analysis/{dists,volatility,traits}.py</code>
and <code>analysis/dist_views/</code>. The panel reproduces the reference cohort's
time in range, time below 54, mean glucose and carbs per day independently, and
total absorbed insulin matches total delivered to 0.3%.</p>
</div>
</section>

</div>
"""


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
    build(BODY.replace("__ROWS__", rows()))
