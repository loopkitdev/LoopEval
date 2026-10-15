#!/usr/bin/env python3
"""ISF, Rule of X and Outcomes — how Loop users set ISF and the max-basal cap
against their insulin use, and what goes with time in range and lows.

Built around the 2026-09-24 thread (who meets TIR >= 80% with time below 54
<= 1%, the rule of X they run, rule-of-X bands, strategy and max basal), with the
cap and bolusing follow-ups. Every number is read from settings_claims.json
(settings_claims.py); figures w01-w03 from settings_thread_views.py, s03-s04 from
settings_views.py. Run web_figs.py before this.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import page  # noqa

TITLE = "ISF, Rule of X and Outcomes"
FILENAME = "settings_outcomes.html"
C = json.loads((page.OUT / "settings_claims.json").read_text())


def p(v):
    """A p-value in words-friendly form."""
    return "p &lt; 0.001" if v < 0.001 else f"p = {v:.3f}" if v < 0.01 else f"p = {v:.2f}"


def r(key, i=0):
    return C[key][i]


T = C["thread"]
rb = C["rule_bins"]
st = C["temp_2x2"]
tb = C["tir_by_boluses"]
tiers = T["tiers"]
ix = T["implied_x"]
ff = T["fifths"]
b2 = T["bins200"]
sb = T["strategy_bins"]
ht = T["temp_headroom_thirds"]
av = T["ab_vs_temp"]


def row(cells, head=False):
    tag = "th" if head else "td"
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


TIER_TABLE = ("<div class='scroll'><table><thead>" + row(["Outcome", "People", "Median TDD", "Median ISF",
              "Rule of X", "Median TIR", "t&lt;54", "t&lt;70"], True) + "</thead><tbody>"
              + "".join(row([k.replace("<", "&lt;"), v["n"], f"{v['tdd_use']:.0f}", f"{v['isf']:.0f}",
                             f"<strong>{v['k1800']:.0f}</strong>", f"{v['tir']:.0f}", f"{v['t54']:.1f}", f"{v['t70']:.1f}"])
                        for k, v in tiers.items()) + "</tbody></table></div>")
IMPLIED_TABLE = ("<div class='scroll'><table><thead>" + row(["TDD, U/day", "Rule of 1800 ISF", "Cohort ISF",
                 "Target-group ISF", "Implied rule of X"], True) + "</thead><tbody>"
                 + "".join(row([t, f"{v['r1800']:.0f}", f"{v['cohort']:.0f}", f"{v['well']:.0f}",
                                f"<strong>{v['x']:.0f}</strong>" + ("" if v["inside"] else " *")])
                           for t, v in ix.items()) + "</tbody></table></div>")
FIFTH_TABLE = ("<div class='scroll'><table><thead>" + row(["ISF relative to peers at the same TDD", "People",
               "As a rule of X at 40 U/day", "Median TIR", "Median t&lt;54", "Share with t&lt;54 &gt; 1%",
               "Share meeting the target"], True) + "</thead><tbody>"
               + "".join(row([k + (" fifth" if k in ("strongest", "weakest") else ""), v["n"], f"~{v['x40']:.0f}",
                              f"{v['tir']:.0f}", f"{v['t54']:.2f}", f"{v['over1']:.0f}%", f"{v['well']:.0f}%"])
                         for k, v in ff.items()) + "</tbody></table></div>")
BIN_TABLE = ("<div class='scroll'><table><thead>" + row(["Rule of X", "People", "Median TIR", "TIR middle half",
             "Median t&lt;54", "Median t&lt;70", "Median TDD", "Meeting the target"], True) + "</thead><tbody>"
             + "".join(row([k.replace("<", "&lt;"), v["n"], f"<strong>{v['tir']:.0f}</strong>",
                            f"{v['tir25']:.0f}–{v['tir75']:.0f}", f"{v['t54']:.2f}", f"{v['t70']:.1f}",
                            f"{v['tdd']:.0f}", f"{v['well']:.0f}%"]) for k, v in b2.items()) + "</tbody></table></div>")
STRAT_TABLE = ("<div class='scroll'><table><thead>" + row(["Rule of X", "Automatic bolus: people", "TIR",
               "t&lt;54", "Temp basal: people", "TIR", "t&lt;54", "Temp basal pinned at cap when &gt; 180"], True)
               + "</thead><tbody>" + "".join(row([k.replace("<", "&lt;"), sb["bolus"][k]["n"], f"{sb['bolus'][k]['tir']:.0f}",
                                                  f"{sb['bolus'][k]['t54']:.2f}", sb["temp"][k]["n"],
                                                  f"<strong>{sb['temp'][k]['tir']:.0f}</strong>",
                                                  f"{sb['temp'][k]['t54']:.2f}", f"{sb['temp'][k]['pinned']:.0f}%"])
                                             for k in sb["temp"]) + "</tbody></table></div>")
lowT, midT, highT = T["thirds"]["low"], T["thirds"]["mid"], T["thirds"]["high"]
ws = T["well_by_strategy"]
u26, o26 = T["ab_vs_temp_under26"], T["ab_vs_temp_26plus"]
import pandas as _pd
_tt = _pd.read_csv(page.OUT / "settings_tir_tdd.csv").set_index("fifth")    # settings_explore/tir_vs_tdd.py
TT = _tt.to_dict("index")
TDD_TABLE = ("<div class='scroll'><table><thead>" + row(["TDD fifth", "U a day", "People", "Median TIR",
             "Temp basal", "Automatic bolus", "Gap: stronger-ISF half − weaker", "Gap: bolusing more − less"], True)
             + "</thead><tbody>" + "".join(row([q, f"{v['tdd_lo']:.0f}–{v['tdd_hi']:.0f}", v["n"], f"<strong>{v['tir']:.0f}</strong>",
                                                f"{v['tir_temp']:.0f} (n={v['n_temp']})", f"{v['tir_bolus']:.0f} (n={v['n_bolus']})",
                                                f"{v['isf_gap']:+.0f} ({v['isf_lo']:+.0f} to {v['isf_hi']:+.0f})",
                                                f"{v['bol_gap']:+.0f} ({v['bol_lo']:+.0f} to {v['bol_hi']:+.0f})"])
                                           for q, v in TT.items()) + "</tbody></table></div>")
import scipy.stats as _st
_d = _pd.read_csv(page.OUT / "isf_rules.csv").dropna(subset=["tdd_use", "tir"])
TDD_RHO = {"all": _st.spearmanr(_d.tdd_use, _d.tir)[0],
           **{k: _st.spearmanr(g.tdd_use, g.tir)[0] for k, g in _d.groupby("strategy")}}

BODY = f"""
<div class="wrap">

