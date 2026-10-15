#!/usr/bin/env python3
"""An ISF Yardstick — why the ICE work estimates ISF the way it does.

Numbers from isf_split.py, isf_shrink.py, isf_fasting_variants.py,
isf_basal_prior.py; figures r01-r05 from isf_doc_views.py. Run web_figs.py
before this.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import page  # noqa

TITLE = "An ISF Yardstick"
FILENAME = "isf_yardstick.html"

BODY = r"""
<div class="wrap">

<h1>An ISF Yardstick</h1>
<p class="lede">How the counteraction work assigns each of 159 people an insulin
sensitivity factor (ISF), and why. There is no way to measure a true ISF from
closed-loop data. The aim is a number that comes out the same when measured
twice, gives similar people similar values, and can be explained in a
sentence.</p>

<section>
<p class="eyebrow">The recipe</p>
<div class="col">
<ol>
<li><strong>Take the quiet hours.</strong> Hours with no announced carbohydrate
on board, no user bolus in the four hours before, and no pump, sensor or loop
disruption. A typical person has about 12 of them a day.</li>
<li><strong>Measure the slope.</strong> For each quiet hour, note the insulin
absorbed and the change in glucose. Across all of a person's quiet hours, the
extra drop in glucose per extra unit absorbed is their raw slope.</li>
<li><strong>Weigh it by how sure we are.</strong> A noisy slope is pulled toward
what is typical for people with the same fasting insulin rate; a precise one is
left nearly alone.</li>
<li><strong>Apply one shared level factor.</strong> Everyone is multiplied by
the same ×2.01, which puts the cohort median on the median of people's own
settings.</li>
</ol>
<p>The result is a yardstick, not a measurement of the true ISF.</p>
</div>

<div class="ledger">
  <div class="cell"><div class="k">Measured twice</div><div class="v">13%</div>
    <div class="n">Median difference between a person's odd-week and even-week estimates.</div></div>
  <div class="cell"><div class="k">Weight on own data</div><div class="v">0.90</div>
    <div class="n">Median share of the estimate that comes from the person's own slope (p10–p90 0.78–0.95).</div></div>
  <div class="cell"><div class="k">Agrees with settings</div><div class="v">ρ 0.73</div>
    <div class="n">Rank correlation with people's scheduled ISF. Estimate ÷ schedule runs 0.62–1.55 (p10–p90).</div></div>
  <div class="cell"><div class="k">Shared level factor</div><div class="v">×2.01</div>
    <div class="n">The one assumed number. It changes no ranking and no ratio between people.</div></div>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Fig r01 · The measurement</p>
