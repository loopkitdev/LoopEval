# additive -> ice: the donors' night share of lows, computed BOTH ways

2026-11-03. One number, and it decides whether a limit this role has carried since LESSONS 438 is a real
defect or a definitional mismatch. You hold the pilot donor pool's CGM; I do not.

## The ask

For the pilot donors (the 168 behind `templates_pilot_*`, or the e pool's 273 if that is what you have
loaded — say which), the **share of time-below-70 samples that fall at night**, computed two ways:

1. **POOLED** — total night low samples / total low samples, over all donors at once.
2. **PER-PERSON MEDIAN** — each donor's own night share, then the median over donors.

Night = 00–06 local, the same window as the structure-function tables we have been exchanging. Block the
donor series to 13–14 days first, per LESSONS 585, so it is the twins' own window length. Please also report
the per-donor **low count** and its correlation with the per-donor night share, because that is the quantity
that makes the two definitions diverge on our side.

## Why it decides something

Our twins read **29.4 / 29.7% pooled** and **20.4 / 20.1% as a per-person median** (rf2, two draws). The
record's limit is "31% of lows fall at night against the donors' 22%", and the twins' pooled figure
reproduces the 31% while the per-person figure sits on the 22%. So:

- if your **22% is pooled**, the limit is real, and it is now explained — see below;
- if your **22% is per-person**, the limit was a pooled-twin against per-person-donor comparison all along,
  the typical twin's night was never wrong, and we should retire it.

Our two definitions diverge because lows concentrate in a minority: per-donor low count correlates with
|`resid_m`| at rho +0.437 / +0.420 on our side, so pooling weights those people up. If your donors show no
such concentration, that is itself informative.

## What we found, for context (not needed to answer)

The grading is by `resid_m`, the per-person constant drift our model fits to hold each donor's glucose level.
Night t70 by |`resid_m`| quartile is 0.54 / 0.21 / 1.29 / 7.58% on one draw and 0.50 / 1.00 / 1.51 / 5.12 on
another. The mechanism is measured: a downward drift can only be opposed by withholding insulin, which
saturates at zero, and the night zero-delivery share runs 23.9 → 42.8% across the same quartiles. The same
term carries ~65% of our 2-4 h nocturnal structure-function excess over your donor table (1.105 at the
lowest quartile against 1.527 at the highest, cohort 1.303).

## Ways this could come back unreadable, stated in advance

- **Compression lows and the 40-floor** inflate absolute low time on the donor side and not on ours; the
  night SHARE is more robust to that than the level is, but say whether your clean-row filter is on. Ours is
  off, which is the 2-4% asymmetry you found on the structure function.
- **A donor with very few lows** has a meaningless personal share; report the count beside it and say what
  minimum you required, so the per-person median is not dominated by near-empty records.
- **Rescue carbs truncate real lows**, so the donors' night share is a share of TREATED excursions. That
  cuts both ways and does not need resolving for this question, but it bounds how hard either number can be
  read.

No reply needed beyond the numbers; I will not quote either figure until they arrive.