<h1>ISF, Rule of X and Outcomes</h1>
<p class="lede">Which of {T['n']} Loop users reach time in range of 80% or more with
time below 54 of 1% or less, what ISF and rule of X their settings imply, and how the
rule of X, dosing strategy and the max-basal cap line up with time in range and lows.
Observational throughout: people chose these settings, and nothing here says what
changing one would do.</p>

<section>
<p class="eyebrow">Terms</p>
<div class="col">
<p><strong>ISF</strong> is the scheduled insulin sensitivity factor in mg/dL per unit,
time-weighted over the record. <strong>TDD</strong> is the insulin delivered per day.
The <strong>rule of X</strong> is ISF × TDD: the X in the clinical "rule of 1800"
(ISF = 1800 ÷ TDD) that reproduces a person's ISF. A lower X means a stronger ISF for
the insulin used. <strong>The target</strong> here is the project's own: time in range
70–180 of at least 80% with time below 54 of at most 1%. <strong>Headroom</strong> is
max basal ÷ scheduled basal. <strong>Partial correlations</strong> are Spearman
correlations with the named variables held fixed.</p>
</div>

<div class="ledger">
  <div class="cell"><div class="k">Meeting the target</div><div class="v">{T['well_n']} of {T['n']}</div>
    <div class="n">TIR ≥ 80% with time below 54 ≤ 1%.</div></div>
  <div class="cell"><div class="k">Their rule of X</div><div class="v">{T['well_k1800'][0]:.0f}</div>
    <div class="n">Median, against {T['well_k1800'][1]:.0f} for everyone else ({p(T['well_k1800'][2])}).</div></div>
  <div class="cell"><div class="k">ISF against same-TDD peers</div><div class="v">{100 * (1 - T['well_ratio'][0]):.0f}% stronger</div>
    <div class="n">For the target group ({p(T['well_ratio'][2])}); all of it in the lowest third of TDD.</div></div>
  <div class="cell"><div class="k">Time below 54 across rule-of-X bands</div><div class="v">flat</div>
    <div class="n">No band differs (p = {T['bins200_p_t54']:.2f}); time in range does ({p(T['bins200_p_tir'])}).</div></div>
