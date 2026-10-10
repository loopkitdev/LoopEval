#!/usr/bin/env python3
"""Insulin Counteraction — the ICE working document.

Separate from the four-document distribution study: this page holds the ICE
investigation while the definition (above all, the ISF behind it) is still
being settled. Numbers come from ice_first.py, isf_probe.py, isf_corrections.py
and ice_episodes.py; figures from ice_views.py. Run web_figs.py before this.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import page  # noqa

TITLE = "Insulin Counteraction"
FILENAME = "ice.html"

BODY = r"""
<div class="wrap">

<h1>Insulin Counteraction</h1>
<p class="lede">Glucose velocity with modelled insulin activity added back:
the only continuous view the record gives of meals, and of everything else
insulin does not explain. Across 159 people it sees nine in ten of the meals
people announce, at about the size they announced, and a quarter more they never
entered. How big all of it looks depends on the ISF used to compute it, and
that ISF cannot yet be read off the data.</p>

<section>
<p class="eyebrow">Definitions</p>
<div class="col">
<p><strong>ICE</strong> (insulin counteraction effect) at each five-minute step
is the change in glucose plus the glucose-lowering the insulin model says
insulin was doing over the same step, in mg/dL per hour. Insulin activity is
every delivered unit convolved with the person's activity curve and multiplied
by an <strong>ISF</strong> (insulin sensitivity factor, mg/dL per unit).
Unless a figure says otherwise, the ISF is the person's scheduled one.</p>
<p><strong>Fasting</strong> steps have no announced carbohydrate on board, no
user bolus in the previous four hours, and no pump, sensor or loop disruption.
They are about half of all steps (median 50%). The <strong>fasting
baseline</strong> is a person's median ICE over them.</p>
<p>An <strong>episode</strong> is an unbroken stretch where the 30-minute
mean of ICE sits above the fasting baseline. Its size is the glucose it adds,
converted to <strong>gram-equivalents</strong> (g-eq) by the person's carb
sensitivity, ISF ÷ carb ratio. Because the summed glucose change telescopes,
sensor noise barely moves an episode's size. An episode is
<strong>announced</strong> when a carb entry of 5 g or more falls between an
hour before it starts and its end. Everything below uses episodes of at least
10 g-eq.</p>
</div>

<div class="ledger">
  <div class="cell"><div class="k">Announced entries ICE sees</div><div class="v">91%</div>
    <div class="n">Median share of a person's entries of 10 g or more that fall inside an episode (p10–p90 79–97%).</div></div>
  <div class="cell"><div class="k">Size against entry</div><div class="v">1.08</div>
    <div class="n">Gram-equivalents per gram entered over announced episodes. 1.05 for isolated meals in a 4 h window.</div></div>
  <div class="cell"><div class="k">Meal-sized ICE unannounced</div><div class="v">27%</div>
    <div class="n">Median share of episode gram-equivalents with no carb entry. 94% for people announcing under 30 g a day, 15% above 150 g.</div></div>
  <div class="cell"><div class="k">Fasting-fit ISF</div><div class="v">0.50×</div>
    <div class="n">The ISF that makes fasting ICE independent of insulin, as a multiple of the schedule. Closed-loop feedback pulls it low.</div></div>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Fig i01 · What the signal looks like</p>
