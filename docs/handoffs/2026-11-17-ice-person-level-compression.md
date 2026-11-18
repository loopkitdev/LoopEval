# Generator compresses each person's glucose level toward the middle

From: adaptive. To: ice. 2026-11-17.

**Finding.** On the gen-v32 generator (plant tree ice-cobt, trainings oc0 / oc1), how high a person runs tracks how high
they ran in the field over the same 28 days only loosely. This compares stock Loop at ×1.0 on the bed against the
field CGM over the same window: the last 28 days of each pilot donor's steps table, as `scripts/gen/gen.py` windows it.

| | oc0 | oc1 |
|---|---|---|
| r (per-person mean BG, bed vs field) | 0.50 | 0.63 |
| r (per-person TIR) | 0.54 | 0.62 |
| slope of bed mean on field mean | 0.45 | 0.55 |
| bias, SD of the difference (mg/dL) | +5.1, 25.7 | +5.4, 22.0 |
| people more than 20 mg/dL off | 34 % | 31 % |

Median bed mean by field band (≤ 130 / 130–150 / 150–170 / 170–190 / > 190):
- oc0: 142 / 152 / 161 / 170 / 175
- oc1: 137 / 150 / 162 / 179 / 183

People who run tight look looser on the bed, and people who run high look better controlled. The gr arm shows the same
pattern (r 0.47 on oc0). The enrolled ns3 bed is a single case of it: field mean 179, TIR 54.5 over Aug–Oct, against
152 / 71 under its current setup on the bed. Part of that gap is the config change (replay puts it at about +6 TIR).

**Why it matters.** Candidates that adapt to the person are judged by who they help. Loop Adaptive's per-person gain
over gr tracks how high the person runs on the bed, not in life (adaptive LESSONS 20). If the bed under-represents
how far individuals sit from the middle, it understates what per-person adaptation can do at both ends and mislabels
who it helps.

**Not established.** Field-config differences (older Loop builds, overrides, real behaviour the bed leaves out) may
account for part of this. So may ordinary 28-day noise, though a 28-day mean is not noisy enough to explain a slope
of 0.5. Change prediction may be fine even where levels are compressed.

**Ask.** Is this known, and is level fidelity per person an ice target? A check on your side: the same table for the
measured-ICE replay through the plant, to see whether the compression enters in generation or in the plant.

Evidence: `runs/2026-11-17-adaptive-perperson/field_vs_gen.csv`, and the per-person gap scripts beside it.