</div>
</section>

<hr>

<section>
<p class="eyebrow">Fig w01 · Who meets the target</p>
<h2>They run a rule of X near 1500, mostly because they use less insulin</h2>
<div class="col">
<p>{T['well_n']} of {T['n']} people meet the target. Their median rule of X is
<strong>{T['well_k1800'][0]:.0f}</strong>, against {T['well_k1800'][1]:.0f} for everyone
else and a cohort-wide {C['rule_median']:.0f}.</p>
</div>
{TIER_TABLE}
<div class="col">
<p>Most of that gap is insulin use, not ISF. Their ISF is barely different
({T['well_isf'][0]:.0f} against {T['well_isf'][1]:.0f}, {p(T['well_isf'][2])}), but
they take much less insulin: {T['well_tdd_use'][0]:.0f} U a day against
{T['well_tdd_use'][1]:.0f}. And ISF × TDD rises with TDD: across the cohort, ISF falls as
TDD<sup>{T['fit_b']:.2f}</sup>, not TDD<sup>1</sup> (best fit ISF ≈
{T['fit_K']:.0f} ÷ TDD<sup>{T['fit_b']:.2f}</sup>), so a low-TDD group lands on a low
constant almost automatically. Meeting the target is concentrated in low TDD:
{lowT['well']} of {lowT['n']} in the lowest third (under {T['tdd_third_edges'][0]:.0f} U a day),
{midT['well']} of {midT['n']} in the middle third, {highT['well']} of {highT['n']} in the highest.</p>
<p>Against peers who use the same amount of insulin, the gap shrinks but does not
disappear. The target group runs an ISF <strong>{100 * (1 - T['well_ratio'][0]):.0f}%
stronger</strong> than expected for their TDD (ratio {T['well_ratio'][0]:.2f} against
{T['well_ratio'][1]:.2f}, {p(T['well_ratio'][2])}). All of it is in the lowest TDD third
({lowT['ratio_well']:.2f} against {lowT['ratio_rest']:.2f}, {p(lowT['p'])}); in the middle
third it disappears ({midT['ratio_well']:.2f} against {midT['ratio_rest']:.2f},
{p(midT['p'])}), and the highest third has too few to test.</p>
<p>Turned into a rule of X by TDD, using the cohort's curve shifted to the target group's
level (ISF ≈ {T['well_curve_K']:.0f} ÷ TDD<sup>{T['fit_b']:.2f}</sup>):</p>
</div>
{IMPLIED_TABLE}
<p class="foot">* Outside the target group's TDD range ({T['well_tdd_range'][0]:.0f}–{T['well_tdd_range'][1]:.0f} U a day); only {T['well_tdd_range'][2]} of them use more than 50 U a day, so the upper rows are mostly extrapolation.</p>
<figure><img alt="ISF against TDD with the target group highlighted, the rule of X by outcome tier, and ISF relative to same-TDD peers within thirds of TDD" src="{{{{FIG:w01_target}}}}">
<figcaption><b>w01</b> · Left: ISF against TDD, log axes; green are the {T['well_n']} meeting the target, with the rule of 1800, the cohort fit and the cohort fit at the target group's level. Centre: rule of X by outcome tier, medians marked; the dashed line is 1800. Right: ISF ÷ the cohort-expected ISF for that TDD, within thirds of TDD; below 1 is stronger than peers.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig w02 · What rule of X goes with what</p>
<h2>A stronger ISF for the TDD goes with more time in range and no more serious lows</h2>
<div class="col">
<p>Splitting everyone into fifths by ISF relative to peers at the same TDD (shown as the
rule of X it would be at 40 U a day):</p>
</div>
{FIFTH_TABLE}
<div class="col">
<p>Time in range differs across the fifths ({p(T['fifths_p_tir'])}); time below 54 and
below 70 do not (p = {T['fifths_p_t54']:.2f} and {T['fifths_p_t70']:.2f}).</p>
<p>By the rule of X people's settings imply, in steps of 200:</p>
</div>
{BIN_TABLE}
<div class="col">
<ul>
<li><strong>From about 1200 to 2200 time in range is broadly flat</strong>, a median of
64–70%. Moving a few hundred either side of 1800 does not go with a visible difference.</li>
<li><strong>Above 2200 it drops</strong>, to {b2['2200–2500']['tir']:.0f}–{b2['2500+']['tir']:.0f}%: people
whose ISF is weak for their insulin use.</li>
<li><strong>Below 1200 is a different group</strong>: {T['sub1200']['n']} people at a median
{b2['< 1200']['tir']:.0f}%, {T['sub1200']['well']} of them meeting the target. They use the least
insulin (median {T['sub1200']['tdd']:.0f} U a day), {T['sub1200']['temp']} of {T['sub1200']['n']} are
temp-basal users on twiist, and they carry more mild lows: time below 70 of
{T['sub1200']['t70']:.1f}% against {T['sub1200']['t70_rest']:.1f}% for everyone else.</li>
<li><strong>Time below 54 is flat across every band</strong> (p = {T['bins200_p_t54']:.2f}).</li>
</ul>
<div class="read"><p><strong>On "what rule of X suits Loop users".</strong> 1800 describes the
typical user here, not the ones meeting the target, who sit nearer 1500. But X is not one
number: for the target group it climbs from about {ix['15']['x']:.0f} at 15 U a day to about
{ix['60']['x']:.0f} at 60. It also differs by strategy: target-group automatic-bolus users sit on
the cohort curve (ratio {ws['bolus']['ratio']:.2f}, median X {ws['bolus']['x']:.0f}, n = {ws['bolus']['n']}),
temp-basal users well below it (ratio {ws['temp']['ratio']:.2f}, median X {ws['temp']['x']:.0f},
n = {ws['temp']['n']}). This is association; these people chose their settings.</p></div>
</div>
<figure><img alt="Time in range, time below 54 and TDD by rule-of-X band in steps of 200" src="{{{{FIG:w02_bins}}}}">
<figcaption><b>w02</b> · Each dot is a person, green if meeting the target; black bars are medians. The dashed line marks 1800.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig w03 · Dosing strategy and the max-basal cap</p>
<h2>The rule of X matters more for temp-basal users, and their cap tracks the lows</h2>
<div class="col">
<div class="read"><p><strong>Strategy is also a device here.</strong> Temp-basal users are
{C['strategy_pump']['temp']['twiist']} of {C['strategy_n']['temp']} on twiist with Libre 3;
automatic-bolus users are {C['strategy_pump']['bolus']['Omnipod']} of {C['strategy_n']['bolus']} on
Omnipod with Dexcom. Only {C['strategy_pump']['temp']['Omnipod']} Omnipod users run temp basal.</p></div>
</div>
{STRAT_TABLE}
<div class="col">
<ul>
<li><strong>The rule of X tracks time in range far more for temp-basal users</strong>
(ρ {T['strategy_rho_temp']:+.2f}, {sb['temp']['< 1400']['tir']:.0f}% → {sb['temp']['2200+']['tir']:.0f}%)
than for automatic-bolus users (ρ {T['strategy_rho_bolus']:+.2f},
{sb['bolus']['< 1400']['tir']:.0f}% → {sb['bolus']['2200+']['tir']:.0f}%). The sub-1400 group is
mostly temp-basal users, {sb['temp']['< 1400']['well']:.0f}% of whom meet the target.</li>
<li><strong>For temp-basal users, max basal is where corrections come from.</strong> Their
median max basal is {T['temp_max_basal']:.2f} U/hr, {T['temp_headroom']:.1f}× scheduled basal;
automatic-bolus users almost never reach theirs. Low-X temp-basal users run into it: pinned
at the cap {T['temp_low_x_pinned'][0]:.0f}% of their time above 180, against
{T['temp_low_x_pinned'][1]:.0f}% ({p(T['temp_low_x_pinned'][2])}), with a lower max basal
({T['temp_low_x_maxbasal'][0]:.2f} against {T['temp_low_x_maxbasal'][1]:.2f} U/hr).</li>
<li><strong>Headroom tracks the lows; the rule of X does not.</strong> Temp-basal users with
the most headroom ({ht['high']['headroom']:.1f}×) have a median time below 70 of
{ht['high']['t70']:.1f}%, against {ht['low']['t70']:.1f}% for those with the least
({ht['low']['headroom']:.1f}×).</li>
</ul>
<h3>Automatic bolus against temp basal</h3>
<p>Time in range is similar ({av['tir'][0]:.0f}% against {av['tir'][1]:.0f}%, {p(av['tir'][2])}),
but automatic-bolus users have more severe lows: time below 54 of {av['t54'][0]:.2f}% against
{av['t54'][1]:.2f}% ({p(av['t54'][2])}), and {T['ab_vs_temp_over1'][0]:.0f}% of them above 1%
against {T['ab_vs_temp_over1'][1]:.0f}%. That holds after TDD, age and target (partial ρ
{C['t54_strategy_partial'][0]:+.2f}, {p(C['t54_strategy_partial'][1])}), and while running a weaker
ISF (X {av['k1800'][0]:.0f} against {av['k1800'][1]:.0f}). They are also much younger (median age
{av['age_years'][0]:.0f} against {av['age_years'][1]:.0f}), and the difference is concentrated under
26: time below 54 of {u26['t54'][0]:.2f}% against {u26['t54'][1]:.2f}% ({p(u26['t54'][2])}), against
{o26['t54'][0]:.2f}% and {o26['t54'][1]:.2f}% ({p(o26['t54'][2])}) at 26 and over.</p>
</div>
<figure><img alt="Time in range and time below 54 by rule-of-X band split by strategy, and time below 70 by thirds of max-basal headroom" src="{{{{FIG:w03_strategy}}}}">
<figcaption><b>w03</b> · Left and centre: each strategy's people in four rule-of-X bands, medians marked. Right: time below 70 in thirds of headroom within each strategy; labels give the median time below 70 and the headroom multiple. Orange automatic bolus, blue temp basal.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Follow-up · Fig s03</p>
<h2>The cap and ISF act independently, and raising the cap within a person moves both</h2>
<div class="col">
<p>Among the {C['temp_n']} temp-basal users, holding TDD, age, target and the other setting:
the rule of X goes with time in range (partial ρ {r('temp_rule_tir'):+.2f},
{p(r('temp_rule_tir', 1))}) and not with lows; headroom goes with time below 70
({r('temp_head_t70'):+.2f}, {p(r('temp_head_t70', 1))}) and below 54 ({r('temp_head_t54'):+.2f},
{p(r('temp_head_t54', 1))}) and not with time in range ({r('temp_head_tir'):+.2f}). The two settings
barely move together (ρ {C['temp_rule_head_rho']:+.2f}) and do not interact
({p(C['temp_interaction_p']['tir'])} for time in range): a strong ISF with a low cap looks best because
the two effects add. In the strong-ISF half, a low cap goes with time below 70 of
{st['strong|low cap']['t70']:.2f}% against {st['strong|high cap']['t70']:.2f}%, with time in range
unchanged ({st['strong|low cap']['tir']:.0f}% against {st['strong|high cap']['tir']:.0f}%).</p>
<p>Within a person, {C['cap_clean']['raised']} max-basal raises with no ISF change within three days
and at least {C['cap_pre_days_min']} days either side go with time in range
{r('cap_up_tir'):+.1f} points ({p(r('cap_up_tir', 1))}) and time below 70 {r('cap_up_t70'):+.2f}
points ({p(r('cap_up_t70', 1))}). People tend to raise a cap after a bad stretch, so regression to
the mean could inflate the gain in time in range; it cannot explain the rise in lows.</p>
</div>
<figure><img alt="Headroom against time below 70, a two-by-two of ISF strength and cap, and before-and-after time in range for people who raised their cap" src="{{{{FIG:s03_cap}}}}">
<figcaption><b>s03</b> · Temp-basal users. Left: headroom against time below 70, dark for the stronger-ISF half. Centre: median time below 70 in each cell of ISF strength × cap. Right: each person who raised their cap, before and after; black is the median.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Follow-up · Fig s04</p>
<h2>Bolusing tracks time in range; TDD mostly does not once ISF is held</h2>
<div class="col">
<p>User boluses per day is the strongest behavioural correlate of time in range: partial
ρ {r('bol_tir'):+.2f} holding TDD, rule of X, age, target and strategy. Median time in range
runs {tb['< 3']['tir']:.0f}% under 3 a day, {tb['3–5']['tir']:.0f}% at 3–5,
{tb['5–8']['tir']:.0f}% at 5–8 and {tb['≥ 8']['tir']:.0f}% at 8 or more, with a little more
time below 70 ({r('bol_t70'):+.2f}) and no more below 54 ({r('bol_t54'):+.2f}). TDD's own link
to time in range, ρ {r('tdd_tir_raw'):+.2f} raw, falls to {r('tdd_tir_adj'):+.2f}
({p(r('tdd_tir_adj', 1))}) once bolusing and rule of X are held. Age adds nothing
({r('age_tir_adj'):+.2f}). Frequent bolusing is also a marker of engagement: association,
not effect.</p>
</div>
<figure><img alt="Time in range against user boluses per day, and against TDD" src="{{{{FIG:s04_bolus}}}}">
<figcaption><b>s04</b> · Left: each person with the median of each bolusing band. Right: time in range against TDD, log axis. Colour is dosing strategy.</figcaption></figure>
</section>