<h2>Meals stand out as episodes, and some carry no entry</h2>
<div class="col">
<p>Over a day, ICE sits near a fasting level of a few tens of mg/dL per hour.
This is the glucose output that basal insulin exists to cover. It then rises in
episodes of one to four hours that reach several hundred mg/dL per hour. Most
episodes line up with a carb entry. Some do not.</p>
<p>The fasting level itself runs above what the basal schedule covers. At the
scheduled ISF, fasting ICE has a median of <strong>49&nbsp;mg/dL per
hour</strong>, while the scheduled basal rate times ISF comes to
<strong>35</strong> overnight. In Loop's own convention, which counts scheduled
basal as zero, fasting ICE sits at <strong>+10&nbsp;mg/dL per hour</strong>
rather than zero, and only about one person in ten is at or below zero. Most
people's glucose tends to rise on scheduled basal alone, and the loop's extra
delivery covers the difference.</p>
</div>
<figure><img alt="One day of glucose, insulin activity and ICE with episodes shaded by whether a carb entry explains them" src="{{FIG:i01_day}}">
<figcaption><b>i01</b> · One person from the representative sample, 24 hours from 06:00 local. Bottom: ICE at every five minutes (grey) and as a 30-minute mean (black) against the person's fasting baseline (dashed). Shaded episodes are labelled with their size in gram-equivalents, and with the grams entered when a carb entry explains them.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig i02 · The ISF behind it</p>
<h2>Every ICE statistic moves with the ISF, and the data do not yet pick one</h2>
<div class="col">
<p>ICE is linear in the ISF, and each summary moves with it. Recomputed at
half, three-quarters, one and one-and-a-quarter times the schedule:</p>
<ul>
<li>The <strong>fasting baseline</strong> scales almost in proportion, with
medians of 22, 35, 49 and 62&nbsp;mg/dL per hour.</li>
<li><strong>Meal-sized ICE</strong> above the baseline falls from 276 to 174
g-eq per day. A weaker assumed insulin effect leaves more glucose to explain,
and each gram is worth fewer mg/dL.</li>
<li>The <strong>unannounced share</strong> falls from 42% to 22%. Much of what
looks unannounced at a low ISF is insulin's own action, left unaccounted for.</li>
<li><strong>Dips below baseline</strong> go from 3.6 episodes a day at half
the schedule to 1.1 at the schedule and 0.8 above it. A dip is ICE falling
faster than insulin explains.</li>
</ul>
<p>One way to choose an ISF from the data: take the value that makes fasting
ICE uncorrelated with insulin absorbed. Regress each fasting hour's change in
glucose on the units absorbed over that hour. The fitted ISF lands at a median
of <strong>0.50× the schedule</strong> (p10–p90 0.28–0.78). It ranks people
the same way their schedules do (Spearman ρ 0.71), so it tracks something real
about each person's sensitivity. It survives 30-minute blocks (0.56×), a
control for the previous hour's trend (0.48×), and using only insulin delivered
at least an hour before the block (0.49×).</p>
<div class="read"><p><strong>The fasting fit is not a measurement of ISF.</strong>
In a closed loop, insulin is delivered <em>because</em> glucose is moving. A
persistent unmodelled rise, such as a slow meal or rising glucose output,
brings more insulin while glucose keeps rising. That makes insulin and velocity
co-move and pulls the fitted slope toward zero. Using only older insulin does
not remove the problem, because the disturbances last longer than the lag. The
fit is biased low by an amount this data cannot bound. It also differs by
dosing strategy: 0.43× for automatic-bolus users against 0.57× for temp-basal
ones (p&lt;0.001).</p></div>
<p>The clinical definition, glucose drop per unit of a correction bolus, needs
corrections given with nothing else going on: no carbs, no other bolus, a
contiguous five hours. Only <strong>19 of the 159</strong> have a dozen such
events. Among them the loop's own compensation holds total insulin absorbed
nearly constant across bolus sizes, so the regression has nothing to fit.</p>
</div>
<figure><img alt="Fasting baseline, meal-sized ICE and unannounced share against the ISF multiple, and the distribution of the fasting-fit ISF relative to the schedule" src="{{FIG:i02_isf}}">
<figcaption><b>i02</b> · Top: each faint line is a person, recomputed at four ISF multiples. The twelve coloured lines are the study's fixed representative sample, and bold is the median. Bottom left: the fasting-fit ISF as a multiple of the schedule, one dot per person, median and p10–p90 marked. Bottom right: fitted against scheduled ISF. The dashed line is equality; the solid line is the median ratio.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig i03 · Announced meals</p>
<h2>What people enter, ICE sees at about the size entered</h2>
<div class="col">
<p>At the scheduled ISF, a median <strong>91%</strong> of a person's carb
entries of 10 g or more fall inside an ICE episode. Over those episodes, ICE
adds up to <strong>1.08 gram-equivalents per gram entered</strong> (p10–p90
0.78–1.78). Isolated meals, with nothing else entered for four hours either
side, give 1.05. That the carb ratio and ISF people set reproduce the size of
the meals they announce is a consistency check on the settings as a pair. It
cannot tell whether both are off by the same factor.</p>
<p>The ratio rises for people who announce little. Their few entries sit inside
larger stretches of unannounced eating, which the episode then counts in full.</p>
<p>How much of meal-sized ICE carries no entry is mostly a statement about the
person: <strong>94%</strong> for the 22 people announcing under 30 g a day,
40% at 30–80 g, 27% at 80–150 g and 15% above 150 g (Spearman ρ −0.73
against announced grams). It is lower among people with a higher time in range
(ρ −0.41). It does not differ by dosing strategy (29% automatic-bolus, 26%
temp-basal).</p>
</div>
<figure><img alt="Share of carb entries that fall inside an ICE episode, ICE size relative to grams entered, and the unannounced share against announced carbohydrate" src="{{FIG:i03_meals}}">
<figcaption><b>i03</b> · Scheduled ISF. Colour is announcing behaviour: blue non-announcer, green moderate, orange heavy.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig i04 · Episodes</p>
<h2>Unannounced episodes are smaller, shorter, and happen late in the day</h2>
<div class="col">
<p>Pooled over 65,113 episodes: announced ones have a median of
<strong>42&nbsp;g-eq</strong> and last 2.8 hours; unannounced ones
<strong>20&nbsp;g-eq</strong> and 1.5 hours. Both have long tails, 10% of
unannounced episodes exceed 53&nbsp;g-eq. Announced gram-equivalents follow
mealtimes, rising from 08:00 with peaks around 14:00 and 19:00–21:00. The
unannounced ones build through the day and peak between <strong>22:00 and
01:00</strong>.</p>
<p>Some unannounced episodes are the second hump of an announced meal rather
than separate eating. A third of them begin within three hours of an announced
episode ending, against 21% expected by chance at the same hour on another day.
The excess is real but covers a minority; most unannounced episodes stand on
their own.</p>
</div>
<figure><img alt="Size and duration distributions of announced and unannounced ICE episodes, and their share by local hour" src="{{FIG:i04_episodes}}">
<figcaption><b>i04</b> · Every episode of 10 g-eq or more across the cohort at the scheduled ISF. Left and centre: the share of episodes at least as large or as long as the x value. Right: each kind's gram-equivalents by the local hour its episode starts.</figcaption></figure>
</section>