<h2>In quiet hours, more insulin goes with more fall</h2>
<div class="col">
<p>With nothing eaten and nothing broken, two things move glucose: the body's
own steady output pushing up and insulin pushing down. Hours with more insulin
absorbed should show glucose falling further, and they do. The slope of that
relationship is the raw measurement. For the person below, 1,092 quiet hours
give 24&nbsp;mg/dL per unit.</p>
<p>Insulin absorbed comes from delivered doses and the activity curve of the
person's insulin, so the measurement needs no ISF to start from. Hours are
summed as whole 60-minute blocks, which makes sensor noise a small part of
each hour's change.</p>
</div>
<figure><img alt="One person's quiet hours: glucose change against insulin absorbed, with the fitted slope, and the steps from raw slope to final estimate" src="{{FIG:r01_measure}}">
<figcaption><b>r01</b> · Left: every quiet hour as a faint dot, the average of each tenth of the hours in black, and the fitted line. Right: this person's raw slope, the small pull toward the basal rule, the shared level factor, and their scheduled ISF for comparison.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig r02 · The level</p>
<h2>The raw slope runs at half of people's settings, and one shared factor fixes the level</h2>
<div class="col">
<p>Across the cohort the raw slope is a median <strong>0.51×</strong> the
scheduled ISF (p10–p90 0.29–0.78). Some of that gap is real. Much of it comes
from the loop itself: it adds insulin <em>because</em> glucose is rising, so in
the record extra insulin and rising glucose arrive together, and insulin looks
weaker than it is. The data cannot say how much of the gap that explains.</p>
<p>So the level is set by convention. Every estimate is multiplied by the same
×2.01, chosen so the cohort median equals the scheduled median of
45&nbsp;mg/dL per unit. A shared factor changes no one's position relative to
anyone else. It keeps gram-equivalents and corrections in the same currency as
people's own carb ratios and ISFs.</p>
</div>
<figure><img alt="Raw slope relative to the schedule, and the final estimate against the scheduled ISF" src="{{FIG:r02_level}}">
<figcaption><b>r02</b> · Left: raw slope ÷ scheduled ISF, one dot per person, median and p10–p90 marked. Right: final estimate against scheduled ISF on log axes; the dashed line is equality.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig r03 · Weighing the evidence</p>
<h2>A noisy slope leans on what is typical for the person's basal rate</h2>
<div class="col">
<p>Some people have fewer quiet hours or noisier ones, and their slope is less
certain. Each estimate is a weighted blend of the person's own slope and the
value typical for people with the same <strong>fasting insulin rate</strong>,
the insulin they absorb per hour while quiet. The weight compares the
uncertainty in their slope with how much people genuinely differ. People
differ a lot, about ±44% beyond what basal predicts. A whole record's slope is
uncertain by a calibrated 9% (13% for half a record). So the weight on a person's own data is high,
a median 0.90, and the typical estimate moves only 2%.</p>
<p>The uncertainty is calibrated against the data rather than taken from the
regression formula. Quiet hours follow one another and are not independent,
so the formula understated the real odd-week-to-even-week scatter by a factor
of 1.34. Every uncertainty is widened by that factor before it sets a
weight.</p>
</div>
<figure><img alt="Distribution of the weight on each person's own slope, and own slope against final estimate coloured by weight" src="{{FIG:r03_shrink}}">
<figcaption><b>r03</b> · Left: weight on the person's own slope, one dot per person. Right: the slope alone (with the same shared factor) against the final estimate; colour is the weight, and points above or below the dashed line were pulled toward the basal rule.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig r04 · Why basal, not daily insulin</p>
<h2>A rule built on total daily insulin mistakes appetite for resistance</h2>
<div class="col">
<p>The standard rule of thumb scales ISF with total daily insulin, the "rule of
1800". But total daily insulin includes the insulin for meals. Two people with
the same sensitivity and different diets have different totals, and the rule
would call the bigger eater more resistant.</p>
<p>The data show exactly that. Measured against a daily-insulin rule, a
person's estimate drifts upward with how much carbohydrate they announce
(ρ&nbsp;+0.30, p&nbsp;&lt;&nbsp;0.001), and people's own schedules show the same
drift. Measured against a rule built on the fasting insulin rate, the link is
gone (ρ&nbsp;+0.00). The fasting rate tracks people's scheduled ISF about as
well as daily insulin does (ρ&nbsp;−0.78 against −0.81) without carrying
their diet. The basal rule fitted across the cohort is
ISF&nbsp;≈&nbsp;48&nbsp;÷&nbsp;fasting&nbsp;rate<sup>0.66</sup>.</p>
</div>
<figure><img alt="Departure from the daily-insulin rule and from the basal rule against announced carbohydrate" src="{{FIG:r04_why_basal}}">
<figcaption><b>r04</b> · Each person's estimate relative to the rule it leans on, against announced carbohydrate per day. Colour is announcing behaviour: blue non-announcer, green moderate, orange heavy.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig r05 · Does it repeat</p>
<h2>Measured on alternate weeks, a person gets nearly the same answer</h2>
<div class="col">
<p>The test of a yardstick is that it gives the same reading twice. Each
person's record was split into alternating calendar weeks, and the slope, its
uncertainty and the fasting rate were recomputed from each half alone. The
halves of the final estimate differ by a median <strong>13%</strong>, down from
18% for the raw slope. About a quarter of people (23%) still differ by more than 25%
between halves; for them, read the estimate as a range.</p>
</div>
<figure><img alt="Odd-week against even-week estimates, raw slope and final estimate" src="{{FIG:r05_repeat}}">
<figcaption><b>r05</b> · Each dot is one person, odd weeks against even weeks, log axes. Left: the raw slope (with the shared factor). Right: the final estimate.</figcaption></figure>

<h3>Against the alternatives</h3>
<div class="col"><p>Every candidate was scored the same way. "Similar people"
is the median difference between each person and their nearest neighbour on
the named traits; "random" is the same for any two people. A rule built on
one trait makes people similar on that trait look identical by construction,
so read the two similar-people columns together.</p></div>
<div class="scroll"><table>
<thead><tr><th>Estimator</th><th>People</th><th>Odd vs even weeks</th><th>&gt; 25% apart</th><th>Similar daily insulin + age</th><th>Similar basal + age</th><th>Random pairs</th><th>Verdict</th></tr></thead>
<tbody>
<tr><td>Scheduled ISF</td><td>159</td><td>untestable*</td><td>—</td><td>25%</td><td>—</td><td>54%</td><td>the reference</td></tr>
<tr><td>Daily-insulin rule</td><td>157</td><td>3%</td><td>0%</td><td>4%</td><td>15%</td><td>41%</td><td>diet-contaminated</td></tr>
<tr><td>Basal rule alone</td><td>158</td><td>2%</td><td>0%</td><td>14%</td><td>2%</td><td>41%</td><td>no own measurement</td></tr>
<tr><td>Own slope alone</td><td>155</td><td>18%</td><td>35%</td><td>28%</td><td>—</td><td>77%</td><td>noisy for some</td></tr>
<tr><td>Meal match</td><td>56</td><td>65%</td><td>71%</td><td>162%</td><td>—</td><td>223%</td><td>too few meals</td></tr>
<tr><td><strong>Own slope, weighed toward basal rule</strong></td><td>158</td><td>13%</td><td>23%</td><td>29%</td><td>32%</td><td>67%</td><td><strong>adopted</strong></td></tr>
</tbody></table></div>
<p class="foot">* The export carries only the end-of-window schedule, so both halves share one value. Meal match: the ISF at which an announced meal's leftover glucose rise equals the grams the insulin did not cover.</p>
</section>