<section>
<p class="eyebrow">Fig s05 · Time in range against TDD</p>
<h2>At low TDD a stronger ISF separates people; above it, bolusing does</h2>
<div class="col">
<p>Time in range falls as daily insulin rises (ρ {TDD_RHO['all']:+.2f}), more steeply for
temp-basal users (ρ {TDD_RHO['temp']:+.2f}) than automatic-bolus users
(ρ {TDD_RHO['bolus']:+.2f}). Within each fifth of TDD, people were split two ways and the
medians compared. For ISF the quantity split is each person's ISF divided by the ISF the
cohort curve predicts at their own TDD, which removes the TDD that still varies inside a
fifth; the split point is that fifth's median of this ratio, so "stronger" means the half
with the strongest ISF relative to the curve (median ratios
{min(v['ratio_strong'] for v in TT.values()):.2f}–{max(v['ratio_strong'] for v in TT.values()):.2f}
against {min(v['ratio_weak'] for v in TT.values()):.2f}–{max(v['ratio_weak'] for v in TT.values()):.2f}
for the weaker half). For bolusing it is user boluses per day, split at the fifth's median.
Intervals are 90% bootstrap.</p>
</div>
{TDD_TABLE}
<div class="col">
<ul>
<li><strong>The ISF gap is a low-TDD effect.</strong> In the lowest fifth (under
{TT['Q1']['tdd_hi']:.0f} U a day) the stronger-ISF half has
<strong>{TT['Q1']['isf_gap']:+.0f} points</strong> of time in range; in every other fifth the
gap is between {min(TT[q]['isf_gap'] for q in ('Q2','Q3','Q4','Q5')):+.0f} and
{max(TT[q]['isf_gap'] for q in ('Q2','Q3','Q4','Q5')):+.0f}, and no interval excludes zero.
The two halves differ by a similar amount of ISF in every fifth, so this is not a narrower
spread of settings at high TDD.</li>
<li><strong>The bolusing gap points the same way at every TDD</strong>, from
{min(v['bol_gap'] for v in TT.values()):+.0f} to {max(v['bol_gap'] for v in TT.values()):+.0f}
points and largest in the highest fifth; its interval clears zero in
{', '.join(q for q, v in TT.items() if v['bol_lo'] > 0)}.</li>
<li>That is consistent with TDD's own link to time in range shrinking once ISF and bolusing are
held (section s04). With about 31 people per fifth the intervals are wide, strategy shifts
across the fifths, and the lowest fifth includes the children.</li>
</ul>
</div>
<figure><img alt="Time in range against TDD with medians by fifth, and the time-in-range gaps from a stronger ISF and from bolusing more within each fifth" src="{{{{FIG:s05_tir_tdd}}}}">
<figcaption><b>s05</b> · Left: each person's time in range against TDD, log axis, with the median of each fifth. Right: within each fifth, the difference in median time in range between the stronger- and weaker-ISF halves, ISF taken relative to the cohort curve at each person's TDD and split at the fifth's median (green), and the more- and less-bolusing halves (grey), with 90% bootstrap intervals.</figcaption></figure>
</section>

<section>
<p class="eyebrow">What bounds these numbers</p>
<h2>Limits worth carrying</h2>
<div class="col">
<ul>
<li><strong>People chose these settings.</strong> A setting that goes with more time in range may
be one that only people whose glucose already sits mostly in range can use. Only the
within-person cap changes come close to an effect, and there are {C['cap_clean']['raised']} of them.</li>
<li><strong>Strategy, pump and sensor coincide</strong>, and age differs sharply between the
strategies.</li>
<li><strong>Settings are the end-of-window snapshot</strong> for ISF and the cap, used across the
whole record.</li>
<li><strong>TDD includes meal insulin</strong>, so the rule of X mixes sensitivity with diet.</li>
<li><strong>The target group is small</strong> ({T['well_n']} people, {T['well_tdd_range'][2]} above
50 U a day), so its rule-of-X curve is solid only at low and middle TDD.</li>
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