<section>
<p class="eyebrow">What bounds these numbers</p>
<h2>Limits worth carrying</h2>
<div class="col">
<ul>
<li><strong>ICE is a residual.</strong> Any error in the insulin curve, dose
timing or ISF lands in it with the opposite sign. A curve that is too slow
moves ICE earlier and makes insulin peaks look like dips.</li>
<li><strong>Gram-equivalents use the settings.</strong> They divide by ISF ÷
carb ratio as scheduled, so they are grams in the settings' own currency,
not in food.</li>
<li><strong>"Fasting" means no announced carbs.</strong> For people who
announce little, the fasting baseline includes eating, which lowers every
episode measured against it.</li>
<li><strong>Rescue carbohydrate is in it.</strong> Treating a low appears as
an episode, announced or not, and is a response to the trajectory rather than
an independent input.</li>
<li><strong>The ISF is the end-of-window schedule.</strong> Mid-window setting
changes are not tracked, and the activity curve comes from a recorded brand for
72 of the 159; the rest use the rapid-acting default.</li>
</ul>
</div>
</section>

__NAV__

</div>
"""


def nav() -> str:
    links = "".join(f'<a href="{u}">{n}</a>' for n, u in page.SIBLINGS.values())
    return f'<nav class="sib"><span class="sib-l">Related, the distribution study:</span>{links}</nav>'


def build() -> Path:
    return page.build(BODY.replace("__NAV__", nav()), FILENAME, TITLE)


if __name__ == "__main__":
    build()