<section>
<p class="eyebrow">What it tracks, and what it does not</p>
<h2>It follows people's own settings and not their diet or age; it tilts by device</h2>
<div class="col">
<p>Where a person's estimate sits above or below the basal rule agrees with
where their own schedule sits (ρ&nbsp;+0.24, p&nbsp;=&nbsp;0.002): two
independent sources, one set by the person and their clinician and one
measured from their quiet hours, see the same difference. It does not track
how much they announce (ρ&nbsp;+0.00) or their age (ρ&nbsp;+0.13, p&nbsp;=&nbsp;0.11).
It does tilt by device: relative to the basal rule, Omnipod users sit 18% lower than
twiist users (p&nbsp;=&nbsp;0.002). Pump, sensor and dosing strategy coincide almost
perfectly here, so this cannot yet be placed: the six Omnipod users on temp basal sit
with the twiist users rather than the other Omnipod users, which points at strategy,
but six people cannot settle it.</p>
</div>
</section>

<section>
<p class="eyebrow">In use</p>
<h2>Three tiers, by how much history a person has</h2>
<div class="col">
<ul>
<li><strong>No dosing or glucose history:</strong> ISF ≈ 1267 ÷ TDD<sup>0.90</sup>
(or 1874 ÷ TDD), fitted to the yardstick. Its median error is about 24%, barely better than
1800 ÷ TDD at 25%, and adding age does not improve it. It needs a total daily dose from somewhere, and it
inherits that dose's dependence on diet.</li>
<li><strong>Any history:</strong> the yardstick. Until a person has about 100 quiet hours, roughly two
weeks, it is exactly the basal rule from their measured fasting insulin rate. The weight on their own
slope then grows: about half at two weeks, three-quarters at a month, 0.8 beyond. From three weeks on,
two separate stretches of the same person's data differ by about 13–15% and do not converge further, so
month-to-month variation sets the floor, not the amount of data.</li>
</ul>
<p>Measured against grams eaten among the 102 people who announce at least 80 g a day, the yardstick does
not depend on diet (doubling carbs moves it ×0.95, not significant) while the rule of 1800 does
(×0.83, p &lt; 0.001), with the fasting insulin rate held fixed.</p>
</div>
</section>

<section>
<p class="eyebrow">Limits</p>
<h2>What the yardstick cannot do</h2>
<div class="col">
<ul>
<li><strong>Its level is a convention.</strong> The shared ×2.01 is chosen, not
measured. Comparisons between people and over time are meaningful; the
absolute value is anchored to what people set.</li>
<li><strong>Quiet hours are quiet only as far as the record knows.</strong>
Unannounced eating can still sit in them. Requiring no recent glucose rise
tightened agreement with the schedule but cost half the hours, so the simpler
definition was kept.</li>
<li><strong>It is one number per person.</strong> Sensitivity that changes with
time of day, exercise or illness is averaged away. Overnight-only hours are
too few to estimate on their own.</li>
<li><strong>The insulin curve matters.</strong> Absorbed insulin uses the
recorded insulin brand where there is one (72 of 159) and the rapid-acting
default otherwise. Over whole hours of steady insulin the curve's timing has
little effect, but it is not nothing.</li>
<li><strong>Settings are the end-of-window snapshot.</strong> Comparisons with
the schedule use the last recorded settings; people who changed their ISF
mid-window are compared against the newest value.</li>
</ul>
</div>
</section>

__NAV__

</div>
"""


def nav() -> str:
    links = "".join(f'<a href="{u}">{n}</a>' for n, u in page.SIBLINGS.values())
    links += '<a href="https://claude.ai/artifact/UF5D9JAGJ5hZ9KpDQ8eiwV">Insulin Counteraction</a>'
    return f'<nav class="sib"><span class="sib-l">Related:</span>{links}</nav>'


def build() -> Path:
    return page.build(BODY.replace("__NAV__", nav()), FILENAME, TITLE)


if __name__ == "__main__":
    build()
